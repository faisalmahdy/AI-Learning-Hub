---
id: jsonnan-inter-01
title: JSON has no NaN or Infinity — Python emits them as bare tokens that round-trip in Python but strict parsers everywhere else reject
topic: teaching-and-portability
level: intermediate
status: ready
time: 15 min
summary: The JSON grammar defines a number as an ordinary decimal — there is no NaN, no Infinity, no -Infinity anywhere in the spec — but floating-point math produces those values constantly: zero divided by zero is NaN, an overflowing sum is infinity, a missing measurement is frequently stored as NaN. When such a value reaches json.dumps, Python's default (allow_nan=True) papers over the gap with a non-standard extension, writing the bare words NaN, Infinity, and -Infinity straight into the output. The text looks like JSON and is almost JSON, but those tokens are not part of the standard, and — the trap — Python's json.loads accepts them right back, so within a single Python program the value round-trips perfectly and nothing looks wrong. The bug is invisible until the text leaves Python: send it to JavaScript's JSON.parse, a strict parser in Go or Java or Rust, a database's JSON column, or any spec-validating service, and it is rejected as malformed, because bare NaN and Infinity are exactly what a conforming parser refuses. The fix is to decide what these values mean before serializing — pass allow_nan=False so json.dumps raises the moment it hits one (a loud local error instead of a silent interop failure), or replace NaN and the infinities with null (or a documented sentinel) so the output is valid JSON every consumer can read. On a fixture record holding a normal number, a NaN, and an infinity, the default dump contains bare NaN and Infinity and fails a strict parse though Python re-reads it, allow_nan=False raises, and the sanitized dump is valid JSON.
eli5: Imagine a form that only has boxes for regular numbers, but you need to write down "not a number" and "infinity" for a couple of answers. There's literally no box for those. Your own note-taking app is lenient — it lets you scribble the words "NaN" and "Infinity" in the margins and can read your own scribbles back later, so to you everything looks fine. But the form's official rules don't allow those scribbles, so the moment you hand the form to anyone who follows the rules strictly — another office, another country's system — they look at it and say "this isn't a valid form" and throw it out. The data seemed fine because you only ever tested it with your own lenient reader. The safe move is to decide up front what those special answers should be — leave the box blank (a proper "empty"), or refuse to submit until they're fixed — instead of scribbling words the standard doesn't allow.
---

## Why this module

Serialization formats are contracts, and a value that the format cannot represent has to be handled deliberately — coerced, rejected, or mapped to something the format does allow. JSON's number type is deliberately narrow: finite decimals only. The special floating-point values NaN, +Infinity, and -Infinity are not in the grammar, so strictly speaking there is no way to put them in JSON at all.

But those values are not exotic; they are the routine output of ordinary arithmetic. A ratio with a zero denominator is NaN, a product that overflows the double range is infinity, and NaN is the near-universal convention for "missing" in numeric data. So any pipeline that computes then serializes will, sooner or later, hand json.dumps a value JSON cannot hold, and what happens next is decided by a default most people never set.

The default is to emit the value anyway, as a bare token, which is the worst of the three options because it fails silently. It is not an error you catch in testing and not obviously wrong output; it is text that your own tools read back perfectly. The failure is deferred to whoever consumes the JSON with a strict parser — a different language, a different service, a validator — and surfaces there as a rejection with no obvious connection to the producer that wrote it. This module serializes a record with these values and shows the default, the strict rejection, and the two fixes.

**JSON's number type excludes NaN and infinity, but arithmetic produces them routinely; Python's default emits them as non-standard bare tokens that read back in Python and fail only when a strict parser elsewhere consumes them.**

## Concepts

The core issue is a lenient producer paired with a lenient consumer inside one ecosystem, hiding a contract violation. Python's json module both writes and reads the NaN/Infinity extension, so a Python-to-Python round trip is a closed loop that never touches the standard. Every test you run inside Python passes. The contract JSON promises — that the output is readable by any conforming parser — is broken, but nothing in the loop checks that promise, so the breakage is invisible until the output crosses an ecosystem boundary.

That boundary is where JSON's whole value lives, which is why this bug is more than pedantry. The point of JSON is interoperability — it exists so that a Python service and a JavaScript client and a Go database can exchange data. A JSON document that only Python can parse has forfeited the one thing the format was chosen for. The bare-token output is JSON in appearance and Python-specific data in fact.

The two fixes correspond to two philosophies, and both are better than the default. Failing fast — allow_nan=False — treats the special value as a programming error to surface immediately, raising at the point of serialization so a human decides what it should mean before any invalid text is produced. Sanitizing — mapping NaN and the infinities to null or a sentinel — treats them as legitimate data with a defined JSON representation, chosen deliberately so every consumer reads the same thing. The unforgivable option is the default, which makes the choice by not making it, and defers the cost to a stranger's parser.

<svg role="img" aria-label="A closed Python-to-Python loop reads its own NaN output fine, but crossing the boundary to another ecosystem the same document is rejected" viewBox="0 0 440 140">
<rect x="20" y="40" width="150" height="60" fill="var(--panel)" stroke="var(--s1)"/>
<text x="95" y="35" fill="var(--muted)" font-size="8" text-anchor="middle">Python ecosystem</text>
<text x="95" y="66" fill="var(--ink)" font-size="9" text-anchor="middle">dump -&gt; load</text>
<text x="95" y="84" fill="var(--s1)" font-size="8" text-anchor="middle">round-trips fine</text>
<line x1="170" y1="70" x2="270" y2="70" stroke="var(--s2)" stroke-dasharray="4 3"/>
<text x="220" y="62" fill="var(--muted)" font-size="8" text-anchor="middle">boundary</text>
<rect x="270" y="40" width="150" height="60" fill="var(--panel)" stroke="var(--s2)"/>
<text x="345" y="35" fill="var(--muted)" font-size="8" text-anchor="middle">other ecosystem</text>
<text x="345" y="66" fill="var(--ink)" font-size="9" text-anchor="middle">strict parse</text>
<text x="345" y="84" fill="var(--s2)" font-size="8" text-anchor="middle">rejected</text>
</svg>
^ Inside Python the NaN document round-trips and looks fine; the failure appears only when it crosses the boundary to a strict parser in another ecosystem.

**A lenient Python producer and consumer hide the contract violation inside one ecosystem, forfeiting JSON's interoperability; failing fast or sanitizing both make the choice deliberately, while the default makes it silently and defers the cost.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/teaching-and-portability/code/jsonnan-inter-01. The fixture names the record's fields; the special floats themselves are built in code, since the JSON fixture cannot store them.

```json filename=modules/teaching-and-portability/code/jsonnan-inter-01/jsonnan.json:3-4 COMPLETE
  "record_fields": ["ok", "ratio", "score"],
  "record_values_note": "ok=1.0 (normal), ratio=NaN (0/0), score=Infinity (overflow); NaN and Infinity cannot be written in this JSON fixture, so the code constructs them"
```

The record is rebuilt in code with the values JSON itself cannot hold.

```python filename=modules/teaching-and-portability/code/jsonnan-inter-01/jsonnan.py:35-37 COMPLETE
def build_record():
    """Rebuild the record with the special floats JSON itself cannot store."""
    return {"ok": 1.0, "ratio": float("nan"), "score": float("inf")}
```

A strict parser rejects the bare NaN/Infinity tokens; this detects them.

```python filename=modules/teaching-and-portability/code/jsonnan-inter-01/jsonnan.py:40-42 COMPLETE
def is_strict_json(text):
    """A conforming parser rejects the bare NaN/Infinity tokens; detect them in the text."""
    return not any(tok in text for tok in ("NaN", "Infinity"))
```

The sanitizer replaces the non-finite values with None before serializing.

```python filename=modules/teaching-and-portability/code/jsonnan-inter-01/jsonnan.py:45-47 COMPLETE
def sanitize(record):
    """Replace NaN and the infinities with None (JSON null) before serializing."""
    return {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in record.items()}
```

Before running it, predict: the default dump contains the bare words NaN and Infinity, Python re-reads it fine, but it fails a strict parse. Run `--dump`:

```text filename=jsonnan.py --dump
DUMP — default json.dumps of a record with NaN and Infinity
------------------------------------------------------------
  serialized: {"ok": 1.0, "ratio": NaN, "score": Infinity}
  Python json.loads re-reads it:        True
  passes a strict (standard) JSON parse: False
```

The prediction holds. The serialized text has `NaN` and `Infinity` sitting where numbers should be — no quotes, bare tokens. Python's own json.loads reads it back without complaint, which is exactly why the bug hides. But a strict parse fails: those tokens are not valid JSON, so any conforming consumer rejects the document.

<svg role="img" aria-label="The JSON text with bare NaN and Infinity tokens flows to two readers: Python json.loads accepts it, a strict parser rejects it" viewBox="0 0 440 140">
<rect x="20" y="20" width="400" height="26" fill="var(--panel)" stroke="var(--line)"/>
<text x="220" y="37" fill="var(--ink)" font-size="9" text-anchor="middle">{"ok": 1.0, "ratio": NaN, "score": Infinity}</text>
<line x1="150" y1="46" x2="110" y2="78" stroke="var(--muted)"/>
<line x1="290" y1="46" x2="330" y2="78" stroke="var(--muted)"/>
<rect x="40" y="80" width="140" height="40" fill="var(--panel)" stroke="var(--s1)"/>
<text x="110" y="98" fill="var(--ink)" font-size="9" text-anchor="middle">Python json.loads</text>
<text x="110" y="113" fill="var(--s1)" font-size="9" text-anchor="middle">accepts (hides bug)</text>
<rect x="260" y="80" width="140" height="40" fill="var(--panel)" stroke="var(--s2)"/>
<text x="330" y="98" fill="var(--ink)" font-size="9" text-anchor="middle">strict JSON parser</text>
<text x="330" y="113" fill="var(--s2)" font-size="9" text-anchor="middle">rejects: malformed</text>
</svg>
^ The same bare-token text is accepted by Python's lenient reader and rejected by a conforming parser — the split that hides the bug until it crosses ecosystems.

Now the two fixes. Predict: allow_nan=False raises, and the sanitized dump replaces the specials with null and passes strict. Run `--fix`:

```text filename=jsonnan.py --fix
FIX — two safe ways to handle the special values
------------------------------------------------------------
  json.dumps(..., allow_nan=False) raises: True
    -> Out of range float values are not JSON compliant
  sanitized (NaN/Inf -> null): {"ok": 1.0, "ratio": null, "score": null}
  sanitized passes a strict JSON parse:    True
```

The prediction holds. With allow_nan=False, json.dumps raises "Out of range float values are not JSON compliant" the instant it meets the NaN — the failure is now loud, local, and at the producer, where it can be handled. The sanitized dump maps both specials to `null`, producing valid JSON that every consumer reads identically. Both are deliberate; both beat the default.

<svg role="img" aria-label="Three outcomes: default emits bare tokens (invalid), allow_nan=False raises at serialization, sanitize emits null (valid)" viewBox="0 0 440 140">
<rect x="15" y="30" width="130" height="70" fill="var(--panel)" stroke="var(--s2)"/>
<text x="80" y="50" fill="var(--ink)" font-size="9" text-anchor="middle">default</text>
<text x="80" y="68" fill="var(--muted)" font-size="8" text-anchor="middle">emits NaN token</text>
<text x="80" y="86" fill="var(--s2)" font-size="8" text-anchor="middle">invalid, silent</text>
<rect x="155" y="30" width="130" height="70" fill="var(--panel)" stroke="var(--s1)"/>
<text x="220" y="50" fill="var(--ink)" font-size="9" text-anchor="middle">allow_nan=False</text>
<text x="220" y="68" fill="var(--muted)" font-size="8" text-anchor="middle">raises at dump</text>
<text x="220" y="86" fill="var(--s1)" font-size="8" text-anchor="middle">loud, local</text>
<rect x="295" y="30" width="130" height="70" fill="var(--panel)" stroke="var(--s1)"/>
<text x="360" y="50" fill="var(--ink)" font-size="9" text-anchor="middle">sanitize</text>
<text x="360" y="68" fill="var(--muted)" font-size="8" text-anchor="middle">NaN -&gt; null</text>
<text x="360" y="86" fill="var(--s1)" font-size="8" text-anchor="middle">valid everywhere</text>
</svg>
^ The default emits an invalid token silently; failing fast raises at the producer; sanitizing emits valid null — the two right choices are deliberate, the wrong one is the default.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the default emits bare tokens, that Python re-reads its own output (so the bug hides), that the default fails a strict parse, that allow_nan=False raises, and that sanitizing to null yields strict JSON.

```python filename=modules/teaching-and-portability/code/jsonnan-inter-01/jsonnan.py:95-116 COMPLETE
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
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if Python ever stops emitting the tokens or the sanitizer ever leaves one in:

```text filename=jsonnan.py --check
SELF-TEST — Python emits bare NaN/Infinity that it re-reads but strict parsers reject; sanitizing to null is valid
--------------------------------------------------------------------------------------------------------------------
  default json.dumps emits bare NaN/Infinity tokens = True
  Python json.loads re-reads its own output = True (bug stays hidden in Python)
  the default output fails a strict JSON parse = True
  allow_nan=False raises at serialization time = True
  sanitizing NaN/Inf to null yields strict JSON = True ({"ok": 1.0, "ratio": null, "score": null})
```

**The self-test asserts both that Python re-reads the bad output and that a strict parse fails — pinning the exact shape of the trap, a document valid in its home ecosystem and invalid everywhere else.**

## Definition of done

You can state that JSON's grammar has no NaN or Infinity and name the ordinary computations that produce those values.
You can explain why Python's default emits them as bare tokens and why a Python-to-Python round trip hides the problem.
You can explain why this specifically defeats JSON's purpose — interoperability across ecosystems.
You can describe the two deliberate fixes — allow_nan=False to fail fast, or sanitize to null/sentinel — and say why each beats the default.
You can predict what a strict parser (JavaScript's JSON.parse) does with the default output and why.

## Boss fight

Consider the round-trip meaning once you sanitize to null. Mapping NaN to null is valid JSON, but null is JSON's representation of "no value," and on the way back in a consumer reads null, not NaN — so the distinction between "this was NaN" and "this field was absent" is lost. If that distinction matters (NaN often means "computed but undefined," which is different from "missing"), null is lossy in a second way, and you may need a documented sentinel — a string "NaN", or an object {"special": "nan"} — that both sides agree to interpret. The lesson deepens: sanitizing is a choice about semantics, not just syntax, and the right target depends on what the special value meant.

Now consider large integers, a sibling trap in the same format. JSON's number grammar allows arbitrarily large integers, but many parsers (JavaScript especially) read all numbers as 64-bit floats, so an integer beyond 2^53 is silently rounded to a nearby value on parse — valid JSON, no error, wrong number. Unlike NaN this passes even a strict parse; the corruption is at the value level, in the consumer. The general principle unifies them: JSON's contract is narrower and looser than it looks, so a robust producer avoids the ragged edges — no NaN or Infinity, and large integers sent as strings — rather than trusting every consumer to handle them the same way.

**Sanitizing NaN to null is lossy in meaning (it collapses "undefined" into "missing"), so a distinction that matters needs a documented sentinel, not null; and the broader rule is to avoid JSON's ragged edges entirely — no NaN/Infinity, large integers as strings — since the contract is narrower and its parsers looser than they appear.**

## External resources

RFC 8259 defines JSON's number grammar as finite decimals, with no NaN or Infinity, which is why conforming parsers reject them.
Python's json module documentation describes the allow_nan parameter and its default, and notes that the NaN/Infinity output is a non-standard extension other parsers may not accept.
The topic's own modules on JSON type coercion and on comparing NaN cover the adjacent JSON-serialization and floating-point-special-value pitfalls this one sits between.
