"""Order events by a logical clock, or a skewed wall clock puts a message's receipt before its send.

Across machines, wall clocks disagree. Each is set from its own source and drifts, so two clocks can be
seconds -- or more -- apart. That is fine until you use timestamps to ORDER events from different machines.
If the receiver's clock runs behind the sender's, a message can be stamped as RECEIVED at 95 when it was SENT
at 101: sort by wall clock and the receive comes before the send, which is causally impossible -- an effect
before its cause. Any logic that trusts that order (who wrote last, what happened first, which update wins)
is now built on a lie the clocks told, and no amount of "sync the clocks better" removes the risk, because
clocks can always skew between syncs.

A Lamport logical clock fixes the ordering without trusting wall time. Each process keeps a counter. It
increments the counter on every event, and stamps outgoing messages with the counter's value. On receiving a
message, it sets its counter to max(its own, the message's) + 1. This guarantees the one thing that matters:
a send always has a smaller Lamport timestamp than its receive, so the causal order (send before receive) is
never violated. Logical clocks do not tell you what time it was; they tell you what came before what, which is
what ordering actually needs.

On this fixture p2's clock runs behind p1's. Sorting the five events by wall clock puts the receipt of m1
(wall 95) before its send (wall 101) -- a causality violation. Sorting by Lamport timestamp gives send m1 (2)
before receive m1 (3), the correct causal order. This computes both.

  --wall       the events ordered by wall clock, flagging any receive that precedes its send
  --lamport    the Lamport timestamp of each event, and the causal order it yields
  --check      wall-clock order violates causality; the Lamport order puts every send before its receive

The event log is the fixture; every timestamp is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "events.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def lamport_stamps(events):
    """Assign a Lamport timestamp to each event, processing the log in causal order."""
    counter = {}                       # per-process counter
    sent = {}                          # msg -> lamport ts of its send
    stamp = {}                         # event id -> lamport ts
    for e in events:
        p = e["proc"]
        if e["kind"] == "recv":
            counter[p] = max(counter.get(p, 0), sent[e["msg"]]) + 1
        else:
            counter[p] = counter.get(p, 0) + 1
        stamp[e["id"]] = counter[p]
        if e["kind"] == "send":
            sent[e["msg"]] = counter[p]
    return stamp


def pairs(events):
    """(send event, recv event) for each message."""
    by_msg = {}
    for e in events:
        if e["kind"] in ("send", "recv"):
            by_msg.setdefault(e["msg"], {})[e["kind"]] = e
    return [(v["send"], v["recv"]) for v in by_msg.values() if "send" in v and "recv" in v]


# ----------------------------------------------------------------- printing

def wall_view(data):
    events = data["events"]
    print("WALL — events ordered by wall clock")
    print("-" * 58)
    for e in sorted(events, key=lambda e: e["wall"]):
        tag = "  msg=%s" % e["msg"] if "msg" in e else ""
        print("  wall %3d  %-4s %-5s %s%s" % (e["wall"], e["id"], e["proc"], e["kind"], tag))
    print("-" * 58)
    for s, r in pairs(events):
        if r["wall"] < s["wall"]:
            print("  VIOLATION: %s received (wall %d) before it was sent (wall %d)" % (s["msg"], r["wall"], s["wall"]))
    print("  a clock behind on the receiver makes a receive look earlier than its send.")


def lamport_view(data):
    events = data["events"]
    stamp = lamport_stamps(events)
    print("LAMPORT — logical timestamp per event, then the causal order")
    print("-" * 58)
    for e in sorted(events, key=lambda e: stamp[e["id"]]):
        tag = "  msg=%s" % e["msg"] if "msg" in e else ""
        print("  L%-2d  %-4s %-5s %-5s%s" % (stamp[e["id"]], e["id"], e["proc"], e["kind"], tag))
    print("-" * 58)
    print("  every send has a smaller Lamport stamp than its receive.")


def check(data):
    print("SELF-TEST — wall-clock order violates causality; the Lamport order puts every send before its receive")
    print("-" * 104)
    events = data["events"]
    stamp = lamport_stamps(events)
    ps = pairs(events)

    wall_violates = any(r["wall"] < s["wall"] for s, r in ps)
    print("  some message is received (by wall clock) before it was sent = %s" % wall_violates)
    for s, r in ps:
        if r["wall"] < s["wall"]:
            print("    %s: send wall %d, recv wall %d" % (s["msg"], s["wall"], r["wall"]))

    lamport_respects = all(stamp[s["id"]] < stamp[r["id"]] for s, r in ps)
    print("  every send has a smaller Lamport stamp than its receive = %s" % lamport_respects)
    for s, r in ps:
        print("    %s: send L%d < recv L%d = %s" % (s["msg"], stamp[s["id"]], stamp[r["id"]], stamp[s["id"]] < stamp[r["id"]]))

    wall_order = [e["id"] for e in sorted(events, key=lambda e: e["wall"])]
    lamport_order = [e["id"] for e in sorted(events, key=lambda e: stamp[e["id"]])]
    causal_order = [e["id"] for e in events]

    wall_reorders = wall_order != causal_order
    print("  wall-clock order differs from the true causal order = %s (%s)" % (wall_reorders, wall_order))

    lamport_matches_causal = lamport_order == causal_order
    print("  Lamport order matches the true causal order = %s (%s)" % (lamport_matches_causal, lamport_order))

    stamps_strictly_increase = all(stamp[events[i]["id"]] < stamp[events[i + 1]["id"]] for i in range(len(events) - 1))
    print("  Lamport stamps strictly increase along the causal log = %s" % stamps_strictly_increase)

    ok = wall_violates and lamport_respects and wall_reorders and lamport_matches_causal and stamps_strictly_increase
    print("-" * 104)
    print("SELF-TEST %s  wall_violates=%s  lamport_respects=%s  wall_reorders=%s  lamport_matches_causal=%s  stamps_strictly_increase=%s"
          % ("PASS" if ok else "FAIL", wall_violates, lamport_respects, wall_reorders, lamport_matches_causal, stamps_strictly_increase))
    return ok


def main():
    p = argparse.ArgumentParser(description="Order distributed events by a Lamport logical clock, not a skewed wall clock.")
    p.add_argument("--wall", action="store_true")
    p.add_argument("--lamport", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("events=%d  file=%s  (the event log is a fixture)" % (len(data["events"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.wall:
        wall_view(data)
    elif args.lamport:
        lamport_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
