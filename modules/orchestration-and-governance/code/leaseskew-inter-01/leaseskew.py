"""A lease holder must use an effective lease shorter than the granted duration by a safety margin -- if it uses the full duration on its own clock, network delay and clock skew put its stop moment past the grantor's expiry, so the grantor can reassign the lease while the old holder still thinks it holds it: two holders at once.

A lease grants exclusive use of a resource for a duration D. Two clocks are involved. The grantor starts counting when it sends the grant and will reassign the lease at its own time D. The holder starts counting when it receives the grant -- later than the grantor sent it, by the network delay -- and the holder's clock may run slow relative to the grantor's, so its D-length timer takes extra real time to finish.

Put those together in the grantor's timeline. The holder receives the grant at delay, runs a timer that takes D plus the skew to elapse, and stops at delay + D + skew. The grantor expired the lease at D. So the holder is still acting from D until delay + D + skew -- a window in which the grantor may have already handed the lease to a new holder. Two nodes hold the same lease, which is exactly the mutual-exclusion failure the lease existed to prevent.

The holder cannot see the grantor's clock, so it cannot measure this directly. What it can do is assume the worst and shorten its own view of the lease. Use an effective lease of D minus a safety margin, with the margin at least the maximum network delay plus the maximum clock skew. Then the holder stops at delay + (D - margin) + skew, which is at most D -- at or before the grantor's expiry -- so the windows never overlap.

On this fixture D is 100, the network delay is 10, the clock skew is 15, and the margin is 30. The naive holder stops at 125, overrunning the grantor's expiry of 100 by 25 (exactly delay + skew). The holder using D minus 30 stops at 95, safely before 100. A margin of only 20 is smaller than delay + skew and still overruns, to 105. This computes all of it.

  --naive   the holder uses the full duration and overruns the grantor's expiry
  --safe    the holder uses the duration minus a margin and stops before the expiry
  --check   the naive stop overruns the grantor's expiry by delay + skew, a margin of at least delay + skew stops in time, and a margin smaller than that still overruns

the lease duration, network delay, clock skew, and margins are the fixture; the grantor expiry, the stop times, and the overlaps are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "leaseskew.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def grantor_expiry(d):
    """When the grantor considers the lease expired and may reassign it: its own duration."""
    return d["lease_duration"]


def holder_stop(d, effective_duration):
    """When the holder actually stops, in the grantor's timeline: receipt delay + its timer + skew."""
    return d["network_delay"] + effective_duration + d["clock_skew"]


def overlap(d, effective_duration):
    """How long the holder keeps acting past the grantor's expiry (0 if it stops in time)."""
    return max(0, holder_stop(d, effective_duration) - grantor_expiry(d))


def needed_margin(d):
    """The smallest safety margin that avoids overlap: the network delay plus the clock skew."""
    return d["network_delay"] + d["clock_skew"]


# ----------------------------------------------------------------- printing

def naive_view(d):
    dur = d["lease_duration"]
    print("NAIVE — holder uses the full granted duration %d on its own clock" % dur)
    print("-" * 64)
    print("  grantor expiry (grantor clock) = %d" % grantor_expiry(d))
    print("  holder stop = delay %d + duration %d + skew %d = %d" % (d["network_delay"], dur, d["clock_skew"], holder_stop(d, dur)))
    print("  overlap past expiry = %d" % overlap(d, dur))
    print("-" * 64)
    print("  the holder is still acting after the grantor reassigned the lease -- two holders")


def safe_view(d):
    dur, m = d["lease_duration"], d["margin"]
    eff = dur - m
    print("SAFE — holder uses an effective lease of duration %d minus margin %d = %d" % (dur, m, eff))
    print("-" * 64)
    print("  grantor expiry = %d" % grantor_expiry(d))
    print("  holder stop = delay %d + effective %d + skew %d = %d" % (d["network_delay"], eff, d["clock_skew"], holder_stop(d, eff)))
    print("  overlap past expiry = %d   (margin %d >= needed %d)" % (overlap(d, eff), m, needed_margin(d)))
    print("-" * 64)
    print("  shortening the lease by at least delay + skew makes the holder stop before expiry")


def check(d):
    print("SELF-TEST — the naive stop overruns the grantor's expiry by delay + skew, a margin of at least delay + skew stops in time, and a smaller margin still overruns")
    print("-" * 112)
    dur, m, sm = d["lease_duration"], d["margin"], d["small_margin"]

    naive_overlaps = overlap(d, dur) > 0
    print("  naive holder overruns the grantor's expiry = %s (stop %d > expiry %d)" % (naive_overlaps, holder_stop(d, dur), grantor_expiry(d)))

    overlap_is_delay_plus_skew = overlap(d, dur) == needed_margin(d)
    print("  the overrun equals delay + skew = %s (%d == %d)" % (overlap_is_delay_plus_skew, overlap(d, dur), needed_margin(d)))

    safe_no_overlap = overlap(d, dur - m) == 0
    print("  margin %d (>= delay+skew) stops the holder in time = %s (stop %d <= expiry %d)" % (m, safe_no_overlap, holder_stop(d, dur - m), grantor_expiry(d)))

    margin_covers = m >= needed_margin(d)
    print("  the chosen margin covers delay + skew = %s (%d >= %d)" % (margin_covers, m, needed_margin(d)))

    small_margin_fails = overlap(d, dur - sm) > 0
    print("  a margin of only %d (< delay+skew) still overruns = %s (stop %d)" % (sm, small_margin_fails, holder_stop(d, dur - sm)))

    ok = (naive_overlaps and overlap_is_delay_plus_skew and safe_no_overlap and margin_covers and small_margin_fails)
    print("-" * 112)
    print("SELF-TEST %s  naive_overlaps=%s  overlap_is_delay_plus_skew=%s  safe_no_overlap=%s  margin_covers=%s  small_margin_fails=%s"
          % ("PASS" if ok else "FAIL", naive_overlaps, overlap_is_delay_plus_skew, safe_no_overlap, margin_covers, small_margin_fails))
    return ok


def main():
    p = argparse.ArgumentParser(description="Lease safety margin: a lease holder must use an effective lease shorter than the granted duration by at least the maximum network delay plus clock skew, because using the full duration on its own clock puts its stop moment past the grantor's expiry -- the grantor reassigns the lease while the old holder still believes it holds it, producing two holders; the holder cannot see the grantor's clock, so it shortens its own view of the lease to stay safely inside the grant.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--safe", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("lease=%d  network_delay=%d  clock_skew=%d  margin=%d  file=%s"
          % (d["lease_duration"], d["network_delay"], d["clock_skew"], d["margin"], DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.naive:
        naive_view(d)
    elif args.safe:
        safe_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
