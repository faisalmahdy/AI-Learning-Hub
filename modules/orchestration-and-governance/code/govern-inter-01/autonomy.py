#!/usr/bin/env python3
"""Earned autonomy: promote on the confidence bound, not the lucky streak.

An agent earns more autonomy -- act without asking -- by a measured track record:
the fraction of its decisions a human accepted. The obvious rule is to promote
when that fraction clears a threshold. It hands full autonomy to an agent that
went 5-for-5, because 5/5 = 100% >= 80%. But 5 decisions cannot tell 100% from
60%; the rate is real and the confidence is not. Promote instead on the LOWER
BOUND of a confidence interval (Wilson), and a hot rookie must keep proving
itself while a veteran with a long record is promoted -- because autonomy should
follow evidence, not a streak.

  --ledger      each agent: accepted / total, point rate, Wilson lower bound
  --decide      naive (point-rate) vs earned (lower-bound) promotion, per agent
  --measure     premature promotions each rule makes against each agent's true rate
  --check       the point rule promotes a lucky streak; the bound rule never does

Introduces the Wilson score interval (stdlib math), the right tool for a pass
rate at small n. No network, no model. Ledgers and true rates are a fixture.
"""
import argparse
import json
import sys
from math import sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "ledger.json"

Z = 1.96          # 95% confidence
THRESHOLD = 0.80  # the acceptance rate an agent must clear to earn the next tier


def load():
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    return data["agents"]


def rate(agent):
    return agent["accepted"] / agent["total"] if agent["total"] else 0.0


def wilson_lower(accepted, n, z=Z):
    """Lower bound of the Wilson score interval for a proportion. Shrinks toward
    0.5 and widens when n is small, so a short streak cannot clear a high bar."""
    if n == 0:
        return 0.0
    p = accepted / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z / denom) * sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return center - margin


# ------------------------------------------------------------------ the rules

def promote_naive(agent):
    """THE BUG: promote when the raw acceptance rate clears the threshold. Blind
    to how few decisions that rate is built on."""
    return rate(agent) >= THRESHOLD


def promote_earned(agent):
    """Promote only when the lower confidence bound clears the threshold -- i.e.
    we are 95% sure the TRUE rate is above the bar, not just this sample's."""
    return wilson_lower(agent["accepted"], agent["total"]) >= THRESHOLD


# ---------------------------------------------------------------- the measurement

def premature(agents, rule):
    """Promotions the rule makes for agents whose TRUE rate is below the bar."""
    return [a["id"] for a in agents if rule(a) and a["true_rate"] < THRESHOLD]


def missed(agents, rule):
    """Agents whose true rate clears the bar but the rule withholds promotion."""
    return [a["id"] for a in agents if not rule(a) and a["true_rate"] >= THRESHOLD]


# ------------------------------------------------------------------- printing

def ledger_view(agents):
    print("LEDGER — acceptance record and the confidence bound   (bar = %.0f%%)" % (THRESHOLD * 100))
    print("-" * 68)
    print("  agent       accepted/total   rate     wilson-lower   true")
    for a in sorted(agents, key=lambda x: -x["total"]):
        print("  %-10s  %3d/%-3d          %.2f     %.2f           %.2f"
              % (a["id"], a["accepted"], a["total"], rate(a), wilson_lower(a["accepted"], a["total"]), a["true_rate"]))
    print("-" * 68)
    print("  the rate can hit 1.00 on five decisions; the lower bound cannot -- it")
    print("  stays low until enough decisions rule out an unlucky-or-lucky sample.")


def decide_view(agents):
    print("DECISIONS — naive (rate) vs earned (lower bound)   (bar = %.0f%%)" % (THRESHOLD * 100))
    print("-" * 68)
    print("  agent       rate   lower   naive        earned")
    for a in sorted(agents, key=lambda x: -x["total"]):
        nv = "PROMOTE" if promote_naive(a) else "hold"
        er = "PROMOTE" if promote_earned(a) else "hold"
        flag = "  <-- lucky streak" if promote_naive(a) and not promote_earned(a) and a["true_rate"] < THRESHOLD else ""
        print("  %-10s  %.2f   %.2f    %-11s  %-8s%s"
              % (a["id"], rate(a), wilson_lower(a["accepted"], a["total"]), nv, er, flag))
    print("-" * 68)


def measure(agents):
    print("PROMOTION QUALITY — premature promotions against each agent's true rate")
    print("-" * 68)
    for label, rule in (("naive (rate)", promote_naive), ("earned (lower bound)", promote_earned)):
        prem = premature(agents, rule)
        print("  %-22s premature: %d  %s" % (label, len(prem), prem or ""))
    print("-" * 68)
    print("  a premature promotion hands unattended autonomy to an agent whose true")
    print("  rate is below the bar -- the exact failure earned autonomy exists to stop.")


def check(agents):
    print("SELF-TEST — the point rule promotes a lucky streak; the bound rule does not")
    print("-" * 68)
    nv_prem = premature(agents, promote_naive)
    er_prem = premature(agents, promote_earned)
    print("  naive premature promotions   = %s" % (nv_prem or "none"))
    print("  earned premature promotions  = %s" % (er_prem or "none"))

    naive_overreaches = len(nv_prem) > 0
    print("  the point rule promotes at least one under-bar agent = %s" % naive_overreaches)
    earned_clean = len(er_prem) == 0
    print("  the bound rule promotes no under-bar agent = %s" % earned_clean)

    # the mechanism: a perfect short streak clears the rate but not the bound.
    streak = [a for a in agents if rate(a) >= 0.999 and a["total"] <= 8]
    streak_ok = all(promote_naive(a) and not promote_earned(a) for a in streak) and len(streak) > 0
    ids = ", ".join(a["id"] for a in streak)
    print("  a perfect short streak (%s) is promoted by rate, held by bound = %s" % (ids, streak_ok))

    # a veteran with a long strong record earns it under both interpretations.
    vet = max(agents, key=lambda a: a["total"])
    vet_earned = promote_earned(vet) and vet["true_rate"] >= THRESHOLD
    print("  the longest-record agent (%s) is earned-promoted and truly qualifies = %s" % (vet["id"], vet_earned))

    det = wilson_lower(agents[0]["accepted"], agents[0]["total"]) == wilson_lower(agents[0]["accepted"], agents[0]["total"])
    ok = naive_overreaches and earned_clean and streak_ok and vet_earned and det
    print("-" * 68)
    print("SELF-TEST %s  naive_overreaches=%s  earned_clean=%s  streak_held=%s  vet_ok=%s"
          % ("PASS" if ok else "FAIL", naive_overreaches, earned_clean, streak_ok, vet_earned))
    return ok


def main():
    p = argparse.ArgumentParser(description="Gate autonomy on a confidence bound, not a rate.")
    p.add_argument("--ledger", action="store_true")
    p.add_argument("--decide", action="store_true")
    p.add_argument("--measure", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    agents = load()
    print("agents=%d  bar=%.0f%%  z=%.2f  file=%s  (ledgers are a fixture)"
          % (len(agents), THRESHOLD * 100, Z, LEDGER.name))
    print("")

    if args.check:
        return 0 if check(agents) else 1
    if args.ledger:
        ledger_view(agents)
    elif args.decide:
        decide_view(agents)
    elif args.measure:
        measure(agents)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
