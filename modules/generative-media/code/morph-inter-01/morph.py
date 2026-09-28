"""Open (erode then dilate) to remove specks, or a plain erosion also eats a layer off the shape you kept.

Erosion is the simple way to delete salt noise from a binary image: keep a foreground pixel only if all of its
neighbors are foreground too, and any isolated speck -- a pixel with background around it -- vanishes. It works,
but it is indiscriminate. The same rule that deletes the speck also peels one layer off every real object, so a
3x3 blob you wanted to keep shrinks to a single pixel. You removed the noise and damaged the signal in the same
pass, and if you erode again to catch bigger noise you erode the object away entirely. Erosion cannot tell a
speck from the edge of a real shape; it treats every boundary pixel the same.

Opening separates the two goals by following the erosion with a dilation -- the mirror operation that regrows
every shape by a layer. The erosion still deletes the speck, and because a speck erased to nothing has nothing to
grow back from, the dilation cannot resurrect it. But the blob, merely shrunk rather than erased, IS grown back:
the dilation restores the layer the erosion peeled, returning it to its original size. Erode-then-dilate removes
anything smaller than the structuring element while leaving everything larger unchanged. That pairing -- erosion
for removal, dilation for repair -- is a morphological opening, and it is the right tool for despeckling because
it fixes the collateral damage erosion alone leaves behind.

On this fixture a 3x3 blob (area 9) sits beside a 1-pixel speck. Erosion alone removes the speck but shrinks the
blob from 9 pixels to 1. Opening removes the speck AND restores the blob to its full 9 pixels. Same despeckling,
no collateral damage. This computes both.

  --steps      the original, the erosion, and the opening as grids, side by side
  --area       the blob's surviving pixel count and whether the speck is gone, under erosion vs opening
  --check      erosion removes the speck but shrinks the blob; opening removes the speck and preserves the blob

The image is the fixture; every pixel is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "morph.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def get(grid, r, c):
    """Pixel value with out-of-bounds treated as background (0)."""
    if 0 <= r < len(grid) and 0 <= c < len(grid[0]):
        return grid[r][c]
    return 0


def erode(grid):
    """Foreground only where every cell in the 3x3 neighborhood is foreground."""
    return [[1 if all(get(grid, r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)) else 0
             for c in range(len(grid[0]))] for r in range(len(grid))]


def dilate(grid):
    """Foreground where any cell in the 3x3 neighborhood is foreground."""
    return [[1 if any(get(grid, r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)) else 0
             for c in range(len(grid[0]))] for r in range(len(grid))]


def opening(grid):
    """Erosion followed by dilation."""
    return dilate(erode(grid))


def area(grid):
    return sum(sum(row) for row in grid)


# ----------------------------------------------------------------- printing

def as_text(grid):
    return "\n".join("  " + " ".join("#" if v else "." for v in row) for row in grid)


def steps_view(data):
    grid = data["grid"]
    print("STEPS — original, erosion, opening (# foreground, . background)")
    print("-" * 40)
    print("original (blob + speck):")
    print(as_text(grid))
    print("erosion (speck gone, blob shrunk to 1):")
    print(as_text(erode(grid)))
    print("opening = erode then dilate (speck gone, blob restored):")
    print(as_text(opening(grid)))
    print("-" * 40)
    print("  erosion peels the blob to a dot; the dilation in opening grows it back.")


def area_view(data):
    grid, sr_sc = data["grid"], data["speck_at"]
    sr, sc = sr_sc
    er, op = erode(grid), opening(grid)
    print("AREA — surviving foreground and the speck, under erosion vs opening")
    print("-" * 56)
    print("  operation   total px   speck present   blob preserved")
    print("  original    %2d         %s            (area %d)" % (area(grid), bool(grid[sr][sc]), data["blob_area"]))
    print("  erosion     %2d         %s           %s" % (area(er), bool(er[sr][sc]), area(er) == data["blob_area"]))
    print("  opening     %2d         %s           %s" % (area(op), bool(op[sr][sc]), area(op) == data["blob_area"]))
    print("-" * 56)
    print("  both remove the speck; only opening keeps the blob at its full %d pixels." % data["blob_area"])


def check(data):
    print("SELF-TEST — erosion removes the speck but shrinks the blob; opening removes the speck and preserves the blob")
    print("-" * 108)
    grid, sr_sc, blob = data["grid"], data["speck_at"], data["blob_area"]
    sr, sc = sr_sc
    er, op = erode(grid), opening(grid)

    erosion_removes_speck = er[sr][sc] == 0
    print("  erosion removes the noise speck = %s" % erosion_removes_speck)

    erosion_shrinks_blob = area(er) < blob
    print("  erosion shrinks the blob below its true area = %s (%d < %d)" % (erosion_shrinks_blob, area(er), blob))

    opening_removes_speck = op[sr][sc] == 0
    print("  opening also removes the speck = %s" % opening_removes_speck)

    opening_preserves_blob = area(op) == blob
    print("  opening keeps the blob at its full area = %s (%d = %d)" % (opening_preserves_blob, area(op), blob))

    opening_differs_from_erosion = op != er
    print("  opening differs from erosion alone (dilation restored the blob) = %s" % opening_differs_from_erosion)

    ok = erosion_removes_speck and erosion_shrinks_blob and opening_removes_speck and opening_preserves_blob and opening_differs_from_erosion
    print("-" * 108)
    print("SELF-TEST %s  erosion_removes_speck=%s  erosion_shrinks_blob=%s  opening_removes_speck=%s  opening_preserves_blob=%s  opening_differs_from_erosion=%s"
          % ("PASS" if ok else "FAIL", erosion_removes_speck, erosion_shrinks_blob, opening_removes_speck, opening_preserves_blob, opening_differs_from_erosion))
    return ok


def main():
    p = argparse.ArgumentParser(description="Morphological opening (erode then dilate) despeckles a binary image without shrinking the objects, which erosion alone does.")
    p.add_argument("--steps", action="store_true")
    p.add_argument("--area", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("grid=%dx%d  blob_area=%d  speck_at=%s  file=%s  (the image is a fixture)"
          % (len(data["grid"]), len(data["grid"][0]), data["blob_area"], data["speck_at"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.steps:
        steps_view(data)
    elif args.area:
        area_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
