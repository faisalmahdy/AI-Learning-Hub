---
id: separable-inter-01
title: Blur with two 1-D passes, not one 2-D kernel — a separable filter gives the identical result at a fraction of the cost
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: A Gaussian blur, a box blur, and many common filters are applied by convolution — slide a k-by-k kernel over the image and at each pixel multiply the kernel weights by the covered pixels and sum. Done directly this is k×k multiply-adds per output pixel, and for a real blur (an 11×11 or 21×21 kernel) that is a hundred to several hundred operations at every pixel. The saving comes from a structural fact about these kernels: they are separable — a separable 2-D kernel is exactly the outer product of a 1-D kernel with itself, which the Gaussian classically is, because a 2-D Gaussian factors into a product of two 1-D Gaussians, one per axis. When a kernel separates like this, convolving with the full 2-D kernel is mathematically identical to convolving each row with the 1-D kernel and then convolving each column of that intermediate with the same 1-D kernel — two passes of a k-length filter instead of one pass of a k-by-k filter. The cost drops from k×k to 2k per pixel, and the outputs are not approximately equal but identical, because the two-pass computation is just the 2-D convolution's sum re-associated, not an approximation. For k=3 that is 9 versus 6, a modest win; for k=11 it is 121 versus 22, and for k=21, 441 versus 42 — the larger the blur, the bigger the factor, which is why every production image library implements Gaussian blur as separable passes. The one precondition is separability, which Gaussian, box, and many smoothing and derivative kernels satisfy. On a fixture with the 1-D kernel [0.25, 0.5, 0.25], its outer product is the 3×3 blur kernel, and the 2-D convolution and the two 1-D passes produce identical interior outputs (max difference 0, center 40 → 25) at 9 versus 6 operations per pixel.
eli5: Imagine you want to gently smudge a drawing so it looks soft, and your smudging tool is a little 3-by-3 square stamp — every time you press it, you blend a pixel with its 8 neighbors, which is 9 things to mix. That works, but it is a lot of mixing. It turns out you can get the exact same softness in two easy steps: first smudge the whole picture a little left-and-right, then smudge that result a little up-and-down. Each smudge only mixes 3 things instead of 9, so it is less work — and because the left-right-then-up-down smudge is really the same blend split into two directions, the picture comes out looking identical, not just close. The bigger and softer the smudge you want, the more work this two-step trick saves.
---

## Why this module

Blur is one of the most-run operations in all of image processing — it is inside denoising, downsampling, bloom, depth-of-field, edge detection, and half the filters in any photo app — so how you implement it matters at scale. The naive implementation is the direct definition of convolution: a k-by-k kernel, k×k multiplications per pixel. For a 3×3 that is cheap; for the 15×15 or 25×25 kernels a real Gaussian blur uses, it is hundreds of multiplications at every pixel of a multi-megapixel image, and it is the difference between a filter that runs in real time and one that stutters.

The reason you almost never pay that full cost is a property of the kernel itself, not a clever approximation. Many blur and smoothing kernels are separable: the 2-D kernel is the outer product of a single 1-D kernel with itself. The Gaussian is the canonical case, because the 2-D Gaussian is literally a product of a horizontal Gaussian and a vertical Gaussian. When that holds, the 2-D convolution can be factored into two 1-D convolutions — one along rows, one along columns — and the result is not an estimate of the 2-D blur, it is the 2-D blur, exactly, by the associativity of the sum.

This module runs the same blur both ways on a small image, proves the outputs are byte-identical, and counts the operations each path costs.

**Apply a separable blur as two 1-D convolutions — once across rows, once down columns — rather than one 2-D convolution with the full kernel, because a separable kernel is the outer product of a 1-D kernel with itself, so the two-pass computation gives the byte-identical result at 2k multiply-adds per pixel instead of k×k, a saving that grows with kernel size.**

## Concepts

The fixture is a 5×5 grayscale image — a symmetric bump, peaking at 40 in the center — and a 1-D blur kernel [0.25, 0.5, 0.25]. That 1-D kernel is the whole specification: the 2-D kernel is derived from it.

```json filename=modules/generative-media/code/separable-inter-01/separable.json:12-18 COMPLETE
  "image": [
    [10, 10, 10, 10, 10],
    [10, 20, 20, 20, 10],
    [10, 20, 40, 20, 10],
    [10, 20, 20, 20, 10],
    [10, 10, 10, 10, 10]
  ],
  "kernel_1d": [0.25, 0.5, 0.25]
```

The 2-D kernel a separable filter uses is the outer product of the 1-D kernel with itself — every pair of weights multiplied. The direct 2-D convolution slides that full kernel over the interior pixels, doing k×k multiply-adds each.

```python filename=modules/generative-media/code/separable-inter-01/separable.py:53-70 COMPLETE
def outer(k1d):
    """The 2-D kernel a 1-D kernel generates: the outer product of the kernel with itself."""
    return [[a * b for b in k1d] for a in k1d]


def conv2d_interior(img, k2d):
    """Full 2-D convolution at interior pixels (valid region), k*k multiply-adds each."""
    h, w = len(img), len(img[0])
    r = len(k2d) // 2
    out = []
    for y in range(r, h - r):
        row = []
        for x in range(r, w - r):
            s = 0.0
            for i in range(len(k2d)):
                for j in range(len(k2d)):
                    s += img[y + i - r][x + j - r] * k2d[i][j]
            row.append(s)
        out.append(row)
    return out
```

The separable path does the same blur as two 1-D passes: first convolve every row with the 1-D kernel (the horizontal pass), then convolve every column of that intermediate with the same 1-D kernel (the vertical pass). Each pass touches only k pixels, so the total is 2k per output pixel.

```python filename=modules/generative-media/code/separable-inter-01/separable.py:73-89 COMPLETE
def separable_interior(img, k1d):
    """Two 1-D passes: rows then columns, 2*k multiply-adds each, over the same interior region."""
    h, w = len(img), len(img[0])
    r = len(k1d) // 2
    horiz = [[None] * w for _ in range(h)]
    for y in range(h):
        for x in range(r, w - r):
            horiz[y][x] = sum(img[y][x + j - r] * k1d[j] for j in range(len(k1d)))
    out = []
    for y in range(r, h - r):
        row = []
        for x in range(r, w - r):
            row.append(sum(horiz[y + i - r][x] * k1d[i] for i in range(len(k1d))))
        out.append(row)
    return out
```

<svg role="img" aria-label="A 2-D kernel factoring into a vertical 1-D kernel times a horizontal 1-D kernel, with the two-pass path shown as a horizontal blur followed by a vertical blur" viewBox="0 0 320 150">
  <text x="10" y="20" font-size="9" fill="var(--muted)">2-D kernel = outer product of 1-D with itself</text>
  <text x="20" y="45" font-size="9" fill="var(--ink)">[.0625 .125 .0625]</text>
  <text x="20" y="60" font-size="9" fill="var(--ink)">[.125&#8195;.25&#8195;.125&#8197;]</text>
  <text x="20" y="75" font-size="9" fill="var(--ink)">[.0625 .125 .0625]</text>
  <text x="150" y="60" font-size="11" fill="var(--muted)">=</text>
  <text x="168" y="60" font-size="9" fill="var(--s1)">[.25 .5 .25]ᵀ</text>
  <text x="235" y="60" font-size="11" fill="var(--muted)">×</text>
  <text x="250" y="60" font-size="9" fill="var(--s2)">[.25 .5 .25]</text>
  <rect x="20" y="100" width="70" height="24" fill="var(--s2)"/>
  <text x="28" y="116" font-size="9" fill="var(--panel)">blur rows</text>
  <text x="96" y="116" font-size="11" fill="var(--muted)">→</text>
  <rect x="112" y="100" width="80" height="24" fill="var(--s1)"/>
  <text x="120" y="116" font-size="9" fill="var(--panel)">blur columns</text>
  <text x="200" y="116" font-size="9" fill="var(--muted)">= same result, 2k ops</text>
</svg>
^ The 3×3 kernel factors into a column kernel times a row kernel — that is what separable means. So the 2-D blur can be done as a horizontal 1-D pass followed by a vertical 1-D pass, each costing k, for 2k total instead of k×k.

**Separability is not a property of the blur you want but of the kernel that produces it — when the 2-D kernel is an outer product, the convolution factors, and factoring a sum is exact, not approximate.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the blur step of an image-processing pipeline, reduced to a 5×5 image so every convolved value is checkable by hand.

Run `--kernels` to see the 1-D kernel and the 2-D kernel it generates.

```text filename=separable.py --kernels
  1-D kernel = [0.25, 0.5, 0.25]  (sum 1)
  2-D kernel = outer product:
    [0.0625 0.1250 0.0625]
    [0.1250 0.2500 0.1250]
    [0.0625 0.1250 0.0625]
  2-D kernel sum = 1 (normalized) ; separable = True
```

The 2-D kernel is every pair of 1-D weights multiplied: the center is 0.5×0.5 = 0.25, the edges 0.5×0.25 = 0.125, the corners 0.25×0.25 = 0.0625. Both kernels sum to 1, so the blur preserves overall brightness rather than darkening or brightening the image. And the kernel is confirmed separable — which it must be, since it was built as an outer product.

Now `--blur` runs both convolutions over the interior.

```text filename=separable.py --blur
  2-D convolved interior:
    [16.875 20.000 16.875]
    [20.000 25.000 20.000]
    [16.875 20.000 16.875]
  two-pass interior:
    [16.875 20.000 16.875]
    [20.000 25.000 20.000]
    [16.875 20.000 16.875]
  maximum difference = 0 (identical)
```

The two grids are the same to the last digit — maximum difference 0. The center pixel, which was 40 in the original, is now 25: the blur pulled the bright peak down toward its neighbors, which is exactly what a blur does. Both methods produce that 25; the separable path did it in 6 multiply-adds per pixel, the 2-D path in 9, and they agree completely because the two-pass sum is the 2-D sum reorganized, not a cheaper approximation of it.

<svg role="img" aria-label="A tall narrow bump at value 40 becoming a shorter wider bump at value 25 after blurring, with corners rising from the surround" viewBox="0 0 320 120">
  <text x="10" y="18" font-size="9" fill="var(--muted)">center pixel, before → after blur</text>
  <line x1="20" y1="100" x2="150" y2="100" stroke="var(--line)" stroke-width="1"/>
  <rect x="70" y="24" width="26" height="76" fill="var(--s2)"/>
  <text x="72" y="20" font-size="9" fill="var(--ink)">40</text>
  <text x="55" y="113" font-size="8" fill="var(--muted)">before (sharp peak)</text>
  <line x1="180" y1="100" x2="310" y2="100" stroke="var(--line)" stroke-width="1"/>
  <rect x="212" y="52" width="26" height="48" fill="var(--s1)"/>
  <text x="214" y="48" font-size="9" fill="var(--ink)">25</text>
  <rect x="186" y="68" width="26" height="32" fill="var(--s1)" opacity="0.5"/>
  <rect x="238" y="68" width="26" height="32" fill="var(--s1)" opacity="0.5"/>
  <text x="205" y="113" font-size="8" fill="var(--muted)">after (peak lowered, spread)</text>
</svg>
^ The blur pulls the sharp 40 peak down to 25 and lifts its neighbors — brightness is conserved (both kernels sum to 1), so the energy spreads rather than disappearing. Both the 2-D and separable paths produce this exact result.

**The two paths produce identical values including the center's 40 → 25 blur — the separable version is not a faster estimate of the 2-D blur, it is the same computation with the additions regrouped.**

## Build

The self-test asserts the precondition and the payoff: that the kernel is genuinely separable, that both kernels are normalized so the blur preserves brightness, and — the central claim — that the two-pass output is bit-for-bit identical to the 2-D output.

```python filename=modules/generative-media/code/separable-inter-01/separable.py:112-123 COMPLETE
    kernel_separable = is_separable(k2d, k1d)
    print("  the 2-D kernel is the outer product of the 1-D kernel (separable) = %s" % kernel_separable)

    kernel_normalized = abs(sum(k1d) - 1.0) < 1e-12 and abs(sum(sum(r) for r in k2d) - 1.0) < 1e-12
    print("  both kernels sum to 1 (blur preserves brightness) = %s (1-D %g, 2-D %g)" % (kernel_normalized, sum(k1d), sum(sum(r) for r in k2d)))

    results_identical = max_diff(a, b) < 1e-12
    print("  the two-pass output is identical to the 2-D output = %s (max diff %g)" % (results_identical, max_diff(a, b)))

    two_d_ops = k * k
    sep_ops = 2 * k
    separable_fewer_ops = sep_ops < two_d_ops
    print("  the separable passes use fewer multiply-adds per pixel = %s (%d vs %d for k=%d)" % (separable_fewer_ops, sep_ops, two_d_ops, k))
```

<svg role="img" aria-label="A bar chart comparing operations per pixel for 2-D versus separable at kernel sizes 3, 11, and 21, with the 2-D bars growing quadratically and the separable bars staying short" viewBox="0 0 320 140">
  <line x1="30" y1="115" x2="300" y2="115" stroke="var(--line)" stroke-width="1"/>
  <text x="40" y="128" font-size="8" fill="var(--muted)">k=3</text>
  <rect x="40" y="106" width="16" height="9" fill="var(--s2)"/><text x="58" y="114" font-size="7" fill="var(--muted)">9</text>
  <rect x="40" y="109" width="16" height="6" fill="var(--s1)"/>
  <text x="130" y="128" font-size="8" fill="var(--muted)">k=11</text>
  <rect x="130" y="55" width="16" height="60" fill="var(--s2)"/><text x="148" y="52" font-size="7" fill="var(--muted)">121</text>
  <rect x="130" y="104" width="16" height="11" fill="var(--s1)"/><text x="148" y="114" font-size="7" fill="var(--muted)">22</text>
  <text x="220" y="128" font-size="8" fill="var(--muted)">k=21</text>
  <rect x="220" y="15" width="16" height="100" fill="var(--s2)"/><text x="238" y="24" font-size="7" fill="var(--muted)">441</text>
  <rect x="220" y="94" width="16" height="21" fill="var(--s1)"/><text x="238" y="108" font-size="7" fill="var(--muted)">42</text>
  <text x="40" y="20" font-size="8.5" fill="var(--s2)">2-D: k×k</text>
  <text x="40" y="33" font-size="8.5" fill="var(--s1)">separable: 2k</text>
</svg>
^ Operations per pixel: the 2-D cost grows as k² while the separable cost grows as 2k. At k=3 they are close (9 vs 6); by k=21 it is 441 vs 42, a tenfold saving — which is why real blurs are always separable passes.

Running the check confirms every clause, including that the saving grows with k and the center is genuinely blurred.

```text filename=separable.py --check
  the 2-D kernel is the outer product of the 1-D kernel (separable) = True
  both kernels sum to 1 (blur preserves brightness) = True (1-D 1, 2-D 1)
  the two-pass output is identical to the 2-D output = True (max diff 0)
  the separable passes use fewer multiply-adds per pixel = True (6 vs 9 for k=3)
  the saving grows with kernel size = True (k=11: 121 vs 22, ratio 5.5x > k=3 ratio 1.5x)
  the bright center is actually blurred (peak lowered) = True (25.0 < 40)
```

**The check pins both halves — the identity of the outputs and the reduction in operations — so the separable path is proven to be the same blur, done cheaper, not a different, faster one.**

## Definition of done

Two properties close it, and they are the two that make separability a free win rather than a trade. The outputs must be identical (max difference 0), so nothing is sacrificed for the speed, and the operation count must be strictly lower and grow more favorably with k, so the speed is real and scales.

```python filename=modules/generative-media/code/separable-inter-01/separable.py:125-129 COMPLETE
    big_two_d, big_sep = 11 * 11, 2 * 11
    saving_grows_with_k = (big_two_d / big_sep) > (two_d_ops / sep_ops)
    print("  the saving grows with kernel size = %s (k=11: %d vs %d, ratio %.1fx > k=%d ratio %.1fx)"
          % (saving_grows_with_k, big_two_d, big_sep, big_two_d / big_sep, k, two_d_ops / sep_ops))

    center_is_blurred = a[len(a) // 2][len(a[0]) // 2] < img[len(img) // 2][len(img[0]) // 2]
    print("  the bright center is actually blurred (peak lowered) = %s (%.1f < %d)" % (center_is_blurred, a[len(a) // 2][len(a[0]) // 2], img[len(img) // 2][len(img[0]) // 2]))
```

The one precondition keeps the tool from being mis-applied: separability is required, and not every kernel has it. Gaussian, box, and many smoothing and first-derivative kernels are separable by construction, and the Sobel operator is separable (a smoothing kernel times a difference kernel). But a genuinely non-separable kernel — a disk-shaped bokeh kernel, an arbitrary learned filter, a motion blur along a diagonal — cannot be split into two 1-D passes and must be applied in full 2-D, or approximated by a sum of a few separable kernels (a low-rank approximation, which is how large non-separable blurs are often sped up). The check that a kernel equals its 1-D outer product is exactly the test for whether the trick applies. Where it applies it is pure win: identical output, fewer operations, no downside.

**Done means the two-pass blur is provably identical to the 2-D blur and strictly cheaper with a saving that grows as k — a free speedup wherever the kernel is separable, and a test (outer-product equality) for when it is.**

## Boss fight

You profile an image pipeline and find that a Gaussian blur with a 25×25 kernel is the bottleneck, eating most of the frame time. A teammate proposes shrinking the kernel to 9×9 to speed it up, accepting a less smooth blur. Before you sacrifice blur quality, what should you check, and what would you change instead?

Check whether the blur is implemented as a full 2-D convolution or as two separable 1-D passes — a 25×25 Gaussian done in 2-D is 625 multiply-adds per pixel, but the Gaussian is separable, so the identical blur done as two 1-D passes is 2×25 = 50 per pixel, more than a tenfold reduction with no change to the output. If the pipeline is doing the full 2-D convolution, that is the bottleneck, and switching to separable passes gives you the same 25×25 quality at a fraction of the cost — you do not have to shrink the kernel at all. Shrinking to 9×9 would sacrifice the smoothness you presumably chose 25 for, and even the 9×9, done in 2-D, is 81 ops per pixel versus 18 separable, so the real problem is the implementation, not the kernel size. The change is to factor the Gaussian into its 1-D kernel and run a horizontal pass then a vertical pass. If the kernel in question were genuinely non-separable (say a shaped bokeh), then separable passes would not apply and you would look at a low-rank approximation or a different algorithm — but for a Gaussian, separability is the answer and it costs nothing in quality.

## External resources

The Wikipedia article on separable filters and the "separable convolution" sections of standard image-processing texts — the derivation of why a separable 2-D kernel factors into two 1-D convolutions, and the k² versus 2k cost argument, stated in general.

The OpenCV `getGaussianKernel` and `sepFilter2D` documentation — the production API that hands you the 1-D Gaussian kernel and applies it as separable row/column passes, the exact operation this module models, plus `getDerivKernels` showing the Sobel operator's separable factorization.
