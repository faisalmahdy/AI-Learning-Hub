"""Liveness and readiness are different checks -- conflate them and you route to a broken instance.

An orchestrator asks each instance one question to make two decisions, and that is the bug.
The two decisions are: should I restart this instance (is the process wedged?), and should I
send it traffic (can it actually serve a request right now?). They are not the same question. A
freshly-started instance is alive but still loading its model -- do not restart it, but do not
route to it either. An instance whose database connection dropped is alive -- restarting it may
not help -- but it cannot serve, so route away from it. A single 'healthy?' check cannot answer
both, and whichever decision you wire it to, the other breaks.

The fix is two probes. Liveness answers 'is the process wedged?' and drives restarts. Readiness
answers 'can it serve right now?' -- alive AND dependencies up AND done warming -- and drives
routing. On this fleet of four instances a naive load balancer that routes by liveness sends
traffic to three instances and two of them fail (one warming, one with a dead dependency),
while a readiness-gated balancer routes only to the one instance that can serve and drops
nothing; meanwhile restarts correctly target only the one crashed process, not the warming or
dependency-degraded ones that just need to be left alone. This computes both routings and both
restart sets and shows the conflation failing each way.

  --fleet      each instance's liveness, readiness, and why they differ
  --route      naive (route-by-liveness) vs readiness-gated routing, and the requests each drops
  --check      liveness routing hits a non-serving instance; readiness routing drops nothing; restarts target only the dead

The instance states are the fixture; every routing and restart decision is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "fleet.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- the two probes

def is_live(inst):
    """Liveness: is the process running at all? Drives the restart decision."""
    return inst["alive"]


def is_ready(inst):
    """Readiness: can it serve a request right now? Alive AND deps up AND done warming. Drives routing."""
    return inst["alive"] and inst["deps_ok"] and not inst["warming"]


# ------------------------------------------------------------- routing and restarting

def route_targets(fleet, by_readiness):
    """Instances the load balancer will send traffic to."""
    probe = is_ready if by_readiness else is_live
    return [i["id"] for i in fleet if probe(i)]


def failures(fleet, targets):
    """Of the routed instances, which cannot actually serve (routed but not ready)."""
    ready = {i["id"] for i in fleet if is_ready(i)}
    return [t for t in targets if t not in ready]


def restart_targets(fleet):
    """Restart exactly the instances whose process is wedged -- keyed on liveness, not readiness."""
    return [i["id"] for i in fleet if not is_live(i)]


# ----------------------------------------------------------------- printing

def fleet_view(data):
    print("FLEET — liveness (restart signal) vs readiness (routing signal)")
    print("-" * 68)
    print("  id     alive  deps_ok  warming  live  ready  note")
    for i in data["fleet"]:
        note = ("serving" if is_ready(i) else
                "crashed" if not i["alive"] else
                "warming up" if i["warming"] else
                "dependency down")
        print("  %-6s %-6s %-8s %-8s %-5s %-6s %s"
              % (i["id"], i["alive"], i["deps_ok"], i["warming"], is_live(i), is_ready(i), note))
    print("-" * 68)
    print("  live-but-not-ready instances are the trap: don't restart them, don't route to them.")


def route_view(data):
    fleet = data["fleet"]
    naive = route_targets(fleet, by_readiness=False)
    ready = route_targets(fleet, by_readiness=True)
    print("ROUTE — naive (by liveness) vs readiness-gated")
    print("-" * 68)
    print("  route by liveness:  %s   -> failures: %s" % (naive, failures(fleet, naive)))
    print("  route by readiness: %s   -> failures: %s" % (ready, failures(fleet, ready)))
    print("  restart targets (by liveness): %s" % restart_targets(fleet))
    print("-" * 68)
    print("  the naive router sends traffic to instances that are alive but cannot serve.")


def check(data):
    print("SELF-TEST — liveness routing hits a non-serving instance; readiness routing drops nothing")
    print("-" * 68)
    fleet = data["fleet"]

    naive = route_targets(fleet, by_readiness=False)
    naive_fail = failures(fleet, naive)
    naive_routes_broken = len(naive_fail) > 0
    print("  routing by liveness sends traffic to non-serving instances = %s (%s)"
          % (naive_routes_broken, naive_fail))

    ready = route_targets(fleet, by_readiness=True)
    ready_fail = failures(fleet, ready)
    readiness_clean = len(ready_fail) == 0 and len(ready) > 0
    print("  routing by readiness drops nothing and still has a target = %s (targets %s)"
          % (readiness_clean, ready))

    # at least one instance where liveness and readiness disagree -- the whole reason for two probes
    differ = [i["id"] for i in fleet if is_live(i) != is_ready(i)]
    probes_differ = len(differ) > 0
    print("  some instance is live but not ready (the two probes disagree) = %s (%s)" % (probes_differ, differ))

    # restarts target exactly the dead processes, not the merely-not-ready ones
    restarts = restart_targets(fleet)
    dead = [i["id"] for i in fleet if not i["alive"]]
    restart_correct = set(restarts) == set(dead) and any(i["id"] not in restarts and not is_ready(i) for i in fleet)
    print("  restarts target only crashed processes, sparing warming/degraded ones = %s (%s)"
          % (restart_correct, restarts))

    ok = naive_routes_broken and readiness_clean and probes_differ and restart_correct
    print("-" * 68)
    print("SELF-TEST %s  naive_routes_broken=%s  readiness_clean=%s  probes_differ=%s  restart_correct=%s"
          % ("PASS" if ok else "FAIL", naive_routes_broken, readiness_clean, probes_differ, restart_correct))
    return ok


def main():
    p = argparse.ArgumentParser(description="Liveness vs readiness: two probes, two decisions.")
    p.add_argument("--fleet", action="store_true")
    p.add_argument("--route", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("instances=%d  file=%s  (the instance states are a fixture)" % (len(data["fleet"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.fleet:
        fleet_view(data)
    elif args.route:
        route_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
