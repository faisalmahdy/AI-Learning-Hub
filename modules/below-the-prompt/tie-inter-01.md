---
id: tie-inter-01
title: Tie the output projection to the input embedding — or you pay twice for the same token vectors
topic: below-the-prompt
level: intermediate
status: ready
time: 21 min
summary: A language model uses one vector per vocabulary token at the input (the embedding) and again at the output (the unembedding that produces logits). Left independent, those are two matrices of the same shape — double the vocabulary parameters, learned separately. Weight tying sets the unembedding equal to the embedding, halving those parameters and putting a token's input and output representations in one space. On a 4-token, 3-dim toy, untied uses 24 parameters and can score a hidden state that equals a token's embedding for the wrong token; tied uses 12 and always scores the right one.
eli5: A model has a little dictionary that turns each word into a list of numbers when reading, and another that turns numbers back into word-scores when writing. Weight tying says: use the same dictionary both ways. You store half as many numbers, and a word you were clearly "thinking of" automatically gets the top score — because reading and writing now speak the same language.
---

## Why this module

A model represents every vocabulary token as a vector twice — once to read it and once to predict it — and keeping those two representations separate is often pure waste.

A language model meets its vocabulary at both ends of the network. At the input, it embeds each token: it looks up a vector for the token in an embedding matrix that has one row per vocabulary word and one column per model dimension. At the output, it does the reverse — it takes the final hidden state and produces a score (a logit) for every vocabulary word, by multiplying the hidden state against an unembedding matrix that, again, has one vector per word. Both ends need a vector per token, and by default those are two different matrices of exactly the same shape.

That duplication is expensive and unconstrained. In a real model the vocabulary is large (tens of thousands of tokens) and these two matrices can together account for a big fraction of all parameters — a serious cost that scales with vocabulary size. And because the embedding and the unembedding are separate sets of weights learned independently, there is nothing tying a token's input vector to its output vector; the model must learn twice, from scratch, how each token is represented in each direction, with no guarantee the two agree.

Weight tying removes both problems by setting the unembedding equal to the embedding. The same matrix that turns a token into a vector on the way in is used to score it on the way out, so the logit for token t is simply the dot product of the hidden state with token t's own embedding. This halves the vocabulary parameters — one matrix instead of two — and it couples the two representations into a single shared space: a hidden state that has moved toward a token's embedding automatically gives that token a high logit, because scoring is measuring alignment with the very same vectors. Empirically, tying does not hurt and usually improves perplexity, which is why most modern language models tie these weights.

On the fixture, a tiny model has 4 tokens and a 3-dimensional hidden state. Untied, the embedding and unembedding are two 4×3 matrices — 24 parameters — and because the unembedding is unrelated to the embedding, a hidden state equal to a token's embedding can be scored highest for a different token. Tied, there is one 4×3 matrix — 12 parameters — and a hidden state equal to token t's embedding always scores token t highest.

**A model uses a vector per token at both input and output, so an untied model stores and learns two independent vocabulary matrices; weight tying sets the output projection equal to the input embedding, halving those parameters and putting a token's input and output representations in one shared space, with no loss (often a gain) in quality.**

## Concepts

The output projection and the input embedding are doing mirror-image jobs, which is why sharing them is natural. The embedding answers "what vector represents this token?" The unembedding answers "how much does this hidden state look like each token?" — a logit per token. If a token is represented by a vector, then the most sensible way to ask whether a hidden state predicts that token is to measure the hidden state's alignment with that same vector. Tying makes the output ask exactly that question against the input's own vectors, so the two operations become adjoint: embed with a matrix, unembed with its transpose. The model no longer maintains two opinions about what a token's vector is.

<svg role="img" aria-label="Untied stores two separate vocab-by-dim matrices; tied stores one and reuses it at both the input and the output" viewBox="0 0 470 175" width="470" height="175">
  <rect x="0" y="0" width="470" height="175" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">untied: two matrices; tied: one, used both ways</text>
  <text x="30" y="46" font-family="var(--mono)" font-size="9" fill="var(--s2)">untied</text>
  <rect x="30" y="54" width="60" height="46" fill="var(--panel)" stroke="var(--s2)"/>
  <text x="34" y="80" font-family="var(--mono)" font-size="7" fill="var(--s2)">E (in)</text>
  <rect x="110" y="54" width="60" height="46" fill="var(--panel)" stroke="var(--s2)"/>
  <text x="114" y="80" font-family="var(--mono)" font-size="7" fill="var(--s2)">U (out)</text>
  <text x="34" y="116" font-family="var(--mono)" font-size="7" fill="var(--muted)">2 x vocab x dim</text>
  <text x="280" y="46" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">tied</text>
  <rect x="280" y="54" width="60" height="46" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="286" y="80" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">E = U</text>
  <path d="M280,64 Q250,50 280,44" fill="none" stroke="var(--acc-line)"/>
  <text x="350" y="62" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">← embeds input</text>
  <text x="350" y="94" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">← scores output</text>
  <text x="280" y="116" font-family="var(--mono)" font-size="7" fill="var(--muted)">1 x vocab x dim (half)</text>
</svg>
^ The untied model keeps a separate input embedding and output projection; the tied model keeps one matrix and uses it for both, halving the vocabulary parameters.

The parameter saving is direct and large at scale. Each vocabulary matrix has vocab × dim entries; two of them is 2 × vocab × dim, and tying makes it vocab × dim — an exact halving of the token-vector parameters. For a model with a 50,000-token vocabulary and a 1,000-dimensional model, that is 50 million parameters saved, which for smaller models is a substantial share of the whole. The saving is free in the sense that it removes parameters the model turned out not to need as separate quantities — the tied model reaches the same or better quality with half the vocabulary weights, so the untied model was spending capacity to relearn a relationship tying gives for nothing.

The representational benefit is subtler and is the reason tying tends to help rather than merely not hurt. Tying forces the geometry of "tokens as inputs" and "tokens as prediction targets" to be the same geometry. A hidden state that the network has pushed toward a token's embedding is, by construction, a hidden state that scores that token highly — input similarity and output preference are the same measurement. In an untied model these are two unrelated spaces, so the network has to independently arrange the unembedding to agree with the embedding, wasting capacity and risking inconsistency. The demonstration below makes this concrete: with tied weights, a hidden state equal to a token's embedding always predicts that token; with an unrelated untied unembedding, it need not.

Tying is standard, with a few caveats worth knowing. It assumes the input and output vector spaces should be the same, which is almost always desirable for a language model but requires the input and output dimensions to match (they do, both being the model dimension). Some architectures scale the tied embedding differently in its two uses (a scaling factor on the input side) or share weights only partially. And tying couples two roles, so a token that should embed and predict differently cannot — rarely a problem in practice. The technique traces to early work (Press and Wolf's "Using the Output Embedding to Improve Language Models," and the closely related weight-tying in pointer networks and the original transformer), and it is on by default in most language-model implementations because the cost is negative and the quality is equal or better.

**Embedding and unembedding are mirror operations — represent a token, and measure alignment with that representation — so tying makes them adjoint, exactly halving the vocabulary parameters and forcing input similarity and output preference into one geometry, which is why a token the hidden state resembles is automatically the token it predicts.**

## Worked example

The fixture is a tiny model's embedding and a separate untied unembedding.

```json filename=modules/below-the-prompt/code/tie-inter-01/model.json:3-14 COMPLETE
  "embed": [
    [2, 0, 0],
    [0, 2, 0],
    [0, 0, 2],
    [1, 1, 1]
  ],
  "unembed": [
    [0, 0, 3],
    [3, 0, 0],
    [0, 1, 0],
    [1, 1, 0]
  ]
```

Four tokens, three dimensions. The embedding gives each token a vector; the untied unembedding is a separate matrix, chosen unrelated to the embedding. A logit is the hidden state dotted with each token's row of whichever matrix scores the output.

```python filename=modules/below-the-prompt/code/tie-inter-01/tie.py:46-48 COMPLETE
def logits(hidden, matrix):
    """One logit per token: the hidden state dotted with each token vector (row of the matrix)."""
    return [dot(hidden, row) for row in matrix]
```

Tying is the one-line choice: the unembedding is the embedding itself.

```python filename=modules/below-the-prompt/code/tie-inter-01/tie.py:59-61 COMPLETE
def tied_matrix(embed):
    """Tied: the unembedding IS the embedding."""
    return embed
```

A matrix's parameter count is just its rows times its columns — vocab by dim.

```python filename=modules/below-the-prompt/code/tie-inter-01/tie.py:55-56 COMPLETE
def n_params(matrix):
    return len(matrix) * len(matrix[0])
```

First the parameter count. Predict: untied is two 4×3 matrices (24), tied is one (12).

```text filename=modules/below-the-prompt/code/tie-inter-01/tie.py --params
PARAMS — vocabulary matrix parameters, untied vs tied
----------------------------------------------------
  untied: embed 12 + unembed 12 = 24
  tied:   one shared matrix       = 12
----------------------------------------------------
  tying halves the vocabulary parameters.
```

Untied stores 24 parameters in its two matrices; tied stores 12 in its one — an exact halving. Now the representational test: set the hidden state equal to each token's embedding in turn, and ask which token each model scores highest. A consistent model should predict token t when its hidden state is token t's own embedding.

```text filename=modules/below-the-prompt/code/tie-inter-01/tie.py --score
SCORE — for hidden = each token's embedding, the top-scoring token
----------------------------------------------------------
  hidden = E[t]   untied top    tied top   (want t)
  t=0             1             0          ok
  t=1             2             1          ok
  t=2             0             2          ok
  t=3             0             3          ok
```

The tied column recovers the target every time: hidden = E[0] scores token 0 highest, E[1] scores token 1, and so on, because scoring is a dot product against the same embeddings and a vector's largest alignment is with itself. The untied column is scrambled — hidden = E[0] scores token 1 highest, E[1] scores token 2, E[2] and E[3] both score token 0 — because the unrelated unembedding measures alignment in a different geometry, so "looks like token 0 on input" does not mean "predicts token 0 on output." Same hidden states; tying makes input and output agree, and untying lets them disagree.

<svg role="img" aria-label="For hidden equal to each token's embedding, the tied model's top token matches the index on the diagonal, while the untied model's top tokens are scattered off the diagonal" viewBox="0 0 470 190" width="470" height="190">
  <rect x="0" y="0" width="470" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">top-scored token when hidden = E[t] (rows t=0..3)</text>
  <text x="120" y="40" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">tied (diagonal)</text>
  <text x="320" y="40" font-family="var(--mono)" font-size="9" fill="var(--s2)">untied (scattered)</text>
  <g font-family="var(--mono)" font-size="9">
    <text x="40" y="70" fill="var(--muted)">t=0</text><text x="40" y="98" fill="var(--muted)">t=1</text><text x="40" y="126" fill="var(--muted)">t=2</text><text x="40" y="154" fill="var(--muted)">t=3</text>
  </g>
  <g fill="var(--acc-line)"><circle cx="120" cy="66" r="7"/><circle cx="150" cy="94" r="7"/><circle cx="180" cy="122" r="7"/><circle cx="210" cy="150" r="7"/></g>
  <g fill="var(--panel)" font-family="var(--mono)" font-size="8"><text x="117" y="69">0</text><text x="147" y="97">1</text><text x="177" y="125">2</text><text x="207" y="153">3</text></g>
  <text x="120" y="172" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">always token t ✓</text>
  <g fill="var(--s2)"><circle cx="330" cy="94" r="7"/><circle cx="360" cy="122" r="7"/><circle cx="300" cy="66" r="7"/><circle cx="300" cy="150" r="7"/></g>
  <g fill="var(--panel)" font-family="var(--mono)" font-size="8"><text x="327" y="97">1</text><text x="357" y="125">2</text><text x="297" y="69">0</text><text x="297" y="153">0</text></g>
  <text x="300" y="172" font-family="var(--mono)" font-size="7" fill="var(--s2)">off-diagonal — wrong token</text>
</svg>
^ The tied model's top token lies on the diagonal (hidden = E[t] predicts t) for every token; the untied model's top tokens fall off the diagonal, predicting a different token than the one the hidden state matches.

## Build

Reproduce the counts and scores. Pure standard library, deterministic, so the 24-versus-12 parameters and the diagonal-versus-scattered predictions come out exactly.

Run `--params` for the counts, `--score` for the per-token top prediction, `--check` for the gate. <svg role="img" aria-label="Vocabulary parameters at a realistic scale: untied about 33 million, tied about 16 million, half the size" viewBox="0 0 470 150" width="470" height="150">
  <rect x="0" y="0" width="470" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">vocab params at vocab 32k, dim 512 — the saving scales</text>
  <line x1="60" y1="120" x2="450" y2="120" stroke="var(--line)"/>
  <rect x="90" y="40" width="90" height="80" fill="var(--s2)"/>
  <text x="92" y="34" font-family="var(--mono)" font-size="8" fill="var(--s2)">untied ~33M</text>
  <rect x="290" y="80" width="90" height="40" fill="var(--acc-line)"/>
  <text x="292" y="74" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">tied ~16M</text>
  <text x="150" y="140" font-family="var(--mono)" font-size="8" fill="var(--muted)">tying frees ~16M parameters — a big share of a small model</text>
</svg>
^ The 4×3 toy hides how large this gets: at a 32,000-token vocabulary and 512 dimensions, tying removes about 16 million parameters, so the win grows with vocabulary size.

The self-test pins the halving and the consistency.

```python filename=modules/below-the-prompt/code/tie-inter-01/tie.py:94-98 COMPLETE
    tied_halves_params = n_params(embed) == (n_params(embed) + n_params(unembed)) // 2
    print("  tied uses half the vocabulary parameters = %s (%d vs %d)"
          % (tied_halves_params, n_params(embed), n_params(embed) + n_params(unembed)))

    tied_self_consistent = all(argmax(logits(embed[t], tied_matrix(embed))) == t for t in range(len(embed)))
    print("  tied: hidden = E[t] always scores token t highest = %s" % tied_self_consistent)
```

```text filename=modules/below-the-prompt/code/tie-inter-01/tie.py --check
SELF-TEST — tying halves the parameters and makes input and output representations consistent
------------------------------------------------------------------------------------------------
  tied uses half the vocabulary parameters = True (12 vs 24)
  tied: hidden = E[t] always scores token t highest = True
  untied: hidden = E[t] can score a different token highest = True
  tied: the unembedding is literally the embedding = True
  tied has fewer parameters than untied = True (12 < 24)
------------------------------------------------------------------------------------------------
SELF-TEST PASS  tied_halves_params=True  tied_self_consistent=True  untied_can_disagree=True  tied_reuses_embedding=True  tied_fewer_params=True
```

Five True flags. Tied_halves_params: 12 is exactly half of 24. Tied_self_consistent: with tied weights, hidden = E[t] scores token t highest for every token. Untied_can_disagree: with the unrelated unembedding, at least one hidden = E[t] scores a different token. Tied_reuses_embedding: the tied unembedding is literally the embedding object. Tied_fewer_params: 12 is fewer than 24. The self-consistency flag is the one that shows the representational win — tying does not just save memory, it aligns the two vocabulary geometries so the model's input and output views of a token agree.

**The self-consistency flag is the deeper payoff — tying guarantees that a hidden state resembling a token's embedding predicts that token, so it removes both the duplicated parameters and the freedom for the two vocabulary geometries to disagree.**

## Definition of done

You are done when you reproduce the halved parameters and the consistency difference, and can explain why tying helps.

Concretely: `--params` shows untied at 24 and tied at 12; `--score` shows tied recovering token t for every hidden = E[t] while untied scatters; `--check` prints PASS with five True flags. You can explain that embedding and unembedding are mirror operations (represent a token; measure alignment with that representation), that tying makes them adjoint and exactly halves the vocabulary parameters, and that it forces input similarity and output preference into one geometry so a token the hidden state resembles is the token it predicts. You can name the caveats: input/output dimensions must match, some models scale the two uses differently, and tying couples the two roles.

The habit to carry: tie the output projection to the input embedding in any language model unless you have a specific reason not to — it halves a large parameter block and typically improves perplexity. When a small model spends a surprising fraction of its parameters on the vocabulary, or when the embedding and unembedding are learned separately for no reason, suspect untied weights and tie them. Reuse the token vectors rather than paying for two sets.

## Boss fight

The instructive failure is a small model bloated and slightly worse because its vocabulary weights are untied.

A team trains a compact language model with a 32,000-token vocabulary and a 512-dimensional hidden size. The embedding and the output projection are separate, so the two matrices together hold 32k × 512 × 2 ≈ 33 million parameters — a large share of a small model — and the model both trains slower and reaches a slightly worse perplexity than a tied baseline, because it spends capacity learning two independent vocabulary geometries that ought to agree. Tying the weights removes 16 million parameters and matches or beats the untied perplexity, and it is a one-line change (share the matrix). The tell is a small model whose parameter budget is dominated by two same-shaped vocabulary matrices.

Your turn, two moves. First, scale the saving: recompute the parameter counts at a realistic vocab (say 32,000) and dim (512) and confirm tying removes tens of millions of parameters, so the win grows with vocabulary size — which is why tying matters more for small models where the vocabulary is a big fraction of the whole. Second, probe the caveat: make the input and output dimensions differ (a model that projects to a different size before the vocabulary) and confirm you cannot tie directly without a projection to reconcile the shapes — the one structural requirement, that the two token-vector spaces have the same dimension.

## External resources

Press and Wolf's "Using the Output Embedding to Improve Language Models" (2017) is the standard reference showing that tying the input and output embeddings reduces parameters and improves perplexity, with the theory of why the two should share a space.

The original Transformer paper ("Attention Is All You Need") ties the embedding and the pre-softmax linear transformation (with a scaling factor), and most open language-model implementations (GPT-2, and many since) tie these weights by default — reading their config for a "tie_word_embeddings" flag shows the practice.

Any language-model implementation guide's section on the embedding and LM head covers the shapes (vocab × dim), the memory cost, and how tying shares the matrix, which grounds the parameter arithmetic this module computes.
