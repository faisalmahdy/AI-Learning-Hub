---
id: ship-inter-11
title: Canary the release to a slice first — deploy straight to 100% and a bad version hits everyone
topic: ship-and-operate
level: intermediate
status: ready
time: 21 min
summary: Deploying a new version to all of production at once exposes every user to a regression before anyone can react. A canary routes a small fraction first, reads its error rate against a rollback threshold, and only promotes if healthy. A bad release (30% errors) fails 300 of 1000 at full deploy but only 34 when canaried and rolled back.
eli5: Before serving a new dish to the whole restaurant, you give a taste to one table. If they get sick, you pull the dish and nobody else is harmed. If they're fine, you serve everyone. Shipping to all users at once is serving the whole restaurant before anyone has tasted it.
---

## Why this module

Deploying to all of production at once is a bet you settle only after everyone has already paid if you lose.

A new version either works or it does not, and you find out from production traffic. If you deploy it to 100% of users at once, then the way you discover a regression is that all of your users hit it — the errors, the crashes, the corrupted data happen at full scale before your monitoring even fires, let alone before a human can respond. The blast radius of a bad release is your entire traffic, and the time-to-detect is however long it takes the damage to become visible. By then it is done.

A canary deployment changes the bet from all-or-nothing to a cheap probe. Route a small fraction of traffic — 1%, 5% — to the new version and leave the rest on the old, known-good one. Watch the canary's error rate. If it stays healthy, promote the new version to the rest of the traffic. If it crosses a rollback threshold, roll back: the new version is pulled, and the fraction that saw errors is the whole cost, while the other 95% never left the version that works. The bad release still errors, but only on the slice, and only until the threshold trips.

The mechanism is nearly free when the release is good. A healthy version sails through the canary — its error rate matches baseline — and gets promoted, and the users who were on the canary saw exactly what they would have seen anyway. You pay a small, bounded exposure to buy the guarantee that you will never expose everyone to an untested version. That is the trade, and it is almost always worth it.

We will run a bad release and a good release through both strategies. The bad release, deployed straight to 100%, fails 300 of 1000 requests; canaried at 5% and rolled back, it fails 34. The good release passes the canary and promotes, adding no failures over baseline. Same releases, two strategies, and the canary turns a 300-failure outage into a 34-failure blip.

**Deploying to 100% at once makes your users the ones who discover a regression; a canary discovers it on a small slice and rolls back before the rest of the traffic is ever exposed.**

## Concepts

The quantity a canary controls is blast radius: how much of your traffic a bad release can damage before you stop it. With a full deploy, blast radius is 100% — everyone is on the new version, so everyone is exposed. With a canary, blast radius is bounded by the canary fraction plus whatever leaks through before the rollback fires: you route only the fraction to the new version, so only the fraction can be hit, and a rollback returns even that fraction's traffic to the old version. The smaller the canary and the faster the rollback, the smaller the blast radius. Blast radius is the thing progressive delivery exists to minimize.

<svg role="img" aria-label="Traffic exposure to a bad release: full deploy exposes the entire bar, canary exposes only a 5 percent slice" viewBox="0 0 460 150" width="460" height="150">
  <rect x="0" y="0" width="460" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">traffic exposed to the new (bad) version</text>
  <text x="20" y="52" font-family="var(--mono)" font-size="10" fill="var(--ink)">full deploy</text>
  <rect x="130" y="40" width="300" height="24" fill="var(--s2)" stroke="var(--line)"/><text x="250" y="57" font-family="var(--mono)" font-size="10" fill="var(--ink)">100% exposed</text>
  <text x="20" y="102" font-family="var(--mono)" font-size="10" fill="var(--ink)">canary</text>
  <rect x="130" y="90" width="15" height="24" fill="var(--s2)" stroke="var(--line)"/>
  <rect x="145" y="90" width="285" height="24" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="240" y="107" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">95% stays on old version</text>
  <text x="120" y="132" font-family="var(--mono)" font-size="9" fill="var(--s2)">5% slice</text>
</svg>
^ Full deploy puts all traffic on the new version at once; the canary exposes only a 5% slice and keeps the rest on the known-good version until the slice proves healthy.

The decision the canary makes is a hypothesis test on the new version's health. You pick a metric — error rate, latency, a business KPI — and a threshold that separates "healthy" from "roll back." The canary's traffic gives you a sample of that metric under the new version, and you compare it to the threshold (ideally to the baseline version running in parallel, to control for time-of-day and traffic-mix effects). Above the threshold, roll back; at or below, promote. The threshold is a calibration: too tight and normal noise triggers false rollbacks that stall every deploy; too loose and a real regression slips through the canary and reaches everyone. It lives in the gap between baseline noise and the smallest regression you care to catch.

The canary size is its own trade. A bigger canary gives a more statistically confident read on the new version's health — more requests, tighter error-rate estimate, fewer false decisions — but a bigger blast radius if the version is bad. A smaller canary bounds the damage tighter but may not send enough traffic to distinguish a real regression from noise, especially for rare errors. Real systems often ramp: 1%, then 5%, then 25%, then 100%, checking health at each stage, so the exposure grows only as confidence does. The single-stage canary here is the core idea; the ramp is the same idea applied repeatedly.

What the canary is not is a substitute for testing — it is the last line, catching what testing missed, on the smallest possible slice of real traffic. And it only works if you can actually roll back: the new version must be safely reversible, which is why canary deployment pairs with backward-compatible changes and quick rollback machinery. A canary that detects a bad release but cannot undo it has only told you the bad news early.

**A canary bounds blast radius to a small fraction and turns "is this release healthy" into a threshold test on that fraction's metrics, trading a bigger canary's confidence against its exposure.**

## Worked example

The fixture is the traffic, the canary fraction, the rollback threshold, and two candidate releases.

```json filename=modules/ship-and-operate/code/ship-inter-11/release.json:7-14 COMPLETE
  "total_requests": 1000,
  "canary_fraction": 0.05,
  "baseline_error_rate": 0.02,
  "rollback_threshold": 0.1,
  "releases": {
    "good": 0.02,
    "bad": 0.3
  }
```

A thousand requests, a 5% canary, a 10% rollback threshold, a 2% baseline error rate. The good release errors at 2% (same as baseline); the bad release errors at 30%. Look at how each stands against the threshold.

```text filename=modules/ship-and-operate/code/ship-inter-11/canary.py --releases
RELEASES — candidate error rates vs the 10% rollback threshold
------------------------------------------------------
  baseline (old version): 2%
  good   release:     2%   would promote
  bad    release:    30%   would roll back
------------------------------------------------------
  canary sends 5% of traffic first and reads the error rate before promoting.
```

The good release is under the 10% threshold, the bad release is way over. Full deploy ignores the threshold entirely — it sends everything to the new version.

```python filename=modules/ship-and-operate/code/ship-inter-11/canary.py:43-46 COMPLETE
def deploy_full(total, release_rate, baseline, fraction, threshold):
    """Deploy to 100% at once: every request faces the new version."""
    failures = round(total * release_rate)
    return {"failures": failures, "decision": "all traffic on new version"}
```

The canary sends the fraction, reads its rate against the threshold, and either rolls back (rest stays on baseline) or promotes (rest goes to the new version).

```python filename=modules/ship-and-operate/code/ship-inter-11/canary.py:49-60 COMPLETE
def deploy_canary(total, release_rate, baseline, fraction, threshold):
    """Canary a slice; roll back if its error rate exceeds the threshold, else promote to 100%."""
    canary_n = round(total * fraction)
    canary_failures = round(canary_n * release_rate)
    rest = total - canary_n
    if release_rate > threshold:
        # roll back: the rest of the traffic stays on the old version at baseline
        rest_failures = round(rest * baseline)
        return {"failures": canary_failures + rest_failures, "decision": "ROLLED BACK", "canary_failures": canary_failures}
    # promote: the rest runs on the (healthy) new version
    rest_failures = round(rest * release_rate)
    return {"failures": canary_failures + rest_failures, "decision": "promoted", "canary_failures": canary_failures}
```

Predict the bad release: full deploy fails 1000 × 30% = 300. Canary fails 50 × 30% = 15 on the slice, rolls back, and the remaining 950 stay on baseline at 2% = 19, for 34 total. Run both releases.

```text filename=modules/ship-and-operate/code/ship-inter-11/canary.py --deploy
DEPLOY — failures over 1000 requests: deploy-to-100% vs canary
------------------------------------------------------------------
  good   release ( 2%):  full deploy  20 failures   canary  20 failures (promoted)
  bad    release (30%):  full deploy 300 failures   canary  34 failures (ROLLED BACK)
------------------------------------------------------------------
  the bad release fails 300 at full deploy but only 34 when canaried and rolled back.
```

The bad release is the story: 300 failures deployed straight to everyone, 34 when canaried and rolled back — a nearly 9× smaller blast radius, and the 34 is mostly just the baseline error rate the old version would have had anyway. The good release shows the canary's cost when it is not needed: 20 failures either way, because a healthy version does the same thing at 5% or 100%. The canary saved 266 failures on the bad release and cost nothing on the good one.

<svg role="img" aria-label="Failures for the bad release: full deploy 300, canary 34; and the good release: 20 either way" viewBox="0 0 460 190" width="460" height="190">
  <rect x="0" y="0" width="460" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="11" fill="var(--muted)">failures of 1000 requests</text>
  <line x1="60" y1="160" x2="440" y2="160" stroke="var(--line)"/>
  <text x="16" y="40" font-family="var(--mono)" font-size="10" fill="var(--s2)">bad release</text>
  <rect x="70" y="40" width="70" height="120" fill="var(--s2)" stroke="var(--line)"/><text x="82" y="34" font-family="var(--mono)" font-size="10" fill="var(--s2)">300</text><text x="72" y="174" font-family="var(--mono)" font-size="8" fill="var(--muted)">full</text>
  <rect x="160" y="146" width="70" height="14" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="172" y="140" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">34</text><text x="162" y="174" font-family="var(--mono)" font-size="8" fill="var(--muted)">canary</text>
  <text x="270" y="40" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">good release</text>
  <rect x="300" y="152" width="50" height="8" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="312" y="146" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">20</text><text x="302" y="174" font-family="var(--mono)" font-size="8" fill="var(--muted)">full</text>
  <rect x="370" y="152" width="50" height="8" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="382" y="146" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">20</text><text x="372" y="174" font-family="var(--mono)" font-size="8" fill="var(--muted)">canary</text>
</svg>
^ The canary collapses the bad release's 300 failures to 34 and leaves the good release's 20 untouched — all upside on the bad day, no cost on the good one.

<svg role="img" aria-label="The canary decision flow: route a fraction, measure its error rate, then either roll back or promote to 100 percent" viewBox="0 0 460 170" width="460" height="170">
  <rect x="0" y="0" width="460" height="170" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="20" y="65" width="90" height="40" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="30" y="82" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">route 5%</text><text x="30" y="96" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">to canary</text>
  <line x1="110" y1="85" x2="160" y2="85" stroke="var(--ink)"/>
  <rect x="160" y="65" width="100" height="40" fill="var(--panel)" stroke="var(--line)"/><text x="168" y="82" font-family="var(--mono)" font-size="9" fill="var(--ink)">error rate ></text><text x="168" y="96" font-family="var(--mono)" font-size="9" fill="var(--ink)">threshold?</text>
  <line x1="260" y1="85" x2="320" y2="50" stroke="var(--s2)"/><text x="300" y="40" font-family="var(--mono)" font-size="9" fill="var(--s2)">yes</text>
  <rect x="320" y="30" width="120" height="34" fill="var(--s2)" stroke="var(--line)"/><text x="330" y="51" font-family="var(--mono)" font-size="9" fill="var(--ink)">ROLL BACK (34)</text>
  <line x1="260" y1="85" x2="320" y2="120" stroke="var(--acc-ink)"/><text x="300" y="135" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">no</text>
  <rect x="320" y="106" width="120" height="34" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="330" y="127" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">promote to 100%</text>
</svg>
^ The canary reads its slice's error rate once and branches: over the threshold it rolls back and bounds the damage, under it promotes to the rest of the traffic.

## Build

Reproduce the failure counts. Pure standard library, deterministic rates, so 300, 34, and 20 come out exactly.

Run `--releases` for the verdicts, `--deploy` for the failure counts, `--check` for the gate. The self-test pins both outcomes: the canary catches and shrinks the bad release, and it promotes the good one without harm.

```python filename=modules/ship-and-operate/code/ship-inter-11/canary.py:96-104 COMPLETE
    bad_full = deploy_full(t, bad, base, frac, thr)
    bad_canary = deploy_canary(t, bad, base, frac, thr)

    canary_rolls_back = bad_canary["decision"] == "ROLLED BACK"
    print("  the canary rolls the bad release back = %s (%.0f%% > %.0f%% threshold)"
          % (canary_rolls_back, bad * 100, thr * 100))

    blast_radius_shrinks = bad_canary["failures"] < bad_full["failures"]
    print("  the canary shrinks the bad release's blast radius = %s (%d vs %d failures)"
          % (blast_radius_shrinks, bad_canary["failures"], bad_full["failures"]))
```

The `good_no_harm` check, below, is the one that proves the canary is free when it is not needed. It asserts that promoting the good release produces exactly the baseline failure count — no extra failures from the canary process itself. Without that check, someone could claim the canary "works" while quietly adding overhead on every good deploy, which would make teams avoid it. Zero cost on the common case (a good release) is what makes canarying something you do every time, not just when you are worried.

```python filename=modules/ship-and-operate/code/ship-inter-11/canary.py:107-114 COMPLETE
    good_canary = deploy_canary(t, good, base, frac, thr)
    good_promotes = good_canary["decision"] == "promoted"
    print("  the canary promotes the good release = %s (%.0f%% <= %.0f%% threshold)"
          % (good_promotes, good * 100, thr * 100))

    good_no_harm = good_canary["failures"] == round(t * base)
    print("  promoting the good release adds no failures over baseline = %s (%d = %d)"
          % (good_no_harm, good_canary["failures"], round(t * base)))
```

```text filename=modules/ship-and-operate/code/ship-inter-11/canary.py --check
SELF-TEST — the canary catches the bad release and shrinks its blast radius; it promotes the good one
------------------------------------------------------------------------------------------------
  the canary rolls the bad release back = True (30% > 10% threshold)
  the canary shrinks the bad release's blast radius = True (34 vs 300 failures)
  the canary promotes the good release = True (2% <= 10% threshold)
  promoting the good release adds no failures over baseline = True (20 = 20)
------------------------------------------------------------------------------------------------
SELF-TEST PASS  canary_rolls_back=True  blast_radius_shrinks=True  good_promotes=True  good_no_harm=True
```

Four True flags. Canary_rolls_back: the bad release trips the threshold and is pulled. Blast_radius_shrinks: 34 failures instead of 300. Good_promotes: the healthy release passes. Good_no_harm: it does so at exactly baseline cost. The last two together are what make canarying a default rather than an exception — it is all upside on a bad release and no cost on a good one.

**The good-no-harm check proves the canary costs exactly baseline on a healthy release, which is what makes it a habit you can afford on every deploy, not just the scary ones.**

## Definition of done

You are done when you reproduce 300, 34, and 20 and can explain blast radius.

Concretely: `--deploy` shows the bad release at 300 failures full versus 34 canaried, and the good release at 20 either way; `--check` prints PASS with four True flags. You can define blast radius and explain how the canary fraction and rollback bound it. You can describe the canary decision as a threshold test on the slice's health metric, and name the two calibration trades: threshold (false rollbacks versus missed regressions) and canary size (confidence versus exposure). And you can state the precondition — the release must be reversible — without which a canary only delivers bad news early.

The habit to carry: never deploy a change to 100% at once when you can canary it first, ramp exposure as confidence grows, and wire an automatic rollback on a health threshold so a bad release is pulled before it reaches everyone. Testing catches what it can; the canary catches the rest on the smallest slice.

## Boss fight

The instructive failure is a Friday-afternoon deploy that takes down the whole site in the time it takes to read one alert.

A team ships a config change straight to 100% of production. It has a bug that errors on a third of requests, but that only shows up under real traffic, which the tests did not have. Within thirty seconds every third user is seeing errors; the alert fires, the on-call scrambles, and by the time they roll back manually, hundreds of thousands of requests have failed and the incident is a headline. A 5% canary with an automatic rollback would have caught the same bug on 5% of traffic, pulled the change in seconds without a human in the loop, and the incident would have been a line in a deploy log. The bug was identical; the only difference was whether the whole site or a slice discovered it.

Your turn, two moves. First, tune the canary size against detection. Shrink the canary to 1% (10 requests) and predict: the bad release still trips the threshold and rolls back, blast radius even smaller — but for a rarer bug, say 3% errors against a 2% baseline, 10 requests may see zero or one error and the canary cannot tell it from noise. Compute how many canary requests you need to distinguish a 3% rate from 2% with any confidence, and see why rare-but-real regressions demand a bigger canary or a longer bake. Second, probe the threshold. Set the rollback threshold to 40% and predict: the 30% bad release now sneaks under it, promotes to 100%, and fails 300 — the canary ran and waved the bad release through, because the threshold was above the regression. That is the false-negative failure, and it shows the threshold is not a formality: set it above a regression you care about and the canary becomes theater. The threshold belongs just above baseline noise, not wherever is convenient.

## External resources

The canary-release pattern is documented in every progressive-delivery guide; Martin Fowler's "CanaryRelease" and the Google SRE book's chapter on release engineering cover the fraction-then-promote mechanics and the automatic-rollback tie-in.

For automated canary analysis — comparing canary metrics to a baseline statistically rather than by a fixed threshold — Netflix's Kayenta and the Spinnaker canary docs are the reference implementations, and they formalize the "compare canary to baseline, not to an absolute" point this module gestures at.

For the delivery machinery, Argo Rollouts and Flagger document how canaries and progressive traffic ramps are configured in Kubernetes, including the health checks and rollback triggers that turn the idea in this module into a running deployment.
