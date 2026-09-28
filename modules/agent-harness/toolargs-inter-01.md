---
id: toolargs-inter-01
title: Validate a proposed tool call against the schema before dispatching — the model's arguments are not trusted input
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: An agent lets a model call tools by emitting a tool name and a JSON object of arguments, but that JSON is generated text, not a checked function call: the model can omit a required argument, give one the wrong type, invent an argument the tool does not have, or supply a value outside the allowed set. A well-typed program never has these problems because the compiler enforces the signature; an agent has no enforcement between the model and the tool unless the harness adds it. Dispatch the model's arguments straight to the tool and a bad call reaches real code — a missing required field raises deep inside the tool, a string where an int was expected crashes or silently coerces, an invented argument is ignored or throws an opaque stack trace, an out-of-range enum drives an illegal branch — and the failure surfaces far from its cause. The fix is to validate every proposed call against the tool's declared schema (types, required fields, enums) before dispatching, returning a structured error as the observation when it fails, which both stops the malformed call from touching the tool and tells the model exactly what to fix. On a fixture, get_weather (required string city, optional units in ['c','f'], optional int days) is given five proposed calls: the valid one passes, and a missing city, a string 'three' for days, an invented 'country' argument, and 'kelvin' outside the enum are each rejected with a precise reason — so the validated harness dispatches only the one well-formed call.
eli5: When an app lets you fill out a form, it checks your answers before submitting — this box needs a number, that box can't be blank, this dropdown only allows certain choices. An AI agent calling a tool is filling out a form too, except the AI writes the answers freely and sometimes writes nonsense: it leaves a required box empty, types a word where a number goes, or makes up a box that doesn't exist. If nobody checks the form first, the broken answers go straight into the machine and jam it. The fix is the same as the web form: check every answer against the rules before submitting, and if something's wrong, say exactly what — so the AI can fix it and try again.
---

## Why this module

An agent's tool calls look like function calls but are not: the arguments are text a model wrote, with no compiler between the writing and the running. Treat that text as a trustworthy call and the first malformed one — a missing field, a wrong type, an invented argument — lands inside your tool as a crash whose stack trace points everywhere except the actual problem, which was that the call should never have been dispatched.

An agent lets a language model call tools by emitting a tool name and a JSON object of arguments. That JSON is generated text, not a checked function call: the model can omit a required argument, give an argument the wrong type, invent an argument the tool does not have, or supply a value outside the allowed set. A well-typed program never has these problems because the compiler enforces the signature; an agent has no such enforcement between the model and the tool unless the harness adds it. Dispatch the model's arguments straight to the tool and a bad call reaches real code: a missing required field raises deep inside the tool, a string where an int was expected crashes the arithmetic or silently coerces and does the wrong thing, an invented argument is ignored (so the call does something other than intended) or rejected with an opaque stack trace, and an out-of-range enum drives an illegal branch. The failure surfaces far from its cause, as a tool crash rather than a bad call.

The fix is to validate every proposed call against the tool's declared schema before dispatching it. The schema states each parameter's type, whether it is required, and any enum of allowed values; validation checks the proposed arguments against that and either passes the call through or returns a structured error — "missing required arg city", "arg days must be int" — as the observation. That error is doubly useful: it stops the malformed call from ever touching the tool, and it tells the model exactly what was wrong, so the next turn can produce a corrected call. Validation turns an untrusted blob of generated JSON into either a well-formed call or an actionable error — the same discipline a web server applies to request bodies. This module checks five proposed calls against a schema and dispatches only the valid one.

**A model's tool-call arguments are untrusted generated JSON, so the harness must validate them against the tool's schema — types, required fields, enums — before dispatch, rejecting a malformed call with a structured error rather than letting it crash or misbehave inside the tool.**

## Concepts

**Validation** walks the schema in the order a call goes wrong: required fields present, no unknown arguments, then each argument's type and enum. The first violation returns a specific reason; passing all of them returns ok.

```python filename=modules/agent-harness/code/toolargs-inter-01/toolargs.py:55-70 COMPLETE
def validate(schema, args):
    """Check args against the schema; return (ok, reason). The order mirrors how a call is malformed."""
    params = schema["params"]
    for name, spec in params.items():
        if spec.get("required") and name not in args:
            return False, "missing required arg '%s'" % name
    for name in args:
        if name not in params:
            return False, "unknown arg '%s'" % name
    for name, value in args.items():
        spec = params[name]
        if not type_ok(value, spec["type"]):
            return False, "arg '%s' must be %s, got %r" % (name, spec["type"], value)
        if "enum" in spec and value not in spec["enum"]:
            return False, "arg '%s'=%r not in enum %s" % (name, value, spec["enum"])
    return True, "ok"
```

**The type check** compares a JSON value against the declared type — where a JSON number loads as an int and a JSON string as a str, so `"three"` fails an int parameter. Guarding bool out of int matters because a bool is an int subclass.

```python filename=modules/agent-harness/code/toolargs-inter-01/toolargs.py:46-52 COMPLETE
def type_ok(value, declared):
    """Does the value match the declared type? (json ints load as int, strings as str)."""
    if declared == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "str":
        return isinstance(value, str)
    return True
```

<svg role="img" aria-label="A validation gate: the model's proposed JSON arguments pass through a schema check that either dispatches a well-formed call to the tool or returns a structured error observation" viewBox="0 0 300 108" width="300" height="108">
  <text x="6" y="12" fill="var(--muted)" font-size="8">the schema check is the boundary between the model and the tool</text>
  <rect x="6" y="40" width="56" height="24" fill="none" stroke="var(--line)"/><text x="12" y="55" fill="var(--muted)" font-size="7">model JSON</text>
  <rect x="96" y="38" width="52" height="28" fill="none" stroke="var(--s1)"/><text x="104" y="50" fill="var(--muted)" font-size="7">validate</text><text x="104" y="60" fill="var(--muted)" font-size="7">vs schema</text>
  <line x1="62" y1="52" x2="96" y2="52" stroke="var(--muted)"/>
  <rect x="216" y="20" width="76" height="20" fill="none" stroke="var(--s1)"/><text x="222" y="33" fill="var(--muted)" font-size="7">DISPATCH → tool</text>
  <rect x="216" y="64" width="76" height="20" fill="none" stroke="var(--s2)"/><text x="222" y="77" fill="var(--muted)" font-size="7">error observation</text>
  <line x1="148" y1="46" x2="216" y2="30" stroke="var(--s1)"/><text x="160" y="34" fill="var(--muted)" font-size="6">valid</text>
  <line x1="148" y1="58" x2="216" y2="74" stroke="var(--s2)"/><text x="158" y="76" fill="var(--muted)" font-size="6">malformed</text>
</svg>
^ Every proposed call passes through the schema check first: a well-formed call is dispatched to the tool, and a malformed one becomes a structured error observation that never reaches the tool but tells the model what to fix.

**Validation sits between the model and the tool, converting untrusted generated arguments into either a well-formed dispatch or a specific, correctable error — the enforcement a compiled call signature would give but an agent otherwise lacks.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/toolargs-inter-01/toolargs.py

The fixture's tool declares a required string, an enum, and an int.

```json filename=modules/agent-harness/code/toolargs-inter-01/toolargs.json:3-10 COMPLETE
  "schema": {
    "name": "get_weather",
    "params": {
      "city": {"type": "str", "required": true},
      "units": {"type": "str", "required": false, "enum": ["c", "f"]},
      "days": {"type": "int", "required": false}
    }
  },
```

Run `--validate` on the five proposed calls.

```text filename=--validate
VALIDATE — each proposed call checked against the get_weather schema
------------------------------------------------------------------------
  valid            {"city": "paris", "units": "c", "days": 3} PASS
  missing_required {"units": "f"}                             REJECT: missing required arg 'city'
  wrong_type       {"city": "paris", "days": "three"}         REJECT: arg 'days' must be int, got 'three'
  unknown_arg      {"city": "paris", "country": "france"}     REJECT: unknown arg 'country'
  bad_enum         {"city": "paris", "units": "kelvin"}       REJECT: arg 'units'='kelvin' not in enum ['c', 'f']
```

One call passes and four are rejected, each for a different, common way a model produces a malformed call. The valid call supplies all the right names, types, and an in-enum unit. `missing_required` omits the required `city` — the kind of call a model makes when it thinks context implies the value; dispatched unvalidated, the tool raises a KeyError on `args["city"]` somewhere in its body. `wrong_type` gives the string `"three"` for `days`, which a model writes surprisingly often; the tool would either crash on `range("three")` or, worse, silently misuse it. `unknown_arg` invents `country`, a plausible-sounding parameter the tool does not have; unvalidated, it is silently dropped and the call does something subtly different from intended. `bad_enum` picks `kelvin`, a real temperature unit the tool does not support; unvalidated, it drives a branch that does not exist. Each rejection names the exact problem — not "invalid arguments" but which argument and why — which is what makes it correctable.

<svg role="img" aria-label="Five proposed calls checked against the schema: one passes and four fail for four distinct reasons — missing required, wrong type, unknown argument, and out-of-enum value" viewBox="0 0 300 120" width="300" height="120">
  <text x="6" y="12" fill="var(--muted)" font-size="8">four distinct ways a model call goes wrong, each named</text>
  <g font-size="7">
  <rect x="10" y="22" width="70" height="14" fill="var(--s1)"/><text x="14" y="32" fill="var(--panel)">valid</text><text x="90" y="32" fill="var(--muted)">→ PASS</text>
  <rect x="10" y="40" width="70" height="14" fill="none" stroke="var(--s2)"/><text x="14" y="50" fill="var(--muted)">missing_required</text><text x="90" y="50" fill="var(--muted)">→ no required 'city'</text>
  <rect x="10" y="58" width="70" height="14" fill="none" stroke="var(--s2)"/><text x="14" y="68" fill="var(--muted)">wrong_type</text><text x="90" y="68" fill="var(--muted)">→ days "three" not int</text>
  <rect x="10" y="76" width="70" height="14" fill="none" stroke="var(--s2)"/><text x="14" y="86" fill="var(--muted)">unknown_arg</text><text x="90" y="86" fill="var(--muted)">→ 'country' not a param</text>
  <rect x="10" y="94" width="70" height="14" fill="none" stroke="var(--s2)"/><text x="14" y="104" fill="var(--muted)">bad_enum</text><text x="90" y="104" fill="var(--muted)">→ 'kelvin' not in [c,f]</text>
  </g>
</svg>
^ Of the five proposed calls only the valid one passes; the other four fail four different schema rules — a missing required field, a wrong type, an invented argument, and an out-of-enum value — each reported as a specific reason the model can act on.

## Build

The point of validating is what it does to dispatch: which calls actually reach the tool. Run `--dispatch`.

```text filename=--dispatch
DISPATCH — unvalidated (trust the model) vs validated (check first)
------------------------------------------------------------------------
  UNVALIDATED: all 5 calls are sent to the tool --
    valid            -> would run
    missing_required -> reaches tool as a bug (missing required arg 'city')
    wrong_type       -> reaches tool as a bug (arg 'days' must be int, got 'three')
    unknown_arg      -> reaches tool as a bug (unknown arg 'country')
    bad_enum         -> reaches tool as a bug (arg 'units'='kelvin' not in enum ['c', 'f'])
  VALIDATED: only well-formed calls dispatch; the rest become error observations --
    valid            -> DISPATCH
    missing_required -> error observation (not run)
    wrong_type       -> error observation (not run)
    unknown_arg      -> error observation (not run)
    bad_enum         -> error observation (not run)
```

Unvalidated, all five calls reach the tool, so four of them become bugs inside the tool's code — four different crashes or misbehaviors, each surfacing as a stack trace or a wrong result far from the real cause. Validated, only the one well-formed call dispatches; the other four are turned into error observations that never touch the tool. The difference is not just safety, it is recoverability: an error observation goes back to the model as "missing required arg city", and the model's next turn can supply it, so a malformed call costs one wasted step instead of a crash or a silently wrong action. This is why validation belongs in the harness and not only in each tool — every tool would otherwise have to re-implement the same argument checking, and a tool that forgot to would be the one that crashes. The list of what actually dispatched is a one-line filter over the validation result.

```json filename=modules/agent-harness/code/toolargs-inter-01/toolargs.json:11-17 COMPLETE
  "proposed_calls": [
    {"label": "valid", "args": {"city": "paris", "units": "c", "days": 3}},
    {"label": "missing_required", "args": {"units": "f"}},
    {"label": "wrong_type", "args": {"city": "paris", "days": "three"}},
    {"label": "unknown_arg", "args": {"city": "paris", "country": "france"}},
    {"label": "bad_enum", "args": {"city": "paris", "units": "kelvin"}}
  ]
```

<svg role="img" aria-label="Five proposed calls: without validation all five reach the tool and four crash it, with validation only the valid call dispatches and four become error observations" viewBox="0 0 300 120" width="300" height="120">
  <text x="6" y="12" fill="var(--muted)" font-size="8">unvalidated: 4 bugs reach the tool; validated: 1 clean dispatch</text>
  <text x="10" y="30" fill="var(--muted)" font-size="7">unvalidated</text>
  <g transform="translate(10,36)" font-size="6">
  <rect x="0" y="0" width="42" height="14" fill="var(--s1)"/><text x="4" y="10" fill="var(--panel)">valid</text>
  <rect x="46" y="0" width="30" height="14" fill="var(--s2)"/><rect x="80" y="0" width="30" height="14" fill="var(--s2)"/><rect x="114" y="0" width="30" height="14" fill="var(--s2)"/><rect x="148" y="0" width="30" height="14" fill="var(--s2)"/>
  <text x="184" y="10" fill="var(--muted)">→ 4 crash the tool</text>
  </g>
  <text x="10" y="76" fill="var(--muted)" font-size="7">validated</text>
  <g transform="translate(10,82)" font-size="6">
  <rect x="0" y="0" width="42" height="14" fill="var(--s1)"/><text x="4" y="10" fill="var(--panel)">valid → DISPATCH</text>
  <rect x="46" y="0" width="30" height="14" fill="none" stroke="var(--line)"/><rect x="80" y="0" width="30" height="14" fill="none" stroke="var(--line)"/><rect x="114" y="0" width="30" height="14" fill="none" stroke="var(--line)"/><rect x="148" y="0" width="30" height="14" fill="none" stroke="var(--line)"/>
  <text x="184" y="10" fill="var(--muted)">→ 4 error observations</text>
  </g>
</svg>
^ Without validation all five calls reach the tool and the four malformed ones become bugs inside it; with validation only the valid call dispatches and the four malformed ones become correctable error observations that never run.

## Definition of done

The self-test pins the pass and each distinct rejection.

```python filename=modules/agent-harness/code/toolargs-inter-01/toolargs.py:110-119 COMPLETE
    valid_passes = validate(schema, by_label["valid"])[0]
    print("  the well-formed call passes validation = %s" % valid_passes)

    ok, reason = validate(schema, by_label["missing_required"])
    missing_caught = not ok and "missing required" in reason
    print("  a missing required arg is rejected = %s (%s)" % (missing_caught, reason))

    ok, reason = validate(schema, by_label["wrong_type"])
    type_caught = not ok and "must be int" in reason
    print("  a wrong-typed arg is rejected = %s (%s)" % (type_caught, reason))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the valid call passes; a missing required, wrong type, unknown arg, and bad enum are each caught
------------------------------------------------------------------------------------------------------------
  the well-formed call passes validation = True
  a missing required arg is rejected = True (missing required arg 'city')
  a wrong-typed arg is rejected = True (arg 'days' must be int, got 'three')
  an invented (unknown) arg is rejected = True (unknown arg 'country')
  an out-of-enum value is rejected = True (arg 'units'='kelvin' not in enum ['c', 'f'])
```

**Done means each failure mode is caught with a specific reason: the well-formed call passes, and a missing required arg, a wrong-typed arg, an invented argument, and an out-of-enum value are each rejected before dispatch with a message naming the offending argument — so only the one valid call reaches the tool and the four malformed calls become correctable error observations.**

## Boss fight

Predict two ways validation is more than a type check, because the schema is also a contract the model reads and a security boundary the tool relies on.

The first trap is that the schema serves two audiences and both must agree. It validates the model's output, but it is also what the model was *shown* to know how to call the tool — so a schema that is stricter than what the model was told, or a tool whose real requirements drift from its published schema, produces calls that are individually well-formed and still wrong. If the model's tool description says `days` is optional but the tool actually needs it, validation passes a call the tool then rejects; if the description omits an enum that validation enforces, the model keeps guessing values that keep getting rejected, burning turns. The schema shown to the model and the schema used to validate must be the same source of truth, and the error messages must go *back to the model* in a form it can act on — "arg days must be int" is correctable, a bare `False` or a Python traceback is not. Validation is only half of a loop; the other half is the model reading the rejection and fixing the call, which only works if the rejection is specific and the contract is consistent.

The second trap is that structural validity is not safety — a call can match the schema perfectly and still be dangerous, so type-checking is necessary but not sufficient. `city` being a required string does not stop it from being `"'; DROP TABLE"`, a path-traversal `"../../etc/passwd"`, or a URL pointing at an internal address for a tool that fetches; `days` being an int does not stop it from being 100000000 and exhausting memory. Schema validation guards shape, not intent, so it must be paired with value-level checks the schema cannot express (ranges, formats, allow-lists), with the tool treating even validated arguments as untrusted (parameterized queries, sandboxed file access, egress limits), and with authorization checks that the *agent* is allowed to make this call at all. And the model's arguments are only one untrusted input; the tool's *output* is another (a fetched page can carry a prompt injection, per the harness's broader threat model). The discipline is layered: validate the shape at the harness boundary so malformed calls never dispatch, then validate the values and enforce authorization at the tool so well-formed but harmful calls are still contained — because the model is a capable but unreliable and potentially manipulated source, and neither layer alone is enough.

**Schema validation is necessary but not sufficient: the schema the model is shown and the schema used to validate must be one source of truth with model-readable error messages (or the correction loop stalls), and structural validity does not imply safety — a schema-valid argument can still be an injection, a huge value, or an unauthorized target — so pair harness-level shape validation with tool-level value checks, sandboxing, and authorization, treating the model's arguments (and its tools' outputs) as untrusted throughout.**

## External resources

The tool/function-calling documentation for any major model API and the JSON Schema specification — how tools declare parameter types, required fields, and enums, and why the runtime must validate the model's arguments against that schema rather than trusting them.

Writing on agent and LLM security (e.g., the OWASP Top 10 for LLM applications) — why model outputs, including tool-call arguments, are untrusted input, and the layered defenses (validation, sandboxing, authorization) a tool needs beyond shape-checking.

The companion unknown-tool-name and observation-truncation modules in this topic — all three are the harness enforcing a contract at the model/tool boundary: an unknown tool, malformed arguments, and oversized outputs each become a structured observation the model can act on rather than a crash.
