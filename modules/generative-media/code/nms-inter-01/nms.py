"""Thin edges with non-maximum suppression, or thresholding a gradient gives a fuzzy band instead of a line.

An edge detector reports the gradient magnitude at every pixel, and where the image steps from dark to light the
magnitude does not spike on a single pixel -- it rises to a peak and falls away over several. So a real edge, which
is one pixel wide, shows up in the magnitude map as a RIDGE several pixels across. The obvious next step,
thresholding the magnitude, keeps every pixel on that ridge that clears the cutoff, and hands you an edge three or
four pixels thick: a fuzzy band, not a line. Every downstream step that assumes edges are thin -- following a
contour, measuring a length, matching a shape -- is now working with a smear, and thresholding harder does not
fix it, it just erodes the whole edge including the peak.

Non-maximum suppression thins the ridge to its crest. Keep a pixel only if its magnitude is a local maximum -- at
least as large as its neighbors along the gradient direction -- and also above the threshold. On the ridge, only
the single peak pixel is a local maximum; the shoulders on either side are smaller than the peak, so they are
suppressed even though they cleared the threshold. What survives is one pixel, sitting exactly on the crest, which
is the true edge location. Thresholding answers 'is this pixel edgy enough'; non-maximum suppression answers 'is
this the pixel where the edge actually is', and only the second gives a one-pixel edge.

On this fixture the magnitude ridge is 0 2 4 7 5 2 0, peaking at index 3. Thresholding at 3 keeps indices 2, 3,
and 4 -- a three-pixel-thick edge. Non-maximum suppression keeps only index 3, the peak -- a one-pixel edge at the
true location. This computes both.

  --profile    the magnitude ridge, which pixels clear the threshold, and which are local maxima
  --thin       the thick thresholded edge vs the one-pixel non-maximum-suppressed edge
  --check      thresholding gives a multi-pixel band; NMS gives one pixel, at the ridge's peak

The magnitude profile is the fixture; every decision is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "nms.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def at(mag, i):
    """Magnitude with out-of-bounds treated as -1 (so an endpoint can be a local max)."""
    return mag[i] if 0 <= i < len(mag) else -1


def thresholded(mag, threshold):
    """Indices whose magnitude clears the threshold -- the thick edge."""
    return [i for i, m in enumerate(mag) if m >= threshold]


def is_local_max(mag, i):
    """Is pixel i at least as large as both neighbors along the profile?"""
    return mag[i] >= at(mag, i - 1) and mag[i] >= at(mag, i + 1)


def suppressed(mag, threshold):
    """Non-maximum suppression: keep pixels that are both above threshold and a local maximum."""
    return [i for i, m in enumerate(mag) if m >= threshold and is_local_max(mag, i)]


# ----------------------------------------------------------------- printing

def profile_view(data):
    mag, thr = data["magnitudes"], data["threshold"]
    print("PROFILE — gradient magnitude across the edge (threshold %d)" % thr)
    print("-" * 60)
    print("  index      %s" % "  ".join("%d" % i for i in range(len(mag))))
    print("  magnitude  %s" % "  ".join("%d" % m for m in mag))
    print("  >= thresh  %s" % "  ".join("Y" if m >= thr else "." for m in mag))
    print("  local max  %s" % "  ".join("Y" if is_local_max(mag, i) else "." for i in range(len(mag))))
    print("-" * 60)
    print("  the ridge clears the threshold over several pixels; only its peak is a local max.")


def thin_view(data):
    mag, thr = data["magnitudes"], data["threshold"]
    th = thresholded(mag, thr)
    nms = suppressed(mag, thr)
    print("THIN — thresholded edge vs non-maximum-suppressed edge")
    print("-" * 60)
    print("  thresholded (thick):   pixels %s  (%d wide)" % (th, len(th)))
    print("  suppressed  (thin):    pixels %s  (%d wide)" % (nms, len(nms)))
    print("-" * 60)
    print("  NMS keeps the peak at index %d and drops the shoulders -- a one-pixel edge." % nms[0])


def check(data):
    print("SELF-TEST — thresholding gives a multi-pixel band; NMS gives one pixel, at the ridge's peak")
    print("-" * 104)
    mag, thr, peak = data["magnitudes"], data["threshold"], data["peak_index"]
    th = thresholded(mag, thr)
    nms = suppressed(mag, thr)

    threshold_is_thick = len(th) >= 3
    print("  thresholding gives a thick edge (>= 3 pixels) = %s (%d pixels %s)" % (threshold_is_thick, len(th), th))

    nms_is_one_pixel = len(nms) == 1
    print("  non-maximum suppression gives one pixel = %s (%s)" % (nms_is_one_pixel, nms))

    nms_keeps_the_peak = nms == [peak] and mag[peak] == max(mag)
    print("  the surviving pixel is the ridge's peak = %s (index %d, magnitude %d = max)" % (nms_keeps_the_peak, peak, mag[peak]))

    nms_subset_of_thresholded = set(nms) <= set(th)
    print("  every NMS pixel also cleared the threshold = %s" % nms_subset_of_thresholded)

    nms_thinner = len(nms) < len(th)
    print("  the NMS edge is thinner than the thresholded edge = %s (%d < %d)" % (nms_thinner, len(nms), len(th)))

    ok = threshold_is_thick and nms_is_one_pixel and nms_keeps_the_peak and nms_subset_of_thresholded and nms_thinner
    print("-" * 104)
    print("SELF-TEST %s  threshold_is_thick=%s  nms_is_one_pixel=%s  nms_keeps_the_peak=%s  nms_subset_of_thresholded=%s  nms_thinner=%s"
          % ("PASS" if ok else "FAIL", threshold_is_thick, nms_is_one_pixel, nms_keeps_the_peak, nms_subset_of_thresholded, nms_thinner))
    return ok


def main():
    p = argparse.ArgumentParser(description="Non-maximum suppression thins a thick thresholded gradient ridge to a one-pixel edge at the peak.")
    p.add_argument("--profile", action="store_true")
    p.add_argument("--thin", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("magnitudes=%s  threshold=%d  peak_index=%d  file=%s  (the profile is a fixture)"
          % (data["magnitudes"], data["threshold"], data["peak_index"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.profile:
        profile_view(data)
    elif args.thin:
        thin_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
