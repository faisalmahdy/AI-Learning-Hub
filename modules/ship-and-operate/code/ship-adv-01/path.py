#!/usr/bin/env python3
"""A resilient request path composes retry bounds, a circuit breaker, and recovery.

The earlier ship modules built resilience primitives one at a time: bounded retries, a
circuit breaker, dead-lettering, deadlines. This composes the first three into one request
path and measures what the composition buys during a downstream outage -- the exact
scenario that separates a system that degrades gracefully from one that makes its own
outage worse.

The naive path retries every failing request many times. During an outage, that is a retry
storm: dozens of calls hammering a dependency that is already down, so the moment it tries
to recover it is knocked flat again -- a cascading failure the caller caused. The resilient
path bounds retries per request, and after enough consecutive failures OPENS a circuit
breaker so further requests fail fast without calling the dependency at all; after a
cooldown it half-opens, probes once, and closes if the probe succeeds. Same outage, same
failed requests -- you cannot serve a request against a dead service -- but a fraction of
the downstream load, and automatic recovery when the outage ends.

  --naive       the naive path: retry every request; count the downstream hammering
  --resilient   the composed path: bounded retries + breaker + recovery; per-request disposition
  --check       the resilient path slashes downstream load, opens the breaker, and recovers

Deterministic: the up/down pattern is the fixture, not a clock. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "traffic.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the naive path

def run_naive(data):
    """Retry every request up to naive_retries. No breaker -> a retry storm during the outage."""
    up = data["up"]
    cap = data["naive_retries"]
    attempts = [0] * len(up)      # downstream attempts per request
    completed = []
    for i, ok in enumerate(up):
        for _ in range(cap):
            attempts[i] += 1
            if ok:
                completed.append(i)
                break
    return attempts, completed


# ------------------------------------------------------------- the resilient path

def run_resilient(data):
    """Bounded retries + circuit breaker + half-open recovery. Returns (attempts, disposition)."""
    up = data["up"]
    threshold, max_retries, cooldown = data["threshold"], data["max_retries"], data["cooldown"]
    attempts = [0] * len(up)
    disposition = ["" for _ in up]      # 'ok', 'failed', 'fast-fail', 'probe-ok', 'probe-fail'
    consec = 0
    breaker_open = False
    opened_at = None
    opens = 0

    for i, ok in enumerate(up):
        if breaker_open:
            if i - opened_at >= cooldown:          # half-open: allow one probe
                attempts[i] += 1
                if ok:
                    breaker_open, consec = False, 0
                    disposition[i] = "probe-ok"     # recovered -> circuit closes
                else:
                    opened_at = i                   # probe failed -> stay open, reset cooldown
                    disposition[i] = "probe-fail"
            else:
                disposition[i] = "fast-fail"        # breaker open -> no downstream call at all
            continue
        # closed: bounded retries
        served = False
        for _ in range(max_retries):
            attempts[i] += 1
            if ok:
                served, consec = True, 0
                break
            consec += 1
            if consec >= threshold:
                breaker_open, opened_at, opens = True, i, opens + 1
                break
        disposition[i] = "ok" if served else "failed"
    return attempts, disposition, opens


# ------------------------------------------------------------- windows

def outage_indices(data):
    return [i for i, ok in enumerate(data["up"]) if not ok]


# ----------------------------------------------------------------- printing

def naive_view(data):
    attempts, completed = run_naive(data)
    outage = outage_indices(data)
    print("NAIVE — retry every request up to %d times (no breaker)" % data["naive_retries"])
    print("-" * 66)
    print("  downstream attempts total:          %d" % sum(attempts))
    print("  downstream attempts during outage:  %d  (requests %s hammered)" % (sum(attempts[i] for i in outage), outage))
    print("  completed: %s" % completed)
    print("-" * 66)
    print("  the retry storm pounds a dependency that is already down.")


def resilient_view(data):
    attempts, disp, opens = run_resilient(data)
    outage = outage_indices(data)
    print("RESILIENT — bounded retries + circuit breaker + half-open recovery")
    print("-" * 66)
    for i in range(len(data["up"])):
        print("  req %2d  up=%-5s attempts=%d  %s" % (i, data["up"][i], attempts[i], disp[i]))
    print("-" * 66)
    print("  downstream attempts during outage: %d (breaker opened %d time(s))"
          % (sum(attempts[i] for i in outage), opens))
    print("  recovered after the outage: %s" % ("probe-ok" in disp))


def check(data):
    print("SELF-TEST — the composed path slashes downstream load, opens the breaker, and recovers")
    print("-" * 66)
    outage = outage_indices(data)

    na, nc = run_naive(data)
    ra, rd, opens = run_resilient(data)

    naive_out = sum(na[i] for i in outage)
    res_out = sum(ra[i] for i in outage)
    protects = res_out < naive_out / 3
    print("  resilient cuts downstream load during the outage = %s (%d vs %d attempts)"
          % (protects, res_out, naive_out))

    breaker_opened = opens >= 1
    print("  the circuit breaker opened during the outage = %s (%d time(s))" % (breaker_opened, opens))

    fast_failed = "fast-fail" in rd
    print("  some outage requests fast-failed without a downstream call = %s" % fast_failed)

    recovered = "probe-ok" in rd and rd[-1] == "ok"
    print("  the path recovered and served requests after the outage = %s" % recovered)

    # Same user-visible outcome: both fail the outage requests (a down service cannot be served).
    naive_ok = set(nc)
    res_ok = {i for i, d in enumerate(rd) if d in ("ok", "probe-ok")}
    same_completions = naive_ok == res_ok
    print("  both paths complete the same requests (resilient just fails cheaply) = %s" % same_completions)

    ok = protects and breaker_opened and fast_failed and recovered and same_completions
    print("-" * 66)
    print("SELF-TEST %s  protects=%s  breaker_opened=%s  fast_failed=%s  recovered=%s  same_completions=%s"
          % ("PASS" if ok else "FAIL", protects, breaker_opened, fast_failed, recovered, same_completions))
    return ok


def main():
    p = argparse.ArgumentParser(description="A composed resilient request path vs a naive one.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--resilient", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("requests=%d  threshold=%d  max_retries=%d  cooldown=%d  file=%s  (up/down is a fixture)"
          % (len(data["up"]), data["threshold"], data["max_retries"], data["cooldown"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.resilient:
        resilient_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
