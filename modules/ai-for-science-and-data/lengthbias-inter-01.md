---
id: lengthbias-inter-01
title: Screen-detected cases survive longer partly because screening skims the slow ones — length-time bias, not benefit
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: A screening program finds disease before symptoms, and the patients it finds often live longer than patients diagnosed after symptoms — which looks like proof the screening works. But some of that survival gap is built in by which cases screening tends to catch, independent of any benefit, and telling the two apart is the whole problem with evaluating screening by comparing screen-detected to symptom-detected survival. The mechanism is length-time bias: cases vary in progression speed, aggressive cases move quickly from undetectable to symptomatic and spend only a short time in the window a screen could catch them, while indolent cases linger in that detectable-but-asymptomatic window for a long time. A screen that tests the population at points in time is far more likely to catch a case during a long window than a short one, so screen-detected cases are disproportionately the slow, indolent ones — and those have better survival to begin with, for reasons unrelated to being screened. The screen-detected group is thus enriched for good-prognosis cases: it looks like screening extends life when part of the effect is that screening preferentially picks the cases that were going to do well anyway. The tell is composition — if screening detected a much higher share of slow cases than exist in the population, the survival advantage is at least partly bias, and honest evaluation needs population-level disease-specific mortality (a randomized screened-vs-not trial), not survival among each method's detected cases. On a fixture with equal fast (window 1, survival 2) and slow (window 3, survival 8) cases, screening detects slow cases at 3× the rate, making the screen-detected group 75% slow with mean survival 6.5 — far above the clinically-detected 3.5 and the population 5 — purely from enrichment, with no case's survival changed.
eli5: Imagine a pond with two kinds of fish: fast fish that dart through a net-zone in a second, and slow fish that drift through it for a long time. If you dip a net in at random moments, you'll mostly scoop up slow fish, simply because they spend more time where your net is. Now suppose slow fish also happen to live longer than fast fish, for reasons that have nothing to do with your net. If you measure how long the fish you caught live, they'll seem to live a long time — and you might brag that your net makes fish live longer. But it doesn't; your net just tends to catch the long-lived kind. To really know if the net helps, you'd have to compare whole ponds with and without netting, not just the fish you happened to scoop.
---

## Why this module

Screening seems like it should be easy to evaluate: find the disease early, and the people you found should do better than the people who waited for symptoms. That comparison is intuitive, ubiquitous in how screening gets promoted, and systematically misleading, because it compares two groups that differ in more than whether they were screened. Length-time bias is one of the two biases (lead-time bias is the other) that make screen-detected survival look good even when screening changes nothing, and it is worth understanding because it is not a small correction — it can manufacture a large survival gap out of pure selection.

The setup is that disease is not uniform in speed. Aggressive, fast-progressing cases spend little time in the window where a symptom-free screen could catch them; they announce themselves with symptoms quickly. Indolent, slow-progressing cases sit in that detectable-but-quiet window for a long time. A screening program is a sampler in time, and a sampler catches things in proportion to how long they are available to be caught — so it disproportionately catches the slow cases. Those slow cases also tend to have better outcomes regardless of screening. The screen-detected group is therefore a biased sample, skewed toward good-prognosis disease before any benefit of early detection is even considered.

This module builds a population of fast and slow cases, screens it, and measures how the survival comparison is distorted by composition.

**Do not judge a screening program by comparing survival of screen-detected cases to symptom-detected cases, because screening preferentially catches slow-progressing cases (they spend longer in the detectable window) and those have better prognosis anyway — so the screen-detected group is enriched for good-prognosis cases and appears to survive longer even when screening provides no benefit; judge screening by population-level mortality instead.**

## Concepts

The fixture is a population of two case types. Fast cases have a short detectable window (1) and low survival (2 years); slow cases have a long window (3) and high survival (8 years). The population is 50/50 — twelve of each — and a screen detects a case at a rate proportional to its window.

```json filename=modules/ai-for-science-and-data/code/lengthbias-inter-01/lengthbias.json:3-8 COMPLETE
  "metric": "survival_years",
  "groups": {
    "fast": {"window": 1, "survival": 2, "count": 12},
    "slow": {"window": 3, "survival": 8, "count": 12}
  },
  "screen_detection_rate_per_window": 0.25
```

Detection probability is proportional to the window — the longer a case is detectable, the more likely a time-sampling screen catches it. Screen-detected counts are the population times that probability; clinically-detected are the remainder, found later by symptoms.

```python filename=modules/ai-for-science-and-data/code/lengthbias-inter-01/lengthbias.py:32-44 COMPLETE
def detection_prob(window, rate):
    """Screening detects a case with probability proportional to its detectable window."""
    return window * rate


def screen_detected(groups, rate):
    """Count of each type detected by screening (count * detection prob)."""
    return {k: g["count"] * detection_prob(g["window"], rate) for k, g in groups.items()}


def clinical_detected(groups, rate):
    """Count of each type NOT caught by screening, detected later by symptoms."""
    return {k: g["count"] - g["count"] * detection_prob(g["window"], rate) for k, g in groups.items()}
```

The comparison is mean survival by detection route, and the diagnostic is the slow-case share — how enriched each group is for the good-prognosis type.

```python filename=modules/ai-for-science-and-data/code/lengthbias-inter-01/lengthbias.py:47-55 COMPLETE
def mean_survival(groups, counts):
    """Mean survival over a set of per-type counts."""
    total = sum(counts.values())
    return sum(groups[k]["survival"] * counts[k] for k in counts) / total if total else 0.0


def slow_share(counts):
    total = sum(counts.values())
    return counts["slow"] / total if total else 0.0
```

<svg role="img" aria-label="A time window strip: a fast case occupies a short detectable segment, a slow case a long one; a screening sampler line crosses the long segment more often" viewBox="0 0 320 120">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">time in the detectable window (where a screen can catch it)</text>
  <text x="10" y="42" font-size="8" fill="var(--muted)">fast:</text>
  <rect x="50" y="34" width="20" height="12" fill="var(--s2)"/><text x="74" y="44" font-size="7" fill="var(--muted)">short window (1)</text>
  <text x="10" y="72" font-size="8" fill="var(--muted)">slow:</text>
  <rect x="50" y="64" width="60" height="12" fill="var(--s1)"/><text x="114" y="74" font-size="7" fill="var(--muted)">long window (3) — 3x more likely to be caught</text>
  <g stroke="var(--ink)" stroke-width="1" stroke-dasharray="2 3">
  <line x1="60" y1="28" x2="60" y2="90"/><line x1="90" y1="28" x2="90" y2="90"/><line x1="120" y1="28" x2="120" y2="90"/>
  </g>
  <text x="130" y="104" font-size="7.5" fill="var(--ink)">screening samples in time → catches the long window more</text>
</svg>
^ A screen samples the population at points in time (dashed lines). A slow case's long detectable window overlaps more sampling points than a fast case's short one, so screening catches slow cases disproportionately — the root of the bias.

**Screening is a time-sampler, and a sampler catches things in proportion to how long they persist — so it over-selects the slow, long-window cases, which happen to be the good-prognosis ones.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the screening-evaluation step of an epidemiological analysis, reduced to two case types so every count is checkable by hand.

Run `--detect` to see who screening catches.

```text filename=lengthbias.py --detect
  type  window  detection prob   population   screen-detected   clinical
  fast  1       0.25             12           3.0               9.0
  slow  3       0.75             12           9.0               3.0
  screening catches slow cases at 3x the rate of fast (window ratio)
```

The population is balanced — twelve fast, twelve slow — but detection is not. Fast cases (window 1) are caught at rate 0.25, so screening finds 3 of the 12; slow cases (window 3) are caught at rate 0.75, so screening finds 9 of the 12. Screening's catch is 3 fast and 9 slow, while the cases it misses (found later by symptoms) are 9 fast and 3 slow. The two detection routes end up with mirror-image compositions, purely because of how long each case type is available to be caught.

Now `--survival` compares the outcomes.

```text filename=lengthbias.py --survival
  screen-detected: mean 6.5 years, 75% slow cases
  clinical (symptom): mean 3.5 years, 25% slow cases
  whole population:   mean 5.0 years, 50% slow cases
```

Screen-detected cases average 6.5 years; clinically-detected average 3.5; the whole population averages 5.0. A naive reading says screening nearly doubles survival over waiting for symptoms. But look at the slow-case share: screen-detected is 75% slow, clinical is 25% slow, the population is 50%. The survival gap is the composition gap — screen-detected is enriched for the good-prognosis slow cases (75% vs the population's 50%), and clinical is depleted of them. No case's survival changed; screening did not extend anyone's life. It sorted the cases, and then the sorted groups were compared as if the sorting were a treatment effect.

**Screening detects 75% slow cases against 50% in the population, and that enrichment alone lifts screen-detected survival to 6.5 versus the population's 5.0 — a benefit that is entirely composition, with every case's survival unchanged.**

## Build

The self-test asserts the mechanism and the artifact: screening detects slow cases at a higher rate, the screen-detected group is enriched for slow cases, and its survival exceeds both the clinical and population means.

```python filename=modules/ai-for-science-and-data/code/lengthbias-inter-01/lengthbias.py:100-111 COMPLETE
    slow_detected_more = detection_prob(groups["slow"]["window"], rate) > detection_prob(groups["fast"]["window"], rate)
    print("  screening detects slow cases at a higher rate than fast = %s (%.2f > %.2f)"
          % (slow_detected_more, detection_prob(groups["slow"]["window"], rate), detection_prob(groups["fast"]["window"], rate)))

    screen_enriched_for_slow = slow_share(sd) > slow_share(pop)
    print("  the screen-detected group is enriched for slow cases = %s (%.0f%% vs %.0f%% in population)" % (screen_enriched_for_slow, 100 * slow_share(sd), 100 * slow_share(pop)))

    screen_beats_clinical = sd_mean > cd_mean
    print("  screen-detected survival exceeds clinically-detected = %s (%.1f > %.1f)" % (screen_beats_clinical, sd_mean, cd_mean))

    screen_beats_population = sd_mean > pop_mean
    print("  screen-detected survival even exceeds the population mean = %s (%.1f > %.1f)" % (screen_beats_population, sd_mean, pop_mean))
```

<svg role="img" aria-label="Two pie-like bars: population 50 percent slow, screen-detected 75 percent slow, with survival means 5.0 and 6.5 labeled" viewBox="0 0 320 120">
  <text x="10" y="18" font-size="8.5" fill="var(--muted)">slow-case share and mean survival</text>
  <text x="10" y="42" font-size="8" fill="var(--muted)">population</text>
  <rect x="90" y="32" width="100" height="16" fill="var(--s1)"/><rect x="190" y="32" width="100" height="16" fill="var(--muted)"/>
  <text x="120" y="44" font-size="7.5" fill="var(--panel)">50% slow</text><text x="255" y="60" font-size="8" fill="var(--ink)">mean 5.0</text>
  <text x="10" y="86" font-size="8" fill="var(--muted)">screen-detected</text>
  <rect x="90" y="76" width="150" height="16" fill="var(--s1)"/><rect x="240" y="76" width="50" height="16" fill="var(--muted)"/>
  <text x="130" y="88" font-size="7.5" fill="var(--panel)">75% slow</text><text x="255" y="104" font-size="8" fill="var(--ink)">mean 6.5</text>
</svg>
^ Screening shifts the slow-case share from 50% (population) to 75% (screen-detected), and the survival mean rises from 5.0 to 6.5 in lockstep — the survival gain is the composition shift, nothing more.

Running the check confirms every clause, including that per-case survival is unchanged and the gap is composition.

```text filename=lengthbias.py --check
  screening detects slow cases at a higher rate than fast = True (0.75 > 0.25)
  the screen-detected group is enriched for slow cases = True (75% vs 50% in population)
  screen-detected survival exceeds clinically-detected = True (6.5 > 3.5)
  screen-detected survival even exceeds the population mean = True (6.5 > 5.0)
  no case's survival was changed by screening (same per-type survival) = True
  the survival gap comes from group composition, not benefit = True (slow share shifted 50%->75%)
```

**The check ties the survival gap to the slow-share shift with per-case survival held fixed — so the apparent benefit is demonstrably enrichment, not any change screening made to an outcome.**

## Definition of done

Two properties close it. The survival gap must be real (screen-detected exceeds clinical and even the population) and it must be attributable to composition — the slow-case share shifted substantially while no case's survival changed. The second is what proves it is bias: if survival rose without any case living longer, the rise came from re-sorting, not from benefit.

```python filename=modules/ai-for-science-and-data/code/lengthbias-inter-01/lengthbias.py:113-118 COMPLETE
    survival_per_type_unchanged = groups["fast"]["survival"] == 2 and groups["slow"]["survival"] == 8
    print("  no case's survival was changed by screening (same per-type survival) = %s" % survival_per_type_unchanged)

    gap_is_composition = abs(slow_share(sd) - slow_share(pop)) > 0.2
    print("  the survival gap comes from group composition, not benefit = %s (slow share shifted %.0f%%->%.0f%%)"
          % (gap_is_composition, 100 * slow_share(pop), 100 * slow_share(sd)))
```

Two clarifications keep the tool honest. First, length-time bias is distinct from lead-time bias, and both inflate screen-detected survival: lead-time bias moves the diagnosis date earlier so survival-from-diagnosis is longer even with the same death date, while length-time bias (this module) selects inherently slower, better-prognosis cases into the screen-detected group; a fair evaluation has to defeat both. Its extreme form is overdiagnosis — screening detects indolent cases that would never have caused symptoms or death at all, which have "infinite" survival and are counted as screening successes though the patient is treated for a disease that would never have harmed them. Second, the fix is not a cleverer survival comparison on the detected cases — no adjustment to a biased sample recovers the answer — it is to change the endpoint and the design: compare disease-specific mortality between whole populations randomized to be screened or not. In a randomized mortality trial, the slow-case enrichment happens in both arms and cancels, so a mortality difference reflects real benefit. This is exactly why screening is judged by randomized mortality trials rather than by how long screen-detected patients live, and why some widely-adopted screens turned out to move survival statistics without moving mortality.

<svg role="img" aria-label="Two screening biases side by side: lead-time bias moves the diagnosis point earlier on the same lifespan, length-time bias selects the slow long-window cases" viewBox="0 0 320 120">
  <text x="10" y="16" font-size="8.5" fill="var(--s2)">lead-time bias: same death, earlier clock start</text>
  <line x1="20" y1="34" x2="180" y2="34" stroke="var(--muted)" stroke-width="2"/>
  <circle cx="60" cy="34" r="3" fill="var(--s2)"/><text x="46" y="28" font-size="6.5" fill="var(--muted)">screen dx</text>
  <circle cx="110" cy="34" r="3" fill="var(--ink)"/><text x="98" y="28" font-size="6.5" fill="var(--muted)">symptom dx</text>
  <circle cx="180" cy="34" r="3" fill="var(--s2)"/><text x="168" y="28" font-size="6.5" fill="var(--muted)">death</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s1)">length-time bias: screen selects the slow cases</text>
  <rect x="20" y="82" width="16" height="10" fill="var(--muted)"/><text x="40" y="91" font-size="6.5" fill="var(--muted)">fast (missed)</text>
  <rect x="20" y="96" width="60" height="10" fill="var(--s1)"/><text x="84" y="105" font-size="6.5" fill="var(--muted)">slow (caught, lives longer)</text>
</svg>
^ The two screening biases differ: lead-time bias moves the diagnosis point earlier on an unchanged lifespan (survival-from-diagnosis grows, death date fixed); length-time bias (this module) selects the slow, long-window cases that live longer anyway. A fair evaluation must defeat both — which is why mortality, not survival-by-detection, is the endpoint.

**Done means screen-detected survival exceeds clinical and population survival while per-case survival is unchanged and the slow-share shifted — a composition artifact, defeated only by comparing population-level mortality, not detected-case survival.**

## Boss fight

A company markets a blood test that screens for a cancer and advertises that "patients whose cancer was found by our test have a 5-year survival of 80%, versus 45% for patients diagnosed after symptoms." Regulators ask you to assess whether this proves the test saves lives. What biases are at work, and what evidence would actually settle it?

The comparison proves almost nothing about benefit, because it pits screen-detected survival against symptom-detected survival — the exact comparison length-time and lead-time bias corrupt. Length-time bias: the test, sampling people at a point in time, preferentially catches slow-growing, indolent cancers that spend a long time detectable, and those have far better prognosis regardless of the test, so the screen-detected group is enriched for good-prognosis disease before any benefit is counted. Lead-time bias: even for cancers the test would have caught anyway, finding them earlier starts the survival clock sooner, so "5-year survival" rises even if the date of death is unchanged. And in the extreme, overdiagnosis: the test may detect indolent cancers that would never have caused symptoms, counting patients who were never at risk as survival successes. All three inflate the 80% number without the test extending a single life. What would settle it is a randomized controlled trial that assigns whole populations to be screened or not and compares disease-specific mortality (deaths from that cancer per person in each arm), not survival among the detected. Because the enrichment and the lead time occur in both arms and cancel, a lower mortality in the screened arm is real benefit; if mortality is the same despite the survival statistics looking better, the test moves numbers, not outcomes. The regulator should require the mortality endpoint from a randomized trial, not the survival-by-detection-method comparison.

## External resources

The standard epidemiology treatment of screening biases — lead-time bias, length-time bias, and overdiagnosis (Gordis, *Epidemiology*, or the equivalent chapter in any screening-evaluation text) — the definitive account of why screen-detected survival overstates benefit and why randomized mortality trials are required.

Welch, Schwartz, and Woloshin, *Overdiagnosed*, and the USPSTF methodology on evaluating screening — accessible discussions of length-time bias and overdiagnosis in real screening programs (breast, prostate, thyroid), and why disease-specific mortality, not survival among detected cases, is the correct endpoint.
