---
id: gambler-inter-01
title: After a run of heads, tails is not "due" — an independent coin has no memory, and long runs are expected, not omens
topic: ai-for-science-and-data
level: intermediate
status: ready
time: 16 min
summary: Watch a fair coin come up heads four times and something insists the next is more likely to be tails — the coin is "due" to balance. That is the gambler's fallacy, and it is wrong for a precise reason: the coin has no memory. Each flip is independent, so the probability of heads on the next flip is exactly what it always was, regardless of the previous flips. P(heads | four heads in a row) equals P(heads). The pull toward "tails is due" confuses two true facts — that long runs are rare to start, and that the long-run average is 50/50 — into a false one: that the coin corrects as it goes. The second half of the fallacy is treating a run as surprising: a run of k has probability only p^k from a given point, but across a long sequence there are many starting points, so at least one long run is expected. Crucially the fallacy is about independence: when a process genuinely has memory — a Markov coin, an autocorrelated series — conditioning on the recent past is correct inference, not a fallacy. On a fixture, the fair coin's P(heads | run of k) stays 0.500 for every run length while a "sticky" coin whose next flip copies the last with probability 0.8 sits at 0.800, and a run of 3 heads appears in about 80% of 20-flip sequences.
eli5: A coin doesn't remember what it just did. Flip four heads and the coin isn't "keeping score" and planning to even things out — the next flip is still 50/50, exactly like the first. And streaks aren't spooky: flip a coin twenty times and you'll almost always see three-in-a-row somewhere, just by chance. Feeling that a streak means tails is "owed," or that a streak proves the coin is rigged, are the same mistake — both imagine the independent flips are secretly working together. They're not, unless the thing you're flipping actually has a memory.
---

## Why this module

A probability is a property of the next event given the process, and for an independent process the next event does not know or care what came before — so any belief that a run changes the odds is a belief that the events are coordinated when, by construction, they are not.

The gambler's fallacy is the intuition that a streak creates a debt: four heads in a row, and tails is now "due" to restore balance. It is wrong because independence means exactly that the flips do not influence each other. The probability of heads on the next flip is a fixed property of the coin, and conditioning on the past — "given the last four were heads" — does not change it, because the past flips contribute no information about a memoryless future. Formally, P(heads and four prior heads) = p·p⁴ and P(four prior heads) = p⁴, so the conditional P(heads | four heads) = p⁴·p / p⁴ = p, the unconditioned probability, unchanged. The feeling of a pull toward tails comes from smuggling in a law that does not exist: the coin does not remember its balance and steer toward 50/50. The long-run average does approach 50/50, but not because past excess is corrected — because it is *diluted* by an ever-growing number of fresh, independent flips.

**For independent trials the conditional probability of the next outcome given any run of prior outcomes equals the unconditional probability — the process has no memory, so a streak creates no "debt" and the next flip is not "due" to reverse.**

The fallacy has a mirror image that is just as common: reading a streak as evidence that something is wrong. A run of k heads has probability only pᵏ counted from a single starting point, so a long run *looks* rare — but a sequence has many starting points, and across all of them at least one long run becomes likely, even expected. In twenty fair flips, a run of three heads shows up about eighty percent of the time and a run of four nearly half. So the instinct "five heads running, the coin must be biased" is as mistaken as "tails is due" — both treat independent events as if coordinated. And here is the pivot that makes this a data lesson and not a casino anecdote: the fallacy is specifically about *independence*. When a process genuinely has memory — an autocorrelated time series, a system with momentum, a Markov chain — the recent past really does inform the next value, and conditioning on it is correct inference, not a fallacy. This module computes the conditional for a memoryless coin and a coin with memory and shows exactly where the fallacy lives.

## Concepts

**Independence means memorylessness.** The conditional probability of the next flip given any history equals the unconditional probability, because the prior flips carry no information about the next one.

```python filename=modules/ai-for-science-and-data/code/gambler-inter-01/gambler.py:44-56 COMPLETE
def conditional_independent(p, k):
    """P(next heads | first k flips all heads) for an independent coin, computed by enumerating weighted sequences."""
    joint_runH = 0.0   # P(first k heads AND next heads)
    marg_runH = 0.0    # P(first k heads)
    for seq in product([1, 0], repeat=k + 1):
        pr = 1.0
        for flip in seq:
            pr *= p if flip == 1 else (1 - p)
        if all(seq[i] == 1 for i in range(k)):      # first k are heads
            marg_runH += pr
            if seq[k] == 1:                          # and the next is heads
                joint_runH += pr
    return joint_runH / marg_runH
```

**A run has probability pᵏ from a fixed start, but is common across a sequence.** Long runs look rare pointwise yet are expected somewhere, because a sequence offers many chances for one to occur.

**The fallacy is about independence, not streaks.** For a process with memory, conditioning on the recent past is correct — so the error is assuming independence (no memory) when reasoning about the next event.

<svg role="img" aria-label="As the run of heads grows from 1 to 4, the independent conditional stays flat at 0.5 while the gambler imagines it declining toward tails" viewBox="0 0 300 100" width="300" height="100">
  <line x1="30" y1="82" x2="290" y2="82" stroke="var(--grid)"/><line x1="30" y1="14" x2="30" y2="82" stroke="var(--grid)"/>
  <text x="2" y="20" fill="var(--muted)" font-size="7">P(H|run)</text><text x="235" y="96" fill="var(--muted)" font-size="7">run length →</text>
  <line x1="30" y1="48" x2="290" y2="48" stroke="var(--s1)" stroke-width="1.5"/>
  <g fill="var(--s1)"><circle cx="60" cy="48" r="2.5"/><circle cx="120" cy="48" r="2.5"/><circle cx="180" cy="48" r="2.5"/><circle cx="240" cy="48" r="2.5"/></g>
  <text x="150" y="42" fill="var(--s1)" font-size="7">independent: stays 0.5 (reality)</text>
  <path d="M60 48 L120 58 L180 68 L240 76" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"/>
  <text x="150" y="78" fill="var(--s2)" font-size="7">gambler imagines: tails 'due'</text>
  <text x="30" y="97" fill="var(--muted)" font-size="8">the conditional does not move; the belief that it drops is the fallacy</text>
</svg>
^ The independent conditional P(heads | run of k) is a flat line at 0.5; the gambler's fallacy is the imagined declining curve, the false belief that a longer run of heads makes the next flip less likely to be heads.

**A streak does not change the odds of the next independent event and long runs are expected by chance — so treating a run as a debt to be repaid, or as proof of bias, both mistake independent events for coordinated ones.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ai-for-science-and-data/code/gambler-inter-01/gambler.py

The fixture is a fair independent coin, a run length to condition on, and a "sticky" coin whose next flip copies the last with probability 0.8.

```json filename=modules/ai-for-science-and-data/code/gambler-inter-01/gambler.json:3-6 COMPLETE
  "fair_p": 0.5,
  "run_length": 4,
  "sequence_length": 20,
  "sticky_p_heads_after_heads": 0.8
```

Run `--conditional` to compute the next-flip probability after a run, for both coins.

```text filename=--conditional
CONDITIONAL — P(next heads | a run of k heads): independent coin vs sticky coin
----------------------------------------------------------------------
  run k    independent (fair 0.50)    sticky (P(H|H)=0.80)
  1        0.500                     0.800
  2        0.500                     0.800
  3        0.500                     0.800
  4        0.500                     0.800
```

The independent column is flat: after one head, or four heads, the probability of the next head is 0.500 — the enumeration over all weighted sequences confirms the algebra, P(heads | any run) = p. There is no downward drift toward tails; the coin is not "due" for anything. The sticky column is also flat, but at 0.800, not 0.500. That is the crucial contrast. The sticky coin has memory — its next flip depends on the last — so conditioning on a run of heads genuinely changes the next-flip probability, from its 50/50 long-run rate up to 0.8. For the sticky coin, "the last flip was heads, so the next is probably heads too" is *correct*, because the process really is autocorrelated. So the identical observation — a run of heads — licenses opposite conclusions depending on the process: for the independent coin it tells you nothing about the next flip, and for the sticky coin it tells you a lot. The gambler's fallacy is not "conditioning on the past is wrong"; it is "conditioning on the past when the process is memoryless," and the fix is to know which process you have.

<svg role="img" aria-label="The independent coin's conditional is a flat line at 0.5 for all run lengths; the sticky coin's is a flat line at 0.8" viewBox="0 0 300 100" width="300" height="100">
  <line x1="30" y1="84" x2="290" y2="84" stroke="var(--grid)"/><line x1="30" y1="14" x2="30" y2="84" stroke="var(--grid)"/>
  <text x="2" y="20" fill="var(--muted)" font-size="7">P(H|run)</text>
  <line x1="30" y1="30" x2="290" y2="30" stroke="var(--s2)" stroke-width="1.5"/><text x="150" y="26" fill="var(--s2)" font-size="7">sticky (memory): 0.8</text>
  <line x1="30" y1="57" x2="290" y2="57" stroke="var(--s1)" stroke-width="1.5"/><text x="150" y="53" fill="var(--s1)" font-size="7">independent: 0.5</text>
  <g fill="var(--s1)"><circle cx="70" cy="57" r="2.5"/><circle cx="140" cy="57" r="2.5"/><circle cx="210" cy="57" r="2.5"/><circle cx="270" cy="57" r="2.5"/></g>
  <g fill="var(--s2)"><circle cx="70" cy="30" r="2.5"/><circle cx="140" cy="30" r="2.5"/><circle cx="210" cy="30" r="2.5"/><circle cx="270" cy="30" r="2.5"/></g>
  <text x="30" y="98" fill="var(--muted)" font-size="8">both flat, but the memory coin sits above its 50/50 rate — history informs it, the fair coin's does not</text>
</svg>
^ The independent conditional is flat at 0.5 (a run tells you nothing) and the sticky conditional is flat at 0.8 (well above its 50/50 long-run rate, so a run is informative) — the difference is whether the process has memory.

## Build

Now the other half: is a streak itself surprising? Run `--streaks`.

```text filename=--streaks
STREAKS — how likely a run of k heads is by chance in 20 fair flips
----------------------------------------------------------
  run k    P(a single run of k)   P(>=1 run of k in 20 flips)
  2        0.2500                 0.983
  3        0.1250                 0.787
  4        0.0625                 0.478
  5        0.0312                 0.250
```

The middle column is the pointwise probability, pᵏ: a run of five heads from a specific starting flip is only 0.0312, genuinely rare. The right column is the probability that *at least one* such run appears somewhere in twenty flips, computed by a dynamic program over the running head-count, and it tells a completely different story. A run of three appears in 78.7% of twenty-flip sequences — it is the norm, not the exception. A run of four appears nearly half the time. Even a run of five, "rare" pointwise at 0.0312, shows up in a quarter of sequences. The gap between the two columns is the whole misconception: a streak feels rare because we compute its pointwise probability, but we *observe* it against all the starting points in a sequence, where it is common. So "I saw five heads in a row, the coin must be loaded" commits the mirror fallacy — using an expected fluctuation as evidence of bias. To actually detect bias you need enough data to distinguish the coin's rate from 0.5 with statistical confidence; a single streak, however striking, is exactly the kind of pattern chance produces all the time. Randomness looks streaky, and a mind that expects randomness to look uniform reads its normal clumps as signals.

```python filename=modules/ai-for-science-and-data/code/gambler-inter-01/gambler.py:69-84 COMPLETE
def prob_at_least_one_run(n, k, p):
    """P(at least one run of >= k heads somewhere in n flips), by DP over the current consecutive-heads count."""
    # state[c] = P(after i flips, current head-run = c, and no run of k yet)
    state = [0.0] * k
    state[0] = 1.0
    absorbed = 0.0   # probability mass that has hit a run of k
    for _ in range(n):
        nxt = [0.0] * k
        for c in range(k):
            nxt[0] += state[c] * (1 - p)             # tails resets the run
            if c + 1 < k:
                nxt[c + 1] += state[c] * p           # heads extends the run
            else:
                absorbed += state[c] * p             # heads completes a run of k
        state = nxt
    return absorbed
```

<svg role="img" aria-label="The probability of at least one run of k heads in 20 flips falls from 0.98 at k=2 to 0.25 at k=5, staying high for short runs" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">P(≥1 run of k heads in 20 flips)</text>
  <line x1="30" y1="78" x2="290" y2="78" stroke="var(--grid)"/>
  <line x1="30" y1="30" x2="290" y2="30" stroke="var(--ink)" stroke-dasharray="2 2"/><text x="250" y="28" fill="var(--muted)" font-size="7">50%</text>
  <rect x="50" y="18" width="30" height="60" fill="var(--s1)"/><text x="58" y="90" fill="var(--muted)" font-size="7">k2 .98</text>
  <rect x="110" y="30" width="30" height="48" fill="var(--s1)"/><text x="116" y="90" fill="var(--muted)" font-size="7">k3 .79</text>
  <rect x="170" y="49" width="30" height="29" fill="var(--s2)"/><text x="176" y="90" fill="var(--muted)" font-size="7">k4 .48</text>
  <rect x="230" y="63" width="30" height="15" fill="var(--s2)"/><text x="236" y="90" fill="var(--muted)" font-size="7">k5 .25</text>
  <text x="6" y="96" fill="var(--muted)" font-size="7">short and medium runs are more likely than not — a streak is expected, not evidence</text>
</svg>
^ In twenty flips a run of three (0.79) or even four (0.48) is common, above or near even odds — so a streak is an expected fluctuation, and reading it as bias or as a debt is the fallacy from either side.

## Definition of done

The self-test pins both halves and the pivot: the independent conditional never moves off p, a run of k has probability pᵏ, a run of three is more likely than not in twenty flips, and a coin with memory changes the conditional.

```python filename=modules/ai-for-science-and-data/code/gambler-inter-01/gambler.py:116-126 COMPLETE
    independent_constant = all(abs(conditional_independent(p, k) - p) < 1e-9 for k in range(1, K + 1))
    print("  independent P(heads | run of k) equals p for every k = %s (%.3f)" % (independent_constant, conditional_independent(p, K)))

    not_due = abs(conditional_independent(p, K) - p) < 1e-9
    print("  after %d heads, heads is NOT less likely (no 'due') = %s (%.3f, not < %.3f)" % (K, not_due, conditional_independent(p, K), p))

    run_is_p_to_k = abs(run_probability(p, K) - p ** K) < 1e-12
    print("  a run of %d heads has probability p^%d = %s (%.4f)" % (K, K, run_is_p_to_k, run_probability(p, K)))

    long_runs_expected = prob_at_least_one_run(n, 3, p) > 0.5
    print("  a run of 3 in %d flips is more likely than not = %s (%.3f)" % (n, long_runs_expected, prob_at_least_one_run(n, 3, p)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the independent conditional never moves; a run of k has prob p^k; the sticky coin's history matters
----------------------------------------------------------------------------------------------------------------
  independent P(heads | run of k) equals p for every k = True (0.500)
  after 4 heads, heads is NOT less likely (no 'due') = True (0.500, not < 0.500)
  a run of 4 heads has probability p^4 = True (0.0625)
  a run of 3 in 20 flips is more likely than not = True (0.787)
  a coin WITH memory changes the conditional (so the fallacy is about independence) = True (0.800 vs 0.500)
```

**Done means the fallacy and its boundary are both proven: for the independent coin P(heads | a run of k heads) equals 0.500 for every run length (no "due"), a run of k has probability pᵏ (0.0625 for four heads) yet a run of three appears in 78.7% of twenty-flip sequences (long runs are expected) — while the sticky coin's conditional is 0.800, far from its 0.500 long-run rate, so history informs the next flip exactly when the process has memory.**

## Boss fight

Predict the two ways the "it's just independent" answer itself misleads. It is tempting to conclude that streaks never carry information.

The first trap is that real-world sequences are far more often dependent than the fair coin suggests, so dismissing every streak as chance is its own error. Stock returns, weather, disease outbreaks, queue lengths, and human performance are usually autocorrelated to some degree — the recent past does shift the odds — so conditioning on a run can be correct inference, as it was for the sticky coin. The discipline is not "ignore streaks" but "test for independence before you assume it." If the process has memory, the gambler's fallacy is not even in play; refusing to update on the recent past would then be the mistake, throwing away real predictive signal. So the two failures are symmetric: assume independence in a process with memory and you ignore real information; assume dependence in a memoryless process and you invent a pattern. The question is always empirical — does the next value's distribution actually depend on the last? — and the fair coin is only the special case where the answer is no.

```python filename=modules/ai-for-science-and-data/code/gambler-inter-01/gambler.py:59-61 COMPLETE
def conditional_sticky(p_hh, k):
    """P(next heads | a run of heads) for a Markov 'sticky' coin: depends only on the last flip, so it is p_hh."""
    return p_hh
```

The second trap is the "hot hand" and its debunking, which is subtler than either side first claimed. The hot-hand fallacy is the belief that a player who just made several shots is more likely to make the next — often dismissed as the gambler's fallacy in reverse (a streak means nothing for independent shots). But two twists complicate it. First, shooting may genuinely not be independent: confidence, defense, and fatigue create real dependence, so a hot hand can exist and treating shots as independent coin flips would then be the error. Second, and famously, the naive way to *test* for a hot hand — take all shots following a streak of makes and compute their success rate — has a selection bias (the finite-sequence version of the same streak counting), which understates the rate, so early studies that "found no hot hand" were partly measuring an artifact. The lesson layered on the fallacy is that detecting dependence is statistically delicate: the same combinatorics that make streaks common by chance also bias the estimators you use to check whether streaks are more than chance. So "is this streak meaningful?" is not answered by intuition on either side; it needs a model of the process and an estimator that accounts for how streaks are selected — the independence assumption is a hypothesis to test with care, not a default to assert or deny.

**For independent trials a run changes nothing about the next outcome (P(next | run) = p) and long runs are expected by chance, so treating a streak as a debt to be repaid or as proof of bias both wrongly assume the events are coordinated — but the fallacy is specifically about independence, so before applying it, test whether the process actually has memory (autocorrelated series, momentum, and Markov processes genuinely make the past informative), and be aware that detecting dependence is delicate, because the same combinatorics that make streaks common also bias the naive estimators used to check for them (the hot-hand selection bias).**

## External resources

Any probability text's treatment of independence, conditional probability, and the gambler's fallacy — the derivation that P(next | history) = p for independent trials and the distinction from the law of large numbers (dilution, not correction).

Miller and Sanjurjo's work on the hot-hand fallacy and streak-selection bias, and any reference on testing for autocorrelation / Markov dependence — how to check whether a sequence actually has memory and why the naive streak-conditioned estimator is biased.

The companion "switching wins Monty Hall 2/3 of the time" and "a 99% detector that is mostly wrong when it fires" (base-rate) modules — all three are conditional-probability pitfalls where intuition diverges from the correct conditioning, here specifically the conditioning on a history that a memoryless process makes irrelevant.
