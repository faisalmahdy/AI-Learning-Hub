---
id: huelerp-inter-01
title: Interpolate hue along the shorter arc around the color wheel — a linear lerp of the two angle numbers takes the long way and sweeps through the opposite color
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Hue is an angle in [0, 360) and the wheel wraps at that seam — 0 and 360 are the same red — so between any two hues there are two arcs that sum to 360, a short one and a long one, and a gradient between two colors should follow the shorter arc, the way the colors are actually near each other on the wheel. Linear interpolation of the raw angle numbers, start + t·(end − start), does not know about the wrap: it walks the number line from one value to the other, which is correct when both hues are on the same side of the seam but wrong when they straddle it. For 350 (red) and 20 (a warm red-orange), only 30 degrees apart going through red, the raw difference is 20 − 350 = −330, so the naive lerp sweeps 330 degrees the long way — down through magenta, blue, cyan, green — and its midpoint lands near 185, a cyan, the near-complement of both endpoints instead of a color between them. The fix computes the signed shortest angular step: if end − start exceeds 180 or is below −180, add or subtract 360 so the step is at most 180 degrees, interpolate along that shorter arc, and wrap each result back into [0, 360). On the 350-to-20 fixture the naive lerp sweeps 330 degrees with midpoint 185 (cyan) while the shortest-arc lerp sweeps 30 degrees with midpoint 5 (red) — the two midpoints are a full 180 degrees apart.
eli5: Picture a circular clock face where the colors live, with red sitting right at the top straddling twelve o'clock. You want to fade from a color just before twelve to a color just after twelve — a tiny hop across the top through red. But if you fade by just counting down the numbers from 11:50 to 12:20 as if they were a straight ruler, you go the wrong way all the way around the clock — down past 6 o'clock — and halfway through you are at the very bottom, showing the opposite color instead of red. The fix is to notice the two points are actually neighbors across the top and take the short hop, wrapping past twelve, so the fade stays in the reds the whole way. Colors on a wheel need the short way around, not straight-line counting.
---

## Why this module

Fading one color into another sounds like the simplest thing in graphics: take the start value, take the end value, and slide a fraction of the way from one to the other. For most quantities that is exactly right — brightness, position, opacity all live on a straight line, and linear interpolation between two points on a line is unambiguous.

Hue is not on a line. It is an angle on the color wheel, running 0 to 360 and then wrapping back to 0, because 0 degrees and 360 degrees are the same red. That wrap changes everything about interpolation: between two hues there are now two ways to get from one to the other — a short arc and a long arc that together go all the way around — and a color gradient almost always means the short one, because that is the sense in which the two colors are close.

The trap is that linear interpolation of the raw angle numbers still runs without error and still looks right much of the time. As long as both hues sit on the same side of the 0/360 seam, walking the number line and walking the short arc are the same walk. The bug only appears when the two hues straddle the seam — and then the naive lerp cheerfully walks the long way around, through colors on the far side of the wheel, and the midpoint of a red-to-red fade comes out cyan.

<svg role="img" aria-label="On the left a straight number line from 0 to 360 with 350 near the right end and 20 near the left end, far apart, with an arrow sweeping the whole width between them. On the right the same two hues drawn on a circle where they sit right next to each other across the top seam, a short arc between them." viewBox="0 0 440 150">
<text x="110" y="18" fill="var(--muted)" font-size="9" text-anchor="middle">as a number line: far apart</text>
<line x1="20" y1="60" x2="210" y2="60" stroke="var(--line)"/>
<text x="20" y="76" fill="var(--muted)" font-size="8" text-anchor="middle">0</text>
<text x="210" y="76" fill="var(--muted)" font-size="8" text-anchor="middle">360</text>
<circle cx="30" cy="60" r="3" fill="var(--s1)"/>
<text x="30" y="48" fill="var(--s1)" font-size="8" text-anchor="middle">20</text>
<circle cx="205" cy="60" r="3" fill="var(--s2)"/>
<text x="196" y="48" fill="var(--s2)" font-size="8" text-anchor="middle">350</text>
<path d="M30 100 L 205 100" fill="none" stroke="var(--muted)" stroke-dasharray="3 3"/>
<text x="115" y="114" fill="var(--muted)" font-size="8" text-anchor="middle">naive walks the whole way</text>
<text x="345" y="18" fill="var(--muted)" font-size="9" text-anchor="middle">on the wheel: neighbors</text>
<circle cx="345" cy="80" r="45" fill="none" stroke="var(--line)"/>
<line x1="345" y1="80" x2="345" y2="35" stroke="var(--grid)"/>
<text x="345" y="30" fill="var(--muted)" font-size="7" text-anchor="middle">0 / 360</text>
<circle cx="337" cy="36" r="3" fill="var(--s2)"/>
<text x="315" y="40" fill="var(--s2)" font-size="8">350</text>
<circle cx="353" cy="36" r="3" fill="var(--s1)"/>
<text x="368" y="40" fill="var(--s1)" font-size="8">20</text>
</svg>
^ The same two hues: on a straight number line 350 and 20 sit at opposite ends, but on the wheel they are neighbors across the top seam — interpolation must respect the wheel, not the line.

**Hue is a circular angle, so between two hues there are a short arc and a long arc; a gradient means the short arc, but linear interpolation of the raw angle numbers walks the number line — right when both hues share a side of the seam, wrong when they straddle it.**

## Concepts

Fix the picture of the wheel. Zero is at the top; hue increases clockwise through red, yellow, green, cyan, blue, magenta, and back to red at 360. Two hues cut the circle into two arcs whose lengths add to 360. For 350 and 20 the short arc is the 30 degrees straight across the top through red; the long arc is the other 330 degrees, sweeping down one side, across the bottom through cyan, and up the other.

The naive lerp picks its arc by accident, based on the sign and size of the raw difference end − start. When that difference is small the walk is short and correct. When the two hues straddle the seam the raw difference is large — 20 − 350 is −330 — so the walk is long, and it heads off in the direction that passes through every color on the far side of the wheel. Nothing in the arithmetic knows the endpoints were meant to be close.

<svg role="img" aria-label="A color wheel with two points at 350 and 20 near the top. A short arc of 30 degrees across the top through red is marked as the intended path; a long arc of 330 degrees going down and around through the bottom is marked as the naive path passing through cyan." viewBox="0 0 440 170">
<circle cx="220" cy="90" r="65" fill="none" stroke="var(--line)"/>
<text x="220" y="20" fill="var(--muted)" font-size="8" text-anchor="middle">0 / 360 (red)</text>
<text x="220" y="168" fill="var(--muted)" font-size="8" text-anchor="middle">180 (cyan)</text>
<circle cx="209" cy="27" r="3" fill="var(--s2)"/>
<text x="176" y="30" fill="var(--s2)" font-size="8">350</text>
<circle cx="231" cy="27" r="3" fill="var(--s1)"/>
<text x="248" y="30" fill="var(--s1)" font-size="8">20</text>
<path d="M209 27 A 65 65 0 0 1 231 27" fill="none" stroke="var(--s1)" stroke-width="2"/>
<text x="220" y="48" fill="var(--s1)" font-size="8" text-anchor="middle">short 30&#176;</text>
<path d="M209 27 A 65 65 0 1 0 231 27" fill="none" stroke="var(--s2)" stroke-dasharray="4 3"/>
<text x="220" y="120" fill="var(--s2)" font-size="8" text-anchor="middle">naive: long 330&#176;</text>
</svg>
^ The 30-degree short arc across the top stays in the reds; the naive lerp takes the 330-degree long arc down through the bottom of the wheel, passing through cyan.

The fix is to choose the arc deliberately by computing the signed shortest angular step. Take delta = end − start; if it is more than 180 degrees, subtract 360, and if it is less than −180 degrees, add 360. That folds the step into the range from −180 to 180 — always the shorter arc, with a sign that says which way to turn. For 350 to 20, delta = −330 becomes +30: a small positive step, clockwise across the top.

Then interpolate along that step, start + t·delta, and wrap each result back into [0, 360) so a value like 365 becomes 5. The gradient now sweeps the 30-degree short arc and stays red throughout. The same wrap-aware step handles every case — same-side pairs get an unchanged small delta, straddling pairs get the corrected one — so it is simply the correct way to interpolate any angle.

**Compute the signed shortest step — fold end − start into [−180, 180] by adding or subtracting 360 — interpolate along it, and wrap the result back into [0, 360); this takes the short arc in every case, while the raw difference takes whichever arc its unadjusted size happens to name.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/huelerp-inter-01. The fixture is two hues that straddle the seam and a step count for the gradient.

```json filename=modules/generative-media/code/huelerp-inter-01/huelerp.json:3-5 COMPLETE
  "start_hue": 350,
  "end_hue": 20,
  "steps": 5
```

Wrapping a hue back into range is a modulo — a value of 365 is 5, and −10 is 350.

```python filename=modules/generative-media/code/huelerp-inter-01/huelerp.py:30-32 COMPLETE
def wrap360(h):
    """Bring a hue angle back into [0, 360)."""
    return h % 360
```

The signed shortest step folds the raw difference into the range from −180 to 180, so it is always the shorter arc with a direction.

```python filename=modules/generative-media/code/huelerp-inter-01/huelerp.py:35-42 COMPLETE
def shortest_delta(start, end):
    """Signed shortest angular step from start to end, in (-180, 180]."""
    delta = end - start
    while delta > 180:
        delta -= 360
    while delta < -180:
        delta += 360
    return delta
```

The two interpolations differ by exactly one thing: the naive one steps by the raw difference, the correct one steps by the shortest delta. Both wrap the result.

```python filename=modules/generative-media/code/huelerp-inter-01/huelerp.py:45-52 COMPLETE
def naive_lerp(start, end, t):
    """Linear interpolation of the raw angle numbers -- ignores the wrap."""
    return wrap360(start + t * (end - start))


def arc_lerp(start, end, t):
    """Interpolation along the shorter arc -- steps by the signed shortest delta, then wraps."""
    return wrap360(start + t * shortest_delta(start, end))
```

Before running it, predict: a fade from red 350 to red 20 should stay red, so its midpoint should be a red hue near the top of the wheel, not near 180. Run `--interp`:

```text filename=huelerp.py --interp
INTERP — gradient from hue 350 to hue 20 in 5 steps
----------------------------------------------------
  t       naive lerp     shortest-arc
  0.00    350.0          350.0
  0.25    267.5          357.5
  0.50    185.0          5.0
  0.75    102.5          12.5
  1.00    20.0           20.0
----------------------------------------------------
  naive swings to the far side of the wheel; shortest-arc stays in the reds
```

The prediction holds for one column and fails for the other. Both agree at the endpoints — 350 and 20 — because at t=0 and t=1 there is no interpolation to get wrong. In between they diverge completely: the naive column walks 350, 267.5, 185, 102.5, 20 — down through magenta and blue to cyan at the midpoint and back up through green — while the shortest-arc column walks 350, 357.5, 5, 12.5, 20, a tight sweep across the top that never leaves the reds. Same endpoints, opposite journeys.

The midpoint is the cleanest way to see the size of the error. Run `--arc`:

```text filename=huelerp.py --arc
ARC — the two paths from hue 350 to hue 20
----------------------------------------------------
  naive lerp arc length     = 330 degrees (the long way)
  shortest-arc length       = 30 degrees (the short way)
  naive midpoint (t=0.5)    = 185.0
  shortest-arc midpoint     = 5.0
----------------------------------------------------
  the two arcs sum to 360; the shorter one is the gradient you meant
```

The two arcs are 330 and 30, summing to 360 as they must. The naive midpoint is 185 — a cyan, almost exactly the complementary color of the reds at the endpoints — while the shortest-arc midpoint is 5, a red sitting right between 350 and 20. The naive fade does not just take a slightly wrong path; halfway through, it shows the opposite color.

<svg role="img" aria-label="A color wheel showing the two midpoints of a fade from 350 to 20. The shortest-arc midpoint at 5 degrees sits at the top near red, between the endpoints; the naive midpoint at 185 degrees sits at the bottom near cyan, the opposite side of the wheel." viewBox="0 0 440 175">
<circle cx="220" cy="90" r="65" fill="none" stroke="var(--line)"/>
<circle cx="209" cy="27" r="2.5" fill="var(--muted)"/>
<text x="182" y="26" fill="var(--muted)" font-size="7">350</text>
<circle cx="231" cy="27" r="2.5" fill="var(--muted)"/>
<text x="240" y="26" fill="var(--muted)" font-size="7">20</text>
<circle cx="220" cy="25" r="4" fill="var(--s1)"/>
<text x="220" y="14" fill="var(--s1)" font-size="8" text-anchor="middle">short midpoint 5 (red)</text>
<circle cx="220" cy="155" r="4" fill="var(--s2)"/>
<text x="220" y="172" fill="var(--s2)" font-size="8" text-anchor="middle">naive midpoint 185 (cyan)</text>
<line x1="220" y1="25" x2="220" y2="155" stroke="var(--grid)" stroke-dasharray="2 3"/>
</svg>
^ The two fades' midpoints land on opposite sides of the wheel: the shortest-arc midpoint is a red between the endpoints, the naive midpoint is the near-complementary cyan.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the naive arc is more than half the wheel, that the shortest arc is at most 180 and shorter than the naive one, that the naive midpoint is far from both endpoints, that the shortest-arc midpoint sits within the short arc of both, and that the two midpoints are on opposite sides of the wheel.

```python filename=modules/generative-media/code/huelerp-inter-01/huelerp.py:101-116 COMPLETE
    naive_goes_long_way = naive_arc > 180
    print("  naive lerp walks more than half the wheel = %s (%.0f degrees)" % (naive_goes_long_way, naive_arc))

    short_arc_is_short = short_arc <= 180 and short_arc < naive_arc
    print("  shortest-arc stays on the short side = %s (%.0f degrees)" % (short_arc_is_short, short_arc))

    naive_mid = naive_lerp(start, end, 0.5)
    naive_midpoint_far = min(circular_distance(naive_mid, start), circular_distance(naive_mid, end)) > 90
    print("  naive midpoint is far from both endpoints = %s (mid %.1f, nearest endpoint %.0f away)"
          % (naive_midpoint_far, naive_mid, min(circular_distance(naive_mid, start), circular_distance(naive_mid, end))))

    short_mid = arc_lerp(start, end, 0.5)
    short_midpoint_between = (circular_distance(short_mid, start) <= short_arc
                             and circular_distance(short_mid, end) <= short_arc)
    print("  shortest-arc midpoint sits between the endpoints = %s (mid %.1f, %.0f from each)"
          % (short_midpoint_between, short_mid, circular_distance(short_mid, start)))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the naive path ever stopped taking the long way or the shortest-arc midpoint ever drifted off the short arc:

```text filename=huelerp.py --check
SELF-TEST — the naive lerp takes the long way and its midpoint lands near the opposite color; the shortest-arc lerp stays on the short arc
----------------------------------------------------------------------------------------------------------------
  naive lerp walks more than half the wheel = True (330 degrees)
  shortest-arc stays on the short side = True (30 degrees)
  naive midpoint is far from both endpoints = True (mid 185.0, nearest endpoint 165 away)
  shortest-arc midpoint sits between the endpoints = True (mid 5.0, 15 from each)
  the two midpoints are on opposite sides of the wheel = True (180 apart)
```

**The self-test measures the error by distance on the wheel, not by the raw angle difference — checking the naive midpoint is over 90 degrees from both endpoints and the two midpoints are 180 apart — so a pass certifies the naive path is genuinely on the far side, not merely numerically different.**

## Definition of done

You can explain why hue is a circular quantity and why that gives two arcs between any two hues.
You can explain why linear interpolation of the raw angle numbers is correct for same-side hues but wrong for hues that straddle the 0/360 seam.
You can compute the signed shortest angular step by folding the raw difference into [−180, 180] and say why that always picks the short arc.
You can explain why the result must be wrapped back into [0, 360) after each step.
You can predict that a naive fade between seam-straddling hues passes through the near-complementary color at its midpoint.

## Boss fight

Consider two hues that are exactly 180 degrees apart — say 0 (red) and 180 (cyan). Reason about what the shortest-arc method does. The signed delta is +180 (or equivalently −180; the fold leaves 180 as the boundary case), so there is no shorter arc — both ways around are 180 degrees, and the method picks one consistently by its sign convention. This is the one input where "the shorter arc" is genuinely ambiguous, and any hue interpolator has to make an arbitrary but consistent choice; the lesson is that the ambiguity is real and inherent to the wheel, not a bug, so you decide the tie-break deliberately (for example, always clockwise) rather than letting floating-point noise flip it per pixel and produce a seam in a gradient.

Now the deeper trap: hue alone is not a color. A hue near the gray axis — very low saturation or very low value — barely differs from any other hue, so interpolating hue there is nearly meaningless and can introduce visible swings for no perceptual reason. The robust move is to interpolate in a space where the fade is actually straight: convert both endpoints to a Cartesian representation such as RGB, or to a perceptual space like Oklab, and lerp the coordinates there, which handles the circular-hue problem and the low-saturation problem at once because the wheel's wrap is baked into the geometry. Shortest-arc hue interpolation is the right fix when you must stay in HSV or HSL; when you can choose the space, interpolating in a linear or perceptual color space is better still.

**At exactly 180 degrees apart the shorter arc is genuinely ambiguous, so pick a consistent tie-break rather than letting noise decide; and because hue is meaningless near the gray axis, interpolating in RGB or a perceptual space like Oklab avoids both the wrap and the low-saturation trap when you are free to choose the space.**

## External resources

The HSV and HSL color-model references (for example the Wikipedia articles) describe hue as an angle and note that interpolation must go around the wheel.
Björn Ottosson's writing on the Oklab color space explains why interpolating in a perceptual space gives more even gradients than interpolating hue directly.
The topic's own module on rotating hue with modular arithmetic covers the neighboring case — a single hue pushed past the seam — while this one covers interpolating between two hues.
