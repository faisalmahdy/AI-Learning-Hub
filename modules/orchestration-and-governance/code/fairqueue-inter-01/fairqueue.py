"""Schedule a shared server with fair queuing -- one queue per tenant, served round-robin -- not one shared FIFO, because a FIFO serves in arrival order, so a tenant that floods the queue with a burst monopolizes the capacity and starves everyone behind it.

A single FIFO queue has exactly one notion of fairness: first come, first served. That sounds fair and is not, when the server is shared across tenants, because it ties a tenant's share of the service to how many requests it submitted. A tenant that sends a burst of many requests lands them all at the front, gets served in bulk, and pushes every other tenant's requests back -- and if the server's capacity is exhausted before those are reached, they are not just delayed, they are starved. One heavy user degrades or shuts out all the others on the shared resource. This is the noisy-neighbor problem, and FIFO has no defense against it.

Fair queuing breaks the link between how much you submit and how much you are served. Keep a separate queue per tenant and serve them round-robin: one request from each tenant's queue per cycle, skipping any that are empty. Now each active tenant gets an equal share of the capacity regardless of how many requests it enqueued -- a burst from one tenant piles up in that tenant's own queue and cannot crowd out the others, because the scheduler only ever takes one of its requests per round before moving on.

The result is that capacity is divided by tenant, not by volume. A tenant that submitted one request and a tenant that submitted a thousand both get a turn each round, so the light tenants are served promptly and the heavy tenant is served at its fair rate rather than all at once. Weighted fair queuing generalizes this by giving some tenants more turns per cycle, but the core is the round-robin that makes the share independent of the burst.

On this fixture tenant A sends a burst of 6 requests that all arrive before B's 2 and C's 1. A FIFO server with capacity 6 serves all 6 of A's and starves B and C completely; fair queuing serves 3 of A's, both of B's, and C's one -- every tenant served. This computes both.

  --fifo    the per-tenant service under one shared FIFO queue, and who is starved
  --fair    the per-tenant service under fair (round-robin) queuing
  --check   FIFO lets the flooding tenant monopolize and starves the others; fair queuing serves every tenant and caps the greedy one

capacity and the arrival sequence are the fixture; the per-tenant service under each scheme and the starved tenants are computed. Stdlib only.
"""
import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "fairqueue.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def pending(arrivals):
    """Requests waiting, per tenant, in first-appearance order."""
    counts = OrderedDict()
    for t in arrivals:
        counts[t] = counts.get(t, 0) + 1
    return counts


def fifo_serve(arrivals, capacity):
    """One shared FIFO: serve the first `capacity` arrivals in order."""
    served = OrderedDict((t, 0) for t in pending(arrivals))
    for t in arrivals[:capacity]:
        served[t] += 1
    return served


def fair_serve(arrivals, capacity):
    """Fair queuing: one queue per tenant, served round-robin one each per cycle."""
    remaining = pending(arrivals)
    served = OrderedDict((t, 0) for t in remaining)
    total = 0
    while total < capacity and any(remaining[t] > 0 for t in remaining):
        for t in remaining:
            if remaining[t] > 0 and total < capacity:
                served[t] += 1
                remaining[t] -= 1
                total += 1
    return served


def starved(served):
    """Tenants that had requests but received no service."""
    return [t for t, n in served.items() if n == 0]


# ----------------------------------------------------------------- printing

def fifo_view(data):
    arrivals, cap = data["arrivals"], data["capacity"]
    s = fifo_serve(arrivals, cap)
    print("FIFO — one shared queue, capacity %d, served in arrival order" % cap)
    print("-" * 52)
    print("  pending  : %s" % dict(pending(arrivals)))
    print("  served   : %s" % dict(s))
    print("  starved  : %s" % starved(s))
    print("-" * 52)
    print("  the flooding tenant takes the capacity; the rest are starved")


def fair_view(data):
    arrivals, cap = data["arrivals"], data["capacity"]
    s = fair_serve(arrivals, cap)
    print("FAIR — one queue per tenant, capacity %d, served round-robin" % cap)
    print("-" * 52)
    print("  pending  : %s" % dict(pending(arrivals)))
    print("  served   : %s" % dict(s))
    print("  starved  : %s" % starved(s))
    print("-" * 52)
    print("  every tenant gets a turn each cycle; the burst fills only its own queue")


def check(data):
    print("SELF-TEST — FIFO lets the flooding tenant monopolize and starves the others; fair queuing serves every tenant and guarantees each its floor share")
    print("-" * 112)
    arrivals, cap = data["arrivals"], data["capacity"]
    n_tenants = len(pending(arrivals))

    fifo = fifo_serve(arrivals, cap)
    fair = fair_serve(arrivals, cap)

    fifo_max = max(fifo.values())
    fair_max = max(fair.values())

    fifo_lets_one_dominate = fifo_max > fair_max
    print("  FIFO's top tenant takes more than fair's does = %s (%d > %d)" % (fifo_lets_one_dominate, fifo_max, fair_max))

    fifo_starves_someone = len(starved(fifo)) > 0
    print("  FIFO starves at least one tenant that had requests = %s (%s)" % (fifo_starves_someone, starved(fifo)))

    fair_serves_everyone = len(starved(fair)) == 0
    print("  fair queuing serves every tenant that had requests = %s" % fair_serves_everyone)

    pend = pending(arrivals)
    floor_share = cap // n_tenants
    fair_guarantees_floor_share = all(fair[t] >= min(pend[t], floor_share) for t in fair)
    print("  fair queuing guarantees each tenant its floor share (max-min) = %s (floor %d)" % (fair_guarantees_floor_share, floor_share))

    same_total_served = sum(fifo.values()) == sum(fair.values()) == cap
    print("  both schemes serve the same total = %s (%d)" % (same_total_served, sum(fair.values())))

    ok = (fifo_lets_one_dominate and fifo_starves_someone and fair_serves_everyone
          and fair_guarantees_floor_share and same_total_served)
    print("-" * 112)
    print("SELF-TEST %s  fifo_lets_one_dominate=%s  fifo_starves_someone=%s  fair_serves_everyone=%s  fair_guarantees_floor_share=%s  same_total_served=%s"
          % ("PASS" if ok else "FAIL", fifo_lets_one_dominate, fifo_starves_someone, fair_serves_everyone,
             fair_guarantees_floor_share, same_total_served))
    return ok


def main():
    p = argparse.ArgumentParser(description="Fair queuing: schedule a shared server with one queue per tenant served round-robin, not one shared FIFO, because FIFO serves in arrival order so a tenant that floods the queue monopolizes the capacity and starves everyone behind it.")
    p.add_argument("--fifo", action="store_true")
    p.add_argument("--fair", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("capacity=%d  arrivals=%s  file=%s  (these are a fixture)" % (data["capacity"], data["arrivals"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.fifo:
        fifo_view(data)
    elif args.fair:
        fair_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
