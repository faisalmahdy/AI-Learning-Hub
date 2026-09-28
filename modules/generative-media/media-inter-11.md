---
id: media-inter-11
title: Divide a convolution kernel by its weight-sum — or a blur that sums to 16 makes the image 16× brighter
topic: generative-media
level: intermediate
status: ready
time: 21 min
summary: What a convolution kernel does to brightness is set by one number — the sum of its weights. Sum 1 preserves the mean, sum S scales it by S, sum 0 zeroes it. A blur kernel summing to 16 must be divided by 16, or the image comes out 1870 mean from 116.875 — 16× too bright. Sharpen sums to 1 already; edge sums to 0 by design.
eli5: A blur mixes each pixel with its neighbors by some recipe of amounts. If those amounts add up to more than one whole pixel, you're adding brightness out of nowhere and the picture gets too bright. You have to scale the recipe back so the amounts add to exactly one — then the picture stays as bright as it was.
---

## Why this module

The most common convolution bug is forgetting one division, and it does not crash — it just quietly changes how bright your image is.

A convolution replaces each pixel with a weighted sum of its neighborhood, using a small grid of numbers called the kernel. The whole effect on brightness comes down to a single property of that grid: the sum of its weights. If the weights sum to 1, the output pixel is a weighted *average* of its neighbors and the overall brightness is preserved. If they sum to some other number S, every output is scaled by S, and the image gets S times brighter or darker. A typical blur kernel — say the binomial `[[1,2,1],[2,4,2],[1,2,1]]` — has weights that sum to 16, because they were written as whole numbers for convenience. Apply it as written and you multiply the image's brightness by sixteen; it clips to white and looks blown out.

The fix is to normalize: divide the kernel by its weight-sum before applying it, so the effective weights sum to 1. Divide that blur by 16 and it becomes a proper average that preserves brightness. This is a one-line step, and it is exactly the line people forget, because the failure is silent — no exception, just a washed-out image that gets blamed on the wrong thing.

What makes the bug sneaky is that it hides behind the kernels that happen to be self-normalizing. A sharpen kernel like `[[0,-1,0],[-1,5,-1],[0,-1,0]]` already sums to 1, so it preserves brightness with no division and works fine as written. An edge-detection kernel sums to 0, and that is deliberate — it is supposed to produce a zero-mean result. Work only with those and you never learn you need to normalize; then you write your first blur, apply it raw, and the image explodes.

We will run all three kernels on one image and read the brightness off each. The blur, raw, drives the mean from 116.875 to 1870 — exactly 16×. Divided by its sum, it holds at 116.875. The sharpen preserves it untouched. The edge kernel drives it to exactly 0.

**A kernel's weight-sum is its brightness multiplier: sum 1 preserves, sum S scales by S, sum 0 zeroes — so a blur written with whole-number weights must be divided by their sum.**

## Concepts

The brightness law is exact and worth stating precisely: convolving an image with a kernel whose weights sum to S multiplies the image's mean brightness by S. The reason is linearity. Each output pixel is a linear combination of input pixels with coefficients from the kernel, and when you sum those outputs over the whole image, each input pixel gets counted once for every kernel position, weighted by the corresponding kernel value — so each input pixel contributes its value times the total kernel weight S. Sum over all pixels and the total brightness scales by exactly S, hence the mean does too. (This is exact under wrap-around edges, where every pixel has a full neighborhood; other edge handling perturbs it slightly at the borders.)

<svg role="img" aria-label="The brightness law: output mean equals kernel sum times input mean, a straight line through the origin with the three kernels marked at sums 0, 1, and 16" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">output mean = kernel-sum × input mean</text>
  <line x1="50" y1="150" x2="440" y2="150" stroke="var(--line)"/><text x="300" y="168" font-family="var(--mono)" font-size="9" fill="var(--muted)">kernel weight-sum →</text>
  <line x1="50" y1="150" x2="50" y2="30" stroke="var(--line)"/>
  <line x1="50" y1="150" x2="420" y2="35" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="50" cy="150" r="4" fill="var(--ink)"/><text x="42" y="145" font-family="var(--mono)" font-size="9" fill="var(--ink)">edge (0) → mean 0</text>
  <circle cx="73" cy="143" r="4" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="80" y="140" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">sharpen (1) → preserved</text>
  <circle cx="418" cy="36" r="5" fill="var(--s2)"/><text x="300" y="52" font-family="var(--mono)" font-size="9" fill="var(--s2)">blur (16) → 16× (raw)</text>
  <line x1="73" y1="30" x2="73" y2="150" stroke="var(--acc-ink)" stroke-dasharray="3 2"/><text x="80" y="60" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">sum 1 = preserve</text>
</svg>
^ Brightness scales linearly with the weight-sum, so preserving brightness means landing on sum 1 — the blur at sum 16 sits far up the line until you divide it back down.

That law tells you what each kind of kernel is for. A blurring or averaging kernel should sum to 1 — it redistributes brightness among neighbors without creating or destroying any. A sharpening kernel also sums to 1, because it preserves overall brightness while amplifying local differences. An edge or gradient kernel sums to 0, because it measures *change* rather than level: on a flat region it should output zero, and a zero-sum kernel does exactly that. So the weight-sum is not an arbitrary detail; it encodes the operation's relationship to brightness, and getting it wrong means the kernel is doing a different job than you think.

Normalization is how you set the sum to the value the operation needs. For a blur, you write the weights as convenient integers and then divide by their sum, turning a weighted sum into a weighted average. You could instead write the weights as fractions that already sum to 1, but integer weights plus a divisor is the standard idiom — it keeps the weights readable and puts the normalization in one obvious place. The bug is when that place is empty: the weights are there, the divisor is not, and the kernel silently sums to 16 instead of 1.

The failure mode is specifically insidious because it is not obviously wrong. A 16× brightness multiply clips most of the image to pure white, which a careless eye might read as "over-exposed input" or "the blur washed it out" rather than "I forgot to divide." And a subtler version — dividing by the wrong constant, say 9 for a 3×3 kernel assuming uniform weights when the kernel actually sums to 16 — produces a mild brightness shift that is easy to miss entirely and slowly corrupts a pipeline that applies the filter repeatedly.

**The weight-sum encodes the operation's job — average, sharpen, or difference — so normalizing to the intended sum is not tidying, it is making the kernel do what you meant.**

## Worked example

The fixture is a small image and three kernels — one that needs normalizing and two that do not.

```text filename=modules/generative-media/code/media-inter-11/normalize.py --kernels
KERNELS — the 3x3 weights and their sums
--------------------------------------------
  blur     sum = 16   [[1, 2, 1], [2, 4, 2], [1, 2, 1]]
  sharpen  sum =  1   [[0, -1, 0], [-1, 5, -1], [0, -1, 0]]
  edge     sum =  0   [[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]]
```

The blur sums to 16, the sharpen to 1, the edge to 0. The weight-sum is just the total of the grid.

```python filename=modules/generative-media/code/media-inter-11/normalize.py:40-41 COMPLETE
def kernel_sum(k):
    return sum(sum(row) for row in k)
```

Brightness is the mean pixel value.

```python filename=modules/generative-media/code/media-inter-11/normalize.py:44-46 COMPLETE
def mean(img):
    flat = [v for row in img for v in row]
    return round(sum(flat) / len(flat), 4)
```

The convolution uses wrap-around edges so the brightness law is exact — the divisor argument is where normalization happens (1 for raw, the kernel sum for normalized).

```python filename=modules/generative-media/code/media-inter-11/normalize.py:51-65 COMPLETE
def convolve(img, k, divisor):
    """Convolve with wrap-around edges, dividing the result by `divisor`. Wrap makes the brightness law exact."""
    h, w = len(img), len(img[0])
    out = []
    for r in range(h):
        row = []
        for c in range(w):
            acc = 0
            for i in range(3):
                for j in range(3):
                    rr, cc = (r + i - 1) % h, (c + j - 1) % w  # wrap around the edges
                    acc += k[i][j] * img[rr][cc]
            row.append(acc / divisor)
        out.append(row)
    return out
```

The input image has mean brightness 116.875. Predict each output's mean: the blur raw should be 16 × 116.875 = 1870; the blur divided by 16 should be 116.875; the sharpen (sum 1) should stay 116.875 with or without division; the edge (sum 0) should be 0. Run it.

```text filename=modules/generative-media/code/media-inter-11/normalize.py --brightness
BRIGHTNESS — mean after each kernel, applied raw vs divided by its sum (input mean 116.875)
------------------------------------------------------------------------
  blur     sum 16   raw mean  1870.000   divided-by-sum mean 116.875
  sharpen  sum  1   raw mean   116.875   divided-by-sum mean 116.875
  edge     sum  0   raw mean     0.000   divided-by-sum mean (sum 0 -- cannot divide)
```

The blur, applied raw, drives the mean to 1870 — sixteen times the input, exactly as the weight-sum predicts, and far past the 255 ceiling of an 8-bit image, so every pixel would clip to white. Divided by 16, it lands back on 116.875: brightness preserved, blur applied. The sharpen preserves 116.875 whether or not you divide, because its weights already sum to 1 — dividing by 1 does nothing. And the edge kernel produces a mean of exactly 0, which is correct: it measures change, and the average change across a wrapped image is zero. Only the blur needed the divide, and it is the one that would silently break.

<svg role="img" aria-label="Three kernels and their weight-sums mapped to what they do to brightness: blur sum 16 scales, sharpen sum 1 preserves, edge sum 0 zeroes" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">weight-sum → effect on brightness</text>
  <rect x="30" y="45" width="110" height="30" fill="var(--s2)" stroke="var(--line)"/><text x="42" y="65" font-family="var(--mono)" font-size="11" fill="var(--ink)">blur  sum 16</text>
  <text x="150" y="65" font-family="var(--mono)" font-size="10" fill="var(--s2)">→ 16× brighter (must ÷16)</text>
  <rect x="30" y="85" width="110" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="42" y="105" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">sharpen sum 1</text>
  <text x="150" y="105" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">→ brightness preserved</text>
  <rect x="30" y="125" width="110" height="30" fill="var(--panel)" stroke="var(--line)"/><text x="42" y="145" font-family="var(--mono)" font-size="11" fill="var(--ink)">edge  sum 0</text>
  <text x="150" y="145" font-family="var(--mono)" font-size="10" fill="var(--muted)">→ mean zeroed (difference)</text>
</svg>
^ The weight-sum reads directly off the kernel and tells you its brightness behavior: only the blur, at sum 16, needs dividing back to 1.

<svg role="img" aria-label="Mean brightness bars: input 117, raw blur 1870 far past the 255 white ceiling, normalized blur 117, edge 0" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">mean brightness (8-bit white = 255)</text>
  <line x1="70" y1="150" x2="440" y2="150" stroke="var(--line)"/>
  <line x1="70" y1="120" x2="440" y2="120" stroke="var(--acc-ink)" stroke-dasharray="4 3"/><text x="360" y="116" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">255 (white)</text>
  <rect x="90" y="122" width="40" height="28" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="86" y="164" font-family="var(--mono)" font-size="8" fill="var(--muted)">input 117</text>
  <rect x="170" y="35" width="40" height="115" fill="var(--s2)" stroke="var(--line)"/><text x="166" y="30" font-family="var(--mono)" font-size="9" fill="var(--s2)">1870</text><text x="166" y="164" font-family="var(--mono)" font-size="8" fill="var(--muted)">raw blur</text>
  <rect x="250" y="122" width="40" height="28" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="246" y="164" font-family="var(--mono)" font-size="8" fill="var(--muted)">÷16 blur 117</text>
  <rect x="350" y="148" width="40" height="2" fill="var(--ink)" stroke="var(--line)"/><text x="360" y="164" font-family="var(--mono)" font-size="8" fill="var(--muted)">edge 0</text>
</svg>
^ The raw blur towers seven times past the white ceiling — it clips to pure white; dividing by the weight-sum brings it back level with the input.

## Build

Reproduce the brightnesses. Pure standard library, wrap-around edges, so 1870.000, 116.875, and 0.000 come out exactly.

Run `--kernels` for the sums, `--brightness` for the means, `--check` for the gate. The self-test verifies the whole brightness law: the raw blur scales by its sum, dividing preserves, the sharpen self-preserves, and the edge zeroes.

```python filename=modules/generative-media/code/media-inter-11/normalize.py:101-109 COMPLETE
    blur_s = kernel_sum(ks["blur"])
    raw_blur = mean(convolve(img, ks["blur"], 1))
    raw_scales_by_sum = abs(raw_blur - blur_s * m0) < 1e-6
    print("  the raw blur scales the mean by its weight-sum = %s (%.3f = %d x %.3f)"
          % (raw_scales_by_sum, raw_blur, blur_s, m0))

    norm_blur = mean(convolve(img, ks["blur"], blur_s))
    dividing_preserves = abs(norm_blur - m0) < 1e-6
    print("  dividing the blur by its sum preserves the mean = %s (%.3f = %.3f)" % (dividing_preserves, norm_blur, m0))
```

The `raw_scales_by_sum` check is an exact equality — `abs(raw_blur - blur_s * m0) < 1e-6` — that verifies the brightness law itself, not just that the blur is "too bright." It asserts the raw output mean equals the kernel sum times the input mean to floating-point precision. That is only exactly true because the convolution wraps its edges; the check and the wrap padding are a matched pair, and the exactness is what turns "the blur brightens the image" into "the blur multiplies brightness by exactly its weight-sum." The sharpen and edge checks complete the picture.

```python filename=modules/generative-media/code/media-inter-11/normalize.py:111-117 COMPLETE
    sharpen_s = kernel_sum(ks["sharpen"])
    sharpen_preserves = sharpen_s == 1 and abs(mean(convolve(img, ks["sharpen"], 1)) - m0) < 1e-6
    print("  the sharpen sums to 1 and preserves the mean untouched = %s (sum %d)" % (sharpen_preserves, sharpen_s))

    edge_s = kernel_sum(ks["edge"])
    edge_zeroes = edge_s == 0 and abs(mean(convolve(img, ks["edge"], 1))) < 1e-6
    print("  the edge kernel sums to 0 and zeroes the mean = %s (sum %d, mean %.3f)"
          % (edge_zeroes, edge_s, mean(convolve(img, ks["edge"], 1))))
```

```text filename=modules/generative-media/code/media-inter-11/normalize.py --check
SELF-TEST — the raw blur scales brightness by its sum; dividing by the sum preserves it
------------------------------------------------------------------------------------
  the raw blur scales the mean by its weight-sum = True (1870.000 = 16 x 116.875)
  dividing the blur by its sum preserves the mean = True (116.875 = 116.875)
  the sharpen sums to 1 and preserves the mean untouched = True (sum 1)
  the edge kernel sums to 0 and zeroes the mean = True (sum 0, mean 0.000)
------------------------------------------------------------------------------------
SELF-TEST PASS  raw_scales_by_sum=True  dividing_preserves=True  sharpen_preserves=True  edge_zeroes=True
```

Four True flags. Raw_scales_by_sum: the brightness law holds exactly. Dividing_preserves: normalizing fixes it. Sharpen_preserves: a sum-1 kernel needs no divide. Edge_zeroes: a sum-0 kernel is supposed to zero the mean. Together they say the weight-sum fully determines brightness behavior, and normalization is how you choose it.

**The exact-equality check works only because the convolution wraps its edges — the check and the padding are a matched pair, and the exactness turns "too bright" into "×16 exactly."**

## Definition of done

You are done when you reproduce the means and can read a kernel's brightness behavior off its weight-sum.

Concretely: `--brightness` shows the raw blur at 1870 versus the normalized blur at 116.875, the sharpen preserving, and the edge zeroing; `--check` prints PASS with four True flags. You can state the brightness law — output mean equals kernel sum times input mean — and explain it from linearity. You can classify a kernel by its sum: sum 1 for average and sharpen, sum 0 for edge and gradient, any other sum a bug for a brightness-preserving filter. And you can name the failure mode: writing integer blur weights and forgetting the divide, producing a silently over-bright, clipped image.

The habit to carry: before applying any kernel, sum its weights, and if it should preserve brightness, confirm it sums to 1 or divide it by its sum. When a filtered image comes out mysteriously washed out or dark, check the kernel sum first — it is the single most likely cause.

## Boss fight

The instructive failure is a filter that drifts an image darker every time it runs.

A pipeline applies a smoothing kernel written as integers, and someone normalizes it — but by the wrong constant. They divide a 3×3 kernel by 9, reasoning "nine cells, divide by nine," when the actual weights sum to 16. Now every application multiplies brightness by 16/9 ≈ 1.78, or if they over-divide, shrinks it. On a single pass it might pass review as "a little bright." But the pipeline applies the smoothing every frame of a video, or every step of an iterative denoiser, and the brightness compounds: 1.78 per pass over ten passes is 300×, or the darkening version fades the image toward black. The bug is one wrong constant, and it is invisible per-pass and catastrophic over many. The fix is to always divide by the actual `sum(kernel)`, computed, never by a guessed constant.

Your turn, two moves. First, confirm the compounding. Take the blur normalized by 9 instead of 16 and predict the per-pass brightness factor (16/9 ≈ 1.78) and where a 116.875-mean image ends up after three passes (116.875 × 1.78³ ≈ 660, clipped). Run it by changing the divisor and watch the drift. Second, build a kernel to a target. Suppose you want a kernel that *doubles* brightness while blurring — an unusual but valid request. Predict its required weight-sum (2) and confirm that scaling the normalized blur's weights so they sum to 2 produces exactly a 2× brightness output. That closes the loop: the weight-sum is not a constraint you obey blindly, it is a dial you set to whatever brightness behavior you actually want, and "preserve brightness" is just the special case of setting it to 1.

## External resources

Any image-processing reference covers kernel normalization; Szeliski's "Computer Vision" and the classic Gonzalez and Woods "Digital Image Processing" both state the sum-to-one rule for smoothing kernels and sum-to-zero for derivative kernels.

For the hands-on version, the documentation for convolution in OpenCV, Pillow, and scipy.ndimage all note that smoothing kernels must be normalized by their sum, and several provide the normalized kernels precisely so users do not hit this bug.

For the theory, the brightness law is the DC-gain of the filter: the kernel's response to a constant (zero-frequency) input is the sum of its weights, which is why a low-pass filter needs sum 1 and a high-pass or derivative filter needs sum 0 — any signals-and-systems treatment of 2D filters frames it this way.
