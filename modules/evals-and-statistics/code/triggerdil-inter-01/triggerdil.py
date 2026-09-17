"""Measure an A/B effect on the users who actually triggered the feature, not on everyone assigned -- otherwise the effect is diluted toward zero by users the change never touched.

Many experiments test a change that only fires on a code path a minority of users reach: a new checkout flow only for users who reach checkout, a fix for an error only some sessions hit, a recommendation shown only when a particular shelf renders. Users who never trigger the feature are, by construction, unaffected -- their metric is identical in the treatment and control arms, because from their perspective nothing changed. They are dead weight in the comparison.

Average the metric over every assigned user and that dead weight silently taxes the result. The real effect lives entirely in the triggered minority, but the mean spreads it across the whole assigned population, so the measured lift is the true effect multiplied by the trigger rate. A genuine +0.20 improvement among the 20% who trigger shows up as a diluted +0.04 over all users -- five times too small. That diluted number is easy to dismiss as noise, and easy to fail to power for: you sized the experiment expecting +0.20 and are trying to detect +0.04, so the test comes back inconclusive and a real, large effect is declared a non-result.

The fix is trigger-based analysis. Log the trigger condition in BOTH arms -- not just where the feature fires, but wherever a user MEETS the condition that would fire it -- so you can identify the control users who would have triggered had they been in treatment. Then compute the effect only among triggered users in treatment versus would-have-triggered users in control. That comparison is still a valid randomized experiment (triggering is determined by user behavior, not by the treatment, so the two triggered groups are comparable), and it recovers the true effect on the population the change can actually move.

The rule: analyze the effect on the triggered population -- users who experienced the feature in treatment versus users who met the same trigger condition in control -- not on all assigned users, because unaffected non-triggering users dilute the measured effect by the trigger rate, shrinking a real effect toward zero and toward non-significance.

On this fixture 20% of users trigger; the true effect among them is +0.20 conversion, but averaged over everyone it dilutes to +0.04 -- exactly the trigger rate times the true effect. This computes both.

  --populations   each arm's users and conversions, split by whether they triggered the feature
  --effect        the overall (all-users, diluted) effect vs the triggered-only effect, and the dilution
  --check         the all-users effect is diluted by the trigger rate; the triggered-only effect recovers the true lift

all counts and conversions are the fixture; every rate, the diluted and triggered effects, and the dilution relationship are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "triggerdil.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def rate(cell):
    return cell["conv"] / cell["n"]


def arm_totals(arm):
    n = arm["triggered"]["n"] + arm["not_triggered"]["n"]
    conv = arm["triggered"]["conv"] + arm["not_triggered"]["conv"]
    return n, conv


def overall_rate(arm):
    n, conv = arm_totals(arm)
    return conv / n


def trigger_rate(arm):
    n, _ = arm_totals(arm)
    return arm["triggered"]["n"] / n


# ----------------------------------------------------------------- printing

def populations_view(data):
    t, c = data["treatment"], data["control"]
    print("POPULATIONS — users and conversions by arm and trigger status")
    print("-" * 66)
    print("  arm        group          n    conv   rate")
    for name, arm in (("treatment", t), ("control", c)):
        for grp in ("triggered", "not_triggered"):
            cell = arm[grp]
            print("  %-9s  %-13s  %-3d  %-4d   %.2f" % (name, grp, cell["n"], cell["conv"], rate(cell)))
    print("-" * 66)
    print("  non-triggered users convert identically in both arms — the feature never touched them")


def effect_view(data):
    t, c = data["treatment"], data["control"]
    diluted = overall_rate(t) - overall_rate(c)
    triggered = rate(t["triggered"]) - rate(c["triggered"])
    tr = trigger_rate(t)
    print("EFFECT — all-users (diluted) vs triggered-only")
    print("-" * 60)
    print("  overall treatment rate = %.2f, control rate = %.2f" % (overall_rate(t), overall_rate(c)))
    print("  all-users (diluted) effect        = %+.2f" % diluted)
    print("  triggered-only effect (the truth) = %+.2f" % triggered)
    print("  trigger rate                      = %.2f" % tr)
    print("  trigger_rate x triggered_effect   = %+.2f  (equals the diluted effect)" % (tr * triggered))
    print("-" * 60)
    print("  averaging over everyone shrinks the +%.2f effect to +%.2f — %dx too small" % (triggered, diluted, round(triggered / diluted)))


def check(data):
    print("SELF-TEST — the all-users effect is diluted by the trigger rate; the triggered-only effect recovers the true lift")
    print("-" * 118)
    t, c = data["treatment"], data["control"]
    diluted = overall_rate(t) - overall_rate(c)
    triggered = rate(t["triggered"]) - rate(c["triggered"])
    nontrig = rate(t["not_triggered"]) - rate(c["not_triggered"])
    tr = trigger_rate(t)

    only_fraction_triggers = tr < 1.0
    print("  only a fraction of users trigger the feature = %s (%.0f%%)" % (only_fraction_triggers, 100 * tr))

    nontriggered_unaffected = abs(nontrig) < 1e-9
    print("  non-triggered users are unaffected (zero effect) = %s (%+.2f)" % (nontriggered_unaffected, nontrig))

    diluted_understates = abs(diluted) < abs(triggered)
    print("  the all-users effect understates the true effect = %s (%+.2f vs %+.2f)" % (diluted_understates, diluted, triggered))

    dilution_matches_rate = abs(diluted - tr * triggered) < 1e-9
    print("  the diluted effect equals trigger_rate x true effect = %s (%.2f x %+.2f = %+.2f)" % (dilution_matches_rate, tr, triggered, tr * triggered))

    triggered_recovers = abs(triggered - 0.20) < 1e-9
    print("  the triggered-only analysis recovers the true +0.20 effect = %s (%+.2f)" % (triggered_recovers, triggered))

    ok = (only_fraction_triggers and nontriggered_unaffected and diluted_understates
          and dilution_matches_rate and triggered_recovers)
    print("-" * 118)
    print("SELF-TEST %s  only_fraction_triggers=%s  nontriggered_unaffected=%s  diluted_understates=%s  dilution_matches_rate=%s  triggered_recovers=%s"
          % ("PASS" if ok else "FAIL", only_fraction_triggers, nontriggered_unaffected, diluted_understates, dilution_matches_rate, triggered_recovers))
    return ok


def main():
    p = argparse.ArgumentParser(description="Trigger dilution: analyze the effect on the triggered population (users who experienced the feature in treatment vs users who met the same trigger condition in control), not on all assigned users, because unaffected non-triggering users dilute the measured effect by the trigger rate, shrinking a real effect toward zero and toward non-significance.")
    p.add_argument("--populations", action="store_true")
    p.add_argument("--effect", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    tn, _ = arm_totals(data["treatment"])
    cn, _ = arm_totals(data["control"])
    print("treatment_n=%d  control_n=%d  file=%s  (the counts are a fixture)" % (tn, cn, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.populations:
        populations_view(data)
    elif args.effect:
        effect_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
