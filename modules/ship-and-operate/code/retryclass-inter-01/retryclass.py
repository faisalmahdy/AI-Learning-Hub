"""Classify errors before retrying -- retry only transient failures, fail fast on permanent ones -- because retrying a permanent error (a 4xx) produces the identical error every time, wasting the retry budget and delaying the inevitable failure.

A retry is a bet that the failure was temporary. That bet pays off for a whole class of errors: a 503 from an overloaded service, a 500 from a transient glitch, a 429 rate-limit, a dropped connection or a timeout can all succeed on a later attempt once the momentary condition clears. Retrying them is exactly right, and is what retry logic exists for.

The bet loses for the other class. A 400 malformed request, a 401 unauthorized, a 403 forbidden, a 404 not-found are not momentary -- they are deterministic verdicts on the request itself. The request is wrong, or unauthorized, or aimed at something that does not exist, and none of that changes because you send it again. Retrying a permanent error returns the same error the second time, the third, and the last, with certainty.

So a policy that retries every failure indiscriminately spends its attempts on requests that can never succeed. It burns the retry budget on the permanent failures, adds latency -- several backoff delays -- before surfacing an error the first attempt already determined, and pounds the backend with requests it has already definitively rejected. All of that cost buys nothing, because the outcome for a permanent error is fixed from the first try.

The fix is to look at the error before deciding to retry. Classify by status: 5xx, 429, and network-level errors are transient and worth retrying; most 4xx are permanent and should fail fast, immediately, with the error the caller needs to fix the request. Retry what can recover; do not retry what cannot.

The rule: classify a failure before retrying -- retry transient errors (5xx, 429, timeouts, connection errors) and fail fast on permanent ones (most 4xx) -- because retrying a permanent error yields the identical error every attempt, wasting the retry budget and the latency while never succeeding.

On this fixture six requests fail: three transient (503, 500, 429) and three permanent (400, 404, 401), with a retry limit of 3. A blind policy retries all six and wastes 9 attempts on the permanent ones; a classify-first policy retries only the transient three and fails the permanent three immediately. This computes both.

  --classify   each request's status code and whether it is transient (retry) or permanent (fail fast)
  --attempts   total attempts and wasted retries under retry-everything vs classify-first
  --check      retry-everything wastes attempts on permanent errors; classify-first retries only what can recover

requests and max_retries are the fixture; the classification and the attempt counts are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "retryclass.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def is_transient(code):
    """Transient (worth retrying): server errors and rate limits. Permanent: most 4xx."""
    return code >= 500 or code == 429


def attempts_blind(request, max_retries):
    """Retry everything: every request gets the full retry allowance."""
    return 1 + max_retries


def attempts_classify(request, max_retries):
    """Classify first: retry transient errors, fail permanent ones on the first attempt."""
    return 1 + max_retries if is_transient(request["code"]) else 1


# ----------------------------------------------------------------- printing

def classify_view(data):
    print("CLASSIFY — each failed request by status code")
    print("-" * 48)
    print("  id    code   class       action")
    for r in data["requests"]:
        t = is_transient(r["code"])
        print("  %-4s  %-5d  %-10s  %s"
              % (r["id"], r["code"], "transient" if t else "permanent", "retry" if t else "fail fast"))
    print("-" * 48)
    print("  5xx and 429 can recover; most 4xx are verdicts on the request itself")


def attempts_view(data):
    reqs, mr = data["requests"], data["max_retries"]
    blind = sum(attempts_blind(r, mr) for r in reqs)
    smart = sum(attempts_classify(r, mr) for r in reqs)
    wasted = sum(mr for r in reqs if not is_transient(r["code"]))
    print("ATTEMPTS — total attempts with retry limit %d" % mr)
    print("-" * 52)
    print("  retry everything : %d attempts" % blind)
    print("  classify first   : %d attempts" % smart)
    print("  wasted retries on permanent errors (avoided): %d" % wasted)
    print("-" * 52)
    print("  the avoided retries were guaranteed to fail with the same error")


def check(data):
    print("SELF-TEST — retry-everything wastes attempts on permanent errors; classify-first retries only what can recover")
    print("-" * 116)
    reqs, mr = data["requests"], data["max_retries"]

    transient_are_5xx_429 = all(is_transient(r["code"]) == (r["code"] >= 500 or r["code"] == 429) for r in reqs)
    print("  transient = 5xx or 429; permanent = other 4xx = %s" % transient_are_5xx_429)

    perm = [r for r in reqs if not is_transient(r["code"])]
    tran = [r for r in reqs if is_transient(r["code"])]

    blind = sum(attempts_blind(r, mr) for r in reqs)
    smart = sum(attempts_classify(r, mr) for r in reqs)

    classify_fewer_attempts = smart < blind
    print("  classify-first uses fewer total attempts = %s (%d < %d)" % (classify_fewer_attempts, smart, blind))

    permanent_not_retried = all(attempts_classify(r, mr) == 1 for r in perm)
    print("  classify-first does not retry any permanent error = %s (%d permanent)" % (permanent_not_retried, len(perm)))

    transient_still_retried = all(attempts_classify(r, mr) == 1 + mr for r in tran)
    print("  classify-first still retries every transient error = %s (%d transient)" % (transient_still_retried, len(tran)))

    saved = blind - smart
    saved_equals_wasted = saved == len(perm) * mr
    print("  the attempts saved equal the wasted retries on permanent errors = %s (%d)" % (saved_equals_wasted, saved))

    ok = (transient_are_5xx_429 and classify_fewer_attempts and permanent_not_retried
          and transient_still_retried and saved_equals_wasted)
    print("-" * 116)
    print("SELF-TEST %s  transient_are_5xx_429=%s  classify_fewer_attempts=%s  permanent_not_retried=%s  transient_still_retried=%s  saved_equals_wasted=%s"
          % ("PASS" if ok else "FAIL", transient_are_5xx_429, classify_fewer_attempts,
             permanent_not_retried, transient_still_retried, saved_equals_wasted))
    return ok


def main():
    p = argparse.ArgumentParser(description="Retry classification: classify a failure before retrying -- retry transient errors (5xx, 429, timeouts, connection errors) and fail fast on permanent ones (most 4xx) -- because retrying a permanent error yields the identical error every attempt, wasting the retry budget and the latency while never succeeding.")
    p.add_argument("--classify", action="store_true")
    p.add_argument("--attempts", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("requests=%d  max_retries=%d  file=%s  (the requests are a fixture)"
          % (len(data["requests"]), data["max_retries"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.classify:
        classify_view(data)
    elif args.attempts:
        attempts_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
