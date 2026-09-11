---
id: saga-inter-01
title: Undo a failed multi-step transaction with compensating actions, in reverse — a saga stays consistent without the locks 2PC holds
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A transaction that spans several services — reserve a flight, reserve a hotel, charge a card — must not leave a half-finished mess, and two-phase commit prevents that by making every participant lock its resources and wait for a global commit (atomic, but it blocks: a coordinator crash freezes the participants holding locks). A saga takes the opposite approach — run the steps one at a time, each committing immediately with no lock held, and if a later step fails, undo the completed steps by running a compensating action for each. No step waits on the others; consistency is restored by compensation, not prevented by locking. The mechanism has two rules: forward, execute steps in order, each fully committing before the next; on failure, for every completed step run its compensating action, in reverse order, because later steps may depend on earlier ones so you unwind newest-first (cancel the hotel before the flight, the mirror of booking). The failing step is not compensated because it never completed. The contrast with a naive pipeline that stops at failure and leaves every completed step's effect in place — the orphaned reservations — is the point: the saga's compensating actions are an explicit inverse for each step, invoked on failure to clean up, which is what lets a saga be lock-free where 2PC is not. The cost: a saga is only eventually consistent (the partial effects are visible between a step and its compensation), and every step needs a real compensating action (you can cancel a reservation, but some effects cannot be truly undone). On a fixture where a trip books reserve_flight, reserve_hotel, then charge_card fails, the naive pipeline leaves the flight and hotel reserved (2 orphans) while the saga runs cancel_hotel then cancel_flight, leaving none.
eli5: Imagine booking a trip in steps: first you grab plane seats, then a hotel room, then you go to pay — and your card is declined. If you just walk away, you've left a plane seat and a hotel room reserved in your name that nobody paid for, blocking them from other people and maybe costing you a cancellation fee later. The smart way is to have an "undo" ready for each step you did: since payment failed, you cancel the hotel room you grabbed, then cancel the plane seats — undoing them in the opposite order you did them — so everything is released and it's as if you never started. You don't lock the whole airline and hotel while you shop (that would freeze everyone else); you just tidy up your own steps if something goes wrong.
---

## Why this module

Distributed transactions force a choice, and it is one of the cleanest architecture tradeoffs there is. When an operation touches multiple services and any of them can fail, you must either prevent partial states (lock everything until you are sure all can commit — two-phase commit) or allow partial states and clean them up (commit each step and undo on failure — a saga). This module is the second half of that tradeoff, and it is worth understanding alongside 2PC because the choice between them determines whether your system blocks under failure or merely becomes briefly inconsistent.

The saga's bet is that holding locks across a multi-step, possibly long-running operation (booking a trip, fulfilling an order, onboarding a user) is worse than tolerating a short window of inconsistency. So it does not lock. Each step commits on its own, immediately, releasing its resources — which means the whole operation never blocks other work, and a slow or crashed participant does not freeze the rest. The price is that after step two commits and before step three, the system genuinely has a flight and hotel reserved with no payment: a real intermediate state.

Handling failure without locks requires an explicit undo for each step, and running those undos correctly is the saga's core. This module runs a three-step booking that fails at the last step, both with and without compensation.

**Run a multi-step distributed transaction as a saga — commit each step immediately and, on failure, undo the completed steps by running their compensating actions in reverse order — rather than holding locks across all steps (2PC), because compensation restores consistency without blocking, at the cost of eventual (not immediate) consistency and a requirement that every step have a real compensating action.**

## Concepts

The fixture is a trip booking: three steps, each with a forward action and a compensating action that reverses it, and the step that fails.

```json filename=modules/orchestration-and-governance/code/saga-inter-01/saga.json:3-8 COMPLETE
  "steps": [
    {"name": "reserve_flight", "compensate": "cancel_flight"},
    {"name": "reserve_hotel", "compensate": "cancel_hotel"},
    {"name": "charge_card", "compensate": "refund_card"}
  ],
  "fails_at": "charge_card"
```

The completed steps are those before the failure — the ones whose effects exist and must be undone.

```python filename=modules/orchestration-and-governance/code/saga-inter-01/saga.py:34-41 COMPLETE
def completed_steps(steps, fails_at):
    """The steps that ran successfully -- those before the failing one."""
    out = []
    for s in steps:
        if s["name"] == fails_at:
            break
        out.append(s)
    return out
```

The naive pipeline leaves those completed steps' effects orphaned; the saga produces compensating actions for exactly them, in reverse order.

```python filename=modules/orchestration-and-governance/code/saga-inter-01/saga.py:44-51 COMPLETE
def naive_orphans(steps, fails_at):
    """Naive pipeline: stops at failure, leaving the completed steps' effects in place."""
    return [s["name"] for s in completed_steps(steps, fails_at)]


def saga_compensations(steps, fails_at):
    """Saga: compensating actions for the completed steps, in reverse order."""
    return [s["compensate"] for s in reversed(completed_steps(steps, fails_at))]
```

Reverse order matters: later steps may depend on earlier ones, so you unwind newest-first, exactly mirroring how you built up the state.

<svg role="img" aria-label="Forward: reserve_flight, reserve_hotel, then charge_card fails; backward compensation: cancel_hotel then cancel_flight, mirroring the forward order" viewBox="0 0 320 130">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">forward (commit each step)</text>
  <rect x="14" y="24" width="80" height="18" fill="var(--s1)"/><text x="20" y="37" font-size="7.5" fill="var(--panel)">reserve_flight</text>
  <rect x="100" y="24" width="80" height="18" fill="var(--s1)"/><text x="108" y="37" font-size="7.5" fill="var(--panel)">reserve_hotel</text>
  <rect x="186" y="24" width="80" height="18" fill="none" stroke="var(--s2)" stroke-width="1.5"/><text x="196" y="37" font-size="7.5" fill="var(--s2)">charge_card ✗</text>
  <text x="10" y="72" font-size="8.5" fill="var(--muted)">on failure, compensate in reverse</text>
  <rect x="100" y="80" width="80" height="18" fill="var(--muted)"/><text x="110" y="93" font-size="7.5" fill="var(--panel)">cancel_hotel</text>
  <rect x="14" y="80" width="80" height="18" fill="var(--muted)"/><text x="24" y="93" font-size="7.5" fill="var(--panel)">cancel_flight</text>
  <path d="M 186 42 Q 150 60 140 78" fill="none" stroke="var(--ink)" stroke-width="1"/>
  <text x="10" y="118" font-size="7.5" fill="var(--ink)">cancel_hotel first, then cancel_flight — newest completed step undone first</text>
</svg>
^ The saga books flight then hotel, then charge_card fails. It compensates in reverse — cancel_hotel, then cancel_flight — undoing the newest completed step first, the mirror of the forward order. The failed charge is not compensated; it never happened.

**A saga trades locking for undoing: each step commits freely, and correctness on failure comes from an explicit compensating action per step, run in reverse to respect dependencies.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the distributed-transaction step of an orchestration layer, reduced to a three-step booking so every action is checkable by hand.

Run `--run` to see the forward execution.

```text filename=saga.py --run
  reserve_flight   done
  reserve_hotel    done
  charge_card      FAILS
  completed before failure: ['reserve_flight', 'reserve_hotel']
```

The saga runs forward: reserve_flight commits, reserve_hotel commits, and charge_card fails. Two steps completed before the failure, and their effects — a reserved flight and a reserved hotel — are now real, committed, and unpaid. This is the intermediate state a saga permits and 2PC's locks would have prevented; the question is what happens next.

Now `--compensate` compares doing nothing to compensating.

```text filename=saga.py --compensate
  naive (no undo): leaves 2 orphaned effect(s): ['reserve_flight', 'reserve_hotel']
  saga compensations (reverse order): ['cancel_hotel', 'cancel_flight']
  saga orphaned effects after compensation: 0
  the failing step (charge_card) is not compensated -- it never completed
```

The naive pipeline, with no notion of undo, simply stops and leaves both reservations orphaned — a flight and hotel held with no payment, leaking money and blocking inventory. The saga runs the compensating actions for the two completed steps, in reverse: cancel_hotel first, then cancel_flight, returning the system to a clean state with zero orphaned effects. And charge_card is not compensated — it never completed, so there is nothing to undo. The saga restored consistency by undoing exactly what had been done.

**The naive pipeline leaves two orphaned reservations; the saga cancels the hotel then the flight and leaves none — the compensating actions are the undo that lets the saga clean up a failure without ever having held a lock.**

## Build

The self-test asserts the setup and the fix: the transaction fails partway, the naive pipeline leaves orphans, and the saga compensates exactly the completed steps in reverse order.

```python filename=modules/orchestration-and-governance/code/saga-inter-01/saga.py:85-95 COMPLETE
    fails_partway = 0 < len(completed) < len(steps)
    print("  the transaction fails after some steps completed = %s (%d of %d done)" % (fails_partway, len(completed), len(steps)))

    naive_leaves_partial = len(naive_orphans(steps, fails)) > 0
    print("  the naive pipeline leaves orphaned effects = %s (%s)" % (naive_leaves_partial, naive_orphans(steps, fails)))

    saga_compensates_all_completed = len(comps) == len(completed)
    print("  the saga compensates exactly the completed steps = %s (%d compensations for %d completed)" % (saga_compensates_all_completed, len(comps), len(completed)))

    reverse_order = comps == [s["compensate"] for s in reversed(completed)]
    print("  the compensations run in reverse order = %s (%s)" % (reverse_order, comps))
```

<svg role="img" aria-label="Two end states: naive leaves flight and hotel reserved (orphans), saga leaves nothing reserved after cancel_hotel and cancel_flight" viewBox="0 0 320 110">
  <text x="10" y="18" font-size="8.5" fill="var(--s2)">naive: 2 orphaned effects remain</text>
  <rect x="14" y="26" width="90" height="16" fill="var(--s2)"/><text x="20" y="38" font-size="7.5" fill="var(--panel)">flight reserved</text>
  <rect x="110" y="26" width="90" height="16" fill="var(--s2)"/><text x="116" y="38" font-size="7.5" fill="var(--panel)">hotel reserved</text>
  <text x="10" y="70" font-size="8.5" fill="var(--s1)">saga: 0 orphaned effects</text>
  <rect x="14" y="78" width="90" height="16" fill="none" stroke="var(--line)" stroke-dasharray="3 2"/><text x="20" y="90" font-size="7.5" fill="var(--muted)">flight cancelled</text>
  <rect x="110" y="78" width="90" height="16" fill="none" stroke="var(--line)" stroke-dasharray="3 2"/><text x="116" y="90" font-size="7.5" fill="var(--muted)">hotel cancelled</text>
</svg>
^ The naive end state has a flight and hotel reserved and unpaid; the saga end state has both cancelled, clean. The compensations are the difference between a consistent system and two leaked reservations.

Running the check confirms every clause, including that the failing step is not compensated and the saga undoes every orphan.

```text filename=saga.py --check
  the transaction fails after some steps completed = True (2 of 3 done)
  the naive pipeline leaves orphaned effects = True (['reserve_flight', 'reserve_hotel'])
  the saga compensates exactly the completed steps = True (2 compensations for 2 completed)
  the compensations run in reverse order = True (['cancel_hotel', 'cancel_flight'])
  the failing step is NOT compensated (it never completed) = True
  the saga undoes every effect the naive pipeline would orphan = True
```

**The check pins the compensations to exactly the completed steps, in reverse, sparing the failed one — so the saga's undo is precise: everything done is undone, nothing that was not done is touched.**

## Definition of done

Two properties close it. The failing step must not be compensated (only completed steps have effects to undo), and the saga must undo every effect the naive pipeline would have orphaned. Together they define a correct compensation: complete coverage of the completed steps, and nothing more.

```python filename=modules/orchestration-and-governance/code/saga-inter-01/saga.py:97-101 COMPLETE
    failing_step_not_compensated = next(s["compensate"] for s in steps if s["name"] == fails) not in comps
    print("  the failing step is NOT compensated (it never completed) = %s" % failing_step_not_compensated)

    saga_no_orphans = set(naive_orphans(steps, fails)) == {s["name"] for s in completed} and len(comps) == len(naive_orphans(steps, fails))
    print("  the saga undoes every effect the naive pipeline would orphan = %s" % saga_no_orphans)
```

Three caveats place the saga against its alternative. First, the consistency model: a saga is eventually consistent, not atomic — between a step committing and its compensation running, the partial state is visible to other observers, so a saga is wrong where you need strict isolation (no one may ever see the flight reserved without payment); that is where 2PC's locks, and their blocking cost, are the right trade. Second, compensations must be real and should be idempotent and near-guaranteed to succeed: you can cancel a reservation or refund a charge, but some effects cannot be truly undone (an email sent, a physical shipment), and for those a saga must be designed so such steps come last or are replaced by a reservation-then-confirm pattern; a compensation that can itself fail needs its own retry, because a saga that cannot complete its rollback is stuck in a worse state than either extreme. Third, real sagas need durable orchestration — the saga's progress must be persisted so that if the orchestrator crashes mid-rollback it resumes the compensations, which is why sagas are typically run on a workflow engine rather than in-process. The essence, though, is the pattern this module shows: commit forward, compensate backward, lock nothing.

<svg role="img" aria-label="Two approaches contrasted: 2PC holds locks across all steps and blocks on coordinator failure but is atomic; saga holds no locks and never blocks but is only eventually consistent" viewBox="0 0 320 120">
  <text x="10" y="16" font-size="8.5" fill="var(--s2)">two-phase commit</text>
  <rect x="14" y="24" width="60" height="14" fill="var(--s2)"/><rect x="76" y="24" width="60" height="14" fill="var(--s2)"/><rect x="138" y="24" width="60" height="14" fill="var(--s2)"/>
  <text x="204" y="34" font-size="7" fill="var(--muted)">locks held across all → atomic, blocks</text>
  <text x="10" y="70" font-size="8.5" fill="var(--s1)">saga</text>
  <rect x="14" y="78" width="60" height="14" fill="var(--s1)"/><rect x="76" y="78" width="60" height="14" fill="var(--s1)" opacity="0.6"/><rect x="138" y="78" width="60" height="14" fill="var(--s1)" opacity="0.35"/>
  <text x="204" y="88" font-size="7" fill="var(--muted)">each commits, no lock → non-blocking, eventual</text>
  <text x="10" y="110" font-size="7.5" fill="var(--ink)">2PC prevents partial states with locks; a saga permits then compensates them</text>
</svg>
^ The two ends of the tradeoff: 2PC holds locks across every step (atomic, but blocks on coordinator failure), while a saga commits each step lock-free (non-blocking, but eventually consistent). The saga permits the partial state and cleans it up rather than preventing it.

**Done means the saga compensates exactly the completed steps in reverse and spares the failed one — lock-free consistency via explicit undo, correct when steps are individually committable and reversible, and eventually (not immediately) consistent by design.**

## Boss fight

An e-commerce team implements order fulfillment as a single distributed transaction across inventory, payment, and shipping services using two-phase commit. It is correct but slow and fragile: during peak load, orders hang for seconds, and when the coordinator restarts during a deploy, inventory rows stay locked and the whole checkout flow stalls. They ask whether a saga would help and what they would have to change. What do you tell them?

A saga would directly address the hang and the stall, because both come from 2PC holding locks across the whole multi-service transaction: participants lock their resources at prepare and hold them until the global commit, so under load orders queue behind locked rows, and a coordinator restart leaves prepared participants blocked (in doubt, holding locks) until it recovers — exactly the stall they see. A saga holds no cross-step locks: each service commits its step immediately and releases, so orders do not queue on locks and a crash of the orchestrator does not freeze inventory; the orchestrator resumes from its durable log and continues or compensates. What they must change and accept: first, define a compensating action for every step — release inventory, refund payment, cancel shipping label — and order the steps so the hardest-to-undo one (physical shipping) comes last, ideally after payment is confirmed, so a failure rarely requires undoing an irreversible action. Second, accept eventual consistency: there will be a brief window where inventory is decremented but payment has not completed (or vice versa), visible to other observers, so any invariant that requires never seeing a partial order must be relaxed or handled with a reservation/confirmation state rather than a hard lock. Third, make compensations idempotent and retryable, and run the saga on a durable workflow engine so a crashed orchestrator resumes its rollback rather than leaving a half-undone order. Fourth, keep 2PC (or a stricter mechanism) only for any sub-step that genuinely cannot tolerate a visible intermediate state. The net trade is giving up strict atomicity and immediate consistency in exchange for a non-blocking, load-tolerant checkout — usually the right trade for order fulfillment, where steps are reversible and throughput matters more than momentary isolation.

## External resources

Hector Garcia-Molina and Kenneth Salem, "Sagas" (1987) — the original paper defining the saga: a sequence of transactions each with a compensating transaction, run without holding locks across the whole sequence, and compensated in reverse on failure.

Chris Richardson's microservices.io saga pattern (choreography vs orchestration) and Martin Kleppmann, *Designing Data-Intensive Applications* on distributed transactions — practical treatments of implementing sagas, why compensations must be idempotent and possible, and how sagas trade atomicity for availability against 2PC.
