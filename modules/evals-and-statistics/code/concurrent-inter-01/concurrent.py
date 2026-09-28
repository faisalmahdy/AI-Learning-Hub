"""Compare against a concurrent control, not a before/after -- a metric that drifts over time gets its trend credited to the treatment, because a before/after design confounds the effect with the time period, while a concurrent split cancels the trend.

Real metrics move on their own. Traffic swings between weekday and weekend, seasons turn, a marketing campaign lands, the user mix drifts. None of that is your change, but all of it shows up in the numbers over time. So the question a good experiment has to answer -- did MY change move the metric? -- can only be answered if the comparison holds time constant.

A before/after design does not. It measures the old variant in one period, ships the new variant, and measures it in a later period. The difference it reports is the treatment effect plus everything the metric drifted between the two periods, and the two are inseparable: there is no way, from those two numbers, to tell how much was the change and how much was the calendar. A metric that was rising anyway makes a neutral change look like a win; a metric that was falling makes a real win look like a loss.

A concurrent design fixes this by running both variants at the same time, on a random split of the same traffic. Now the two arms live through the identical time period -- the same day, the same campaign, the same user mix -- so whatever the metric was going to do over time happens to both of them equally and cancels out of their difference. What remains is the treatment effect, uncontaminated by the trend. The control is not the past; it is the other half of today.

The rule: compare a treatment against a concurrent control -- both variants running at the same time on randomly split traffic -- not against a before/after baseline from an earlier period, because a before/after difference confounds the treatment effect with the metric's time trend, while a concurrent split subjects both arms to the same trend so it cancels.

On this fixture the metric drifts up by 5 between periods while the treatment's true effect is 2. A before/after comparison (old in period 1, new in period 2) reports 7 -- the effect plus the trend; a concurrent comparison (both in period 2) reports 2. This computes both.

  --values    the metric for each variant in each period, and the two designs' reported differences
  --attribute the before/after difference split into true effect vs time trend
  --check     before/after confounds the effect with the time trend; a concurrent split cancels it

base, time_trend, and true_effect are the fixture; the per-cell values and the two differences are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "concurrent.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def metric(base, trend, effect, period, is_new):
    """The metric for a variant in a period: baseline + the period's trend + the effect if it's the new variant."""
    return base + (trend if period == 2 else 0) + (effect if is_new else 0)


def before_after(base, trend, effect):
    """Old variant measured in period 1, new variant in period 2 -- across two time periods."""
    old_p1 = metric(base, trend, effect, 1, is_new=False)
    new_p2 = metric(base, trend, effect, 2, is_new=True)
    return new_p2 - old_p1


def concurrent(base, trend, effect):
    """Both variants measured in the same period (2), on a random split -- same time for both."""
    old_p2 = metric(base, trend, effect, 2, is_new=False)
    new_p2 = metric(base, trend, effect, 2, is_new=True)
    return new_p2 - old_p2


# ----------------------------------------------------------------- printing

def values_view(data):
    b, t, e = data["base"], data["time_trend"], data["true_effect"]
    print("VALUES — metric per variant per period (base=%d, trend=%d, effect=%d)" % (b, t, e))
    print("-" * 58)
    print("  period   old variant   new variant")
    print("  1        %-11d   %d" % (metric(b, t, e, 1, False), metric(b, t, e, 1, True)))
    print("  2        %-11d   %d" % (metric(b, t, e, 2, False), metric(b, t, e, 2, True)))
    print("-" * 58)
    print("  before/after diff = %d   concurrent diff = %d   (true effect = %d)"
          % (before_after(b, t, e), concurrent(b, t, e), e))


def attribute_view(data):
    b, t, e = data["base"], data["time_trend"], data["true_effect"]
    ba = before_after(b, t, e)
    print("ATTRIBUTE — what the before/after difference is made of")
    print("-" * 50)
    print("  before/after difference        = %d" % ba)
    print("    of which true effect         = %d" % e)
    print("    of which time trend (bias)   = %d" % t)
    print("  concurrent difference          = %d  (trend cancels)" % concurrent(b, t, e))
    print("-" * 50)
    print("  the trend is credited to the treatment only in the before/after design")


def check(data):
    print("SELF-TEST — before/after confounds the effect with the time trend; a concurrent split cancels it")
    print("-" * 104)
    b, t, e = data["base"], data["time_trend"], data["true_effect"]
    ba = before_after(b, t, e)
    co = concurrent(b, t, e)

    trend_exists = metric(b, t, e, 2, False) != metric(b, t, e, 1, False)
    print("  the metric drifts over time on its own (trend != 0) = %s (%d)" % (trend_exists, t))

    before_after_overstates = ba != e
    print("  before/after difference does not equal the true effect = %s (%d vs %d)" % (before_after_overstates, ba, e))

    before_after_is_effect_plus_trend = ba == e + t
    print("  before/after difference = true effect + time trend = %s (%d = %d + %d)" % (before_after_is_effect_plus_trend, ba, e, t))

    concurrent_correct = co == e
    print("  concurrent difference equals the true effect = %s (%d)" % (concurrent_correct, co))

    concurrent_beats_before_after = abs(co - e) < abs(ba - e)
    print("  concurrent is closer to the truth than before/after = %s" % concurrent_beats_before_after)

    ok = (trend_exists and before_after_overstates and before_after_is_effect_plus_trend
          and concurrent_correct and concurrent_beats_before_after)
    print("-" * 104)
    print("SELF-TEST %s  trend_exists=%s  before_after_overstates=%s  before_after_is_effect_plus_trend=%s  concurrent_correct=%s  concurrent_beats_before_after=%s"
          % ("PASS" if ok else "FAIL", trend_exists, before_after_overstates,
             before_after_is_effect_plus_trend, concurrent_correct, concurrent_beats_before_after))
    return ok


def main():
    p = argparse.ArgumentParser(description="Concurrent control: compare a treatment against a concurrent control -- both variants running at the same time on randomly split traffic -- not against a before/after baseline from an earlier period, because a before/after difference confounds the treatment effect with the metric's time trend, while a concurrent split subjects both arms to the same trend so it cancels.")
    p.add_argument("--values", action="store_true")
    p.add_argument("--attribute", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("base=%d  time_trend=%d  true_effect=%d  file=%s  (these are a fixture)"
          % (data["base"], data["time_trend"], data["true_effect"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.values:
        values_view(data)
    elif args.attribute:
        attribute_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
