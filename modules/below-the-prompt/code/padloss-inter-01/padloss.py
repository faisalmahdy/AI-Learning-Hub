"""Mask the padding positions out of the loss -- averaging cross-entropy over the padded tensor lets trivial filler tokens dilute the loss and leak gradient.

To train on sequences of different lengths, you batch them into one rectangular tensor, which means padding the shorter sequences with a filler token up to the batch's longest length. Padding is a bookkeeping device: those positions carry no real data, and the model should learn nothing from them. But the loss is computed position by position over the whole tensor, and if you simply average the per-token cross-entropy across every position, you have quietly included the padding. The padding positions get a loss too -- and because the padding token is perfectly predictable (it is always the same filler in the same trailing positions), that loss is small. So the naive average is pulled toward the easy padding, understating the real loss.

The dilution of the reported number is the visible symptom; the real damage is in the gradient. Every padding position that contributes to the loss also contributes a gradient, and that gradient trains the model on the task of predicting filler -- teaching it to spend capacity on positions that will never appear at inference. A batch that is mostly padding (a few long sequences among many short ones) can have most of its gradient signal coming from padding, so the model optimizes the wrong objective and the loss curve misrepresents progress. None of this raises an error; the shapes line up and the numbers look plausible.

The fix is a mask: a 0/1 flag per position marking which are real tokens, computed from each sequence's true length. The loss sums the per-token cross-entropy only where the mask is 1 and divides by the count of real tokens, not by the padded size. Padding positions contribute nothing to the numerator and nothing to the denominator, so they influence neither the reported loss nor the gradient. The mask is cheap -- one comparison per position -- and it is the difference between training on your data and training on your data plus a pile of filler.

The rule: mask padding positions out of the loss -- sum the per-token cross-entropy only over real tokens and divide by the real-token count, using a length-derived 0/1 mask -- rather than averaging over the full padded tensor, because padding is trivially predictable filler whose low loss dilutes the average and whose gradient trains the model to predict positions that never occur at inference.

On this batch, sequence A is length 2 (real losses 2.0, 4.0) padded with two easy positions (losses 1.0, 1.0), and B is length 4 (losses 3.0). The naive mean over all 8 positions is 20/8 = 2.5; the masked mean over the 6 real tokens is 18/6 = 3.0. This computes both.

  --batch    each sequence's real length, its per-position losses, and which positions are padding
  --loss     naive mean over the full padded tensor vs masked mean over real tokens only, and the gradient leaked to padding
  --check    the batch has padding; the naive loss dilutes it and leaks gradient, while masking recovers the correct per-token loss

padded_len and batch are the fixture; every mask, count, and mean is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "padloss.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def mask_for(seq, padded_len):
    """1 for real token positions, 0 for padding, from the sequence's real length."""
    return [1 if i < seq["real_len"] else 0 for i in range(padded_len)]


def naive_loss(batch, padded_len):
    """Average the per-token loss over EVERY padded position (padding included)."""
    total = sum(sum(seq["token_losses"]) for seq in batch)
    count = len(batch) * padded_len
    return total, count, total / count


def masked_loss(batch, padded_len):
    """Sum the per-token loss over real tokens only (mask == 1) and divide by the real-token count."""
    total = 0.0
    count = 0
    for seq in batch:
        m = mask_for(seq, padded_len)
        for loss, keep in zip(seq["token_losses"], m):
            total += loss * keep
            count += keep
    return total, count, total / count


def padding_contribution(batch, padded_len):
    """The total loss the naive average charges to padding positions -- the leaked gradient signal."""
    total = 0.0
    for seq in batch:
        m = mask_for(seq, padded_len)
        for loss, keep in zip(seq["token_losses"], m):
            if keep == 0:
                total += loss
    return total


# ----------------------------------------------------------------- printing

def batch_view(data):
    padded_len, batch = data["padded_len"], data["batch"]
    print("BATCH — each sequence's real length, per-position losses, and mask (padded to %d)" % padded_len)
    print("-" * 66)
    print("  seq  real_len  token_losses          mask (1=real, 0=pad)")
    for seq in batch:
        m = mask_for(seq, padded_len)
        print("  %-3s  %-8d  %-20s  %s" % (seq["id"], seq["real_len"], seq["token_losses"], m))
    print("-" * 66)
    real = sum(seq["real_len"] for seq in batch)
    print("  real tokens = %d ; padded positions = %d ; total = %d" % (real, len(batch) * padded_len - real, len(batch) * padded_len))


def loss_view(data):
    padded_len, batch = data["padded_len"], data["batch"]
    nt, nc, nm = naive_loss(batch, padded_len)
    mt, mc, mm = masked_loss(batch, padded_len)
    print("LOSS — naive (full tensor) vs masked (real tokens only)")
    print("-" * 62)
    print("  naive  mean = %.4f = %.1f / %d  (averages over all padded positions)" % (nm, nt, nc))
    print("  masked mean = %.4f = %.1f / %d  (averages over real tokens only)" % (mm, mt, mc))
    print("-" * 62)
    print("  loss charged to padding by the naive average = %.1f (leaked gradient)" % padding_contribution(batch, padded_len))
    print("  naive understates the true per-token loss by %.4f" % (mm - nm))


def check(data):
    print("SELF-TEST — the batch has padding; the naive loss dilutes it and leaks gradient, while masking recovers the correct per-token loss")
    print("-" * 130)
    padded_len, batch = data["padded_len"], data["batch"]
    nt, nc, nm = naive_loss(batch, padded_len)
    mt, mc, mm = masked_loss(batch, padded_len)
    real = sum(seq["real_len"] for seq in batch)

    batch_has_padding = any(seq["real_len"] < padded_len for seq in batch)
    print("  at least one sequence is padded = %s" % batch_has_padding)

    naive_counts_padding = nc == len(batch) * padded_len and nc > real
    print("  the naive average divides by all padded positions = %s (%d, not the %d real tokens)" % (naive_counts_padding, nc, real))

    masked_counts_real = mc == real
    print("  the masked average divides by the real-token count = %s (%d)" % (masked_counts_real, mc))

    naive_understates = nm < mm
    print("  the naive loss understates the true per-token loss = %s (%.4f < %.4f)" % (naive_understates, nm, mm))

    masked_mean_correct = abs(mm - 3.0) < 1e-9
    print("  the masked loss equals the true mean over real tokens = %s (%.4f == 3.0)" % (masked_mean_correct, mm))

    gradient_leaks_to_padding = padding_contribution(batch, padded_len) > 0
    print("  the naive loss charges nonzero loss to padding (leaked gradient) = %s (%.1f)" % (gradient_leaks_to_padding, padding_contribution(batch, padded_len)))

    ok = batch_has_padding and naive_counts_padding and masked_counts_real and naive_understates and masked_mean_correct and gradient_leaks_to_padding
    print("-" * 130)
    print("SELF-TEST %s  batch_has_padding=%s  naive_counts_padding=%s  masked_counts_real=%s  naive_understates=%s  masked_mean_correct=%s  gradient_leaks_to_padding=%s"
          % ("PASS" if ok else "FAIL", batch_has_padding, naive_counts_padding, masked_counts_real, naive_understates, masked_mean_correct, gradient_leaks_to_padding))
    return ok


def main():
    p = argparse.ArgumentParser(description="Padding loss masking: mask padding positions out of the loss -- sum the per-token cross-entropy only over real tokens and divide by the real-token count, using a length-derived 0/1 mask -- rather than averaging over the full padded tensor, because padding is trivially predictable filler whose low loss dilutes the average and whose gradient trains the model to predict positions that never occur at inference.")
    p.add_argument("--batch", action="store_true")
    p.add_argument("--loss", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("padded_len=%d  sequences=%d  file=%s  (the batch lengths and per-token losses are a fixture)"
          % (data["padded_len"], len(data["batch"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.batch:
        batch_view(data)
    elif args.loss:
        loss_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
