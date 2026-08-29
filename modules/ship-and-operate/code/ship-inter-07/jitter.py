#!/usr/bin/env python3
"""Exponential backoff needs jitter -- without it, synchronized retries become a thundering herd.

When a dependency goes down, every client that was mid-request fails at nearly the same moment.
Each one backs off and retries -- and if they all use the same backoff schedule (wait 1, then
2, then 4 seconds), they all retry at the same instants, in lockstep, forever. The moment the
dependency recovers it is hit by the entire fleet at once, knocked flat, and the synchronized
herd re-forms on the next backoff step. Exponential backoff alone does not spread the load; it
just spreads it into synchronized spikes.

Jitter breaks the lockstep. Instead of retrying at exactly base * 2^attempt, each client waits
a random time in [0, base * 2^attempt]. The same average delay, but the retries scatter across
the window instead of stacking on one instant, so the peak number of simultaneous retries drops
from the whole fleet to a handful -- under the server's capacity, so the recovery sticks. This
simulates a fleet retrying against a capacity-limited server, deterministically (seeded), and
measures the one number that decides whether recovery holds: the peak simultaneous retries.

  --no-jitter   fixed exponential backoff: every client retries in lockstep
  --jitter      randomized backoff: the same fleet, retries scattered
  --check       no-jitter peaks at the whole fleet and wastes attempts; jitter stays under capacity

Deterministic: the jitter draws come from a seeded PRNG, so the run reproduces. Stdlib only.
"""
import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "fleet.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the retry simulation

def simulate(cfg, jitter):
    """A fleet retries a downed dependency until served. Server serves `capacity` per time slot.

    Returns (attempts, peak, done_slot, load_by_slot). With jitter, each backoff is a random
    time in [1, base*2^attempt]; without, it is exactly base*2^attempt -- lockstep.
    """
    rng = random.Random(cfg["seed"])
    capacity = cfg["capacity"]
    base = cfg["base"]

    # every client fails at slot 0 (dependency down) and schedules its first retry
    pending = []            # (retry_slot, client_id, attempt)
    for cid in range(cfg["clients"]):
        pending.append((backoff(base, 0, jitter, rng), cid, 0))

    attempts = 0
    load = {}               # slot -> how many retries landed there
    done = 0
    while pending:
        slot = min(p[0] for p in pending)
        due = [p for p in pending if p[0] == slot]
        pending = [p for p in pending if p[0] != slot]
        load[slot] = len(due)
        # the server serves up to `capacity` this slot; the rest fail and back off again
        due.sort(key=lambda p: p[1])
        for i, (_, cid, attempt) in enumerate(due):
            attempts += 1
            if i < capacity:
                done += 1
            else:
                pending.append((slot + backoff(base, attempt + 1, jitter, rng), cid, attempt + 1))
    peak = max(load.values())
    return {"attempts": attempts, "peak": peak, "done_slot": max(load), "load": load, "served": done}


def backoff(base, attempt, jitter, rng):
    """Exponential backoff. Fixed = base*2^attempt; jittered = random in [1, base*2^attempt]."""
    window = base * (2 ** attempt)
    if jitter:
        return rng.randint(1, window)
    return window


# ----------------------------------------------------------------- printing

def view(cfg, jitter, label):
    r = simulate(cfg, jitter)
    print("%s — %d clients, server capacity %d/slot" % (label, cfg["clients"], cfg["capacity"]))
    print("-" * 62)
    print("  retries landing per time slot:")
    for slot in sorted(r["load"]):
        bar = "#" * r["load"][slot]
        over = "  <- OVER CAPACITY" if r["load"][slot] > cfg["capacity"] else ""
        print("    slot %3d: %-14s %d%s" % (slot, bar, r["load"][slot], over))
    print("-" * 62)
    print("  peak simultaneous retries: %d   total attempts: %d   all served by slot %d"
          % (r["peak"], r["attempts"], r["done_slot"]))


def check(data):
    print("SELF-TEST — no-jitter peaks at the whole fleet and wastes attempts; jitter stays low")
    print("-" * 62)
    cfg = data
    noj = simulate(cfg, jitter=False)
    jit = simulate(cfg, jitter=True)

    herd = noj["peak"] == cfg["clients"]
    print("  no-jitter peak equals the whole fleet (a thundering herd) = %s (%d of %d)"
          % (herd, noj["peak"], cfg["clients"]))

    overloads = noj["peak"] > cfg["capacity"]
    print("  no-jitter peak exceeds server capacity = %s (%d > %d)" % (overloads, noj["peak"], cfg["capacity"]))

    jitter_lower = jit["peak"] < noj["peak"]
    print("  jitter cuts the peak = %s (%d vs %d)" % (jitter_lower, jit["peak"], noj["peak"]))

    jitter_within = jit["peak"] <= cfg["capacity"]
    print("  jitter peak stays within capacity = %s (%d <= %d)" % (jitter_within, jit["peak"], cfg["capacity"]))

    fewer_attempts = jit["attempts"] < noj["attempts"]
    print("  jitter wastes fewer attempts = %s (%d vs %d)" % (fewer_attempts, jit["attempts"], noj["attempts"]))

    ok = herd and overloads and jitter_lower and jitter_within and fewer_attempts
    print("-" * 62)
    print("SELF-TEST %s  herd=%s  overloads=%s  jitter_lower=%s  within_cap=%s  fewer_attempts=%s"
          % ("PASS" if ok else "FAIL", herd, overloads, jitter_lower, jitter_within, fewer_attempts))
    return ok


def main():
    p = argparse.ArgumentParser(description="Exponential backoff needs jitter to avoid a thundering herd.")
    p.add_argument("--no-jitter", action="store_true")
    p.add_argument("--jitter", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    cfg = load()
    print("clients=%d  capacity=%d  base=%d  seed=%d  file=%s  (the fleet config is a fixture)"
          % (cfg["clients"], cfg["capacity"], cfg["base"], cfg["seed"], DATA.name))
    print("")

    if args.check:
        return 0 if check(cfg) else 1
    if getattr(args, "no_jitter"):
        view(cfg, jitter=False, label="NO JITTER")
    elif args.jitter:
        view(cfg, jitter=True, label="JITTER")
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
