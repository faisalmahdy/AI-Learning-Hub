"""Re-measure the winning variant on a fresh holdout -- the one you picked for having the highest observed lift is biased upward, because you selected on noise.

Run several variants, measure each one's lift, ship the best. It is the obvious way to pick a winner and it systematically overstates how good the winner is. The reason is selection: every measured lift is the true lift plus noise, and when you take the MAXIMUM observed lift, you are not just selecting for a high true effect -- you are also selecting for a high noise draw. The variant that happens to catch a lucky upward error is more likely to top the chart than an equally-good variant that got unlucky. So the winner is disproportionately a variant whose noise was positive, and its observed lift is inflated relative to its true lift. This is the winner's curse, and it means the number you used to justify the launch is, on average, too high.

Two things follow, both damaging. First, the winner underdelivers: you shipped it expecting the observed lift and get the (lower) true lift, so the launch looks like a regression against its own forecast even when it is a real improvement. Second, the winner may not even be the best variant -- a genuinely superior variant that drew unlucky noise can lose the selection to a mediocre variant that drew lucky noise, so you ship the wrong one. The more variants you compare, the stronger the effect, because the maximum of many noisy estimates is pulled further above the truth.

The fix is to separate selection from estimation. Use the experiment to SELECT the winner, but do not trust that same experiment's number as the winner's effect -- re-measure the chosen variant on a FRESH holdout (or a follow-up experiment) that had no part in the selection. The holdout's estimate of the winner is unbiased, because the winner was not chosen for its holdout noise, so it reveals the true (lower) effect and gives you an honest launch forecast. Selecting and estimating on the same data is the mistake; splitting them is the correction, the same discipline as not evaluating a model on its training set.

The rule: select the winning variant on the experiment but re-estimate its effect on a fresh holdout, rather than trusting the observed lift of the highest-scoring variant, because taking the maximum over noisy estimates selects for positive noise -- so the winner's observed lift is biased upward and it underdelivers, and a holdout that did not drive the selection gives an unbiased estimate.

On this fixture four variants have true effects 2, 1, 3, 2 and observed effects 2, 5, 3, 4. Selecting the highest observed picks v2 at +5, but its true effect is only 1 -- an inflation of 4 -- and v3, the genuinely best variant (true +3), was not selected. A holdout re-measure of v2 reveals the true +1. This computes both.

  --variants   each variant's true and observed effect, and which the observed-max selection picks
  --curse      the selected winner's observed vs true effect (the inflation), and whether it is the truly-best variant
  --check      selecting on the observed maximum inflates the winner's estimate and can miss the true best; a holdout reveals the truth

variants (true and observed effects) are the fixture; the selected winner, its inflation, and the true-best comparison are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "winnerscurse.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def selected_by_observed(variants):
    """The variant the naive rule ships: highest observed effect (ties broken by id)."""
    return max(variants, key=lambda v: (v["observed_effect"], v["id"]))


def true_best(variants):
    """The variant with the highest true effect (ties broken by id)."""
    return max(variants, key=lambda v: (v["true_effect"], v["id"]))


def inflation(variant):
    """How much the observed effect overstates the true effect."""
    return variant["observed_effect"] - variant["true_effect"]


def holdout_estimate(variant):
    """A fresh holdout, not used for selection, measures the true effect (unbiased)."""
    return variant["true_effect"]


# ----------------------------------------------------------------- printing

def variants_view(data):
    variants = data["variants"]
    win = selected_by_observed(variants)
    print("VARIANTS — true vs observed effect (selection picks the observed max)")
    print("-" * 60)
    print("  variant  true   observed   selected?")
    for v in variants:
        print("  %-7s  %-5d  %-9d  %s" % (v["id"], v["true_effect"], v["observed_effect"], "<- SHIP" if v["id"] == win["id"] else ""))
    print("-" * 60)
    print("  the naive rule ships the highest observed effect: %s (+%d observed)" % (win["id"], win["observed_effect"]))


def curse_view(data):
    variants = data["variants"]
    win = selected_by_observed(variants)
    best = true_best(variants)
    print("CURSE — the selected winner's observed vs true effect")
    print("-" * 62)
    print("  selected winner %s: observed +%d, true +%d -> inflated by %d" % (win["id"], win["observed_effect"], win["true_effect"], inflation(win)))
    print("  holdout re-measure of %s reveals: +%d (the true effect)" % (win["id"], holdout_estimate(win)))
    print("  truly-best variant: %s (true +%d) -- %s" % (best["id"], best["true_effect"], "same as selected" if best["id"] == win["id"] else "NOT the one selected"))
    print("-" * 62)
    print("  shipping on the observed lift forecasts +%d but delivers +%d" % (win["observed_effect"], win["true_effect"]))


def check(data):
    print("SELF-TEST — selecting on the observed maximum inflates the winner's estimate and can miss the true best; a holdout reveals the truth")
    print("-" * 130)
    variants = data["variants"]
    win = selected_by_observed(variants)
    best = true_best(variants)

    winner_is_observed_max = win["observed_effect"] == max(v["observed_effect"] for v in variants)
    print("  the naive rule ships the variant with the maximum observed effect = %s (%s, +%d)" % (winner_is_observed_max, win["id"], win["observed_effect"]))

    winner_estimate_inflated = win["observed_effect"] > win["true_effect"]
    print("  the winner's observed effect overstates its true effect = %s (+%d > +%d)" % (winner_estimate_inflated, win["observed_effect"], win["true_effect"]))

    inflation_positive = inflation(win) > 0
    print("  the selection bias is positive (winner's curse direction) = %s (inflated by %d)" % (inflation_positive, inflation(win)))

    winner_not_true_best = win["true_effect"] < best["true_effect"]
    print("  the selected winner is NOT the truly-best variant = %s (true +%d < best +%d, which is %s)" % (winner_not_true_best, win["true_effect"], best["true_effect"], best["id"]))

    holdout_lower_than_observed = holdout_estimate(win) < win["observed_effect"]
    print("  the holdout re-measure is lower than the selection estimate = %s (+%d < +%d)" % (holdout_lower_than_observed, holdout_estimate(win), win["observed_effect"]))

    holdout_is_unbiased = holdout_estimate(win) == win["true_effect"]
    print("  the holdout estimate equals the true effect (unbiased) = %s (+%d)" % (holdout_is_unbiased, holdout_estimate(win)))

    ok = (winner_is_observed_max and winner_estimate_inflated and inflation_positive and winner_not_true_best
          and holdout_lower_than_observed and holdout_is_unbiased)
    print("-" * 130)
    print("SELF-TEST %s  winner_is_observed_max=%s  winner_estimate_inflated=%s  inflation_positive=%s  winner_not_true_best=%s  holdout_lower_than_observed=%s  holdout_is_unbiased=%s"
          % ("PASS" if ok else "FAIL", winner_is_observed_max, winner_estimate_inflated, inflation_positive, winner_not_true_best, holdout_lower_than_observed, holdout_is_unbiased))
    return ok


def main():
    p = argparse.ArgumentParser(description="Winner's curse: select the winning variant on the experiment but re-estimate its effect on a fresh holdout, rather than trusting the observed lift of the highest-scoring variant, because taking the maximum over noisy estimates selects for positive noise -- so the winner's observed lift is biased upward and it underdelivers, and a holdout that did not drive the selection gives an unbiased estimate.")
    p.add_argument("--variants", action="store_true")
    p.add_argument("--curse", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("variants=%d  file=%s  (each variant's true and observed effect is a fixture)"
          % (len(data["variants"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.variants:
        variants_view(data)
    elif args.curse:
        curse_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
