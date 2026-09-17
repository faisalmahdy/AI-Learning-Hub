---
id: hysteresis-inter-01
title: Threshold edges with hysteresis — or one cutoff either breaks real edges or lets noise through
topic: generative-media
level: intermediate
status: ready
time: 17 min
summary: A single threshold on edge strength cannot win. Real edges vary in strength along their length — a contour fades where contrast dips, then recovers — while noise scatters pixels of middling strength. Set the threshold high enough to reject the noise and you also cut the real edge wherever it dipped, so a continuous contour comes back as broken fragments; set it low enough to bridge the dips and you admit every noise pixel. Hysteresis uses two thresholds: pixels at or above the high threshold are strong and kept unconditionally; pixels between low and high are weak and kept only if they connect, through a chain of kept pixels, to a strong one. A weak pixel is judged by its company, not its own strength — a weak stretch that continues an edge is linked in, an isolated weak pixel (noise) is dropped. On a fixture with a strong edge at index 1, a weak continuation at 2-3, and isolated noise at 5, a high-only threshold keeps just {1} (broken), a low-only keeps {1,2,3,5} (noise), and hysteresis keeps {1,2,3}.
eli5: Imagine deciding who to invite to a party by how loudly they RSVP'd. Only invite the loudest and you'll leave out quiet-but-real friends; invite everyone who whispered and you'll get random strangers too. The trick: always invite the loud ones, and invite a quiet person only if they came with a loud friend who vouches for them. A random quiet stranger with no loud friend stays out. Edge pixels work the same way — strong pixels are in, weak ones only if they're connected to a strong one.
---

## Why this module

Edge strength alone cannot separate real edges from noise, because a real edge is sometimes weak and noise is sometimes middling, so any single cutoff you pick is simultaneously too high for the faint parts of true edges and too low to exclude the noise.

After you have a gradient-magnitude map (and thinned it, so edges are one pixel wide), you still have to decide which pixels are edges. The obvious rule is a threshold: keep pixels above some strength. But real edges are not uniformly strong — a contour runs along a boundary whose contrast rises and falls, so parts of a genuine edge are faint. Noise, meanwhile, produces isolated pixels of moderate strength. Now the single threshold is trapped. Put it high enough to reject the noise pixels and it also rejects the faint parts of real edges, so a continuous contour comes back broken into disconnected fragments with gaps where it dipped. Put it low enough to keep those faint parts and it also keeps the noise. The threshold that rejects the noise is above the weakest real edge, and the threshold that keeps the weakest real edge is below the noise — and those two ranges overlap, so no single value is both.

**A single threshold must be above the noise and below the weakest part of a real edge at once, and those ranges overlap, so it either breaks real edges into fragments or admits noise.**

Hysteresis breaks the deadlock with two thresholds and a connectivity rule. Pixels at or above the high threshold are strong — confident edges, kept unconditionally. Pixels between the low and high thresholds are weak — kept only if they connect, through a chain of kept pixels, back to a strong pixel. The move is to judge a weak pixel by its company rather than its own strength: a weak stretch that continues a strong edge gets linked in and the edge is made whole, while an isolated weak pixel with no strong neighbor to vouch for it is dropped as noise. This module thresholds a magnitude profile three ways and shows hysteresis keep the connected edge while rejecting the isolated pixel.

## Concepts

**Strong pixels** are at or above the high threshold — confident edges, kept unconditionally.

**Weak pixels** are between the low and high thresholds — plausible edges, kept only if connected to a strong pixel.

**A single threshold** forces one cutoff to do both jobs, so it is either a high-only rule (rejects noise but breaks edges) or a low-only rule (keeps edges but admits noise).

```python filename=modules/generative-media/code/hysteresis-inter-01/hysteresis.py:50-52 COMPLETE
def single(mag, threshold):
    """Pixels kept by a single threshold."""
    return [i for i, m in enumerate(mag) if m >= threshold]
```

**Connectivity** is the deciding test for weak pixels: a weak pixel is kept if a chain of kept pixels links it to a strong one, so the same weak value is kept when it extends an edge and dropped when it stands alone.

**Judged by company, not strength.** Strong pixels are decided by their own value; weak pixels are decided by what they connect to, which is exactly what separates a faint edge continuation from an isolated noise speck of the same magnitude.

**Two thresholds plus connectivity beat any single cutoff: the high threshold anchors confident edges, and connectivity to those anchors rescues faint real edges while rejecting isolated weak noise.**

<svg role="img" aria-label="On a strength axis the weak-edge range and the noise range overlap, so one threshold cannot separate them, but two thresholds plus connectivity can" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">edge strength axis (weak &amp; noise overlap)</text>
  <line x1="20" y1="60" x2="285" y2="60" stroke="var(--grid)" stroke-width="1"/>
  <rect x="40" y="40" width="120" height="8" fill="var(--s1)" opacity="0.5"/><text x="44" y="36" fill="var(--s1)" font-size="7">weak real edges</text>
  <rect x="90" y="50" width="110" height="8" fill="var(--s2)" opacity="0.5"/><text x="150" y="72" fill="var(--s2)" font-size="7">noise</text>
  <line x1="200" y1="30" x2="200" y2="66" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 2"/><text x="190" y="28" fill="var(--muted)" font-size="7">high</text>
  <line x1="40" y1="30" x2="40" y2="66" stroke="var(--ink)" stroke-width="1" stroke-dasharray="3 2"/><text x="30" y="28" fill="var(--muted)" font-size="7">low</text>
  <text x="20" y="90" fill="var(--muted)" font-size="8">no single line splits the overlapping bars; connectivity decides the middle zone</text>
</svg>
^ The weak-real-edge and noise strength ranges overlap, so no single threshold cleanly separates them; hysteresis brackets the overlap with a low and a high line and uses connectivity to sort the pixels between them.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/hysteresis-inter-01/hysteresis.py

The fixture is a 1D magnitude profile: a strong edge, a weak continuation, and an isolated weak noise pixel.

```json filename=modules/generative-media/code/hysteresis-inter-01/hysteresis.json:1-5 COMPLETE
{
  "_meta": "A 1D slice of (already-thinned) edge magnitudes. A single threshold on edge strength forces a bad choice: set it HIGH and you keep only the strongest pixels, so a real edge whose strength dips in the middle breaks into disconnected fragments; set it LOW and you admit every faint pixel, including isolated noise. Hysteresis (double) thresholding uses TWO thresholds. Pixels at or above `high` are STRONG and always kept. Pixels between `low` and `high` are WEAK and kept only if they connect, through a chain of kept pixels, to a strong pixel -- so a weak stretch that continues a real edge is linked in, while an isolated weak pixel (noise) with no strong neighbor is dropped. magnitudes is the profile; index 5 (value 4) is an isolated weak noise pixel, and indices 2-3 are a weak continuation of the strong edge at index 1.",
  "magnitudes": [0, 8, 5, 6, 0, 4, 0],
  "high": 7,
  "low": 3
}
```

Hysteresis keeps the strong pixels and floods out through connected weak pixels to include only those linked to a strong one.

```python filename=modules/generative-media/code/hysteresis-inter-01/hysteresis.py:55-65 COMPLETE
def hysteresis(mag, low, high):
    """Keep strong pixels, plus weak pixels reachable from a strong one through a chain of >=low pixels."""
    eligible = set(single(mag, low))          # strong or weak
    kept, frontier = set(strong(mag, high)), list(strong(mag, high))
    while frontier:
        i = frontier.pop()
        for j in (i - 1, i + 1):
            if 0 <= j < len(mag) and j in eligible and j not in kept:
                kept.add(j)
                frontier.append(j)
    return sorted(kept)
```

Run `--thresh` to see all three rules.

```text filename=--thresh
THRESH — pixels kept by each rule (high 7, low 3)
------------------------------------------------------------
  magnitudes:   [0, 8, 5, 6, 0, 4, 0]
  high-only:    [1]   (real edge broken)
  low-only:     [1, 2, 3, 5]   (noise admitted)
  hysteresis:   [1, 2, 3]   (connected edge, noise dropped)
```

The real edge runs across indices 1, 2, 3 — strong at 1 (value 8), then dipping to a still-real 5 and 6 — while index 5 (value 4) is an isolated noise pixel. The high-only threshold at 7 keeps only index 1: the edge's faint continuation at 2 and 3 falls below the cutoff and the contour is broken. The low-only threshold at 3 keeps 1, 2, 3 — and also the noise at 5, which cleared the lower bar. Hysteresis keeps 1, 2, 3 and drops 5: it kept the weak pixels at 2 and 3 because they chain back to the strong pixel at 1, and dropped the weak pixel at 5 because a gap (the zero at index 4) cuts it off from any strong pixel. Same weak value range, two different fates, decided by connection.

<svg role="img" aria-label="High-only keeps index 1; low-only keeps 1,2,3,5 including noise; hysteresis keeps 1,2,3 the connected edge" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">edge pixels kept (indices 0–6)</text>
  <text x="8" y="34" fill="var(--s2)" font-size="8">high</text>
  <rect x="45" y="26" width="16" height="12" fill="none" stroke="var(--grid)"/><rect x="63" y="26" width="16" height="12" fill="var(--s2)"/><rect x="81" y="26" width="16" height="12" fill="none" stroke="var(--grid)"/><rect x="99" y="26" width="16" height="12" fill="none" stroke="var(--grid)"/><rect x="117" y="26" width="16" height="12" fill="none" stroke="var(--grid)"/><rect x="135" y="26" width="16" height="12" fill="none" stroke="var(--grid)"/><rect x="153" y="26" width="16" height="12" fill="none" stroke="var(--grid)"/>
  <text x="178" y="36" fill="var(--s2)" font-size="7">only 1 — broken</text>
  <text x="8" y="60" fill="var(--muted)" font-size="8">low</text>
  <rect x="45" y="52" width="16" height="12" fill="none" stroke="var(--grid)"/><rect x="63" y="52" width="16" height="12" fill="var(--grid)"/><rect x="81" y="52" width="16" height="12" fill="var(--grid)"/><rect x="99" y="52" width="16" height="12" fill="var(--grid)"/><rect x="117" y="52" width="16" height="12" fill="none" stroke="var(--grid)"/><rect x="135" y="52" width="16" height="12" fill="var(--s2)"/><rect x="153" y="52" width="16" height="12" fill="none" stroke="var(--grid)"/>
  <text x="178" y="62" fill="var(--muted)" font-size="7">+ noise at 5</text>
  <text x="8" y="86" fill="var(--s1)" font-size="8">hyst</text>
  <rect x="45" y="78" width="16" height="12" fill="none" stroke="var(--grid)"/><rect x="63" y="78" width="16" height="12" fill="var(--s1)"/><rect x="81" y="78" width="16" height="12" fill="var(--s1)"/><rect x="99" y="78" width="16" height="12" fill="var(--s1)"/><rect x="117" y="78" width="16" height="12" fill="none" stroke="var(--grid)"/><rect x="135" y="78" width="16" height="12" fill="none" stroke="var(--grid)"/><rect x="153" y="78" width="16" height="12" fill="none" stroke="var(--grid)"/>
  <text x="178" y="88" fill="var(--s1)" font-size="7">1,2,3 — whole edge</text>
  <text x="45" y="104" fill="var(--muted)" font-size="7">0  1  2  3  4  5  6</text>
  <text x="45" y="116" fill="var(--muted)" font-size="8">hysteresis fills the edge (1–3) but leaves the isolated noise at 5 empty</text>
</svg>
^ High-only lights one cell and breaks the edge; low-only lights the edge plus the noise at 5; hysteresis lights the connected edge 1–3 and leaves the isolated noise dark.

## Build

The deciding step is connectivity. Run `--trace`.

```text filename=--trace
TRACE — hysteresis grows from the strong pixel through connected weak ones
------------------------------------------------------------
  strong (>= 7): [1]   kept unconditionally
  weak   (3..7): [2, 3, 5]   kept only if connected
    weak pixel 2 (value 5): linked to a strong edge -> KEEP
    weak pixel 3 (value 6): linked to a strong edge -> KEEP
    weak pixel 5 (value 4): isolated (noise) -> drop
```

There is one strong pixel, index 1, kept outright. The three weak pixels — 2, 3, 5 — are all in the same strength range, so a threshold cannot tell them apart, but connectivity can. Pixel 2 is adjacent to the strong pixel 1, so it is kept and becomes part of the growing edge; pixel 3 is adjacent to the now-kept pixel 2, so it chains in too. Pixel 5 has value 4 — no weaker than the kept pixels — but its neighbors are both zero, so no chain of kept pixels reaches it, and it is dropped. This is why hysteresis rejects the noise: not because the noise pixel was weaker (it was not), but because it stood alone. The identical weak strength is an edge when it extends a strong one and noise when it does not, and only connectivity distinguishes the two.

<svg role="img" aria-label="From the strong pixel at index 1, hysteresis grows right into weak pixels 2 and 3, but a gap at index 4 blocks it from reaching the isolated weak pixel at 5" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">growth from the strong anchor, blocked by the gap</text>
  <rect x="30" y="30" width="30" height="18" fill="var(--s1)"/><text x="38" y="43" fill="var(--panel)" font-size="8">1 (8)</text>
  <text x="62" y="43" fill="var(--muted)" font-size="10">→</text>
  <rect x="78" y="30" width="30" height="18" fill="var(--s1)"/><text x="82" y="43" fill="var(--panel)" font-size="8">2 (5)</text>
  <text x="110" y="43" fill="var(--muted)" font-size="10">→</text>
  <rect x="126" y="30" width="30" height="18" fill="var(--s1)"/><text x="130" y="43" fill="var(--panel)" font-size="8">3 (6)</text>
  <rect x="158" y="30" width="30" height="18" fill="var(--grid)"/><text x="164" y="43" fill="var(--muted)" font-size="8">4 (0)</text>
  <text x="190" y="43" fill="var(--s2)" font-size="9">✕ gap</text>
  <rect x="222" y="30" width="30" height="18" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"/><text x="228" y="43" fill="var(--s2)" font-size="8">5 (4)</text>
  <text x="30" y="72" fill="var(--muted)" font-size="8">the chain reaches 2 and 3; the zero at 4 stops it before the isolated noise at 5</text>
</svg>
^ Hysteresis grows from the strong pixel 1 into the connected weak pixels 2 and 3, but the zero-magnitude gap at 4 blocks the chain, so the equally-weak noise at 5 is never reached and is dropped.

## Definition of done

The self-test pins it: high-only breaks the edge, low-only admits the noise, hysteresis keeps the connected edge and drops the isolated pixel, and it sits between the two single-threshold results.

```python filename=modules/generative-media/code/hysteresis-inter-01/hysteresis.py:103-116 COMPLETE
    high_only_breaks = len(hi) < len(hy)
    print("  high-only keeps fewer pixels than hysteresis (edge broken) = %s (%s vs %s)" % (high_only_breaks, hi, hy))

    low_only_admits_noise = noise in lo
    print("  low-only admits the isolated noise pixel = %s (index %d in %s)" % (low_only_admits_noise, noise, lo))

    hysteresis_keeps_connected = all(i in hy for i in (1, 2, 3))
    print("  hysteresis keeps the connected edge 1,2,3 = %s (%s)" % (hysteresis_keeps_connected, hy))

    hysteresis_rejects_isolated = noise not in hy
    print("  hysteresis drops the isolated noise pixel = %s (index %d not in %s)" % (hysteresis_rejects_isolated, noise, hy))

    hysteresis_between = set(hi) <= set(hy) <= set(lo)
    print("  hysteresis is between high-only and low-only = %s" % hysteresis_between)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — high-only breaks the edge; low-only admits noise; hysteresis keeps the connected edge, drops the isolated pixel
--------------------------------------------------------------------------------------------------------------------
  high-only keeps fewer pixels than hysteresis (edge broken) = True ([1] vs [1, 2, 3])
  low-only admits the isolated noise pixel = True (index 5 in [1, 2, 3, 5])
  hysteresis keeps the connected edge 1,2,3 = True ([1, 2, 3])
  hysteresis drops the isolated noise pixel = True (index 5 not in [1, 2, 3])
  hysteresis is between high-only and low-only = True
--------------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  high_only_breaks=True  low_only_admits_noise=True  hysteresis_keeps_connected=True  hysteresis_rejects_isolated=True  hysteresis_between=True
```

**Done means the two-threshold win is proven: high-only keeps just {1} (edge broken), low-only keeps {1,2,3,5} (noise at 5 admitted), and hysteresis keeps exactly {1,2,3} — the connected edge whole, the isolated noise gone — a result no single threshold produces.**

## Boss fight

Two thresholds beat one here. Predict how you set the high and low values, and the failure mode hysteresis still has. It is tempting to think two thresholds remove the tuning problem.

Hysteresis moves the tuning from one knob to two, and the two do different jobs. The high threshold controls how confident an edge must be to seed the process — set it too high and you have too few strong anchors, so real edges with no strong pixel anywhere are lost entirely; too low and noise pixels become strong anchors that then recruit weak noise around them. The low threshold controls how far the edge is allowed to grow from an anchor — set it too low and a weak chain can bridge from a real edge across noise into a spurious extension; too high and genuine faint continuations fall below it and the edge still breaks. The usual guidance is a low-to-high ratio around 1:2 or 1:3, but the right values are image-dependent, and hysteresis is genuinely better than one threshold precisely because it decouples "what counts as a confident edge" from "how far a confident edge may extend."

The failure mode it cannot fix is that connectivity is only as good as the thinning and the gaps. If the earlier stages left a true edge with a real gap — a genuine break in the gradient, not just a dip — no chain crosses it, and hysteresis leaves the edge in two pieces exactly as the gap dictates; it links weak pixels across dips, not across true zeros. And it can be fooled the other way: if noise happens to form a chain that touches a real strong edge, hysteresis will recruit the whole noisy chain, because a single connection to a strong pixel is enough. So hysteresis assumes that real edges are mostly-connected and noise is mostly-isolated, which is usually true and occasionally not. It is the final stage of the Canny detector for good reason — gradient, non-maximum suppression to thin, then hysteresis to threshold — and like every stage it improves the common case without being infallible; the connectivity heuristic is a strong prior about what edges look like, not a guarantee.

```python filename=modules/generative-media/code/hysteresis-inter-01/hysteresis.py:46-48 COMPLETE
def weak(mag, low, high):
    return [i for i, m in enumerate(mag) if low <= m < high]
```

**Threshold edges with two cutoffs, not one: keep strong pixels (above high) unconditionally and weak pixels (between low and high) only when connected through a chain to a strong one, so faint real-edge continuations are linked in and isolated weak noise is dropped — set high for confident anchors and low for how far they may grow (roughly a 1:2–1:3 ratio), remembering connectivity links across dips but not true gaps.**

## External resources

The Canny edge detector description in any computer-vision text — hysteresis is its final stage, following gradient computation and non-maximum suppression, with the double-threshold and connectivity rule spelled out.

The OpenCV `Canny` documentation and its two threshold parameters — the production implementation, the low-to-high ratio guidance, and how the thresholds interact with the gradient scale.

The companion "thin edges with non-maximum suppression" and "combine both gradient directions" modules — the thinning stage that precedes hysteresis and the gradient stage that precedes both, the three steps that turn raw pixel differences into clean, connected edges.
