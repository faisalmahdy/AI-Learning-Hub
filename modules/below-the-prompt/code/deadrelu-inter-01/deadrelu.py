"""Use a smooth activation -- ReLU's gradient is exactly zero for negative inputs, so a neuron stuck negative can never recover.

A neural network layer applies a nonlinear activation function to each neuron's pre-activation (the weighted sum coming in),
and the choice of activation has a consequence that only shows up during training. ReLU -- rectified linear unit,
ReLU(x) = max(0, x) -- is the classic choice: cheap, and it fixed the vanishing-gradient problem of the old saturating
activations for positive inputs. But it has a sharp corner at zero and is flat for all negative inputs, and 'flat' means its
gradient there is exactly 0. During backpropagation, a neuron's incoming weights are updated in proportion to the gradient
flowing back through its activation; if the neuron's pre-activation is negative, ReLU's gradient is 0, so NO gradient flows,
so its weights do not change. That is fine for one step. The problem is that if a neuron's pre-activation is negative for
every input in the data -- which can happen after an unlucky update pushes its bias very negative -- it outputs 0 always,
receives 0 gradient always, and its weights never move again. It is a DEAD RELU: permanently stuck, contributing nothing,
and unable to recover because the very mechanism that would revive it (a gradient) is switched off exactly where it is stuck.

A dead neuron is wasted capacity, and in a bad case (too high a learning rate, a bad initialization) a large fraction of a
layer can die, so the network effectively has fewer neurons than it was built with. The fix is an activation that is not
flat for negative inputs: instead of clamping negatives to a hard zero with zero slope, let them pass a small, nonzero
gradient. Leaky ReLU does this with a small linear slope for negatives; GELU and its relatives do it with a smooth curve
(GELU multiplies the input by a soft gate, so it bends gently through zero rather than cornering). Because the gradient of
a smooth activation is nonzero even where the input is negative, a neuron sitting in the negative region still receives a
learning signal and can climb back out -- it is not condemned to zero by a flat spot. This is a large part of why modern
transformers use GELU (or SwiGLU) rather than plain ReLU in their feed-forward layers.

The rule: prefer a smooth (or leaky) activation over plain ReLU where dead units are a risk, because ReLU's gradient is
exactly 0 for negative pre-activations, so a neuron whose input stays negative gets no gradient and its weights never
update -- a permanently dead unit -- while a smooth activation passes a nonzero gradient through the negative region so the
neuron keeps learning and can recover.

On this fixture four neurons have pre-activations -2, -0.5, 0.5, 2. Under ReLU the two negative neurons output 0 with
gradient exactly 0 (dead), so 2 of 4 units get no learning signal. Under GELU every neuron's gradient is nonzero (the
negatives too), so 0 of 4 are dead. This computes both.

  --activate   each neuron's pre-activation, and its ReLU and GELU output and gradient side by side
  --dead       how many units get a zero gradient (dead) under ReLU vs GELU, and which pre-activations they are
  --check      ReLU zeros the gradient for negative inputs (dead units); GELU keeps the gradient nonzero everywhere

pre_activations is the fixture; every output, gradient, and dead-unit count is computed with math.erf. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "deadrelu.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def relu(x):
    return max(0.0, x)


def relu_grad(x):
    """The derivative of ReLU: 1 for x>0, exactly 0 for x<=0."""
    return 1.0 if x > 0 else 0.0


def gelu(x):
    """Exact GELU: x times the standard-normal CDF, gelu(x) = 0.5*x*(1 + erf(x/sqrt(2)))."""
    return 0.5 * x * (1.0 + math.erf(x / math.sqrt(2.0)))


def gelu_grad(x):
    """Derivative of exact GELU: 0.5*(1+erf(x/sqrt(2))) + x/sqrt(2*pi) * exp(-x^2/2)."""
    cdf = 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    pdf = math.exp(-x * x / 2.0) / math.sqrt(2.0 * math.pi)
    return cdf + x * pdf


def is_dead(grad, tol=1e-9):
    return abs(grad) < tol


# ----------------------------------------------------------------- printing

def activate_view(data):
    zs = data["pre_activations"]
    print("ACTIVATE — each neuron's pre-activation through ReLU and GELU")
    print("-" * 74)
    print("  pre-act   ReLU out   ReLU grad   GELU out    GELU grad")
    for z in zs:
        print("  %-8.1f  %-10.3f %-11.1f %-11.4f %.4f" % (z, relu(z), relu_grad(z), gelu(z), gelu_grad(z)))
    print("-" * 74)
    print("  ReLU grad is 0 wherever the pre-activation is negative; GELU grad never is.")


def dead_view(data):
    zs = data["pre_activations"]
    relu_dead = [z for z in zs if is_dead(relu_grad(z))]
    gelu_dead = [z for z in zs if is_dead(gelu_grad(z))]
    print("DEAD — units with zero gradient (no learning signal)")
    print("-" * 58)
    print("  ReLU: %d of %d dead  (pre-activations %s)" % (len(relu_dead), len(zs), relu_dead))
    print("  GELU: %d of %d dead  (pre-activations %s)" % (len(gelu_dead), len(zs), gelu_dead or "none"))
    print("-" * 58)
    print("  a dead unit's weights never update -- it is stuck contributing nothing.")


def check(data):
    print("SELF-TEST — ReLU zeros the gradient for negative inputs (dead units); GELU keeps the gradient nonzero everywhere")
    print("-" * 114)
    zs = data["pre_activations"]
    negs = [z for z in zs if z < 0]

    relu_zeros_negatives = all(relu(z) == 0.0 for z in negs)
    print("  ReLU outputs 0 for every negative pre-activation = %s (%s)" % (relu_zeros_negatives, [relu(z) for z in negs]))

    relu_grad_zero_on_negatives = all(relu_grad(z) == 0.0 for z in negs)
    print("  ReLU gradient is exactly 0 on the negatives = %s (%s)" % (relu_grad_zero_on_negatives, [relu_grad(z) for z in negs]))

    relu_dead_count = sum(1 for z in zs if is_dead(relu_grad(z)))
    relu_has_dead = relu_dead_count == len(negs) and relu_dead_count > 0
    print("  ReLU has one dead unit per negative pre-activation = %s (%d dead)" % (relu_has_dead, relu_dead_count))

    gelu_grad_nonzero = all(not is_dead(gelu_grad(z)) for z in zs)
    print("  GELU gradient is nonzero for every neuron, negatives included = %s" % gelu_grad_nonzero)

    gelu_no_dead = sum(1 for z in zs if is_dead(gelu_grad(z))) == 0
    print("  GELU has zero dead units = %s" % gelu_no_dead)

    ok = relu_zeros_negatives and relu_grad_zero_on_negatives and relu_has_dead and gelu_grad_nonzero and gelu_no_dead
    print("-" * 114)
    print("SELF-TEST %s  relu_zeros_negatives=%s  relu_grad_zero_on_negatives=%s  relu_has_dead=%s  gelu_grad_nonzero=%s  gelu_no_dead=%s"
          % ("PASS" if ok else "FAIL", relu_zeros_negatives, relu_grad_zero_on_negatives, relu_has_dead, gelu_grad_nonzero, gelu_no_dead))
    return ok


def main():
    p = argparse.ArgumentParser(description="Dead ReLU: prefer a smooth (or leaky) activation over plain ReLU where dead units are a risk, because ReLU's gradient is exactly 0 for negative pre-activations, so a neuron whose input stays negative gets no gradient and its weights never update (a permanently dead unit), while a smooth activation passes a nonzero gradient through the negative region so the neuron keeps learning and can recover.")
    p.add_argument("--activate", action="store_true")
    p.add_argument("--dead", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pre_activations=%s  file=%s  (the pre-activation values are a fixture)" % (data["pre_activations"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.activate:
        activate_view(data)
    elif args.dead:
        dead_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
