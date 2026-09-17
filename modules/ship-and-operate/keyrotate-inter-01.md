---
id: keyrotate-inter-01
title: Rotate a signing key by adding it to the verifier's keyset, not by swapping it in
topic: ship-and-operate
level: intermediate
status: ready
time: 15 min
summary: A token is a message signed with a secret — the issuer HMACs (id, issued_at, ttl) with the current key, and the verifier accepts the token only if the signature matches a key it trusts and the token has not expired. Rotating the signing secret tempts the obvious move: swap the verifier to the new key. That is a hard cutover, and it is an outage. At the instant of rotation the verifier's trusted set becomes {v2} alone, so every token still signed with v1 fails the signature check — including tokens issued a minute ago whose ttl has twenty minutes left. Those are live sessions, and rotation just invalidated all of them at once; the pager goes off for an auth failure no code change caused. On the fixture, at now 110 with rotation at 100 and ttl 30, two v1 tokens (issued 85 and 95) are unexpired and one (issued 60) has expired; the hard cutover to {v2} rejects all three v1 tokens, two of them wrongly. The fix is to treat rotation as an add, not a swap: the verifier trusts a set {v1, v2}, new tokens are signed with v2, old tokens keep verifying against v1 until they expire on their own, and v1 is retired only after the last token that could carry it — issued the instant before rotation — has expired, at rotation_time + max_ttl = 130. The overlap set still enforces expiry, so the genuinely expired v1 token is still rejected; it only stops rejecting the unexpired ones — accepting 3 valid tokens where the cutover accepted 1. The rule: a signing key cannot be rotated atomically because tokens outlive the rotation, so the verifier must trust old and new together for an overlap window as long as the longest token lives.
eli5: Imagine the doorman checks wristbands against today's stamp. If you change the stamp at noon and tell the doorman to only accept the new one, everyone who got the old stamp this morning — bands that are still good all day — gets turned away at the door, even though they did nothing wrong. The fix is to tell the doorman to accept both stamps for a while: hand out the new stamp to newcomers, but keep honoring this morning's stamp until every band that carries it would have expired anyway. Only once no valid old band can exist do you tell the doorman to forget the old stamp. You can't swap the stamp in an instant, because the bands you already gave out outlive the swap.
---

## Why this module

Rotating a signing key — for sessions, API tokens, signed cookies, JWTs — is routine security hygiene, and it has a trap that looks like the correct implementation. The key is a single value the verifier holds; rotating it looks like assigning a new value. Replace the secret, deploy, done.

That reasoning is right for a password and wrong for a signing key, and the difference is that tokens signed with the old key are already out in the world with lifetimes that extend past the moment you rotate. The verifier does not just need the new key going forward; it still needs the old key to honor everything it already signed.

**A signing key cannot be rotated atomically, because the tokens it signed outlive the rotation — swap it in an instant and you invalidate every live session that carried the old key.**

## Concepts

A token carries its own signature. The issuer takes the token's fields — here (id, issued_at, ttl) — and computes an HMAC of them with the current secret, attaching the result. To verify, the verifier recomputes the HMAC with a key it trusts and checks two things: the signature matches, and the token has not expired (issued_at + ttl is still in the future). Both must hold.

Rotation introduces a new secret, v2, at some rotation_time. The question is what the verifier's trusted keys are after that moment, and the whole bug lives in the answer.

The hard cutover makes the trusted set {v2} — the new key replaces the old. Now a token signed with v1 recomputes to a signature that matches no trusted key, so it is rejected on the signature check alone, before expiry is even considered. Its ttl is irrelevant; a token issued one second before rotation with a full lifetime ahead of it fails exactly as hard as a forged one. Every unexpired v1 token in the wild is invalidated the instant you deploy.

The overlap keyset makes the trusted set {v1, v2} — the new key is added, not substituted. A v1 token still matches v1 and passes the signature check, then faces the normal expiry check and is accepted if and only if it is still within its ttl. New tokens are signed with v2 and verify against v2. The old key stays in the set until every token that could bear it has expired: the last such token was issued the instant before rotation_time, so it expires at rotation_time + max_ttl, and only then is v1 safe to retire.

**Hard cutover rejects a token for being signed with the old key; the overlap keyset trusts both keys and rejects a token only for being genuinely expired.**

<svg role="img" aria-label="Two verifier configurations after rotation. Cutover trusts only v2, so a v1 token fails the signature check regardless of its expiry. Overlap trusts v1 and v2, so a v1 token passes the signature check and is then judged on expiry alone." viewBox="0 0 520 160">
<rect x="0" y="0" width="520" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">what the verifier trusts after rotation</text>
<text x="12" y="48" fill="var(--s1)" font-size="11">cutover: trusts { v2 }</text>
<text x="30" y="68" fill="var(--muted)" font-size="10">v1 token &#8594; signature matches nothing &#8594; REJECT (even if unexpired)</text>
<text x="12" y="104" fill="var(--s2)" font-size="11">overlap: trusts { v1, v2 }</text>
<text x="30" y="124" fill="var(--muted)" font-size="10">v1 token &#8594; signature matches v1 &#8594; then expiry decides &#8594; ACCEPT if unexpired</text>
<text x="30" y="142" fill="var(--muted)" font-size="10">retire v1 only at rotation_time + max_ttl</text>
</svg>
^ The only difference is the size of the trusted set; adding v2 instead of substituting it moves the v1 token past the signature gate so expiry, not the key, decides its fate.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/ship-and-operate/code/keyrotate-inter-01/keyrotate.py

The fixture rotates at time 100 with a ttl of 30, and reads the tokens at now = 110.

```json filename=modules/ship-and-operate/code/keyrotate-inter-01/keyrotate.json:3-13 COMPLETE
  "secret_v1": "old-signing-secret-v1",
  "secret_v2": "new-signing-secret-v2",
  "rotation_time": 100,
  "now": 110,
  "max_ttl": 30,
  "tokens": [
    {"id": "sess-1", "issued_at": 85,  "ttl": 30, "signed_with": "v1"},
    {"id": "sess-2", "issued_at": 95,  "ttl": 30, "signed_with": "v1"},
    {"id": "sess-3", "issued_at": 60,  "ttl": 30, "signed_with": "v1"},
    {"id": "sess-4", "issued_at": 105, "ttl": 30, "signed_with": "v2"}
  ]
```

The signature is a real HMAC over the token's fields.

```python filename=modules/ship-and-operate/code/keyrotate-inter-01/keyrotate.py:32-35 COMPLETE
def sign(secret, tok):
    """The token's HMAC-SHA256 signature over its (id, issued_at, ttl) under a secret."""
    msg = ("%s|%d|%d" % (tok["id"], tok["issued_at"], tok["ttl"])).encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
```

Verification is the two-part gate: the signature must match some trusted key, and the token must not be expired.

```python filename=modules/ship-and-operate/code/keyrotate-inter-01/keyrotate.py:43-55 COMPLETE
def signature_valid(tok, keyset):
    """True if the token's signature matches ANY trusted key (compared in constant time)."""
    return any(hmac.compare_digest(tok["sig"], sign(secret, tok)) for secret in keyset.values())


def not_expired(tok, now):
    """True if the token's lifetime has not run out yet."""
    return tok["issued_at"] + tok["ttl"] > now


def verify(tok, keyset, now):
    """Accept only a token whose signature is trusted AND whose ttl has not expired."""
    return signature_valid(tok, keyset) and not_expired(tok, now)
```

Run the hard cutover — trusted set {v2} only — and the still-valid sessions fail.

```text filename=keyrotate.py --cutover
CUTOVER — hard swap: verifier trusts {v2} only, from rotation_time 100
------------------------------------------------------------------------
  sess-1 signed v1 issued 85 exp 115  unexpired=True  ACCEPT=False   <- valid, wrongly rejected
  sess-2 signed v1 issued 95 exp 125  unexpired=True  ACCEPT=False   <- valid, wrongly rejected
  sess-3 signed v1 issued 60 exp 90  unexpired=False  ACCEPT=False
  sess-4 signed v2 issued 105 exp 135  unexpired=True  ACCEPT=True
------------------------------------------------------------------------
  every unexpired v1 token fails the signature check -- a self-inflicted auth outage
```

sess-1 and sess-2 are unexpired — they expire at 115 and 125, both after now 110 — yet they are rejected, because their v1 signature matches nothing in {v2}. sess-3 is expired and would be rejected anyway. sess-4 is the only survivor. Two live sessions logged out by a key rotation.

<svg role="img" aria-label="A timeline from 60 to 135 with rotation at 100 and now at 110. Token sess-1 spans 85 to 115, sess-2 spans 95 to 125, both crossing now; sess-3 spans 60 to 90, ending before now; sess-4 spans 105 to 135. The two v1 tokens crossing now are the ones a hard cutover wrongly rejects." viewBox="0 0 520 180">
<rect x="0" y="0" width="520" height="180" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">token lifetimes around the rotation (now = 110)</text>
<line x1="60" y1="150" x2="490" y2="150" stroke="var(--line)"></line>
<line x1="300" y1="30" x2="300" y2="150" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="270" y="28" fill="var(--muted)" font-size="9">rotate 100</text>
<line x1="360" y1="30" x2="360" y2="150" stroke="var(--grid)"></line>
<text x="352" y="28" fill="var(--muted)" font-size="9">now 110</text>
<line x1="210" y1="48" x2="390" y2="48" stroke="var(--s1)" stroke-width="3"></line>
<text x="394" y="52" fill="var(--s1)" font-size="9">sess-1 v1 (85-115)</text>
<line x1="270" y1="72" x2="450" y2="72" stroke="var(--s1)" stroke-width="3"></line>
<text x="394" y="68" fill="var(--s1)" font-size="9">sess-2 v1 (95-125)</text>
<line x1="60" y1="96" x2="240" y2="96" stroke="var(--muted)" stroke-width="3"></line>
<text x="60" y="92" fill="var(--muted)" font-size="9">sess-3 v1 (60-90, expired)</text>
<line x1="330" y1="120" x2="510" y2="120" stroke="var(--s2)" stroke-width="3"></line>
<text x="360" y="134" fill="var(--s2)" font-size="9">sess-4 v2 (105-135)</text>
</svg>
^ sess-1 and sess-2 cross the now line still alive but signed with v1; a cutover to {v2} rejects exactly these two, while sess-3 was already expired and sess-4 is on the new key.

## Build

Add the key instead of swapping it — trusted set {v1, v2}.

```text filename=keyrotate.py --overlap
OVERLAP — keyset {v1, v2}: v1 tokens verify until they expire, v2 tokens verify
------------------------------------------------------------------------
  sess-1 signed v1 issued 85 exp 115  unexpired=True  ACCEPT=True
  sess-2 signed v1 issued 95 exp 125  unexpired=True  ACCEPT=True
  sess-3 signed v1 issued 60 exp 90  unexpired=False  ACCEPT=False   <- expired, correctly rejected
  sess-4 signed v2 issued 105 exp 135  unexpired=True  ACCEPT=True
------------------------------------------------------------------------
  v1 can be retired only at rotation_time + max_ttl = 130 (now is 110)
```

Now the two unexpired v1 sessions are accepted, the expired one is still rejected — the overlap did not disable expiry, it only stopped rejecting on the key — and the v2 token verifies. Three accepted where the cutover accepted one.

<svg role="img" aria-label="A bar showing accepted tokens: hard cutover accepts 1 of 4, overlap keyset accepts 3 of 4, and the fourth is the genuinely expired token that both correctly reject." viewBox="0 0 460 160">
<rect x="0" y="0" width="460" height="160" fill="var(--panel)"></rect>
<text x="12" y="20" fill="var(--ink)" font-size="12">tokens accepted (3 are valid, 1 is expired)</text>
<line x1="60" y1="130" x2="430" y2="130" stroke="var(--line)"></line>
<line x1="60" y1="52" x2="430" y2="52" stroke="var(--grid)" stroke-dasharray="3 3"></line>
<text x="434" y="55" fill="var(--muted)" font-size="9">3 valid</text>
<rect x="110" y="104" width="70" height="26" fill="var(--s1)"></rect>
<text x="112" y="98" fill="var(--s1)" font-size="10">cutover: 1</text>
<rect x="290" y="52" width="70" height="78" fill="var(--s2)"></rect>
<text x="292" y="46" fill="var(--s2)" font-size="10">overlap: 3</text>
</svg>
^ The overlap keyset accepts every valid token (3) and stops at the expired one; the hard cutover accepts only the single token that happened to be on the new key.

The self-test ties the two failures together: the cutover rejects a still-valid token, and the overlap both accepts every unexpired token and still rejects the expired one — plus it refuses to retire v1 while a valid v1 token can still exist.

```python filename=modules/ship-and-operate/code/keyrotate-inter-01/keyrotate.py:105-111 COMPLETE
    cutover_rejects_valid = any(not verify(t, cut, now) and not_expired(t, now) for t in tokens)
    print("  hard cutover rejects a token that is still unexpired = %s" % cutover_rejects_valid)

    overlap_accepts_valid = all(verify(t, ovl, now) for t in tokens if not_expired(t, now))
    print("  overlap set accepts every unexpired token = %s" % overlap_accepts_valid)

    overlap_rejects_expired = all(not verify(t, ovl, now) for t in tokens if not not_expired(t, now))
    print("  overlap set still rejects the expired token (expiry enforced) = %s" % overlap_rejects_expired)
```

```text filename=keyrotate.py --check
SELF-TEST — the hard cutover rejects a still-valid token while the overlap set accepts every unexpired token, still rejects the expired one, and cannot retire v1 yet without rejecting valid tokens
----------------------------------------------------------------------------------------------------------------
  hard cutover rejects a token that is still unexpired = True
  overlap set accepts every unexpired token = True
  overlap set still rejects the expired token (expiry enforced) = True
  cutover wrongly rejects 2 valid token(s); overlap accepts 3 token(s)
  retiring v1 now would reject an unexpired v1 token (retire safe only at 130) = True
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  cutover_rejects_valid=True  overlap_accepts_valid=True  overlap_rejects_expired=True  retire_unsafe_now=True
```

The retirement time is not a guess — it is the rotation time plus the longest a token can live, and a v1 token is still out there whenever now has not reached it.

```python filename=modules/ship-and-operate/code/keyrotate-inter-01/keyrotate.py:118-120 COMPLETE
    retire_at = data["rotation_time"] + data["max_ttl"]
    retire_unsafe_now = now < retire_at and any(t["signed_with"] == "v1" and not_expired(t, now) for t in tokens)
    print("  retiring v1 now would reject an unexpired v1 token (retire safe only at %d) = %s" % (retire_at, retire_unsafe_now))
```

**The retire_unsafe_now flag is the part people skip: adding v2 is easy, but removing v1 too early re-creates the exact cutover outage — v1 stays until rotation_time + max_ttl.**

## Definition of done

You can explain why a signing key is not like a password: rotating a password takes effect instantly because nothing was signed with it, while a signing key has outstanding tokens whose lifetimes cross the rotation.

You can compute the safe retirement time for the old key from the rotation time and the maximum token ttl, and say why retiring earlier reproduces the cutover outage.

You can state the two independent reasons the verifier rejects a token — untrusted signature and expiry — and show that the overlap keyset changes only the first while leaving the second intact.

You can name what a token needs to carry to make this efficient in practice: a key id (kid) so the verifier tries the one matching key instead of every key in the set.

## Boss fight

Your service signs session cookies with a single secret in an environment variable, and a rotation runbook says "update the secret and redeploy." A rotation last week logged out every active user for the length of the deploy, and the proposed fix is "rotate at 3am when traffic is low."

First: explain why "rotate at low traffic" reduces the blast radius but does not fix the bug — what is the largest ttl of a token that could still be live at 3am, and does a quiet hour make those tokens any less valid?

Then: design the overlap. The verifier must accept two secrets at once, but a plain HMAC gives no hint which key signed a token, so the verifier has to try both — fine for two keys, a problem at more. Add the one field to the token that lets the verifier pick the right key directly, and say what the verifier does when that field names a key it has already retired.

Finally: write the three-phase runbook that a signing-key rotation actually requires, and give the earliest safe time for each phase in terms of rotation_time and max_ttl — phase 1 adds v2 and starts signing new tokens with it, phase 2 waits, phase 3 removes v1. What exactly is phase 2 waiting for, and what breaks if an operator compresses phases 1 and 3 into one deploy?

## External resources

The JWT/JWKS model is this module standardized: a JSON Web Key Set publishes multiple keys at once, each with a kid, and verifiers select the key named by the token's header — the overlap keyset is the whole point of the format.

Any secrets manager's rotation documentation (AWS Secrets Manager, HashiCorp Vault) describes the same two-secret window under names like "AWSCURRENT and AWSPREVIOUS" — the previous version is kept live precisely so in-flight credentials signed with it keep working during the overlap.
