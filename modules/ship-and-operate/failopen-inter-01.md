---
id: failopen-inter-01
title: Choose fail-open vs fail-closed per check — a security check must deny when its service is down, a cosmetic one must allow
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: Every request runs through checks that call other services — an authorization check asks an auth service if the user may proceed, a rate limiter asks if the user is within quota, a personalization step asks an enrichment service for extras — and each of those calls can fail. The design must answer one question for each: when the check cannot run, does the request proceed or stop? "Fail open" proceeds as if the check passed; "fail closed" treats the failure as a rejection. The instinct is to pick one and apply it everywhere, but the correct choice is opposite for the two kinds of check. A security or safety check exists precisely to deny — if it cannot run, allowing the request defeats its purpose, so it must fail closed; let authorization fail open and an outage of the auth service becomes an authorization bypass. A non-critical enrichment exists only to make the response nicer — if it cannot run, the request is still valid, so it must fail open; let recommendations fail closed and an outage of a cosmetic service takes down the whole page. That is why a single blanket rule is wrong: blanket fail-open sacrifices the critical checks during their outage (an availability-first default that quietly disables the guards), and blanket fail-closed sacrifices availability during a non-critical outage. Only a deliberate per-check policy — critical fails closed, non-critical fails open — is right for both. On a fixture of two critical and two non-critical checks, blanket fail-open bypasses both critical checks, blanket fail-closed blocks the request on both non-critical ones, and the per-check policy denies only the critical ones.
eli5: Think of a nightclub with a security guard at the door and a coat-check clerk inside. The guard's whole job is to stop people who shouldn't come in. The coat-check clerk's job is just a nice extra. Now imagine each of them calls in sick. If the guard is out and you say "well, just let everyone in" — that's a disaster, because anyone can walk in unchecked; when the guard can't do their job, the safe move is to keep the door shut. But if the coat-check clerk is out and you say "then nobody can enter at all" — that's silly, because you've closed the whole club over a missing coat rack; when the clerk can't do their job, the right move is to let people in anyway and skip the coats. The mistake is having one rule for both. A guard being down should stop people; a coat clerk being down should not. Software checks are the same: figure out for each one whether its being down should block you or wave you through.
---

## Why this module

A request is rarely a single self-contained computation; it is a pipeline of checks, most of which reach out to other services. Some of those checks are guards — they decide whether the request is allowed at all — and some are embellishments that make the response richer. All of them share one property that matters here: the service behind them can be unavailable at the exact moment the check runs, and the code must have already decided what to do in that case.

The decision is binary and consequential. Fail open means a failed check is treated as a pass, so the request continues. Fail closed means a failed check is treated as a rejection, so the request stops. Neither is universally right, because the checks are not all the same kind of thing. What a guard should do on failure is the opposite of what an embellishment should do.

The failure that this module is about is the failure to decide per check — to instead let one blanket policy govern all of them, whether by explicit choice or by whatever the code happens to do when an exception is thrown. A blanket policy is guaranteed to be wrong for one class of check: either it disables the guards during an outage, or it lets a cosmetic dependency take down valid requests. This module runs the same set of checks under both blanket rules and a per-check policy and shows which requests each one gets wrong.

**Each dependency check is either a guard or an embellishment, and the two demand opposite behavior when their service is down — so a single fail-open or fail-closed rule for all of them is wrong for one class by construction.**

## Concepts

The property that decides the direction is what the check is for. A check that enforces security or safety exists to deny — its value is entirely in the requests it blocks — so a state where it cannot evaluate must be treated as a block, or the guarantee it provides evaporates exactly when the dependency is down. This is fail-closed, and it is why an auth check, a license check, a payment-authorization check, or a safety interlock must reject on failure rather than wave the request through.

A check that only enriches or optimizes exists to add value to requests that were already valid without it. Its absence degrades the response but does not make it wrong, so a state where it cannot evaluate must be treated as a skip. This is fail-open, and it is why a recommendation widget, a related-items panel, or an optional personalization step should let the request proceed on failure rather than fail the whole thing for a missing nicety.

The trap is treating the on-failure behavior as an accident of the code rather than a declared property of each check. When a check is written as "call the service, use the result", an exception propagates to whatever the surrounding handler does — often a blanket "return 500" (accidental fail-closed everywhere) or a blanket "swallow and continue" (accidental fail-open everywhere). Both are one rule applied to checks that needed opposite rules. The fix is to make fail-open-or-closed an explicit attribute of every check, set from whether it is a guard, so an outage of any one dependency produces the intended behavior and not the default one.

<svg role="img" aria-label="Two kinds of check with opposite on-failure directions: a guard's value is in what it blocks so it fails closed, an embellishment's value is added on top so it fails open" viewBox="0 0 440 130">
<rect x="20" y="30" width="185" height="70" fill="var(--panel)" stroke="var(--line)"/>
<text x="112" y="52" fill="var(--ink)" font-size="10" text-anchor="middle">guard (auth, rate limit)</text>
<text x="112" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">value = what it blocks</text>
<text x="112" y="88" fill="var(--s1)" font-size="10" text-anchor="middle">down =&gt; fail CLOSED</text>
<rect x="235" y="30" width="185" height="70" fill="var(--panel)" stroke="var(--line)"/>
<text x="327" y="52" fill="var(--ink)" font-size="10" text-anchor="middle">extra (recommendations)</text>
<text x="327" y="70" fill="var(--muted)" font-size="9" text-anchor="middle">value = added on top</text>
<text x="327" y="88" fill="var(--s1)" font-size="10" text-anchor="middle">down =&gt; fail OPEN</text>
</svg>
^ A guard's worth is in the requests it stops, so its outage must deny; an embellishment's worth is additive, so its outage must be skipped.

**A guard must fail closed and an embellishment must fail open; the on-failure direction has to be a declared attribute of each check, because leaving it to the default exception path applies one blanket rule where opposite rules were needed.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/ship-and-operate/code/failopen-inter-01. The fixture is a request's checks, each tagged critical (a guard, must fail closed) or not.

```json filename=modules/ship-and-operate/code/failopen-inter-01/failopen.json:3-6 COMPLETE
  "checks": [
    {"name": "authorization", "critical": true},
    {"name": "rate_limit", "critical": true},
    {"name": "recommendations", "critical": false},
```

The two blanket rules ignore the check entirely — one always allows on failure, one always denies.

```python filename=modules/ship-and-operate/code/failopen-inter-01/failopen.py:32-39 COMPLETE
def blanket_open(check):
    """Allow every check on failure (availability-first blanket rule)."""
    return "allow"


def blanket_closed(check):
    """Deny every check on failure (security-first blanket rule)."""
    return "deny"
```

The deliberate policy branches on whether the check is a guard.

```python filename=modules/ship-and-operate/code/failopen-inter-01/failopen.py:42-44 COMPLETE
def per_check(check):
    """Deliberate: a critical check fails closed (deny), a non-critical one fails open (allow)."""
    return "deny" if check["critical"] else "allow"
```

Before running it, predict: blanket-open allows all four (bypassing the two guards), blanket-closed denies all four (blocking on the two extras), and per-check denies only the two guards. Run `--outcomes`:

```text filename=failopen.py --outcomes
OUTCOMES — request outcome when each check's service is down
----------------------------------------------------------------
  check            critical   blanket-open   blanket-closed   per-check
  authorization    True       allow          deny             deny
  rate_limit       True       allow          deny             deny
  recommendations  False      allow          deny             allow
  related_items    False      allow          deny             allow
```

The prediction holds. Blanket-open's "allow" on the two critical rows is the bypass; blanket-closed's "deny" on the two non-critical rows is the needless block. The per-check column is the only one that denies exactly the guards and allows exactly the embellishments.

<svg role="img" aria-label="A table of four checks under three policies: blanket-open allows all including the two critical guards, blanket-closed denies all including the two cosmetic checks, per-check denies only the two guards and allows the two cosmetic checks" viewBox="0 0 440 170">
<text x="70" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">check</text>
<text x="185" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">blanket-open</text>
<text x="290" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">blanket-closed</text>
<text x="390" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">per-check</text>
<text x="20" y="45" fill="var(--ink)" font-size="9">authz (guard)</text>
<text x="185" y="45" fill="var(--s2)" font-size="9" text-anchor="middle">allow ✗</text>
<text x="290" y="45" fill="var(--s1)" font-size="9" text-anchor="middle">deny ✓</text>
<text x="390" y="45" fill="var(--s1)" font-size="9" text-anchor="middle">deny ✓</text>
<text x="20" y="70" fill="var(--ink)" font-size="9">rate (guard)</text>
<text x="185" y="70" fill="var(--s2)" font-size="9" text-anchor="middle">allow ✗</text>
<text x="290" y="70" fill="var(--s1)" font-size="9" text-anchor="middle">deny ✓</text>
<text x="390" y="70" fill="var(--s1)" font-size="9" text-anchor="middle">deny ✓</text>
<text x="20" y="95" fill="var(--ink)" font-size="9">recs (extra)</text>
<text x="185" y="95" fill="var(--s1)" font-size="9" text-anchor="middle">allow ✓</text>
<text x="290" y="95" fill="var(--s2)" font-size="9" text-anchor="middle">deny ✗</text>
<text x="390" y="95" fill="var(--s1)" font-size="9" text-anchor="middle">allow ✓</text>
<text x="20" y="120" fill="var(--ink)" font-size="9">related (extra)</text>
<text x="185" y="120" fill="var(--s1)" font-size="9" text-anchor="middle">allow ✓</text>
<text x="290" y="120" fill="var(--s2)" font-size="9" text-anchor="middle">deny ✗</text>
<text x="390" y="120" fill="var(--s1)" font-size="9" text-anchor="middle">allow ✓</text>
<line x1="20" y1="132" x2="420" y2="132" stroke="var(--line)"/>
<text x="220" y="152" fill="var(--muted)" font-size="9" text-anchor="middle">each blanket column has two ✗; only per-check is all ✓</text>
</svg>
^ Each blanket rule is wrong on two of the four checks; only the per-check policy is correct on every row.

Now name the specific damage. Run `--danger`:

```text filename=failopen.py --danger
DANGER — what each blanket rule gets wrong
------------------------------------------------------------
  blanket fail-open  bypasses these critical checks: ['authorization', 'rate_limit']
  blanket fail-closed blocks on these non-critical checks: ['recommendations', 'related_items']
------------------------------------------------------------
  each blanket rule sacrifices the side it does not favor
```

The two danger lists come straight from the mismatch between each blanket rule and what the check needed.

```python filename=modules/ship-and-operate/code/failopen-inter-01/failopen.py:62-63 COMPLETE
    bypassed = [c["name"] for c in checks if c["critical"] and blanket_open(c) == "allow"]
    blocked = [c["name"] for c in checks if not c["critical"] and blanket_closed(c) == "deny"]
```

Blanket fail-open turns an auth or rate-limit outage into a security bypass; blanket fail-closed turns a recommendations outage into a full request failure. Each blanket rule sacrifices exactly the side it does not favor — availability-first disables the guards, security-first fails valid requests.

<svg role="img" aria-label="Two blanket rules each with a downside: fail-open bypasses the guards during an outage, fail-closed blocks valid requests during a cosmetic outage; per-check avoids both" viewBox="0 0 440 130">
<rect x="15" y="30" width="130" height="70" fill="var(--panel)" stroke="var(--s2)"/>
<text x="80" y="50" fill="var(--ink)" font-size="10" text-anchor="middle">blanket open</text>
<text x="80" y="70" fill="var(--s2)" font-size="9" text-anchor="middle">guards bypassed</text>
<text x="80" y="86" fill="var(--muted)" font-size="8" text-anchor="middle">insecure</text>
<rect x="155" y="30" width="130" height="70" fill="var(--panel)" stroke="var(--s2)"/>
<text x="220" y="50" fill="var(--ink)" font-size="10" text-anchor="middle">blanket closed</text>
<text x="220" y="70" fill="var(--s2)" font-size="9" text-anchor="middle">valid requests blocked</text>
<text x="220" y="86" fill="var(--muted)" font-size="8" text-anchor="middle">unavailable</text>
<rect x="295" y="30" width="130" height="70" fill="var(--panel)" stroke="var(--s1)"/>
<text x="360" y="50" fill="var(--ink)" font-size="10" text-anchor="middle">per-check</text>
<text x="360" y="70" fill="var(--s1)" font-size="9" text-anchor="middle">guards deny,</text>
<text x="360" y="84" fill="var(--s1)" font-size="9" text-anchor="middle">extras allow</text>
</svg>
^ Each blanket rule pays with the side it does not favor; the per-check policy avoids both failures at once.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that blanket fail-open lets a critical check through, that blanket fail-closed blocks a non-critical one, that per-check denies every critical and allows every non-critical check, and that neither blanket rule matches the per-check policy everywhere.

```python filename=modules/ship-and-operate/code/failopen-inter-01/failopen.py:77-92 COMPLETE
    open_bypasses_critical = any(c["critical"] and blanket_open(c) == "allow" for c in checks)
    print("  blanket fail-open lets a critical check through on failure = %s" % open_bypasses_critical)

    closed_blocks_noncritical = any((not c["critical"]) and blanket_closed(c) == "deny" for c in checks)
    print("  blanket fail-closed blocks a non-critical check on failure = %s" % closed_blocks_noncritical)

    per_check_denies_critical = all(per_check(c) == "deny" for c in checks if c["critical"])
    print("  per-check: every critical check fails closed (deny) = %s" % per_check_denies_critical)

    per_check_allows_noncritical = all(per_check(c) == "allow" for c in checks if not c["critical"])
    print("  per-check: every non-critical check fails open (allow) = %s" % per_check_allows_noncritical)

    # each blanket rule matches per-check on some checks but is wrong on at least one
    open_wrong_somewhere = any(blanket_open(c) != per_check(c) for c in checks)
    closed_wrong_somewhere = any(blanket_closed(c) != per_check(c) for c in checks)
    no_blanket_is_right = open_wrong_somewhere and closed_wrong_somewhere
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if a blanket rule ever happens to match the per-check policy on every check:

```text filename=failopen.py --check
SELF-TEST — blanket fail-open bypasses critical checks; blanket fail-closed blocks on trivial ones; per-check is right
------------------------------------------------------------------------------------------------------------------------
  blanket fail-open lets a critical check through on failure = True
  blanket fail-closed blocks a non-critical check on failure = True
  per-check: every critical check fails closed (deny) = True
  per-check: every non-critical check fails open (allow) = True
  neither blanket rule matches the per-check policy everywhere = True
------------------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  open_bypasses_critical=True  closed_blocks_noncritical=True  per_check_denies_critical=True  per_check_allows_noncritical=True  no_blanket_is_right=True
```

**The self-test proves both blanket rules are wrong on at least one check while the per-check policy is right on all — the point being not that one blanket rule beats the other, but that neither can be correct for a mix of guards and embellishments.**

## Definition of done

You can define fail-open and fail-closed and state the question they answer: what a request does when a check's service is unavailable.
You can classify a check as a guard or an embellishment and derive its correct on-failure direction from that.
You can explain why a security check that fails open turns its dependency's outage into a bypass, and why a cosmetic check that fails closed turns its outage into a full request failure.
You can explain why the on-failure direction must be a declared attribute of each check rather than whatever the exception path does by default.
You can predict, for a new check, which direction it should fail and justify it.

## Boss fight

Consider a check that is critical but whose fail-closed behavior would itself cause an outage — a rate limiter, for instance. Failing it closed on the limiter's outage denies every request, which protects nothing and takes the service down; failing it open lets traffic through unmetered, risking overload. Neither pure direction is comfortable, and the real answer is often a third option: a local fallback (a conservative in-process limit) so the check degrades to a safe approximation rather than choosing between total denial and total bypass. The lesson deepens: "critical" does not automatically mean "fail closed to a hard deny" — it means the failure must be handled deliberately, and sometimes the deliberate handling is a fallback, not a binary.

Now consider the auditing angle. Suppose an authorization check fails closed correctly, denying the request — but the denial is silent, indistinguishable from a normal "not authorized". During an auth-service outage, a flood of these looks like a spike in legitimate denials, hiding the outage. So fail-closed is necessary but not sufficient: the failure must also be observable, logged and alerted as a dependency failure and not as a routine rejection, or you will make the safe choice and still be blind to why your denials spiked. Correct behavior and correct observability are separate requirements.

**"Critical" means handle the failure deliberately, not always hard-deny — sometimes a conservative fallback is the right degradation — and even a correct fail-closed must be observable as a dependency failure, or a safe denial spike hides the outage causing it.**

## External resources

Security engineering texts use "fail-safe defaults" (Saltzer and Schroeder) to argue that access decisions should default to denial — the principled statement of why guards fail closed.
Site-reliability writing on graceful degradation covers the complementary case: shedding non-critical features so a request survives a dependency's outage, which is fail-open applied to embellishments.
The topic's own modules on circuit breakers and on stale-cache fallback cover adjacent tools for behaving well when a dependency is unavailable.
