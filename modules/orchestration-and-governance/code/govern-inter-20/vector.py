"""Use a vector clock to tell concurrency from causality, or a single Lamport number invents an order.

A Lamport clock gives every event one number and guarantees a send has a smaller number than its receive. That
is enough to build a total order that never contradicts causality -- but the number throws away information. If
event A has a smaller Lamport number than event B, you cannot tell whether A actually happened-before B or
whether the two are CONCURRENT (on different processes, with no message between them) and their numbers merely
landed in that order. Two unrelated events get sequenced as if one caused the other, and any logic that reads
that order as causation -- last-writer-wins, conflict resolution -- is acting on a fiction.

A vector clock keeps the information Lamport discards: one counter PER PROCESS. Each process increments its own
counter on every event and stamps outgoing messages with the whole vector; on receipt it takes the element-wise
maximum with the message's vector, then increments its own. Now the ordering is partial and honest: A
happened-before B exactly when A's vector is <= B's element-wise (and they differ); when NEITHER vector is <=
the other, the events are concurrent, and the vector clock says so. It can distinguish 'A caused B' from 'A and
B are independent', which a single number never can.

On this fixture p1 does a local event then sends m1; p2 does its own local event (concurrent with p1's) then
receives m1. The vector clock marks e2 (send) -> e4 (recv) as causally ordered, and e2 vs e3 as CONCURRENT.
A Lamport number would give e3 a smaller value than e2 and imply e3 came first -- a false order. This computes
both.

  --clocks     the vector clock stamped on each event, step by step
  --relate     the causal relation between event pairs: before, after, or concurrent
  --check      the vector clock finds a concurrent pair that a single Lamport number would falsely order

The event log is the fixture; every vector is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "events.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def vector_clocks(procs, events):
    """Assign a vector clock to each event by the standard rules; also return each event's Lamport number."""
    idx = {p: i for i, p in enumerate(procs)}
    clock = {p: [0] * len(procs) for p in procs}
    sent, stamp, lamport = {}, {}, {}
    lam = {p: 0 for p in procs}
    for e in events:
        p = e["proc"]
        if e["kind"] == "recv":
            mv, ml = sent[e["msg"]]
            clock[p] = [max(clock[p][i], mv[i]) for i in range(len(procs))]
            lam[p] = max(lam[p], ml)
        clock[p][idx[p]] += 1                      # increment own component
        lam[p] += 1
        stamp[e["id"]] = list(clock[p])
        lamport[e["id"]] = lam[p]
        if e["kind"] == "send":
            sent[e["msg"]] = (list(clock[p]), lam[p])
    return stamp, lamport


def relation(a, b):
    """Causal relation of vectors a and b: 'before', 'after', 'equal', or 'concurrent'."""
    le = all(a[i] <= b[i] for i in range(len(a)))
    ge = all(a[i] >= b[i] for i in range(len(a)))
    if le and ge:
        return "equal"
    if le:
        return "before"
    if ge:
        return "after"
    return "concurrent"


# ----------------------------------------------------------------- printing

def clocks_view(data):
    stamp, lam = vector_clocks(data["procs"], data["events"])
    print("CLOCKS — vector clock and Lamport number per event (procs %s)" % data["procs"])
    print("-" * 58)
    for e in data["events"]:
        tag = "  msg=%s" % e["msg"] if "msg" in e else ""
        print("  %-4s %-5s %-5s  vector %s   Lamport %d%s" % (e["id"], e["proc"], e["kind"], stamp[e["id"]], lam[e["id"]], tag))
    print("-" * 58)
    print("  the receive takes the element-wise max, then bumps its own counter.")


def relate_view(data):
    stamp, lam = vector_clocks(data["procs"], data["events"])
    pairs = [("e2", "e4"), ("e2", "e3"), ("e1", "e3")]
    print("RELATE — causal relation of event pairs (vector) vs their Lamport numbers")
    print("-" * 64)
    for a, b in pairs:
        rel = relation(stamp[a], stamp[b])
        print("  %s %s vs %s %s -> %-10s  (Lamport %d vs %d)" % (a, stamp[a], b, stamp[b], rel, lam[a], lam[b]))
    print("-" * 64)
    print("  concurrent pairs have incomparable vectors but still differ in Lamport.")


def check(data):
    print("SELF-TEST — the vector clock finds a concurrent pair that a single Lamport number would falsely order")
    print("-" * 104)
    stamp, lam = vector_clocks(data["procs"], data["events"])

    send_before_recv = relation(stamp["e2"], stamp["e4"]) == "before"
    print("  the send causally precedes its receive = %s (e2 %s before e4 %s)" % (send_before_recv, stamp["e2"], stamp["e4"]))

    concurrent_pair = relation(stamp["e2"], stamp["e3"]) == "concurrent"
    print("  e2 and e3 are concurrent = %s (%s vs %s, neither <= the other)" % (concurrent_pair, stamp["e2"], stamp["e3"]))

    lamport_would_order_them = lam["e2"] != lam["e3"]
    print("  a single Lamport number would order that concurrent pair = %s (e3 %d < e2 %d implies e3 first)" % (lamport_would_order_them, lam["e3"], lam["e2"]))

    receive_took_max = stamp["e4"] == [max(stamp["e2"][0], stamp["e3"][0]), stamp["e3"][1] + 1]
    print("  the receive vector is the element-wise max plus own increment = %s (%s)" % (receive_took_max, stamp["e4"]))

    another_concurrent = relation(stamp["e1"], stamp["e3"]) == "concurrent"
    print("  e1 and e3 are also concurrent = %s" % another_concurrent)

    ok = send_before_recv and concurrent_pair and lamport_would_order_them and receive_took_max and another_concurrent
    print("-" * 104)
    print("SELF-TEST %s  send_before_recv=%s  concurrent_pair=%s  lamport_would_order_them=%s  receive_took_max=%s  another_concurrent=%s"
          % ("PASS" if ok else "FAIL", send_before_recv, concurrent_pair, lamport_would_order_them, receive_took_max, another_concurrent))
    return ok


def main():
    p = argparse.ArgumentParser(description="Use a vector clock to distinguish concurrent events from causally ordered ones.")
    p.add_argument("--clocks", action="store_true")
    p.add_argument("--relate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("procs=%d  events=%d  file=%s  (the event log is a fixture)" % (len(data["procs"]), len(data["events"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.clocks:
        clocks_view(data)
    elif args.relate:
        relate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
