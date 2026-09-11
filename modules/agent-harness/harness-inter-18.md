---
id: harness-inter-18
title: Cap the sub-agent recursion depth — or a task that never decides it is done spawns an exponential swarm
topic: agent-harness
level: intermediate
status: ready
time: 19 min
summary: An agent that decomposes a hard task into sub-tasks, each handled by a sub-agent, builds a tree of agents. If every task spawns b sub-tasks, there are b agents at depth 1, b² at depth 2, bᵈ at depth d — exponential in depth. That is fine while the decomposition converges and leaf tasks stop spawning. It is a disaster when the decomposition never decides it is done: a task splits into sub-tasks that are no simpler, each splitting again. With no depth cap the harness launches bᵈ agents at depth d — hundreds, then thousands — burning budget and rate limits, a self-inflicted denial of service from one request. A depth cap turns the unbounded tree into a bounded one: the total is the geometric sum 1 + b + … + b^D, fixed no matter how badly the decomposition misbehaves. On branching 3, a cap at depth 3 is 40 agents; an uncapped drift to depth 8 is 9841 — 246× more, 6561 at the last level alone.
eli5: If one helper is allowed to hire three more helpers whenever a job feels hard, and those each hire three more, the crowd doubles and triples until you have thousands of helpers and a giant bill — all from one job that nobody ever finished. A depth limit says "after a few rounds of hiring, you must do the work yourself." It keeps the crowd small even when the job keeps feeling too hard.
---

## Why this module

A single agent loop can only waste time in a line; a recursive agent that spawns sub-agents can waste it in a tree, and a tree grows exponentially.

When an agent handles a hard task by decomposing it into sub-tasks and handing each to a sub-agent, the sub-agents can decompose further, and so on. Each level multiplies the agent count by the branching factor: three sub-tasks per task means three agents at depth 1, nine at depth 2, twenty-seven at depth 3. If the leaf tasks are genuinely simpler and stop spawning, the tree is shallow and the total is modest. But if the decomposition never converges — each sub-task is as hard as its parent and splits again — nothing stops the growth, and a harness with no depth limit will keep launching agents until it exhausts your budget, your rate limits, or the provider's patience. One request becomes a swarm.

**A recursive spawn without a depth cap is an exponential blowup waiting for a decomposition that fails to converge — and decompositions fail to converge all the time.**

The fix is a depth cap: refuse to spawn a sub-agent past a maximum depth, forcing a task at the cap to solve itself or fail rather than split. That converts an unbounded tree into a geometric sum — a fixed, known number of agents regardless of how badly the decomposition behaves. This module computes the agent count by depth and shows the cap contain the explosion.

## Concepts

The **branching factor** b is how many sub-agents each task spawns. **Depth** is the level in the tree, with the root at depth 0.

The **agent count at depth d** is bᵈ — each level multiplies the previous by b. This is the exponential: it is not that the tree is large, it is that it multiplies, so every extra level of runaway costs b times the last.

The **total agents** down to a maximum depth is the geometric sum 1 + b + b² + … + b^D, with closed form (b^(D+1) − 1) / (b − 1). The point of the closed form is that it is finite and fixed the moment you fix D.

The **depth cap** is the harness rule: no spawning beyond depth D. It is the tree analogue of the iteration limit on a plain agent loop — the loop limit bounds a line of steps, the depth cap bounds a tree of agents. Without either, a non-terminating process runs until it exhausts a resource.

The trap is assuming the decomposition will converge because it usually does. "Usually" is not "always," and the failure mode is not graceful degradation — it is exponential, so by the time you notice the swarm it is already enormous. The cap is cheap insurance against a tail event that is catastrophic when it hits.

**A depth cap bounds the whole tree to a geometric sum, converting an exponential blowup from a non-converging decomposition into a bounded, debuggable failure.**

The tree fans out by the branching factor at every level, so the depth cap is a horizontal line that stops the widening before it runs away.

<svg role="img" aria-label="A tree with one root, three children, nine grandchildren, and a dashed cap line below which no further children are spawned" viewBox="0 0 300 120" width="300" height="120">
  <circle cx="150" cy="18" r="4" fill="var(--s2)"/>
  <circle cx="90" cy="48" r="4" fill="var(--s2)"/><circle cx="150" cy="48" r="4" fill="var(--s2)"/><circle cx="210" cy="48" r="4" fill="var(--s2)"/>
  <line x1="150" y1="18" x2="90" y2="48" stroke="var(--line)" stroke-width="1"/><line x1="150" y1="18" x2="150" y2="48" stroke="var(--line)" stroke-width="1"/><line x1="150" y1="18" x2="210" y2="48" stroke="var(--line)" stroke-width="1"/>
  <g fill="var(--s2)">
    <circle cx="70" cy="78" r="3"/><circle cx="90" cy="78" r="3"/><circle cx="110" cy="78" r="3"/>
    <circle cx="130" cy="78" r="3"/><circle cx="150" cy="78" r="3"/><circle cx="170" cy="78" r="3"/>
    <circle cx="190" cy="78" r="3"/><circle cx="210" cy="78" r="3"/><circle cx="230" cy="78" r="3"/>
  </g>
  <line x1="20" y1="92" x2="285" y2="92" stroke="var(--s1)" stroke-width="1.5" stroke-dasharray="4 2"/>
  <text x="25" y="104" fill="var(--s1)" font-size="8">depth cap: no spawning below this line</text>
</svg>
^ Each level triples in width; the dashed cap line is what stops the tree from fanning out into the exponentially wider levels beneath it.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/harness-inter-18/recursion.py

The fixture is a branching factor, a depth cap, and the depth an uncapped run drifted to before anyone noticed.

```json filename=modules/agent-harness/code/harness-inter-18/tree.json:1-6 COMPLETE
{
  "_meta": "An agent that decomposes a task into sub-agents: each task spawns `branching` sub-tasks, which each spawn `branching` more, and so on. depth_cap is the maximum recursion depth the harness allows (the root is depth 0). runaway_depth is how deep an UNCAPPED run drifted before someone noticed -- when a decomposition never decides it is done. The question: how many sub-agents does each spawn, and does the cap actually bound it?",
  "branching": 3,
  "depth_cap": 3,
  "runaway_depth": 8
}
```

The counts are three tiny functions: agents at a depth, the total down to a depth, and the closed-form geometric sum.

```python filename=modules/agent-harness/code/harness-inter-18/recursion.py:40-52 COMPLETE
def agents_at_depth(b, d):
    """How many agents live at depth d: b^d."""
    return b ** d


def total_agents(b, max_depth):
    """All agents from the root (depth 0) down to max_depth: the geometric sum 1 + b + ... + b^max_depth."""
    return sum(b ** d for d in range(max_depth + 1))


def geometric_sum(b, max_depth):
    """Closed form of the total: (b^(max_depth+1) - 1) / (b - 1)."""
    return (b ** (max_depth + 1) - 1) // (b - 1)
```

Run `--tree` and watch the count multiply by level.

```text filename=--tree
TREE — agents at each depth (branching 3, cap at depth 3)
----------------------------------------------------------
  depth 0:       1 agents
  depth 1:       3 agents
  depth 2:       9 agents
  depth 3:      27 agents  <- CAP: no spawning past here
  depth 4:      81 agents  (only reached without a cap)
  depth 5:     243 agents  (only reached without a cap)
  depth 6:     729 agents  (only reached without a cap)
  depth 7:    2187 agents  (only reached without a cap)
  depth 8:    6561 agents  (only reached without a cap)
----------------------------------------------------------
  each level multiplies the count by 3; the cap stops it at depth 3.
```

Each depth is three times the one above — 1, 3, 9, 27, then 81, 243, 729, and on. The cap draws the line after depth 3. Everything below it, up to 6561 agents at depth 8, exists only if the harness never says stop. A single unconverging task, left uncapped, reaches thousands of concurrent agents just by drifting a few levels deeper.

<svg role="img" aria-label="Agent count per depth grows 1, 3, 9, 27 up to the cap then continues exponentially to 6561 at depth 8" viewBox="0 0 300 130" width="300" height="130">
  <line x1="30" y1="15" x2="30" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="105" x2="285" y2="105" stroke="var(--grid)" stroke-width="1"/>
  <rect x="35" y="103" width="18" height="2" fill="var(--s2)"/>
  <rect x="60" y="102" width="18" height="3" fill="var(--s2)"/>
  <rect x="85" y="100" width="18" height="5" fill="var(--s2)"/>
  <rect x="110" y="96" width="18" height="9" fill="var(--s2)"/>
  <line x1="132" y1="15" x2="132" y2="105" stroke="var(--s1)" stroke-width="1" stroke-dasharray="3 2"/>
  <text x="108" y="26" fill="var(--s1)" font-size="7">cap (depth 3)</text>
  <rect x="140" y="90" width="18" height="15" fill="var(--s1)"/>
  <rect x="165" y="80" width="18" height="25" fill="var(--s1)"/>
  <rect x="190" y="62" width="18" height="43" fill="var(--s1)"/>
  <rect x="215" y="35" width="18" height="70" fill="var(--s1)"/>
  <rect x="240" y="18" width="18" height="87" fill="var(--s1)"/>
  <text x="228" y="14" fill="var(--s1)" font-size="7">6561</text>
  <text x="60" y="122" fill="var(--muted)" font-size="8">bounded left of the cap; exponential to the right</text>
</svg>
^ Left of the cap the bars are a handful of agents; right of it, where an uncapped run drifts, they climb exponentially to thousands at depth 8.

## Build

The totals view sums the tree down to the cap and down to the runaway depth for comparison.

```python filename=modules/agent-harness/code/harness-inter-18/recursion.py:68-76 COMPLETE
def totals_view(data):
    b, cap, run = data["branching"], data["depth_cap"], data["runaway_depth"]
    tc, tr = total_agents(b, cap), total_agents(b, run)
    print("TOTALS — total agents under the cap vs at the runaway depth")
    print("-" * 58)
    print("  capped at depth %d:   %6d agents" % (cap, tc))
    print("  runaway to depth %d:  %6d agents  (%dx more)" % (run, tr, tr // tc))
    print("-" * 58)
    print("  the cap turns an exponential swarm into a fixed budget.")
```

Sum it up with `--totals`.

```text filename=--totals
TOTALS — total agents under the cap vs at the runaway depth
----------------------------------------------------------
  capped at depth 3:       40 agents
  runaway to depth 8:    9841 agents  (246x more)
----------------------------------------------------------
  the cap turns an exponential swarm into a fixed budget.
```

Capped at depth 3 the whole tree is 40 agents — 1 + 3 + 9 + 27. Left uncapped to depth 8 it is 9841, more than 240 times larger, and it was still multiplying. The cap did not make the decomposition succeed; it made its failure cost 40 agents instead of ten thousand. That is the trade: a bounded, cheap failure you can debug, instead of a resource-exhausting swarm you have to firefight.

<svg role="img" aria-label="Total agents: capped tree 40, runaway tree 9841 — the runaway bar dwarfs the capped one" viewBox="0 0 300 100" width="300" height="100">
  <line x1="70" y1="12" x2="70" y2="75" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="75" x2="285" y2="75" stroke="var(--grid)" stroke-width="1"/>
  <rect x="70" y="22" width="2" height="14" fill="var(--s2)"/><text x="78" y="33" fill="var(--muted)" font-size="8">capped 40</text>
  <rect x="70" y="46" width="205" height="14" fill="var(--s1)"/><text x="150" y="57" fill="var(--panel)" font-size="8">runaway 9841 (246x)</text>
  <text x="70" y="92" fill="var(--muted)" font-size="8">the capped tree is a sliver of the runaway one</text>
</svg>
^ The capped total is a barely-visible sliver next to the runaway total — the cap is the difference between a 40-agent bill and a 9841-agent one.

## Definition of done

The self-test pins the exponential and the bound: each level multiplies by b, the capped total is the geometric sum, the runaway tree dwarfs it, the per-depth growth is exponential, and the entire capped tree is smaller than a single runaway level.

```python filename=modules/agent-harness/code/harness-inter-18/recursion.py:85-97 COMPLETE
    each_level_multiplies = all(agents_at_depth(b, d + 1) == b * agents_at_depth(b, d) for d in range(run))
    print("  each depth has b times the agents of the one above = %s" % each_level_multiplies)

    capped_is_geometric_sum = tc == geometric_sum(b, cap)
    print("  the capped total is the geometric sum = %s (%d = (b^%d-1)/(b-1))" % (capped_is_geometric_sum, tc, cap + 1))

    runaway_far_exceeds_capped = tr > tc * 100
    print("  the runaway tree dwarfs the capped one = %s (%d vs %d, %dx)" % (runaway_far_exceeds_capped, tr, tc, tr // tc))

    growth_is_exponential = agents_at_depth(b, run) == agents_at_depth(b, cap) * b ** (run - cap)
    print("  the per-depth count grows exponentially = %s (depth %d has %d agents)" % (growth_is_exponential, run, agents_at_depth(b, run)))

    whole_cap_tree_below_one_runaway_level = tc < agents_at_depth(b, run)
    print("  the entire capped tree is smaller than one runaway level = %s (%d < %d at depth %d)" % (whole_cap_tree_below_one_runaway_level, tc, agents_at_depth(b, run), run))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the cap bounds the tree to a geometric sum; uncapped growth is exponential
----------------------------------------------------------------------------------------------------
  each depth has b times the agents of the one above = True
  the capped total is the geometric sum = True (40 = (b^4-1)/(b-1))
  the runaway tree dwarfs the capped one = True (9841 vs 40, 246x)
  the per-depth count grows exponentially = True (depth 8 has 6561 agents)
  the entire capped tree is smaller than one runaway level = True (40 < 6561 at depth 8)
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  each_level_multiplies=True  capped_is_geometric_sum=True  runaway_far_exceeds_capped=True  growth_is_exponential=True  whole_cap_tree_below_one_runaway_level=True
```

**Done means the blowup is quantified against the bound: the capped tree is 40 agents while depth 8 alone is 6561, so the cap is provably the difference between a geometric sum and an exponential swarm.**

## Boss fight

A depth cap of 3 bounds this tree to 40. Predict whether raising the branching factor is safe as long as the depth cap holds. It is tempting to think the cap alone makes any branching safe.

The cap bounds the tree, but the bound is still exponential in the cap, so a large branching factor makes even a shallow capped tree huge. At branching 3 and cap 3 the tree is 40; at branching 10 and the same cap 3 it is 1 + 10 + 100 + 1000 = 1111. The depth cap prevents the unbounded runaway, but the total is a geometric sum in b, so both b and D need budgeting — a total-agent budget (fan-out limit) is the complementary control that caps the whole tree directly rather than just its depth. Real harnesses often use both: a depth cap and a global spawn count, whichever binds first.

The mirror-image mistake is capping so shallow that legitimate decompositions cannot finish. A cap of 1 forbids any sub-agent from decomposing at all, which breaks genuinely hierarchical tasks that need a few levels. The cap must be above the depth real work requires and below where runaway becomes expensive — the same tension as an agent loop's iteration limit, which must outlast honest work but still stop a stuck loop.

```python filename=modules/agent-harness/code/harness-inter-18/recursion.py:45-47 COMPLETE
def total_agents(b, max_depth):
    """All agents from the root (depth 0) down to max_depth: the geometric sum 1 + b + ... + b^max_depth."""
    return sum(b ** d for d in range(max_depth + 1))
```

**Cap the sub-agent recursion depth so a non-converging decomposition fails at a geometric sum instead of an exponential swarm — and pair it with a total-spawn budget, because the bounded tree is still exponential in the cap and the branching factor.**

## External resources

The agent-loop iteration-limit pattern (this hub's "bound the agent loop" module) — the one-dimensional version of this control; the depth cap is its extension to a tree of agents.

Frameworks with sub-agent orchestration (LangGraph, CrewAI, Anthropic's multi-agent research writeups) — their configuration for maximum recursion depth and total agent/step budgets, the production form of these two caps.

Any algorithms text on the geometric series and branching processes — why bᵈ growth and the closed-form sum (b^(D+1)−1)/(b−1) are the exact shape of a bounded recursion tree.
