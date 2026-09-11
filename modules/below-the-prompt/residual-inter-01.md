---
id: residual-inter-01
title: Add a residual connection or the gradient vanishes through depth — the +1 identity is the highway
topic: below-the-prompt
level: intermediate
status: ready
time: 22 min
summary: Backprop multiplies the gradient by each layer's local derivative, so in a plain deep stack of factors below 1 the gradient shrinks exponentially and the early layers stop learning. A residual layer's derivative is 1 + branch — the +1 carries the gradient straight through. At 20 layers the plain gradient is 0.0008; the residual is 6.73.
eli5: To send a message back through a long line of people, each person passes it on a little quieter. After twenty people it's a whisper no one can hear. A skip connection is a megaphone wire running straight down the line: the message travels it undiminished, so even the first person hears it clearly.
---

## Why this module

The reason you can stack a hundred transformer layers and train them is one addition per layer, and without it the whole tower is untrainable.

Training works by backpropagation: the gradient of the loss flows from the output back to every parameter, telling each how to change. As it flows backward through a layer, it gets multiplied by that layer's local derivative. Through a deep stack, the gradient reaching the early layers is therefore the product of all the layers' derivatives above it. And here is the problem: those derivatives are typically a bit less than one, and a product of numbers less than one shrinks exponentially. Twenty layers of ×0.7 and the gradient arriving at the input is 0.7²⁰ — under a thousandth of what it started as. The early layers receive almost no gradient, so they barely update, so they never learn. This is the vanishing gradient, and it is why, before the fix, simply stacking more layers made networks worse, not better.

The fix is the residual connection, and it is almost insultingly simple. Instead of a layer computing y = f(x), it computes y = x + f(x): it adds its input back to its output. That changes the layer's local derivative from f'(x) to 1 + f'(x). The +1 is an identity path — a direct wire from output back to input — and the gradient flows down it undiminished no matter what the branch f is doing. So instead of multiplying by a shrinking factor at each layer, the gradient multiplies by something at least around one, and it survives all the way down.

We will send a gradient through a twenty-layer stack both ways. Plain, it arrives as 0.0008 — vanished. With residuals, it arrives as 6.73 — alive and well. And then we will remove just the +1 from the residual and watch the gradient collapse to 1e-20, proving that it was the identity highway, not the branch, doing the work.

**Backprop multiplies the gradient by each layer's derivative, so a plain deep stack shrinks it to nothing; the residual's +1 identity is a direct wire that carries the gradient through undiminished.**

## Concepts

Start with why the product shrinks. The gradient at the input is the chain rule unrolled over the whole stack: multiply the loss's sensitivity to the last layer by the last layer's sensitivity to the one before, and so on down. Each of those factors is a layer's local derivative. If every factor is 0.7, the product over N layers is 0.7ᴺ, which heads to zero exponentially. If every factor were 1.3, the product would explode to infinity instead — the exploding gradient, the same problem mirrored. The knife-edge you want is factors near 1, so the gradient neither vanishes nor explodes as it travels through depth. A plain stack has no mechanism to sit on that edge; its factors are whatever the weights happen to make them, usually below one after initialization and normalization.

The residual connection puts you on the edge by construction. Writing y = x + f(x) means the layer's output is its input plus a learned adjustment. Differentiate: dy/dx = 1 + f'(x). The 1 comes from the identity term x, and it is not learned and cannot be trained away — it is always exactly one. So the layer's factor is one plus whatever the branch contributes. Even if the branch derivative f'(x) is tiny or negative, the factor stays near one, and the product of factors-near-one over many layers stays near one rather than decaying. The gradient has, in effect, a direct route from the loss to every layer that skips all the multiplying.

That is why the identity, not the branch, is the load-bearing part. The branch f is where the layer does its actual work — it learns the transformation. But the branch alone, without the +1, would multiply the gradient by a small number each layer and vanish just like a plain stack. The +1 is what guarantees a floor. You can see this by counterfactual: take the residual factor 1.1 and strip the identity, leaving just the 0.1 branch, and the gradient goes from healthy to 0.1²⁰ = 1e-20, deader than the plain stack. The residual's magic is entirely in the term that does no learning.

This is the architectural reason deep learning is deep. Residual connections — introduced by ResNet for vision and adopted by every transformer — are what let gradients reach the bottom of a very tall stack, and without them the "deep" in deep learning tops out at a dozen or so layers. Every transformer block wraps its attention and its feed-forward in residual connections for exactly this reason.

**A product of factors below one vanishes and above one explodes; the residual's non-learnable +1 pins each layer's factor near one, giving the gradient a floor that depth cannot erode.**

## Worked example

The fixture is the stack's shape — its depth and the per-layer derivative in each regime.

```json filename=modules/below-the-prompt/code/residual-inter-01/depth.json:7-10 COMPLETE
  "n_layers": 20,
  "plain_jacobian": 0.7,
  "branch_jacobian": 0.1,
  "vanish_threshold": 0.01
```

Twenty layers. A plain layer's derivative is 0.7; a residual layer's branch derivative is 0.1, so its full derivative is 1 + 0.1 = 1.1. A gradient below 0.01 counts as vanished.

```text filename=modules/below-the-prompt/code/residual-inter-01/residual.py --stack
STACK — per-layer gradient factor, plain vs residual (20 layers)
------------------------------------------------------
  plain layer:     y = f(x)      local derivative = 0.70
  residual layer:  y = x + f(x)  local derivative = 1 + 0.10 = 1.10
------------------------------------------------------
  a factor below 1 shrinks the gradient each layer; the +1 keeps it from shrinking.
```

The gradient reaching the input is the product of the per-layer factor over the whole stack — the chain rule as a loop.

```python filename=modules/below-the-prompt/code/residual-inter-01/residual.py:43-48 COMPLETE
def gradient_through(per_layer_jacobian, n_layers):
    """The gradient reaching the input: the product of the per-layer derivative over the whole stack."""
    g = 1.0
    for _ in range(n_layers):
        g *= per_layer_jacobian
    return g
```

The residual stack feeds it 1 + branch; the counterfactual feeds it the branch alone, to isolate what the +1 does.

```python filename=modules/below-the-prompt/code/residual-inter-01/residual.py:56-58 COMPLETE
def residual_gradient(data):
    """Residual stack: each layer's factor is 1 + branch -- the +1 identity carries the gradient."""
    return gradient_through(1 + data["branch_jacobian"], data["n_layers"])
```

```python filename=modules/below-the-prompt/code/residual-inter-01/residual.py:61-63 COMPLETE
def residual_without_identity(data):
    """Counterfactual: the residual branch alone, without the +1 -- shows what the identity was doing."""
    return gradient_through(data["branch_jacobian"], data["n_layers"])
```

Predict before running. Plain: 0.7²⁰. That is a small number — 0.7¹⁰ is about 0.028, squared is about 0.0008. Residual: 1.1²⁰, which grows to about 6.7. Branch-only: 0.1²⁰ = 1e-20, utterly dead. Run it.

```text filename=modules/below-the-prompt/code/residual-inter-01/residual.py --gradient
GRADIENT — magnitude reaching the input through 20 layers (vanished if < 0.01)
------------------------------------------------------------------
  plain (0.7 each):              0.000797923   VANISHED
  residual (1.1 each):           6.727       alive
  residual minus the +1 (0.1):   1e-20   VANISHED
------------------------------------------------------------------
  depth by depth:
     1 layers:  plain 0.7   residual 1.1
     5 layers:  plain 0.16807   residual 1.61
    10 layers:  plain 0.028248   residual 2.59
    20 layers:  plain 0.00079792   residual 6.73
------------------------------------------------------------------
  plain vanishes with depth; residual holds; strip the +1 and the residual vanishes too.
```

The plain gradient arrives as 0.0008 — vanished, four orders of magnitude below where it started. The residual gradient arrives as 6.73 — fully alive. The depth-by-depth rows show the divergence opening up: at one layer they are close (0.7 versus 1.1), but the plain one halves and halves while the residual one holds and grows, and by twenty layers they are separated by a factor of thousands. The branch-only counterfactual at 1e-20 is the clincher: the residual branch by itself is far worse than the plain stack, so everything good about the residual came from the +1.

<svg role="img" aria-label="Three final gradients on a log scale: residual 6.73 alive, plain 0.0008 vanished, residual-without-identity 1e-20 dead" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">gradient at input, 20 layers (log scale)</text>
  <line x1="150" y1="30" x2="150" y2="150" stroke="var(--ink)" stroke-dasharray="3 2"/><text x="120" y="164" font-family="var(--mono)" font-size="9" fill="var(--muted)">1 (start)</text>
  <text x="16" y="52" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">residual</text>
  <rect x="150" y="44" width="60" height="16" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="216" y="56" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">6.73 alive</text>
  <text x="16" y="92" font-family="var(--mono)" font-size="10" fill="var(--ink)">plain</text>
  <rect x="88" y="84" width="62" height="16" fill="var(--s1)" stroke="var(--line)"/><text x="216" y="96" font-family="var(--mono)" font-size="9" fill="var(--s2)">0.0008 vanished</text>
  <text x="16" y="132" font-family="var(--mono)" font-size="10" fill="var(--ink)">no +1</text>
  <rect x="12" y="124" width="138" height="16" fill="var(--s2)" stroke="var(--line)"/><text x="216" y="136" font-family="var(--mono)" font-size="9" fill="var(--s2)">1e-20 dead</text>
</svg>
^ Bars right of the start line survived, left of it decayed: only the residual clears it — strip its +1 and it falls off the chart.

<svg role="img" aria-label="A residual layer: input x flows into a branch f and also along an identity skip connection, and they add to form y equals x plus f of x" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="30" y="90" font-family="var(--mono)" font-size="12" fill="var(--ink)">x</text>
  <circle cx="50" cy="85" r="4" fill="var(--ink)"/>
  <rect x="150" y="35" width="90" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="180" y="57" font-family="var(--mono)" font-size="12" fill="var(--acc-ink)">f(x)</text>
  <line x1="54" y1="85" x2="100" y2="85" stroke="var(--ink)"/>
  <line x1="100" y1="85" x2="100" y2="52" stroke="var(--ink)"/><line x1="100" y1="52" x2="150" y2="52" stroke="var(--ink)"/>
  <path d="M100 85 Q100 130 230 130 Q360 130 360 100" fill="none" stroke="var(--acc-ink)" stroke-width="2"/>
  <text x="180" y="146" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">identity skip (+1) — the gradient highway</text>
  <line x1="240" y1="52" x2="360" y2="52" stroke="var(--ink)"/><line x1="360" y1="52" x2="360" y2="80" stroke="var(--ink)"/>
  <circle cx="360" cy="90" r="14" fill="var(--panel)" stroke="var(--ink)"/><text x="354" y="95" font-family="var(--mono)" font-size="14" fill="var(--ink)">+</text>
  <line x1="374" y1="90" x2="420" y2="90" stroke="var(--ink)"/><text x="426" y="94" font-family="var(--mono)" font-size="12" fill="var(--ink)">y</text>
  <text x="150" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">y = x + f(x),  dy/dx = 1 + f'(x)</text>
</svg>
^ The input takes two paths to the sum: through the branch f, and straight along the identity skip; the skip is the +1 in the derivative that keeps the gradient alive.

<svg role="img" aria-label="Gradient magnitude versus depth on a log scale: the plain curve decays steeply toward zero, the residual curve stays flat and rises, crossing the vanish threshold" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">gradient vs depth (log scale)</text>
  <line x1="50" y1="160" x2="440" y2="160" stroke="var(--line)"/>
  <line x1="50" y1="30" x2="50" y2="160" stroke="var(--line)"/>
  <line x1="50" y1="70" x2="440" y2="70" stroke="var(--s2)" stroke-dasharray="4 3"/><text x="350" y="66" font-family="var(--mono)" font-size="9" fill="var(--s2)">vanish threshold</text>
  <text x="20" y="45" font-family="var(--mono)" font-size="9" fill="var(--muted)">1</text>
  <text x="60" y="176" font-family="var(--mono)" font-size="9" fill="var(--muted)">1</text><text x="430" y="176" font-family="var(--mono)" font-size="9" fill="var(--muted)">20 layers</text>
  <polyline points="70,60 165,55 260,50 430,42" fill="none" stroke="var(--acc-ink)" stroke-width="2"/>
  <circle cx="430" cy="42" r="4" fill="var(--acc-line)"/><text x="330" y="38" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">residual → 6.73</text>
  <polyline points="70,62 165,88 260,110 430,150" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="430" cy="150" r="4" fill="var(--s1)"/><text x="330" y="146" font-family="var(--mono)" font-size="9" fill="var(--ink)">plain → 0.0008</text>
</svg>
^ The plain gradient dives below the vanish threshold as depth grows; the residual gradient stays above it, so the early layers keep getting a usable signal.

## Build

Reproduce the gradients. Pure standard library, so 0.000797923, 6.727, and 1e-20 come out exactly.

Run `--stack` for the factors, `--gradient` for the magnitudes and the depth sweep, `--check` for the gate. The self-test pins all four facts: the plain gradient vanishes, the residual survives, stripping the +1 kills it, and the residual dwarfs the plain.

```python filename=modules/below-the-prompt/code/residual-inter-01/residual.py:100-108 COMPLETE
    p, r, ri = plain_gradient(data), residual_gradient(data), residual_without_identity(data)

    plain_vanishes = p < thr
    print("  the plain deep stack's gradient vanishes = %s (%.6g < %g)" % (plain_vanishes, p, thr))

    residual_survives = r >= thr
    print("  the residual stack's gradient survives = %s (%.4g >= %g)" % (residual_survives, r, thr))

    identity_is_the_cause = ri < thr
    print("  removing the +1 identity makes it vanish too = %s (%.3g < %g)" % (identity_is_the_cause, ri, thr))
```

The `identity_is_the_cause` check is the one that turns a demonstration into a proof. It is not enough to show the residual works and the plain does not — you have to show *why*, and the way to prove it is the +1 is to remove it and watch the residual fail. That counterfactual, `residual_without_identity` vanishing below threshold, rules out the alternative explanation that the branch was doing the work. The branch alone is worse than plain; only with the identity does the stack survive. Here is the full gate.

```text filename=modules/below-the-prompt/code/residual-inter-01/residual.py --check
SELF-TEST — the plain gradient vanishes; the residual survives; the +1 identity is the cause
----------------------------------------------------------------------------------------
  the plain deep stack's gradient vanishes = True (0.000797923 < 0.01)
  the residual stack's gradient survives = True (6.727 >= 0.01)
  removing the +1 identity makes it vanish too = True (1e-20 < 0.01)
  the residual gradient is far larger than the plain one = True (6.727 vs 0.000797923)
----------------------------------------------------------------------------------------
SELF-TEST PASS  plain_vanishes=True  residual_survives=True  identity_is_the_cause=True  residual_beats_plain=True
```

Four True flags. Plain_vanishes: the plain gradient is below threshold. Residual_survives: the residual gradient is above it. Identity_is_the_cause: strip the +1 and the residual dies too. Residual_beats_plain: the residual gradient is thousands of times the plain one. The third flag is the argument — it isolates the identity as the mechanism, so the module claims causation, not just correlation.

**The self-test removes the +1 and shows the residual then vanishes, which is what proves the identity — not the branch — is the mechanism.**

## Definition of done

You are done when you reproduce the gradients and can explain the mechanism from the chain rule.

Concretely: `--gradient` shows plain 0.0008 (vanished) versus residual 6.73 (alive), with the depth sweep showing the gap widening; `--check` prints PASS with four True flags. You can explain why the input gradient is the product of per-layer derivatives, why a product of sub-one factors vanishes exponentially with depth, and why y = x + f(x) makes the derivative 1 + f'(x). You can state which part of that derivative is load-bearing — the non-learnable 1 — and prove it with the branch-only counterfactual. And you can connect it to real architecture: every transformer block wraps its sublayers in residuals for exactly this reason.

The habit to carry: whenever a deep network trains badly or the early layers seem frozen, suspect gradient flow first, and remember that the residual connection's whole job is to keep that flow alive through depth. The +1 is cheap; the depth it buys is not.

## Boss fight

The instructive failure is the one that motivated ResNet in the first place: a deeper network that does worse than a shallower one.

A team stacks a plain network deeper to increase capacity — more layers should mean more power. Instead training error goes up: the fifty-six-layer network is worse than the twenty-layer one, not from overfitting but because it cannot train, its early layers starved of gradient. The intuition "more layers, more capacity, better" is correct about capacity and wrong about trainability, and the gap is the vanishing gradient. ResNet's answer was residual connections, and with them the fifty-six-layer network trains fine and the thousand-layer network becomes possible. The bug was never capacity; it was that the gradient could not reach the parameters that had the capacity.

Your turn, two moves. First, find the depth where the plain stack dies. Keeping the 0.7 factor, solve for the N where 0.7ᴺ drops below the 0.01 threshold: that is N = log(0.01)/log(0.7) ≈ 13 layers. Predict and confirm that a plain stack is fine at ten layers and dead at twenty, while the residual is alive at both — the plain stack has a depth cliff and the residual does not. Second, probe the exploding-gradient mirror. Set the branch factor to 0.5 so the residual factor is 1.5, and predict: 1.5²⁰ is about 3300 — the gradient now explodes instead of vanishing, which is just as untrainable. That shows residuals alone are not the whole answer: they solve vanishing but can overshoot into exploding, which is why real networks pair residuals with normalization (LayerNorm, RMSNorm) to keep each layer's factor genuinely near one. The residual gives the gradient a floor; normalization gives it a ceiling.

## External resources

He, Zhang, Ren, and Sun, "Deep Residual Learning for Image Recognition" (2015), is the origin: it shows the degradation problem — deeper plain nets training worse — and introduces the residual block as the fix, enabling networks of 100+ layers.

For the transformer-specific version, the original "Attention Is All You Need" wraps every sublayer as LayerNorm(x + Sublayer(x)); any annotated-transformer walkthrough shows the residual around both attention and the feed-forward, and the "pre-norm vs post-norm" literature is about where to place the normalization relative to that residual.

For the mathematics of vanishing and exploding gradients, any deep-learning text's treatment of backpropagation through depth (Goodfellow, Bengio, Courville) derives the product-of-Jacobians and the exponential decay or growth this module computes.
