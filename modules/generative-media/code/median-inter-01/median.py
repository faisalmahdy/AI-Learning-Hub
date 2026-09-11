"""Remove salt-and-pepper noise with a median filter -- a mean filter smears the speck and blurs the edge.

A stuck sensor pixel, a bit flip, a compression glitch: these produce impulse noise -- a single pixel
jammed to pure white (salt) or black (pepper), wildly far from its neighbors. The instinct is to blur it
away with a mean (box) filter, averaging each pixel with its neighbors. That is the wrong tool twice over.
Averaging does not delete the speck; it spreads it. A lone 200 among 10s becomes three pixels of ~73,
because the outlier is dragged into every window it touches -- one bad pixel becomes a bad smudge. And the
same averaging blurs every real edge in the image, because a mean straddling a light-to-dark boundary
lands halfway between, softening the very structure you wanted to keep.

The median filter fixes both. Replace each pixel with the median of its neighborhood, not the mean. The
median is a rank statistic: it picks the middle value and ignores how extreme the others are, so a single
outlier -- highest or lowest in its window -- is never selected and simply vanishes. And because the
median of values drawn from one side of an edge is a value from that side, a true edge passes through
unblurred: the filter is edge-preserving. One outlier cannot move a median; a real step survives it.

On this fixture a row of pixels has a clean step from 10 to 80 and one salt speck (a 200 where a 10 should
be). The mean filter leaves total error 236.7 -- it smears the speck across three pixels and softens the
step to 33 and 57. The median filter leaves total error 0.0 -- the speck is gone and the step is exactly
10-to-80, pixel for pixel. This computes both.

  --filter     the clean, noisy, mean-filtered, and median-filtered rows side by side
  --error      per-pixel and total absolute error against the clean row, mean vs median
  --check      the mean filter smears the speck and blurs the edge; the median filter removes it and keeps the edge

The clean row, the speck, and the window are the fixture; every filtered value is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "row.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def at(row, i):
    """Clamp out-of-bounds indices to the edge pixel (edge-extend padding)."""
    return row[min(max(i, 0), len(row) - 1)]


def window(row, i, half):
    return [at(row, j) for j in range(i - half, i + half + 1)]


def mean_filter(row, half):
    return [sum(window(row, i, half)) / (2 * half + 1) for i in range(len(row))]


def median_filter(row, half):
    out = []
    for i in range(len(row)):
        w = sorted(window(row, i, half))
        out.append(w[len(w) // 2])
    return out


def abs_error(a, b):
    return [abs(x - y) for x, y in zip(a, b)]


# ----------------------------------------------------------------- printing

def fmt(row):
    return "[" + " ".join("%5.1f" % x for x in row) + "]"


def filter_view(data):
    clean, noisy, half = data["clean"], noisy_row(data), data["window"] // 2
    print("FILTER — one row of pixels (window %d), clean vs noisy vs filtered" % data["window"])
    print("-" * 62)
    print("  clean:   %s" % fmt(clean))
    print("  noisy:   %s   (speck of %d at index %d)" % (fmt(noisy), data["speck_value"], data["speck_index"]))
    print("  mean:    %s" % fmt(mean_filter(noisy, half)))
    print("  median:  %s" % fmt(median_filter(noisy, half)))
    print("-" * 62)
    print("  mean smears the speck and softens the step; median removes it and keeps the step.")


def error_view(data):
    clean, noisy, half = data["clean"], noisy_row(data), data["window"] // 2
    me, md = abs_error(mean_filter(noisy, half), clean), abs_error(median_filter(noisy, half), clean)
    print("ERROR — absolute error against the clean row")
    print("-" * 62)
    print("  mean err:   %s   total %.1f" % (fmt(me), sum(me)))
    print("  median err: %s   total %.1f" % (fmt(md), sum(md)))
    print("-" * 62)
    print("  the mean spreads the speck's error across pixels; the median leaves none.")


def noisy_row(data):
    row = list(data["clean"])
    row[data["speck_index"]] = data["speck_value"]
    return row


def check(data):
    print("SELF-TEST — the mean filter smears the speck and blurs the edge; the median removes it and keeps the edge")
    print("-" * 106)
    clean, half = data["clean"], data["window"] // 2
    noisy = noisy_row(data)
    mean_out, median_out = mean_filter(noisy, half), median_filter(noisy, half)
    me, md = abs_error(mean_out, clean), abs_error(median_out, clean)
    si, ei = data["speck_index"], data["edge_index"]

    median_removes_speck = md[si] == 0
    print("  median restores the speck pixel exactly = %s (%.1f vs clean %.1f)" % (median_removes_speck, median_out[si], clean[si]))

    mean_smears_speck = sum(1 for i in range(len(clean)) if abs(i - si) <= half and me[i] > 1) >= 2
    print("  mean spreads the speck's error to multiple pixels = %s (%d affected)"
          % (mean_smears_speck, sum(1 for i in range(len(clean)) if abs(i - si) <= half and me[i] > 1)))

    median_keeps_edge = md[ei] == 0 and md[ei - 1] == 0
    print("  median preserves the edge exactly = %s (%.1f, %.1f)" % (median_keeps_edge, median_out[ei - 1], median_out[ei]))

    mean_blurs_edge = me[ei] > 1
    print("  mean blurs the edge = %s (edge error %.1f)" % (mean_blurs_edge, me[ei]))

    median_beats_mean = sum(md) < sum(me)
    print("  median's total error beats the mean's = %s (%.1f vs %.1f)" % (median_beats_mean, sum(md), sum(me)))

    ok = median_removes_speck and mean_smears_speck and median_keeps_edge and mean_blurs_edge and median_beats_mean
    print("-" * 106)
    print("SELF-TEST %s  median_removes_speck=%s  mean_smears_speck=%s  median_keeps_edge=%s  mean_blurs_edge=%s  median_beats_mean=%s"
          % ("PASS" if ok else "FAIL", median_removes_speck, mean_smears_speck, median_keeps_edge, mean_blurs_edge, median_beats_mean))
    return ok


def main():
    p = argparse.ArgumentParser(description="Remove salt-and-pepper noise with a median filter, not a mean filter.")
    p.add_argument("--filter", action="store_true")
    p.add_argument("--error", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pixels=%d  window=%d  speck=%d@%d  file=%s  (the row and speck are a fixture)"
          % (len(data["clean"]), data["window"], data["speck_value"], data["speck_index"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.filter:
        filter_view(data)
    elif args.error:
        error_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
