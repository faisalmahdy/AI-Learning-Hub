"""Order distributed events by Lamport logical clocks, not wall-clock time -- a skewed clock makes a reply look older than the message it answers.

When events happen on different machines and you need a single order for them -- to replay a log, to break a tie, to decide which write is "later" -- the obvious key is the wall-clock timestamp each machine stamped on its event. It is the obvious key and it is wrong, because the machines' clocks are not identical. Physical clocks drift; even with NTP they disagree by milliseconds, and a laggy or misconfigured one can be off by seconds. So an event that genuinely happened LATER, on a machine whose clock runs behind, carries a LOWER timestamp than an earlier event on a faster machine. Sort by wall-clock and you can place a message's receipt -- or a reply to it -- BEFORE the message was ever sent. Causality inverted, from nothing but two clocks that do not agree.

The fix does not try to synchronize the physical clocks; it stops using them for ordering. A LAMPORT logical clock is a per-node counter with two rules: increment it on every local event, and on receiving a message, first advance the counter to max(its own value, the timestamp carried on the message) + 1. The receive rule is the whole trick: a message's stamp is a lower bound the receiver must exceed, so a received event always gets a stamp strictly greater than the send it depends on -- regardless of what the two wall clocks say. Because of that, if event a happened-before event b (a is a's send and b is its receive, or they are consecutive on one node), then Lamport(a) < Lamport(b). Sorting by the Lamport stamp therefore never places an effect before its cause.

Lamport clocks give a TOTAL order (break ties by node id) that is CONSISTENT WITH causality -- it never contradicts a happens-before relationship. It does not tell you that two unrelated events are truly concurrent (that needs vector clocks), and it does not measure real elapsed time. What it guarantees is exactly what wall-clock ordering fails to guarantee: causes come before effects.

The rule: order distributed events by Lamport logical clocks -- a per-node counter incremented on each event and advanced to max(local, received stamp) + 1 on every receive -- not by wall-clock timestamps, because clock skew lets an event on a slow clock carry a lower timestamp than an earlier event on a fast clock, placing effects before their causes, whereas the Lamport receive rule forces every received event's stamp above the send it depends on.

On this fixture A sends m1 (wall 100), B -- whose clock runs behind -- receives it (wall 95) and replies with m2 (wall 96), and A receives the reply (wall 103). The true order is e1 -> e2 -> e3 -> e4. Sorting by wall-clock puts e2 and e3 (95, 96) before e1 (100), placing B's receipt of m1 before A ever sent it: one causality violation. Lamport stamps come out 1,2,3,4 and reproduce the causal order exactly. This computes both.

  --order    each event's wall-clock reading and computed Lamport stamp, and the two orderings side by side
  --causal   the causality-violation count for each ordering: how many messages are received before they are sent
  --check    wall-clock ordering violates causality under the skew; Lamport ordering reproduces the causal order with zero violations

events and causal_order are the fixture; every Lamport stamp, ordering, and violation count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "lamport.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def lamport_stamps(events):
    """Per-node counter: +1 on every event, and on receive advance to max(local, message stamp) + 1."""
    clocks = {}
    sent = {}
    stamps = {}
    for e in events:
        node = e["node"]
        clocks.setdefault(node, 0)
        if e["op"] == "send":
            clocks[node] += 1
            sent[e["msg"]] = clocks[node]
        else:
            clocks[node] = max(clocks[node], sent[e["msg"]]) + 1
        stamps[e["id"]] = clocks[node]
    return stamps


def order_by_wall(events):
    """Total order by wall-clock reading, breaking ties by node then id."""
    return [e["id"] for e in sorted(events, key=lambda e: (e["wall"], e["node"], e["id"]))]


def order_by_lamport(events, stamps):
    """Total order by Lamport stamp, breaking ties by node then id."""
    return [e["id"] for e in sorted(events, key=lambda e: (stamps[e["id"]], e["node"], e["id"]))]


def causality_violations(events, order):
    """Count messages whose recv is placed before its send in this ordering -- an effect before its cause."""
    pos = {eid: i for i, eid in enumerate(order)}
    send_at = {e["msg"]: e["id"] for e in events if e["op"] == "send"}
    recv_at = {e["msg"]: e["id"] for e in events if e["op"] == "recv"}
    violations = []
    for msg in send_at:
        if msg in recv_at and pos[recv_at[msg]] < pos[send_at[msg]]:
            violations.append(msg)
    return violations


# ----------------------------------------------------------------- printing

def order_view(data):
    events = data["events"]
    stamps = lamport_stamps(events)
    print("ORDER — each event's wall-clock reading and computed Lamport stamp")
    print("-" * 64)
    print("  event  node  op    msg   wall-clock   Lamport")
    for e in events:
        print("  %-5s  %-4s  %-4s  %-4s  %-11d  %d" % (e["id"], e["node"], e["op"], e["msg"], e["wall"], stamps[e["id"]]))
    print("-" * 64)
    print("  order by wall-clock: %s" % " ".join(order_by_wall(events)))
    print("  order by Lamport:    %s" % " ".join(order_by_lamport(events, stamps)))
    print("  true causal order:   %s" % " ".join(data["causal_order"]))


def causal_view(data):
    events = data["events"]
    stamps = lamport_stamps(events)
    wall = order_by_wall(events)
    lam = order_by_lamport(events, stamps)
    print("CAUSAL — messages received before they are sent, per ordering")
    print("-" * 62)
    wv = causality_violations(events, wall)
    lv = causality_violations(events, lam)
    print("  wall-clock order %s -> %d violation(s): %s" % (wall, len(wv), wv or "none"))
    print("  Lamport order    %s -> %d violation(s): %s" % (lam, len(lv), lv or "none"))
    print("-" * 62)
    if wv:
        msg = wv[0]
        send = next(e["id"] for e in events if e["op"] == "send" and e["msg"] == msg)
        recv = next(e["id"] for e in events if e["op"] == "recv" and e["msg"] == msg)
        print("  under wall-clock, %s (recv %s) is ordered before %s (send %s) -- a reply before its cause"
              % (recv, msg, send, msg))


def check(data):
    print("SELF-TEST — wall-clock ordering violates causality under the skew; Lamport ordering reproduces the causal order with zero violations")
    print("-" * 130)
    events = data["events"]
    causal = data["causal_order"]
    stamps = lamport_stamps(events)
    wall = order_by_wall(events)
    lam = order_by_lamport(events, stamps)

    wall_of = {e["id"]: e["wall"] for e in events}
    clock_skew_present = min(e["wall"] for e in events if e["node"] == "B") < max(e["wall"] for e in events if e["node"] == "A")
    print("  a slow clock exists (a B event reads lower than an A event) = %s" % clock_skew_present)

    wall_violations = causality_violations(events, wall)
    wallclock_violates_causality = len(wall_violations) > 0
    print("  wall-clock ordering places a receive before its send = %s (%d violation: %s)"
          % (wallclock_violates_causality, len(wall_violations), wall_violations))

    lamport_violations = causality_violations(events, lam)
    lamport_respects_causality = len(lamport_violations) == 0
    print("  Lamport ordering has zero causality violations = %s (%s)" % (lamport_respects_causality, lamport_violations or "none"))

    lamport_matches_causal = lam == causal
    print("  Lamport order reproduces the true causal order = %s (%s)" % (lamport_matches_causal, " ".join(lam)))

    stamps_strictly_increase = all(stamps[causal[i]] < stamps[causal[i + 1]] for i in range(len(causal) - 1))
    print("  Lamport stamp strictly increases along the causal chain = %s (%s)"
          % (stamps_strictly_increase, " < ".join(str(stamps[e]) for e in causal)))

    ok = clock_skew_present and wallclock_violates_causality and lamport_respects_causality and lamport_matches_causal and stamps_strictly_increase
    print("-" * 130)
    print("SELF-TEST %s  clock_skew_present=%s  wallclock_violates_causality=%s  lamport_respects_causality=%s  lamport_matches_causal=%s  stamps_strictly_increase=%s"
          % ("PASS" if ok else "FAIL", clock_skew_present, wallclock_violates_causality, lamport_respects_causality, lamport_matches_causal, stamps_strictly_increase))
    return ok


def main():
    p = argparse.ArgumentParser(description="Lamport logical clocks: order distributed events by a per-node counter incremented on each event and advanced to max(local, received stamp) + 1 on every receive, not by wall-clock timestamps, because clock skew lets an event on a slow clock carry a lower timestamp than an earlier event on a fast clock, placing effects before their causes, whereas the Lamport receive rule forces every received event's stamp above the send it depends on.")
    p.add_argument("--order", action="store_true")
    p.add_argument("--causal", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("events=%d  nodes=%s  file=%s  (the events and their causal order are a fixture)"
          % (len(data["events"]), sorted({e["node"] for e in data["events"]}), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.order:
        order_view(data)
    elif args.causal:
        causal_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
