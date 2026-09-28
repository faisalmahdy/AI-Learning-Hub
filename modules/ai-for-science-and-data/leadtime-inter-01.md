---
id: leadtime-inter-01
title: Judge screening by mortality, not survival-from-diagnosis — detecting a disease earlier inflates survival without saving anyone
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: Screening programs are almost always defended with a survival statistic — "cancers caught by screening survive 6 years on average, versus 2 for those caught by symptoms, so screening triples survival." That comparison is one of the most persistent traps in medical statistics, because survival-from-diagnosis starts its clock at the moment of diagnosis, and screening's entire job is to move that moment earlier. If a disease kills a patient at a fixed time no matter when it is found, detecting it earlier adds not one day to their life — it only starts the survival clock sooner, so measured survival-from-diagnosis grows while the date of death does not move. The extra survival is an artifact called lead time, the interval by which screening advances the diagnosis. A patient diagnosed from symptoms at year 8 who dies at year 10 has 2 years of survival; screen the same patient, catch it at year 4, they still die at year 10, and survival "becomes" 6 years — tripled, with nothing about their life changed. A screened group therefore always shows longer survival-from-diagnosis than an unscreened group, even for a disease screening cannot treat, so survival-from-diagnosis cannot tell a life-saving program from a useless one. The fix is to measure mortality — deaths per population over calendar time — which is anchored to the calendar, not the diagnosis, and so is immune to lead time. On a fixture of three patients each detected 4 years earlier by screening but dying at a fixed time, survival-from-screen averages 6 years and survival-from-symptom 2 years, the 4-year gap is exactly the lead time, and the ages at death are identical.
eli5: Imagine two runners who both cross the finish line at exactly 3 o'clock. You time the first from the starting gun and the second from an earlier warm-up lap. The second runner's "time" is much longer — but they finished at the very same moment; you just started their stopwatch sooner. That's what earlier cancer screening does: it starts the clock sooner, so the "years survived after diagnosis" looks bigger, even when the person dies at the exact same time they would have anyway. To know if screening really helps, you have to check whether people actually finish later — whether fewer of them die by a given date — not how long their stopwatch was running.
---

## Why this module

The most convincing-sounding defense of a screening program is usually the one that proves nothing. "People whose disease we caught early live much longer after diagnosis" feels like a direct measurement of the program working, and it is instead a near-automatic consequence of catching the disease early, true even when early catching does no good at all. The reason is a clock: survival-from-diagnosis is timed from the day of diagnosis, and moving that day earlier lengthens the measured survival by exactly the amount you moved it, whether or not the patient's life was extended by a single day.

Survival-from-diagnosis starts its clock at the moment of diagnosis, and screening's entire job is to move that moment earlier. If a disease will kill a patient at a fixed time no matter when it is found, then detecting it earlier does not add a day to their life — it only starts the survival clock sooner, so measured survival-from-diagnosis grows while the date of death does not move at all. That inflation has a name: lead time, the interval by which screening advances the diagnosis, and it is added to every screened patient's measured survival whether or not screening helps them.

The fix is to measure the thing screening is supposed to change: mortality — the rate of death in the whole population over a fixed calendar period. Mortality is immune to lead time because it is anchored to the calendar and the population, not to the moment of diagnosis: if screening does not postpone death, the death rate is unchanged, and the honest statistic says so. This module computes both from a cohort where death is fixed.

**Evaluate a screening program by mortality (deaths per population over calendar time), never by survival measured from the date of diagnosis, because screening advances the diagnosis date by a lead time that inflates survival-from-diagnosis even when the date of death — and thus the real benefit — does not change at all.**

## Concepts

**Survival is measured from a start date, and there are two candidate start dates:** the screen date (early) and the symptom date (later); their difference is the lead time, which is exactly the gap between the two survival measures.

```python filename=modules/ai-for-science-and-data/code/leadtime-inter-01/leadtime.py:55-65 COMPLETE
def survival_from_screen(p):
    return p["death"] - p["screen_detect"]


def survival_from_symptom(p):
    return p["death"] - p["symptom_detect"]


def lead_time(p):
    """How much earlier screening detects the disease than symptoms would -- the interval added to measured survival."""
    return p["symptom_detect"] - p["screen_detect"]
```

**We average over the cohort** so the inflation shows up as a difference of means, not a single anecdote.

```python filename=modules/ai-for-science-and-data/code/leadtime-inter-01/leadtime.py:68-69 COMPLETE
def mean(xs):
    return sum(xs) / len(xs)
```

<svg role="img" aria-label="A timeline for one patient: screening detects at year 4, symptoms would appear at year 8, death at year 10; the survival-from-screen bracket spans 6 years and the survival-from-symptom bracket spans 2 years, both ending at the same death" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same death (year 10); two start dates give two 'survivals'</text>
  <line x1="20" y1="60" x2="285" y2="60" stroke="var(--grid)"/>
  <line x1="40" y1="55" x2="40" y2="65" stroke="var(--s1)"/><text x="30" y="52" fill="var(--s1)" font-size="6">screen (4)</text>
  <line x1="150" y1="55" x2="150" y2="65" stroke="var(--muted)"/><text x="132" y="52" fill="var(--muted)" font-size="6">symptom (8)</text>
  <line x1="260" y1="50" x2="260" y2="70" stroke="var(--s2)"/><text x="240" y="46" fill="var(--s2)" font-size="6">death (10)</text>
  <line x1="40" y1="80" x2="260" y2="80" stroke="var(--s1)"/><text x="120" y="90" fill="var(--s1)" font-size="6">survival-from-screen = 6</text>
  <line x1="150" y1="98" x2="260" y2="98" stroke="var(--muted)"/><text x="170" y="108" fill="var(--muted)" font-size="6">from-symptom = 2</text>
  <text x="60" y="108" fill="var(--muted)" font-size="6">lead time = 4</text>
</svg>
^ For one patient the death is fixed at year 10; measuring survival from the screen date (year 4) gives 6 years and from the symptom date (year 8) gives 2 — the two brackets end at the same death, and their 4-year difference is exactly the lead time by which screening moved the start.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/leadtime-inter-01/leadtime.py

The fixture is three patients, each caught 4 years earlier by screening than by symptoms, and each dying at a fixed time.

```json filename=modules/ai-for-science-and-data/code/leadtime-inter-01/leadtime.json:3-7 COMPLETE
  "patients": [
    {"id": "p1", "screen_detect": 4, "symptom_detect": 8, "death": 10},
    {"id": "p2", "screen_detect": 5, "symptom_detect": 9, "death": 11},
    {"id": "p3", "screen_detect": 3, "symptom_detect": 7, "death": 9}
  ]
```

Run `--survival`.

```text filename=--survival
SURVIVAL — from the screen date vs the symptom date (death is the same either way)
------------------------------------------------------------------------------
  patient  screen  symptom  death   survival-from-screen   survival-from-symptom
  p1       4       8        10      6                      2
  p2       5       9        11      6                      2
  p3       3       7        9       6                      2
------------------------------------------------------------------------------
  mean survival-from-screen  = 6.0 years  <- the screening headline
  mean survival-from-symptom = 2.0 years  <- the no-screening baseline
```

Read the two survival columns. Measured from the screen date, every patient survives 6 years; measured from the symptom date, every patient survives 2 years. If you ran a study comparing a screened population (diagnosed at the screen date) to an unscreened one (diagnosed at symptoms), you would report that screening lifts mean survival from 2 years to 6 — it triples survival, a spectacular-looking result. Now look at the death column: 10, 11, 9. Those are identical in both framings, because in this fixture screening does not change when anyone dies — it is the same patients, dying at the same times, detected earlier. The entire "tripling" came from starting each patient's survival clock 4 years sooner. The survival statistic moved a lot; the only thing that actually matters — when people die — did not move at all.

## Build

The inflation is not approximately the lead time; it is exactly the lead time, patient by patient.

```text filename=--leadtime
LEADTIME — the survival 'gain' is exactly the lead time; nobody died later
----------------------------------------------------------------------
  patient  lead time (symptom-screen)   age at death   survival inflation
  p1       4                           10             4
  p2       4                           11             4
  p3       4                           9              4
----------------------------------------------------------------------
  mean lead time = 4.0;  mean survival inflation = 4.0;  mean age at death = 10.0 (unchanged)
```

Each patient's "survival inflation" — how much longer they survive measured from screening than from symptoms — is 4 years, and their lead time — how much earlier screening caught the disease — is also 4 years. They are equal by construction: survival-from-screen minus survival-from-symptom is (death − screen) − (death − symptom) = symptom − screen = lead time, and the death cancels out algebraically. That cancellation is the whole phenomenon in one line: the death term is identical in both survival measures, so their difference cannot contain any information about whether death was postponed — it contains only the shift in the diagnosis date. This is why survival-from-diagnosis is not merely a noisy or weak measure of screening benefit; it is structurally incapable of detecting the absence of benefit, because it reports a gain (the lead time) even when the gain in lifespan is exactly zero, as it is here.

<svg role="img" aria-label="A bar decomposition: the 6-year survival-from-screen equals the 2-year survival-from-symptom plus a 4-year lead time; the real lifespan gain is zero" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">survival-from-screen = survival-from-symptom + lead time</text>
  <text x="10" y="36" fill="var(--muted)" font-size="7">from-screen</text>
  <rect x="90" y="26" width="60" height="14" fill="var(--muted)"/><text x="112" y="37" fill="var(--panel)" font-size="7">2</text>
  <rect x="150" y="26" width="120" height="14" fill="var(--s2)"/><text x="200" y="37" fill="var(--panel)" font-size="7">+4 lead time</text>
  <text x="272" y="37" fill="var(--muted)" font-size="7">= 6</text>
  <text x="10" y="60" fill="var(--muted)" font-size="7">from-symptom</text>
  <rect x="90" y="50" width="60" height="14" fill="var(--muted)"/><text x="112" y="61" fill="var(--panel)" font-size="7">2</text>
  <text x="156" y="61" fill="var(--muted)" font-size="7">the honest baseline</text>
  <text x="10" y="84" fill="var(--muted)" font-size="7">real lifespan gain</text>
  <rect x="90" y="74" width="2" height="14" fill="var(--s1)"/><text x="98" y="84" fill="var(--s1)" font-size="7">0 — the death date never moved</text>
</svg>
^ The 6-year survival-from-screen is just the 2-year survival-from-symptom plus the 4-year lead time; the quantity that actually matters, the gain in lifespan, is zero because the death date never moved — the lead-time slab is the entire apparent benefit.

```python filename=modules/ai-for-science-and-data/code/leadtime-inter-01/leadtime.py:113-122 COMPLETE
    screen_survival_longer = mean_screen > mean_symptom
    print("  survival-from-screen beats survival-from-symptom = %s (%.1f vs %.1f years)"
          % (screen_survival_longer, mean_screen, mean_symptom))

    inflation_is_lead_time = abs((mean_screen - mean_symptom) - mean_lead) < 1e-9
    print("  the survival inflation equals the lead time exactly = %s (%.1f = %.1f)"
          % (inflation_is_lead_time, mean_screen - mean_symptom, mean_lead))

    deaths_unchanged = all(survival_from_screen(p) - survival_from_symptom(p) == lead_time(p) for p in patients)
    print("  earlier detection did not move any death (inflation = lead time per patient) = %s" % deaths_unchanged)
```

## Definition of done

The self-test pins the tripled survival, that the inflation equals the lead time exactly, and the honest metric — mortality — showing no benefit.

```python filename=modules/ai-for-science-and-data/code/leadtime-inter-01/leadtime.py:124-130 COMPLETE
    screening_triples_survival = abs(mean_screen / mean_symptom - 3.0) < 1e-9
    print("  the headline: screening 'triples' survival = %s (%.1f / %.1f = %.1f)"
          % (screening_triples_survival, mean_screen, mean_symptom, mean_screen / mean_symptom))

    horizon = 12
    mortality = sum(1 for p in patients if p["death"] <= horizon)
    mortality_shows_no_benefit = mortality == len(patients)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — survival-from-diagnosis is longer under screening purely by the lead time; mortality is unchanged
------------------------------------------------------------------------------------------------------------
  survival-from-screen beats survival-from-symptom = True (6.0 vs 2.0 years)
  the survival inflation equals the lead time exactly = True (4.0 = 4.0)
  earlier detection did not move any death (inflation = lead time per patient) = True
  the headline: screening 'triples' survival = True (6.0 / 2.0 = 3.0)
  the honest metric: dead by year 12 = 3 of 3 (screening or not) -> no benefit = True
```

<svg role="img" aria-label="Two metrics: survival-from-diagnosis rises from 2 to 6 years under screening, but mortality by year 12 stays at 3 of 3 deaths whether or not screening happens" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">survival triples, but mortality (the honest metric) is flat</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">survival, no-screen</text>
  <rect x="110" y="26" width="40" height="12" fill="var(--muted)"/><text x="154" y="36" fill="var(--muted)" font-size="7">2 yr</text>
  <text x="10" y="52" fill="var(--muted)" font-size="7">survival, screen</text>
  <rect x="110" y="44" width="120" height="12" fill="var(--s2)"/><text x="234" y="54" fill="var(--s2)" font-size="7">6 yr (looks great)</text>
  <line x1="14" y1="64" x2="286" y2="64" stroke="var(--grid)"/>
  <text x="10" y="82" fill="var(--muted)" font-size="7">dead by yr 12, no-screen</text>
  <rect x="150" y="74" width="90" height="10" fill="var(--s1)"/><text x="244" y="83" fill="var(--muted)" font-size="7">3/3</text>
  <text x="10" y="98" fill="var(--muted)" font-size="7">dead by yr 12, screen</text>
  <rect x="150" y="90" width="90" height="10" fill="var(--s1)"/><text x="244" y="99" fill="var(--muted)" font-size="7">3/3 (no change)</text>
</svg>
^ Survival-from-diagnosis jumps from 2 to 6 years with screening, a tripling that looks like a triumph; but the honest metric, mortality by year 12, is 3 of 3 deaths either way — screening moved the survival number and not a single death.

**Done means the bias is proven on real numbers: survival-from-screen averages 6 years and survival-from-symptom 2 years (a 3x "benefit"), the 4-year difference equals the lead time exactly and per-patient, and mortality by year 12 is unchanged at 3 of 3 — so a screening program must be judged by mortality, which is anchored to the calendar and immune to lead time, never by survival measured from the moment of diagnosis.**

## Boss fight

Predict two further ways screening statistics mislead, because lead time is only the first of several biases that all push in the same optimistic direction.

The first trap is length-time bias, which inflates screening's apparent benefit even in a mortality analysis if you are not careful, and which compounds with lead time. Screening catches a disease during its pre-symptomatic phase, and slow-growing, indolent cases spend far longer in that phase than fast, aggressive ones — so a periodic screen is disproportionately likely to catch the slow cases (they sit around waiting to be found) and disproportionately likely to miss the fast ones (which arise and turn deadly between screens). The screened-detected group is therefore enriched for inherently less-dangerous disease, so it shows better outcomes than the symptom-detected group even beyond any lead-time effect, purely because of which cases screening tends to find. The extreme form is overdiagnosis: screening detects indolent "disease" that would never have caused symptoms or death at all, and treating those cases counts as screening "successes" (they all "survive") while actually representing harm — treatment of people who were never going to be sick. Length bias and overdiagnosis mean that even comparing outcomes between screen-detected and symptom-detected cases is biased by the nature of the cases screening selects, which is why the gold standard is randomizing whole populations to be offered screening or not and comparing disease-specific mortality across the entire arms, not across the detected cases.

The second trap is that "mortality" itself must be the right mortality, or it reintroduces bias by the back door. Disease-specific mortality (deaths from the screened cancer) can be distorted by how deaths are attributed — a screening-detected patient who dies of a treatment complication or a reclassified cause may be miscounted, sliding a death out of the "cancer death" column — so all-cause mortality is the most bias-resistant endpoint, since it cannot be gamed by attribution, though it needs larger samples because the screened disease is only a fraction of all deaths. And the comparison has to be over a fixed calendar window on the whole randomized population (intention-to-screen), not conditioned on being diagnosed, because conditioning on diagnosis is exactly what lets lead time and length bias back in. So "measure mortality" is necessary but not sufficient: it must be all-cause (or very carefully attributed disease-specific) mortality, over a fixed follow-up, compared between randomized arms of the entire population — anything that instead compares the detected cases, or survival timed from diagnosis, has quietly rebuilt the trap this module is about.

**Lead time is one of a family of biases that all flatter screening: length-time bias enriches the screen-detected group with slow, indolent cases (and, at the extreme, overdiagnoses disease that would never have harmed anyone), so even comparing outcomes between detected cases is biased — the fix is randomizing whole populations to be offered screening or not. And the mortality endpoint must be the right one: prefer all-cause mortality (attribution can shift disease-specific deaths), measured over a fixed calendar window on the entire intention-to-screen population, never conditioned on diagnosis, or lead time and length bias walk straight back in.**

## External resources

The screening-bias literature (Welch's "Should I Be Tested for Cancer?", Gigerenzer's risk work, and the USPSTF methodology) — lead-time bias, length-time bias, and overdiagnosis, and why disease-specific and all-cause mortality from randomized trials are the only trustworthy measures of screening benefit.

Documentation and primers on survival analysis and screening evaluation — why survival-from-diagnosis is contaminated by lead time, how mortality endpoints are constructed, and the intention-to-screen principle.

The companion base-rate, regression-to-the-mean, and survivorship modules in this topic — lead-time bias is another case where the wrong denominator or start point manufactures an effect, and screening's apparent gains, like a treatment tried on the worst cases, evaporate once the honest, population-anchored comparison is made.
