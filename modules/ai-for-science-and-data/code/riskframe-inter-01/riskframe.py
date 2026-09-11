"""Report the absolute risk reduction, not just the relative one -- '50% lower risk' means something different at every baseline.

A treatment's benefit gets reported two ways, and they can sound wildly different for the exact same effect. The RELATIVE
risk reduction is the fraction of the baseline risk that the treatment removes: if 2% of untreated people have the event
and 1% of treated people do, the treatment removed half of the risk, so the relative risk reduction is 50%. That number
is dramatic and technically true, and it is the number headlines and press releases reach for. The ABSOLUTE risk
reduction is the actual drop in the event rate: from 2% to 1% is a drop of 1 percentage point. The relative figure hides
the baseline, and the baseline is what decides whether 'half the risk' is a big deal or a rounding error.

Watch what happens when the same 50% relative reduction sits on two different baselines. On a rare outcome -- 2% down to
1% -- the absolute reduction is 1 percentage point, which means you would have to treat 100 people to prevent a single
event, because 99 of every 100 treated people were never going to have the event anyway and one who would have is now
spared. On a common outcome -- 40% down to 20% -- the same 50% relative reduction is a 20 percentage-point absolute drop,
and you only need to treat 5 people to prevent one event. Identical relative reduction, one is a marginal intervention and
the other is transformative, and the relative number alone cannot tell them apart. The number needed to treat (NNT), the
reciprocal of the absolute reduction, is the honest single number: how many people must take the treatment for one to
benefit.

The rule: a relative risk reduction is meaningless without the baseline it applies to, so always report the absolute risk
reduction (the change in percentage points) and ideally the number needed to treat alongside it -- the same '50% lower'
can be an NNT of 5 or an NNT of 100, and only the absolute framing tells you which. Reporting relative reductions alone is
not wrong arithmetic; it is a framing that systematically makes small effects look large by hiding how rare the event was.

On this fixture two treatments each cut risk by a relative 50%. The rare-outcome treatment (2% to 1%) has an absolute
reduction of 1 point and an NNT of 100; the common-outcome treatment (40% to 20%) has an absolute reduction of 20 points
and an NNT of 5. Same relative number, 20x difference in real benefit. This computes both.

  --risk       each treatment's relative reduction (both 50%), absolute reduction (1pt vs 20pt), and NNT (100 vs 5)
  --headline   what a '50% risk reduction' headline hides: of 10000 treated, how many events are actually prevented
  --check      the relative reduction is identical while the absolute reduction and NNT differ 20-fold -- relative alone is ambiguous

The event counts are the fixture; every relative reduction, absolute reduction, and NNT is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "riskframe.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def relative_reduction(control_events, treated_events):
    """Fraction of the baseline risk removed = (control - treated) / control."""
    return (control_events - treated_events) / control_events


def absolute_reduction(control_events, treated_events, per):
    """Drop in the event rate, in the same units as the risks (a proportion) = (control - treated) / per."""
    return (control_events - treated_events) / per


def number_needed_to_treat(control_events, treated_events, per):
    """How many must be treated to prevent one event = 1 / absolute_reduction = per / (control - treated)."""
    return per / (control_events - treated_events)


def metrics(s):
    c, t, per = s["control_events"], s["treated_events"], s["per"]
    return {
        "control_risk": c / per,
        "treated_risk": t / per,
        "rrr": relative_reduction(c, t),
        "arr": absolute_reduction(c, t, per),
        "nnt": number_needed_to_treat(c, t, per),
        "prevented": c - t,
    }


# ----------------------------------------------------------------- printing

def risk_view(data):
    print("RISK — two treatments, each a 50% RELATIVE reduction, on different baselines")
    print("-" * 82)
    print("  treatment                       baseline  treated   RRR     ARR      NNT")
    for s in data["scenarios"]:
        m = metrics(s)
        print("  %-31s %-9s %-9s %-7s %-8s %g"
              % (s["name"], "%.0f%%" % (m["control_risk"] * 100), "%.0f%%" % (m["treated_risk"] * 100),
                 "%.0f%%" % (m["rrr"] * 100), "%.0f pt" % (m["arr"] * 100), m["nnt"]))
    print("-" * 82)
    print("  same RRR (50%), but ARR and NNT differ 20-fold -- the relative number hid the baseline.")


def headline_view(data):
    print("HEADLINE — what '50% lower risk' means per 10000 people treated")
    print("-" * 74)
    for s in data["scenarios"]:
        m = metrics(s)
        per = s["per"]
        print("  %s:" % s["name"])
        print("    without treatment: %d of %d have the event" % (s["control_events"], per))
        print("    with treatment:    %d of %d have the event" % (s["treated_events"], per))
        print("    events prevented:  %d  (so %d treated people got no benefit; NNT %g)"
              % (m["prevented"], per - m["prevented"], m["nnt"]))
    print("-" * 74)
    print("  '50% reduction' is the same headline for both; the rare case spares 100, the common case spares 2000.")


def check(data):
    print("SELF-TEST — the relative reduction is identical while the absolute reduction and NNT differ 20-fold")
    print("-" * 100)
    rare, common = data["scenarios"][0], data["scenarios"][1]
    mr, mc = metrics(rare), metrics(common)

    same_rrr = abs(mr["rrr"] - mc["rrr"]) < 1e-9
    print("  both treatments have the same relative reduction = %s (%.0f%% vs %.0f%%)"
          % (same_rrr, mr["rrr"] * 100, mc["rrr"] * 100))

    arr_differs = abs(mr["arr"] - mc["arr"]) > 0.1
    print("  the absolute reductions differ = %s (%.0f pt vs %.0f pt)"
          % (arr_differs, mr["arr"] * 100, mc["arr"] * 100))

    rare_nnt_100 = abs(mr["nnt"] - 100) < 1e-9
    print("  rare-outcome NNT = %s (%g)" % (rare_nnt_100, mr["nnt"]))

    common_nnt_5 = abs(mc["nnt"] - 5) < 1e-9
    print("  common-outcome NNT = %s (%g)" % (common_nnt_5, mc["nnt"]))

    relative_alone_ambiguous = same_rrr and mr["nnt"] != mc["nnt"]
    print("  identical RRR maps to different NNT -> relative framing is ambiguous = %s (NNT %g vs %g)"
          % (relative_alone_ambiguous, mr["nnt"], mc["nnt"]))

    ok = same_rrr and arr_differs and rare_nnt_100 and common_nnt_5 and relative_alone_ambiguous
    print("-" * 100)
    print("SELF-TEST %s  same_rrr=%s  arr_differs=%s  rare_nnt_100=%s  common_nnt_5=%s  relative_alone_ambiguous=%s"
          % ("PASS" if ok else "FAIL", same_rrr, arr_differs, rare_nnt_100, common_nnt_5, relative_alone_ambiguous))
    return ok


def main():
    p = argparse.ArgumentParser(description="Absolute vs relative risk: a relative risk reduction is meaningless without its baseline, so the same '50% lower risk' can be a 1-point absolute drop (number needed to treat 100) or a 20-point drop (NNT 5); always report the absolute risk reduction and the NNT, because the relative figure alone systematically makes small effects look large by hiding how rare the event was.")
    p.add_argument("--risk", action="store_true")
    p.add_argument("--headline", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("scenarios=%d  file=%s  (the event counts are a fixture)" % (len(data["scenarios"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.risk:
        risk_view(data)
    elif args.headline:
        headline_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
