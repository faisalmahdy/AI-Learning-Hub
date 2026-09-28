---
id: zeroinit-inter-01
title: Zero-initialize the last layer of each residual branch so every block starts as the identity — a nonzero branch perturbs the signal and the perturbation compounds with depth
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: A residual block computes x + f(x): the input passes through on the skip connection, and the residual branch f adds a correction. What f(x) is at the very start of training depends entirely on how f's last layer is initialized. With standard random init, f(x) is a nonzero perturbation of x, so the block scales its input by roughly (1 + branch_gain) rather than preserving it. One block's small perturbation is harmless, but stacked depth multiplies the signal by (1 + branch_gain) once per block, so the magnitude grows as (1 + gain) to the depth — the same exponential-in-depth compounding that makes plain initialization scale dangerous, now riding on the residual path. Zero-initializing the final layer of each residual branch removes the perturbation at its source: f(x) is exactly zero at init, every block computes x + 0 = x, and the whole network — however deep — is the identity function at step zero, so depth becomes free at initialization and each branch learns to add its correction starting from nothing. On a fixture with a signal of 1.0 and branch gain 0.1, standard init reaches about 2.59 at depth 10 and 117 at depth 50, while zero-init stays exactly 1.0 at any depth.
eli5: Imagine a message whispered down a long line of people, where each person is supposed to pass it along unchanged and quietly add their own small note at the end. If everyone starts by adding a note that makes it a bit louder, then after ten people it is noticeably louder and after fifty it is a deafening roar — a tiny change per person, multiplied by a very long line. The fix is to have everyone start by adding nothing at all: they pass the message along exactly as they heard it, so it arrives at the end at the same volume no matter how long the line is. Only later, once training begins, does each person gently start adding their own small note. Zero-initializing a residual branch is that same rule: begin by adding nothing, so a very deep network starts out passing its signal through untouched.
---

## Why this module

Residual networks are what let us stack hundreds of layers, and the reason is usually explained as the backward pass: the skip connection's +1 carries the gradient straight through, so it does not vanish with depth. That is true and it is a different module. This one is about the forward pass at step zero, before any gradient has flowed at all.

The question is what a freshly-initialized deep residual network computes on its very first input. You might hope it is close to the identity — signal in, roughly the same signal out — so that training starts from a calm, well-behaved state. Whether it actually is depends on one detail: how the last layer of each residual branch is initialized.

With ordinary random init, each branch outputs a small nonzero perturbation, and a small per-block perturbation does not stay small when you stack it. It compounds, block after block, exactly the way a per-layer gain compounds through a plain network — except now it is happening along the residual path that was supposed to be the safe one. This module builds the block both ways and runs the signal through a deep stack to show one exploding and one holding still.

<svg role="img" aria-label="A deep stack of residual blocks with a signal entering at the top at magnitude 1.0. On the left, standard init multiplies by 1.1 at each block and the signal leaves the bottom at 117. On the right, zero-init leaves each block unchanged and the signal leaves at 1.0" viewBox="0 0 440 160">
<text x="112" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">standard init</text>
<text x="327" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">zero-init</text>
<text x="112" y="34" fill="var(--ink)" font-size="9" text-anchor="middle">in: 1.0</text>
<text x="327" y="34" fill="var(--ink)" font-size="9" text-anchor="middle">in: 1.0</text>
<rect x="62" y="42" width="100" height="20" fill="var(--panel)" stroke="var(--line)"/>
<rect x="62" y="66" width="100" height="20" fill="var(--panel)" stroke="var(--line)"/>
<rect x="62" y="90" width="100" height="20" fill="var(--panel)" stroke="var(--line)"/>
<text x="180" y="80" fill="var(--s2)" font-size="9">&#215;1.1 each</text>
<rect x="277" y="42" width="100" height="20" fill="var(--panel)" stroke="var(--line)"/>
<rect x="277" y="66" width="100" height="20" fill="var(--panel)" stroke="var(--line)"/>
<rect x="277" y="90" width="100" height="20" fill="var(--panel)" stroke="var(--line)"/>
<text x="395" y="80" fill="var(--s1)" font-size="9">+0 each</text>
<text x="112" y="130" fill="var(--s2)" font-size="10" text-anchor="middle">out: 117 (depth 50)</text>
<text x="327" y="130" fill="var(--s1)" font-size="10" text-anchor="middle">out: 1.0 (any depth)</text>
</svg>
^ The same input signal down a deep stack: standard init multiplies it at every block and it explodes with depth; zero-init leaves every block the identity and it exits unchanged.

**A residual network's behavior at initialization is set by how each branch's last layer is initialized: nonzero, and the block is not the identity, so the signal drifts and compounds with depth; zero, and every block is the identity and the whole network passes its signal through untouched.**

## Concepts

Start with a single residual block. It computes x + f(x), where x flows through unchanged on the skip connection and f is the residual branch — some layers ending in a final linear layer. At initialization f's weights are random, so f(x) is a nonzero function of x, and to a first approximation it is a small multiple of the input: the block outputs about x + gain·x = x·(1 + gain). The block scales its input rather than preserving it.

For one block, a gain of a tenth is nothing. The trap is depth. Stack N blocks and each one multiplies by (1 + gain), so the signal comes out multiplied by (1 + gain) to the Nth power. That is exponential in depth: a factor that is negligible at one block is a large multiplier through fifty, and the network's activations have already drifted or blown up before the first gradient step. This is the same compounding that makes initialization scale matter in a plain network — it does not disappear just because there is a skip connection; it rides on the branch.

<svg role="img" aria-label="A residual block: input x splits into a skip connection that passes through unchanged and a residual branch f; the two are added to give x plus f of x. Two versions shown: standard init where the branch outputs a nonzero perturbation so the block scales the signal, and zero-init where the branch outputs zero so the block is the identity" viewBox="0 0 440 170">
<text x="220" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">a residual block computes  x + f(x)</text>
<rect x="20" y="30" width="185" height="110" fill="var(--panel)" stroke="var(--line)"/>
<text x="112" y="48" fill="var(--ink)" font-size="10" text-anchor="middle">standard init</text>
<text x="112" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">branch f(x) = nonzero</text>
<text x="112" y="88" fill="var(--muted)" font-size="9" text-anchor="middle">block: x + gain&#183;x</text>
<text x="112" y="106" fill="var(--s2)" font-size="9" text-anchor="middle">scales by (1 + gain)</text>
<text x="112" y="126" fill="var(--s2)" font-size="9" text-anchor="middle">compounds with depth</text>
<rect x="235" y="30" width="185" height="110" fill="var(--panel)" stroke="var(--line)"/>
<text x="327" y="48" fill="var(--ink)" font-size="10" text-anchor="middle">zero-init</text>
<text x="327" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">branch f(x) = 0</text>
<text x="327" y="88" fill="var(--muted)" font-size="9" text-anchor="middle">block: x + 0</text>
<text x="327" y="106" fill="var(--s1)" font-size="9" text-anchor="middle">the identity</text>
<text x="327" y="126" fill="var(--s1)" font-size="9" text-anchor="middle">unchanged at any depth</text>
</svg>
^ The same block, two initializations: a nonzero branch scales the signal and the scaling compounds with depth; a zero branch leaves the block equal to its input.

The fix targets the source. If the final layer of each residual branch is initialized to zero, then f(x) is exactly zero at initialization — the branch outputs nothing. Every block computes x + 0 = x, the identity, and the entire network, however deep, is the identity function at step zero. The signal passes through untouched, the activations are exactly the input's, and training begins from a stable point instead of from a signal that depth has already corrupted.

This is why depth becomes free at initialization: adding more blocks cannot change the output when every branch outputs zero. The skip connection alone carries the signal at the start, and each branch begins contributing nothing, then learns to move its correction away from zero. Much of what lets residual networks be trained at hundreds of layers is that they start out doing nothing harmful.

**Zero-initializing the last layer of each residual branch makes f(x) = 0 at init, so every block is x + 0 = x and the network is the identity at any depth — while a nonzero branch scales the signal by (1 + gain) per block, compounding to (1 + gain) to the depth.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/zeroinit-inter-01. The fixture is an input signal magnitude, the residual branch's effective gain under standard init, and two depths — a shallow one and a deep one.

```json filename=modules/below-the-prompt/code/zeroinit-inter-01/zeroinit.json:3-6 COMPLETE
  "x0": 1.0,
  "branch_gain": 0.1,
  "depth": 10,
  "deep_depth": 50
```

Propagating the signal through the stack is one loop: each block replaces x with x + gain·x, which is x·(1 + gain).

```python filename=modules/below-the-prompt/code/zeroinit-inter-01/zeroinit.py:34-39 COMPLETE
def propagate(x0, branch_gain, depth):
    """Signal after `depth` residual blocks x -> x + gain*x = x*(1+gain)."""
    x = x0
    for _ in range(depth):
        x = x + branch_gain * x
    return x
```

Standard init runs that loop with the fixture's nonzero gain — the branch adds a real perturbation at every block.

```python filename=modules/below-the-prompt/code/zeroinit-inter-01/zeroinit.py:42-44 COMPLETE
def standard(x0, branch_gain, depth):
    """Standard init: the residual branch has a nonzero gain."""
    return propagate(x0, branch_gain, depth)
```

Zero-init runs the exact same loop with a gain of zero — the branch's last layer is zero, so it outputs nothing and each block is the identity.

```python filename=modules/below-the-prompt/code/zeroinit-inter-01/zeroinit.py:47-49 COMPLETE
def zero_init(x0, depth):
    """Zero-init: the branch's last layer is zero, so its gain is 0 -- each block is the identity."""
    return propagate(x0, 0.0, depth)
```

Before running it, predict: with gain 0.1, ten blocks should scale the signal by 1.1 to the tenth, a bit under 2.6, and fifty blocks by 1.1 to the fiftieth, over a hundred — while zero-init should read exactly 1.0 both times. Run `--propagate`:

```text filename=zeroinit.py --propagate
PROPAGATE — signal of 1.0 through residual blocks (branch gain 0.1)
--------------------------------------------------------
  depth   standard init      zero-init
  10      2.5937             1.0000
  50      117.3909           1.0000
--------------------------------------------------------
  standard init drifts and then explodes with depth; zero-init holds at 1.0
```

The prediction holds. Standard init reaches 2.5937 at depth 10 and 117.3909 at depth 50 — a signal that started at 1.0 is over a hundred times larger by the bottom of a fifty-block stack, purely from initialization, before a single step of training. Zero-init reads 1.0000 at both depths, because every block passed the signal through unchanged.

The growth is worth seeing as depth ramps up, because it is not linear — it is exponential. Run `--depth`:

```text filename=zeroinit.py --depth
DEPTH — standard-init output as the stack grows (zero-init stays 1.0)
--------------------------------------------------
  depth   standard init
  0       1.0000
  5       1.6105
  10      2.5937
  25      10.8347
  50      117.3909
--------------------------------------------------
  the growth is (1+gain)^depth -- exponential in depth
```

At depth 0 the signal is the input, 1.0. Each row multiplies by 1.1 five or fifteen or twenty-five more times, and the numbers pull away fast: 1.61, 2.59, 10.83, 117. The gap between the two initializations is not a constant offset — it widens without bound as the network gets deeper, which is exactly why the choice matters most for the deepest models.

<svg role="img" aria-label="Standard-init output rising steeply and accelerating with depth from 1.0 at depth 0 to 117 at depth 50, while zero-init stays flat at 1.0 across every depth" viewBox="0 0 440 160">
<line x1="45" y1="130" x2="410" y2="130" stroke="var(--line)"/>
<line x1="45" y1="20" x2="45" y2="130" stroke="var(--line)"/>
<text x="30" y="30" fill="var(--muted)" font-size="9" text-anchor="middle">117</text>
<text x="30" y="128" fill="var(--muted)" font-size="9" text-anchor="middle">1.0</text>
<text x="225" y="150" fill="var(--muted)" font-size="9" text-anchor="middle">depth  0 &#8594; 50</text>
<path d="M45 129 L 82 128 L 118 126 L 191 121 L 300 100 L 405 25" fill="none" stroke="var(--s2)"/>
<text x="300" y="60" fill="var(--s2)" font-size="9">standard init</text>
<line x1="45" y1="129" x2="405" y2="129" stroke="var(--s1)"/>
<text x="120" y="122" fill="var(--s1)" font-size="9">zero-init (flat at 1.0)</text>
</svg>
^ Standard init accelerates away with depth as (1 + gain) to the depth; zero-init holds flat at the input value no matter how deep the stack.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that standard init drifts the signal off the input at the shallow depth, that going deeper compounds that drift, that the deep output matches the closed-form (1 + gain) to the depth, that zero-init equals the input exactly (the identity), and that zero-init gives the same output at both depths (depth-invariant).

```python filename=modules/below-the-prompt/code/zeroinit-inter-01/zeroinit.py:86-99 COMPLETE
    standard_drifts = abs(s_shallow - x0) > 1e-9
    print("  standard init: the signal drifts from the input = %s (%.4f vs %.1f)" % (standard_drifts, s_shallow, x0))

    standard_compounds = s_deep > s_shallow
    print("  standard init: deeper compounds the drift = %s (%.2f at %d > %.2f at %d)" % (standard_compounds, s_deep, dd, s_shallow, d))

    standard_matches_formula = abs(s_deep - x0 * (1 + g) ** dd) < 1e-6
    print("  standard init: output equals (1+gain)^depth = %s" % standard_matches_formula)

    zeroinit_is_identity = abs(z_shallow - x0) < 1e-12
    print("  zero-init: the signal equals the input (identity) = %s (%.4f)" % (zeroinit_is_identity, z_shallow))

    zeroinit_depth_invariant = abs(z_deep - z_shallow) < 1e-12
    print("  zero-init: the output is the same at any depth = %s (%.4f == %.4f)" % (zeroinit_depth_invariant, z_deep, z_shallow))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if standard init ever stopped compounding or if zero-init ever drifted off the identity:

```text filename=zeroinit.py --check
SELF-TEST — standard init compounds the signal with depth; zero-init leaves it the identity at any depth
----------------------------------------------------------------------------------------------------------------
  standard init: the signal drifts from the input = True (2.5937 vs 1.0)
  standard init: deeper compounds the drift = True (117.39 at 50 > 2.59 at 10)
  standard init: output equals (1+gain)^depth = True
  zero-init: the signal equals the input (identity) = True (1.0000)
  zero-init: the output is the same at any depth = True (1.0000 == 1.0000)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  standard_drifts=True  standard_compounds=True  standard_matches_formula=True  zeroinit_is_identity=True  zeroinit_depth_invariant=True
```

**The self-test pins zero-init to the exact identity with a tolerance of a trillionth and pins standard init to the closed-form (1 + gain) to the depth — so it distinguishes a genuine identity block from a branch that merely happens to be small, and confirms the growth is the exponential the theory predicts.**

## Definition of done

You can explain what a residual block computes at initialization and why the answer depends on how the branch's last layer is initialized.
You can explain why a small per-block perturbation is harmless at one block but compounds to (1 + gain) to the depth across a deep stack.
You can explain why zero-initializing the branch's last layer makes each block the identity and the whole network the identity at step zero, at any depth.
You can state why this makes depth "free" at initialization and why that helps very deep residual networks train.
You can distinguish this forward-pass argument at initialization from the separate backward-pass argument for why the skip connection carries the gradient.

## Boss fight

Suppose you zero-initialize the branch's last layer, so the block is the identity at step zero — and now training starts and gradients flow. A tempting worry is that a zero-initialized layer is a dead end: if its output is zero, is its gradient zero too, so it can never learn? Reason it through. The last layer's weights are zero, but its inputs — the activations from earlier in the branch — are not, and the gradient with respect to those weights is the upstream gradient times those nonzero inputs. So the weight gradient is generally nonzero, the layer receives a real update on the first step, and the branch starts contributing from the very next step. Zero-init is a zero output, not a zero gradient; the branch is dormant at init, not permanently disabled.

Now a subtler design point: which layer of the branch you zero, and why the last one specifically. If you instead zeroed the branch's first layer, its output would be zero and, in a typical branch, everything downstream of it would be zero too — so the branch output would also be zero at init, seemingly the same effect. But then the first layer's own input gradient can be killed by the zeroed weights sitting after it, and you have made the branch harder to wake up. Zeroing only the final layer gives you the identity block at init while leaving every earlier layer randomly initialized and fully connected to its gradient, so the branch is poised to start learning immediately. The rule is precise for a reason: zero the last layer of the branch, not the branch.

**A zero-initialized final layer has zero output but nonzero weight gradient, so the branch wakes up on the first step; and zeroing the last layer rather than an earlier one gives the identity block at init while keeping the rest of the branch primed to learn.**

## External resources

Goyal et al., "Accurate, Large Minibatch SGD" (2017), popularized zero-initializing the last BatchNorm gamma in each residual block so the block starts as the identity, and reports it helping large-scale training.
Zhang, Dauphin, and Ma, "Fixup Initialization" (2019), shows deep residual networks can be trained without normalization by carefully scaling and zero-initializing branch layers, and analyzes the depth-compounding of the signal directly.
The topic's own modules on initialization scale and on the residual connection cover the neighboring pieces: setting the per-layer gain to one, and why the skip connection's +1 carries the gradient through depth.
