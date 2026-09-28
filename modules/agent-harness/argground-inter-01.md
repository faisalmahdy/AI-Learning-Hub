---
id: argground-inter-01
title: Ground identifier tool-arguments in what the agent actually observed — a schema-valid id can still be a hallucination
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: Validating a tool call against its schema is necessary and universal — the argument must be the right type, match the expected pattern, fall in the allowed set — but it catches a malformed call, not a well-formed lie, and language models produce well-formed lies constantly for one kind of argument: references to entities the model does not actually have in front of it. Asked to "pull up the invoice and refund it" without the invoice id in its context, a model does not stop and say it lacks the id; it generates one — "INV-9999", right prefix, plausible number — because producing a fluent, correctly-shaped token is exactly what it does. That fabricated id passes every schema check, because it is indistinguishable in form from a real id; it simply corresponds to no real invoice, so the tool fetches nothing, errors confusingly, or — the dangerous case — hits a different real record and acts on the wrong one. Schema validation cannot catch this because the flaw is not in the shape of the value but in its provenance. The fix is grounding: for arguments that are references (ids, filenames, record keys, user handles), require the value to appear somewhere the agent actually saw — a prior observation, the user's message, the retrieved context — and treat a reference that does not as ungrounded, rejecting it and making the agent find or ask for the real id rather than dispatch a fabrication. On a fixture where the agent has observed two invoice ids and proposes three schema-valid calls, one using an unobserved INV-9999, schema-only validation dispatches all three while grounding validation dispatches only the two real ones.
eli5: Imagine you ask a helper to grab "the library book" and hand it back, but you never told them the book's ID number. Instead of admitting they don't know it, they confidently write down a real-looking number — same format, right number of digits — that they just made up. If the librarian only checks that the number *looks* like a valid ID, they'll go pull whatever book happens to have it, which isn't your book at all. The safer rule is: the helper may only use an ID they actually saw somewhere — on your note, on the shelf, in an earlier answer — and if they don't have it, they have to go look it up or ask, not invent one that looks right. Checking the shape of the ID isn't enough; you have to check they didn't make it up.
---

## Why this module

Every agent harness validates tool arguments against a schema, and it should — a call with a missing field or a wrong type is broken and must be rejected before dispatch. But schema validation quietly answers only one question: is this argument well-formed? For a large class of arguments the harder question is a different one: is this argument real? Those are not the same, and the gap between them is where a specific, common agent failure lives.

The gap opens for reference arguments — values that point at an entity in the world: an id, a filename, a record key, an account handle. A model asked to act on such an entity, when it does not actually have the reference in its context, will not reliably stop and say so. It will emit a plausible value, because emitting fluent well-shaped tokens is its core behavior, and a fabricated id is every bit as well-shaped as a real one. The schema sees a valid id and waves it through. The tool then operates on a reference to nothing, or to something that happens to exist but is not what anyone meant.

This is not a malformed-input problem that better validation of shape can fix; it is a provenance problem. This module runs three schema-valid tool calls, one of which uses a fabricated id, through a schema-only gate and a grounding gate.

**Schema validation checks an argument's shape, not its provenance, so a model can pass a fabricated reference straight through — identifier arguments must be grounded, required to trace to a value the agent actually observed, or the tool acts on an invented id.**

## Concepts

The fixture is the set of ids the agent has actually observed, the schema pattern an id must match, and three proposed calls — two using observed ids and one using a fabricated one.

```json filename=modules/agent-harness/code/argground-inter-01/argground.json:3-9 COMPLETE
  "observed_ids": ["INV-1001", "INV-1002"],
  "id_pattern": "^INV-[0-9]+$",
  "calls": [
    {"tool": "fetch_invoice", "id": "INV-1001"},
    {"tool": "fetch_invoice", "id": "INV-9999"},
    {"tool": "fetch_invoice", "id": "INV-1002"}
  ]
```

Two checks. `schema_valid` asks whether the id matches the pattern — the right shape. `grounded` asks whether the id is one the agent actually observed — the right provenance. The `accepted` function dispatches on schema alone, or on schema plus grounding.

```python filename=modules/agent-harness/code/argground-inter-01/argground.py:33-49 COMPLETE
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
```

The two checks look at different things entirely: one at the string, one at the history of what the agent has seen. A fabricated id can only ever fail the second.

<svg role="img" aria-label="Three ids passing a schema-pattern filter, but only two of them also appearing in the observed set; INV-9999 passes the pattern but is outside the observed set" viewBox="0 0 320 130">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">schema (matches pattern) vs grounded (in observed set)</text>
  <rect x="20" y="26" width="280" height="34" fill="none" stroke="var(--s2)"/>
  <text x="26" y="38" font-size="7.5" fill="var(--s2)">schema-valid: INV-1001, INV-9999, INV-1002</text>
  <rect x="20" y="70" width="180" height="34" fill="none" stroke="var(--s1)"/>
  <text x="26" y="82" font-size="7.5" fill="var(--s1)">grounded (observed): INV-1001, INV-1002</text>
  <text x="210" y="90" font-size="7.5" fill="var(--ink)">INV-9999 is here:</text>
  <text x="210" y="101" font-size="7.5" fill="var(--ink)">schema-valid, NOT grounded</text>
  <text x="20" y="122" font-size="7.5" fill="var(--muted)">the fabricated id sits inside the schema box but outside the grounded box</text>
</svg>
^ All three ids fall inside the schema box because all three match the pattern. Only two fall inside the grounded box, the ids the agent actually observed. INV-9999 is the fabrication: it clears the schema and fails grounding, which is precisely the region a shape-only check cannot see.

**The schema check and the grounding check inspect different things — the id's form versus its provenance — so a fabricated reference is caught only by grounding, never by the schema.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the argument-validation step of an agent's tool dispatcher, reduced to three calls so every decision is checkable by hand.

Run `--calls` to see each proposed call scored both ways.

```text filename=argground.py --calls
  tool            id         schema-valid   grounded
  fetch_invoice   INV-1001   True           True
  fetch_invoice   INV-9999   True           False   <- HALLUCINATED
  fetch_invoice   INV-1002   True           True
```

All three ids are schema-valid — they all match `^INV-[0-9]+$`. That column tells you nothing useful here, because the model is good at producing well-formed ids whether or not they are real. The grounded column separates them: INV-1001 and INV-1002 were observed, INV-9999 was not. INV-9999 is the hallucination — a value with the exact form of a real invoice id and no invoice behind it.

Now `--gate` runs each policy — schema-only and schema-plus-grounding — over the calls.

```python filename=modules/agent-harness/code/argground-inter-01/argground.py:69-70 COMPLETE
    schema_only = accepted(data["calls"], pattern, observed, require_grounding=False)
    grounded_gate = accepted(data["calls"], pattern, observed, require_grounding=True)
```

The two dispatch lists differ by one id.

```text filename=argground.py --gate
  schema-only validation dispatches  = ['INV-1001', 'INV-9999', 'INV-1002']
  grounding validation dispatches    = ['INV-1001', 'INV-1002']
  dispatched by schema but not grounded = ['INV-9999']
```

Schema-only validation dispatches all three, including the fabricated INV-9999 — it sends a `fetch_invoice` for an invoice that does not exist. Depending on the backend, that returns an error the agent must now handle, or returns empty and the agent proceeds as if there were no invoice, or, in the worst case, matches some unrelated record and the agent refunds the wrong one. Grounding validation dispatches only the two observed ids and holds back INV-9999. The last line names exactly what schema-only let through and grounding stopped: the one id the model invented.

<svg role="img" aria-label="Two gates: schema-only dispatches all three ids including the fabricated one, grounding dispatches only the two observed ids and blocks INV-9999" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">calls dispatched (INV-9999 is fabricated)</text>
  <text x="10" y="40" font-size="8" fill="var(--s2)">schema-only</text>
  <rect x="80" y="30" width="50" height="14" fill="var(--s1)"/><text x="86" y="41" font-size="7" fill="var(--panel)">1001</text>
  <rect x="132" y="30" width="50" height="14" fill="var(--s2)"/><text x="138" y="41" font-size="7" fill="var(--panel)">9999</text>
  <rect x="184" y="30" width="50" height="14" fill="var(--s1)"/><text x="190" y="41" font-size="7" fill="var(--panel)">1002</text>
  <text x="240" y="41" font-size="7.5" fill="var(--ink)">fabrication sent</text>
  <text x="10" y="72" font-size="8" fill="var(--s1)">grounding</text>
  <rect x="80" y="62" width="50" height="14" fill="var(--s1)"/><text x="86" y="73" font-size="7" fill="var(--panel)">1001</text>
  <rect x="132" y="62" width="50" height="14" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/><text x="138" y="73" font-size="7" fill="var(--muted)">9999</text>
  <rect x="184" y="62" width="50" height="14" fill="var(--s1)"/><text x="190" y="73" font-size="7" fill="var(--panel)">1002</text>
  <text x="240" y="73" font-size="7.5" fill="var(--ink)">fabrication held</text>
  <text x="10" y="104" font-size="7.5" fill="var(--muted)">same three calls — grounding blocks exactly the invented id</text>
</svg>
^ Schema-only dispatches all three calls, sending the fabricated INV-9999 to the tool. Grounding dispatches only the observed ids and holds INV-9999 back. The two policies differ on exactly one call — the one the model made up.

**Schema-only validation dispatches all three calls including the invented INV-9999; grounding dispatches only the two observed ids — the policies differ precisely on the fabricated reference.**

## Build

The self-test establishes the trap: every id is schema-valid, yet one was never observed — a hallucination — and schema-only validation dispatches it.

```python filename=modules/agent-harness/code/argground-inter-01/argground.py:89-96 COMPLETE
    all_schema_valid = all(schema_valid(c, pattern) for c in calls)
    print("  every proposed id is schema-valid = %s" % all_schema_valid)

    hallucinated_exists = len(hallucinated) > 0
    print("  a schema-valid id was never observed (a hallucination) = %s (%s)" % (hallucinated_exists, hallucinated))

    schema_accepts_hallucinated = any(h in schema_only for h in hallucinated)
    print("  schema-only validation dispatches the hallucinated id = %s" % schema_accepts_hallucinated)
```

Then the fix: grounding rejects the hallucination and keeps every real id.

```python filename=modules/agent-harness/code/argground-inter-01/argground.py:98-102 COMPLETE
    grounding_rejects_hallucinated = all(h not in grounded_gate for h in hallucinated)
    print("  grounding validation rejects the hallucinated id = %s" % grounding_rejects_hallucinated)

    grounding_keeps_real = set(grounded_gate) == set(data["observed_ids"]) & {c["id"] for c in calls}
    print("  grounding validation keeps every real (observed) id = %s (%s)" % (grounding_keeps_real, grounded_gate))
```

Running the check confirms every clause.

```text filename=argground.py --check
  every proposed id is schema-valid = True
  a schema-valid id was never observed (a hallucination) = True (['INV-9999'])
  schema-only validation dispatches the hallucinated id = True
  grounding validation rejects the hallucinated id = True
  grounding validation keeps every real (observed) id = True (['INV-1001', 'INV-1002'])
```

**The check shows a schema-valid id passing shape validation but failing grounding, and grounding rejecting exactly it while keeping the observed ids — the fabrication caught by provenance, not form.**

## Definition of done

Done means schema validation accepts the fabricated id and grounding rejects it while preserving every observed id. The clause that grounding keeps all the real ids matters as much as the one that it drops the fake: a grounding check that is too aggressive — rejecting legitimate references — would make the agent unable to act, so the requirement is precise, block only references that trace to nothing.

Two clarifications keep this usable. First, grounding applies to reference arguments, not to all arguments. A tool argument that is genuinely generative — a summary the agent writes, a search query it composes, a new record's contents — is supposed to be produced by the model and has no prior source to trace to; grounding those would be wrong. The check is for arguments that name an existing entity (ids, keys, paths, handles), where a value that was never observed is by definition unfounded. The harness needs to know which arguments are references, which is a per-tool annotation, not a global rule. Second, rejecting an ungrounded reference is not the end of the interaction but the start of the right one: instead of dispatching a fabrication, the harness returns the rejection to the model as an observation ("that id was not found in context; look it up or ask"), so the agent is steered to fetch the id from a list, search for it, or ask the user — the behavior it should have had instead of inventing. Grounding both prevents the wrong action and redirects toward acquiring the real reference, and it composes with schema validation rather than replacing it: shape first, then provenance.

<svg role="img" aria-label="An argument routing decision: reference arguments get grounded against observed context, generative arguments do not; an ungrounded reference is returned to the model to look up or ask" viewBox="0 0 320 120">
  <rect x="14" y="22" width="130" height="34" fill="none" stroke="var(--s1)"/>
  <text x="22" y="36" font-size="7.5" fill="var(--s1)">reference arg (id, key, path)</text>
  <text x="22" y="49" font-size="7" fill="var(--ink)">→ require grounding</text>
  <rect x="160" y="22" width="146" height="34" fill="none" stroke="var(--s2)"/>
  <text x="168" y="36" font-size="7.5" fill="var(--s2)">generative arg (query, text)</text>
  <text x="168" y="49" font-size="7" fill="var(--ink)">→ no grounding, model produces it</text>
  <text x="14" y="80" font-size="7.5" fill="var(--muted)">ungrounded reference → return to model: "not in context, look it up or ask"</text>
  <text x="14" y="100" font-size="7.5" fill="var(--ink)">grounding composes with schema validation: shape first, then provenance</text>
</svg>
^ Only reference arguments are grounded; generative arguments the model is meant to author are not. An ungrounded reference is returned to the model as an observation so it fetches or asks for the real value, rather than being dispatched as a fabrication.

**Done means grounding rejects the fabricated reference and keeps every observed one, applied to reference arguments only and returned to the model as a look-it-up-or-ask observation — a provenance check layered on top of schema validation, not a replacement for it.**

## Boss fight

A customer-support agent can look up and modify orders by id. It works well when the user gives an order number, but support notices rare cases where it modified the wrong order, and even rarer ones where it claimed to act on an order that does not exist. The tool layer validates that every order_id argument matches the order-id format before executing. Why does a format check not prevent these, and what would?

The format check validates shape, not provenance, so it cannot catch a fabricated but well-formed order id — which is exactly what the model produces when it needs an order id it does not actually have. When the user refers to "my order" without giving the number and the agent has not looked it up, the model generates a plausible order id in the correct format; the format check passes it, and the tool executes against it. If that id corresponds to no order, the agent claims to have acted on a nonexistent order; if it happens to match a real but unrelated order, the agent modifies the wrong one — the two symptoms support is seeing. The fix is to ground the order_id argument: require that any order id passed to a lookup or modify tool trace to a value the agent actually observed — the user's message, a prior order-search result, the retrieved account context — and reject an order id that appears nowhere in that context instead of executing it. On rejection, return an observation telling the agent the id was not found in context so it searches the user's orders or asks the user for the number, rather than inventing one. Mark order_id (and any other reference argument, like account_id) as a grounded argument per tool, while leaving genuinely generative arguments (a note to add, a reason string) ungrounded since the model is supposed to author those. This composes with the existing format check — keep validating shape, and add the provenance check on top — and it closes both failure modes at once, because a fabricated id fails grounding whether it happens to hit a real order or no order at all.

## External resources

Writing on grounding and hallucinated arguments in tool-using agents (the distinction between argument validation and argument grounding, and patterns like constraining tool arguments to enumerated values retrieved from prior results) — why schema validation is necessary but insufficient for reference arguments, and how to source references from observed context.

Guidance on reducing entity hallucination in LLM agents (retrieval-grounded tool arguments, requiring ids to come from a prior list/search rather than free generation, and returning "not found" as a corrective observation) — the production techniques for keeping an agent from acting on identifiers it invented.
