"""Interpolate positions into the trained range to extend context, do not extrapolate past it -- RoPE rotated by a position larger than any it saw in training produces an out-of-distribution angle, and attention degrades.

RoPE encodes position by rotating each pair of query/key dimensions by an angle proportional to the token's position. It uses a spectrum of frequencies: high-frequency pairs rotate a lot per position and resolve nearby tokens, low-frequency pairs rotate very little per position and carry long-range order. Attention's dot product then depends on the relative rotation between two positions, so what a trained model has actually seen is the range of rotation angles that positions and distances up to its training length L produce.

Run the same model on a context longer than L and the far positions rotate by angles beyond that range. It bites the low-frequency dimensions hardest: they rotate so little per position that even at L they have barely turned, so pushing them out to a position several times L sends them into angle territory the model never trained on -- out of distribution. The query-key geometry there is unfamiliar, and attention quality collapses. This is extrapolation, and it is why a model run naively past its training length falls apart.

Position interpolation fixes it by scaling every position by L/target before applying RoPE. That squeezes the whole target-length range of positions back into the trained angle range, so the far position now rotates by exactly the angle the old maximum position did -- in distribution. No dimension ever sees an angle it did not see in training; the model is operating in the regime it knows.

The cost is resolution. Because positions are squeezed together, adjacent tokens are now closer in angle than they were in training -- the high-frequency dimensions, which did the fine position resolution, now separate neighbors by a smaller angle, so the model must distinguish positions it previously kept farther apart. Interpolation trades angular resolution for staying in distribution, which is why it usually needs a little fine-tuning and why smarter schemes (NTK-aware, YaRN) interpolate the low frequencies while sparing the high ones.

On this fixture a model trained to length 8 is run at length 32. Extrapolation rotates the lowest-frequency dimension to 4x its trained maximum angle; interpolation scales positions by 8/32 and brings that angle exactly back to the trained maximum, at the cost of quartering the adjacent-token resolution. This computes both.

  --angles    the max rotation angle of the lowest-frequency dimension under training, extrapolation, and interpolation
  --tradeoff  how interpolation returns the long-range angle to the trained range while shrinking adjacent-token resolution
  --check     extrapolation pushes the angle out of the trained range by the context ratio; interpolation returns it exactly, at a resolution cost

base, head_dim, train_len, target_len are the fixture; the frequencies, the angles, and the resolution cost are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "posinterp.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def frequencies(base, head_dim):
    """RoPE frequencies: pair i rotates at base**(-2i/head_dim). i=0 is fastest, the last is slowest."""
    return [base ** (-2.0 * i / head_dim) for i in range(head_dim // 2)]


def angle(position, freq):
    """The rotation angle RoPE applies to a dimension pair at a given position."""
    return position * freq


def scale_factor(train_len, target_len):
    """Position interpolation multiplies every position by this, squeezing target_len into train_len."""
    return train_len / target_len


# ----------------------------------------------------------------- printing

def angles_view(data):
    base, d, L, T = data["base"], data["head_dim"], data["train_len"], data["target_len"]
    freqs = frequencies(base, d)
    fmin = min(freqs)
    s = scale_factor(L, T)
    print("ANGLES — max rotation of the lowest-frequency pair (freq %.4f)" % fmin)
    print("-" * 60)
    print("  trained (position %d)          : %.4f rad" % (L, angle(L, fmin)))
    print("  extrapolated (position %d)     : %.4f rad" % (T, angle(T, fmin)))
    print("  interpolated (position %d * %.3f): %.4f rad" % (T, s, angle(T * s, fmin)))
    print("-" * 60)
    print("  extrapolation leaves the trained range; interpolation returns exactly to it")


def tradeoff_view(data):
    base, d, L, T = data["base"], data["head_dim"], data["train_len"], data["target_len"]
    freqs = frequencies(base, d)
    fmax = max(freqs)
    s = scale_factor(L, T)
    print("TRADEOFF — adjacent-token angle step on the highest-frequency pair (freq %.4f)" % fmax)
    print("-" * 60)
    print("  trained step (distance 1)      : %.4f rad" % angle(1, fmax))
    print("  interpolated step (distance 1) : %.4f rad" % angle(1 * s, fmax))
    print("-" * 60)
    print("  interpolation squeezes neighbors closer in angle -- finer to resolve (%.0fx)" % (1 / s))


def check(data):
    print("SELF-TEST — extrapolation pushes the angle out of the trained range by the context ratio; interpolation returns it exactly, at a resolution cost")
    print("-" * 112)
    base, d, L, T = data["base"], data["head_dim"], data["train_len"], data["target_len"]
    freqs = frequencies(base, d)
    fmin, fmax = min(freqs), max(freqs)
    s = scale_factor(L, T)

    trained_max = angle(L, fmin)
    extrap_max = angle(T, fmin)
    interp_max = angle(T * s, fmin)

    extrapolation_out_of_range = extrap_max > trained_max
    print("  extrapolation exceeds the trained max angle = %s (%.4f > %.4f)" % (extrapolation_out_of_range, extrap_max, trained_max))

    ood_factor_is_context_ratio = abs(extrap_max / trained_max - T / L) < 1e-9
    print("  the overshoot factor equals the context ratio = %s (%.1fx = %d/%d)" % (ood_factor_is_context_ratio, extrap_max / trained_max, T, L))

    interpolation_in_range = interp_max <= trained_max + 1e-9
    print("  interpolation stays within the trained range = %s (%.4f)" % (interpolation_in_range, interp_max))

    interpolation_matches_trained_max = abs(interp_max - trained_max) < 1e-9
    print("  interpolation returns exactly to the trained max = %s (%.4f == %.4f)" % (interpolation_matches_trained_max, interp_max, trained_max))

    interp_step = angle(1 * s, fmax)
    train_step = angle(1, fmax)
    interpolation_costs_resolution = interp_step < train_step
    print("  interpolation shrinks the adjacent-token angle step = %s (%.4f < %.4f)" % (interpolation_costs_resolution, interp_step, train_step))

    ok = (extrapolation_out_of_range and ood_factor_is_context_ratio and interpolation_in_range
          and interpolation_matches_trained_max and interpolation_costs_resolution)
    print("-" * 112)
    print("SELF-TEST %s  extrapolation_out_of_range=%s  ood_factor_is_context_ratio=%s  interpolation_in_range=%s  interpolation_matches_trained_max=%s  interpolation_costs_resolution=%s"
          % ("PASS" if ok else "FAIL", extrapolation_out_of_range, ood_factor_is_context_ratio, interpolation_in_range,
             interpolation_matches_trained_max, interpolation_costs_resolution))
    return ok


def main():
    p = argparse.ArgumentParser(description="Position interpolation: to extend a RoPE model's context, scale positions into the trained range rather than feeding positions larger than any seen in training, because RoPE rotated past its trained range produces out-of-distribution angles (worst on the low-frequency dimensions) and attention degrades -- interpolation returns the angle to the trained range at the cost of adjacent-token resolution.")
    p.add_argument("--angles", action="store_true")
    p.add_argument("--tradeoff", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("base=%d  head_dim=%d  train_len=%d  target_len=%d  file=%s  (these are a fixture)"
          % (data["base"], data["head_dim"], data["train_len"], data["target_len"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.angles:
        angles_view(data)
    elif args.tradeoff:
        tradeoff_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
