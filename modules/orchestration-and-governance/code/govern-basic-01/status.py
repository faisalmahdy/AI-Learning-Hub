#!/usr/bin/env python3
"""Reader-derived status: govern a fleet on the evidence, not the agent's word.

An orchestrator watching a fleet of agents needs to know which are healthy and
which are stuck -- that judgment gates every autonomy decision downstream. The
tempting source is the agent's own report: each emits a status field, "healthy"
or "done". But a stalled agent's last word was "healthy", and a failed one still
claims "done"; a self-reported status is exactly the thing that lies when it
matters. The fix is to DERIVE status from the observable event stream -- last
heartbeat age, whether a claimed completion actually emitted a result -- and never
read the emitter's own label. Emitter-claimed status is a wish; derived is a fact.

  --fleet       every agent: its self-reported status, derived status, and the truth
  --agent ID    one agent's event log and how the derived status reads it
  --measure     how many agents each method labels correctly against ground truth
  --check       derived status matches truth; emitter status is fooled by the liars

Mirrors faisalmahdy/agent-command-center: a reader-derived status engine, never an
emitter-claimed one. Stdlib only. No network. NOW and the logs are a fixture.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FLEET = HERE / "fleet.json"

STALE_SECS = 600      # no heartbeat for 10 minutes -> stalled, whatever it claims


def load():
    data = json.loads(FLEET.read_text(encoding="utf-8"))
    return data["now"], data["agents"]


# ---------------------------------------------------------- the two status sources

def emitter_status(agent):
    """THE TRAP: the agent's own last self-reported status. Trusts the label."""
    reports = [e for e in agent["events"] if "status" in e]
    return reports[-1]["status"] if reports else "unknown"


def derived_status(now, agent):
    """Read the evidence, ignore the label. A silent agent is stalled; a 'done'
    with no emitted result is incomplete; a last event that errored is failed."""
    events = agent["events"]
    beats = [e["ts"] for e in events if e["type"] == "heartbeat"]
    last_beat = max(beats) if beats else 0
    if now - last_beat > STALE_SECS:
        return "stalled"
    if events[-1]["type"] == "error":
        return "failed"
    claimed_done = any(e.get("status") == "done" for e in events)
    really_done = any(e["type"] == "task_complete" and e.get("result") == "ok" for e in events)
    if really_done:
        return "done"
    if claimed_done and not really_done:
        return "incomplete"
    return "healthy"


GOOD = {"healthy", "done"}      # the fine states; everything else is a broken agent


# ---------------------------------------------------------------- the measurement

def score(now, agents, status_fn):
    """How often a status method's healthy/not-healthy call matches the truth."""
    correct = 0
    for a in agents:
        called_ok = status_fn(a) in GOOD
        truly_ok = a["truth"] in GOOD
        correct += 1 if called_ok == truly_ok else 0
    return correct


# ------------------------------------------------------------------- printing

def fleet_view(now, agents):
    print("FLEET — self-reported vs derived vs the truth   (now = %d)" % now)
    print("-" * 66)
    print("  agent      emitter says   derived        truth       agree?")
    for a in agents:
        em = emitter_status(a)
        dv = derived_status(now, a)
        agree = "ok" if (dv == a["truth"] or (dv in GOOD) == (a["truth"] in GOOD)) else "--"
        flag = "" if em == a["truth"] or (em in GOOD) == (a["truth"] in GOOD) else "  <-- emitter lies"
        print("  %-9s  %-13s  %-13s  %-10s  %s%s" % (a["id"], em, dv, a["truth"], agree, flag))
    print("-" * 66)
    print("  the emitter's label is what the agent WISHES were true; derived reads")
    print("  the heartbeat and completion evidence and catches the ones that lie.")


def agent_view(now, agents, aid):
    a = next(x for x in agents if x["id"] == aid)
    print("AGENT %s — event log   (now = %d, stale after %ds)" % (aid, now, STALE_SECS))
    print("-" * 66)
    for e in a["events"]:
        extra = "  status=%s" % e["status"] if "status" in e else ""
        extra += "  result=%s" % e["result"] if "result" in e else ""
        print("  ts=%-6d  age=%-5d  %-14s%s" % (e["ts"], now - e["ts"], e["type"], extra))
    print("-" * 66)
    print("  emitter says: %-12s  derived: %-12s  truth: %s"
          % (emitter_status(a), derived_status(now, a), a["truth"]))


def measure(now, agents):
    n = len(agents)
    print("STATUS ACCURACY — healthy vs not, against ground truth")
    print("-" * 66)
    print("  emitter-claimed status   %d/%d" % (score(now, agents, emitter_status), n))
    print("  derived status           %d/%d" % (score(now, agents, lambda a: derived_status(now, a)), n))
    print("-" * 66)
    print("  every agent the emitter mislabels is one the orchestrator would keep")
    print("  running unattended (or kill by mistake). Governance reads evidence.")


def check(now, agents):
    print("SELF-TEST — derived status matches truth; emitter status is fooled")
    print("-" * 66)
    n = len(agents)
    em = score(now, agents, emitter_status)
    dv = score(now, agents, lambda a: derived_status(now, a))
    print("  emitter correct=%d/%d   derived correct=%d/%d" % (em, n, dv, n))

    derived_perfect = dv == n
    print("  derived status matches the truth for every agent = %s" % derived_perfect)
    emitter_fooled = em < n
    print("  emitter status is wrong for at least one agent = %s (%d < %d)" % (emitter_fooled, em, n))

    # the mechanism: at least one agent claims healthy/done while truly broken.
    liars = [a["id"] for a in agents
             if (emitter_status(a) in GOOD) and (a["truth"] not in GOOD)]
    has_liar = len(liars) > 0
    print("  agents that self-report OK while truly broken = %s (%s)" % (has_liar, ", ".join(liars)))

    # a stalled agent is caught by heartbeat age even though its label says healthy.
    stalled = [a for a in agents if a["truth"] == "stalled"]
    caught = all(derived_status(now, a) == "stalled" for a in stalled)
    print("  every stalled agent is derived as stalled from heartbeat age = %s" % caught)

    det = derived_status(now, agents[0]) == derived_status(now, agents[0])
    ok = derived_perfect and emitter_fooled and has_liar and caught and det
    print("-" * 66)
    print("SELF-TEST %s  derived_perfect=%s  emitter_fooled=%s  liars=%s  stalled_caught=%s"
          % ("PASS" if ok else "FAIL", derived_perfect, emitter_fooled, has_liar, caught))
    return ok


def main():
    p = argparse.ArgumentParser(description="Derive fleet status from evidence, not self-report.")
    p.add_argument("--fleet", action="store_true")
    p.add_argument("--agent", metavar="ID")
    p.add_argument("--measure", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    now, agents = load()
    print("agents=%d  now=%d  stale_after=%ds  file=%s  (logs are a fixture)"
          % (len(agents), now, STALE_SECS, FLEET.name))
    print("")

    if args.check:
        return 0 if check(now, agents) else 1
    if args.fleet:
        fleet_view(now, agents)
    elif args.agent:
        agent_view(now, agents, args.agent)
    elif args.measure:
        measure(now, agents)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
