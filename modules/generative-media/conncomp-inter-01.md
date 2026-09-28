---
id: conncomp-inter-01
title: Label connected blobs with union-find, and choose 4- vs 8-connectivity on purpose — or you miscount the regions
topic: generative-media
level: intermediate
status: ready
time: 16 min
summary: After binarizing an image the next question is usually how many separate objects the foreground holds — how many cells, glyphs, or detected regions — and that is connected-components labeling: assign every foreground pixel a label so two pixels share a label exactly when a foreground path connects them, then count distinct labels. Two decisions decide correctness. The first is what "connected" means: 4-connectivity joins pixels sharing an edge, 8-connectivity also joins pixels touching only at a corner, so two blobs that kiss at one diagonal are two objects under 4-connectivity and one under 8. The second is resolving label equivalences: a raster scan gives a U-shaped component two labels on its two arms before they meet, so a naive first pass over-counts — union-find merges the arms and counts the true number. On a fixture where a 2×2 block, a lone pixel, and another 2×2 block sit on a diagonal chain, 4-connectivity finds 3 components (the diagonals don't connect) while 8-connectivity chains them into 1.
eli5: You've highlighted some blobs of ink on a page and want to know how many separate blobs there are. Two blobs that only touch at a single corner — do they count as one blob or two? That's a choice you have to make on purpose, and it changes the answer. And when one wiggly blob gets discovered from two different directions as you scan, you have to notice that the two pieces are actually the same blob and join them. Union-find is the bookkeeping that keeps track of which pieces have turned out to be the same blob.
---

## Why this module

Counting the objects in a binarized image sounds like a simple tally, but two quiet choices — how pixels count as touching, and how you notice that two partial blobs are the same blob — each change the count, and getting either wrong gives a confidently wrong number.

Once an image is reduced to foreground and background, connected-components labeling answers "how many separate things are there, and which pixels belong to each." The definition is clean: two foreground pixels get the same label if and only if you can walk from one to the other stepping only on foreground pixels. But "step" hides the first choice. Under 4-connectivity a step goes to an edge-sharing neighbor — up, down, left, right. Under 8-connectivity a step may also go diagonally, to a corner-touching neighbor. Those are different graphs on the same pixels, so they produce different components: two regions that meet only at a single diagonal corner are one connected blob under 8-connectivity and two disconnected blobs under 4-connectivity. There is no universally correct choice — counting touching cells might want 4-connectivity so barely-touching cells stay separate, while tracing a thin diagonal line wants 8-connectivity so the line does not fragment — but you must choose deliberately, because the count depends on it.

**Connected-components labeling depends on a connectivity choice — 4-connectivity (edges) versus 8-connectivity (edges and corners) — so the same binary image yields different component counts, and the count is only meaningful once you have picked the connectivity your task requires.**

The second choice is mechanical but just as fatal to get wrong: resolving label equivalences. The efficient way to label is a single raster scan, giving each foreground pixel a label from an already-labeled neighbor — but a component shaped like a U, or any component a left-to-right top-to-bottom scan reaches from two directions, gets a different label on each branch before the branches meet lower down. A naive count of the labels handed out therefore over-counts, splitting one object into several. The fix is union-find: give each pixel a provisional label, union it with its foreground neighbors so that when two branches meet their labels are merged, and count the distinct roots at the end. Union-find turns "how many labels did I assign" into "how many distinct components actually exist." This module counts a diagonal-chain image both ways and shows the labels merge.

## Concepts

**Connectivity** is the neighbor set. 4-connectivity is the four edge neighbors; 8-connectivity adds the four diagonal corner neighbors. The choice defines which pixels are "connected."

**Union-find** tracks which provisional labels have turned out to be the same component. `find` returns a pixel's current component root, following the parent chain and compressing it.

```python filename=modules/generative-media/code/conncomp-inter-01/conncomp.py:45-50 COMPLETE
def find(parent, x):
    """Union-find root of x, with path compression."""
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
```

**Labeling** gives every foreground pixel its own provisional label, unions it with each foreground neighbor in the chosen connectivity, and reports each pixel's final root — so a component reached from two directions ends with one root.

```python filename=modules/generative-media/code/conncomp-inter-01/conncomp.py:58-68 COMPLETE
def label(image, neighbors):
    """Union-find labeling: union each foreground pixel with its foreground neighbors, return {pixel: component root}."""
    rows, cols = len(image), len(image[0])
    fg = [(r, c) for r in range(rows) for c in range(cols) if image[r][c]]
    parent = {p: p for p in fg}
    for r, c in fg:
        for dr, dc in neighbors:
            nb = (r + dr, c + dc)
            if 0 <= nb[0] < rows and 0 <= nb[1] < cols and image[nb[0]][nb[1]]:
                union(parent, (r, c), nb)
    return {p: find(parent, p) for p in fg}
```

<svg role="img" aria-label="A center pixel with its four edge neighbors marked for 4-connectivity, and the four diagonal corner neighbors additionally marked for 8-connectivity" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">4-connectivity vs 8-connectivity neighborhoods</text>
  <g transform="translate(40,24)">
  <rect x="20" y="20" width="20" height="20" fill="var(--ink)"/>
  <rect x="20" y="0" width="20" height="20" fill="var(--s1)"/><rect x="20" y="40" width="20" height="20" fill="var(--s1)"/><rect x="0" y="20" width="20" height="20" fill="var(--s1)"/><rect x="40" y="20" width="20" height="20" fill="var(--s1)"/>
  <rect x="0" y="0" width="20" height="20" fill="none" stroke="var(--line)"/><rect x="40" y="0" width="20" height="20" fill="none" stroke="var(--line)"/><rect x="0" y="40" width="20" height="20" fill="none" stroke="var(--line)"/><rect x="40" y="40" width="20" height="20" fill="none" stroke="var(--line)"/>
  </g>
  <text x="46" y="94" fill="var(--muted)" font-size="7">4-conn: edges (filled)</text>
  <g transform="translate(180,24)">
  <rect x="20" y="20" width="20" height="20" fill="var(--ink)"/>
  <rect x="20" y="0" width="20" height="20" fill="var(--s1)"/><rect x="20" y="40" width="20" height="20" fill="var(--s1)"/><rect x="0" y="20" width="20" height="20" fill="var(--s1)"/><rect x="40" y="20" width="20" height="20" fill="var(--s1)"/>
  <rect x="0" y="0" width="20" height="20" fill="var(--s2)"/><rect x="40" y="0" width="20" height="20" fill="var(--s2)"/><rect x="0" y="40" width="20" height="20" fill="var(--s2)"/><rect x="40" y="40" width="20" height="20" fill="var(--s2)"/>
  </g>
  <text x="186" y="94" fill="var(--muted)" font-size="7">8-conn: + corners</text>
</svg>
^ 4-connectivity counts only the four edge neighbors as connected; 8-connectivity adds the four diagonal corner neighbors, so corner-touching pixels join the same component.

**Pick 4- or 8-connectivity to match what you are counting, and resolve label equivalences with union-find, so the component count is the number of distinct objects — not the connectivity's default and not the number of provisional labels a raster scan handed out.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/conncomp-inter-01/conncomp.py

The fixture is a 5×5 binary image with a 2×2 block, a lone pixel, and another 2×2 block placed on a diagonal chain.

```json filename=modules/generative-media/code/conncomp-inter-01/conncomp.json:3-9 COMPLETE
  "image": [
    [1, 1, 0, 0, 0],
    [1, 1, 0, 0, 0],
    [0, 0, 1, 0, 0],
    [0, 0, 0, 1, 1],
    [0, 0, 0, 1, 1]
  ]
```

Run `--count` to count the components both ways.

```text filename=--count
COUNT — connected components by connectivity
----------------------------------------------
    1 1 0 0 0
    1 1 0 0 0
    0 0 1 0 0
    0 0 0 1 1
    0 0 0 1 1
----------------------------------------------
  4-connectivity (edges only):        3 components
  8-connectivity (edges + corners):   1 components
```

The same nine foreground pixels give 3 components under 4-connectivity and 1 under 8-connectivity. Trace it: the top-left 2×2 block, the lone pixel at (2, 2), and the bottom-right 2×2 block touch only at diagonal corners — (1, 1) meets (2, 2) at a corner, and (2, 2) meets (3, 3) at a corner. Under 4-connectivity a corner touch is not a connection, so the three pieces stay separate: 3 components. Under 8-connectivity the corner touches are connections, so (1,1)–(2,2)–(3,3) chain the three pieces into one continuous blob: 1 component. Neither answer is wrong; they answer different questions. If these were three cells that happen to abut at corners, 4-connectivity's "3 cells" is right; if this were one diagonal stroke, 8-connectivity's "1 stroke" is right. The image alone does not tell you — the connectivity you chose does, and choosing it silently by using whatever the library defaults to is how a counting task quietly reports the wrong number.

<svg role="img" aria-label="The 5x5 image showing a top-left block, a center pixel, and a bottom-right block touching only at diagonal corners along a chain" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the three pieces touch only at diagonal corners</text>
  <g transform="translate(90,18)">
  <rect x="0" y="0" width="16" height="16" fill="var(--s1)"/><rect x="16" y="0" width="16" height="16" fill="var(--s1)"/>
  <rect x="0" y="16" width="16" height="16" fill="var(--s1)"/><rect x="16" y="16" width="16" height="16" fill="var(--s1)"/>
  <rect x="32" y="32" width="16" height="16" fill="var(--s2)"/>
  <rect x="48" y="48" width="16" height="16" fill="var(--s1)"/><rect x="64" y="48" width="16" height="16" fill="var(--s1)"/>
  <rect x="48" y="64" width="16" height="16" fill="var(--s1)"/><rect x="64" y="64" width="16" height="16" fill="var(--s1)"/>
  <circle cx="32" cy="32" r="3" fill="var(--ink)"/><circle cx="48" cy="48" r="3" fill="var(--ink)"/>
  </g>
  <text x="185" y="40" fill="var(--muted)" font-size="7">corner touch (dots):</text>
  <text x="185" y="54" fill="var(--muted)" font-size="7">4-conn → 3 blobs</text>
  <text x="185" y="68" fill="var(--muted)" font-size="7">8-conn → 1 blob</text>
  <text x="6" y="100" fill="var(--muted)" font-size="8">the connectivity choice, not the pixels, decides whether this is three objects or one</text>
</svg>
^ The block, the lone pixel, and the second block meet only at diagonal corners (marked), so 4-connectivity sees three separate blobs and 8-connectivity sees one chained blob.

## Build

The label grids show union-find doing its job. Run `--labels`.

```text filename=--labels
LABELS — 4-connectivity
----------------------------------------------
    1 1 . . .
    1 1 . . .
    . . 2 . .
    . . . 3 3
    . . . 3 3
    -> 3 component(s)

LABELS — 8-connectivity
----------------------------------------------
    1 1 . . .
    1 1 . . .
    . . 1 . .
    . . . 1 1
    . . . 1 1
    -> 1 component(s)
```

Under 4-connectivity every pixel of the top-left block is labeled 1, the lone pixel 2, and the bottom-right block 3 — three distinct roots. Under 8-connectivity all nine pixels carry label 1: union-find merged them. That merge is the whole point. As the scan reached each block it started giving it a fresh provisional label, but when it found a diagonal foreground neighbor it called `union`, joining the two labels' sets, so by the end every pixel in the chain resolved to the same root. Without that equivalence resolution — if you had simply counted "I assigned three starting labels" — you would report 3 even under 8-connectivity, because the raster order discovers the three pieces before it discovers they connect. Union-find is what lets a single pass over the pixels still produce the correct global count: local unions accumulate into the true partition, and `find` reads it back at the end. The same machinery scales to a megapixel image with thousands of blobs and to the U-shapes and spirals where a component is genuinely reached from many directions.

<svg role="img" aria-label="Label grids: under 4-connectivity three components labeled 1, 2, 3; under 8-connectivity all pixels labeled 1" viewBox="0 0 300 96" width="300" height="96">
  <text x="20" y="14" fill="var(--muted)" font-size="8">4-connectivity: 3 roots</text>
  <g transform="translate(20,20)" font-size="8" fill="var(--panel)">
  <rect x="0" y="0" width="16" height="16" fill="var(--s1)"/><text x="5" y="12">1</text><rect x="16" y="0" width="16" height="16" fill="var(--s1)"/><text x="21" y="12">1</text>
  <rect x="0" y="16" width="16" height="16" fill="var(--s1)"/><text x="5" y="28">1</text><rect x="16" y="16" width="16" height="16" fill="var(--s1)"/><text x="21" y="28">1</text>
  <rect x="32" y="32" width="16" height="16" fill="var(--s2)"/><text x="37" y="44">2</text>
  <rect x="48" y="48" width="16" height="16" fill="var(--muted)"/><text x="53" y="60">3</text><rect x="64" y="48" width="16" height="16" fill="var(--muted)"/><text x="69" y="60">3</text>
  <rect x="48" y="64" width="16" height="16" fill="var(--muted)"/><text x="53" y="76">3</text><rect x="64" y="64" width="16" height="16" fill="var(--muted)"/><text x="69" y="76">3</text>
  </g>
  <text x="180" y="14" fill="var(--muted)" font-size="8">8-connectivity: 1 root</text>
  <g transform="translate(180,20)" font-size="8" fill="var(--panel)">
  <rect x="0" y="0" width="16" height="16" fill="var(--s1)"/><text x="5" y="12">1</text><rect x="16" y="0" width="16" height="16" fill="var(--s1)"/><text x="21" y="12">1</text>
  <rect x="0" y="16" width="16" height="16" fill="var(--s1)"/><text x="5" y="28">1</text><rect x="16" y="16" width="16" height="16" fill="var(--s1)"/><text x="21" y="28">1</text>
  <rect x="32" y="32" width="16" height="16" fill="var(--s1)"/><text x="37" y="44">1</text>
  <rect x="48" y="48" width="16" height="16" fill="var(--s1)"/><text x="53" y="60">1</text><rect x="64" y="48" width="16" height="16" fill="var(--s1)"/><text x="69" y="60">1</text>
  <rect x="48" y="64" width="16" height="16" fill="var(--s1)"/><text x="53" y="76">1</text><rect x="64" y="64" width="16" height="16" fill="var(--s1)"/><text x="69" y="76">1</text>
  </g>
</svg>
^ Under 4-connectivity the three pieces keep distinct labels 1, 2, 3; under 8-connectivity union-find merges the diagonal chain so all pixels share root 1 — the equivalence resolution a raw label count would miss.

## Definition of done

The self-test pins both facts: the diagonal chain is 3 under 4-connectivity and 1 under 8, 8-connectivity never counts more than 4, and every foreground pixel is labeled.

```python filename=modules/generative-media/code/conncomp-inter-01/conncomp.py:113-126 COMPLETE
    four_is_three = c4 == 3
    print("  under 4-connectivity the diagonal chain is 3 separate components = %s (%d)" % (four_is_three, c4))

    eight_is_one = c8 == 1
    print("  under 8-connectivity the corner-touches merge it into 1 = %s (%d)" % (eight_is_one, c8))

    eight_le_four = c8 <= c4
    print("  8-connectivity never counts more components than 4 = %s (%d <= %d)" % (eight_le_four, c8, c4))

    lab8 = label(img, NEIGHBORS_8)
    all_one_root = len(set(lab8.values())) == 1
    print("  under 8-connectivity every foreground pixel shares one root = %s" % all_one_root)

    fg_pixels = sum(sum(row) for row in img)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — 8-connectivity never counts more than 4; the diagonal chain is 3 under 4 and 1 under 8; labels equal roots
----------------------------------------------------------------------------------------------------------------------
  under 4-connectivity the diagonal chain is 3 separate components = True (3)
  under 8-connectivity the corner-touches merge it into 1 = True (1)
  8-connectivity never counts more components than 4 = True (1 <= 3)
  under 8-connectivity every foreground pixel shares one root = True
  every foreground pixel receives a label = True (9 pixels)
```

**Done means both decisions are proven to matter and to be handled: the diagonal-chain image is 3 components under 4-connectivity and 1 under 8-connectivity (8 never counting more than 4), union-find merges the chain so all nine pixels share one root under 8-connectivity, and every foreground pixel receives a label — so the count reflects the chosen connectivity and the true component partition, not the raster scan's provisional labels.**

## Boss fight

Predict the two ways the connectivity choice compounds with other decisions. It is tempting to pick 8-connectivity everywhere because it "connects more."

The first trap is that the foreground and background connectivity are coupled, and choosing the same for both creates a topological paradox. A closed diagonal loop of foreground pixels, one pixel thick, encloses a background hole. If you use 8-connectivity for the foreground so the loop is connected, and also 8-connectivity for the background, then the background inside the hole 8-connects to the background outside the loop *through the same diagonal gaps the foreground crossed* — so the loop both separates the inside from the outside (it is a closed curve) and does not (the backgrounds connect), which is contradictory. The standard fix is to use opposite connectivities for foreground and background: 8-connectivity for foreground with 4-connectivity for background, or vice versa, so that a curve that connects also separates, matching the Jordan curve theorem. So "just use 8-connectivity" is not a free choice — it constrains the background rule, and getting the pairing wrong makes hole-counting and region topology inconsistent.

```python filename=modules/generative-media/code/conncomp-inter-01/conncomp.py:53-55 COMPLETE
def union(parent, a, b):
    """Merge the sets containing a and b."""
    parent[find(parent, a)] = find(parent, b)
```

The second trap is that the count is only as trustworthy as the binarization and the noise before it. Connected components runs on the thresholded mask, so it inherits every flaw upstream: a single stray noise pixel is its own component, inflating the count, and a one-pixel bridge of noise between two real objects merges them into one — the labeling is exactly correct about a wrong mask. That is why component labeling is almost never the first step: it follows a threshold (chosen well, per the Otsu module) and usually a morphological cleanup (an opening to erase specks, a closing to seal thin gaps, per the morphology module) so that the components correspond to real objects rather than to noise. And even then, tiny components are typically filtered by an area threshold after labeling, because the honest number of objects is "components above a minimum size," not "every connected set of foreground pixels." The labeling is a precise operation on an imprecise input, so its output means what you want only when the pipeline before it has made the mask mean what you want.

**Connected-components labeling counts foreground blobs under a chosen connectivity — 4-connectivity (edges) or 8-connectivity (edges and corners), which change the count for corner-touching regions — resolved correctly with union-find so a component reached from several directions merges to one root; but the foreground and background connectivities must be opposite (8/4 or 4/8) to avoid a topological contradiction, and the count is only as good as the binarization and noise cleanup before it, so pair labeling with a deliberate threshold, morphological opening/closing, and an area filter rather than trusting a raw component count on a noisy mask.**

## External resources

Any image-processing reference on connected-components labeling — the classic two-pass (Hoshen–Kopelman / union-find) algorithm, 4- versus 8-connectivity, and the foreground/background connectivity pairing required by digital topology.

Writing on digital topology and the Jordan curve theorem in discrete images — why foreground and background must use complementary connectivities for curves to both connect and separate consistently.

The companion "pick the threshold from the histogram (Otsu)" and "open (erode then dilate) to remove specks" modules — labeling is the step after binarization and morphological cleanup, so the three form the standard segment-then-count pipeline, and the count is only meaningful once the earlier two have produced a clean mask.
