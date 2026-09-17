---
id: parconflict-inter-01
title: Serialize conflicting parallel tool calls — two calls on the same resource where one writes are not independent, and running them at once races
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: Running the model's tool calls in parallel is a genuine speedup when the calls are independent — calls on different resources, or calls that only read the same resource, cannot interfere, so firing them all at once costs the slowest one instead of the sum. The mistake is to treat every parallel batch as if it were independent. Two calls conflict when they touch the same resource and at least one of them writes it: write-write is a conflict because both change the same thing and the final state depends on which finishes last, and read-write is a conflict because the reader may observe the value before, during, or after the writer, nondeterministically. Only read-read on a shared resource is safe, because neither call changes anything. Run conflicting calls concurrently and you have a data race: the batch's result depends on timing, so the same calls can produce different outcomes on different runs and a read can return a value that never coherently existed — a bug invisible in testing and corrupting in production. The fix is to schedule the batch into groups so that no group contains a conflicting pair: independent calls still share a group and run in parallel, while conflicting calls are split into separate groups that run in a defined order. On a fixture of five calls — two reads of A and three calls on B (two writes and a read) — the naive schedule runs all five in one batch that contains conflicts, while the safe schedule keeps the two A-reads parallel and serializes the three B-calls.
eli5: Imagine you have a team of helpers and a stack of chores. Some chores don't get in each other's way at all — one person waters the garden while another reads the mailbox — so you send everyone off at once and it's fast. But some chores fight: if two helpers both try to repaint the same wall at the same time, you get a streaky mess, and if one is painting the wall while another is trying to take a photo of it, the photo catches it half-done. Those chores touch the same thing, and at least one is changing it, so you can't let them happen together — you have to line them up one after another. The trick is telling the two kinds apart: chores that only look at the same thing are fine together; chores where someone changes a shared thing must take turns. Tool calls an AI makes are the same — run the independent ones together, but make the ones that fight over the same resource wait their turn.
---

## Why this module

Parallel tool execution is one of the biggest, easiest wins a harness has. A model often emits several tool calls in one turn, and if they are independent, running them serially wastes time — the turn takes the sum of their durations when it could take the maximum. Firing them concurrently is the obvious fix, and for independent calls it is exactly right.

The word doing all the work in that sentence is "independent", and it is easy to skip over. A batch of tool calls is not independent just because the model emitted them together; independence is a property of what the calls touch. Two calls that operate on different resources are independent. Two that read the same resource are independent, because reading changes nothing. But two that touch the same resource where at least one writes are not independent — and running them in parallel anyway is a data race.

A data race is a particularly nasty bug because its symptom is nondeterminism. The concurrent writes resolve in whatever order the scheduler happens to pick, so the result varies run to run; a concurrent read can catch a value mid-write. In testing the race usually resolves the benign way and everything looks fine; in production it occasionally resolves the other way and corrupts state, with no error and no reproduction. This module takes a batch of calls, finds the conflicts, and schedules the batch so no parallel group contains one.

**Parallelism is safe only for independent calls, and independence is about what the calls touch — two calls on the same resource where at least one writes must be serialized, or running them concurrently is a data race.**

## Concepts

The conflict rule is precise: two calls conflict when they share a resource and at least one is a write. That gives three cases. Read-read on a shared resource is safe — neither call mutates, so their order is irrelevant. Write-write is a conflict — both mutate, and the surviving value depends on which finishes last. Read-write is a conflict — the read's result depends on whether it lands before or after the write. The single condition "same resource and at least one write" captures both hazardous cases and excludes the safe one.

The reason a race is worse than a plain bug is that it is not a stable wrong answer; it is an unstable one. A deterministic bug fails the same way every time and is found in testing. A race is correct most of the time and wrong occasionally, gated by timing you do not control, so it survives testing and surfaces in production as sporadic corruption. This is why you cannot rely on "it worked when I ran it" — the run that works tells you nothing about the run that races.

The fix is a scheduling problem, and it is the same shape as graph coloring: treat each call as a node, draw an edge between any two that conflict, and partition the nodes into groups with no edge inside a group. Each group is a parallel batch, the groups run in sequence, and the number of groups is however many are needed to keep every conflicting pair apart. Independent calls fall into the same group and keep their parallelism; conflicting calls are forced into different groups and thereby serialized. The parallelism is preserved wherever it is safe and removed only where it is not.

<svg role="img" aria-label="A three-by-three grid of read and write against read and write on a shared resource: read-read is safe, the other three cells (read-write, write-read, write-write) are conflicts" viewBox="0 0 300 170">
<text x="150" y="16" fill="var(--muted)" font-size="10" text-anchor="middle">same resource</text>
<text x="90" y="48" fill="var(--muted)" font-size="10" text-anchor="middle">read</text>
<text x="170" y="48" fill="var(--muted)" font-size="10" text-anchor="middle">write</text>
<text x="35" y="78" fill="var(--muted)" font-size="10" text-anchor="middle">read</text>
<text x="35" y="128" fill="var(--muted)" font-size="10" text-anchor="middle">write</text>
<rect x="60" y="58" width="60" height="40" fill="var(--panel)" stroke="var(--s1)"/>
<text x="90" y="82" fill="var(--s1)" font-size="10" text-anchor="middle">safe</text>
<rect x="140" y="58" width="60" height="40" fill="var(--panel)" stroke="var(--s2)"/>
<text x="170" y="82" fill="var(--s2)" font-size="10" text-anchor="middle">conflict</text>
<rect x="60" y="108" width="60" height="40" fill="var(--panel)" stroke="var(--s2)"/>
<text x="90" y="132" fill="var(--s2)" font-size="10" text-anchor="middle">conflict</text>
<rect x="140" y="108" width="60" height="40" fill="var(--panel)" stroke="var(--s2)"/>
<text x="170" y="132" fill="var(--s2)" font-size="10" text-anchor="middle">conflict</text>
</svg>
^ On a shared resource only read-read is safe; any pairing with a write is a conflict — the single rule "same resource and at least one write".

**The conflict test is "same resource and at least one write"; a race is a nondeterministic bug that testing misses, and the cure is to group the calls so no parallel group holds a conflicting pair — parallel where safe, serial where not.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/parconflict-inter-01. The fixture is a batch of five tool calls, each with the resource it touches and its mode.

```json filename=modules/agent-harness/code/parconflict-inter-01/parconflict.json:3-6 COMPLETE
  "calls": [
    {"id": "c1", "resource": "A", "mode": "read"},
    {"id": "c2", "resource": "A", "mode": "read"},
    {"id": "c3", "resource": "B", "mode": "write"},
```

The conflict test is a single condition — same resource, and at least one writes.

```python filename=modules/agent-harness/code/parconflict-inter-01/parconflict.py:34-36 COMPLETE
def conflict(a, b):
    """Two calls conflict if they touch the same resource and at least one writes it."""
    return a["resource"] == b["resource"] and (a["mode"] == "write" or b["mode"] == "write")
```

The safe scheduler greedily places each call in the first group that holds nothing it conflicts with — graph coloring by conflict.

```python filename=modules/agent-harness/code/parconflict-inter-01/parconflict.py:49-61 COMPLETE
def safe_schedule(calls):
    """Greedily place each call in the first group that holds no call it conflicts with."""
    groups = []
    for c in calls:
        placed = False
        for g in groups:
            if all(not conflict(c, other) for other in g):
                g.append(c)
                placed = True
                break
        if not placed:
            groups.append([c])
    return groups
```

Two small helpers list the conflicting pairs and test whether a proposed parallel group already holds one.

```python filename=modules/agent-harness/code/parconflict-inter-01/parconflict.py:39-46 COMPLETE
def conflict_pairs(calls):
    return [(a["id"], b["id"]) for i, a in enumerate(calls) for b in calls[i + 1:] if conflict(a, b)]


def has_conflict_within(group):
    """Does any pair inside this parallel group conflict?"""
    return any(conflict(group[i], group[j])
               for i in range(len(group)) for j in range(i + 1, len(group)))
```

First, which pairs conflict? Predict: the two reads of A are safe, and the three calls on B (two writes and a read) all conflict with each other. Run `--conflicts`:

```text filename=parconflict.py --conflicts
CONFLICTS — pairs on the same resource with at least one write
--------------------------------------------------------
  c1  resource=A  mode=read
  c2  resource=A  mode=read
  c3  resource=B  mode=write
  c4  resource=B  mode=write
  c5  resource=B  mode=read
  conflicting pairs: [('c3', 'c4'), ('c3', 'c5'), ('c4', 'c5')]
```

The prediction holds. The reads of A, c1 and c2, are not a conflicting pair. On B, every pair among the two writes and the read conflicts — write-write (c3,c4) and read-write (c3,c5 and c4,c5). Three conflicting pairs, all on resource B.

<svg role="img" aria-label="Five call nodes: c1 and c2 on resource A with no edge between them, and c3 c4 c5 on resource B forming a triangle of conflict edges" viewBox="0 0 440 160">
<text x="110" y="24" fill="var(--muted)" font-size="10" text-anchor="middle">resource A (reads)</text>
<circle cx="70" cy="70" r="16" fill="var(--panel)" stroke="var(--s1)"/>
<text x="70" y="74" fill="var(--ink)" font-size="10" text-anchor="middle">c1</text>
<circle cx="150" cy="70" r="16" fill="var(--panel)" stroke="var(--s1)"/>
<text x="150" y="74" fill="var(--ink)" font-size="10" text-anchor="middle">c2</text>
<text x="110" y="110" fill="var(--s1)" font-size="9" text-anchor="middle">no edge: safe</text>
<text x="330" y="24" fill="var(--muted)" font-size="10" text-anchor="middle">resource B (2 writes, 1 read)</text>
<circle cx="300" cy="60" r="16" fill="var(--panel)" stroke="var(--s2)"/>
<text x="300" y="64" fill="var(--ink)" font-size="10" text-anchor="middle">c3</text>
<circle cx="380" cy="60" r="16" fill="var(--panel)" stroke="var(--s2)"/>
<text x="380" y="64" fill="var(--ink)" font-size="10" text-anchor="middle">c4</text>
<circle cx="340" cy="120" r="16" fill="var(--panel)" stroke="var(--s2)"/>
<text x="340" y="124" fill="var(--ink)" font-size="10" text-anchor="middle">c5</text>
<line x1="316" y1="60" x2="364" y2="60" stroke="var(--s2)"/>
<line x1="306" y1="75" x2="332" y2="106" stroke="var(--s2)"/>
<line x1="374" y1="75" x2="348" y2="106" stroke="var(--s2)"/>
<text x="340" y="150" fill="var(--s2)" font-size="9" text-anchor="middle">a triangle of conflicts</text>
</svg>
^ The two reads of A share no conflict edge; the three calls on B form a conflict triangle, so no two of them may run together.

Now compare the two schedules. Predict: the naive one-batch schedule contains a conflict; the safe schedule does not. Run `--schedule`:

```text filename=parconflict.py --schedule
SCHEDULE — naive one parallel batch vs a safe grouped schedule
------------------------------------------------------------
  naive batches: [['c1', 'c2', 'c3', 'c4', 'c5']]  conflict inside? True
  safe  batches: [['c1', 'c2', 'c3'], ['c4'], ['c5']]  conflict inside? False
```

The prediction holds. The naive schedule is one batch of all five, which contains the B triangle — a race. The safe schedule runs c1, c2, and c3 together (they are mutually independent: two A-reads and one B-write that shares nothing with them), then c4, then c5, so the three conflicting B-calls each land in a different group and run in order. The two A-reads keep their parallelism.

<svg role="img" aria-label="Naive schedule is one batch of all five calls marked as racing; safe schedule is three sequential groups with the B calls separated and no conflict in any group" viewBox="0 0 440 160">
<text x="20" y="35" fill="var(--muted)" font-size="9">naive</text>
<rect x="70" y="22" width="300" height="24" fill="var(--panel)" stroke="var(--s2)"/>
<text x="220" y="38" fill="var(--ink)" font-size="9" text-anchor="middle">c1 c2 c3 c4 c5 (one batch)</text>
<text x="220" y="60" fill="var(--s2)" font-size="9" text-anchor="middle">contains the conflict -> races</text>
<text x="20" y="100" fill="var(--muted)" font-size="9">safe</text>
<rect x="70" y="86" width="120" height="24" fill="var(--panel)" stroke="var(--s1)"/>
<text x="130" y="102" fill="var(--ink)" font-size="9" text-anchor="middle">c1 c2 c3</text>
<rect x="200" y="86" width="70" height="24" fill="var(--panel)" stroke="var(--s1)"/>
<text x="235" y="102" fill="var(--ink)" font-size="9" text-anchor="middle">c4</text>
<rect x="280" y="86" width="70" height="24" fill="var(--panel)" stroke="var(--s1)"/>
<text x="315" y="102" fill="var(--ink)" font-size="9" text-anchor="middle">c5</text>
<text x="220" y="130" fill="var(--s1)" font-size="9" text-anchor="middle">three groups run in order; no group has a conflict</text>
</svg>
^ The naive batch bundles the conflict; the safe schedule spreads the B-calls across sequential groups while keeping the A-reads parallel.

## Build

The self-test plants the failure and names each claim as a boolean flag. It finds the conflict pairs and both schedules, then checks that conflicts exist, that read-read is not one, that the naive single batch contains a conflicting pair, that no safe group does, and that the two independent reads still share a group.

```python filename=modules/agent-harness/code/parconflict-inter-01/parconflict.py:103-115 COMPLETE
    conflicts_exist = len(pairs) > 0
    print("  some calls conflict (same resource, a write) = %s (%s)" % (conflicts_exist, pairs))

    read_read_not_conflict = ("c1", "c2") not in pairs
    print("  two reads of the same resource are not a conflict = %s" % read_read_not_conflict)

    naive_batch_races = any(has_conflict_within(g) for g in naive)
    print("  naive: the single parallel batch contains a conflicting pair = %s" % naive_batch_races)

    safe_no_conflict = not any(has_conflict_within(g) for g in safe)
    print("  safe: no parallel group contains a conflicting pair = %s (%s)" % (safe_no_conflict, [ids(g) for g in safe]))

    safe_keeps_independent_parallel = any(set(ids(g)) >= {"c1", "c2"} for g in safe)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the scheduler ever leaves a conflict in a group or needlessly serializes the safe reads:

```text filename=parconflict.py --check
SELF-TEST — the naive batch races on the shared resource; the safe schedule serializes the conflicts and keeps the rest parallel
--------------------------------------------------------------------------------------------------------------------------------
  some calls conflict (same resource, a write) = True ([('c3', 'c4'), ('c3', 'c5'), ('c4', 'c5')])
  two reads of the same resource are not a conflict = True
  naive: the single parallel batch contains a conflicting pair = True
  safe: no parallel group contains a conflicting pair = True ([['c1', 'c2', 'c3'], ['c4'], ['c5']])
  safe: the two independent reads still run in parallel = True
```

**The self-test checks both directions — no group holds a conflict AND the independent reads stay together — so a scheduler that "fixed" the race by serializing everything would fail the parallelism flag, not pass.**

## Definition of done

You can state the conflict rule — same resource and at least one write — and classify read-read, write-write, and read-write from it.
You can explain why a data race is worse than a deterministic bug: it is timing-dependent, so it survives testing and corrupts in production.
You can frame safe scheduling as graph coloring — nodes are calls, edges are conflicts, groups are conflict-free parallel batches run in sequence.
You can explain why independence is a property of what calls touch, not of the model emitting them together.
You can predict, for a new batch, which calls stay parallel and which must be serialized, and why.

## Boss fight

Consider ordering within the conflict cluster. The safe schedule serializes c3, c4, and c5, but into which order? For two writes to the same resource, the order determines the final value, and for the read c5, the order determines what it sees. Serializing removes the race — the outcome is now deterministic — but you still have to choose an order that matches intent, usually the order the model issued them. The lesson sharpens: serialization makes the result well-defined, but a well-defined wrong order is still wrong, so the harness should preserve issue order among conflicting calls, not just separate them.

Now consider the granularity of "resource". The whole analysis depends on knowing what each call touches, and if the harness models resources too coarsely — treating every call to one tool as touching one resource — it will serialize calls that were actually independent (two writes to different files under the same tool), throwing away safe parallelism. Model it too finely and it may miss a real conflict (two tools that both touch the same underlying database). The conflict test is only as good as the resource identity it compares, so the payoff and the safety both hinge on naming resources at the right granularity.

**Serialization must preserve the model's issue order among conflicting calls, because a defined-but-wrong order is still wrong; and the whole analysis is only as correct as the resource granularity — too coarse serializes safe calls, too fine misses real conflicts.**

## External resources

Database concurrency-control theory names exactly this rule: two operations conflict if they access the same item and at least one is a write, the basis of conflict-serializability.
Anthropic's and OpenAI's tool-use guides describe parallel tool calling as a latency optimization; this module is the safety condition that optimization needs.
The topic's own module on running independent tool calls in parallel covers the speedup; this one covers when calls are not independent and must not be parallelized.
