---
id: harness-inter-23
title: Repair the model's tool-call JSON before parsing — or a code fence aborts a turn that expressed a perfect call
topic: agent-harness
level: intermediate
status: ready
time: 16 min
summary: The harness turns the model's text into a tool call by parsing it as JSON, and a strict parser accepts only perfectly-formed JSON. But models, trained on prose and Markdown, routinely emit JSON that is clear but not strictly valid: wrapped in a code fence, ending with a trailing comma, a similar surface slip. The call is unambiguous, but json.loads raises on the extra characters, and if the harness treats a parse failure as a hard error it throws away the whole step. A lightweight repair pass — strip the code fence, remove trailing commas — fixes the common malformations before parsing, with no model round-trip, and because the tool name and arguments are untouched, repairing them cannot change the call's meaning. What repair must not do is pretend to fix everything: a genuinely malformed structure stays broken and fails loudly. On four candidates — valid, fenced, trailing-comma, and missing-comma — strict parsing accepts 1 of 4 while repair-then-parse accepts 3, leaving the structural missing-comma error to fail.
eli5: If someone hands you a note that says "buy milk" but they wrapped it in a decorative envelope and added a stray comma, you can still read it perfectly — you just take it out of the envelope and ignore the comma. A too-strict robot would throw the whole note away because of the envelope. But if the note is actually garbled — words missing so you can't tell what they meant — you shouldn't guess; you ask again. Repairing tool-call JSON is unwrapping the envelope, not guessing at garbled notes.
---

## Why this module

An agent's tool call arrives as text that has to be parsed, and the model's harmless formatting habits produce text that is unmistakably a valid call yet not valid JSON — so a strict parser rejects a call whose meaning was never in doubt.

The loop runs on parsing: the model emits text, the harness reads it as JSON to recover the tool name and arguments, and executes. A strict JSON parser is unforgiving by design — it accepts only well-formed JSON and raises on anything else. The trouble is that the model was trained on a world of Markdown and prose, so it habitually decorates its output: it wraps the call in a ```json code fence because that is how JSON appears in documentation, or it leaves a trailing comma because that is a common and forgivable coding style. None of these change the call — the tool is "read", the path is "a.txt", unambiguous — but each adds characters that make `json.loads` raise. If the harness treats a parse failure as a hard error, it discards the step, re-prompts the model, and wastes a turn recovering from a mistake that altered no argument. A whole run stutters on formatting.

**The model expresses tool calls in text that is often clear but not strictly valid JSON — code fences, trailing commas — so a strict parser aborts turns whose actual call was never ambiguous.**

A lightweight repair pass recovers the common slips before parsing, with no model round-trip. Strip a code fence if the string is wrapped in one; remove a trailing comma before a closing brace or bracket. These are purely syntactic fixes on the mistakes models make most, and because they touch only the wrapping and never the tool name or arguments, they cannot change what the call means. The one thing repair must not do is over-reach: a genuinely malformed structure — a missing comma between fields, a truncated object — is not something a few regexes can safely reconstruct, so repair leaves it broken and lets it fail loudly rather than guessing at a call the model never made. This module parses four candidates strictly and with repair, and shows repair recover the slips while the structural error still fails.

## Concepts

**Strict parsing** accepts only well-formed JSON. It is correct but brittle: any extra or missing character raises, discarding the call.

**Model formatting slips** are syntactic, not semantic: a Markdown code fence around the JSON, a trailing comma before a closing brace. They add or misplace characters without changing the tool or arguments.

```python filename=modules/agent-harness/code/harness-inter-23/repair.py:44-50 COMPLETE
def parses(raw):
    """Does the string parse as strict JSON?"""
    try:
        json.loads(raw)
        return True
    except json.JSONDecodeError:
        return False
```

**Repair** strips the fence and removes trailing commas before parsing. Because it edits only the wrapping, it recovers the call without risk of changing its meaning.

```python filename=modules/agent-harness/code/harness-inter-23/repair.py:53-59 COMPLETE
def repair(raw):
    """Fix common model slips: strip a Markdown code fence and remove trailing commas. Does not fix structure."""
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)   # opening fence
    s = re.sub(r"\s*```$", "", s)             # closing fence
    s = re.sub(r",(\s*[}\]])", r"\1", s)      # trailing comma before } or ]
    return s.strip()
```

**Repair must not over-reach.** A structural error (a missing comma between fields, a truncation) cannot be safely reconstructed by regex, so repair leaves it broken and lets it fail rather than guessing a call the model never made.

**Salvage slips, escalate real errors.** Repair recovers the unambiguous, syntactic mistakes and lets the genuinely-broken ones fail loudly — the right split, because inventing a call is worse than a clean retry.

**A strict parser wastes turns on formatting the model got harmlessly wrong, so repair the surface slips (fences, trailing commas) before parsing — but only those, letting structural errors fail rather than guessing.**

<svg role="img" aria-label="Raw model text goes to a strict parser that aborts on a fence; the repair pass unwraps it first so the same call parses" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">model text → parse → tool call</text>
  <rect x="15" y="26" width="66" height="18" fill="var(--panel)" stroke="var(--grid)"/><text x="20" y="38" fill="var(--ink)" font-size="7" font-family="monospace">```json {..}```</text>
  <text x="83" y="30" fill="var(--s2)" font-size="8">→ strict</text>
  <text x="120" y="30" fill="var(--s2)" font-size="8">✕ abort turn</text>
  <text x="83" y="42" fill="var(--s1)" font-size="8">→ repair</text>
  <rect x="120" y="34" width="60" height="14" fill="var(--s1)"/><text x="124" y="44" fill="var(--panel)" font-size="7">unwrap {..}</text>
  <text x="184" y="44" fill="var(--s1)" font-size="8">→ parses ✓</text>
  <text x="15" y="72" fill="var(--muted)" font-size="8">the strict path throws the turn away; the repair path unwraps and recovers it</text>
  <text x="15" y="86" fill="var(--muted)" font-size="8">a truly garbled call still fails on both paths — repair does not guess</text>
</svg>
^ The strict path aborts the turn on the fence; the repair path strips the wrapping so the identical call parses, while a genuinely garbled call fails on both.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/harness-inter-23/repair.py

The fixture is four raw model outputs: a valid call, a fenced one, a trailing-comma one, and a structurally broken one.

```json filename=modules/agent-harness/code/harness-inter-23/calls.json:3-8 COMPLETE
  "candidates": [
    {"id": "valid",          "raw": "{\"tool\": \"read\", \"path\": \"a.txt\"}"},
    {"id": "fenced",         "raw": "```json\n{\"tool\": \"read\", \"path\": \"a.txt\"}\n```"},
    {"id": "trailing_comma", "raw": "{\"tool\": \"read\", \"path\": \"a.txt\",}"},
    {"id": "missing_comma",  "raw": "{\"tool\": \"read\" \"path\": \"a.txt\"}"}
  ]
```

Run `--parse` to try each under strict parsing and after repair.

```text filename=--parse
PARSE — strict parsing vs repair-then-parse
------------------------------------------------------------
  candidate        strict   repaired
  valid            True     True
  fenced           False    True
  trailing_comma   False    True
  missing_comma    False    False
```

The valid call parses both ways — repair is a no-op on already-valid JSON, so it never hurts. The fenced call fails strict parsing because of the surrounding ```json and ``` characters, but after the fence is stripped it parses: the call inside was always `{"tool": "read", "path": "a.txt"}`. The trailing-comma call fails strict parsing on the comma before the closing brace, and parses once that comma is removed. The missing-comma call fails both ways: with `"read" "path"` there is no comma between the two fields, which is not a wrapper to strip but a genuine structural break, and repair correctly does not try to invent one. Three of the four express a clear call; repair recovers exactly those three.

<svg role="img" aria-label="Strict parsing accepts only the valid call; repair also accepts the fenced and trailing-comma calls; the missing-comma call fails both" viewBox="0 0 300 120" width="300" height="120">
  <text x="10" y="12" fill="var(--muted)" font-size="8">strict (left) vs repaired (right) — green kept, grey rejected</text>
  <text x="8" y="34" fill="var(--muted)" font-size="8">valid</text><rect x="90" y="26" width="40" height="12" fill="var(--s1)"/><rect x="140" y="26" width="40" height="12" fill="var(--s1)"/>
  <text x="8" y="54" fill="var(--muted)" font-size="8">fenced</text><rect x="90" y="46" width="40" height="12" fill="none" stroke="var(--grid)"/><rect x="140" y="46" width="40" height="12" fill="var(--s1)"/>
  <text x="8" y="74" fill="var(--muted)" font-size="8">trail-comma</text><rect x="90" y="66" width="40" height="12" fill="none" stroke="var(--grid)"/><rect x="140" y="66" width="40" height="12" fill="var(--s1)"/>
  <text x="8" y="94" fill="var(--muted)" font-size="8">miss-comma</text><rect x="90" y="86" width="40" height="12" fill="none" stroke="var(--grid)"/><rect x="140" y="86" width="40" height="12" fill="none" stroke="var(--s2)" stroke-dasharray="3 2"/>
  <text x="92" y="112" fill="var(--muted)" font-size="7">strict</text><text x="142" y="112" fill="var(--muted)" font-size="7">repaired</text>
  <text x="190" y="92" fill="var(--s2)" font-size="7">structural → fails</text>
</svg>
^ Strict keeps only the valid call; repair also keeps the fenced and trailing-comma calls; the structurally broken missing-comma call is rejected by both, correctly.

## Build

The count is the cost. Run `--recover`.

```text filename=--recover
RECOVER — calls recovered by each approach (of 4)
------------------------------------------------------------
  strict parsing:      1 recovered   ['valid']
  repair-then-parse:   3 recovered   ['valid', 'fenced', 'trailing_comma']
  still broken after repair: ['missing_comma']
```

Strict parsing recovers 1 call of 4; the other three become aborted turns. Repair-then-parse recovers 3 — the valid call plus the two syntactic slips — turning three would-be aborts into two salvaged calls, at the cost of a few regexes and no model round-trip. The fourth, missing-comma, stays broken under both, and that is the correct outcome: repair recovered every call whose meaning was clear and refused the one whose structure was genuinely broken. The point is not that repair fixes everything — it recovers 3 of 4, not 4 of 4 — but that it recovers the calls a strict parser needlessly threw away, while still failing loudly on the one that actually needs a retry.

<svg role="img" aria-label="Strict parsing recovers 1 of 4 calls; repair recovers 3 of 4, leaving 1 structural error broken" viewBox="0 0 300 100" width="300" height="100">
  <text x="10" y="12" fill="var(--muted)" font-size="8">tool calls recovered (of 4)</text>
  <line x1="70" y1="20" x2="70" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <line x1="70" y1="78" x2="285" y2="78" stroke="var(--grid)" stroke-width="1"/>
  <rect x="70" y="26" width="50" height="16" fill="var(--s2)"/><text x="124" y="38" fill="var(--muted)" font-size="8">strict: 1 of 4</text>
  <rect x="70" y="50" width="150" height="16" fill="var(--s1)"/><text x="224" y="62" fill="var(--muted)" font-size="8">repair: 3 of 4</text>
  <text x="70" y="94" fill="var(--muted)" font-size="8">repair salvages 2 aborted turns; the 4th (structural) still fails, correctly</text>
</svg>
^ Repair triples the recovered calls, turning two aborts into salvaged turns, while the fourth structural error stays broken under both — recovered are the clear calls, not all calls.

## Definition of done

The self-test pins it: a valid call parses both ways, strict rejects the slips, repair recovers them, the structural error stays broken, and repair recovers more than strict.

```python filename=modules/agent-harness/code/harness-inter-23/repair.py:93-106 COMPLETE
    valid_parses_both = parses(by_id["valid"]) and parses(repair(by_id["valid"]))
    print("  a valid call parses strictly and after repair = %s" % valid_parses_both)

    strict_rejects_slips = not parses(by_id["fenced"]) and not parses(by_id["trailing_comma"])
    print("  strict parsing rejects the fenced and trailing-comma calls = %s" % strict_rejects_slips)

    repair_recovers_slips = parses(repair(by_id["fenced"])) and parses(repair(by_id["trailing_comma"]))
    print("  repair recovers both slips = %s" % repair_recovers_slips)

    structural_stays_broken = not parses(repair(by_id["missing_comma"]))
    print("  the structural (missing-comma) error still fails after repair = %s" % structural_stays_broken)

    repair_beats_strict = sum(parses(repair(c["raw"])) for c in data["candidates"]) > sum(parses(c["raw"]) for c in data["candidates"])
    print("  repair recovers more calls than strict = %s (%d > %d of %d)" % (repair_beats_strict, sum(parses(repair(c["raw"])) for c in data["candidates"]), sum(parses(c["raw"]) for c in data["candidates"]), len(data["candidates"])))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — strict rejects the repairable slips; repair recovers them; the structural error still fails
--------------------------------------------------------------------------------------------------------
  a valid call parses strictly and after repair = True
  strict parsing rejects the fenced and trailing-comma calls = True
  repair recovers both slips = True
  the structural (missing-comma) error still fails after repair = True
  repair recovers more calls than strict = True (3 > 1 of 4)
--------------------------------------------------------------------------------------------------------
SELF-TEST PASS  valid_parses_both=True  strict_rejects_slips=True  repair_recovers_slips=True  structural_stays_broken=True  repair_beats_strict=True
```

**Done means the salvage-and-escalate split is proven: strict parsing recovers 1 of 4 calls while repair recovers 3 — the valid, fenced, and trailing-comma calls — and the missing-comma structural error stays broken under both, so repair rescued exactly the clear calls and refused to invent the broken one.**

## Boss fight

Repair recovered the slips here. Predict where a repair pass becomes dangerous, and what removes the need for it entirely. It is tempting to keep adding repair rules until nothing ever fails to parse.

Repair gets dangerous exactly when it stops being a safe syntactic unwrap and starts guessing at meaning. Stripping a fence or a trailing comma cannot change which tool or arguments the call names, so it is safe. But add a rule that "fixes" a missing comma by inserting one, or closes an unbalanced brace, or coerces a bare word into a string, and you are now reconstructing structure the model may not have intended — you can turn a truncated, half-formed call into a syntactically valid call that means something the model never asked for, and execute it. That is worse than a clean failure: a failed parse retries, but a mis-repaired call runs the wrong tool with confidence. So the repair pass must stay on the safe side of the line — recover only transformations that provably preserve meaning, and let anything ambiguous fail — because the cost of a false recovery (an unintended action) exceeds the cost of a retry.

The deeper fix is to make the model emit valid JSON in the first place, which good harnesses increasingly do with constrained decoding: at generation time the sampler is restricted to only tokens that keep the output valid against the tool's JSON schema, so a malformed call is literally unrepresentable — no fence, no trailing comma, no missing field, because the decoder could not have produced them. Constrained (or "structured") decoding, and provider-side function-calling that returns arguments as already-parsed objects, remove the parse-failure class of bug at the source, and where they are available they are better than repairing after the fact. Repair is the pragmatic fallback for when you only have raw text — a model or endpoint without constrained output — and even then it composes with the other guards: repair the surface, validate the repaired object against the schema (a repaired call can still name a nonexistent tool or a wrong argument type), and only then execute. Salvage what is safe, constrain what you can, and validate before you act.

```python filename=modules/agent-harness/code/harness-inter-23/repair.py:76-78 COMPLETE
    strict = [c["id"] for c in cands if parses(c["raw"])]
    repaired = [c["id"] for c in cands if parses(repair(c["raw"]))]
    broken = [c["id"] for c in cands if not parses(repair(c["raw"]))]
```

**Repair the model's surface JSON slips (code fences, trailing commas) before parsing so a strict parser does not abort turns whose call was clear — but keep repair to transformations that provably preserve meaning and let structural errors fail loudly, prefer constrained/structured decoding that makes invalid calls unrepresentable at the source, and always validate the repaired object against the schema before executing.**

## External resources

Documentation for structured-output and constrained decoding (for example OpenAI's structured outputs, or grammar/JSON-schema-constrained sampling in llama.cpp, Outlines, or Guidance) — how restricting the sampler to schema-valid tokens removes malformed tool calls at generation time.

Lenient JSON parsers and repair libraries (for example `json5`, `dirty-json`, or `json-repair`) — the productionized versions of the repair pass, with their rules and the caution about over-aggressive fixes.

The companion "validate a tool call against its schema before executing" and "return a tool error as an observation" modules — schema validation is the step after repair that catches wrong tools and argument types, and returning a parse or validation failure as an observation is how the loop recovers when repair cannot.
