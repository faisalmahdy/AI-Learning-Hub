"""Divide the attention logits by sqrt(d_k), or the softmax saturates as the head grows and gradients die.

Attention scores a query against each key with a dot product, then softmaxes the scores into weights.
The dot product of two d-dimensional vectors is a sum of d terms, so its magnitude grows with d: for
vectors with unit-scale entries the score has variance about d and a spread of about sqrt(d). Feed
scores that swing over +/- sqrt(d) into a softmax and, as d climbs, the largest score runs away from
the rest, the softmax collapses onto it, and the weights become nearly one-hot -- attention stops
attending and just picks the argmax. Worse, softmax gradients vanish where it saturates, so the head
can no longer learn which key to prefer.

The fix in "Attention Is All You Need" is one factor: divide every score by sqrt(d_k) before the
softmax. That rescales the spread back to about 1 no matter how large the head is, keeping the weight
distribution soft and its gradients alive. This builds one query and eight keys with deterministic
+/-1 entries, computes the attention weights with and without the 1/sqrt(d_k) scale at head sizes 4,
16, 64, 256, and measures the softmax entropy (how spread out the weights are) and the top weight at
each. Unscaled, the entropy collapses toward zero and the top weight toward one as the head grows;
scaled, both hold steady.

  --logits     the raw dot-product scores at each head size, and their spread
  --weights    the softmax entropy and top weight, unscaled vs scaled, as d_k grows
  --check      unscaled attention saturates as d_k grows; the 1/sqrt(d_k) scale keeps it soft

The query and key vectors are generated deterministically; every score and weight is computed. Stdlib.
"""
import argparse
import math
import sys
from pathlib import Path

HEAD_SIZES = [4, 16, 64, 256]
NUM_KEYS = 8


def gen(seed, n):
    """Deterministic +/-1 vector of length n from a small LCG -- reproducible, zero-mean, unit-scale."""
    x = (seed * 2654435761 + 12345) & 0x7FFFFFFF
    out = []
    for _ in range(n):
        x = (1103515245 * x + 12345) & 0x7FFFFFFF
        out.append(1.0 if (x >> 16) & 1 else -1.0)
    return out


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


# ------------------------------------------------------------- softmax and its spread

def softmax(scores):
    m = max(scores)
    exps = [math.exp(s - m) for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def entropy(weights):
    """Shannon entropy in nats -- high means the weights are spread over many keys, 0 means one-hot."""
    return round(-sum(w * math.log(w) for w in weights if w > 0), 4)


def logits(d, scale):
    """The NUM_KEYS attention scores for one query at head size d; scale=True divides by sqrt(d)."""
    q = gen(0, d)
    raw = [dot(q, gen(j + 1, d)) for j in range(NUM_KEYS)]
    if scale:
        raw = [s / math.sqrt(d) for s in raw]
    return raw


# ----------------------------------------------------------------- printing

def logits_view():
    print("LOGITS — raw dot-product scores for one query vs %d keys, per head size" % NUM_KEYS)
    print("-" * 62)
    for d in HEAD_SIZES:
        raw = logits(d, scale=False)
        spread = max(raw) - min(raw)
        print("  d_k=%3d  scores %-38s spread %.1f" % (d, [int(s) for s in raw], spread))
    print("-" * 62)
    print("  the spread of the scores grows with the head size, roughly like sqrt(d_k).")


def weights_view():
    max_ent = math.log(NUM_KEYS)
    print("WEIGHTS — softmax entropy (max %.3f) and top weight, unscaled vs 1/sqrt(d_k) scaled" % max_ent)
    print("-" * 68)
    print("  d_k     unscaled: entropy  top      scaled: entropy  top")
    for d in HEAD_SIZES:
        wu = softmax(logits(d, scale=False))
        ws = softmax(logits(d, scale=True))
        print("  %3d               %.3f   %.3f              %.3f   %.3f"
              % (d, entropy(wu), max(wu), entropy(ws), max(ws)))
    print("-" * 68)
    print("  unscaled entropy collapses and the top weight runs to 1; scaled, both hold.")


def check():
    print("SELF-TEST — unscaled attention saturates as d_k grows; the 1/sqrt(d_k) scale keeps it soft")
    print("-" * 78)
    max_ent = math.log(NUM_KEYS)

    small, large = HEAD_SIZES[0], HEAD_SIZES[-1]
    ent_unscaled_small = entropy(softmax(logits(small, scale=False)))
    ent_unscaled_large = entropy(softmax(logits(large, scale=False)))
    unscaled_collapses = ent_unscaled_large < ent_unscaled_small / 2
    print("  unscaled entropy collapses as d_k grows = %s (d=%d: %.3f -> d=%d: %.3f)"
          % (unscaled_collapses, small, ent_unscaled_small, large, ent_unscaled_large))

    top_unscaled_large = max(softmax(logits(large, scale=False)))
    unscaled_near_onehot = top_unscaled_large > 0.9
    print("  at the largest head the unscaled top weight is near one = %s (%.3f)"
          % (unscaled_near_onehot, top_unscaled_large))

    ents_scaled = [entropy(softmax(logits(d, scale=True))) for d in HEAD_SIZES]
    scaled_stays_soft = all(e > 0.6 * max_ent for e in ents_scaled)
    print("  scaled entropy stays soft at every head size = %s (min %.3f of max %.3f)"
          % (scaled_stays_soft, min(ents_scaled), max_ent))

    top_scaled_large = max(softmax(logits(large, scale=True)))
    scaled_beats_unscaled = top_scaled_large < top_unscaled_large
    print("  scaling keeps the top weight far below the unscaled one = %s (%.3f vs %.3f)"
          % (scaled_beats_unscaled, top_scaled_large, top_unscaled_large))

    ok = unscaled_collapses and unscaled_near_onehot and scaled_stays_soft and scaled_beats_unscaled
    print("-" * 78)
    print("SELF-TEST %s  unscaled_collapses=%s  unscaled_near_onehot=%s  scaled_stays_soft=%s  scaled_beats_unscaled=%s"
          % ("PASS" if ok else "FAIL", unscaled_collapses, unscaled_near_onehot, scaled_stays_soft, scaled_beats_unscaled))
    return ok


def main():
    p = argparse.ArgumentParser(description="Divide attention logits by sqrt(d_k) to keep the softmax soft.")
    p.add_argument("--logits", action="store_true")
    p.add_argument("--weights", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    print("head_sizes=%s  keys=%d  (query and keys are generated deterministically)" % (HEAD_SIZES, NUM_KEYS))
    print("")

    if args.check:
        return 0 if check() else 1
    if args.logits:
        logits_view()
    elif args.weights:
        weights_view()
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
