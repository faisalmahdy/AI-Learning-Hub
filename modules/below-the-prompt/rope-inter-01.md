---
id: rope-inter-01
title: RoPE rotates q and k by position — so attention sees only relative distance
topic: below-the-prompt
level: intermediate
status: ready
time: 8-10h
summary: Rotary position embedding encodes a token's position by rotating its query or key vector by an angle proportional to that position, and because the dot product of two rotated vectors depends only on the difference of their angles, the attention score between a query at position m and a key at position n comes out depending only on the relative offset n minus m — pairs (0,2) and (3,5) both score 0.9402, while a different offset scores 0.7442. The instructive wrong way is to add a position vector to q and k, which leaks the absolute positions into cross terms so the same offset-2 pairs score 2.88 and 22.91, invariance gone. Rotation is the right operation because it preserves the vector's norm and turns a difference of positions into a difference of angles, which the dot product reads directly.
eli5: Imagine each word holds a clock hand, and its position in the sentence spins the hand by a fixed amount per step. When two words compare hands, what matters is the angle between them, and that angle only depends on how many steps apart they are — not where they are in the sentence. So "three words back" feels the same at the start and the middle. If instead you slid the hands outward by position, the comparison would depend on the absolute spot, and the nice sameness would break.
---

## Why this module

Attention is a dot product between a query and a key, and a bare dot product knows nothing about where its two tokens sit in the sequence. Position has to be injected somehow, and how you inject it is one of the most consequential design choices in a transformer, because it decides whether the model generalizes across positions or has to relearn every relationship at every offset. This module builds rotary position embedding, the scheme used in most modern models, from the geometry up, and shows the exact property that makes it work — attention depending only on relative distance — by measuring it and then breaking it with the natural wrong alternative.

The idea is to rotate rather than add. Give each token's query and key vector a rotation by an angle proportional to its position: the token at position m has its query turned by m times a base angle, the token at position n has its key turned by n times that angle. Now the attention score is the dot product of two rotated vectors, and there is a clean fact from geometry: the dot product of a vector rotated by angle a with a vector rotated by angle b depends only on b minus a. So the score between query-at-m and key-at-n depends only on n minus m — the relative offset — and not on the absolute positions at all. "Three tokens back" produces the identical score whether it happens at the start of the document or deep inside it, which is exactly the invariance you want a position scheme to have. The instructive failure is to encode position by adding a position vector to q and k, the older absolute style: the dot product then picks up cross terms in the absolute m and n, so the same offset scores differently at different positions and the invariance is lost.

You need the attention dot product from `attention-inter-01` and basic trigonometry. Everything runs offline against a vector fixture — one query, one key, one rotation plane — stdlib Python 3, `$0.00`. The instinct to unlearn is that a model needs to be told each token's absolute position. What attention actually needs is the relative distance between tokens, and rotation delivers exactly that while leaving absolute position invisible.

Here is the invariance, measured:

```
# modules/below-the-prompt/code/rope-inter-01/ — COMPLETE, run from that directory
$ python3 rope.py --scores

SCORES — RoPE attention score per (m,n) pair, with the offset n-m
------------------------------------------------------------------
  m    n    offset   rope score
  0    2    2        0.9402
  3    5    2        0.9402
  1    4    3        0.7442
  0    1    1        0.9060
```

run: 2026-08-26 · deterministic; vectors are a fixture · 4 pairs · `python3 rope.py --scores`

Query at position 0 with key at 2, and query at 3 with key at 5 — different absolute positions, same offset of 2 — score identically at 0.9402. A different offset, 3, gives a different score. This module is why those two offset-2 scores are exactly equal.

## Concepts

Named here so you can find them again; each is built below.

- **Attention score** — the dot product of a query and a key; the thing position must modulate.
- **Rotary position embedding (RoPE)** — encoding position by rotating q and k by position-dependent angles.
- **Rotation angle** — position times a base angle theta; how far a token's vector is turned.
- **Relative-position invariance** — the score depends only on the offset n minus m, not on m and n.
- **Norm preservation** — rotation only turns a vector, never scales it, so it does not distort magnitudes.
- **Additive encoding** — the older scheme of adding a position vector; it leaks absolute position into the score.

## Worked example

Source: rotary position embedding as introduced in RoFormer (Su et al.) and used in most current LLMs, reduced to a single 2D rotation plane; the query and key vectors here stand in for one head's projections so the relative-position property is exact and checkable. Real RoPE applies this per pair of dimensions across the head with different base frequencies.

Script and fixture: `modules/below-the-prompt/code/rope-inter-01/` — `rope.py`, and `vectors.json`, a query, a key, a base angle, and position pairs. Every command runs from there.

### Rotation, and the dot product it feeds

RoPE rests on a 2D rotation. Turning a vector by an angle mixes its two components with a cosine and a sine.

```
# rope.py:42-49 — COMPLETE (2D rotation and the dot product)
def rotate(v, angle):
    """Rotate a 2D vector by `angle` radians."""
    c, s = math.cos(angle), math.sin(angle)
    return [v[0] * c - v[1] * s, v[0] * s + v[1] * c]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]
```

The one fact to hold onto is why rotation, not any other transform. A rotation preserves the vector's length — it only changes direction — so it cannot inflate or shrink a query's influence based on position, only reorient it. And rotations compose by adding angles: rotating by a then by b is rotating by a plus b. Those two properties together are what make the dot product of two rotated vectors collapse to a function of the angle difference alone, which is the next step.

### The RoPE score depends only on the offset

Rotate the query by its position, the key by its position, then dot.

```
# rope.py:56-58 — COMPLETE (RoPE score: rotate each by position, then dot)
def rope_score(q, k, m, n, theta):
    """RoPE: rotate q by m*theta, k by n*theta, then dot. Depends only on (n-m)."""
    return dot(rotate(q, m * theta), rotate(k, n * theta))
```

Here is the algebra behind the equal scores. The dot product of q rotated by m·theta and k rotated by n·theta equals q dotted with k rotated by (n − m)·theta — the query's rotation can be "moved onto" the key as a relative rotation, because a rotation transposed is its inverse. So the score is a function of n − m and nothing else. The two offset-2 pairs in the run, (0,2) and (3,5), both reduce to q dotted with k rotated by 2·theta, giving the identical 0.9402. The absolute positions 0, 2, 3, 5 have vanished; only the gap survives.

<svg viewBox="0 0 700 200" role="img" aria-label="Two clock-like diagrams. Left: query hand at angle 0 (position 0) and key hand at angle 2-theta (position 2); the angle between them is 2-theta. Right: query hand at 3-theta (position 3) and key hand at 5-theta (position 5); the angle between them is again 2-theta. Both show the same angle between the hands despite different absolute angles.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the score reads the angle BETWEEN q and k — same offset, same angle</text>
    <circle cx="175" cy="110" r="60" fill="none" stroke="var(--grid)"></circle>
    <line x1="175" y1="110" x2="235" y2="110" stroke="var(--s1)" stroke-width="2"></line><text x="240" y="112" fill="var(--s1)" font-size="8">q @ 0</text>
    <line x1="175" y1="110" x2="205" y2="58" stroke="var(--s2)" stroke-width="2"></line><text x="205" y="52" fill="var(--s2)" font-size="8">k @ 2</text>
    <path d="M 205 110 A 30 30 0 0 0 190 84" fill="none" stroke="var(--acc)"></path><text x="215" y="92" fill="var(--acc-ink)" font-size="8">2θ</text>
    <text x="175" y="190" text-anchor="middle" fill="var(--muted)" font-size="8">positions 0 and 2</text>
    <circle cx="500" cy="110" r="60" fill="none" stroke="var(--grid)"></circle>
    <line x1="500" y1="110" x2="546" y2="72" stroke="var(--s1)" stroke-width="2"></line><text x="548" y="68" fill="var(--s1)" font-size="8">q @ 3</text>
    <line x1="500" y1="110" x2="512" y2="51" stroke="var(--s2)" stroke-width="2"></line><text x="500" y="46" fill="var(--s2)" font-size="8">k @ 5</text>
    <path d="M 546 72 A 30 30 0 0 0 528 57" fill="none" stroke="var(--acc)"></path><text x="548" y="60" fill="var(--acc-ink)" font-size="8">2θ</text>
    <text x="500" y="190" text-anchor="middle" fill="var(--muted)" font-size="8">positions 3 and 5</text>
  </g>
</svg>
^ Both panels have the query and key hands separated by the same angle, 2·theta, because both offsets are 2. The absolute orientations differ, but the dot product reads only the angle between the hands — so the scores are equal.

### Breaking it: additive position encoding

Now the natural wrong way. Encode position by adding a position vector, scaled by the index, to q and k.

```
# rope.py:61-66 — COMPLETE (the additive scheme: add position instead of rotating)
def additive_score(q, k, m, n, theta):
    """The wrong way: ADD a position vector (m or n scaled) to q, k, then dot."""
    pos = [math.cos(theta), math.sin(theta)]  # a fixed position direction, scaled by index
    qm = [q[0] + m * pos[0], q[1] + m * pos[1]]
    kn = [k[0] + n * pos[0], k[1] + n * pos[1]]
    return dot(qm, kn)
```

Adding position and then dotting expands into four terms: q·k, plus terms in m, in n, and in m·n. Those last three carry the absolute positions into the score, and they do not reduce to a function of n − m. Run it and the invariance is gone:

```
# $ python3 rope.py --additive
#   m    n    offset   additive score
#   0    2    2        2.8846
#   3    5    2        22.9112
#   1    4    3        9.6774
#   0    1    1        1.7673
```

run: 2026-08-26 · deterministic · `python3 rope.py --additive`

<svg viewBox="0 0 700 175" role="img" aria-label="Two grouped pairs of bars for the offset-2 pairs (0,2) and (3,5). Under RoPE both bars are the same height (0.94). Under additive, the (0,2) bar is short (2.88) and the (3,5) bar is very tall (22.91).">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">two pairs, both offset 2: does the scheme give them the same score?</text>
    <text x="150" y="40" fill="var(--ink)">RoPE</text>
    <rect x="150" y="120" width="40" height="30" fill="var(--s1)"></rect><text x="170" y="115" text-anchor="middle" fill="var(--s1)" font-size="8">0.94</text>
    <rect x="200" y="120" width="40" height="30" fill="var(--s1)"></rect><text x="220" y="115" text-anchor="middle" fill="var(--s1)" font-size="8">0.94</text>
    <text x="195" y="164" text-anchor="middle" fill="var(--muted)" font-size="8">identical -> invariant</text>
    <text x="430" y="40" fill="var(--ink)">additive</text>
    <rect x="430" y="140" width="40" height="10" fill="var(--s2)"></rect><text x="450" y="135" text-anchor="middle" fill="var(--s2)" font-size="8">2.88</text>
    <rect x="480" y="52" width="40" height="98" fill="var(--s2)"></rect><text x="500" y="47" text-anchor="middle" fill="var(--s2)" font-size="8">22.91</text>
    <text x="475" y="164" text-anchor="middle" fill="var(--muted)" font-size="8">8x apart -> absolute leaked</text>
    <line x1="140" y1="150" x2="560" y2="150" stroke="var(--grid)"></line>
  </g>
</svg>
^ RoPE gives the two offset-2 pairs the same score; additive gives them scores eight times apart. The only difference between the pairs is where they sit in the sequence, which RoPE hides and additive exposes.

The offset-2 pairs now score 2.88 and 22.91 — the same relative distance producing wildly different scores because the absolute positions leaked in through the m·n cross term. A model with this encoding would have to learn what "two tokens apart" means separately at every absolute position, because the score for that relationship changes as you move through the sequence. Rotation avoids this precisely because it does not add anything into the vector; it turns the vector, and turning composes as angle differences.

**RoPE encodes position by rotating q and k by position-proportional angles, so the attention score depends only on the relative offset n minus m — because a dot product of rotated vectors reads only their angle difference — while adding a position vector leaks absolute position through cross terms and destroys that invariance.**

### The self-test

The `--check` mode asserts all of it: RoPE gives equal scores for equal offsets, different scores for different offsets, additive leaks absolute position, and rotation preserves the norm.

```
# $ python3 rope.py --check
#   RoPE: same offset -> same score = True (0.9402 == 0.9402)
#   RoPE: different offset -> different score = True (0.7442 vs 0.9402)
#   additive: same offset -> DIFFERENT score = True (2.8846 vs 22.9112)
#   rotation preserves the vector norm = True (|q|=1.1180)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 rope.py --check`

The decisive comparison is four lines — the same two offset-2 pairs under each scheme:

```
# rope.py:99-111 — COMPLETE (RoPE holds the invariance; additive breaks it)
    s1 = rope_score(q, k, 0, 2, theta)
    s2 = rope_score(q, k, 3, 5, theta)
    rope_relative = abs(s1 - s2) < 1e-9

    a1 = additive_score(q, k, 0, 2, theta)
    a2 = additive_score(q, k, 3, 5, theta)
    additive_leaks = abs(a1 - a2) > 1e-6
```

`rope_relative` demands the two RoPE scores be equal; `additive_leaks` demands the two additive scores differ — the invariance proven present in one scheme and absent in the other.

The `rope_relative` line is the correctness anchor: two pairs sharing an offset must score identically to floating-point tolerance, and if the rotation were wrong — an added term, a sign error — that equality would break first. The `rope_discriminates` line guards against a trivial pass: the score must still change with offset, or "depends only on n − m" would be satisfied vacuously by a constant. And `norm_preserved` verifies the property that justifies using rotation at all — it reorients without rescaling.

### The running tally

| pair (m, n) | offset | RoPE score | additive score |
|---|---|---|---|
| (0, 2) | 2 | 0.9402 | 2.8846 |
| (3, 5) | 2 | 0.9402 | 22.9112 |
| (1, 4) | 3 | 0.7442 | 9.6774 |

<svg viewBox="0 0 700 160" role="img" aria-label="RoPE score plotted against offset. Offset 1 gives 0.906, offset 2 gives 0.940, offset 3 gives 0.744. The score varies smoothly with offset, and every point is determined by offset alone regardless of absolute position.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">RoPE score as a function of offset alone (absolute position irrelevant)</text>
    <line x1="60" y1="130" x2="650" y2="130" stroke="var(--grid)"></line>
    <line x1="60" y1="30" x2="60" y2="130" stroke="var(--grid)"></line>
    <polyline points="180,54 360,44 540,96" fill="none" stroke="var(--s1)" stroke-width="2.5"></polyline>
    <circle cx="180" cy="54" r="4" fill="var(--s1)"></circle><circle cx="360" cy="44" r="4" fill="var(--s1)"></circle><circle cx="540" cy="96" r="4" fill="var(--s1)"></circle>
    <text x="180" y="46" text-anchor="middle" fill="var(--muted)" font-size="8">0.906</text><text x="360" y="36" text-anchor="middle" fill="var(--muted)" font-size="8">0.940</text><text x="540" y="88" text-anchor="middle" fill="var(--muted)" font-size="8">0.744</text>
    <g fill="var(--muted)" text-anchor="middle"><text x="180" y="146">offset 1</text><text x="360" y="146">offset 2</text><text x="540" y="146">offset 3</text></g>
  </g>
</svg>
^ Each offset maps to one score, and that mapping is all RoPE exposes to attention — a clean function of relative distance. The additive scheme has no such curve, because its score depends on absolute position too.

Read the two offset-2 rows against each other. Under RoPE they are identical, 0.9402 and 0.9402 — the invariance made visible in two numbers. Under additive encoding they are 2.88 and 22.91, an eightfold difference for the same relative distance, purely because one pair sits later in the sequence. That single comparison is the whole case for rotary embeddings: the operation you choose to inject position decides whether relative distance is a stable, reusable signal or something the model must relearn at every offset.

### What we did not settle

This is one rotation plane; real RoPE tiles it across the head dimension with many frequencies. Each pair of dimensions gets its own base angle, geometrically spaced from fast to slow, so different frequency planes capture position at different scales — the fast ones distinguish nearby tokens, the slow ones carry long-range order, much like the wavelengths in sinusoidal encodings. That multi-frequency structure is what lets RoPE handle long contexts, and it is also what techniques like position interpolation and NTK-aware scaling adjust to extend a model's context window past its training length. RoPE also has a bounded-decay property — scores for distant tokens tend to attenuate — which the single plane here does not show. The core is exactly what you built: rotate by position, and the dot product reads relative distance.

## Build

The practice in one paragraph: inject position by rotating query and key vectors by an angle proportional to position, not by adding a position vector; verify the property that makes it worth doing — the attention score for a fixed pair of vectors depends only on the offset n − m, identical across absolute positions — and confirm rotation preserves norms so it reorients without rescaling; then tile the rotation across the head dimension with geometrically spaced frequencies for multi-scale position. Test the invariance directly, with two pairs sharing an offset at different absolute positions.

We opened on the invariance. The number that proves it is the pair of equal offset-2 scores:

```
# modules/below-the-prompt/code/rope-inter-01/ — COMPLETE, run from that directory
$ python3 rope.py --scores
  0    2    2        0.9402
  3    5    2        0.9402
```

Now build it yourself. Implement RoPE on a small head, take a fixed query and key, and score them at several (m, n) pairs — some sharing an offset, some not. Your number to beat is not any single score; it is **the spread among scores that share an offset, which under RoPE must be zero and under additive encoding will not be** — then implement the additive version and watch equal offsets diverge. Bring back the offset-grouped scores for both schemes. Good luck.

## Definition of done

- [ ] A 2D (or per-dimension-pair) rotation applied to query and key by position
- [ ] The RoPE attention score computed for several (m, n) pairs
- [ ] Confirmation that pairs sharing an offset score identically
- [ ] Confirmation that different offsets score differently (the invariance is not trivial)
- [ ] The additive-encoding version implemented, shown to leak absolute position
- [ ] Verification that rotation preserves the vector norm
- [ ] `python3 rope.py --check` printing SELF-TEST PASS: rope-relative, rope-discriminates, additive-leaks, norm-preserved
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. RoPE encodes position by rotating. Why does the resulting attention score depend only on n − m and not on m and n separately?
2. What two properties of rotation (about length and about composition) make the relative-position invariance work?
3. The additive scheme breaks the invariance. Which term in the expanded dot product is responsible, and what does it depend on?
4. Why does a model with a relative-position-invariant score generalize better across positions than one without?
5. Your own RoPE and additive versions were scored on offset-sharing pairs. What was the spread within each offset group for each scheme?

## External resources

- Su et al., *RoFormer: Enhanced Transformer with Rotary Position Embedding* (2021) — https://arxiv.org/abs/2104.09864 — my summary: the paper introducing RoPE, with the multi-frequency rotation and the proof that attention becomes a function of relative position; read it for the full head-dimension construction this module reduces to one plane.
- *Position interpolation* / NTK-aware scaling notes on extending RoPE context — my summary: how rescaling the rotation frequencies extends a model's usable context past its training length; read it for what the multi-frequency structure buys and how long-context models exploit it.
- This hub, *attention-inter-01* — modules/below-the-prompt/attention-inter-01.md — my summary: the scaled-dot-product attention this module adds position to; read it for the query-key dot product that RoPE rotates, and where position enters the attention computation.
