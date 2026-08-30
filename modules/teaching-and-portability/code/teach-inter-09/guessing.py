"""Correct the quiz score for guessing before you call it mastery -- raw accuracy promotes a coin-flipper.

A learner takes a 20-item, 4-choice quiz and scores 70%. The rule says advance at 65%, so up they
go. But four-choice items hand out a quarter of the answers for free: guess blindly on every item and
you expect to score 25% knowing nothing. A 70% raw score is not 70% knowledge -- it is the knowledge
plus a layer of luck, and the thinner the real knowledge the thicker the luck layer relative to it.

The fix is the correction-for-guessing formula, as old as standardized testing: score = R - W/(g-1),
where R is right, W is wrong, and g is the number of choices. The logic is that each wrong answer is
evidence of a guess, and for every g-1 wrong guesses the learner probably got one more right by luck,
so you dock a fraction of a point per wrong answer to cancel the expected lucky hits. On this record
the learner truly knew 12 of 20 items; they guessed the other 8 and 2 came up lucky, for 14 right and
a raw score of 0.70. The correction subtracts 6/3 = 2 lucky hits, recovering exactly 12 -- a corrected
score of 0.60, which is below the 0.65 bar. Raw says advance; corrected, and the ground truth, say
not yet. This computes both scores and both advancement decisions.

  --responses   the item-by-item record: what the learner knew vs what they got right
  --score       raw accuracy vs guessing-corrected score, and the advancement decision under each
  --check       raw accuracy overstates mastery and advances; the correction recovers the true known fraction

The known flags and the lucky-guess count are the fixture; every score and decision is computed. Stdlib.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "responses.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- scoring

def raw_accuracy(items):
    """Fraction correct -- counts a lucky guess as if it were knowledge."""
    return round(sum(1 for it in items if it["correct"]) / len(items), 4)


def corrected_score(items, choices):
    """Correction for guessing: (R - W/(g-1)) / N -- docks the expected lucky hits back out."""
    right = sum(1 for it in items if it["correct"])
    wrong = len(items) - right
    corrected_right = right - wrong / (choices - 1)
    return round(corrected_right / len(items), 4)


def true_known(items):
    """Ground truth: the fraction the learner actually knew (fixture flag, not computed from answers)."""
    return round(sum(1 for it in items if it["known"]) / len(items), 4)


# ----------------------------------------------------------------- printing

def responses_view(data):
    items = data["items"]
    print("RESPONSES — %d items, %d choices each; knew? vs correct?" % (len(items), data["choices"]))
    print("-" * 46)
    print("  item   knew   correct   how")
    for it in items:
        how = "knew it" if it["known"] else ("lucky guess" if it["correct"] else "wrong guess")
        print("  %s   %-4s   %-5s     %s" % (it["item"], "yes" if it["known"] else "no",
                                             "yes" if it["correct"] else "no", how))
    print("-" * 46)
    right = sum(1 for it in items if it["correct"])
    print("  %d right, %d wrong; %d truly known, %d guessed."
          % (right, len(items) - right, sum(1 for it in items if it["known"]),
             sum(1 for it in items if not it["known"])))


def score_view(data):
    items, g, thr = data["items"], data["choices"], data["advance_threshold"]
    raw = raw_accuracy(items)
    cor = corrected_score(items, g)
    print("SCORE — raw accuracy vs guessing-corrected, advance at %.2f" % thr)
    print("-" * 56)
    print("  raw accuracy:        %.2f  -> %s" % (raw, "ADVANCE" if raw >= thr else "hold"))
    print("  corrected for guess: %.2f  -> %s" % (cor, "advance" if cor >= thr else "HOLD"))
    print("-" * 56)
    print("  raw counts 2 lucky guesses as knowledge and clears the bar; corrected does not.")


def check(data):
    print("SELF-TEST — raw accuracy overstates mastery and advances; correcting recovers the true known fraction")
    print("-" * 84)
    items, g, thr = data["items"], data["choices"], data["advance_threshold"]

    raw = raw_accuracy(items)
    cor = corrected_score(items, g)
    truth = true_known(items)

    raw_overstates = raw > truth
    print("  raw accuracy overstates what the learner knows = %s (raw %.2f vs true %.2f)" % (raw_overstates, raw, truth))

    corrected_recovers = abs(cor - truth) < 1e-9
    print("  the correction recovers the true known fraction = %s (corrected %.2f, true %.2f)" % (corrected_recovers, cor, truth))

    raw_advances = raw >= thr
    corrected_holds = cor < thr
    decisions_disagree = raw_advances and corrected_holds
    print("  raw advances but corrected holds (opposite calls) = %s (bar %.2f)" % (decisions_disagree, thr))

    truth_says_hold = truth < thr
    corrected_is_right = corrected_holds == truth_says_hold
    print("  the corrected decision matches ground truth = %s (true mastery %.2f < %.2f)" % (corrected_is_right, truth, thr))

    ok = raw_overstates and corrected_recovers and decisions_disagree and corrected_is_right
    print("-" * 84)
    print("SELF-TEST %s  raw_overstates=%s  corrected_recovers=%s  decisions_disagree=%s  corrected_is_right=%s"
          % ("PASS" if ok else "FAIL", raw_overstates, corrected_recovers, decisions_disagree, corrected_is_right))
    return ok


def main():
    p = argparse.ArgumentParser(description="Correct the quiz score for guessing before deciding mastery.")
    p.add_argument("--responses", action="store_true")
    p.add_argument("--score", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("items=%d  choices=%d  advance_threshold=%.2f  file=%s  (the response record is a fixture)"
          % (len(data["items"]), data["choices"], data["advance_threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.responses:
        responses_view(data)
    elif args.score:
        score_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
