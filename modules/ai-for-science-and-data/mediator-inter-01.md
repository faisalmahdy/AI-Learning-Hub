---
id: mediator-inter-01
title: Don't control for a mediator when you want the total effect — adjusting for a variable on the causal path shrinks a real effect toward zero
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: Choosing which variables to adjust for is the whole game in causal analysis, and the data cannot make the choice for you: the same statistical move — stratify by a third variable, watch the X-Y association change — is correct for one kind of variable and disastrous for another, and only the causal structure distinguishes them. A confounder is a common cause of X and Y and you must control for it, or its influence is misread as an effect of X. A collider is a common effect of X and Y and controlling for it manufactures a correlation that is not there. A mediator sits on the path X→M→Y, carrying part of X's effect — and controlling for it cuts that wire: holding M fixed, X can no longer influence Y through M, so you measure only the direct path and erase the indirect one. If the question is the total effect of X on Y — the usual question for a treatment or intervention — that is wrong, a number smaller than the truth, sometimes all the way to zero. The trap is the reflex to "control for everything," which removes bias for a confounder but introduces it for a mediator by silently answering the direct-effect question instead of the total-effect one; the two look identical in the data and differ only in what the third variable is causally. On a fixture where X raises a mediator M and Y depends on both (Y = 10 + 3X + 5M), the unadjusted total effect of X is 8, adjusting for M leaves only the direct effect of 3, and the removed 5 is the indirect effect that travels through M.
eli5: Imagine you want to know how much taking a training course helps people earn more. The course helps in two ways: it teaches skills directly, and it also helps people get a promotion, and the promotion raises their pay too. If you compare pay between people who took the course and people who didn't, you see the full boost. But if you "control for promotion" — only compare people at the same promotion level — you've thrown away the part of the raise that came through getting promoted, so the course looks like it helped much less than it really did. The promotion is a stepping stone on the path from the course to higher pay, and you shouldn't hold a stepping stone fixed when you're measuring how far the path goes.
---

## Why this module

Causal analysis lives and dies by variable selection, and the hardest part is that the statistics give no signal about whether you have chosen right. "Adjust for a third variable and the effect shrinks" is exactly what you see when you correctly remove a confounder's bias, and exactly what you see when you wrongly block a mediator's path. The numbers are identical; the meaning is opposite. The only thing that tells them apart is the causal role of the third variable, which comes from domain knowledge, not from the dataset.

This module isolates the mediator case, which the popular instinct to "control for everything" gets wrong. A mediator is a variable through which the treatment acts: the treatment changes it, and it changes the outcome. Some of the treatment's effect flows through this channel. Hold the mediator fixed — which is what adjusting for it does — and that channel is severed, so the treatment's measured effect is only what leaks around the mediator by other paths. For a treatment whose whole point is to work through that channel, adjusting for the mediator can shrink the effect to nearly nothing and make a working intervention look useless.

The fix is not statistical but conceptual: know the causal graph before you choose adjustments. This module builds a treatment with both a direct and a mediated effect and shows the adjustment throwing the mediated part away.

**A mediator carries part of the treatment's effect (X→M→Y), so adjusting for it blocks that path and reports only the direct effect — understating the total effect the intervention actually has; the same adjustment that fixes a confounder breaks a mediator, and only the causal structure says which.**

## Concepts

The fixture is four cells of a treatment X and a mediator M, with counts. Each cell's outcome Y is fixed by X and M through Y = 10 + 3X + 5M — a direct effect of 3 from X and a 5-per-unit effect from M.

```json filename=modules/ai-for-science-and-data/code/mediator-inter-01/mediator.json:3-8 COMPLETE
  "cells": [
    {"x": 0, "m": 0, "count": 3},
    {"x": 0, "m": 2, "count": 1},
    {"x": 1, "m": 0, "count": 1},
    {"x": 1, "m": 2, "count": 3}
  ]
```

The total effect is the plain difference in mean Y between the treatment groups. The direct effect is the X effect within a fixed level of M — the mediator-adjusted estimate. A helper reads how M's mean differs by X, the signature that X causes M.

```python filename=modules/ai-for-science-and-data/code/mediator-inter-01/mediator.py:32-57 COMPLETE
def y_value(x, m):
    """Outcome determined by the treatment and the mediator: direct effect 3, mediator effect 5."""
    return 10 + 3 * x + 5 * m


def mean_y(cells, x):
    rows = [c for c in cells if c["x"] == x]
    total = sum(c["count"] * y_value(c["x"], c["m"]) for c in rows)
    n = sum(c["count"] for c in rows)
    return total / n


def mean_m(cells, x):
    rows = [c for c in cells if c["x"] == x]
    return sum(c["count"] * c["m"] for c in rows) / sum(c["count"] for c in rows)


def total_effect(cells):
    return mean_y(cells, 1) - mean_y(cells, 0)


def direct_effect(cells):
    """X effect within a fixed mediator level -- the mediator-adjusted estimate."""
    ms = sorted({c["m"] for c in cells})
    diffs = [y_value(1, m) - y_value(0, m) for m in ms]
    return diffs[0] if len(set(diffs)) == 1 else sum(diffs) / len(diffs)
```

The total effect lets M move with X as it naturally does; the direct effect pins M and asks what X does with that channel closed. The gap between them is the effect that traveled through M.

<svg role="img" aria-label="A causal diagram: X points to Y directly with strength 3, and X points to M which points to Y, an indirect path; controlling for M blocks the indirect path" viewBox="0 0 320 120">
  <circle cx="40" cy="60" r="14" fill="none" stroke="var(--ink)"/><text x="35" y="63" font-size="9" fill="var(--ink)">X</text>
  <circle cx="160" cy="25" r="14" fill="none" stroke="var(--s2)"/><text x="155" y="28" font-size="9" fill="var(--s2)">M</text>
  <circle cx="280" cy="60" r="14" fill="none" stroke="var(--ink)"/><text x="275" y="63" font-size="9" fill="var(--ink)">Y</text>
  <line x1="53" y1="55" x2="147" y2="30" stroke="var(--s2)" stroke-width="1.5"/><text x="90" y="34" font-size="7" fill="var(--s2)">X→M</text>
  <line x1="173" y1="30" x2="267" y2="55" stroke="var(--s2)" stroke-width="1.5"/><text x="215" y="34" font-size="7" fill="var(--s2)">M→Y (×5)</text>
  <line x1="54" y1="63" x2="266" y2="63" stroke="var(--s1)" stroke-width="1.5"/><text x="150" y="76" font-size="7" fill="var(--s1)">direct X→Y (3)</text>
  <line x1="160" y1="39" x2="160" y2="90" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 3"/><text x="164" y="100" font-size="7" fill="var(--ink)">control M = cut here → lose the indirect path</text>
</svg>
^ X reaches Y two ways: directly (strength 3) and through the mediator M (X→M→Y, contributing 5). Controlling for M holds it fixed, which severs the X→M→Y path, leaving only the direct 3 — so the adjustment removes exactly the indirect effect the intervention has through M.

**The total effect lets M vary with X and captures both paths; the mediator-adjusted (direct) effect pins M and keeps only the direct path — the difference is the indirect effect adjustment discards.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the effect-estimation step of a causal analysis, reduced to four cells so every mean is checkable by hand.

Run `--data` to see the cells.

```text filename=mediator.py --data
  X   M   count   Y
  0   0   3       10
  0   2   1       20
  1   0   1       13
  1   2   3       23
```

Notice how M tracks X: the X=0 group is mostly M=0 (three of four), the X=1 group mostly M=2 (three of four). That is X causing M — the treatment pushes the mediator up. Within a fixed M, the effect of X is small and constant: at M=0, Y goes 10→13 (a direct 3); at M=2, Y goes 20→23 (the same direct 3). The large swings — 10 to 23 across the corners — come mostly from M changing, and M changes because X changed it.

Now `--effect` computes both estimates side by side.

```python filename=modules/ai-for-science-and-data/code/mediator-inter-01/mediator.py:75-75 COMPLETE
    tot, dir_ = total_effect(cells), direct_effect(cells)
```

The two numbers are more than a factor of two apart.

```text filename=mediator.py --effect
  mean Y at X=0 = 12.5, at X=1 = 20.5
  unadjusted total effect of X    = 8.0
  effect adjusting for M (direct) = 3.0
  indirect effect removed by adjusting = 5.0
```

The unadjusted comparison gives a total effect of 8.0: the treatment group averages 20.5, the control 12.5. Adjusting for M — comparing only within the same mediator level — gives 3.0, the direct effect. The difference, 5.0, is the indirect effect: X raised M's mean by 1 unit (from 0.5 to 1.5), and each unit of M adds 5 to Y. Adjusting for M threw that 5 away. If this treatment's value is that it works partly by raising M, the adjusted estimate of 3 understates its real impact by more than half — and a researcher who "controlled for M to be safe" would report the smaller number as the effect.

<svg role="img" aria-label="Bars: total effect of X is 8, split into a direct effect of 3 and an indirect effect of 5 through M; adjusting for M keeps only the direct 3" viewBox="0 0 320 110">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">effect of X on Y</text>
  <text x="10" y="40" font-size="8.5" fill="var(--s1)">total (unadjusted)</text>
  <rect x="120" y="30" width="60" height="16" fill="var(--s1)"/><rect x="180" y="30" width="100" height="16" fill="var(--s2)"/><text x="140" y="42" font-size="7.5" fill="var(--panel)">direct 3</text><text x="205" y="42" font-size="7.5" fill="var(--panel)">indirect 5</text><text x="284" y="42" font-size="8" fill="var(--ink)">8</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s1)">adjusted for M</text>
  <rect x="120" y="62" width="60" height="16" fill="var(--s1)"/><text x="140" y="74" font-size="7.5" fill="var(--panel)">direct 3</text><text x="186" y="74" font-size="8" fill="var(--ink)">3 (indirect discarded)</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">adjusting for the mediator removes the indirect 5, keeping only the direct 3</text>
</svg>
^ The total effect of 8 splits into a direct effect of 3 and an indirect effect of 5 through M. Adjusting for M keeps only the direct 3 and discards the indirect 5 — reporting less than half the true total effect of the treatment.

**The unadjusted total effect is 8, the mediator-adjusted direct effect is 3, and the discarded 5 is the indirect path X→M→Y — controlling for the mediator reported under half the treatment's real effect.**

## Build

The self-test establishes that X raises M (so M is a mediator, not an independent covariate), that the total effect is real, and that adjusting for M shrinks it.

```python filename=modules/ai-for-science-and-data/code/mediator-inter-01/mediator.py:92-100 COMPLETE
    x_raises_m = mean_m(cells, 1) > mean_m(cells, 0)
    print("  X raises the mediator M (M is on the path from X) = %s (mean M %.1f -> %.1f)"
          % (x_raises_m, mean_m(cells, 0), mean_m(cells, 1)))

    total_nonzero = tot > 0
    print("  the total effect of X on Y is positive = %s (%.1f)" % (total_nonzero, tot))

    adjusting_shrinks = dir_ < tot
    print("  adjusting for M shrinks the estimated effect = %s (%.1f < %.1f)" % (adjusting_shrinks, dir_, tot))
```

Then the diagnosis: the removed part is exactly the indirect effect through M, and a direct effect does remain (X also acts on Y directly, so this is partial, not full, mediation).

```python filename=modules/ai-for-science-and-data/code/mediator-inter-01/mediator.py:102-105 COMPLETE
    removed_is_indirect = abs((tot - dir_) - 5.0) < 1e-9
    print("  the removed part is the indirect effect through M = %s (%.1f)" % (removed_is_indirect, tot - dir_))

    direct_is_positive_too = dir_ > 0
    print("  a direct effect remains after adjusting (X -> Y directly) = %s (%.1f)" % (direct_is_positive_too, dir_))
```

Running the check confirms every clause.

```text filename=mediator.py --check
  X raises the mediator M (M is on the path from X) = True (mean M 0.5 -> 1.5)
  the total effect of X on Y is positive = True (8.0)
  adjusting for M shrinks the estimated effect = True (3.0 < 8.0)
  the removed part is the indirect effect through M = True (5.0)
  a direct effect remains after adjusting (X -> Y directly) = True (3.0)
```

**The check confirms M is downstream of X, so adjusting for it removes the indirect path — shrinking the total 8 to the direct 3, with the missing 5 identified as the mediated effect.**

## Definition of done

Done means adjusting for M is shown to shrink the treatment's effect by exactly the indirect path, with M established as caused by X (a mediator) rather than a cause of X (a confounder). The clause that X raises M is doing the causal work the data cannot: it is the evidence, backed by the assumed graph, that M is on the path and therefore must not be adjusted for when the total effect is wanted.

Two clarifications complete the picture. First, this is the third case of a trilogy the data cannot resolve, and getting the direction right requires the causal graph, not the numbers. A confounder (common cause of X and Y) must be controlled, or bias inflates or fabricates the effect. A collider (common effect of X and Y) must not be controlled, or conditioning on it opens a spurious path. A mediator (on the path X→M→Y) must not be controlled if you want the total effect. All three present as "the X-Y association changes when you adjust," and only knowing whether the third variable causes X, is caused by X, or is a common effect tells you which rule applies — which is why "control for everything" is not a safe default but a way to guarantee you sometimes control the wrong thing. Second, there are legitimate reasons to hold a mediator fixed, but they answer a different question: the direct effect (the "controlled direct effect" in mediation analysis) is exactly what you want if you are asking how much of the effect does not go through M — for instance, whether a drug helps beyond its effect on blood pressure. The error is not computing the direct effect; it is reporting it as the total effect, or adjusting for a mediator by reflex while believing you are removing bias. State which estimand you want first, then choose adjustments to match.

<svg role="img" aria-label="Three roles of a third variable and the adjustment rule for each: confounder control it, collider do not, mediator do not for the total effect" viewBox="0 0 320 118">
  <rect x="10" y="22" width="98" height="44" fill="none" stroke="var(--s1)"/>
  <text x="17" y="36" font-size="7.5" fill="var(--s1)">confounder</text>
  <text x="17" y="47" font-size="6.5" fill="var(--ink)">common cause of X,Y</text>
  <text x="17" y="59" font-size="6.5" fill="var(--ink)">→ CONTROL it</text>
  <rect x="112" y="22" width="98" height="44" fill="none" stroke="var(--s2)"/>
  <text x="119" y="36" font-size="7.5" fill="var(--s2)">collider</text>
  <text x="119" y="47" font-size="6.5" fill="var(--ink)">common effect of X,Y</text>
  <text x="119" y="59" font-size="6.5" fill="var(--ink)">→ do NOT control</text>
  <rect x="214" y="22" width="96" height="44" fill="none" stroke="var(--ink)"/>
  <text x="221" y="36" font-size="7.5" fill="var(--ink)">mediator</text>
  <text x="221" y="47" font-size="6.5" fill="var(--ink)">on path X→M→Y</text>
  <text x="221" y="59" font-size="6.5" fill="var(--ink)">→ don't, for total</text>
  <text x="10" y="86" font-size="7.5" fill="var(--muted)">all three look identical in the data — only the causal graph says which rule applies</text>
  <text x="10" y="106" font-size="7.5" fill="var(--ink)">name the estimand (total vs direct) first, then choose adjustments</text>
</svg>
^ The same "adjust and the effect changes" pattern arises for confounders (control them), colliders (never), and mediators (not for the total effect). The data cannot distinguish the three; the causal graph must, and the estimand you want — total or direct — decides whether a mediator is held fixed.

**Done means adjusting for M shrinks the treatment's effect by exactly the indirect path, with M shown downstream of X — so a mediator is not controlled when the total effect is wanted, the rule chosen from the causal graph and the named estimand, not the data.**

## Boss fight

An analyst evaluates whether a mentorship program raises employee retention. Comparing mentored vs non-mentored employees, retention is much higher for the mentored group. To "remove confounding," the analyst controls for job satisfaction, which the program is known to improve, and the retention effect shrinks to almost nothing — so they conclude the program does not work. Is that conclusion sound, and what would you do?

The conclusion is not sound: job satisfaction is a mediator, not a confounder, and controlling for it has thrown away most of the program's real effect. The program works in large part by raising job satisfaction, and higher satisfaction raises retention — that is a genuine causal path, mentorship → satisfaction → retention, through which much of the program's benefit flows. By controlling for satisfaction, the analyst held it fixed and severed that path, so the shrunken estimate is only the direct effect of mentorship on retention that does not go through satisfaction. That is a different quantity from the total effect the evaluation is supposed to measure, and reporting it as "the program does not work" is wrong — the program does work, substantially, via satisfaction. The tell is causal, not statistical: satisfaction is caused by the program (downstream of the treatment), which makes it a mediator; a confounder would be something that causes both program participation and retention and precedes the treatment (like prior tenure or role). What to do: for the total effect of the program, do not adjust for satisfaction or any other downstream mediator — the unadjusted comparison (assuming participation was randomized or properly adjusted for true pre-treatment confounders like tenure, department, and performance history) estimates the total effect the decision needs. If the analyst specifically wants to know how much of the effect is not explained by satisfaction — a mechanism question — then a mediation analysis reporting the direct and indirect effects separately is appropriate, but the headline evaluation number is the total effect. The general discipline: before choosing what to adjust for, draw the causal graph and classify each candidate variable as a confounder (control), a collider (never control), or a mediator (don't control for the total effect), and state whether you want the total or the direct effect first.

## External resources

Causal-inference references on adjustment and the confounder/collider/mediator distinction (Pearl's causal-diagram framework, the "table 2 fallacy," and Cinelli, Forney, and Pearl's "A Crash Course in Good and Bad Controls") — why the data cannot tell you which variables to adjust for and how the causal graph classifies each candidate.

Mediation-analysis material on direct vs indirect and total effects (Baron-Kenny and the modern counterfactual mediation framework, controlled and natural direct effects) — the legitimate reasons to condition on a mediator, the estimands that result, and why they answer a mechanism question rather than the total-effect question.
