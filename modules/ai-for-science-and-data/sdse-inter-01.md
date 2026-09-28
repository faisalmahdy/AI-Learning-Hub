---
id: sdse-inter-01
title: The standard deviation is the spread of the data; the standard error is the uncertainty of the mean — they differ by a factor of √n
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 15 min
summary: You measure something n times and report "mean ± something", and the something is where the confusion lives, because there are two different spreads and they are not interchangeable. The standard deviation (SD) describes the data — how far a typical single measurement sits from the mean — and it is a property of the thing you measure, so more data pins it down but does not make it smaller. The standard error of the mean (SEM = SD/√n) describes the estimate — how far the sample mean is likely to sit from the true mean — and it shrinks as you gather more, halving every time n quadruples. Swap them and you get two symmetric errors: an error bar of one SD on the mean overstates its uncertainty by √n and, absurdly, never tightens as data piles up; a range of mean ± SEM for a typical individual understates the spread by √n and excludes most of the data. On the fixture of 16 blood-pressure readings the mean is 134.19, the SD is 10.84, and the SEM is 10.84/√16 = 2.71 — a factor of 4 apart; at 4× the sample size the SEM would fall to 1.35 while the SD stays 10.84, and at 1/4× it would rise to 5.42 while the SD stays 10.84. The tell is coverage: mean ± SD contains 10 of 16 points (62%) because SD is a range for individuals, while mean ± SEM contains only 2 of 16 (12%) because SEM never was. The rule: SD answers "how much do individuals vary", SEM answers "how well do I know the mean", and the ratio between them is exactly √n.
eli5: If you weigh sixteen apples, there are two different "give or take" numbers, and mixing them up gives nonsense. One is how much the apples differ from each other — some are big, some small — and that spread is real no matter how many apples you weigh; weighing more apples doesn't make them all the same size. The other is how sure you are about the average apple weight, and that one does get tighter the more apples you weigh, because an average over many is steadier than an average over few. If you put the first number as the error bar on the average, you make the average look far shakier than it is — and weirdly it never improves with more apples. If you put the second number as the range for a single apple, you claim almost every apple is nearly identical, when really most of them fall outside that tiny band.
---

## Why this module

Almost every measured result is reported as a center and a spread — "134 ± 11", "the average is 2.7 seconds, plus or minus half a second". The center is usually unambiguous. The spread is not, because two completely different quantities get written in that same slot, and swapping them is one of the most common quiet errors in a results section.

The two quantities even move in opposite ways as you collect data, which is the fastest way to catch the mistake. One is fixed by the thing you are studying; the other tightens with every measurement. If your "error bar" does not shrink when you add data, it is describing the wrong thing — or it is supposed to.

**Reporting a mean with a spread requires choosing which spread: how much individuals vary, or how well you know the mean — and those differ by a factor of √n.**

## Concepts

The standard deviation measures the data. It asks: how far does a typical single measurement sit from the mean? That is a fact about what you are measuring — how much blood pressures vary between people, how noisy one reading is — and it does not depend on how many measurements you took. Take more and you estimate the SD more precisely, but the true spread of individuals is what it is; it does not shrink because you looked harder.

The standard error of the mean measures the estimate. It asks: how far is the sample mean likely to sit from the true mean I am trying to estimate? That is not a fact about the spread of the data but about the precision of one number you computed from it, and averaging more measurements makes that one number steadier. The relationship is exact: SEM = SD / √n. Quadruple the sample size and the SEM halves; the √n in the denominator is the whole story.

So the two answer different questions. SD answers "how much do individuals vary" and is a property of the world. SEM answers "how well do I know the mean" and is a property of your sample size. They coincide only at n = 1, and past that the SD is always the larger by exactly √n.

Now the two symmetric mistakes. Put an error bar of one SD on the mean and you claim the mean is √n times less certain than it is — and the bar has the absurd property of never tightening no matter how much data you gather, which should be the giveaway. Put a range of mean ± SEM around the individuals and you claim they cluster √n times more tightly than they do, promising that a typical measurement lands in a band that most measurements actually fall outside.

**SD does not shrink with n and is the range for individuals; SEM shrinks as √n and is the precision of the mean — an error bar that never tightens with data is an SD masquerading as an SEM.**

<svg role="img" aria-label="A chart across three sample sizes 4, 16, 64. The SD stays flat at 10.84 across all three. The SEM falls from 5.42 at n=4 to 2.71 at n=16 to 1.35 at n=64, halving each time n quadruples." viewBox="0 0 460 170">
<rect x="0" y="0" width="460" height="170" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">as n grows, SD holds and SEM falls as 1/&#8730;n</text>
<line x1="60" y1="140" x2="430" y2="140" stroke="var(--line)"></line>
<text x="90" y="156" fill="var(--muted)" font-size="9">n=4</text>
<text x="220" y="156" fill="var(--muted)" font-size="9">n=16</text>
<text x="350" y="156" fill="var(--muted)" font-size="9">n=64</text>
<line x1="100" y1="52" x2="360" y2="52" stroke="var(--s1)"></line>
<circle cx="100" cy="52" r="3" fill="var(--s1)"></circle>
<circle cx="230" cy="52" r="3" fill="var(--s1)"></circle>
<circle cx="360" cy="52" r="3" fill="var(--s1)"></circle>
<text x="364" y="55" fill="var(--s1)" font-size="9">SD 10.84 (flat)</text>
<circle cx="100" cy="95" r="3" fill="var(--s2)"></circle>
<circle cx="230" cy="118" r="3" fill="var(--s2)"></circle>
<circle cx="360" cy="130" r="3" fill="var(--s2)"></circle>
<line x1="100" y1="95" x2="230" y2="118" stroke="var(--s2)"></line>
<line x1="230" y1="118" x2="360" y2="130" stroke="var(--s2)"></line>
<text x="104" y="90" fill="var(--s2)" font-size="9">5.42</text>
<text x="234" y="114" fill="var(--s2)" font-size="9">2.71</text>
<text x="364" y="128" fill="var(--s2)" font-size="9">SEM 1.35</text>
</svg>
^ The SD line is flat because the spread of individuals is fixed; the SEM curve halves each time n quadruples, which is what "shrinks as 1/&#8730;n" looks like.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/ai-for-science-and-data/code/sdse-inter-01/sdse.py

The fixture is 16 blood-pressure readings.

```json filename=modules/ai-for-science-and-data/code/sdse-inter-01/sdse.json:3-4 COMPLETE
  "label": "systolic blood pressure (mmHg)",
  "measurements": [128, 142, 119, 135, 151, 124, 138, 145, 122, 133, 147, 130, 118, 140, 126, 149]
```

The SD is the spread of the individual readings.

```python filename=modules/ai-for-science-and-data/code/sdse-inter-01/sdse.py:38-41 COMPLETE
def sample_sd(xs):
    """The sample standard deviation: the spread of individual measurements (uses n-1)."""
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))
```

The SEM divides it by √n.

```python filename=modules/ai-for-science-and-data/code/sdse-inter-01/sdse.py:44-46 COMPLETE
def sem(xs):
    """The standard error of the mean: the uncertainty of the sample mean, SD / sqrt(n)."""
    return sample_sd(xs) / math.sqrt(len(xs))
```

Run it and watch which number moves with the sample size.

```text filename=sdse.py --describe
DESCRIBE — systolic blood pressure (mmHg), n=16
----------------------------------------------------------------
  mean            = 134.19
  SD  (spread of individuals)      = 10.84   -- does not shrink with n
  SEM (uncertainty of the mean)    = 2.71   = SD / sqrt(16)
  if n were 64 (4x):  SEM = 1.35   SD = 10.84 (unchanged)
  if n were 4 (1/4x): SEM = 5.42   SD = 10.84 (unchanged)
----------------------------------------------------------------
  more data tightens the mean (SEM falls) but not the spread (SD holds)
```

The SD is 10.84 and the SEM is 2.71 — a factor of 4, which is √16. Change the sample size and only the SEM moves: at 4× the data it falls to 1.35, at 1/4× it rises to 5.42, and the SD sits at 10.84 the whole time, because the spread of blood pressures is not something a bigger sample changes.

<svg role="img" aria-label="A number line centered on the mean 134. A wide band labeled plus-or-minus SD spans about 123 to 145; a narrow band labeled plus-or-minus SEM spans about 131.5 to 137. The SD band is four times wider than the SEM band." viewBox="0 0 480 150">
<rect x="0" y="0" width="480" height="150" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">two spreads on the same mean (134.19)</text>
<line x1="40" y1="95" x2="460" y2="95" stroke="var(--line)"></line>
<line x1="250" y1="40" x2="250" y2="110" stroke="var(--grid)"></line>
<text x="236" y="34" fill="var(--muted)" font-size="9">mean</text>
<rect x="88" y="58" width="324" height="14" fill="var(--s1)" opacity="0.5"></rect>
<text x="88" y="52" fill="var(--s1)" font-size="10">mean &#177; SD = [123.4, 145.0]  (individuals)</text>
<rect x="209" y="78" width="82" height="14" fill="var(--s2)"></rect>
<text x="120" y="128" fill="var(--s2)" font-size="10">mean &#177; SEM = [131.5, 136.9]  (the mean's precision)</text>
</svg>
^ Same center, two spreads: the SD band is the range individuals occupy, the SEM band is how tightly the mean itself is pinned — and the first is √16 = 4 times the second.

## Build

The coverage view makes the misuse concrete: count how many of the 16 readings actually fall in each band.

```python filename=modules/ai-for-science-and-data/code/sdse-inter-01/sdse.py:54-57 COMPLETE
def coverage(xs, half_width):
    """How many individual points fall within mean +/- half_width."""
    m = mean(xs)
    return sum(1 for x in xs if m - half_width <= x <= m + half_width)
```

```text filename=sdse.py --coverage
COVERAGE — how many of the 16 points fall in each band
----------------------------------------------------------------
  mean +/- SD  = [123.35, 145.03]  contains 10 of 16 points (62%)
  mean +/- SEM = [131.48, 136.90]  contains 2 of 16 points (12%)
----------------------------------------------------------------
  SD is a range for individuals; SEM is not -- most points fall outside +/- SEM
```

Mean ± SD holds 10 of the 16 readings — a majority, which is what a range for individuals should do. Mean ± SEM holds 2 of 16; if you reported "a typical patient is within ± 2.7 of 134" you would be wrong for 14 of the 16 patients you actually measured. The SEM band is narrow because it describes the mean, not the patients.

<svg role="img" aria-label="Sixteen dots spread horizontally around the mean. A wide SD band covers ten of them; a narrow SEM band at the center covers two. The dots outside the SEM band but inside the SD band are the majority the SEM misclassifies." viewBox="0 0 480 150">
<rect x="0" y="0" width="480" height="150" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">the 16 readings, with each band drawn</text>
<rect x="70" y="44" width="340" height="60" fill="var(--s1)" opacity="0.35"></rect>
<text x="74" y="40" fill="var(--s1)" font-size="9">mean &#177; SD (10 of 16 inside)</text>
<rect x="212" y="44" width="56" height="60" fill="var(--s2)" opacity="0.6"></rect>
<text x="200" y="120" fill="var(--s2)" font-size="9">mean &#177; SEM (2 of 16)</text>
<circle cx="60" cy="74" r="4" fill="var(--ink)"></circle>
<circle cx="95" cy="74" r="4" fill="var(--ink)"></circle>
<circle cx="130" cy="74" r="4" fill="var(--ink)"></circle>
<circle cx="165" cy="74" r="4" fill="var(--ink)"></circle>
<circle cx="200" cy="74" r="4" fill="var(--ink)"></circle>
<circle cx="228" cy="74" r="4" fill="var(--ink)"></circle>
<circle cx="252" cy="74" r="4" fill="var(--ink)"></circle>
<circle cx="285" cy="74" r="4" fill="var(--ink)"></circle>
<circle cx="315" cy="74" r="4" fill="var(--ink)"></circle>
<circle cx="345" cy="74" r="4" fill="var(--ink)"></circle>
<circle cx="380" cy="74" r="4" fill="var(--ink)"></circle>
<circle cx="420" cy="74" r="4" fill="var(--ink)"></circle>
</svg>
^ Only the two dots inside the small central band fall within mean ± SEM; treating that band as the range for individuals excludes almost everyone, while the wide SD band holds the majority it should.

The self-test ties the definition to the numbers: SEM × √n recovers the SD, the SEM is the smaller of the two, quadrupling n halves it, and the coverage split is exactly the individuals-versus-mean distinction.

```python filename=modules/ai-for-science-and-data/code/sdse-inter-01/sdse.py:97-104 COMPLETE
    sem_is_sd_over_sqrt_n = abs(se * math.sqrt(n) - sd) < 1e-9
    print("  SEM * sqrt(n) equals the SD (SEM = SD/sqrt(n)) = %s (%.4f == %.4f)" % (sem_is_sd_over_sqrt_n, se * math.sqrt(n), sd))

    sem_smaller_than_sd = se < sd
    print("  SEM is smaller than the SD = %s (%.2f < %.2f)" % (sem_smaller_than_sd, se, sd))

    quadrupling_halves_sem = abs(sem_at(sd, 4 * n) - se / 2) < 1e-9
    print("  quadrupling n halves the SEM = %s (%.4f == %.4f)" % (quadrupling_halves_sem, sem_at(sd, 4 * n), se / 2))
```

```text filename=sdse.py --check
SELF-TEST — the SEM is SD/sqrt(n) and smaller than the SD, quadrupling n halves it, most individuals fall within one SD, and only a minority within one SEM
----------------------------------------------------------------------------------------------------------------
  SEM * sqrt(n) equals the SD (SEM = SD/sqrt(n)) = True (10.8395 == 10.8395)
  SEM is smaller than the SD = True (2.71 < 10.84)
  quadrupling n halves the SEM = True (1.3549 == 1.3549)
  most individuals fall within mean +/- SD = True (10 of 16)
  only a minority fall within mean +/- SEM = True (2 of 16)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  sem_is_sd_over_sqrt_n=True  sem_smaller_than_sd=True  quadrupling_halves_sem=True  sd_covers_most=True  sem_covers_few=True
```

**quadrupling_halves_sem is the load-bearing fact: an honest error bar on a mean gets tighter with data, so if yours does not move when n grows, it is an SD, not an SEM.**

## Definition of done

You can say which quantity answers "how much do individuals vary" (SD) and which answers "how well do I know the mean" (SEM), and give the ratio between them (√n).

You can predict what happens to each as the sample grows: the SD is estimated more precisely but does not shrink, while the SEM falls as 1/√n — and you can use "does it shrink with n" as the test for which one an error bar is.

You can state the two symmetric misuses and their size: an SD error bar on a mean is √n too wide, and an SEM range for an individual is √n too narrow and excludes most of the data.

You can name what a figure's error bars must be labeled as, because "134 ± 11" and "134 ± 2.7" describe the same data and mean opposite things.

## Boss fight

A paper reports "mean tumor shrinkage was 34% ± 3%, n = 400" and a reader concludes "so most patients shrank between 31% and 37%." A second paper reports "mean reaction time 250 ms ± 80 ms, n = 4" as evidence the drug's effect is precisely measured.

First: for each paper, decide whether the ± number is far more likely an SD or an SEM, using only the sample size and what the sentence claims. What is the tell in each case — what would the other interpretation imply that is implausible?

Then: the first reader made the classic swap. If 3% is the SEM at n = 400, what is the SD, and what is the actual range most patients fall in? Show the √n conversion both ways, and state which band the sentence "most patients shrank between…" needs.

Finally: the second paper wants its effect to look precisely measured. If 80 ms is the SD at n = 4, compute the SEM, then explain why "± 80 ms, n = 4" is not evidence of precision at all — and what specifically they would have to change (not just recompute) to make the mean genuinely precise. Why can you not get a small SEM out of a large SD without doing that thing?

## External resources

Any statistics text's chapter on sampling distributions derives SEM = SD/√n from the variance of a sum of independent draws — the √n is not a convention, it falls out of the algebra, and seeing that derivation makes the "shrinks with n" behavior obvious.

Journal figure guidelines (for example Nature's) require every error bar to state whether it is SD, SEM, or a confidence interval, precisely because the same drawn bar means three different things — the requirement exists because this swap is common enough to legislate against.
