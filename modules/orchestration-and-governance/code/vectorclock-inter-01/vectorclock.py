"""Compare writes with vector clocks, not wall-clock time -- last-write-wins silently drops a concurrent update instead of flagging it as a conflict.

When a value is replicated and two clients update it at nearly the same time on different replicas, you eventually have two versions and must decide what happened. The easy rule is LAST-WRITE-WINS: keep the version with the later wall-clock timestamp, discard the other. It always produces a single answer, and it is wrong exactly when it matters most -- when the two writes were CONCURRENT, neither aware of the other. Those are not a newer-and-older pair; they are a genuine conflict, two independent edits that both deserve to survive (or at least to be surfaced). Last-write-wins cannot tell a concurrent conflict from a legitimate overwrite, because a wall-clock timestamp only orders events, it never says whether one causally depended on the other. So it silently drops one of the two edits -- a lost update -- and reports success.

A VECTOR CLOCK carries the information last-write-wins is missing. It is one counter per node; a write's clock records how many updates from each node the writer had seen when it wrote. Comparing two clocks reveals their causal relationship directly. If every component of clock X is less than or equal to clock Y (and at least one strictly less), then X happened-before Y -- Y's writer had seen X, so Y is a legitimate successor and supersedes it. If that ordering holds in neither direction -- each clock is ahead of the other on some node -- the two writes are CONCURRENT: neither writer saw the other, and it is a true conflict. That distinction, invisible to a timestamp, is exactly the one you need.

With conflicts detected instead of hidden, the system can do the right thing: keep both concurrent versions as siblings and let the application (or a merge function) reconcile them -- union two shopping carts, prompt the user, apply a domain rule -- rather than throwing an edit away. And when a later write genuinely descends from both (a client that read both siblings and wrote a merge), its vector clock dominates them both, so the conflict is recognized as resolved. Last-write-wins would have destroyed one edit at the first step and never known a conflict existed.

The rule: compare replicated writes with vector clocks and treat clocks that are ordered in neither direction as CONCURRENT conflicts to be kept and reconciled, rather than resolving versions by last-write-wins on a wall-clock timestamp, because a timestamp cannot distinguish a concurrent conflict from a causal overwrite, so last-write-wins silently discards one of two independent edits.

On this fixture w1 (A's 'apple') and w2 (B's 'banana') are concurrent -- their clocks {A:1,B:0} and {A:0,B:1} are ordered in neither direction. Last-write-wins keeps w2 (later wall time) and drops 'apple'. Vector clocks flag the conflict, keep both, and recognize w3 ('apple,banana', clock {A:1,B:1}) as the merge that causally dominates both. This computes both.

  --compare   every pair of writes and their vector-clock relationship (before / after / concurrent)
  --resolve   last-write-wins (one survivor, an edit lost) vs vector clocks (conflict kept, then merged by w3)
  --check     two writes are concurrent; last-write-wins drops one while vector clocks flag the conflict and the merge resolves it

nodes and writes are the fixture; every comparison, the LWW winner, and the conflict set are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "vectorclock.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def compare(c1, c2, nodes):
    """Vector-clock relationship: 'before', 'after', 'equal', or 'concurrent'."""
    le = all(c1[n] <= c2[n] for n in nodes)
    ge = all(c1[n] >= c2[n] for n in nodes)
    if le and ge:
        return "equal"
    if le:
        return "before"
    if ge:
        return "after"
    return "concurrent"


def concurrent_pairs(writes, nodes):
    """All pairs of writes whose clocks are ordered in neither direction (true conflicts)."""
    out = []
    for i in range(len(writes)):
        for j in range(i + 1, len(writes)):
            if compare(writes[i]["clock"], writes[j]["clock"], nodes) == "concurrent":
                out.append((writes[i]["id"], writes[j]["id"]))
    return out


def lww_winner(writes):
    """Last-write-wins: the single write with the latest wall-clock time."""
    return max(writes, key=lambda w: (w["wall"], w["id"]))


def dominating(writes, nodes):
    """A write whose clock is >= every other write's clock -- a version that supersedes all others, if one exists."""
    for w in writes:
        if all(compare(w["clock"], o["clock"], nodes) in ("after", "equal") for o in writes):
            return w
    return None


# ----------------------------------------------------------------- printing

def compare_view(data):
    writes, nodes = data["writes"], data["nodes"]
    print("COMPARE — vector-clock relationship of every pair of writes")
    print("-" * 60)
    for i in range(len(writes)):
        for j in range(i + 1, len(writes)):
            a, b = writes[i], writes[j]
            rel = compare(a["clock"], b["clock"], nodes)
            arrow = {"before": "%s -> %s (causal)" % (a["id"], b["id"]), "after": "%s -> %s (causal)" % (b["id"], a["id"]),
                     "concurrent": "%s || %s (CONFLICT)" % (a["id"], b["id"]), "equal": "%s == %s" % (a["id"], b["id"])}[rel]
            print("  %s %s  vs  %s %s   ->  %s" % (a["id"], a["clock"], b["id"], b["clock"], arrow))
    print("-" * 60)
    print("  concurrent (conflicting) pairs: %s" % (concurrent_pairs(writes, nodes) or "none"))


def resolve_view(data):
    writes, nodes = data["writes"], data["nodes"]
    conflict = [w for w in writes if w["id"] in ("w1", "w2")]
    win = lww_winner(conflict)
    dropped = [w["value"] for w in conflict if w["id"] != win["id"]]
    print("RESOLVE — last-write-wins vs vector clocks on the concurrent writes w1, w2")
    print("-" * 66)
    print("  last-write-wins: keeps %s ('%s', wall %d), DROPS %s (lost update)"
          % (win["id"], win["value"], win["wall"], dropped))
    print("  vector clocks:   w1 || w2 concurrent -> keep BOTH as siblings for reconciliation")
    dom = dominating(writes, nodes)
    print("  merge: %s ('%s', clock %s) dominates w1 and w2 -> conflict resolved" % (dom["id"], dom["value"], dom["clock"]))


def check(data):
    print("SELF-TEST — two writes are concurrent; last-write-wins drops one while vector clocks flag the conflict and the merge resolves it")
    print("-" * 132)
    writes, nodes = data["writes"], data["nodes"]
    by_id = {w["id"]: w for w in writes}
    w1, w2, w3 = by_id["w1"], by_id["w2"], by_id["w3"]

    w1_w2_concurrent = compare(w1["clock"], w2["clock"], nodes) == "concurrent"
    print("  w1 and w2 are concurrent (ordered in neither direction) = %s (%s vs %s)" % (w1_w2_concurrent, w1["clock"], w2["clock"]))

    win = lww_winner([w1, w2])
    lww_drops_one = win["id"] in ("w1", "w2") and len([w1, w2]) == 2
    print("  last-write-wins keeps only one of the two edits = %s (keeps %s, drops the other)" % (lww_drops_one, win["id"]))

    lww_loses_data = win["value"] != "apple,banana"
    print("  the last-write-wins survivor is missing the other edit = %s ('%s' has lost the concurrent value)" % (lww_loses_data, win["value"]))

    vclock_flags_conflict = ("w1", "w2") in concurrent_pairs(writes, nodes)
    print("  vector clocks flag w1 || w2 as a conflict (both kept) = %s" % vclock_flags_conflict)

    w3_dominates_both = compare(w1["clock"], w3["clock"], nodes) == "before" and compare(w2["clock"], w3["clock"], nodes) == "before"
    print("  w3 causally dominates both w1 and w2 (the merge) = %s (%s after both)" % (w3_dominates_both, w3["clock"]))

    causal_not_flagged = ("w1", "w3") not in concurrent_pairs(writes, nodes) and ("w2", "w3") not in concurrent_pairs(writes, nodes)
    print("  vector clocks do NOT flag the causal pairs (w1->w3, w2->w3) as conflicts = %s" % causal_not_flagged)

    ok = w1_w2_concurrent and lww_drops_one and lww_loses_data and vclock_flags_conflict and w3_dominates_both and causal_not_flagged
    print("-" * 132)
    print("SELF-TEST %s  w1_w2_concurrent=%s  lww_drops_one=%s  lww_loses_data=%s  vclock_flags_conflict=%s  w3_dominates_both=%s  causal_not_flagged=%s"
          % ("PASS" if ok else "FAIL", w1_w2_concurrent, lww_drops_one, lww_loses_data, vclock_flags_conflict, w3_dominates_both, causal_not_flagged))
    return ok


def main():
    p = argparse.ArgumentParser(description="Vector clocks: compare replicated writes with vector clocks and treat clocks that are ordered in neither direction as CONCURRENT conflicts to be kept and reconciled, rather than resolving versions by last-write-wins on a wall-clock timestamp, because a timestamp cannot distinguish a concurrent conflict from a causal overwrite, so last-write-wins silently discards one of two independent edits.")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--resolve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("nodes=%s  writes=%d  file=%s  (the nodes and versioned writes are a fixture)"
          % (data["nodes"], len(data["writes"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.compare:
        compare_view(data)
    elif args.resolve:
        resolve_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
