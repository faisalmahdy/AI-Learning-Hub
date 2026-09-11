"""Screen-detected cases survive longer partly because screening skims the slow ones -- length-time bias, not benefit.

A screening program finds disease before symptoms, and the patients it finds often live longer than patients diagnosed after symptoms appear. That looks like proof the screening works. But some of that survival gap is built in by WHICH cases screening tends to catch, independent of any benefit -- and telling the two apart is the whole problem with evaluating screening by comparing screen-detected to symptom-detected survival.

The mechanism is length-time bias. Disease cases vary in how fast they progress: aggressive cases move quickly from undetectable to symptomatic, spending only a short time in the window where a screen could catch them; indolent cases linger in that detectable-but-asymptomatic window for a long time. A screening program that tests the population at points in time is far more likely to catch a case during a long window than a short one -- so screen-detected cases are disproportionately the slow, indolent ones. And slow, indolent cases have better survival to begin with, for reasons that have nothing to do with being screened. The screen-detected group is thus ENRICHED for good-prognosis cases: it looks like screening extends life when part of the effect is just that screening preferentially picks the cases that were going to do well anyway.

The tell is composition. Compare the mix of case types in the screen-detected group to the mix in the whole population: if screening detected a much higher share of slow cases than exist in the population, the survival advantage is at least partly length-time bias, not benefit. The screen-detected mean can even exceed the overall population mean while screening helps no one, because it is a biased sample of the healthiest-prognosis cases. Evaluating screening honestly requires comparing outcomes at the population level -- ideally disease-specific mortality in a randomized trial (screened vs not-screened whole populations) -- not survival among the cases each method happened to detect.

The rule: do not judge a screening program by comparing survival of screen-detected cases to symptom-detected cases, because screening preferentially catches slow-progressing cases (they spend longer in the detectable window) and those have better prognosis anyway -- so the screen-detected group is enriched for good-prognosis cases and appears to survive longer even when screening provides no benefit; judge screening by population-level mortality instead.

On this fixture fast cases (short window, survival 2) and slow cases (long window, survival 8) are equal in the population (50/50). Screening detects slow cases at three times the rate of fast ones, so the screen-detected group is 75% slow and shows mean survival 6.5 -- far above the clinically-detected 3.5 and the population 5 -- purely from enrichment. This computes both.

  --detect    how many of each case type screening detects vs leaves for clinical (symptom) detection
  --survival  the mean survival of screen-detected vs clinically-detected vs the whole population, and the slow-case share of each
  --check     screen-detected survival exceeds clinical and population survival purely because screening enriches for slow cases

groups and the detection rate are the fixture; every detected count, composition, and mean survival is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "lengthbias.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def detection_prob(window, rate):
    """Screening detects a case with probability proportional to its detectable window."""
    return window * rate


def screen_detected(groups, rate):
    """Count of each type detected by screening (count * detection prob)."""
    return {k: g["count"] * detection_prob(g["window"], rate) for k, g in groups.items()}


def clinical_detected(groups, rate):
    """Count of each type NOT caught by screening, detected later by symptoms."""
    return {k: g["count"] - g["count"] * detection_prob(g["window"], rate) for k, g in groups.items()}


def mean_survival(groups, counts):
    """Mean survival over a set of per-type counts."""
    total = sum(counts.values())
    return sum(groups[k]["survival"] * counts[k] for k in counts) / total if total else 0.0


def slow_share(counts):
    total = sum(counts.values())
    return counts["slow"] / total if total else 0.0


def population_counts(groups):
    return {k: g["count"] for k, g in groups.items()}


# ----------------------------------------------------------------- printing

def detect_view(data):
    groups, rate = data["groups"], data["screen_detection_rate_per_window"]
    sd = screen_detected(groups, rate)
    cd = clinical_detected(groups, rate)
    print("DETECT — who screening catches (rate %.2f per unit window)" % rate)
    print("-" * 60)
    print("  type  window  detection prob   population   screen-detected   clinical")
    for k, g in groups.items():
        print("  %-4s  %-6d  %-14.2f   %-10d   %-15.1f   %.1f" % (k, g["window"], detection_prob(g["window"], rate), g["count"], sd[k], cd[k]))
    print("-" * 60)
    print("  screening catches slow cases at %.0fx the rate of fast (window ratio)" % (detection_prob(groups["slow"]["window"], rate) / detection_prob(groups["fast"]["window"], rate)))


def survival_view(data):
    groups, rate = data["groups"], data["screen_detection_rate_per_window"]
    sd = screen_detected(groups, rate)
    cd = clinical_detected(groups, rate)
    pop = population_counts(groups)
    print("SURVIVAL — mean survival and slow-case share by detection route")
    print("-" * 66)
    print("  screen-detected: mean %.1f years, %.0f%% slow cases" % (mean_survival(groups, sd), 100 * slow_share(sd)))
    print("  clinical (symptom): mean %.1f years, %.0f%% slow cases" % (mean_survival(groups, cd), 100 * slow_share(cd)))
    print("  whole population:   mean %.1f years, %.0f%% slow cases" % (mean_survival(groups, pop), 100 * slow_share(pop)))
    print("-" * 66)
    print("  screen-detected 'survives longer' -- but it is enriched for slow (good-prognosis) cases")


def check(data):
    print("SELF-TEST — screen-detected survival exceeds clinical and population survival purely because screening enriches for slow cases")
    print("-" * 128)
    groups, rate = data["groups"], data["screen_detection_rate_per_window"]
    sd = screen_detected(groups, rate)
    cd = clinical_detected(groups, rate)
    pop = population_counts(groups)
    sd_mean, cd_mean, pop_mean = mean_survival(groups, sd), mean_survival(groups, cd), mean_survival(groups, pop)

    slow_detected_more = detection_prob(groups["slow"]["window"], rate) > detection_prob(groups["fast"]["window"], rate)
    print("  screening detects slow cases at a higher rate than fast = %s (%.2f > %.2f)"
          % (slow_detected_more, detection_prob(groups["slow"]["window"], rate), detection_prob(groups["fast"]["window"], rate)))

    screen_enriched_for_slow = slow_share(sd) > slow_share(pop)
    print("  the screen-detected group is enriched for slow cases = %s (%.0f%% vs %.0f%% in population)" % (screen_enriched_for_slow, 100 * slow_share(sd), 100 * slow_share(pop)))

    screen_beats_clinical = sd_mean > cd_mean
    print("  screen-detected survival exceeds clinically-detected = %s (%.1f > %.1f)" % (screen_beats_clinical, sd_mean, cd_mean))

    screen_beats_population = sd_mean > pop_mean
    print("  screen-detected survival even exceeds the population mean = %s (%.1f > %.1f)" % (screen_beats_population, sd_mean, pop_mean))

    survival_per_type_unchanged = groups["fast"]["survival"] == 2 and groups["slow"]["survival"] == 8
    print("  no case's survival was changed by screening (same per-type survival) = %s" % survival_per_type_unchanged)

    gap_is_composition = abs(slow_share(sd) - slow_share(pop)) > 0.2
    print("  the survival gap comes from group composition, not benefit = %s (slow share shifted %.0f%%->%.0f%%)"
          % (gap_is_composition, 100 * slow_share(pop), 100 * slow_share(sd)))

    ok = (slow_detected_more and screen_enriched_for_slow and screen_beats_clinical and screen_beats_population
          and survival_per_type_unchanged and gap_is_composition)
    print("-" * 128)
    print("SELF-TEST %s  slow_detected_more=%s  screen_enriched_for_slow=%s  screen_beats_clinical=%s  screen_beats_population=%s  survival_per_type_unchanged=%s  gap_is_composition=%s"
          % ("PASS" if ok else "FAIL", slow_detected_more, screen_enriched_for_slow, screen_beats_clinical, screen_beats_population, survival_per_type_unchanged, gap_is_composition))
    return ok


def main():
    p = argparse.ArgumentParser(description="Length-time bias: do not judge a screening program by comparing survival of screen-detected cases to symptom-detected cases, because screening preferentially catches slow-progressing cases (they spend longer in the detectable window) and those have better prognosis anyway -- so the screen-detected group is enriched for good-prognosis cases and appears to survive longer even when screening provides no benefit; judge screening by population-level mortality instead.")
    p.add_argument("--detect", action="store_true")
    p.add_argument("--survival", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("groups=%s  screen_rate=%.2f  file=%s  (the case types and detection rate are a fixture)"
          % ({k: v["count"] for k, v in data["groups"].items()}, data["screen_detection_rate_per_window"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.detect:
        detect_view(data)
    elif args.survival:
        survival_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
