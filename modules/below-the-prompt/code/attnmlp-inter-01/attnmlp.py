"""A self-attention layer's output is a softmax-weighted average of the value vectors -- a convex combination -- so it always lies within the convex hull of its inputs and can never produce a value the inputs do not already bracket, while the MLP applies a per-token nonlinearity and can leave that range: attention moves information between positions, the MLP computes, and a transformer needs both.

Read the attention formula for what it does to values. Each output is a sum of weight times value, and the weights come from a softmax, so they are all non-negative and sum to one. That makes the output a weighted average of the value vectors -- a convex combination. A weighted average is bounded: it can be no larger than the largest value and no smaller than the smallest. So whatever the attention weights are, the output stays inside the range the inputs span. Attention can route, mix, and select information across positions, but it cannot manufacture a value outside the hull of what it was given, and in particular it cannot compute a nonlinear function of a single token's features.

That is not a limitation to fix; it is a division of labor. The MLP -- a hidden layer with a nonlinearity, then a projection -- is the block that computes per token. Because of the nonlinearity, its output is not a weighted average of its input and can land outside the input range entirely. The MLP is where a token's features are transformed into new features; attention is where tokens share features with each other.

So the common phrase 'attention is where the thinking happens' is backwards about which block computes. Attention communicates; the MLP computes. Strip the MLP out and every layer can only take weighted averages, and stacking weighted averages still gives a weighted average -- no nonlinear function of a single input is reachable at all.

On this fixture the values are 1, 3, 2. Every attention output, for every weighting, lands in [1, 3]. The MLP -- relu(w1*x + b1)*w2 + b2 with w1=1, b1=-2, w2=4 -- maps 3 to 4 (above the range) and 1 to 0 (below it), escaping the hull that bounds attention. This computes both.

  --attend  attention outputs for several weightings, each a weighted average bracketed by the values
  --mlp     the MLP's outputs, which leave the value range attention is confined to
  --check   every attention output lies within the values' range while the MLP produces outputs outside it, and the attention weights are a valid distribution

the values, several score sets, and the MLP parameters are the fixture; every attention weight, output, bracket, and MLP output is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "attnmlp.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def softmax(scores):
    """Attention weights: non-negative and summing to one, so any weighted sum is a convex combination."""
    hi = max(scores)
    exps = [math.exp(s - hi) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def attention_output(values, scores):
    """The attention output: the softmax-weighted average of the value vectors."""
    w = softmax(scores)
    return sum(wi * vi for wi, vi in zip(w, values))


def mlp_output(x, m):
    """A per-token MLP: relu(w1*x + b1)*w2 + b2 -- a nonlinearity, so not a weighted average of inputs."""
    hidden = max(0.0, m["w1"] * x + m["b1"])
    return hidden * m["w2"] + m["b2"]


# ----------------------------------------------------------------- printing

def attend_view(d):
    values = d["values"]
    lo, hi = min(values), max(values)
    print("ATTEND — attention output is a weighted average of values %s" % values)
    print("-" * 64)
    for scores in d["score_sets"]:
        w = softmax(scores)
        out = attention_output(values, scores)
        print("  weights %s  ->  output %.3f   in [%.0f, %.0f]? %s" % (["%.3f" % x for x in w], out, lo, hi, lo <= out <= hi))
    print("-" * 64)
    print("  every output lands inside the values' range -- attention cannot leave the hull")


def mlp_view(d):
    m = d["mlp"]
    values = d["values"]
    lo, hi = min(values), max(values)
    print("MLP — a per-token nonlinearity: relu(%g*x %+g)*%g %+g" % (m["w1"], m["b1"], m["w2"], m["b2"]))
    print("-" * 64)
    for x in d["mlp_inputs"]:
        out = mlp_output(x, m)
        where = "above" if out > hi else ("below" if out < lo else "inside")
        print("  x = %.0f  ->  MLP %.3f   (%s the value range [%.0f, %.0f])" % (x, out, where, lo, hi))
    print("-" * 64)
    print("  the nonlinearity lets the MLP produce values attention never could")


def check(d):
    print("SELF-TEST — every attention output lies within the values' range while the MLP produces outputs outside it, and the attention weights are a valid distribution")
    print("-" * 112)
    values = d["values"]
    lo, hi = min(values), max(values)
    m = d["mlp"]

    attn_outs = [attention_output(values, s) for s in d["score_sets"]]
    attn_in_hull = all(lo <= o <= hi for o in attn_outs)
    print("  every attention output is within [%.0f, %.0f] = %s (%s)" % (lo, hi, attn_in_hull, ["%.3f" % o for o in attn_outs]))

    weights_valid = all(abs(sum(softmax(s)) - 1.0) < 1e-9 and all(w >= 0 for w in softmax(s)) for s in d["score_sets"])
    print("  attention weights are non-negative and sum to 1 (a convex combination) = %s" % weights_valid)

    mlp_outs = [mlp_output(x, m) for x in d["mlp_inputs"]]
    mlp_escapes = any(o > hi or o < lo for o in mlp_outs)
    print("  the MLP produces at least one output outside the value range = %s (%s)" % (mlp_escapes, ["%.3f" % o for o in mlp_outs]))

    mlp_both_sides = any(o > hi for o in mlp_outs) and any(o < lo for o in mlp_outs)
    print("  the MLP escapes the hull on both sides (above and below) = %s" % mlp_both_sides)

    ok = (attn_in_hull and weights_valid and mlp_escapes and mlp_both_sides)
    print("-" * 112)
    print("SELF-TEST %s  attn_in_hull=%s  weights_valid=%s  mlp_escapes=%s  mlp_both_sides=%s"
          % ("PASS" if ok else "FAIL", attn_in_hull, weights_valid, mlp_escapes, mlp_both_sides))
    return ok


def main():
    p = argparse.ArgumentParser(description="Attention communicates, the MLP computes: a self-attention output is a softmax-weighted average of the value vectors, a convex combination bounded by the smallest and largest value, so attention can route information between positions but never produce a value outside the input range or a nonlinear function of a single token; the MLP applies a per-token nonlinearity and can leave that range, which is why a transformer needs both blocks and why 'attention is where the computation happens' is backwards.")
    p.add_argument("--attend", action="store_true")
    p.add_argument("--mlp", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("values=%s  score_sets=%d  file=%s" % (d["values"], len(d["score_sets"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.attend:
        attend_view(d)
    elif args.mlp:
        mlp_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
