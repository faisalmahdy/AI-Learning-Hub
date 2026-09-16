"""Selecting on a collider invents a correlation -- two independent traits look related the moment you condition on something they both cause.

You have two traits that are genuinely unrelated in the population -- say a performer's skill and their looks, independent, knowing one tells you nothing about the other. Then you study a SELECTED group: famous performers. And in that group the two traits are correlated -- the more skilled ones are less good-looking, the better-looking ones less skilled. The correlation is real in the data you have, it replicates, and it is entirely an artifact of who you let into the sample. This is Berkson's paradox, and it is one of the most common ways a study finds a relationship that does not exist.

The mechanism is selection on a COLLIDER: a variable that two others both influence. Fame is a collider here -- both skill and looks lead to fame -- and 'famous performers' is the population conditioned on that collider. Conditioning on a collider is exactly the operation that induces a dependence between its causes. The intuition is a process of elimination: if fame requires skill OR looks, then a famous performer who lacks skill MUST have looks (there was no other way in), so within the famous group, low skill predicts high looks. The traits did not become related; the selection rule tied them together by excluding the one cell -- low skill AND low looks -- where their independence was visible.

The failure is dangerous precisely because the correlation is stable and plausible. Restrict a medical study to hospitalized patients (hospitalization is a collider -- many conditions lead to it) and two unrelated diseases show up correlated. Study only funded startups, only admitted students, only users who churned -- any sample defined by a threshold on an outcome that multiple inputs feed -- and you will find relationships among the inputs that are not there in the population. The fix is not statistical cleverness on the sample; it is recognizing that the sample was selected on a collider and that the correlation cannot be read as a population relationship.

The rule: when a sample is selected by a threshold on a variable that several traits jointly influence (a collider), do not read correlations among those traits in the sample as real -- because conditioning on the collider induces a spurious association between its causes (a low value on one trait implies a high value on another just to clear the threshold), so the relationship is an artifact of selection, absent in the unconditioned population.

On this fixture skill and looks are independent in the population (phi correlation 0.0). Selecting the 'famous' -- skill OR looks, which drops only the low-low cell -- makes them correlated at phi -0.5 in the famous subgroup. This computes both.

  --population   the full 2x2 of skill by looks, the marginals, and the phi correlation (independent: 0)
  --selected     the famous subgroup after conditioning on the collider, its 2x2, and its phi correlation (spurious: negative)
  --check        the traits are independent in the population but negatively correlated in the collider-selected subgroup -- an artifact of selection

groups and admit_if_sum_at_least are the fixture; every marginal, conditional, and phi correlation is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "berkson.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def cell(groups, skill, looks):
    """Count in the (skill, looks) cell."""
    return sum(g["count"] for g in groups if g["skill"] == skill and g["looks"] == looks)


def phi(groups):
    """Phi correlation for the 2x2 of skill by looks: (ad - bc) / sqrt of the four margins."""
    a = cell(groups, 1, 1)
    b = cell(groups, 1, 0)
    c = cell(groups, 0, 1)
    d = cell(groups, 0, 0)
    denom = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    if denom == 0:
        return 0.0
    val = (a * d - b * c) / denom
    return 0.0 if abs(val) < 1e-9 else val


def select(groups, threshold):
    """Keep only the cells whose skill + looks meets the collider threshold (fame = skill OR looks)."""
    return [g for g in groups if g["skill"] + g["looks"] >= threshold]


def p_looks_given_skill(groups, skill):
    """P(looks = 1 | skill) in whatever groups are passed."""
    total = cell(groups, skill, 1) + cell(groups, skill, 0)
    return cell(groups, skill, 1) / total if total else 0.0


# ----------------------------------------------------------------- printing

def table(groups):
    lines = []
    lines.append("           looks=0   looks=1")
    lines.append("  skill=1    %-7d   %-7d" % (cell(groups, 1, 0), cell(groups, 1, 1)))
    lines.append("  skill=0    %-7d   %-7d" % (cell(groups, 0, 0), cell(groups, 0, 1)))
    return lines


def population_view(data):
    groups = data["groups"]
    print("POPULATION — the full 2x2 of skill by looks")
    print("-" * 52)
    for line in table(groups):
        print(line)
    print("-" * 52)
    print("  P(looks=1 | skill=1) = %.2f ; P(looks=1 | skill=0) = %.2f" % (p_looks_given_skill(groups, 1), p_looks_given_skill(groups, 0)))
    print("  phi correlation = %.2f (skill and looks are independent)" % phi(groups))


def selected_view(data):
    groups, thr = data["groups"], data["admit_if_sum_at_least"]
    sel = select(groups, thr)
    dropped = [g for g in groups if g["skill"] + g["looks"] < thr]
    print("SELECTED — the famous subgroup (skill + looks >= %d, i.e. skill OR looks)" % thr)
    print("-" * 62)
    for line in table(sel):
        print(line)
    print("-" * 62)
    print("  the low-low cell is dropped: %s" % ("(skill 0, looks 0) = %d people removed" % dropped[0]["count"] if dropped else "none"))
    print("  P(looks=1 | skill=1) = %.2f ; P(looks=1 | skill=0) = %.2f" % (p_looks_given_skill(sel, 1), p_looks_given_skill(sel, 0)))
    print("  phi correlation = %.2f (skill and looks now negatively correlated -- an artifact)" % phi(sel))


def check(data):
    print("SELF-TEST — the traits are independent in the population but negatively correlated in the collider-selected subgroup -- an artifact of selection")
    print("-" * 134)
    groups, thr = data["groups"], data["admit_if_sum_at_least"]
    sel = select(groups, thr)

    phi_pop = phi(groups)
    independent_in_population = abs(phi_pop) < 1e-9
    print("  skill and looks are independent in the population = %s (phi = %.2f)" % (independent_in_population, phi_pop))

    pop_conditionals_equal = abs(p_looks_given_skill(groups, 1) - p_looks_given_skill(groups, 0)) < 1e-9
    print("  P(looks | skill) does not depend on skill in the population = %s (%.2f vs %.2f)"
          % (pop_conditionals_equal, p_looks_given_skill(groups, 1), p_looks_given_skill(groups, 0)))

    dropped = [g for g in groups if g["skill"] + g["looks"] < thr]
    selection_on_collider = len(dropped) == 1 and dropped[0]["skill"] == 0 and dropped[0]["looks"] == 0
    print("  selection on the collider drops exactly the low-low cell = %s" % selection_on_collider)

    phi_sel = phi(sel)
    spurious_negative_in_sample = phi_sel < 0
    print("  skill and looks are negatively correlated in the famous subgroup = %s (phi = %.2f)" % (spurious_negative_in_sample, phi_sel))

    correlation_is_artifact = abs(phi_sel - phi_pop) > 0.4
    print("  the sample correlation is absent in the population (an artifact) = %s (%.2f in sample vs %.2f in population)"
          % (correlation_is_artifact, phi_sel, phi_pop))

    low_skill_implies_looks = p_looks_given_skill(sel, 0) > p_looks_given_skill(sel, 1)
    print("  in the subgroup, low skill implies higher looks (elimination) = %s (%.2f > %.2f)"
          % (low_skill_implies_looks, p_looks_given_skill(sel, 0), p_looks_given_skill(sel, 1)))

    ok = independent_in_population and pop_conditionals_equal and selection_on_collider and spurious_negative_in_sample and correlation_is_artifact and low_skill_implies_looks
    print("-" * 134)
    print("SELF-TEST %s  independent_in_population=%s  pop_conditionals_equal=%s  selection_on_collider=%s  spurious_negative_in_sample=%s  correlation_is_artifact=%s  low_skill_implies_looks=%s"
          % ("PASS" if ok else "FAIL", independent_in_population, pop_conditionals_equal, selection_on_collider, spurious_negative_in_sample, correlation_is_artifact, low_skill_implies_looks))
    return ok


def main():
    p = argparse.ArgumentParser(description="Berkson's paradox: when a sample is selected by a threshold on a variable that several traits jointly influence (a collider), do not read correlations among those traits in the sample as real, because conditioning on the collider induces a spurious association between its causes (a low value on one trait implies a high value on another just to clear the threshold), so the relationship is an artifact of selection, absent in the unconditioned population.")
    p.add_argument("--population", action="store_true")
    p.add_argument("--selected", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    total = sum(g["count"] for g in data["groups"])
    print("population=%d  cells=%d  admit_if_sum_at_least=%d  file=%s  (the population and selection rule are a fixture)"
          % (total, len(data["groups"]), data["admit_if_sum_at_least"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.population:
        population_view(data)
    elif args.selected:
        selected_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
