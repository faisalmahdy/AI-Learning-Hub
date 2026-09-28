---
id: screenblend-inter-01
title: Combine light with the screen operator, not addition — adding two bright layers clips to a flat white
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Compositing a glow, a lens flare, two lamps, or an additive particle effect means combining two layers of light, and the physically honest way is addition — light energy sums, so a + b. The trouble is that a display channel maxes out at 1.0, so any sum above 1.0 is clamped, and a lot of overlaps sum above 1.0; every one of them becomes the same flat 1.0, so bright regions blow out to white and lose their variation and hue, and two genuinely different bright overlaps become indistinguishable. The screen operator, 1 − (1 − a)(1 − b), has three properties addition lacks: it brightens (the result is at least as bright as the brighter input, so light still accumulates), it stays in range (it approaches 1 as the inputs approach 1 but never exceeds it), and it is commutative (screen(a, b) = screen(b, a), so layer order does not matter — unlike the alpha "over" operator, which occludes and is order-dependent). On the fixture a warm layer [0.70, 0.40, 0.20] and a cool layer [0.60, 0.50, 0.90] overlap: added, the red channel is 1.30 and the blue 1.10, both clamped to 1.0, so the overlap is a blown-out near-white [1.00, 0.90, 1.00]; screened, the same overlap is [0.88, 0.70, 0.92] — brighter than either layer, every channel below 1.0, the color preserved. And two different additive sums, 0.70 + 0.60 and 0.90 + 0.80, both clamp to 1.0 and collapse to the same value, while screen keeps them 0.88 and 0.98. The rule: addition is the right physics but the wrong operator for a bounded display, and screen is the bounded brightening that keeps bright-on-bright distinct and order-free.
eli5: Imagine shining two colored flashlights on the same wall. In real life the spot where both hit gets brighter, but you can still see it has a color. If a computer just adds the two lights together, the bright overlap can go past the brightest the screen can show, so it gets chopped off at pure white — and every bright overlap, no matter how different, turns into the same blank white blob. A smarter recipe called "screen" makes the overlap brighter too, but it eases toward white instead of slamming into it, so it never chops anything off and the color stays. It also does not care which flashlight you count first, which is right, because two lights on a wall have no front or back.
---

## Why this module

Any effect made of light stacked on light — bloom, glow, flares, sparks, headlights through fog — has to answer one question: how do two light layers combine into one. The intuitive answer, and the one that matches physics, is to add them, because that is what light does.

That answer is right about the world and wrong about the buffer. The world has no upper limit on brightness; an 8-bit or float-clamped image channel stops at 1.0. So the honest physical sum runs off the top of the range exactly where the effect is most visible — the bright cores — and the clamp flattens all of them to the same white. The fix is an operator that brightens like light but respects the ceiling.

**Addition is the correct physics and the wrong operator for a bounded display; the bright overlaps it produces are exactly the ones the clamp destroys.**

## Concepts

Additive blend is a + b per channel. Below the ceiling it behaves perfectly: two dim lights sum to a brighter one. At the ceiling it fails, because the display clamps every channel to 1.0, and clamping is lossy — it maps every value at or above 1.0 to the same 1.0. Two overlaps that summed to 1.3 and 1.7 both become 1.0, so the brightest, most important regions lose all their structure and turn into a flat white blob. Worse, a colored overlap clips per channel, so a warm-plus-cool region whose channels each cross 1.0 comes out near-white, its hue gone.

The screen operator is 1 − (1 − a)(1 − b). Read it as: invert both layers, multiply, invert back. Multiplying two numbers in [0, 1] gives a smaller number, and the double inversion turns that into brightening. Three things fall out. It brightens — screen(a, b) is at least as large as the larger of a and b, so light accumulates. It never leaves the range — since (1 − a) and (1 − b) are in [0, 1], their product is too, so the result is in [0, 1] by construction; it approaches 1 but cannot reach past it. And it is commutative, because multiplication is, so the order of the two layers does not matter.

That last property is the quiet one. The alpha "over" operator is not commutative — it puts one layer in front and occludes the other — which is correct for opaque objects with a front-to-back order and wrong for light sources, which have none. Two lamps illuminating the same wall should give the same result whichever you list first, and screen does; over does not.

**Screen brightens toward 1 without crossing it and does not care about layer order, which is exactly the behavior light needs and neither addition nor over provides.**

<svg role="img" aria-label="A warm layer and a cool layer, and their overlap under two operators. The additive overlap is a near-white swatch with its channels clamped. The screen overlap is a brighter but still tinted swatch with all channels in range." viewBox="0 0 460 150">
<rect x="0" y="0" width="460" height="150" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">the same warm+cool overlap under each operator</text>
<rect x="40" y="40" width="60" height="40" fill="var(--s1)"></rect>
<text x="40" y="98" fill="var(--muted)" font-size="9">warm A</text>
<rect x="110" y="40" width="60" height="40" fill="var(--s2)"></rect>
<text x="110" y="98" fill="var(--muted)" font-size="9">cool B</text>
<rect x="230" y="40" width="80" height="40" fill="var(--panel)" stroke="var(--line)"></rect>
<text x="234" y="64" fill="var(--ink)" font-size="9">additive</text>
<text x="230" y="98" fill="var(--s1)" font-size="9">[1.00,0.90,1.00] blown out</text>
<rect x="340" y="40" width="80" height="40" fill="var(--s2)"></rect>
<text x="344" y="64" fill="var(--panel)" font-size="9">screen</text>
<text x="330" y="98" fill="var(--s2)" font-size="9">[0.88,0.70,0.92] tinted</text>
<text x="40" y="130" fill="var(--ink)" font-size="10">additive clamps two channels to white; screen keeps all three in range</text>
</svg>
^ Additive pins the red and blue channels to 1.0, so the warm-cool overlap reads as a flat near-white; screen keeps every channel below 1.0, so the overlap stays a bright but recognizably colored value.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/generative-media/code/screenblend-inter-01/screenblend.py

The fixture overlaps a warm layer and a cool layer, both in normalized RGB.

```json filename=modules/generative-media/code/screenblend-inter-01/screenblend.json:3-6 COMPLETE
  "layer_a": [0.7, 0.4, 0.2],
  "layer_b": [0.6, 0.5, 0.9],
  "collide_pair_1": [0.7, 0.6],
  "collide_pair_2": [0.9, 0.8]
```

Additive blend sums the channels, then the display clamps.

```python filename=modules/generative-media/code/screenblend-inter-01/screenblend.py:28-30 COMPLETE
def add_raw(a, b):
    """Plain additive blend, before the display clamps it: light energy sums."""
    return [x + y for x, y in zip(a, b)]
```

```python filename=modules/generative-media/code/screenblend-inter-01/screenblend.py:33-35 COMPLETE
def clamp(v):
    """What the display actually stores: every channel pinned into 0..1."""
    return [min(1.0, max(0.0, x)) for x in v]
```

```text filename=screenblend.py --additive
ADDITIVE — add the two light layers, then clamp to the display range
----------------------------------------------------------------
  layer A     = [0.70, 0.40, 0.20]
  layer B     = [0.60, 0.50, 0.90]
  a + b (raw) = [1.30, 0.90, 1.10]
  clamped     = [1.00, 0.90, 1.00]   <- channels over 1.0 are pinned to white
----------------------------------------------------------------
  the bright overlap blows out; the amount of light above 1.0 is thrown away
```

The raw sum is [1.30, 0.90, 1.10]; the red and blue channels are over the ceiling and clamp to 1.00, leaving [1.00, 0.90, 1.00] — a near-white with its warm-cool character crushed out. The 0.30 of red and 0.10 of blue above the ceiling are simply gone.

Screen replaces that with the bounded operator.

```python filename=modules/generative-media/code/screenblend-inter-01/screenblend.py:38-40 COMPLETE
def screen(a, b):
    """The screen operator, 1 - (1-a)(1-b): brightens toward 1 without ever exceeding it."""
    return [1.0 - (1.0 - x) * (1.0 - y) for x, y in zip(a, b)]
```

```text filename=screenblend.py --screen
SCREEN — 1 - (1-a)(1-b): brighten without leaving the range
----------------------------------------------------------------
  layer A = [0.70, 0.40, 0.20]
  layer B = [0.60, 0.50, 0.90]
  screen  = [0.88, 0.70, 0.92]   <- brighter than either, every channel below 1.0
  screen(b, a) = [0.88, 0.70, 0.92]   (order does not matter)
----------------------------------------------------------------
  light accumulates and stays in range, so the overlap keeps its color
```

The screened overlap is [0.88, 0.70, 0.92] — brighter than either input in every channel, but all below 1.0, so the warm-cool structure survives as a bright, still-colored value. And screen(b, a) is identical, confirming the order-independence that light needs.

<svg role="img" aria-label="Two response curves of output brightness versus summed input. The additive curve rises linearly then flattens hard at 1.0 with a corner where it clips. The screen curve rises and bends smoothly, approaching 1.0 without ever reaching a hard corner." viewBox="0 0 460 180">
<rect x="0" y="0" width="460" height="180" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">output vs combined input: additive clips, screen eases</text>
<line x1="50" y1="150" x2="430" y2="150" stroke="var(--line)"></line>
<line x1="50" y1="40" x2="50" y2="150" stroke="var(--line)"></line>
<line x1="50" y1="45" x2="430" y2="45" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="434" y="48" fill="var(--muted)" font-size="9">1.0</text>
<polyline points="50,150 210,45 430,45" fill="none" stroke="var(--s1)"></polyline>
<text x="150" y="92" fill="var(--s1)" font-size="9">additive (clamps hard)</text>
<path d="M50 150 Q 210 60 430 50" fill="none" stroke="var(--s2)"></path>
<text x="300" y="90" fill="var(--s2)" font-size="9">screen (eases to 1)</text>
</svg>
^ Additive rises straight then hits the ceiling with a corner — everything past that corner is flattened to white; screen bends toward the ceiling and approaches it without ever clamping, so bright values stay distinct.

## Build

The collapse is the sharpest way to see the loss: two different overlaps that additive makes identical.

```python filename=modules/generative-media/code/screenblend-inter-01/screenblend.py:81-88 COMPLETE
    additive_clips = any(x > 1.0 for x in raw)
    print("  additive sum exceeds 1.0 and must be clamped = %s (raw %s)" % (additive_clips, _fmt(raw)))

    screen_in_range = all(0.0 <= x <= 1.0 for x in s)
    print("  screen result stays within 0..1 (never clips) = %s (%s)" % (screen_in_range, _fmt(s)))

    screen_brightens = all(s[i] >= max(a[i], b[i]) - 1e-9 for i in range(len(s)))
    print("  screen is at least as bright as the brighter layer (light accumulates) = %s" % screen_brightens)
```

```text filename=screenblend.py --check
SELF-TEST — additive clips while screen never does, screen still brightens and is commutative, and additive collapses distinct overlaps that screen keeps apart
----------------------------------------------------------------------------------------------------------------
  additive sum exceeds 1.0 and must be clamped = True (raw [1.30, 0.90, 1.10])
  screen result stays within 0..1 (never clips) = True ([0.88, 0.70, 0.92])
  screen is at least as bright as the brighter layer (light accumulates) = True
  screen is commutative, so layer order does not matter = True
  two distinct overlaps collapse to the same clamped value but stay distinct under screen = True (add 1.00==1.00, screen 0.88 vs 0.98)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  additive_clips=True  screen_in_range=True  screen_brightens=True  screen_commutative=True  additive_collapses=True
```

<svg role="img" aria-label="Two overlaps, 0.7+0.6 and 0.9+0.8. Under additive both clamp to the same bar at 1.0. Under screen they are two different bars, 0.88 and 0.98." viewBox="0 0 460 160">
<rect x="0" y="0" width="460" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">two different overlaps: additive merges them, screen keeps them</text>
<line x1="50" y1="130" x2="430" y2="130" stroke="var(--line)"></line>
<line x1="50" y1="42" x2="430" y2="42" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="434" y="45" fill="var(--muted)" font-size="9">1.0</text>
<text x="95" y="146" fill="var(--muted)" font-size="9">additive</text>
<rect x="70" y="42" width="30" height="88" fill="var(--s1)"></rect>
<text x="66" y="38" fill="var(--s1)" font-size="9">1.00</text>
<rect x="110" y="42" width="30" height="88" fill="var(--s1)"></rect>
<text x="106" y="38" fill="var(--s1)" font-size="9">1.00</text>
<text x="300" y="146" fill="var(--muted)" font-size="9">screen</text>
<rect x="280" y="52" width="30" height="78" fill="var(--s2)"></rect>
<text x="276" y="48" fill="var(--s2)" font-size="9">0.88</text>
<rect x="320" y="44" width="30" height="86" fill="var(--s2)"></rect>
<text x="316" y="40" fill="var(--s2)" font-size="9">0.98</text>
</svg>
^ The two additive bars are the same height (both clamped to 1.0) — the overlaps are now indistinguishable; the two screen bars differ (0.88 vs 0.98), preserving that one overlap was brighter than the other.

**additive_collapses is the loss made concrete: clamping is many-to-one, so it does not just cap brightness, it erases the differences between everything above the cap.**

## Definition of done

You can explain why addition is physically correct yet wrong for a bounded buffer — the sum is right, but the clamp that follows is lossy and hits exactly the bright regions the effect cares about.

You can write the screen operator and read its three guarantees off the algebra: it brightens, it stays in [0, 1] by construction, and it is commutative.

You can say why commutativity matters for light and why the alpha "over" operator is the wrong choice here — over occludes and is order-dependent, which suits opaque layers, not light sources.

You can describe the failure mode precisely: clamping is many-to-one, so additive blow-out does not merely cap brightness, it collapses distinct bright overlaps to the same white and destroys hue.

## Boss fight

Your engine renders glow by drawing each light sprite with additive blending. It looks great for sparse scenes, but in a dense fight — many overlapping muzzle flashes and explosions — the screen turns into a wall of featureless white, and artists complain they cannot see the action.

First: explain why the problem appears only when many lights overlap, in terms of how additive interacts with the clamp. Roughly how many mid-brightness sprites need to stack before a channel saturates, and what happens to every sprite added after that?

Then: switching those sprites to screen blending keeps them in range. But screen has its own character — stack many screen layers and the result creeps toward white and compresses. Contrast how additive and screen each behave as you pile on 2, 5, 20 layers, and say which failure is easier for artists to work with and why.

Finally: some engines keep additive blending but render to an HDR buffer (values allowed above 1.0) and tone-map at the end. Explain how that fixes the blow-out that plain additive-to-an-8-bit-buffer suffers, and what screen is really standing in for when you cannot afford an HDR pipeline.

## External resources

The Porter-Duff and Photoshop blend-mode references define screen alongside multiply and overlay with the exact formula 1 − (1 − a)(1 − b); reading screen and multiply as inverses of each other is the fastest way to remember what each does to brightness.

Any real-time rendering discussion of bloom and HDR (for example the bloom chapters in GPU Gems) frames this module's tradeoff directly: additive light in an HDR buffer with tone-mapping versus bounded operators like screen when the pipeline is limited to a low-dynamic-range target.
