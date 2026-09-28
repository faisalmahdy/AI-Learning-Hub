"""Warm a new instance before full traffic, or its first requests pay the cold-start cost and time out.

A freshly started instance looks healthy but is not ready. Its connection pool is empty, its caches are cold,
its code is not yet JIT-compiled, its lazily-loaded config is unread. The process is up and answering, so a naive
readiness check passes and the load balancer sends it a full share of traffic immediately. But the first requests
arrive to find none of that warm state prepared, so each one pays the setup cost -- establishing a connection,
filling a cache, compiling a path -- on top of serving the request. That extra cost lands on real user requests,
and if it pushes their latency past the timeout, they do not just run slow: they fail. A deploy that should be
invisible turns into a burst of errors every time an instance comes up.

Warm-up moves that cost off the user's critical path. Before the instance is marked ready, it pre-establishes its
connections, pre-loads its caches, and exercises its hot paths -- doing the expensive first-time work against
itself, not against a user's request. Only once it is genuinely warm does it start receiving traffic, so every
real request finds the pool full and the caches hot and pays only the steady-state serving cost. The total setup
work is the same; the difference is who waits for it. Warm-up makes the instance, not the first users, absorb the
cold start.

On this fixture a pool of 10 connections costs 200ms each to establish, base serving is 50ms, and the timeout is
100ms. Cold, the first 10 requests each pay 250ms (50 serve + 200 connect) -- over the 100ms timeout -- so all 10
fail; the rest are fine. Warmed, all 10 connections are built beforehand, every request pays 50ms, and none fail.
This computes both.

  --latency    the per-request latency for the first several requests, cold vs warmed
  --timeouts   how many requests exceed the timeout under a cold start vs after warm-up, and the warm-up cost
  --check      a cold start times out its first pool_size requests; warm-up eliminates the timeouts

The pool, timings, and timeout are the fixture; every latency is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "warmup.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def latency(i, data, warmed):
    """Latency of request i (0-indexed). Cold: the first pool_size requests also pay connect_ms."""
    cold_conn = (not warmed) and i < data["pool_size"]
    return data["serve_ms"] + (data["connect_ms"] if cold_conn else 0)


def timeouts(data, warmed):
    """How many of the requests exceed the timeout."""
    return sum(1 for i in range(data["requests"]) if latency(i, data, warmed) > data["timeout_ms"])


def warmup_cost(data):
    """Preparation cost paid before traffic: establish every pooled connection."""
    return data["pool_size"] * data["connect_ms"]


# ----------------------------------------------------------------- printing

def latency_view(data):
    n = data["pool_size"] + 2
    print("LATENCY — per-request latency, cold vs warmed (timeout %dms)" % data["timeout_ms"])
    print("-" * 58)
    print("  request   cold ms   warmed ms")
    for i in range(n):
        c, w = latency(i, data, False), latency(i, data, True)
        flag = "  <- times out" if c > data["timeout_ms"] else ""
        print("  %-7d   %4d      %4d%s" % (i, c, w, flag))
    print("  ...")
    print("-" * 58)
    print("  cold, the first %d requests pay the connect cost and blow the timeout; warmed, none do." % data["pool_size"])


def timeouts_view(data):
    ct, wt = timeouts(data, False), timeouts(data, True)
    print("TIMEOUTS — failed requests under a cold start vs after warm-up")
    print("-" * 58)
    print("  cold start:   %d of %d requests time out" % (ct, data["requests"]))
    print("  warmed:       %d of %d requests time out" % (wt, data["requests"]))
    print("  warm-up cost: %dms of preparation (%d conns x %dms), off the critical path" % (warmup_cost(data), data["pool_size"], data["connect_ms"]))
    print("-" * 58)
    print("  same setup work; warm-up moves it before traffic so users never see a timeout.")


def check(data):
    print("SELF-TEST — a cold start times out its first pool_size requests; warm-up eliminates the timeouts")
    print("-" * 100)
    P = data["pool_size"]

    cold_first_is_slow = latency(0, data, False) > latency(0, data, True)
    print("  the first cold request is slower than warmed = %s (%dms vs %dms)" % (cold_first_is_slow, latency(0, data, False), latency(0, data, True)))

    cold_first_times_out = latency(0, data, False) > data["timeout_ms"]
    print("  the first cold request exceeds the timeout = %s (%dms > %dms)" % (cold_first_times_out, latency(0, data, False), data["timeout_ms"]))

    cold_timeouts_equal_pool = timeouts(data, False) == P
    print("  a cold start times out exactly the first pool_size requests = %s (%d = %d)" % (cold_timeouts_equal_pool, timeouts(data, False), P))

    warm_no_timeouts = timeouts(data, True) == 0
    print("  after warm-up no request times out = %s (%d)" % (warm_no_timeouts, timeouts(data, True)))

    steady_state_identical = latency(P, data, False) == latency(P, data, True)
    print("  past the pool, cold and warmed serve identically = %s (%dms)" % (steady_state_identical, latency(P, data, False)))

    ok = cold_first_is_slow and cold_first_times_out and cold_timeouts_equal_pool and warm_no_timeouts and steady_state_identical
    print("-" * 100)
    print("SELF-TEST %s  cold_first_is_slow=%s  cold_first_times_out=%s  cold_timeouts_equal_pool=%s  warm_no_timeouts=%s  steady_state_identical=%s"
          % ("PASS" if ok else "FAIL", cold_first_is_slow, cold_first_times_out, cold_timeouts_equal_pool, warm_no_timeouts, steady_state_identical))
    return ok


def main():
    p = argparse.ArgumentParser(description="Warm a new instance (pre-fill the pool, pre-load caches) before sending traffic, so users never pay the cold-start cost.")
    p.add_argument("--latency", action="store_true")
    p.add_argument("--timeouts", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pool=%d  connect=%dms  serve=%dms  timeout=%dms  requests=%d  file=%s  (the timings are a fixture)"
          % (data["pool_size"], data["connect_ms"], data["serve_ms"], data["timeout_ms"], data["requests"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.latency:
        latency_view(data)
    elif args.timeouts:
        timeouts_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
