---
id: labelmap-inter-01
title: Resample a label map with nearest-neighbor — or bilinear averaging invents a class that isn't there
topic: generative-media
level: intermediate
status: ready
time: 19 min
summary: Bilinear interpolation is right for a photo — a pixel is a brightness, and the average of two brightnesses is a valid in-between brightness. A label map — a segmentation mask, a palette-index image, any picture whose pixels are class IDs — is the opposite case. The number 2 does not mean "a bit more than 1"; it names a class. Average class 1 (road) and class 3 (car) and you get 2, which is not half-road-half-car — it is the class building, a different thing that appears nowhere near those pixels. Bilinear on a label map produces either a fractional ID that is no class at all, or a whole-number ID for a real but wrong class, silently painting a building between the road and the car. Nearest-neighbor copies the closer label, so every output is a class that actually occurred. On two pixels labeled 1 and 3, bilinear gives 1.0, 1.5, 2.0, 2.5, 3.0 while nearest gives 1, 1, 3, 3, 3.
eli5: If your pixels are paint colors, mixing two of them makes a sensible new color. But if your pixels are jersey numbers, "the average of player 1 and player 3" is player 2 — a completely different person, not a blend of the two. Class labels are jersey numbers, not paint. So when you resize a label picture, you copy the nearest number, you never average.
---

## Why this module

The same resizing method that is correct for a photograph is destructive for a label map, because the two store fundamentally different things in a pixel.

In a photo, a pixel value is a quantity — a brightness — and interpolation is meaningful: halfway between a value of 100 and a value of 200 really is 150, a valid shade. In a label map, a pixel value is a category — a class ID — and the ID is a name, not a magnitude. Class 3 is not "more" than class 1; it is simply a different class that happens to be numbered 3. Averaging them is like averaging phone numbers. Bilinear interpolation does exactly this averaging, so on a label map it manufactures values between the real labels: either fractional IDs that name no class at all, or, more insidiously, whole-number IDs that name a real class which does not belong at that location.

**A class ID is a name, not a quantity, so averaging two labels produces a third label with no relation to either — the arithmetic is meaningless even when the result looks valid.**

Nearest-neighbor resampling is correct for label maps: it copies the label of the closer source pixel, so every output value is an ID that actually appeared in the input. It looks blocky, and blocky is right — a class boundary is a hard edge, not a gradient, and there is nothing to interpolate across it. This module resamples a two-pixel label map both ways and shows bilinear invent a class.

## Concepts

A **label map** stores a class ID per pixel. The **classes** table gives each ID a meaning; here 1 is road, 2 is building, 3 is car.

**Bilinear interpolation** computes an output pixel as a weighted average of nearby source pixels — correct for continuous quantities. Applied to labels, it blends the IDs: sampling between label 1 and label 3 yields 1 + f × (3 − 1) for a fraction f, sweeping through 1.5, 2.0, 2.5.

**Nearest-neighbor** copies the label of the nearest source pixel — no arithmetic on the IDs at all. Its output is always one of the input labels.

Two distinct failures come out of the bilinear blend. A **non-integer** result (1.5) corresponds to no class — it is nonsense that a later step must round or reject. A **whole-number wrong class** (2.0 = building) is worse: it is a perfectly valid ID, so nothing flags it as an error, and you have silently inserted a class that was never in the scene, between the two that were.

The rule is a clean split: **interpolate quantities, copy categories.** Brightness, depth, and flow are quantities and take bilinear; segmentation masks, palette indices, and instance IDs are categories and take nearest.

**Bilinear on a label map can hit a real but wrong class, which passes every validity check while corrupting the data — nearest-neighbor cannot, because it never produces a value that was not already a label.**

The two pixel meanings sit on different scales: brightness is a ruler where the space between marks is real, and a class ID is a set of bins where the space between bins means nothing.

<svg role="img" aria-label="A brightness ruler where midpoints are valid, versus labeled bins road building car where the gap between bins is meaningless" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="16" fill="var(--s2)" font-size="8">quantity (a ruler)</text>
  <line x1="20" y1="30" x2="280" y2="30" stroke="var(--s2)" stroke-width="2"/>
  <line x1="150" y1="25" x2="150" y2="35" stroke="var(--s2)" stroke-width="1.5"/>
  <text x="128" y="48" fill="var(--s2)" font-size="7">midpoint is valid</text>
  <text x="10" y="72" fill="var(--s1)" font-size="8">category (bins)</text>
  <rect x="20" y="80" width="70" height="16" fill="none" stroke="var(--s1)"/><text x="35" y="92" fill="var(--muted)" font-size="7">road</text>
  <rect x="115" y="80" width="70" height="16" fill="none" stroke="var(--s1)"/><text x="128" y="92" fill="var(--muted)" font-size="7">building</text>
  <rect x="210" y="80" width="70" height="16" fill="none" stroke="var(--s1)"/><text x="228" y="92" fill="var(--muted)" font-size="7">car</text>
  <text x="92" y="92" fill="var(--s1)" font-size="9">?</text><text x="187" y="92" fill="var(--s1)" font-size="9">?</text>
  <text x="20" y="108" fill="var(--muted)" font-size="7">nothing lives in the gaps between category bins</text>
</svg>
^ On the quantity ruler the point between two marks is a real value; between category bins there is no value at all, so a blend lands either in a gap or, by accident, in the wrong bin.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/generative-media/code/labelmap-inter-01/labelmap.py

The fixture is two source labels and the class table, sampled across the gap between them.

```json filename=modules/generative-media/code/labelmap-inter-01/labels.json:1-6 COMPLETE
{
  "_meta": "A 1D label map to be upsampled: labels are class IDs (not brightnesses), one per source pixel. classes maps each valid ID to what it means. We resample from the two source pixels at fractional positions (0.0 = first pixel, 1.0 = second) two ways: bilinear (average the neighboring labels) and nearest (pick the closer label). fractions are the positions to sample. The question: which method only ever produces a real, existing class ID?",
  "labels": [1, 3],
  "classes": {"1": "road", "2": "building", "3": "car"},
  "fractions": [0.0, 0.25, 0.5, 0.75, 1.0]
}
```

Bilinear blends the two endpoint labels; nearest copies the closer one. The class lookup marks any value that is not a valid whole-number ID.

```python filename=modules/generative-media/code/labelmap-inter-01/labelmap.py:41-56 COMPLETE
def bilinear(labels, f):
    """Linear blend of the two endpoint labels -- treats class IDs as if they were quantities."""
    return labels[0] + f * (labels[1] - labels[0])


def nearest(labels, f):
    """Copy the label of the nearer source pixel: index 0 if f<0.5, else index 1."""
    return labels[int(f + 0.5)]


def class_of(value, classes):
    """The class name for an integer ID, or a marker that the value is not a valid class."""
    key = str(int(value)) if float(value).is_integer() else None
    if key is not None and key in classes:
        return classes[key]
    return "<not a class>"
```

The resample view walks the sample positions and prints both methods' values and the class each resolves to.

```python filename=modules/generative-media/code/labelmap-inter-01/labelmap.py:62-70 COMPLETE
    labels, classes, fracs = data["labels"], data["classes"], data["fractions"]
    print("RESAMPLE — labels %s (%s -> %s) sampled across the gap" % (labels, classes[str(labels[0])], classes[str(labels[1])]))
    print("-" * 64)
    print("  pos    bilinear -> class            nearest -> class")
    for f in fracs:
        b, n = bilinear(labels, f), nearest(labels, f)
        print("  %.2f   %4.1f -> %-16s %d -> %s" % (f, b, class_of(b, classes), n, class_of(n, classes)))
    print("-" * 64)
    print("  bilinear drifts through in-between values; nearest snaps to a real label.")
```

Run `--resample` and read the class each method lands on.

```text filename=--resample
RESAMPLE — labels [1, 3] (road -> car) sampled across the gap
----------------------------------------------------------------
  pos    bilinear -> class            nearest -> class
  0.00    1.0 -> road             1 -> road
  0.25    1.5 -> <not a class>    1 -> road
  0.50    2.0 -> building         3 -> car
  0.75    2.5 -> <not a class>    3 -> car
  1.00    3.0 -> car              3 -> car
----------------------------------------------------------------
  bilinear drifts through in-between values; nearest snaps to a real label.
```

Bilinear sweeps 1.0 → 1.5 → 2.0 → 2.5 → 3.0. The 1.5 and 2.5 are not classes at all. The 2.0 at the midpoint is the damning one: it resolves to building — a real class, so it passes silently, but there is no building anywhere near a road-to-car boundary. Nearest stays on road then jumps to car; every value it emits is a class that was actually present.

<svg role="img" aria-label="Bilinear sweeps from label 1 through 1.5, 2, 2.5 to 3, hitting building at the midpoint; nearest steps from road to car" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="16" fill="var(--muted)" font-size="8">bilinear (blends IDs)</text>
  <line x1="20" y1="45" x2="280" y2="20" stroke="var(--s1)" stroke-width="2"/>
  <circle cx="20" cy="45" r="3" fill="var(--s1)"/><text x="12" y="60" fill="var(--muted)" font-size="7">road(1)</text>
  <circle cx="150" cy="32" r="4" fill="var(--s1)"/><text x="132" y="30" fill="var(--s1)" font-size="7">2 = building!</text>
  <circle cx="280" cy="20" r="3" fill="var(--s1)"/><text x="255" y="16" fill="var(--muted)" font-size="7">car(3)</text>
  <line x1="10" y1="72" x2="290" y2="72" stroke="var(--line)" stroke-width="1"/>
  <text x="10" y="90" fill="var(--muted)" font-size="8">nearest (copies IDs)</text>
  <polyline points="20,115 150,115 150,98 280,98" fill="none" stroke="var(--s2)" stroke-width="2"/>
  <text x="30" y="112" fill="var(--s2)" font-size="7">road</text>
  <text x="240" y="95" fill="var(--s2)" font-size="7">car</text>
</svg>
^ Bilinear draws a ramp that passes through building at the midpoint; nearest is a step from road straight to car, never touching a class that was not there.

## Build

The `--invent` view isolates what bilinear added that was never in the input.

```text filename=--invent
INVENT — labels bilinear introduces that were never in the input
----------------------------------------------------------------
  input labels:        [1, 3]
  bilinear outputs:    [1.0, 1.5, 2.0, 2.5, 3.0]
  invented values:     [1.5, 2.0, 2.5] (none of these were in the input)
  worst case:          2 is a REAL class 'building' that belongs nowhere here
----------------------------------------------------------------
  nearest introduces nothing new -- it can only copy an existing label.
```

Three of the five bilinear outputs — 1.5, 2.0, 2.5 — were never in the input at all. Two are non-classes a pipeline might catch by rejecting non-integers. But 2.0 is a valid ID, so it slips through as building, and now your resized mask claims a building sits on the boundary between the road and the car. Nearest's invented set is empty by construction: it selects from the input labels, so it can add nothing.

<svg role="img" aria-label="Input labels 1 and 3; bilinear adds 1.5, 2, 2.5 with 2 being a valid wrong class; nearest adds nothing" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="18" fill="var(--muted)" font-size="8">input labels</text>
  <rect x="110" y="10" width="22" height="14" fill="var(--s2)"/><text x="115" y="21" fill="var(--panel)" font-size="8">1</text>
  <rect x="160" y="10" width="22" height="14" fill="var(--s2)"/><text x="165" y="21" fill="var(--panel)" font-size="8">3</text>
  <text x="10" y="48" fill="var(--s1)" font-size="8">bilinear adds</text>
  <rect x="110" y="40" width="22" height="14" fill="none" stroke="var(--s1)" stroke-dasharray="2 2"/><text x="113" y="51" fill="var(--s1)" font-size="7">1.5</text>
  <rect x="135" y="40" width="22" height="14" fill="var(--s1)"/><text x="138" y="51" fill="var(--panel)" font-size="7">2!</text>
  <rect x="160" y="40" width="22" height="14" fill="none" stroke="var(--s1)" stroke-dasharray="2 2"/><text x="163" y="51" fill="var(--s1)" font-size="7">2.5</text>
  <text x="188" y="51" fill="var(--s1)" font-size="7">2 = building (valid, wrong)</text>
  <text x="10" y="78" fill="var(--s2)" font-size="8">nearest adds</text>
  <text x="110" y="78" fill="var(--muted)" font-size="8">— nothing —</text>
  <text x="10" y="100" fill="var(--muted)" font-size="8">only bilinear manufactures labels the scene never had</text>
</svg>
^ Bilinear injects three values absent from the input, one of them a valid but wrong class; nearest adds none, because it can only reproduce labels that were already present.

## Definition of done

The self-test pins both failure modes and the fix: bilinear invents values, some are non-integer, one lands on a real wrong class, while every nearest value is an existing label and a whole number.

```python filename=modules/generative-media/code/labelmap-inter-01/labelmap.py:99-112 COMPLETE
    bilinear_invents = any(v not in valid for v in bvals)
    print("  bilinear produces values not in the input = %s (%s)" % (bilinear_invents, [round(v, 2) for v in bvals if v not in valid]))

    bilinear_non_integer = any(not float(v).is_integer() for v in bvals)
    print("  some bilinear values are non-integer (no class at all) = %s" % bilinear_non_integer)

    bilinear_hits_wrong_class = any(float(v).is_integer() and v not in valid and str(int(v)) in classes for v in bvals)
    wrong = [int(v) for v in bvals if float(v).is_integer() and v not in valid and str(int(v)) in classes]
    print("  a bilinear value lands on a real but wrong class = %s (%s)" % (bilinear_hits_wrong_class, [classes[str(w)] for w in wrong]))

    nearest_only_existing = all(v in valid for v in nvals)
    print("  every nearest value is an existing input label = %s (%s)" % (nearest_only_existing, sorted(set(nvals))))

    nearest_all_integer = all(float(v).is_integer() for v in nvals)
    print("  every nearest value is a whole-number class ID = %s" % nearest_all_integer)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — bilinear invents non-existent and wrong-class labels; nearest emits only real ones
----------------------------------------------------------------------------------------------------
  bilinear produces values not in the input = True ([1.5, 2.0, 2.5])
  some bilinear values are non-integer (no class at all) = True
  a bilinear value lands on a real but wrong class = True (['building'])
  every nearest value is an existing input label = True ([1, 3])
  every nearest value is a whole-number class ID = True
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  bilinear_invents=True  bilinear_non_integer=True  bilinear_hits_wrong_class=True  nearest_only_existing=True  nearest_all_integer=True
```

**Done means the corruption is exhibited, not warned about: bilinear outputs the class building (ID 2) between road and car, which passes as valid, while nearest emits only the classes 1 and 3 that were actually present.**

## Boss fight

Nearest is right for labels here. Predict whether that means nearest is the safe default for resizing any image. It is tempting to over-correct after seeing bilinear fail.

It is the wrong default for the common case, which is the mirror of this module. For a photograph, nearest-neighbor is the one that looks bad — it produces blocky, aliased edges because it cannot smooth a gradient, and bilinear (or bicubic) is correct there precisely because brightness *is* interpolatable. The two modules are a matched pair: bilinear for quantities, nearest for categories, and using either on the other's data corrupts it — nearest blocks a photo, bilinear invents classes in a mask. The question is never "which method is best" but "is this pixel a quantity or a category."

The mirror-image mistake is a mixed image where some channels are quantities and some are categories — an RGBA image whose alpha is a soft mask (quantity) beside a segmentation channel (category), or a depth map with an instance-ID channel. Resample each channel with the method its type demands; a single blanket method corrupts whichever channel it does not fit. And when downsampling a label map, nearest still applies, but you may want majority vote over the source region rather than a single nearest pixel, to avoid dropping thin classes.

```python filename=modules/generative-media/code/labelmap-inter-01/labelmap.py:46-48 COMPLETE
def nearest(labels, f):
    """Copy the label of the nearer source pixel: index 0 if f<0.5, else index 1."""
    return labels[int(f + 0.5)]
```

**Resample by what a pixel means: nearest-neighbor for categories (masks, indices, IDs) so no class is invented, bilinear for quantities (brightness, depth) so no gradient is blocked — the data type, not a house default, picks the method.**

## External resources

The OpenCV and Pillow resize documentation — `INTER_NEAREST` vs `INTER_LINEAR`/`INTER_CUBIC`, with the explicit guidance to use nearest for label/index images and interpolation for photographs.

Any semantic-segmentation codebase's data pipeline (e.g. the torchvision segmentation transforms) — image and mask are resized with different interpolation modes for exactly this reason.

The companion "upsample with bilinear, not nearest" module — the opposite lesson for photographs; the two together are the quantity-vs-category rule that decides every resampling.
