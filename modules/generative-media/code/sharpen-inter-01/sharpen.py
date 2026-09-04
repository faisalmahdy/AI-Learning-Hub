"""Sharpen by adding back the detail a blur removed, or raising the contrast just stretches everything.

"Make it sharper" tempts an obvious move: turn up the contrast. But global contrast is a point operation --
new = (old - mean) * k + mean -- it decides each pixel from its own value alone. It pushes darks darker and
brights brighter across the whole image, changing every pixel including the flat regions, and it shifts the
overall look. What it cannot do is add LOCAL sharpness: a smooth ramp stays a smooth ramp, just steeper end
to end. Sharpness is an edge phenomenon, and a point operation is blind to where the edges are.

Unsharp masking is the real thing. Blur the signal to get its low-frequency part, subtract to recover the
high-frequency detail (detail = signal - blur), then add a scaled copy of that detail back:
sharpened = signal + amount * detail. In a flat region the blur equals the signal, so detail is exactly zero
and the pixel is left untouched. At an edge the detail is large, and adding it back overshoots -- the value
dips below the original low and rises above the original high, the "halo" the eye reads as crisp. It is a
spatial operation: it acts only where the neighborhood varies.

On this fixture the signal is a flat 10, a step up to 30, and a flat 30. Unsharp masking leaves the four flat
pixels exactly 10 and 30 and turns the edge into 5 then 35 -- an overshoot past the original range. Global
contrast (k=1.5 about the mean 20) rewrites all six pixels to 5 and 35, changing the flat regions too, with
no localized halo. Both widen the edge; only one is actually sharpening. This computes both.

  --sharpen    the signal, its blur, the recovered detail, and the unsharp vs contrast results
  --edges      the flat-region change and the edge overshoot for each method
  --check      unsharp leaves flat regions exactly unchanged and overshoots the edge; contrast rewrites all

The signal, amount, and contrast multiplier are the fixture; every transform is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "signal.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def blur(sig):
    """A normalized [1,2,1]/4 smoothing with replicate padding at the borders."""
    out = []
    for i in range(len(sig)):
        left = sig[i - 1] if i > 0 else sig[i]
        right = sig[i + 1] if i < len(sig) - 1 else sig[i]
        out.append((left + 2 * sig[i] + right) / 4.0)
    return out


def detail(sig):
    """The high-frequency part the blur removed: signal minus blur."""
    b = blur(sig)
    return [sig[i] - b[i] for i in range(len(sig))]


def unsharp(sig, amount):
    """Add the detail back, scaled by amount: sharpened = signal + amount * detail."""
    d = detail(sig)
    return [sig[i] + amount * d[i] for i in range(len(sig))]


def contrast(sig, k):
    """A global point operation: push every pixel away from the mean by factor k."""
    m = sum(sig) / len(sig)
    return [(v - m) * k + m for v in sig]


def fmt(seq):
    return " ".join("%5.1f" % v for v in seq)


def max_gradient(seq):
    return max(abs(seq[i] - seq[i - 1]) for i in range(1, len(seq)))


# ----------------------------------------------------------------- printing

def sharpen_view(data):
    sig, amt, k = data["signal"], data["amount"], data["contrast_k"]
    print("SHARPEN — unsharp mask (amount %.1f) vs global contrast (k %.1f)" % (amt, k))
    print("-" * 58)
    print("  signal:     %s" % fmt(sig))
    print("  blur:       %s" % fmt(blur(sig)))
    print("  detail:     %s   (signal - blur)" % fmt(detail(sig)))
    print("  unsharp:    %s   signal + %.1f*detail" % (fmt(unsharp(sig, amt)), amt))
    print("  contrast:   %s   (v - mean)*%.1f + mean" % (fmt(contrast(sig, k)), k))
    print("-" * 58)
    print("  detail is 0 in the flat runs; unsharp only moves the edge.")


def edges_view(data):
    sig, amt, k = data["signal"], data["amount"], data["contrast_k"]
    u, c, d = unsharp(sig, amt), contrast(sig, k), detail(sig)
    flat = [i for i in range(len(sig)) if d[i] == 0]
    print("EDGES — flat-region change and edge overshoot")
    print("-" * 58)
    print("  flat pixels (detail==0): indices %s" % flat)
    print("  unsharp changed flat pixels:  %d" % sum(1 for i in flat if u[i] != sig[i]))
    print("  contrast changed flat pixels: %d" % sum(1 for i in flat if c[i] != sig[i]))
    print("  original range [%.1f, %.1f]" % (min(sig), max(sig)))
    print("  unsharp range  [%.1f, %.1f]  (overshoots the edge)" % (min(u), max(u)))
    print("  contrast range [%.1f, %.1f]" % (min(c), max(c)))
    print("-" * 58)
    print("  max adjacent gradient: signal %.1f  unsharp %.1f  contrast %.1f"
          % (max_gradient(sig), max_gradient(u), max_gradient(c)))


def check(data):
    print("SELF-TEST — unsharp leaves flat regions exactly unchanged and overshoots the edge; contrast rewrites all")
    print("-" * 104)
    sig, amt, k = data["signal"], data["amount"], data["contrast_k"]
    u, c, d = unsharp(sig, amt), contrast(sig, k), detail(sig)
    flat = [i for i in range(len(sig)) if d[i] == 0]

    unsharp_leaves_flat = all(u[i] == sig[i] for i in flat)
    print("  unsharp leaves every flat pixel unchanged = %s (flat indices %s)" % (unsharp_leaves_flat, flat))

    contrast_changes_flat = any(c[i] != sig[i] for i in flat)
    print("  contrast changes flat pixels = %s (e.g. index %d: %.1f -> %.1f)"
          % (contrast_changes_flat, flat[0], sig[flat[0]], c[flat[0]]))

    unsharp_overshoots = min(u) < min(sig) and max(u) > max(sig)
    print("  unsharp overshoots the original range (the halo) = %s ([%.1f,%.1f] vs [%.1f,%.1f])"
          % (unsharp_overshoots, min(u), max(u), min(sig), max(sig)))

    both_steepen_edge = max_gradient(u) > max_gradient(sig) and max_gradient(c) > max_gradient(sig)
    print("  both raise the edge gradient = %s (%.1f -> unsharp %.1f, contrast %.1f)"
          % (both_steepen_edge, max_gradient(sig), max_gradient(u), max_gradient(c)))

    detail_zero_in_flat = all(d[i] == 0 for i in flat) and any(d[i] != 0 for i in range(len(sig)))
    print("  detail is zero in flat runs, nonzero at the edge = %s" % detail_zero_in_flat)

    ok = unsharp_leaves_flat and contrast_changes_flat and unsharp_overshoots and both_steepen_edge and detail_zero_in_flat
    print("-" * 104)
    print("SELF-TEST %s  unsharp_leaves_flat=%s  contrast_changes_flat=%s  unsharp_overshoots=%s  both_steepen_edge=%s  detail_zero_in_flat=%s"
          % ("PASS" if ok else "FAIL", unsharp_leaves_flat, contrast_changes_flat, unsharp_overshoots, both_steepen_edge, detail_zero_in_flat))
    return ok


def main():
    p = argparse.ArgumentParser(description="Sharpen by adding back removed detail (unsharp mask), not by raising contrast.")
    p.add_argument("--sharpen", action="store_true")
    p.add_argument("--edges", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("length=%d  amount=%.1f  contrast_k=%.1f  file=%s  (the signal is a fixture)"
          % (len(data["signal"]), data["amount"], data["contrast_k"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.sharpen:
        sharpen_view(data)
    elif args.edges:
        edges_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
