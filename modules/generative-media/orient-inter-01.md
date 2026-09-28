---
id: orient-inter-01
title: Apply the EXIF orientation before you process — ignoring it shows sideways, stripping it loses the fix forever
topic: generative-media
level: intermediate
status: ready
time: 15 min
summary: A camera writes pixels in the sensor's native order and records how it was held as an EXIF Orientation tag — 1 is already upright, 3 is 180 degrees, 6 is rotate 90 clockwise to display, 8 is rotate 90 counter-clockwise, plus mirrored variants — so the pixels are not upright and the tag says how to make them upright. A correct viewer applies the tag before showing the image; a naive tool that decodes the raw pixel array and treats it as final shows a portrait photo lying on its side, the classic "why is my photo sideways" bug. The worse failure is re-encoding: many pipelines strip metadata when they resize or convert, and if they drop the orientation tag without first applying it, the image is stored in its sideways pixel order with a tag of 1 (which every viewer reads as "already upright"), so the one piece of information that could have corrected it is gone and the image is permanently wrong. The fix is to bake the orientation in — physically rotate the pixel array per the tag, then set the tag to 1 — so the stored pixels are upright, the tag is honest, and no viewer needs to do anything. On the fixture the stored grid is 2 rows by 3 columns with tag 6, so the correct display is that grid rotated 90 clockwise to 3 rows by 2 columns; ignoring the tag shows the raw 2×3 grid, stripping the tag leaves the raw 2×3 grid with tag 1 (wrong and unrecoverable), and baking rotates to 3×2 and sets tag 1 (correct). The rule: orientation lives in the metadata, not the pixels, so any tool that reads pixels must apply the tag first, and any tool that drops metadata must bake the tag in before it does.
eli5: A camera often takes the picture sideways and just writes a sticky note on the file that says "turn this 90 degrees before showing it." A good photo viewer reads the note and turns the picture; a lazy one ignores the note and shows it sideways. The real disaster is a tool that, while shrinking or converting the photo, throws away the sticky note without actually turning the picture first — now the picture is still sideways and the note that said to turn it is gone, so it's stuck sideways forever. The safe move is to actually rotate the picture the way the note says, and then change the note to "already upright." Do the turn, then update the note — never just tear the note off.
---

## Why this module

"Why is this photo sideways" is one of the most common image bugs in any product that accepts uploads, and it is not a decoding error — the pixels decoded perfectly. It is an orientation bug: the image carries its rotation in metadata, and the code read the pixels without reading the note that says how to turn them.

It matters beyond the cosmetic annoyance because of when it becomes permanent. As long as the orientation tag survives, the image is recoverable — some later viewer can still apply it. The moment a pipeline strips the tag without baking it in, the rotation is lost for good, and now every viewer, correct or not, shows the image wrong. So the bug has a benign form (a viewer ignores the tag today) and a fatal form (a re-encode drops the tag), and they look the same until the tag is gone.

**Orientation lives in the metadata, not the pixels, so reading pixels without the tag shows the image wrong, and dropping the tag without baking it in makes wrong permanent.**

## Concepts

A camera sensor has a fixed readout order, so the pixels are written in that order regardless of how the camera was held. To record the holding, the file carries an EXIF Orientation tag with eight possible values: 1 (upright as stored), 3 (rotate 180), 6 (rotate 90 clockwise), 8 (rotate 90 counter-clockwise), and four mirrored variants. The pixels plus the tag together specify the upright image; the pixels alone do not.

A correct display path reads both: decode the pixels, then transform them per the tag before showing or processing. Skip the transform and you show the sensor's raw order — for a photo taken in portrait with a landscape sensor, that is the image rotated 90 degrees, lying on its side. The pixels are fine; the tag was never applied.

Re-encoding is where the benign bug turns fatal. Resizing, format conversion, and thumbnailing all rewrite the file, and many such tools drop EXIF metadata in the process — often deliberately, to shrink the file or scrub location data. If the tool drops the orientation tag without first applying it to the pixels, the new file has the old sideways pixel order and a tag of 1. Every viewer now reads "already upright" and shows the sideways pixels. The rotation that the tag encoded is unrecoverable, because nothing records it anymore.

The correct handling is to bake: apply the orientation transform to the pixel array so the stored pixels are physically upright, and only then set the tag to 1. After baking, the pixels are correct on their own, the tag honestly says "upright," and stripping metadata is now harmless because there is no orientation left to lose. Baking then resetting is safe; resetting (or stripping) without baking is destruction.

**Apply the tag to the pixels before display, and before dropping metadata bake it in and set the tag to 1 — the pixels alone must be made upright before the tag that describes them is discarded.**

<svg role="img" aria-label="The upright image equals the stored pixels plus the orientation tag. A viewer that uses both shows it upright; a viewer that uses only the pixels shows it sideways." viewBox="0 0 320 140">
<rect x="0" y="0" width="320" height="140" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">upright = pixels + tag, not pixels alone</text>
<text x="20" y="50" fill="var(--ink)" font-size="10">pixels (sideways)</text>
<text x="150" y="50" fill="var(--muted)" font-size="12">+</text>
<text x="170" y="50" fill="var(--ink)" font-size="10">tag (rotate 90)</text>
<text x="20" y="82" fill="var(--s2)" font-size="10">viewer uses both &#8594; upright</text>
<text x="20" y="110" fill="var(--s1)" font-size="10">viewer uses pixels only &#8594; sideways</text>
</svg>
^ The stored pixels are only half the image; the tag is the other half, so a viewer that reads pixels without the tag is missing the information that makes the image upright.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/generative-media/code/orient-inter-01/orient.py

The fixture is a small stored grid whose tag says rotate 90 clockwise.

```json filename=modules/generative-media/code/orient-inter-01/orient.json:3-4 COMPLETE
  "stored_grid": [["A", "B", "C"], ["D", "E", "F"]],
  "orientation": 6
```

Applying the tag rotates the pixels; tag 6 is a 90-degree clockwise rotation.

```python filename=modules/generative-media/code/orient-inter-01/orient.py:32-34 COMPLETE
def rot90cw(grid):
    """Rotate a grid 90 degrees clockwise; rows and columns swap."""
    return [list(row) for row in zip(*grid[::-1])]
```

```python filename=modules/generative-media/code/orient-inter-01/orient.py:47-57 COMPLETE
def apply_orientation(grid, tag):
    """Transform the pixels the way the EXIF tag says to display them."""
    if tag == 1:
        return [row[:] for row in grid]
    if tag == 3:
        return rot180(grid)
    if tag == 6:
        return rot90cw(grid)
    if tag == 8:
        return rot90ccw(grid)
    raise ValueError("unsupported tag %r" % tag)
```

```text filename=orient.py --display
DISPLAY — stored tag 6 says how to orient the pixels
----------------------------------------------------------------
  raw pixels        A B C / D E F  dims (2, 3)
  correct display   D A / E B / F C  dims (3, 2)   (tag applied)
  ignoring the tag  A B C / D E F  dims (2, 3)   <- shown sideways
```

The stored pixels are a 2×3 grid; the correct display, tag applied, is the 3×2 rotation. A viewer that ignores the tag shows the raw 2×3 grid — the wrong orientation and the wrong aspect ratio, a landscape frame for what should be portrait.

<svg role="img" aria-label="On the left, a wide 2-by-3 grid labeled 'stored pixels (sideways)'. An arrow labeled 'apply tag 6' points to a tall 3-by-2 grid labeled 'correct display (upright)'." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">the tag rotates the stored pixels to upright</text>
<rect x="30" y="50" width="90" height="60" fill="none" stroke="var(--s1)"></rect>
<text x="40" y="126" fill="var(--muted)" font-size="9">stored 2x3 (sideways)</text>
<text x="140" y="82" fill="var(--muted)" font-size="10">apply tag 6 &#8594;</text>
<rect x="230" y="40" width="60" height="90" fill="none" stroke="var(--s2)"></rect>
<text x="228" y="146" fill="var(--muted)" font-size="9">correct 3x2 (upright)</text>
</svg>
^ The stored pixels are the wide sideways grid; applying tag 6 rotates them into the tall upright grid a viewer should show.

## Build

Re-encoding can strip the tag (fatal) or bake it in (correct).

```text filename=orient.py --handle
HANDLE — re-encoding the file two ways
----------------------------------------------------------------
  strip tag: pixels A B C / D E F  tag 1   correct? False   <- orientation lost
  bake in  : pixels D A / E B / F C  tag 1   correct? True
----------------------------------------------------------------
  stripping keeps the sideways pixels and drops the fix; baking rotates then resets the tag
```

Stripping the tag leaves the sideways 2×3 pixels but sets the tag to 1, so the file now claims to be upright while being wrong — and there is no tag left to correct it. Baking rotates the pixels to the upright 3×2 first and then sets the tag to 1, so the file is correct and needs no tag. Both end with tag 1; only baking made the pixels match that claim.

<svg role="img" aria-label="Two re-encode outcomes. Strip: sideways pixels with a tag reset to 1, marked wrong and unrecoverable. Bake: rotated upright pixels with a tag reset to 1, marked correct." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">re-encode: tag ends at 1 either way, pixels differ</text>
<text x="20" y="48" fill="var(--s1)" font-size="10">strip tag (no rotate)</text>
<rect x="40" y="56" width="70" height="46" fill="none" stroke="var(--s1)"></rect>
<text x="40" y="118" fill="var(--s1)" font-size="9">sideways, tag=1 &#8594; wrong forever</text>
<text x="180" y="48" fill="var(--s2)" font-size="10">bake in (rotate first)</text>
<rect x="200" y="52" width="46" height="60" fill="none" stroke="var(--s2)"></rect>
<text x="180" y="128" fill="var(--s2)" font-size="9">upright, tag=1 &#8594; correct</text>
</svg>
^ Both files carry tag 1, but the stripped one still holds sideways pixels the tag can no longer fix, while the baked one holds upright pixels that need no tag.

The self-test states the display error, the dimension swap, the permanent loss, and the correct bake.

```python filename=modules/generative-media/code/orient-inter-01/orient.py:102-106 COMPLETE
    ignore_wrong = raw != correct
    print("  ignoring the tag differs from the correct display = %s (%s vs %s)" % (ignore_wrong, _fmt(raw), _fmt(correct)))

    dims_swap = dims(correct) != dims(raw)
    print("  applying the 90-degree tag swaps rows and columns = %s (%s -> %s)" % (dims_swap, dims(raw), dims(correct)))
```

```python filename=modules/generative-media/code/orient-inter-01/orient.py:108-113 COMPLETE
    stripped_grid, stripped_tag = [row[:] for row in raw], 1
    strip_permanent_wrong = stripped_grid != correct and stripped_tag == 1
    print("  stripping the tag leaves wrong pixels with an 'upright' tag (unrecoverable) = %s" % strip_permanent_wrong)

    baked_grid, baked_tag = apply_orientation(raw, tag), 1
    bake_correct = baked_grid == correct and baked_tag == 1
    print("  baking rotates the pixels and resets the tag to 1 = %s" % bake_correct)
```

```text filename=orient.py --check
SELF-TEST — ignoring the tag differs from the correct display, stripping the tag is permanently wrong, and baking matches the correct display with the tag reset to 1
----------------------------------------------------------------------------------------------------------------
  ignoring the tag differs from the correct display = True (A B C / D E F vs D A / E B / F C)
  applying the 90-degree tag swaps rows and columns = True ((2, 3) -> (3, 2))
  stripping the tag leaves wrong pixels with an 'upright' tag (unrecoverable) = True
  baking rotates the pixels and resets the tag to 1 = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  ignore_wrong=True  dims_swap=True  strip_permanent_wrong=True  bake_correct=True
```

**strip_permanent_wrong is the failure that outlives the deploy: an ignored tag is fixable later, but a stripped tag with unrotated pixels is wrong in every viewer, forever.**

## Definition of done

You can explain why the pixels are stored in the sensor's order and what the EXIF Orientation tag adds — the rotation needed to make them upright.

You can trace why ignoring the tag shows the image sideways and swaps its aspect ratio, and why the pixels being "correct" does not make the displayed image correct.

You can describe why stripping the tag on re-encode is the fatal case — the pixels stay sideways and the tag that would fix them is gone — versus the recoverable case of a viewer merely ignoring the tag.

You can state the correct handling: apply the transform to the pixels, then set the tag to 1, so the stored pixels are upright before any metadata is dropped.

## Boss fight

Your app lets users upload photos, resizes them to thumbnails with a library that strips metadata, and stores both. Portrait phone photos show upright in the original but sideways in the thumbnail, and older stored thumbnails cannot be fixed even after you patch the code.

First: explain the two different failures. Why is the original fine but the thumbnail sideways, and why can the old thumbnails not be repaired while new uploads can — what did the resize step do to the orientation tag?

Then: fix the pipeline. State the exact order of operations the resize step must follow so the thumbnail is upright and its (possibly stripped) metadata no longer matters, and explain why doing the resize before applying orientation, versus after, changes nothing about correctness but everything about whether you must track the tag through the resize.

Finally: the mirrored orientation tags (2, 4, 5, 7) involve a flip, not just a rotation, and a naive "rotate by the degrees" implementation gets them backwards. Explain why a flip cannot be expressed as a rotation, and why a correct implementation must handle all eight tags explicitly rather than mapping the tag to an angle.

## External resources

The EXIF specification's Orientation field defines all eight values and the transform each requires; every correct image library implements exactly this table, and reading it shows why tags 2, 4, 5, and 7 need a flip.

Image-library documentation for orientation handling (for example Pillow's ImageOps.exif_transpose) describes the bake-and-reset operation this module builds — apply the tag to the pixels and clear it — as the standard way to normalize orientation before further processing.
