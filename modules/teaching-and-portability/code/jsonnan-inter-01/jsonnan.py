"""JSON has no NaN or Infinity, but Python's json.dumps emits them as bare NaN/Infinity tokens by default -- text Python reads back fine but strict parsers in other languages reject as malformed.

The JSON grammar defines a number as an ordinary decimal. There is no NaN, no Infinity, no -Infinity anywhere in the spec. But floating-point math produces those values all the time: zero divided by zero is NaN, an overflowing sum is infinity, a missing measurement is frequently stored as NaN. So they show up in data that then has to be serialized, and JSON has nowhere to put them.

Python's encoder papers over the gap with a non-standard extension. By default (allow_nan=True) json.dumps writes the bare words NaN, Infinity, and -Infinity straight into the output. The text looks like JSON and is almost JSON, but those three tokens are not part of the standard. Worse, Python's json.loads accepts them right back, so within a single Python program the value round-trips perfectly and nothing looks wrong.

That symmetry is the trap. The bug is invisible until the text leaves Python. Send it to JavaScript's JSON.parse, to a strict parser in Go or Java or Rust, to a database's JSON column, or to any service that validates against the spec, and it is rejected as malformed -- because bare NaN and Infinity are exactly what a conforming parser refuses. The producer thinks it emitted JSON; the consumer receives something no standard JSON parser will read.

The fix is to decide what these values mean before they are serialized. Pass allow_nan=False and json.dumps raises a ValueError the moment it hits one, turning a silent interoperability failure into a loud local error you can handle. Or sanitize deliberately: replace NaN and the infinities with null, or a documented sentinel, so the output is valid JSON every consumer can read. What you must not do is let the default emit tokens that only Python can parse.

The rule: JSON cannot represent NaN or Infinity, so do not let Python's json.dumps emit them (its default does, as non-standard tokens) -- pass allow_nan=False to fail fast, or replace the special values with null before serializing, because the bare tokens round-trip in Python but are rejected by strict parsers everywhere else.

On this fixture a record holds a normal number, a NaN, and an infinity. The default dump contains bare NaN and Infinity and fails a strict parse though Python re-reads it; allow_nan=False raises; the sanitized dump is valid JSON. This computes all three.

  --dump     the default (non-standard) serialization, whether Python re-reads it, and whether it is strict JSON
  --fix      the allow_nan=False behavior and the sanitized (null-replaced) serialization
  --check    Python emits bare NaN/Infinity that it re-reads but strict parsers reject; sanitizing to null is valid

the record (with its special floats) is rebuilt in code; the serializations and their validity are computed. Stdlib only.
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "jsonnan.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def build_record():
    """Rebuild the record with the special floats JSON itself cannot store."""
    return {"ok": 1.0, "ratio": float("nan"), "score": float("inf")}


def is_strict_json(text):
    """A conforming parser rejects the bare NaN/Infinity tokens; detect them in the text."""
    return not any(tok in text for tok in ("NaN", "Infinity"))


def sanitize(record):
    """Replace NaN and the infinities with None (JSON null) before serializing."""
    return {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in record.items()}


# ----------------------------------------------------------------- printing

def dump_view(data):
    rec = build_record()
    text = json.dumps(rec)
    reparsed_ok = True
    try:
        json.loads(text)
    except ValueError:
        reparsed_ok = False
    print("DUMP — default json.dumps of a record with NaN and Infinity")
    print("-" * 60)
    print("  serialized: %s" % text)
    print("  Python json.loads re-reads it:        %s" % reparsed_ok)
    print("  passes a strict (standard) JSON parse: %s" % is_strict_json(text))
    print("-" * 60)
    print("  Python round-trips it; a strict parser elsewhere rejects the bare tokens")


def fix_view(data):
    rec = build_record()
    raised = False
    try:
        json.dumps(rec, allow_nan=False)
    except ValueError as e:
        raised = True
        msg = str(e)
    clean = json.dumps(sanitize(rec))
    print("FIX — two safe ways to handle the special values")
    print("-" * 60)
    print("  json.dumps(..., allow_nan=False) raises: %s" % raised)
    if raised:
        print("    -> %s" % msg)
    print("  sanitized (NaN/Inf -> null): %s" % clean)
    print("  sanitized passes a strict JSON parse:    %s" % is_strict_json(clean))
    print("-" * 60)
    print("  fail fast, or replace with null -- either beats emitting non-standard tokens")


def check(data):
    print("SELF-TEST — Python emits bare NaN/Infinity that it re-reads but strict parsers reject; sanitizing to null is valid")
    print("-" * 116)
    rec = build_record()
    text = json.dumps(rec)

    emits_nonstandard = ("NaN" in text) or ("Infinity" in text)
    print("  default json.dumps emits bare NaN/Infinity tokens = %s" % emits_nonstandard)

    python_reparses = True
    try:
        json.loads(text)
    except ValueError:
        python_reparses = False
    print("  Python json.loads re-reads its own output = %s (bug stays hidden in Python)" % python_reparses)

    not_strict = not is_strict_json(text)
    print("  the default output fails a strict JSON parse = %s" % not_strict)

    allow_nan_false_raises = False
    try:
        json.dumps(rec, allow_nan=False)
    except ValueError:
        allow_nan_false_raises = True
    print("  allow_nan=False raises at serialization time = %s" % allow_nan_false_raises)

    clean = json.dumps(sanitize(rec))
    sanitized_is_strict = is_strict_json(clean)
    print("  sanitizing NaN/Inf to null yields strict JSON = %s (%s)" % (sanitized_is_strict, clean))

    ok = (emits_nonstandard and python_reparses and not_strict
          and allow_nan_false_raises and sanitized_is_strict)
    print("-" * 116)
    print("SELF-TEST %s  emits_nonstandard=%s  python_reparses=%s  not_strict=%s  allow_nan_false_raises=%s  sanitized_is_strict=%s"
          % ("PASS" if ok else "FAIL", emits_nonstandard, python_reparses, not_strict,
             allow_nan_false_raises, sanitized_is_strict))
    return ok


def main():
    p = argparse.ArgumentParser(description="JSON NaN/Infinity: JSON cannot represent NaN or Infinity, so do not let Python's json.dumps emit them (its default does, as non-standard tokens) -- pass allow_nan=False to fail fast, or replace the special values with null before serializing, because the bare tokens round-trip in Python but are rejected by strict parsers everywhere else.")
    p.add_argument("--dump", action="store_true")
    p.add_argument("--fix", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("record fields=%s  file=%s  (the special floats are built in code)" % (data["record_fields"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.dump:
        dump_view(data)
    elif args.fix:
        fix_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
