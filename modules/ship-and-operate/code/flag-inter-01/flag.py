"""Ship features behind a runtime flag, so a bad feature is disabled in place -- rolling the deploy back to before it also reverts every good feature shipped since, because they all live in later versions of the same artifact.

When release is coupled to deploy, a feature goes live the instant its code deploys, and the only way to turn it off is another deploy. That is fine until a feature already in production turns out to be broken and you need it gone now.

To disable it, you roll the deployable artifact back to the version before that feature was introduced. But every feature deployed after it is baked into later versions of that same artifact, so rolling back past the bug takes those later features with it. You remove the broken checkout flow and, in the same motion, remove the search filters and dark mode that shipped afterward and were working perfectly. The alternative -- writing and deploying a forward fix -- costs the time an incident does not have.

A feature flag breaks the coupling. The feature's code is deployed but gated behind a runtime flag that defaults off or can be turned off; releasing the feature is flipping the flag, and disabling it is flipping it back. That is a configuration change, not a deploy, so it disables exactly the one feature and leaves every other deployed feature -- flagged or not -- running. Deploy ships the code; the flag releases the feature; and the two being separate is what lets you undo a release without undoing a deploy.

On this fixture three features are deployed in order and the first, checkout_v2, is buggy. Rolling back to before it leaves nothing live -- search_filters and dark_mode, shipped after, are reverted too. Flipping checkout_v2's flag off leaves search_filters and dark_mode running. This computes both.

  --rollback  disable the bug by rolling the deploy back to before it: the later good features go too
  --flag      disable the bug by flipping its flag off: only that feature is gone
  --check     the rollback reverts the good features shipped after the bug while the flag disables only the buggy one

deploys and which one is buggy are the fixture; the live features and the good features lost under each approach are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "flag.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def buggy_index(deploys):
    """The position in deploy order of the feature that must be disabled."""
    return next(i for i, d in enumerate(deploys) if d["buggy"])


def live_after_rollback(deploys):
    """Rolling the artifact back to before the bug keeps only the features deployed before it."""
    return [d["name"] for d in deploys[:buggy_index(deploys)]]


def live_after_flag(deploys):
    """Flipping the bug's flag off keeps every deployed feature except the one flagged off."""
    return [d["name"] for d in deploys if not d["buggy"]]


def good_features_lost(deploys, live):
    """Non-buggy features that were deployed but are not live under this mitigation."""
    return [d["name"] for d in deploys if not d["buggy"] and d["name"] not in live]


# ----------------------------------------------------------------- printing

def rollback_view(data):
    deploys = data["deploys"]
    live = live_after_rollback(deploys)
    bug = deploys[buggy_index(deploys)]["name"]
    print("ROLLBACK — disable the bug by reverting the deploy to before it")
    print("-" * 64)
    print("  deploy order: %s" % [d["name"] for d in deploys])
    print("  roll back to before %r -> live features: %s" % (bug, live))
    print("  good features lost: %s" % good_features_lost(deploys, live))
    print("  needed a new deploy? yes")
    print("-" * 64)
    print("  the bug is gone, but so is every good feature shipped after it")


def flag_view(data):
    deploys = data["deploys"]
    live = live_after_flag(deploys)
    bug = deploys[buggy_index(deploys)]["name"]
    print("FLAG — disable the bug by flipping its runtime flag off")
    print("-" * 64)
    print("  deploy order: %s" % [d["name"] for d in deploys])
    print("  flag %r off -> live features: %s" % (bug, live))
    print("  good features lost: %s" % good_features_lost(deploys, live))
    print("  needed a new deploy? no (a config change)")
    print("-" * 64)
    print("  only the buggy feature is gone; the rest keep running")


def check(data):
    print("SELF-TEST — the rollback reverts the good features shipped after the bug while the flag disables only the buggy one")
    print("-" * 112)
    deploys = data["deploys"]
    bug = deploys[buggy_index(deploys)]["name"]
    rb_live = live_after_rollback(deploys)
    fl_live = live_after_flag(deploys)

    bug_deployed_first = buggy_index(deploys) == 0
    print("  the buggy feature was deployed before good ones = %s (%r first)" % (bug_deployed_first, bug))

    rollback_disables_bug = bug not in rb_live
    print("  rollback disables the bug = %s" % rollback_disables_bug)

    rollback_reverts_good = len(good_features_lost(deploys, rb_live)) > 0
    print("  rollback also reverts good features shipped after it = %s (%s)" % (rollback_reverts_good, good_features_lost(deploys, rb_live)))

    flag_disables_bug = bug not in fl_live
    print("  the flag disables the bug = %s" % flag_disables_bug)

    flag_keeps_good = good_features_lost(deploys, fl_live) == []
    print("  the flag keeps every good feature = %s (live %s)" % (flag_keeps_good, fl_live))

    ok = (bug_deployed_first and rollback_disables_bug and rollback_reverts_good
          and flag_disables_bug and flag_keeps_good)
    print("-" * 112)
    print("SELF-TEST %s  bug_deployed_first=%s  rollback_disables_bug=%s  rollback_reverts_good=%s  flag_disables_bug=%s  flag_keeps_good=%s"
          % ("PASS" if ok else "FAIL", bug_deployed_first, rollback_disables_bug, rollback_reverts_good,
             flag_disables_bug, flag_keeps_good))
    return ok


def main():
    p = argparse.ArgumentParser(description="Feature flags: ship features behind runtime flags so a bad feature can be disabled in place with a config change, because the only alternative -- rolling the deploy back to before the feature -- also reverts every good feature shipped into later versions of the same artifact, coupling the release you want to undo to deploys you do not.")
    p.add_argument("--rollback", action="store_true")
    p.add_argument("--flag", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("deploys=%s  buggy=%r  file=%s  (these are a fixture)"
          % ([d["name"] for d in data["deploys"]], data["deploys"][buggy_index(data["deploys"])]["name"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rollback:
        rollback_view(data)
    elif args.flag:
        flag_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
