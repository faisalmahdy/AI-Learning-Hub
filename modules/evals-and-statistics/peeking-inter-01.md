---
id: peeking-inter-01
title: Fix the sample size before you look — peeking at an experiment and stopping at the first significant result manufactures false positives
topic: evals-and-statistics
level: intermediate
status: ready
time: 15 min
summary: You run an A/B test and watch the dashboard; on day three the p-value dips below 0.05, the result is "significant", and you ship. This feels like diligence but is the single most common way online experiments produce effects that are not real. The problem is not any one look — it is looking repeatedly and stopping at whichever look happens to cross the line. Even when the two arms are identical, with no true effect, the test statistic wanders as data accumulates, and a wandering statistic given many chances to cross a threshold will eventually cross by chance; stop at that moment and you have declared a real effect from pure noise. The nominal 5% false-positive rate is the probability of crossing on one predetermined look — a guarantee about a single test, not a sequence. Each peek is another chance for the noise to cross, so the probability that some look crosses climbs well past 5%. Fixed-horizon discipline — decide the sample size in advance, look once at the end, judge significance only by that final look — keeps the guarantee intact. What makes peeking seductive is that the false positives look like early wins: the statistic crosses at an interim look and, if you had kept going, would often have drifted back below the threshold by the planned end, but the peeking analyst never sees the drift-back because they stopped and shipped. On eight A/A tests (identical arms, true effect zero, every "significant" result a false positive), the fixed-horizon rule flags 1 of 8 (12%, near nominal for this tiny sample) while peeking flags 5 of 8 (62%), four of them on trajectories that crossed at an interim look and fell back below 1.96 by the end.
eli5: Imagine you and a friend flip a coin to see who is luckier, and you agree the winner is whoever is ahead after exactly 100 flips. Fair enough — if the coins are the same, you each have about an even shot. But now imagine you instead say "let's stop the moment either of us is 20 flips ahead." Because the lead bounces around as you flip, sooner or later someone will happen to be 20 ahead just by luck, even though neither coin is better — and whoever calls "stop!" at that lucky moment gets to claim they are luckier. Checking over and over and stopping at the best moment lets pure luck look like a real difference. The honest way is to decide the finish line first and only check the score there.
---

## Why this module

Watching an experiment live feels responsible. The data are arriving, the p-value is on the dashboard, and the moment it crosses 0.05 you have your answer — why wait? This instinct, checking significance repeatedly and acting on the first crossing, is called peeking or optional stopping, and it quietly destroys the one guarantee a significance test is supposed to give you. It is worth seeing concretely because nothing about it looks like cheating: every individual p-value is computed correctly, and the effect you "find" is often plausible and even directionally sensible. The error is entirely in the stopping rule, not the statistics.

The guarantee a 0.05 threshold gives you is narrow: if there is no real effect, the probability of crossing the threshold on one predetermined look is 5%. That is a promise about a single test at a single, pre-committed sample size. It says nothing about what happens if you check ten times. And when the two arms are genuinely identical — an A/A test, no effect at all — the test statistic does not sit at zero; it wanders as noise accumulates, wandering more than you would guess. Give that wandering statistic many chances to cross the line and the probability that it crosses on at least one look climbs far above 5%. Peek at every look and stop at the first crossing, and you have built a machine for turning noise into significance.

This module makes the mechanism literal: eight A/A tests where the truth is known to be null, evaluated two ways — once by looking only at the end, once by peeking at every look.

**Fix the sample size in advance and evaluate significance only at that predetermined endpoint, rather than checking at every interim look and stopping at the first crossing, because the 0.05 false-positive rate is the probability of crossing on a single look — repeated looks give the wandering statistic many chances to cross, inflating the real rate far above nominal, and the crossings that trigger an early stop are disproportionately the noise excursions that would have reverted by the planned end.**

## Concepts

The fixture is eight A/A tests. In each, the two arms are identical, so the true effect is zero and every "significant" result is by definition a false positive. Each trajectory records the two-sided z-statistic at five successive interim looks as data accumulates; because there is no effect, the z just wanders around zero. The threshold is 1.96, the two-sided 0.05 critical value.

```json filename=modules/evals-and-statistics/code/peeking-inter-01/peeking.json:3-4 COMPLETE
  "z_threshold": 1.96,
  "true_effect": 0,
```

The trajectories themselves are the recorded z-paths — eight null tests, five looks each.

```json filename=modules/evals-and-statistics/code/peeking-inter-01/peeking.json:16-25 COMPLETE
  "trajectories": {
    "t1": [0.5, 1.2, 2.10, 1.4, 0.30],
    "t2": [0.3, 0.8, 1.10, 0.9, 0.50],
    "t3": [1.0, 2.30, 1.8, 1.0, 0.70],
    "t4": [0.2, 0.6, 1.0, 1.5, 1.20],
    "t5": [0.7, 1.3, 0.9, 2.05, 0.40],
    "t6": [0.4, 0.9, 1.3, 1.1, 0.60],
    "t7": [0.6, 1.1, 1.9, 2.40, 2.10],
    "t8": [0.8, 1.4, 2.20, 1.0, 0.50]
  }
```

The two decision rules differ in one thing: which looks they are allowed to consult. The fixed-horizon rule sees only the final look — the pre-committed endpoint — and declares significance only if the z there reaches 1.96. The peeking rule sees every look and declares significance the first time any of them crosses.

```python filename=modules/evals-and-statistics/code/peeking-inter-01/peeking.py:44-66 COMPLETE
def crosses_peeking(traj, thr):
    """Under peeking, the test 'wins' if ANY interim look reaches the threshold."""
    return any(abs(z) >= thr for z in traj)


def first_crossing(traj, thr):
    """The interim look index (1-based) where peeking would stop, or None."""
    for i, z in enumerate(traj):
        if abs(z) >= thr:
            return i + 1
    return None


def crosses_fixed(traj, thr):
    """Under a fixed horizon, the test 'wins' only if the FINAL look reaches the threshold."""
    return abs(traj[-1]) >= thr


def rate(flags):
    return sum(flags) / len(flags)
```

That is the whole difference — `any` over the looks versus the last look alone. The false-positive rate of each rule is just the fraction of the eight null tests it flags.

<svg role="img" aria-label="A wandering z-statistic over five looks that rises above the 1.96 threshold line at look 3 then falls back below it by look 5" viewBox="0 0 320 160">
  <line x1="35" y1="20" x2="35" y2="140" stroke="var(--line)" stroke-width="1"/>
  <line x1="35" y1="140" x2="300" y2="140" stroke="var(--line)" stroke-width="1"/>
  <line x1="35" y1="55" x2="300" y2="55" stroke="var(--ink)" stroke-width="1.3" stroke-dasharray="4 3"/>
  <text x="240" y="50" font-size="9" fill="var(--ink)">threshold 1.96</text>
  <text x="14" y="59" font-size="8" fill="var(--muted)">1.96</text>
  <text x="20" y="143" font-size="8" fill="var(--muted)">0</text>
  <polyline points="60,120 120,92 180,45 240,82 290,131" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="60" cy="120" r="3" fill="var(--s2)"/>
  <circle cx="120" cy="92" r="3" fill="var(--s2)"/>
  <circle cx="180" cy="45" r="4" fill="var(--s1)"/>
  <circle cx="240" cy="82" r="3" fill="var(--s2)"/>
  <circle cx="290" cy="131" r="4" fill="var(--s2)"/>
  <text x="150" y="34" font-size="8.5" fill="var(--s1)">peeker stops here (0.30 final never seen)</text>
  <text x="255" y="127" font-size="8.5" fill="var(--muted)">final: 0.30</text>
  <text x="52" y="155" font-size="8" fill="var(--muted)">look1</text>
  <text x="272" y="155" font-size="8" fill="var(--muted)">look5</text>
</svg>
^ Trajectory t1: the z wanders up across 1.96 at look 3, where a peeker stops and ships, then drifts back to 0.30 by the planned end. The fixed-horizon rule sees only that 0.30 and correctly calls it null.

**The two rules read the same numbers; peeking simply grants itself five chances to find a crossing where the fixed horizon takes one, and five chances at a 5%-per-look event is no longer a 5% event.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the experiment-analysis step of an evaluation harness, reduced to eight recorded A/A trajectories so every crossing and rate is checkable by hand.

Run `--trajectories` to see each null test's path and whether it ever crosses.

```text filename=peeking.py --trajectories
  test   z at looks 1..5                 peak    ever crosses?   stops at look
  t1     0.50 1.20 2.10 1.40 0.30        2.10    True           3
  t2     0.30 0.80 1.10 0.90 0.50        1.10    False          -
  t3     1.00 2.30 1.80 1.00 0.70        2.30    True           2
  t4     0.20 0.60 1.00 1.50 1.20        1.50    False          -
  t5     0.70 1.30 0.90 2.05 0.40        2.05    True           4
  t6     0.40 0.90 1.30 1.10 0.60        1.30    False          -
  t7     0.60 1.10 1.90 2.40 2.10        2.40    True           4
  t8     0.80 1.40 2.20 1.00 0.50        2.20    True           3
```

Read the "ever crosses?" column: five of the eight trajectories touch 1.96 at some interim look — t1 at look 3, t3 at look 2, and so on. But look at where they end. t1 finishes at 0.30, t3 at 0.70, t5 at 0.40, t8 at 0.50 — all comfortably below the threshold. These are noise excursions that peaked mid-experiment and reverted. Only t7 is still above 1.96 at the final look.

Now `--rates` applies the two rules and counts.

```text filename=peeking.py --rates
  fixed-horizon flags: ['t7']
  peeking flags:       ['t1', 't3', 't5', 't7', 't8']
  false-positive rate  fixed-horizon = 1/8 = 12%   peeking = 5/8 = 62%
  peeked 'wins' that had reverted below 1.96 by the final look: ['t1', 't3', 't5', 't8']
```

The fixed-horizon rule flags one test, t7 — a 12% false-positive rate, which for eight tests is in the neighborhood of the nominal 5% you accept by design. Peeking flags five — 62% — on the exact same data. And the last line names the mechanism: four of peeking's five "wins" (t1, t3, t5, t8) had already reverted below the threshold by the end. The fixed-horizon analyst would have correctly called all four null; the peeker shipped them because they stopped at the crossing and never saw the revert.

**On identical arms, changing nothing but the stopping rule takes the false-positive rate from 12% to 62% — the extra false positives are precisely the trajectories that peaked on noise and would have come back.**

## Build

The self-test asserts the setup and the failure: every test is genuinely null, the fixed-horizon rate stays near nominal, and peeking's rate is inflated well above it. Establishing that the arms are identical is what makes every peeking "win" provably a false positive rather than a real effect caught early.

```python filename=modules/evals-and-statistics/code/peeking-inter-01/peeking.py:120-133 COMPLETE
    all_aa_tests = data["true_effect"] == 0
    print("  every test is an A/A test (true effect zero, so any win is a false positive) = %s" % all_aa_tests)

    fixed_horizon_near_nominal = fixed_rate <= 0.20
    print("  fixed-horizon false-positive rate stays near nominal = %s (%d/%d = %.0f%%)" % (fixed_horizon_near_nominal, sum(fixed_flags), len(names), 100 * fixed_rate))

    peeking_inflated = peek_rate > fixed_rate
    print("  peeking's false-positive rate exceeds the fixed-horizon rate = %s (%.0f%% > %.0f%%)" % (peeking_inflated, 100 * peek_rate, 100 * fixed_rate))

    peeking_at_least_doubles = peek_rate >= 2 * fixed_rate
    print("  peeking at least doubles the false-positive rate = %s (%.0f%% vs %.0f%%)" % (peeking_at_least_doubles, 100 * peek_rate, 100 * fixed_rate))
```

<svg role="img" aria-label="Eight test rows; the fixed-horizon column flags one, the peeking column flags five, four of them marked as reverted" viewBox="0 0 330 150">
  <text x="70" y="16" font-size="9" fill="var(--muted)">fixed-horizon</text>
  <text x="200" y="16" font-size="9" fill="var(--muted)">peeking</text>
  <text x="10" y="34" font-size="8.5" fill="var(--ink)">t1</text>
  <rect x="70" y="26" width="12" height="10" fill="none" stroke="var(--line)"/>
  <rect x="200" y="26" width="12" height="10" fill="var(--s2)"/>
  <text x="220" y="35" font-size="7.5" fill="var(--muted)">reverted</text>
  <text x="10" y="50" font-size="8.5" fill="var(--ink)">t3</text>
  <rect x="70" y="42" width="12" height="10" fill="none" stroke="var(--line)"/>
  <rect x="200" y="42" width="12" height="10" fill="var(--s2)"/>
  <text x="220" y="51" font-size="7.5" fill="var(--muted)">reverted</text>
  <text x="10" y="66" font-size="8.5" fill="var(--ink)">t5</text>
  <rect x="70" y="58" width="12" height="10" fill="none" stroke="var(--line)"/>
  <rect x="200" y="58" width="12" height="10" fill="var(--s2)"/>
  <text x="220" y="67" font-size="7.5" fill="var(--muted)">reverted</text>
  <text x="10" y="82" font-size="8.5" fill="var(--ink)">t7</text>
  <rect x="70" y="74" width="12" height="10" fill="var(--s1)"/>
  <rect x="200" y="74" width="12" height="10" fill="var(--s2)"/>
  <text x="220" y="83" font-size="7.5" fill="var(--muted)">stays up</text>
  <text x="10" y="98" font-size="8.5" fill="var(--ink)">t8</text>
  <rect x="70" y="90" width="12" height="10" fill="none" stroke="var(--line)"/>
  <rect x="200" y="90" width="12" height="10" fill="var(--s2)"/>
  <text x="220" y="99" font-size="7.5" fill="var(--muted)">reverted</text>
  <text x="10" y="120" font-size="8.5" fill="var(--muted)">t2,t4,t6: neither flags</text>
  <text x="70" y="138" font-size="8.5" fill="var(--s1)">1 of 8 = 12%</text>
  <text x="200" y="138" font-size="8.5" fill="var(--s2)">5 of 8 = 62%</text>
</svg>
^ Fixed-horizon flags only t7 (still above the line at the end). Peeking flags five — t7 plus the four that peaked and reverted. The four reverted rows are the entire gap between 12% and 62%.

Running the check confirms every clause, including the reversion mechanism.

```text filename=peeking.py --check
  every test is an A/A test (true effect zero, so any win is a false positive) = True
  fixed-horizon false-positive rate stays near nominal = True (1/8 = 12%)
  peeking's false-positive rate exceeds the fixed-horizon rate = True (62% > 12%)
  peeking at least doubles the false-positive rate = True (62% vs 12%)
  some peeked wins had reverted below the threshold by the end = True (['t1', 't3', 't5', 't8'])
  the fixed-horizon rule correctly ignores those reverted trajectories = True
```

**The check pins that peeking's extra flags are exactly the reverted trajectories the fixed-horizon rule ignores — so the inflation is the stopping rule harvesting noise excursions, not a real signal the peeker was faster to see.**

## Definition of done

Two properties close it. Peeking must at least double the fixed-horizon rate — a real, large inflation, not a rounding difference — and the extra flags must be trajectories that reverted, with the fixed-horizon rule correctly ignoring them. The second is what proves the inflation is manufactured by the stopping rule rather than being a genuine effect peeking detected sooner.

```python filename=modules/evals-and-statistics/code/peeking-inter-01/peeking.py:135-141 COMPLETE
    reverted = [n for n in names if crosses_peeking(trajs[n], thr) and not crosses_fixed(trajs[n], thr)]
    reversion_drives_it = len(reverted) > 0
    print("  some peeked wins had reverted below the threshold by the end = %s (%s)" % (reversion_drives_it, reverted))

    fixed_ignores_reverted = all(not crosses_fixed(trajs[n], thr) for n in reverted)
    print("  the fixed-horizon rule correctly ignores those reverted trajectories = %s" % fixed_ignores_reverted)
```

The honest framing matters here, so the module is not oversold. This is an illustrative hand-set sample of eight tests; the exact numbers (12%, 62%) are not a measured false-positive rate for any specific number of looks — they demonstrate the mechanism on a small, transparent set. The general, established result is that peeking inflates the false-positive rate above the nominal level, and the inflation grows with the number of looks: continuously monitoring an A/A test and stopping at the first crossing drives the eventual false-positive rate toward certainty. The fix is not to forbid looking — teams need to monitor experiments — but to use a method built for repeated looks: pre-registered fixed horizons, or sequential procedures (alpha-spending, group-sequential boundaries, always-valid p-values) that budget the error across looks so the guarantee survives peeking.

<svg role="img" aria-label="A rising curve showing the probability that a null test crosses the threshold on at least one look, climbing from 5 percent at one look toward high values as looks increase" viewBox="0 0 320 150">
  <line x1="40" y1="20" x2="40" y2="125" stroke="var(--line)" stroke-width="1"/>
  <line x1="40" y1="125" x2="300" y2="125" stroke="var(--line)" stroke-width="1"/>
  <line x1="40" y1="113" x2="300" y2="113" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 3"/>
  <text x="4" y="117" font-size="8" fill="var(--muted)">5%</text>
  <text x="4" y="26" font-size="8" fill="var(--muted)">high</text>
  <polyline points="55,113 100,92 150,74 200,60 250,50 290,44" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="55" cy="113" r="3" fill="var(--s1)"/>
  <text x="48" y="105" font-size="8" fill="var(--s1)">1 look = 5%</text>
  <text x="150" y="145" font-size="8.5" fill="var(--muted)">number of looks →</text>
  <text x="120" y="40" font-size="8.5" fill="var(--s2)">P(some look crosses) climbs with looks</text>
</svg>
^ The nominal 5% holds only at one look (the dashed line). Each added peek gives the wandering null statistic another chance to cross, so the probability that some look crosses rises — the more you peek, the further above 5% the real false-positive rate sits.

**Done means peeking at least doubles the false-positive rate and its extra flags are provably the reverted noise excursions the fixed horizon ignores — an inflation manufactured by the stopping rule, fixable with a method designed for repeated looks rather than by never looking.**

## Boss fight

Your team runs experiments on a platform that shows a live significance readout, and a well-meaning PM has a habit: launch a test, watch the dashboard, and ship the moment it goes green. Over a quarter they ship eleven "significant" wins, but the aggregate metric the experiments were supposed to move has not budged. An engineer proposes fixing this by raising the threshold from 0.05 to 0.01 so it is harder to hit green. Why will that not solve the problem, and what actually will?

Raising the threshold does not fix it because the disease is the stopping rule, not the threshold value. Peeking inflates the false-positive rate above whatever nominal level you set: a wandering statistic given many looks will eventually cross 0.01 too, just a bit less often, so a 0.01 threshold checked repeatedly still produces false positives well above 1%, and the PM still ships noise excursions that would have reverted. You would trade some false positives for less power and slower decisions without closing the hole. What actually works is aligning the analysis with the behavior: either commit to a fixed horizon (pre-register the sample size, and read significance only at the end) so the nominal guarantee holds, or — since the team clearly wants to monitor live — adopt a sequential method built for continuous looks, such as an alpha-spending group-sequential design or always-valid (anytime) p-values, which budget the total error across every look so that stopping at a crossing keeps the false-positive rate at the level you intended. The readout should be one that is correct to peek at, not a fixed-horizon p-value peeked at repeatedly.

## External resources

Evan Miller, "How Not to Run an A/B Test" — the widely cited practitioner explanation of the peeking problem, with an interactive demonstration of how repeated significance testing inflates the false-positive rate, matching the mechanism modeled here.

Johari, Koomen, Pekelis, and Walsh, "Always Valid Inference: Continuous Monitoring of A/B Tests" — the paper behind anytime-valid p-values and sequential testing, the principled fix for teams that need to monitor experiments continuously without paying the peeking penalty.
