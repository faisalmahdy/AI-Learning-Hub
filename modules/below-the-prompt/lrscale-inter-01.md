---
id: lrscale-inter-01
title: Scale the learning rate with the batch size — a bigger batch takes fewer steps, so a fixed rate undertrains
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: An optimizer step moves the parameters by the learning rate times the gradient, and over one epoch of N examples a batch of size b makes N/b steps, so the total parameter movement across the epoch is (N/b) times the learning rate times the per-step gradient — that product is how far the model got. Grow the batch to k times b and, over the same N examples, you take only N/(k·b) steps, a k-th as many, because each step consumes k times as much data. With the learning rate unchanged, the total movement over the epoch is a k-th of the small-batch run's, so the large-batch model undertrains: same data, less progress, which is often misattributed to large batches "generalizing worse" when the immediate cause is a learning rate never scaled to match the reduced step count. The linear scaling rule fixes it: multiply the learning rate by k so each of the fewer, larger steps moves k times as far and the per-epoch movement is restored, licensed by the larger batch's gradient being an average over k times more examples and so a lower-variance estimate that tolerates the bigger step (up to a limit past which warmup is needed). On the fixture N is 64, the small batch 8, k is 4 (large batch 32), the base learning rate 0.1, and a representative per-step gradient 1.0: the small run makes 8 steps and moves 0.8, the large run at the same rate makes 2 steps and moves 0.2 (a quarter, undertrained), and the large run at rate 0.4 makes 2 steps and moves 0.8 (matched). The rule: batch size and learning rate are coupled through the step count, so changing one without the other silently changes how far training gets per epoch.
eli5: Imagine walking to a destination by taking steps, where each step is a fixed length. If you take many small steps you cover a certain distance. Now suppose you decide to rest longer and take fewer steps for the same trip — you'll end up short, because fewer steps of the same length don't reach as far. To still arrive, you have to make each of your fewer steps proportionally longer. Training is the same: using a bigger batch means taking fewer, less-frequent steps over the same data, so to get as far you make each step bigger — you turn up the learning rate by the same factor you grew the batch.
---

## Why this module

Practitioners scale batch sizes constantly — to use a bigger GPU, to add more GPUs, to speed up an epoch — and it is easy to think of batch size as a pure performance knob that does not touch the math. It is not. Batch size and learning rate are coupled, and changing the batch alone quietly changes how much the model actually learns per epoch.

The symptom is a large-batch run that trains more slowly or plateaus lower than the small-batch run it replaced, on the same data and the same number of epochs. It is tempting to blame the batch size itself — "large batches hurt generalization" is a real and subtle effect — but the first thing to rule out is the mechanical one: the learning rate was left where it was, and a bigger batch with the old rate simply takes fewer, same-sized steps and gets less far.

**Batch size and learning rate are linked through the number of steps per epoch, so scaling the batch without the rate changes how far training gets.**

## Concepts

Follow the arithmetic of one epoch. An optimizer step updates the parameters by the learning rate times the gradient. In one pass over N examples, a batch of size b produces N/b steps, so the total distance the parameters move across the epoch is the number of steps times the step size: (N/b) × learning_rate × gradient. That total is what determines how much the model changed in the epoch.

Now multiply the batch by k. The same N examples now come in k times fewer batches, so you take N/(k·b) steps — a k-th as many. Each step is still learning_rate × gradient, so the epoch's total movement is (N/(k·b)) × learning_rate × gradient, exactly a k-th of what the small batch achieved. Nothing about the loss changed; you simply took fewer steps of the same size, so you went a fraction of the distance. That is undertraining, and it is invisible unless you compare against the small-batch run.

The linear scaling rule restores the balance by making each step bigger in proportion. Multiply the learning rate by k, and the epoch's total movement becomes (N/(k·b)) × (k · learning_rate) × gradient = (N/b) × learning_rate × gradient — the small-batch total again. Fewer steps, each k times larger, same distance.

Why is the bigger step safe? Because the larger batch's gradient is an average over k times as many examples, so it is a lower-variance, more reliable estimate of the true gradient, and a more reliable direction can bear a larger step without overshooting. This is what licenses the linear rule. It holds across the ordinary range of batch sizes; at very large batches the rule needs a learning-rate warmup to get started and eventually breaks down as the gradient estimate stops improving, but the coupling itself — scale the batch, scale the rate — is the default.

**The epoch's total movement is steps times step size, and a bigger batch cuts the steps by k, so the rate must rise by k to keep the movement the same.**

<svg role="img" aria-label="A chain of factors. Batch times k leads to steps divided by k, which leads to movement divided by k at a fixed learning rate; scaling the learning rate times k cancels it back to the same movement." viewBox="0 0 320 140">
<rect x="0" y="0" width="320" height="140" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">how batch size reaches total movement</text>
<text x="20" y="48" fill="var(--ink)" font-size="10">batch &#215; k</text>
<text x="95" y="48" fill="var(--muted)" font-size="12">&#8594;</text>
<text x="115" y="48" fill="var(--ink)" font-size="10">steps &#247; k</text>
<text x="185" y="48" fill="var(--muted)" font-size="12">&#8594;</text>
<text x="205" y="48" fill="var(--s1)" font-size="10">movement &#247; k</text>
<text x="20" y="86" fill="var(--s2)" font-size="10">fix: learning rate &#215; k</text>
<text x="155" y="86" fill="var(--muted)" font-size="12">&#8594;</text>
<text x="175" y="86" fill="var(--s2)" font-size="10">movement unchanged</text>
<text x="20" y="118" fill="var(--muted)" font-size="9">the &#247; k from fewer steps and the &#215; k from a bigger rate cancel</text>
</svg>
^ A bigger batch shrinks the step count and thus the movement by k; multiplying the learning rate by k is the exact factor that cancels the shrink.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/below-the-prompt/code/lrscale-inter-01/lrscale.py

The fixture is one epoch of 64 examples at a small and a large batch.

```json filename=modules/below-the-prompt/code/lrscale-inter-01/lrscale.json:3-7 COMPLETE
  "n": 64,
  "small_batch": 8,
  "k": 4,
  "base_lr": 0.1,
  "grad": 1.0
```

Steps per epoch is one per batch, and total movement is steps times rate times gradient.

```python filename=modules/below-the-prompt/code/lrscale-inter-01/lrscale.py:30-32 COMPLETE
def steps_per_epoch(n, batch):
    """Number of optimizer steps in one epoch: one per batch."""
    return n // batch
```

```python filename=modules/below-the-prompt/code/lrscale-inter-01/lrscale.py:35-37 COMPLETE
def movement(n, batch, lr, grad):
    """Total parameter movement over one epoch: steps times learning rate times per-step gradient."""
    return steps_per_epoch(n, batch) * lr * grad
```

```text filename=lrscale.py --steps
STEPS — one epoch of 64 examples, base learning rate 0.10
----------------------------------------------------------------
  small batch 8: 8 steps  ->  movement 0.80
  large batch 32: 2 steps  ->  movement 0.20  <- same lr, 4x fewer steps
----------------------------------------------------------------
  the large batch takes a k-th as many steps, so at the same lr it moves a k-th as far
```

The small batch makes 8 steps and moves 0.80. The large batch, at the same 0.10 rate, makes only 2 steps and moves 0.20 — a quarter of the distance, because it took a quarter as many steps of the same size. Same data, same epoch, four times less progress.

<svg role="img" aria-label="Two paths toward a target line. The small batch takes eight short steps and reaches the target. The large batch at the same learning rate takes two short steps and stops a quarter of the way there." viewBox="0 0 320 140">
<rect x="0" y="0" width="320" height="140" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">distance covered in one epoch (target = 0.80)</text>
<line x1="30" y1="120" x2="290" y2="120" stroke="var(--line)"></line>
<line x1="270" y1="40" x2="270" y2="120" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="250" y="36" fill="var(--muted)" font-size="9">target</text>
<text x="20" y="56" fill="var(--s2)" font-size="9">small batch: 8 steps</text>
<line x1="30" y1="64" x2="270" y2="64" stroke="var(--s2)" stroke-width="3"></line>
<text x="20" y="92" fill="var(--s1)" font-size="9">large batch, same lr: 2 steps</text>
<line x1="30" y1="100" x2="90" y2="100" stroke="var(--s1)" stroke-width="3"></line>
<text x="96" y="104" fill="var(--s1)" font-size="9">stops at 0.20</text>
</svg>
^ The small batch's eight steps reach the target; the large batch at the same rate takes two steps of the same length and ends a quarter of the way, undertrained.

## Build

Scaling the learning rate by k restores the distance.

```text filename=lrscale.py --scaled
SCALED — large batch 32 with learning rate scaled by k=4
----------------------------------------------------------------
  scaled learning rate = 0.10 x 4 = 0.40
  large batch 32: 2 steps  ->  movement 0.80
  small batch 8 movement (target) = 0.80
----------------------------------------------------------------
  each of the fewer steps is k times larger, so the total per-epoch movement matches
```

At a learning rate of 0.40 the large batch's 2 steps each move four times as far, so the epoch's total is 0.80 — exactly the small batch's. Two big steps cover the same ground as eight small ones.

<svg role="img" aria-label="The large batch with the scaled learning rate: two long steps that reach the target line, matching the small batch's total distance." viewBox="0 0 320 120">
<rect x="0" y="0" width="320" height="120" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">large batch, lr x k: 2 big steps reach the target</text>
<line x1="30" y1="90" x2="290" y2="90" stroke="var(--line)"></line>
<line x1="270" y1="40" x2="270" y2="90" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="250" y="36" fill="var(--muted)" font-size="9">target</text>
<line x1="30" y1="60" x2="150" y2="60" stroke="var(--s2)" stroke-width="3"></line>
<line x1="150" y1="60" x2="270" y2="60" stroke="var(--s2)" stroke-width="3"></line>
<circle cx="150" cy="60" r="3" fill="var(--panel)" stroke="var(--s2)"></circle>
<text x="70" y="52" fill="var(--s2)" font-size="9">step 1</text>
<text x="190" y="52" fill="var(--s2)" font-size="9">step 2</text>
</svg>
^ With the rate scaled by k, each of the two steps is four times longer, so they reach the same target the eight small steps did.

The self-test ties the shortfall to k and confirms the scaled match.

```python filename=modules/below-the-prompt/code/lrscale-inter-01/lrscale.py:71-79 COMPLETE
    small_move = movement(n, sb, lr, g)
    large_fixed = movement(n, lb, lr, g)
    large_scaled = movement(n, lb, lr * k, g)

    large_undershoots = large_fixed < small_move
    print("  large batch at fixed lr moves less than the small batch = %s (%.2f < %.2f)" % (large_undershoots, large_fixed, small_move))

    undershoot_is_k = abs(small_move / large_fixed - k) < 1e-9
    print("  the shortfall factor equals k = %s (%.2f / %.2f = %g)" % (undershoot_is_k, small_move, large_fixed, small_move / large_fixed))
```

```python filename=modules/below-the-prompt/code/lrscale-inter-01/lrscale.py:81-84 COMPLETE
    scaled_matches = abs(large_scaled - small_move) < 1e-9
    print("  scaling the learning rate by k matches the small batch = %s (%.2f == %.2f)" % (scaled_matches, large_scaled, small_move))

    fewer_steps = steps_per_epoch(n, lb) * k == steps_per_epoch(n, sb)
    print("  the large batch takes a k-th as many steps = %s (%d x %d = %d)" % (fewer_steps, steps_per_epoch(n, lb), k, steps_per_epoch(n, sb)))
```

```text filename=lrscale.py --check
SELF-TEST — the large batch at a fixed learning rate undershoots the small batch's movement by exactly k, while scaling the learning rate by k matches it
----------------------------------------------------------------------------------------------------------------
  large batch at fixed lr moves less than the small batch = True (0.20 < 0.80)
  the shortfall factor equals k = True (0.80 / 0.20 = 4)
  scaling the learning rate by k matches the small batch = True (0.80 == 0.80)
  the large batch takes a k-th as many steps = True (2 x 4 = 8)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  large_undershoots=True  undershoot_is_k=True  scaled_matches=True  fewer_steps=True
```

**undershoot_is_k is the coupling made exact: the movement shortfall is precisely the batch-size factor, so the rate must rise by that same factor to cancel it.**

## Definition of done

You can derive the epoch's total movement as steps × learning_rate × gradient, and show why a k-times-larger batch takes a k-th as many steps.

You can explain why a fixed learning rate then undertrains by exactly k, and why this is easy to misread as a generalization effect rather than a step-count one.

You can state the linear scaling rule (multiply the learning rate by k with the batch) and why the larger batch's lower-variance gradient makes the bigger step safe.

You can name the rule's limits — a warmup is needed at very large batches to get started, and the linear relationship eventually breaks down — so you scale but also validate rather than extrapolating forever.

## Boss fight

You move a training run from one GPU to eight and raise the global batch size 8× to keep each GPU busy, changing nothing else. The run is 8× faster per epoch but the loss after the usual number of epochs is clearly worse than the single-GPU baseline.

First: explain, in terms of steps per epoch and movement, why the loss is worse even though the model saw the same data — and why "8× faster per epoch" and "less progress per epoch" are both true at once.

Then: apply the linear scaling rule. What is the new learning rate, and why does raising it restore per-epoch progress rather than causing the instability you might fear from a large rate — what property of the 8×-larger batch's gradient makes the bigger step reasonable?

Finally: you scale the rate by 8 and the very first few steps diverge (loss spikes to NaN), even though the scaled rate is right for steady state. Explain why the start of training is the dangerous moment for a large scaled rate (the gradients are largest and least reliable early), and what warmup does to get past it — and why warmup is a fix for the transient, not evidence the linear rule is wrong.

## External resources

The paper "Accurate, Large Minibatch SGD" (Goyal et al.) states and validates the linear scaling rule at ImageNet scale, and introduces the learning-rate warmup precisely for the early-training instability the boss fight raises.

Any optimization reference's treatment of minibatch SGD derives the gradient's variance shrinking as 1/batch_size, which is the fact that justifies taking a proportionally larger step with a larger batch.
