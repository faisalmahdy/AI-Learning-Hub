"""Choose fail-open vs fail-closed per check, not with one blanket rule -- when a check's backing service is down, a security check must fail closed (deny) or its outage becomes a bypass, and a non-critical enrichment must fail open (allow) or its outage takes down the whole request.

Every request runs through checks that call other services: an authorization check asks an auth service if the user may proceed, a rate limiter asks if the user is within quota, a personalization step asks an enrichment service for extras. Each of those calls can fail -- the dependency times out or is down -- and the design has to answer one question for each: when the check cannot run, does the request proceed or stop?

'Fail open' proceeds as if the check passed; 'fail closed' treats the failure as a rejection. The instinct is to pick one and apply it everywhere, but the correct choice is opposite for the two kinds of check. A security or safety check exists precisely to deny -- if it cannot run, allowing the request defeats its entire purpose, so it must fail closed. Let authorization fail open and an outage of the auth service becomes an authorization bypass: everyone gets in exactly when the guard is blind. A non-critical enrichment exists only to make the response nicer -- if it cannot run, the request is still valid, so it must fail open. Let recommendations fail closed and an outage of a cosmetic service takes down the whole page for want of a widget.

That is why a single blanket rule is wrong. Blanket fail-open sacrifices the critical checks during their outage -- an availability-first default that quietly disables the guards. Blanket fail-closed sacrifices availability during a non-critical outage -- a security-first default that lets a trivial dependency fail the whole request. Only a per-check policy -- critical fails closed, non-critical fails open -- is right for both, and it has to be a deliberate, declared property of each check, not whatever the code happens to do when an exception is thrown.

The rule: decide fail-open vs fail-closed for each dependency check by whether it enforces security or safety -- those fail closed (deny on failure), non-critical ones fail open (allow on failure) -- because a blanket fail-open turns a security check's outage into a bypass and a blanket fail-closed turns a cosmetic check's outage into an outage of the whole request.

On this fixture two checks are critical (authorization, rate limit) and two are not (recommendations, related items). Blanket fail-open bypasses the two critical checks during an outage; blanket fail-closed blocks the request over the two non-critical ones; the deliberate policy denies only on the critical ones. This computes all three.

  --outcomes   for each check, the request outcome under blanket open, blanket closed, and per-check policy
  --danger     the checks each blanket rule gets wrong -- bypassed critical checks, or needless blocks
  --check      blanket fail-open bypasses critical checks; blanket fail-closed blocks on trivial ones; per-check is right

checks is the fixture; the outcomes under the three policies are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "failopen.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def blanket_open(check):
    """Allow every check on failure (availability-first blanket rule)."""
    return "allow"


def blanket_closed(check):
    """Deny every check on failure (security-first blanket rule)."""
    return "deny"


def per_check(check):
    """Deliberate: a critical check fails closed (deny), a non-critical one fails open (allow)."""
    return "deny" if check["critical"] else "allow"


# ----------------------------------------------------------------- printing

def outcomes_view(data):
    print("OUTCOMES — request outcome when each check's service is down")
    print("-" * 64)
    print("  check            critical   blanket-open   blanket-closed   per-check")
    for c in data["checks"]:
        print("  %-15s  %-8s   %-12s   %-14s   %s"
              % (c["name"], c["critical"], blanket_open(c), blanket_closed(c), per_check(c)))
    print("-" * 64)
    print("  per-check denies exactly the critical checks and allows the rest")


def danger_view(data):
    checks = data["checks"]
    bypassed = [c["name"] for c in checks if c["critical"] and blanket_open(c) == "allow"]
    blocked = [c["name"] for c in checks if not c["critical"] and blanket_closed(c) == "deny"]
    print("DANGER — what each blanket rule gets wrong")
    print("-" * 60)
    print("  blanket fail-open  bypasses these critical checks: %s" % bypassed)
    print("  blanket fail-closed blocks on these non-critical checks: %s" % blocked)
    print("-" * 60)
    print("  each blanket rule sacrifices the side it does not favor")


def check(data):
    print("SELF-TEST — blanket fail-open bypasses critical checks; blanket fail-closed blocks on trivial ones; per-check is right")
    print("-" * 120)
    checks = data["checks"]

    open_bypasses_critical = any(c["critical"] and blanket_open(c) == "allow" for c in checks)
    print("  blanket fail-open lets a critical check through on failure = %s" % open_bypasses_critical)

    closed_blocks_noncritical = any((not c["critical"]) and blanket_closed(c) == "deny" for c in checks)
    print("  blanket fail-closed blocks a non-critical check on failure = %s" % closed_blocks_noncritical)

    per_check_denies_critical = all(per_check(c) == "deny" for c in checks if c["critical"])
    print("  per-check: every critical check fails closed (deny) = %s" % per_check_denies_critical)

    per_check_allows_noncritical = all(per_check(c) == "allow" for c in checks if not c["critical"])
    print("  per-check: every non-critical check fails open (allow) = %s" % per_check_allows_noncritical)

    # each blanket rule matches per-check on some checks but is wrong on at least one
    open_wrong_somewhere = any(blanket_open(c) != per_check(c) for c in checks)
    closed_wrong_somewhere = any(blanket_closed(c) != per_check(c) for c in checks)
    no_blanket_is_right = open_wrong_somewhere and closed_wrong_somewhere
    print("  neither blanket rule matches the per-check policy everywhere = %s" % no_blanket_is_right)

    ok = (open_bypasses_critical and closed_blocks_noncritical and per_check_denies_critical
          and per_check_allows_noncritical and no_blanket_is_right)
    print("-" * 120)
    print("SELF-TEST %s  open_bypasses_critical=%s  closed_blocks_noncritical=%s  per_check_denies_critical=%s  per_check_allows_noncritical=%s  no_blanket_is_right=%s"
          % ("PASS" if ok else "FAIL", open_bypasses_critical, closed_blocks_noncritical,
             per_check_denies_critical, per_check_allows_noncritical, no_blanket_is_right))
    return ok


def main():
    p = argparse.ArgumentParser(description="Fail open vs fail closed: decide it for each dependency check by whether it enforces security or safety -- those fail closed (deny on failure), non-critical ones fail open (allow on failure) -- because a blanket fail-open turns a security check's outage into a bypass and a blanket fail-closed turns a cosmetic check's outage into an outage of the whole request.")
    p.add_argument("--outcomes", action="store_true")
    p.add_argument("--danger", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    crit = sum(c["critical"] for c in data["checks"])
    print("checks=%d  critical=%d  non_critical=%d  file=%s  (the checks are a fixture)"
          % (len(data["checks"]), crit, len(data["checks"]) - crit, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.outcomes:
        outcomes_view(data)
    elif args.danger:
        danger_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
