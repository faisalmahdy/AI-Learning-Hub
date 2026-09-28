---
id: aspectfit-inter-01
title: Fit an image into a box with one uniform scale — resizing to the box's exact width and height stretches it
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: Almost every thumbnail, avatar, and preview path has one line that says "make this image target_w by target_h", and the obvious implementation resizes to exactly those dimensions — scale the width by target_w/src_w and the height by target_h/src_h. When the source and the target share an aspect ratio (width over height) those two factors are equal and nothing goes wrong. When they differ — a 4:3 photo into a square box — the factors differ, each axis is scaled by a different amount, and the image is squashed on one axis and stretched on the other. Nothing errors: the file comes out at exactly the requested size. But a circle has become an ellipse and a face is fat or thin. On the fixture an 800x600 source (aspect 1.333) forced into a 400x400 box scales x by 0.500 and y by 0.667, so the output is 400x400 at aspect 1.000 and a source circle of radius 100 becomes an ellipse with semi-axes 50 and 67. The fix is to choose one scale for both axes and then decide what to do with the box's leftover space: fit (contain) uses the smaller scale, min(0.500, 0.667) = 0.500, so the image lands inside at 400x300 with 100px of letterbox padding and the circle stays round; cover (fill) uses the larger scale, max = 0.667, so the box is filled at 533x400 and 133px of overflow is cropped, again keeping the circle round. Both preserve the shape; they trade padding against cropping. The rule is that a resize to a box of a different aspect ratio is never a single "set both dimensions" call — it is one uniform scale plus a padding-or-crop decision.
eli5: If you have a wide photo and a square frame, and you shove the photo to fill the frame exactly, you squash it — everyone in it gets short and fat, and a round clock becomes an oval. The photo is the right size and the wrong shape, and the computer thinks it did the job. To keep everyone their real shape you have to shrink the photo by the same amount side-to-side as top-to-bottom, and then either leave blank bars where it doesn't reach the edges, or let it spill past the frame and trim the spill. Same-amount-both-ways is the whole trick; bars or trimming is just what you do with the space left over.
---

## Why this module

The most common image operation in any product is "make this fit here" — a photo into a thumbnail grid, an upload into an avatar circle, a frame into a video slot. The most common way to write it is the one that reads straight off the requirement: the slot is 400 by 400, so resize the image to 400 by 400.

That line is a bug whenever the image and the slot are different shapes. It does produce a 400x400 image, so it passes every check that looks at the output size, and it ships. What it also does is scale the width and the height by different amounts, which stretches the picture — and stretch is the one image defect the eye catches instantly and the code never does.

**A resize into a differently-shaped box is not one operation but two decisions: one scale for both axes, then what to do with the leftover.**

## Concepts

Aspect ratio is width divided by height. An 800x600 photo has aspect 1.333; a 400x400 box has aspect 1.000. Two images look "the same shape" exactly when their aspect ratios match.

Resize-to-fill computes two scale factors — scale_x = target_w / src_w and scale_y = target_h / src_h — and applies each to its own axis. When the aspects match, scale_x equals scale_y and the image is uniformly shrunk. When they differ, so do the factors, and the axes are scaled unequally. That inequality is the distortion: every horizontal distance is multiplied by one number and every vertical distance by another, so anything round becomes oval and anything square becomes rectangular.

The fix is to pick a single scale for both axes. There are two sensible choices, and they differ only in which scale factor they take.

Fit (also called contain) takes the smaller factor, min(scale_x, scale_y). At that scale the image fits entirely inside the box, touching it on the tight axis and falling short on the other, so the short axis gets padding bars — letterboxing.

Cover (also called fill) takes the larger factor, max(scale_x, scale_y). At that scale the image covers the box completely, matching it on one axis and overflowing on the other, so the overflow is cropped.

**Stretch scales the two axes by different numbers; fit and cover scale both by the same number and spend the difference on padding or on a crop.**

<svg role="img" aria-label="A number line of the two candidate scale factors, 0.500 and 0.667, with the smaller one labelled 'min, used by fit' and the larger 'max, used by cover'; stretch is shown using both at once." viewBox="0 0 480 150">
<rect x="0" y="0" width="480" height="150" fill="var(--panel)"></rect>
<text x="12" y="22" fill="var(--ink)" font-size="12">two candidate scales for 800x600 into 400x400</text>
<line x1="60" y1="70" x2="420" y2="70" stroke="var(--line)"></line>
<circle cx="140" cy="70" r="5" fill="var(--s2)"></circle>
<text x="118" y="58" fill="var(--s2)" font-size="11">0.500</text>
<text x="98" y="98" fill="var(--muted)" font-size="10">min &#8594; fit</text>
<circle cx="340" cy="70" r="5" fill="var(--s2)"></circle>
<text x="318" y="58" fill="var(--s2)" font-size="11">0.667</text>
<text x="300" y="98" fill="var(--muted)" font-size="10">max &#8594; cover</text>
<text x="60" y="128" fill="var(--s1)" font-size="10">stretch uses BOTH at once &#8594; unequal axes &#8594; distortion</text>
</svg>
^ scale_x = 400/800 = 0.500 and scale_y = 400/600 = 0.667; fit picks the min, cover the max, and stretch is the mistake of using each on its own axis.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/generative-media/code/aspectfit-inter-01/aspectfit.py

The fixture is just the two rectangles and a circle to watch.

```json filename=modules/generative-media/code/aspectfit-inter-01/aspectfit.json:2-8 COMPLETE
  "_meta": "A source image and a target box of a different aspect ratio, used to show that resizing an image to exactly the target's width and height -- the one-line default of almost every thumbnail and preview path -- stretches it, because forcing both dimensions to the target applies a different scale factor to width and to height whenever the two aspect ratios differ. Aspect ratio is width divided by height; a 800x600 photo is 1.333 and a 400x400 box is 1.000. Resize-to-fill computes scale_x = target_w / src_w and scale_y = target_h / src_h and uses each on its own axis, so when scale_x != scale_y the image is squashed on one axis and stretched on the other: a circle becomes an ellipse, a face gets fat or thin, and nothing errors -- the output is exactly the requested size, just the wrong shape. The fix is to pick ONE uniform scale for both axes so the aspect ratio is preserved, and then decide what to do with the leftover: 'fit' (contain) uses scale = min(scale_x, scale_y) so the whole image lands inside the box with padding bars on the short axis (letterbox), and 'cover' uses scale = max(scale_x, scale_y) so the box is completely filled and the overflow on the long axis is cropped. Both keep the shape; they trade padding against cropping. src_w, src_h and target_w, target_h are the fixture; every scale factor, output dimension, aspect ratio, and the ellipse axes of a unit circle carried through each strategy are computed. Stdlib only.",
  "src_w": 800,
  "src_h": 600,
  "target_w": 400,
  "target_h": 400,
  "circle_radius": 100
}
```

The buggy version forces both dimensions to the target and lets each axis take its own scale.

```python filename=modules/generative-media/code/aspectfit-inter-01/aspectfit.py:36-38 COMPLETE
def stretch(src_w, src_h, tw, th):
    """Resize-to-fill: force both dimensions to the target, so each axis gets its own scale."""
    return {"scale_x": tw / src_w, "scale_y": th / src_h, "out_w": tw, "out_h": th}
```

Run it and the output is exactly the box, and exactly the wrong shape.

```text filename=aspectfit.py --stretch
STRETCH — resize-to-fill: force the image to exactly 400x400
----------------------------------------------------------------
  scale_x = 0.500   scale_y = 0.667   (different per axis)
  output 400x400  aspect 1.000   (source aspect was 1.333)
  the source circle r=100 becomes an ellipse: semi-axes 50 x 67
----------------------------------------------------------------
  exactly the requested size, and the wrong shape -- the aspect ratio changed
```

The x axis shrank to half and the y axis to two thirds, so the circle's horizontal radius dropped to 50 while its vertical radius held at 67 — an ellipse. The aspect ratio moved from 1.333 to 1.000, which is the number a shape-check would catch and a size-check never will.

<svg role="img" aria-label="A round circle of radius 100 on the left, and on the right the same circle after stretch scaling: horizontal radius 50, vertical radius 67, an ellipse wider-looking because the two radii differ." viewBox="0 0 420 180">
<rect x="0" y="0" width="420" height="180" fill="var(--panel)"></rect>
<text x="12" y="22" fill="var(--ink)" font-size="12">a source circle, and the same circle after stretch</text>
<text x="70" y="48" fill="var(--muted)" font-size="11">source r=100</text>
<circle cx="110" cy="115" r="55" fill="none" stroke="var(--s2)"></circle>
<text x="88" y="118" fill="var(--muted)" font-size="10">round</text>
<text x="280" y="48" fill="var(--muted)" font-size="11">stretched</text>
<ellipse cx="310" cy="115" rx="27" ry="37" fill="none" stroke="var(--s1)"></ellipse>
<text x="255" y="150" fill="var(--s1)" font-size="10">rx 50, ry 67 &#8594; ellipse</text>
</svg>
^ Unequal axis scales (0.500 across, 0.667 down) turn the circle's two equal radii into 50 and 67 — the same distortion a face or a logo suffers.

Fit takes the smaller scale so the whole image lands inside the box.

```python filename=modules/generative-media/code/aspectfit-inter-01/aspectfit.py:41-46 COMPLETE
def fit(src_w, src_h, tw, th):
    """Contain: one scale = min(scale_x, scale_y); the whole image lands inside the box."""
    s = min(tw / src_w, th / src_h)
    out_w, out_h = round(src_w * s), round(src_h * s)
    return {"scale": s, "out_w": out_w, "out_h": out_h,
            "pad_w": tw - out_w, "pad_h": th - out_h}
```

```text filename=aspectfit.py --fit
FIT — contain: one scale, the whole image inside the 400x400 box
----------------------------------------------------------------
  scale = min = 0.500   (same on both axes)
  output 400x300  aspect 1.333   padding 0x100 (letterbox bars)
  the source circle r=100 stays a circle: semi-axes 50 x 50
----------------------------------------------------------------
  aspect preserved; the leftover space becomes padding, nothing is cropped
```

One scale, 0.500, on both axes: the output is 400x300, still aspect 1.333, and the circle's two semi-axes are both 50 — round. The image is 100 pixels short of the box's height, and those 100 pixels become the letterbox bars.

Cover takes the larger scale instead, so the image fills the box and the overflow is cropped.

```python filename=modules/generative-media/code/aspectfit-inter-01/aspectfit.py:49-54 COMPLETE
def cover(src_w, src_h, tw, th):
    """Fill: one scale = max(scale_x, scale_y); the box is filled and the overflow is cropped."""
    s = max(tw / src_w, th / src_h)
    out_w, out_h = round(src_w * s), round(src_h * s)
    return {"scale": s, "out_w": out_w, "out_h": out_h,
            "crop_w": out_w - tw, "crop_h": out_h - th}
```

Cover scales by 0.667 to 533x400, which fills the 400-tall box and overruns its width by 133 pixels — those get cropped. The aspect is still 1.333 and the circle is still round. Fit and cover are the same move (one scale, aspect preserved); they differ only in whether the leftover is padding you keep or overflow you trim.

## Build

<svg role="img" aria-label="An 800 by 600 source rectangle with a round circle, shown resized three ways into a 400 by 400 square box: stretched to fill (circle squashed to an ellipse), fit inside with padding bars (circle round), and covering the box with the sides cropped (circle round)." viewBox="0 0 640 200">
<rect x="0" y="0" width="640" height="200" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">source 800x600 (aspect 1.333), box 400x400 (aspect 1.000)</text>
<text x="40" y="48" fill="var(--muted)" font-size="11">stretch</text>
<rect x="40" y="56" width="90" height="90" fill="none" stroke="var(--line)"></rect>
<ellipse cx="85" cy="101" rx="42" ry="30" fill="none" stroke="var(--s1)"></ellipse>
<text x="40" y="164" fill="var(--s1)" font-size="10">aspect 1.000 — oval</text>
<text x="250" y="48" fill="var(--muted)" font-size="11">fit (contain)</text>
<rect x="250" y="56" width="90" height="90" fill="none" stroke="var(--line)"></rect>
<rect x="250" y="56" width="90" height="11" fill="var(--grid)"></rect>
<rect x="250" y="135" width="90" height="11" fill="var(--grid)"></rect>
<circle cx="295" cy="101" r="30" fill="none" stroke="var(--s2)"></circle>
<text x="250" y="164" fill="var(--s2)" font-size="10">aspect 1.333 — padded</text>
<text x="460" y="48" fill="var(--muted)" font-size="11">cover (fill)</text>
<rect x="460" y="56" width="90" height="90" fill="none" stroke="var(--line)"></rect>
<circle cx="505" cy="101" r="30" fill="none" stroke="var(--s2)"></circle>
<line x1="472" y1="56" x2="472" y2="146" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<line x1="538" y1="56" x2="538" y2="146" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="460" y="164" fill="var(--s2)" font-size="10">aspect 1.333 — cropped</text>
</svg>
^ Stretch fills the box by scaling the axes unequally, so the circle ovals; fit and cover both use one scale and keep it round, spending the mismatch on padding bars (fit) or a side crop (cover).

The self-test asserts the whole story at once: stretch changes the aspect and ovals the circle, while fit and cover both hold the aspect and keep it round.

```python filename=modules/generative-media/code/aspectfit-inter-01/aspectfit.py:110-115 COMPLETE
    stretch_changes_aspect = abs(aspect(st["out_w"], st["out_h"]) - src_aspect) > 0.01
    print("  stretch output aspect differs from the source = %s (%.3f vs %.3f)" % (stretch_changes_aspect, aspect(st["out_w"], st["out_h"]), src_aspect))

    sax, say = circle_axes(r, st["scale_x"], st["scale_y"])
    stretch_ellipse = abs(sax - say) > 0.5
    print("  stretch turns the circle into an ellipse = %s (semi-axes %.0f vs %.0f)" % (stretch_ellipse, sax, say))
```

```text filename=aspectfit.py --check
SELF-TEST — stretch changes the aspect ratio and ellipticizes the circle, while fit and cover both preserve the aspect and keep the circle round
----------------------------------------------------------------------------------------------------------------
  stretch output aspect differs from the source = True (1.000 vs 1.333)
  stretch turns the circle into an ellipse = True (semi-axes 50 vs 67)
  fit preserves the aspect ratio = True (1.333)
  fit output lies inside the box (padding, no crop) = True (400x300 in 400x400)
  cover preserves the aspect ratio = True (1.333)
  cover output covers the box (crop, no padding) = True (533x400 over 400x400)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  stretch_changes_aspect=True  stretch_ellipse=True  fit_keeps_aspect=True  fit_inside_box=True  cover_keeps_aspect=True  cover_fills_box=True
```

**Fit lands inside the box (400x300 in 400x400) and cover covers it (533x400 over 400x400); the same one-scale rule produces both, and only the leftover differs.**

## Definition of done

You can state the aspect ratios of the source and the box and say whether a plain resize-to-box will distort — it distorts exactly when they differ.

You can compute both candidate scales, target_w/src_w and target_h/src_h, and say which one fit uses (the min) and which cover uses (the max), and why.

You can predict the leftover: fit pads the axis that came up short, cover crops the axis that overflowed, and you can give the pixel amount from the numbers above (100px of padding for fit, 133px of crop for cover).

You can name the check that catches this in review — compare output aspect to source aspect, not just output size to target size.

## Boss fight

Your avatar pipeline resizes every upload to a 256x256 square with a single resize-to-box call, and portrait selfies come out looking wide — faces subtly stretched horizontally. Someone proposes "detect portrait uploads and resize those differently."

First: what is the actual scale mismatch for a 1080x1440 portrait going into 256x256, and which axis is being stretched relative to the other? Compute scale_x and scale_y and say which is larger.

Then: the avatar is a fixed square that must be completely filled with no bars — so which strategy is forced here, fit or cover? Given that choice, what gets cropped from a 1080x1440 portrait, and is cropping the top-and-bottom or the sides the right call for a face? State the scale you would use and the crop in source pixels.

Finally: rewrite the requirement so the bug cannot recur. The wrong requirement is "output must be 256x256". Write the right one as two clauses — one about the scale applied to the two axes, one about how the leftover is resolved — so that "the output is 256x256" is a consequence of the rule rather than the whole rule.

## External resources

The CSS object-fit property (MDN) names exactly these strategies — fill, contain, cover — and its documentation is the clearest short reference for what each does to a differently-shaped box.

Any image library's resize documentation (Pillow's Image.resize and ImageOps.fit, or ImageMagick's geometry flags) shows the same fork: a plain resize distorts, and a "fit"/"thumbnail"/"cover" helper exists precisely because the plain call is the wrong default here.
