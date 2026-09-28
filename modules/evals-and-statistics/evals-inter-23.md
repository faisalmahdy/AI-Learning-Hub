---
id: evals-inter-23
title: Don't stop the A/B test when it first hits significance — or peeking inflates the false-positive rate
topic: evals-and-statistics
level: intermediate
status: ready
time: 18 min
summary: A test at alpha=0.05 promises that if the variants are truly identical you wrongly call them different only 5% of the time — but that promise holds for one look at a sample size fixed in advance. Watch the test run and stop as soon as the p-value dips below 0.05, and you are no longer taking one 5% gamble; you are taking a fresh gamble at every peek and keeping the first that wins. The running statistic wanders like a random walk under the null, so given enough looks it crosses the line by chance, and a peeker who stops at the first crossing declares a winner that does not exist. On a fixture where the variants are identical (every "significant" is false), looking once gives a false-positive rate of 0.05 while peeking at five points and stopping early gives 0.135 — almost triple — and the rate climbs monotonically with the number of peeks: 0.05, 0.08, 0.10, 0.12, 0.14.
eli5: If you flip a fair coin and only decide "heads wins" once, you have a fair chance. But if you get to keep flipping and shout "I win!" the moment you're ahead, you'll almost always eventually be ahead by luck and stop there. Watching an experiment and stopping the instant it looks good is the same trick played on yourself — you give luck many chances and keep the one where it paid off, so you "find" a result that isn't real.
---

## Why this module

The 5% error rate a significance test promises is the error rate of looking once, and every extra time you check a running test and let yourself stop is another independent chance to be fooled.

A test at alpha=0.05 guarantees that under the null — the variants are truly the same — you will cross the significance threshold only 5% of the time. That guarantee is about a single test on a sample whose size you fixed before collecting data. Live experimentation breaks the assumption: you watch the metric accumulate, and the moment the p-value drops below 0.05 you stop and declare a winner. But the test statistic is not still — as samples arrive it wanders up and down, and under the null it behaves like a random walk that will, sooner or later, drift across the 1.96 line purely by chance. Each time you peek, you give that walk another opportunity to be across the line at the moment you look, and you keep the first opportunity that succeeds. You are not running one 5% test; you are running one at every peek and reporting the luckiest.

**The nominal false-positive rate is the rate for a single look at a fixed sample size, so peeking at a running test and stopping at the first significant result takes many chances at the 5% event and inflates the real false-positive rate far above alpha.**

The discipline is to fix the sample size in advance and look once, at the end — then the statistic gets a single chance to cross and the false-positive rate is the nominal alpha. If you genuinely need to monitor a test and stop early, you cannot use the fixed-sample cutoff; you need a sequential method (alpha spending, group-sequential boundaries, or a Bayesian test) that budgets the error across the looks so the total stays at alpha. The sin is not looking — it is looking with a threshold that assumed a single look. This module simulates identical variants and shows peeking manufacture false positives that a single look does not.

## Concepts

**The false-positive rate** is how often you call identical variants "different." A correct test at alpha=0.05 holds it at 5% — for one look at a pre-fixed sample size.

**The running statistic is a random walk.** Under the null, as data accumulates the z-statistic wanders, and a wandering series eventually crosses any fixed line by chance if you watch long enough.

**Peeking (optional stopping)** checks significance repeatedly and stops at the first crossing. Each peek is another chance for the walk to be over the line, so the crossings accumulate.

```python filename=modules/evals-and-statistics/code/evals-inter-23/peeking.py:44-55 COMPLETE
def crosses_any(seed, peeks, z_cutoff):
    """One trial under the null: streaming samples, does |z| cross the cutoff at ANY peek (stop-early peeking)?"""
    r = random.Random(seed)
    total, n, prev = 0.0, 0, 0
    for p in peeks:
        for _ in range(p - prev):
            total += r.gauss(0, 1)
            n += 1
        prev = p
        if abs(total / math.sqrt(n)) > z_cutoff:
            return True
    return False
```

**A single fixed-N look** gives the statistic one chance to cross, so its false-positive rate is the nominal alpha.

**Sequential methods** are the correct fix for early stopping — they spread the alpha budget across the planned looks so the total false-positive rate stays at alpha, at the cost of a stricter per-look threshold.

**The false-positive guarantee is a property of the analysis plan, not just the data — decide the sample size and the number of looks in advance, because a fixed-N threshold checked repeatedly is no longer a 5% test.**

<svg role="img" aria-label="Under the null the z-statistic wanders and briefly pokes above the 1.96 line at one peek before falling back; a peeker stops there" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">running z-statistic under the null (variants identical)</text>
  <line x1="25" y1="60" x2="285" y2="60" stroke="var(--grid)" stroke-width="1" stroke-dasharray="2 3"/><text x="26" y="58" fill="var(--muted)" font-size="7">0</text>
  <line x1="25" y1="32" x2="285" y2="32" stroke="var(--s2)" stroke-width="1" stroke-dasharray="3 2"/><text x="26" y="30" fill="var(--s2)" font-size="7">1.96</text>
  <polyline points="25,58 60,50 95,44 130,28 165,46 200,52 235,40 270,55" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <circle cx="130" cy="28" r="3" fill="var(--s2)"/><text x="112" y="24" fill="var(--s2)" font-size="7">peeker stops here</text>
  <text x="60" y="76" fill="var(--muted)" font-size="7">↑ peek points ↑</text>
  <text x="25" y="92" fill="var(--muted)" font-size="8">the walk pokes over 1.96 by chance at one look, then falls back — a peeker keeps the crossing</text>
  <text x="25" y="104" fill="var(--muted)" font-size="8">looking only at the end (z=−0.5 here) would correctly find nothing</text>
</svg>
^ The statistic wanders under the null and briefly crosses 1.96 at the fourth peek by luck before drifting back; a peeker stops at that crossing, while a single end-of-test look would have seen no effect.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/evals-and-statistics/code/evals-inter-23/peeking.py

The fixture is a peek schedule, the z-cutoff, and a trial count — with the variants identical, so every "significant" is false.

```json filename=modules/evals-and-statistics/code/evals-inter-23/peeking.json:1-6 COMPLETE
{
  "_meta": "A peeking simulation for a running A/B test under the NULL hypothesis (the two variants are truly identical, so any 'significant' result is a false positive). Each trial streams standard-normal samples of the difference; after reaching each sample count in `peeks`, we compute the z-statistic (running mean times sqrt(n)) and test |z| > z_cutoff (1.96 for a 5% two-sided test). A DISCIPLINED analysis looks only once, at the final sample count, and its false-positive rate is the nominal alpha. A PEEKING analysis checks at every peek and stops the moment any check crosses -- so it gets many chances at the 5% event, and its false-positive rate climbs far above alpha. trials averages over many independent runs; base_seed seeds them. The samples are drawn under the null, so every 'significant' is a false alarm.",
  "peeks": [100, 200, 300, 400, 500],
  "z_cutoff": 1.96,
  "trials": 3000,
  "base_seed": 0
}
```

The false-positive rate is the fraction of null trials that cross at any peek in the schedule.

```python filename=modules/evals-and-statistics/code/evals-inter-23/peeking.py:58-60 COMPLETE
def false_positive_rate(peeks, z_cutoff, trials, base_seed):
    """Fraction of null trials that cross at any peek in the schedule."""
    return sum(crosses_any(base_seed + i, peeks, z_cutoff) for i in range(trials)) / trials
```

Run `--rate` to compare one look with peeking.

```text filename=--rate
RATE — false-positive rate under the null (variants identical), 3000 trials
--------------------------------------------------------------
  look once at n=500 (disciplined):   0.050   (nominal alpha)
  peek at 5 points, stop early:      0.135   (2.7x alpha)
--------------------------------------------------------------
  every 'significant' here is false; peeking manufactures 8% more of them.
```

Both analyses use the exact same data and the exact same 1.96 cutoff — the only difference is when they look. Looking once, at the final 500 samples, gives a false-positive rate of 0.050, precisely the nominal 5%: the test is correct when used as designed. Peeking at all five points and stopping at the first crossing gives 0.135 — 2.7 times the alpha you thought you were risking. Since the variants are identical here, every one of those "significant" results is a false alarm, and peeking produced them at almost triple the honest rate. The threshold did not change; the number of chances did.

<svg role="img" aria-label="Looking once gives a false-positive rate of 0.05; peeking at five points gives 0.135, against the nominal 0.05 line" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">false-positive rate under the null (nominal 0.05)</text>
  <line x1="60" y1="20" x2="60" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <line x1="60" y1="78" x2="285" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <line x1="127" y1="20" x2="127" y2="78" stroke="var(--line)" stroke-width="1" stroke-dasharray="3 3"/><text x="105" y="18" fill="var(--muted)" font-size="7">alpha</text>
  <rect x="60" y="26" width="67" height="16" fill="var(--s1)"/><text x="131" y="38" fill="var(--muted)" font-size="8">look once: 0.05</text>
  <rect x="60" y="50" width="182" height="16" fill="var(--s2)"/><text x="84" y="62" fill="var(--panel)" font-size="8">peek at 5: 0.135 (2.7x)</text>
  <text x="60" y="94" fill="var(--muted)" font-size="8">same data, same cutoff — only the number of looks differs</text>
</svg>
^ The single-look bar lands on the alpha line; the peeking bar runs almost three times past it, all of it false positives since the variants are identical.

## Build

Where does the inflation come from? Run `--growth`.

```text filename=--growth
GROWTH — false-positive rate as the number of peeks grows
--------------------------------------------------------------
  1 look :  false-positive rate 0.049
  2 looks:  false-positive rate 0.079
  3 looks:  false-positive rate 0.101
  4 looks:  false-positive rate 0.123
  5 looks:  false-positive rate 0.135
--------------------------------------------------------------
  each extra peek is another chance at the 5% event, so the rate only climbs.
```

With one look the rate is 0.049 — the nominal alpha, correct. Each additional peek adds roughly two to three points of false-positive rate: 0.08 at two looks, 0.10 at three, 0.12 at four, 0.135 at five. The climb is monotonic because every peek can only add crossings, never remove them — a trial that already crossed stays counted, and a new peek gives the still-uncrossed trials a fresh chance. Continuous monitoring is the limit of this: peek after every single sample and the false-positive rate climbs toward 1, meaning a watched A/B test under the null will *eventually* show a significant result essentially every time if you wait for one. The p-value you are watching is not converging to a verdict; it is wandering, and you are cherry-picking its lowest excursion.

<svg role="img" aria-label="The false-positive rate rises from 0.049 at one look to 0.135 at five looks, climbing with each peek" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">false-positive rate vs number of peeks</text>
  <line x1="30" y1="20" x2="30" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="90" x2="285" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="78" x2="285" y2="78" stroke="var(--line)" stroke-width="1" stroke-dasharray="2 3"/><text x="255" y="76" fill="var(--muted)" font-size="7">alpha</text>
  <polyline points="55,78 108,64 161,50 214,38 267,28" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="55" cy="78" r="2.5" fill="var(--s2)"/><text x="48" y="90" fill="var(--muted)" font-size="7">1</text><text x="42" y="76" fill="var(--muted)" font-size="7">.05</text>
  <circle cx="267" cy="28" r="2.5" fill="var(--s2)"/><text x="262" y="90" fill="var(--muted)" font-size="7">5</text><text x="252" y="26" fill="var(--s2)" font-size="7">.135</text>
  <text x="30" y="106" fill="var(--muted)" font-size="8">the first look is at alpha; every added peek pushes the rate further above it</text>
</svg>
^ The curve starts on the alpha line at one look and rises with each additional peek, a monotonic climb toward the certainty of a false positive under continuous monitoring.

## Definition of done

The self-test pins it: one look is at alpha, peeking is inflated past 2x alpha, peeking beats one look, and the rate climbs monotonically with the number of peeks.

```python filename=modules/evals-and-statistics/code/evals-inter-23/peeking.py:95-109 COMPLETE
    one_look_at_alpha = abs(once - 0.05) < 0.02
    print("  looking once gives about the nominal 5%% false-positive rate = %s (%.3f)" % (one_look_at_alpha, once))

    peeking_inflated = peeking > 2 * 0.05
    print("  peeking inflates the false-positive rate past 2x alpha = %s (%.3f)" % (peeking_inflated, peeking))

    peeking_above_once = peeking > once
    print("  peeking is worse than looking once = %s (%.3f > %.3f)" % (peeking_above_once, peeking, once))

    rates = [false_positive_rate(peeks[:k], z, trials, seed) for k in range(1, len(peeks) + 1)]
    monotonic = all(rates[i] <= rates[i + 1] for i in range(len(rates) - 1)) and rates[-1] > rates[0]
    print("  the false-positive rate climbs with the number of peeks = %s (%s)" % (monotonic, [round(r, 3) for r in rates]))

    reproducible = false_positive_rate(peeks, z, trials, seed) == peeking
    print("  the seeded simulation is reproducible = %s (%.3f)" % (reproducible, peeking))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — one look sits at alpha; peeking inflates the false-positive rate; more peeks make it worse
--------------------------------------------------------------------------------------------------------
  looking once gives about the nominal 5% false-positive rate = True (0.050)
  peeking inflates the false-positive rate past 2x alpha = True (0.135)
  peeking is worse than looking once = True (0.135 > 0.050)
  the false-positive rate climbs with the number of peeks = True ([0.049, 0.079, 0.101, 0.123, 0.135])
  the seeded simulation is reproducible = True (0.135)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  one_look_at_alpha=True  peeking_inflated=True  peeking_above_once=True  monotonic=True  reproducible=True
```

**Done means the inflation is proven and located: one look sits at the nominal 0.050, peeking at five points reaches 0.135 (2.7x alpha), and the rate climbs monotonically 0.049 → 0.079 → 0.101 → 0.123 → 0.135 as looks are added — every one of them a false positive, since the variants are identical.**

## Boss fight

Fixing the sample size in advance solves peeking, but predict the cost, and whether you can ever legitimately stop a test early. It is tempting to conclude you must never look at a running experiment.

Fixing the sample size and looking once costs you the ability to stop early, which is a real cost: a variant that is clearly winning has to run to the planned end before you can call it, and a variant that is clearly harming users cannot be killed on the statistics alone. You do not have to accept that — you have to pay for early stopping correctly. Group-sequential designs (O'Brien-Fleming, Pocock boundaries) pre-plan a handful of looks with stricter thresholds at each, spending the alpha budget so the total stays at 5%; alpha-spending functions generalize this to flexible timing; and Bayesian or always-valid (anytime-valid, e-value/mSPRT) methods give a statistic you can monitor continuously without inflation. Each buys the right to peek by demanding more evidence per look, so early stopping is possible — just not with the naive fixed-N cutoff you would use for a single look. Choose the method before the test, and it tells you exactly how strict each interim look must be.

The subtler trap is that peeking is one member of a family of "researcher degrees of freedom" that all inflate false positives the same way: stopping when significant, but also adding samples until significant, trying subgroups until one is significant, or switching the metric to the one that reached significance. Each is optional stopping in disguise — you let the data decide when or what to test, and keep the winning roll. The single defense is the same across all of them: pre-register the analysis. Decide the sample size, the metric, the subgroups, and the number of looks before seeing the data, and stick to it. A result is only worth the alpha it claims if the decision to declare it was made independent of the data that declared it — and a running p-value watched until it dips is the opposite of that.

```python filename=modules/evals-and-statistics/code/evals-inter-23/peeking.py:58-60 COMPLETE
def false_positive_rate(peeks, z_cutoff, trials, base_seed):
    """Fraction of null trials that cross at any peek in the schedule."""
    return sum(crosses_any(base_seed + i, peeks, z_cutoff) for i in range(trials)) / trials
```

**A fixed-N significance threshold checked repeatedly is not a 5% test — every peek is another chance for the wandering statistic to cross by luck, so peeking at five points nearly triples the false-positive rate and continuous monitoring drives it toward one; fix the sample size and look once, or pay for early stopping with a sequential or anytime-valid method, and pre-register the whole plan because peeking is just one of the researcher degrees of freedom that manufacture significance.**

## External resources

Evan Miller's "How Not to Run an A/B Test" — the widely-cited demonstration that stopping a test at the first significant result massively inflates the false-positive rate, with the intuition and the numbers.

The literature on group-sequential and alpha-spending designs (O'Brien-Fleming, Pocock) and always-valid inference (Johari et al., "Peeking at A/B Tests") — the correct methods for monitoring a test and stopping early without inflating alpha.

The companion "correct for multiple comparisons" and "optimize the proxy and it stops measuring the target" modules — peeking is multiplicity across time as multiple comparisons is across metrics, and both are ways the freedom to choose after seeing the data manufactures false results.
