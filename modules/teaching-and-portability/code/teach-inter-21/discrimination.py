"""Measure an item's discrimination, not just its difficulty, or a question that separates nobody counts as good.

A quiz exists to sort learners: who has the skill and who does not. The natural knob is DIFFICULTY -- the fraction
who pass -- and the standard advice is to aim for the middle, around 0.5, so an item is neither trivial nor
impossible. But difficulty alone is a trap. An item can sit at a perfect 0.5 pass rate and still tell you nothing,
because the half who pass it are not the half who know the material -- strong and weak students pass it equally,
so it splits the class at random. Difficulty measures how HARD an item is; it says nothing about whether the item
measures the RIGHT thing.

Discrimination is the missing number. Rank students by their overall score, take the top group and the bottom
group, and compare how each does on the item: discrimination = pass_rate(top) - pass_rate(bottom). A good item is
one the strong students pass and the weak students miss, so its discrimination is high and positive. An item
everyone passes has discrimination zero (both groups score 1.0). An item that strong and weak pass equally has
discrimination zero too -- even at an ideal 0.5 difficulty. A NEGATIVE discrimination is the alarm bell: the weak
students beat the strong ones, which usually means the item is mis-keyed or measures a misconception.

On this fixture item A is passed by the top students and missed by the bottom -- difficulty 0.44, discrimination
1.00, an excellent item. Item B is passed by everyone -- difficulty 1.00, discrimination 0.00, dead weight. Item
C sits at difficulty 0.56, right in the 'ideal' band, yet the top and bottom groups pass it equally -- discrimination
0.00. Judge by difficulty and C looks like your best item; judge by discrimination and it measures nothing.

  --items      each item's difficulty and discrimination, ranked
  --groups     the top/bottom split and each group's pass rate per item, so the discrimination is visible
  --check      the easy item and the mid-difficulty item both have zero discrimination; only A separates students

The students and their answers are the fixture; every statistic is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "items.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def difficulty(students, item):
    """Pass rate: the fraction of students who got the item right."""
    return sum(s[item] for s in students) / len(students)


def groups(students, frac=1 / 3):
    """Split students into the top and bottom `frac` by total score."""
    ranked = sorted(students, key=lambda s: s["total"], reverse=True)
    k = max(1, int(len(ranked) * frac))
    return ranked[:k], ranked[-k:]


def discrimination(students, item):
    """pass_rate(top group) - pass_rate(bottom group): does the item separate strong from weak?"""
    top, bottom = groups(students)
    top_rate = sum(s[item] for s in top) / len(top)
    bottom_rate = sum(s[item] for s in bottom) / len(bottom)
    return top_rate - bottom_rate


# ----------------------------------------------------------------- printing

def items_view(data):
    students, items = data["students"], data["items"]
    print("ITEMS — difficulty (pass rate) and discrimination (top - bottom)")
    print("-" * 62)
    print("  item   difficulty   discrimination   verdict")
    for it in sorted(items, key=lambda i: discrimination(students, i), reverse=True):
        d, disc = difficulty(students, it), discrimination(students, it)
        verdict = "keeps" if disc >= 0.3 else "measures nothing"
        print("  %-4s   %.2f         %+.2f            %s" % (it, d, disc, verdict))
    print("-" * 62)
    print("  an ideal 0.5 difficulty does not save an item whose discrimination is 0.")


def groups_view(data):
    students, items = data["students"], data["items"]
    top, bottom = groups(students)
    print("GROUPS — top third %s vs bottom third %s (by total score)" % ([s["id"] for s in top], [s["id"] for s in bottom]))
    print("-" * 62)
    print("  item   top pass   bottom pass   discrimination")
    for it in items:
        tr = sum(s[it] for s in top) / len(top)
        br = sum(s[it] for s in bottom) / len(bottom)
        print("  %-4s   %.2f       %.2f          %+.2f" % (it, tr, br, tr - br))
    print("-" * 62)
    print("  discrimination is just how much more the top group passes than the bottom group.")


def check(data):
    print("SELF-TEST — the easy item and the mid-difficulty item both have zero discrimination; only A separates")
    print("-" * 104)
    students = data["students"]
    dA, dB, dC = (discrimination(students, i) for i in ("A", "B", "C"))
    fA, fB, fC = (difficulty(students, i) for i in ("A", "B", "C"))

    good_item_discriminates = dA >= 0.5
    print("  item A separates strong from weak students = %s (discrimination %+.2f)" % (good_item_discriminates, dA))

    easy_item_zero_disc = dB == 0.0 and fB == 1.0
    print("  item B is too easy and discriminates nothing = %s (difficulty %.2f, disc %+.2f)" % (easy_item_zero_disc, fB, dB))

    ideal_difficulty_still_useless = 0.4 <= fC <= 0.6 and dC == 0.0
    print("  item C has ideal difficulty but zero discrimination = %s (difficulty %.2f, disc %+.2f)" % (ideal_difficulty_still_useless, fC, dC))

    difficulty_would_mislead = fC > fA and dC < dA
    print("  difficulty alone would rank C above A, discrimination reverses it = %s (C %.2f>%.2f A, but disc %+.2f<%+.2f)" % (difficulty_would_mislead, fC, fA, dC, dA))

    only_A_kept = [i for i in data["items"] if discrimination(students, i) >= 0.3] == ["A"]
    print("  only item A clears a discrimination bar of 0.3 = %s" % only_A_kept)

    ok = good_item_discriminates and easy_item_zero_disc and ideal_difficulty_still_useless and difficulty_would_mislead and only_A_kept
    print("-" * 104)
    print("SELF-TEST %s  good_item_discriminates=%s  easy_item_zero_disc=%s  ideal_difficulty_still_useless=%s  difficulty_would_mislead=%s  only_A_kept=%s"
          % ("PASS" if ok else "FAIL", good_item_discriminates, easy_item_zero_disc, ideal_difficulty_still_useless, difficulty_would_mislead, only_A_kept))
    return ok


def main():
    p = argparse.ArgumentParser(description="Rate quiz items by discrimination (does it separate strong from weak) not just difficulty (how hard it is).")
    p.add_argument("--items", action="store_true")
    p.add_argument("--groups", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("students=%d  items=%s  file=%s  (the students and answers are a fixture)"
          % (len(data["students"]), data["items"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.items:
        items_view(data)
    elif args.groups:
        groups_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
