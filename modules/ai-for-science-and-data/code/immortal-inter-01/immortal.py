"""Analyze a delayed treatment from a landmark, not from enrollment -- classifying by whether treatment was ever received credits the treated group with immortal (guaranteed-alive) time and invents a benefit.

An observational study compares subjects who got an intervention against those who did not, and the intervention is delivered some time after enrollment: a transplant that becomes available, a medication a patient survives long enough to fill, an award given years into a career. The trap is in how the groups are formed. To be classified as treated, a subject must survive until the intervention -- anyone who dies before then never gets it and lands in the untreated group. So the treated group carries, baked into its definition, a stretch of guaranteed survival before treatment: 'immortal time', during which a treated subject could not have died without ceasing to be treated.

Analyze survival from enrollment (time 0), classifying by whether treatment was ever received, and two errors compound. The treated group is credited with the immortal, death-free time before treatment. And every early death is dumped into the untreated group, because dying early is exactly what disqualified those subjects from treatment. The treated group therefore looks better no matter what the treatment does -- it is made of survivors, measured over time that includes a period they were guaranteed to survive.

The tell is that the effect appears even when the treatment does nothing. If post-treatment survival is genuinely identical between those who took it and comparable subjects who did not, the naive from-enrollment analysis still shows the treated living longer, purely from the immortal time and the survivor selection. That is the fingerprint of a bias, not a benefit.

The fix is a landmark analysis. Choose the time by which treatment status is determined, discard subjects who did not survive to it, classify the survivors by their status at the landmark, and measure survival from the landmark forward. Now the immortal time is excluded (everyone in the comparison was alive at the landmark), the early deaths are excluded from both groups equally, and the two groups are compared only over time in which either could die -- so a treatment that does nothing shows nothing.

The rule: analyze a delayed intervention with a landmark -- restrict to subjects alive at the landmark, classify by status then, and measure survival from there -- not from enrollment by ever-treated status, because the treated group's required survival-to-treatment is immortal time that inflates its apparent benefit even when the treatment has no effect.

On this fixture treatment truly does nothing: post-landmark survival is identical for treated and untreated survivors. The naive ever-treated analysis reports the treated living 2.75 days longer on average; the landmark analysis reports no difference. This computes both.

  --cohort    each subject's group and survival, and which subjects carry immortal time
  --analyze   the naive ever-treated survival difference vs the landmark survival difference
  --check     the naive analysis invents a benefit from immortal time; the landmark analysis shows the true null

landmark and the group death days are the fixture; both survival differences are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "immortal.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mean(xs):
    return sum(xs) / len(xs)


def naive_difference(groups):
    """Classify by ever-treated, measure survival from enrollment (day 0)."""
    treated = groups["treated"]
    untreated = groups["early"] + groups["untreated_survivors"]
    return mean(treated) - mean(untreated), mean(treated), mean(untreated)


def landmark_difference(groups, landmark):
    """Keep survivors to the landmark, classify by status then, measure survival from the landmark."""
    treated = [d - landmark for d in groups["treated"]]
    untreated = [d - landmark for d in groups["untreated_survivors"]]
    return mean(treated) - mean(untreated), mean(treated), mean(untreated)


# ----------------------------------------------------------------- printing

def cohort_view(data):
    groups, L = data["groups"], data["landmark"]
    print("COHORT — each subject's group and survival (landmark day = %d)" % L)
    print("-" * 62)
    print("  group                 death days   survived to landmark?")
    for name in ("early", "treated", "untreated_survivors"):
        days = groups[name]
        survived = all(d > L for d in days)
        print("  %-20s  %-11s  %s" % (name, days, survived))
    print("-" * 62)
    print("  the treated group all survived past day %d — that guaranteed survival is 'immortal time'" % L)


def analyze_view(data):
    groups, L = data["groups"], data["landmark"]
    n_diff, n_t, n_u = naive_difference(groups)
    l_diff, l_t, l_u = landmark_difference(groups, L)
    print("ANALYZE — naive (ever-treated, from enrollment) vs landmark (survivors, from landmark)")
    print("-" * 74)
    print("  naive:     treated mean %.2f, untreated mean %.2f, difference %+.2f" % (n_t, n_u, n_diff))
    print("  landmark:  treated mean %.2f, untreated mean %.2f, difference %+.2f" % (l_t, l_u, l_diff))
    print("-" * 74)
    print("  the naive analysis shows a survival benefit; the landmark analysis shows none")


def check(data):
    print("SELF-TEST — the naive analysis invents a benefit from immortal time; the landmark analysis shows the true null")
    print("-" * 122)
    groups, L = data["groups"], data["landmark"]
    n_diff, n_t, n_u = naive_difference(groups)
    l_diff, l_t, l_u = landmark_difference(groups, L)

    treated_are_survivors = all(d > L for d in groups["treated"])
    print("  every treated subject survived to the landmark (immortal time) = %s (all death days > %d)" % (treated_are_survivors, L))

    early_deaths_untreated = all(d <= L for d in groups["early"])
    print("  subjects who died before the landmark are all untreated = %s" % early_deaths_untreated)

    naive_shows_benefit = n_diff > 0
    print("  the naive ever-treated analysis shows a survival benefit = %s (%+.2f days)" % (naive_shows_benefit, n_diff))

    landmark_shows_no_effect = abs(l_diff) < 1e-9
    print("  the landmark analysis shows no effect (the truth) = %s (%+.2f days)" % (landmark_shows_no_effect, l_diff))

    bias_removed = naive_shows_benefit and landmark_shows_no_effect
    print("  the benefit was an immortal-time artifact, removed by landmarking = %s" % bias_removed)

    ok = (treated_are_survivors and early_deaths_untreated and naive_shows_benefit
          and landmark_shows_no_effect and bias_removed)
    print("-" * 122)
    print("SELF-TEST %s  treated_are_survivors=%s  early_deaths_untreated=%s  naive_shows_benefit=%s  landmark_shows_no_effect=%s  bias_removed=%s"
          % ("PASS" if ok else "FAIL", treated_are_survivors, early_deaths_untreated, naive_shows_benefit, landmark_shows_no_effect, bias_removed))
    return ok


def main():
    p = argparse.ArgumentParser(description="Immortal time bias: analyze a delayed intervention with a landmark -- restrict to subjects alive at the landmark, classify by status then, and measure survival from there -- not from enrollment by ever-treated status, because the treated group's required survival-to-treatment is immortal time that inflates its apparent benefit even when the treatment has no effect.")
    p.add_argument("--cohort", action="store_true")
    p.add_argument("--analyze", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("landmark=%d  groups=%s  file=%s  (the cohort is a fixture)"
          % (data["landmark"], {k: len(v) for k, v in data["groups"].items()}, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.cohort:
        cohort_view(data)
    elif args.analyze:
        analyze_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
