"""An ANN index searches only the nearest clusters, so it misses a true neighbor across a boundary -- recall < 1 until nprobe rises.

Exact nearest-neighbor search compares the query to every indexed vector and returns the genuinely closest -- perfectly
accurate, but O(N) per query, which does not scale to millions of vectors. So production vector search uses APPROXIMATE
nearest-neighbor (ANN) indexes that are far faster by not looking at every point. A common one is IVF (inverted file): at
build time it partitions the vectors into clusters around centroids; at query time it finds the query's nearest centroids
and searches only the points in those `nprobe` clusters, skipping the rest. Skipping most of the index is where the speed
comes from -- and where the accuracy loss comes from, because a true nearest neighbor that lives in a cluster the query
did not search is simply never seen.

This is not a rare edge case; it happens at every cluster boundary. A point just on the far side of a boundary from the
query can be one of the closest points overall, yet belong to a different cluster than the query's own, so with nprobe=1
(search only the single nearest cluster) it is missed. The result is a returned list that is MISSING some of the true
top-k, measured as recall: the fraction of the exact top-k that the ANN search actually found. ANN search is fast and
lossy; exact search is slow and complete; recall is the number that says how lossy.

The knob is nprobe (for IVF; graph indexes like HNSW have analogous ones): searching more clusters raises recall toward 1
because the boundary neighbors' clusters get included, at the cost of touching more points and so more time. So ANN is a
speed/recall trade-off you tune -- higher nprobe (or ef, for HNSW) buys recall with latency -- and the right operating
point depends on how much missed-neighbor loss the application tolerates. The mistake is treating an ANN index as if it
returned exact results: it returns approximate ones, and its recall must be measured, not assumed.

On this fixture the query at 4.5 is closest to points p1 (4.0) and p2 (5.5), but p2 sits in cluster c1 while the query's
nearest centroid is c0. Exact top-3 is p1, p2, p3. IVF with nprobe=1 searches only c0 and returns p1, p3, p4 -- missing
p2, a true neighbor, for recall 2/3 = 0.67. With nprobe=2 it searches both clusters and recovers the exact top-3, recall
1.0. This computes both.

  --search   the exact top-k vs the IVF result at nprobe=1, with the missed neighbor and the recall
  --nprobe   recall at nprobe=1 vs nprobe=2 -- searching more clusters recovers the boundary neighbor at a cost
  --check    exact search finds all top-k; IVF nprobe=1 misses a boundary neighbor (recall<1); raising nprobe restores recall

The query, centroids, and points are the fixture; every distance, assignment, and recall is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "annrecall.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def dist(a, b):
    return math.dist(a, b)


def nearest_centroid(vec, centroids):
    return min(centroids, key=lambda c: dist(vec, centroids[c]))


def assignments(points, centroids):
    """Assign each point to its nearest centroid -- the IVF cluster it lives in."""
    return {p: nearest_centroid(points[p], centroids) for p in points}


def exact_topk(data):
    """Compare the query to every point and return the k genuinely closest."""
    q, pts, k = data["query"], data["points"], data["k"]
    return sorted(pts, key=lambda p: dist(q, pts[p]))[:k]


def ivf_topk(data, nprobe):
    """Search only the nprobe clusters nearest the query, then take the k closest among their points."""
    q, pts, k, cents = data["query"], data["points"], data["k"], data["centroids"]
    assign = assignments(pts, cents)
    probed = sorted(cents, key=lambda c: dist(q, cents[c]))[:nprobe]
    candidates = [p for p in pts if assign[p] in probed]
    return sorted(candidates, key=lambda p: dist(q, pts[p]))[:k]


def recall(result, exact):
    return len(set(result) & set(exact)) / len(exact)


# ----------------------------------------------------------------- printing

def search_view(data):
    ex = exact_topk(data)
    iv = ivf_topk(data, 1)
    q, cents = data["query"], data["centroids"]
    print("SEARCH — exact top-%d vs IVF nprobe=1 (query %s)" % (data["k"], q))
    print("-" * 62)
    print("  query's nearest cluster: %s" % nearest_centroid(q, cents))
    print("  exact top-%d      : %s" % (data["k"], ex))
    print("  IVF nprobe=1     : %s   <- searched only the query's cluster" % iv)
    missed = [p for p in ex if p not in iv]
    print("-" * 62)
    print("  missed neighbor(s): %s  (recall %.2f)" % (missed, recall(iv, ex)))


def nprobe_view(data):
    ex = exact_topk(data)
    print("NPROBE — recall rises as more clusters are searched")
    print("-" * 58)
    print("  nprobe   result            recall")
    for np_ in (1, 2):
        r = ivf_topk(data, np_)
        print("  %-7d  %-16s  %.2f" % (np_, r, recall(r, ex)))
    print("-" * 58)
    print("  nprobe=1 is fast but misses the boundary neighbor; nprobe=2 is complete here.")


def check(data):
    print("SELF-TEST — exact search finds all top-k; IVF nprobe=1 misses a boundary neighbor (recall<1); raising nprobe restores recall")
    print("-" * 124)
    ex = exact_topk(data)
    q, cents, pts = data["query"], data["centroids"], data["points"]
    assign = assignments(pts, cents)

    exact_full = recall(ex, ex) == 1.0
    print("  exact search returns the full top-%d = %s (%s)" % (data["k"], exact_full, ex))

    iv1 = ivf_topk(data, 1)
    nprobe1_misses = recall(iv1, ex) < 1.0
    print("  IVF nprobe=1 misses a true neighbor = %s (%s, recall %.2f)" % (nprobe1_misses, iv1, recall(iv1, ex)))

    missed = [p for p in ex if p not in iv1][0]
    boundary_neighbor = assign[missed] != nearest_centroid(q, cents)
    print("  the missed neighbor is in a different cluster than the query = %s (%s in %s, query in %s)"
          % (boundary_neighbor, missed, assign[missed], nearest_centroid(q, cents)))

    iv2 = ivf_topk(data, 2)
    nprobe2_full = recall(iv2, ex) == 1.0
    print("  IVF nprobe=2 recovers full recall = %s (%s)" % (nprobe2_full, iv2))

    recall_rises = recall(iv2, ex) > recall(iv1, ex)
    print("  recall rises with nprobe = %s (%.2f -> %.2f)" % (recall_rises, recall(iv1, ex), recall(iv2, ex)))

    ok = exact_full and nprobe1_misses and boundary_neighbor and nprobe2_full and recall_rises
    print("-" * 124)
    print("SELF-TEST %s  exact_full=%s  nprobe1_misses=%s  boundary_neighbor=%s  nprobe2_full=%s  recall_rises=%s"
          % ("PASS" if ok else "FAIL", exact_full, nprobe1_misses, boundary_neighbor, nprobe2_full, recall_rises))
    return ok


def main():
    p = argparse.ArgumentParser(description="ANN recall: an IVF vector index searches only the nprobe clusters nearest the query, so a true neighbor across a cluster boundary is missed and recall (fraction of the exact top-k found) is below 1; raising nprobe recovers recall at the cost of touching more points, so ANN is a tunable speed/recall trade-off, not exact search.")
    p.add_argument("--search", action="store_true")
    p.add_argument("--nprobe", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("query=%s  k=%d  centroids=%s  points=%d  file=%s  (the vectors are a fixture)"
          % (data["query"], data["k"], data["centroids"], len(data["points"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.search:
        search_view(data)
    elif args.nprobe:
        nprobe_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
