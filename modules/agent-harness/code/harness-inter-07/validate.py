"""Validate a tool call against its schema before executing -- or a malformed call fails opaquely.

A model proposes tool calls as free-form structured text: a tool name and a bag of arguments.
Nothing guarantees they are well-formed. The name might not be a real tool, a required argument
might be missing, an argument might be the wrong type, or there might be an extra argument the
tool does not expect. The tempting harness executes whatever it is handed and lets the tool sort
it out -- and that fails in the worst way, because the error surfaces deep inside the tool as a
crash or, worse, the tool half-runs on garbage and does the wrong thing, with an error message
that says nothing the model can act on.

A validating harness checks each call against the tool's schema first -- known tool, all required
arguments present, every argument the right type, no unexpected arguments -- and rejects a bad
call before it runs, with a specific reason the model can read and fix ('missing required
argument limit', 'argument body should be str, got int'). Of six proposed calls here, one is
well-formed and five are malformed in five different ways; the naive harness executes all six and
the five bad ones fail at the tool, while the validating harness executes only the one good call
and returns five precise rejections. This checks both and shows the malformed calls stopped at
the boundary.

  --schemas    the tool schemas, and each proposed call's validation result and reason
  --run        the calls the naive harness executes vs the calls the validating harness executes
  --check      validation catches every malformed call before execution; only the valid call runs

The tool schemas and proposed calls are the fixture; every validation is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "calls.json"

TYPES = {"str": str, "int": int, "bool": bool, "float": (int, float)}


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ------------------------------------------------------------- validation

def validate(call, schemas):
    """Return None if the call is well-formed, else a specific reason it is rejected."""
    name, args = call["tool"], call["args"]
    if name not in schemas:
        return "unknown tool %r" % name
    spec = schemas[name]
    for param, typ in spec.items():
        if param not in args:
            return "missing required argument %r" % param
        if not isinstance(args[param], TYPES[typ]) or (typ != "bool" and isinstance(args[param], bool)):
            return "argument %r should be %s, got %s" % (param, typ, type(args[param]).__name__)
    for param in args:
        if param not in spec:
            return "unexpected argument %r" % param
    return None


def is_valid(call, schemas):
    return validate(call, schemas) is None


# ------------------------------------------------------------- the two harnesses

def naive_executes(calls, schemas):
    """The bug: execute every proposed call; the malformed ones fail at the tool."""
    return [c["id"] for c in calls]


def validated_executes(calls, schemas):
    """The fix: execute only the calls that pass validation."""
    return [c["id"] for c in calls if is_valid(c, schemas)]


# ----------------------------------------------------------------- printing

def schemas_view(data):
    schemas = data["schemas"]
    print("SCHEMAS — %d tools; each proposed call validated before execution" % len(schemas))
    print("-" * 68)
    for name, spec in schemas.items():
        print("  tool %-12s (%s)" % (name, ", ".join("%s:%s" % (p, t) for p, t in spec.items())))
    print("-" * 68)
    print("  id    tool          result   reason")
    for c in data["calls"]:
        reason = validate(c, schemas)
        print("  %-5s %-13s %-8s %s" % (c["id"], c["tool"], "OK" if reason is None else "REJECT", reason or ""))


def run_view(data):
    calls, schemas = data["calls"], data["schemas"]
    naive = naive_executes(calls, schemas)
    valid = validated_executes(calls, schemas)
    bad = [c["id"] for c in calls if not is_valid(c, schemas)]
    print("RUN — naive (execute all) vs validating (execute only well-formed)")
    print("-" * 68)
    print("  naive executes:      %s   (of which malformed: %s)" % (naive, bad))
    print("  validating executes: %s" % valid)
    print("-" * 68)
    print("  the naive harness sends %d malformed calls to the tools; the validating one sends 0." % len(bad))


def check(data):
    print("SELF-TEST — validation catches every malformed call before execution; only the valid call runs")
    print("-" * 70)
    calls, schemas = data["calls"], data["schemas"]

    malformed = [c["id"] for c in calls if not is_valid(c, schemas)]
    valid = [c["id"] for c in calls if is_valid(c, schemas)]

    naive_runs_malformed = set(malformed).issubset(set(naive_executes(calls, schemas)))
    print("  the naive harness executes the malformed calls = %s (%s)" % (naive_runs_malformed, malformed))

    validated_blocks_all = len(set(validated_executes(calls, schemas)) & set(malformed)) == 0
    print("  the validating harness executes NONE of the malformed calls = %s" % validated_blocks_all)

    only_valid_runs = validated_executes(calls, schemas) == valid and len(valid) > 0
    print("  the validating harness executes exactly the well-formed calls = %s (%s)" % (only_valid_runs, valid))

    # the rejections name distinct, specific failure kinds
    reasons = [validate(c, schemas) for c in calls if not is_valid(c, schemas)]
    kinds = {r.split()[0] + " " + r.split()[1] for r in reasons}
    specific_reasons = len(kinds) >= 3
    print("  the rejections give specific, distinct reasons = %s (%d kinds)" % (specific_reasons, len(kinds)))

    ok = naive_runs_malformed and validated_blocks_all and only_valid_runs and specific_reasons
    print("-" * 70)
    print("SELF-TEST %s  naive_runs_malformed=%s  validated_blocks_all=%s  only_valid_runs=%s  specific_reasons=%s"
          % ("PASS" if ok else "FAIL", naive_runs_malformed, validated_blocks_all, only_valid_runs, specific_reasons))
    return ok


def main():
    p = argparse.ArgumentParser(description="Validate tool calls against their schema before executing.")
    p.add_argument("--schemas", action="store_true")
    p.add_argument("--run", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("tools=%d  calls=%d  file=%s  (schemas and proposed calls are a fixture)"
          % (len(data["schemas"]), len(data["calls"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.schemas:
        schemas_view(data)
    elif args.run:
        run_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
