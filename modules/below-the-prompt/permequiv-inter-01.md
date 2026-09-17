---
id: permequiv-inter-01
title: Self-attention is permutation-equivariant — without positions it cannot tell "dog bites man" from "man bites dog"
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Self-attention computes each token's output as a softmax-weighted average of every token's value, with weights from dot products between tokens — and nothing in that computation refers to where a token sits, only to which tokens are present. The consequence is exact: permute the input rows by any permutation π and every output row comes out permuted by the same π, otherwise unchanged, so attn(permute(X)) equals permute(attn(X)). Attention commutes with reordering. On the fixture the three orthonormal token embeddings dog, bites, man attend to give outputs [0.471, 0.264, 0.264], [0.264, 0.471, 0.264], [0.264, 0.264, 0.471]; reverse the sequence to man, bites, dog and the outputs are exactly those three rows reversed, and an order-blind readout — mean pooling — returns the byte-identical [0.333, 0.333, 0.333] for both orders. That is a model that cannot represent word order at all, and word order is most of syntax. The fix is to inject position before attention: add a per-position vector p_i to whatever token lands at position i, so position 0 always contributes p_0. Now permuting the tokens no longer permutes the augmented input — the token that moves to position 0 picks up p_0, not the vector it carried before — so the pooled vector changes from [0.500, 0.500, 0.500] to [0.485, 0.530, 0.485] and the two word orders become distinguishable. The rule: raw attention treats a sentence as a bag of tokens, and every positional scheme — learned embeddings, RoPE, ALiBi — exists to break that symmetry so order can be represented.
eli5: Imagine a group of people at a round table where everyone listens to everyone and then updates what they think — but nobody knows their seat number, only who else is in the room. If you shuffle who sits where, nothing about the conversation changes: the same people are talking to the same people, so the same thoughts come out, just in shuffled seats. That means the group literally cannot tell one seating from another — and for words, the "seating" is the order, so "dog bites man" and "man bites dog" would feel exactly the same to it. To fix this you pin a little name-tag to each seat, "seat 0", "seat 1", and give whoever sits there that seat's tag. Now shuffling really does change things, because seat 0's tag stays on seat 0 no matter who moves into it — and the group can finally tell the two seatings apart.
---

## Why this module

Every positional-encoding scheme — learned position embeddings, sinusoids, RoPE, ALiBi — answers a question this module asks: why does attention need positions bolted on at all? Other layers do not get a special "where am I" input. The answer is that plain self-attention has a symmetry so strong it erases order entirely, and the positional scheme exists only to break it.

Seeing the symmetry directly makes every later position trick make sense. They are not adding a nice-to-have signal; they are repairing a model that, on its own, treats a sentence as an unordered bag of tokens.

**Raw self-attention cannot represent word order — positional encodings exist to break a symmetry, not to add a feature.**

## Concepts

Permutation equivariance is the precise name for the symmetry. A function f is permutation-equivariant if reordering its inputs reorders its outputs the same way and changes nothing else: f(permute(X)) = permute(f(X)). Self-attention is exactly such a function.

Look at where position could enter. Each output is a weighted average of value vectors, and each weight is a softmax over dot products between one token and every token. Both the dot products and the averaging range over the set of tokens; neither carries an index that says "this is the third token." So if you relabel which row is first, second, third, every dot product between the same two tokens is unchanged — it just appears at a different pair of indices — and the outputs are the same vectors, relocated to match.

The damaging consequence follows from equivariance plus any order-blind readout. Mean pooling averages the output vectors, and the average of a set does not depend on the order of the set. So a sentence and any anagram of it — same tokens, different order — produce the same multiset of outputs and therefore the identical pooled vector. "dog bites man" and "man bites dog" are indistinguishable to such a model, and telling them apart is the whole job of syntax.

The fix injects position before attention runs. Add a fixed per-position vector p_i to whatever token occupies position i. Now the input to attention is token-plus-position, and position i's contribution p_i stays at position i regardless of which token sits there. Permuting the tokens no longer produces a permutation of this augmented input, because the moved token picks up its new seat's vector, not its old one — so equivariance is broken on purpose and the outputs finally depend on order.

**Attention ranges over the set of tokens, so it is blind to order; adding a per-position vector ties each slot to a fixed contribution and makes order visible.**

<svg role="img" aria-label="A commutative square. Top edge: X goes through attention to output Y. Left edge: permuting X. Bottom edge: permuted X goes through attention. Right edge: permuting Y. Both paths from X reach the same permuted output, showing attention commutes with permutation." viewBox="0 0 420 180">
<rect x="0" y="0" width="420" height="180" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">both paths reach the same place: attn commutes with permute</text>
<text x="60" y="60" fill="var(--ink)" font-size="12">X</text>
<text x="330" y="60" fill="var(--ink)" font-size="12">attn(X)</text>
<text x="46" y="150" fill="var(--ink)" font-size="12">permute(X)</text>
<text x="300" y="150" fill="var(--ink)" font-size="12">permute(attn(X))</text>
<line x1="80" y1="55" x2="320" y2="55" stroke="var(--line)"></line>
<text x="170" y="48" fill="var(--muted)" font-size="9">attn</text>
<line x1="65" y1="70" x2="65" y2="135" stroke="var(--line)"></line>
<text x="70" y="105" fill="var(--muted)" font-size="9">permute</text>
<line x1="355" y1="70" x2="355" y2="135" stroke="var(--line)"></line>
<text x="360" y="105" fill="var(--muted)" font-size="9">permute</text>
<line x1="130" y1="145" x2="295" y2="145" stroke="var(--s1)"></line>
<text x="190" y="138" fill="var(--s1)" font-size="9">attn</text>
</svg>
^ Attention then permute equals permute then attention — the square commutes, which is permutation equivariance stated as a picture.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/below-the-prompt/code/permequiv-inter-01/permequiv.py

The fixture uses orthonormal one-hot embeddings so the arithmetic is transparent, and reverses the sequence as the permutation.

```json filename=modules/below-the-prompt/code/permequiv-inter-01/permequiv.json:3-6 COMPLETE
  "tokens": {"dog": [1.0, 0.0, 0.0], "bites": [0.0, 1.0, 0.0], "man": [0.0, 0.0, 1.0]},
  "sequence": ["dog", "bites", "man"],
  "permutation": [2, 1, 0],
  "position_vectors": [[0.5, 0.0, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 0.5]]
```

Attention is query = key = value = X, with no positional term anywhere in it.

```python filename=modules/below-the-prompt/code/permequiv-inter-01/permequiv.py:42-51 COMPLETE
def attention(X):
    """Scaled dot-product self-attention with query=key=value=X (no positional term anywhere)."""
    d = len(X[0])
    scale = math.sqrt(d)
    out = []
    for xi in X:
        scores = [dot(xi, xj) / scale for xj in X]
        w = softmax(scores)
        out.append([sum(w[j] * X[j][k] for j in range(len(X))) for k in range(d)])
    return out
```

The permutation just reorders rows.

```python filename=modules/below-the-prompt/code/permequiv-inter-01/permequiv.py:54-56 COMPLETE
def permute(rows, perm):
    """Reorder the rows: new row i is old row perm[i]."""
    return [rows[p] for p in perm]
```

Run it with no positions and reordering only reorders the outputs.

```text filename=permequiv.py --nopos
NO-POS — attention on ['dog', 'bites', 'man'] vs its reversal ['man', 'bites', 'dog']
------------------------------------------------------------------------
  out[dog   ] = [0.471, 0.264, 0.264]
  out[bites ] = [0.264, 0.471, 0.264]
  out[man   ] = [0.264, 0.264, 0.471]
  reversed sequence outputs equal the reversed original outputs? True
  mean pool (original) = [0.333, 0.333, 0.333]
  mean pool (reversed) = [0.333, 0.333, 0.333]
```

The reversed sequence's outputs are exactly the original outputs reversed — equivariance, confirmed True. And mean pooling returns [0.333, 0.333, 0.333] for both orders: the two sentences are the same to any pooled readout. A classifier reading that pooled vector could never separate "dog bites man" from "man bites dog".

<svg role="img" aria-label="Two rows. Top: input tokens dog, bites, man go through attention to outputs A, B, C. Bottom: the reversed input man, bites, dog goes through the same attention to outputs C, B, A -- the same three outputs in reversed order." viewBox="0 0 480 160">
<rect x="0" y="0" width="480" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">attention commutes with reordering (no positions)</text>
<text x="20" y="52" fill="var(--muted)" font-size="10">dog bites man</text>
<rect x="150" y="38" width="60" height="20" fill="none" stroke="var(--line)"></rect>
<text x="158" y="52" fill="var(--ink)" font-size="10">attn</text>
<text x="230" y="52" fill="var(--s2)" font-size="10">A B C</text>
<text x="20" y="102" fill="var(--muted)" font-size="10">man bites dog</text>
<rect x="150" y="88" width="60" height="20" fill="none" stroke="var(--line)"></rect>
<text x="158" y="102" fill="var(--ink)" font-size="10">attn</text>
<text x="230" y="102" fill="var(--s2)" font-size="10">C B A</text>
<text x="20" y="140" fill="var(--s1)" font-size="10">mean pool of {A,B,C} = mean pool of {C,B,A} &#8594; identical</text>
</svg>
^ The reversed sentence produces the same three output vectors in reversed order, so any order-blind pooling of them is the same vector — the two orders are indistinguishable.

## Build

Adding positions breaks the symmetry. The position vector for slot i is added to whatever token lands there.

```python filename=modules/below-the-prompt/code/permequiv-inter-01/permequiv.py:59-61 COMPLETE
def add_positions(X, P):
    """Add the position vector P[i] to whatever token sits at position i."""
    return [[x + p for x, p in zip(X[i], P[i])] for i in range(len(X))]
```

```text filename=permequiv.py --withpos
WITH-POS — add position vectors, then attention on ['dog', 'bites', 'man'] vs ['man', 'bites', 'dog']
------------------------------------------------------------------------
  mean pool (original) = [0.500, 0.500, 0.500]
  mean pool (reversed) = [0.485, 0.530, 0.485]
  reversed outputs still equal the reversed original outputs? False
```

Now the pooled vectors differ — [0.500, 0.500, 0.500] versus [0.485, 0.530, 0.485] — and the reversed sequence no longer gives the reversed outputs. The reason is exactly that position 0 always adds p_0: when "man" moves to the front it picks up p_0 = [0.5, 0, 0] instead of the p_2 it had at the end, so the augmented input for "man bites dog" is not a permutation of the augmented input for "dog bites man". Order is now represented.

<svg role="img" aria-label="Slot 0 always adds position vector p0 regardless of token. In dog-bites-man, dog sits in slot 0 and gets p0. In man-bites-dog, man sits in slot 0 and gets p0 instead. So the two augmented inputs are not permutations of each other." viewBox="0 0 480 150">
<rect x="0" y="0" width="480" height="150" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">position vector p&#8320; stays on slot 0, whatever token moves in</text>
<text x="20" y="52" fill="var(--muted)" font-size="10">slot 0</text>
<text x="20" y="70" fill="var(--muted)" font-size="10">slot 0</text>
<text x="80" y="52" fill="var(--s2)" font-size="10">dog + p&#8320;</text>
<text x="80" y="70" fill="var(--s1)" font-size="10">man + p&#8320;</text>
<text x="200" y="52" fill="var(--muted)" font-size="10">(order 1: dog first)</text>
<text x="200" y="70" fill="var(--muted)" font-size="10">(order 2: man first)</text>
<text x="20" y="112" fill="var(--ink)" font-size="10">different token gets p&#8320; &#8594; augmented inputs are not permutations</text>
<text x="20" y="132" fill="var(--s1)" font-size="10">&#8594; outputs and pooled vector differ &#8594; order is representable</text>
</svg>
^ Because slot 0's contribution p₀ is fixed, swapping which token occupies slot 0 changes the input in a way reordering alone never could — the symmetry that erased order is gone.

The self-test runs both directions: equivariant and order-invariant without positions, both broken with them.

```python filename=modules/below-the-prompt/code/permequiv-inter-01/permequiv.py:131-135 COMPLETE
    equivariant = rows_close(outr, permute(out, perm))
    print("  no-pos: attn(reverse(X)) == reverse(attn(X)) (permutation-equivariant) = %s" % equivariant)

    pooled_invariant = rows_close([mean_pool(out)], [mean_pool(outr)])
    print("  no-pos: mean pool is identical for both orders (order-invariant) = %s" % pooled_invariant)
```

```text filename=permequiv.py --check
SELF-TEST — without positions attention is permutation-equivariant and the pooled readout is order-invariant, while adding positions breaks both
----------------------------------------------------------------------------------------------------------------
  no-pos: attn(reverse(X)) == reverse(attn(X)) (permutation-equivariant) = True
  no-pos: mean pool is identical for both orders (order-invariant) = True
  with-pos: attn(reverse) != reverse(attn) (equivariance broken) = True
  with-pos: mean pool differs between the two orders (order now matters) = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  equivariant=True  pooled_invariant=True  equivariance_broken=True  pooled_differs=True
```

**Equivariance is not a defect in the attention code — it is what attention is; the defect would be shipping it without a positional scheme to break the symmetry.**

## Definition of done

You can state permutation equivariance precisely — attn(permute(X)) = permute(attn(X)) — and point to the exact reason it holds: attention ranges over the set of tokens and never over their indices.

You can explain why an order-blind readout turns equivariance into order-invariance, so a sentence and its anagram become identical, and why that is fatal for anything order-dependent.

You can describe how adding a per-position vector breaks the symmetry, and specifically why "the same token in a different slot gets a different position vector" is what reordering alone can never reproduce.

You can place the standard positional schemes as instances of this one fix: learned absolute embeddings add a p_i like the fixture; RoPE and ALiBi break the symmetry inside the attention scores instead of on the inputs, but all exist for this reason.

## Boss fight

A colleague builds a sentence classifier: embed the tokens, run one self-attention layer, mean-pool the outputs, feed a linear head. It trains to decent accuracy on topic classification but scores at chance on any task where word order matters — sentiment with negation, subject-versus-object, anything syntactic.

First: explain, from permutation equivariance, why this architecture is exactly at chance on order-dependent tasks and yet fine on topic classification. What property of the task decides which bucket it falls in?

Then: they propose fixing it by stacking more attention layers. Does depth alone break the symmetry? Argue whether a stack of position-free attention layers followed by mean pooling is still order-invariant, and identify the one component that must change.

Finally: they add learned absolute position embeddings and it works — until they evaluate on sentences longer than any seen in training, where accuracy collapses. Connect that failure back to this module (the position vectors for unseen slots) and name which alternative schemes from the topic were designed to avoid it and why.

## External resources

The original "Attention Is All You Need" adds sinusoidal positional encodings in its very first section, and its one-line justification — that the model is otherwise permutation-invariant — is the fact this module demonstrates from scratch.

Work on set-based architectures (Deep Sets, Set Transformer) uses the same equivariance deliberately, building models that should be order-blind — the mirror image of this module, where the symmetry is the goal rather than the bug.
