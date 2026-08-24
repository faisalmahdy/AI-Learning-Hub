#!/usr/bin/env python3
"""The agent loop, hand-written and offline — a referee for a tool-using model.

An agent is a loop: ask the model for its next move, and either it hands back a
final answer or it calls a tool; run the tool, append the result, ask again.
The whole reliability of an agent lives in the two rules that guarantee the loop
always stops. This file builds that loop from scratch, drives it with a
deterministic scripted provider (no API, no spend), and shows the guards fire.

  --run       solve a 2-step task with the scripted Echo provider
  --caponly   a stuck model under the step cap ALONE: burns every step
  --guarded   the same stuck model with the no-progress guard: stops clean
  --check     the loop is deterministic (same trace twice) and the answer holds

Stdlib only. No network, no API keys, no model calls — the provider is a fixture
that mimics a model. Swap it for a real provider behind the same Provider base
and the loop does not change; that is the point.
"""
import argparse
import sys


# ------------------------------------------------------------------- messages

class Msg:
    """One turn in the transcript. role is user / assistant / tool."""
    def __init__(self, role, content, tool=None, args=None):
        self.role = role
        self.content = content
        self.tool = tool
        self.args = args


# ------------------------------------------------------------------ the seams

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


# --------------------------------------------------------------- a tool, a model

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


class StuckProvider(Provider):
    """A model that never finishes: it calls the same tool with the same args
    forever. Every real harness meets one; the loop must survive it."""
    def respond(self, messages):
        return Reply(tool="add", args={"a": 1, "b": 1})


# ------------------------------------------------------------------- the loop

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


# ------------------------------------------------------------------- printing

def show(trace):
    for ev in trace:
        if ev[0] == "call":
            _, step, tool, args, result = ev
            print("  step %d  CALL  %s(%s) -> %s"
                  % (step, tool, ", ".join("%s=%s" % kv for kv in sorted(args.items())), result))
        elif ev[0] == "final":
            print("  step %d  FINAL %s" % (ev[1], ev[2]))
        else:
            print("  step %d  STOP  %s" % (ev[1], ev[2]))


TOOLS = {"add": AddTool()}
TASK = "What is 2 + 3, then add 10 to that?"


def check():
    print("SELF-TEST — the loop is deterministic and the answer holds")
    print("-" * 62)
    a1, t1 = run(EchoProvider(), TOOLS, TASK)
    a2, t2 = run(EchoProvider(), TOOLS, TASK)
    same = [e for e in t1] == [e for e in t2]
    print("  run 1 answer = %s" % a1)
    print("  run 2 answer = %s" % a2)
    print("  identical trace across two runs = %s" % same)
    # cross-check the arithmetic the tool did, by hand.
    calls = [e for e in t1 if e[0] == "call"]
    print("  tool calls made = %d" % len(calls))
    hand = str((2 + 3) + 10)
    got = a1.strip(".").split()[-1] if a1 else None
    print("  final says %s, by-hand (2+3)+10 = %s, match = %s" % (got, hand, got == hand))
    # a stuck model must never hang: it stops, one way or another.
    _, tc = run(StuckProvider(), TOOLS, TASK, guard=False)
    _, tg = run(StuckProvider(), TOOLS, TASK, guard=True)
    cap_stopped = tc[-1][0] == "stopped"
    guard_stopped = tg[-1][0] == "stopped" and "no progress" in tg[-1][2]
    print("  stuck+cap stops = %s   stuck+guard stops early = %s" % (cap_stopped, guard_stopped))
    ok = same and got == hand and cap_stopped and guard_stopped
    print("-" * 62)
    print("SELF-TEST %s" % ("PASS" if ok else "FAIL"))
    return ok


def main():
    p = argparse.ArgumentParser(description="A hand-written agent loop, run offline.")
    for flag in ("run", "caponly", "guarded", "check"):
        p.add_argument("--" + flag, action="store_true")
    args = p.parse_args()

    if args.check:
        return 0 if check() else 1

    print('task: "%s"' % TASK)
    print("")
    if args.run:
        answer, trace = run(EchoProvider(), TOOLS, TASK)
        show(trace)
        print("  => %s" % answer)
    elif args.caponly:
        answer, trace = run(StuckProvider(), TOOLS, TASK, max_steps=8, guard=False)
        show(trace)
        print("  => %s  (burned every step)" % answer)
    elif args.guarded:
        answer, trace = run(StuckProvider(), TOOLS, TASK, max_steps=8, guard=True)
        show(trace)
        print("  => %s  (stopped early, on purpose)" % answer)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
