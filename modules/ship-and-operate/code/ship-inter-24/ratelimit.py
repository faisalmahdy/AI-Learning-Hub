"""Count requests in a sliding window, or a fixed-window rate limiter lets a double burst through at the boundary.

A rate limiter promises no more than `limit` requests per window. The simplest implementation counts requests in
fixed calendar buckets -- [0, W), [W, 2W), and so on -- incrementing a counter and resetting it to zero at each
bucket boundary. It is cheap: one counter, reset on a timer. But the reset is a loophole. A client can send the
full limit at the very end of one bucket, then, a fraction of a second later when the boundary flips and the
counter resets, send the full limit again at the start of the next bucket. Two full limits land in a span shorter
than one window, so the actual peak rate is DOUBLE the limit you configured. The limiter enforced the average
over each bucket while letting the instantaneous rate spike to 2x, and a client aiming to overwhelm a downstream
service will aim exactly at that boundary.

A sliding-window limiter closes the loophole by counting the requests in the trailing `window` seconds up to each
request, rather than in a fixed bucket. There is no boundary to straddle: when the second burst arrives, the
first burst is still inside the trailing window -- it has not aged out -- so its requests still count, the limit
is already reached, and the second burst is rejected. The trailing window moves with each request, so the
`limit`-per-`window` bound holds at every instant, not just per calendar bucket. The cost is bookkeeping: you must
remember recent request timestamps (or approximate them) rather than keep a single counter, but you get the rate
guarantee the fixed window only pretended to give.

On this fixture the limit is 5 per 10 seconds. Five requests arrive at t=9 (end of the first bucket) and five at
t=10 (start of the second). The fixed-window limiter admits all 10 -- 2x the limit -- in a one-second span. The
sliding-window limiter admits the first 5 and rejects the second 5, holding the true rate. This computes both.

  --admit      how many requests each limiter admits, and the peak rate over any one-window span
  --window     the trailing-window count the sliding limiter sees when the second burst arrives
  --check      the fixed window admits 2x the limit at the boundary; the sliding window holds the limit

The limit, window, and arrival times are the fixture; every decision is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "ratelimit.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def fixed_window(requests, limit, window):
    """Admit if the fixed calendar bucket [k*window, (k+1)*window) holds fewer than `limit` so far."""
    counts, admitted = {}, []
    for t in requests:
        bucket = t // window
        if counts.get(bucket, 0) < limit:
            counts[bucket] = counts.get(bucket, 0) + 1
            admitted.append(t)
    return admitted


def sliding_window(requests, limit, window):
    """Admit if the trailing `window` seconds up to t hold fewer than `limit` already-admitted requests."""
    admitted = []
    for t in requests:
        in_window = [a for a in admitted if t - window < a <= t]
        if len(in_window) < limit:
            admitted.append(t)
    return admitted


def peak_in_any_window(admitted, window):
    """The most admitted requests inside any trailing `window`-second span."""
    return max((sum(1 for a in admitted if t - window < a <= t) for t in admitted), default=0)


# ----------------------------------------------------------------- printing

def admit_view(data):
    reqs, limit, w = data["requests"], data["limit"], data["window"]
    fx = fixed_window(reqs, limit, w)
    sl = sliding_window(reqs, limit, w)
    print("ADMIT — requests admitted (limit %d per %ds), %d arrivals at the boundary" % (limit, w, len(reqs)))
    print("-" * 62)
    print("  fixed window:    admitted %d   peak in one window: %d   (%.0fx the limit)" % (len(fx), peak_in_any_window(fx, w), peak_in_any_window(fx, w) / limit))
    print("  sliding window:  admitted %d   peak in one window: %d   (at the limit)" % (len(sl), peak_in_any_window(sl, w)))
    print("-" * 62)
    print("  the fixed window's reset lets a second full burst through; the sliding window does not.")


def window_view(data):
    reqs, limit, w = data["requests"], data["limit"], data["window"]
    boundary = w  # the second burst arrives at t = window
    admitted_so_far = sliding_window([t for t in reqs if t < boundary], limit, w)
    in_trailing = [a for a in admitted_so_far if boundary - w < a <= boundary]
    print("WINDOW — what the sliding limiter sees when the second burst arrives at t=%d" % boundary)
    print("-" * 62)
    print("  admitted in the trailing %d seconds (%d, %d]: %d" % (w, boundary - w, boundary, len(in_trailing)))
    print("  limit: %d  ->  the trailing window is already full, so the second burst is rejected" % limit)
    print("-" * 62)
    print("  the first burst has not aged out of the trailing window, so it still counts against the limit.")


def check(data):
    print("SELF-TEST — the fixed window admits 2x the limit at the boundary; the sliding window holds the limit")
    print("-" * 104)
    reqs, limit, w = data["requests"], data["limit"], data["window"]
    fx = fixed_window(reqs, limit, w)
    sl = sliding_window(reqs, limit, w)

    fixed_admits_double = len(fx) == 2 * limit
    print("  the fixed window admits twice the limit = %s (%d = 2*%d)" % (fixed_admits_double, len(fx), limit))

    fixed_peak_exceeds = peak_in_any_window(fx, w) > limit
    print("  the fixed window's peak rate exceeds the limit = %s (%d > %d in one window)" % (fixed_peak_exceeds, peak_in_any_window(fx, w), limit))

    sliding_admits_limit = len(sl) == limit
    print("  the sliding window admits exactly the limit = %s (%d)" % (sliding_admits_limit, len(sl)))

    sliding_peak_within = peak_in_any_window(sl, w) <= limit
    print("  the sliding window never exceeds the limit in any window = %s (%d <= %d)" % (sliding_peak_within, peak_in_any_window(sl, w), limit))

    both_admit_first_burst = len([t for t in fx if t == 9]) == limit and len([t for t in sl if t == 9]) == limit
    print("  both admit the first burst at the window's end = %s" % both_admit_first_burst)

    ok = fixed_admits_double and fixed_peak_exceeds and sliding_admits_limit and sliding_peak_within and both_admit_first_burst
    print("-" * 104)
    print("SELF-TEST %s  fixed_admits_double=%s  fixed_peak_exceeds=%s  sliding_admits_limit=%s  sliding_peak_within=%s  both_admit_first_burst=%s"
          % ("PASS" if ok else "FAIL", fixed_admits_double, fixed_peak_exceeds, sliding_admits_limit, sliding_peak_within, both_admit_first_burst))
    return ok


def main():
    p = argparse.ArgumentParser(description="A fixed-window rate limiter allows a 2x burst at the window boundary; a sliding window counts the trailing window and holds the true rate.")
    p.add_argument("--admit", action="store_true")
    p.add_argument("--window", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("limit=%d  window=%ds  requests=%d  file=%s  (the arrivals are a fixture)"
          % (data["limit"], data["window"], len(data["requests"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.admit:
        admit_view(data)
    elif args.window:
        window_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
