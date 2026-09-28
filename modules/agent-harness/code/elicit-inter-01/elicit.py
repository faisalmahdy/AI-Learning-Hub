"""Ask when a required argument is missing -- guessing a default and dispatching commits a confidently wrong action.

An agent turns a user's request into a tool call, and the request does not always contain everything the tool needs. 'Book
me a flight to New York' names a destination but not a date; 'delete the old logs' names an action but not which logs or how
old. The tool has REQUIRED parameters, and one of them is unspecified. The agent now faces a fork, and the wrong branch is
seductive because it keeps things moving: fill the missing parameter with a guess -- a default, today's date, the most
common value, whatever the model finds plausible -- and dispatch the tool anyway. The request is satisfied, superficially,
and nothing errored. But the agent has just committed an action the user never actually specified: it booked a flight for a
date the user did not choose, deleted logs by a threshold the user did not set. When the action is irreversible or costly
(a booking, a payment, a deletion, an email), a guessed parameter is not a small inaccuracy -- it is doing the wrong thing
with full confidence, and the user finds out only after it is done.

The correct behavior is ELICITATION: when a required parameter cannot be filled from the request (or from unambiguous
context), the agent should ASK the user a clarifying question that names the missing parameter, and NOT dispatch the tool
until it has an answer. This trades a round-trip of latency for correctness, and it is almost always the right trade for a
consequential action -- a question is cheap and reversible, a wrong booking is neither. The skill is knowing WHICH gaps to
elicit: a truly required parameter with no safe default must be asked; a parameter with a sensible, stated default (and a
low-stakes, reversible action) can be defaulted. The failure this module is about is defaulting a genuinely required
parameter of a consequential tool and calling it done.

The tell that separates guessing from knowing is provenance: a guessed value is one that did NOT come from the user's
request. An agent that fills 'date' with 'today' when the user never said 'today' has fabricated the value, and the honest
thing to do with a fabricated required value is not to act on it but to ask.

The rule: before dispatching a tool, check that every required parameter is actually supplied by the request (or safe,
stated context); if a required parameter is missing, elicit -- ask the user a question naming the gap -- rather than filling
it with a guessed default and dispatching, because a fabricated required argument turns 'helpful' into a confidently wrong,
possibly irreversible action the user never asked for.

On this fixture book_flight requires origin, destination, and date; the request supplied origin and destination but not
date. The guess-and-dispatch agent fills date with 'today' (a value never in the request) and dispatches a booking; the
eliciting agent detects the missing date, asks for it, and dispatches nothing. This computes both.

  --slots     the required parameters, which were provided, which are missing, and what a guess would fabricate
  --dispatch  what each agent does: guess dispatches book_flight with a fabricated date; elicit asks and dispatches nothing
  --check     the required date is missing; guessing fabricates and dispatches, while eliciting asks and withholds the call

tool, required_params, provided, and guess_defaults are the fixture; every detection, fabrication, and decision is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "elicit.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def missing_required(required, provided):
    """The required parameters the request did not supply."""
    return [p for p in required if p not in provided]


def run_guess(data):
    """Fill each missing required parameter from the guess defaults and dispatch the tool."""
    args = dict(data["provided"])
    fabricated = {}
    for p in missing_required(data["required_params"], data["provided"]):
        args[p] = data["guess_defaults"].get(p, "?")
        fabricated[p] = args[p]
    return {"action": "dispatch", "tool": data["tool"], "args": args, "fabricated": fabricated}


def run_elicit(data):
    """If a required parameter is missing, ask for it and dispatch nothing."""
    missing = missing_required(data["required_params"], data["provided"])
    if missing:
        return {"action": "ask", "question": "Which %s? (required, not specified)" % ", ".join(missing), "tool": None}
    return {"action": "dispatch", "tool": data["tool"], "args": dict(data["provided"]), "fabricated": {}}


# ----------------------------------------------------------------- printing

def slots_view(data):
    required, provided = data["required_params"], data["provided"]
    missing = missing_required(required, provided)
    print("SLOTS — required parameters of %s vs what the request supplied" % data["tool"])
    print("-" * 62)
    for p in required:
        if p in provided:
            print("  %-12s provided: %r" % (p, provided[p]))
        else:
            print("  %-12s MISSING  (a guess would fabricate %r)" % (p, data["guess_defaults"].get(p, "?")))
    print("-" * 62)
    print("  missing required: %s" % missing)


def dispatch_view(data):
    g = run_guess(data)
    e = run_elicit(data)
    print("DISPATCH — what each agent does with the missing 'date'")
    print("-" * 66)
    print("  GUESS-AND-DISPATCH:")
    print("    action: %s %s(%s)" % (g["action"], g["tool"], ", ".join("%s=%r" % kv for kv in g["args"].items())))
    print("    fabricated (never in the request): %s" % g["fabricated"])
    print("  ELICIT:")
    print("    action: %s -> %r" % (e["action"], e.get("question")))
    print("    tool dispatched: %s" % e["tool"])
    print("-" * 66)
    print("  guessing books a flight on a date the user never chose; eliciting asks first.")


def check(data):
    print("SELF-TEST — the required date is missing; guessing fabricates and dispatches, eliciting asks and withholds the call")
    print("-" * 116)
    required, provided = data["required_params"], data["provided"]
    missing = missing_required(required, provided)
    g = run_guess(data)
    e = run_elicit(data)

    required_slot_missing = "date" in missing
    print("  a required parameter is missing from the request = %s (missing: %s)" % (required_slot_missing, missing))

    guess_fabricates = "date" in g["fabricated"] and g["fabricated"]["date"] not in provided.values()
    print("  guess fabricates the missing value (not from the request) = %s (date=%r)" % (guess_fabricates, g["fabricated"].get("date")))

    guess_dispatches = g["action"] == "dispatch"
    print("  guess dispatches the tool anyway = %s (%s)" % (guess_dispatches, g["tool"]))

    elicit_asks = e["action"] == "ask" and "date" in e["question"]
    print("  elicit asks a question naming the gap = %s (%r)" % (elicit_asks, e.get("question")))

    elicit_no_dispatch = e["tool"] is None
    print("  elicit dispatches no tool until answered = %s" % elicit_no_dispatch)

    ok = required_slot_missing and guess_fabricates and guess_dispatches and elicit_asks and elicit_no_dispatch
    print("-" * 116)
    print("SELF-TEST %s  required_slot_missing=%s  guess_fabricates=%s  guess_dispatches=%s  elicit_asks=%s  elicit_no_dispatch=%s"
          % ("PASS" if ok else "FAIL", required_slot_missing, guess_fabricates, guess_dispatches, elicit_asks, elicit_no_dispatch))
    return ok


def main():
    p = argparse.ArgumentParser(description="Elicitation: before dispatching a tool, check that every required parameter is actually supplied by the request (or safe context); if one is missing, ask the user a question naming the gap rather than filling it with a guessed default and dispatching, because a fabricated required argument turns 'helpful' into a confidently wrong, possibly irreversible action the user never asked for.")
    p.add_argument("--slots", action="store_true")
    p.add_argument("--dispatch", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tool=%s  required=%s  provided=%s  file=%s  (the tool schema and request are a fixture)"
          % (data["tool"], data["required_params"], data["provided"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.slots:
        slots_view(data)
    elif args.dispatch:
        dispatch_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
