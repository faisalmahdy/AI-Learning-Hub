"""Sampling a minified texture must read from a prefiltered mip level chosen by the minification, not point-sample the full-resolution texture -- point-sampling level 0 reads one texel per screen pixel and skips the rest, so the sample is not the average of the region the pixel covers and the texture aliases; the right level is log2(minification), and a level higher than that over-blurs.

A mipmap is a precomputed pyramid of a texture: level 0 is the texture itself, level 1 is level 0 with every adjacent pair averaged to half the length, level 2 halves it again, and so on, each level a correctly prefiltered smaller copy. The pyramid exists so that a minified draw can read an already-averaged texel instead of averaging on the fly.

When a surface is minified so each screen pixel covers m texels, the naive sampler reads level 0 at the pixel's location -- one texel -- and skips the other m-1. That is aliasing: the value it returns is a single point, not the average of the m texels the pixel actually covers, so a fine pattern folds into a false one and shimmers as the view moves. The retriever of pixels did nothing wrong; it read a texel. The texel just was not the region.

The fix is to sample the level whose texels are about one screen pixel wide. Each step down the pyramid doubles the texels-per-texel, so the level whose one texel spans m originals is level log2(m). At that level the texel already holds the average of the m originals the screen pixel covers, and the sample is the true footprint average -- prefiltered once, reused every frame.

Picking the wrong level fails in two directions. Below log2(m) the texels are smaller than the pixel footprint, so you are back to skipping texels and aliasing. Above log2(m) a texel averages more originals than the pixel covers, so neighboring pixels that cover different regions read texels that overlap into each other's regions and collapse to the same value -- over-blur.

On this fixture the texture is a 16-texel ramp and the minification is 4, so each screen pixel covers 4 texels, the correct level is 2, and the true footprint averages are 15, 55, 95, 135. Level 0 point-sampling gives 0, 40, 80, 120 (aliased low); level 2 gives exactly the footprint averages; level 3 gives 35, 35, 115, 115 (adjacent pixels collapsed). This computes all of it.

  --levels    the mip pyramid and the footprint averages the correct level must reproduce
  --sample    point-sampling level 0 (aliased), the correct level log2(m), and one level too high (over-blur)
  --check     the correct level is log2(minification), level 0 aliases (misses the footprint average), the correct level matches it, and a higher level over-blurs

the texture and the minification are the fixture; the pyramid, the footprint averages, and the per-level samples are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "mipmap.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def build_pyramid(texture):
    """The mip pyramid: each level halves the previous by averaging adjacent pairs."""
    levels = [list(texture)]
    while len(levels[-1]) > 1:
        prev = levels[-1]
        levels.append([(prev[2 * i] + prev[2 * i + 1]) / 2 for i in range(len(prev) // 2)])
    return levels


def footprint_averages(texture, m):
    """The truth: each screen pixel's value is the average of the m texels it covers."""
    screen = len(texture) // m
    return [sum(texture[i * m:(i + 1) * m]) / m for i in range(screen)]


def sample_level(level, screen):
    """Sample a mip level across `screen` output pixels, nearest-texel."""
    return [level[i * len(level) // screen] for i in range(screen)]


def correct_level(m):
    """The level whose texels span one screen pixel's footprint: log2(minification)."""
    return int(math.log2(m))


# ----------------------------------------------------------------- printing

def levels_view(d):
    tex, m = d["texture"], d["minification"]
    pyr = build_pyramid(tex)
    print("LEVELS — mip pyramid of a %d-texel texture, minification %d" % (len(tex), m))
    print("-" * 64)
    for k, lv in enumerate(pyr):
        tag = "  <- correct level (log2 %d)" % m if k == correct_level(m) else ""
        print("  level %d (%2d texels): %s%s" % (k, len(lv), [("%g" % x) for x in lv], tag))
    print("  footprint averages (truth): %s" % footprint_averages(tex, m))
    print("-" * 64)
    print("  the correct level's texels each hold the average of the %d texels a screen pixel covers" % m)


def sample_view(d):
    tex, m = d["texture"], d["minification"]
    pyr = build_pyramid(tex)
    screen = len(tex) // m
    cl = correct_level(m)
    print("SAMPLE — screen of %d pixels, each covering %d texels" % (screen, m))
    print("-" * 64)
    print("  level 0 (point-sample):   %s   <- aliased" % [("%g" % x) for x in sample_level(pyr[0], screen)])
    print("  level %d (correct):        %s   <- footprint average" % (cl, [("%g" % x) for x in sample_level(pyr[cl], screen)]))
    print("  level %d (too high):       %s   <- over-blurred" % (cl + 1, [("%g" % x) for x in sample_level(pyr[cl + 1], screen)]))
    print("-" * 64)
    print("  level 0 skips texels; the correct level averages exactly the footprint; a higher level bleeds neighbors together")


def check(d):
    print("SELF-TEST — the correct level is log2(minification), level 0 aliases, the correct level matches the footprint average, and a higher level over-blurs")
    print("-" * 112)
    tex, m = d["texture"], d["minification"]
    pyr = build_pyramid(tex)
    screen = len(tex) // m
    truth = footprint_averages(tex, m)
    cl = correct_level(m)

    level_is_log2 = cl == int(math.log2(m)) and 2 ** cl == m
    print("  correct level = log2(minification) = %d (2^%d == %d) = %s" % (cl, cl, m, level_is_log2))

    lvl0 = sample_level(pyr[0], screen)
    level0_aliases = lvl0 != truth
    print("  level 0 point-sampling misses the footprint average (aliases) = %s (%s vs truth %s)" % (level0_aliases, [("%g" % x) for x in lvl0], truth))

    correct_matches = sample_level(pyr[cl], screen) == truth
    print("  the correct level reproduces the footprint average = %s (%s)" % (correct_matches, [("%g" % x) for x in sample_level(pyr[cl], screen)]))

    high = sample_level(pyr[cl + 1], screen)
    toohigh_overblurs = any(high[i] == high[i + 1] and truth[i] != truth[i + 1] for i in range(len(high) - 1))
    print("  a higher level collapses pixels that should differ (over-blur) = %s (%s)" % (toohigh_overblurs, [("%g" % x) for x in high]))

    ok = (level_is_log2 and level0_aliases and correct_matches and toohigh_overblurs)
    print("-" * 112)
    print("SELF-TEST %s  level_is_log2=%s  level0_aliases=%s  correct_matches=%s  toohigh_overblurs=%s"
          % ("PASS" if ok else "FAIL", level_is_log2, level0_aliases, correct_matches, toohigh_overblurs))
    return ok


def main():
    p = argparse.ArgumentParser(description="Mipmap level selection: sampling a minified texture must read from the prefiltered mip level whose texels span one screen pixel's footprint -- level log2(minification) -- because point-sampling the full-resolution level 0 skips texels and aliases, while a level higher than log2(minification) averages more texels than the pixel covers and over-blurs; the mip pyramid precomputes the averaged levels so the correct one is a single lookup.")
    p.add_argument("--levels", action="store_true")
    p.add_argument("--sample", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    d = load()
    print("texture=%d texels  minification=%d  file=%s" % (len(d["texture"]), d["minification"], DATA.name))
    print("")

    if args.check:
        return 0 if check(d) else 1
    if args.levels:
        levels_view(d)
    elif args.sample:
        sample_view(d)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
