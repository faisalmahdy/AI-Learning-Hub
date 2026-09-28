"""Retry at one layer, not every layer, or retries multiply into a storm on the failing dependency.

Retries are the reflex fix for a flaky call: if it fails, try again. Applied at one place that is sensible.
Applied at every layer of a call stack, it is a multiplier. A request passes through several services --
edge, then service A, then service B, then the database -- and if each layer retries its downstream on
failure, the retries compound. The edge calls A; A fails, so the edge retries it; but each of A's attempts
itself retried B; and each of those retried the database. The database, already struggling (which is why
calls were failing), is hit not once per request but retries-to-the-power-of-layers times. The retry meant
to ride out a blip instead pours a multiplied flood onto the exact component that was failing, turning a
transient dip into a self-inflicted outage. This is retry amplification.

The fix is a retry budget: do not let every layer retry independently. Retry at a single layer (usually the
edge, or the one closest to the user), and have the inner layers fail fast and propagate. Or cap the total
retries per request across the whole stack. Either way the load on the failing dependency is bounded by a
small constant instead of growing multiplicatively with depth -- so a struggling backend sees a survivable
number of extra calls, not an exponential pile-on.

On this fixture a request crosses 3 retrying layers to reach a failing backend, each layer retrying 3
times. Retrying at every layer hits the backend 3^3 = 27 times for one request. Retrying at only one layer
hits it 3 times. Same per-layer retry count; the difference is whether the retries multiply. This computes
both.

  --trace      calls reaching each layer under retry-everywhere vs retry-at-one-layer
  --amplify    the backend load and amplification factor of each policy
  --check      retrying at every layer amplifies multiplicatively; retrying at one layer bounds the load

The layer count and retry count are the fixture; every call count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "stack.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def calls_per_layer_naive(layers, retries):
    """Calls reaching each layer when every layer retries its downstream: retries**depth."""
    return [retries ** d for d in range(layers + 1)]   # index 0 = the entry, index `layers` = the backend


def calls_per_layer_edge(layers, retries):
    """Calls reaching each layer when only the edge retries: retries at every hop, no compounding."""
    return [1] + [retries] * layers


def backend_calls(per_layer):
    return per_layer[-1]


# ----------------------------------------------------------------- printing

def trace_view(data):
    layers, retries = data["layers"], data["retries"]
    naive = calls_per_layer_naive(layers, retries)
    edge = calls_per_layer_edge(layers, retries)
    names = ["entry"] + ["layer%d" % (i + 1) for i in range(layers - 1)] + ["backend"]
    print("TRACE — calls reaching each layer (%d layers, %d retries each)" % (layers, retries))
    print("-" * 56)
    print("  %-10s retry-every-layer   retry-one-layer" % "reaches")
    for name, n, e in zip(names, naive, edge):
        print("  %-10s %-18d  %d" % (name, n, e))
    print("-" * 56)
    print("  retry-every-layer multiplies by %d each hop; retry-one-layer does not." % retries)


def amplify_view(data):
    layers, retries = data["layers"], data["retries"]
    naive = backend_calls(calls_per_layer_naive(layers, retries))
    edge = backend_calls(calls_per_layer_edge(layers, retries))
    print("AMPLIFY — backend load per request")
    print("-" * 56)
    print("  retry every layer: %d calls  (%d^%d)" % (naive, retries, layers))
    print("  retry one layer:   %d calls" % edge)
    print("  amplification of retry-every-layer over retry-one-layer: %dx" % (naive // edge))
    print("-" * 56)
    print("  the failing backend sees %d calls instead of %d for one request." % (naive, edge))


def check(data):
    print("SELF-TEST — retrying at every layer amplifies multiplicatively; retrying at one layer bounds the load")
    print("-" * 96)
    layers, retries = data["layers"], data["retries"]
    naive = calls_per_layer_naive(layers, retries)
    edge = calls_per_layer_edge(layers, retries)
    naive_backend = backend_calls(naive)
    edge_backend = backend_calls(edge)

    naive_is_exponential = naive_backend == retries ** layers
    print("  retry-every-layer hits the backend retries**layers times = %s (%d = %d^%d)"
          % (naive_is_exponential, naive_backend, retries, layers))

    grows_multiplicatively = all(naive[i + 1] == retries * naive[i] for i in range(layers))
    print("  each hop multiplies the calls by the retry count = %s (%s)" % (grows_multiplicatively, naive))

    edge_is_bounded = edge_backend == retries
    print("  retry-one-layer hits the backend a fixed retries times = %s (%d)" % (edge_is_bounded, edge_backend))

    edge_independent_of_depth = edge_backend == backend_calls(calls_per_layer_edge(layers + 5, retries))
    print("  retry-one-layer's backend load does not grow with depth = %s" % edge_independent_of_depth)

    amplification = naive_backend > edge_backend
    print("  retry-every-layer's backend load dwarfs retry-one-layer = %s (%d vs %d, %dx)"
          % (amplification, naive_backend, edge_backend, naive_backend // edge_backend))

    ok = naive_is_exponential and grows_multiplicatively and edge_is_bounded and edge_independent_of_depth and amplification
    print("-" * 96)
    print("SELF-TEST %s  naive_is_exponential=%s  grows_multiplicatively=%s  edge_is_bounded=%s  edge_independent_of_depth=%s  amplification=%s"
          % ("PASS" if ok else "FAIL", naive_is_exponential, grows_multiplicatively, edge_is_bounded, edge_independent_of_depth, amplification))
    return ok


def main():
    p = argparse.ArgumentParser(description="Retry at one layer, not every layer, to avoid retry amplification.")
    p.add_argument("--trace", action="store_true")
    p.add_argument("--amplify", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("layers=%d  retries=%d  file=%s  (the layer and retry counts are a fixture)"
          % (data["layers"], data["retries"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.trace:
        trace_view(data)
    elif args.amplify:
        amplify_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
