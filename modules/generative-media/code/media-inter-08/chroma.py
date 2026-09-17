"""Subsample chroma, not luma -- the eye barely sees color detail but is sharp on brightness.

Compression that throws away resolution has to choose what to throw away. An image split into
luma (brightness, Y) and chroma (color, Cb and Cr) offers an easy answer, because the eye is
far more sensitive to fine detail in brightness than in color. Halve the resolution of a chroma
channel and almost no one can tell; halve the resolution of luma and the image visibly softens.
This is why JPEG and essentially every video codec store chroma at half or quarter resolution
(4:2:0) and keep luma full -- same bytes saved, wildly different perceptual cost.

To isolate the principle, this gives all three channels the identical high-frequency pattern,
so subsampling any one of them produces the exact same raw reconstruction error. The only thing
that differs is the perceptual weight of the channel: luma carries most of the eye's acuity,
each chroma channel very little. So subsampling luma costs 93 perceptual units while subsampling
a chroma channel costs 8 -- the same bytes saved and the same raw error, but eleven times the
visible damage when you took it from the wrong channel. This computes the raw error and the
perceptual error of subsampling each channel and shows luma is the one to leave alone.

  --channels   each channel's pattern, its raw reconstruction error when subsampled, and its weight
  --cost       perceptual cost of subsampling luma vs a chroma channel, for the same bytes saved
  --check      same bytes and same raw error, but subsampling luma costs far more perceptually

The channel patterns and perceptual weights are the fixture; every error is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "image.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- subsample and reconstruct

def subsample_reconstruct(channel):
    """Halve resolution by averaging adjacent pairs, then reconstruct by duplicating each average."""
    out = []
    for i in range(0, len(channel), 2):
        avg = (channel[i] + channel[i + 1]) / 2
        out.extend([avg, avg])
    return out


def raw_error(channel):
    """Mean absolute error between the channel and its subsample-then-reconstruct version."""
    recon = subsample_reconstruct(channel)
    return sum(abs(a - b) for a, b in zip(channel, recon)) / len(channel)


def saved_samples(channel):
    """How many samples subsampling this channel removes (half of them)."""
    return len(channel) // 2


# ------------------------------------------------------------- perceptual cost

def perceptual_cost(name, data):
    """Raw error of subsampling one channel, weighted by that channel's perceptual sensitivity."""
    return raw_error(data["channels"][name]) * data["weights"][name]


# ----------------------------------------------------------------- printing

def channels_view(data):
    print("CHANNELS — same pattern in each, so raw error is identical; weights differ")
    print("-" * 66)
    print("  channel  role        pattern                 raw error  weight")
    for name in data["order"]:
        ch = data["channels"][name]
        print("  %-8s %-11s %-22s %-10.1f %.3f"
              % (name, data["roles"][name], str(ch), raw_error(ch), data["weights"][name]))
    print("-" * 66)
    print("  luma carries most of the eye's acuity; each chroma channel very little.")


def cost_view(data):
    luma = data["luma"]
    chroma = data["chroma_example"]
    print("COST — subsample luma (%s) vs a chroma channel (%s), same bytes saved" % (luma, chroma))
    print("-" * 66)
    print("  subsample %-4s: saves %d samples, raw error %.1f, perceptual cost %.1f"
          % (luma, saved_samples(data["channels"][luma]), raw_error(data["channels"][luma]),
             perceptual_cost(luma, data)))
    print("  subsample %-4s: saves %d samples, raw error %.1f, perceptual cost %.1f"
          % (chroma, saved_samples(data["channels"][chroma]), raw_error(data["channels"][chroma]),
             perceptual_cost(chroma, data)))
    ratio = perceptual_cost(luma, data) / perceptual_cost(chroma, data)
    print("  luma subsampling costs %.1fx more for the same bytes." % ratio)
    print("-" * 66)
    print("  this is why codecs subsample chroma (4:2:0) and keep luma full resolution.")


def check(data):
    print("SELF-TEST — same bytes and raw error, but subsampling luma costs far more perceptually")
    print("-" * 66)
    luma, chroma = data["luma"], data["chroma_example"]

    same_bytes = saved_samples(data["channels"][luma]) == saved_samples(data["channels"][chroma])
    print("  subsampling luma and chroma save the same number of samples = %s (%d each)"
          % (same_bytes, saved_samples(data["channels"][luma])))

    raw_equal = abs(raw_error(data["channels"][luma]) - raw_error(data["channels"][chroma])) < 1e-9
    print("  the raw reconstruction error is identical for both = %s (%.1f)"
          % (raw_equal, raw_error(data["channels"][luma])))

    cl, cc = perceptual_cost(luma, data), perceptual_cost(chroma, data)
    luma_costlier = cl > 3 * cc
    print("  subsampling luma costs much more perceptually = %s (%.1f vs %.1f, %.1fx)"
          % (luma_costlier, cl, cc, cl / cc))

    weight_luma_high = data["weights"][luma] > data["weights"][chroma]
    print("  luma's perceptual weight exceeds chroma's = %s (%.3f vs %.3f)"
          % (weight_luma_high, data["weights"][luma], data["weights"][chroma]))

    ok = same_bytes and raw_equal and luma_costlier and weight_luma_high
    print("-" * 66)
    print("SELF-TEST %s  same_bytes=%s  raw_equal=%s  luma_costlier=%s  weight_luma_high=%s"
          % ("PASS" if ok else "FAIL", same_bytes, raw_equal, luma_costlier, weight_luma_high))
    return ok


def main():
    p = argparse.ArgumentParser(description="Subsample chroma, not luma.")
    p.add_argument("--channels", action="store_true")
    p.add_argument("--cost", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("channels=%d  luma=%s  file=%s  (channel patterns and weights are a fixture)"
          % (len(data["channels"]), data["luma"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.channels:
        channels_view(data)
    elif args.cost:
        cost_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
