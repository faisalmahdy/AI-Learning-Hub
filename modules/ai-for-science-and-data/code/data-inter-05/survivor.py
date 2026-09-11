#!/usr/bin/env python3
"""Survivorship bias: averaging over the survivors overstates -- the failures self-selected out.

The dataset you can get is usually the survivors: funds still trading, models still deployed,
users still active, planes that came back. The ones that failed are gone -- shut down, churned,
shot down -- and missing from the data. Computing a statistic over only the survivors is
biased, and not by a little, because survival was CAUSED by the very outcome you are measuring:
the good performers stayed, the bad ones left. So the survivor average is not an estimate of
the true average made noisy by a smaller sample; it is a systematically inflated number.

Here eight strategies, three of which blew up (return below the survive threshold) and would be
absent from a real dataset. The survivor-only mean is a healthy +10.2%. The full-cohort mean,
counting the failures, is -2.4% -- a loss. Same period, and the sign flips, purely from which
rows you were allowed to see. This measures the survivor mean, the full mean, and the bias.

  --cohort      every strategy, marked survived or failed, with the threshold
  --means       survivor-only mean vs full-cohort mean, and the bias between them
  --check       survivor mean overstates the full mean; the failures were the worst; the gap is large

Stdlib only. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "funds.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- survivorship

def survived(strategy, threshold):
    """A strategy survives if it did not blow up: return above the threshold."""
    return strategy["return_pct"] > threshold


def mean_return(strategies):
    return sum(s["return_pct"] for s in strategies) / len(strategies)


def survivors(strategies, threshold):
    return [s for s in strategies if survived(s, threshold)]


def failures(strategies, threshold):
    return [s for s in strategies if not survived(s, threshold)]


# ----------------------------------------------------------------- printing

def cohort_view(data):
    strats, thr = data["strategies"], data["survive_threshold"]
    print("COHORT — every strategy (survive if return > %.0f%%)" % thr)
    print("-" * 66)
    for s in strats:
        tag = "survived" if survived(s, thr) else "FAILED (missing from real data)"
        print("  %-4s return=%+6.1f%%  %s" % (s["id"], s["return_pct"], tag))
    print("-" * 66)
    print("  the FAILED rows are the ones a survivor-only dataset never shows you.")


def means_view(data):
    strats, thr = data["strategies"], data["survive_threshold"]
    surv = survivors(strats, thr)
    full = strats
    ms, mf = mean_return(surv), mean_return(full)
    print("MEANS — survivor-only vs full-cohort mean return")
    print("-" * 66)
    print("  survivor-only mean = %+6.2f%%  (n=%d, the data you'd actually have)" % (ms, len(surv)))
    print("  full-cohort mean   = %+6.2f%%  (n=%d, counting the failures)" % (mf, len(full)))
    print("  survivorship bias  = %+6.2f percentage points" % (ms - mf))
    print("-" * 66)
    print("  the survivor average overstates reality because the losers are invisible.")


def check(data):
    print("SELF-TEST — survivor mean overstates; failures were the worst; the gap is large")
    print("-" * 66)
    strats, thr = data["strategies"], data["survive_threshold"]
    surv = survivors(strats, thr)
    fail = failures(strats, thr)

    ms, mf = mean_return(surv), mean_return(strats)
    overstates = ms > mf
    print("  survivor-only mean exceeds the full-cohort mean = %s (%+.2f > %+.2f)" % (overstates, ms, mf))

    # The bias exists because the failures had worse returns than any survivor.
    worst_survivor = min(s["return_pct"] for s in surv)
    best_failure = max(s["return_pct"] for s in fail)
    failures_worse = best_failure < worst_survivor
    print("  every failure underperformed every survivor = %s (best fail %+.1f < worst surv %+.1f)"
          % (failures_worse, best_failure, worst_survivor))

    bias = ms - mf
    big_bias = bias > 5.0
    print("  the survivorship bias is substantial = %s (%+.2f points)" % (big_bias, bias))

    # The sign even flips here: survivors look profitable, the cohort actually lost money.
    sign_flip = ms > 0 and mf < 0
    print("  the bias flips the conclusion (survivors profit, cohort loses) = %s" % sign_flip)

    ok = overstates and failures_worse and big_bias and sign_flip
    print("-" * 66)
    print("SELF-TEST %s  overstates=%s  failures_worse=%s  big_bias=%s  sign_flip=%s"
          % ("PASS" if ok else "FAIL", overstates, failures_worse, big_bias, sign_flip))
    return ok


def main():
    p = argparse.ArgumentParser(description="Survivorship bias in a cohort statistic.")
    p.add_argument("--cohort", action="store_true")
    p.add_argument("--means", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("strategies=%d  survive_threshold=%.0f%%  file=%s  (returns are a fixture)"
          % (len(data["strategies"]), data["survive_threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.cohort:
        cohort_view(data)
    elif args.means:
        means_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
