---
id: padmask-inter-01
title: Mask padding in the attention, not just the loss — an unmasked pad key gets attention weight and averages its filler value into every real token
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Batching sequences of different lengths requires padding the short ones up to the batch maximum with a filler token, and that filler is not nothing: a pad token has an embedding, and that embedding flows through the same projections as every real token, producing a key vector and therefore an attention score — usually an unremarkable one that sits in the query's score row looking just like a real token's. If nothing masks it, the softmax does its job on the whole row, pad included, so some of the query's attention weight lands on the pad position and the pad value gets averaged into the query's output in proportion to that weight; the token's representation is now a blend of real context and meaningless filler, and because every layer feeds the next, the contamination propagates through the whole stack. This is a different failure from masking padding out of the loss — loss masking stops filler from diluting the training signal on the output side, while attention masking stops filler from corrupting the representations on the forward-pass side — and a model can mask the loss perfectly and still be poisoned in every hidden state if it forgot the attention mask, because the damage happens before the loss is computed. The fix is to set each pad position's pre-softmax score to negative infinity: exp(−inf) is zero, so the softmax gives those positions exactly zero weight and the remaining weight over the real tokens renormalizes to sum to one. On a fixture where a query scores four keys and the last (padding) scores as high as the top real token, the unmasked softmax puts about 39% of the weight on the pad while masking gives it zero and redistributes it to the real tokens.
eli5: Imagine a group discussion where, to make every group the same size, you seat some cardboard cutouts of people at the shorter tables. The cutouts don't say anything real, but they're sitting right there. Now when a real person "listens to the table" to form their opinion, they include the cutouts' blank contributions in the average — so their opinion gets watered down with nonsense, just because the cutouts had a seat. And once one person's opinion is muddled, the next person who listens to them inherits the muddle. The fix is to tell everyone: ignore the cutouts completely, don't count them at all when you listen. In a transformer, padding tokens are those cutouts, and "attention masking" is the instruction to ignore them — set their score so low that they get zero share of the listening, so real tokens only ever absorb real tokens.
---

## Why this module

Attention is an averaging operation: each token computes a weighted average of the value vectors of the tokens it attends to, with the weights coming from a softmax over its attention scores. The quality of a token's new representation depends entirely on what it averages over, so anything that sneaks into that average corrupts the representation directly. Padding is the classic thing that sneaks in.

Padding exists only for the convenience of batching — rectangular tensors need every sequence the same length — and carries no information. But the model does not know that unless it is told. A pad token is embedded, projected, and scored like any other position, and its score is not special; there is no reason a pad key would score low against a given query. So in the raw score row, the pad position is indistinguishable from a real one, and the softmax treats it accordingly.

The consequence is that every real token, on every unmasked attention head, mixes some fraction of the pad value into its output — a fraction that can be large when the pad happens to score high. This is not a subtle numerical nuisance; it is a first-class corruption of the forward pass, present in every layer, and it is invisible if you only checked that the loss was masked. This module scores a query over a batch with one pad position and shows the attention weight leaking onto it.

**Attention averages value vectors by softmax weight, and an unmasked pad position is scored like a real one, so every real token mixes filler into its representation — a forward-pass corruption entirely separate from whether the loss was masked.**

## Concepts

The two padding masks live on opposite sides of the network and fix opposite failures, which is why doing one does not cover the other. The loss mask is on the output side: it stops the model from being trained to predict filler tokens, keeping the padding from diluting the gradient. The attention mask is on the input/hidden side: it stops real tokens from reading filler while they build their representations. The loss mask protects what the model learns; the attention mask protects what the model computes.

The order of operations is what makes the attention mask indispensable. Attention happens in every layer of the forward pass, long before the loss is calculated at the very end. So a hidden state corrupted by attending to padding is corrupted well upstream of where the loss mask acts, and no amount of output-side masking can clean a representation that was already poisoned in layer one. The loss mask cannot reach back in time to fix the forward pass.

The mechanism of the fix is worth seeing precisely. Setting a score to negative infinity before the softmax works because the softmax exponentiates: exp(−∞) is exactly zero, so the pad position contributes nothing to the normalizing sum and receives exactly zero weight. The weight it would have taken is not lost — the softmax renormalizes over the finite scores, so the real tokens' weights scale up to sum to one. The result is identical to having computed attention over only the real tokens in the first place, which is exactly what you want.

<svg role="img" aria-label="A network from input to loss: the attention mask acts at every layer on the hidden states, the loss mask acts only at the output, so a poisoned hidden state upstream cannot be fixed downstream" viewBox="0 0 440 130">
<rect x="20" y="45" width="60" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="50" y="64" fill="var(--ink)" font-size="8" text-anchor="middle">layer 1</text>
<rect x="100" y="45" width="60" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="130" y="64" fill="var(--ink)" font-size="8" text-anchor="middle">layer 2</text>
<rect x="180" y="45" width="60" height="30" fill="var(--panel)" stroke="var(--line)"/>
<text x="210" y="64" fill="var(--ink)" font-size="8" text-anchor="middle">layer N</text>
<rect x="290" y="45" width="60" height="30" fill="var(--panel)" stroke="var(--s2)"/>
<text x="320" y="64" fill="var(--ink)" font-size="8" text-anchor="middle">loss</text>
<line x1="80" y1="60" x2="100" y2="60" stroke="var(--muted)"/>
<line x1="160" y1="60" x2="180" y2="60" stroke="var(--muted)"/>
<line x1="240" y1="60" x2="290" y2="60" stroke="var(--muted)"/>
<text x="50" y="30" fill="var(--s1)" font-size="7" text-anchor="middle">attn mask</text>
<text x="130" y="30" fill="var(--s1)" font-size="7" text-anchor="middle">attn mask</text>
<text x="210" y="30" fill="var(--s1)" font-size="7" text-anchor="middle">attn mask</text>
<text x="320" y="30" fill="var(--s2)" font-size="7" text-anchor="middle">loss mask</text>
<text x="220" y="100" fill="var(--muted)" font-size="8" text-anchor="middle">the loss mask cannot reach back to clean a hidden state poisoned in layer 1</text>
</svg>
^ The attention mask must act at every layer; the loss mask acts only at the end, too late to undo an upstream representation already poisoned by padding.

**The loss mask protects what the model learns and the attention mask protects what it computes; attention runs in every layer before the loss, so a −inf score before the softmax is the only thing that keeps a hidden state from being poisoned by padding.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/below-the-prompt/code/padmask-inter-01. The fixture is one query's pre-softmax scores over four key positions, the last of which is padding and scores as high as the top real token.

```json filename=modules/below-the-prompt/code/padmask-inter-01/padmask.json:3-4 COMPLETE
  "scores": [2.0, 1.0, 0.5, 2.0],
  "is_pad": [false, false, false, true]
```

The softmax subtracts the max, exponentiates, and normalizes; a −inf score contributes zero.

```python filename=modules/below-the-prompt/code/padmask-inter-01/padmask.py:35-40 COMPLETE
def softmax(scores):
    """Stable softmax: subtract the max, exponentiate, normalize. -inf scores give zero weight."""
    m = max(s for s in scores if s != float("-inf"))
    exps = [math.exp(s - m) if s != float("-inf") else 0.0 for s in scores]
    total = sum(exps)
    return [e / total for e in exps]
```

Masking sets every pad position's score to negative infinity before that softmax.

```python filename=modules/below-the-prompt/code/padmask-inter-01/padmask.py:43-45 COMPLETE
def masked_scores(scores, is_pad):
    """Set every pad position's score to negative infinity before the softmax."""
    return [float("-inf") if pad else s for s, pad in zip(scores, is_pad)]
```

Before running it, predict: the pad position scores 2.0, tied with the top real token, so unmasked it should take a large share of the weight; masked it should take zero. Run `--weights`:

```text filename=padmask.py --weights
WEIGHTS — attention weight per key position (last is padding)
--------------------------------------------------------
  position   pad?    unmasked   masked
  0          False   0.386      0.629
  1          False   0.142      0.231
  2          False   0.086      0.140
  3          True    0.386      0.000
```

The prediction holds. Unmasked, the pad position (score 2.0) takes 0.386 of the attention — as much as the top real token — so nearly two-fifths of the query's output is the pad value. Masked, the pad gets exactly 0.000, and the three real tokens' weights rise (0.386 to 0.629, and so on) to reclaim the freed weight and sum to one.

<svg role="img" aria-label="Attention weights over four positions: unmasked gives position 0 and the pad position 3 each about 0.39; masked gives the pad 0 and raises the real positions" viewBox="0 0 440 160">
<line x1="40" y1="130" x2="410" y2="130" stroke="var(--line)"/>
<text x="120" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">unmasked</text>
<rect x="55" y="55" width="20" height="75" fill="var(--s1)"/>
<rect x="80" y="103" width="20" height="27" fill="var(--s1)"/>
<rect x="105" y="113" width="20" height="17" fill="var(--s1)"/>
<rect x="130" y="55" width="20" height="75" fill="var(--s2)"/>
<text x="140" y="49" fill="var(--s2)" font-size="8" text-anchor="middle">pad .39</text>
<text x="320" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">masked</text>
<rect x="255" y="35" width="20" height="95" fill="var(--s1)"/>
<text x="265" y="29" fill="var(--s1)" font-size="8" text-anchor="middle">.63</text>
<rect x="280" y="95" width="20" height="35" fill="var(--s1)"/>
<rect x="305" y="109" width="20" height="21" fill="var(--s1)"/>
<rect x="330" y="129" width="20" height="1" fill="var(--s2)"/>
<text x="340" y="123" fill="var(--s2)" font-size="8" text-anchor="middle">pad 0</text>
</svg>
^ Unmasked, the pad takes as much weight as the top real token; masked, it takes zero and the real tokens' weights rise to fill the gap.

Now quantify the damage. Run `--leak`:

```text filename=padmask.py --leak
LEAK — attention weight lost to padding
----------------------------------------------------
  weight on padding (unmasked) = 0.386
  weight on real tokens (unmasked) = 0.614
  weight on real tokens (masked)   = 1.000
----------------------------------------------------
  the pad steals 39% of the attention that should go to real tokens
```

Unmasked, 0.386 of the query's attention lands on padding and only 0.614 on real content — 39% of the token's new representation is filler. Masked, the real tokens get the full 1.000. That 39% is not degraded signal; it is anti-signal, a meaningless vector blended into a representation that then feeds every layer above.

<svg role="img" aria-label="The query's output composition: unmasked is 61 percent real and 39 percent pad filler; masked is 100 percent real" viewBox="0 0 440 130">
<text x="110" y="24" fill="var(--ink)" font-size="10" text-anchor="middle">unmasked output</text>
<rect x="40" y="40" width="86" height="30" fill="var(--s1)"/>
<text x="83" y="60" fill="var(--ink)" font-size="9" text-anchor="middle">real 61%</text>
<rect x="126" y="40" width="54" height="30" fill="var(--s2)"/>
<text x="153" y="60" fill="var(--ink)" font-size="8" text-anchor="middle">pad 39%</text>
<text x="330" y="24" fill="var(--ink)" font-size="10" text-anchor="middle">masked output</text>
<rect x="260" y="40" width="140" height="30" fill="var(--s1)"/>
<text x="330" y="60" fill="var(--ink)" font-size="9" text-anchor="middle">real 100%</text>
<text x="220" y="100" fill="var(--muted)" font-size="9" text-anchor="middle">the 39% filler is anti-signal, propagated into every layer above</text>
</svg>
^ Nearly two-fifths of the unmasked query's representation is filler; masking makes it entirely real content.

## Build

The self-test plants the failure and names each claim as a boolean flag. It first computes the two weightings.

```python filename=modules/below-the-prompt/code/padmask-inter-01/padmask.py:82-84 COMPLETE
    scores, is_pad = data["scores"], data["is_pad"]
    unmasked = softmax(scores)
    masked = softmax(masked_scores(scores, is_pad))
```

Then it checks that the pad gets weight unmasked and zero masked, that the real tokens are diluted unmasked but get the full weight masked, and that both weightings are valid softmaxes summing to one.

```python filename=modules/below-the-prompt/code/padmask-inter-01/padmask.py:86-99 COMPLETE
    pad_weight_unmasked = sum(w for w, p in zip(unmasked, is_pad) if p)
    pad_gets_weight = pad_weight_unmasked > 0.0
    print("  unmasked: the pad position receives attention weight = %s (%.3f)" % (pad_gets_weight, pad_weight_unmasked))

    pad_weight_masked = sum(w for w, p in zip(masked, is_pad) if p)
    pad_zero_masked = pad_weight_masked == 0.0
    print("  masked: the pad position receives zero weight = %s" % pad_zero_masked)

    real_unmasked = sum(w for w, p in zip(unmasked, is_pad) if not p)
    real_diluted = real_unmasked < 1.0 - 1e-12
    print("  unmasked: real tokens share less than all the weight = %s (%.3f)" % (real_diluted, real_unmasked))

    real_masked = sum(w for w, p in zip(masked, is_pad) if not p)
    real_full_masked = abs(real_masked - 1.0) < 1e-9
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the mask ever stops zeroing the pad or the softmax stops normalizing:

```text filename=padmask.py --check
SELF-TEST — an unmasked pad gets attention weight and leaks its value; masking gives it zero and renormalizes
----------------------------------------------------------------------------------------------------------------
  unmasked: the pad position receives attention weight = True (0.386)
  masked: the pad position receives zero weight = True
  unmasked: real tokens share less than all the weight = True (0.614)
  masked: real tokens receive all the weight = True (1.000)
  both weightings sum to one (valid softmax) = True
```

**The self-test checks the masked weights still sum to one, not just that the pad is zeroed — proving masking renormalizes over the real tokens rather than dropping weight and leaving an under-normalized distribution.**

## Definition of done

You can explain why attention is an averaging operation and why anything with attention weight enters a token's representation.
You can explain why a pad token gets a normal-looking attention score and so is indistinguishable from a real key without a mask.
You can distinguish the loss mask (output side, protects learning) from the attention mask (hidden side, protects computation) and say why one does not cover the other.
You can explain why the attention mask must act before the loss — attention runs in every layer upstream of the loss.
You can explain mechanically why a −inf pre-softmax score yields zero weight and how the remaining weight renormalizes.

## Boss fight

Consider a fully-padded row — a query position that is itself padding, attending over a row where the causal mask plus the pad mask leave nothing valid to attend to. Every score is −inf, so the softmax's normalizing sum is zero and you get 0/0, a NaN that then propagates through the network and poisons even the real positions via later operations. This is a real, notorious edge case: the fix is to detect all-masked rows and handle them (leave the pad position's output as zero, or exclude it entirely), because the −inf trick assumes at least one finite score remains. The lesson sharpens: masking is correct only where something survives the mask, and the degenerate all-masked row needs its own guard.

Now consider interaction with the causal mask, since a decoder has both. The two masks compose by union — a position is attendable only if it is neither in the future (causal) nor padding — and they are applied together as additive −inf terms on the score matrix before the single softmax. Getting the composition wrong in either direction is a bug: forget the pad mask and real tokens read filler; forget the causal mask and they read the future. A correct decoder builds one combined mask, and a common implementation error is applying the pad mask to the query dimension instead of (or as well as) the key dimension — you mask which positions are attended to, the keys, not merely which positions do the attending.

**A fully-masked row makes the softmax compute 0/0 and emit NaN, so all-masked rows need an explicit guard; and the pad and causal masks compose by union on the key dimension as additive −inf terms before one softmax — mask the keys attended to, not just the queries attending.**

## External resources

The Hugging Face documentation on the attention_mask explains how padding is masked in the attention of transformer models and why it is separate from label masking.
"The Annotated Transformer" implements the additive −inf mask before the attention softmax and shows the causal and padding masks composed into one.
The topic's own modules on masking padding out of the loss and on the causal mask cover the two sibling masks this one sits between — output-side and future-side masking.
