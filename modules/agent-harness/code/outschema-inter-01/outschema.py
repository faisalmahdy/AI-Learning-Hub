"""Validate the agent's FINAL answer against its output schema and feed the error back -- returning the first answer ships garbage.

A tool-calling agent's loop is usually careful about the calls going INTO tools -- it validates the model's proposed
arguments against each tool's schema before dispatching. It is often careless about the value coming OUT: the final
answer the harness returns to whatever called the agent. When a caller depends on a STRUCTURED result -- a JSON object
with specific fields and types, because a downstream service or UI will read it programmatically -- the model's first
attempt is frequently not that. It writes a sentence of prose where an object was promised, or emits JSON that is missing
a required field, or gets a type wrong. A harness that simply returns the model's first response hands the caller that
malformed answer, and the failure surfaces far downstream (a KeyError in the service, a blank field in the UI, a silently
wrong number) where it is expensive to trace back to 'the agent didn't actually answer in the required shape'.

The fix mirrors what we already do for tool inputs, applied to the output: validate the final answer against the output
schema before returning it, and when it fails, do not just retry blindly -- feed the SPECIFIC validation error back to the
model as an observation ('missing required field: currency') so its next attempt is a targeted repair, not another guess.
This turns a one-shot 'hope it's shaped right' into a bounded repair loop: parse, check required fields and their types,
and on failure return a precise message the model can act on, up to a small repair budget so a model that can never
produce the shape fails loudly instead of looping forever. The specificity of the feedback is the point -- 'invalid
output' teaches the model nothing, while 'missing required field: currency (have: total)' tells it exactly what to add.

The rule: the agent's final structured answer is untrusted output the same way a proposed tool call is untrusted input, so
validate it against the declared output schema before returning it, and on failure feed back the specific error for a
bounded repair loop -- an unvalidated answer that merely 'looks done' is how malformed results leak past the harness into
the caller, where the schema was supposed to be a contract.

On this fixture the model produces three answers in turn: prose (not JSON), then JSON missing the required 'currency',
then a valid object. Without validation the harness returns the prose -- garbage against the schema. With validation it
rejects the prose (not parseable), rejects the partial object (missing currency, and the error says so by name), and
accepts the third on repair attempt 3. This computes both.

  --answers   each candidate answer, whether it passes the output schema, and the specific error -- and what each harness returns
  --repair    the repair loop step by step: the model's answer, the validator's verdict, and the exact feedback sent back
  --check     the no-validation harness returns unparseable prose; the validating harness repairs to a schema-valid object

The candidate answers and the schema are the fixture; every accept/reject decision and error message is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "outschema.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def type_ok(value, expected):
    """Check a parsed JSON value against a schema type name. bool is not accepted as a number."""
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    return False


def validate(raw, schema):
    """Parse the raw answer as JSON and check it against the output schema; return (ok, value, error)."""
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return False, None, "not valid JSON (expected an object matching the schema)"
    if not isinstance(value, dict):
        return False, None, "top-level value is %s, expected a JSON object" % type(value).__name__
    for field, expected in schema.items():
        if field not in value:
            return False, None, "missing required field: %s (have: %s)" % (field, ", ".join(value.keys()) or "nothing")
        if not type_ok(value[field], expected):
            return False, None, "field %r has wrong type (expected %s)" % (field, expected)
    return True, value, ""


def run_no_validation(candidates):
    """The naive harness: return the model's first answer as-is, no schema check."""
    return candidates[0]


def run_with_validation(candidates, schema, max_repairs):
    """Validate each answer; on failure feed the specific error back and let the model try again, up to max_repairs."""
    log = []
    for attempt in range(1, max_repairs + 1):
        if attempt - 1 >= len(candidates):
            break
        raw = candidates[attempt - 1]
        ok, value, error = validate(raw, schema)
        log.append({"attempt": attempt, "raw": raw, "ok": ok, "error": error})
        if ok:
            return value, log, True
    return None, log, False


# ----------------------------------------------------------------- printing

def answers_view(data):
    schema = data["output_schema"]
    cands = data["candidates"]
    print("ANSWERS — each candidate final answer checked against the output schema %s" % schema)
    print("-" * 78)
    for i, raw in enumerate(cands, 1):
        ok, value, error = validate(raw, schema)
        print("  attempt %d: %s" % (i, raw))
        print("             -> %s%s" % ("VALID" if ok else "REJECT", "" if ok else " -- " + error))
    print("-" * 78)
    print("  no-validation harness returns: %r" % run_no_validation(cands))
    final, _, ok = run_with_validation(cands, schema, data["max_repairs"])
    print("  validating harness returns:    %r (schema-valid = %s)" % (final, ok))


def repair_view(data):
    schema = data["output_schema"]
    final, log, ok = run_with_validation(data["candidates"], schema, data["max_repairs"])
    print("REPAIR — the bounded repair loop, with the specific feedback sent back on each failure")
    print("-" * 76)
    for e in log:
        print("  attempt %d: %s" % (e["attempt"], e["raw"]))
        if e["ok"]:
            print("             verdict: VALID -> return to caller")
        else:
            print("             verdict: REJECT -> feed back: %r" % e["error"])
    print("-" * 76)
    print("  final answer after %d attempt(s): %r (valid = %s)" % (len(log), final, ok))


def check(data):
    print("SELF-TEST — the naive harness returns unparseable prose; the validating harness repairs to a schema-valid object")
    print("-" * 110)
    schema = data["output_schema"]
    cands = data["candidates"]

    naive = run_no_validation(cands)
    naive_ok, _, _ = validate(naive, schema)
    no_validation_returns_garbage = not naive_ok
    print("  no-validation harness returns a schema-INVALID answer = %s (%r)" % (no_validation_returns_garbage, naive))

    ok1, _, err1 = validate(cands[0], schema)
    validation_rejects_prose = not ok1 and "JSON" in err1
    print("  validating harness rejects the prose answer = %s (%r)" % (validation_rejects_prose, err1))

    ok2, _, err2 = validate(cands[1], schema)
    validation_rejects_partial = not ok2 and "missing required field" in err2
    print("  validating harness rejects the partial answer = %s (%r)" % (validation_rejects_partial, err2))

    feedback_is_specific = "currency" in err2
    print("  the feedback names the missing field by name = %s" % feedback_is_specific)

    final, log, final_ok = run_with_validation(cands, schema, data["max_repairs"])
    validation_accepts_on_repair = final_ok and final == {"total": 42, "currency": "USD"}
    print("  validating harness accepts the repaired answer = %s (attempt %d, %r)" % (validation_accepts_on_repair, len(log), final))

    ok = no_validation_returns_garbage and validation_rejects_prose and validation_rejects_partial and feedback_is_specific and validation_accepts_on_repair
    print("-" * 110)
    print("SELF-TEST %s  no_validation_returns_garbage=%s  validation_rejects_prose=%s  validation_rejects_partial=%s  feedback_is_specific=%s  validation_accepts_on_repair=%s"
          % ("PASS" if ok else "FAIL", no_validation_returns_garbage, validation_rejects_prose, validation_rejects_partial, feedback_is_specific, validation_accepts_on_repair))
    return ok


def main():
    p = argparse.ArgumentParser(description="Output-schema validation: an agent's final structured answer is untrusted output just as a proposed tool call is untrusted input, so validate it against the declared output schema before returning it and, on failure, feed the specific error back for a bounded repair loop -- returning the first unvalidated answer leaks malformed results past the harness to the caller.")
    p.add_argument("--answers", action="store_true")
    p.add_argument("--repair", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("output_schema=%s  max_repairs=%d  candidates=%d  file=%s  (the answers and schema are a fixture)"
          % (data["output_schema"], data["max_repairs"], len(data["candidates"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.answers:
        answers_view(data)
    elif args.repair:
        repair_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
