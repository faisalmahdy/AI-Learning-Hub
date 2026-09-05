---
id: teach-inter-04
title: "Ready" is derived from facts — never trust the status a module claims
topic: teaching-and-portability
level: intermediate
status: ready
time: 8-10h
summary: A module's status field is a claim its author set, and a claim is not evidence, so a portable knowledge artifact must let a reader derive readiness from checkable facts — sections present, self-test green, recall logged — and trust the derivation, never the claim. Across six modules, four claim ready but only three meet every criterion: two are overclaims (marked ready, one with a failing self-test, one with no recall log) and one is an underclaim (marked draft, meets all three), so the claimed and derived statuses disagree for half the modules and a dashboard reading the claimed field over-reports readiness by one. The derived count is the honest one because it is computed from facts the reader can verify, and the fix is to compute status, never to store it.
eli5: A sticker on a box that says "checked" means nothing unless someone actually checked. The honest way is to open the box and verify what is inside, and decide "ready" from that — not from the sticker. Some boxes have a "ready" sticker but fail the check, and some have a "not done" sticker but are actually fine. Trust the check, never the sticker.
---

## Why this module

The hub's entire method rests on one refusal: nothing is trusted because it says so. A number is real because a committed script printed it; a module is done because a build gate verified it; a concept is learned because a from-memory recall was logged. This module turns that refusal on the modules' own status fields. A module can carry `status: ready`, but that field is a claim its author typed, and this module builds the reader that ignores the claim and derives readiness from facts — because a knowledge artifact is only portable, only trustworthy to someone who did not write it, if its readiness can be checked rather than taken on faith.

The distinction is claimed status versus derived status. Claimed status is what the author wrote in the field. Derived status is computed from criteria a reader can verify independently: are all the required sections present, did the module's self-test pass, is there a dated recall log. Readiness is the second, never the first. The failure this prevents is a dashboard that counts the claimed field: it reports the authors' intentions rather than the state of the work, so it counts overclaims — modules marked ready that fail a criterion — as done, and misses underclaims — modules marked draft that quietly meet every criterion. The two counts disagree, and only the derived one is honest, because only it is grounded in facts. The fix is a principle: compute status from evidence, never store it as an assertion.

You need the recall-ledger and verification instincts from the earlier teaching modules and nothing more. Everything runs offline against a module manifest — six modules, each with a claimed status and three checkable facts — stdlib Python 3, `$0.00`. The instinct to unlearn is that a status field tells you the status. It tells you what the author claimed; the status is whatever the facts derive, and the two are different for half of these modules.

Here is the claim against the derivation:

```
# modules/teaching-and-portability/code/teach-inter-04/ — COMPLETE, run from that directory
$ python3 verify.py --derive

DERIVE — claimed status vs status derived from the facts
------------------------------------------------------------------
  mod-a   claimed=ready derived=ready
  mod-b   claimed=ready derived=draft  <-- MISMATCH  (fails: self_test_passes)
  mod-c   claimed=ready derived=draft  <-- MISMATCH  (fails: recall_logged)
  mod-d   claimed=draft derived=ready  <-- MISMATCH
  mod-e   claimed=draft derived=draft  (fails: sections_ok, recall_logged)
  mod-f   claimed=ready derived=ready
```

run: 2026-08-26 · deterministic; statuses and facts are a fixture · 6 modules · `python3 verify.py --derive`

Three of six modules have a claimed status that the facts contradict — two claiming ready they have not earned, one selling itself short. This module is why the derived column is the one to trust.

## Concepts

Named here so you can find them again; each is built below.

- **Claimed status** — the status field an author set; an assertion, not evidence.
- **Derived status** — readiness computed from checkable criteria; the trustworthy one.
- **Criteria** — the facts a reader can verify: sections present, self-test green, recall logged.
- **Overclaim** — marked ready while a criterion fails; readiness the facts do not support.
- **Underclaim** — marked draft while every criterion holds; done work the claim undersells.
- **Reader-derived trust** — a portable artifact lets its reader compute status, not take it on faith.

## Worked example

Source: the hub's own build-gate philosophy — `tools/build_site.py` derives whether the hub is sound from checkable facts rather than trusting any status field — generalized to a module manifest; the statuses and facts here stand in for a real module set so the overclaims and the count gap are exact and checkable.

Script and fixture: `modules/teaching-and-portability/code/teach-inter-04/` — `verify.py`, and `manifest.json`, six modules each with a claimed status and three facts. Every command runs from there.

### Deriving status from facts

Readiness is a conjunction: a module is ready only if every required criterion holds. Nothing about the claimed field enters.

```
# verify.py:39-45 — COMPLETE (status derived from criteria, not from the claim)
def derived_status(module, criteria):
    """READY only if every required criterion is true; otherwise draft. Facts, not claims."""
    return "ready" if all(module[c] for c in criteria) else "draft"


def failed_criteria(module, criteria):
    return [c for c in criteria if not module[c]]
```

<svg viewBox="0 0 700 160" role="img" aria-label="mod-b evaluated against three criteria. sections_ok is a check (true). self_test_passes is a cross (false). recall_logged is a check (true). Because one criterion is false, the AND gate outputs draft, even though the module claims ready.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">mod-b: claims ready — deriving its status from the three facts</text>
    <text x="60" y="52" fill="var(--s1)">sections_ok = true  OK</text>
    <text x="60" y="80" fill="var(--s2)">self_test_passes = false  X</text>
    <text x="60" y="108" fill="var(--s1)">recall_logged = true  OK</text>
    <path d="M 300 45 L 300 115 L 360 115 L 400 80 L 360 45 Z" fill="var(--panel)" stroke="var(--line)"></path>
    <text x="335" y="84" text-anchor="middle" fill="var(--ink)" font-size="8">AND</text>
    <line x1="300" y1="48" x2="240" y2="48" stroke="var(--muted)"></line><line x1="300" y1="80" x2="240" y2="80" stroke="var(--muted)"></line><line x1="300" y1="112" x2="240" y2="112" stroke="var(--muted)"></line>
    <line x1="400" y1="80" x2="470" y2="80" stroke="var(--s2)"></line>
    <rect x="470" y="66" width="120" height="28" rx="4" fill="var(--panel)" stroke="var(--s2)"></rect><text x="530" y="84" text-anchor="middle" fill="var(--s2)" font-size="8">derived = draft</text>
    <text x="300" y="140" fill="var(--muted)" font-size="8">one false input makes the conjunction false — the "ready" claim is overruled</text>
  </g>
</svg>
^ Readiness is a conjunction, so a single failing criterion — here the self-test — makes the derived status draft, whatever the claim says. The deriver never even looks at the claimed field.

The `all(module[c] for c in criteria)` is the whole definition of ready: sections present AND self-test green AND recall logged. If any one is false the module is draft, no matter what its status field says. Notice the function never reads `claimed_status` — it cannot, because the claim is exactly what we refuse to trust. The status is a computation over facts, and `failed_criteria` names precisely which fact is missing, so a mismatch is never a mystery: `mod-b` is draft because its self-test fails, full stop.

### The two ways a claim lies

A claim can be wrong in both directions, and both matter.

```
# verify.py:48-55 — COMPLETE (overclaimers and underclaimers)
def overclaimers(modules, criteria):
    """Marked ready, but a criterion fails -- claimed readiness the facts do not support."""
    return [m for m in modules if m["claimed_status"] == "ready" and derived_status(m, criteria) == "draft"]


def underclaimers(modules, criteria):
    """Marked draft, but every criterion holds -- done work the claim undersells."""
    return [m for m in modules if m["claimed_status"] == "draft" and derived_status(m, criteria) == "ready"]
```

Run the audit and both kinds surface:

```
# $ python3 verify.py --audit
#   OVERCLAIMERS (trust these at your peril):
#      mod-b   marked ready, fails: self_test_passes
#      mod-c   marked ready, fails: recall_logged
#   UNDERCLAIMERS (actually done, marked draft):
#      mod-d   marked draft, meets every criterion
```

run: 2026-08-26 · deterministic · `python3 verify.py --audit`

The overclaimers are the dangerous ones: `mod-b` and `mod-c` present themselves as ready and are not, so anyone trusting the claim inherits a broken self-test or an unverified concept. The underclaimer, `mod-d`, is the opposite error — real, finished work hidden behind a cautious label, which wastes effort if someone rebuilds what is already done. A claim is not merely optimistic; it is unreliable in both directions, and only the facts resolve which.

<svg viewBox="0 0 700 200" role="img" aria-label="A 2x2 grid. Rows: claimed ready, claimed draft. Columns: derived ready, derived draft. Claimed-ready/derived-ready holds mod-a and mod-f (honest). Claimed-ready/derived-draft holds mod-b and mod-c, marked overclaim. Claimed-draft/derived-ready holds mod-d, marked underclaim. Claimed-draft/derived-draft holds mod-e (honest). The two off-diagonal cells are the mismatches.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">claimed status (rows) vs derived status (columns)</text>
    <text x="250" y="44" text-anchor="middle" fill="var(--ink)">derived ready</text>
    <text x="470" y="44" text-anchor="middle" fill="var(--ink)">derived draft</text>
    <text x="70" y="80" fill="var(--ink)">claimed</text><text x="70" y="92" fill="var(--ink)">ready</text>
    <rect x="160" y="56" width="180" height="50" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="250" y="86" text-anchor="middle" fill="var(--acc-ink)">mod-a, mod-f (honest)</text>
    <rect x="380" y="56" width="180" height="50" fill="var(--panel)" stroke="var(--s2)"></rect><text x="470" y="80" text-anchor="middle" fill="var(--s2)">mod-b, mod-c</text><text x="470" y="94" text-anchor="middle" fill="var(--s2)" font-size="8">OVERCLAIM</text>
    <text x="70" y="140" fill="var(--ink)">claimed</text><text x="70" y="152" fill="var(--ink)">draft</text>
    <rect x="160" y="116" width="180" height="50" fill="var(--panel)" stroke="var(--s1)"></rect><text x="250" y="140" text-anchor="middle" fill="var(--s1)">mod-d</text><text x="250" y="154" text-anchor="middle" fill="var(--s1)" font-size="8">UNDERCLAIM</text>
    <rect x="380" y="116" width="180" height="50" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="470" y="146" text-anchor="middle" fill="var(--acc-ink)">mod-e (honest)</text>
    <text x="160" y="188" fill="var(--muted)" font-size="8">the diagonal is honest; the off-diagonal cells are where the claim lies</text>
  </g>
</svg>
^ On the diagonal the claim and the facts agree. Off the diagonal the claim lies — overclaim in one corner, underclaim in the other. A system that reads the claimed field cannot tell which cell a module is in; only deriving from facts places it.

### The dashboard bug: counting claims

Now the failure. A readiness dashboard that counts the claimed field reports optimism, not reality.

```
# $ python3 verify.py --count
#   claimed ready = 4  ['mod-a', 'mod-b', 'mod-c', 'mod-f']
#   derived ready = 3  ['mod-a', 'mod-d', 'mod-f']
```

run: 2026-08-26 · deterministic · `python3 verify.py --count`

<svg viewBox="0 0 700 165" role="img" aria-label="Two rows of module chips. Claimed ready: mod-a, mod-b, mod-c, mod-f (four). Derived ready: mod-a, mod-d, mod-f (three). mod-b and mod-c appear only in the claimed row (false), mod-d only in the derived row (missed), and mod-a and mod-f in both.">
  <g font-family="var(--mono)" font-size="8">
    <text x="20" y="16" fill="var(--muted)">who is 'ready' — claimed set vs derived set (not even nested)</text>
    <text x="20" y="52" fill="var(--ink)" font-size="9">claimed (4)</text>
    <g fill="var(--acc-soft)" stroke="var(--acc-line)"><rect x="150" y="38" width="70" height="22" rx="4"></rect><rect x="380" y="38" width="70" height="22" rx="4"></rect></g>
    <g fill="var(--panel)" stroke="var(--s2)"><rect x="228" y="38" width="70" height="22" rx="4"></rect><rect x="306" y="38" width="70" height="22" rx="4"></rect></g>
    <g text-anchor="middle"><text x="185" y="53" fill="var(--acc-ink)">mod-a</text><text x="263" y="53" fill="var(--s2)">mod-b</text><text x="341" y="53" fill="var(--s2)">mod-c</text><text x="415" y="53" fill="var(--acc-ink)">mod-f</text></g>
    <text x="470" y="53" fill="var(--s2)">b,c are false</text>
    <text x="20" y="108" fill="var(--ink)" font-size="9">derived (3)</text>
    <g fill="var(--acc-soft)" stroke="var(--acc-line)"><rect x="150" y="94" width="70" height="22" rx="4"></rect><rect x="380" y="94" width="70" height="22" rx="4"></rect></g>
    <rect x="228" y="94" width="70" height="22" rx="4" fill="var(--panel)" stroke="var(--s1)"></rect>
    <g text-anchor="middle"><text x="185" y="109" fill="var(--acc-ink)">mod-a</text><text x="263" y="109" fill="var(--s1)">mod-d</text><text x="415" y="109" fill="var(--acc-ink)">mod-f</text></g>
    <text x="470" y="109" fill="var(--s1)">d was missed</text>
    <text x="150" y="145" fill="var(--muted)">the claim adds two it should not and drops one it should keep — wrong by three, not one</text>
  </g>
</svg>
^ Only `mod-a` and `mod-f` are in both sets. The claim adds `mod-b` and `mod-c` (not actually ready) and omits `mod-d` (actually ready), so it is wrong about three modules while the counts differ by only one.

The claimed count is 4, the derived count is 3 — and note the sets are not even nested: claimed-ready is `{a, b, c, f}`, derived-ready is `{a, d, f}`. The claim both adds modules that are not ready (`b`, `c`) and omits one that is (`d`). A dashboard trusting the claim over-reports the total by one and gets the membership wrong by three, so it is not merely inflated, it is pointing at the wrong modules. If you shipped based on "4 ready", two of your four would be broken and a finished one would sit unshipped. The derived count is the only one that corresponds to reality.

**A status field is a claim, and a claim is not evidence, so readiness must be derived from criteria a reader can verify — a system that counts the claimed field over-reports readiness and names the wrong modules, while the derived status, computed from facts, is the only trustworthy one.**

### The self-test

The `--check` mode asserts the whole argument: claim and facts disagree, overclaimers and underclaimers both exist, the derivation is sound, and the claimed count over-reports.

```
# $ python3 verify.py --check
#   claimed and derived status disagree for some module = True (3 modules)
#   overclaimers exist (ready but fail a criterion) = True (['mod-b', 'mod-c'])
#   underclaimers exist (draft but meet all) = True (['mod-d'])
#   every derived-ready module passes all criteria = True
#   claimed-ready count over-reports the derived count = True (4 > 3)
#   SELF-TEST PASS ...
```

run: 2026-08-26 · deterministic · `python3 verify.py --check`

The two structural assertions are the derivation's own proof and the dashboard bug, side by side:

```
# verify.py:123-129 — COMPLETE (the derivation is sound; the claimed count over-reports)
    derived_ready = [m for m in mods if derived_status(m, crit) == "ready"]
    all_derived_valid = all(all(m[c] for c in crit) for m in derived_ready)

    claimed_n = sum(1 for m in mods if m["claimed_status"] == "ready")
    over_reports = claimed_n > len(derived_ready)
```

The `derivation_sound` line is the correctness anchor: every module the deriver calls ready must, on independent re-check, pass all criteria — a proof the derivation is not itself trusting something it should not. The `over_reports` line encodes the lesson as a guardrail, requiring the claimed count to exceed the derived count, so the module cannot pretend the claimed field is harmless. Both overclaim and underclaim assertions must fire, so the test proves the claim is unreliable in both directions, not merely optimistic.

### The running tally

| source of "ready" | count | members | trustworthy |
|---|---|---|---|
| claimed field | 4 | mod-a, mod-b, mod-c, mod-f | no — 2 overclaims, misses mod-d |
| derived from facts | 3 | mod-a, mod-d, mod-f | yes — every criterion checked |

The two rows are the same six modules read two ways. The claimed row is what the authors said; the derived row is what is true. They differ by more than a count — they disagree on which modules are ready, because the claim is uncorrelated with the facts wherever an author was optimistic or cautious. This is the hub's build gate in miniature: `build_site.py` never trusts a `status` field to decide whether the hub is sound; it derives soundness from checkable facts and reports that. Store facts, derive status, and never let a claim stand in for a check.

### What we did not settle

Derivation is only as honest as its criteria and its facts. The criteria must be complete — a module that passes all three checks here could still be pedagogically weak, since "sections present, self-test green, recall logged" does not measure clarity, so the derived "ready" is necessary, not sufficient. The facts themselves must be trustworthy: `self_test_passes` should come from actually running the self-test, not from another claimed field, or you have just moved the trust problem down a level. This is why the hub's gate runs the checks itself rather than reading a cached result. And criteria evolve — adding a new required check reclassifies modules, which is correct: readiness is relative to the current bar. The principle here — derive from facts, never trust a claim — is the floor; picking criteria that actually capture readiness is the ongoing work.

## Build

The practice in one paragraph: never let a status field decide anything; define the criteria that actually constitute "ready", compute each fact by checking it yourself rather than reading a cached claim, and derive status as the conjunction; report the derived count and the specific failed criteria, so a mismatch is diagnosable; and audit for both overclaims and underclaims, because a claim is unreliable in both directions. A portable artifact is one whose readiness its reader can recompute from scratch.

We opened on the derivation. The number that shows the claim cannot be trusted is the count gap:

```
# modules/teaching-and-portability/code/teach-inter-04/ — COMPLETE, run from that directory
$ python3 verify.py --count
  claimed ready = 4  ['mod-a', 'mod-b', 'mod-c', 'mod-f']
  derived ready = 3  ['mod-a', 'mod-d', 'mod-f']
```

Now do it to your own artifacts. Take a set of documents, modules, or tasks with a status field, define the criteria that truly constitute done, and derive each one's status from the facts — checked, not claimed. Your number to beat is not how many claim ready; it is **the count of overclaimers, modules marked ready that fail a criterion**, because those are the ones a reader would be burned by. Then find the underclaimers too. Bring back the claimed and derived counts and the overclaimer list. Good luck.

## Definition of done

- [ ] A set of criteria that actually constitute "ready", each independently checkable
- [ ] Status derived as the conjunction of the criteria, ignoring any claimed field
- [ ] The specific failed criteria named for every not-ready module
- [ ] Overclaimers (claimed ready, fail a criterion) and underclaimers (claimed draft, meet all) audited
- [ ] The claimed-ready count compared to the derived-ready count, and the membership gap shown
- [ ] Facts computed by checking, not by reading another cached claim
- [ ] `python3 verify.py --check` printing SELF-TEST PASS: disagree, overclaims, underclaims, derivation-sound, over-reports
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. What is the difference between claimed status and derived status, and why is only one trustworthy?
2. A claim can be wrong in two directions. Name them, and explain why the overclaim is the more dangerous.
3. The claimed and derived ready-sets were not nested. Why does that make a claim-reading dashboard worse than merely inflated?
4. Why must the facts themselves be computed by checking rather than read from another field?
5. Your own artifacts were audited. How many overclaimers did you find, and what was the gap between the claimed and derived ready counts?

## External resources

- The hub, *tools/build_site.py* — my summary: the build gate that derives whether the hub is sound from checkable facts (sections, links, ledger schema) rather than trusting any status field; read it for the working implementation of this module's principle.
- Trust-but-verify / provenance writing (e.g. reproducible-build and supply-chain trust models) — my summary: the general pattern of deriving trust from verifiable evidence rather than asserted labels; read it for the same principle applied to software artifacts and why a signed claim still needs a checkable fact behind it.
- This hub, *teach-inter-03* — modules/teaching-and-portability/teach-inter-03.md — my summary: the calibration module where a learner's self-rated confidence overshoots actual recall; read it for the same lesson one level up — a self-report (of confidence, or of status) is a claim, and only a check derives the truth.
