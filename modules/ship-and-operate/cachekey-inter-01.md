---
id: cachekey-inter-01
title: Put every response-affecting input in the cache key — a key that omits one serves the first requester's variant to everyone who differs on it
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A cache is a promise that any two requests with the same key deserve the same response, and that promise is kept only if the key captures every input the response actually depends on. Leave one out and two requests that should get different answers collide on one key, so whichever arrived first has its answer cached for both. If a response depends on the resource and the locale, the correct key is the pair; key on the resource alone and the locale silently drops out of the entry's identity, so the first request for a resource caches its locale's rendering under the resource key, and every later request for that resource — whatever its locale — gets that first locale's response. The failure is quiet because the response is not corrupt, just wrong: a French user requesting a page gets a perfectly valid rendering in English because an English request populated the slot first — no exception, no malformed data, just the wrong variant served confidently from cache. It hides in testing, where one locale usually dominates and the collision rarely fires, and fires constantly in production with a real mix of locales. The fix is to compose the key from every response-affecting input — resource plus locale plus any other varying dimension (currency, device, feature cohort, user) — which is exactly the job of the HTTP Vary header. On a fixture where requests for the same resource in different locales collide under a resource-only key, a French request for page A is served the cached English response, while a key of (resource, locale) keeps the variants separate and every request is correct.
eli5: Imagine a coat-check where the tickets only have the coat's color written on them, not whose coat it is. You hand in your red coat, get ticket "red." Later someone else hands in their red coat and also gets ticket "red." When you both come back, the clerk grabs whichever red coat is on the hook first and gives it to whoever asks — so you might walk off with a stranger's coat. Nothing looks broken: it's a real red coat, just not yours. The fix is to write enough on the ticket to tell the coats apart — color and owner and size — so every different coat gets a different ticket. A cache ticket (the key) has to capture everything that makes one answer different from another, or it hands out the wrong answer to people who happen to share the incomplete ticket.
---

## Why this module

Caching is one of the highest-leverage tools in a system, and its whole correctness rests on one modeling decision that is easy to make carelessly: what goes in the key. The key defines the equivalence classes of requests — the cache assumes every request mapping to a key is interchangeable with every other, deserving the identical stored response. Get that equivalence right and the cache is a pure speedup; get it wrong and the cache becomes a source of confidently-served wrong answers.

The error is almost always an omission. A developer keys the cache on the obvious input — the URL, the resource id, the query — and forgets a second input that also shapes the response: the user's locale, their currency, their device type, an authenticated user id, an active feature flag. That second input varies the output but not the key, so requests that differ only on it are merged into one cache entry, and the first one to arrive fills it for all.

What makes this pernicious is that the served response is valid. It is not garbage or an error; it is a genuine response for a different variant, which is far harder to catch than a crash. And traffic patterns hide it: in a test or a low-diversity environment one variant dominates, the collision rarely fires, and everything looks fine — until production traffic spans all the variants and users start seeing each other's language, currency, or personalization. This module runs a mixed request stream through an incomplete and a complete key and counts the wrong serves.

**A cache key defines which requests are treated as interchangeable, so omitting a response-affecting input merges requests that deserve different answers — and the first variant to arrive is served, validly but wrongly, to all of them.**

## Concepts

The governing principle is that the key must be a function of exactly the inputs the response is a function of. If the response depends on inputs (a, b, c), the key must include (a, b, c); any input the output depends on but the key omits becomes a hidden dimension along which the cache silently serves stale variants. This is a completeness requirement, not a performance tuning knob: an incomplete key is not a slower cache, it is an incorrect one.

The symptom is specific and worth recognizing: cross-variant contamination. A wrong serve under an incomplete key is not a random or corrupted value; it is a real, correct response for a different value of the omitted input. That signature — "the data is valid but it is the wrong user's / language's / currency's version" — is the fingerprint of a key missing a dimension, and it points straight at which dimension by what varies between the expected and served responses.

The web already has a formal mechanism for this, which is worth knowing because it names the discipline. HTTP's Vary response header declares exactly which request headers the response varies on — Vary: Accept-Language says "this response depends on the language, so cache it separately per language." A shared cache that honors Vary composes the key from the URL plus the named headers; one that ignores it commits precisely this bug. The same idea applies to any cache, HTTP or not: enumerate what the output varies on, and put all of it in the key.

<svg role="img" aria-label="The response depends on inputs resource, locale, and device; the incomplete key covers only resource, leaving locale and device as hidden dimensions the cache serves stale across" viewBox="0 0 440 130">
<text x="90" y="20" fill="var(--ink)" font-size="9" text-anchor="middle">output depends on</text>
<rect x="30" y="30" width="60" height="20" fill="var(--panel)" stroke="var(--s1)"/>
<text x="60" y="44" fill="var(--ink)" font-size="8" text-anchor="middle">resource</text>
<rect x="30" y="55" width="60" height="20" fill="var(--panel)" stroke="var(--s1)"/>
<text x="60" y="69" fill="var(--ink)" font-size="8" text-anchor="middle">locale</text>
<rect x="30" y="80" width="60" height="20" fill="var(--panel)" stroke="var(--s1)"/>
<text x="60" y="94" fill="var(--ink)" font-size="8" text-anchor="middle">device</text>
<text x="300" y="20" fill="var(--ink)" font-size="9" text-anchor="middle">incomplete key covers</text>
<rect x="270" y="30" width="60" height="20" fill="var(--panel)" stroke="var(--s1)"/>
<text x="300" y="44" fill="var(--ink)" font-size="8" text-anchor="middle">resource</text>
<line x1="90" y1="40" x2="270" y2="40" stroke="var(--s1)"/>
<text x="360" y="69" fill="var(--s2)" font-size="8">locale: hidden</text>
<text x="360" y="94" fill="var(--s2)" font-size="8">device: hidden</text>
</svg>
^ Any response-affecting input the key omits becomes a hidden dimension the cache serves stale variants across; the key must cover all of them.

**The key must be a function of every input the output is a function of; the signature of a missing dimension is cross-variant contamination — a valid response for the wrong variant — and HTTP's Vary header is the formal name for declaring those dimensions.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/cachekey-inter-01. The fixture is a stream of requests that differ by resource and by locale, both of which affect the response.

```json filename=modules/ship-and-operate/code/cachekey-inter-01/cachekey.json:3-5 COMPLETE
  "requests": [
    {"resource": "A", "locale": "en"},
    {"resource": "A", "locale": "fr"},
```

The correct response depends on both inputs.

```python filename=modules/ship-and-operate/code/cachekey-inter-01/cachekey.py:34-36 COMPLETE
def correct_response(req):
    """The right response depends on both inputs: the resource and the locale."""
    return "%s/%s" % (req["resource"], req["locale"])
```

The cache stores the response computed on a miss under whatever key it is given.

```python filename=modules/ship-and-operate/code/cachekey-inter-01/cachekey.py:39-48 COMPLETE
def serve(requests, key_fn):
    """Run the requests through a cache keyed by key_fn; return the response served to each."""
    cache = {}
    served = []
    for req in requests:
        key = key_fn(req)
        if key not in cache:
            cache[key] = correct_response(req)   # computed on a miss, stored under the key
        served.append(cache[key])
    return served
```

The incomplete key uses the resource only; the complete key uses both inputs.

```python filename=modules/ship-and-operate/code/cachekey-inter-01/cachekey.py:51-53 COMPLETE
def incomplete_key(req):
    """Keys on the resource only -- omits the locale, which also affects the response."""
    return req["resource"]
```

Before running it, predict: the second request (A/fr) will hit the entry the first request (A/en) filled and be served A/en. Run `--serve`:

```text filename=cachekey.py --serve
SERVE — response served to each request, and whether it is correct
--------------------------------------------------------------------
  request      want    incomplete-key   complete-key
  A/en       A/en    A/en   ok       A/en   ok
  A/fr       A/fr    A/en   WRONG    A/fr   ok
  B/fr       B/fr    B/fr   ok       B/fr   ok
  A/en       A/en    A/en   ok       A/en   ok
```

The prediction holds. The A/fr request wanted A/fr but was served A/en — the English response the first A request cached under the shared key "A". Every other request happens to be correct here (their key was filled by a matching variant), but the collision fired for the one request whose locale differed from the slot's owner. The complete key gives A/en and A/fr separate slots, and every request is correct.

<svg role="img" aria-label="Two requests A/en and A/fr both map to the key A under the incomplete key, so A/fr gets served the cached A/en; under the complete key they map to separate keys and each is correct" viewBox="0 0 440 150">
<text x="110" y="18" fill="var(--s2)" font-size="9" text-anchor="middle">incomplete key</text>
<text x="40" y="45" fill="var(--ink)" font-size="9">A/en</text>
<text x="40" y="80" fill="var(--ink)" font-size="9">A/fr</text>
<line x1="70" y1="42" x2="150" y2="55" stroke="var(--s2)"/>
<line x1="70" y1="77" x2="150" y2="60" stroke="var(--s2)"/>
<rect x="150" y="48" width="60" height="20" fill="var(--panel)" stroke="var(--s2)"/>
<text x="180" y="62" fill="var(--ink)" font-size="9" text-anchor="middle">key "A"</text>
<text x="180" y="90" fill="var(--s2)" font-size="8" text-anchor="middle">A/fr served A/en</text>
<text x="330" y="18" fill="var(--s1)" font-size="9" text-anchor="middle">complete key</text>
<text x="260" y="45" fill="var(--ink)" font-size="9">A/en</text>
<text x="260" y="80" fill="var(--ink)" font-size="9">A/fr</text>
<line x1="290" y1="42" x2="360" y2="42" stroke="var(--s1)"/>
<line x1="290" y1="77" x2="360" y2="77" stroke="var(--s1)"/>
<rect x="360" y="34" width="66" height="16" fill="var(--panel)" stroke="var(--s1)"/>
<text x="393" y="46" fill="var(--ink)" font-size="8" text-anchor="middle">(A,en)</text>
<rect x="360" y="69" width="66" height="16" fill="var(--panel)" stroke="var(--s1)"/>
<text x="393" y="81" fill="var(--ink)" font-size="8" text-anchor="middle">(A,fr)</text>
</svg>
^ The incomplete key merges A/en and A/fr into one slot so the second gets the first's response; the complete key gives them separate slots.

Now isolate the wrong serve. Run `--wrong`:

```text filename=cachekey.py --wrong
WRONG — requests served the wrong variant under the resource-only key
--------------------------------------------------------------
  wanted A/fr but served A/en  (same key 'A')
--------------------------------------------------------------
  each wrong serve is a real response for the wrong locale -- a cache collision
```

The wrong serve is exactly the cross-variant signature: it wanted A/fr and got A/en — a valid page A, in the wrong language, because both share the key "A". Nothing is malformed; the cache did precisely what its key told it to, which was to treat two different requests as one.

<svg role="img" aria-label="The A/fr request's wanted response A/fr versus the served response A/en: both are valid page-A responses, differing only in the omitted locale dimension" viewBox="0 0 440 120">
<text x="110" y="30" fill="var(--ink)" font-size="10" text-anchor="middle">wanted</text>
<rect x="60" y="42" width="100" height="30" fill="var(--panel)" stroke="var(--s1)"/>
<text x="110" y="61" fill="var(--s1)" font-size="11" text-anchor="middle">A / fr</text>
<text x="330" y="30" fill="var(--ink)" font-size="10" text-anchor="middle">served</text>
<rect x="280" y="42" width="100" height="30" fill="var(--panel)" stroke="var(--s2)"/>
<text x="330" y="61" fill="var(--s2)" font-size="11" text-anchor="middle">A / en</text>
<text x="220" y="95" fill="var(--muted)" font-size="9" text-anchor="middle">same resource A, wrong locale — the omitted dimension is exactly what differs</text>
</svg>
^ The wrong serve is a valid page-A response differing from the wanted one only in the locale — the very dimension the key left out.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that the incomplete key serves a wrong variant, that the complete key serves everything correctly, that requests differing only in locale collide under the incomplete key while the complete key distinguishes them, and that every wrong serve is a valid (cross-variant) response.

```python filename=modules/ship-and-operate/code/cachekey-inter-01/cachekey.py:100-108 COMPLETE
    incomplete_serves_wrong = len(wrong_inc) > 0
    print("  incomplete key serves at least one wrong variant = %s (%d)" % (incomplete_serves_wrong, len(wrong_inc)))

    complete_all_correct = all(g == correct_response(r) for r, g in zip(reqs, com))
    print("  complete key serves every request correctly = %s" % complete_all_correct)

    # two requests differing only in locale collide under the incomplete key
    collision = any(incomplete_key(a) == incomplete_key(b) and a["locale"] != b["locale"]
                    for a in reqs for b in reqs)
    print("  requests differing only in locale share an incomplete key = %s" % collision)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if the incomplete key ever stops colliding or the complete key ever serves a wrong variant:

```text filename=cachekey.py --check
SELF-TEST — an incomplete key serves cross-variant wrong responses; a complete key is always correct
------------------------------------------------------------------------------------------------------------
  incomplete key serves at least one wrong variant = True (1)
  complete key serves every request correctly = True
  requests differing only in locale share an incomplete key = True
  the complete key gives those requests different keys = True
  every wrong serve is a valid response, just the wrong variant = True
```

**The self-test asserts the wrong serve is a valid response for another variant — pinning the failure as a cache collision on a missing dimension, not a compute error, which is what makes it hide in testing.**

## Definition of done

You can explain why the cache key defines which requests are treated as interchangeable and why that makes an omitted input a correctness bug, not a performance one.
You can describe the cross-variant contamination signature — a valid response for the wrong variant — and use it to identify which dimension the key is missing.
You can explain why the bug hides in testing (one variant dominates) and fires in production (a mix of variants).
You can name HTTP's Vary header as the formal mechanism and generalize it to any cache: enumerate what the output varies on and key on all of it.
You can predict, for a new cached endpoint, which inputs must be in the key.

## Boss fight

Consider the opposite error: putting too much in the key. If you include an input that does not affect the response — a request id, a timestamp, a tracking parameter — every request gets a unique key, so nothing ever hits the cache and the hit rate collapses to zero. The cache is now correct but useless, a pure overhead. The lesson has two edges: the key must include every input that affects the output (or it serves wrong answers) and exclude every input that does not (or it never hits). The right key is exactly the response-affecting inputs, no more and no less, which is why normalizing the key — stripping irrelevant query params, canonicalizing header values — matters as much as including the relevant ones.

Now consider a subtler completeness failure: an input that affects the response indirectly. Suppose the response depends on a feature flag whose value is looked up from the user's cohort, and you key on the user id — that seems complete, but if the flag flips for everyone, every cached entry is now stale despite the key being unchanged, because the response depended on the flag's value, not just the user. This is why response-affecting configuration is often folded into the key as a version or an epoch: bump the config version and every old entry's key no longer matches, invalidating the whole cache atomically. The completeness rule extends to inputs that are not part of the request at all — global state the response depends on must be represented in the key (as a version) or the cache serves answers from a world that no longer exists.

**The key must include every response-affecting input and exclude every irrelevant one — too little serves wrong variants, too much kills the hit rate — and response-affecting global state (a config or flag) must enter the key as a version, or a change to it leaves every entry stale under an unchanged key.**

## External resources

The HTTP caching specification's Vary header is the formal mechanism for declaring which request dimensions a response varies on, so shared caches key correctly.
CDN and reverse-proxy documentation (Fastly, Cloudflare, Varnish) covers cache-key customization and the classic bugs of caching per-URL while ignoring locale, device, or auth.
The topic's own modules on single-flight coalescing and negative caching cover other cache correctness and efficiency concerns that compose with getting the key right.
