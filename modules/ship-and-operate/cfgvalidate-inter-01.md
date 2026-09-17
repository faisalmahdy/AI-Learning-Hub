---
id: cfgvalidate-inter-01
title: Validate the whole config at startup and refuse to boot on any error — lazy per-field checks crash in production one field at a time
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A configuration value is only checked when something reads it, and a service reads its fields on a schedule set by traffic, not by you — the port at boot, a timeout on the first outbound call, a feature mode only when that feature is exercised, a retry count only when something fails. So if validation is lazy, each field checked the moment it is first accessed, an invalid value stays hidden until the request that happens to touch it arrives, and only then does the service crash — in production, mid-traffic, one bad field at a time, while every other bad field is still hiding behind its own code path. Worse, an invalid field on a path no request exercised in testing is never caught, so it ships and waits. On the fixture the config has three invalid fields (port 70000 out of range, timeout −5, mode "turbo"), and the running service reads workers, then retries, then timeout: the lazy run serves two requests fine and crashes on the third when it first reads the timeout, while the invalid port and mode are never read this run and lurk undetected, waiting to crash some later request. Startup validation runs every field's rule once before accepting any traffic and refuses to start if any fails — surfacing all three errors at once, at deploy time, where a human is watching the rollout, instead of scattered across future incidents. The rule: validate the entire configuration at startup and fail fast, so a bad config is a failed deploy, not a production outage discovered one field at a time.
eli5: Imagine you're about to drive somewhere and your car has three problems — a flat tire, no gas, and a dead headlight. A bad way to find out is to just start driving: you notice the flat right away, but the empty tank only stops you an hour later on the highway, and the dead headlight only matters after dark, so each problem ambushes you at the worst possible moment, one at a time. A good way is a pre-trip checklist: before you pull out of the driveway, you check the tires, the gas, and the lights all at once, see all three problems together, and fix them while you're still safely at home. Software configuration is the same — check every setting before the service starts taking real traffic, not whenever the running code happens to trip over each bad one.
---

## Why this module

Bad configuration is one of the most common causes of outages, and the reason it hurts so much is timing. A config value that is wrong does no damage sitting in a file; it does damage the instant running code reads it and chokes. The question that decides whether a bad config is a minor deploy hiccup or a production incident is entirely about when that read happens.

Lazy validation — checking each field the first time the code uses it — hands that timing to traffic. Different fields are read at different moments: some at boot, some on the first request of a kind, some only on a rare error path, some not for hours. So the bad values reveal themselves scattered across production, one crash at a time, and the ones on paths your tests never hit do not reveal themselves at all until a real user finds them.

This module loads a config with three invalid fields and runs it two ways. The lazy service serves a couple of requests, then crashes when it first reads the bad timeout — with two more bad fields still hidden. The startup validator checks all five fields before accepting any traffic, reports all three errors together, and refuses to boot. Then it shows why the second is strictly better.

**A wrong config value is a latent fault whose blast radius is set by when it is first read, and lazy validation lets production traffic pick that moment for you — always the worst one.**

## Concepts

Think of each configuration field as having a fuse whose length is "how long until some code path reads this." Validating a field lazily lights nothing early; it just waits at the end of the fuse and, when the read finally happens, either passes or blows up. The fuses have wildly different lengths — the port is read once at startup, a retry count only when a downstream call fails — so lazy validation converts a static set of bad values into a stream of crashes spread across the service's running life.

Two things make that stream especially bad. First, it is in production: the fuses burn while real traffic is being served, so each bad field takes down live requests rather than a deploy. Second, it is one at a time: fixing the field that crashed today does nothing about the two other bad fields still sitting behind their own unburned fuses, so you get a sequence of incidents, each looking fresh, each a separate page.

And some fuses never burn in testing. If a bad field lives on a code path your smoke test did not exercise — an admin endpoint, an error handler, a seasonal feature — lazy validation gives it a clean bill of health and ships it. It will burn eventually, when the right request arrives weeks later, and by then the deploy that introduced it is long forgotten.

Startup validation cuts every fuse at once, at boot. It reads the rule for every field before the service accepts traffic, collects all the failures, and refuses to start if there are any. The bad values are now discovered at deploy time — synchronously, all together, with a human watching the rollout — which is the cheapest possible place to find them.

<svg role="img" aria-label="Two timelines. The lazy timeline has a boot point then request points spread over time, with three bad fields exploding at different later moments and one marked never-tested. The startup timeline has a single validation gate at boot where all three bad fields are caught before any request" viewBox="0 0 640 250">
<text x="30" y="40" fill="var(--ink)" font-size="12">lazy: bad fields burn across production</text>
<line x1="40" y1="70" x2="600" y2="70" stroke="var(--line)" stroke-width="1"/>
<text x="50" y="90" fill="var(--muted)" font-size="9" text-anchor="middle">boot</text>
<circle cx="180" cy="70" r="5" fill="var(--s2)"/>
<text x="180" y="58" fill="var(--s2)" font-size="9" text-anchor="middle">timeout</text>
<circle cx="330" cy="70" r="5" fill="var(--s2)"/>
<text x="330" y="58" fill="var(--s2)" font-size="9" text-anchor="middle">port</text>
<circle cx="470" cy="70" r="5" fill="var(--s2)"/>
<text x="470" y="58" fill="var(--s2)" font-size="9" text-anchor="middle">mode</text>
<text x="560" y="90" fill="var(--muted)" font-size="9" text-anchor="middle">(some never)</text>
<text x="30" y="150" fill="var(--ink)" font-size="12">startup: all caught at the boot gate</text>
<line x1="40" y1="180" x2="600" y2="180" stroke="var(--line)" stroke-width="1"/>
<rect x="60" y="160" width="70" height="40" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="5"/>
<text x="95" y="184" fill="var(--ink)" font-size="10" text-anchor="middle">validate</text>
<text x="150" y="168" fill="var(--s1)" font-size="9">port</text>
<text x="150" y="182" fill="var(--s1)" font-size="9">timeout</text>
<text x="150" y="196" fill="var(--s1)" font-size="9">mode</text>
<text x="320" y="185" fill="var(--muted)" font-size="10">→ refuse to start, before any request</text>
</svg>
^ Lazy validation lets each bad field detonate whenever traffic first reads it; startup validation catches all of them at a single gate before serving.

**Lazy validation does not reduce the number of bad fields, it only randomizes when each one crashes you — and randomizing failure into live traffic is the opposite of what an operator wants.**

## Worked example

The fixture is a config with three invalid fields and the order the running service happens to read fields in.

```json filename=modules/ship-and-operate/code/cfgvalidate-inter-01/cfgvalidate.json:3-10 COMPLETE
  "config": {
    "port": 70000,
    "timeout_seconds": -5,
    "mode": "turbo",
    "workers": 4,
    "retries": 2
  },
  "access_order": ["workers", "retries", "timeout_seconds"]
```

Startup validation checks every field once and returns all the errors.

```python filename=modules/ship-and-operate/code/cfgvalidate-inter-01/cfgvalidate.py:45-47 COMPLETE
def validate_at_startup(config):
    """Check every field once, before serving; return the list of all errors (empty means safe to boot)."""
    return [err for name, value in config.items() if (err := validate_field(name, value)) is not None]
```

Lazy validation instead checks each field only as the service first reads it, and stops at the first failure — the production crash.

```python filename=modules/ship-and-operate/code/cfgvalidate-inter-01/cfgvalidate.py:50-56 COMPLETE
def lazy_run(config, access_order):
    """Validate each field only as it is first read; stop at the first error (the production crash)."""
    for step, name in enumerate(access_order):
        err = validate_field(name, config[name])
        if err is not None:
            return {"crashed_at_step": step, "error": err, "served_before_crash": step}
    return {"crashed_at_step": None, "error": None, "served_before_crash": len(access_order)}
```

The fields that no request reads this run are never checked at all — they lurk.

```python filename=modules/ship-and-operate/code/cfgvalidate-inter-01/cfgvalidate.py:59-61 COMPLETE
def lurking_invalid_fields(config, access_order):
    """Invalid fields the lazy run never reads -- they ship and crash some later request in production."""
    return [name for name in config if validate_field(name, config[name]) is not None and name not in access_order]
```

Running the lazy path shows the shape of the incident: some requests served fine, then a crash, with more bad fields still hidden.

```text filename=cfgvalidate.py --lazy
LAZY — validate each field only when the running service first reads it
----------------------------------------------------------------
  read order: ['workers', 'retries', 'timeout_seconds']
  served 2 request(s) OK, then crashed reading 'timeout_seconds' at step 2:
    timeout_seconds -5 must be > 0
  invalid fields never read this run (still lurking): ['port', 'mode']
----------------------------------------------------------------
  the crash is in production, and the untouched bad fields are still waiting
```

Two requests served, then a crash on the timeout — and the invalid port and mode were never even read, so lazy validation would let them ship. The startup path checks everything before serving.

```text filename=cfgvalidate.py --startup
STARTUP — validate every field before accepting any traffic
----------------------------------------------------------------
  checked 5 fields; 3 invalid:
    port 70000 out of range 1..65535
    timeout_seconds -5 must be > 0
    mode 'turbo' not in {fast, safe}
  decision: REFUSE TO START
----------------------------------------------------------------
  every bad field surfaced at once, at deploy time, before a single request
```

All three errors at once, and a refusal to boot. The figure contrasts the two outcomes.

<svg role="img" aria-label="Two panels. The lazy panel shows two green served requests, a red crash on timeout, and two grey lurking fields port and mode. The startup panel shows three red errors listed together and a refuse-to-start banner, with zero requests served" viewBox="0 0 640 230">
<text x="160" y="28" fill="var(--ink)" font-size="12" text-anchor="middle">lazy run</text>
<rect x="60" y="44" width="200" height="24" fill="var(--panel)" stroke="var(--s1)" stroke-width="1" rx="4"/>
<text x="160" y="61" fill="var(--muted)" font-size="10" text-anchor="middle">req 1: workers OK</text>
<rect x="60" y="74" width="200" height="24" fill="var(--panel)" stroke="var(--s1)" stroke-width="1" rx="4"/>
<text x="160" y="91" fill="var(--muted)" font-size="10" text-anchor="middle">req 2: retries OK</text>
<rect x="60" y="104" width="200" height="24" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="4"/>
<text x="160" y="121" fill="var(--ink)" font-size="10" text-anchor="middle">req 3: timeout CRASH</text>
<rect x="60" y="140" width="200" height="34" fill="var(--panel)" stroke="var(--line)" stroke-width="1" stroke-dasharray="4 3" rx="4"/>
<text x="160" y="154" fill="var(--muted)" font-size="10" text-anchor="middle">port, mode: lurking</text>
<text x="160" y="168" fill="var(--muted)" font-size="9" text-anchor="middle">(not read — still bad)</text>
<text x="480" y="28" fill="var(--ink)" font-size="12" text-anchor="middle">startup validation</text>
<rect x="380" y="44" width="200" height="84" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="4"/>
<text x="480" y="64" fill="var(--ink)" font-size="10" text-anchor="middle">port out of range</text>
<text x="480" y="84" fill="var(--ink)" font-size="10" text-anchor="middle">timeout must be &gt; 0</text>
<text x="480" y="104" fill="var(--ink)" font-size="10" text-anchor="middle">mode not in {fast,safe}</text>
<text x="480" y="122" fill="var(--muted)" font-size="9" text-anchor="middle">all three, together</text>
<rect x="380" y="140" width="200" height="30" fill="var(--panel)" stroke="var(--ink)" stroke-width="1.5" rx="4"/>
<text x="480" y="160" fill="var(--ink)" font-size="11" text-anchor="middle">REFUSE TO START</text>
</svg>
^ The lazy run trades two served requests for a live crash and two undetected bad fields; startup validation surfaces all three at boot and serves nothing broken.

**The lazy run's two successful requests are the trap — they make the service look healthy right up until the moment a bad field is read, which is exactly why the failure lands in production instead of the deploy.**

## Build

The self-test pins the asymmetry: startup validation reports every invalid field before serving, while the lazy run crashes only after serving real requests and leaves invalid fields undetected.

```python filename=modules/ship-and-operate/code/cfgvalidate-inter-01/cfgvalidate.py:103-114 COMPLETE
    startup_catches_all = len(startup_errors) == len(all_invalid) and len(all_invalid) > 0
    print("  startup validation reports every invalid field = %s (%d of %d)" % (startup_catches_all, len(startup_errors), len(all_invalid)))

    startup_before_serving = len(startup_errors) > 0
    print("  startup validation fails before any request is served = %s (refuse to boot)" % startup_before_serving)

    lazy_crashes_after_serving = run["crashed_at_step"] is not None and run["served_before_crash"] > 0
    print("  the lazy run serves real requests, then crashes = %s (served %d, crashed at step %d)"
          % (lazy_crashes_after_serving, run["served_before_crash"], run["crashed_at_step"]))

    lazy_leaves_errors_lurking = len(lurking) > 0
    print("  the lazy run leaves invalid fields undetected = %s (%s)" % (lazy_leaves_errors_lurking, lurking))
```

Running the check turns all five flags green.

```text filename=cfgvalidate.py --check
SELF-TEST — startup catches every invalid field before serving, while the lazy run crashes late and leaves invalid fields undetected
----------------------------------------------------------------------------------------------------------------
  startup validation reports every invalid field = True (3 of 3)
  startup validation fails before any request is served = True (refuse to boot)
  the lazy run serves real requests, then crashes = True (served 2, crashed at step 2)
  the lazy run leaves invalid fields undetected = True (['port', 'mode'])
  startup catches what the lazy run misses = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  startup_catches_all=True  startup_before_serving=True  lazy_crashes_after_serving=True  lazy_leaves_errors_lurking=True  startup_strictly_better=True
```

**The check shows startup validation is not merely earlier but more complete — it catches the port and mode that the lazy run, driven by this run's traffic, never even looked at.**

## Definition of done

You are done when the service validates its entire configuration during startup, before it binds a port or accepts a request, and exits non-zero with all the errors printed if anything is invalid.

The shape is a boot-time gate: load the config, run every field's rule, collect the failures, and if the list is non-empty, log them all and refuse to start. Report every error at once, not just the first — an operator fixing a bad deploy wants the whole list, so they fix it in one pass instead of rediscovering the next bad field on the next failed boot. Validate everything you can check without live dependencies (ranges, enums, formats, required fields, cross-field consistency), and for values you can only check against a live system (a reachable database, a valid credential), do a startup readiness probe that fails the boot the same way. The orchestration layer does the rest: a container that exits on bad config never becomes healthy, so the rollout halts on the old good version instead of replacing it with a broken one.

<svg role="img" aria-label="A startup flow: load config, validate all fields, then a decision. If any errors, log them all and exit non-zero, halting the rollout. If none, bind the port and accept traffic" viewBox="0 0 640 200">
<rect x="30" y="80" width="90" height="40" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="75" y="104" fill="var(--ink)" font-size="11" text-anchor="middle">load config</text>
<line x1="120" y1="100" x2="150" y2="100" stroke="var(--line)" stroke-width="1"/>
<polygon points="150,100 142,95 142,105" fill="var(--line)"/>
<rect x="152" y="80" width="110" height="40" fill="var(--panel)" stroke="var(--line)" stroke-width="1.5" rx="6"/>
<text x="207" y="98" fill="var(--ink)" font-size="11" text-anchor="middle">validate every</text>
<text x="207" y="112" fill="var(--ink)" font-size="11" text-anchor="middle">field</text>
<line x1="262" y1="100" x2="292" y2="100" stroke="var(--line)" stroke-width="1"/>
<polygon points="292,100 284,95 284,105" fill="var(--line)"/>
<text x="330" y="60" fill="var(--muted)" font-size="11" text-anchor="middle">any errors?</text>
<line x1="330" y1="75" x2="330" y2="120" stroke="var(--line)" stroke-width="1"/>
<line x1="330" y1="88" x2="400" y2="88" stroke="var(--s2)" stroke-width="1"/>
<rect x="400" y="52" width="200" height="40" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5" rx="6"/>
<text x="500" y="70" fill="var(--ink)" font-size="10" text-anchor="middle">yes → log all, exit non-zero</text>
<text x="500" y="84" fill="var(--muted)" font-size="9" text-anchor="middle">rollout halts on old version</text>
<line x1="330" y1="112" x2="400" y2="112" stroke="var(--s1)" stroke-width="1"/>
<rect x="400" y="108" width="200" height="40" fill="var(--panel)" stroke="var(--s1)" stroke-width="1.5" rx="6"/>
<text x="500" y="126" fill="var(--ink)" font-size="10" text-anchor="middle">no → bind port, serve</text>
<text x="500" y="140" fill="var(--muted)" font-size="9" text-anchor="middle">only valid config serves</text>
</svg>
^ The boot gate fails the whole deploy on bad config, so a broken version never reaches traffic and the good version keeps serving.

**Failing to start is a feature, not a defect: a service that refuses to boot on bad config turns a would-be production incident into a failed deploy that the rollout automatically contains.**

## Boss fight

Your turn: add a field that is only read on a rare path and watch lazy validation ship it. Put a `"log_level": "verbos"` (a typo for "verbose") into the config, give it a validator that requires one of the known levels, and leave it out of `access_order` — the run never changes log level, so the lazy path never reads it. Rerun `--startup` and it appears in the error list and blocks the boot; rerun `--lazy` and it joins port and mode in the lurking set, shipped and waiting. This is the case that makes lazy validation genuinely dangerous rather than merely late: the fields most likely to be misconfigured are often the rarely-touched ones, which are exactly the ones traffic-driven validation never exercises.

Then consider the tempting half-measure: validate lazily but cache the result, so at least each bad field only crashes once. It does not help. The crash is still in production, still at a moment traffic chose, still one field at a time, and the lurking fields are still lurking — caching the outcome of a check you ran too late does nothing about when you ran it. The only fix that changes the timing is to run every check before serving. There is a real cost, honestly: startup validation makes boots stricter, so a config that was "mostly fine" now fails to start, and you must keep the validators correct or they reject good config. That trade is the right one — a boot that fails loudly at deploy time is worth far more than a service that starts happily and fails quietly under load — but it is a trade, and the discipline is keeping the validation as authoritative as the code that consumes the config.

**Making each bad field crash only once is optimizing the wrong axis; the thing that hurts is not how many times a bad field crashes but that it crashes in production at all, and only pre-serve validation moves the failure to where it belongs.**

## External resources

The Twelve-Factor App's "Config" factor argues for strict separation of config from code and for treating config as a first-class input, which is the backdrop for validating it as rigorously as any other input, at startup.

Most schema-validation libraries (JSON Schema, Pydantic in Python, `envalid` and similar in other ecosystems) are built precisely to run a full config validation pass at load time and fail with the complete error set — a practical implementation of this module's rule.

The AWS and Google SRE writing on change-induced outages repeatedly identifies configuration changes as a leading cause and recommends validate-at-deploy gates, which is the operational form of failing the boot on bad config.
