---
id: prenorm-inter-01
title: Put the LayerNorm inside the residual branch (pre-norm), not on the residual stream — post-norm attenuates the gradient at every layer and vanishes it with depth
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: A transformer layer has three pieces — a sublayer (attention or MLP), a residual connection, and a normalization — and where you put the norm relative to the residual add decides whether a deep model trains. Post-norm, the original Transformer design, computes x = LayerNorm(x + sublayer(x)): the norm sits on the main residual stream, so on the backward pass the gradient flowing toward earlier layers passes through the norm's Jacobian once per layer, which scales it by a factor typically below one — and a number below one raised to the depth shrinks toward zero, so the first layers see a vanishing gradient, training is unstable, and it needs a carefully tuned learning-rate warmup to converge at all. Pre-norm computes x = x + sublayer(LayerNorm(x)): the norm is inside the branch and the residual stream from input to output is a pure identity path, so the gradient flows back along it undiminished — its multiplier on the residual path is exactly one regardless of depth — and deep pre-norm transformers train stably without the delicate warmup. The difference is entirely where the norm sits relative to the residual add, and it is why essentially every modern large transformer uses pre-norm. On a fixture where the post-norm residual path attenuates the gradient by 0.85 per layer and pre-norm keeps it at 1.0, the post-norm input gradient is 0.38 at depth 6, 0.02 at depth 24 (below the vanish threshold), and 0.0004 at depth 48, while pre-norm stays at 1.0 at every depth.
eli5: Think of the residual connection as an express elevator that carries the learning signal from the top of a tall building straight down to the bottom floors. In the good design (pre-norm), the elevator shaft is clear all the way down — the signal arrives at the ground floor at full strength no matter how tall the building. In the original design (post-norm), there's a slightly dimming filter installed on every floor of the shaft, so the signal loses a bit passing each one; in a short building it's fine, but in a tall building it fades to almost nothing by the time it reaches the bottom floors, and those floors barely learn. The fix is to move the filters out of the shaft and into the side rooms, leaving the express elevator clear.
---

## Why this module

The residual connection is the single most important structural reason deep networks train at all: it gives the gradient an identity path back to the early layers, so it does not have to survive being multiplied by every layer's weights on the way down. A transformer keeps that highway, but it also inserts a LayerNorm at every layer, and the question the original Transformer got wrong for depth is whether the norm sits on the highway or beside it.

Post-norm puts it on the highway. Because x = LayerNorm(x + sublayer(x)), the normalization is applied to the residual stream itself, so the identity path is no longer clean — every gradient travelling back down it is filtered through a LayerNorm at each layer. The norm's backward Jacobian scales the gradient, and that scaling, applied once per layer, compounds: a factor below one raised to the number of layers drives the gradient toward zero at the bottom. That is the classic vanishing-gradient problem the residual connection was supposed to solve, reintroduced by putting the norm in the wrong place.

Pre-norm restores the clean highway by moving the norm into the branch: x = x + sublayer(LayerNorm(x)). The residual stream is now a pure sum with nothing on it, and the gradient reaches the first layer undiminished. This module models the gradient reaching the first layer as a function of depth for both orders.

**Post-norm places the LayerNorm on the residual stream, so the backward gradient is attenuated by the norm's Jacobian at every layer and vanishes with depth; pre-norm places it inside the branch, leaving the residual identity path clean so the gradient survives to the first layer.**

## Concepts

The fixture is the per-layer gradient multiplier on the residual path for each order, the depths to evaluate, and the threshold below which the gradient counts as vanished.

```json filename=modules/below-the-prompt/code/prenorm-inter-01/prenorm.json:3-5 COMPLETE
  "residual_multiplier": {"pre_norm": 1.0, "post_norm": 0.85},
  "depths": [6, 12, 24, 48],
  "vanish_threshold": 0.1
}
```

The gradient reaching the first layer is the per-layer residual multiplier raised to the depth — each layer applies its multiplier once. A helper finds the depth at which that gradient first drops below the threshold.

```python filename=modules/below-the-prompt/code/prenorm-inter-01/prenorm.py:32-46 COMPLETE
def input_gradient(multiplier, depth):
    """Gradient magnitude reaching the first layer: the per-layer residual multiplier raised to the depth."""
    return multiplier ** depth


def vanish_depth(multiplier, threshold, max_depth=512):
    """Smallest depth at which the input gradient falls below the threshold (None if it never does)."""
    if multiplier >= 1.0:
        return None
    d = 1
    while d <= max_depth:
        if input_gradient(multiplier, d) < threshold:
            return d
        d += 1
    return None
```

Pre-norm's multiplier is exactly 1.0 — the identity path — so `1.0 ** depth` is 1.0 forever. Post-norm's is 0.85, a stylized stand-in for the norm's sub-unit Jacobian on the residual path, so `0.85 ** depth` decays. The identity-versus-attenuated contrast is the real mechanism; the exact 0.85 is illustrative.

<svg role="img" aria-label="Two residual layers: pre-norm has a clean identity line from input to output with the norm on a side branch, post-norm has the norm sitting on the main line so the gradient passes through it" viewBox="0 0 320 130">
  <text x="14" y="16" font-size="8" fill="var(--s1)">pre-norm: x + sublayer(norm(x))</text>
  <line x1="20" y1="34" x2="300" y2="34" stroke="var(--s1)" stroke-width="2"/><text x="150" y="30" font-size="7" fill="var(--s1)">clean identity path (×1)</text>
  <rect x="120" y="40" width="60" height="14" fill="none" stroke="var(--muted)"/><text x="126" y="50" font-size="6.5" fill="var(--muted)">norm→sublayer</text>
  <line x1="150" y1="40" x2="150" y2="34" stroke="var(--muted)"/>
  <text x="14" y="80" font-size="8" fill="var(--s2)">post-norm: norm(x + sublayer(x))</text>
  <line x1="20" y1="98" x2="120" y2="98" stroke="var(--s2)" stroke-width="2"/>
  <rect x="120" y="91" width="40" height="14" fill="var(--s2)"/><text x="126" y="101" font-size="6.5" fill="var(--panel)">norm</text>
  <line x1="160" y1="98" x2="300" y2="98" stroke="var(--s2)" stroke-width="2"/>
  <text x="120" y="120" font-size="7" fill="var(--s2)">norm sits ON the path (×0.85 each layer)</text>
</svg>
^ In pre-norm the residual line runs unbroken from input to output and the norm hangs off a side branch, so the backward gradient travels the identity path at full strength. In post-norm the norm sits directly on the residual line, so every layer's gradient is scaled passing through it — the attenuation that compounds with depth.

**Pre-norm's residual path is a bare identity (multiplier 1); post-norm's has a norm on it (multiplier below 1) — so the gradient to the first layer is 1 raised to the depth versus a sub-unit number raised to the depth.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the layer-structure choice of a transformer, reduced to a per-layer gradient multiplier so the depth scaling is checkable by hand.

Run `--depth` to see the gradient reaching the first layer.

```text filename=prenorm.py --depth
  depth   pre-norm   post-norm
  6       1.0000     0.3771
  12      1.0000     0.1422
  24      1.0000     0.0202
  48      1.0000     0.0004
```

Pre-norm holds at 1.0 at every depth — the identity path does not scale the gradient, so a 48-layer pre-norm network delivers the same gradient to its first layer as a 6-layer one. Post-norm decays geometrically: 0.38 at 6 layers, 0.14 at 12, 0.02 at 24, and 0.0004 at 48. By 48 layers the first layer receives four ten-thousandths of the gradient the top layer does, so it barely updates — the bottom of a deep post-norm network is effectively frozen unless the learning rate is warmed up and tuned to compensate.

Now `--vanish` scans each variant for the depth where it crosses the threshold.

```python filename=modules/below-the-prompt/code/prenorm-inter-01/prenorm.py:67-69 COMPLETE
    for name in ("pre_norm", "post_norm"):
        vd = vanish_depth(mult[name], thr)
        print("  %-10s  vanishes at depth %s" % (name, vd if vd is not None else "never"))
```

Only one of them has such a depth.

```text filename=prenorm.py --vanish
  pre_norm    vanishes at depth never
  post_norm   vanishes at depth 15
```

Post-norm's gradient falls below the vanish threshold at depth 15 — well within the range of modern transformers, which run to dozens or hundreds of layers. Pre-norm never vanishes, because its multiplier is exactly one. This is the concrete reason the field switched: post-norm can be trained at moderate depth with enough warmup and care, but it fights the architecture the whole way, while pre-norm makes depth free from the gradient's perspective. The residual highway does its job only if nothing is installed on it.

<svg role="img" aria-label="Gradient magnitude versus depth: pre-norm a flat line at 1.0, post-norm a curve decaying through the vanish threshold around depth 15 toward zero" viewBox="0 0 320 120">
  <line x1="30" y1="20" x2="30" y2="100" stroke="var(--line)" stroke-width="1"/>
  <line x1="30" y1="100" x2="300" y2="100" stroke="var(--line)" stroke-width="1"/>
  <text x="2" y="24" font-size="7" fill="var(--muted)">grad</text>
  <text x="270" y="112" font-size="7" fill="var(--muted)">depth</text>
  <line x1="30" y1="30" x2="300" y2="30" stroke="var(--s1)" stroke-width="2"/><text x="240" y="27" font-size="7" fill="var(--s1)">pre-norm 1.0</text>
  <line x1="30" y1="88" x2="300" y2="88" stroke="var(--ink)" stroke-width="0.6" stroke-dasharray="2 2"/><text x="250" y="86" font-size="6.5" fill="var(--ink)">vanish threshold</text>
  <path d="M 30 40 Q 90 78 150 88 T 300 99" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="112" cy="88" r="2.5" fill="var(--s2)"/><text x="96" y="76" font-size="6.5" fill="var(--s2)">vanishes ~depth 15</text>
  <text x="240" y="97" font-size="7" fill="var(--s2)">post-norm</text>
</svg>
^ Pre-norm's gradient is flat at 1.0 for any depth; post-norm's decays and crosses the vanish threshold around depth 15, heading toward zero. Past that depth the early layers of a post-norm network receive too little gradient to learn without heavy warmup.

**Pre-norm delivers the same gradient to the first layer at depth 48 as at depth 6, while post-norm's gradient vanishes below the threshold by depth 15 — depth is free for pre-norm and a fight for post-norm.**

## Build

The self-test establishes the mechanism: pre-norm's residual path is a pure identity (multiplier 1), post-norm's attenuates (multiplier below 1), and pre-norm's gradient stays 1.0 at every depth.

```python filename=modules/below-the-prompt/code/prenorm-inter-01/prenorm.py:81-88 COMPLETE
    prenorm_identity_path = pre == 1.0
    print("  pre-norm's residual path is a pure identity (multiplier 1.0) = %s" % prenorm_identity_path)

    postnorm_attenuates = post < 1.0
    print("  post-norm's residual path attenuates the gradient (multiplier < 1) = %s (%.2f)" % (postnorm_attenuates, post))

    prenorm_gradient_stable = all(abs(input_gradient(pre, d) - 1.0) < 1e-9 for d in depths)
    print("  pre-norm's input gradient stays 1.0 at every depth = %s" % prenorm_gradient_stable)
```

Then the payoff: post-norm's gradient shrinks with depth and vanishes at the deepest network, exactly where pre-norm still survives.

```python filename=modules/below-the-prompt/code/prenorm-inter-01/prenorm.py:90-98 COMPLETE
    postnorm_gradient_decays = input_gradient(post, depths[-1]) < input_gradient(post, depths[0])
    print("  post-norm's input gradient shrinks with depth = %s (%.4f -> %.4f)"
          % (postnorm_gradient_decays, input_gradient(post, depths[0]), input_gradient(post, depths[-1])))

    postnorm_vanishes = input_gradient(post, depths[-1]) < thr
    print("  post-norm's gradient falls below the vanish threshold at the deepest network = %s (%.4f < %.2f)"
          % (postnorm_vanishes, input_gradient(post, depths[-1]), thr))

    prenorm_survives_where_post_vanishes = input_gradient(pre, depths[-1]) >= thr and postnorm_vanishes
    print("  pre-norm survives at a depth where post-norm has vanished = %s" % prenorm_survives_where_post_vanishes)
```

Running the check confirms every clause.

```text filename=prenorm.py --check
  pre-norm's residual path is a pure identity (multiplier 1.0) = True
  post-norm's residual path attenuates the gradient (multiplier < 1) = True (0.85)
  pre-norm's input gradient stays 1.0 at every depth = True
  post-norm's input gradient shrinks with depth = True (0.3771 -> 0.0004)
  post-norm's gradient falls below the vanish threshold at the deepest network = True (0.0004 < 0.10)
  pre-norm survives at a depth where post-norm has vanished = True
```

**The check ties the vanishing gradient to the norm sitting on the residual path (multiplier below 1 compounding with depth), and shows pre-norm's identity path holding the gradient at 1.0 where post-norm has collapsed.**

## Definition of done

Done means post-norm's gradient is shown to decay and vanish with depth while pre-norm's stays constant, traced to whether the norm sits on the residual identity path. The clause that pre-norm survives exactly where post-norm vanishes is the point: the two architectures diverge precisely in the deep regime that matters, so the choice is not cosmetic but the difference between a deep model that trains and one that needs elaborate rescue.

Two clarifications keep this honest and useful. First, the 0.85 per-layer multiplier is a stylized stand-in for the LayerNorm Jacobian's effect on the residual-path gradient; the real per-layer factor depends on the activation scales and is not a fixed constant, and the genuine analysis (from the Pre-LN vs Post-LN papers) shows post-norm's gradient magnitude growing toward the output layers and the effective condition worsening with depth, which is why post-norm needs warmup while pre-norm does not. What is exactly right in the model is the qualitative structure: pre-norm's residual multiplier is identically one (a clean identity path) and post-norm's is not, and only that difference compounds over depth. Second, pre-norm is not free of tradeoffs — because its residual stream accumulates unnormalized sublayer outputs, the stream's magnitude grows with depth and a final LayerNorm is applied before the output, and some very large models revisit the placement (sandwich norms, or normalizing the residual branch's output) to recover a little of post-norm's representational sharpness while keeping pre-norm's trainability. The durable rule for building a deep transformer is to use pre-norm (or a well-justified variant) so the identity path stays clean, and to treat any design that puts a norm directly on the residual stream as one that will fight you at depth.

<svg role="img" aria-label="A summary: pre-norm keeps a clean residual identity path and trains deep stably, post-norm puts the norm on the path and needs warmup and fights depth" viewBox="0 0 320 118">
  <rect x="14" y="22" width="150" height="42" fill="none" stroke="var(--s1)"/>
  <text x="22" y="37" font-size="7.5" fill="var(--s1)">pre-norm</text>
  <text x="22" y="49" font-size="7" fill="var(--ink)">norm inside branch,</text>
  <text x="22" y="58" font-size="7" fill="var(--ink)">clean identity path → deep-stable</text>
  <rect x="176" y="22" width="130" height="42" fill="none" stroke="var(--s2)"/>
  <text x="184" y="37" font-size="7.5" fill="var(--s2)">post-norm</text>
  <text x="184" y="49" font-size="7" fill="var(--ink)">norm on the stream,</text>
  <text x="184" y="58" font-size="7" fill="var(--ink)">vanishes at depth → needs warmup</text>
  <text x="14" y="84" font-size="7.5" fill="var(--muted)">what's exact: pre-norm multiplier ≡ 1; the 0.85 is a stylized post-norm attenuation</text>
  <text x="14" y="104" font-size="7.5" fill="var(--ink)">build deep transformers pre-norm; a norm on the residual stream fights depth</text>
</svg>
^ Pre-norm keeps the norm inside the branch and the residual path a clean identity, so it trains deep stably; post-norm puts the norm on the stream and its gradient vanishes with depth, demanding warmup. The exact fact is that pre-norm's residual multiplier is one; the 0.85 is a stylized post-norm attenuation.

**Done means post-norm's gradient vanishes with depth while pre-norm's holds at 1.0, traced to the norm's placement relative to the residual add — so deep transformers use pre-norm to keep the identity path clean, treating any norm on the residual stream as a fight against depth.**

## Boss fight

A team scales their transformer from 12 to 48 layers, keeping the original post-norm architecture. The 12-layer model trained fine, but the 48-layer model's loss barely moves for the first many steps and then sometimes diverges, and the early layers' weights hardly change from initialization. Lowering the learning rate helps a little but hurts final quality. What is going on, and what is the principled fix?

The symptoms are the signature of post-norm's vanishing gradient at depth. In post-norm (x = LayerNorm(x + sublayer(x))) the normalization sits on the residual stream, so the gradient flowing back to the early layers is attenuated by the norm's Jacobian once per layer; at 12 layers the compounding is mild and the model trains, but at 48 layers the gradient reaching the bottom layers is a tiny fraction of what the top layers see, which is exactly why the early layers' weights barely move from initialization. The unstable start and occasional divergence are the other half of the post-norm depth problem — the gradient scale is badly conditioned across layers, so a learning rate large enough to train the early layers is too large for the late ones (and vice versa), which is why lowering the LR only trades one failure for another and why post-norm has always needed a carefully tuned learning-rate warmup that becomes harder to get right as depth grows. The principled fix is to switch to pre-norm: x = x + sublayer(LayerNorm(x)), which moves the normalization inside the sublayer branch and leaves the residual stream a clean identity path, so the gradient reaches every layer — including the first — undiminished regardless of depth, and the 48-layer model trains stably without a delicate warmup. Add the final LayerNorm before the output head that pre-norm implies (since the residual stream is no longer normalized at the end), and expect to be able to use a more normal learning-rate schedule. Warmup is a patch for a conditioning problem post-norm creates; pre-norm removes the problem. If the team wants to keep some of post-norm's representational sharpness, the modern middle grounds (sandwich/peri-LN normalization, or scaling the residual branch) preserve pre-norm's clean identity path while adding controlled normalization, but the baseline fix for "deep model won't train, early layers frozen" is to stop putting the norm on the residual stream.

## External resources

The pre-LN vs post-LN analysis (Xiong et al., "On Layer Normalization in the Transformer Architecture," and the original Transformer's post-norm design) — the derivation of why post-norm's gradients are large near the output and require warmup while pre-norm's are well-behaved at initialization, the rigorous version of this module's stylized multiplier.

Discussions of normalization placement in large models (pre-norm as the default in GPT-style and most modern LLMs, and variants like sandwich norm, DeepNet's post-norm-with-scaling, and normformer) — how the field settled on keeping the residual identity path clean and the refinements that recover representational quality without reintroducing the depth instability.
