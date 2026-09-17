---
id: ship-inter-21
title: Keep the old version warm for an instant flip — or rolling back means redeploying while the bad version serves
topic: ship-and-operate
level: intermediate
status: ready
time: 17 min
summary: A canary limits how many users see a bad release; this is a different lever — how fast you can roll back once a bad version is live. Both strategies pay the same detection window: the bad version serves every request from ship until monitoring notices, and you cannot roll back what you have not detected. What differs is the rollback itself. In-place deployment overwrote the old version, so rolling back means redeploying from scratch — minutes of build, ship, restart — while the bad version keeps serving. Blue-green keeps the old version running in a second environment, so rollback is flipping traffic back in seconds. On 100 req/s and a bad version detected after 30s, in-place needs a 300s redeploy and serves 33,000 bad requests; blue-green flips in 2s and serves 3,200. The shared 30s detection costs 3,000 either way; blue-green saves the 29,800 in the rollback window.
eli5: Imagine you swap out a light bulb and the new one flickers. If you threw the old bulb in the trash, fixing it means driving to the store for another — and you sit in the dark the whole trip. If you kept the old bulb on the shelf, you just screw it back in, and the dark lasts seconds. Deploying software is the same: keep the previous version ready to switch back to, and a bad release costs seconds instead of the whole time it takes to build and ship a replacement.
---

## Why this module

The time you spend rolling back a bad release is time the bad release is still serving every user, and whether that time is seconds or minutes is decided before the bad release ever ships — by whether the previous version is still runnable.

A canary answers "how many users see the bad version" by rolling out to a slice first. This module answers a different question: once a bad version is live to everyone, how fast can you get rid of it. The two are not the same cost. Every strategy pays a detection window — the bad version serves from the moment it ships until monitoring notices, and nothing can roll back a problem that has not been detected yet. That window is unavoidable and identical across strategies. What is not identical is how long the rollback itself takes, and that is set entirely by whether the version you want to return to still exists and is running.

**However you deploy, the bad version serves through the detection window; the strategy only controls the rollback window after it, and that window is the rollback's execution time times the request rate.**

In-place deployment overwrites the old version on the same servers, so once the new one is bad, the old one is gone — rolling back means deploying again from scratch, minutes of build and ship and restart, all while the bad version keeps serving. Blue-green keeps the old version running untouched in a second environment and just points traffic at the new one; rolling back is flipping the pointer back, seconds. This module computes the bad version's total airtime under each and shows the difference is exactly the rollback time you saved.

## Concepts

The **detection window** is the time from ship to noticing the release is bad — monitoring lag. The bad version serves the whole time, and this cost is paid identically no matter how you deploy.

The **rollback window** is how long the rollback itself takes to execute once you decide to do it. This is where strategies diverge, and it is multiplied by the request rate into bad requests served.

**In-place deployment** overwrites the running version. Rolling back means redeploying the old one from scratch — rebuild, ship, restart, warm — which takes minutes, and the bad version serves throughout.

**Blue-green deployment** runs the new version in a second environment while the old one keeps running untouched. Rolling back is flipping traffic back to the still-warm old environment: seconds.

**Rollback speed is not detection speed.** Blue-green makes recovery instant but still pays the detection window; to shrink that you need better monitoring, not a better deploy strategy. The two costs are independent and you attack them with different tools.

```python filename=modules/ship-and-operate/code/ship-inter-21/rollback.py:41-48 COMPLETE
def airtime(detect_s, rollback_s):
    """Seconds the bad version serves: the detection window plus the rollback time."""
    return detect_s + rollback_s


def bad_requests(rate, detect_s, rollback_s):
    """Requests served by the bad version = rate * its airtime."""
    return rate * airtime(detect_s, rollback_s)
```

**The bad version's airtime is detection plus rollback; blue-green cannot touch detection but collapses rollback from a redeploy to a flip, so its whole win lives in the rollback window.**

<svg role="img" aria-label="In-place overwrites the old version so rollback must rebuild it; blue-green keeps the old environment running so rollback is a traffic flip" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">in-place: one environment, overwritten</text>
  <rect x="20" y="20" width="60" height="20" fill="var(--s2)"/><text x="26" y="34" fill="var(--panel)" font-size="8">new (bad)</text>
  <text x="88" y="34" fill="var(--muted)" font-size="8">old is gone → rollback must rebuild it (slow)</text>
  <text x="10" y="66" fill="var(--muted)" font-size="8">blue-green: two environments, traffic pointer</text>
  <rect x="20" y="74" width="60" height="20" fill="var(--s2)"/><text x="26" y="88" fill="var(--panel)" font-size="8">new (bad)</text>
  <rect x="90" y="74" width="60" height="20" fill="var(--s1)"/><text x="96" y="88" fill="var(--panel)" font-size="8">old (warm)</text>
  <text x="158" y="88" fill="var(--muted)" font-size="8">← flip traffic back (instant)</text>
  <text x="20" y="112" fill="var(--muted)" font-size="8">keeping the old environment warm is what makes rollback a flip instead of a build</text>
</svg>
^ In-place has thrown the old version away, so rollback rebuilds it; blue-green keeps it running beside the new one, so rollback just repoints traffic.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/ship-inter-21/rollback.py

The fixture is a request rate and the three timings: detection, redeploy, and flip.

```json filename=modules/ship-and-operate/code/ship-inter-21/rollback.json:1-8 COMPLETE
{
  "_meta": "A rollback-speed model. A bad version is deployed at t=0 and serves every request until the rollback completes. rate is requests per second. detect_s is how long until the bad version is noticed (monitoring lag) — this window is paid no matter how you deploy, because you cannot roll back what you have not detected. Then rollback happens two ways. In-place deploy has thrown away the old version, so rolling back means DEPLOYING AGAIN from scratch: redeploy_s seconds of build/ship/restart, during which the bad version keeps serving. Blue-green keeps the old version running in a second environment, so rollback is just flipping traffic back: flip_s seconds, essentially instant. Bad requests served = rate * (detect_s + rollback time). The detection window is shared; the rollback window is where blue-green wins.",
  "rate": 100,
  "detect_s": 30,
  "redeploy_s": 300,
  "flip_s": 2
}
```

The airtime view prints each strategy's rollback time, airtime, and bad-request count from the same two helpers.

```python filename=modules/ship-and-operate/code/ship-inter-21/rollback.py:57-59 COMPLETE
    print("  strategy     rollback   airtime      bad requests")
    print("  in-place     %4ds      %4ds        %d" % (redeploy, airtime(d, redeploy), bad_requests(rate, d, redeploy)))
    print("  blue-green   %4ds      %4ds        %d" % (flip, airtime(d, flip), bad_requests(rate, d, flip)))
```

Run `--airtime` to see how long the bad version serves and how many requests it poisons under each strategy.

```text filename=--airtime
AIRTIME — how long the bad version serves and how many requests it poisons
------------------------------------------------------------------
  strategy     rollback   airtime      bad requests
  in-place      300s       330s        33000
  blue-green      2s        32s        3200
------------------------------------------------------------------
  same detection, but in-place keeps serving bad for the whole redeploy; blue-green flips out.
```

Both strategies detect the problem at 30 seconds. From there, in-place must redeploy the old version, 300 seconds of build and ship and restart, so the bad version's total airtime is 330 seconds and it serves 33,000 requests. Blue-green flips traffic back to the old environment in 2 seconds, so its airtime is 32 seconds and it serves 3,200. The bad code was identical; the only difference was whether the previous version was still running when the alarm went off.

<svg role="img" aria-label="In-place airtime is 330 seconds mostly redeploy; blue-green airtime is 32 seconds, the detection window plus a 2-second flip" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">bad-version airtime = detection (grey) + rollback (color)</text>
  <text x="6" y="38" fill="var(--muted)" font-size="8">in-place</text>
  <rect x="70" y="28" width="21" height="16" fill="var(--grid)"/><rect x="91" y="28" width="207" height="16" fill="var(--s2)"/><text x="150" y="40" fill="var(--panel)" font-size="8">redeploy 300s → 33,000 bad</text>
  <text x="6" y="74" fill="var(--muted)" font-size="8">blue-green</text>
  <rect x="70" y="64" width="21" height="16" fill="var(--grid)"/><rect x="91" y="64" width="6" height="16" fill="var(--s1)"/><text x="102" y="76" fill="var(--muted)" font-size="8">flip 2s → 3,200 bad</text>
  <text x="70" y="98" fill="var(--muted)" font-size="8">the grey detection window is equal; the colored rollback window is the whole gap</text>
</svg>
^ Both bars start with the same grey detection window; in-place then runs a long redeploy bar while blue-green adds only a sliver, so its total airtime is a tenth of in-place's.

## Build

The win has to be attributed correctly — to rollback, not detection. Run `--split`.

```text filename=--split
SPLIT — shared detection cost vs the rollback cost that blue-green cuts
------------------------------------------------------------------
  detection window (shared):   30s  ->  3000 bad requests either way
  in-place rollback:           300s  ->  30000 bad requests
  blue-green rollback:         2s  ->  200 bad requests
------------------------------------------------------------------
  blue-green saves 29800 bad requests: the rollback window shrinks from 300s to 2s.
```

The 30-second detection window costs 3,000 bad requests under either strategy — blue-green does nothing for it, because you still cannot roll back before you detect. The difference is entirely in the rollback: 30,000 bad requests for the in-place redeploy versus 200 for the blue-green flip, a saving of 29,800. Attributing the win this way matters, because it tells you where each lever applies: to cut the 3,000 you need faster detection (better monitoring, health checks, alerting), and to cut the 30,000 you need a faster rollback (keep the old version warm). Blue-green buys the second, not the first.

<svg role="img" aria-label="Bad requests split into a shared 3000 detection cost and a rollback cost of 30000 for in-place versus 200 for blue-green" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">bad requests: detection (grey, shared) + rollback (color)</text>
  <line x1="30" y1="90" x2="30" y2="24" stroke="var(--grid)" stroke-width="1"/>
  <line x1="30" y1="90" x2="290" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <text x="40" y="102" fill="var(--muted)" font-size="8">in-place</text>
  <rect x="45" y="66" width="18" height="24" fill="var(--grid)"/><rect x="45" y="26" width="18" height="40" fill="var(--s2)"/><text x="66" y="40" fill="var(--muted)" font-size="7">30,000 rollback</text><text x="66" y="80" fill="var(--muted)" font-size="7">3,000 detect</text>
  <text x="200" y="102" fill="var(--muted)" font-size="8">blue-green</text>
  <rect x="205" y="66" width="18" height="24" fill="var(--grid)"/><rect x="205" y="62" width="18" height="4" fill="var(--s1)"/><text x="226" y="70" fill="var(--muted)" font-size="7">200 rollback</text>
  <text x="30" y="108" fill="var(--muted)" font-size="8">the grey detect blocks are equal; only the colored rollback block shrinks</text>
</svg>
^ The grey detection block is the same height in both stacks; blue-green shrinks the colored rollback block from 30,000 down to 200, which is the entire difference.

## Definition of done

The self-test pins the split: detection is shared, in-place is far slower, blue-green serves fewer, the win is exactly rate·(redeploy−flip), and blue-green still pays detection.

```python filename=modules/ship-and-operate/code/ship-inter-21/rollback.py:81-94 COMPLETE
    detection_shared = bad_requests(rate, d, 0) == rate * d
    print("  the detection window costs the same either way = %s (%d requests)" % (detection_shared, rate * d))

    inplace_rollback_slow = redeploy > 10 * flip
    print("  in-place rollback is far slower than a flip = %s (%ds > %ds)" % (inplace_rollback_slow, redeploy, flip))

    bluegreen_serves_fewer = bad_requests(rate, d, flip) < bad_requests(rate, d, redeploy)
    print("  blue-green serves fewer bad requests = %s (%d < %d)" % (bluegreen_serves_fewer, bad_requests(rate, d, flip), bad_requests(rate, d, redeploy)))

    win_is_rollback_gap = (bad_requests(rate, d, redeploy) - bad_requests(rate, d, flip)) == rate * (redeploy - flip)
    print("  the saving is exactly rate*(redeploy - flip) = %s (%d = %d*%d)" % (win_is_rollback_gap, bad_requests(rate, d, redeploy) - bad_requests(rate, d, flip), rate, redeploy - flip))

    detection_still_paid = bad_requests(rate, d, flip) > 0
    print("  blue-green still pays the detection window (rollback speed is not detection) = %s (%d > 0)" % (detection_still_paid, bad_requests(rate, d, flip)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — detection is shared; in-place redeploys slowly; blue-green flips fast; win is rate*(redeploy-flip)
------------------------------------------------------------------------------------------------------------
  the detection window costs the same either way = True (3000 requests)
  in-place rollback is far slower than a flip = True (300s > 2s)
  blue-green serves fewer bad requests = True (3200 < 33000)
  the saving is exactly rate*(redeploy - flip) = True (29800 = 100*298)
  blue-green still pays the detection window (rollback speed is not detection) = True (3200 > 0)
------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  detection_shared=True  inplace_rollback_slow=True  bluegreen_serves_fewer=True  win_is_rollback_gap=True  detection_still_paid=True
```

**Done means the two costs are provably separated: the 30s detection window costs 3,000 requests under both, blue-green cuts the rollback window from 33,000 to 3,200 bad requests total, and the 29,800 saved is exactly the request rate times the redeploy-minus-flip time.**

## Boss fight

Blue-green cut the rollback to a flip. Predict what it costs to keep the old environment warm, and the one new failure mode the instant flip introduces. It is tempting to think a faster rollback is a pure free win.

Blue-green's speed is bought with a second environment: for the duration of a release you run two full copies of production, roughly doubling that footprint, plus the discipline of keeping the idle one genuinely warm — same data access, same config, same scaled-up capacity — because an old environment that has quietly gone cold or stale is not a rollback target, it is a second outage. The trade is real infrastructure cost and operational care for near-instant recovery, and it is usually worth it for user-facing services where minutes of a bad version is expensive; for a low-traffic internal tool the redeploy time may be cheap enough that the second environment is not. The point is that rollback speed has a price, and you buy it deliberately where airtime is costly.

The new failure mode is state. A traffic flip is instant for stateless request serving, but if the new version wrote to a shared database in a format the old version cannot read — a migrated schema, a new field, a changed encoding — flipping back to the old version can leave it staring at data it does not understand, so the rollback that was supposed to be safe corrupts or crashes on the new rows. This is why schema changes are done in expand-contract steps that keep both versions readable: the instant flip only stays safe if the old version can still run against whatever the new one touched. Blue-green gives you a fast rollback of the *code*; it does not, by itself, give you a rollback of the *data*, and forgetting that turns the safety net into a trap.

```python filename=modules/ship-and-operate/code/ship-inter-21/rollback.py:46-48 COMPLETE
def bad_requests(rate, detect_s, rollback_s):
    """Requests served by the bad version = rate * its airtime."""
    return rate * airtime(detect_s, rollback_s)
```

**Keep the previous version warm in a second environment so rollback is a traffic flip, not a redeploy — the bad version's airtime drops from detection-plus-redeploy to detection-plus-flip — but pay for the doubled footprint, keep the idle side genuinely warm, and make schema changes backward-compatible, because an instant code flip does not roll back the data.**

## External resources

Martin Fowler's "BlueGreenDeployment" article — the canonical description of the two-environment pattern, the traffic switch, and the database-migration caveat that the flip does not roll back state.

Cloud providers' deployment documentation on blue-green and rolling versus in-place strategies (for example AWS CodeDeploy or Kubernetes deployment strategies) — the concrete mechanics and cost trade-offs of keeping a second environment.

The companion "canary the release to a slice first" and "migrate a schema in expand-contract steps" modules — canary limits blast radius while blue-green limits rollback time, and expand-contract is what keeps the instant flip safe when the schema has changed.
