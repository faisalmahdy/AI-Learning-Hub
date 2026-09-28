"""EXIF orientation is stored as a tag separate from the pixels, so a pipeline must APPLY it to the pixels before display -- ignoring the tag shows the image sideways, and stripping the tag without first baking the rotation loses the orientation forever.

A camera writes pixels in the sensor's native order and records how it was held as an Orientation tag: 1 is already upright, 3 is 180 degrees, 6 is rotate 90 clockwise to display, 8 is rotate 90 counter-clockwise, with mirrored variants for the rest. The pixels are not upright; the tag says how to make them upright.

A correct viewer applies the tag before showing the image. A naive tool that decodes the raw pixel array and treats it as final shows a portrait photo lying on its side -- the classic "why is my photo sideways" bug. The pixels are right; the tag was ignored.

The worse failure is re-encoding. Many pipelines strip metadata when they resize or convert a file, and if they drop the orientation tag without first applying it, the image is now stored in its sideways pixel order with a tag of 1, which every viewer reads as "already upright." The one piece of information that could have corrected it is gone, and the image is permanently wrong.

The fix is to bake the orientation in: physically rotate the pixel array according to the tag, then set the tag to 1. Now the stored pixels are upright, the tag is honest, and no viewer needs to do anything. Applying then resetting is safe; stripping without applying is destruction.

On this fixture the stored grid is 2 rows by 3 columns with tag 6, so the correct display is that grid rotated 90 clockwise to 3 rows by 2 columns. Ignoring the tag shows the raw 2x3 grid (wrong). Stripping the tag leaves the raw 2x3 grid with tag 1 (wrong and unrecoverable). Baking rotates to 3x2 and sets tag 1 (correct). This computes all of it.

  --display  the raw grid, the correct oriented display, and what ignoring the tag shows
  --handle   stripping the tag (loses orientation) versus baking it in (correct and permanent)
  --check    ignoring the tag differs from the correct display, stripping the tag is permanently wrong, and baking matches the correct display with the tag reset to 1

the stored grid and orientation tag are the fixture; the correct display and the three handling strategies are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "orient.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def rot90cw(grid):
    """Rotate a grid 90 degrees clockwise; rows and columns swap."""
    return [list(row) for row in zip(*grid[::-1])]


def rot90ccw(grid):
    """Rotate a grid 90 degrees counter-clockwise."""
    return [list(row) for row in zip(*grid)][::-1]


def rot180(grid):
    """Rotate a grid 180 degrees."""
    return [row[::-1] for row in grid[::-1]]


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


def dims(grid):
    """(rows, columns) of a grid."""
    return (len(grid), len(grid[0]))


# ----------------------------------------------------------------- printing

def _fmt(grid):
    return " / ".join(" ".join(row) for row in grid)


def display_view(d):
    raw, tag = d["stored_grid"], d["orientation"]
    correct = apply_orientation(raw, tag)
    print("DISPLAY — stored tag %d says how to orient the pixels" % tag)
    print("-" * 64)
    print("  raw pixels        %s  dims %s" % (_fmt(raw), dims(raw)))
    print("  correct display   %s  dims %s   (tag applied)" % (_fmt(correct), dims(correct)))
    print("  ignoring the tag  %s  dims %s   <- shown sideways" % (_fmt(raw), dims(raw)))
    print("-" * 64)
    print("  the pixels are stored sideways; the tag is what makes them upright")


def handle_view(d):
    raw, tag = d["stored_grid"], d["orientation"]
    correct = apply_orientation(raw, tag)
    stripped_grid, stripped_tag = [row[:] for row in raw], 1
    baked_grid, baked_tag = apply_orientation(raw, tag), 1
    print("HANDLE — re-encoding the file two ways")
    print("-" * 64)
    print("  strip tag: pixels %s  tag %d   correct? %s   <- orientation lost" % (_fmt(stripped_grid), stripped_tag, stripped_grid == correct))
    print("  bake in  : pixels %s  tag %d   correct? %s" % (_fmt(baked_grid), baked_tag, baked_grid == correct))
    print("-" * 64)
    print("  stripping keeps the sideways pixels and drops the fix; baking rotates then resets the tag")


def check(d):
    print("SELF-TEST — ignoring the tag differs from the correct display, stripping the tag is permanently wrong, and baking matches the correct display with the tag reset to 1")
    print("-" * 112)
    raw, tag = d["stored_grid"], d["orientation"]
    correct = apply_orientation(raw, tag)

    ignore_wrong = raw != correct
    print("  ignoring the tag differs from the correct display = %s (%s vs %s)" % (ignore_wrong, _fmt(raw), _fmt(correct)))

    dims_swap = dims(correct) != dims(raw)
    print("  applying the 90-degree tag swaps rows and columns = %s (%s -> %s)" % (dims_swap, dims(raw), dims(correct)))

    stripped_grid, stripped_tag = [row[:] for row in raw], 1
    strip_permanent_wrong = stripped_grid != correct and stripped_tag == 1
    print("  stripping the tag leaves wrong pixels with an 'upright' tag (unrecoverable) = %s" % strip_permanent_wrong)

    baked_grid, baked_tag = apply_orientation(raw, tag), 1
    bake_correct = baked_grid == correct and baked_tag == 1
    print("  baking rotates the pixels and resets the tag to 1 = %s" % bake_correct)

    ok = (ignore_wrong and dims_swap and strip_permanent_wrong and bake_correct)
    print("-" * 112)
    print("SELF-TEST %s  ignore_wrong=%s  dims_swap=%s  strip_permanent_wrong=%s  bake_correct=%s"
          % ("PASS" if ok else "FAIL", ignore_wrong, dims_swap, strip_permanent_wrong, bake_correct))
    return ok


def main():
    p = argparse.ArgumentParser(description="EXIF orientation: pixels are stored in the sensor's native order with a separate Orientation tag saying how to rotate them for display, so a pipeline must apply the tag to the pixels before display -- ignoring it shows the image sideways, and stripping the tag when re-encoding without first baking the rotation loses the orientation permanently; the fix is to physically rotate the pixels per the tag and then set the tag to 1.")
    p.add_argument("--display", action="store_true")
    p.add_argument("--handle", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("stored dims %s  orientation tag %d  file=%s" % (dims(d["stored_grid"]), d["orientation"], DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.display:
        display_view(d)
    elif args.handle:
        handle_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
