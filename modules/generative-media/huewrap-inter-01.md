---
id: huewrap-inter-01
title: Rotate hue with modular arithmetic, not clamping — a hue pushed past 360° must wrap into the reds, or it sticks at the boundary and collapses
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Hue is the angular coordinate of color — 0° is red, it sweeps through green at 120° and blue at 240°, and at 360° it comes all the way back to red — so it lives on a circle, not a line, and every operation on it is an operation on a circle. Rotating a palette warmer or cooler means turning every hue by some number of degrees around that wheel, which is modular addition: add the rotation and take the result modulo 360, so a hue of 340° rotated by 40° lands at 20° (a warm red-orange), having crossed the 360/0 seam and continued into the low angles — a normal, correct crossing, because the wheel has no edge. The naive mistake is to treat hue as an ordinary bounded number and clamp the sum to its range: then 340 + 40 = 380 is clamped to 360 rather than wrapped to 20, a red-magenta the rotation was supposed to move away from, so the rotation silently stops working for any hue near the top of the range — exactly the reds and magentas. Clamping does a second, worse thing: it is many-to-one at the boundary, so every hue that would rotate past 360 clamps to the same ceiling and distinct colors collapse into one, while wrapping preserves the distinction because the circle has room past the seam. On a fixture rotating four hues by 40°, the two low hues behave the same either way, but 340° and 350° cross the seam: wrapping sends them to 20° and 30° while clamping pins both to 360° — the wrong color and a collision.
eli5: Think of hue as a position on a clock face, where 12 o'clock is red, 4 o'clock is green, 8 o'clock is blue, and going all the way around brings you back to red at 12. If you want to "turn" every color a little, you move the clock hand forward — and when the hand passes 12, it just keeps going into 1, 2, 3, the way a clock always does. The mistake is to treat the clock like a straight ruler that stops at 12: then a hand that should sweep past 12 to 1 o'clock instead gets jammed at 12 and stays there. Worse, two hands that were at 11 and 11:30 both get jammed at 12, so two different colors turn into the exact same one. The fix is to let the hand wrap around the clock like a real clock, so it lands where it should and two different starting colors stay two different colors.
---

## Why this module

Most quantities in image code are linear — a brightness, a coordinate, an alpha — and they live on an interval with a floor and a ceiling, where clamping to the range is the correct way to handle an out-of-bounds result. Hue is not one of those quantities. It is an angle, and angles are periodic: there is no highest hue and no lowest, because 360° and 0° are the same point on the color wheel. Treating a periodic quantity with the linear reflex is where this bug is born.

The distinction is invisible in the middle of the range and only bites at the seam. A hue of 100° rotated by 40° goes to 140° whether you wrap or clamp — nothing crossed the boundary, so both are correct. The two approaches agree everywhere except near 360°, which is exactly why the bug survives casual testing: rotate a few greens and blues and everything looks fine, and only the reds and magentas near the top of the wheel come out wrong.

When the seam is crossed, the linear reflex fails in two distinct ways at once. It puts the hue at the wrong color — pinned at the boundary instead of wrapped around to the low angles — and it destroys information, because many different hues past the seam all clamp to the same ceiling value. This module rotates a set of hues that straddle the seam and shows wrapping and clamping diverging.

**Hue is a periodic angle where 360° equals 0°, so it must be rotated with modular arithmetic; the linear reflex of clamping agrees in the middle of the range but at the seam gives the wrong color and collapses distinct hues into one.**

## Concepts

The governing fact is that hue is a coordinate on a circle, and the only arithmetic that respects a circle is modular. Adding a rotation and taking the result modulo 360 is exactly "turn this far around the wheel and land wherever that is," with the wraparound built in: passing the seam is not an error to be corrected but the normal behavior of going around. Clamping, by contrast, encodes a false belief that the wheel has an edge you can fall off of.

The two failures clamping causes are worth separating because they are different kinds of wrong. The first is a value error: the rotated hue is simply the wrong color, off by however far past the seam it should have gone. That is a visible artifact — a band of reds that refuse to rotate. The second is worse: it is a loss of injectivity. A correct rotation is a bijection on the circle — every input hue maps to exactly one output and every output comes from exactly one input, because rotation just relabels positions on the wheel. Clamping breaks the bijection at the boundary, mapping a whole range of distinct input hues onto the single ceiling value, so distinct colors become identical and the information is gone, not merely displaced.

This generalizes well beyond hue, which is why it is worth internalizing as a shape of bug. Any periodic quantity — a compass bearing, a phase angle, a time of day, a longitude — has the same seam and the same trap, and the same fix: do the arithmetic modulo the period, and never clamp a circular quantity to a linear range. Recognizing a value as periodic is the whole battle; once you see the circle, modular arithmetic is forced.

<svg role="img" aria-label="A line from 0 to 360 with an edge versus a circle where 360 meets 0; clamping treats hue as the line and jams at the edge, wrapping treats it as the circle and continues past the seam" viewBox="0 0 440 140">
<text x="110" y="20" fill="var(--s2)" font-size="9" text-anchor="middle">clamp: line with an edge</text>
<line x1="30" y1="45" x2="190" y2="45" stroke="var(--line)"/>
<text x="30" y="60" fill="var(--muted)" font-size="7" text-anchor="middle">0</text>
<text x="190" y="60" fill="var(--muted)" font-size="7" text-anchor="middle">360</text>
<line x1="190" y1="38" x2="190" y2="52" stroke="var(--s2)"/>
<text x="205" y="49" fill="var(--s2)" font-size="8">jams here</text>
<text x="330" y="20" fill="var(--s1)" font-size="9" text-anchor="middle">wrap: circle, no edge</text>
<circle cx="330" cy="80" r="40" fill="none" stroke="var(--s1)"/>
<line x1="330" y1="40" x2="330" y2="30" stroke="var(--ink)"/>
<text x="330" y="26" fill="var(--muted)" font-size="7" text-anchor="middle">0=360</text>
<path d="M355 48 A 40 40 0 0 1 368 72" fill="none" stroke="var(--s1)" stroke-dasharray="3 2"/>
<text x="330" y="130" fill="var(--muted)" font-size="8" text-anchor="middle">past the seam it continues into the low angles</text>
</svg>
^ Clamping models hue as a line that ends at 360 and jams there; wrapping models the true circle, where passing 360 simply continues into the low angles.

**Modular arithmetic is the only arithmetic that respects a circle, so it makes rotation a bijection with wraparound built in; clamping both lands the wrong color and destroys injectivity — and the trap recurs for every periodic quantity.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/huewrap-inter-01. The fixture is four hue angles and a rotation; two of the hues sit near the seam.

```json filename=modules/generative-media/code/huewrap-inter-01/huewrap.json:3-5 COMPLETE
  "hues": [10, 200, 340, 350],
  "rotation": 40,
  "hue_max": 360
```

The correct rotation adds and takes the modulus, wrapping around the wheel.

```python filename=modules/generative-media/code/huewrap-inter-01/huewrap.py:34-36 COMPLETE
def wrap(hue, rotation, hue_max):
    """Circular rotation: add and take modulo, so the hue wraps around the wheel."""
    return (hue + rotation) % hue_max
```

The naive rotation adds and clamps, treating the wheel as if it had an edge.

```python filename=modules/generative-media/code/huewrap-inter-01/huewrap.py:39-41 COMPLETE
def clamp(hue, rotation, hue_max):
    """Naive rotation: add and clamp to the range, treating the wheel as if it had an edge."""
    return min(hue + rotation, hue_max)
```

A hue crosses the seam when its rotation pushes it to or past 360.

```python filename=modules/generative-media/code/huewrap-inter-01/huewrap.py:44-46 COMPLETE
def crosses_seam(hue, rotation, hue_max):
    """Does this hue's rotation push it past the 360/0 seam?"""
    return hue + rotation >= hue_max
```

Before running it, predict: 10 and 200 stay well inside the range and agree; 340 and 350 cross 360, so wrapping sends them to 20 and 30 while clamping pins them to 360. Run `--rotate`:

```text filename=huewrap.py --rotate
ROTATE — each hue turned by 40 degrees
--------------------------------------------------------
  hue    wrapped   clamped   crosses seam?
  10     50        50        False
  200    240       240       False
  340    20        360       True
  350    30        360       True
```

The prediction holds. The two low hues rotate identically under both methods — no seam crossed. The two high hues cross: wrapping carries 340 to 20 and 350 to 30, warm red-oranges on the far side of the seam, while clamping jams both against 360, a red-magenta, which is not where a 40° turn should land them.

<svg role="img" aria-label="A color wheel with hues 340 and 350 near the top; a 40-degree rotation wraps them across the 0 seam to 20 and 30, while clamping pins them at the 360/0 boundary" viewBox="0 0 440 160">
<circle cx="120" cy="80" r="60" fill="none" stroke="var(--grid)"/>
<line x1="120" y1="20" x2="120" y2="10" stroke="var(--ink)"/>
<text x="120" y="8" fill="var(--muted)" font-size="8" text-anchor="middle">0/360</text>
<circle cx="98" cy="24" r="4" fill="var(--ink)"/>
<text x="86" y="20" fill="var(--muted)" font-size="7">340</text>
<circle cx="140" cy="25" r="4" fill="var(--s1)"/>
<text x="150" y="22" fill="var(--s1)" font-size="7">20 (wrap)</text>
<path d="M100 26 A 60 60 0 0 1 138 26" fill="none" stroke="var(--s1)" stroke-dasharray="3 2"/>
<circle cx="118" cy="20" r="5" fill="var(--s2)"/>
<text x="118" y="44" fill="var(--s2)" font-size="7" text-anchor="middle">clamp: stuck</text>
<text x="300" y="60" fill="var(--ink)" font-size="10" text-anchor="middle">340 + 40 = 380</text>
<text x="300" y="82" fill="var(--s1)" font-size="9" text-anchor="middle">wrap -&gt; 20 (correct)</text>
<text x="300" y="102" fill="var(--s2)" font-size="9" text-anchor="middle">clamp -&gt; 360 (wrong)</text>
</svg>
^ A 40° rotation carries the near-seam hues across 0 into the low reds; clamping instead pins them at the boundary, far from where they belong.

Now the information loss. Run `--collide`:

```text filename=huewrap.py --collide
COLLIDE — hues that cross the seam, clamped vs wrapped
--------------------------------------------------------
  hue 340 -> wrapped 20, clamped 360
  hue 350 -> wrapped 30, clamped 360
  clamped values: [360, 360]  (distinct: 1)
  wrapped values: [20, 30]  (distinct: 2)
```

The prediction holds and sharpens. The two distinct input hues, 340 and 350, both clamp to the single value 360 — two colors collapsed into one, distinct: 1. Wrapping keeps them apart at 20 and 30, distinct: 2. Clamping did not just misplace the colors; it merged them, destroying the difference between two inputs.

<svg role="img" aria-label="Two distinct input hues 340 and 350 map under clamping to a single value 360 (a collision) but under wrapping to two distinct values 20 and 30" viewBox="0 0 440 150">
<text x="60" y="30" fill="var(--ink)" font-size="10" text-anchor="middle">inputs</text>
<text x="60" y="60" fill="var(--ink)" font-size="10" text-anchor="middle">340</text>
<text x="60" y="100" fill="var(--ink)" font-size="10" text-anchor="middle">350</text>
<text x="220" y="20" fill="var(--s2)" font-size="9" text-anchor="middle">clamp</text>
<line x1="80" y1="58" x2="200" y2="76" stroke="var(--s2)"/>
<line x1="80" y1="98" x2="200" y2="80" stroke="var(--s2)"/>
<text x="230" y="82" fill="var(--s2)" font-size="10">360 (collision)</text>
<text x="360" y="20" fill="var(--s1)" font-size="9" text-anchor="middle">wrap</text>
<line x1="80" y1="56" x2="330" y2="55" stroke="var(--s1)"/>
<text x="345" y="58" fill="var(--s1)" font-size="10">20</text>
<line x1="80" y1="100" x2="330" y2="110" stroke="var(--s1)"/>
<text x="345" y="113" fill="var(--s1)" font-size="10">30</text>
</svg>
^ Clamping maps two distinct hues to one boundary value (a many-to-one collision); wrapping keeps them distinct, preserving the bijection.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that some hues cross the seam, that every wrapped hue stays in range, that wrap and clamp disagree on the crossing hues, that clamping collapses distinct crossing hues to one value, and that wrapping keeps them distinct.

```python filename=modules/generative-media/code/huewrap-inter-01/huewrap.py:83-97 COMPLETE
    some_cross = len(crossing) > 0
    print("  some hues cross the 360/0 seam when rotated = %s (%s)" % (some_cross, crossing))

    wrap_in_range = all(0 <= wrap(h, rot, hm) < hm for h in hues)
    print("  every wrapped hue stays in [0, %d) = %s" % (hm, wrap_in_range))

    wrap_differs_from_clamp = any(wrap(h, rot, hm) != clamp(h, rot, hm) for h in crossing)
    print("  wrap and clamp disagree on the crossing hues = %s" % wrap_differs_from_clamp)

    clamped_vals = [clamp(h, rot, hm) for h in crossing]
    clamp_collides = len(set(clamped_vals)) < len(crossing)
    print("  clamping collapses distinct crossing hues to one value = %s (%s)" % (clamp_collides, clamped_vals))

    wrapped_vals = [wrap(h, rot, hm) for h in crossing]
    wrap_keeps_distinct = len(set(wrapped_vals)) == len(crossing)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if wrapping ever leaves the range or clamping ever stops colliding:

```text filename=huewrap.py --check
SELF-TEST — hues that cross 360 wrap to the correct low angles; clamping gives the wrong color and collides
--------------------------------------------------------------------------------------------------------------------
  some hues cross the 360/0 seam when rotated = True ([340, 350])
  every wrapped hue stays in [0, 360) = True
  wrap and clamp disagree on the crossing hues = True
  clamping collapses distinct crossing hues to one value = True ([360, 360])
  wrapping keeps the crossing hues distinct = True ([20, 30])
```

**The self-test asserts both the value error (wrap and clamp disagree) and the injectivity loss (clamp collides while wrap stays distinct) — the two separate ways clamping a circular quantity fails.**

## Definition of done

You can explain why hue is a periodic (circular) quantity and why that makes clamping the wrong reflex for it.
You can state the correct rotation as (hue + rotation) modulo 360 and explain why crossing the seam is normal behavior, not an error.
You can separate the two failures of clamping — landing the wrong color, and collapsing distinct hues — and say why the second destroys information.
You can explain why the bug is invisible in the middle of the range and only appears near the seam.
You can generalize the lesson to other periodic quantities (bearings, phase, time of day) and give the same fix.

## Boss fight

Consider a negative rotation — turning the palette the other way, say −40°, applied to a low hue like 10°. Correct modular arithmetic gives (10 − 40) mod 360 = 330, wrapping backward across the 0 seam into the magentas; the naive clamp gives max(10 − 40, 0) = 0, pinning it at red. So the seam trap is symmetric: it bites at the bottom of the range for negative rotations exactly as it bites at the top for positive ones, and a clamp to [0, 360] fails at both ends. Note also that Python's modulo handles negatives correctly ((−30) % 360 = 330), which is why the modular fix needs no special case for the direction — one operation covers both.

Now consider the endpoint convention, a subtle correctness detail. Hue is usually represented on [0, 360) — 360 excluded, because it is the same point as 0. The wrap operation respects this: (hue + rotation) % 360 can never produce 360, only 0, so the output is always in the half-open range. The clamp, by contrast, produces 360 as a value, which is not even a canonical hue — it is a second name for 0 that some downstream code may not recognize, causing a further mismatch. The lesson tightens: modular arithmetic keeps a circular quantity in its canonical half-open range automatically, while clamping can emit the non-canonical endpoint, so even when clamp happens not to collide it can still produce an out-of-convention value.

**The seam trap is symmetric — clamping fails at 0 for negative rotations as it fails at 360 for positive ones, while one modulo covers both directions; and modulo keeps hue in its canonical [0, 360) range, whereas clamp can emit the non-canonical 360, a second name for 0 that downstream code may mishandle.**

## External resources

Any color-science or graphics reference describing the HSV/HSL hue wheel notes that hue is an angle in [0, 360) and that operations on it are modular.
Discussions of circular (directional) statistics and angle arithmetic generalize this seam problem and its modular fix to bearings, phases, and times.
The topic's own modules on saturation adjustment and on clamping pixel arithmetic cover the neighboring color operations — one that does need the luma anchor, one that does need clamping — against which this circular case is the contrast.
