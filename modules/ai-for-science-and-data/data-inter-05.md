---
id: data-inter-05
title: Survivorship bias — averaging over the survivors flips a loss into a gain
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 8-10h
summary: The dataset you can get is usually the survivors — funds still trading, models still deployed, users still active — because the failures dropped out and are missing, and computing a statistic over survivors is biased upward because survival was caused by the very outcome you are measuring. Across eight strategies, three blew up (returns below the survive threshold) and would be absent from a real dataset, so the survivor-only mean is a healthy plus 10.2 percent while the full-cohort mean, counting the failures at minus 20, minus 35, minus 15, is minus 2.38 percent — the sign flips from a gain to a loss purely from which rows you were allowed to see. The bias is 12.57 points, it exists because every failure underperformed every survivor, and the fix is to account for the dropouts, not to trust the sample that is conveniently in front of you.
eli5: If you only ask the runners who finished a race how hard it was, they will all say it was manageable — because the ones who collapsed and quit are not there to answer. Judging the race by the finishers makes it look easier than it was. The missing people are missing for a reason connected to exactly what you are trying to measure, so leaving them out does not just add noise, it tilts the answer.
---

## Why this module

You built real datasets, and the most dangerous thing about a real dataset is what is not in it. Entities that failed — funds that closed, experiments that were killed, users who churned, models that were rolled back — leave the dataset, and they leave for reasons tied to the exact outcome you are studying. Analyzing what remains, the survivors, gives a systematically wrong answer, and this module measures how wrong on a cohort where the bias is large enough to flip the conclusion from a gain to a loss. Survivorship bias is not a subtle statistical footnote; it is one of the most common ways a data analysis reaches a confidently false conclusion.

The reason it is not merely noise is that survival is endogenous. A survivor sample is not a smaller random sample of the population that you could correct by widening error bars — it is a filtered sample, and the filter is the outcome. Strategies survive because they performed well; the poor performers were shut down and removed. So the survivor average is systematically higher than the true average, by an amount that depends on how badly the failures did and how many there were. Here three of eight strategies blew up, and their returns — minus 20, minus 35, minus 15 — are exactly the rows a real dataset would be missing. Average the five survivors and you get plus 10.2 percent, a healthy return; average all eight and you get minus 2.38 percent, a loss. The sign flips, from the same period, purely from whether the failures were in the data.

You need no prior module, only the mean. Everything runs offline against a cohort fixture — eight strategies, three of which fail — stdlib Python 3, `$0.00`. Survival is derived from the returns, so survivorship is endogenous to the outcome exactly as in reality. The instinct to unlearn is that the data you have is a fair sample of the data you want. If the missing rows went missing for a reason related to what you are measuring, the sample in front of you is biased, not just small.

Here is the cohort, with the rows a real dataset would hide:

```
# modules/ai-for-science-and-data/code/data-inter-05/ — COMPLETE, run from that directory
$ python3 survivor.py --cohort

COHORT — every strategy (survive if return > -10%)
------------------------------------------------------------------
  s1   return= +12.0%  survived
  s2   return=  +8.0%  survived
  s3   return= +15.0%  survived
  s4   return=  +6.0%  survived
  s5   return= +10.0%  survived
  s6   return= -20.0%  FAILED (missing from real data)
  s7   return= -35.0%  FAILED (missing from real data)
  s8   return= -15.0%  FAILED (missing from real data)
```

run: 2026-08-26 · deterministic; returns are a fixture · 8 strategies · `python3 survivor.py --cohort`

Five survivors, all positive; three failures, all badly negative — and the failures are precisely what a survivor-only dataset omits. This module is what those three missing rows do to the average.

## Concepts

Named here so you can find them again; each is built below.

- **Survivorship bias** — a statistic computed over survivors, biased because failures are missing.
- **Endogenous selection** — survival is caused by the outcome, so the sample filter is not random.
- **Survivor-only sample** — the data you can actually get; the failures have already dropped out.
- **Full-cohort mean** — the true average, counting the entities that failed and left.
- **The bias** — the gap between the survivor mean and the full mean; systematic, not noise.
- **Sign flip** — when the bias is large enough to reverse the conclusion, here gain to loss.

## Worked example

Source: the survivorship bias that distorts fund-performance studies, backtests, and any longitudinal cohort (the WWII bomber-armor story and the mutual-fund graveyard are the classics); the returns here stand in for a real cohort so the bias and the sign flip are exact and checkable.

Script and fixture: `modules/ai-for-science-and-data/code/data-inter-05/` — `survivor.py`, and `funds.json`, eight strategies with returns and a survive threshold. Every command runs from there.

### Survival is caused by the outcome

The one line that makes this a bias rather than noise: whether a strategy survives is determined by its return.

```
# survivor.py:37-43 — COMPLETE (survival derived from the outcome; the mean)
def survived(strategy, threshold):
    """A strategy survives if it did not blow up: return above the threshold."""
    return strategy["return_pct"] > threshold


def mean_return(strategies):
    return sum(s["return_pct"] for s in strategies) / len(strategies)
```

`survived` reads the very quantity we are averaging. That is endogenous selection, and it is what separates survivorship bias from ordinary sampling error. If the failures dropped out for a reason unrelated to return — say, alphabetical — the survivors would still be a fair sample and the mean would be unbiased, just noisier. But they drop out because their return was bad, so removing them removes the low end of the distribution, and the average of what remains can only go up. The bias has a direction, and the direction is set by the selection rule.

### The two means

Compute the average two ways: over the survivors you would actually have, and over the full cohort.

```
# survivor.py:46-51 — COMPLETE (partition into survivors and failures)
def survivors(strategies, threshold):
    return [s for s in strategies if survived(s, threshold)]


def failures(strategies, threshold):
    return [s for s in strategies if not survived(s, threshold)]
```

The gap between the two means is the bias:

```
# $ python3 survivor.py --means
#   survivor-only mean = +10.20%  (n=5, the data you'd actually have)
#   full-cohort mean   =  -2.38%  (n=8, counting the failures)
#   survivorship bias  = +12.57 percentage points
```

run: 2026-08-26 · deterministic · `python3 survivor.py --means`

<svg viewBox="0 0 700 150" role="img" aria-label="Two bars against a zero line. Survivor-only mean is a positive bar reaching +10.2. Full-cohort mean is a negative bar reaching -2.38 below zero. An arrow spans the 12.57-point gap between them, crossing zero.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="18" fill="var(--muted)">mean return: survivors only vs full cohort (zero line = break even)</text>
    <line x1="60" y1="80" x2="650" y2="80" stroke="var(--grid)"></line>
    <text x="40" y="84" fill="var(--muted)" font-size="8">0</text>
    <rect x="150" y="42" width="140" height="38" fill="var(--s1)"></rect><text x="220" y="36" text-anchor="middle" fill="var(--s1)" font-size="9">survivors +10.2%</text>
    <rect x="400" y="80" width="140" height="16" fill="var(--s2)"></rect><text x="470" y="110" text-anchor="middle" fill="var(--s2)" font-size="9">full cohort -2.38%</text>
    <text x="330" y="128" text-anchor="middle" fill="var(--muted)" font-size="8">the 12.57-point gap crosses zero — profit becomes loss</text>
  </g>
</svg>
^ The survivor bar sits above the break-even line and the full-cohort bar below it. The gap between them is the survivorship bias, and here it straddles zero — the difference between reporting a winner and a loser.

The survivor-only mean is plus 10.2 percent — the number a naive analysis would report, and a compelling one. The full-cohort mean is minus 2.38 percent — the truth, that this set of strategies lost money on average. The bias is 12.57 percentage points, and critically it crosses zero: survivors look profitable, the cohort actually lost. A backtest that only included strategies still running at the end of the period, or a fund study that dropped the closed funds, would confidently report a profitable strategy that in reality lost money.

<svg viewBox="0 0 700 190" role="img" aria-label="Eight strategy returns on a vertical axis around a zero line. Five survivors are positive bars (6 to 15). Three failures are negative bars (-15, -20, -35), drawn faded as 'missing'. A dashed line at +10.2 marks the survivor mean, well above zero; a dashed line at -2.4 marks the full mean, below zero.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">strategy returns; the survivor mean sits above zero, the full mean below</text>
    <line x1="40" y1="100" x2="660" y2="100" stroke="var(--grid)"></line>
    <text x="30" y="104" fill="var(--muted)">0</text>
    <g fill="var(--s1)"><rect x="70" y="64" width="30" height="36"></rect><rect x="115" y="76" width="30" height="24"></rect><rect x="160" y="55" width="30" height="45"></rect><rect x="205" y="82" width="30" height="18"></rect><rect x="250" y="70" width="30" height="30"></rect></g>
    <g fill="var(--s2)" opacity="0.4"><rect x="340" y="100" width="30" height="60"></rect><rect x="385" y="100" width="30" height="105"></rect><rect x="430" y="100" width="30" height="45"></rect></g>
    <text x="180" y="175" fill="var(--s1)" font-size="8">survivors (kept)</text>
    <text x="360" y="175" fill="var(--s2)" font-size="8">failures (missing from data)</text>
    <line x1="40" y1="70" x2="300" y2="70" stroke="var(--s1)" stroke-dasharray="3 3"></line><text x="300" y="68" fill="var(--s1)" font-size="8">survivor mean +10.2</text>
    <line x1="40" y1="108" x2="500" y2="108" stroke="var(--s2)" stroke-dasharray="3 3"></line><text x="500" y="120" fill="var(--s2)" font-size="8">full mean -2.4</text>
  </g>
</svg>
^ The survivors are all above zero and the failures, faded here, are what a real dataset drops. Cover the faded bars and the mean jumps from below zero to well above it — the entire bias is the missing rows.

**Survivorship bias is systematic, not noise, because survival is caused by the outcome being measured: dropping the failures removes the low end of the distribution, so the survivor mean overstates the truth — here enough to flip a 2.4 percent loss into an apparent 10.2 percent gain.**

### The self-test

The `--check` mode asserts the bias and its cause: the survivor mean overstates the full mean, every failure underperformed every survivor, the gap is large, and it flips the sign.

```
# $ python3 survivor.py --check
#   survivor-only mean exceeds the full-cohort mean = True (+10.20 > -2.38)
#   every failure underperformed every survivor = True (best fail -15.0 < worst surv +6.0)
#   the survivorship bias is substantial = True (+12.57 points)
#   the bias flips the conclusion (survivors profit, cohort loses) = True
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 survivor.py --check`

The causal core is three lines — the failures underperform every survivor, which is why removing them lifts the mean:

```
# survivor.py:93-95 — COMPLETE (every failure is worse than every survivor)
    worst_survivor = min(s["return_pct"] for s in surv)
    best_failure = max(s["return_pct"] for s in fail)
    failures_worse = best_failure < worst_survivor
```

And the sign flip makes the bias a wrong conclusion, not a small one:

```
# survivor.py:99-104 — COMPLETE (the bias is large and reverses the sign)
    bias = ms - mf
    big_bias = bias > 5.0

    sign_flip = ms > 0 and mf < 0
```

The `failures_worse` line is the causal anchor: it verifies that every failure had a lower return than every survivor, which is why removing them raises the mean — the bias is not a coincidence of these numbers but a consequence of the selection rule. The `sign_flip` line makes the stakes concrete: the bias is large enough that the survivor sample and the full cohort disagree not just in magnitude but in direction, so the conclusion itself is wrong, not merely imprecise.

### The running tally

| sample | n | mean return | conclusion |
|---|---|---|---|
| survivors only | 5 | +10.20% | a profitable strategy |
| full cohort | 8 | −2.38% | a losing strategy |
| the three failures | 3 | −23.33% | why the bias exists |

<svg viewBox="0 0 700 140" role="img" aria-label="A funnel showing how the population becomes the sample. Left: full cohort of 8 strategies, mean -2.38. A filter labelled 'survive: return > -10%' drops the 3 failures. Right: survivor sample of 5, mean +10.2. The dropped failures, mean -23.3, fall out the bottom.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the filter that makes the sample: survival removes the worst rows</text>
    <rect x="40" y="50" width="150" height="40" rx="4" fill="var(--panel)" stroke="var(--line)"></rect><text x="115" y="68" text-anchor="middle" fill="var(--ink)" font-size="8">full cohort n=8</text><text x="115" y="82" text-anchor="middle" fill="var(--s2)" font-size="8">mean -2.38%</text>
    <path d="M 190 70 L 300 70" stroke="var(--muted)"></path><text x="245" y="62" text-anchor="middle" fill="var(--muted)" font-size="7">survive &gt; -10%</text>
    <rect x="300" y="50" width="150" height="40" rx="4" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="375" y="68" text-anchor="middle" fill="var(--acc-ink)" font-size="8">survivors n=5</text><text x="375" y="82" text-anchor="middle" fill="var(--s1)" font-size="8">mean +10.2%</text>
    <path d="M 245 88 L 245 115" stroke="var(--s2)"></path>
    <rect x="170" y="115" width="150" height="22" rx="4" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"></rect><text x="245" y="130" text-anchor="middle" fill="var(--s2)" font-size="8">3 failures dropped, mean -23.3%</text>
  </g>
</svg>
^ The survive filter routes the three worst strategies out the bottom, so the sample that reaches your analysis is the top five. The mean rises from below zero to +10.2 not by any change in the strategies, only by which ones the filter kept.

The first two rows are the same strategies, and they reach opposite conclusions. The third row is the mechanism: the failures averaged minus 23 percent, and excluding them is what lifted the survivor mean 12.57 points into positive territory. Survivorship bias is exactly this — the gap between the sample you can conveniently collect and the population you actually care about, opened by a filter that is tied to your outcome. The fix is never a bigger survivor sample; it is finding the failures, or reasoning about them, before you trust the average.

### What we did not settle

Survivorship is one face of selection bias, and the family is large. The dropouts are not always fully gone — sometimes they leave partial data, and how you handle that missing data (dropping it repeats the bias; imputing it makes assumptions) is its own discipline. Selection can be subtler than survival: any sampling process correlated with the outcome biases the result, including self-selection into a study and non-response. The correction depends on the mechanism — sometimes you can reconstruct the failures (fund graveyards, deleted-account logs), sometimes you must model the dropout process, sometimes you can only bound the bias. And the direction is not always up: select on a variable negatively correlated with the outcome and the bias flips down. The rule here — the missing rows went missing for a reason, so account for them — is the floor beneath all of it.

## Build

The practice in one paragraph: before trusting any cohort statistic, ask what could have dropped out of the dataset and whether it dropped out for a reason tied to your outcome; if so, find the failures — the graveyard of closed funds, the churned users, the killed experiments — and include them, or at minimum bound how much they could move your number; never treat a survivor sample as merely a smaller version of the population; and report the dropout rate alongside any longitudinal result. The data you can easily collect is the data that survived, which is exactly the data that lies.

We opened on the cohort. The number that proves the sample lies is the bias between the two means:

```
# modules/ai-for-science-and-data/code/data-inter-05/ — COMPLETE, run from that directory
$ python3 survivor.py --means
  survivor-only mean = +10.20%
  full-cohort mean   =  -2.38%
```

Now do it to your own data. Take a longitudinal dataset — user retention, model versions, experiment outcomes — identify what dropped out, and compute your statistic over survivors only versus the full cohort including the dropouts. Your number to beat is not the survivor statistic; it is **the survivorship bias, the gap between the survivor and full-cohort values**, and whether it is large enough to change your conclusion. Reconstruct or estimate the failures. Bring back both values and the bias. Good luck.

## Definition of done

- [ ] A longitudinal cohort where some entities dropped out for an outcome-related reason
- [ ] Survival derived from the outcome, making the selection endogenous
- [ ] The statistic computed over survivors only and over the full cohort
- [ ] The survivorship bias (the gap) reported, with its direction
- [ ] Confirmation the failures underperformed the survivors, explaining the bias
- [ ] A check of whether the bias is large enough to change the conclusion
- [ ] `python3 survivor.py --check` printing SELF-TEST PASS: overstates, failures-worse, big-bias, sign-flip
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why is survivorship bias systematic rather than random noise that a larger sample would fix?
2. What does "endogenous selection" mean here, and which line of code makes the selection endogenous?
3. The survivor mean was +10.2% and the full mean −2.4%. Explain where the 12.57-point gap comes from.
4. Why can you not fix survivorship bias by collecting more survivors, and what must you do instead?
5. Your own cohort was analyzed both ways. What was the survivorship bias, and did it change your conclusion?

## External resources

- Wald / Mangel & Samaniego on the WWII bomber-armor problem — my summary: the origin story of survivorship bias, where armoring the planes' undamaged areas was correct because the damaged-there planes never returned; read it for the clearest intuition of why the missing data is the point.
- Elton, Gruber & Blake, *Survivorship Bias and Mutual Fund Performance* (1996) — my summary: the empirical measurement of how excluding dead funds overstates industry returns; read it for the real-world magnitude of the bias this module reproduces.
- This hub, *data-inter-03* — modules/ai-for-science-and-data/data-inter-03.md — my summary: the base-rate module, another case where the sample or population you condition on decides whether a statistic tells the truth; read it for the shared lesson — a number is only as honest as the population behind it.
