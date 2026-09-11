"""Report Cohen's kappa, not raw agreement -- two raters who both say 'no' agree 82% of the time by chance alone.

When two raters label the same items -- two human annotators, an LLM judge against a gold label, two judges to be compared
-- the natural quality measure is how often they agree. But raw agreement (the fraction of items labeled the same) is
inflated whenever the labels are imbalanced, because agreement can happen by accident. If 90% of items are really 'no',
two raters who each say 'no' most of the time will land on 'no' together most of the time WITHOUT any shared judgment --
their agreement is mostly the arithmetic of both usually guessing the common class. So a headline like '82% agreement'
can describe raters who are, in the part that matters, no better than two independent coin-weightings.

Cohen's kappa corrects for chance agreement. It computes the observed agreement p_o (the raw fraction) and the expected
agreement p_e -- how often the two would agree if their labels were independent given their individual 'yes' rates -- and
reports kappa = (p_o - p_e) / (1 - p_e). The numerator is the agreement ABOVE chance; the denominator is the room above
chance there was to agree. So kappa = 0 means agreement exactly at the chance level (no real signal), kappa = 1 means
perfect agreement, and negative kappa means worse than chance. The rescaling by (1 - p_e) is what makes kappa comparable
across datasets with different class balances -- raw agreement is not.

The practical upshot for evaluation: reporting raw agreement between an LLM judge and gold, or between two annotators, on a
skewed label distribution overstates how trustworthy the labeling is, and two judges can look equally good on raw
agreement while one has real skill and the other is riding the base rate. Kappa (or a variant like weighted kappa for
ordinal labels, or Krippendorff's alpha for many raters) is the metric to report.

On this fixture two scenarios each reach high raw agreement. In 'chance_agreement' the raters' yes-labels are independent
on an imbalanced set: raw agreement 0.82, but expected-by-chance agreement is also 0.82, so kappa is 0 -- no real
agreement at all. In 'real_agreement' the raters genuinely agree: raw agreement 0.94 and kappa 0.79. Raw agreement cannot
tell these apart; kappa can. This computes both.

  --agreement  each scenario's raw agreement, chance agreement, and kappa -- both raw-high, but kappa 0.00 vs 0.79
  --explain    why the chance scenario's agreement is all chance: both raters mostly say 'no', so they collide on 'no'
  --check      raw agreement is high in both scenarios; the chance scenario's kappa is ~0 while the real one's is high; kappa = (po-pe)/(1-pe)

The 2x2 counts are the fixture; every agreement figure and kappa is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "kappa.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def total(c):
    return c["both_yes"] + c["r1_yes_r2_no"] + c["r1_no_r2_yes"] + c["both_no"]


def observed_agreement(c):
    """p_o: the fraction of items the two raters labeled the same."""
    return (c["both_yes"] + c["both_no"]) / total(c)


def chance_agreement(c):
    """p_e: agreement expected if the two raters' labels were independent given their yes-rates."""
    n = total(c)
    r1_yes = (c["both_yes"] + c["r1_yes_r2_no"]) / n
    r2_yes = (c["both_yes"] + c["r1_no_r2_yes"]) / n
    return r1_yes * r2_yes + (1 - r1_yes) * (1 - r2_yes)


def kappa(c):
    """Cohen's kappa: (observed - chance) / (1 - chance)."""
    po, pe = observed_agreement(c), chance_agreement(c)
    k = (po - pe) / (1 - pe)
    return 0.0 if abs(k) < 1e-9 else k


# ----------------------------------------------------------------- printing

def agreement_view(data):
    print("AGREEMENT — raw agreement vs Cohen's kappa, per scenario")
    print("-" * 66)
    print("  scenario           raw agreement   chance agreement   kappa")
    for name, c in data["scenarios"].items():
        print("  %-17s  %-14.2f  %-17.2f  %.2f" % (name, observed_agreement(c), chance_agreement(c), kappa(c)))
    print("-" * 66)
    print("  both scenarios have high raw agreement; only kappa separates real from chance.")


def explain_view(data):
    c = data["scenarios"]["chance_agreement"]
    n = total(c)
    r1_yes = (c["both_yes"] + c["r1_yes_r2_no"]) / n
    r2_yes = (c["both_yes"] + c["r1_no_r2_yes"]) / n
    print("EXPLAIN — why the chance scenario's 0.82 agreement is all chance")
    print("-" * 62)
    print("  rater 1 says 'yes' %.0f%% of the time, 'no' %.0f%%" % (r1_yes * 100, (1 - r1_yes) * 100))
    print("  rater 2 says 'yes' %.0f%% of the time, 'no' %.0f%%" % (r2_yes * 100, (1 - r2_yes) * 100))
    print("  so by chance they both say 'no' %.0f%% x %.0f%% = %.0f%% of the time," % ((1 - r1_yes) * 100, (1 - r2_yes) * 100, (1 - r1_yes) * (1 - r2_yes) * 100))
    print("  plus both 'yes' %.0f%% x %.0f%% = %.0f%% -> chance agreement %.2f" % (r1_yes * 100, r2_yes * 100, r1_yes * r2_yes * 100, chance_agreement(c)))
    print("-" * 62)
    print("  observed agreement (%.2f) equals chance agreement (%.2f), so kappa = 0."
          % (observed_agreement(c), chance_agreement(c)))


def check(data):
    print("SELF-TEST — raw agreement is high in both scenarios; the chance scenario's kappa is ~0 while the real one's is high; kappa = (po-pe)/(1-pe)")
    print("-" * 132)
    ch = data["scenarios"]["chance_agreement"]
    re = data["scenarios"]["real_agreement"]

    both_raw_high = observed_agreement(ch) >= 0.8 and observed_agreement(re) >= 0.8
    print("  both scenarios have raw agreement >= 0.80 = %s (%.2f, %.2f)" % (both_raw_high, observed_agreement(ch), observed_agreement(re)))

    chance_kappa_zero = abs(kappa(ch)) < 1e-9
    print("  the chance scenario's kappa is 0 = %s (%.2f)" % (chance_kappa_zero, kappa(ch)))

    real_kappa_high = kappa(re) > 0.7
    print("  the real scenario's kappa is high = %s (%.2f)" % (real_kappa_high, kappa(re)))

    raw_cannot_separate = abs(observed_agreement(ch) - observed_agreement(re)) < abs(kappa(ch) - kappa(re))
    print("  raw agreement separates them less than kappa does = %s (raw gap %.2f vs kappa gap %.2f)"
          % (raw_cannot_separate, abs(observed_agreement(ch) - observed_agreement(re)), abs(kappa(ch) - kappa(re))))

    formula_ok = all(abs(kappa(c) - (observed_agreement(c) - chance_agreement(c)) / (1 - chance_agreement(c))) < 1e-12 for c in data["scenarios"].values())
    print("  kappa equals (observed - chance) / (1 - chance) = %s" % formula_ok)

    ok = both_raw_high and chance_kappa_zero and real_kappa_high and raw_cannot_separate and formula_ok
    print("-" * 132)
    print("SELF-TEST %s  both_raw_high=%s  chance_kappa_zero=%s  real_kappa_high=%s  raw_cannot_separate=%s  formula_ok=%s"
          % ("PASS" if ok else "FAIL", both_raw_high, chance_kappa_zero, real_kappa_high, raw_cannot_separate, formula_ok))
    return ok


def main():
    p = argparse.ArgumentParser(description="Cohen's kappa: raw inter-rater agreement is inflated on imbalanced labels because two raters who both favor the common class agree by chance, so report kappa = (observed - chance) / (1 - chance), which is 0 at chance-level agreement and comparable across class balances.")
    p.add_argument("--agreement", action="store_true")
    p.add_argument("--explain", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("scenarios=%s  file=%s  (the 2x2 rater counts are a fixture)"
          % (list(data["scenarios"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.agreement:
        agreement_view(data)
    elif args.explain:
        explain_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
