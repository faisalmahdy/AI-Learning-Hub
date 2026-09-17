"""Fitting an image into a target box of a different shape needs ONE uniform scale for both axes -- resizing to the target's exact width and height applies a different scale to each axis and stretches the image, turning a circle into an ellipse while reporting success, because the output is exactly the size that was asked for and only the shape is wrong.

Almost every thumbnail, avatar, and preview path has one line that says "make this image target_w by target_h". The obvious implementation resizes to exactly those dimensions: scale the width by target_w / src_w and the height by target_h / src_h. When the source and the target have the same aspect ratio (width over height) those two scale factors are equal and everything is fine. When they differ -- a 4:3 photo into a square box -- the two factors differ, each axis is scaled by a different amount, and the image is squashed on one axis and stretched on the other.

Nothing errors. The file comes out at exactly the requested size. But a circle has become an ellipse, a face is fat or thin, and text leans. The distortion is invisible to the code and obvious to the eye.

The fix is to choose a single scale for both axes so the aspect ratio is preserved, then decide what to do with the box's leftover space. 'fit' (contain) uses the smaller scale, min(scale_x, scale_y), so the whole image lands inside the box and the short axis gets padding bars -- letterboxing. 'cover' uses the larger scale, max(scale_x, scale_y), so the box is filled completely and the overflow on the long axis is cropped. Both keep the shape; they trade padding against cropping.

On this fixture an 800x600 source (aspect 1.333) goes into a 400x400 box (aspect 1.000). Stretch gives 400x400 at aspect 1.000 -- distorted. Fit gives 400x300 at aspect 1.333 inside the box with padding. Cover gives 533x400 at aspect 1.333 filling the box with crop. This computes all three, and tracks a source circle through each to show the ellipse.

  --stretch  resize-to-fill: exact target size, but the aspect ratio changes and the circle becomes an ellipse
  --fit      contain: one scale, image inside the box with letterbox padding, aspect preserved
  --cover    fill the box with one scale and crop the overflow, aspect preserved
  --check    stretch changes the aspect ratio and ellipticizes the circle, while fit and cover both preserve the aspect and keep the circle round

src and target dimensions and the circle radius are the fixture; every scale factor, output size, aspect ratio, padding, crop, and ellipse axis is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "aspectfit.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def aspect(w, h):
    """Aspect ratio: width divided by height."""
    return w / h


def stretch(src_w, src_h, tw, th):
    """Resize-to-fill: force both dimensions to the target, so each axis gets its own scale."""
    return {"scale_x": tw / src_w, "scale_y": th / src_h, "out_w": tw, "out_h": th}


def fit(src_w, src_h, tw, th):
    """Contain: one scale = min(scale_x, scale_y); the whole image lands inside the box."""
    s = min(tw / src_w, th / src_h)
    out_w, out_h = round(src_w * s), round(src_h * s)
    return {"scale": s, "out_w": out_w, "out_h": out_h,
            "pad_w": tw - out_w, "pad_h": th - out_h}


def cover(src_w, src_h, tw, th):
    """Fill: one scale = max(scale_x, scale_y); the box is filled and the overflow is cropped."""
    s = max(tw / src_w, th / src_h)
    out_w, out_h = round(src_w * s), round(src_h * s)
    return {"scale": s, "out_w": out_w, "out_h": out_h,
            "crop_w": out_w - tw, "crop_h": out_h - th}


def circle_axes(radius, scale_x, scale_y):
    """A source circle of this radius, scaled per-axis, has these two semi-axes (equal = still a circle)."""
    return radius * scale_x, radius * scale_y


# ----------------------------------------------------------------- printing

def stretch_view(data):
    sw, sh, tw, th, r = data["src_w"], data["src_h"], data["target_w"], data["target_h"], data["circle_radius"]
    st = stretch(sw, sh, tw, th)
    ax, ay = circle_axes(r, st["scale_x"], st["scale_y"])
    print("STRETCH — resize-to-fill: force the image to exactly %dx%d" % (tw, th))
    print("-" * 64)
    print("  scale_x = %.3f   scale_y = %.3f   (different per axis)" % (st["scale_x"], st["scale_y"]))
    print("  output %dx%d  aspect %.3f   (source aspect was %.3f)" % (st["out_w"], st["out_h"], aspect(st["out_w"], st["out_h"]), aspect(sw, sh)))
    print("  the source circle r=%d becomes an ellipse: semi-axes %.0f x %.0f" % (r, ax, ay))
    print("-" * 64)
    print("  exactly the requested size, and the wrong shape -- the aspect ratio changed")


def fit_view(data):
    sw, sh, tw, th, r = data["src_w"], data["src_h"], data["target_w"], data["target_h"], data["circle_radius"]
    ft = fit(sw, sh, tw, th)
    ax, ay = circle_axes(r, ft["scale"], ft["scale"])
    print("FIT — contain: one scale, the whole image inside the %dx%d box" % (tw, th))
    print("-" * 64)
    print("  scale = min = %.3f   (same on both axes)" % ft["scale"])
    print("  output %dx%d  aspect %.3f   padding %dx%d (letterbox bars)" % (ft["out_w"], ft["out_h"], aspect(ft["out_w"], ft["out_h"]), ft["pad_w"], ft["pad_h"]))
    print("  the source circle r=%d stays a circle: semi-axes %.0f x %.0f" % (r, ax, ay))
    print("-" * 64)
    print("  aspect preserved; the leftover space becomes padding, nothing is cropped")


def cover_view(data):
    sw, sh, tw, th, r = data["src_w"], data["src_h"], data["target_w"], data["target_h"], data["circle_radius"]
    cv = cover(sw, sh, tw, th)
    ax, ay = circle_axes(r, cv["scale"], cv["scale"])
    print("COVER — fill: one scale, the %dx%d box completely filled" % (tw, th))
    print("-" * 64)
    print("  scale = max = %.3f   (same on both axes)" % cv["scale"])
    print("  output %dx%d  aspect %.3f   crop %dx%d (overflow trimmed)" % (cv["out_w"], cv["out_h"], aspect(cv["out_w"], cv["out_h"]), cv["crop_w"], cv["crop_h"]))
    print("  the source circle r=%d stays a circle: semi-axes %.0f x %.0f" % (r, ax, ay))
    print("-" * 64)
    print("  aspect preserved; the box is filled and the overflow is cropped, no padding")


def check(data):
    print("SELF-TEST — stretch changes the aspect ratio and ellipticizes the circle, while fit and cover both preserve the aspect and keep the circle round")
    print("-" * 112)
    sw, sh, tw, th, r = data["src_w"], data["src_h"], data["target_w"], data["target_h"], data["circle_radius"]
    src_aspect = aspect(sw, sh)
    st, ft, cv = stretch(sw, sh, tw, th), fit(sw, sh, tw, th), cover(sw, sh, tw, th)

    stretch_changes_aspect = abs(aspect(st["out_w"], st["out_h"]) - src_aspect) > 0.01
    print("  stretch output aspect differs from the source = %s (%.3f vs %.3f)" % (stretch_changes_aspect, aspect(st["out_w"], st["out_h"]), src_aspect))

    sax, say = circle_axes(r, st["scale_x"], st["scale_y"])
    stretch_ellipse = abs(sax - say) > 0.5
    print("  stretch turns the circle into an ellipse = %s (semi-axes %.0f vs %.0f)" % (stretch_ellipse, sax, say))

    fit_keeps_aspect = abs(aspect(ft["out_w"], ft["out_h"]) - src_aspect) < 0.01
    print("  fit preserves the aspect ratio = %s (%.3f)" % (fit_keeps_aspect, aspect(ft["out_w"], ft["out_h"])))

    fit_inside_box = ft["out_w"] <= tw and ft["out_h"] <= th
    print("  fit output lies inside the box (padding, no crop) = %s (%dx%d in %dx%d)" % (fit_inside_box, ft["out_w"], ft["out_h"], tw, th))

    cover_keeps_aspect = abs(aspect(cv["out_w"], cv["out_h"]) - src_aspect) < 0.01
    print("  cover preserves the aspect ratio = %s (%.3f)" % (cover_keeps_aspect, aspect(cv["out_w"], cv["out_h"])))

    cover_fills_box = cv["out_w"] >= tw and cv["out_h"] >= th
    print("  cover output covers the box (crop, no padding) = %s (%dx%d over %dx%d)" % (cover_fills_box, cv["out_w"], cv["out_h"], tw, th))

    ok = (stretch_changes_aspect and stretch_ellipse and fit_keeps_aspect
          and fit_inside_box and cover_keeps_aspect and cover_fills_box)
    print("-" * 112)
    print("SELF-TEST %s  stretch_changes_aspect=%s  stretch_ellipse=%s  fit_keeps_aspect=%s  fit_inside_box=%s  cover_keeps_aspect=%s  cover_fills_box=%s"
          % ("PASS" if ok else "FAIL", stretch_changes_aspect, stretch_ellipse, fit_keeps_aspect,
             fit_inside_box, cover_keeps_aspect, cover_fills_box))
    return ok


def main():
    p = argparse.ArgumentParser(description="Aspect-ratio-preserving fit: resizing an image into a target box of a different aspect ratio must use one uniform scale for both axes, because forcing both dimensions to the target scales each axis differently and stretches the image -- a circle becomes an ellipse -- while reporting the exact size that was asked for; 'fit' contains the image with letterbox padding and 'cover' fills the box with a crop, and both preserve the shape.")
    p.add_argument("--stretch", action="store_true")
    p.add_argument("--fit", action="store_true")
    p.add_argument("--cover", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("source %dx%d (aspect %.3f)  target %dx%d (aspect %.3f)  file=%s"
          % (data["src_w"], data["src_h"], aspect(data["src_w"], data["src_h"]),
             data["target_w"], data["target_h"], aspect(data["target_w"], data["target_h"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.stretch:
        stretch_view(data)
    elif args.fit:
        fit_view(data)
    elif args.cover:
        cover_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
