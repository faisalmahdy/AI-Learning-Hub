---
id: ship-inter-15
title: Migrate a schema in expand-contract steps — a one-shot rename breaks the half-deployed fleet
topic: ship-and-operate
level: intermediate
status: ready
time: 21 min
summary: A rolling deploy runs old and new instances side by side for a window, so a schema change must be readable by both. A one-shot column rename has no schema that satisfies both — while the old column exists new code fails, and the moment you rename old code fails — so half the fleet errors during the rollout. Expand-contract makes it three safe steps: add the new column (both work), backfill, then drop the old only after the old version is gone. On the fixture the one-shot rename breaks a live version; expand-contract has zero breaking steps.
eli5: When you upgrade a team, for a while some people follow the old playbook and some the new one. If you throw out the old playbook the instant you print the new one, half the team is lost. Instead you hand out the new playbook while the old one still works, wait until everyone has switched, and only then recycle the old one. Nobody is ever without a playbook they can read.
---

## Why this module

A database rename is one instant to the database and a disaster to a fleet that is only half-upgraded, because for a while both the old and new code are live at once.

A rolling deploy never flips every instance at the same moment. New instances come up while old ones are still serving, and for a window — seconds to minutes — the two versions run side by side against the same database. That overlap is the whole reason deploys are safe (you can roll back, you never have zero capacity), but it imposes a rule on schema changes: any change you make to the database during that window has to be readable by both the old code and the new code, because both are live and both are hitting the same tables.

A one-shot rename violates that rule with no way to satisfy it. Say the old code reads a column `name` and the new code reads `full_name`. To rename in one step you drop `name` and add `full_name`. But think about the overlap: while `name` still exists, the new instances that read `full_name` fail; the instant you rename, the old instances that read `name` fail. There is no single schema that has the column both versions need, because they need different columns. So one deploy of a rename means that throughout the rollout, one half of your fleet is throwing errors on every request that touches that column. The database call was atomic and correct; the fleet-wide effect was an outage.

Expand-contract (also called parallel change) fixes this by turning the rename into a sequence of individually backward-compatible steps, none of which ever removes a column a running version needs. Expand: add the new column alongside the old, so the schema has both — old code reads the old column, new code reads the new one, and both work. Deploy the new code across the fleet. Backfill: copy the data from the old column to the new. Only once every instance is the new version — so nothing reads the old column anymore — do you contract: drop the old column. The rename is spread over three deploys, and at no single moment does any live version lack a column it needs.

On the fixture, the old version reads `name` and the new reads `full_name`. The one-shot rename has a step where both versions run against a schema with only one of the columns, so one version breaks. The expand-contract plan keeps both columns present while both versions run, and drops the old column only after the old version is gone: zero breaking steps.

**A rolling deploy runs old and new code against one database at once, so a schema change must satisfy both versions; a one-shot rename cannot, because they need different columns, so it breaks half the fleet — expand-contract adds the new column before requiring it and drops the old only after nothing reads it, so every step is backward compatible.**

## Concepts

The governing constraint is that during a deploy, the set of running code versions is not a single version — it is old and new together — and the schema must be compatible with the intersection of what they all need. Compatibility with the new code alone is not enough, and neither is compatibility with the old; the live schema has to serve every version that is currently taking traffic. A migration step is safe exactly when every running version can still find the columns it reads. A one-shot rename fails this because the old and new versions read disjoint columns, and no schema contains a column that is simultaneously present (for new) and the old name (for old) — the requirement is contradictory during the overlap.

Expand-contract dissolves the contradiction by never letting the requirements be contradictory at the same time. It does so by ordering the schema and code changes so that "add" always precedes "require" and "stop using" always precedes "remove." Concretely: you add the new column before any code depends on it (expand), you get all code onto the new column before you remove the old one (contract), and in between there is a period where the schema is a superset — it carries both columns — so it satisfies both versions at once. The superset step is the key: it is the bridge that lets you swap the code underneath without the schema ever dropping below what a live version needs.

<svg role="img" aria-label="Additive changes are safe before their code; destructive changes are safe only after their code retires; expand-contract puts adds first and drops last" viewBox="0 0 470 165" width="470" height="165">
  <rect x="0" y="0" width="470" height="165" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">safe ordering of schema vs code changes</text>
  <line x1="30" y1="90" x2="440" y2="90" stroke="var(--line)"/>
  <rect x="50" y="60" width="110" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="58" y="76" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">ADD column (expand)</text>
  <rect x="180" y="60" width="110" height="24" fill="var(--panel)" stroke="var(--line)"/>
  <text x="188" y="76" font-family="var(--mono)" font-size="7" fill="var(--ink)">deploy new code</text>
  <rect x="310" y="60" width="120" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="318" y="76" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">DROP column (contract)</text>
  <text x="55" y="108" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">before its code ✓</text>
  <text x="315" y="108" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">after its code retires ✓</text>
  <text x="185" y="130" font-family="var(--mono)" font-size="7" fill="var(--s2)">a destructive change here (with old code live) breaks it</text>
  <line x1="240" y1="112" x2="240" y2="90" stroke="var(--s2)"/>
</svg>
^ Additive changes (add a column) go before the code that needs them; destructive changes (drop a column) go after the code that used them retires — expand-contract is that rule run end to end.

The ordering is asymmetric in a way worth internalizing: additive changes are safe to make before the code that uses them, and destructive changes are safe to make only after the code that used them is gone. Adding a column, adding a nullable field, adding a new table — these never break existing code, because existing code simply ignores them, so they can go first. Dropping a column, removing a field, tightening a constraint — these break any code still using the old shape, so they must go last, after that code is fully retired. Expand-contract is just this rule applied end to end: do all the additive work up front, migrate the readers and writers across, and do the destructive work at the very end.

This generalizes far beyond a rename and is the backbone of zero-downtime schema evolution. Changing a column's type becomes: add a new column of the new type, dual-write to both, backfill, switch reads, drop the old. Splitting a table, adding a NOT NULL constraint, changing an enum — all follow the same expand, migrate, contract shape, often with a dual-write phase where the new code writes both the old and new locations so a rollback is safe. The cost is real: a migration that could be one line becomes three or more deploys spread over time, with a period of duplicated data. But the alternative is a schema change that is only safe if you take downtime (stop the fleet, migrate, start the new fleet), and expand-contract is precisely what buys zero-downtime deploys for stateful changes.

**A migration step is safe only if every running version can read what it needs, and a rolling deploy makes "every running version" mean old and new together; expand-contract orders additive changes before their code and destructive changes after their code retires, with a both-columns bridge step, so the requirement is never contradictory.**

## Worked example

The fixture is the two versions' column requirements and two migration plans.

```json filename=modules/ship-and-operate/code/ship-inter-15/migration.json:3-16 COMPLETE
  "requires": {"old": "name", "new": "full_name"},
  "plans": {
    "one-shot-rename": [
      {"cols": ["full_name"], "running": ["old", "new"]}
    ],
    "expand-contract": [
      {"cols": ["name"], "running": ["old"]},
      {"cols": ["name", "full_name"], "running": ["old", "new"]},
      {"cols": ["full_name"], "running": ["new"]}
    ]
  }
```

The old version reads `name`, the new reads `full_name`. The one-shot plan is a single step: rename to `full_name` while both versions are live during the rollout. A step breaks a version when that version's required column is absent from the schema.

```python filename=modules/ship-and-operate/code/ship-inter-15/migrate.py:42-50 COMPLETE
def broken_versions(step, requires):
    """Running versions whose required column is absent from this step's schema."""
    cols = set(step["cols"])
    return [v for v in step["running"] if requires[v] not in cols]


def breaking_steps(plan, requires):
    """Steps of a plan where at least one running version is broken."""
    return [(i, broken_versions(s, requires)) for i, s in enumerate(plan) if broken_versions(s, requires)]
```

Predict: the one-shot step has `full_name` only, but `old` (still running during the rollout) needs `name`, so `old` breaks. The expand-contract steps each keep every running version's column present. Look at the plans.

```text filename=modules/ship-and-operate/code/ship-inter-15/migrate.py --plan
PLAN — each plan's steps (schema columns and running versions)
--------------------------------------------------------------
  one-shot-rename:
    step 0  cols ['full_name']          running ['old', 'new']
  expand-contract:
    step 0  cols ['name']               running ['old']
    step 1  cols ['name', 'full_name']  running ['old', 'new']
    step 2  cols ['full_name']          running ['new']
--------------------------------------------------------------
  versions require: {'old': 'name', 'new': 'full_name'}
```

The one-shot plan renames in a single step, and during that step both `old` and `new` are running against a schema that has only `full_name`. The expand-contract plan has three steps: start with only `old` running on `name`; the middle step carries both columns while both versions run; the last step has dropped `name` but only `new` is running. Now compute the breaks.

```text filename=modules/ship-and-operate/code/ship-inter-15/migrate.py --breaks
BREAKS — steps that break a running version
--------------------------------------------------------------
  one-shot-rename  step 0 BREAKS ['old'] (cols ['full_name'])
  expand-contract  no breaking steps
--------------------------------------------------------------
  only expand-contract is safe at every step.
```

The one-shot rename's single step breaks `old`: it is still serving traffic and reads `name`, which the rename just removed, so every request the old instances handle for that column fails until the rollout finishes replacing them. Expand-contract has no breaking step. Its middle step is why: the schema carries both `name` and `full_name` while both versions run, so `old` finds `name` and `new` finds `full_name`. The old column is dropped only in the last step, by which point `old` is no longer running and nothing reads it. Same rename, reached safely by never removing a column a live version needs.

<svg role="img" aria-label="One-shot rename: during the overlap the schema has only full_name so old breaks; expand-contract: the middle step has both columns so both versions read, and old is dropped only after old is gone" viewBox="0 0 470 210" width="470" height="210">
  <rect x="0" y="0" width="470" height="210" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">schema columns vs running versions per step</text>
  <text x="20" y="42" font-family="var(--mono)" font-size="9" fill="var(--s2)">one-shot</text>
  <rect x="100" y="30" width="150" height="30" fill="var(--panel)" stroke="var(--s2)"/>
  <text x="108" y="43" font-family="var(--mono)" font-size="7" fill="var(--ink)">cols: [full_name]</text>
  <text x="108" y="55" font-family="var(--mono)" font-size="7" fill="var(--s2)">running: old + new  → old BREAKS</text>
  <text x="20" y="96" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">expand-contract</text>
  <rect x="60" y="86" width="115" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="66" y="99" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">[name]</text>
  <text x="66" y="111" font-family="var(--mono)" font-size="7" fill="var(--muted)">old only ✓</text>
  <rect x="180" y="86" width="130" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="186" y="99" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">[name, full_name]</text>
  <text x="186" y="111" font-family="var(--mono)" font-size="7" fill="var(--muted)">old + new ✓ (bridge)</text>
  <rect x="315" y="86" width="115" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"/>
  <text x="321" y="99" font-family="var(--mono)" font-size="7" fill="var(--acc-ink)">[full_name]</text>
  <text x="321" y="111" font-family="var(--mono)" font-size="7" fill="var(--muted)">new only ✓</text>
  <text x="60" y="140" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">expand →</text>
  <text x="185" y="140" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">both columns bridge →</text>
  <text x="320" y="140" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">contract</text>
  <text x="30" y="180" font-family="var(--mono)" font-size="8" fill="var(--muted)">the middle step carries both columns, so the code can swap underneath</text>
  <text x="30" y="196" font-family="var(--mono)" font-size="8" fill="var(--muted)">without the schema ever dropping below what a live version needs</text>
</svg>
^ The one-shot step's schema lacks `name` while `old` is still live, so `old` breaks; expand-contract's middle step carries both columns during the overlap and drops `name` only once `old` is gone.

## Build

Reproduce the breaks. Pure standard library, deterministic, so the one-shot's broken `old` and expand-contract's clean run come out exactly.

Run `--plan` for the steps, `--breaks` for which steps break a version, `--check` for the gate. A step's broken versions come from one check — the running versions whose required column is missing from that step's schema.

```python filename=modules/ship-and-operate/code/ship-inter-15/migrate.py:42-45 COMPLETE
def broken_versions(step, requires):
    """Running versions whose required column is absent from this step's schema."""
    cols = set(step["cols"])
    return [v for v in step["running"] if requires[v] not in cols]
```

<svg role="img" aria-label="Bar of breaking steps per plan: one-shot rename has one breaking step, expand-contract has zero across its three steps" viewBox="0 0 470 150" width="470" height="150">
  <rect x="0" y="0" width="470" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">breaking steps per plan (lower is safer)</text>
  <line x1="60" y1="120" x2="450" y2="120" stroke="var(--line)"/>
  <rect x="90" y="60" width="90" height="60" fill="var(--s2)"/>
  <text x="95" y="54" font-family="var(--mono)" font-size="8" fill="var(--s2)">one-shot: 1 of 1</text>
  <text x="100" y="90" font-family="var(--mono)" font-size="7" fill="var(--panel)">breaks old</text>
  <rect x="290" y="116" width="90" height="4" fill="var(--acc-line)"/>
  <text x="295" y="110" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">expand-contract: 0 of 3</text>
</svg>
^ Every step of the one-shot plan (all one of them) breaks a live version, while none of expand-contract's three steps does — the safety is per-step, at every step.

The self-test pins the one-shot break, that it happens during the overlap, and expand-contract's safety.

```python filename=modules/ship-and-operate/code/ship-inter-15/migrate.py:91-95 COMPLETE
    onestep_breaks = len(one_breaks) > 0
    print("  the one-shot rename has a breaking step = %s (%d)" % (onestep_breaks, len(one_breaks)))

    breaks_during_overlap = any(len(one[i]["running"]) > 1 for i, _ in one_breaks)
    print("  the break happens while both versions run (the deploy overlap) = %s" % breaks_during_overlap)
```

The two expand-contract flags encode the recipe directly: keep both columns through the overlap, and only drop the old one once no version that reads it is still running.

```python filename=modules/ship-and-operate/code/ship-inter-15/migrate.py:100-104 COMPLETE
    both_cols_during_overlap = all(set(requires.values()) <= set(s["cols"]) for s in exp if len(s["running"]) > 1)
    print("  expand-contract keeps both columns while both versions run = %s" % both_cols_during_overlap)

    contract_only_after_old_gone = all("old" not in s["running"] for s in exp if requires["old"] not in s["cols"])
    print("  the old column is dropped only after the old version is gone = %s" % contract_only_after_old_gone)
```

```text filename=modules/ship-and-operate/code/ship-inter-15/migrate.py --check
SELF-TEST — the one-shot rename breaks a live version; expand-contract never does
------------------------------------------------------------------------------------------
  the one-shot rename has a breaking step = True (1)
  the break happens while both versions run (the deploy overlap) = True
  expand-contract has no breaking step = True
  expand-contract keeps both columns while both versions run = True
  the old column is dropped only after the old version is gone = True
------------------------------------------------------------------------------------------
SELF-TEST PASS  onestep_breaks=True  breaks_during_overlap=True  expand_contract_safe=True  both_cols_during_overlap=True  contract_after_old_gone=True
```

Five True flags. Onestep_breaks: the one-shot rename has a breaking step. Breaks_during_overlap: it breaks while both versions run — the deploy window, not some edge case. Expand_contract_safe: expand-contract has no breaking step. Both_cols_during_overlap: because it keeps both columns present whenever both versions are live. Contract_after_old_gone: and it drops the old column only after the old version is gone. The last two flags are the recipe — carry both columns through the overlap, and contract only after the readers are retired.

**The overlap flag is the crux — the one-shot rename does not break at some rare moment but for the entire duration of the rollout, because that whole window has both versions live against a schema only one of them can read.**

## Definition of done

You are done when you reproduce the one-shot break and expand-contract's safety, and can explain the ordering rule.

Concretely: `--plan` shows the one-shot single step with both versions on a `full_name`-only schema, and expand-contract's three steps with the both-columns bridge; `--breaks` shows the one-shot breaking `old` and expand-contract clean; `--check` prints PASS with five True flags. You can explain that a rolling deploy runs old and new together so the schema must satisfy both, that a rename needs contradictory columns during the overlap, and that expand-contract orders additive changes before their code and destructive changes after their code retires, with a both-columns bridge step. You can extend the pattern to type changes and constraints (add, dual-write, backfill, switch, drop).

The habit to carry: never make a destructive schema change (drop, rename, tighten) in the same deploy as the code that stops needing the old shape — split it into expand (add), migrate (deploy + backfill), and contract (drop) across separate releases, and drop the old shape only after the last instance using it is gone. When a deploy causes a burst of errors on one column that clears once the rollout finishes, suspect a one-shot destructive migration hitting the not-yet-updated half of the fleet.

## Boss fight

The instructive failure is a "simple column rename" that takes the checkout service down for the length of every deploy.

An engineer renames `user.email_address` to `user.email` in a single migration bundled with the code that reads the new name. The migration runs at deploy time, and for the two minutes the rolling deploy takes, the still-old instances query `email_address`, which no longer exists, and every checkout they handle 500s — a partial outage that mysteriously heals itself once the rollout completes, so it is easy to misdiagnose as a transient. The fix is expand-contract: deploy one release that adds `email` and dual-writes both columns, backfill `email` from `email_address`, deploy the release that reads `email`, and only in a later release drop `email_address` — each step backward compatible, no instance ever missing a column it reads.

Your turn, two moves. First, break expand-contract on purpose by reordering: put the contract (drop `name`) before the new code is fully rolled out — a step with `cols` of only `full_name` while `old` still runs — and confirm the checker now flags a break, showing the ordering (contract last) is what makes it safe, not the mere existence of a middle step. Second, model a column type change: add columns for old-type and new-type, a dual-write step where both versions run and both columns are present, then contract the old — and confirm the same expand-contract shape gives zero breaks, generalizing the pattern beyond a rename.

## External resources

The expand-contract (parallel change) pattern is documented by Martin Fowler and others as the standard approach to evolving a database without downtime, with exactly the add-migrate-contract sequencing this module models.

Tooling for zero-downtime migrations (gh-ost, pt-online-schema-change, and framework guides for Rails, Django, and Flyway) encodes the same rules — additive changes are safe, destructive ones require the readers to be gone first — and reading their safety checks shows the pattern enforced in practice.

Any treatment of rolling deploys and backward/forward compatibility (in the continuous-delivery literature) frames the general principle: during a deploy multiple versions run at once, so every change to shared state must be compatible with all of them.
