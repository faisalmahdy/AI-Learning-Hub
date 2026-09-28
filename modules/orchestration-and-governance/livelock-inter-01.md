---
id: livelock-inter-01
title: Break the symmetry of retries to escape livelock — two workers that grab-fail-release in lockstep make no progress though neither is blocked
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: Livelock is a failure where processes keep changing state in response to each other and make no progress, even though none is blocked. Two transactions that each need the same two resources in opposite order show it: each round both grab their first resource (they differ, so both succeed), each fails at its second because the other holds it, and each politely releases what it holds and retries. This is not deadlock — the distinction is the whole point. In deadlock each would hold its first resource and wait forever, a cycle in the wait-for graph a detector can find and break by aborting a victim; here nothing waits and nothing is held between rounds, so there is no cycle and nothing for a deadlock detector to abort, and every liveness check that looks for stuck processes passes while zero work gets done. The cause is symmetry: if both retry on the same schedule, each round is a bit-for-bit repeat of the last. The cure is to make the retries asymmetric so the tie breaks exactly once — back off by different amounts (here by transaction id), so one retries while the other is still waiting, gets both resources, completes, and clears the way; randomized backoff does the same statistically, which is why real retry loops randomize. On a fixture of two transactions and a 6-round budget, the lockstep policy completes zero transactions over the full budget with the resources free at every round boundary (livelock, not deadlock), while the asymmetric policy completes both in three rounds.
eli5: Picture two people meeting in a narrow hallway. Each steps to the same side to let the other pass; they are now face to face again. So each steps to the other side; face to face again. They keep politely dodging in perfect unison and never get past each other, even though neither is stuck against a wall — they are both moving, both trying, both being courteous, and both getting nowhere. That is livelock: lots of activity, no progress, and nobody is actually blocked. The fix is to break the mirror-image dance: one person just waits a moment while the other goes. Making the two behave differently — even a tiny random pause — lets them get past, where doing the exact same thing at the exact same time never can.
---

## Why this module

The topic already has a module on deadlock — processes stuck in a cycle, each holding something the next one needs, waiting forever — and the fix there is to detect the cycle and abort a victim. Livelock is the failure that looks like deadlock's opposite and hides from deadlock's cure: the processes are not stuck at all. They are running flat out, doing work every moment, and still nothing finishes.

It happens when processes react to a conflict by backing off and retrying, which is usually the right thing to do, and then retry in a way that recreates the same conflict. Two transactions that each need the same two resources in opposite order are the classic case: each grabs one, finds the other taken, and — to be polite and avoid deadlock — releases and tries again. If they do this in step, the release-and-retry just resets them to the start, and they loop.

What makes livelock nasty in production is that the usual alarms stay quiet. A deadlock detector walks the wait-for graph looking for a cycle of blocked processes; in livelock nothing is blocked and nothing is held between attempts, so there is no cycle to find. Health checks that watch for stuck threads see busy, responsive threads. CPU is high, throughput is zero, and every tool that defines "stuck" as "not running" reports the system healthy.

**Livelock is progress-free activity: processes keep grabbing, failing, and releasing in response to each other, so nothing is blocked and a deadlock detector finds no cycle to break — yet no work completes.**

## Concepts

Draw the conflict. Transaction 0 wants A then B; transaction 1 wants B then A. They ask for different resources first, so both get their first grab. Then each asks for its second — the one the other is now holding — and both fail. The only safe reaction that avoids deadlock is to let go of the first resource and retry, so both do, and the round ends with everything free and nothing accomplished.

<svg role="img" aria-label="Two transactions in a round. T0 holds A and wants B; T1 holds B and wants A. Arrows show each waiting on the resource the other holds. Then both release, and the resources are free again." viewBox="0 0 440 130">
<rect x="30" y="30" width="70" height="24" fill="var(--panel)" stroke="var(--line)"/><text x="65" y="46" fill="var(--ink)" font-size="9" text-anchor="middle">T0 holds A</text>
<rect x="340" y="30" width="70" height="24" fill="var(--panel)" stroke="var(--line)"/><text x="375" y="46" fill="var(--ink)" font-size="9" text-anchor="middle">T1 holds B</text>
<path d="M100 40 L 338 40" fill="none" stroke="var(--s2)"/><text x="220" y="34" fill="var(--s2)" font-size="8" text-anchor="middle">T0 wants B (held by T1)</text>
<path d="M340 50 L 102 50" fill="none" stroke="var(--s2)"/><text x="220" y="64" fill="var(--s2)" font-size="8" text-anchor="middle">T1 wants A (held by T0)</text>
<text x="220" y="92" fill="var(--muted)" font-size="9" text-anchor="middle">both fail their second grab, both release</text>
<text x="220" y="110" fill="var(--s1)" font-size="9" text-anchor="middle">round ends: A free, B free — and repeat</text>
</svg>
^ Each transaction holds one resource and wants the other's; both fail and release, so the round ends with everything free — the setup repeats identically next round.

Now the distinction that matters operationally. If instead of releasing, each transaction held its first resource and waited for the second, you would have deadlock: a cycle, T0 waiting on T1 waiting on T0, with resources held indefinitely — and a detector could spot the cycle and abort one. Livelock is the polite version that avoids that cycle and pays for it: because everything is released each round, there is no cycle, no held resource, no blocked process — nothing the deadlock machinery can even see, let alone fix.

<svg role="img" aria-label="Two panels. Deadlock: T0 and T1 in a cycle, each holding a resource and waiting, resources held, a detector finds the cycle. Livelock: T0 and T1 both released, resources free, retrying, a detector finds nothing." viewBox="0 0 440 140">
<text x="110" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">deadlock</text>
<circle cx="70" cy="55" r="16" fill="var(--panel)" stroke="var(--line)"/><text x="70" y="59" fill="var(--ink)" font-size="8" text-anchor="middle">T0</text>
<circle cx="150" cy="55" r="16" fill="var(--panel)" stroke="var(--line)"/><text x="150" y="59" fill="var(--ink)" font-size="8" text-anchor="middle">T1</text>
<path d="M86 50 L 134 50" fill="none" stroke="var(--s2)"/><path d="M134 62 L 86 62" fill="none" stroke="var(--s2)"/>
<text x="110" y="90" fill="var(--s2)" font-size="8" text-anchor="middle">cycle, held, waiting</text>
<text x="110" y="106" fill="var(--s1)" font-size="8" text-anchor="middle">detector aborts a victim</text>
<text x="330" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">livelock</text>
<circle cx="290" cy="55" r="16" fill="var(--panel)" stroke="var(--line)"/><text x="290" y="59" fill="var(--ink)" font-size="8" text-anchor="middle">T0</text>
<circle cx="370" cy="55" r="16" fill="var(--panel)" stroke="var(--line)"/><text x="370" y="59" fill="var(--ink)" font-size="8" text-anchor="middle">T1</text>
<text x="330" y="90" fill="var(--muted)" font-size="8" text-anchor="middle">both released, free, retrying</text>
<text x="330" y="106" fill="var(--s2)" font-size="8" text-anchor="middle">detector finds no cycle</text>
</svg>
^ Deadlock is a cycle of held-and-waiting a detector can break; livelock releases everything each round, so there is no cycle to find — the safety move against deadlock is exactly what hides livelock.

The root cause is symmetry, and naming it gives the fix. Two identical processes, reacting identically to the identical conflict on the identical schedule, produce an identical next state — a fixed point of the retry loop that never escapes on its own. To break out, something must differ between them, just once. The standard way is asymmetric or randomized backoff: after a conflict, wait a delay that differs between the two (or is random), so their retries land on different rounds. Then one retries alone, finds both resources free, and completes; with it gone, the other completes too.

**Livelock is a symmetric fixed point of the retry loop, so the fix is to break the symmetry — back off by amounts that differ between the actors (by id, or randomly) so their retries desynchronize and one gets through, after which the other does too.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/livelock-inter-01. The fixture is two transactions acquiring the same two resources in opposite order, a round budget, and the backoff policy.

```json filename=modules/orchestration-and-governance/code/livelock-inter-01/livelock.json:3-5 COMPLETE
  "resource_order": {"0": ["A", "B"], "1": ["B", "A"]},
  "max_rounds": 8,
  "asymmetric_backoff": true
```

The backoff rule is the whole difference between the two policies — the same for everyone, or id-dependent.

```python filename=modules/orchestration-and-governance/code/livelock-inter-01/livelock.py:30-33 COMPLETE
def backoff(t, asymmetric):
    """The retry delay after a conflict. Lockstep: the same (0) for everyone -- the tie never breaks.
    Asymmetric: an id-dependent delay, so the two transactions retry on different rounds."""
    return t if asymmetric else 0
```

Each round, the active transactions grab their first resource.

```python filename=modules/orchestration-and-governance/code/livelock-inter-01/livelock.py:36-55 COMPLETE
def simulate(order, max_rounds, asymmetric):
    """Run the two transactions. Each round: all active grab their first resource, then simultaneously
    try their second against a snapshot; a transaction that would get both commits and releases,
    one that conflicts releases its first and backs off. Resources are free between rounds."""
    txns = sorted(int(t) for t in order)
    completed = []
    next_round = {t: 0 for t in txns}
    log = []                                   # (round, holdings-at-round-end, completed-this-round)
    for r in range(max_rounds):
        if len(completed) == len(txns):
            break
        active = [t for t in txns if t not in completed and next_round[t] <= r]
        held = {}                              # resource -> transaction
        # phase 1: each active transaction grabs its first resource if free
        first = {}
        for t in active:
            res0 = order[str(t)][0]
            if res0 not in held:
                held[res0] = t
                first[t] = res0
```

Then they try their second against a snapshot (simultaneously), so a conflict makes both release; only a transaction retrying alone finds its second resource free.

```python filename=modules/orchestration-and-governance/code/livelock-inter-01/livelock.py:56-71 COMPLETE
        # phase 2: decide all outcomes against the post-phase-1 snapshot (simultaneous)
        snapshot = dict(held)                  # what each grabbed before anyone releases
        done_now = []
        for t in active:
            if t not in first:
                continue
            res1 = order[str(t)][1]
            if res1 not in snapshot:           # second resource was free -> commit, then release both
                completed.append(t)
                done_now.append(t)
                del held[first[t]]
            else:                              # conflict: release the first, retry after a backoff
                del held[first[t]]
                next_round[t] = r + 1 + backoff(t, asymmetric)
        log.append((r, list(active), snapshot, list(done_now), dict(held)))
    return {"completed": completed, "rounds_used": len(log), "log": log}
```

Before running it, predict: with the same backoff for both, every round should be a copy of the first, and nothing should complete. Run `--lockstep`:

```text filename=livelock.py --lockstep
LOCKSTEP — both retry on the same schedule
--------------------------------------------------------------------
  round   grabbed (mid-round)     completed   held at round end
  0       A->T0, B->T1            []          (all free)
  1       A->T0, B->T1            []          (all free)
  2       A->T0, B->T1            []          (all free)
  3       A->T0, B->T1            []          (all free)
  4       A->T0, B->T1            []          (all free)
  5       A->T0, B->T1            []          (all free)
  6       A->T0, B->T1            []          (all free)
  7       A->T0, B->T1            []          (all free)
--------------------------------------------------------------------
  completed 0 of 2 transactions in 8 rounds -- no progress; resources freed every round (livelock, not deadlock)
```

The prediction holds exactly. Every round is identical: T0 grabs A, T1 grabs B, both fail their second, both release — the "held at round end" column is all-free every single round. Zero transactions complete across the full eight-round budget, and yet the system is never idle and never stuck: both transactions are active and grabbing in every row. A deadlock detector inspecting the "held at round end" state would find nothing held, no cycle, nothing to abort. This is the signature of livelock — full activity, empty progress, and invisible to the deadlock machinery.

Now flip the backoff to asymmetric. Run `--asymmetric`:

```text filename=livelock.py --asymmetric
ASYMMETRIC — back off by different amounts (by id)
--------------------------------------------------------------------
  round   grabbed (mid-round)     completed   held at round end
  0       A->T0, B->T1            []          (all free)
  1       A->T0                   ['T0']      (all free)
  2       B->T1                   ['T1']      (all free)
--------------------------------------------------------------------
  completed 2 of 2 transactions in 3 rounds -- the tie is broken and both complete
```

Round 0 is the same conflict — both grab, both fail, both release. But now the backoff differs: T0 retries at round 1, T1 not until round 2. So round 1 has T0 alone; it grabs A, finds B free (T1 is waiting), takes it, and completes. Round 2 has T1 alone; it grabs B, finds A free, and completes. Both done in three rounds. The only thing that changed from the lockstep run is that the two transactions stopped retrying in unison — the same grabs, the same conflict, but desynchronized retries, and the fixed point is broken.

<svg role="img" aria-label="Two timelines. Lockstep: every round identical, both transactions retry together, zero completions across the budget. Asymmetric: round 0 conflict, then T0 completes alone at round 1 and T1 at round 2." viewBox="0 0 440 140">
<text x="20" y="16" fill="var(--muted)" font-size="9">lockstep: same round forever</text>
<rect x="30" y="24" width="45" height="16" fill="var(--s2)"/><rect x="80" y="24" width="45" height="16" fill="var(--s2)"/><rect x="130" y="24" width="45" height="16" fill="var(--s2)"/><rect x="180" y="24" width="45" height="16" fill="var(--s2)"/><rect x="230" y="24" width="45" height="16" fill="var(--s2)"/>
<text x="290" y="36" fill="var(--s2)" font-size="8">... 0 done</text>
<text x="20" y="72" fill="var(--muted)" font-size="9">asymmetric: staggered</text>
<rect x="30" y="80" width="45" height="16" fill="var(--s2)"/><text x="52" y="92" fill="var(--ink)" font-size="7" text-anchor="middle">conflict</text>
<rect x="80" y="80" width="45" height="16" fill="var(--s1)"/><text x="102" y="92" fill="var(--ink)" font-size="7" text-anchor="middle">T0 done</text>
<rect x="130" y="80" width="45" height="16" fill="var(--s1)"/><text x="152" y="92" fill="var(--ink)" font-size="7" text-anchor="middle">T1 done</text>
<text x="200" y="92" fill="var(--s1)" font-size="8">both done</text>
<text x="220" y="122" fill="var(--muted)" font-size="8" text-anchor="middle">same conflict; only the retry timing differs</text>
</svg>
^ Lockstep repeats the identical conflict-and-release forever; asymmetric backoff staggers the retries so T0 completes, then T1 — the fix is entirely in the timing, not the grabs.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that lockstep completes zero transactions in the budget, that it keeps both transactions active every round (not blocked), that it holds no resources between rounds (no cycle to detect), that asymmetric completes all transactions, and that asymmetric finishes within the budget.

```python filename=modules/orchestration-and-governance/code/livelock-inter-01/livelock.py:109-121 COMPLETE
    lockstep_no_progress = len(lock["completed"]) == 0
    print("  lockstep completes zero transactions in %d rounds = %s" % (mr, lockstep_no_progress))

    lockstep_stays_active = all(len(active) == n for _, active, _, _, _ in lock["log"])
    print("  lockstep keeps both transactions active every round (not blocked) = %s" % lockstep_stays_active)

    lockstep_never_deadlocks = all(len(endheld) == 0 for _, _, _, _, endheld in lock["log"])
    print("  lockstep holds no resources between rounds (no cycle to detect) = %s" % lockstep_never_deadlocks)

    asymmetric_all_complete = len(asym["completed"]) == n
    print("  asymmetric completes all %d transactions = %s (%s)" % (n, asymmetric_all_complete, ["T%d" % t for t in asym["completed"]]))

    asymmetric_faster = asym["rounds_used"] < mr
    print("  asymmetric finishes within the budget = %s (%d rounds)" % (asymmetric_faster, asym["rounds_used"]))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if lockstep ever made progress or asymmetry ever failed to complete both:

```text filename=livelock.py --check
SELF-TEST — lockstep makes no progress yet never deadlocks (resources always freed); asymmetry breaks the tie and both complete
----------------------------------------------------------------------------------------------------------------
  lockstep completes zero transactions in 8 rounds = True
  lockstep keeps both transactions active every round (not blocked) = True
  lockstep holds no resources between rounds (no cycle to detect) = True
  asymmetric completes all 2 transactions = True (['T0', 'T1'])
  asymmetric finishes within the budget = True (3 rounds)
```

**The self-test asserts both that lockstep makes no progress and that it holds nothing between rounds — pinning the two halves of livelock at once: it is failing (zero completions) and it is not deadlocked (no held resources, no cycle), which is exactly why the deadlock detector would call it healthy.**

## Definition of done

You can define livelock and distinguish it from deadlock and from starvation.
You can explain why the polite release-and-retry that avoids deadlock is exactly what creates livelock.
You can explain why a deadlock detector finds nothing in a livelock (no cycle, nothing held).
You can explain why symmetry is the root cause and why breaking it — asymmetric or randomized backoff — is the fix.
You can predict that identical retry schedules loop forever while desynchronized ones make progress.

## Boss fight

Suppose you fix it with randomized backoff and it works, but under heavy contention throughput still collapses even though no single pair livelocks. Reason about what is happening. Random backoff breaks the exact-repeat symmetry, but if many actors contend for the same resources and all retry within a short window, they keep colliding probabilistically — the system spends most of its effort on retries rather than work, a congestion collapse that looks like livelock in aggregate. The standard escalation is exponential backoff (widen the random window after each successive conflict, so contention thins out as it rises) combined with a cap on attempts, and, better, removing the contention at its source — a consistent global lock ordering so the conflicting pattern never forms, or a lock manager that grants in a fair order. Randomized backoff is the minimal fix for two actors; at scale you need backoff that adapts to the contention level and, ideally, a design that prevents the conflict rather than resolving it repeatedly.

Now the deeper structural fix that dissolves this whole class of bug: order the resource acquisition. The livelock (and the deadlock it was avoiding) both come from the two transactions acquiring A and B in opposite orders. If every actor acquires resources in one global order — always A before B, never B before A — then two transactions contending for both cannot form the cyclic pattern at all: whoever gets A first proceeds to B and finishes, and the other simply waits for A, a plain, progress-making wait. This is why "always acquire locks in a fixed global order" is the standard prevention for both deadlock and livelock, and it is better than any detection or backoff scheme because it removes the possibility rather than recovering from it. Backoff and detection are for when a global order is impossible (locks discovered dynamically, or across systems that do not share an ordering); when you can impose the order, do, and the retries and detectors become unnecessary.

**Randomized backoff fixes two actors but not congestion collapse under heavy contention, which needs exponential backoff with a cap and, better, contention removed at the source; and the structural cure for both livelock and deadlock is a single global lock-acquisition order, which prevents the cyclic pattern from forming rather than recovering from it.**

## External resources

Operating-systems and concurrency texts (for example, Silberschatz's chapters on deadlock, or Tanenbaum) define livelock alongside deadlock and starvation and give the symmetry-breaking and lock-ordering remedies.
The Ethernet/CSMA literature on collision resolution is where exponential backoff with randomization was developed for exactly this contention problem, and it recurs in distributed retry design.
The topic's own modules on detecting deadlock as a cycle and aborting a victim, on priority inheritance, and on priority aging cover the neighboring liveness failures — a cycle of blocked processes, a lock-holder preempted, and low-priority starvation — that livelock is distinct from.
