"""Combine both gradient directions, or an edge detector blind to one orientation misses half the edges.

An edge is where brightness changes fast. The Sobel operator measures that change with two derivatives: gx,
the horizontal gradient (how fast brightness changes left-to-right), and gy, the vertical gradient (top-to-
bottom). A vertical edge -- dark on the left, bright on the right -- is a big left-to-right change, so gx is
large; but going top-to-bottom nothing changes, so gy is zero. A horizontal edge is the mirror image: gy
large, gx zero. If you build your edge detector on gx alone, you catch every vertical edge and completely
miss every horizontal one, because a horizontal edge produces gx = 0. Half the edges in the image are
invisible to you, and nothing about the number gx tells you they are there.

The fix is to combine the two directions into the gradient magnitude: sqrt(gx*gx + gy*gy). This is the length
of the gradient vector, and it is large whenever brightness changes fast in ANY direction -- vertical,
horizontal, or diagonal. A vertical edge (gx=40, gy=0) and a horizontal edge (gx=0, gy=40) both give
magnitude 40; a diagonal edge splits the change across both and the magnitude still fires. The magnitude is
orientation-agnostic, which is exactly what "find the edges" requires; a single derivative is orientation-
blind, which is exactly the bug.

On this fixture the vertical edge gives gx=40, gy=0; the horizontal edge gives gx=0, gy=40; the diagonal
gives gx=30, gy=30. A gx-only detector scores the horizontal edge at 0 -- missed -- while the magnitude scores
all three above 40. This computes both.

  --gradients   gx, gy, and the magnitude for each edge orientation
  --detect      what a gx-only detector catches vs what the magnitude catches, per edge
  --check       gx alone misses the horizontal edge; the magnitude catches every orientation

The images are the fixture; every gradient is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "edges.json"

GX_KERNEL = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
GY_KERNEL = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def convolve_center(img, kernel):
    """Apply a 3x3 kernel at the center of a 3x3 image (one response)."""
    return sum(img[r][c] * kernel[r][c] for r in range(3) for c in range(3))


def gx(img):
    return convolve_center(img, GX_KERNEL)


def gy(img):
    return convolve_center(img, GY_KERNEL)


def magnitude(img):
    """The gradient magnitude: length of the (gx, gy) vector -- large for an edge in any direction."""
    return math.hypot(gx(img), gy(img))


# ----------------------------------------------------------------- printing

def gradients_view(data):
    print("GRADIENTS — Sobel gx, gy, and magnitude at the center of each edge")
    print("-" * 58)
    print("  edge          gx     gy    magnitude")
    for name, img in data["images"].items():
        print("  %-11s %5.0f  %5.0f    %7.2f" % (name, gx(img), gy(img), magnitude(img)))
    print("-" * 58)
    print("  a vertical edge lives in gx, a horizontal edge in gy.")


def detect_view(data):
    thr = 20.0
    print("DETECT — a gx-only detector vs the magnitude (threshold %.0f)" % thr)
    print("-" * 58)
    print("  edge          gx-only          magnitude")
    for name, img in data["images"].items():
        g, m = abs(gx(img)), magnitude(img)
        print("  %-11s %-16s %s" % (name,
              "EDGE (%.0f)" % g if g >= thr else "missed (%.0f)" % g,
              "edge (%.2f)" % m if m >= thr else "missed (%.2f)" % m))
    print("-" * 58)
    print("  gx-only misses the horizontal edge; the magnitude catches all three.")


def check(data):
    print("SELF-TEST — gx alone misses the horizontal edge; the magnitude catches every orientation")
    print("-" * 100)
    imgs = data["images"]
    thr = 20.0

    gx_detects_vertical = abs(gx(imgs["vertical"])) >= thr
    print("  gx detects the vertical edge = %s (gx %.0f)" % (gx_detects_vertical, gx(imgs["vertical"])))

    gx_misses_horizontal = abs(gx(imgs["horizontal"])) < thr
    print("  gx misses the horizontal edge = %s (gx %.0f)" % (gx_misses_horizontal, gx(imgs["horizontal"])))

    gy_detects_horizontal = abs(gy(imgs["horizontal"])) >= thr
    print("  gy detects the horizontal edge = %s (gy %.0f)" % (gy_detects_horizontal, gy(imgs["horizontal"])))

    magnitude_detects_all = all(magnitude(imgs[name]) >= thr for name in imgs)
    print("  the magnitude detects every orientation = %s (min %.2f)" % (magnitude_detects_all, min(magnitude(imgs[name]) for name in imgs)))

    magnitude_is_hypot = all(abs(magnitude(imgs[name]) - math.sqrt(gx(imgs[name]) ** 2 + gy(imgs[name]) ** 2)) < 1e-9 for name in imgs)
    print("  the magnitude equals sqrt(gx^2 + gy^2) = %s" % magnitude_is_hypot)

    ok = gx_detects_vertical and gx_misses_horizontal and gy_detects_horizontal and magnitude_detects_all and magnitude_is_hypot
    print("-" * 100)
    print("SELF-TEST %s  gx_detects_vertical=%s  gx_misses_horizontal=%s  gy_detects_horizontal=%s  magnitude_detects_all=%s  magnitude_is_hypot=%s"
          % ("PASS" if ok else "FAIL", gx_detects_vertical, gx_misses_horizontal, gy_detects_horizontal, magnitude_detects_all, magnitude_is_hypot))
    return ok


def main():
    p = argparse.ArgumentParser(description="Combine both Sobel gradients into a magnitude so no edge orientation is missed.")
    p.add_argument("--gradients", action="store_true")
    p.add_argument("--detect", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("images=%d  file=%s  (the images are a fixture)" % (len(data["images"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.gradients:
        gradients_view(data)
    elif args.detect:
        detect_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
