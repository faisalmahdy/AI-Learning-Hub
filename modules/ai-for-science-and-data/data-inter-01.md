---
id: data-inter-01
title: Regression to the mean — the treatment that worked because you picked the worst
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 8-10h
summary: Measure a population twice with no intervention at all, select the worst 40 on the first measurement, and their second measurement rises +8.86 while the best 40 fall -12.65 — both toward the mean — because a low score is partly real skill and partly bad luck that does not repeat. An analyst who "coached" the bottom group between the measurements would report an 8.86 improvement that never happened, and only a control group selected the same way reveals it: the untreated half improves +9.24, as much as the treated +8.47, so the gain is regression to the mean, not the coaching.
eli5: The rookies who did worst this week will mostly do better next week, and the best will mostly do worse, even if nobody changes anything — because part of an extreme score is luck, and luck does not repeat. So if you only help the worst and measure again, they improve on their own, and you will wrongly credit your help.
---

## Why this module

The previous data module showed an aggregate lying because of a confounder. This one shows a difference that is real in the numbers and still not caused by what you think — the most expensive mistake in applied data analysis, because the improvement is genuinely there, it just is not yours. The track's goal is knowing "which differences are real," and this is the difference that is real *and meaningless*: regression to the mean, the statistical pull of extreme measurements back toward the average on re-measurement. Select a group because it scored low, measure it again, and it improves — with no intervention, guaranteed — and any treatment you happened to apply in between will look like it worked.

The mechanism is simple once you see it. A measurement is part signal and part noise. A unit that scored very low did so partly because its true value is low and partly because it got unlucky this time, and the luck does not carry over — next time the noise is fresh, so the score drifts back up toward the unit's true value. The worst performers, selected on a noisy score, are enriched for bad luck, so they rise; the best are enriched for good luck, so they fall. The only way to separate a real effect from this artifact is a control group selected the same way and left alone: if it improves as much as the treated group, the improvement was regression, not treatment.

You need the evals-track instinct that a number carries noise. Everything runs offline against a seeded simulated population — no real intervention is applied anywhere, so every change you see is the artifact — stdlib Python 3, `$0.00`. The instinct to unlearn is that a before-after improvement in a selected group is evidence the thing you did worked. On a group selected for being extreme, improvement is the null result.

Here is the artifact, on a population nothing was done to:

```
# modules/ai-for-science-and-data/code/data-inter-01/ — COMPLETE, run from that directory
$ python3 regression.py --select

SELECTED GROUPS — the extremes on measurement 1, re-measured   (k=40)
--------------------------------------------------------------
  bottom 40:  m1 mean 31.37 -> m2 mean 40.23   change +8.86
  top 40:     m1 mean 70.86 -> m2 mean 58.22   change -12.65
```

run: 2026-08-25 · deterministic; seeded simulation, no intervention · n=200, k=40, noise_sd=10 · `python3 regression.py --select`

The worst 40 improved by nearly 9 points and the best 40 fell by nearly 13, and nothing was done to any of them between the two measurements. This module is why those numbers are guaranteed, and the control group that tells them apart from a real effect.

## Concepts

Named here so you can find them again; each is built below.

- **True value vs measurement** — a unit's stable quantity, versus one noisy observation of it.
- **Regression to the mean** — extreme measurements drift toward the average on re-measurement, because their noise does not repeat.
- **Selection on a noisy score** — choosing a group by an extreme measurement enriches it for luck in that direction.
- **Apparent effect** — the before-after change in a selected group; contaminated by regression.
- **Control group** — a group selected the same way but left untreated; the baseline that isolates a real effect.
- **The null result** — on an extreme-selected group, improvement with no cause is the expected outcome.

## Worked example

Source: the track's experiment-design material on uncertainty, simulated here so the true values are known and the intervention is provably zero. The same trap appears in every "we helped the strugglers and they improved" claim across the labs' own systems.

Script and fixture: `modules/ai-for-science-and-data/code/data-inter-01/` — `regression.py`, a seeded 200-unit population measured twice. Every command runs from there.

### The frame: the sophomore slump and the speed camera

Two everyday versions of this. An athlete has a spectacular rookie season, makes the magazine cover, and slumps the next year — the "cover jinx." There is no jinx; a spectacular season is true talent plus a lot of things going right, and the things going right do not all recur, so the next season regresses toward their real level. And a town installs a speed camera at the intersection where accidents spiked last year, and accidents drop — but they were going to drop anyway, because a spike is a bad-luck cluster that does not repeat, and the camera gets credit for the regression.

Both are the same statistical fact wearing different clothes: you selected on an extreme, and extremes are made partly of luck that reverts. The rookie and the intersection were chosen *because* they were extreme, which is exactly the condition that guarantees regression. This module builds the mechanism in a population where we know for certain nothing was done, so the improvement can only be the artifact.

### The population: measured twice, untouched

Each unit has a fixed true skill; each measurement is that skill plus fresh, independent noise. There is no step between the two measurements — no coaching, no treatment, nothing.

```
# regression.py:33-43 — COMPLETE (two noisy measurements of a fixed skill, no intervention)
def population():
    """Each unit has a fixed true skill; each MEASUREMENT is skill plus fresh noise.
    Two measurements, no intervention between them."""
    rng = random.Random(SEED)
    units = []
    for _ in range(N):
        true = rng.gauss(TRUE_MEAN, TRUE_SD)
        m1 = true + rng.gauss(0, NOISE_SD)
        m2 = true + rng.gauss(0, NOISE_SD)          # independent noise, same skill
        units.append((m1, m2))
    return units
```

The population as a whole does not move — because nothing moved it:

```
# $ python3 regression.py --population
#   overall mean, measurement 1 = 50.66
#   overall mean, measurement 2 = 48.93
```

run: 2026-08-25 · fixture · `python3 regression.py --population`

Both measurement rounds average about 50, as designed. The whole population is flat. Any group that moves must be moving *within* this flat population — some units up, others down, canceling out. Selection decides which units you look at, and that is where the artifact enters.

<svg viewBox="0 0 700 160" role="img" aria-label="A low first measurement of 31 decomposed into true skill 38 minus bad luck 7. On the second measurement the true skill 38 stays but fresh luck is near zero, so the score rises toward 38.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">why a low score rises: it was true skill MINUS luck, and the luck resets</text>
    <text x="20" y="52" fill="var(--ink)">measurement 1</text>
    <rect x="140" y="42" width="190" height="16" fill="var(--s1)" opacity="0.4"></rect><text x="150" y="54" fill="var(--ink)" font-size="8">true skill 38</text>
    <rect x="330" y="42" width="70" height="16" fill="var(--s2)"></rect><text x="336" y="54" fill="var(--panel)" font-size="8">-luck 7</text>
    <text x="410" y="54" fill="var(--s2)">= observed 31 (low)</text>
    <text x="20" y="92" fill="var(--ink)">measurement 2</text>
    <rect x="140" y="82" width="190" height="16" fill="var(--s1)" opacity="0.4"></rect><text x="150" y="94" fill="var(--ink)" font-size="8">true skill 38 (unchanged)</text>
    <rect x="330" y="82" width="8" height="16" fill="var(--muted)"></rect><text x="345" y="94" fill="var(--muted)" font-size="8">±luck ~0 (fresh)</text>
    <text x="410" y="94" fill="var(--s1)">= observed ~38 (risen)</text>
    <text x="20" y="130" fill="var(--muted)">the skill was always ~38; the first score was dragged down by luck that</text>
    <text x="20" y="144" fill="var(--muted)">did not recur -- so re-measuring recovers the skill. That rise is the artifact.</text>
  </g>
</svg>
^ A low first measurement is true skill minus a slug of bad luck; the skill persists to the second measurement but the luck is drawn fresh and averages to nothing, so the score climbs back to the skill. Selecting the worst selects the unluckiest, and un-luck is what reverts.

### Selecting the extremes

Pick the worst and best on the first measurement.

```
# regression.py:50-55 — COMPLETE (select the extremes on the FIRST measurement)
def bottom_k(units, k):
    return sorted(units, key=lambda u: u[0])[:k]     # worst on the FIRST measurement


def top_k(units, k):
    return sorted(units, key=lambda u: u[0])[-k:]    # best on the FIRST measurement
```

The bottom 40 are not just low-skill units — they are units whose skill is low *and/or* whose first-measurement noise was negative. Averaged over 40, the bad luck is real and sizable, and it is gone by the second measurement, so the group rises. The top 40 are the mirror: high skill and/or lucky noise, and the luck evaporates, so they fall.

<svg viewBox="0 0 700 190" role="img" aria-label="A number line with the mean at 50. The bottom-40 group sits at 31 on measurement 1 and moves right to 40 on measurement 2, toward the mean. The top-40 group sits at 71 on measurement 1 and moves left to 58 on measurement 2, toward the mean. The population mean stays at 50.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">both extremes drift toward the mean on re-measurement (nothing was done)</text>
    <line x1="60" y1="100" x2="640" y2="100" stroke="var(--grid)"></line>
    <line x1="350" y1="70" x2="350" y2="130" stroke="var(--acc-line)" stroke-dasharray="3 2"></line><text x="335" y="150" fill="var(--acc-ink)">mean 50</text>
    <circle cx="155" cy="100" r="5" fill="var(--s2)"></circle><text x="120" y="88" fill="var(--s2)">bottom m1=31</text>
    <circle cx="245" cy="100" r="5" fill="var(--s1)"></circle><text x="225" y="128" fill="var(--s1)">m2=40</text>
    <path d="M 162 100 L 238 100" stroke="var(--s1)" stroke-width="1.5" marker-end="url(#a)"></path>
    <circle cx="545" cy="100" r="5" fill="var(--s2)"></circle><text x="520" y="88" fill="var(--s2)">top m1=71</text>
    <circle cx="415" cy="100" r="5" fill="var(--s1)"></circle><text x="400" y="128" fill="var(--s1)">m2=58</text>
    <path d="M 538 100 L 422 100" stroke="var(--s1)" stroke-width="1.5" marker-end="url(#a)"></path>
    <defs><marker id="a" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="var(--s1)"></path></marker></defs>
    <text x="20" y="178" fill="var(--muted)">+8.86 for the bottom, -12.65 for the top: both toward 50, both with no cause.</text>
  </g>
</svg>
^ Selected on a noisy first measurement, the extremes are enriched for luck in their direction; on re-measurement the luck is fresh and they slide toward the mean. The improvement of the bottom group is the same phenomenon as the decline of the top — one artifact, two signs.

### The apparent effect, and why it fools you

The before-after change in a selected group is what an analyst would report as the treatment effect.

```
# regression.py:60-63 — COMPLETE (the before-after change an analyst would call the effect)
def apparent_effect(group):
    """The change from first to second measurement -- what an analyst would call the
    treatment effect if they had 'treated' this group between the two."""
    return mean([m2 for _, m2 in group]) - mean([m1 for m1, _ in group])
```

For the bottom group it is +8.86. Imagine the story that writes itself: "we identified the 40 worst performers, gave them targeted coaching, and they improved by 8.86 points." Every word is true except the causal claim, and the causal claim is the whole point of the report. The improvement is real; the coaching did nothing; and there is no way to tell from the treated group alone, because a treated group and an untreated one selected the same way both regress.

### The control group reveals it

Split the bottom group in two, "treat" one half (there is no real treatment, which is the point), and compare.

```
# $ python3 regression.py --control
#   treated bottom half:  change +8.47
#   control bottom half:  change +9.24
```

run: 2026-08-25 · fixture · `python3 regression.py --control`

The control half improved +9.24, as much as the treated half's +8.47 — because nothing distinguishes them but a label. A real treatment effect is the *difference* between treated and control, and here that difference is essentially zero, correctly reporting no effect. Without the control you would have reported +8.47 as the effect of coaching; with it, you report ≈0, the truth. The control is not a nicety; it is the only thing standing between you and a confident false conclusion.

<svg viewBox="0 0 700 150" role="img" aria-label="Two bars: treated bottom half change +8.47, control bottom half change +9.24. They are nearly equal, so the treatment effect (their difference) is about zero.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="18" fill="var(--muted)">apparent improvement: treated vs a control selected the same way</text>
    <text x="20" y="55" fill="var(--ink)">treated</text>
    <rect x="120" y="44" width="339" height="18" rx="3" fill="var(--s1)" opacity="0.5"></rect><text x="465" y="58" fill="var(--muted)">+8.47</text>
    <text x="20" y="90" fill="var(--ink)">control</text>
    <rect x="120" y="79" width="370" height="18" rx="3" fill="var(--muted)"></rect><text x="496" y="93" fill="var(--muted)">+9.24</text>
    <text x="20" y="128" fill="var(--s1)">treatment effect = treated - control ≈ 0  (the coaching did nothing)</text>
  </g>
</svg>
^ Both halves of the bottom group improve by nearly the same amount. The treatment effect is their difference, ≈0 — so the +8.47 the treated group showed was regression to the mean, and the control is what makes that visible.

**On a group selected for being extreme, improvement on re-measurement is guaranteed with no cause, so a before-after gain is not evidence a treatment worked — only its difference from a control selected the same way is.**

The self-test confirms the full pattern:

```
# $ python3 regression.py --check
#   bottom-group apparent effect = +8.86   top-group = -12.65
#   the selected-worst group 'improves' = True
#   the selected-best group 'declines' = True
#   the whole population barely moves = True (50.66 -> 48.93)
#   a control group improves as much as the treated = True (8.47 vs 9.24)
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · `python3 regression.py --check`

### What we did not settle

The simulation makes the true values knowable; in the real world you never see them, which is exactly why the artifact fools people. Real details we skipped: the size of the regression depends on the measurement's reliability — the noisier the score you selected on, the larger the pull, and a perfectly reliable measurement has none, so the fix is partly better measurement; the effect applies to any selection on an extreme, including selecting the *best* (a star performer who then disappoints) and selecting on a composite; and a proper design randomizes *which* extreme units are treated versus control, so the two groups regress identically and their difference is the clean effect — this demo's even/odd split stands in for that randomization. The dial here is selection on one noisy measurement; the fix everywhere is a control group and, ideally, randomization.

## Build

The pipeline in one paragraph: whenever you select a group because it scored extreme and then re-measure, expect regression toward the mean with no cause; never report the before-after change of that group as a treatment effect; instead select a control the same way, leave it untreated, and report the treated-minus-control difference as the effect. Randomize which selected units are treated versus control so the two regress identically.

We opened on the artifact. The comparison that is honest:

```
# modules/ai-for-science-and-data/code/data-inter-01/ — COMPLETE, run from that directory
$ python3 regression.py --control
  treated +8.47   control +9.24   -> effect ≈ 0
```

Now find it in your own data. Take any "we helped the worst cases and they improved" analysis — slowest queries you optimized, lowest-scoring outputs you re-prompted, worst-performing agents you tuned — and ask whether a control selected the same way would have improved anyway. Your number to beat is the **treated-minus-control difference**, not the treated group's before-after change. Simulate a zero-effect population, select the extremes, and confirm they move without any intervention. Bring back the apparent effect and the control-adjusted effect side by side. Good luck.

## Definition of done

- [ ] A population (real or simulated) measured twice, with the selection made on the first measurement
- [ ] The before-after change of an extreme-selected group, shown to move with no intervention
- [ ] A control group selected the same way and left untreated
- [ ] The treatment effect reported as treated-minus-control, not the treated group's raw change
- [ ] A demonstration that both extremes (worst and best) regress toward the mean
- [ ] `python3 regression.py --check` printing SELF-TEST PASS: bottom rises, top falls, population flat, control matches treated
- [ ] The apparent effect and the control-adjusted effect recorded side by side
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. The worst 40 units improved +8.86 with no intervention. Explain the mechanism in terms of signal and noise, and why the best 40 declined.
2. Why does the whole population stay flat while both selected extremes move a lot?
3. An analyst coached the bottom group and reports a +8.47 improvement. What is wrong with the causal claim, and what one comparison would correct it?
4. How does the reliability (noisiness) of the selection measurement change the size of the regression?
5. Your own analysis selected an extreme group. What was its before-after change, and what did a control-adjusted estimate say the real effect was?

## External resources

- Kahneman, *Thinking, Fast and Slow*, ch. 17 (regression to the mean) — https://us.macmillan.com/books/9780374533557/thinkingfastandslow — my summary: the flight-instructor example (praise seems to hurt, punishment seems to help, both are regression) and why the mind invents causal stories for it; read it for the cognitive pull that makes this error so durable.
- Galton, *Regression Towards Mediocrity in Hereditary Stature* (1886) — https://galton.org/essays/1880-1889/galton-1886-jaigi-regression-stature.pdf — my summary: the original discovery of the effect in heights of parents and children; read it for where the word "regression" in statistics comes from and the first clean demonstration.
- This hub, *evals-inter-01* — modules/evals-and-statistics/evals-inter-01.md — my summary: comparing two groups with an interval and a paired test; read it for how to decide whether the treated-minus-control difference here is real once you have a control, closing the loop from "you need a control" to "is the controlled effect significant".
