"""Score a missing heartbeat against the node's own timing variance -- or one fixed timeout is wrong for every node.

A failure detector decides a node is dead when its heartbeat has been silent too long. The obvious rule is a fixed
timeout: no heartbeat for T seconds means dead. But T is a single number applied to every node, and nodes do not all
beat alike. A node on a quiet path is metronome-regular; one behind a busy queue or a flaky link is bursty, its gaps
swinging wildly even while it is perfectly alive. Pick T tight enough to notice the regular node stalling and you will
trip constantly on the bursty node's normal jitter -- false positives that evict healthy nodes and trigger needless
failovers. Pick T loose enough to tolerate the bursty node and you are blind to the regular node dying, because its
fatal silence is shorter than the loose timeout. No single T serves both, and a real system has thousands of nodes with
thousands of timing profiles.

An adaptive detector fixes this by measuring the gap in units of the node's OWN variability. Track each node's recent
heartbeat intervals, take their mean and standard deviation, and score the current silence as how many standard
deviations it sits above the mean -- roughly (gap - mean) / stddev. Now the threshold is a suspicion LEVEL, not a
duration, and it means the same thing on every node: a gap three sigma out is equally alarming on a regular node and a
bursty one, even though those are wildly different numbers of seconds. The regular node's small variance makes a modest
delay enormous in sigma; the bursty node's large variance absorbs the same delay as ordinary. One tuning parameter, the
suspicion threshold, works fleet-wide because each node is judged against itself. (This is the idea behind the
phi-accrual detector, which reports the suspicion as a continuous log-probability rather than a hard sigma count.)

On this fixture both nodes show the SAME 1.6s gap, but node A beats regularly (mean 1.0, tiny variance) and has truly
failed, while node B is bursty (mean 1.0, large variance) and is fine. A fixed 1.5s timeout fires on both -- a false
positive on B. A fixed 2.0s timeout fires on neither -- missing A's death. The adaptive detector scores A's gap at many
sigma (dead) and B's at under one (alive), correct on both with one threshold. This computes both.

  --detect     each node's baseline, the two fixed-timeout verdicts, and the adaptive suspicion score
  --threshold  why no single fixed timeout separates A's fatal gap from B's normal gap (they are the same 1.6s)
  --check      the same gap is many sigma for the regular node and under one for the bursty node; adaptive gets both right

The intervals, test gaps, and thresholds are the fixture; every mean, stddev, and score is computed. Stdlib only.
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "faildetect.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def baseline(intervals):
    """The node's own heartbeat mean and standard deviation -- what 'normal' means for this node."""
    return statistics.mean(intervals), statistics.pstdev(intervals)


def suspicion(gap, intervals):
    """How many standard deviations the current silence sits above the node's mean interval (a phi-like score)."""
    mean, sd = baseline(intervals)
    return (gap - mean) / sd if sd > 0 else float("inf")


def fixed_says_dead(gap, timeout):
    """A fixed-timeout detector: dead if the gap exceeds the one global timeout."""
    return gap > timeout


def adaptive_says_dead(gap, intervals, phi_threshold):
    """An adaptive detector: dead if the suspicion (sigma above the node's own mean) exceeds the threshold."""
    return suspicion(gap, intervals) > phi_threshold


# ----------------------------------------------------------------- printing

def detect_view(data):
    lo, hi, phi = data["fixed_low"], data["fixed_high"], data["phi_threshold"]
    print("DETECT — same 1.6s gap on two nodes; fixed timeouts vs an adaptive score")
    print("-" * 78)
    print("  node  mean  stddev  gap   fixed>%.1f  fixed>%.1f  suspicion(sigma)  adaptive>%.0f  truly_failed" % (lo, hi, phi))
    for name, node in data["nodes"].items():
        mean, sd = baseline(node["intervals"])
        g = node["test_gap"]
        print("  %-4s  %.2f  %.3f   %.1f   %-8s   %-8s   %-15.1f   %-11s   %s"
              % (name, mean, sd, g, fixed_says_dead(g, lo), fixed_says_dead(g, hi),
                 suspicion(g, node["intervals"]), adaptive_says_dead(g, node["intervals"], phi), node["truly_failed"]))
    print("-" * 78)
    print("  the same 1.6s is many sigma for the regular node and under one for the bursty node.")


def threshold_view(data):
    lo, hi = data["fixed_low"], data["fixed_high"]
    a, b = data["nodes"]["A"], data["nodes"]["B"]
    print("THRESHOLD — no single fixed timeout separates a fatal gap from a normal one")
    print("-" * 62)
    print("  node A (failed) gap = %.1fs   node B (alive) gap = %.1fs   -- identical" % (a["test_gap"], b["test_gap"]))
    print("  fixed timeout %.1fs: A dead=%s, B dead=%s  (B is a false positive)" % (lo, fixed_says_dead(a["test_gap"], lo), fixed_says_dead(b["test_gap"], lo)))
    print("  fixed timeout %.1fs: A dead=%s, B dead=%s  (A is missed)" % (hi, fixed_says_dead(a["test_gap"], hi), fixed_says_dead(b["test_gap"], hi)))
    print("-" * 62)
    print("  a duration cannot tell the two apart because they ARE the same duration; only variance can.")


def check(data):
    print("SELF-TEST — the same gap is many sigma for the regular node and under one for the bursty node; adaptive gets both right")
    print("-" * 120)
    a, b = data["nodes"]["A"], data["nodes"]["B"]
    lo, hi, phi = data["fixed_low"], data["fixed_high"], data["phi_threshold"]

    same_gap = a["test_gap"] == b["test_gap"]
    print("  both nodes show the identical numeric gap = %s (%.1fs)" % (same_gap, a["test_gap"]))

    regular_gap_extreme = suspicion(a["test_gap"], a["intervals"]) > phi
    print("  the gap is extreme in sigma for the regular node A = %s (%.1f sigma)" % (regular_gap_extreme, suspicion(a["test_gap"], a["intervals"])))

    bursty_gap_normal = suspicion(b["test_gap"], b["intervals"]) < phi
    print("  the same gap is within normal for the bursty node B = %s (%.1f sigma)" % (bursty_gap_normal, suspicion(b["test_gap"], b["intervals"])))

    fixed_low_false_positive = fixed_says_dead(b["test_gap"], lo) and not b["truly_failed"]
    print("  the tight fixed timeout false-positives on the healthy bursty node = %s" % fixed_low_false_positive)

    fixed_high_misses = not fixed_says_dead(a["test_gap"], hi) and a["truly_failed"]
    print("  the loose fixed timeout misses the failed regular node = %s" % fixed_high_misses)

    adaptive_correct = (adaptive_says_dead(a["test_gap"], a["intervals"], phi) == a["truly_failed"]
                        and adaptive_says_dead(b["test_gap"], b["intervals"], phi) == b["truly_failed"])
    print("  the adaptive detector is correct on both nodes with one threshold = %s" % adaptive_correct)

    ok = same_gap and regular_gap_extreme and bursty_gap_normal and fixed_low_false_positive and fixed_high_misses and adaptive_correct
    print("-" * 120)
    print("SELF-TEST %s  same_gap=%s  regular_gap_extreme=%s  bursty_gap_normal=%s  fixed_low_false_positive=%s  fixed_high_misses=%s  adaptive_correct=%s"
          % ("PASS" if ok else "FAIL", same_gap, regular_gap_extreme, bursty_gap_normal, fixed_low_false_positive, fixed_high_misses, adaptive_correct))
    return ok


def main():
    p = argparse.ArgumentParser(description="Adaptive failure detection: score a missing heartbeat in units of the node's own interval variance, so one suspicion threshold works fleet-wide where no single fixed timeout can.")
    p.add_argument("--detect", action="store_true")
    p.add_argument("--threshold", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("nodes=%s  fixed_low=%.1f  fixed_high=%.1f  phi_threshold=%.1f  file=%s  (the heartbeat histories are a fixture)"
          % (list(data["nodes"]), data["fixed_low"], data["fixed_high"], data["phi_threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.detect:
        detect_view(data)
    elif args.threshold:
        threshold_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
