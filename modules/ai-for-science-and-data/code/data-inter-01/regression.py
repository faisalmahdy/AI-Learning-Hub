#!/usr/bin/env python3
"""Regression to the mean: the intervention that 'worked' because you picked the worst.

Measure a population twice with no intervention at all, select the worst performers
on the first measurement, and their second measurement improves -- on average,
guaranteed -- because a low first score is partly real and partly bad luck, and the
luck does not repeat. Select the best and they decline. An analyst who coaches the
bottom group and re-measures will see a real-looking improvement that is entirely
this artifact. The only way to tell a true effect from regression to the mean is a
control group selected the same way but left alone. This simulates it and measures
the trap.

  --population    the two measurements, and the overall (unchanged) mean
  --select        the bottom and top groups: their first vs second measurement
  --control       treated vs untreated bottom groups -- the improvement is identical
  --check         the bottom 'improves' and the top 'declines' with zero real effect

Seeded RNG (stdlib random), so the whole thing is deterministic and offline. No
real intervention is applied anywhere -- every change you see is the artifact.
"""
import argparse
import random
import sys

SEED = 0
N = 200            # population size
K = 40             # how many extremes to select
TRUE_MEAN = 50.0
TRUE_SD = 10.0     # spread of real skill
NOISE_SD = 10.0    # measurement noise per observation


def population():
    """Each unit has a fixed true skill; each MEASUREMENT is skill plus fresh noise.
    Two measurements, no intervention between them."""
    rng = random.Random(SEED)
    units = []
    for _ in range(N):
        true = rng.gauss(TRUE_MEAN, TRUE_SD)
        m1 = true + rng.gauss(0, NOISE_SD)
        m2 = true + rng.gauss(0, NOISE_SD)          # independent noise, same skill
        units.append((m1, m2))
    return units


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def bottom_k(units, k):
    return sorted(units, key=lambda u: u[0])[:k]     # worst on the FIRST measurement


def top_k(units, k):
    return sorted(units, key=lambda u: u[0])[-k:]    # best on the FIRST measurement


# ----------------------------------------------------------------- the "effect"

def apparent_effect(group):
    """The change from first to second measurement -- what an analyst would call the
    treatment effect if they had 'treated' this group between the two."""
    return mean([m2 for _, m2 in group]) - mean([m1 for m1, _ in group])


# ------------------------------------------------------------------- printing

def population_view(units):
    print("POPULATION — two measurements, no intervention   (n=%d)" % N)
    print("-" * 62)
    print("  overall mean, measurement 1 = %.2f" % mean([m1 for m1, _ in units]))
    print("  overall mean, measurement 2 = %.2f" % mean([m2 for _, m2 in units]))
    print("-" * 62)
    print("  the population as a whole does not move -- nothing was done to it.")


def select_view(units):
    b, t = bottom_k(units, K), top_k(units, K)
    print("SELECTED GROUPS — the extremes on measurement 1, re-measured   (k=%d)" % K)
    print("-" * 62)
    print("  bottom %d:  m1 mean %.2f -> m2 mean %.2f   change %+.2f" %
          (K, mean([m1 for m1, _ in b]), mean([m2 for _, m2 in b]), apparent_effect(b)))
    print("  top %d:     m1 mean %.2f -> m2 mean %.2f   change %+.2f" %
          (K, mean([m1 for m1, _ in t]), mean([m2 for _, m2 in t]), apparent_effect(t)))
    print("-" * 62)
    print("  the bottom rose and the top fell, toward the mean, with no intervention.")
    print("  select on a noisy score and the luck that made it extreme does not repeat.")


def control_view(units):
    """Split the bottom group in two: 'treat' one half (do nothing, since there is no
    real treatment here) and leave the other as control. Both improve identically."""
    b = bottom_k(units, K)
    treated, control = b[::2], b[1::2]
    print("TREATED vs CONTROL — both halves of the bottom group, one 'coached'")
    print("-" * 62)
    print("  treated bottom half:  change %+.2f" % apparent_effect(treated))
    print("  control bottom half:  change %+.2f" % apparent_effect(control))
    print("-" * 62)
    print("  the control improves as much as the treated -- so the improvement is not")
    print("  the coaching, it is regression to the mean. The control is what reveals it.")


def check(units):
    print("SELF-TEST — bottom rises, top falls, population flat: zero real effect")
    print("-" * 62)
    b, t = bottom_k(units, K), top_k(units, K)
    eff_b, eff_t = apparent_effect(b), apparent_effect(t)
    print("  bottom-group apparent effect = %+.2f   top-group = %+.2f" % (eff_b, eff_t))

    bottom_rises = eff_b > 0
    top_falls = eff_t < 0
    print("  the selected-worst group 'improves' = %s" % bottom_rises)
    print("  the selected-best group 'declines' = %s" % top_falls)

    m1_all = mean([m1 for m1, _ in units])
    m2_all = mean([m2 for _, m2 in units])
    population_flat = abs(m1_all - m2_all) < 3.0      # small vs the +8.9 / -12.6 group moves
    print("  the whole population barely moves = %s (%.2f -> %.2f)" % (population_flat, m1_all, m2_all))

    # a control selected the same way improves as much as the 'treated' half.
    treated, control = b[::2], b[1::2]
    control_matches = abs(apparent_effect(treated) - apparent_effect(control)) < 3.0
    print("  a control group improves as much as the treated = %s (%.2f vs %.2f)"
          % (control_matches, apparent_effect(treated), apparent_effect(control)))

    det = population() == units
    ok = bottom_rises and top_falls and population_flat and control_matches and det
    print("-" * 62)
    print("SELF-TEST %s  bottom_up=%s  top_down=%s  pop_flat=%s  control_matches=%s"
          % ("PASS" if ok else "FAIL", bottom_rises, top_falls, population_flat, control_matches))
    return ok


def main():
    p = argparse.ArgumentParser(description="Regression to the mean, and why you need a control.")
    p.add_argument("--population", action="store_true")
    p.add_argument("--select", action="store_true")
    p.add_argument("--control", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    units = population()
    print("n=%d  k=%d  seed=%d  noise_sd=%.0f  (a simulated population, deterministic)"
          % (N, K, SEED, NOISE_SD))
    print("")

    if args.check:
        return 0 if check(units) else 1
    if args.population:
        population_view(units)
    elif args.select:
        select_view(units)
    elif args.control:
        control_view(units)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
