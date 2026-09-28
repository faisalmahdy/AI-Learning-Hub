"""Retries at every layer multiply -- one request becomes attempts^depth at the bottom, a storm exactly during an incident.

A retry is a good idea in isolation: a request fails transiently, you try again, it succeeds. The trouble is that a
modern request passes through a stack of services -- a frontend calls an api, which calls storage, which calls a disk
layer -- and each of them, sensibly, retries on a failure from the layer below. Those retries COMPOUND. When the api
retries its call to storage 3 times, and storage retries its call to disk 3 times, and the frontend retries the api 3
times, a single top-level request can become 3 x 3 x 3 = 27 requests at the disk, because each retry at a layer re-drives
the entire subtree beneath it. The amplification is the PRODUCT of the per-layer retry counts, and it grows exponentially
with the depth of the call chain.

The reason this is dangerous, and not just wasteful, is the timing: retries fire precisely when something is failing,
which is precisely when the failing layer can least afford extra load. A disk layer that is briefly slow returns some
errors; every layer above dutifully retries; the disk is now hit with many times its normal traffic while it is already
struggling; it fails more; the retries multiply further. This is a retry storm (a metastable failure), and it can keep a
service down long after the original trigger is gone, because the retries themselves have become the load. The naive
per-layer retry that helps a single request is the mechanism that prevents the whole system from recovering.

The fixes all attack the multiplication. Retry at ONLY ONE layer (usually the edge) so the factor is linear in that
layer's attempts, not a product across the depth. Impose a retry BUDGET -- allow retries only up to a small fraction of
requests (a token bucket), so a widespread failure cannot multiply load. Propagate a DEADLINE so a retry is not even
attempted once the overall time budget is spent. And add backoff with jitter and circuit breakers so retries slow down
and stop when the downstream is unhealthy.

On this fixture the chain is frontend -> api -> storage -> disk, and each of the three upper layers retries 3 times. One
request reaches the disk as 27 requests (load grows 1 -> 3 -> 9 -> 27 down the chain). Retrying at only the edge makes it
3; not retrying at all makes it 1. This computes each.

  --amplify   the load reaching each layer and the total amplification for the per-layer-retry chain -- one request -> 27
  --budget    the same chain with retries at only the edge (linear, 3) and with no retries (1), against the naive 27
  --check     the amplification is the product of per-layer attempts; deep per-layer retry explodes; edge-only is linear

The chain and per-layer attempts are the fixture; every load figure is computed. Stdlib only.
"""
import argparse
import json
import sys
from math import prod
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "retryamp.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def inbound_per_layer(attempts):
    """Requests reaching each layer for one top-level request: the running product of the attempts above it (top = 1)."""
    load = [1]
    for a in attempts:
        load.append(load[-1] * a)
    return load


def amplification(attempts):
    """Total requests reaching the bottom layer per top-level request: the product of every layer's retry count."""
    return prod(attempts)


def edge_only(attempts):
    """Retry only at the edge (top) layer; every layer below does a single attempt."""
    return [attempts[0]] + [1] * (len(attempts) - 1)


def no_retry(attempts):
    """No retries anywhere: one attempt per layer."""
    return [1] * len(attempts)


# ----------------------------------------------------------------- printing

def amplify_view(data):
    layers, attempts = data["layers"], data["attempts"]
    load = inbound_per_layer(attempts)
    print("AMPLIFY — load reaching each layer, per-layer retry (attempts=%s)" % attempts)
    print("-" * 60)
    print("  layer        retries downstream   requests reaching it")
    for i, name in enumerate(layers):
        retries = attempts[i] if i < len(attempts) else "-"
        print("  %-11s  %-18s   %d" % (name, retries, load[i]))
    print("-" * 60)
    print("  one top request becomes %d at the bottom (%s) -- amplification x%d."
          % (amplification(attempts), layers[-1], amplification(attempts)))


def budget_view(data):
    attempts = data["attempts"]
    print("BUDGET — where you allow retries decides the multiplier")
    print("-" * 58)
    print("  per-layer retry (all 3): attempts=%s -> bottom load %d" % (attempts, amplification(attempts)))
    print("  edge-only retry        : attempts=%s -> bottom load %d" % (edge_only(attempts), amplification(edge_only(attempts))))
    print("  no retry (baseline)    : attempts=%s -> bottom load %d" % (no_retry(attempts), amplification(no_retry(attempts))))
    print("-" * 58)
    print("  retrying at one layer is linear; retrying at every layer is a product across the depth.")


def check(data):
    print("SELF-TEST — the amplification is the product of per-layer attempts; deep per-layer retry explodes; edge-only is linear")
    print("-" * 122)
    layers, attempts = data["layers"], data["attempts"]

    load = inbound_per_layer(attempts)
    amp_is_product = load[-1] == prod(attempts)
    print("  the bottom-layer load equals the product of attempts = %s (%d == %s)" % (amp_is_product, load[-1], "*".join(map(str, attempts))))

    deep_explodes = amplification(attempts) >= 27
    print("  three layers each retrying 3x reach 27x load = %s (%d)" % (deep_explodes, amplification(attempts)))

    edge_linear = amplification(edge_only(attempts)) == attempts[0]
    print("  retrying only at the edge is linear in its attempts = %s (%d)" % (edge_linear, amplification(edge_only(attempts))))

    baseline_one = amplification(no_retry(attempts)) == 1
    print("  no retries anywhere is 1x load = %s" % baseline_one)

    budget_beats_naive = amplification(edge_only(attempts)) < amplification(attempts)
    print("  edge-only load is far below per-layer load = %s (%d < %d)"
          % (budget_beats_naive, amplification(edge_only(attempts)), amplification(attempts)))

    ok = amp_is_product and deep_explodes and edge_linear and baseline_one and budget_beats_naive
    print("-" * 122)
    print("SELF-TEST %s  amp_is_product=%s  deep_explodes=%s  edge_linear=%s  baseline_one=%s  budget_beats_naive=%s"
          % ("PASS" if ok else "FAIL", amp_is_product, deep_explodes, edge_linear, baseline_one, budget_beats_naive))
    return ok


def main():
    p = argparse.ArgumentParser(description="Retry amplification: retries at every layer of a call chain multiply, so one request becomes attempts^depth at the bottom -- a retry storm exactly when the failing downstream can least afford it; fix it by retrying at one layer, imposing a retry budget, and propagating deadlines.")
    p.add_argument("--amplify", action="store_true")
    p.add_argument("--budget", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("layers=%s  attempts=%s  file=%s  (the chain and attempts are a fixture)"
          % (data["layers"], data["attempts"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.amplify:
        amplify_view(data)
    elif args.budget:
        budget_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
