---
id: toolbudget-inter-01
title: Cap tool calls per tool, not just total steps — or one runaway tool eats the whole run and starves the ones the task needs
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: An agent loop needs a budget or it runs forever, and the obvious one is a total cap on tool calls. That bounds the run but not where the budget goes. Agents get stuck in single-tool loops — searching again and again for something they never find, retrying a failing call — and a runaway tool, issued greedily up front, can consume the entire total budget before the agent reaches the tools the task actually requires. The run stops at its cap having done nothing but search, and the read and write the task needed never happened. A per-tool cap fixes the distribution: give each tool its own ceiling so no single tool can monopolize the run, and once search hits its cap, further search calls are refused (returned as an observation, so the agent moves on) and the budget it would have burned is preserved for the other tools. The total cap bounds the run; the per-tool caps bound each tool within it. On a fixture where the agent wants 12 searches plus one read and one write against a total budget of 10 with search capped at 5, the total-only budget pours all 10 into search (read and write get 0, the task fails), while the per-tool cap bounds search to 5 and leaves room for read and write to each run once (7 calls total, task can succeed).
eli5: Give a kid $10 for a shopping trip and a list that needs milk, bread, and eggs, and if they blow all $10 on candy in the first aisle, they come home with no milk, bread, or eggs — the budget was spent, just all in one place. A total limit doesn't guarantee the important things get bought. Put a small cap on candy specifically, and there's money left for the things on the list. Same with an agent: limit not just how many tool calls it makes, but how many of any one tool, so a loop in one tool can't crowd out the tools the job actually needs.
---

## Why this module

A total budget bounds how much an agent can do but not how it spends, and agents fail by over-spending in one place — so a run can hit its cap having burned everything on a single looping tool and never touched the tools the task required.

Every agent loop needs a stopping condition, and the simplest sufficient one is a total cap: allow N tool calls, then stop. It guarantees termination, which is the first thing you need. But termination is not success, and a total cap says nothing about the *distribution* of those N calls across the tools. That matters because the characteristic agent failure is not doing too much overall — it is doing the same thing too many times: searching repeatedly for a result it never finds, retrying a call that keeps failing, re-reading a file hoping for a different answer. When an agent falls into one of these single-tool loops early, and issues those calls greedily before it gets to the rest of its plan, the loop drinks the whole budget. The run terminates exactly as designed, at N calls, but all N went to one tool, and the tools the task genuinely needed — the read that gathers the input, the write that produces the output — were still queued when the budget ran dry.

**A total-only call budget bounds the run but not the allocation, so a runaway single-tool loop issued greedily can consume the entire budget and leave the tools the task requires unrun — the run terminates without ever doing the work.**

A per-tool cap fixes the allocation directly. Alongside the total budget, give each tool its own ceiling: search may be called at most k times, no matter what. When search hits k, the harness refuses further search calls — returning the refusal as an observation, "search budget exhausted," so the agent reads it and moves on to something else — and the budget those extra searches would have consumed is preserved for the other tools. The total cap still bounds the run as a whole; the per-tool caps guarantee that the run can spread across the tools a task needs instead of pooling in one. The two are complementary and both are necessary: the total alone lets one tool starve the rest, and per-tool caps alone (without a total) could still let many tools collectively run forever. This module allocates the same demand under both policies and shows the required tools starve under one and run under the other.

## Concepts

**A total-only budget** serves tool calls in the order requested until the total runs out. If the first tool requested wants more calls than the whole budget, it takes all of it.

```python filename=modules/agent-harness/code/toolbudget-inter-01/toolbudget.py:42-49 COMPLETE
def allocate_total_only(intended, order, budget):
    """Greedy allocation against a single total budget: serve tools in request order until the budget runs out."""
    alloc, remaining = {}, budget
    for tool in order:
        take = min(intended.get(tool, 0), remaining)
        alloc[tool] = take
        remaining -= take
    return alloc
```

**A per-tool cap** limits each tool to its own ceiling first, then draws on the shared total. A runaway tool is bounded to its cap, leaving the rest of the total for other tools.

```python filename=modules/agent-harness/code/toolbudget-inter-01/toolbudget.py:52-60 COMPLETE
def allocate_per_tool(intended, order, caps, budget):
    """Allocation with a per-tool cap: each tool is limited to its cap, then the total budget, in request order."""
    alloc, remaining = {}, budget
    for tool in order:
        want = min(intended.get(tool, 0), caps.get(tool, budget))
        take = min(want, remaining)
        alloc[tool] = take
        remaining -= take
    return alloc
```

**Required-tool coverage** is the real success test: did every tool the task needs get to run at least once? A run that starves a required tool fails no matter how many calls it made.

<svg role="img" aria-label="A total-only budget is one bucket that search drains completely; per-tool caps are separate buckets so search is bounded and read and write keep theirs" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">total-only: one bucket, search drains it</text>
  <rect x="20" y="18" width="120" height="26" fill="none" stroke="var(--line)"/><rect x="20" y="18" width="120" height="26" fill="var(--s2)" opacity="0.6"/>
  <text x="52" y="35" fill="var(--panel)" font-size="8">search fills all 10</text>
  <text x="150" y="26" fill="var(--muted)" font-size="7">read: 0</text><text x="150" y="40" fill="var(--muted)" font-size="7">write: 0 (starved)</text>
  <line x1="6" y1="52" x2="292" y2="52" stroke="var(--grid)"/>
  <text x="6" y="66" fill="var(--muted)" font-size="8">per-tool: separate buckets</text>
  <rect x="20" y="72" width="60" height="20" fill="var(--s2)"/><text x="30" y="86" fill="var(--panel)" font-size="7">search 5/5</text>
  <rect x="86" y="72" width="24" height="20" fill="var(--s1)"/><text x="90" y="86" fill="var(--panel)" font-size="7">read 1</text>
  <rect x="116" y="72" width="24" height="20" fill="var(--s1)"/><text x="120" y="86" fill="var(--panel)" font-size="7">write 1</text>
  <text x="150" y="86" fill="var(--muted)" font-size="7">required tools run</text>
</svg>
^ A total-only budget is one bucket the runaway search drains completely, starving read and write; per-tool caps are separate buckets, so search is bounded to its cap and read and write keep theirs.

**Budget each tool, not just the total, so a loop in one tool cannot monopolize the run — the total cap bounds the whole run and the per-tool caps guarantee it can still reach the tools the task requires.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/toolbudget-inter-01/toolbudget.py

The fixture is an agent that wants 12 searches plus one read and one write, a total budget of 10, and a per-tool cap of 5 on search.

```json filename=modules/agent-harness/code/toolbudget-inter-01/toolbudget.json:3-7 COMPLETE
  "intended_calls": {"search": 12, "read": 1, "write": 1},
  "request_order": ["search", "read", "write"],
  "total_budget": 10,
  "per_tool_caps": {"search": 5, "read": 3, "write": 3},
  "required": ["read", "write"]
```

Run `--allocate` to distribute the calls under each policy.

```text filename=--allocate
ALLOCATE — total-only budget vs per-tool caps (total budget = 10)
--------------------------------------------------------------
  tool      intended   total-only   per-tool (cap)
  search    12         10           5 (5)
  read      1          0            1 (3)
  write     1          0            1 (3)
  TOTAL     14         10           7
--------------------------------------------------------------
  total-only pours the whole budget into search; per-tool caps leave room for read and write.
```

Under the total-only budget, search — requested first and wanting 12 calls — takes all 10 the budget allows, and read and write get 0. The run made ten tool calls and hit its cap, so by the "we bounded the run" standard it succeeded; by the "did the task get done" standard it failed completely, because read and write, the tools that gather the input and produce the output, never ran. Under the per-tool policy, search is capped at 5, so it takes 5 and stops; read takes 1, write takes 1, for 7 calls total — under the budget of 10, with room to spare. The runaway loop was contained to 5 wasted searches instead of 10, and the 5 calls it did not get went to the tools that needed them. Same demand, same total budget; the only difference is that the per-tool cap refused to let one tool have all of it. The total budget was never the problem — 10 calls is plenty for one read and one write — the problem was letting search reach them all first.

<svg role="img" aria-label="Total-only allocates 10 to search and 0 to read and write; per-tool allocates 5 to search, 1 to read, 1 to write" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">calls allocated per tool</text>
  <text x="6" y="30" fill="var(--muted)" font-size="8">total-only</text>
  <rect x="70" y="22" width="200" height="12" fill="var(--s2)"/><text x="120" y="32" fill="var(--panel)" font-size="7">search 10</text>
  <text x="70" y="46" fill="var(--muted)" font-size="7">read 0 · write 0 — starved, task fails</text>
  <line x1="6" y1="56" x2="292" y2="56" stroke="var(--grid)"/>
  <text x="6" y="72" fill="var(--muted)" font-size="8">per-tool</text>
  <rect x="70" y="64" width="100" height="12" fill="var(--s2)"/><text x="100" y="74" fill="var(--panel)" font-size="7">search 5</text>
  <rect x="70" y="78" width="20" height="12" fill="var(--s1)"/><text x="94" y="88" fill="var(--muted)" font-size="7">read 1</text>
  <rect x="70" y="92" width="20" height="12" fill="var(--s1)"/><text x="94" y="102" fill="var(--muted)" font-size="7">write 1 — task can succeed</text>
</svg>
^ The total-only budget gives search all 10 calls and read and write none; the per-tool cap bounds search to 5 and leaves the budget for read and write to run once each.

## Build

The allocation is only a means; the end is whether the task's tools ran. Run `--coverage`.

```text filename=--coverage
COVERAGE — which tools run, and whether the required tools are covered
--------------------------------------------------------------
  required tools: ['read', 'write']
  total-only:  ran ['search']   required covered? False
  per-tool:    ran ['read', 'search', 'write']   required covered? True
```

Under the total-only budget the run touched exactly one tool — search — and both required tools are uncovered, so the task cannot complete regardless of how the ten searches went. Under the per-tool policy the run touched all three, and both required tools ran, so the task can complete. This is the metric that matters: not "did we stay under budget" (both did) but "did the run reach the tools the task needs" (only one did). It reframes the budget's job. A budget is not only a spending limit; it is a *scheduling* decision about what a bounded run is allowed to prioritize, and a total-only budget implicitly lets whichever tool asks first set that priority. Per-tool caps take the priority decision back from the runaway loop: by reserving headroom for every tool (or at least bounding the greedy ones), they ensure the total budget is spent across the plan rather than dumped into its first stuck step. The same principle appears wherever a shared resource meets a greedy consumer — it is fair-share scheduling, quotas, rate-limit-per-key — applied to an agent's own tool calls so that no single tool's loop can crowd out the work the run exists to do.

<svg role="img" aria-label="Under total-only only search runs and the required read and write are missing; under per-tool all three run and the required tools are covered" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">tools that ran (★ = required)</text>
  <text x="6" y="32" fill="var(--muted)" font-size="8">total-only</text>
  <rect x="80" y="22" width="40" height="16" fill="var(--s2)"/><text x="86" y="34" fill="var(--panel)" font-size="7">search</text>
  <rect x="124" y="22" width="40" height="16" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/><text x="128" y="34" fill="var(--muted)" font-size="7">★read ✗</text>
  <rect x="168" y="22" width="40" height="16" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/><text x="172" y="34" fill="var(--muted)" font-size="7">★write ✗</text>
  <text x="214" y="34" fill="var(--s2)" font-size="7">task fails</text>
  <text x="6" y="66" fill="var(--muted)" font-size="8">per-tool</text>
  <rect x="80" y="56" width="40" height="16" fill="var(--s2)"/><text x="86" y="68" fill="var(--panel)" font-size="7">search</text>
  <rect x="124" y="56" width="40" height="16" fill="var(--s1)"/><text x="130" y="68" fill="var(--panel)" font-size="7">★read</text>
  <rect x="168" y="56" width="40" height="16" fill="var(--s1)"/><text x="172" y="68" fill="var(--panel)" font-size="7">★write</text>
  <text x="214" y="68" fill="var(--s1)" font-size="7">task can succeed</text>
  <text x="6" y="92" fill="var(--muted)" font-size="8">coverage of the required tools, not staying under budget, is the real success test</text>
</svg>
^ Total-only leaves both required tools (read, write) unrun, so the task fails; per-tool caps let all three tools run, covering the required ones so the task can succeed.

## Definition of done

The self-test pins the failure and the fix: total-only lets one tool consume the whole budget and starves the required tools, while per-tool caps bound each tool, cover the required tools, and stay within the total.

```python filename=modules/agent-harness/code/toolbudget-inter-01/toolbudget.py:112-125 COMPLETE
    one_tool_hogs = max(to.values()) == budget
    print("  total-only lets one tool consume the entire budget = %s (search=%d of %d)" % (one_tool_hogs, to["search"], budget))

    required_starved = not required_covered(to, req)
    print("  the required tools are starved under total-only = %s (ran %s)" % (required_starved, sorted(tools_run(to))))

    caps_bound_each = all(pt[t] <= caps[t] for t in pt)
    print("  per-tool caps bound every tool = %s (search=%d <= cap %d)" % (caps_bound_each, pt["search"], caps["search"]))

    required_covered_pt = required_covered(pt, req)
    print("  the required tools all run under per-tool caps = %s (ran %s)" % (required_covered_pt, sorted(tools_run(pt))))

    within_budget = sum(pt.values()) <= budget
    print("  per-tool allocation still respects the total budget = %s (%d <= %d)" % (within_budget, sum(pt.values()), budget))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the total-only budget lets one tool consume it and starves the required tools; per-tool caps prevent it
----------------------------------------------------------------------------------------------------------------------
  total-only lets one tool consume the entire budget = True (search=10 of 10)
  the required tools are starved under total-only = True (ran ['search'])
  per-tool caps bound every tool = True (search=5 <= cap 5)
  the required tools all run under per-tool caps = True (ran ['read', 'search', 'write'])
  per-tool allocation still respects the total budget = True (7 <= 10)
```

**Done means the per-tool guardrail is proven: the total-only budget lets search consume all 10 calls and starves both required tools (only search ran), while per-tool caps bound search to 5, let read and write each run once (all three tools covered, required tools included), and still finish within the total budget at 7 of 10 calls.**

## Boss fight

Predict the two ways per-tool caps go wrong if you treat them as a set-and-forget number. It is tempting to pick one cap per tool and never revisit it.

The first trap is that a cap that is too tight cripples a legitimate need as surely as no cap invites a runaway. Some tasks genuinely require many calls of one tool — a research task that must search twenty distinct sub-questions, a batch job that must read a hundred files — and a search cap of 5 chosen to stop a loop will strangle the task that legitimately needs 20. The cap cannot distinguish "searched 12 times because it is looping" from "searched 12 times because the task has 12 things to look up." So a fixed per-tool cap trades one failure (runaway) for another (legitimate work blocked), and the real fix is usually not a hard cap but loop *detection* — noticing that the repeated calls are identical or making no progress (the same query, the same empty result) — combined with a generous cap as a backstop. A cap bounds the damage; detecting the no-progress loop is what tells a real need apart from a stuck one, so the two belong together: detect the loop to stop wasted calls early, keep the cap so an undetected loop still cannot run away.

```python filename=modules/agent-harness/code/toolbudget-inter-01/toolbudget.py:68-70 COMPLETE
def required_covered(alloc, required):
    """Did every required tool get to run at least once?"""
    return all(alloc.get(t, 0) > 0 for t in required)
```

The second trap is that refusing a call is only safe if the agent can act on the refusal, and a badly-handled cap creates its own failure. When search hits its cap, the harness must return the refusal *as an observation* — "search budget exhausted, N calls used" — so the model reads it and adapts (tries a different tool, concludes with what it has, or reports it is blocked). Silently dropping the call, or raising an exception that aborts the turn, is worse than no cap: the agent either spins re-issuing a call that vanishes, or the run dies over a guardrail that was supposed to protect it. And the cap should ideally degrade gracefully rather than hard-stop — warn the model as it approaches the limit so it can prioritize its remaining calls, the way a token budget is more useful surfaced to the model than sprung on it. So per-tool budgeting is not just a counter that blocks calls; it is a piece of the agent's feedback loop, and its refusals must be observations the agent can reason about, the same discipline as returning any tool error as an observation rather than an exception. The guardrail works only if the agent can see it working.

**Cap tool calls per tool, not only in total, so a runaway single-tool loop cannot consume the whole run and starve the tools the task requires — the total budget bounds the run and the per-tool caps guarantee it can spread across the plan — but a fixed cap cannot tell a legitimate high-volume need from a loop, so pair it with no-progress loop detection (a generous cap as backstop, detection to stop wasted calls early), and surface an exhausted cap to the agent as an observation it can adapt to, never a silent drop or an exception, or the guardrail becomes its own failure.**

## External resources

Agent-framework documentation on tool-call limits, per-tool quotas, and loop/no-progress detection — the practical mechanisms for bounding a run's tool usage and for surfacing budget state to the model.

Any reference on fair-share scheduling and resource quotas (per-key rate limits, cgroup limits, weighted fair queueing) — the general principle that a shared budget needs per-consumer bounds to stop one greedy consumer from monopolizing it.

The companion "cap the run's token budget, not just its step count" and "bound the agent loop and detect no-progress" modules — the first bounds a different resource (tokens) at the run level, the second is the loop detection this module's boss fight pairs with the cap, so together they cover bounding a run by steps, by tokens, by per-tool calls, and by progress.
