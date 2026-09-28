#!/usr/bin/env python3
"""Your confidence is not your competence -- study by recall, not by feeling.

Before a boss fight you have a feeling about each concept: a judgment of learning, how
well you think you know it. After, you have the truth: did you recall it from memory or
blank. The two diverge, and they diverge with a direction -- fluency feels like mastery,
so re-reading a concept until it flows leaves you confident about material you cannot
actually reproduce. Averaged over concepts, mean confidence sits above the real recall
rate: an overconfidence gap.

The gap would be harmless if it were uniform, but it is not. The most dangerous concepts
are the ones you are confident about AND fail -- overconfident-wrong -- because they do
not feel weak, so any study plan that allocates time by what feels weak skips exactly
them. This measures the overconfidence gap, the miscalibration inside the high-confidence
group, and the coverage failure of studying by confidence versus studying by an actual
recall test.

  --gap        mean confidence vs actual recall rate, and each concept's error
  --calib      recall rate inside the high-confidence group -- is confidence earned there?
  --study      what a confidence-based plan restudies vs a recall-based plan; who is skipped
  --check      confidence overshoots recall; the confident group is miscalibrated; feeling-based study skips real failures

Stdlib only. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "judgments.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the statistics

def mean_confidence(concepts):
    return sum(c["confidence"] for c in concepts) / len(concepts)


def recall_rate(concepts):
    return sum(c["recalled"] for c in concepts) / len(concepts)


def overconfidence_gap(concepts):
    """How far mean confidence sits above the true recall rate."""
    return mean_confidence(concepts) - recall_rate(concepts)


def high_confidence(concepts, threshold=0.7):
    return [c for c in concepts if c["confidence"] >= threshold]


def failed(concepts):
    return [c for c in concepts if not c["recalled"]]


# ------------------------------------------------------------- study plans

def study_by_confidence(concepts, budget):
    """Restudy what FEELS weakest: the lowest-confidence concepts (the naive plan)."""
    ranked = sorted(concepts, key=lambda c: (c["confidence"], c["name"]))
    return ranked[:budget]


def study_by_recall(concepts, budget):
    """Restudy what you ACTUALLY failed: blanked concepts first (the honest plan)."""
    ranked = sorted(concepts, key=lambda c: (c["recalled"], c["name"]))
    return ranked[:budget]


def missed_failures(concepts, studied):
    """Failed concepts a study plan did NOT include -- real weaknesses left unstudied."""
    picked = {c["name"] for c in studied}
    return [c["name"] for c in failed(concepts) if c["name"] not in picked]


# ----------------------------------------------------------------- printing

def gap_view(data):
    cs = data["concepts"]
    print("GAP — self-rated confidence vs what was actually recalled")
    print("-" * 66)
    for c in cs:
        mark = "ok" if (c["confidence"] >= 0.5) == bool(c["recalled"]) else "<-- miscalibrated"
        print("  %-16s confidence=%.2f  recalled=%d  %s" % (c["name"], c["confidence"], c["recalled"], mark))
    print("-" * 66)
    print("  mean confidence = %.2f   actual recall rate = %.2f   overconfidence gap = %.2f"
          % (mean_confidence(cs), recall_rate(cs), overconfidence_gap(cs)))


def calib_view(data):
    cs = data["concepts"]
    hi = high_confidence(cs)
    print("CALIB — inside the high-confidence group (confidence >= 0.70)")
    print("-" * 66)
    for c in hi:
        print("  %-16s confidence=%.2f  recalled=%d" % (c["name"], c["confidence"], c["recalled"]))
    print("-" * 66)
    print("  %d concepts felt known; only %d were recalled -> recall rate %.0f%% in the group"
          % (len(hi), sum(c["recalled"] for c in hi), 100 * recall_rate(hi)))
    print("  mean confidence there was %.0f%% -- the confidence was not earned." % (100 * mean_confidence(hi)))


def study_view(data):
    cs, budget = data["concepts"], data["study_budget"]
    by_conf = study_by_confidence(cs, budget)
    by_recall = study_by_recall(cs, budget)
    print("STUDY — restudy %d concepts: by feeling vs by an actual recall test" % budget)
    print("-" * 66)
    print("  confidence-based restudies: %s" % [c["name"] for c in by_conf])
    print("    failed concepts it SKIPS:  %s" % missed_failures(cs, by_conf))
    print("  recall-based restudies:     %s" % [c["name"] for c in by_recall])
    print("    failed concepts it SKIPS:  %s" % missed_failures(cs, by_recall))
    print("-" * 66)
    print("  studying by feeling skips the overconfident-wrong concepts -- your real gaps.")


def check(data):
    print("SELF-TEST — confidence overshoots recall; the confident group is miscalibrated; feeling-based study skips failures")
    print("-" * 66)
    cs, budget = data["concepts"], data["study_budget"]

    gap = overconfidence_gap(cs)
    overconfident = gap > 0
    print("  mean confidence exceeds actual recall = %s (gap %.2f)" % (overconfident, gap))

    hi = high_confidence(cs)
    hi_miscalibrated = recall_rate(hi) < mean_confidence(hi)
    print("  the high-confidence group under-recalls its confidence = %s (recall %.2f < conf %.2f)"
          % (hi_miscalibrated, recall_rate(hi), mean_confidence(hi)))

    conf_skips = missed_failures(cs, study_by_confidence(cs, budget))
    feeling_skips_failures = len(conf_skips) > 0
    print("  confidence-based study skips real failures = %s (%s)" % (feeling_skips_failures, conf_skips))

    recall_skips = missed_failures(cs, study_by_recall(cs, budget))
    recall_covers = len(recall_skips) == 0
    print("  recall-based study covers every failure = %s (skips %s)" % (recall_covers, recall_skips))

    ok = overconfident and hi_miscalibrated and feeling_skips_failures and recall_covers
    print("-" * 66)
    print("SELF-TEST %s  overconfident=%s  hi_miscalibrated=%s  feeling_skips=%s  recall_covers=%s"
          % ("PASS" if ok else "FAIL", overconfident, hi_miscalibrated, feeling_skips_failures, recall_covers))
    return ok


def main():
    p = argparse.ArgumentParser(description="Calibrating judgments of learning against actual recall.")
    p.add_argument("--gap", action="store_true")
    p.add_argument("--calib", action="store_true")
    p.add_argument("--study", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("concepts=%d  study_budget=%d  file=%s  (confidence/recall pairs are a fixture)"
          % (len(data["concepts"]), data["study_budget"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.gap:
        gap_view(data)
    elif args.calib:
        calib_view(data)
    elif args.study:
        study_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
