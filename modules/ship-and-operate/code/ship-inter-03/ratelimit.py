#!/usr/bin/env python3
"""A token-bucket rate limiter -- and the idle bug that lets a burst flood through.

A token bucket bounds request rate. The bucket holds up to `capacity` tokens and
refills at `refill_per_sec`; each request spends one token if one is available, else
it is denied. Capacity is the burst size -- the most requests that can pass
back-to-back -- and the refill rate is the sustained throughput. It is the standard
primitive behind every 'N requests per second' limit.

The whole thing rests on one clamp that is easy to forget: after adding refilled
tokens, cap the bucket at `capacity`. Skip that and tokens accumulate without bound
during idle periods, so after the service sits quiet for a while the bucket holds far
more than capacity, and the next burst -- however large -- sails straight through.
The limiter looks fine under steady load and fails exactly when a burst follows a
lull, which is precisely the traffic shape that overloads a service. This measures
the correct limiter and the uncapped bug side by side.

  --run         allow/deny each request under the correct (capped) limiter
  --burst       largest burst let through at one instant: correct vs buggy
  --check       correct caps every burst at capacity; the buggy one floods after idle

Deterministic: 'time' is the request timestamps, not a clock. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "traffic.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the limiter

def run_limiter(capacity, refill, requests, cap_bucket=True):
    """Token bucket. cap_bucket=False is the BUG: refilled tokens are never clamped.

    Returns a list of (time, allowed) decisions, one per request.
    """
    tokens = float(capacity)  # start full
    last = requests[0] if requests else 0
    decisions = []
    for t in requests:
        tokens += (t - last) * refill  # refill for elapsed time
        if cap_bucket:
            tokens = min(tokens, capacity)  # THE CLAMP: never hold more than capacity
        last = t
        if tokens >= 1.0:
            tokens -= 1.0
            decisions.append((t, True))
        else:
            decisions.append((t, False))
    return decisions


def allowed_count(decisions):
    return sum(1 for _, a in decisions if a)


def max_instant_burst(decisions):
    """Most requests ALLOWED sharing a single timestamp -- the true burst let through."""
    per_time = {}
    for t, a in decisions:
        if a:
            per_time[t] = per_time.get(t, 0) + 1
    return max(per_time.values()) if per_time else 0


# ----------------------------------------------------------------- printing

def run_view(data):
    d = run_limiter(data["capacity"], data["refill_per_sec"], data["requests"], cap_bucket=True)
    print("RUN — correct limiter (capacity=%d, refill=%.0f/s)" % (data["capacity"], data["refill_per_sec"]))
    print("-" * 66)
    for t, a in d:
        print("  t=%-3d  %s" % (t, "allow" if a else "DENY"))
    print("-" * 66)
    print("  allowed %d of %d; each burst is capped at capacity=%d."
          % (allowed_count(d), len(d), data["capacity"]))


def burst_view(data):
    cap, refill, reqs = data["capacity"], data["refill_per_sec"], data["requests"]
    good = run_limiter(cap, refill, reqs, cap_bucket=True)
    bug = run_limiter(cap, refill, reqs, cap_bucket=False)
    print("BURST — largest burst let through at one instant, after the idle gap")
    print("-" * 66)
    print("  correct (capped) limiter: allowed=%d  max instant burst=%d"
          % (allowed_count(good), max_instant_burst(good)))
    print("  buggy (uncapped) limiter: allowed=%d  max instant burst=%d"
          % (allowed_count(bug), max_instant_burst(bug)))
    print("-" * 66)
    print("  the uncapped bucket saved up tokens through the idle gap and flooded.")


def check(data):
    print("SELF-TEST — correct caps every burst at capacity; buggy floods after idle")
    print("-" * 66)
    cap, refill, reqs = data["capacity"], data["refill_per_sec"], data["requests"]

    good = run_limiter(cap, refill, reqs, cap_bucket=True)
    bug = run_limiter(cap, refill, reqs, cap_bucket=False)

    burst_bounded = max_instant_burst(good) <= cap
    print("  correct: no instant burst exceeds capacity = %s (%d <= %d)"
          % (burst_bounded, max_instant_burst(good), cap))

    bug_floods = max_instant_burst(bug) > cap
    print("  buggy: an instant burst exceeds capacity = %s (%d > %d)"
          % (bug_floods, max_instant_burst(bug), cap))

    denied = len(good) - allowed_count(good)
    correct_denies = denied > 0
    print("  correct limiter denies the over-limit requests = %s (%d denied)" % (correct_denies, denied))

    buggy_allows_more = allowed_count(bug) > allowed_count(good)
    print("  buggy limiter allows more than the correct one = %s (%d > %d)"
          % (buggy_allows_more, allowed_count(bug), allowed_count(good)))

    ok = burst_bounded and bug_floods and correct_denies and buggy_allows_more
    print("-" * 66)
    print("SELF-TEST %s  burst_bounded=%s  bug_floods=%s  correct_denies=%s  buggy_allows_more=%s"
          % ("PASS" if ok else "FAIL", burst_bounded, bug_floods, correct_denies, buggy_allows_more))
    return ok


def main():
    p = argparse.ArgumentParser(description="Token-bucket rate limiting and the uncapped-bucket bug.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--burst", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("requests=%d  capacity=%d  refill=%.0f/s  file=%s  (arrival times are a fixture)"
          % (len(data["requests"]), data["capacity"], data["refill_per_sec"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.burst:
        burst_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
