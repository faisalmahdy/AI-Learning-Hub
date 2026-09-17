---
id: trunccall-inter-01
title: Gate tool execution on finish_reason, not on whether the arguments parse — a truncated call can still be valid JSON
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: A model emits a tool call as structured text and the harness parses it and runs the tool, and alongside the text the provider returns a finish_reason — why generation stopped. When the model finished the call, finish_reason is a completion reason (tool_calls or stop) and the arguments are whole; when generation stopped because it hit the max-token limit, finish_reason is length and the arguments are only whatever had been written so far. Truncation usually mangles the JSON — an unterminated string — and a naive parse fails, which tempts the wrong lesson: reach for a more lenient parser. That is dangerous, because truncation can also stop where the partial JSON is accidentally well-formed: the model meant {"tool": "delete_dir", "path": "/data/tmp/cache"} but got cut off after the first path segment, leaving {"tool": "delete_dir", "path": "/data"} — valid JSON, parses cleanly, and asks to delete /data instead of /data/tmp/cache. A harness that decides by whether json.loads succeeds runs it. The authoritative signal is finish_reason, not JSON validity: a response with finish_reason length is an unfinished turn whose tool call must not be executed, and the harness continues the generation with more budget or errors — it never guesses the missing arguments. On the fixture r1 is a complete call, r2 is truncated into invalid JSON, and r3 is truncated but accidentally valid; the naive harness runs r1, fails on r2, and runs r3 with the wrong path (/data), while the finish_reason-gated harness runs only r1 and refuses both truncated responses. The rule: JSON validity tells you the bytes are well-formed, finish_reason tells you the model was done, and only the second licenses running the call.
eli5: Imagine someone dictating an address for a delivery, and the phone cuts out partway through. Sometimes you get "123 Maple Str—" and you can tell it's unfinished. But sometimes it cuts out right after "123 Maple" and that sounds like a complete address, so you send the package there — to the wrong place, because they were going to say "123 Maple Street, Apartment 5, the blue building." The safe move isn't to guess whether the address "sounds complete"; it's to check whether the call actually ended or just dropped. If the line dropped, you don't deliver anywhere — you call back and get the whole address. Whether the words sound finished is not the same as whether the person was finished talking.
---

## Why this module

A tool-calling harness has one especially consequential decision per turn: was the model's tool call complete enough to execute? Get it wrong in the permissive direction and you run an action the model did not finish specifying — and actions have side effects.

The tempting way to make that decision is to look at the arguments: if they parse, they are good; if they do not, reject them. It feels safe because a broken tool call usually does produce broken JSON. But "usually" is the trap. The provider hands you a separate, authoritative signal for exactly this question — why generation stopped — and a harness that ignores it in favor of inspecting the bytes will occasionally run a truncated call that happened to parse.

**Whether the arguments parse and whether the model finished emitting them are different questions, and only the second decides if a call is safe to run.**

## Concepts

Every model response carries a finish_reason describing why generation halted. For a tool call, a completion reason — tool_calls, or stop — means the model emitted the whole call and stopped on its own. The reason length means something entirely different: generation ran into the max-token limit and was cut off mid-emission, so the arguments are only the prefix that fit.

A truncated tool call, then, is not a malformed one — it is an incomplete one. The bytes that exist may be perfectly well-formed; they are just missing the end. That distinction is the whole module, because the two natural ways truncation lands are not equally detectable.

Most of the time truncation stops inside a value — an unterminated string, a dangling comma — and the JSON is invalid, so any parser rejects it. This is the easy case: the naive "run it if it parses" harness fails safe here, refusing to run because the parse failed.

Occasionally truncation stops at a boundary where the prefix is accidentally complete JSON: after a field and where the structure happens to close. Now json.loads succeeds and returns an object — but it is missing every field the model had not yet written, and the fields it does have may be truncated to a shorter, different value. The naive harness sees a successful parse and runs the call, with arguments the model never actually produced. If the tool is destructive, the shorter path or missing scope turns a specific operation into a broad one.

The fix is to decide on finish_reason before ever looking at the bytes. A response with finish_reason length is an unfinished turn; its tool call is incomplete regardless of whether the fragment parses, and the harness must not execute it. It should continue generating from where it stopped (with more budget), or surface an error — but never fill in the missing arguments by guessing.

**A length finish_reason means the call is incomplete even when its JSON is valid, so the harness gates on the reason, not the parse.**

<svg role="img" aria-label="Two ways a tool call can be truncated. Usually it stops inside a value, leaving invalid JSON that any parser rejects. Occasionally it stops at a boundary, leaving accidentally valid JSON with missing fields that a parser accepts." viewBox="0 0 460 160">
<rect x="0" y="0" width="460" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">where truncation lands, and whether the parser catches it</text>
<text x="20" y="52" fill="var(--muted)" font-size="10">usually: stops inside a value</text>
<text x="40" y="70" fill="var(--s2)" font-size="10">{"path": "/data/tmp/ca   &#8594; invalid JSON &#8594; parser rejects &#10003;</text>
<text x="20" y="106" fill="var(--muted)" font-size="10">occasionally: stops at a boundary</text>
<text x="40" y="124" fill="var(--s1)" font-size="10">{"path": "/data"}   &#8594; valid JSON &#8594; parser accepts &#10007;</text>
<text x="20" y="146" fill="var(--ink)" font-size="9">only finish_reason=length catches both</text>
</svg>
^ The parser catches the common truncation but waves through the one that lands on valid JSON; finish_reason flags both because it reports that generation was cut off, not what the bytes look like.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/agent-harness/code/trunccall-inter-01/trunccall.py

The fixture is three responses: one complete, one truncated into invalid JSON, one truncated but accidentally valid.

```json filename=modules/agent-harness/code/trunccall-inter-01/trunccall.json:3-7 COMPLETE
  "complete_reasons": ["tool_calls", "stop"],
  "responses": [
    {"id": "r1", "finish_reason": "tool_calls", "text": "{\"tool\": \"read_file\", \"path\": \"/data/report.txt\"}", "intended_path": "/data/report.txt"},
    {"id": "r2", "finish_reason": "length", "text": "{\"tool\": \"delete_dir\", \"path\": \"/data/tmp/ca", "intended_path": "/data/tmp/cache"},
    {"id": "r3", "finish_reason": "length", "text": "{\"tool\": \"delete_dir\", \"path\": \"/data\"}", "intended_path": "/data/tmp/cache"}
```

Validity is a property of the bytes; completeness is finish_reason.

```python filename=modules/agent-harness/code/trunccall-inter-01/trunccall.py:30-36 COMPLETE
def parses(text):
    """Whether the emitted text is well-formed JSON -- a property of the bytes, not of completeness."""
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False
```

```python filename=modules/agent-harness/code/trunccall-inter-01/trunccall.py:39-41 COMPLETE
def is_complete(resp, complete_reasons):
    """Whether generation finished the call, by finish_reason -- the authoritative signal."""
    return resp["finish_reason"] in complete_reasons
```

The naive harness runs anything that parses.

```text filename=trunccall.py --naive
NAIVE — parse the text and run the call if it parses (ignores finish_reason)
------------------------------------------------------------------------
  r1 [tool_calls]  RAN path=/data/report.txt
  r2 [length]  did not run (parse failed)
  r3 [length]  RAN path=/data   <- WRONG path (intended /data/tmp/cache)
------------------------------------------------------------------------
  r3 parsed cleanly and ran with a truncated path -- a delete on /data, not /data/tmp/cache
```

r1 runs correctly. r2 is truncated into invalid JSON and the parse fails, so it does not run — the naive harness got lucky here. r3 is the danger: it was cut off after "/data", the remaining bytes happen to form valid JSON, so it parses and runs a delete on /data instead of the intended /data/tmp/cache. The parse succeeded; the call was still incomplete.

<svg role="img" aria-label="Two signals for r3. JSON validity says valid, which the naive harness reads as safe to run. finish_reason says length, which means truncated. The two disagree, and only finish_reason is correct." viewBox="0 0 460 150">
<rect x="0" y="0" width="460" height="150" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">r3: the two signals disagree</text>
<text x="30" y="54" fill="var(--muted)" font-size="10">JSON valid?</text>
<text x="150" y="54" fill="var(--s1)" font-size="11">yes &#8594; naive runs it</text>
<text x="150" y="72" fill="var(--muted)" font-size="9">but the bytes are only a prefix</text>
<text x="30" y="104" fill="var(--muted)" font-size="10">finish_reason?</text>
<text x="150" y="104" fill="var(--s2)" font-size="11">length &#8594; truncated, do not run</text>
<text x="150" y="122" fill="var(--muted)" font-size="9">the authoritative signal</text>
</svg>
^ r3 is valid JSON and truncated at once; the naive harness trusts validity and runs the wrong call, while finish_reason names the truncation the bytes concealed.

## Build

The safe harness checks finish_reason before the parse.

```python filename=modules/agent-harness/code/trunccall-inter-01/trunccall.py:52-59 COMPLETE
def safe_execute(resp, complete_reasons):
    """Run the call only if finish_reason says the turn completed; refuse a truncated response."""
    if not is_complete(resp, complete_reasons):
        return {"ran": False, "reason": "finish_reason=%s (truncated, not executed)" % resp["finish_reason"]}
    if not parses(resp["text"]):
        return {"ran": False, "reason": "parse failed"}
    args = json.loads(resp["text"])
    return {"ran": True, "path": args.get("path")}
```

```text filename=trunccall.py --safe
SAFE — run only if finish_reason is a completion reason
------------------------------------------------------------------------
  r1 [tool_calls]  RAN path=/data/report.txt
  r2 [length]  refused (finish_reason=length (truncated, not executed))
  r3 [length]  refused (finish_reason=length (truncated, not executed))
------------------------------------------------------------------------
  only the completed r1 runs; both length-truncated responses are held back
```

Both truncated responses are refused for the same reason — finish_reason is length — regardless of whether their bytes parsed. r3, which fooled the naive harness, is caught not because its JSON is bad (it is fine) but because the model never finished the turn.

<svg role="img" aria-label="A table of the three responses through each harness. r1 both run. r2 both refuse. r3: naive runs it with the wrong path, safe refuses. The r3 row is where the two harnesses differ." viewBox="0 0 440 160">
<rect x="0" y="0" width="440" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">what each harness does (naive vs finish_reason-gated)</text>
<text x="150" y="48" fill="var(--muted)" font-size="10">naive</text>
<text x="300" y="48" fill="var(--muted)" font-size="10">safe</text>
<text x="20" y="76" fill="var(--ink)" font-size="11">r1 complete</text>
<text x="150" y="76" fill="var(--s2)" font-size="10">run &#10003;</text>
<text x="300" y="76" fill="var(--s2)" font-size="10">run &#10003;</text>
<text x="20" y="104" fill="var(--ink)" font-size="11">r2 trunc (invalid)</text>
<text x="150" y="104" fill="var(--s2)" font-size="10">refuse</text>
<text x="300" y="104" fill="var(--s2)" font-size="10">refuse</text>
<text x="20" y="132" fill="var(--ink)" font-size="11">r3 trunc (valid)</text>
<text x="150" y="132" fill="var(--s1)" font-size="10">run WRONG &#10007;</text>
<text x="300" y="132" fill="var(--s2)" font-size="10">refuse &#10003;</text>
</svg>
^ The harnesses agree on r1 and r2; the whole difference is r3, where the naive one runs a truncated call and the finish_reason gate holds it back.

The self-test isolates the trap: r3 parses yet is truncated, the naive harness runs it wrong, the safe harness refuses it.

```python filename=modules/agent-harness/code/trunccall-inter-01/trunccall.py:99-105 COMPLETE
    naive_runs_truncated = naive_execute(r3)["ran"] and naive_execute(r3)["path"] != r3["intended_path"]
    print("  naive harness runs the accidentally-valid truncated r3 with the WRONG path = %s (ran path=%s, intended %s)"
          % (naive_runs_truncated, naive_execute(r3)["path"], r3["intended_path"]))

    r3_parses_but_truncated = parses(r3["text"]) and not is_complete(r3, cr)
    print("  r3 is valid JSON yet truncated, so validity alone would pass it = %s (parses=%s, finish_reason=%s)"
          % (r3_parses_but_truncated, parses(r3["text"]), r3["finish_reason"]))
```

```text filename=trunccall.py --check
SELF-TEST — the naive harness executes a truncated call because it parsed, while the safe harness refuses every finish_reason=length response, and JSON validity alone does not detect the truncation
----------------------------------------------------------------------------------------------------------------
  naive harness runs the accidentally-valid truncated r3 with the WRONG path = True (ran path=/data, intended /data/tmp/cache)
  r3 is valid JSON yet truncated, so validity alone would pass it = True (parses=True, finish_reason=length)
  safe harness refuses both truncated responses (r2 and r3) = True
  safe harness runs the completed r1 with the right path = True (path=/data/report.txt)
  r2 truncation left invalid JSON (the easy case, caught by any parser) = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  naive_runs_truncated=True  r3_parses_but_truncated=True  safe_blocks_truncated=True  safe_runs_complete=True  r2_invalid=True
```

**r3_parses_but_truncated is the point: parsing cannot detect truncation, because a truncation can be valid JSON, so the check must be finish_reason and it must come first.**

## Definition of done

You can state the difference between a malformed tool call and a truncated one, and why finish_reason (not JSON validity) is what distinguishes an unfinished turn.

You can explain why "reach for a more lenient parser" is the wrong response to truncation, and why leniently completing a truncated call is more dangerous than rejecting it.

You can describe the accidentally-valid case — truncation that lands on well-formed JSON with missing or shortened fields — and why a destructive tool makes it worse than an inconvenience.

You can say what the harness should do on finish_reason length: continue generation with more budget or error, and never guess the missing arguments.

## Boss fight

Your agent occasionally executes a tool call with arguments that look subtly wrong — a truncated file path, a search query missing its last clause — and it correlates with long argument lists. Your harness parses the model's output as JSON and runs the call if it parses.

First: explain the correlation with long arguments. Why do calls with more or longer arguments hit this bug more often, and what is the single field in the response that would have told you every one of these was truncated?

Then: a teammate proposes raising max_tokens so truncation never happens. Explain why that reduces the frequency but cannot be the fix — what is still true at any finite limit, and why a correctness property must not depend on an output never being long enough to truncate.

Finally: once you gate on finish_reason, a length-truncated tool call needs a recovery, not just a refusal. Describe how you would continue the call — what you send back to the model so it can finish the same call rather than restart the whole turn — and why simply re-running the turn from scratch risks a different, also-truncated call instead of completing this one.

## External resources

The Anthropic and OpenAI API references both document the response's stop/finish reason and list "max_tokens" / "length" as a distinct value from a normal or tool-call completion — reading that enum is the fastest way to see that the provider already hands you the completeness signal.

Guidance on handling truncated model output (for example provider cookbooks on continuing a cut-off response) describes the continuation pattern the boss fight asks for: feed the partial output back and ask the model to resume, rather than re-prompting from the start.
