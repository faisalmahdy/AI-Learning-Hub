---
id: attnmlp-inter-01
title: Attention communicates, the MLP computes — attention only averages values, so it never leaves their range
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Read the attention formula for what it does to values — each output is a sum of weight times value, and the weights come from a softmax, so they are all non-negative and sum to one, which makes the output a weighted average of the value vectors, a convex combination. A weighted average is bounded: no larger than the largest value, no smaller than the smallest. So whatever the attention weights are, the output stays inside the range its inputs span; attention can route, mix, and select information across positions, but it cannot manufacture a value outside the hull of what it was given, and in particular cannot compute a nonlinear function of a single token's features. The MLP is the block that computes per token — a hidden layer with a nonlinearity, then a projection — and because of the nonlinearity its output is not a weighted average of its input and can land outside the input range entirely. On the fixture the values are 1, 3, 2, so every attention output for every weighting lands in [1, 3] (0.333/0.333/0.333 gives 2.000, a peaked weighting gives 2.864, none escapes), while the MLP relu(x − 2)·4 maps 3 to 4 (above the range) and 1 to 0 (below it). This is the structural reason a transformer needs both blocks and the correction to the common phrase that "attention is where the thinking happens": attention communicates, the MLP computes. Strip the MLP out and every layer can only take weighted averages, and stacking weighted averages still gives a weighted average, so no nonlinear function of a single input is reachable at all. The rule: attention moves information between tokens, the MLP transforms each token, and only the second can leave the convex hull of its inputs.
eli5: Picture each token as a point, and a layer's job is to make new points. Attention makes a new point by blending existing points — like mixing paints. No matter how you mix red, blue, and green paint, you get some color that sits among them; you can never mix your way to a color brighter than all three, because a blend is always somewhere in the middle. That is attention: it blends what the tokens already have. To get a genuinely new color — brighter, or a shade outside the mix — you need a step that transforms a point instead of blending points, and that is the MLP, which can push a value past the range of everything it started with. So attention shares information between tokens, and the MLP is where a token actually gets reshaped; you need both.
---

## Why this module

It is common to say the Transformer's power lives in attention — that attention is where the model "reasons." Attention is the famous part, and it is genuinely what makes the architecture work across long contexts. But it is worth being precise about which block does what, because attention alone, no matter how many layers you stack, cannot compute most functions.

The reason is a one-line fact about the attention formula that is easy to skip past: its output is an average. Averages are bounded. Once you see that, the division of labor in a Transformer block — attention then MLP — stops looking like two similar layers and starts looking like two complementary operations, one that moves information and one that transforms it.

**Attention's output is a weighted average of values, so it is confined to the range of its inputs; the MLP is the only block that can leave that range.**

## Concepts

Attention computes each output as a sum over positions of a weight times that position's value vector. The weights are a softmax of the attention scores, and a softmax always produces non-negative numbers that sum to one. A sum of values with non-negative weights that sum to one is, by definition, a convex combination — a weighted average.

A weighted average has a hard property: it lies within the convex hull of the things averaged. In one dimension that means the output is between the smallest and the largest value; in higher dimensions it means the output is inside the polytope spanned by the value vectors. There is no choice of attention weights that escapes it. Put all the weight on the largest value and you reach that value exactly, never past it. So attention can select a value, blend values, ignore values — but every result it can produce was already bracketed by its inputs.

This is exactly why attention cannot, on its own, compute a nonlinear function of a single token. Squaring a feature, thresholding it, computing an AND of two features — these produce outputs that are not weighted averages of the inputs, so they lie outside the hull, and attention cannot reach them. Stacking attention layers does not help: a weighted average of weighted averages is still a weighted average.

The MLP is the block that breaks out. It takes one token's vector, projects it up, applies a nonlinearity — a ReLU, a GELU — and projects back. The nonlinearity is the crucial ingredient: it is not a weighted average of the input, so its output can land anywhere, including outside the range the inputs spanned. The MLP is where a token's features are transformed into genuinely new features, per token, independent of the other positions.

So the two blocks are not redundant and not interchangeable. Attention is communication: it lets each token gather information from the others. The MLP is computation: it transforms what each token holds into something new. A Transformer alternates them because you need both — routing without transformation can only shuffle, and transformation without routing can only work on isolated tokens.

**Attention moves information between tokens and stays inside their hull; the MLP transforms a single token through a nonlinearity and can leave the hull — routing and computation, not two of the same thing.**

<svg role="img" aria-label="Three value vectors as points forming a triangle (their convex hull). An attention output is a point inside the triangle. An MLP output is a point outside the triangle." viewBox="0 0 440 160">
<rect x="0" y="0" width="440" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">the convex hull of the value vectors (2-D view)</text>
<polygon points="120,50 220,120 80,120" fill="var(--grid)" stroke="var(--line)"></polygon>
<circle cx="120" cy="50" r="4" fill="var(--ink)"></circle>
<circle cx="220" cy="120" r="4" fill="var(--ink)"></circle>
<circle cx="80" cy="120" r="4" fill="var(--ink)"></circle>
<text x="228" y="122" fill="var(--muted)" font-size="9">values</text>
<circle cx="140" cy="95" r="4" fill="var(--s2)"></circle>
<text x="148" y="98" fill="var(--s2)" font-size="9">attention (inside)</text>
<circle cx="330" cy="60" r="4" fill="var(--s1)"></circle>
<text x="300" y="50" fill="var(--s1)" font-size="9">MLP (outside)</text>
</svg>
^ Any attention output is a blend of the corner values, so it lands inside the triangle they span; the MLP's nonlinearity lets it place an output anywhere, including outside the hull.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/below-the-prompt/code/attnmlp-inter-01/attnmlp.py

The fixture uses three scalar values so the "hull" is just the range [1, 3].

```json filename=modules/below-the-prompt/code/attnmlp-inter-01/attnmlp.json:3-6 COMPLETE
  "values": [1.0, 3.0, 2.0],
  "score_sets": [[0, 0, 0], [2, 0, 0], [0, 3, 0], [0, 0, 1]],
  "mlp": {"w1": 1.0, "b1": -2.0, "w2": 4.0, "b2": 0.0},
  "mlp_inputs": [3.0, 1.0]
```

The attention weights are a softmax — non-negative, summing to one — and the output is their weighted average of the values.

```python filename=modules/below-the-prompt/code/attnmlp-inter-01/attnmlp.py:31-36 COMPLETE
def softmax(scores):
    """Attention weights: non-negative and summing to one, so any weighted sum is a convex combination."""
    hi = max(scores)
    exps = [math.exp(s - hi) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]
```

```python filename=modules/below-the-prompt/code/attnmlp-inter-01/attnmlp.py:39-42 COMPLETE
def attention_output(values, scores):
    """The attention output: the softmax-weighted average of the value vectors."""
    w = softmax(scores)
    return sum(wi * vi for wi, vi in zip(w, values))
```

```text filename=attnmlp.py --attend
ATTEND — attention output is a weighted average of values [1.0, 3.0, 2.0]
----------------------------------------------------------------
  weights ['0.333', '0.333', '0.333']  ->  output 2.000   in [1, 3]? True
  weights ['0.787', '0.107', '0.107']  ->  output 1.320   in [1, 3]? True
  weights ['0.045', '0.909', '0.045']  ->  output 2.864   in [1, 3]? True
  weights ['0.212', '0.212', '0.576']  ->  output 2.000   in [1, 3]? True
----------------------------------------------------------------
  every output lands inside the values' range -- attention cannot leave the hull
```

Uniform weights give 2.000, a weighting peaked on the largest value gives 2.864, and a weighting peaked on the smallest gives 1.320 — every one inside [1, 3]. There is no weighting that reaches 3.5 or 0.5, because a weighted average of 1, 3, and 2 cannot leave [1, 3].

<svg role="img" aria-label="A number line from 0 to 5. The three values 1, 3, 2 are marked, and the range [1,3] is shaded. Four attention outputs are plotted inside the shaded range. Two MLP outputs, 0 and 4, are plotted outside it." viewBox="0 0 440 130">
<rect x="0" y="0" width="440" height="130" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">values, attention outputs, and MLP outputs on a line</text>
<line x1="40" y1="70" x2="420" y2="70" stroke="var(--line)"></line>
<rect x="116" y="62" width="152" height="16" fill="var(--grid)"></rect>
<text x="150" y="100" fill="var(--muted)" font-size="9">value range [1, 3]</text>
<circle cx="116" cy="70" r="4" fill="var(--ink)"></circle>
<circle cx="268" cy="70" r="4" fill="var(--ink)"></circle>
<circle cx="192" cy="70" r="4" fill="var(--ink)"></circle>
<circle cx="140" cy="70" r="3" fill="var(--s2)"></circle>
<circle cx="257" cy="70" r="3" fill="var(--s2)"></circle>
<text x="120" y="52" fill="var(--s2)" font-size="9">attention: inside</text>
<circle cx="40" cy="70" r="4" fill="var(--s1)"></circle>
<text x="30" y="58" fill="var(--s1)" font-size="9">MLP 0</text>
<circle cx="344" cy="70" r="4" fill="var(--s1)"></circle>
<text x="334" y="58" fill="var(--s1)" font-size="9">MLP 4</text>
</svg>
^ Every attention output falls in the shaded value range; the MLP's outputs at 0 and 4 sit outside it, which no weighted average of the values could ever reach.

## Build

The MLP applies a nonlinearity per token, so its output is not a weighted average and can escape the range.

```python filename=modules/below-the-prompt/code/attnmlp-inter-01/attnmlp.py:45-48 COMPLETE
def mlp_output(x, m):
    """A per-token MLP: relu(w1*x + b1)*w2 + b2 -- a nonlinearity, so not a weighted average of inputs."""
    hidden = max(0.0, m["w1"] * x + m["b1"])
    return hidden * m["w2"] + m["b2"]
```

```text filename=attnmlp.py --mlp
MLP — a per-token nonlinearity: relu(1*x -2)*4 +0
----------------------------------------------------------------
  x = 3  ->  MLP 4.000   (above the value range [1, 3])
  x = 1  ->  MLP 0.000   (below the value range [1, 3])
----------------------------------------------------------------
  the nonlinearity lets the MLP produce values attention never could
```

Feed the MLP the value 3 and it returns 4 — above the range attention is confined to. Feed it 1 and it returns 0 — below. The ReLU is what makes this possible: it is not a weighted average, so its output is free of the hull.

<svg role="img" aria-label="Two blocks. Attention takes several tokens and outputs a blend that stays in the hull. The MLP takes one token and outputs a transformed value that can leave the hull." viewBox="0 0 440 140">
<rect x="0" y="0" width="440" height="140" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">two blocks, two jobs</text>
<text x="20" y="52" fill="var(--s2)" font-size="11">attention</text>
<text x="20" y="70" fill="var(--muted)" font-size="9">many tokens in &#8594; a blend out</text>
<text x="20" y="86" fill="var(--s2)" font-size="9">stays in the hull (communication)</text>
<text x="240" y="52" fill="var(--s1)" font-size="11">MLP</text>
<text x="240" y="70" fill="var(--muted)" font-size="9">one token in &#8594; transformed out</text>
<text x="240" y="86" fill="var(--s1)" font-size="9">can leave the hull (computation)</text>
<text x="20" y="120" fill="var(--ink)" font-size="10">a transformer alternates them because it needs both</text>
</svg>
^ Attention blends many tokens into a result inside their hull; the MLP reshapes one token into a result that can leave it — routing and computation side by side.

The self-test states the boundary: attention is confined, the MLP escapes on both sides, and the attention weights are a genuine distribution.

```python filename=modules/below-the-prompt/code/attnmlp-inter-01/attnmlp.py:87-92 COMPLETE
    attn_outs = [attention_output(values, s) for s in d["score_sets"]]
    attn_in_hull = all(lo <= o <= hi for o in attn_outs)
    print("  every attention output is within [%.0f, %.0f] = %s (%s)" % (lo, hi, attn_in_hull, ["%.3f" % o for o in attn_outs]))

    weights_valid = all(abs(sum(softmax(s)) - 1.0) < 1e-9 and all(w >= 0 for w in softmax(s)) for s in d["score_sets"])
    print("  attention weights are non-negative and sum to 1 (a convex combination) = %s" % weights_valid)
```

```text filename=attnmlp.py --check
SELF-TEST — every attention output lies within the values' range while the MLP produces outputs outside it, and the attention weights are a valid distribution
----------------------------------------------------------------------------------------------------------------
  every attention output is within [1, 3] = True (['2.000', '1.320', '2.864', '2.000'])
  attention weights are non-negative and sum to 1 (a convex combination) = True
  the MLP produces at least one output outside the value range = True (['4.000', '0.000'])
  the MLP escapes the hull on both sides (above and below) = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  attn_in_hull=True  weights_valid=True  mlp_escapes=True  mlp_both_sides=True
```

**weights_valid is the crux: because the weights are a softmax — non-negative, summing to one — the output is a convex combination, and everything about attention's confinement to the hull follows from that one fact.**

## Definition of done

You can explain why attention's output is a convex combination of the values, pointing to the softmax's two properties (non-negative, sums to one) as the source.

You can state the consequence — the output lies in the convex hull of the values, so in one dimension it is bracketed by the min and max — and why no choice of weights escapes it.

You can say why this means attention alone cannot compute a nonlinear function of a single token, and why stacking attention layers does not change that (an average of averages is an average).

You can describe the MLP's role and the specific ingredient (the nonlinearity) that lets it leave the hull, and frame the two blocks as communication versus computation.

## Boss fight

A colleague builds a "attention-only" model — Transformer blocks with the MLP sublayers removed — reasoning that attention is the powerful part and the MLPs are just extra parameters. It trains, but it plateaus at a surprisingly high loss and cannot fit tasks a normal small model handles easily.

First: explain, using the convex-hull argument, a concrete function of the inputs that this model provably cannot represent no matter how many attention layers it has or how it sets the weights. Why does adding more attention layers not rescue it?

Then: the colleague adds back a single linear (no nonlinearity) layer per block instead of the full MLP, expecting that to fix it. Explain why a linear layer does not escape the limitation the way a ReLU MLP does — what property must the added block have, precisely, and why is linearity not enough?

Finally: the residual stream complicates the clean story. With a residual connection, the block computes x + attention(x), not attention(x) alone. Explain how the residual changes the hull argument — is x + attention(x) still confined to a hull, and if so, of what — and why this does not save the attention-only model from needing a nonlinearity somewhere.

## External resources

The "mathematical framework for transformer circuits" (Anthropic) formalizes exactly this division — attention moves information between token positions while the MLP does per-token processing — and is the clearest treatment of attention as communication and the MLP as computation.

Any derivation of the universal approximation theorem shows why a nonlinearity is the ingredient that lets a network represent arbitrary functions; it is the same reason a linear layer cannot replace the ReLU MLP in the boss fight.
