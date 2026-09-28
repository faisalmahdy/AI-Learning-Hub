"""Canary the release to a slice of traffic first -- deploy straight to 100% and a bad version hits everyone.

Shipping a new version to all of production at once is a bet that it works, settled after everyone has
already been exposed. If the version is bad -- a regression that errors on a chunk of requests -- every
user hits it before anyone can react, and the blast radius is your entire traffic. A canary deployment
makes the bet cheap: route a small fraction of traffic to the new version, watch its error rate, and
only promote to 100% if it stays healthy. If the canary's errors cross a rollback threshold, you roll
back, and the rest of the traffic never leaves the old, known-good version.

The point is blast-radius control. A bad release still errors -- on the canary slice -- but only the
slice, and only until the threshold trips. The other 95% of traffic is protected by the rollback. A good
release sails through the canary and gets promoted, so the mechanism costs nothing when the version is
fine. You are buying a small, bounded exposure in exchange for never exposing everyone to an untested
version.

On this fixture 1000 requests face a release. Deployed straight to 100%, the bad version (30% error
rate) fails 300 requests. Canaried at 5%, its 50-request slice errors at 30% -- over the 10% threshold --
so it rolls back, and the remaining 950 requests stay on the old version at the 2% baseline: 34 failures
total instead of 300. The good version (2%, same as baseline) passes the canary and promotes with no
extra harm. This computes both.

  --releases   the candidate releases, their error rates, and the rollback threshold
  --deploy     failures under deploy-to-100% vs canary-with-rollback, for each release
  --check      the canary catches the bad release and shrinks its blast radius; it promotes the good one

The traffic, rates, and threshold are the fixture; every failure count and decision is computed. Stdlib.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "release.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- two deploy strategies

def deploy_full(total, release_rate, baseline, fraction, threshold):
    """Deploy to 100% at once: every request faces the new version."""
    failures = round(total * release_rate)
    return {"failures": failures, "decision": "all traffic on new version"}


def deploy_canary(total, release_rate, baseline, fraction, threshold):
    """Canary a slice; roll back if its error rate exceeds the threshold, else promote to 100%."""
    canary_n = round(total * fraction)
    canary_failures = round(canary_n * release_rate)
    rest = total - canary_n
    if release_rate > threshold:
        # roll back: the rest of the traffic stays on the old version at baseline
        rest_failures = round(rest * baseline)
        return {"failures": canary_failures + rest_failures, "decision": "ROLLED BACK", "canary_failures": canary_failures}
    # promote: the rest runs on the (healthy) new version
    rest_failures = round(rest * release_rate)
    return {"failures": canary_failures + rest_failures, "decision": "promoted", "canary_failures": canary_failures}


# ----------------------------------------------------------------- printing

def releases_view(data):
    print("RELEASES — candidate error rates vs the %.0f%% rollback threshold" % (data["rollback_threshold"] * 100))
    print("-" * 54)
    print("  baseline (old version): %.0f%%" % (data["baseline_error_rate"] * 100))
    for name, rate in data["releases"].items():
        verdict = "would roll back" if rate > data["rollback_threshold"] else "would promote"
        print("  %-6s release: %5.0f%%   %s" % (name, rate * 100, verdict))
    print("-" * 54)
    print("  canary sends %.0f%% of traffic first and reads the error rate before promoting."
          % (data["canary_fraction"] * 100))


def deploy_view(data):
    t, base, frac, thr = data["total_requests"], data["baseline_error_rate"], data["canary_fraction"], data["rollback_threshold"]
    print("DEPLOY — failures over %d requests: deploy-to-100%% vs canary" % t)
    print("-" * 66)
    for name, rate in data["releases"].items():
        full = deploy_full(t, rate, base, frac, thr)
        can = deploy_canary(t, rate, base, frac, thr)
        print("  %-6s release (%2.0f%%):  full deploy %3d failures   canary %3d failures (%s)"
              % (name, rate * 100, full["failures"], can["failures"], can["decision"]))
    print("-" * 66)
    print("  the bad release fails 300 at full deploy but only 34 when canaried and rolled back.")


def check(data):
    print("SELF-TEST — the canary catches the bad release and shrinks its blast radius; it promotes the good one")
    print("-" * 96)
    t, base, frac, thr = data["total_requests"], data["baseline_error_rate"], data["canary_fraction"], data["rollback_threshold"]
    bad, good = data["releases"]["bad"], data["releases"]["good"]

    bad_full = deploy_full(t, bad, base, frac, thr)
    bad_canary = deploy_canary(t, bad, base, frac, thr)

    canary_rolls_back = bad_canary["decision"] == "ROLLED BACK"
    print("  the canary rolls the bad release back = %s (%.0f%% > %.0f%% threshold)"
          % (canary_rolls_back, bad * 100, thr * 100))

    blast_radius_shrinks = bad_canary["failures"] < bad_full["failures"]
    print("  the canary shrinks the bad release's blast radius = %s (%d vs %d failures)"
          % (blast_radius_shrinks, bad_canary["failures"], bad_full["failures"]))

    good_canary = deploy_canary(t, good, base, frac, thr)
    good_promotes = good_canary["decision"] == "promoted"
    print("  the canary promotes the good release = %s (%.0f%% <= %.0f%% threshold)"
          % (good_promotes, good * 100, thr * 100))

    good_no_harm = good_canary["failures"] == round(t * base)
    print("  promoting the good release adds no failures over baseline = %s (%d = %d)"
          % (good_no_harm, good_canary["failures"], round(t * base)))

    ok = canary_rolls_back and blast_radius_shrinks and good_promotes and good_no_harm
    print("-" * 96)
    print("SELF-TEST %s  canary_rolls_back=%s  blast_radius_shrinks=%s  good_promotes=%s  good_no_harm=%s"
          % ("PASS" if ok else "FAIL", canary_rolls_back, blast_radius_shrinks, good_promotes, good_no_harm))
    return ok


def main():
    p = argparse.ArgumentParser(description="Canary the release to a slice of traffic before promoting to 100%.")
    p.add_argument("--releases", action="store_true")
    p.add_argument("--deploy", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("total=%d  canary=%.0f%%  baseline=%.0f%%  threshold=%.0f%%  file=%s  (the rates are a fixture)"
          % (data["total_requests"], data["canary_fraction"] * 100, data["baseline_error_rate"] * 100,
             data["rollback_threshold"] * 100, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.releases:
        releases_view(data)
    elif args.deploy:
        deploy_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
