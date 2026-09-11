"""Switching wins the Monty Hall game 2/3 of the time -- but only because of HOW the host chose the door to open.

You pick one of three doors; a car is behind one, goats behind the other two. The host, who knows where the car is,
opens a different door to reveal a goat, then asks if you want to switch to the last unopened door. Intuition says the
two remaining doors are now 50/50, so switching cannot matter. Intuition is wrong: switching wins 2/3 of the time and
staying wins only 1/3. Your first pick was right 1/3 of the time, and nothing the host did changed that, so the other
door must carry the remaining 2/3 -- the host, forced to avoid the car, funneled that probability onto the one door he
left closed.

The subtle part is that this answer depends entirely on the host's POLICY, not on what you see. You see the same thing
either way -- a goat behind an opened door -- but the number behind it differs. A host who KNOWS where the car is and is
constrained to reveal a goat has leaked information: his choice was not free, and the door he avoided is special. A host
who opens a random unpicked door and just happens to reveal a goat has leaked nothing about the remaining doors, so from
those runs switching is a coin flip. Same visible outcome, different probability, because the data-generating process
differs. That is the real lesson, and it is a data-analysis lesson: you cannot compute a conditional probability from
the outcome alone; you must condition on how the outcome was produced.

This enumerates every case exactly (no simulation) for both host policies.

  --enumerate  every (car, pick) case under the knowing host: when staying wins and when switching wins, and the totals
  --reveal     switching's win probability under the knowing host (2/3) vs the ignorant host who revealed a goat (1/2)
  --check      switching wins 2/3 and staying 1/3 under the knowing host; the ignorant-host-revealed-a-goat case is 1/2

The number of doors and the host policies are the fixture; every probability is an exact fraction. Stdlib only.
"""
import argparse
import json
import sys
from fractions import Fraction
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "montyhall.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def knowing_host_probs(doors):
    """Exact P(switch wins) and P(stay wins) when the host always opens a goat door that isn't the pick."""
    switch_wins = Fraction(0)
    stay_wins = Fraction(0)
    for car, pick in product(range(doors), range(doors)):
        w = Fraction(1, doors * doors)                 # each (car, pick) is equally likely
        if pick == car:
            stay_wins += w                             # staying wins exactly when the first pick was the car
        else:
            switch_wins += w                           # host clears the other goat, so switching lands on the car
    return switch_wins, stay_wins


def ignorant_host_switch_prob(doors):
    """Exact P(switch wins | host revealed a goat) when the host opens a RANDOM unpicked door (may hit the car)."""
    good = Fraction(0)   # runs where the opened door was a goat AND switching wins
    revealed_goat = Fraction(0)   # runs where the opened door was a goat (the condition)
    for car, pick in product(range(doors), range(doors)):
        others = [d for d in range(doors) if d != pick]
        for opened in others:                          # host opens a uniformly random unpicked door
            w = Fraction(1, doors * doors * len(others))
            if opened == car:
                continue                               # host accidentally revealed the car: excluded by conditioning
            revealed_goat += w
            switch_to = [d for d in range(doors) if d != pick and d != opened][0]
            if switch_to == car:
                good += w
    return good / revealed_goat


# ----------------------------------------------------------------- printing

def enumerate_view(data):
    doors = data["doors"]
    print("ENUMERATE — every (car, pick) case under the knowing host (each equally likely)")
    print("-" * 58)
    print("  car  pick   staying wins   switching wins")
    stay = switch = 0
    for car, pick in product(range(doors), range(doors)):
        s = pick == car
        print("   %d    %d      %-12s   %s" % (car, pick, s, not s))
        stay += 1 if s else 0
        switch += 0 if s else 1
    total = doors * doors
    print("-" * 58)
    print("  staying wins %d/%d = %s ; switching wins %d/%d = %s"
          % (stay, total, Fraction(stay, total), switch, total, Fraction(switch, total)))


def reveal_view(data):
    doors = data["doors"]
    sw, st = knowing_host_probs(doors)
    ig = ignorant_host_switch_prob(doors)
    print("REVEAL — the same goat behind an opened door, two host policies, two answers")
    print("-" * 62)
    print("  knowing host (opens a goat on purpose):   P(switch wins) = %s" % sw)
    print("  knowing host:                             P(stay wins)   = %s" % st)
    print("  ignorant host (opened at random, hit a goat this run):    %s" % ig)
    print("-" * 62)
    print("  you saw a goat either way; what is behind the other door depends on how it was chosen.")


def check(data):
    print("SELF-TEST — switching wins 2/3 and staying 1/3 under the knowing host; the ignorant-host-revealed-a-goat case is 1/2")
    print("-" * 116)
    doors = data["doors"]
    sw, st = knowing_host_probs(doors)
    ig = ignorant_host_switch_prob(doors)

    switch_two_thirds = sw == Fraction(2, 3)
    print("  switching wins exactly 2/3 under the knowing host = %s (%s)" % (switch_two_thirds, sw))

    stay_one_third = st == Fraction(1, 3)
    print("  staying wins exactly 1/3 under the knowing host = %s (%s)" % (stay_one_third, st))

    switch_beats_stay = sw > st
    print("  switching strictly beats staying = %s (%s > %s)" % (switch_beats_stay, sw, st))

    probs_sum_to_one = sw + st == 1
    print("  the two knowing-host outcomes partition the probability = %s (%s + %s = 1)" % (probs_sum_to_one, sw, st))

    ignorant_is_half = ig == Fraction(1, 2)
    print("  the ignorant host who revealed a goat gives switch = 1/2 = %s (%s)" % (ignorant_is_half, ig))

    policy_matters = sw != ig
    print("  same visible goat, different answer by host policy = %s (%s vs %s)" % (policy_matters, sw, ig))

    ok = switch_two_thirds and stay_one_third and switch_beats_stay and probs_sum_to_one and ignorant_is_half and policy_matters
    print("-" * 116)
    print("SELF-TEST %s  switch_two_thirds=%s  stay_one_third=%s  switch_beats_stay=%s  probs_sum_to_one=%s  ignorant_is_half=%s  policy_matters=%s"
          % ("PASS" if ok else "FAIL", switch_two_thirds, stay_one_third, switch_beats_stay, probs_sum_to_one, ignorant_is_half, policy_matters))
    return ok


def main():
    p = argparse.ArgumentParser(description="Monty Hall by exact enumeration: switching wins 2/3 under a knowing host, but the answer depends on the host's door-opening policy, not on the goat you see.")
    p.add_argument("--enumerate", action="store_true")
    p.add_argument("--reveal", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("doors=%d  host_policies=%s  file=%s  (the setup is a fixture; every probability is enumerated exactly)"
          % (data["doors"], data["host_policies"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if getattr(args, "enumerate"):
        enumerate_view(data)
    elif args.reveal:
        reveal_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
