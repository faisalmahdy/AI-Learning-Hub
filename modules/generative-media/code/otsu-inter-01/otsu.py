"""Pick the threshold from the histogram, not a fixed 128 -- or an object whose brightness sits below the constant vanishes.

Binarizing a grayscale image means choosing an intensity threshold: pixels brighter than it are foreground, darker are
background. The lazy default is a constant -- 128, the middle of the 0..255 range. That constant only works if the
foreground and background happen to straddle it. They usually do not: lighting, exposure, and the object's own albedo
slide both populations up or down together, and the moment both the dark peak and the bright peak fall on the same
side of 128, the constant puts nearly every pixel in one class and the object either floods or disappears. The
threshold has to come from the image, because the image is what moved.

Otsu's method reads it off the histogram. Every threshold splits the pixels into a background class (at or below t)
and a foreground class (above t); a good threshold makes those two classes as separated as possible. Otsu measures
separation by the BETWEEN-CLASS variance -- w0*w1*(mu0 - mu1)^2, the class weights times the squared gap between
their means -- and picks the t that maximizes it. That maximum sits in the valley between the two histogram peaks,
wherever the peaks happen to be, so the threshold tracks the image instead of a magic number. It needs no labels and
no parameters: just the histogram the image already gives you.

On this fixture the two pixel populations peak near intensity 55 (background) and 100 (foreground) -- both below 128.
A fixed threshold of 128 calls almost everything background: it recovers a foreground fraction near 0.004 when the
true fraction is 0.40, so the object nearly vanishes. Otsu's threshold lands in the valley around 77, between the two
peaks, and recovers a foreground fraction near 0.39. The histogram is built deterministically from the two clusters.

  --threshold  Otsu's threshold and its between-class variance vs the fixed 128's -- Otsu's is the maximum
  --split      the foreground fraction each threshold recovers vs the true 0.40 -- fixed 128 loses the object
  --check      Otsu maximizes between-class variance, lands between the two peaks, and recovers the object 128 loses

The two clusters and the fixed threshold are the fixture; the histogram and every variance are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "otsu.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def histogram(data):
    """Build the normalized intensity histogram from the two Gaussian clusters (deterministic, no sampling)."""
    levels = data["levels"]
    h = [0.0] * levels
    for c in data["clusters"]:
        for i in range(levels):
            h[i] += c["weight"] * math.exp(-((i - c["mean"]) ** 2) / (2 * c["std"] ** 2))
    total = sum(h)
    return [x / total for x in h]


def between_class_variance(h, t):
    """Otsu's objective at threshold t: w0*w1*(mu0-mu1)^2 for classes {<=t} and {>t}."""
    w0 = sum(h[: t + 1])
    w1 = 1.0 - w0
    if w0 == 0 or w1 == 0:
        return 0.0
    mu0 = sum(i * h[i] for i in range(t + 1)) / w0
    mu1 = sum(i * h[i] for i in range(t + 1, len(h))) / w1
    return w0 * w1 * (mu0 - mu1) ** 2


def otsu_threshold(h):
    """The threshold that maximizes the between-class variance."""
    return max(range(len(h)), key=lambda t: between_class_variance(h, t))


def fg_fraction(h, t):
    """The fraction of pixels called foreground (intensity strictly above t)."""
    return sum(h[t + 1:])


# ----------------------------------------------------------------- printing

def threshold_view(data):
    h = histogram(data)
    fixed = data["fixed_threshold"]
    t = otsu_threshold(h)
    print("THRESHOLD — Otsu maximizes between-class variance; the fixed 128 does not")
    print("-" * 64)
    print("  cluster peaks (means):     %s" % [c["mean"] for c in data["clusters"]])
    print("  Otsu threshold t*        = %3d   between-class variance = %.2f" % (t, between_class_variance(h, t)))
    print("  fixed threshold          = %3d   between-class variance = %.2f" % (fixed, between_class_variance(h, fixed)))
    print("-" * 64)
    print("  Otsu's t* sits in the valley between the peaks; 128 sits past both of them.")


def split_view(data):
    h = histogram(data)
    fixed, true = data["fixed_threshold"], data["true_fg_fraction"]
    t = otsu_threshold(h)
    print("SPLIT — the foreground fraction each threshold recovers (true = %.2f)" % true)
    print("-" * 60)
    print("  Otsu   t*=%3d -> foreground fraction %.3f" % (t, fg_fraction(h, t)))
    print("  fixed  t =%3d -> foreground fraction %.3f" % (fixed, fg_fraction(h, fixed)))
    print("-" * 60)
    print("  both peaks are below 128, so the fixed threshold calls the object background and loses it.")


def check(data):
    print("SELF-TEST — Otsu maximizes between-class variance, lands between the peaks, and recovers the object 128 loses")
    print("-" * 112)
    h = histogram(data)
    fixed, true = data["fixed_threshold"], data["true_fg_fraction"]
    t = otsu_threshold(h)
    peaks = sorted(c["mean"] for c in data["clusters"])

    is_maximum = all(between_class_variance(h, t) >= between_class_variance(h, u) for u in range(len(h)))
    print("  Otsu's t* maximizes between-class variance over all thresholds = %s (var=%.2f)" % (is_maximum, between_class_variance(h, t)))

    in_valley = peaks[0] < t < peaks[1]
    print("  t* lies in the valley between the two peaks = %s (%d < %d < %d)" % (in_valley, peaks[0], t, peaks[1]))

    otsu_recovers = abs(fg_fraction(h, t) - true) < 0.05
    print("  Otsu recovers the true foreground fraction = %s (%.3f vs %.2f)" % (otsu_recovers, fg_fraction(h, t), true))

    fixed_loses = fg_fraction(h, fixed) < 0.05
    print("  the fixed 128 threshold loses the object = %s (foreground %.3f)" % (fixed_loses, fg_fraction(h, fixed)))

    otsu_beats_fixed = between_class_variance(h, t) > between_class_variance(h, fixed)
    print("  Otsu's separation beats the fixed threshold's = %s (%.2f > %.2f)" % (otsu_beats_fixed, between_class_variance(h, t), between_class_variance(h, fixed)))

    ok = is_maximum and in_valley and otsu_recovers and fixed_loses and otsu_beats_fixed
    print("-" * 112)
    print("SELF-TEST %s  is_maximum=%s  in_valley=%s  otsu_recovers=%s  fixed_loses=%s  otsu_beats_fixed=%s"
          % ("PASS" if ok else "FAIL", is_maximum, in_valley, otsu_recovers, fixed_loses, otsu_beats_fixed))
    return ok


def main():
    p = argparse.ArgumentParser(description="Otsu's method: choose the binarization threshold that maximizes between-class variance, so it tracks the image's histogram instead of a fixed constant.")
    p.add_argument("--threshold", action="store_true")
    p.add_argument("--split", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("clusters=%s  fixed_threshold=%d  levels=%d  file=%s  (the clusters are a fixture)"
          % ([(c["mean"], c["std"], c["weight"]) for c in data["clusters"]], data["fixed_threshold"], data["levels"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.threshold:
        threshold_view(data)
    elif args.split:
        split_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
