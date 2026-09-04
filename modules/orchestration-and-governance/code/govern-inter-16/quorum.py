"""Make the read and write quorums overlap (R + W > N), or a read can miss the latest write.

A value is replicated across N nodes for durability. A write does not have to reach all N -- it succeeds
once W of them acknowledge. A read does not have to ask all N -- it queries R of them and takes the newest
version it sees. This is quorum replication, and it is fast and available because neither operation waits
for every node. The catch is the guarantee: will a read reflect the most recent write? Only if the set of
nodes the read asks is certain to include at least one node the write reached. If R + W is not greater than
N, it is possible to choose R read nodes that are entirely disjoint from the W write nodes -- so the read
sees only stale replicas and returns the old value, even though the write succeeded. Silent stale reads.

The rule that prevents it is R + W > N. By the pigeonhole principle, if the read quorum and the write
quorum together must cover more than N nodes, they cannot fit into N without overlapping -- every possible
read set intersects every possible write set in at least one node, and that node has the latest write, so
the read sees it. Overlap is the guarantee; R + W > N is how you force overlap. Common settings: W = N and
R = 1 (fast reads, slow writes), R = N and W = 1 (the reverse), or R = W = a majority (balanced) -- all
satisfy R + W > N.

On this fixture N = 3 and a write reached 2 nodes (W = 2). A strong config (R = 2, so R + W = 4 > 3) makes
every possible read set include an up-to-date node, so every read is fresh. A weak config (R = 1, so
R + W = 3, not > 3) allows a read set disjoint from the write -- the single node that missed it -- so that
read returns the stale old value. This computes both.

  --config     for each config, whether R + W > N and the overlap guarantee
  --reads      every possible read set and whether it returns fresh or stale, per config
  --check      R + W > N makes every read fresh; R + W <= N allows a stale read

The replica count, versions, and configs are the fixture; every read set is enumerated. Stdlib only.
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "replicas.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def versions(n, write_set):
    """Version per replica: written replicas hold the new version (2), the rest the old (1)."""
    return [2 if i in write_set else 1 for i in range(n)]


def read_value(read_set, vers):
    """A read returns the newest version among the replicas it queried."""
    return max(vers[i] for i in read_set)


def all_read_sets(n, r):
    return [set(c) for c in itertools.combinations(range(n), r)]


def stale_reads(n, r, write_set):
    """Read sets (of size r) that return the OLD version -- i.e. disjoint from the write set."""
    vers = versions(n, write_set)
    new = max(vers)
    return [rs for rs in all_read_sets(n, r) if read_value(rs, vers) != new]


# ----------------------------------------------------------------- printing

def config_view(data):
    n, write_set = data["n"], set(data["write_set"])
    w = len(write_set)
    print("CONFIG — does R + W exceed N = %d? (write reached %d nodes)" % (n, w))
    print("-" * 58)
    for name, r in data["configs"].items():
        ok = r + w > n
        print("  %-8s R=%d W=%d  R+W=%d %s %d  overlap guaranteed: %s"
              % (name, r, w, r + w, ">" if ok else "<=", n, ok))
    print("-" * 58)
    print("  R + W > N is what forces the read and write quorums to overlap.")


def reads_view(data):
    n, write_set = data["n"], set(data["write_set"])
    print("READS — every read set's result (write set = %s, new version = 2)" % sorted(write_set))
    print("-" * 58)
    vers = versions(n, write_set)
    for name, r in data["configs"].items():
        print("  %s (R=%d):" % (name, r))
        for rs in all_read_sets(n, r):
            v = read_value(rs, vers)
            print("    read %-10s -> version %d  %s" % (sorted(rs), v, "fresh" if v == 2 else "STALE"))
    print("-" * 58)
    print("  a read set disjoint from the write set returns the stale version.")


def check(data):
    print("SELF-TEST — R + W > N makes every read fresh; R + W <= N allows a stale read")
    print("-" * 90)
    n, write_set = data["n"], set(data["write_set"])
    w = len(write_set)
    strong_r = data["configs"]["strong"]
    weak_r = data["configs"]["weak"]

    strong_sum_exceeds = strong_r + w > n
    print("  strong config has R + W > N = %s (%d > %d)" % (strong_sum_exceeds, strong_r + w, n))

    strong_all_fresh = len(stale_reads(n, strong_r, write_set)) == 0
    print("  strong config: every read set is fresh = %s" % strong_all_fresh)

    weak_sum_insufficient = not (weak_r + w > n)
    print("  weak config has R + W <= N = %s (%d <= %d)" % (weak_sum_insufficient, weak_r + w, n))

    weak_has_stale = len(stale_reads(n, weak_r, write_set)) > 0
    print("  weak config: some read set returns stale = %s (%s)"
          % (weak_has_stale, [sorted(s) for s in stale_reads(n, weak_r, write_set)]))

    overlap_iff_sum = strong_all_fresh == strong_sum_exceeds and weak_has_stale == weak_sum_insufficient
    print("  freshness holds exactly when R + W > N = %s" % overlap_iff_sum)

    ok = strong_sum_exceeds and strong_all_fresh and weak_sum_insufficient and weak_has_stale and overlap_iff_sum
    print("-" * 90)
    print("SELF-TEST %s  strong_sum_exceeds=%s  strong_all_fresh=%s  weak_sum_insufficient=%s  weak_has_stale=%s  overlap_iff_sum=%s"
          % ("PASS" if ok else "FAIL", strong_sum_exceeds, strong_all_fresh, weak_sum_insufficient, weak_has_stale, overlap_iff_sum))
    return ok


def main():
    p = argparse.ArgumentParser(description="Make the read and write quorums overlap (R + W > N).")
    p.add_argument("--config", action="store_true")
    p.add_argument("--reads", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("N=%d  write_set=%s  configs=%s  file=%s  (the replicas and configs are a fixture)"
          % (data["n"], data["write_set"], data["configs"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.config:
        config_view(data)
    elif args.reads:
        reads_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
