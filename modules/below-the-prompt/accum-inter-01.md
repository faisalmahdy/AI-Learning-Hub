---
id: accum-inter-01
title: Average the accumulated micro-batch gradients — or you have secretly multiplied the learning rate
topic: below-the-prompt
level: intermediate
status: ready
time: 21 min
summary: Gradient accumulation simulates a large batch by running k small micro-batches, adding their gradients, and stepping once — but only if you average the accumulated gradient, not sum it. Summing makes the gradient k times too large, so the optimizer takes a step k times bigger than configured: the effective learning rate is silently multiplied by the accumulation-step count. On 6 example gradients as 3 micro-batches, the averaged accumulation reproduces the full-batch gradient exactly while the summed one is 3x too large — identical to running at 3x the learning rate.
eli5: You want to carry six bags but can only lift two at a time, so you make three trips. To know the average weight per bag you add up all six and divide by six — if you forget to divide, you think each bag weighs three times as much and overcorrect. Adding up the trips without dividing makes your training take steps three times too big.
---

## Why this module

Gradient accumulation is a one-line trick to train with a big batch on small memory, and one missing division turns it into a silent, unconfigured learning-rate hike.

You want a large batch — say six examples per step — because a gradient averaged over more examples is less noisy and the training is more stable. But the large batch will not fit in memory. Gradient accumulation is the standard way out: run the batch as several smaller micro-batches, keep a running total of their gradients, and after the last one do a single optimizer step. You have computed the same gradient the big batch would have produced, without ever holding all of it in memory at once. It is the technique that lets a modest GPU train at an effective batch size far larger than it can physically fit.

The trick works precisely when the accumulated gradient equals what the full batch would have produced — and the full-batch gradient is the average over the examples, not the sum. A batch of six contributes the mean of six per-example gradients; if you accumulate three micro-batches of two and add them without dividing by three, you get three times that mean. The gradient you hand the optimizer is k times too large, where k is the number of accumulation steps.

That oversized gradient does not raise an error. The optimizer faithfully takes a step proportional to the gradient it was given, so a gradient three times too large produces a step three times too large — which is exactly what would happen if you had set the learning rate three times higher. Your effective learning rate has been silently multiplied by the accumulation-step count. Training that was stable at a micro-batch of two starts oscillating or diverging the moment you accumulate, and the learning rate on your config — the thing you would check — looks perfectly reasonable. The bug is a division you did not do.

On the fixture, six example gradients are processed as three micro-batches of two. The correct averaged accumulation reproduces the full-batch gradient exactly, so its optimizer step matches what one big batch would do. The buggy summed accumulation is three times too large, so its step is three times too big — identical to running the correct code at three times the learning rate.

**Gradient accumulation reproduces a large-batch step from small micro-batches only if the accumulated gradient is averaged; summing it makes the gradient k times too large and the optimizer step k times too big, which is a silent multiplication of the learning rate by the accumulation-step count.**

## Concepts

The whole point of accumulation is to be mathematically identical to the big batch, and identity requires the same normalization. A loss is almost always defined as a mean over the batch — mean cross-entropy, mean squared error — so its gradient is a mean over the examples' gradients. When you split the batch into micro-batches and want the same gradient, you must combine the micro-batch gradients the same way the loss combines examples: by averaging. Summing changes the normalization, and a gradient with the wrong normalization is a gradient for a different loss — here, the loss scaled up by k, whose gradient is k times larger. Accumulation is not "add up the pieces"; it is "reconstruct the mean from the pieces."

The reason the bug masquerades as a learning-rate change is that the optimizer step is (in plain SGD) the learning rate times the gradient, and that product does not care which factor is too big. Multiply the gradient by k or multiply the learning rate by k and you get the identical step. So a k-times-too-large gradient is indistinguishable, in its effect on the weights, from a k-times-too-large learning rate — the update vector is exactly the same. This is why the symptom is classic learning-rate-too-high behavior (loss spikes, oscillation, divergence) while the learning rate in your config is untouched: the extra factor is hiding in the gradient, not the hyperparameter.

<svg role="img" aria-label="Six examples split into three micro-batches of two; averaging the three recovers the full-batch mean, summing gives three times it" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">3 micro-batches of 2 → one step</text>
  <g fill="var(--acc-soft)" stroke="var(--acc-line)"><rect x="40" y="40" width="90" height="26"/><rect x="150" y="40" width="90" height="26"/><rect x="260" y="40" width="90" height="26"/></g>
  <text x="60" y="57" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">micro 1</text>
  <text x="170" y="57" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">micro 2</text>
  <text x="280" y="57" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">micro 3</text>
  <text x="370" y="57" font-family="var(--mono)" font-size="9" fill="var(--muted)">+ + +</text>
  <text x="40" y="102" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">divide by 3 → full-batch gradient (correct)</text>
  <rect x="40" y="108" width="120" height="20" fill="var(--acc-line)"/>
  <text x="46" y="122" font-family="var(--mono)" font-size="8" fill="var(--panel)">[1.667, 2.0]</text>
  <text x="40" y="150" font-family="var(--mono)" font-size="9" fill="var(--s2)">forget the divide → 3x too large (bug)</text>
  <rect x="40" y="154" width="360" height="18" fill="var(--s2)"/>
  <text x="46" y="167" font-family="var(--mono)" font-size="8" fill="var(--panel)">[5.0, 6.0]</text>
</svg>
^ The three micro-batch gradients sum, and dividing by three recovers the full-batch [1.667, 2.0]; skipping the division leaves [5.0, 6.0], three times too large.

There is a second, subtler place the same division bites: the micro-batch averaging itself. If each micro-batch's loss is a mean over its own examples, then averaging the k micro-batch gradients recovers the full mean only when the micro-batches are equal-sized — which they are here, and usually are. When the last micro-batch is smaller (the batch does not divide evenly), a plain average of micro-batch gradients over-weights the small batch's examples, and the exact fix is to weight each micro-batch by its example count, or equivalently to sum per-example gradients and divide by the total. The clean mental model is: divide by the total number of examples once, at the end. Any scheme that does that is correct; any scheme that divides by the wrong count is off by that ratio.

This matters because effective batch size is a real hyperparameter that interacts with the learning rate, and accumulation is how you decouple it from memory. Practitioners deliberately raise the accumulation steps to grow the effective batch, and there is a well-known rule of thumb that a larger batch can support a larger learning rate (linear scaling). The summing bug corrupts exactly this relationship: it changes the learning rate as a side effect of changing the accumulation, so you can no longer reason about the two independently. Getting the average right is what makes accumulation transparent — the effective batch grows, the gradient stays correctly normalized, and the learning rate means what you set it to.

**A batch loss is a mean, so accumulation must average micro-batch gradients to reconstruct it; summing scales the gradient by k, and since the step is learning-rate times gradient, that is indistinguishable from a k-times learning rate — the safe rule is to divide by the total example count exactly once.**

## Worked example

The fixture is per-example gradients for one batch, the micro-batch size, and a learning rate.

```json filename=modules/below-the-prompt/code/accum-inter-01/grads.json:3-11 COMPLETE
  "lr": 0.1,
  "micro_batch": 2,
  "grads": [
    [1.0, 0.0],
    [3.0, 0.0],
    [0.0, 2.0],
    [0.0, 4.0],
    [2.0, 2.0],
    [4.0, 4.0]
  ]
```

Six examples, micro-batches of two, so three accumulation steps. The full-batch gradient is the mean over all six; a micro-batch gradient is the mean over its two.

```python filename=modules/below-the-prompt/code/accum-inter-01/accum.py:60-67 COMPLETE
def micro_batches(grads, m):
    """Split the per-example gradients into micro-batches of size m, each averaged."""
    return [vmean(grads[i:i + m]) for i in range(0, len(grads), m)]


def full_batch_grad(grads):
    """The gradient the whole batch would produce -- the mean over all examples."""
    return vmean(grads)
```

The correct accumulation averages the three micro-batch gradients; the buggy one sums them.

```python filename=modules/below-the-prompt/code/accum-inter-01/accum.py:70-81 COMPLETE
def accum_averaged(grads, m):
    """Correct accumulation: average the micro-batch gradients."""
    return vmean(micro_batches(grads, m))


def accum_summed(grads, m):
    """Buggy accumulation: sum the micro-batch gradients (forgot to divide by k)."""
    mbs = micro_batches(grads, m)
    total = mbs[0]
    for v in mbs[1:]:
        total = vadd(total, v)
    return total
```

Predict: the averaged accumulation equals the full-batch mean, and the summed one is three times that. Run it.

```text filename=modules/below-the-prompt/code/accum-inter-01/accum.py --grads
GRADS — full-batch gradient vs accumulations (3 micro-batches of 2)
----------------------------------------------------------
  full batch (mean of all): [1.667, 2.0]
  averaged accumulation:    [1.667, 2.0]
  summed accumulation:      [5.0, 6.0]
----------------------------------------------------------
  averaged == full batch; summed is 3x too large.
```

The averaged accumulation is [1.667, 2.0] — identical to the full-batch gradient, which is the whole promise of accumulation delivered. The summed accumulation is [5.0, 6.0], exactly three times larger, because the three micro-batch means were added instead of averaged. Nothing about [5.0, 6.0] looks wrong on its own — it is a perfectly plausible gradient — which is why the bug is invisible without the comparison. Now the optimizer step.

```text filename=modules/below-the-prompt/code/accum-inter-01/accum.py --update
UPDATE — optimizer step (lr 0.10) from each accumulation
----------------------------------------------------------
  averaged step: [0.167, 0.2]   norm 0.260
  summed step:   [0.5, 0.6]   norm 0.781
----------------------------------------------------------
  the summed step equals the averaged step at lr=0.30 (3x the learning rate).
```

The averaged step has norm 0.260; the summed step has norm 0.781 — three times larger. And the summed step at learning rate 0.10 is exactly what the correct code would produce at learning rate 0.30. That is the bug's true nature made concrete: it is not a random error, it is a precise triplication of the learning rate. If 0.10 was tuned and stable, the accumulation silently ran at 0.30, and the training will behave like an over-hot learning rate while the config still says 0.10.

<svg role="img" aria-label="Two optimizer step vectors from the origin: the averaged step short, the summed step three times longer in the same direction, matching the full-batch step scaled by 3" viewBox="0 0 470 190" width="470" height="190">
  <rect x="0" y="0" width="470" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">optimizer step vectors (same direction, 3x length)</text>
  <line x1="40" y1="165" x2="40" y2="30" stroke="var(--line)"/>
  <line x1="40" y1="165" x2="440" y2="165" stroke="var(--line)"/>
  <line x1="40" y1="165" x2="140" y2="145" stroke="var(--acc-line)" stroke-width="3"/>
  <text x="90" y="138" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">averaged: norm 0.260</text>
  <line x1="40" y1="165" x2="340" y2="105" stroke="var(--s2)" stroke-width="3"/>
  <text x="250" y="98" font-family="var(--mono)" font-size="8" fill="var(--s2)">summed: norm 0.781 (3x)</text>
  <text x="120" y="182" font-family="var(--mono)" font-size="8" fill="var(--muted)">same direction — only the length is wrong, which is exactly a learning-rate change</text>
</svg>
^ The summed step points the same way as the averaged step but is three times as long — and a step scaled in place is indistinguishable from a learning rate scaled by the same factor.

## Build

Reproduce the accumulations. Pure standard library, deterministic, so the exact 3x factor and the effective learning rate of 0.30 come out cleanly.

Run `--grads` for the gradients, `--update` for the steps, `--check` for the gate. The averaging is one helper that means the batch loss (a mean) exactly — used both inside each micro-batch and across them.

```python filename=modules/below-the-prompt/code/accum-inter-01/accum.py:70-72 COMPLETE
def accum_averaged(grads, m):
    """Correct accumulation: average the micro-batch gradients."""
    return vmean(micro_batches(grads, m))
```

<svg role="img" aria-label="Bar chart of optimizer-step norm: averaged 0.260, summed 0.781, with the summed bar three times the averaged and equal to averaged-at-3x-lr" viewBox="0 0 470 160" width="470" height="160">
  <rect x="0" y="0" width="470" height="160" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">optimizer-step norm (lr 0.10)</text>
  <line x1="60" y1="130" x2="450" y2="130" stroke="var(--line)"/>
  <rect x="90" y="105" width="90" height="25" fill="var(--acc-line)"/>
  <text x="95" y="99" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">averaged 0.260</text>
  <rect x="270" y="55" width="90" height="75" fill="var(--s2)"/>
  <text x="272" y="49" font-family="var(--mono)" font-size="9" fill="var(--s2)">summed 0.781</text>
  <text x="255" y="146" font-family="var(--mono)" font-size="8" fill="var(--muted)">3x taller = the step at 3x the learning rate</text>
</svg>
^ The summed step's norm is three times the averaged step's — the same height you would get by tripling the learning rate on the correct code.

The self-test pins that averaging matches the full batch, summing is k times too large, and the bug equals a k-times learning rate.

```python filename=modules/below-the-prompt/code/accum-inter-01/accum.py:120-123 COMPLETE
    averaged_matches_full = max(abs(a - b) for a, b in zip(avg, full)) < 1e-9
    print("  averaged accumulation equals the full-batch gradient = %s" % averaged_matches_full)

    summed_is_k_times = max(abs(s - k * f) for s, f in zip(summed, full)) < 1e-9
    print("  summed accumulation is exactly k times the full gradient = %s (k=%d)" % (summed_is_k_times, k))
```

```text filename=modules/below-the-prompt/code/accum-inter-01/accum.py --check
SELF-TEST — averaging reproduces the full batch; summing multiplies the step by the accumulation count
----------------------------------------------------------------------------------------------------
  averaged accumulation equals the full-batch gradient = True
  summed accumulation is exactly k times the full gradient = True (k=3)
  the buggy step is k times the correct step = True (0.781 vs 0.260)
  the bug is identical to the correct code at k times the learning rate = True (lr 0.30)
  correct accumulation reproduces the full-batch step with no full batch in memory = True
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  averaged_matches_full=True  summed_is_k_times=True  bug_step_k_times=True  effective_lr_k=True  correct_reproduces_fullbatch=True
```

Five True flags. Averaged_matches_full: the averaged accumulation equals the full-batch gradient exactly. Summed_is_k_times: the summed one is exactly k = 3 times the full gradient. Bug_step_k_times: so the buggy step is 3 times the correct step (0.781 versus 0.260). Effective_lr_k: and the buggy step at lr 0.10 is bit-identical to the correct step at lr 0.30 — the bug is a learning-rate multiplication, provably. Correct_reproduces_fullbatch: the correct accumulation reproduces the full-batch step without ever holding the full batch, which is the entire reason to accumulate. The effective-lr flag is the diagnosis: this is not a vague instability but an exact k-times learning rate.

**The effective-lr flag names the bug precisely — the summed step at lr 0.10 equals the averaged step at lr 0.30, so gradient accumulation done by summing is not "a bit unstable," it is training at k times the learning rate you configured.**

## Definition of done

You are done when you reproduce the 3x gradient and can explain why summing is a learning-rate multiplication.

Concretely: `--grads` shows the averaged accumulation matching the full-batch [1.667, 2.0] and the summed one at [5.0, 6.0]; `--update` shows steps of norm 0.260 and 0.781 with the summed step equal to the correct step at lr 0.30; `--check` prints PASS with five True flags. You can explain that a batch loss is a mean so accumulation must average to reconstruct it, that the optimizer step is learning-rate times gradient so a k-times gradient is indistinguishable from a k-times learning rate, and that the safe rule is to divide by the total example count exactly once (weighting unequal micro-batches by their size).

The habit to carry: when you add gradient accumulation, verify the accumulated gradient is normalized by the total number of examples, not the number of micro-batches summed, and re-check the learning rate is still what you intend. When training that was stable suddenly oscillates or diverges after you increase accumulation steps or change micro-batch size, suspect a normalization mismatch multiplying your effective learning rate before you suspect anything subtler.

## Boss fight

The instructive failure is a fine-tuning run that diverges the moment someone adds accumulation to fit a bigger batch.

An engineer trains fine at a batch of 8, then, to reach an effective batch of 32 on the same GPU, adds gradient accumulation with 4 steps of 8 — and the loss immediately spikes and NaNs. The accumulation code summed the four micro-batch gradients without dividing by four, so the effective learning rate quadrupled the instant accumulation turned on. The engineer, seeing an unchanged learning rate in the config, spends hours suspecting the data, the new batch size, or numerical precision, when the fix is a single division by the accumulation-step count. The tell was that it broke exactly when accumulation was introduced and the breakage looked like a learning rate far too high.

Your turn, two moves. First, make the batch not divide evenly — use 5 examples with a micro-batch of 2 (micro-batches of 2, 2, 1) — and confirm that averaging the three micro-batch gradients no longer equals the full mean, because the last micro-batch of one is over-weighted; then fix it by weighting each micro-batch by its example count (or summing per-example gradients and dividing by 5) and watch it match again. Second, compensate the bug deliberately: keep the summing but divide the learning rate by k, and confirm the step returns to correct — proving the two are the same knob, and illustrating why some codebases fold the 1/k into the loss instead of the gradient (mathematically identical, and it keeps the learning rate meaning what it says).

## External resources

Any deep-learning framework's gradient-accumulation guide (PyTorch's, Hugging Face Accelerate's) states the rule explicitly — scale the loss (or the accumulated gradient) by 1/accumulation_steps — and warns about the uneven-last-batch case this module's boss fight explores.

Goyal et al.'s "Accurate, Large Minibatch SGD" (2017) is the reference on the batch-size/learning-rate relationship (the linear scaling rule and warmup), which is exactly the relationship the summing bug silently corrupts.

Framework issue trackers and forums are full of "loss diverges after enabling gradient accumulation" reports; reading a few shows the summing-versus-averaging normalization error is one of the most common causes, which is why the one-division check is worth building in.
