"""Seed the random generator, or the learner can never reproduce your documented output.

A teaching artifact that uses randomness -- a simulation, a sampled quiz, a shuffled deck -- prints some
numbers, and the lesson documents them: 'you should see a sum of 21.' But if the generator is left
unseeded, it draws its starting state from the wall clock or system entropy, so every run produces a
DIFFERENT sequence. The learner runs it, gets 17, and has no idea whether they made a mistake or the output
is just supposed to vary. Reproducibility is broken: the documented number is unreachable, and 'measure or
it didn't happen' becomes 'measure and get something else every time.'

Seeding fixes it. A pseudo-random generator is a deterministic function of its seed: give it the same seed
and it produces the exact same sequence, run after run, machine after machine. Set the seed to a fixed
value at the start and the artifact becomes reproducible -- the learner runs it and gets your documented
21, every time, so they can check their work against a known answer. The randomness is still
'random-looking' (good enough for sampling and shuffling); it is simply anchored, so the whole run is a
pure function of the seed.

On this fixture a task rolls five dice and sums them, using a small deterministic generator. Left unseeded
(modeled as seeding from a varying clock), two runs give sums of 17 and 23 -- different, unreproducible.
Seeded with a fixed 42, two runs both give 20, matching the documented output. This computes both.

  --rolls      the five rolls and their sum, unseeded (two clocks) vs seeded (fixed 42)
  --reproduce  whether each mode reproduces the documented output across two runs
  --check      the unseeded runs disagree and miss the documented value; the seeded runs match it exactly

The seed values and documented output are the fixture; every roll is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "task.json"

# A small linear congruential generator (glibc constants) -- a deterministic function of its seed.
A, C, M = 1103515245, 12345, 1 << 31


def rolls(seed, n):
    """n dice rolls (1..6) from the LCG started at `seed` -- identical whenever the seed is identical."""
    out, x = [], seed
    for _ in range(n):
        x = (A * x + C) % M
        out.append(x % 6 + 1)
    return out


def total(seed, n):
    return sum(rolls(seed, n))


# ----------------------------------------------------------------- printing

def rolls_view(data):
    n = data["n_dice"]
    fixed = data["fixed_seed"]
    c1, c2 = data["clock_seeds"]
    print("ROLLS — five dice and their sum, unseeded (two clocks) vs seeded (fixed %d)" % fixed)
    print("-" * 58)
    print("  unseeded run 1 (clock %d): %s  sum %d" % (c1, rolls(c1, n), total(c1, n)))
    print("  unseeded run 2 (clock %d): %s  sum %d" % (c2, rolls(c2, n), total(c2, n)))
    print("  seeded   run 1 (seed  %d):   %s  sum %d" % (fixed, rolls(fixed, n), total(fixed, n)))
    print("  seeded   run 2 (seed  %d):   %s  sum %d" % (fixed, rolls(fixed, n), total(fixed, n)))
    print("-" * 58)
    print("  same seed -> same rolls; a varying seed -> different rolls.")


def reproduce_view(data):
    n, fixed, doc = data["n_dice"], data["fixed_seed"], data["documented_sum"]
    c1, c2 = data["clock_seeds"]
    print("REPRODUCE — does each mode match the documented sum of %d?" % doc)
    print("-" * 58)
    print("  unseeded: runs give %d and %d   -> match documented? %s"
          % (total(c1, n), total(c2, n), total(c1, n) == doc and total(c2, n) == doc))
    print("  seeded:   runs give %d and %d   -> match documented? %s"
          % (total(fixed, n), total(fixed, n), total(fixed, n) == doc))
    print("-" * 58)
    print("  only the seeded run reproduces the documented output.")


def check(data):
    print("SELF-TEST — the unseeded runs disagree and miss the documented value; the seeded runs match it exactly")
    print("-" * 96)
    n, fixed, doc = data["n_dice"], data["fixed_seed"], data["documented_sum"]
    c1, c2 = data["clock_seeds"]

    unseeded_differs = total(c1, n) != total(c2, n)
    print("  two unseeded runs give different sums = %s (%d vs %d)" % (unseeded_differs, total(c1, n), total(c2, n)))

    unseeded_misses_doc = total(c1, n) != doc or total(c2, n) != doc
    print("  the unseeded runs do not match the documented sum = %s (doc %d)" % (unseeded_misses_doc, doc))

    seeded_matches_itself = rolls(fixed, n) == rolls(fixed, n)
    print("  two seeded runs are byte-for-byte identical = %s" % seeded_matches_itself)

    seeded_matches_doc = total(fixed, n) == doc
    print("  the seeded run matches the documented sum = %s (%d)" % (seeded_matches_doc, total(fixed, n)))

    same_seed_same_sequence = rolls(fixed, n) == rolls(fixed, n) and rolls(c1, n) != rolls(c2, n)
    print("  the sequence is a pure function of the seed = %s" % same_seed_same_sequence)

    ok = unseeded_differs and unseeded_misses_doc and seeded_matches_itself and seeded_matches_doc and same_seed_same_sequence
    print("-" * 96)
    print("SELF-TEST %s  unseeded_differs=%s  unseeded_misses_doc=%s  seeded_matches_itself=%s  seeded_matches_doc=%s  pure_function_of_seed=%s"
          % ("PASS" if ok else "FAIL", unseeded_differs, unseeded_misses_doc, seeded_matches_itself, seeded_matches_doc, same_seed_same_sequence))
    return ok


def main():
    p = argparse.ArgumentParser(description="Seed the generator so a teaching artifact reproduces its documented output.")
    p.add_argument("--rolls", action="store_true")
    p.add_argument("--reproduce", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = json.loads((HERE / "task.json").read_text(encoding="utf-8"))
    print("n_dice=%d  fixed_seed=%d  documented_sum=%d  file=task.json  (the seeds and output are a fixture)"
          % (data["n_dice"], data["fixed_seed"], data["documented_sum"]))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rolls:
        rolls_view(data)
    elif args.reproduce:
        reproduce_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
