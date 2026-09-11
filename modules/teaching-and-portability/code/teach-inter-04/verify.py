#!/usr/bin/env python3
"""'Ready' is derived from checkable facts -- never trust the status a module claims.

Every module carries a status field its author set: ready or draft. That field is a
CLAIM, and a claim is not evidence. A portable knowledge artifact -- one someone else
can pick up and trust -- has to let a reader DERIVE readiness from facts they can check
themselves: are the required sections present, did the self-test pass, is there a dated
recall log. The hub's build gate works exactly this way, and this module is that
principle turned on the modules' own status fields.

The failure is a dashboard that counts readiness off the claimed field. It reports the
authors' optimism, not the state of the work: modules marked ready that fail a criterion
(overclaims) are counted as done, and modules marked draft that actually meet every
criterion (underclaims) are missed. The reader-derived count is the honest one, and it
disagrees with the claimed count. This measures the gap and finds the overclaimers.

  --derive      each module's claimed vs derived status, and why
  --audit       the overclaimers (ready but not really) and underclaimers (done but modest)
  --count       claimed-ready vs derived-ready totals -- the dashboard bug
  --check       claimed and derived disagree; overclaimers exist; derived-ready meets every criterion

Stdlib only. Deterministic.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "manifest.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------- deriving status from facts

def derived_status(module, criteria):
    """READY only if every required criterion is true; otherwise draft. Facts, not claims."""
    return "ready" if all(module[c] for c in criteria) else "draft"


def failed_criteria(module, criteria):
    return [c for c in criteria if not module[c]]


def overclaimers(modules, criteria):
    """Marked ready, but a criterion fails -- claimed readiness the facts do not support."""
    return [m for m in modules if m["claimed_status"] == "ready" and derived_status(m, criteria) == "draft"]


def underclaimers(modules, criteria):
    """Marked draft, but every criterion holds -- done work the claim undersells."""
    return [m for m in modules if m["claimed_status"] == "draft" and derived_status(m, criteria) == "ready"]


# ----------------------------------------------------------------- printing

def derive_view(data):
    mods, crit = data["modules"], data["required_criteria"]
    print("DERIVE — claimed status vs status derived from the facts")
    print("-" * 66)
    for m in mods:
        d = derived_status(m, crit)
        flag = "" if d == m["claimed_status"] else "  <-- MISMATCH"
        miss = failed_criteria(m, crit)
        why = "" if not miss else "  (fails: %s)" % ", ".join(miss)
        print("  %-7s claimed=%-5s derived=%-5s%s%s" % (m["id"], m["claimed_status"], d, flag, why))
    print("-" * 66)
    print("  derived status is computed from facts; the claim is just what the author wrote.")


def audit_view(data):
    mods, crit = data["modules"], data["required_criteria"]
    over = overclaimers(mods, crit)
    under = underclaimers(mods, crit)
    print("AUDIT — overclaimers (ready but not) and underclaimers (done but modest)")
    print("-" * 66)
    print("  OVERCLAIMERS (trust these at your peril):")
    for m in over:
        print("     %-7s marked ready, fails: %s" % (m["id"], ", ".join(failed_criteria(m, crit))))
    print("  UNDERCLAIMERS (actually done, marked draft):")
    for m in under:
        print("     %-7s marked draft, meets every criterion" % m["id"])
    print("-" * 66)
    print("  the claim disagrees with the facts in both directions.")


def count_view(data):
    mods, crit = data["modules"], data["required_criteria"]
    claimed_ready = [m for m in mods if m["claimed_status"] == "ready"]
    derived_ready = [m for m in mods if derived_status(m, crit) == "ready"]
    print("COUNT — how many modules are 'ready', by claim vs by facts")
    print("-" * 66)
    print("  claimed ready = %d  %s" % (len(claimed_ready), [m["id"] for m in claimed_ready]))
    print("  derived ready = %d  %s" % (len(derived_ready), [m["id"] for m in derived_ready]))
    print("-" * 66)
    print("  a dashboard reading the claimed field over-reports readiness by %d module(s)."
          % (len(claimed_ready) - len(derived_ready)))


def check(data):
    print("SELF-TEST — claim and facts disagree; overclaimers exist; derived-ready meets every criterion")
    print("-" * 66)
    mods, crit = data["modules"], data["required_criteria"]

    mismatches = [m for m in mods if derived_status(m, crit) != m["claimed_status"]]
    disagree = len(mismatches) > 0
    print("  claimed and derived status disagree for some module = %s (%d modules)" % (disagree, len(mismatches)))

    over = overclaimers(mods, crit)
    overclaims_exist = len(over) > 0
    print("  overclaimers exist (ready but fail a criterion) = %s (%s)"
          % (overclaims_exist, [m["id"] for m in over]))

    under = underclaimers(mods, crit)
    underclaims_exist = len(under) > 0
    print("  underclaimers exist (draft but meet all) = %s (%s)"
          % (underclaims_exist, [m["id"] for m in under]))

    # Every derived-ready module really does pass all criteria -- the derivation is sound.
    derived_ready = [m for m in mods if derived_status(m, crit) == "ready"]
    all_derived_valid = all(all(m[c] for c in crit) for m in derived_ready)
    print("  every derived-ready module passes all criteria = %s" % all_derived_valid)

    # The claimed count over-reports vs the derived count.
    claimed_n = sum(1 for m in mods if m["claimed_status"] == "ready")
    over_reports = claimed_n > len(derived_ready)
    print("  claimed-ready count over-reports the derived count = %s (%d > %d)"
          % (over_reports, claimed_n, len(derived_ready)))

    ok = disagree and overclaims_exist and underclaims_exist and all_derived_valid and over_reports
    print("-" * 66)
    print("SELF-TEST %s  disagree=%s  overclaims=%s  underclaims=%s  derivation_sound=%s  over_reports=%s"
          % ("PASS" if ok else "FAIL", disagree, overclaims_exist, underclaims_exist, all_derived_valid, over_reports))
    return ok


def main():
    p = argparse.ArgumentParser(description="Reader-derived readiness vs author-claimed status.")
    p.add_argument("--derive", action="store_true")
    p.add_argument("--audit", action="store_true")
    p.add_argument("--count", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("modules=%d  criteria=%s  file=%s  (statuses and facts are a fixture)"
          % (len(data["modules"]), data["required_criteria"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.derive:
        derive_view(data)
    elif args.audit:
        audit_view(data)
    elif args.count:
        count_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
