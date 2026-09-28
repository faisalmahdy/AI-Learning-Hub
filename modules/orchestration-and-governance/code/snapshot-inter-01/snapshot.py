"""Snapshot a distributed system by capturing the in-flight messages on the channels, not just each node's local state -- otherwise the global picture loses or double-counts whatever was in transit.

You want a snapshot of a running distributed system: a consistent backup, a checkpoint to restart from, a distributed debugger's view, a check for deadlock or termination. The obvious approach is to ask every node for its current state and staple the answers together. It does not work, because there is no shared instant at which all the nodes are recorded. Each node reports its state at a slightly different real time, and while you are collecting, messages are traveling on the channels between nodes -- money mid-transfer, a request sent but not yet handled, a token in flight.

Consider two accounts and a transfer. A starts with 100, B with 0, and A sends 30 to B. For a stretch of real time the 30 has left A (A now holds 70) but has not yet arrived at B (B still holds 0); the 30 is on the channel from A to B. Now snapshot naively. Record A after it sent (70) and B before it received (0), and ignore the channel: your snapshot totals 70 -- the 30 in transit is simply gone, money the real system never lost. Record A before it sent (100) and B after it received (30), still ignoring the channel: your snapshot totals 130 -- the same 30 counted twice. Both snapshots show a global state that never existed and that breaks the conservation the real system always obeys.

The fix is the Chandy-Lamport consistent-snapshot algorithm, and its key idea is that a snapshot is not just the nodes -- it is the nodes plus the messages in flight on the channels at the cut. Record A's state at the cut (70), B's state at the cut (0), AND the message on the channel (30), and the snapshot totals 100: a real, reachable global state that conserves the money. The channel contents are a first-class part of the snapshot, not an afterthought.

The rule: to snapshot a distributed system, record each node's local state AND the messages in flight on the channels between them, because a node-only snapshot taken at inconsistent moments loses messages that had been sent but not received (undercount) or double-counts messages recorded on both ends (overcount) -- only capturing the channel state yields a consistent global cut.

On this fixture the true total is always 100. A naive snapshot that misses the channel totals 70 (loses the transfer) or 130 (double-counts it); the consistent snapshot that records the channel totals 100. This computes all three.

  --states     the balances of A, B, and the channel A->B before the send, in flight, and after the receive
  --snapshots  the naive (node-only) snapshots vs the consistent (node + channel) snapshot, with totals
  --check      the naive snapshots break conservation (lose or double-count the in-flight transfer); the consistent one conserves it

accounts and transfer are the fixture; every node state, channel state, and snapshot total is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "snapshot.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def states(accounts, transfer):
    """The three moments: before the send, message in flight, after the receive."""
    a0, b0 = accounts["A"], accounts["B"]
    amt = transfer["amount"]
    return {
        "before_send": {"A": a0, "B": b0, "channel": 0},
        "in_flight": {"A": a0 - amt, "B": b0, "channel": amt},
        "after_receive": {"A": a0 - amt, "B": b0 + amt, "channel": 0},
    }


def true_total(accounts):
    return accounts["A"] + accounts["B"]


def naive_snapshot(a_state, b_state):
    """Record A's balance and B's balance, ignore the channel entirely."""
    return {"A": a_state["A"], "B": b_state["B"], "total": a_state["A"] + b_state["B"]}


def consistent_snapshot(cut):
    """Record A, B, AND the message in flight on the channel -- a Chandy-Lamport cut."""
    return {"A": cut["A"], "B": cut["B"], "channel": cut["channel"],
            "total": cut["A"] + cut["B"] + cut["channel"]}


# ----------------------------------------------------------------- printing

def states_view(data):
    st = states(data["accounts"], data["transfer"])
    print("STATES — A, B, and the channel A->B at each moment of the transfer")
    print("-" * 60)
    print("  moment          A     B     channel A->B")
    for name in ("before_send", "in_flight", "after_receive"):
        s = st[name]
        print("  %-14s  %-4d  %-4d  %d" % (name, s["A"], s["B"], s["channel"]))
    print("-" * 60)
    print("  while in flight the 30 has left A but not reached B; it lives on the channel")


def snapshots_view(data):
    accounts, transfer = data["accounts"], data["transfer"]
    st = states(accounts, transfer)
    total = true_total(accounts)
    naive_lose = naive_snapshot(st["in_flight"], st["before_send"])
    naive_double = naive_snapshot(st["before_send"], st["after_receive"])
    consistent = consistent_snapshot(st["in_flight"])
    print("SNAPSHOTS — node-only (naive) vs node+channel (consistent), true total = %d" % total)
    print("-" * 68)
    print("  naive, record A after send + B before recv, no channel  = %d  (%+d)" % (naive_lose["total"], naive_lose["total"] - total))
    print("  naive, record A before send + B after recv, no channel  = %d  (%+d)" % (naive_double["total"], naive_double["total"] - total))
    print("  consistent, record A + B + channel (Chandy-Lamport)     = %d  (%+d)" % (consistent["total"], consistent["total"] - total))
    print("-" * 68)
    print("  the naive snapshots lose or double-count the in-flight transfer; the consistent one conserves it")


def check(data):
    print("SELF-TEST — the naive snapshots break conservation (lose or double-count the in-flight transfer); the consistent one conserves it")
    print("-" * 128)
    accounts, transfer = data["accounts"], data["transfer"]
    st = states(accounts, transfer)
    total = true_total(accounts)
    naive_lose = naive_snapshot(st["in_flight"], st["before_send"])["total"]
    naive_double = naive_snapshot(st["before_send"], st["after_receive"])["total"]
    consistent = consistent_snapshot(st["in_flight"])

    true_total_conserved = total == accounts["A"] + accounts["B"]
    print("  the real system conserves the total = %s (%d)" % (true_total_conserved, total))

    naive_loses_money = naive_lose < total
    print("  a naive snapshot LOSES the in-flight transfer = %s (%d < %d)" % (naive_loses_money, naive_lose, total))

    naive_double_counts = naive_double > total
    print("  a naive snapshot DOUBLE-COUNTS the in-flight transfer = %s (%d > %d)" % (naive_double_counts, naive_double, total))

    channel_captured = consistent["channel"] == transfer["amount"]
    print("  the consistent snapshot records the in-flight message on the channel = %s (%d)" % (channel_captured, consistent["channel"]))

    consistent_conserves = consistent["total"] == total
    print("  the consistent snapshot conserves the total = %s (%d)" % (consistent_conserves, consistent["total"]))

    ok = (true_total_conserved and naive_loses_money and naive_double_counts and channel_captured and consistent_conserves)
    print("-" * 128)
    print("SELF-TEST %s  true_total_conserved=%s  naive_loses_money=%s  naive_double_counts=%s  channel_captured=%s  consistent_conserves=%s"
          % ("PASS" if ok else "FAIL", true_total_conserved, naive_loses_money, naive_double_counts, channel_captured, consistent_conserves))
    return ok


def main():
    p = argparse.ArgumentParser(description="Consistent snapshot: to snapshot a distributed system, record each node's local state AND the messages in flight on the channels between them, because a node-only snapshot taken at inconsistent moments loses sent-but-not-received messages (undercount) or double-counts messages recorded on both ends (overcount) -- only capturing the channel state yields a consistent global cut.")
    p.add_argument("--states", action="store_true")
    p.add_argument("--snapshots", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("accounts=%s  transfer=%s  file=%s  (the balances and transfer are a fixture)"
          % (data["accounts"], "%s->%s %d" % (data["transfer"]["from"], data["transfer"]["to"], data["transfer"]["amount"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.states:
        states_view(data)
    elif args.snapshots:
        snapshots_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
