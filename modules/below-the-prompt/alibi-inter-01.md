---
id: alibi-inter-01
title: ALiBi puts position in a distance penalty on the attention scores — so it biases toward recent tokens and extrapolates to any length
topic: below-the-prompt
level: intermediate
status: ready
time: 15 min
summary: Position has to enter attention somewhere. Learned absolute position embeddings add a per-position vector to each token, which means a lookup table with one row per position the model was trained on — and no row for a position it never saw. ALiBi (Attention with Linear Biases) puts position in a different place: it subtracts slope·(query_pos − key_pos) from each attention score before the softmax, so a key one step back loses a little and a key many steps back loses a lot, and with the raw scores equal the softmax concentrates on the nearest keys. Position becomes a recency bias baked into the scores, with a single per-head slope and nothing learned per position. Two things follow. It favors recent tokens by construction — on the fixture, a query at position 3 with slope 0.5 gives biases [−1.5, −1.0, −0.5, 0] over keys 0..3 and attention [0.10, 0.17, 0.28, 0.46], the nearest key winning. And it extrapolates: the bias depends only on the query-key distance, so bias(q=3, k=1) and bias(q=103, k=101) are both −1.0, the bias at distance 103 is a finite −51.5, and the last-four-key bias pattern is identical at position 3 and position 103 — while a learned absolute embedding trained to length 4 has no vector at all for position 103. This is the mirror image of RoPE, whose rotations go out of distribution past the trained length and must be interpolated; ALiBi's linear distance bias is well-defined at every length by design. The rule: encoding position as a distance penalty on the scores gives a recency bias for free and a model that runs past its training length, because a function of distance is defined at any length.
eli5: Imagine everyone in a long line is shouting answers to you, and you want to trust the people nearest you more than the people far back. One way is to memorize a special badge for each spot in line — but then someone standing in a spot further back than any you memorized has no badge, and you're stuck. ALiBi's trick is simpler: just subtract points from each shouter based on how far back they are — one step back loses a little, ten steps back loses a lot. Now you naturally listen to the nearest people, and it works no matter how long the line gets, because "how far back are you" always has an answer, even for spots you've never seen before. You never needed a badge for each spot; you only needed the distance.
---

## Why this module

A transformer's attention is position-blind on its own — a dot product between a query and a key does not know which came first. Something has to inject order, and the choice of how shapes two things that matter a lot in practice: whether the model prefers nearby context, and whether it can run on inputs longer than it was trained on.

The textbook answer, learned absolute position embeddings, injects order by adding a learned vector to each token according to its index. It works within the trained length and fails at the boundary of it: the model has a vector for position 0 through the maximum it trained on, and literally nothing for the position after. Extend the context and the new positions have no representation.

ALiBi moves position out of the token vectors and into the scores, as a penalty that grows with the query-key distance. This module shows the two consequences that fall out of that one design choice: attention becomes recency-biased, favoring the nearest keys, and the bias — being a plain function of distance — is defined at any length, so the model extrapolates where a learned absolute table simply runs out of rows. It is the clean counterpart to RoPE, whose rotations must be interpolated to reach past training.

**Where you put position determines what you get for free: put it in a per-token embedding table and you are bounded by the table; put it in a distance penalty on the scores and you get recency bias and length extrapolation without a table at all.**

## Concepts

Attention scores a query against each key and softmaxes the scores into weights. To make those weights depend on order, you have to add position information, and there are two places to add it: to the token vectors before the dot product, or to the scores after it.

Adding it to the token vectors is the absolute-embedding approach: keep a table with one learned vector per position, add the vector for a token's index to the token, and let the dot product see it. The information is rich, but the table is finite — it has exactly as many rows as the longest sequence trained on, and a position past that has no row. The model cannot represent an index it never trained on, so it cannot attend correctly there.

ALiBi adds position to the scores instead. After the query-key dot product, it subtracts slope·(query_pos − key_pos) — the slope is a fixed per-head constant, and query_pos − key_pos is how many steps back the key is. A key at the current position (distance 0) loses nothing; a key one step back loses one slope; a key d steps back loses d slopes. With the raw scores equal, the softmax now leans toward the small-distance keys, because they kept more of their score. Position has become a recency bias, and no per-position vector was learned — just one slope per head.

Because the bias is slope times distance and distance is just query_pos − key_pos, two facts hold that the absolute table cannot match. It is translation-invariant: the bias for a key two steps back is the same whether the query is at position 3 or position 300, since only the gap of 2 enters. And it is total: the bias for any distance, including a distance larger than any sequence ever trained on, is a perfectly ordinary number — slope times that distance. A function of distance is defined at every distance, so ALiBi has a position signal at lengths it never saw, exactly where the absolute table has nothing.

<svg role="img" aria-label="Two ways to inject position. On the left, absolute embeddings add a per-position vector from a table with rows 0 to 3, and there is no row for position 103. On the right, ALiBi subtracts slope times distance from the scores, with no table, defined for any distance." viewBox="0 0 640 210">
<text x="160" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">absolute embeddings</text>
<rect x="90" y="42" width="140" height="22" fill="var(--panel)" stroke="var(--line)"/>
<text x="160" y="58" fill="var(--muted)" font-size="9" text-anchor="middle">pos 0 → vector</text>
<rect x="90" y="66" width="140" height="22" fill="var(--panel)" stroke="var(--line)"/>
<text x="160" y="82" fill="var(--muted)" font-size="9" text-anchor="middle">pos 1..3 → vectors</text>
<rect x="90" y="90" width="140" height="22" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" stroke-dasharray="4 3"/>
<text x="160" y="106" fill="var(--s2)" font-size="9" text-anchor="middle">pos 103 → no row</text>
<text x="160" y="132" fill="var(--muted)" font-size="9" text-anchor="middle">table bounded by trained length</text>
<text x="480" y="26" fill="var(--ink)" font-size="12" text-anchor="middle">ALiBi</text>
<rect x="380" y="60" width="200" height="40" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="480" y="80" fill="var(--ink)" font-size="10" text-anchor="middle">score − slope · distance</text>
<text x="480" y="96" fill="var(--muted)" font-size="9" text-anchor="middle">no table; a function of distance</text>
<text x="480" y="126" fill="var(--muted)" font-size="9" text-anchor="middle">defined for any distance, any length</text>
</svg>
^ Absolute embeddings store a vector per position and run out at the trained length; ALiBi computes a penalty from the distance, so it needs no table and is defined everywhere.

**Absolute embeddings put a finite, learned table between position and attention; ALiBi puts a single arithmetic rule, and a rule over distance has an answer at every length while a table has only the rows it was given.**

## Worked example

The fixture is a head with slope 0.5, trained to length 4, with a query inside that range and one far beyond it.

```json filename=modules/below-the-prompt/code/alibi-inter-01/alibi.json:3-6 COMPLETE
  "slope": 0.5,
  "train_len": 4,
  "query_pos": 3,
  "far_query_pos": 103
```

The bias is minus the slope times the query-key distance.

```python filename=modules/below-the-prompt/code/alibi-inter-01/alibi.py:31-33 COMPLETE
def alibi_bias(query_pos, key_pos, slope):
    """The penalty ALiBi adds to a score: -slope times the query-key distance (depends only on the gap)."""
    return -slope * (query_pos - key_pos)
```

The attention weights are the softmax over the biased scores, taking the raw scores equal so the bias is what shapes them.

```python filename=modules/below-the-prompt/code/alibi-inter-01/alibi.py:36-42 COMPLETE
def attention_weights(query_pos, slope):
    """Softmax over the biased scores (raw scores taken equal), for causal keys 0..query_pos."""
    biased = [alibi_bias(query_pos, k, slope) for k in range(query_pos + 1)]
    hi = max(biased)
    exps = [math.exp(b - hi) for b in biased]
    total = sum(exps)
    return [e / total for e in exps]
```

An absolute position embedding exists only for the positions seen in training.

```python filename=modules/below-the-prompt/code/alibi-inter-01/alibi.py:45-47 COMPLETE
def absolute_position_defined(pos, train_len):
    """A learned absolute position embedding exists only for positions seen in training (0..train_len-1)."""
    return pos < train_len
```

At a trained position, the bias grows with distance and the attention leans toward the nearest keys.

```text filename=alibi.py --attend
ATTEND — ALiBi biases and attention at query position 3 (raw scores equal)
----------------------------------------------------------------
  key 0: distance 3  bias -1.50  attention 0.102
  key 1: distance 2  bias -1.00  attention 0.167
  key 2: distance 1  bias -0.50  attention 0.276
  key 3: distance 0  bias -0.00  attention 0.455
----------------------------------------------------------------
  the nearest key gets the most weight, the farthest the least -- a recency bias
```

The nearest key takes 0.455 of the attention and the farthest 0.102 — a recency bias produced entirely by the distance penalty. The extrapolation view shows the bias is the same for equal distances anywhere and defined far past training.

```text filename=alibi.py --extrapolate
EXTRAPOLATE — the same bias at any position, and the far position's coverage
----------------------------------------------------------------
  bias(q=3, k=1) [dist 2] = -1.00
  bias(q=103, k=101) [dist 2] = -1.00   (same distance, same bias)
  bias at distance 103 (far past train_len 4) = -51.50   (a finite, ordinary number)
  learned absolute embedding exists at position 103? False
----------------------------------------------------------------
  ALiBi is defined at any distance; the absolute table has no row for the far position
```

The bias two steps back is −1.00 whether the query sits at position 3 or 103, the bias at distance 103 is a finite −51.5, and the absolute table has nothing at position 103. The figure shows the recency-weighted attention.

<svg role="img" aria-label="A bar chart of the attention weights at query position 3 over keys 0 to 3. The bars rise with proximity: key 0 (distance 3) is shortest at 0.10, key 3 (distance 0) is tallest at 0.46." viewBox="0 0 640 210">
<line x1="60" y1="175" x2="600" y2="175" stroke="var(--line)" stroke-width="1"/>
<rect x="100" y="134" width="90" height="41" fill="var(--s2)" opacity="0.6"/>
<text x="145" y="192" fill="var(--muted)" font-size="10" text-anchor="middle">key 0 (d3)</text>
<text x="145" y="126" fill="var(--muted)" font-size="10" text-anchor="middle">0.10</text>
<rect x="220" y="108" width="90" height="67" fill="var(--s2)" opacity="0.6"/>
<text x="265" y="192" fill="var(--muted)" font-size="10" text-anchor="middle">key 1 (d2)</text>
<text x="265" y="100" fill="var(--muted)" font-size="10" text-anchor="middle">0.17</text>
<rect x="340" y="65" width="90" height="110" fill="var(--s1)" opacity="0.7"/>
<text x="385" y="192" fill="var(--muted)" font-size="10" text-anchor="middle">key 2 (d1)</text>
<text x="385" y="57" fill="var(--muted)" font-size="10" text-anchor="middle">0.28</text>
<rect x="460" y="27" width="90" height="148" fill="var(--s1)" opacity="0.7"/>
<text x="505" y="192" fill="var(--muted)" font-size="10" text-anchor="middle">key 3 (d0)</text>
<text x="505" y="19" fill="var(--ink)" font-size="10" text-anchor="middle">0.46</text>
</svg>
^ With the raw scores equal, the distance penalty alone makes attention rise toward the nearest key — the recency bias ALiBi bakes in.

**The attention rising from 0.10 to 0.46 as the key gets closer is the slope at work: no dot product distinguished these keys, only the distance penalty did.**

## Build

The self-test pins both properties: ALiBi favors recent tokens, its bias is translation-invariant and finite at any distance, and a learned absolute embedding has no vector for the far position.

```python filename=modules/below-the-prompt/code/alibi-inter-01/alibi.py:81-88 COMPLETE
    favors_recent = weights[-1] > weights[0]
    print("  the nearest key gets more attention than the farthest = %s (%.3f > %.3f)" % (favors_recent, weights[-1], weights[0]))

    translation_invariant = alibi_bias(q, q - 2, slope) == alibi_bias(fq, fq - 2, slope)
    print("  the bias depends only on distance, not absolute position = %s (%.2f == %.2f)" % (translation_invariant, alibi_bias(q, q - 2, slope), alibi_bias(fq, fq - 2, slope)))

    defined_at_far = math.isfinite(alibi_bias(fq, 0, slope))
    print("  the bias is a finite number at a distance far past training = %s (%.2f at distance %d)" % (defined_at_far, alibi_bias(fq, 0, slope), fq))
```

The remaining flags confirm the absolute table is missing the far position and the local bias pattern is identical at both positions. All five pass.

```text filename=alibi.py --check
SELF-TEST — ALiBi favors recent tokens, its bias is translation-invariant and defined at any distance, and it needs no per-position table the way absolute embeddings do
----------------------------------------------------------------------------------------------------------------
  the nearest key gets more attention than the farthest = True (0.455 > 0.102)
  the bias depends only on distance, not absolute position = True (-1.00 == -1.00)
  the bias is a finite number at a distance far past training = True (-51.50 at distance 103)
  a learned absolute embedding has no vector for the far position = True (position 103, train_len 4)
  the last-4-key bias pattern is identical at both positions = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  favors_recent=True  translation_invariant=True  defined_at_far=True  absolute_missing_far=True  local_pattern_invariant=True
```

**"The last-4-key bias pattern is identical at both positions" is the extrapolation guarantee in one line: what the model learned about the nearest few keys at trained positions applies unchanged at positions it never saw.**

## Definition of done

You are done when you understand that ALiBi encodes position as a per-head, distance-proportional penalty added to the attention scores, giving a recency bias and length extrapolation without any learned per-position parameters — and when you can place it against the alternatives.

The design details that matter: each head gets its own slope, and the slopes are set geometrically across heads (small slopes for heads that should look far back, large slopes for heads that should stay local), so the model has both short- and long-range heads without learning any of it. The bias is added to the scores before the softmax and after the causal mask, so it composes with masking rather than replacing it. The payoff is train-short-test-long: a model trained at one length runs at a longer one with graceful degradation, because every head's bias is defined at the new distances. The honest caveats: the recency bias is a strong prior that helps language modeling but is not free — it makes attending to a very distant token harder, so tasks that need long-range retrieval can suffer, and ALiBi's clean extrapolation degrades slowly rather than never. And it is one of several positional schemes with different trade-offs — learned absolute (rich, bounded), sinusoidal absolute (fixed, extrapolates poorly), RoPE (relative via rotation, extrapolates only with interpolation as in the companion module), and ALiBi (relative via a score penalty, extrapolates by construction) — so the choice is a design decision about how much long-range reach you are willing to trade for length robustness.

<svg role="img" aria-label="A comparison of positional schemes on two axes: whether it is a learned table and whether it extrapolates past training. Learned absolute is a table and does not extrapolate; RoPE is relative and extrapolates only with interpolation; ALiBi is a distance penalty and extrapolates by construction." viewBox="0 0 640 180">
<rect x="40" y="40" width="180" height="46" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="6"/>
<text x="130" y="60" fill="var(--ink)" font-size="10" text-anchor="middle">absolute (table)</text>
<text x="130" y="76" fill="var(--muted)" font-size="9" text-anchor="middle">bounded by trained length</text>
<rect x="230" y="40" width="180" height="46" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="320" y="60" fill="var(--ink)" font-size="10" text-anchor="middle">RoPE (rotation)</text>
<text x="320" y="76" fill="var(--muted)" font-size="9" text-anchor="middle">extrapolates with interpolation</text>
<rect x="420" y="40" width="180" height="46" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="510" y="60" fill="var(--ink)" font-size="10" text-anchor="middle">ALiBi (score penalty)</text>
<text x="510" y="76" fill="var(--muted)" font-size="9" text-anchor="middle">extrapolates by construction</text>
<text x="320" y="120" fill="var(--muted)" font-size="10" text-anchor="middle">the further right, the less a longer input surprises the model</text>
</svg>
^ Positional schemes trade richness for length robustness; ALiBi sits at the robust end, encoding position as a distance penalty that is defined at any length.

**ALiBi's recency bias and extrapolation are two faces of one choice — position as a function of distance — so adopting it means accepting a built-in preference for nearby context in exchange for a model that does not fall apart when the input grows.**

## Boss fight

Your turn: change the slope and watch the recency bias sharpen or soften. Set the slope to 2.0 and rerun `--attend`: the biases become [−6, −4, −2, 0], the far keys are penalized so hard that the softmax nearly ignores them, and attention collapses almost entirely onto the last one or two positions — a very local head. Set the slope to 0.1 and the biases become [−0.3, −0.2, −0.1, 0], almost flat, so the attention is nearly uniform — a far-looking head. This is why ALiBi gives each head a different slope: the small-slope heads carry long-range information and the large-slope heads sharpen on recent tokens, and the model gets a spectrum of ranges without learning a single positional parameter.

Then probe the limit of the extrapolation claim, so you do not oversell it. The self-test shows the bias is defined at distance 103, which is true and is exactly what a learned absolute table lacks — but "defined" is not "as good as trained." At distances far beyond training, every key that far back is penalized by a large, roughly equal amount, so the model's ability to distinguish among distant tokens flattens: it can still attend locally with full fidelity, but its long-range resolution degrades as the input grows. ALiBi extrapolates gracefully, not perfectly, and the graceful part is precisely because the near-distance biases — the ones that matter most for language — are unchanged at any length, while the far-distance biases, which were always a coarse recency prior, simply extend. The honest claim is not "ALiBi makes context length free" but "ALiBi keeps a model coherent past its training length, at a cost concentrated in long-range precision," which is a very good trade for most uses and a poor one for a task that must retrieve a specific token from far away.

**ALiBi's extrapolation is real but graded: the near-distance biases that dominate language modeling are identical at every length, so local attention is untouched, while long-range resolution flattens as the input grows — extending past training coherently rather than freely.**

## External resources

Press, Smith, and Lewis's "Train Short, Test Long: Attention with Linear Biases Enables Input Length Extrapolation" (2022) is the original ALiBi paper — the slope schedule across heads, the extrapolation results, and the comparison to sinusoidal and rotary position encodings.

The companion RoPE and position-interpolation material (this topic's rope and posinterp modules) is the natural contrast: RoPE encodes relative position by rotation and needs interpolation to reach past training, where ALiBi's linear score bias is defined at any length by construction.

Surveys of positional encoding in transformers (for example the "positional encoding" sections of transformer architecture reviews) lay the schemes side by side — absolute learned, sinusoidal, relative, RoPE, ALiBi — and are the place to see the full set of trade-offs this module's definition-of-done sketches.
