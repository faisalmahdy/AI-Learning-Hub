"""Balance the expert load and cap it, or a Mixture-of-Experts router sends every token to a few experts and starves the rest.

A Mixture-of-Experts layer has many expert sub-networks and a router that sends each token to only one or a few of them,
so the model has huge capacity but activates a small slice per token. The catch is the router. Nothing in "pick the
highest-scoring expert" forces the load to spread: training can drive the router into a corner where a handful of
experts win almost every token and the rest receive almost none. Those starved experts never get gradients, never
improve, and stay dead weight -- routing collapse -- so a model that paid for many experts effectively runs a few. The
router optimizing only for the main loss has every incentive to concentrate on the experts that are already good, a rich
-get-richer spiral, and no incentive to keep the others alive.

Two mechanisms keep the load balanced. First, an auxiliary load-balancing loss added to training: E * sum over experts
of (fraction of tokens routed there) x (mean gate probability there). It is minimized at 1.0 when every expert gets an
equal share and grows as the load concentrates, so adding it to the objective pushes the router toward spreading tokens
even when the main loss would rather pile them up. Second, an expert CAPACITY: each expert can process only so many
tokens per batch -- capacity_factor x tokens / experts -- and tokens beyond that overflow and are dropped (skipped, or
passed through). Capacity is a hard cap that bounds the damage of imbalance and keeps the computation rectangular for the
hardware, at the cost of dropping the overflow. The load-balancing loss discourages imbalance; the capacity survives it.

On this fixture the router prefers expert 0: top-1 routing sends 5 of 8 tokens there, 2 to expert 1, 1 to expert 2, and
0 to expert 3 -- a dead expert. The load-balancing loss is 1.50, well above the balanced 1.00. With capacity_factor 1.0
each expert may take 2 tokens, so expert 0's 5 overflow to 2 kept and 3 dropped. This computes both.

  --route    the top-1 load per expert, the dead expert, and the tokens dropped when an expert exceeds capacity
  --balance  the load-balancing auxiliary loss for this routing vs the balanced minimum of 1.0
  --check    the load is imbalanced with a dead expert; the aux loss exceeds 1.0; capacity caps load and drops overflow

The gates, expert count, and capacity factor are the fixture; every load and loss is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "moe.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def top1_route(gates):
    """Each token goes to the expert with the highest gate probability (argmax)."""
    return [max(range(len(g)), key=lambda e: g[e]) for g in gates]


def loads(routes, num_experts):
    """Number of tokens routed to each expert."""
    return [routes.count(e) for e in range(num_experts)]


def balance_loss(gates, routes, num_experts):
    """Switch-Transformer aux loss: E * sum_e (fraction routed to e) * (mean gate for e). 1.0 when balanced."""
    n = len(gates)
    frac = [routes.count(e) / n for e in range(num_experts)]
    mean_gate = [sum(g[e] for g in gates) / n for e in range(num_experts)]
    return num_experts * sum(frac[e] * mean_gate[e] for e in range(num_experts))


def capacity(n, num_experts, factor):
    """Per-expert capacity = factor * tokens / experts (tokens beyond it overflow)."""
    return math.ceil(factor * n / num_experts)


def apply_capacity(routes, num_experts, cap):
    """Keep up to `cap` tokens per expert in arrival order; count the rest as dropped."""
    kept = [0] * num_experts
    dropped = 0
    for e in routes:
        if kept[e] < cap:
            kept[e] += 1
        else:
            dropped += 1
    return kept, dropped


# ----------------------------------------------------------------- printing

def route_view(data):
    gates, E, f = data["gates"], data["num_experts"], data["capacity_factor"]
    routes = top1_route(gates)
    ld = loads(routes, E)
    cap = capacity(len(gates), E, f)
    kept, dropped = apply_capacity(routes, E, cap)
    print("ROUTE — top-1 expert load (%d tokens, %d experts)" % (len(gates), E))
    print("-" * 56)
    print("  expert   tokens routed   after capacity %d" % cap)
    for e in range(E):
        tag = "  <- DEAD (no tokens)" if ld[e] == 0 else ("  <- overflow" if ld[e] > cap else "")
        print("  %-6d   %-13d   %d%s" % (e, ld[e], kept[e], tag))
    print("-" * 56)
    print("  expert 0 hogs the load; expert 3 is dead; %d tokens dropped to capacity." % dropped)


def balance_view(data):
    gates, E = data["gates"], data["num_experts"]
    routes = top1_route(gates)
    print("BALANCE — the load-balancing auxiliary loss (1.0 = perfectly balanced)")
    print("-" * 58)
    print("  fraction routed per expert:  %s" % [round(routes.count(e) / len(gates), 3) for e in range(E)])
    print("  mean gate per expert:        %s" % [round(sum(g[e] for g in gates) / len(gates), 3) for e in range(E)])
    print("  load-balancing loss:         %.3f   (balanced minimum = 1.000)" % balance_loss(gates, routes, E))
    print("-" * 58)
    print("  the loss exceeds 1.0 because load and gate mass both concentrate on expert 0.")


def check(data):
    print("SELF-TEST — the load is imbalanced with a dead expert; the aux loss exceeds 1.0; capacity caps load and drops overflow")
    print("-" * 118)
    gates, E, f = data["gates"], data["num_experts"], data["capacity_factor"]
    routes = top1_route(gates)
    ld = loads(routes, E)
    cap = capacity(len(gates), E, f)
    kept, dropped = apply_capacity(routes, E, cap)

    imbalanced = max(ld) >= 3 * (min(ld) + 1)
    print("  the load is imbalanced (max %d vs min %d) = %s" % (max(ld), min(ld), imbalanced))

    has_dead_expert = min(ld) == 0
    print("  at least one expert is dead (gets no tokens) = %s (expert %d)" % (has_dead_expert, ld.index(0)))

    loss = balance_loss(gates, routes, E)
    loss_above_balanced = loss > 1.0
    print("  the load-balancing loss exceeds the balanced 1.0 = %s (%.3f)" % (loss_above_balanced, loss))

    capacity_caps = all(k <= cap for k in kept)
    print("  capacity caps every expert's kept tokens at %d = %s (kept %s)" % (cap, capacity_caps, kept))

    overflow_dropped = dropped == max(0, max(ld) - cap)
    print("  the overflow beyond capacity is dropped = %s (%d dropped)" % (overflow_dropped, dropped))

    ok = imbalanced and has_dead_expert and loss_above_balanced and capacity_caps and overflow_dropped
    print("-" * 118)
    print("SELF-TEST %s  imbalanced=%s  has_dead_expert=%s  loss_above_balanced=%s  capacity_caps=%s  overflow_dropped=%s"
          % ("PASS" if ok else "FAIL", imbalanced, has_dead_expert, loss_above_balanced, capacity_caps, overflow_dropped))
    return ok


def main():
    p = argparse.ArgumentParser(description="Mixture-of-Experts routing: top-1 routing collapses load onto a few experts (a dead-expert failure), which a load-balancing auxiliary loss discourages and an expert capacity hard-caps by dropping overflow.")
    p.add_argument("--route", action="store_true")
    p.add_argument("--balance", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tokens=%d  num_experts=%d  capacity_factor=%.1f  file=%s  (the router gates are a fixture)"
          % (len(data["gates"]), data["num_experts"], data["capacity_factor"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.route:
        route_view(data)
    elif args.balance:
        balance_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
