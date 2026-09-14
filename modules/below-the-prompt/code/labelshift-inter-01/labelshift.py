"""Shift the labels by one for next-token prediction -- the target at position i is tokens[i+1], not tokens[i]; the same-position objective asks the model to predict a token it can already see, and a copy model aces it while learning nothing.

A language model is trained by teacher forcing: it reads a prefix of tokens and predicts the token that comes next. Turning a sequence into training pairs therefore needs a one-token shift between what the model reads and what it must produce -- the target for the model's output at position i is tokens[i+1]. Concretely, inputs are tokens[:-1] and targets are tokens[1:], so position i means 'given tokens[0..i], predict tokens[i+1]'.

The classic bug is to align the outputs with the inputs at the SAME position: the target for position i is tokens[i]. Now the model is asked to predict the token sitting at its own position -- a token that, under a correct causal mask, it can already see. That objective is solved by the identity function. A model that does nothing but copy its input to its output gets every prediction right and drives the loss to zero, having learned nothing about which token follows which. At generation time such a model can only echo what it was just given.

This failure is easy to miss precisely because it looks like success: the training loss plummets, the accuracy hits 100%, everything seems to be working. But the metric is measuring a task the model cannot fail, not the task you care about. The tell is that a trivial copy baseline -- output = input -- achieves the same perfect score, which means the objective carries no signal.

The one-token shift fixes it by making the target a token the model has not been shown. Predicting tokens[i+1] from tokens[0..i] cannot be done by copying, so a copy model drops to chance and only a model that actually learns the sequence's structure scores well. The shift is what turns 'repeat what you see' into 'predict what comes next'.

The rule: shift the targets one position ahead of the inputs for next-token training -- target[i] = tokens[i+1] -- because aligning the target with the same position asks the model to predict a token it can already see, an objective a copy model solves perfectly while learning nothing; this is separate from the causal mask, which controls attention, not the prediction target.

On this fixture a copy model (output = its input token) scores a perfect 100% under the same-position alignment and only chance under the shifted alignment, because only the shift makes the target a token the model was not shown. This computes both.

  --align   the input->target pairs under same-position vs shifted-by-one alignment
  --score   a copy model's accuracy on each alignment -- perfect on same-position, chance on shifted
  --check   the same-position objective is aced by copying; the one-token shift makes it a real prediction

tokens is the fixture; the alignments and the copy model's accuracy on each are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "labelshift.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def same_position(tokens):
    """The buggy alignment: the target at position i is tokens[i] -- the token already visible there."""
    return list(zip(tokens, tokens))


def shifted(tokens):
    """The correct alignment: the target at position i is tokens[i+1] -- the next token."""
    return list(zip(tokens[:-1], tokens[1:]))


def copy_accuracy(pairs):
    """A copy model outputs its input token; how often does that equal the target?"""
    if not pairs:
        return 0.0
    correct = sum(1 for inp, tgt in pairs if inp == tgt)
    return correct / len(pairs)


# ----------------------------------------------------------------- printing

def align_view(data):
    tokens = data["tokens"]
    print("ALIGN — input -> target pairs under each alignment")
    print("-" * 56)
    print("  same-position (target = tokens[i], the visible token):")
    print("    %s" % same_position(tokens))
    print("  shifted-by-one (target = tokens[i+1], the next token):")
    print("    %s" % shifted(tokens))
    print("-" * 56)
    print("  same-position makes every target equal its own input; the shift makes it the next token")


def score_view(data):
    tokens = data["tokens"]
    sp, sh = same_position(tokens), shifted(tokens)
    print("SCORE — a copy model (output = input token) on each alignment")
    print("-" * 56)
    print("  same-position   copy accuracy = %.0f%%  (%d/%d)"
          % (100 * copy_accuracy(sp), sum(i == t for i, t in sp), len(sp)))
    print("  shifted-by-one  copy accuracy = %.0f%%  (%d/%d)"
          % (100 * copy_accuracy(sh), sum(i == t for i, t in sh), len(sh)))
    print("-" * 56)
    print("  copying aces the buggy objective and fails the real one -- the shift carries the signal")


def check(data):
    print("SELF-TEST — the same-position objective is aced by copying; the one-token shift makes it a real prediction")
    print("-" * 112)
    tokens = data["tokens"]
    sp, sh = same_position(tokens), shifted(tokens)

    same_target_equals_input = all(inp == tgt for inp, tgt in sp)
    print("  same-position: every target equals its own input token = %s" % same_target_equals_input)

    copy_aces_same = copy_accuracy(sp) == 1.0
    print("  same-position: a copy model scores a perfect 100%% = %s" % copy_aces_same)

    shifted_target_is_next = all(tgt == tokens[i + 1] for i, (inp, tgt) in enumerate(sh))
    print("  shifted: every target is the next token tokens[i+1] = %s" % shifted_target_is_next)

    copy_fails_shifted = copy_accuracy(sh) < 1.0
    print("  shifted: the copy model no longer scores perfectly = %s (%.0f%%)"
          % (copy_fails_shifted, 100 * copy_accuracy(sh)))

    shift_carries_signal = copy_accuracy(sh) < copy_accuracy(sp)
    print("  the shift lowers the copy baseline (so it carries signal) = %s" % shift_carries_signal)

    ok = (same_target_equals_input and copy_aces_same and shifted_target_is_next
          and copy_fails_shifted and shift_carries_signal)
    print("-" * 112)
    print("SELF-TEST %s  same_target_equals_input=%s  copy_aces_same=%s  shifted_target_is_next=%s  copy_fails_shifted=%s  shift_carries_signal=%s"
          % ("PASS" if ok else "FAIL", same_target_equals_input, copy_aces_same,
             shifted_target_is_next, copy_fails_shifted, shift_carries_signal))
    return ok


def main():
    p = argparse.ArgumentParser(description="Label shift: shift the targets one position ahead of the inputs for next-token training -- target[i] = tokens[i+1] -- because aligning the target with the same position asks the model to predict a token it can already see, an objective a copy model solves perfectly while learning nothing; this is separate from the causal mask, which controls attention, not the prediction target.")
    p.add_argument("--align", action="store_true")
    p.add_argument("--score", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tokens=%s  file=%s  (the token sequence is a fixture)" % (data["tokens"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.align:
        align_view(data)
    elif args.score:
        score_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
