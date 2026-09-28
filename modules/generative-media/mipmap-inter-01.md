---
id: mipmap-inter-01
title: Sample a minified texture from the right mip level — point-sampling level 0 aliases, too high a level blurs
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: A mipmap is a precomputed pyramid of a texture: level 0 is the texture, level 1 is level 0 with every adjacent pair averaged to half the length, level 2 halves again, each level a correctly prefiltered smaller copy, so a minified draw can read an already-averaged texel instead of averaging on the fly. When a surface is minified so each screen pixel covers m texels, the naive sampler reads level 0 at the pixel's location — one texel — and skips the other m−1, which aliases: the value it returns is a single point, not the average of the m texels the pixel covers, so a fine pattern folds into a false one and shimmers as the view moves. The fix is to sample the level whose texels are about one screen pixel wide; each step down the pyramid doubles the texels-per-texel, so that level is log2(m), and there each texel already holds the average of the m originals the pixel covers, making the sample the true footprint average. Picking too low a level is back to skipping texels (aliasing); too high a level averages more originals than the pixel covers, so neighboring pixels collapse to the same value (over-blur). On the fixture the texture is a 16-texel ramp and the minification is 4, so each screen pixel covers 4 texels, the correct level is 2, and the true footprint averages are 15, 55, 95, 135; level 0 point-sampling gives 0, 40, 80, 120 (aliased low), level 2 gives exactly the footprint averages, and level 3 gives 35, 35, 115, 115 (adjacent pixels collapsed). The rule: minification is not "sample the texture smaller," it is "sample a smaller, prefiltered texture," and which one is set by the minification factor.
eli5: Imagine a detailed mural, and you have to shrink it onto a tiny postcard by copying just a few dots. If you copy one dot here, one dot there, skipping most of the mural, the postcard looks nothing like the whole — you happened to land on a few random spots, and if you move a little the spots change and the picture flickers. The smarter way is to first make a few pre-shrunk versions of the mural — half size, quarter size, eighth size — each one already blended down properly, and then copy from the version that's closest to your postcard's size. Copy from the full mural and you get flicker; copy from a version that's shrunk too far and everything turns to mush; copy from the right-sized one and it looks just like the mural, small.
---

## Why this module

Minification — drawing a texture smaller than its resolution — is constant in graphics: any textured surface receding into the distance, any thumbnail of a detailed image, any zoomed-out map. And it has a sampling problem that is the mirror of magnification's: when many texels fall behind one pixel, which texel do you show?

The tempting answer, "sample the texture at the pixel's location," picks one texel and throws the rest away. That is not shrinking the image, it is decimating it, and it produces the shimmering, crawling artifacts that define cheap minification. Mipmapping is the standard fix, and using it correctly is entirely about picking the right level.

**Minification is not sampling the texture at fewer points; it is sampling a smaller, prefiltered copy — and the minification factor decides which copy.**

## Concepts

A mip pyramid is built once, ahead of time. Level 0 is the full texture. Each next level averages adjacent texels down to half the size — level 1 is half, level 2 a quarter, and so on until a single texel. Every level is a properly filtered smaller version of the texture, so the expensive averaging is done once and reused for every frame that needs it.

Now the sampling. Say the surface is minified so each screen pixel covers m texels. The pixel's honest value is the average of those m texels — its footprint average. Point-sampling level 0 returns just one of the m and ignores the rest, so it is not the footprint average; it is a single sample of a signal finer than the screen can represent, which is the definition of aliasing. As the view shifts and the pixel lands on a different one of the m texels, the value jumps, and the texture crawls.

The mip pyramid gives you the footprint average for free, if you pick the right level. Each level down doubles how many original texels one texel represents: level 1's texel is 2 originals, level 2's is 4, level k's is 2^k. So the level whose one texel spans exactly the m originals a pixel covers is level log2(m). Sample there and each screen pixel reads a texel that already holds its footprint average.

Both neighbors of that level are wrong in opposite ways. A level below log2(m) has texels smaller than the footprint, so you are again reading a fraction of the region and aliasing. A level above log2(m) has texels larger than the footprint, so a pixel's texel reaches into its neighbors' regions and pixels that should differ read the same value — over-blur, the mushy look of a texture minified with too coarse a level.

**The correct mip level is log2(minification): its texels match the pixel footprint, so the sample is the footprint average — below it aliases, above it over-blurs.**

<svg role="img" aria-label="One screen pixel covers four texels of level 0 (its footprint). Level 0's texels are too small (point-sample skips three). The correct level's one texel spans exactly the footprint. A higher level's texel spans eight, reaching past the footprint." viewBox="0 0 320 160">
<rect x="0" y="0" width="320" height="160" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">one screen pixel's footprint = 4 texels</text>
<rect x="40" y="34" width="128" height="16" fill="none" stroke="var(--s1)" stroke-dasharray="4 3"></rect>
<text x="172" y="46" fill="var(--s1)" font-size="9">footprint (4 texels)</text>
<rect x="40" y="58" width="32" height="14" fill="none" stroke="var(--line)"></rect>
<rect x="72" y="58" width="32" height="14" fill="none" stroke="var(--line)"></rect>
<rect x="104" y="58" width="32" height="14" fill="none" stroke="var(--line)"></rect>
<rect x="136" y="58" width="32" height="14" fill="none" stroke="var(--line)"></rect>
<text x="172" y="70" fill="var(--muted)" font-size="9">L0 texels: too small &#8594; alias</text>
<rect x="40" y="82" width="128" height="14" fill="var(--s2)"></rect>
<text x="172" y="94" fill="var(--s2)" font-size="9">correct level: one texel = footprint</text>
<rect x="40" y="106" width="256" height="14" fill="none" stroke="var(--muted)"></rect>
<text x="40" y="136" fill="var(--muted)" font-size="9">higher level: one texel spans 8 &#8594; over-blur</text>
</svg>
^ The correct level's single texel covers exactly the pixel's footprint; level 0's texels are too small so point-sampling skips most, and a higher level's texel reaches past the footprint into neighbors.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/generative-media/code/mipmap-inter-01/mipmap.py

The fixture is a 16-texel ramp, minified by 4.

```json filename=modules/generative-media/code/mipmap-inter-01/mipmap.json:3-4 COMPLETE
  "texture": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150],
  "minification": 4
```

The pyramid halves the texture by averaging pairs, and the footprint average is the truth each pixel should show.

```python filename=modules/generative-media/code/mipmap-inter-01/mipmap.py:33-39 COMPLETE
def build_pyramid(texture):
    """The mip pyramid: each level halves the previous by averaging adjacent pairs."""
    levels = [list(texture)]
    while len(levels[-1]) > 1:
        prev = levels[-1]
        levels.append([(prev[2 * i] + prev[2 * i + 1]) / 2 for i in range(len(prev) // 2)])
    return levels
```

```python filename=modules/generative-media/code/mipmap-inter-01/mipmap.py:42-45 COMPLETE
def footprint_averages(texture, m):
    """The truth: each screen pixel's value is the average of the m texels it covers."""
    screen = len(texture) // m
    return [sum(texture[i * m:(i + 1) * m]) / m for i in range(screen)]
```

The pyramid makes the correct level visible.

```text filename=mipmap.py --levels
LEVELS — mip pyramid of a 16-texel texture, minification 4
----------------------------------------------------------------
  level 0 (16 texels): ['0', '10', '20', '30', '40', '50', '60', '70', '80', '90', '100', '110', '120', '130', '140', '150']
  level 1 ( 8 texels): ['5', '25', '45', '65', '85', '105', '125', '145']
  level 2 ( 4 texels): ['15', '55', '95', '135']  <- correct level (log2 4)
  level 3 ( 2 texels): ['35', '115']
  level 4 ( 1 texels): ['75']
  footprint averages (truth): [15.0, 55.0, 95.0, 135.0]
```

Level 2 — log2(4) — has four texels holding 15, 55, 95, 135, exactly the footprint averages of the four screen pixels. The pyramid already computed the answer; the only job left is to read the right row.

<svg role="img" aria-label="A mip pyramid drawn as stacked rows: level 0 with 16 cells, level 1 with 8, level 2 with 4 highlighted as the correct level, level 3 with 2, level 4 with 1. Each level is half the width of the one below." viewBox="0 0 320 170">
<rect x="0" y="0" width="320" height="170" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">mip pyramid (each level half the last)</text>
<rect x="30" y="30" width="256" height="18" fill="none" stroke="var(--line)"></rect>
<text x="290" y="43" fill="var(--muted)" font-size="9">L0 (16)</text>
<rect x="30" y="54" width="128" height="18" fill="none" stroke="var(--line)"></rect>
<text x="290" y="67" fill="var(--muted)" font-size="9">L1 (8)</text>
<rect x="30" y="78" width="64" height="18" fill="var(--s2)"></rect>
<text x="290" y="91" fill="var(--s2)" font-size="9">L2 (4) &#8592;</text>
<rect x="30" y="102" width="32" height="18" fill="none" stroke="var(--line)"></rect>
<text x="290" y="115" fill="var(--muted)" font-size="9">L3 (2)</text>
<rect x="30" y="126" width="16" height="18" fill="none" stroke="var(--line)"></rect>
<text x="290" y="139" fill="var(--muted)" font-size="9">L4 (1)</text>
<text x="30" y="160" fill="var(--ink)" font-size="9">minification 4 &#8594; log2(4) = level 2</text>
</svg>
^ The pyramid is precomputed top to bottom; a minification of 4 selects level 2, whose four texels are the four pixels' footprint averages.

## Build

Sampling the same screen from three levels shows the two failures around the correct one.

```python filename=modules/generative-media/code/mipmap-inter-01/mipmap.py:53-55 COMPLETE
def correct_level(m):
    """The level whose texels span one screen pixel's footprint: log2(minification)."""
    return int(math.log2(m))
```

```text filename=mipmap.py --sample
SAMPLE — screen of 4 pixels, each covering 4 texels
----------------------------------------------------------------
  level 0 (point-sample):   ['0', '40', '80', '120']   <- aliased
  level 2 (correct):        ['15', '55', '95', '135']   <- footprint average
  level 3 (too high):       ['35', '35', '115', '115']   <- over-blurred
----------------------------------------------------------------
  level 0 skips texels; the correct level averages exactly the footprint; a higher level bleeds neighbors together
```

Level 0 reads texels 0, 4, 8, 12 — one of every four — giving 0, 40, 80, 120, each below its region's true average because it is a single low sample, not the mean. Level 2 gives 15, 55, 95, 135, the footprint averages. Level 3's texels each average eight originals, so the first two pixels both read 35 and the last two both read 115 — detail that should distinguish them is gone.

<svg role="img" aria-label="Four screen pixels plotted three ways. Level 0 samples 0, 40, 80, 120 (a low, stepped line). Level 2 samples 15, 55, 95, 135 (the correct rising line). Level 3 samples 35, 35, 115, 115 (a two-step line where pairs are equal)." viewBox="0 0 300 170">
<rect x="0" y="0" width="300" height="170" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">the four pixels sampled from each level</text>
<line x1="40" y1="150" x2="280" y2="150" stroke="var(--line)"></line>
<polyline points="60,150 130,122 200,95 270,68" fill="none" stroke="var(--s1)"></polyline>
<text x="200" y="64" fill="var(--s1)" font-size="9">level 0 (aliased)</text>
<polyline points="60,140 130,112 200,84 270,56" fill="none" stroke="var(--s2)"></polyline>
<text x="120" y="104" fill="var(--s2)" font-size="9">level 2 (correct)</text>
<polyline points="60,130 130,130 200,74 270,74" fill="none" stroke="var(--muted)"></polyline>
<text x="120" y="145" fill="var(--muted)" font-size="9">level 3 (over-blur, stepped)</text>
</svg>
^ Level 0 tracks low and steps like the aliased point samples; level 2 rises smoothly through the footprint averages; level 3 is flat across each pair, the over-blur that collapses neighbors.

The self-test names the level formula and both failure directions.

```python filename=modules/generative-media/code/mipmap-inter-01/mipmap.py:99-104 COMPLETE
    lvl0 = sample_level(pyr[0], screen)
    level0_aliases = lvl0 != truth
    print("  level 0 point-sampling misses the footprint average (aliases) = %s (%s vs truth %s)" % (level0_aliases, [("%g" % x) for x in lvl0], truth))

    correct_matches = sample_level(pyr[cl], screen) == truth
    print("  the correct level reproduces the footprint average = %s (%s)" % (correct_matches, [("%g" % x) for x in sample_level(pyr[cl], screen)]))
```

```text filename=mipmap.py --check
SELF-TEST — the correct level is log2(minification), level 0 aliases, the correct level matches the footprint average, and a higher level over-blurs
----------------------------------------------------------------------------------------------------------------
  correct level = log2(minification) = 2 (2^2 == 4) = True
  level 0 point-sampling misses the footprint average (aliases) = True (['0', '40', '80', '120'] vs truth [15.0, 55.0, 95.0, 135.0])
  the correct level reproduces the footprint average = True (['15', '55', '95', '135'])
  a higher level collapses pixels that should differ (over-blur) = True (['35', '35', '115', '115'])
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  level_is_log2=True  level0_aliases=True  correct_matches=True  toohigh_overblurs=True
```

**correct_matches is the payoff of precomputation: the footprint average is expensive to compute per frame, but the pyramid did it once, so the correct draw is a single texel lookup.**

## Definition of done

You can describe how a mip pyramid is built and why each level is a valid prefiltered smaller copy of the texture.

You can compute the correct level from the minification (log2 m) and explain why that level's texels match the pixel footprint.

You can name both failure directions and their look: too low a level aliases and shimmers, too high a level over-blurs and collapses detail.

You can say why mipmapping is a precomputation win: the footprint average is expensive per frame, and the pyramid turns it into one lookup, at the cost of a third more texture memory.

## Boss fight

A textured floor stretching to the horizon shimmers and crawls in the distance while looking fine up close, and turning on mipmapping fixes the shimmer but makes the far floor look soft and muddy. Someone proposes just picking a single fixed mip level for the whole floor.

First: explain why the near floor is fine and the far floor shimmers with no mipmapping — what is different about the minification factor across the floor, and why does a single point sample fail only where it does?

Then: a single fixed mip level for the whole floor is wrong for the same reason. Describe what level the near floor needs versus the far floor, and what artifact you get on each half if you pick one level for both — connect each to the too-low (alias) and too-high (blur) failures from this module.

Finally: real minification is rarely an exact power of two, so log2(m) lands between levels — say 2.4. Explain what trilinear filtering does in that case (which levels it reads and how it combines them), and why sampling only the nearest integer level produces a visible "mip band" seam where the level switches across the floor.

## External resources

The original mipmap paper (Williams, "Pyramidal Parametrics") introduces the pyramid and the level-of-detail selection this module builds, and its "d" parameter is exactly the log2(minification) computed here.

Any real-time rendering reference's texture-filtering chapter covers trilinear and anisotropic filtering as the refinements on top: trilinear blends the two bracketing levels to hide the mip band, and anisotropic filtering handles footprints that are longer in one direction than the other, which a single square mip level cannot.
