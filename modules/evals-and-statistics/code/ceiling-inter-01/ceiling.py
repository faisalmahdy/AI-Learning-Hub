"""Retire a benchmark once models saturate it -- at the ceiling two different models both score 100% and look equal.

A benchmark is a measuring instrument, and like any instrument it has a range. When the things you are measuring outgrow
that range, the instrument stops measuring. For a capability benchmark, the range is item difficulty: a benchmark can only
tell two models apart on the items where one succeeds and the other fails. If every item is easy enough that both models
pass it, every item is uninformative, and the benchmark reports the same score -- 100% -- for both, no matter how large
the real gap in their ability. This is SATURATION (a ceiling effect): the benchmark has hit its ceiling, and a score at the
ceiling carries no information about how much further a model could have gone, because there was nothing left to test.

The trap is that a saturated benchmark still produces numbers, and the numbers look like a result. Two models both score
99% or 100%, the leaderboard shows them tied or nearly so, and the natural reading is 'these models are equivalent.' They
are not equivalent; the benchmark has simply run out of items hard enough to separate them. Worse, near the ceiling the
tiny remaining differences are dominated by the handful of hardest (and often noisiest or most flawed) items, so the
ranking among top models becomes driven by measurement noise and idiosyncratic item quirks rather than real capability --
the benchmark is not just uninformative, it is actively misleading about which model is better. Progress that is real
becomes invisible, and noise gets promoted to signal.

The fix is to match the instrument to what you are measuring: a benchmark whose items straddle the models' current ability
-- some they pass, some they fail -- has discriminating power, so the real gap shows up as a real score difference. As
models improve, the benchmark that discriminated last year saturates, and you must retire it and move to a harder one (or
add harder items), the same way a bathroom scale is the wrong instrument for weighing a truck. A single high score is not
evidence of capability; it is evidence you have outgrown the test.

The rule: a benchmark can only distinguish models on items where they differ, so once models saturate it (both near the
maximum score) it has hit its ceiling and can no longer rank them -- their tie is an artifact of the test's range, not their
equality -- and you must move to a harder, discriminating benchmark to keep measuring the real gap.

On this fixture model A (ability 8) is genuinely stronger than model B (ability 6). On the easy, saturated benchmark both
pass every item and score 100%, so the measured gap is 0 -- A's superiority is hidden. On the discriminating benchmark,
whose items straddle the two abilities, A scores 75% and B 25%, a 50-point gap that reveals the real difference. This
computes both.

  --score     each model's score on each benchmark, and the measured gap -- 0 on the saturated one, 50 points on the discriminating one
  --items     per-item pass/fail for both models: on the easy benchmark every item is passed by both (uninformative)
  --check     the saturated benchmark ties two unequal models at the ceiling; the discriminating one reveals the true gap

model_ability and benchmarks are the fixture; every pass/fail, score, and gap is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "ceiling.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def passes(ability, difficulty):
    """A model passes an item when its ability is at least the item's difficulty."""
    return ability >= difficulty


def score(ability, items):
    """Fraction of items the model passes (0..1)."""
    return sum(1 for d in items if passes(ability, d)) / len(items)


def gap(abilities, items):
    """The score difference between model A and model B on a benchmark (percentage points)."""
    return (score(abilities["A"], items) - score(abilities["B"], items)) * 100


def discriminating_items(abilities, items):
    """Items that one model passes and the other fails -- the only items that carry ranking signal."""
    return [d for d in items if passes(abilities["A"], d) != passes(abilities["B"], d)]


# ----------------------------------------------------------------- printing

def score_view(data):
    ab, benches = data["model_ability"], data["benchmarks"]
    print("SCORE — model A (ability %d) vs B (ability %d) on each benchmark" % (ab["A"], ab["B"]))
    print("-" * 62)
    print("  benchmark              A score   B score   measured gap")
    for name, items in benches.items():
        print("  %-21s %-9s %-9s %+.0f pts"
              % (name, "%.0f%%" % (score(ab["A"], items) * 100), "%.0f%%" % (score(ab["B"], items) * 100), gap(ab, items)))
    print("-" * 62)
    print("  same two models: the saturated benchmark measures a 0-point gap; the harder one, 50.")


def items_view(data):
    ab, benches = data["model_ability"], data["benchmarks"]
    print("ITEMS — per-item pass/fail; an item separates models only if they disagree on it")
    print("-" * 66)
    for name, items in benches.items():
        print("  %s:" % name)
        print("    difficulty:  %s" % "  ".join("%2d" % d for d in items))
        print("    A passes:    %s" % "  ".join(" y" if passes(ab["A"], d) else " n" for d in items))
        print("    B passes:    %s" % "  ".join(" y" if passes(ab["B"], d) else " n" for d in items))
        disc = discriminating_items(ab, items)
        print("    discriminating items (A!=B): %s" % (disc if disc else "none -- benchmark is saturated"))
    print("-" * 66)
    print("  only items where A and B disagree carry ranking signal; a saturated benchmark has none.")


def check(data):
    print("SELF-TEST — the saturated benchmark ties two unequal models at the ceiling; the discriminating one reveals the true gap")
    print("-" * 120)
    ab, benches = data["model_ability"], data["benchmarks"]
    easy, hard = benches["easy_saturated"], benches["hard_discriminating"]

    saturated_both_max = score(ab["A"], easy) == 1.0 and score(ab["B"], easy) == 1.0
    print("  on the easy benchmark both models score 100%% = %s (A %.0f%%, B %.0f%%)"
          % (saturated_both_max, score(ab["A"], easy) * 100, score(ab["B"], easy) * 100))

    saturated_gap_zero = gap(ab, easy) == 0
    print("  the saturated benchmark measures a zero gap = %s (%.0f pts)" % (saturated_gap_zero, gap(ab, easy)))

    true_gap_exists = ab["A"] > ab["B"]
    print("  but the models are genuinely unequal = %s (ability %d vs %d)" % (true_gap_exists, ab["A"], ab["B"]))

    discriminating_shows_gap = gap(ab, hard) > 0
    print("  the discriminating benchmark reveals the gap = %s (%.0f pts)" % (discriminating_shows_gap, gap(ab, hard)))

    saturated_has_no_signal = len(discriminating_items(ab, easy)) == 0 and len(discriminating_items(ab, hard)) > 0
    print("  the saturated benchmark has no discriminating items, the hard one does = %s (%d vs %d)"
          % (saturated_has_no_signal, len(discriminating_items(ab, easy)), len(discriminating_items(ab, hard))))

    ok = saturated_both_max and saturated_gap_zero and true_gap_exists and discriminating_shows_gap and saturated_has_no_signal
    print("-" * 120)
    print("SELF-TEST %s  saturated_both_max=%s  saturated_gap_zero=%s  true_gap_exists=%s  discriminating_shows_gap=%s  saturated_has_no_signal=%s"
          % ("PASS" if ok else "FAIL", saturated_both_max, saturated_gap_zero, true_gap_exists, discriminating_shows_gap, saturated_has_no_signal))
    return ok


def main():
    p = argparse.ArgumentParser(description="Benchmark saturation: a benchmark can only distinguish models on items where they differ, so once models saturate it (both near the maximum score) it has hit its ceiling and can no longer rank them -- their tie is an artifact of the test's range, not their equality -- and you must move to a harder, discriminating benchmark to keep measuring the real gap.")
    p.add_argument("--score", action="store_true")
    p.add_argument("--items", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("model_ability=%s  benchmarks=%s  file=%s  (the abilities and item difficulties are a fixture)"
          % (data["model_ability"], {k: v for k, v in data["benchmarks"].items()}, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.score:
        score_view(data)
    elif args.items:
        items_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
