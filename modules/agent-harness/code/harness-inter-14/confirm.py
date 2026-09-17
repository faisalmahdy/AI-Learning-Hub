"""Gate the irreversible tools for confirmation, not every tool and not none -- reversibility is the line.

An agent's tools are not equally dangerous. Reading a file, listing a directory, updating a record you can
un-update -- if the agent gets these wrong, you fix them and move on. Deleting a record with no backup,
sending an email, charging a card -- get these wrong and there is no undo. A harness that runs every tool
automatically will, sooner or later, fire an irreversible action the user never saw coming: the agent
deletes the wrong rows or emails the wrong list, and the mistake is permanent. Auto-running everything
treats a DELETE like a SELECT.

The opposite over-correction is to confirm every single tool call. That is safe but unusable: the user is
prompted to approve reading a file, listing a directory, every trivial step, and confirmation fatigue sets
in -- people click 'yes' reflexively, which defeats the gate exactly when it finally matters. The right
policy gates on the property that actually distinguishes the dangerous calls: reversibility. Auto-run the
read-only and reversible tools; hold only the irreversible ones for an explicit confirmation. The user is
asked precisely when it counts and never when it doesn't, so the prompts stay rare and meaningful.

On this fixture a run issues 6 tool calls: 3 reads, 1 reversible write, and 2 irreversible actions (a
delete and an email). Auto-run executes all 6, firing both irreversible actions with no confirmation.
Confirm-everything holds all 6, prompting 6 times. Gate-by-reversibility auto-runs the 4 safe calls and
holds only the 2 irreversible ones -- zero unconfirmed destructive actions, and just 2 prompts. This
computes all three.

  --run        each tool call's effect class and what each policy does with it
  --tally      unconfirmed destructive actions and prompt counts per policy
  --check      auto fires destructive actions unconfirmed; gating only the irreversible ones is safe and quiet

The tool effect classes and the run are the fixture; every decision is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "tools.json"

IRREVERSIBLE = "irreversible"
SAFE = {"read", "reversible"}


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def effect(call, tools):
    return tools[call]


def decide(call, tools, policy):
    """Return 'run' (executed automatically) or 'confirm' (held for user approval)."""
    e = effect(call, tools)
    if policy == "auto":
        return "run"
    if policy == "confirm-all":
        return "confirm"
    if policy == "gate-irreversible":
        return "confirm" if e == IRREVERSIBLE else "run"
    raise ValueError(policy)


def outcomes(run, tools, policy):
    return [(c, effect(c, tools), decide(c, tools, policy)) for c in run]


def unconfirmed_destructive(run, tools, policy):
    """Irreversible actions that executed without confirmation -- the ones that can't be undone."""
    return [c for c, e, d in outcomes(run, tools, policy) if e == IRREVERSIBLE and d == "run"]


def prompts(run, tools, policy):
    return [c for c, e, d in outcomes(run, tools, policy) if d == "confirm"]


def auto_ran_safe(run, tools, policy):
    return [c for c, e, d in outcomes(run, tools, policy) if e in SAFE and d == "run"]


POLICIES = ["auto", "confirm-all", "gate-irreversible"]


# ----------------------------------------------------------------- printing

def run_view(data):
    run, tools = data["run"], data["tools"]
    print("RUN — each tool call's effect and each policy's decision")
    print("-" * 66)
    print("  call            effect         auto     confirm-all  gate-irrev")
    for c in run:
        e = effect(c, tools)
        cells = [decide(c, tools, p) for p in POLICIES]
        print("  %-14s  %-13s  %-7s  %-11s  %s" % (c, e, cells[0], cells[1], cells[2]))
    print("-" * 66)
    print("  gate-irrev runs the safe calls and confirms only the irreversible ones.")


def tally_view(data):
    run, tools = data["run"], data["tools"]
    print("TALLY — unconfirmed destructive actions and prompt count per policy")
    print("-" * 66)
    print("  policy              unconfirmed destructive   prompts")
    for p in POLICIES:
        print("  %-18s  %-23d  %d" % (p, len(unconfirmed_destructive(run, tools, p)), len(prompts(run, tools, p))))
    print("-" * 66)
    print("  auto is unsafe (fires destructive); confirm-all is noisy; gate-irrev is both safe and quiet.")


def check(data):
    print("SELF-TEST — auto fires destructive actions unconfirmed; gating only the irreversible ones is safe and quiet")
    print("-" * 108)
    run, tools = data["run"], data["tools"]

    auto_fires_destructive = len(unconfirmed_destructive(run, tools, "auto")) > 0
    print("  auto-run fires irreversible actions with no confirmation = %s (%s)"
          % (auto_fires_destructive, unconfirmed_destructive(run, tools, "auto")))

    gate_holds_destructive = len(unconfirmed_destructive(run, tools, "gate-irreversible")) == 0
    print("  gate-irreversible lets no irreversible action run unconfirmed = %s" % gate_holds_destructive)

    gate_runs_safe = auto_ran_safe(run, tools, "gate-irreversible") == auto_ran_safe(run, tools, "auto")
    print("  gate-irreversible still auto-runs every safe call = %s (%d safe)"
          % (gate_runs_safe, len(auto_ran_safe(run, tools, "gate-irreversible"))))

    gate_fewer_prompts = len(prompts(run, tools, "gate-irreversible")) < len(prompts(run, tools, "confirm-all"))
    print("  gate-irreversible prompts less than confirm-all = %s (%d vs %d)"
          % (gate_fewer_prompts, len(prompts(run, tools, "gate-irreversible")), len(prompts(run, tools, "confirm-all"))))

    gate_prompts_are_the_destructive_ones = set(prompts(run, tools, "gate-irreversible")) == {c for c in run if effect(c, tools) == IRREVERSIBLE}
    print("  the prompts are exactly the irreversible calls = %s (%s)" % (gate_prompts_are_the_destructive_ones, prompts(run, tools, "gate-irreversible")))

    ok = auto_fires_destructive and gate_holds_destructive and gate_runs_safe and gate_fewer_prompts and gate_prompts_are_the_destructive_ones
    print("-" * 108)
    print("SELF-TEST %s  auto_fires_destructive=%s  gate_holds_destructive=%s  gate_runs_safe=%s  gate_fewer_prompts=%s  prompts_are_destructive=%s"
          % ("PASS" if ok else "FAIL", auto_fires_destructive, gate_holds_destructive, gate_runs_safe, gate_fewer_prompts, gate_prompts_are_the_destructive_ones))
    return ok


def main():
    p = argparse.ArgumentParser(description="Gate irreversible tools for confirmation, not every tool and not none.")
    p.add_argument("--run", action="store_true")
    p.add_argument("--tally", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("calls=%d  tools=%d  file=%s  (the effect classes and run are a fixture)"
          % (len(data["run"]), len(data["tools"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.run:
        run_view(data)
    elif args.tally:
        tally_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
