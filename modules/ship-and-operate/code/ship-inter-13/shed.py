"""Shed load when the queue is full, or an overloaded server wastes all its capacity on doomed requests.

When arrivals exceed what a server can process, the naive server accepts everything and queues it. The
queue grows without bound, so each new request waits behind a longer and longer backlog. Past a point
every request waits longer than its deadline -- by the time the server gets to it, the client has already
timed out and discarded the answer. The server is at 100% utilization and its useful output is near zero:
it spends every cycle computing replies no one will read. This is congestion collapse. Accepting a request
you cannot serve in time is worse than rejecting it, because it costs a slot that a servable request could
have used.

Load shedding fixes it. Cap the queue; when it is full, reject new arrivals immediately with a fast error
instead of enqueuing them. A rejected client fails fast and can retry elsewhere or degrade gracefully. The
requests that ARE admitted wait behind a bounded queue, so their wait is bounded too -- if the cap is no
larger than the deadline allows, every admitted request is served in time. The server converts a flood
into a steady stream it can actually satisfy: fewer requests accepted, but the accepted ones succeed, so
useful throughput (goodput) stays near capacity instead of collapsing to zero.

On this fixture 18 requests arrive in a burst against a server that clears one per tick with a 3-tick
deadline. The accept-everything server serves only 4 within their deadline and burns the rest of its
capacity on 14 requests that are already too late -- goodput 4. Shedding at a queue cap of 3 rejects 10
fast and serves 8, every one within deadline -- goodput 8, double. This computes both.

  --run        walk the queue tick by tick for each policy, showing waits and which requests make it
  --goodput    requests served in time, served too late (wasted), and rejected, for each policy
  --check      accept-everything wastes capacity on late requests; shedding lifts goodput and wastes none

The arrivals, capacity, deadline, and cap are the fixture; every wait is computed. Stdlib only.
"""
import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "load.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def simulate(arrivals, capacity, deadline, queue_cap):
    """Serve capacity requests per tick FIFO; with queue_cap set, reject arrivals when the queue is full."""
    records = {i: {"id": i, "arrival": a, "served": None, "waited": None, "good": False, "rejected": False}
               for i, a in enumerate(arrivals)}
    by_tick = defaultdict(list)
    for i, a in enumerate(arrivals):
        by_tick[a].append(i)

    q = deque()
    horizon = max(arrivals) + len(arrivals) + deadline + 2
    for t in range(horizon):
        for _ in range(capacity):                 # serve from the front of the queue
            if q:
                rid = q.popleft()
                r = records[rid]
                r["served"], r["waited"] = t, t - r["arrival"]
                r["good"] = r["waited"] <= deadline
        for rid in by_tick.get(t, []):            # admit this tick's arrivals, or shed if full
            if queue_cap is not None and len(q) >= queue_cap:
                records[rid]["rejected"] = True
            else:
                q.append(rid)
    return records


def tally(records):
    good = sum(1 for r in records.values() if r["good"])
    late = sum(1 for r in records.values() if r["served"] is not None and not r["good"])
    rejected = sum(1 for r in records.values() if r["rejected"])
    return good, late, rejected


# ----------------------------------------------------------------- printing

def run_view(data):
    arr, cap, dl, qc = data["arrivals"], data["capacity"], data["deadline"], data["queue_cap"]
    for name, cap_arg in (("ACCEPT-EVERYTHING (unbounded queue)", None),
                          ("SHED at queue cap %d" % qc, qc)):
        recs = simulate(arr, cap, dl, cap_arg)
        print("%s   (%d arrivals, %d/tick, deadline %d)" % (name, len(arr), cap, dl))
        print("-" * 62)
        for r in sorted(recs.values(), key=lambda x: x["id"]):
            if r["rejected"]:
                print("  req %2d  arr %d  REJECTED (queue full)" % (r["id"], r["arrival"]))
            else:
                mark = "in time" if r["good"] else "TOO LATE (wasted)"
                print("  req %2d  arr %d  served %2d  waited %d  %s"
                      % (r["id"], r["arrival"], r["served"], r["waited"], mark))
        g, l, rj = tally(recs)
        print("  goodput %d   late %d   rejected %d" % (g, l, rj))
        print("")


def goodput_view(data):
    arr, cap, dl, qc = data["arrivals"], data["capacity"], data["deadline"], data["queue_cap"]
    print("GOODPUT — requests served in time vs capacity wasted on late ones")
    print("-" * 62)
    print("  policy               goodput   late(wasted)   rejected")
    for name, cap_arg in (("accept-everything", None), ("shed cap %d" % qc, qc)):
        g, l, rj = tally(simulate(arr, cap, dl, cap_arg))
        print("  %-18s   %5d   %10d   %8d" % (name, g, l, rj))
    print("-" * 62)
    print("  shedding trades rejections for goodput; late work is pure waste.")


def check(data):
    print("SELF-TEST — accept-everything wastes capacity on late requests; shedding lifts goodput and wastes none")
    print("-" * 98)
    arr, cap, dl, qc = data["arrivals"], data["capacity"], data["deadline"], data["queue_cap"]
    g_open, l_open, rj_open = tally(simulate(arr, cap, dl, None))
    g_shed, l_shed, rj_shed = tally(simulate(arr, cap, dl, qc))

    open_wastes = l_open > 0
    print("  accept-everything serves requests too late to matter = %s (%d wasted)" % (open_wastes, l_open))

    shed_no_waste = l_shed == 0
    print("  shedding never serves a request too late = %s (%d wasted)" % (shed_no_waste, l_shed))

    shed_lifts_goodput = g_shed > g_open
    print("  shedding's goodput beats accept-everything's = %s (%d vs %d)" % (shed_lifts_goodput, g_shed, g_open))

    open_rejects_none = rj_open == 0 and rj_shed > 0
    print("  accept-everything rejects nothing; shedding fails fast = %s (%d rejected)" % (open_rejects_none, rj_shed))

    ok = open_wastes and shed_no_waste and shed_lifts_goodput and open_rejects_none
    print("-" * 98)
    print("SELF-TEST %s  open_wastes=%s  shed_no_waste=%s  shed_lifts_goodput=%s  open_rejects_none=%s"
          % ("PASS" if ok else "FAIL", open_wastes, shed_no_waste, shed_lifts_goodput, open_rejects_none))
    return ok


def main():
    p = argparse.ArgumentParser(description="Shed load when the queue is full to protect goodput under overload.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--goodput", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("arrivals=%d  capacity=%d/tick  deadline=%d  queue_cap=%d  file=%s  (the load is a fixture)"
          % (len(data["arrivals"]), data["capacity"], data["deadline"], data["queue_cap"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.goodput:
        goodput_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
