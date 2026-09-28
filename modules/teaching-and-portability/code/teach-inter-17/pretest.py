"""Pretest before you teach, or you skip the failed attempt that makes the studying stick.

The intuitive order is study first, then test. But attempting a test BEFORE studying -- and getting most
of it wrong, because you have not learned the material yet -- improves how much you retain from the studying
that follows. The failed retrieval attempt is not wasted effort: it activates related knowledge, exposes the
exact gap, and generates a question the subsequent study answers, so the material is encoded more deeply than
if you had simply read it. This is the pretesting effect, and it is robust and replicated. The catch is that
the pretest itself looks like a disaster -- the learner answers almost nothing correctly -- so judging it by
its in-the-moment score says "this does not work," while the delayed test says the opposite.

That is the same trap the interleaving schedule falls into: the metric available DURING learning (here, the
pretest accuracy) points away from the method that wins the delayed test. The pretest scores near zero and
looks useless; the delayed retention it produces is higher than study-only. The whole effect is countable:
the delayed-test boost scales with how many items were pretested, so pretesting half the items yields half
the boost. This computes the pretest accuracy and the delayed retention for study-only, half-pretested, and
fully-pretested conditions, and shows the in-the-moment signal reverses against the outcome.

On this fixture study-only reaches 0.55 on the delayed test; pretesting every item reaches 0.75; pretesting
half reaches 0.65 -- exactly midway. Yet the pretest itself is answered at 0.05. This computes both.

  --conditions  each condition's pretested count and the in-the-moment pretest accuracy
  --retention   the delayed-test accuracy per condition, and how the boost scales with pretesting
  --check       the pretest looks like failure in the moment but wins the delayed test -- a reversal

The conditions and the learning-model constants are the fixture; every score is computed.
This is a stylized model of a replicated finding, deterministic. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "pretest.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def pretest_fraction(cond, n):
    """How much of the material was attempted as a pretest before studying."""
    return cond["pretested"] / n


def delayed_accuracy(cond, n, m):
    """Delayed-test accuracy: studying gets you study_gain; pretesting adds a boost scaled by how much you pretested."""
    return m["study_gain"] + m["max_pretest_boost"] * pretest_fraction(cond, n)


def immediate_pretest_accuracy(cond, m):
    """How the pretest itself scored -- near zero, because the learner has not studied yet."""
    return m["pretest_immediate_accuracy"] if cond["pretested"] > 0 else None


# ----------------------------------------------------------------- printing

def conditions_view(data):
    n, m = data["n_items"], data["model"]
    print("CONDITIONS — how much each learner pretested, and how the pretest itself scored (%d items)" % n)
    print("-" * 66)
    for c in data["conditions"]:
        imm = immediate_pretest_accuracy(c, m)
        imm_s = "%.2f" % imm if imm is not None else "  —  (no pretest)"
        print("  %-13s pretested %2d/%d   in-the-moment pretest accuracy %s" % (c["name"], c["pretested"], n, imm_s))
    print("-" * 66)
    print("  the pretest is answered at %.2f -- it looks like failure in the moment." % m["pretest_immediate_accuracy"])


def retention_view(data):
    n, m = data["n_items"], data["model"]
    print("RETENTION — delayed-test accuracy per condition")
    print("-" * 66)
    base = None
    for c in data["conditions"]:
        d = delayed_accuracy(c, n, m)
        if c["pretested"] == 0:
            base = d
        boost = "" if base is None else "   (+%.2f over study-only)" % (d - base)
        print("  %-13s delayed test %.2f%s" % (c["name"], d, boost if c["pretested"] > 0 else ""))
    print("-" * 66)
    print("  the boost scales with how many items were pretested: half pretested, half the boost.")


def check(data):
    print("SELF-TEST — the pretest looks like failure in the moment but wins the delayed test -- a reversal")
    print("-" * 104)
    n, m = data["n_items"], data["model"]
    by = {c["name"]: c for c in data["conditions"]}
    study = delayed_accuracy(by["study_only"], n, m)
    half = delayed_accuracy(by["pretest_half"], n, m)
    allp = delayed_accuracy(by["pretest_all"], n, m)
    imm = m["pretest_immediate_accuracy"]

    study_only_baseline = abs(study - m["study_gain"]) < 1e-9
    print("  study-only equals the study gain, no boost = %s (%.2f)" % (study_only_baseline, study))

    pretest_wins_delayed = allp > study
    print("  pretesting every item wins the delayed test = %s (%.2f > %.2f)" % (pretest_wins_delayed, allp, study))

    boost_scales_linearly = abs(half - (study + allp) / 2) < 1e-9
    print("  pretesting half gives half the boost (midway) = %s (%.2f vs %.2f)" % (boost_scales_linearly, half, (study + allp) / 2))

    pretest_looks_like_failure = imm < study
    print("  in the moment the pretest looks like failure = %s (pretest %.2f < study-only delayed %.2f)" % (pretest_looks_like_failure, imm, study))

    proxy_reversal = imm < study and allp > study
    print("  the in-the-moment signal reverses against the outcome = %s" % proxy_reversal)

    ok = study_only_baseline and pretest_wins_delayed and boost_scales_linearly and pretest_looks_like_failure and proxy_reversal
    print("-" * 104)
    print("SELF-TEST %s  study_only_baseline=%s  pretest_wins_delayed=%s  boost_scales_linearly=%s  pretest_looks_like_failure=%s  proxy_reversal=%s"
          % ("PASS" if ok else "FAIL", study_only_baseline, pretest_wins_delayed, boost_scales_linearly, pretest_looks_like_failure, proxy_reversal))
    return ok


def main():
    p = argparse.ArgumentParser(description="Pretest before teaching -- the failed attempt improves later retention.")
    p.add_argument("--conditions", action="store_true")
    p.add_argument("--retention", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("items=%d  conditions=%d  file=%s  (the conditions and model constants are a fixture)"
          % (data["n_items"], len(data["conditions"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.conditions:
        conditions_view(data)
    elif args.retention:
        retention_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
