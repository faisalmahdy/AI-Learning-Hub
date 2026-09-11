"""Hedge the slow requests -- send a duplicate to another replica after a short delay and take the first reply, so one slow replica cannot own your tail latency.

In a replicated service, average latency is easy and tail latency is hard. Most requests are fast, but a few land on a replica that is briefly slow -- a garbage-collection pause, a hot cache miss, a noisy neighbor -- and those few define the p99 and p99.9 that users actually feel. You cannot prevent a replica from occasionally being slow; there are too many transient causes. So the question is not how to make every replica always fast, but how to stop one occasionally-slow replica from making a request slow, when other replicas are available and fast.

Hedged requests answer it directly. Send the request to one replica as usual, but if it has not answered within a short delay -- chosen around the normal p95, well below the tail -- send a SECOND copy to a different replica and take whichever response comes back first. The insight is that a replica being slow right now is mostly independent of another replica being slow right now, so the probability that BOTH the original and the hedge are slow is much smaller than the probability that one is. A request that would have waited 200ms on an unlucky replica instead waits only until a healthy replica answers the duplicate, capping its latency near the hedge delay plus a normal response time.

The cost is controlled precisely by the delay. Because the hedge fires only for requests still outstanding at the delay, and the delay sits above the normal latency, the fast majority finish before the hedge is ever sent -- so hedging adds duplicate work only for the slow tail, a small fraction of traffic, not for every request. Set the delay too low and you double your load chasing latency you did not need to; set it around the p95 and you spend a few percent extra requests to cut the tail dramatically. Hedging trades a little extra capacity for a lot less tail latency, and the trade is tunable with one number.

The rule: hedge slow requests -- after a delay set near the normal p95, send a duplicate to another replica and take the first response -- rather than waiting on a single replica, because tail latency is dominated by the occasional slow replica and a second replica is usually fast, so the duplicate caps the tail near the hedge delay while firing only for the slow minority, adding little extra load.

On this fixture four requests are fast (10-13ms) and one hit a slow replica (200ms). Without hedging the tail is 200ms. With a 20ms hedge delay to a 15ms replica, the slow request drops to min(200, 35)=35ms and the four fast ones finish before the hedge fires, so only one extra request is sent. This computes both.

  --latency   each request's original latency, whether a hedge fires, and its effective latency
  --tail      the tail (max) latency without vs with hedging, and how many extra requests hedging sent
  --check     one slow replica dominates the tail; hedging caps it while firing only for the slow request

latencies_ms, hedge_delay_ms, and fallback_ms are the fixture; every effective latency, the tail, and the extra-request count are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "hedged.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def hedge_fires(orig, delay):
    """A hedge is sent only if the request is still outstanding at the hedge delay."""
    return orig > delay


def effective_latency(orig, delay, fallback):
    """With hedging: if the hedge fires, the effective latency is min(original, delay + fallback)."""
    if hedge_fires(orig, delay):
        return min(orig, delay + fallback)
    return orig


def tail(latencies):
    return max(latencies)


def median(latencies):
    s = sorted(latencies)
    return s[len(s) // 2]


# ----------------------------------------------------------------- printing

def latency_view(data):
    lat, delay, fb = data["latencies_ms"], data["hedge_delay_ms"], data["fallback_ms"]
    print("LATENCY — original vs effective latency with hedging (delay %dms, fallback %dms)" % (delay, fb))
    print("-" * 68)
    print("  req  original   hedge fires?   effective")
    for i, o in enumerate(lat):
        print("  %-3d  %-9d  %-13s  %d" % (i, o, hedge_fires(o, delay), effective_latency(o, delay, fb)))
    print("-" * 68)
    print("  the hedge fires only for requests slower than the %dms delay" % delay)


def tail_view(data):
    lat, delay, fb = data["latencies_ms"], data["hedge_delay_ms"], data["fallback_ms"]
    hedged = [effective_latency(o, delay, fb) for o in lat]
    extra = sum(1 for o in lat if hedge_fires(o, delay))
    print("TAIL — tail latency without vs with hedging")
    print("-" * 60)
    print("  median latency        = %dms" % median(lat))
    print("  tail (max) no hedge   = %dms" % tail(lat))
    print("  tail (max) hedged     = %dms" % tail(hedged))
    print("-" * 60)
    print("  extra requests sent by hedging = %d of %d (only the slow tail)" % (extra, len(lat)))


def check(data):
    print("SELF-TEST — one slow replica dominates the tail; hedging caps it while firing only for the slow request")
    print("-" * 116)
    lat, delay, fb = data["latencies_ms"], data["hedge_delay_ms"], data["fallback_ms"]
    hedged = [effective_latency(o, delay, fb) for o in lat]
    extra = sum(1 for o in lat if hedge_fires(o, delay))

    has_tail = tail(lat) > 5 * median(lat)
    print("  one request has a tail latency far above the median = %s (%dms vs median %dms)" % (has_tail, tail(lat), median(lat)))

    delay_above_typical = delay > median(lat)
    print("  the hedge delay sits above the typical latency = %s (%dms > %dms)" % (delay_above_typical, delay, median(lat)))

    hedging_caps_tail = tail(hedged) < tail(lat)
    print("  hedging caps the tail latency = %s (%dms < %dms)" % (hedging_caps_tail, tail(hedged), tail(lat)))

    fast_unaffected = all(effective_latency(o, delay, fb) == o for o in lat if not hedge_fires(o, delay))
    print("  requests faster than the delay are unchanged (no hedge sent) = %s" % fast_unaffected)

    extra_bounded = extra < len(lat) and extra == sum(1 for o in lat if o > delay)
    print("  hedging sends extra requests only for the slow tail = %s (%d of %d)" % (extra_bounded, extra, len(lat)))

    tail_capped_near_delay = tail(hedged) <= delay + fb
    print("  the hedged tail is capped near delay + fallback = %s (%dms <= %dms)" % (tail_capped_near_delay, tail(hedged), delay + fb))

    ok = has_tail and delay_above_typical and hedging_caps_tail and fast_unaffected and extra_bounded and tail_capped_near_delay
    print("-" * 116)
    print("SELF-TEST %s  has_tail=%s  delay_above_typical=%s  hedging_caps_tail=%s  fast_unaffected=%s  extra_bounded=%s  tail_capped_near_delay=%s"
          % ("PASS" if ok else "FAIL", has_tail, delay_above_typical, hedging_caps_tail, fast_unaffected, extra_bounded, tail_capped_near_delay))
    return ok


def main():
    p = argparse.ArgumentParser(description="Hedged requests: hedge slow requests -- after a delay set near the normal p95, send a duplicate to another replica and take the first response -- rather than waiting on a single replica, because tail latency is dominated by the occasional slow replica and a second replica is usually fast, so the duplicate caps the tail near the hedge delay while firing only for the slow minority, adding little extra load.")
    p.add_argument("--latency", action="store_true")
    p.add_argument("--tail", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("requests=%d  hedge_delay_ms=%d  fallback_ms=%d  file=%s  (the latencies and hedge parameters are a fixture)"
          % (len(data["latencies_ms"]), data["hedge_delay_ms"], data["fallback_ms"], DATA.name))
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
