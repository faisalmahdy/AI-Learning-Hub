---
id: teach-inter-05
title: Recommend from the ready-to-learn frontier, not the next module in the list
topic: teaching-and-portability
level: intermediate
status: ready
time: 8-10h
summary: A curriculum is a prerequisite graph, and the only modules worth recommending to a learner are those on the ready-to-learn frontier — prerequisites all mastered, module not yet mastered — because studying a module whose prerequisites are unmet means bouncing off material that silently assumes knowledge the learner does not have. With intro and basics mastered, the frontier is vectors and calculus, while attention and training stay locked waiting on vectors. The bug is recommending by list order: it picks the first not-yet-mastered module by id and sends the learner to attention, which needs vectors they have not done — a guaranteed bounce — while the frontier recommender sends them to calculus, which they can actually absorb. The fix is to compute what is reachable from what is mastered, not to walk the list.
eli5: You cannot learn to divide before you can multiply, no matter where division sits in the textbook. The right next lesson is one whose building blocks you already have. A dumb planner that just says "do the next chapter" will hand you a chapter you are not ready for and you will get stuck. A good one looks at what you already know and picks something that builds directly on it.
---

## Why this module

This hub is a curriculum, and a curriculum is not a list — it is a graph. Each module assumes the ones before it, and the order modules happen to sit in a file has nothing to do with the order a given learner can absorb them. Recommending what to study next is therefore a graph question, not a list question, and getting it wrong wastes the learner's most limited resource: the effort they spend bouncing off material they were not ready for. This module builds the correct recommender — the ready-to-learn frontier — and the natural wrong one that walks the list and sends learners into walls.

The key object is the frontier: the set of modules whose prerequisites are all mastered but which the learner has not mastered yet. Those are exactly the modules that can be absorbed right now — the building blocks are in place, and there is something new to learn. A module with an unmet prerequisite is locked: studying it means hitting an assumption the learner cannot meet, and the usual result is not learning-but-slow, it is a bounce, a demoralizing stall that teaches nothing. The tempting bug is to recommend by list order or id — pick the first not-yet-mastered module and go. That ignores the graph entirely, so it will recommend a module deep in the dependency chain whose prerequisites are missing, sending the learner somewhere they cannot follow. The fix is to compute the frontier from the prerequisites and recommend only from it.

You need the readiness and prerequisite instincts from the earlier teaching modules; this shares topological machinery with the orchestration DAG module but asks a different question — not "what order can these run" but "what can this learner absorb next". Everything runs offline against a curriculum fixture — six modules, a mastered set — stdlib Python 3, `$0.00`. The instinct to unlearn is that the next thing to study is the next thing in the list. The next thing to study is anything on the frontier of what you already know, and the list order is irrelevant to it.

Here is the frontier, and what is still locked:

```
# modules/teaching-and-portability/code/teach-inter-05/ — COMPLETE, run from that directory
$ python3 frontier.py --frontier

FRONTIER — ready to learn now (prereqs met, not yet mastered)
------------------------------------------------------------------
  mastered: ['basics', 'intro']
  UNLOCKED (recommend from here): ['vectors', 'calculus']
  LOCKED:
     attention  waiting on: ['vectors']
     training   waiting on: ['attention', 'calculus']
```

run: 2026-08-26 · deterministic; curriculum is a fixture · 6 modules · `python3 frontier.py --frontier`

With intro and basics mastered, two modules are ready — vectors and calculus — and two are locked, each naming what it waits on. This module is why you recommend from the unlocked set and what happens when you do not.

## Concepts

Named here so you can find them again; each is built below.

- **Prerequisite graph** — the curriculum as modules with edges to the modules they require.
- **Mastered set** — what the learner has already learned; the ground the frontier grows from.
- **Prerequisites met** — all of a module's required modules are in the mastered set.
- **Ready-to-learn frontier** — modules with prereqs met and not yet mastered; the recommendable set.
- **Locked module** — a module with an unmet prerequisite; studying it means bouncing off it.
- **By-order recommendation** — the bug: picking the next module by id, ignoring the graph.

## Worked example

Source: the prerequisite-gating logic in adaptive learning systems and skill trees (Khan Academy's knowledge map, mastery-based unlocking); the curriculum and mastered set here stand in for a real learner's state so the frontier and the by-order mistake are exact and checkable.

Script and fixture: `modules/teaching-and-portability/code/teach-inter-05/` — `frontier.py`, and `curriculum.json`, six modules with prerequisites and a mastered set. Every command runs from there.

### Readiness: prerequisites met, not yet mastered

A module is ready to learn under two conditions, and both matter.

```
# frontier.py:38-45 — COMPLETE (prereqs met; ready to learn now)
def prereqs_met(module, mastered):
    """Are all of a module's prerequisites in the mastered set?"""
    return all(p in mastered for p in module["prereqs"])


def is_unlocked(module, mastered):
    """Ready to learn now: prereqs met AND not already mastered."""
    return module["id"] not in mastered and prereqs_met(module, mastered)
```

`prereqs_met` checks the building blocks are in place; the `module["id"] not in mastered` guard excludes what the learner already knows, because recommending a mastered module is wasted time in the other direction. Both conditions together define the frontier: new, and reachable. A module fails to be on the frontier for one of two opposite reasons — already done, or not yet reachable — and a good recommender excludes both.

### The frontier and the locked set

Partition the not-yet-mastered modules into those that are reachable and those that are not.

```
# frontier.py:48-52 — COMPLETE (the frontier, and the locked remainder)
def frontier(modules, mastered):
    return [m for m in modules if is_unlocked(m, mastered)]


def locked(modules, mastered):
    return [m for m in modules if m["id"] not in mastered and not prereqs_met(m, mastered)]
```

From the cold open, the frontier is vectors and calculus, and the locked set is attention (waiting on vectors) and training (waiting on attention and calculus). Notice the structure this reveals: calculus has no prerequisites at all, so it was reachable from the very start; attention is one step past the frontier, unlockable as soon as vectors is done; training is two steps out. The frontier is a moving boundary — master vectors and attention joins the frontier next. The recommender's job is to keep the learner on that boundary, always studying something reachable, never something locked.

<svg viewBox="0 0 700 210" role="img" aria-label="A prerequisite graph. intro and basics are shaded as mastered. vectors (needs basics) and calculus (no prereqs) are highlighted as the frontier. attention (needs vectors) and training (needs attention and calculus) are drawn locked. Arrows point from prerequisite to dependent.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">mastered (solid) -> frontier (highlighted) -> locked (dashed)</text>
    <g fill="var(--acc-soft)" stroke="var(--acc-line)"><rect x="40" y="90" width="80" height="26" rx="4"></rect><rect x="150" y="90" width="80" height="26" rx="4"></rect></g>
    <text x="80" y="107" text-anchor="middle" fill="var(--acc-ink)">intro ✓</text><text x="190" y="107" text-anchor="middle" fill="var(--acc-ink)">basics ✓</text>
    <g fill="var(--panel)" stroke="var(--s1)" stroke-width="2"><rect x="260" y="50" width="90" height="26" rx="4"></rect><rect x="260" y="130" width="90" height="26" rx="4"></rect></g>
    <text x="305" y="67" text-anchor="middle" fill="var(--s1)">vectors ★</text><text x="305" y="147" text-anchor="middle" fill="var(--s1)">calculus ★</text>
    <g fill="none" stroke="var(--muted)" stroke-dasharray="3 2"><rect x="390" y="50" width="90" height="26" rx="4"></rect><rect x="520" y="90" width="90" height="26" rx="4"></rect></g>
    <text x="435" y="67" text-anchor="middle" fill="var(--muted)">attention 🔒</text><text x="565" y="107" text-anchor="middle" fill="var(--muted)">training 🔒</text>
    <g stroke="var(--muted)" fill="none"><path d="M230 100 L258 70"></path><path d="M350 63 L388 63"></path><path d="M480 63 L520 95"></path><path d="M350 143 L520 108"></path></g>
    <text x="360" y="195" fill="var(--muted)" font-size="8">the frontier is the boundary just past what is mastered — recommend only from it</text>
  </g>
</svg>
^ Mastered modules seed the frontier; vectors and calculus sit just past that boundary, reachable now. Attention and training are locked behind unmet prerequisites — one and two steps out — and become reachable only as the frontier advances.

### The bug: recommend by order

The natural wrong recommender ignores the graph and walks the list.

```
# frontier.py:62-71 — COMPLETE (frontier-based vs by-order recommendation)
def recommend_frontier(modules, mastered):
    """Correct: pick from the ready-to-learn frontier (first by id for determinism)."""
    ready = sorted(frontier(modules, mastered), key=lambda m: m["id"])
    return ready[0]["id"] if ready else None


def recommend_by_order(modules, mastered):
    """The bug: pick the first not-yet-mastered module by id, ignoring prerequisites."""
    todo = sorted((m for m in modules if m["id"] not in mastered), key=lambda m: m["id"])
    return todo[0]["id"] if todo else None
```

`recommend_by_order` sorts the not-yet-mastered modules and takes the first — and the first alphabetically is attention, which needs vectors the learner has not done. It never checks the prerequisites, so it cannot know. Run both:

```
# $ python3 frontier.py --recommend
#   frontier recommends: calculus  (prereqs met: True)
#   by-order recommends: attention  (prereqs met: False, missing ['vectors'])
```

run: 2026-08-26 · deterministic · `python3 frontier.py --recommend`

<svg viewBox="0 0 700 150" role="img" aria-label="Two recommendation outcomes. Frontier recommends calculus, drawn with a green check and 'prereqs met'. By-order recommends attention, drawn with a red cross and 'missing: vectors', and an arrow to a wall labelled bounce.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">same learner, two recommenders</text>
    <text x="30" y="52" fill="var(--s1)">frontier -></text>
    <rect x="130" y="38" width="110" height="26" rx="4" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="185" y="55" text-anchor="middle" fill="var(--acc-ink)" font-size="8">calculus</text>
    <text x="255" y="55" fill="var(--s1)" font-size="8">prereqs met -> learns it</text>
    <text x="30" y="102" fill="var(--s2)">by-order -></text>
    <rect x="130" y="88" width="110" height="26" rx="4" fill="var(--panel)" stroke="var(--s2)"></rect><text x="185" y="105" text-anchor="middle" fill="var(--s2)" font-size="8">attention</text>
    <text x="255" y="98" fill="var(--s2)" font-size="8">missing vectors -></text>
    <rect x="430" y="88" width="60" height="26" fill="var(--s2)" opacity="0.3"></rect><text x="460" y="105" text-anchor="middle" fill="var(--s2)" font-size="8">BOUNCE</text>
  </g>
</svg>
^ The frontier pick lands on a module the learner can absorb; the by-order pick lands on one whose prerequisite is missing, and the learner bounces off it. The recommender's quality is decided entirely by whether it read the prerequisites.

The frontier recommender sends the learner to calculus, whose prerequisites are met — they can absorb it today. The by-order recommender sends them to attention, whose prerequisite vectors is missing — they will open it, hit an assumption they cannot meet, and bounce. Same learner, same curriculum, and the difference is whether the recommender consulted the graph or just the list. The by-order bug is seductive because on a curriculum that happens to be authored in dependency order it would work by accident — which is exactly how it survives to break on the first curriculum that is not.

**The next module to study is any module on the ready-to-learn frontier — prerequisites mastered, itself not — so a recommender must compute reachability from the mastered set, because recommending by list order sends the learner to a module whose prerequisites are unmet and they bounce off it.**

### The self-test

The `--check` mode asserts the frontier is valid and the bug is real: every frontier module has its prereqs met, the frontier excludes mastered modules and is non-empty, by-order recommends a locked module, and the frontier recommends a ready one.

```
# $ python3 frontier.py --check
#   every module on the frontier has its prereqs met = True (['vectors', 'calculus'])
#   the frontier excludes already-mastered modules = True
#   the frontier is non-empty (there is something to learn) = True
#   by-order recommends a LOCKED module = True (attention needs ['vectors'])
#   frontier recommends a module the learner is ready for = True (calculus)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 frontier.py --check`

The two decisive assertions are the frontier's guarantee and the bug's mistake:

```
# frontier.py:108-121 — COMPLETE (frontier picks are ready; by-order picks a locked module)
    fr = frontier(mods, mastered)
    frontier_ready = all(prereqs_met(m, mastered) for m in fr)

    bo = recommend_by_order(mods, mastered)
    bo_module = next(m for m in mods if m["id"] == bo)
    by_order_locked = not prereqs_met(bo_module, mastered)
```

`frontier_ready` requires every frontier module to have its prerequisites met; `by_order_locked` requires the by-order pick to be missing one — safe recommendation proven for one policy and unsafe for the other.

The `frontier_ready` line is the correctness anchor: every module the frontier offers must have all prerequisites met, and if the reachability check were wrong that would fail first. The `by_order_locked` line encodes the lesson as a guardrail — it requires the by-order recommender to actually pick a module with an unmet prerequisite on this curriculum, so the test proves the list-walking approach is unsafe rather than merely asserting the frontier works.

### The running tally

| module | prereqs | status | recommendable? |
|---|---|---|---|
| calculus | (none) | unlocked | yes — frontier |
| vectors | basics ✓ | unlocked | yes — frontier |
| attention | vectors ✗ | locked | no — by-order picks it anyway |
| training | attention ✗, calculus ✓ | locked | no |

<svg viewBox="0 0 700 150" role="img" aria-label="Two states of the frontier. Before: mastered intro, basics; frontier vectors, calculus; attention locked. After mastering vectors: mastered gains vectors; the frontier now includes attention and still calculus; training still locked on calculus and attention.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">the frontier moves as the learner masters modules</text>
    <text x="30" y="44" fill="var(--ink)">now</text>
    <text x="90" y="44" fill="var(--acc-ink)">mastered: intro, basics</text>
    <text x="90" y="60" fill="var(--s1)">frontier: vectors, calculus</text>
    <text x="90" y="76" fill="var(--muted)">locked: attention (needs vectors), training</text>
    <line x1="30" y1="88" x2="660" y2="88" stroke="var(--grid)"></line>
    <text x="30" y="110" fill="var(--ink)">after</text>
    <text x="90" y="110" fill="var(--acc-ink)">mastered: intro, basics, vectors</text>
    <text x="90" y="126" fill="var(--s1)">frontier: attention, calculus  &lt;- attention just unlocked</text>
    <text x="90" y="142" fill="var(--muted)">locked: training (still needs calculus)</text>
  </g>
</svg>
^ Mastering vectors advances the frontier: attention, previously locked, becomes reachable and joins the recommendable set. The frontier is not a fixed list but a boundary that moves with the learner's progress.

Read attention's row against the recommenders. It is locked — one prerequisite unmet — yet the by-order recommender picks it because alphabetically it comes first among the unfinished. The frontier recommender skips it precisely because vectors is missing. The whole difference between a recommender that helps and one that stalls the learner is in that one row: does the recommendation respect the prerequisite edges, or only the module names. Consult the graph, never the list.

### What we did not settle

A frontier is the start of curriculum sequencing, not the end. Among several ready modules, which to recommend first depends on more than readiness — the learner's goal, the shortest path to a target module, prerequisite depth, and interleaving for retention (which the spacing literature favors over finishing one branch before starting another). Prerequisites are not always hard gates; some are soft, where missing them slows rather than blocks, so a real system weights them. Mastery itself is derived, not claimed — the readiness-honesty module's lesson applies to the mastered set feeding this one. And the graph can have cycles if authored carelessly, which must be detected exactly as the DAG module did. The rule here — recommend from the reachable frontier, not the list — is the floor; ordering within the frontier is the next layer.

## Build

The practice in one paragraph: model the curriculum as a prerequisite graph, not a list; compute the ready-to-learn frontier as the modules whose prerequisites are all mastered and which are not yet mastered; recommend only from that frontier, never by list or id order, because a list-walking recommender sends learners to locked modules they bounce off; and re-derive the mastered set from actual evidence, so the frontier grows on real progress. Order within the frontier by the learner's goal and by spacing, not by convenience.

We opened on the frontier. The number that proves a recommender is safe is whether its pick has its prerequisites met:

```
# modules/teaching-and-portability/code/teach-inter-05/ — COMPLETE, run from that directory
$ python3 frontier.py --recommend
  frontier recommends: calculus  (prereqs met: True)
  by-order recommends: attention  (prereqs met: False, missing ['vectors'])
```

Now do it to your own curriculum. Model your modules as a prerequisite graph, take your real mastered set, and compute the frontier. Your number to beat is not the size of the frontier; it is **whether your recommender ever offers a module with an unmet prerequisite** — the frontier recommender never does, a by-order one will. Then build the by-order version and watch it recommend a locked module. Bring back the frontier and both recommenders' picks. Good luck.

## Definition of done

- [ ] A curriculum modelled as a prerequisite graph, with a mastered set
- [ ] The ready-to-learn frontier computed (prereqs met, not yet mastered)
- [ ] The locked modules identified, each with its missing prerequisites
- [ ] A frontier-based recommender that only offers reachable modules
- [ ] A by-order recommender shown to offer a locked module
- [ ] Confirmation the frontier's picks always have prerequisites met
- [ ] `python3 frontier.py --check` printing SELF-TEST PASS: frontier-ready, none-mastered, nonempty, by-order-locked, frontier-safe
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What two conditions put a module on the ready-to-learn frontier, and why does each matter?
2. Why is recommending the next module by list order a bug, and when would it happen to work?
3. attention is locked but the by-order recommender picks it. Explain the exact mistake and its consequence for the learner.
4. The frontier is called a moving boundary. What makes it move, and how does that change the recommendation over time?
5. Your own curriculum was modelled as a graph. What was the frontier, and did your by-order recommender ever offer a locked module?

## External resources

- Khan Academy knowledge map / mastery-learning writing — my summary: a production prerequisite graph that gates content on mastery of upstream skills; read it for how a real system computes and presents the ready-to-learn frontier.
- Cognitive-load theory on prerequisite knowledge and the expertise-reversal effect — my summary: why material that assumes missing prerequisites overloads a learner, and why readiness, not sequence, determines what can be absorbed; read it for the learning-science basis of "bouncing off" a locked module.
- This hub, *govern-inter-04* — modules/orchestration-and-governance/govern-inter-04.md — my summary: the task-DAG module that orders work by dependencies and detects cycles; read it for the shared topological machinery applied to a different question — execution order there, learner readiness here.
