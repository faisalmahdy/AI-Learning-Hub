"""Alert on the error-budget burn rate, not the raw error rate -- a slow burn under the threshold blows the whole SLO.

An SLO -- say 99.9% success over 30 days -- is an error BUDGET: it permits a small fraction of requests to
fail (here 0.1%), and the budget is spent as errors occur. The question monitoring must answer is not "is the
error rate high right now" but "are we spending the budget faster than we can afford." Those come apart. A
raw-threshold alert fires when the instantaneous error rate crosses a fixed line; it catches a loud FAST burn
that spikes well above the line, but it is blind to a quiet SLOW burn that sits just under the line and yet,
run long enough, exhausts the entire month's budget. The SLO is breached and no alert ever fired.

Burn rate makes both visible. Burn rate is error_rate divided by the budgeted error rate: how many times
faster than sustainable you are spending. A burn rate of 1 spends the budget exactly over the window; 50
spends it fifty times too fast; 3 spends it three times too fast, which exhausts a month's budget in ten
days. Alerting on burn rate catches the fast burn (huge rate, fires at once) and the slow burn (modest rate
but above sustainable, fires on a longer window) -- because it measures consumption, not instantaneous level.

On this fixture the SLO allows a 0.1% error budget over 720 hours. A fast burn (5% errors for 2 hours) has
burn rate 50 and eats 14% of the month's budget in those 2 hours -- and the raw 1% alert catches it. A slow
burn (0.3% errors for the whole month) has burn rate 3, consumes 300% of the budget (blowing the SLO), and
the raw 1% alert never fires because 0.3% is below 1%. Burn-rate alerting catches both. This computes it.

  --budget     the SLO, the error budget, and the two scenarios
  --burn       each scenario's burn rate, budget consumed, and which alert fires
  --check      the slow burn blows the SLO under the raw threshold; burn-rate alerting catches both

The SLO, thresholds, and scenarios are the fixture; every burn rate is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "slo.json"

BURN_RATE_ALERT = 2.0  # fire if spending the budget more than twice as fast as sustainable


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def error_budget(slo):
    """The fraction of requests the SLO permits to fail."""
    return round(1 - slo, 6)


def burn_rate(error_rate, slo):
    """How many times faster than sustainable the budget is being spent."""
    return round(error_rate / error_budget(slo), 4)


def budget_consumed(scenario, data):
    """Fraction of the whole-window budget this scenario spends (>1 means the SLO is blown)."""
    frac_of_window = scenario["hours"] / data["window_hours"]
    return round(scenario["error_rate"] * frac_of_window / error_budget(data["slo"]), 4)


# ----------------------------------------------------------------- printing

def budget_view(data):
    b = error_budget(data["slo"])
    print("BUDGET — SLO %.1f%% over %d hours" % (data["slo"] * 100, data["window_hours"]))
    print("-" * 52)
    print("  error budget: %.3f%% of requests may fail" % (b * 100))
    print("  raw alert fires at instantaneous error rate > %.1f%%" % (data["raw_alert_rate"] * 100))
    print("  burn-rate alert fires at burn rate > %.1f" % BURN_RATE_ALERT)
    print("-" * 52)
    for name, s in data["scenarios"].items():
        print("  %-10s %.1f%% errors for %d h" % (name, s["error_rate"] * 100, s["hours"]))


def burn_view(data):
    print("BURN — burn rate, budget consumed, and which alert fires")
    print("-" * 68)
    print("  scenario     burn rate   budget used   raw alert   burn alert")
    for name, s in data["scenarios"].items():
        br = burn_rate(s["error_rate"], data["slo"])
        used = budget_consumed(s, data)
        raw = "FIRES" if s["error_rate"] > data["raw_alert_rate"] else "silent"
        burn = "FIRES" if br > BURN_RATE_ALERT else "silent"
        print("  %-10s %8.1f   %10.0f%%   %-9s   %s" % (name, br, used * 100, raw, burn))
    print("-" * 68)
    print("  the slow burn blows the budget (300%) yet the raw alert stays silent; burn-rate catches it.")


def check(data):
    print("SELF-TEST — the slow burn blows the SLO under the raw threshold; burn-rate alerting catches both")
    print("-" * 92)
    slow = data["scenarios"]["slow_burn"]
    fast = data["scenarios"]["fast_burn"]

    slow_blows_budget = budget_consumed(slow, data) > 1.0
    print("  the slow burn exhausts the whole budget = %s (%.0f%% consumed)" % (slow_blows_budget, budget_consumed(slow, data) * 100))

    raw_misses_slow = slow["error_rate"] <= data["raw_alert_rate"]
    print("  the raw threshold never fires on the slow burn = %s (%.1f%% <= %.1f%%)"
          % (raw_misses_slow, slow["error_rate"] * 100, data["raw_alert_rate"] * 100))

    burn_catches_both = burn_rate(slow["error_rate"], data["slo"]) > BURN_RATE_ALERT and burn_rate(fast["error_rate"], data["slo"]) > BURN_RATE_ALERT
    print("  burn-rate alerting fires on both burns = %s (slow %.0f, fast %.0f)"
          % (burn_catches_both, burn_rate(slow["error_rate"], data["slo"]), burn_rate(fast["error_rate"], data["slo"])))

    fast_burns_fast = budget_consumed(fast, data) > 0.1 and fast["hours"] < 24
    print("  the fast burn eats a large chunk of budget quickly = %s (%.0f%% in %d h)"
          % (fast_burns_fast, budget_consumed(fast, data) * 100, fast["hours"]))

    ok = slow_blows_budget and raw_misses_slow and burn_catches_both and fast_burns_fast
    print("-" * 92)
    print("SELF-TEST %s  slow_blows_budget=%s  raw_misses_slow=%s  burn_catches_both=%s  fast_burns_fast=%s"
          % ("PASS" if ok else "FAIL", slow_blows_budget, raw_misses_slow, burn_catches_both, fast_burns_fast))
    return ok


def main():
    p = argparse.ArgumentParser(description="Alert on the error-budget burn rate, not the raw error rate.")
    p.add_argument("--budget", action="store_true")
    p.add_argument("--burn", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("slo=%.3f  window=%dh  raw_alert=%.1f%%  burn_alert=%.1fx  file=%s  (the scenarios are a fixture)"
          % (data["slo"], data["window_hours"], data["raw_alert_rate"] * 100, BURN_RATE_ALERT, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.budget:
        budget_view(data)
    elif args.burn:
        burn_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
