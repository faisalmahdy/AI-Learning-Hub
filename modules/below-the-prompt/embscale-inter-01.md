---
id: embscale-inter-01
title: Scale token embeddings by √d_model before adding positional encodings — otherwise position drowns out which token it is
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: The input to a Transformer's first layer is a sum — the token embedding (which token this is) plus the positional encoding (where in the sequence it sits) — and for that sum to carry both pieces the two addends must be of comparable magnitude; if one is much larger, it dominates the vector and the smaller becomes a rounding error the model can barely read. By default they are not comparable: token embeddings are initialized small (each component about 1/√d_model, so the whole vector has norm about 1, regardless of dimension), while sinusoidal positional encodings have components swinging across [-1, 1], so their norm grows with dimension — the bigger the model, the more the positional encoding out-sizes the token embedding. Add them as-is and the sum points almost entirely in the positional direction, with token identity a faint perturbation on top: the model receives "position 5, and barely some token" when it needed "this token, at position 5" with both legible. The fix in the original Transformer is a single multiply — scale the token embedding by √d_model before adding the positional encoding — which raises the embedding's norm from about 1 to about √d_model, the same order as the positional norm, so the two contribute on equal footing. It is a small, easily-overlooked line, and leaving it out quietly degrades the model by drowning token identity in the positional signal. On a fixture where the embedding has norm 1.0 and the positional encoding has norm 2.0, unscaled the embedding is only half the positional magnitude (ratio 0.5, 33% of the summed signal), while multiplying by √d_model=2 raises the embedding norm to 2.0, equal to the positional norm (ratio 1.0, an even 50% of the signal).
eli5: Imagine you're mixing two sounds into one track: a voice saying which word it is, and a tone saying which position in the line it is. If the tone is blasting at full volume and the voice is a whisper, the mixed track is basically just the tone — you can barely make out the word. To hear both, you turn the voice up so it's about as loud as the tone. In a Transformer, the "voice" is the token embedding (which word) and the "tone" is the positional encoding (which position); the token embedding starts out quiet, so you multiply it by a set amount (the square root of the model's width) to bring it up to the same loudness as the position signal, and now the model can hear both the word and where it sits.
---

## Why this module

The first thing a Transformer does with a token is add two vectors, and the balance between them is a design decision that is easy to miss because it is one multiplication in the embedding layer. The sum has to encode both what the token is and where it is, and a sum only preserves both addends when they are of similar size — a big vector plus a small one is, to a good approximation, just the big vector. So the relative magnitudes of the token embedding and the positional encoding decide whether the model can read token identity at all, and those magnitudes do not come out equal on their own.

They come out unequal for a specific reason. Embeddings are initialized to be small — the standard initialization gives a vector of norm around 1 no matter the dimension. Positional encodings are fixed sinusoids with values in [-1, 1], so a d-dimensional positional vector has a norm that grows with d. In any real model (d in the hundreds or thousands) the positional encoding is several times the size of the token embedding, so their raw sum is dominated by position and the token is a small correction.

The remedy is to scale the embedding up to match, and this module measures the imbalance and the fix on a small vector pair.

**Multiply token embeddings by √d_model before adding positional encodings, because embeddings are initialized to a norm of about 1 while positional encodings have a norm that grows with dimension — so without the scale the position signal dominates the sum and token identity is attenuated, while scaling makes the two comparable.**

## Concepts

The fixture is a token embedding and a positional encoding for a tiny d_model of 4. The embedding has each component 1/√4 = 0.5 (norm 1.0); the positional encoding has norm 2.0.

```json filename=modules/below-the-prompt/code/embscale-inter-01/embscale.json:3-5 COMPLETE
  "d_model": 4,
  "embedding": [0.5, 0.5, 0.5, 0.5],
  "positional": [1, 1, 1, 1]
```

The scale factor is √d_model; scaling the embedding multiplies every component by it. Norm measures each vector's magnitude, and add forms the first-layer input.

```python filename=modules/below-the-prompt/code/embscale-inter-01/embscale.py:33-47 COMPLETE
def norm(vec):
    return math.sqrt(sum(x * x for x in vec))


def scale_factor(d_model):
    return math.sqrt(d_model)


def scaled_embedding(embedding, d_model):
    s = scale_factor(d_model)
    return [x * s for x in embedding]


def add(a, b):
    return [x + y for x, y in zip(a, b)]
```

The sum view measures how much of the combined signal is token versus position — the diagnostic that shows whether token identity survives the addition.

```python filename=modules/below-the-prompt/code/embscale-inter-01/embscale.py:64-71 COMPLETE
def sum_view(data):
    emb, pos, d = data["embedding"], data["positional"], data["d_model"]
    se = scaled_embedding(emb, d)
    unscaled_sum = add(emb, pos)
    scaled_sum = add(se, pos)
    print("SUM — the first-layer input (embedding + positional)")
    print("-" * 60)
    print("  unscaled: %s   token share of norm = %.0f%%" % (unscaled_sum, 100 * norm(emb) / (norm(emb) + norm(pos))))
```

<svg role="img" aria-label="A vector sum: unscaled, a small embedding vector plus a large positional vector gives a sum pointing mostly along positional; scaled, a comparable embedding gives a balanced sum" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8" fill="var(--muted)">unscaled: sum ≈ positional</text>
  <line x1="40" y1="60" x2="120" y2="60" stroke="var(--s2)" stroke-width="3"/><text x="70" y="54" font-size="7" fill="var(--s2)">positional (2.0)</text>
  <line x1="40" y1="60" x2="80" y2="60" stroke="var(--s1)" stroke-width="3"/><text x="42" y="74" font-size="7" fill="var(--s1)">embed (1.0)</text>
  <text x="10" y="92" font-size="7" fill="var(--muted)">token = 33% of signal</text>
  <text x="180" y="14" font-size="8" fill="var(--muted)">scaled: balanced</text>
  <line x1="200" y1="60" x2="280" y2="60" stroke="var(--s2)" stroke-width="3"/><text x="228" y="54" font-size="7" fill="var(--s2)">positional (2.0)</text>
  <line x1="200" y1="60" x2="280" y2="60" stroke="var(--s1)" stroke-width="3" stroke-dasharray="3 3"/><text x="210" y="74" font-size="7" fill="var(--s1)">embed×√d (2.0)</text>
  <text x="180" y="92" font-size="7" fill="var(--muted)">token = 50% of signal</text>
</svg>
^ Unscaled, the embedding (1.0) is half the positional (2.0), so the sum is mostly positional and the token is a third of the signal. Scaling the embedding to 2.0 makes them equal, and the token becomes an even half — legible alongside position.

**A sum preserves both addends only when they are comparable in size, so the embedding must be scaled up to the positional encoding's magnitude or the token identity is swamped.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the input-embedding step of a Transformer, reduced to a 4-dimensional vector pair so every norm is checkable by hand.

Run `--norms` to see the magnitudes.

```text filename=embscale.py --norms
  positional norm            = 2.00
  embedding norm (unscaled)  = 1.00   (ratio to positional 0.50)
  embedding norm (x sqrt d)  = 2.00   (ratio to positional 1.00)
  scaling raises the embedding to the positional encoding's magnitude
```

The positional encoding has norm 2.0. The unscaled embedding has norm 1.0 — half the positional magnitude, ratio 0.50. Multiplying by √d_model = 2 raises the embedding norm to 2.0, matching the positional norm exactly (ratio 1.00). One multiplication moved the embedding from half-size to equal-size.

Now `--sum` shows what that does to the first-layer input.

```text filename=embscale.py --sum
  unscaled: [1.5, 1.5, 1.5, 1.5]   token share of norm = 33%
  scaled:   [2.0, 2.0, 2.0, 2.0]   token share of norm = 50%
  unscaled the token is the minority of the signal; scaled it is an equal half
```

Unscaled, the token contributes 33% of the combined signal — the model's input is two-thirds position, one-third token identity. Scaled, the token is 50% — an equal partner with position. The unscaled model would have to recover which token it is looking at from a third of the signal, while position takes the majority; the scaled model reads both on equal terms. And note this is d_model = 4; at a real d_model of 512 or 4096 the unscaled imbalance is far worse, because the positional norm keeps growing while the embedding norm stays around 1.

**Scaling moved the token from a third of the input to a full half, so token identity and position contribute equally — and at real model widths, where the unscaled gap is much larger, the scaling matters even more.**

## Build

The self-test asserts the imbalance and the fix: the scale is √d_model, the unscaled embedding is below the positional norm, and the positional signal dominates the unscaled sum.

```python filename=modules/below-the-prompt/code/embscale-inter-01/embscale.py:85-95 COMPLETE
    scale_is_sqrt_d = abs(scale_factor(d) - math.sqrt(d)) < 1e-9
    print("  the scale factor is sqrt(d_model) = %s (%.2f)" % (scale_is_sqrt_d, scale_factor(d)))

    embedding_underweighted = norm(emb) < norm(pos)
    print("  unscaled, the embedding norm is below the positional norm = %s (%.2f < %.2f)" % (embedding_underweighted, norm(emb), norm(pos)))

    positional_dominates_unscaled = unscaled_ratio < 0.75
    print("  unscaled, the positional signal dominates the sum = %s (embedding is %.0f%% of positional)" % (positional_dominates_unscaled, 100 * unscaled_ratio))

    scaling_raises_embedding = norm(se) > norm(emb)
    print("  scaling raises the embedding norm = %s (%.2f -> %.2f)" % (scaling_raises_embedding, norm(emb), norm(se)))
```

<svg role="img" aria-label="Token share of the summed signal: unscaled 33 percent, scaled 50 percent, with the positional filling the rest" viewBox="0 0 320 90">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">token share of the first-layer input</text>
  <text x="10" y="40" font-size="8.5" fill="var(--s2)">unscaled</text>
  <rect x="80" y="30" width="73" height="16" fill="var(--s1)"/><text x="98" y="43" font-size="7.5" fill="var(--panel)">token 33%</text>
  <rect x="153" y="30" width="147" height="16" fill="var(--muted)"/><text x="200" y="43" font-size="7.5" fill="var(--panel)">position 67%</text>
  <text x="10" y="68" font-size="8.5" fill="var(--s1)">scaled</text>
  <rect x="80" y="58" width="110" height="16" fill="var(--s1)"/><text x="110" y="71" font-size="7.5" fill="var(--panel)">token 50%</text>
  <rect x="190" y="58" width="110" height="16" fill="var(--muted)"/><text x="220" y="71" font-size="7.5" fill="var(--panel)">position 50%</text>
</svg>
^ Unscaled, position takes two-thirds of the input and the token a third; scaled, they split it evenly. The √d_model multiply is what rebalances the token's share up to parity.

Running the check confirms every clause, including that scaling makes the norms comparable and moves the ratio toward 1.

```text filename=embscale.py --check
  the scale factor is sqrt(d_model) = True (2.00)
  unscaled, the embedding norm is below the positional norm = True (1.00 < 2.00)
  unscaled, the positional signal dominates the sum = True (embedding is 50% of positional)
  scaling raises the embedding norm = True (1.00 -> 2.00)
  scaled, the embedding and positional norms are comparable = True (ratio 1.00)
  scaling moves the ratio toward 1 (equal footing) = True (0.50 -> 1.00)
```

**The check ties the unscaled positional dominance to the embedding's small init norm and shows √d_model scaling restoring parity — the one multiply that keeps token identity legible in the sum.**

## Definition of done

Two properties close it. Scaling must make the embedding and positional norms comparable (ratio near 1), and it must move the ratio toward 1 from the unscaled imbalance — the embedding raised to the positional encoding's magnitude, on equal footing. Comparable magnitude is the whole objective; the exact ratio need not be precisely 1, only close enough that neither addend swamps the other.

```python filename=modules/below-the-prompt/code/embscale-inter-01/embscale.py:97-101 COMPLETE
    comparable_after_scaling = 0.75 <= scaled_ratio <= 1.33
    print("  scaled, the embedding and positional norms are comparable = %s (ratio %.2f)" % (comparable_after_scaling, scaled_ratio))

    ratio_moves_toward_one = abs(scaled_ratio - 1) < abs(unscaled_ratio - 1)
    print("  scaling moves the ratio toward 1 (equal footing) = %s (%.2f -> %.2f)" % (ratio_moves_toward_one, unscaled_ratio, scaled_ratio))
```

Three clarifications place the scale correctly. First, √d_model here is a different scaling from the √d that appears in attention: attention divides the query-key dot product by √d_k to keep the softmax's input variance stable, while this multiplies the embedding by √d_model to match the positional encoding's magnitude — same-looking factor, unrelated purposes, both in the Transformer. Second, the specific value √d_model is tied to how embeddings are initialized (to norm ~1) and to sinusoidal positional encodings; models that use learned positional embeddings, or initialize embeddings differently, may not need this exact factor — the invariant is "make token and position comparable," and √d_model is the value that achieves it under the original paper's choices. Third, the scaling also interacts with weight tying: when the embedding matrix is shared with the output projection (a common trick), the √d_model factor helps keep the two uses on compatible scales, which is part of why the original Transformer includes it. Modern architectures often fold this into their normalization or use RoPE (which rotates rather than adds position), so you will not always see an explicit √d_model multiply — but where embeddings are added to positional encodings, the magnitudes still have to be balanced.

<svg role="img" aria-label="Two different square-root-d factors in a Transformer: multiply embeddings by sqrt(d_model) at the input, divide attention scores by sqrt(d_k) inside attention" viewBox="0 0 320 100">
  <rect x="14" y="20" width="130" height="46" fill="none" stroke="var(--s1)" stroke-width="1.2"/>
  <text x="24" y="38" font-size="8" fill="var(--ink)">input embedding</text>
  <text x="24" y="54" font-size="8.5" fill="var(--s1)">× √d_model</text>
  <rect x="176" y="20" width="130" height="46" fill="none" stroke="var(--s2)" stroke-width="1.2"/>
  <text x="186" y="38" font-size="8" fill="var(--ink)">attention scores</text>
  <text x="186" y="54" font-size="8.5" fill="var(--s2)">÷ √d_k</text>
  <text x="14" y="86" font-size="7.5" fill="var(--muted)">match positional magnitude</text>
  <text x="176" y="86" font-size="7.5" fill="var(--muted)">stabilize softmax variance</text>
</svg>
^ Two same-looking √d factors, different places and purposes: multiply embeddings by √d_model at the input (to match the positional encoding's magnitude), divide attention scores by √d_k inside attention (to keep the softmax's input variance stable). Confusing them, or applying only one, is a common bug.

**Done means scaling raises the embedding norm to the positional encoding's, moving their ratio to near 1 — token and position on equal footing in the sum, achieved by the √d_model multiply the original Transformer applies before adding positions.**

## Boss fight

An engineer implements a Transformer from the paper and it trains, but converges slowly and to a worse loss than a reference implementation, and ablations show the model is unusually weak at tasks requiring it to distinguish specific tokens (it seems to rely heavily on position). They have double-checked attention, the feedforward, and the normalization. Where should they look, and why would that cause exactly this symptom?

They should look at the input embedding layer, specifically whether they multiply the token embeddings by √d_model before adding the positional encodings — the paper includes this and it is easy to omit. If it is missing, the symptom matches exactly: token embeddings are initialized to a norm around 1, but sinusoidal positional encodings have a norm that grows with dimension, so at a realistic d_model the positional signal is several times larger than the token embedding, and their sum is dominated by position. The model's first-layer input is then mostly "where the token is" with token identity attenuated to a small fraction of the signal, which is precisely why it leans on position and struggles to distinguish specific tokens — the information about which token it is arrives too weak to use well, and training is slower because the model has to work harder to amplify that faint token signal through the layers. The fix is the one-line multiply: scale the token embeddings by √d_model (about 22.6 for d_model=512) before adding positional encodings, raising the embedding norm to the same order as the positional norm so token and position contribute comparably. This is distinct from the √d_k division inside attention (which they may have implemented correctly) — same-looking factor, different place and purpose — so checking attention would not surface it. After adding the embedding scale, token-distinguishing tasks and convergence should both improve, because the model finally receives token identity at a magnitude it can read.

## External resources

Vaswani et al., "Attention Is All You Need" (2017), section 3.4 — the original statement that token embeddings are multiplied by √d_model before adding positional encodings, alongside the sinusoidal positional encoding definition whose magnitude this balances.

The Annotated Transformer (Harvard NLP) and standard Transformer implementation walkthroughs — line-by-line implementations showing the `* math.sqrt(d_model)` in the embedding layer and clarifying that it is separate from the attention-score scaling.
