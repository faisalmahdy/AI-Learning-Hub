"""Blind the LLM judge to provenance, or self-preference bias crowns its own family's answer.

An LLM judge that can see which model wrote each answer is not neutral. Judges systematically score answers
from their own model family higher than a fair grader would -- self-preference bias. So when you use a
judge to compare its own family's output against a competitor's, the judge tips the scale toward its own,
and on any case where the two answers are close in real quality, the bias flips the verdict: the judge
picks its own answer even though the other was actually better. Your eval then reports that your model wins,
when a neutral grader would have called it a loss.

The bias only changes the outcome when the true quality gap is smaller than the bias. A far-better
competitor answer still wins despite the bias; a slightly-better one loses to it. So the damage is
concentrated exactly on the close comparisons -- which are the ones an eval most needs to get right, because
those are where the models are actually competitive. And every error points the same way: toward the
judge's own family. That systematic, one-directional tilt is what makes self-preference bias dangerous
rather than just noisy.

The fix is to blind the judge to provenance: strip which model produced each answer before the judge sees
them, so it grades on content alone. With provenance hidden the self-preference bonus has nothing to attach
to, and the judge scores by true quality. On this fixture a biased judge (a +2 bonus to its own answer)
gets 3 of 5 verdicts right, wrongly favoring its own on the two close cases; the blinded judge gets all 5
right. This computes both.

  --verdicts   each case: true quality of each answer, and what the biased vs blinded judge picks
  --accuracy   the judge's accuracy against the true-better answer, biased vs blinded
  --check      the biased judge favors its own on close cases and is less accurate; blinding fixes it

The per-case qualities and the bias are the fixture; every verdict is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "cases.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def true_better(case):
    """The genuinely better answer by quality (ties go to 'other', the neutral choice)."""
    return "own" if case["q_own"] > case["q_other"] else "other"


def judge_pick(case, bias):
    """The judge picks the higher-scoring answer; a biased judge adds `bias` to its own answer's score."""
    return "own" if case["q_own"] + bias > case["q_other"] else "other"


def accuracy(cases, bias):
    return round(sum(judge_pick(c, bias) == true_better(c) for c in cases) / len(cases), 3)


def own_pick_rate(cases, bias):
    return round(sum(judge_pick(c, bias) == "own" for c in cases) / len(cases), 3)


# ----------------------------------------------------------------- printing

def verdicts_view(data):
    cases, bias = data["cases"], data["bias"]
    print("VERDICTS — true-better vs biased judge (+%d to own) vs blinded judge" % bias)
    print("-" * 62)
    print("  case  q_own  q_other  truth   biased   blinded")
    for i, c in enumerate(cases):
        b, bl = judge_pick(c, bias), judge_pick(c, 0)
        mark = "" if b == true_better(c) else "  <- biased wrong"
        print("  %-4d  %-5d  %-7d  %-6s  %-7s  %s%s" % (i + 1, c["q_own"], c["q_other"], true_better(c), b, bl, mark))
    print("-" * 62)
    print("  the bias flips the close cases toward 'own'.")


def accuracy_view(data):
    cases, bias = data["cases"], data["bias"]
    truth_own_rate = round(sum(true_better(c) == "own" for c in cases) / len(cases), 3)
    print("ACCURACY — judge accuracy and how often it picks its own answer")
    print("-" * 58)
    print("  biased judge:   accuracy %.3f   picks own %.3f" % (accuracy(cases, bias), own_pick_rate(cases, bias)))
    print("  blinded judge:  accuracy %.3f   picks own %.3f" % (accuracy(cases, 0), own_pick_rate(cases, 0)))
    print("  ground truth:                    own is better %.3f of the time" % truth_own_rate)
    print("-" * 58)
    print("  the biased judge picks own more than the truth warrants.")


def check(data):
    print("SELF-TEST — the biased judge favors its own on close cases and is less accurate; blinding fixes it")
    print("-" * 100)
    cases, bias = data["cases"], data["bias"]
    biased_errors = [i for i, c in enumerate(cases) if judge_pick(c, bias) != true_better(c)]

    blinded_perfect = accuracy(cases, 0) == 1.0
    print("  the blinded judge matches the true-better answer every time = %s (%.3f)" % (blinded_perfect, accuracy(cases, 0)))

    biased_less_accurate = accuracy(cases, bias) < accuracy(cases, 0)
    print("  the biased judge is less accurate than the blinded one = %s (%.3f vs %.3f)"
          % (biased_less_accurate, accuracy(cases, bias), accuracy(cases, 0)))

    errors_favor_own = all(judge_pick(cases[i], bias) == "own" for i in biased_errors) and len(biased_errors) > 0
    print("  every biased error wrongly favors the judge's own answer = %s (cases %s)" % (errors_favor_own, [i + 1 for i in biased_errors]))

    flips_are_close = all(0 < cases[i]["q_other"] - cases[i]["q_own"] <= bias for i in biased_errors)
    print("  the flipped cases are exactly those where own trailed by <= the bias = %s" % flips_are_close)

    own_rate_inflated = own_pick_rate(cases, bias) > own_pick_rate(cases, 0)
    print("  the biased judge picks its own answer more often than blinded = %s (%.3f vs %.3f)"
          % (own_rate_inflated, own_pick_rate(cases, bias), own_pick_rate(cases, 0)))

    ok = blinded_perfect and biased_less_accurate and errors_favor_own and flips_are_close and own_rate_inflated
    print("-" * 100)
    print("SELF-TEST %s  blinded_perfect=%s  biased_less_accurate=%s  errors_favor_own=%s  flips_are_close=%s  own_rate_inflated=%s"
          % ("PASS" if ok else "FAIL", blinded_perfect, biased_less_accurate, errors_favor_own, flips_are_close, own_rate_inflated))
    return ok


def main():
    p = argparse.ArgumentParser(description="Blind the LLM judge to provenance to remove self-preference bias.")
    p.add_argument("--verdicts", action="store_true")
    p.add_argument("--accuracy", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("cases=%d  bias=+%d  file=%s  (the qualities and bias are a fixture)"
          % (len(data["cases"]), data["bias"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.verdicts:
        verdicts_view(data)
    elif args.accuracy:
        accuracy_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
