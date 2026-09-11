"""Size the quorums so R + W > N -- otherwise a read can contact only replicas that never saw the write, and go stale.

A replicated store keeps N copies of each key so it survives node failures. A write does not have to reach all N copies
to be considered done; it reaches W of them (the write quorum) and returns. A read does not have to consult all N either;
it consults R of them (the read quorum) and returns the newest version it finds. Choosing W and R smaller than N is what
buys availability and low latency -- you can write while some replicas are down, and read from whichever are nearby. But
it puts a correctness condition on the two numbers, because a read only sees a write if the read set and the write set
share at least one replica: that shared replica is the one carrying the new version into the read. If the read set and
the write set are disjoint, the read contacts only replicas that never received the write and confidently returns the old
value.

The condition for the sets to be guaranteed to overlap is exactly R + W > N. It is pigeonhole: the write touched W of N
replicas, the read touches R of N, and if R + W exceeds N the two subsets cannot fit into N slots without colliding, so
they must share at least one replica. If R + W <= N, there is room for a disjoint read and write, and a stale read is
possible -- not on every read, but on the ones whose read set happens to miss the written replicas, which is precisely
the kind of intermittent, unreproducible staleness that is miserable to debug. This is the tuning knob behind 'eventual'
versus 'strong' read-your-writes consistency in quorum systems: W + R > N gives you the overlap guarantee (common choices
are W = R = the majority, or write-all/read-one, or write-one/read-all), and anything less trades that guarantee for
lower latency.

On this fixture with N = 3, the config W = 1, R = 1 has R + W = 2, which is not greater than 3, so the minimum overlap
between a write set and a read set is 0: writing only replica 0 and reading only replica 1 returns the stale old version.
The config W = 2, R = 2 has R + W = 4 > 3, so every read set and write set share at least one replica (minimum overlap
1): writing replicas 0 and 1 and then reading replicas 1 and 2 finds the new version on replica 1. The minimum overlaps
here are found by enumerating every subset pair, not assumed. This computes both.

  --quorum   each config's R + W vs N and the worst-case (minimum) overlap between a read set and a write set
  --stale    a concrete disjoint read under W1R1 that returns the stale value, and an overlapping read under W2R2 that does not
  --check    R + W > N gives a guaranteed non-zero overlap; R + W <= N allows a disjoint, stale read; the concrete reads match

The replica count and configs are the fixture; every overlap and read is computed by enumerating the actual subsets. Stdlib only.
"""
import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "quorum.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def min_overlap(n, w, r):
    """The smallest possible intersection between any W-subset and any R-subset of N replicas -- enumerated, not assumed."""
    return min(len(set(ws) & set(rs)) for ws in combinations(range(n), w) for rs in combinations(range(n), r))


def read_version(replicas, read_set):
    """A read returns the newest version among the replicas it contacted."""
    return max(replicas[i] for i in read_set)


def apply_write(n, write_set, new_version=2):
    """Every replica starts at version 1; the write sets the write_set replicas to the new version."""
    replicas = {i: 1 for i in range(n)}
    for i in write_set:
        replicas[i] = new_version
    return replicas


# ----------------------------------------------------------------- printing

def quorum_view(data):
    n = data["n"]
    print("QUORUM — does the read set always overlap the write set? (N=%d)" % n)
    print("-" * 66)
    print("  config   W    R    R+W    R+W>N    min overlap    stale read?")
    for c in data["configs"]:
        w, r = c["w"], c["r"]
        ov = min_overlap(n, w, r)
        print("  %-7s  %-4d %-4d %-6d %-8s %-14d %s" % (
            c["name"], w, r, r + w, r + w > n, ov, "no" if ov > 0 else "YES -- possible"))
    print("-" * 66)
    print("  overlap is guaranteed exactly when R + W > N.")


def stale_view(data):
    n = data["n"]
    print("STALE — a disjoint read (W1R1) vs an overlapping read (W2R2), N=%d" % n)
    print("-" * 66)
    rep1 = apply_write(n, write_set=[0])
    print("  W=1: write replica 0 -> versions %s" % rep1)
    print("       read replica [1] (R=1, disjoint) -> version %d  <- STALE (missed the write)" % read_version(rep1, [1]))
    rep2 = apply_write(n, write_set=[0, 1])
    print("  W=2: write replicas 0,1 -> versions %s" % rep2)
    print("       read replicas [1,2] (R=2) -> version %d  <- FRESH (replica 1 carried the write)" % read_version(rep2, [1, 2]))
    print("-" * 66)
    print("  the only difference is quorum size: W1R1 lets the read miss the write; W2R2 forces an overlap.")


def check(data):
    print("SELF-TEST — R+W>N gives a guaranteed non-zero overlap; R+W<=N allows a disjoint, stale read; the concrete reads match")
    print("-" * 122)
    n = data["n"]
    cfg = {c["name"]: c for c in data["configs"]}

    w1 = cfg["W1R1"]
    rw_le_n_no_guarantee = (w1["r"] + w1["w"] <= n) and min_overlap(n, w1["w"], w1["r"]) == 0
    print("  W1R1 has R+W<=N and a possible zero overlap = %s (R+W=%d, min overlap %d)"
          % (rw_le_n_no_guarantee, w1["r"] + w1["w"], min_overlap(n, w1["w"], w1["r"])))

    w2 = cfg["W2R2"]
    rw_gt_n_guaranteed = (w2["r"] + w2["w"] > n) and min_overlap(n, w2["w"], w2["r"]) >= 1
    print("  W2R2 has R+W>N and a guaranteed overlap >=1 = %s (R+W=%d, min overlap %d)"
          % (rw_gt_n_guaranteed, w2["r"] + w2["w"], min_overlap(n, w2["w"], w2["r"])))

    concrete_stale = read_version(apply_write(n, [0]), [1]) == 1
    print("  W1R1: writing replica 0 then reading replica 1 is stale = %s" % concrete_stale)

    concrete_fresh = read_version(apply_write(n, [0, 1]), [1, 2]) == 2
    print("  W2R2: writing replicas 0,1 then reading replicas 1,2 is fresh = %s" % concrete_fresh)

    formula_matches = all(min_overlap(n, c["w"], c["r"]) == max(0, c["w"] + c["r"] - n) for c in data["configs"])
    print("  the enumerated min overlap equals max(0, W+R-N) for every config = %s" % formula_matches)

    ok = rw_le_n_no_guarantee and rw_gt_n_guaranteed and concrete_stale and concrete_fresh and formula_matches
    print("-" * 122)
    print("SELF-TEST %s  rw_le_n_no_guarantee=%s  rw_gt_n_guaranteed=%s  concrete_stale=%s  concrete_fresh=%s  formula_matches=%s"
          % ("PASS" if ok else "FAIL", rw_le_n_no_guarantee, rw_gt_n_guaranteed, concrete_stale, concrete_fresh, formula_matches))
    return ok


def main():
    p = argparse.ArgumentParser(description="Quorum consistency: a replicated read sees the latest write only if the read set and write set overlap, which is guaranteed exactly when R + W > N; sizing the read and write quorums below that (R + W <= N) allows a read to contact only replicas that never received the write and return a stale value.")
    p.add_argument("--quorum", action="store_true")
    p.add_argument("--stale", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("N=%d  configs=%s  file=%s  (the replica count and configs are a fixture)"
          % (data["n"], [(c["name"], c["w"], c["r"]) for c in data["configs"]], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.quorum:
        quorum_view(data)
    elif args.stale:
        stale_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
