---
id: media-inter-10
title: A 2D Gaussian blur factors into two 1D passes — identical output, a fraction of the multiplies
topic: generative-media
level: intermediate
status: ready
time: 22 min
summary: A separable 2D kernel is the outer product of a 1D kernel with itself, so a blur can run as a row pass then a column pass. On a 5×5 Gaussian that is 10 taps per pixel instead of 25 — the same image pixel for pixel, at k/2 the cost. But skip a pass and you get a horizontal smear, not a blur.
eli5: To blur a picture you normally mix each pixel with the 25 pixels around it. But you can get the exact same result by first blurring left-to-right, then blurring the result top-to-bottom — only 10 mixes instead of 25. The trick only works if you do both directions; do one and you've just smeared it sideways.
---

## Why this module

Separability is the difference between a blur that runs in real time and one that does not, and it is free — the output is bit-for-bit identical, you just stop doing most of the arithmetic.

Here is the arithmetic that matters. A 2D convolution slides a kernel over the image and, for each output pixel, multiplies and sums every kernel tap against the pixels under it. A 5×5 Gaussian has 25 taps, so every output pixel costs 25 multiply-adds. Scale that to a four-megapixel image and you are doing a hundred million multiply-adds per blur, per frame, and a real pipeline blurs constantly — bloom, depth of field, shadows, denoising. The 25 is the whole cost, and it grows as the square of the kernel width: a 9×9 blur is 81 taps, a 15×15 is 225.

The Gaussian has a property that collapses that square back to a line. It is separable: its 2D kernel is exactly the outer product of a 1D kernel with itself. And a separable convolution factors into two 1D convolutions — blur along the rows with the 1D kernel, then blur that result along the columns with the same 1D kernel. Now each output pixel costs 5 taps for the row pass plus 5 for the column pass: 10 instead of 25. The cost drops from k² to 2k, so the wider the kernel the bigger the win — a 15×15 blur goes from 225 taps to 30, a 7.5× saving, for the identical image.

The trap, and the reason this needs demonstrating rather than asserting, is that "two 1D passes" is a factoring of the full 2D convolution, not a shortcut that does half the work. Do only the row pass and you have blurred horizontally and not at all vertically — a directional smear that looks nothing like a Gaussian. We will run all three: the full 2D blur, the separable two-pass blur that matches it pixel for pixel at 10 taps, and the rows-only blur that costs 5 taps and is simply wrong.

**A separable kernel lets you pay 2k instead of k² per pixel for the identical result — but only if both passes run; one pass is a smear, not a blur.**

## Concepts

Separability is a statement about the kernel's structure. A 2D kernel is separable when it can be written as the outer product of two 1D vectors — when every entry K[i][j] equals a[i]·b[j] for some 1D vectors a and b. The Gaussian qualifies because a 2D Gaussian is the product of a horizontal Gaussian and a vertical one; box blurs qualify; many sharpening and edge kernels qualify. When a kernel is separable, the double sum that defines the 2D convolution factors, by distributivity, into an inner sum over one axis wrapped in an outer sum over the other — which is precisely a 1D convolution followed by a second 1D convolution.

The cost argument is then just counting. The full 2D convolution evaluates k² taps per output pixel. The separable form evaluates k taps in the first pass and k in the second, touching an intermediate image in between: 2k taps per pixel. The ratio is k²/2k = k/2, so the speedup is exactly half the kernel width. At k=5 that is 2.5×; at k=15 it is 7.5×. This is why every graphics and vision library implements Gaussian blur separably and why kernel width, not image size, is where the separable win lives.

<svg role="img" aria-label="Taps per pixel versus kernel width: the 2D cost grows as k squared while the separable cost grows as 2k, the gap widening with width" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">taps per pixel vs kernel width k</text>
  <line x1="50" y1="160" x2="440" y2="160" stroke="var(--line)"/>
  <line x1="50" y1="30" x2="50" y2="160" stroke="var(--line)"/>
  <g font-family="var(--mono)" font-size="10" fill="var(--muted)">
    <text x="88" y="174">3</text><text x="168" y="174">5</text><text x="258" y="174">9</text><text x="345" y="174">15</text>
  </g>
  <polyline points="90,151 170,135 260,79 350,35" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <circle cx="90" cy="151" r="3" fill="var(--s2)"/><circle cx="170" cy="135" r="3" fill="var(--s2)"/><circle cx="260" cy="79" r="3" fill="var(--s2)"/><circle cx="350" cy="35" r="3" fill="var(--s2)"/>
  <text x="300" y="52" font-family="var(--mono)" font-size="10" fill="var(--s2)">2D: k² (9,25,81,225)</text>
  <polyline points="90,157 170,154 260,149 350,143" fill="none" stroke="var(--acc-ink)" stroke-width="2"/>
  <circle cx="90" cy="157" r="3" fill="var(--acc-line)"/><circle cx="170" cy="154" r="3" fill="var(--acc-line)"/><circle cx="260" cy="149" r="3" fill="var(--acc-line)"/><circle cx="350" cy="143" r="3" fill="var(--acc-line)"/>
  <text x="230" y="139" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">separable: 2k (6,10,18,30)</text>
</svg>
^ The 2D cost curves upward as k² while the separable cost creeps up as 2k — the wider the blur, the more the separable form saves.

The order of the two passes does not matter — rows then columns, or columns then rows, give the same result, because convolution is commutative and the two 1D kernels act on independent axes. What matters is that both passes happen. The intermediate image after the first pass is not a blur of anything meaningful; it is a half-done computation, blurred on one axis and untouched on the other. Only after the second pass does it equal the 2D convolution. Stopping early is not a cheaper blur, it is a different and wrong operation.

That wrong operation has a recognizable look, which is useful for catching the bug. A rows-only pass smears every pixel horizontally, so a vertical edge softens but a horizontal edge stays razor sharp — a motion-blur streak, not a symmetric Gaussian. If your "blur" looks directional, you did one pass. The symmetry of a real Gaussian is the visual signature that both passes ran.

**Separability is the kernel being an outer product; the two-pass algorithm is that factoring made mechanical, and its correctness depends entirely on completing both factors.**

## Worked example

The fixture is a 1D Gaussian kernel and a small image — the kernel is the thing that gets squared into 2D or applied twice, so it is what the fixture pins down.

```json filename=modules/generative-media/code/media-inter-10/image.json:7-14 COMPLETE
  "kernel1d": [
    1,
    4,
    6,
    4,
    1
  ],
  "norm": 16,
```

The 1D kernel [1, 4, 6, 4, 1] is the fifth row of Pascal's triangle — a binomial approximation to a Gaussian — and it normalizes by its sum, 16. The 2D kernel that the full blur uses is this vector's outer product with itself.

```python filename=modules/generative-media/code/media-inter-10/separable.py:39-41 COMPLETE
def outer(k):
    """The 2D kernel as the outer product of the 1D kernel with itself -- this is what 'separable' means."""
    return [[a * b for b in k] for a in k]
```

```text filename=modules/generative-media/code/media-inter-10/separable.py --kernel
  1D: [1, 4, 6, 4, 1]  (normalize by 16)
  5x5 outer product (normalize by 256):
     1  4  6  4  1
     4 16 24 16  4
     6 24 36 24  6
     4 16 24 16  4
     1  4  6  4  1
```

Every entry of that 5×5 is the product of two 1D entries — the center 36 is 6×6, the corner 1 is 1×1 — which is exactly what "separable" means, made visible. The full blur convolves the image with all 25 of these taps.

<svg role="img" aria-label="A column vector times a row vector equals the 5x5 kernel: the outer product decomposition of the separable Gaussian" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">5×5 kernel = column ⊗ row</text>
  <g font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">
    <text x="24" y="55">1</text><text x="24" y="75">4</text><text x="24" y="95">6</text><text x="24" y="115">4</text><text x="24" y="135">1</text>
  </g>
  <rect x="16" y="42" width="20" height="100" fill="none" stroke="var(--acc-line)"/>
  <text x="46" y="95" font-family="var(--mono)" font-size="12" fill="var(--ink)">×</text>
  <g font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">
    <text x="66" y="35">1</text><text x="86" y="35">4</text><text x="106" y="35">6</text><text x="126" y="35">4</text><text x="146" y="35">1</text>
  </g>
  <rect x="58" y="24" width="100" height="18" fill="none" stroke="var(--acc-line)"/>
  <text x="170" y="95" font-family="var(--mono)" font-size="12" fill="var(--ink)">=</text>
  <g font-family="var(--mono)" font-size="10" fill="var(--ink)">
    <text x="196" y="45">1</text><text x="216" y="45">4</text><text x="236" y="45">6</text><text x="256" y="45">4</text><text x="276" y="45">1</text>
    <text x="196" y="65">4</text><text x="214" y="65">16</text><text x="234" y="65">24</text><text x="254" y="65">16</text><text x="276" y="65">4</text>
    <text x="196" y="85">6</text><text x="214" y="85">24</text><text x="234" y="85">36</text><text x="254" y="85">24</text><text x="276" y="85">6</text>
    <text x="196" y="105">4</text><text x="214" y="105">16</text><text x="234" y="105">24</text><text x="254" y="105">16</text><text x="276" y="105">4</text>
    <text x="196" y="125">1</text><text x="216" y="125">4</text><text x="236" y="125">6</text><text x="256" y="125">4</text><text x="276" y="125">1</text>
  </g>
  <rect x="188" y="32" width="108" height="102" fill="none" stroke="var(--line)"/>
  <text x="150" y="158" font-family="var(--mono)" font-size="10" fill="var(--muted)">25 taps stored as two 5-tap vectors</text>
</svg>
^ The 5×5 kernel is literally a column times a row, so applying it is applying the column then the row — 25 taps become 5 + 5.

The full 2D blur runs the double loop over all k² taps.

```python filename=modules/generative-media/code/media-inter-10/separable.py:53-69 COMPLETE
def blur_2d(img, k):
    """Full 2D convolution with the k-by-k kernel: k*k taps per pixel. Returns (image, taps_per_pixel)."""
    k2 = outer(k)
    n = len(k)
    off = n // 2
    total_norm = sum(k) ** 2
    out = []
    for r in range(len(img)):
        row = []
        for c in range(len(img[0])):
            acc = 0
            for i in range(n):
                for j in range(n):
                    acc += k2[i][j] * clamp_get(img, r + i - off, c + j - off)
            row.append(round(acc / total_norm))
        out.append(row)
    return out, n * n
```

The separable version does two single loops with an intermediate image between them — rows first, then columns of the result.

```python filename=modules/generative-media/code/media-inter-10/separable.py:72-93 COMPLETE
def blur_separable(img, k):
    """Two 1D passes: rows then columns. 2*k taps per pixel, identical result. Returns (image, taps)."""
    n = len(k)
    off = n // 2
    norm = sum(k)
    # pass 1: convolve each row with the 1D kernel (keep integer, divide by norm)
    tmp = []
    for r in range(len(img)):
        row = []
        for c in range(len(img[0])):
            acc = sum(k[j] * clamp_get(img, r, c + j - off) for j in range(n))
            row.append(acc / norm)
        tmp.append(row)
    # pass 2: convolve each column of the intermediate with the same 1D kernel
    out = []
    for r in range(len(img)):
        row = []
        for c in range(len(img[0])):
            acc = sum(k[i] * (tmp[r + i - off][c] if 0 <= r + i - off < len(img) else 0) for i in range(n))
            row.append(round(acc / norm))
        out.append(row)
    return out, 2 * n
```

Run all three and compare.

```text filename=modules/generative-media/code/media-inter-10/separable.py --blur
  full 2D blur (25 taps/pixel):
      5  10  21  28  20   8
     10  18  32  41  31  14
     21  32  45  52  43  24
     28  41  52  59  50  31
     20  31  43  50  41  24
      8  14  24  31  24  11
  separable two-pass (10 taps/pixel):
      5  10  21  28  20   8
     10  18  32  41  31  14
     21  32  45  52  43  24
     28  41  52  59  50  31
     20  31  43  50  41  24
      8  14  24  31  24  11
  rows-only, the bug (5 taps/pixel):
      7  14  30  40  29  12
      7  14  30  40  29  12
      7  14  30  40  29  12
     62  84  90  90  84  62
      7  14  30  40  29  12
      7  14  30  40  29  12
```

The first two grids are identical, digit for digit — the separable two-pass blur is not an approximation of the 2D blur, it is the same number in every cell, at 10 taps instead of 25. The third grid is the bug, and its signature is unmistakable: five of the six rows are identical to each other. The rows-only pass smeared each row horizontally but never mixed across rows, so the vertical structure is completely untouched — the bright horizontal bar at row 3 stays a hard edge while the vertical bar has softened. That is a horizontal motion blur wearing a blur's name.

<svg role="img" aria-label="Two blurs compared as heat rows: the separable two-pass matches the 2D blur, while rows-only leaves the vertical structure unblurred as identical rows" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">two-pass = 2D (symmetric)</text>
  <g stroke="var(--line)">
    <rect x="20" y="34" width="18" height="18" fill="var(--panel)"/><rect x="38" y="34" width="18" height="18" fill="var(--acc-soft)"/><rect x="56" y="34" width="18" height="18" fill="var(--acc-line)"/><rect x="74" y="34" width="18" height="18" fill="var(--acc-soft)"/><rect x="92" y="34" width="18" height="18" fill="var(--panel)"/>
    <rect x="20" y="52" width="18" height="18" fill="var(--acc-soft)"/><rect x="38" y="52" width="18" height="18" fill="var(--acc-line)"/><rect x="56" y="52" width="18" height="18" fill="var(--acc-ink)"/><rect x="74" y="52" width="18" height="18" fill="var(--acc-line)"/><rect x="92" y="52" width="18" height="18" fill="var(--acc-soft)"/>
    <rect x="20" y="70" width="18" height="18" fill="var(--acc-line)"/><rect x="38" y="70" width="18" height="18" fill="var(--acc-ink)"/><rect x="56" y="70" width="18" height="18" fill="var(--acc-ink)"/><rect x="74" y="70" width="18" height="18" fill="var(--acc-ink)"/><rect x="92" y="70" width="18" height="18" fill="var(--acc-line)"/>
    <rect x="20" y="88" width="18" height="18" fill="var(--acc-soft)"/><rect x="38" y="88" width="18" height="18" fill="var(--acc-line)"/><rect x="56" y="88" width="18" height="18" fill="var(--acc-ink)"/><rect x="74" y="88" width="18" height="18" fill="var(--acc-line)"/><rect x="92" y="88" width="18" height="18" fill="var(--acc-soft)"/>
    <rect x="20" y="106" width="18" height="18" fill="var(--panel)"/><rect x="38" y="106" width="18" height="18" fill="var(--acc-soft)"/><rect x="56" y="106" width="18" height="18" fill="var(--acc-line)"/><rect x="74" y="106" width="18" height="18" fill="var(--acc-soft)"/><rect x="92" y="106" width="18" height="18" fill="var(--panel)"/>
  </g>
  <text x="250" y="22" font-family="var(--mono)" font-size="11" fill="var(--s2)">rows-only (streaked)</text>
  <g stroke="var(--line)">
    <rect x="254" y="34" width="18" height="18" fill="var(--acc-soft)"/><rect x="272" y="34" width="18" height="18" fill="var(--acc-line)"/><rect x="290" y="34" width="18" height="18" fill="var(--acc-ink)"/><rect x="308" y="34" width="18" height="18" fill="var(--acc-line)"/><rect x="326" y="34" width="18" height="18" fill="var(--acc-soft)"/>
    <rect x="254" y="52" width="18" height="18" fill="var(--acc-soft)"/><rect x="272" y="52" width="18" height="18" fill="var(--acc-line)"/><rect x="290" y="52" width="18" height="18" fill="var(--acc-ink)"/><rect x="308" y="52" width="18" height="18" fill="var(--acc-line)"/><rect x="326" y="52" width="18" height="18" fill="var(--acc-soft)"/>
    <rect x="254" y="70" width="18" height="18" fill="var(--acc-soft)"/><rect x="272" y="70" width="18" height="18" fill="var(--acc-line)"/><rect x="290" y="70" width="18" height="18" fill="var(--acc-ink)"/><rect x="308" y="70" width="18" height="18" fill="var(--acc-line)"/><rect x="326" y="70" width="18" height="18" fill="var(--acc-soft)"/>
    <rect x="254" y="88" width="18" height="18" fill="var(--acc-soft)"/><rect x="272" y="88" width="18" height="18" fill="var(--acc-line)"/><rect x="290" y="88" width="18" height="18" fill="var(--acc-ink)"/><rect x="308" y="88" width="18" height="18" fill="var(--acc-line)"/><rect x="326" y="88" width="18" height="18" fill="var(--acc-soft)"/>
    <rect x="254" y="106" width="18" height="18" fill="var(--acc-soft)"/><rect x="272" y="106" width="18" height="18" fill="var(--acc-line)"/><rect x="290" y="106" width="18" height="18" fill="var(--acc-ink)"/><rect x="308" y="106" width="18" height="18" fill="var(--acc-line)"/><rect x="326" y="106" width="18" height="18" fill="var(--acc-soft)"/>
  </g>
  <text x="20" y="146" font-family="var(--mono)" font-size="10" fill="var(--muted)">symmetric halo</text>
  <text x="254" y="146" font-family="var(--mono)" font-size="10" fill="var(--muted)">identical rows = no vertical blur</text>
</svg>
^ The two-pass result spreads symmetrically like a real Gaussian; the rows-only result has identical rows — a dead giveaway that the vertical pass never ran.

## Build

Reproduce the three grids and the tap counts. Pure standard library, integer arithmetic held until the final divide, so the two-pass output equals the 2D output exactly — not within rounding, exactly.

Run `--kernel` for the outer product, `--blur` for the three grids, `--check` for the gate. The self-test checks the two claims that make separability worth using — identical output and lower cost — plus the two that keep you honest: that the saving is exactly k/2, and that skipping a pass is wrong.

```python filename=modules/generative-media/code/media-inter-10/separable.py:154-160 COMPLETE
    separable_matches = bs == b2
    print("  separable two-pass equals the full 2D blur pixel for pixel = %s" % separable_matches)

    separable_cheaper = taps_sep < taps_2d
    print("  the separable pass costs fewer taps per pixel = %s (%d vs %d)" % (separable_cheaper, taps_sep, taps_2d))

    savings_is_ratio = taps_2d / taps_sep == len(k) / 2
    print("  the saving is the k/2 factor separability predicts = %s (%.1fx, k=%d)"
          % (savings_is_ratio, taps_2d / taps_sep, len(k)))
```

The `separable_matches = bs == b2` is a full-image equality, not a tolerance check — every one of the 36 pixels must agree. That is only defensible because the code keeps integers until the final division; had it divided and rounded mid-pass, floating-point drift would force a tolerance and the "identical" claim would soften to "close." Exact equality is the strong form of the claim, and the integer discipline is what earns it. Here is the full gate.

```text filename=modules/generative-media/code/media-inter-10/separable.py --check
SELF-TEST — two 1D passes equal the full 2D blur exactly and cost less; one pass does not match
------------------------------------------------------------------------------------------
  separable two-pass equals the full 2D blur pixel for pixel = True
  the separable pass costs fewer taps per pixel = True (10 vs 25)
  the saving is the k/2 factor separability predicts = True (2.5x, k=5)
  rows-only does NOT match the 2D blur = True (skipping a pass is not separability)
------------------------------------------------------------------------------------------
SELF-TEST PASS  separable_matches=True  separable_cheaper=True  savings_is_ratio=True  one_pass_wrong=True
```

Four True flags. Separable_matches: the two-pass output is the 2D output, exactly. Separable_cheaper: 10 taps beat 25. Savings_is_ratio: the speedup is 2.5× = k/2, on the nose. One_pass_wrong: the rows-only blur is a different image, so the second pass is not optional. The last flag is the guardrail — it stops anyone reading "separable is cheaper" as "one pass is enough."

**The self-test asserts pixel-exact equality, not closeness — a claim the code can only make because it stays in integers until the last divide.**

## Definition of done

You are done when you reproduce the grids and can explain both the win and the trap.

Concretely: `--blur` shows the two-pass grid identical to the 2D grid and the rows-only grid streaked; `--check` prints PASS with the 2.5× saving. You can define a separable kernel as an outer product and explain why that structure lets the double sum factor into two single sums. You can compute the cost ratio k²/2k = k/2 for any kernel width and say why the win grows with width. And you can describe the visual signature of the one-pass bug — a directional smear, identical rows or columns — so you would catch it by eye.

The habit to carry: whenever you apply a blur or a large linear filter, ask whether the kernel is separable, and if it is, never run the 2D form. And whenever a "blur" looks directional, suspect a missing second pass before you suspect anything else.

## Boss fight

The instructive failure is a shader that ships at 30 frames per second when it could ship at 60, and no one questions it because the picture looks right.

An engineer writes a Gaussian blur as a single 2D pass with a 9×9 kernel — 81 texture samples per pixel. It works, the blur looks correct, and it costs what it costs. The separable version is two passes of 9 samples each, 18 total, a 4.5× reduction in sampling, and it produces the identical image. On a full-screen bloom effect at 4K that is the difference between fitting in the frame budget and not. The 2D version is not wrong; it is just paying k²/2k times too much for the same result, forever, on every frame. This is the most expensive kind of "working" code — correct output, quietly wasteful, and invisible until someone profiles it.

Your turn, two moves. First, confirm the scaling law. Change the kernel to a 1D vector of length 7 (say [1, 6, 15, 20, 15, 6, 1], the seventh Pascal row) and predict before running: the 2D cost jumps to 49 taps, the separable to 14, and the ratio becomes 3.5× = k/2. Check that `savings_is_ratio` still passes. Second, break the equality on purpose and watch the self-test catch it. Make the two passes use different kernels — blur rows with [1,4,6,4,1] and columns with [1,2,1] — and predict: the result is a valid separable blur, but of a non-symmetric kernel that is no longer the outer product of one vector with itself, so it will not match `blur_2d`'s symmetric kernel and `separable_matches` will fail. That failure is the definition of separability enforced: the two-pass trick reproduces the 2D blur only when the 2D kernel actually is the outer product of the 1D kernel you are applying twice.

## External resources

The separable-convolution optimization is standard in every image-processing reference; Szeliski's "Computer Vision: Algorithms and Applications" derives the k² → 2k cost and the outer-product condition in its filtering chapter.

For the GPU version — why separable blur is the default for real-time bloom and depth-of-field — the classic write-ups on two-pass Gaussian blur in the GPU Gems series walk through the exact row-then-column shader passes this module counts by hand.

For the linear-algebra root, a separable kernel is a rank-1 matrix, and any rank-1 matrix is an outer product of two vectors; the singular value decomposition of a kernel tells you whether it is separable (one nonzero singular value) and, if not, how to approximate it by a sum of a few separable passes.
