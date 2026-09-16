---
id: govern-inter-12
title: Age waiting tasks up in priority — a strict priority queue starves the low-priority work forever
topic: orchestration-and-governance
level: intermediate
status: ready
time: 21 min
summary: Strict priority scheduling always serves the most urgent task, so under sustained high-priority load a low-priority task is never chosen — it waits forever while the system stays busy. Aging raises a task's effective priority by its wait time, so it eventually outranks fresh high-priority work. With a high task arriving every tick, strict never serves the low task; aging serves it at tick 4.
eli5: If a busy doctor always sees the most urgent patient first, and urgent patients keep arriving, the person with a mild problem waits all day and never gets seen. The fix: the longer someone waits, the more their number bumps up, so eventually even a mild case jumps ahead and gets seen.
---

## Why this module

Strict priority scheduling is correct about urgency and silently cruel about fairness, and under load the cruelty wins.

A priority queue serves the highest-priority task available, which is exactly what you want for urgency: the critical task jumps ahead of the routine one. But consider what happens when high-priority work keeps arriving, which under real load it does. Every time the server finishes a task and looks for the next, there is something high-priority waiting — a fresh urgent task that arrived while it was busy — so it serves that. The low-priority task at the back is never the highest, so it is never chosen. It does not error, it does not time out, it just waits, indefinitely, while the system runs at full tilt serving a never-ending stream of more-urgent work. This is starvation, and it is the default behavior of strict priority under sustained load.

The failure is invisible in exactly the way that makes it dangerous. The system looks healthy: the queue is being served, throughput is high, high-priority latency is great. Nothing is broken. But some low-priority task — a cleanup job, a batch report, one unlucky user's request — has been waiting for an hour, a day, forever, and no metric on the urgent path shows it. Starvation is a fairness failure that hides behind a performance success.

<svg role="img" aria-label="A queue where high-priority tasks keep arriving and jumping ahead of the low task, which stays stuck at the front-of-service line but never crosses it" viewBox="0 0 460 130" width="460" height="130">
  <rect x="0" y="0" width="460" height="130" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">strict priority: fresh H tasks always cut in front of L</text>
  <line x1="360" y1="30" x2="360" y2="100" stroke="var(--acc-ink)" stroke-dasharray="3 2"/><text x="366" y="45" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">served →</text>
  <g font-family="var(--mono)" font-size="9">
    <rect x="290" y="50" width="60" height="28" fill="var(--acc-soft)" stroke="var(--line)"/><text x="308" y="68" fill="var(--acc-ink)">H (5)</text>
    <rect x="220" y="50" width="60" height="28" fill="var(--acc-soft)" stroke="var(--line)"/><text x="238" y="68" fill="var(--acc-ink)">H (5)</text>
    <rect x="150" y="50" width="60" height="28" fill="var(--acc-soft)" stroke="var(--line)"/><text x="168" y="68" fill="var(--acc-ink)">H (5)</text>
    <rect x="70" y="50" width="50" height="28" fill="var(--s2)" stroke="var(--line)"/><text x="84" y="68" fill="var(--ink)">L (1)</text>
  </g>
  <text x="60" y="98" font-family="var(--mono)" font-size="8" fill="var(--s2)">L waits at the back — new H's keep arriving and pass it</text>
  <path d="M40 40 Q100 25 150 45" fill="none" stroke="var(--acc-ink)"/><text x="60" y="34" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">new H cuts in</text>
</svg>
^ Every fresh high-priority task outranks the waiting low task, so L never advances to the front — the queue is busy and L is permanently stuck.

The fix is aging: let a task's effective priority rise the longer it waits. A low-priority task that has waited long enough eventually has an effective priority above a freshly-arrived high-priority task, and it gets served. Urgency still wins in the short run — a brand-new urgent task beats a low task that just arrived — but the low task's accumulated wait steadily closes the gap, so no task can be starved past a bounded wait. You trade a little promptness on high-priority work for a guarantee that nothing waits forever.

We will flood a single-server queue with a high-priority task every tick and drop in one low-priority task. Under strict priority, the low task is never served across the whole horizon — starved. Under aging, its priority climbs with its wait, passes the high-priority level, and it is served at tick 4. Same arrivals; only the scheduler's fairness differs.

**Strict priority under sustained high-priority load never reaches the low-priority task, so it starves; aging lifts a task's effective priority by its wait, guaranteeing every task a turn within a bounded time.**

## Concepts

Starvation is a consequence of a scheduling rule that depends only on a task's intrinsic priority and never on how long it has waited. Strict priority is exactly such a rule: it compares base priorities, and if higher-priority tasks keep arriving, the comparison always goes against the low task, forever. Nothing in the rule notices that the low task has been waiting; waiting does not change its standing. So the low task's fate is decided entirely by the arrival rate of higher-priority work, and when that rate is high enough to keep the server busy, the low task never runs.

Aging breaks the dependence on arrival rate by making waiting count. The effective priority becomes the base priority plus a term that grows with wait time — here, simply the number of ticks waited. Now a low task's standing improves the longer it sits, and the improvement is unbounded, so eventually it must exceed the base priority of even a fresh high-priority task. At that point it is the highest-priority task available and it is served. The maximum time any task can wait is bounded by how long it takes its age term to overcome the priority gap, which is a function of the gap and the aging rate — not of the arrival rate. That is the key: aging makes the worst-case wait independent of how much higher-priority work shows up.

The aging rate is the tuning dial, and it sets the fairness-versus-urgency trade. A fast aging rate closes the priority gap quickly, so low-priority tasks wait less — but high-priority tasks lose their edge sooner, so urgent work can be delayed by aged low-priority work more often. A slow aging rate preserves urgency longer but lets low tasks wait longer before their turn. The right rate is chosen from your fairness requirement: pick the maximum acceptable wait for a low-priority task, and set the aging rate so its effective priority overtakes a fresh high task by then. Strict priority is the limit of zero aging rate — infinite acceptable wait, i.e., starvation allowed.

This is a classic OS scheduler technique, and it generalizes anywhere priorities meet sustained load: task queues, request routers, job schedulers, any system where some work is more urgent than other work and the urgent work is plentiful. The lesson is that "serve the most important thing first" is an incomplete policy — it needs "and don't let anything wait forever" bolted on, which is precisely what aging provides. A priority scheduler without an anti-starvation mechanism is a starvation bug waiting for enough load to surface it.

**Strict priority depends only on base priority, so sustained higher-priority arrivals starve the low task; aging adds a wait term whose unbounded growth guarantees a turn, with the worst-case wait set by the aging rate, not the arrival rate.**

## Worked example

The fixture is an arrival stream designed to starve: a high-priority task every tick, one low task at the start.

```json filename=modules/orchestration-and-governance/code/govern-inter-12/queue.json:7-13 COMPLETE
  "horizon": 12,
  "tasks": [
    {
      "id": "H00",
      "priority": 5,
      "arrival": 0
    },
```

Twelve ticks, one task served per tick. A priority-5 task arrives every tick (H00 through H11), and one priority-1 task, L, arrives at tick 0.

```text filename=modules/orchestration-and-governance/code/govern-inter-12/aging.py --queue
QUEUE — 12 ticks, one task served per tick
------------------------------------------------------
  a priority-5 task arrives every tick (12 of them)
  one priority-1 task 'L' arrives at tick 0
------------------------------------------------------
  with something urgent always arriving, does L ever get served?
```

The effective priority is base plus wait, and the wait term is only counted when aging is on.

```python filename=modules/orchestration-and-governance/code/govern-inter-12/aging.py:40-43 COMPLETE
def effective_priority(task, now, aging):
    """Base priority, plus wait time if aging is on -- a long wait lifts a low task above a fresh high one."""
    wait = now - task["arrival"]
    return task["priority"] + (wait if aging else 0)
```

The scheduler serves one task per tick, always picking the highest effective priority.

```python filename=modules/orchestration-and-governance/code/govern-inter-12/aging.py:46-59 COMPLETE
def schedule(data, aging):
    """Serve one task per tick, picking the highest effective priority (ties: earliest arrival). Returns the served order."""
    pending = []
    arrivals = {}
    for tk in data["tasks"]:
        arrivals.setdefault(tk["arrival"], []).append(tk)
    served = []
    for now in range(data["horizon"]):
        pending.extend(arrivals.get(now, []))
        if not pending:
            continue
        pending.sort(key=lambda tk: (-effective_priority(tk, now, aging), tk["arrival"], tk["id"]))
        served.append((now, pending.pop(0)["id"]))
    return served
```

```python filename=modules/orchestration-and-governance/code/govern-inter-12/aging.py:62-66 COMPLETE
def served_tick(order, task_id):
    for tick, tid in order:
        if tid == task_id:
            return tick
    return None
```

Predict: under strict priority, every tick the highest available is a priority-5 H (L is priority 1), so L is never served. Under aging, L's effective priority is 1 + wait, which passes 5 once it has waited more than 4 ticks — so around tick 4 or 5 it overtakes the fresh H tasks. Run both.

```text filename=modules/orchestration-and-governance/code/govern-inter-12/aging.py --schedule
SCHEDULE — served order, strict priority vs aging
----------------------------------------------------------
  strict: H00 H01 H02 H03 H04 H05 H06 H07 H08 H09 H10 H11
    L served at: NEVER (starved)
  aging:  H00 H01 H02 H03 L H04 H05 H06 H07 H08 H09 H10
    L served at: tick 4
----------------------------------------------------------
  strict never reaches L; aging lifts it above the fresh high-priority tasks in time.
```

Strict serves H00 through H11 — twelve high-priority tasks, and L never once. It is starved for the entire horizon, and would stay starved for as long as high tasks keep arriving, which is forever. Aging serves H00 through H03, then at tick 4 — when L has waited 4 ticks and its effective priority is 1 + 4 = 5, tying and then beating the fresh H — it serves L, then returns to the H tasks. L waited 4 ticks and got its turn; the high-priority tasks were delayed by exactly one slot. That is the whole trade: one high task waits one extra tick so that the low task does not wait forever.

<svg role="img" aria-label="Served order per tick: strict serves H every tick with L never appearing; aging serves H then inserts L at tick 4" viewBox="0 0 460 150" width="460" height="150">
  <rect x="0" y="0" width="460" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">who is served each tick (0–11)</text>
  <text x="20" y="52" font-family="var(--mono)" font-size="9" fill="var(--s2)">strict</text>
  <g font-family="var(--mono)" font-size="8">
    <g fill="var(--acc-soft)" stroke="var(--line)"><rect x="70" y="40" width="26" height="18"/><rect x="98" y="40" width="26" height="18"/><rect x="126" y="40" width="26" height="18"/><rect x="154" y="40" width="26" height="18"/><rect x="182" y="40" width="26" height="18"/><rect x="210" y="40" width="26" height="18"/><rect x="238" y="40" width="26" height="18"/></g>
    <text x="78" y="53" fill="var(--acc-ink)">H</text><text x="106" y="53" fill="var(--acc-ink)">H</text><text x="134" y="53" fill="var(--acc-ink)">H</text><text x="162" y="53" fill="var(--acc-ink)">H</text><text x="190" y="53" fill="var(--acc-ink)">H</text><text x="218" y="53" fill="var(--acc-ink)">H</text><text x="246" y="53" fill="var(--acc-ink)">…</text>
  </g>
  <text x="300" y="53" font-family="var(--mono)" font-size="9" fill="var(--s2)">L never appears</text>
  <text x="20" y="102" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">aging</text>
  <g font-family="var(--mono)" font-size="8">
    <g fill="var(--acc-soft)" stroke="var(--line)"><rect x="70" y="90" width="26" height="18"/><rect x="98" y="90" width="26" height="18"/><rect x="126" y="90" width="26" height="18"/><rect x="154" y="90" width="26" height="18"/></g>
    <rect x="182" y="90" width="26" height="18" fill="var(--acc-line)" stroke="var(--acc-ink)"/>
    <g fill="var(--acc-soft)" stroke="var(--line)"><rect x="210" y="90" width="26" height="18"/><rect x="238" y="90" width="26" height="18"/></g>
    <text x="78" y="103" fill="var(--acc-ink)">H</text><text x="106" y="103" fill="var(--acc-ink)">H</text><text x="134" y="103" fill="var(--acc-ink)">H</text><text x="162" y="103" fill="var(--acc-ink)">H</text><text x="190" y="103" fill="var(--acc-ink)">L</text><text x="218" y="103" fill="var(--acc-ink)">H</text><text x="246" y="103" fill="var(--acc-ink)">…</text>
  </g>
  <text x="300" y="103" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">L served at tick 4</text>
  <text x="20" y="134" font-family="var(--mono)" font-size="8" fill="var(--muted)">one H slips one slot; L gets its turn instead of waiting forever</text>
</svg>
^ Strict fills every slot with an H and never reaches L; aging gives up one H slot at tick 4 to serve L, bounding its wait.

<svg role="img" aria-label="L's effective priority under aging rises from 1, crossing the constant high-priority level of 5 at tick 4, where it gets served" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">L's effective priority vs the fresh high tasks</text>
  <line x1="50" y1="160" x2="440" y2="160" stroke="var(--line)"/>
  <line x1="50" y1="40" x2="50" y2="160" stroke="var(--line)"/>
  <line x1="50" y1="90" x2="440" y2="90" stroke="var(--s2)" stroke-dasharray="4 3"/><text x="360" y="86" font-family="var(--mono)" font-size="9" fill="var(--s2)">fresh high = 5</text>
  <polyline points="60,150 118,138 176,126 234,102 292,90 350,78" fill="none" stroke="var(--acc-ink)" stroke-width="2"/>
  <circle cx="60" cy="150" r="3" fill="var(--acc-line)"/><circle cx="118" cy="138" r="3" fill="var(--acc-line)"/><circle cx="176" cy="126" r="3" fill="var(--acc-line)"/><circle cx="234" cy="102" r="3" fill="var(--acc-line)"/><circle cx="292" cy="90" r="5" fill="var(--acc-line)" stroke="var(--acc-ink)"/>
  <text x="70" y="146" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">L: 1 + wait</text>
  <line x1="292" y1="40" x2="292" y2="160" stroke="var(--acc-ink)" stroke-dasharray="2 2"/><text x="266" y="176" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">tick 4: L served</text>
  <text x="55" y="176" font-family="var(--mono)" font-size="8" fill="var(--muted)">tick 0</text>
</svg>
^ L's effective priority climbs one per tick; when it reaches the fresh-high level of 5 at tick 4 it is finally the highest and gets served — the crossing point is the bounded wait.

## Build

Reproduce the two schedules. Pure standard library, deterministic, so the starved strict order and L-at-tick-4 aging order come out exactly.

Run `--queue` for the setup, `--schedule` for the two orders, `--check` for the gate. The self-test pins the contrast: strict starves L, aging serves it within a bounded wait, and aging still serves early high-priority work promptly.

```python filename=modules/orchestration-and-governance/code/govern-inter-12/aging.py:101-105 COMPLETE
    strict_starves = served_tick(strict, "L") is None
    print("  strict priority never serves L in the horizon = %s" % strict_starves)

    aging_serves = served_tick(aged, "L") is not None
    print("  aging serves L = %s (tick %s)" % (aging_serves, served_tick(aged, "L")))
```

The `high_still_prompt` check, below these, is what keeps aging honest. It is easy to prevent starvation by simply serving oldest-first (a FIFO queue), but that throws away priority entirely — urgent work would wait behind routine work. The check asserts that under aging an early high-priority task is still served immediately, proving aging preserves urgency in the short run while adding fairness in the long run. Killing starvation without killing priority is the whole point; a fix that did the first by abandoning the second would be no better than a plain queue. Here is the full gate.

```text filename=modules/orchestration-and-governance/code/govern-inter-12/aging.py --check
SELF-TEST — strict priority starves L; aging serves it within a bounded wait
------------------------------------------------------------------------------------
  strict priority never serves L in the horizon = True
  aging serves L = True (tick 4)
  L's wait under aging is bounded (below the horizon) = True (4 < 12)
  aging still serves an early high-priority task promptly = True (H00 at tick 0)
------------------------------------------------------------------------------------
SELF-TEST PASS  strict_starves=True  aging_serves=True  bounded_wait=True  high_still_prompt=True
```

Four True flags. Strict_starves: strict priority never serves L. Aging_serves: aging does. Bounded_wait: L's wait is finite (tick 4). High_still_prompt: aging still serves the first high task at tick 0. The last flag is the guard against overcorrecting — aging must add fairness without discarding priority, and serving H00 immediately proves urgency survives.

**The high-still-prompt check guards against overcorrection: aging must end starvation without becoming a plain FIFO, so urgent work still goes first in the short run.**

## Definition of done

You are done when you reproduce the two schedules and can explain the bound.

Concretely: `--schedule` shows strict serving only H tasks (L starved) and aging serving L at tick 4; `--check` prints PASS with four True flags. You can explain why strict priority starves under sustained high-priority load — its rule ignores wait time, so the low task's fate depends on arrival rate — and why aging bounds the wait — the wait term grows without limit and must eventually overcome the priority gap. You can describe the aging rate as the fairness-versus-urgency dial, and identify strict priority as its zero-rate limit. And you can name where the bug hides: a healthy-looking system with high throughput and good urgent latency, silently starving something.

The habit to carry: any priority scheduler under load needs an anti-starvation mechanism, and aging is the standard one. When some low-priority work "never seems to run" while the system looks busy and healthy, suspect starvation, and check whether the scheduler accounts for wait time at all.

## Boss fight

The instructive failure is a batch job that never runs because the interactive traffic never stops.

A job system runs interactive requests at high priority and nightly batch jobs at low priority, on a shared strict-priority queue. It works during quiet hours. But as the service grows, interactive traffic becomes continuous — there is always a request in the queue — and the batch jobs stop running entirely, because there is never a moment when a batch job is the highest-priority item. Reports go stale, cleanup stops, disk fills, and the incident looks like a storage problem or a cron failure, not a scheduling one, because the batch jobs are not failing — they are simply never selected. Aging would have let each batch job's priority climb until it earned a slot between interactive requests, running the batch work in the gaps without a dedicated window. The system was never overloaded; it was unfair.

Your turn, two moves. First, tune the aging rate to a fairness target. Right now L waits 4 ticks because its priority climbs by 1 per tick and must cross a gap of 4 (from 1 to 5). If your requirement is "no task waits more than 2 ticks," double the aging rate to 2 per tick and predict: L crosses 5 after waiting 2 ticks, served at tick 2 — but now high tasks lose their edge faster, so measure how often a fresh high task is delayed by an aged low one. The rate trades directly between the two. Second, find the starvation threshold under strict priority. Reduce the high-priority arrivals from every tick to every *other* tick and predict: now there are ticks with no fresh high task, so even strict priority eventually serves L — starvation under strict priority requires the high-priority arrival rate to keep the server continuously busy. That tells you strict priority is safe only when you can guarantee high-priority load never saturates the server, which under real growth you cannot, which is why aging is the safe default.

## External resources

Any operating-systems textbook (Silberschatz's "Operating System Concepts," Tanenbaum's "Modern Operating Systems") covers priority scheduling, starvation, and aging as the standard remedy, with the same "raise priority with wait time" mechanism.

For the distributed-systems version, scheduler designs in Kubernetes, YARN, and Borg all include fairness and anti-starvation mechanisms alongside priority; their docs on preemption and fair-sharing describe how they keep low-priority work from being starved indefinitely.

For the queueing-theory framing, the literature on priority queues and their waiting-time distributions shows analytically that low-priority classes can have unbounded expected wait as high-priority load approaches saturation — the formal statement of the starvation this module demonstrates.
