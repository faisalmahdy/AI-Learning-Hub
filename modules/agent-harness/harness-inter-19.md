---
id: harness-inter-19
title: Prune the tool menu — or every unused tool's schema is a token tax paid on every single call
topic: agent-harness
level: intermediate
status: ready
time: 19 min
summary: An agent's tool definitions — each tool's name, description, and parameter schema — are sent to the model on every request, because the model is stateless and must be told its tools each time. Register fifty tools and all fifty schemas ride along on every call, used or not. That is a fixed tax on the context window: tokens spent before the model reads a word of the task, spent again on the next call, and again, for the whole loop. A task that needs two tools but is handed fifty pays for forty-eight it never touches, over and over. Pruning the menu to the tools the task actually needs makes the per-call cost the sum of the relevant schemas, not the whole registry, and the reclaimed budget goes to the task. On eight 250-token tools where the task needs two, the full menu spends 2000 tokens per call (25% of an 8000-token budget), 1500 of it unused; over a 10-call loop that is 15000 wasted tokens.
eli5: Imagine you had to carry a giant instruction binder for every gadget you own into a room each time you wanted to do one small thing — and you own fifty gadgets but only need the stapler. You would haul all fifty manuals, every trip, wasting your arms on forty-nine you never open. Bringing only the stapler's page each time leaves your hands free for the actual work. A tool menu is that binder, re-carried on every single call.
---

## Why this module

A tool the agent never uses is not free just because it goes uncalled — its schema is re-sent to the model on every request, spending context budget before any work begins.

The model is stateless: it does not remember its tools between calls, so the harness sends the full tool menu — every name, description, and parameter schema — on each request. That is fine for a few tools and a real cost for many. Register a large tool catalog and every schema in it is serialized into the context window on every single call of the loop, regardless of whether the task touches it. A task that genuinely needs two tools, handed a fifty-tool menu, pays the token cost of forty-eight irrelevant schemas — not once, but on call after call after call. The tools are behaving perfectly; the harness is taxing the context to describe capabilities the task will never invoke.

**A registered tool costs tokens on every call whether or not it is used, so an over-broad menu is a fixed per-call tax on the context budget.**

Pruning the menu removes the tax. Expose only the tools this task needs — chosen up front, or retrieved per step from a larger catalog — so the per-call cost is the sum of the relevant schemas alone. The reclaimed budget goes to the actual task, and because the menu re-ships every call, the saving multiplies across the loop. This module measures the full menu's cost against the pruned one and the waste compounding over a loop.

## Concepts

The **tool menu** is the set of tool schemas sent to the model. Each tool costs some number of tokens to describe; the **menu cost** is the sum of those, and it is paid **per call** because the menu is re-sent every request.

The **needed** tools are the ones a given task actually uses. The **unused** tools are the rest of the registry — present in the menu, absent from the work.

The **waste** is the token cost of the unused schemas, and it has two multipliers. It is paid on every call, and there are many calls in a loop, so the total waste is per-call-waste times the number of calls. A modest per-call waste becomes a large total because the menu is stateless and re-shipped each step.

The **context budget** is the model's window. The menu cost is a fraction of it spent before the task, its context, and the model's reasoning get any room — so a bloated menu does not just cost tokens, it crowds out the work.

The trap is treating registered-but-unused tools as harmless. They are harmless to correctness but not to cost: every call pays for them, and the payment recurs. The fix is not fewer capabilities but a smaller *exposed* menu per task — retrieve the relevant tools, do not register the whole catalog into every prompt.

**Menu cost is per-call and recurring, so pruning to the needed tools reclaims budget on every call and multiplies that saving across the loop.**

Because the model is stateless, the whole menu rides along on every request — the same schemas re-serialized each call, not remembered from the last.

<svg role="img" aria-label="Three sequential calls, each carrying the full eight-tool menu again, showing the menu re-sent every time" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="16" fill="var(--muted)" font-size="8">each call re-sends the entire menu</text>
  <g font-size="7" fill="var(--muted)">
    <rect x="20" y="24" width="60" height="30" fill="none" stroke="var(--s1)"/><text x="30" y="36" fill="var(--s1)">menu×8</text><text x="30" y="49" fill="var(--muted)">+task</text><text x="35" y="66" >call 1</text>
    <rect x="120" y="24" width="60" height="30" fill="none" stroke="var(--s1)"/><text x="130" y="36" fill="var(--s1)">menu×8</text><text x="130" y="49" fill="var(--muted)">+task</text><text x="135" y="66">call 2</text>
    <rect x="220" y="24" width="60" height="30" fill="none" stroke="var(--s1)"/><text x="230" y="36" fill="var(--s1)">menu×8</text><text x="230" y="49" fill="var(--muted)">+task</text><text x="235" y="66">call 3</text>
  </g>
  <line x1="80" y1="39" x2="120" y2="39" stroke="var(--grid)" stroke-width="1"/>
  <line x1="180" y1="39" x2="220" y2="39" stroke="var(--grid)" stroke-width="1"/>
  <text x="20" y="88" fill="var(--muted)" font-size="8">the menu is not cached across calls — it is paid again and again</text>
</svg>
^ The model keeps no memory between calls, so the full menu is re-serialized into every request — which is why its cost is a per-call tax that compounds over the loop.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/harness-inter-19/menu.py

The fixture is eight equally-sized tools, the two the task needs, the loop length, and the budget.

```json filename=modules/agent-harness/code/harness-inter-19/tools.json:1-11 COMPLETE
{
  "_meta": "An agent's tool menu. tool_tokens maps each registered tool to the number of tokens its schema (name, description, parameters) occupies -- this whole menu is sent to the model on EVERY request. needed lists the tools this particular task actually uses. calls is how many model calls the task's loop makes. context_budget is the model's context window in tokens. The question: how much of the budget does the full menu spend per call, and how much of that is wasted on tools the task never uses?",
  "tool_tokens": {
    "search": 250, "read_file": 250, "write_file": 250, "delete_file": 250,
    "list_dir": 250, "move_file": 250, "run_shell": 250, "http_get": 250
  },
  "needed": ["search", "read_file"],
  "calls": 10,
  "context_budget": 8000
}
```

The menu cost is a sum over the exposed tools; the unused set is the registry minus the needed tools.

```python filename=modules/agent-harness/code/harness-inter-19/menu.py:40-46 COMPLETE
def menu_cost(tool_tokens, tools):
    """Tokens the given set of tool schemas occupies -- paid on every call."""
    return sum(tool_tokens[t] for t in tools)


def unused(tool_tokens, needed):
    return [t for t in tool_tokens if t not in needed]
```

Run `--cost` for the per-call price of each menu.

```text filename=--cost
COST — per-call menu cost, full vs pruned (budget 8000 tokens)
--------------------------------------------------------------
  full menu (8 tools):    2000 tokens/call   25.0% of budget
  pruned  (2 tools):       500 tokens/call    6.2% of budget
--------------------------------------------------------------
  the menu is spent before the task is even read -- every call.
```

The full menu is 2000 tokens — a quarter of the 8000-token budget — spent on every call before the model sees the task. The pruned menu is 500, 6.2% of the budget. Same two tools do the work in both; the full menu just carries six more descriptions the task never invokes, and it carries them every single call.

<svg role="img" aria-label="Full menu takes 25 percent of the budget bar, pruned menu 6.2 percent; the rest is free for the task" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="16" fill="var(--muted)" font-size="8">full menu</text>
  <rect x="20" y="22" width="260" height="16" fill="none" stroke="var(--line)"/>
  <rect x="20" y="22" width="65" height="16" fill="var(--s1)"/>
  <text x="90" y="34" fill="var(--muted)" font-size="7">2000 (25%) menu · rest for the task</text>
  <text x="10" y="62" fill="var(--muted)" font-size="8">pruned</text>
  <rect x="20" y="68" width="260" height="16" fill="none" stroke="var(--line)"/>
  <rect x="20" y="68" width="16" height="16" fill="var(--s2)"/>
  <text x="42" y="80" fill="var(--muted)" font-size="7">500 (6.2%) menu · far more for the task</text>
  <text x="20" y="102" fill="var(--muted)" font-size="8">the menu is the shaded slice; pruning shrinks it and grows the room for work</text>
</svg>
^ The shaded menu slice eats a quarter of the budget under the full registry and a sliver under the pruned one — the unshaded remainder is what the task itself gets to use.

## Build

The waste view sums the unused schemas and multiplies by the loop length.

```python filename=modules/agent-harness/code/harness-inter-19/menu.py:63-71 COMPLETE
def waste_view(data):
    tt, needed, calls = data["tool_tokens"], data["needed"], data["calls"]
    waste_per_call = menu_cost(tt, unused(tt, needed))
    print("WASTE — tokens spent on tools the task never uses")
    print("-" * 62)
    print("  unused tools: %d of %d" % (len(unused(tt, needed)), len(tt)))
    print("  wasted per call:      %5d tokens" % waste_per_call)
    print("  calls in the loop:    %5d" % calls)
    print("  wasted over the loop: %5d tokens" % (waste_per_call * calls))
```

Now count what the unused tools cost with `--waste`.

```text filename=--waste
WASTE — tokens spent on tools the task never uses
--------------------------------------------------------------
  unused tools: 6 of 8
  wasted per call:       1500 tokens
  calls in the loop:       10
  wasted over the loop: 15000 tokens
--------------------------------------------------------------
  the waste multiplies by the number of calls, because the menu re-ships each time.
```

Six of the eight tools go unused, and their schemas cost 1500 tokens — paid on every call. One call wastes 1500; a ten-call loop wastes 15000, because the menu is stateless and re-sent each step. That 15000 is not a rounding error against an 8000-token window — it is nearly two full context windows of budget, burned entirely on describing tools the task never touched.

<svg role="img" aria-label="Per-call waste of 1500 tokens repeated across 10 calls stacks to 15000 tokens" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="16" fill="var(--muted)" font-size="8">1500 wasted tokens/call, re-sent every call</text>
  <g fill="var(--s1)" opacity="0.7">
    <rect x="20" y="24" width="24" height="10"/><rect x="47" y="24" width="24" height="10"/><rect x="74" y="24" width="24" height="10"/><rect x="101" y="24" width="24" height="10"/><rect x="128" y="24" width="24" height="10"/>
    <rect x="155" y="24" width="24" height="10"/><rect x="182" y="24" width="24" height="10"/><rect x="209" y="24" width="24" height="10"/><rect x="236" y="24" width="24" height="10"/><rect x="263" y="24" width="17" height="10"/>
  </g>
  <text x="20" y="52" fill="var(--muted)" font-size="8">× 10 calls</text>
  <rect x="20" y="60" width="260" height="16" fill="var(--s1)"/>
  <text x="95" y="72" fill="var(--panel)" font-size="8">15000 tokens wasted total</text>
  <text x="20" y="98" fill="var(--muted)" font-size="8">the tax recurs, so it compounds with loop length</text>
</svg>
^ Each call re-pays the 1500-token tax on unused tools, so over ten calls it stacks to 15000 — the recurrence, not the single call, is what makes it expensive.

## Definition of done

The self-test pins the tax: the full menu costs more per call, the waste equals the unused schemas, it multiplies over the loop, most tools go unused, and pruning reclaims a real share of the budget.

```python filename=modules/agent-harness/code/harness-inter-19/menu.py:84-97 COMPLETE
    full_menu_costs_more = full > pruned
    print("  the full menu costs more per call than the pruned one = %s (%d vs %d)" % (full_menu_costs_more, full, pruned))

    waste_equals_unused = waste_per_call == full - pruned
    print("  the waste equals the unused tools' schemas = %s (%d = %d - %d)" % (waste_equals_unused, waste_per_call, full, pruned))

    total_waste = waste_per_call * calls
    waste_compounds = total_waste > waste_per_call and calls > 1
    print("  the waste multiplies over the loop = %s (%d over %d calls)" % (waste_compounds, total_waste, calls))

    unused_are_majority = len(unused(tt, needed)) > len(needed)
    print("  most registered tools go unused = %s (%d unused vs %d needed)" % (unused_are_majority, len(unused(tt, needed)), len(needed)))

    pruning_frees_budget = pruned < full and (full - pruned) / budget > 0.1
    print("  pruning reclaims a real share of the budget = %s (%.1f%% freed per call)" % (pruning_frees_budget, 100 * (full - pruned) / budget))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the full menu is re-sent every call; most of it is unused; pruning reclaims the budget
--------------------------------------------------------------------------------------------------------
  the full menu costs more per call than the pruned one = True (2000 vs 500)
  the waste equals the unused tools' schemas = True (1500 = 2000 - 500)
  the waste multiplies over the loop = True (15000 over 10 calls)
  most registered tools go unused = True (6 unused vs 2 needed)
  pruning reclaims a real share of the budget = True (18.8% freed per call)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  full_menu_costs_more=True  waste_equals_unused=True  waste_compounds=True  unused_are_majority=True  pruning_frees_budget=True
```

**Done means the tax is quantified: the full menu spends 2000 tokens/call to the pruned menu's 500, the 1500-token gap is exactly the unused schemas, and over ten calls it compounds to 15000 wasted tokens.**

## Boss fight

Pruning saved tokens here. Predict the second, subtler cost of the full menu beyond the tokens. It is tempting to think token cost is the whole story.

The other cost is selection accuracy: a model choosing among fifty tools picks the right one less reliably than a model choosing among two, because the extra tools are distractors — similar-looking options that invite a wrong call. So an over-broad menu taxes the budget *and* degrades the decision, and pruning helps both. This is why retrieval-augmented tool selection exists: for a large catalog, retrieve the handful of tools relevant to the current step and expose only those, so the model both pays less and chooses better. The token math is the measurable half; the accuracy half compounds the case for pruning.

The mirror-image mistake is pruning so aggressively that a tool the task turns out to need is not exposed, so the model cannot call it and the task fails. The menu must contain every tool the task might use, just not every tool that exists — the discipline is "expose the relevant set," which requires knowing or retrieving what is relevant, not blindly cutting to a fixed small number. And when tools genuinely all get used, the cost is real work, not waste; the tax is specifically the schemas that ride along uninvoked.

```python filename=modules/agent-harness/code/harness-inter-19/menu.py:40-42 COMPLETE
def menu_cost(tool_tokens, tools):
    """Tokens the given set of tool schemas occupies -- paid on every call."""
    return sum(tool_tokens[t] for t in tools)
```

**Expose only the tools a task needs, because every registered tool's schema is re-sent on every call — an over-broad menu taxes the budget on each step and multiplies across the loop, while also making the model's tool choice less accurate.**

## External resources

Anthropic's and OpenAI's tool-use documentation on token usage — tool definitions count against the input tokens on every request, the mechanism behind this tax.

Writeups on retrieval-augmented tool selection (and MCP's tool-listing patterns) — retrieving a relevant subset of tools per step for agents with large tool catalogs, the production form of pruning.

The companion "run independent tool calls in parallel" and "bound the agent loop" modules — the loop length that multiplies this tax is the same loop those modules bound and parallelize.
