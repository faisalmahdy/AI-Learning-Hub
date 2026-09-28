"""Composite layers in z-order with the 'over' operator -- it is not commutative, so putting the background over the foreground hides the foreground instead of showing it through.

Alpha compositing stacks layers with the Porter-Duff 'over' operator. Placing a top layer over a bottom one gives out_color = (top_color*top_alpha + bottom_color*bottom_alpha*(1 - top_alpha)) / out_alpha, where out_alpha = top_alpha + bottom_alpha*(1 - top_alpha). The crucial factor is (1 - top_alpha): it is the fraction of the pixel the top layer leaves uncovered, and it is what lets the bottom layer show through the top's transparency. It is also what makes the operator asymmetric. The top layer contributes at full strength (weighted by its own alpha); the bottom contributes only through the hole the top leaves. Swap which layer is on top and you swap those roles, and you get a different result.

So 'A over B' and 'B over A' are not the same, and only one of them is correct -- the one that matches the layers' actual z-order, which is in front and which is behind. Compositing is associative (you can combine a stack in any grouping) but not commutative (you cannot reorder the layers), exactly like stacking physical transparencies: the order you lay them down changes what you see.

The bug is easy to hit and its worst form is stark. When the background is opaque, compositing correctly -- foreground over background -- lets the foreground's color mix into the result through its alpha. Compositing backwards -- the opaque background over the foreground -- puts a fully opaque layer on top, and an opaque top layer's (1 - top_alpha) is zero, so the bottom contributes nothing: the background covers everything and the foreground disappears completely. A layer you carefully drew is simply gone, not because it was transparent but because it was composited under an opaque layer instead of over it.

The rule: composite layers in their true z-order with the over operator, because over is not commutative -- 'top over bottom' weights the bottom by (1 - top_alpha), so reversing the order changes the result, and compositing an opaque background over a foreground zeroes the foreground's contribution and hides it entirely.

On this fixture a semi-transparent red foreground over an opaque blue background composites to purple, with the red visible; reversing the order composites the opaque blue over the red and yields pure blue, the foreground gone. This computes both.

  --over      the over operator applied both ways, with the resulting colors
  --order     the correct z-order (foreground visible) vs the reversed one (foreground hidden)
  --check     the over operator is not commutative; reversing the order with an opaque background hides the foreground

fg and bg are the fixture; the composited colors both ways are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "composite.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def over(top, bottom):
    """Porter-Duff 'over': top composited over bottom. Returns (color, alpha)."""
    tc, ta = top["color"], top["alpha"]
    bc, ba = bottom["color"], bottom["alpha"]
    out_a = ta + ba * (1 - ta)
    out_c = [(tc[i] * ta + bc[i] * ba * (1 - ta)) / out_a for i in range(3)]
    return [round(x, 1) for x in out_c], round(out_a, 2)


def contributes(layer_color, result_color):
    """Does the layer's color show up in the result (any channel it has, the result also has)?"""
    return any(layer_color[i] > 0 and result_color[i] > 0 for i in range(3))


# ----------------------------------------------------------------- printing

def over_view(data):
    fg, bg = data["fg"], data["bg"]
    correct = over(fg, bg)
    reversed_ = over(bg, fg)
    print("OVER — the over operator applied both ways")
    print("-" * 60)
    print("  fg=%s@%.1f  bg=%s@%.1f" % (fg["color"], fg["alpha"], bg["color"], bg["alpha"]))
    print("  fg over bg (correct z-order) = color %s alpha %.2f" % correct)
    print("  bg over fg (reversed)        = color %s alpha %.2f" % reversed_)
    print("-" * 60)
    print("  the two orders give different colors — over is not commutative")


def order_view(data):
    fg, bg = data["fg"], data["bg"]
    correct = over(fg, bg)[0]
    reversed_ = over(bg, fg)[0]
    print("ORDER — is the foreground visible in the result?")
    print("-" * 60)
    print("  correct  (fg over bg): %s  foreground visible = %s" % (correct, contributes(fg["color"], correct)))
    print("  reversed (bg over fg): %s  foreground visible = %s" % (reversed_, contributes(fg["color"], reversed_)))
    print("-" * 60)
    print("  the opaque background composited on top erases the foreground entirely")


def check(data):
    print("SELF-TEST — the over operator is not commutative; reversing the order with an opaque background hides the foreground")
    print("-" * 122)
    fg, bg = data["fg"], data["bg"]
    correct = over(fg, bg)[0]
    reversed_ = over(bg, fg)[0]

    over_not_commutative = correct != reversed_
    print("  fg-over-bg differs from bg-over-fg (over is not commutative) = %s (%s vs %s)" % (over_not_commutative, correct, reversed_))

    fg_visible_correct = contributes(fg["color"], correct)
    print("  in the correct order the foreground shows in the result = %s (%s)" % (fg_visible_correct, correct))

    fg_hidden_reversed = not contributes(fg["color"], reversed_)
    print("  in the reversed order the foreground is hidden = %s (%s)" % (fg_hidden_reversed, reversed_))

    bg_opaque = bg["alpha"] == 1.0
    reversed_equals_bg = reversed_ == [round(float(c), 1) for c in bg["color"]]
    print("  the opaque background over the foreground equals the background alone = %s (%s)" % (bg_opaque and reversed_equals_bg, reversed_))

    correct_mixes_both = correct != [round(float(c), 1) for c in bg["color"]] and correct != [round(float(c), 1) for c in fg["color"]]
    print("  the correct order mixes both layers (neither pure) = %s (%s)" % (correct_mixes_both, correct))

    ok = (over_not_commutative and fg_visible_correct and fg_hidden_reversed
          and (bg_opaque and reversed_equals_bg) and correct_mixes_both)
    print("-" * 122)
    print("SELF-TEST %s  over_not_commutative=%s  fg_visible_correct=%s  fg_hidden_reversed=%s  reversed_equals_bg=%s  correct_mixes_both=%s"
          % ("PASS" if ok else "FAIL", over_not_commutative, fg_visible_correct, fg_hidden_reversed, reversed_equals_bg, correct_mixes_both))
    return ok


def main():
    p = argparse.ArgumentParser(description="Alpha compositing order: composite layers in their true z-order with the over operator, because over is not commutative -- 'top over bottom' weights the bottom by (1 - top_alpha), so reversing the order changes the result, and compositing an opaque background over a foreground zeroes the foreground's contribution and hides it entirely.")
    p.add_argument("--over", action="store_true")
    p.add_argument("--order", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("fg=%s@%.1f  bg=%s@%.1f  file=%s  (the layers are a fixture)"
          % (data["fg"]["color"], data["fg"]["alpha"], data["bg"]["color"], data["bg"]["alpha"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.over:
        over_view(data)
    elif args.order:
        order_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
