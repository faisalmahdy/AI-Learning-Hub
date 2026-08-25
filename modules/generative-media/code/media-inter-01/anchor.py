#!/usr/bin/env python3
"""A style anchor is referenced once, not retyped per scene -- or the storyboard drifts.

A multi-scene image or video prompt has to look like one film: same palette, lens,
film stock, mood, across every shot. The tempting way is to write the style into
each scene's prompt by hand. It reads fine and it drifts -- each shot is phrased a
little differently, so the model renders a slightly different look, and worse, when
the art director changes the palette you must edit every scene and will miss some.
The fix is a single Master Visual Anchor referenced by every scene: one string,
prepended identically, one place to change. This composes a storyboard both ways
and measures the consistency and the missed-update bug.

  --compose      the composed scene prompts, drift (retyped) vs anchored (referenced)
  --consistency  how many distinct style signatures each approach produces
  --restyle S    change the palette to S: which scenes actually pick up the new style
  --check        drift is inconsistent and misses a restyle; the anchor is neither

Stdlib only. No image model -- the 'render' is the composed prompt string, where
the style either matches across scenes or does not. Deterministic. A fixture.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOARD = HERE / "storyboard.json"


def load():
    data = json.loads(BOARD.read_text(encoding="utf-8"))
    return data["anchor"], data["scenes"], data["drift_styles"]


def style_of(prompt):
    """Extract the style clause (everything before the ' | ' scene separator)."""
    return prompt.split(" | ", 1)[0].strip()


# ------------------------------------------------------------- the two composers

def compose_anchored(anchor, scenes):
    """Reference the one anchor from every scene: identical style prefix everywhere."""
    return [anchor + " | " + s["action"] for s in scenes]


def compose_drift(scenes, drift_styles):
    """THE BUG: retype the style per scene (each paraphrased differently), so the
    look drifts shot to shot and no two prompts share a style string."""
    return [drift_styles[i] + " | " + s["action"] for i, s in enumerate(scenes)]


# ------------------------------------------------------------------ the metrics

def distinct_styles(prompts):
    """How many different style signatures appear across the storyboard. 1 = consistent."""
    return len({style_of(p) for p in prompts})


def restyle_anchored(new_style, scenes):
    """Change the palette in one place -- every scene inherits it."""
    return compose_anchored(new_style, scenes)


def restyle_drift(new_palette, scenes, drift_styles):
    """Change the palette by editing each scene's retyped style. Simulates a human
    find-and-replace that only catches the scenes phrased the expected way."""
    out = []
    for i, s in enumerate(scenes):
        st = drift_styles[i]
        # the art director searches for the old palette word and swaps it -- but only
        # the scenes that spelled it the canonical way get updated.
        if OLD_PALETTE in st:
            st = st.replace(OLD_PALETTE, new_palette)
        out.append(st + " | " + s["action"])
    return out


OLD_PALETTE = "teal-and-orange"


def picked_up(prompts, new_palette):
    """Which scenes actually contain the new palette after a restyle."""
    return [i for i, p in enumerate(prompts) if new_palette in style_of(p)]


# ------------------------------------------------------------------- printing

def compose_view(anchor, scenes, drift_styles):
    a = compose_anchored(anchor, scenes)
    d = compose_drift(scenes, drift_styles)
    print("COMPOSED PROMPTS — drift (retyped) vs anchored (referenced)")
    print("-" * 68)
    print("  DRIFT:")
    for p in d:
        print("    " + p[:64])
    print("  ANCHORED:")
    for p in a:
        print("    " + p[:64])
    print("-" * 68)
    print("  every anchored scene opens with the identical style string; the drift")
    print("  scenes each open differently, so the render looks different shot to shot.")


def consistency_view(anchor, scenes, drift_styles):
    a = compose_anchored(anchor, scenes)
    d = compose_drift(scenes, drift_styles)
    print("STYLE CONSISTENCY — distinct style signatures across %d scenes" % len(scenes))
    print("-" * 68)
    print("  drift     : %d distinct styles  (looks like %d different films)"
          % (distinct_styles(d), distinct_styles(d)))
    print("  anchored  : %d distinct style   (one film)" % distinct_styles(a))
    print("-" * 68)


def restyle_view(anchor, scenes, drift_styles, new_palette):
    print("RESTYLE — change the palette to %r; who actually gets it?" % new_palette)
    print("-" * 68)
    new_anchor = anchor.replace(OLD_PALETTE, new_palette)
    a = restyle_anchored(new_anchor, scenes)
    d = restyle_drift(new_palette, scenes, drift_styles)
    ap, dp = picked_up(a, new_palette), picked_up(d, new_palette)
    print("  anchored: scenes with the new palette = %d/%d %s" % (len(ap), len(scenes), ap))
    print("  drift:    scenes with the new palette = %d/%d %s" % (len(dp), len(scenes), dp))
    print("-" * 68)
    print("  the anchor updates every scene from one edit; the drift restyle misses the")
    print("  scenes that were paraphrased, so the storyboard is now half old, half new.")


def check(anchor, scenes, drift_styles):
    print("SELF-TEST — drift is inconsistent and misses a restyle; the anchor is neither")
    print("-" * 68)
    a = compose_anchored(anchor, scenes)
    d = compose_drift(scenes, drift_styles)

    anchored_consistent = distinct_styles(a) == 1
    drift_inconsistent = distinct_styles(d) > 1
    print("  anchored has exactly one style across all scenes = %s" % anchored_consistent)
    print("  drift has more than one style = %s (%d distinct)" % (drift_inconsistent, distinct_styles(d)))

    # restyle: anchored updates all scenes, drift misses some.
    new = "sepia-monochrome"
    new_anchor = anchor.replace(OLD_PALETTE, new)
    ra = restyle_anchored(new_anchor, scenes)
    rd = restyle_drift(new, scenes, drift_styles)
    anchored_all = len(picked_up(ra, new)) == len(scenes)
    drift_partial = 0 < len(picked_up(rd, new)) < len(scenes)
    print("  restyle reaches every anchored scene = %s (%d/%d)" % (anchored_all, len(picked_up(ra, new)), len(scenes)))
    print("  restyle misses some drift scenes = %s (%d/%d)" % (drift_partial, len(picked_up(rd, new)), len(scenes)))

    det = compose_anchored(anchor, scenes) == compose_anchored(anchor, scenes)
    ok = anchored_consistent and drift_inconsistent and anchored_all and drift_partial and det
    print("-" * 68)
    print("SELF-TEST %s  consistent=%s  drift_varies=%s  restyle_all=%s  restyle_misses=%s"
          % ("PASS" if ok else "FAIL", anchored_consistent, drift_inconsistent, anchored_all, drift_partial))
    return ok


def main():
    p = argparse.ArgumentParser(description="A referenced style anchor vs per-scene style drift.")
    p.add_argument("--compose", action="store_true")
    p.add_argument("--consistency", action="store_true")
    p.add_argument("--restyle", metavar="S")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    anchor, scenes, drift_styles = load()
    print("scenes=%d  file=%s  (storyboard is a fixture)" % (len(scenes), BOARD.name))
    print("")

    if args.check:
        return 0 if check(anchor, scenes, drift_styles) else 1
    if args.compose:
        compose_view(anchor, scenes, drift_styles)
    elif args.consistency:
        consistency_view(anchor, scenes, drift_styles)
    elif args.restyle:
        restyle_view(anchor, scenes, drift_styles, args.restyle)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
