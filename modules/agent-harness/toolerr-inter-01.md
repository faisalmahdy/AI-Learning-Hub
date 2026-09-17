---
id: toolerr-inter-01
title: Return structured errors from tools, not raw tracebacks — the harness needs a field to branch on, the model needs a hint
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: When a tool call fails, the harness has to turn the failure into something it puts back in the conversation, and the path of least resistance — catch the exception, hand back its traceback — is wrong for two audiences at once. The harness's own retry logic gets a blob of text with no machine-readable signal, so it cannot decide whether the failure is worth retrying: it either retries everything (wasting calls on permanent errors) or retries nothing (giving up on transient ones). And the model gets a wall of internal stack frames — implementation paths, library versions — that is mostly noise, costs tokens, and buries the one thing it needs: what to do next. A structured error fixes both. It carries the fields a decision turns on: a stable machine-readable code, a short human message, a retryable flag, an optional retry_after, and a hint written for the model. The harness branches on retryable — retry the transient failures after the suggested delay, do not retry the permanent ones — and the model gets a compact instruction instead of a traceback. The two failure classes are the point: a rate limit is transient (the same call likely succeeds after a wait, so retryable), a bad argument is permanent (retrying the identical call fails forever; the fix is to change the argument), and a raw traceback does not distinguish them, so any blanket retry policy mishandles one. On a fixture with a transient rate-limit and a permanent bad-argument error given both ways, reading the tracebacks the harness has no retryable field and both blanket policies mishandle one of the two, while reading the structured errors it retries the transient, does not retry the permanent, and the structured payloads total 366 chars against the tracebacks' 481.
eli5: Imagine you send a helper to do errands and one fails. If they come back and dump the whole story — every street they walked, every door they knocked on, the weather — you have to dig through all of it to find out what actually went wrong and whether it is worth sending them again. Much better if they hand you a little card: "Store closed, reopens in 5 minutes — worth trying again," or "You gave me the wrong address — fix it and I'll go." Now you know instantly whether to wait and resend or to change something first. The little card is a structured error: it says what went wrong, whether trying again will help, and what to do — instead of a pile of details you have to sort through.
---

## Why this module

Tool failures are not the exception in an agent loop; they are routine. Networks time out, rate limits trip, arguments are malformed, permissions are missing. So how a harness represents a failure is not an edge case — it is a hot path that runs constantly, and getting it wrong quietly degrades every retry decision and wastes context on every failure. The tempting implementation is the one every language makes easy: catch the exception, stringify the traceback, put it back in the conversation. It runs on the first try, which is exactly why it survives into production.

The traceback is wrong for two different readers. The first is the harness itself, which has to decide what to do next — retry, or give up and surface the error. A traceback gives it no field to make that decision; it is prose, and branching on prose means brittle string matching. So the harness falls back to a blanket policy, and every blanket policy is wrong for some failures: retry-everything burns calls re-running permanently-broken requests, retry-nothing abandons requests that a two-second wait would have fixed. The second reader is the model, which gets a wall of internal stack frames — file paths, library versions, framework internals — that is mostly noise, costs tokens, and buries the actionable part.

A structured error serves both readers with a small object. This module takes a transient failure and a permanent one, renders each as a traceback and as a structured error, and shows the retry decision each representation supports.

**Have tools return a structured error — a machine-readable code, a retryable flag, an optional retry_after, and a short actionable hint — rather than passing the raw exception traceback back to the harness and the model, because the harness needs a field to make the retry decision and the model needs a next action, and a traceback carries neither.**

## Concepts

The fixture is two failures, each with both representations. The first is a transient rate limit (HTTP 429): the same call will likely succeed after a short wait, so it is retryable. The second is a permanent bad argument (a non-numeric user_id): retrying the identical call fails forever, so it is not retryable — the fix is to change the argument.

```json filename=modules/agent-harness/code/toolerr-inter-01/toolerr.json:5-11 COMPLETE
      "raw_traceback": "Traceback (most recent call last):\n  File \"/app/harness/tools/web.py\", line 88, in call\n    resp = session.get(url, timeout=10)\n  File \"/usr/lib/python3.11/site-packages/requests/api.py\", line 231, in get\n    raise HTTPError(429, 'Too Many Requests')\nrequests.exceptions.HTTPError: 429 Too Many Requests",
      "code": "rate_limited",
      "message": "search_web hit the provider rate limit",
      "retryable": true,
      "retry_after_s": 2,
      "hint": "wait retry_after_s and retry the same query"
```

The structured error is the subset of fields a decision turns on — code, message, retryable, retry_after, hint — extracted from the failure.

```python filename=modules/agent-harness/code/toolerr-inter-01/toolerr.py:52-62 COMPLETE
def structured(f):
    """The fields a tool should return on failure: code, message, retryable, retry_after, hint."""
    return {"code": f["code"], "message": f["message"], "retryable": f["retryable"], "retry_after_s": f["retry_after_s"], "hint": f["hint"]}


def structured_size(f):
    return len(json.dumps(structured(f)))


def raw_size(f):
    return len(f["raw_traceback"])
```

The two extractions are the crux. From a structured error the harness reads the retryable flag directly; from a traceback there is no such field, so the extraction returns None — "cannot decide" — and the decision function maps each to an action.

```python filename=modules/agent-harness/code/toolerr-inter-01/toolerr.py:65-82 COMPLETE
def retryable_from_structured(f):
    """The harness reads the retryable flag directly."""
    return f["retryable"]


def retryable_from_traceback(f):
    """There is no machine-readable retryable field in a traceback -- None means 'cannot decide'."""
    return None


def decision_from(retryable, f):
    """The harness's action given a retryable value (or None when it cannot tell)."""
    if retryable is None:
        return "unknown (no signal)"
    if retryable:
        return "retry after %ds" % f["retry_after_s"]
    return "do not retry; surface hint to model"
```

<svg role="img" aria-label="A tool failure branching two ways: a large traceback blob feeding a question-mark retry decision, versus a small structured error with a retryable field feeding a clear retry-or-not decision" viewBox="0 0 320 150">
  <rect x="120" y="10" width="80" height="20" fill="none" stroke="var(--ink)" stroke-width="1.5"/>
  <text x="132" y="24" font-size="9" fill="var(--ink)">tool fails</text>
  <line x1="140" y1="30" x2="70" y2="52" stroke="var(--s2)" stroke-width="1.2"/>
  <line x1="180" y1="30" x2="250" y2="52" stroke="var(--s1)" stroke-width="1.2"/>
  <rect x="14" y="54" width="110" height="44" fill="var(--muted)"/>
  <text x="20" y="70" font-size="8" fill="var(--panel)">traceback blob</text>
  <text x="20" y="82" font-size="7.5" fill="var(--panel)">stack frames, paths</text>
  <text x="20" y="93" font-size="7.5" fill="var(--panel)">no retryable field</text>
  <rect x="200" y="54" width="110" height="44" fill="var(--s1)"/>
  <text x="206" y="68" font-size="8" fill="var(--panel)">structured</text>
  <text x="206" y="80" font-size="7.5" fill="var(--panel)">code, retryable,</text>
  <text x="206" y="91" font-size="7.5" fill="var(--panel)">retry_after, hint</text>
  <text x="52" y="120" font-size="11" fill="var(--s2)">retry? → ???</text>
  <text x="212" y="120" font-size="10" fill="var(--s1)">retry? → read flag</text>
  <text x="14" y="140" font-size="8" fill="var(--muted)">blanket policy, mishandles a class</text>
  <text x="200" y="140" font-size="8" fill="var(--muted)">correct per-failure decision</text>
</svg>
^ Both start from the same failure. The traceback path reaches the retry decision with no field to read, forcing a blanket policy; the structured path carries a retryable flag the harness branches on directly.

**A traceback is written for a human debugging after the fact; a structured error is written for the two machines that must act now — the retry logic and the model.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the tool-failure-handling step of an agent harness, reduced to two failures so every field and size is checkable by hand.

Run `--errors` to see each failure both ways, with byte sizes.

```text filename=toolerr.py --errors
  tool search_web (rate_limited):
    raw traceback (303 chars):
      Traceback (most recent call last):
        File "/app/harness/tools/web.py", line 88, in call
          resp = session.get(url, timeout=10)
        File "/usr/lib/python3.11/site-packages/requests/api.py", line 231, in get
          raise HTTPError(429, 'Too Many Requests')
      requests.exceptions.HTTPError: 429 Too Many Requests
    structured (171 chars): {"code": "rate_limited", "message": "search_web hit the provider rate limit", "retryable": true, "retry_after_s": 2, "hint": "wait retry_after_s and retry the same query"}
```

The traceback is 303 characters of stack frames — the request library's internals, a file path inside the harness, a line number — and to learn that this is a rate limit you have to read to the last line and know that 429 means "too many requests." The structured error is 171 characters and says it directly: code `rate_limited`, `retryable: true`, `retry_after_s: 2`, and a hint. Everything the harness and model need is a field lookup, not a parse.

Now `--decide` shows the retry decision each representation supports.

```text filename=toolerr.py --decide
  search_web (rate_limited):
    from structured: retryable=True -> retry after 2s
    from traceback:  retryable=None -> unknown (no signal)
  get_user (invalid_argument):
    from structured: retryable=False -> do not retry; surface hint to model
    from traceback:  retryable=None -> unknown (no signal)
  blanket 'always retry' mishandles 1 of 2; blanket 'never retry' mishandles 1 of 2
```

From the structured errors the harness makes the right call on both: retry the rate limit after 2 seconds, do not retry the bad argument (surface the hint so the model fixes it). From the tracebacks it gets `None` both times — no signal — so it must fall back to a blanket policy, and the last line is the verdict: always-retry mishandles the permanent error (retrying `int('abc')` forever), never-retry mishandles the transient one (abandoning a call a 2-second wait would fix). There is no single blanket policy that gets both right, because the distinction it needs is the one the traceback discarded.

<svg role="img" aria-label="Two bars for the rate-limit failure: a long 303-character traceback bar and a short 171-character structured bar, with the structured bar annotated as carrying the retryable field" viewBox="0 0 320 110">
  <text x="10" y="24" font-size="9" fill="var(--s2)">traceback</text>
  <rect x="90" y="14" width="210" height="18" fill="var(--muted)"/>
  <text x="150" y="27" font-size="8" fill="var(--panel)">303 chars, no retryable field</text>
  <text x="10" y="64" font-size="9" fill="var(--s1)">structured</text>
  <rect x="90" y="54" width="118" height="18" fill="var(--s1)"/>
  <text x="98" y="67" font-size="8" fill="var(--panel)">171 chars + retryable</text>
  <text x="90" y="94" font-size="8.5" fill="var(--muted)">the structured error is smaller AND carries the decision field — real tracebacks are far deeper</text>
</svg>
^ For the rate-limit failure the structured error is both smaller (171 vs 303 chars) and richer — it holds the retryable flag the traceback lacks. Production tracebacks run dozens of frames, so the size gap in practice is far larger than this toy shows.

**The traceback forces a blanket policy that is provably wrong for one of the two failure classes; the structured error's retryable flag is exactly the distinction that lets the harness be right on both.**

## Build

The self-test asserts the whole claim: that the traceback has no retryable field, that the structured error does, that it drives the correct decision for each class, and that no blanket traceback-only policy handles both.

```python filename=modules/agent-harness/code/toolerr-inter-01/toolerr.py:112-129 COMPLETE
    traceback_has_no_flag = all(retryable_from_traceback(f) is None for f in failures)
    print("  the raw traceback carries no machine-readable retryable field = %s" % traceback_has_no_flag)

    structured_exposes_flag = all(isinstance(retryable_from_structured(f), bool) for f in failures)
    print("  the structured error exposes a retryable flag = %s" % structured_exposes_flag)

    structured_decides_transient = decision_from(retryable_from_structured(transient), transient).startswith("retry")
    print("  structured drives RETRY for the transient rate-limit = %s (%s)" % (structured_decides_transient, decision_from(retryable_from_structured(transient), transient)))

    structured_decides_permanent = decision_from(retryable_from_structured(permanent), permanent).startswith("do not retry")
    print("  structured drives NO-RETRY for the permanent bad-argument = %s (%s)" % (structured_decides_permanent, decision_from(retryable_from_structured(permanent), permanent)))

    blanket_always_mis = blanket_retry_correct(failures, True)
    blanket_never_mis = blanket_retry_correct(failures, False)
    blanket_always_mishandles = blanket_always_mis > 0 and blanket_never_mis > 0
    print("  every blanket traceback-only policy mishandles a failure class = %s (always-retry %d, never-retry %d)" % (blanket_always_mishandles, blanket_always_mis, blanket_never_mis))
```

<svg role="img" aria-label="A 2x2 table: rows transient and permanent, columns always-retry and never-retry, each blanket policy wrong in one cell, while the retryable flag is right in both" viewBox="0 0 320 130">
  <text x="95" y="20" font-size="8.5" fill="var(--muted)">always-retry</text>
  <text x="185" y="20" font-size="8.5" fill="var(--muted)">never-retry</text>
  <text x="270" y="20" font-size="8.5" fill="var(--s1)">retryable</text>
  <text x="10" y="48" font-size="8.5" fill="var(--ink)">transient</text>
  <rect x="95" y="36" width="70" height="18" fill="var(--s1)"/><text x="118" y="49" font-size="8" fill="var(--panel)">right</text>
  <rect x="175" y="36" width="70" height="18" fill="var(--s2)"/><text x="196" y="49" font-size="8" fill="var(--panel)">wrong</text>
  <rect x="255" y="36" width="55" height="18" fill="var(--s1)"/><text x="272" y="49" font-size="8" fill="var(--panel)">right</text>
  <text x="10" y="78" font-size="8.5" fill="var(--ink)">permanent</text>
  <rect x="95" y="66" width="70" height="18" fill="var(--s2)"/><text x="115" y="79" font-size="8" fill="var(--panel)">wrong</text>
  <rect x="175" y="66" width="70" height="18" fill="var(--s1)"/><text x="198" y="79" font-size="8" fill="var(--panel)">right</text>
  <rect x="255" y="66" width="55" height="18" fill="var(--s1)"/><text x="272" y="79" font-size="8" fill="var(--panel)">right</text>
  <text x="10" y="108" font-size="8" fill="var(--muted)">each blanket column has a wrong cell; the flag column has none</text>
</svg>
^ Neither blanket policy is right in both rows — always-retry fails on the permanent error, never-retry fails on the transient one. Only the retryable flag is right for both, because it is the per-failure distinction the blanket policies lack.

Running the check confirms every clause, including the aggregate size win and the leaked internal paths.

```text filename=toolerr.py --check
  the raw traceback carries no machine-readable retryable field = True
  the structured error exposes a retryable flag = True
  structured drives RETRY for the transient rate-limit = True (retry after 2s)
  structured drives NO-RETRY for the permanent bad-argument = True (do not retry; surface hint to model)
  every blanket traceback-only policy mishandles a failure class = True (always-retry 1, never-retry 1)
  the structured errors are smaller than the tracebacks = True (366 < 481 chars)
  the tracebacks leak internal file paths (noise) = True
```

**The check pins the decision quality, not just the size — the structured error is right on both failure classes where every blanket policy is wrong on one, which is the reliability win, with the token saving on top.**

## Definition of done

Two properties close it. The structured error must drive the correct decision for both classes — retry transient, do not retry permanent — which no single traceback-only policy achieves, and the structured payloads must be smaller in aggregate than the tracebacks. The decision-correctness is the reliability win; the size is the context win.

```python filename=modules/agent-harness/code/toolerr-inter-01/toolerr.py:131-137 COMPLETE
    structured_smaller = sum(structured_size(f) for f in failures) < sum(raw_size(f) for f in failures)
    print("  the structured errors are smaller than the tracebacks = %s (%d < %d chars)" % (structured_smaller, sum(structured_size(f) for f in failures), sum(raw_size(f) for f in failures)))

    traceback_leaks_paths = all("/app/harness" in f["raw_traceback"] for f in failures)
    print("  the tracebacks leak internal file paths (noise) = %s" % traceback_leaks_paths)
```

Two honest caveats keep the tool calibrated. First, the size numbers here are illustrative and understated: these tracebacks are only two to four frames deep, so one structured error (the bad-argument one, 195 chars) is actually a touch larger than its shallow traceback (178) — the aggregate still wins, and in production the gap is enormous, because real tracebacks run dozens of frames through framework internals while the structured error stays fixed-size. The point is not that a structured error is always shorter than any traceback; it is that it is bounded and relevant while a traceback grows with stack depth and is mostly irrelevant. Second, a structured error is not a reason to discard the traceback entirely: keep it, but out of the model's context — log it under the error `code` for the human debugging later, and give the model only the structured fields. The classification (retryable, and the code) also has to be accurate; a tool that marks a permanent failure retryable sends the harness into a retry loop, which is why the failure taxonomy is worth designing deliberately rather than guessing per exception.

**Done means the structured error drives the correct retry decision for both failure classes and is smaller in aggregate — reliability from the retryable flag, context savings from dropping the stack dump, with the raw traceback kept in logs, not in the model's context.**

## Boss fight

Your agent occasionally gets stuck in a loop where it calls the same tool over and over, and you also notice it sometimes gives up on a task the moment a tool hiccups. Both behaviors trace back to how one tool reports failures: it catches every exception and returns `str(e)` to the model. Why does a single bad error-reporting choice produce both opposite-looking failures, and what is the fix?

Both come from the model (and the harness) having no reliable signal about whether a failure is retryable, because `str(e)` is unstructured text. When the underlying failure is permanent — a bad argument, a missing resource — the model cannot tell it is permanent, so it re-issues the same call expecting a different result, and loops; when the failure is transient — a rate limit, a brief timeout — the model cannot tell it is worth retrying either, so on a different run it reads the error as fatal and abandons the task. Same missing information, opposite symptoms, depending on which way the model guesses. The fix is to return a structured error from the tool: a stable code, a retryable flag, an optional retry_after, and a hint. Then the harness can enforce the right behavior mechanically — cap or forbid retries on non-retryable codes (killing the loop), and automatically retry retryable ones after the suggested delay before surfacing anything to the model (killing the premature give-up) — and when the model does see the error, it sees an instruction ("fix the user_id argument") rather than a string it has to interpret. As a guardrail, pair it with a loop check that treats repeated identical calls with identical results as no-progress, so even a mis-classified permanent error cannot loop forever. The root change, though, is replacing `str(e)` with a typed error the harness can branch on.

## External resources

The gRPC status code model and Google's API design guide on errors — the canonical taxonomy of machine-readable error codes with retry semantics (which codes are retryable, and RetryInfo carrying a delay), the production form of exactly the structured error this module argues for.

The Model Context Protocol tool-result specification, which distinguishes protocol errors from tool execution errors and returns results with an `isError` flag and structured content — how a modern agent tool interface represents failures to the model as data rather than as a raw exception string.
