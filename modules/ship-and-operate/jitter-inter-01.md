---
id: jitter-inter-01
title: Add jitter to the retry backoff — without it, every client that failed together retries together and recreates the spike
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: Exponential backoff is the standard retry discipline — after a failure, wait, and double the wait each time so a struggling dependency is not hammered — and it fixes the rate at which a single client retries while doing nothing about the problem that actually takes systems down: synchronization. When a shared dependency has a blip, every client fails at nearly the same instant, each computes the same backoff delay, and all of them retry at the same moment in one synchronized wave — which is the exact load spike that caused the outage, arriving again just as the dependency tries to recover. Backoff spread out one client's retries in time; it lined up all the clients' retries at the same time. This is the thundering herd, and it can wedge a system into a retry-storm loop where the herd hits, everyone backs off by the same (doubled) delay, and the herd re-forms in lockstep, so the dependency never gets a quiet interval to recover. Jitter breaks the synchronization by randomizing the delay: instead of every client waiting exactly the backoff, each waits a random amount (full jitter picks a retry time uniformly between zero and the backoff), so retries that used to land in one instant are smeared across the window and the dependency sees a trickle it can absorb instead of a wall it cannot. Jitter does not reduce the number of retries or slow any client meaningfully — it only de-synchronizes them. On a fixture where six clients fail together with a backoff of 4, without jitter all six retry at once (peak concurrency 6), while full jitter spreads their retry times into buckets [2, 1, 1, 2], dropping the peak to 2 — the same six retries, de-synchronized.
eli5: Imagine a whole classroom rushes to the water fountain at the exact same second the bell rings — there's a crush, nobody can drink, everyone gives up, waits, and then rushes again all together, and the crush happens again. The problem isn't that they drink too often; it's that they all go at the same moment. The fix is for each kid to wait a slightly different random amount of time before heading to the fountain, so they arrive spread out and there's never a crush. They still all get their water; they just don't all show up at once. For computers retrying a failed request, jitter is that "wait a random little bit" rule.
---

## Why this module

Backoff is universally recommended and universally implemented, and on its own it does not prevent the failure mode people reach for it to prevent. The reason is a subtle mismatch between what backoff controls and what causes cascading outages. Backoff controls the timing of one client's retries — it makes a single client politely slow down. Cascading outages are caused by many clients doing the same thing at the same time, and backoff, applied identically by every client, does not desynchronize them; it keeps them in lockstep. Understanding jitter is understanding that correlated failures require uncorrelated recoveries, and that a fixed backoff provides the opposite.

The trigger is that failures are correlated by construction. A shared dependency serves many clients, so when it hiccups, they all fail within a narrow window. Each applies the same backoff formula to the same starting time and arrives at the same retry moment. The retries pile up into a spike as large as the original traffic — the thundering herd — which knocks the dependency back down, and the cycle repeats with a longer but still-identical delay. The system oscillates instead of recovering, because nothing in the retry logic breaks the clients out of phase.

Jitter is the missing randomization, and this module makes its effect concrete by counting how many retries land at once with and without it.

**Add random jitter to the retry backoff delay (e.g. full jitter: a random wait uniform in [0, backoff]) rather than retrying after a fixed backoff, because clients that fail together compute the same fixed delay and retry in a synchronized wave that recreates the original load spike — while jitter spreads the same retries across the window so the recovering dependency sees a trickle, not a herd.**

## Concepts

The fixture is six clients that all failed at the same instant, a backoff delay of 4, and a window divided into 4 time buckets. Each client carries a jitter fraction — the pre-drawn random value in [0, 1) that full jitter uses to pick its retry time.

```json filename=modules/ship-and-operate/code/jitter-inter-01/jitter.json:3-6 COMPLETE
  "base_delay": 4,
  "num_buckets": 4,
  "clients": [
    {"id": "c1", "jitter_frac": 0.1},
```

Without jitter, every client retries at exactly the backoff delay. With full jitter, each retries at its fraction times the backoff — a time uniform in [0, backoff). The bucket function says which time slot a retry lands in.

```python filename=modules/ship-and-operate/code/jitter-inter-01/jitter.py:32-44 COMPLETE
def no_jitter_time(base):
    """Without jitter, every client retries at exactly the backoff delay."""
    return base


def full_jitter_time(jitter_frac, base):
    """Full jitter: a retry time uniform in [0, base) -- here the pre-drawn fraction times base."""
    return jitter_frac * base


def bucket(t, base, num_buckets):
    """Which time slot a retry lands in (clamped to the last slot)."""
    return min(int(t / base * num_buckets), num_buckets - 1)
```

Counting the full-jitter retries per bucket gives the arrival profile the dependency sees — the peak of that profile is the herd size.

```python filename=modules/ship-and-operate/code/jitter-inter-01/jitter.py:47-51 COMPLETE
def buckets_full_jitter(clients, base, num_buckets):
    counts = [0] * num_buckets
    for c in clients:
        counts[bucket(full_jitter_time(c["jitter_frac"], base), base, num_buckets)] += 1
    return counts
```

<svg role="img" aria-label="Two arrival profiles: without jitter all six retries pile into one time slot; with jitter they spread across four slots as 2,1,1,2" viewBox="0 0 320 130">
  <text x="10" y="16" font-size="8.5" fill="var(--s2)">no jitter: all 6 at t=4</text>
  <line x1="20" y1="60" x2="150" y2="60" stroke="var(--line)" stroke-width="1"/>
  <rect x="128" y="20" width="16" height="40" fill="var(--s2)"/><text x="126" y="16" font-size="8" fill="var(--s2)">6</text>
  <text x="10" y="86" font-size="8.5" fill="var(--s1)">full jitter: spread [2,1,1,2]</text>
  <line x1="180" y1="120" x2="310" y2="120" stroke="var(--line)" stroke-width="1"/>
  <rect x="184" y="104" width="26" height="16" fill="var(--s1)"/><text x="192" y="116" font-size="7" fill="var(--panel)">2</text>
  <rect x="214" y="112" width="26" height="8" fill="var(--s1)"/>
  <rect x="244" y="112" width="26" height="8" fill="var(--s1)"/>
  <rect x="274" y="104" width="26" height="16" fill="var(--s1)"/><text x="282" y="116" font-size="7" fill="var(--panel)">2</text>
  <text x="180" y="100" font-size="7.5" fill="var(--muted)">peak 2 across the window</text>
</svg>
^ Without jitter the six retries stack into one instant — a spike of 6. With jitter the same six spread across the window as [2, 1, 1, 2], so the dependency's worst moment sees 2, not 6. Same retries, unstacked.

<svg role="img" aria-label="A loop: dependency blip causes all clients to fail together, they back off the same delay, retry in a synchronized wave, which overloads the dependency again, repeating" viewBox="0 0 320 120">
  <rect x="20" y="20" width="80" height="22" fill="none" stroke="var(--s2)" stroke-width="1.2"/><text x="30" y="34" font-size="7.5" fill="var(--ink)">blip → all fail</text>
  <rect x="220" y="20" width="80" height="22" fill="none" stroke="var(--s2)" stroke-width="1.2"/><text x="228" y="34" font-size="7.5" fill="var(--ink)">same backoff</text>
  <rect x="220" y="78" width="80" height="22" fill="none" stroke="var(--s2)" stroke-width="1.2"/><text x="226" y="92" font-size="7.5" fill="var(--ink)">synchronized wave</text>
  <rect x="20" y="78" width="80" height="22" fill="none" stroke="var(--s2)" stroke-width="1.2"/><text x="26" y="92" font-size="7.5" fill="var(--ink)">overload again</text>
  <line x1="100" y1="31" x2="220" y2="31" stroke="var(--ink)" stroke-width="1"/>
  <line x1="260" y1="42" x2="260" y2="78" stroke="var(--ink)" stroke-width="1"/>
  <line x1="220" y1="89" x2="100" y2="89" stroke="var(--ink)" stroke-width="1"/>
  <line x1="60" y1="78" x2="60" y2="42" stroke="var(--ink)" stroke-width="1"/>
  <text x="120" y="65" font-size="7.5" fill="var(--s2)">lockstep loop — jitter breaks it here</text>
</svg>
^ Without jitter the system loops: a blip fails everyone, they back off by the same delay, retry in one wave, overload the dependency, and repeat — in lockstep. Jitter breaks the loop at the "same backoff" step by making each client wait a different time.

**Backoff sets how long each client waits; jitter sets whether they wait the same length — and only the second decides whether correlated failures produce a correlated retry spike.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the retry step of a resilient client, reduced to six clients so every retry time is checkable by hand.

Run `--retries` to see each client's retry time both ways.

```text filename=jitter.py --retries
  client   no-jitter time   jitter time   jitter bucket
  c1       4                0.4           0
  c2       4                3.6           3
  c3       4                1.2           1
  c4       4                2.4           2
  c5       4                0.8           0
  c6       4                3.2           3
  without jitter every client retries at t=4; with jitter they spread across [0,4)
```

The no-jitter column is 4 for every client — they all retry at the same instant, because they all applied the same backoff to the same failure time. The jitter column is spread across the window: c1 at 0.4, c3 at 1.2, c4 at 2.4, c2 at 3.6, and so on. Same six clients, same backoff, but their retry times now range across the whole [0, 4) window instead of collapsing to a single point.

Now `--peak` counts the herd.

```text filename=jitter.py --peak
  no jitter:  all 6 retries at t=4 -> peak concurrency 6
  full jitter: buckets [2, 1, 1, 2] -> peak concurrency 2
  total retries: 6 both ways (jitter spreads them, it does not reduce them)
```

Without jitter, the peak concurrency is 6 — all six retries hit the dependency in the same instant, the spike that re-triggers the outage. With jitter, the retries fall into buckets [2, 1, 1, 2], so the worst instant sees only 2. And the last line is the honest accounting: both approaches issue exactly 6 retries. Jitter did not make the clients retry less or give up; it de-synchronized them, converting a spike of 6 into a smooth arrival of at most 2 at a time — which is the difference between a dependency that recovers and one that gets knocked back down.

**Jitter cut the peak from 6 to 2 without changing the total of 6 retries — it did not reduce the work, it unstacked it, turning the herd into a trickle the recovering dependency can absorb.**

## Build

The self-test asserts the failure and the fix: without jitter every client retries at the same time and the peak equals the herd size, while jitter spreads the retries across buckets and lowers the peak.

```python filename=modules/ship-and-operate/code/jitter-inter-01/jitter.py:89-99 COMPLETE
    all_synchronize_no_jitter = len({no_jitter_time(base) for _ in clients}) == 1
    print("  without jitter every client retries at the same time = %s (all at t=%d)" % (all_synchronize_no_jitter, base))

    no_jitter_peak_is_n = no_jitter_peak == n
    print("  the no-jitter peak concurrency equals the herd size = %s (%d)" % (no_jitter_peak_is_n, no_jitter_peak))

    jitter_spreads = sum(1 for b in jbuckets if b > 0) > 1
    print("  jitter spreads retries across multiple time buckets = %s (%s)" % (jitter_spreads, jbuckets))

    jitter_lowers_peak = jitter_peak < no_jitter_peak
    print("  jitter lowers the peak concurrency = %s (%d < %d)" % (jitter_lowers_peak, jitter_peak, no_jitter_peak))
```

<svg role="img" aria-label="Two peak bars: no jitter peak 6, jitter peak 2, with a note that total retries are 6 in both" viewBox="0 0 320 100">
  <text x="10" y="16" font-size="8.5" fill="var(--muted)">peak concurrent retries (herd size)</text>
  <text x="10" y="40" font-size="8.5" fill="var(--s2)">no jitter</text>
  <rect x="80" y="30" width="180" height="16" fill="var(--s2)"/><text x="264" y="43" font-size="8" fill="var(--ink)">6</text>
  <text x="10" y="68" font-size="8.5" fill="var(--s1)">jitter</text>
  <rect x="80" y="58" width="60" height="16" fill="var(--s1)"/><text x="144" y="71" font-size="8" fill="var(--ink)">2</text>
  <text x="10" y="92" font-size="7.5" fill="var(--muted)">total retries: 6 both ways — jitter unstacks, it does not reduce</text>
</svg>
^ The no-jitter peak is the full herd of 6; the jitter peak is 2. Both issue 6 retries total — the bar shrinks because the retries are spread over time, not because there are fewer of them.

Running the check confirms every clause, including that the total is unchanged and the jittered peak is near the uniform ideal.

```text filename=jitter.py --check
  without jitter every client retries at the same time = True (all at t=4)
  the no-jitter peak concurrency equals the herd size = True (6)
  jitter spreads retries across multiple time buckets = True ([2, 1, 1, 2])
  jitter lowers the peak concurrency = True (2 < 6)
  the total number of retries is unchanged by jitter = True (6)
  the jittered peak is near the uniform ideal (~n/buckets) = True (peak 2 vs ideal ~2)
```

**The check ties the spike to synchronization and the relief to spreading — same six retries, peak cut from 6 to 2 — so jitter is shown desynchronizing the herd, not throttling it.**

## Definition of done

Two properties close it. The total number of retries must be unchanged by jitter (it de-synchronizes, it does not throttle), and the jittered peak must be near the uniform ideal of about n/buckets (the spreading is effective, not token). Together they show jitter converts a spike into a near-flat arrival profile without dropping any retries.

```python filename=modules/ship-and-operate/code/jitter-inter-01/jitter.py:101-105 COMPLETE
    total_retries_same = sum(jbuckets) == n
    print("  the total number of retries is unchanged by jitter = %s (%d)" % (total_retries_same, sum(jbuckets)))

    peak_near_uniform = jitter_peak <= (n + nb - 1) // nb + 1
    print("  the jittered peak is near the uniform ideal (~n/buckets) = %s (peak %d vs ideal ~%d)" % (peak_near_uniform, jitter_peak, -(-n // nb)))
```

Three clarifications keep the tool precise. First, jitter and backoff are complementary, not alternatives: backoff controls the growing delay for a single client (so a persistently failing dependency is retried ever more slowly), jitter desynchronizes clients from each other — you want both, which is why the standard recommendation is exponential backoff *with* jitter. Second, "full jitter" (uniform in [0, backoff]) is one of several schemes; AWS's analysis found full jitter and "decorrelated jitter" both effective, and the key finding is that some jitter dramatically beats none while the exact scheme matters less — a common mistake is "equal jitter" that only jitters half the delay, leaving a partial spike. Third, the randomness must be independent per client: seeding every client's RNG identically, or deriving jitter from a value they share (the same request id), re-synchronizes them and defeats the purpose — the jitter has to be uncorrelated across clients, which is the whole point. And jitter is not a substitute for the other retry-storm defenses (a retry budget or circuit breaker to cap total retries, load shedding to protect the dependency); it addresses timing, while those address volume.

**Done means jitter leaves the retry total unchanged while cutting the peak toward the uniform ideal — a timing de-synchronization (not a throttle), effective only when the randomness is independent per client and paired with backoff.**

## Boss fight

A service depends on a database that occasionally has a brief hiccup, and the team added exponential backoff to the client to handle it. But now, instead of recovering from hiccups, the system experiences full outages: a one-second database blip turns into a multi-minute outage where the database is pinned at 100% and keeps failing. The backoff delays are clearly working (they see the retries slowing down), yet it is worse than before. What is happening, and what is the fix?

The backoff is working per-client but the clients are synchronized, which turns the hiccup into a self-sustaining retry storm. When the database blips, every client's in-flight request fails at nearly the same instant; each applies the same exponential backoff to the same failure time and retries at the same moment, so all the retries arrive as one spike — as large as the original traffic — which re-overloads the just-recovering database and makes it fail again. Every client then backs off by the same (now doubled) delay and retries in lockstep again, so the database is hit by wave after synchronized wave and never gets the quiet interval it needs to recover; the backoff got longer but the clients stayed in phase, which is why they see retries "slowing down" while the outage drags on. The fix is to add jitter to the backoff: randomize each client's wait (full jitter — a random delay uniform in [0, current backoff]) so the retries that used to land in one instant spread across the window and the database sees an absorbable trickle instead of a wall. Make sure the jitter is independent per client (do not seed all clients' randomness the same way or derive it from a shared value) so they actually desynchronize. Keep the exponential backoff — you want backoff *with* jitter — and, to be safe against the volume as well as the timing, add a retry budget or circuit breaker so total retries are capped and the clients stop hammering entirely if the database stays down. The single change that stops the storm, though, is jitter: it breaks the lockstep that converts a one-second blip into a multi-minute outage.

## External resources

Marc Brooker's AWS Architecture Blog post "Exponential Backoff and Jitter" — the canonical analysis showing that adding jitter dramatically reduces contention and comparing full, equal, and decorrelated jitter, the source of the schemes described here.

Google's *Site Reliability Engineering*, the chapters on addressing cascading failures and handling overload — why synchronized retries cause retry storms, and how jitter combines with retry budgets, circuit breakers, and load shedding to keep a hiccup from becoming an outage.
