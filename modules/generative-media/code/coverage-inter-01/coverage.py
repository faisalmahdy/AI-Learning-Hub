"""Rasterize an edge by pixel coverage -- the fraction of each pixel the shape covers -- not by a single center-inside test, or a slanted edge becomes a staircase of hard steps and the rendered area jumps a whole pixel at a time.

Turning a continuous shape into pixels forces a yes/no decision at every pixel the edge crosses. The naive decision tests one point, the pixel's center: if the center is inside the shape the pixel is fully on (1), otherwise fully off (0). Simple, and wrong at the edge, because a pixel the edge passes through is neither fully inside nor fully outside -- it is partly covered, and a center test throws that partial information away.

The visible cost is jaggies. A slanted edge, forced to be all-or-nothing per pixel, becomes a staircase: each row flips from off to on at some column, and the steps between rows are hard, so the smooth line renders as a jagged one. The measurable cost is area: because each pixel counts as a whole 0 or 1, the rasterized area jumps by a full pixel as the edge moves, and the total 'ink' misestimates the true area the shape covers.

Coverage-based anti-aliasing answers the better question: how much of this pixel does the shape cover. A pixel the edge cuts gets a fractional value equal to the covered fraction, so the edge becomes a smooth ramp of partial pixels rather than a hard step, and -- the property that makes it correct, not just prettier -- the summed coverage equals the true covered area. The eye reads the ramp of partial pixels as a clean edge.

The coverage fraction can be computed analytically for simple shapes, but the general and simplest estimate is supersampling: test many sub-points spread across each pixel and take the fraction that fall inside. More sub-samples give a finer estimate; a center test is just supersampling with a single sub-point at the center, which is why it can only ever return 0 or 1.

On this fixture a straight edge crosses a small grid. The center test renders every pixel as 0 or 1 and its ink total misses the true area; the coverage raster has fractional pixels along the edge and its total matches the true area closely. This computes both.

  --binary    the center-inside raster (every pixel 0 or 1) and its ink total
  --coverage  the coverage raster (fractional edge pixels) and its total vs the true area
  --check     the center test is all-or-nothing and misestimates the area; coverage has partial pixels and matches the true area

grid size, the edge a*x+b*y=c, and the supersample count are the fixture; the two rasters, their ink totals, and the true area are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "coverage.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def inside(x, y, data):
    """The shape is the half-plane a*x + b*y < c."""
    return data["a"] * x + data["b"] * y < data["c"]


def binary_pixel(i, j, data):
    """Center-inside test: 1 if the pixel center is inside, else 0."""
    return 1.0 if inside(i + 0.5, j + 0.5, data) else 0.0


def coverage_pixel(i, j, data, n):
    """Fraction of the pixel covered, estimated by an n-by-n grid of sub-samples."""
    hits = 0
    for sy in range(n):
        for sx in range(n):
            x = i + (sx + 0.5) / n
            y = j + (sy + 0.5) / n
            if inside(x, y, data):
                hits += 1
    return hits / (n * n)


def binary_raster(data):
    return [[binary_pixel(i, j, data) for i in range(data["grid_w"])] for j in range(data["grid_h"])]


def coverage_raster(data, n):
    return [[coverage_pixel(i, j, data, n) for i in range(data["grid_w"])] for j in range(data["grid_h"])]


def total(raster):
    return sum(sum(row) for row in raster)


def true_area(data):
    """A high-resolution coverage estimate over the whole grid -- the reference area."""
    return total(coverage_raster(data, 64))


# ----------------------------------------------------------------- printing

def _show(raster):
    for row in raster:
        print("  " + " ".join("%4.2f" % v for v in row))


def binary_view(data):
    r = binary_raster(data)
    print("BINARY — center-inside test (every pixel 0 or 1)")
    print("-" * 40)
    _show(r)
    print("-" * 40)
    print("  ink total = %.2f  (whole pixels only)" % total(r))


def coverage_view(data):
    r = coverage_raster(data, data["supersample"])
    print("COVERAGE — fraction of each pixel covered (supersample %d)" % data["supersample"])
    print("-" * 40)
    _show(r)
    print("-" * 40)
    print("  ink total = %.4f   true area = %.4f" % (total(r), true_area(data)))


def check(data):
    print("SELF-TEST — the center test is all-or-nothing and misestimates the area; coverage has partial pixels and matches the true area")
    print("-" * 112)
    n = data["supersample"]
    b = binary_raster(data)
    cov = coverage_raster(data, n)
    area = true_area(data)

    flat = [v for row in b for v in row]
    binary_all_or_nothing = all(v == 0.0 or v == 1.0 for v in flat)
    print("  the center test makes every pixel 0 or 1 = %s" % binary_all_or_nothing)

    cflat = [v for row in cov for v in row]
    coverage_has_partial = any(0.0 < v < 1.0 for v in cflat)
    print("  the coverage raster has partial (edge) pixels = %s (%d of %d)" % (coverage_has_partial, sum(1 for v in cflat if 0.0 < v < 1.0), len(cflat)))

    coverage_area_err = abs(total(cov) - area)
    binary_area_err = abs(total(b) - area)

    coverage_matches_area = coverage_area_err < 0.05
    print("  the coverage total matches the true area = %s (err %.4f)" % (coverage_matches_area, coverage_area_err))

    binary_misestimates_area = binary_area_err > coverage_area_err
    print("  the center-test total misestimates the area by more = %s (%.4f vs %.4f)" % (binary_misestimates_area, binary_area_err, coverage_area_err))

    # the coverage edge has intermediate values where the center test has only a hard 0->1 step
    edge_is_ramp = coverage_has_partial and not any(0.0 < v < 1.0 for v in flat)
    print("  coverage ramps the edge where the center test steps hard = %s" % edge_is_ramp)

    ok = (binary_all_or_nothing and coverage_has_partial and coverage_matches_area
          and binary_misestimates_area and edge_is_ramp)
    print("-" * 112)
    print("SELF-TEST %s  binary_all_or_nothing=%s  coverage_has_partial=%s  coverage_matches_area=%s  binary_misestimates_area=%s  edge_is_ramp=%s"
          % ("PASS" if ok else "FAIL", binary_all_or_nothing, coverage_has_partial, coverage_matches_area,
             binary_misestimates_area, edge_is_ramp))
    return ok


def main():
    p = argparse.ArgumentParser(description="Coverage anti-aliasing: rasterize an edge by pixel coverage (the fraction of each pixel the shape covers), not by a single center-inside test, or a slanted edge becomes a staircase of hard steps and the rendered area jumps a whole pixel at a time.")
    p.add_argument("--binary", action="store_true")
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("grid=%dx%d  edge %.1f*x+%.1f*y=%.1f  supersample=%d  file=%s  (these are a fixture)"
          % (data["grid_w"], data["grid_h"], data["a"], data["b"], data["c"], data["supersample"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.binary:
        binary_view(data)
    elif args.coverage:
        coverage_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
