"""Switch batch norm to eval mode at inference -- in train mode an example's output depends on its batchmates.

Batch normalization standardizes an activation by subtracting a mean and dividing by a standard deviation, then applying
a learned scale and shift. The subtlety is WHICH mean and standard deviation. During training, batch norm uses the
statistics of the CURRENT mini-batch -- the mean and variance of the activations across the examples that happen to be
batched together on that step. This is deliberate: it is what makes the normalization adapt as the network learns, and
the noise it injects even acts as a mild regularizer. But it has a consequence that is fine during training and
catastrophic at inference: an example's normalized value depends on the OTHER examples in its batch. The same input, put
in a different batch, comes out a different number.

That is exactly why batch norm keeps a second set of statistics: a running mean and running variance, accumulated across
all of training as an exponential moving average of the batch statistics. At inference the layer is supposed to switch
to EVAL mode and use those fixed running statistics instead of the batch's, so that an example's output depends only on
the example -- deterministic, batch-independent, correct one at a time. The bug is forgetting to switch: running a model
with batch norm still in TRAIN mode at inference. Now predictions depend on how requests are grouped into batches, the
same input scores differently depending on its neighbors, and a batch of size one -- the normal case for a single
online request -- has zero variance, so every input collapses to the shift parameter beta and the feature carries no
information at all. It is a silent bug: the shapes are right, no error is thrown, the numbers are just quietly wrong and
irreproducible.

On this fixture the layer has running_mean 0 and running_var 1, and we score the example x=2.0. In EVAL mode it
normalizes to (2-0)/sqrt(1) = 2.0 regardless of any batch. In TRAIN mode, batched with [2, 0, 4] it comes out 0.0 (that
batch's mean is 2, so x sits at the mean), but batched with [2, 6, 10] the SAME x=2.0 comes out -1.2247 -- the batchmates
moved it. And a size-1 batch normalizes x to 0.0 for ANY x. This computes all of it.

  --modes     the example scored in eval mode (running stats) vs train mode (this batch's stats) -- 2.0 vs 0.0
  --batchdep  the same example in batch_a vs batch_b under train mode -- 0.0 vs -1.2247, output depends on batchmates
  --check     eval uses running stats and is batch-independent; train uses batch stats so the output moves with the batch; size-1 collapses

The statistics, example, and batches are the fixture; every normalized output is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "batchnorm.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def normalize(x, mean, var, data):
    """Batch-norm transform: scale*(x - mean)/sqrt(var + eps) + shift."""
    return data["gamma"] * (x - mean) / math.sqrt(var + data["eps"]) + data["beta"]


def eval_mode(x, data):
    """Inference-correct: normalize with the fixed running statistics -- depends only on x."""
    return normalize(x, data["running_mean"], data["running_var"], data)


def train_mode(x, batch, data):
    """Inference-BUG: normalize with THIS batch's mean and variance -- depends on the batchmates."""
    mean = sum(batch) / len(batch)
    var = sum((z - mean) ** 2 for z in batch) / len(batch)
    return normalize(x, mean, var, data)


# ----------------------------------------------------------------- printing

def modes_view(data):
    x = data["example"]
    print("MODES — the same example under eval mode vs train mode")
    print("-" * 60)
    print("  running stats: mean=%.1f var=%.1f   gamma=%.1f beta=%.1f" % (
        data["running_mean"], data["running_var"], data["gamma"], data["beta"]))
    print("  example x = %.1f" % x)
    print("-" * 60)
    print("  EVAL  (running stats): (%.1f-%.1f)/sqrt(%.1f) = %.4f" % (
        x, data["running_mean"], data["running_var"], eval_mode(x, data)))
    print("  TRAIN (batch %s stats): = %.4f" % (data["batch_a"], train_mode(x, data["batch_a"], data)))
    print("  eval is correct at inference; train mode leaks the batch into the answer.")


def batchdep_view(data):
    x = data["example"]
    print("BATCHDEP — the same example, two different batches, TRAIN mode")
    print("-" * 62)
    for name in ("batch_a", "batch_b"):
        batch = data[name]
        mean = sum(batch) / len(batch)
        print("  %s = %-14s mean=%.1f -> train-mode output %.4f" % (name, batch, mean, train_mode(x, batch, data)))
    print("  (eval-mode output is %.4f for both -- it never looks at the batch)" % eval_mode(x, data))
    print("-" * 62)
    single = train_mode(x, [x], data)
    print("  batch of size 1 ([%.1f]): variance 0, output collapses to beta = %.4f (true of ANY input)." % (x, single))


def check(data):
    print("SELF-TEST — eval uses running stats and is batch-independent; train uses batch stats so the output moves with the batch; size-1 collapses")
    print("-" * 132)
    x = data["example"]

    ev = eval_mode(x, data)
    eval_is_running = abs(ev - (x - data["running_mean"]) / math.sqrt(data["running_var"] + data["eps"])) < 1e-12
    print("  eval mode normalizes with the running stats = %s (%.4f)" % (eval_is_running, ev))

    ta = train_mode(x, data["batch_a"], data)
    tb = train_mode(x, data["batch_b"], data)
    train_depends_on_batchmates = abs(ta - tb) > 1e-6
    print("  train mode gives the SAME x different outputs per batch = %s (%.4f vs %.4f)" % (train_depends_on_batchmates, ta, tb))

    train_ne_eval = abs(ta - ev) > 1e-6
    print("  train-mode output differs from the correct eval output = %s (%.4f vs %.4f)" % (train_ne_eval, ta, ev))

    eval_batch_independent = eval_mode(x, data) == ev
    print("  eval-mode output never depends on a batch = %s (%.4f)" % (eval_batch_independent, ev))

    single = train_mode(x, [x], data)
    other = train_mode(99.0, [99.0], data)
    size1_collapses = abs(single - data["beta"]) < 1e-3 and abs(other - data["beta"]) < 1e-3
    print("  a size-1 batch collapses any input to beta = %s (x=%.1f->%.4f, x=99->%.4f)" % (size1_collapses, x, single, other))

    ok = eval_is_running and train_depends_on_batchmates and train_ne_eval and eval_batch_independent and size1_collapses
    print("-" * 132)
    print("SELF-TEST %s  eval_is_running=%s  train_depends_on_batchmates=%s  train_ne_eval=%s  eval_batch_independent=%s  size1_collapses=%s"
          % ("PASS" if ok else "FAIL", eval_is_running, train_depends_on_batchmates, train_ne_eval, eval_batch_independent, size1_collapses))
    return ok


def main():
    p = argparse.ArgumentParser(description="Batch norm train/eval mode: at inference the layer must use its fixed running mean/variance (eval mode); left in train mode it normalizes by the current batch's statistics, so an example's output depends on its batchmates, the same input scores differently in different batches, and a size-1 batch collapses every input to beta.")
    p.add_argument("--modes", action="store_true")
    p.add_argument("--batchdep", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("running=(mean %.1f, var %.1f)  example=%.1f  batch_a=%s  batch_b=%s  file=%s  (the stats and batches are a fixture)"
          % (data["running_mean"], data["running_var"], data["example"], data["batch_a"], data["batch_b"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.modes:
        modes_view(data)
    elif args.batchdep:
        batchdep_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
