---
id: ship-inter-07
title: Exponential backoff needs jitter — or synchronized retries become a thundering herd
topic: ship-and-operate
level: intermediate
status: ready
time: 5-8h
summary: When a dependency goes down the whole fleet fails at nearly the same instant, and if every client uses the same backoff schedule — wait base, then 2·base, then 4·base — they all retry at the same instants in lockstep, so the moment the dependency recovers it is hit by the entire fleet at once, knocked flat, and the synchronized herd re-forms on the next backoff step. On the fixture, fixed exponential backoff peaks at 12 simultaneous retries — the whole fleet — against a server that can serve 4 per slot, wastes 24 attempts, and does not finish clearing the fleet until slot 56; adding jitter (retry at a random time in [1, base·2^attempt] instead of exactly base·2^attempt) scatters the retries so the peak drops to 3, under the capacity of 4, every client is served on its first retry for 12 attempts total, and the fleet clears by slot 7. Same average delay, same exponential growth — the only change is randomizing within the window, and it turns a self-perpetuating retry storm into a recovery that sticks.
eli5: Picture a crowd all pushing on the same door at the exact same second — it jams, nobody gets through, everyone steps back and pushes again together, and it jams again. Exponential backoff just tells them to wait longer between shoves, but they still shove in unison. Jitter tells each person to wait a slightly different random amount, so they arrive at the door a few at a time and everyone gets through quickly. The waiting is the same on average; spreading it out is the whole trick.
---

## Why this module

Retries are supposed to make a system resilient, and exponential backoff is the standard way to do them: after a failure wait a base delay, and double the wait on each subsequent failure, so a struggling dependency gets exponentially more breathing room. Every backoff tutorial teaches this, and it is necessary — but on its own it is not sufficient, and the way it fails is counterintuitive, because the thing that breaks it is that all your clients follow the advice correctly at the same time.

When a shared dependency goes down, it does not take out one client — it fails every in-flight request across the fleet at nearly the same instant. Now every client starts the same backoff schedule from the same moment: they all wait `base`, and retry together; they all wait `2·base`, and retry together; they all wait `4·base`, and retry together. Exponential backoff spread the retries out in time, but it spread them into synchronized spikes. The instant the dependency recovers, it is hit not by a trickle but by the entire fleet at once — more load than it could handle when healthy, let alone while recovering — so it falls over again, and the herd re-forms on the next backoff step. The retry mechanism has become a self-sustaining denial of service that the clients are inflicting on their own dependency.

The fix is jitter: instead of retrying at exactly `base·2^attempt`, each client retries at a random time in the interval `[1, base·2^attempt]`. The average delay and the exponential growth are unchanged — the window still doubles each attempt — but within each window the retries scatter instead of stacking on one instant, so the peak number of simultaneous retries drops from the whole fleet to a handful. This module simulates a fleet retrying a capacity-limited server, deterministically, and measures the one number that decides whether recovery holds: the peak simultaneous retries. Everything runs offline against a fleet fixture, stdlib Python 3 with a seeded PRNG, `$0.00`. The instinct to unlearn is that exponential backoff is the retry strategy. Exponential backoff without jitter is a synchronized retry strategy, and synchronized retries against a recovering dependency are the outage extending itself.

## Concepts

Named here so you can find them again; each is built below.

- **Exponential backoff** — wait base·2^attempt between retries; more room after each failure.
- **Lockstep** — all clients failing together retry at the same instants, in synchronized spikes.
- **Thundering herd** — the whole fleet hitting a recovering dependency at once, knocking it back down.
- **Jitter** — randomizing each backoff within its window so retries scatter instead of stacking.
- **Peak simultaneous retries** — the max load in any one slot; the number that decides if recovery holds.
- **Server capacity** — requests the dependency can serve per slot; a peak above it re-triggers the outage.

## Worked example

Source: a fleet of clients retrying a downed dependency — the situation every distributed system hits when a shared service restarts. The simulation stands in for real retry traffic; the server serves a fixed number of requests per time slot, and anything above that fails and backs off again, which is how a synchronized peak perpetuates itself.

Script and fixture: `modules/ship-and-operate/code/ship-inter-07/` — `jitter.py`, and `fleet.json`, 12 clients against a capacity-4 server. Every command runs from there.

### Backoff, with and without jitter

The whole difference between the two strategies is one branch in the backoff function.

```
# jitter.py:75-80 — COMPLETE (fixed backoff vs a random draw within the same window)
def backoff(base, attempt, jitter, rng):
    """Exponential backoff. Fixed = base*2^attempt; jittered = random in [1, base*2^attempt]."""
    window = base * (2 ** attempt)
    if jitter:
        return rng.randint(1, window)
    return window
```

Both compute the same `window` — `base·2^attempt`, doubling each attempt. Fixed backoff returns the window's end, so every client waiting the same window lands on the same slot. Jittered backoff returns a random point inside the window, so clients waiting the same window scatter across it. The average jittered delay is half the window, but the peak is what matters, and the peak is where they collide.

<svg viewBox="0 0 700 170" role="img" aria-label="Two timelines over the same backoff window. On top, fixed backoff: all client markers stacked on the single instant at the window's end. On the bottom, jittered backoff: the same markers spread evenly across the window. Both cover the same span; only the distribution within it differs.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the same backoff window, two distributions of retries within it</text>
    <text x="30" y="52" fill="var(--s2)" font-size="8">fixed</text>
    <line x1="90" y1="55" x2="620" y2="55" stroke="var(--line)"></line>
    <g fill="var(--s2)"><circle cx="612" cy="45" r="4"></circle><circle cx="612" cy="55" r="4"></circle><circle cx="612" cy="65" r="4"></circle><circle cx="620" cy="50" r="4"></circle><circle cx="620" cy="60" r="4"></circle><circle cx="604" cy="50" r="4"></circle><circle cx="604" cy="60" r="4"></circle></g>
    <text x="500" y="82" fill="var(--s2)" font-size="8">whole fleet on one instant → peak 12</text>
    <text x="30" y="122" fill="var(--s1)" font-size="8">jittered</text>
    <line x1="90" y1="125" x2="620" y2="125" stroke="var(--line)"></line>
    <g fill="var(--s1)"><circle cx="120" cy="125" r="4"></circle><circle cx="170" cy="125" r="4"></circle><circle cx="220" cy="125" r="4"></circle><circle cx="290" cy="125" r="4"></circle><circle cx="350" cy="125" r="4"></circle><circle cx="410" cy="125" r="4"></circle><circle cx="470" cy="125" r="4"></circle><circle cx="540" cy="125" r="4"></circle><circle cx="600" cy="125" r="4"></circle></g>
    <text x="300" y="152" fill="var(--s1)" font-size="8">scattered across the window → peak 3</text>
    <text x="90" y="98" fill="var(--muted)" font-size="7">|← same window (base·2^attempt) →|</text>
  </g>
</svg>
^ Fixed backoff piles the whole fleet on the window's final instant; jitter spreads the same clients across the same window. Identical span, identical average delay — only the peak changes, and the peak is the outage.

### The simulation

The fleet all fails at slot 0 and schedules a first retry — this is the moment the herd is born, every client entering the same backoff from the same instant:

```
# jitter.py:50-53 — COMPLETE (the whole fleet fails together and schedules its first retry)
    # every client fails at slot 0 (dependency down) and schedules its first retry
    pending = []            # (retry_slot, client_id, attempt)
    for cid in range(cfg["clients"]):
        pending.append((backoff(base, 0, jitter, rng), cid, 0))
```

Then each slot the server serves up to `capacity`, and the rest fail and back off again.

```
# jitter.py:58-72 — COMPLETE (serve `capacity` per slot; the overflow backs off again)
    while pending:
        slot = min(p[0] for p in pending)
        due = [p for p in pending if p[0] == slot]
        pending = [p for p in pending if p[0] != slot]
        load[slot] = len(due)
        # the server serves up to `capacity` this slot; the rest fail and back off again
        due.sort(key=lambda p: p[1])
        for i, (_, cid, attempt) in enumerate(due):
            attempts += 1
            if i < capacity:
                done += 1
            else:
                pending.append((slot + backoff(base, attempt + 1, jitter, rng), cid, attempt + 1))
    peak = max(load.values())
```

The one rule that makes this realistic is `if i < capacity`: a slot serves only `capacity` requests, and everything above that is a failed retry that must back off again. So a peak above capacity is not just a spike — it is wasted load that regenerates the herd. Run the fixed-backoff fleet:

```
# $ python3 jitter.py --no-jitter
#   retries landing per time slot:
#     slot   8: ############   12  <- OVER CAPACITY
#     slot  24: ########       8  <- OVER CAPACITY
#     slot  56: ####           4
#   peak simultaneous retries: 12   total attempts: 24   all served by slot 56
```

run: 2026-08-27 · deterministic; the fleet config is a fixture · 12 clients, seed 7 · `python3 jitter.py --no-jitter`

Every client retries at exactly slot 8 — all 12 at once, three times the server's capacity. The server serves 4; the other 8 fail and, in lockstep, all reschedule to slot 24; 4 more are served, 8... 4 fail and all land on slot 56. The peak is 12, the whole fleet; 24 attempts were made to serve 12 clients, so half were wasted; and because each synchronized wave pushes the survivors to an exponentially later slot, the fleet is not cleared until slot 56. The retries are spread in time and stacked in load — the worst of both.

<svg viewBox="0 0 700 200" role="img" aria-label="Fixed backoff load over time. Three tall spikes at slots 8, 24, and 56 of heights 12, 8, and 4, all at the same horizontal position class, each above a dashed capacity line at 4. The spikes are synchronized — the whole fleet lands on one slot each wave.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">fixed backoff: synchronized spikes, each far above capacity</text>
    <line x1="50" y1="170" x2="660" y2="170" stroke="var(--line)"></line>
    <line x1="50" y1="130" x2="660" y2="130" stroke="var(--s2)" stroke-dasharray="4 3"></line><text x="664" y="133" fill="var(--s2)" font-size="7">capacity 4</text>
    <rect x="120" y="50" width="40" height="120" fill="var(--s2)"></rect><text x="140" y="44" text-anchor="middle" fill="var(--s2)" font-size="8">12</text><text x="140" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">slot 8</text>
    <rect x="330" y="90" width="40" height="80" fill="var(--s2)"></rect><text x="350" y="84" text-anchor="middle" fill="var(--s2)" font-size="8">8</text><text x="350" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">slot 24</text>
    <rect x="540" y="130" width="40" height="40" fill="var(--muted)"></rect><text x="560" y="124" text-anchor="middle" fill="var(--muted)" font-size="8">4</text><text x="560" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">slot 56</text>
    <text x="120" y="120" fill="var(--panel)" font-size="7"> </text>
  </g>
</svg>
^ Every wave lands the entire remaining fleet on a single slot, three times over capacity, and the survivors bunch onto an exponentially later slot each time — so recovery drags to slot 56 while still overloading the server every wave.

### The same fleet, with jitter

Now the identical fleet, with each backoff randomized within its window:

```
# $ python3 jitter.py --jitter
#   retries landing per time slot:
#     slot   1: ###            3
#     slot   2: ###            3
#     slot   3: #              1
#     slot   4: #              1
#     slot   6: ##             2
#     slot   7: ##             2
#   peak simultaneous retries: 3   total attempts: 12   all served by slot 7
```

run: 2026-08-27 · deterministic · `python3 jitter.py --jitter`

The 12 clients scatter across slots 1 through 7, at most 3 in any one slot — under the server's capacity of 4. So every retry is served on its first try: 12 attempts for 12 clients, zero waste, and the whole fleet cleared by slot 7. Same exponential backoff, same clients, same average delay; randomizing where in the window each retry lands turned a peak of 12 into a peak of 3, and a slot-56 recovery into a slot-7 one.

<svg viewBox="0 0 700 200" role="img" aria-label="Jittered backoff load over time. Short bars spread across slots 1 through 7 of heights 3, 3, 1, 1, 0, 2, 2, all at or below the dashed capacity line at 4. The load is scattered and stays under capacity.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">jittered backoff: retries scattered, peak stays under capacity</text>
    <line x1="50" y1="170" x2="660" y2="170" stroke="var(--line)"></line>
    <line x1="50" y1="90" x2="660" y2="90" stroke="var(--s2)" stroke-dasharray="4 3"></line><text x="664" y="93" fill="var(--s2)" font-size="7">capacity 4</text>
    <g fill="var(--s1)">
      <rect x="90" y="110" width="50" height="60"></rect><rect x="170" y="110" width="50" height="60"></rect><rect x="250" y="150" width="50" height="20"></rect><rect x="330" y="150" width="50" height="20"></rect><rect x="490" y="130" width="50" height="40"></rect><rect x="570" y="130" width="50" height="40"></rect>
    </g>
    <text x="115" y="104" text-anchor="middle" fill="var(--s1)" font-size="8">3</text><text x="195" y="104" text-anchor="middle" fill="var(--s1)" font-size="8">3</text><text x="275" y="144" text-anchor="middle" fill="var(--s1)" font-size="8">1</text><text x="355" y="144" text-anchor="middle" fill="var(--s1)" font-size="8">1</text><text x="515" y="124" text-anchor="middle" fill="var(--s1)" font-size="8">2</text><text x="595" y="124" text-anchor="middle" fill="var(--s1)" font-size="8">2</text>
    <text x="115" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">1</text><text x="195" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">2</text><text x="275" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">3</text><text x="355" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">4</text><text x="515" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">6</text><text x="595" y="186" text-anchor="middle" fill="var(--muted)" font-size="7">7</text>
  </g>
</svg>
^ The same fleet, spread across seven slots at no more than 3 per slot — every bar under the capacity line, so every client is served on its first retry and the fleet clears by slot 7 instead of 56.

**Exponential backoff spreads retries in time but leaves the whole fleet synchronized on the same instants, so a recovering dependency is hit by a peak equal to the entire fleet and knocked back down; jitter — a random delay within the same backoff window — scatters the retries so the peak drops below capacity, turning a self-perpetuating retry storm into a recovery that holds, with no change to the average delay.**

### The self-test

The `--check` mode plants the bug — fixed backoff — and proves the storm: the peak equals the whole fleet and exceeds capacity, while jitter cuts the peak below capacity and wastes fewer attempts.

```
# $ python3 jitter.py --check
#   no-jitter peak equals the whole fleet (a thundering herd) = True (12 of 12)
#   no-jitter peak exceeds server capacity = True (12 > 4)
#   jitter cuts the peak = True (3 vs 12)
#   jitter peak stays within capacity = True (3 <= 4)
#   jitter wastes fewer attempts = True (12 vs 24)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 jitter.py --check`

The `overloads` and `within_cap` lines are the pair that matters operationally: fixed backoff's peak of 12 is triple the capacity of 4, so it re-triggers the outage every wave, while jitter's peak of 3 fits under 4, so the recovery sticks. The `fewer_attempts` line is the efficiency cost — 24 attempts versus 12 — every wasted attempt being a synchronized retry that the server had to reject and the client had to repeat.

```
# jitter.py:106-111 — COMPLETE (the two capacity assertions: herd equals the fleet, and it overloads)
    herd = noj["peak"] == cfg["clients"]
    print("  no-jitter peak equals the whole fleet (a thundering herd) = %s (%d of %d)"
          % (herd, noj["peak"], cfg["clients"]))

    overloads = noj["peak"] > cfg["capacity"]
    print("  no-jitter peak exceeds server capacity = %s (%d > %d)" % (overloads, noj["peak"], cfg["capacity"]))
```

### The running tally

| metric | fixed backoff | jittered backoff |
|---|---|---|
| peak simultaneous retries | 12 (whole fleet) | 3 |
| peak vs capacity (4) | 3× over — re-triggers outage | under — recovery holds |
| total attempts (for 12 clients) | 24 (12 wasted) | 12 (none wasted) |
| fleet cleared by slot | 56 | 7 |

Read the peak row against the capacity row: the whole failure mode is there. Fixed backoff's peak is triple the server's capacity, so each wave knocks the recovering server back down and the survivors bunch onto an exponentially later slot — which is why the "spread out in time" backoff still takes until slot 56. Jitter's peak fits under capacity, so the server clears everyone quickly and the retries never wasted a cycle. The average per-client delay is the same under both; jitter only changed the variance, and the variance was the whole problem.

### What we did not settle

This is the core jitter fix; the family is larger. The scheme here is "full jitter" — uniform over the whole window — which minimizes the peak; "equal jitter" (half the window plus a random half) and "decorrelated jitter" trade a little peak reduction for a slightly higher floor delay, and the right choice depends on how tight your latency budget is. Jitter composes with the other ship modules: a circuit breaker (`ship-inter-04`) stops retrying a dependency that is down at all, and a token bucket (`ship-inter-03`) caps a single client's rate, but neither de-synchronizes the fleet — only jitter does that, and you want all three. The capacity model here is a hard per-slot cap; a real server degrades more gradually, which makes the synchronized peak's damage worse, not better. And the seed makes one run reproducible; over many outages you would report the peak's distribution, not a single number. The invariant: never retry on a fixed schedule shared across a fleet — always randomize within the backoff window.

## Build

The build in one paragraph: on each retry, compute the exponential backoff window base·2^attempt as usual, then wait a random time drawn uniformly from within that window rather than the window's end, so a fleet that failed together scatters its retries instead of stacking them on one instant; keep the average delay and the exponential growth, change only the variance. Confirm on a simulated fleet against a capacity-limited server that fixed backoff peaks at the whole fleet and exceeds capacity while jitter's peak stays under it. Combine jitter with a circuit breaker and a per-client rate limit, pick a jitter variant to fit your latency floor, and report the peak's distribution across many outages, not one run.

We opened on the storm. The number that proves the fix is the peak simultaneous retries under each strategy:

```
# modules/ship-and-operate/code/ship-inter-07/ — COMPLETE, run from that directory
$ python3 jitter.py --check
  no-jitter peak equals the whole fleet (a thundering herd) = True (12 of 12)
  jitter cuts the peak = True (3 vs 12)
```

Now build your own. Take a real fleet size and a dependency with a known per-slot capacity below it, and simulate a recovery both ways. Your number to beat is not the average delay — that is identical; it is **the peak simultaneous retries, fixed versus jittered** — fixed should equal your fleet and blow past capacity, jitter should fall under it. Confirm the wasted-attempt count drops too. Bring back both peaks. Good luck.

## Definition of done

- [ ] Exponential backoff computing base·2^attempt per retry
- [ ] A jitter switch: fixed returns the window, jittered returns a uniform draw within it
- [ ] A fleet simulation against a server with a per-slot capacity, overflow backing off again
- [ ] Confirmation fixed backoff peaks at the whole fleet and exceeds capacity
- [ ] Confirmation jitter cuts the peak below capacity
- [ ] Confirmation jitter makes fewer total attempts (less wasted load)
- [ ] `python3 jitter.py --check` printing SELF-TEST PASS: herd, overloads, jitter_lower, within_cap, fewer_attempts
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does exponential backoff alone still produce a thundering herd? What synchronizes the fleet?
2. What exactly does jitter change, and what does it deliberately leave unchanged?
3. Fixed backoff's peak was 12 against capacity 4. Trace why that peak re-triggers the outage and drags recovery to slot 56.
4. Jitter served all 12 clients in 12 attempts; fixed backoff took 24. Where did the extra 12 attempts come from?
5. Your own fleet was simulated both ways. What was the peak under each, and did jitter's peak fit under capacity?

## External resources

- AWS Architecture Blog, *Exponential Backoff And Jitter* — my summary: the canonical write-up that measures full, equal, and decorrelated jitter against fixed backoff and shows jitter both reduces load and completes work faster; read it for the variant comparison this module simplifies.
- Google SRE Book, chapter on handling overload and cascading failures — my summary: how synchronized retries and retry amplification cause outages to persist, and the client-side controls that prevent them; read it for the system-level picture jitter sits inside.
- This hub, *ship-inter-03* (token bucket) and *ship-inter-04* (circuit breaker) — read them for the per-client rate cap and the stop-retrying-a-dead-service control that pair with jitter; you want all three, not one.
