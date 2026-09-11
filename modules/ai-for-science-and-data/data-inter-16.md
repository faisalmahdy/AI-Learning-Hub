---
id: data-inter-16
title: A shared denominator manufactures correlation — two unrelated ratios move together because they share a divisor
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 21 min
summary: Form two ratios that share a denominator — crime per capita and doctors per capita, both over population — and they can correlate strongly even when the numerators are unrelated, because dividing by the same quantity injects a shared 1/denominator factor into both. On columns where X and Y are uncorrelated (0.00), X/Z and Y/Z correlate 0.971; give each numerator a different divisor and the correlation vanishes to 0.03. A correlation between ratios is not evidence the numerators are related.
eli5: If you divide two totally unrelated numbers by the same thing, the ratios rise and fall together just because of the shared bottom — when the bottom is small, both are big. So "these two per-person rates go together" can be an illusion created by dividing both by population, not a real link between the things on top.
---

## Why this module

Two rates that share a denominator can track each other beautifully and mean nothing, because the correlation you see is the shared divisor, not the quantities you care about.

It is natural to compare ratios. Crime per capita against doctors per capita; expenses as a fraction of revenue against salaries as a fraction of revenue; deaths per thousand against births per thousand. You plot two such ratios, see them rise and fall together, compute a correlation, and conclude the numerators are related — more doctors go with more crime, say. That conclusion can be entirely an artifact of the division. When two ratios share a denominator, they share a common factor of one-over-that-denominator, and that shared factor makes them move together regardless of whether the numerators have anything to do with each other.

The mechanism is simple once you see it. A ratio X/Z is large when Z is small and small when Z is large. If a second ratio Y/Z uses the same Z, it is also large when Z is small and small when Z is large. So both ratios swing up and down in lockstep with 1/Z, and that shared swing appears as correlation between X/Z and Y/Z — even if X and Y are independent, even if X and Y are unrelated to Z. The population term, or whatever the common denominator is, has smuggled a correlation into the comparison that has nothing to do with the numerators.

The way to expose it is to move the denominator around. Correlate the raw numerators X and Y directly: if there is nothing, the numerators are unrelated. Correlate the two ratios with the same denominator: a correlation appears. Correlate them with different, unrelated denominators — X over Z and Y over some other divisor W: the correlation vanishes again. That last step is the proof: since only the shared denominator produced the correlation, giving each numerator its own divisor removes it. A correlation between two ratios is therefore not evidence that the numerators are related; you must check the numerators directly or the shared divisor will invent a relationship.

On the fixture, X and Y are uncorrelated numerators — correlation 0.00. Dividing both by the same Z gives ratios that correlate 0.971, a strong spurious correlation. Dividing X by Z and Y by a different divisor W gives 0.03 — gone. Same numerators; only the shared denominator created the correlation.

**Two ratios that share a denominator both vary with one-over-that-denominator, so they correlate even when their numerators are independent; the correlation lives in the shared divisor, revealed by the fact that correlating the numerators directly, or the ratios with different denominators, makes it disappear.**

## Concepts

The heart of the issue is that a ratio is a product of two things — the numerator and the reciprocal of the denominator — and a shared denominator makes two ratios share one of those factors. Write X/Z as X · (1/Z) and Y/Z as Y · (1/Z). Both are the product of an independent numerator with the common factor 1/Z. When 1/Z varies (which it does, since Z varies across your data points), it drives both products up and down together, and Pearson correlation registers that common driver as a relationship between X/Z and Y/Z. The numerators X and Y contribute their own, uncorrelated variation, but if the 1/Z swing is large relative to that, it dominates and the correlation is high. This is why a widely-varying denominator produces the strongest spurious correlation.

<svg role="img" aria-label="Both ratios X/Z and Y/Z plotted against the data points descend together as Z grows, tracking the shared one-over-Z curve" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">X/Z and Y/Z both fall with Z — the shared 1/Z drives both</text>
  <line x1="45" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <line x1="45" y1="35" x2="45" y2="150" stroke="var(--line)"/>
  <text x="20" y="42" font-family="var(--mono)" font-size="7" fill="var(--muted)">ratio</text>
  <polyline points="70,45 160,105 250,120 340,140 430,145" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <g fill="var(--s2)"><circle cx="70" cy="45" r="3"/><circle cx="160" cy="105" r="3"/><circle cx="250" cy="120" r="3"/><circle cx="340" cy="140" r="3"/><circle cx="430" cy="145" r="3"/></g>
  <text x="120" y="60" font-family="var(--mono)" font-size="8" fill="var(--s2)">X/Z</text>
  <polyline points="70,52 160,95 250,120 340,138 430,147" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <g fill="var(--s1)"><circle cx="70" cy="52" r="3"/><circle cx="160" cy="95" r="3"/><circle cx="250" cy="120" r="3"/><circle cx="340" cy="138" r="3"/><circle cx="430" cy="147" r="3"/></g>
  <text x="120" y="88" font-family="var(--mono)" font-size="8" fill="var(--s1)">Y/Z</text>
  <text x="60" y="166" font-family="var(--mono)" font-size="7" fill="var(--muted)">Z=1</text>
  <text x="410" y="166" font-family="var(--mono)" font-size="7" fill="var(--muted)">Z=16</text>
</svg>
^ Both ratios trace nearly the same descending curve because both are dominated by the shared 1/Z; their near-parallel motion is the spurious correlation, not any link between X and Y.

This is a specific, and historically important, case of a confounder — the denominator is a variable that influences both ratios. Ordinary confounding says a lurking variable Z that causes both X and Y creates a correlation between them; here Z does not even cause X or Y, it is merely divided into both, and that is enough. The division is a mechanical operation, not a causal story, yet it produces the same statistical signature. Karl Pearson identified this in 1897 precisely because scientists were correlating indices and organ measurements normalized by body size and finding "relationships" that were artifacts of the shared normalizer. The lesson has to be relearned constantly because forming per-capita, per-dollar, and per-unit rates is so routine.

The diagnostic follows directly from the mechanism. Because the correlation comes from the shared 1/Z, anything that breaks the sharing breaks the correlation. Correlating the numerators directly removes the denominator entirely, so if they are unrelated you see nothing. Correlating X/Z against Y/W, with W an independent denominator, means the two ratios no longer share a factor, so the spurious correlation collapses — this is the cleanest confirmation that the divisor, not the numerators, was responsible. If instead the numerators are genuinely related, that relationship will still show up when you correlate them directly, so checking the numerators never hides a real effect; it only strips out the artifact.

The practical guidance is to be suspicious of any correlation between two ratios that share a denominator, and to always look at the numerators. Per-capita crime versus per-capita anything (both over population), spending categories as fractions of a shared budget, closing-price returns of two stocks normalized by an index — all are exposed. The fixes: correlate the raw quantities (or use a model that includes the denominator as a variable rather than dividing it out); if a rate is genuinely the quantity of interest, compare it against a rate with a different denominator or use partial correlation controlling for the denominator; and treat "these two rates are correlated" as a hypothesis to test on the numerators, not a finding. The shared divisor is a correlation machine, and it runs whether or not there is anything real underneath.

**A ratio is numerator times one-over-denominator, so a shared denominator gives two ratios a common factor that correlates them mechanically — a confounder created by division, not causation; correlate the numerators directly or use independent denominators to strip the artifact, which never hides a real numerator relationship.**

## Worked example

The fixture is three columns plus an alternative denominator.

```json filename=modules/ai-for-science-and-data/code/data-inter-16/columns.json:3-6 COMPLETE
  "X": [10, 8, 12, 9, 11],
  "Y": [9, 11, 12, 10, 8],
  "Z": [1, 2, 4, 8, 16],
  "W": [2, 4, 8, 16, 1]
```

X and Y are the numerators (built to be uncorrelated); Z is a widely-varying shared denominator; W is a different denominator (the same values as Z, but shuffled, so it is an unrelated divisor). Correlation is standard Pearson.

```python filename=modules/ai-for-science-and-data/code/data-inter-16/ratio.py:47-52 COMPLETE
def correlation(xs, ys):
    mx, my = mean(xs), mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    vy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return round(cov / (vx * vy), 3) if vx and vy else 0.0
```

A ratio is just the elementwise division of a numerator column by a denominator column.

```python filename=modules/ai-for-science-and-data/code/data-inter-16/ratio.py:55-56 COMPLETE
def ratio(num, den):
    return [round(n / d, 3) for n, d in zip(num, den)]
```

First look at the ratios over the shared Z, to see them swing together with 1/Z.

```text filename=modules/ai-for-science-and-data/code/data-inter-16/ratio.py --data
DATA — three columns and the ratios over a shared denominator Z
----------------------------------------------------------
  X:    [10, 8, 12, 9, 11]
  Y:    [9, 11, 12, 10, 8]
  Z:    [1, 2, 4, 8, 16]   (shared denominator)
  X/Z:  [10.0, 4.0, 3.0, 1.125, 0.688]
  Y/Z:  [9.0, 5.5, 3.0, 1.25, 0.5]
----------------------------------------------------------
  when Z is small both ratios are large, and vice versa.
```

Both X/Z and Y/Z start high (Z = 1) and fall as Z grows to 16 — they descend together because both are dominated by the same shrinking 1/Z, even though their numerators wander independently. That shared descent is the spurious correlation waiting to be measured. Predict: the numerators correlate near zero, the same-denominator ratios correlate strongly, and different-denominator ratios correlate near zero again. Compute all three.

```text filename=modules/ai-for-science-and-data/code/data-inter-16/ratio.py --correlate
CORRELATE — correlation of numerators vs ratios
----------------------------------------------------------
  numerators        X   vs Y   : +0.000
  same denominator  X/Z vs Y/Z : +0.971
  diff denominator  X/Z vs Y/W : +0.031
----------------------------------------------------------
  the correlation appears only with the shared denominator.
```

The numerators X and Y correlate exactly 0.000 — genuinely unrelated. Divide both by the same Z and the ratios correlate 0.971, a near-perfect relationship that exists nowhere in the numerators. Divide X by Z and Y by the different divisor W, and the correlation drops to 0.031 — essentially gone. The 0.971 was manufactured entirely by the shared denominator: remove the sharing (different denominators) or remove the denominator (raw numerators), and there is nothing there. Anyone who saw only the middle line would confidently report a strong relationship that does not exist.

<svg role="img" aria-label="Three correlation values: numerators at 0.00, same-denominator ratios at 0.97, different-denominator ratios at 0.03, on a scale from 0 to 1" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">correlation (0 → 1): only the shared denominator is high</text>
  <line x1="40" y1="150" x2="450" y2="150" stroke="var(--line)"/>
  <line x1="40" y1="40" x2="40" y2="150" stroke="var(--line)"/>
  <rect x="70" y="148" width="70" height="2" fill="var(--acc-line)"/>
  <text x="66" y="164" font-family="var(--mono)" font-size="7" fill="var(--muted)">X vs Y</text>
  <text x="72" y="140" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">0.00</text>
  <rect x="200" y="45" width="70" height="105" fill="var(--s2)"/>
  <text x="196" y="164" font-family="var(--mono)" font-size="7" fill="var(--muted)">X/Z vs Y/Z</text>
  <text x="205" y="39" font-family="var(--mono)" font-size="8" fill="var(--s2)">0.97 (spurious)</text>
  <rect x="340" y="147" width="70" height="3" fill="var(--acc-line)"/>
  <text x="336" y="164" font-family="var(--mono)" font-size="7" fill="var(--muted)">X/Z vs Y/W</text>
  <text x="345" y="139" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">0.03</text>
</svg>
^ The numerators and the different-denominator ratios sit near zero; only the shared-denominator ratios spike to 0.97 — the correlation is entirely the shared divisor's doing.

## Build

Reproduce the correlations. Pure standard library, deterministic, so the 0.000 numerator correlation, the 0.971 shared-denominator correlation, and the 0.031 different-denominator correlation come out exactly.

Run `--data` for the columns and ratios, `--correlate` for the three correlations, `--check` for the gate. The self-test pins that the numerators are uncorrelated, the shared-denominator ratios are, and different denominators remove it.

```python filename=modules/ai-for-science-and-data/code/data-inter-16/ratio.py:93-102 COMPLETE
    numerators_uncorrelated = abs(r_num) < 0.1
    print("  the raw numerators are uncorrelated = %s (%.3f)" % (numerators_uncorrelated, r_num))

    shared_denom_correlated = r_same > 0.7
    print("  the same-denominator ratios are strongly correlated = %s (%.3f)" % (shared_denom_correlated, r_same))

    spurious_gap = r_same - abs(r_num) > 0.7
    print("  the ratio correlation dwarfs the numerator correlation = %s (%.3f vs %.3f)" % (spurious_gap, r_same, r_num))

    diff_denom_not_correlated = abs(r_diff) < 0.2
```

```text filename=modules/ai-for-science-and-data/code/data-inter-16/ratio.py --check
SELF-TEST — uncorrelated numerators, but a shared denominator makes the ratios correlate
------------------------------------------------------------------------------------------------
  the raw numerators are uncorrelated = True (0.000)
  the same-denominator ratios are strongly correlated = True (0.971)
  the ratio correlation dwarfs the numerator correlation = True (0.971 vs 0.000)
  different denominators remove the correlation = True (0.031)
  the spurious correlation is positive (shared 1/Z) = True
------------------------------------------------------------------------------------------------
SELF-TEST PASS  numerators_uncorrelated=True  shared_denom_correlated=True  spurious_gap=True  diff_denom_not_correlated=True  positive_spurious=True
```

Five True flags. Numerators_uncorrelated: X and Y correlate 0.000. Shared_denom_correlated: X/Z and Y/Z correlate 0.971. Spurious_gap: the ratio correlation exceeds the numerator correlation by nearly a full unit — the artifact, quantified. Diff_denom_not_correlated: using different denominators drops it to 0.031. Positive_spurious: the spurious correlation is positive, as expected since both ratios share the same positive 1/Z factor. The two flags that isolate the cause check that a different denominator kills the correlation and that the artifact is positive.

```python filename=modules/ai-for-science-and-data/code/data-inter-16/ratio.py:102-106 COMPLETE
    diff_denom_not_correlated = abs(r_diff) < 0.2
    print("  different denominators remove the correlation = %s (%.3f)" % (diff_denom_not_correlated, r_diff))

    positive_spurious = r_same > 0
    print("  the spurious correlation is positive (shared 1/Z) = %s" % positive_spurious)
```

<svg role="img" aria-label="Three cases side by side: raw numerators near zero, shared denominator high, different denominators back near zero" viewBox="0 0 470 150" width="470" height="150">
  <rect x="0" y="0" width="470" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">what changes the correlation: only sharing the denominator</text>
  <text x="30" y="52" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">no denominator (X vs Y)</text>
  <rect x="250" y="42" width="6" height="14" fill="var(--acc-line)"/>
  <text x="262" y="53" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">0.00</text>
  <text x="30" y="86" font-family="var(--mono)" font-size="8" fill="var(--s2)">shared Z (X/Z vs Y/Z)</text>
  <rect x="250" y="76" width="160" height="14" fill="var(--s2)"/>
  <text x="415" y="87" font-family="var(--mono)" font-size="8" fill="var(--s2)">0.97</text>
  <text x="30" y="120" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">diff Z, W (X/Z vs Y/W)</text>
  <rect x="250" y="110" width="8" height="14" fill="var(--acc-line)"/>
  <text x="264" y="121" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">0.03</text>
</svg>
^ Only the middle case — sharing the denominator — is high; remove the denominator or make it independent and the correlation returns to near zero, pinning the cause on the shared divisor.

The different-denominator flag is the decisive one — it isolates the shared divisor as the cause, because the only thing changed between 0.971 and 0.031 is whether the denominator was shared.

**The different-denominator flag is the proof of cause — swapping Y's divisor from the shared Z to an independent W collapses the correlation from 0.971 to 0.031, so the shared denominator, not any numerator relationship, manufactured it.**

## Definition of done

You are done when you reproduce the manufactured correlation and its disappearance, and can explain the mechanism.

Concretely: `--correlate` shows the numerators at 0.000, the shared-denominator ratios at 0.971, and the different-denominator ratios at 0.031; `--check` prints PASS with five True flags. You can explain that a ratio is numerator times one-over-denominator, so two ratios with a shared denominator share a 1/Z factor that correlates them mechanically, that this is a confounder created by division rather than causation, and that correlating the numerators directly or using independent denominators strips the artifact without hiding a real numerator relationship. You can name the fixes: correlate raw quantities, use partial correlation controlling for the denominator, or model the denominator as a variable.

The habit to carry: when two ratios share a denominator, treat any correlation between them as suspect and check the numerators directly before believing it. Per-capita, per-dollar, and per-unit rates over a common base are the usual traps — population, revenue, total budget. When a "relationship" between two indices or rates seems too clean, ask what they were divided by; a shared divisor correlates whatever you feed it. Test the numerators, not the ratios.

## Boss fight

The instructive failure is a policy claim built on two per-capita rates that share a population denominator.

An analyst reports that regions with more police officers per capita also have more crime per capita, correlation 0.8, and it is cited as evidence police cause crime (or fail to prevent it). But both rates are divided by population, and population varies enormously across regions; the shared 1/population factor makes the two rates correlate strongly regardless of any real link between raw officer counts and raw crime counts. Correlating the raw counts, or controlling for population, the relationship largely disappears — the 0.8 was substantially the shared denominator. The fix is to analyze the raw numerators with population as an explicit covariate, not to correlate two population-normalized rates and read causation into it.

Your turn, two moves. First, dial the artifact with the denominator's spread: shrink Z's range (make it nearly constant, say [7, 8, 8, 9, 8]) and confirm the spurious correlation collapses even with the shared denominator — because a near-constant 1/Z injects almost no common variation, so the spurious correlation grows with how much the denominator varies. Second, plant a real effect and confirm the check still finds it: make Y genuinely track X (set Y = X), and confirm the numerators now correlate too, so checking the numerators directly reports the real relationship rather than hiding it — the diagnostic strips artifacts without erasing genuine effects.

## External resources

Karl Pearson's 1897 paper "On a Form of Spurious Correlation Which May Arise When Indices Are Used in the Measurement of Organs" is the origin, and it lays out exactly the shared-denominator mechanism this module computes.

Any statistics text's treatment of spurious correlation and the analysis of ratios (and the related "ratio fallacy" in ecology and geology, where indices normalized by a common size variable are correlated) covers the diagnostic of examining the raw variables.

The literature on compositional data (Aitchison) is the modern generalization — data expressed as fractions of a whole are constrained and correlate spuriously, and it develops the log-ratio methods that handle shared-denominator effects correctly.
