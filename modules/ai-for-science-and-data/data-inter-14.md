---
id: data-inter-14
title: The ecological fallacy — a correlation of group averages can be the opposite of the individual one
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 21 min
summary: A correlation computed on group averages describes the groups, not the people in them, and the two can differ in sign. Averaging keeps only the between-group trend and throws away the within-group variation that carries the individual relationship. On three groups where every group's internal correlation is -0.80 (y falls as x rises), the correlation of the three group means is +1.00 — so the aggregate says x and y move together while the individuals say they move apart. You cannot infer individuals from aggregates.
eli5: Say in every classroom, the kids who study more happen to score a bit lower on one weird test — a negative link inside each room. But the fancier schools both assign more studying and get higher scores. If you only compare school averages, studying looks great; if you look at actual kids, it looks bad. Averages describe schools, not students.
---

## Why this module

A relationship you measure between group averages tells you about the groups, and assuming it holds for the individuals inside them can get the direction exactly backwards.

You have data grouped into units — regions, schools, cohorts, countries — and you compute a correlation on the group averages: average income against average vote share, mean class size against mean test score. It comes out strong and positive, and the natural next sentence is about people: richer individuals vote this way, students in smaller classes score higher. That step — from a correlation of averages to a claim about individuals — is the ecological fallacy, and it is not a small approximation error. The two correlations are different quantities and can point in opposite directions.

The reason is what averaging does to the data. Each group average collapses all the individuals in that group to a single point, discarding every bit of within-group variation. But the within-group variation is exactly where the individual-level relationship lives — it is the variation among people who share a group. What survives averaging is only the between-group trend: how the groups differ from each other. So a correlation of group means measures the between-group relationship and is blind to the within-group one. When those two relationships disagree, the aggregate correlation misrepresents the individuals, and it can do so by flipping the sign entirely.

The classic shape is this. Within every group, x and y move opposite — as one person's x rises, their y falls — so the individual correlation is negative. But the groups are arranged so that a group with a higher average x also has a higher average y, making the correlation of the averages positive. Plot the group means and x and y march up together; look inside any single group and they pull apart. The aggregate is not a blurred version of the individual relationship; here it is its mirror image.

On the fixture, three groups each have a within-group correlation of −0.80, while the correlation of the three group means is +1.00. Same data, two levels of aggregation: the group means say x and y move together, the individuals inside say they move apart. Read the aggregate as if it described people and you would conclude the exact opposite of the truth.

**A correlation of group averages measures the between-group trend and discards the within-group variation that carries the individual relationship, so the aggregate and individual correlations can differ in sign — here the group means correlate +1.00 while every group internally correlates −0.80.**

## Concepts

The core fact is that a correlation is a property of a specific set of points, and group means are not the individuals. When you correlate group averages you are analyzing a dataset of one point per group, and its correlation describes how groups relate. When you correlate individuals you are analyzing a dataset of one point per person, and its correlation describes how people relate. These are two different datasets built from the same raw data, and there is no law forcing their correlations to agree — the mapping from individual data to group means is lossy, and the loss is precisely the within-group spread. Inferring one correlation from the other is unjustified in general, and the ecological fallacy is the name for doing it from aggregate to individual.

<svg role="img" aria-label="Total variation splitting into a between-group part that the ecological correlation sees and a within-group part that carries the individual relationship" viewBox="0 0 470 165" width="470" height="165">
  <rect x="0" y="0" width="470" height="165" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">total variation = between-group + within-group</text>
  <rect x="40" y="40" width="390" height="26" fill="var(--panel)" stroke="var(--line)"/>
  <text x="46" y="57" font-family="var(--mono)" font-size="9" fill="var(--ink)">all the variation in the data</text>
  <rect x="40" y="90" width="150" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="48" y="107" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">between groups</text>
  <text x="48" y="130" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">ecological corr sees this (+)</text>
  <rect x="190" y="90" width="240" height="26" fill="var(--s2)" opacity="0.3" stroke="var(--s2)"/>
  <text x="198" y="107" font-family="var(--mono)" font-size="8" fill="var(--s2)">within groups</text>
  <text x="198" y="130" font-family="var(--mono)" font-size="7" fill="var(--s2)">individual relationship lives here (-), discarded by averaging</text>
</svg>
^ Averaging keeps only the between-group slice, which the ecological correlation measures; the within-group slice — where the individual relationship lives — is thrown away, so the aggregate can have a different sign.

It helps to see the total variation as split into two parts: variation between groups (how group means differ) and variation within groups (how individuals differ from their own group's mean). The individual-level relationship is driven by the within-group part; the ecological correlation sees only the between-group part. When the between-group and within-group relationships have the same sign, the aggregate is a reasonable (if exaggerated) proxy. When they have opposite signs — a real and common situation — the aggregate is actively misleading. Because averaging always amplifies the between-group signal (means are less noisy than individuals), ecological correlations are also systematically stronger in magnitude, which makes them look more authoritative exactly when they may be most wrong.

This is distinct from Simpson's paradox, though they are cousins. Simpson's paradox is about categorical rates reversing when you pool or split by a variable — a treatment that helps in every subgroup can look harmful in the combined table. The ecological fallacy is the continuous-correlation version of the same underlying warning: a statistical relationship measured at one level of aggregation need not hold at another. Simpson's says "conditioning can flip a rate"; the ecological fallacy says "aggregating can flip a correlation." Both are instances of the general rule that the level at which you analyze data is part of the claim, and moving between levels is not free.

The practical consequence is that you must match the level of your data to the level of your claim. If you want to say something about individuals, you need individual-level data; group-level data can only support group-level conclusions. This is a live issue in any field that works with aggregated data — epidemiology (disease rates by region), social science (voting by district), and increasingly machine learning, where models trained or evaluated on aggregated features can learn a between-group relationship and be deployed as if it were an individual one. The famous origin is Robinson's 1950 finding that US states with more immigrants had higher literacy (ecological, positive) while immigrants individually were less literate than natives (individual, negative) — the fallacy in one dataset.

**Total variation splits into between-group and within-group parts; the ecological correlation sees only the between-group part and averaging amplifies it, so when the two levels disagree the aggregate is both stronger and wrong — which is why a claim about individuals needs individual-level data.**

## Worked example

The fixture is individual points grouped into three regions.

```json filename=modules/ai-for-science-and-data/code/data-inter-14/groups.json:3-7 COMPLETE
  "groups": {
    "region_A": [[1, 4], [2, 2], [3, 3], [4, 1]],
    "region_B": [[5, 8], [6, 6], [7, 7], [8, 5]],
    "region_C": [[9, 12], [10, 10], [11, 11], [12, 9]]
  }
```

Within each region, y trends down as x goes up — a negative within-group relationship. But region A sits low on both x and y, region C high on both, so the region averages trend up together. The correlation is standard Pearson.

```python filename=modules/ai-for-science-and-data/code/data-inter-14/ecological.py:48-58 COMPLETE
def correlation(xs, ys):
    """Pearson correlation of two equal-length lists."""
    mx, my = mean(xs), mean(ys)
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    vy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return round(cov / (vx * vy), 3) if vx and vy else 0.0


def within_corr(group):
    return correlation([p[0] for p in group], [p[1] for p in group])
```

The ecological correlation is computed on the three group means; the individual correlation is the average of the three within-group correlations.

```python filename=modules/ai-for-science-and-data/code/data-inter-14/ecological.py:65-73 COMPLETE
def ecological_corr(groups):
    """Correlation of the group means -- the aggregate-level relationship."""
    means = [group_mean(g) for g in groups.values()]
    return correlation([m[0] for m in means], [m[1] for m in means])


def mean_within_corr(groups):
    """Average of the per-group (individual-level) correlations."""
    return round(mean([within_corr(g) for g in groups.values()]), 3)
```

Predict: each group's internal correlation is negative (y falls as x rises), while the three means (2.5, 2.5), (6.5, 6.5), (10.5, 10.5) lie on a rising line, so their correlation is strongly positive. Look at the groups first.

```text filename=modules/ai-for-science-and-data/code/data-inter-14/ecological.py --groups
GROUPS — each group's points and its own within-group correlation
------------------------------------------------------------
  region_A  points [[1, 4], [2, 2], [3, 3], [4, 1]]
      mean (2.5, 2.5)   within-group corr -0.80
  region_B  points [[5, 8], [6, 6], [7, 7], [8, 5]]
      mean (6.5, 6.5)   within-group corr -0.80
  region_C  points [[9, 12], [10, 10], [11, 11], [12, 9]]
      mean (10.5, 10.5)   within-group corr -0.80
------------------------------------------------------------
  inside every group, y falls as x rises (negative).
```

Every region has a within-group correlation of −0.80: inside each, higher x goes with lower y. And the three means climb together — (2.5, 2.5), (6.5, 6.5), (10.5, 10.5) — perfectly collinear and rising. Now the two levels side by side.

```text filename=modules/ai-for-science-and-data/code/data-inter-14/ecological.py --levels
LEVELS — the same data at two levels of aggregation
------------------------------------------------------------
  individual (mean within-group) correlation:  -0.80
  ecological (group-means) correlation:        +1.00
------------------------------------------------------------
  the group means say +1; the people inside say -0.8. Opposite signs.
```

The individual correlation is −0.80 and the ecological correlation is +1.00 — opposite signs, from the same data. If you only had the region averages, you would report a perfect positive relationship and confidently predict that a person with higher x has higher y. Every individual in the dataset says the reverse. The aggregate did not blur the truth; it inverted it, because averaging kept the upward march of the group means and discarded the downward slope inside each group.

<svg role="img" aria-label="Three groups of points each sloping down (negative) but positioned along a rising diagonal so the group means climb up together (positive)" viewBox="0 0 470 200" width="470" height="200">
  <rect x="0" y="0" width="470" height="200" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">x (right) vs y (up): groups slope down, means climb up</text>
  <line x1="40" y1="175" x2="450" y2="175" stroke="var(--line)"/>
  <line x1="40" y1="175" x2="40" y2="30" stroke="var(--line)"/>
  <line x1="55" y1="165" x2="440" y2="45" stroke="var(--acc-line)" stroke-dasharray="4 3"/>
  <text x="300" y="70" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">group means: +1.00</text>
  <g fill="var(--s2)"><circle cx="60" cy="120" r="4"/><circle cx="95" cy="150" r="4"/><circle cx="130" cy="135" r="4"/><circle cx="165" cy="165" r="4"/></g>
  <line x1="60" y1="120" x2="165" y2="165" stroke="var(--s2)" stroke-width="1"/>
  <text x="60" y="112" font-family="var(--mono)" font-size="7" fill="var(--s2)">A: -0.8</text>
  <g fill="var(--s2)"><circle cx="200" cy="95" r="4"/><circle cx="235" cy="125" r="4"/><circle cx="270" cy="110" r="4"/><circle cx="305" cy="140" r="4"/></g>
  <line x1="200" y1="95" x2="305" y2="140" stroke="var(--s2)" stroke-width="1"/>
  <text x="230" y="90" font-family="var(--mono)" font-size="7" fill="var(--s2)">B: -0.8</text>
  <g fill="var(--s2)"><circle cx="340" cy="70" r="4"/><circle cx="375" cy="100" r="4"/><circle cx="410" cy="85" r="4"/><circle cx="440" cy="112" r="4"/></g>
  <line x1="340" y1="70" x2="440" y2="112" stroke="var(--s2)" stroke-width="1"/>
  <text x="370" y="64" font-family="var(--mono)" font-size="7" fill="var(--s2)">C: -0.8</text>
</svg>
^ Each group's four points slope down (within-group −0.80), but the groups sit along a rising diagonal, so the group means correlate +1.00 — the aggregate trend is the opposite of every group's internal trend.

## Build

Reproduce the two correlations. Pure standard library, deterministic, so the −0.80 within-group and +1.00 ecological values come out exactly.

Run `--groups` for the per-group correlations, `--levels` for the two aggregation levels, `--check` for the gate. The self-test pins the sign flip and that it is not an artifact of one odd group.

```python filename=modules/ai-for-science-and-data/code/data-inter-14/ecological.py:107-110 COMPLETE
    within_negative = within < 0
    print("  the individual (within-group) correlation is negative = %s (%+.2f)" % (within_negative, within))

    ecological_positive = eco > 0
    print("  the ecological (group-means) correlation is positive = %s (%+.2f)" % (ecological_positive, eco))
```

```text filename=modules/ai-for-science-and-data/code/data-inter-14/ecological.py --check
SELF-TEST — the within-group correlation is negative while the group-means correlation is positive
------------------------------------------------------------------------------------------------
  the individual (within-group) correlation is negative = True (-0.80)
  the ecological (group-means) correlation is positive = True (+1.00)
  the two levels have opposite signs = True (-0.80 vs +1.00)
  every single group is negative internally = True
  the aggregate misstates the individual by more than one full unit of correlation = True (gap 1.80)
------------------------------------------------------------------------------------------------
SELF-TEST PASS  within_negative=True  ecological_positive=True  sign_flip=True  every_group_negative=True  ecological_misleads=True
```

The individual level is the average of the per-group correlations — one helper that measures the relationship inside groups, where it actually lives.

```python filename=modules/ai-for-science-and-data/code/data-inter-14/ecological.py:71-73 COMPLETE
def mean_within_corr(groups):
    """Average of the per-group (individual-level) correlations."""
    return round(mean([within_corr(g) for g in groups.values()]), 3)
```

<svg role="img" aria-label="A correlation axis from minus one to plus one with the individual correlation at minus 0.80 and the ecological correlation at plus 1.00 on opposite ends" viewBox="0 0 470 130" width="470" height="130">
  <rect x="0" y="0" width="470" height="130" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">the same data on the correlation axis (-1 to +1)</text>
  <line x1="40" y1="75" x2="440" y2="75" stroke="var(--line)"/>
  <line x1="240" y1="65" x2="240" y2="85" stroke="var(--muted)"/>
  <text x="232" y="100" font-family="var(--mono)" font-size="8" fill="var(--muted)">0</text>
  <text x="40" y="100" font-family="var(--mono)" font-size="8" fill="var(--muted)">-1</text>
  <text x="430" y="100" font-family="var(--mono)" font-size="8" fill="var(--muted)">+1</text>
  <circle cx="80" cy="75" r="6" fill="var(--s2)"/>
  <text x="60" y="58" font-family="var(--mono)" font-size="8" fill="var(--s2)">individual -0.80</text>
  <circle cx="440" cy="75" r="6" fill="var(--acc-line)"/>
  <text x="360" y="58" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">ecological +1.00</text>
  <line x1="86" y1="75" x2="434" y2="75" stroke="var(--muted)" stroke-dasharray="3 3"/>
  <text x="180" y="120" font-family="var(--mono)" font-size="8" fill="var(--muted)">a gap of 1.80 — opposite ends of the axis</text>
</svg>
^ The two correlations sit at opposite ends of the axis — individual at −0.80, ecological at +1.00 — a gap of 1.80, so the aggregate is not a noisy version of the individual truth but its inversion.

Five True flags. Within_negative and ecological_positive: the individual correlation is −0.80 and the aggregate is +1.00. Sign_flip: opposite signs, the headline. Every_group_negative: all three groups are negative internally, so the individual result is not driven by one weird group — it is the consistent within-group truth. Ecological_misleads: the gap between the two is 1.80, more than a full unit of correlation, so the aggregate is not slightly off but maximally wrong. The every-group-negative flag is what rules out the excuse that some group is an outlier: the fallacy is systematic, not a fluke.

**The sign_flip and every-group-negative flags together are the verdict — the aggregate correlation is +1.00 while all three groups are internally −0.80, so reading the group-means correlation as an individual one inverts a relationship that every single group agrees on.**

## Definition of done

You are done when you reproduce the sign flip and can explain why averaging causes it.

Concretely: `--groups` shows all three groups at within-group −0.80 with means climbing together; `--levels` shows individual −0.80 versus ecological +1.00; `--check` prints PASS with five True flags including a gap of 1.80. You can explain that a correlation of group means measures the between-group trend and discards the within-group variation that carries the individual relationship, that total variation splits into between- and within-group parts, and that when they disagree the aggregate is both stronger (averaging amplifies the between-group signal) and wrong. You can distinguish this from Simpson's paradox — categorical rate reversal on conditioning versus continuous correlation reversal on aggregation — and name that a claim about individuals needs individual-level data.

The habit to carry: match the level of your data to the level of your claim, and treat any correlation of averages as a statement about the groups only. When a result is computed on regional, school, or cohort averages and then used to predict individual behavior, flag the ecological fallacy and ask for individual-level data before believing the individual claim. Aggregated data can only earn aggregated conclusions.

## Boss fight

The instructive failure is a model that scores well on regional averages and harms the individuals it is deployed on.

An analytics team builds a risk model using features aggregated to the ZIP-code level — average income, average age — because individual data was easier to get in aggregate, and it correlates beautifully with ZIP-level outcomes. Deployed to score individuals, it performs badly and, worse, systematically misranks people, because the ZIP-level relationships it learned are between-neighborhood trends that need not hold between people within a neighborhood — the ecological fallacy baked into a model. The fix is to train and validate on individual-level data whenever the deployment target is an individual; aggregated features can enter as context, but the label-to-feature relationship must be learned at the individual level, or the model inherits the sign-flip risk this module shows.

Your turn, two moves. First, make the two levels agree and watch the fallacy vanish. Change the data so that within each group y also rises with x (flip the within-group slope positive) and confirm both correlations are now positive — the fallacy is dangerous only when the between- and within-group relationships disagree, so the risk is specifically a sign or magnitude mismatch, not aggregation per se. Second, compute the pooled correlation (ignore the grouping and correlate all twelve points together) and see it is strongly positive too — dominated by the between-group spread — which shows that pooling without accounting for groups makes the same mistake as using group means, and that the honest individual relationship is the within-group one that controls for the group.

## External resources

Robinson's 1950 paper "Ecological Correlations and the Behavior of Individuals" is the origin and still the clearest statement — his literacy-and-immigration example is exactly the sign flip this module reproduces.

Any epidemiology or social-science methods text covers the ecological fallacy and its partner, the atomistic fallacy (inferring group relationships from individuals), and the general point that inference does not transfer across levels of aggregation.

The multilevel-modeling literature (Gelman and Hill, "Data Analysis Using Regression and Multilevel/Hierarchical Models") is the constructive response — models that separate within-group and between-group relationships explicitly, so you can estimate both instead of conflating them.
