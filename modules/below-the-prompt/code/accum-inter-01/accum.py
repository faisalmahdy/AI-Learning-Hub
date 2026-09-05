"""Average the accumulated micro-batch gradients, or you have secretly multiplied the learning rate.

You want to train with a large batch -- say 6 examples per step for a stable gradient -- but the batch will
not fit in memory. The standard trick is gradient accumulation: run k smaller micro-batches, add up their
gradients, do one optimizer step, and you have simulated the big batch without ever holding it all at once.
It works exactly when the accumulated gradient equals the gradient the full batch would have produced --
which is the AVERAGE of the micro-batch gradients, not their sum.

Summing is the classic bug. Accumulate k micro-batch gradients by adding them and forget to divide by k,
and the gradient you step with is k times too large. The optimizer takes a step k times bigger than you
configured: your effective learning rate is silently multiplied by the number of accumulation steps.
Nothing errors -- the loss just becomes unstable or diverges, and you burn a day wondering why a learning
rate that worked at batch size 2 explodes at an accumulation of 3. The fix is one division: average the
accumulated gradient over the number of micro-batches, and it matches the full batch exactly.

On this fixture 6 example gradients are processed as 3 micro-batches of 2. The correct (averaged)
accumulation reproduces the full-batch gradient exactly, so its update matches what one big batch would do.
The buggy (summed) accumulation is 3 times too large, so its update is 3 times too big -- identical to
running the correct code at 3 times the learning rate. This computes both.

  --grads      the full-batch gradient vs the averaged and summed accumulations
  --update     the optimizer step each produces, and the effective learning rate of the bug
  --check      averaging reproduces the full batch; summing multiplies the step by the accumulation count

The example gradients, micro-batch size, and learning rate are the fixture; every gradient is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "grads.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def vadd(a, b):
    return [x + y for x, y in zip(a, b)]


def vscale(v, f):
    return [x * f for x in v]


def vmean(vs):
    total = vs[0]
    for v in vs[1:]:
        total = vadd(total, v)
    return vscale(total, 1.0 / len(vs))


def norm(v):
    return math.sqrt(sum(x * x for x in v))


def micro_batches(grads, m):
    """Split the per-example gradients into micro-batches of size m, each averaged."""
    return [vmean(grads[i:i + m]) for i in range(0, len(grads), m)]


def full_batch_grad(grads):
    """The gradient the whole batch would produce -- the mean over all examples."""
    return vmean(grads)


def accum_averaged(grads, m):
    """Correct accumulation: average the micro-batch gradients."""
    return vmean(micro_batches(grads, m))


def accum_summed(grads, m):
    """Buggy accumulation: sum the micro-batch gradients (forgot to divide by k)."""
    mbs = micro_batches(grads, m)
    total = mbs[0]
    for v in mbs[1:]:
        total = vadd(total, v)
    return total


# ----------------------------------------------------------------- printing

def grads_view(data):
    grads, m = data["grads"], data["micro_batch"]
    k = len(micro_batches(grads, m))
    print("GRADS — full-batch gradient vs accumulations (%d micro-batches of %d)" % (k, m))
    print("-" * 58)
    print("  full batch (mean of all): %s" % [round(x, 3) for x in full_batch_grad(grads)])
    print("  averaged accumulation:    %s" % [round(x, 3) for x in accum_averaged(grads, m)])
    print("  summed accumulation:      %s" % [round(x, 3) for x in accum_summed(grads, m)])
    print("-" * 58)
    print("  averaged == full batch; summed is %dx too large." % k)


def update_view(data):
    grads, m, lr = data["grads"], data["micro_batch"], data["lr"]
    k = len(micro_batches(grads, m))
    up_ok = vscale(accum_averaged(grads, m), lr)
    up_bug = vscale(accum_summed(grads, m), lr)
    print("UPDATE — optimizer step (lr %.2f) from each accumulation" % lr)
    print("-" * 58)
    print("  averaged step: %s   norm %.3f" % ([round(x, 3) for x in up_ok], norm(up_ok)))
    print("  summed step:   %s   norm %.3f" % ([round(x, 3) for x in up_bug], norm(up_bug)))
    print("-" * 58)
    print("  the summed step equals the averaged step at lr=%.2f (%dx the learning rate)." % (lr * k, k))


def check(data):
    print("SELF-TEST — averaging reproduces the full batch; summing multiplies the step by the accumulation count")
    print("-" * 100)
    grads, m, lr = data["grads"], data["micro_batch"], data["lr"]
    k = len(micro_batches(grads, m))
    full = full_batch_grad(grads)
    avg = accum_averaged(grads, m)
    summed = accum_summed(grads, m)

    averaged_matches_full = max(abs(a - b) for a, b in zip(avg, full)) < 1e-9
    print("  averaged accumulation equals the full-batch gradient = %s" % averaged_matches_full)

    summed_is_k_times = max(abs(s - k * f) for s, f in zip(summed, full)) < 1e-9
    print("  summed accumulation is exactly k times the full gradient = %s (k=%d)" % (summed_is_k_times, k))

    up_ok, up_bug = vscale(avg, lr), vscale(summed, lr)
    bug_step_k_times = abs(norm(up_bug) - k * norm(up_ok)) < 1e-9
    print("  the buggy step is k times the correct step = %s (%.3f vs %.3f)" % (bug_step_k_times, norm(up_bug), norm(up_ok)))

    # the buggy step at lr equals the correct step at lr*k -- effective learning rate is multiplied
    up_ok_klr = vscale(avg, lr * k)
    effective_lr_k = max(abs(a - b) for a, b in zip(up_bug, up_ok_klr)) < 1e-9
    print("  the bug is identical to the correct code at k times the learning rate = %s (lr %.2f)" % (effective_lr_k, lr * k))

    correct_reproduces_fullbatch = max(abs(a - b) for a, b in zip(vscale(avg, lr), vscale(full, lr))) < 1e-9
    print("  correct accumulation reproduces the full-batch step with no full batch in memory = %s" % correct_reproduces_fullbatch)

    ok = averaged_matches_full and summed_is_k_times and bug_step_k_times and effective_lr_k and correct_reproduces_fullbatch
    print("-" * 100)
    print("SELF-TEST %s  averaged_matches_full=%s  summed_is_k_times=%s  bug_step_k_times=%s  effective_lr_k=%s  correct_reproduces_fullbatch=%s"
          % ("PASS" if ok else "FAIL", averaged_matches_full, summed_is_k_times, bug_step_k_times, effective_lr_k, correct_reproduces_fullbatch))
    return ok


def main():
    p = argparse.ArgumentParser(description="Average accumulated micro-batch gradients so accumulation matches the full batch.")
    p.add_argument("--grads", action="store_true")
    p.add_argument("--update", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    k = len(micro_batches(data["grads"], data["micro_batch"]))
    print("examples=%d  micro_batch=%d  accum_steps=%d  lr=%.2f  file=%s  (the gradients are a fixture)"
          % (len(data["grads"]), data["micro_batch"], k, data["lr"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.grads:
        grads_view(data)
    elif args.update:
        update_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
