---
id: holblock-inter-01
title: Don't force unrelated tasks through one FIFO lane — the slow task at the head blocks every quick task behind it
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: Put every task through one first-in-first-out queue served by one worker, and each task's fate is chained to whatever sits ahead of it. If a long task is at the head, the short tasks behind it cannot start until it finishes — their completion times are dominated by a task they have nothing to do with. The item at the head of the line holds up the whole line, so a single slow request inflates the latency of every request queued behind it. This is head-of-line blocking, and it is why one big upload, one slow query, or one stuck message can wreck the latency of a stream of small fast ones sharing the lane. The crucial thing is that it is not a capacity problem: the server is busy the entire time in either ordering, and the total work and throughput are exactly the same. What changes is who waits — under FIFO the many short tasks each pay the long task's duration as pure waiting, while serving the same tasks on the same single server in a different order (shortest first) lets the short tasks finish immediately and only the one long task waits, dropping the mean completion time sharply. HOL blocking is an ordering effect: a strict single FIFO lane couples the latency of unrelated tasks, and the cure is to stop forcing them through one head-blocked lane. On a fixture of four tasks with a slow one at the head, FIFO gives a mean completion of 11.5 while shortest-first gives 4.75 — at identical total work.
eli5: Imagine a single checkout line at a shop. The person at the front has a cart piled high with a hundred items, and behind them are three people each holding a single candy bar. Everyone has to wait for the giant cart to be rung up before the three quick shoppers can pay — even though their purchases take five seconds each. The line isn't slow because the cashier is lazy or because there's too much stuff overall; it's slow because one big order is stuck at the front, blocking everyone. If you let the three quick shoppers go first (or open a second lane for them), they're done in seconds and only the big cart waits — the same cashier, the same total work, but almost everyone gets out faster. Computers queue up work the same way, and one slow job at the head of a single line can make a crowd of fast jobs crawl.
---

## Why this module

Queues are everywhere in a system — a thread pool's work queue, a connection's request pipeline, a message broker's partition, a network switch's port. The default and most natural discipline for all of them is first-in-first-out: serve requests in the order they arrived, which feels fair and is trivially simple. FIFO is fine as long as the tasks are all roughly the same size. It becomes a trap the moment they are not.

The trap is that FIFO makes latency contagious. Because a task cannot start until every task ahead of it has finished, one slow task at the head of the queue imposes its entire duration on everyone behind it. Those waiting tasks may be tiny, unrelated, and individually fast, but their latency is now set by a stranger at the front of the line. A single heavy request turns a queue of quick requests into a queue of slow ones.

What makes this so easy to misdiagnose is that nothing is overloaded. The worker is not idle, no capacity is wasted, throughput is unchanged — the system is doing exactly as much work as it always did. The damage is entirely in the ordering, which means you cannot fix it by adding capacity or shedding load; you fix it by not chaining unrelated tasks together in one lane. This module serves the same tasks two ways on one worker and measures the latency difference.

**A single FIFO lane chains every task's latency to the one ahead of it, so a slow task at the head blocks the quick tasks behind it — and because throughput is unchanged, the damage is pure ordering, not capacity.**

## Concepts

The metric that exposes head-of-line blocking is mean completion time, not throughput. Throughput — total work over total time — is blind to ordering, because the same jobs finishing in a different order still finish in the same total span. Completion time is per-task and order-sensitive: it counts how long each task waited plus its own service, so it captures the waiting that FIFO inflicts and throughput hides. Watching only throughput, you would see nothing wrong.

The reason reordering helps is a scheduling fact worth stating plainly: to minimize mean completion time on one server, serve the shortest task first. Every task that finishes contributes its completion time to the mean, and finishing the quick tasks early gets many small numbers out of the way before the one large number, whereas FIFO with a long head does the opposite. This is why shortest-job-first is optimal for mean latency, and why a long task at the head is the worst case.

But the deeper point is not "use shortest-job-first" — it is that HOL blocking comes from forcing unrelated tasks to share one strictly-ordered lane. Any cure that breaks that coupling works: separate lanes by task class or size, a dedicated lane for big tasks, or allowing out-of-order completion so a finished small task need not wait for a stuck large one. The classic systems examples — network switch ports, HTTP/1.1 pipelining, TCP's in-order delivery — all suffer HOL blocking, and their successors (virtual output queues, HTTP/2 and HTTP/3) all cure it by removing the single shared ordered lane.

<svg role="img" aria-label="One shared FIFO lane with a big task blocking small ones behind it, versus two separate lanes where the big task has its own lane and the small tasks flow freely" viewBox="0 0 440 140">
<text x="110" y="18" fill="var(--ink)" font-size="10" text-anchor="middle">one shared lane</text>
<rect x="40" y="30" width="70" height="20" fill="var(--s2)" stroke="var(--line)"/>
<text x="75" y="44" fill="var(--ink)" font-size="9" text-anchor="middle">big</text>
<rect x="110" y="30" width="20" height="20" fill="var(--s1)" stroke="var(--line)"/>
<rect x="130" y="30" width="20" height="20" fill="var(--s1)" stroke="var(--line)"/>
<rect x="150" y="30" width="20" height="20" fill="var(--s1)" stroke="var(--line)"/>
<text x="110" y="66" fill="var(--s2)" font-size="9" text-anchor="middle">small tasks blocked</text>
<text x="330" y="18" fill="var(--ink)" font-size="10" text-anchor="middle">separate lanes</text>
<rect x="250" y="30" width="70" height="20" fill="var(--s2)" stroke="var(--line)"/>
<text x="285" y="44" fill="var(--ink)" font-size="9" text-anchor="middle">big</text>
<rect x="250" y="86" width="20" height="20" fill="var(--s1)" stroke="var(--line)"/>
<rect x="272" y="86" width="20" height="20" fill="var(--s1)" stroke="var(--line)"/>
<rect x="294" y="86" width="20" height="20" fill="var(--s1)" stroke="var(--line)"/>
<text x="330" y="122" fill="var(--s1)" font-size="9" text-anchor="middle">small tasks flow freely</text>
</svg>
^ The cure is to uncouple the lanes: give the big task its own lane so the small tasks are never trapped behind it.

**Throughput hides HOL blocking and mean completion time reveals it; shortest-first is optimal for that mean, but the general cure is to stop coupling unrelated tasks in one strictly-ordered lane.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/holblock-inter-01. The fixture is a batch of tasks queued at once, with a slow one at the head and three quick ones behind it.

```json filename=modules/orchestration-and-governance/code/holblock-inter-01/holblock.json:3-3 COMPLETE
  "service_times": [10, 1, 1, 1]
```

Completion time is computed by serving tasks one at a time in the given order, all present from the start.

```python filename=modules/orchestration-and-governance/code/holblock-inter-01/holblock.py:32-39 COMPLETE
def completions(order):
    """Completion time of each task when served one at a time in the given order (all present at t=0)."""
    t = 0
    out = []
    for s in order:
        t += s
        out.append(t)
    return out
```

The mean of those completion times is the number that measures the blocking.

```python filename=modules/orchestration-and-governance/code/holblock-inter-01/holblock.py:42-43 COMPLETE
def mean(xs):
    return sum(xs) / len(xs)
```

Before running it, predict: under FIFO the three quick tasks all finish after the slow head, so the mean is high; shortest-first frees them and the mean drops. Run `--complete`:

```text filename=holblock.py --complete
COMPLETE — completion time per task (one server, all queued at t=0)
------------------------------------------------------------
  order          service times      completions          mean
  FIFO           [10, 1, 1, 1]      [10, 11, 12, 13]     11.50
  shortest-first [1, 1, 1, 10]      [1, 2, 3, 13]        4.75
```

The prediction holds. Under FIFO the quick tasks complete at 11, 12, and 13 — each dragging the head's 10 units behind it — for a mean of 11.5. Shortest-first finishes them at 1, 2, and 3, and the mean falls to 4.75. The last task still completes at 13 either way, so the total span is unchanged; only the mean moved.

<svg role="img" aria-label="Two timelines on one server: FIFO runs the 10-unit task first then three 1-unit tasks completing at 11 12 13; shortest-first runs the three 1-unit tasks first completing at 1 2 3 then the 10-unit task at 13" viewBox="0 0 440 160">
<text x="20" y="35" fill="var(--muted)" font-size="9">FIFO</text>
<rect x="60" y="24" width="260" height="18" fill="var(--s2)" stroke="var(--line)"/>
<text x="190" y="37" fill="var(--ink)" font-size="9" text-anchor="middle">slow (10)</text>
<rect x="320" y="24" width="26" height="18" fill="var(--s1)" stroke="var(--line)"/>
<rect x="346" y="24" width="26" height="18" fill="var(--s1)" stroke="var(--line)"/>
<rect x="372" y="24" width="26" height="18" fill="var(--s1)" stroke="var(--line)"/>
<text x="360" y="58" fill="var(--s2)" font-size="9" text-anchor="middle">quick tasks wait to 11,12,13</text>
<text x="20" y="105" fill="var(--muted)" font-size="9">SJF</text>
<rect x="60" y="94" width="26" height="18" fill="var(--s1)" stroke="var(--line)"/>
<rect x="86" y="94" width="26" height="18" fill="var(--s1)" stroke="var(--line)"/>
<rect x="112" y="94" width="26" height="18" fill="var(--s1)" stroke="var(--line)"/>
<text x="99" y="128" fill="var(--s1)" font-size="9" text-anchor="middle">done at 1,2,3</text>
<rect x="138" y="94" width="260" height="18" fill="var(--s2)" stroke="var(--line)"/>
<text x="268" y="107" fill="var(--ink)" font-size="9" text-anchor="middle">slow (10)</text>
<text x="220" y="150" fill="var(--muted)" font-size="9" text-anchor="middle">same server, same span to 13 -- only the order and the mean differ</text>
</svg>
^ The same four tasks on one server: FIFO traps the quick tasks behind the slow head, shortest-first lets them out first, and the span to 13 is identical.

Now see the waiting FIFO imposes, task by task. Run `--waste`:

```text filename=holblock.py --waste
WASTE — for FIFO, how much of each task's completion is waiting behind the head (10)
----------------------------------------------------------
  task   service   completion   own service   waited
  t      10        10           10            0
  t      1         11           1             10
  t      1         12           1             11
  t      1         13           1             12
----------------------------------------------------------
  every task after the head inherits the head's duration as pure waiting
```

Each quick task does one unit of its own work but waits ten or more — almost all of its completion time is pure blocking behind the head. That waiting is the head-of-line penalty, and it is entirely manufactured by the choice to serve one strict FIFO lane.

<svg role="img" aria-label="For each quick FIFO task, a bar split into a large waiting portion of about ten units and a tiny own-work portion of one unit" viewBox="0 0 440 140">
<text x="220" y="16" fill="var(--muted)" font-size="10" text-anchor="middle">each quick task: mostly waiting, barely any own work</text>
<rect x="40" y="34" width="200" height="18" fill="var(--s2)" stroke="var(--line)"/>
<rect x="240" y="34" width="20" height="18" fill="var(--s1)" stroke="var(--line)"/>
<text x="300" y="47" fill="var(--muted)" font-size="9">wait 10 + work 1</text>
<rect x="40" y="60" width="220" height="18" fill="var(--s2)" stroke="var(--line)"/>
<rect x="260" y="60" width="20" height="18" fill="var(--s1)" stroke="var(--line)"/>
<text x="320" y="73" fill="var(--muted)" font-size="9">wait 11 + work 1</text>
<rect x="40" y="86" width="240" height="18" fill="var(--s2)" stroke="var(--line)"/>
<rect x="280" y="86" width="20" height="18" fill="var(--s1)" stroke="var(--line)"/>
<text x="340" y="99" fill="var(--muted)" font-size="9">wait 12 + work 1</text>
<text x="150" y="126" fill="var(--s2)" font-size="9" text-anchor="middle">waiting (behind the head)</text>
<text x="320" y="126" fill="var(--s1)" font-size="9" text-anchor="middle">own work</text>
</svg>
^ For each blocked task the waiting dwarfs its own one unit of work — the penalty is the head task's duration, not anything the task did.

## Build

The self-test plants the failure and names each claim as a boolean flag. It first serves the tasks both ways and computes each order's completions and mean.

```python filename=modules/orchestration-and-governance/code/holblock-inter-01/holblock.py:78-82 COMPLETE
    fifo = st
    sjf = sorted(st)

    cf, cs = completions(fifo), completions(sjf)
    mf, ms = mean(cf), mean(cs)
```

It then checks that the head is the slowest, that every FIFO task after the head finishes no sooner than the head does, that reordering lowers the mean, and that total work and makespan are identical — so the change is pure ordering.

```python filename=modules/orchestration-and-governance/code/holblock-inter-01/holblock.py:84-93 COMPLETE
    head_is_slowest = st[0] == max(st)
    print("  the head task is the slowest in the queue = %s (%d)" % (head_is_slowest, st[0]))

    quick_tasks_blocked = all(c >= st[0] for c in cf[1:])
    print("  under FIFO every task after the head finishes no sooner than the head = %s" % quick_tasks_blocked)

    reorder_lowers_mean = ms < mf
    print("  shortest-first has a lower mean completion than FIFO = %s (%.2f < %.2f)" % (reorder_lowers_mean, ms, mf))

    same_total_work = sum(fifo) == sum(sjf) and max(cf) == max(cs)
    print("  total work and makespan are identical either way = %s (%d)" % (same_total_work, sum(fifo)))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if reordering ever stops helping or secretly changes the total work:

```text filename=holblock.py --check
SELF-TEST — FIFO's head task blocks the queue and inflates mean completion; reordering lowers it at equal total work
------------------------------------------------------------------------------------------------------------------------
  the head task is the slowest in the queue = True (10)
  under FIFO every task after the head finishes no sooner than the head = True
  shortest-first has a lower mean completion than FIFO = True (4.75 < 11.50)
  total work and makespan are identical either way = True (13)
  so the latency change is pure ordering, not capacity = True
------------------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  head_is_slowest=True  quick_tasks_blocked=True  reorder_lowers_mean=True  same_total_work=True  ordering_effect=True
```

**The self-test pins total work and makespan as equal while the mean drops — which is what proves the win is ordering, not extra capacity, and rules out a fix that secretly did less work.**

## Definition of done

You can explain why FIFO makes latency contagious — a task cannot start until every task ahead of it finishes.
You can say why throughput is blind to head-of-line blocking and why mean completion time reveals it.
You can state that shortest-job-first minimizes mean completion time on one server, and why finishing small tasks early helps.
You can name the general cure — break the single ordered lane (separate lanes by class, a dedicated lane for big tasks, or out-of-order completion) — and give a real systems example.
You can distinguish HOL blocking from a capacity problem, and explain why adding workers or shedding load does not address the ordering.

## Boss fight

Shortest-first fixes the mean, but reason about its cost: make the head task depend on the queue never starving it. If short tasks keep arriving, a strict shortest-first policy serves them forever and the one long task waits indefinitely — starvation, the exact failure the topic's priority-aging module addresses. So the naive cure for HOL blocking can create a starvation bug. The robust answer is usually not pure shortest-first but separate lanes: give big tasks their own lane so they neither block the small ones nor get starved by them. The lesson tightens: the goal is to decouple the lanes, and shortest-first is only one way to do that, with its own hazard.

Now consider where you cannot reorder at all. TCP delivers bytes strictly in order, so if one segment is lost, every segment that arrived after it waits in the buffer until the lost one is retransmitted — head-of-line blocking you cannot schedule your way out of, because the ordering is a correctness requirement, not a policy. This is why HTTP/2, which multiplexed many streams over one ordered TCP connection, still suffered HOL blocking at the transport layer, and why HTTP/3 moved to QUIC, where independent streams can make progress past one another. When in-order delivery is mandatory, the only cure is more independent lanes underneath.

**Shortest-first cures the mean but can starve the long task, so separate lanes are the robust fix; and where ordering is a correctness requirement (in-order transport), you cannot schedule around HOL blocking at all — you need independent lanes beneath it.**

## External resources

The Wikipedia entry on head-of-line blocking surveys the phenomenon across network switches, HTTP, and transport protocols in one place.
The HTTP/3 and QUIC design documents explain precisely how one lost packet caused transport-level HOL blocking under HTTP/2-over-TCP and how independent streams remove it.
The topic's own modules on priority aging and on bulkheads cover the adjacent concerns — starving low-priority work, and isolating resources per dependency — that a lane-separation fix has to respect.
