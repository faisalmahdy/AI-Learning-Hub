---
id: priorityinv-inter-01
title: Let a lock-holder inherit its waiter's priority — otherwise a medium task preempts the low-priority holder and blocks the high-priority one behind it
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: A preemptive scheduler runs the highest-priority runnable task at every instant, which is exactly right until a shared lock is involved. If a low-priority task L holds a lock that a high-priority task H needs, H must wait for L to release it — an unavoidable, bounded wait, as long as L's critical section. The pathology comes from an unrelated third task: a medium-priority task M that needs no lock becomes runnable while L holds the lock, and because M outranks L the scheduler preempts L to run M — so L cannot make progress, cannot release the lock, and H (which outranks M) is stuck behind M for as long as M runs. A high-priority task has been delayed by a lower-priority one it has no dependency on, and the delay is unbounded: any number of medium tasks can keep preempting L. This is priority inversion, and it famously nearly killed the Mars Pathfinder mission. Priority inheritance fixes it with a small rule: while L holds a lock that a higher-priority task is blocked on, L temporarily inherits that waiter's priority, so M can no longer preempt it; L runs its critical section to completion, releases the lock, drops back to its own priority, and H proceeds. On a fixture where H (priority 3) needs a lock held by L (priority 1) and M (priority 2) needs no lock, no-inheritance scheduling makes M preempt L and H waits 16 ticks, while priority inheritance blocks M and H waits 6 — the 10-tick difference is exactly M's work, time H should never have lost.
eli5: Imagine you're at a copy machine and a slow person (low priority) is using it while an important person (high priority) waits their turn. That's a fair wait. But then a bunch of medium-important people who DON'T need the copy machine keep pulling the slow person away to help with other errands, so the slow person never finishes copying, and the important person is stuck waiting — not because of the copying, but because everyone keeps borrowing the slow helper. The fix: while the important person is waiting on the slow person, treat the slow person as important too, so nobody is allowed to pull them away. They finish copying fast, and the important person gets their turn. The waiting should only be for the copy itself, never for unrelated errands.
---

## Why this module

Priority scheduling has a clean promise: the most important runnable work runs first. Locks quietly break that promise, and the way they break it is counterintuitive enough that it has caused real, famous failures. The direct effect of a lock is easy to accept — if a high-priority task needs something a low-priority task is holding, it waits, and that wait is bounded by how long the holder keeps the lock. You can budget for it.

The trouble is the indirect effect, which involves a task that has nothing to do with the lock. A medium-priority task, needing no lock, is still runnable, and to the scheduler it simply outranks the low-priority lock-holder — so it preempts it. Now the low-priority task is frozen mid-critical-section, the lock stays held, and the high-priority task waits not for the lock's work but for the medium task's work, even though the high-priority task outranks the medium one. The priority order has been inverted: a lower-priority task effectively delays a higher-priority one, and with several medium tasks the delay has no bound at all.

Priority inheritance is the standard fix, and it is local and cheap. This module simulates the three tasks under plain priority scheduling and under priority inheritance, and measures how long the high-priority task waits.

**A lock lets a medium-priority task preempt a low-priority holder and thereby block a high-priority waiter for an unbounded time — priority inheritance has the holder inherit the waiter's priority so it cannot be preempted, bounding the wait to the critical section the high-priority task actually depends on.**

## Concepts

The fixture is three tasks: low-priority L holds the lock, high-priority H needs it, and medium-priority M needs no lock and arrives while L is holding.

```json filename=modules/orchestration-and-governance/code/priorityinv-inter-01/priorityinv.json:3-7 COMPLETE
  "tasks": {
    "L": {"priority": 1, "arrive": 0, "work": 8, "needs_lock": true},
    "H": {"priority": 3, "arrive": 2, "work": 4, "needs_lock": true},
    "M": {"priority": 2, "arrive": 3, "work": 10, "needs_lock": false}
  }
```

The scheduler is preemptive priority with one lock. The key line is the effective priority: normally a task's own priority, but under inheritance a lock-holder is boosted to the highest priority among the tasks waiting on its lock.

```python filename=modules/orchestration-and-governance/code/priorityinv-inter-01/priorityinv.py:32-58 COMPLETE
def simulate(tasks, inherit, horizon=200):
    """Preemptive priority scheduling with one shared lock. Returns (H_acquire_time, trace of runner per tick)."""
    rem = {k: v["work"] for k, v in tasks.items()}
    done, waiting = set(), []
    lock_holder = None
    h_acquire = None
    trace = []
    for t in range(horizon):
        if len(done) == len(tasks):
            break
        runnable = []
        for k, v in tasks.items():
            if k in done or t < v["arrive"]:
                continue
            if v["needs_lock"]:
                if lock_holder == k or lock_holder is None:
                    runnable.append(k)
                elif k not in waiting:
                    waiting.append(k)          # blocked on the lock
            else:
                runnable.append(k)

        def effective_priority(k):
            p = tasks[k]["priority"]
            if inherit and lock_holder == k and waiting:
                p = max(p, max(tasks[w]["priority"] for w in waiting))
            return p
```

Without inheritance, `effective_priority` returns the task's own priority, so M (2) outranks L (1) and preempts it. With inheritance, once H (3) is waiting on L's lock, L's effective priority becomes 3, and M can no longer preempt it.

<svg role="img" aria-label="Timelines: without inheritance L runs then M preempts it, delaying the lock release and H; with inheritance L runs through to release the lock and H runs before M" viewBox="0 0 320 140">
  <text x="10" y="12" font-size="8" fill="var(--muted)">who runs each tick (L holds the lock; H needs it; M needs no lock)</text>
  <text x="14" y="34" font-size="7.5" fill="var(--s2)">no inherit</text>
  <g font-size="6.5">
  <rect x="66" y="26" width="30" height="12" fill="var(--s1)"/><text x="72" y="35" fill="var(--panel)">L (lock)</text>
  <rect x="96" y="26" width="100" height="12" fill="var(--s2)"/><text x="128" y="35" fill="var(--panel)">M preempts L</text>
  <rect x="196" y="26" width="50" height="12" fill="var(--s1)"/><text x="205" y="35" fill="var(--panel)">L finishes</text>
  <rect x="246" y="26" width="40" height="12" fill="var(--ink)"/><text x="252" y="35" fill="var(--panel)">H (t=18)</text>
  </g>
  <text x="14" y="60" font-size="7.5" fill="var(--s1)">inherit</text>
  <g font-size="6.5">
  <rect x="66" y="52" width="80" height="12" fill="var(--s1)"/><text x="86" y="61" fill="var(--panel)">L (boosted, lock)</text>
  <rect x="146" y="52" width="40" height="12" fill="var(--ink)"/><text x="152" y="61" fill="var(--panel)">H (t=8)</text>
  <rect x="186" y="52" width="100" height="12" fill="var(--s2)"/><text x="228" y="61" fill="var(--panel)">M runs last</text>
  </g>
  <text x="14" y="86" font-size="7.5" fill="var(--ink)">no inherit: H waits behind M (16 ticks); inherit: H waits only for L's lock (6)</text>
  <text x="14" y="106" font-size="7.5" fill="var(--muted)">inheritance stops M from preempting the lock-holder</text>
</svg>
^ Without inheritance, M preempts L mid-critical-section, so the lock releases late and H runs at t=18. With inheritance, L is boosted to H's priority, runs through, releases the lock, and H runs at t=8 — before M. The medium task no longer sits between the high task and its lock.

**The only change is the effective priority of the lock-holder: own priority (M can preempt) versus the waiter's inherited priority (M cannot) — that single rule decides whether the inversion happens.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the lock-and-scheduler interaction of a task runner, reduced to three tasks so every tick is checkable by hand.

Run `--schedule` to see who runs each tick under both policies.

```text filename=priorityinv.py --schedule
  tick:       0 1 2 3 4 5 6 7 8 9101112131415161718192021
  no-inherit  L L L M M M M M M M M M M L L L L L H H H H
  inherit     L L L L L L L L H H H H M M M M M M M M M M
```

Follow the no-inherit row. L holds the lock and runs ticks 0–2; H arrives at tick 2 and blocks. M arrives at tick 3 and, outranking L, preempts it — M runs ticks 3–12, its full 10 units, while L is frozen holding the lock. Only at tick 13 does L resume, finishing its critical section at tick 17 and releasing the lock, so H finally runs at tick 18. In the inherit row, H blocks at tick 2, L inherits priority 3, and when M arrives at tick 3 it cannot preempt the boosted L. L runs straight through to tick 7, releases, and H runs at tick 8 — M runs afterward, ticks 12 onward. The two schedules order the same work oppositely.

Now `--wait` runs both simulations and reads off when H acquires the lock.

```python filename=modules/orchestration-and-governance/code/priorityinv-inter-01/priorityinv.py:97-98 COMPLETE
    hn, _ = simulate(tasks, inherit=False)
    hi, _ = simulate(tasks, inherit=True)
```

The two acquisition times are ten ticks apart.

```text filename=priorityinv.py --wait
  no-inheritance:  H acquires at t=18, wait 16
  inheritance:     H acquires at t=8, wait 6
  inversion cost (extra wait)       = 10  (= M's work 10)
```

Without inheritance H waits 16 ticks for a lock whose critical section is only 6 ticks of L's remaining work; with inheritance it waits 6. The extra 10 ticks are exactly M's work — a task lower in priority than H, which under a correct priority order should never have run before H got what it needed. That is the inversion made numeric: the high-priority task paid the full cost of an unrelated medium-priority task, and inheritance refunds precisely that amount.

<svg role="img" aria-label="H's wait: 16 ticks without inheritance versus 6 with it, the 10-tick difference labeled as the medium task's work" viewBox="0 0 320 110">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">H's wait for the lock (critical section is 6 ticks)</text>
  <text x="10" y="42" font-size="8.5" fill="var(--s2)">no inherit</text>
  <rect x="80" y="32" width="160" height="16" fill="var(--s1)"/><rect x="140" y="32" width="100" height="16" fill="var(--s2)"/><text x="244" y="44" font-size="8" fill="var(--ink)">16</text>
  <text x="150" y="28" font-size="6.5" fill="var(--s2)">+10 = M's work</text>
  <text x="10" y="72" font-size="8.5" fill="var(--s1)">inherit</text>
  <rect x="80" y="62" width="60" height="16" fill="var(--s1)"/><text x="146" y="74" font-size="8" fill="var(--ink)">6 (just the critical section)</text>
  <text x="10" y="98" font-size="7.5" fill="var(--muted)">the extra wait is exactly the unrelated medium task's work</text>
</svg>
^ H waits 16 ticks without inheritance and 6 with it. The 6 ticks are the critical section H genuinely depends on; the extra 10 are M's work, which inheritance removes from H's wait entirely.

**H waits 16 ticks without inheritance but only 6 with it, and the 10-tick gap equals M's work exactly — the high-priority task was paying for an unrelated lower-priority task, and inheritance refunds that cost.**

## Build

The self-test establishes the setup and the inversion: H is the highest-priority task, yet without inheritance the medium task M runs while H is still waiting.

```python filename=modules/orchestration-and-governance/code/priorityinv-inter-01/priorityinv.py:118-125 COMPLETE
    h_is_highest = tasks["H"]["priority"] == max(t["priority"] for t in tasks.values())
    print("  H is the highest-priority task = %s" % h_is_highest)

    m_runs_before_release_noinherit = any(who == "M" and t < hn for t, who in tn)
    print("  without inheritance the medium task M runs while H waits = %s" % m_runs_before_release_noinherit)

    m_blocked_under_inherit = all(not (who == "M" and t < hi) for t, who in ti)
    print("  with inheritance M does NOT run before H acquires the lock = %s" % m_blocked_under_inherit)
```

Then the fix: inheritance reduces H's wait, and by exactly the medium task's work — showing the removed cost was precisely the inversion.

```python filename=modules/orchestration-and-governance/code/priorityinv-inter-01/priorityinv.py:127-130 COMPLETE
    inheritance_reduces_wait = wait_i < wait_n
    print("  inheritance reduces H's wait = %s (%d < %d)" % (inheritance_reduces_wait, wait_i, wait_n))

    cost_equals_medium_work = (wait_n - wait_i) == tasks["M"]["work"]
    print("  the extra wait equals the medium task's work = %s (%d == %d)" % (cost_equals_medium_work, wait_n - wait_i, tasks["M"]["work"]))
```

Running the check confirms every clause.

```text filename=priorityinv.py --check
  H is the highest-priority task = True
  without inheritance the medium task M runs while H waits = True
  with inheritance M does NOT run before H acquires the lock = True
  inheritance reduces H's wait = True (6 < 16)
  the extra wait equals the medium task's work = True (10 == 10)
```

**The check ties H's extra wait to the medium task running ahead of it, and shows inheritance blocking M and refunding exactly that work — the inversion identified by the lower-priority task delaying the higher one, and removed.**

## Definition of done

Done means the medium task delays the high-priority task without inheritance and is blocked by it with inheritance, reducing H's wait by exactly the medium task's work. That the removed cost equals M's work is the precise fingerprint of priority inversion: H's wait separates into the critical section it truly depends on (unavoidable) plus the unrelated medium work (the inversion), and inheritance removes only the second.

Two clarifications place this in real systems. First, priority inheritance is not the only remedy and each has tradeoffs: the priority ceiling protocol raises any lock-holder to a precomputed ceiling priority (the highest of any task that can take the lock) the moment it acquires, which also prevents inversion and additionally avoids deadlock, at the cost of needing the ceilings known in advance; simply disabling preemption while holding a lock works for very short critical sections but blocks even genuinely higher-priority unrelated work. Inheritance is the common general-purpose choice because it boosts only when a higher-priority task actually blocks, and only to the level needed. Second, this is a real-world hazard, not a textbook curiosity: the Mars Pathfinder lander suffered repeated system resets in 1997 caused by exactly this — a high-priority task blocked on a mutex held by a low-priority task that a medium-priority task kept preempting, tripping a watchdog — and the fix deployed to the spacecraft was to enable priority inheritance on that mutex. The general lesson for any priority-scheduled system with shared locks (real-time schedulers, thread pools with priorities, prioritized task queues) is that a lock couples the priorities of everything that touches it, so a lock-holder must be protected from preemption by tasks that outrank it but not its waiter.

<svg role="img" aria-label="Three remedies for priority inversion: priority inheritance boosts on block to the waiter's level, priority ceiling boosts on acquire to a precomputed ceiling, disabling preemption blocks all others during the critical section" viewBox="0 0 320 120">
  <rect x="10" y="22" width="98" height="42" fill="none" stroke="var(--s1)"/>
  <text x="17" y="36" font-size="7" fill="var(--s1)">inheritance</text>
  <text x="17" y="47" font-size="6.5" fill="var(--ink)">boost on block,</text>
  <text x="17" y="56" font-size="6.5" fill="var(--ink)">to waiter's level</text>
  <rect x="112" y="22" width="98" height="42" fill="none" stroke="var(--s2)"/>
  <text x="119" y="36" font-size="7" fill="var(--s2)">priority ceiling</text>
  <text x="119" y="47" font-size="6.5" fill="var(--ink)">boost on acquire,</text>
  <text x="119" y="56" font-size="6.5" fill="var(--ink)">to precomputed max</text>
  <rect x="214" y="22" width="96" height="42" fill="none" stroke="var(--muted)"/>
  <text x="221" y="36" font-size="7" fill="var(--muted)">no preemption</text>
  <text x="221" y="47" font-size="6.5" fill="var(--ink)">blocks everyone;</text>
  <text x="221" y="56" font-size="6.5" fill="var(--ink)">short sections only</text>
  <text x="10" y="84" font-size="7.5" fill="var(--muted)">a lock couples the priorities of everything that touches it</text>
  <text x="10" y="104" font-size="7.5" fill="var(--ink)">Mars Pathfinder's 1997 resets were this bug; the fix was inheritance on the mutex</text>
</svg>
^ Three remedies for the same coupling: inheritance boosts the holder to its waiter's priority on block, the priority ceiling boosts to a precomputed maximum on acquire (and avoids deadlock), and disabling preemption blocks everyone (only viable for very short sections). All protect the lock-holder from being preempted by a task that outranks it but not its waiter.

**Done means the medium task delays H without inheritance and is blocked with it, cutting H's wait by exactly the medium task's work — the general rule being that a shared lock couples the priorities of everything touching it, so the holder must inherit (or be ceiling-raised to) its waiter's priority.**

## Boss fight

An embedded controller runs tasks under a preemptive priority scheduler. A critical high-priority task occasionally misses its deadline, and the watchdog resets the system. Logs show the high-priority task was ready but not running, while a medium-priority task unrelated to it was executing, and a low-priority task held a mutex the high-priority task needed. The mutex code is correct and the critical sections are short. What is happening, and how do you fix it?

This is priority inversion. The high-priority task needs a mutex held by the low-priority task, so it blocks — a bounded, expected wait for the short critical section. But the medium-priority task, which does not need the mutex, is runnable and outranks the low-priority holder, so the scheduler preempts the holder to run the medium task. While the medium task runs, the low-priority task cannot proceed to release the mutex, so the high-priority task stays blocked far longer than the critical section — long enough to miss its deadline and trip the watchdog. The logs match exactly: the high-priority task is ready but not running, a medium task unrelated to the mutex is executing, and the mutex is held by the low-priority task. The critical section being short is a red herring; the delay is the medium task's runtime, not the critical section's, and it is unbounded in the number and length of medium tasks. The fix is to enable priority inheritance on that mutex: while the low-priority task holds a mutex a higher-priority task is blocked on, it inherits the waiter's priority, so the medium task can no longer preempt it, the critical section completes promptly, the mutex is released, and the high-priority task meets its deadline. This is precisely the bug and fix from the Mars Pathfinder mission in 1997. If the set of tasks that can take each lock is known ahead of time, the priority ceiling protocol is an alternative that also prevents deadlock; for extremely short critical sections, briefly disabling preemption is a cruder option. The durable lesson: any priority-scheduled system with shared locks must protect a lock-holder from preemption by tasks that outrank it but not its blocked waiter, because a lock couples their priorities.

## External resources

The Mars Pathfinder priority-inversion case study (Glenn Reeves's account of the 1997 resets and the priority-inheritance fix) — the canonical real-world instance of this bug and how it was diagnosed and corrected on a live spacecraft.

Real-time systems references on priority inversion and its remedies (the priority inheritance protocol and the priority ceiling protocol, as in Liu's or Buttazzo's real-time scheduling texts, and RTOS mutex documentation) — the formal protocols, their bounds on blocking time, and the deadlock-avoidance property of the ceiling protocol.
