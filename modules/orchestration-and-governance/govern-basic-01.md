---
id: govern-basic-01
title: Trust the evidence, not the agent's word — reader-derived fleet status
topic: orchestration-and-governance
level: basic
status: ready
time: 6-8h
summary: Read a six-agent fleet's status from each agent's own self-reported label and it looks all-green — every agent claims healthy or done — but three are stalled, incomplete, or failed, so the emitter-claimed view scores 3 of 6 against the truth. Derive status from the evidence instead — heartbeat age, whether a claimed completion emitted a result — and catch all six, because a self-reported status is exactly the signal that lies when it matters.
eli5: Ask each robot worker "are you okay?" and the broken ones still say yes. Instead, check the clock on their last heartbeat and whether they actually finished — the one that went quiet twenty minutes ago is stuck no matter what it claims.
---

## Why this module

This opens the orchestration-and-governance track, and it starts with the question every other module here depends on: which agents are actually working? An orchestrator running a fleet has to know who is healthy and who is stuck, because that judgment gates everything downstream — whether to hand an agent more autonomy, whether to kill it, whether to trust its output. Get the status wrong and every governance decision built on top is wrong too. The labs already hit this: the fleet dashboard in `agent-command-center` was built on one hard rule, and the scan records that its metrics still ship "UNCOMPUTABLE" precisely where that rule was not yet enforced.

The tempting way to know an agent's status is to ask it. Every agent emits a status field — "healthy", "done" — so just read the latest one. The problem is that a self-reported status is the one signal guaranteed to lie exactly when you need it: a stalled agent's last word before it went silent was "healthy", and a failed one still claims "done". The label is what the agent *wishes* were true, frozen at the moment it last spoke. The fix is to never read the label and instead *derive* status from the observable event stream — when did it last heartbeat, did its claimed completion actually produce a result — which cannot be wished into being.

You need nothing but Python 3 and the standard library. Everything runs offline against a six-agent fixture, `$0.00`, one sitting. The instinct to unlearn is that a component reporting its own health is a source of truth. In a fleet, self-report is a rumor; the evidence is the record.

Here is the same fleet judged both ways:

```
# modules/orchestration-and-governance/code/govern-basic-01/ — COMPLETE, run from that directory
$ python3 status.py --measure

STATUS ACCURACY — healthy vs not, against ground truth
------------------------------------------------------------------
  emitter-claimed status   3/6
  derived status           6/6
```

run: 2026-08-25 · deterministic; the logs are a fixture · n=6 agents, stale threshold 600s · `python3 status.py --measure`

Reading the agents' own labels gets half the fleet wrong. Reading the evidence gets all of it right. Every agent in that gap is one an orchestrator would keep running unattended while it is quietly broken — or kill while it is fine. This module is that gap and the few lines of derivation that close it.

## Concepts

Named here so you can find them again; each is built below.

- **Emitter-claimed status** — the status an agent reports about itself. Convenient, and the source of the bug.
- **Reader-derived status** — status computed by the observer from the event stream. The fix.
- **Heartbeat** — a periodic "still alive" event; its *age* is the signal, not its contents.
- **Event stream** — the log of what an agent did: claims, heartbeats, completions, errors.
- **Stale threshold** — the heartbeat age past which an agent is treated as stalled, whatever it claims.
- **The kill decision** — keep-running-unattended versus intervene; only trustworthy on derived status.

## Worked example

Source: faisalmahdy/agent-command-center — a read-only fleet monitor whose core thesis is a "reader-derived status engine, never an emitter-claimed status." This module builds the smallest honest version of that engine and shows what it catches.

Script and fixture: `modules/orchestration-and-governance/code/govern-basic-01/` — `status.py`, and `fleet.json`, six agents' event logs at a fixed clock time. Every command runs from there.

### The frame: a dashboard of self-marked attendance

Picture a status board where each worker marks their own attendance. Present, present, present — the board is all green, and it is worthless, because the one worker who left an hour ago is exactly the one who is not there to mark themselves absent. Their last mark still reads "present". That is emitter-claimed status: a label written by the thing being judged, frozen at the last moment it was capable of writing.

Reader-derived status throws the self-marks away and reads the room. Who has swiped a badge in the last ten minutes? Whose work actually landed? A worker who went silent is absent no matter what their last mark said. The whole module is that switch — from reading labels the agent controls to reading evidence it cannot fake after the fact.

### The two sources of status

The emitter-claimed version is trivial: find the agent's last self-reported status and return it.

```
# status.py:39-42 — COMPLETE (the trap: read the agent's own last label)
def emitter_status(agent):
    """THE TRAP: the agent's own last self-reported status. Trusts the label."""
    reports = [e for e in agent["events"] if "status" in e]
    return reports[-1]["status"] if reports else "unknown"
```

The derived version never looks at the label. It reads the heartbeat age, the last event, and whether a claimed completion actually emitted a result.

```
# status.py:45-61 — COMPLETE (read the evidence, ignore the label)
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
```

Each branch is a lie the label could tell. A stalled agent whose last heartbeat is older than the threshold is caught by the clock, not its claim. An agent that reported "done" but never emitted a `task_complete` with a result is `incomplete` — it announced a finish line it never crossed. The label is never consulted; only the record is.

### Look at the fleet: all-green, and three of them broken

```
# $ python3 status.py --fleet
#   agent      emitter says   derived        truth       agree?
#   nusa       healthy        healthy        healthy     ok
#   manik      healthy        stalled        stalled     ok  <-- emitter lies
#   patti      done           incomplete     incomplete  ok  <-- emitter lies
#   juanda     healthy        failed         failed      ok  <-- emitter lies
#   habibie    done           done           done        ok
#   malaya     healthy        healthy        healthy     ok
```

run: 2026-08-25 · fixture · `python3 status.py --fleet`

Read the emitter column alone and the fleet is perfect — every agent reports healthy or done. That is the dashboard a naive orchestrator shows, and it is lying about half the fleet. `manik` last heartbeated 1,100 seconds ago, well past the 600-second threshold: it is stalled, and its cheerful "healthy" is a fossil from before it froze. `patti` reported "done" but no result ever landed. `juanda`'s last event was an error, after a "healthy" heartbeat. The evidence disagrees with all three, and the evidence is right.

<svg viewBox="0 0 700 200" role="img" aria-label="Two views of the same six agents. The emitter view shows all six as green (healthy or done). The derived view shows nusa, habibie, malaya green but manik stalled, patti incomplete, and juanda failed, three of them red.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="20" fill="var(--s2)">emitter-claimed: all green (and lying)</text>
    <text x="380" y="20" fill="var(--s1)">reader-derived: the truth</text>
    <g>
      <rect x="20" y="34" width="150" height="20" rx="3" fill="var(--s1)"></rect><text x="26" y="49" fill="var(--panel)" font-size="8">nusa healthy</text>
      <rect x="20" y="58" width="150" height="20" rx="3" fill="var(--s1)"></rect><text x="26" y="73" fill="var(--panel)" font-size="8">manik healthy</text>
      <rect x="20" y="82" width="150" height="20" rx="3" fill="var(--s1)"></rect><text x="26" y="97" fill="var(--panel)" font-size="8">patti done</text>
      <rect x="20" y="106" width="150" height="20" rx="3" fill="var(--s1)"></rect><text x="26" y="121" fill="var(--panel)" font-size="8">juanda healthy</text>
      <rect x="20" y="130" width="150" height="20" rx="3" fill="var(--s1)"></rect><text x="26" y="145" fill="var(--panel)" font-size="8">habibie done</text>
      <rect x="20" y="154" width="150" height="20" rx="3" fill="var(--s1)"></rect><text x="26" y="169" fill="var(--panel)" font-size="8">malaya healthy</text>
    </g>
    <g>
      <rect x="380" y="34" width="150" height="20" rx="3" fill="var(--s1)"></rect><text x="386" y="49" fill="var(--panel)" font-size="8">nusa healthy</text>
      <rect x="380" y="58" width="150" height="20" rx="3" fill="var(--s2)"></rect><text x="386" y="73" fill="var(--panel)" font-size="8">manik STALLED</text>
      <rect x="380" y="82" width="150" height="20" rx="3" fill="var(--s2)"></rect><text x="386" y="97" fill="var(--panel)" font-size="8">patti INCOMPLETE</text>
      <rect x="380" y="106" width="150" height="20" rx="3" fill="var(--s2)"></rect><text x="386" y="121" fill="var(--panel)" font-size="8">juanda FAILED</text>
      <rect x="380" y="130" width="150" height="20" rx="3" fill="var(--s1)"></rect><text x="386" y="145" fill="var(--panel)" font-size="8">habibie done</text>
      <rect x="380" y="154" width="150" height="20" rx="3" fill="var(--s1)"></rect><text x="386" y="169" fill="var(--panel)" font-size="8">malaya healthy</text>
    </g>
  </g>
</svg>
^ The same fleet, two ways. Self-reports paint every agent green; derivation from heartbeat age and completion evidence turns three of them red. The dashboard you trust is the one on the right.

### Measure it

The governance question is binary — is this agent fine (healthy or done) or broken? — so score each method on that call against the truth.

```
# status.py:69-77 — COMPLETE (score the fine-vs-broken call against ground truth)
def score(now, agents, status_fn):
    """How often a status method's healthy/not-healthy call matches the truth."""
    correct = 0
    for a in agents:
        called_ok = status_fn(a) in GOOD
        truly_ok = a["truth"] in GOOD
        correct += 1 if called_ok == truly_ok else 0
    return correct
```

Emitter-claimed status scores 3 of 6; derived scores 6 of 6. The self-test confirms the mechanism — that the misses are agents claiming they are fine while broken, and that the stalled one is caught purely by heartbeat age:

```
# $ python3 status.py --check
#   emitter correct=3/6   derived correct=6/6
#   agents that self-report OK while truly broken = True (manik, patti, juanda)
#   every stalled agent is derived as stalled from heartbeat age = True
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · n=6 agents · `python3 status.py --check`

<svg viewBox="0 0 700 150" role="img" aria-label="manik's timeline: last heartbeat at age 1100 seconds, well past the 600-second stale threshold. Its self-reported label at that heartbeat was healthy, but the elapsed silence since means the deriver marks it stalled.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="20" fill="var(--muted)">manik: last heartbeat was 1100s ago; stale threshold is 600s</text>
    <line x1="40" y1="70" x2="660" y2="70" stroke="var(--grid)"></line>
    <circle cx="120" cy="70" r="4" fill="var(--muted)"></circle><text x="90" y="90" fill="var(--muted)">heartbeat</text><text x="90" y="102" fill="var(--muted)">"healthy"</text>
    <line x1="360" y1="55" x2="360" y2="85" stroke="var(--s1)" stroke-width="1.5" stroke-dasharray="3 2"></line><text x="300" y="48" fill="var(--s1)">600s threshold</text>
    <circle cx="660" cy="70" r="5" fill="var(--s2)"></circle><text x="600" y="90" fill="var(--s2)">now</text>
    <path d="M 120 118 L 660 118" stroke="var(--s2)" stroke-width="1"></path>
    <text x="300" y="134" fill="var(--s2)">1100s of silence -> stalled</text>
    <rect x="360" y="60" width="300" height="20" fill="var(--s2)" opacity="0.15"></rect>
  </g>
</svg>
^ manik's last word was "healthy" — 1,100 seconds ago. Everything right of the 600-second line is silence the label cannot explain, so the deriver reads the clock and calls it stalled. The evidence is the elapsed time, not the frozen claim.

**A component's report on its own health is not evidence — it is a claim, frozen at the last moment it could speak; govern on what you can observe, never on what the agent says about itself.**

## Build

The pipeline in one paragraph: collect each agent's event stream — claims, heartbeats, completions, errors, each timestamped; derive status from that stream, using heartbeat age against a stale threshold and completion evidence against claimed completions; never read the agent's self-reported status label for a governance decision; and validate the deriver against a labelled ground truth so you know its false-healthy rate before you let it gate autonomy.

We opened on the two accuracies. The line that matters:

```
# modules/orchestration-and-governance/code/govern-basic-01/ — COMPLETE, run from that directory
$ python3 status.py --measure
  derived status           6/6
```

Now point it at your own fleet. The dial is `STALE_SECS`: set it from your agents' real heartbeat interval — too tight and a slow-but-alive agent is flagged stalled, too loose and a dead one looks alive for too long. Your number to beat is the **false-healthy count**: agents your status engine calls fine that are actually broken, because those are the ones that hurt — a false-broken wastes an intervention, a false-healthy lets a dead agent keep holding a task. Build a fixture where an agent self-reports "done" without emitting a result and confirm your deriver calls it incomplete while the emitter calls it done. Bring back both accuracies and the false-healthy count. Good luck.

## Definition of done

- [ ] Agents emit a timestamped event stream: claims, heartbeats, completions, errors
- [ ] A deriver that computes status from heartbeat age and completion evidence, never the self-reported label
- [ ] A stale threshold that flags a silent agent regardless of its last claim
- [ ] Your own `fleet.json` with a ground-truth label per agent, including at least one that self-reports fine while broken
- [ ] Emitter-claimed status kept alongside, so the gap is measured, not asserted
- [ ] `python3 status.py --check` printing SELF-TEST PASS: derived matches truth, emitter is fooled, stalled caught by age
- [ ] The two accuracies and the false-healthy count recorded, and the stale threshold you chose
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. An agent's dashboard shows "healthy" but it has done nothing for twenty minutes. Explain why its self-report says healthy and what signal a deriver uses instead.
2. Give the difference between emitter-claimed and reader-derived status in one sentence, and why the difference only matters for the broken agents.
3. An agent reported "done". What one piece of evidence decides whether the deriver agrees or calls it incomplete?
4. Between a false-healthy and a false-broken status call, which is the dangerous one for an unattended fleet, and why?
5. Your own run produced two accuracies. What were they, and which agents did the emitter view get wrong?

## External resources

- faisalmahdy/agent-command-center — the fleet status engine — my summary: a read-only monitor built on "reader-derived status, never emitter-claimed"; read it for the wire protocol that carries the events this module derives from, and note its metrics shipped UNCOMPUTABLE exactly where derivation was not yet wired — the gap this module closes.
- Google SRE, *Monitoring Distributed Systems* (SRE Book, ch. 6) — https://sre.google/sre-book/monitoring-distributed-systems/ — my summary: the discipline of black-box (observed) versus white-box (self-reported) monitoring; read it for why production systems trust probes over a service's own health endpoint, which is this module's lesson at datacenter scale.
- Nygard, *Release It!* — stability patterns (heartbeats, timeouts, circuit breakers) — https://pragprog.com/titles/mnee2/release-it-second-edition/ — my summary: the failure patterns a heartbeat-and-timeout deriver defends against; read it for why a silent dependency must be treated as failed, not pending, and how the stale threshold here is a timeout in disguise.
