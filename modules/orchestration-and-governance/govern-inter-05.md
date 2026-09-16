---
id: govern-inter-05
title: A saga compensates the completed steps in reverse — not abort, not compensate-all
topic: orchestration-and-governance
level: intermediate
status: ready
time: 8-10h
summary: A multi-step workflow with real side effects cannot be rolled back by a transaction — once a seat is held and a card is charged, the effects are out in the world — so a saga pairs each forward action with a compensating action and, on failure, undoes the steps that already completed, in reverse order. When issue_ticket fails after reserve_seat and charge_card commit, the correct saga compensates charge then reserve and returns the ledger to zero; abort-only stops and leaves a seat held and a card charged with no ticket; compensate-all runs every step's compensation including the one that never ran, driving tickets to negative one. Only compensating the completed prefix, reversed, is consistent — the failed step needs no compensation because its effect never landed.
eli5: If you are assembling a toy and get stuck on the last piece, you cannot pretend you never started — you have already opened the box and attached three parts. To undo cleanly you take off exactly the parts you attached, in the reverse order you added them. Do nothing and you leave a half-built mess; take off parts you never attached and you break something that was fine.
---

## Why this module

When you fan a task out into steps that each do something real — reserve a resource, charge an account, send a message, write a record — you lose the safety net a database transaction gives you. A transaction can atomically roll back because nothing it did was visible until it committed; a workflow of side-effecting steps has already made each effect visible to the world by the time a later step fails. This module builds the saga pattern, which handles exactly this, and shows the two natural wrong answers on either side of it: doing too little on failure, and doing too much.

A saga pairs every forward action with a compensating action that semantically undoes it — reserve with release, charge with refund. It runs the steps forward, and if one fails, it runs the compensations for the steps that already completed, in reverse order, unwinding the work like popping a stack. The two failures that bracket it are instructive. Abort-only stops on failure and does nothing else, which leaves orphaned side effects: a seat held and a card charged for a ticket that was never issued, a customer billed for nothing. Compensate-all runs the compensation for every declared step, including the failed one and any never reached, which over-compensates: it refunds a charge that never happened, driving the ledger negative. The correct saga compensates exactly the completed prefix, reversed — and the failed step needs no compensation, because its effect never landed.

You need the fan-out and dependency framing from the earlier governance modules. Everything runs offline against a saga fixture — a three-step booking where the third step fails — stdlib Python 3, `$0.00`. State is a small effect ledger that a correct unwind must return to its initial value. The instinct to unlearn is that handling failure means aborting. Aborting a workflow that has already committed effects leaves those effects stranded; correct failure handling means compensating precisely what completed.

Here is the workflow failing partway:

```
# modules/orchestration-and-governance/code/govern-inter-05/ — COMPLETE, run from that directory
$ python3 saga.py --forward

FORWARD — run the workflow until a step fails
------------------------------------------------------------------
  completed: ['reserve_seat', 'charge_card']
  failed at: ['issue_ticket']
  state after forward (effects committed): {'seats_held': 1, 'balance': -100, 'tickets': 0}
```

run: 2026-08-26 · deterministic; workflow and effects are a fixture · 3 steps · `python3 saga.py --forward`

Two steps committed real effects — a seat held, a hundred charged — and the third failed. The state is now inconsistent: money taken, seat held, no ticket. This module is how you get from here back to zero, and the two ways people get it wrong.

## Concepts

Named here so you can find them again; each is built below.

- **Saga** — a workflow of side-effecting steps, each with a paired compensating action.
- **Forward action** — a step's real effect on shared state (hold a seat, charge a card).
- **Compensating action** — the semantic undo of a forward action (release, refund).
- **Completed prefix** — the steps that ran before the failure; exactly what must be compensated.
- **Reverse-order unwind** — compensating completed steps last-in-first-out, like popping a stack.
- **Orphaned effect** — a committed effect left in place because failure was handled by aborting.

## Worked example

Source: the saga pattern from distributed-systems practice (Garcia-Molina & Salem's sagas, and its modern use in microservice and multi-agent orchestration), reduced to a three-step booking; the effects here stand in for real side-effecting actions so the unwind is exact and checkable against a ledger.

Script and fixture: `modules/orchestration-and-governance/code/govern-inter-05/` — `saga.py`, and `saga.json`, a three-step booking (reserve, charge, issue) where issue fails. Every command runs from there.

### The ledger and the forward run

State is an effect ledger. Each forward action adds its effect; each compensation subtracts it. A consistent unwind returns every field to its initial value.

```
# saga.py:41-55 — COMPLETE (apply an effect; run forward until a step fails)
def apply_effect(state, effect, sign=1):
    """Add (sign=+1) or undo (sign=-1) an effect to the running ledger."""
    for field, delta in effect.items():
        state[field] += sign * delta


def run_forward(steps, state):
    """Apply forward actions until one fails. Returns the list of COMPLETED steps."""
    completed = []
    for step in steps:
        if step["fails"]:
            break  # the failing step's effect never lands
        apply_effect(state, step["effect"], sign=1)
        completed.append(step)
    return completed
```

The crucial detail is the `break` before applying the failing step's effect: when `issue_ticket` fails, its effect never lands, so `tickets` stays 0 and the step is not in `completed`. This is what makes the failed step need no compensation — there is nothing to undo. The forward run returns exactly the prefix that committed, which is the precise set the saga must reverse.

### The correct saga: compensate the completed prefix, reversed

Run forward, then walk the completed steps backward, undoing each.

```
# saga.py:60-66 — COMPLETE (forward, then compensate completed steps in reverse)
def saga_correct(data):
    """Forward until failure, then compensate the COMPLETED steps in REVERSE order."""
    state = copy.deepcopy(data["initial_state"])
    completed = run_forward(data["steps"], state)
    for step in reversed(completed):  # unwind in reverse
        apply_effect(state, step["effect"], sign=-1)
    return state, completed
```

Run it and the ledger returns to zero:

```
# $ python3 saga.py --run
#   compensated (reverse of completed): ['charge_card', 'reserve_seat']
#   final state: {'seats_held': 0, 'balance': 0, 'tickets': 0}
#   fully reverted to initial? True
```

run: 2026-08-26 · deterministic · `python3 saga.py --run`

The saga compensated `charge_card` then `reserve_seat` — the reverse of the order they ran — refunding the hundred and releasing the seat, and left `issue_ticket` alone because it never committed. Every field is back to its initial value. The reverse order matters when compensations have dependencies: you refund the charge before releasing the seat that justified it, just as you unstack in the opposite order you stacked. Here the effects are independent so the arithmetic would balance either way, but reverse order is the rule because it is the only order that is always safe.

<svg viewBox="0 0 700 210" role="img" aria-label="A stack diagram. Forward: push reserve_seat, then charge_card; issue_ticket fails and is not pushed. Compensation: pop charge_card (refund), then pop reserve_seat (release), unwinding in reverse. The stack returns to empty.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">forward pushes effects; compensation pops them in reverse (LIFO)</text>
    <text x="90" y="44" fill="var(--ink)">forward -></text>
    <rect x="60" y="120" width="130" height="26" fill="var(--panel)" stroke="var(--line)"></rect><text x="125" y="137" text-anchor="middle" fill="var(--ink)" font-size="8">reserve_seat</text>
    <rect x="60" y="92" width="130" height="26" fill="var(--panel)" stroke="var(--line)"></rect><text x="125" y="109" text-anchor="middle" fill="var(--ink)" font-size="8">charge_card</text>
    <rect x="60" y="64" width="130" height="26" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"></rect><text x="125" y="81" text-anchor="middle" fill="var(--s2)" font-size="8">issue_ticket FAILS</text>
    <path d="M 260 105 L 320 105" stroke="var(--muted)"></path>
    <text x="430" y="44" fill="var(--ink)">&lt;- compensate</text>
    <rect x="400" y="92" width="130" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="465" y="109" text-anchor="middle" fill="var(--acc-ink)" font-size="8">refund (pop 1st)</text>
    <rect x="400" y="120" width="130" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="465" y="137" text-anchor="middle" fill="var(--acc-ink)" font-size="8">release (pop 2nd)</text>
    <text x="400" y="176" fill="var(--s1)" font-size="8">stack empty -> ledger back to zero</text>
    <text x="60" y="176" fill="var(--s2)" font-size="8">failed step never pushed -> nothing to pop</text>
  </g>
</svg>
^ Forward pushes each committed effect onto a stack; the failing step is never pushed. Compensation pops in reverse — refund before release — until the stack is empty and the ledger is back to zero.

### Failure one: abort-only leaves orphans

The first wrong answer is to treat a failed workflow like a failed function: stop and return.

```
# saga.py:69-73 — COMPLETE (abort-only: stop on failure, leave effects committed)
def saga_abort_only(data):
    """The bug: on failure, stop. Completed steps' effects are left orphaned."""
    state = copy.deepcopy(data["initial_state"])
    run_forward(data["steps"], state)
    return state
```

It runs forward, hits the failure, and returns the state as-is — `{seats_held: 1, balance: -100, tickets: 0}`. The seat is still held, the card is still charged, and there is no ticket to show for it. These are orphaned effects: real actions with no completing outcome, the customer billed for nothing. Aborting felt like the safe conservative move and it is the opposite — it freezes the system in its most inconsistent state. A workflow that can fail after committing effects must compensate, not abort.

### Failure two: compensate-all over-reverts

The second wrong answer over-corrects: compensate every declared step, not just the completed ones.

```
# saga.py:76-81 — COMPLETE (compensate-all: undo every step, even the un-run one)
def saga_compensate_all(data):
    """The bug: compensate EVERY declared step, even the failed/never-run ones."""
    state = copy.deepcopy(data["initial_state"])
    run_forward(data["steps"], state)
    for step in reversed(data["steps"]):  # compensates issue_ticket too -- it never ran
        apply_effect(state, step["effect"], sign=-1)
    return state
```

Because it compensates `issue_ticket`, whose forward effect never landed, it subtracts a ticket that was never added — `tickets` goes to −1. It undid something that never happened. In a real system this is refunding a charge that never went through, or releasing a seat that was never reserved, corrupting state in the opposite direction from the orphan. The compensation set must be exactly the completed steps, no more: the failed and unreached steps have no effect to undo.

**A saga compensates exactly the completed prefix of steps, in reverse order — aborting on failure leaves orphaned effects, and compensating every declared step over-reverts a step that never ran, so only unwinding what actually committed returns the system to a consistent state.**

### The three side by side

Put the final states together against the target of all-zero.

```
# $ python3 saga.py --compare
#   abort-only:      {'seats_held': 1, 'balance': -100, 'tickets': 0}   reverted=False  (orphaned effects)
#   compensate-all:  {'seats_held': 0, 'balance': 0, 'tickets': -1}   reverted=False  (over-compensated)
#   correct saga:    {'seats_held': 0, 'balance': 0, 'tickets': 0}   reverted=True
```

run: 2026-08-26 · deterministic · `python3 saga.py --compare`

<svg viewBox="0 0 700 190" role="img" aria-label="Three rows showing the final ledger under each policy against the target of all zeros. abort-only: seats +1 and balance -100 bars remain (nonzero). compensate-all: a tickets -1 bar (nonzero the other way). correct saga: all bars flat at zero.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">final ledger by policy — the zero line is consistency</text>
    <line x1="60" y1="60" x2="650" y2="60" stroke="var(--grid)"></line>
    <text x="20" y="46" fill="var(--ink)" font-size="8">abort-only</text>
    <rect x="200" y="46" width="40" height="14" fill="var(--s2)"></rect><text x="245" y="57" fill="var(--s2)" font-size="7">seat held</text>
    <rect x="360" y="60" width="40" height="14" fill="var(--s2)"></rect><text x="405" y="72" fill="var(--s2)" font-size="7">-100 charged</text>
    <line x1="60" y1="115" x2="650" y2="115" stroke="var(--grid)"></line>
    <text x="20" y="101" fill="var(--ink)" font-size="8">compensate-all</text>
    <rect x="200" y="115" width="40" height="14" fill="var(--s2)"></rect><text x="245" y="126" fill="var(--s2)" font-size="7">-1 ticket (never issued)</text>
    <line x1="60" y1="165" x2="650" y2="165" stroke="var(--grid)"></line>
    <text x="20" y="151" fill="var(--ink)" font-size="8">correct saga</text>
    <circle cx="220" cy="165" r="3" fill="var(--s1)"></circle><circle cx="380" cy="165" r="3" fill="var(--s1)"></circle><circle cx="540" cy="165" r="3" fill="var(--s1)"></circle>
    <text x="560" y="169" fill="var(--s1)" font-size="7">all zero — reverted</text>
  </g>
</svg>
^ Abort-only leaves bars above the zero line (effects left in); compensate-all leaves a bar below it (an effect taken out that was never there); only the correct saga sits flat on zero.

Only the correct saga returns to the initial state. Abort-only is inconsistent by leaving effects in; compensate-all is inconsistent by taking effects out that were never there. The two failures are mirror images — under-compensation and over-compensation — and the correct policy is the narrow path between them: compensate what completed, exactly, reversed.

### The self-test

The `--check` mode asserts all three outcomes and the compensation set: the correct saga reverts, abort orphans, compensate-all over-reverts, and the failed step is never compensated.

```
# $ python3 saga.py --check
#   correct saga returns to the initial state = True ({'seats_held': 0, 'balance': 0, 'tickets': 0})
#   abort-only leaves orphaned effects = True ({'seats_held': 1, 'balance': -100, 'tickets': 0})
#   compensate-all over-compensates the un-run step = True ({'seats_held': 0, 'balance': 0, 'tickets': -1})
#   the failed step is never compensated = True (compensated 2 of 3 steps)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 saga.py --check`

The `reverts` line is the correctness anchor: the correct saga must return the ledger to its exact initial value, and if the compensation set or order were wrong that equality would break. The `only_completed` line encodes the crux — the saga compensates two of three steps, never the failed one — so the test proves the compensation set is the completed prefix, which is what separates the correct policy from compensate-all.

### The running tally

| policy | final ledger | reverted? | failure mode |
|---|---|---|---|
| abort-only | seats 1, balance −100, tickets 0 | no | orphaned effects (under) |
| compensate-all | seats 0, balance 0, tickets −1 | no | over-reverted the un-run step |
| correct saga | seats 0, balance 0, tickets 0 | yes | — |

<svg viewBox="0 0 700 150" role="img" aria-label="A one-dimensional axis of compensation amount. The left end is under-compensation (abort-only, orphaned effects). The right end is over-compensation (compensate-all, un-run step undone). A single point in the middle, at 'compensate the completed prefix', is marked as the only consistent policy.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">how much to undo — consistency is a single point between two errors</text>
    <line x1="60" y1="80" x2="640" y2="80" stroke="var(--grid)"></line>
    <circle cx="100" cy="80" r="5" fill="var(--s2)"></circle><text x="100" y="66" text-anchor="middle" fill="var(--s2)" font-size="8">abort-only</text><text x="100" y="104" text-anchor="middle" fill="var(--muted)" font-size="7">undo too little</text>
    <circle cx="350" cy="80" r="6" fill="var(--s1)"></circle><text x="350" y="62" text-anchor="middle" fill="var(--s1)" font-size="8">compensate completed prefix</text><text x="350" y="104" text-anchor="middle" fill="var(--s1)" font-size="7">exactly consistent</text>
    <circle cx="600" cy="80" r="5" fill="var(--s2)"></circle><text x="600" y="66" text-anchor="middle" fill="var(--s2)" font-size="8">compensate-all</text><text x="600" y="104" text-anchor="middle" fill="var(--muted)" font-size="7">undo too much</text>
    <text x="350" y="132" text-anchor="middle" fill="var(--muted)" font-size="8">one uncompensated effect = orphan; one over-compensated = corruption</text>
  </g>
</svg>
^ The correct policy is a single point: undo exactly the steps that committed. Fall short and effects are orphaned; overshoot and effects that never happened are undone. Both neighbours of the right answer are inconsistent.

The three rows are the same failure handled three ways, and consistency is a razor's edge between two errors. Leave one completed effect uncompensated and you have an orphan; compensate one uncompleted step and you have corruption. The correct saga is defined entirely by matching the compensation set to the completed set — which is why the forward run returns that set explicitly, so the unwind cannot guess.

### What we did not settle

Real sagas carry more machinery. Compensations must be idempotent and retryable, because the compensation itself can fail or run twice — the same at-least-once problem the idempotency module handled, now on the undo path. Some steps are not cleanly compensable (an email cannot be unsent), so sagas distinguish compensable, retriable, and pivot steps, and order them so the irreversible step comes last. Orchestration versus choreography is a real design axis: a central coordinator running the saga, versus each step emitting events the next reacts to. And a saga gives up isolation — other actors can observe the intermediate state before compensation runs — so it trades atomicity for availability. The core here — pair every action with a compensation, and on failure undo the completed prefix in reverse — is the invariant under all of it.

## Build

The practice in one paragraph: for any multi-step workflow with real side effects, pair every forward action with a compensating action; run forward tracking exactly which steps completed; on failure, run the compensations for the completed steps in reverse order and nothing else; and verify the system returns to a consistent state, neither leaving committed effects (abort) nor undoing effects that never landed (compensate-all). Make compensations idempotent, and order irreversible steps last.

We opened on the failed forward run. The number that proves the saga is correct is the reverted ledger:

```
# modules/orchestration-and-governance/code/govern-inter-05/ — COMPLETE, run from that directory
$ python3 saga.py --compare
  abort-only:      {...}   reverted=False
  correct saga:    {'seats_held': 0, 'balance': 0, 'tickets': 0}   reverted=True
```

Now build one. Model a real multi-step workflow of your own — a booking, a deploy, a data migration — give each step a forward and a compensating action over a shared ledger, and fail a middle step. Your number to beat is not that it completes; it is **that the ledger returns exactly to its initial state after a mid-workflow failure**, which only compensating the completed prefix in reverse achieves. Then try abort-only and compensate-all and watch each leave the ledger wrong in its own direction. Bring back all three final states. Good luck.

## Definition of done

- [ ] A multi-step workflow where each step has a forward action and a compensating action
- [ ] A shared effect ledger that a consistent unwind returns to its initial value
- [ ] The forward run tracked so the completed prefix is known exactly
- [ ] On failure, compensation of the completed steps in reverse order
- [ ] Confirmation the ledger fully reverts, and the failed step is not compensated
- [ ] The abort-only and compensate-all policies shown to leave the ledger inconsistent
- [ ] `python3 saga.py --check` printing SELF-TEST PASS: reverts, abort-orphans, over-reverts, only-completed
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why can a workflow of side-effecting steps not be rolled back the way a database transaction can?
2. What exactly is the set of steps a saga must compensate, and why is the failed step not in it?
3. Abort-only and compensate-all are both wrong. Describe the opposite way each corrupts the state.
4. Why does the saga compensate in reverse order, and when does the order actually matter?
5. Your own workflow failed at a middle step. What was the final ledger under each of the three policies, and which returned to the initial state?

## External resources

- Garcia-Molina & Salem, *Sagas* (1987) — my summary: the original paper defining sagas as sequences of transactions with compensating transactions for failure recovery without global locks; read it for the formal model this module implements.
- Microservices saga-pattern writing (e.g. Richardson, microservices.io) — my summary: orchestration vs choreography, compensable/pivot/retriable steps, and idempotent compensations in production; read it for the machinery beyond the core unwind here.
- This hub, *govern-inter-04* — modules/orchestration-and-governance/govern-inter-04.md — my summary: the task-DAG scheduling module for ordering multi-agent work by dependencies; read it for the forward-ordering counterpart to this module's reverse-order unwind — how the steps get ordered before a saga has to undo them.
