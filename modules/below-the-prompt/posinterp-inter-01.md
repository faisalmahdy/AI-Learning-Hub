---
id: posinterp-inter-01
title: Interpolate positions into the trained range to extend context — RoPE rotated past its trained range produces out-of-distribution angles
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: RoPE encodes position by rotating each pair of query/key dimensions by an angle proportional to the token's position, across a spectrum of frequencies — high-frequency pairs rotate a lot per position and resolve nearby tokens, low-frequency pairs rotate very little per position and carry long-range order. Attention's dot product depends on the relative rotation between two positions, so what a trained model has seen is the range of angles that positions up to its training length L produce. Run the model on a context longer than L and the far positions rotate by angles beyond that range — worst on the low-frequency dimensions, which rotate so little per position that even at L they have barely turned, so pushing them out to several times L sends them into angle territory never trained on, out of distribution, and attention degrades. That is extrapolation. Position interpolation fixes it by scaling every position by L/target before applying RoPE, squeezing the whole target range back into the trained angle range so no dimension ever sees an unfamiliar angle; the cost is resolution, because squeezing positions together makes adjacent tokens closer in angle. On a fixture of a model trained to length 8 run at length 32, extrapolation rotates the lowest-frequency dimension to 4× its trained maximum angle (0.32 vs 0.08 rad), while interpolation scales positions by 8/32 and returns that angle exactly to the trained maximum, at the cost of quartering the adjacent-token angle step (1.0 → 0.25 rad).
eli5: Imagine a set of clock hands of different speeds all pinned at the same center, and the position of a word is written by how far each hand has swung. A fast hand sweeps all the way around even for small positions, but the slowest hand barely creeps — over the whole span the model was trained on, it only nudges a tiny bit. Now you want to use the model on a span four times longer. If you just keep swinging the slow hand, it moves into a stretch of the dial it has never been in during training, and the model gets confused because it has never read the clock there. The safe fix is to squeeze the longer span back onto the same little arc the slow hand already knows — so it still only creeps the familiar amount. The price is that the fast hands, which used to put a big gap between neighboring words, now put a smaller gap, so neighbors are harder to tell apart.
---

## Why this module

A model is trained with a fixed maximum context length, and then someone wants to run it on longer inputs. With RoPE, the position information lives in rotations applied to the query and key vectors, and the naive way to handle a longer context is simply to keep assigning positions — token 9, token 10, up to whatever length you need. That is extrapolation, and it usually makes quality fall off a cliff well before the new length is reached.

Understanding why needs one fact about RoPE: it is a spectrum of rotations, not one. Each pair of head dimensions rotates at its own frequency, geometrically spaced from fast to slow. The fast pairs spin through many full turns over the training length and resolve fine position differences between nearby tokens; the slow pairs turn only a little over the whole training length and encode coarse, long-range order.

The slow pairs are the vulnerability. Because they barely move across the entire trained range, the model has only ever seen them at small angles. Extend the context several times over and those slow pairs rotate to angles several times larger than anything in training — a region of the rotation the model has no experience with. The query-key geometry there is out of distribution, and attention, which was tuned on the trained angles, breaks down.

**RoPE's low-frequency dimensions barely rotate over the training length, so extending the context extrapolates them to angles the model never trained on — out of distribution — and attention degrades before the new length is reached.**

## Concepts

Fix the picture of the spectrum. For a head dimension d, the pairs rotate at frequencies base to the power minus-two-i-over-d, so pair 0 rotates at frequency 1 (fast) and the last pair at the smallest frequency (slow). Over the training length L, the fast pair sweeps an angle of L radians or more — many turns — while the slow pair sweeps only L times its tiny frequency, a small fraction of a turn.

<svg role="img" aria-label="Two dials for the same training length. The high-frequency dial has its hand swept most of the way around, many turns. The low-frequency dial has its hand barely moved from the start, a small wedge. A label notes the slow hand has seen only small angles." viewBox="0 0 440 150">
<text x="110" y="18" fill="var(--muted)" font-size="9" text-anchor="middle">high frequency: many turns</text>
<circle cx="110" cy="80" r="45" fill="none" stroke="var(--line)"/>
<line x1="110" y1="80" x2="110" y2="38" stroke="var(--grid)"/>
<line x1="110" y1="80" x2="145" y2="100" stroke="var(--s1)"/>
<path d="M110 38 A 42 42 0 1 1 143 101" fill="none" stroke="var(--s1)" stroke-dasharray="3 2"/>
<text x="110" y="138" fill="var(--muted)" font-size="8" text-anchor="middle">resolves neighbors</text>
<text x="330" y="18" fill="var(--muted)" font-size="9" text-anchor="middle">low frequency: barely moves</text>
<circle cx="330" cy="80" r="45" fill="none" stroke="var(--line)"/>
<line x1="330" y1="80" x2="330" y2="38" stroke="var(--grid)"/>
<line x1="330" y1="80" x2="342" y2="40" stroke="var(--s2)"/>
<path d="M330 38 A 42 42 0 0 1 342 40" fill="none" stroke="var(--s2)"/>
<text x="330" y="138" fill="var(--muted)" font-size="8" text-anchor="middle">only small angles seen</text>
</svg>
^ Over the training length the high-frequency pair sweeps many turns while the low-frequency pair barely moves — so the model has only ever seen the slow pair at small angles.

Now extend the context to a multiple of L. Extrapolation keeps the same frequencies and lets positions grow, so the slow pair's angle grows in proportion: at four times L, it reaches four times its trained maximum angle — outside everything the model saw. Interpolation instead multiplies every position by L over target before the rotation, which rescales the whole longer range back onto the trained angle range: the position that would have hit four times the trained angle now hits exactly the trained maximum. The model stays in the angle regime it knows.

<svg role="img" aria-label="An arc marked with the trained angle range from zero to a small angle. Extrapolation's marker sits far outside that range, four times out. Interpolation's marker sits exactly at the edge of the trained range." viewBox="0 0 440 130">
<path d="M40 100 A 180 180 0 0 1 400 100" fill="none" stroke="var(--line)"/>
<path d="M40 100 A 180 180 0 0 1 130 30" fill="none" stroke="var(--s1)" stroke-width="4"/>
<text x="70" y="55" fill="var(--s1)" font-size="8">trained range</text>
<circle cx="130" cy="30" r="4" fill="var(--s1)"/>
<text x="128" y="22" fill="var(--s1)" font-size="7" text-anchor="middle">interp lands here</text>
<circle cx="360" cy="52" r="4" fill="var(--s2)"/>
<text x="360" y="44" fill="var(--s2)" font-size="7" text-anchor="middle">extrap: 4x out</text>
<text x="220" y="120" fill="var(--muted)" font-size="8" text-anchor="middle">interpolation keeps the angle inside the trained range; extrapolation shoots past it</text>
</svg>
^ Extrapolation pushes the slow pair's angle far outside the trained range; interpolation rescales positions so the same far token lands exactly at the trained maximum angle.

Interpolation is not free, and the cost falls on the fast pairs. Squeezing positions together means adjacent tokens are now closer in angle than they were in training — the high-frequency pairs, which separated neighbors by a large angle, now separate them by a smaller one, so the fine position resolution the model relied on is coarsened. This is why plain interpolation usually needs a little fine-tuning to recover, and why smarter schemes — NTK-aware scaling and YaRN — interpolate the low frequencies that cause the out-of-distribution problem while sparing the high frequencies that do the resolving.

**Extrapolation grows the slow pair's angle past the trained range in proportion to the context ratio; interpolation scales positions by L over target to return it exactly to the trained range, at the cost of shrinking the fast pairs' adjacent-token angle and thus resolution.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/posinterp-inter-01. The fixture is a RoPE configuration: the rotary base, the head dimension, the trained length, and a longer target length.

```json filename=modules/below-the-prompt/code/posinterp-inter-01/posinterp.json:3-6 COMPLETE
  "base": 10000,
  "head_dim": 4,
  "train_len": 8,
  "target_len": 32
```

The frequencies are geometrically spaced, fastest first.

```python filename=modules/below-the-prompt/code/posinterp-inter-01/posinterp.py:32-34 COMPLETE
def frequencies(base, head_dim):
    """RoPE frequencies: pair i rotates at base**(-2i/head_dim). i=0 is fastest, the last is slowest."""
    return [base ** (-2.0 * i / head_dim) for i in range(head_dim // 2)]
```

The rotation angle at a position is just the position times the frequency.

```python filename=modules/below-the-prompt/code/posinterp-inter-01/posinterp.py:37-39 COMPLETE
def angle(position, freq):
    """The rotation angle RoPE applies to a dimension pair at a given position."""
    return position * freq
```

Interpolation scales every position by the ratio of the two lengths.

```python filename=modules/below-the-prompt/code/posinterp-inter-01/posinterp.py:42-44 COMPLETE
def scale_factor(train_len, target_len):
    """Position interpolation multiplies every position by this, squeezing target_len into train_len."""
    return train_len / target_len
```

Before running it, predict: the target is 4× the trained length, so extrapolating the slowest pair should overshoot its trained maximum angle by 4×, and interpolation should bring it exactly back. Run `--angles`:

```text filename=posinterp.py --angles
ANGLES — max rotation of the lowest-frequency pair (freq 0.0100)
------------------------------------------------------------
  trained (position 8)          : 0.0800 rad
  extrapolated (position 32)     : 0.3200 rad
  interpolated (position 32 * 0.250): 0.0800 rad
------------------------------------------------------------
  extrapolation leaves the trained range; interpolation returns exactly to it
```

The prediction holds exactly. The slowest pair rotates at frequency 0.01, so over the trained length 8 it reaches only 0.08 radians — a sliver, confirming how little the slow pairs move in training. Extrapolating to position 32 rotates it to 0.32 radians, four times the trained maximum and an angle the model never saw. Interpolation scales position 32 by 0.25 back to an effective 8, so it rotates to exactly 0.08 — right at the trained edge. The out-of-distribution angle is gone.

Now the cost. Run `--tradeoff`:

```text filename=posinterp.py --tradeoff
TRADEOFF — adjacent-token angle step on the highest-frequency pair (freq 1.0000)
------------------------------------------------------------
  trained step (distance 1)      : 1.0000 rad
  interpolated step (distance 1) : 0.2500 rad
------------------------------------------------------------
  interpolation squeezes neighbors closer in angle -- finer to resolve (4x)
```

The fastest pair rotates at frequency 1, so in training two adjacent tokens differ by 1.0 radian on it — a large, easy-to-read gap. After interpolation the same two neighbors differ by only 0.25 radians, a quarter of the gap, because positions were squeezed together by 4×. The model now has to distinguish neighboring positions from an angular difference four times smaller than it trained on. That is the price interpolation pays to keep the slow pairs in distribution — better than the collapse extrapolation causes, but not free, which is exactly why it typically needs fine-tuning and why frequency-aware schemes exist.

<svg role="img" aria-label="Two rows of tick marks on an angle axis. The trained row has ticks spaced widely, one radian apart. The interpolated row has ticks spaced four times closer, a quarter radian apart, showing neighbors are harder to resolve." viewBox="0 0 440 130">
<text x="20" y="20" fill="var(--muted)" font-size="9">adjacent-token angle spacing (fast pair)</text>
<text x="70" y="52" fill="var(--ink)" font-size="8" text-anchor="end">trained</text>
<line x1="80" y1="48" x2="400" y2="48" stroke="var(--line)"/>
<line x1="120" y1="42" x2="120" y2="54" stroke="var(--s1)"/>
<line x1="200" y1="42" x2="200" y2="54" stroke="var(--s1)"/>
<line x1="280" y1="42" x2="280" y2="54" stroke="var(--s1)"/>
<line x1="360" y1="42" x2="360" y2="54" stroke="var(--s1)"/>
<text x="240" y="68" fill="var(--muted)" font-size="7" text-anchor="middle">wide gaps — easy to resolve</text>
<text x="70" y="98" fill="var(--ink)" font-size="8" text-anchor="end">interpolated</text>
<line x1="80" y1="94" x2="400" y2="94" stroke="var(--line)"/>
<line x1="120" y1="88" x2="120" y2="100" stroke="var(--s2)"/>
<line x1="140" y1="88" x2="140" y2="100" stroke="var(--s2)"/>
<line x1="160" y1="88" x2="160" y2="100" stroke="var(--s2)"/>
<line x1="180" y1="88" x2="180" y2="100" stroke="var(--s2)"/>
<line x1="200" y1="88" x2="200" y2="100" stroke="var(--s2)"/>
<text x="240" y="114" fill="var(--muted)" font-size="7" text-anchor="middle">4x closer — harder to resolve</text>
</svg>
^ Interpolation squeezes the fast pair's adjacent-token angle from 1.0 to 0.25 radians — neighbors are four times closer in angle and harder to tell apart.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that extrapolation exceeds the trained max angle, that the overshoot factor equals the context ratio, that interpolation stays within the trained range, that interpolation returns exactly to the trained max, and that interpolation shrinks the adjacent-token angle step.

```python filename=modules/below-the-prompt/code/posinterp-inter-01/posinterp.py:84-103 COMPLETE
    trained_max = angle(L, fmin)
    extrap_max = angle(T, fmin)
    interp_max = angle(T * s, fmin)

    extrapolation_out_of_range = extrap_max > trained_max
    print("  extrapolation exceeds the trained max angle = %s (%.4f > %.4f)" % (extrapolation_out_of_range, extrap_max, trained_max))

    ood_factor_is_context_ratio = abs(extrap_max / trained_max - T / L) < 1e-9
    print("  the overshoot factor equals the context ratio = %s (%.1fx = %d/%d)" % (ood_factor_is_context_ratio, extrap_max / trained_max, T, L))

    interpolation_in_range = interp_max <= trained_max + 1e-9
    print("  interpolation stays within the trained range = %s (%.4f)" % (interpolation_in_range, interp_max))

    interpolation_matches_trained_max = abs(interp_max - trained_max) < 1e-9
    print("  interpolation returns exactly to the trained max = %s (%.4f == %.4f)" % (interpolation_matches_trained_max, interp_max, trained_max))

    interp_step = angle(1 * s, fmax)
    train_step = angle(1, fmax)
    interpolation_costs_resolution = interp_step < train_step
    print("  interpolation shrinks the adjacent-token angle step = %s (%.4f < %.4f)" % (interpolation_costs_resolution, interp_step, train_step))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if extrapolation ever stayed in range or interpolation ever missed the trained maximum:

```text filename=posinterp.py --check
SELF-TEST — extrapolation pushes the angle out of the trained range by the context ratio; interpolation returns it exactly, at a resolution cost
----------------------------------------------------------------------------------------------------------------
  extrapolation exceeds the trained max angle = True (0.3200 > 0.0800)
  the overshoot factor equals the context ratio = True (4.0x = 32/8)
  interpolation stays within the trained range = True (0.0800)
  interpolation returns exactly to the trained max = True (0.0800 == 0.0800)
  interpolation shrinks the adjacent-token angle step = True (0.2500 < 1.0000)
```

**The self-test pins the exact quantities that make the argument: the overshoot factor equals the context ratio (so extrapolation's damage scales with how far you push), interpolation returns to the trained max to the last digit, and the same interpolation that fixes the slow pair provably shrinks the fast pair's step — the tradeoff, not a free lunch.**

## Definition of done

You can explain why RoPE is a spectrum of rotation frequencies and what the fast and slow pairs each encode.
You can explain why the low-frequency pairs are the ones extrapolation sends out of distribution.
You can explain why extrapolation's angle overshoot scales with the context-extension ratio.
You can describe position interpolation and why scaling positions by L over target returns the angle to the trained range.
You can explain the resolution cost interpolation pays and why frequency-aware schemes (NTK, YaRN) exist to reduce it.

## Boss fight

Suppose instead of scaling all frequencies equally, you reason about which ones actually need it. Work out why NTK-aware scaling is better. The out-of-distribution problem is only on the low-frequency pairs — the high-frequency pairs complete many rotations within the training length, so their angles at long positions land back in a range the model saw (a rotation is periodic). Plain position interpolation scales every frequency by the same factor, so it needlessly squeezes the high frequencies too, paying the full resolution cost even on pairs that did not need help. NTK-aware scaling changes the rotary base so the scaling is applied mostly to the low frequencies and barely to the high ones — it interpolates where the OOD problem is and extrapolates (safely, via periodicity) where it is not, keeping more of the fine resolution. YaRN refines this further with a per-frequency ramp and an attention-temperature correction. The lesson: the uniform interpolation here is the honest baseline that reveals the mechanism, and the better methods come precisely from noticing that the problem is frequency-specific.

Now the trap that catches people extending context without any interpolation at all. Because RoPE's relative rotation is periodic, a model run past its training length does not fail with an obvious error — it produces fluent-looking output that quietly loses coherence over long ranges, because the slow pairs are reading angles they were never trained on while the fast pairs still look fine. So the failure is silent and gradual, not a crash, which is why it is easy to ship a "long-context" model that is only nominally long-context: it accepts the tokens and generates text, but its use of distant context is degraded in a way a short benchmark never reveals. The defense is to evaluate long-context capability directly (retrieval across the full window, not just perplexity), and to apply and fine-tune an interpolation scheme rather than assuming the architecture extends for free.

**NTK-aware and YaRN scaling beat uniform interpolation by scaling mostly the low frequencies that actually go out of distribution while sparing the high frequencies that do the resolving; and because extrapolation fails silently and gradually, long context must be measured with retrieval across the full window, not assumed.**

## External resources

Chen et al., "Extending Context Window of Large Language Models via Position Interpolation" (2023), introduced the linear position-interpolation scheme this module demonstrates and its fine-tuning recipe.
The NTK-aware scaling discussions and Peng et al., "YaRN: Efficient Context Window Extension of Large Language Models" (2023), develop the frequency-aware refinements the boss fight describes.
The topic's own module on RoPE covers the rotation-by-position mechanism this one extends; the original RoFormer paper (Su et al., 2021) defines RoPE and its relative-position property.
