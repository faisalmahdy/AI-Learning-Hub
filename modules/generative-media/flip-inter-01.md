---
id: flip-inter-01
title: Flip the kernel before you slide it — or your convolution is a correlation and mirrors every asymmetric kernel
topic: generative-media
level: intermediate
status: ready
time: 18 min
summary: The operation almost everyone calls "convolution" is arithmetically a correlation — line the kernel up as written and take the weighted sum. True convolution flips (reverses) the kernel first. For a symmetric kernel the flip changes nothing, so the two agree and no one notices; for an asymmetric kernel they disagree by producing a mirrored result. On an impulse at index 2 with the kernel [1, 0, 0] (weight the left neighbor), correlation moves the impulse to index 3 (right) and convolution moves it to index 1 (left) — same signal, same kernel, opposite directions. The symmetric blur [1, 2, 1] gives byte-identical output either way. Convolution is exactly correlation with the reversed kernel.
eli5: Imagine a stamp with a picture on it. If you press the stamp down exactly as it looks, that is one operation. Real convolution flips the stamp over first, like pressing it backwards, so the picture comes out mirrored. If the stamp's picture is symmetric — the same forwards and backwards — you cannot tell the difference. But if it is lopsided, flipping it sends everything the other way.
---

## Why this module

The thing your framework calls "convolution" flips the kernel; the thing your CNN calls "convolution" does not — and for an asymmetric kernel those are different operations that produce mirror images of each other.

Sliding a kernel over a signal and taking a weighted sum at each position is *correlation*: the kernel is used exactly as written. Mathematical *convolution* is the same slide with one extra step — reverse the kernel first. The two coincide whenever the kernel is symmetric, because a symmetric kernel is its own reverse, and most of the kernels you meet early (box blur, Gaussian, the [1, 2, 1] smooth) are symmetric. So the distinction stays invisible until the day you use an asymmetric kernel — a directional edge, a shift, an emboss — and your output comes out mirrored, features leaning the wrong way, edges signed backward, and nothing in the code looks wrong.

**Convolution and correlation are the same slide-and-sum; the only difference is whether the kernel is reversed first, and that difference is invisible for symmetric kernels and a mirror image for asymmetric ones.**

The crisp case is an impulse. Put a single 1 at index 2 and a kernel that weights the left neighbor. Correlation reads the left neighbor and pushes the impulse right; convolution flips the kernel, reads the right neighbor, and pushes it left. This module runs both, watches the impulse land two cells apart, and confirms that convolution is exactly correlation with the kernel reversed.

## Concepts

**Correlation** computes `out[i] = sum_d signal[i+d] * kernel[d]`, the kernel applied in its written order. This is what a convolutional layer actually does.

**Convolution** computes `out[i] = sum_d signal[i-d] * kernel[d]`. The sign on `d` flips, which is identical to reversing the kernel and then correlating. This is what `scipy.signal.convolve`, signal-processing textbooks, and the convolution theorem mean.

A **symmetric kernel** equals its own reverse, so the flip is a no-op and correlation equals convolution. A blur, a Gaussian, any palindromic kernel — the two operations are byte-identical, which is why the difference goes unnoticed for so long.

An **asymmetric kernel** differs from its reverse, so correlation and convolution give mirrored results. A kernel that weights the left neighbor, under the flip, weights the right one — the response is reflected.

**The flip is the whole definition: convolution is correlation with the kernel reversed, so anything you call convolution on an asymmetric kernel had better have flipped, or it is silently doing the mirror-image operation.**

<svg role="img" aria-label="Correlation applies the kernel as written; convolution reverses it first; for a symmetric kernel the reversed kernel is the same" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="14" fill="var(--muted)" font-size="8">the only difference is the reversal</text>
  <text x="10" y="34" fill="var(--s1)" font-size="8">correlation: use kernel as written</text>
  <rect x="30" y="40" width="20" height="16" fill="var(--s1)"/><rect x="50" y="40" width="20" height="16" fill="var(--grid)"/><rect x="70" y="40" width="20" height="16" fill="var(--grid)"/>
  <text x="95" y="52" fill="var(--muted)" font-size="8">[1, 0, 0]</text>
  <text x="10" y="80" fill="var(--s2)" font-size="8">convolution: reverse, then use</text>
  <rect x="30" y="86" width="20" height="16" fill="var(--grid)"/><rect x="50" y="86" width="20" height="16" fill="var(--grid)"/><rect x="70" y="86" width="20" height="16" fill="var(--s2)"/>
  <text x="95" y="98" fill="var(--muted)" font-size="8">[0, 0, 1]</text>
  <text x="170" y="52" fill="var(--muted)" font-size="8">weight moved from</text>
  <text x="170" y="98" fill="var(--muted)" font-size="8">left end to right end</text>
</svg>
^ Correlation weights the first cell; convolution reverses the kernel so the weight lands on the last cell — a symmetric kernel would look the same in both rows.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/flip-inter-01/conv1d.py

The fixture is an impulse and two kernels: one asymmetric, one symmetric.

```json filename=modules/generative-media/code/flip-inter-01/signal.json:1-14 COMPLETE
{
  "_meta": "A 1D signal and two kernels, to compare correlation with true convolution. A kernel is 3 weights at offsets [-1, 0, +1] around each output position. Correlation slides the kernel as written: out[i] = sum_d signal[i+d]*kernel[d]. Convolution FLIPS the kernel first: out[i] = sum_d signal[i-d]*kernel[d], which equals correlation with the reversed kernel. asym is an asymmetric kernel (weight on the left neighbor only) so flipping changes the result; sym is a symmetric blur so flipping is a no-op. Out-of-range signal samples are 0 (zero padding).",
  "signal": [0, 0, 1, 0, 0],
  "kernels": {
    "asym": [1, 0, 0],
    "sym": [1, 2, 1]
  }
}
```

Samples outside the array read as zero, so the output keeps the input's length.

```python filename=modules/generative-media/code/flip-inter-01/conv1d.py:39-41 COMPLETE
def at(signal, i):
    """Signal sample with zero padding outside the array."""
    return signal[i] if 0 <= i < len(signal) else 0
```

Correlation slides the kernel as written; convolution reverses it first and then does the identical slide.

```python filename=modules/generative-media/code/flip-inter-01/conv1d.py:44-52 COMPLETE
def correlate(signal, kernel):
    """Slide the kernel as written: out[i] = sum_d signal[i+d]*kernel[d], center offset d in {-1,0,+1}."""
    r = len(kernel) // 2
    return [sum(at(signal, i + d) * kernel[d + r] for d in range(-r, r + 1)) for i in range(len(signal))]


def convolve(signal, kernel):
    """True convolution: flip the kernel first, then correlate."""
    return correlate(signal, list(reversed(kernel)))
```

Run `--compare` to see both operations on both kernels.

```text filename=--compare
COMPARE — correlation vs convolution (signal [0, 0, 1, 0, 0])
--------------------------------------------------------------
  kernel asym [1, 0, 0]   flipped [0, 0, 1]
    correlation:  [0, 0, 0, 1, 0]
    convolution:  [0, 1, 0, 0, 0]   (MIRRORED — differ)
  kernel sym  [1, 2, 1]   flipped [1, 2, 1]
    correlation:  [0, 1, 2, 1, 0]
    convolution:  [0, 1, 2, 1, 0]   (identical)
--------------------------------------------------------------
  the asymmetric kernel disagrees; the symmetric kernel is a no-op under the flip.
```

The asymmetric kernel `[1, 0, 0]` reverses to `[0, 0, 1]`, and the two outputs are mirror images: correlation puts the impulse at index 3, convolution at index 1. The symmetric kernel `[1, 2, 1]` reverses to itself, so its two outputs are the same list. Symmetry is exactly the property that hides the flip.

<svg role="img" aria-label="For the asymmetric kernel the correlation and convolution outputs are mirror images; for the symmetric kernel they are identical" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">impulse output position (cell index)</text>
  <text x="8" y="34" fill="var(--muted)" font-size="8">asym</text>
  <rect x="60" y="26" width="18" height="12" fill="var(--grid)"/><rect x="78" y="26" width="18" height="12" fill="var(--grid)"/><rect x="96" y="26" width="18" height="12" fill="var(--grid)"/><rect x="114" y="26" width="18" height="12" fill="var(--s1)"/><rect x="132" y="26" width="18" height="12" fill="var(--grid)"/>
  <text x="155" y="35" fill="var(--s1)" font-size="8">correlation → index 3</text>
  <rect x="60" y="42" width="18" height="12" fill="var(--grid)"/><rect x="78" y="42" width="18" height="12" fill="var(--s2)"/><rect x="96" y="42" width="18" height="12" fill="var(--grid)"/><rect x="114" y="42" width="18" height="12" fill="var(--grid)"/><rect x="132" y="42" width="18" height="12" fill="var(--grid)"/>
  <text x="155" y="51" fill="var(--s2)" font-size="8">convolution → index 1</text>
  <text x="8" y="80" fill="var(--muted)" font-size="8">sym</text>
  <rect x="60" y="72" width="18" height="12" fill="var(--grid)"/><rect x="78" y="72" width="18" height="12" fill="var(--s1)"/><rect x="96" y="72" width="18" height="12" fill="var(--ink)"/><rect x="114" y="72" width="18" height="12" fill="var(--s1)"/><rect x="132" y="72" width="18" height="12" fill="var(--grid)"/>
  <text x="155" y="81" fill="var(--muted)" font-size="8">both → identical</text>
  <text x="60" y="104" fill="var(--muted)" font-size="8">the lit cell sits on opposite sides of center for the asymmetric kernel</text>
</svg>
^ The asymmetric kernel lights index 3 under correlation and index 1 under convolution — mirror images across the center — while the symmetric kernel produces the same row twice.

## Build

The direction is the tell. Run `--shift` to watch where the impulse lands.

```text filename=--shift
SHIFT — impulse at index 2, kernel [1, 0, 0] (weights the LEFT neighbor)
--------------------------------------------------------------
  correlation lands the impulse at index 3  -> moved RIGHT (+1)
  convolution lands the impulse at index 1  -> moved LEFT  (-1)
--------------------------------------------------------------
  same kernel, opposite directions: the flip reverses which neighbor is weighted.
```

The kernel `[1, 0, 0]` places its only weight on offset `-1`, the left neighbor. Correlation reads `signal[i-1]` into `out[i]`, so a feature at index 2 reappears at index 3 — it moves right. Convolution flips the kernel to `[0, 0, 1]`, reads `signal[i+1]`, and the feature moves to index 1 — left. This is why a directional edge kernel copied from a signal-processing reference will detect the opposite edge in a CNN, and vice versa: the two fields disagree on whether "convolution" includes the flip, so the same weights point opposite ways.

<svg role="img" aria-label="A kernel weighting the left neighbor moves the impulse right under correlation and left under convolution" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="14" fill="var(--muted)" font-size="8">kernel weights the LEFT neighbor</text>
  <circle cx="150" cy="46" r="9" fill="var(--ink)"/><text x="140" y="70" fill="var(--muted)" font-size="8">impulse @2</text>
  <line x1="150" y1="46" x2="205" y2="46" stroke="var(--s1)" stroke-width="2"/><text x="210" y="49" fill="var(--s1)" font-size="8">→ correlation (+1, right)</text>
  <circle cx="205" cy="46" r="5" fill="var(--s1)"/>
  <line x1="150" y1="46" x2="95" y2="46" stroke="var(--s2)" stroke-width="2"/><text x="12" y="49" fill="var(--s2)" font-size="8">convolution (−1)</text>
  <circle cx="95" cy="46" r="5" fill="var(--s2)"/>
  <text x="60" y="90" fill="var(--muted)" font-size="8">one kernel, two operations, opposite directions — the flip is the only difference</text>
</svg>
^ The same left-weighting kernel drives the impulse right under correlation and left under convolution; the flip is what reverses the arrow.

## Definition of done

The self-test pins all five facts: the asymmetric kernel differs, the symmetric one is identical, convolution equals flipped correlation, the shifts are opposite, and flipping twice is the identity.

```python filename=modules/generative-media/code/flip-inter-01/conv1d.py:97-113 COMPLETE
    asymmetric_differs = correlate(sig, asym) != convolve(sig, asym)
    print("  the asymmetric kernel differs under the flip = %s (%s vs %s)" % (asymmetric_differs, correlate(sig, asym), convolve(sig, asym)))

    symmetric_identical = correlate(sig, sym) == convolve(sig, sym)
    print("  the symmetric kernel is identical either way = %s (%s)" % (symmetric_identical, convolve(sig, sym)))

    conv_is_flipped_corr = convolve(sig, asym) == correlate(sig, list(reversed(asym)))
    print("  convolution == correlation with the reversed kernel = %s" % conv_is_flipped_corr)

    src = peak(sig)
    corr_right = peak(correlate(sig, asym)) - src
    conv_left = peak(convolve(sig, asym)) - src
    opposite_directions = corr_right == -conv_left and corr_right != 0
    print("  correlation and convolution shift the impulse opposite ways = %s (%+d vs %+d)" % (opposite_directions, corr_right, conv_left))

    flip_is_involution = list(reversed(list(reversed(asym)))) == asym
    print("  flipping the kernel twice returns the original = %s" % flip_is_involution)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — asymmetric kernel comes out mirrored; symmetric is identical; conv == flipped corr
----------------------------------------------------------------------------------------------------
  the asymmetric kernel differs under the flip = True ([0, 0, 0, 1, 0] vs [0, 1, 0, 0, 0])
  the symmetric kernel is identical either way = True ([0, 1, 2, 1, 0])
  convolution == correlation with the reversed kernel = True
  correlation and convolution shift the impulse opposite ways = True (+1 vs -1)
  flipping the kernel twice returns the original = True
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  asymmetric_differs=True  symmetric_identical=True  conv_is_flipped_corr=True  opposite_directions=True  flip_is_involution=True
```

**Done means the flip is proven to matter exactly when the kernel is asymmetric: the [1, 0, 0] kernel yields [0, 0, 0, 1, 0] one way and [0, 1, 0, 0, 0] the other, while [1, 2, 1] yields [0, 1, 2, 1, 0] both ways.**

## Boss fight

The self-test used a symmetric blur that hid the flip. Predict which is safer to be careless about: a Gaussian blur or a directional edge kernel. It is tempting to conclude the flip never really matters because your blurs always looked fine.

Your blurs looked fine because they were symmetric, and symmetry is the one case where correlation and convolution agree. A Gaussian, a box, any palindromic kernel is its own reverse, so you can call the operation whatever you like and the pixels are identical — you got away with it, but not because the flip was harmless. The moment the kernel is directional — an asymmetric edge detector, a motion blur, an emboss, a learned CNN filter you then hand to a signal-processing tool — the flip decides which way the feature points, and getting it wrong mirrors the result. The rule: symmetric kernels forgive you, asymmetric kernels do not, and "it worked on my blur" is not evidence the flip is optional.

The subtler trap is mixing conventions across a boundary. A CNN's learned weights assume correlation (no flip); a Fourier-domain multiply implements true convolution (with flip); `scipy.signal.correlate` and `scipy.signal.convolve` differ by exactly the reversal. Move a kernel from one world to the other without accounting for the flip and every asymmetric feature reflects. When you port a kernel, either keep it in one convention end to end or reverse it once at the boundary — and test with an asymmetric kernel, because a symmetric one will pass no matter which mistake you made.

```python filename=modules/generative-media/code/flip-inter-01/conv1d.py:50-52 COMPLETE
def convolve(signal, kernel):
    """True convolution: flip the kernel first, then correlate."""
    return correlate(signal, list(reversed(kernel)))
```

**Convolution is correlation with the kernel reversed, so the flip is invisible for symmetric kernels and a mirror image for asymmetric ones — pick one convention, reverse once at any boundary between them, and always test with an asymmetric kernel because a symmetric one hides the mistake.**

## External resources

The `scipy.signal.convolve` versus `scipy.signal.correlate` documentation — the two functions differ by exactly the kernel flip, and reading their definitions side by side makes the distinction concrete.

Any deep-learning text's note that "convolutional layers actually compute cross-correlation" (for example the *Dive into Deep Learning* chapter on convolutions) — the standard admission that the CNN "convolution" omits the flip, and why it does not matter when the kernel is learned.

The companion "combine both gradient directions" and "weight neighbors by intensity too" modules — both build directional and asymmetric kernels, exactly the case where whether you flipped decides the result.
