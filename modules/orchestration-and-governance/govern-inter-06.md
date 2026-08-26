---
id: govern-inter-06
title: Dead-letter a poison task after max retries, or it blocks the whole fan-out
topic: orchestration-and-governance
level: intermediate
status: ready
time: 8-10h
summary: Fan work out to a worker and some tasks fail transiently — retry and they pass — but a poison task fails every time, and retrying it is not resilience, it is a trap that starves every task behind it. A correct worker retries up to max_retries and then moves the failing task to a dead-letter queue and continues, so all four tasks reach a terminal state in 7 attempts with the poison task contained in the DLQ. A worker that retries forever burns the entire 20-attempt budget on the poison task and never reaches the two tasks behind it, stalling the whole fan-out on one bad input. The retry bound plus a dead-letter queue is what converts an unbounded failure into a contained one with a record, and without it a single malformed input takes down the queue.
eli5: If one letter has a bad address and keeps coming back, you do not keep re-mailing it forever while every other letter waits in the bag. You set the bad one aside in a special pile to look at later and send the rest. A worker with no such pile gets stuck on the bad letter and nobody else's mail ever goes out.
---

## Why this module

Fan-out is the heart of orchestration: split work across workers and let them churn through a queue of tasks. Retrying failed tasks is standard and correct — most failures are transient. But retrying assumes failures eventually succeed, and some do not: a malformed input, a permanently broken dependency, a task that will fail on every attempt until the heat death of the universe. This module builds what a worker must do with those poison tasks, because the naive answer — keep retrying — does not just waste effort on the bad task, it starves every task behind it, converting one bad input into a total stall.

The failure is a blocked queue. A worker processing a queue in order, retrying on failure, will loop on a poison task forever, and while it loops, nothing else in the queue is processed. The tasks behind the poison one are not failing — they are perfectly fine — but they never get the chance to run, because the worker never moves past the task that cannot succeed. The fix is two pieces: a retry bound and a dead-letter queue. Retry a failing task up to a maximum number of attempts; if it still fails, stop retrying it, move it to a dead-letter queue — a holding area for tasks that could not be processed — and continue to the next task. The poison task is now contained: it consumed a bounded number of attempts, it is recorded for later inspection, and the rest of the fan-out drains normally. Without the bound and the DLQ, one poison task is a denial of service on your own queue.

You need the fan-out framing from the earlier governance modules. Everything runs offline against a queue fixture — four tasks, one of them poison, an attempt budget — stdlib Python 3, `$0.00`. The budget bounds the simulation so a "retry forever" bug shows up as starvation rather than an actual infinite loop. The instinct to unlearn is that retrying is always the resilient choice. Retrying is resilient against transient failures and catastrophic against permanent ones, and telling them apart — by bounding the retries — is what keeps one bad task from taking down the queue.

Here is the correct worker draining the queue:

```
# modules/orchestration-and-governance/code/govern-inter-06/ — COMPLETE, run from that directory
$ python3 dlq.py --run

RUN — correct worker: retry to max_retries=3, then dead-letter
------------------------------------------------------------------
  done:        ['t1', 't3', 't4']
  dead-letter: ['t2']
  unreached:   []
  attempts used: 7 of 20 budget
```

run: 2026-08-26 · deterministic; outcomes are a fixture · 4 tasks · `python3 dlq.py --run`

Three tasks done, the poison task t2 dead-lettered, nothing unreached, and only 7 of the 20 attempts used. Every task reached a terminal state and the poison one is safely set aside. This module is that outcome and the stall that happens without the dead-letter queue.

## Concepts

Named here so you can find them again; each is built below.

- **Fan-out queue** — an ordered set of tasks a worker processes.
- **Transient failure** — a task that fails now but succeeds on retry.
- **Poison task** — a task that fails on every attempt; retrying never helps.
- **Retry bound (max_retries)** — the cap on attempts before giving up on a task.
- **Dead-letter queue (DLQ)** — a holding area for tasks that exhausted their retries.
- **Starvation** — tasks behind a poison one never running because the worker is stuck.

## Worked example

Source: the dead-letter-queue pattern from every production message system (SQS, RabbitMQ, Kafka) and the retry-bound discipline behind it, applied to a subagent fan-out; the task outcomes here stand in for real success and failure so the drain and the starvation are exact and checkable.

Script and fixture: `modules/orchestration-and-governance/code/govern-inter-06/` — `dlq.py`, and `queue.json`, four tasks (one poison) with a retry bound and an attempt budget. Every command runs from there.

### The worker: retry, bound, dead-letter

The worker is one function with a policy flag — dead-letter or not — and returns four sets that account for every task:

```
# dlq.py:38-42 — COMPLETE (the worker's contract)
def run_queue(data, dead_letter):
    """Process the queue within the attempt budget.

    dead_letter=True: retry up to max_retries, then move on (to the DLQ). False: retry
    forever (the bug). Returns (done, dlq, unreached, attempts_used).
    """
```

It processes tasks in order. For each, it retries until success — or, with the dead-letter policy, until the retry bound, then sets the task aside.

```
# dlq.py:44-66 — COMPLETE (the bounded worker; dead_letter=False is the bug)
    done, dlq = [], []
    attempts_used = 0
    i = 0
    while i < len(tasks) and attempts_used < budget:
        task = tasks[i]
        tries = 0
        while attempts_used < budget:
            tries += 1
            attempts_used += 1
            if tries >= task["attempts_to_succeed"]:      # succeeds on this attempt
                done.append(task["id"])
                i += 1
                break
            if dead_letter and tries >= max_retries:      # give up, dead-letter it
                dlq.append(task["id"])
                i += 1
                break
            # else: retry (dead_letter=False loops until budget runs out on a poison task)
```

Whatever the policy leaves unprocessed is captured as `unreached` — the tasks the worker never got to:

```
# dlq.py:67 — COMPLETE (the tasks the worker never reached)
    unreached = [t["id"] for t in tasks[i:]]
```

The two exits from the inner loop are the whole design. A task succeeds when `tries` reaches its `attempts_to_succeed` — t1 needs 1, t3 needs 2. Or, with `dead_letter` on, a task that reaches `max_retries` without succeeding is moved to the DLQ and the worker advances. The poison task t2 needs 999 attempts, so it never succeeds; the only way past it is the dead-letter exit. Turn that exit off — `dead_letter=False` — and the inner loop has no way to leave a poison task except exhausting the global budget, which is the bug.

### The correct run: contained and drained

With dead-lettering on, the poison task is bounded and the queue drains. The cold open showed it: t1 and t3 and t4 done, t2 dead-lettered, 7 attempts used. Trace the attempts: t1 succeeds in 1, t2 fails 3 times and is dead-lettered (3), t3 succeeds on its 2nd (2), t4 succeeds in 1 — 1 + 3 + 2 + 1 = 7. The poison task cost exactly max_retries attempts and then got out of the way.

<svg viewBox="0 0 700 180" role="img" aria-label="A queue of four tasks processed left to right. t1 done in 1 attempt. t2 (poison) fails 3 times then routes down to a dead-letter queue box. t3 done in 2. t4 done in 1. All four reach a terminal state; the main lane keeps flowing past t2.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">correct: retry to the bound, dead-letter the poison, keep draining</text>
    <line x1="40" y1="70" x2="660" y2="70" stroke="var(--grid)"></line>
    <rect x="60" y="56" width="70" height="28" rx="4" fill="var(--s1)"></rect><text x="95" y="74" text-anchor="middle" fill="var(--panel)" font-size="8">t1 ✓</text>
    <rect x="170" y="56" width="70" height="28" rx="4" fill="var(--s2)"></rect><text x="205" y="74" text-anchor="middle" fill="var(--panel)" font-size="8">t2 fail×3</text>
    <rect x="280" y="56" width="70" height="28" rx="4" fill="var(--s1)"></rect><text x="315" y="74" text-anchor="middle" fill="var(--panel)" font-size="8">t3 ✓</text>
    <rect x="390" y="56" width="70" height="28" rx="4" fill="var(--s1)"></rect><text x="425" y="74" text-anchor="middle" fill="var(--panel)" font-size="8">t4 ✓</text>
    <path d="M 205 84 L 205 130" stroke="var(--s2)" stroke-dasharray="3 2"></path>
    <rect x="150" y="130" width="110" height="26" rx="4" fill="none" stroke="var(--s2)"></rect><text x="205" y="147" text-anchor="middle" fill="var(--s2)" font-size="8">dead-letter: t2</text>
    <text x="480" y="74" fill="var(--s1)" font-size="8">queue drained, 7 attempts</text>
  </g>
</svg>
^ The poison task fails its bounded three times and is routed down to the dead-letter queue, and the main lane flows straight past it to t3 and t4. Every task ends somewhere — done or dead-lettered — and the fan-out completes.

### The bug: retry forever, starve the rest

Turn off dead-lettering and the worker retries the poison task until the budget is gone.

```
# $ python3 dlq.py --broken
#   done:        ['t1']
#   dead-letter: []  (no DLQ -- nothing is ever given up)
#   unreached:   ['t2', 't3', 't4']  <- starved by the poison task
#   attempts used: 20 of 20 budget (all burned on the poison task)
```

run: 2026-08-26 · deterministic · `python3 dlq.py --broken`

t1 succeeds, and then the worker hits t2 and never leaves. It retries t2 attempt after attempt — 4, 5, 6, all the way to the 20-attempt budget — and t3 and t4, both perfectly good tasks, never run. The report shows them unreached, starved not because they failed but because the worker was trapped on the one task that could not succeed. In a real system with no budget cap this is an infinite loop: the fan-out hangs forever on a single malformed input, and every task queued behind it waits indefinitely. One poison message is a denial of service on the whole queue.

<svg viewBox="0 0 700 170" role="img" aria-label="The broken worker. t1 done. t2 (poison) has a loop arrow retrying it over and over, consuming all remaining attempts. t3 and t4 sit greyed out behind it, never reached. The main lane is blocked at t2.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">broken: retry forever — t2 blocks the lane, t3 and t4 starve</text>
    <line x1="40" y1="80" x2="660" y2="80" stroke="var(--grid)"></line>
    <rect x="60" y="66" width="70" height="28" rx="4" fill="var(--s1)"></rect><text x="95" y="84" text-anchor="middle" fill="var(--panel)" font-size="8">t1 ✓</text>
    <rect x="180" y="66" width="80" height="28" rx="4" fill="var(--s2)"></rect><text x="220" y="84" text-anchor="middle" fill="var(--panel)" font-size="8">t2 ∞ retry</text>
    <path d="M 220 66 A 26 26 0 1 1 246 70" fill="none" stroke="var(--s2)" stroke-width="1.5"></path>
    <text x="220" y="122" text-anchor="middle" fill="var(--s2)" font-size="8">burns all 20 attempts</text>
    <rect x="340" y="66" width="70" height="28" rx="4" fill="none" stroke="var(--muted)" stroke-dasharray="3 2"></rect><text x="375" y="84" text-anchor="middle" fill="var(--muted)" font-size="8">t3</text>
    <rect x="430" y="66" width="70" height="28" rx="4" fill="none" stroke="var(--muted)" stroke-dasharray="3 2"></rect><text x="465" y="84" text-anchor="middle" fill="var(--muted)" font-size="8">t4</text>
    <text x="520" y="84" fill="var(--muted)" font-size="8">never reached</text>
  </g>
</svg>
^ The worker circles on t2, spending every remaining attempt, and t3 and t4 sit untouched behind it. Their failure is not their own — they are starved by a worker that will not give up on a task that cannot succeed.

**A worker that retries every failure without bound converts one poison task into a stalled queue, starving every task behind it — a retry bound plus a dead-letter queue contains the poison after max_retries and lets the rest of the fan-out drain, turning an unbounded failure into a bounded one with a record.**

### The self-test

The `--check` mode asserts both the containment and the failure: the correct worker reaches a terminal state for every task and dead-letters the poison, while the broken worker starves the tasks behind it and burns the whole budget.

```
# $ python3 dlq.py --check
#   correct: every task reached a terminal state (done or DLQ) = True
#   correct: the poison task is dead-lettered = True (DLQ=['t2'])
#   correct: tasks after the poison one still ran = True (t3, t4 done)
#   broken: tasks behind the poison are STARVED = True (unreached ['t2', 't3', 't4'])
#   broken: the poison task burned the whole attempt budget = True (20)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 dlq.py --check`

The drained-queue definition and the starvation are each one line:

```
# dlq.py:101-112 — COMPLETE (correct drains to terminal; broken starves the rest)
    done, dlq, unreached, used = run_queue(data, dead_letter=True)
    all_terminal = set(done) | set(dlq) == set(tasks) and unreached == []

    b_done, b_dlq, b_unreached, b_used = run_queue(data, dead_letter=False)
    broken_starves = "t3" in b_unreached and "t4" in b_unreached
```

`all_terminal` requires every task to be done or dead-lettered with nothing unreached; `broken_starves` requires the two good tasks to be unreached under the broken policy — a drained queue proven for one policy, a stalled one for the other.

The `all_terminal` line is the correctness anchor: every task must end as either done or dead-lettered with nothing unreached, which is the definition of a drained queue, and if the poison task were not contained that would fail. The `broken_starves` line makes the stakes unavoidable — it requires the good tasks t3 and t4 to be unreached under the broken policy, proving that the harm is not to the poison task but to the innocent tasks behind it, which is why retrying forever is a fleet-level failure, not a local one.

### The running tally

| policy | done | dead-letter | unreached | attempts |
|---|---|---|---|---|
| correct (bound + DLQ) | t1, t3, t4 | t2 | none | 7 |
| broken (retry forever) | t1 | none | t2, t3, t4 | 20 (all) |

<svg viewBox="0 0 700 160" role="img" aria-label="Two stacked bars over the four tasks. Correct: 3 done (green) + 1 dead-lettered (amber) = 4 terminal, 0 unreached. Broken: 1 done (green) + 3 unreached (grey). The correct bar is fully accounted; the broken bar is mostly unreached.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">task outcomes by policy (of 4 tasks)</text>
    <text x="20" y="54" fill="var(--ink)">correct</text>
    <rect x="130" y="42" width="330" height="20" fill="var(--s1)"></rect><text x="295" y="57" text-anchor="middle" fill="var(--panel)" font-size="8">3 done</text>
    <rect x="460" y="42" width="110" height="20" fill="var(--acc)"></rect><text x="515" y="57" text-anchor="middle" fill="var(--acc-ink)" font-size="8">1 DLQ</text>
    <text x="580" y="57" fill="var(--s1)" font-size="8">0 unreached</text>
    <text x="20" y="98" fill="var(--ink)">broken</text>
    <rect x="130" y="86" width="110" height="20" fill="var(--s1)"></rect><text x="185" y="101" text-anchor="middle" fill="var(--panel)" font-size="8">1 done</text>
    <rect x="240" y="86" width="330" height="20" fill="var(--muted)" opacity="0.4"></rect><text x="405" y="101" text-anchor="middle" fill="var(--s2)" font-size="8">3 unreached (starved)</text>
    <text x="130" y="132" fill="var(--muted)" font-size="8">same poison task — one policy accounts for every task, the other abandons three</text>
  </g>
</svg>
^ The correct bar is fully accounted for — three done, one dead-lettered, none left. The broken bar completes one task and abandons three. The poison task is identical; only the retry bound differs.

Read the unreached column. The correct policy leaves nothing unreached — the queue fully drains — while the broken policy leaves three of four tasks unreached, two of them healthy. And the attempts column shows the waste: the broken worker spent the entire budget and completed one task, while the correct worker finished everything with 7 attempts. The poison task is the same in both; the only difference is whether the worker was allowed to give up on it. A bounded failure with a record beats an unbounded retry every time, because the record is recoverable and the stall is not.

### What we did not settle

A dead-letter queue is the containment, not the cure. The DLQ needs monitoring — a growing dead-letter queue is a signal something is systematically broken, and tasks there need triage, reprocessing after a fix, or alerting. Retries should usually back off exponentially rather than fire immediately, so a transiently-overloaded dependency gets time to recover, which the immediate-retry model here omits. Distinguishing transient from permanent failures earlier — by error type — lets you dead-letter a clearly-permanent failure immediately instead of wasting max_retries on it. And in a concurrent fan-out, one worker stuck on a poison task starves less if other workers keep draining, but the poison task still needs a bound or it blocks its own retries forever. The core here — bound the retries, dead-letter the rest, keep draining — is the invariant under all of it.

## Build

The practice in one paragraph: never retry a failing task without a bound; cap retries at max_retries, and on exhaustion move the task to a dead-letter queue and continue, so the fan-out drains instead of stalling; monitor the dead-letter queue as a health signal and triage what lands there; and back off between retries so a transient overload recovers. Distinguish permanent failures by error type when you can, and dead-letter them without wasting the full retry budget.

We opened on the correct drain. The number that separates containment from stall is the unreached count:

```
# modules/orchestration-and-governance/code/govern-inter-06/ — COMPLETE, run from that directory
$ python3 dlq.py --broken
  unreached:   ['t2', 't3', 't4']  <- starved by the poison task
```

Now build it yourself. Model a fan-out queue with a poison task, and process it with a retry bound and a dead-letter queue. Your number to beat is not throughput; it is **that every task reaches a terminal state and the tasks behind the poison one still run**, which only the bounded, dead-lettering worker achieves. Then remove the bound and watch the poison task starve the rest. Bring back both policies' done, DLQ, and unreached sets. Good luck.

## Definition of done

- [ ] A fan-out queue processed in order, with retries on failure
- [ ] A poison task that fails on every attempt
- [ ] A retry bound (max_retries) after which a task is given up on
- [ ] A dead-letter queue holding tasks that exhausted their retries
- [ ] Confirmation the correct worker drains the queue and dead-letters the poison
- [ ] Confirmation an unbounded-retry worker starves the tasks behind the poison one
- [ ] `python3 dlq.py --check` printing SELF-TEST PASS: all-terminal, poison-dead-lettered, later-processed, broken-starves, broken-burns-budget
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What is a poison task, and why is retrying it not resilience?
2. What two mechanisms contain a poison task, and what does each do?
3. The broken worker's harm is not to the poison task. Who does it harm, and how?
4. Why is a bounded failure with a dead-letter record better than an unbounded retry?
5. Your own queue had a poison task. Under each policy, which tasks reached a terminal state and which were starved?

## External resources

- AWS SQS / RabbitMQ dead-letter-queue documentation — my summary: the production DLQ pattern, with max-receive counts, dead-letter routing, and monitoring; read it for how real message systems bound retries and contain poison messages.
- Google SRE Book, chapters on retries and cascading failures — my summary: why unbounded retries cause overload and how backoff and budgets contain them; read it for the retry-bound discipline this module's DLQ complements.
- This hub, *ship-inter-04* — modules/ship-and-operate/ship-inter-04.md — my summary: the circuit-breaker module, another mechanism for not hammering a failing dependency; read it for the complementary control — the breaker stops calling a broken service, the DLQ sets aside a broken task.
