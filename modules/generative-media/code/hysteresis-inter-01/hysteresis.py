"""Threshold edges with hysteresis, or one cutoff either breaks real edges or lets noise through.

A single threshold on edge strength cannot win. Real edges vary in strength along their length -- a contour fades
where the contrast dips, then recovers -- and noise produces scattered pixels of middling strength. Set the
threshold HIGH enough to reject the noise and you also cut the real edge wherever it dipped below the line, so a
continuous contour comes back as broken fragments with gaps. Set it LOW enough to bridge those dips and you also
admit every noise pixel that clears the lower bar. One cutoff has to be both above the noise and below the
weakest part of a real edge, and when those two ranges overlap -- which they usually do -- no single value exists.

Hysteresis thresholding uses two. Pixels at or above the HIGH threshold are STRONG: they are confident edges, kept
unconditionally. Pixels between the LOW and HIGH thresholds are WEAK: kept only if they connect, through a chain
of kept pixels, back to a strong pixel. This is the key move -- a weak pixel is judged not by its own strength but
by its COMPANY. A weak stretch that continues a strong edge is linked in and the edge is made whole; an isolated
weak pixel, noise with no strong neighbor to vouch for it, is dropped. Strength decides the confident pixels;
connectivity decides the doubtful ones, so the same weak value is kept when it extends an edge and rejected when
it stands alone.

On this fixture the strong edge is at index 1 (value 8); indices 2-3 (values 5, 6) are a weak continuation, and
index 5 (value 4) is isolated weak noise. A high-only threshold keeps just index 1 -- the edge is broken. A
low-only threshold keeps 1, 2, 3, and the noise at 5. Hysteresis keeps 1, 2, 3 (the connected edge) and drops 5.
This computes all three.

  --thresh     which pixels each rule keeps: high-only, low-only, and hysteresis
  --trace      how hysteresis grows the edge from the strong pixel through connected weak pixels, stopping at gaps
  --check      high-only breaks the edge; low-only admits noise; hysteresis keeps the connected edge and drops the isolated pixel

The magnitude profile and thresholds are the fixture; every decision is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "hysteresis.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def strong(mag, high):
    return [i for i, m in enumerate(mag) if m >= high]


def weak(mag, low, high):
    return [i for i, m in enumerate(mag) if low <= m < high]


def single(mag, threshold):
    """Pixels kept by a single threshold."""
    return [i for i, m in enumerate(mag) if m >= threshold]


def hysteresis(mag, low, high):
    """Keep strong pixels, plus weak pixels reachable from a strong one through a chain of >=low pixels."""
    eligible = set(single(mag, low))          # strong or weak
    kept, frontier = set(strong(mag, high)), list(strong(mag, high))
    while frontier:
        i = frontier.pop()
        for j in (i - 1, i + 1):
            if 0 <= j < len(mag) and j in eligible and j not in kept:
                kept.add(j)
                frontier.append(j)
    return sorted(kept)


# ----------------------------------------------------------------- printing

def thresh_view(data):
    mag, high, low = data["magnitudes"], data["high"], data["low"]
    print("THRESH — pixels kept by each rule (high %d, low %d)" % (high, low))
    print("-" * 60)
    print("  magnitudes:   %s" % mag)
    print("  high-only:    %s   (real edge broken)" % single(mag, high))
    print("  low-only:     %s   (noise admitted)" % single(mag, low))
    print("  hysteresis:   %s   (connected edge, noise dropped)" % hysteresis(mag, low, high))
    print("-" * 60)
    print("  hysteresis sits between: every high pixel, only the low pixels connected to one.")


def trace_view(data):
    mag, high, low = data["magnitudes"], data["high"], data["low"]
    print("TRACE — hysteresis grows from the strong pixel through connected weak ones")
    print("-" * 60)
    print("  strong (>= %d): %s   kept unconditionally" % (high, strong(mag, high)))
    print("  weak   (%d..%d): %s   kept only if connected" % (low, high, weak(mag, low, high)))
    kept = hysteresis(mag, low, high)
    for i in weak(mag, low, high):
        linked = i in kept
        print("    weak pixel %d (value %d): %s" % (i, mag[i], "linked to a strong edge -> KEEP" if linked else "isolated (noise) -> drop"))
    print("-" * 60)
    print("  the same weak value is kept when it extends an edge and dropped when it stands alone.")


def check(data):
    print("SELF-TEST — high-only breaks the edge; low-only admits noise; hysteresis keeps the connected edge, drops the isolated pixel")
    print("-" * 116)
    mag, high, low = data["magnitudes"], data["high"], data["low"]
    hi, lo, hy = single(mag, high), single(mag, low), hysteresis(mag, low, high)
    noise = 5  # the isolated weak pixel in the fixture

    high_only_breaks = len(hi) < len(hy)
    print("  high-only keeps fewer pixels than hysteresis (edge broken) = %s (%s vs %s)" % (high_only_breaks, hi, hy))

    low_only_admits_noise = noise in lo
    print("  low-only admits the isolated noise pixel = %s (index %d in %s)" % (low_only_admits_noise, noise, lo))

    hysteresis_keeps_connected = all(i in hy for i in (1, 2, 3))
    print("  hysteresis keeps the connected edge 1,2,3 = %s (%s)" % (hysteresis_keeps_connected, hy))

    hysteresis_rejects_isolated = noise not in hy
    print("  hysteresis drops the isolated noise pixel = %s (index %d not in %s)" % (hysteresis_rejects_isolated, noise, hy))

    hysteresis_between = set(hi) <= set(hy) <= set(lo)
    print("  hysteresis is between high-only and low-only = %s" % hysteresis_between)

    ok = high_only_breaks and low_only_admits_noise and hysteresis_keeps_connected and hysteresis_rejects_isolated and hysteresis_between
    print("-" * 116)
    print("SELF-TEST %s  high_only_breaks=%s  low_only_admits_noise=%s  hysteresis_keeps_connected=%s  hysteresis_rejects_isolated=%s  hysteresis_between=%s"
          % ("PASS" if ok else "FAIL", high_only_breaks, low_only_admits_noise, hysteresis_keeps_connected, hysteresis_rejects_isolated, hysteresis_between))
    return ok


def main():
    p = argparse.ArgumentParser(description="Hysteresis (double) thresholding keeps strong edges and only the weak edges connected to them, unlike a single cutoff.")
    p.add_argument("--thresh", action="store_true")
    p.add_argument("--trace", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("magnitudes=%s  high=%d  low=%d  file=%s  (the profile is a fixture)"
          % (data["magnitudes"], data["high"], data["low"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.thresh:
        thresh_view(data)
    elif args.trace:
        trace_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
