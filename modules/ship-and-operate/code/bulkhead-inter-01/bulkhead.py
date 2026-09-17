"""Partition the pool per dependency -- one shared pool lets a slow dependency's saturation starve a healthy one.

A service that calls several downstream dependencies usually draws its concurrency -- threads, connections, in-flight
slots -- from ONE shared pool. That is efficient when everything is healthy: whichever dependency is busy gets the slots.
It becomes a fault-propagation path the moment one dependency goes slow. If dependency A starts taking 10x longer, each
in-flight call to A holds its slot 10x longer, so a burst of A calls can occupy every slot in the shared pool at once.
Now a call to dependency B -- which is perfectly healthy and would return in a millisecond -- arrives and finds no free
slot, so it is rejected or queued behind A's slow calls. A single sick dependency has taken down an unrelated one, and
from B's users' point of view the whole service is broken. The shared pool did nothing wrong; sharing is what let A's
failure leak into B.

A bulkhead fixes this by PARTITIONING the pool: each dependency (or class of work) gets its own capped share of the
slots, so a dependency can only ever exhaust its OWN partition. The name is from ships -- a hull is divided into
watertight compartments so a breach in one does not flood the whole vessel. Give A a cap of 2 slots and B a cap of 2, and
when A saturates, it fills its 2 slots and its further calls are rejected, but B's 2 slots are untouched, so B keeps
serving. The trade-off is deliberate: bulkheading caps each dependency below the full pool, so under normal load a single
dependency can no longer burst up to the whole pool -- you trade some peak throughput for the guarantee that one
dependency's failure is contained. That containment is the point: isolation over utilization.

The rule: draw concurrency for independent dependencies from separate, capped partitions, not one shared pool, so a slow
or failing dependency exhausts only its own bulkhead and cannot starve the healthy ones -- the same isolation a circuit
breaker gives in time (stop calling a broken dependency), a bulkhead gives in space (cap the resources it can hold).

On this fixture four slow A calls (service 10) arrive at once, then three healthy B calls (service 1) arrive one per tick.
The shared pool has 4 slots; the bulkhead gives A and B 2 each. With the shared pool, A's four calls take all 4 slots for
10 ticks and every B call is rejected -- B served 0 of 3. With the bulkhead, A fills its 2 slots (2 A calls rejected) but
B's partition is free, so all 3 B calls are served. This computes both.

  --pool    the per-request admit/reject outcome and the served/rejected counts per dependency, shared pool vs bulkhead
  --trace   the shared-pool run tick by tick: slots in use and why each B call is rejected while A holds the pool
  --check   the shared pool starves healthy B (0 served); the bulkhead protects it (all served) by capping A's slots

The requests, pool size, and caps are the fixture; every admit/reject decision is computed by the simulation. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "bulkhead.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def simulate(requests, total_slots, caps=None):
    """Admit each request if a slot is free (shared pool: caps=None) or its dependency's partition has room (bulkhead).

    A slot is held from the arrival tick until arrival+service, then freed. Returns the per-request outcomes.
    """
    reqs = sorted(requests, key=lambda r: (r["arrival"], r["id"]))
    in_flight = []  # (dep, release_tick) for each held slot
    outcomes = []
    last_arrival = max(r["arrival"] for r in reqs)
    for tick in range(0, last_arrival + 1):
        in_flight = [(d, rel) for (d, rel) in in_flight if rel > tick]  # free completed slots
        for r in reqs:
            if r["arrival"] != tick:
                continue
            dep = r["dep"]
            if caps is None:
                admit = len(in_flight) < total_slots
            else:
                used_dep = sum(1 for (d, rel) in in_flight if d == dep)
                admit = used_dep < caps[dep]
            if admit:
                in_flight.append((dep, tick + r["service"]))
                outcomes.append({"id": r["id"], "dep": dep, "result": "admit"})
            else:
                outcomes.append({"id": r["id"], "dep": dep, "result": "REJECT"})
    return outcomes


def counts(outcomes, dep, result):
    return sum(1 for o in outcomes if o["dep"] == dep and o["result"] == result)


# ----------------------------------------------------------------- printing

def pool_view(data):
    reqs = data["requests"]
    shared = simulate(reqs, data["total_slots"])
    bulk = simulate(reqs, data["total_slots"], data["bulkhead_caps"])
    print("POOL — 4 slow A calls (service 10) then 3 healthy B calls (service 1); pool=%d, bulkhead caps=%s"
          % (data["total_slots"], data["bulkhead_caps"]))
    print("-" * 74)
    print("  id  dep  arrival  shared-pool   bulkhead")
    by_id = {o["id"]: o for o in shared}
    bk_id = {o["id"]: o for o in bulk}
    for r in sorted(reqs, key=lambda r: r["id"]):
        print("  %-3d %-4s %-8d %-13s %s" % (r["id"], r["dep"], r["arrival"], by_id[r["id"]]["result"], bk_id[r["id"]]["result"]))
    print("-" * 74)
    print("  SHARED POOL: A served %d/%d, B served %d/%d  <- healthy B starved by A"
          % (counts(shared, "A", "admit"), counts(shared, "A", "admit") + counts(shared, "A", "REJECT"),
             counts(shared, "B", "admit"), counts(shared, "B", "admit") + counts(shared, "B", "REJECT")))
    print("  BULKHEAD:    A served %d/%d, B served %d/%d  <- A capped, B fully protected"
          % (counts(bulk, "A", "admit"), counts(bulk, "A", "admit") + counts(bulk, "A", "REJECT"),
             counts(bulk, "B", "admit"), counts(bulk, "B", "admit") + counts(bulk, "B", "REJECT")))


def trace_view(data):
    reqs = sorted(data["requests"], key=lambda r: (r["arrival"], r["id"]))
    total_slots = data["total_slots"]
    in_flight = []
    print("TRACE — shared pool of %d slots, tick by tick" % total_slots)
    print("-" * 66)
    print("  tick  free-before  arrivals   decision")
    for tick in range(0, max(r["arrival"] for r in reqs) + 1):
        in_flight = [(d, rel) for (d, rel) in in_flight if rel > tick]
        free = total_slots - len(in_flight)
        arrivals = [r for r in reqs if r["arrival"] == tick]
        parts = []
        for r in arrivals:
            if len(in_flight) < total_slots:
                in_flight.append((r["dep"], tick + r["service"]))
                parts.append("%s#%d admit" % (r["dep"], r["id"]))
            else:
                parts.append("%s#%d REJECT (pool full)" % (r["dep"], r["id"]))
        print("  %-5d %-12d %-10s %s" % (tick, free, "%d call(s)" % len(arrivals) if arrivals else "-", "; ".join(parts) if parts else "-"))
    print("-" * 66)
    print("  the 4 A calls hold all 4 slots for 10 ticks, so every B call finds a full pool.")


def check(data):
    print("SELF-TEST — the shared pool lets slow A starve healthy B; the bulkhead caps A and keeps B serving")
    print("-" * 96)
    reqs = data["requests"]
    shared = simulate(reqs, data["total_slots"])
    bulk = simulate(reqs, data["total_slots"], data["bulkhead_caps"])

    b_total = counts(shared, "B", "admit") + counts(shared, "B", "REJECT")

    shared_starves_b = counts(shared, "B", "admit") == 0
    print("  shared pool: healthy B calls served = %d of %d -> starved = %s"
          % (counts(shared, "B", "admit"), b_total, shared_starves_b))

    bulkhead_protects_b = counts(bulk, "B", "admit") == b_total and counts(bulk, "B", "REJECT") == 0
    print("  bulkhead: healthy B calls served = %d of %d -> fully protected = %s"
          % (counts(bulk, "B", "admit"), b_total, bulkhead_protects_b))

    bulkhead_caps_a = counts(bulk, "A", "admit") < counts(shared, "A", "admit")
    print("  bulkhead caps A below the whole pool = %s (A served %d vs %d shared)"
          % (bulkhead_caps_a, counts(bulk, "A", "admit"), counts(shared, "A", "admit")))

    a_confined_to_partition = counts(bulk, "A", "admit") == data["bulkhead_caps"]["A"]
    print("  A can hold at most its own partition = %s (%d slots)"
          % (a_confined_to_partition, data["bulkhead_caps"]["A"]))

    outcomes_differ = counts(shared, "B", "admit") != counts(bulk, "B", "admit")
    print("  bulkhead changes B's fate (isolation worked) = %s (%d vs %d served)"
          % (outcomes_differ, counts(shared, "B", "admit"), counts(bulk, "B", "admit")))

    ok = shared_starves_b and bulkhead_protects_b and bulkhead_caps_a and a_confined_to_partition and outcomes_differ
    print("-" * 96)
    print("SELF-TEST %s  shared_starves_b=%s  bulkhead_protects_b=%s  bulkhead_caps_a=%s  a_confined_to_partition=%s  outcomes_differ=%s"
          % ("PASS" if ok else "FAIL", shared_starves_b, bulkhead_protects_b, bulkhead_caps_a, a_confined_to_partition, outcomes_differ))
    return ok


def main():
    p = argparse.ArgumentParser(description="Bulkhead isolation: drawing concurrency for independent dependencies from one shared pool lets a slow dependency's saturation starve a healthy one; partitioning the pool into per-dependency capped bulkheads confines each failure to its own share, trading peak throughput for containment.")
    p.add_argument("--pool", action="store_true")
    p.add_argument("--trace", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("total_slots=%d  bulkhead_caps=%s  requests=%d  file=%s  (requests, pool size, and caps are a fixture)"
          % (data["total_slots"], data["bulkhead_caps"], len(data["requests"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.pool:
        pool_view(data)
    elif args.trace:
        trace_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
