---
id: fp16-inter-01
title: Scale the loss before the fp16 backward pass — or small gradients underflow to zero and never learn
topic: below-the-prompt
level: intermediate
status: ready
time: 21 min
summary: fp16 cannot represent numbers below about 6.1e-5, so small gradients flush to zero and their weights never update. Loss scaling multiplies the loss — and thus every gradient — by a large factor before the backward pass to lift small gradients into range, then divides back after. Of six gradients, three underflow unscaled; scaled by 1024, all six survive and recover their true values.
eli5: A cheap scale can't weigh anything lighter than a gram, so a feather reads as zero. If you first tape the feather to a kilogram weight, the scale can read the total, and you subtract the kilogram afterward to get the feather's weight. Loss scaling does that for tiny gradients a low-precision number format would otherwise read as nothing.
---

## Why this module

Training in half precision is nearly free speed and memory — until it silently stops updating part of your model, and loss scaling is the one line that prevents it.

fp16, the 16-bit floating-point format, is half the size of fp32 and much faster on modern hardware, which is why mixed-precision training is standard. But sixteen bits buy a narrow range: fp16's smallest normal value is about 6.1e-5, and any number smaller than that flushes to zero. Gradients are frequently that small — deep in a network where signals have attenuated, for weights that are rarely active, or late in training as the model converges — and when a small gradient is stored in fp16, it underflows to zero. The optimizer then sees no gradient for that weight and does not update it. The update was real and nonzero; fp16 just could not represent it, so it vanished, and that weight stops learning for a reason nothing in the logs will show.

The damage is quiet and partial. The large gradients are fine, so most of the model trains normally and the loss goes down; only the weights with small gradients are frozen, so the model underperforms in ways that look like "it just isn't learning this part" rather than a numerical bug. Because it is not a crash and not obviously wrong, it is easy to blame the architecture or the data when the real cause is fp16 eating the small gradients.

Loss scaling fixes it with a rescaling that cancels out. Before the backward pass, multiply the loss by a large factor S. By the chain rule, every gradient is then multiplied by S too, which lifts the small gradients up into fp16's representable range so they survive the round-trip through fp16. Then, before the optimizer applies the update, divide the gradients back by S to restore their true magnitudes. The multiply and divide cancel mathematically, so the weight update is unchanged — except that the small gradients that would have underflowed now make it through.

We will push six gradients through fp16. Unscaled, three of them fall below the threshold and flush to zero — three frozen weights. Scaled by 1024 before the backward pass and divided back after, all six survive and recover their exact values. Same gradients; scaling is the difference between three lost updates and none.

**fp16 flushes gradients below ~6.1e-5 to zero, freezing their weights; loss scaling multiplies the loss by S to lift small gradients into range and divides back after, a cancelling rescale that saves them at no cost.**

## Concepts

The root constraint is fp16's dynamic range. A floating-point format trades bits between the exponent (range) and the mantissa (precision), and fp16's five exponent bits give it a smallest normal magnitude around 2⁻¹⁴ ≈ 6.1e-5. Below that it has only gradual-underflow subnormals and then zero, and many training pipelines flush subnormals to zero for speed, so effectively anything under the threshold becomes zero. This is not a rounding error in the last digit; it is total loss — the value becomes exactly zero, and zero times any learning rate is no update.

Why gradients specifically hit this: gradients span an enormous range across a network and across training. Early layers, small learning signals, converging weights, and attention to rare features all produce gradients orders of magnitude smaller than the typical activation or weight. fp32, with eight exponent bits, has a smallest normal around 1e-38 and never notices; fp16's floor at 6.1e-5 sits right in the middle of the gradient distribution, so a meaningful fraction of gradients fall below it. The forward pass usually survives fp16 fine — activations are larger — but the backward pass, full of small gradients, is where underflow bites.

Loss scaling exploits linearity. Scaling the loss by S scales every gradient by S exactly (the gradient of S·L is S·∇L), so it is a uniform shift of the whole gradient distribution up by a factor S — in log terms, a rightward slide that moves the small gradients above the underflow threshold while the large ones stay representable (as long as S is not so large that the largest gradients overflow the top of fp16's range, about 65504). After the gradients are safely in fp16, dividing by S restores their true values before the weight update, so the optimizer sees the correct gradients. The whole trick is to do the fragile fp16 round-trip while the values are temporarily large.

<svg role="img" aria-label="A log axis of the loss scale S: below about 16 the smallest gradient underflows, above about 1.3 million the largest overflows, with a wide safe window between" viewBox="0 0 460 130" width="460" height="130">
  <rect x="0" y="0" width="460" height="130" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="10" fill="var(--muted)">loss scale S (log axis)</text>
  <line x1="30" y1="70" x2="440" y2="70" stroke="var(--line)"/>
  <rect x="30" y="60" width="90" height="20" fill="var(--s2)" stroke="var(--line)"/><text x="40" y="100" font-family="var(--mono)" font-size="8" fill="var(--s2)">S&lt;16: small underflows</text>
  <rect x="120" y="60" width="230" height="20" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="150" y="74" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">safe window (all survive)</text>
  <rect x="350" y="60" width="90" height="20" fill="var(--s2)" stroke="var(--line)"/><text x="356" y="100" font-family="var(--mono)" font-size="8" fill="var(--s2)">S&gt;1.3e6: large overflows</text>
  <line x1="120" y1="52" x2="120" y2="88" stroke="var(--acc-ink)"/><text x="112" y="48" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">16</text>
  <line x1="350" y1="52" x2="350" y2="88" stroke="var(--acc-ink)"/><text x="336" y="48" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">1.3e6</text>
</svg>
^ The scale must clear the floor for the smallest gradient (~16 here) but stay under the ceiling for the largest (~1.3e6); dynamic loss scaling hunts for the top of that window automatically.

Choosing S is the one subtlety. Too small and the smallest gradients still underflow; too large and the largest gradients overflow to infinity, which is worse. Production uses dynamic loss scaling: start with a large S, and if an overflow (inf/nan) is detected in the gradients, halve S and skip that step; if many steps pass with no overflow, double S. This automatically tracks the largest safe scale as the gradient magnitudes change over training. The fixed S in this module is the static version; the dynamic version is the same idea with an automatic thermostat.

**fp16's exponent range floors small values at ~6.1e-5, right inside the gradient distribution; loss scaling slides the whole distribution up by S past that floor for the fp16 round-trip, then slides back — bounded above by fp16's overflow ceiling.**

## Worked example

The fixture is six gradient magnitudes, the fp16 threshold, and a loss-scale factor.

```json filename=modules/below-the-prompt/code/fp16-inter-01/grads.json:7-16 COMPLETE
  "fp16_min": 6.104e-05,
  "scale": 1024,
  "gradients": [
    0.05,
    0.002,
    8e-05,
    3e-05,
    1e-05,
    4e-06
  ]
```

The fp16 threshold is 6.104e-5; the loss scale is 1024. The gradients range from 0.05 down to 4e-6. fp16 storage flushes anything below the threshold to zero.

```python filename=modules/below-the-prompt/code/fp16-inter-01/lossscale.py:39-41 COMPLETE
def to_fp16(x, fp16_min):
    """Model fp16 flush-to-zero: values below the smallest representable magnitude round to 0."""
    return 0.0 if 0 < abs(x) < fp16_min else x
```

Unscaled stores each gradient directly; loss-scaled multiplies by the scale first, then divides back.

```python filename=modules/below-the-prompt/code/fp16-inter-01/lossscale.py:44-46 COMPLETE
def unscaled(gradients, fp16_min):
    """Each gradient stored directly in fp16 -- the small ones underflow to zero."""
    return [to_fp16(g, fp16_min) for g in gradients]
```

```python filename=modules/below-the-prompt/code/fp16-inter-01/lossscale.py:49-51 COMPLETE
def loss_scaled(gradients, fp16_min, scale):
    """Multiply by scale before fp16 (lifts small gradients into range), then divide back to recover."""
    return [to_fp16(g * scale, fp16_min) / scale for g in gradients]
```

Which gradients are below the threshold?

```text filename=modules/below-the-prompt/code/fp16-inter-01/lossscale.py --gradients
GRADIENTS — true magnitudes vs the fp16 threshold 6.10e-05
--------------------------------------------------
  0.05
  0.002
  8e-05
  3e-05  <- below threshold, will underflow
  1e-05  <- below threshold, will underflow
  4e-06  <- below threshold, will underflow
```

The bottom three — 3e-5, 1e-5, 4e-6 — are below 6.1e-5 and will underflow. Predict: unscaled, those three flush to zero. Scaled by 1024, they become 0.031, 0.010, 0.0041, all far above the threshold, so they survive fp16, and dividing back by 1024 recovers 3e-5, 1e-5, 4e-6. Run it.

```text filename=modules/below-the-prompt/code/fp16-inter-01/lossscale.py --scale
SCALE — fp16 storage unscaled vs loss-scaled (scale=1024)
--------------------------------------------------------------
  true grad      unscaled fp16    loss-scaled (recovered)
  0.05           0.05             0.05
  0.002          0.002            0.002
  8e-05          8e-05            8e-05
  3e-05          0                3e-05
  1e-05          0                1e-05
  4e-06          0                4e-06
```

The unscaled column zeros the bottom three — those three weights get no update this step, and if their gradients stay small they never learn. The loss-scaled column recovers all six exactly: the three that would have underflowed are back at their true values, because scaling carried them through the fp16 round-trip while they were temporarily large. The top three gradients are identical in both columns — scaling did not disturb them — so the fix is pure upside: it rescues the small gradients and leaves the large ones alone.

<svg role="img" aria-label="Gradients preserved of six: unscaled keeps three, loss-scaled keeps all six" viewBox="0 0 460 140" width="460" height="140">
  <rect x="0" y="0" width="460" height="140" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">gradients that survive fp16 (of 6)</text>
  <line x1="60" y1="110" x2="440" y2="110" stroke="var(--line)"/>
  <rect x="100" y="65" width="120" height="45" fill="var(--s2)" stroke="var(--line)"/><text x="150" y="59" font-family="var(--mono)" font-size="11" fill="var(--s2)">3 / 6</text><text x="98" y="126" font-family="var(--mono)" font-size="9" fill="var(--muted)">unscaled</text>
  <rect x="280" y="20" width="120" height="90" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="330" y="14" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">6 / 6</text><text x="278" y="126" font-family="var(--mono)" font-size="9" fill="var(--muted)">loss-scaled</text>
</svg>
^ Unscaled fp16 keeps only the three gradients above its floor; loss scaling brings all six through, freezing no weights.

<svg role="img" aria-label="A log number line with the fp16 threshold; three gradients sit above it and survive, three sit below and flush to zero; loss scaling shifts all six right past the threshold" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">gradient magnitude (log scale); left of the line → 0 in fp16</text>
  <line x1="200" y1="30" x2="200" y2="95" stroke="var(--s2)" stroke-dasharray="4 3"/><text x="150" y="44" font-family="var(--mono)" font-size="8" fill="var(--s2)">fp16 floor 6.1e-5</text>
  <line x1="30" y1="70" x2="440" y2="70" stroke="var(--line)"/>
  <text x="20" y="88" font-family="var(--mono)" font-size="8" fill="var(--muted)">unscaled:</text>
  <g fill="var(--acc-line)"><circle cx="300" cy="70" r="4"/><circle cx="340" cy="70" r="4"/><circle cx="215" cy="70" r="4"/></g>
  <g fill="var(--s2)"><circle cx="150" cy="70" r="4"/><circle cx="110" cy="70" r="4"/><circle cx="70" cy="70" r="4"/></g>
  <text x="70" y="58" font-family="var(--mono)" font-size="8" fill="var(--s2)">3 flush to 0</text>
  <line x1="200" y1="120" x2="200" y2="175" stroke="var(--s2)" stroke-dasharray="4 3"/>
  <line x1="30" y1="150" x2="440" y2="150" stroke="var(--line)"/>
  <text x="20" y="140" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">scaled ×1024:</text>
  <g fill="var(--acc-line)"><circle cx="420" cy="150" r="4"/><circle cx="400" cy="150" r="4"/><circle cx="360" cy="150" r="4"/><circle cx="330" cy="150" r="4"/><circle cx="300" cy="150" r="4"/><circle cx="270" cy="150" r="4"/></g>
  <text x="270" y="170" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">all 6 now right of the floor → survive, then ÷1024</text>
</svg>
^ Unscaled, three gradients sit left of the fp16 floor and flush to zero; scaling slides the whole set right past the floor so all six survive the fp16 round-trip, then dividing back restores them.

## Build

Reproduce the two columns. Pure arithmetic modeling fp16 flush-to-zero, so the three underflows and the full recovery come out exactly.

Run `--gradients` for the threshold check, `--scale` for the two columns, `--check` for the gate. The self-test pins the whole story: unscaled loses small gradients, scaling loses none, the scaled values recover the true ones, and the lost gradients were real updates.

```python filename=modules/below-the-prompt/code/fp16-inter-01/lossscale.py:92-95 COMPLETE
    unscaled_loses = lost(g, uns) > 0
    print("  unscaled fp16 flushes small gradients to zero = %s (%d of %d lost)" % (unscaled_loses, lost(g, uns), len(g)))

    scaled_loses_none = lost(g, sca) == 0
    print("  loss scaling loses none = %s (%d lost)" % (scaled_loses_none, lost(g, sca)))
```

The `recovered` check, in the gate, is what proves loss scaling is lossless on the values it saves — not just that the small gradients are nonzero after scaling, but that they equal their true magnitudes to floating-point precision. That is the whole point of dividing back by S: the rescue must not distort the gradient, or you would be training on wrong values. The multiply-then-divide has to cancel exactly, and the check confirms it does. Here is the full gate.

```text filename=modules/below-the-prompt/code/fp16-inter-01/lossscale.py --check
SELF-TEST — unscaled loses the small gradients; loss scaling preserves and recovers all of them
------------------------------------------------------------------------------------------
  unscaled fp16 flushes small gradients to zero = True (3 of 6 lost)
  loss scaling loses none = True (0 lost)
  loss-scaled gradients recover the true values = True
  the lost gradients were real, nonzero updates = True (weights that would never learn)
------------------------------------------------------------------------------------------
SELF-TEST PASS  unscaled_loses=True  scaled_loses_none=True  recovered=True  lost_were_real=True
```

Four True flags. Unscaled_loses: fp16 zeroes three gradients. Scaled_loses_none: loss scaling saves all six. Recovered: the saved gradients equal their true values exactly. Lost_were_real: the underflowed gradients were nonzero updates, so unscaled fp16 froze real learning. The recovered flag is the one that makes loss scaling safe — it rescues the small gradients without changing any of them.

**The recovered check proves the multiply-by-S then divide-by-S cancels exactly, so loss scaling saves the small gradients without distorting them — lossless, not approximate.**

## Definition of done

You are done when you reproduce the underflow and the recovery and can explain why scaling cancels.

Concretely: `--scale` shows unscaled zeroing three gradients and loss-scaled recovering all six; `--check` prints PASS with four True flags. You can explain fp16's range floor (~6.1e-5, from five exponent bits) and why gradients fall below it while activations usually do not. You can explain why scaling the loss by S scales every gradient by S (linearity of the derivative), why that lifts small gradients above the floor, and why dividing back by S recovers the true update exactly. And you can describe dynamic loss scaling — raise S until an overflow, then back off — as the automatic version bounded by fp16's overflow ceiling.

The habit to carry: never train in fp16 without loss scaling, and prefer a dynamic loss scaler. When a mixed-precision model trains worse than its fp32 twin or seems to "not learn" some part, suspect gradient underflow before the architecture, and check whether loss scaling is on and large enough.

## Boss fight

The instructive failure is a mixed-precision speedup that quietly costs accuracy no one can explain.

A team switches training to fp16 for the 2× speedup and 50% memory saving, with no loss scaling. Training runs, the loss goes down, and the model ships — but it is a point or two worse than the fp32 baseline, and no one can find why. There is no crash, no nan, no error; the code is "correct." The cause is that a slice of the gradients underflowed to zero every step, so some weights barely trained, and the model converged to a slightly worse solution. The fix is one wrapper — a loss scaler — that would have recovered the fp32 accuracy at fp16 speed. The bug was invisible precisely because fp16 underflow is silent: it does not fail, it just drops the small gradients.

Your turn, two moves. First, find the scale that saves the smallest gradient. The smallest gradient is 4e-6 and the floor is 6.1e-5, so it needs a scale of at least 6.1e-5 / 4e-6 ≈ 15.3 to clear the floor — round up to the next power of two, 16. Predict and check that scale=16 saves the 4e-6 gradient (16 × 4e-6 = 6.4e-5 > floor) while scale=8 does not (8 × 4e-6 = 3.2e-5 < floor). The scale must exceed the ratio of the floor to your smallest meaningful gradient. Second, find the overflow ceiling. fp16's largest value is about 65504; the largest gradient is 0.05, so the scale that would overflow it is 65504 / 0.05 ≈ 1.3e6. Predict the safe window for S — above ~16 to save the smallest, below ~1.3e6 to not overflow the largest — and see why dynamic loss scaling exists: it hunts for the top of that window automatically, because the safe range shifts as gradients grow and shrink over training.

## External resources

Micikevicius et al., "Mixed Precision Training" (2018), is the paper that introduced loss scaling; it shows fp16 gradient underflow directly (a histogram of gradients against the fp16 range) and demonstrates that loss scaling recovers fp32 accuracy at fp16 cost.

The NVIDIA Apex and PyTorch AMP (`torch.cuda.amp`) documentation describe dynamic loss scaling — the automatic raise-until-overflow-then-back-off scaler — and are the standard practical references for enabling it.

For the numerics, the IEEE 754 half-precision format and the concept of dynamic range versus precision explain why fp16's floor sits at 2⁻¹⁴ and why bf16 (more exponent bits, fewer mantissa bits) sidesteps the underflow problem at the cost of precision — the alternative modern formats make.
