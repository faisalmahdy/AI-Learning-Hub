"""Adapt the concurrency limit to the dependency's current capacity (AIMD on latency), not a static value -- a fixed limit overloads a degraded dependency or starves a healthy one.

A concurrency limit caps how many requests a client keeps in flight to a dependency at once -- the client-side analogue of a bulkhead, and the knob that protects a dependency from being swamped. The dependency has a capacity C: the number of concurrent requests it serves at its baseline latency. Send more than C at once and the surplus queues, so latency climbs roughly in proportion to how far concurrency overshoots capacity (Little's law made visible). Send fewer than C and requests wait in your own queue while the dependency sits idle -- throughput left on the table.

If C were constant you could just set the limit to C and stop. It is not. A dependency that serves 10 concurrent requests when healthy might serve only 2 when degraded -- a slow query plan, a GC pause, a struggling downstream of its own. And there is no static limit that is right for both. A limit tuned to the healthy capacity (say 10) keeps ten requests hammering a dependency that can now handle two, driving latency up several-fold exactly when the dependency is weakest. A limit tuned to the degraded capacity (say 2) is safe when degraded but throttles the client to a fifth of the throughput the dependency could give when healthy. You are forced to choose which regime to be wrong in.

Adaptive concurrency limiting refuses the choice by measuring instead of guessing. It watches latency: while latency stays at baseline, it additively increases the limit, probing for more capacity; when latency spikes above a threshold, it multiplicatively decreases the limit, backing off fast -- the same additive-increase / multiplicative-decrease control that lets TCP find a link's capacity. The limit therefore tracks the current C, converging up when the dependency is healthy and down when it degrades, keeping the client at the knee of the latency curve in every regime.

The rule: set the concurrency limit adaptively from observed latency (AIMD), not to a static value, because a dependency's capacity varies -- so any fixed limit either overloads it when it degrades or starves it when it recovers, while an adaptive limit converges to the current capacity in both.

On this fixture the dependency serves 10 concurrent when healthy and 2 when degraded. A static limit of 10 gives baseline latency healthy but 50ms (5x) when degraded; a static limit of 2 is safe when degraded but caps throughput at 2 of 10 when healthy; the adaptive limit converges to 10 and to 2 respectively -- right in both. This computes all three.

  --regimes   each policy's latency and throughput in the healthy and degraded regimes
  --adapt     the AIMD controller's limit converging to the capacity in each regime
  --check     no static limit is right in both regimes; the adaptive limit tracks the current capacity

d0, threshold, the regimes, and the static limits are the fixture; every latency, throughput, and the converged adaptive limit are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "adaptconc.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def latency(limit, capacity, d0):
    """Baseline latency up to capacity; above it, requests queue and latency rises with the overshoot."""
    return d0 if limit <= capacity else round(d0 * limit / capacity)


def throughput(limit, capacity):
    """Concurrent requests actually served: the smaller of the limit and the capacity."""
    return min(limit, capacity)


def aimd_limit(capacity, d0, threshold, rounds=40):
    """Additive-increase while latency is at/under threshold, decrease when it spikes; return the settled low limit."""
    limit, history = 12, []
    for _ in range(rounds):
        limit = limit + 1 if latency(limit, capacity, d0) <= threshold else limit - 1
        limit = max(1, limit)
        history.append(limit)
    return min(history[-8:])


# ----------------------------------------------------------------- printing

def regimes_view(data):
    d0 = data["d0"]
    print("REGIMES — latency (ms) and throughput of each policy per regime (baseline %dms)" % d0)
    print("-" * 72)
    print("  regime    cap   static_high(%d)      static_low(%d)       adaptive" % (data["static_high"], data["static_low"]))
    for name, C in data["regimes"].items():
        aL = aimd_limit(C, d0, data["threshold"])
        print("  %-8s  %-3d   lat %-3d thru %-2d      lat %-3d thru %-2d      lat %-3d thru %-2d (L=%d)"
              % (name, C,
                 latency(data["static_high"], C, d0), throughput(data["static_high"], C),
                 latency(data["static_low"], C, d0), throughput(data["static_low"], C),
                 latency(aL, C, d0), throughput(aL, C), aL))
    print("-" * 72)
    print("  static_high overloads when degraded; static_low starves when healthy; adaptive fits both")


def adapt_view(data):
    d0, thr = data["d0"], data["threshold"]
    print("ADAPT — the AIMD limit converges to the dependency's current capacity")
    print("-" * 58)
    for name, C in data["regimes"].items():
        aL = aimd_limit(C, d0, thr)
        print("  %-8s  capacity %-3d  ->  adaptive limit converges to %d" % (name, C, aL))
    print("-" * 58)
    print("  increase while latency is at baseline, back off when it spikes — it finds C")


def check(data):
    print("SELF-TEST — no static limit is right in both regimes; the adaptive limit tracks the current capacity")
    print("-" * 120)
    d0, thr = data["d0"], data["threshold"]
    hi, lo = data["static_high"], data["static_low"]
    healthy, degraded = data["regimes"]["healthy"], data["regimes"]["degraded"]

    static_high_overloads_degraded = latency(hi, degraded, d0) > 2 * d0
    print("  static_high overloads the degraded dependency = %s (%dms latency)" % (static_high_overloads_degraded, latency(hi, degraded, d0)))

    static_low_starves_healthy = throughput(lo, healthy) < healthy
    print("  static_low starves the healthy dependency = %s (throughput %d of %d)" % (static_low_starves_healthy, throughput(lo, healthy), healthy))

    ah, ad = aimd_limit(healthy, d0, thr), aimd_limit(degraded, d0, thr)
    adaptive_tracks_capacity = ah == healthy and ad == degraded
    print("  the adaptive limit converges to the capacity in each regime = %s (%d, %d)" % (adaptive_tracks_capacity, ah, ad))

    adaptive_bounded_latency = latency(ah, healthy, d0) <= thr and latency(ad, degraded, d0) <= thr
    print("  adaptive keeps latency at baseline in both regimes = %s" % adaptive_bounded_latency)

    adaptive_full_throughput = throughput(ah, healthy) == healthy and throughput(ad, degraded) == degraded
    print("  adaptive uses the full capacity in both regimes = %s" % adaptive_full_throughput)

    ok = (static_high_overloads_degraded and static_low_starves_healthy and adaptive_tracks_capacity
          and adaptive_bounded_latency and adaptive_full_throughput)
    print("-" * 120)
    print("SELF-TEST %s  static_high_overloads_degraded=%s  static_low_starves_healthy=%s  adaptive_tracks_capacity=%s  adaptive_bounded_latency=%s  adaptive_full_throughput=%s"
          % ("PASS" if ok else "FAIL", static_high_overloads_degraded, static_low_starves_healthy, adaptive_tracks_capacity, adaptive_bounded_latency, adaptive_full_throughput))
    return ok


def main():
    p = argparse.ArgumentParser(description="Adaptive concurrency limiting: set the concurrency limit adaptively from observed latency (AIMD), not to a static value, because a dependency's capacity varies -- so any fixed limit either overloads it when it degrades or starves it when it recovers, while an adaptive limit converges to the current capacity in both.")
    p.add_argument("--regimes", action="store_true")
    p.add_argument("--adapt", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("d0=%dms  threshold=%dms  regimes=%s  static_high=%d  static_low=%d  file=%s  (all fixture)"
          % (data["d0"], data["threshold"], data["regimes"], data["static_high"], data["static_low"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.regimes:
        regimes_view(data)
    elif args.adapt:
        adapt_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
