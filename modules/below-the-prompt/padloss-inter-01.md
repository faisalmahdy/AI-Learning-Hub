---
id: padloss-inter-01
title: Mask the padding out of the loss — averaging cross-entropy over the padded tensor lets filler tokens dilute it and leak gradient
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: To train on sequences of different lengths, you batch them into one rectangular tensor, which means padding the shorter sequences with a filler token up to the batch's longest length. Padding is bookkeeping — those positions carry no real data and the model should learn nothing from them — but the loss is computed position by position over the whole tensor, and if you simply average the per-token cross-entropy across every position you have quietly included the padding. The padding positions get a loss too, and because the padding token is perfectly predictable (always the same filler in the same trailing positions), that loss is small, so the naive average is pulled toward the easy padding and understates the real loss. The dilution of the reported number is the visible symptom; the real damage is in the gradient: every padding position that contributes to the loss also contributes a gradient, training the model to predict filler that never appears at inference. A batch that is mostly padding can have most of its gradient coming from padding, so the model optimizes the wrong objective and the loss curve misrepresents progress — none of it raising an error. The fix is a mask: a 0/1 flag per position from each sequence's true length; the loss sums cross-entropy only where the mask is 1 and divides by the count of real tokens, so padding influences neither the reported loss nor the gradient. On a batch where sequence A is length 2 (real losses 2.0, 4.0) padded with two easy positions (losses 1.0, 1.0) and B is length 4 (losses 3.0), the naive mean over all 8 positions is 20/8 = 2.5 while the masked mean over the 6 real tokens is 18/6 = 3.0.
eli5: Imagine grading a class's essays, but to make the stack neat you add blank filler pages to the shorter essays so every stack is the same height. Now you grade page by page and average the scores. The filler pages are blank and trivially "correct," so they all get easy high marks — and when you average every page, those easy filler pages pull the class average up and make the real essays look better than they are. Worse, if you use those grades to decide what to teach next, you end up spending lesson time on "how to write a blank page," which no one needs. The fix is simple: mark which pages are real, grade only those, and ignore the filler entirely — then the average reflects the actual essays and your teaching targets real writing.
---

## Why this module

Batching is not optional — you train on many sequences at once for efficiency — and sequences are not the same length, so padding is not optional either. That makes the padding mask one of those small, boring pieces of plumbing that is easy to get subtly wrong, and getting it wrong does not crash anything. The tensor shapes are correct, the loss is a finite number, the training loop runs. It just trains on the wrong objective, and the loss it reports is not the loss you think it is. This is worth seeing concretely because the bug is invisible at every layer except the one that matters: what the gradient is actually optimizing.

The mechanism is quiet. Padding fills the trailing positions of short sequences with a constant filler token. When the loss averages cross-entropy over every position in the padded tensor, those filler positions are in the average — and they are the easiest positions in the batch, because the padding token is perfectly predictable, so their loss is low. The naive average is therefore dragged down by the easy filler, understating the real per-token loss. And each of those positions, being in the loss, carries a gradient that trains the model to predict padding — capacity spent on positions that never occur at inference.

The remedy is a per-position mask derived from each sequence's true length. This module computes the loss over a small batch both ways — averaging over the full padded tensor and masking to real tokens — and measures the dilution and the leaked gradient.

**Mask padding positions out of the loss — sum the per-token cross-entropy only over real tokens and divide by the real-token count, using a length-derived 0/1 mask — rather than averaging over the full padded tensor, because padding is trivially predictable filler whose low loss dilutes the average and whose gradient trains the model to predict positions that never occur at inference.**

## Concepts

The fixture is a batch of two sequences padded to length 4. Sequence A is truly length 2 — real losses 2.0 and 4.0 — with two padding positions whose losses are 1.0 each (low, because padding is easy). Sequence B is a full length 4, all real, losses 3.0. The per-token cross-entropy at every position is given; what the code computes is how you combine them.

```json filename=modules/below-the-prompt/code/padloss-inter-01/padloss.json:3-7 COMPLETE
  "padded_len": 4,
  "batch": [
    {"id": "A", "real_len": 2, "token_losses": [2.0, 4.0, 1.0, 1.0]},
    {"id": "B", "real_len": 4, "token_losses": [3.0, 3.0, 3.0, 3.0]}
  ]
```

The mask is one comparison per position: real where the index is below the sequence's true length, padding otherwise. The naive loss ignores the mask and averages over every position in the tensor.

```python filename=modules/below-the-prompt/code/padloss-inter-01/padloss.py:53-63 COMPLETE
def mask_for(seq, padded_len):
    """1 for real token positions, 0 for padding, from the sequence's real length."""
    return [1 if i < seq["real_len"] else 0 for i in range(padded_len)]


def naive_loss(batch, padded_len):
    """Average the per-token loss over EVERY padded position (padding included)."""
    total = sum(sum(seq["token_losses"]) for seq in batch)
    count = len(batch) * padded_len
    return total, count, total / count
```

The masked loss multiplies each position's loss by its mask before summing, and divides by the number of real tokens — not the padded size. Padding contributes zero to both the numerator and the denominator. The leaked-gradient measure is the total loss the naive average charges to padding, which is exactly the signal masking removes.

```python filename=modules/below-the-prompt/code/padloss-inter-01/padloss.py:66-85 COMPLETE
def masked_loss(batch, padded_len):
    """Sum the per-token loss over real tokens only (mask == 1) and divide by the real-token count."""
    total = 0.0
    count = 0
    for seq in batch:
        m = mask_for(seq, padded_len)
        for loss, keep in zip(seq["token_losses"], m):
            total += loss * keep
            count += keep
    return total, count, total / count


def padding_contribution(batch, padded_len):
    """The total loss the naive average charges to padding positions -- the leaked gradient signal."""
    total = 0.0
    for seq in batch:
        m = mask_for(seq, padded_len)
        for loss, keep in zip(seq["token_losses"], m):
            if keep == 0:
                total += loss
    return total
```

<svg role="img" aria-label="Two sequence rows: A has two real cells and two shaded padding cells, B has four real cells; the padding cells are marked as included by naive and excluded by masked" viewBox="0 0 320 130">
  <text x="10" y="20" font-size="9" fill="var(--muted)">seq A (real_len 2)</text>
  <rect x="120" y="10" width="34" height="24" fill="var(--s1)"/>
  <text x="132" y="27" font-size="10" fill="var(--panel)">2.0</text>
  <rect x="156" y="10" width="34" height="24" fill="var(--s1)"/>
  <text x="168" y="27" font-size="10" fill="var(--panel)">4.0</text>
  <rect x="192" y="10" width="34" height="24" fill="var(--muted)" stroke="var(--ink)" stroke-dasharray="3 2"/>
  <text x="204" y="27" font-size="10" fill="var(--panel)">1.0</text>
  <rect x="228" y="10" width="34" height="24" fill="var(--muted)" stroke="var(--ink)" stroke-dasharray="3 2"/>
  <text x="240" y="27" font-size="10" fill="var(--panel)">1.0</text>
  <text x="268" y="27" font-size="8" fill="var(--muted)">← padding</text>
  <text x="10" y="60" font-size="9" fill="var(--muted)">seq B (real_len 4)</text>
  <rect x="120" y="50" width="34" height="24" fill="var(--s1)"/>
  <text x="132" y="67" font-size="10" fill="var(--panel)">3.0</text>
  <rect x="156" y="50" width="34" height="24" fill="var(--s1)"/>
  <text x="168" y="67" font-size="10" fill="var(--panel)">3.0</text>
  <rect x="192" y="50" width="34" height="24" fill="var(--s1)"/>
  <text x="204" y="67" font-size="10" fill="var(--panel)">3.0</text>
  <rect x="228" y="50" width="34" height="24" fill="var(--s1)"/>
  <text x="240" y="67" font-size="10" fill="var(--panel)">3.0</text>
  <text x="10" y="100" font-size="8.5" fill="var(--s2)">naive: sum all 8 / 8 = 2.5</text>
  <text x="10" y="116" font-size="8.5" fill="var(--s1)">masked: sum 6 real / 6 = 3.0</text>
</svg>
^ The two dashed cells are A's padding — trivially low loss (1.0). Naive averages all eight cells; masked keeps only the six solid real cells. The dashed cells are the entire difference between 2.5 and 3.0.

**The mask is a single comparison per position, but it decides whether the loss is an average over your data or an average over your data plus a pile of easy filler.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the loss-reduction step of a training loop, reduced to a two-sequence batch so every count and mean is checkable by hand.

Run `--batch` to see the sequences, their per-position losses, and the derived masks.

```text filename=padloss.py --batch
  seq  real_len  token_losses          mask (1=real, 0=pad)
  A    2         [2.0, 4.0, 1.0, 1.0]  [1, 1, 0, 0]
  B    4         [3.0, 3.0, 3.0, 3.0]  [1, 1, 1, 1]
  real tokens = 6 ; padded positions = 2 ; total = 8
```

Sequence A's mask is [1, 1, 0, 0] — its first two positions are real, its last two are padding. B is all real. Across the batch there are 6 real tokens and 2 padding positions, 8 total. The naive average will divide by 8; the masked average by 6, and the difference is exactly those two easy padding positions.

Now `--loss` computes both.

```text filename=padloss.py --loss
  naive  mean = 2.5000 = 20.0 / 8  (averages over all padded positions)
  masked mean = 3.0000 = 18.0 / 6  (averages over real tokens only)
  loss charged to padding by the naive average = 2.0 (leaked gradient)
  naive understates the true per-token loss by 0.5000
```

The naive mean is 2.5: it sums all eight losses to 20 and divides by 8. The masked mean is 3.0: it sums only the six real losses to 18 and divides by 6. The naive number is lower — the two padding positions, at loss 1.0 each, pulled the average down by half a point. And the leaked-gradient line names the real cost: 2.0 of loss (and the gradient that comes with it) was charged to positions that are pure filler. The reported loss is wrong and the gradient is being spent on predicting padding.

**Including two easy padding positions drops the reported per-token loss from 3.0 to 2.5 and hands 2.0 of loss to filler — the number is diluted and the gradient is misdirected, with no error to signal either.**

## Build

The self-test asserts the setup and both failure modes: that padding is present, that the naive average divides by the padded size while the masked one divides by real tokens, and that the naive loss both understates the truth and charges loss to padding.

```python filename=modules/below-the-prompt/code/padloss-inter-01/padloss.py:113-127 COMPLETE
    batch_has_padding = any(seq["real_len"] < padded_len for seq in batch)
    print("  at least one sequence is padded = %s" % batch_has_padding)

    naive_counts_padding = nc == len(batch) * padded_len and nc > real
    print("  the naive average divides by all padded positions = %s (%d, not the %d real tokens)" % (naive_counts_padding, nc, real))

    masked_counts_real = mc == real
    print("  the masked average divides by the real-token count = %s (%d)" % (masked_counts_real, mc))

    naive_understates = nm < mm
    print("  the naive loss understates the true per-token loss = %s (%.4f < %.4f)" % (naive_understates, nm, mm))

    masked_mean_correct = abs(mm - 3.0) < 1e-9
    print("  the masked loss equals the true mean over real tokens = %s (%.4f == 3.0)" % (masked_mean_correct, mm))
```

<svg role="img" aria-label="Two divisions shown as fractions: naive 20 over 8 equals 2.5 with padding shaded in the denominator, masked 18 over 6 equals 3.0 with only real tokens" viewBox="0 0 320 120">
  <text x="20" y="30" font-size="9" fill="var(--s2)">naive</text>
  <text x="70" y="45" font-size="13" fill="var(--ink)">20.0</text>
  <line x1="65" y1="52" x2="120" y2="52" stroke="var(--ink)" stroke-width="1.5"/>
  <text x="82" y="70" font-size="13" fill="var(--ink)">8</text>
  <text x="130" y="58" font-size="13" fill="var(--ink)">= 2.5</text>
  <text x="130" y="74" font-size="7.5" fill="var(--s2)">8 includes 2 padding</text>
  <text x="20" y="100" font-size="9" fill="var(--s1)">masked</text>
  <text x="220" y="45" font-size="13" fill="var(--ink)">18.0</text>
  <line x1="215" y1="52" x2="270" y2="52" stroke="var(--ink)" stroke-width="1.5"/>
  <text x="232" y="70" font-size="13" fill="var(--ink)">6</text>
  <text x="280" y="58" font-size="13" fill="var(--ink)">= 3.0</text>
  <text x="200" y="90" font-size="7.5" fill="var(--s1)">6 real tokens only</text>
</svg>
^ Both the numerator and the denominator change: masking drops the 2.0 of padding loss from the top and the 2 padding positions from the bottom. 20/8 = 2.5 becomes 18/6 = 3.0.

Running the check confirms every clause, including the leaked gradient.

```text filename=padloss.py --check
  at least one sequence is padded = True
  the naive average divides by all padded positions = True (8, not the 6 real tokens)
  the masked average divides by the real-token count = True (6)
  the naive loss understates the true per-token loss = True (2.5000 < 3.0000)
  the masked loss equals the true mean over real tokens = True (3.0000 == 3.0)
  the naive loss charges nonzero loss to padding (leaked gradient) = True (2.0)
```

**The check ties the diluted number and the leaked gradient to the same cause — the padding positions in the average — and shows masking removing both by changing what the loss counts.**

## Definition of done

Two properties close it. The masked loss must equal the true mean over real tokens (3.0 here), proving masking recovers the correct objective, and the naive loss must charge nonzero loss to padding, proving the gradient leak is real and not just a reporting quirk. The second is the one that matters for training: a diluted number you could correct after the fact, but a gradient computed over padding has already updated the weights.

```python filename=modules/below-the-prompt/code/padloss-inter-01/padloss.py:129-133 COMPLETE
    gradient_leaks_to_padding = padding_contribution(batch, padded_len) > 0
    print("  the naive loss charges nonzero loss to padding (leaked gradient) = %s (%.1f)" % (gradient_leaks_to_padding, padding_contribution(batch, padded_len)))

    ok = batch_has_padding and naive_counts_padding and masked_counts_real and naive_understates and masked_mean_correct and gradient_leaks_to_padding
```

The size of the effect scales with how much padding a batch carries, which is worth stating so the tool is neither under- nor over-sold. Here padding is a quarter of the positions and the loss moves 2.5 to 3.0 — noticeable. In a batch with one long sequence and many short ones, padding can be the majority of positions, and then most of the gradient comes from filler and the reported loss is badly wrong. The direction can also flip if the filler token were somehow high-loss, but in practice padding is the easiest possible prediction, so the naive loss almost always understates. The fix does not depend on any of this: mask by true length, divide by real-token count, and padding cannot touch the loss or the gradient regardless of how much of it there is. Related masks (ignoring the prompt tokens in instruction tuning, or a specific ignore-index for labels) are the same operation applied to a different set of positions.

<svg role="img" aria-label="Two batches: one a quarter padding where the gradient is mostly real, one mostly padding where the gradient bar is dominated by filler" viewBox="0 0 320 130">
  <text x="10" y="20" font-size="9" fill="var(--muted)">this batch (2 of 8 padding)</text>
  <rect x="10" y="28" width="180" height="18" fill="var(--s1)"/>
  <rect x="190" y="28" width="60" height="18" fill="var(--muted)"/>
  <text x="70" y="41" font-size="8" fill="var(--panel)">real gradient</text>
  <text x="193" y="41" font-size="8" fill="var(--panel)">padding</text>
  <text x="10" y="78" font-size="9" fill="var(--muted)">short data, pad to 512 (mostly padding)</text>
  <rect x="10" y="86" width="30" height="18" fill="var(--s1)"/>
  <rect x="40" y="86" width="210" height="18" fill="var(--muted)"/>
  <text x="12" y="99" font-size="8" fill="var(--panel)">real</text>
  <text x="110" y="99" font-size="8" fill="var(--panel)">padding dominates the gradient</text>
  <text x="10" y="122" font-size="8.5" fill="var(--s2)">the leak grows with the padding fraction — masking removes it at any fraction</text>
</svg>
^ The gradient leak is proportional to the padding fraction. In this small batch padding is a quarter of positions; with short examples padded to a large fixed length it becomes the majority, and the model trains mostly on filler. Masking zeroes the padding share regardless.

**Done means the masked loss equals the true per-token mean and the naive loss provably charges loss to padding — so masking is fixing a real gradient leak, not just tidying a reported number.**

## Boss fight

A teammate is fine-tuning a model and reports that their training loss looks great — lower than the baseline from the start — but the model's actual generations are no better, and sometimes worse. You look at their data loader and see they batch by padding to a fixed maximum length of 512, and their dataset is mostly short examples (30–80 tokens). Their loss function is a plain mean of per-token cross-entropy over the batch tensor. What is almost certainly happening, and what one change would both fix the loss number and improve the model?

Their loss is dominated by padding. With short examples padded to 512, the overwhelming majority of positions in each batch are filler, and filler is the easiest possible prediction, so the mean per-token loss is pulled far below the true loss on real tokens — which is exactly why it "looks great from the start" while the model does not actually improve. Worse, most of the gradient is coming from those padding positions, so the optimizer is spending nearly all its signal teaching the model to predict padding rather than the real task, which is why generations do not improve and can degrade. The one change is to mask the padding out of the loss: build a length-derived 0/1 mask, sum cross-entropy only over real tokens, and divide by the real-token count. That instantly makes the reported loss reflect real tokens (it will jump up to an honest, higher value — which is correct, not a regression) and redirects the entire gradient onto the actual task. As a secondary win, padding to the batch's longest sequence instead of a fixed 512, or grouping similar-length examples together, would cut the wasted computation too — but the masking is the change that fixes both the number and the model.

## External resources

The PyTorch documentation for cross-entropy loss and its `ignore_index` argument, and for `pack_padded_sequence` — the production mechanisms for exactly this masking, showing how the framework lets you exclude padding (or any position) from the loss and the gradient.

The Hugging Face discussion of `attention_mask` and label masking with the -100 ignore index — how padding masking and prompt masking are handled in practice for transformer fine-tuning, generalizing the single mask here to attention and to instruction-tuning label masking.
