---
id: faildetect-inter-01
title: Score a missing heartbeat against the node's own timing variance — or one fixed timeout is wrong for every node
topic: orchestration-and-governance
level: intermediate
status: ready
time: 16 min
summary: A failure detector declares a node dead when its heartbeat is silent too long, and the obvious rule is a fixed timeout — but that one number is applied to every node, and nodes do not beat alike. A node on a quiet path is metronome-regular; one behind a busy queue is bursty, its gaps swinging wildly while perfectly alive. Set the timeout tight enough to notice the regular node stall and it trips constantly on the bursty node's normal jitter; set it loose enough to tolerate the bursty node and it is blind to the regular node dying. No single timeout serves both. An adaptive detector measures the gap in units of each node's own variability — roughly (gap − mean) / stddev — so the threshold becomes a suspicion level that means the same on every node. On a fixture where both nodes show the identical 1.6 s gap, the regular node (which truly failed) scores 53.7σ while the bursty node (alive) scores 1.9σ; a 1.5 s fixed timeout false-positives on the bursty node, a 2.0 s one misses the failed node, and the adaptive detector is correct on both with one threshold.
eli5: To tell if a friend is in trouble because they went quiet, you'd use their normal habits, not a stopwatch. A friend who texts like clockwork every minute going five minutes silent is alarming; a friend who texts erratically, sometimes every ten minutes, going five minutes silent is nothing. A single rule like "worry after three minutes" is wrong for both — it panics over the erratic friend and misses the reliable one. Judge each person's silence against how they normally are, and one rule ("this is way more silent than usual for them") fits everyone.
---

## Why this module

Failure detection is a judgment about whether a silence is abnormal, and abnormal is defined by the node's own rhythm — so a detector that compares every node's silence to one fixed duration is measuring against a baseline that fits almost none of them.

A heartbeat detector waits for periodic pings and declares a node dead when they stop. The tempting rule is a timeout: no heartbeat for T seconds means dead. The problem is that T is one number and a fleet is many nodes with many timing profiles. A node on an idle path emits heartbeats like a metronome, gaps tightly clustered around one second. A node behind a saturated queue or a jittery network link is alive but bursty, its gaps swinging from half a second to two seconds as load ebbs and flows. A timeout tight enough to catch the metronome node stalling — say 1.5 seconds — is well inside the bursty node's normal range, so it fires on healthy jitter and evicts a live node, triggering a pointless failover. A timeout loose enough to leave the bursty node alone — say 2.5 seconds — is longer than the metronome node's fatal silence, so a real death goes unnoticed for far too long. The two requirements pull in opposite directions and no single T satisfies both.

**A fixed heartbeat timeout is one duration judged against every node, but "too long a silence" depends on the node's own beat variance — so any single timeout either false-positives on bursty-but-alive nodes or misses regular nodes that die within it.**

The adaptive detector escapes the dilemma by changing the unit. Instead of comparing the silence to a duration, compare it to the node's own history: track each node's recent heartbeat intervals, compute their mean and standard deviation, and score the current silence as how many standard deviations it sits above that mean. Now the threshold is a *suspicion level*, not a number of seconds, and it means the same thing everywhere — three sigma out is equally alarming on a regular node and a bursty one, even though those are very different numbers of seconds. The regular node's tiny variance makes a modest delay huge in sigma; the bursty node's large variance absorbs the same delay as routine. One suspicion threshold works fleet-wide because each node is judged against itself. This module scores the same silence on two nodes and shows the fixed timeout fail where the adaptive score succeeds.

## Concepts

**A node's baseline** is the mean and standard deviation of its recent heartbeat intervals — its own definition of a normal gap. A regular node has a small standard deviation; a bursty node a large one.

```python filename=modules/orchestration-and-governance/code/faildetect-inter-01/faildetect.py:46-48 COMPLETE
def baseline(intervals):
    """The node's own heartbeat mean and standard deviation -- what 'normal' means for this node."""
    return statistics.mean(intervals), statistics.pstdev(intervals)
```

**Suspicion** scores the current silence in units of that baseline: how many standard deviations the gap sits above the node's mean interval. It is dimensionless, so the same score means the same thing on any node.

```python filename=modules/orchestration-and-governance/code/faildetect-inter-01/faildetect.py:51-54 COMPLETE
def suspicion(gap, intervals):
    """How many standard deviations the current silence sits above the node's mean interval (a phi-like score)."""
    mean, sd = baseline(intervals)
    return (gap - mean) / sd if sd > 0 else float("inf")
```

**The threshold is a level, not a duration.** A fixed detector compares the gap to seconds; the adaptive detector compares the suspicion to a sigma count (the idea behind the phi-accrual detector, which reports a continuous log-probability instead of a hard sigma).

<svg role="img" aria-label="Node A's interval distribution is narrow and node B's is wide; the same 1.6s gap falls far in A's tail (many sigma) but within B's bulk (under one sigma)" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">interval distributions; the same 1.6s gap (dashed) on each</text>
  <line x1="20" y1="52" x2="200" y2="52" stroke="var(--grid)"/>
  <path d="M60 52 Q70 22 80 52" fill="none" stroke="var(--s1)" stroke-width="1.5"/><text x="52" y="64" fill="var(--s1)" font-size="7">A (regular)</text>
  <line x1="150" y1="24" x2="150" y2="58" stroke="var(--ink)" stroke-dasharray="3 2"/><text x="132" y="20" fill="var(--ink)" font-size="7">1.6s</text>
  <text x="120" y="40" fill="var(--muted)" font-size="7">53.7σ out →</text>
  <line x1="20" y1="98" x2="200" y2="98" stroke="var(--grid)"/>
  <path d="M40 98 Q70 60 100 98" fill="none" stroke="var(--s2)" stroke-width="1.5"/><text x="44" y="90" fill="var(--s2)" font-size="7">B (bursty)</text>
  <line x1="150" y1="70" x2="150" y2="104" stroke="var(--ink)" stroke-dasharray="3 2"/><text x="132" y="108" fill="var(--ink)" font-size="7">1.6s</text>
  <text x="156" y="80" fill="var(--muted)" font-size="7">1.9σ (within normal)</text>
</svg>
^ The same 1.6 s silence lands deep in the tail of regular node A's tight distribution (53.7σ, alarming) but inside the bulk of bursty node B's wide distribution (1.9σ, routine) — the sigma, not the seconds, carries the meaning.

**Judge a silence by how many standard deviations it is from the node's own mean, not by a fixed number of seconds — because the same duration is a death on a regular node and normal jitter on a bursty one, and only the variance tells them apart.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/orchestration-and-governance/code/faildetect-inter-01/faildetect.py

The fixture is two nodes with the same current gap: a regular node A that truly failed and a bursty node B that is alive.

```json filename=modules/orchestration-and-governance/code/faildetect-inter-01/faildetect.json:3-9 COMPLETE
  "nodes": {
    "A": {"intervals": [1.0, 0.98, 1.02, 1.0, 0.99, 1.01, 1.0, 1.0], "test_gap": 1.6, "truly_failed": true},
    "B": {"intervals": [1.0, 0.5, 1.5, 0.6, 1.4, 0.9, 1.1, 1.0], "test_gap": 1.6, "truly_failed": false}
  },
  "fixed_low": 1.5,
  "fixed_high": 2.0,
  "phi_threshold": 3.0
```

Run `--detect` to score the same gap on both nodes.

```text filename=--detect
DETECT — same 1.6s gap on two nodes; fixed timeouts vs an adaptive score
------------------------------------------------------------------------------
  node  mean  stddev  gap   fixed>1.5  fixed>2.0  suspicion(sigma)  adaptive>3  truly_failed
  A     1.00  0.011   1.6   True       False      53.7              True          True
  B     1.00  0.324   1.6   True       False      1.9               False         False
```

Both nodes have a mean interval of 1.00 s and both are currently 1.6 s silent — identical on every number a fixed timeout can see. The only difference is the standard deviation: 0.011 s for the metronome node A, 0.324 s for the bursty node B, a 30× spread in how much each normally wanders. That is exactly the information the fixed timeout throws away and the adaptive score keeps. In sigma, A's 1.6 s silence is 53.7 standard deviations above its mean — astronomically abnormal for a node that never varies — while B's identical 1.6 s is 1.9 sigma, well within a node that routinely swings that far. The adaptive column reads the truth off those scores: A dead (correct, it failed), B alive (correct, it is fine). The fixed columns cannot: at 1.5 s both are "dead" (a false positive on B), at 2.0 s both are "alive" (missing A). Same seconds, opposite realities, and only the variance-aware score sees it.

<svg role="img" aria-label="The same 1.6s gap scores 53.7 sigma on regular node A and 1.9 sigma on bursty node B; the adaptive threshold of 3 sigma separates them while the fixed timeouts do not" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">suspicion of the same 1.6s gap (σ); threshold = 3</text>
  <line x1="30" y1="70" x2="290" y2="70" stroke="var(--grid)"/>
  <line x1="70" y1="20" x2="70" y2="76" stroke="var(--ink)" stroke-dasharray="3 2"/><text x="52" y="18" fill="var(--muted)" font-size="7">3σ threshold</text>
  <rect x="30" y="30" width="8" height="12" fill="var(--s2)"/><text x="42" y="40" fill="var(--muted)" font-size="7">B: 1.9σ — alive ✓ (below)</text>
  <rect x="278" y="52" width="10" height="12" fill="var(--s1)"/><text x="150" y="62" fill="var(--muted)" font-size="7">A: 53.7σ — dead ✓ (far right)</text>
  <line x1="38" y1="36" x2="66" y2="36" stroke="var(--s2)"/><line x1="86" y1="58" x2="278" y2="58" stroke="var(--s1)"/>
  <text x="6" y="94" fill="var(--muted)" font-size="8">one 3σ line puts B on the alive side and A far on the dead side — the fixed timeouts can't</text>
</svg>
^ Scored in sigma, the same 1.6 s gap is 1.9σ on bursty B (below the 3σ line, alive) and 53.7σ on regular A (far past it, dead) — one adaptive threshold separates what no single fixed timeout can.

## Build

Why can no fixed timeout work? Run `--threshold`.

```text filename=--threshold
THRESHOLD — no single fixed timeout separates a fatal gap from a normal one
--------------------------------------------------------------
  node A (failed) gap = 1.6s   node B (alive) gap = 1.6s   -- identical
  fixed timeout 1.5s: A dead=True, B dead=True  (B is a false positive)
  fixed timeout 2.0s: A dead=False, B dead=False  (A is missed)
--------------------------------------------------------------
  a duration cannot tell the two apart because they ARE the same duration; only variance can.
```

This is the impossibility stated plainly. A fixed timeout is a single cutoff on the gap in seconds, and here the failed node and the healthy node present the *same* gap — 1.6 s both. Any cutoff below 1.6 marks both dead; any cutoff at or above 1.6 marks both alive. There is no value of T that calls A dead and B alive, because T only sees the duration and the durations are equal. The information that distinguishes them is not in the current gap at all; it is in the history — how much each node normally varies — which a scalar timeout has no way to consult. This is why large fleets that rely on fixed timeouts are forced into per-node tuning (a different T for every node, unmaintainable) or into picking a T that is wrong for the tails of the distribution (false positives on bursty nodes, slow detection on regular ones). The adaptive detector needs no per-node tuning because the per-node information is already in each node's variance.

<svg role="img" aria-label="On a duration axis both the failed gap and the healthy gap sit at 1.6s, so any fixed cutoff line puts them on the same side" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">gap duration (s) — both nodes at 1.6</text>
  <line x1="20" y1="50" x2="290" y2="50" stroke="var(--grid)"/>
  <g font-size="7" fill="var(--muted)"><text x="60" y="64">1.0</text><text x="150" y="64">1.6</text><text x="230" y="64">2.5</text></g>
  <circle cx="158" cy="50" r="4" fill="var(--s1)"/><text x="132" y="34" fill="var(--s1)" font-size="7">A failed 1.6</text>
  <circle cx="150" cy="50" r="4" fill="var(--s2)"/><text x="150" y="80" fill="var(--s2)" font-size="7">B alive 1.6</text>
  <line x1="120" y1="40" x2="120" y2="60" stroke="var(--muted)" stroke-dasharray="2 2"/><text x="96" y="30" fill="var(--muted)" font-size="6">T=1.5: both dead</text>
  <line x1="188" y1="40" x2="188" y2="60" stroke="var(--muted)" stroke-dasharray="2 2"/><text x="190" y="30" fill="var(--muted)" font-size="6">T=2.0: both alive</text>
  <text x="6" y="90" fill="var(--muted)" font-size="8">the two gaps coincide, so every fixed cutoff groups them together — no T separates them</text>
</svg>
^ On the duration axis the failed and healthy gaps sit at the same 1.6 s, so every fixed cutoff — 1.5 s, 2.0 s, anything — puts both on the same side; the durations are identical, so no timeout can tell them apart.

## Definition of done

The self-test pins the whole argument: the gaps are numerically identical, the same gap is many sigma for the regular node and under one for the bursty node, the tight timeout false-positives, the loose one misses, and the adaptive detector is correct on both.

```python filename=modules/orchestration-and-governance/code/faildetect-inter-01/faildetect.py:102-115 COMPLETE
    same_gap = a["test_gap"] == b["test_gap"]
    print("  both nodes show the identical numeric gap = %s (%.1fs)" % (same_gap, a["test_gap"]))

    regular_gap_extreme = suspicion(a["test_gap"], a["intervals"]) > phi
    print("  the gap is extreme in sigma for the regular node A = %s (%.1f sigma)" % (regular_gap_extreme, suspicion(a["test_gap"], a["intervals"])))

    bursty_gap_normal = suspicion(b["test_gap"], b["intervals"]) < phi
    print("  the same gap is within normal for the bursty node B = %s (%.1f sigma)" % (bursty_gap_normal, suspicion(b["test_gap"], b["intervals"])))

    fixed_low_false_positive = fixed_says_dead(b["test_gap"], lo) and not b["truly_failed"]
    print("  the tight fixed timeout false-positives on the healthy bursty node = %s" % fixed_low_false_positive)

    fixed_high_misses = not fixed_says_dead(a["test_gap"], hi) and a["truly_failed"]
    print("  the loose fixed timeout misses the failed regular node = %s" % fixed_high_misses)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the same gap is many sigma for the regular node and under one for the bursty node; adaptive gets both right
------------------------------------------------------------------------------------------------------------------------
  both nodes show the identical numeric gap = True (1.6s)
  the gap is extreme in sigma for the regular node A = True (53.7 sigma)
  the same gap is within normal for the bursty node B = True (1.9 sigma)
  the tight fixed timeout false-positives on the healthy bursty node = True
  the loose fixed timeout misses the failed regular node = True
  the adaptive detector is correct on both nodes with one threshold = True
```

**Done means the fixed-timeout dilemma and its adaptive fix are both proven: the failed regular node and the healthy bursty node show the identical 1.6 s gap, which is 53.7σ for the regular node (dead) and 1.9σ for the bursty one (alive), so the tight 1.5 s timeout false-positives on the healthy node, the loose 2.0 s timeout misses the failed one, and a single 3σ adaptive threshold is correct on both.**

## Boss fight

Predict the two ways the adaptive detector still goes wrong. It is tempting to think "score in sigma" removes every tuning decision.

The first trap is that the suspicion threshold trades false positives against detection speed exactly as the fixed timeout did — it has just moved the knob to a better place. A high sigma threshold (say 8σ) almost never false-positives but waits longer to accumulate that many sigma, so it detects real deaths more slowly; a low threshold (2σ) detects fast but fires on the occasional legitimate outlier. The phi-accrual detector makes this explicit by outputting a continuous suspicion that rises over time, letting each caller choose its own threshold for its own cost of a wrong decision — a load balancer that can cheaply reroute wants a twitchy low threshold, a leader-election that triggers an expensive reconfiguration wants a patient high one. So adaptive detection does not eliminate the speed-versus-accuracy trade; it makes it a single meaningful dial (suspicion level) instead of a per-node duration, and the dial still has to be set for the consequence of being wrong.

```python filename=modules/orchestration-and-governance/code/faildetect-inter-01/faildetect.py:62-64 COMPLETE
def adaptive_says_dead(gap, intervals, phi_threshold):
    """An adaptive detector: dead if the suspicion (sigma above the node's own mean) exceeds the threshold."""
    return suspicion(gap, intervals) > phi_threshold
```

The second trap is that the baseline is only as good as the history it is estimated from, and estimating variance is fragile. From a handful of intervals the standard deviation is noisy, so early in a node's life the sigma score swings wildly and can false-positive or miss until enough samples accumulate — a cold-start problem. Worse, the mean and variance drift: a node that legitimately slows down under sustained load has a rising true mean, and if the window that computes the baseline is too short it chases the new normal and never flags a genuine problem (it "adapts" to the failure), while too long a window is slow to accept a real regime change. And the whole method assumes the intervals are roughly stationary and unimodal; a node with bimodal timing (fast when idle, slow when batching) has a variance that describes neither mode, so a sigma score against the blended baseline is meaningless. Real detectors therefore bound the window, sometimes weight recent samples more, and can be fooled by correlated network partitions where many nodes go silent together for a shared reason that is not individual death. The adaptive detector is a large improvement, but its correctness rests on a well-estimated, stationary baseline, and both of those assumptions need guarding.

**Score a missing heartbeat in standard deviations of the node's own interval history, not against a fixed timeout, so one suspicion threshold works fleet-wide where no single duration can separate a regular node's fatal silence from a bursty node's normal jitter — but the threshold still trades detection speed against false positives (a real dial, set per the cost of being wrong), and the per-node baseline must be estimated from enough recent, roughly-stationary samples, or a cold start, a drifting mean, or bimodal timing makes the sigma score itself unreliable.**

## External resources

The phi-accrual failure detector paper (Hayashibara et al., "The φ Accrual Failure Detector") — the canonical adaptive detector that outputs a continuous suspicion level (a log-probability) from the heartbeat history, letting each application pick its own threshold.

Any distributed-systems reference on failure detectors (Chandra and Toueg's completeness/accuracy properties) and on the fundamental impossibility of a perfect detector in an asynchronous network — the theory of why detection is always a speed-versus-accuracy trade.

The companion "trip a circuit breaker after repeated failures" and "fence writes with a monotonic epoch" modules — the circuit breaker acts on failed requests rather than heartbeat timing, and fencing handles what happens after a node is (perhaps wrongly) declared dead and later returns, so the three cover detecting, reacting to, and recovering from a suspected failure.
