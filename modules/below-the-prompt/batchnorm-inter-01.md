---
id: batchnorm-inter-01
title: Switch batch norm to eval mode at inference — in train mode an example's output depends on its batchmates
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Batch normalization standardizes an activation by subtracting a mean and dividing by a standard deviation, then applying a learned scale and shift — and the subtlety is which mean and standard deviation. During training it uses the statistics of the current mini-batch, which is deliberate but has a consequence that is fine while training and catastrophic at inference: an example's normalized value depends on the other examples in its batch. That is why batch norm also accumulates a running mean and running variance across training, and why at inference the layer must switch to eval mode and use those fixed running statistics, so an example's output depends only on the example. The bug is forgetting to switch — running with batch norm still in train mode at inference — so predictions depend on how requests are batched, the same input scores differently with different neighbors, and a batch of size one has zero variance and collapses every input to the shift parameter beta. On a fixture with running_mean 0 and running_var 1, the example x=2.0 normalizes to a stable 2.0 in eval mode, but in train mode comes out 0.0 batched with [2,0,4] and −1.2247 batched with [2,6,10] — the same input, moved by its batchmates — and a size-1 batch maps any input to 0.0.
eli5: Imagine grading a test by curving each student against the others in the same room. If you always grade a student against the same fixed reference, their score only depends on their own answers — fair and repeatable. But if you curve them against whoever happens to be sitting in the room that day, the same answers get a different grade depending on the neighbors, and if a student takes the test alone in a room, the curve has nothing to compare against and everyone gets the same flat score. Batch normalization at inference is supposed to use the fixed reference it saved during training; the bug is accidentally curving each input against its batchmates, so identical inputs get different answers and a single input gets a meaningless one.
---

## Why this module

Batch norm is a training-time trick that quietly changes what it does between training and inference, and the switch is a mode flag that is easy to forget. Forget it and the model still runs, still returns numbers of the right shape, and is silently wrong in a way that depends on how you happened to group the inputs — the hardest kind of bug to see, because the same code gives different answers to the same input.

Batch normalization standardizes an activation by subtracting a mean and dividing by a standard deviation, then applying a learned scale and shift. The subtlety is which mean and standard deviation. During training, batch norm uses the statistics of the current mini-batch — the mean and variance of the activations across the examples batched together on that step. This is deliberate: it makes the normalization adapt as the network learns, and the noise it injects acts as a mild regularizer. But it has a consequence that is fine during training and catastrophic at inference: an example's normalized value depends on the *other* examples in its batch. The same input, in a different batch, comes out a different number.

That is exactly why batch norm keeps a second set of statistics: a running mean and running variance, accumulated across all of training. At inference the layer is supposed to switch to eval mode and use those fixed running statistics instead of the batch's, so an example's output depends only on the example — deterministic, batch-independent, correct one at a time. The bug is forgetting to switch: running a model with batch norm still in train mode at inference. Now predictions depend on how requests are grouped into batches, the same input scores differently depending on its neighbors, and a batch of size one — the normal case for a single online request — has zero variance, so every input collapses to the shift parameter beta and the feature carries no information. This module scores one example both ways and shows the batch leak.

**Batch norm uses the current batch's statistics in train mode and fixed running statistics in eval mode, so at inference the layer must be in eval mode — otherwise an example's output depends on its batchmates, identical inputs score differently in different batches, and a size-1 batch collapses every input to beta.**

## Concepts

**The transform** is the same in both modes — scale times the standardized value plus shift. Only the mean and variance fed into it change.

```python filename=modules/below-the-prompt/code/batchnorm-inter-01/batchnorm.py:46-48 COMPLETE
def normalize(x, mean, var, data):
    """Batch-norm transform: scale*(x - mean)/sqrt(var + eps) + shift."""
    return data["gamma"] * (x - mean) / math.sqrt(var + data["eps"]) + data["beta"]
```

**Eval mode** feeds in the fixed running statistics accumulated during training, so the output is a function of x alone — the same for any batch.

```python filename=modules/below-the-prompt/code/batchnorm-inter-01/batchnorm.py:51-53 COMPLETE
def eval_mode(x, data):
    """Inference-correct: normalize with the fixed running statistics -- depends only on x."""
    return normalize(x, data["running_mean"], data["running_var"], data)
```

**Train mode** computes the mean and variance from the current batch, so x's output is entangled with its batchmates — correct for a training step, wrong for an inference request.

```python filename=modules/below-the-prompt/code/batchnorm-inter-01/batchnorm.py:56-60 COMPLETE
def train_mode(x, batch, data):
    """Inference-BUG: normalize with THIS batch's mean and variance -- depends on the batchmates."""
    mean = sum(batch) / len(batch)
    var = sum((z - mean) ** 2 for z in batch) / len(batch)
    return normalize(x, mean, var, data)
```

<svg role="img" aria-label="Two paths for normalizing an example: eval mode draws from the fixed running statistics, train mode draws from the current batch, so only the train path is affected by the batchmates" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same transform, two sources of mean/variance</text>
  <rect x="120" y="20" width="60" height="20" fill="none" stroke="var(--line)"/><text x="132" y="34" fill="var(--muted)" font-size="8">example x</text>
  <rect x="10" y="60" width="90" height="22" fill="none" stroke="var(--s1)"/><text x="18" y="74" fill="var(--muted)" font-size="7">running stats (fixed)</text>
  <rect x="200" y="60" width="90" height="22" fill="none" stroke="var(--s2)"/><text x="208" y="74" fill="var(--muted)" font-size="7">this batch's stats</text>
  <rect x="110" y="94" width="80" height="20" fill="none" stroke="var(--ink)"/><text x="122" y="108" fill="var(--muted)" font-size="8">normalized</text>
  <line x1="140" y1="40" x2="90" y2="60" stroke="var(--s1)"/><text x="60" y="52" fill="var(--s1)" font-size="6">eval</text>
  <line x1="160" y1="40" x2="235" y2="60" stroke="var(--s2)"/><text x="212" y="52" fill="var(--s2)" font-size="6">train (bug)</text>
  <line x1="55" y1="82" x2="130" y2="94" stroke="var(--s1)"/>
  <line x1="245" y1="82" x2="170" y2="94" stroke="var(--s2)"/>
</svg>
^ Both modes apply the same standardize-scale-shift transform; eval mode draws the mean and variance from the fixed running statistics (a function of x alone), while train mode draws them from the current batch, so only the train path lets the batchmates change x's output.

**The transform is identical; the mode chooses whether the mean and variance come from the fixed running statistics (eval, batch-independent) or from the current batch (train, batch-dependent) — so at inference only eval mode gives an example an output that depends on the example alone.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/batchnorm-inter-01/batchnorm.py

The fixture is one feature's learned statistics and the example we score, plus two batches it might land in.

```json filename=modules/below-the-prompt/code/batchnorm-inter-01/batchnorm.json:3-10 COMPLETE
  "running_mean": 0.0,
  "running_var": 1.0,
  "gamma": 1.0,
  "beta": 0.0,
  "eps": 1e-5,
  "example": 2.0,
  "batch_a": [2.0, 0.0, 4.0],
  "batch_b": [2.0, 6.0, 10.0]
```

Run `--modes` to score x=2.0 both ways.

```text filename=--modes
MODES — the same example under eval mode vs train mode
------------------------------------------------------------
  running stats: mean=0.0 var=1.0   gamma=1.0 beta=0.0
  example x = 2.0
------------------------------------------------------------
  EVAL  (running stats): (2.0-0.0)/sqrt(1.0) = 2.0000
  TRAIN (batch [2.0, 0.0, 4.0] stats): = 0.0000
  eval is correct at inference; train mode leaks the batch into the answer.
```

In eval mode the example normalizes with the running statistics: (2.0 − 0.0) / √1.0 = 2.0, the value training taught the layer to produce for an input of 2.0. In train mode, batched with [2, 0, 4], the layer instead uses that batch's mean of 2.0, so x sits exactly at the batch mean and normalizes to 0.0. Same input, same weights, same layer — 2.0 versus 0.0, and the only difference is which statistics the mode selected. The train-mode answer is not a small perturbation of the right one; it is a different number entirely, because standardizing against the batch mean of 2.0 says "this example is perfectly average for its batch," which is a fact about the batch, not about the model's learned representation of a 2.0 input.

## Build

The deeper problem is not that train mode gives a different constant — it is that it gives a different answer for *every* different batch. Run `--batchdep`.

```text filename=--batchdep
BATCHDEP — the same example, two different batches, TRAIN mode
--------------------------------------------------------------
  batch_a = [2.0, 0.0, 4.0] mean=2.0 -> train-mode output 0.0000
  batch_b = [2.0, 6.0, 10.0] mean=6.0 -> train-mode output -1.2247
  (eval-mode output is 2.0000 for both -- it never looks at the batch)
--------------------------------------------------------------
  batch of size 1 ([2.0]): variance 0, output collapses to beta = 0.0000 (true of ANY input).
```

The same x=2.0 comes out 0.0 in batch_a and −1.2247 in batch_b, because the two batches have different means (2.0 and 6.0) and x is standardized against whichever it landed in. In a real service this means the model's output for a request depends on which other requests were batched with it — an input can get one prediction at low traffic (batched alone or with similar inputs) and a different prediction at high traffic (batched with a varied mix), with no error and no log line to explain it. The eval-mode output stays 2.0 across both batches, because it never consults the batch. And the size-1 case is the sharpest: a single-example batch has zero variance, so the standardized value is 0 for any input and the output collapses to beta — the feature is destroyed, the same 0.0 for x=2.0 and for x=99.

<svg role="img" aria-label="The same input x equals 2.0 producing three different outputs: eval 2.0, train in batch a 0.0, train in batch b negative 1.2247" viewBox="0 0 300 116" width="300" height="116">
  <text x="6" y="12" fill="var(--muted)" font-size="8">one input x=2.0, three outputs — only eval is stable</text>
  <line x1="30" y1="70" x2="290" y2="70" stroke="var(--line)"/>
  <text x="24" y="40" fill="var(--muted)" font-size="7" text-anchor="end">2</text>
  <text x="24" y="73" fill="var(--muted)" font-size="7" text-anchor="end">0</text>
  <text x="24" y="100" fill="var(--muted)" font-size="7" text-anchor="end">-1.22</text>
  <g transform="translate(60,0)">
  <rect x="0" y="38" width="40" height="32" fill="var(--s1)"/><text x="0" y="84" fill="var(--muted)" font-size="7">eval 2.0</text>
  </g>
  <g transform="translate(140,0)">
  <rect x="0" y="68" width="40" height="4" fill="var(--s2)"/><text x="-4" y="84" fill="var(--muted)" font-size="7">train_a 0.0</text>
  </g>
  <g transform="translate(220,0)">
  <rect x="0" y="70" width="40" height="27" fill="var(--s2)"/><text x="-4" y="108" fill="var(--muted)" font-size="7">train_b -1.22</text>
  </g>
</svg>
^ Eval mode gives the correct, batch-independent 2.0, while train mode gives 0.0 or −1.2247 for the identical input depending on its batch — three outputs for one x, two of them artifacts of the batching.

## Definition of done

The self-test pins all four facts: eval uses running stats, train's output moves with the batch and differs from eval, eval is batch-independent, and a size-1 batch collapses.

```python filename=modules/below-the-prompt/code/batchnorm-inter-01/batchnorm.py:110-116 COMPLETE
    eval_batch_independent = eval_mode(x, data) == ev
    print("  eval-mode output never depends on a batch = %s (%.4f)" % (eval_batch_independent, ev))

    single = train_mode(x, [x], data)
    other = train_mode(99.0, [99.0], data)
    size1_collapses = abs(single - data["beta"]) < 1e-3 and abs(other - data["beta"]) < 1e-3
    print("  a size-1 batch collapses any input to beta = %s (x=%.1f->%.4f, x=99->%.4f)" % (size1_collapses, x, single, other))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — eval uses running stats and is batch-independent; train uses batch stats so the output moves with the batch; size-1 collapses
------------------------------------------------------------------------------------------------------------------------------------
  eval mode normalizes with the running stats = True (2.0000)
  train mode gives the SAME x different outputs per batch = True (0.0000 vs -1.2247)
  train-mode output differs from the correct eval output = True (0.0000 vs 2.0000)
  eval-mode output never depends on a batch = True (2.0000)
  a size-1 batch collapses any input to beta = True (x=2.0->0.0000, x=99->0.0000)
```

**Done means the mode's effect is proven on real values: eval mode gives x=2.0 the stable, running-statistics output 2.0 regardless of batch, while train mode gives the same x 0.0 in batch_a and −1.2247 in batch_b (differing from each other and from the correct 2.0), and a size-1 batch maps both x=2.0 and x=99 to beta=0.0 — so inference must run in eval mode or the output is a function of the batching, not the input.**

## Boss fight

Predict where this bites beyond the obvious forgotten flag, because the train/eval split touches training stability and distributed setups too.

<svg role="img" aria-label="A batch of size one: three different inputs 2, 40, and 99 each in their own single-example batch all collapse to the same output beta equals zero, destroying the signal" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">a size-1 batch has zero variance — every input maps to beta</text>
  <g transform="translate(20,26)">
  <rect x="0" y="0" width="46" height="16" fill="none" stroke="var(--line)"/><text x="10" y="12" fill="var(--muted)" font-size="7">x = 2</text>
  <rect x="0" y="24" width="46" height="16" fill="none" stroke="var(--line)"/><text x="8" y="36" fill="var(--muted)" font-size="7">x = 40</text>
  <rect x="0" y="48" width="46" height="16" fill="none" stroke="var(--line)"/><text x="8" y="60" fill="var(--muted)" font-size="7">x = 99</text>
  </g>
  <text x="90" y="60" fill="var(--muted)" font-size="9">→</text>
  <line x1="68" y1="34" x2="130" y2="60" stroke="var(--s2)"/><line x1="68" y1="58" x2="130" y2="60" stroke="var(--s2)"/><line x1="68" y1="82" x2="130" y2="60" stroke="var(--s2)"/>
  <g transform="translate(132,50)">
  <rect x="0" y="0" width="60" height="18" fill="var(--s2)"/><text x="10" y="13" fill="var(--panel)" font-size="8">output 0.0</text>
  </g>
  <text x="210" y="58" fill="var(--muted)" font-size="7">= beta,</text>
  <text x="210" y="70" fill="var(--muted)" font-size="7">signal destroyed</text>
</svg>
^ With one example per batch the batch variance is zero, so the standardized value is 0 for every input and the output is beta regardless of x — three different inputs (2, 40, 99) all map to 0.0, the worst case of train-mode inference.

The first trap is that the running statistics themselves can be wrong even when you *do* switch to eval mode, and then eval mode is confidently wrong in a stable way. The running mean and variance are an exponential moving average over training batches, so they are only trustworthy if training saw enough batches, with a large enough batch size, from the same distribution as inference. Fine-tune on a tiny dataset, or train with batch size 2, or shift the input distribution at serving time, and the stored statistics do not describe the inference data — eval mode will normalize by a mean and variance that no longer fit, and the error is now silent AND reproducible, which is harder to catch than the batch-dependent version because at least the latter is visibly inconsistent. The lesson is that batch norm couples your inference correctness to a statistic estimated during training, so the batch size and data distribution during training are inference-time concerns, not just optimization details.

The second trap is that batch norm's batch-dependence causes subtler failures wherever the "batch" is not what you think. In distributed data-parallel training each device computes statistics over only its local shard, so the effective normalization batch is the per-device batch, not the global one — which is why synchronized batch norm exists to pool statistics across devices when the per-device batch is small. And any leakage of information across examples in a batch is a correctness hazard for tasks that must treat examples independently: contrastive setups, metric learning, and some RL objectives can have examples "see" each other through the shared batch statistics, so a model can exploit batch composition in ways that do not generalize to single-example inference. This is a large part of why transformer language models use layer normalization (or RMSNorm) instead — layer norm normalizes across the feature dimension of each token independently, so it behaves identically in train and eval, needs no running statistics, and never lets one example's output depend on another. Batch norm's power in convolutional vision models comes with a train/eval asymmetry that layer norm was chosen, in sequence models, specifically to avoid.

**Batch norm ties inference to statistics estimated during training, so correctness depends not just on switching to eval mode but on the running statistics being estimated from enough same-distribution data — and its batch-coupling causes further failures across devices (per-shard statistics, hence synchronized batch norm) and across examples that must stay independent, which is why sequence models prefer layer norm / RMSNorm, whose train and eval behavior are identical and per-example.**

## External resources

The batch normalization paper (Ioffe and Szegedy) and any deep-learning framework's BatchNorm documentation — the train/eval mode distinction, the running-statistics (momentum) mechanism, and the explicit instruction to put the model in eval mode for inference.

Writing on synchronized batch norm and small-batch normalization alternatives (Group Norm, Layer Norm) — why per-device or tiny batches break batch norm's statistics and what replaces it when the batch is not a reliable sample.

The companion RMSNorm and residual-stream modules in this topic — layer norm and RMSNorm are the sequence-model answer to batch norm's train/eval asymmetry, normalizing per token so training and inference behave identically without running statistics.
