---
id: backmap-inter-01
title: Resample by walking the output pixels and pulling from the source — forward-mapping the source leaves holes
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Every geometric operation on an image — scaling, rotating, warping, lens correction — is a resample: you have pixels on one grid and need values on a different grid. There are two directions to implement it, and only one works. The forward direction is the one people reach for first because it matches how you picture the transform: take each source pixel, compute where it lands in the output, and write it there. The problem is a geometric mapping almost never sends source pixels onto output pixels one-to-one. Enlarging an image gives more output pixels than source pixels, so some output pixels are never any source's landing spot and are left as holes — black speckle. Shrinking maps several source pixels to the same output, so they collide and all but one are lost. The backward (inverse) direction fixes this by iterating over the output: for each output pixel, apply the inverse transform to find the source location it came from, and sample there. Because you visit every output pixel exactly once, every output pixel gets a value — no holes, no collisions, by construction — and a fractional source location just means you interpolate. On a fixture upscaling a 4-pixel row 2x to 8 pixels, forward mapping writes source i to output 2i, so only outputs 0,2,4,6 are written and 1,3,5,7 are holes, while backward mapping reads source j//2 for each output j and fills all 8: [10,10,20,20,30,30,40,40].
eli5: Imagine copying a short row of colored beads onto a longer string, stretched to twice the length. If you go bead by bead on the SHORT string and place each one where it "should" go on the long string, you only ever touch every other slot — half the long string stays empty, with gaps. Instead, go slot by slot along the LONG string and, for each empty slot, look back at the short string and ask "which bead belongs here?" and copy that color. Now every single slot on the long string gets filled, no gaps — because you walked the thing you were trying to fill, not the thing you were copying from.
---

## Why this module

The instinct when you rotate or resize an image is to push: for each pixel I have, figure out where it goes and put it there. It reads correctly and it is almost always wrong, because it fills the output only as a side effect of processing the input, and a geometric transform does not hand out one output pixel per input pixel. Enlarge and you have more slots than pixels to fill them; the leftovers stay empty. Shrink and several pixels fight for the same slot; most are thrown away. The output's completeness is left to chance, and for any transform that is not an exact integer copy, chance loses.

Enlarging an image gives more output pixels than source pixels, so some output pixels are never the landing spot of any source pixel — they are left as holes, showing through as black speckle. Shrinking maps several source pixels to the same output pixel, so they collide and all but the last are lost. Forward mapping's coverage of the output depends on the transform, and for anything but an exact integer copy it is wrong.

The backward (inverse) direction fixes this by iterating over the thing you actually need to fill: the output. For each output pixel, apply the inverse transform to find the source location it came from, and sample the source there. Because you visit every output pixel exactly once, every output pixel gets a value — no holes, no collisions, by construction. A fractional source location (the normal case for a rotation or non-integer scale) just means you interpolate between neighbors. This module runs both directions on a 2x upscale.

**Implement a geometric resample as a backward map — loop over the output pixels and, for each, invert the transform to find and sample its source location — because forward-mapping the source pixels leaves holes when you enlarge and collisions when you shrink, so output coverage is only guaranteed when the loop runs over the output.**

## Concepts

**Forward mapping walks the source and pushes** each pixel to where it lands, leaving every unlanded-on output as a hole (None).

```python filename=modules/generative-media/code/backmap-inter-01/backmap.py:49-55 COMPLETE
def forward_map(row, scale):
    """Walk the SOURCE: write each source pixel i to output i*scale. Outputs never written stay None (holes)."""
    out_len = len(row) * scale
    out = [None] * out_len
    for i, value in enumerate(row):
        out[i * scale] = value
    return out
```

**Backward mapping walks the output and pulls**, computing each output pixel's source location and sampling it — so every output is filled.

```python filename=modules/generative-media/code/backmap-inter-01/backmap.py:58-65 COMPLETE
def backward_map(row, scale):
    """Walk the OUTPUT: for each output j, read source j//scale (its inverse-mapped location) and sample it."""
    out_len = len(row) * scale
    out = []
    for j in range(out_len):
        src = min(j // scale, len(row) - 1)
        out.append(row[src])
    return out
```

<svg role="img" aria-label="Forward mapping: four source pixels push arrows to every other output slot, leaving four output slots empty; backward mapping: eight output slots each pull an arrow from a source pixel, leaving none empty" viewBox="0 0 300 130" width="300" height="130">
  <text x="6" y="12" fill="var(--muted)" font-size="8">forward pushes from 4 sources (gaps); backward pulls into 8 outputs (full)</text>
  <text x="6" y="30" fill="var(--muted)" font-size="7">forward</text>
  <g font-size="7">
    <rect x="40" y="24" width="16" height="12" fill="var(--s2)"/><rect x="96" y="24" width="16" height="12" fill="var(--s2)"/><rect x="152" y="24" width="16" height="12" fill="var(--s2)"/><rect x="208" y="24" width="16" height="12" fill="var(--s2)"/>
  </g>
  <g stroke="var(--s2)"><line x1="48" y1="38" x2="48" y2="52"/><line x1="104" y1="38" x2="104" y2="52"/><line x1="160" y1="38" x2="160" y2="52"/><line x1="216" y1="38" x2="216" y2="52"/></g>
  <g><rect x="40" y="52" width="16" height="12" fill="var(--s2)"/><rect x="68" y="52" width="16" height="12" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/><rect x="96" y="52" width="16" height="12" fill="var(--s2)"/><rect x="124" y="52" width="16" height="12" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/><rect x="152" y="52" width="16" height="12" fill="var(--s2)"/><rect x="180" y="52" width="16" height="12" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/><rect x="208" y="52" width="16" height="12" fill="var(--s2)"/><rect x="236" y="52" width="16" height="12" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/></g>
  <text x="256" y="62" fill="var(--muted)" font-size="6">= holes</text>
  <text x="6" y="86" fill="var(--muted)" font-size="7">backward</text>
  <g><rect x="40" y="80" width="16" height="12" fill="var(--s1)"/><rect x="68" y="80" width="16" height="12" fill="var(--s1)"/><rect x="96" y="80" width="16" height="12" fill="var(--s1)"/><rect x="124" y="80" width="16" height="12" fill="var(--s1)"/><rect x="152" y="80" width="16" height="12" fill="var(--s1)"/><rect x="180" y="80" width="16" height="12" fill="var(--s1)"/><rect x="208" y="80" width="16" height="12" fill="var(--s1)"/><rect x="236" y="80" width="16" height="12" fill="var(--s1)"/></g>
  <g stroke="var(--s1)"><line x1="48" y1="108" x2="48" y2="94"/><line x1="76" y1="108" x2="76" y2="94"/><line x1="104" y1="108" x2="104" y2="94"/><line x1="132" y1="108" x2="132" y2="94"/><line x1="160" y1="108" x2="160" y2="94"/><line x1="188" y1="108" x2="188" y2="94"/><line x1="216" y1="108" x2="216" y2="94"/><line x1="244" y1="108" x2="244" y2="94"/></g>
  <text x="6" y="124" fill="var(--muted)" font-size="6">every output pulls from a source → no empty slots</text>
</svg>
^ Forward mapping's four sources push into only four of the eight output slots, leaving four holes; backward mapping's eight outputs each pull a value from some source, so all eight are filled — the loop direction, source-driven versus output-driven, decides whether the output is fully covered.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/backmap-inter-01/backmap.py

The fixture is a 4-pixel row and a 2x upscale.

```json filename=modules/generative-media/code/backmap-inter-01/backmap.json:3-4 COMPLETE
  "row": [10, 20, 30, 40],
  "scale": 2
```

Run `--resample`.

```text filename=--resample
RESAMPLE — upscale [10, 20, 30, 40] by 2x to 8 pixels
--------------------------------------------------------------
  forward  (walk source) = [10, __, 20, __, 30, __, 40, __]
    ... holes at outputs [1, 3, 5, 7] -- never written
  backward (walk output) = [10, 10, 20, 20, 30, 30, 40, 40]
    ... no holes -- every output pixel sampled a source
--------------------------------------------------------------
  forward wrote 4 of 8 outputs; backward filled all 8.
```

Read the two outputs. Forward mapping produced [10, __, 20, __, 30, __, 40, __] — the four source values landed on outputs 0, 2, 4, and 6, and outputs 1, 3, 5, 7 were never written by anyone, so they are holes. There are only four source pixels, so forward mapping can write at most four outputs; the other four are structurally impossible to fill this way, because no source pixel maps to them. Backward mapping produced [10, 10, 20, 20, 30, 30, 40, 40] — every one of the eight outputs asked "where do I come from?", computed source j//2, and sampled it, so all eight are filled. This is a nearest-neighbor 2x upscale, exactly what you want. The forward version is not a worse upscale; it is not an upscale at all, it is a sparse scatter of the original pixels with gaps between them.

## Build

The holes are not a rounding artifact you can patch — they are baked into which loop you run.

```text filename=--map
MAP — the index mapping each direction
----------------------------------------------------------
  FORWARD: source i -> output i*2  (only these outputs written)
    source 0 (=10) -> output 0
    source 1 (=20) -> output 2
    source 2 (=30) -> output 4
    source 3 (=40) -> output 6
  BACKWARD: output j -> source j//2  (every output reads one source)
    output 0 <- source 0 (=10)
    output 1 <- source 0 (=10)
    output 2 <- source 1 (=20)
    output 3 <- source 1 (=20)
    output 4 <- source 2 (=30)
    output 5 <- source 2 (=30)
    output 6 <- source 3 (=40)
    output 7 <- source 3 (=40)
```

Look at the two mappings as functions. Forward is a function from source indices to output indices: it has four inputs (0,1,2,3) and therefore at most four outputs in its image (0,2,4,6), so half the output range is outside the image of the function and can never be reached. Backward is a function from output indices to source indices: it has eight inputs (0..7), one per output pixel, and each is defined, so every output is covered. This is the whole argument in one line — you get full coverage of a set exactly when your loop's index ranges over that set. That is why backward mapping is universal: for a rotation, output pixel (x,y) inverts to some fractional source location, and you interpolate; for a downscale, output pixel j inverts to a source location and you sample (or average a neighborhood) — in every case the output loop guarantees coverage, and the transform only has to be invertible, which the affine and projective transforms used for resizing and rotating always are.

<svg role="img" aria-label="Forward mapping on a downscale: eight source pixels push into four output slots, so pairs of sources collide on the same slot and one of each pair is overwritten and lost" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">forward on a shrink: sources collide, all but the last are lost</text>
  <g><rect x="30" y="24" width="14" height="12" fill="var(--s2)"/><rect x="58" y="24" width="14" height="12" fill="var(--s2)"/><rect x="86" y="24" width="14" height="12" fill="var(--s2)"/><rect x="114" y="24" width="14" height="12" fill="var(--s2)"/><rect x="142" y="24" width="14" height="12" fill="var(--s2)"/><rect x="170" y="24" width="14" height="12" fill="var(--s2)"/><rect x="198" y="24" width="14" height="12" fill="var(--s2)"/><rect x="226" y="24" width="14" height="12" fill="var(--s2)"/></g>
  <text x="244" y="34" fill="var(--muted)" font-size="6">8 sources</text>
  <g stroke="var(--s2)"><line x1="37" y1="38" x2="51" y2="64"/><line x1="65" y1="38" x2="51" y2="64"/><line x1="93" y1="38" x2="107" y2="64"/><line x1="121" y1="38" x2="107" y2="64"/><line x1="149" y1="38" x2="163" y2="64"/><line x1="177" y1="38" x2="163" y2="64"/><line x1="205" y1="38" x2="219" y2="64"/><line x1="233" y1="38" x2="219" y2="64"/></g>
  <g><rect x="44" y="64" width="14" height="12" fill="var(--s1)"/><rect x="100" y="64" width="14" height="12" fill="var(--s1)"/><rect x="156" y="64" width="14" height="12" fill="var(--s1)"/><rect x="212" y="64" width="14" height="12" fill="var(--s1)"/></g>
  <text x="234" y="74" fill="var(--muted)" font-size="6">4 outputs</text>
  <text x="30" y="98" fill="var(--muted)" font-size="6">two sources hit each output; the first is overwritten — half the data thrown away</text>
</svg>
^ Forward mapping on a downscale is the mirror failure of the upscale: eight sources push into four outputs, so two collide on each slot and the earlier one is overwritten and lost — backward mapping instead has each of the four outputs pull (and average) its source neighborhood, keeping the information.

```python filename=modules/generative-media/code/backmap-inter-01/backmap.py:116-124 COMPLETE
    forward_has_holes = len(holes(fwd)) > 0
    print("  forward output has holes = %s (at %s)" % (forward_has_holes, holes(fwd)))

    forward_wrote_only_source_count = sum(1 for v in fwd if v is not None) == len(row)
    print("  forward wrote only as many outputs as there are sources = %s (%d of %d)"
          % (forward_wrote_only_source_count, len(row), out_len))

    backward_no_holes = len(holes(bwd)) == 0
    print("  backward output has no holes = %s" % backward_no_holes)
```

## Definition of done

The self-test pins the forward holes, the source-count ceiling on what forward can write, and backward's full, correct coverage.

```python filename=modules/generative-media/code/backmap-inter-01/backmap.py:126-129 COMPLETE
    backward_fills_all = len(bwd) == out_len and all(v is not None for v in bwd)
    print("  backward filled all %d outputs = %s" % (out_len, backward_fills_all))

    backward_correct = bwd == [10, 10, 20, 20, 30, 30, 40, 40]
    print("  backward output is the expected 2x nearest upscale = %s (%s)" % (backward_correct, show(bwd)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — forward mapping leaves holes on the upscale; backward mapping fills every output pixel
--------------------------------------------------------------------------------------------------
  forward output has holes = True (at [1, 3, 5, 7])
  forward wrote only as many outputs as there are sources = True (4 of 8)
  backward output has no holes = True
  backward filled all 8 outputs = True
  backward output is the expected 2x nearest upscale = True ([10, 10, 20, 20, 30, 30, 40, 40])
```

<svg role="img" aria-label="Output coverage: forward fills 4 of 8 output pixels; backward fills 8 of 8" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">output coverage: forward 4/8, backward 8/8</text>
  <text x="10" y="38" fill="var(--muted)" font-size="7">forward</text>
  <rect x="70" y="26" width="200" height="16" fill="none" stroke="var(--line)"/>
  <rect x="70" y="26" width="100" height="16" fill="var(--s2)"/><text x="176" y="38" fill="var(--muted)" font-size="7">4 of 8 (holes)</text>
  <text x="10" y="66" fill="var(--muted)" font-size="7">backward</text>
  <rect x="70" y="54" width="200" height="16" fill="none" stroke="var(--line)"/>
  <rect x="70" y="54" width="200" height="16" fill="var(--s1)"/><text x="120" y="66" fill="var(--panel)" font-size="7">8 of 8 (full)</text>
  <text x="10" y="88" fill="var(--muted)" font-size="6">forward can cover at most as many outputs as it has sources</text>
</svg>
^ Forward mapping covers only 4 of the 8 output pixels — it can never exceed its source count — while backward mapping covers all 8, because its loop runs once per output pixel; coverage is a property of which set the loop ranges over.

**Done means the resampling direction is proven on real pixels: forward mapping writes source i to output 2i, covering only 4 of 8 outputs and leaving holes at [1,3,5,7], while backward mapping reads source j//2 for each of the 8 outputs and fills them all as [10,10,20,20,30,30,40,40] — so a geometric resample must loop over the output and invert the transform, because output coverage is guaranteed only when the loop ranges over the output.**

## Boss fight

Predict two things backward mapping still has to get right, because looping over the output guarantees coverage but not correctness of what each output samples.

The first trap is that backward mapping guarantees no holes but not a good-looking result — the sampling inside the loop is a separate decision, and getting it wrong reintroduces the very artifacts other modules exist to fix. Here the backward map used nearest-neighbor (source j//2), which fills every output but, on an upscale, produces blocky stair-steps, and on a *downscale* it is worse than blocky: sampling one source pixel per output while throwing away all the pixels in between is exactly the point-sampling that aliases fine detail into a false pattern. So backward mapping is the correct *structure*, but inside it you still owe the right sampler: interpolate (bilinear) when the source location is fractional and you are enlarging, and pre-filter or area-average when you are shrinking, because one output pixel then covers many source pixels and must summarize all of them, not pick one. The loop direction and the sampler are two independent choices, and backward mapping only settles the first.

The second trap is the inverse transform itself — backward mapping needs the transform to be invertible and needs you to actually apply the inverse, not the forward, and it needs care at the edges. If the geometric transform is not invertible (a fold, a degenerate projection that collapses area to a line) there is no single source location for some output pixels, and backward mapping has no defined answer there; the realistic version of this is a transform that is invertible in the interior but maps some output pixels *outside* the source image, where there is no pixel to sample — so you need an explicit out-of-bounds policy (clamp to the edge, wrap, mirror, or fill with a constant), which is the same border-policy decision a convolution faces, now at arbitrary fractional locations. And it is easy to write the forward transform where you needed its inverse: rotating the output by +θ to find sources requires sampling the input at −θ, and getting the sign wrong produces a clean, hole-free image that is rotated the wrong way. Backward mapping trades the hole problem for the obligation to have a correct inverse and a defined answer everywhere that inverse can point, including off the edge of the source.

**Backward mapping guarantees coverage, not quality: the sampler inside the loop is a separate obligation — interpolate on enlargement and area-average (pre-filter) on reduction, or you get blocky stair-steps and aliasing despite having no holes; and the loop needs a genuine inverse transform plus an out-of-bounds policy (clamp, wrap, mirror, or constant) for the output pixels whose source location falls outside the image, because an invertible-looking transform can still point off the edge or, with the sign flipped, fill every pixel correctly with the wrong picture.**

## External resources

Any computer-graphics or image-processing text on image warping and resampling (Wolberg's "Digital Image Warping", or the resampling chapters of Szeliski) — the forward-vs-backward mapping distinction, why backward mapping is standard, and how the reconstruction filter inside the loop is chosen.

Documentation for image resize/rotate/warp functions (Pillow's `Image.transform`, OpenCV's `warpAffine`/`remap`, GPU texture sampling) — all specify the mapping as backward (destination-to-source) and expose the interpolation and border modes this module's boss fight warns about.

The companion aliasing, bilinear-upsample, and border-policy modules in this topic — backward mapping is the structure into which those samplers and edge policies plug: interpolation for the fractional source location, pre-filtering against aliasing on reduction, and a border rule for source locations that fall off the image.
