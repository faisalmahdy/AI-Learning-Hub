---
id: worksteal-inter-01
title: Balance uneven work by letting idle workers steal queued tasks — a static round-robin split by count overloads the worker that draws the heavy tasks
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: The intuitive way to give N tasks to K workers is to deal them out round-robin — task i to worker i modulo K — so each worker gets the same number of tasks. That is balanced only if every task takes the same time. When durations vary, equal counts are not equal work: the worker that happens to draw the long tasks has a large total and finishes late, while the workers that drew only short tasks finish early and sit idle even though the schedule as a whole is not done. The makespan — the time until the last worker finishes — is set by the single overloaded worker, and the idle time on the others is pure waste. Work stealing removes the up-front commitment: each worker drains its own queue, but when it empties it steals a task from the back of the most-loaded worker's queue, so work migrates from busy workers to idle ones on demand and no worker stops while queued work remains. This is the discipline behind Cilk, Java's fork/join pool, Go's scheduler, and Rust's Rayon. On a fixture of eight tasks with two large ones that round-robin hands to the same worker, the static split gives loads 22 and 4 (makespan 22, 18 units of idle) while work stealing gives 11 and 15 (makespan 15, 4 idle) — a large step toward the ideal of 13, though a coarse steal that grabs a big task late does not reach it exactly.
eli5: Imagine two checkout lanes and you split the shoppers by just alternating them left, right, left, right. If it happened that both shoppers with enormous overflowing carts went to the left lane, that cashier is stuck for ages while the right cashier scans a few small baskets and then stands there with nothing to do — even though there is still a huge line's worth of work, it is all trapped in the other lane. The smarter rule: when a cashier runs out of customers, they wave over someone from the back of the busy lane. Work slides from the swamped lane to the free one until both finish around the same time. Splitting people up front by counting them ignores how full their carts are; letting the free cashier grab work keeps nobody standing idle next to a backlog.
---

## Why this module

Handing a pile of tasks to a pool of workers looks like a problem you solve once, at the start: divide the tasks among the workers and let them run. The natural division is round-robin — first task to the first worker, second to the second, wrapping around — because it gives every worker the same number of tasks, and equal counts feel like the definition of fair.

Equal counts are fair only when the tasks are interchangeable in cost. They rarely are. One request hits a cache and returns in a millisecond; the next misses and runs for a second. One document is a paragraph; the next is a book. When durations vary, dealing out equal counts says nothing about equal work, and the split that looked balanced can drop almost all the heavy tasks on one worker purely by where they fell in the deal.

The result is a schedule whose finish time is hostage to one worker. The overloaded worker grinds through its heavy pile while the others, having finished their light piles, sit idle — not because there is no work left, but because the remaining work is committed to a worker who cannot get to it yet. The total time is set by the unluckiest worker, and every idle second on the others is capacity you paid for and threw away.

<svg role="img" aria-label="Two worker timelines under a static round-robin split. Worker 0 has a long bar reaching 22 made of two large blocks and small ones; worker 1 has a short bar reaching 4, then a long empty idle stretch to 22." viewBox="0 0 440 150">
<text x="20" y="20" fill="var(--muted)" font-size="9">static round-robin: finish time set by worker 0</text>
<text x="15" y="52" fill="var(--ink)" font-size="9">w0</text>
<rect x="35" y="42" width="150" height="16" fill="var(--s2)"/>
<rect x="185" y="42" width="15" height="16" fill="var(--s1)"/>
<rect x="200" y="42" width="150" height="16" fill="var(--s2)"/>
<rect x="350" y="42" width="45" height="16" fill="var(--s1)"/>
<text x="400" y="54" fill="var(--muted)" font-size="8">22</text>
<text x="15" y="86" fill="var(--ink)" font-size="9">w1</text>
<rect x="35" y="76" width="60" height="16" fill="var(--s1)"/>
<rect x="95" y="76" width="300" height="16" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="3 3"/>
<text x="105" y="88" fill="var(--muted)" font-size="8">idle (18 units) while work remains on w0</text>
<line x1="395" y1="36" x2="395" y2="98" stroke="var(--grid)"/>
<text x="35" y="118" fill="var(--muted)" font-size="8">large task</text>
<rect x="90" y="108" width="12" height="10" fill="var(--s2)"/>
<text x="108" y="117" fill="var(--muted)" font-size="8">small task</text>
<rect x="163" y="108" width="12" height="10" fill="var(--s1)"/>
</svg>
^ Round-robin drops both large tasks on worker 0, which runs to 22, while worker 1 finishes its small tasks at 4 and idles for 18 — the makespan is one worker's bad luck.

**Splitting tasks across workers up front by count assumes equal task sizes; when durations vary, the makespan is set by whichever worker drew the heavy tasks, and the workers that drew light tasks sit idle beside a backlog they cannot reach.**

## Concepts

The fix is to stop committing the whole assignment in advance and let it form as workers become free. Each worker still starts with a local queue, but the rule when a worker empties its queue changes: instead of stopping, it steals a task from another worker that still has a backlog. Work migrates from busy workers to idle ones exactly when and where it is needed, and the invariant becomes simple — no worker is idle while any worker has queued work.

The detail that makes it efficient is which end you steal from. A worker takes its own tasks from the front of its queue, but a thief steals from the back of the victim's queue. The two ends stay apart, so the owner and the thief rarely touch the same task and contend for it — the owner is working at the front while the thief takes from the back. In fork/join workloads the back also holds the oldest, largest-granularity task, so one steal moves a big chunk of work and steals happen rarely.

<svg role="img" aria-label="Two worker deques. Worker 1's deque is empty, so it reaches over and steals a task from the back of worker 0's full deque, while worker 0 keeps taking tasks from the front of its own deque." viewBox="0 0 440 140">
<text x="20" y="20" fill="var(--muted)" font-size="9">idle worker steals from the back of the busy worker's queue</text>
<text x="15" y="55" fill="var(--ink)" font-size="9">w0</text>
<rect x="40" y="42" width="30" height="20" fill="var(--s2)"/>
<rect x="72" y="42" width="30" height="20" fill="var(--s2)"/>
<rect x="104" y="42" width="30" height="20" fill="var(--s2)"/>
<rect x="136" y="42" width="30" height="20" fill="var(--s1)"/>
<text x="55" y="80" fill="var(--muted)" font-size="7" text-anchor="middle">front</text>
<text x="151" y="80" fill="var(--muted)" font-size="7" text-anchor="middle">back</text>
<path d="M40 38 Q 30 30, 30 55" fill="none" stroke="var(--s2)"/>
<text x="20" y="34" fill="var(--s2)" font-size="7">owner takes front</text>
<text x="15" y="112" fill="var(--ink)" font-size="9">w1</text>
<rect x="40" y="99" width="120" height="20" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="3 3"/>
<text x="100" y="113" fill="var(--muted)" font-size="8" text-anchor="middle">empty</text>
<path d="M151 66 Q 200 95, 160 99" fill="none" stroke="var(--s1)"/>
<text x="205" y="88" fill="var(--s1)" font-size="8">thief steals the back task</text>
</svg>
^ The owner pulls from the front of its own deque; an idle worker steals from the back of the busiest deque, so the two ends stay apart and steals are cheap and rare.

Work stealing is decentralized — there is no dispatcher assigning work; each worker independently decides to steal when it runs dry — which is what makes it scale, since the balancing cost falls only on workers that would otherwise be idle. And it is self-tuning to the skew: when task sizes are uniform the round-robin split is already fine and almost no steals happen, and when they are highly skewed the stealing does the most work, because that is exactly when a static split strands the most behind one worker.

It is a heuristic, not an oracle. A steal that happens to grab a large task late in the schedule cannot undo the imbalance perfectly, so the makespan lands near the ideal — total work divided by workers — rather than exactly on it. The guarantee is the classic list-scheduling bound: the finish time stays within one maximum task duration (times one minus one over the worker count) of the ideal, and it shrinks as tasks get finer-grained.

**Let each worker drain its own queue front and steal from the back of the busiest queue when it empties, so no worker idles beside a backlog; the makespan drops toward the ideal, within a bound set by the largest task, and stealing costs the most only when the skew is worst.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/worksteal-inter-01. The fixture is eight task durations — mostly small, with two large ones — and two workers.

```json filename=modules/orchestration-and-governance/code/worksteal-inter-01/worksteal.json:3-4 COMPLETE
  "durations": [10, 1, 1, 1, 10, 1, 1, 1],
  "workers": 2
```

The static split assigns task i to worker i modulo the worker count, up front, and sums each worker's durations.

```python filename=modules/orchestration-and-governance/code/worksteal-inter-01/worksteal.py:30-35 COMPLETE
def static_loads(durations, workers):
    """Round-robin by count: task i goes to worker i % workers, decided up front."""
    loads = [0.0] * workers
    for i, d in enumerate(durations):
        loads[i % workers] += d
    return loads
```

Work stealing simulates the same round-robin queues, then lets the earliest-free worker take its own next task, or — when its queue is empty — steal the back task of the most-loaded queue.

```python filename=modules/orchestration-and-governance/code/worksteal-inter-01/worksteal.py:38-51 COMPLETE
def steal_finish(durations, workers):
    """Work stealing: each worker drains its own round-robin queue, then steals from the back of the most-loaded queue when it runs dry."""
    queues = [[durations[i] for i in range(len(durations)) if i % workers == w] for w in range(workers)]
    free = [0.0] * workers
    while any(queues):
        # the earliest-free worker takes the next task (its own, or a stolen one)
        w = min(range(workers), key=lambda j: free[j])
        if queues[w]:
            task = queues[w].pop(0)
        else:
            victim = max(range(workers), key=lambda j: len(queues[j]))
            task = queues[victim].pop()  # steal from the back
        free[w] += task
    return free
```

The makespan is the last finish time, and the idle time is the total worker-time no one spent working.

```python filename=modules/orchestration-and-governance/code/worksteal-inter-01/worksteal.py:54-56 COMPLETE
def makespan(loads):
    """The time the last worker finishes -- the schedule's real duration."""
    return max(loads)
```

```python filename=modules/orchestration-and-governance/code/worksteal-inter-01/worksteal.py:59-61 COMPLETE
def idle_time(loads):
    """Total worker-time wasted: every worker waits until the makespan, minus the work it did."""
    return makespan(loads) * len(loads) - sum(loads)
```

Before running it, predict: the total work is 26 and there are two workers, so the best possible makespan is 13. Round-robin sends tasks 0 and 4 — both the 10s — to worker 0, so worker 0 should carry far more than half. Run `--schedule`:

```text filename=worksteal.py --schedule
SCHEDULE — 8 tasks across 2 workers (total work 26, ideal makespan 13)
--------------------------------------------------------
  static round-robin loads : ['22', '4']   makespan 22
  work-stealing loads      : ['11', '15']   makespan 15
--------------------------------------------------------
  same tasks, same total work; stealing moves work off the overloaded worker
```

The prediction holds. The static split gives worker 0 a load of 22 and worker 1 just 4, for a makespan of 22 — nearly double the ideal 13 — because both 10s landed on worker 0. Work stealing rebalances to 11 and 15: worker 1, having drained its four small tasks, stole from worker 0 until the loads were much closer, cutting the makespan to 15. Same eight tasks, same 26 units of total work; only the assignment moved.

The waste shows up most clearly as idle time. The static schedule leaves 22×2 − 26 = 18 units of idle worker-time — worker 1 standing idle from time 4 to 22. Work stealing leaves 15×2 − 26 = 4 units. It does not reach the ideal 13: worker 1 stole one of the 10s only after it had already taken several small tasks, so it overshot slightly, which is the coarse-steal limitation the bound predicts. But it turned an 18-unit waste into a 4-unit one without changing a single task.

<svg role="img" aria-label="Three makespan bars. Static reaches 22 with a large idle portion; work stealing reaches 15 with a small idle portion; a dashed line marks the ideal at 13." viewBox="0 0 440 150">
<line x1="60" y1="20" x2="60" y2="120" stroke="var(--line)"/>
<text x="55" y="45" fill="var(--ink)" font-size="9" text-anchor="end">static</text>
<rect x="60" y="36" width="240" height="18" fill="var(--s2)"/>
<rect x="300" y="36" width="90" height="18" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="3 3"/>
<text x="398" y="49" fill="var(--muted)" font-size="8">22</text>
<text x="55" y="80" fill="var(--ink)" font-size="9" text-anchor="end">steal</text>
<rect x="60" y="71" width="165" height="18" fill="var(--s1)"/>
<rect x="225" y="71" width="20" height="18" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="3 3"/>
<text x="253" y="84" fill="var(--muted)" font-size="8">15</text>
<line x1="203" y1="20" x2="203" y2="120" stroke="var(--grid)" stroke-dasharray="4 3"/>
<text x="203" y="134" fill="var(--muted)" font-size="8" text-anchor="middle">ideal 13</text>
<text x="320" y="30" fill="var(--muted)" font-size="8">dashed = idle</text>
</svg>
^ Static finishes at 22 with a wide idle tail; work stealing finishes at 15 with a thin one, closing most of the gap to the ideal 13.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that both schedules do the same total work, that the static makespan exceeds the ideal, that work stealing finishes sooner than static, that work stealing stays within the list-scheduling bound, and that static wastes more idle worker-time.

```python filename=modules/orchestration-and-governance/code/worksteal-inter-01/worksteal.py:103-116 COMPLETE
    same_total_work = abs(sum(s) - sum(durations)) < 1e-9 and abs(sum(w) - sum(durations)) < 1e-9
    print("  both schedules do the same total work = %s (%g)" % (same_total_work, sum(durations)))

    static_exceeds_ideal = makespan(s) > ideal
    print("  static makespan far exceeds the ideal = %s (%g > %g)" % (static_exceeds_ideal, makespan(s), ideal))

    steal_beats_static = makespan(w) < makespan(s)
    print("  work-stealing finishes sooner than static = %s (%g < %g)" % (steal_beats_static, makespan(w), makespan(s)))

    steal_within_bound = makespan(w) <= bound + 1e-9
    print("  work-stealing stays within the list-scheduling bound = %s (%g <= %g)" % (steal_within_bound, makespan(w), bound))

    static_wastes_idle = idle_time(s) > idle_time(w)
    print("  static wastes more idle worker-time = %s (%g > %g)" % (static_wastes_idle, idle_time(s), idle_time(w)))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if stealing ever failed to beat static or ever blew past the scheduling bound:

```text filename=worksteal.py --check
SELF-TEST — static round-robin overloads one worker and leaves others idle; work stealing cuts the makespan and the idle time toward the ideal
----------------------------------------------------------------------------------------------------------------
  both schedules do the same total work = True (26)
  static makespan far exceeds the ideal = True (22 > 13)
  work-stealing finishes sooner than static = True (15 < 22)
  work-stealing stays within the list-scheduling bound = True (15 <= 18)
  static wastes more idle worker-time = True (18 > 4)
```

**The self-test checks the honest claim, not an inflated one: it holds work stealing to the list-scheduling bound (15 ≤ 18) rather than to the ideal 13, so a pass certifies a real, bounded improvement over static — not a claim that stealing balances perfectly.**

## Definition of done

You can explain why a round-robin split by count is balanced only when task durations are equal.
You can explain why the makespan is set by the single most-loaded worker and why the others' idle time is wasted capacity.
You can describe the work-stealing rule — drain your own queue front, steal from the back of the busiest queue when empty — and why owner and thief use opposite ends.
You can explain why work stealing is decentralized and why it costs the most only when the skew is worst.
You can state the list-scheduling bound and explain why stealing approaches but need not reach the ideal makespan.

## Boss fight

Suppose the tasks are not known up front but arrive over time, and worse, each task can spawn child tasks as it runs — the classic fork/join shape. Reason about how work stealing handles this versus a static split. A static split cannot cope at all: you cannot deal out tasks you have not seen yet, and children born on one worker would be stuck there. Work stealing handles it natively — a worker pushes the children it spawns onto its own deque, and idle workers steal them from the back — which is exactly why the technique was invented for recursive parallelism. The back-of-deque steal matters more here: the oldest task on the deque is the highest, coarsest node of the recursion, so stealing it hands the thief a large independent subtree to expand on its own, and steals stay rare even as the total task count explodes.

Now the trap that undoes the benefit: task granularity. If tasks are extremely fine — each a few instructions — the cost of a steal (the synchronization to safely take the back of another worker's deque) can exceed the work stolen, and the overhead dominates. The standard fix is a granularity cutoff: below some size, a worker stops splitting and just runs the task inline rather than making it stealable, so steals amortize over enough real work. The rule generalizes the module's own caveat — stealing approaches the ideal as tasks get finer, but only until they get so fine that the steal overhead itself becomes the bottleneck, so real schedulers keep tasks coarse enough to steal profitably.

**Work stealing handles dynamically spawned fork/join tasks natively — spawn onto your own deque, steal coarse subtrees from the back — but if tasks are too fine the steal overhead dominates, so a granularity cutoff that runs tiny tasks inline keeps steals profitable.**

## External resources

Blumofe and Leiserson, "Scheduling Multithreaded Computations by Work Stealing" (1999), is the foundational analysis, with the time and space bounds behind the Cilk scheduler.
The documentation for Java's ForkJoinPool, Go's runtime scheduler, and Rust's Rayon describes production work-stealing deques and the spawn/steal model.
Any parallel-computing text's treatment of list scheduling and Graham's bound covers why a greedy or stealing schedule finishes within a maximum task duration of the ideal makespan; the topic's own modules on power-of-two-choices load balancing and head-of-line blocking cover the neighboring dispatch-time and queueing problems.
