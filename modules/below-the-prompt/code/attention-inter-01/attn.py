#!/usr/bin/env python3
"""Self-attention needs a causal mask, or a language model reads its own answer.

Attention lets each position mix in information from other positions, weighted by
how relevant they are. For a language model that predicts the next token, that is
a trap: if position i is allowed to attend to position i+1, its representation
already contains the token it is supposed to predict, so training accuracy is
perfect and the model learns nothing. The fix is a causal mask -- forbid every
position from attending to any later position, before the softmax. This builds
scaled dot-product self-attention in plain Python and measures the leak: without
the mask each position spends real attention weight on its own future; with it,
zero.

  --weights [mask]   the attention matrix, unmasked or masked (who attends to whom)
  --leak             future-attention mass per position, unmasked vs masked
  --readout          reconstruct how much of token i+1 leaks into position i's output
  --check            unmasked attends to the future; the mask drives future mass to 0

Stdlib only (math). No numpy, no model -- token vectors are a fixture and the
matrices are hand-multiplied so every step is visible. Deterministic.
"""
import argparse
import json
import sys
from math import exp, sqrt
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEQ = HERE / "seq.json"

NEG_INF = float("-inf")


def load():
    data = json.loads(SEQ.read_text(encoding="utf-8"))
    return data["tokens"], data["emb"]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def softmax(row):
    m = max(v for v in row if v != NEG_INF)
    exps = [0.0 if v == NEG_INF else exp(v - m) for v in row]
    s = sum(exps)
    return [e / s for e in exps]


# ------------------------------------------------------------- attention itself

def scores(emb):
    """Scaled dot-product scores: how much position i wants position j, scaled by
    sqrt(dim) so the softmax does not saturate."""
    d = len(emb[0])
    n = len(emb)
    return [[dot(emb[i], emb[j]) / sqrt(d) for j in range(n)] for i in range(n)]


def apply_mask(sc):
    """Causal mask: position i may not attend to any j > i. Set those scores to
    -inf BEFORE the softmax so they get exactly zero weight."""
    n = len(sc)
    return [[sc[i][j] if j <= i else NEG_INF for j in range(n)] for i in range(n)]


def attention(emb, masked):
    sc = scores(emb)
    if masked:
        sc = apply_mask(sc)
    weights = [softmax(row) for row in sc]
    out = []
    for i in range(len(emb)):
        out.append([sum(weights[i][j] * emb[j][k] for j in range(len(emb)))
                    for k in range(len(emb[0]))])
    return weights, out


# ---------------------------------------------------------------- the leak metric

def future_mass(weights):
    """Per position, the total attention weight spent on later positions -- the
    fraction of its representation that came from the future."""
    n = len(weights)
    return [sum(weights[i][j] for j in range(i + 1, n)) for i in range(n)]


def leak_into(emb, out, i):
    """How much of token i+1's vector shows up in position i's output -- a cosine
    between position i's attention output and the next token's embedding."""
    if i + 1 >= len(emb):
        return 0.0
    a, b = out[i], emb[i + 1]
    na, nb = sqrt(dot(a, a)), sqrt(dot(b, b))
    return dot(a, b) / (na * nb) if na and nb else 0.0


# ------------------------------------------------------------------- printing

def weights_view(tokens, emb, masked):
    weights, _ = attention(emb, masked)
    print("ATTENTION WEIGHTS — %s   (row i attends to column j)" % ("masked" if masked else "UNMASKED"))
    print("-" * 60)
    print("        " + "  ".join("%-5s" % t for t in tokens))
    for i, t in enumerate(tokens):
        print("  %-5s " % t + "  ".join("%.2f " % weights[i][j] for j in range(len(tokens))))
    print("-" * 60)
    print("  upper triangle is the future; masked keeps it exactly 0.00.")


def leak_view(tokens, emb):
    wu, _ = attention(emb, masked=False)
    wm, _ = attention(emb, masked=True)
    fu, fm = future_mass(wu), future_mass(wm)
    print("FUTURE MASS — attention weight each position spends on later tokens")
    print("-" * 60)
    print("  position   unmasked   masked")
    for i, t in enumerate(tokens):
        print("  %-9s  %.3f      %.3f" % (t, fu[i], fm[i]))
    print("-" * 60)
    print("  unmasked, early positions pour weight into the future they must not")
    print("  see; masked, every position spends exactly zero on what comes after.")


def readout_view(tokens, emb):
    _, ou = attention(emb, masked=False)
    _, om = attention(emb, masked=True)
    print("NEXT-TOKEN LEAK — how much of token i+1 is in position i's output")
    print("-" * 60)
    print("  position   unmasked   masked")
    for i in range(len(tokens) - 1):
        print("  %-9s  %.3f      %.3f" % (tokens[i], leak_into(emb, ou, i), leak_into(emb, om, i)))
    print("-" * 60)
    print("  unmasked, position i's representation is soaked in the next token --")
    print("  the exact thing a next-token predictor is supposed to guess.")


def check(tokens, emb):
    print("SELF-TEST — unmasked attends to the future; the mask drives it to zero")
    print("-" * 60)
    wu, ou = attention(emb, masked=False)
    wm, om = attention(emb, masked=True)
    fu, fm = future_mass(wu), future_mass(wm)

    leaks = any(f > 1e-6 for f in fu[:-1])
    print("  unmasked future mass is positive for early positions = %s (%s)"
          % (leaks, [round(f, 2) for f in fu]))
    sealed = all(f < 1e-9 for f in fm)
    print("  masked future mass is zero everywhere = %s (%s)" % (sealed, [round(f, 2) for f in fm]))

    # each masked row is a valid distribution over the past only.
    rows_ok = all(abs(sum(wm[i]) - 1.0) < 1e-9 and all(wm[i][j] == 0 for j in range(i + 1, len(tokens)))
                  for i in range(len(tokens)))
    print("  every masked row sums to 1 and is zero on the future = %s" % rows_ok)

    # the next-token leak: unmasked output resembles i+1 more than masked does.
    lu = sum(leak_into(emb, ou, i) for i in range(len(tokens) - 1))
    lm = sum(leak_into(emb, om, i) for i in range(len(tokens) - 1))
    leak_drops = lu > lm
    print("  next-token leak is larger unmasked than masked = %s (%.2f > %.2f)" % (leak_drops, lu, lm))

    det = attention(emb, masked=True)[0] == attention(emb, masked=True)[0]
    ok = leaks and sealed and rows_ok and leak_drops and det
    print("-" * 60)
    print("SELF-TEST %s  leaks=%s  sealed=%s  rows_valid=%s  leak_drops=%s"
          % ("PASS" if ok else "FAIL", leaks, sealed, rows_ok, leak_drops))
    return ok


def main():
    p = argparse.ArgumentParser(description="Scaled dot-product self-attention and the causal mask.")
    p.add_argument("--weights", nargs="?", const="unmasked", choices=["unmasked", "mask"])
    p.add_argument("--leak", action="store_true")
    p.add_argument("--readout", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    tokens, emb = load()
    print("seq_len=%d  dim=%d  file=%s  (token vectors are a fixture)"
          % (len(tokens), len(emb[0]), SEQ.name))
    print("")

    if args.check:
        return 0 if check(tokens, emb) else 1
    if args.weights:
        weights_view(tokens, emb, masked=(args.weights == "mask"))
    elif args.leak:
        leak_view(tokens, emb)
    elif args.readout:
        readout_view(tokens, emb)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
