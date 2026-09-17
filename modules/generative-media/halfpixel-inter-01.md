---
id: halfpixel-inter-01
title: Map output pixels to source by their centers when resampling — the naive corner mapping shifts the image half a pixel and breaks its symmetry
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Resizing an image walks the output pixels and, for each, computes a source coordinate to sample from, then interpolates the source there — and the whole correctness of the resize lives in that one coordinate formula. It hinges on a fact easy to forget: a pixel is not a point, it is a little square, and the value it stores is the sample at its center. So output pixel j does not sit at position j; its center maps to (j + 0.5)·scale in source space, which on the source's own pixel-center grid is src = (j + 0.5)·scale − 0.5. The naive formula src = j·scale drops both half-pixel terms and treats pixels as points at their top-left corners, so it samples half a pixel off — and the error is not a harmless constant: it shifts the whole resampled image toward one side, asymmetrically, so the output no longer looks the same measured from the left as from the right. In deep learning this is the align_corners flag that silently misaligns feature maps between training and inference; in graphics it is the half-texel offset that seams tiled textures and shimmers upscaled sprites. The clean diagnostic is symmetry: correct center-based resampling is symmetric about the image center, so it commutes with flipping the image — resample then flip equals flip then resample — while the naive convention does not, having built a left/right bias into the resize. On a fixture downsampling a 4-sample signal to 2, the center convention samples the interval centers and returns a symmetric [15, 35] that passes the flip test, while the naive convention samples the left edges, returns a shifted [10, 30], and fails it.
eli5: When you shrink a photo, you have to decide, for each new pixel, which spot in the original it should copy from. The catch is that a pixel isn't a dot — it's a tiny tile, and its "real" spot is the middle of the tile, not its corner. If you measure from the corner instead of the middle, every new pixel grabs its color from slightly too far to one side, so the whole shrunk picture slides over by half a pixel — and it slides unevenly, more off on one edge than the other. An easy way to catch the mistake: a correct shrink should give the same result whether you flip the picture before or after shrinking. The corner method fails that test; the middle method passes it. Always measure from the middle of the pixel.
---

## Why this module

Every resize is a loop over output pixels asking "where in the source does this pixel come from?" The answer is a coordinate, and interpolation does the rest. Because the interpolation is usually the part people think about — bilinear, bicubic, Lanczos — the coordinate formula gets written quickly and rarely re-examined. That is where the half-pixel bug hides: not in the fancy filter, but in the one line that maps output index to source position.

The correct mapping comes from taking pixels seriously as areas. A pixel covers a unit cell and is sampled at its center. When you scale by a factor, output pixel j's center lands at (j + 0.5)·scale in continuous source space, and since the source's stored samples also sit at cell centers (index k means position k), you subtract the half to land on that grid: src = (j + 0.5)·scale − 0.5. The naive src = j·scale skips this. It aligns the corners of the images instead of their centers, and the consequence is a half-pixel translation of the entire output — small, constant-looking, and wrong in a way that compounds through pipelines and misaligns anything that assumes a centered resize.

The failure is easy to overlook because a shifted image still looks like the image. This module makes it unmissable by using symmetry: a correct resize cannot have a left/right preference, so flipping must commute with it. The naive one fails that test.

**A pixel's sample point is its center, so the source coordinate for output pixel j is (j + 0.5)·scale − 0.5 — the naive j·scale aligns corners instead, shifting the resampled image half a pixel and giving it a left/right asymmetry a correct resize never has.**

## Concepts

The fixture is a four-sample signal downsampled to two.

```json filename=modules/generative-media/code/halfpixel-inter-01/halfpixel.json:3-4 COMPLETE
  "src": [10, 20, 30, 40],
  "dst_n": 2
```

Three functions do the work. `src_coord` is the whole subject — the center convention versus the naive corner. `sample` interpolates the source linearly at a (possibly fractional) coordinate, clamping at the edges. `resample` maps each output pixel to a source coordinate and samples it.

```python filename=modules/generative-media/code/halfpixel-inter-01/halfpixel.py:32-52 COMPLETE
def src_coord(j, scale, mode):
    """Where output pixel j samples the source: center convention or naive corner."""
    if mode == "center":
        return (j + 0.5) * scale - 0.5
    return j * scale


def sample(src, x):
    """Linear interpolation at coordinate x, clamped at the edges."""
    if x <= 0:
        return float(src[0])
    if x >= len(src) - 1:
        return float(src[-1])
    i = int(x)
    f = x - i
    return src[i] * (1 - f) + src[i + 1] * f


def resample(src, dst_n, mode):
    scale = len(src) / dst_n
    return [sample(src, src_coord(j, scale, mode)) for j in range(dst_n)]
```

The only difference between a correct and a broken resize here is which branch of `src_coord` runs — the two half-pixel terms that the naive mode drops.

<svg role="img" aria-label="A source strip of 4 pixels and a target of 2; the center convention samples at 0.5 and 2.5 (interval centers), the naive convention samples at 0 and 2 (left corners), shifted left" viewBox="0 0 320 130">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">source pixels 0–3; two output pixels each cover 2 source cells</text>
  <g font-size="7">
  <rect x="20" y="24" width="60" height="18" fill="none" stroke="var(--line)"/><text x="46" y="37" fill="var(--muted)">0</text>
  <rect x="80" y="24" width="60" height="18" fill="none" stroke="var(--line)"/><text x="106" y="37" fill="var(--muted)">1</text>
  <rect x="140" y="24" width="60" height="18" fill="none" stroke="var(--line)"/><text x="166" y="37" fill="var(--muted)">2</text>
  <rect x="200" y="24" width="60" height="18" fill="none" stroke="var(--line)"/><text x="226" y="37" fill="var(--muted)">3</text>
  </g>
  <circle cx="50" cy="60" r="3.5" fill="var(--s1)"/><text x="34" y="76" font-size="7" fill="var(--s1)">center 0.5</text>
  <circle cx="170" cy="60" r="3.5" fill="var(--s1)"/><text x="154" y="76" font-size="7" fill="var(--s1)">center 2.5</text>
  <circle cx="20" cy="96" r="3.5" fill="var(--s2)"/><text x="8" y="112" font-size="7" fill="var(--s2)">naive 0</text>
  <circle cx="140" cy="96" r="3.5" fill="var(--s2)"/><text x="128" y="112" font-size="7" fill="var(--s2)">naive 2</text>
  <text x="20" y="126" font-size="7.5" fill="var(--ink)">center dots sit in the middle of each output pixel's span; naive dots hug the left edge</text>
</svg>
^ Each output pixel spans two source cells. The center convention samples the middle of each span (0.5 and 2.5); the naive convention samples the left corner (0 and 2), half a pixel to the left. The naive dots are not centered in their spans, and the whole pattern is shifted toward the left edge.

**The correct source coordinate centers the sample in the output pixel's span; the naive one puts it at the left corner — half a pixel off, and off in the same direction for every pixel.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the coordinate step of an image resampler, reduced to a 1-D signal so every sample position is checkable by hand.

Run `--coords` to see where each output pixel samples.

```text filename=halfpixel.py --coords
  out pixel   center: (j+0.5)*s-0.5   naive: j*s
  0           0.50                   0.00
  1           2.50                   2.00
```

With scale 2, the center convention samples 0.5 and 2.5 — the midpoints of the two halves of the signal, and symmetric about the source center at 1.5 (0.5 is one unit left, 2.5 is one unit right). The naive convention samples 0.0 and 2.0 — both a half-pixel to the left, and not symmetric about 1.5 (0.0 is 1.5 left, 2.0 is only 0.5 right). The naive sampler leans left.

Now `--resample` interpolates each convention and compares the flipped resample against the resample of the flipped input.

```python filename=modules/generative-media/code/halfpixel-inter-01/halfpixel.py:73-76 COMPLETE
    for mode in ("center", "naive"):
        r = resample(src, dst_n, mode)
        rf = resample(list(reversed(src)), dst_n, mode)
        sym = rf == list(reversed(r))
```

The two rows tell opposite stories.

```text filename=halfpixel.py --resample
  center   resample=[15.0, 35.0]  flip(resample)=[35.0, 15.0]  flip-symmetric=True
  naive    resample=[10.0, 30.0]  flip(resample)=[30.0, 10.0]  flip-symmetric=False
```

The center convention returns [15, 35]: the average of the first pair (10, 20) and the second pair (30, 40), exactly what a 2× downsample should give. Flip the source to [40, 30, 20, 10], resample, and you get [35, 15] — precisely the reverse of [15, 35]. Resampling commuted with flipping, because the operation has no left/right bias. The naive convention returns [10, 30]: it sampled the left edge of each half, so it just copied source pixels 0 and 2 and threw away 1 and 3. Flip the source and naive returns [40, 20], whose reverse is [20, 40] — but the naive resample of the original was [10, 30]. They disagree. The naive resize is not the same operation left-to-right as right-to-left.

<svg role="img" aria-label="Flip-symmetry test: center resampling of the signal and of its flip are mirror images (symmetric), naive resampling of the signal and its flip are not mirror images (asymmetric)" viewBox="0 0 320 130">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">does resample commute with flip? (it must, for a correct resize)</text>
  <text x="10" y="40" font-size="8" fill="var(--s1)">center</text>
  <text x="60" y="40" font-size="7.5" fill="var(--ink)">resample [15,35] · flip→[35,15] = resample(flip) [35,15] ✓</text>
  <text x="10" y="70" font-size="8" fill="var(--s2)">naive</text>
  <text x="60" y="70" font-size="7.5" fill="var(--ink)">resample [10,30] · flip→[30,10] ≠ resample(flip) [20,40] ✗</text>
  <text x="10" y="104" font-size="7.5" fill="var(--muted)">the mismatch is the fingerprint of the half-pixel shift — a built-in left/right bias</text>
</svg>
^ For the center convention, flipping the input mirrors the output — the resize is symmetric. For the naive convention, the flipped-input result is not the mirror of the original result, exposing the left/right bias the half-pixel shift introduced.

**The center convention returns the true pair-averages [15, 35] and passes the flip test; the naive convention returns the shifted [10, 30] — copies of the left edges — and fails it, proving the resize has a direction it should not have.**

## Build

The self-test asserts the coordinate divergence and its shape: the two conventions sample different coordinates, the naive one lands on the very edge while the center one lands inward, and the center coordinates are symmetric about the source middle.

```python filename=modules/generative-media/code/halfpixel-inter-01/halfpixel.py:90-99 COMPLETE
    coords_differ = center_coords != naive_coords
    print("  the two conventions sample different source coordinates = %s (%s vs %s)" % (coords_differ, center_coords, naive_coords))

    naive_samples_left_edge = naive_coords[0] == 0.0 and center_coords[0] > 0.0
    print("  the naive convention samples the very edge; the center convention samples inward = %s (%.2f vs %.2f)"
          % (naive_samples_left_edge, naive_coords[0], center_coords[0]))

    # symmetry of the source-coordinate pattern about the middle of the source
    mid = (len(src) - 1) / 2.0
    center_symmetric = all(abs((center_coords[j] - mid) + (center_coords[dst_n - 1 - j] - mid)) < 1e-9 for j in range(dst_n))
    print("  the center coords are symmetric about the source middle = %s" % center_symmetric)
```

Then the decisive test: center resampling commutes with flipping, and naive resampling does not.

```python filename=modules/generative-media/code/halfpixel-inter-01/halfpixel.py:102-109 COMPLETE
    r = resample(src, dst_n, "center")
    rf = resample(list(reversed(src)), dst_n, "center")
    center_flip_ok = rf == list(reversed(r))
    print("  center resampling commutes with flipping = %s (%s)" % (center_flip_ok, r))

    rn = resample(src, dst_n, "naive")
    rnf = resample(list(reversed(src)), dst_n, "naive")
    naive_flip_broken = rnf != list(reversed(rn))
```

Running the check confirms every clause.

```text filename=halfpixel.py --check
  the two conventions sample different source coordinates = True ([0.5, 2.5] vs [0.0, 2.0])
  the naive convention samples the very edge; the center convention samples inward = True (0.00 vs 0.50)
  the center coords are symmetric about the source middle = True
  center resampling commutes with flipping = True ([15.0, 35.0])
  naive resampling does NOT commute with flipping = True
```

**The check ties the half-pixel shift to a concrete asymmetry — the naive convention samples the edge and fails the flip test — while the center convention samples symmetric interior points and commutes with flipping.**

## Definition of done

Done means the naive corner mapping is shown to shift the samples and break flip symmetry, and the center mapping to stay centered and commute with flipping. The flip test is the load-bearing clause: a shift alone might be dismissed as a convention choice, but a resize that behaves differently left-to-right than right-to-left is unambiguously wrong, and the flip test catches exactly that with no reference image needed.

Two clarifications place this in real systems. First, this is the substance of the align_corners flag in deep-learning resize ops (PyTorch's `interpolate`, TensorFlow's historical resize bug). `align_corners=False` with the half-pixel-center convention is the geometrically correct default that matches how OpenCV, PIL, and GPU texture sampling resample; `align_corners=True` maps the corner samples of input and output onto each other, which changes the effective scale factor and is a frequent source of train/inference mismatch when a model trained with one convention is served with the other. The rule is to fix one convention across the whole pipeline and prefer the half-pixel-center one. Second, the fix generalizes to 2-D unchanged — apply src = (j + 0.5)·scale − 0.5 independently to x and y — and to upsampling as well as downsampling; the half-pixel offset is not a downsampling detail but the definition of where a pixel lives. Edge handling (clamp, reflect, wrap) is a separate choice layered on top and does not change the center convention.

<svg role="img" aria-label="align_corners comparison: half-pixel-center (align_corners false) matches OpenCV/PIL/GPU sampling and is correct; align_corners true remaps corners and changes the scale, a common train-inference mismatch" viewBox="0 0 320 120">
  <rect x="16" y="24" width="140" height="40" fill="none" stroke="var(--s1)"/>
  <text x="24" y="40" font-size="7.5" fill="var(--s1)">half-pixel center</text>
  <text x="24" y="52" font-size="7" fill="var(--ink)">(j+0.5)·s−0.5 · matches</text>
  <text x="24" y="61" font-size="7" fill="var(--ink)">OpenCV / PIL / GPU</text>
  <rect x="168" y="24" width="140" height="40" fill="none" stroke="var(--s2)"/>
  <text x="176" y="40" font-size="7.5" fill="var(--s2)">align_corners=True</text>
  <text x="176" y="52" font-size="7" fill="var(--ink)">remaps corners, changes</text>
  <text x="176" y="61" font-size="7" fill="var(--ink)">scale · train/infer mismatch</text>
  <text x="16" y="88" font-size="7.5" fill="var(--muted)">pick one convention pipeline-wide; the half-pixel center is the correct default</text>
  <text x="16" y="104" font-size="7.5" fill="var(--ink)">applies per-axis in 2-D, to upsampling and downsampling alike</text>
</svg>
^ The half-pixel-center convention is the geometrically correct default that matches standard image libraries and GPU sampling; align_corners=True uses a different mapping that changes the effective scale and causes train/inference mismatches. Fix one convention across the pipeline.

**Done means the naive convention is shown to shift the image and fail the flip test while the center convention passes it — so resampling uses src = (j + 0.5)·scale − 0.5 per axis, the align_corners=False / half-pixel-center default, consistently across the pipeline.**

## Boss fight

An engineer trains a segmentation model with images resized by one library and, at inference, resizes with a different library's default. Accuracy is a bit worse than in validation, and the predicted masks look subtly shifted, a pixel or two off, especially near image borders. The model and weights are identical. What is the likely cause, and how would you fix and prevent it?

The two libraries almost certainly use different resampling coordinate conventions — one the half-pixel-center mapping (align_corners=False), the other a corner-aligned mapping (align_corners=True) or a naive src = dst·scale. The half-pixel difference shifts the resized image by a fraction of a pixel, and because the shift is consistent and slightly scale-dependent, the model's learned spatial alignment is off at inference relative to training, which shows up exactly as masks that are a pixel or two shifted and as worse accuracy concentrated near borders where the misalignment and edge handling matter most. The weights are fine; the input geometry changed under them. The fix is to make the resize convention identical in training and inference: pick the half-pixel-center convention (src = (j + 0.5)·scale − 0.5 per axis, align_corners=False in framework terms) and use it in both pipelines, or at minimum use the same library and flags in both. To prevent the class of bug, treat the resize convention as part of the model contract — pin it explicitly rather than relying on a library default that can differ across libraries and versions — and add a test that resizes a known asymmetric test pattern and checks the result against the expected centered output (the flip-symmetry test in this module is a convention-free way to catch a corner-aligned resize without a golden image). More generally, any preprocessing geometry that differs between train and serve — resize convention, crop offsets, normalization — is a silent accuracy leak, and resizing is the most common culprit because the half-pixel offset looks like a harmless implementation detail.

## External resources

The align_corners documentation and discussions for deep-learning resize ops (PyTorch `torch.nn.functional.interpolate`, and the write-ups on TensorFlow's historical `resize_images` alignment bug) — the definition of the half-pixel-center convention, why align_corners=True changes the effective scale, and how the mismatch misaligns feature maps between training and inference.

Image-library resampling references (OpenCV's and PIL's coordinate conventions, and GPU texture-sampling documentation on texel centers) — the standard half-pixel-center mapping this module derives, and confirmation that it is the geometrically correct default the naive corner mapping departs from.
