"""Keep sqrt(N) activations, not all N -- gradient checkpointing trades one extra forward pass for a memory ceiling.

Backpropagation through an N-layer network needs each layer's forward activation to compute that layer's gradient, so
the naive backward pass keeps all N activations in memory at once. For a deep, wide model that is the memory wall: the
activations, not the weights, are what overflow the accelerator, and they grow linearly with depth. The opposite
extreme -- keep nothing and recompute each activation from the input when the backward pass reaches it -- fixes memory
but pays for it catastrophically in compute: recomputing layer i from scratch costs i forward steps, and summed over
all layers that is N*(N+1)/2, quadratic recompute. Neither storing everything nor storing nothing is the answer.

Gradient (activation) checkpointing takes the middle. Keep only a few evenly spaced activations -- the checkpoints --
and during the backward pass recompute the layers between two checkpoints on demand, starting from the checkpoint just
before them. Now peak memory is the checkpoints you hold plus the one segment you are actively recomputing: with c
checkpoints over N layers each segment is about N/c long, so peak memory is about c + N/c. That sum is minimized at
c = sqrt(N), giving a memory ceiling of about 2*sqrt(N) instead of N -- a square-root, not linear, footprint. The cost
is that every non-checkpoint layer is recomputed once, which is at most one extra forward pass over the network, not a
quadratic blowup. You buy a square-root memory ceiling for a single recompute of the forward.

On this fixture the network is 64 layers deep. Storing all activations costs 64 units of memory and zero recompute;
storing none costs 1 unit but 2080 layer-recomputes (quadratic); checkpointing at sqrt(64) = 8 costs 16 units of memory
-- a 4x reduction -- for 56 recomputes, under one extra forward pass. This computes all three.

  --memory     peak activation memory and recompute for store-all, sqrt-checkpointing, and store-none
  --tradeoff   peak memory c + N/c across checkpoint counts, and the sqrt(N) count that minimizes it
  --check      store-all is linear memory; store-none is quadratic recompute; sqrt-checkpointing is sqrt(N) memory, ~1 pass

The layer count and checkpoint count are the fixture; every memory and recompute count is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "checkpoint.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def checkpoint_memory(n, c):
    """Peak activation memory with c checkpoints: the c stored checkpoints plus one active segment of length n/c."""
    return c + math.ceil(n / c)


def checkpoint_recompute(n, c):
    """Extra layer-forwards in the backward pass: every non-checkpoint layer is recomputed once."""
    return n - c


def store_none_recompute(n):
    """Recompute layer i from the input for every i: 1 + 2 + ... + n = n(n+1)/2, quadratic."""
    return n * (n + 1) // 2


def optimal_checkpoints(n):
    """The checkpoint count that minimizes peak memory c + n/c -- the integer nearest sqrt(n)."""
    return min(range(1, n + 1), key=lambda c: checkpoint_memory(n, c))


# ----------------------------------------------------------------- printing

def memory_view(data):
    n, c = data["n_layers"], data["checkpoints"]
    print("MEMORY — peak activation memory vs recompute, three strategies (%d layers)" % n)
    print("-" * 68)
    print("  strategy            peak memory      recompute (extra layer-forwards)")
    print("  store all           %-15d  %d" % (n, 0))
    print("  checkpoint sqrt(N)  %-15d  %d" % (checkpoint_memory(n, c), checkpoint_recompute(n, c)))
    print("  store none          %-15d  %d" % (1, store_none_recompute(n)))
    print("-" * 68)
    print("  checkpointing cuts memory %dx for under one extra forward pass; store-none pays %dx the recompute."
          % (n // checkpoint_memory(n, c), store_none_recompute(n) // max(1, checkpoint_recompute(n, c))))


def tradeoff_view(data):
    n = data["n_layers"]
    print("TRADEOFF — peak memory c + N/c across checkpoint counts (N=%d)" % n)
    print("-" * 50)
    print("  checkpoints c   peak memory   recompute")
    for c in (1, 2, 4, 8, 16, 32, 64):
        mark = "  <- min (sqrt N)" if c == optimal_checkpoints(n) else ""
        print("  %-13d   %-11d   %d%s" % (c, checkpoint_memory(n, c), checkpoint_recompute(n, c), mark))
    print("-" * 50)
    print("  memory is a U in c: too few checkpoints means big segments, too many means storing them all.")


def check(data):
    print("SELF-TEST — store-all is linear memory; store-none is quadratic recompute; sqrt-checkpointing is sqrt(N) memory, ~1 pass")
    print("-" * 118)
    n, c = data["n_layers"], data["checkpoints"]

    store_all_memory = n  # storing every activation costs one memory unit per layer, and recomputes nothing
    store_all_linear = store_all_memory == n and store_all_memory > checkpoint_memory(n, c)
    print("  store-all peak memory equals the depth (linear) = %s (%d, recompute 0)" % (store_all_linear, store_all_memory))

    store_none_quadratic = store_none_recompute(n) > n * n // 2
    print("  store-none recompute is quadratic in depth = %s (%d > %d)" % (store_none_quadratic, store_none_recompute(n), n * n // 2))

    checkpoint_sqrt_memory = checkpoint_memory(n, c) <= 2 * math.isqrt(n) + 1
    print("  sqrt-checkpointing memory is about 2*sqrt(N) = %s (%d <= %d)" % (checkpoint_sqrt_memory, checkpoint_memory(n, c), 2 * math.isqrt(n) + 1))

    recompute_under_one_pass = checkpoint_recompute(n, c) < n
    print("  its recompute is under one extra forward pass (linear) = %s (%d < %d)" % (recompute_under_one_pass, checkpoint_recompute(n, c), n))

    sqrt_is_optimal = optimal_checkpoints(n) == c and c == math.isqrt(n)
    print("  the memory-minimizing checkpoint count is sqrt(N) = %s (%d)" % (sqrt_is_optimal, optimal_checkpoints(n)))

    beats_store_all = checkpoint_memory(n, c) < n
    print("  checkpointing uses far less memory than store-all = %s (%d < %d)" % (beats_store_all, checkpoint_memory(n, c), n))

    ok = store_all_linear and store_none_quadratic and checkpoint_sqrt_memory and recompute_under_one_pass and sqrt_is_optimal and beats_store_all
    print("-" * 118)
    print("SELF-TEST %s  store_none_quadratic=%s  checkpoint_sqrt_memory=%s  recompute_under_one_pass=%s  sqrt_is_optimal=%s  beats_store_all=%s"
          % ("PASS" if ok else "FAIL", store_none_quadratic, checkpoint_sqrt_memory, recompute_under_one_pass, sqrt_is_optimal, beats_store_all))
    return ok


def main():
    p = argparse.ArgumentParser(description="Gradient checkpointing: keep sqrt(N) activations and recompute the rest, for an O(sqrt(N)) memory ceiling at the cost of one extra forward pass.")
    p.add_argument("--memory", action="store_true")
    p.add_argument("--tradeoff", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n_layers=%d  checkpoints=%d  file=%s  (the layer and checkpoint counts are a fixture)"
          % (data["n_layers"], data["checkpoints"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.memory:
        memory_view(data)
    elif args.tradeoff:
        tradeoff_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
