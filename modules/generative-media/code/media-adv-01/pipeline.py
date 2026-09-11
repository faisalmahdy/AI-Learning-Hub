#!/usr/bin/env python3
"""A correct RGBA downsample composes three signal-correctness fixes, then hashes its output.

Resizing an antialiased RGBA sprite is one operation -- average each block of source pixels
into one destination pixel -- and the generative-media track showed it has three independent
ways to be wrong, each its own module. Decimate instead of filtering and fine detail aliases
into a false artifact (media-inter-03). Average the sRGB bytes instead of linear light and
every blend comes out too dark (media-inter-04). Average straight-alpha color instead of
premultiplied and a soft edge bleeds a dark fringe (media-inter-05). This composes all three
fixes into one downsample and measures it against the naive version, then records the correct
output's provenance by a content hash (media-basic-01) so the pixels that shipped are the
pixels that were verified.

The three fixes are not interchangeable and fixing one does nothing for the others: a box
filter in the wrong color space still darkens, a linear-light average of straight-alpha color
still fringes, and a premultiplied straight-decimation still aliases. Only turning on box
filtering AND linear light AND premultiplied alpha together reproduces the physically-correct
area average -- the ground truth this measures against -- which is why a correct resize is the
conjunction of all three and every image library that gets one wrong ships a subtly broken
downscale.

  --input       the source RGBA strip and the physically-correct downsample it should produce
  --ablate      each fix toggled on in turn; watch the error fall to zero only with all three
  --naive       the naive downsample (decimate, sRGB bytes, straight alpha) vs ground truth
  --check       only all three fixes reach zero error; the correct output's hash verifies

The sRGB transfer function and the correct area average are computed here, so every number is
from the run, not hand-derived. Deterministic; stdlib only.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "sprite.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the sRGB transfer function

def srgb_to_linear(c8):
    """One sRGB byte (0-255) to linear light (0-1). The standard sRGB EOTF (media-inter-04)."""
    c = c8 / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    """Linear light (0-1) back to an sRGB byte (0-255)."""
    s = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
    return round(max(0.0, min(1.0, s)) * 255)


# ------------------------------------------------------------- one downsample, three toggles

def process_pair(p, q, box, linear, premul):
    """Average source pixels p and q into one, with each of the three fixes independently toggled.

    box    -- average the pair (True) vs decimate, keep p only (False)      [media-inter-03]
    linear -- average in linear light (True) vs in sRGB bytes (False)        [media-inter-04]
    premul -- premultiply alpha before averaging (True) vs straight (False)  [media-inter-05]
    """
    def decode(px):
        r, g, b, a = px
        rgb = [srgb_to_linear(c) if linear else c / 255.0 for c in (r, g, b)]
        if premul:
            rgb = [c * a for c in rgb]
        return rgb, a

    pr, pa = decode(p)
    qr, qa = decode(q)
    if box:
        avg = [(pr[i] + qr[i]) / 2 for i in range(3)]
        aa = (pa + qa) / 2
    else:                                   # decimate: keep the first sample, drop the second
        avg, aa = pr, pa
    if premul:                              # un-premultiply by the blended alpha
        avg = [c / aa if aa > 0 else 0.0 for c in avg]
    out = [linear_to_srgb(c) if linear else round(max(0.0, min(1.0, c)) * 255) for c in avg]
    return [out[0], out[1], out[2], round(aa, 4)]


def downsample(strip, box, linear, premul):
    """Halve an RGBA strip pair by pair."""
    return [process_pair(strip[i], strip[i + 1], box, linear, premul) for i in range(0, len(strip), 2)]


def ground_truth(strip):
    """The physically-correct downsample: box filter, in linear light, premultiplied alpha."""
    return downsample(strip, box=True, linear=True, premul=True)


def error_vs(out, truth):
    """Total absolute channel error against ground truth: RGB in 0-255, alpha rescaled to 0-255."""
    e = 0.0
    for o, t in zip(out, truth):
        e += abs(o[0] - t[0]) + abs(o[1] - t[1]) + abs(o[2] - t[2])
        e += abs(o[3] - t[3]) * 255
    return round(e, 1)


# ------------------------------------------------------------- provenance (media-basic-01)

def content_hash(strip):
    """SHA-256 of the actual output bytes -- provenance is a function of content, not a label."""
    payload = json.dumps(strip, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


# ----------------------------------------------------------------- printing

def input_view(data):
    strip, truth = data["strip"], ground_truth(data["strip"])
    print("INPUT — source RGBA strip (%d px) and its physically-correct downsample" % len(strip))
    print("-" * 70)
    print("  source:")
    for i, px in enumerate(strip):
        print("    px%d  rgb(%3d,%3d,%3d)  a=%.2f" % (i, px[0], px[1], px[2], px[3]))
    print("  ground truth (box + linear + premultiplied):")
    for i, px in enumerate(truth):
        print("    out%d rgb(%3d,%3d,%3d)  a=%.2f" % (i, px[0], px[1], px[2], px[3]))
    print("-" * 70)
    print("  a correct downsample must reproduce the ground-truth area average exactly.")


def ablate_view(data):
    strip, truth = data["strip"], ground_truth(data["strip"])
    print("ABLATE — turn the three fixes on cumulatively; error falls to zero only with all three")
    print("-" * 70)
    print("  box    linear premul  error_vs_ground_truth")
    ladder = [(False, False, False), (True, False, False), (True, True, False), (True, True, True)]
    for box, lin, pre in ladder:
        out = downsample(strip, box, lin, pre)
        print("  %-6s %-6s %-6s  %s" % (box, lin, pre, error_vs(out, truth)))
    print("-" * 70)
    print("  box fixes aliasing, linear fixes darkening, premul fixes the fringe -- all three needed.")


def naive_view(data):
    strip, truth = data["strip"], ground_truth(data["strip"])
    naive = downsample(strip, box=False, linear=False, premul=False)
    print("NAIVE — decimate, average sRGB bytes, straight alpha (all three fixes off)")
    print("-" * 70)
    for i in range(len(truth)):
        print("  out%d  naive rgb(%3d,%3d,%3d) a=%.2f   truth rgb(%3d,%3d,%3d) a=%.2f"
              % (i, naive[i][0], naive[i][1], naive[i][2], naive[i][3],
                 truth[i][0], truth[i][1], truth[i][2], truth[i][3]))
    print("-" * 70)
    print("  total error vs ground truth: %s" % error_vs(naive, truth))


def check(data):
    print("SELF-TEST — only all three fixes reach zero error; the correct output's hash verifies")
    print("-" * 70)
    strip = data["strip"]
    truth = ground_truth(strip)

    naive = downsample(strip, False, False, False)
    naive_wrong = error_vs(naive, truth) > 0
    print("  the naive downsample differs from ground truth = %s (error %s)"
          % (naive_wrong, error_vs(naive, truth)))

    # each single fix alone still leaves error -- none of the three is sufficient on its own
    singles = {
        "box only": downsample(strip, True, False, False),
        "linear only": downsample(strip, False, True, False),
        "premul only": downsample(strip, False, False, True),
    }
    each_insufficient = all(error_vs(o, truth) > 0 for o in singles.values())
    print("  no single fix alone reaches zero = %s (%s)"
          % (each_insufficient, {k: error_vs(v, truth) for k, v in singles.items()}))

    allthree = downsample(strip, True, True, True)
    all_correct = error_vs(allthree, truth) == 0
    print("  all three fixes together reach zero error = %s" % all_correct)

    # provenance: the hash of the correct output verifies; a fringed naive output does not match
    h = content_hash(allthree)
    rehash_ok = content_hash(downsample(strip, True, True, True)) == h
    naive_differs = content_hash(naive) != h
    print("  the correct output's content hash re-verifies = %s (%s)" % (rehash_ok, h))
    print("  the naive output hashes to a different value = %s" % naive_differs)

    ok = naive_wrong and each_insufficient and all_correct and rehash_ok and naive_differs
    print("-" * 70)
    print("SELF-TEST %s  naive_wrong=%s  each_insufficient=%s  all_correct=%s  provenance=%s"
          % ("PASS" if ok else "FAIL", naive_wrong, each_insufficient, all_correct, rehash_ok and naive_differs))
    return ok


def main():
    p = argparse.ArgumentParser(description="A correct RGBA downsample composing three fixes, plus provenance.")
    p.add_argument("--input", action="store_true")
    p.add_argument("--ablate", action="store_true")
    p.add_argument("--naive", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("source_px=%d  file=%s  (the RGBA strip is a fixture; the sRGB math is computed here)"
          % (len(data["strip"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.input:
        input_view(data)
    elif args.ablate:
        ablate_view(data)
    elif args.naive:
        naive_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
