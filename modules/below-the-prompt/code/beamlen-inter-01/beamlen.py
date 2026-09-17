"""Normalize a beam-search hypothesis's score by its length, or beam search prefers the shorter sequence -- every token adds another negative log-probability, so a long fluent answer loses to a short generic one on raw total score.

Beam search ranks hypotheses by the product of their token probabilities, which is the sum of the token log-probabilities. Every token probability is at most one, so every log-probability is at most zero, and each additional token can only subtract from the total. A hypothesis's raw score therefore falls monotonically as it grows longer, regardless of how good the tokens are.

That is a bias, not a preference. Two sequences are being compared on a quantity that is contaminated by length: the shorter one starts with an advantage worth one negative term per token it lacks. So beam search, left raw, drifts toward short, terse, generic completions -- and in the extreme toward the empty sequence, whose score is zero, the largest a sum of negative terms can be. The famous symptom is a translation or summarization model that emits a curt fragment when a full sentence was both available and more probable per token.

The fix is to score by the per-token average, not the total: divide the summed log-probability by the sequence length (optionally by length raised to a penalty exponent alpha, to tune how hard length is rewarded). The normalized score does not shrink merely because a sequence is longer, so a sequence that is more probable token for token wins even when it has more tokens.

On this fixture the short candidate 'ok.' is a single token with a low per-token probability of 0.45, while the long candidate is five tokens each at 0.70 -- more fluent at every step. Raw beam picks 'ok.' because one negative term beats five. Length-normalized beam picks the long fluent sequence, because 0.70 per token beats 0.45 per token. This computes both scores.

  --score    each candidate's length, raw summed log-prob, per-token geometric mean, and normalized score
  --decode   the head-to-head: which sequence raw beam returns versus which length-normalized beam returns
  --check    raw beam prefers the shortest while normalized beam prefers the longest, and the longer sequence is the more fluent per token

candidates and their token probabilities are the fixture; the raw and normalized scores are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "beamlen.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def raw_score(cand):
    """Beam's native score: the sum of token log-probabilities (a product of probabilities)."""
    return sum(math.log(p) for p in cand["token_probs"])


def normalized_score(cand, alpha=1.0):
    """Length-normalized score: the raw score divided by length**alpha -- a per-token average at alpha=1."""
    length = len(cand["token_probs"])
    return raw_score(cand) / (length ** alpha)


def per_token_mean(cand):
    """The geometric mean probability per token -- how fluent the sequence is, independent of its length."""
    return math.exp(raw_score(cand) / len(cand["token_probs"]))


def winner(cands, key):
    """The candidate with the highest score under the given scoring function (that is what beam keeps)."""
    return max(cands, key=key)


# ----------------------------------------------------------------- printing

def score_view(data):
    cands = data["candidates"]
    raw_win = winner(cands, raw_score)
    norm_win = winner(cands, normalized_score)
    print("SCORE — each candidate by raw total versus length-normalized")
    print("-" * 72)
    print("  %-22s %3s  %10s  %10s  %12s" % ("candidate", "len", "raw", "per-token", "normalized"))
    for c in cands:
        marks = []
        if c is raw_win:
            marks.append("raw-win")
        if c is norm_win:
            marks.append("norm-win")
        print("  %-22s %3d  %10.4f  %10.4f  %12.4f  %s"
              % (c["label"], len(c["token_probs"]), raw_score(c), per_token_mean(c), normalized_score(c), " ".join(marks)))
    print("-" * 72)
    print("  raw score falls with length; the normalized score is a per-token average that does not")


def decode_view(data):
    cands = data["candidates"]
    raw_win = winner(cands, raw_score)
    norm_win = winner(cands, normalized_score)
    print("DECODE — what each beam returns")
    print("-" * 72)
    print("  raw beam returns        : %r  (len %d, per-token %.2f)" % (raw_win["label"], len(raw_win["token_probs"]), per_token_mean(raw_win)))
    print("  normalized beam returns : %r  (len %d, per-token %.2f)" % (norm_win["label"], len(norm_win["token_probs"]), per_token_mean(norm_win)))
    print("-" * 72)
    print("  raw beam took the terse %r though the longer answer is more probable token for token" % raw_win["label"])


def check(data):
    print("SELF-TEST — raw beam prefers the shortest while normalized beam prefers the longest, and the longer sequence is the more fluent per token")
    print("-" * 112)
    cands = data["candidates"]
    lengths = [len(c["token_probs"]) for c in cands]
    shortest = cands[lengths.index(min(lengths))]
    longest = cands[lengths.index(max(lengths))]
    raw_win = winner(cands, raw_score)
    norm_win = winner(cands, normalized_score)

    raw_prefers_shortest = raw_win is shortest
    print("  raw beam's winner is the shortest candidate = %s (%r, len %d)" % (raw_prefers_shortest, raw_win["label"], len(raw_win["token_probs"])))

    normalized_prefers_longest = norm_win is longest
    print("  normalized beam's winner is the longest candidate = %s (%r, len %d)" % (normalized_prefers_longest, norm_win["label"], len(norm_win["token_probs"])))

    beams_disagree = raw_win is not norm_win
    print("  the two beams disagree = %s (raw %r vs norm %r)" % (beams_disagree, raw_win["label"], norm_win["label"]))

    longer_is_more_fluent = per_token_mean(longest) > per_token_mean(shortest)
    print("  the longer sequence is more probable per token = %s (%.2f vs %.2f)" % (longer_is_more_fluent, per_token_mean(longest), per_token_mean(shortest)))

    raw_score_falls_with_length = all(
        raw_score({"token_probs": longest["token_probs"][:k]}) > raw_score({"token_probs": longest["token_probs"][:k + 1]})
        for k in range(1, len(longest["token_probs"]))
    )
    print("  each extra token lowers the raw score = %s" % raw_score_falls_with_length)

    ok = (raw_prefers_shortest and normalized_prefers_longest and beams_disagree
          and longer_is_more_fluent and raw_score_falls_with_length)
    print("-" * 112)
    print("SELF-TEST %s  raw_prefers_shortest=%s  normalized_prefers_longest=%s  beams_disagree=%s  longer_is_more_fluent=%s  raw_score_falls_with_length=%s"
          % ("PASS" if ok else "FAIL", raw_prefers_shortest, normalized_prefers_longest, beams_disagree,
             longer_is_more_fluent, raw_score_falls_with_length))
    return ok


def main():
    p = argparse.ArgumentParser(description="Beam length normalization: divide a beam hypothesis's summed log-probability by its length (optionally length**alpha), because raw beam scores are a sum of negative log-probabilities that only shrinks with length, so raw beam prefers the shorter sequence and drifts toward terse, generic, even empty outputs.")
    p.add_argument("--score", action="store_true")
    p.add_argument("--decode", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("candidates=%s  file=%s  (these are a fixture)"
          % ([c["label"] for c in data["candidates"]], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.score:
        score_view(data)
    elif args.decode:
        decode_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
