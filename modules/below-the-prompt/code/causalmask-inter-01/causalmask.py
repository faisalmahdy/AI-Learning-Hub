"""Mask the future before the softmax -- without a causal mask, a next-token model attends to the answer and cheats.

A decoder predicts token i+1 from tokens 0..i. It does this with self-attention: position i builds its output as a
weighted average of the value vectors at the positions it attends to, where the weights come from a softmax over
attention scores. The scores say how much position i wants to look at position j, and the softmax turns them into weights
that sum to 1. Nothing in that machinery, by itself, stops position i from attending to position i+1, i+2, and beyond --
the future tokens. During training that is a disaster hiding as a triumph: the model is trained on complete sequences
(teacher forcing), so the future tokens ARE present, and a position that can attend to them can read the very token it is
supposed to predict. Training loss collapses toward zero, not because the model learned language, but because it learned
to copy the answer from a position it will not have at inference.

The causal mask is the fix, and it is applied at exactly one place: the attention scores, before the softmax. For each
query position i, every future key position j>i has its score set to negative infinity. exp(-inf) is 0, so after the
softmax those future positions carry zero weight, and position i's output is a weighted average of only positions 0..i.
The mask is a property of the architecture, not the data: it must be present at training time (or the model learns to
cheat) and at inference time (though at inference the future simply is not there yet). Getting it wrong -- an off-by-one
that lets position i see i+1, a mask applied after the softmax instead of before, or no mask at all -- produces a model
that scores beautifully in training and generates nonsense, because the ability it relied on vanishes the moment it must
produce tokens one at a time.

On this fixture the scores are all equal, to isolate the mask from any learned attention pattern, and the values are
stand-in token vectors 10, 20, 30, 40. WITHOUT the mask every position outputs 25 -- the average of all four tokens,
including the future ones -- so position 0's output already depends on tokens 20, 30, 40 that come after it. WITH the
mask position i averages only tokens 0..i, giving outputs 10, 15, 20, 25, each depending only on the past and present.
This computes both.

  --weights   the attention weight matrix with and without the mask -- masked is lower-triangular, unmasked is full
  --leak      the fraction of each position's attention that lands on FUTURE tokens, and how the mask changes the output
  --check     the masked weights are lower-triangular with zero future mass; unmasked leaks future mass; the mask changes the output

The scores and values are the fixture; every attention weight and output is computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "causalmask.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def softmax(xs):
    """Softmax over a list; a score of -inf contributes exp(-inf)=0, i.e. zero weight."""
    m = max(v for v in xs if v != float("-inf"))
    e = [math.exp(v - m) if v != float("-inf") else 0.0 for v in xs]
    s = sum(e)
    return [v / s for v in e]


def attention_weights(scores, causal):
    """Per-position softmax attention weights; if causal, mask future positions (j>i) to -inf BEFORE the softmax."""
    n = len(scores)
    rows = []
    for i in range(n):
        masked = [scores[i][j] if (not causal or j <= i) else float("-inf") for j in range(n)]
        rows.append(softmax(masked))
    return rows


def attention_output(weights, values):
    """Each position's output: the weighted average of the value vectors it attends to."""
    n = len(values)
    return [round(sum(weights[i][j] * values[j] for j in range(n)), 4) for i in range(n)]


def future_mass(weights):
    """Per-position total attention weight landing on FUTURE positions (j>i)."""
    n = len(weights)
    return [round(sum(weights[i][j] for j in range(i + 1, n)), 4) for i in range(n)]


# ----------------------------------------------------------------- printing

def weights_view(data):
    scores = data["scores"]
    print("WEIGHTS — attention weight matrix, unmasked vs causal-masked")
    print("-" * 60)
    for label, causal in (("UNMASKED (attends everywhere)", False), ("MASKED (attends only 0..i)", True)):
        W = attention_weights(scores, causal)
        print("  %s:" % label)
        for i, row in enumerate(W):
            print("    pos %d: %s" % (i, [round(w, 3) for w in row]))
    print("-" * 60)
    print("  masked rows are lower-triangular: position i puts zero weight on any j>i.")


def leak_view(data):
    scores, values = data["scores"], data["values"]
    Wu = attention_weights(scores, False)
    Wm = attention_weights(scores, True)
    print("LEAK — attention mass on FUTURE tokens, and the output it corrupts")
    print("-" * 62)
    print("  pos   future mass (unmasked)   future mass (masked)")
    fu, fm = future_mass(Wu), future_mass(Wm)
    for i in range(len(values)):
        print("  %-4d  %-23.3f  %.3f" % (i, fu[i], fm[i]))
    print("-" * 62)
    print("  unmasked output: %s  (every position = 25, it averaged the future too)" % attention_output(Wu, values))
    print("  masked   output: %s  (position i averages only tokens 0..i)" % attention_output(Wm, values))


def check(data):
    print("SELF-TEST — the masked weights are lower-triangular with zero future mass; unmasked leaks future mass; the mask changes the output")
    print("-" * 130)
    scores, values = data["scores"], data["values"]
    n = len(values)
    Wu = attention_weights(scores, False)
    Wm = attention_weights(scores, True)

    lower_triangular = all(Wm[i][j] == 0.0 for i in range(n) for j in range(i + 1, n))
    print("  masked weights are lower-triangular (no weight on j>i) = %s" % lower_triangular)

    masked_no_future = sum(future_mass(Wm)) == 0.0
    print("  masked attention puts zero total mass on the future = %s" % masked_no_future)

    unmasked_leaks = future_mass(Wu)[0] > 0.0
    print("  unmasked attention leaks future mass (position 0) = %s (%.3f)" % (unmasked_leaks, future_mass(Wu)[0]))

    rows_sum_one = all(abs(sum(Wm[i]) - 1.0) < 1e-9 and abs(sum(Wu[i]) - 1.0) < 1e-9 for i in range(n))
    print("  every attention row still sums to 1 (both) = %s" % rows_sum_one)

    out_u, out_m = attention_output(Wu, values), attention_output(Wm, values)
    mask_changes_output = out_u[0] != out_m[0]
    print("  the mask changes position 0's output = %s (%.1f unmasked vs %.1f masked)" % (mask_changes_output, out_u[0], out_m[0]))

    ok = lower_triangular and masked_no_future and unmasked_leaks and rows_sum_one and mask_changes_output
    print("-" * 130)
    print("SELF-TEST %s  lower_triangular=%s  masked_no_future=%s  unmasked_leaks=%s  rows_sum_one=%s  mask_changes_output=%s"
          % ("PASS" if ok else "FAIL", lower_triangular, masked_no_future, unmasked_leaks, rows_sum_one, mask_changes_output))
    return ok


def main():
    p = argparse.ArgumentParser(description="Causal masking: a decoder's self-attention must forbid position i from attending to future positions j>i, done by setting their scores to -inf before the softmax; without the mask, position i attends to the tokens it is meant to predict, so teacher-forced training loss collapses by cheating and the model fails at autoregressive inference.")
    p.add_argument("--weights", action="store_true")
    p.add_argument("--leak", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("values=%s  scores=equal (isolate the mask)  n=%d  file=%s  (the scores and values are a fixture)"
          % (data["values"], len(data["values"]), DATA.name))
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
