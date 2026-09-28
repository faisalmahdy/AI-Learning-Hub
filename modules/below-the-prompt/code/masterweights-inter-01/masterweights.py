"""Keep fp32 master weights in mixed precision -- a small update added straight to an fp16 weight underflows (it is below the weight's representable step), so w + update rounds back to w and the parameter never moves; accumulate the update in an fp32 master copy instead.

Mixed-precision training runs the forward and backward passes in fp16 for speed and memory, and this module is about a trap on the update, separate from the well-known gradient-underflow trap. Even when the gradient is perfectly good, the optimizer's step -- learning rate times gradient -- is usually tiny compared to the weight it is applied to. A weight near 1.0 with an update of a few ten-thousandths is asking fp16 to represent a change far smaller than its resolution at that magnitude.

fp16 has about ten mantissa bits, so near a value of 1.0 the gap between one representable number and the next (the ulp) is about 2^-10, roughly one thousandth. An update of 0.0004 is less than half that gap, so w + update rounds to the nearest fp16 value, which is w itself. The addition happens, the result rounds away, and the weight is unchanged -- not this step, and not any step, because every step the same too-small update rounds off. The parameter silently stops learning.

The fix is to keep the master copy of each weight in fp32. The optimizer applies its update to the fp32 master, where 0.0004 is represented exactly and accumulates step after step; the fp16 weight used in the fast passes is just a rounded snapshot of the master. One step still looks like no change in fp16, but the master keeps the true running total, and after enough steps that total grows past the fp16 ulp and the snapshot finally moves. The small updates are not lost; they are banked in fp32 until they are large enough to show.

This is the second pillar of mixed-precision training, alongside loss scaling: loss scaling keeps small gradients from underflowing to zero, and fp32 master weights keep small updates from rounding off against a large weight. Both are needed; each fixes a different underflow.

The rule: keep the master weights in fp32 and apply the optimizer update there, using fp16 only for the forward and backward passes -- because a small update added directly to an fp16 weight is below the weight's representable step and rounds away every step, while an fp32 master accumulates it faithfully until it is large enough to survive rounding.

On this fixture an update of 0.0004 per step is applied to a weight of 1.0 for 100 steps. Added directly in fp16 it rounds off every step and the weight stays 1.0; accumulated in an fp32 master it reaches 1.04, and the fp16 snapshot then moves too. This computes both.

  --step      the fate of a single update: fp16 direct (rounds away) vs fp32 master (accumulates)
  --train     the weight after all steps under direct-fp16 updates vs fp32-master updates
  --check     a small update underflows against an fp16 weight every step; an fp32 master banks it until it shows

weight, update, steps, and mantissa_bits are the fixture; the fp16 rounding and the two training paths are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "masterweights.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def round_fp16(x, mantissa_bits):
    """Round x to the nearest value on the fp16 grid for its magnitude (ulp = 2^(exponent - mantissa_bits))."""
    if x == 0:
        return 0.0
    exponent = math.floor(math.log2(abs(x)))
    ulp = 2.0 ** (exponent - mantissa_bits)
    return round(x / ulp) * ulp


def train_direct(weight, update, steps, mantissa_bits):
    """Apply the update straight to the fp16 weight each step -- the update rounds away."""
    w = round_fp16(weight, mantissa_bits)
    for _ in range(steps):
        w = round_fp16(w + update, mantissa_bits)
    return w


def train_master(weight, update, steps, mantissa_bits):
    """Accumulate the update in an fp32 master; the fp16 weight is a rounded snapshot of it."""
    master = weight  # fp32, full precision
    for _ in range(steps):
        master = master + update
    return master, round_fp16(master, mantissa_bits)


# ----------------------------------------------------------------- printing

def step_view(data):
    w, u, mb = data["weight"], data["update"], data["mantissa_bits"]
    ulp = 2.0 ** (math.floor(math.log2(abs(w))) - mb)
    print("STEP — one update of %.4f applied to a weight of %.1f" % (u, w))
    print("-" * 56)
    print("  fp16 ulp near %.1f = %.6f  (smallest change fp16 can show here)" % (w, ulp))
    print("  direct fp16:  round16(%.1f + %.4f) = %.6f" % (w, u, round_fp16(w + u, mb)))
    print("  fp32 master:  %.1f + %.4f = %.4f" % (w, u, w + u))
    print("-" * 56)
    print("  the update is below the fp16 step, so direct rounds it away; the master keeps it")


def train_view(data):
    w, u, s, mb = data["weight"], data["update"], data["steps"], data["mantissa_bits"]
    direct = train_direct(w, u, s, mb)
    master, master_fp16 = train_master(w, u, s, mb)
    print("TRAIN — the weight after %d updates of %.4f" % (s, u))
    print("-" * 56)
    print("  direct fp16 weight       = %.4f  (moved %.4f)" % (direct, direct - w))
    print("  fp32 master weight       = %.4f  (moved %.4f)" % (master, master - w))
    print("  fp16 snapshot of master  = %.4f" % master_fp16)
    print("-" * 56)
    print("  direct never moved; the master banked every update and the snapshot now shows it")


def check(data):
    print("SELF-TEST — a small update underflows against an fp16 weight every step; an fp32 master banks it until it shows")
    print("-" * 116)
    w, u, s, mb = data["weight"], data["update"], data["steps"], data["mantissa_bits"]

    single_update_underflows = round_fp16(w + u, mb) == round_fp16(w, mb)
    print("  a single update rounds back to the same fp16 weight = %s (%.6f)" % (single_update_underflows, round_fp16(w + u, mb)))

    direct = train_direct(w, u, s, mb)
    direct_stuck = direct == round_fp16(w, mb)
    print("  direct fp16: the weight never moves over %d steps = %s (%.4f)" % (s, direct_stuck, direct))

    master, master_fp16 = train_master(w, u, s, mb)
    master_accumulates = abs(master - (w + s * u)) < 1e-9
    print("  fp32 master: the update accumulates faithfully = %s (%.4f)" % (master_accumulates, master))

    master_snapshot_moves = master_fp16 != round_fp16(w, mb)
    print("  the fp16 snapshot of the master has moved = %s (%.4f)" % (master_snapshot_moves, master_fp16))

    master_beats_direct = abs(master_fp16 - w) > abs(direct - w)
    print("  the master path learned and the direct path did not = %s" % master_beats_direct)

    ok = (single_update_underflows and direct_stuck and master_accumulates
          and master_snapshot_moves and master_beats_direct)
    print("-" * 116)
    print("SELF-TEST %s  single_update_underflows=%s  direct_stuck=%s  master_accumulates=%s  master_snapshot_moves=%s  master_beats_direct=%s"
          % ("PASS" if ok else "FAIL", single_update_underflows, direct_stuck,
             master_accumulates, master_snapshot_moves, master_beats_direct))
    return ok


def main():
    p = argparse.ArgumentParser(description="Master weights: keep the master weights in fp32 and apply the optimizer update there, using fp16 only for the forward and backward passes -- because a small update added directly to an fp16 weight is below the weight's representable step and rounds away every step, while an fp32 master accumulates it faithfully until it is large enough to survive rounding.")
    p.add_argument("--step", action="store_true")
    p.add_argument("--train", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("weight=%.1f  update=%.4f  steps=%d  mantissa_bits=%d  file=%s  (these are a fixture)"
          % (data["weight"], data["update"], data["steps"], data["mantissa_bits"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.step:
        step_view(data)
    elif args.train:
        train_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
