"""Match one image's tone to another through their CDFs -- a brightness shift moves the mean but cannot reshape the distribution.

Sometimes you do not want to make an image's histogram uniform (that is histogram EQUALIZATION); you want to make it look
like a SPECIFIC other image -- transfer the tonal character of a reference photo onto a source, so a batch of images
matches one look, or a dull frame takes on a graded reference's mood. That is histogram MATCHING (or specification), and the
naive way to do it -- shift the source's brightness until its average matches the reference's -- does not work, because a
shift (or a linear scale) can only move and stretch the distribution, not RESHAPE it. If the source is skewed dark and the
reference is skewed bright, shifting the source brighter moves its mean up but leaves it just as skewed; the shape is still
the source's, not the reference's. Matching the mean is not matching the look.

Histogram matching reshapes the distribution by working through the CUMULATIVE distribution functions. The CDF at a level is
the fraction of pixels at or below that level, and it captures the tonal shape: a dark image's CDF rises fast (most pixels
are low), a bright image's rises slowly. To make the source's tone match the reference's, you map each source level to the
reference level that occupies the same position in the reference's CDF -- for a source level whose cumulative probability is
p, find the reference level whose cumulative probability first reaches p, and send the source's pixels there. Because the
mapping is driven by matching cumulative probabilities, the remapped source pixels land so that the OUTPUT distribution
approximates the reference's shape, not just its mean. The mapping is monotonic (brighter stays brighter), so it never
inverts tones; it only redistributes them to follow the reference.

The catch, which the mechanism makes visible, is that matching is only exact in the continuous limit; with a finite set of
discrete levels the CDFs cannot line up perfectly, so the output histogram approximates the reference rather than equalling
it -- the fewer levels, the coarser the match. But even approximately, CDF matching moves the source's whole distribution
toward the reference, which a brightness shift can never do.

The rule: match one image's tone to a reference by mapping each source intensity through the two images' CDFs -- send a
source level to the reference level with the same cumulative probability -- because this reshapes the source's distribution
to approximate the reference's, whereas a brightness shift or linear scale only moves the mean and leaves the source's shape
unchanged.

On this fixture the source is dark (mean 1.0) and the reference bright (mean 2.0). CDF matching maps source levels 0,1,2,3
to 2,3,3,3, pushing the dark pixels bright, so the output distribution is measurably closer to the reference's than the
source was. This computes both.

  --cdf      the source and reference histograms and their CDFs -- the tonal shapes matching works from
  --match    the CDF-driven level mapping, the output histogram, and how much closer its CDF is to the reference's
  --check    matching remaps dark levels to bright ones (monotonically) and moves the output distribution toward the reference

source_hist and reference_hist are the fixture; every CDF, mapping, and output distribution is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "histmatch.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cdf(hist):
    """Cumulative distribution: the running fraction of pixels at or below each level."""
    total = sum(hist)
    running = 0
    out = []
    for h in hist:
        running += h
        out.append(running / total)
    return out


def match_mapping(source_cdf, ref_cdf):
    """Map each source level to the reference level whose CDF first reaches the source level's CDF."""
    mapping = []
    for p in source_cdf:
        j = next(k for k, c in enumerate(ref_cdf) if c >= p)
        mapping.append(j)
    return mapping


def apply_mapping(source_hist, mapping, levels):
    """Redistribute the source pixels to their mapped levels, producing the output histogram."""
    out = [0] * levels
    for level, count in enumerate(source_hist):
        out[mapping[level]] += count
    return out


def mean_level(hist):
    total = sum(hist)
    return sum(level * count for level, count in enumerate(hist)) / total


def cdf_l1(a, b):
    """L1 distance between two CDFs -- how different the two tonal shapes are."""
    return sum(abs(x - y) for x, y in zip(a, b))


# ----------------------------------------------------------------- printing

def cdf_view(data):
    s, r = data["source_hist"], data["reference_hist"]
    print("CDF — the source (dark) and reference (bright) histograms and CDFs")
    print("-" * 62)
    print("  level          0     1     2     3")
    print("  source hist    %s" % "  ".join("%-4d" % h for h in s))
    print("  source CDF     %s" % "  ".join("%-4.1f" % c for c in cdf(s)))
    print("  reference hist %s" % "  ".join("%-4d" % h for h in r))
    print("  reference CDF  %s" % "  ".join("%-4.1f" % c for c in cdf(r)))
    print("-" * 62)
    print("  source mean = %.1f (dark) ; reference mean = %.1f (bright)" % (mean_level(s), mean_level(r)))


def match_view(data):
    s, r = data["source_hist"], data["reference_hist"]
    sc, rc = cdf(s), cdf(r)
    mapping = match_mapping(sc, rc)
    out = apply_mapping(s, mapping, len(r))
    print("MATCH — CDF-driven level mapping and the output distribution")
    print("-" * 60)
    for level in range(len(s)):
        print("  source level %d (CDF %.1f) -> reference level %d (CDF %.1f)"
              % (level, sc[level], mapping[level], rc[mapping[level]]))
    print("-" * 60)
    print("  output histogram = %s   output CDF = %s" % (out, ["%.1f" % c for c in cdf(out)]))
    print("  CDF distance to reference: source %.1f -> output %.1f (closer is better)"
          % (cdf_l1(sc, rc), cdf_l1(cdf(out), rc)))


def check(data):
    print("SELF-TEST — matching remaps dark levels to bright ones (monotonically) and moves the output distribution toward the reference")
    print("-" * 126)
    s, r = data["source_hist"], data["reference_hist"]
    sc, rc = cdf(s), cdf(r)
    mapping = match_mapping(sc, rc)
    out = apply_mapping(s, mapping, len(r))

    source_darker = mean_level(s) < mean_level(r)
    print("  the source is darker than the reference = %s (mean %.1f < %.1f)" % (source_darker, mean_level(s), mean_level(r)))

    mapping_monotonic = all(mapping[i] <= mapping[i + 1] for i in range(len(mapping) - 1))
    print("  the mapping is monotonic (brighter stays brighter) = %s (%s)" % (mapping_monotonic, mapping))

    maps_dark_to_bright = mapping[0] > 0
    print("  the darkest source level is remapped brighter = %s (level 0 -> %d)" % (maps_dark_to_bright, mapping[0]))

    output_closer = cdf_l1(cdf(out), rc) < cdf_l1(sc, rc)
    print("  the output CDF is closer to the reference than the source was = %s (%.1f < %.1f)"
          % (output_closer, cdf_l1(cdf(out), rc), cdf_l1(sc, rc)))

    pixels_conserved = sum(out) == sum(s)
    print("  no pixels are created or lost by the remap = %s (%d == %d)" % (pixels_conserved, sum(out), sum(s)))

    ok = source_darker and mapping_monotonic and maps_dark_to_bright and output_closer and pixels_conserved
    print("-" * 126)
    print("SELF-TEST %s  source_darker=%s  mapping_monotonic=%s  maps_dark_to_bright=%s  output_closer=%s  pixels_conserved=%s"
          % ("PASS" if ok else "FAIL", source_darker, mapping_monotonic, maps_dark_to_bright, output_closer, pixels_conserved))
    return ok


def main():
    p = argparse.ArgumentParser(description="Histogram matching: match one image's tone to a reference by mapping each source intensity through the two images' CDFs (send a source level to the reference level with the same cumulative probability), because this reshapes the source's distribution to approximate the reference's, whereas a brightness shift or linear scale only moves the mean and leaves the source's shape unchanged.")
    p.add_argument("--cdf", action="store_true")
    p.add_argument("--match", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("source_hist=%s  reference_hist=%s  file=%s  (the two histograms are a fixture)"
          % (data["source_hist"], data["reference_hist"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.cdf:
        cdf_view(data)
    elif args.match:
        match_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
