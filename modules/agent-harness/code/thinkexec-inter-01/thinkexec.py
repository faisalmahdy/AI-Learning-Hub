"""Execute tool calls only from the action channel, never from the model's reasoning text -- a harness that scans the chain-of-thought for tool names will run a tool the model was only considering, including a destructive one it explicitly deferred.

Modern models emit a reasoning trace -- a chain-of-thought or scratchpad -- alongside their committed actions. In that trace the model thinks out loud, and thinking out loud routinely names tools it is weighing but has not chosen: 'I could call delete_account to reset it, but first let me check the status.' The reasoning is deliberation; the decision is separate.

The tool-calling API keeps them separate on purpose. Committed tool calls come back as structured data in a dedicated action field; the reasoning is free text in a different field. Only the action field is a decision the model made. The reasoning field is the model's private weighing of options, and the tools it mentions there are candidates, hypotheticals, things rejected -- not instructions to the harness.

The bug is dispatching by pattern-matching the model's whole output. A harness that greps the text for tool-call-shaped mentions cannot tell 'I will call X' from 'I could call X but won't', because both are just text, so it executes every tool it finds -- including delete_account, which the model named only to reject it in favor of get_status. The harness has now performed an irreversible action the model deliberately deferred, driven by a thought rather than a decision. The more a model reasons about dangerous options (which is exactly what you want it to do), the more such phantom calls a text scanner fires.

The fix is to dispatch strictly from the action channel: run the calls in the structured action field, and treat the reasoning purely as data to log or display, never as a source of executable calls. The separation the API already provides is the safety boundary; honor it.

On this fixture the model's reasoning mentions both delete_account (considered, then deferred) and get_status, while its action field commits only to get_status. A text-scanning dispatcher runs both -- including the destructive delete; an action-channel dispatcher runs only get_status. This computes both.

  --scan     the tools a text-scanning dispatcher would execute (from reasoning + action)
  --action   the tools an action-channel dispatcher executes (from the action field only)
  --check    the text scanner executes a deferred destructive tool from the reasoning; the action channel executes only the committed call

reasoning, mentioned_tools, action, and destructive_tools are the fixture; what each dispatcher executes is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "thinkexec.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def scan_dispatch(data):
    """BUG: extract tool calls by scanning all the model's output, reasoning included."""
    executed = list(data["mentioned_tools"])      # every tool named anywhere, including in reasoning
    if data["action"]["tool"] not in executed:
        executed.append(data["action"]["tool"])
    return executed


def action_dispatch(data):
    """FIX: execute only the call committed in the structured action channel."""
    return [data["action"]["tool"]]


def destructive_executed(executed, data):
    """Which executed tools are irreversible."""
    return [t for t in executed if t in data["destructive_tools"]]


# ----------------------------------------------------------------- printing

def scan_view(data):
    ex = scan_dispatch(data)
    print("SCAN — a dispatcher that pattern-matches the model's whole output")
    print("-" * 56)
    print("  reasoning : %s" % data["reasoning"])
    print("  executed  : %s" % ex)
    print("  destructive among them: %s" % destructive_executed(ex, data))
    print("-" * 56)
    print("  it ran %s, which the model only considered and then deferred" % destructive_executed(ex, data))


def action_view(data):
    ex = action_dispatch(data)
    print("ACTION — a dispatcher that runs only the committed action channel")
    print("-" * 56)
    print("  action field: %s" % data["action"])
    print("  executed    : %s" % ex)
    print("  destructive among them: %s" % destructive_executed(ex, data))
    print("-" * 56)
    print("  it ran only the call the model actually decided on")


def check(data):
    print("SELF-TEST — the text scanner executes a deferred destructive tool from the reasoning; the action channel executes only the committed call")
    print("-" * 112)
    scan = scan_dispatch(data)
    act = action_dispatch(data)
    committed = data["action"]["tool"]

    reasoning_mentions_destructive = any(t in data["destructive_tools"] for t in data["mentioned_tools"])
    print("  the reasoning mentions a destructive tool = %s (%s)" % (reasoning_mentions_destructive, [t for t in data["mentioned_tools"] if t in data["destructive_tools"]]))

    committed_is_not_destructive = committed not in data["destructive_tools"]
    print("  the committed action is NOT that destructive tool = %s (committed %s)" % (committed_is_not_destructive, committed))

    scan_runs_destructive = len(destructive_executed(scan, data)) > 0
    print("  the text scanner executes the destructive tool = %s (%s)" % (scan_runs_destructive, destructive_executed(scan, data)))

    action_runs_only_committed = act == [committed]
    print("  the action-channel dispatcher runs only the committed call = %s (%s)" % (action_runs_only_committed, act))

    action_runs_nothing_destructive = len(destructive_executed(act, data)) == 0
    print("  the action-channel dispatcher runs nothing destructive = %s" % action_runs_nothing_destructive)

    ok = (reasoning_mentions_destructive and committed_is_not_destructive and scan_runs_destructive
          and action_runs_only_committed and action_runs_nothing_destructive)
    print("-" * 112)
    print("SELF-TEST %s  reasoning_mentions_destructive=%s  committed_is_not_destructive=%s  scan_runs_destructive=%s  action_runs_only_committed=%s  action_runs_nothing_destructive=%s"
          % ("PASS" if ok else "FAIL", reasoning_mentions_destructive, committed_is_not_destructive, scan_runs_destructive,
             action_runs_only_committed, action_runs_nothing_destructive))
    return ok


def main():
    p = argparse.ArgumentParser(description="Reasoning vs action channel: execute tool calls only from the structured action channel, never from the model's reasoning text, because the chain-of-thought names tools the model is only considering -- a harness that scans it will run a tool the model deferred, including a destructive one.")
    p.add_argument("--scan", action="store_true")
    p.add_argument("--action", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("action=%s  mentioned=%s  file=%s  (these are a fixture)"
          % (data["action"], data["mentioned_tools"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.scan:
        scan_view(data)
    elif args.action:
        action_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
