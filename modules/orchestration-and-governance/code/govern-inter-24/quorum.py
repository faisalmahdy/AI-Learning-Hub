"""Require a majority to elect a leader, or a network partition elects two and they both accept writes.

A cluster elects one leader so there is a single authority for writes. The danger is the network partition: the
nodes split into groups that cannot see each other, and each group, unable to reach the others, may conclude the
old leader is gone and elect a new one. If the election rule lets ANY group elect -- "whoever can gather its own
side" -- then a partition produces one leader PER group. Now two (or more) leaders each believe they are in
charge, each accepts writes, and the state diverges: split-brain. When the partition heals you have two conflicting
histories and no principled way to merge them. The election rule that allowed each side to proceed independently
is exactly what let two authorities exist at once.

The fix is to require a MAJORITY: a candidate must be backed by more than half of the WHOLE cluster, not just its
own group. This single rule makes split-brain impossible, by a counting argument: two disjoint groups cannot both
contain more than half the nodes, because their sizes would sum to more than the cluster. So at most one group can
ever hold a majority, and at most one leader is ever elected -- across any partition, however the nodes split. The
price is availability: if the partition leaves no group with a majority (a close or three-way split), NO leader is
elected and the cluster refuses writes until it heals. That is the correct trade -- unavailable but consistent
beats available but split-brained -- and it is why real systems (Raft, ZooKeeper, etcd) elect on a quorum.

On this fixture a 5-node cluster needs 3 votes for a majority. Split 3-vs-2, the majority rule elects exactly 1
leader (the group of 3); the any-group rule elects 2 -- split-brain. Split 2-2-1 three ways, the majority rule
elects 0 (no group has 3; safe but unavailable) while the any-group rule elects 3. This computes both.

  --elect      how many leaders each rule elects on the 3-vs-2 partition
  --splits     the leader count under each rule across several partitions, including a three-way split
  --check      the majority rule elects at most one leader on every partition; the any-group rule splits the brain

The cluster size and partitions are the fixture; every leader count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "quorum.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def majority_threshold(nodes):
    """Votes needed for a majority of the whole cluster: more than half."""
    return nodes // 2 + 1


def leaders(groups, nodes, majority):
    """The group sizes that manage to elect a leader under the chosen rule."""
    threshold = majority_threshold(nodes) if majority else 1
    return [g for g in groups if g >= threshold]


# ----------------------------------------------------------------- printing

def elect_view(data):
    part, n = data["partition"], data["nodes"]
    maj = leaders(part, n, majority=True)
    any_ = leaders(part, n, majority=False)
    print("ELECT — %d-node cluster split %s (majority needs %d votes)" % (n, part, majority_threshold(n)))
    print("-" * 60)
    print("  majority rule:   %d leader(s)   (groups that reach %d: %s)" % (len(maj), majority_threshold(n), maj))
    print("  any-group rule:  %d leader(s)   (every non-empty group: %s)" % (len(any_), any_))
    print("-" * 60)
    print("  the any-group rule elects one leader per side -- split-brain; majority elects at most one.")


def splits_view(data):
    n = data["nodes"]
    print("SPLITS — leaders elected per rule across partitions (%d nodes, majority %d)" % (n, majority_threshold(n)))
    print("-" * 60)
    print("  partition     majority   any-group")
    for part in (data["partition"], data["three_way"], [n]):
        print("  %-12s  %d          %d" % (str(part), len(leaders(part, n, True)), len(leaders(part, n, False))))
    print("-" * 60)
    print("  majority is always <= 1 (never split-brain); any-group elects one per group.")


def check(data):
    print("SELF-TEST — the majority rule elects at most one leader on every partition; the any-group rule splits the brain")
    print("-" * 112)
    n, part, three = data["nodes"], data["partition"], data["three_way"]

    majority_one_leader = len(leaders(part, n, True)) == 1
    print("  on the 3-vs-2 split the majority rule elects exactly one leader = %s (%s)" % (majority_one_leader, leaders(part, n, True)))

    any_group_split_brain = len(leaders(part, n, False)) == 2
    print("  on the same split the any-group rule elects two (split-brain) = %s (%s)" % (any_group_split_brain, leaders(part, n, False)))

    majority_never_two = all(len(leaders(p, n, True)) <= 1 for p in (part, three, [n], [4, 1]))
    print("  the majority rule elects at most one leader on every partition = %s" % majority_never_two)

    three_way_safe_unavailable = len(leaders(three, n, True)) == 0 and len(leaders(three, n, False)) == 3
    print("  a three-way split elects 0 under majority (safe, unavailable) but 3 under any-group = %s" % three_way_safe_unavailable)

    majority_more_than_half = majority_threshold(n) > n / 2
    print("  the majority threshold is more than half the cluster = %s (%d > %.1f)" % (majority_more_than_half, majority_threshold(n), n / 2))

    ok = majority_one_leader and any_group_split_brain and majority_never_two and three_way_safe_unavailable and majority_more_than_half
    print("-" * 112)
    print("SELF-TEST %s  majority_one_leader=%s  any_group_split_brain=%s  majority_never_two=%s  three_way_safe_unavailable=%s  majority_more_than_half=%s"
          % ("PASS" if ok else "FAIL", majority_one_leader, any_group_split_brain, majority_never_two, three_way_safe_unavailable, majority_more_than_half))
    return ok


def main():
    p = argparse.ArgumentParser(description="Requiring a majority to elect a leader makes split-brain impossible, because two disjoint groups cannot both hold a majority.")
    p.add_argument("--elect", action="store_true")
    p.add_argument("--splits", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("nodes=%d  partition=%s  majority=%d  file=%s  (the cluster is a fixture)"
          % (data["nodes"], data["partition"], majority_threshold(data["nodes"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.elect:
        elect_view(data)
    elif args.splits:
        splits_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
