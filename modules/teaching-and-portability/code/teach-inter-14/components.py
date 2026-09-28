"""Score by knowledge component, not whole item, or you know a student is failing but not which skill to fix.

Most real problems exercise several skills at once: a word problem needs reading, setup, and arithmetic; a
proof needs three lemmas. Grade the item as one right-or-wrong and you learn whether the student got it,
not why they missed it. That single bit is enough to compute an accuracy but useless for teaching, because
remediation has to target a skill, and '70% correct' names no skill. Worse, two students can have the
identical item accuracy while lacking completely different skills -- the whole-item score cannot tell them
apart, so it cannot route either to the right practice.

Decomposing each item into its knowledge components fixes this. Tag every item with the skills it requires,
and for each skill compute the student's success rate across the items that use it. Now a missing skill
shows up as a low success rate on exactly the items requiring it, while the skills the student has stay
high. The deficit is localized: instead of '70% correct, remediate something,' you get 'fractions are at
0%, everything else is fine, remediate fractions.' Same responses, but attributed to skills instead of
items, which is the difference between a grade and a diagnosis.

On this fixture two students each score 3 of 6 items -- identical whole-item accuracy of 0.50. But student
P misses every item requiring fractions and student Q misses every item requiring multiplication. The item
score is blind to the difference; the per-component analysis pins P's deficit to fractions (0.00 there,
fine elsewhere) and Q's to multiplication. This computes both.

  --responses  each item's required skills and whether each student got it right
  --components  each student's per-skill success rate and inferred weakest skill
  --check      both students share one item accuracy but have different, correctly identified skill deficits

The skills, items, and each student's mastered skills are the fixture; every response is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "skills.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def correct(item_skills, mastered):
    """An item is correct iff the student has mastered every skill it requires."""
    return all(s in mastered for s in item_skills)


def item_accuracy(items, mastered):
    return round(sum(correct(it, mastered) for it in items) / len(items), 3)


def component_rates(items, skills, mastered):
    """Per-skill success: fraction of items requiring that skill the student got right."""
    rates = {}
    for s in skills:
        using = [it for it in items if s in it]
        rates[s] = round(sum(correct(it, mastered) for it in using) / len(using), 3) if using else None
    return rates


def weakest(items, skills, mastered):
    """The skill with the lowest success rate -- the one to remediate."""
    rates = component_rates(items, skills, mastered)
    return min(rates, key=lambda s: rates[s])


# ----------------------------------------------------------------- printing

def responses_view(data):
    items, students = data["items"], data["students"]
    print("RESPONSES — each item's required skills and whether each student got it right")
    print("-" * 62)
    header = "   ".join(students)
    print("  item  skills%s%s" % (" " * 18, header))
    for i, it in enumerate(items):
        marks = "     ".join("Y" if correct(it, students[st]) else "n" for st in students)
        print("  %-4d  %-22s %s" % (i + 1, "+".join(it), marks))
    print("-" * 62)
    for st in students:
        print("  %s item accuracy: %.2f" % (st, item_accuracy(items, students[st])))


def components_view(data):
    items, skills, students = data["items"], data["skills"], data["students"]
    print("COMPONENTS — per-skill success rate and inferred weakest skill")
    print("-" * 62)
    for st in students:
        rates = component_rates(items, skills, students[st])
        cells = "   ".join("%s %.2f" % (s, rates[s]) for s in skills)
        print("  %s:  %s   -> remediate %s" % (st, cells, weakest(items, skills, students[st])))
    print("-" * 62)
    print("  same 0.50 item accuracy, different skill at fault.")


def check(data):
    print("SELF-TEST — both students share one item accuracy but have different, correctly identified skill deficits")
    print("-" * 104)
    items, skills, students = data["items"], data["skills"], data["students"]
    names = list(students)
    p, q = names[0], names[1]

    same_item_accuracy = item_accuracy(items, students[p]) == item_accuracy(items, students[q])
    print("  the two students have identical item accuracy = %s (%.2f = %.2f)"
          % (same_item_accuracy, item_accuracy(items, students[p]), item_accuracy(items, students[q])))

    dp, dq = weakest(items, skills, students[p]), weakest(items, skills, students[q])
    different_deficits = dp != dq
    print("  the component analysis finds different deficits = %s (%s vs %s)" % (different_deficits, dp, dq))

    # ground truth: the skill each student did NOT master
    missing_p = [s for s in skills if s not in students[p]]
    missing_q = [s for s in skills if s not in students[q]]
    identifies_truth = [dp] == missing_p and [dq] == missing_q
    print("  each inferred deficit is the truly missing skill = %s (P missing %s, Q missing %s)"
          % (identifies_truth, missing_p, missing_q))

    deficit_is_zero = component_rates(items, skills, students[p])[dp] == 0.0 and component_rates(items, skills, students[q])[dq] == 0.0
    print("  the missing skill sits at 0.00 success while others are higher = %s" % deficit_is_zero)

    others_high = min(v for s, v in component_rates(items, skills, students[p]).items() if s != dp) > 0.0
    print("  the student's other skills are clearly above the deficit = %s" % others_high)

    ok = same_item_accuracy and different_deficits and identifies_truth and deficit_is_zero and others_high
    print("-" * 104)
    print("SELF-TEST %s  same_item_accuracy=%s  different_deficits=%s  identifies_truth=%s  deficit_is_zero=%s  others_high=%s"
          % ("PASS" if ok else "FAIL", same_item_accuracy, different_deficits, identifies_truth, deficit_is_zero, others_high))
    return ok


def main():
    p = argparse.ArgumentParser(description="Score by knowledge component, not whole item, to diagnose which skill failed.")
    p.add_argument("--responses", action="store_true")
    p.add_argument("--components", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("items=%d  skills=%d  students=%d  file=%s  (the items and mastery are a fixture)"
          % (len(data["items"]), len(data["skills"]), len(data["students"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.responses:
        responses_view(data)
    elif args.components:
        components_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
