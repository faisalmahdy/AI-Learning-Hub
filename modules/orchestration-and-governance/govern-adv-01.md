---
id: govern-adv-01
title: The resilient orchestrator — compose the contract, the DAG, retries, and the saga into commit-or-unwind
topic: orchestration-and-governance
level: advanced
status: ready
time: 12-16h
summary: An orchestrator that runs a multi-step workflow with real side effects has to get four separate guarantees right at once — the fan-out assignment must be a true partition (disjoint and complete), the steps must run in dependency order not authoring order, a step that fails every retry must be dead-lettered rather than allowed to starve the run, and a failure past the point of no return must unwind the steps that already committed. Composing the orchestration track's partition contract, task DAG, retry-plus-dead-letter queue, and saga, the resilient orchestrator runs a five-step booking, retries a transient hold, dead-letters the poison ticket-issue after 3 attempts, and compensates the committed prefix in reverse to a clean zero ledger — 7 attempts, nothing leaked. The naive orchestrator runs the plan in file order (2 stale-input reads), commits a seat, a card charge, and a customer notification, then stops dead at the poison step and leaves all three real effects in the world with no record. The property is commit-every-step-or-unwind-to-zero, and it is the conjunction of all four guarantees — drop any one and the run ends in a partial, corrupt, silent middle.
eli5: Booking a trip online sets off a chain of real actions — hold a seat, charge your card, issue a ticket, email you. If the ticket machine is broken, a careless system charges your card and then just stops, leaving you paying for a ticket you never got. A careful system does the steps in the right order, tries the flaky ones a few times, gives up cleanly on the truly broken one, and then walks backwards undoing everything it already did — refunds the card, releases the seat — so you end up exactly where you started, as if you never pressed the button.
---

## Why this module

The orchestration track built each guarantee a real executor needs, one module at a time, and each was demonstrated by a failure it prevents. The partition contract (`govern-inter-03`) rejected a fan-out whose file assignment overlapped and gapped, before any write was lost. The task DAG (`govern-inter-04`) ran producers before consumers, because authoring order is not dependency order and a subagent that runs early reads an input that does not exist yet. The retry bound plus dead-letter queue (`govern-inter-06`) contained a poison task instead of letting it burn the whole budget and starve the tasks behind it. The saga (`govern-inter-05`) undid the completed prefix in reverse when a step past the point of no return failed, because a workflow with real side effects cannot be rolled back by a transaction. This module composes all four into a single orchestrator and measures the property that no one of them gives alone: run the plan, and it either commits every step or unwinds to exactly the state it started in — never a partial, leaked, corrupt middle.

The composition matters because the four guarantees are not a menu you pick from; they are a conjunction, and a real workflow trips all four at once. A booking holds a seat, charges a card, issues a ticket, and emails the customer. Those steps depend on each other, they each write a distinct resource, one of them is transiently flaky, and one of them fails hard when the downstream ticketing service is down. An orchestrator that gets three of the four right still ends corrupt: order the steps right but skip the saga and you charge a card for a ticket you never issue; run the saga but ignore the DAG and you compensate steps that ran on stale inputs; check the partition but retry the poison forever and the run never terminates. The property "commit-or-unwind" is only true when every guarantee holds simultaneously.

The four guarantees stack, each ruling out one failure mode, and the run is safe only when every layer holds:

<svg viewBox="0 0 700 200" role="img" aria-label="Four stacked guarantee layers feeding one property. Layer 1 partition contract rules out clobbered writes. Layer 2 dependency order rules out stale reads. Layer 3 retries plus dead-letter rules out a starved queue. Layer 4 saga rules out a leaked side effect. All four ANDed produce commit-or-unwind. A note says dropping any layer drops to the failure it prevents.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">four guarantees, each ruling out one failure → commit-or-unwind</text>
    <rect x="20" y="28" width="300" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="30" y="47" fill="var(--acc-ink)" font-size="8">1. partition contract</text><text x="330" y="47" fill="var(--s2)" font-size="8">✗ else: clobbered write</text>
    <rect x="20" y="62" width="300" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="30" y="81" fill="var(--acc-ink)" font-size="8">2. dependency (topo) order</text><text x="330" y="81" fill="var(--s2)" font-size="8">✗ else: stale read</text>
    <rect x="20" y="96" width="300" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="30" y="115" fill="var(--acc-ink)" font-size="8">3. bounded retry + dead-letter</text><text x="330" y="115" fill="var(--s2)" font-size="8">✗ else: starved queue</text>
    <rect x="20" y="130" width="300" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="30" y="149" fill="var(--acc-ink)" font-size="8">4. saga (reverse compensate)</text><text x="330" y="149" fill="var(--s2)" font-size="8">✗ else: leaked side effect</text>
    <line x1="560" y1="43" x2="600" y2="94" stroke="var(--line)"></line><line x1="560" y1="77" x2="600" y2="94" stroke="var(--line)"></line><line x1="560" y1="111" x2="600" y2="94" stroke="var(--line)"></line><line x1="560" y1="145" x2="600" y2="94" stroke="var(--line)"></line>
    <rect x="600" y="80" width="80" height="30" fill="var(--s1)"></rect><text x="640" y="99" text-anchor="middle" fill="var(--panel)" font-size="8">AND</text>
    <text x="360" y="184" fill="var(--muted)" font-size="8">the property holds only when all four layers hold; drop one and the run ends in that layer's failure</text>
  </g>
</svg>
^ Each guarantee rules out exactly one corruption — a clobbered write, a stale read, a starved queue, a leaked effect — and commit-or-unwind is their conjunction. This module is the AND of all four on one plan.

You need the whole orchestration track: `govern-inter-03` (partition), `govern-inter-04` (DAG), `govern-inter-05` (saga), and `govern-inter-06` (retries and DLQ). Everything runs offline against a plan fixture — five steps with dependencies, partition keys, forward effects, a poison flag, and transient-failure counts — stdlib Python 3, `$0.00`. The instinct to unlearn is that resilience is a feature you add. It is a conjunction of guarantees you compose, and the moment you drop one, the orchestrator fails in exactly the mode that guarantee existed to prevent — and worse, it fails silently, because a corrupt ledger does not raise.

Here is the plan, with the partition check and both orderings resolved:

```
# modules/orchestration-and-governance/code/govern-adv-01/ — COMPLETE, run from that directory
$ python3 orchestrator.py --plan

PLAN — 5 steps; partition target ['seat', 'card', 'email', 'ticket', 'hold_slot']
----------------------------------------------------------------------
  id          deps            key    forward  poison  fails_before
  reserve     -               seat        +1  False   0
  charge      reserve         card        +1  False   0
  notify      issue           email       +1  False   0
  issue       hold            ticket      +1  True    0
  hold        charge          hold_slot   +1  False   1
----------------------------------------------------------------------
  partition disjoint+complete = True
  file order:  ['reserve', 'charge', 'notify', 'issue', 'hold']  (stale reads: 2)
  topo order:  ['reserve', 'charge', 'hold', 'issue', 'notify']  (stale reads: 0)
```

run: 2026-08-27 · deterministic; plan and failure pattern are a fixture · 5 steps · `python3 orchestrator.py --plan`

Read the two order lines: the plan as authored in the file has 2 stale-input reads (notify is listed before issue, issue before hold), while the dependency-sorted order has zero. That gap is the DAG guarantee in one number, and it is only the first of the four. This module is what a correct orchestrator does with this exact plan when `issue` — the ticketing step — is down, and how a naive one corrupts the booking.

## Concepts

Named here so you can find them again; each is built below, and each is the core of a prior module.

- **Partition contract** — the steps' resource keys are disjoint and cover the target exactly; no key written twice, none missed.
- **Topological order** — run each step only after its dependencies are done; a stale read is a consumer running before its producer.
- **Bounded retry + dead-letter** — retry a transient failure up to a bound, then move a poison step to a dead-letter queue and keep going.
- **Saga compensation** — on a failure past the point of no return, undo the committed steps in reverse; compensation is the inverse of the forward effect.
- **Commit-or-unwind** — the whole-run property: every step commits, or the ledger returns to exactly its starting state.
- **The leak** — a committed real side effect (a seat held, a card charged) left in the world with no unwind and no record.

## Worked example

Source: the composition of the orchestration track's own guarantees into one executor — the kind of workflow engine that runs a booking, a checkout, or a multi-tool agent plan. The ledger here stands in for the real side effects (seats, charges, tickets) so the commit-or-unwind property is exact and checkable.

Script and fixture: `modules/orchestration-and-governance/code/govern-adv-01/` — `orchestrator.py`, and `plan.json`, one five-step booking workflow. Every command runs from there.

### Guarantee one: the partition contract

Before running anything, the orchestrator checks that the steps' resource keys form a true partition of the target — disjoint (no key written by two steps) and complete (every target key written). This is `govern-inter-03` verbatim: the damage of an overlap or a gap is in the assignment, not the execution, so it must be caught before any side effect lands.

```
# orchestrator.py:44-56 — COMPLETE (the partition contract: disjoint and complete)
def check_partition(steps, target):
    """govern-inter-03: the steps' partition keys must be disjoint and cover the target exactly."""
    keys = [s["key"] for s in steps]
    seen, overlap = set(), set()
    for k in keys:
        if k in seen:
            overlap.add(k)
        seen.add(k)
    missing = set(target) - seen
    extra = seen - set(target)
    ok = not overlap and not missing and not extra
    return ok, {"overlap": sorted(overlap), "missing": sorted(missing), "extra": sorted(extra)}
```

On this plan the five keys — seat, card, email, ticket, hold_slot — are exactly the target, so the contract passes. Were two steps to write `card`, the overlap set would name it and the orchestrator would reject the plan rather than run a booking where one charge silently clobbers another. The contract is a precondition, not a runtime check: it holds before the first step, or the run does not start.

### Guarantee two: the task DAG

The steps are then sorted into dependency order by Kahn's algorithm — `govern-inter-04`. A dependency promises the producer finishes before the consumer starts; running the plan in the order it happens to sit in the file breaks that promise.

```
# orchestrator.py:60-80 — COMPLETE (Kahn's topological sort; empty order signals a cycle)
def topo_order(steps):
    """govern-inter-04: Kahn's algorithm. Returns (order, cycle) -- order empty if a cycle exists."""
    ids = [s["id"] for s in steps]
    dep = {s["id"]: list(s["deps"]) for s in steps}
    indeg = {i: 0 for i in ids}
    for i in ids:
        for d in dep[i]:
            indeg[i] += 1
    ready = sorted(i for i in ids if indeg[i] == 0)
    order = []
    while ready:
        n = ready.pop(0)
        order.append(n)
        for i in ids:
            if n in dep[i]:
                indeg[i] -= 1
                if indeg[i] == 0:
                    ready.append(i)
        ready.sort()
    cycle = [i for i in ids if i not in order]
    return (order if not cycle else []), cycle
```

The stale-read count is the DAG guarantee made measurable: how many steps, in a given order, run before one of their dependencies.

```
# orchestrator.py:83-94 — COMPLETE (a stale read is a consumer positioned before its producer)
def violations_in_order(order, steps):
    """How many consumers run before a producer in this exact order (a stale-input read)."""
    pos = {sid: i for i, sid in enumerate(order)}
    dep = {s["id"]: s["deps"] for s in steps}
    v = 0
    for sid in order:
        for d in dep[sid]:
            if pos.get(d, 1 << 30) > pos[sid]:
                v += 1
    return v
```

The file order scores 2, the topological order scores 0 — that is the `--plan` output above. Kahn's sort carries a second duty from the same module: a plan whose dependencies form a cycle has no valid order, and `topo_order` returns an empty order with the stranded steps named, so the orchestrator reports it uncompletable instead of deadlocking.

<svg viewBox="0 0 700 210" role="img" aria-label="The five booking steps as a dependency DAG: reserve to charge to hold to issue to notify, a chain. Below it two orderings. File order reserve, charge, notify, issue, hold has two backward edges (notify before issue, issue before hold) marked as stale reads. Topo order reserve, charge, hold, issue, notify has all edges pointing forward, zero stale reads.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the dependency DAG: reserve → charge → hold → issue → notify</text>
    <g>
      <rect x="20" y="30" width="72" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="56" y="46" text-anchor="middle" fill="var(--acc-ink)" font-size="8">reserve</text>
      <rect x="120" y="30" width="72" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="156" y="46" text-anchor="middle" fill="var(--acc-ink)" font-size="8">charge</text>
      <rect x="220" y="30" width="72" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="256" y="46" text-anchor="middle" fill="var(--acc-ink)" font-size="8">hold</text>
      <rect x="320" y="30" width="72" height="24" fill="var(--panel)" stroke="var(--s2)"></rect><text x="356" y="46" text-anchor="middle" fill="var(--s2)" font-size="8">issue ✗</text>
      <rect x="420" y="30" width="72" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="456" y="46" text-anchor="middle" fill="var(--acc-ink)" font-size="8">notify</text>
      <line x1="92" y1="42" x2="120" y2="42" stroke="var(--ink)"></line>
      <line x1="192" y1="42" x2="220" y2="42" stroke="var(--ink)"></line>
      <line x1="292" y1="42" x2="320" y2="42" stroke="var(--ink)"></line>
      <line x1="392" y1="42" x2="420" y2="42" stroke="var(--ink)"></line>
    </g>
    <text x="20" y="96" fill="var(--s2)">file order</text>
    <text x="20" y="110" fill="var(--muted)" font-size="8">reserve · charge · notify · issue · hold</text>
    <text x="20" y="126" fill="var(--s2)" font-size="8">2 stale reads: notify before issue, issue before hold</text>
    <line x1="200" y1="106" x2="300" y2="106" stroke="var(--s2)"></line><text x="250" y="102" text-anchor="middle" fill="var(--s2)" font-size="8">← backward</text>
    <text x="20" y="164" fill="var(--s1)">topo order</text>
    <text x="20" y="178" fill="var(--muted)" font-size="8">reserve · charge · hold · issue · notify</text>
    <text x="20" y="194" fill="var(--s1)" font-size="8">0 stale reads: every edge points forward</text>
  </g>
</svg>
^ The five steps form a dependency chain. The authored file order sends notify and issue ahead of their producers — two backward edges, two stale reads — while Kahn's topological sort lays every step after its dependencies for zero. The orchestrator runs the topo order; the naive one runs the file.

### Guarantees three and four: retries, dead-letter, and the saga

The execution loop composes the last two guarantees. Each step gets bounded retries; a transient step (here `hold`, which fails once) succeeds on a later attempt, while the poison step (`issue`, the down ticketing service) exhausts its retries and is dead-lettered. Dead-lettering `issue` is a failure past the point of no return — a seat is held and a card is charged — so it triggers the saga: compensate the committed prefix in reverse.

```
# orchestrator.py:109-133 — COMPLETE (bounded retries + DLQ, then saga-unwind the committed prefix)
    for sid in order:
        s = steps[sid]
        ok = False
        for _ in range(max_retries):
            attempts += 1
            # transient steps fail (fails_before) times then succeed; poison never succeeds
            fails_needed = 999 if s["poison"] else s["fails_before"]
            if (attempts_for(trace, sid)) >= fails_needed:
                ok = True
                break
            trace.append((sid, "fail"))
        if ok:
            ledger[s["key"]] += s["forward"]
            committed.append(sid)
            trace.append((sid, "commit"))
        else:
            dlq.append(sid)
            trace.append((sid, "dead-letter"))
            # saga: compensate the committed prefix in reverse -- past the point of no return
            for csid in reversed(committed):
                cs = steps[csid]
                ledger[cs["key"]] -= cs["forward"]     # compensate == inverse of forward
                trace.append((csid, "compensate"))
            committed = []
            break
```

Two things in this loop are the whole composition. The `dlq.append(sid)` is `govern-inter-06`: the poison step is contained, not retried forever, so the run terminates. The `for csid in reversed(committed)` is `govern-inter-05`: only the completed prefix is compensated, and in reverse — the failed step needs no compensation because its effect never landed, and a step compensated out of order could undo a later effect before an earlier one that depends on it. Run it:

```
# $ python3 orchestrator.py --resilient
#   reserve     commit
#   charge      commit
#   hold        fail
#   hold        commit
#   issue       fail
#   issue       fail
#   issue       fail
#   issue       dead-letter
#   hold        compensate
#   charge      compensate
#   reserve     compensate
#   attempts: 7   dead-lettered: ['issue']   still committed: []
#   final ledger: {'seat': 0, 'card': 0, 'email': 0, 'ticket': 0, 'hold_slot': 0}
```

run: 2026-08-27 · deterministic · `python3 orchestrator.py --resilient`

Read the trace top to bottom. reserve and charge commit. hold fails once — the transient flake — then the retry commits it; that one retry is the DLQ module's other half, the failure that resilience is supposed to absorb rather than escalate. Then issue fails three times (the poison, `max_retries = 3`), is dead-lettered, and the saga runs: hold, charge, reserve compensated in reverse. The final ledger is all zeros. Seven attempts, one dead letter, nothing left in the world.

<svg viewBox="0 0 700 220" role="img" aria-label="A timeline of the resilient run. reserve commits, charge commits, hold fails once then commits (retry), issue fails three times then is dead-lettered, then compensations run in reverse: hold, charge, reserve. A ledger track below shows seat and card rising to 1 as they commit and hold_slot rising, then all three falling back to 0 during compensation, ending flat at zero.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">resilient run: commit forward, then saga-unwind in reverse to zero</text>
    <line x1="30" y1="40" x2="30" y2="150" stroke="var(--line)"></line>
    <line x1="30" y1="150" x2="680" y2="150" stroke="var(--line)"></line>
    <rect x="40" y="120" width="44" height="30" fill="var(--s1)"></rect><text x="62" y="139" text-anchor="middle" fill="var(--panel)" font-size="7">reserve✓</text>
    <rect x="90" y="120" width="44" height="30" fill="var(--s1)"></rect><text x="112" y="139" text-anchor="middle" fill="var(--panel)" font-size="7">charge✓</text>
    <rect x="140" y="120" width="20" height="30" fill="var(--panel)" stroke="var(--s2)"></rect><text x="150" y="139" text-anchor="middle" fill="var(--s2)" font-size="7">✗</text>
    <rect x="164" y="120" width="44" height="30" fill="var(--s1)"></rect><text x="186" y="139" text-anchor="middle" fill="var(--panel)" font-size="7">hold✓</text>
    <rect x="214" y="120" width="20" height="30" fill="var(--panel)" stroke="var(--s2)"></rect><rect x="238" y="120" width="20" height="30" fill="var(--panel)" stroke="var(--s2)"></rect><rect x="262" y="120" width="20" height="30" fill="var(--panel)" stroke="var(--s2)"></rect><text x="238" y="112" text-anchor="middle" fill="var(--s2)" font-size="7">issue ✗✗✗</text>
    <rect x="286" y="120" width="60" height="30" fill="var(--s2)"></rect><text x="316" y="139" text-anchor="middle" fill="var(--panel)" font-size="7">DEAD-LETTER</text>
    <rect x="360" y="120" width="44" height="30" fill="var(--muted)"></rect><text x="382" y="139" text-anchor="middle" fill="var(--panel)" font-size="7">↩hold</text>
    <rect x="410" y="120" width="44" height="30" fill="var(--muted)"></rect><text x="432" y="139" text-anchor="middle" fill="var(--panel)" font-size="7">↩charge</text>
    <rect x="460" y="120" width="52" height="30" fill="var(--muted)"></rect><text x="486" y="139" text-anchor="middle" fill="var(--panel)" font-size="7">↩reserve</text>
    <text x="40" y="176" fill="var(--muted)" font-size="8">ledger climbs to 3 committed effects, saga walks it back down to 0 — clean unwind</text>
    <text x="360" y="196" fill="var(--s1)" font-size="8">final ledger: all zeros · dead-lettered: [issue] · 7 attempts</text>
  </g>
</svg>
^ The forward run commits reserve, charge, and (after one retry) hold; issue exhausts three attempts and is dead-lettered; the saga then compensates the three committed steps in reverse, landing the ledger back at zero. Commit-or-unwind, resolved to unwind.

### The naive orchestrator: four guarantees dropped

The naive orchestrator runs the plan in file order, trusts the assignment, has no retry or dead-letter, and on a failure simply stops.

```
# orchestrator.py:144-160 — COMPLETE (file order, no contract/DLQ/saga; stop and leak)
def run_naive(data):
    """File order, no partition check, no retry/DLQ, no saga: stop on the first failure and leak."""
    steps = data["steps"]                       # as authored, not topo-sorted
    ledger = {s["key"]: 0 for s in steps}
    committed = []
    stale_reads = violations_in_order([s["id"] for s in steps], steps)
    stopped_at = None
    for s in steps:
        if s["poison"]:                          # no retry, no DLQ -> the run just stops here
            stopped_at = s["id"]
            break
        ledger[s["key"]] += s["forward"]         # commit real side effects, one attempt
        committed.append(s["id"])
    # no saga: whatever committed stays committed
    return {"ledger": ledger, "committed": committed, "stopped_at": stopped_at,
            "stale_reads": stale_reads}
```

A leak is simply any ledger entry that did not return to zero — a real effect still standing in the world after the run ended:

```
# orchestrator.py:162-163 — COMPLETE (a leak is any nonzero ledger entry after the run)
def leaked(ledger):
    return {k: v for k, v in ledger.items() if v != 0}
```

For the resilient run this is empty; for the naive run it names every side effect left uncompensated. Run it, and read the leak:

```
# $ python3 orchestrator.py --naive
#   ran in file order, stale-input reads: 2
#   committed (kept, never unwound): ['reserve', 'charge', 'notify']
#   stopped at poison step: issue
#   final ledger: {'seat': 1, 'card': 1, 'email': 1, 'ticket': 0, 'hold_slot': 0}
#   LEAKED side effects left in the world: {'seat': 1, 'card': 1, 'email': 1}
```

run: 2026-08-27 · deterministic · `python3 orchestrator.py --naive`

Three corruptions in one run. It read stale inputs twice — it committed `notify` (the customer email) before `issue` ever ran, because file order put notify first, so the customer was told about a ticket that does not exist. It hit the poison `issue`, and with no retry or dead-letter the run just stopped. And with no saga, the seat it held, the card it charged, and the email it sent are all left committed: `{seat: 1, card: 1, email: 1}`. The customer is charged for a ticket they never got, notified that they have it, and there is no record of why. Same plan, same failing step — the resilient orchestrator ended at all zeros with `issue` in a dead-letter queue; the naive one ended leaked and silent.

<svg viewBox="0 0 700 180" role="img" aria-label="Two final ledgers side by side after the same poison failure. Resilient: seat 0, card 0, email 0, ticket 0, hold_slot 0 — all zero, labeled clean unwind. Naive: seat 1, card 1, email 1, ticket 0, hold_slot 0 — three bars at 1 labeled leaked, one for a held seat, one for a charged card, one for a sent email about a nonexistent ticket.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">final ledger after the same poison failure — commit-or-unwind vs leak</text>
    <text x="20" y="42" fill="var(--s1)">resilient</text>
    <rect x="120" y="32" width="16" height="14" fill="var(--panel)" stroke="var(--line)"></rect><text x="128" y="60" text-anchor="middle" fill="var(--muted)" font-size="7">seat 0</text>
    <rect x="180" y="32" width="16" height="14" fill="var(--panel)" stroke="var(--line)"></rect><text x="188" y="60" text-anchor="middle" fill="var(--muted)" font-size="7">card 0</text>
    <rect x="240" y="32" width="16" height="14" fill="var(--panel)" stroke="var(--line)"></rect><text x="248" y="60" text-anchor="middle" fill="var(--muted)" font-size="7">email 0</text>
    <rect x="300" y="32" width="16" height="14" fill="var(--panel)" stroke="var(--line)"></rect><text x="316" y="60" text-anchor="middle" fill="var(--muted)" font-size="7">ticket 0</text>
    <rect x="380" y="32" width="16" height="14" fill="var(--panel)" stroke="var(--line)"></rect><text x="396" y="60" text-anchor="middle" fill="var(--muted)" font-size="7">hold 0</text>
    <text x="460" y="43" fill="var(--s1)" font-size="8">all zero — clean unwind</text>
    <text x="20" y="112" fill="var(--s2)">naive</text>
    <rect x="120" y="88" width="16" height="28" fill="var(--s2)"></rect><text x="128" y="130" text-anchor="middle" fill="var(--s2)" font-size="7">seat 1</text>
    <rect x="180" y="88" width="16" height="28" fill="var(--s2)"></rect><text x="188" y="130" text-anchor="middle" fill="var(--s2)" font-size="7">card 1</text>
    <rect x="240" y="88" width="16" height="28" fill="var(--s2)"></rect><text x="248" y="130" text-anchor="middle" fill="var(--s2)" font-size="7">email 1</text>
    <rect x="300" y="102" width="16" height="14" fill="var(--panel)" stroke="var(--line)"></rect><text x="316" y="130" text-anchor="middle" fill="var(--muted)" font-size="7">ticket 0</text>
    <rect x="380" y="102" width="16" height="14" fill="var(--panel)" stroke="var(--line)"></rect><text x="396" y="130" text-anchor="middle" fill="var(--muted)" font-size="7">hold 0</text>
    <text x="460" y="103" fill="var(--s2)" font-size="8">3 leaked: held, charged, notified</text>
    <text x="120" y="160" fill="var(--muted)" font-size="8">same plan, same failing step — the only difference is whether the four guarantees held</text>
  </g>
</svg>
^ The two orchestrators end the same failed booking in opposite states: the resilient ledger is flat at zero, the naive one carries a held seat, a charged card, and a customer notified about a ticket that was never issued. The corruption is not in the failing step — it is in the three guarantees the naive path dropped.

**Commit-or-unwind is the conjunction of four guarantees — a true partition, dependency order, bounded retries with a dead-letter queue, and a saga that reverses the committed prefix — so an orchestrator that drops any one of them ends a workflow in a partial, corrupt, silent middle: a stale read, a starved queue, or a charged card with no ticket and no record.**

### The self-test

The `--check` mode asserts the whole composition: the partition is valid, the topological order beats file order on stale reads, the resilient path dead-letters exactly the poison step and unwinds to zero, and the naive path leaks real side effects.

```
# $ python3 orchestrator.py --check
#   the plan's partition is disjoint and complete = True
#   topo order has zero stale reads while file order has some = True (file=2, topo=0)
#   resilient dead-lettered exactly the poison step = True (['issue'])
#   resilient ledger fully unwound to zero (no leak) = True ({'seat': 0, ...})
#   naive left real side effects leaked (a seat held, a card charged) = True ({'seat': 1, 'card': 1, 'email': 1})
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 orchestrator.py --check`

Each line guards one guarantee. `partition` is the contract, checked before any run. The `file=2, topo=0` line is the DAG: the same plan, two orders, only one safe. `poison_dlq` is the retry-and-dead-letter half — exactly one step contained, and it is the poison, so the queue never starves and the run terminates. `resilient_clean` is the saga: the ledger is back to zero and nothing is still committed. And `naive_leaks` proves the corruption is real, not hypothetical — drop the four guarantees and this exact booking leaves a charged card behind. The combined gate is an AND of all five: the orchestrator is correct only when every guarantee holds at once.

```
# orchestrator.py:229-237 — COMPLETE (the saga anchor and the combined gate: an AND of all five)
    resilient_clean = not leaked(r["ledger"]) and not r["committed"]
    print("  resilient ledger fully unwound to zero (no leak) = %s (%s)"
          % (resilient_clean, r["ledger"]))

    naive_leaks = bool(leaked(n["ledger"]))
    print("  naive left real side effects leaked (a seat held, a card charged) = %s (%s)"
          % (naive_leaks, leaked(n["ledger"])))

    ok_all = ok and topo_clean and file_bad and poison_dlq and resilient_clean and naive_leaks
```

`resilient_clean` is two conditions, not one: the ledger has no leak *and* nothing is still marked committed — a saga that compensated the effects but forgot to clear its committed list would pass the first and fail the second. And `ok_all` is the composition in a single line: the orchestrator is correct only when the partition, the ordering, the containment, the unwind, and the demonstrated naive leak all hold together, which is the same conjunction discipline the orchestrator enforces on the workflow itself.

### The running tally

| step | committed by resilient? | committed by naive? | resilient final | naive final | note |
|---|---|---|---|---|---|
| reserve | yes → compensated | yes (kept) | 0 | 1 leaked | seat held, naive never releases |
| charge | yes → compensated | yes (kept) | 0 | 1 leaked | card charged, naive never refunds |
| hold | retried, yes → compensated | not reached | 0 | 0 | transient flake, absorbed by retry |
| issue | dead-lettered | stopped here | 0 | 0 | the poison; contained vs fatal |
| notify | never runs | yes (stale) | 0 | 1 leaked | naive emails a ticket that doesn't exist |

Read the two final columns. The resilient orchestrator's is all zeros: every committed effect was compensated, the poison was contained, and the steps that should not have run (notify) never did. The naive orchestrator's has three leaks, and each is a different guarantee it dropped — reserve and charge leaked because there was no saga, notify leaked because there was no dependency order, and the run stopped rather than contained because there was no dead-letter. This is why an orchestrator cannot be built one guarantee at a time and shipped early: the guarantees are orthogonal, a real workflow trips all of them, and commit-or-unwind is the single point where all four hold.

### What we did not settle

This composes four guarantees into one in-process run; a production orchestrator carries more. Compensation here is a perfect inverse of the forward effect, but real compensations are themselves fallible — a refund can fail — so the saga needs its own retries and a compensation dead-letter for the effects it cannot reverse, which is where a human is paged. The run is single-process and synchronous; a distributed orchestrator persists the trace to a durable log so it can resume after its own crash mid-saga, and makes each step idempotent (`ship-inter-02`) so a retry after a lost acknowledgement does not double-charge. The dead-lettered `issue` needs a policy — alert, park for manual retry, or fail the booking — not just a queue entry. And the whole thing runs under a deadline budget (`ship-inter-05`), so a workflow that will miss its deadline unwinds early rather than holding resources to the end. The invariant survives all of it: every step commits, or the world returns to exactly where it started.

## Build

The build in one paragraph: validate that the plan's step assignment is a true partition before running anything; sort the steps into dependency order so no consumer reads a producer's output before it exists; execute each step with bounded retries, dead-lettering a step that exhausts them so the run terminates instead of starving; and when a dead-letter lands past the point of no return, run the saga — compensate the committed steps in reverse, each compensation the inverse of its forward effect — so the ledger returns to exactly zero. Persist the trace so the run can resume after a crash, make each step idempotent so retries are safe, give compensations their own retry and dead-letter, and run the whole thing under a deadline.

We opened on the plan. The number that proves the composition works is the resilient ledger against the naive one:

```
# modules/orchestration-and-governance/code/govern-adv-01/ — COMPLETE, run from that directory
$ python3 orchestrator.py --check
  resilient ledger fully unwound to zero (no leak) = True ({'seat': 0, 'card': 0, 'email': 0, 'ticket': 0, 'hold_slot': 0})
  naive left real side effects leaked (a seat held, a card charged) = True ({'seat': 1, 'card': 1, 'email': 1})
```

Now build your own. Take a real multi-step workflow — a checkout, a provisioning flow, a multi-tool agent plan — with dependencies and real side effects, and compose the four guarantees into one orchestrator. Your number to beat is not throughput; it is **the final state after a mid-plan failure: every committed effect compensated to zero, against a naive baseline that leaks**. Inject a poison step and confirm your orchestrator dead-letters it and unwinds, while the baseline stops and leaks. Bring back both final ledgers. Good luck.

## Definition of done

- [ ] A partition contract rejecting a plan whose keys are not disjoint and complete, checked before any step runs
- [ ] A topological sort producing a dependency order with zero stale reads, and reporting a cycle as uncompletable
- [ ] Bounded retries that absorb a transient failure and a dead-letter queue that contains a poison step
- [ ] A saga that compensates the committed prefix in reverse on a failure past the point of no return
- [ ] Confirmation the resilient run unwinds to exactly the starting ledger with the poison dead-lettered
- [ ] Confirmation the naive file-order, no-saga run leaks real side effects
- [ ] `python3 orchestrator.py --check` printing SELF-TEST PASS: partition, order, poison_dlq, resilient_clean, naive_leaks
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Name the four guarantees the resilient orchestrator composes and the prior module each comes from.
2. Why is commit-or-unwind the conjunction of all four rather than any one of them? Give a failure for dropping each.
3. The saga compensates the committed prefix in reverse. Why in reverse, and why does the failed step itself need no compensation?
4. The naive orchestrator leaked three effects — seat, card, and email. Explain which dropped guarantee caused each leak.
5. Your own workflow was run through both orchestrators after a poison injection. What was each one's final ledger?

## External resources

- Garcia-Molina & Salem, *Sagas* — my summary: the original long-lived-transaction paper behind compensating a completed prefix rather than locking; read it for why real side effects need compensation, not rollback.
- Temporal / AWS Step Functions orchestration docs — my summary: production workflow engines that persist the trace, make steps idempotent, and run compensations durably — the real systems this in-process composition abstracts; read them for how the guarantees survive crashes and distribution.
- This hub, *govern-inter-03*, *govern-inter-04*, *govern-inter-05*, *govern-inter-06* — the partition contract, task DAG, saga, and retry-plus-dead-letter modules this capstone composes; read each for its guarantee in isolation before seeing them combined into one orchestrator.
