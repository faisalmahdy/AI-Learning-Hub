---
id: flag-inter-01
title: Ship features behind a runtime flag — rolling back the deploy to disable one bad feature also reverts every good feature shipped since
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: When release is coupled to deploy, a feature goes live the instant its code deploys and the only off-switch is another deploy — and that is fine until a feature already in production turns out to be broken and you need it gone now. To disable it you roll the deployable artifact back to the version before that feature was introduced, but every feature deployed after it is baked into later versions of that same artifact, so rolling back past the bug takes those later features with it. On the fixture three features ship in order — checkout_v2 (buggy), then search_filters, then dark_mode — and rolling back to before checkout_v2 leaves nothing live: the two good features shipped afterward are reverted too. The alternative, writing and deploying a forward fix, costs the time an incident does not have. A feature flag breaks the coupling: the feature's code is deployed but gated behind a runtime flag, so disabling it is a configuration change rather than a deploy, and flipping checkout_v2's flag off leaves search_filters and dark_mode running while removing only the bug. Deploy ships the code, the flag releases the feature, and the two being separate is what lets you undo a release without undoing unrelated deploys. The rule: ship risky features behind runtime flags so a bad one can be turned off in place, because the deploy-rollback alternative reverts everything that shipped after it — the release you want to undo is coupled to deploys you do not.
eli5: Imagine your house has one big master switch for all the lights, and you added the porch light first, then the kitchen light, then the bedroom light, all on that one switch. Now the porch light is sparking and dangerous. To turn just it off, your only option is to go back to before you wired the porch light — which means unwiring the kitchen and bedroom lights too, because they were added afterward on the same circuit. Everything goes dark to fix one bulb. The better way is to give each light its own switch when you install it: then the sparking porch light gets flipped off by itself, and the kitchen and bedroom stay on. A feature flag is that per-feature switch — you can turn one thing off without tearing out everything built after it.
---

## Why this module

The scariest moment in operations is discovering that a feature already serving production traffic is broken — corrupting data, erroring, leaking. The clock is running, and the question is how fast you can make it stop. If your only tool is the deploy pipeline, the answer is worse than it looks.

The trouble is that a deploy is usually one artifact — one container image, one build — that accumulates features over time. The broken feature was added in some past deploy, and every deploy since layered more features on top of the same artifact. There is no version of the artifact that has the later features but not the broken one, because the broken one came first. So "roll back to before the bug" and "keep the good work shipped since" are mutually exclusive when the only unit you can move is the whole artifact.

This module makes that concrete: three features deployed in order, the first one buggy. Rolling back to before it leaves nothing live — the two good features that shipped afterward are gone too. Then it adds a runtime flag to the buggy feature and flips it off: the bug is disabled and the two good features keep running, with no deploy at all. The difference is whether release is coupled to deploy.

**When the only off-switch for a feature is a deploy, disabling an old feature means rewinding to before it — which discards everything built on top, so the cost of turning off one bad feature is every good feature shipped since.**

## Concepts

Separate two events that a naive pipeline fuses into one. Deploy is putting code onto the servers. Release is making a feature's behavior active for users. When they are the same event — the feature runs the moment its code is present — you have no way to talk about one feature independently of the artifact it rode in on.

That fusion is what makes rollback so blunt. The deployable artifact is a stack: each deploy adds a layer, and rolling back means popping layers off the top back to an earlier version. To remove a feature that was added early, you have to pop every layer above it, because those layers are later versions of the same artifact and they contain the early feature plus everything after. Rollback can only move in whole versions along that stack; it cannot reach in and remove one layer from the middle.

A feature flag adds exactly that ability. The feature's code ships in the artifact like any other, but it is wrapped in a conditional on a runtime flag, so whether it actually runs is decided by configuration read at request time, not by which version is deployed. Now release is flipping the flag, and un-release is flipping it back — a configuration change that touches one feature and leaves the deployed artifact, with all its other features, exactly where it is.

This decoupling is why teams "deploy dark": ship a feature's code with its flag off, so deploying it changes nothing for users, then release it later by flipping the flag — and disable it instantly if it misbehaves. The deploy and the release are now independent axes, and an incident on one feature is handled by moving only that feature's flag, never by rewinding the whole artifact.

<svg role="img" aria-label="A stack of deploy versions. Version 1 adds the buggy checkout_v2, version 2 adds search_filters on top, version 3 adds dark_mode on top. An arrow shows that rolling back to before checkout_v2 must pop all three layers, removing search_filters and dark_mode too" viewBox="0 0 640 220">
<rect x="80" y="150" width="200" height="34" fill="var(--s2)" opacity="0.55" stroke="var(--line)"/>
<text x="180" y="172" fill="var(--ink)" font-size="11" text-anchor="middle">v1: + checkout_v2 (buggy)</text>
<rect x="80" y="112" width="200" height="34" fill="var(--panel)" stroke="var(--line)"/>
<text x="180" y="134" fill="var(--ink)" font-size="11" text-anchor="middle">v2: + search_filters</text>
<rect x="80" y="74" width="200" height="34" fill="var(--panel)" stroke="var(--line)"/>
<text x="180" y="96" fill="var(--ink)" font-size="11" text-anchor="middle">v3: + dark_mode</text>
<line x1="300" y1="167" x2="360" y2="167" stroke="var(--s2)" stroke-width="1.5"/>
<polygon points="360,167 352,162 352,172" fill="var(--s2)"/>
<text x="470" y="150" fill="var(--muted)" font-size="11" text-anchor="middle">roll back to before v1</text>
<text x="470" y="168" fill="var(--s2)" font-size="11" text-anchor="middle">pops v2 and v3 too</text>
<text x="470" y="186" fill="var(--muted)" font-size="10" text-anchor="middle">good features go with the bug</text>
</svg>
^ The artifact is a stack of versions; removing the early buggy feature means popping every later version off, so the good features layered on top are reverted with it.

**Deploy and release are different actions, and coupling them means the only granularity you can undo is a whole artifact version — a flag restores per-feature granularity, so you can undo one release without touching any deploy.**

## Worked example

The fixture is three features deployed in order, the first one buggy.

```json filename=modules/ship-and-operate/code/flag-inter-01/flag.json:3-7 COMPLETE
  "deploys": [
    {"name": "checkout_v2", "buggy": true},
    {"name": "search_filters", "buggy": false},
    {"name": "dark_mode", "buggy": false}
  ]
```

Rolling back to before the bug keeps only the features deployed before it.

```python filename=modules/ship-and-operate/code/flag-inter-01/flag.py:35-37 COMPLETE
def live_after_rollback(deploys):
    """Rolling the artifact back to before the bug keeps only the features deployed before it."""
    return [d["name"] for d in deploys[:buggy_index(deploys)]]
```

Flipping the flag off keeps every deployed feature except the one flagged off.

```python filename=modules/ship-and-operate/code/flag-inter-01/flag.py:40-42 COMPLETE
def live_after_flag(deploys):
    """Flipping the bug's flag off keeps every deployed feature except the one flagged off."""
    return [d["name"] for d in deploys if not d["buggy"]]
```

The good features lost are the non-buggy ones a mitigation takes down with the bug.

```python filename=modules/ship-and-operate/code/flag-inter-01/flag.py:45-47 COMPLETE
def good_features_lost(deploys, live):
    """Non-buggy features that were deployed but are not live under this mitigation."""
    return [d["name"] for d in deploys if not d["buggy"] and d["name"] not in live]
```

Rolling back disables the bug but takes the later good features with it.

```text filename=flag.py --rollback
ROLLBACK — disable the bug by reverting the deploy to before it
----------------------------------------------------------------
  deploy order: ['checkout_v2', 'search_filters', 'dark_mode']
  roll back to before 'checkout_v2' -> live features: []
  good features lost: ['search_filters', 'dark_mode']
  needed a new deploy? yes
----------------------------------------------------------------
  the bug is gone, but so is every good feature shipped after it
```

Because checkout_v2 was first, rolling back to before it leaves nothing — search_filters and dark_mode, shipped afterward, are reverted too. The flag disables only the bug.

```text filename=flag.py --flag
FLAG — disable the bug by flipping its runtime flag off
----------------------------------------------------------------
  deploy order: ['checkout_v2', 'search_filters', 'dark_mode']
  flag 'checkout_v2' off -> live features: ['search_filters', 'dark_mode']
  good features lost: []
  needed a new deploy? no (a config change)
----------------------------------------------------------------
  only the buggy feature is gone; the rest keep running
```

The flag leaves search_filters and dark_mode running and turns off checkout_v2 with a configuration change, no deploy. The figure contrasts what survives each mitigation.

<svg role="img" aria-label="Two outcomes. Under rollback, all three features checkout_v2, search_filters, dark_mode are struck through — nothing live. Under flag, checkout_v2 is struck through but search_filters and dark_mode remain live." viewBox="0 0 640 210">
<text x="160" y="28" fill="var(--ink)" font-size="12" text-anchor="middle">rollback</text>
<text x="160" y="58" fill="var(--s2)" font-size="11" text-anchor="middle" text-decoration="line-through">checkout_v2 (bug)</text>
<text x="160" y="82" fill="var(--s2)" font-size="11" text-anchor="middle" text-decoration="line-through">search_filters</text>
<text x="160" y="106" fill="var(--s2)" font-size="11" text-anchor="middle" text-decoration="line-through">dark_mode</text>
<rect x="60" y="122" width="200" height="28" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="5"/>
<text x="160" y="141" fill="var(--s2)" font-size="11" text-anchor="middle">2 good features lost</text>
<text x="480" y="28" fill="var(--ink)" font-size="12" text-anchor="middle">flag off</text>
<text x="480" y="58" fill="var(--s2)" font-size="11" text-anchor="middle" text-decoration="line-through">checkout_v2 (bug)</text>
<text x="480" y="82" fill="var(--s1)" font-size="11" text-anchor="middle">search_filters ✓</text>
<text x="480" y="106" fill="var(--s1)" font-size="11" text-anchor="middle">dark_mode ✓</text>
<rect x="380" y="122" width="200" height="28" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="5"/>
<text x="480" y="141" fill="var(--s1)" font-size="11" text-anchor="middle">0 good features lost</text>
</svg>
^ Both remove the bug; the rollback removes the two good features with it, the flag removes only the bug.

**The rollback and the flag both disable checkout_v2 — the entire difference is the collateral, two good features versus none, and that collateral is the price of not being able to move one feature independently.**

## Build

The self-test pins the asymmetry: the rollback disables the bug but also reverts good features shipped after it, while the flag disables the bug and keeps them all.

```python filename=modules/ship-and-operate/code/flag-inter-01/flag.py:88-95 COMPLETE
    bug_deployed_first = buggy_index(deploys) == 0
    print("  the buggy feature was deployed before good ones = %s (%r first)" % (bug_deployed_first, bug))

    rollback_disables_bug = bug not in rb_live
    print("  rollback disables the bug = %s" % rollback_disables_bug)

    rollback_reverts_good = len(good_features_lost(deploys, rb_live)) > 0
    print("  rollback also reverts good features shipped after it = %s (%s)" % (rollback_reverts_good, good_features_lost(deploys, rb_live)))
```

The remaining flags confirm the flag disables the bug and keeps every good feature. All five pass.

```text filename=flag.py --check
SELF-TEST — the rollback reverts the good features shipped after the bug while the flag disables only the buggy one
----------------------------------------------------------------------------------------------------------------
  the buggy feature was deployed before good ones = True ('checkout_v2' first)
  rollback disables the bug = True
  rollback also reverts good features shipped after it = True (['search_filters', 'dark_mode'])
  the flag disables the bug = True
  the flag keeps every good feature = True (live ['search_filters', 'dark_mode'])
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  bug_deployed_first=True  rollback_disables_bug=True  rollback_reverts_good=True  flag_disables_bug=True  flag_keeps_good=True
```

**Both mitigations set `rollback_disables_bug` and `flag_disables_bug` true — the bug dies either way — so the module's whole content is `rollback_reverts_good`, the collateral the flag avoids.**

## Definition of done

You are done when features that carry rollout risk ship behind runtime flags, so releasing and un-releasing a feature is a configuration change independent of the deploy that shipped its code.

The pattern is deploy-dark then release: merge and deploy the feature with its flag defaulted off, so the deploy is a no-op for users and can be verified in production before anyone sees the feature; then flip the flag to release, and flip it back to disable — with a kill switch on anything risky so mitigation is a seconds-long config change, not a deploy. Flags cost discipline in return: each one is a branch in the code that must be tested in both states, and a flag left on forever becomes permanent dead complexity, so retire a flag once the feature is stable and the code path is settled. And flags are not a universal replacement for rollback — a change to a database schema, a data migration, or the deploy artifact itself still needs real rollback machinery and backward-compatible steps (which is why this pairs with expand-contract migrations and a warm previous version); the flag decouples the release of behavior, not every kind of change.

<svg role="img" aria-label="Two independent axes. The deploy axis moves code onto servers with the feature flag off (dark). The release axis flips the flag on to release and off to disable, each a config change, without moving the deploy axis." viewBox="0 0 640 200">
<line x1="60" y1="150" x2="420" y2="150" stroke="var(--line)" stroke-width="1.5"/>
<text x="240" y="172" fill="var(--muted)" font-size="11" text-anchor="middle">deploy (ship code, flag off = dark) →</text>
<circle cx="140" cy="150" r="5" fill="var(--ink)"/>
<circle cx="260" cy="150" r="5" fill="var(--ink)"/>
<circle cx="380" cy="150" r="5" fill="var(--ink)"/>
<line x1="500" y1="60" x2="500" y2="150" stroke="var(--line)" stroke-width="1.5"/>
<text x="500" y="172" fill="var(--muted)" font-size="10" text-anchor="middle">release axis</text>
<rect x="440" y="52" width="120" height="26" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="5"/>
<text x="500" y="70" fill="var(--ink)" font-size="10" text-anchor="middle">flag on = release</text>
<rect x="440" y="98" width="120" height="26" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="5"/>
<text x="500" y="116" fill="var(--ink)" font-size="10" text-anchor="middle">flag off = disable</text>
<text x="300" y="30" fill="var(--ink)" font-size="11" text-anchor="middle">deploy and release move independently</text>
</svg>
^ Deploying ships code dark; releasing and disabling move the flag on the other axis, so a feature's state changes without a deploy.

**Deploy-dark-then-release turns a release into a reversible config change on its own axis, so the feature you must disable in an incident is never entangled with the deploys that shipped after it.**

## Boss fight

Your turn: move the bug later in the deploy order and watch the rollback cost shrink — then see why it is still the wrong tool. Mark dark_mode buggy instead of checkout_v2 and rerun `--rollback`. Now the bug shipped last, so rolling back to before it keeps checkout_v2 and search_filters and only loses dark_mode itself — the rollback is cheap because there is nothing good on top of the bug. This is the tell for when coupled deploy-rollback happens to be tolerable: only when the broken feature is the most recent thing shipped. The moment anything good ships after a latent bug, the rollback's collateral reappears, and you do not get to choose which of your features breaks first.

Then confront the flag's own failure mode, so you do not treat it as free. Add a fourth "feature" that is a database migration — a change to the schema, not a gated code path — and try to disable it with a flag. You cannot: the schema changed the moment the migration ran, and a flag over a code path does not un-migrate a table. Flags decouple the release of behavior that lives behind a runtime conditional; they do nothing for changes that alter state the moment they deploy. This is why real systems pair flags with expand-contract migrations (so schema changes are themselves reversible in stages) and with a warm previous version for the changes a flag cannot cover. The discipline is knowing which changes a flag can gate — behavior behind a conditional — and which still need genuine rollback machinery, and never assuming a flag makes every change safe.

**A flag makes gated behavior reversible with a config change, but a schema change or a data migration takes effect at deploy time and no flag un-does it — so flags cover the releases that live behind a conditional and leave the state-changing deploys to expand-contract and real rollback.**

## External resources

Martin Fowler's writing on "feature toggles" is the canonical taxonomy — release toggles, ops toggles, kill switches, experiment toggles — and covers the discipline of retiring toggles before they become permanent complexity.

The continuous-delivery literature (Humble and Farley's "Continuous Delivery") makes the decouple-deploy-from-release argument in full, including deploying dark and using flags to separate the technical act of deploying from the business act of releasing.

Feature-management platforms' documentation (LaunchDarkly, Unleash, and similar) describes the operational side — kill switches, gradual rollouts, and targeting — and is the practical guide to running flags at scale, including the flag-lifecycle hygiene the boss fight warns about.
