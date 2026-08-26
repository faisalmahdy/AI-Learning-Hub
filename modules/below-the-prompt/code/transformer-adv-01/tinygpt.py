#!/usr/bin/env python3
"""One transformer layer, end to end -- and the causal mask that makes it a language model.

This is a complete forward pass of a single-layer, single-head transformer, from token
ids to a next-token distribution, in stdlib Python. It ties together the pieces built
across the below-the-prompt track: token embeddings, rotary position (RoPE), scaled
dot-product attention, the residual stream, LayerNorm, an MLP, and a softmax over logits.
Everything is tiny (vocab 6, d_model 4) and the weights are a fixture, so every number is
real and checkable, and you can watch a token turn into a prediction.

The load-bearing detail is the CAUSAL MASK. A language model predicts the next token from
the ones before it, so position i must attend only to positions <= i -- never to the
future. Drop the mask and each position attends to the whole sequence, including tokens
that, at generation time, do not exist yet. The tell is a broken invariance: with the
mask, the prediction at position i is identical whether or not later tokens are present;
without it, appending a future token CHANGES the prediction at i. That is the model
cheating -- reading the answer -- and it is why a mask-less model trains to a low loss and
generates garbage. This runs the pass both ways and measures the broken invariance.

  --forward     the full forward pass on the sequence; the predicted next token
  --attn        the attention weights per position, with vs without the causal mask
  --peek        the causality test: does the position-i prediction depend on future tokens?
  --check       softmax normalizes; LayerNorm standardizes; causal is invariant, unmasked cheats

Stdlib only. Deterministic. Weights are a fixture (untrained).
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "weights.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- linear algebra

def matvec(mat, vec):
    """mat is rows x cols (list of rows); vec is length cols. Returns length rows."""
    return [sum(m * v for m, v in zip(row, vec)) for row in mat]


def vecmat(vec, mat):
    """vec length R times mat (R x C) -> length C. (mat indexed [r][c].)"""
    cols = len(mat[0])
    return [sum(vec[r] * mat[r][c] for r in range(len(vec))) for c in range(cols)]


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def relu(v):
    return [x if x > 0 else 0.0 for x in v]


# ------------------------------------------------------------- transformer pieces

def softmax(xs):
    m = max(xs)
    exps = [math.exp(x - m) for x in xs]
    s = sum(exps)
    return [e / s for e in exps]


def layernorm(v):
    """Standardize to zero mean, unit variance (no learnable affine here)."""
    n = len(v)
    mean = sum(v) / n
    var = sum((x - mean) ** 2 for x in v) / n
    denom = math.sqrt(var + 1e-9)
    return [(x - mean) / denom for x in v]


def rope(vec, pos, theta):
    """Rotate successive 2D pairs of the vector by pos*theta (one frequency here)."""
    out = list(vec)
    for i in range(0, len(vec) - 1, 2):
        c, s = math.cos(pos * theta), math.sin(pos * theta)
        x, y = out[i], out[i + 1]
        out[i], out[i + 1] = x * c - y * s, x * s + y * c
    return out


# ------------------------------------------------------------- attention

def attention(hidden, W, theta, causal):
    """Single-head attention over the sequence `hidden` (list of d_model vectors).

    Returns (outputs, weights): outputs per position, and the attention weight matrix.
    With causal=True, position i attends only to positions <= i.
    """
    n = len(hidden)
    d = len(hidden[0])
    q = [rope(matvec(W["Wq"], h), i, theta) for i, h in enumerate(hidden)]
    k = [rope(matvec(W["Wk"], h), i, theta) for i, h in enumerate(hidden)]
    v = [matvec(W["Wv"], h) for h in hidden]
    scale = 1.0 / math.sqrt(d)
    outputs, weights = [], []
    for i in range(n):
        scores = []
        for j in range(n):
            if causal and j > i:
                scores.append(float("-inf"))  # mask the future
            else:
                scores.append(dot(q[i], k[j]) * scale)
        w = softmax(scores)
        weights.append(w)
        ctx = [sum(w[j] * v[j][c] for j in range(n)) for c in range(d)]
        outputs.append(matvec(W["Wo"], ctx))
    return outputs, weights


# ------------------------------------------------------------- the forward pass

def forward(data, tokens, causal=True):
    """Embed -> attention (+residual, norm) -> MLP (+residual, norm) -> logits per position."""
    W = data
    E = data["E"]
    theta = data["theta"]

    hidden = [list(E[t]) for t in tokens]                      # token embeddings
    attn_out, weights = attention(hidden, W, theta, causal)
    hidden = [layernorm(add(hidden[i], attn_out[i])) for i in range(len(tokens))]  # residual + norm

    mlp = []
    for h in hidden:
        a = relu(vecmat(h, W["W1"]))       # D -> F, relu
        mlp.append(vecmat(a, W["W2"]))     # F -> D
    hidden = [layernorm(add(hidden[i], mlp[i])) for i in range(len(tokens))]       # residual + norm

    logits = [[dot(h, E[t]) for t in range(len(E))] for h in hidden]  # weight-tied unembed
    return logits, weights


def next_token_dist(data, tokens, causal=True):
    """The predicted distribution over the vocab for the position after the last token."""
    logits, _ = forward(data, tokens, causal)
    return softmax(logits[-1])


# ----------------------------------------------------------------- printing

def forward_view(data):
    tokens = data["tokens"]
    vocab = data["vocab"]
    dist = next_token_dist(data, tokens, causal=True)
    pred = max(range(len(dist)), key=lambda t: dist[t])
    print("FORWARD — single-layer transformer, causal (deterministic, untrained weights)")
    print("-" * 66)
    print("  input tokens: %s" % [vocab[t] for t in tokens])
    print("  next-token distribution:")
    for t in range(len(vocab)):
        bar = "#" * int(round(dist[t] * 40))
        print("    %-5s %.3f %s" % (vocab[t], dist[t], bar))
    print("-" * 66)
    print("  predicted next token: '%s' (argmax) -- untrained, so this is just the wiring." % vocab[pred])


def attn_view(data):
    tokens = data["tokens"]
    vocab = data["vocab"]
    _, wc = forward(data, tokens, causal=True)
    _, wu = forward(data, tokens, causal=False)
    print("ATTN — attention weights of the LAST position, causal vs unmasked")
    print("-" * 66)
    print("  positions:      %s" % "  ".join("%-5s" % v for v in [vocab[t] for t in tokens]))
    print("  causal   (last): %s" % "  ".join("%.2f " % x for x in wc[-1]))
    print("  unmasked (last): %s" % "  ".join("%.2f " % x for x in wu[-1]))
    print("-" * 66)
    print("  the last position sees everything either way; the difference shows at EARLIER positions.")


def peek_view(data):
    tokens = data["tokens"]
    vocab = data["vocab"]
    i = 1  # look at the prediction made AT position i (index 1)
    prefix = tokens[: i + 1]                    # the sequence truncated after position i
    full = tokens                               # the full sequence, with future tokens present

    lc_prefix, _ = forward(data, prefix, causal=True)
    lc_full, _ = forward(data, full, causal=True)
    lu_prefix, _ = forward(data, prefix, causal=False)
    lu_full, _ = forward(data, full, causal=False)

    print("PEEK — does the prediction at position %d depend on FUTURE tokens?" % i)
    print("-" * 66)
    print("  prefix (tokens 0..%d): %s      full: %s" % (i, [vocab[t] for t in prefix], [vocab[t] for t in tokens]))
    print("  causal   logits at pos %d, prefix vs full: %s  vs  %s"
          % (i, [round(x, 3) for x in lc_prefix[i]], [round(x, 3) for x in lc_full[i]]))
    print("  unmasked logits at pos %d, prefix vs full: %s  vs  %s"
          % (i, [round(x, 3) for x in lu_prefix[i]], [round(x, 3) for x in lu_full[i]]))
    print("-" * 66)
    print("  causal: identical (the future is invisible). unmasked: different (it peeked).")


def approx_eq(a, b, tol=1e-9):
    return all(abs(x - y) < tol for x, y in zip(a, b))


def check(data):
    print("SELF-TEST — softmax normalizes; LayerNorm standardizes; causal invariant, unmasked cheats")
    print("-" * 66)
    tokens = data["tokens"]

    dist = next_token_dist(data, tokens, causal=True)
    sums_to_one = abs(sum(dist) - 1.0) < 1e-9
    print("  next-token distribution sums to 1 = %s (%.6f)" % (sums_to_one, sum(dist)))

    ln = layernorm([1.0, 2.0, 3.0, 10.0])
    ln_ok = abs(sum(ln) / len(ln)) < 1e-9 and abs((sum(x * x for x in ln) / len(ln)) - 1.0) < 1e-6
    print("  LayerNorm output has ~0 mean and unit variance = %s" % ln_ok)

    # Causality: prediction at position i is invariant to tokens after i (with the mask).
    i = 1
    lc_prefix, _ = forward(data, tokens[: i + 1], causal=True)
    lc_full, _ = forward(data, tokens, causal=True)
    causal_invariant = approx_eq(lc_prefix[i], lc_full[i])
    print("  CAUSAL: position-%d logits unchanged by future tokens = %s" % (i, causal_invariant))

    # Without the mask, the same prediction DOES change when the future is added -- it cheated.
    lu_prefix, _ = forward(data, tokens[: i + 1], causal=False)
    lu_full, _ = forward(data, tokens, causal=False)
    unmasked_cheats = not approx_eq(lu_prefix[i], lu_full[i])
    print("  UNMASKED: position-%d logits change with future tokens (cheating) = %s" % (i, unmasked_cheats))

    ok = sums_to_one and ln_ok and causal_invariant and unmasked_cheats
    print("-" * 66)
    print("SELF-TEST %s  softmax_ok=%s  layernorm_ok=%s  causal_invariant=%s  unmasked_cheats=%s"
          % ("PASS" if ok else "FAIL", sums_to_one, ln_ok, causal_invariant, unmasked_cheats))
    return ok


def main():
    p = argparse.ArgumentParser(description="A single-layer transformer forward pass and the causal mask.")
    p.add_argument("--forward", action="store_true")
    p.add_argument("--attn", action="store_true")
    p.add_argument("--peek", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("vocab=%d  d_model=%d  d_ff=%d  tokens=%s  file=%s  (weights are a fixture)"
          % (len(data["vocab"]), data["d_model"], data["d_ff"], data["tokens"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.forward:
        forward_view(data)
    elif args.attn:
        attn_view(data)
    elif args.peek:
        peek_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
