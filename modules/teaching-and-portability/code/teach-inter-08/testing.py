"""Retrieval practice beats re-reading -- the study that feels easy builds the weakest memory.

Give a learner the same material and the same study time and let them spend it two ways.
Re-reading (restudy) passes the eyes over the text again: it feels fluent, smooth, like the
material is sinking in. Retrieval practice (self-testing) puts the book away and forces recall
from memory: it feels effortful, halting, like it is not working. The feeling is exactly
backwards. The act of retrieving a memory strengthens it far more than seeing it again does, so
for the same number of exposures the tested learner remembers much more later -- while the
re-reader, lulled by fluency, remembers less and is more confident about it.

This models memory strength accumulating per exposure (retrieval adds more than restudy), a
retention decay over the delay before the test, and the in-the-moment fluency each method
produces. Over 4 exposures the re-reader reaches 0.63 retention and the self-tester 0.89 -- same
time, same material -- yet re-reading feels far more fluent (0.90 vs 0.40), so a learner who
picks a study method by how well it feels picks the one that teaches least. This computes both
methods' retention and fluency and shows the fluency signal points the wrong way.

  --methods    each study method's exposures, memory strength, retention, and in-study fluency
  --choose     the method a fluency-driven learner picks vs the one that maximizes retention
  --check      retrieval yields higher retention while feeling less fluent -- fluency misleads

The gains, decay, and fluency values are the fixture; every retention is computed. This is a
stylized model of a replicated finding. Deterministic; stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "study.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the memory model

def strength(method, m):
    """Memory strength after the study exposures: gain-per-exposure times the number of exposures."""
    return m["exposures"] * m["gain"][method]


def retention(method, data):
    """Retention after the delay: saturating in strength, then decayed by the retention interval."""
    s = strength(method, data)
    learned = 1 - math.exp(-s)            # diminishing returns of more strength
    return round(learned * data["retention_decay"], 4)


def fluency(method, data):
    """How fluent the method feels DURING study -- the (misleading) in-the-moment signal."""
    return data["fluency"][method]


# ----------------------------------------------------------------- printing

def methods_view(data):
    print("METHODS — same %d exposures, same material; retention vs in-study fluency" % data["exposures"])
    print("-" * 66)
    print("  method     gain/exp  strength  retention  fluency (feels like)")
    for name in data["order"]:
        print("  %-10s %-9.2f %-9.2f %-10.4f %.2f"
              % (name, data["gain"][name], strength(name, data), retention(name, data), fluency(name, data)))
    print("-" * 66)
    print("  retrieval builds more strength per exposure but feels less fluent while you do it.")


def choose_view(data):
    by_fluency = max(data["order"], key=lambda n: fluency(n, data))
    by_retention = max(data["order"], key=lambda n: retention(n, data))
    print("CHOOSE — study method by how it feels vs by what it teaches")
    print("-" * 66)
    print("  pick by fluency (feels best):   %-10s -> retention %.4f"
          % (by_fluency, retention(by_fluency, data)))
    print("  pick by retention (works best): %-10s -> retention %.4f"
          % (by_retention, retention(by_retention, data)))
    print("-" * 66)
    print("  the fluent method is the weaker teacher; feeling is the wrong signal to choose by.")


def check(data):
    print("SELF-TEST — retrieval yields higher retention while feeling less fluent")
    print("-" * 66)
    restudy, test = data["restudy"], data["test"]

    same_exposures = strength(restudy, data) / data["gain"][restudy] == strength(test, data) / data["gain"][test]
    print("  both methods used the same number of exposures (same time) = %s (%d each)"
          % (same_exposures, data["exposures"]))

    test_retains_more = retention(test, data) > retention(restudy, data)
    print("  retrieval practice yields higher retention = %s (%.4f vs %.4f)"
          % (test_retains_more, retention(test, data), retention(restudy, data)))

    restudy_feels_better = fluency(restudy, data) > fluency(test, data)
    print("  re-reading feels more fluent during study = %s (%.2f vs %.2f)"
          % (restudy_feels_better, fluency(restudy, data), fluency(test, data)))

    by_fluency = max(data["order"], key=lambda n: fluency(n, data))
    by_retention = max(data["order"], key=lambda n: retention(n, data))
    fluency_misleads = by_fluency != by_retention
    print("  the method that feels best is NOT the one that teaches best = %s (feels:%s, teaches:%s)"
          % (fluency_misleads, by_fluency, by_retention))

    ok = same_exposures and test_retains_more and restudy_feels_better and fluency_misleads
    print("-" * 66)
    print("SELF-TEST %s  same_exposures=%s  test_retains_more=%s  restudy_feels_better=%s  fluency_misleads=%s"
          % ("PASS" if ok else "FAIL", same_exposures, test_retains_more, restudy_feels_better, fluency_misleads))
    return ok


def main():
    p = argparse.ArgumentParser(description="Retrieval practice vs re-reading: retention vs fluency.")
    p.add_argument("--methods", action="store_true")
    p.add_argument("--choose", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("exposures=%d  decay=%.2f  file=%s  (gains, decay, and fluency are a fixture)"
          % (data["exposures"], data["retention_decay"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.methods:
        methods_view(data)
    elif args.choose:
        choose_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
