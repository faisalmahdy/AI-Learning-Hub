"""Judge screening by mortality, not survival-from-diagnosis -- detecting a disease earlier inflates survival without saving anyone.

Screening programs are almost always defended with a survival statistic: 'patients whose cancer was caught by screening
survive 6 years on average, versus 2 years for those caught by symptoms -- screening triples survival.' That comparison
is one of the most persistent traps in medical statistics, because 'survival from diagnosis' starts its clock at the
moment of diagnosis, and screening's entire job is to move that moment earlier. If a disease will kill a patient at a
fixed time no matter when it is found, then detecting it earlier does not add a single day to their life -- it only starts
the survival clock sooner, so the measured 'survival from diagnosis' gets longer while the date of death does not move at
all. The extra survival is an artifact of the earlier start, not a benefit, and it has a name: LEAD TIME, the interval by
which screening advances the diagnosis.

The mechanism is worth being precise about. Say a patient would be diagnosed from symptoms at year 8 and dies at year 10:
survival from diagnosis is 2 years. Now screen the same patient and catch the disease at year 4; they still die at year
10, so survival from diagnosis is now 6 years. Nothing about the patient's life changed -- same death, same everything --
but the survival statistic tripled, purely because the clock started 4 years earlier. That 4 years is the lead time, and
it is added to every screened patient's measured survival whether or not screening does them any good. So a screened group
will ALWAYS show longer survival-from-diagnosis than an unscreened group, even for a disease that screening cannot treat
at all, which means survival-from-diagnosis cannot distinguish a screening program that saves lives from one that saves
none.

The fix is to measure the thing screening is supposed to change: MORTALITY -- the rate of death in the whole population
over a fixed calendar period, or equivalently the age at death -- not survival timed from diagnosis. Mortality is immune to
lead time because it is anchored to the calendar and the population, not to the moment of diagnosis: if screening does not
postpone death, the death rate is unchanged, and the honest statistic says so. Only a randomized comparison of mortality
between screened and unscreened populations can tell whether earlier detection actually helps; survival-from-diagnosis,
however dramatic, is contaminated by lead time (and by length bias, its companion) and cannot.

The rule: evaluate a screening program by mortality (deaths per population over calendar time), never by survival measured
from the date of diagnosis, because screening advances the diagnosis date by a lead time that inflates survival-from-
diagnosis even when the date of death -- and thus the real benefit -- does not change at all.

On this fixture three patients each would be diagnosed from symptoms 4 years after screening would catch them, and each
dies at a fixed time regardless. Survival from the screen date averages 6 years; survival from the symptom date averages 2
years; the 4-year difference is exactly the lead time, and the ages at death are identical either way. This computes both.

  --survival   each patient's survival measured from the screen date vs the symptom date, and the two means (6 vs 2)
  --leadtime   the inflation equals the lead time exactly, while the ages at death are unchanged -- no life was extended
  --check      survival-from-diagnosis is longer under screening purely by the lead time; mortality (age at death) is unchanged

The patient event times are the fixture; every survival duration, mean, and lead time is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "leadtime.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def survival_from_screen(p):
    return p["death"] - p["screen_detect"]


def survival_from_symptom(p):
    return p["death"] - p["symptom_detect"]


def lead_time(p):
    """How much earlier screening detects the disease than symptoms would -- the interval added to measured survival."""
    return p["symptom_detect"] - p["screen_detect"]


def mean(xs):
    return sum(xs) / len(xs)


# ----------------------------------------------------------------- printing

def survival_view(data):
    patients = data["patients"]
    print("SURVIVAL — from the screen date vs the symptom date (death is the same either way)")
    print("-" * 78)
    print("  patient  screen  symptom  death   survival-from-screen   survival-from-symptom")
    for p in patients:
        print("  %-7s  %-6d  %-7d  %-6d  %-21d  %d"
              % (p["id"], p["screen_detect"], p["symptom_detect"], p["death"],
                 survival_from_screen(p), survival_from_symptom(p)))
    print("-" * 78)
    print("  mean survival-from-screen  = %.1f years  <- the screening headline"
          % mean([survival_from_screen(p) for p in patients]))
    print("  mean survival-from-symptom = %.1f years  <- the no-screening baseline"
          % mean([survival_from_symptom(p) for p in patients]))


def leadtime_view(data):
    patients = data["patients"]
    print("LEADTIME — the survival 'gain' is exactly the lead time; nobody died later")
    print("-" * 70)
    print("  patient  lead time (symptom-screen)   age at death   survival inflation")
    for p in patients:
        infl = survival_from_screen(p) - survival_from_symptom(p)
        print("  %-7s  %-26d  %-13d  %d" % (p["id"], lead_time(p), p["death"], infl))
    print("-" * 70)
    print("  mean lead time = %.1f;  mean survival inflation = %.1f;  mean age at death = %.1f (unchanged)"
          % (mean([lead_time(p) for p in patients]),
             mean([survival_from_screen(p) - survival_from_symptom(p) for p in patients]),
             mean([p["death"] for p in patients])))


def check(data):
    print("SELF-TEST — survival-from-diagnosis is longer under screening purely by the lead time; mortality is unchanged")
    print("-" * 108)
    patients = data["patients"]
    mean_screen = mean([survival_from_screen(p) for p in patients])
    mean_symptom = mean([survival_from_symptom(p) for p in patients])
    mean_lead = mean([lead_time(p) for p in patients])

    screen_survival_longer = mean_screen > mean_symptom
    print("  survival-from-screen beats survival-from-symptom = %s (%.1f vs %.1f years)"
          % (screen_survival_longer, mean_screen, mean_symptom))

    inflation_is_lead_time = abs((mean_screen - mean_symptom) - mean_lead) < 1e-9
    print("  the survival inflation equals the lead time exactly = %s (%.1f = %.1f)"
          % (inflation_is_lead_time, mean_screen - mean_symptom, mean_lead))

    deaths_unchanged = all(survival_from_screen(p) - survival_from_symptom(p) == lead_time(p) for p in patients)
    print("  earlier detection did not move any death (inflation = lead time per patient) = %s" % deaths_unchanged)

    screening_triples_survival = abs(mean_screen / mean_symptom - 3.0) < 1e-9
    print("  the headline: screening 'triples' survival = %s (%.1f / %.1f = %.1f)"
          % (screening_triples_survival, mean_screen, mean_symptom, mean_screen / mean_symptom))

    horizon = 12
    mortality = sum(1 for p in patients if p["death"] <= horizon)
    mortality_shows_no_benefit = mortality == len(patients)
    print("  the honest metric: dead by year %d = %d of %d (screening or not) -> no benefit = %s"
          % (horizon, mortality, len(patients), mortality_shows_no_benefit))

    ok = screen_survival_longer and inflation_is_lead_time and deaths_unchanged and screening_triples_survival and mortality_shows_no_benefit
    print("-" * 108)
    print("SELF-TEST %s  screen_survival_longer=%s  inflation_is_lead_time=%s  deaths_unchanged=%s  screening_triples_survival=%s  mortality_shows_no_benefit=%s"
          % ("PASS" if ok else "FAIL", screen_survival_longer, inflation_is_lead_time, deaths_unchanged, screening_triples_survival, mortality_shows_no_benefit))
    return ok


def main():
    p = argparse.ArgumentParser(description="Lead-time bias: evaluate a screening program by mortality (deaths per population over calendar time), never by survival measured from the date of diagnosis, because screening advances the diagnosis by a lead time that inflates survival-from-diagnosis even when the date of death -- and thus the real benefit -- does not change at all.")
    p.add_argument("--survival", action="store_true")
    p.add_argument("--leadtime", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("patients=%d  file=%s  (the patient event times are a fixture)" % (len(data["patients"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.survival:
        survival_view(data)
    elif args.leadtime:
        leadtime_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
