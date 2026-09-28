---
id: govern-inter-03
title: Fan-out needs a partition contract — overlap clobbers, gaps drop work
topic: orchestration-and-governance
level: intermediate
status: ready
time: 8-10h
summary: Fan eight files out to three parallel workers and hand one file to two of them and another to none, and the naive dispatch runs every worker cleanly while one worker's write is silently overwritten and one file is never written at all — two bugs that pass every "the workers ran" check because the damage is in the assignment, not the execution. A contract that verifies the assignment is a true partition — disjoint and complete — rejects the plan before any work is lost, and every lost write traces to an overlap the contract named.
eli5: Split a moving job among three people. If two both grab the kitchen, one packs it and the other repacks over them and the first packing is lost; if nobody grabs the garage, it gets left behind. Check that every room has exactly one owner before anyone lifts a box.
---

## Why this module

The governance modules so far judged agents after they ran. This one is about the orchestration itself — dividing a job across parallel workers — and the correctness bug that hides in the division. The labs run real fan-outs: the scan records "8+8+8 subagent fan-outs with partitioned ownership and worker contracts." That phrase — *partitioned ownership* — is doing quiet, load-bearing work, and this module shows what happens without it. When you fan a job out to workers that write files, the failure is almost never a worker crashing. It is two workers assigned the same file, or a file assigned to no one, and both failures happen while every worker reports success.

That is what makes the bug dangerous: it is invisible to execution. Every worker ran, every worker did its job, nothing threw an error — and yet one worker's output was silently overwritten by another, and one file was never touched. The work vanished not in the running but in the *assignment*, before any worker started. The fix is a contract you check before dispatch: the assignment must be a true partition of the work — every item owned by exactly one worker, disjoint so nothing is written twice and complete so nothing is skipped.

You need the governance instinct from this track: verify before you trust. Everything runs offline against an eight-file fan-out plan, stdlib Python 3, `$0.00`. The instinct to unlearn is that a successful fan-out is one where every worker succeeds. A fan-out where every worker succeeds can still lose half its work, and the only way to know is to check the assignment, not the execution.

Here is the naive fan-out running "successfully":

```
# modules/orchestration-and-governance/code/govern-inter-03/ — COMPLETE, run from that directory
$ python3 fanout.py --dispatch

NAIVE DISPATCH — run the workers, count the damage
--------------------------------------------------------------
  LOST WRITE  f3        alpha's work overwritten by beta
  NEVER WRITTEN  f8        (no worker owned it)
--------------------------------------------------------------
  1 lost write(s), 1 file(s) never written. Every worker ran; the plan
  was the bug, so nothing errored -- the work just quietly vanished.
```

run: 2026-08-25 · deterministic; the plan is a fixture · 8 files, 3 workers · `python3 fanout.py --dispatch`

Three workers, all successful, and the job came out wrong: `alpha`'s work on `f3` overwritten because `beta` was also assigned it, and `f8` never written because nobody was. No exception, no failed worker — just missing work. This module is that damage and the one check that prevents it.

## Concepts

Named here so you can find them again; each is built below.

- **Fan-out** — dispatch a job to several workers running in parallel, each owning part of it.
- **Assignment** — which work items each worker owns.
- **Overlap** — an item owned by more than one worker; both write it, one clobbers the other.
- **Gap** — an item owned by no worker; it is never written.
- **Partition** — an assignment that is disjoint (no overlaps) and complete (no gaps); the correctness condition.
- **The contract** — the partition check, run before dispatch, that rejects a broken assignment.

## Worked example

Source: faisalmahdy/ai-engineer-learning — the "8+8+8 subagent fan-outs with partitioned ownership and worker contracts" the scan records; and faisalmahdy/agents-workspace-files, whose governance treats disjoint ownership as a precondition. This module builds the smallest honest version of that contract.

Script and fixture: `modules/orchestration-and-governance/code/govern-inter-03/` — `fanout.py`, and `plan.json`, eight files assigned to three workers with one overlap and one gap. Every command runs from there.

### The frame: dividing the rooms of a house

Picture a moving crew splitting a house. The right way is a partition: each person owns a set of rooms, no room owned twice, no room owned zero times. Get that wrong in two ways and both are disasters that look like success. If two people both claim the kitchen, the first packs it and the second, finding it "not done" in their list, repacks it — the first person's careful packing is undone and lost, and both report "kitchen done." If nobody claims the garage, everyone reports their rooms done, the truck leaves, and the garage is still full. In both cases every mover succeeded at their assignment; the assignment was the failure.

A fan-out of file-writing workers is exactly this house. Two workers assigned the same file both write it, and last-writer-wins means one write is lost. A file assigned to no worker is the garage left behind. The contract is the crew chief who, before anyone lifts a box, checks that every room has exactly one owner.

### The plan: one overlap, one gap

```
# $ python3 fanout.py --plan
#   alpha     owns ['f1', 'f2', 'f3']
#   beta      owns ['f3', 'f4', 'f5']
#   gamma     owns ['f6', 'f7']
#   overlaps (owned twice): {'f3': ['alpha', 'beta']}
#   gaps (owned zero times): ['f8']
```

run: 2026-08-25 · fixture · `python3 fanout.py --plan`

`f3` is in both `alpha`'s and `beta`'s lists — an overlap. `f8` is in nobody's list — a gap. Eight files, three workers, and the assignment is neither disjoint nor complete. Both defects are one line each to detect, and both are invisible if you only watch the workers run.

<svg viewBox="0 0 700 170" role="img" aria-label="A coverage map of eight files f1 to f8 against three workers. alpha owns f1 f2 f3, beta owns f3 f4 f5, gamma owns f6 f7. f3 is covered twice (overlap, red), f8 is covered zero times (gap, red).">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="18" fill="var(--muted)">who owns each file — f3 twice (overlap), f8 never (gap)</text>
    <g fill="var(--muted)" text-anchor="middle">
      <text x="120" y="40">f1</text><text x="180" y="40">f2</text><text x="240" y="40">f3</text><text x="300" y="40">f4</text><text x="360" y="40">f5</text><text x="420" y="40">f6</text><text x="480" y="40">f7</text><text x="540" y="40">f8</text>
    </g>
    <text x="20" y="70" fill="var(--ink)">alpha</text>
    <rect x="96" y="58" width="48" height="16" fill="var(--s1)"></rect><rect x="156" y="58" width="48" height="16" fill="var(--s1)"></rect><rect x="216" y="58" width="48" height="16" fill="var(--s1)"></rect>
    <text x="20" y="98" fill="var(--ink)">beta</text>
    <rect x="216" y="86" width="48" height="16" fill="var(--s1)"></rect><rect x="276" y="86" width="48" height="16" fill="var(--s1)"></rect><rect x="336" y="86" width="48" height="16" fill="var(--s1)"></rect>
    <text x="20" y="126" fill="var(--ink)">gamma</text>
    <rect x="396" y="114" width="48" height="16" fill="var(--s1)"></rect><rect x="456" y="114" width="48" height="16" fill="var(--s1)"></rect>
    <rect x="216" y="56" width="48" height="48" fill="none" stroke="var(--s2)" stroke-width="2"></rect><text x="240" y="150" fill="var(--s2)" text-anchor="middle">overlap</text>
    <rect x="516" y="56" width="48" height="74" fill="none" stroke="var(--s2)" stroke-width="2" stroke-dasharray="3 2"></rect><text x="540" y="150" fill="var(--s2)" text-anchor="middle">gap</text>
  </g>
</svg>
^ The coverage map. Every file should have exactly one owner; `f3` has two (their writes collide) and `f8` has none (it is never written). A partition is this map with exactly one block filled in every column.

### Detecting the two defects

Overlaps are files with more than one owner; gaps are files with none. Two small functions.

```
# fanout.py:38-52 — COMPLETE (the two ways an assignment breaks)
def overlaps(workers):
    """Files handed to more than one worker -> {file: [owners]}. These get clobbered."""
    owners = {}
    for w, files in workers.items():
        for f in files:
            owners.setdefault(f, []).append(w)
    return {f: ws for f, ws in owners.items() if len(ws) > 1}


def gaps(files, workers):
    """Files handed to no worker -> never written."""
    owned = set()
    for fs in workers.values():
        owned |= set(fs)
    return [f for f in files if f not in owned]
```

The contract is their conjunction: an assignment is a partition when it has no overlaps and no gaps.

```
# fanout.py:55-57 — COMPLETE (the contract: disjoint and complete)
def is_partition(files, workers):
    """The contract: the assignment is a true partition -- disjoint and complete."""
    return not overlaps(workers) and not gaps(files, workers)
```

### What the naive dispatch does with the broken plan

Simulate the fan-out honestly: workers run in some order, each writes its files, and a later write to the same file overwrites the earlier one — last writer wins, exactly as two processes writing the same path would.

```
# fanout.py:62-74 — COMPLETE (last-writer-wins, and the work that vanishes)
def dispatch(files, workers):
    """Simulate the fan-out: each worker writes its files in a fixed order. A later
    write to the same file overwrites an earlier one -- last writer wins. Returns
    the final store, the lost writes, and the files nobody wrote."""
    store = {}
    lost = []
    for w in sorted(workers):                       # deterministic dispatch order
        for f in workers[w]:
            if f in store:
                lost.append((f, store[f], w))       # (file, clobbered owner, winner)
            store[f] = w
    never = [f for f in files if f not in store]
    return store, lost, never
```

`alpha` writes `f3`, then `beta` writes `f3` and overwrites it — `alpha`'s work is lost, and neither worker knows. `f8` is in no list, so it stays absent from the store. The dispatch "succeeds" with a lost write and a missing file, and nothing in the execution surfaces either.

<svg viewBox="0 0 700 150" role="img" aria-label="A timeline of writes to f3: alpha writes f3 first, then beta writes f3 and overwrites it, so the final value is beta's and alpha's write is lost. Separately, f8 has no writer and stays empty.">
  <g font-family="var(--mono)" font-size="9.5">
    <text x="20" y="20" fill="var(--muted)">f3 is written twice; the second write wins and the first is lost</text>
    <line x1="60" y1="60" x2="640" y2="60" stroke="var(--grid)"></line>
    <circle cx="180" cy="60" r="5" fill="var(--s1)"></circle><text x="150" y="48" fill="var(--s1)">alpha writes f3</text>
    <circle cx="420" cy="60" r="5" fill="var(--s2)"></circle><text x="390" y="48" fill="var(--s2)">beta writes f3</text>
    <text x="470" y="64" fill="var(--s2)">final = beta; alpha LOST</text>
    <text x="20" y="110" fill="var(--muted)">f8: no writer on the timeline at all -> never written</text>
    <rect x="60" y="120" width="200" height="18" rx="3" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"></rect><text x="66" y="133" fill="var(--s2)" font-size="8">f8: empty</text>
  </g>
</svg>
^ The lost write in time: two writers hit `f3`, the later one wins, the earlier one's work is gone with no error. `f8` never appears on any writer's timeline. Both are assignment defects, surfaced only by looking at the plan.

### The contract catches both before any work is done

Run the contract and it rejects the plan up front, naming exactly what is wrong, so no worker is dispatched and no work is lost.

```
# $ python3 fanout.py --contract
#   REJECTED: not a partition.
#     overlap: f3 owned by ['alpha', 'beta']
#     gap: f8 owned by nobody
#   fix the assignment and re-check; no work is dispatched until it passes.
```

run: 2026-08-25 · fixture · `python3 fanout.py --contract`

The self-test closes the loop: the naive plan loses a write and drops a file, the contract rejects it, a repaired partition dispatches with zero loss, and every lost write traces back to an overlap the contract flagged.

```
# $ python3 fanout.py --check
#   naive dispatch loses at least one write = True (1 lost)
#   naive dispatch never writes at least one file = True (['f8'])
#   the contract rejects this plan before dispatch = True
#   a repaired partition dispatches with no loss = True
#   every lost write was a file the contract flagged as an overlap = True
#   SELF-TEST PASS ...
```

run: 2026-08-25 · deterministic · `python3 fanout.py --check`

The repair is a repartition: move `f3` to a single owner and give `f8` an owner, so every file sits in exactly one worker's column. A valid partition is the coverage map with one and only one block filled per file — no column empty, no column doubled.

<svg viewBox="0 0 700 120" role="img" aria-label="Two coverage maps. The broken one has f3 doubled and f8 empty. The valid partition has every one of the eight files owned by exactly one worker, one filled block per column.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--s2)">broken: f3 doubled, f8 empty</text>
    <g>
      <rect x="60" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="84" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="108" y="26" width="20" height="14" fill="var(--s2)"></rect><rect x="132" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="156" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="180" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="204" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="228" y="26" width="20" height="14" fill="none" stroke="var(--s2)" stroke-dasharray="2 2"></rect>
      <text x="118" y="52" fill="var(--s2)" font-size="8">f3 x2</text><text x="230" y="52" fill="var(--s2)" font-size="8">f8 gap</text>
    </g>
    <text x="380" y="16" fill="var(--s1)">valid partition: exactly one owner each</text>
    <g>
      <rect x="420" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="444" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="468" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="492" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="516" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="540" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="564" y="26" width="20" height="14" fill="var(--s1)"></rect><rect x="588" y="26" width="20" height="14" fill="var(--s1)"></rect>
      <text x="470" y="52" fill="var(--s1)" font-size="8">f1..f8 each owned once</text>
    </g>
  </g>
</svg>
^ Broken versus valid. The contract's whole job is to insist on the right-hand shape — one owner per file, none doubled, none empty — before a single worker starts.

**A fan-out's correctness lives in the assignment, not the execution: verify the work is a true partition — every item owned exactly once — before you dispatch, because every worker can succeed while the job silently loses half its output.**

### The running tally

| stage | lost writes | never written | how you find out |
|---|---|---|---|
| naive dispatch | 1 | 1 | never — every worker reported success |
| partition contract | 0 | 0 | up front — the plan is rejected and fixed |

The workers never changed; only whether the assignment was checked before they ran. The naive path finds the damage never, because there is nothing to find in the execution — the workers are innocent, the plan is guilty. The contract moves the check to the one place the bug lives, and turns a silent data loss into a loud, fixable rejection. This is why "partitioned ownership" is written into the labs' fan-out contracts as a precondition, not a hope.

### What we did not settle

The fixture uses file ownership as the unit and last-writer-wins as the collision rule, which is the common case but not the only one. Real complications we skipped: some fan-outs *want* controlled overlap — two workers reading the same input is fine; the contract must partition *writes*, not reads, so the real check is over the write-set, not every file touched. Collisions are not always last-writer-wins — two workers appending to a shared log interleave rather than clobber, which corrupts differently and needs a merge or a lock, not a partition. And ownership can be dynamic: a worker that discovers new work mid-run expands its partition, so the contract has to be re-checked on every claim, not just at dispatch — a running invariant, not a one-time gate. The dial here is a static file partition; the real system enforces the same disjoint-and-complete invariant continuously over writes.

## Build

The pipeline in one paragraph: before dispatching a fan-out, collect each worker's set of owned work items; check that the union covers every item (no gaps) and that no item appears in two workers' sets (no overlaps); reject and fix the assignment if either fails; and re-run the check whenever a worker claims new work mid-run. Never trust that a fan-out where every worker succeeded produced correct output — check the partition, not the exit codes.

We opened on the silent damage. The contract that prevents it:

```
# modules/orchestration-and-governance/code/govern-inter-03/ — COMPLETE, run from that directory
$ python3 fanout.py --contract
  REJECTED: not a partition.  (overlap: f3; gap: f8)
```

Now check your own fan-out. Take a real dispatch plan — the files a set of subagents will write, or the tasks a worker pool will own — and run the partition check over the write-sets. Your number to beat is **lost writes plus dropped items at zero**: a fan-out that loses any work is broken no matter how clean its logs. Construct a plan with a deliberate overlap and a deliberate gap and confirm the contract names both before dispatch while the naive run hides both. Bring back the overlap and gap lists and the repaired partition. Good luck.

## Definition of done

- [ ] A fan-out assignment: each worker's set of owned work items
- [ ] An overlap check (items owned by more than one worker) and a gap check (items owned by none)
- [ ] A partition contract that rejects an assignment that is not disjoint and complete, before dispatch
- [ ] Your own `plan.json` with at least one deliberate overlap and one gap
- [ ] A simulated dispatch that shows the lost writes and never-written items the naive path produces
- [ ] `python3 fanout.py --check` printing SELF-TEST PASS: naive loses and drops, contract rejects, repaired partition is clean, losses trace to overlaps
- [ ] The overlap and gap lists recorded, and the repaired partition that dispatches with zero loss
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Three workers all reported success and the job still came out wrong. Name the two assignment defects that cause this and why neither surfaces as a worker error.
2. Define a partition in terms of disjoint and complete, and say which defect each of those two words rules out.
3. In the fixture, `alpha`'s work on `f3` was lost. Walk through the dispatch and explain the last-writer-wins mechanism.
4. The what-we-did-not-settle section says to partition writes, not reads. Why is a read overlap fine and a write overlap not?
5. Your own fan-out plan had an overlap and a gap. What were they, and how did you repartition to fix them?

## External resources

- faisalmahdy/ai-engineer-learning — the 8+8+8 subagent fan-out with partitioned ownership — my summary: a real fan-out whose worker contracts require disjoint ownership; read it for how partitioned ownership scales to dozens of workers, and note the contract is a precondition checked before dispatch, exactly as here.
- faisalmahdy/agents-workspace-files — `GOVERNANCE.md` — my summary: the governance rules that gate agent output, including ownership and provenance; read it for how a partition contract sits inside a larger PR-gated pipeline, the subject of this track's later modules.
- Kleppmann, *Designing Data-Intensive Applications*, ch. 5 (replication) and ch. 7 (the lost-update problem) — https://dataintensive.net/ — my summary: the canonical treatment of concurrent writes and lost updates; read it for why last-writer-wins silently loses data and how partitioning and locks address it — the database version of this module's fan-out bug.
