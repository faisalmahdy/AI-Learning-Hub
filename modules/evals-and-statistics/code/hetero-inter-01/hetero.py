"""Check the effect per segment, not just the average -- a positive overall A/B result can hide a segment it harms.

An A/B test reports one headline number: the average treatment effect, how much the change moved the metric across all
users. That average is what ship decisions are usually made on -- positive, ship it; negative, kill it. But the average is
a single summary of what may be very different experiences underneath. A change does not affect everyone the same way:
it can help one kind of user and hurt another (a simpler interface that delights newcomers but strips out the shortcuts
power users depend on; a model that improves for the common case and regresses on a rare-but-important one). When the
effect varies across segments -- a HETEROGENEOUS treatment effect -- the overall average is a weighted blend, and if the
helped segment is large enough, the average comes out positive even while a smaller segment is being actively harmed. The
team sees a green number and ships a change that made a valuable minority worse.

The failure is that the average is not wrong, it is incomplete: +5.8 overall is a true statement about the mean user and a
misleading one about any particular user, because it silently sums a big win for one group with a real loss for another.
Shipping on the average alone treats the users the change hurt as acceptable collateral, usually without anyone deciding
that on purpose -- the harm never appeared on the dashboard because the dashboard only showed the mean.

The fix is to look at the effect BY SEGMENT before shipping, not only in aggregate: break the result down along the axes
that matter (user tenure, platform, region, usage level, the slices your product cares about) and check whether any
important segment regressed, even when the overall number is positive. A positive average with a harmed key segment is a
decision to make deliberately -- ship anyway, ship with a fix for that segment, or hold -- not a decision to make by
accident because the segment was averaged away. Segmentation turns 'the change is good' into 'the change is good for these
users and bad for those,' which is the information a ship decision actually needs.

The rule: an A/B test's average treatment effect can be positive while the change harms an important subgroup, because the
average blends a large helped segment with a smaller harmed one, so evaluate the effect per segment before shipping and
treat a regressed key segment as a real cost -- not as noise the positive average absolves.

On this fixture the change helps new users (+10, 700 of them) and hurts power users (-4, 300 of them). The size-weighted
overall effect is +5.8, so an average-only view ships it; the per-segment view shows power users regressed and flags the
harm. This computes both.

  --segments   each segment's size and effect, and the size-weighted overall effect (+5.8)
  --decision   ship-on-average (green, ship) vs ship-with-segments (a key segment regressed -> flag before shipping)
  --check      the overall effect is positive while a segment is harmed; the average hides it, segmentation surfaces it

segments (name, size, effect) is the fixture; the overall effect and per-segment decision are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "hetero.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def overall_effect(segments):
    """The size-weighted average treatment effect across all users."""
    total = sum(s["size"] for s in segments)
    return sum(s["effect"] * s["size"] for s in segments) / total


def harmed_segments(segments):
    """Segments the change made worse (negative effect)."""
    return [s for s in segments if s["effect"] < 0]


def ship_on_average(segments):
    """Naive decision: ship if the overall effect is positive."""
    return overall_effect(segments) > 0


def ship_with_segments(segments):
    """Segment-aware decision: only 'clear to ship' if positive overall AND no segment regressed."""
    return overall_effect(segments) > 0 and not harmed_segments(segments)


# ----------------------------------------------------------------- printing

def segments_view(data):
    segs = data["segments"]
    total = sum(s["size"] for s in segs)
    print("SEGMENTS — per-segment effect and the size-weighted overall effect")
    print("-" * 60)
    print("  segment       size   share   effect")
    for s in segs:
        tag = "  <- harmed" if s["effect"] < 0 else ""
        print("  %-12s  %-6d %-6s %+d%s" % (s["name"], s["size"], "%.0f%%" % (s["size"] / total * 100), s["effect"], tag))
    print("-" * 60)
    print("  overall (size-weighted) effect = %+.1f" % overall_effect(segs))


def decision_view(data):
    segs = data["segments"]
    print("DECISION — ship on the average vs ship with segments checked")
    print("-" * 62)
    print("  overall effect = %+.1f" % overall_effect(segs))
    print("  SHIP ON AVERAGE:   overall positive -> ship = %s" % ship_on_average(segs))
    harmed = harmed_segments(segs)
    print("  SHIP WITH SEGMENTS: any segment regressed? %s" % ([s["name"] for s in harmed] or "none"))
    print("                      clear to ship = %s" % ship_with_segments(segs))
    print("-" * 62)
    print("  the average says ship; the segment view flags harm to %s first." % ", ".join(s["name"] for s in harmed))


def check(data):
    print("SELF-TEST — the overall effect is positive while a segment is harmed; the average hides it, segmentation surfaces it")
    print("-" * 118)
    segs = data["segments"]
    oe = overall_effect(segs)
    harmed = harmed_segments(segs)

    overall_positive = oe > 0
    print("  the overall treatment effect is positive = %s (%+.1f)" % (overall_positive, oe))

    a_segment_harmed = len(harmed) > 0
    print("  at least one segment was harmed = %s (%s)" % (a_segment_harmed, [(s["name"], s["effect"]) for s in harmed]))

    average_hides_harm = overall_positive and a_segment_harmed
    print("  a positive average hides a harmed segment = %s" % average_hides_harm)

    ship_on_average_says_yes = ship_on_average(segs)
    print("  ship-on-average would ship it = %s" % ship_on_average_says_yes)

    segments_flag_it = not ship_with_segments(segs)
    print("  the segment-aware check does NOT clear it to ship = %s" % segments_flag_it)

    ok = overall_positive and a_segment_harmed and average_hides_harm and ship_on_average_says_yes and segments_flag_it
    print("-" * 118)
    print("SELF-TEST %s  overall_positive=%s  a_segment_harmed=%s  average_hides_harm=%s  ship_on_average_says_yes=%s  segments_flag_it=%s"
          % ("PASS" if ok else "FAIL", overall_positive, a_segment_harmed, average_hides_harm, ship_on_average_says_yes, segments_flag_it))
    return ok


def main():
    p = argparse.ArgumentParser(description="Heterogeneous treatment effects: an A/B test's average treatment effect can be positive while the change harms an important subgroup, because the average blends a large helped segment with a smaller harmed one, so evaluate the effect per segment before shipping and treat a regressed key segment as a real cost -- not as noise the positive average absolves.")
    p.add_argument("--segments", action="store_true")
    p.add_argument("--decision", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("segments=%d  file=%s  (the segment sizes and effects are a fixture)" % (len(data["segments"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.segments:
        segments_view(data)
    elif args.decision:
        decision_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
