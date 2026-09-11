#!/usr/bin/env python3
"""Quantize weights: trade bits for memory -- and watch one outlier wreck the grid.

A model's weights are floats, and floats are expensive: 32 (or 16) bits each. Most
of that precision is wasted, so we quantize -- map the floats onto a small grid of
integers with far fewer bits, storing only the integer codes plus a scale to undo
the mapping. Fewer bits means less memory and faster memory traffic, at the cost of
reconstruction error. This measures that trade, and then the failure that makes
naive quantization fall over on real transformers: a single large-magnitude outlier
weight stretches one global scale so far that every ordinary weight loses almost all
its precision. The fix -- one scale per channel instead of one for the whole tensor --
isolates the outlier and is why per-channel (group-wise) quantization exists.

  --sweep       per-tensor RMSE and memory as the bit width shrinks 8 -> 2
  --outlier     per-tensor vs per-channel error on the ordinary weights, at 4 bits
  --check       affine round-trip is bounded by half a step; more bits help; per-channel wins

Affine quantization: q = round((x - zero) / scale) clamped to [0, 2^bits - 1];
x_hat = zero + q * scale, where scale = (max - min) / (2^bits - 1), zero = min.
Stdlib only. No model, no network. Deterministic.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEIGHTS = HERE / "weights.json"


def load():
    return json.loads(WEIGHTS.read_text(encoding="utf-8"))


# ------------------------------------------------------ the affine quantizer

def quantize(values, bits):
    """Affine per-group quantize/dequantize. Returns (x_hat list, scale, zero)."""
    levels = (1 << bits) - 1
    lo, hi = min(values), max(values)
    scale = (hi - lo) / levels if hi > lo else 1.0
    zero = lo
    x_hat = []
    for x in values:
        q = round((x - zero) / scale)
        q = 0 if q < 0 else (levels if q > levels else q)
        x_hat.append(zero + q * scale)
    return x_hat, scale, zero


def rmse(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))


def max_abs_err(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


# ---------------------------------------------- per-tensor vs per-channel

def per_tensor(channels, bits):
    """One scale for the whole matrix. Returns flat original, flat reconstructed."""
    flat = [w for row in channels for w in row]
    x_hat, _, _ = quantize(flat, bits)
    return flat, x_hat


def per_channel(channels, bits):
    """One scale per row. Returns flat original, flat reconstructed (row order)."""
    flat, recon = [], []
    for row in channels:
        r_hat, _, _ = quantize(row, bits)
        flat.extend(row)
        recon.extend(r_hat)
    return flat, recon


def bulk_only(channels, outlier_channel):
    """Every weight except the row that carries the outlier -- the weights we care about."""
    return [w for i, row in enumerate(channels) for w in row if i != outlier_channel]


def bulk_rmse_per_tensor(data, bits):
    """Quantize the whole tensor with one scale, then score error on the ordinary rows only."""
    channels, oc = data["channels"], data["outlier_channel"]
    flat = [w for row in channels for w in row]
    x_hat, _, _ = quantize(flat, bits)
    orig, recon = [], []
    idx = 0
    for i, row in enumerate(channels):
        for w in row:
            if i != oc:
                orig.append(w)
                recon.append(x_hat[idx])
            idx += 1
    return rmse(orig, recon)


def bulk_rmse_per_channel(data, bits):
    channels, oc = data["channels"], data["outlier_channel"]
    orig, recon = [], []
    for i, row in enumerate(channels):
        r_hat, _, _ = quantize(row, bits)
        if i != oc:
            orig.extend(row)
            recon.extend(r_hat)
    return rmse(orig, recon)


# --------------------------------------------------------------- printing

def sweep_view(data):
    channels = data["channels"]
    n = sum(len(r) for r in channels)
    print("SWEEP — per-tensor quantization: fewer bits, less memory, more error")
    print("-" * 66)
    print("  bits   memory vs fp32   RMSE (all weights)   max abs error")
    for bits in (8, 4, 3, 2):
        flat, x_hat = per_tensor(channels, bits)
        mem = bits / 32.0
        print("  %-6d %4.2fx           %-20.4f %.4f" % (bits, mem, rmse(flat, x_hat), max_abs_err(flat, x_hat)))
    print("-" * 66)
    print("  error climbs as bits fall; note the outlier inflates every row's error.")


def outlier_view(data):
    bits = 4
    pt = bulk_rmse_per_tensor(data, bits)
    pc = bulk_rmse_per_channel(data, bits)
    oc = data["outlier_channel"]
    print("OUTLIER — one scale for the whole tensor vs one scale per channel, at %d bits" % bits)
    print("-" * 66)
    print("  the outlier (48.0) lives in channel %d; we score error on the OTHER rows" % oc)
    print("  per-tensor  bulk RMSE = %.4f   (global scale stretched by the outlier)" % pt)
    print("  per-channel bulk RMSE = %.4f   (outlier isolated to its own row)" % pc)
    print("-" * 66)
    print("  per-channel is %.1fx more accurate on the ordinary weights, same bit width." % (pt / pc))


def check(data):
    print("SELF-TEST — affine round-trip is bounded, more bits help, per-channel beats per-tensor")
    print("-" * 66)
    channels = data["channels"]

    # 1. Affine correctness: reconstruction error <= half a step, per group.
    row = channels[0]
    x_hat, scale, _ = quantize(row, 4)
    bounded = max_abs_err(row, x_hat) <= scale / 2 + 1e-9
    print("  per-group reconstruction error <= scale/2 = %s (%.4f <= %.4f)"
          % (bounded, max_abs_err(row, x_hat), scale / 2))

    # 2. More bits -> lower RMSE (monotone) on the whole tensor.
    errs = [rmse(*per_tensor(channels, b)) for b in (2, 3, 4, 8)]
    monotone = all(errs[i] >= errs[i + 1] for i in range(len(errs) - 1))
    print("  RMSE falls monotonically as bits rise 2->8 = %s (%s)"
          % (monotone, " > ".join("%.3f" % e for e in errs)))

    # 3. Per-channel isolates the outlier: much lower bulk error at the same bits.
    pt = bulk_rmse_per_tensor(data, 4)
    pc = bulk_rmse_per_channel(data, 4)
    per_channel_wins = pc < pt / 5.0
    print("  per-channel bulk RMSE < per-tensor/5 = %s (%.4f vs %.4f)"
          % (per_channel_wins, pc, pt))

    # 4. Determinism.
    det = per_tensor(channels, 4)[1] == per_tensor(channels, 4)[1]

    ok = bounded and monotone and per_channel_wins and det
    print("-" * 66)
    print("SELF-TEST %s  bounded=%s  monotone=%s  per_channel_wins=%s"
          % ("PASS" if ok else "FAIL", bounded, monotone, per_channel_wins))
    return ok


def main():
    p = argparse.ArgumentParser(description="Affine quantization: bits vs error, and the outlier problem.")
    p.add_argument("--sweep", action="store_true")
    p.add_argument("--outlier", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    n = sum(len(r) for r in data["channels"])
    print("weights=%d  channels=%d  file=%s  (weights are a fixture)" % (n, len(data["channels"]), WEIGHTS.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.sweep:
        sweep_view(data)
    elif args.outlier:
        outlier_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
