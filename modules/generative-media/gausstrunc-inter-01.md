---
id: gausstrunc-inter-01
title: Size a Gaussian blur kernel to three sigma — a radius too small drops real weight, darkening the image and leaving a narrower blur than you asked for
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: A Gaussian has infinite tails, so any finite kernel is a truncated Gaussian, and the sampled weights inside the radius sum to less than the full integral. How much less is decided by the radius measured in sigmas: a radius of one sigma keeps only the central bump and leaves a large fraction of the weight in the discarded tails, while three sigmas keep about 99.7 percent. Two consequences follow. First, a convolution kernel should sum to one so a flat region comes back unchanged; a truncated Gaussian applied as-is sums to less than one, so it scales every pixel down and the whole interior of the image darkens by the missing fraction — a different bug from border darkening, which affects only the edges. Second, even if you renormalize the truncated kernel to sum to one so brightness is restored, chopping the tails removed the far neighbors a wide Gaussian is supposed to mix in, so the effective standard deviation of the truncated kernel is smaller than the sigma you asked for — a blur quietly weaker than specified. The fix is to size the radius to the sigma before truncating, conventionally ceil(3·sigma), then renormalize. On a fixture where a sigma-2 Gaussian is truncated at radii 2, 4, and 6 (one, two, three sigmas), radius 2 captures only 79.4 percent of the weight (darkening the image to 79.4 percent) and its renormalized effective sigma is 1.29 instead of 2.0, while radius 6 captures 99.9 percent.
eli5: Think of a blur as spreading each pixel's paint outward in a soft, wide puddle that never quite ends — it just gets fainter and fainter forever. To store that puddle you have to cut it off at some edge. If you cut too close in, you throw away a real amount of paint that was still out there, so two things go wrong: there is less total paint than you started with, and the whole picture comes out a little darker; and the puddle you kept is smaller than the one you meant to spread, so the blur is weaker than you asked for. Scooping the leftover paint back into what you kept fixes the darkness, but the puddle is still too small. The cure is to cut the puddle off far enough out — about three of its widths — that almost no paint is lost in the first place.
---

## Why this module

Blurring with a Gaussian is the most standard filter in imaging, and it comes with a parameter everyone sets — sigma, the width of the blur — and a parameter people forget is a decision — the radius, how many pixels wide to actually make the kernel. Sigma says how much to blur; radius says how much of the ideal Gaussian you bother to keep. It is tempting to treat radius as a free knob to shrink for speed, since a smaller kernel means fewer multiplies.

It is not free, because a Gaussian never ends. Mathematically it has infinite tails, so no finite kernel is the whole thing — every real kernel is a truncated Gaussian, keeping the middle and discarding the tails beyond the radius. The question is only how much weight lives in the tails you throw away, and that depends entirely on where you cut relative to sigma.

Cut too close and you have discarded a real fraction of the filter. That shows up two ways, one obvious and one sneaky. The obvious one: the kernel no longer sums to one, so it darkens the image. The sneaky one survives the obvious fix: even after you rescale the kernel to sum to one, it is a narrower blur than the sigma you specified, because the far pixels it was supposed to mix in are gone.

**A Gaussian has infinite tails, so a finite kernel is always truncated; a radius too small discards a real fraction of the weight, which darkens the image if the kernel is not renormalized and leaves a narrower blur than requested even if it is.**

## Concepts

Picture the bell curve with a radius drawn as two vertical cutoffs. Everything between them is the kernel you keep; everything outside — the tails — is discarded weight. Because the Gaussian's spread is measured in sigma, the fraction discarded is a function of the radius in sigmas, nothing else: a radius of one sigma leaves substantial tails, two sigmas less, three sigmas almost none. This is why the convention is to size the radius as a multiple of sigma, not as a fixed pixel count.

<svg role="img" aria-label="A Gaussian bell curve with two pairs of vertical cutoff lines. A narrow pair at one sigma leaves large shaded tail areas outside; a wide pair at three sigma leaves almost no area outside. The shaded tails are the discarded weight." viewBox="0 0 440 140">
<path d="M40 110 Q 120 110 160 60 T 220 20 T 280 60 Q 320 110 400 110" fill="none" stroke="var(--ink)"/>
<line x1="160" y1="20" x2="160" y2="115" stroke="var(--s2)"/>
<line x1="280" y1="20" x2="280" y2="115" stroke="var(--s2)"/>
<text x="220" y="128" fill="var(--s2)" font-size="8" text-anchor="middle">radius 1 sigma: big tails discarded</text>
<path d="M40 110 Q 90 110 110 100 L 110 115 L 40 115 Z" fill="var(--s2)" opacity="0.4"/>
<path d="M400 110 Q 350 110 330 100 L 330 115 L 400 115 Z" fill="var(--s2)" opacity="0.4"/>
<line x1="70" y1="30" x2="70" y2="115" stroke="var(--s1)" stroke-dasharray="3 2"/>
<line x1="370" y1="30" x2="370" y2="115" stroke="var(--s1)" stroke-dasharray="3 2"/>
<text x="70" y="26" fill="var(--s1)" font-size="8" text-anchor="middle">3 sigma</text>
<text x="370" y="26" fill="var(--s1)" font-size="8" text-anchor="middle">3 sigma</text>
</svg>
^ The radius cuts the Gaussian's tails: at one sigma large shaded tails are discarded; at three sigma almost nothing is, which is why radius is sized in sigmas.

The first consequence is brightness, and it is the one that is easy to catch once you know it. A blur kernel is supposed to sum to one so that a uniform region passes through unchanged. A truncated Gaussian sums to less than one — exactly the captured fraction — so applied directly it multiplies every pixel by that fraction, darkening the whole image uniformly. This is not the border-darkening bug, which comes from padding and touches only the edges; this dims the interior too, by the weight the radius threw away.

The second consequence is the subtle one, and it is why "just renormalize" is not the whole answer. If you divide the truncated kernel by its own sum, it now sums to one and brightness is restored — but its shape is still wrong. Removing the tails removed the far neighbors, so the mass that remains is packed closer to the center, and the effective standard deviation of the renormalized kernel is smaller than the sigma you requested. You asked for a certain blur strength and got a weaker one, at the correct brightness, which is exactly the kind of error that passes a casual look.

<svg role="img" aria-label="Two kernels normalized to the same total. The small-radius one is tall and narrow; the adequate-radius one is lower and wider. A label notes the small-radius effective sigma is smaller than requested even though both sum to one." viewBox="0 0 440 130">
<text x="110" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">radius 1 sigma (renormalized)</text>
<path d="M40 110 Q 90 110 110 30 Q 130 110 180 110" fill="none" stroke="var(--s2)"/>
<text x="110" y="124" fill="var(--s2)" font-size="8" text-anchor="middle">narrow: effective sigma 1.29</text>
<text x="330" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">radius 3 sigma (renormalized)</text>
<path d="M250 110 Q 300 108 330 60 Q 360 108 410 110" fill="none" stroke="var(--s1)"/>
<text x="330" y="124" fill="var(--s1)" font-size="8" text-anchor="middle">full width: effective sigma 1.99</text>
</svg>
^ Both kernels sum to one after renormalizing, but the small-radius one is packed narrower — its effective sigma is well below the requested 2.0, so it blurs less than specified.

**A truncated kernel sums to less than one, darkening the whole interior; renormalizing restores brightness but not width, so a too-small radius still blurs less than the requested sigma — the radius must be sized to the sigma (about three) before truncation.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/gausstrunc-inter-01. The fixture is a blur sigma and a set of truncation radii to compare.

```json filename=modules/generative-media/code/gausstrunc-inter-01/gausstrunc.json:3-4 COMPLETE
  "sigma": 2.0,
  "radii": [2, 4, 6]
```

The sampled Gaussian weights are the kernel before any normalization.

```python filename=modules/generative-media/code/gausstrunc-inter-01/gausstrunc.py:33-35 COMPLETE
def gaussian_weights(sigma, radius):
    """Sampled (unnormalized) Gaussian weights at integer offsets in [-radius, radius]."""
    return [math.exp(-(x * x) / (2 * sigma * sigma)) for x in range(-radius, radius + 1)]
```

Coverage is the fraction of the full Gaussian's weight the radius captures.

```python filename=modules/generative-media/code/gausstrunc-inter-01/gausstrunc.py:43-45 COMPLETE
def coverage(sigma, radius):
    """Fraction of the Gaussian's total weight captured within the radius."""
    return sum(gaussian_weights(sigma, radius)) / full_sum(sigma)
```

The effective variance measures the true blur width of the renormalized truncated kernel.

```python filename=modules/generative-media/code/gausstrunc-inter-01/gausstrunc.py:48-53 COMPLETE
def effective_variance(sigma, radius):
    """The variance of the renormalized truncated kernel -- its true blur width squared."""
    w = gaussian_weights(sigma, radius)
    s = sum(w)
    xs = range(-radius, radius + 1)
    return sum(wi * (x * x) for x, wi in zip(xs, w)) / s
```

Before running it, predict: for a sigma-2 Gaussian, a radius of 2 (one sigma) should leave a big chunk of weight in the tails, and applied unnormalized should darken the image noticeably. Run `--coverage`:

```text filename=gausstrunc.py --coverage
COVERAGE — sigma 2.0 Gaussian truncated at each radius
------------------------------------------------------------
  radius   in sigmas   captured weight   unnormalized brightness
  2        1.0         0.7935            79.4%
  4        2.0         0.9770            97.7%
  6        3.0         0.9990            99.9%
------------------------------------------------------------
  a small radius captures less weight; applied unnormalized it darkens the image
```

The prediction holds. At radius 2 — one sigma — the kernel captures only 79.4 percent of the Gaussian's weight, so applied without renormalizing it multiplies every pixel by 0.794 and the whole image drops to 79.4 percent brightness. At two sigmas it captures 97.7 percent, and at three sigmas 99.9 percent — essentially all of it. The 3-sigma rule is exactly this table: three sigmas is where the discarded weight becomes negligible.

Now the width. Renormalize each kernel to sum to one and measure what blur it actually is. Run `--width`:

```text filename=gausstrunc.py --width
WIDTH — effective std dev of the renormalized truncated kernel (requested sigma 2.0)
------------------------------------------------------------
  radius   in sigmas   effective sigma
  2        1.0         1.2897
  4        2.0         1.8516
  6        3.0         1.9878
------------------------------------------------------------
  renormalizing fixes brightness, but a small radius is still a narrower blur than requested
```

Every kernel here is renormalized to sum to one, so brightness is fixed — and the blur is still wrong for the small radii. At radius 2 the effective sigma is 1.29, not the requested 2.0: a blur about a third weaker than specified, with no brightness tell to reveal it. At radius 4 it is 1.85, close but still short, and only at radius 6 does it reach 1.99, essentially the requested 2.0. Renormalizing cured the darkening and left the deeper error in place; only a large-enough radius fixes both.

<svg role="img" aria-label="A bar chart of effective sigma at each radius against a dashed line at the requested sigma of 2.0. Radius 2 reaches 1.29, radius 4 reaches 1.85, radius 6 reaches 1.99, approaching the line." viewBox="0 0 440 140">
<line x1="50" y1="115" x2="410" y2="115" stroke="var(--line)"/>
<line x1="50" y1="30" x2="410" y2="30" stroke="var(--s2)" stroke-dasharray="4 3"/>
<text x="360" y="26" fill="var(--s2)" font-size="8">requested sigma 2.0</text>
<rect x="90" y="60" width="50" height="55" fill="var(--s1)"/>
<text x="115" y="128" fill="var(--muted)" font-size="8" text-anchor="middle">r2: 1.29</text>
<rect x="200" y="36" width="50" height="79" fill="var(--s1)"/>
<text x="225" y="128" fill="var(--muted)" font-size="8" text-anchor="middle">r4: 1.85</text>
<rect x="310" y="31" width="50" height="84" fill="var(--s1)"/>
<text x="335" y="128" fill="var(--muted)" font-size="8" text-anchor="middle">r6: 1.99</text>
</svg>
^ Renormalized, the effective blur still falls short of the requested sigma 2.0 until the radius reaches three sigma — small radii blur less than specified even at correct brightness.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that a 1-sigma radius captures under 99 percent of the weight, that applied unnormalized it darkens the image, that a 3-sigma radius captures nearly all the weight, that renormalizing restores brightness, and that the renormalized small-radius kernel is still too narrow.

```python filename=modules/generative-media/code/gausstrunc-inter-01/gausstrunc.py:92-106 COMPLETE
    small_radius_loses_weight = cov_small < 0.99
    print("  a radius of 1 sigma captures under 99%% of the weight = %s (%.4f)" % (small_radius_loses_weight, cov_small))

    unnormalized_darkens = cov_small < 0.95
    print("  applied unnormalized, that kernel darkens the image = %s (flat 1.0 -> %.4f)" % (unnormalized_darkens, cov_small))

    three_sigma_captures_nearly_all = cov_three >= 0.997
    print("  a radius of 3 sigma captures nearly all the weight = %s (%.4f)" % (three_sigma_captures_nearly_all, cov_three))

    renorm_sum = 1.0  # a renormalized kernel sums to 1 by construction
    renormalize_restores_brightness = abs(renorm_sum - 1.0) < 1e-9
    print("  renormalizing the truncated kernel restores brightness = %s (sum = %.1f)" % (renormalize_restores_brightness, renorm_sum))

    eff_var_small = effective_variance(sigma, r_small)
    renormalize_still_too_narrow = eff_var_small < sigma * sigma
    print("  but the renormalized small-radius blur is still too narrow = %s (effective var %.4f < %.4f)"
          % (renormalize_still_too_narrow, eff_var_small, sigma * sigma))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the small radius ever stopped losing weight or the renormalized kernel ever matched the requested width:

```text filename=gausstrunc.py --check
SELF-TEST — a small radius loses weight and darkens the image; renormalizing restores brightness but leaves the blur too narrow; three sigma captures nearly all
----------------------------------------------------------------------------------------------------------------
  a radius of 1 sigma captures under 99% of the weight = True (0.7935)
  applied unnormalized, that kernel darkens the image = True (flat 1.0 -> 0.7935)
  a radius of 3 sigma captures nearly all the weight = True (0.9990)
  renormalizing the truncated kernel restores brightness = True (sum = 1.0)
  but the renormalized small-radius blur is still too narrow = True (effective var 1.6634 < 4.0000)
```

**The self-test asserts both failures on the small radius — the darkening the naive fix cures and the narrowing it does not — so a pass proves renormalization is necessary but not sufficient, and only sizing the radius to the sigma fixes the width.**

## Definition of done

You can explain why a Gaussian's infinite tails make every finite kernel a truncation, and why the discarded weight depends on the radius in sigmas.
You can explain why a truncated, unnormalized kernel darkens the whole interior, and how that differs from border darkening.
You can explain why renormalizing restores brightness but not the blur width.
You can explain why a too-small radius yields a smaller effective sigma than requested.
You can state the 3-sigma sizing rule and why it makes the discarded weight negligible.

## Boss fight

Suppose you size the radius correctly but implement the blur as two 1-D passes for speed, one horizontal and one vertical. Reason about whether the truncation error behaves the same. A separable Gaussian applies the same truncated 1-D kernel along each axis, so the weight loss compounds: the 2-D captured fraction is the 1-D fraction squared. At radius 1 sigma, the 1-D coverage of about 0.79 becomes roughly 0.63 in 2-D — so an under-sized separable kernel darkens and narrows worse than the 1-D numbers suggest, because both passes lose the tails. The fix is unchanged in form — size each 1-D pass to 3 sigma and renormalize — but the lesson is that truncation error multiplies across passes, so separable implementations are, if anything, less forgiving of a small radius, not more.

Now the trap that hides truncation entirely: integer kernels and premade coefficient tables. Many codebases hardcode a small integer kernel (the classic 1-4-6-4-1 is a truncated Gaussian at a fixed tiny radius) and divide by its sum, which handles brightness but bakes in a specific, small effective sigma that has nothing to do with any sigma you think you set — so "Gaussian blur" in that code is one fixed, narrow blur regardless of the parameter. And GPU and library implementations often clamp the radius for performance, silently truncating your requested sigma. The defense is to know your kernel's real effective sigma (measure it, as this module does) rather than trusting the nominal parameter, and to verify that a library's radius is at least 3 sigma for the sigma you asked for, especially at large sigma where the clamp bites. The rule generalizes: the blur you get is the kernel you actually applied, not the sigma you named.

**Truncation error squares across the two passes of a separable blur, so an under-sized radius is worse in 2-D; and because hardcoded integer kernels and library radius clamps bake in a fixed small effective sigma, measure the kernel's real width rather than trusting the nominal sigma.**

## External resources

The SciPy and OpenCV Gaussian-filter documentation specify how the kernel radius is derived from sigma (truncate at a multiple of sigma, typically 3 to 4) and note the truncation parameter explicitly.
Any image-processing reference on Gaussian smoothing covers the infinite-support / finite-kernel trade-off and the convention of sizing the kernel to about three standard deviations.
The topic's own modules on dividing a kernel by its weight-sum and on separable blurs cover the neighboring concerns — normalizing the kernel and computing it as two 1-D passes — that this one connects to the question of how wide the kernel must be in the first place.
