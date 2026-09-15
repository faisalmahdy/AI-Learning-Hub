---
id: deadman-inter-01
title: Alert on the absence of a success, not only on errors — a job that stops running emits no error to catch
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: Error-based alerting fires on the presence of a bad thing — an exception, a failed run, a non-2xx status — which is the right shape for a job that runs and fails. It has a wide blind spot: a job that stops running entirely emits nothing. A crashed cron that never starts, a queue consumer wedged on a lock, a scheduler that skipped its trigger, a broker that quietly stopped delivering — none produce an error event, because nothing ran to produce one, so there is no event for an error rule to match and the alert stays quiet through the whole outage. Worse, silence reads as health: the dashboards are green and the error rate is zero precisely because the component is so broken it cannot even fail out loud, and the longer it is down the calmer the monitoring looks. The fix inverts the question with a dead man's switch: record the time of the last success and alert when the time since it exceeds the expected run interval plus a margin, so the alert fires on the absence of the heartbeat — the only signal a dead component still sends. Now a job that runs and fails trips the error rule and a job that silently dies trips the freshness rule. On a fixture where the job succeeds, errors once (caught by error alerting), succeeds again, then dies silently, error alerting sees no event after the last success at t=180 and never fires, while the freshness check sees the gap grow to 180 — past the interval-plus-margin threshold of 90 — and fires.
eli5: Imagine you ask a friend to text you "safe" every hour on a long drive. If you only worry when they text "I'm stuck," you will never worry when the scary thing happens — a crash where they can't text at all — because that sends no message. Silence is exactly the signal you must not ignore, and it is the one a bad-news-only rule cannot see. So instead you watch the clock: if more than an hour goes by with no "safe," you call. You are now alarmed by the missing check-in, not by a bad message, which is the only kind of alarm that catches a phone that went dead. A monitored job is the same — watch for the "I ran and it worked" that fails to arrive, not just for an error that announces itself.
---

## Why this module

Monitoring usually grows up around errors, because errors are what you see when something breaks: a stack trace, a 500, a failed job exit code. So the alerts get written to match errors — page when the error rate crosses a threshold, when an exception fires, when a run reports failure. This works well for the failure mode where a component runs and does the wrong thing.

There is a second failure mode it cannot touch: a component that stops running. A cron that the scheduler never triggered, a worker that crashed on startup, a consumer stuck forever on a lock, an upstream that quietly stopped sending. In all of these, the component produces no output at all — and critically, no error either, because producing an error requires running far enough to fail, and this component did not run. There is simply nothing.

An error rule matches events. When there are no events, there is nothing to match, so the rule never fires. That inverts the intuition in a dangerous way: the more completely a component has died, the quieter your error-based monitoring becomes, because a total stop produces total silence. The outage surfaces not from monitoring but from a human noticing downstream — the report never arrived, the data is a day stale, the queue is a million deep.

**Error-based alerting fires on the presence of a bad event, so it is blind to a component that stops running and emits nothing — and the more completely that component has died, the healthier the error monitoring looks.**

## Concepts

The two failure modes need two shapes of alert, because they present as opposites. A running-but-failing component emits a bad event, and you catch it by watching for that event to appear — presence detection. A stopped component emits nothing, and you catch it by watching for a good event to fail to arrive — absence detection. An error rule is presence detection; it structurally cannot do absence detection, because absence is not an event.

<svg role="img" aria-label="Two alert shapes. Error alert: a rule that watches a stream of events and fires when a bad (error) event appears. Freshness alert: a rule that watches the clock since the last success and fires when no success has arrived in too long." viewBox="0 0 440 130">
<text x="110" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">error alert (presence)</text>
<line x1="30" y1="55" x2="185" y2="55" stroke="var(--line)"/>
<circle cx="55" cy="55" r="3" fill="var(--s1)"/><circle cx="90" cy="55" r="3" fill="var(--s1)"/><circle cx="120" cy="55" r="4" fill="var(--s2)"/><text x="120" y="45" fill="var(--s2)" font-size="7" text-anchor="middle">error</text>
<text x="110" y="78" fill="var(--muted)" font-size="8" text-anchor="middle">fires when a bad event appears</text>
<text x="110" y="98" fill="var(--s2)" font-size="8" text-anchor="middle">nothing to match in silence</text>
<text x="330" y="16" fill="var(--muted)" font-size="9" text-anchor="middle">freshness alert (absence)</text>
<line x1="255" y1="55" x2="410" y2="55" stroke="var(--line)"/>
<circle cx="275" cy="55" r="3" fill="var(--s1)"/><circle cx="305" cy="55" r="3" fill="var(--s1)"/>
<line x1="305" y1="55" x2="405" y2="55" stroke="var(--s2)" stroke-dasharray="3 3"/>
<text x="360" y="48" fill="var(--s2)" font-size="7" text-anchor="middle">no success</text>
<text x="330" y="78" fill="var(--muted)" font-size="8" text-anchor="middle">fires when a good event is missing</text>
<text x="330" y="98" fill="var(--s1)" font-size="8" text-anchor="middle">silence is the trigger</text>
</svg>
^ Error alerting watches for a bad event to appear and has nothing to match in silence; a freshness alert watches for a good event to be missing, so silence is exactly what trips it.

The absence detector is the dead man's switch: a mechanism that fires unless it is continually reset by a sign of life. Here the sign of life is a successful run, so you record the timestamp of the last success and compute the gap between it and now. While the job runs on schedule, each success resets the timer and the gap stays small; when the job dies, no success arrives, the gap grows without bound, and once it passes a threshold the alert fires. The component's failure to check in is the trigger.

<svg role="img" aria-label="A line of the gap since last success over time. It stays low while successes arrive, resetting to near zero at each success, then after the job dies it climbs steadily and crosses a threshold line where the freshness alert fires." viewBox="0 0 440 130">
<line x1="40" y1="100" x2="410" y2="100" stroke="var(--line)"/>
<line x1="40" y1="20" x2="40" y2="100" stroke="var(--line)"/>
<text x="30" y="24" fill="var(--muted)" font-size="8" text-anchor="end">gap</text>
<line x1="40" y1="55" x2="410" y2="55" stroke="var(--s2)" stroke-dasharray="4 3"/>
<text x="405" y="50" fill="var(--s2)" font-size="8" text-anchor="end">threshold (interval + margin)</text>
<path d="M60 95 L 95 80 L 95 95 L 150 80 L 150 95 L 205 80 L 205 95" fill="none" stroke="var(--s1)"/>
<path d="M205 95 L 400 25" fill="none" stroke="var(--s1)"/>
<circle cx="300" cy="60" r="3" fill="var(--s2)"/><text x="300" y="52" fill="var(--s2)" font-size="7" text-anchor="middle">alert fires</text>
<text x="130" y="118" fill="var(--muted)" font-size="8">successes reset the gap</text>
<text x="340" y="118" fill="var(--muted)" font-size="8">job dead: gap climbs</text>
</svg>
^ Each success resets the gap toward zero; when the job dies the gap climbs steadily and, crossing the interval-plus-margin threshold, trips the dead man's switch.

The threshold is the one tuning decision, and it is a tradeoff. Too tight — barely above the interval — and normal jitter (a run that is a little late, a slow tick) trips a false alarm. Too loose and a real death goes unnoticed for a long time. The principled setting is the expected interval plus a margin that covers legitimate variance, so the alert fires only when a run is later than any healthy run would be. Both alerts then run together: the error rule for runs that fail loudly, the freshness rule for the silence that no error rule can see.

**A dead man's switch fires unless a sign of life keeps resetting it, so alert when the gap since the last success exceeds the interval plus a margin — tight enough to catch a real stop, loose enough to survive normal jitter — and run it alongside error alerting, which it complements rather than replaces.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/deadman-inter-01. The fixture is a job's event log, the expected run interval, a margin, and the current time.

```json filename=modules/ship-and-operate/code/deadman-inter-01/deadman.json:3-11 COMPLETE
  "events": [
    {"time": 0, "outcome": "success"},
    {"time": 60, "outcome": "success"},
    {"time": 120, "outcome": "error"},
    {"time": 180, "outcome": "success"}
  ],
  "interval": 60,
  "margin": 30,
  "now": 360
```

The sign of life is the last success.

```python filename=modules/ship-and-operate/code/deadman-inter-01/deadman.py:30-33 COMPLETE
def last_success_time(events):
    """The time of the most recent success, or None if there was never one."""
    successes = [e["time"] for e in events if e["outcome"] == "success"]
    return max(successes) if successes else None
```

Error alerting matches an error event; silence produces no event to match.

```python filename=modules/ship-and-operate/code/deadman-inter-01/deadman.py:36-38 COMPLETE
def error_alert_fires_after(events, since):
    """Error-based alerting: does any ERROR event occur at or after `since`? Silence emits no event."""
    return any(e["outcome"] == "error" and e["time"] >= since for e in events)
```

The dead man's switch fires on the gap since the last success exceeding the interval plus a margin.

```python filename=modules/ship-and-operate/code/deadman-inter-01/deadman.py:47-50 COMPLETE
def freshness_alert_fires(events, now, interval, margin):
    """Dead man's switch: fire when the gap since the last success exceeds the interval plus a margin."""
    gap = freshness_gap(events, now)
    return gap is not None and gap > interval + margin
```

Before running it, predict: the last event is a success at t=180 and now is 360, so nothing has happened for 180 — three intervals — but no error was emitted, so error alerting has nothing to fire on. Run `--timeline`:

```text filename=deadman.py --timeline
TIMELINE — the job's events, and the gap since the last success
----------------------------------------------------
  t=0     success
  t=60    success
  t=120   error
  t=180   success
  (no events after t=180 -- the job went silent)
----------------------------------------------------
  now=360  last success=180  gap=180  (expected interval 60)
```

The prediction holds. The job ran every 60 seconds, failed once at t=120 (which error alerting would have caught), recovered at t=180, and then stopped emitting anything. It is now t=360 — the job should have run at 240, 300, and 360 and did not — but there is no event after t=180, success or error. The gap since the last success is 180, three times the expected interval.

Now the two alerts on that silence. Run `--alerts`:

```text filename=deadman.py --alerts
ALERTS — does each scheme fire during the silent outage after the last success?
----------------------------------------------------
  error-based    : False  (looks for an error event after t=180 -- there is none)
  freshness-based: True  (gap 180 > interval+margin 90)
----------------------------------------------------
  error alerting is blind to silence; the freshness check catches the dead job
```

There it is. Error-based alerting is False — it scans for an error event after the last success and finds none, because a dead job emits none, so it stays quiet through a three-interval outage. The freshness check is True — the gap of 180 exceeds the interval-plus-margin threshold of 90 — so it fires. The error rule was not useless: it correctly caught the real error at t=120. But for the silent death after t=180 it is blind, and only the absence detector sees it.

<svg role="img" aria-label="Two alert states over the outage. The error alert line stays flat at 'not firing' the whole time after t=180. The freshness gap rises past the threshold at which its alert flips to firing." viewBox="0 0 440 130">
<line x1="40" y1="100" x2="410" y2="100" stroke="var(--line)"/>
<text x="20" y="40" fill="var(--muted)" font-size="8">alert</text>
<text x="30" y="60" fill="var(--s2)" font-size="8" text-anchor="end">error</text>
<line x1="40" y1="90" x2="410" y2="90" stroke="var(--s2)"/><text x="220" y="84" fill="var(--s2)" font-size="8" text-anchor="middle">error alert: never fires (silent outage)</text>
<text x="30" y="40" fill="var(--s1)" font-size="8" text-anchor="end">fresh</text>
<path d="M60 65 L 210 65 L 240 30 L 410 30" fill="none" stroke="var(--s1)"/>
<circle cx="240" cy="30" r="3" fill="var(--s1)"/><text x="245" y="26" fill="var(--s1)" font-size="7">fires (gap past threshold)</text>
<text x="130" y="118" fill="var(--muted)" font-size="8">t=180 last success</text>
</svg>
^ Through the silent outage the error alert never fires (no event to match), while the freshness alert flips to firing once the gap crosses the threshold.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that error alerting fires on the run that errored, that the job went silent after its last success (a big gap with no error), that error alerting is silent during the outage, that the freshness alert fires, and that the gap genuinely exceeds the interval plus margin.

```python filename=modules/ship-and-operate/code/deadman-inter-01/deadman.py:86-99 COMPLETE
    error_alert_catches_errors = error_alert_fires_after(events, 0)
    print("  error alerting fires on the run that errored = %s (a real error at some t)" % error_alert_catches_errors)

    gap = freshness_gap(events, now)
    job_died_silently = gap > interval and not error_alert_fires_after(events, last)
    print("  the job went silent after its last success (big gap, no error) = %s (gap %d)" % (job_died_silently, gap))

    error_alert_misses_silence = not error_alert_fires_after(events, last)
    print("  error alerting is silent during the outage = %s (no error event after t=%d)" % (error_alert_misses_silence, last))

    freshness_fires = freshness_alert_fires(events, now, interval, margin)
    print("  the freshness (dead man's switch) alert fires = %s" % freshness_fires)

    gap_is_abnormal = gap > interval + margin
    print("  the gap exceeds the interval plus margin (genuinely late) = %s (%d > %d)" % (gap_is_abnormal, gap, interval + margin))
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if error alerting ever caught the silence or the freshness check ever missed it:

```text filename=deadman.py --check
SELF-TEST — error alerting catches the errored run but misses the silent death; the freshness check catches it
----------------------------------------------------------------------------------------------------------------
  error alerting fires on the run that errored = True (a real error at some t)
  the job went silent after its last success (big gap, no error) = True (gap 180)
  error alerting is silent during the outage = True (no error event after t=180)
  the freshness (dead man's switch) alert fires = True
  the gap exceeds the interval plus margin (genuinely late) = True (180 > 90)
```

**The self-test first confirms error alerting works (it catches the real error) and then that it is blind to the silence — so a pass proves the gap is not that error alerting is broken, but that it is structurally unable to see an absence, which only the freshness check can.**

## Definition of done

You can explain why error-based alerting cannot detect a component that stops running.
You can explain why silence reads as health and why the failure surfaces downstream instead of from monitoring.
You can describe a dead man's switch and why the sign of life must continually reset it.
You can explain the threshold tradeoff (interval plus margin) between false alarms on jitter and slow detection.
You can explain why the error rule and the freshness rule are complementary, not alternatives.

## Boss fight

Suppose you add a freshness alert on the last success, but the monitoring system that runs the check is itself a component that can die. Reason about the gap. If the alerting pipeline crashes, it will not evaluate the freshness rule, so a job death during that window goes unnoticed — you have moved the dead man's switch's own liveness into a new blind spot. This is why production dead man's switches are often externalized: the job pushes a heartbeat to a third-party service (a healthcheck.io-style endpoint, a separate cluster's monitoring) that fires an alert if the ping does not arrive, so the thing watching for absence is not the same system that might be absent. The general principle is that an absence detector must be more reliable than the thing it watches, and ideally in a different failure domain — you cannot detect your own silence, so someone outside has to.

Now the subtlety that makes freshness alerts either noisy or slow: what "the interval" is when it is not fixed. A cron every 60 seconds has a clean expected interval, but many jobs are irregular — a nightly batch, an event-driven consumer whose rate varies, a weekend-quiet workload — and a single fixed threshold is wrong for all of them, either paging on a normal quiet period or missing a death during a busy one. The refinements mirror the adaptive-timeout idea from failure detection: set the threshold from the observed inter-success distribution (a multiple of the typical gap, or a percentile) rather than a guessed constant, schedule-aware thresholds that relax on weekends or known-idle windows, and for event-driven work, alert on the rate of successes dropping rather than a single gap. The invariant is unchanged — watch for the expected sign of life to go missing — but "expected" has to track the job's real cadence, not a constant, or the switch is either a nuisance or a no-op.

**A dead man's switch must be run by something more reliable than, and in a different failure domain from, the job it watches — externalize the heartbeat so the watcher is not the component that might be absent; and set the freshness threshold from the job's real inter-success cadence (or its rate), not a fixed constant, or an irregular schedule makes the alert either noisy or slow.**

## External resources

Dead man's switch / heartbeat monitoring services (Healthchecks.io, Cronitor, PagerDuty's and Prometheus's absence rules such as the `absent()` and `absent_over_time()` functions) implement exactly this absence detection for scheduled jobs.
Google's Site Reliability Engineering material on alerting distinguishes symptom-based alerts and freshness/staleness monitoring, and warns that a healthy-looking error rate can hide a stopped pipeline.
The topic's own module on error-budget burn-rate alerting covers the presence-detection side (alerting on an elevated error rate), and the failure-detection module on scoring a missing heartbeat against a node's timing variance covers the adaptive-threshold refinement this one's boss fight points to.
