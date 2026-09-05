---
id: gamma-inter-01
title: Gamma-encode before quantizing — linear codes waste the brights and band the shadows
topic: generative-media
level: intermediate
status: ready
time: 21 min
summary: The eye is far more sensitive to changes in dark tones than bright ones, so a limited set of codes must be spaced by perceived lightness, not physical intensity. Linear coding leaves a huge perceptual gap in the darkest step (banding) and wastes finely-spaced codes on the brights. With 8 codes, linear's darkest step is a 0.413 perceptual jump; gamma coding makes every step a uniform 0.143.
eli5: Your eyes notice a small change in a dim room much more than the same change in bright sunlight. So if you only have a few brightness levels to work with, you should put most of them in the dark range where eyes are picky, not spread them evenly. Gamma encoding does exactly that; spacing them evenly (linear) leaves ugly jumps in the shadows.
---

## Why this module

Every image file you have ever opened is gamma-encoded, and the reason is that spacing brightness codes evenly would put them in all the wrong places.

The eye's response to light is non-linear. A change from very dark to slightly-less-dark is glaringly obvious; the same physical change from bright to slightly-brighter is nearly invisible. Perceived lightness is roughly physical intensity raised to the power 1/gamma, with gamma around 2.2 — a curve that is steep in the darks (small intensity changes are big perceptual changes) and shallow in the brights. This is not a display quirk; it is how human vision works, and any system that stores brightness in a limited number of codes has to reckon with it.

Here is the consequence. You have a fixed budget of codes — 256 for an 8-bit channel — to represent the whole brightness range. If you space those codes evenly in physical intensity (linear coding), you have spaced them evenly in the wrong space: the brights, where the eye can barely tell adjacent codes apart, get lots of finely-spaced codes that are wasted, while the darks, where the eye is acute, get coarsely-spaced codes with large perceptual gaps between them. Those gaps are visible banding — the ugly stepped contours you see in a smooth dark gradient stored with too few bits.

Gamma coding fixes it by spacing the codes evenly in perceived lightness instead. You store intensity raised to 1/gamma, so equal steps in the stored value are equal steps in perception, and the codes cluster into the darks where they are needed. Now every step looks the same size, there is no banding, and none of the budget is wasted on brights the eye cannot resolve. The display applies the inverse gamma to recover physical intensity when it shows the image. This is why image formats and cameras gamma-encode: it is perceptual compression, spending the bit budget where perception lives.

We will spread 8 codes across the range both ways. Linear coding's darkest step is a 0.413 jump in perceived lightness — a glaring band — while its brightest step is a wasted 0.068. Gamma coding's steps are a uniform 0.143 everywhere. Same 8 codes; gamma spends them where the eye is.

**The eye is non-linear, so a limited code budget must be spaced by perceived lightness; linear coding bands the shadows and wastes codes on the brights, while gamma coding spaces the codes evenly in perception.**

## Concepts

The core relationship is perceived lightness ≈ intensity^(1/gamma). Because 1/gamma is less than one, this curve rises steeply from zero — a small increase in intensity near black produces a large increase in perceived lightness — and flattens near white. So equal intervals of physical intensity map to unequal intervals of perceived lightness: the interval nearest black spans a large perceptual range, and each successive interval spans less. That non-uniformity is the whole story: any coding that is uniform in intensity is wildly non-uniform in what the eye sees.

Linear coding makes exactly that mistake. Its codes are at intensities 0, 1/(n−1), 2/(n−1), and so on — evenly spaced in intensity. Run them through the perception curve and the perceptual gaps between adjacent codes come out large at the dark end and small at the bright end. The darkest gap is the banding you see; the bright gaps are so small the eye cannot distinguish those codes, so they are wasted precision. Linear coding both bands and wastes, and it does both worst exactly where it matters — the darks are where banding is visible and the brights are where extra codes are pointless.

Gamma coding inverts the spacing to match. Its codes are at intensities (i/(n−1))^gamma — bunched toward zero, sparse toward one — which is precisely the distribution that comes out uniform after the perception curve. Store intensity^(1/gamma) and quantize that uniformly, and every code is one equal perceptual step from the next. The math is a clean cancellation: encoding raises to 1/gamma, perception raises to 1/gamma of the decoded value, and the uniform stored steps become uniform perceived steps. The codes end up dense in the darks, which is where the eye's acuity demanded them.

<svg role="img" aria-label="The perception curve: perceived lightness rises steeply from black and flattens toward white, so equal intensity intervals map to unequal perceptual intervals" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">perceived lightness = intensity^(1/gamma), gamma 2.2</text>
  <line x1="60" y1="160" x2="440" y2="160" stroke="var(--line)"/>
  <line x1="60" y1="160" x2="60" y2="40" stroke="var(--line)"/>
  <text x="60" y="178" font-family="var(--mono)" font-size="8" fill="var(--muted)">0</text>
  <text x="430" y="178" font-family="var(--mono)" font-size="8" fill="var(--muted)">intensity 1</text>
  <text x="20" y="44" font-family="var(--mono)" font-size="8" fill="var(--muted)">L 1</text>
  <path d="M60,160 L98,102 L136,82 L174,68 L212,58 L250,49 L288,42 L326,36 L364,31 L402,26 L440,22" fill="none" stroke="var(--s1)" stroke-width="2"/>
  <line x1="60" y1="160" x2="98" y2="160" stroke="var(--s2)" stroke-width="3"/>
  <line x1="60" y1="160" x2="60" y2="102" stroke="var(--s2)" stroke-width="3"/>
  <text x="104" y="150" font-family="var(--mono)" font-size="8" fill="var(--s2)">one dark intensity step → tall perceptual jump</text>
  <line x1="402" y1="160" x2="440" y2="160" stroke="var(--acc-line)" stroke-width="3"/>
  <line x1="440" y1="26" x2="440" y2="22" stroke="var(--acc-line)" stroke-width="3"/>
  <text x="250" y="150" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">same step in brights → tiny jump</text>
</svg>
^ The curve is steep near black and flat near white, so an equal step in intensity spans a large perceptual range in the darks and a tiny one in the brights — the source of both the banding and the waste.

This is perceptual bit allocation, and it is why gamma is not an annoyance to "correct away" but a feature to preserve. Linear light is the right space for *computing* on pixels — blending, filtering, lighting — which is why you decode to linear before those operations (a separate lesson), but it is the wrong space for *storing* pixels in limited bits, because storage should be perceptually uniform. Modern variants (the sRGB transfer function, or perceptual-quantizer curves for HDR) refine the exact shape, but all encode roughly this same insight: put the codes where the eye can see the difference.

**Perception raises intensity to 1/gamma, so uniform-in-intensity codes are non-uniform in perception; gamma coding pre-distorts the code spacing by the inverse curve so the perceived steps come out equal, dense in the darks where the eye needs them.**

## Worked example

The fixture is a gamma and a small code budget.

```json filename=modules/generative-media/code/gamma-inter-01/coding.json:7-8 COMPLETE
  "gamma": 2.2,
  "n_codes": 8
```

Gamma 2.2, eight codes — small enough to see the effect starkly. Linear codes are evenly spaced in intensity; gamma codes are (i/7)^2.2, bunched toward zero.

```python filename=modules/generative-media/code/gamma-inter-01/gamma.py:44-46 COMPLETE
def linear_codes(n):
    """Codes spaced evenly in physical intensity."""
    return [i / (n - 1) for i in range(n)]
```

```python filename=modules/generative-media/code/gamma-inter-01/gamma.py:49-51 COMPLETE
def gamma_codes(n, gamma):
    """Codes spaced evenly in perceived lightness -- their intensities are lightness^gamma."""
    return [(i / (n - 1)) ** gamma for i in range(n)]
```

```text filename=modules/generative-media/code/gamma-inter-01/gamma.py --codes
CODES — intensity of each of the 8 codes (gamma 2.2)
------------------------------------------------------
  linear:  [0.0, 0.143, 0.286, 0.429, 0.571, 0.714, 0.857, 1.0]
  gamma:   [0.0, 0.014, 0.064, 0.155, 0.292, 0.477, 0.712, 1.0]
------------------------------------------------------
  gamma coding packs codes into the darks, where the eye is sensitive.
```

The linear codes step by a flat 0.143 in intensity. The gamma codes crowd the bottom — 0, 0.014, 0.064, 0.155 — four of the eight codes are below intensity 0.16, because that dark region needs the resolution. The perceptual step is the jump in perceived lightness between adjacent codes.

```python filename=modules/generative-media/code/gamma-inter-01/gamma.py:54-57 COMPLETE
def perceptual_steps(intensities, gamma):
    """The jump in perceived lightness between adjacent codes -- big jumps are visible banding."""
    L = [lightness(x, gamma) for x in intensities]
    return [L[i] - L[i - 1] for i in range(1, len(L))]
```

Predict: linear coding's perceptual steps should be large at the dark end (the flat intensity step spans a big perceptual range there) and shrink toward the brights. Gamma coding's should all be equal. Run it.

```text filename=modules/generative-media/code/gamma-inter-01/gamma.py --steps
STEPS — perceived-lightness jump between adjacent codes
----------------------------------------------------------
  linear:  [0.4129, 0.1529, 0.1145, 0.095, 0.0828, 0.0742, 0.0677]   max 0.413
  gamma:   [0.1429, 0.1429, 0.1429, 0.1429, 0.1429, 0.1429, 0.1429]   max 0.143
----------------------------------------------------------
  linear's biggest jump is the darkest step (banding); gamma's are equal.
```

Linear coding's darkest step is 0.4129 — the jump from black to the first code covers 41% of the entire perceptual range, in one step, which is severe banding. Its steps then shrink monotonically to 0.0677 at the bright end, where the eye cannot see the difference between adjacent codes, so those are wasted. Gamma coding's steps are all 0.1429 — every step the same perceptual size, which is 1/7, exactly the uniform spacing you would want from seven intervals. Same eight codes; linear puts a 0.41 chasm in the shadows and wastes precision in the highlights, while gamma spreads the perceptual load evenly.

<svg role="img" aria-label="Eight codes on the intensity axis: linear codes evenly spaced, gamma codes bunched toward the dark end" viewBox="0 0 460 150" width="460" height="150">
  <rect x="0" y="0" width="460" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">code positions on the intensity axis (0=black, 1=white)</text>
  <text x="20" y="52" font-family="var(--mono)" font-size="9" fill="var(--ink)">linear</text>
  <line x1="70" y1="48" x2="440" y2="48" stroke="var(--line)"/>
  <g fill="var(--s2)"><circle cx="70" cy="48" r="4"/><circle cx="123" cy="48" r="4"/><circle cx="176" cy="48" r="4"/><circle cx="229" cy="48" r="4"/><circle cx="282" cy="48" r="4"/><circle cx="335" cy="48" r="4"/><circle cx="388" cy="48" r="4"/><circle cx="440" cy="48" r="4"/></g>
  <text x="80" y="68" font-family="var(--mono)" font-size="8" fill="var(--s2)">evenly spaced → big perceptual gap here ↑ (dark)</text>
  <text x="20" y="102" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">gamma</text>
  <line x1="70" y1="98" x2="440" y2="98" stroke="var(--line)"/>
  <g fill="var(--acc-line)"><circle cx="70" cy="98" r="4"/><circle cx="75" cy="98" r="4"/><circle cx="94" cy="98" r="4"/><circle cx="127" cy="98" r="4"/><circle cx="178" cy="98" r="4"/><circle cx="246" cy="98" r="4"/><circle cx="333" cy="98" r="4"/><circle cx="440" cy="98" r="4"/></g>
  <text x="80" y="118" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">bunched into the darks → uniform perceptual steps</text>
</svg>
^ Linear codes sit at even intensities, leaving a wide perceptual gap in the darkest interval; gamma codes crowd toward black so every perceptual step is equal.

<svg role="img" aria-label="Bar chart of perceptual steps: linear coding starts with a tall darkest bar shrinking toward the brights, gamma coding is seven equal bars" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">perceptual step per interval (dark → bright)</text>
  <line x1="30" y1="160" x2="440" y2="160" stroke="var(--line)"/>
  <text x="34" y="40" font-family="var(--mono)" font-size="9" fill="var(--s2)">linear</text>
  <g fill="var(--s2)"><rect x="34" y="42" width="22" height="118"/><rect x="60" y="116" width="22" height="44"/><rect x="86" y="127" width="22" height="33"/><rect x="112" y="133" width="22" height="27"/><rect x="138" y="136" width="22" height="24"/><rect x="164" y="139" width="22" height="21"/><rect x="190" y="141" width="22" height="19"/></g>
  <text x="34" y="175" font-family="var(--mono)" font-size="8" fill="var(--s2)">0.413 → 0.068 (bands the darks)</text>
  <text x="250" y="40" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">gamma</text>
  <g fill="var(--acc-line)"><rect x="250" y="119" width="22" height="41"/><rect x="276" y="119" width="22" height="41"/><rect x="302" y="119" width="22" height="41"/><rect x="328" y="119" width="22" height="41"/><rect x="354" y="119" width="22" height="41"/><rect x="380" y="119" width="22" height="41"/><rect x="406" y="119" width="22" height="41"/></g>
  <text x="250" y="175" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">0.143 everywhere (no band)</text>
</svg>
^ Linear coding's steps tower in the darkest interval and dwindle toward the brights; gamma coding's seven steps are all one height, spreading the perceptual load evenly.

## Build

Reproduce the steps. Pure standard library, deterministic, so the 0.413 dark banding step and the uniform 0.143 gamma steps come out exactly.

Run `--codes` for the positions, `--steps` for the perceptual jumps, `--check` for the gate. The self-test pins the whole story: linear bands (a large worst step), its worst step is the darkest, gamma's steps are uniform, and both use the same codes.

```python filename=modules/generative-media/code/gamma-inter-01/gamma.py:91-95 COMPLETE
    linear_bands = max(lin) > 2 * max(gam)
    print("  linear's worst perceptual step is far larger than gamma's = %s (%.3f vs %.3f)" % (linear_bands, max(lin), max(gam)))

    worst_is_darkest = lin.index(max(lin)) == 0
    print("  linear's worst step is the darkest one = %s (step %d of %d)" % (worst_is_darkest, lin.index(max(lin)) + 1, len(lin)))
```

The `worst_is_darkest` check is what makes this a lesson about the eye, not just about uneven steps. It confirms linear coding's largest perceptual gap is the very first step — the darkest one — which is exactly where the eye is most sensitive and banding is most visible. If the worst step were in the brights, the unevenness would be harmless, because the eye cannot see it there. That the failure lands in the shadows is what makes linear coding actually look bad, and the check pins it. Here is the full gate.

```text filename=modules/generative-media/code/gamma-inter-01/gamma.py --check
SELF-TEST — linear coding bands the darks with a large step; gamma coding's steps are uniform
----------------------------------------------------------------------------------------
  linear's worst perceptual step is far larger than gamma's = True (0.413 vs 0.143)
  linear's worst step is the darkest one = True (step 1 of 7)
  gamma's perceptual steps are all equal = True (0.143)
  both codings use the same 8 codes = True
----------------------------------------------------------------------------------------
SELF-TEST PASS  linear_bands=True  worst_is_darkest=True  gamma_uniform=True  same_codes=True
```

Four True flags. Linear_bands: linear's worst step is far larger than gamma's. Worst_is_darkest: and it is the darkest step, where the eye sees it. Gamma_uniform: gamma's steps are all equal, so no step bands. Same_codes: both use the same eight codes, so gamma's win is from spacing, not more codes. The worst-is-darkest flag is the one that connects the numbers to what you would actually see: a band in the shadows.

**The worst-is-darkest check ties the uneven steps to the eye — linear's biggest perceptual gap lands in the shadows, exactly where banding shows, which is what makes it look bad rather than merely uneven.**

## Definition of done

You are done when you reproduce the steps and can explain why the codes go where they do.

Concretely: `--steps` shows linear's darkest step at 0.413 shrinking to 0.068 and gamma's uniform at 0.143; `--check` prints PASS with four True flags. You can state the perception relationship (lightness ≈ intensity^(1/gamma)) and explain why uniform-in-intensity codes are non-uniform in perception, banding the darks and wasting the brights. You can explain how gamma coding pre-distorts the spacing so perceived steps come out equal, and why the codes end up dense in the darks. And you can state the storage-versus-compute distinction: gamma space for storing in limited bits, linear space for blending and filtering.

The habit to carry: store and quantize brightness in a perceptual (gamma or sRGB) space so the limited codes go where the eye can see the difference, and decode to linear only for math on pixels. When a smooth dark gradient shows banding, suspect too few bits or linear-space storage, not the source — and remember that adding bits helps far less than encoding perceptually.

## Boss fight

The instructive failure is an HDR-to-8-bit conversion that bands every shadow because someone stored linear light.

A rendering pipeline computes in linear light (correct for the physics) and then, to save the result as an 8-bit image, quantizes the linear values directly to 256 codes without gamma-encoding. The output looks fine in the highlights and bands horribly in the shadows — every dark gradient shows stepped contours — because 8 bits spaced evenly in linear intensity leave large perceptual gaps in the darks, exactly as this module shows at 8 codes. The team tries bumping to 10 or 12 bits, which helps but is wasteful, when the real fix is to gamma-encode before quantizing: the same 8 bits, spaced perceptually, band nothing. Storing linear light in low bit depth is the classic version of this bug, and it is why the standard is to encode to sRGB (a gamma-like curve) before writing an 8-bit file.

Your turn, two moves. First, see how bit depth trades against gamma. Bump n_codes to 16 with linear coding and predict: the darkest step roughly halves but is still the largest and still much bigger than gamma's uniform step at 16 codes — so doubling the codes helps linear but never fixes the shape; only perceptual spacing does. Compute how many linear codes you would need for the darkest step to match gamma's, and see it is far more than gamma needs. Second, check the round-trip. Gamma-encode a value (raise to 1/gamma), quantize, then decode (raise to gamma) and confirm the recovered intensity is close to the original for a dark value but that the *linear*-quantized version of the same dark value lands on a distant code — the concrete banding. That shows gamma encoding is a lossless-in-perception round trip for the bit budget, while linear encoding throws away shadow detail the eye would have seen.

## External resources

Charles Poynton's "Digital Video and HD" and his gamma FAQ are the canonical references on why gamma exists — perceptual coding of a limited signal — and carefully separate it from display non-linearity and from the linear space needed for image math.

The sRGB specification defines the exact transfer function (a gamma-like curve with a small linear segment near black) that image files use; reading it shows the production form of this module's simple intensity^(1/gamma).

For HDR, the SMPTE ST 2084 perceptual quantizer (PQ) curve is the modern high-dynamic-range version of the same idea — a transfer function shaped to human contrast sensitivity so a limited bit budget bands nowhere across a huge brightness range.
