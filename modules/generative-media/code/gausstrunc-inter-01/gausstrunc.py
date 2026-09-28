"""Size a Gaussian blur kernel to its sigma -- radius about three sigma -- and renormalize; a radius chosen too small drops a real fraction of the kernel's weight, darkening the whole image if unnormalized and staying a narrower blur than requested even if renormalized.

A Gaussian never reaches zero. Its tails run to infinity, so every finite kernel is a truncated Gaussian, and the sampled weights inside the radius sum to less than the full integral. How much less is decided entirely by the radius measured in sigmas: a radius of one sigma keeps only the central bump and leaves a large fraction of the weight in the discarded tails; three sigmas keep about 99.7 percent.

The first consequence is brightness. A convolution kernel should sum to one, so that a flat region of the image comes back unchanged. A truncated Gaussian applied as-is sums to less than one, so it scales every pixel down by the missing fraction and the whole image darkens -- not just the border (that is a different bug, the edge-padding one), but the interior too, uniformly, by however much weight the radius threw away.

The second consequence is subtler and survives the obvious fix. Suppose you renormalize the truncated kernel to sum to one, so brightness is restored. The blur is still wrong: chopping the tails removed the far neighbors that a wide Gaussian is supposed to mix in, so the effective standard deviation of the truncated-and-renormalized kernel is smaller than the sigma you asked for. You requested a sigma-2 blur and got a narrower one, at the right brightness -- a blur that is quietly weaker than specified.

The fix is to size the radius to the sigma before truncating: the conventional choice is ceil(three sigma), which captures essentially all the weight, and then renormalize to correct for the last sliver. Radius is not a free parameter to set small for speed; it is dictated by the sigma.

On this fixture a sigma-2 Gaussian is truncated at radii 2, 4, and 6 (one, two, and three sigmas). At radius 2 the kernel captures well under all the weight and, unnormalized, darkens the image; at radius 6 it captures essentially everything. This computes the coverage, the brightness, and the effective width at each.

  --coverage  the captured weight fraction and the unnormalized brightness at each radius
  --width     the effective standard deviation of the renormalized truncated kernel vs the requested sigma
  --check     a small radius loses weight and darkens the image; renormalizing restores brightness but leaves the blur too narrow; three sigma captures nearly all

sigma and the radii are the fixture; the coverage, brightness, and effective width are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "gausstrunc.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def gaussian_weights(sigma, radius):
    """Sampled (unnormalized) Gaussian weights at integer offsets in [-radius, radius]."""
    return [math.exp(-(x * x) / (2 * sigma * sigma)) for x in range(-radius, radius + 1)]


def full_sum(sigma):
    """The weight of the whole Gaussian, sampled out to a very large radius (the tails included)."""
    return sum(gaussian_weights(sigma, int(math.ceil(sigma * 10))))


def coverage(sigma, radius):
    """Fraction of the Gaussian's total weight captured within the radius."""
    return sum(gaussian_weights(sigma, radius)) / full_sum(sigma)


def effective_variance(sigma, radius):
    """The variance of the renormalized truncated kernel -- its true blur width squared."""
    w = gaussian_weights(sigma, radius)
    s = sum(w)
    xs = range(-radius, radius + 1)
    return sum(wi * (x * x) for x, wi in zip(xs, w)) / s


# ----------------------------------------------------------------- printing

def coverage_view(data):
    sigma = data["sigma"]
    print("COVERAGE — sigma %.1f Gaussian truncated at each radius" % sigma)
    print("-" * 60)
    print("  radius   in sigmas   captured weight   unnormalized brightness")
    for r in data["radii"]:
        c = coverage(sigma, r)
        print("  %-6d   %-9.1f   %-15.4f   %.1f%%" % (r, r / sigma, c, 100 * c))
    print("-" * 60)
    print("  a small radius captures less weight; applied unnormalized it darkens the image")


def width_view(data):
    sigma = data["sigma"]
    print("WIDTH — effective std dev of the renormalized truncated kernel (requested sigma %.1f)" % sigma)
    print("-" * 60)
    print("  radius   in sigmas   effective sigma")
    for r in data["radii"]:
        eff = math.sqrt(effective_variance(sigma, r))
        print("  %-6d   %-9.1f   %.4f" % (r, r / sigma, eff))
    print("-" * 60)
    print("  renormalizing fixes brightness, but a small radius is still a narrower blur than requested")


def check(data):
    print("SELF-TEST — a small radius loses weight and darkens the image; renormalizing restores brightness but leaves the blur too narrow; three sigma captures nearly all")
    print("-" * 112)
    sigma = data["sigma"]
    r_small = int(round(sigma))       # radius = 1 sigma
    r_three = int(round(3 * sigma))   # radius = 3 sigma

    cov_small = coverage(sigma, r_small)
    cov_three = coverage(sigma, r_three)

    small_radius_loses_weight = cov_small < 0.99
    print("  a radius of 1 sigma captures under 99%% of the weight = %s (%.4f)" % (small_radius_loses_weight, cov_small))

    unnormalized_darkens = cov_small < 0.95
    print("  applied unnormalized, that kernel darkens the image = %s (flat 1.0 -> %.4f)" % (unnormalized_darkens, cov_small))

    three_sigma_captures_nearly_all = cov_three >= 0.997
    print("  a radius of 3 sigma captures nearly all the weight = %s (%.4f)" % (three_sigma_captures_nearly_all, cov_three))

    renorm_sum = 1.0  # a renormalized kernel sums to 1 by construction
    renormalize_restores_brightness = abs(renorm_sum - 1.0) < 1e-9
    print("  renormalizing the truncated kernel restores brightness = %s (sum = %.1f)" % (renormalize_restores_brightness, renorm_sum))

    eff_var_small = effective_variance(sigma, r_small)
    renormalize_still_too_narrow = eff_var_small < sigma * sigma
    print("  but the renormalized small-radius blur is still too narrow = %s (effective var %.4f < %.4f)"
          % (renormalize_still_too_narrow, eff_var_small, sigma * sigma))

    ok = (small_radius_loses_weight and unnormalized_darkens and three_sigma_captures_nearly_all
          and renormalize_restores_brightness and renormalize_still_too_narrow)
    print("-" * 112)
    print("SELF-TEST %s  small_radius_loses_weight=%s  unnormalized_darkens=%s  three_sigma_captures_nearly_all=%s  renormalize_restores_brightness=%s  renormalize_still_too_narrow=%s"
          % ("PASS" if ok else "FAIL", small_radius_loses_weight, unnormalized_darkens, three_sigma_captures_nearly_all,
             renormalize_restores_brightness, renormalize_still_too_narrow))
    return ok


def main():
    p = argparse.ArgumentParser(description="Gaussian kernel truncation: size the kernel radius to about three sigma and renormalize, because a Gaussian has infinite tails so any finite kernel is truncated -- a radius too small drops a real fraction of the weight, darkening the whole image if unnormalized and staying a narrower blur than requested even if renormalized.")
    p.add_argument("--coverage", action="store_true")
    p.add_argument("--width", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("sigma=%.1f  radii=%s  file=%s  (these are a fixture)" % (data["sigma"], data["radii"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.coverage:
        coverage_view(data)
    elif args.width:
        width_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
