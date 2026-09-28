---
id: whitebalance-inter-01
title: Remove a color cast with gray-world white balance — but only when the scene's average really is gray, or you flatten a real color
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: A camera cannot discount the color of the light the way the eye does, so a photo shot under a bluish LED carries a blue cast — every channel average shifted by the light, not the scene. The simplest correction is gray-world white balance: assume the average of a whole scene is a neutral gray (many colored objects average out), so any imbalance between the channel means is the light's cast, and remove it by scaling each channel by target/channel_mean until all three means are equal. On a neutral scene under a bluish light (means R=100, G=110, B=160) this works: gray-world scales the channels to a common 123.3 and the cast is gone. But the method is only as true as its assumption, which is a claim about the scene, not a law. On a scene genuinely dominated by one color — grass with means R=60, G=150, B=50 — the average is NOT gray, and gray-world "corrects" the real green out of the image, flattening all three channels to 86.7. The algorithm cannot tell a green cast from green grass; it assumes any imbalance is a cast, and on a one-color scene that assumption is false.
eli5: Your eyes automatically figure out that a white shirt is white whether you're indoors under yellow light or outdoors under blue sky. A camera can't do that on its own, so a photo under colored light comes out tinted. One fix guesses that if you average all the colors in the whole picture together you should get gray, so it stretches the colors until the average IS gray. That works great for most photos — but if you photograph a field of grass, the average really is green, and the fix will "helpfully" drain the green right out of your grass. The trick only works when its guess about the picture is true.
---

## Why this module

Your eye discounts the color of the light automatically — a white shirt looks white under a yellow bulb and under blue sky — but a camera records the light's color mixed into every pixel, so a photo under colored light comes out tinted, and software has to guess the light and cancel it. The cheapest guess is right often enough to ship and wrong in a way that quietly destroys real color.

White balance is the correction. A photograph taken under colored light carries a color cast: shoot a neutral wall under a bluish LED and the blue channel's average is lifted relative to red and green, so the whole image reads faintly blue. Gray-world white balance corrects it with one assumption — that over a whole scene the average of all the colors is a neutral gray, because the many differently-colored objects average out. If that holds, then any imbalance between the three channel averages is not the scene's content but the light's cast, and you remove it by scaling each channel so its average matches the others: scale blue down, red and green up, until all three averages are equal, and the cast is gone. The scale factors are exactly `target / channel_mean`, where the target is the average the channels should share.

That single assumption is the whole module, because it is a claim about the scene, not a law. When a scene really is dominated by one color — a field of grass, an open ocean, a red-brick wall — its average is genuinely not gray, and gray-world will "correct" the real color out, scaling the dominant channel down until the grass turns gray. The algorithm cannot tell a green cast from green grass; it assumes any channel imbalance is a cast. This module runs gray-world on a neutral scene under a blue light, where it works, and on genuinely green grass, where it flattens the color, and pins both with a self-test.

**Gray-world white balance removes a color cast by scaling each channel to a common average, and it is correct exactly when its assumption holds — that the scene's average is neutral gray — so on a genuinely color-dominated scene it does not remove a cast, it removes the color.**

## Concepts

**The gray-world assumption** is that the average color of a whole scene is neutral gray. Under it, any difference between the three channel means is attributed entirely to the light, so equalizing the means removes the light's cast.

**The scale factors** are `target / channel_mean` per channel, where the target is the mean of the three channel means. Multiplying a channel by `target/mean` moves that channel's average exactly to the target, so after scaling all three channels share the same average — a neutral gray.

```python filename=modules/generative-media/code/whitebalance-inter-01/whitebalance.py:50-53 COMPLETE
def gray_world_scales(means):
    """The per-channel scale factors that make every channel mean equal the target: target / channel_mean."""
    t = target(means)
    return {c: t / means[c] for c in CHANNELS}
```

**Applying the scales** multiplies each channel by its factor. On a scene whose average really is gray this cancels the light; on a scene whose average is a real color it destroys that color, because the two cases are arithmetically identical — the code sees only three channel means and cannot know which one it was handed.

```python filename=modules/generative-media/code/whitebalance-inter-01/whitebalance.py:56-58 COMPLETE
def apply_scales(means, scales):
    """Apply the scale factors to the channel means."""
    return {c: means[c] * scales[c] for c in CHANNELS}
```

<svg role="img" aria-label="Three channel-mean bars for red, green, and blue at 100, 110, 160 before gray-world, and all three equalized to 123.3 after" viewBox="0 0 300 130" width="300" height="130">
  <text x="6" y="12" fill="var(--muted)" font-size="8">gray-world scales each channel to the shared target 123.3</text>
  <line x1="30" y1="100" x2="290" y2="100" stroke="var(--line)"/>
  <text x="24" y="30" fill="var(--muted)" font-size="7" text-anchor="end">160</text>
  <line x1="30" y1="27" x2="290" y2="27" stroke="var(--grid)" stroke-dasharray="2 2"/>
  <text x="24" y="60" fill="var(--muted)" font-size="7" text-anchor="end">123</text>
  <line x1="30" y1="57" x2="290" y2="57" stroke="var(--grid)" stroke-dasharray="2 2"/>
  <g transform="translate(48,0)">
  <rect x="0" y="60" width="16" height="40" fill="var(--s1)"/><text x="0" y="112" fill="var(--muted)" font-size="7">R100</text>
  <rect x="22" y="55" width="16" height="45" fill="var(--s1)"/><text x="22" y="112" fill="var(--muted)" font-size="7">G110</text>
  <rect x="44" y="27" width="16" height="73" fill="var(--s2)"/><text x="44" y="112" fill="var(--muted)" font-size="7">B160</text>
  <text x="8" y="124" fill="var(--muted)" font-size="7">before (cast)</text>
  </g>
  <text x="150" y="80" fill="var(--muted)" font-size="10">→</text>
  <g transform="translate(180,0)">
  <rect x="0" y="57" width="16" height="43" fill="var(--ink)"/><text x="0" y="112" fill="var(--muted)" font-size="7">R</text>
  <rect x="22" y="57" width="16" height="43" fill="var(--ink)"/><text x="22" y="112" fill="var(--muted)" font-size="7">G</text>
  <rect x="44" y="57" width="16" height="43" fill="var(--ink)"/><text x="44" y="112" fill="var(--muted)" font-size="7">B</text>
  <text x="4" y="124" fill="var(--muted)" font-size="7">after: all 123.3</text>
  </g>
</svg>
^ Before gray-world the blue channel mean (160) is lifted by the light; scaling each channel by target/mean brings all three to the shared target 123.3, and the blue cast is gone.

**Every scale factor is target/channel_mean, so applying them always makes the three channel means equal — the operation is the same whether the imbalance was a light's cast or the scene's own color, and only the scene decides whether equalizing is a correction or a destruction.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/whitebalance-inter-01/whitebalance.py

The fixture is two scenes, each given by its three channel means. The cast scene is a neutral surface under a bluish light — blue lifted. The color scene is real grass under neutral light — green genuinely dominant.

```json filename=modules/generative-media/code/whitebalance-inter-01/whitebalance.json:3-4 COMPLETE
  "cast_scene": {"R": 100.0, "G": 110.0, "B": 160.0},
  "color_scene": {"R": 60.0, "G": 150.0, "B": 50.0}
```

Run `--balance` on the cast scene, where the assumption holds.

```text filename=--balance
BALANCE — gray-world on a neutral scene under a bluish light
----------------------------------------------------------
  channel   mean     scale (target/mean)   after
  R         100.0    1.233                 123.3
  G         110.0    1.121                 123.3
  B         160.0    0.771                 123.3
----------------------------------------------------------
  target = 123.3; blue is scaled down, red and green up, cast removed (all equal).
```

The target is the mean of the three means, `(100 + 110 + 160) / 3 = 123.3`. Each scale is `123.3 / mean`: red `1.233`, green `1.121`, blue `0.771`. Blue is above target so it scales down; red and green are below so they scale up; after scaling all three sit at 123.3. Because this scene really was a neutral surface, its true colors averaged gray before the light tinted it — so cancelling the imbalance recovers the neutral it should have been. This is gray-world at its best: the imbalance was entirely the light, and equalizing the channels removes exactly the light. Nothing in the numbers, though, marks this scene as the good case — the code computed three ratios and multiplied. The next section feeds it a scene where the same three multiplications are a mistake.

## Build

Run `--assumption` on the grass, where the scene's average is genuinely not gray.

```text filename=--assumption
ASSUMPTION — gray-world on genuinely green grass (average is NOT gray)
------------------------------------------------------------
  channel   mean     after gray-world
  R         60.0     86.7
  G         150.0    86.7
  B         50.0     86.7
------------------------------------------------------------
  the real green (G=150) is flattened to the same 86.7 as red and blue -- the color is gone.
```

The grass has means R=60, G=150, B=50 — green is three times the other channels because the grass really is green, not because of any light. Gray-world does not know that. It computes the target `(60 + 150 + 50) / 3 = 86.7`, scales green by `86.7 / 150 = 0.578` down to 86.7, scales red and blue up to 86.7, and hands back a scene where all three channels are equal: a gray field. The real, correct green has been "corrected" away. This is not a bug in the arithmetic — the arithmetic is the same arithmetic that fixed the cast scene. It is the assumption failing: the method's one premise, that the scene's average is gray, is false here, and when the premise is false the operation that removes a cast instead removes the content. The target the whole method aims at is only the right destination when the scene really should be neutral.

<svg role="img" aria-label="Grass channel means red 60, green 150, blue 50, all flattened by gray-world to 86.7, destroying the dominant green" viewBox="0 0 300 130" width="300" height="130">
  <text x="6" y="12" fill="var(--muted)" font-size="8">on real grass, gray-world flattens the dominant green to 86.7</text>
  <line x1="30" y1="100" x2="290" y2="100" stroke="var(--line)"/>
  <text x="24" y="30" fill="var(--muted)" font-size="7" text-anchor="end">150</text>
  <line x1="30" y1="27" x2="290" y2="27" stroke="var(--grid)" stroke-dasharray="2 2"/>
  <text x="24" y="66" fill="var(--muted)" font-size="7" text-anchor="end">87</text>
  <line x1="30" y1="63" x2="290" y2="63" stroke="var(--grid)" stroke-dasharray="2 2"/>
  <g transform="translate(48,0)">
  <rect x="0" y="84" width="16" height="16" fill="var(--s1)"/><text x="0" y="112" fill="var(--muted)" font-size="7">R60</text>
  <rect x="22" y="27" width="16" height="73" fill="var(--s2)"/><text x="22" y="112" fill="var(--muted)" font-size="7">G150</text>
  <rect x="44" y="87" width="16" height="13" fill="var(--s1)"/><text x="44" y="112" fill="var(--muted)" font-size="7">B50</text>
  <text x="4" y="124" fill="var(--muted)" font-size="7">real grass (green)</text>
  </g>
  <text x="150" y="80" fill="var(--muted)" font-size="10">→</text>
  <g transform="translate(180,0)">
  <rect x="0" y="63" width="16" height="37" fill="var(--muted)"/><text x="0" y="112" fill="var(--muted)" font-size="7">R</text>
  <rect x="22" y="63" width="16" height="37" fill="var(--muted)"/><text x="22" y="112" fill="var(--muted)" font-size="7">G</text>
  <rect x="44" y="63" width="16" height="37" fill="var(--muted)"/><text x="44" y="112" fill="var(--muted)" font-size="7">B</text>
  <text x="6" y="124" fill="var(--muted)" font-size="7">after: gray 86.7</text>
  </g>
</svg>
^ The grass really is green (G=150 vs R=60, B=50), but gray-world reads that as a cast and scales all three channels to 86.7 — the same equalizing move that fixed the cast scene here erases a real color.

## Definition of done

The self-test pins both halves: gray-world neutralizes a real cast, and the same operation flattens a genuinely color-dominated scene, with the scale factors confirmed to be `target/channel_mean`.

```python filename=modules/generative-media/code/whitebalance-inter-01/whitebalance.py:99-108 COMPLETE
    cast_has_imbalance = not is_neutral(cast)
    print("  the cast scene has unequal channel means (a cast) = %s (%s)" % (cast_has_imbalance, {c: cast[c] for c in CHANNELS}))

    cast_scales = gray_world_scales(cast)
    cast_out = apply_scales(cast, cast_scales)
    cast_neutralized = is_neutral(cast_out)
    print("  gray-world equalizes the cast scene's channels = %s (%s)" % (cast_neutralized, {c: round(cast_out[c], 1) for c in CHANNELS}))

    scales_are_ratio = all(abs(cast_scales[c] - target(cast) / cast[c]) < 1e-12 for c in CHANNELS)
    print("  the scale factors are target/channel_mean = %s" % scales_are_ratio)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — gray-world equalizes the channel means (removing a cast) but also flattens a real color-dominated scene
------------------------------------------------------------------------------------------------------------------
  the cast scene has unequal channel means (a cast) = True ({'R': 100.0, 'G': 110.0, 'B': 160.0})
  gray-world equalizes the cast scene's channels = True ({'R': 123.3, 'G': 123.3, 'B': 123.3})
  the scale factors are target/channel_mean = True
  applied to real green grass, gray-world flattens the color = True (G 150 -> 86.7)
  the grass scene was genuinely green-dominant (not a cast) = True
```

The test asserts what the method does and what it cannot distinguish. `cast_has_imbalance` and `cast_neutralized` confirm the cast scene is unbalanced and that gray-world equalizes it. `scales_are_ratio` confirms the factors are exactly `target/channel_mean`. `color_flattened` confirms the grass, which has a genuine green dominance (`green_was_dominant`), is equalized to 86.7 by the identical operation — the failure is not an exception path, it is the same code doing the same thing to a different scene.

**Done means the same gray-world operation is shown to both fix a cast (the neutral scene under a blue light equalizes to 123.3) and destroy a color (real green grass flattened to 86.7), with the scales verified as target/channel_mean — proving the outcome is decided by whether the scene's average is gray, not by any property the algorithm can check.**

## Boss fight

Predict two ways this bites in a real pipeline, and how to make gray-world safer without pretending it is a universal solver.

The first is that you cannot detect the failure from the scene's own channel means, because a neutral scene under a colored light and a color-dominated scene under neutral light produce the *same* signal: three unequal channel means. `is_neutral` only tells you the channels are already equal — it does not tell you whether an imbalance is a cast to remove or content to keep.

```python filename=modules/generative-media/code/whitebalance-inter-01/whitebalance.py:61-63 COMPLETE
def is_neutral(means, tol=1e-6):
    """Are all three channel means equal (a neutral, cast-free scene)?"""
    return max(means[c] for c in CHANNELS) - min(means[c] for c in CHANNELS) < tol
```

<svg role="img" aria-label="Two different scenes, a neutral surface under blue light and real green grass, both producing three unequal channel means, so the same signal has two causes gray-world cannot tell apart" viewBox="0 0 300 128" width="300" height="128">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the same signal (three unequal means) has two causes</text>
  <g transform="translate(10,22)">
  <rect x="0" y="0" width="70" height="34" fill="none" stroke="var(--line)"/>
  <text x="6" y="14" fill="var(--muted)" font-size="7">neutral wall</text>
  <text x="6" y="26" fill="var(--muted)" font-size="7">+ blue light</text>
  </g>
  <g transform="translate(10,74)">
  <rect x="0" y="0" width="70" height="34" fill="none" stroke="var(--line)"/>
  <text x="6" y="14" fill="var(--muted)" font-size="7">green grass</text>
  <text x="6" y="26" fill="var(--muted)" font-size="7">+ neutral light</text>
  </g>
  <text x="92" y="44" fill="var(--muted)" font-size="9">→</text>
  <text x="92" y="96" fill="var(--muted)" font-size="9">→</text>
  <g transform="translate(112,26)">
  <rect x="0" y="20" width="10" height="10" fill="var(--s1)"/><rect x="14" y="14" width="10" height="16" fill="var(--s1)"/><rect x="28" y="0" width="10" height="30" fill="var(--s2)"/>
  <text x="0" y="42" fill="var(--muted)" font-size="7">unequal means</text>
  </g>
  <g transform="translate(112,78)">
  <rect x="0" y="18" width="10" height="12" fill="var(--s1)"/><rect x="14" y="0" width="10" height="30" fill="var(--s2)"/><rect x="28" y="20" width="10" height="10" fill="var(--s1)"/>
  <text x="0" y="42" fill="var(--muted)" font-size="7">unequal means</text>
  </g>
  <text x="182" y="66" fill="var(--muted)" font-size="8">gray-world sees</text>
  <text x="182" y="78" fill="var(--muted)" font-size="8">only the means —</text>
  <text x="182" y="90" fill="var(--muted)" font-size="8">a cast to remove?</text>
  <text x="182" y="102" fill="var(--muted)" font-size="8">or real color to keep?</text>
</svg>
^ A neutral surface under a colored light and a genuinely colored scene under neutral light both hand gray-world the same thing — three unequal channel means — so from the means alone it cannot tell a cast to remove from a color to keep.

Since the ambiguity is real, the fixes bring in information gray-world throws away. The white-patch (max-RGB) estimator assumes the *brightest* region of the scene is a true white or specular highlight and scales each channel so that its maximum, not its mean, hits full white — robust to a large colored area but fooled by a saturated colored light. Better still, most real cameras do not commit to one assumption: they use a learned or reference-based auto white balance that looks for known neutral cues (skin tones, sky, a gray card, the shape of the color histogram) and estimate the illuminant directly, then fall back toward gray-world only as a weak prior. And when you can, you sidestep estimation entirely: photograph a physical gray card or color chart in the scene, read the light off a patch you *know* is neutral, and apply that — no assumption about the scene's average at all. The lesson is not "gray-world is bad"; it is that gray-world encodes one prior about the scene, so it is only as good as that prior, and a robust system either checks the prior against extra cues or measures the illuminant from a known reference rather than inferring it from the average.

The second trap is that the correction is often applied where it is least valid: per-tile or per-region gray-world, run to fix uneven lighting, will happily gray out any tile that happens to be one color — the patch of sky, the close-up of a red sweater — precisely because a smaller region is *more* likely to be genuinely one-colored and *less* likely to average gray. The whole-scene average is the assumption's best case; shrinking the window makes the assumption weaker exactly as you demand more of it. So the safe uses of gray-world are the ones where its premise is plausible — a full, varied scene, as a mild global nudge, or as a fallback prior behind a real illuminant estimate — and the dangerous ones are the aggressive, local, high-strength corrections applied to scenes or tiles that may legitimately be one color.

**Gray-world removes a cast by equalizing channel means under the assumption that the scene averages to gray, but that imbalance is indistinguishable from real color, so a robust system does not trust the average alone — it estimates the illuminant from known-neutral cues or a physical gray card, treats gray-world as a weak global prior rather than a per-tile hammer, and reserves it for full, varied scenes where its one premise is actually plausible.**

## External resources

Any color-constancy or computational-photography reference on the gray-world assumption and its estimators — gray-world (average-to-gray), white-patch / max-RGB (brightest-to-white), and shades-of-gray, which generalize both — plus why each is a different prior about the scene rather than a measurement of the light.

Writing on illuminant estimation and auto white balance in cameras — how reference-based and learned methods use known-neutral cues (skin, sky, gray cards) and histogram shape to estimate the light directly, using gray-world only as a fallback prior.

The companion binarization and histogram modules — like Otsu thresholding, white balance is a per-image estimate made from image statistics under an assumption, so both teach the same discipline: name the assumption, test it, and fall back to a measured reference when the assumption may not hold.
