"""Precompute a summed-area table, and any rectangle's sum is four lookups -- a box blur costs the same at any radius.

A box filter -- the simplest blur -- replaces each pixel with the average of a square window around it. Averaging means
summing every pixel in the window and dividing by its area, so the naive cost is k*k additions per output pixel for a
k-wide window. That is fine for a 3x3 blur and ruinous for a 51x51 one: the work per pixel grows with the WINDOW AREA,
so doubling the blur radius quadruples the cost, and a large-radius box blur over a big image becomes the bottleneck.
The waste is that neighboring windows overlap almost completely and the naive loop re-adds the same pixels for every
output.

A summed-area table (integral image) pays that sum once. Precompute, in a single pass, the sum of every top-left
rectangle: entry S[i][j] is the total of all pixels above and to the left of (i, j). Then the sum over ANY rectangle is
four lookups by inclusion-exclusion -- the big corner minus the two edge rectangles plus the corner that got subtracted
twice -- regardless of how big the rectangle is. A 3x3 window and a 300x300 window both cost the same four reads. So a
box blur becomes: build the table once (one pass over the image), then four lookups per output pixel, and the total
work no longer depends on the blur radius at all. Constant per pixel, any size.

On this fixture the four query rectangles sum to the same values whether added up directly or read off the table in
four lookups -- the table is exact, not approximate. And the operation count for a box blur is k*k per pixel the naive
way but a flat 4 per pixel with the table, so at a 15-wide window the naive filter does 225 additions per pixel and the
table does 4. This computes both.

  --sum     each query rectangle summed directly vs by the four-corner table formula -- they match exactly
  --cost    additions per output pixel for a box blur, naive (k*k) vs summed-area table (4), across window sizes
  --check   the table sum equals the direct sum for every rectangle; its cost is 4 per pixel, flat in the window size

The image, query rectangles, and window sizes are the fixture; every sum and count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "integral.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def build_sat(image):
    """Summed-area table with a zero top/left border: S[i][j] = sum of image[0:i][0:j]."""
    rows, cols = len(image), len(image[0])
    s = [[0] * (cols + 1) for _ in range(rows + 1)]
    for i in range(1, rows + 1):
        for j in range(1, cols + 1):
            s[i][j] = image[i - 1][j - 1] + s[i - 1][j] + s[i][j - 1] - s[i - 1][j - 1]
    return s


def sat_rect_sum(s, r0, c0, r1, c1):
    """Sum over the half-open rectangle rows [r0,r1), cols [c0,c1) via four-corner inclusion-exclusion."""
    return s[r1][c1] - s[r0][c1] - s[r1][c0] + s[r0][c0]


def direct_rect_sum(image, r0, c0, r1, c1):
    """The same rectangle summed the naive way: add up every pixel in it."""
    return sum(image[i][j] for i in range(r0, r1) for j in range(c0, c1))


def naive_ops_per_pixel(k):
    """Additions per output pixel for a naive k-wide box blur: one per pixel in the window."""
    return k * k


def sat_ops_per_pixel():
    """Additions/subtractions per output pixel for a summed-area box blur: four corner lookups, any window size."""
    return 4


# ----------------------------------------------------------------- printing

def sum_view(data):
    image = data["image"]
    s = build_sat(image)
    print("SUM — each rectangle: direct addition vs the four-corner table lookup")
    print("-" * 64)
    print("  rectangle (r0,c0,r1,c1)     direct   table(4 lookups)   match")
    for r0, c0, r1, c1 in data["windows"]:
        d = direct_rect_sum(image, r0, c0, r1, c1)
        t = sat_rect_sum(s, r0, c0, r1, c1)
        print("  (%d,%d,%d,%d)%s   %-6d   %-16d   %s" % (r0, c0, r1, c1, " " * (12 - len("%d,%d,%d,%d" % (r0, c0, r1, c1))), d, t, d == t))
    print("-" * 64)
    print("  the table adds pixels above-left once, then answers any rectangle in four reads.")


def cost_view(data):
    print("COST — additions per output pixel for a box blur, by window size")
    print("-" * 58)
    print("  window k   naive (k*k)   summed-area (4)   naive/table")
    for k in data["blur_sizes"]:
        naive = naive_ops_per_pixel(k)
        print("  %-8d   %-11d   %-15d   %dx" % (k, naive, sat_ops_per_pixel(), naive // sat_ops_per_pixel()))
    print("-" * 58)
    print("  the table's cost is flat at 4; the naive filter's grows with the window area.")


def check(data):
    print("SELF-TEST — the table sum equals the direct sum for every rectangle; its cost is 4 per pixel, flat in window size")
    print("-" * 114)
    image = data["image"]
    s = build_sat(image)

    all_match = all(sat_rect_sum(s, *w) == direct_rect_sum(image, *w) for w in data["windows"])
    print("  every query rectangle: table sum equals direct sum = %s" % all_match)

    rows, cols = len(image), len(image[0])
    whole = sat_rect_sum(s, 0, 0, rows, cols)
    whole_correct = whole == sum(sum(row) for row in image)
    print("  the full-image rectangle sums to the total of all pixels = %s (%d)" % (whole_correct, whole))

    single = all(sat_rect_sum(s, i, j, i + 1, j + 1) == image[i][j] for i in range(rows) for j in range(cols))
    print("  a 1x1 rectangle recovers the exact pixel (border indexing correct) = %s" % single)

    sat_flat = len({sat_ops_per_pixel() for _ in data["blur_sizes"]}) == 1
    print("  the table's per-pixel cost is the same for every window size = %s (%d)" % (sat_flat, sat_ops_per_pixel()))

    naive_grows = all(naive_ops_per_pixel(k2) > naive_ops_per_pixel(k1)
                      for k1, k2 in zip(sorted(data["blur_sizes"]), sorted(data["blur_sizes"])[1:]))
    print("  the naive per-pixel cost grows with the window size = %s (%s)" % (naive_grows, [naive_ops_per_pixel(k) for k in data["blur_sizes"]]))

    table_cheaper = all(sat_ops_per_pixel() < naive_ops_per_pixel(k) for k in data["blur_sizes"])
    print("  the table is cheaper per pixel at every listed window size = %s" % table_cheaper)

    ok = all_match and whole_correct and single and sat_flat and naive_grows and table_cheaper
    print("-" * 114)
    print("SELF-TEST %s  all_match=%s  whole_correct=%s  single=%s  sat_flat=%s  naive_grows=%s  table_cheaper=%s"
          % ("PASS" if ok else "FAIL", all_match, whole_correct, single, sat_flat, naive_grows, table_cheaper))
    return ok


def main():
    p = argparse.ArgumentParser(description="A summed-area table (integral image) answers any rectangle sum in four lookups, so a box blur costs a constant four operations per pixel regardless of the window size.")
    p.add_argument("--sum", action="store_true")
    p.add_argument("--cost", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("image=%dx%d  windows=%d  blur_sizes=%s  file=%s  (the image and rectangles are a fixture)"
          % (len(data["image"]), len(data["image"][0]), len(data["windows"]), data["blur_sizes"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.sum:
        sum_view(data)
    elif args.cost:
        cost_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
