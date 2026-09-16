---
id: outschema-inter-01
title: Validate the agent's final answer against its output schema — returning the first unchecked answer ships prose where the caller needs JSON
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: A tool-calling agent's loop is usually careful about the calls going into tools — it validates the model's proposed arguments against each tool's schema before dispatching — and careless about the value coming out: the final answer the harness returns to whatever called the agent. When a caller depends on a structured result (a JSON object with specific fields and types, because a downstream service or UI reads it programmatically), the model's first attempt is frequently prose where an object was promised, or JSON missing a required field, or a wrong type. A harness that returns the model's first response hands the caller that malformed answer, and the failure surfaces far downstream where it is expensive to trace back to "the agent didn't answer in the required shape." The fix mirrors what we already do for tool inputs, applied to the output: validate the final answer against the output schema before returning it, and on failure feed the specific validation error back to the model as an observation ("missing required field: currency") so its next attempt is a targeted repair, bounded by a small repair budget. On a fixture where the model produces prose, then JSON missing "currency", then a valid object, the no-validation harness returns the prose (garbage against the schema) while the validating harness rejects the prose (not parseable), rejects the partial object (naming the missing field), and accepts the valid object on repair attempt 3.
eli5: Imagine you ask a helper to fill out a form and hand it back — name and amount, both required. The helper first hands you a sticky note that says "it's about forty-two dollars," then a form with the amount but no name, then finally a properly filled form. If you just take whatever they hand you first, you file the sticky note and the office computer chokes on it later. Instead, you check each form against the blanks that must be filled, and each time one is wrong you hand it back saying exactly what's missing ("you left the name blank") — so the next try fixes that one thing, and you only accept the form once every required blank is filled correctly.
---

## Why this module

A tool-calling harness tends to guard one direction and trust the other. It validates every argument the model proposes to a tool — the input — and then takes the model's final answer and returns it to the caller unchecked. That is the same trust mistake in the opposite direction: the final answer is the model's output, and the model is exactly as capable of getting the output's shape wrong as it is of getting a tool call's arguments wrong. When the caller is a program that reads specific fields, an answer that merely "looks done" but is prose, or is missing a field, becomes a failure that surfaces far downstream — a KeyError in a service, a blank in a UI, a silently wrong number — where nobody thinks to blame the agent for not answering in the promised shape.

When a caller depends on a structured result — a JSON object with specific fields and types — the model's first attempt is frequently not that. It writes a sentence where an object was promised, emits JSON that is missing a required field, or gets a type wrong. A harness that simply returns the model's first response hands the caller that malformed answer. The output schema was supposed to be a contract, and returning the first unvalidated answer is exactly how a malformed result leaks past the harness and breaks the contract silently.

The fix mirrors what we already do for tool inputs, applied to the output: validate the final answer against the output schema before returning it, and when it fails, feed the *specific* validation error back to the model as an observation so its next attempt is a targeted repair, not another guess — bounded by a small repair budget so a model that can never produce the shape fails loudly instead of looping forever. The specificity is the point: "invalid output" teaches the model nothing, while "missing required field: currency (have: total)" tells it exactly what to add. This module runs the same three model answers through a no-validation harness and a validating one.

**An agent's final structured answer is untrusted output the same way a proposed tool call is untrusted input, so validate it against the declared output schema before returning it and, on failure, feed back the specific error for a bounded repair loop — an unvalidated answer that merely "looks done" is how malformed results leak past the harness to the caller, where the schema was supposed to be a contract.**

## Concepts

**The validator parses the answer as JSON and checks every required field and its type**, returning a precise, actionable error string instead of a bare boolean — that error is what the repair loop feeds back.

```python filename=modules/agent-harness/code/outschema-inter-01/outschema.py:58-71 COMPLETE
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
```

**The repair loop validates each answer and, on failure, lets the model try again with the error in hand** — bounded by max_repairs so a hopeless case terminates instead of spinning forever.

```python filename=modules/agent-harness/code/outschema-inter-01/outschema.py:79-90 COMPLETE
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
```

<svg role="img" aria-label="Two arrows into an agent: the input side (proposed tool call) is already validated against a tool schema; the output side (final answer) is the unguarded gap this module closes by validating against an output schema" viewBox="0 0 300 118" width="300" height="118">
  <text x="6" y="12" fill="var(--muted)" font-size="8">we guard the input already — the output is the unguarded side</text>
  <rect x="110" y="40" width="80" height="34" fill="none" stroke="var(--ink)"/><text x="128" y="60" fill="var(--ink)" font-size="8">agent loop</text>
  <line x1="20" y1="57" x2="108" y2="57" stroke="var(--s1)"/><text x="18" y="34" fill="var(--muted)" font-size="7">tool call in</text>
  <text x="20" y="88" fill="var(--s1)" font-size="6">✓ arg schema checked</text>
  <line x1="192" y1="57" x2="280" y2="57" stroke="var(--s2)"/><text x="210" y="34" fill="var(--muted)" font-size="7">final answer out</text>
  <text x="196" y="88" fill="var(--s2)" font-size="6">✗ output schema not checked → fix here</text>
  <text x="196" y="100" fill="var(--muted)" font-size="6">validate before returning to caller</text>
</svg>
^ The harness already validates the tool call going in against a tool schema; the final answer going out is the symmetric, usually unguarded gap — validating it against an output schema is the same discipline applied to the value the caller actually receives.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/outschema-inter-01/outschema.py

The fixture is the schema plus the three raw answers the model produces across attempts: prose, then JSON missing a field, then a valid object.

```json filename=modules/agent-harness/code/outschema-inter-01/outschema.json:3-8 COMPLETE
  "output_schema": {"total": "number", "currency": "string"},
  "max_repairs": 3,
  "candidates": [
    "The total is about 42 dollars.",
    "{\"total\": 42}",
    "{\"total\": 42, \"currency\": \"USD\"}"
  ]
```

Run `--answers`.

```text filename=--answers
ANSWERS — each candidate final answer checked against the output schema {'total': 'number', 'currency': 'string'}
------------------------------------------------------------------------------
  attempt 1: The total is about 42 dollars.
             -> REJECT -- not valid JSON (expected an object matching the schema)
  attempt 2: {"total": 42}
             -> REJECT -- missing required field: currency (have: total)
  attempt 3: {"total": 42, "currency": "USD"}
             -> VALID
------------------------------------------------------------------------------
  no-validation harness returns: 'The total is about 42 dollars.'
  validating harness returns:    {'total': 42, 'currency': 'USD'} (schema-valid = True)
```

Read the two harness lines at the bottom. The no-validation harness returns the model's first answer verbatim: the string "The total is about 42 dollars." — which the caller expected to be a JSON object with a numeric total and a string currency, and is instead a sentence. Nothing here is going to fail loudly at the agent; the failure is now the caller's problem, and it will look like the caller's bug. The validating harness walks the same three answers and rejects the first two for concrete, different reasons — the prose does not parse as JSON at all, and the second answer parses but is missing the required "currency" field — and accepts the third, returning the actual object the contract asked for. Same model, same three answers; the only difference is whether the harness checks the output before it leaves.

## Build

The repair loop is what turns rejection into a fix: each failure sends back the exact error, so the next answer targets it.

```text filename=--repair
REPAIR — the bounded repair loop, with the specific feedback sent back on each failure
----------------------------------------------------------------------------
  attempt 1: The total is about 42 dollars.
             verdict: REJECT -> feed back: 'not valid JSON (expected an object matching the schema)'
  attempt 2: {"total": 42}
             verdict: REJECT -> feed back: 'missing required field: currency (have: total)'
  attempt 3: {"total": 42, "currency": "USD"}
             verdict: VALID -> return to caller
```

The feedback on attempt 2 is the crux: "missing required field: currency (have: total)". It does not say "invalid" — it names the missing field and even lists what the answer *did* contain, so the model's next move is unambiguous: add a currency. That is why validation is worth pairing with feedback rather than a blind retry. A bare "try again" leaves the model to re-guess what was wrong and it may well produce a differently-broken answer; a precise error converts the retry into a correction. The bound (max_repairs) is the safety valve: if the model can never produce the shape — a schema it fundamentally cannot satisfy, a contradiction in the request — the loop stops after a few attempts and the harness fails loudly with the last error, rather than burning budget forever on an answer that will never validate. Precise feedback makes the common case converge fast; the bound makes the hopeless case terminate.

```python filename=modules/agent-harness/code/outschema-inter-01/outschema.py:136-145 COMPLETE
    ok1, _, err1 = validate(cands[0], schema)
    validation_rejects_prose = not ok1 and "JSON" in err1
    print("  validating harness rejects the prose answer = %s (%r)" % (validation_rejects_prose, err1))

    ok2, _, err2 = validate(cands[1], schema)
    validation_rejects_partial = not ok2 and "missing required field" in err2
    print("  validating harness rejects the partial answer = %s (%r)" % (validation_rejects_partial, err2))

    feedback_is_specific = "currency" in err2
    print("  the feedback names the missing field by name = %s" % feedback_is_specific)
```

<svg role="img" aria-label="A three-rung ladder: attempt 1 prose rejected, attempt 2 partial JSON rejected with a named missing field, attempt 3 valid and returned; each rejection feeds a specific error to the next rung" viewBox="0 0 300 128" width="300" height="128">
  <text x="6" y="12" fill="var(--muted)" font-size="8">each rejection feeds a specific error up to the next attempt</text>
  <text x="10" y="34" fill="var(--s2)" font-size="7">attempt 1: prose</text>
  <text x="150" y="34" fill="var(--muted)" font-size="6">REJECT: not JSON</text>
  <line x1="20" y1="40" x2="20" y2="58" stroke="var(--line)" stroke-dasharray="1 2"/>
  <text x="10" y="70" fill="var(--s2)" font-size="7">attempt 2: {total}</text>
  <text x="150" y="70" fill="var(--muted)" font-size="6">REJECT: missing currency</text>
  <line x1="20" y1="76" x2="20" y2="94" stroke="var(--line)" stroke-dasharray="1 2"/>
  <text x="10" y="106" fill="var(--s1)" font-size="7">attempt 3: {total, currency}</text>
  <text x="150" y="106" fill="var(--s1)" font-size="6">VALID → return</text>
  <text x="10" y="122" fill="var(--muted)" font-size="6">bound: stop after max_repairs if never valid</text>
</svg>
^ The loop climbs three rungs — prose (rejected: not JSON), partial object (rejected: missing currency, named), valid object (returned) — each rejection passing a specific error to the next attempt, and the repair budget caps the climb so a hopeless case terminates.

## Definition of done

The self-test pins the naive harness returning garbage, both rejections with their specific reasons, and the accepted repair.

```python filename=modules/agent-harness/code/outschema-inter-01/outschema.py:147-149 COMPLETE
    final, log, final_ok = run_with_validation(cands, schema, data["max_repairs"])
    validation_accepts_on_repair = final_ok and final == {"total": 42, "currency": "USD"}
    print("  validating harness accepts the repaired answer = %s (attempt %d, %r)" % (validation_accepts_on_repair, len(log), final))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the naive harness returns unparseable prose; the validating harness repairs to a schema-valid object
--------------------------------------------------------------------------------------------------------------
  no-validation harness returns a schema-INVALID answer = True ('The total is about 42 dollars.')
  validating harness rejects the prose answer = True ('not valid JSON (expected an object matching the schema)')
  validating harness rejects the partial answer = True ('missing required field: currency (have: total)')
  the feedback names the missing field by name = True
  validating harness accepts the repaired answer = True (attempt 3, {'total': 42, 'currency': 'USD'})
```

<svg role="img" aria-label="Two harness outcomes: no-validation returns the prose string to the caller as invalid output; validating returns the schema-valid object after repair" viewBox="0 0 300 96" width="300" height="96">
  <text x="6" y="12" fill="var(--muted)" font-size="8">same three answers, opposite deliverables to the caller</text>
  <text x="10" y="36" fill="var(--muted)" font-size="7">no validation</text>
  <rect x="90" y="26" width="180" height="16" fill="var(--s2)"/><text x="96" y="38" fill="var(--panel)" font-size="7">"about 42 dollars." (invalid)</text>
  <text x="10" y="68" fill="var(--muted)" font-size="7">validating</text>
  <rect x="90" y="58" width="180" height="16" fill="var(--s1)"/><text x="96" y="70" fill="var(--panel)" font-size="7">{total:42, currency:'USD'} (valid)</text>
</svg>
^ The no-validation harness delivers the prose string as the agent's answer — invalid against the schema the caller relies on — while the validating harness delivers the schema-valid object, the only difference being an output check the caller cannot add after the fact.

**Done means the trust gap and its fix are proven on real answers: the no-validation harness returns unparseable prose (schema-invalid) to the caller, while the validating harness rejects the prose ("not valid JSON"), rejects the partial object naming the missing field ("missing required field: currency"), and accepts the valid object on repair attempt 3 — so the final answer must be validated against the output schema before returning, with the specific error fed back for a bounded repair.**

## Boss fight

Predict two ways this output check can lull you into a false sense of correctness, because a schema that a value satisfies is not the same as a value that is right.

The first trap is that schema-valid is not the same as correct, and it is easy to let the check's green light stand in for actual quality. The validator here confirms shape: there is a numeric total and a string currency. It says nothing about whether the total is the *right* number or the currency the *right* code — an answer of {"total": -999, "currency": "ZZZ"} passes every check in this module and is still wrong. Output-schema validation is a guardrail against malformed results, not a correctness oracle, so it belongs alongside the things that check meaning (an eval on the answer's value, a business-rule check that the total is non-negative and the currency is one of the accepted set, a downstream sanity bound) and never in place of them. The danger is precisely that a passing schema check feels like verification; it verifies the contract's *form*, and treating that as verification of the answer is how a well-shaped wrong answer sails through. Tighten the schema toward meaning where you can — enums for currency, ranges for numbers — but know that no schema fully closes the gap between valid and correct.

The second trap is that the repair loop can mask a systematic failure and can itself run away if the bound or the feedback is wrong. If the model routinely needs three attempts to produce the shape, a loop that silently repairs it hides a real problem — a bad prompt, an under-specified schema, a model mismatched to the task — behind a higher latency and token cost that nobody sees because the final answer is always eventually valid. So the repair attempts should be *counted and surfaced*, not just tolerated: a rising repair rate is a signal, the same way a rising retry rate is. And the bound has to be real and the feedback has to actually reduce the error space, or the loop is worse than no loop: too high a max_repairs turns a hopeless request into a slow, expensive failure; feedback that is vague ("invalid output") gives the model nothing to correct, so it re-guesses and may oscillate between two broken shapes until the budget runs out. The loop is safe only when the feedback is specific enough to converge and the bound is low enough to give up — and when the fact that it had to repair at all is recorded, so a systematic shape problem shows up as a metric instead of hiding as latency.

**Schema-valid is not correct — the check guards the answer's form, not its meaning, so pair it with value-level evals and business-rule checks and never let a passing schema stand in for verification; and treat the repair loop as instrumented, not free — count and surface the repairs (a rising repair rate is a real signal), keep the feedback specific enough to converge and the bound low enough to fail loudly, because a silent repair loop hides a systematic shape problem behind cost and latency.**

## External resources

Documentation for structured-output and function-calling APIs (JSON mode, response-format/JSON-schema constraints, Pydantic/`instructor`-style validators) — how output schemas are declared and enforced, and why validation plus repair-on-error is the standard pattern for structured agent results.

Writing on guardrails and output validation for LLM systems (Guardrails-AI, the "validate then repair" pattern) — validating a model's output against a contract and returning a targeted error for correction, and why schema validity is necessary but not sufficient for correctness.

The companion tool-argument-validation and tool-error-as-observation modules in this topic — output validation is the same discipline applied to the value leaving the agent that argument validation applies to the value entering a tool, and the repair loop reuses the "feed the error back as an observation" mechanism.
