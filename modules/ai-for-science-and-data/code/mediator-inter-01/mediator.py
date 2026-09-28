"""Do not control for a mediator when you want the total effect -- adjusting for a variable on the causal path X -> M -> Y removes the indirect effect and shrinks a real effect toward zero.

Choosing which variables to adjust for is the whole game in causal analysis, and the data cannot make the choice for you. The same statistical move -- stratify by a third variable, watch the X-Y association change -- is correct for one kind of variable and disastrous for another, and only the causal structure distinguishes them. A confounder is a common cause of X and Y: you must control for it, or its influence is misread as an effect of X. A collider is a common effect of X and Y: controlling for it manufactures a correlation that is not there. And a mediator sits on the path from X to Y -- X causes M, M causes Y -- carrying part of X's effect.

Control for a mediator and you cut the wire the effect travels on. Holding M fixed, X can no longer influence Y through M, so the association you measure is only the direct path, X -> Y, and the indirect path X -> M -> Y is erased. If the question you are answering is 'what is the total effect of X on Y' -- the usual question for a treatment or intervention -- this is simply wrong: you have thrown away a real component of the effect and reported a number smaller than the truth, sometimes all the way to zero.

The trap is the reflex to 'control for everything', which sounds cautious and is not. Adjusting for a confounder removes bias; adjusting for a mediator introduces it, by answering a different question (the direct effect) than the one asked (the total effect). The two look identical in the data -- both are 'the X-Y effect after adjusting for a third variable' -- and differ only in what that third variable is causally, which you must supply from knowledge of the domain, not read off the numbers.

The rule: do not adjust for a mediator (a variable on the causal path from X to Y) when estimating the total effect of X, because holding it fixed blocks the indirect path and understates the effect -- the same adjustment that is required for a confounder and forbidden for a collider is forbidden for a mediator too, and only the causal role, not the data, tells you which.

On this fixture X raises the mediator M and Y depends on both, so the total effect of X on Y is 8; adjusting for M leaves only the direct effect of 3, removing the indirect effect of 5 that travels through M. This computes both.

  --data      each (X, M) cell, its count, and its Y value
  --effect    the unadjusted (total) effect vs the mediator-adjusted (direct) effect, and the removed indirect effect
  --check      X raises M (it is a mediator); adjusting for M understates the total effect by the indirect path

cells is the fixture; the effects and M's dependence on X are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "mediator.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def y_value(x, m):
    """Outcome determined by the treatment and the mediator: direct effect 3, mediator effect 5."""
    return 10 + 3 * x + 5 * m


def mean_y(cells, x):
    rows = [c for c in cells if c["x"] == x]
    total = sum(c["count"] * y_value(c["x"], c["m"]) for c in rows)
    n = sum(c["count"] for c in rows)
    return total / n


def mean_m(cells, x):
    rows = [c for c in cells if c["x"] == x]
    return sum(c["count"] * c["m"] for c in rows) / sum(c["count"] for c in rows)


def total_effect(cells):
    return mean_y(cells, 1) - mean_y(cells, 0)


def direct_effect(cells):
    """X effect within a fixed mediator level -- the mediator-adjusted estimate."""
    ms = sorted({c["m"] for c in cells})
    diffs = [y_value(1, m) - y_value(0, m) for m in ms]
    return diffs[0] if len(set(diffs)) == 1 else sum(diffs) / len(diffs)


# ----------------------------------------------------------------- printing

def data_view(data):
    cells = data["cells"]
    print("DATA — each (X, M) cell, its count, and its Y = 10 + 3X + 5M")
    print("-" * 50)
    print("  X   M   count   Y")
    for c in sorted(cells, key=lambda c: (c["x"], c["m"])):
        print("  %d   %d   %-5d   %d" % (c["x"], c["m"], c["count"], y_value(c["x"], c["m"])))
    print("-" * 50)
    print("  X=1 rows sit at higher M than X=0 rows — X pushes the mediator up")


def effect_view(data):
    cells = data["cells"]
    tot, dir_ = total_effect(cells), direct_effect(cells)
    print("EFFECT — total (unadjusted) vs direct (adjusted for the mediator)")
    print("-" * 60)
    print("  mean Y at X=0 = %.1f, at X=1 = %.1f" % (mean_y(cells, 0), mean_y(cells, 1)))
    print("  unadjusted total effect of X    = %.1f" % tot)
    print("  effect adjusting for M (direct) = %.1f" % dir_)
    print("  indirect effect removed by adjusting = %.1f" % (tot - dir_))
    print("-" * 60)
    print("  controlling the mediator blocks the X -> M -> Y path and shrinks the effect")


def check(data):
    print("SELF-TEST — X raises M (it is a mediator); adjusting for M understates the total effect by the indirect path")
    print("-" * 122)
    cells = data["cells"]
    tot, dir_ = total_effect(cells), direct_effect(cells)

    x_raises_m = mean_m(cells, 1) > mean_m(cells, 0)
    print("  X raises the mediator M (M is on the path from X) = %s (mean M %.1f -> %.1f)"
          % (x_raises_m, mean_m(cells, 0), mean_m(cells, 1)))

    total_nonzero = tot > 0
    print("  the total effect of X on Y is positive = %s (%.1f)" % (total_nonzero, tot))

    adjusting_shrinks = dir_ < tot
    print("  adjusting for M shrinks the estimated effect = %s (%.1f < %.1f)" % (adjusting_shrinks, dir_, tot))

    removed_is_indirect = abs((tot - dir_) - 5.0) < 1e-9
    print("  the removed part is the indirect effect through M = %s (%.1f)" % (removed_is_indirect, tot - dir_))

    direct_is_positive_too = dir_ > 0
    print("  a direct effect remains after adjusting (X -> Y directly) = %s (%.1f)" % (direct_is_positive_too, dir_))

    ok = (x_raises_m and total_nonzero and adjusting_shrinks and removed_is_indirect and direct_is_positive_too)
    print("-" * 122)
    print("SELF-TEST %s  x_raises_m=%s  total_nonzero=%s  adjusting_shrinks=%s  removed_is_indirect=%s  direct_is_positive_too=%s"
          % ("PASS" if ok else "FAIL", x_raises_m, total_nonzero, adjusting_shrinks, removed_is_indirect, direct_is_positive_too))
    return ok


def main():
    p = argparse.ArgumentParser(description="Mediator over-adjustment: do not adjust for a mediator (a variable on the causal path from X to Y) when estimating the total effect of X, because holding it fixed blocks the indirect path and understates the effect -- the same adjustment required for a confounder and forbidden for a collider is forbidden for a mediator too, and only the causal role, not the data, tells you which.")
    p.add_argument("--data", action="store_true")
    p.add_argument("--effect", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("cells=%d  Y=10+3X+5M  file=%s  (the cells are a fixture)" % (len(data["cells"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.data:
        data_view(data)
    elif args.effect:
        effect_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
