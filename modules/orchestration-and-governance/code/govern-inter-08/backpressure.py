"""Bound the queue and apply backpressure -- an unbounded buffer turns overload into a slow crash.

A producer hands work to a slower consumer through a queue. If the producer is faster than the
consumer for any sustained stretch, the queue between them grows -- and if that queue is
unbounded, it grows without limit. This does not fail loudly; it fails slowly. Memory climbs
until the process is killed, and long before that, every item waits behind an ever-longer
backlog, so latency climbs toward infinity while the system still reports itself 'up'. An
unbounded queue does not absorb overload, it hides it and converts it into a memory leak and a
latency explosion.

A bounded queue with backpressure refuses to hide it. Cap the queue; when it is full, the
excess is shed (or the producer is blocked), so the depth never exceeds the cap, latency stays
bounded, and memory is flat. You do lose the shed work -- but that work was never going to be
served anyway, because the consumer's rate is the hard ceiling on throughput; the only choice
is whether the unservable surplus is dropped now with a bounded queue or buffered forever in an
unbounded one until the process dies. Over 20 ticks of overload the unbounded queue grows to 40
and climbing while the bounded queue holds at 10 and sheds the 30 surplus, and both complete the
same 60 items the consumer could actually process. This simulates both and measures depth,
shed, and completions.

  --run        per-tick queue depth for the unbounded vs the bounded queue
  --summary    final depth, completions, and shed count for each
  --check      unbounded grows unboundedly; bounded caps depth and sheds; both complete the same

The arrival pattern, consumer rate, and cap are the fixture; every depth is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "load.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the two queues

def run_unbounded(data):
    """No cap: accept every arrival, process consumer_rate per tick. Depth grows without limit."""
    rate = data["consumer_rate"]
    depth, completed = 0, 0
    depths = []
    for a in data["arrivals"]:
        depth += a                       # accept everything -- nothing is ever refused
        served = min(depth, rate)
        depth -= served
        completed += served
        depths.append(depth)
    return {"depths": depths, "final": depth, "completed": completed, "shed": 0}


def run_bounded(data):
    """Cap the queue; shed arrivals that don't fit. Depth never exceeds the cap."""
    rate, cap = data["consumer_rate"], data["cap"]
    depth, completed, shed = 0, 0, 0
    depths = []
    for a in data["arrivals"]:
        space = cap - depth
        accepted = min(a, space)
        shed += a - accepted             # backpressure: the surplus is dropped, not buffered
        depth += accepted
        served = min(depth, rate)
        depth -= served
        completed += served
        depths.append(depth)
    return {"depths": depths, "final": depth, "completed": completed, "shed": shed}


# ----------------------------------------------------------------- printing

def run_view(data):
    u = run_unbounded(data)
    b = run_bounded(data)
    print("RUN — queue depth per tick (arrivals %s/tick, consumer %d/tick, cap %d)"
          % (data["arrivals"][0], data["consumer_rate"], data["cap"]))
    print("-" * 60)
    print("  tick  unbounded depth       bounded depth")
    for t in range(len(data["arrivals"])):
        bar_u = "#" * min(u["depths"][t], 40)
        print("  %-5d %-21s %d   |%s" % (t, "%d %s" % (u["depths"][t], bar_u[:14]), b["depths"][t],
                                          "=" * b["depths"][t]))
    print("-" * 60)
    print("  the unbounded queue climbs every tick; the bounded one holds at the cap.")


def summary_view(data):
    u = run_unbounded(data)
    b = run_bounded(data)
    total = sum(data["arrivals"])
    print("SUMMARY — after %d ticks, %d items arrived" % (len(data["arrivals"]), total))
    print("-" * 60)
    print("  unbounded: final depth %-4d completed %-4d shed %d" % (u["final"], u["completed"], u["shed"]))
    print("  bounded:   final depth %-4d completed %-4d shed %d" % (b["final"], b["completed"], b["shed"]))
    print("-" * 60)
    print("  same completions (consumer-limited); the surplus is buffered forever vs shed now.")


def check(data):
    print("SELF-TEST — unbounded grows unboundedly; bounded caps depth and sheds; completions match")
    print("-" * 60)
    u = run_unbounded(data)
    b = run_bounded(data)
    cap = data["cap"]

    # unbounded depth grows monotonically under sustained overload
    unbounded_grows = u["depths"][-1] > u["depths"][len(u["depths"]) // 2] > u["depths"][0]
    print("  the unbounded queue depth keeps growing = %s (%d -> %d -> %d)"
          % (unbounded_grows, u["depths"][0], u["depths"][len(u["depths"]) // 2], u["depths"][-1]))

    bounded_capped = max(b["depths"]) <= cap
    print("  the bounded queue never exceeds the cap = %s (max %d <= %d)"
          % (bounded_capped, max(b["depths"]), cap))

    bounded_sheds = b["shed"] > 0
    print("  the bounded queue sheds the surplus (not buffered) = %s (%d shed)" % (bounded_sheds, b["shed"]))

    same_completed = u["completed"] == b["completed"]
    print("  both complete the same work (consumer-limited) = %s (%d each)"
          % (same_completed, u["completed"]))

    ok = unbounded_grows and bounded_capped and bounded_sheds and same_completed
    print("-" * 60)
    print("SELF-TEST %s  unbounded_grows=%s  bounded_capped=%s  bounded_sheds=%s  same_completed=%s"
          % ("PASS" if ok else "FAIL", unbounded_grows, bounded_capped, bounded_sheds, same_completed))
    return ok


def main():
    p = argparse.ArgumentParser(description="Bound the queue and apply backpressure.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--summary", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("ticks=%d  consumer_rate=%d  cap=%d  file=%s  (the load pattern is a fixture)"
          % (len(data["arrivals"]), data["consumer_rate"], data["cap"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.summary:
        summary_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
