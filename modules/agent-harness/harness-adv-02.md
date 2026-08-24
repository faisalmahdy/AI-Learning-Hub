---
id: harness-adv-02
title: What should the agent build next? Reading the field's convergence against your own gaps
topic: agent-harness
level: advanced
status: ready
eli5: Seven different agent programs were studied. Some ideas show up in almost all of them, which is a strong hint they matter. But "everyone does it" is not the same as "we should build it next" — the second-most-common idea is one your own agent already has, so building it would be wasted work.
summary: Seven harness deep-dives distilled into one convergence table — hooks appear in six of seven, an OS sandbox in five, plan mode and progressive disclosure in four each, checkpoints in two. The trap is ranking what to build by that count alone, which puts an OS sandbox second even though Santara already runs a Landlock/seccomp jail; gate the ranking on Santara's own gaps instead and hooks lead a queue that never once tells you to build what you already have.
time: 10-14h
---

## Why this module

Five modules built this topic from nothing: the loop, its seams, a governed tool surface, a measured self-improvement ratchet, and a control chart for the live eval. Each one built a thing. This one builds a decision. The labs did nine deep-dive studies of other people's agent harnesses — Claude Code, Hermes, OpenClaw, NanoClaw, Codex, Cursor, OpenCode, and two comparison passes — and produced sixty-odd ranked lessons. `CURRICULUM.md`'s Track 2.6 is the seminar that turns that pile into something actionable: "distill the convergence list into hub modules — hooks, sandboxing, plan mode, checkpoints, progressive disclosure — each with a Santara implementation status." The deliverable is not another primitive. It is the answer to "of everything the field agrees on, what should our own agent build next, and in what order?"

The payoff of a survey is never any single system. It is the **convergence**: when harnesses of completely different shapes — a coding CLI, a Telegram assistant, an editor, a fork — independently land on the same primitive, that agreement is a signal no single team's taste can give you. But a signal is not an instruction, and this module is about the one step that quietly ruins the decision. The obvious move is to rank the primitives by how many harnesses converge on each and build from the top. That move is wrong, and it is wrong in a way that costs real weeks: the second-most-converged primitive in the whole dataset is one Santara already has, and building it again is pure waste. The fix is one idea — priority is not what the field agrees on, it is what the field agrees on **that you still lack** — and the whole module is making that idea mechanical and checkable.

This is the topic's second `advanced` module and its capstone, so it composes instead of introducing: it reuses the keep/reject discipline of the ratchet (harness-inter-03) and the "a number needs its denominator" instinct from the evals track, now aimed at a portfolio decision rather than a single skill. What it omits: no live agent, no scraping — the convergence table is a committed fixture distilled from the deep-dives, each row citing the exact file and line it came from, so the whole thing runs offline in well under a second and every number is traceable to a source you can open. Stdlib Python 3, `$0.00`, one long sitting.

By the end, one command reads the table and prints a build queue that never once tells you to build what you already have. Skipping ahead:

```
# modules/agent-harness/code/harness-adv-02/ — COMPLETE, run from that directory
$ python3 convergence.py --priority

BUILD QUEUE — convergence gated on Santara's gaps (the correct ranking)
--------------------------------------------------------------------------
  1. hooks                  x6/7  (Santara: MISSING)
  2. plan_mode              x4/7  (Santara: MISSING)
  3. progressive_disclosure x4/7  (Santara: partial)
  4. checkpoints            x2/7  (Santara: MISSING)
--------------------------------------------------------------------------
  dropped (already have): sandbox
```

run: 2026-08-22 · table is a sourced fixture; ranking is deterministic · 7 harnesses, 5 primitives · `python3 convergence.py --priority`

Hooks lead because they are both the most-agreed primitive in the entire series and a thing Santara does not have. Sandbox — the second-most-agreed — is not on the list at all, because Santara already runs one. This module is about the table those two facts come from, the ranking that gets it right, and the one-line trap that gets it exactly, expensively wrong.

## Concepts

Named here so you can find them again; each is built, and one is broken, below.

- **Convergence** — the count of independently-built harnesses that land on the same primitive; the survey's real signal.
- **The convergence table** — the distilled fixture: per primitive, its count, its dissenter, its source line, and Santara's status.
- **Santara status** — for each primitive, whether the labs' own agent has it: `missing`, `partial`, or `have`.
- **The build queue** — the ordered answer to "what next", derived from the table.
- **Gap-gated ranking** — rank by convergence, but only over primitives Santara lacks. #3.
- **Raw-count ranking** — rank by convergence alone. The planted bug.
- **The dissenter** — a harness that considered a converged primitive and refused it on purpose; the reason a high count is not unanimity.

## Worked example

Source: faisalmahdy/agent — `docs/harness-landscape.md` and the seven deep-dive files (`claude-code-deep-dive.md`, `codex-deep-dive.md`, `cursor-deep-dive.md`, `opencode-deep-dive.md`, and the Hermes/OpenClaw/NanoClaw studies), whose per-lesson convergence tallies this table distills. Every count below cites the file and line it was read from.

Script and fixture: `modules/agent-harness/code/harness-adv-02/` — `convergence.py`, and `convergence.json`, five primitives across seven harnesses. Every command runs from there. The one dial is the table: edit a Santara status or a count and the queue recomputes.

### Install the frame: convergence is triangulation, priority is triangulation minus your position

In my opinion the right way to think about "what does the field agree on" is triangulation, not voting. When three surveyors on three hilltops all sight the same distant peak, the point where their bearings cross is a real landmark — not because any one of them is authoritative, but because independent lines of sight do not agree by accident. That is exactly what a converged primitive is: hooks show up in a coding CLI, a Telegram bot, and an editor, and three sightlines from vantage points that different, all crossing at one idea, mean the idea is really there and not one team's fashion.

But here is the whole module in one sentence. A bearing is not a heading. Knowing where the peak is does not tell you which way to sail — that depends on where *you* are standing. Your course is the landmark's position **minus your own position**. The trap this module exists to kill is plotting a course from the bearings alone: you read that the field converges hard on an OS sandbox, you point the ship at it, and you sail toward an island you are already standing on. Priority is convergence minus what you have, and forgetting the subtraction is the most natural mistake in any "learn from the field" exercise.

<svg viewBox="0 0 700 250" role="img" aria-label="Three sightlines from three harnesses (a CLI, a bot, an editor) crossing at one point labelled hooks — convergence as triangulation. A separate short arrow shows that the course to sail is the landmark's position minus the viewer's own position.">
  <g font-family="var(--mono)" font-size="10">
    <text x="40" y="24" fill="var(--muted)">three independent harnesses, one crossing point = a real primitive</text>
    <circle cx="470" cy="90" r="7" fill="var(--acc)"></circle>
    <text x="484" y="86" fill="var(--acc-ink)">hooks</text>
    <text x="484" y="99" fill="var(--muted)" font-size="8">x6/7 — the crossing</text>
    <g stroke="var(--s1)" stroke-width="1.5">
      <line x1="70" y1="150" x2="470" y2="90"></line>
      <line x1="90" y1="210" x2="470" y2="90"></line>
      <line x1="220" y1="220" x2="470" y2="90"></line>
    </g>
    <g fill="var(--ink)" font-size="9">
      <circle cx="70" cy="150" r="4" fill="var(--ink)"></circle><text x="20" y="145">CLI</text>
      <circle cx="90" cy="210" r="4" fill="var(--ink)"></circle><text x="30" y="224">bot</text>
      <circle cx="220" cy="220" r="4" fill="var(--ink)"></circle><text x="196" y="236">editor</text>
    </g>
    <line x1="150" y1="120" x2="150" y2="120" stroke="var(--grid)"></line>
    <rect x="300" y="176" width="360" height="58" rx="6" fill="var(--panel)" stroke="var(--line)"></rect>
    <text x="316" y="196" fill="var(--ink)">course to sail  =  landmark position  −  your position</text>
    <text x="316" y="214" fill="var(--muted)" font-size="9">a bearing everyone agrees on is a real place;</text>
    <text x="316" y="228" fill="var(--muted)" font-size="9">it is still not a heading until you subtract where you already are.</text>
  </g>
</svg>
^ Convergence is triangulation: independent sightlines crossing at one primitive make it real. But the crossing point is a landmark, not a course — the heading is the landmark minus your own position, and skipping that subtraction is the bug below.

### Look at the data: five primitives, seven harnesses, the studies' own counts

Here is the whole table, distilled from the deep-dives. The count is `x N / 7` — how many of the seven studied harnesses the studies tally as landing on each primitive — and the last column is Santara's own status, read from each study's "Santara today" line.

```
# $ python3 convergence.py --table
#   hooks                  x6/7  [xxxxxx.]  Santara: MISSING
#       the most-confirmed extensibility move in the entire series (cursor-deep-dive.md:430)
#   sandbox                x5/7  [xxxxx..]  Santara: HAVE     dissent: opencode
#       all five studied systems converge on OS-enforced sandboxing (codex-deep-dive.md:469)
#   plan_mode              x4/7  [xxxx...]  Santara: MISSING
#       the most-confirmed workflow pattern after hooks (opencode-deep-dive.md:392)
#   progressive_disclosure x4/7  [xxxx...]  Santara: partial
#       highest cross-repo agreement of any lesson (claude-code-deep-dive.md:318)
#   checkpoints            x2/7  [xx.....]  Santara: MISSING
#       a trust net separate from git (cursor-deep-dive.md:450)
```

run: 2026-08-22 · counts are the deep-dives' tallies, each cited · 7 harnesses · `python3 convergence.py --table`

Read the counts as evidence strength, not as a to-do list. Hooks at six of seven is the strongest agreement in the whole series — the studies call it "the most-confirmed extensibility move," landing in a CLI (Claude Code), a security-hardened operator (Hermes), a plugin-based bot (OpenClaw), a container-per-agent runner (NanoClaw), a second coding CLI (Codex), and an editor (Cursor). When six systems that share almost no code and no goals all grow the same lifecycle-hook mechanism, that primitive is not a fashion; it is a fixed point. The bars fall off from there: an OS sandbox in five, plan mode and progressive disclosure in four each, and workspace checkpoints in only two — a coding-surface convenience that did not generalize.

<svg viewBox="0 0 700 220" role="img" aria-label="A bar chart of convergence counts: hooks 6 of 7, sandbox 5, plan_mode 4, progressive_disclosure 4, checkpoints 2. Bars are tagged with Santara's status: hooks missing, sandbox have, plan_mode missing, progressive_disclosure partial, checkpoints missing.">
  <g font-family="var(--mono)" font-size="10">
    <text x="150" y="22" fill="var(--muted)">convergence across seven harnesses, tagged with Santara's status</text>
    <g>
      <text x="16" y="52" fill="var(--ink)">hooks</text>
      <rect x="150" y="42" width="468" height="16" rx="3" fill="var(--s1)"></rect>
      <text x="626" y="55" fill="var(--muted)">x6 · MISSING</text>
      <text x="16" y="88" fill="var(--ink)">sandbox</text>
      <rect x="150" y="78" width="390" height="16" rx="3" fill="var(--muted)"></rect>
      <text x="548" y="91" fill="var(--muted)">x5 · HAVE</text>
      <text x="16" y="124" fill="var(--ink)">plan_mode</text>
      <rect x="150" y="114" width="312" height="16" rx="3" fill="var(--s1)"></rect>
      <text x="470" y="127" fill="var(--muted)">x4 · MISSING</text>
      <text x="16" y="160" fill="var(--ink)">prog._disclosure</text>
      <rect x="150" y="150" width="312" height="16" rx="3" fill="var(--s2)"></rect>
      <text x="470" y="163" fill="var(--muted)">x4 · partial</text>
      <text x="16" y="196" fill="var(--ink)">checkpoints</text>
      <rect x="150" y="186" width="156" height="16" rx="3" fill="var(--s1)"></rect>
      <text x="314" y="199" fill="var(--muted)">x2 · MISSING</text>
    </g>
    <line x1="150" y1="36" x2="150" y2="206" stroke="var(--grid)" stroke-width="1"></line>
  </g>
</svg>
^ The convergence bars, each tagged with Santara's status. Length is how much the field agrees; the tag is what Santara has. The whole decision is that the two columns are different questions — and the grey bar (sandbox, HAVE) is the one the raw ranking is about to trip over.

How to read this: scan the bar lengths for evidence strength, then scan the tags for Santara's position. The failure signature you are looking for is a long bar with a `HAVE` tag — high agreement on something you have already built — because that is precisely the row a count-only ranking will mistake for a top priority.

### Strategy #1 — rank by the convergence count. This is the bug.

The obvious build queue sorts the primitives by their count and takes the top. It is one line and it feels like exactly what a survey is for — the field agrees hardest on hooks, then sandbox, so build hooks, then sandbox.

```
# convergence.py:54-57 — COMPLETE (the trap: rank by raw convergence, top of the list is the queue)
def raw_rank(prims):
    """THE BUG: rank every primitive by raw convergence and call the top of the list
    the build queue -- ignoring that Santara already implemented some of them."""
    return [n for n, _ in sorted(prims.items(), key=rank_key)]
```

Stop here and predict. The top of this list is hooks, which Santara lacks — correct. What is second, and is it something Santara should spend a week building? Write it down before the output.

```
# $ python3 convergence.py --rawrank
#   1. hooks                  x6/7
#   2. sandbox                x5/7  <-- Santara already HAS this
#   3. plan_mode              x4/7
```

run: 2026-08-22 · fixture · 7 harnesses · `python3 convergence.py --rawrank`

Second on the build list is a sandbox — and Santara already runs one. The `sandbox` deep-dive's own "Santara today" line says it: a subprocess jail with rlimits and a denylist, plus Docker and SSH backends, and by the Codex study the labs had added a Landlock/seccomp confinement. Santara is not merely at parity here; it is *ahead* of OpenCode, the one studied harness with no OS sandbox at all. The raw ranking took the single row where Santara had already done the work and put it second on the list of things to do. The reason the bug is dangerous rather than obvious is that it agrees on the easy call — hooks, a real gap, is genuinely first — and only diverges on the row where the answer was already in hand. A ranking that is right about the thing you were going to do anyway and wrong about the thing that wastes a week is worse than no ranking, because it comes with the authority of six citations.

<svg viewBox="0 0 700 210" role="img" aria-label="Two build queues side by side. The raw-count queue lists hooks, sandbox, plan_mode; sandbox is struck through and flagged as already-built. The gap-gated queue lists hooks, plan_mode, progressive_disclosure, checkpoints, with sandbox removed to a dropped bin.">
  <g font-family="var(--mono)" font-size="10">
    <text x="40" y="24" fill="var(--s2)">raw-count queue (the trap)</text>
    <text x="400" y="24" fill="var(--s1)">gap-gated queue (correct)</text>
    <g>
      <text x="40" y="60" fill="var(--ink)">1. hooks       x6</text>
      <text x="40" y="86" fill="var(--muted)">2. sandbox     x5</text>
      <line x1="58" y1="82" x2="196" y2="82" stroke="var(--s2)" stroke-width="1.5"></line>
      <text x="210" y="86" fill="var(--s2)" font-size="8">already built — wasted week</text>
      <text x="40" y="112" fill="var(--ink)">3. plan_mode   x4</text>
    </g>
    <g>
      <text x="400" y="60" fill="var(--ink)">1. hooks       x6  MISSING</text>
      <text x="400" y="86" fill="var(--ink)">2. plan_mode   x4  MISSING</text>
      <text x="400" y="112" fill="var(--ink)">3. prog.disc.  x4  partial</text>
      <text x="400" y="138" fill="var(--ink)">4. checkpoints x2  MISSING</text>
    </g>
    <rect x="400" y="158" width="260" height="26" rx="6" fill="var(--panel)" stroke="var(--s1)"></rect>
    <text x="412" y="175" fill="var(--s1)" font-size="9">dropped (HAVE): sandbox — subtracted out</text>
    <line x1="360" y1="40" x2="360" y2="190" stroke="var(--grid)" stroke-width="1" stroke-dasharray="3 3"></line>
  </g>
</svg>
^ Same table, two queues. The raw count keeps sandbox and puts it second; the gated queue subtracts every HAVE row first, so sandbox never appears and the real gaps close ranks. The only difference between the two is the subtraction.

### Strategy #2 — gate the ranking on your own gaps

The fix is the subtraction from the frame. Rank by convergence, yes — but only over the primitives Santara lacks. A primitive you already have is not a thing to build, whatever the field thinks of it.

```
# convergence.py:47-51 — COMPLETE (the fix: rank convergence, but only over the gaps)
def build_priority(prims):
    """CORRECT: only primitives Santara still lacks (missing/partial), ranked by
    convergence. A primitive Santara already HAS is not a thing to build."""
    gap = [(n, p) for n, p in prims.items() if p["santara"] != "have"]
    return [n for n, _ in sorted(gap, key=rank_key)]
```

The single change is the filter `if p["santara"] != "have"` — the subtraction, in code. Both rankings share the same sort key, so this is not a different opinion about evidence; it is the same evidence with your own position taken out first.

```
# convergence.py:39-42 — COMPLETE (the shared sort key: convergence, then gap severity, then name)
def rank_key(item):
    """Deterministic order: convergence desc, then gap severity desc, then name."""
    name, p = item
    return (-p["stated_count"], -STATUS_GAP[p["santara"]], name)
```

The key sorts on convergence first, and breaks the plan-mode / progressive-disclosure tie at four each by gap severity — `missing` (2) outranks `partial` (1) — so plan mode, which Santara lacks entirely, sits above progressive disclosure, which it has in a weaker form. Run the gated queue:

```
# $ python3 convergence.py --priority
#   1. hooks                  x6/7  (Santara: MISSING)
#   2. plan_mode              x4/7  (Santara: MISSING)
#   3. progressive_disclosure x4/7  (Santara: partial)
#   4. checkpoints            x2/7  (Santara: MISSING)
#   dropped (already have): sandbox
```

run: 2026-08-22 · fixture · deterministic · `python3 convergence.py --priority`

Hooks first — most-agreed, and missing. Then plan mode and progressive disclosure, both at four, ordered by how much Santara lacks each. Checkpoints last, because two of seven is weak evidence and its "trust net separate from git" value is a coding-surface nicety a Telegram assistant barely needs. Sandbox is gone — subtracted, not demoted — and the queue reads as a plan the labs could actually execute top to bottom without once rebuilding something they already ship.

**The field's agreement tells you where the landmark is; your own status tells you where you stand. A build queue is the first minus the second, and a ranking that skips the subtraction will send you to build what you already have.**

### The count is not a vote: the dissenter

One more honesty check the frame demands, because a triangulated landmark can still be a mirage if you ignore who *didn't* sight it. Each row in the table carries its own provenance — the count, the harnesses that back it, the dissenter, and the source line — so nothing is a bare number:

```
# convergence.json — DELTA (the sandbox primitive's record; every field is traceable)
"sandbox": {
  "stated_count": 5,
  "confirmed_in": ["claude_code", "hermes", "openclaw", "nanoclaw", "codex"],
  "dissent": "opencode",
  "santara": "have",
  "source": "codex-deep-dive.md:469",
  "headline": "all five studied systems converge on OS-enforced sandboxing"
}
```

The `dissent` tag matters more than the five. OpenCode is not missing a sandbox by oversight — it considered OS-level isolation and deliberately rested its safety on a permission ruleset instead, which the deep-dive flags as the reason Santara's kernel jail is *ahead* of it. A raw count of five reads as "the field agrees"; the truth is "five built it, one refused it on purpose, and the one who refused is the newest and most-starred." A converged primitive with a principled dissenter is a weaker mandate than its bare count suggests — the same lesson the evals track teaches about a headline number with no denominator. The queue still ranks sandbox out because Santara has it, but the dissent is why you would not have blindly trusted the count even if it didn't.

<svg viewBox="0 0 700 210" role="img" aria-label="A presence matrix: five primitive rows against seven harness columns. Filled cells show which harness has each primitive; hooks is filled across six, sandbox across five with the OpenCode cell marked as a deliberate refusal, plan_mode and progressive_disclosure across four each, checkpoints across two.">
  <g font-family="var(--mono)" font-size="8.5">
    <g fill="var(--muted)" text-anchor="middle">
      <text x="300" y="30">CC</text><text x="352" y="30">Herm</text><text x="404" y="30">OClaw</text><text x="456" y="30">NClaw</text><text x="508" y="30">Codex</text><text x="560" y="30">Curs</text><text x="612" y="30">OCode</text>
    </g>
    <g font-size="9.5" fill="var(--ink)" text-anchor="end">
      <text x="150" y="55">hooks</text><text x="150" y="87">sandbox</text><text x="150" y="119">plan_mode</text><text x="150" y="151">prog.disclosure</text><text x="150" y="183">checkpoints</text>
    </g>
    <g>
      <rect x="284" y="44" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="336" y="44" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="388" y="44" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="440" y="44" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="492" y="44" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="544" y="44" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="596" y="44" width="32" height="16" rx="2" fill="var(--grid)"></rect>
      <rect x="284" y="76" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="336" y="76" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="388" y="76" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="440" y="76" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="492" y="76" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="544" y="76" width="32" height="16" rx="2" fill="var(--grid)"></rect><rect x="596" y="76" width="32" height="16" rx="2" fill="var(--panel)" stroke="var(--s2)" stroke-width="1.5"></rect><text x="612" y="88" text-anchor="middle" fill="var(--s2)">no</text>
      <rect x="284" y="108" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="336" y="108" width="32" height="16" rx="2" fill="var(--grid)"></rect><rect x="388" y="108" width="32" height="16" rx="2" fill="var(--grid)"></rect><rect x="440" y="108" width="32" height="16" rx="2" fill="var(--grid)"></rect><rect x="492" y="108" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="544" y="108" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="596" y="108" width="32" height="16" rx="2" fill="var(--s1)"></rect>
      <rect x="284" y="140" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="336" y="140" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="388" y="140" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="440" y="140" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="492" y="140" width="32" height="16" rx="2" fill="var(--grid)"></rect><rect x="544" y="140" width="32" height="16" rx="2" fill="var(--grid)"></rect><rect x="596" y="140" width="32" height="16" rx="2" fill="var(--grid)"></rect>
      <rect x="284" y="172" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="336" y="172" width="32" height="16" rx="2" fill="var(--grid)"></rect><rect x="388" y="172" width="32" height="16" rx="2" fill="var(--grid)"></rect><rect x="440" y="172" width="32" height="16" rx="2" fill="var(--grid)"></rect><rect x="492" y="172" width="32" height="16" rx="2" fill="var(--grid)"></rect><rect x="544" y="172" width="32" height="16" rx="2" fill="var(--s1)"></rect><rect x="596" y="172" width="32" height="16" rx="2" fill="var(--grid)"></rect>
    </g>
  </g>
</svg>
^ The presence matrix behind the counts: filled = the studies credit that harness with the primitive. The one outlined cell is OpenCode refusing an OS sandbox on purpose — the dissent a bare count of five hides.

### The running tally

| ranking | 1st | 2nd | 3rd | verdict |
|---|---|---|---|---|
| raw count | hooks | sandbox (HAVE) | plan_mode | sends you to rebuild a sandbox |
| gap-gated | hooks | plan_mode | progressive_disclosure | every row is a real gap |

The table never changed; only the ranking did. Both agree that hooks come first, which is what makes the raw count seductive — it nails the easy call. They diverge on exactly one row, and it is the expensive one: the raw count spends a week rebuilding the sandbox Santara already runs, while the gated queue subtracts it and closes ranks on the real gaps. One filter is the whole difference, and it is the filter that asks "do we already have this?" before "does the field like it?"

**A survey of others is a map of where things are; it is not a route from where you are. Never let a convergence count become a build order without subtracting what you already ship.**

### Prove the whole thing in one run

One command checks the claims the decision rests on: every count matches the harnesses the studies actually name, the raw ranking really does queue a have-already, and the gated queue never does. The data-integrity guard is the one that keeps a count from drifting away from its evidence:

```
# convergence.py:110-119 — COMPLETE (a count must equal the harnesses that back it)
    # data integrity: stated_count equals the number of harnesses named, all known.
    counts_ok = True
    known = set(harnesses)
    for name, p in prims.items():
        named = p["confirmed_in"]
        if len(named) != p["stated_count"] or not set(named) <= known:
            counts_ok = False
        if p["dissent"] and p["dissent"] not in known:
            counts_ok = False
```

```
# $ python3 convergence.py --check
#   every stated_count equals its named harnesses, all in the roster = True
#   raw-rank top 3 = ['hooks', 'sandbox', 'plan_mode']
#   raw rank tells Santara to build something it HAS (sandbox) = True
#   gated queue = ['hooks', 'plan_mode', 'progressive_disclosure', 'checkpoints']
#   gated queue excludes every have-already = True, leads with hooks = True
#   rank is independent of dict order (deterministic) = True
#   SELF-TEST PASS  counts=True  trap_shows=True  gated_clean=True  deterministic=True
```

run: 2026-08-22 · deterministic · 7 harnesses, 5 primitives · `python3 convergence.py --check`

The data-integrity line is the one that keeps this honest: for every primitive, the count equals the number of harnesses named in `confirmed_in`, and every name is in the seven-harness roster, so a count cannot drift from the systems that back it. The trap is shown to build a have-already; the gated queue is shown never to. The self-test asserts all four and is the only thing you should trust over the prose.

### Bridge to the standard names

Nobody at a whiteboard calls it triangulation. This is **convergent validity** — agreement across independent instruments as evidence a construct is real — paired with a **gap analysis** or **capability audit**: score the field's practices against your own current state and prioritize the deltas. Product teams call the trap **build-what's-popular** or **cargo-culting the roadmap**; the fix is a **buy-vs-build / have-vs-need** filter applied before ranking. The dissenter point is **survivorship bias**'s cousin — a raw count tallies the systems that adopted a primitive and silently drops the one that evaluated and rejected it, so the denominator hides. "Triangulation minus your position" is just the operational feel: the field tells you what is real, your own audit tells you what is a gap, and only the second is a plan.

### What we did not settle

The table is a fixture, so this measures the decision procedure honestly and the world only as the deep-dives tallied it. Real complications we skipped, each of which would refine a live version: convergence count says nothing about **effort** or **payoff size** — hooks are both high-agreement and high-leverage, but a real queue would weight each row by build cost and expected benefit, not agreement alone, so a x2 primitive that takes an afternoon might outrank a x4 that takes a quarter; the counts are the studies' **own tallies**, and a stricter pass would re-verify each harness's mechanism first-hand rather than trusting the headline number, because a lesson's ×N can quietly inflate as later studies round up; **partial** is doing a lot of work as a single status — Santara "has" progressive disclosure but injects full skill bodies rather than an index, which is arguably closer to missing than to have, and a real audit would score maturity on a finer scale; and a primitive's convergence can be an artifact of a **shared lineage** rather than independent invention — several of these harnesses build on the same Agent SDK, so their agreement on a primitive it provides is one sightline wearing three coats, not three independent ones, which is the triangulation frame's sharpest failure mode.

## Build

The pipeline in one paragraph: read many independent systems; for each cross-cutting primitive, count how many converge on it and cite where you read it; record your own status for each — have, partial, or missing; then rank the primitives by convergence but only over the ones you lack, subtracting everything you already ship, and read the top of that list as your build queue. Never let the raw count be the order, and always check who dissented before trusting a high count.

We opened on the gated queue. The payoff again:

```
# modules/agent-harness/code/harness-adv-02/ — COMPLETE, run from that directory
$ python3 convergence.py --priority
  1. hooks                  x6/7  (Santara: MISSING)
  2. plan_mode              x4/7  (Santara: MISSING)
  dropped (already have): sandbox
```

Now do it for your own agent. The one dial is `convergence.json`: replace the five primitives with the cross-cutting lessons from your own reading, each with its `stated_count`, the `confirmed_in` harnesses that back it, any `dissent`, a `source` line you can open, and your project's honest `santara` status. Everything in `convergence.py` derives from that file. Keep the source citations — a count you cannot trace to a line is the one that inflates.

```
# convergence.py:31 — COMPLETE (the one knob worth turning: how much a status counts as a gap)
STATUS_GAP = {"missing": 2, "partial": 1, "have": 0}   # how much room is left to build
```

Your number to beat is not the length of the queue — it is the **count of rows the gate drops**. If your gate drops nothing, either you have built nothing the field has (unlikely) or your statuses are dishonest (likely), and the queue is just the raw count wearing a filter that never fires. A gate that never subtracts is the bug with extra steps. Bring back two numbers: how many primitives the field converges on, and how many your gate removed because you already ship them — the second is the measure of how much of the field you have already caught up to. Good luck.

### FAQ

**Isn't the raw count still useful — it got hooks right?** It did, and that is the trap. A ranking that is correct on the calls you would make anyway and wrong on the one that costs a week is more dangerous than an obviously bad one, because six citations make the wrong second-place look authoritative. Use the count for evidence strength; never use it as the order.

**Why does plan mode beat progressive disclosure at the same count of four?** The tie-break in `rank_key` is gap severity: plan mode is `missing`, progressive disclosure is `partial` (Santara has skills but injects full bodies). All else equal, build the total gap before the half-built one.

**Should a dissenter drop a primitive out of the queue?** Not by itself — sandbox left the queue because Santara has it, not because OpenCode refused it. But a dissenter should lower your confidence in a high count and make you read *why* it was refused before you build; sometimes the dissenter is the one who saw the cost you are about to pay.

**My own audit says I "have" everything — now what?** Then either you are further along than the field (check the dissenters — maybe you are the OpenCode of your niche) or your statuses are graded too generously. Re-score `partial` honestly: "has a weaker form" is not "have," and the demo's progressive-disclosure row is exactly that kind of soft `partial`.

### Errata

Version one, dated 2026-08-22. The counts are the deep-dives' peak stated tallies, not an independent re-derivation — the "what we did not settle" section flags that a stricter pass would re-verify each mechanism, and that shared-SDK lineage can inflate apparent independence. Hooks are marked `x6` after the six harnesses the studies name individually; OpenCode's plugin SDK carries hooks too, which would make it seven, but the table holds to the figure the series itself printed rather than rounding up — the same discipline the module is about.

## Definition of done

- [ ] `convergence.json` for your own agent: each cross-cutting primitive with a count, the harnesses that back it, any dissenter, a citable source line, and your honest status
- [ ] A convergence table that prints each primitive's count, dissent, source, and your status
- [ ] A build queue that ranks convergence but only over primitives you lack (`have` rows subtracted, not demoted)
- [ ] The raw-count ranking kept for contrast, so the trap — queuing a have-already — is visible
- [ ] `python3 convergence.py --check` printing SELF-TEST PASS: counts match named harnesses, the trap builds a have-already, the gated queue never does, deterministic
- [ ] Every count traceable to a source line you can open; no untraced numbers
- [ ] The two numbers that matter recorded: primitives the field converges on, and how many your gate dropped as already-shipped
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Hooks convergence at six of seven and an OS sandbox at five. State which one belongs at the top of Santara's build queue and why the other is not on the queue at all.
2. Give the one-line difference between the raw-count ranking and the gap-gated ranking, and the single expensive row on which they disagree.
3. In the triangulation frame, say what a convergence count is and what "your own position" is, and write the one-sentence formula for a build queue.
4. The sandbox row is `x5` with a dissenter. Name the dissenter, say why its refusal was principled, and explain why a count of five with a dissenter is a weaker mandate than a bare five suggests.
5. Your own convergence table dropped some rows from the queue. How many did your gate drop, which primitive led your queue, and what does the number of dropped rows measure about your project?

## External resources

- faisalmahdy/agent — `docs/harness-landscape.md` — my summary: the source survey that ranks 23 harnesses and states the cross-cutting convergences this module distills; read the "Cross-cutting signals" section for the field-level agreements, and note it is explicitly a decision doc, not a deep dive.
- faisalmahdy/agent — `docs/claude-code-deep-dive.md` (Part 4, "Lessons for Santara") — my summary: the template for a single deep-dive's ranked, convergence-tagged lessons with a per-lesson "Santara today / Do" status; the `[×N]` markers this table's counts come from live here, one lesson at a time.
- This hub, *evals-inter-04* — modules/evals-and-statistics/evals-inter-04.md — my summary: rubric aggregation, where a mean can hide a failed gate; the same instinct as this module's dissenter — an aggregate number (a rubric mean, a convergence count) can be high while a component that should veto it is quietly outvoted.
