---
id: premult-inter-01
title: Premultiply color by alpha before averaging — a transparent pixel's invisible color leaks into edges otherwise
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: An RGBA pixel stores a color and an alpha. The color of a fully transparent pixel (alpha 0) is invisible and therefore undefined — authoring tools leave whatever bytes were there — and that is harmless until you average pixels, which downscaling, blurring, mipmapping, and antialiasing all do. A naive average of the RGB channels weights that invisible color equally with the visible ones, so a red opaque pixel averaged with a transparent pixel that happens to carry blue comes out purple, and composited onto a page that purple shows as a colored fringe around every cut-out edge. The fix is premultiplied alpha: multiply each pixel's color by its alpha before averaging, so a transparent pixel's color becomes zero and contributes nothing; average the premultiplied colors and the alphas, and divide by the averaged alpha to recover a straight color. On a fixture averaging opaque red (255,0,0, alpha 1) with transparent blue (0,0,255, alpha 0), straight averaging gives purple (127.5,0,127.5) at alpha 0.5 — the invisible blue leaked in — while premultiplying gives (127.5,0,0) at alpha 0.5, which un-premultiplies to pure red (255,0,0); over a white background the straight result is a purplish (191,128,191) versus the correct pink (255,128,128).
eli5: Picture two stickers you're blending into one: a solid red sticker and a completely see-through one that, for no visible reason, was printed on blue backing you can't see. If you mix their colors by just averaging, the invisible blue sneaks into the mix and your red turns purple — even though that blue was supposed to be invisible. The fix is to first fade each sticker's color by how see-through it is, so the fully transparent one fades to nothing before you mix. Now the invisible blue really contributes nothing, and your red stays red. This is why cut-out images sometimes get an ugly colored halo at the edges: an invisible color leaked in during resizing.
---

## Why this module

Transparency hides a value that does not matter — until an averaging step makes it matter. Resize or blur an image with a cut-out edge and the color of pixels you can't even see gets mixed into the pixels you can, producing a fringe that appears from nowhere and is baffling until you know where it came from.

An RGBA pixel stores a color and an alpha (coverage/opacity). The color of a fully transparent pixel — alpha 0 — is invisible, so it is also undefined: nothing on screen depends on it, and tools leave whatever bytes happened to be there. That is harmless as long as the pixel stays transparent. But the moment you average pixels — and downscaling, blurring, mipmapping, and antialiasing all average pixels — the question of what a transparent pixel's color is suddenly matters, because a naive average of the RGB channels weights that invisible color equally with the visible ones. A red opaque pixel averaged with a transparent pixel that happens to carry blue comes out purple, and when that purple is composited onto a page it shows as a colored fringe around every edge where opaque meets transparent. The bug is famous: dark or discolored halos around cut-out images, entirely from averaging color that should have carried zero weight.

The fix is premultiplied alpha. Before averaging, multiply each pixel's color by its alpha, so a transparent pixel's color becomes zero and contributes nothing no matter what garbage it stored. Average the premultiplied colors and the alphas, and you have the correct premultiplied result directly; to recover a straight color, divide by the averaged alpha. The rule mirrors the gamma rule: an averaging operation is only correct on the right representation, and for alpha that representation is premultiplied, because it weights each pixel's color by how much of it is actually there. This module averages a red and a transparent-blue pixel both ways and shows the leak.

**Averaging RGBA pixels on straight color lets a transparent pixel's invisible color leak into edges as a fringe, so premultiply each color by its alpha before averaging — a transparent pixel then contributes zero color — and un-premultiply to recover a straight result.**

## Concepts

**Straight blending** averages the RGB channels and the alpha separately, with no regard for coverage — so an invisible pixel's color counts as much as a visible one.

```python filename=modules/generative-media/code/premult-inter-01/premult.py:54-58 COMPLETE
def blend_straight(p1, p2):
    """WRONG: average the RGB channels and the alpha separately, ignoring coverage."""
    rgb = avg(p1["rgb"], p2["rgb"])
    alpha = (p1["alpha"] + p2["alpha"]) / 2
    return rgb, alpha
```

**Premultiplying** multiplies a pixel's color by its alpha. A transparent pixel (alpha 0) becomes color 0, so whatever undefined color it carried is erased before it can contaminate anything.

```python filename=modules/generative-media/code/premult-inter-01/premult.py:61-63 COMPLETE
def premultiply(pixel):
    """Multiply color by alpha, so a transparent pixel's color becomes zero."""
    return [c * pixel["alpha"] for c in pixel["rgb"]]
```

**Premultiplied blending** averages the premultiplied colors (where transparent pixels weigh nothing) and the alphas, then divides by the averaged alpha to return a straight color.

```python filename=modules/generative-media/code/premult-inter-01/premult.py:66-71 COMPLETE
def blend_premultiplied(p1, p2):
    """RIGHT: premultiply, average, then un-premultiply (divide by the averaged alpha)."""
    pm = avg(premultiply(p1), premultiply(p2))
    alpha = (p1["alpha"] + p2["alpha"]) / 2
    rgb = [c / alpha for c in pm] if alpha else [0.0] * CH
    return rgb, alpha
```

<svg role="img" aria-label="Two pixels averaged: straight averaging mixes red and the invisible blue into purple, premultiplying zeroes the transparent pixel first so the result stays red" viewBox="0 0 300 128" width="300" height="128">
  <text x="6" y="12" fill="var(--muted)" font-size="8">premultiply zeroes the transparent pixel before the average</text>
  <g transform="translate(20,22)" font-size="6">
  <rect x="0" y="0" width="30" height="20" fill="var(--s2)"/><text x="4" y="13" fill="var(--panel)">red a1.0</text>
  <rect x="0" y="26" width="30" height="20" fill="var(--s1)" opacity="0.25"/><rect x="0" y="26" width="30" height="20" fill="none" stroke="var(--line)"/><text x="2" y="39" fill="var(--muted)">blue a0.0</text>
  </g>
  <text x="60" y="40" fill="var(--muted)" font-size="7">straight avg →</text>
  <rect x="130" y="26" width="30" height="20" fill="var(--muted)"/><text x="126" y="58" fill="var(--muted)" font-size="6">purple (leak)</text>
  <text x="60" y="92" fill="var(--muted)" font-size="7">premultiply →</text>
  <g transform="translate(130,82)" font-size="6">
  <rect x="0" y="0" width="30" height="14" fill="var(--s2)"/><text x="2" y="10" fill="var(--panel)">255,0,0</text>
  <rect x="0" y="16" width="30" height="14" fill="var(--ink)"/><text x="2" y="26" fill="var(--panel)">0,0,0</text>
  </g>
  <text x="172" y="96" fill="var(--muted)" font-size="7">avg → un-premult →</text>
  <rect x="262" y="86" width="26" height="20" fill="var(--s2)"/><text x="258" y="118" fill="var(--muted)" font-size="6">red (correct)</text>
</svg>
^ Straight averaging blends the opaque red with the transparent pixel's undefined blue into purple; premultiplying first turns the transparent pixel's color to (0,0,0) so it adds nothing, and the average un-premultiplies back to pure red.

**Averaging is only correct on premultiplied color, where each pixel's color is weighted by its alpha, so a transparent pixel contributes zero — averaging straight color instead lets an invisible pixel's undefined color leak into the result.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/premult-inter-01/premult.py

The fixture is two pixels: an opaque red, and a fully transparent pixel that still carries a leftover blue.

```json filename=modules/generative-media/code/premult-inter-01/premult.json:3-6 COMPLETE
  "pixels": [
    {"name": "opaque_red", "rgb": [255, 0, 0], "alpha": 1.0},
    {"name": "transparent_blue", "rgb": [0, 0, 255], "alpha": 0.0}
  ],
```

Run `--blend` to average them both ways.

```text filename=--blend
BLEND — average an opaque red with a transparent blue pixel
--------------------------------------------------------------
  input  opaque_red       rgb=[255, 0, 0] alpha=1.0
  input  transparent_blue rgb=[0, 0, 255] alpha=0.0
--------------------------------------------------------------
  straight avg       rgb=[127.5, 0.0, 127.5] alpha=0.5  <- purple: blue leaked from the invisible pixel
  premultiplied avg  rgb=[255.0, 0.0, 0.0] alpha=0.5  <- pure red: transparent pixel contributed nothing
```

Straight averaging produces (127.5, 0, 127.5) — half red, half blue, a purple — at alpha 0.5. Both channels were averaged as-is, so the blue from a pixel that was completely invisible now makes up half the result's color. Premultiplied averaging produces (255, 0, 0), pure red, at the same alpha 0.5. The difference is that premultiplying multiplied the transparent pixel's blue by its alpha of 0, erasing it before the average, so only the red contributed color; dividing the averaged premultiplied color (127.5, 0, 0) by the averaged alpha (0.5) restores the red to full strength. Both methods agree the result is 50% covered — the alpha is 0.5 either way — but only the premultiplied method gets the *color* of that coverage right. The straight method invented a purple that no visible pixel ever contained.

## Build

Where the leak actually shows up is on screen, when the averaged pixel is composited onto a background. Run `--composite`.

```text filename=--composite
COMPOSITE — put each averaged result over the white background [255, 255, 255]
------------------------------------------------------------
  straight result over white       = [191.2, 127.5, 191.2]  (purplish fringe)
  premultiplied result over white  = [255.0, 127.5, 127.5]  (clean pink)
------------------------------------------------------------
  the straight composite is tinted toward blue/purple by a pixel that was fully transparent.
```

Composited over white, the two results diverge visibly. The premultiplied result is (255, 128, 128) — a clean pink, exactly what 50%-opacity red over white should be. The straight result is (191, 128, 191) — a muddy purple, because the leaked blue lifted the blue channel and dragged the red channel down. That purple is the fringe: run it around the edge of a red cut-out on a white page and you get a visible violet halo tracing the boundary, produced entirely by pixels that were supposed to show nothing. This is why the bug is so confusing in practice — the offending pixels are invisible in the source, so nothing in the artwork looks wrong until a resize or a composite averages them in. The leak is one channel that should have been weighted to zero and was not.

<svg role="img" aria-label="The averaged pixel composited over white: the straight version is a purplish swatch, the premultiplied version is a pink swatch" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the fringe on a white page: straight is purple, premult is pink</text>
  <text x="20" y="34" fill="var(--muted)" font-size="7">straight over white</text>
  <rect x="20" y="40" width="110" height="30" fill="var(--muted)"/><text x="24" y="84" fill="var(--muted)" font-size="7">(191,128,191) purple</text>
  <text x="175" y="34" fill="var(--muted)" font-size="7">premult over white</text>
  <rect x="175" y="40" width="110" height="30" fill="var(--s2)" opacity="0.5"/><text x="179" y="84" fill="var(--muted)" font-size="7">(255,128,128) pink</text>
</svg>
^ Over the white background the straight blend reads as a purplish swatch (blue leaked in) while the premultiplied blend reads as the correct pink — the visible fringe versus the clean edge a resize should produce.

## Definition of done

The self-test pins the blue leak, its absence under premultiplication, the preserved red, and the zeroed transparent pixel.

```python filename=modules/generative-media/code/premult-inter-01/premult.py:114-121 COMPLETE
    straight_leaks_blue = s_rgb[2] > 0
    print("  straight average leaks blue from the transparent pixel = %s (blue=%.1f)" % (straight_leaks_blue, s_rgb[2]))

    premult_no_blue = m_rgb[2] == 0
    print("  premultiplied average has no blue leak = %s (blue=%.1f)" % (premult_no_blue, m_rgb[2]))

    premult_is_pure_red = m_rgb[0] == 255 and m_rgb[1] == 0 and m_rgb[2] == 0
    print("  premultiplied result is pure red = %s (%s)" % (premult_is_pure_red, [round(x, 1) for x in m_rgb]))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — straight averaging leaks the transparent pixel's blue; premultiplying zeroes it and preserves the true red
--------------------------------------------------------------------------------------------------------------------
  straight average leaks blue from the transparent pixel = True (blue=127.5)
  premultiplied average has no blue leak = True (blue=0.0)
  premultiplied result is pure red = True ([255.0, 0.0, 0.0])
  both methods give the same alpha = True (0.5)
  the transparent pixel premultiplies to zero color = True ([0.0, 0.0, 0.0])
```

**Done means the leak and the fix are proven on real channels: straight averaging leaves 127.5 of blue from a fully transparent pixel and a purple result, while premultiplying zeroes that pixel's color (0,0,0), gives no blue leak, and preserves pure red (255,0,0) — at the same alpha 0.5 either way — so RGBA averaging must premultiply or an invisible color fringes every edge.**

## Boss fight

Predict two ways this compounds, because premultiplication interacts with the un-premultiply divide and with the gamma correction from the companion module.

The first trap is the un-premultiply step, which divides by alpha and so is unstable exactly where alpha is small. Recovering a straight color as premultiplied/alpha is a division that blows up as alpha approaches 0: a nearly-transparent pixel with a tiny premultiplied color divides to a wildly amplified, noisy straight color, and at alpha exactly 0 it is 0/0. This is why premultiplied is often the *better representation to keep* rather than convert back from — compositing, filtering, and blending are all defined cleanly on premultiplied color (compositing is just out = fg + bg·(1−alpha), with no separate alpha-weighting of fg), so many renderers and image formats stay premultiplied end to end and only un-premultiply at the very last step, if ever. The bug's mirror image also exists: double-premultiplication. If an asset is already premultiplied and a pipeline premultiplies it again (or a format's alpha mode is mislabeled), colors get multiplied by alpha twice and edges go too dark — the "dark halo" that looks like the straight-alpha fringe but comes from the opposite mistake. So the alpha mode of every image is metadata you must track, not guess.

<svg role="img" aria-label="The correct RGBA resize pipeline as five steps: decode to linear, premultiply by alpha, average, un-premultiply, re-encode" viewBox="0 0 300 78" width="300" height="78">
  <text x="6" y="12" fill="var(--muted)" font-size="8">a correct transparent resize does BOTH corrections, in order</text>
  <g font-size="6" fill="var(--muted)">
  <rect x="6" y="24" width="48" height="22" fill="none" stroke="var(--s1)"/><text x="10" y="34">decode</text><text x="10" y="43">→ linear</text>
  <rect x="62" y="24" width="52" height="22" fill="none" stroke="var(--s2)"/><text x="66" y="34">premultiply</text><text x="66" y="43">× alpha</text>
  <rect x="122" y="24" width="44" height="22" fill="none" stroke="var(--ink)"/><text x="126" y="38">average</text>
  <rect x="174" y="24" width="56" height="22" fill="none" stroke="var(--s2)"/><text x="178" y="34">un-premult</text><text x="178" y="43">÷ alpha</text>
  <rect x="238" y="24" width="50" height="22" fill="none" stroke="var(--s1)"/><text x="242" y="34">re-encode</text><text x="242" y="43">→ gamma</text>
  </g>
  <text x="54" y="37" fill="var(--muted)" font-size="8">→</text><text x="114" y="37" fill="var(--muted)" font-size="8">→</text><text x="166" y="37" fill="var(--muted)" font-size="8">→</text><text x="230" y="37" fill="var(--muted)" font-size="8">→</text>
  <text x="6" y="62" fill="var(--muted)" font-size="7">skip decode → dark blend (gamma bug); skip premultiply → fringed edges (this bug)</text>
</svg>
^ The gamma correction (decode/re-encode, outer) and the alpha correction (premultiply/un-premultiply, inner) wrap the average together — omitting the decode darkens the blend and omitting the premultiply fringes the edges, so a correct RGBA downscale must do both.

The second trap is that this is the *same* averaging discipline as gamma, and the two corrections stack in a specific order. Both say an averaging operation is only valid on the right representation: gamma says decode to linear light first, alpha says premultiply first. A fully correct downscale of a transparent, gamma-encoded image therefore does both — decode each pixel to linear light, premultiply by alpha, average, un-premultiply, and re-encode — and getting the order wrong reintroduces one of the errors. Skipping the linearize darkens the blend (the gamma bug); skipping the premultiply fringes the edges (this bug); doing neither gives you both a dark and a discolored halo, which is the default output of a naive image resize on RGBA data. This is why high-quality image libraries make such a point of "premultiplied, linear-light" resampling: it is not one exotic setting but the composition of the two averaging rules, each of which alone is a visible defect.

**Un-premultiplying divides by alpha and is unstable as alpha approaches zero (and undefined at zero), so prefer to stay premultiplied through the pipeline and beware double-premultiplication darkening edges — and because premultiplication is the same "average in the right representation" rule as gamma, a correct RGBA resize must both linearize and premultiply, in that order, or edges come out dark, fringed, or both.**

## External resources

Any compositing or image-processing reference on premultiplied (associated) versus straight (unassociated) alpha — the "dark fringe" / halo bug, why filtering and compositing are defined on premultiplied color, and the instability of un-premultiplying at low alpha.

Tom Duff and Thomas Porter's classic "Compositing Digital Images" and modern write-ups on alpha — the algebra of premultiplied compositing (out = fg + bg·(1−alpha)) and why it composes cleanly under averaging.

The companion gamma / linear-light module in this topic — premultiplied alpha and linear-light are the two representation rules a correct RGBA resize must apply together, so the two modules combine into the full "linearize then premultiply then average" resampling recipe.
