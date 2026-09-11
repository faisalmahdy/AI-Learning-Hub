"""Migrate a schema in expand-contract steps, or a one-shot rename breaks the half-deployed fleet.

A rolling deploy never flips the whole fleet at once: for a window, old instances and new instances run
side by side against the same database. So a schema change has to be readable by BOTH versions during that
window. Rename a column in one step -- drop `name`, add `full_name` -- and there is no schema that satisfies
both: while `name` still exists the new instances (which read `full_name`) fail, and the moment you rename,
the old instances (which read `name`) fail. One deploy, and half your fleet is throwing errors on every
request until the rollout finishes. The rename is atomic in the database and catastrophic in the fleet.

The expand-contract (parallel-change) pattern makes the migration a sequence of individually-safe steps.
EXPAND: add the new column alongside the old, so the schema has both; new code reads the new column, old
code still reads the old one -- both work. Deploy the new code. BACKFILL: copy the data across. Only once
every instance is the new version do you CONTRACT: drop the old column. At no single moment does a running
version lack a column it needs, because you never remove the old column until nothing reads it and never
require the new one until it exists. The migration is spread over three deploys instead of one, and each is
backward compatible.

On this fixture the old version reads `name` and the new reads `full_name`. The one-shot rename has a step
where both versions run against a schema with only one of the columns -- so one version breaks. The
expand-contract plan has both columns present while both versions run, and drops the old column only after
the old version is gone: zero breaking steps. This computes both.

  --plan       each migration plan's steps: the schema and which versions are running
  --breaks     which steps break a running version, for each plan
  --check      the one-shot rename breaks a live version; expand-contract never does

The version column requirements and the migration plans are the fixture; every break is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "migration.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def broken_versions(step, requires):
    """Running versions whose required column is absent from this step's schema."""
    cols = set(step["cols"])
    return [v for v in step["running"] if requires[v] not in cols]


def breaking_steps(plan, requires):
    """Steps of a plan where at least one running version is broken."""
    return [(i, broken_versions(s, requires)) for i, s in enumerate(plan) if broken_versions(s, requires)]


# ----------------------------------------------------------------- printing

def plan_view(data):
    requires, plans = data["requires"], data["plans"]
    print("PLAN — each plan's steps (schema columns and running versions)")
    print("-" * 62)
    for name, plan in plans.items():
        print("  %s:" % name)
        for i, s in enumerate(plan):
            print("    step %d  cols %-22s running %s" % (i, s["cols"], s["running"]))
    print("-" * 62)
    print("  versions require: %s" % requires)


def breaks_view(data):
    requires, plans = data["requires"], data["plans"]
    print("BREAKS — steps that break a running version")
    print("-" * 62)
    for name, plan in plans.items():
        bs = breaking_steps(plan, requires)
        if bs:
            for i, broke in bs:
                print("  %-16s step %d BREAKS %s (cols %s)" % (name, i, broke, plan[i]["cols"]))
        else:
            print("  %-16s no breaking steps" % name)
    print("-" * 62)
    print("  only expand-contract is safe at every step.")


def check(data):
    print("SELF-TEST — the one-shot rename breaks a live version; expand-contract never does")
    print("-" * 90)
    requires, plans = data["requires"], data["plans"]
    one = plans["one-shot-rename"]
    exp = plans["expand-contract"]
    one_breaks = breaking_steps(one, requires)
    exp_breaks = breaking_steps(exp, requires)

    onestep_breaks = len(one_breaks) > 0
    print("  the one-shot rename has a breaking step = %s (%d)" % (onestep_breaks, len(one_breaks)))

    breaks_during_overlap = any(len(one[i]["running"]) > 1 for i, _ in one_breaks)
    print("  the break happens while both versions run (the deploy overlap) = %s" % breaks_during_overlap)

    expand_contract_safe = len(exp_breaks) == 0
    print("  expand-contract has no breaking step = %s" % expand_contract_safe)

    both_cols_during_overlap = all(set(requires.values()) <= set(s["cols"]) for s in exp if len(s["running"]) > 1)
    print("  expand-contract keeps both columns while both versions run = %s" % both_cols_during_overlap)

    contract_only_after_old_gone = all("old" not in s["running"] for s in exp if requires["old"] not in s["cols"])
    print("  the old column is dropped only after the old version is gone = %s" % contract_only_after_old_gone)

    ok = onestep_breaks and breaks_during_overlap and expand_contract_safe and both_cols_during_overlap and contract_only_after_old_gone
    print("-" * 90)
    print("SELF-TEST %s  onestep_breaks=%s  breaks_during_overlap=%s  expand_contract_safe=%s  both_cols_during_overlap=%s  contract_after_old_gone=%s"
          % ("PASS" if ok else "FAIL", onestep_breaks, breaks_during_overlap, expand_contract_safe, both_cols_during_overlap, contract_only_after_old_gone))
    return ok


def main():
    p = argparse.ArgumentParser(description="Migrate a schema in expand-contract steps so a rolling deploy never breaks.")
    p.add_argument("--plan", action="store_true")
    p.add_argument("--breaks", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("versions=%d  plans=%s  file=%s  (the requirements and plans are a fixture)"
          % (len(data["requires"]), list(data["plans"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.plan:
        plan_view(data)
    elif args.breaks:
        breaks_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
