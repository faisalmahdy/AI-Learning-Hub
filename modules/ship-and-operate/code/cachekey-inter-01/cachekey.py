"""Compose the cache key from every input that affects the output -- a key that omits an input serves the first requester's variant to everyone who differs only on that input.

A cache is a promise: any two requests with the same key deserve the same response. That promise is only kept if the key captures every input the response actually depends on. Leave one out, and two requests that should get different answers now collide on one key, and whichever arrived first has its answer cached for both.

Here the response depends on two things: which resource is requested and which locale it is rendered in. The correct key is the pair. Key on the resource alone and the locale silently drops out of the identity of the cache entry: the first request for resource A caches A-in-its-locale under the key "A", and every later request for A -- whatever its locale -- gets that first locale's response back.

The failure is quiet because the response is not corrupt, just wrong. A French user requesting page A gets a perfectly valid rendering of page A, in English, because an English request populated the slot first. No exception, no malformed data -- just the wrong variant, served confidently from cache. In testing, where one locale usually dominates the traffic, the collision rarely fires; in production, with a mix of locales, it fires constantly and shows up as baffling "why is this user seeing the wrong language" reports.

The fix is to put every response-affecting input into the key. If the output varies by locale, the key includes the locale; if it varies by currency, device, feature-flag cohort, or authenticated user, each of those goes in too. The discipline is exactly the HTTP Vary header's job -- declare what the response varies on so the cache splits its entries along those dimensions.

The rule: build the cache key from every input that affects the output -- resource plus locale plus any other varying dimension -- because a key that omits a response-affecting input collides requests that deserve different responses, serving the first variant to all of them; the response is valid but for the wrong variant.

On this fixture requests for the same resource in different locales collide under a resource-only key, so a French request for page A is served the cached English response; a key of (resource, locale) keeps the variants separate and every request gets its correct response. This computes both.

  --serve    each request's served response and whether it matches the correct one, under each key scheme
  --wrong    the requests served the wrong variant under the incomplete key, and why
  --check    an incomplete key serves cross-variant wrong responses; a complete key is always correct

requests is the fixture; the served responses and their correctness under each key are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "cachekey.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def correct_response(req):
    """The right response depends on both inputs: the resource and the locale."""
    return "%s/%s" % (req["resource"], req["locale"])


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


def incomplete_key(req):
    """Keys on the resource only -- omits the locale, which also affects the response."""
    return req["resource"]


def complete_key(req):
    """Keys on every response-affecting input: the resource and the locale."""
    return (req["resource"], req["locale"])


# ----------------------------------------------------------------- printing

def serve_view(data):
    reqs = data["requests"]
    inc = serve(reqs, incomplete_key)
    com = serve(reqs, complete_key)
    print("SERVE — response served to each request, and whether it is correct")
    print("-" * 68)
    print("  request      want    incomplete-key   complete-key")
    for req, i, c in zip(reqs, inc, com):
        wanted = correct_response(req)
        print("  %s/%-4s     %-5s   %-6s %-6s   %-6s %s"
              % (req["resource"], req["locale"], wanted,
                 i, "ok" if i == wanted else "WRONG", c, "ok" if c == wanted else "WRONG"))
    print("-" * 68)
    print("  the incomplete key serves one locale's response for every locale")


def wrong_view(data):
    reqs = data["requests"]
    inc = serve(reqs, incomplete_key)
    print("WRONG — requests served the wrong variant under the resource-only key")
    print("-" * 62)
    for req, got in zip(reqs, inc):
        wanted = correct_response(req)
        if got != wanted:
            print("  wanted %s but served %s  (same key '%s')" % (wanted, got, incomplete_key(req)))
    print("-" * 62)
    print("  each wrong serve is a real response for the wrong locale -- a cache collision")


def check(data):
    print("SELF-TEST — an incomplete key serves cross-variant wrong responses; a complete key is always correct")
    print("-" * 108)
    reqs = data["requests"]
    inc = serve(reqs, incomplete_key)
    com = serve(reqs, complete_key)

    wrong_inc = [correct_response(r) for r, g in zip(reqs, inc) if g != correct_response(r)]
    incomplete_serves_wrong = len(wrong_inc) > 0
    print("  incomplete key serves at least one wrong variant = %s (%d)" % (incomplete_serves_wrong, len(wrong_inc)))

    complete_all_correct = all(g == correct_response(r) for r, g in zip(reqs, com))
    print("  complete key serves every request correctly = %s" % complete_all_correct)

    # two requests differing only in locale collide under the incomplete key
    collision = any(incomplete_key(a) == incomplete_key(b) and a["locale"] != b["locale"]
                    for a in reqs for b in reqs)
    print("  requests differing only in locale share an incomplete key = %s" % collision)

    complete_distinguishes = all(complete_key(a) != complete_key(b)
                                 for i, a in enumerate(reqs) for b in reqs[i + 1:]
                                 if a["resource"] == b["resource"] and a["locale"] != b["locale"])
    print("  the complete key gives those requests different keys = %s" % complete_distinguishes)

    wrong_is_real_response = all(g in {correct_response(r) for r in reqs} for r, g in zip(reqs, inc))
    print("  every wrong serve is a valid response, just the wrong variant = %s" % wrong_is_real_response)

    ok = (incomplete_serves_wrong and complete_all_correct and collision
          and complete_distinguishes and wrong_is_real_response)
    print("-" * 108)
    print("SELF-TEST %s  incomplete_serves_wrong=%s  complete_all_correct=%s  collision=%s  complete_distinguishes=%s  wrong_is_real_response=%s"
          % ("PASS" if ok else "FAIL", incomplete_serves_wrong, complete_all_correct,
             collision, complete_distinguishes, wrong_is_real_response))
    return ok


def main():
    p = argparse.ArgumentParser(description="Cache key completeness: build the cache key from every input that affects the output -- resource plus locale plus any other varying dimension -- because a key that omits a response-affecting input collides requests that deserve different responses, serving the first variant to all of them; the response is valid but for the wrong variant.")
    p.add_argument("--serve", action="store_true")
    p.add_argument("--wrong", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("requests=%d  file=%s  (the requests are a fixture; response depends on resource and locale)"
          % (len(data["requests"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.serve:
        serve_view(data)
    elif args.wrong:
        wrong_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
