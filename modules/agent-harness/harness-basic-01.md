---
id: harness-basic-01
title: An agent is a loop — build the thirty lines yourself
topic: agent-harness
level: basic
status: ready
eli5: An agent is just — ask the model, run the tool it asked for, repeat — plus two rules so it can never get stuck forever.
time: 6-8h
summary: Build a tool-calling agent loop from scratch and drive it with a scripted offline model; then watch a step cap alone waste all 8 turns on a model that gets stuck, while a three-line no-progress guard stops it at 3 — because the whole reliability of an agent is the two rules that make the loop end.
---

## Why this module

This is the first module of the agent-harness topic, and it starts where every agent actually starts and almost no tutorial does: the loop. People `import` an `Agent` from a framework, call `.run()`, and never see that underneath is a `for` loop asking a model for its next move. The scan found the loop worth teaching from the labs' own harness — a hand-written multi-turn tool-calling loop whose docstring enumerates its reliability guarantees, backed by ~3,200 tests that run with no API key via a deterministic fake provider. The loop is small. Its guarantees are the whole game.

This module builds that loop at `basic`. A minimal but real agent loop, a fake tool, and a scripted provider that stands in for a model — so the whole thing runs offline, deterministically, for free — and you watch it solve a two-step task, then watch it survive a model that never finishes. What it omits: no streaming, no real API calls, no checkpointing — those wrap the loop later without changing it. You need to know what a Python class and a `for` loop are. Stdlib Python 3, offline, $0.00, under a second a run, one sitting. The hard part is one idea: the loop's reliability is not in the model, it is in two rules you write.

By the end, one command runs your loop end to end. Skipping ahead:

```
# modules/agent-harness/code/harness-basic-01/ — COMPLETE, run from that directory
$ python3 agentloop.py --run

task: "What is 2 + 3, then add 10 to that?"

  step 1  CALL  add(a=2, b=3) -> 5
  step 2  CALL  add(a=5, b=10) -> 15
  step 3  FINAL The answer is 15.
  => The answer is 15.
```

run: 2026-08-22 · provider is a deterministic fixture, no model call · `python3 agentloop.py --run`

Three steps, and every line is the loop working: the model asks for a tool, the loop runs it and hands back the result, the model asks again with the result in hand, then answers. No framework, no magic — a `for` loop you will write below. The interesting part is not this happy path; it is what happens when the model does not cooperate, which is where the two guarantees earn their place.

## Concepts

Named here so you can find them again; each is built below.

- **The transcript** — the growing list of messages (user, tool calls, tool results) the model sees each turn.
- **Provider** — the one seam the model lives behind: given the transcript, return the next move. Real or fake, the loop can't tell.
- **Tool** — a named thing the model can call; takes args, returns a string.
- **Reply** — what a provider hands back: either a final answer or a tool call.
- **Step cap** — the loop stops after N turns no matter what. The backstop.
- **No-progress guard** — the loop stops early when the model repeats the same call. The brake.

## Worked example

Source: faisalmahdy/agent — `agent/core/loop.py` (the hand-written multi-turn tool-calling loop, ~384 lines, whose docstring enumerates step caps, no-progress guards, and cancellation) and `agent/providers/base.py` (the provider seam). De-personalized; the toy here is the same shape, minus the production plumbing.

Script and fixtures: `modules/agent-harness/code/harness-basic-01/` — `agentloop.py`, 203 lines, no fixtures file needed (the provider is the fixture). Every command runs from there.

### Install the frame: the loop is a referee

In my opinion, the best way to think of an agent loop is as the referee of a turn-based game, not as the player.

The model is the player: each turn it either makes a move (calls a tool) or declares the game won (returns a final answer). The referee — the loop — does none of the thinking. It takes the move, applies it (runs the tool), writes it into the record (the transcript), and hands the board back to the player for the next turn. And a referee's real job is not the moves; it is enforcing the two rules that guarantee the game *ends*: a move limit, and a repetition rule — the same one chess uses, where shuffling the same position over and over is a draw, not an eternity.

Three jobs, one line each: the provider says "what is my next move?", the tool says "here is what that move does", and the loop says "apply it, record it, and check we are not stuck."

### The seams: what a model and a tool must expose

Before the loop, the two interfaces it talks to. A provider returns a `Reply` — either a final answer or a tool call. A tool has a name and runs on args. That is the whole contract.

```
# agentloop.py:36-57 — COMPLETE (the three seams the loop talks to)
class Reply:
    """What a provider hands back: EITHER a final answer OR a tool call."""
    def __init__(self, final=None, tool=None, args=None):
        self.final = final
        self.tool = tool
        self.args = args


class Provider:
    """The one method a model must expose. A real one calls an API here; ours
    reads the transcript and returns a scripted move. The loop never knows which."""
    def respond(self, messages):
        raise NotImplementedError


class Tool:
    name = "?"

    def run(self, args):
        raise NotImplementedError
```

This is called the **provider seam**, and it is the most important line in the file even though it does nothing: because the loop only ever calls `provider.respond(...)`, it cannot tell a real model from a fixture. That is what lets the whole agent be tested offline — and what lets you swap models without touching the loop.

Now a real tool and a scripted provider. The provider is a fixture standing in for a model doing "2 + 3, then add 10"; it plans off the tool results already in the transcript, exactly as a model would.

```
# agentloop.py:60-81 — COMPLETE (one tool, and a model-shaped fixture)
class AddTool(Tool):
    name = "add"

    def run(self, args):
        return str(args["a"] + args["b"])


class EchoProvider(Provider):
    """A fixture standing in for a model doing '2+3, then add 10'. It plans off
    the tool results already in the transcript, exactly as a real model would."""
    def respond(self, messages):
        results = [m for m in messages if m.role == "tool"]
        if len(results) == 0:
            return Reply(tool="add", args={"a": 2, "b": 3})
        if len(results) == 1:
            prev = int(results[-1].content)
            return Reply(tool="add", args={"a": prev, "b": 10})
        return Reply(final="The answer is " + results[-1].content + ".")
```

### The loop itself

Here is the whole agent. Read it as the referee: ask, and either the player is done, or apply the move and record it.

```
# agentloop.py:89-126 — COMPLETE (the entire loop; imports at the top of the file)
def run(provider, tools, task, max_steps=8, guard=True):
    """Drive the model until it answers, or a guarantee stops us.
    Returns (answer_or_None, trace). The trace is a list of printable events."""
    messages = [Msg("user", task)]
    trace = []
    last_call = None
    repeats = 0

    for step in range(1, max_steps + 1):
        reply = provider.respond(messages)

        if reply.final is not None:              # the model is done
            trace.append(("final", step, reply.final))
            return reply.final, trace

        call = (reply.tool, tuple(sorted(reply.args.items())))
        if call == last_call:                    # same tool, same args as before
            repeats += 1
        else:
            repeats = 0
            last_call = call
        if guard and repeats >= 2:               # seen three times running
            trace.append(("stopped", step, "no progress: same call 3x -> " + reply.tool))
            return None, trace

        tool = tools.get(reply.tool)             # dispatch, or a clear error
        if tool is None:
            result = "ERROR: no tool named '" + reply.tool + "'"
        else:
            result = tool.run(reply.args)

        messages.append(Msg("assistant", "", tool=reply.tool, args=reply.args))
        messages.append(Msg("tool", result))     # <- the result the model must see
        trace.append(("call", step, reply.tool, dict(reply.args), result))

    trace.append(("stopped", max_steps, "step cap reached (" + str(max_steps) + ")"))
    return None, trace
```

That is it. Bracket for the size: the logic is under forty lines; the labs' production loop is 384, and every extra line is streaming, checkpoint-and-resume, and cancellation — none of which change the cycle you just read. Confess the magic numbers before we lean on them: `max_steps=8` and `repeats >= 2` (stop on the third identical call) are picked by feel, and we will watch both fire below.

<svg viewBox="0 0 680 250" role="img" aria-label="A cycle diagram: the model returns either a final answer, which exits the loop, or a tool call; the loop dispatches the tool, appends the result to the transcript, and returns to the model. Two guards, a step cap and a no-progress check, sit on the loop.">
  <g font-family="var(--mono)">
    <rect x="60" y="100" width="140" height="50" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="130" y="122" font-size="11" text-anchor="middle" fill="var(--ink)">provider</text>
    <text x="130" y="138" font-size="9" text-anchor="middle" fill="var(--muted)">what's my move?</text>
    <rect x="300" y="100" width="140" height="50" rx="8" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect>
    <text x="370" y="122" font-size="11" text-anchor="middle" fill="var(--acc-ink)">the loop</text>
    <text x="370" y="138" font-size="9" text-anchor="middle" fill="var(--acc-ink)">apply · record · check</text>
    <rect x="540" y="100" width="120" height="50" rx="8" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="600" y="122" font-size="11" text-anchor="middle" fill="var(--ink)">tool</text>
    <text x="600" y="138" font-size="9" text-anchor="middle" fill="var(--muted)">run(args)</text>
    <line x1="200" y1="118" x2="298" y2="118" stroke="var(--line)" stroke-width="1.5" marker-end="url(#a)"></line>
    <text x="249" y="110" font-size="9" text-anchor="middle" fill="var(--muted)">tool call</text>
    <line x1="440" y1="118" x2="538" y2="118" stroke="var(--line)" stroke-width="1.5" marker-end="url(#a)"></line>
    <line x1="540" y1="138" x2="440" y2="138" stroke="var(--line)" stroke-width="1.5" marker-end="url(#a)"></line>
    <text x="490" y="132" font-size="9" text-anchor="middle" fill="var(--muted)">result</text>
    <path d="M300 138 q-120 60 -170 0" fill="none" stroke="var(--line)" stroke-width="1.5" marker-end="url(#a)"></path>
    <text x="215" y="192" font-size="9" text-anchor="middle" fill="var(--muted)">append result, ask again</text>
    <line x1="370" y1="100" x2="370" y2="52" stroke="var(--s1)" stroke-width="1.5" marker-end="url(#a)"></line>
    <text x="370" y="44" font-size="9.5" text-anchor="middle" fill="var(--s1)">final answer -> exit</text>
    <rect x="300" y="200" width="290" height="26" rx="6" fill="var(--panel)" stroke="var(--grid)"></rect>
    <text x="445" y="217" font-size="9.5" text-anchor="middle" fill="var(--muted)">guards on the loop: step cap · no-progress</text>
    <defs><marker id="a" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6 z" fill="var(--line)"></path></marker></defs>
  </g>
</svg>
^ The loop as a referee: the provider proposes a move or declares done; the loop applies the tool, appends the result, and asks again, until a final answer exits or a guard stops it.

How to read this: follow the arrows in a circle — that circle is the agent. The only exit at the top is a final answer; the only other way out is a guard, which is why the guards are the reliability.

### Look at the loop run: the transcript grows

On the happy path the cold-open trace is the loop turning three times. What actually changes between turns is the transcript — the message list the provider reads each time.

<svg viewBox="0 0 680 210" role="img" aria-label="The transcript growing over the run: it starts with the user task, then gains an assistant tool-call and a tool result for add 2 3 equals 5, then another pair for add 5 10 equals 15, then the assistant's final answer.">
  <g font-family="var(--mono)">
    <text x="40" y="24" font-size="10.5" fill="var(--muted)">the transcript the provider reads, after each step</text>
    <g font-size="10">
      <rect x="40" y="36" width="600" height="22" rx="4" fill="var(--panel)" stroke="var(--grid)"></rect><text x="50" y="51" fill="var(--muted)">user   · What is 2 + 3, then add 10 to that?</text>
      <rect x="40" y="62" width="600" height="22" rx="4" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="50" y="77" fill="var(--acc-ink)">assistant · CALL add(a=2, b=3)</text>
      <rect x="40" y="88" width="600" height="22" rx="4" fill="var(--panel)" stroke="var(--grid)"></rect><text x="50" y="103" fill="var(--ink)">tool   · 5</text>
      <rect x="40" y="114" width="600" height="22" rx="4" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="50" y="129" fill="var(--acc-ink)">assistant · CALL add(a=5, b=10)</text>
      <rect x="40" y="140" width="600" height="22" rx="4" fill="var(--panel)" stroke="var(--grid)"></rect><text x="50" y="155" fill="var(--ink)">tool   · 15</text>
      <rect x="40" y="166" width="600" height="22" rx="4" fill="var(--s1)" opacity="0.18" stroke="var(--s1)"></rect><text x="50" y="181" fill="var(--ink)">assistant · FINAL The answer is 15.</text>
    </g>
  </g>
</svg>
^ Each turn appends two lines — the model's tool call and the tool's result — until the model has what it needs and answers. The provider re-reads the whole list every turn.

How to read this: the two shaded assistant rows are the model's moves; the plain rows below each are what the tool handed back. The model on turn 2 knows the answer is 5 only because that `tool · 5` line is in the transcript — which is the one line the loop must never forget to append.

### Ugly first: what stops a model that won't stop?

Now the prediction — commit before the next section. Swap in a model that never finishes: it calls `add(1, 1)` every single turn, forever. Our loop has a step cap of 8. Before the loop gives up, how many times does it call the tool — a couple, because it notices the repeat, or all eight? Write it down. Most people expect the loop to notice. The answer is at the top of the next section.

Strategy #1 is the loop with no cap at all — a bare `while True`. On the cooperative model it finishes fine. On the stuck model it never returns, so we cannot even print a trace: the demo would hang your terminal. That is the failure, and it is why every agent loop ever written has a cap.

Strategy #2 adds the cap — the `for step in range(max_steps)` you already read. Now it is safe to run. On the stuck model:

```
# $ python3 agentloop.py --caponly
#   step 1  CALL  add(a=1, b=1) -> 2
#   step 2  CALL  add(a=1, b=1) -> 2
#   ...
#   step 8  CALL  add(a=1, b=1) -> 2
#   step 8  STOP  step cap reached (8)
#   => None  (burned every step)
```

run: 2026-08-22 · fixture, no model call · `python3 agentloop.py --caponly`

There is the answer to the prediction, and the size of the surprise: **all eight.** The step cap does not look at *what* the model does, only how many times — so a stuck model burns the entire budget, eight identical calls, before the cap trips. With a real model those are eight API calls and eight bills for one wasted turn. The cap is a backstop, not a brake.

Strategy #3 is the brake: the no-progress guard, the three lines in the loop that remember the last call and stop when it repeats. This is called the **no-progress guard** — the same idea as chess's threefold repetition, and no scarier: keep the last `(tool, args)`, count repeats, stop at three. On the same stuck model:

```
# $ python3 agentloop.py --guarded
#   step 1  CALL  add(a=1, b=1) -> 2
#   step 2  CALL  add(a=1, b=1) -> 2
#   step 3  STOP  no progress: same call 3x -> add
#   => None  (stopped early, on purpose)
```

run: 2026-08-22 · fixture, no model call · `python3 agentloop.py --guarded`

Three steps instead of eight, and the stop says *why*. The cap still sits behind it as the backstop for a model that thrashes without exactly repeating — you keep both.

**A step cap guarantees the loop ends; the no-progress guard guarantees it does not waste your budget getting there.**

### The loop is deterministic, and the answer is right

A trace you can read is not a trace you can trust; `--check` runs the loop twice and cross-checks the arithmetic by hand.

```
# $ python3 agentloop.py --check
#   run 1 answer = The answer is 15.
#   run 2 answer = The answer is 15.
#   identical trace across two runs = True
#   tool calls made = 2
#   final says 15, by-hand (2+3)+10 = 15, match = True
#   stuck+cap stops = True   stuck+guard stops early = True
# SELF-TEST PASS
```

run: 2026-08-22 · provider is a deterministic fixture · `python3 agentloop.py --check`

Two runs, identical traces — because the provider is a fixture, the loop has no hidden randomness, which is exactly what makes an agent testable. The final answer, 15, is checked against `(2 + 3) + 10` computed directly, and both stop guarantees are asserted to fire. When you put a real, stochastic model behind the seam, this determinism is what you lose — and inter-03 in the evals track is where you learn to measure what replaces it.

## Build

The pipeline in one paragraph: define the provider and tool seams; write the loop that asks, dispatches, appends, and repeats; add a step cap so it always ends and a no-progress guard so it ends cheaply; test the whole thing offline with a scripted provider before a real model ever touches it.

We opened on the loop solving a two-step task. The payoff block (again):

```
# modules/agent-harness/code/harness-basic-01/ — COMPLETE, run from that directory
$ python3 agentloop.py --run
  step 1  CALL  add(a=2, b=3) -> 5
  step 2  CALL  add(a=5, b=10) -> 15
  step 3  FINAL The answer is 15.
  => The answer is 15.
```

Now point it at a real model. The one dial is `EchoProvider`: write a second `Provider` subclass whose `respond` calls an actual API and translates the reply into a `Reply` — a final answer or a `tool` + `args`. Nothing in `run` changes, because the loop only ever sees the seam. Add a second tool (a `multiply`, a fake `search`) to `TOOLS` and give the model a task that needs two.

Your number to beat is not a score — it is that your loop **survives a stuck model**. Point your real provider at a task it can loop on and confirm both guarantees fire: the cap ends it, and the guard ends it sooner. If a stuck model can burn your whole budget, you have a backstop but no brake; add the brake. Bring back the trace where the guard stopped it. Good luck.

### FAQ

**Isn't a real agent way more than this?** More lines, not more idea: streaming, retries, checkpointing, cancellation all wrap this cycle. The labs' 384-line loop is this loop plus production plumbing; the ask-dispatch-append-repeat is unchanged.

**Why append the tool result — can't the model remember?** No. The model is stateless between turns; it sees only the transcript you pass. Drop the `tool` line and the model never learns what its call returned, so it asks again, and again — the most common way a real agent gets stuck is a loop that forgets to append the result.

**Why stop at three repeats, not two?** A judgment, like the cap of 8 — two identical calls can be a legitimate retry, three is a rut. Both numbers are yours to tune; the module's point is that the numbers exist, not that these are right.

**Why is mine slow?** This one isn't — it's a fixture and pure Python. Yours is slow because each turn is a real API call; that is why the no-progress guard matters, and why you test the loop offline first.

### Errata

Version one, dated 2026-08-22. The Echo provider is scripted to a single task, so it demonstrates the loop's mechanics, not a model's judgment; a real provider replaces it without touching `run`. One soft spot left in: the no-progress guard here only catches *exact* repeats of `(tool, args)` — a model that varies its args slightly while making no real progress slips past it, and catching that is a harder problem than this module solves.

## Definition of done

- [ ] A `Provider` and `Tool` base class, and a loop that only ever talks to those seams
- [ ] A step cap so the loop always terminates, and a no-progress guard so it terminates cheaply
- [ ] The tool result appended to the transcript every turn — verified by a task that needs a previous result
- [ ] A scripted provider that runs the whole thing offline with no API key
- [ ] `python3 agentloop.py --check` printing SELF-TEST PASS: identical trace twice, and both guards fire
- [ ] One real `Provider` subclass added behind the same seam, the loop unchanged
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Draw the loop as a cycle: name the two things a provider can return, and the two ways the loop can exit.
2. A model gets stuck calling the same tool forever. Say what the step cap does, what the no-progress guard does, and why you keep both.
3. Why can the loop not tell a real model from a fixture, and what does that one fact buy you?
4. The loop appends two messages per turn. Name them, and say what breaks if you forget the second.
5. Your own run printed how many tool calls the cap-only stuck model made before stopping. What was it, and what does that number cost with a real model?

## External resources

- Yao et al., *ReAct: Synergizing Reasoning and Acting in Language Models* (2022) — https://arxiv.org/abs/2210.03629 — my summary: the reason-then-act-then-observe loop this module implements, minus the guards; read it for the pattern, then notice it says nothing about how the loop terminates.
- Anthropic, *Building effective agents* — https://www.anthropic.com/research/building-effective-agents — my summary: argues most "agents" are a simple loop plus tools, and that the engineering is in the loop's control, not the model; read against the corpus-bias rule as one vendor's framing.
- Anthropic, tool use documentation — https://docs.claude.com/en/docs/build-with-claude/tool-use — my summary: the real shape of a `Reply` (tool_use / tool_result blocks) that a production `Provider.respond` translates into the loop's terms.
