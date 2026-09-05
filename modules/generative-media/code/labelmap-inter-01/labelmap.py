"""Resample a label map with nearest-neighbor, or bilinear averaging invents a class that isn't there.

Bilinear interpolation is the right way to resize a PHOTO: a pixel's value is a brightness, and the average of
two brightnesses is a valid, meaningful in-between brightness. A LABEL MAP -- a segmentation mask, a
palette-index image, any picture whose pixels are class IDs rather than intensities -- is the opposite case.
The number 2 does not mean "a bit more than 1"; it means a specific class. Averaging class 1 (road) and class 3
(car) gives 2, which is not "half road, half car" -- it is the class 'building', a completely different thing
that appears nowhere near those pixels. Bilinear on a label map either produces a fractional ID that
corresponds to no class at all, or, worse, a whole-number ID for a real but WRONG class, silently painting a
building between the road and the car.

Nearest-neighbor is correct for label maps. It picks the label of the closer source pixel and copies it, so
every output pixel is an ID that actually occurred in the input -- a real class, never an average. It can look
blocky, but blocky is right here: a class boundary is a hard edge, not a gradient, and there is no meaningful
value between two classes to interpolate. The rule is that you interpolate quantities and you copy categories.
Use bilinear for brightness, nearest for labels; using the wrong one corrupts the data.

On this fixture two source pixels are labeled 1 (road) and 3 (car). Sampled across the gap, bilinear produces
1.0, 1.5, 2.0, 2.5, 3.0 -- the 1.5 and 2.5 are non-classes, and the 2.0 is 'building', a wrong class. Nearest
produces 1, 1, 3, 3, 3 -- only road and car, the classes that were actually there. This computes both.

  --resample   the bilinear and nearest values at each sampled position, with the class each maps to
  --invent     the labels bilinear introduces that were never in the input, and the wrong-class hit
  --check      bilinear invents non-existent and wrong-class labels; nearest emits only real ones

The labels, classes, and sample positions are the fixture; every value is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "labels.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


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


# ----------------------------------------------------------------- printing

def resample_view(data):
    labels, classes, fracs = data["labels"], data["classes"], data["fractions"]
    print("RESAMPLE — labels %s (%s -> %s) sampled across the gap" % (labels, classes[str(labels[0])], classes[str(labels[1])]))
    print("-" * 64)
    print("  pos    bilinear -> class            nearest -> class")
    for f in fracs:
        b, n = bilinear(labels, f), nearest(labels, f)
        print("  %.2f   %4.1f -> %-16s %d -> %s" % (f, b, class_of(b, classes), n, class_of(n, classes)))
    print("-" * 64)
    print("  bilinear drifts through in-between values; nearest snaps to a real label.")


def invent_view(data):
    labels, classes, fracs = data["labels"], data["classes"], data["fractions"]
    valid = set(labels)
    bvals = [bilinear(labels, f) for f in fracs]
    invented = sorted({v for v in bvals if v not in valid})
    wrong_class = [v for v in bvals if float(v).is_integer() and v not in valid and str(int(v)) in classes]
    print("INVENT — labels bilinear introduces that were never in the input")
    print("-" * 64)
    print("  input labels:        %s" % sorted(valid))
    print("  bilinear outputs:    %s" % [round(v, 2) for v in bvals])
    print("  invented values:     %s (none of these were in the input)" % invented)
    if wrong_class:
        w = wrong_class[0]
        print("  worst case:          %d is a REAL class '%s' that belongs nowhere here" % (int(w), classes[str(int(w))]))
    print("-" * 64)
    print("  nearest introduces nothing new -- it can only copy an existing label.")


def check(data):
    print("SELF-TEST — bilinear invents non-existent and wrong-class labels; nearest emits only real ones")
    print("-" * 100)
    labels, classes, fracs = data["labels"], data["classes"], data["fractions"]
    valid = set(labels)
    bvals = [bilinear(labels, f) for f in fracs]
    nvals = [nearest(labels, f) for f in fracs]

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

    ok = bilinear_invents and bilinear_non_integer and bilinear_hits_wrong_class and nearest_only_existing and nearest_all_integer
    print("-" * 100)
    print("SELF-TEST %s  bilinear_invents=%s  bilinear_non_integer=%s  bilinear_hits_wrong_class=%s  nearest_only_existing=%s  nearest_all_integer=%s"
          % ("PASS" if ok else "FAIL", bilinear_invents, bilinear_non_integer, bilinear_hits_wrong_class, nearest_only_existing, nearest_all_integer))
    return ok


def main():
    p = argparse.ArgumentParser(description="Resample label maps with nearest-neighbor, not bilinear, so no non-existent class is invented.")
    p.add_argument("--resample", action="store_true")
    p.add_argument("--invent", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("labels=%s  classes=%d  positions=%d  file=%s  (the label map is a fixture)"
          % (data["labels"], len(data["classes"]), len(data["fractions"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.resample:
        resample_view(data)
    elif args.invent:
        invent_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
