---
id: regmean-inter-01
title: Extreme scores regress to the mean on retest — so an intervention on the worst looks effective when nothing was done
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: Any noisy measurement is part signal and part luck — a test score is ability plus how the questions fell, a month's sales is the salesperson plus which deals closed. When you pick out the most extreme scores you are selecting for cases where the luck was also extreme, because a record-high score usually needed high ability and good luck to line up, and luck does not repeat. So on a second measurement the same subjects keep their ability but get average luck, and their scores move back toward the middle: the top performers decline, the bottom rise, with nothing done to any of them. This becomes a costly fallacy when you act on the extremes and re-measure: give the worst group extra coaching and they improve, but they would have improved anyway, so the coaching gets credit for regression, and praising the best makes praise look harmful — exactly backwards. The tell is that the group's overall mean did not change; the top came down and the bottom came up by similar amounts, redistribution toward the center, not improvement, and only an untreated control group can separate a real effect from the free regression. On a fixture of ten subjects measured twice with no intervention and an overall mean fixed at 100, the top 3 by round 1 average 123.3 then 108.0 (down 15.3) and the bottom 3 average 78.3 then 92.7 (up 14.3) — both toward the mean, the top still above it (ability is real, so regression is partial), the overall mean unchanged.
eli5: If you roll dice and keep the people who rolled highest, then have them roll again, they'll almost all roll lower the second time — not because they got worse, but because rolling a record high needed luck that won't strike twice. Test scores and sales work the same way: they mix real skill with luck. So the worst performers tend to bounce up on their own next time, and if you happened to "help" them right before, the help looks like a miracle. To know if help actually worked, you have to compare against a group that was equally unlucky but got no help.
---

## Why this module

Measure anything noisy, pick the extremes, measure again, and they move toward average — every time, with no cause but chance. This looks exactly like an effect: the struggling group you helped got better, the star you rewarded slipped. Mistaking that automatic movement for the result of your action is one of the most common ways people conclude a worthless intervention works, or a harmless one hurts.

Any noisy measurement is part signal and part luck: a test score is ability plus how the questions fell that day, a month's sales is the salesperson plus which deals happened to close. When you pick out the most extreme scores — the very highest or the very lowest — you are selecting for cases where the luck was also extreme, because a record-high score usually needed both high ability and good luck to line up. Luck does not repeat. So on a second measurement the same subjects keep their ability but get average luck, and their scores move back toward the middle: the top performers decline, the bottom performers rise, with nothing done to any of them. This is regression to the mean, and it is a property of measuring the same noisy thing twice, not a story about the subjects.

It becomes a costly fallacy the moment you act on the extremes and then re-measure. Give the worst-performing group extra coaching and they improve — but they would have improved anyway, because their scores were unluckily low; the coaching gets credit for regression. Praise or reward the best group and they decline, so praise appears to hurt and punishment of the worst appears to help, which is exactly backwards and has misled real managers, teachers, and clinicians. The tell is that the group's overall mean did not change: the top came down and the bottom came up by similar amounts, redistribution toward the center, not improvement. Without a control group — subjects who were also extreme but got no intervention — you cannot separate a real treatment effect from the regression that happens for free. This module measures ten subjects twice and shows the movement.

**Extreme measurements are extreme partly by luck, which does not repeat, so the highest scorers fall and the lowest rise on retest with no intervention; acting on the extremes then credits the treatment with regression, and only an untreated control group can separate a real effect from it.**

## Concepts

**Selecting the extremes** by the first measurement is where the trap is set — the top and bottom groups are chosen on round 1, which means they were chosen partly for their luck that round.

```python filename=modules/ai-for-science-and-data/code/regmean-inter-01/regmean.py:51-54 COMPLETE
def group_by_round1(subjects, k, top):
    """The k subjects with the highest (top=True) or lowest (top=False) round-1 score."""
    ordered = sorted(subjects, key=lambda name: subjects[name]["round1"], reverse=top)
    return ordered[:k]
```

**The overall mean** is the anchor that exposes regression: if the whole group's average is unchanged between rounds, any group's movement is redistribution toward the center, not a real shift in the population.

```python filename=modules/ai-for-science-and-data/code/regmean-inter-01/regmean.py:47-48 COMPLETE
def overall_mean(subjects, round_key):
    return mean([s[round_key] for s in subjects.values()])
```

<svg role="img" aria-label="A score shown as ability plus luck; selecting the highest scores selects both high ability and good luck, but on retest the luck averages out and the score falls toward the mean" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">a top score = high ability + good luck; luck won't repeat</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">round 1 (selected top)</text>
  <g transform="translate(120,24)">
  <rect x="0" y="0" width="90" height="12" fill="var(--s1)"/><text x="4" y="9" fill="var(--panel)" font-size="6">ability</text>
  <rect x="92" y="0" width="50" height="12" fill="var(--s2)"/><text x="96" y="9" fill="var(--panel)" font-size="6">good luck</text>
  </g>
  <text x="10" y="66" fill="var(--muted)" font-size="7">round 2 (retest)</text>
  <g transform="translate(120,56)">
  <rect x="0" y="0" width="90" height="12" fill="var(--s1)"/><text x="4" y="9" fill="var(--panel)" font-size="6">ability</text>
  <rect x="92" y="0" width="16" height="12" fill="var(--muted)"/><text x="110" y="9" fill="var(--muted)" font-size="6">avg luck</text>
  </g>
  <line x1="212" y1="30" x2="128" y2="62" stroke="var(--ink)" stroke-dasharray="2 2"/>
  <text x="10" y="96" fill="var(--muted)" font-size="7">ability stays; the extra luck evaporates → the score falls toward the mean</text>
</svg>
^ A selected top score is ability plus a lucky bonus; on retest the ability persists but the luck reverts to average, so the score drops toward the mean — regression is the disappearance of the luck that selection picked out.

**Selecting on a noisy measurement selects for luck as well as signal, and the overall mean staying constant is the proof that a group's movement on retest is that luck reverting, not the population changing.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/regmean-inter-01/regmean.py

The fixture is ten subjects measured twice, with the overall mean held at 100 in both rounds so any group movement is regression.

```json filename=modules/ai-for-science-and-data/code/regmean-inter-01/regmean.json:4-13 COMPLETE
    "A": {"round1": 130, "round2": 112},
    "B": {"round1": 122, "round2": 108},
    "C": {"round1": 118, "round2": 104},
    "D": {"round1": 105, "round2": 101},
    "E": {"round1": 100, "round2": 99},
    "F": {"round1": 98,  "round2": 102},
    "G": {"round1": 92,  "round2": 96},
    "H": {"round1": 85,  "round2": 99},
    "I": {"round1": 78,  "round2": 90},
    "J": {"round1": 72,  "round2": 89}
```

Run `--regress` to track the extreme groups across the two rounds.

```text filename=--regress
REGRESS — top and bottom 3 by round 1, measured again (no intervention)
------------------------------------------------------------------
  group    subjects       round1 avg   round2 avg   change
  top      A,B,C          123.3        108.0        -15.3
  bottom   J,I,H          78.3         92.7         +14.3
------------------------------------------------------------------
  overall mean: round1 100.0 -> round2 100.0 (unchanged) -- the groups moved toward it.
```

The top three by round 1 averaged 123.3 and fell to 108.0 on round 2 — down 15.3 — while the bottom three averaged 78.3 and rose to 92.7 — up 14.3. Nothing was done to anyone; these are the same subjects measured twice. Both groups moved *toward* the center, and the overall mean stayed exactly 100, so the population did not improve or decline — score just sloshed from the extremes toward the middle. This is the pure regression signal with no intervention to confuse it: being selected as extreme on round 1 is itself the cause of the round-2 movement, because the selection caught the lucky-high and unlucky-low, and luck averaged out. Notice the top group did not fall all the way to 100 (it landed at 108) — ability is real, so the regression is partial, pulling the score back toward the mean by roughly the fraction of it that was luck, not erasing the signal.

## Build

Now watch the same numbers become a false success story. Run `--intervene`.

```text filename=--intervene
INTERVENE — 'we coached the bottom group between rounds'
--------------------------------------------------------------
  bottom group round1 -> round2: 78.3 -> 92.7  (apparent gain +14.3)
  but the UNTOUCHED top group moved -15.3, and the overall mean is flat (100.0).
--------------------------------------------------------------
  the 'gain' is regression to the mean; only an untreated control group could reveal a real effect.
```

Reframe the identical data as an experiment: we identified the bottom performers, gave them coaching, and re-measured — and they improved by 14.3 points. That is a headline result, the kind that gets a program funded, and it is entirely regression to the mean. The proof is right there: the top group, which got no coaching at all, moved by 15.3 in the opposite direction, and the overall mean did not budge. If the coaching had a real effect, the bottom group would have risen *more* than regression alone predicts — but we have no way to know how much regression alone predicts without a control group of equally-low scorers who were not coached. This is why the fallacy is so durable: acting on the worst cases always seems to help, because the worst cases were going to improve anyway, so the intervention is credited with an improvement it did not cause. The apparent gain is just the group average changing between rounds.

```python filename=modules/ai-for-science-and-data/code/regmean-inter-01/regmean.py:57-58 COMPLETE
def group_avg(subjects, names, round_key):
    return mean([subjects[n][round_key] for n in names])
```

<svg role="img" aria-label="Two number lines from round 1 to round 2: the top group moves down from 123 to 108 and the bottom group moves up from 78 to 93, both toward the mean at 100, which stays fixed" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">both extreme groups move toward the fixed mean (100)</text>
  <line x1="20" y1="60" x2="285" y2="60" stroke="var(--line)"/>
  <line x1="150" y1="30" x2="150" y2="90" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="140" y="26" fill="var(--muted)" font-size="7">mean 100</text>
  <text x="30" y="52" fill="var(--muted)" font-size="7">78</text><text x="255" y="52" fill="var(--muted)" font-size="7">123</text>
  <circle cx="55" cy="60" r="3" fill="var(--s1)"/><circle cx="112" cy="60" r="3" fill="var(--s1)"/>
  <path d="M58,60 L108,60" stroke="var(--s1)"/><text x="60" y="76" fill="var(--muted)" font-size="6">bottom 78→93 (+14)</text>
  <circle cx="245" cy="60" r="3" fill="var(--s2)"/><circle cx="180" cy="60" r="3" fill="var(--s2)"/>
  <path d="M242,60 L184,60" stroke="var(--s2)"/><text x="182" y="48" fill="var(--muted)" font-size="6">top 123→108 (−15)</text>
</svg>
^ The bottom group climbs from 78 toward the mean and the top group falls from 123 toward it; both converge on the fixed mean of 100, so the movement is regression, and crediting only the (coached) bottom group's rise ignores the untouched top group's equal-and-opposite fall.

## Definition of done

The self-test pins both directions of regression, the fixed mean, and the partial (not total) reversion.

```python filename=modules/ai-for-science-and-data/code/regmean-inter-01/regmean.py:102-111 COMPLETE
    top_regresses_down = group_avg(subs, top, "round2") < group_avg(subs, top, "round1")
    print("  the top group's score falls on retest = %s (%.1f -> %.1f)"
          % (top_regresses_down, group_avg(subs, top, "round1"), group_avg(subs, top, "round2")))

    bottom_regresses_up = group_avg(subs, bot, "round2") > group_avg(subs, bot, "round1")
    print("  the bottom group's score rises on retest = %s (%.1f -> %.1f)"
          % (bottom_regresses_up, group_avg(subs, bot, "round1"), group_avg(subs, bot, "round2")))

    overall_mean_unchanged = abs(m1 - m2) < 1e-9
    print("  the overall mean is unchanged = %s (%.1f == %.1f)" % (overall_mean_unchanged, m1, m2))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the top regresses down and the bottom regresses up while the overall mean is unchanged; the top stays above the mean
--------------------------------------------------------------------------------------------------------------------------
  the top group's score falls on retest = True (123.3 -> 108.0)
  the bottom group's score rises on retest = True (78.3 -> 92.7)
  the overall mean is unchanged = True (100.0 == 100.0)
  the top group is still above the mean (partial regression) = True (108.0 > 100.0)
  both extreme groups moved toward the mean (regression signature) = True
```

**Done means the free regression is proven on the fixture: with no intervention the top group falls 123.3 → 108.0 and the bottom rises 78.3 → 92.7 while the overall mean stays 100.0, and the top remains above the mean (partial regression) — so a group selected for being extreme moves toward the center on retest by itself, and an intervention applied to it would be credited with that movement unless an untreated control group is measured too.**

## Boss fight

Predict two ways regression to the mean hides in analyses that do not look like a coaching experiment, because the same mechanism drives selection effects and correlational reasoning generally.

The first trap is that regression scales with noise and with how extreme the selection is, so it masquerades as a real trend in any before/after study of a selected group. The less a measurement reflects true signal (the noisier it is), the more of an extreme score is luck, and the harder it regresses — so a program targeted at, say, the schools with the worst test scores, the hospitals with the highest infection rates, or the machines with the most defects will *always* show improvement on re-measurement, and the improvement is larger the noisier and more extreme the selection was. This is why "we focused on the bottom decile and it improved" is not evidence of anything on its own, and why the only trustworthy design is a randomized control: assign equally-extreme units to treatment and control, and compare, so both groups regress equally and the difference is the real effect. Pre-post comparisons of a selected group, matched historical controls, and "we fixed the outliers and they got better" are all the same regression trap wearing different clothes.

<svg role="img" aria-label="A control design: equally-low subjects split into treated and control; both rise from regression, and the real effect is the extra rise of the treated group above the control" viewBox="0 0 300 110" width="300" height="110">
  <text x="6" y="12" fill="var(--muted)" font-size="8">only a control group separates the treatment from regression</text>
  <text x="10" y="30" fill="var(--muted)" font-size="7">low scorers →</text>
  <line x1="80" y1="90" x2="80" y2="24" stroke="var(--line)"/><line x1="80" y1="90" x2="285" y2="90" stroke="var(--line)"/>
  <text x="60" y="88" fill="var(--muted)" font-size="6">78</text>
  <circle cx="80" cy="82" r="3" fill="var(--muted)"/>
  <path d="M83,82 L200,58" stroke="var(--s1)"/><circle cx="200" cy="58" r="3" fill="var(--s1)"/><text x="205" y="58" fill="var(--muted)" font-size="6">control 93 (regression only)</text>
  <path d="M83,82 L200,40" stroke="var(--s2)"/><circle cx="200" cy="40" r="3" fill="var(--s2)"/><text x="205" y="40" fill="var(--muted)" font-size="6">treated 100</text>
  <line x1="200" y1="40" x2="200" y2="58" stroke="var(--ink)"/><text x="150" y="34" fill="var(--muted)" font-size="6">real effect = the gap</text>
</svg>
^ Split equally-low subjects into treated and control: both rise from regression, so the control shows how much rise was free, and only the treated group's *extra* rise above the control is the real treatment effect.

The second trap is that regression is a general property of imperfect correlation, not just a two-time-point story, and it reshapes how you should read predictions and extremes everywhere.

The second trap is that regression is a general property of imperfect correlation, not just a two-time-point story, and it reshapes how you should read predictions and extremes everywhere. Whenever two variables are correlated less than perfectly, the value paired with an extreme of one is, on average, less extreme in the other — tall fathers have sons shorter than themselves (but still tall), a stock's best year is usually followed by a worse one, this quarter's top-performing fund tends toward the pack next quarter. Galton discovered the effect exactly this way and it is where the statistical term "regression" comes from. The practical consequences: do not extrapolate an extreme observation as if it will persist, expect the second measurement of any record to be less extreme, and be suspicious of any narrative built on "the best/worst got better/worse" without accounting for the regression that was coming for free. And it interacts with base rates and selection: measuring people *because* they were extreme (patients who came in with very high blood pressure, applicants who tested exceptionally well) builds the selection on the noisy measurement, so the follow-up will regress — which is why clinical trials need controls and why "the treatment we gave the sickest patients helped" is the single most common way a useless treatment looks effective.

**Regression to the mean is stronger the noisier the measure and the more extreme the selection, so any before/after study of a group chosen for being extreme will show improvement for free — only a randomized control group (equally extreme, untreated) reveals a real effect — and because it is a general property of imperfect correlation, extreme observations should be expected to be less extreme on any correlated re-measurement, never extrapolated as a trend.**

## External resources

Daniel Kahneman's "Thinking, Fast and Slow" chapter on regression to the mean (the flight-instructor example) and Galton's original work — why extremes revert, why the term is called "regression," and why praise seems to hurt and punishment seems to help.

Any experimental-design or epidemiology text on why pre-post comparisons of a selected group are confounded by regression to the mean, and why a randomized control group is the fix.

The companion base-rate and Simpson's-paradox modules in this topic — all three are cases where an intuitive read of data is confidently wrong, here because a group selected on a noisy measurement moves toward the mean on its own, crediting or blaming an intervention that did nothing.
