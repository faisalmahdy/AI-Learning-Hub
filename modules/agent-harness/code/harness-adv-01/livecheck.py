#!/usr/bin/env python3
"""A scheduled eval that trends over time and alarms on a real regression.

A live eval runs the same task suite against the production model on a schedule
and appends one dated row per run. The runbook version stops there -- a human
squints at the numbers. This turns the squint into a rule: a p-chart (a control
chart for a pass/fail proportion). Freeze a baseline band from the first few
stable weeks, then alarm when a later run breaches the lower limit OR a run of
weeks sits below the baseline center. The band is 3 sigma of a proportion,
sigma = sqrt(p*(1-p)/n) -- the same "state the spread" discipline as the evals
track, pointed at a time series instead of a leaderboard.

  --trend    the weekly pass rate against the frozen baseline band
  --alarm    the correct detector: which week the regression is caught
  --naive    the "alarm if it dropped since last week" detector (the false-alarm storm)
  --bug      a chart that recomputes its limits over ALL history (baseline contamination)
  --check    limits match the closed form; the bug goes silent; deterministic

Stdlib only (math.sqrt). No network, no model calls -- the twelve runs are a
fixture in ledger.json. Point it at your own dated runs.
"""
import argparse
import json
import sys
from math import sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "ledger.json"

BASE = 6          # weeks used to freeze the baseline band (the stable period)
SIGMA = 3.0       # control-limit width, in standard errors
SHIFT = 5         # consecutive weeks below center that count as a sustained shift


def load():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    runs = data["runs"]
    for r in runs:
        r["rate"] = r["passed"] / r["n"]
    return runs


# ------------------------------------------------------- the control limits

def limits(runs):
    """Freeze the baseline: center and 3-sigma band from the first BASE weeks.

    sigma of a proportion over n tasks is sqrt(p*(1-p)/n) -- the binomial
    standard error. The band is center +/- SIGMA*sigma. Frozen: computed once,
    from the clean period, and never moved by later weeks."""
    base = runs[:BASE]
    passed = sum(r["passed"] for r in base)
    n = sum(r["n"] for r in base)
    center = passed / n
    per_run_n = n / len(base)                      # avg tasks per run
    se = sqrt(center * (1 - center) / per_run_n)
    return center, center - SIGMA * se, center + SIGMA * se, se


# --------------------------------------------------------------- detectors

def alarm_measured(runs):
    """Two rules on the FROZEN band: a point below the lower limit, or SHIFT
    weeks in a row below center. Returns the first alarming week or None."""
    center, lcl, ucl, _ = limits(runs)
    below_streak = 0
    for i, r in enumerate(runs):
        if r["rate"] < center:
            below_streak += 1
        else:
            below_streak = 0
        point = r["rate"] < lcl
        shift = below_streak >= SHIFT
        if point or shift:
            why = "point < LCL" if point else "%d wk run below center" % SHIFT
            return i, why
    return None, None


def alarm_naive(runs):
    """The trap: alarm on any week whose rate dropped since the week before.
    Returns the list of alarming week indices."""
    hits = []
    for i in range(1, len(runs)):
        if runs[i]["rate"] < runs[i - 1]["rate"]:
            hits.append(i)
    return hits


def alarm_contaminated(runs):
    """THE BUG: recompute the band over ALL weeks seen so far, every week, so the
    regression is folded into its own baseline. Returns the first alarm or None."""
    for i in range(BASE, len(runs)):
        seen = runs[: i + 1]                       # <- includes the regressed weeks
        passed = sum(r["passed"] for r in seen)
        n = sum(r["n"] for r in seen)
        center = passed / n
        per_run_n = n / len(seen)
        se = sqrt(center * (1 - center) / per_run_n)
        lcl = center - SIGMA * se
        if runs[i]["rate"] < lcl:
            return i, lcl
    return None, None


# ---------------------------------------------------------------- printing

def bar(rate, lo=0.40, hi=1.00, width=28):
    k = int(round((rate - lo) / (hi - lo) * width))
    k = max(0, min(width, k))
    return "#" * k + "-" * (width - k)


def trend(runs):
    center, lcl, ucl, se = limits(runs)
    print("WEEKLY TREND — pass rate vs the frozen baseline band")
    print("  baseline = first %d weeks   center %.3f   LCL %.3f   UCL %.3f   (3 sigma, se %.4f)"
          % (BASE, center, lcl, ucl, se))
    print("-" * 72)
    for i, r in enumerate(runs):
        flag = "  <-- below LCL" if r["rate"] < lcl else ""
        band = "base" if i < BASE else " "
        print("  wk%02d %s  %s  %2d/%d = %.2f  %s%s"
              % (i + 1, r["date"], band, r["passed"], r["n"], r["rate"], bar(r["rate"]), flag))
    print("-" * 72)
    print("  the band is frozen from weeks 1-%d; weeks 7-12 are a model swap." % BASE)


def alarm(runs):
    center, lcl, ucl, _ = limits(runs)
    print("THE ALARM — frozen band, two rules (point < LCL, or %d weeks below center)" % SHIFT)
    print("  center %.3f   LCL %.3f" % (center, lcl))
    print("-" * 72)
    wk, why = alarm_measured(runs)
    if wk is None:
        print("  no regression flagged.")
    else:
        r = runs[wk]
        print("  ALARM at wk%02d (%s): rate %.2f  --  %s"
              % (wk + 1, r["date"], r["rate"], why))
        print("  caught the model swap the first week it showed, with zero baseline alarms.")


def naive(runs):
    print("THE NAIVE DETECTOR — alarm if this week dropped vs last week (the trap)")
    print("-" * 72)
    hits = alarm_naive(runs)
    for i in hits:
        era = "baseline" if i < BASE else "regression"
        print("  ALARM at wk%02d %s: %.2f -> %.2f  (%s)"
              % (i + 1, runs[i]["date"], runs[i - 1]["rate"], runs[i]["rate"], era))
    print("-" * 72)
    base_hits = [i for i in hits if i < BASE]
    print("  %d alarms total, %d of them in the stable baseline. A detector that cries"
          % (len(hits), len(base_hits)))
    print("  wolf every ordinary down-week is one the on-call learns to ignore.")


def check(runs):
    print("SELF-TEST — closed-form limits, the contamination bug, determinism")
    print("-" * 72)
    center, lcl, ucl, se = limits(runs)

    # closed form: sigma of a proportion is sqrt(p(1-p)/n).
    hand_se = sqrt(0.80 * 0.20 / 50)
    se_ok = abs(se - hand_se) < 1e-9 and abs(center - 0.80) < 1e-9
    print("  baseline center = %.3f, se = %.4f, hand-computed se = %.4f, agree = %s"
          % (center, se, hand_se, se_ok))
    print("  frozen LCL = %.3f  (regression weeks sit at ~0.60-0.64)" % lcl)

    # the correct detector catches the swap on the first regressed week.
    wk, why = alarm_measured(runs)
    caught_early = wk == BASE          # week index BASE == the 7th week (0-based)
    print("  correct detector alarms at wk%02d (%s) = first regressed week is %s"
          % (wk + 1, why, caught_early))

    # the bug: recomputing over all history swallows the regression -> no alarm.
    bwk, blcl = alarm_contaminated(runs)
    bug_silent = bwk is None
    print("  contaminated detector: %s (its LCL sinks below the regressed weeks)"
          % ("no alarm" if bug_silent else "alarm at wk%02d" % (bwk + 1)))
    # show how far the contaminated limit has sunk by the final week.
    seen = runs
    p_all = sum(r["passed"] for r in seen) / sum(r["n"] for r in seen)
    se_all = sqrt(p_all * (1 - p_all) / (sum(r["n"] for r in seen) / len(seen)))
    print("  by wk12 the contaminated LCL = %.3f vs the frozen LCL = %.3f"
          % (p_all - SIGMA * se_all, lcl))

    # determinism: the fixture yields identical limits twice.
    c2, l2, u2, s2 = limits(load())
    deterministic = (center, lcl, ucl) == (c2, l2, u2)

    ok = se_ok and caught_early and bug_silent and deterministic
    print("-" * 72)
    print("SELF-TEST %s  closed_form=%s  caught_early=%s  bug_silent=%s  deterministic=%s"
          % ("PASS" if ok else "FAIL", se_ok, caught_early, bug_silent, deterministic))
    return ok


def main():
    p = argparse.ArgumentParser(description="A scheduled eval as a p-chart with a regression alarm.")
    for flag in ("trend", "alarm", "naive", "bug", "check"):
        p.add_argument("--" + flag, action="store_true")
    args = p.parse_args()

    runs = load()
    print("weeks=%d  n/run=%d  baseline=first %d  file=%s  (runs are a fixture)"
          % (len(runs), runs[0]["n"], BASE, LEDGER.name))
    print("")

    if args.check:
        return 0 if check(runs) else 1
    if args.trend:
        trend(runs)
    elif args.alarm:
        alarm(runs)
    elif args.naive:
        naive(runs)
    elif args.bug:
        wk, lcl = alarm_contaminated(runs)
        print("THE BUG — recompute the band over all history, every week")
        print("-" * 72)
        if wk is None:
            print("  no alarm, ever: the regressed weeks were folded into the baseline,")
            print("  the band widened and drooped to cover them, and the chart went quiet")
            print("  exactly when it should have screamed. The baseline must stay frozen.")
        else:
            print("  alarm at wk%02d (LCL %.3f)" % (wk + 1, lcl))
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
