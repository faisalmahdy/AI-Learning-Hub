"""Send a backup request after a short delay, or one slow replica sets your whole tail latency.

A request goes to one replica and waits for it. Most replicas are fast, but at any moment a few are slow --
a garbage-collection pause, a busy disk, a noisy neighbor. When your request lands on one of those, it waits
the full straggler time, and there is nothing wrong with the request or the data; you just got unlucky with
the replica. Across many requests, these unlucky ones set the tail: the 99th-percentile latency is dominated
by the slowest replica each request happened to hit, not by the typical one. You cannot fix this by making
the median faster, because the tail is about the worst replica, not the average one.

Hedged (backup) requests attack the tail directly. Wait a short delay -- long enough that a normal request
has usually already answered -- and if the primary has not returned, send the SAME request to a second
replica and take whichever answers first. A straggler is rescued: instead of waiting 200ms for the slow
replica, you wait the short delay plus a normal replica's time. The cost is a few extra requests -- only the
ones that crossed the delay, a small fraction -- so you buy a dramatically lower tail for a small increase in
load. Set the delay near the 95th percentile and only about 5% of requests ever hedge.

On this fixture nine requests take ~12ms and one straggler takes 200ms; the hedge delay is 20ms. Without
hedging the tail is 200ms. With hedging the straggler is rescued to 35ms (20ms delay + 15ms backup), the tail
drops to 35ms, and exactly one extra request was sent. This computes both.

  --latency   each request's completion time without hedging vs with hedging
  --tail      the tail (max) latency each way, and how many extra requests hedging sent
  --check     hedging rescues the straggler and cuts the tail for only a few extra requests

The latencies and hedge delay are the fixture; every completion time is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "requests.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def no_hedge(primary):
    """Completion time with one replica: just the primary's latency."""
    return primary


def hedged(primary, backup, delay):
    """If the primary answers before the delay, use it; else race it against a backup sent at the delay."""
    if primary <= delay:
        return primary                      # primary already back before we would hedge
    return min(primary, delay + backup)     # backup sent at `delay`, take whichever is first


def hedge_fired(primary, delay):
    return primary > delay


# ----------------------------------------------------------------- printing

def latency_view(data):
    pr, bk, d = data["primary_ms"], data["backup_ms"], data["hedge_delay_ms"]
    print("LATENCY — completion per request, no hedge vs hedge (delay %dms)" % d)
    print("-" * 60)
    print("  req   primary   no-hedge   hedged   note")
    for i in range(len(pr)):
        h = hedged(pr[i], bk[i], d)
        note = "hedged (backup raced)" if hedge_fired(pr[i], d) else ""
        print("  %2d    %5dms   %5dms   %5dms   %s" % (i, pr[i], no_hedge(pr[i]), h, note))
    print("-" * 60)
    print("  only the straggler crosses the delay and gets a backup.")


def tail_view(data):
    pr, bk, d = data["primary_ms"], data["backup_ms"], data["hedge_delay_ms"]
    nh = [no_hedge(p) for p in pr]
    hg = [hedged(pr[i], bk[i], d) for i in range(len(pr))]
    extra = sum(1 for p in pr if hedge_fired(p, d))
    print("TAIL — worst-case latency and extra request cost")
    print("-" * 60)
    print("  tail (max) latency:  no-hedge %dms   hedged %dms" % (max(nh), max(hg)))
    print("  extra requests sent: %d of %d (%.0f%%)" % (extra, len(pr), 100 * extra / len(pr)))
    print("-" * 60)
    print("  a %dx tail reduction for %.0f%% more requests." % (max(nh) // max(hg), 100 * extra / len(pr)))


def check(data):
    print("SELF-TEST — hedging rescues the straggler and cuts the tail for only a few extra requests")
    print("-" * 100)
    pr, bk, d = data["primary_ms"], data["backup_ms"], data["hedge_delay_ms"]
    nh = [no_hedge(p) for p in pr]
    hg = [hedged(pr[i], bk[i], d) for i in range(len(pr))]
    extra = sum(1 for p in pr if hedge_fired(p, d))
    s = pr.index(max(pr))                     # the straggler

    hedge_cuts_tail = max(hg) < max(nh)
    print("  hedging lowers the tail latency = %s (%dms -> %dms)" % (hedge_cuts_tail, max(nh), max(hg)))

    straggler_rescued = hg[s] < pr[s]
    print("  the straggler is rescued = %s (req %d: %dms -> %dms)" % (straggler_rescued, s, pr[s], hg[s]))

    few_extra_requests = extra < len(pr) / 2
    print("  only a small fraction hedged = %s (%d of %d)" % (few_extra_requests, extra, len(pr)))

    fast_requests_no_hedge = all(not hedge_fired(p, d) for p in pr if p <= d)
    print("  requests answered before the delay sent no backup = %s" % fast_requests_no_hedge)

    hedge_is_min = hg[s] == min(pr[s], d + bk[s])
    print("  the hedged time is min(primary, delay+backup) = %s (min(%d, %d+%d)=%d)" % (hedge_is_min, pr[s], d, bk[s], hg[s]))

    ok = hedge_cuts_tail and straggler_rescued and few_extra_requests and fast_requests_no_hedge and hedge_is_min
    print("-" * 100)
    print("SELF-TEST %s  hedge_cuts_tail=%s  straggler_rescued=%s  few_extra_requests=%s  fast_requests_no_hedge=%s  hedge_is_min=%s"
          % ("PASS" if ok else "FAIL", hedge_cuts_tail, straggler_rescued, few_extra_requests, fast_requests_no_hedge, hedge_is_min))
    return ok


def main():
    p = argparse.ArgumentParser(description="Hedge a slow request with a backup replica to cut tail latency.")
    p.add_argument("--latency", action="store_true")
    p.add_argument("--tail", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("requests=%d  hedge_delay=%dms  file=%s  (the latencies are a fixture)"
          % (len(data["primary_ms"]), data["hedge_delay_ms"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.latency:
        latency_view(data)
    elif args.tail:
        tail_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
