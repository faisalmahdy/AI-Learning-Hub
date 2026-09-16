"""Add a residual connection or the gradient vanishes through depth -- the +1 identity is the highway.

Backpropagation sends the gradient from the loss back through every layer to the input, and at each
layer it is multiplied by that layer's local derivative. In a plain deep stack those derivatives
multiply together, so the gradient reaching the early layers is the PRODUCT of all of them. If each
layer's factor is a little below 1 -- which is typical -- the product shrinks exponentially with depth
and the early layers receive essentially no gradient. They stop learning. This is the vanishing
gradient, and it is why naively stacking layers stopped working past a certain depth.

A residual connection fixes it with one addition. Instead of y = f(x) the layer computes y = x + f(x),
so its local derivative is 1 + f'(x): the branch contributes f' and the identity contributes a fixed
1. That +1 is an uninterruptible highway -- the gradient flows straight through it undiminished, no
matter how small the branch derivative is, so the product of per-layer factors stays near or above 1
instead of decaying to zero. It is the single trick that made very deep networks, including every
transformer, trainable.

On this fixture a 20-layer plain stack with per-layer factor 0.7 delivers a gradient of 0.0008 to the
input -- vanished. The same depth with a residual (branch factor 0.1) delivers 6.73 -- alive. And
removing just the +1 identity, leaving only the 0.1 branch, collapses it to 1e-20, proving the
identity, not the branch, is what saved it. This computes the gradient reaching the input each way.

  --stack      the per-layer factors for the plain vs residual stack at this depth
  --gradient   the gradient reaching the input under plain, residual, and residual-minus-identity
  --check      the plain gradient vanishes; the residual survives; the +1 identity is the cause

The per-layer factors and depth are the fixture; every gradient is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "depth.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- gradient through depth

def gradient_through(per_layer_jacobian, n_layers):
    """The gradient reaching the input: the product of the per-layer derivative over the whole stack."""
    g = 1.0
    for _ in range(n_layers):
        g *= per_layer_jacobian
    return g


def plain_gradient(data):
    """Plain stack: each layer multiplies the gradient by its own factor, below 1."""
    return gradient_through(data["plain_jacobian"], data["n_layers"])


def residual_gradient(data):
    """Residual stack: each layer's factor is 1 + branch -- the +1 identity carries the gradient."""
    return gradient_through(1 + data["branch_jacobian"], data["n_layers"])


def residual_without_identity(data):
    """Counterfactual: the residual branch alone, without the +1 -- shows what the identity was doing."""
    return gradient_through(data["branch_jacobian"], data["n_layers"])


# ----------------------------------------------------------------- printing

def stack_view(data):
    n = data["n_layers"]
    print("STACK — per-layer gradient factor, plain vs residual (%d layers)" % n)
    print("-" * 54)
    print("  plain layer:     y = f(x)      local derivative = %.2f" % data["plain_jacobian"])
    print("  residual layer:  y = x + f(x)  local derivative = 1 + %.2f = %.2f"
          % (data["branch_jacobian"], 1 + data["branch_jacobian"]))
    print("-" * 54)
    print("  a factor below 1 shrinks the gradient each layer; the +1 keeps it from shrinking.")


def gradient_view(data):
    n, thr = data["n_layers"], data["vanish_threshold"]
    p, r, ri = plain_gradient(data), residual_gradient(data), residual_without_identity(data)
    print("GRADIENT — magnitude reaching the input through %d layers (vanished if < %g)" % (n, thr))
    print("-" * 66)
    print("  plain (0.7 each):              %.6g   %s" % (p, "VANISHED" if p < thr else "alive"))
    print("  residual (1.1 each):           %.4g       %s" % (r, "VANISHED" if r < thr else "alive"))
    print("  residual minus the +1 (0.1):   %.3g   %s" % (ri, "VANISHED" if ri < thr else "alive"))
    print("-" * 66)
    print("  depth by depth:")
    for d in [1, 5, 10, 20]:
        print("    %2d layers:  plain %.5g   residual %.3g"
              % (d, gradient_through(data["plain_jacobian"], d), gradient_through(1 + data["branch_jacobian"], d)))
    print("-" * 66)
    print("  plain vanishes with depth; residual holds; strip the +1 and the residual vanishes too.")


def check(data):
    print("SELF-TEST — the plain gradient vanishes; the residual survives; the +1 identity is the cause")
    print("-" * 88)
    thr = data["vanish_threshold"]
    p, r, ri = plain_gradient(data), residual_gradient(data), residual_without_identity(data)

    plain_vanishes = p < thr
    print("  the plain deep stack's gradient vanishes = %s (%.6g < %g)" % (plain_vanishes, p, thr))

    residual_survives = r >= thr
    print("  the residual stack's gradient survives = %s (%.4g >= %g)" % (residual_survives, r, thr))

    identity_is_the_cause = ri < thr
    print("  removing the +1 identity makes it vanish too = %s (%.3g < %g)" % (identity_is_the_cause, ri, thr))

    residual_beats_plain = r > p
    print("  the residual gradient is far larger than the plain one = %s (%.4g vs %.6g)" % (residual_beats_plain, r, p))

    ok = plain_vanishes and residual_survives and identity_is_the_cause and residual_beats_plain
    print("-" * 88)
    print("SELF-TEST %s  plain_vanishes=%s  residual_survives=%s  identity_is_the_cause=%s  residual_beats_plain=%s"
          % ("PASS" if ok else "FAIL", plain_vanishes, residual_survives, identity_is_the_cause, residual_beats_plain))
    return ok


def main():
    p = argparse.ArgumentParser(description="Add a residual connection or the gradient vanishes through depth.")
    p.add_argument("--stack", action="store_true")
    p.add_argument("--gradient", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n_layers=%d  plain_jac=%.2f  branch_jac=%.2f  file=%s  (the factors and depth are a fixture)"
          % (data["n_layers"], data["plain_jacobian"], data["branch_jacobian"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.stack:
        stack_view(data)
    elif args.gradient:
        gradient_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
