"""Estimate the steady state, not the early average -- a new feature's launch metrics are inflated by novelty that wears off.

You ship a new feature, run an experiment, and the lift is big. It is tempting to read that number as the feature's value and ship on it. But a brand-new feature enjoys a boost that has nothing to do with its lasting worth: NOVELTY. Users click it because it is new, explore it out of curiosity, and engage at a rate they will not sustain once the shine wears off. So the early metrics are inflated, and the inflation DECAYS over the following days as the novelty fades toward the feature's true, steady-state effect. Measure during the spike and you measure the curiosity, not the value.

The trap has a subtle second layer: averaging does not fix it. A natural instinct, seeing that early days are high, is to average over the whole experiment to smooth it out. But any average over a decaying curve is pulled upward by the early novelty -- the mean of the first three days and even the mean of all eight days both sit well above the plateau the lift is decaying toward. Averaging a novelty spike with a steady state gives you a number that is neither: higher than the truth, lower than the peak, and wrong for forecasting the long run. The decay is not noise to be averaged away; it is signal about which part of the curve is real.

The honest estimate of the long-run effect is the STEADY STATE -- the level the lift settles to after novelty has worn off. Getting it requires running the experiment long enough for the curve to flatten and reading the plateau (the tail), not a window that includes the spike. If you cannot run that long, you at least model the decay and extrapolate to the asymptote rather than trusting an early or windowed average. The counterpart is the PRIMACY effect (a new feature can also under-perform at first while users learn it, then rise), so the general rule is the same: the number that matters is where the curve settles, not where it starts.

The rule: estimate a new feature's long-run effect from the steady state its metric decays (or rises) to after novelty wears off -- reading the flat tail of a long-enough experiment -- rather than from an early window or an average over the launch period, because novelty inflates the early metrics and any average over the decaying curve is pulled above the true steady-state effect.

On this fixture the daily lift starts at 10 and decays to a steady state of 3. The first-3-days average is 7.33 and even the full 8-day average is 4.75 -- both far above the true long-run lift of 3. This computes both.

  --curve      the daily lift and where it decays to (the steady state)
  --estimate   the short-window mean vs the full-window mean vs the steady-state estimate, and how much each overstates
  --check      the early and windowed averages overstate the long-run effect; the steady-state (tail) estimate does not

daily_lift and short_window_days are the fixture; the short-window mean, full-window mean, and steady state are computed. Stdlib only.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "novelty.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def steady_state(daily_lift):
    """The plateau the lift decays to: the value of the flat tail."""
    last = daily_lift[-1]
    # the steady state is the run of equal values at the end
    plateau = [v for v in reversed(daily_lift) if v == last]
    return statistics.mean(plateau)


def short_window_mean(daily_lift, days):
    return statistics.mean(daily_lift[:days])


def full_window_mean(daily_lift):
    return statistics.mean(daily_lift)


def decays(daily_lift):
    """Whether the lift is non-increasing (novelty fading)."""
    return all(daily_lift[i] >= daily_lift[i + 1] for i in range(len(daily_lift) - 1))


# ----------------------------------------------------------------- printing

def curve_view(data):
    dl = data["daily_lift"]
    print("CURVE — daily lift over the experiment")
    print("-" * 52)
    print("  day    " + " ".join("%2d" % (i + 1) for i in range(len(dl))))
    print("  lift   " + " ".join("%2d" % v for v in dl))
    print("-" * 52)
    print("  starts at %d (novelty), decays to steady state %.0f" % (dl[0], steady_state(dl)))


def estimate_view(data):
    dl, sw = data["daily_lift"], data["short_window_days"]
    ss = steady_state(dl)
    print("ESTIMATE — three ways to summarize the lift")
    print("-" * 60)
    print("  short-window mean (first %d days) = %.2f  (overstates by %.2f)" % (sw, short_window_mean(dl, sw), short_window_mean(dl, sw) - ss))
    print("  full-window mean  (all %d days)   = %.2f  (overstates by %.2f)" % (len(dl), full_window_mean(dl), full_window_mean(dl) - ss))
    print("  steady-state (flat tail)         = %.2f  (the true long-run lift)" % ss)
    print("-" * 60)
    print("  averaging over the decay overstates; the steady state is the honest estimate")


def check(data):
    print("SELF-TEST — the early and windowed averages overstate the long-run effect; the steady-state (tail) estimate does not")
    print("-" * 122)
    dl, sw = data["daily_lift"], data["short_window_days"]
    ss = steady_state(dl)
    swm = short_window_mean(dl, sw)
    fwm = full_window_mean(dl)

    early_lift_high = dl[0] > ss
    print("  the early lift is well above the steady state (novelty) = %s (%d vs %.0f)" % (early_lift_high, dl[0], ss))

    lift_decays = decays(dl)
    print("  the lift decays over time (novelty fading) = %s" % lift_decays)

    short_window_overstates = swm > ss
    print("  the short-window mean overstates the long-run lift = %s (%.2f > %.0f)" % (short_window_overstates, swm, ss))

    full_window_also_overstates = fwm > ss
    print("  even the full-window average overstates it = %s (%.2f > %.0f)" % (full_window_also_overstates, fwm, ss))

    steady_state_is_plateau = len({v for v in dl[sw + 1:]}) == 1
    print("  the lift reaches a flat steady-state plateau = %s (tail all %.0f)" % (steady_state_is_plateau, ss))

    steady_below_windowed = ss < swm and ss < fwm
    print("  the steady state is below both averages (the true, lower value) = %s (%.0f < %.2f, %.2f)" % (steady_below_windowed, ss, swm, fwm))

    ok = (early_lift_high and lift_decays and short_window_overstates and full_window_also_overstates
          and steady_state_is_plateau and steady_below_windowed)
    print("-" * 122)
    print("SELF-TEST %s  early_lift_high=%s  lift_decays=%s  short_window_overstates=%s  full_window_also_overstates=%s  steady_state_is_plateau=%s  steady_below_windowed=%s"
          % ("PASS" if ok else "FAIL", early_lift_high, lift_decays, short_window_overstates, full_window_also_overstates, steady_state_is_plateau, steady_below_windowed))
    return ok


def main():
    p = argparse.ArgumentParser(description="Novelty effect: estimate a new feature's long-run effect from the steady state its metric decays to after novelty wears off (reading the flat tail of a long-enough experiment), rather than from an early window or an average over the launch period, because novelty inflates the early metrics and any average over the decaying curve is pulled above the true steady-state effect.")
    p.add_argument("--curve", action="store_true")
    p.add_argument("--estimate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("days=%d  short_window_days=%d  file=%s  (the daily lift is a fixture)"
          % (len(data["daily_lift"]), data["short_window_days"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.curve:
        curve_view(data)
    elif args.estimate:
        estimate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
