---
id: govern-inter-04
title: Order a multi-agent plan by its dependencies, or run subagents on stale inputs
topic: orchestration-and-governance
level: intermediate
status: ready
time: 8-10h
summary: A fan-out plan is a task DAG where a dependency promises the producer finishes before the consumer starts, and running the tasks in the order they sit in the plan file breaks that promise six times over six tasks — every consumer runs before its producer, each violation a subagent reading an input that does not exist yet. A topological sort by Kahn's algorithm produces an order with zero violations by only ever running a task whose dependencies are all done, and it carries a second duty: a plan whose dependencies form a cycle has no valid order, so the scheduler reports it uncompletable and names the stranded tasks instead of deadlocking. The lesson is that dependency order is not the authoring order, and a scheduler that ignores it fails silently on stale data rather than loudly on a crash.
eli5: If you are baking, you must crack the eggs before you whisk them and whisk before you pour the batter. A list of steps written in any order does not change that. If you just do the steps top to bottom without checking what each one needs, you will try to pour batter you have not made yet. And if step one needs step three which needs step one, no order works at all — you have to notice that instead of standing there forever.
---

## Why this module

The orchestration track has built fan-outs that split work across subagents under a partition contract. This module handles what comes next: the pieces of a fanned-out plan are usually not independent — one subagent's output is another's input. `clean_data` needs `fetch_sources`; `evaluate` needs both `build_index` and `train_model`. Those needs are dependencies, and a dependency is a scheduling constraint: the producer must finish before the consumer starts. This module builds the scheduler that honours those constraints and shows the specific, quiet failure of the scheduler that does not.

The failure is quiet, which is what makes it dangerous. If you run tasks in whatever order they appear in the plan file, a consumer can run before its producer, and the subagent does not crash — it reads whatever is at the input's location, which is nothing yet, or worse, a stale artifact from a previous run, and returns a plausible-looking result built on the wrong data. Nothing errors; the answer is just wrong, and traced back weeks later. The fix is a topological sort: an ordering where every task follows all of its dependencies, produced by only ever running tasks whose dependencies are already done. And the scheduler has a second duty that is easy to forget until it bites — if the dependencies form a cycle, no valid order exists, and the scheduler must detect and report that rather than loop or hang.

You need the fan-out framing from the earlier governance modules, nothing more. Everything runs offline against a plan fixture — six tasks with real dependencies, plus a deliberately cyclic plan — stdlib Python 3, `$0.00`. The instinct to unlearn is that the order tasks are written in is a runnable order. It is not; the runnable order is any topological sort of the dependency graph, and they can be exact opposites.

Here is the plan's written order against a dependency-respecting one:

```
# modules/orchestration-and-governance/code/govern-inter-04/ — COMPLETE, run from that directory
$ python3 dag.py --order

ORDER — the plan's listed order vs a dependency-respecting order
------------------------------------------------------------------
  listed order (as written): write_report -> evaluate -> build_index -> train_model -> clean_data -> fetch_sources
  topological order:         fetch_sources -> clean_data -> build_index -> train_model -> evaluate -> write_report
```

run: 2026-08-26 · deterministic; plan dependencies are a fixture · 6 tasks · `python3 dag.py --order`

The listed order is the exact reverse of a valid one — `write_report` first, `fetch_sources` last. Run it as written and every task runs before the thing it depends on. This module is the distance between those two lines.

## Concepts

Named here so you can find them again; each is built below.

- **Task DAG** — tasks as nodes, dependencies as directed edges; a plan is a directed acyclic graph.
- **Dependency** — an edge meaning the producer must finish before the consumer starts.
- **Topological sort** — an ordering in which every task follows all its dependencies.
- **Kahn's algorithm** — build that order by repeatedly running whatever has no unfinished dependencies.
- **Violation** — a consumer scheduled before its producer; a subagent reading an input that is not ready.
- **Cycle** — dependencies that loop, so no valid order exists; the scheduler must report it, not hang.

## Worked example

Source: the task-graph scheduling every workflow engine does (Airflow, Make, build systems, and multi-agent planners that fan work to subagents), reduced to its core algorithm; the plan and its dependencies here stand in for a real fan-out so the ordering, violations, and cycle are exact and checkable.

Script and fixture: `modules/orchestration-and-governance/code/govern-inter-04/` — `dag.py`, and `plan.json`, six tasks with dependencies plus a three-task cyclic plan. Every command runs from there.

### The plan is a graph, not a list

The six tasks form a diamond: everything starts at `fetch_sources`, `build_index` and `train_model` both branch off `clean_data`, and `evaluate` waits for both before `write_report` closes it out.

<svg viewBox="0 0 700 200" role="img" aria-label="A dependency DAG. fetch_sources points to clean_data. clean_data points to both build_index and train_model. build_index and train_model both point to evaluate. evaluate points to write_report. It forms a diamond that opens at clean_data and closes at evaluate.">
  <g font-family="var(--mono)" font-size="9">
    <g fill="var(--panel)" stroke="var(--line)">
      <rect x="20" y="85" width="95" height="26" rx="4"></rect>
      <rect x="150" y="85" width="90" height="26" rx="4"></rect>
      <rect x="280" y="40" width="95" height="26" rx="4"></rect>
      <rect x="280" y="130" width="95" height="26" rx="4"></rect>
      <rect x="415" y="85" width="85" height="26" rx="4"></rect>
      <rect x="535" y="85" width="105" height="26" rx="4"></rect>
    </g>
    <g fill="var(--ink)" text-anchor="middle">
      <text x="67" y="102">fetch</text><text x="195" y="102">clean_data</text>
      <text x="327" y="57">build_index</text><text x="327" y="147">train_model</text>
      <text x="457" y="102">evaluate</text><text x="587" y="102">write_report</text>
    </g>
    <g stroke="var(--muted)" fill="none">
      <path d="M115 98 L148 98"></path>
      <path d="M240 92 L278 60"></path><path d="M240 104 L278 140"></path>
      <path d="M375 58 L414 92"></path><path d="M375 140 L414 104"></path>
      <path d="M500 98 L533 98"></path>
    </g>
    <text x="330" y="185" text-anchor="middle" fill="var(--muted)" font-size="8">edges point producer -> consumer; a valid run follows the arrows</text>
  </g>
</svg>
^ The plan is a graph with a shape, and that shape — not the order lines appear in the file — dictates what can run when. `evaluate` cannot start until two separate branches both finish; no linear reading of the file encodes that.

### Kahn's algorithm: run what is ready

The topological sort is mechanical. Count each task's unfinished dependencies; run any task with none; when a task finishes, decrement its dependents' counts; repeat.

```
# dag.py:42-61 — COMPLETE (Kahn's algorithm; ok is False on a cycle)
def topo_order(tasks):
    """Kahn's algorithm. Returns (order, ok): ok is False if a cycle blocks completion."""
    indeg = {t: len(spec["deps"]) for t, spec in tasks.items()}
    dependents = {t: [] for t in tasks}
    for t, spec in tasks.items():
        for d in spec["deps"]:
            dependents[d].append(t)

    ready = sorted(t for t, n in indeg.items() if n == 0)  # sorted -> deterministic
    order = []
    while ready:
        t = ready.pop(0)
        order.append(t)
        for dep in sorted(dependents[t]):
            indeg[dep] -= 1
            if indeg[dep] == 0:
                ready.append(dep)
        ready.sort()
    ok = len(order) == len(tasks)  # fewer than all -> a cycle stranded the rest
    return order, ok
```

The `ready` queue starts with `fetch_sources`, the only task with zero dependencies. Running it unlocks `clean_data`, which unlocks `build_index` and `train_model`, and so on down the diamond. Sorting `ready` at each step makes the order deterministic — with two tasks ready at once, the lexicographically smaller runs first — so the same plan always yields the same order, which matters for reproducibility. The final `ok` check is the cycle detector, and it is nearly free: if the algorithm scheduled fewer tasks than exist, some tasks never reached zero dependencies, which can only happen inside a cycle.

### The cost of the wrong order: violations

A violation is a task scheduled before one of its dependencies. Count them by position in the order.

```
# dag.py:71-79 — COMPLETE (dependencies broken by an order: consumer before producer)
def violations(tasks, order):
    """Dependencies broken by running tasks in `order`: a task placed before a dep of it."""
    position = {t: i for i, t in enumerate(order)}
    broken = []
    for t, spec in tasks.items():
        for d in spec["deps"]:
            if position[t] < position[d]:  # consumer runs before producer
                broken.append((t, d))
    return sorted(broken)
```

Run it on both orders and the difference is total:

```
# $ python3 dag.py --violations
#   listed order: 6 violation(s)
#      build_index    ran before its dependency clean_data
#      clean_data     ran before its dependency fetch_sources
#      evaluate       ran before its dependency build_index
#      evaluate       ran before its dependency train_model
#      train_model    ran before its dependency clean_data
#      write_report   ran before its dependency evaluate
#   topological order: 0 violation(s)
```

run: 2026-08-26 · deterministic · `python3 dag.py --violations`

Six dependencies, six violations under the listed order — every single edge broken, because the listed order is the reverse of a valid one. The topological order breaks zero. Each of those six lines is a concrete failure at runtime: `evaluate` ran before `build_index`, so it evaluated against an index that did not exist; `write_report` ran first, reporting on an evaluation that had not happened. A naive scheduler would not raise a single error running this; it would just produce a report built on nothing.

<svg viewBox="0 0 700 150" role="img" aria-label="Two horizontal bars showing dependency violations. Listed order: a full bar at 6 violations, all six edges broken. Topological order: an empty bar at 0.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="20" fill="var(--muted)">dependencies broken (of 6 total)</text>
    <text x="20" y="62" fill="var(--ink)">listed order</text>
    <rect x="160" y="50" width="420" height="20" fill="var(--s2)"></rect><text x="588" y="65" fill="var(--s2)" font-size="9">6 / 6</text>
    <text x="20" y="102" fill="var(--ink)">topological</text>
    <rect x="160" y="90" width="3" height="20" fill="var(--s1)"></rect><text x="170" y="105" fill="var(--s1)" font-size="9">0 / 6</text>
    <text x="160" y="132" fill="var(--muted)" font-size="8">every broken edge is a subagent consuming an input its producer has not made</text>
  </g>
</svg>
^ The listed order breaks all six dependencies; the topological order breaks none. The gap is not a performance difference — it is the difference between six subagents running on real inputs and six running on absent or stale ones.

**A plan's dependencies, not its authoring order, decide what can run when: schedule by a topological sort so every producer finishes before its consumer, because a scheduler that ignores dependencies does not crash — it silently feeds subagents inputs that are missing or stale.**

### The second duty: catch the cycle

A scheduler that only orders acyclic plans is half a scheduler. Hand it a cyclic plan and it must report the impossibility, not spin.

```
# $ python3 dag.py --cycle
#   tasks: a->c, b->a, c->b
#   scheduled: (nothing -- every task waits on another)
#   completable: False
#   stranded in the cycle: ['a', 'b', 'c']
```

run: 2026-08-26 · deterministic · `python3 dag.py --cycle`

The stranded set is just the tasks the sort could never place — everything the cycle swallowed:

```
# dag.py:64-66 — COMPLETE (the tasks a topo sort could never schedule)
def stranded_by_cycle(tasks, order):
    """Tasks a topological sort could never schedule -- the ones caught in a cycle."""
    return sorted(set(tasks) - set(order))
```

<svg viewBox="0 0 700 170" role="img" aria-label="Three nodes a, b, c in a triangle with arrows forming a loop: a points to c, c points to b, b points to a. Every node has an incoming edge, so none can ever start. Beside it, the diamond plan has a clear entry node with no incoming edge.">
  <g font-family="var(--mono)" font-size="10">
    <text x="20" y="18" fill="var(--muted)">a cyclic plan: every task waits on another, so none can start</text>
    <g fill="var(--panel)" stroke="var(--s2)"><circle cx="160" cy="70" r="22"></circle><circle cx="260" cy="130" r="22"></circle><circle cx="360" cy="70" r="22"></circle></g>
    <g fill="var(--ink)" text-anchor="middle"><text x="160" y="74">a</text><text x="260" y="134">b</text><text x="360" y="74">c</text></g>
    <g stroke="var(--s2)" fill="none">
      <path d="M342 82 L178 82"></path>
      <path d="M168 91 L248 121"></path>
      <path d="M272 121 L352 91"></path>
    </g>
    <text x="160" y="60" text-anchor="middle" fill="var(--s2)" font-size="8">a<-c</text>
    <text x="410" y="74" fill="var(--muted)" font-size="8">a needs c, c needs b, b needs a</text>
    <text x="410" y="118" fill="var(--s2)" font-size="8">no zero-dependency task exists -></text>
    <text x="410" y="130" fill="var(--s2)" font-size="8">ready queue starts empty -> report cycle</text>
  </g>
</svg>
^ Every node has an incoming edge, so no task ever reaches zero unfinished dependencies and the ready queue never fills. The diamond plan had `fetch_sources` as an entry point with no dependencies; a cycle has none, and that absence is exactly what the length check detects.

In the cyclic plan `a` needs `c`, `c` needs `b`, `b` needs `a` — a loop. No task ever has zero unfinished dependencies, so Kahn's `ready` queue starts empty and stays empty; nothing schedules. The `ok` flag comes back False and the stranded set names all three tasks. This is the graceful failure: a real orchestrator would surface "these tasks form a dependency cycle, fix the plan" instead of deadlocking with subagents all waiting on each other forever. The same length check that costs nothing on a valid plan is the cycle detector on a broken one.

### The self-test

The `--check` mode asserts all of it: the topological order is valid and violation-free, the listed order is not, every dependency is respected by position, and the cyclic plan is caught.

```
# $ python3 dag.py --check
#   topological order completes and has 0 violations = True (6 tasks)
#   the listed order breaks dependencies = True (6 violations)
#   every task follows all its dependencies in the topo order = True
#   the cyclic plan is reported uncompletable (not deadlocked) = True
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 dag.py --check`

The `all_after` line is the correctness anchor: it independently re-checks, by position, that every task in the topo order sits after each of its dependencies — a second proof that does not trust the algorithm's own output. The `cycle_caught` line guards the second duty, so a refactor that made the scheduler loop on a cycle instead of reporting it would fail here rather than hang in production.

### The running tally

| order | dependencies broken | what runs on bad data | completable |
|---|---|---|---|
| listed (as written) | 6 of 6 | every task | — |
| topological | 0 of 6 | none | yes |
| cyclic plan | — | — | no (reported) |

The first two rows are the whole point: the same six tasks, the same dependencies, and the only variable is the order — yet one breaks every constraint and the other breaks none. The third row is the reminder that "produce an order" is not the only job; recognising when no order exists is the other half, and a scheduler that hangs on a cycle has failed as surely as one that runs tasks out of order.

### What we did not settle

Real schedulers do more than order. They parallelise: `build_index` and `train_model` have no dependency between them, so a good orchestrator runs them at once rather than serially, and the topological order is then a set of levels, not a single line. They handle partial failure: if `train_model` fails, `evaluate` and `write_report` must not run on a missing input, which means the scheduler prunes the dependent subtree rather than marching on. And dependencies can be dynamic — a task discovered at runtime adds edges — so the graph is rebuilt as work reveals itself. The core here, order by dependencies and detect cycles, is the foundation all of that sits on.

## Build

The practice in one paragraph: model any fan-out plan as a task DAG with an edge from each producer to each consumer; schedule with a topological sort — run only tasks whose dependencies are all complete — never by the order tasks appear in the plan; verify zero violations before running anything; and always run the cycle check, reporting an uncompletable plan by name instead of letting subagents deadlock. Break ties deterministically so the schedule is reproducible.

We opened on the two orders. The number that proves the scheduler is safe is the violation count:

```
# modules/orchestration-and-governance/code/govern-inter-04/ — COMPLETE, run from that directory
$ python3 dag.py --violations
  listed order: 6 violation(s)
  topological order: 0 violation(s)
```

Now do it to your own plan. Take a real multi-step task you would fan out — data prep, indexing, evaluation, reporting — write its dependencies, and topologically sort it. Your number to beat is not that the plan runs; it is **zero dependency violations in your chosen order, verified independently of the scheduler that produced it**, plus a deliberately cyclic version that your scheduler reports rather than hangs on. Bring back the violation counts for both the authored order and the topological one. Good luck.

## Definition of done

- [ ] A plan modelled as a task DAG with producer→consumer dependency edges
- [ ] A topological sort (Kahn's algorithm) producing a dependency-respecting order
- [ ] Deterministic tie-breaking so the schedule is reproducible
- [ ] Dependency violations counted for the authored order and the topological order
- [ ] Independent verification that every task follows its dependencies by position
- [ ] A cyclic plan the scheduler reports as uncompletable, naming the stranded tasks
- [ ] `python3 dag.py --check` printing SELF-TEST PASS: topo valid, listed bad, all-after, cycle caught
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What does a dependency edge promise, and what concretely goes wrong at runtime when a consumer is scheduled before its producer?
2. Describe Kahn's algorithm in two sentences, and explain how the same run detects a cycle for free.
3. The listed order broke all six dependencies while the topological order broke none. Why is the naive failure more dangerous than a crash?
4. Why must a scheduler report a cyclic plan rather than simply attempt to run it, and what does "stranded" mean here?
5. Your own plan was ordered two ways. What were the violation counts, and how did you verify the topological order independently of the algorithm that produced it?

## External resources

- Arthur Kahn, *Topological sorting of large networks* (1962) — the original algorithm — my summary: the ready-queue method this module implements, still the standard for scheduling with dependencies; read it for the algorithm in its original framing and why the in-degree bookkeeping is the whole trick.
- Apache Airflow, *DAGs and task dependencies* documentation — my summary: a production workflow engine built entirely on the task-DAG model, with parallel levels, retries, and failure pruning; read it for the real version of the scheduler this module cores out, and the operational duties beyond ordering.
- This hub, *govern-inter-03* — modules/orchestration-and-governance/govern-inter-03.md — my summary: the fan-out partition contract for splitting work across subagents; read it for the step before this one — how work is divided — where this module handles how the divided pieces must be ordered.
