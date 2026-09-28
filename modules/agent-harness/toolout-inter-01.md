---
id: toolout-inter-01
title: Validate a tool's returned payload against its contract — a tool can succeed and still hand back garbage the model will believe
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: A tool call goes wrong two ways. It can fail — raise or return an error — which a companion module handles by returning a structured error the harness branches on. Or it can succeed — return normally, no exception — and hand back a payload that violates its own contract: a required field null, a value out of range, the wrong type. A success is not a valid payload, and the harness's error handling never fires here because nothing errored. Forwarding that payload to the model unchecked is the bug: the model reasons over invalid data as fact — treating a null temperature as a real reading, or a sensor-glitch 250°C as the weather — and answers confidently wrong, or a later step that computes on the field crashes deep in the pipeline, far from the tool that produced the bad value. The fix mirrors input validation: a companion module validates the model's proposed arguments before dispatch; this validates the tool's returned payload after dispatch, against a declared output schema — required fields, types, ranges — and on a violation treats the success as a failure, returning a structured error rather than forwarding garbage. On a fixture where a weather tool declares temp_c in [-90, 60] and returns three success payloads (a valid 20, a null, and a 250), the unchecked path forwards all three and hands the model a None and an absurd 482°F, while the validated path forwards only the real 68°F and turns the other two into errors.
eli5: Imagine you ask an assistant to phone the weather station and write down the temperature. The assistant calls, comes back, and reports "the temperature is: blank" or "the temperature is 250 degrees" — the call went fine, they really did phone and really did write something down, but what they wrote is nonsense. If you just trust whatever they hand you, you will plan your day around a blank or an impossible number. The sensible move is to glance at what they wrote and check it makes sense — is it actually a number, is it in a possible range — before you use it, and if it is nonsense, treat the call as failed and try again. A successful phone call is not the same as a sensible answer, so you check the answer, not just whether the call happened.
---

## Why this module

A harness that calls tools has to guard the boundary in two directions, and it is easy to guard only one. A companion module makes the first case: the model's proposed tool-call arguments are untrusted, so validate them against the tool's schema before dispatching. That protects the tool from the model. This module is about the return trip — protecting the model, and the rest of the pipeline, from the tool.

The reason it gets missed is that harnesses equate "the call succeeded" with "the result is good." Success is a weak guarantee: it only means the tool returned without raising. It says nothing about whether the returned payload obeys the tool's own contract. A weather API can return HTTP 200 with a null temperature because a sensor was offline; a database query can succeed and return a row with a corrupt field; a flaky service can return a placeholder or an out-of-range value. No error is raised, so the harness's error handling never runs.

If the harness forwards that payload straight into the context, the model treats it as fact — it has no independent way to know the field is null rather than a real zero, or that 250°C is impossible. It reasons over the garbage and produces a confident wrong answer. Or worse, a later step computes on the field — converts it, compares it, sums it — and crashes far downstream, where the stack trace points at the arithmetic and not at the tool that returned the bad value.

**A tool that succeeds can still return a payload that violates its contract — a null field, an out-of-range value — and because nothing raised, the harness's error handling never fires, so forwarding it unchecked feeds the model garbage it will believe or crashes a later step far from the cause.**

## Concepts

The clean way to see it is that a tool call has two independent outcomes, not one: did it error, and is the payload valid. Those are separate axes. A call can error (handle it as a failure), or succeed with a valid payload (use it), or — the case this module is about — succeed with an invalid payload, which lives in the same "no error" bucket as the good case and is treated identically unless you check.

<svg role="img" aria-label="A two-by-two view of tool outcomes. The error axis: raised or returned normally. Only the returned-normally-and-valid cell is safe to use; returned-normally-but-invalid is the trap, sitting in the no-error column but holding bad data." viewBox="0 0 440 140">
<text x="20" y="14" fill="var(--muted)" font-size="9">a tool call has two outcomes, not one</text>
<rect x="40" y="26" width="170" height="40" fill="var(--panel)" stroke="var(--s2)"/>
<text x="125" y="42" fill="var(--s2)" font-size="9" text-anchor="middle">raised / returned error</text>
<text x="125" y="58" fill="var(--muted)" font-size="8" text-anchor="middle">handled: structured error</text>
<rect x="230" y="26" width="170" height="40" fill="var(--panel)" stroke="var(--s1)"/>
<text x="315" y="42" fill="var(--s1)" font-size="9" text-anchor="middle">success + valid payload</text>
<text x="315" y="58" fill="var(--muted)" font-size="8" text-anchor="middle">safe to use</text>
<rect x="230" y="76" width="170" height="40" fill="var(--panel)" stroke="var(--s2)" stroke-dasharray="4 3"/>
<text x="315" y="92" fill="var(--s2)" font-size="9" text-anchor="middle">success + invalid payload</text>
<text x="315" y="108" fill="var(--s2)" font-size="8" text-anchor="middle">the trap: no error, bad data</text>
<text x="125" y="96" fill="var(--muted)" font-size="8" text-anchor="middle">error handling</text>
<text x="125" y="110" fill="var(--muted)" font-size="8" text-anchor="middle">never fires here -&gt;</text>
</svg>
^ Erroring and payload-validity are separate axes; the dangerous cell is a success carrying an invalid payload, which the harness's error handling never touches because nothing errored.

The fix is symmetric with input validation, and stating it that way makes it hard to forget. The harness already (should) validate what goes into a tool: the arguments, against the input schema, before dispatch. It must equally validate what comes out: the payload, against the output schema, after dispatch. Same idea, other direction — required fields present, types correct, values in range — and a returned payload that fails the check is not a result, it is a failure.

<svg role="img" aria-label="A tool call flow with two validation gates. Before the tool: validate the model's arguments (input gate, present). After the tool: validate the returned payload (output gate). The naive harness has the input gate but the output gate is missing, so bad payloads flow straight to the model." viewBox="0 0 440 120">
<rect x="20" y="45" width="70" height="24" fill="var(--panel)" stroke="var(--line)"/><text x="55" y="60" fill="var(--ink)" font-size="8" text-anchor="middle">model</text>
<rect x="110" y="45" width="60" height="24" fill="var(--panel)" stroke="var(--s1)"/><text x="140" y="57" fill="var(--s1)" font-size="7" text-anchor="middle">input</text><text x="140" y="66" fill="var(--s1)" font-size="7" text-anchor="middle">check</text>
<rect x="190" y="45" width="60" height="24" fill="var(--panel)" stroke="var(--line)"/><text x="220" y="60" fill="var(--ink)" font-size="8" text-anchor="middle">tool</text>
<rect x="270" y="45" width="60" height="24" fill="var(--panel)" stroke="var(--s2)" stroke-dasharray="4 3"/><text x="300" y="57" fill="var(--s2)" font-size="7" text-anchor="middle">output</text><text x="300" y="66" fill="var(--s2)" font-size="7" text-anchor="middle">check</text>
<rect x="350" y="45" width="70" height="24" fill="var(--panel)" stroke="var(--line)"/><text x="385" y="60" fill="var(--ink)" font-size="8" text-anchor="middle">model</text>
<line x1="90" y1="57" x2="110" y2="57" stroke="var(--line)"/><line x1="170" y1="57" x2="190" y2="57" stroke="var(--line)"/><line x1="250" y1="57" x2="270" y2="57" stroke="var(--line)"/><line x1="330" y1="57" x2="350" y2="57" stroke="var(--line)"/>
<text x="140" y="88" fill="var(--s1)" font-size="7" text-anchor="middle">present</text>
<text x="300" y="88" fill="var(--s2)" font-size="7" text-anchor="middle">often missing</text>
</svg>
^ Input validation guards the tool from the model's arguments; output validation guards the model from the tool's payload — the same gate, the other direction, and the one the naive harness leaves out.

Treating a contract-violating success as a failure is what makes the two paths converge. Once the output check flags a bad payload, the harness does exactly what it does for a raised exception: return a structured error observation the loop can branch on — retry the call, try a fallback, or report honestly — rather than passing the payload downstream. The tool's contract is enforced on the way out, so the model only ever sees data that at least obeys the shape the tool promised.

**Validate the returned payload against the output schema after dispatch, mirroring the input validation before it; a payload that fails the check is a failure, not a result, and is turned into a structured error rather than forwarded.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/toolout-inter-01. The fixture is a weather tool's output contract and three success payloads it returned.

```json filename=modules/agent-harness/code/toolout-inter-01/toolout.json:3-8 COMPLETE
  "schema": {"temp_c_min": -90, "temp_c_max": 60},
  "responses": [
    {"temp_c": 20, "conditions": "sunny"},
    {"temp_c": null, "conditions": "cloudy"},
    {"temp_c": 250, "conditions": "clear"}
  ]
```

The validator checks the returned payload against the contract — a numeric temperature in range, a non-empty conditions string.

```python filename=modules/agent-harness/code/toolout-inter-01/toolout.py:30-40 COMPLETE
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
```

Downstream, a later step computes on the field — here converting to Fahrenheit — which is where a bad value bites.

```python filename=modules/agent-harness/code/toolout-inter-01/toolout.py:43-47 COMPLETE
def to_fahrenheit(temp_c):
    """A downstream computation on the field -- what a later step (or the model) does with it."""
    if not isinstance(temp_c, (int, float)):
        return None  # cannot compute on a non-number: garbage in, nothing out
    return temp_c * 9 / 5 + 32
```

The validated path forwards only payloads that pass; the rest become structured errors.

```python filename=modules/agent-harness/code/toolout-inter-01/toolout.py:55-64 COMPLETE
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
```

Before running it, predict: all three responses are successful returns, but two — the null and the 250 — violate the contract. Run `--validate`:

```text filename=toolout.py --validate
VALIDATE — each returned payload against the output contract
----------------------------------------------------------------
  {'temp_c': 20, 'conditions': 'sunny'} ok  
  {'temp_c': None, 'conditions': 'cloudy'} VIOLATION  temp_c is not a number (None)
  {'temp_c': 250, 'conditions': 'clear'} VIOLATION  temp_c 250 out of range [-90, 60]
----------------------------------------------------------------
  every one of these was a successful return -- no error was raised
```

The prediction holds. The first payload is valid; the second has a null temperature (the sensor was down but the API still returned 200); the third reads 250°C, a physical impossibility from a glitchy sensor. None of these raised — they are all successful returns — so error handling alone would treat all three as good.

Now watch what reaches the model each way. Run `--forward`:

```text filename=toolout.py --forward
FORWARD — what reaches the model, unchecked vs validated
----------------------------------------------------------------
  unchecked path forwards 3 payloads:
      temp_c=20    -> 68.0 degrees F  (model believes this)
      temp_c=None  -> None degrees F  (model believes this)
      temp_c=250   -> 482.0 degrees F  (model believes this)
  validated path forwards 1 payload(s):
      temp_c=20    -> 68.0 degrees F
  validated path turns 2 into errors:
      temp_c is not a number (None)
      temp_c 250 out of range [-90, 60]
----------------------------------------------------------------
  unchecked reaches the model with a None and an absurd 482; validated forwards only the real reading
```

The unchecked path forwards all three: the model sees a real 68°F, a None it will try to reason about (or crash on), and 482°F reported as the actual temperature. Two of the three values the model receives are garbage, and nothing flagged them. The validated path forwards only the one real reading and converts the other two into structured errors — a null-field error and a range error — which the harness can retry or report. Same tool, same three successful returns; the difference is entirely the output check.

<svg role="img" aria-label="Three payloads flowing to the model. Unchecked: all three arrive, labeled 68 F valid, None garbage, 482 F absurd. Validated: only 68 F arrives; the null and 250 are diverted to an errors box." viewBox="0 0 440 150">
<text x="20" y="14" fill="var(--muted)" font-size="9">unchecked forwards all three</text>
<rect x="30" y="24" width="70" height="16" fill="var(--s1)"/><text x="65" y="36" fill="var(--ink)" font-size="8" text-anchor="middle">68 F ok</text>
<rect x="110" y="24" width="90" height="16" fill="var(--s2)"/><text x="155" y="36" fill="var(--s2)" font-size="8" text-anchor="middle">None (garbage)</text>
<rect x="210" y="24" width="100" height="16" fill="var(--s2)"/><text x="260" y="36" fill="var(--s2)" font-size="8" text-anchor="middle">482 F (absurd)</text>
<text x="325" y="36" fill="var(--muted)" font-size="8">-&gt; model</text>
<text x="20" y="76" fill="var(--muted)" font-size="9">validated forwards only the valid one</text>
<rect x="30" y="86" width="70" height="16" fill="var(--s1)"/><text x="65" y="98" fill="var(--ink)" font-size="8" text-anchor="middle">68 F ok</text>
<text x="110" y="98" fill="var(--muted)" font-size="8">-&gt; model</text>
<rect x="30" y="112" width="280" height="18" fill="var(--panel)" stroke="var(--s2)" stroke-dasharray="4 3"/>
<text x="170" y="124" fill="var(--s2)" font-size="8" text-anchor="middle">null-field error, range error  -&gt; retry / report</text>
</svg>
^ Unchecked, the model receives 68°F plus a None and an absurd 482°F; validated, only the real 68°F reaches it and the two violations become errors the harness can act on.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that every payload was a successful return, that the validator flags the two invalid ones, that the unchecked path forwards all of them, that the unchecked path yields garbage or absurd downstream values, and that the validated path forwards only the valid payload.

```python filename=modules/agent-harness/code/toolout-inter-01/toolout.py:106-121 COMPLETE
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
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if a violation ever slipped past the validator or the unchecked path ever stopped producing garbage:

```text filename=toolout.py --check
SELF-TEST — a tool can succeed with an invalid payload; unchecked forwarding reaches the model with garbage, validation blocks it
----------------------------------------------------------------------------------------------------------------
  every payload was a successful return (no error) = True
  the validator flags the invalid payloads = True (2 of 3)
  the unchecked path forwards every payload, violations included = True (3)
  the unchecked path yields garbage/absurd values = True ([68.0, None, 482.0])
  the validated path forwards only the valid payload = True (1 forwarded, 2 errored)
```

**The self-test first asserts every payload was a success (no error) and then that two are invalid — pinning the exact gap this module fills: the failures live entirely inside the no-error bucket, so error handling alone would pass them all and only an output check catches them.**

## Definition of done

You can explain why "the call succeeded" does not imply "the payload is valid," and give examples of contract-violating successes.
You can explain why the harness's error handling never fires on a success with a bad payload.
You can explain the two harms of forwarding it unchecked — the model reasoning over garbage, and a downstream crash far from the tool.
You can describe output validation as the mirror of input validation, and why a failed output check is treated as a tool failure.
You can explain why turning a violation into a structured error lets the loop retry, fall back, or report.

## Boss fight

Suppose you validate types and ranges and it still lets a bad value through — the tool returns a temperature of 15°C when the real temperature is 30°C, perfectly in range and the wrong number. Reason about what output validation can and cannot do. Schema validation is a shape check, not a truth check: it can catch a null, a wrong type, an impossible range, a missing field — structural violations that are provably wrong regardless of context — but it cannot catch a plausible-but-incorrect value, because nothing in the payload's shape reveals the error. So output validation is necessary and not sufficient; it removes the class of garbage that is detectable from the contract alone, and the residual class of plausible-wrong values needs other defenses — cross-checking against a second source, sanity bounds tied to context (the temperature yesterday was 29°C), or surfacing uncertainty rather than asserting. The lesson is to be precise about what the guarantee is: a validated payload is well-formed, not verified true.

Now the trap that makes output validation quietly incomplete: partial and nested payloads. A tool that returns a list of results, or a nested object, can be valid at the top level and contain one malformed element three levels down — and a shallow validator that checks only the outer shape passes it, so the bad element reaches the model or crashes a loop that iterates the list. Validation has to recurse to the granularity the downstream actually consumes: every element of a list that will be iterated, every field that will be read. And there is a decision to make on partial validity — if nine of ten results are valid and one is malformed, do you drop the bad one, error the whole batch, or forward the nine with the failure noted. That policy should be deliberate and consistent, because silently dropping the bad element hides a tool problem, while failing the whole batch throws away good data. Validate to the depth you consume, and decide the partial-failure policy on purpose.

**Output validation catches structurally-wrong payloads, not plausible-but-incorrect values, so it is necessary and not sufficient — a validated payload is well-formed, not verified true; and it must recurse to the granularity the downstream consumes, with a deliberate policy for partially-valid batches rather than a shallow top-level check.**

## External resources

The JSON Schema specification and validators (and typed-model libraries like Pydantic) are the standard way to declare and enforce an output contract on a tool's returned payload, not only on its inputs.
The tool-use and function-calling guides for major model APIs describe validating both the arguments a model proposes and the results a tool returns before the results re-enter the context.
The topic's own modules on validating a tool call against its schema, on returning structured errors from tools, and on grounding identifiers in real observations cover the neighboring boundary checks — the input side, the error side, and the hallucination side — that this one completes on the output side.
