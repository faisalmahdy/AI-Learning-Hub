"""The DCT is lossless -- quantizing its coefficients is where an image loses detail, and quantizing each block independently is where the blocking artifact comes from, so quantize gently or the block seams show.

JPEG-style compression rewrites each small block of an image as a sum of cosine waves of rising frequency (the discrete cosine transform), then throws away precision. It is easy to blame the transform for the loss, but the transform is exactly invertible: run the DCT and then the inverse DCT and you get the block back to the last bit. Nothing is lost there.

What the transform buys is energy compaction. For smooth content almost all the block's energy lands in the lowest-frequency coefficients -- the DC term (the block's average) and the first alternating term (its gradient) -- while the high-frequency coefficients are near zero. That is the whole reason an image compresses: a handful of coefficients describe the block, and the rest can be dropped cheaply.

The loss enters at quantization. Each coefficient is rounded to a multiple of a step size to save bits. A large step zeroes the small high-frequency coefficients, which blurs fine detail, and coarsely rounds the surviving low-frequency ones. That is a real, chosen trade of quality for size -- but it has a second, sneakier cost. Each block is quantized on its own, so two neighbouring blocks that were part of one smooth gradient round to slightly different reconstructed levels. A discontinuity appears at the boundary between them that was never in the original: the blocking artifact, the 8-pixel grid you see in an over-compressed JPEG.

On this fixture a smooth gradient of 16 samples is split into two 8-sample blocks. Un-quantized, the round trip is exact. A fine step keeps the gradient, with small error and a seam as smooth as the original. A coarse step saves more bits but drives the error up and opens a boundary jump several times the original's smooth step -- visible blocking. This computes all three.

  --transform  the DCT coefficients, the energy compaction, and the lossless (un-quantized) round trip
  --quantize   fine versus coarse quantization: the reconstruction error and the block-boundary jump of each
  --check      the DCT is lossless, coarse quantization loses more detail than fine, and coarse quantization opens a blocking seam the fine step does not

signal, the block size, and the two steps are the fixture; the coefficients, the round trip, the errors, and the seam jumps are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "dctquant.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def dct(block):
    """Forward DCT-II: rewrite the block as amplitudes of cosine waves of frequency 0, 1, 2, ... (orthonormal)."""
    n = len(block)
    out = []
    for k in range(n):
        s = sum(block[i] * math.cos(math.pi * (2 * i + 1) * k / (2 * n)) for i in range(n))
        scale = (1.0 / n) ** 0.5 if k == 0 else (2.0 / n) ** 0.5
        out.append(scale * s)
    return out


def idct(coef):
    """Inverse DCT-III: sum the cosine waves back into samples -- the exact inverse of dct()."""
    n = len(coef)
    out = []
    for i in range(n):
        s = sum(((1.0 / n) ** 0.5 if k == 0 else (2.0 / n) ** 0.5) * coef[k]
                * math.cos(math.pi * (2 * i + 1) * k / (2 * n)) for k in range(n))
        out.append(s)
    return out


def quantize(coef, step):
    """Round each coefficient to a multiple of step -- the lossy operation; step=None means no quantization."""
    if step is None:
        return list(coef)
    return [round(c / step) * step for c in coef]


def compress(signal, block_size, step):
    """DCT each block, quantize its coefficients, inverse-DCT -- JPEG's per-block pipeline, reconstructed."""
    out = []
    for start in range(0, len(signal), block_size):
        block = signal[start:start + block_size]
        out.extend(idct(quantize(dct(block), step)))
    return out


def boundary_jump(signal, block_size):
    """The size of the step across the first block seam -- how discontinuous the reconstruction is there."""
    return abs(signal[block_size] - signal[block_size - 1])


def max_error(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


# ----------------------------------------------------------------- printing

def transform_view(data):
    sig, bs = data["signal"], data["block_size"]
    coef = dct(sig[:bs])
    energy = [c * c for c in coef]
    low = 100.0 * (energy[0] + energy[1]) / sum(energy)
    lossless = compress(sig, bs, None)
    print("TRANSFORM — the DCT, and that it loses nothing on its own")
    print("-" * 64)
    print("  block 0 coefficients (DC, then rising frequency):")
    print("    %s" % [round(c, 2) for c in coef])
    print("  energy in the DC + first AC coefficient = %.1f%%" % low)
    print("  un-quantized round trip max error = %.4f" % max_error(sig, lossless))
    print("-" * 64)
    print("  a smooth block is two coefficients, and DCT->IDCT returns it exactly")


def quantize_view(data):
    sig, bs = data["signal"], data["block_size"]
    fine = compress(sig, bs, data["fine_step"])
    coarse = compress(sig, bs, data["coarse_step"])
    orig_seam = boundary_jump(sig, bs)
    print("QUANTIZE — fine versus coarse, and where each shows")
    print("-" * 64)
    print("  original seam step (samples %d->%d) = %.2f" % (bs - 1, bs, orig_seam))
    print("  fine   step %-3d: max error %6.2f   seam jump %6.2f" % (data["fine_step"], max_error(sig, fine), boundary_jump(fine, bs)))
    print("  coarse step %-3d: max error %6.2f   seam jump %6.2f" % (data["coarse_step"], max_error(sig, coarse), boundary_jump(coarse, bs)))
    print("-" * 64)
    print("  coarse quantization loses more detail AND opens a seam the smooth gradient never had")


def check(data):
    print("SELF-TEST — the DCT is lossless, coarse quantization loses more detail than fine, and coarse quantization opens a blocking seam the fine step does not")
    print("-" * 112)
    sig, bs = data["signal"], data["block_size"]
    coef = dct(sig[:bs])
    energy = [c * c for c in coef]

    lossless_err = max_error(sig, compress(sig, bs, None))
    dct_is_lossless = lossless_err < 1e-9
    print("  DCT -> IDCT with no quantization is exact = %s (max error %.2e)" % (dct_is_lossless, lossless_err))

    energy_compacted = (energy[0] + energy[1]) / sum(energy) > 0.99
    print("  a smooth block's energy sits in its two lowest coefficients = %s (%.1f%%)" % (energy_compacted, 100 * (energy[0] + energy[1]) / sum(energy)))

    fine_err = max_error(sig, compress(sig, bs, data["fine_step"]))
    coarse_err = max_error(sig, compress(sig, bs, data["coarse_step"]))
    coarse_loses_more_detail = coarse_err > fine_err
    print("  coarse quantization loses more detail than fine = %s (%.2f > %.2f)" % (coarse_loses_more_detail, coarse_err, fine_err))

    orig_seam = boundary_jump(sig, bs)
    coarse_seam = boundary_jump(compress(sig, bs, data["coarse_step"]), bs)
    coarse_creates_blocking = coarse_seam > 2 * orig_seam
    print("  coarse quantization opens a blocking seam = %s (jump %.2f vs original %.2f)" % (coarse_creates_blocking, coarse_seam, orig_seam))

    fine_seam = boundary_jump(compress(sig, bs, data["fine_step"]), bs)
    fine_seam_smooth = abs(fine_seam - orig_seam) < orig_seam
    print("  the fine step keeps the seam smooth = %s (jump %.2f near original %.2f)" % (fine_seam_smooth, fine_seam, orig_seam))

    ok = (dct_is_lossless and energy_compacted and coarse_loses_more_detail
          and coarse_creates_blocking and fine_seam_smooth)
    print("-" * 112)
    print("SELF-TEST %s  dct_is_lossless=%s  energy_compacted=%s  coarse_loses_more_detail=%s  coarse_creates_blocking=%s  fine_seam_smooth=%s"
          % ("PASS" if ok else "FAIL", dct_is_lossless, energy_compacted, coarse_loses_more_detail,
             coarse_creates_blocking, fine_seam_smooth))
    return ok


def main():
    p = argparse.ArgumentParser(description="DCT quantization and blocking: the discrete cosine transform is lossless and compacts a smooth block's energy into its lowest coefficients; quantizing those coefficients is the lossy step, and quantizing each block independently makes neighbouring blocks reconstruct to different levels, opening the blocking artifact at the seam -- so quantize gently.")
    p.add_argument("--transform", action="store_true")
    p.add_argument("--quantize", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("signal=%s  block_size=%d  steps=%d/%d  file=%s"
          % (data["signal"], data["block_size"], data["fine_step"], data["coarse_step"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.transform:
        transform_view(data)
    elif args.quantize:
        quantize_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
