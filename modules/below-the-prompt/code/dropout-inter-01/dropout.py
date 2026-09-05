"""Rescale after dropping units, or training's expected activation won't match test's and every value shifts.

Dropout regularizes a network by randomly zeroing a fraction of units on each training step, so no unit can
rely on any other and the network learns redundant, robust features. The catch is arithmetic. During training,
with keep probability p, only about a fraction p of the units are active, so the sum they feed downstream is on
average p times what it would be with all units on. At TEST time there is no dropout -- every unit is active --
so the same layer produces the full sum. Train on p-scale activations and test on full-scale ones and every
downstream value is off by a factor of 1/p: the network was tuned for inputs of one size and handed inputs of
another, and it silently degrades even though nothing looks broken.

The fix is to rescale so the expected activation is the same in both modes. Inverted dropout does it during
training: after zeroing the dropped units, divide the survivors by p, which lifts the expected sum back to the
full value, so test (with all units, unscaled) matches. Equivalently you could scale DOWN at test by p, but
inverted dropout keeps test-time code identical to a no-dropout network, which is why it is the standard. The
principle is that dropout must be expectation-preserving: whatever fraction you drop, you scale so the layer's
expected output is unchanged.

On this fixture four units sum to 10 with a keep probability of 0.5. Enumerating every dropout mask weighted by
its probability, the expected training sum WITHOUT rescaling is 5.0 -- half of the test-time 10.0, a 2x
mismatch. WITH inverted dropout the expected training sum is 10.0, matching test exactly. This computes both.

  --expect     the exact expected training sum (no-scale vs inverted) against the test-time sum
  --masks      a few dropout masks and their contribution, showing the expectation is enumerated not sampled
  --check      no-scale training underactivates vs test; inverted dropout matches the test-time activation

The units and keep probability are the fixture; every expectation is computed exactly. Stdlib only.
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "dropout.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mask_prob(mask, p):
    """Probability of a dropout mask: p for each kept unit, (1-p) for each dropped one."""
    prob = 1.0
    for bit in mask:
        prob *= p if bit else (1 - p)
    return prob


def expected_sum(units, p, invert):
    """Exact expected training sum over all masks; invert=True divides survivors by p (inverted dropout)."""
    scale = (1.0 / p) if invert else 1.0
    total = 0.0
    for mask in itertools.product([0, 1], repeat=len(units)):
        kept = sum(u * scale for u, bit in zip(units, mask) if bit)
        total += mask_prob(mask, p) * kept
    return total


def test_sum(units):
    """Test time: no dropout, every unit active, no scaling."""
    return sum(units)


# ----------------------------------------------------------------- printing

def expect_view(data):
    units, p = data["units"], data["keep_prob"]
    print("EXPECT — expected training sum vs test sum (units %s, keep %.1f)" % (units, p))
    print("-" * 62)
    print("  test time (all units on):      %.1f" % test_sum(units))
    print("  train, no rescale:             %.1f   (x%.1f of test)" % (expected_sum(units, p, False), expected_sum(units, p, False) / test_sum(units)))
    print("  train, inverted dropout (/p):  %.1f   (matches test)" % expected_sum(units, p, True))
    print("-" * 62)
    print("  without rescaling, training runs at %.0f%% of test-time scale." % (100 * expected_sum(units, p, False) / test_sum(units)))


def masks_view(data):
    units, p = data["units"], data["keep_prob"]
    masks = list(itertools.product([0, 1], repeat=len(units)))
    print("MASKS — a few of the %d dropout masks and their weighted contribution (no rescale)" % len(masks))
    print("-" * 62)
    for mask in masks[:5]:
        kept = sum(u for u, bit in zip(units, mask) if bit)
        print("  mask %s  keeps %s  sum %d  prob %.4f  contributes %.4f" % (mask, [units[i] for i in range(len(units)) if mask[i]], kept, mask_prob(mask, p), mask_prob(mask, p) * kept))
    print("  ... (%d masks total, summed exactly)" % len(masks))
    print("-" * 62)
    print("  the expectation is the probability-weighted sum over all masks, not a sample.")


def check(data):
    print("SELF-TEST — no-scale training underactivates vs test; inverted dropout matches the test-time activation")
    print("-" * 104)
    units, p = data["units"], data["keep_prob"]
    test = test_sum(units)
    no_scale = expected_sum(units, p, False)
    inverted = expected_sum(units, p, True)

    no_scale_below_test = no_scale < test
    print("  no-rescale training activation is below test = %s (%.1f < %.1f)" % (no_scale_below_test, no_scale, test))

    mismatch_is_factor_p = abs(no_scale - p * test) < 1e-9
    print("  the no-rescale training sum is exactly p times the test sum = %s (%.1f = %.1f*%.1f)" % (mismatch_is_factor_p, no_scale, p, test))

    inverted_matches_test = abs(inverted - test) < 1e-9
    print("  inverted dropout matches the test-time sum = %s (%.1f = %.1f)" % (inverted_matches_test, inverted, test))

    inverted_scales_by_1_over_p = abs(inverted - no_scale / p) < 1e-9
    print("  inverted dropout is the no-scale sum divided by p = %s (%.1f = %.1f/%.1f)" % (inverted_scales_by_1_over_p, inverted, no_scale, p))

    computed_exactly = abs(sum(mask_prob(m, p) for m in itertools.product([0, 1], repeat=len(units))) - 1.0) < 1e-9
    print("  the mask probabilities sum to 1 (exact enumeration) = %s" % computed_exactly)

    ok = no_scale_below_test and mismatch_is_factor_p and inverted_matches_test and inverted_scales_by_1_over_p and computed_exactly
    print("-" * 104)
    print("SELF-TEST %s  no_scale_below_test=%s  mismatch_is_factor_p=%s  inverted_matches_test=%s  inverted_scales_by_1_over_p=%s  computed_exactly=%s"
          % ("PASS" if ok else "FAIL", no_scale_below_test, mismatch_is_factor_p, inverted_matches_test, inverted_scales_by_1_over_p, computed_exactly))
    return ok


def main():
    p = argparse.ArgumentParser(description="Rescale dropped-out activations so training and test expected activations match.")
    p.add_argument("--expect", action="store_true")
    p.add_argument("--masks", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("units=%d  sum=%d  keep_prob=%.1f  file=%s  (the units are a fixture)"
          % (len(data["units"]), sum(data["units"]), data["keep_prob"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.expect:
        expect_view(data)
    elif args.masks:
        masks_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
