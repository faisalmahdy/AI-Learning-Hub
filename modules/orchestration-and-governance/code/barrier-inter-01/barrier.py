"""A reusable barrier needs a generation number, not a boolean 'released' flag -- a 'count arrivals and reset' barrier synchronizes correctly the first time and silently breaks on every reuse, because the reset zeroes the count but leaves the released flag set, so at the next phase the first worker to arrive rides the stale flag and passes through before the others arrive.

A barrier's contract is simple: N workers each reach it at the end of a phase, and none may cross until all N have arrived, so that phase 2 can safely assume all of phase 1's output exists. The naive implementation keeps a count and a released flag. Each arrival increments the count; the arrival that brings the count to N flips released to true and resets the count to zero so the barrier can be used again for the next phase.

That reset is the bug. It zeroes the count but not the flag. When the next phase begins the flag is still true, so the very first worker to arrive is told to proceed -- the barrier is open when one of N has arrived, not N. The workers desynchronize with no error, and any invariant the next phase depended on is quietly violated. The barrier worked once and is now a no-op.

The fix is to make each use a distinct episode. Replace the boolean with a generation number: each time the count reaches N, advance the generation and reset the count. A worker records the generation it arrived under and proceeds only once the generation has moved past it -- which happens exactly when the N-th worker of its own generation arrives. A worker that loops back into the next phase arrives under the new generation and cannot be released by the previous one's advance, so every phase synchronizes on its own N.

On this fixture N is 3 and the barrier is used for two phases of three workers. For each barrier the code reports the arrival count at which the barrier first opens in each phase; a correct barrier opens only at 3. The naive barrier opens at 3 in phase 1 and at 1 in phase 2 -- broken on reuse -- while the generation barrier opens at 3 in both.

  --naive       the count-and-flag barrier: opens at N the first time, at 1 on reuse (a worker proceeds alone)
  --generation  the generation-number barrier: opens at N in every phase
  --check       the naive barrier opens correctly in phase 1 but early on reuse, while the generation barrier opens at N in every phase

n and the two-phase arrival schedule are the fixture; the arrival count at which each barrier first opens per phase is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "barrier.json"


class NaiveBarrier:
    """Count arrivals; the N-th sets released and resets the count -- but never clears released."""
    def __init__(self, n):
        self.n = n
        self.count = 0
        self.released = False

    def arrive(self):
        self.count += 1
        if self.count == self.n:
            self.released = True
            self.count = 0
        return self.released  # True = this worker may proceed now


class GenerationBarrier:
    """Count arrivals; the N-th advances the generation -- each phase is a fresh episode."""
    def __init__(self, n):
        self.n = n
        self.count = 0
        self.generation = 0

    def arrive(self):
        my_gen = self.generation
        self.count += 1
        if self.count == self.n:
            self.generation += 1
            self.count = 0
            return True  # the N-th arrival opens the barrier for this generation
        return self.generation != my_gen  # a waiter proceeds only once its generation is superseded


def opens_at(barrier, phase):
    """The 1-based arrival index at which the barrier first lets a worker proceed in this phase."""
    for i, _worker in enumerate(phase, start=1):
        if barrier.arrive():
            return i
    return None  # never opened


def run(barrier_cls, data):
    """Run each phase through a fresh-but-reused barrier and record where it opened."""
    barrier = barrier_cls(data["n"])
    return [opens_at(barrier, phase) for phase in data["phases"]]


# ----------------------------------------------------------------- printing

def _report(name, opens, n):
    print("%s — arrival count at which the barrier opens, per phase (correct = %d)" % (name, n))
    print("-" * 64)
    for p, o in enumerate(opens):
        flag = "" if o == n else "   <- OPENED EARLY (a worker proceeded before the rest)"
        print("  phase %d: opens at arrival %s of %d%s" % (p, o, n, flag))
    print("-" * 64)


def naive_view(data):
    opens = run(NaiveBarrier, data)
    _report("NAIVE", opens, data["n"])
    print("  the reset zeroed the count but left released=True, so phase 2 opens on the first arrival")


def generation_view(data):
    opens = run(GenerationBarrier, data)
    _report("GENERATION", opens, data["n"])
    print("  each phase runs under its own generation, so the barrier opens only at N every time")


def check(data):
    print("SELF-TEST — the naive barrier opens correctly in phase 1 but early on reuse, while the generation barrier opens at N in every phase")
    print("-" * 112)
    n = data["n"]
    naive = run(NaiveBarrier, data)
    gen = run(GenerationBarrier, data)

    naive_first_use_ok = naive[0] == n
    print("  naive barrier opens at N on first use = %s (opened at %s)" % (naive_first_use_ok, naive[0]))

    naive_reuse_broken = naive[1] < n
    print("  naive barrier opens EARLY on reuse = %s (opened at %s, before all %d arrived)" % (naive_reuse_broken, naive[1], n))

    gen_every_phase_ok = all(o == n for o in gen)
    print("  generation barrier opens at N in every phase = %s (opened at %s)" % (gen_every_phase_ok, gen))

    gen_reusable = len(data["phases"]) > 1 and gen_every_phase_ok
    print("  generation barrier is safely reusable across phases = %s" % gen_reusable)

    ok = (naive_first_use_ok and naive_reuse_broken and gen_every_phase_ok and gen_reusable)
    print("-" * 112)
    print("SELF-TEST %s  naive_first_use_ok=%s  naive_reuse_broken=%s  gen_every_phase_ok=%s  gen_reusable=%s"
          % ("PASS" if ok else "FAIL", naive_first_use_ok, naive_reuse_broken, gen_every_phase_ok, gen_reusable))
    return ok


def main():
    p = argparse.ArgumentParser(description="Reusable barrier: synchronize N workers per phase with a generation number, not a boolean released flag, because a count-and-reset barrier leaves the flag set after the first phase, so on reuse the first worker to arrive rides the stale flag and proceeds before the others -- the barrier opens at 1 of N instead of N; a generation number makes each phase a fresh episode so the barrier opens only at N every time.")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--generation", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("n=%d  phases=%d  file=%s" % (data["n"], len(data["phases"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.naive:
        naive_view(data)
    elif args.generation:
        generation_view(data)
    else:
        p.print_help()
        return 2
    return 0


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


if __name__ == "__main__":
    sys.exit(main())
