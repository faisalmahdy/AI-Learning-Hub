---
id: immortal-inter-01
title: Analyze a delayed treatment from a landmark, not from enrollment — the treated group's survival-to-treatment is immortal time that invents a benefit
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: An observational study compares subjects who got an intervention against those who did not, where the intervention is delivered some time after enrollment — a transplant that becomes available, a medication a patient survives long enough to fill, an award given years into a career. The trap is in how the groups form: to be classified as treated, a subject must survive until the intervention, so anyone who dies before then never gets it and lands in the untreated group. The treated group therefore carries, baked into its definition, a stretch of guaranteed survival before treatment — "immortal time," during which a treated subject could not have died without ceasing to be treated. Analyze survival from enrollment (time 0) by whether treatment was ever received and two errors compound: the treated group is credited with the immortal, death-free time, and every early death is dumped into the untreated group because dying early is exactly what disqualified those subjects from treatment. The treated group looks better no matter what the treatment does. The tell is that the effect appears even when the treatment does nothing. The fix is a landmark analysis: choose the time by which treatment status is determined, discard subjects who did not survive to it, classify the survivors by their status then, and measure survival from the landmark forward — excluding the immortal time and comparing the groups only over time in which either could die. On a fixture where treatment truly has no effect (post-landmark survival is identical for treated and untreated survivors), the naive ever-treated analysis reports the treated living 2.75 days longer while the landmark analysis reports no difference.
eli5: Imagine judging whether joining a fancy club makes people live longer, but you can only join the club if you're still alive at age 50. So everyone in the club automatically lived to at least 50 — that's built into being a member. If you then compare club members' lifespans to everyone else (including people who died at 30), the members look like they live much longer, but it's only because dying young kept you out of the club in the first place. The club didn't help; it just quietly excluded the early deaths. To judge it fairly, look only at people who reached 50, and count their years from 50 onward — then joining the club shows its real effect, which here is nothing.
---

## Why this module

Immortal time bias is one of the most persistent errors in observational research because the mistake looks like careful bookkeeping. You have an enrollment date, a treatment date, and a death date; you group by treatment and measure survival from enrollment. Every step is a real, recorded fact. The flaw is not in any number but in the logical structure of the grouping: membership in the treated group is conditional on an outcome — surviving to treatment — that is correlated with the very thing you are measuring.

The consequence is a group of treated subjects who are survivors by construction, compared over a window that includes a period they were guaranteed to survive. Two forces push the same way. The immortal time before treatment is death-free by definition, lowering the treated group's apparent death rate. And the subjects who died early, who might have been treated had they lived, are shunted into the untreated group, raising its death rate. The treated group cannot help but look better, and it does so most dramatically when treatment is common enough that many survivors receive it.

The clean diagnostic is a null: build a cohort where treatment genuinely does nothing, and see whether the naive analysis still finds a benefit. This module does exactly that and contrasts it with the landmark fix.

**To be classified as treated, a subject must survive to treatment, so the treated group carries immortal (guaranteed-alive) time — analyzed from enrollment by ever-treated status it shows a survival benefit even when the treatment has none; a landmark analysis excludes the immortal time and reveals the truth.**

## Concepts

The fixture is a landmark day and three groups: subjects who died before the landmark (never treated), survivors who were treated, and survivors who were not. The death days are chosen so post-landmark survival is identical for the two survivor groups — treatment does nothing.

```json filename=modules/ai-for-science-and-data/code/immortal-inter-01/immortal.json:3-8 COMPLETE
  "landmark": 5,
  "groups": {
    "early": [3, 4],
    "treated": [7, 11],
    "untreated_survivors": [6, 12]
  }
```

Two analyses. The naive one classifies by whether treatment was ever received and measures survival from enrollment: the treated group is the treated survivors; the untreated group is everyone else, including the early deaths. The landmark one keeps only survivors to the landmark and measures their survival from the landmark forward.

```python filename=modules/ai-for-science-and-data/code/immortal-inter-01/immortal.py:34-49 COMPLETE
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
```

The naive analysis puts the early deaths in the untreated group and counts the treated group's full survival, immortal time included; the landmark analysis drops the early deaths from both and starts the clock where treatment status is settled.

<svg role="img" aria-label="A timeline: treated subjects have a guaranteed-alive immortal period from enrollment to the landmark at day 5, and the naive analysis credits that death-free time to the treatment while dumping early deaths into the untreated group" viewBox="0 0 320 130">
  <line x1="30" y1="20" x2="30" y2="115" stroke="var(--line)" stroke-width="1"/>
  <text x="8" y="18" font-size="7" fill="var(--muted)">enroll</text>
  <line x1="150" y1="20" x2="150" y2="115" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="3 3"/>
  <text x="130" y="18" font-size="7" fill="var(--ink)">landmark 5</text>
  <rect x="30" y="30" width="120" height="12" fill="var(--s2)" opacity="0.5"/><text x="34" y="39" font-size="6.5" fill="var(--ink)">treated: immortal time (guaranteed alive)</text>
  <line x1="150" y1="36" x2="250" y2="36" stroke="var(--s1)" stroke-width="2"/><text x="204" y="33" font-size="6.5" fill="var(--s1)">treated, at risk</text>
  <line x1="150" y1="54" x2="270" y2="54" stroke="var(--s1)" stroke-width="2" stroke-dasharray="2 2"/><text x="200" y="51" font-size="6.5" fill="var(--muted)">untreated survivor, at risk</text>
  <circle cx="66" cy="80" r="3" fill="var(--s2)"/><text x="72" y="83" font-size="6.5" fill="var(--s2)">early death (day 3) → untreated</text>
  <circle cx="90" cy="96" r="3" fill="var(--s2)"/><text x="96" y="99" font-size="6.5" fill="var(--s2)">early death (day 4) → untreated</text>
  <text x="30" y="124" font-size="7" fill="var(--muted)">naive counts the shaded immortal time as treated; landmark starts at the dashed line</text>
</svg>
^ Treated subjects are guaranteed alive from enrollment to the landmark — the shaded immortal time — and the early deaths fall into the untreated group because dying disqualified them from treatment. The naive analysis credits the immortal time to the treatment; the landmark analysis starts everyone at the dashed line, after status is settled.

**The naive analysis counts the treated group's guaranteed-alive immortal time and banishes the early deaths to the untreated group; the landmark analysis excludes both, comparing survivors over time in which either group could die.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the survival-analysis step of a cohort study, reduced to six subjects so every mean is checkable by hand.

Run `--cohort` to see the groups and who carries immortal time.

```text filename=immortal.py --cohort
  group                 death days   survived to landmark?
  early                 [3, 4]       False
  treated               [7, 11]      True
  untreated_survivors   [6, 12]      True
```

The treated group's death days are 7 and 11 — both past the landmark at day 5, necessarily, because a subject who died before day 5 could not have been treated at day 5. That guaranteed survival from day 0 to day 5 is the immortal time. The early deaths (days 3 and 4) are untreated not by chance but by the same logic: they died before they could be treated. The untreated survivors (6 and 12) are the fair comparison group — alive at the landmark, but not treated.

Now `--analyze` computes the survival difference each way.

```python filename=modules/ai-for-science-and-data/code/immortal-inter-01/immortal.py:69-70 COMPLETE
    n_diff, n_t, n_u = naive_difference(groups)
    l_diff, l_t, l_u = landmark_difference(groups, L)
```

The two differences could hardly be further apart.

```text filename=immortal.py --analyze
  naive:     treated mean 9.00, untreated mean 6.25, difference +2.75
  landmark:  treated mean 4.00, untreated mean 4.00, difference +0.00
```

The naive analysis reports treated survival of 9.00 days versus 6.25 for untreated — a 2.75-day apparent benefit. But treatment does nothing here: the entire gap is immortal time plus survivor selection. The treated mean is high because it excludes everyone who died early (they are in the untreated group) and counts the guaranteed days before treatment; the untreated mean is low because it is weighed down by those early deaths. The landmark analysis restricts to survivors to day 5, measures from day 5, and reports 4.00 versus 4.00 — exactly no difference, which is the truth. The 2.75-day "benefit" was manufactured entirely by the analysis structure.

<svg role="img" aria-label="Bars: naive analysis shows treated 9.0 versus untreated 6.25 (a 2.75 gap), landmark analysis shows treated 4.0 versus untreated 4.0 (no gap)" viewBox="0 0 320 130">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">mean survival (treatment truly has no effect)</text>
  <text x="10" y="36" font-size="8" fill="var(--muted)">naive</text>
  <rect x="60" y="28" width="144" height="12" fill="var(--s1)"/><text x="208" y="38" font-size="7.5" fill="var(--s1)">treated 9.0</text>
  <rect x="60" y="44" width="100" height="12" fill="var(--s2)"/><text x="164" y="54" font-size="7.5" fill="var(--s2)">untreated 6.25 (gap +2.75)</text>
  <text x="10" y="80" font-size="8" fill="var(--muted)">landmark</text>
  <rect x="60" y="72" width="64" height="12" fill="var(--s1)"/><text x="128" y="82" font-size="7.5" fill="var(--s1)">treated 4.0</text>
  <rect x="60" y="88" width="64" height="12" fill="var(--s2)"/><text x="128" y="98" font-size="7.5" fill="var(--s2)">untreated 4.0 (gap 0)</text>
  <text x="10" y="120" font-size="7.5" fill="var(--muted)">the naive gap is pure immortal-time artifact; landmarking removes it entirely</text>
</svg>
^ The naive analysis shows a 2.75-day treated advantage; the landmark analysis shows none. Since the treatment truly does nothing, the entire naive gap is the immortal-time-plus-survivor-selection artifact, and the landmark analysis recovers the true null.

**The naive analysis invents a 2.75-day survival benefit for a treatment that does nothing; the landmark analysis, measuring survivors from the landmark, reports exactly zero — the gap was an artifact of the grouping, not an effect.**

## Build

The self-test establishes the structure of the trap: every treated subject survived to the landmark (they carry immortal time), and the early deaths are all untreated. Then it shows the naive analysis reporting a benefit.

```python filename=modules/ai-for-science-and-data/code/immortal-inter-01/immortal.py:86-93 COMPLETE
    treated_are_survivors = all(d > L for d in groups["treated"])
    print("  every treated subject survived to the landmark (immortal time) = %s (all death days > %d)" % (treated_are_survivors, L))

    early_deaths_untreated = all(d <= L for d in groups["early"])
    print("  subjects who died before the landmark are all untreated = %s" % early_deaths_untreated)

    naive_shows_benefit = n_diff > 0
    print("  the naive ever-treated analysis shows a survival benefit = %s (%+.2f days)" % (naive_shows_benefit, n_diff))
```

Then the fix: the landmark analysis shows no effect, so the naive benefit was the immortal-time artifact.

```python filename=modules/ai-for-science-and-data/code/immortal-inter-01/immortal.py:95-98 COMPLETE
    landmark_shows_no_effect = abs(l_diff) < 1e-9
    print("  the landmark analysis shows no effect (the truth) = %s (%+.2f days)" % (landmark_shows_no_effect, l_diff))

    bias_removed = naive_shows_benefit and landmark_shows_no_effect
    print("  the benefit was an immortal-time artifact, removed by landmarking = %s" % bias_removed)
```

Running the check confirms every clause.

```text filename=immortal.py --check
  every treated subject survived to the landmark (immortal time) = True (all death days > 5)
  subjects who died before the landmark are all untreated = True
  the naive ever-treated analysis shows a survival benefit = True (+2.75 days)
  the landmark analysis shows no effect (the truth) = True (+0.00 days)
  the benefit was an immortal-time artifact, removed by landmarking = True
```

**The check pins the benefit to the grouping structure — treated subjects are survivors by construction, early deaths are untreated — and shows the landmark analysis, freed of immortal time, recovering the true null.**

## Definition of done

Done means the naive from-enrollment analysis finds a benefit and the landmark analysis finds none, on a cohort where treatment provably does nothing. Building the fixture as a true null is the whole rigor of the demonstration: a benefit that survives even when there is no effect is unambiguously a bias, and the landmark analysis erasing it shows the fix targets exactly that bias rather than an effect.

Two clarifications carry this to real studies. First, the landmark method is the simplest correct approach but not the only one: the more general fix is to model treatment as a time-varying exposure, so that a subject contributes unexposed person-time from enrollment until they are treated and exposed person-time thereafter (a time-dependent Cox model). That attributes the immortal, pre-treatment days to the unexposed state where they belong, rather than to the treatment; the landmark analysis is a discretized special case that is easier to explain and to get right. Either way, the principle is the same — do not let time before treatment count as treated time. Second, the bias is not confined to medicine. Any "did X ever happen" grouping where X takes time to occur has it: the studies claiming Oscar winners or Hall-of-Famers live longer (you must survive to win), that responders to a therapy do better (you must survive to be assessed as a responder), or that users who adopt a feature retain better (they had to stick around to adopt it). The reflex to build is: whenever group membership requires surviving to some event, ask what happened to the subjects who did not survive to it, and start the clock where membership is decided.

<svg role="img" aria-label="Two correct approaches to a delayed treatment: landmark analysis starts the clock at a fixed landmark among survivors, and time-varying exposure assigns pre-treatment days as unexposed and post-treatment days as exposed" viewBox="0 0 320 118">
  <rect x="14" y="22" width="140" height="38" fill="none" stroke="var(--s1)"/>
  <text x="22" y="37" font-size="7.5" fill="var(--s1)">landmark analysis</text>
  <text x="22" y="49" font-size="7" fill="var(--ink)">survivors only, clock from landmark</text>
  <rect x="166" y="22" width="140" height="38" fill="none" stroke="var(--s2)"/>
  <text x="174" y="37" font-size="7.5" fill="var(--s2)">time-varying exposure</text>
  <text x="174" y="49" font-size="7" fill="var(--ink)">pre-treat = unexposed person-time</text>
  <text x="14" y="80" font-size="7.5" fill="var(--muted)">both refuse to count time-before-treatment as treated time</text>
  <text x="14" y="100" font-size="7.5" fill="var(--ink)">watch for it wherever group membership requires surviving to an event</text>
</svg>
^ Both correct approaches refuse to count pre-treatment time as treated time: landmark analysis starts the clock at a fixed landmark among survivors, and a time-varying model assigns pre-treatment days as unexposed person-time. The pattern to watch for is any "ever did X" grouping where X takes time to occur.

**Done means the naive analysis finds a benefit and the landmark analysis finds none on a true-null cohort — the fix being to never count pre-treatment time as treated time, via a landmark or a time-varying exposure, wherever group membership requires surviving to an event.**

## Boss fight

A team analyzes whether patients who received a particular procedure survive longer than those who did not, using a registry. They find a large survival advantage for the procedure group and are ready to recommend it. You notice the procedure is only performed once a patient has been stable for several weeks after admission. Why is the result suspect, and how would you reanalyze it?

The result is almost certainly inflated by immortal time bias. Because the procedure is only performed after several weeks of stability, a patient must survive those weeks to be classified in the procedure group at all — any patient who died in the interim could not have received it and falls into the no-procedure group. So the procedure group has, built into its definition, several weeks of guaranteed survival (immortal time), and the no-procedure group is loaded with the early deaths that were disqualified from the procedure. Measuring survival from admission by whether the procedure was ever done credits the procedure group with that death-free immortal time and penalizes the comparison group with the early deaths, producing a large apparent advantage even if the procedure has no effect — exactly the pattern seen. To reanalyze, stop counting pre-procedure time as procedure time. The simplest fix is a landmark analysis: pick a landmark (say, the point by which the procedure is typically decided), keep only patients still alive at the landmark, classify them by whether they had the procedure by then, and measure survival from the landmark forward — this removes the immortal time and drops the early deaths from both groups. The more general fix is a time-dependent model in which each patient contributes non-procedure person-time from admission until the procedure and procedure person-time afterward, so the pre-procedure days are correctly attributed to the untreated state. Either way, expect the dramatic advantage to shrink or vanish; if a real effect remains after removing the immortal time, that is the one worth acting on. And flag the general lesson: whenever the "treated" group is defined by an event that takes time to occur, the survival needed to reach that event is not evidence of benefit.

## External resources

The methodological literature on immortal time bias (Suissa's papers on immortal time bias in observational studies, and the landmark-analysis and time-dependent-covariate treatments in survival-analysis texts) — the formal definition, the landmark and time-varying-exposure fixes, and worked clinical examples where the bias reversed a study's conclusion.

Popular and cross-domain discussions of the same structure (the "do Oscar winners live longer?" reanalyses, and immortal-time critiques of adherence and responder analyses) — how a "did X ever happen" grouping that requires surviving to X manufactures a benefit far outside medicine, and the reflex of asking what became of the subjects who never reached the event.
