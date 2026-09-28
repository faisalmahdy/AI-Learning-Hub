"""The linear scaling rule: when you multiply the batch size by k, multiply the learning rate by k too -- a larger batch takes proportionally fewer optimizer steps over the same data, so holding the learning rate fixed makes one k-th the total progress per epoch and the model undertrains.

An optimizer step moves the parameters by the learning rate times the gradient. Over one epoch of N examples, a batch of size b makes N/b steps, so the total parameter movement across the epoch is (N/b) times the learning rate times the per-step gradient. That product is what actually determines how far the model got in an epoch.

Now grow the batch to k times b. Over the same N examples you take only N/(k*b) steps -- a k-th as many, because each step now consumes k times as much data. With the learning rate unchanged, the total movement over the epoch is a k-th of what the small batch achieved. The large-batch run undertrains: same data, less progress. This is often misattributed to large batches 'generalizing worse,' when the immediate, mechanical cause is a learning rate that was never scaled to match the reduced step count.

The linear scaling rule corrects it directly: multiply the learning rate by k so each of the fewer, larger steps moves k times as far, and the total per-epoch movement is restored. It is licensed by the fact that a k-times-larger batch averages the gradient over k times more examples, so it is a lower-variance estimate that can bear the bigger step -- up to a point, past which warmup is needed and eventually the rule breaks down, but across the ordinary range the relationship is linear.

On this fixture N is 64, the small batch is 8, k is 4 (large batch 32), the base learning rate is 0.1, and a representative per-step gradient is 1.0. The small run makes 8 steps and moves 0.8; the large run at the same learning rate makes 2 steps and moves 0.2 -- a quarter, undertrained; the large run at learning rate 0.4 makes 2 steps and moves 0.8 -- matched. This computes all three.

  --steps    the step counts and total movement for the small batch and the large batch at the base learning rate
  --scaled   the large batch with the learning rate scaled by k, restoring the small batch's movement
  --check    the large batch at a fixed learning rate undershoots the small batch's movement by exactly k, while scaling the learning rate by k matches it

N, the small batch, k, the base learning rate, and the gradient are the fixture; step counts and total movements are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "lrscale.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def steps_per_epoch(n, batch):
    """Number of optimizer steps in one epoch: one per batch."""
    return n // batch


def movement(n, batch, lr, grad):
    """Total parameter movement over one epoch: steps times learning rate times per-step gradient."""
    return steps_per_epoch(n, batch) * lr * grad


# ----------------------------------------------------------------- printing

def steps_view(d):
    n, sb, k, lr, g = d["n"], d["small_batch"], d["k"], d["base_lr"], d["grad"]
    lb = sb * k
    print("STEPS — one epoch of %d examples, base learning rate %.2f" % (n, lr))
    print("-" * 64)
    print("  small batch %d: %d steps  ->  movement %.2f" % (sb, steps_per_epoch(n, sb), movement(n, sb, lr, g)))
    print("  large batch %d: %d steps  ->  movement %.2f  <- same lr, %dx fewer steps" % (lb, steps_per_epoch(n, lb), movement(n, lb, lr, g), k))
    print("-" * 64)
    print("  the large batch takes a k-th as many steps, so at the same lr it moves a k-th as far")


def scaled_view(d):
    n, sb, k, lr, g = d["n"], d["small_batch"], d["k"], d["base_lr"], d["grad"]
    lb = sb * k
    print("SCALED — large batch %d with learning rate scaled by k=%d" % (lb, k))
    print("-" * 64)
    print("  scaled learning rate = %.2f x %d = %.2f" % (lr, k, lr * k))
    print("  large batch %d: %d steps  ->  movement %.2f" % (lb, steps_per_epoch(n, lb), movement(n, lb, lr * k, g)))
    print("  small batch %d movement (target) = %.2f" % (sb, movement(n, sb, lr, g)))
    print("-" * 64)
    print("  each of the fewer steps is k times larger, so the total per-epoch movement matches")


def check(d):
    print("SELF-TEST — the large batch at a fixed learning rate undershoots the small batch's movement by exactly k, while scaling the learning rate by k matches it")
    print("-" * 112)
    n, sb, k, lr, g = d["n"], d["small_batch"], d["k"], d["base_lr"], d["grad"]
    lb = sb * k

    small_move = movement(n, sb, lr, g)
    large_fixed = movement(n, lb, lr, g)
    large_scaled = movement(n, lb, lr * k, g)

    large_undershoots = large_fixed < small_move
    print("  large batch at fixed lr moves less than the small batch = %s (%.2f < %.2f)" % (large_undershoots, large_fixed, small_move))

    undershoot_is_k = abs(small_move / large_fixed - k) < 1e-9
    print("  the shortfall factor equals k = %s (%.2f / %.2f = %g)" % (undershoot_is_k, small_move, large_fixed, small_move / large_fixed))

    scaled_matches = abs(large_scaled - small_move) < 1e-9
    print("  scaling the learning rate by k matches the small batch = %s (%.2f == %.2f)" % (scaled_matches, large_scaled, small_move))

    fewer_steps = steps_per_epoch(n, lb) * k == steps_per_epoch(n, sb)
    print("  the large batch takes a k-th as many steps = %s (%d x %d = %d)" % (fewer_steps, steps_per_epoch(n, lb), k, steps_per_epoch(n, sb)))

    ok = (large_undershoots and undershoot_is_k and scaled_matches and fewer_steps)
    print("-" * 112)
    print("SELF-TEST %s  large_undershoots=%s  undershoot_is_k=%s  scaled_matches=%s  fewer_steps=%s"
          % ("PASS" if ok else "FAIL", large_undershoots, undershoot_is_k, scaled_matches, fewer_steps))
    return ok


def main():
    p = argparse.ArgumentParser(description="Linear scaling rule: when you multiply the batch size by k, multiply the learning rate by k, because a larger batch takes a k-th as many optimizer steps over the same data -- so at a fixed learning rate its total per-epoch movement is a k-th of the small batch's and the model undertrains; scaling the learning rate by k makes each of the fewer, larger steps move k times as far and restores the progress, licensed by the larger batch's lower-variance gradient.")
    p.add_argument("--steps", action="store_true")
    p.add_argument("--scaled", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("n=%d  small_batch=%d  k=%d  base_lr=%.2f  grad=%.1f  file=%s"
          % (d["n"], d["small_batch"], d["k"], d["base_lr"], d["grad"], DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.steps:
        steps_view(d)
    elif args.scaled:
        scaled_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
