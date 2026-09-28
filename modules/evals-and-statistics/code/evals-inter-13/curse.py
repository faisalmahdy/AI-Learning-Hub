"""Pick the best of many models on one noisy eval and its score is inflated -- the winner's curse.

Every eval score is the true skill plus noise -- a finite test set, sampling temperature, luck of which
items were asked. When you evaluate one model, that noise averages toward zero and the score is roughly
honest. But when you evaluate many models and crown the highest scorer, you are not sampling the noise
once -- you are taking the maximum over many noisy draws, and the maximum is biased upward. The model you
pick is disproportionately likely to be one that got lucky, so its measured score overstates its true
skill. This is the winner's curse: selecting on a noisy measurement guarantees the selected value is an
overestimate.

It is worse than a harmless bias, because it manufactures a gap out of nothing. If several models are
genuinely equal in skill, one of them will still top the leaderboard by luck, and its lead over the field
looks like a real difference. Report that leader's eval score as its performance and you have overstated
it; believe the leaderboard gap and you have crowned a false winner whose advantage was noise.

The fix is a fresh held-out set. The noise that inflated the winner on the selection eval is independent
of the noise on a new eval, so re-scoring the winner on held-out data gives an unbiased estimate -- which
regresses back toward the truth and erases the fake gap.

On this fixture five models have identical true skill of 0.70, so every difference between them is noise.
The selection eval crowns model_c at 0.78 -- an 0.08 inflation over its true 0.70, and an apparent lead
over the field. Re-scored on held-out data, model_c drops to 0.69, right at the truth, and it is no longer
even the top scorer. This computes both.

  --scores     each model's true skill, selection-eval score, and held-out score
  --winner     the selection winner, its inflation, and what held-out says about it
  --check      selecting the max inflates the winner's score; a held-out re-score regresses it to the truth

The true skills and the two eval scores are the fixture; every comparison is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "models.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def winner_on(scores):
    """The model with the highest score on a given eval."""
    return max(scores, key=scores.get)


def mean(xs):
    return sum(xs) / len(xs)


# ----------------------------------------------------------------- printing

def scores_view(data):
    true, sel, hold = data["true_skill"], data["selection_eval"], data["holdout_eval"]
    print("SCORES — true skill vs selection eval vs held-out eval")
    print("-" * 58)
    print("  model      true    selection   held-out")
    for m in true:
        print("  %-8s   %.2f      %.2f        %.2f" % (m, true[m], sel[m], hold[m]))
    print("-" * 58)
    print("  every true skill is equal, so all gaps are noise.")


def winner_view(data):
    true, sel, hold = data["true_skill"], data["selection_eval"], data["holdout_eval"]
    w = winner_on(sel)
    field = [sel[m] for m in sel if m != w]
    print("WINNER — the model crowned by the selection eval")
    print("-" * 58)
    print("  selection winner:      %s at %.2f" % (w, sel[w]))
    print("  its true skill:        %.2f  (inflation +%.2f)" % (true[w], sel[w] - true[w]))
    print("  its lead over field:   +%.3f on selection eval" % (sel[w] - mean(field)))
    print("  its held-out score:    %.2f  (regressed to the truth)" % hold[w])
    print("  held-out top scorer:   %s   (the crown moved)" % winner_on(hold))
    print("-" * 58)
    print("  the winner was lucky, not better; held-out reveals it.")


def check(data):
    print("SELF-TEST — selecting the max inflates the winner; a held-out re-score regresses it to the truth")
    print("-" * 96)
    true, sel, hold = data["true_skill"], data["selection_eval"], data["holdout_eval"]
    w = winner_on(sel)

    true_all_equal = max(true.values()) - min(true.values()) < 1e-9
    print("  all models have equal true skill, so any gap is noise = %s (%.2f)" % (true_all_equal, true[w]))

    selection_inflates = sel[w] > true[w]
    print("  the selection winner's score exceeds its true skill = %s (%.2f > %.2f)" % (selection_inflates, sel[w], true[w]))

    holdout_regresses = hold[w] < sel[w]
    print("  the winner's held-out score drops back down = %s (%.2f < %.2f)" % (holdout_regresses, hold[w], sel[w]))

    holdout_closer = abs(hold[w] - true[w]) < abs(sel[w] - true[w])
    print("  held-out is closer to the truth than selection = %s (|%.2f| < |%.2f|)"
          % (holdout_closer, hold[w] - true[w], sel[w] - true[w]))

    crown_moves = winner_on(hold) != w
    print("  the selection winner is not the held-out winner = %s (%s vs %s)" % (crown_moves, w, winner_on(hold)))

    ok = true_all_equal and selection_inflates and holdout_regresses and holdout_closer and crown_moves
    print("-" * 96)
    print("SELF-TEST %s  true_all_equal=%s  selection_inflates=%s  holdout_regresses=%s  holdout_closer=%s  crown_moves=%s"
          % ("PASS" if ok else "FAIL", true_all_equal, selection_inflates, holdout_regresses, holdout_closer, crown_moves))
    return ok


def main():
    p = argparse.ArgumentParser(description="The winner's curse: picking the best model on a noisy eval inflates its score.")
    p.add_argument("--scores", action="store_true")
    p.add_argument("--winner", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("models=%d  file=%s  (the true skills and both eval scores are a fixture)"
          % (len(data["true_skill"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.scores:
        scores_view(data)
    elif args.winner:
        winner_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
