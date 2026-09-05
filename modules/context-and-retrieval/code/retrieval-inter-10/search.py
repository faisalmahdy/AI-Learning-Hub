"""Probe enough clusters or approximate nearest-neighbor silently misses the answer across a boundary.

A vector index that searches every document is exact but slow, so production retrieval uses an
approximate index: bucket the documents by their nearest centroid (this is the IVF family -- FAISS,
most vector databases), and at query time search only the nprobe buckets closest to the query. It is
fast because it looks at a fraction of the corpus. It is approximate because the true nearest document
can sit just across a cluster boundary, in a bucket the query did not probe -- so the search returns a
farther document and never knows it was wrong.

The failure is silent and it is not uniform: it strikes exactly the queries that fall near a boundary
between clusters, where the nearest document belongs to a neighbor bucket. Average recall looks fine;
the boundary queries fail. The knob that fixes it is nprobe -- probe more buckets and you catch the
neighbors, at the cost of touching more of the corpus. At nprobe = number-of-clusters the approximate
search becomes exact.

On this fixture five queries hit a three-cluster index. Two of them (q1 and q5) have their true nearest
document one bucket away, so nprobe=1 misses them: recall@1 is 0.60. Bumping to nprobe=2 probes the
neighbor bucket and recovers both: recall@1 is 1.00, matching exhaustive search. This computes the true
nearest by brute force and the approximate nearest at each nprobe, and reports the recall.

  --index      the documents bucketed by nearest centroid, and the queries
  --search     the true nearest vs the nprobe=1 and nprobe=2 nearest for each query
  --check      nprobe=1 misses the boundary queries (recall<1); nprobe=2 recovers exhaustive recall

The centroids, documents, and queries are the fixture; every distance and recall is computed. Stdlib.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "points.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# ------------------------------------------------------------- the index

def bucket_of(point, centroids):
    """Assign a point to its nearest centroid -- the IVF bucket it lands in."""
    return min(centroids, key=lambda c: dist(point, centroids[c]))


def exhaustive_nearest(q, docs):
    """Brute force: the true nearest document, checking every one."""
    return min(docs, key=lambda d: dist(q, docs[d]))


def ann_nearest(q, docs, centroids, buckets, nprobe):
    """Approximate: search only the nprobe buckets nearest the query."""
    order = sorted(centroids, key=lambda c: dist(q, centroids[c]))
    probed = set(order[:nprobe])
    candidates = [d for d in docs if buckets[d] in probed]
    return min(candidates, key=lambda d: dist(q, docs[d]))


def recall_at_1(data, nprobe):
    """Fraction of queries whose approximate nearest equals the true nearest."""
    docs, cents, queries = data["docs"], data["centroids"], data["queries"]
    buckets = {d: bucket_of(p, cents) for d, p in docs.items()}
    hits = 0
    for q in queries.values():
        if ann_nearest(q, docs, cents, buckets, nprobe) == exhaustive_nearest(q, docs):
            hits += 1
    return round(hits / len(queries), 4)


# ----------------------------------------------------------------- printing

def index_view(data):
    docs, cents = data["docs"], data["centroids"]
    buckets = {d: bucket_of(p, cents) for d, p in docs.items()}
    print("INDEX — %d documents bucketed by nearest centroid into %d clusters" % (len(docs), len(cents)))
    print("-" * 50)
    for c in cents:
        members = [d for d in docs if buckets[d] == c]
        print("  bucket %s @ %-8s: %s" % (c, cents[c], " ".join(members)))
    print("-" * 50)
    print("  %d queries to answer: %s" % (len(data["queries"]), " ".join(data["queries"])))


def search_view(data):
    docs, cents, queries = data["docs"], data["centroids"], data["queries"]
    buckets = {d: bucket_of(p, cents) for d, p in docs.items()}
    print("SEARCH — true nearest vs approximate at nprobe 1 and 2")
    print("-" * 58)
    print("  query   true   np=1   np=2   nprobe=1 result")
    for q, pt in queries.items():
        true = exhaustive_nearest(pt, docs)
        a1 = ann_nearest(pt, docs, cents, buckets, 1)
        a2 = ann_nearest(pt, docs, cents, buckets, 2)
        tag = "hit" if a1 == true else "MISS (answer in bucket %s)" % buckets[true]
        print("  %s    %-4s   %-4s   %-4s   %s" % (q, true, a1, a2, tag))
    print("-" * 58)
    print("  the misses are the queries whose nearest doc sits one bucket away.")


def check(data):
    print("SELF-TEST — nprobe=1 misses the boundary queries; nprobe=2 recovers exhaustive recall")
    print("-" * 76)
    cents = data["centroids"]

    r1 = recall_at_1(data, 1)
    r2 = recall_at_1(data, 2)
    r_full = recall_at_1(data, len(cents))

    np1_misses = r1 < 1.0
    print("  nprobe=1 misses some true nearest neighbors = %s (recall@1 = %.2f)" % (np1_misses, r1))

    np2_recovers = r2 == 1.0
    print("  nprobe=2 recovers every true nearest = %s (recall@1 = %.2f)" % (np2_recovers, r2))

    more_probes_help = r2 > r1
    print("  probing more buckets raises recall = %s (%.2f -> %.2f)" % (more_probes_help, r1, r2))

    full_is_exact = r_full == 1.0
    print("  probing all buckets equals exhaustive search = %s (recall@1 = %.2f)" % (full_is_exact, r_full))

    ok = np1_misses and np2_recovers and more_probes_help and full_is_exact
    print("-" * 76)
    print("SELF-TEST %s  np1_misses=%s  np2_recovers=%s  more_probes_help=%s  full_is_exact=%s"
          % ("PASS" if ok else "FAIL", np1_misses, np2_recovers, more_probes_help, full_is_exact))
    return ok


def main():
    p = argparse.ArgumentParser(description="Probe enough clusters or ANN silently misses the true nearest.")
    p.add_argument("--index", action="store_true")
    p.add_argument("--search", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("docs=%d  clusters=%d  queries=%d  file=%s  (the points are a fixture)"
          % (len(data["docs"]), len(data["centroids"]), len(data["queries"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.index:
        index_view(data)
    elif args.search:
        search_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
