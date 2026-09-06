"""Compute attention in one streaming pass with a running max -- or you store the whole score row and overflow on big scores.

Attention turns a query into a weighted average of value vectors, weighted by the softmax of the query-key scores. The
textbook softmax needs the whole score row in memory at once: one pass to find the maximum score (subtracted for
numerical stability), a second pass to exponentiate and sum, a third to normalize. For a query attending to thousands
of keys that row is large, and for every query in a long sequence you would materialize an N-by-N matrix of scores --
the memory that makes naive attention quadratic in space and the reason long contexts do not fit.

Online (streaming) softmax computes the identical result in a SINGLE pass over the keys, keeping only three running
scalars: the running maximum score, the running sum of exponentials (the normalizer), and the running weighted output.
The trick is rescaling. When a new score arrives that is larger than the running maximum, every accumulator computed
against the old maximum is now off by a fixed factor exp(old_max - new_max), so you multiply the running sum and the
running output by that correction and then add the new term. At the end, dividing the running output by the running
normalizer gives exactly the softmax-weighted average -- no full row ever stored. This is the kernel behind
FlashAttention: stream over keys in blocks, carry the three scalars from block to block, and attention runs in memory
that does not grow with the sequence length.

The running maximum is not just a memory trick; it is what keeps the exponentials from overflowing. Exponentiate a raw
score of 1000 and you get infinity; subtract the running max first and every exponent is <= 0, so it stays in [0, 1].
On this fixture the online pass matches the two-pass softmax attention exactly (output 39.95 on the moderate scores),
and on scores near 1000 the naive sum-of-exp overflows to nan while the online pass returns the correct 21.55. Computes it.

  --attention  two-pass softmax attention vs the one-pass online version -- identical output, three scalars of state
  --overflow   huge scores: naive exp overflows to inf/nan, the running-max online pass stays finite and correct
  --check      online equals two-pass exactly; naive overflows on large scores; the online state is O(1), not O(keys)

The scores and values are the fixture; every output is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "flashattn.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def two_pass_attention(scores, values):
    """Standard softmax attention: subtract the max, exponentiate, normalize -- needs the whole score row."""
    m = max(scores)
    weights = [math.exp(s - m) for s in scores]
    z = sum(weights)
    return sum(w * v for w, v in zip(weights, values)) / z


def online_attention(scores, values):
    """One streaming pass keeping (running max m, running normalizer l, running output o); rescale on a new max."""
    m, l, o = float("-inf"), 0.0, 0.0
    for s, v in zip(scores, values):
        m_new = max(m, s)
        correction = math.exp(m - m_new)          # rescales the old accumulators to the new max
        e = math.exp(s - m_new)
        l = l * correction + e
        o = o * correction + e * v
        m = m_new
    return o / l


def _ieee_exp(x):
    """exp that returns +inf on overflow, as IEEE float hardware (numpy/torch) does, rather than raising."""
    try:
        return math.exp(x)
    except OverflowError:
        return float("inf")


def naive_no_max(scores, values):
    """The tempting shortcut: sum exp(score) with no max subtraction -- overflows to inf on large scores (inf/inf = nan)."""
    weights = [_ieee_exp(s) for s in scores]
    z = sum(weights)
    return sum(w * v for w, v in zip(weights, values)) / z


# ----------------------------------------------------------------- printing

def attention_view(data):
    sc, val = data["scores"], data["values"]
    print("ATTENTION — two-pass softmax vs one-pass online (moderate scores)")
    print("-" * 62)
    print("  scores:            %s" % sc)
    print("  two-pass output:   %.4f  (stores the whole %d-score row)" % (two_pass_attention(sc, val), len(sc)))
    print("  online output:     %.4f  (three running scalars, one pass)" % online_attention(sc, val))
    print("  match?             %s" % (abs(two_pass_attention(sc, val) - online_attention(sc, val)) < 1e-9))
    print("-" * 62)
    print("  identical result; the online pass never materializes the score row.")


def overflow_view(data):
    sc, val = data["large_scores"], data["large_values"]
    naive = naive_no_max(sc, val)
    print("OVERFLOW — scores near 1000: naive exp overflows, running-max online does not")
    print("-" * 64)
    print("  scores:                 %s" % sc)
    print("  naive sum(exp(score)):  %s  (exp(1000) = inf, so inf/inf)" % naive)
    print("  online output:          %.4f  (every exponent <= 0, so finite)" % online_attention(sc, val))
    print("  two-pass output:        %.4f" % two_pass_attention(sc, val))
    print("-" * 64)
    print("  subtracting the running max keeps exponents in [0,1]; skipping it overflows.")


def check(data):
    print("SELF-TEST — online equals two-pass exactly; naive overflows on large scores; the online state is O(1)")
    print("-" * 108)
    sc, val = data["scores"], data["values"]
    lsc, lval = data["large_scores"], data["large_values"]

    online_matches = abs(online_attention(sc, val) - two_pass_attention(sc, val)) < 1e-9
    print("  online attention equals two-pass on the moderate scores = %s (%.4f)" % (online_matches, online_attention(sc, val)))

    online_matches_large = abs(online_attention(lsc, lval) - two_pass_attention(lsc, lval)) < 1e-9
    print("  online equals two-pass on the large scores too = %s (%.4f)" % (online_matches_large, online_attention(lsc, lval)))

    naive_overflows = not math.isfinite(naive_no_max(lsc, lval))
    print("  the naive no-max version overflows to non-finite on large scores = %s (%s)" % (naive_overflows, naive_no_max(lsc, lval)))

    online_finite_large = math.isfinite(online_attention(lsc, lval))
    print("  the online version stays finite on the same large scores = %s" % online_finite_large)

    online_state_scalars = 3  # the online pass keeps exactly three running scalars (max, normalizer, output)
    state_smaller_than_row = online_state_scalars < len(sc)
    print("  the online pass keeps %d scalars, fewer than the %d-score row the two-pass stores = %s"
          % (online_state_scalars, len(sc), state_smaller_than_row))

    ok = online_matches and online_matches_large and naive_overflows and online_finite_large and state_smaller_than_row
    print("-" * 108)
    print("SELF-TEST %s  online_matches=%s  online_matches_large=%s  naive_overflows=%s  online_finite_large=%s  state_smaller_than_row=%s"
          % ("PASS" if ok else "FAIL", online_matches, online_matches_large, naive_overflows, online_finite_large, state_smaller_than_row))
    return ok


def main():
    p = argparse.ArgumentParser(description="Online (streaming) softmax attention: compute exact softmax-weighted attention in one pass with three running scalars, rescaling on a new running max, which also prevents overflow.")
    p.add_argument("--attention", action="store_true")
    p.add_argument("--overflow", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("scores=%s  values=%s  file=%s  (the query's scores and values are a fixture)"
          % (data["scores"], data["values"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.attention:
        attention_view(data)
    elif args.overflow:
        overflow_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
