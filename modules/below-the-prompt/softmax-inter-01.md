---
id: softmax-inter-01
title: Softmax must subtract the max before exp — or a large logit overflows to NaN
topic: below-the-prompt
level: intermediate
status: ready
time: 5-8h
summary: Every generation step ends in a softmax over the vocabulary logits, and the textbook formula exp(x_i)/sum(exp(x_j)) is a trap on real logits, because a deep network can emit a logit of 800 and exp(800) is not a large number in float64 — it is inf, since exp overflows above an argument of about 709. One inf term makes the sum inf, inf/inf is NaN, and the whole distribution becomes NaN with no error raised. The fix is one free line: softmax is shift-invariant, so subtracting the max logit first leaves the distribution bit-for-bit identical while making the largest exponent exp(0)=1 and every other term between 0 and 1, so nothing overflows. On the large-logit vector the naive softmax returns all NaN while the stable one returns a clean [0.085, 0.232, 0.631, 0.052]; on moderate logits the two agree to machine precision, proving the fix costs nothing; and subtracting a constant of 10, 100, or 1000 moves the result by under 2e-15, which is the shift-invariance the fix stands on. The log-sum-exp trick applies the same shift to keep log-probabilities finite.
eli5: To turn a model's raw scores into probabilities you raise a special number to the power of each score and then share the total out. The catch is that raising to a big power blows up past the biggest number a computer can hold, and once one score blows up, the whole sharing turns to nonsense — quietly, no alarm. The escape is a freebie: subtracting the same amount from every score before you start gives the exact same probabilities (it cancels out), so you subtract the biggest score, which drags everything down to a safe size. Same answer, no blow-up.
---

## Why this module

The last thing a language model does at every step is turn a vector of logits — one raw score per vocabulary token — into a probability distribution, and the tool for that is the softmax. Written the way it appears in every textbook, softmax is exp(x_i) divided by the sum of exp(x_j) over all j: exponentiate each score, then normalize so they sum to one. It is correct as mathematics and it is a bug as code, because the exponential of a real logit can be a number no floating-point format can hold.

The overflow threshold is closer than it looks. In float64, `exp` overflows once its argument passes about 709 — `exp(709)` is near the largest representable double, and `exp(710)` is inf. Logits of that size are not pathological; a deep network with a confident prediction can produce a logit of 800 without anything being wrong. The moment it does, the naive softmax exponentiates it to inf, the sum of the exponentials is inf, and every probability is inf divided by inf, which is NaN. The distribution is now entirely NaN, the token you sample from it is garbage, and — the dangerous part — nothing raised an exception. A NaN propagates silently through the sample, the loss, the gradient, until something far downstream is quietly broken.

<svg viewBox="0 0 700 170" role="img" aria-label="A curve of exp(x) rising steeply, with a vertical line at x = 709 marked as the float64 overflow threshold. Below 709 the curve is a finite representable value; at and beyond 709 it is marked inf. A logit of 800 sits well to the right of the threshold, in the inf region.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">exp(x) overflows float64 at x ≈ 709 — logits of 800 are past it</text>
    <line x1="60" y1="140" x2="60" y2="34" stroke="var(--line)"></line>
    <line x1="60" y1="140" x2="660" y2="140" stroke="var(--line)"></line>
    <path d="M 60 138 Q 380 135 470 60 T 520 34" fill="none" stroke="var(--s1)"></path>
    <line x1="470" y1="34" x2="470" y2="140" stroke="var(--s2)" stroke-dasharray="4 3"></line><text x="470" y="154" text-anchor="middle" fill="var(--s2)" font-size="8">x ≈ 709</text>
    <text x="250" y="120" fill="var(--muted)" font-size="8">representable</text>
    <rect x="472" y="40" width="188" height="100" fill="var(--panel)" stroke="var(--s2)"></rect><text x="566" y="86" text-anchor="middle" fill="var(--s2)" font-size="8">exp(x) = inf</text>
    <circle cx="600" cy="140" r="4" fill="var(--s2)"></circle><text x="600" y="156" text-anchor="middle" fill="var(--s2)" font-size="7">logit 800</text>
    <text x="60" y="30" fill="var(--muted)" font-size="7">exp(x)</text>
  </g>
</svg>
^ Past an argument of about 709, exp exceeds the largest float64 and returns inf; a logit of 800 lands well inside that region. The naive softmax calls exp on that logit directly, so it overflows before it can normalize.

The fix is one line and it is genuinely free, because softmax has a symmetry: it is shift-invariant. Subtract the same constant from every logit and the distribution does not change at all, because the constant appears as a factor in both the numerator and the denominator and cancels exactly. So before exponentiating, subtract the maximum logit. Now the largest shifted logit is 0, its exponential is 1, every other term is between 0 and 1, and nothing can overflow — and by shift-invariance the answer is the exact distribution the textbook formula was trying to compute. This module builds both, shows the naive one going to NaN where the stable one holds, and shows they agree to machine precision where the naive one still works. Everything runs offline against a logit fixture, stdlib Python 3, `$0.00`, with every exponential computed. The instinct to unlearn is that the textbook formula is the implementation. The implementation subtracts the max first, always, and it costs nothing to do so.

## Concepts

Named here so you can find them again; each is built below.

- **Logit** — a raw pre-softmax score, one per vocabulary token; can be large in magnitude.
- **Softmax** — exp of each logit divided by the sum of the exps; turns logits into a distribution.
- **Overflow** — `exp` above an argument of ~709 exceeds float64 and returns inf.
- **NaN propagation** — inf/inf is NaN, and one NaN poisons the whole distribution silently.
- **Shift-invariance** — subtracting a constant from every logit leaves the distribution unchanged.
- **Log-sum-exp** — the stable way to compute log(sum(exp)) for log-probabilities.

## Worked example

Source: the softmax at the end of a transformer's forward pass, the one that produces next-token probabilities. The logit vectors stand in for real pre-softmax outputs — one with ordinary small values, one with the large values a confident deep network actually emits.

Script and fixture: `modules/below-the-prompt/code/softmax-inter-01/` — `softmax.py`, and `logits.json`, three logit vectors. Every command runs from there.

### The naive softmax, and where it breaks

The textbook softmax exponentiates each logit and normalizes. The only defensive touch is that `math.exp` raises `OverflowError` rather than returning inf, so we catch it and return inf to reproduce exactly what a float exp (as in NumPy or a GPU) would do.

```
# softmax.py:41-55 — COMPLETE (the textbook softmax, and the exp that overflows to inf)
def softmax_naive(logits):
    """Textbook formula: exp each logit, divide by the sum. Overflows to inf -> NaN on large logits."""
    exps = [safe_exp(x) for x in logits]
    total = sum(exps)
    return [e / total for e in exps]


def safe_exp(x):
    """math.exp raises OverflowError above ~709; return inf so the NaN propagates like float exp would."""
    try:
        return math.exp(x)
    except OverflowError:
        return math.inf
```

There is nothing wrong with the arithmetic — it is the definition. The problem is entirely that `exp(x)` for `x` around 800 is not representable. Run both softmaxes on all three vectors:

```
# $ python3 softmax.py --logits
#   moderate   logits=[2.0, 1.0, 0.1, -0.5]
#      naive : [0.6252, 0.2300, 0.0935, 0.0513]  valid=True
#      stable: [0.6252, 0.2300, 0.0935, 0.0513]  valid=True
#   large      logits=[800.0, 801.0, 802.0, 799.5]
#      naive : [nan, nan, nan, nan]  valid=False
#      stable: [0.0854, 0.2321, 0.6308, 0.0518]  valid=True
```

run: 2026-08-27 · deterministic; the logit vectors are a fixture · 3 vectors · `python3 softmax.py --logits`

On the moderate vector the naive softmax is fine — the logits are small, nothing overflows, and it returns [0.6252, 0.2300, 0.0935, 0.0513]. On the large vector, where the logits are near 800, it returns all NaN, and `valid=False`. The stable softmax returns a clean distribution on both, and on the large vector it recovers exactly the probabilities the naive one destroyed: [0.0854, 0.2321, 0.6308, 0.0518], correctly putting most mass on the largest logit (802). Same inputs, and the only difference is one subtraction.

<svg viewBox="0 0 700 200" role="img" aria-label="Two softmaxes on the large-logit vector. The naive path: exp(800) overflows to inf, the sum is inf, inf over inf is NaN, giving a NaN distribution. The stable path: subtract the max 802, exp of the shifted logits is at most 1, the sum is finite, giving a valid distribution 0.085, 0.232, 0.631, 0.052.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the large-logit vector [800, 801, 802, 799.5] through both softmaxes</text>
    <text x="40" y="46" fill="var(--s2)">naive</text>
    <rect x="90" y="34" width="90" height="22" fill="var(--panel)" stroke="var(--s2)"></rect><text x="135" y="49" text-anchor="middle" fill="var(--s2)" font-size="8">exp(802)</text>
    <text x="190" y="49" fill="var(--s2)" font-size="8">→ inf</text>
    <rect x="240" y="34" width="90" height="22" fill="var(--panel)" stroke="var(--s2)"></rect><text x="285" y="49" text-anchor="middle" fill="var(--s2)" font-size="8">sum = inf</text>
    <text x="340" y="49" fill="var(--s2)" font-size="8">→ inf/inf</text>
    <rect x="420" y="34" width="150" height="22" fill="var(--s2)"></rect><text x="495" y="49" text-anchor="middle" fill="var(--panel)" font-size="8">[nan, nan, nan, nan]</text>
    <text x="40" y="116" fill="var(--s1)">stable</text>
    <rect x="90" y="104" width="120" height="22" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="150" y="119" text-anchor="middle" fill="var(--acc-ink)" font-size="8">subtract max 802</text>
    <rect x="230" y="104" width="110" height="22" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="285" y="119" text-anchor="middle" fill="var(--acc-ink)" font-size="8">exp(≤0) ≤ 1</text>
    <rect x="360" y="104" width="90" height="22" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="405" y="119" text-anchor="middle" fill="var(--acc-ink)" font-size="8">sum finite</text>
    <rect x="470" y="104" width="180" height="22" fill="var(--s1)"></rect><text x="560" y="119" text-anchor="middle" fill="var(--panel)" font-size="8">[.085, .232, .631, .052]</text>
    <text x="40" y="170" fill="var(--muted)" font-size="8">same logits — the naive path overflows before it can normalize; the stable path never exceeds 1</text>
  </g>
</svg>
^ The naive path exponentiates a logit of 802 straight to inf and collapses to NaN; the stable path subtracts the max so the largest exponent is exp(0)=1, keeps the sum finite, and lands the correct distribution. The overflow happens before normalization can save it.

### The stable softmax and why it is free

The fix subtracts the max logit before exponentiating.

```
# softmax.py:58-64 — COMPLETE (subtract the max first: shift-invariant, so identical but safe)
def softmax_stable(logits):
    """Subtract the max logit first. Shift-invariant, so identical result -- but nothing overflows."""
    m = max(logits)
    exps = [math.exp(x - m) for x in logits]   # largest term is exp(0)=1; nothing overflows
    total = sum(exps)
    return [e / total for e in exps]
```

The single new line is `x - m`. Because the same `m` is subtracted from every logit, it factors out of the softmax entirely — it multiplies numerator and denominator by the same `exp(-m)` and cancels — so the distribution is unchanged. That is the claim the fix rests on, and it is worth seeing directly rather than trusting: subtract 10, 100, or 1000 from the moderate vector and watch the distribution not move.

```
# $ python3 softmax.py --shift
#   logits           [2.0, 1.0, 0.1, -0.5] -> [0.6252, 0.2300, 0.0935, 0.0513]
#   minus 10         [-8.0, -9.0, -9.9, -10.5] -> [0.6252, 0.2300, 0.0935, 0.0513]  (max diff 2.78e-17)
#   minus 100        [-98.0, -99.0, -99.9, -100.5] -> [0.6252, 0.2300, 0.0935, 0.0513]  (max diff 4.86e-16)
#   minus 1000       [-998.0, -999.0, -999.9, -1000.5] -> [0.6252, 0.2300, 0.0935, 0.0513]  (max diff 1.93e-15)
```

run: 2026-08-27 · deterministic · `python3 softmax.py --shift`

The distribution is identical to within 2e-15 no matter what constant you subtract — that residue is ordinary floating-point rounding, not a real change. Shift-invariance is exact in the math, so subtracting the max is not an approximation that trades accuracy for safety; it is the same answer, made computable. The choice of the max specifically is what guarantees the largest shifted logit is exactly 0, so the largest exponential is exactly 1 and overflow is impossible.

<svg viewBox="0 0 700 170" role="img" aria-label="A bar chart showing the same four-bar distribution repeated four times under different shifts: original, minus 10, minus 100, minus 1000. All four groups of bars are identical heights, illustrating shift-invariance. A note gives the max difference under 2e-15.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the distribution is unchanged under any shift — shift-invariance</text>
    <line x1="40" y1="130" x2="660" y2="130" stroke="var(--line)"></line>
    <g fill="var(--s1)">
      <rect x="50" y="55" width="14" height="75"></rect><rect x="66" y="102" width="14" height="28"></rect><rect x="82" y="119" width="14" height="11"></rect><rect x="98" y="124" width="14" height="6"></rect>
      <rect x="200" y="55" width="14" height="75"></rect><rect x="216" y="102" width="14" height="28"></rect><rect x="232" y="119" width="14" height="11"></rect><rect x="248" y="124" width="14" height="6"></rect>
      <rect x="350" y="55" width="14" height="75"></rect><rect x="366" y="102" width="14" height="28"></rect><rect x="382" y="119" width="14" height="11"></rect><rect x="398" y="124" width="14" height="6"></rect>
      <rect x="500" y="55" width="14" height="75"></rect><rect x="516" y="102" width="14" height="28"></rect><rect x="532" y="119" width="14" height="11"></rect><rect x="548" y="124" width="14" height="6"></rect>
    </g>
    <text x="80" y="148" text-anchor="middle" fill="var(--muted)" font-size="8">original</text>
    <text x="230" y="148" text-anchor="middle" fill="var(--muted)" font-size="8">−10</text>
    <text x="380" y="148" text-anchor="middle" fill="var(--muted)" font-size="8">−100</text>
    <text x="530" y="148" text-anchor="middle" fill="var(--muted)" font-size="8">−1000</text>
    <text x="590" y="90" fill="var(--muted)" font-size="8">identical</text><text x="590" y="104" fill="var(--muted)" font-size="8">(< 2e-15)</text>
  </g>
</svg>
^ The four bar groups are the same distribution under four different shifts; the constant cancels, so subtracting the max is a free change of representation, not a change of answer.

### Log-sum-exp for log-probabilities

The same shift rescues the other quantity you need from logits: the log of the sum of exponentials, which is how you get normalized log-probabilities (for cross-entropy loss, or log-likelihood scoring) without overflowing.

```
# softmax.py:66-69 — COMPLETE (log-sum-exp: the shift moved outside the log)
def logsumexp(logits):
    """log(sum(exp(x))) computed stably: m + log(sum(exp(x - m))). Needed for log-probabilities."""
    m = max(logits)
    return m + math.log(sum(math.exp(x - m) for x in logits))
```

Computing `log(sum(exp(x)))` directly overflows for the same reason softmax does — the inner `exp` blows up. Factoring the max out of the sum turns it into `m + log(sum(exp(x - m)))`, where the inner exponentials are all at most 1 and the `m` is added back outside the log. On the large vector this returns 802.461, finite, where the naive version would be `log(inf)` = inf. It is the same trick — subtract the max, add it back where it belongs.

**Softmax is shift-invariant, so subtracting the max logit before exponentiating returns the identical distribution while guaranteeing the largest exponent is exp(0)=1 — the naive textbook formula overflows a logit of 800 to inf and collapses the whole distribution to NaN with no error raised, and the one-line, cost-free fix is to never call exp on an un-shifted logit.**

### The self-test

The `--check` mode plants the bug — the un-shifted exp — and proves it: the naive softmax NaNs on the large vector, the stable one is a valid distribution on the same input, the two agree exactly where the naive one works, the shift is invariant, and log-sum-exp stays finite.

```
# $ python3 softmax.py --check
#   naive softmax on the large-logit vector produces NaN = True ([nan, nan, nan, nan])
#   stable softmax on the SAME vector is a valid distribution = True ([0.0854, 0.2321, 0.6308, 0.0518])
#   where the naive one works (moderate logits), the two agree exactly = True
#   subtracting the max is shift-invariant (same distribution) = True
#   logsumexp on the large vector stays finite = True (802.461)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 softmax.py --check`

The `agree` line is the one that makes the case airtight: the stable softmax is not a different, safer approximation — it is the same function, so where the naive one is able to compute at all, they match to machine precision. The fix therefore has no downside to weigh; it is strictly the naive formula with its one failure mode removed.

```
# softmax.py:74-78 — COMPLETE (the valid-distribution test the self-test asserts)
def is_valid_dist(p):
    """A valid distribution: all entries finite in [0,1] and summing to 1."""
    if any(math.isnan(x) or math.isinf(x) for x in p):
        return False
    return all(0.0 <= x <= 1.0 for x in p) and abs(sum(p) - 1.0) < 1e-9
```

### The running tally

| vector | naive softmax | stable softmax | agree? |
|---|---|---|---|
| moderate [2, 1, 0.1, −0.5] | [0.625, 0.230, 0.094, 0.051] | [0.625, 0.230, 0.094, 0.051] | yes, to 1e-12 |
| large [800, 801, 802, 799.5] | [nan, nan, nan, nan] | [0.085, 0.232, 0.631, 0.052] | naive is broken |
| shift by −10 / −100 / −1000 | (unchanged) | (unchanged) | diff < 2e-15 |

Read the agree column: where the naive softmax produces a number at all, it is the same number the stable one produces, and where it does not, the stable one is still correct. There is no regime in which the naive formula is better — only regimes where it is equal or broken. That asymmetry is why the max-subtraction is not an optimization you reach for under load; it is the definition of a correct softmax implementation.

### What we did not settle

This is the core stability fix; a few neighbors round it out. The same overflow lurks in temperature scaling — dividing logits by a small temperature before softmax makes them larger, so the max-subtraction matters more, not less, at low temperature (`sampling-inter-01`). Cross-entropy loss is computed as the log-sum-exp minus the target logit, using exactly the `logsumexp` here, which is why training frameworks fuse "log-softmax" into one stable op rather than composing `log` after `softmax`. Underflow is the mirror image — a very negative shifted logit exponentiates to 0, which is harmless for softmax but bites if you then take its log, another reason to work in log-space. And on a GPU the reduction (the sum) has its own numerical order-of-operations subtleties beyond this. The invariant is the one to keep: never exponentiate a logit you have not first shifted by the max.

## Build

The build in one paragraph: implement softmax as subtract-the-max-then-exponentiate-then-normalize, never the raw textbook formula, so the largest exponent is exp(0)=1 and no logit can overflow; rely on shift-invariance, which makes the subtraction exact rather than approximate; and compute any log-probability through log-sum-exp (max plus log of the shifted sum) rather than log after softmax. Confirm on a large-logit vector that the naive formula NaNs and yours does not, and that the two agree to machine precision where the naive one works. Fuse log-softmax for training loss, watch temperature scaling which amplifies logits, and stay in log-space when you need logs.

We opened on the overflow. The number that proves the fix is the two softmaxes on the same large vector:

```
# modules/below-the-prompt/code/softmax-inter-01/ — COMPLETE, run from that directory
$ python3 softmax.py --check
  naive softmax on the large-logit vector produces NaN = True ([nan, nan, nan, nan])
  stable softmax on the SAME vector is a valid distribution = True ([0.0854, 0.2321, 0.6308, 0.0518])
```

Now build your own. Take a logit vector with a value above 709 — from a real model's final layer, or synthetic — and implement softmax both ways. Your number to beat is not speed; it is **validity: the naive softmax should NaN on the large vector while yours returns a distribution summing to 1, and the two should agree to machine precision on a moderate vector**. Then confirm shift-invariance by subtracting a large constant and seeing the distribution hold. Bring back both softmaxes on the large vector. Good luck.

## Definition of done

- [ ] A naive softmax (raw exp) and a stable softmax (subtract the max first)
- [ ] Confirmation the naive one produces NaN on a logit above ~709 and the stable one does not
- [ ] Confirmation the stable one is a valid distribution (finite, in [0,1], sums to 1)
- [ ] Confirmation the two agree to machine precision where the naive one works
- [ ] A demonstration of shift-invariance: subtracting a constant leaves the distribution unchanged
- [ ] A log-sum-exp that stays finite on the large vector
- [ ] `python3 softmax.py --check` printing SELF-TEST PASS: naive_nans, stable_valid, agree, shift_ok, lse_finite
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does the textbook softmax fail on a logit of 800? At what argument does exp overflow, and what does the distribution become?
2. What property makes subtracting the max free rather than an approximation? Sketch why the constant cancels.
3. Why subtract the max specifically, rather than the mean or the min?
4. Why does the self-test check that the two softmaxes agree on moderate logits — what would it mean if they did not?
5. Your own large-logit vector was run both ways. What did each softmax return, and did shift-invariance hold under a large subtraction?

## External resources

- The log-sum-exp trick (any numerical-methods or deep-learning-framework reference) — my summary: the derivation of m + log(sum(exp(x - m))) and where frameworks use it for log-softmax and cross-entropy; read it for why loss is computed in log-space.
- The sampling module in this hub, *sampling-inter-01* (temperature and top-p shape the softmax) — my summary: how temperature rescales logits before this softmax and why low temperature makes the overflow risk worse; read it for the operation that sits directly upstream of this one.
- This hub, *transformer-adv-01* (one transformer layer end to end) — read it for where this softmax sits at the model's output and what the logits it consumes are.
