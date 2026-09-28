"""ALiBi encodes position as a distance-proportional penalty on the attention scores, not a vector added to the tokens -- so it biases attention toward recent tokens and, because the penalty depends only on the query-key distance, it is defined at any length and the model runs past its training length where a learned absolute position embedding has no vector at all.

Standard attention scores every key with a query by a dot product and softmaxes. Position has to enter somewhere. Learned absolute position embeddings add a per-position vector to each token, which means a lookup table with one row per position the model was trained on -- and no row for a position it never saw.

ALiBi puts position in a different place: it subtracts slope*(query_pos - key_pos) from each attention score before the softmax. A key one step back loses a little, a key many steps back loses a lot, so with the raw scores equal the softmax concentrates on the nearest keys. Position is now a recency bias baked into the scores, with a single per-head slope and nothing learned per position.

Two things follow from the bias being a fixed linear function of distance. First, it favors recent tokens by construction -- the penalty grows with distance, so near keys keep more of their score. Second, and this is the payoff, it extrapolates. The bias for a distance of 500 is just slope times 500, an ordinary number, whether or not the model ever trained on a sequence that long. The bias depends only on the gap between query and key, not on their absolute positions, so it is translation-invariant and well-defined at any length. A model with learned absolute position embeddings, by contrast, simply has no embedding for a position beyond its trained range.

On this fixture a head with slope 0.5, trained to length 4, attends at a position inside that range and at a position far beyond it. The attention prefers recent keys; the bias for a far distance is a finite number; and the learned absolute table has no row for the far position. This computes all of it.

  --attend       the ALiBi biases at a trained position and the recency-weighted attention they produce
  --extrapolate  the bias is the same for equal distances at any position and is defined far past training, where the absolute table is not
  --check        ALiBi favors recent tokens, its bias is translation-invariant and defined at any distance, and it needs no per-position table the way absolute embeddings do

slope, train_len, and the two query positions are the fixture; the biases, attention weights, and the absolute table's coverage are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "alibi.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def alibi_bias(query_pos, key_pos, slope):
    """The penalty ALiBi adds to a score: -slope times the query-key distance (depends only on the gap)."""
    return -slope * (query_pos - key_pos)


def attention_weights(query_pos, slope):
    """Softmax over the biased scores (raw scores taken equal), for causal keys 0..query_pos."""
    biased = [alibi_bias(query_pos, k, slope) for k in range(query_pos + 1)]
    hi = max(biased)
    exps = [math.exp(b - hi) for b in biased]
    total = sum(exps)
    return [e / total for e in exps]


def absolute_position_defined(pos, train_len):
    """A learned absolute position embedding exists only for positions seen in training (0..train_len-1)."""
    return pos < train_len


# ----------------------------------------------------------------- printing

def attend_view(data):
    q, slope = data["query_pos"], data["slope"]
    weights = attention_weights(q, slope)
    print("ATTEND — ALiBi biases and attention at query position %d (raw scores equal)" % q)
    print("-" * 64)
    for k in range(q + 1):
        print("  key %d: distance %d  bias %+.2f  attention %.3f" % (k, q - k, alibi_bias(q, k, slope), weights[k]))
    print("-" * 64)
    print("  the nearest key gets the most weight, the farthest the least -- a recency bias")


def extrapolate_view(data):
    q, fq, slope, tl = data["query_pos"], data["far_query_pos"], data["slope"], data["train_len"]
    print("EXTRAPOLATE — the same bias at any position, and the far position's coverage")
    print("-" * 64)
    print("  bias(q=%d, k=%d) [dist 2] = %+.2f" % (q, q - 2, alibi_bias(q, q - 2, slope)))
    print("  bias(q=%d, k=%d) [dist 2] = %+.2f   (same distance, same bias)" % (fq, fq - 2, alibi_bias(fq, fq - 2, slope)))
    print("  bias at distance %d (far past train_len %d) = %+.2f   (a finite, ordinary number)" % (fq, tl, alibi_bias(fq, 0, slope)))
    print("  learned absolute embedding exists at position %d? %s" % (fq, absolute_position_defined(fq, tl)))
    print("-" * 64)
    print("  ALiBi is defined at any distance; the absolute table has no row for the far position")


def check(data):
    print("SELF-TEST — ALiBi favors recent tokens, its bias is translation-invariant and defined at any distance, and it needs no per-position table the way absolute embeddings do")
    print("-" * 112)
    q, fq, slope, tl = data["query_pos"], data["far_query_pos"], data["slope"], data["train_len"]
    weights = attention_weights(q, slope)

    favors_recent = weights[-1] > weights[0]
    print("  the nearest key gets more attention than the farthest = %s (%.3f > %.3f)" % (favors_recent, weights[-1], weights[0]))

    translation_invariant = alibi_bias(q, q - 2, slope) == alibi_bias(fq, fq - 2, slope)
    print("  the bias depends only on distance, not absolute position = %s (%.2f == %.2f)" % (translation_invariant, alibi_bias(q, q - 2, slope), alibi_bias(fq, fq - 2, slope)))

    defined_at_far = math.isfinite(alibi_bias(fq, 0, slope))
    print("  the bias is a finite number at a distance far past training = %s (%.2f at distance %d)" % (defined_at_far, alibi_bias(fq, 0, slope), fq))

    absolute_missing_far = not absolute_position_defined(fq, tl)
    print("  a learned absolute embedding has no vector for the far position = %s (position %d, train_len %d)" % (absolute_missing_far, fq, tl))

    local_pattern_invariant = [alibi_bias(q, q - d, slope) for d in range(tl)] == [alibi_bias(fq, fq - d, slope) for d in range(tl)]
    print("  the last-%d-key bias pattern is identical at both positions = %s" % (tl, local_pattern_invariant))

    ok = (favors_recent and translation_invariant and defined_at_far
          and absolute_missing_far and local_pattern_invariant)
    print("-" * 112)
    print("SELF-TEST %s  favors_recent=%s  translation_invariant=%s  defined_at_far=%s  absolute_missing_far=%s  local_pattern_invariant=%s"
          % ("PASS" if ok else "FAIL", favors_recent, translation_invariant, defined_at_far,
             absolute_missing_far, local_pattern_invariant))
    return ok


def main():
    p = argparse.ArgumentParser(description="ALiBi (Attention with Linear Biases): encode position by subtracting a per-head slope times the query-key distance from each attention score before the softmax, rather than adding a learned per-position embedding to the tokens -- so attention is biased toward recent tokens and, because the bias depends only on distance, it is defined at any length and the model extrapolates past its training length, where an absolute position embedding has no vector.")
    p.add_argument("--attend", action="store_true")
    p.add_argument("--extrapolate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("slope=%.1f  train_len=%d  query_pos=%d  far_query_pos=%d  file=%s"
          % (data["slope"], data["train_len"], data["query_pos"], data["far_query_pos"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.attend:
        attend_view(data)
    elif args.extrapolate:
        extrapolate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
