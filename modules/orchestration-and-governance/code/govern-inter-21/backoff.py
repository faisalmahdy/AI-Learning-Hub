"""Add jitter to backoff, or every client that failed together retries together and stampedes the recovery.

Exponential backoff spaces out retries: wait a little, then more, then more, so a struggling dependency is not
hammered on a tight loop. But backoff alone fixes the RATE of one client's retries, not the PHASE across many.
When a shared dependency fails, every client fails at nearly the same instant, and if they all use the same
backoff schedule they all wait the same amount and retry at the same instant too. The load you were trying to
spread out arrives as a spike: N clients, one retry, one moment. The dependency, just coming back up, is knocked
flat again by a synchronized wave -- a thundering herd. Backoff without jitter reschedules the stampede; it does
not disperse it.

Jitter breaks the phase lock. Instead of waiting exactly base*2^attempt, each client waits a RANDOM time in
[0, base*2^attempt) -- full jitter. Now two clients that failed together retry at different moments, because
their waits are drawn independently. The same total number of retries still happens, but they are smeared across
the whole backoff window instead of piling into one instant, so the peak load per moment drops sharply. The
recovering dependency sees a trickle it can absorb, not a wall it cannot.

On this fixture 12 clients fail together and retry 3 times each with base 4s. Without jitter every wave lands all
12 retries in a single second -- peak 12. With full jitter (seeded) the same 36 retries spread across the window
and the busiest second holds far fewer. Same work, a fraction of the peak. This computes both.

  --load       the per-second retry histogram with and without jitter, and each one's peak second
  --peak       the peak concurrent retries for both, and the totals (jitter spreads, it does not drop work)
  --check      no-jitter peaks at all clients at once; jitter cuts the peak; the total retries are unchanged

The clients, base, and seed are the fixture; every arrival time is computed. Stdlib only.
"""
import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "backoff.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def arrivals(clients, base, attempts, seed, jitter):
    """Every retry's arrival second. All clients fail at t=0; attempt a has backoff cap base*2^a.
    jitter=False waits exactly the cap; jitter=True waits uniform(0, cap). Returns a list of int seconds."""
    rng = random.Random(seed)
    out = []
    for _ in range(clients):
        t = 0.0
        for a in range(attempts):
            cap = base * (2 ** a)
            wait = rng.uniform(0, cap) if jitter else cap
            t += wait
            out.append(int(t))
    return out


def histogram(times):
    """Retries per 1-second bucket."""
    return Counter(times)


def peak(times):
    """The most retries landing in any single second."""
    h = histogram(times)
    return max(h.values()) if h else 0


# ----------------------------------------------------------------- printing

def load_view(data):
    c, b, a, s = data["clients"], data["base"], data["attempts"], data["seed"]
    plain = arrivals(c, b, a, s, jitter=False)
    jit = arrivals(c, b, a, s, jitter=True)
    print("LOAD — retries per second (%d clients, base %ds, %d attempts)" % (c, b, a))
    print("-" * 62)
    hp, hj = histogram(plain), histogram(jit)
    span = range(0, max(list(hp) + list(hj)) + 1)
    print("  no jitter:  " + " ".join("%d@%ds" % (hp[t], t) for t in span if hp[t]))
    print("  full jitter:" + " ".join("%d@%ds" % (hj[t], t) for t in span if hj[t]))
    print("-" * 62)
    print("  no jitter piles every wave into one second; jitter smears each wave across the window.")


def peak_view(data):
    c, b, a, s = data["clients"], data["base"], data["attempts"], data["seed"]
    plain = arrivals(c, b, a, s, jitter=False)
    jit = arrivals(c, b, a, s, jitter=True)
    print("PEAK — busiest second and total retries")
    print("-" * 62)
    print("  no jitter:    peak %2d retries/s   total %d retries" % (peak(plain), len(plain)))
    print("  full jitter:  peak %2d retries/s   total %d retries" % (peak(jit), len(jit)))
    print("-" * 62)
    print("  same total work; jitter cuts the peak from %d to %d per second." % (peak(plain), peak(jit)))


def check(data):
    print("SELF-TEST — no jitter peaks at all clients at once; jitter cuts the peak; the total is unchanged")
    print("-" * 100)
    c, b, a, s = data["clients"], data["base"], data["attempts"], data["seed"]
    plain = arrivals(c, b, a, s, jitter=False)
    jit = arrivals(c, b, a, s, jitter=True)

    no_jitter_peak_is_all_clients = peak(plain) == c
    print("  without jitter the peak second holds every client = %s (%d = %d)" % (no_jitter_peak_is_all_clients, peak(plain), c))

    jitter_cuts_peak = peak(jit) < peak(plain)
    print("  jitter lowers the peak second = %s (%d < %d)" % (jitter_cuts_peak, peak(jit), peak(plain)))

    total_unchanged = len(jit) == len(plain) == c * a
    print("  the total retries are unchanged = %s (%d = %d = %d*%d)" % (total_unchanged, len(jit), len(plain), c, a))

    jitter_spreads_wider = len(histogram(jit)) > len(histogram(plain))
    print("  jitter occupies more distinct seconds = %s (%d buckets vs %d)" % (jitter_spreads_wider, len(histogram(jit)), len(histogram(plain))))

    jit_again = arrivals(c, b, a, s, jitter=True)
    deterministic = jit == jit_again
    print("  the seeded jitter is reproducible = %s" % deterministic)

    ok = no_jitter_peak_is_all_clients and jitter_cuts_peak and total_unchanged and jitter_spreads_wider and deterministic
    print("-" * 100)
    print("SELF-TEST %s  no_jitter_peak_is_all_clients=%s  jitter_cuts_peak=%s  total_unchanged=%s  jitter_spreads_wider=%s  deterministic=%s"
          % ("PASS" if ok else "FAIL", no_jitter_peak_is_all_clients, jitter_cuts_peak, total_unchanged, jitter_spreads_wider, deterministic))
    return ok


def main():
    p = argparse.ArgumentParser(description="Full jitter on exponential backoff disperses synchronized retries so a recovering dependency is not stampeded.")
    p.add_argument("--load", action="store_true")
    p.add_argument("--peak", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("clients=%d  base=%ds  attempts=%d  seed=%d  file=%s  (the parameters are a fixture)"
          % (data["clients"], data["base"], data["attempts"], data["seed"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.load:
        load_view(data)
    elif args.peak:
        peak_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
