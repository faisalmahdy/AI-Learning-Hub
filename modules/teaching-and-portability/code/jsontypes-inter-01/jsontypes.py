"""JSON does not preserve types on a round trip -- integer dict keys come back as strings and tuples come back as lists, so json.loads(json.dumps(x)) is not x, and a lookup by the original integer key misses.

JSON has a deliberately narrow type model, and two of its limits bite silently. First, JSON object keys are always strings -- there is no integer key -- so a dict with integer keys is serialized with those keys coerced to their string form, and they come back as strings. Second, JSON has one sequence type, the array, so a tuple is serialized as an array and comes back as a list. JSON also has no set, no bytes, no datetime.

The result is that a round trip through JSON is lossless for VALUES but lossy for TYPES. The numbers and strings survive intact, but the containers and key types can change underneath you: an integer key becomes a string key, a tuple becomes a list. Nothing errors -- the JSON is valid, the values are all there -- but the reconstructed object is not equal to the one you serialized.

The sharpest symptom is the integer key. Serialize {1: "a"} and you get back {"1": "a"}, and now a lookup by the integer 1 fails -- the key is the string "1". Code that stored a mapping keyed by user id or year as an integer, persisted it as JSON, and later looked it up by the integer id will quietly miss every entry, because the keys silently changed type in transit.

The fix is to not assume a JSON round trip is the identity function. Design the data to use string keys and lists from the start if it must pass through JSON, or convert on the way back in (re-key by int, re-wrap tuples), or use a serialization format that preserves the types you need. The point is to know that JSON coerces types, so you handle it deliberately instead of being surprised.

The rule: do not assume json.loads(json.dumps(x)) equals x -- JSON coerces integer dict keys to strings and tuples to lists (and cannot represent sets, bytes, or datetimes) -- so design data to survive JSON's type model or convert types explicitly across the round trip.

On this fixture a dict with integer keys and a tuple is round-tripped through JSON. The integer keys come back as strings, the tuple comes back as a list, a lookup by the original integer key fails, and the plain string list survives unchanged. This computes all of it.

  --serialize   the original object, its JSON text, and the round-tripped object
  --changes     the specific type changes: int keys to str, tuple to list, list unchanged
  --check       JSON coerces int keys to strings and tuples to lists, so the round trip is not the identity

the fixture supplies the values; the original Python object (with int keys and a tuple), its JSON, and the round trip are built in code. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "jsontypes.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def build_original(data):
    """Reconstruct the real Python object: integer dict keys and a tuple."""
    counts = {k: v for k, v in zip(data["counts_keys"], data["counts_values"])}  # integer keys
    return {"counts": counts, "point": tuple(data["point"]), "tags": list(data["tags"])}


def roundtrip(obj):
    """Serialize to JSON and parse it back -- what persistence or a network hop does."""
    return json.loads(json.dumps(obj))


# ----------------------------------------------------------------- printing

def serialize_view(data):
    orig = build_original(data)
    text = json.dumps(orig)
    back = roundtrip(orig)
    print("SERIALIZE — original object -> JSON text -> round-tripped object")
    print("-" * 60)
    print("  original:     %r" % orig)
    print("  json text:    %s" % text)
    print("  round-tripped: %r" % back)
    print("-" * 60)
    print("  the JSON is valid and the values are all there -- but the types moved")


def changes_view(data):
    orig = build_original(data)
    back = roundtrip(orig)
    print("CHANGES — what each field's type became across the round trip")
    print("-" * 60)
    print("  counts keys: %s -> %s"
          % (sorted(type(k).__name__ for k in orig["counts"]),
             sorted(type(k).__name__ for k in back["counts"])))
    print("  point:       %s -> %s" % (type(orig["point"]).__name__, type(back["point"]).__name__))
    print("  tags:        %s -> %s" % (type(orig["tags"]).__name__, type(back["tags"]).__name__))
    print("  lookup counts[1]: original=%r  round-tripped=%r"
          % (orig["counts"].get(1), back["counts"].get(1)))
    print("-" * 60)
    print("  int keys turned to str, the tuple to a list; the plain list is unchanged")


def check(data):
    print("SELF-TEST — JSON coerces int keys to strings and tuples to lists, so the round trip is not the identity")
    print("-" * 104)
    orig = build_original(data)
    back = roundtrip(orig)

    int_keys_become_strings = all(isinstance(k, str) for k in back["counts"]) and any(isinstance(k, int) for k in orig["counts"])
    print("  integer dict keys come back as strings = %s (%s -> %s)"
          % (int_keys_become_strings, list(orig["counts"]), list(back["counts"])))

    lookup_by_int_key_fails = orig["counts"].get(1) is not None and back["counts"].get(1) is None
    print("  a lookup by the original integer key now misses = %s (%r vs %r)"
          % (lookup_by_int_key_fails, orig["counts"].get(1), back["counts"].get(1)))

    tuple_becomes_list = isinstance(orig["point"], tuple) and isinstance(back["point"], list)
    print("  the tuple comes back as a list = %s (%s -> %s)"
          % (tuple_becomes_list, type(orig["point"]).__name__, type(back["point"]).__name__))

    roundtrip_not_identity = back != orig
    print("  the round trip is not equal to the original = %s" % roundtrip_not_identity)

    list_survives = back["tags"] == orig["tags"]
    print("  a plain string list survives unchanged = %s" % list_survives)

    ok = (int_keys_become_strings and lookup_by_int_key_fails and tuple_becomes_list
          and roundtrip_not_identity and list_survives)
    print("-" * 104)
    print("SELF-TEST %s  int_keys_become_strings=%s  lookup_by_int_key_fails=%s  tuple_becomes_list=%s  roundtrip_not_identity=%s  list_survives=%s"
          % ("PASS" if ok else "FAIL", int_keys_become_strings, lookup_by_int_key_fails,
             tuple_becomes_list, roundtrip_not_identity, list_survives))
    return ok


def main():
    p = argparse.ArgumentParser(description="JSON type coercion: do not assume json.loads(json.dumps(x)) equals x -- JSON coerces integer dict keys to strings and tuples to lists (and cannot represent sets, bytes, or datetimes) -- so design data to survive JSON's type model or convert types explicitly across the round trip.")
    p.add_argument("--serialize", action="store_true")
    p.add_argument("--changes", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("fixture=%s  file=%s  (the values are a fixture; the typed object is built in code)"
          % ({k: data[k] for k in ("counts_keys", "point")}, DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.serialize:
        serialize_view(data)
    elif args.changes:
        changes_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
