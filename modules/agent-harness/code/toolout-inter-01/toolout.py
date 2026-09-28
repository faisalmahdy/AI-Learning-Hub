"""Validate a tool's returned payload against its output contract before feeding it to the model -- a tool can succeed (return with no error) and still hand back data that violates its contract, and forwarding it unchecked makes the model reason over garbage.

A tool call can go wrong two ways. It can fail -- raise, or return an error -- which a companion module handles by returning a structured error the harness can branch on. Or it can succeed: return normally, no exception, and hand back a payload that is nonetheless wrong -- a required field null, a value outside its valid range, the wrong type. A success is not a valid payload, and the harness's error handling never fires on this case, because nothing errored.

Forwarding that payload to the model unchecked is the bug. The model has no way to know the temperature field is null rather than a real reading, or that 250 degrees Celsius is a sensor glitch and not the weather -- it reasons over whatever it is given, and produces a confident, wrong answer built on invalid data. Or a later step that computes on the field -- converting the temperature, comparing it, summing it -- crashes deep in the pipeline, far from the tool that returned the bad value, so the failure surfaces nowhere near its cause.

The fix mirrors input validation. A companion module validates the model's proposed tool-call arguments before dispatch; this validates the tool's returned payload after dispatch, against a declared output schema -- required fields present, types correct, values in range. On a violation, the harness treats the success as a failure: it returns a structured error and retries or reports, exactly as it would for a raised exception, rather than passing the bad payload on. The tool's contract is enforced on the way out, not assumed.

On this fixture a weather tool declares temp_c in [-90, 60] and a non-empty conditions string, and returns three success payloads: a valid one, one with a null temperature, and one reading 250 degrees. The unchecked path forwards all three and computes a Fahrenheit value the model will believe (or fails to, on the null); the validated path forwards only the valid one and turns the other two into errors. This computes both.

  --validate   each returned payload checked against the output contract, with the reason on a violation
  --forward    what the unchecked path passes to the model and computes, vs what the validated path passes
  --check      a tool can succeed with an invalid payload; unchecked forwarding reaches the model with garbage, validation blocks it

schema and the responses are the fixture; the per-response validation, the forwarded payloads, and the computed values are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "toolout.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def validate(payload, schema):
    """Check a returned payload against the output contract. Returns (ok, reason)."""
    t = payload.get("temp_c")
    if not isinstance(t, (int, float)):
        return False, "temp_c is not a number (%r)" % t
    if not (schema["temp_c_min"] <= t <= schema["temp_c_max"]):
        return False, "temp_c %r out of range [%d, %d]" % (t, schema["temp_c_min"], schema["temp_c_max"])
    c = payload.get("conditions")
    if not isinstance(c, str) or not c:
        return False, "conditions is empty or not a string (%r)" % c
    return True, "ok"


def to_fahrenheit(temp_c):
    """A downstream computation on the field -- what a later step (or the model) does with it."""
    if not isinstance(temp_c, (int, float)):
        return None  # cannot compute on a non-number: garbage in, nothing out
    return temp_c * 9 / 5 + 32


def naive_forward(responses, schema):
    """Forward every success payload to the model unchecked, and compute the downstream value."""
    return [(r, to_fahrenheit(r.get("temp_c"))) for r in responses]


def validated_forward(responses, schema):
    """Forward only payloads that pass the output contract; the rest become structured errors."""
    forwarded, errors = [], []
    for r in responses:
        ok, reason = validate(r, schema)
        if ok:
            forwarded.append((r, to_fahrenheit(r["temp_c"])))
        else:
            errors.append((r, reason))
    return forwarded, errors


# ----------------------------------------------------------------- printing

def validate_view(data):
    schema = data["schema"]
    print("VALIDATE — each returned payload against the output contract")
    print("-" * 64)
    for r in data["responses"]:
        ok, reason = validate(r, schema)
        print("  %-32s %s  %s" % (r, "ok" if ok else "VIOLATION", "" if ok else reason))
    print("-" * 64)
    print("  every one of these was a successful return -- no error was raised")


def forward_view(data):
    print("FORWARD — what reaches the model, unchecked vs validated")
    print("-" * 64)
    naive = naive_forward(data["responses"], data["schema"])
    print("  unchecked path forwards %d payloads:" % len(naive))
    for r, f in naive:
        print("      temp_c=%-5r -> %s degrees F  (model believes this)" % (r.get("temp_c"), f))
    forwarded, errors = validated_forward(data["responses"], data["schema"])
    print("  validated path forwards %d payload(s):" % len(forwarded))
    for r, f in forwarded:
        print("      temp_c=%-5r -> %.1f degrees F" % (r["temp_c"], f))
    print("  validated path turns %d into errors:" % len(errors))
    for r, reason in errors:
        print("      %s" % reason)
    print("-" * 64)
    print("  unchecked reaches the model with a None and an absurd 482; validated forwards only the real reading")


def check(data):
    print("SELF-TEST — a tool can succeed with an invalid payload; unchecked forwarding reaches the model with garbage, validation blocks it")
    print("-" * 112)
    schema, responses = data["schema"], data["responses"]

    results = [validate(r, schema) for r in responses]
    violations = [r for r, (ok, _) in zip(responses, results) if not ok]

    all_are_successes = all("error" not in r for r in responses)
    print("  every payload was a successful return (no error) = %s" % all_are_successes)

    validator_flags_violations = len(violations) == 2
    print("  the validator flags the invalid payloads = %s (%d of %d)" % (validator_flags_violations, len(violations), len(responses)))

    naive = naive_forward(responses, schema)
    naive_forwards_violations = len(naive) == len(responses)
    print("  the unchecked path forwards every payload, violations included = %s (%d)" % (naive_forwards_violations, len(naive)))

    naive_values = [f for _, f in naive]
    naive_produces_garbage = None in naive_values or any(f is not None and f > 200 for f in naive_values)
    print("  the unchecked path yields garbage/absurd values = %s (%s)" % (naive_produces_garbage, naive_values))

    forwarded, errors = validated_forward(responses, schema)
    validated_blocks_violations = len(forwarded) == 1 and len(errors) == len(violations)
    print("  the validated path forwards only the valid payload = %s (%d forwarded, %d errored)" % (validated_blocks_violations, len(forwarded), len(errors)))

    ok = (all_are_successes and validator_flags_violations and naive_forwards_violations
          and naive_produces_garbage and validated_blocks_violations)
    print("-" * 112)
    print("SELF-TEST %s  all_are_successes=%s  validator_flags_violations=%s  naive_forwards_violations=%s  naive_produces_garbage=%s  validated_blocks_violations=%s"
          % ("PASS" if ok else "FAIL", all_are_successes, validator_flags_violations, naive_forwards_violations,
             naive_produces_garbage, validated_blocks_violations))
    return ok


def main():
    p = argparse.ArgumentParser(description="Tool-output validation: validate a tool's returned payload against its output contract before feeding it to the model, because a tool can succeed (return with no error) and still hand back data that violates its contract -- a null field, an out-of-range value -- and forwarding it unchecked makes the model reason over garbage or crashes a later step far from the tool.")
    p.add_argument("--validate", action="store_true")
    p.add_argument("--forward", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("responses=%d  file=%s  (these are a fixture)" % (len(data["responses"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.validate:
        validate_view(data)
    elif args.forward:
        forward_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
