---
id: orthoexp-inter-01
title: Randomize concurrent experiments independently — two overlapping A/B tests confound each other unless assignment is orthogonal
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: An A/B test measures its effect as the treated mean minus the control mean, and that difference equals the experiment's own effect only if its two arms are balanced on everything else. Randomization buys that balance for a single experiment — but two experiments running on the same users at the same time break it unless they are randomized independently. If assignment to experiment X and assignment to experiment Y are correlated — users put in X's treatment tend to also be in Y's treatment — then X's treated arm carries a higher fraction of Y-treated users than X's control arm, so Y is imbalanced across X's arms and Y's effect leaks into X's measured effect. The bias is exactly the imbalance in Y-treatment fraction between X's arms times Y's true effect, and it is symmetric: X leaks into Y the same way. On the fixture X's true effect is 2 and Y's is 5; under correlated assignment X's treated arm is 80% Y-treated versus 20% for its control (imbalance 0.60), so X measures 2 + 0.60·5 = 5.00 and Y measures 6.20 — both inflated. Orthogonal assignment, X and Y by independent coins, makes each of X's arms 50% Y-treated, so Y's effect is equal in both arms and cancels in the difference: X measures 2.00 and Y measures 5.00. The rule: randomize concurrent experiments independently so each one's arms are balanced on every other experiment, and any number of experiments can then share the same traffic without confounding each other.
eli5: Imagine two taste tests running at once: one compares a new cookie recipe, the other compares a new juice. If you accidentally give the new cookie and the new juice to the same kids, and the old cookie and old juice to the other kids, then when the "new cookie" group is happier you can't tell if it was the cookie or the juice — they always came together. The fix is to mix it up so that within the cookie test, half the kids got new juice and half got old juice on both sides. Now the juice helps both cookie groups equally, so it cancels out, and any difference left is really about the cookie. Flip a separate coin for each test and they stop stepping on each other.
---

## Why this module

Big products do not run one experiment at a time; they run dozens or hundreds concurrently, all on the same users. That is only safe because of a property that is easy to assume and easy to lose: each experiment's arms are balanced on every other experiment. When that holds, all the other experiments are just background that affects both of your arms equally and cancels. When it fails, the experiments contaminate each other's results.

It fails whenever two experiments' assignments are correlated. If the same coin, or two correlated coins, decides both, then being in one experiment's treatment predicts being in the other's, and each experiment's treated and control arms differ not only in their own treatment but in how much of the other treatment they carry. The other experiment becomes a confounder, and its effect is added to yours.

This module runs two experiments, X and Y, on the same users two ways. Under correlated assignment X's true effect of 2 is measured as 5 — it has absorbed most of Y's effect of 5 — and Y is inflated too. Under orthogonal assignment, independent coins for X and Y, each recovers its own effect exactly. Then it shows that the bias is precisely the arm imbalance times the other effect.

**Concurrency is not the problem and isolation is not the fix — the fix is independence, because two experiments can share every user safely as long as neither one's assignment predicts the other's.**

## Concepts

Start from why randomization works for one experiment. Splitting users at random makes the treated and control arms statistically identical on everything except the treatment, so their difference in outcome is the treatment's effect and nothing else. The guarantee is balance: every other variable is present in equal proportion in both arms.

A second concurrent experiment is just another variable, and the guarantee extends to it only if the two randomizations are independent. Picture the four cells of the two-by-two: X-treated crossed with Y-treated, X-treated with Y-control, and so on. Experiment X's effect is the difference between its treated arm (the top two cells) and its control arm (the bottom two). That difference is clean only if the Y-treated fraction is the same in X's treated arm as in X's control arm.

Correlated assignment destroys that equality. If X-treated users are disproportionately Y-treated, then X's treated arm is richer in Y-treatment than its control arm, and Y-treatment raises outcomes. So X's treated arm is lifted partly by X and partly by the extra Y-treatment it carries, and the treated-minus-control difference counts both. The amount of the leak is the difference in Y-treatment fraction between the arms, scaled by how much Y-treatment actually moves the outcome — the imbalance times Y's true effect.

Independence restores it. Flip a separate coin for Y, and within each of X's arms half the users are Y-treated — the same fraction on both sides. Now Y's effect adds the same amount to X's treated arm and X's control arm, and it subtracts out of their difference. X is measured cleanly no matter how large Y's effect is, and the argument holds for any number of independently-randomized experiments sharing the traffic.

<svg role="img" aria-label="Two two-by-two grids of experiment X arm by experiment Y arm. The correlated grid has large counts on the diagonal cells (X-treat Y-treat and X-control Y-control) and small counts off-diagonal, so X-treated is mostly Y-treated. The orthogonal grid has equal counts in all four cells" viewBox="0 0 640 250">
<text x="160" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">correlated</text>
<text x="40" y="70" fill="var(--muted)" font-size="9">X-treat</text>
<text x="40" y="130" fill="var(--muted)" font-size="9">X-ctrl</text>
<text x="95" y="45" fill="var(--muted)" font-size="9" text-anchor="middle">Y-treat</text>
<text x="200" y="45" fill="var(--muted)" font-size="9" text-anchor="middle">Y-ctrl</text>
<rect x="70" y="52" width="90" height="48" fill="var(--s2)" opacity="0.55"/>
<text x="115" y="80" fill="var(--ink)" font-size="12" text-anchor="middle">40</text>
<rect x="160" y="52" width="90" height="48" fill="var(--s2)" opacity="0.18"/>
<text x="205" y="80" fill="var(--ink)" font-size="12" text-anchor="middle">10</text>
<rect x="70" y="100" width="90" height="48" fill="var(--s2)" opacity="0.18"/>
<text x="115" y="128" fill="var(--ink)" font-size="12" text-anchor="middle">10</text>
<rect x="160" y="100" width="90" height="48" fill="var(--s2)" opacity="0.55"/>
<text x="205" y="128" fill="var(--ink)" font-size="12" text-anchor="middle">40</text>
<text x="160" y="175" fill="var(--muted)" font-size="10" text-anchor="middle">X-treat is 80% Y-treat</text>
<text x="480" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">orthogonal</text>
<rect x="390" y="52" width="90" height="48" fill="var(--s1)" opacity="0.4"/>
<text x="435" y="80" fill="var(--ink)" font-size="12" text-anchor="middle">25</text>
<rect x="480" y="52" width="90" height="48" fill="var(--s1)" opacity="0.4"/>
<text x="525" y="80" fill="var(--ink)" font-size="12" text-anchor="middle">25</text>
<rect x="390" y="100" width="90" height="48" fill="var(--s1)" opacity="0.4"/>
<text x="435" y="128" fill="var(--ink)" font-size="12" text-anchor="middle">25</text>
<rect x="480" y="100" width="90" height="48" fill="var(--s1)" opacity="0.4"/>
<text x="525" y="128" fill="var(--ink)" font-size="12" text-anchor="middle">25</text>
<text x="480" y="175" fill="var(--muted)" font-size="10" text-anchor="middle">each X arm is 50% Y-treat</text>
</svg>
^ Correlated assignment piles users on the diagonal, so X's treated arm is mostly Y-treated; orthogonal assignment fills all four cells equally, balancing Y across X's arms.

**A concurrent experiment confounds yours exactly to the degree your assignment predicts its assignment, so the whole game is making the two randomizations independent.**

## Worked example

The fixture gives each experiment's true effect and the user counts in the four cells under a correlated and an orthogonal design.

```json filename=modules/evals-and-statistics/code/orthoexp-inter-01/orthoexp.json:3-7 COMPLETE
  "base": 10.0,
  "effect_x": 2.0,
  "effect_y": 5.0,
  "correlated_cells": {"xt_yt": 40, "xt_yc": 10, "xc_yt": 10, "xc_yc": 40},
  "orthogonal_cells": {"xt_yt": 25, "xt_yc": 25, "xc_yt": 25, "xc_yc": 25}
```

Each cell's outcome is the baseline plus whichever treatments that cell received — the effects are real and additive.

```python filename=modules/evals-and-statistics/code/orthoexp-inter-01/orthoexp.py:30-32 COMPLETE
def cell_outcome(data, in_x, in_y):
    """The deterministic outcome in a cell: baseline plus each experiment's effect if that arm is treated."""
    return data["base"] + (data["effect_x"] if in_x else 0.0) + (data["effect_y"] if in_y else 0.0)
```

Each experiment measures its effect as its treated-arm mean minus its control-arm mean.

```python filename=modules/evals-and-statistics/code/orthoexp-inter-01/orthoexp.py:46-49 COMPLETE
def measured_effect(data, cells, which):
    """What experiment `which` measures on these cells: treated-arm mean minus control-arm mean."""
    treat_mean, control_mean = arm_means(data, cells, which)
    return treat_mean - control_mean
```

The confound is the imbalance in the other experiment's treatment between the two arms.

```python filename=modules/evals-and-statistics/code/orthoexp-inter-01/orthoexp.py:52-60 COMPLETE
def other_arm_fraction(cells, which):
    """Fraction of the OTHER experiment's treatment in each of `which`'s two arms -- balance iff equal."""
    if which == "x":
        t = cells["xt_yt"] / (cells["xt_yt"] + cells["xt_yc"])   # Y-treat share among X-treated
        c = cells["xc_yt"] / (cells["xc_yt"] + cells["xc_yc"])   # Y-treat share among X-control
    else:
        t = cells["xt_yt"] / (cells["xt_yt"] + cells["xc_yt"])
        c = cells["xt_yc"] / (cells["xt_yc"] + cells["xc_yc"])
    return t, c
```

Under the correlated design, X's arms differ sharply in Y-treatment, and both measured effects are inflated.

```text filename=orthoexp.py --correlated
CORRELATED — X and Y assignment overlap (X-treated are mostly Y-treated)
----------------------------------------------------------------
  X arms' Y-treated share: treated 0.80 vs control 0.20  (imbalance 0.60)
  measured X effect = 5.00   (true 2.0)
  measured Y effect = 6.20   (true 5.0)
----------------------------------------------------------------
  Y is imbalanced across X's arms, so Y's effect leaks into X's (and vice versa)
```

X measures 5.00 against a true 2.0 — the extra 3.00 is the imbalance 0.60 times Y's effect 5.0, Y's effect leaking straight in. Orthogonal assignment balances the arms.

```text filename=orthoexp.py --orthogonal
ORTHOGONAL — X and Y assigned by independent coins
----------------------------------------------------------------
  X arms' Y-treated share: treated 0.50 vs control 0.50  (imbalance 0.00)
  measured X effect = 2.00   (true 2.0)
  measured Y effect = 5.00   (true 5.0)
----------------------------------------------------------------
  each arm has the same share of the other's treatment, so the other effect cancels
```

Zero imbalance, and both effects come back exactly right. The figure shows the true and measured effects side by side.

<svg role="img" aria-label="A bar chart comparing true and measured effects. For experiment X, true is 2 and measured under correlated is 5, under orthogonal is 2. For experiment Y, true is 5 and measured under correlated is 6.2, under orthogonal is 5" viewBox="0 0 640 250">
<line x1="60" y1="200" x2="600" y2="200" stroke="var(--line)" stroke-width="1"/>
<text x="180" y="222" fill="var(--muted)" font-size="11" text-anchor="middle">experiment X (true 2)</text>
<rect x="90" y="160" width="50" height="40" fill="var(--ink)"/>
<text x="115" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">2.0 true</text>
<rect x="160" y="100" width="50" height="100" fill="var(--s2)"/>
<text x="185" y="90" fill="var(--muted)" font-size="10" text-anchor="middle">5.0 corr</text>
<rect x="230" y="160" width="50" height="40" fill="var(--s1)"/>
<text x="255" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">2.0 orth</text>
<text x="460" y="222" fill="var(--muted)" font-size="11" text-anchor="middle">experiment Y (true 5)</text>
<rect x="370" y="100" width="50" height="100" fill="var(--ink)"/>
<text x="395" y="90" fill="var(--muted)" font-size="10" text-anchor="middle">5.0 true</text>
<rect x="440" y="76" width="50" height="124" fill="var(--s2)"/>
<text x="465" y="66" fill="var(--muted)" font-size="10" text-anchor="middle">6.2 corr</text>
<rect x="510" y="100" width="50" height="100" fill="var(--s1)"/>
<text x="535" y="90" fill="var(--muted)" font-size="10" text-anchor="middle">5.0 orth</text>
</svg>
^ The correlated bars overshoot the true effects; the orthogonal bars land exactly on them for both experiments at once.

**The correlated design did not add noise — it added a precise, repeatable bias equal to the arm imbalance times the other experiment's effect, which is why it survives any amount of data.**

## Build

The self-test pins the mechanism: correlated assignment biases both estimates and leaves X's arms imbalanced on Y, while orthogonal assignment balances the arms and recovers both true effects.

```python filename=modules/evals-and-statistics/code/orthoexp-inter-01/orthoexp.py:93-101 COMPLETE
    corr_x_biased = abs(measured_effect(data, corr, "x") - data["effect_x"]) > 1e-9
    print("  correlated design biases X's estimate = %s (measured %.2f vs true %.1f)" % (corr_x_biased, measured_effect(data, corr, "x"), data["effect_x"]))

    corr_y_biased = abs(measured_effect(data, corr, "y") - data["effect_y"]) > 1e-9
    print("  correlated design biases Y's estimate = %s (measured %.2f vs true %.1f)" % (corr_y_biased, measured_effect(data, corr, "y"), data["effect_y"]))

    tx, cx = other_arm_fraction(corr, "x")
    corr_arms_imbalanced = abs(tx - cx) > 1e-9
    print("  correlated design's X arms are imbalanced on Y = %s (%.2f vs %.2f)" % (corr_arms_imbalanced, tx, cx))
```

Running the check confirms all five flags.

```text filename=orthoexp.py --check
SELF-TEST — correlated assignment biases both estimates while orthogonal assignment recovers the true effects
----------------------------------------------------------------------------------------------------------------
  correlated design biases X's estimate = True (measured 5.00 vs true 2.0)
  correlated design biases Y's estimate = True (measured 6.20 vs true 5.0)
  correlated design's X arms are imbalanced on Y = True (0.80 vs 0.20)
  orthogonal design recovers both true effects = True (X 2.00, Y 5.00)
  orthogonal design's X arms are balanced on Y = True (0.50 vs 0.50)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  corr_x_biased=True  corr_y_biased=True  corr_arms_imbalanced=True  orth_effects_clean=True  orth_arms_balanced=True
```

**The check reads the confound directly off the arm fractions — 0.80 versus 0.20 under correlation, 0.50 versus 0.50 under independence — so the bias is not a mystery to be discovered in the outcome but a design property visible before any outcome is measured.**

## Definition of done

You are done when concurrent experiments are randomized independently of one another, so that no experiment's assignment carries information about any other's, and each experiment's arms are balanced on all the others.

The standard way to guarantee this at scale is an overlapping-experiment platform: hash each user with a different, experiment-specific salt (or seed) so that the split for experiment X is statistically independent of the split for experiment Y, and check the independence by confirming each experiment's arms are balanced on the others (the same sample-ratio and covariate checks you already run, applied across experiments). When two experiments genuinely cannot be independent — they touch the same surface and one's treatment forces the other's — put them in the same mutually-exclusive layer so a user is in at most one, trading the ability to run them together for a clean estimate of each. And when you do want to measure how two treatments combine, that is a deliberate factorial design with an interaction term, not an accident of correlated assignment.

<svg role="img" aria-label="A diagram of a user passing through two independent hash functions, one salted for experiment X and one for experiment Y, producing independent arm assignments, so the two experiments are orthogonal" viewBox="0 0 640 190">
<rect x="40" y="80" width="80" height="40" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="80" y="104" fill="var(--ink)" font-size="11" text-anchor="middle">user id</text>
<line x1="120" y1="90" x2="170" y2="60" stroke="var(--line)" stroke-width="1"/>
<line x1="120" y1="110" x2="170" y2="140" stroke="var(--line)" stroke-width="1"/>
<rect x="170" y="40" width="180" height="40" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="6"/>
<text x="260" y="64" fill="var(--ink)" font-size="10" text-anchor="middle">hash(id + salt_X) → X arm</text>
<rect x="170" y="120" width="180" height="40" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="260" y="144" fill="var(--ink)" font-size="10" text-anchor="middle">hash(id + salt_Y) → Y arm</text>
<line x1="350" y1="60" x2="430" y2="90" stroke="var(--s2)" stroke-width="1"/>
<line x1="350" y1="140" x2="430" y2="110" stroke="var(--s1)" stroke-width="1"/>
<rect x="430" y="80" width="170" height="40" fill="var(--panel)" stroke="var(--ink)" stroke-width="1.5" rx="6"/>
<text x="515" y="100" fill="var(--ink)" font-size="10" text-anchor="middle">independent → orthogonal</text>
<text x="515" y="114" fill="var(--muted)" font-size="9" text-anchor="middle">arms balanced on each other</text>
</svg>
^ Different salts make the two assignments independent, so every experiment's arms are balanced on every other — the platform-level version of flipping a separate coin.

**The safe way to run many experiments on the same users is not fewer experiments but independent randomization, and a per-experiment salt is what turns "concurrent" into "orthogonal."**

## Boss fight

Your turn: make the correlation partial and watch the bias scale with it. Change the correlated cells so X-treated is 60% Y-treated and X-control is 40% Y-treated — an imbalance of 0.20 instead of 0.60 — and rerun `--correlated`. X's measured effect drops from 5.0 toward 3.0, because the bias is imbalance times Y's effect, 0.20 times 5.0 equals 1.0 on top of the true 2.0. The confound is not all-or-nothing; it is proportional to exactly how much the two assignments overlap, so even a mild correlation between experiments injects a mild, invisible bias into both.

Then flip the sign and see it turn a real effect negative. Keep the 0.60 imbalance but make Y's effect −10 instead of +5. Now X's treated arm, being richer in Y-treatment, is dragged down by Y's harm, and X's measured effect becomes 2.0 + 0.60·(−10) = −4.0 — X looks harmful when it genuinely helps. This is the case that makes correlated concurrent experiments genuinely dangerous rather than merely noisy: a confounding experiment with a large effect of either sign can not only inflate or deflate your estimate but flip its conclusion, and nothing in your own experiment's data reveals it. Only knowing that the other experiment was imbalanced across your arms — a design fact, checkable before you ever look at the outcome — tells you the estimate cannot be trusted.

**A correlated concurrent experiment can flip your result's sign, and because the damage lives in the assignment and not the outcome, no amount of staring at your own metric will show it — you have to check the design, not the data.**

## External resources

Tang and colleagues' "Overlapping Experiment Infrastructure: More, Better, Faster Experimentation" (Google, KDD 2010) is the canonical description of running many concurrent experiments with independent (and, where needed, layered) randomization.

Kohavi, Tang, and Xu's "Trustworthy Online Controlled Experiments" devotes attention to interactions between concurrent experiments and to the sample-ratio and balance checks that detect a broken randomization.

Any treatment of factorial experimental design explains the flip side — when you deliberately want to estimate how two treatments interact, you cross them on purpose and fit an interaction term, which is the intended version of the accident this module prevents.
