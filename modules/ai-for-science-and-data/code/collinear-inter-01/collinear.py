"""When two predictors are collinear the individual coefficients are not identified -- many coefficient pairs fit the data exactly equally, so a single coefficient's size or sign is meaningless, even though the predictions and the coefficient SUM are pinned down.

A regression with two predictors fits y with b1*x1 + b2*x2. We read the coefficients as effects: b1 is "the effect of x1 holding x2 fixed", b2 the effect of x2. That reading assumes you can hold one predictor fixed while the other varies -- that the data contains rows where they disagree. Collinearity is exactly the case where they do not: x1 and x2 move together, so the data never separates them.

Take the extreme where x2 equals x1. Then the fitted value is b1*x1 + b2*x2 = (b1+b2)*x1 -- it depends only on the SUM of the coefficients, not on how that sum is split. Any two pairs with the same sum produce the identical prediction for every row and therefore the identical residual sum of squares. The fit literally cannot tell (2, 0) from (0, 2) from (1, 1) from (5, -3); they are the same model wearing different coefficient labels.

So under collinearity the sum b1+b2 is identified -- the data pins it -- but the split is not. You can shovel weight from one coefficient to the other, even driving one negative, without moving the fit a hair. That is why a coefficient's sign can flip between two equally-good fits, and why interpreting a single collinear coefficient ("x2 has a negative effect") is nonsense: an equally-good fit gives x2 a positive coefficient. The prediction is trustworthy; the attribution is not.

The rule: do not interpret an individual coefficient when its predictor is collinear with another -- the fit identifies only their combination, so many coefficient pairs (including sign-flipped ones) fit identically; report the prediction and the combined effect, not the split.

On this fixture x2 equals x1 and y is twice x1, so the true combined slope is 2. Every coefficient pair that sums to 2 fits perfectly, including (5, -3) with a negative x2 coefficient; a pair that sums to anything else misfits. This computes each pair's sum, predictions, and residual sum of squares.

  --fits      each candidate (b1, b2): its coefficient sum, first prediction, and residual sum of squares
  --identify  what the data identifies (the sum) vs what it does not (the split), with the sign-flip example
  --check     collinear predictors identify only the coefficient sum; the individual split (and its sign) is free

x1, x2, y, and the candidate pairs are the fixture; the sums, predictions, and residuals are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "collinear.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def predict(b1, b2, x1, x2):
    """The fitted value row by row: b1*x1 + b2*x2."""
    return [b1 * a + b2 * b for a, b in zip(x1, x2)]


def sse(preds, y):
    """Residual sum of squares -- how badly a coefficient pair misfits."""
    return sum((p - t) ** 2 for p, t in zip(preds, y))


def perfect(pair, x1, x2, y):
    return sse(predict(pair[0], pair[1], x1, x2), y) == 0


# ----------------------------------------------------------------- printing

def fits_view(data):
    x1, x2, y = data["x1"], data["x2"], data["y"]
    print("FITS — each candidate coefficient pair scored against the same data")
    print("-" * 60)
    print("  b1    b2    b1+b2   pred[0]   SSE")
    for b1, b2 in data["coeff_pairs"]:
        preds = predict(b1, b2, x1, x2)
        print("  %-4d  %-4d  %-6d  %-8d  %d" % (b1, b2, b1 + b2, preds[0], sse(preds, y)))
    print("-" * 60)
    print("  every pair whose coefficients sum to the true slope fits perfectly")


def identify_view(data):
    x1, x2, y = data["x1"], data["x2"], data["y"]
    fits = [(b1, b2) for b1, b2 in data["coeff_pairs"] if perfect((b1, b2), x1, x2, y)]
    print("IDENTIFY — what the collinear data pins down, and what it leaves free")
    print("-" * 62)
    print("  perfectly-fitting pairs: %s" % fits)
    print("  their coefficient sums:  %s  (all equal -> the SUM is identified)"
          % sorted(set(b1 + b2 for b1, b2 in fits)))
    print("  their b1 values:         %s  (all different -> the SPLIT is not)"
          % sorted(set(b1 for b1, b2 in fits)))
    flip = next(((b1, b2) for b1, b2 in fits if b2 < 0), None)
    print("  sign-flip example:       %s fits perfectly yet gives x2 a negative coefficient" % (flip,))
    print("-" * 62)
    print("  the prediction is trustworthy; the individual coefficient is not")


def check(data):
    print("SELF-TEST — collinear predictors identify only the coefficient sum; the individual split (and its sign) is free")
    print("-" * 116)
    x1, x2, y = data["x1"], data["x2"], data["y"]

    predictors_collinear = x1 == x2
    print("  the two predictors are collinear (x2 == x1) = %s" % predictors_collinear)

    fits = [(b1, b2) for b1, b2 in data["coeff_pairs"] if perfect((b1, b2), x1, x2, y)]
    many_perfect_fits = len(fits) > 1
    print("  more than one coefficient pair fits perfectly = %s (%d pairs)" % (many_perfect_fits, len(fits)))

    sum_is_identified = len(set(b1 + b2 for b1, b2 in fits)) == 1
    print("  every perfect fit has the same coefficient sum = %s (%s)"
          % (sum_is_identified, sorted(set(b1 + b2 for b1, b2 in fits))))

    split_not_identified = len(set(b1 for b1, b2 in fits)) > 1
    print("  the individual b1 differs across perfect fits = %s" % split_not_identified)

    sign_can_flip = any(b2 < 0 for b1, b2 in fits)
    print("  a perfect fit exists with a negative x2 coefficient = %s" % sign_can_flip)

    # predictions are identical across all perfect fits, though coefficients differ
    pred_sets = set(tuple(predict(b1, b2, x1, x2)) for b1, b2 in fits)
    predictions_identical = len(pred_sets) == 1
    print("  all perfect fits produce identical predictions = %s" % predictions_identical)

    ok = (predictors_collinear and many_perfect_fits and sum_is_identified
          and split_not_identified and sign_can_flip and predictions_identical)
    print("-" * 116)
    print("SELF-TEST %s  predictors_collinear=%s  many_perfect_fits=%s  sum_is_identified=%s  split_not_identified=%s  sign_can_flip=%s  predictions_identical=%s"
          % ("PASS" if ok else "FAIL", predictors_collinear, many_perfect_fits, sum_is_identified,
             split_not_identified, sign_can_flip, predictions_identical))
    return ok


def main():
    p = argparse.ArgumentParser(description="Multicollinearity: do not interpret an individual coefficient when its predictor is collinear with another -- the fit identifies only their combination, so many coefficient pairs (including sign-flipped ones) fit identically; report the prediction and the combined effect, not the split.")
    p.add_argument("--fits", action="store_true")
    p.add_argument("--identify", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("rows=%d  predictors=2 (x2==x1)  candidate_pairs=%d  file=%s  (the columns are a fixture)"
          % (len(data["y"]), len(data["coeff_pairs"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.fits:
        fits_view(data)
    elif args.identify:
        identify_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
