---
id: jsontypes-inter-01
title: A JSON round trip does not preserve types — integer dict keys come back as strings and tuples come back as lists
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: JSON has a deliberately narrow type model, and two of its limits bite silently. First, JSON object keys are always strings — there is no integer key — so a dict with integer keys is serialized with those keys coerced to their string form, and they come back as strings. Second, JSON has one sequence type, the array, so a tuple is serialized as an array and comes back as a list; JSON also has no set, no bytes, no datetime. The result is that a round trip through JSON is lossless for values but lossy for types: the numbers and strings survive intact, but the containers and key types can change underneath you, and nothing errors — the JSON is valid, the values are all there — yet the reconstructed object is not equal to the one you serialized. The sharpest symptom is the integer key: serialize {1: "a"} and you get back {"1": "a"}, so a lookup by the integer 1 now fails because the key is the string "1"; code that stored a mapping keyed by user id or year as an integer, persisted it as JSON, and later looked it up by the integer will quietly miss every entry. The fix is to not assume a JSON round trip is the identity function — design the data to use string keys and lists if it must pass through JSON, or convert types explicitly on the way back, or use a format that preserves the types you need. On a fixture with integer dict keys and a tuple, the keys come back as strings, the tuple comes back as a list, a lookup by the original integer key returns None, and a plain string list survives unchanged.
eli5: Imagine you have a box of toys sorted into drawers labeled 1, 2, and 3, and you want to mail the whole thing to a friend. But the mailing form only lets you write labels in letters, not numbers, so drawer "1" gets relabeled "one-as-text" on the way. When your friend opens the box and looks for drawer number 1, there isn't one — there's a drawer called "1" spelled as text, which their machine treats as a different thing, so their search comes up empty even though all the toys are right there. Also, you had one set of toys taped together as a fixed bundle, but the shipping only knows loose bags, so it arrives as a loose bag instead of a taped bundle. Nothing got lost — every toy made it — but the labels and the packaging changed. Sending data as JSON is like that: the values arrive fine, but number-labels turn into text-labels and fixed bundles turn into loose lists, and code that expected the originals gets confused.
---

## Why this module

Serialization formats are contracts about what kinds of values can be represented, and JSON's contract is small on purpose. It has objects (with string keys only), arrays, numbers, strings, booleans, and null. That is the whole type system. Every richer type in your programming language — an integer used as a key, a tuple, a set, a byte string, a datetime — has to be squeezed into one of those slots on the way out, and JSON does the squeezing silently.

Silent is the operative word. When you serialize a value JSON cannot represent exactly, it does not raise an error asking you to choose; it applies a default coercion. An integer key becomes its string form because keys must be strings. A tuple becomes an array because that is the only sequence. The output is valid JSON, it parses back cleanly, and the values inside are all correct — so nothing signals that a type changed.

The trap springs on the way back in, when your code assumes it received what it sent. It looks up a mapping by an integer key that is now a string and finds nothing; it checks `isinstance(x, tuple)` on something that is now a list; it compares the round-tripped object to the original and they are not equal. This module round-trips a structure with integer keys and a tuple through JSON and shows exactly which types moved.

**JSON's type model is small, so it silently coerces the types it cannot represent — integer keys to strings, tuples to arrays — producing valid JSON whose parsed result is not equal to the object you serialized.**

## Concepts

The distinction that matters is value-preserving versus type-preserving. A JSON round trip is value-preserving — every number, string, and boolean comes back with the same value — but not type-preserving, because the container and key types are part of the type, not the value, and JSON does not carry them. Confusing the two is what makes the bug invisible: you check that the data "is all there" (values), it is, and you conclude the round trip was faithful, but faithfulness of type is a separate property that failed.

The integer-key case is the most damaging because it breaks lookups, not just comparisons. A dict is used by looking things up, and a lookup is by key identity: the integer `1` and the string `"1"` are different keys, so after the round trip every access by the original integer key misses. The data is intact and completely unreachable at the same time — the worst kind of failure, because it looks like the data is simply gone when it is really just re-keyed.

The reason the fix has to be deliberate is that the coercion is one-way and lossy of type information. JSON does not record that a key was originally an integer or that an array was originally a tuple, so there is nothing to reverse on the way back — the parser cannot know to restore the type. You either avoid the types JSON cannot hold (use string keys and lists from the start), or you re-impose the types after parsing (re-key the dict by int, re-wrap the tuple), or you choose a format whose contract includes the types you need. What you cannot do is assume the round trip will do it for you.

<svg role="img" aria-label="A grid of source types mapped to JSON's type slots: int key and str key both land on string key, tuple and list both land on array, while set, bytes and datetime have no slot" viewBox="0 0 440 150">
<text x="90" y="18" fill="var(--muted)" font-size="9" text-anchor="middle">source type</text>
<text x="330" y="18" fill="var(--muted)" font-size="9" text-anchor="middle">JSON slot</text>
<text x="30" y="42" fill="var(--ink)" font-size="9">int key</text>
<text x="30" y="60" fill="var(--ink)" font-size="9">str key</text>
<line x1="90" y1="38" x2="270" y2="50" stroke="var(--s2)"/>
<line x1="90" y1="56" x2="270" y2="50" stroke="var(--s1)"/>
<rect x="272" y="42" width="120" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="332" y="54" fill="var(--ink)" font-size="9" text-anchor="middle">string key</text>
<text x="30" y="90" fill="var(--ink)" font-size="9">tuple</text>
<text x="30" y="108" fill="var(--ink)" font-size="9">list</text>
<line x1="90" y1="86" x2="270" y2="98" stroke="var(--s2)"/>
<line x1="90" y1="104" x2="270" y2="98" stroke="var(--s1)"/>
<rect x="272" y="90" width="120" height="16" fill="var(--panel)" stroke="var(--line)"/>
<text x="332" y="102" fill="var(--ink)" font-size="9" text-anchor="middle">array</text>
<text x="30" y="134" fill="var(--muted)" font-size="9">set, bytes, datetime</text>
<text x="332" y="134" fill="var(--s2)" font-size="9" text-anchor="middle">no slot</text>
</svg>
^ JSON collapses distinct source types onto one slot — two key types onto string, two sequences onto array — so the round trip cannot tell them back apart.

**A JSON round trip preserves values but not types, and the integer-key case is worst because it silently breaks lookups; the coercion is one-way, so restoring the types must be done deliberately, not expected for free.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/jsontypes-inter-01. The fixture supplies plain values; the code builds the real Python object with integer keys and a tuple — because the fixture file, being JSON itself, cannot store those types either.

```json filename=modules/teaching-and-portability/code/jsontypes-inter-01/jsontypes.json:3-6 COMPLETE
  "counts_keys": [1, 2],
  "counts_values": [10, 20],
  "point": [3, 4],
  "tags": ["a", "b"]
```

The code reconstructs the typed object — integer dict keys and a tuple.

```python filename=modules/teaching-and-portability/code/jsontypes-inter-01/jsontypes.py:34-37 COMPLETE
def build_original(data):
    """Reconstruct the real Python object: integer dict keys and a tuple."""
    counts = {k: v for k, v in zip(data["counts_keys"], data["counts_values"])}  # integer keys
    return {"counts": counts, "point": tuple(data["point"]), "tags": list(data["tags"])}
```

The round trip is what persistence or a network hop does — serialize, then parse back.

```python filename=modules/teaching-and-portability/code/jsontypes-inter-01/jsontypes.py:40-42 COMPLETE
def roundtrip(obj):
    """Serialize to JSON and parse it back -- what persistence or a network hop does."""
    return json.loads(json.dumps(obj))
```

Before running it, predict: the integer keys of `counts` should come back as strings and the tuple `point` should come back as a list, while `tags` stays a list. Run `--serialize`:

```text filename=jsontypes.py --serialize
SERIALIZE — original object -> JSON text -> round-tripped object
------------------------------------------------------------
  original:     {'counts': {1: 10, 2: 20}, 'point': (3, 4), 'tags': ['a', 'b']}
  json text:    {"counts": {"1": 10, "2": 20}, "point": [3, 4], "tags": ["a", "b"]}
  round-tripped: {'counts': {'1': 10, '2': 20}, 'point': [3, 4], 'tags': ['a', 'b']}
```

The prediction holds, and the JSON text shows the coercion happening: the keys are already quoted as `"1"` and `"2"` in the serialized form, and `point` is already an array. The round-tripped object has string keys and a list where the original had integer keys and a tuple. Every value is correct; two types changed.

<svg role="img" aria-label="The original object with an integer key 1 and a tuple passes through JSON and returns with a string key quote-1 and a list, while the values 10 and 3,4 are unchanged" viewBox="0 0 440 150">
<rect x="20" y="30" width="130" height="90" fill="var(--panel)" stroke="var(--line)"/>
<text x="85" y="26" fill="var(--muted)" font-size="9" text-anchor="middle">original</text>
<text x="30" y="55" fill="var(--ink)" font-size="10">key 1 (int)</text>
<text x="30" y="80" fill="var(--ink)" font-size="10">point (tuple)</text>
<text x="30" y="105" fill="var(--ink)" font-size="10">tags (list)</text>
<text x="200" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">JSON</text>
<line x1="155" y1="75" x2="245" y2="75" stroke="var(--muted)"/>
<rect x="250" y="30" width="160" height="90" fill="var(--panel)" stroke="var(--line)"/>
<text x="330" y="26" fill="var(--muted)" font-size="9" text-anchor="middle">round-tripped</text>
<text x="260" y="55" fill="var(--s2)" font-size="10">key "1" (str)</text>
<text x="260" y="80" fill="var(--s2)" font-size="10">point (list)</text>
<text x="260" y="105" fill="var(--s1)" font-size="10">tags (list, same)</text>
</svg>
^ The integer key and the tuple change type through JSON; the plain list is unchanged — values intact, two types moved.

Now the consequence that breaks code. Run `--changes`:

```text filename=jsontypes.py --changes
CHANGES — what each field's type became across the round trip
------------------------------------------------------------
  counts keys: ['int', 'int'] -> ['str', 'str']
  point:       tuple -> list
  tags:        list -> list
  lookup counts[1]: original=10  round-tripped=None
```

The last line is the whole danger in one row. In the original, `counts[1]` is 10; after the round trip, looking up the integer `1` returns None, because the key is now the string `"1"`. The value 10 is still in the dict, perfectly intact, and completely unreachable by the key the code uses. Nothing raised; the lookup just quietly missed.

<svg role="img" aria-label="A lookup of integer key 1 against the round-tripped dict whose key is string quote-1: the lookup misses and returns None, though the value 10 is present under the string key" viewBox="0 0 440 130">
<text x="90" y="40" fill="var(--ink)" font-size="11" text-anchor="middle">lookup: counts[1]</text>
<text x="90" y="58" fill="var(--muted)" font-size="9" text-anchor="middle">(integer key)</text>
<line x1="160" y1="50" x2="240" y2="50" stroke="var(--muted)"/>
<rect x="245" y="25" width="170" height="55" fill="var(--panel)" stroke="var(--line)"/>
<text x="330" y="48" fill="var(--ink)" font-size="10" text-anchor="middle">dict has key "1" (str): 10</text>
<text x="330" y="68" fill="var(--muted)" font-size="9" text-anchor="middle">no integer key 1</text>
<text x="220" y="108" fill="var(--s2)" font-size="11" text-anchor="middle">result: None — value present but unreachable</text>
</svg>
^ The value 10 is in the dict under the string key "1", so a lookup by the integer 1 misses and returns None — intact yet unreachable.

## Build

The self-test plants the failure and names each claim as a boolean flag. It first builds the typed object and its round trip.

```python filename=modules/teaching-and-portability/code/jsontypes-inter-01/jsontypes.py:79-80 COMPLETE
    orig = build_original(data)
    back = roundtrip(orig)
```

Then it checks that the integer keys became strings, that a lookup by the original integer key now misses, that the tuple became a list, that the round trip is not equal to the original, and that the plain list survived.

```python filename=modules/teaching-and-portability/code/jsontypes-inter-01/jsontypes.py:82-94 COMPLETE
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
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if a future assumption that JSON preserves these types slips in:

```text filename=jsontypes.py --check
SELF-TEST — JSON coerces int keys to strings and tuples to lists, so the round trip is not the identity
--------------------------------------------------------------------------------------------------------
  integer dict keys come back as strings = True ([1, 2] -> ['1', '2'])
  a lookup by the original integer key now misses = True (10 vs None)
  the tuple comes back as a list = True (tuple -> list)
  the round trip is not equal to the original = True
  a plain string list survives unchanged = True
```

**The self-test asserts both that the value is present (the list survives, the number is intact) and that the lookup misses — proving the failure is a type change that hides reachable data, not lost data.**

## Definition of done

You can state JSON's type model and name the coercions it applies: integer keys to strings, tuples to arrays, and the types it cannot represent at all (set, bytes, datetime).
You can distinguish value-preserving from type-preserving and explain why "the data is all there" does not mean the round trip was faithful.
You can explain why the integer-key case is the most damaging — it breaks lookups, leaving the value intact but unreachable.
You can explain why the coercion cannot be reversed automatically on parse, so restoring types must be deliberate.
You can name three fixes — use JSON-native types from the start, re-impose types after parsing, or use a type-preserving format — and pick one for a given situation.

## Boss fight

Try a type JSON cannot represent at all: put a `set` in the object and serialize it. Unlike the silent coercions, this one raises — `json.dumps` refuses a set with a TypeError — so the failure is loud, not silent. Reason about why that is arguably better: a coercion that changes a type quietly (int key to string) is more dangerous than a refusal that stops you, because the refusal forces a decision while the coercion ships a bug. The lesson sharpens: JSON's dangerous cases are not the types it rejects but the types it accepts and silently transforms, because only those pass your tests and reach production.

Now consider a value-level version of the same hazard: a large integer. JSON numbers have no defined precision, and many parsers (JavaScript's especially) read numbers as 64-bit floats, so an integer beyond 2^53 round-trips to a nearby but wrong value — a user id like 9007199254740993 comes back as 9007199254740992. Here even the value is not preserved, and it is silent in exactly the way the type coercions are. The general rule generalizes: JSON is a lossy contract at both the type and the precision boundary, and the only safe assumption is that a round trip may change anything the format cannot represent exactly — so large integers cross as strings, just as tuples should.

**JSON's silent transforms are more dangerous than its loud refusals — a rejected set stops you, a coerced key ships a bug — and the hazard extends to values: a large integer can round-trip to a wrong number under float-based parsers, so cross it as a string too.**

## External resources

The JSON specification (RFC 8259) defines the complete type model — objects with string keys, arrays, numbers, strings, booleans, null — that everything else must be mapped into.
Python's json module documentation lists its type conversion table, including that dict keys are coerced to strings and that tuples serialize as arrays.
The topic's own module on writing CSV with a real writer covers a sibling lesson — a text data format whose defaults silently corrupt structure the naive code assumed was safe.
