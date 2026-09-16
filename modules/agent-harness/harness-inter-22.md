---
id: harness-inter-22
title: Record each tool call's output — or you can never reproduce the run because the live tools have moved on
topic: agent-harness
level: intermediate
status: ready
time: 17 min
summary: An agent run that went wrong is a bug report you cannot reopen, because tools are not pure functions of their arguments — a search returns different results tomorrow, a clock a different time, an API different data, a write leaves a side effect you don't want to repeat. Re-running the agent live does not reproduce the original run: the tools have moved on, the inputs the agent saw no longer exist, and the failure vanishes or mutates. Recording fixes it: capture every tool call and its exact output into a transcript as the run executes, then replay by feeding each call's recorded output back to the agent instead of invoking the live tool. On a fixture where get_time returned 5 and double(3) returned 6, replay returns both recorded values exactly, while a live re-run at the current clock of 9 returns 9 for get_time (diverged) and 6 for double — the pure tool reproduces either way, but only replay reproduces the clock.
eli5: If you record a magic trick on video, you can watch the exact same trick again and again to spot how it's done. If instead you just ask the magician to redo it, they'll do it a little differently each time and the moment you wanted to catch is gone. An agent's tools are like the magician — they answer differently each time — so to study a run that went wrong, you replay the recording, not ask the tools to do it again.
---

## Why this module

Debugging an agent run means re-watching the exact sequence it took, but the tools it called answer differently every time, so running it again gives you a different run and the bug you were chasing is gone.

A failed agent run is the thing you most want to reproduce and the thing you cannot, because the agent's behavior depends on what its tools returned, and tools are not pure functions of their arguments. Call a search again and it returns today's results; call a clock and it returns now, not then; call an API and the data has changed; call a random function and you get a different draw. Even a tool that only reads state reads a state that has moved on. So re-running the agent live does not replay the original run — it produces a new one, on new inputs, following a possibly different path to a possibly different outcome. The failure you were investigating may not even occur, and if it does you cannot be sure it is the same failure. You are trying to debug a run you can no longer observe.

**Tools are not pure functions of their arguments, so re-running an agent live does not reproduce the original run — the tools return new outputs and the agent takes a new path, and the original failure vanishes or mutates.**

Recording makes the run reproducible. As the original run executes, capture every tool call together with the exact output the tool returned at that moment into a transcript. To reproduce the run, replay it: feed each tool call's recorded output back to the agent instead of invoking the live tool. The agent now sees precisely the inputs it saw the first time, follows the same path, and reaches the same failure — deterministically, offline, with no live calls and no side effects re-triggered. This module records two tool calls and shows replay reproduce both while a live re-run diverges on the non-deterministic one.

## Concepts

**A non-deterministic tool** returns a different output for the same arguments over time — a clock, a search, an API, a random draw, or any read of changing state. Its output is a function of the world, not just the arguments.

**A pure tool** returns the same output for the same arguments forever — arithmetic, a formatter, a deterministic transform. It reproduces on a live re-run without any help.

**A recording** is a transcript of the original run: every tool call paired with the exact output it returned at that moment.

```python filename=modules/agent-harness/code/harness-inter-22/replay.py:52-54 COMPLETE
def replay(step):
    """Replay: return the tool call's RECORDED output, without invoking the live tool."""
    return step["output"]
```

**Replay** feeds recorded outputs back to the agent instead of invoking the live tools, so the agent sees the original inputs and follows the original path — deterministically, offline, with no side effects.

**The recording is what makes non-deterministic tools reproducible.** Pure tools would replay correctly anyway; the transcript's whole value is capturing the outputs that a live re-run could never recreate.

**Reproducing an agent run requires replaying recorded tool outputs, not re-invoking the tools, because the tools' outputs depend on a world that has changed since the run you are trying to reproduce.**

<svg role="img" aria-label="Replay feeds recorded outputs from the transcript to the agent; a live re-run calls the tools against the changed world" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">two ways to feed the agent its inputs</text>
  <rect x="15" y="26" width="50" height="18" fill="var(--s1)"/><text x="22" y="38" fill="var(--panel)" font-size="7">agent</text>
  <text x="8" y="60" fill="var(--s1)" font-size="8">replay</text>
  <line x1="65" y1="35" x2="120" y2="35" stroke="var(--s1)" stroke-width="1.5"/><polygon points="120,35 114,32 114,38" fill="var(--s1)"/>
  <rect x="122" y="27" width="70" height="16" fill="var(--s1)"/><text x="128" y="39" fill="var(--panel)" font-size="7">recording (fixed)</text>
  <rect x="15" y="66" width="50" height="18" fill="var(--s2)"/><text x="22" y="78" fill="var(--panel)" font-size="7">agent</text>
  <text x="8" y="100" fill="var(--s2)" font-size="8">live</text>
  <line x1="65" y1="75" x2="120" y2="75" stroke="var(--s2)" stroke-width="1.5"/><polygon points="120,75 114,72 114,78" fill="var(--s2)"/>
  <rect x="122" y="67" width="90" height="16" fill="var(--s2)"/><text x="128" y="79" fill="var(--panel)" font-size="7">live tools (world moved on)</text>
  <text x="15" y="104" fill="var(--muted)" font-size="8">replay's inputs are frozen in the transcript; live's inputs are whatever the world says now</text>
</svg>
^ Replay draws the agent's inputs from the frozen recording, so the run is identical; a live re-run draws them from tools whose world has changed, so the run diverges.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/harness-inter-22/replay.py

The fixture is a recording of two tool calls plus the current clock for a live re-run.

```json filename=modules/agent-harness/code/harness-inter-22/replay.json:1-9 COMPLETE
{
  "_meta": "A recorded agent run plus the current world for a live re-run. recording is the original run: each step is a tool call (tool + arg) and the output that tool returned AT THE TIME. get_time is a non-deterministic tool -- it returns the world's clock, which changes between runs. double is a pure tool -- it returns 2*arg, the same forever. recorded_time is the clock value when the run was first recorded; current_time is the clock now, later, when someone tries to reproduce the run. Replaying from the recording returns the recorded outputs, so the run reproduces exactly. Re-running live reads the CURRENT world, so get_time returns current_time instead of recorded_time and the run diverges -- the bug you were chasing no longer reproduces.",
  "recorded_time": 5,
  "current_time": 9,
  "recording": [
    {"tool": "get_time", "arg": 0, "output": 5},
    {"tool": "double", "arg": 3, "output": 6}
  ]
}
```

A live call reads the current world (which may have changed); a replay reads the recording.

```python filename=modules/agent-harness/code/harness-inter-22/replay.py:43-49 COMPLETE
def live(tool, arg, world_time):
    """Invoke the tool against the CURRENT world. get_time is non-deterministic; double is pure."""
    if tool == "get_time":
        return world_time
    if tool == "double":
        return 2 * arg
    raise ValueError(tool)
```

Run `--run` to compare recorded, replayed, and live outputs.

```text filename=--run
RUN — recorded output vs replayed vs live re-run (clock now 9)
--------------------------------------------------------------
  tool       arg   recorded   replayed   live re-run
  get_time   0     5          5          9
  double     3     6          6          6
--------------------------------------------------------------
  replay matches recorded exactly; the live re-run's clock has moved on.
```

The recording says get_time returned 5 and double(3) returned 6 during the original run. Replayed, both return their recorded values — 5 and 6 — so the agent sees exactly what it saw before. Re-run live at the current clock of 9, get_time returns 9: the clock moved on between the original run and now, so the live re-run feeds the agent a different input, and from here its path can diverge from the original. double(3) still returns 6 live, because it is pure. The recording reproduced the run; the live re-run reproduced only the half of it that never needed reproducing.

<svg role="img" aria-label="get_time recorded 5, replays 5, but re-runs live as 9; double recorded 6, replays 6, re-runs live as 6" viewBox="0 0 300 110" width="300" height="110">
  <text x="10" y="12" fill="var(--muted)" font-size="8">output: recorded / replayed / live re-run</text>
  <text x="8" y="34" fill="var(--muted)" font-size="8">get_time</text>
  <rect x="70" y="24" width="30" height="14" fill="var(--s1)"/><text x="78" y="35" fill="var(--panel)" font-size="8">5</text>
  <rect x="105" y="24" width="30" height="14" fill="var(--s1)"/><text x="113" y="35" fill="var(--panel)" font-size="8">5</text>
  <rect x="140" y="24" width="30" height="14" fill="var(--s2)"/><text x="148" y="35" fill="var(--panel)" font-size="8">9</text>
  <text x="176" y="35" fill="var(--s2)" font-size="7">live diverged</text>
  <text x="8" y="66" fill="var(--muted)" font-size="8">double</text>
  <rect x="70" y="56" width="30" height="14" fill="var(--s1)"/><text x="78" y="67" fill="var(--panel)" font-size="8">6</text>
  <rect x="105" y="56" width="30" height="14" fill="var(--s1)"/><text x="113" y="67" fill="var(--panel)" font-size="8">6</text>
  <rect x="140" y="56" width="30" height="14" fill="var(--s1)"/><text x="148" y="67" fill="var(--panel)" font-size="8">6</text>
  <text x="176" y="67" fill="var(--muted)" font-size="7">pure — same</text>
  <text x="70" y="90" fill="var(--muted)" font-size="7">recorded</text><text x="105" y="90" fill="var(--muted)" font-size="7">replay</text><text x="140" y="90" fill="var(--muted)" font-size="7">live</text>
  <text x="30" y="104" fill="var(--muted)" font-size="8">replay matches recorded everywhere; live matches only the pure tool</text>
</svg>
^ Replay's column equals the recorded column for both tools, while the live column matches only for the pure double — get_time's live value has moved to 9.

## Build

Which tools actually need the recording? Run `--diverge`.

```text filename=--diverge
DIVERGE — which tools reproduce live, and which need the recording
--------------------------------------------------------------
  get_time   recorded 5, live 9  ->  NON-deterministic -- needs the recording
  double     recorded 6, live 6  ->  pure -- reproduces live
--------------------------------------------------------------
  the recording is what makes the non-deterministic tools reproducible.
```

double reproduces on a live re-run because it is a pure function of its argument — the recording is redundant for it. get_time does not: its output depends on the world clock, which is now 9 instead of 5, so only the recording can give the agent back the 5 it originally saw. This is the whole value proposition of recording stated precisely: it does nothing for the deterministic tools and everything for the non-deterministic ones, and since a real agent run is full of the latter — searches, API reads, timestamps, model calls at temperature — the recording is the only way to make the run reproducible at all. It is also what lets you replay a run that had side effects (a write, a payment) without performing them again, because replay never calls the tool.

<svg role="img" aria-label="double reproduces live so needs no recording; get_time diverges live so the recording is required" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">does a live re-run reproduce the recorded output?</text>
  <text x="8" y="36" fill="var(--s1)" font-size="8">double (pure)</text>
  <rect x="110" y="26" width="60" height="16" fill="var(--s1)"/><text x="116" y="38" fill="var(--panel)" font-size="8">yes — live is enough</text>
  <text x="8" y="66" fill="var(--s2)" font-size="8">get_time</text>
  <rect x="110" y="56" width="120" height="16" fill="var(--s2)"/><text x="116" y="68" fill="var(--panel)" font-size="8">no — recording required</text>
  <text x="8" y="92" fill="var(--muted)" font-size="8">a real run is mostly non-deterministic tools, so recording is what makes it replayable</text>
</svg>
^ The pure tool reproduces live and needs no recording; the non-deterministic tool can only be reproduced from the transcript, and real runs are dominated by the latter.

## Definition of done

The self-test pins it: replay reproduces every recorded output, a live re-run diverges, the non-deterministic tool diverges live while the pure one does not, and replay reproduces the non-deterministic tool where live cannot.

```python filename=modules/agent-harness/code/harness-inter-22/replay.py:88-103 COMPLETE
    replay_reproduces_all = all(replay(step) == step["output"] for step in rec)
    print("  replay reproduces every recorded output = %s" % replay_reproduces_all)

    live_diverges = any(live(step["tool"], step["arg"], now) != step["output"] for step in rec)
    print("  a live re-run diverges on at least one tool = %s" % live_diverges)

    stateful = next(s for s in rec if s["tool"] == "get_time")
    stateful_diverges_live = live(stateful["tool"], stateful["arg"], now) != stateful["output"]
    print("  the non-deterministic tool diverges live = %s (recorded %d, live %d)" % (stateful_diverges_live, stateful["output"], live(stateful["tool"], stateful["arg"], now)))

    pure = next(s for s in rec if s["tool"] == "double")
    pure_same_live = live(pure["tool"], pure["arg"], now) == pure["output"]
    print("  the pure tool reproduces even live = %s (%d)" % (pure_same_live, pure["output"]))

    replay_reproduces_stateful = replay(stateful) == stateful["output"]
    print("  replay reproduces the non-deterministic tool where live cannot = %s (%d)" % (replay_reproduces_stateful, replay(stateful)))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — replay reproduces every recorded output; a live re-run diverges on the non-deterministic tool
------------------------------------------------------------------------------------------------------------
  replay reproduces every recorded output = True
  a live re-run diverges on at least one tool = True
  the non-deterministic tool diverges live = True (recorded 5, live 9)
  the pure tool reproduces even live = True (6)
  replay reproduces the non-deterministic tool where live cannot = True (5)
------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  replay_reproduces_all=True  live_diverges=True  stateful_diverges_live=True  pure_same_live=True  replay_reproduces_stateful=True
```

**Done means the reproducibility gap is proven: replay returns the recorded 5 and 6 exactly, while a live re-run returns 9 for get_time (diverged from 5) and 6 for double — so only the recording reproduces the non-deterministic tool, which is what a live re-run can never recreate.**

## Boss fight

Replay reproduced the run by returning recorded outputs. Predict what makes a recording go stale even for replay, and what you must capture besides tool outputs. It is tempting to think a recording is a perfect, permanent snapshot.

A recording replays faithfully only as long as the agent's own logic is unchanged. Replay works by feeding recorded outputs back in the order the agent requests them — but if you change the agent's code or prompt and then replay, the agent may request a tool call the recording does not have, or request them in a different order, and the replay desynchronizes. So a recording reproduces a run against the code that produced it; it is a regression fixture for that version, not an eternal one. Good replay systems detect the mismatch (the agent asked for a call not in the transcript) and fail loudly rather than silently feeding the wrong recorded output, and they key recordings to the code version so you know which recording matches which agent. The recording captures the world's non-determinism, not the agent's — change the agent and you need a new recording.

The subtler point is what "the output" must include. Replaying a tool's return value is not enough if the agent also branches on out-of-band signals: an exception a tool raised, a timeout, a latency it measured, a streaming order, the wall-clock time between calls. To replay faithfully you record whatever the agent can observe and branch on — errors and timings included — not just the happy-path return value, or the replayed run takes a different branch at the first thing you failed to capture. And you must record deterministically enough to be useful without recording so much that the transcript is unwieldy or leaks secrets. The discipline is the same one behind seeding a random generator and pinning a dependency: identify every source of non-determinism the run depends on, and capture or control all of them — a replay is only as reproducible as the least-captured thing the agent looked at.

```python filename=modules/agent-harness/code/harness-inter-22/replay.py:74-78 COMPLETE
    for step in rec:
        live_out = live(step["tool"], step["arg"], now)
        reproduces_live = live_out == step["output"]
        note = "pure -- reproduces live" if reproduces_live else "NON-deterministic -- needs the recording"
        print("  %-9s  recorded %d, live %d  ->  %s" % (step["tool"], step["output"], live_out, note))
```

**Record every tool call's exact output as a run executes and replay by feeding those outputs back instead of re-invoking the tools, because non-deterministic tools have moved on and a live re-run reproduces a different run — but a recording matches only the agent version that made it, so key it to the code, capture everything the agent can branch on (errors, timings, order), and fail loudly when replay desynchronizes.**

## External resources

VCR-style record/replay libraries for HTTP (for example VCR, Betamax, or Polly.js) — the same pattern for API calls, recording responses into cassettes and replaying them in tests, with the cassette-staleness and matching concerns spelled out.

Writing on deterministic simulation testing and record/replay debugging (for example FoundationDB's simulation approach, or `rr` for native programs) — the general discipline of capturing or controlling every source of non-determinism so a run can be replayed exactly.

The companion "a retried tool call must be idempotent" and "seed the random generator" modules — idempotency lets replay re-run effectful tools safely, and seeding is the same reproducibility principle applied to randomness rather than tool outputs.
