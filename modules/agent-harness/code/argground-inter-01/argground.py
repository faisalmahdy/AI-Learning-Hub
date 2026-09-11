"""Check that an identifier tool-argument is GROUNDED -- it traces to something the agent actually observed -- not just that it matches the schema, or the model dispatches a plausible id it invented.

Validating a tool call against its schema is necessary and everyone does it: the argument must be the right type, match the expected pattern, fall in the allowed set. That catches a malformed call. It does not catch a well-formed lie, and language models produce well-formed lies constantly for one specific kind of argument: references to entities the model does not actually have in front of it.

Picture an agent asked to 'pull up the invoice and refund it.' If the invoice id was never given to it and never appeared in a prior tool result, the model does not stop and say it lacks the id. It produces one -- 'INV-9999', with the right prefix and a plausible number -- because generating a fluent, correctly-shaped token is exactly what it does. That fabricated id passes every schema check, because it is indistinguishable in form from a real id; it simply does not correspond to any real invoice. The tool then fetches nothing, or errors confusingly, or -- the dangerous case -- happens to hit a different real record and acts on the wrong one.

Schema validation cannot catch this because the flaw is not in the shape of the value but in its provenance. The fix is grounding: for arguments that are references (ids, filenames, record keys, user handles), require that the value appear somewhere in what the agent has actually seen -- a prior observation, the user's message, the retrieved context -- and treat a reference that does not as ungrounded. An ungrounded reference is not dispatched; it is rejected, and the agent is made to go find or ask for the real id rather than act on a fabrication.

The rule: ground identifier arguments before dispatching -- require that a reference argument trace to a value the agent has actually observed, not merely that it matches the schema -- because a schema-valid identifier can be a hallucination, and acting on an invented id hits a nonexistent or wrong record.

On this fixture the agent has observed two invoice ids. Three calls are proposed, all schema-valid; two use observed ids and one uses INV-9999, which matches the pattern but was never seen -- a hallucination. Schema validation accepts all three; grounding accepts only the two real ones. This computes both.

  --calls    each proposed call: whether it is schema-valid and whether its id is grounded
  --gate     which calls pass schema-only validation vs grounding validation
  --check    schema validation accepts the hallucinated id; grounding rejects it and keeps the real ones

observed_ids, id_pattern, and calls are the fixture; the schema and grounding decisions are computed. Stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "argground.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def schema_valid(call, pattern):
    """The id has the right shape."""
    return re.match(pattern, call["id"]) is not None


def grounded(call, observed):
    """The id traces to something the agent actually observed."""
    return call["id"] in observed


def accepted(calls, pattern, observed, require_grounding):
    out = []
    for c in calls:
        ok = schema_valid(c, pattern) and (grounded(c, observed) if require_grounding else True)
        if ok:
            out.append(c["id"])
    return out


# ----------------------------------------------------------------- printing

def calls_view(data):
    pattern, observed = data["id_pattern"], set(data["observed_ids"])
    print("CALLS — each proposed tool call: schema-valid? grounded? (observed=%s)" % data["observed_ids"])
    print("-" * 66)
    print("  tool            id         schema-valid   grounded")
    for c in data["calls"]:
        sv, gd = schema_valid(c, pattern), grounded(c, observed)
        note = "   <- HALLUCINATED" if sv and not gd else ""
        print("  %-14s  %-9s  %-13s  %s%s" % (c["tool"], c["id"], sv, gd, note))
    print("-" * 66)
    print("  the hallucinated id matches the pattern but was never observed")


def gate_view(data):
    pattern, observed = data["id_pattern"], set(data["observed_ids"])
    schema_only = accepted(data["calls"], pattern, observed, require_grounding=False)
    grounded_gate = accepted(data["calls"], pattern, observed, require_grounding=True)
    print("GATE — which calls each policy dispatches")
    print("-" * 60)
    print("  schema-only validation dispatches  = %s" % schema_only)
    print("  grounding validation dispatches    = %s" % grounded_gate)
    print("  dispatched by schema but not grounded = %s" % [i for i in schema_only if i not in grounded_gate])
    print("-" * 60)
    print("  schema-only lets the fabricated id through; grounding stops it")


def check(data):
    print("SELF-TEST — schema validation accepts the hallucinated id; grounding rejects it and keeps the real ones")
    print("-" * 116)
    pattern, observed = data["id_pattern"], set(data["observed_ids"])
    calls = data["calls"]
    schema_only = accepted(calls, pattern, observed, require_grounding=False)
    grounded_gate = accepted(calls, pattern, observed, require_grounding=True)
    hallucinated = [c["id"] for c in calls if schema_valid(c, pattern) and not grounded(c, observed)]

    all_schema_valid = all(schema_valid(c, pattern) for c in calls)
    print("  every proposed id is schema-valid = %s" % all_schema_valid)

    hallucinated_exists = len(hallucinated) > 0
    print("  a schema-valid id was never observed (a hallucination) = %s (%s)" % (hallucinated_exists, hallucinated))

    schema_accepts_hallucinated = any(h in schema_only for h in hallucinated)
    print("  schema-only validation dispatches the hallucinated id = %s" % schema_accepts_hallucinated)

    grounding_rejects_hallucinated = all(h not in grounded_gate for h in hallucinated)
    print("  grounding validation rejects the hallucinated id = %s" % grounding_rejects_hallucinated)

    grounding_keeps_real = set(grounded_gate) == set(data["observed_ids"]) & {c["id"] for c in calls}
    print("  grounding validation keeps every real (observed) id = %s (%s)" % (grounding_keeps_real, grounded_gate))

    ok = (all_schema_valid and hallucinated_exists and schema_accepts_hallucinated
          and grounding_rejects_hallucinated and grounding_keeps_real)
    print("-" * 116)
    print("SELF-TEST %s  all_schema_valid=%s  hallucinated_exists=%s  schema_accepts_hallucinated=%s  grounding_rejects_hallucinated=%s  grounding_keeps_real=%s"
          % ("PASS" if ok else "FAIL", all_schema_valid, hallucinated_exists, schema_accepts_hallucinated, grounding_rejects_hallucinated, grounding_keeps_real))
    return ok


def main():
    p = argparse.ArgumentParser(description="Argument grounding: ground identifier arguments before dispatching -- require that a reference argument trace to a value the agent has actually observed, not merely that it matches the schema -- because a schema-valid identifier can be a hallucination, and acting on an invented id hits a nonexistent or wrong record.")
    p.add_argument("--calls", action="store_true")
    p.add_argument("--gate", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("observed_ids=%s  calls=%d  file=%s  (the observed ids and proposed calls are a fixture)"
          % (data["observed_ids"], len(data["calls"]), DATA.name))
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
