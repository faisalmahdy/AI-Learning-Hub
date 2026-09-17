---
id: data-inter-11
title: The law of small numbers — the most extreme rates come from the smallest samples, which is just noise
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 22 min
summary: Rank units by a rate and the top and bottom fill with the smallest samples, because small n is noisy — not because small units are special. The honest signal is the z-score, which shrinks with sample size. Here the eye-catching 0.30 and 0.00 rates are the two smallest samples (within noise); the real anomaly is a 0.13 rate over n=5000, 7 standard errors out.
eli5: If you flip a coin four times you might get all heads; flip it a thousand times and you'll get close to half. So the "luckiest" and "unluckiest" coin-flippers are always the ones who flipped only a few times. If you rank people by their heads-rate, the tiny-sample flippers win and lose — but they were just lucky, not special.
---

## Why this module

Sort anything by a rate and the extremes will be dominated by your smallest samples, and if you read that as a finding you have been fooled by sample size.

The setup is everywhere. You have units — clinics, counties, stores, schools, model variants, ad campaigns — each reporting how often something happened out of some number of trials. You rank them by the rate to find the best and worst performers. The top of the list and the bottom of the list fill up with the units that had the fewest trials. Not because small units are better or worse at anything, but because a small sample is noisy: with few trials, the observed rate swings far from the true rate on chance alone. Flip a fair coin four times and all-heads is common; flip it a thousand times and you land near half. The most extreme observed rates, high and low, come from wherever you had the least data.

This is the law of small numbers, and it produces confident, expensive mistakes. The classic case: someone maps cancer rates by county and finds the highest rates are in small rural counties, and spins a theory about rural life — until they notice the *lowest* rates are also in small rural counties, because small populations produce extreme rates in both directions. The pattern was sample size masquerading as signal. The same trap catches anyone who rewards the "top-performing" store or flags the "worst" clinic without asking how many observations each had.

The honest measure is not the raw rate but how far it sits from the baseline relative to its own noise — the z-score, which counts standard errors, and the standard error shrinks as the sample grows. An extreme rate over a tiny sample is only a couple of standard errors out: noise. A modest rate over a huge sample can be many standard errors out: signal. Ranking by z-score demotes the small-sample flukes and surfaces the units whose deviation is too large to be chance.

We will rank five units that all draw from the same 0.10 baseline. By raw rate, the winners are the two smallest samples — 0.30 at n=20 and 0.00 at n=25 — and both are within noise. By signal, the winner is a unit with an unremarkable 0.13 rate, because it is over n=5000 and sits 7 standard errors from baseline.

**Extreme rates cluster in small samples because small n is noisy; the z-score size-adjusts the rate, so it demotes the flukes the raw ranking crowns.**

## Concepts

The root fact is that the standard error of a rate scales as one over the square root of the sample size. Estimate a rate from n trials and the typical distance between your observed rate and the true rate is proportional to 1/√n. Quadruple the sample and you halve the noise; take a sample a hundred times larger and the noise drops tenfold. So small samples do not just occasionally produce extreme rates — they systematically produce a wider spread of rates, and the smallest samples produce the widest spread, which means they supply both the maximum and the minimum of any rate ranking.

That is why ranking by raw rate is a sample-size sort in disguise. The units with the least data have the most variable rates, so they populate the tails of the distribution regardless of any real effect. The units with the most data have rates pinned close to the truth, so they cluster in the middle and almost never top the ranking, even when they are the ones genuinely deviating. The ranking answers "who got the noisiest estimate," not "who is actually different," and those are opposite questions at the extremes.

The z-score fixes it by dividing the deviation by its own standard error. A rate that is 0.20 above baseline is impressive over a large sample and unremarkable over a tiny one, and the z-score encodes exactly that: same deviation, divided by a larger standard error for the small sample, yields a smaller z. It converts "how far from baseline" into "how many standard errors from baseline," which is the size-adjusted signal. A big z means the deviation is too large to explain by this sample's noise; a small z means it is well within it. Ranking by |z| surfaces real anomalies and buries sampling flukes.

The deeper fix, when you need to *estimate* each unit's rate rather than just rank them, is shrinkage: pull each unit's observed rate toward the baseline by an amount that depends on its sample size, so small samples get pulled hard (trust the baseline) and large samples barely move (trust the data). Empirical Bayes and hierarchical models formalize this, and it is why a well-built ranking of "best stores" or "top campaigns" never uses the raw rate. The z-score in this module is the ranking-only version of that same instinct: never trust a rate without weighing the n behind it.

**Standard error falls as 1/√n, so small samples own the tails of any rate ranking; the z-score divides deviation by that error, turning a sample-size sort into a signal sort.**

## Worked example

The fixture is five units, all drawn from the same baseline rate, with very different sample sizes.

```json filename=modules/ai-for-science-and-data/code/data-inter-11/units.json:7-20 COMPLETE
  "baseline_rate": 0.1,
  "units": {
    "A": {
      "n": 20,
      "successes": 6
    },
    "B": {
      "n": 25,
      "successes": 0
    },
    "C": {
      "n": 5000,
      "successes": 650
    },
```

Baseline 0.10. Unit A is 6 of 20, unit B is 0 of 25, unit C is 650 of 5000. Look at the raw rates.

```text filename=modules/ai-for-science-and-data/code/data-inter-11/smallnum.py --units
UNITS — observed rate per unit (baseline 0.10)
----------------------------------------------
  A  n=20    successes=6    rate 0.300
  B  n=25    successes=0    rate 0.000
  C  n=5000  successes=650  rate 0.130
  D  n=1000  successes=100  rate 0.100
  E  n=30    successes=7    rate 0.233
```

The eye goes straight to A at 0.300 (triple the baseline) and B at 0.000 (zero) — the extremes. Both are the smallest samples, n=20 and n=25. Unit C's 0.130 looks unremarkable next to them. But watch what happens when we weigh each rate against its own noise. The rate is successes over n; the standard error shrinks with n.

```python filename=modules/ai-for-science-and-data/code/data-inter-11/smallnum.py:42-43 COMPLETE
def rate(u):
    return u["successes"] / u["n"]
```

```python filename=modules/ai-for-science-and-data/code/data-inter-11/smallnum.py:46-48 COMPLETE
def std_error(n, p):
    """Standard error of a rate estimated from n trials at baseline p -- shrinks as 1/sqrt(n)."""
    return math.sqrt(p * (1 - p) / n)
```

The z-score is the deviation from baseline in standard errors — the size-adjusted signal.

```python filename=modules/ai-for-science-and-data/code/data-inter-11/smallnum.py:51-53 COMPLETE
def zscore(u, p):
    """How many standard errors the observed rate sits from baseline -- the signal, size-adjusted."""
    return (rate(u) - p) / std_error(u["n"], p)
```

Predict: A's big 0.20 deviation over a tiny sample should be a modest z; C's small 0.03 deviation over a huge sample should be a large z. Run it.

```text filename=modules/ai-for-science-and-data/code/data-inter-11/smallnum.py --signal
SIGNAL — rate vs standard error vs z-score, and the two rankings
--------------------------------------------------------------
  unit  n      rate    std err   z (signal)
  A     20     0.300   0.0671     +2.98
  B     25     0.000   0.0600     -1.67
  C     5000   0.130   0.0042     +7.07
  D     1000   0.100   0.0095     +0.00
  E     30     0.233   0.0548     +2.43
--------------------------------------------------------------
  ranked by raw rate: A > E > C > D > B
  ranked by signal:   C > A > E > B > D
```

The two rankings are almost reversed at the top. By raw rate: A (0.30) wins, B (0.00) is last — the two smallest samples own both ends. By signal: C wins by a mile at z = 7.07, while A's flashy 0.30 is only z = 2.98 and B's shocking 0.00 is a mere z = −1.67, well within the range you would see from 25 trials by chance. Unit C's boring 0.13 rate is the real anomaly — a deviation seven standard errors out is essentially impossible by luck over 5000 trials — and the raw-rate ranking buried it in the middle. The flashy extremes were noise; the quiet one was the signal.

<svg role="img" aria-label="Two rankings side by side: by raw rate A is first and C is third; by signal C is first and A is second, showing the reordering" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="60" y="24" font-family="var(--mono)" font-size="10" fill="var(--muted)">by raw rate</text>
  <text x="300" y="24" font-family="var(--mono)" font-size="10" fill="var(--muted)">by signal (z)</text>
  <g font-family="var(--mono)" font-size="10">
    <rect x="50" y="34" width="90" height="20" fill="var(--s2)" stroke="var(--line)"/><text x="62" y="48" fill="var(--ink)">A  0.30</text>
    <rect x="50" y="58" width="90" height="20" fill="var(--panel)" stroke="var(--line)"/><text x="62" y="72" fill="var(--ink)">E  0.23</text>
    <rect x="50" y="82" width="90" height="20" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="62" y="96" fill="var(--acc-ink)">C  0.13</text>
    <rect x="50" y="106" width="90" height="20" fill="var(--panel)" stroke="var(--line)"/><text x="62" y="120" fill="var(--ink)">D  0.10</text>
    <rect x="50" y="130" width="90" height="20" fill="var(--s2)" stroke="var(--line)"/><text x="62" y="144" fill="var(--ink)">B  0.00</text>
    <rect x="290" y="34" width="90" height="20" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="302" y="48" fill="var(--acc-ink)">C  7.07</text>
    <rect x="290" y="58" width="90" height="20" fill="var(--acc-soft)" stroke="var(--line)"/><text x="302" y="72" fill="var(--ink)">A  2.98</text>
    <rect x="290" y="82" width="90" height="20" fill="var(--acc-soft)" stroke="var(--line)"/><text x="302" y="96" fill="var(--ink)">E  2.43</text>
    <rect x="290" y="106" width="90" height="20" fill="var(--acc-soft)" stroke="var(--line)"/><text x="302" y="120" fill="var(--ink)">B  1.67</text>
    <rect x="290" y="130" width="90" height="20" fill="var(--panel)" stroke="var(--line)"/><text x="302" y="144" fill="var(--ink)">D  0.00</text>
  </g>
  <line x1="140" y1="44" x2="290" y2="92" stroke="var(--s2)" stroke-dasharray="3 2"/>
  <line x1="140" y1="92" x2="290" y2="44" stroke="var(--acc-ink)" stroke-dasharray="3 2"/>
</svg>
^ A tops the raw-rate list but drops to second on signal; C, buried at third by rate, is the runaway winner on signal — the two metrics cross exactly at the units where sample size mattered.

<svg role="img" aria-label="z-score bars: C at 7.07 towers over A 2.98, E 2.43, B minus 1.67, and D at 0" viewBox="0 0 460 160" width="460" height="160">
  <rect x="0" y="0" width="460" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">signal (|z| from baseline)</text>
  <line x1="40" y1="130" x2="440" y2="130" stroke="var(--line)"/>
  <line x1="40" y1="80" x2="440" y2="80" stroke="var(--grid)" stroke-dasharray="3 3"/><text x="360" y="76" font-family="var(--mono)" font-size="9" fill="var(--muted)">z=3.5 noise line</text>
  <rect x="70" y="34" width="50" height="96" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="82" y="28" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">C 7.1</text><text x="88" y="146" font-family="var(--mono)" font-size="8" fill="var(--muted)">n5000</text>
  <rect x="150" y="90" width="50" height="40" fill="var(--s2)" stroke="var(--line)"/><text x="162" y="84" font-family="var(--mono)" font-size="9" fill="var(--ink)">A 3.0</text><text x="164" y="146" font-family="var(--mono)" font-size="8" fill="var(--muted)">n20</text>
  <rect x="230" y="97" width="50" height="33" fill="var(--s2)" stroke="var(--line)"/><text x="242" y="91" font-family="var(--mono)" font-size="9" fill="var(--ink)">E 2.4</text><text x="244" y="146" font-family="var(--mono)" font-size="8" fill="var(--muted)">n30</text>
  <rect x="310" y="107" width="50" height="23" fill="var(--s2)" stroke="var(--line)"/><text x="322" y="101" font-family="var(--mono)" font-size="9" fill="var(--ink)">B 1.7</text><text x="324" y="146" font-family="var(--mono)" font-size="8" fill="var(--muted)">n25</text>
  <rect x="390" y="129" width="50" height="1" fill="var(--ink)" stroke="var(--line)"/><text x="402" y="123" font-family="var(--mono)" font-size="9" fill="var(--ink)">D 0</text>
</svg>
^ Only C clears the noise line; the flashy small-sample extremes A, E, and B all sit below it — visible on the raw-rate list, invisible as real signal.

<svg role="img" aria-label="A funnel plot: observed rate on the vertical axis, sample size on the horizontal, small samples spread wide above and below baseline while large samples cluster near it" viewBox="0 0 460 210" width="460" height="210">
  <rect x="0" y="0" width="460" height="210" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">observed rate vs sample size (baseline dashed)</text>
  <line x1="50" y1="110" x2="440" y2="110" stroke="var(--acc-ink)" stroke-dasharray="4 3"/><text x="20" y="114" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">0.10</text>
  <line x1="50" y1="40" x2="50" y2="190" stroke="var(--line)"/>
  <line x1="50" y1="190" x2="440" y2="190" stroke="var(--line)"/>
  <text x="60" y="204" font-family="var(--mono)" font-size="9" fill="var(--muted)">small n</text><text x="380" y="204" font-family="var(--mono)" font-size="9" fill="var(--muted)">large n (5000)</text>
  <path d="M70 45 Q250 105 430 108" fill="none" stroke="var(--grid)" stroke-dasharray="3 2"/>
  <path d="M70 175 Q250 115 430 112" fill="none" stroke="var(--grid)" stroke-dasharray="3 2"/>
  <text x="90" y="40" font-family="var(--mono)" font-size="8" fill="var(--muted)">noise funnel</text>
  <circle cx="80" cy="60" r="4" fill="var(--s2)"/><text x="86" y="58" font-family="var(--mono)" font-size="8" fill="var(--s2)">A 0.30 (n20)</text>
  <circle cx="90" cy="188" r="4" fill="var(--s2)"/><text x="96" y="186" font-family="var(--mono)" font-size="8" fill="var(--s2)">B 0.00 (n25)</text>
  <circle cx="110" cy="78" r="4" fill="var(--ink)"/><text x="116" y="76" font-family="var(--mono)" font-size="8" fill="var(--muted)">E 0.23 (n30)</text>
  <circle cx="300" cy="110" r="4" fill="var(--ink)"/><text x="270" y="128" font-family="var(--mono)" font-size="8" fill="var(--muted)">D 0.10 (n1000)</text>
  <circle cx="410" cy="98" r="5" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="330" y="90" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">C 0.13 (n5000) — signal</text>
</svg>
^ Small-sample units scatter far above and below the baseline inside the widening noise funnel; C sits only just above baseline but far outside the narrow funnel at n=5000 — a small deviation that is a big signal.

## Build

Reproduce the z-scores and the two rankings. Pure standard library, so 2.98, −1.67, 7.07 and the orderings come out exactly.

Run `--units` for the rates, `--signal` for the z-scores and rankings, `--check` for the gate. The self-test pins the whole lesson: the extremes are the smallest samples, those extremes are within noise, the strongest signal is the largest sample, and the two rankings disagree.

```python filename=modules/ai-for-science-and-data/code/data-inter-11/smallnum.py:89-94 COMPLETE
    by_rate = sorted(units, key=lambda name: rate(units[name]))
    smallest = sorted(ns, key=lambda name: ns[name])[:2]
    lowest, highest = by_rate[0], by_rate[-1]
    extremes_are_smallest = set([lowest, highest]) == set(smallest)
    print("  the highest and lowest raw rates are the two smallest samples = %s (%s and %s, n=%d and %d)"
          % (extremes_are_smallest, highest, lowest, ns[highest], ns[lowest]))
```

The `extremes_are_smallest` check is the one that makes the law of small numbers concrete rather than anecdotal. It asserts that the set of the two most extreme raw rates equals the set of the two smallest samples — not that they overlap, that they are the same two units. That exact-match is the phenomenon: it is not a coincidence that the extremes are small, it is a consequence of 1/√n, and the check demands the fixture exhibit it exactly. The rest of the gate follows.

```text filename=modules/ai-for-science-and-data/code/data-inter-11/smallnum.py --check
SELF-TEST — the extreme raw rates come from the smallest samples; the strongest signal is the largest
------------------------------------------------------------------------------------------------
  the highest and lowest raw rates are the two smallest samples = True (A and B, n=20 and 25)
  those extremes are within noise of baseline = True (|z| 2.98 and 1.67)
  the strongest signal is the largest sample = True (C, n=5000, z=7.07)
  ranking by raw rate and by signal disagree = True (rate top A, signal top C)
------------------------------------------------------------------------------------------------
SELF-TEST PASS  extremes_are_smallest=True  extremes_within_noise=True  strongest_is_largest=True  rankings_disagree=True
```

Four True flags. Extremes_are_smallest: the top and bottom raw rates are the two smallest samples. Extremes_within_noise: their z-scores are modest, so those extremes are chance. Strongest_is_largest: the biggest sample carries the strongest signal. Rankings_disagree: the raw-rate winner and the signal winner are different units. The last flag is the punchline — the metric you sort by decides who you crown, and only one of the two metrics is honest.

**The exact set-equality of "most extreme rates" and "smallest samples" is the law of small numbers made checkable — not a coincidence but a consequence of 1/√n.**

## Definition of done

You are done when you reproduce the rankings and can explain why they disagree.

Concretely: `--signal` shows A and B topping the raw-rate ranking but C topping the signal ranking; `--check` prints PASS with four True flags. You can explain why standard error scales as 1/√n and why that puts small samples at both tails of a rate ranking. You can define the z-score as deviation over standard error and explain why it demotes small-sample extremes and promotes large-sample deviations. And you can name the fix beyond ranking — shrinkage toward the baseline, weighted by sample size — and say why raw-rate leaderboards are untrustworthy.

The habit to carry: never rank or reward units by a raw rate without the sample size beside it. When the "best" and "worst" performers are all small, suspect the law of small numbers before any real effect, and rank by a size-adjusted signal — a z-score, a shrunk estimate, a confidence interval — instead.

## Boss fight

The instructive failure is a policy built on a leaderboard that was measuring nothing but sample size.

An education foundation studies test scores and finds that the highest-performing schools are disproportionately small. The conclusion writes itself: small schools are better, so break up the big ones. Millions are spent creating small schools. Then someone checks the *lowest*-performing schools and finds they are also disproportionately small — because small schools, with few students, have more variable average scores in both directions. The original finding was the law of small numbers, and the policy optimized for noise. This actually happened, and the size-adjusted analysis showed no small-school advantage at all. The raw-rate leaderboard cost real money and helped no student.

Your turn, two moves. First, confirm the funnel. For each unit compute the deviation from baseline times √n and notice it clusters — because multiplying by √n cancels the 1/√n in the standard error, turning raw deviations back into comparable signals. That transformation is what a funnel plot does by eye: rates fan out at small n and converge at large n, and points outside the fanning envelope are the real signals regardless of where they sit vertically. Second, break unit C to see the metric matter. Give C a rate of 0.10 exactly (n=5000, 500 successes) so its z drops to 0, and predict: the signal ranking now has no strong winner, the small-sample units A and E lead it with z around 2.5–3, and you would correctly conclude there is no anomaly worth chasing — whereas the raw-rate ranking would still crown A at 0.30 and send you after a fluke. The rankings only agree when there is no real signal to find; the moment there is one, only the size-adjusted metric points at it.

## External resources

Kahneman and Tversky's "Belief in the law of small numbers" (1971) is the original psychological treatment of why people over-read small-sample results; Kahneman's "Thinking, Fast and Slow" retells it with the small-county cancer-rate example this module echoes.

For the funnel plot and the size-adjusted view, any meta-analysis or quality-control reference covers it; the funnel plot's fanning envelope is exactly the 1/√n noise band, and points outside it are the genuine outliers.

For the estimation fix, Efron and Morris's classic "Stein's paradox in statistics" and any treatment of empirical Bayes / James-Stein shrinkage show why pulling small-sample estimates toward a common mean beats trusting each raw rate — the principled version of the z-score ranking here.
