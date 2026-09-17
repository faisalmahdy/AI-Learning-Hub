#!/usr/bin/env python3
"""Fade the scaffolding as competence grows -- full worked examples HURT an expert.

A worked example is scaffolding: it walks the learner through every step. For a novice it
is essential -- without the steps they flounder. For an expert it is the opposite: the
redundant steps compete with the schema they already have, and processing them costs more
than it teaches. This is the expertise-reversal effect, and it means the right amount of
scaffolding is not a constant -- it depends on the learner, and it must FADE as competence
grows.

The model: a lesson's learning gain is an intrinsic amount plus a scaffolding term that
HELPS in proportion to how much the learner does not yet know and HURTS in proportion to
how much they do. The coefficient of scaffolding flips sign at a reversal competence, above
which more scaffolding lowers the gain. A one-size-fits-all policy -- always full worked
examples -- is optimal for novices and actively harmful for experts. An adaptive policy
that fades scaffolding past the reversal point matches each learner and never underperforms.
This measures the reversal and compares the policies.

  --curve       learning gain vs scaffolding for a novice, a middle learner, and an expert
  --policy      total cohort learning under fixed-full scaffolding vs adaptive fading
  --check       scaffolding helps novices and hurts experts; adaptive beats and dominates fixed

Stdlib only. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "learners.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the model

def learning_gain(c, s, cfg):
    """Gain for competence c at scaffolding s: intrinsic + s*((1-c)*help - c*redundancy)."""
    return cfg["intrinsic"] + s * ((1 - c) * cfg["help"] - c * cfg["redundancy"])


def reversal_point(cfg):
    """The competence where more scaffolding stops helping: help / (help + redundancy)."""
    return cfg["help"] / (cfg["help"] + cfg["redundancy"])


# ------------------------------------------------------------- the two policies

def fixed_full(c, cfg):
    """One-size-fits-all: always full scaffolding (s = 1)."""
    return 1.0


def adaptive(c, cfg):
    """Fade scaffolding past the reversal point: full below it, none above."""
    return 1.0 if c < reversal_point(cfg) else 0.0


def cohort_total(learners, policy, cfg):
    return sum(learning_gain(l["competence"], policy(l["competence"], cfg), cfg) for l in learners)


# ----------------------------------------------------------------- printing

def curve_view(data):
    cfg = data
    print("CURVE — learning gain vs scaffolding (reversal at competence %.2f)" % reversal_point(cfg))
    print("-" * 66)
    print("  learner   c     s=0.0   s=0.5   s=1.0   more scaffold helps?")
    for l in data["learners"]:
        c = l["competence"]
        g0, g5, g1 = (learning_gain(c, s, cfg) for s in (0.0, 0.5, 1.0))
        helps = "yes" if g1 > g0 else "NO -- reversal"
        print("  %-8s %.2f  %5.2f   %5.2f   %5.2f   %s" % (l["id"], c, g0, g5, g1, helps))
    print("-" * 66)
    print("  the novice gains from scaffolding; the expert loses -- expertise reversal.")


def policy_view(data):
    cfg = data
    fixed = cohort_total(data["learners"], fixed_full, cfg)
    adapt = cohort_total(data["learners"], adaptive, cfg)
    print("POLICY — total cohort learning: fixed-full scaffolding vs adaptive fading")
    print("-" * 66)
    for l in data["learners"]:
        c = l["competence"]
        gf = learning_gain(c, fixed_full(c, cfg), cfg)
        ga = learning_gain(c, adaptive(c, cfg), cfg)
        print("  %-8s c=%.2f  fixed(s=1)=%5.2f   adaptive(s=%.0f)=%5.2f"
              % (l["id"], c, gf, adaptive(c, cfg), ga))
    print("-" * 66)
    print("  fixed total = %.2f   adaptive total = %.2f   (adaptive fades scaffolding for experts)"
          % (fixed, adapt))


def check(data):
    print("SELF-TEST — scaffolding helps novices, hurts experts; adaptive beats and dominates fixed")
    print("-" * 66)
    cfg = data
    learners = {l["id"]: l["competence"] for l in data["learners"]}

    nov = learners["novice"]
    novice_helped = learning_gain(nov, 1.0, cfg) > learning_gain(nov, 0.0, cfg)
    print("  full scaffolding helps the novice = %s (%.2f > %.2f)"
          % (novice_helped, learning_gain(nov, 1.0, cfg), learning_gain(nov, 0.0, cfg)))

    exp = learners["expert"]
    expert_hurt = learning_gain(exp, 1.0, cfg) < learning_gain(exp, 0.0, cfg)
    print("  full scaffolding HURTS the expert (reversal) = %s (%.2f < %.2f)"
          % (expert_hurt, learning_gain(exp, 1.0, cfg), learning_gain(exp, 0.0, cfg)))

    fixed = cohort_total(data["learners"], fixed_full, cfg)
    adapt = cohort_total(data["learners"], adaptive, cfg)
    adaptive_wins = adapt > fixed
    print("  adaptive fading beats fixed-full over the cohort = %s (%.2f > %.2f)" % (adaptive_wins, adapt, fixed))

    # Adaptive never does worse than fixed for any single learner (per-learner dominance).
    dominates = all(
        learning_gain(l["competence"], adaptive(l["competence"], cfg), cfg)
        >= learning_gain(l["competence"], fixed_full(l["competence"], cfg), cfg) - 1e-9
        for l in data["learners"])
    print("  adaptive never underperforms fixed for any learner = %s" % dominates)

    expert_gets_less = adaptive(exp, cfg) < fixed_full(exp, cfg)
    print("  adaptive gives the expert less scaffolding than fixed = %s (%.0f < 1)" % (expert_gets_less, adaptive(exp, cfg)))

    ok = novice_helped and expert_hurt and adaptive_wins and dominates and expert_gets_less
    print("-" * 66)
    print("SELF-TEST %s  novice_helped=%s  expert_hurt=%s  adaptive_wins=%s  dominates=%s  expert_gets_less=%s"
          % ("PASS" if ok else "FAIL", novice_helped, expert_hurt, adaptive_wins, dominates, expert_gets_less))
    return ok


def main():
    p = argparse.ArgumentParser(description="Expertise reversal and faded scaffolding.")
    p.add_argument("--curve", action="store_true")
    p.add_argument("--policy", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("learners=%d  reversal_at_competence=%.2f  file=%s  (model is a fixture)"
          % (len(data["learners"]), reversal_point(data), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.curve:
        curve_view(data)
    elif args.policy:
        policy_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
