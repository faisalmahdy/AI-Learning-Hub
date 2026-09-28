"""Scale the loss before the fp16 backward pass, or small gradients underflow to zero and their weights never learn.

Half precision (fp16) makes training faster and halves memory, but it has a narrow range: its smallest
normal value is about 6.1e-5, and anything smaller flushes to zero. Gradients are often that small -- deep
in a network, for rarely-active weights, late in training -- and when a gradient underflows to zero in
fp16, the optimizer sees no signal for that weight and never updates it. The update was real; fp16 just
could not represent it, so it silently vanished, and part of the model stops learning for no visible reason.

Loss scaling is the standard fix. Multiply the loss by a large factor S before the backward pass; by the
chain rule every gradient is then multiplied by S too, which lifts the small ones up into fp16's
representable range so they survive. Before the weight update, divide the gradients back by S to recover
their true magnitudes. The large gradients were always fine; scaling rescues the small ones at no cost to
the big ones, as long as S is not so large that the big gradients overflow the top of the range.

On this fixture six gradients pass through fp16. Unscaled, three of them (3e-5, 1e-5, 4e-6) are below the
6.1e-5 threshold and flush to zero -- their weights get no update. Scaled by 1024 before the backward pass
and divided back after, all six survive and are recovered to their true values. Same gradients; scaling is
the difference between three lost updates and none. This computes both.

  --gradients  the true gradients and the fp16 threshold
  --scale      which gradients survive fp16 unscaled vs loss-scaled, and the recovered values
  --check      unscaled loses the small gradients; loss scaling preserves and recovers all of them

The gradients, threshold, and scale are the fixture; every fp16 rounding is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "grads.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def to_fp16(x, fp16_min):
    """Model fp16 flush-to-zero: values below the smallest representable magnitude round to 0."""
    return 0.0 if 0 < abs(x) < fp16_min else x


def unscaled(gradients, fp16_min):
    """Each gradient stored directly in fp16 -- the small ones underflow to zero."""
    return [to_fp16(g, fp16_min) for g in gradients]


def loss_scaled(gradients, fp16_min, scale):
    """Multiply by scale before fp16 (lifts small gradients into range), then divide back to recover."""
    return [to_fp16(g * scale, fp16_min) / scale for g in gradients]


def lost(true_grads, stored):
    """How many real (nonzero) gradients were flushed to zero."""
    return sum(1 for g, s in zip(true_grads, stored) if g != 0 and s == 0)


# ----------------------------------------------------------------- printing

def gradients_view(data):
    g, thr = data["gradients"], data["fp16_min"]
    print("GRADIENTS — true magnitudes vs the fp16 threshold %.2e" % thr)
    print("-" * 50)
    for x in g:
        mark = "  <- below threshold, will underflow" if x < thr else ""
        print("  %.6g%s" % (x, mark))
    print("-" * 50)
    print("  %d of %d gradients are below the fp16 threshold." % (sum(1 for x in g if x < thr), len(g)))


def scale_view(data):
    g, thr, s = data["gradients"], data["fp16_min"], data["scale"]
    uns = unscaled(g, thr)
    sca = loss_scaled(g, thr, s)
    print("SCALE — fp16 storage unscaled vs loss-scaled (scale=%d)" % s)
    print("-" * 62)
    print("  true grad      unscaled fp16    loss-scaled (recovered)")
    for x, u, c in zip(g, uns, sca):
        print("  %-12.6g   %-14.6g   %.6g" % (x, u, c))
    print("-" * 62)
    print("  unscaled zeros the small gradients; loss scaling brings them all back.")


def check(data):
    print("SELF-TEST — unscaled loses the small gradients; loss scaling preserves and recovers all of them")
    print("-" * 90)
    g, thr, s = data["gradients"], data["fp16_min"], data["scale"]
    uns = unscaled(g, thr)
    sca = loss_scaled(g, thr, s)

    unscaled_loses = lost(g, uns) > 0
    print("  unscaled fp16 flushes small gradients to zero = %s (%d of %d lost)" % (unscaled_loses, lost(g, uns), len(g)))

    scaled_loses_none = lost(g, sca) == 0
    print("  loss scaling loses none = %s (%d lost)" % (scaled_loses_none, lost(g, sca)))

    recovered = all(abs(c - x) < 1e-12 for x, c in zip(g, sca))
    print("  loss-scaled gradients recover the true values = %s" % recovered)

    lost_were_real = all(g[i] != 0 for i in range(len(g)) if uns[i] == 0 and g[i] != 0)
    print("  the lost gradients were real, nonzero updates = %s (weights that would never learn)" % lost_were_real)

    ok = unscaled_loses and scaled_loses_none and recovered and lost_were_real
    print("-" * 90)
    print("SELF-TEST %s  unscaled_loses=%s  scaled_loses_none=%s  recovered=%s  lost_were_real=%s"
          % ("PASS" if ok else "FAIL", unscaled_loses, scaled_loses_none, recovered, lost_were_real))
    return ok


def main():
    p = argparse.ArgumentParser(description="Scale the loss before the fp16 backward pass to save small gradients.")
    p.add_argument("--gradients", action="store_true")
    p.add_argument("--scale", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("gradients=%d  fp16_min=%.2e  scale=%d  file=%s  (the gradients are a fixture)"
          % (len(data["gradients"]), data["fp16_min"], data["scale"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.gradients:
        gradients_view(data)
    elif args.scale:
        scale_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
