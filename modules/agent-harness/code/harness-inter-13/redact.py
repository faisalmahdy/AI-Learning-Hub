"""Redact secrets from tool output before it enters the context -- and use both known values and patterns.

A tool returns a chunk of text -- an error message, an API response, a log tail -- and the harness appends
it to the conversation so the model can reason about it. If that text contains a secret (an API key echoed
in an error, a password in a connection string), the secret is now in the context window: it will be sent
to the model, written to any transcript, folded into every later summary, and can be repeated verbatim in
an answer. Tool output must be scrubbed before it is appended, not after, because after is too late -- the
secret has already been distributed.

There are two ways to scrub, and each alone has a hole. Pattern redaction matches known secret shapes with
regexes (an OpenAI key looks like sk-..., a GitHub token like ghp_...). It catches anything of a recognized
shape, including secrets the harness has never seen -- but it misses a secret of an unusual shape, like a
database password that is just a random string matching no pattern. Value redaction replaces the exact
secret strings the harness knows it holds (the ones it injected as env vars). It catches those regardless
of shape -- but it misses a secret the harness does not know, like a token the tool itself generated. Rely
on patterns alone and the odd-shaped known secret leaks; rely on known values alone and the unknown-but-
recognizable secret leaks. The fix is both: scrub the exact values you hold AND the shapes you recognize,
so each covers the other's blind spot.

On this fixture the tool output carries three secrets: a known API key (matches a pattern), a known DB
password (matches no pattern), and an unknown GitHub token the tool generated (matches a pattern, but the
harness never held it). Pattern-only redaction leaks the DB password; value-only redaction leaks the GitHub
token; using both leaks nothing. This computes all three.

  --output     the raw tool output and what each redaction strategy produces
  --leaks      which of the three secrets survives each strategy
  --check      each strategy alone leaks a secret; combining exact values and patterns leaks none

The tool output, known secrets, and patterns are the fixture; every redaction is computed. Stdlib only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "output.json"

MASK = "[REDACTED]"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def redact_values(text, known):
    """Replace each exact secret the harness holds -- catches any shape, misses unknown secrets."""
    for secret in known:
        text = text.replace(secret, MASK)
    return text


def redact_patterns(text, patterns):
    """Replace anything matching a known secret shape -- catches unknown secrets, misses odd shapes."""
    for pat in patterns:
        text = re.sub(pat, MASK, text)
    return text


def redact_combined(text, known, patterns):
    """Scrub exact known values first, then patterns -- each covers the other's blind spot."""
    return redact_patterns(redact_values(text, known), patterns)


def leaked(text, all_secrets):
    """Which ground-truth secrets still appear in the (supposedly redacted) text."""
    return [s for s in all_secrets if s in text]


# ----------------------------------------------------------------- printing

def output_view(data):
    out, known, pats = data["tool_output"], data["known_secrets"], data["patterns"]
    print("OUTPUT — the raw tool output and each redaction")
    print("-" * 62)
    print("  raw:       %s" % out)
    print("  values:    %s" % redact_values(out, known))
    print("  patterns:  %s" % redact_patterns(out, pats))
    print("  combined:  %s" % redact_combined(out, known, pats))
    print("-" * 62)
    print("  the combined redaction is the only one with no secret left.")


def leaks_view(data):
    out, known, pats, alls = data["tool_output"], data["known_secrets"], data["patterns"], data["all_secrets"]
    print("LEAKS — which secrets survive each strategy")
    print("-" * 62)
    for name, red in (("values-only", redact_values(out, known)),
                      ("patterns-only", redact_patterns(out, pats)),
                      ("combined", redact_combined(out, known, pats))):
        lk = leaked(red, alls)
        print("  %-14s leaks %d: %s" % (name, len(lk), lk or "none"))
    print("-" * 62)
    print("  each single strategy leaks one secret; combined leaks none.")


def check(data):
    print("SELF-TEST — each strategy alone leaks a secret; combining exact values and patterns leaks none")
    print("-" * 96)
    out, known, pats, alls = data["tool_output"], data["known_secrets"], data["patterns"], data["all_secrets"]
    val_leak = leaked(redact_values(out, known), alls)
    pat_leak = leaked(redact_patterns(out, pats), alls)
    both_leak = leaked(redact_combined(out, known, pats), alls)

    patterns_miss_oddshape = len(pat_leak) > 0
    print("  pattern-only leaks an odd-shaped known secret = %s (%s)" % (patterns_miss_oddshape, pat_leak))

    values_miss_unknown = len(val_leak) > 0
    print("  value-only leaks an unknown-but-recognizable secret = %s (%s)" % (values_miss_unknown, val_leak))

    combined_clean = len(both_leak) == 0
    print("  combined leaks nothing = %s (%s)" % (combined_clean, both_leak or "none"))

    combined_beats_each = len(both_leak) < len(pat_leak) and len(both_leak) < len(val_leak)
    print("  combined beats each strategy alone = %s (%d vs %d, %d)" % (combined_beats_each, len(both_leak), len(pat_leak), len(val_leak)))

    each_alone_insufficient = pat_leak != val_leak and len(pat_leak) > 0 and len(val_leak) > 0
    print("  the two strategies miss different secrets = %s (%s vs %s)" % (each_alone_insufficient, pat_leak, val_leak))

    ok = patterns_miss_oddshape and values_miss_unknown and combined_clean and combined_beats_each and each_alone_insufficient
    print("-" * 96)
    print("SELF-TEST %s  patterns_miss_oddshape=%s  values_miss_unknown=%s  combined_clean=%s  combined_beats_each=%s  each_alone_insufficient=%s"
          % ("PASS" if ok else "FAIL", patterns_miss_oddshape, values_miss_unknown, combined_clean, combined_beats_each, each_alone_insufficient))
    return ok


def main():
    p = argparse.ArgumentParser(description="Redact secrets from tool output using both exact known values and patterns.")
    p.add_argument("--output", action="store_true")
    p.add_argument("--leaks", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("secrets=%d  known=%d  patterns=%d  file=%s  (the output and secrets are a fixture)"
          % (len(data["all_secrets"]), len(data["known_secrets"]), len(data["patterns"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.output:
        output_view(data)
    elif args.leaks:
        leaks_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
