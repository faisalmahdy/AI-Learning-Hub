"""Rotate a signing key by ADDING the new key to the verifier's key set, not by SWAPPING it in -- a hard cutover drops the old key at the instant of rotation and every unexpired token still signed with it fails verification, logging out valid sessions that did nothing wrong, while an overlap key set accepts both keys until the old tokens expire on their own.

A token is a message signed with a secret: the issuer computes an HMAC of (id, issued_at, ttl) with the current key and attaches it; the verifier recomputes the HMAC and accepts the token only if the signature matches a key it trusts AND the token has not expired. Rotation replaces the signing secret -- new tokens should be signed with the new key.

The bug is treating rotation as a swap. At rotation_time the verifier's trusted set becomes {v2} alone, so a token signed with v1 no longer matches any trusted key and is rejected -- even though its ttl has not run out. That token is a live session: the user logged in a minute ago, their token is valid for another twenty, and the rotation just invalidated it. Every unexpired v1 token fails at once, and the pager goes off for an auth outage that no code change caused.

The fix is to treat rotation as an add. The verifier trusts a SET of keys, {v1, v2}. New tokens are signed with v2; tokens signed with v1 keep verifying against v1 until they expire naturally; and v1 is retired from the set only after the last token that could carry it -- one issued the instant before rotation_time -- has expired, at rotation_time + max_ttl. The overlap set still checks expiry, so a genuinely expired v1 token is still rejected; the overlap only stops rejecting the unexpired ones.

On this fixture the current time is 110 and rotation happened at 100. Two v1 tokens (issued 85 and 95, ttl 30) are unexpired; one v1 token (issued 60) has expired; one v2 token (issued 105) is fresh. Hard cutover to {v2} rejects all three v1 tokens -- two of them wrongly, because they were still valid. The overlap set {v1, v2} accepts both unexpired v1 tokens, still rejects the expired one, and accepts the v2 token. This computes both with real HMAC signatures.

  --cutover   hard swap to {v2}: unexpired tokens signed with v1 are rejected -- a self-inflicted auth outage
  --overlap   keyset {v1, v2}: v1 tokens verify until they expire, v2 tokens verify, expiry still enforced
  --check     the hard cutover rejects a still-valid token while the overlap set accepts every unexpired token, still rejects the expired one, and cannot retire v1 yet without rejecting valid tokens

the secrets, rotation_time, now, max_ttl, and each token (its issue time, ttl, and signing key) are the fixture; every HMAC signature and accept/reject is computed. Stdlib only.
"""
import argparse
import hashlib
import hmac
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "keyrotate.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def sign(secret, tok):
    """The token's HMAC-SHA256 signature over its (id, issued_at, ttl) under a secret."""
    msg = ("%s|%d|%d" % (tok["id"], tok["issued_at"], tok["ttl"])).encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def make_token(secret, tok):
    """Attach the signature the issuer would have made with the key current at issue time."""
    return dict(tok, sig=sign(secret, tok))


def signature_valid(tok, keyset):
    """True if the token's signature matches ANY trusted key (compared in constant time)."""
    return any(hmac.compare_digest(tok["sig"], sign(secret, tok)) for secret in keyset.values())


def not_expired(tok, now):
    """True if the token's lifetime has not run out yet."""
    return tok["issued_at"] + tok["ttl"] > now


def verify(tok, keyset, now):
    """Accept only a token whose signature is trusted AND whose ttl has not expired."""
    return signature_valid(tok, keyset) and not_expired(tok, now)


# ----------------------------------------------------------------- printing

def _build(data):
    secrets = {"v1": data["secret_v1"], "v2": data["secret_v2"]}
    return [make_token(secrets[t["signed_with"]], t) for t in data["tokens"]], secrets


def cutover_view(data):
    tokens, secrets = _build(data)
    now = data["now"]
    keyset = {"v2": secrets["v2"]}
    print("CUTOVER — hard swap: verifier trusts {v2} only, from rotation_time %d" % data["rotation_time"])
    print("-" * 72)
    for t in tokens:
        ok = verify(t, keyset, now)
        print("  %s signed %s issued %d exp %d  unexpired=%s  ACCEPT=%s%s"
              % (t["id"], t["signed_with"], t["issued_at"], t["issued_at"] + t["ttl"],
                 not_expired(t, now), ok, "" if ok or not not_expired(t, now) else "   <- valid, wrongly rejected"))
    print("-" * 72)
    print("  every unexpired v1 token fails the signature check -- a self-inflicted auth outage")


def overlap_view(data):
    tokens, secrets = _build(data)
    now = data["now"]
    keyset = {"v1": secrets["v1"], "v2": secrets["v2"]}
    print("OVERLAP — keyset {v1, v2}: v1 tokens verify until they expire, v2 tokens verify")
    print("-" * 72)
    for t in tokens:
        ok = verify(t, keyset, now)
        why = "" if ok else ("   <- expired, correctly rejected" if not not_expired(t, now) else "")
        print("  %s signed %s issued %d exp %d  unexpired=%s  ACCEPT=%s%s"
              % (t["id"], t["signed_with"], t["issued_at"], t["issued_at"] + t["ttl"],
                 not_expired(t, now), ok, why))
    retire_at = data["rotation_time"] + data["max_ttl"]
    print("-" * 72)
    print("  v1 can be retired only at rotation_time + max_ttl = %d (now is %d)" % (retire_at, now))


def check(data):
    print("SELF-TEST — the hard cutover rejects a still-valid token while the overlap set accepts every unexpired token, still rejects the expired one, and cannot retire v1 yet without rejecting valid tokens")
    print("-" * 112)
    tokens, secrets = _build(data)
    now = data["now"]
    cut = {"v2": secrets["v2"]}
    ovl = {"v1": secrets["v1"], "v2": secrets["v2"]}

    cutover_rejects_valid = any(not verify(t, cut, now) and not_expired(t, now) for t in tokens)
    print("  hard cutover rejects a token that is still unexpired = %s" % cutover_rejects_valid)

    overlap_accepts_valid = all(verify(t, ovl, now) for t in tokens if not_expired(t, now))
    print("  overlap set accepts every unexpired token = %s" % overlap_accepts_valid)

    overlap_rejects_expired = all(not verify(t, ovl, now) for t in tokens if not not_expired(t, now))
    print("  overlap set still rejects the expired token (expiry enforced) = %s" % overlap_rejects_expired)

    n_wrongly = sum(1 for t in tokens if not verify(t, cut, now) and not_expired(t, now))
    n_ok = sum(1 for t in tokens if verify(t, ovl, now))
    print("  cutover wrongly rejects %d valid token(s); overlap accepts %d token(s)" % (n_wrongly, n_ok))

    retire_at = data["rotation_time"] + data["max_ttl"]
    retire_unsafe_now = now < retire_at and any(t["signed_with"] == "v1" and not_expired(t, now) for t in tokens)
    print("  retiring v1 now would reject an unexpired v1 token (retire safe only at %d) = %s" % (retire_at, retire_unsafe_now))

    ok = (cutover_rejects_valid and overlap_accepts_valid and overlap_rejects_expired and retire_unsafe_now)
    print("-" * 112)
    print("SELF-TEST %s  cutover_rejects_valid=%s  overlap_accepts_valid=%s  overlap_rejects_expired=%s  retire_unsafe_now=%s"
          % ("PASS" if ok else "FAIL", cutover_rejects_valid, overlap_accepts_valid, overlap_rejects_expired, retire_unsafe_now))
    return ok


def main():
    p = argparse.ArgumentParser(description="Key rotation with an overlap window: rotate a signing key by adding the new key to the verifier's trusted set rather than swapping it in, because a hard cutover drops the old key the instant rotation happens and every unexpired token still signed with it fails verification -- an auth outage no code change caused -- while an overlap set trusts both keys until the old tokens expire on their own, and retires the old key only at rotation_time + max_ttl.")
    p.add_argument("--cutover", action="store_true")
    p.add_argument("--overlap", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("rotation_time=%d  now=%d  max_ttl=%d  tokens=%d  file=%s"
          % (data["rotation_time"], data["now"], data["max_ttl"], len(data["tokens"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.cutover:
        cutover_view(data)
    elif args.overlap:
        overlap_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
