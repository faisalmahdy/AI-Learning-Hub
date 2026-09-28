---
id: harness-inter-13
title: Redact secrets from tool output before it enters the context — and use both known values and patterns
topic: agent-harness
level: intermediate
status: ready
time: 21 min
summary: Tool output is appended to the conversation, so a secret in it — an API key echoed in an error, a password in a connection string — is now in the context, every later summary, and any transcript. Scrubbing must happen before the append. Two strategies each have a hole: pattern redaction misses an odd-shaped secret, exact-value redaction misses an unknown one. On output carrying a known API key, an odd-shaped known DB password, and an unknown GitHub token, pattern-only leaks the password, value-only leaks the token, and combining both leaks nothing.
eli5: If you photocopy a page that has a password on it, the password is now on every copy — you can't un-print it. So you black it out before copying, not after. And blacking out only the words you already know misses a secret you didn't know was there, while blacking out anything that "looks like" a password misses one written in an odd way. Do both.
---

## Why this module

A secret that reaches the context window has already been distributed, so the only safe place to remove it is before it is appended, and one redaction strategy is not enough.

An agent's tools return text — an error message, an API response, a log tail — and the harness appends that text to the conversation so the model can reason about it. This is normal and necessary. The danger is that tool output is not always clean: an error might echo the API key it failed to authenticate with, a connection string might carry a password, a log line might print a token. The moment that text is appended, the secret is in the context window, and the context window goes everywhere — it is sent to the model on every subsequent turn, written into any saved transcript, folded into every later summarization of the conversation, and available to be repeated verbatim in an answer.

That is why scrubbing has to happen before the append, not after. Redacting the context once a secret is already in it is closing the barn door — the secret may already have been sent upstream, logged, or summarized into a form you cannot easily find and remove. The tool-output boundary is the one chokepoint where the secret is present in exactly one place and has not yet spread; scrubbing there is the difference between a secret that never entered the record and one you are now trying to chase down across transcripts and summaries.

There are two ways to scrub, and each alone has a blind spot. Pattern redaction matches known secret shapes with regexes — an OpenAI key looks like `sk-…`, a GitHub token like `ghp_…` — and replaces anything of a recognized shape. It catches secrets the harness has never seen, as long as they match a known shape, but it misses a secret of an unusual shape, like a database password that is just a random string fitting no pattern. Value redaction replaces the exact secret strings the harness holds — the ones it injected as environment variables — and catches those whatever they look like, but it misses a secret the harness never held, like a token the tool itself generated.

The fix is to use both. On the fixture the tool output carries three secrets: a known API key (matches a pattern), a known DB password (matches no pattern), and an unknown GitHub token the tool generated (matches a pattern, but the harness never held it). Pattern-only redaction leaks the DB password; value-only redaction leaks the GitHub token; using both leaks nothing.

**A secret in tool output enters the whole context — model, transcript, summaries — so it must be scrubbed before the append; pattern redaction misses odd-shaped secrets and exact-value redaction misses unknown ones, so combine them and each covers the other's blind spot.**

## Concepts

<svg role="img" aria-label="Two overlapping circles: value redaction covers known secrets, pattern redaction covers recognized shapes; only their union covers the three secrets, with the unknown-and-odd corner left outside both" viewBox="0 0 470 190" width="470" height="190">
  <rect x="0" y="0" width="470" height="190" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">what each strategy covers (secrets fall in the circles)</text>
  <circle cx="180" cy="105" r="75" fill="var(--acc-soft)" opacity="0.4" stroke="var(--acc-line)"/>
  <circle cx="290" cy="105" r="75" fill="var(--s1)" opacity="0.2" stroke="var(--s1)"/>
  <text x="120" y="40" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">values: known, any shape</text>
  <text x="300" y="40" font-family="var(--mono)" font-size="8" fill="var(--s1)">patterns: recognized shapes</text>
  <text x="120" y="110" font-family="var(--mono)" font-size="8" fill="var(--ink)">DB pw</text>
  <text x="112" y="122" font-family="var(--mono)" font-size="7" fill="var(--muted)">known, odd</text>
  <text x="315" y="110" font-family="var(--mono)" font-size="8" fill="var(--ink)">gh token</text>
  <text x="315" y="122" font-family="var(--mono)" font-size="7" fill="var(--muted)">unknown, shaped</text>
  <text x="215" y="105" font-family="var(--mono)" font-size="8" fill="var(--ink)">API key</text>
  <text x="380" y="165" font-family="var(--mono)" font-size="8" fill="var(--s2)">unknown + odd → outside both</text>
</svg>
^ The API key sits in the overlap (known and shaped); the DB password only value redaction covers, the GitHub token only patterns cover — and an unknown, odd-shaped secret falls outside both circles, the residual risk.

The two redaction strategies fail on opposite axes, which is exactly why they compose. Value redaction is anchored to identity: it knows the literal secret strings the harness holds and removes those, so it is perfect for any secret the harness injected — an API key, a database password, a signing secret — regardless of how weird the string looks, because it matches the exact bytes. Its blind spot is anything the harness does not know it holds: a token the tool generated at runtime, a credential embedded in a third-party response, a secret from a system the harness never configured. It cannot redact what it was never told about.

Pattern redaction is anchored to shape: it knows what classes of secret look like and removes anything matching, so it catches secrets the harness never held — the runtime token, the third-party credential — as long as they fit a recognized format. Its blind spot is the odd shape: a secret that does not match any pattern sails through. Database passwords are the classic case, because a password can be any random string and there is no reliable regex for "this looks like a password." So pattern redaction is strong exactly where value redaction is weak (unknown secrets) and weak exactly where value redaction is strong (odd-shaped known secrets).

Because the blind spots are complementary, the union catches both. Scrub the exact known values first, then run the patterns over what remains: the known secrets are gone by identity regardless of shape, and any unknown secret of a recognized shape is gone by pattern. What is left uncaught is only the intersection of the two blind spots — an unknown secret of an unrecognized shape — which is genuinely hard for any redactor and is where you accept residual risk and add other controls (never logging raw tool output, minimizing what secrets tools can see at all). The point is that neither strategy alone even approaches that residual; each alone leaves an easy, common category of secret exposed.

This is a specific instance of a general security principle: layered defenses whose weaknesses do not overlap. A single filter has a single failure mode, and an attacker (or just bad luck) finds it; two filters chosen so that each catches what the other misses shrink the exposed surface to their intersection. The redaction belongs at the tool-output boundary specifically because that is the trust boundary — data crossing from the tool into the model's context — and trust boundaries are where scrubbing, validation, and encoding all belong. Treating tool output as untrusted (it may contain secrets, it may contain injection, it may be malformed) and cleaning it at the boundary is the harness's job, and secret redaction is one of the cleanings.

**Value redaction catches known secrets of any shape but misses unknown ones; pattern redaction catches recognized shapes including unknown secrets but misses odd shapes — complementary blind spots, so their union leaves only the rare unknown-and-odd secret, which is why the boundary scrub uses both.**

## Worked example

The fixture is a line of tool output, the secrets the harness knows, the shape patterns, and the ground-truth list of every secret present.

```json filename=modules/agent-harness/code/harness-inter-13/output.json:3-6 COMPLETE
  "tool_output": "connect failed: api_key=sk-live-abc123 password=db_pw_9f3k2j token=ghp_XYZ789tokenABC host=db1",
  "known_secrets": ["sk-live-abc123", "db_pw_9f3k2j"],
  "patterns": ["sk-[a-z0-9-]+", "ghp_[A-Za-z0-9]+"],
  "all_secrets": ["sk-live-abc123", "db_pw_9f3k2j", "ghp_XYZ789tokenABC"]
```

Three secrets in the output. The API key and DB password are known to the harness; the GitHub token was generated by the tool and is unknown. The patterns recognize `sk-` and `ghp_` shapes — so they cover the API key and the GitHub token, but not the password. Value redaction replaces exact known strings; pattern redaction replaces recognized shapes.

```python filename=modules/agent-harness/code/harness-inter-13/redact.py:47-58 COMPLETE
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
```

The combined strategy runs both — exact values first, then patterns over the remainder.

```python filename=modules/agent-harness/code/harness-inter-13/redact.py:61-68 COMPLETE
def redact_combined(text, known, patterns):
    """Scrub exact known values first, then patterns -- each covers the other's blind spot."""
    return redact_patterns(redact_values(text, known), patterns)


def leaked(text, all_secrets):
    """Which ground-truth secrets still appear in the (supposedly redacted) text."""
    return [s for s in all_secrets if s in text]
```

Predict: value-only redaction masks the API key and password (both known) but leaves the GitHub token; pattern-only masks the API key and GitHub token (both recognized shapes) but leaves the password; combined masks all three. Run it.

```text filename=modules/agent-harness/code/harness-inter-13/redact.py --output
OUTPUT — the raw tool output and each redaction
--------------------------------------------------------------
  raw:       connect failed: api_key=sk-live-abc123 password=db_pw_9f3k2j token=ghp_XYZ789tokenABC host=db1
  values:    connect failed: api_key=[REDACTED] password=[REDACTED] token=ghp_XYZ789tokenABC host=db1
  patterns:  connect failed: api_key=[REDACTED] password=db_pw_9f3k2j token=[REDACTED] host=db1
  combined:  connect failed: api_key=[REDACTED] password=[REDACTED] token=[REDACTED] host=db1
```

The value row still shows `ghp_XYZ789tokenABC` — the harness never held that token, so it had nothing to match. The pattern row still shows `db_pw_9f3k2j` — a password matches no shape, so no regex caught it. Each strategy masks two of three secrets and leaks the one in its blind spot. The combined row is clean: exact-value scrubbing removed the two known secrets, pattern scrubbing removed the recognizable unknown one, and nothing is left. Same output, three strategies, one that works.

<svg role="img" aria-label="A three-by-three grid showing which of three secrets each strategy redacts: values catches known two, patterns catches shaped two, combined catches all three" viewBox="0 0 470 195" width="470" height="195">
  <rect x="0" y="0" width="470" height="195" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">does the strategy redact each secret? (check = safe)</text>
  <text x="150" y="46" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">API key</text>
  <text x="235" y="46" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">DB pw</text>
  <text x="235" y="56" font-family="var(--mono)" font-size="7" fill="var(--muted)">(odd shape)</text>
  <text x="320" y="46" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">gh token</text>
  <text x="320" y="56" font-family="var(--mono)" font-size="7" fill="var(--muted)">(unknown)</text>
  <text x="20" y="90" font-family="var(--mono)" font-size="9" fill="var(--ink)">values</text>
  <text x="160" y="90" font-family="var(--mono)" font-size="12" fill="var(--acc-line)">OK</text>
  <text x="242" y="90" font-family="var(--mono)" font-size="12" fill="var(--acc-line)">OK</text>
  <text x="322" y="90" font-family="var(--mono)" font-size="11" fill="var(--s2)">LEAK</text>
  <text x="20" y="125" font-family="var(--mono)" font-size="9" fill="var(--ink)">patterns</text>
  <text x="160" y="125" font-family="var(--mono)" font-size="12" fill="var(--acc-line)">OK</text>
  <text x="242" y="125" font-family="var(--mono)" font-size="11" fill="var(--s2)">LEAK</text>
  <text x="322" y="125" font-family="var(--mono)" font-size="12" fill="var(--acc-line)">OK</text>
  <text x="20" y="160" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">combined</text>
  <text x="160" y="160" font-family="var(--mono)" font-size="12" fill="var(--acc-line)">OK</text>
  <text x="242" y="160" font-family="var(--mono)" font-size="12" fill="var(--acc-line)">OK</text>
  <text x="322" y="160" font-family="var(--mono)" font-size="12" fill="var(--acc-line)">OK</text>
</svg>
^ Values misses the unknown token, patterns misses the odd-shaped password — each leaks one — and only the combined row redacts all three, because the two blind spots do not overlap.

## Build

Reproduce the redactions. Pure standard library — `str.replace` for values, `re.sub` for patterns — so the leak of each strategy comes out exactly.

Run `--output` for the redacted text, `--leaks` for which secret survives each strategy, `--check` for the gate. The leak count comes from scanning the redacted text for any ground-truth secret still present.

```text filename=modules/agent-harness/code/harness-inter-13/redact.py --leaks
LEAKS — which secrets survive each strategy
--------------------------------------------------------------
  values-only    leaks 1: ['ghp_XYZ789tokenABC']
  patterns-only  leaks 1: ['db_pw_9f3k2j']
  combined       leaks 0: none
--------------------------------------------------------------
  each single strategy leaks one secret; combined leaks none.
```

The leak scan is one helper that scans the redacted text for any ground-truth secret still present — the honest scorer that does not trust the redaction to have worked.

```python filename=modules/agent-harness/code/harness-inter-13/redact.py:66-68 COMPLETE
def leaked(text, all_secrets):
    """Which ground-truth secrets still appear in the (supposedly redacted) text."""
    return [s for s in all_secrets if s in text]
```

<svg role="img" aria-label="Bar chart of secrets leaked: values-only 1, patterns-only 1, combined 0" viewBox="0 0 470 155" width="470" height="155">
  <rect x="0" y="0" width="470" height="155" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="18" font-family="var(--mono)" font-size="10" fill="var(--muted)">secrets that reach the context (of 3) — lower is safer</text>
  <line x1="40" y1="120" x2="450" y2="120" stroke="var(--line)"/>
  <rect x="70" y="78" width="80" height="42" fill="var(--s2)"/>
  <text x="80" y="135" font-family="var(--mono)" font-size="8" fill="var(--muted)">values: 1</text>
  <text x="78" y="72" font-family="var(--mono)" font-size="7" fill="var(--s2)">gh token</text>
  <rect x="200" y="78" width="80" height="42" fill="var(--s2)"/>
  <text x="210" y="135" font-family="var(--mono)" font-size="8" fill="var(--muted)">patterns: 1</text>
  <text x="212" y="72" font-family="var(--mono)" font-size="7" fill="var(--s2)">DB pw</text>
  <rect x="330" y="116" width="80" height="4" fill="var(--acc-line)"/>
  <text x="340" y="135" font-family="var(--mono)" font-size="8" fill="var(--acc-ink)">combined: 0</text>
</svg>
^ Each single strategy lets one secret through; only the combined redaction reaches zero — and the two leaked secrets are different ones, which is why the union closes both gaps.

The self-test pins both single-strategy leaks, the clean combined result, and — the important structural fact — that the two strategies miss different secrets, which is why combining them helps.

```python filename=modules/agent-harness/code/harness-inter-13/redact.py:106-109 COMPLETE
    patterns_miss_oddshape = len(pat_leak) > 0
    print("  pattern-only leaks an odd-shaped known secret = %s (%s)" % (patterns_miss_oddshape, pat_leak))

    values_miss_unknown = len(val_leak) > 0
    print("  value-only leaks an unknown-but-recognizable secret = %s (%s)" % (values_miss_unknown, val_leak))
```

```text filename=modules/agent-harness/code/harness-inter-13/redact.py --check
SELF-TEST — each strategy alone leaks a secret; combining exact values and patterns leaks none
------------------------------------------------------------------------------------------------
  pattern-only leaks an odd-shaped known secret = True (['db_pw_9f3k2j'])
  value-only leaks an unknown-but-recognizable secret = True (['ghp_XYZ789tokenABC'])
  combined leaks nothing = True (none)
  combined beats each strategy alone = True (0 vs 1, 1)
  the two strategies miss different secrets = True (['db_pw_9f3k2j'] vs ['ghp_XYZ789tokenABC'])
------------------------------------------------------------------------------------------------
SELF-TEST PASS  patterns_miss_oddshape=True  values_miss_unknown=True  combined_clean=True  combined_beats_each=True  each_alone_insufficient=True
```

Five True flags. Patterns_miss_oddshape: pattern-only leaves the odd-shaped password. Values_miss_unknown: value-only leaves the unknown token. Combined_clean: using both leaves nothing. Combined_beats_each: 0 leaks versus 1 and 1. Each_alone_insufficient: the two leak different secrets — the structural reason the union works. The last flag is the crux: if both strategies missed the same secret, combining them would not help; they help precisely because their blind spots are disjoint.

**The each-alone-insufficient flag is the argument for layering — the two strategies leak different secrets, so their union closes both gaps, and a single redactor of either kind leaves an easy, common class of secret in the context.**

## Definition of done

You are done when you reproduce the two single-strategy leaks and the clean combination, and can explain why they are complementary.

Concretely: `--output` shows value redaction leaving the GitHub token and pattern redaction leaving the DB password, with combined masking all three; `--leaks` shows 1, 1, 0 leaks; `--check` prints PASS with five True flags. You can explain that scrubbing must happen at the tool-output boundary because a secret in the context has already spread to the model, transcript, and summaries; that value redaction catches known secrets of any shape but misses unknown ones; that pattern redaction catches recognized shapes including unknown secrets but misses odd shapes; and that their union leaves only the rare unknown-and-odd secret.

The habit to carry: scrub tool output at the boundary, before appending, with both an exact-value pass over the secrets the harness holds and a pattern pass over recognized secret shapes. When a secret shows up in a transcript, a summary, or a model answer, the failure was almost always a missing or single-strategy redaction at the tool-output boundary — and remember that the boundary is also where you handle injection and malformed output, because tool output is untrusted data in general.

## Boss fight

The instructive failure is an agent that pastes a database password into its final answer.

An agent runs a tool that fails to connect and returns the error verbatim, including the connection string with the password. The harness redacts tool output with a regex list — API keys, cloud tokens, the usual shapes — so the logs look clean in testing. But the database password is a random string matching no pattern, so it flows into the context, and three turns later the agent, summarizing what went wrong, quotes the error and the password lands in the user-visible answer and the saved transcript. The regex list was never going to catch a passwords-are-arbitrary secret. The fix is to add exact-value redaction for every secret the harness injected (it knows the DB password — it set it), so the password is masked by identity regardless of shape, with the pattern list kept as defense against unknown-but-shaped secrets.

Your turn, two moves. First, probe the residual risk. Add a fourth secret that is both unknown to the harness and of an odd shape, and confirm even the combined redactor leaks it — the intersection of the two blind spots — then note the real mitigations for that case (do not log raw tool output, minimize which secrets a tool can see). Second, test an evasion: split a known secret across the output with a space or newline in the middle and confirm exact-value redaction misses it (the bytes no longer match), which is why production redactors also normalize whitespace and scan for secrets before and after common encodings — a reminder that boundary scrubbing is necessary but not a complete defense on its own.

## External resources

Guidance on secret handling in logs and telemetry (OWASP's logging cheat sheet, cloud-provider secret-scanning docs) makes the same core point — scrub secrets at the boundary before they are written or transmitted, because removal after distribution is unreliable.

GitHub's and GitGuardian's secret-scanning pattern libraries show the shape-based half of this in production: large curated regex sets for known credential formats, and their documentation is candid that pattern coverage is necessarily incomplete.

Any treatment of defense in depth and layered controls (the security-engineering literature) is the general principle behind combining strategies whose weaknesses do not overlap, which is exactly why exact-value and pattern redaction are used together rather than either alone.
