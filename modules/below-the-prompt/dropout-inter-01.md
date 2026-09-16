---
id: dropout-inter-01
title: Rescale after dropping units — or training's expected activation won't match test's and every value shifts
topic: below-the-prompt
level: intermediate
status: ready
time: 19 min
summary: Dropout regularizes by randomly zeroing a fraction of units on each training step, so no unit can rely on any other. The catch is arithmetic. During training with keep probability p, only about a fraction p of the units are active, so the sum they feed downstream is on average p times the all-units-on value. At test time there is no dropout — every unit is active — so the layer produces the full sum. Train on p-scale activations and test on full-scale ones and every downstream value is off by 1/p: the network was tuned for inputs of one size and handed inputs of another. Inverted dropout fixes it by dividing the survivors by p during training, lifting the expected sum back to the full value so test matches. On four units summing to 10 with keep 0.5, the expected training sum without rescaling is 5.0 (half the test-time 10.0); with inverted dropout it is 10.0, matching test exactly.
eli5: If you practice a song with half the band randomly sitting out each time, your practice sounds quiet — half as loud as the full band. On concert night everyone plays, so it's suddenly twice as loud as you rehearsed, and it sounds wrong. The fix is to have the players who are in each rehearsal play twice as loud, so practice matches the full-band concert volume all along.
---

## Why this module

Dropout changes how loud a layer is, and if training and test disagree on that loudness, the whole network is tuned for the wrong scale.

Dropout is a regularizer: on each training step it randomly zeroes a fraction of the units, forcing the network to spread its bets across many units rather than leaning on any one. That much is the point and it works. The trap is the bookkeeping it introduces. When you keep each unit with probability p, only about a fraction p of them are active on a given step, so the total they pass downstream is, on average, p times what it would be with every unit on. At test time you turn dropout off — all units fire — and the same layer now outputs the full total, roughly 1/p times larger than what training saw. The downstream weights were fit to the small training-time activations and are suddenly fed large test-time ones, so the network silently operates at the wrong scale.

**Dropping units lowers a layer's expected output by the keep fraction during training, but test uses all units, so without a correction the two run at different scales.**

Inverted dropout removes the mismatch: after zeroing the dropped units in training, divide the survivors by p, which restores the expected output to the full-units value. Then test — all units, no scaling — matches training in expectation. This module computes the exact expected activation both ways by enumerating every dropout mask, and shows which one lines up with test.

## Concepts

The **keep probability** p is the chance each unit survives a dropout step; 1 − p is dropped. The **layer output** here is the sum of the active units' values.

The **test-time output** uses all units with no dropout: the full sum. This is the target — training's expected output should match it.

**Expected training output without rescaling** is p times the full sum, because each unit contributes its value only the fraction p of steps it survives. With p = 0.5 that is half the full sum — a 2× mismatch against test.

**Inverted dropout** multiplies the surviving units by 1/p during training. Each survivor now contributes value/p when present (probability p), so its expected contribution is value again, and the expected training output equals the full sum — matching test. The alternative, scaling *down* by p at test, gives the same expectation but changes test-time code; inverted dropout keeps test identical to a no-dropout network, which is why it is standard.

Because the unit population here is tiny, the expectation is not sampled — every dropout mask is enumerated and weighted by its probability, so the numbers are exact, not noisy estimates.

**Dropout must be expectation-preserving: whatever fraction you drop, you scale the survivors so the layer's expected output is unchanged between training and test.**

The two corrections cancel exactly: dropping half the units multiplies the output by p, and boosting the survivors by 1/p multiplies it back, leaving the expected output where it started.

<svg role="img" aria-label="Full output times p from dropping units, times 1 over p from boosting survivors, returns to the full output" viewBox="0 0 300 90" width="300" height="90">
  <rect x="15" y="30" width="55" height="24" fill="var(--s2)"/><text x="24" y="46" fill="var(--panel)" font-size="8">full 10</text>
  <text x="76" y="46" fill="var(--muted)" font-size="9">× p</text>
  <rect x="98" y="30" width="30" height="24" fill="var(--s1)"/><text x="104" y="46" fill="var(--panel)" font-size="8">5</text>
  <text x="132" y="46" fill="var(--muted)" font-size="9">× 1/p</text>
  <rect x="165" y="30" width="55" height="24" fill="var(--s2)"/><text x="174" y="46" fill="var(--panel)" font-size="8">full 10</text>
  <text x="228" y="46" fill="var(--muted)" font-size="8">= matches test</text>
  <text x="15" y="76" fill="var(--muted)" font-size="8">drop halves it, the survivor boost doubles it back — expectation preserved</text>
</svg>
^ Dropping units scales the expected output down by p and the inverted-dropout boost scales it back up by 1/p, so the product is the original full output that test also produces.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/dropout-inter-01/dropout.py

The fixture is four units summing to 10 and a keep probability of 0.5.

```json filename=modules/below-the-prompt/code/dropout-inter-01/dropout.json:1-5 COMPLETE
{
  "_meta": "A layer of units, each with an activation value, feeding a sum downstream. During training, dropout keeps each unit with probability keep_prob and zeros it otherwise. At test time all units are active. Because the population of units is small, we enumerate EVERY dropout mask and weight it by its probability to compute the EXACT expected activation -- no sampling. The question: does the expected activation during training match the full activation at test, and what does forgetting to rescale do?",
  "units": [1, 2, 3, 4],
  "keep_prob": 0.5
}
```

The expected training sum is the probability-weighted sum over all masks; the invert flag divides survivors by p. Test is just the full sum.

```python filename=modules/below-the-prompt/code/dropout-inter-01/dropout.py:42-61 COMPLETE
def mask_prob(mask, p):
    """Probability of a dropout mask: p for each kept unit, (1-p) for each dropped one."""
    prob = 1.0
    for bit in mask:
        prob *= p if bit else (1 - p)
    return prob


def expected_sum(units, p, invert):
    """Exact expected training sum over all masks; invert=True divides survivors by p (inverted dropout)."""
    scale = (1.0 / p) if invert else 1.0
    total = 0.0
    for mask in itertools.product([0, 1], repeat=len(units)):
        kept = sum(u * scale for u, bit in zip(units, mask) if bit)
        total += mask_prob(mask, p) * kept
    return total


def test_sum(units):
    """Test time: no dropout, every unit active, no scaling."""
```

The expect view computes both training expectations and the test sum from the same units.

```python filename=modules/below-the-prompt/code/dropout-inter-01/dropout.py:68-75 COMPLETE
    units, p = data["units"], data["keep_prob"]
    print("EXPECT — expected training sum vs test sum (units %s, keep %.1f)" % (units, p))
    print("-" * 62)
    print("  test time (all units on):      %.1f" % test_sum(units))
    print("  train, no rescale:             %.1f   (x%.1f of test)" % (expected_sum(units, p, False), expected_sum(units, p, False) / test_sum(units)))
    print("  train, inverted dropout (/p):  %.1f   (matches test)" % expected_sum(units, p, True))
    print("-" * 62)
    print("  without rescaling, training runs at %.0f%% of test-time scale." % (100 * expected_sum(units, p, False) / test_sum(units)))
```

Run `--expect` for the three activations.

```text filename=--expect
EXPECT — expected training sum vs test sum (units [1, 2, 3, 4], keep 0.5)
--------------------------------------------------------------
  test time (all units on):      10.0
  train, no rescale:             5.0   (x0.5 of test)
  train, inverted dropout (/p):  10.0   (matches test)
--------------------------------------------------------------
  without rescaling, training runs at 50% of test-time scale.
```

Test time produces 10.0. Training without rescaling averages 5.0 — exactly half, the factor p = 0.5. So the network trains on activations half the size of what it will see at test, and the downstream weights bake in that half-scale. Inverted dropout averages 10.0, matching test: the ×2 boost to the survivors exactly cancels the halving from dropping half the units.

<svg role="img" aria-label="Test activation 10, no-rescale training 5 (half), inverted-dropout training 10 (matches test)" viewBox="0 0 300 110" width="300" height="110">
  <line x1="80" y1="12" x2="80" y2="80" stroke="var(--grid)" stroke-width="1"/>
  <line x1="80" y1="80" x2="285" y2="80" stroke="var(--grid)" stroke-width="1"/>
  <line x1="260" y1="12" x2="260" y2="80" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 2"/>
  <text x="228" y="22" fill="var(--ink)" font-size="7">test 10</text>
  <rect x="80" y="20" width="180" height="14" fill="var(--s2)"/><text x="150" y="31" fill="var(--panel)" font-size="8">inverted 10 (matches)</text>
  <rect x="80" y="42" width="90" height="14" fill="var(--s1)"/><text x="174" y="53" fill="var(--muted)" font-size="8">no rescale 5 (half)</text>
  <text x="80" y="98" fill="var(--muted)" font-size="8">no-rescale training sits at half the test scale; inverted dropout lands on it</text>
</svg>
^ The no-rescale training bar reaches only half the test line while the inverted-dropout bar lands exactly on it — the ×2 survivor boost undoing the halving.

## Build

Confirm the expectation is exact, not sampled, with `--masks`.

```text filename=--masks
MASKS — a few of the 16 dropout masks and their weighted contribution (no rescale)
--------------------------------------------------------------
  mask (0, 0, 0, 0)  keeps []  sum 0  prob 0.0625  contributes 0.0000
  mask (0, 0, 0, 1)  keeps [4]  sum 4  prob 0.0625  contributes 0.2500
  mask (0, 0, 1, 0)  keeps [3]  sum 3  prob 0.0625  contributes 0.1875
  mask (0, 0, 1, 1)  keeps [3, 4]  sum 7  prob 0.0625  contributes 0.4375
  mask (0, 1, 0, 0)  keeps [2]  sum 2  prob 0.0625  contributes 0.1250
  ... (16 masks total, summed exactly)
```

There are 2⁴ = 16 possible masks; at keep 0.5 each is equally likely (probability 0.0625). Every mask's kept-sum times its probability is added up, so the 5.0 is the true expectation, not a noisy sample average. The whole point of enumerating is honesty: the mismatch is an exact fact about dropout's arithmetic, not something that might wash out with more samples.

<svg role="img" aria-label="All 16 dropout masks, each weighted equally, summing to the exact expected activation of 5.0" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="16" fill="var(--muted)" font-size="8">16 masks, each probability 0.0625, summed exactly</text>
  <g fill="var(--s1)" opacity="0.7">
    <rect x="20" y="24" width="14" height="10"/><rect x="37" y="24" width="14" height="10"/><rect x="54" y="24" width="14" height="10"/><rect x="71" y="24" width="14" height="10"/>
    <rect x="88" y="24" width="14" height="10"/><rect x="105" y="24" width="14" height="10"/><rect x="122" y="24" width="14" height="10"/><rect x="139" y="24" width="14" height="10"/>
    <rect x="156" y="24" width="14" height="10"/><rect x="173" y="24" width="14" height="10"/><rect x="190" y="24" width="14" height="10"/><rect x="207" y="24" width="14" height="10"/>
    <rect x="224" y="24" width="14" height="10"/><rect x="241" y="24" width="14" height="10"/><rect x="258" y="24" width="14" height="10"/><rect x="275" y="24" width="10" height="10"/>
  </g>
  <text x="20" y="55" fill="var(--muted)" font-size="8">Σ probability-weighted kept-sums = 5.0 (exact expectation)</text>
  <text x="20" y="80" fill="var(--muted)" font-size="8">not a sample average — enumerated, so the mismatch is a fact not noise</text>
</svg>
^ Every one of the 16 masks contributes its weighted kept-sum to the exact expectation of 5.0 — enumeration, not sampling, so the half-scale mismatch is provable.

## Definition of done

The self-test pins the arithmetic: no-rescale training is below test, it is exactly p times test, inverted dropout matches test, inverted is the no-scale sum divided by p, and the mask probabilities sum to 1 (a valid enumeration).

```python filename=modules/below-the-prompt/code/dropout-inter-01/dropout.py:99-111 COMPLETE
    no_scale_below_test = no_scale < test
    print("  no-rescale training activation is below test = %s (%.1f < %.1f)" % (no_scale_below_test, no_scale, test))

    mismatch_is_factor_p = abs(no_scale - p * test) < 1e-9
    print("  the no-rescale training sum is exactly p times the test sum = %s (%.1f = %.1f*%.1f)" % (mismatch_is_factor_p, no_scale, p, test))

    inverted_matches_test = abs(inverted - test) < 1e-9
    print("  inverted dropout matches the test-time sum = %s (%.1f = %.1f)" % (inverted_matches_test, inverted, test))

    inverted_scales_by_1_over_p = abs(inverted - no_scale / p) < 1e-9
    print("  inverted dropout is the no-scale sum divided by p = %s (%.1f = %.1f/%.1f)" % (inverted_scales_by_1_over_p, inverted, no_scale, p))

    computed_exactly = abs(sum(mask_prob(m, p) for m in itertools.product([0, 1], repeat=len(units))) - 1.0) < 1e-9
    print("  the mask probabilities sum to 1 (exact enumeration) = %s" % computed_exactly)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — no-scale training underactivates vs test; inverted dropout matches the test-time activation
--------------------------------------------------------------------------------------------------------
  no-rescale training activation is below test = True (5.0 < 10.0)
  the no-rescale training sum is exactly p times the test sum = True (5.0 = 0.5*10.0)
  inverted dropout matches the test-time sum = True (10.0 = 10.0)
  inverted dropout is the no-scale sum divided by p = True (10.0 = 5.0/0.5)
  the mask probabilities sum to 1 (exact enumeration) = True
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  no_scale_below_test=True  mismatch_is_factor_p=True  inverted_matches_test=True  inverted_scales_by_1_over_p=True  computed_exactly=True
```

**Done means the mismatch and the fix are exact: no-rescale training averages 5.0 = 0.5 × 10.0 against test's 10.0, and inverted dropout's 10.0 lands on test precisely, the ×2 cancelling the ×0.5.**

## Boss fight

Inverted dropout matched the expectation. Predict whether matching the expected activation means the training and test activations are identical. It is tempting to think expectation-matching removes all the difference.

It matches the *mean*, not the distribution: during training the activation still varies wildly from step to step (some masks keep the big units, some the small), while at test it is the single fixed full value. Inverted dropout ensures those noisy training activations are centered on the test value, so the network is not systematically mis-scaled — but the per-step noise is the regularization, and it is supposed to be there. The goal is an unbiased match in expectation, not a variance-free one; expecting identical activations misunderstands what dropout is doing. What you must avoid is a *biased* mismatch, which is exactly the un-rescaled case.

The mirror-image mistake is applying dropout at test time, or forgetting to disable it. If dropout stays on at test, every prediction becomes random and, un-rescaled, also half-scale — you have neither a deterministic model nor a matched one. (Deliberately keeping dropout on at test is a real technique, Monte Carlo dropout for uncertainty, but then you average many stochastic passes on purpose, not one.) The default rule is dropout on and rescaled in training, off in test, and a framework's `model.train()` / `model.eval()` switch exists precisely to get this toggle right.

```python filename=modules/below-the-prompt/code/dropout-inter-01/dropout.py:50-57 COMPLETE
def expected_sum(units, p, invert):
    """Exact expected training sum over all masks; invert=True divides survivors by p (inverted dropout)."""
    scale = (1.0 / p) if invert else 1.0
    total = 0.0
    for mask in itertools.product([0, 1], repeat=len(units)):
        kept = sum(u * scale for u, bit in zip(units, mask) if bit)
        total += mask_prob(mask, p) * kept
    return total
```

**Rescale dropout so the expected activation is the same in training and test — divide survivors by the keep probability (inverted dropout) — and toggle dropout off at test, or the network trains and runs at different scales.**

## External resources

Srivastava et al., "Dropout: A Simple Way to Prevent Neural Networks from Overfitting" (2014) — the original method, including the test-time scaling that inverted dropout reorganizes.

The PyTorch `nn.Dropout` docs and `model.train()`/`model.eval()` — how inverted dropout (scaling by 1/p in training) and the train/eval toggle are implemented, the exact mechanics in the boss fight.

Gal and Ghahramani, "Dropout as a Bayesian Approximation" (2016) — Monte Carlo dropout, the deliberate test-time-dropout technique the boss fight distinguishes from the accidental version.
