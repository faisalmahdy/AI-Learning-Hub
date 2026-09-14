"""Mask padding positions in the attention, not just in the loss -- set the pad keys' scores to negative infinity before the softmax, or a real token attends to the filler and averages the pad embedding's value into its own representation.

Batching sequences of different lengths requires padding the short ones up to the batch maximum with a filler token. That filler is not content, but it is not nothing either: a pad token has an embedding, and that embedding flows through the same projections as every real token, producing a key vector and therefore an attention score. The pad's score is usually unremarkable -- there is no reason it should be small -- so it sits in the query's score row looking just like a real token's.

If nothing masks it, the softmax does its job on the whole row, pad included. Some of the query's attention weight lands on the pad position, and the pad value gets averaged into the query's output in proportion to that weight. The token's representation is now a blend of real context and meaningless filler, and because every layer feeds the next, that contamination propagates through the whole stack.

This is a different failure from masking padding out of the loss. Loss masking stops filler tokens from diluting the training signal on the output side; attention masking stops filler from corrupting the representations on the forward-pass side. A model can mask the loss perfectly and still be poisoned in every hidden state if it forgot the attention mask, because the damage happens before the loss is ever computed.

The fix is to set each pad position's pre-softmax score to negative infinity. exp(-inf) is zero, so the softmax gives those positions exactly zero weight, and the remaining weight over the real tokens renormalizes to sum to one. The query then attends only to real content, and no pad value enters its output.

The rule: mask padding positions in attention by setting their key scores to negative infinity before the softmax -- not only in the loss -- because an unmasked pad position receives attention weight and averages its filler value into the query's representation, corrupting every downstream layer; masking gives it zero weight so attention is taken over the real tokens alone.

On this fixture a query scores four key positions, the last of which is padding with a score as high as the top real token. Unmasked, the softmax puts about a quarter of the weight on the pad; masked, the pad gets zero and that weight is redistributed to the real tokens. This computes both.

  --weights   the softmax attention weights over the key positions, without the pad mask and with it
  --leak      how much attention weight lands on padding, and how the real tokens' weights change
  --check     an unmasked pad gets attention weight and leaks its value; masking gives it zero and renormalizes

scores and is_pad are the fixture; the two softmax weightings and the leaked weight are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "padmask.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def softmax(scores):
    """Stable softmax: subtract the max, exponentiate, normalize. -inf scores give zero weight."""
    m = max(s for s in scores if s != float("-inf"))
    exps = [math.exp(s - m) if s != float("-inf") else 0.0 for s in scores]
    total = sum(exps)
    return [e / total for e in exps]


def masked_scores(scores, is_pad):
    """Set every pad position's score to negative infinity before the softmax."""
    return [float("-inf") if pad else s for s, pad in zip(scores, is_pad)]


# ----------------------------------------------------------------- printing

def weights_view(data):
    scores, is_pad = data["scores"], data["is_pad"]
    unmasked = softmax(scores)
    masked = softmax(masked_scores(scores, is_pad))
    print("WEIGHTS — attention weight per key position (last is padding)")
    print("-" * 56)
    print("  position   pad?    unmasked   masked")
    for i, (w0, w1, p) in enumerate(zip(unmasked, masked, is_pad)):
        print("  %-9d  %-6s  %-9.3f  %.3f" % (i, p, w0, w1))
    print("-" * 56)
    print("  unmasked spreads weight onto the pad; masked gives it zero")


def leak_view(data):
    scores, is_pad = data["scores"], data["is_pad"]
    unmasked = softmax(scores)
    masked = softmax(masked_scores(scores, is_pad))
    pad_leak = sum(w for w, p in zip(unmasked, is_pad) if p)
    real_unmasked = sum(w for w, p in zip(unmasked, is_pad) if not p)
    real_masked = sum(w for w, p in zip(masked, is_pad) if not p)
    print("LEAK — attention weight lost to padding")
    print("-" * 52)
    print("  weight on padding (unmasked) = %.3f" % pad_leak)
    print("  weight on real tokens (unmasked) = %.3f" % real_unmasked)
    print("  weight on real tokens (masked)   = %.3f" % real_masked)
    print("-" * 52)
    print("  the pad steals %.0f%% of the attention that should go to real tokens" % (100 * pad_leak))


def check(data):
    print("SELF-TEST — an unmasked pad gets attention weight and leaks its value; masking gives it zero and renormalizes")
    print("-" * 112)
    scores, is_pad = data["scores"], data["is_pad"]
    unmasked = softmax(scores)
    masked = softmax(masked_scores(scores, is_pad))

    pad_weight_unmasked = sum(w for w, p in zip(unmasked, is_pad) if p)
    pad_gets_weight = pad_weight_unmasked > 0.0
    print("  unmasked: the pad position receives attention weight = %s (%.3f)" % (pad_gets_weight, pad_weight_unmasked))

    pad_weight_masked = sum(w for w, p in zip(masked, is_pad) if p)
    pad_zero_masked = pad_weight_masked == 0.0
    print("  masked: the pad position receives zero weight = %s" % pad_zero_masked)

    real_unmasked = sum(w for w, p in zip(unmasked, is_pad) if not p)
    real_diluted = real_unmasked < 1.0 - 1e-12
    print("  unmasked: real tokens share less than all the weight = %s (%.3f)" % (real_diluted, real_unmasked))

    real_masked = sum(w for w, p in zip(masked, is_pad) if not p)
    real_full_masked = abs(real_masked - 1.0) < 1e-9
    print("  masked: real tokens receive all the weight = %s (%.3f)" % (real_full_masked, real_masked))

    both_normalized = abs(sum(unmasked) - 1.0) < 1e-9 and abs(sum(masked) - 1.0) < 1e-9
    print("  both weightings sum to one (valid softmax) = %s" % both_normalized)

    ok = (pad_gets_weight and pad_zero_masked and real_diluted and real_full_masked and both_normalized)
    print("-" * 112)
    print("SELF-TEST %s  pad_gets_weight=%s  pad_zero_masked=%s  real_diluted=%s  real_full_masked=%s  both_normalized=%s"
          % ("PASS" if ok else "FAIL", pad_gets_weight, pad_zero_masked, real_diluted, real_full_masked, both_normalized))
    return ok


def main():
    p = argparse.ArgumentParser(description="Attention padding mask: mask padding positions in attention by setting their key scores to negative infinity before the softmax -- not only in the loss -- because an unmasked pad position receives attention weight and averages its filler value into the query's representation, corrupting every downstream layer; masking gives it zero weight so attention is taken over the real tokens alone.")
    p.add_argument("--weights", action="store_true")
    p.add_argument("--leak", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("key_positions=%d  pad_positions=%d  file=%s  (the scores are a fixture)"
          % (len(data["scores"]), sum(data["is_pad"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.weights:
        weights_view(data)
    elif args.leak:
        leak_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
