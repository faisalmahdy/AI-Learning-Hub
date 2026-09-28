---
id: retryclass-inter-01
title: Classify errors before retrying — retry transient failures, fail fast on permanent ones, or you waste every attempt on a 4xx that can't recover
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A retry is a bet that the failure was temporary, and that bet pays off for a whole class of errors — a 503 from an overloaded service, a 500 from a transient glitch, a 429 rate-limit, a dropped connection or a timeout can all succeed on a later attempt once the momentary condition clears. The bet loses for the other class: a 400 malformed request, a 401 unauthorized, a 403 forbidden, a 404 not-found are deterministic verdicts on the request itself, and none of that changes because you send it again, so retrying a permanent error returns the same error the second time, the third, and the last, with certainty. A policy that retries every failure indiscriminately spends its attempts on requests that can never succeed: it burns the retry budget on the permanent failures, adds several backoff delays of latency before surfacing an error the first attempt already determined, and pounds the backend with requests it has already definitively rejected — all for nothing, because the outcome for a permanent error is fixed from the first try. The fix is to look at the error before deciding to retry: classify by status, so 5xx, 429, and network-level errors are retried while most 4xx fail fast with the error the caller needs to fix. On a fixture of six failed requests (three transient, three permanent) with a retry limit of 3, a blind retry-everything policy uses 24 attempts and wastes 9 on the permanent errors, while a classify-first policy uses 15 and wastes none.
eli5: Imagine you keep calling a phone number and it doesn't go through. Sometimes the reason is temporary — the line was busy, or the network hiccuped — and calling again a moment later works fine; retrying makes sense. But sometimes the reason is permanent: the number you dialed doesn't exist, or you dialed it wrong. Redialing a wrong number a hundred times will never connect it, no matter how patiently you wait between tries — you'll just waste your time and the phone company's. The smart move is to notice which kind of failure you got: if the line was busy, try again; if the number is invalid, stop immediately and go fix the number. Computer requests fail the same two ways, and a good retry rule checks the reason first — retry the temporary failures, and give up right away on the ones that will never work.
---

## Why this module

Retries are one of the highest-leverage reliability tools there is: a large fraction of failures in a distributed system are transient, and a simple retry converts them into successes the caller never even notices. That success makes it tempting to wrap every call in a retry loop and move on. The trouble is that "retry on failure" quietly assumes all failures are the kind a retry can fix, and they are not.

Failures come in two fundamentally different kinds. A transient failure is a property of the moment — the server was overloaded, a packet was lost, a rate limit was briefly hit — and the moment passes, so a later attempt can succeed. A permanent failure is a property of the request — it is malformed, unauthorized, or aimed at something that does not exist — and that property travels with the request, so every attempt meets the same verdict.

Retrying across this line is not merely unhelpful, it is actively costly. Each retry of a permanent failure consumes a slot of the retry budget, adds a backoff delay to the eventual error, and sends the backend another copy of a request it already rejected — during an incident, that is load poured on exactly when it hurts. And it buys nothing, because the answer was decided on the first attempt. This module runs a mixed batch of failures through a blind policy and a classify-first policy and counts the wasted attempts.

**Failures are either transient (a property of the moment, retryable) or permanent (a property of the request, not), and retrying across that line spends budget, latency, and backend load on requests whose answer was fixed from the first attempt.**

## Concepts

The classification is what makes a retry policy correct, and it maps cleanly onto status codes. Server errors (5xx) mean the server failed to handle a request that may be fine — transient, retry. A 429 means slow down, not stop — transient, retry after a wait. Network-level failures (timeouts, connection resets) are transient by nature. Client errors (most 4xx) mean the request itself is the problem — permanent, fail fast. This is not a heuristic to be tuned so much as a reading of what each error category actually asserts.

The reason fail-fast is the right response to a permanent error, not just an acceptable one, is that speed of failure is itself valuable. A permanent error is information the caller needs to act on — fix the request, refresh the token, correct the URL — and delaying it behind three backoff waits helps no one. Failing fast surfaces the actionable error immediately, which is a better outcome for the caller than a slow identical error, quite apart from the resources saved.

There is an interaction with the other retry disciplines worth seeing. The retry budget, the backoff, the jitter, the amplification across layers — all of those govern how and how much you retry, and all of them are undermined if you retry the wrong things. Spending the budget on permanent failures leaves less for the transient ones that could actually use it; classification is the gate that must run before those other mechanisms, so they are applied only to failures that can benefit. Get the classification wrong and the sophistication of the rest is wasted.

<svg role="img" aria-label="A decision gate: a failure enters, is classified transient or permanent; transient flows to the retry machinery (budget, backoff), permanent flows straight to fail-fast" viewBox="0 0 440 130">
<rect x="20" y="50" width="70" height="26" fill="var(--panel)" stroke="var(--line)"/>
<text x="55" y="67" fill="var(--ink)" font-size="9" text-anchor="middle">failure</text>
<line x1="90" y1="63" x2="140" y2="63" stroke="var(--muted)"/>
<rect x="140" y="48" width="80" height="30" fill="var(--panel)" stroke="var(--ink)"/>
<text x="180" y="67" fill="var(--ink)" font-size="9" text-anchor="middle">classify</text>
<line x1="220" y1="55" x2="300" y2="35" stroke="var(--s1)"/>
<text x="255" y="34" fill="var(--s1)" font-size="8">transient</text>
<rect x="300" y="22" width="120" height="26" fill="var(--panel)" stroke="var(--s1)"/>
<text x="360" y="39" fill="var(--ink)" font-size="9" text-anchor="middle">budget + backoff</text>
<line x1="220" y1="70" x2="300" y2="92" stroke="var(--s2)"/>
<text x="255" y="92" fill="var(--s2)" font-size="8">permanent</text>
<rect x="300" y="80" width="120" height="26" fill="var(--panel)" stroke="var(--s2)"/>
<text x="360" y="97" fill="var(--ink)" font-size="9" text-anchor="middle">fail fast</text>
</svg>
^ Classification is the gate before the retry machinery: only transient failures reach the budget and backoff; permanent ones exit immediately.

**Status codes read directly as transient (5xx, 429, network) or permanent (most 4xx); failing fast on permanent errors surfaces the actionable error sooner, and classification is the gate that must precede budget and backoff so they are spent only where a retry can help.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/retryclass-inter-01. The fixture is six failed requests, three with transient codes and three with permanent ones, and a retry limit.

```json filename=modules/ship-and-operate/code/retryclass-inter-01/retryclass.json:3-11 COMPLETE
  "requests": [
    {"id": "q1", "code": 503},
    {"id": "q2", "code": 500},
    {"id": "q3", "code": 429},
    {"id": "q4", "code": 400},
    {"id": "q5", "code": 404},
    {"id": "q6", "code": 401}
  ],
  "max_retries": 3
```

The classification is a single predicate on the status code.

```python filename=modules/ship-and-operate/code/retryclass-inter-01/retryclass.py:34-36 COMPLETE
def is_transient(code):
    """Transient (worth retrying): server errors and rate limits. Permanent: most 4xx."""
    return code >= 500 or code == 429
```

The blind policy gives every request the full retry allowance regardless of its error.

```python filename=modules/ship-and-operate/code/retryclass-inter-01/retryclass.py:39-41 COMPLETE
def attempts_blind(request, max_retries):
    """Retry everything: every request gets the full retry allowance."""
    return 1 + max_retries
```

The classify-first policy retries only transient errors and fails permanent ones on the first attempt.

```python filename=modules/ship-and-operate/code/retryclass-inter-01/retryclass.py:44-46 COMPLETE
def attempts_classify(request, max_retries):
    """Classify first: retry transient errors, fail permanent ones on the first attempt."""
    return 1 + max_retries if is_transient(request["code"]) else 1
```

First, the classification. Predict: 503, 500, 429 are transient (retry); 400, 404, 401 are permanent (fail fast). Run `--classify`:

```text filename=retryclass.py --classify
CLASSIFY — each failed request by status code
------------------------------------------------
  id    code   class       action
  q1    503    transient   retry
  q2    500    transient   retry
  q3    429    transient   retry
  q4    400    permanent   fail fast
  q5    404    permanent   fail fast
  q6    401    permanent   fail fast
------------------------------------------------
  5xx and 429 can recover; most 4xx are verdicts on the request itself
```

The prediction holds. The three server/rate-limit errors are marked retry; the three client errors are marked fail fast. The split is exactly the transient/permanent line drawn through the status codes.

<svg role="img" aria-label="Six status codes sorted into two bins: 503, 500, 429 into transient-retry; 400, 404, 401 into permanent-fail-fast" viewBox="0 0 440 140">
<rect x="20" y="30" width="190" height="90" fill="var(--panel)" stroke="var(--s1)"/>
<text x="115" y="50" fill="var(--ink)" font-size="10" text-anchor="middle">transient — retry</text>
<text x="60" y="78" fill="var(--s1)" font-size="12" text-anchor="middle">503</text>
<text x="115" y="78" fill="var(--s1)" font-size="12" text-anchor="middle">500</text>
<text x="170" y="78" fill="var(--s1)" font-size="12" text-anchor="middle">429</text>
<text x="115" y="104" fill="var(--muted)" font-size="8" text-anchor="middle">the moment can pass</text>
<rect x="230" y="30" width="190" height="90" fill="var(--panel)" stroke="var(--s2)"/>
<text x="325" y="50" fill="var(--ink)" font-size="10" text-anchor="middle">permanent — fail fast</text>
<text x="270" y="78" fill="var(--s2)" font-size="12" text-anchor="middle">400</text>
<text x="325" y="78" fill="var(--s2)" font-size="12" text-anchor="middle">404</text>
<text x="380" y="78" fill="var(--s2)" font-size="12" text-anchor="middle">401</text>
<text x="325" y="104" fill="var(--muted)" font-size="8" text-anchor="middle">the request is the problem</text>
</svg>
^ The status code reads directly as transient (retry) or permanent (fail fast); the code is the classifier.

Now the cost. Predict: blind retries all six with 3 retries each (24 attempts); classify retries only the three transient ones. Run `--attempts`:

```text filename=retryclass.py --attempts
ATTEMPTS — total attempts with retry limit 3
----------------------------------------------------
  retry everything : 24 attempts
  classify first   : 15 attempts
  wasted retries on permanent errors (avoided): 9
----------------------------------------------------
  the avoided retries were guaranteed to fail with the same error
```

The prediction holds. Blind spends 24 attempts; classify spends 15. The 9-attempt difference is exactly the wasted retries — three permanent errors times three retries each — every one of which was guaranteed to return the same error. Those 9 attempts are pure cost: budget, latency, and backend load spent on a foregone conclusion.

<svg role="img" aria-label="Two attempt totals: retry-everything 24 attempts with 9 shaded as wasted on permanent errors; classify-first 15 attempts with none wasted" viewBox="0 0 440 140">
<line x1="40" y1="115" x2="410" y2="115" stroke="var(--line)"/>
<rect x="80" y="35" width="70" height="80" fill="var(--s1)"/>
<rect x="80" y="35" width="70" height="30" fill="var(--s2)"/>
<text x="115" y="53" fill="var(--ink)" font-size="9" text-anchor="middle">9 wasted</text>
<text x="115" y="130" fill="var(--muted)" font-size="9" text-anchor="middle">retry all: 24</text>
<rect x="290" y="65" width="70" height="50" fill="var(--s1)"/>
<text x="325" y="130" fill="var(--muted)" font-size="9" text-anchor="middle">classify: 15</text>
<text x="325" y="58" fill="var(--s1)" font-size="9" text-anchor="middle">0 wasted</text>
</svg>
^ Retry-everything spends 24 attempts, 9 of them wasted on permanent errors; classify-first spends 15 and wastes none.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the classification matches the 5xx/429 rule, that classify-first uses fewer attempts, that it retries no permanent error and every transient one, and that the attempts saved equal exactly the wasted retries.

```python filename=modules/ship-and-operate/code/retryclass-inter-01/retryclass.py:91-101 COMPLETE
    classify_fewer_attempts = smart < blind
    print("  classify-first uses fewer total attempts = %s (%d < %d)" % (classify_fewer_attempts, smart, blind))

    permanent_not_retried = all(attempts_classify(r, mr) == 1 for r in perm)
    print("  classify-first does not retry any permanent error = %s (%d permanent)" % (permanent_not_retried, len(perm)))

    transient_still_retried = all(attempts_classify(r, mr) == 1 + mr for r in tran)
    print("  classify-first still retries every transient error = %s (%d transient)" % (transient_still_retried, len(tran)))

    saved = blind - smart
    saved_equals_wasted = saved == len(perm) * mr
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the policy ever retries a permanent error or stops retrying a transient one:

```text filename=retryclass.py --check
SELF-TEST — retry-everything wastes attempts on permanent errors; classify-first retries only what can recover
--------------------------------------------------------------------------------------------------------------------
  transient = 5xx or 429; permanent = other 4xx = True
  classify-first uses fewer total attempts = True (15 < 24)
  classify-first does not retry any permanent error = True (3 permanent)
  classify-first still retries every transient error = True (3 transient)
  the attempts saved equal the wasted retries on permanent errors = True (9)
```

**The self-test ties the attempts saved to the wasted retries exactly — proving the saving comes from not retrying permanent errors, while every transient error still gets its full allowance.**

## Definition of done

You can distinguish a transient failure (a property of the moment) from a permanent one (a property of the request) and give examples of each.
You can map status codes to the classification: 5xx, 429, and network errors transient; most 4xx permanent.
You can explain why retrying a permanent error is not just useless but costly — budget, latency, and backend load spent for a foregone outcome.
You can explain why failing fast is the right response to a permanent error, not just an acceptable one — it surfaces the actionable error sooner.
You can explain why classification must gate the other retry disciplines (budget, backoff, jitter) so they are spent only where a retry can help.

## Boss fight

Not every code is cleanly one class. A 429 is transient but special — it carries a Retry-After telling you when the moment will pass, so it should be retried on the server's schedule, not the client's backoff (the subject of a companion module). A 409 conflict may be transient (retry may resolve a race) or permanent (a genuine conflict), depending on the operation. A 408 request-timeout is transient. And a 500 that is actually a deterministic server bug will fail every retry despite being "transient" by code. The lesson sharpens: the status code is the first-pass classifier and usually right, but the truly correct classification is whether the failure is a property of the moment or the request, and a few codes need operation-specific judgment.

Now consider idempotency, which interacts sharply here. Classifying an error as transient authorizes a retry, but a retry is only safe if the operation is idempotent — retrying a non-idempotent write that actually succeeded before the connection dropped can double the effect. So the retry decision is really two gates in series: is the error transient (can a retry help?) and is the operation idempotent (is a retry safe?). A transient error on a non-idempotent operation is the dangerous quadrant — the retry might help and might double-charge — and needs an idempotency key to make the retry safe, which is why classification and idempotency are companion disciplines, not alternatives.

**The status code is the first-pass classifier but a few codes (429, 409, deterministic 500s) need operation-specific judgment; and even a correctly transient error is only safe to retry if the operation is idempotent — the retry decision is a transient-AND-idempotent conjunction, not a status check alone.**

## External resources

Google's SRE book and AWS's "timeouts, retries and backoff with jitter" guidance both stress retrying only retryable (transient) errors and failing fast on client errors, alongside budgets and backoff.
The gRPC and HTTP client documentation for major SDKs publish their default retryable-status-code sets (typically 5xx subset plus 429 and connection errors), which encode exactly this classification.
The topic's own modules on the retry budget, on honoring Retry-After, and on idempotent retries cover the disciplines that this classification gates and interacts with.
