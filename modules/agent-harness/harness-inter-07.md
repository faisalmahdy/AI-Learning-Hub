---
id: harness-inter-07
title: Validate a tool call against its schema before executing — or a malformed call fails opaquely
topic: agent-harness
level: intermediate
status: ready
time: 5-8h
summary: A model proposes tool calls as free-form structured text — a tool name and a bag of arguments — and nothing guarantees they are well-formed: the name might not be a real tool, a required argument might be missing, an argument might be the wrong type, or there might be an extra argument the tool does not expect. The tempting harness executes whatever it is handed and lets the tool sort it out, which fails in the worst way, because the error surfaces deep inside the tool as a crash or, worse, the tool half-runs on garbage, with a message that says nothing the model can act on. A validating harness checks each call against the tool's schema first — known tool, all required arguments present, every argument the right type, no unexpected arguments — and rejects a bad call before it runs, with a specific reason the model can read and fix. Of six proposed calls, one is well-formed and five are malformed in five different ways; the naive harness executes all six and sends five broken calls to the tools, while the validating harness executes only the one good call and returns five precise rejections like "missing required argument 'limit'" and "argument 'body' should be str, got int", turning an opaque downstream failure into an actionable boundary error the model can correct on its next turn.
eli5: When you fill out a form and forget your zip code or write letters where numbers go, a good website stops you right there and says exactly what to fix. A bad website submits the broken form and something breaks three steps later with a confusing error nobody can decode. A tool-using AI proposes little "forms" (tool calls) that are sometimes broken, and the smart move is to check each one against the rules before running it — so the AI gets told precisely what was wrong and can fix it, instead of the tool blowing up on bad input.
---

## Why this module

An agent loop's most dangerous moment is the handoff from the model to a tool. The model emits a tool call — a name and some arguments — as generated text, and generated text is not guaranteed to be correct. The model can hallucinate a tool that does not exist, omit a required argument, pass a string where a number belongs, or tack on an argument the tool never declared. These are not rare edge cases; they are the routine failure modes of a system whose tool calls come out of a language model rather than a typechecker.

<svg viewBox="0 0 700 150" role="img" aria-label="The same malformed call taking two paths. Naive path: execute, then fail deep inside the tool with a stack trace that describes the tool's internals. Validated path: reject at the boundary with a clear reason the model can fix.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">a malformed call: fail deep in the tool, or reject at the boundary</text>
    <rect x="30" y="55" width="90" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="75" y="74" text-anchor="middle" fill="var(--ink)" font-size="8">bad call</text>
    <line x1="120" y1="60" x2="200" y2="45" stroke="var(--s2)"></line><line x1="120" y1="80" x2="200" y2="110" stroke="var(--s1)"></line>
    <rect x="200" y="30" width="180" height="30" fill="var(--panel)" stroke="var(--s2)"></rect><text x="290" y="49" text-anchor="middle" fill="var(--s2)" font-size="8">naive: run it →</text>
    <rect x="400" y="30" width="270" height="30" fill="var(--panel)" stroke="var(--s2)"></rect><text x="535" y="49" text-anchor="middle" fill="var(--s2)" font-size="7">KeyError deep in tool (opaque)</text>
    <rect x="200" y="95" width="180" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="290" y="114" text-anchor="middle" fill="var(--acc-ink)" font-size="8">validate: reject →</text>
    <rect x="400" y="95" width="270" height="30" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="535" y="114" text-anchor="middle" fill="var(--acc-ink)" font-size="7">"missing argument 'limit'" (fixable)</text>
  </g>
</svg>
^ The naive path runs the bad call and fails deep in the tool with a message about the tool's internals; the validated path rejects at the boundary with a reason phrased in terms of the model's mistake. Same call, opposite feedback quality.

The naive harness treats the model's call as authoritative and just runs it. When the call is malformed, one of two bad things happens. Either the tool throws deep in its own code — a KeyError, a type error, a database exception — and the harness surfaces a stack trace that describes the tool's internals, not the model's mistake; or, worse, the tool does not throw and instead runs on the bad input, sending an email with a numeric body, searching with a limit of "ten", doing something wrong silently. In both cases the feedback the model gets back is useless for fixing the call: an internal crash message, or no error at all.

The fix is to validate the call against the tool's schema at the boundary, before executing. The schema says what tools exist and, for each, which arguments are required and what type each must be. Validation checks the call against it — is this a real tool, are all required arguments present, is each the right type, are there any arguments the tool did not declare — and if anything fails, the harness rejects the call without running it and returns a precise, model-readable reason. This module runs six proposed calls, one valid and five malformed in five distinct ways, through a naive harness and a validating one, and shows the malformed calls stopped at the boundary with actionable errors. Everything runs offline against a calls fixture, stdlib Python 3, `$0.00`. The instinct to unlearn is that the tool will catch its own bad input. The tool catches it late, deep, and unhelpfully; the schema catches it early, at the boundary, with a reason the model can act on.

## Concepts

Named here so you can find them again; each is built below.

- **Tool schema** — the declared tools and, per tool, the required arguments and their types.
- **Tool call** — the model's proposed invocation: a tool name and an argument bag.
- **Validation** — checking a call against the schema before executing it.
- **The four failure kinds** — unknown tool, missing argument, wrong type, unexpected argument.
- **Boundary error** — a rejection returned before execution, with a reason the model can fix.
- **Opaque failure** — a malformed call executed anyway, failing deep in the tool or running wrong.

## Worked example

Source: the tool-dispatch step of an agent harness — the point where a model's proposed call is turned into an actual tool invocation. The schemas and calls stand in for a real tool registry and a model's (imperfect) structured output.

Script and fixture: `modules/agent-harness/code/harness-inter-07/` — `validate.py`, and `calls.json`, two tools and six calls. Every command runs from there.

### The validation function

One function does all four checks and returns a specific reason for the first failure it finds.

```
# validate.py:43-58 — COMPLETE (four checks: known tool, required present, right type, no extras)
def validate(call, schemas):
    """Return None if the call is well-formed, else a specific reason it is rejected."""
    name, args = call["tool"], call["args"]
    if name not in schemas:
        return "unknown tool %r" % name
    spec = schemas[name]
    for param, typ in spec.items():
        if param not in args:
            return "missing required argument %r" % param
        if not isinstance(args[param], TYPES[typ]) or (typ != "bool" and isinstance(args[param], bool)):
            return "argument %r should be %s, got %s" % (param, typ, type(args[param]).__name__)
    for param in args:
        if param not in spec:
            return "unexpected argument %r" % param
    return None
```

The four checks are the four ways a call goes wrong: the tool name is not in the registry, a declared argument is absent, a present argument is the wrong type, or an argument appears that the schema never declared. The type check has one subtlety worth the extra clause — in Python `bool` is a subclass of `int`, so `True` would pass an `int` check without the guard; a real validator has to be that careful, because a silently-accepted `True` where a count belongs is exactly the kind of bug validation exists to stop. Run every call through it:

```
# $ python3 validate.py --schemas
#   tool search       (query:str, limit:int)
#   tool send_email   (to:str, body:str)
#   id    tool          result   reason
#   c1    search        OK
#   c2    search        REJECT   missing required argument 'limit'
#   c3    transfer_all  REJECT   unknown tool 'transfer_all'
#   c4    send_email    REJECT   argument 'body' should be str, got int
#   c5    search        REJECT   argument 'limit' should be int, got str
#   c6    send_email    REJECT   unexpected argument 'cc'
```

run: 2026-08-27 · deterministic; schemas and proposed calls are a fixture · 6 calls · `python3 validate.py --schemas`

One call, c1, is well-formed and passes. The other five each fail a different check, and — this is the point — each rejection names exactly what is wrong and where: not "invalid call" but "missing required argument 'limit'", "argument 'body' should be str, got int". Those are messages a model can read on its next turn and fix, the same way a compiler error tells you which line and which type. c3 is worth noting on its own: the model hallucinated a `transfer_all` tool that does not exist, and validation refuses it at the boundary — a made-up dangerous tool never even reaches a dispatcher.

<svg viewBox="0 0 700 210" role="img" aria-label="Six tool calls passing through a validation gate. c1 passes as OK. c2 (missing limit), c3 (unknown tool), c4 (wrong type body), c5 (wrong type limit), c6 (unexpected cc) are each rejected with their specific reason. Only c1 continues to the tools.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">six proposed calls → validation gate → only the well-formed one runs</text>
    <rect x="290" y="30" width="120" height="150" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="350" y="110" text-anchor="middle" fill="var(--acc-ink)" font-size="9">VALIDATE</text><text x="350" y="124" text-anchor="middle" fill="var(--acc-ink)" font-size="7">vs schema</text>
    <text x="40" y="44" fill="var(--s1)" font-size="8">c1 search ok</text><line x1="150" y1="40" x2="290" y2="45" stroke="var(--s1)"></line>
    <text x="40" y="70" fill="var(--s2)" font-size="8">c2 no limit</text>
    <text x="40" y="94" fill="var(--s2)" font-size="8">c3 no such tool</text>
    <text x="40" y="118" fill="var(--s2)" font-size="8">c4 body int</text>
    <text x="40" y="142" fill="var(--s2)" font-size="8">c5 limit str</text>
    <text x="40" y="166" fill="var(--s2)" font-size="8">c6 extra cc</text>
    <line x1="150" y1="66" x2="290" y2="70" stroke="var(--s2)"></line><line x1="150" y1="90" x2="290" y2="90" stroke="var(--s2)"></line><line x1="150" y1="114" x2="290" y2="110" stroke="var(--s2)"></line><line x1="150" y1="138" x2="290" y2="130" stroke="var(--s2)"></line><line x1="150" y1="162" x2="290" y2="150" stroke="var(--s2)"></line>
    <line x1="410" y1="55" x2="520" y2="55" stroke="var(--s1)"></line><rect x="520" y="42" width="110" height="26" fill="var(--s1)"></rect><text x="575" y="59" text-anchor="middle" fill="var(--panel)" font-size="8">tools (c1)</text>
    <line x1="410" y1="130" x2="520" y2="130" stroke="var(--s2)" stroke-dasharray="3 2"></line><rect x="520" y="105" width="150" height="50" fill="var(--panel)" stroke="var(--s2)"></rect><text x="595" y="125" text-anchor="middle" fill="var(--s2)" font-size="7">5 rejections</text><text x="595" y="140" text-anchor="middle" fill="var(--muted)" font-size="7">each with a reason</text>
  </g>
</svg>
^ Five of six calls never pass the gate; each is turned back with a specific reason, and only the well-formed c1 reaches the tools. The made-up transfer_all tool (c3) is stopped at the boundary before any dispatcher sees it.

### The two harnesses

The naive harness executes every proposed call; the validating one executes only those that pass.

```
# validate.py:66-73 — COMPLETE (execute everything vs execute only the valid)
def naive_executes(calls, schemas):
    """The bug: execute every proposed call; the malformed ones fail at the tool."""
    return [c["id"] for c in calls]


def validated_executes(calls, schemas):
    """The fix: execute only the calls that pass validation."""
    return [c["id"] for c in calls if is_valid(c, schemas)]
```

A call is valid exactly when validation returns no reason:

```
# validate.py:60-61 — COMPLETE (valid means validation found no fault)
def is_valid(call, schemas):
    return validate(call, schemas) is None
```

<svg viewBox="0 0 700 160" role="img" aria-label="A checklist of the four validation checks applied in order: known tool, all required arguments present, every argument the right type, no unexpected arguments. A call must pass all four to run; failing any one returns that check's specific reason.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">four checks, in order — pass all to run, fail any to reject with that reason</text>
    <rect x="40" y="34" width="180" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="50" y="51" fill="var(--acc-ink)" font-size="8">1. tool exists?</text>
    <rect x="40" y="66" width="180" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="50" y="83" fill="var(--acc-ink)" font-size="8">2. required args present?</text>
    <rect x="40" y="98" width="180" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="50" y="115" fill="var(--acc-ink)" font-size="8">3. types correct?</text>
    <rect x="40" y="130" width="180" height="26" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="50" y="147" fill="var(--acc-ink)" font-size="8">4. no extra args?</text>
    <text x="240" y="51" fill="var(--s2)" font-size="8">✗ unknown tool 'transfer_all'</text>
    <text x="240" y="83" fill="var(--s2)" font-size="8">✗ missing required argument 'limit'</text>
    <text x="240" y="115" fill="var(--s2)" font-size="8">✗ 'body' should be str, got int</text>
    <text x="240" y="147" fill="var(--s2)" font-size="8">✗ unexpected argument 'cc'</text>
    <text x="560" y="83" fill="var(--s1)" font-size="8">all pass → run</text>
  </g>
</svg>
^ Each check maps to one failure kind and one specific reason; a call runs only if it clears all four, and the first failure returns that check's message. The five malformed calls each trip a different rung.

Run them head to head:

```
# $ python3 validate.py --run
#   naive executes:      ['c1', 'c2', 'c3', 'c4', 'c5', 'c6']   (of which malformed: ['c2', 'c3', 'c4', 'c5', 'c6'])
#   validating executes: ['c1']
```

run: 2026-08-27 · deterministic · `python3 validate.py --run`

The naive harness sends all six calls to the tools, five of them malformed — so five tool invocations either crash inside the tool or run on bad input, and each returns a failure that describes the tool's guts rather than the model's mistake. The validating harness sends exactly one call, the well-formed c1, and hands back five clean rejections instead. The malformed calls never reach the tools at all, so there is no opaque crash to debug and no wrong action taken on garbage input; the model simply gets told what to fix.

**A model's tool call is unvalidated generated text, so it can name a missing tool, omit a required argument, mistype an argument, or add an unexpected one — validate against the schema at the boundary and reject with a specific reason ('missing required argument limit', 'body should be str, got int') rather than executing and failing deep in the tool, because the tool's own error describes its internals while a boundary rejection describes the model's mistake in terms it can fix.**

### The self-test

The `--check` mode plants the bug — executing unvalidated calls — and proves it: the naive harness runs the malformed calls, the validating harness runs none of them, exactly the valid call runs, and the rejections give distinct specific reasons.

```
# $ python3 validate.py --check
#   the naive harness executes the malformed calls = True (['c2', 'c3', 'c4', 'c5', 'c6'])
#   the validating harness executes NONE of the malformed calls = True
#   the validating harness executes exactly the well-formed calls = True (['c1'])
#   the rejections give specific, distinct reasons = True (5 kinds)
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 validate.py --check`

The `specific_reasons` line is what separates real validation from a bare boolean check. A validator that returned only "invalid" would block the bad calls but leave the model no way to recover — it would retry blindly. Because each rejection names the exact fault, the model can correct that one thing (supply the limit, fix the type, use a real tool) and succeed next turn, which is what turns validation from a wall into a guardrail.

```
# validate.py:115-118 — COMPLETE (the validating harness blocks all malformed and runs exactly the valid)
    validated_blocks_all = len(set(validated_executes(calls, schemas)) & set(malformed)) == 0
    print("  the validating harness executes NONE of the malformed calls = %s" % validated_blocks_all)

    only_valid_runs = validated_executes(calls, schemas) == valid and len(valid) > 0
    print("  the validating harness executes exactly the well-formed calls = %s (%s)" % (only_valid_runs, valid))
```

### The running tally

| call | fault | naive | validating | rejection reason |
|---|---|---|---|---|
| c1 | none | run | run | — |
| c2 | missing argument | run (fails in tool) | rejected | missing required argument 'limit' |
| c3 | unknown tool | run (fails in tool) | rejected | unknown tool 'transfer_all' |
| c4 | wrong type | run (fails/wrong) | rejected | argument 'body' should be str, got int |
| c5 | wrong type | run (fails in tool) | rejected | argument 'limit' should be int, got str |
| c6 | unexpected argument | run (fails in tool) | rejected | unexpected argument 'cc' |

Read the naive and validating columns: the naive harness runs every row and turns five of them into tool-level failures, while the validating harness runs only the clean row and converts the other five into boundary rejections. The rejection-reason column is the payoff — every fault is named specifically enough to act on, so the model's next turn is a targeted fix, not a blind retry. Validation does not make the model's calls correct; it makes the model's mistakes legible and cheap, catching them one function call from the model instead of many layers deep in a tool.

### What we did not settle

This is schema validation at the dispatch boundary; a production harness layers more. The schema here is a flat required-arguments-and-types check; real tool schemas (JSON Schema, function-calling specs) add optional arguments with defaults, enums, ranges, nested objects, and constraints, and the validator grows to match — but the boundary discipline is identical. Many model APIs constrain generation to the schema (constrained decoding), which prevents most malformed calls at the source; validation is still the backstop, because constraints can be incomplete and the boundary is where you enforce them. A rejection should be returned to the model in a form it can use — as a tool result it can read and retry from — which closes the loop this module opens. And validation composes with permission checks (`harness-inter-02`): a call must be well-formed *and* allowed, and it is cleaner to reject malformed before checking permitted. The invariant: never execute a tool call you have not validated against its schema, and reject with a reason the model can fix.

## Build

The build in one paragraph: validate every proposed tool call against the tool's schema before executing it — confirm the tool exists, every required argument is present, each argument has the declared type (minding traps like bool-is-int), and no undeclared arguments appear — and on any failure reject the call without running it, returning a specific, model-readable reason rather than letting the tool fail on bad input. Return the rejection as a tool result the model can retry from, prefer constrained decoding to prevent malformed calls at the source with validation as the backstop, grow the schema check to match your tool-spec's features, and run validation before permission checks.

We opened on the six calls. The number that proves the fix is how many malformed calls reach the tools under each harness:

```
# modules/agent-harness/code/harness-inter-07/ — COMPLETE, run from that directory
$ python3 validate.py --run
  naive executes:      ['c1', 'c2', 'c3', 'c4', 'c5', 'c6']   (of which malformed: ['c2', 'c3', 'c4', 'c5', 'c6'])
  validating executes: ['c1']
```

Now build your own. Take a real tool registry and a batch of model-proposed calls (include some malformed ones — a missing argument, a wrong type, a hallucinated tool), and dispatch them through a naive harness and a validating one. Your number to beat is not throughput; it is **how many malformed calls reach the tools, and whether each rejection names a fixable reason** — validation should send zero malformed calls through and return a specific reason for each. Confirm the model could act on every rejection. Bring back both execution sets. Good luck.

## Definition of done

- [ ] A tool schema (tools with required arguments and types)
- [ ] A validator checking: known tool, required present, right type, no extras
- [ ] Specific rejection reasons naming the exact fault
- [ ] A naive harness that executes every call and a validating one that executes only valid calls
- [ ] Confirmation the validating harness sends zero malformed calls to the tools
- [ ] Confirmation exactly the well-formed calls run and rejections give distinct reasons
- [ ] `python3 validate.py --check` printing SELF-TEST PASS: naive_runs_malformed, validated_blocks_all, only_valid_runs, specific_reasons
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Name the four ways a tool call can be malformed, with an example of each.
2. Why is executing an unvalidated call and letting the tool fail worse than validating first?
3. Why does the type check need a special case for booleans in Python?
4. Why must a rejection give a specific reason rather than just "invalid"?
5. Your own batch of calls was dispatched both ways. How many malformed calls reached the tools under each, and could the model act on the rejections?

## External resources

- The function-calling / tool-use schema docs for any model API (JSON Schema for tool parameters) — my summary: how tools declare parameters, types, and requiredness, and how the model is asked to conform; read it for the richer schema features (enums, nesting, defaults) this module simplifies.
- Material on constrained decoding / structured generation — my summary: forcing a model's output to conform to a schema at generation time, preventing most malformed calls at the source; read it for the upstream complement to boundary validation.
- This hub, *harness-inter-02* (govern the agent by the menu) and *harness-basic-01* (an agent is a loop) — read them for the permission layer that runs after validation and the loop this dispatch sits inside.
