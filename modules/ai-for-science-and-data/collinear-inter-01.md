---
id: collinear-inter-01
title: Don't read an individual coefficient when its predictor is collinear — the fit pins only the sum, and the split (even its sign) is free
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: A regression with two predictors fits the outcome with b1·x1 + b2·x2, and we read each coefficient as an effect — b1 is the effect of x1 holding x2 fixed, b2 the effect of x2. That reading assumes the data contains rows where the two predictors disagree, so the fit can tell them apart. Collinearity is exactly the case where it can't: x1 and x2 move together, so no row separates them. In the extreme where x2 equals x1, the fitted value is b1·x1 + b2·x2 = (b1+b2)·x1 — it depends only on the sum of the coefficients, not on how that sum is split. Any two coefficient pairs with the same sum produce the identical prediction for every row and therefore the identical residual sum of squares; the fit literally cannot distinguish (2, 0) from (0, 2) from (5, −3). So the sum b1+b2 is identified — the data pins it — but the split is not: you can shovel weight from one coefficient to the other, even driving one negative, without moving the fit a hair. That is why a collinear coefficient's sign can flip between two equally-good fits, and why interpreting one ("x2 has a negative effect") is meaningless when an equally-good fit gives x2 a positive coefficient. The prediction is trustworthy; the attribution is not. On a fixture where x2 equals x1 and y is twice x1, every coefficient pair summing to 2 fits perfectly — including (5, −3) with a negative x2 coefficient — while a pair summing to anything else misfits.
eli5: Imagine two friends always show up to work together and always leave together — they are never apart, not for a single shift. At the end of the month the boss wants to figure out how much each one contributed. But there's no way to tell, because they were always both there or both gone: nothing in the records ever separates them. The boss can say the pair together produced a certain amount, and that number is solid. But splitting it — "she did most of it, he barely helped" — is pure guesswork, and you could just as easily claim the opposite and it would fit the records exactly as well. You could even say one of them had negative output. Two predictors that move together in a model are like those inseparable friends: the model knows what they do as a team, and knows nothing about who did what. Trust the team total; never trust the split.
---

## Why this module

We fit regressions partly to predict and partly to explain. The explaining lives in the coefficients: we point at b1 and say "a one-unit rise in x1, holding everything else fixed, moves y by b1." That sentence has a hidden requirement — that the data actually lets us hold everything else fixed while x1 moves. For it to be meaningful, there must be rows where x1 changes and the other predictors do not.

Collinearity is the failure of that requirement. When two predictors are correlated, they rarely disagree; when they are perfectly collinear, they never do. The data contains no example of x1 moving while x2 stays put, so the fit has no evidence about what x1 does on its own. It only ever saw them move together, so all it learned is what they do together.

The consequence is sharp and often surprising: the model's predictions can be excellent and completely trustworthy while its individual coefficients are meaningless — unstable, arbitrarily large, sign-flipped from what you expected. Practitioners see a coefficient come out negative for a predictor they know is positively related to the outcome and conclude something deep; usually it is just collinearity handing the weight to the other predictor. This module fits the same collinear data with several coefficient pairs and shows which quantities the data actually pins down.

**When two predictors move together, the fit learns their combined effect and nothing about the split — so the prediction is sound but any single coefficient's magnitude and sign are not evidence of anything.**

## Concepts

The key idea is identifiability: a quantity is identified if the data determines it, and unidentified if many values fit equally well. Under perfect collinearity the prediction is a function of b1+b2 alone, so the sum is identified and the individual coefficients are not. This is not a small-sample wobble that more data fixes — more collinear rows add more of the same non-separating evidence. It is structural: the information needed to split the effect is simply absent.

Contrast this with the attenuation problems elsewhere in this topic — a predictor measured with noise flattens its slope, a restricted range weakens a correlation. Those distort the estimate; collinearity does something different. It leaves the joint estimate perfect and destroys only the attribution between the two predictors. The fit is not wrong about y; it is silent about who caused what.

That silence is why the sign can flip. Among the coefficient pairs that fit identically, some give a predictor a positive coefficient and others a negative one — the data endorses all of them equally. So a negative coefficient on a variable you believe helps is not a discovery; it is one arbitrary point on a ridge of equally-good fits. The honest report is the combined effect and the prediction, plus the admission that the individual weights are not identified.

<svg role="img" aria-label="Two predictor columns x1 and x2 shown as identical bars row by row, with no row where they disagree, so an arrow to the coefficient split is marked no evidence" viewBox="0 0 440 150">
<text x="70" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">x1</text>
<text x="130" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">x2</text>
<rect x="55" y="30" width="12" height="10" fill="var(--s1)"/>
<rect x="115" y="30" width="12" height="10" fill="var(--s1)"/>
<rect x="55" y="48" width="24" height="10" fill="var(--s1)"/>
<rect x="115" y="48" width="24" height="10" fill="var(--s1)"/>
<rect x="55" y="66" width="36" height="10" fill="var(--s1)"/>
<rect x="115" y="66" width="36" height="10" fill="var(--s1)"/>
<rect x="55" y="84" width="48" height="10" fill="var(--s1)"/>
<rect x="115" y="84" width="48" height="10" fill="var(--s1)"/>
<text x="95" y="118" fill="var(--muted)" font-size="9" text-anchor="middle">every row: x1 = x2</text>
<text x="95" y="132" fill="var(--muted)" font-size="9" text-anchor="middle">(no separating row)</text>
<line x1="180" y1="62" x2="270" y2="62" stroke="var(--muted)" stroke-dasharray="3 3"/>
<rect x="272" y="40" width="150" height="24" fill="var(--panel)" stroke="var(--s1)"/>
<text x="347" y="56" fill="var(--ink)" font-size="10" text-anchor="middle">sum b1+b2: identified</text>
<rect x="272" y="76" width="150" height="24" fill="var(--panel)" stroke="var(--s2)"/>
<text x="347" y="92" fill="var(--ink)" font-size="10" text-anchor="middle">split b1, b2: no evidence</text>
</svg>
^ With no row where the predictors disagree, the data pins their combined effect but has nothing to say about the individual split.

**Identifiability is the frame: collinearity leaves the coefficient sum identified and the split unidentified, so the flipped sign you see is one arbitrary choice among infinitely many equally-good ones, not a finding.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/collinear-inter-01. The fixture makes x2 equal to x1 exactly — the extreme of collinearity — with y twice x1, so the true combined slope is 2.

```json filename=modules/ai-for-science-and-data/code/collinear-inter-01/collinear.json:3-6 COMPLETE
  "x1": [1, 2, 3, 4],
  "x2": [1, 2, 3, 4],
  "y": [2, 4, 6, 8],
  "coeff_pairs": [[2, 0], [0, 2], [1, 1], [5, -3], [3, 1]]
```

A prediction is just the coefficient pair applied row by row.

```python filename=modules/ai-for-science-and-data/code/collinear-inter-01/collinear.py:32-34 COMPLETE
def predict(b1, b2, x1, x2):
    """The fitted value row by row: b1*x1 + b2*x2."""
    return [b1 * a + b2 * b for a, b in zip(x1, x2)]
```

The residual sum of squares measures how badly a pair misfits — zero means a perfect fit.

```python filename=modules/ai-for-science-and-data/code/collinear-inter-01/collinear.py:37-39 COMPLETE
def sse(preds, y):
    """Residual sum of squares -- how badly a coefficient pair misfits."""
    return sum((p - t) ** 2 for p, t in zip(preds, y))
```

A pair is a perfect fit when its residual sum of squares is exactly zero.

```python filename=modules/ai-for-science-and-data/code/collinear-inter-01/collinear.py:42-43 COMPLETE
def perfect(pair, x1, x2, y):
    return sse(predict(pair[0], pair[1], x1, x2), y) == 0
```

Before running it, predict: every pair whose coefficients sum to 2 should fit perfectly (SSE 0), and the one pair that sums to something else should misfit. Run `--fits`:

```text filename=collinear.py --fits
FITS — each candidate coefficient pair scored against the same data
------------------------------------------------------------
  b1    b2    b1+b2   pred[0]   SSE
  2     0     2       2         0
  0     2     2       2         0
  1     1     2       2         0
  5     -3    2       2         0
  3     1     4       4         120
```

The prediction holds. Four wildly different coefficient pairs — including (5, −3) with a negative x2 coefficient — all fit perfectly, because all four sum to 2. Only (3, 1), which sums to 4, misfits with an SSE of 120. The fit cares about the sum and nothing else.

<svg role="img" aria-label="A ridge of equally-good coefficient pairs: points at (2,0), (1,1), (0,2), (5,-3) all lie on the line b1 plus b2 equals 2, all labeled SSE zero, while (3,1) sits off the line labeled SSE 120" viewBox="0 0 440 200">
<line x1="40" y1="170" x2="410" y2="170" stroke="var(--line)"/>
<line x1="40" y1="20" x2="40" y2="170" stroke="var(--line)"/>
<text x="225" y="192" fill="var(--muted)" font-size="10" text-anchor="middle">b1</text>
<text x="20" y="95" fill="var(--muted)" font-size="10" text-anchor="middle">b2</text>
<line x1="60" y1="60" x2="360" y2="160" stroke="var(--s1)" stroke-dasharray="4 3"/>
<text x="300" y="150" fill="var(--s1)" font-size="9">b1+b2=2</text>
<circle cx="120" cy="140" r="4" fill="var(--s1)"/>
<text x="120" y="132" fill="var(--ink)" font-size="8" text-anchor="middle">(1,1)</text>
<circle cx="160" cy="153" r="4" fill="var(--s1)"/>
<text x="168" y="149" fill="var(--ink)" font-size="8">(2,0)</text>
<circle cx="80" cy="127" r="4" fill="var(--s1)"/>
<text x="80" y="119" fill="var(--ink)" font-size="8" text-anchor="middle">(0,2)</text>
<circle cx="280" cy="60" r="4" fill="var(--s1)"/>
<text x="288" y="56" fill="var(--ink)" font-size="8">(5,-3)</text>
<text x="200" y="45" fill="var(--s1)" font-size="9">all SSE 0</text>
<circle cx="200" cy="90" r="4" fill="var(--s2)"/>
<text x="208" y="86" fill="var(--ink)" font-size="8">(3,1) SSE 120</text>
</svg>
^ Every pair on the line b1+b2=2 fits perfectly; the split along that line is free, and only leaving the line (like (3,1)) misfits.

Now the identifiability verdict — what the data pins versus what it leaves free. Run `--identify`:

```text filename=collinear.py --identify
IDENTIFY — what the collinear data pins down, and what it leaves free
--------------------------------------------------------------
  perfectly-fitting pairs: [(2, 0), (0, 2), (1, 1), (5, -3)]
  their coefficient sums:  [2]  (all equal -> the SUM is identified)
  their b1 values:         [0, 1, 2, 5]  (all different -> the SPLIT is not)
  sign-flip example:       (5, -3) fits perfectly yet gives x2 a negative coefficient
--------------------------------------------------------------
  the prediction is trustworthy; the individual coefficient is not
```

Every perfect fit shares the one sum, 2 — that is identified. Their b1 values span 0, 1, 2, 5 — the split is not. And (5, −3) shows the sign flip: a perfectly-good fit assigns x2 a negative coefficient even though x2 rises with y.

<svg role="img" aria-label="Two boxes: the coefficient sum labeled identified with a single pinned value 2, and the individual split labeled not identified spanning many values including a negative one" viewBox="0 0 440 130">
<rect x="20" y="30" width="180" height="70" fill="var(--panel)" stroke="var(--s1)"/>
<text x="110" y="52" fill="var(--ink)" font-size="11" text-anchor="middle">coefficient sum</text>
<text x="110" y="72" fill="var(--s1)" font-size="14" text-anchor="middle">= 2 (pinned)</text>
<text x="110" y="90" fill="var(--muted)" font-size="9" text-anchor="middle">identified</text>
<rect x="240" y="30" width="180" height="70" fill="var(--panel)" stroke="var(--s2)"/>
<text x="330" y="52" fill="var(--ink)" font-size="11" text-anchor="middle">individual split</text>
<text x="330" y="72" fill="var(--s2)" font-size="12" text-anchor="middle">0, 1, 2, 5, -3 ...</text>
<text x="330" y="90" fill="var(--muted)" font-size="9" text-anchor="middle">not identified</text>
</svg>
^ The data pins the sum to a single value and leaves the split spanning anything that adds to it — including a negative coefficient.

## Build

The self-test plants the failure and names each claim as a boolean flag. It collects the pairs that fit perfectly, then checks that they all share one coefficient sum (identified) while their individual coefficients differ (not identified) — including a negative one — and that despite differing coefficients they produce identical predictions.

```python filename=modules/ai-for-science-and-data/code/collinear-inter-01/collinear.py:88-96 COMPLETE
    sum_is_identified = len(set(b1 + b2 for b1, b2 in fits)) == 1
    print("  every perfect fit has the same coefficient sum = %s (%s)"
          % (sum_is_identified, sorted(set(b1 + b2 for b1, b2 in fits))))

    split_not_identified = len(set(b1 for b1, b2 in fits)) > 1
    print("  the individual b1 differs across perfect fits = %s" % split_not_identified)

    sign_can_flip = any(b2 < 0 for b1, b2 in fits)
    print("  a perfect fit exists with a negative x2 coefficient = %s" % sign_can_flip)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the data ever stops being collinear or the sum stops being pinned:

```text filename=collinear.py --check
SELF-TEST — collinear predictors identify only the coefficient sum; the individual split (and its sign) is free
--------------------------------------------------------------------------------------------------------------------
  the two predictors are collinear (x2 == x1) = True
  more than one coefficient pair fits perfectly = True (4 pairs)
  every perfect fit has the same coefficient sum = True ([2])
  the individual b1 differs across perfect fits = True
  a perfect fit exists with a negative x2 coefficient = True
  all perfect fits produce identical predictions = True
--------------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  predictors_collinear=True  many_perfect_fits=True  sum_is_identified=True  split_not_identified=True  sign_can_flip=True  predictions_identical=True
```

**The self-test asserts both halves at once — the sum is one value and the split is many, yet the predictions are identical — so it distinguishes real non-identifiability from a fit that is merely wrong.**

## Definition of done

You can state the requirement behind reading a coefficient as an effect: the data must contain rows where that predictor moves while the others hold, and explain why collinearity destroys it.
You can show that under perfect collinearity the fit depends only on b1+b2, and conclude the sum is identified and the split is not.
You can explain why a collinear coefficient's sign can flip between two equally-good fits, and why that flip is not a finding.
You can distinguish this from attenuation: collinearity leaves the prediction perfect and destroys only the attribution, whereas measurement error and range restriction distort the estimate itself.
You can say what to report under collinearity — the prediction and the combined effect — and what not to interpret — the individual coefficients.

## Boss fight

Break the collinearity: change `x2` to `[1, 2, 3, 5]` so the last row separates the two predictors, and rerun. Now no single coefficient pair fits every row unless it genuinely splits the effect the way the data demands — the fit gains one row where x1 and x2 disagree, and that one row is enough to start pinning the split. The perfectly-fitting set shrinks, `split_not_identified` moves toward false, and the coefficients become interpretable to the degree the predictors actually diverge. That is the cure in miniature: identifiability is bought with rows where the predictors disagree.

Now go the other way. Add a third perfectly-correlated predictor x3 equal to x1 and extend the pairs to triples. The fit now depends only on b1+b2+b3, so the ridge of equally-good fits grows from a line to a plane — even more freedom in the split, the sum still pinned. The lesson scales: every extra collinear predictor adds a dimension of arbitrariness to the coefficients while leaving the prediction and the combined effect exactly as identified as before.

**Identifiability of the split is bought one disagreeing row at a time — perfect collinearity gives zero such rows, so the coefficients are maximally free; adding a separating row starts to pin them, adding a collinear predictor frees them further.**

## External resources

Most regression textbooks cover multicollinearity and the variance inflation factor, which quantifies how much a predictor's coefficient variance is inflated by its correlation with the others.
Frank Harrell's "Regression Modeling Strategies" argues at length against interpreting individual coefficients under collinearity and in favor of reporting combined effects and predictions.
The topic's own modules on range restriction and on measurement error in a predictor cover the attenuation failures this one is deliberately contrasted against — same topic, different mechanism.
