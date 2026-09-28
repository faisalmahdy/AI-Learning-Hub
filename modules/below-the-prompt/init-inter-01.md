---
id: init-inter-01
title: Scale the initial weights by 1/√fan_in — or the signal explodes or vanishes through depth
topic: below-the-prompt
level: intermediate
status: ready
time: 19 min
summary: A linear layer multiplies its input by random initial weights, and for iid weights the output's standard deviation is the input's times √fan_in × w_std — so that factor is a per-layer gain on the signal's magnitude. Stack L layers and the magnitude is multiplied by that gain L times: it grows as gain^L. A gain even slightly above 1 explodes with depth; slightly below 1 decays to nothing. A deep network with an off-scale w_std produces activations that overflow or are effectively zero before training takes one step, and no learning rate fixes it. The fix sets the gain to exactly 1 — w_std = 1/√fan_in. On fan_in 100 (√ = 10), depth 10: w_std 0.1 gives gain 1.0 and the magnitude stays 1.0; 0.3 gives gain 3.0 and reaches 3^10 ≈ 59049; 0.03 gives gain 0.3 and decays to ≈ 6e-6.
eli5: Imagine whispering a message down a long line of people, where each person makes it a bit louder or a bit quieter. If each makes it 3× louder, by the end it is a deafening roar; if each makes it a third as loud, it is silence before it arrives. Only if each passes it along at the same volume does the message survive the whole line. Setting the starting weights to the right size is choosing that same-volume rule.
---

## Why this module

The size of the random weights a network starts with is not a detail you tune later — for a deep network it decides whether any signal survives to the output at all.

Each linear layer multiplies its input by a matrix of weights. When those weights are random and independent, the layer scales the signal's standard deviation by a fixed factor — √fan_in times the weight standard deviation. That factor is a gain, and a stack of layers applies it once per layer. Ten layers with a gain of 3 multiply the signal by 3 ten times; ten with a gain of 0.3 multiply by 0.3 ten times. The first explodes to tens of thousands, the second collapses to millionths — and both happen before a single gradient step, purely from how the weights were drawn.

**Initialization scale compounds exponentially with depth, so a factor that looks harmless at one layer is catastrophic at fifty.**

Get it wrong and the network is broken at birth: activations overflow to infinity and saturate every nonlinearity, or they underflow toward zero and carry no gradient. No learning rate rescues either. The fix is to choose the weight scale so the per-layer gain is exactly 1 — w_std = 1/√fan_in — and the signal's magnitude is preserved layer after layer. This module propagates a signal through a deep stack under three initializations and measures which survives.

## Concepts

The **fan-in** is the number of inputs to a layer's unit — how many terms are summed to produce one output. Summing more independent terms grows the output's variance, which is why fan-in appears in the scale.

The **per-layer gain** is the factor by which one layer multiplies the signal's standard deviation: √fan_in × w_std. It comes from the variance of a sum of fan_in independent products — the variance adds up over the fan_in terms, so the std grows as √fan_in, and each weight contributes its own w_std.

Through **depth** L, the magnitude is the input times gain^L. This is the whole mechanism: an exponential in the number of layers, with the gain as the base. A base above 1 diverges; below 1 vanishes; exactly 1 is preserved.

The **scaled initialization** picks w_std = 1/√fan_in, making √fan_in × w_std = 1 — gain exactly one. This is the core of the LeCun/Xavier/He family; He adds a √2 to compensate for a ReLU discarding half the signal.

The trap is thinking of initialization as a small perturbation that training will wash out. It is not perturbative — it is the base of an exponential in depth. A w_std that is 3× too large is not 3× too much signal at the end; it is 3^L too much.

**The right initialization is the one whose per-layer gain is 1; anything else is an exponential in disguise.**

Picture one layer as a valve on the signal's volume: three settings of the same valve, applied over and over, give three completely different endings.

<svg role="img" aria-label="One layer as a gain valve with settings 0.3, 1.0, 3.0, feeding a chain that shrinks, holds, or grows" viewBox="0 0 300 120" width="300" height="120">
  <rect x="120" y="12" width="60" height="24" fill="none" stroke="var(--line)" stroke-width="1"/>
  <text x="128" y="28" fill="var(--muted)" font-size="8">× gain</text>
  <text x="90" y="55" fill="var(--muted)" font-size="8">setting:</text>
  <text x="150" y="55" fill="var(--muted)" font-size="8">applied L times</text>
  <text x="20" y="78" fill="var(--s2)" font-size="8">0.3 →</text>
  <text x="55" y="78" fill="var(--s2)" font-size="8">shrinks to nothing</text>
  <text x="20" y="95" fill="var(--ink)" font-size="8">1.0 →</text>
  <text x="55" y="95" fill="var(--ink)" font-size="8">holds steady</text>
  <text x="20" y="112" fill="var(--s1)" font-size="8">3.0 →</text>
  <text x="55" y="112" fill="var(--s1)" font-size="8">grows without bound</text>
</svg>
^ The same per-layer gain valve, repeated through depth, is what turns one weight-scale choice into a signal that dies, survives, or explodes.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/init-inter-01/init.py

The fixture is a fan-in, a depth, and three weight scales.

```json filename=modules/below-the-prompt/code/init-inter-01/init.json:1-14 COMPLETE
{
  "_meta": "A deep stack of plain linear layers, each with fan_in inputs, and three ways to pick the standard deviation of the initial random weights. For a linear layer with iid weights, the output std equals the input std times sqrt(fan_in)*w_std -- so that factor is the per-layer GAIN. depth is how many layers the signal passes through; input_std is the magnitude entering layer 1. The question: what is the signal's magnitude after all the layers, for each choice of w_std?",
  "fan_in": 100,
  "depth": 10,
  "input_std": 1.0,
  "inits": {
    "too_small": 0.03,
    "too_big": 0.3,
    "scaled": 0.1
  }
}
```

The gain is one line; propagation is applying it depth times. The scaled std is 1/√fan_in — the value that makes the gain 1.

```python filename=modules/below-the-prompt/code/init-inter-01/init.py:41-58 COMPLETE
def gain(fan_in, w_std):
    """The factor a single linear layer multiplies the signal's std by."""
    return math.sqrt(fan_in) * w_std


def propagate(input_std, fan_in, w_std, depth):
    """The signal magnitude after each layer: multiply by the gain, depth times."""
    g = gain(fan_in, w_std)
    mags, m = [input_std], input_std
    for _ in range(depth):
        m *= g
        mags.append(m)
    return mags


def scaled_std(fan_in):
    """The initialization that makes the per-layer gain exactly 1."""
    return 1.0 / math.sqrt(fan_in)
```

Run `--propagate` and watch the magnitude layer by layer.

```text filename=--propagate
PROPAGATE — signal magnitude by layer (fan_in 100, depth 10, input 1.0)
------------------------------------------------------------------------
  layer:              0        2        4        6        8       10
  too_small   1.00e+00 9.00e-02 8.10e-03 7.29e-04 6.56e-05 5.90e-06
  too_big     1.00e+00 9.00e+00 8.10e+01 7.29e+02 6.56e+03 5.90e+04
  scaled      1.00e+00 1.00e+00 1.00e+00 1.00e+00 1.00e+00 1.00e+00
------------------------------------------------------------------------
  only the scaled init holds steady; the others run away or die out.
```

Three initializations, three fates. The too-small signal halves an order of magnitude every couple of layers and is essentially gone by layer 10; the too-big signal does the mirror image, climbing to 59,000; the scaled one sits flat at 1.0 the whole way down. Same architecture, same input — only the starting weight scale differs.

<svg role="img" aria-label="Log-scale signal magnitude versus depth: too_big rises, too_small falls, scaled stays flat" viewBox="0 0 300 150" width="300" height="150">
  <line x1="35" y1="15" x2="35" y2="120" stroke="var(--grid)" stroke-width="1"/>
  <line x1="35" y1="70" x2="285" y2="70" stroke="var(--grid)" stroke-width="1" stroke-dasharray="2 2"/>
  <text x="5" y="24" fill="var(--muted)" font-size="8">big</text>
  <text x="5" y="73" fill="var(--muted)" font-size="8">1.0</text>
  <text x="5" y="118" fill="var(--muted)" font-size="8">tiny</text>
  <polyline points="45,68 90,55 135,42 180,29 225,20 270,15" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <text x="235" y="14" fill="var(--s1)" font-size="8">too_big</text>
  <polyline points="45,72 90,85 135,98 180,111 225,118 270,120" fill="none" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="230" y="128" fill="var(--s2)" font-size="8">too_small</text>
  <polyline points="45,70 90,70 135,70 180,70 225,70 270,70" fill="none" stroke="var(--ink)" stroke-width="2"/>
  <text x="120" y="66" fill="var(--ink)" font-size="8">scaled (flat)</text>
  <text x="120" y="138" fill="var(--muted)" font-size="8">depth (log-scale magnitude) →</text>
</svg>
^ On a log scale the two off-scale inits are straight lines sloping away from 1.0 — exponential growth and decay — while the scaled init is flat: gain 1 to the power of anything is 1.

## Build

The gain view reduces each init to the number that governs everything: the per-layer gain, and the final magnitude it produces after the full depth.

```python filename=modules/below-the-prompt/code/init-inter-01/init.py:76-85 COMPLETE
def gain_view(data):
    fan_in, depth, x0 = data["fan_in"], data["depth"], data["input_std"]
    print("GAIN — per-layer gain and final magnitude after %d layers" % depth)
    print("-" * 64)
    for name, w_std in data["inits"].items():
        g = gain(fan_in, w_std)
        final = propagate(x0, fan_in, w_std, depth)[-1]
        print("  %-10s w_std %.3f   gain %.2f   final %.3e" % (name, w_std, g, final))
    print("-" * 64)
    print("  gain**depth is the whole story: 1 stays, >1 explodes, <1 vanishes.")
```

Run `--gain`.

```text filename=--gain
GAIN — per-layer gain and final magnitude after 10 layers
----------------------------------------------------------------
  too_small  w_std 0.030   gain 0.30   final 5.905e-06
  too_big    w_std 0.300   gain 3.00   final 5.905e+04
  scaled     w_std 0.100   gain 1.00   final 1.000e+00
----------------------------------------------------------------
  gain**depth is the whole story: 1 stays, >1 explodes, <1 vanishes.
```

The three gains are 0.30, 3.00, 1.00 — and the finals are exactly those raised to the 10th: 0.3^10 ≈ 6e-6, 3^10 ≈ 59049, 1^10 = 1. The scaled init's w_std of 0.100 is 1/√100 = 1/10, which is why its gain is precisely 1. Nothing here is approximate; the outcome is an exponential and the base is the only free choice.

<svg role="img" aria-label="Three per-layer gains 0.3, 1.0, 3.0 and their tenth powers, showing decay, preservation, and explosion" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="20" fill="var(--muted)" font-size="9">gain</text>
  <text x="120" y="20" fill="var(--muted)" font-size="9">gain^10</text>
  <text x="10" y="42" fill="var(--s2)" font-size="9">0.30</text>
  <text x="120" y="42" fill="var(--s2)" font-size="9">≈ 6e-6   (vanishes)</text>
  <text x="10" y="66" fill="var(--ink)" font-size="9">1.00</text>
  <text x="120" y="66" fill="var(--ink)" font-size="9">1.0     (preserved)</text>
  <text x="10" y="90" fill="var(--s1)" font-size="9">3.00</text>
  <text x="120" y="90" fill="var(--s1)" font-size="9">≈ 59049 (explodes)</text>
  <text x="10" y="112" fill="var(--muted)" font-size="8">a tiny gap in the base becomes a chasm at the tenth power</text>
</svg>
^ The three bases 0.3, 1.0, 3.0 look close, but raised to the depth they span eleven orders of magnitude — the exponential turns a small mis-scale into a catastrophe.

## Definition of done

The self-test pins the mechanism: the gain is √fan_in × w_std, the scaled w_std is 1/√fan_in, the scaled init preserves the magnitude, the too-big init explodes, and the too-small init vanishes.

```python filename=modules/below-the-prompt/code/init-inter-01/init.py:94-109 COMPLETE
    gain_is_sqrt_fanin_times_wstd = abs(gain(fan_in, inits["scaled"]) - math.sqrt(fan_in) * inits["scaled"]) < 1e-12
    print("  the per-layer gain is sqrt(fan_in)*w_std = %s" % gain_is_sqrt_fanin_times_wstd)

    scaled_wstd_is_one_over_sqrt = abs(inits["scaled"] - scaled_std(fan_in)) < 1e-12
    print("  the scaled w_std equals 1/sqrt(fan_in) = %s (%.3f vs %.3f)" % (scaled_wstd_is_one_over_sqrt, inits["scaled"], scaled_std(fan_in)))

    scaled_final = propagate(x0, fan_in, inits["scaled"], depth)[-1]
    scaled_preserves = abs(scaled_final - x0) < 1e-9
    print("  the scaled init preserves the magnitude through depth = %s (%.3f -> %.3f)" % (scaled_preserves, x0, scaled_final))

    big_final = propagate(x0, fan_in, inits["too_big"], depth)[-1]
    big_explodes = big_final > x0 * 100
    print("  the too-big init explodes with depth = %s (final %.3e)" % (big_explodes, big_final))

    small_final = propagate(x0, fan_in, inits["too_small"], depth)[-1]
    small_vanishes = small_final < x0 / 100
    print("  the too-small init vanishes with depth = %s (final %.3e)" % (small_vanishes, small_final))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the scaled init preserves the signal; too-big explodes and too-small vanishes with depth
--------------------------------------------------------------------------------------------------------
  the per-layer gain is sqrt(fan_in)*w_std = True
  the scaled w_std equals 1/sqrt(fan_in) = True (0.100 vs 0.100)
  the scaled init preserves the magnitude through depth = True (1.000 -> 1.000)
  the too-big init explodes with depth = True (final 5.905e+04)
  the too-small init vanishes with depth = True (final 5.905e-06)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  gain_is_sqrt_fanin_times_wstd=True  scaled_wstd_is_one_over_sqrt=True  scaled_preserves=True  big_explodes=True  small_vanishes=True
```

**Done means the survival is derived from the gain, not observed: the scaled init's gain is exactly 1 so gain^depth is 1, while the off-scale gains give 3^10 and 0.3^10 — the exponential is the proof.**

## Boss fight

The scaled init here uses 1/√fan_in. Predict whether that exact formula is right once you put a ReLU after each layer. It is tempting to keep 1/√fan_in — it preserved the signal perfectly.

It is close but no longer exact, and the reason is the whole point of He initialization. A ReLU zeroes the negative half of its inputs, which cuts the signal's variance roughly in half at every layer. So a gain of 1 from the linear part becomes an effective gain below 1 after the ReLU, and the signal slowly decays through depth. He init compensates by scaling the weights up by √2 — w_std = √(2/fan_in) — so the linear gain slightly exceeds 1 and cancels the ReLU's halving, restoring an effective gain of 1. The lesson is that the target is always "effective gain 1," and the formula depends on what the nonlinearity does to the variance.

The mirror-image mistake is assuming a single global w_std works everywhere. Fan-in varies by layer — an attention projection and an MLP have different widths — so the correct w_std is per-layer, computed from that layer's fan-in, not one constant reused across the network.

```python filename=modules/below-the-prompt/code/init-inter-01/init.py:56-58 COMPLETE
def scaled_std(fan_in):
    """The initialization that makes the per-layer gain exactly 1."""
    return 1.0 / math.sqrt(fan_in)
```

**Set the weight scale so the effective per-layer gain is 1 — 1/√fan_in for a linear layer, √(2/fan_in) after a ReLU — and compute it from each layer's own fan-in, because the mistake compounds exponentially with depth.**

## External resources

Glorot and Bengio, "Understanding the difficulty of training deep feedforward neural networks" (2010) — the Xavier initialization paper, deriving the variance-preservation condition this module computes.

He et al., "Delving Deep into Rectifiers" (2015) — the √2 correction for ReLU, the exact subject of the boss fight, and the standard init for modern deep nets.

The PyTorch `torch.nn.init` documentation — `kaiming_normal_`, `xavier_normal_`, and their `fan_in`/`fan_out` and gain arguments, showing how these formulas appear in a real framework.
