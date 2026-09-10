"""Attach a monotonically increasing fencing token to every lock acquisition and have storage reject stale ones -- otherwise a paused lock-holder wakes up and clobbers the data the lock was supposed to protect.

A distributed lock with a lease has a gap you cannot close from the lock alone. A client acquires the lock, then stalls -- a long garbage-collection pause, a network partition, a descheduled thread -- for longer than the lease. The lease expires. A second client, seeing the lock free, legitimately acquires it and does its work. Then the first client wakes up, still believing it holds the lock, and issues the write it was about to make when it stalled. That write is stale: the world moved on while the client was frozen, but the client does not know it. If storage accepts the write, it overwrites the second client's work, and the lock protected nothing -- because the whole failure is that the paused client never learned it had lost the lock.

You cannot fix this by making the client check the lock before writing: it can pass the check, stall, and then write, with the loss of the lock happening in the gap between the check and the write. The check and the write are not atomic across a pause. The protection has to live at the storage, which is the one party that sees the writes actually land.

The fix is a fencing token. The lock service hands out a strictly increasing number with each acquisition: client A gets 1, and when the lease expires and B acquires, B gets 2. Every client attaches its token to every write. Storage remembers the highest token it has ever accepted and rejects any write whose token is not strictly greater. When the paused client A finally writes, it carries its old token 1, storage has already accepted B's token 2, and 1 is not greater than 2 -- so the stale write is rejected. The fence holds even though A still thinks it owns the lock, because the token, not the client's belief, is what storage trusts.

The rule: issue a strictly increasing fencing token with every lock acquisition and have storage reject any write whose token is not greater than the highest already accepted, because a lease-based lock cannot stop a paused holder from waking and writing stale data -- only a monotonic token checked at the storage can.

On this fixture the writes arrive as A(token 1), B(token 2), then A again with its stale token 1. Without fencing, storage applies all three in order and ends on 'a-stale' -- corrupt. With fencing, storage accepts tokens 1 and 2 and rejects the stale token-1 write, ending on 'b2' -- correct. This computes both.

  --replay    each write and whether each policy accepts or rejects it
  --final     the final stored value under no-fencing vs fencing
  --check     without fencing the stale write corrupts storage; with fencing it is rejected and the correct value survives

writes is the fixture; the accept/reject decisions and the final stored value under each policy are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "fencing.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def apply_no_fencing(writes):
    """Storage accepts every write in arrival order -- a lock with no fencing."""
    stored, log = None, []
    for w in writes:
        stored = w["value"]
        log.append((w, "accept", stored))
    return stored, log


def apply_fencing(writes):
    """Storage rejects any write whose token is not strictly greater than the highest accepted."""
    stored, highest, log = None, 0, []
    for w in writes:
        if w["token"] > highest:
            highest, stored = w["token"], w["value"]
            log.append((w, "accept", stored))
        else:
            log.append((w, "reject (stale token)", stored))
    return stored, log


def latest_legitimate(writes):
    """The value from the write holding the highest token -- the one that legitimately holds the lock."""
    return max(writes, key=lambda w: w["token"])["value"]


# ----------------------------------------------------------------- printing

def replay_view(data):
    writes = data["writes"]
    _, nf = apply_no_fencing(writes)
    _, fn = apply_fencing(writes)
    print("REPLAY — each write as it arrives at storage, and each policy's decision")
    print("-" * 74)
    print("  client  token  value      no-fencing        fencing")
    for (w, na, _ns), (_w2, fa, _fs) in zip(nf, fn):
        print("  %-6s  %-5d  %-9s  %-16s  %s" % (w["client"], w["token"], w["value"], na, fa))
    print("-" * 74)
    print("  no-fencing accepts everything; fencing rejects the write with the stale token")


def final_view(data):
    writes = data["writes"]
    nf_final, _ = apply_no_fencing(writes)
    fn_final, _ = apply_fencing(writes)
    print("FINAL — the value left in storage under each policy")
    print("-" * 60)
    print("  latest legitimate value (highest token) = %r" % latest_legitimate(writes))
    print("  no-fencing final                         = %r" % nf_final)
    print("  fencing final                            = %r" % fn_final)
    print("-" * 60)
    print("  no-fencing ends on the stale write; fencing preserves the legitimate value")


def check(data):
    print("SELF-TEST — without fencing the stale write corrupts storage; with fencing it is rejected and the correct value survives")
    print("-" * 122)
    writes = data["writes"]
    nf_final, _ = apply_no_fencing(writes)
    fn_final, fn_log = apply_fencing(writes)
    legit = latest_legitimate(writes)

    seen, stale = 0, []
    for w in writes:
        if w["token"] > seen:
            seen = w["token"]
        else:
            stale.append(w)
    has_stale_write = len(stale) > 0
    print("  a write arrives with a token no higher than one already seen = %s (%s)"
          % (has_stale_write, [(w["client"], w["token"]) for w in stale]))

    nofence_corrupted = nf_final != legit
    print("  without fencing the final value is NOT the legitimate one = %s (%r != %r)" % (nofence_corrupted, nf_final, legit))

    rejects = [w for (w, decision, _s) in fn_log if decision.startswith("reject")]
    fencing_rejects_stale = len(rejects) == len(stale) and len(rejects) > 0
    print("  fencing rejects exactly the stale write(s) = %s (%d rejected)" % (fencing_rejects_stale, len(rejects)))

    fencing_final_correct = fn_final == legit
    print("  with fencing the final value IS the legitimate one = %s (%r)" % (fencing_final_correct, fn_final))

    policies_disagree = nf_final != fn_final
    print("  the two policies leave different values in storage = %s (%r vs %r)" % (policies_disagree, nf_final, fn_final))

    ok = (has_stale_write and nofence_corrupted and fencing_rejects_stale and fencing_final_correct and policies_disagree)
    print("-" * 122)
    print("SELF-TEST %s  has_stale_write=%s  nofence_corrupted=%s  fencing_rejects_stale=%s  fencing_final_correct=%s  policies_disagree=%s"
          % ("PASS" if ok else "FAIL", has_stale_write, nofence_corrupted, fencing_rejects_stale, fencing_final_correct, policies_disagree))
    return ok


def main():
    p = argparse.ArgumentParser(description="Fencing tokens: issue a strictly increasing fencing token with every lock acquisition and have storage reject any write whose token is not greater than the highest already accepted, because a lease-based lock cannot stop a paused holder from waking and writing stale data -- only a monotonic token checked at the storage can.")
    p.add_argument("--replay", action="store_true")
    p.add_argument("--final", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("writes=%d  file=%s  (the write sequence is a fixture)" % (len(data["writes"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.replay:
        replay_view(data)
    elif args.final:
        final_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
