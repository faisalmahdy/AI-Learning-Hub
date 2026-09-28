"""Don't fail readiness on a shared dependency, or one dependency blip pulls the whole fleet at once.

A readiness check tells the load balancer whether to send an instance traffic. The tempting thing is to make it
thorough: check the database, the cache, the downstream API, and report unhealthy if any of them is down. It feels
safe -- why route to an instance that cannot reach its database? But every instance shares that database, so when
it degrades, EVERY instance's readiness check fails at the same instant, the load balancer pulls all of them, and
there is nothing left to serve. A partial degradation of one dependency -- which the instances might have ridden
out on a cache or a fallback -- becomes a total, fleet-wide outage, and it happens the moment the dependency
blips. The check that was supposed to protect users took the whole service down.

The fix is to separate two questions. 'Can THIS instance serve a request?' is a local question -- is the process
up, is it out of memory, can it accept a connection -- and that is what readiness should answer, so the balancer
removes only instances that are genuinely broken. 'Is the shared dependency healthy?' is a different question, and
the answer to a degraded dependency is to serve in a degraded mode -- stale cache, a fallback, a partial response
-- not to remove every instance from rotation. A dependency's health belongs in the instance's request handling
(circuit breakers, fallbacks) and in your alerting, not in the readiness check that decides fleet membership.
Readiness is 'am I able to serve', not 'is everything downstream perfect'.

On this fixture 6 instances are all locally healthy while the shared dependency is down. A cascading readiness
check marks all 6 unhealthy -- 0 in rotation, a total outage. A local check keeps all 6 in rotation, serving
degraded but up. One dependency failure removes the entire fleet under the cascading check and none under the
local one. This computes both.

  --rotation   how many instances stay in the load-balancer rotation under each check, dependency up and down
  --blast      the blast radius: instances removed by one dependency failure under each design
  --check      the cascading check removes the whole fleet on a dependency blip; the local check keeps it serving

The fleet and statuses are the fixture; every count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "healthcheck.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def ready_cascading(local_ok, dependency_ok):
    """Cascading readiness: healthy only if the instance AND the shared dependency are healthy."""
    return local_ok and dependency_ok


def ready_local(local_ok, dependency_ok):
    """Local readiness: healthy if this instance can serve, regardless of the dependency."""
    return local_ok


def in_rotation(n, local_ok, dependency_ok, check):
    """How many of the n instances the load balancer keeps, given a readiness check."""
    return n if check(local_ok, dependency_ok) else 0


# ----------------------------------------------------------------- printing

def rotation_view(data):
    n, local = data["instances"], data["local_ok"]
    print("ROTATION — instances in the load-balancer rotation (fleet of %d, all locally healthy)" % n)
    print("-" * 62)
    print("  dependency   cascading check   local check")
    for dep in (True, False):
        print("  %-11s  %d of %d           %d of %d" % ("healthy" if dep else "DOWN",
              in_rotation(n, local, dep, ready_cascading), n, in_rotation(n, local, dep, ready_local), n))
    print("-" * 62)
    print("  when the dependency is down, the cascading check empties the rotation; the local check keeps it full.")


def blast_view(data):
    n, local = data["instances"], data["local_ok"]
    cascading_removed = n - in_rotation(n, local, False, ready_cascading)
    local_removed = n - in_rotation(n, local, False, ready_local)
    print("BLAST — instances removed by ONE shared-dependency failure")
    print("-" * 62)
    print("  cascading check:  %d of %d removed   (the whole fleet -> total outage)" % (cascading_removed, n))
    print("  local check:      %d of %d removed   (none -> degraded but serving)" % (local_removed, n))
    print("-" * 62)
    print("  cascading readiness makes one dependency the single point of failure for the entire fleet.")


def check(data):
    print("SELF-TEST — the cascading check removes the whole fleet on a dependency blip; the local check keeps it serving")
    print("-" * 108)
    n, local = data["instances"], data["local_ok"]

    cascading_empties = in_rotation(n, local, False, ready_cascading) == 0
    print("  cascading check empties the rotation when the dependency is down = %s (%d in rotation)" % (cascading_empties, in_rotation(n, local, False, ready_cascading)))

    local_keeps_all = in_rotation(n, local, False, ready_local) == n
    print("  local check keeps the whole fleet in rotation when the dependency is down = %s (%d of %d)" % (local_keeps_all, in_rotation(n, local, False, ready_local), n))

    agree_when_healthy = in_rotation(n, local, True, ready_cascading) == in_rotation(n, local, True, ready_local) == n
    print("  both checks agree (all in rotation) when the dependency is healthy = %s" % agree_when_healthy)

    cascade_blast_is_fleet = (n - in_rotation(n, local, False, ready_cascading)) == n
    print("  one dependency failure removes the entire fleet under cascading = %s (blast %d = %d)" % (cascade_blast_is_fleet, n - in_rotation(n, local, False, ready_cascading), n))

    local_blast_is_zero = (n - in_rotation(n, local, False, ready_local)) == 0
    print("  the same failure removes nothing under the local check = %s" % local_blast_is_zero)

    ok = cascading_empties and local_keeps_all and agree_when_healthy and cascade_blast_is_fleet and local_blast_is_zero
    print("-" * 108)
    print("SELF-TEST %s  cascading_empties=%s  local_keeps_all=%s  agree_when_healthy=%s  cascade_blast_is_fleet=%s  local_blast_is_zero=%s"
          % ("PASS" if ok else "FAIL", cascading_empties, local_keeps_all, agree_when_healthy, cascade_blast_is_fleet, local_blast_is_zero))
    return ok


def main():
    p = argparse.ArgumentParser(description="A readiness check that fails on a shared dependency turns one dependency blip into a fleet-wide outage; a local check keeps the fleet serving degraded.")
    p.add_argument("--rotation", action="store_true")
    p.add_argument("--blast", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("instances=%d  local_ok=%s  dependency_ok=%s  file=%s  (the fleet is a fixture)"
          % (data["instances"], data["local_ok"], data["dependency_ok"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.rotation:
        rotation_view(data)
    elif args.blast:
        blast_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
