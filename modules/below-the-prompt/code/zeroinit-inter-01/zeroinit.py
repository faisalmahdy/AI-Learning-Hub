"""Zero-initialize the last layer of each residual branch so every block starts as the identity (x + 0 = x) -- a standard nonzero-initialized branch perturbs the signal at every block, and the perturbation compounds exponentially with depth.

A residual block computes x + f(x): the input passes through on the skip connection, and the residual branch f adds a correction. What f(x) is at the very start of training depends entirely on how f's last layer is initialized. With standard random init, f(x) is a nonzero perturbation of x, so the block does not preserve its input -- it scales it by roughly (1 + branch_gain).

One block's small perturbation is harmless. Stacked depth is not. N blocks multiply the signal by (1 + branch_gain) N times, so the magnitude grows as (1 + branch_gain) to the power N -- the same exponential-in-depth compounding that makes plain initialization scale dangerous, now happening along the residual path. A gain that looks negligible at one block reaches the signal through fifty blocks as a large multiplier, and the network's activations have already drifted or blown up before the first gradient step.

Zero-initializing the final layer of each residual branch removes the perturbation at its source. If that layer is zero, f(x) is exactly zero at initialization, so every block computes x + 0 = x -- the identity -- and the whole network, however deep, is the identity function at step zero. The signal passes through untouched, gradients are clean, and training begins from a stable point instead of from a signal that depth has already corrupted.

This is why residual networks are often initialized this way: the skip connection alone should carry the signal at the start, and each branch should begin contributing nothing, then learn to add its correction from zero. Depth becomes free at initialization -- adding blocks cannot change the output when every branch outputs zero -- which is much of what lets residual networks be trained at hundreds of layers.

The rule: zero-initialize the last layer of each residual branch so the branch outputs zero and the block starts as the identity x + 0 = x, because a nonzero-initialized branch perturbs the signal at every block and the perturbation compounds as (1 + gain) to the depth -- while a zero-initialized branch keeps the output equal to the input at any depth.

On this fixture a signal of 1.0 passes through residual blocks whose branch gain is 0.1. Under standard init the magnitude grows to about 2.6 at depth 10 and 117 at depth 50; under zero-init it stays exactly 1.0 at any depth. This computes both.

  --propagate   the signal magnitude through the stack under standard init vs zero-init, at two depths
  --depth       how the two initializations scale as depth grows
  --check       standard init compounds the signal with depth; zero-init leaves it the identity at any depth

x0, branch_gain, and the depths are the fixture; the output magnitudes under each init are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "zeroinit.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def propagate(x0, branch_gain, depth):
    """Signal after `depth` residual blocks x -> x + gain*x = x*(1+gain)."""
    x = x0
    for _ in range(depth):
        x = x + branch_gain * x
    return x


def standard(x0, branch_gain, depth):
    """Standard init: the residual branch has a nonzero gain."""
    return propagate(x0, branch_gain, depth)


def zero_init(x0, depth):
    """Zero-init: the branch's last layer is zero, so its gain is 0 -- each block is the identity."""
    return propagate(x0, 0.0, depth)


# ----------------------------------------------------------------- printing

def propagate_view(data):
    x0, g, d, dd = data["x0"], data["branch_gain"], data["depth"], data["deep_depth"]
    print("PROPAGATE — signal of %.1f through residual blocks (branch gain %.1f)" % (x0, g))
    print("-" * 56)
    print("  depth   standard init      zero-init")
    for depth in (d, dd):
        print("  %-5d   %-16.4f   %.4f" % (depth, standard(x0, g, depth), zero_init(x0, depth)))
    print("-" * 56)
    print("  standard init drifts and then explodes with depth; zero-init holds at %.1f" % x0)


def depth_view(data):
    x0, g = data["x0"], data["branch_gain"]
    print("DEPTH — standard-init output as the stack grows (zero-init stays %.1f)" % x0)
    print("-" * 50)
    print("  depth   standard init")
    for depth in (0, 5, 10, 25, 50):
        print("  %-5d   %.4f" % (depth, standard(x0, g, depth)))
    print("-" * 50)
    print("  the growth is (1+gain)^depth -- exponential in depth")


def check(data):
    print("SELF-TEST — standard init compounds the signal with depth; zero-init leaves it the identity at any depth")
    print("-" * 112)
    x0, g, d, dd = data["x0"], data["branch_gain"], data["depth"], data["deep_depth"]

    s_shallow = standard(x0, g, d)
    s_deep = standard(x0, g, dd)
    z_shallow = zero_init(x0, d)
    z_deep = zero_init(x0, dd)

    standard_drifts = abs(s_shallow - x0) > 1e-9
    print("  standard init: the signal drifts from the input = %s (%.4f vs %.1f)" % (standard_drifts, s_shallow, x0))

    standard_compounds = s_deep > s_shallow
    print("  standard init: deeper compounds the drift = %s (%.2f at %d > %.2f at %d)" % (standard_compounds, s_deep, dd, s_shallow, d))

    standard_matches_formula = abs(s_deep - x0 * (1 + g) ** dd) < 1e-6
    print("  standard init: output equals (1+gain)^depth = %s" % standard_matches_formula)

    zeroinit_is_identity = abs(z_shallow - x0) < 1e-12
    print("  zero-init: the signal equals the input (identity) = %s (%.4f)" % (zeroinit_is_identity, z_shallow))

    zeroinit_depth_invariant = abs(z_deep - z_shallow) < 1e-12
    print("  zero-init: the output is the same at any depth = %s (%.4f == %.4f)" % (zeroinit_depth_invariant, z_deep, z_shallow))

    ok = (standard_drifts and standard_compounds and standard_matches_formula
          and zeroinit_is_identity and zeroinit_depth_invariant)
    print("-" * 112)
    print("SELF-TEST %s  standard_drifts=%s  standard_compounds=%s  standard_matches_formula=%s  zeroinit_is_identity=%s  zeroinit_depth_invariant=%s"
          % ("PASS" if ok else "FAIL", standard_drifts, standard_compounds,
             standard_matches_formula, zeroinit_is_identity, zeroinit_depth_invariant))
    return ok


def main():
    p = argparse.ArgumentParser(description="Zero-init residual branches: zero-initialize the last layer of each residual branch so the branch outputs zero and the block starts as the identity x + 0 = x, because a nonzero-initialized branch perturbs the signal at every block and the perturbation compounds as (1 + gain) to the depth -- while a zero-initialized branch keeps the output equal to the input at any depth.")
    p.add_argument("--propagate", action="store_true")
    p.add_argument("--depth", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("x0=%.1f  branch_gain=%.1f  depth=%d  deep_depth=%d  file=%s  (these are a fixture)"
          % (data["x0"], data["branch_gain"], data["depth"], data["deep_depth"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.propagate:
        propagate_view(data)
    elif args.depth:
        depth_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
