"""Flip the kernel before you slide it, or your convolution is a correlation and mirrors every asymmetric kernel.

The operation almost everyone calls "convolution" in a neural net is arithmetically a CORRELATION: line the
kernel up on the signal and take the weighted sum, kernel written left-to-right. Mathematical convolution is
the same slide with one extra step -- the kernel is FLIPPED (reversed) first. For a symmetric kernel the flip
changes nothing, so the two agree and no one notices. For an ASYMMETRIC kernel they disagree, and they disagree
in the most confusing possible way: the result comes out mirrored. A kernel you designed to respond to a left
neighbor responds to the right one; a feature you meant to shift one way shifts the other.

Here is the crisp version. Take an impulse -- a single 1 sitting at index 2 -- and a kernel [1, 0, 0], meaning
"weight the LEFT neighbor (offset -1)". Correlation computes out[i] = signal[i-1], so the impulse lands at
index 3: it moves RIGHT. True convolution flips the kernel to [0, 0, 1] first, computes out[i] = signal[i+1],
and the impulse lands at index 1: it moves LEFT. Same signal, same kernel, opposite directions -- and only one
of them is what "convolution" means mathematically. The flip is not decoration; it is the definition.

On this fixture correlation moves the impulse to index 3 and convolution to index 1, a two-cell disagreement.
The symmetric blur [1, 2, 1] gives byte-identical output either way, because its reverse is itself. This
computes both, and confirms convolution equals correlation-with-the-kernel-reversed.

  --compare    correlation vs convolution for the asymmetric and the symmetric kernel, side by side
  --shift      where the impulse lands under each operation, showing the mirrored direction
  --check      the asymmetric kernel differs (mirrored), the symmetric one is identical, conv == flipped corr

The signal and kernels are the fixture; every output is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "signal.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def at(signal, i):
    """Signal sample with zero padding outside the array."""
    return signal[i] if 0 <= i < len(signal) else 0


def correlate(signal, kernel):
    """Slide the kernel as written: out[i] = sum_d signal[i+d]*kernel[d], center offset d in {-1,0,+1}."""
    r = len(kernel) // 2
    return [sum(at(signal, i + d) * kernel[d + r] for d in range(-r, r + 1)) for i in range(len(signal))]


def convolve(signal, kernel):
    """True convolution: flip the kernel first, then correlate."""
    return correlate(signal, list(reversed(kernel)))


def peak(seq):
    """Index of the (first) maximum — where the impulse ended up."""
    return seq.index(max(seq))


# ----------------------------------------------------------------- printing

def compare_view(data):
    sig = data["signal"]
    print("COMPARE — correlation vs convolution (signal %s)" % sig)
    print("-" * 62)
    for name, k in data["kernels"].items():
        corr = correlate(sig, k)
        conv = convolve(sig, k)
        same = "identical" if corr == conv else "MIRRORED — differ"
        print("  kernel %-4s %s   flipped %s" % (name, k, list(reversed(k))))
        print("    correlation:  %s" % corr)
        print("    convolution:  %s   (%s)" % (conv, same))
    print("-" * 62)
    print("  the asymmetric kernel disagrees; the symmetric kernel is a no-op under the flip.")


def shift_view(data):
    sig = data["signal"]
    k = data["kernels"]["asym"]
    corr = correlate(sig, k)
    conv = convolve(sig, k)
    src = peak(sig)
    print("SHIFT — impulse at index %d, kernel %s (weights the LEFT neighbor)" % (src, k))
    print("-" * 62)
    print("  correlation lands the impulse at index %d  -> moved RIGHT (+%d)" % (peak(corr), peak(corr) - src))
    print("  convolution lands the impulse at index %d  -> moved LEFT  (%d)" % (peak(conv), peak(conv) - src))
    print("-" * 62)
    print("  same kernel, opposite directions: the flip reverses which neighbor is weighted.")


def check(data):
    print("SELF-TEST — asymmetric kernel comes out mirrored; symmetric is identical; conv == flipped corr")
    print("-" * 100)
    sig = data["signal"]
    asym, sym = data["kernels"]["asym"], data["kernels"]["sym"]

    asymmetric_differs = correlate(sig, asym) != convolve(sig, asym)
    print("  the asymmetric kernel differs under the flip = %s (%s vs %s)" % (asymmetric_differs, correlate(sig, asym), convolve(sig, asym)))

    symmetric_identical = correlate(sig, sym) == convolve(sig, sym)
    print("  the symmetric kernel is identical either way = %s (%s)" % (symmetric_identical, convolve(sig, sym)))

    conv_is_flipped_corr = convolve(sig, asym) == correlate(sig, list(reversed(asym)))
    print("  convolution == correlation with the reversed kernel = %s" % conv_is_flipped_corr)

    src = peak(sig)
    corr_right = peak(correlate(sig, asym)) - src
    conv_left = peak(convolve(sig, asym)) - src
    opposite_directions = corr_right == -conv_left and corr_right != 0
    print("  correlation and convolution shift the impulse opposite ways = %s (%+d vs %+d)" % (opposite_directions, corr_right, conv_left))

    flip_is_involution = list(reversed(list(reversed(asym)))) == asym
    print("  flipping the kernel twice returns the original = %s" % flip_is_involution)

    ok = asymmetric_differs and symmetric_identical and conv_is_flipped_corr and opposite_directions and flip_is_involution
    print("-" * 100)
    print("SELF-TEST %s  asymmetric_differs=%s  symmetric_identical=%s  conv_is_flipped_corr=%s  opposite_directions=%s  flip_is_involution=%s"
          % ("PASS" if ok else "FAIL", asymmetric_differs, symmetric_identical, conv_is_flipped_corr, opposite_directions, flip_is_involution))
    return ok


def main():
    p = argparse.ArgumentParser(description="Convolution flips the kernel before sliding; correlation does not, so asymmetric kernels come out mirrored.")
    p.add_argument("--compare", action="store_true")
    p.add_argument("--shift", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("signal=%s  kernels=%s  file=%s  (the signal and kernels are a fixture)"
          % (data["signal"], list(data["kernels"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.compare:
        compare_view(data)
    elif args.shift:
        shift_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
