---
id: checkpoint-inter-01
title: Keep √N activations, not all N — gradient checkpointing trades one extra forward pass for a memory ceiling
topic: below-the-prompt
level: intermediate
status: ready
time: 17 min
summary: Backpropagation through an N-layer network needs each layer's forward activation to compute its gradient, so the naive backward pass holds all N activations at once — and for a deep, wide model the activations, not the weights, are what overflow the accelerator, growing linearly with depth. Storing nothing and recomputing each activation from the input fixes memory but pays N(N+1)/2 recomputes, quadratic. Gradient checkpointing takes the middle: keep only a few evenly spaced activations (checkpoints) and recompute the layers between them on demand during backward. Peak memory is then the checkpoints held plus the one segment being recomputed — about c + N/c for c checkpoints — minimized at c = √N, giving an O(√N) memory ceiling instead of O(N), at the cost of recomputing each non-checkpoint layer once (at most one extra forward pass). On a 64-layer fixture, storing all costs 64 memory units and zero recompute, storing none costs 1 unit but 2080 recomputes, and checkpointing at √64 = 8 costs 16 units for 56 recomputes.
eli5: To retrace your steps back through a long hike, you'd like a photo at every point — but that's a lot of photos to carry. Take a photo only every so often (say every eighth spot), and when you need to remember the bits in between, walk that short stretch again from the last photo. You carry far fewer photos, and you only re-walk each stretch once. Snap a photo at every step and your pack is full; snap none and you re-walk the whole trail from the start every single time. Every-√N spots is the sweet spot.
---

## Why this module

The memory that limits training a deep network is usually not the weights but the activations kept alive for the backward pass, and that memory grows with depth — so a big enough model overflows not because it is too wide but because backprop insists on remembering every layer's output at once.

Backpropagation is a bookkeeping constraint before it is anything else. To compute the gradient at layer i you need that layer's forward activation, so the standard backward pass keeps all N activations in memory from the forward pass until the backward pass consumes them. For a shallow model that is nothing; for a deep, wide transformer it is the dominant memory cost, larger than the parameters, and it scales linearly with depth. Double the layers and you double the activation memory, whether or not you have the accelerator RAM for it. The naive escape — keep nothing, and when the backward pass reaches layer i recompute its activation from the input — trades that memory away for a catastrophic compute bill: recomputing layer i costs i forward steps, and summed over all layers that is N(N+1)/2, quadratic recompute for a linear-memory saving. Store everything and you run out of memory; store nothing and you run out of time.

**Backprop needs each layer's activation, so storing all N is O(N) memory and storing none is O(N²) recompute — neither extreme is affordable, and the linear-memory wall is what stops a deep model before its FLOPs do.**

Gradient checkpointing takes the middle and wins both axes but one. Keep only a handful of evenly spaced activations — the checkpoints — and during the backward pass recompute the layers between two checkpoints on demand, starting from the checkpoint just before them. Peak memory becomes the checkpoints you hold plus the single segment you are actively recomputing: with c checkpoints over N layers each segment is about N/c long, so peak memory is about c + N/c. That sum bottoms out at c = √N, giving a memory ceiling of ~2√N instead of N — a square-root footprint. The compute cost is that every non-checkpoint layer is recomputed exactly once, which is at most one extra forward pass, not a quadratic blowup. This module computes the memory and recompute of all three strategies and finds the √N optimum.

## Concepts

**Activation memory** is the number of layer outputs kept alive for the backward pass. Store-all holds N of them; that is the linear wall.

**Peak checkpoint memory** with c checkpoints is the checkpoints you keep plus the one segment (length ~N/c) you recompute at a time — about c + N/c.

```python filename=modules/below-the-prompt/code/checkpoint-inter-01/checkpoint.py:42-44 COMPLETE
def checkpoint_memory(n, c):
    """Peak activation memory with c checkpoints: the c stored checkpoints plus one active segment of length n/c."""
    return c + math.ceil(n / c)
```

**Recompute** is the extra forward work checkpointing adds: every non-checkpoint layer is recomputed once during backward, so N − c extra layer-forwards — under one full extra forward pass. Compare that to store-none, which recomputes layer i from the input for every i, summing to N(N+1)/2 — quadratic.

<svg role="img" aria-label="Three strategies plotted on memory versus recompute: store-all has high memory and zero recompute, store-none has minimal memory and quadratic recompute, sqrt-checkpointing sits low on both" viewBox="0 0 300 108" width="300" height="108">
  <line x1="30" y1="90" x2="290" y2="90" stroke="var(--grid)"/><line x1="30" y1="14" x2="30" y2="90" stroke="var(--grid)"/>
  <text x="2" y="20" fill="var(--muted)" font-size="7">memory</text><text x="245" y="102" fill="var(--muted)" font-size="7">recompute →</text>
  <circle cx="40" cy="22" r="4" fill="var(--s2)"/><text x="46" y="25" fill="var(--muted)" font-size="7">store all (N mem, 0)</text>
  <circle cx="270" cy="84" r="4" fill="var(--s2)"/><text x="196" y="80" fill="var(--muted)" font-size="7">store none (1 mem, N²)</text>
  <circle cx="90" cy="74" r="4.5" fill="var(--s1)"/><text x="98" y="70" fill="var(--s1)" font-size="7">checkpoint √N (√N mem, ~N)</text>
  <text x="30" y="106" fill="var(--muted)" font-size="8">the middle strategy is low on both axes; the extremes each blow up one</text>
</svg>
^ Store-all pays maximum memory for zero recompute and store-none pays quadratic recompute for minimum memory; √N-checkpointing sits low on both axes, the only affordable point.

**Store-all is O(N) memory, store-none is O(N²) recompute, and checkpointing at √N checkpoints is O(√N) memory for one extra forward pass — the square-root ceiling is what makes a deep model fit.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/checkpoint-inter-01/checkpoint.py

The fixture is a 64-layer network and a checkpoint count of √64 = 8.

```json filename=modules/below-the-prompt/code/checkpoint-inter-01/checkpoint.json:3-4 COMPLETE
  "n_layers": 64,
  "checkpoints": 8
```

Run `--memory` to compare the three strategies.

```text filename=--memory
MEMORY — peak activation memory vs recompute, three strategies (64 layers)
--------------------------------------------------------------------
  strategy            peak memory      recompute (extra layer-forwards)
  store all           64               0
  checkpoint sqrt(N)  16               56
  store none          1                2080
--------------------------------------------------------------------
  checkpointing cuts memory 4x for under one extra forward pass; store-none pays 37x the recompute.
```

Read the three rows as three points on the trade curve. Store-all spends 64 memory units — one per layer — to recompute nothing; it is the fastest and the hungriest. Store-none spends a single memory unit but recomputes 2080 layer-forwards, because it rebuilds every layer's activation from the input each time backward reaches it, and that sum is quadratic in depth. Checkpointing at 8 spends 16 memory units and 56 recomputes: a quarter of store-all's memory, and the recompute is 56, less than the 64 layers of a single forward pass, so under one extra forward. The contrast with store-none is the whole argument — both cut memory, but store-none's compute bill (2080) is 37 times the checkpoint bill (56) for a memory saving of just 15 more units. Checkpointing captures almost all of the memory win at almost none of the compute cost.

<svg role="img" aria-label="Peak memory bars: store-all 64, checkpoint 16, store-none 1, with recompute annotations 0, 56, and 2080" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">peak activation memory (units) · recompute annotated</text>
  <line x1="86" y1="18" x2="86" y2="88" stroke="var(--grid)"/>
  <text x="6" y="32" fill="var(--muted)" font-size="8">store all</text>
  <rect x="86" y="24" width="192" height="12" fill="var(--s2)"/><text x="200" y="34" fill="var(--panel)" font-size="7">64 · recompute 0</text>
  <text x="6" y="54" fill="var(--muted)" font-size="8">checkpoint</text>
  <rect x="86" y="46" width="48" height="12" fill="var(--s1)"/><text x="138" y="56" fill="var(--muted)" font-size="7">16 · recompute 56 (~1 pass)</text>
  <text x="6" y="76" fill="var(--muted)" font-size="8">store none</text>
  <rect x="86" y="68" width="3" height="12" fill="var(--s2)"/><text x="93" y="78" fill="var(--muted)" font-size="7">1 · recompute 2080 (quadratic)</text>
  <text x="6" y="96" fill="var(--muted)" font-size="8">checkpointing takes the memory win of store-none without its quadratic compute</text>
</svg>
^ Store-all's memory bar is 4× the checkpoint bar; store-none shrinks memory to 1 but its recompute (2080) dwarfs the checkpoint recompute (56), so the middle bar is the only affordable one.

## Build

Why 8 checkpoints and not 4 or 16? Run `--tradeoff` to sweep the count.

```text filename=--tradeoff
TRADEOFF — peak memory c + N/c across checkpoint counts (N=64)
--------------------------------------------------
  checkpoints c   peak memory   recompute
  1               65            63
  2               34            62
  4               20            60
  8               16            56  <- min (sqrt N)
  16              20            48
  32              34            32
  64              65            0
--------------------------------------------------
  memory is a U in c: too few checkpoints means big segments, too many means storing them all.
```

Peak memory is a U-shaped function of the checkpoint count, and the bottom is at 8. With too few checkpoints (c = 1) each segment is almost the whole network, so recomputing one segment holds ~64 activations — no better than store-all. With too many (c = 64) you are storing every layer as its own checkpoint, which is store-all again. The memory c + N/c is pulled up at both ends and minimized where the two terms are equal, c = N/c, i.e. c = √N = 8, giving 8 + 8 = 16. This is the exact reason gradient checkpointing is described as a √N-memory method: not because √N is a rough gesture, but because the sum of "checkpoints held" and "segment recomputed" is a textbook minimize-x+k/x that bottoms out at the square root.

```python filename=modules/below-the-prompt/code/checkpoint-inter-01/checkpoint.py:57-59 COMPLETE
def optimal_checkpoints(n):
    """The checkpoint count that minimizes peak memory c + n/c -- the integer nearest sqrt(n)."""
    return min(range(1, n + 1), key=lambda c: checkpoint_memory(n, c))
```

The recompute column tells the other half. It falls steadily as c rises — more checkpoints means fewer layers to recompute — from 63 at one checkpoint to 0 at store-all. So memory and recompute pull in opposite directions along c, and √N is the memory-minimizing point; if recompute were the binding constraint you would push c higher, trading memory back for less recompute. In practice memory is the wall (that is why you reached for checkpointing at all), so you sit near √N and accept the ~one-extra-pass cost. The knob is continuous: checkpoint more aggressively when memory is tight, less when compute is, and the whole family costs at most one extra forward pass regardless of where on the curve you sit.

<svg role="img" aria-label="Peak memory as a U-shaped function of checkpoint count, high at 1 and 64, minimized at 16 memory units when c is 8" viewBox="0 0 300 104" width="300" height="104">
  <line x1="30" y1="86" x2="290" y2="86" stroke="var(--grid)"/><line x1="30" y1="14" x2="30" y2="86" stroke="var(--grid)"/>
  <text x="2" y="20" fill="var(--muted)" font-size="7">memory</text><text x="250" y="100" fill="var(--muted)" font-size="7">checkpoints c →</text>
  <path d="M40 20 L70 52 L110 68 L150 72 L190 68 L230 52 L270 20" fill="none" stroke="var(--s1)" stroke-width="1.5"/>
  <circle cx="150" cy="72" r="3" fill="var(--ink)"/><text x="138" y="84" fill="var(--ink)" font-size="7">c=8, mem 16</text>
  <circle cx="40" cy="20" r="2.5" fill="var(--muted)"/><text x="30" y="16" fill="var(--muted)" font-size="7">c=1: 65</text>
  <circle cx="270" cy="20" r="2.5" fill="var(--muted)"/><text x="248" y="16" fill="var(--muted)" font-size="7">c=64: 65</text>
  <text x="30" y="102" fill="var(--muted)" font-size="8">memory c + N/c is minimized where c = N/c, i.e. c = √N</text>
</svg>
^ Peak memory rises at both ends — big segments when c is small, storing everything when c is large — and bottoms out at c = √64 = 8 for 16 memory units, the √N minimum of c + N/c.

## Definition of done

The self-test pins each strategy's scaling: store-all is linear memory, store-none is quadratic recompute, √N-checkpointing is √N memory for under one extra pass, and √N is the memory-minimizing count.

```python filename=modules/below-the-prompt/code/checkpoint-inter-01/checkpoint.py:94-108 COMPLETE
    store_all_memory = n  # storing every activation costs one memory unit per layer, and recomputes nothing
    store_all_linear = store_all_memory == n and store_all_memory > checkpoint_memory(n, c)
    print("  store-all peak memory equals the depth (linear) = %s (%d, recompute 0)" % (store_all_linear, store_all_memory))

    store_none_quadratic = store_none_recompute(n) > n * n // 2
    print("  store-none recompute is quadratic in depth = %s (%d > %d)" % (store_none_quadratic, store_none_recompute(n), n * n // 2))

    checkpoint_sqrt_memory = checkpoint_memory(n, c) <= 2 * math.isqrt(n) + 1
    print("  sqrt-checkpointing memory is about 2*sqrt(N) = %s (%d <= %d)" % (checkpoint_sqrt_memory, checkpoint_memory(n, c), 2 * math.isqrt(n) + 1))

    recompute_under_one_pass = checkpoint_recompute(n, c) < n
    print("  its recompute is under one extra forward pass (linear) = %s (%d < %d)" % (recompute_under_one_pass, checkpoint_recompute(n, c), n))

    sqrt_is_optimal = optimal_checkpoints(n) == c and c == math.isqrt(n)
    print("  the memory-minimizing checkpoint count is sqrt(N) = %s (%d)" % (sqrt_is_optimal, optimal_checkpoints(n)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — store-all is linear memory; store-none is quadratic recompute; sqrt-checkpointing is sqrt(N) memory, ~1 pass
----------------------------------------------------------------------------------------------------------------------
  store-all peak memory equals the depth (linear) = True (64, recompute 0)
  store-none recompute is quadratic in depth = True (2080 > 2048)
  sqrt-checkpointing memory is about 2*sqrt(N) = True (16 <= 17)
  its recompute is under one extra forward pass (linear) = True (56 < 64)
  the memory-minimizing checkpoint count is sqrt(N) = True (8)
  checkpointing uses far less memory than store-all = True (16 < 64)
```

**Done means the three scalings are proven: store-all costs 64 memory units (linear in depth) for zero recompute, store-none costs 2080 recomputes (quadratic) for one memory unit, and √N-checkpointing costs 16 units (≤ 2√N) for 56 recomputes (under one extra forward pass) — with c = 8 = √64 the count that minimizes the c + N/c memory.**

## Boss fight

Predict the two places the clean √N story bends in a real network. It is tempting to treat every layer as costing the same memory and the same recompute.

The first trap is that layers are not uniform, so evenly spaced checkpoints are not optimal spacing. A transformer block's attention and MLP activations dwarf a layernorm's, and some layers are far cheaper to recompute than others — so the real objective is to place checkpoints to minimize peak memory given each layer's actual activation size and recompute cost, which is a small optimization, not "every √N layers." Cheap-to-store, expensive-to-recompute layers (like a large attention matrix you would rather not recompute) argue for checkpointing around them, not through them. The uniform-cost model here gives the right scaling law and the right intuition, but a production checkpointer profiles per-layer costs and places boundaries accordingly; assume uniformity and you leave memory on the table exactly where the layers are lopsided.

```python filename=modules/below-the-prompt/code/checkpoint-inter-01/checkpoint.py:47-49 COMPLETE
def checkpoint_recompute(n, c):
    """Extra layer-forwards in the backward pass: every non-checkpoint layer is recomputed once."""
    return n - c
```

The second trap is that recompute is not free of correctness hazards, and getting it wrong silently corrupts gradients. Recomputing a layer's forward during backward must reproduce the *exact* forward it did the first time — same weights, same inputs, and crucially the same random state. A layer with dropout, or any stochastic op, samples a mask on the first forward; recompute it without restoring that mask's RNG state and the backward pass differentiates a *different* function than the one that produced the loss, so the gradient is wrong in a way no shape check catches. Correct checkpointing therefore saves and restores the RNG state (and handles nondeterministic kernels) at each recomputed segment. The same care applies to anything with forward-pass side effects — batch-norm running statistics, for instance, must not be updated twice. So the trade is not purely memory-for-compute; it is memory-for-compute-plus-bookkeeping, and the bookkeeping is where subtle training bugs hide. The mechanical rule — recompute the forward from a checkpoint — is only correct if the recomputed forward is bit-for-bit the original, which for stochastic layers means the RNG must be checkpointed too.

**Gradient checkpointing keeps ~√N activations and recomputes the rest, turning O(N) activation memory into an O(√N) ceiling for at most one extra forward pass (memory c + N/c, minimized at c = √N) — but real layers have non-uniform activation size and recompute cost, so optimal checkpoint placement profiles per-layer costs rather than spacing evenly, and the recomputed forward must reproduce the original exactly, which means checkpointing the RNG state for stochastic layers or the gradients silently differentiate the wrong function.**

## External resources

The gradient-checkpointing / "sublinear memory cost" work (Chen et al., "Training Deep Nets with Sublinear Memory Cost") — the original derivation of the √N memory ceiling and the c + N/c trade-off, and the extension to non-uniform layers.

Your framework's activation-checkpointing documentation (for example `torch.utils.checkpoint`) — the practical API, its RNG-state preservation for stochastic layers, and its guidance on where to place checkpoint boundaries.

The companion "the KV cache — reuse the past" and "share key/value heads across query heads" modules — all three are memory-management techniques for large models, trading recompute or storage against the activation and cache memory that, not the parameters, set the practical size limit.
