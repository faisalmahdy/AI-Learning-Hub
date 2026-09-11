"""Gate irreversible tool calls behind confirmation -- run reversible ones freely, but never let the model delete or send without a human in the loop.

An agent harness executes the tool calls the model proposes, and the model is wrong often enough that executing all of them unconditionally is a liability. For most tools that is fine: a read, a search, a list can be retried, ignored, or undone, so running one the model should not have is cheap. But some tools have effects you cannot take back -- deleting a file, sending an email, transferring money, deploying to production -- and for those, a single wrong call is not a cheap mistake, it is an incident. Treating a delete like a read, executing it the instant the model asks, means the model's every hallucinated filename or misread instruction becomes an irreversible action.

The distinction that matters is reversibility, not the tool's apparent importance. A tool is safe to auto-run if its effect can be undone or if running it needlessly costs nothing; it needs a gate if its effect is permanent. So the harness should classify each proposed call: reversible calls execute automatically, keeping the agent fast and low-friction on the vast majority of its work, while irreversible calls are HELD -- surfaced for explicit confirmation (a human approves, or a dry-run shows exactly what would happen) before they run. The gate is not on the model's confidence or the argument values; it is on the category of action, because you cannot trust the model to know when it is about to do something unrecoverable.

The payoff is that the number of irreversible actions taken without a human in the loop drops to zero, while the friction of confirmation falls only on the small slice of calls that actually warrant it. You are not slowing the agent down across the board -- reads and searches still flow -- you are inserting a checkpoint exactly where a mistake cannot be undone. And the gate is a property of the harness, not the prompt: it holds even if the model is jailbroken, confused, or manipulated by injected instructions, because the harness refuses to execute an irreversible call without approval regardless of how confidently the model requested it.

The rule: classify each proposed tool call by reversibility and gate the irreversible ones behind explicit confirmation while auto-running the reversible ones, rather than executing every call the model proposes, because irreversible actions (delete, send, transfer, deploy) cannot be undone if the model is wrong -- so a harness-level confirmation checkpoint on exactly those calls prevents unrecoverable mistakes without adding friction to the safe majority.

On this fixture the model proposes four calls: two reversible (list_files, read_file) and two irreversible (delete_file, send_email). The naive harness runs all four, executing two irreversible actions with no confirmation; the gated harness auto-runs the two reversible calls and holds the two irreversible ones, so zero irreversible actions happen unconfirmed. This computes both.

  --calls     each proposed call, whether it is reversible, and how each policy handles it
  --gate      naive (run all) vs gated (auto-run reversible, hold irreversible): what executes and what waits
  --check     the naive harness runs irreversible calls unconfirmed; gating holds them while still auto-running the safe ones

tools and proposed_calls are the fixture; every classification, execution set, and unconfirmed-irreversible count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "confirmgate.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def reversible(tool, tools):
    return tools[tool]["reversible"]


def naive_execute(calls, tools):
    """Naive harness: execute every proposed call immediately."""
    return {"executed": list(calls), "held": []}


def gated_execute(calls, tools):
    """Gated harness: auto-run reversible calls, hold irreversible ones for confirmation."""
    executed = [c for c in calls if reversible(c, tools)]
    held = [c for c in calls if not reversible(c, tools)]
    return {"executed": executed, "held": held}


def unconfirmed_irreversible(result, tools):
    """How many irreversible calls this policy executed without confirmation."""
    return sum(1 for c in result["executed"] if not reversible(c, tools))


# ----------------------------------------------------------------- printing

def calls_view(data):
    tools, calls = data["tools"], data["proposed_calls"]
    print("CALLS — each proposed call, reversibility, and per-policy handling")
    print("-" * 66)
    print("  call          reversible   naive       gated")
    for c in calls:
        rev = reversible(c, tools)
        print("  %-12s  %-11s  %-10s  %s" % (c, rev, "execute", "execute" if rev else "HOLD (confirm)"))
    print("-" * 66)
    print("  the gate keys on reversibility, not on the model's confidence")


def gate_view(data):
    tools, calls = data["tools"], data["proposed_calls"]
    n = naive_execute(calls, tools)
    g = gated_execute(calls, tools)
    print("GATE — naive (run all) vs gated (hold irreversible)")
    print("-" * 62)
    print("  naive: executed %s ; held %s" % (n["executed"], n["held"] or "none"))
    print("         irreversible run WITHOUT confirmation: %d" % unconfirmed_irreversible(n, tools))
    print("  gated: executed %s ; held %s" % (g["executed"], g["held"]))
    print("         irreversible run WITHOUT confirmation: %d" % unconfirmed_irreversible(g, tools))
    print("-" * 62)
    print("  gating held %d irreversible call(s) for approval; the safe calls still ran" % len(g["held"]))


def check(data):
    print("SELF-TEST — the naive harness runs irreversible calls unconfirmed; gating holds them while still auto-running the safe ones")
    print("-" * 124)
    tools, calls = data["tools"], data["proposed_calls"]
    n = naive_execute(calls, tools)
    g = gated_execute(calls, tools)
    irreversible_calls = [c for c in calls if not reversible(c, tools)]
    reversible_calls = [c for c in calls if reversible(c, tools)]

    has_irreversible = len(irreversible_calls) > 0
    print("  the batch contains irreversible calls = %s (%s)" % (has_irreversible, irreversible_calls))

    naive_runs_irreversible = unconfirmed_irreversible(n, tools) > 0
    print("  the naive harness runs irreversible calls without confirmation = %s (%d)" % (naive_runs_irreversible, unconfirmed_irreversible(n, tools)))

    gated_holds_all_irreversible = set(g["held"]) == set(irreversible_calls)
    print("  gating holds every irreversible call for confirmation = %s (%s)" % (gated_holds_all_irreversible, g["held"]))

    gated_zero_unconfirmed = unconfirmed_irreversible(g, tools) == 0
    print("  gating executes zero irreversible calls unconfirmed = %s" % gated_zero_unconfirmed)

    gated_runs_safe = set(g["executed"]) == set(reversible_calls)
    print("  gating still auto-runs the reversible (safe) calls = %s (%s)" % (gated_runs_safe, g["executed"]))

    friction_only_on_irreversible = len(g["held"]) == len(irreversible_calls) and len(g["held"]) < len(calls)
    print("  confirmation friction falls only on the irreversible minority = %s (%d of %d)" % (friction_only_on_irreversible, len(g["held"]), len(calls)))

    ok = (has_irreversible and naive_runs_irreversible and gated_holds_all_irreversible and gated_zero_unconfirmed
          and gated_runs_safe and friction_only_on_irreversible)
    print("-" * 124)
    print("SELF-TEST %s  has_irreversible=%s  naive_runs_irreversible=%s  gated_holds_all_irreversible=%s  gated_zero_unconfirmed=%s  gated_runs_safe=%s  friction_only_on_irreversible=%s"
          % ("PASS" if ok else "FAIL", has_irreversible, naive_runs_irreversible, gated_holds_all_irreversible, gated_zero_unconfirmed, gated_runs_safe, friction_only_on_irreversible))
    return ok


def main():
    p = argparse.ArgumentParser(description="Confirmation gating: classify each proposed tool call by reversibility and gate the irreversible ones behind explicit confirmation while auto-running the reversible ones, rather than executing every call the model proposes, because irreversible actions (delete, send, transfer, deploy) cannot be undone if the model is wrong -- so a harness-level confirmation checkpoint on exactly those calls prevents unrecoverable mistakes without adding friction to the safe majority.")
    p.add_argument("--calls", action="store_true")
    p.add_argument("--gate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tools=%d  proposed_calls=%d  file=%s  (the tools and proposed calls are a fixture)"
          % (len(data["tools"]), len(data["proposed_calls"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.calls:
        calls_view(data)
    elif args.gate:
        gate_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
