"""Add jitter to the retry backoff -- without it, every client that failed together retries together and recreates the spike that caused the failure.

Exponential backoff is the standard retry discipline: after a failure, wait, and double the wait on each successive failure so a struggling dependency is not hammered. It fixes the rate at which a SINGLE client retries, and it does nothing about the problem that actually takes systems down -- SYNCHRONIZATION. When a shared dependency has a blip, every client calling it fails at nearly the same instant. Each then computes the same backoff delay and retries after it. So all of them retry at the same moment, in one synchronized wave, and that wave is the exact load spike that caused the outage, arriving again just as the dependency is trying to recover. Backoff spread out one client's retries in time; it lined up all the clients' retries at the same time.

This is the thundering herd, and it can wedge a system into a retry-storm loop: the herd hits, the dependency fails again, everyone backs off by the (now doubled, but still identical) delay, and the herd re-forms and hits again, synchronized as ever. The backoff got longer but the clients stayed in lockstep, so the dependency never gets the quiet interval it needs to recover.

Jitter breaks the synchronization by randomizing the delay. Instead of every client waiting exactly the backoff delay, each waits a random amount -- full jitter picks the retry time uniformly between zero and the backoff delay -- so the retries that used to land in one instant are smeared across the whole window. The dependency sees a smooth trickle of retries it can absorb instead of a wall it cannot. Crucially, jitter does NOT reduce the number of retries or slow any individual client meaningfully; it only DE-SYNCHRONIZES them, turning a coordinated wave into independent arrivals. The randomness is the point: correlated failures need uncorrelated recoveries.

The rule: add random jitter to the retry backoff delay (e.g. full jitter: a random wait uniform in [0, backoff]) rather than retrying after a fixed backoff, because clients that fail together compute the same fixed delay and retry in a synchronized wave that recreates the original load spike -- while jitter spreads the same retries across the window so the recovering dependency sees a trickle, not a herd.

On this fixture six clients fail together with a backoff of 4. Without jitter all six retry at once (peak concurrency 6). With full jitter their retry times spread across the window into buckets [2, 1, 1, 2], dropping the peak to 2 -- the same six retries, de-synchronized. This computes both.

  --retries   each client's retry time and bucket without jitter vs with full jitter
  --peak      the peak concurrent retries (herd size) without jitter vs with jitter, and the total retries (unchanged)
  --check     without jitter all retries synchronize into one spike; jitter spreads them and lowers the peak, same total

base_delay, num_buckets, and the clients' jitter fractions are the fixture; every retry time, bucket, and peak is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "jitter.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def no_jitter_time(base):
    """Without jitter, every client retries at exactly the backoff delay."""
    return base


def full_jitter_time(jitter_frac, base):
    """Full jitter: a retry time uniform in [0, base) -- here the pre-drawn fraction times base."""
    return jitter_frac * base


def bucket(t, base, num_buckets):
    """Which time slot a retry lands in (clamped to the last slot)."""
    return min(int(t / base * num_buckets), num_buckets - 1)


def buckets_full_jitter(clients, base, num_buckets):
    counts = [0] * num_buckets
    for c in clients:
        counts[bucket(full_jitter_time(c["jitter_frac"], base), base, num_buckets)] += 1
    return counts


# ----------------------------------------------------------------- printing

def retries_view(data):
    clients, base, nb = data["clients"], data["base_delay"], data["num_buckets"]
    print("RETRIES — each client's retry time without jitter vs with full jitter")
    print("-" * 66)
    print("  client   no-jitter time   jitter time   jitter bucket")
    for c in clients:
        jt = full_jitter_time(c["jitter_frac"], base)
        print("  %-6s   %-14d   %-11.1f   %d" % (c["id"], no_jitter_time(base), jt, bucket(jt, base, nb)))
    print("-" * 66)
    print("  without jitter every client retries at t=%d; with jitter they spread across [0,%d)" % (base, base))


def peak_view(data):
    clients, base, nb = data["clients"], data["base_delay"], data["num_buckets"]
    n = len(clients)
    jbuckets = buckets_full_jitter(clients, base, nb)
    print("PEAK — peak concurrent retries (herd size) without vs with jitter")
    print("-" * 60)
    print("  no jitter:  all %d retries at t=%d -> peak concurrency %d" % (n, base, n))
    print("  full jitter: buckets %s -> peak concurrency %d" % (jbuckets, max(jbuckets)))
    print("-" * 60)
    print("  total retries: %d both ways (jitter spreads them, it does not reduce them)" % (n, ))


def check(data):
    print("SELF-TEST — without jitter all retries synchronize into one spike; jitter spreads them and lowers the peak, same total")
    print("-" * 120)
    clients, base, nb = data["clients"], data["base_delay"], data["num_buckets"]
    n = len(clients)
    jbuckets = buckets_full_jitter(clients, base, nb)
    no_jitter_peak = n
    jitter_peak = max(jbuckets)

    all_synchronize_no_jitter = len({no_jitter_time(base) for _ in clients}) == 1
    print("  without jitter every client retries at the same time = %s (all at t=%d)" % (all_synchronize_no_jitter, base))

    no_jitter_peak_is_n = no_jitter_peak == n
    print("  the no-jitter peak concurrency equals the herd size = %s (%d)" % (no_jitter_peak_is_n, no_jitter_peak))

    jitter_spreads = sum(1 for b in jbuckets if b > 0) > 1
    print("  jitter spreads retries across multiple time buckets = %s (%s)" % (jitter_spreads, jbuckets))

    jitter_lowers_peak = jitter_peak < no_jitter_peak
    print("  jitter lowers the peak concurrency = %s (%d < %d)" % (jitter_lowers_peak, jitter_peak, no_jitter_peak))

    total_retries_same = sum(jbuckets) == n
    print("  the total number of retries is unchanged by jitter = %s (%d)" % (total_retries_same, sum(jbuckets)))

    peak_near_uniform = jitter_peak <= (n + nb - 1) // nb + 1
    print("  the jittered peak is near the uniform ideal (~n/buckets) = %s (peak %d vs ideal ~%d)" % (peak_near_uniform, jitter_peak, -(-n // nb)))

    ok = (all_synchronize_no_jitter and no_jitter_peak_is_n and jitter_spreads and jitter_lowers_peak
          and total_retries_same and peak_near_uniform)
    print("-" * 120)
    print("SELF-TEST %s  all_synchronize_no_jitter=%s  no_jitter_peak_is_n=%s  jitter_spreads=%s  jitter_lowers_peak=%s  total_retries_same=%s  peak_near_uniform=%s"
          % ("PASS" if ok else "FAIL", all_synchronize_no_jitter, no_jitter_peak_is_n, jitter_spreads, jitter_lowers_peak, total_retries_same, peak_near_uniform))
    return ok


def main():
    p = argparse.ArgumentParser(description="Retry jitter: add random jitter to the retry backoff delay (e.g. full jitter: a random wait uniform in [0, backoff]) rather than retrying after a fixed backoff, because clients that fail together compute the same fixed delay and retry in a synchronized wave that recreates the original load spike -- while jitter spreads the same retries across the window so the recovering dependency sees a trickle, not a herd.")
    p.add_argument("--retries", action="store_true")
    p.add_argument("--peak", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("clients=%d  base_delay=%d  num_buckets=%d  file=%s  (the clients, backoff, and jitter fractions are a fixture)"
          % (len(data["clients"]), data["base_delay"], data["num_buckets"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.retries:
        retries_view(data)
    elif args.peak:
        peak_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
