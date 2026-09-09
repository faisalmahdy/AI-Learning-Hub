"""Validate a proposed tool call against the tool's schema before dispatching -- the model's arguments are not trusted input.

An agent lets a language model call tools by emitting a tool name and a JSON object of arguments. That JSON is generated
text, not a checked function call: the model can omit a required argument, give an argument the wrong type, invent an
argument the tool does not have, or supply a value outside the allowed set. A well-typed program never has these problems
because the compiler enforces the signature; an agent has no such enforcement between the model and the tool unless the
harness adds it. Dispatch the model's arguments straight to the tool and a bad call reaches real code: a missing required
field raises a KeyError deep inside the tool, a string where an int was expected crashes the arithmetic or -- worse --
silently coerces and does the wrong thing, an invented argument is either ignored (so the call does something other than
the model intended) or rejected with an opaque stack trace, and an out-of-range enum value drives an illegal branch. The
failure surfaces far from its cause, as a tool crash rather than a bad call.

The fix is to validate every proposed call against the tool's declared schema BEFORE dispatching it. The schema states
each parameter's type, whether it is required, and any enum of allowed values; validation checks the proposed arguments
against that and either passes the call through or returns a STRUCTURED error -- 'missing required arg city', 'arg days
must be int' -- as the observation. That error is doubly useful: it stops the malformed call from ever touching the tool,
and it tells the MODEL exactly what was wrong, so the next turn can produce a corrected call. Validation turns an
untrusted blob of generated JSON into either a well-formed call or an actionable error, which is the boundary every tool
dispatch needs, the same discipline a web server applies to request bodies.

On this fixture the tool get_weather requires a string city, takes an optional units in the enum ['c','f'], and an
optional integer days. Five proposed calls are checked: the valid one passes; the others each trip a different rule --
missing the required city, a string 'three' where days must be an int, an invented 'country' argument, and 'kelvin'
outside the units enum. An unvalidated harness would send all five to the tool; the validated harness dispatches only the
first and returns a precise error for each of the other four. This computes both.

  --validate  each proposed call checked against the schema, pass or fail with the specific reason
  --dispatch  unvalidated (all five reach the tool) vs validated (only the valid call dispatches, four become errors)
  --check     the valid call passes; a missing required, wrong type, unknown arg, and bad enum are each caught

The schema and proposed calls are the fixture; which calls pass and why each fails are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "toolargs.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def type_ok(value, declared):
    """Does the value match the declared type? (json ints load as int, strings as str)."""
    if declared == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "str":
        return isinstance(value, str)
    return True


def validate(schema, args):
    """Check args against the schema; return (ok, reason). The order mirrors how a call is malformed."""
    params = schema["params"]
    for name, spec in params.items():
        if spec.get("required") and name not in args:
            return False, "missing required arg '%s'" % name
    for name in args:
        if name not in params:
            return False, "unknown arg '%s'" % name
    for name, value in args.items():
        spec = params[name]
        if not type_ok(value, spec["type"]):
            return False, "arg '%s' must be %s, got %r" % (name, spec["type"], value)
        if "enum" in spec and value not in spec["enum"]:
            return False, "arg '%s'=%r not in enum %s" % (name, value, spec["enum"])
    return True, "ok"


# ----------------------------------------------------------------- printing

def validate_view(data):
    schema = data["schema"]
    print("VALIDATE — each proposed call checked against the %s schema" % schema["name"])
    print("-" * 72)
    for call in data["proposed_calls"]:
        ok, reason = validate(schema, call["args"])
        print("  %-16s %-42s %s" % (call["label"], json.dumps(call["args"]), "PASS" if ok else "REJECT: " + reason))
    print("-" * 72)


def dispatch_view(data):
    schema = data["schema"]
    calls = data["proposed_calls"]
    print("DISPATCH — unvalidated (trust the model) vs validated (check first)")
    print("-" * 72)
    print("  UNVALIDATED: all %d calls are sent to the tool --" % len(calls))
    for call in calls:
        ok, reason = validate(schema, call["args"])
        note = "would run" if ok else "reaches tool as a bug (%s)" % reason
        print("    %-16s -> %s" % (call["label"], note))
    print("  VALIDATED: only well-formed calls dispatch; the rest become error observations --")
    dispatched = [c["label"] for c in calls if validate(schema, c["args"])[0]]
    for call in calls:
        ok, _ = validate(schema, call["args"])
        print("    %-16s -> %s" % (call["label"], "DISPATCH" if ok else "error observation (not run)"))
    print("-" * 72)
    print("  dispatched: %s -- the four malformed calls never touch the tool." % dispatched)


def check(data):
    print("SELF-TEST — the valid call passes; a missing required, wrong type, unknown arg, and bad enum are each caught")
    print("-" * 108)
    schema = data["schema"]
    by_label = {c["label"]: c["args"] for c in data["proposed_calls"]}

    valid_passes = validate(schema, by_label["valid"])[0]
    print("  the well-formed call passes validation = %s" % valid_passes)

    ok, reason = validate(schema, by_label["missing_required"])
    missing_caught = not ok and "missing required" in reason
    print("  a missing required arg is rejected = %s (%s)" % (missing_caught, reason))

    ok, reason = validate(schema, by_label["wrong_type"])
    type_caught = not ok and "must be int" in reason
    print("  a wrong-typed arg is rejected = %s (%s)" % (type_caught, reason))

    ok, reason = validate(schema, by_label["unknown_arg"])
    unknown_caught = not ok and "unknown arg" in reason
    print("  an invented (unknown) arg is rejected = %s (%s)" % (unknown_caught, reason))

    ok, reason = validate(schema, by_label["bad_enum"])
    enum_caught = not ok and "not in enum" in reason
    print("  an out-of-enum value is rejected = %s (%s)" % (enum_caught, reason))

    ok_all = valid_passes and missing_caught and type_caught and unknown_caught and enum_caught
    print("-" * 108)
    print("SELF-TEST %s  valid_passes=%s  missing_caught=%s  type_caught=%s  unknown_caught=%s  enum_caught=%s"
          % ("PASS" if ok_all else "FAIL", valid_passes, missing_caught, type_caught, unknown_caught, enum_caught))
    return ok_all


def main():
    p = argparse.ArgumentParser(description="Tool-argument validation: a model's proposed tool-call arguments are untrusted generated JSON, so the harness must validate them against the tool's schema (required fields, types, enums) before dispatch; an unvalidated bad call crashes or misbehaves in the tool, while validation rejects it and returns a structured error the model can correct from.")
    p.add_argument("--validate", action="store_true")
    p.add_argument("--dispatch", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tool=%s  params=%s  proposed_calls=%d  file=%s  (the schema and calls are a fixture)"
          % (data["schema"]["name"], list(data["schema"]["params"]), len(data["proposed_calls"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.validate:
        validate_view(data)
    elif args.dispatch:
        dispatch_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
