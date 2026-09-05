---
id: govern-inter-21
title: Add jitter to backoff — or every client that failed together retries together and stampedes the recovery
topic: orchestration-and-governance
level: intermediate
status: ready
time: 18 min
summary: Exponential backoff fixes the rate of one client's retries but not the phase across many. When a shared dependency fails, every client fails at nearly the same instant, and if they all use the same backoff schedule they wait the same amount and retry at the same instant too — a synchronized wave that knocks the recovering dependency flat again. Full jitter draws each wait as uniform(0, base·2^attempt) instead of exactly base·2^attempt, so clients that failed together retry at different moments. On 12 clients failing together and retrying 3 times with base 4s, no-jitter backoff lands all 12 retries of each wave in a single second (peak 12); full jitter spreads the same 36 retries across 14 seconds, dropping the busiest second to 7 — same total work, a fraction of the peak.
eli5: If everyone leaves a concert the moment it ends, the exits jam even though the building is empty a minute later. Telling people to wait before leaving does not help if they all wait the same amount — they still leave together. The fix is for each person to wait a different random amount, so the crowd trickles out instead of surging. Retries work the same way: same delay for everyone just moves the traffic jam; a random delay spreads it out.
---

## Why this module

Backoff spaces out one client's retries in time, but it does nothing about the fact that a thousand clients hit the same delay in lockstep — so the retries you spread out for one client arrive all at once across the fleet.

When a shared dependency goes down, every client that depends on it fails at nearly the same instant. If they all retry with the same exponential schedule — wait 4s, then 8s, then 16s — they all wait the same 4s and all retry at the same moment. Backoff controlled the rate of each client's attempts, which is what it is for, but it left every client in phase. The dependency, just clawing back up, is hit by the entire fleet in a single instant: a thundering herd that knocks it down again, and the cycle repeats. You did everything the backoff advice said and still built a synchronized stampede.

**Exponential backoff sets the rate of one client's retries; it does not disperse the phase across many clients, so a fleet on identical backoff retries in lockstep and stampedes the recovering dependency.**

The fix is jitter: instead of waiting exactly the backoff, wait a random amount up to it. Two clients that failed together now draw independent waits and retry at different moments, so the wave smears out across the window. The same number of retries still happens — jitter does not drop work — but the peak load at any one instant collapses. This module simulates a fleet failing together and measures the peak second with and without jitter.

## Concepts

**Exponential backoff** makes attempt `a` wait `base · 2^a` — 4s, 8s, 16s — so a single client backs off a struggling dependency instead of hammering it.

The **thundering herd** is what backoff misses: when many clients fail at the same instant and share a schedule, they all wait the same amount and retry at the same instant, delivering the whole fleet's load in one spike.

**Peak load** is the metric that matters to the recovering dependency — the most retries arriving in one second, not the total. A dependency can absorb 36 retries spread over 30 seconds and fall over under 12 in one.

**Full jitter** replaces the exact wait with `uniform(0, base · 2^a)`. Each client draws independently, so clients that failed together retry at different times; the wave is smeared across the whole backoff window.

**Jitter spreads work, it does not reduce it.** The total number of retries is identical with and without jitter — the same 36 attempts happen — but they land across many seconds instead of piling into one, so the peak drops even though the total is unchanged.

**Backoff without jitter reschedules the stampede to a later instant; jitter is what actually disperses it, trading a spike of N into a trickle the recovering dependency can absorb.**

<svg role="img" aria-label="Clients failing together with identical backoff all retry at the same instant; with jitter their retries land at spread-out instants" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">four clients, all fail at t=0</text>
  <text x="8" y="34" fill="var(--s1)" font-size="8">same wait</text>
  <line x1="70" y1="24" x2="70" y2="44" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="180" cy="30" r="4" fill="var(--s1)"/><circle cx="180" cy="30" r="4" fill="var(--s1)"/><circle cx="182" cy="34" r="4" fill="var(--s1)"/><circle cx="178" cy="26" r="4" fill="var(--s1)"/>
  <text x="192" y="34" fill="var(--muted)" font-size="8">all 4 retry at one instant (spike)</text>
  <text x="8" y="84" fill="var(--s2)" font-size="8">jittered</text>
  <line x1="70" y1="74" x2="70" y2="94" stroke="var(--grid)" stroke-width="1"/>
  <circle cx="110" cy="84" r="4" fill="var(--s2)"/><circle cx="150" cy="84" r="4" fill="var(--s2)"/><circle cx="205" cy="84" r="4" fill="var(--s2)"/><circle cx="250" cy="84" r="4" fill="var(--s2)"/>
  <text x="70" y="112" fill="var(--muted)" font-size="8">independent waits spread the same 4 retries across the window</text>
</svg>
^ Identical backoff stacks all four retries on one instant; jitter draws four independent waits so they land spread apart — same clients, dispersed load.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/govern-inter-21/backoff.py

The fixture is a fleet that fails together, with a backoff base and a seed for the jitter.

```json filename=modules/orchestration-and-governance/code/govern-inter-21/backoff.json:1-8 COMPLETE
{
  "_meta": "A thundering-herd simulation. clients all fail at t=0 (a shared dependency went down) and each retries `attempts` times with exponential backoff: attempt a waits up to base*2^a seconds. Without jitter every client waits exactly that, so all `clients` retries land in the same time bucket. With FULL jitter each client waits a uniform random time in [0, base*2^a), spreading the retries across the window. We bucket every retry arrival into 1-second bins and report the peak bin — the most retries hitting the recovering server in one second. seed makes the jitter deterministic.",
  "clients": 12,
  "base": 4,
  "attempts": 3,
  "seed": 7
}
```

Each retry's arrival time is the cumulative wait. The only difference between the two policies is one line: wait exactly the cap, or a uniform draw up to it.

```python filename=modules/orchestration-and-governance/code/govern-inter-21/backoff.py:42-54 COMPLETE
def arrivals(clients, base, attempts, seed, jitter):
    """Every retry's arrival second. All clients fail at t=0; attempt a has backoff cap base*2^a.
    jitter=False waits exactly the cap; jitter=True waits uniform(0, cap). Returns a list of int seconds."""
    rng = random.Random(seed)
    out = []
    for _ in range(clients):
        t = 0.0
        for a in range(attempts):
            cap = base * (2 ** a)
            wait = rng.uniform(0, cap) if jitter else cap
            t += wait
            out.append(int(t))
    return out
```

The peak is the busiest one-second bucket — the load the recovering dependency actually feels.

```python filename=modules/orchestration-and-governance/code/govern-inter-21/backoff.py:57-65 COMPLETE
def histogram(times):
    """Retries per 1-second bucket."""
    return Counter(times)


def peak(times):
    """The most retries landing in any single second."""
    h = histogram(times)
    return max(h.values()) if h else 0
```

Run `--load` to see the per-second histogram.

```text filename=--load
LOAD — retries per second (12 clients, base 4s, 3 attempts)
--------------------------------------------------------------
  no jitter:  12@4s 12@12s 12@28s
  full jitter:7@0s 4@1s 4@2s 2@3s 5@4s 3@5s 1@6s 1@7s 1@8s 2@10s 1@11s 1@12s 2@14s 2@21s
--------------------------------------------------------------
  no jitter piles every wave into one second; jitter smears each wave across the window.
```

Without jitter every client retries at exactly 4s, 12s, 28s — so all 12 land together three times, three spikes of 12. With jitter the same retries scatter across fourteen different seconds, the busiest holding 7. The waves that were three vertical walls become a low, spread-out trickle.

<svg role="img" aria-label="Without jitter three spikes of twelve retries; with jitter the same retries spread across many seconds with a much lower peak" viewBox="0 0 300 130" width="300" height="130">
  <text x="10" y="12" fill="var(--muted)" font-size="8">retries per second (bar height)</text>
  <line x1="20" y1="60" x2="290" y2="60" stroke="var(--grid)" stroke-width="1"/>
  <text x="8" y="30" fill="var(--s1)" font-size="8">no jitter</text>
  <rect x="60" y="12" width="8" height="48" fill="var(--s1)"/><rect x="120" y="12" width="8" height="48" fill="var(--s1)"/><rect x="200" y="12" width="8" height="48" fill="var(--s1)"/>
  <text x="52" y="70" fill="var(--muted)" font-size="7">4s</text><text x="112" y="70" fill="var(--muted)" font-size="7">12s</text><text x="192" y="70" fill="var(--muted)" font-size="7">28s</text>
  <text x="8" y="90" fill="var(--s2)" font-size="8">full jitter</text>
  <rect x="24" y="88" width="6" height="28" fill="var(--s2)"/><rect x="30" y="104" width="6" height="12" fill="var(--s2)"/><rect x="36" y="104" width="6" height="12" fill="var(--s2)"/><rect x="42" y="112" width="6" height="4" fill="var(--s2)"/><rect x="48" y="100" width="6" height="16" fill="var(--s2)"/><rect x="54" y="108" width="6" height="8" fill="var(--s2)"/><rect x="60" y="114" width="6" height="2" fill="var(--s2)"/><rect x="72" y="114" width="6" height="2" fill="var(--s2)"/><rect x="90" y="112" width="6" height="4" fill="var(--s2)"/><rect x="108" y="112" width="6" height="4" fill="var(--s2)"/><rect x="150" y="112" width="6" height="4" fill="var(--s2)"/>
  <text x="24" y="128" fill="var(--muted)" font-size="8">same 36 retries — three walls of 12 become a spread with peak 7</text>
</svg>
^ The no-jitter policy is three tall bars of 12; full jitter is many short bars, the tallest just 7 — the identical work, dispersed.

## Build

The peak is the number that decides whether the dependency survives. Run `--peak`.

```text filename=--peak
PEAK — busiest second and total retries
--------------------------------------------------------------
  no jitter:    peak 12 retries/s   total 36 retries
  full jitter:  peak  7 retries/s   total 36 retries
--------------------------------------------------------------
  same total work; jitter cuts the peak from 12 to 7 per second.
```

Both policies issue exactly 36 retries — jitter did not skip any work. But the no-jitter peak is 12, the entire fleet in one second, and the jitter peak is 7. The recovering dependency is sized for the peak, not the total, so cutting the peak from 12 to 7 is the difference between absorbing the recovery load and being knocked down by it. Note the peak fell without adding a single unit of delay to the schedule — jitter is free capacity, bought only by giving up the (worthless) guarantee that everyone retries at the same instant.

<svg role="img" aria-label="No jitter peak is 12 equal to all clients; full jitter peak is 7; both issue 36 total retries" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">peak retries in one second (total 36 either way)</text>
  <line x1="70" y1="20" x2="70" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="90" x2="285" y2="90" stroke="var(--grid)" stroke-width="1"/>
  <rect x="70" y="28" width="180" height="20" fill="var(--s1)"/><text x="254" y="42" fill="var(--muted)" font-size="8">no jitter: 12 = all clients</text>
  <rect x="70" y="58" width="105" height="20" fill="var(--s2)"/><text x="179" y="72" fill="var(--muted)" font-size="8">full jitter: 7</text>
  <text x="70" y="106" fill="var(--muted)" font-size="8">the recovering dependency is sized for the peak, and jitter nearly halves it</text>
</svg>
^ Both bars represent 36 total retries, but the no-jitter peak spans all 12 clients while jitter's peak is 7 — the recovery survives the shorter bar.

## Definition of done

The self-test pins the four claims: no jitter peaks at the full fleet, jitter cuts the peak, the total is unchanged, and jitter occupies more seconds — plus that the seeded jitter is reproducible.

```python filename=modules/orchestration-and-governance/code/govern-inter-21/backoff.py:103-116 COMPLETE
    no_jitter_peak_is_all_clients = peak(plain) == c
    print("  without jitter the peak second holds every client = %s (%d = %d)" % (no_jitter_peak_is_all_clients, peak(plain), c))

    jitter_cuts_peak = peak(jit) < peak(plain)
    print("  jitter lowers the peak second = %s (%d < %d)" % (jitter_cuts_peak, peak(jit), peak(plain)))

    total_unchanged = len(jit) == len(plain) == c * a
    print("  the total retries are unchanged = %s (%d = %d = %d*%d)" % (total_unchanged, len(jit), len(plain), c, a))

    jitter_spreads_wider = len(histogram(jit)) > len(histogram(plain))
    print("  jitter occupies more distinct seconds = %s (%d buckets vs %d)" % (jitter_spreads_wider, len(histogram(jit)), len(histogram(plain))))

    jit_again = arrivals(c, b, a, s, jitter=True)
    deterministic = jit == jit_again
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — no jitter peaks at all clients at once; jitter cuts the peak; the total is unchanged
----------------------------------------------------------------------------------------------------
  without jitter the peak second holds every client = True (12 = 12)
  jitter lowers the peak second = True (7 < 12)
  the total retries are unchanged = True (36 = 36 = 12*3)
  jitter occupies more distinct seconds = True (14 buckets vs 3)
  the seeded jitter is reproducible = True
----------------------------------------------------------------------------------------------------
SELF-TEST PASS  no_jitter_peak_is_all_clients=True  jitter_cuts_peak=True  total_unchanged=True  jitter_spreads_wider=True  deterministic=True
```

**Done means the peak is provably cut without dropping work: no-jitter backoff peaks at 12 (the whole fleet) in one second, jitter peaks at 7 across 14 seconds, and both issue the same 36 retries.**

## Boss fight

Jitter cut the peak here. Predict what happens if, worried that pure-random jitter wastes time, you keep the backoff exact and only add a tiny fixed offset — say every client waits `base + client_id · 0.001`. It is tempting to add the smallest perturbation that "technically" differs per client.

A tiny deterministic offset does not disperse a large fleet, because the spread has to be comparable to the backoff window, not to a millisecond. Ten thousand clients each 1ms apart still deliver the whole fleet inside ten seconds, and if the offset is smaller than your bucket they land in the same instant anyway. The point of jitter is not that the waits merely differ; it is that they are spread across the *whole* backoff interval, so the load density per instant falls by roughly the fleet-to-window ratio. Full jitter — uniform over the entire `[0, cap)` — is what achieves that; a cosmetic tie-breaker does not. Jitter has to be a real fraction of the backoff, not a rounding error on top of it.

The opposite over-correction is to jitter so widely that you lose backoff's rate control — for instance drawing waits from `[0, huge]` regardless of attempt. Then early retries can fire almost immediately and you are back to hammering. Full jitter keeps the exponential cap growing per attempt and only randomizes *within* each attempt's window, so the rate still backs off while the phase disperses. The two jobs — backoff sets the growing ceiling, jitter randomizes under it — must both be present; drop either and you get a stampede or a hammer.

```python filename=modules/orchestration-and-governance/code/govern-inter-21/backoff.py:50-51 COMPLETE
            cap = base * (2 ** a)
            wait = rng.uniform(0, cap) if jitter else cap
```

**Backoff sets a per-attempt ceiling that grows; full jitter draws each wait uniformly under that ceiling so a fleet that failed together retries at dispersed moments — keep both, because backoff alone reschedules the stampede and jitter without the growing cap just hammers.**

## External resources

The AWS Architecture Blog post "Exponential Backoff And Jitter" — the canonical treatment, including the full-jitter versus equal-jitter comparison and the measured reduction in contention.

The Google SRE book chapter on handling overload and cascading failures — jitter appears alongside retry budgets and the broader lesson that synchronized clients are the root of thundering herds.

The companion "circuit breaker" and "bounded queue and backpressure" modules — jitter disperses the retry wave, while those two cap how many retries are attempted at all; a resilient client uses all three.
