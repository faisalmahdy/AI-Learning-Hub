---
id: transcorr-inter-01
title: Correlation is not transitive — A tracks B and B tracks C, yet A can correlate negatively with C
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: It is tempting to treat correlation like an ordering that chains: if A moves with B and B moves with C, surely A moves with C. Correlation does not chain, because it measures the alignment between two variables' deviations from their means, and alignment is a direction, not a rank. A can align with B, and C can align with B, while A and C align with B along partly opposing directions — so A and C pull against each other even though both genuinely track B. There is an exact rule: given the correlations r(A,B) and r(B,C), the third correlation r(A,C) is not determined but confined to an interval centered on the product r(A,B)·r(B,C), reaching a square-root term sqrt((1−r(A,B)²)(1−r(B,C)²)) to either side. When r(A,B) and r(B,C) are only moderate, the product is small and the square-root term is large, so the lower end of the interval is negative — a negative r(A,C) is permitted, not paradoxical. On a fixture of three variables over five units, built so A is B plus a vector orthogonal to B and C is B minus that same vector, r(A,B) and r(B,C) both come out at +0.6455 while r(A,C) is −0.1667 — exactly the interval's lower bound, the sharpest possible violation of the transitive intuition.
eli5: Imagine three friends standing around a campfire. Ann faces the fire; so does Cara; and Ben, in the middle, also faces the fire — so each of them is "aligned with Ben" in the sense of all looking toward the same flames. But Ann is on the north side looking south, and Cara is on the south side looking north, so Ann and Cara are actually facing opposite directions — pointed away from each other — even though both are pointed at the fire between them. "Faces the same fire as Ben" does not make Ann and Cara face the same way. Correlation is like that: two things can each line up with a middle thing while lining up against each other, so A matching B and B matching C does not mean A matches C.
---

## Why this module

Correlation gets used, informally, as if it were transitive — as if "A is correlated with B" and "B is correlated with C" chained into "A is correlated with C," the way "A is taller than B" and "B is taller than C" chain into "A is taller than C." That chaining feels so natural that people reason across it without noticing: this biomarker tracks that outcome, and that outcome tracks a third thing, so the biomarker must track the third thing.

It does not follow, and the reason is what correlation actually measures. It is not a rank or an order; it is the alignment between two variables' deviations from their own means — how much, when one is above its average, the other tends to be above its average too. Alignment is a direction in the space of deviations, and directions do not chain the way ranks do.

Two variables can both align with a third while aligning with each other poorly, or even oppositely. A can sit on one side of B's variation and C on the other, so both correlate with B yet move against each other. The transitive intuition quietly assumes the alignments all point the same way; nothing guarantees that, and when they do not, the third correlation can come out zero or negative even though the first two are strongly positive.

**Correlation measures the alignment of two variables' deviations, which is a direction, not a rank — so it does not chain: A correlating with B and B with C does not force A to correlate with C, and A–C can even be negative.**

## Concepts

Picture each variable's deviations as an arrow. Two variables are perfectly correlated when their arrows point the same way, uncorrelated when the arrows are at right angles, and perfectly anti-correlated when they point opposite ways. The correlation is, exactly, the cosine of the angle between the two arrows. Now the transitivity question becomes geometric: if A's arrow is within some angle of B's, and C's arrow is within some angle of B's, what can the angle between A and C be?

<svg role="img" aria-label="Three arrows from a common origin. B points up. A points up and to the left, at a moderate angle from B. C points up and to the right, at the same moderate angle from B on the other side. A and C are far apart in angle, pointing away from each other, so their cosine is negative even though each is close to B." viewBox="0 0 440 150">
<line x1="220" y1="130" x2="220" y2="30" stroke="var(--ink)"/>
<text x="220" y="22" fill="var(--ink)" font-size="9" text-anchor="middle">B</text>
<line x1="220" y1="130" x2="120" y2="70" stroke="var(--s1)"/>
<text x="110" y="66" fill="var(--s1)" font-size="9" text-anchor="end">A</text>
<line x1="220" y1="130" x2="320" y2="70" stroke="var(--s2)"/>
<text x="330" y="66" fill="var(--s2)" font-size="9">C</text>
<path d="M205 88 A 40 40 0 0 1 220 90" fill="none" stroke="var(--muted)"/>
<text x="185" y="104" fill="var(--muted)" font-size="7">A–B ~50&#176;</text>
<path d="M220 90 A 40 40 0 0 1 235 88" fill="none" stroke="var(--muted)"/>
<text x="255" y="104" fill="var(--muted)" font-size="7">B–C ~50&#176;</text>
<text x="220" y="145" fill="var(--muted)" font-size="8" text-anchor="middle">A–C ~100&#176;: cosine negative, though each is close to B</text>
</svg>
^ Correlation is the cosine of the angle between the deviation arrows: A and C each sit about 50° from B, on opposite sides, so they are about 100° apart — a negative correlation — even though both track B.

The geometry gives the exact rule. If A is at angle α from B and C is at angle β from B, then A and C are somewhere between |α − β| and α + β apart. Translating from angles back to correlations (cosines), r(A,C) is confined to the interval centered on the product r(A,B)·r(B,C), reaching sqrt((1 − r(A,B)²)(1 − r(B,C)²)) to each side. The correlations do constrain the third one — but to a range, not a value.

Whether that range dips below zero is the whole question. When r(A,B) and r(B,C) are near 1, the arrows are nearly parallel to B and hence to each other, the product is near 1, the square-root term is near 0, and r(A,C) is forced high. When they are only moderate, the arrows have a lot of angular freedom, the square-root term is large, and the lower end of the range is negative — so A and C can point apart. Strong-enough correlations are "nearly transitive"; moderate ones are not.

<svg role="img" aria-label="A number line for r(A,C) from minus 1 to plus 1. Given r(A,B) and r(B,C) both 0.65, an allowed band is shaded from about minus 0.17 up to plus 1.0, centered on the product 0.42. A marker at minus 0.17 shows where the fixture lands, at the low end." viewBox="0 0 440 120">
<line x1="30" y1="60" x2="410" y2="60" stroke="var(--line)"/>
<text x="30" y="78" fill="var(--muted)" font-size="8" text-anchor="middle">-1</text>
<text x="220" y="78" fill="var(--muted)" font-size="8" text-anchor="middle">0</text>
<text x="410" y="78" fill="var(--muted)" font-size="8" text-anchor="middle">+1</text>
<rect x="188" y="54" width="222" height="12" fill="var(--panel)" stroke="var(--s1)"/>
<text x="300" y="42" fill="var(--s1)" font-size="8" text-anchor="middle">allowed range for r(A,C)</text>
<circle cx="298" cy="60" r="3" fill="var(--muted)"/>
<text x="298" y="98" fill="var(--muted)" font-size="7" text-anchor="middle">product 0.42</text>
<circle cx="188" cy="60" r="4" fill="var(--s2)"/>
<text x="188" y="98" fill="var(--s2)" font-size="7" text-anchor="middle">fixture -0.17</text>
</svg>
^ With r(A,B) and r(B,C) both 0.65, r(A,C) is only pinned to a wide band from −0.17 to +1.0, centered on the product 0.42 — the fixture sits at the negative low end.

**The correlation r(A,C) is confined to an interval centered on r(A,B)·r(B,C), reaching sqrt((1−r(A,B)²)(1−r(B,C)²)) each way; moderate correlations make that interval's lower bound negative, so transitivity holds only when the first two correlations are strong enough.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/transcorr-inter-01. The fixture is three variables measured over the same five units.

```json filename=modules/ai-for-science-and-data/code/transcorr-inter-01/transcorr.json:3-5 COMPLETE
  "a": [3, -1, 2, -3, -1],
  "b": [2, 1, 0, -1, -2],
  "c": [1, 3, -2, 1, -3]
```

Both correlations start from the mean, the center each variable's deviations are measured against.

```python filename=modules/ai-for-science-and-data/code/transcorr-inter-01/transcorr.py:31-32 COMPLETE
def mean(xs):
    return sum(xs) / len(xs)
```

Correlation is the alignment of the two variables' deviations from their means.

```python filename=modules/ai-for-science-and-data/code/transcorr-inter-01/transcorr.py:35-42 COMPLETE
def correlation(xs, ys):
    """Pearson correlation: the alignment of the two variables' deviations from their means."""
    mx, my = mean(xs), mean(ys)
    dx = [x - mx for x in xs]
    dy = [y - my for y in ys]
    num = sum(a * b for a, b in zip(dx, dy))
    den = math.sqrt(sum(a * a for a in dx) * sum(b * b for b in dy))
    return num / den if den else 0.0
```

The transitive interval is the exact range r(A,C) can occupy given the other two correlations.

```python filename=modules/ai-for-science-and-data/code/transcorr-inter-01/transcorr.py:45-49 COMPLETE
def transitive_interval(r_ab, r_bc):
    """Given r(A,B) and r(B,C), the closed interval r(A,C) must lie in."""
    center = r_ab * r_bc
    spread = math.sqrt((1 - r_ab ** 2) * (1 - r_bc ** 2))
    return center - spread, center + spread
```

Before running it, predict: A and B are built to track each other, and so are B and C, so both should be strongly positive — and the transitive intuition says A and C should be positive too. Run `--corr`:

```text filename=transcorr.py --corr
CORR — the three pairwise correlations
------------------------------------------------
  r(A,B) = +0.6455  (A tracks B, strongly)
  r(B,C) = +0.6455  (B tracks C, strongly)
  r(A,C) = -0.1667  (A vs C)
------------------------------------------------
  transitive intuition predicts r(A,C) positive; it is -0.1667
```

Two of the three predictions hold and the important one fails. A and B correlate at +0.6455, B and C at +0.6455 — both genuinely strong. But A and C correlate at −0.1667: negative. Anyone who reasoned "A tracks B, B tracks C, so A tracks C" would have concluded A and C move together, and they move apart. The chain broke at the last link, silently, with no error and two perfectly real positive correlations upstream.

The bound view shows this is not a fluke of these particular numbers but the extreme the math permits. Run `--bound`:

```text filename=transcorr.py --bound
BOUND — the interval r(A,C) is confined to, given r(A,B)=0.6455 and r(B,C)=0.6455
--------------------------------------------------------
  lowest possible r(A,C)  = -0.1667
  product r(A,B)*r(B,C)   = +0.4167  (the interval's center)
  highest possible r(A,C) = +1.0000
  actual r(A,C)           = -0.1667
--------------------------------------------------------
  the actual value sits at the low end -- a negative r(A,C) is allowed, not a paradox
```

Given r(A,B) and r(B,C) of 0.6455 each, r(A,C) could be anything from −0.1667 to +1.0000. The transitive intuition fixates on the top of that range; the fixture is built to sit at the bottom, −0.1667, exactly the lowest value the two correlations allow. The interval's center — the product 0.4167 — is the "expected" r(A,C) if the third alignment were random, and even that is far below what transitivity assumes. The negative correlation is not a paradox; it is a legal point in a range that was always wide.

<svg role="img" aria-label="A triangle with vertices A, B, C. The A-B edge is labeled plus 0.65 and drawn solid, the B-C edge plus 0.65 solid, and the A-C edge minus 0.17 drawn dashed in a contrasting color to mark it as negative." viewBox="0 0 440 150">
<line x1="120" y1="120" x2="220" y2="30" stroke="var(--s1)" stroke-width="2"/>
<text x="150" y="70" fill="var(--s1)" font-size="9">+0.65</text>
<line x1="220" y1="30" x2="320" y2="120" stroke="var(--s1)" stroke-width="2"/>
<text x="285" y="70" fill="var(--s1)" font-size="9">+0.65</text>
<line x1="120" y1="120" x2="320" y2="120" stroke="var(--s2)" stroke-dasharray="5 3" stroke-width="2"/>
<text x="220" y="138" fill="var(--s2)" font-size="9" text-anchor="middle">-0.17</text>
<circle cx="120" cy="120" r="4" fill="var(--ink)"/>
<text x="108" y="124" fill="var(--ink)" font-size="10" text-anchor="end">A</text>
<circle cx="220" cy="30" r="4" fill="var(--ink)"/>
<text x="220" y="24" fill="var(--ink)" font-size="10" text-anchor="middle">B</text>
<circle cx="320" cy="120" r="4" fill="var(--ink)"/>
<text x="332" y="124" fill="var(--ink)" font-size="10">C</text>
</svg>
^ Two strong positive edges (A–B and B–C) and one negative edge (A–C) in the same triple — the correlation structure the transitive intuition says cannot exist.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that r(A,B) is strongly positive, that r(B,C) is strongly positive, that the transitive intuition (the product) is positive, that r(A,C) is nonetheless negative, and that r(A,C) sits exactly at the interval's lower bound.

```python filename=modules/ai-for-science-and-data/code/transcorr-inter-01/transcorr.py:93-106 COMPLETE
    ab_strong_positive = r_ab > 0.5
    print("  r(A,B) is strongly positive = %s (%+.4f)" % (ab_strong_positive, r_ab))

    bc_strong_positive = r_bc > 0.5
    print("  r(B,C) is strongly positive = %s (%+.4f)" % (bc_strong_positive, r_bc))

    transitive_intuition_positive = r_ab * r_bc > 0
    print("  the transitive intuition (product) is positive = %s (%+.4f)" % (transitive_intuition_positive, r_ab * r_bc))

    ac_actually_negative = r_ac < 0
    print("  yet r(A,C) is actually negative = %s (%+.4f)" % (ac_actually_negative, r_ac))

    ac_at_theoretical_min = abs(r_ac - lo) < 1e-9
    print("  r(A,C) sits exactly at the interval's lower bound = %s (%+.4f vs %+.4f)" % (ac_at_theoretical_min, r_ac, lo))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the two upstream correlations ever weakened or r(A,C) ever climbed off the bound:

```text filename=transcorr.py --check
SELF-TEST — two strong positive correlations coexist with a negative third, which sits at the theoretical minimum the bound allows
----------------------------------------------------------------------------------------------------------------
  r(A,B) is strongly positive = True (+0.6455)
  r(B,C) is strongly positive = True (+0.6455)
  the transitive intuition (product) is positive = True (+0.4167)
  yet r(A,C) is actually negative = True (-0.1667)
  r(A,C) sits exactly at the interval's lower bound = True (-0.1667 vs -0.1667)
```

**The self-test proves both halves at once: the two upstream correlations are strong and positive, and the third is negative and sits exactly on the interval's lower bound — so a pass certifies the violation is the mathematically extreme case, not a rounding accident of these five numbers.**

## Definition of done

You can explain why correlation is an alignment (a cosine of an angle), not a rank, and why that means it does not chain.
You can state the interval r(A,C) is confined to given r(A,B) and r(B,C), and identify its center and half-width.
You can explain why strong correlations are nearly transitive while moderate ones are not.
You can predict, from two moderate positive correlations, that the third can be zero or negative, and give the geometric reason.
You can recognize the everyday inference — this tracks that, that tracks a third, so the first tracks the third — as an unwarranted transitivity assumption.

## Boss fight

Suppose you find r(A,B) = 0.9 and r(B,C) = 0.9 and want to reassure yourself that A and C are positively related. Reason about whether transitivity is safe here. Plug into the bound: the product is 0.81, the square-root term is sqrt((1−0.81)(1−0.81)) = 0.19, so r(A,C) is confined to [0.62, 1.0] — comfortably positive, no matter what. The general threshold is exact: r(A,C) is guaranteed positive whenever r(A,B)² + r(B,C)² exceeds 1, and can be negative otherwise. Two correlations of about 0.71 (whose squares sum to 1) are the boundary; above it transitivity is forced, below it it is optional. So "correlation is not transitive" is not a blanket ban on the intuition — it is a warning that the intuition needs the correlations to clear a specific, surprisingly high bar, and moderate correlations do not clear it.

Now the trap that generalizes this into practice: partial correlation and the difference between marginal and conditional relationships. The whole chain-reasoning error reappears in causal language as "A affects B, B affects C, so A affects C," and there the failure is not just the geometric bound but confounding and mediation — the correlations might be driven by common causes, so even a positive r(A,C) would not license the causal chain. The disciplined move when you care about A and C is to measure r(A,C) directly rather than inferring it, and if you cannot, to report the bound honestly (r(A,C) lies in this interval) instead of asserting a point. Inferring an unmeasured correlation from two measured ones is exactly the kind of "measure it, do not assume it" discipline the whole topic is about.

**Transitivity of correlation is guaranteed only when r(A,B)² + r(B,C)² exceeds 1 (roughly, both above 0.71); below that the third correlation can be negative — so measure r(A,C) directly when you can, and otherwise report the interval rather than asserting a sign, all the more so when the claim is causal.**

## External resources

The identity for the range of a third correlation given two others follows from the positive semidefiniteness of the correlation matrix; any multivariate statistics text covers it under partial correlation and the correlation-matrix constraints.
Discussions of "correlation is not transitive" (for example, Langford, Schwertman, and Owens, The American Statistician, 2001) work through the r(A,B)² + r(B,C)² greater than 1 condition for guaranteed positive transitivity.
The topic's own modules on confounding and on mediators cover the causal cousins of this error — why "A relates to B, B to C" does not chain into a causal claim about A and C even when the correlations are real.
