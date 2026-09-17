---
id: tonemap-inter-01
title: Tone-map on the pixel's luminance and scale the color — applying the curve per channel desaturates a bright highlight toward white
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: A high-dynamic-range image holds linear light values that run past 1.0 — a lamp, a sky, a specular glint — and a display can only show 0 to 1, so a tone-mapping operator compresses the range with a curve that is steep near zero and flattens as it rises. The Reinhard operator x → x/(1+x) is the canonical one. The obvious way to apply it is to run every channel through the curve, and that does compress the brightness — but it silently changes the color, because the curve is concave: it squeezes a large input proportionally harder than a small one, so the gap between the three channels closes, and closing the gap between R, G, and B is the definition of desaturation. On the fixture the HDR pixel [2.0, 1.2, 0.5] has saturation 0.75; per-channel Reinhard returns [0.667, 0.545, 0.333] at saturation 0.50 — a vivid warm highlight come back milky. The fix keeps color and brightness on separate tracks: compute the pixel's luminance (1.3195 here), run only that single number through the curve (to 0.5689), and scale the original RGB by the ratio mapped_luminance / luminance. Because the scale is one common factor across all three channels, their ratios are untouched, so the result [0.862, 0.517, 0.216] holds the saturation at exactly 0.75 while its luminance lands precisely on the curve's target of 0.5689. The rule: a tone curve compresses brightness, and brightness is a property of the luminance, not of each channel — map the luminance, then scale the color.
eli5: Imagine three friends of different heights standing in a room with a low ceiling, and you need to shrink them all to fit under it. If you shrink each one by a different rule — the tallest gets squished the most, the shortest barely at all — they end up closer to the same height, and the group looks totally different: you've lost what made them a tall-medium-short trio. A color is like that trio of three numbers, and its "look" (its hue and vividness) is the proportion between them. A tone curve squishes big numbers more than small ones, so applying it to each of red, green, blue separately flattens them toward equal — and three equal channels is gray. The fix is to measure the group's overall height once, figure out the single shrink factor that fits it under the ceiling, and shrink all three by that same factor — now they still look like the same trio, just smaller.
---

## Why this module

Tone mapping is the step that makes a rendered or HDR-captured image displayable: it takes light values that can be arbitrarily bright and squeezes them into the range a screen can show. Every real-time renderer and every HDR photo pipeline does it, and the textbook operator is a one-liner, `x / (1 + x)`, that you apply to the pixel.

Apply it to the pixel and the trap is which "it" you apply it to. Run the curve over each of the three channels and the brightness compresses correctly — the highlight stops clipping, the numbers land in range — so it looks done. But the color has quietly drained. A saturated orange sun comes back a pale cream, a deep blue sky comes back washed and gray, and nothing in the code looks wrong.

This module builds one bright saturated pixel, tone-maps it both ways, and measures the saturation. Per channel, the saturation collapses from 0.75 to 0.50. On the luminance, it stays at exactly 0.75 while the brightness compresses by the same factor the curve intended. Then it shows why the concavity of the curve is the whole cause, and how to keep color and brightness apart.

**A tone curve is a statement about brightness, and running it down the channels applies a brightness rule to the color too — which is why the highlights come back not just darker but paler.**

## Concepts

The tone curve exists to solve a range problem: inputs from zero to infinity, outputs from zero to one. Any such curve must bend — rise steeply where the values are small and flatten where they are large — so that the huge inputs are pulled down hard while the small ones are barely touched. Reinhard's `x / (1 + x)` maps 0.5 to 0.33 (down by a third) and 2.0 to 0.67 (down by two thirds). The bigger the input, the larger its proportional cut.

That concavity is exactly what breaks color when applied per channel. A color's hue and saturation live in the ratios between its channels, not their absolute sizes — double all three and you get the same color, brighter. But the curve does not scale all three by the same factor; it cuts the big channel proportionally more than the small one. So the ratios change, and specifically they compress: the channels move toward each other.

Channels moving toward each other is desaturation by definition — a color whose R, G, and B are equal is gray, and every step toward equal is a step toward gray. A saturated highlight has one channel much larger than the others, which is precisely the channel the curve punishes hardest, so saturated highlights desaturate the most. The brighter and more vivid the color, the more per-channel tone mapping washes it out.

<svg role="img" aria-label="The Reinhard tone curve rising from the origin and flattening below one; two input values on the horizontal axis, 0.5 and 2.0, are mapped up to their outputs on the curve, showing the larger input is compressed proportionally more" viewBox="0 0 640 300">
<line x1="60" y1="250" x2="600" y2="250" stroke="var(--line)" stroke-width="1"/>
<line x1="60" y1="40" x2="60" y2="250" stroke="var(--line)" stroke-width="1"/>
<line x1="60" y1="70" x2="600" y2="70" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3"/>
<text x="52" y="74" fill="var(--muted)" font-size="10" text-anchor="end">1.0</text>
<text x="330" y="285" fill="var(--muted)" font-size="11" text-anchor="middle">input (linear HDR value) &#8594;</text>
<path d="M 60 250 C 160 130 280 92 600 74" fill="none" stroke="var(--ink)" stroke-width="2"/>
<line x1="150" y1="250" x2="150" y2="190" stroke="var(--s1)" stroke-width="1.5" stroke-dasharray="3 2"/>
<line x1="150" y1="190" x2="60" y2="190" stroke="var(--s1)" stroke-width="1.5" stroke-dasharray="3 2"/>
<text x="150" y="264" fill="var(--s1)" font-size="10" text-anchor="middle">0.5</text>
<text x="52" y="194" fill="var(--s1)" font-size="10" text-anchor="end">0.33</text>
<line x1="420" y1="250" x2="420" y2="84" stroke="var(--s2)" stroke-width="1.5" stroke-dasharray="3 2"/>
<line x1="420" y1="84" x2="60" y2="84" stroke="var(--s2)" stroke-width="1.5" stroke-dasharray="3 2"/>
<text x="420" y="264" fill="var(--s2)" font-size="10" text-anchor="middle">2.0</text>
<text x="52" y="88" fill="var(--s2)" font-size="10" text-anchor="end">0.67</text>
<text x="330" y="150" fill="var(--muted)" font-size="10" text-anchor="middle">2.0 falls to 1/3 of itself; 0.5 only to 2/3</text>
</svg>
^ The curve cuts the large input proportionally harder than the small one, so per-channel mapping closes the gap between channels — which is desaturation.

**Hue and saturation are carried by the ratios between channels, and a concave curve changes those ratios by construction, so any per-channel nonlinearity is a color shift wearing a brightness operation's clothes.**

## Worked example

The fixture is one HDR pixel — a saturated warm highlight, brighter than the display can show — and the Rec.709 luminance weights.

```json filename=modules/generative-media/code/tonemap-inter-01/tonemap.json:3-4 COMPLETE
  "pixel": [2.0, 1.2, 0.5],
  "luminance_weights": [0.2126, 0.7152, 0.0722]
```

The tone curve is the Reinhard operator.

```python filename=modules/generative-media/code/tonemap-inter-01/tonemap.py:35-37 COMPLETE
def reinhard(x):
    """The tone curve: compress an unbounded value into 0..1, gently near 0 and hard up high."""
    return x / (1.0 + x)
```

The buggy way runs it down each channel independently.

```python filename=modules/generative-media/code/tonemap-inter-01/tonemap.py:40-42 COMPLETE
def tone_map_per_channel(rgb):
    """BUG: run each channel through the curve on its own -- the concave curve closes the channel gaps."""
    return [reinhard(c) for c in rgb]
```

Running it shows the brightness compressed — and the saturation gone with it.

```text filename=tonemap.py --perchannel
PER-CHANNEL — Reinhard applied to each channel separately (the bug)
----------------------------------------------------------------
  HDR pixel        = [2.0000, 1.2000, 0.5000]   saturation 0.7500
  per-channel out  = [0.6667, 0.5455, 0.3333]   saturation 0.5000
  luminance 1.3195 -> 0.5559
----------------------------------------------------------------
  the channels were pulled together: the saturation collapsed and the color washed out
```

Saturation fell from 0.75 to 0.50 — a third of the color's vividness gone. The fix maps the luminance alone, then scales the color by the resulting ratio.

```python filename=modules/generative-media/code/tonemap-inter-01/tonemap.py:45-49 COMPLETE
def tone_map_on_luminance(rgb, weights):
    """FIX: map the luminance, then scale RGB by the ratio -- one common factor leaves the ratios intact."""
    lum = luminance(rgb, weights)
    scale = reinhard(lum) / lum
    return [c * scale for c in rgb]
```

That one common factor leaves the ratios exactly where they were.

```text filename=tonemap.py --onluminance
ON-LUMINANCE — Reinhard applied to luminance, then scale RGB (the fix)
----------------------------------------------------------------
  HDR pixel        = [2.0000, 1.2000, 0.5000]   saturation 0.7500
  on-luminance out = [0.8622, 0.5173, 0.2156]   saturation 0.7500
  luminance 1.3195 -> 0.5689  (target reinhard(L) = 0.5689)
----------------------------------------------------------------
  the ratios are untouched: same hue and saturation, at the compressed brightness
```

Saturation held at exactly 0.75, and the luminance landed on 0.5689 — precisely `reinhard(1.3195)`, the value the tone curve prescribed for this pixel's brightness. The figure puts the three colors side by side as channel triples.

<svg role="img" aria-label="Three groups of three bars: the original HDR pixel with tall, medium, and short bars in strong proportion; the per-channel result with the three bars pulled close together; the on-luminance result with the three bars keeping the same proportions as the original but shorter" viewBox="0 0 640 280">
<line x1="40" y1="230" x2="600" y2="230" stroke="var(--line)" stroke-width="1"/>
<text x="130" y="255" fill="var(--muted)" font-size="11" text-anchor="middle">HDR original</text>
<text x="130" y="270" fill="var(--muted)" font-size="10" text-anchor="middle">sat 0.75</text>
<rect x="90" y="90" width="24" height="140" fill="var(--ink)"/>
<rect x="118" y="146" width="24" height="84" fill="var(--s1)"/>
<rect x="146" y="195" width="24" height="35" fill="var(--s2)"/>
<text x="320" y="255" fill="var(--muted)" font-size="11" text-anchor="middle">per-channel</text>
<text x="320" y="270" fill="var(--muted)" font-size="10" text-anchor="middle">sat 0.50 (washed out)</text>
<rect x="280" y="137" width="24" height="93" fill="var(--ink)"/>
<rect x="308" y="154" width="24" height="76" fill="var(--s1)"/>
<rect x="336" y="184" width="24" height="46" fill="var(--s2)"/>
<text x="510" y="255" fill="var(--muted)" font-size="11" text-anchor="middle">on-luminance</text>
<text x="510" y="270" fill="var(--muted)" font-size="10" text-anchor="middle">sat 0.75 (preserved)</text>
<rect x="470" y="109" width="24" height="121" fill="var(--ink)"/>
<rect x="498" y="158" width="24" height="72" fill="var(--s1)"/>
<rect x="526" y="200" width="24" height="30" fill="var(--s2)"/>
</svg>
^ Per-channel mapping pulls the three bars toward the same height (gray); luminance mapping shrinks them together, keeping the original proportions (the color).

**The two methods compress the brightness by almost the same amount — 1.32 down to about 0.56 either way — but only the luminance method leaves the color it started with.**

## Build

The self-test measures the color directly: per-channel tone mapping drops the saturation, luminance tone mapping holds it, and it holds it because the R:G:B ratios are untouched.

```python filename=modules/generative-media/code/tonemap-inter-01/tonemap.py:99-108 COMPLETE
    per_channel_desaturates = saturation(per) < sat0 - 0.05
    print("  per-channel tone mapping lowers saturation = %s (%.4f -> %.4f)" % (per_channel_desaturates, sat0, saturation(per)))

    onlum_preserves_saturation = abs(saturation(lum) - sat0) < 1e-9
    print("  luminance tone mapping preserves saturation = %s (%.4f -> %.4f)" % (onlum_preserves_saturation, sat0, saturation(lum)))

    ratios0 = [c / rgb[0] for c in rgb]
    ratios_lum = [c / lum[0] for c in lum]
    onlum_preserves_ratios = all(abs(a - b) < 1e-9 for a, b in zip(ratios0, ratios_lum))
    print("  luminance tone mapping preserves the R:G:B ratios = %s" % onlum_preserves_ratios)
```

The remaining flags confirm the per-channel ratios shift and that the luminance result's brightness equals the curve's target. All five pass.

```text filename=tonemap.py --check
SELF-TEST — per-channel tone mapping desaturates while luminance tone mapping preserves the ratios and hits the intended brightness
----------------------------------------------------------------------------------------------------------------
  per-channel tone mapping lowers saturation = True (0.7500 -> 0.5000)
  luminance tone mapping preserves saturation = True (0.7500 -> 0.7500)
  luminance tone mapping preserves the R:G:B ratios = True
  per-channel tone mapping shifts the R:G:B ratios = True
  luminance result's brightness equals the tone curve's target = True (0.5689 == 0.5689)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  per_channel_desaturates=True  onlum_preserves_saturation=True  onlum_preserves_ratios=True  per_channel_shifts_ratios=True  onlum_hits_target_brightness=True
```

**Preserving the ratios is not a nice-to-have that happens to keep saturation — it is the same fact stated twice, because saturation is a function of the ratios and nothing else.**

## Definition of done

You are done when your tone-mapping operator, and any other nonlinear brightness curve you apply to a color, runs on the luminance and scales the RGB by the ratio — so brightness compression never leaks into the color.

The structure to keep is a two-track split: extract luminance as the brightness track and the RGB ratios as the color track, put the tone curve on the brightness track only, then recombine by scaling the color track to the new brightness. Any operator that is a function of one scalar brightness — Reinhard, its extended variants, a filmic curve, a simple gamma applied for display — belongs on the luminance track, because all of them are concave and all of them would otherwise desaturate.

<svg role="img" aria-label="A pipeline splitting an RGB pixel into a luminance track and a color-ratio track; the tone curve is applied only to the luminance track; the two tracks recombine by scaling the color by the mapped luminance ratio into the output pixel" viewBox="0 0 640 210">
<rect x="30" y="85" width="90" height="40" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="75" y="109" fill="var(--ink)" font-size="11" text-anchor="middle">RGB pixel</text>
<line x1="120" y1="95" x2="180" y2="60" stroke="var(--line)" stroke-width="1"/>
<line x1="120" y1="115" x2="180" y2="150" stroke="var(--line)" stroke-width="1"/>
<rect x="180" y="40" width="150" height="40" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="6"/>
<text x="255" y="58" fill="var(--ink)" font-size="11" text-anchor="middle">luminance</text>
<text x="255" y="72" fill="var(--muted)" font-size="10" text-anchor="middle">→ tone curve</text>
<rect x="180" y="130" width="150" height="40" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="255" y="148" fill="var(--ink)" font-size="11" text-anchor="middle">RGB ratios</text>
<text x="255" y="162" fill="var(--muted)" font-size="10" text-anchor="middle">(untouched)</text>
<line x1="330" y1="60" x2="400" y2="95" stroke="var(--s2)" stroke-width="1"/>
<line x1="330" y1="150" x2="400" y2="115" stroke="var(--s1)" stroke-width="1"/>
<rect x="400" y="85" width="120" height="40" fill="var(--panel)" stroke="var(--ink)" stroke-width="1.5" rx="6"/>
<text x="460" y="103" fill="var(--ink)" font-size="11" text-anchor="middle">scale color</text>
<text x="460" y="117" fill="var(--muted)" font-size="10" text-anchor="middle">by L' / L</text>
<line x1="520" y1="105" x2="560" y2="105" stroke="var(--line)" stroke-width="1"/>
<polygon points="560,105 552,100 552,110" fill="var(--line)"/>
<text x="585" y="109" fill="var(--ink)" font-size="11" text-anchor="middle">out</text>
</svg>
^ Brightness and color travel on separate tracks; the curve touches only brightness, and the color is scaled to match.

**Every display-side brightness curve is concave, so the rule generalizes: compress brightness on the luminance, and let the color ride along by a single scale, or the picture loses its color every time you fit it to the screen.**

## Boss fight

Your turn: push the pixel further into HDR and watch the fix reveal its one real cost. Set `pixel` to `[8.0, 2.0, 1.0]` — a much brighter, more saturated highlight — and rerun `--onluminance`. The saturation is still preserved perfectly, but look at the red channel: scaling by the luminance ratio leaves it above 1.0, out of the display's gamut. Preserving the ratios of a very bright saturated color can push a channel past what the screen can show, and now you face a second, genuine decision — clip that channel (which shifts the hue back, reintroducing a smaller version of the desaturation) or desaturate deliberately and gracefully toward white only as much as gamut requires. This is why production tone mappers pair luminance mapping with an explicit gamut step rather than stopping here.

Then try the opposite extreme: a nearly-gray pixel like `[1.0, 0.98, 0.96]`, and compare the two methods' saturations. They barely differ — per-channel desaturation is negligible when the channels are already close, because there is almost no gap to compress. That is the tell for where this bug hides: it is invisible on the muted, near-gray content that fills most test images, and it only bites on the vivid saturated highlights — the sunset, the neon sign, the stained glass — which are exactly the pixels a viewer looks at. A tone mapper can pass every casual check and still wash out the one part of the frame that was supposed to glow.

**The per-channel bug is quietest precisely where colors are dull and loudest where they are vivid, so it survives testing on ordinary images and fails on the highlights that motivated tone mapping in the first place.**

## External resources

Reinhard and colleagues' "Photographic Tone Reproduction for Digital Images" (2002) is the origin of the operator used here and frames tone mapping as an operation on luminance, with color reintroduced by ratio — the exact split this module builds.

The "filmic" and ACES tone-mapping discussions (for example Hable's "Filmic Tonemapping" notes and the ACES documentation) debate per-channel versus luminance-based curves directly, and are the practical companion for why some pipelines still choose per-channel and how they manage the desaturation.

Any color-science reference on chromaticity versus luminance — for instance the Rec.709 luma definition — grounds why the ratios between channels carry hue and saturation while their common scale carries brightness.
