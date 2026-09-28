"""Write the latest version back to a stale replica during the read -- a quorum read alone returns right but leaves it stale.

A quorum-replicated store keeps N copies of each key and, on a read, contacts a read quorum of them and returns the newest
version it sees; sized correctly (R + W > N) this guarantees the read observes the latest write. But 'the read returns the
right value' is not the same as 'the replicas are consistent.' A replica that missed a write -- it was briefly
unreachable, or the write's message was dropped -- holds a stale version, and a correct quorum read papers over that
staleness rather than fixing it: as long as ENOUGH fresh replicas are in the quorum, the read returns the latest version
and the stale replica is simply outvoted. The stale copy stays stale. It will keep being stale on the next read, and the
next, until something writes the key again or a slow background process reconciles it -- and until then the replica set is
divergent, one bad node away from serving old data if the fresh replicas are the ones that go down.

READ REPAIR closes this gap using the read traffic you are already paying for. When a read contacts several replicas and
finds that some returned an OLDER version than the newest, the coordinator does two things: it returns the newest version
to the client (as always), AND it writes that newest version back to the replicas that were behind. The read thus heals
the replicas it touched: a stale replica that participates in a read is brought up to date as a side effect, so popular
keys -- the ones read often -- stay converged almost for free, and the store repairs itself continuously instead of
accumulating stale copies between writes. Read repair is opportunistic anti-entropy: it only fixes the replicas a read
happened to contact, so it complements (does not replace) a background sweep for the cold keys that are rarely read, but
for hot data it is the cheapest convergence there is.

The important subtlety is that read repair does not change what the read RETURNS -- a correct quorum read already returns
the latest version. It changes the STATE the read leaves behind: without it, the divergence persists; with it, the read
that observed the divergence also erases it.

The rule: on a quorum read that contacts a replica holding an older version than the newest observed, write the newest
version back to that replica during the read (read repair), because a correct quorum read returns the latest value but
leaves a stale replica stale, so the read traffic itself should be used to converge the replicas rather than letting
divergence persist until the next write.

On this fixture a write reached A and B (version 2) but C missed it (version 1). A read contacts A and C. Both with and
without repair the read returns version 2 (correct). Without repair, C stays at version 1 -- one stale replica remains.
With repair, C is written up to version 2 during the read -- zero stale replicas. This computes both.

  --read      the read of A and C: the version each returns, the version returned to the client, and C's version afterward
  --converge  stale replicas (behind the newest) before the read, and after, with and without read repair
  --check     both modes return the latest version; only read repair heals the stale replica during the read

replicas and read_contacts are the fixture; every returned version, repair write, and stale count is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "readrepair.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def do_read(replicas, contacts, repair):
    """Return (returned_version, new_replica_state, repaired). Reads a copy; does not mutate the input."""
    state = dict(replicas)
    seen = {r: state[r] for r in contacts}
    latest = max(seen.values())
    repaired = []
    if repair:
        for r in contacts:
            if state[r] < latest:
                state[r] = latest        # write the newest version back to the behind replica
                repaired.append(r)
    return latest, state, repaired


def stale_count(replicas):
    """How many replicas hold a version behind the newest one anywhere in the set."""
    latest = max(replicas.values())
    return sum(1 for v in replicas.values() if v < latest)


# ----------------------------------------------------------------- printing

def read_view(data):
    replicas, contacts = data["replicas"], data["read_contacts"]
    latest = max(replicas[r] for r in contacts)
    print("READ — contacting %s; newest version among them is %d" % (contacts, latest))
    print("-" * 66)
    for r in contacts:
        tag = "  <- behind" if replicas[r] < latest else ""
        print("    %s returns version %d%s" % (r, replicas[r], tag))
    nr_v, nr_state, _ = do_read(replicas, contacts, repair=False)
    rr_v, rr_state, repaired = do_read(replicas, contacts, repair=True)
    print("-" * 66)
    print("  returned to client: %d (no-repair) / %d (read-repair) -- same correct value" % (nr_v, rr_v))
    print("  C afterwards: version %d (no-repair) / version %d (read-repair, repaired %s)"
          % (nr_state["C"], rr_state["C"], repaired))


def converge_view(data):
    replicas, contacts = data["replicas"], data["read_contacts"]
    _, nr_state, _ = do_read(replicas, contacts, repair=False)
    _, rr_state, repaired = do_read(replicas, contacts, repair=True)
    print("CONVERGE — stale replicas (behind the newest) before and after the read")
    print("-" * 60)
    print("  before read:               %s  -> %d stale" % (replicas, stale_count(replicas)))
    print("  after read, no repair:     %s  -> %d stale" % (nr_state, stale_count(nr_state)))
    print("  after read, read repair:   %s  -> %d stale (repaired %s)" % (rr_state, stale_count(rr_state), repaired))
    print("-" * 60)
    print("  read repair uses the read to converge the replicas; no-repair leaves the divergence for later.")


def check(data):
    print("SELF-TEST — both modes return the latest version; only read repair heals the stale replica during the read")
    print("-" * 108)
    replicas, contacts = data["replicas"], data["read_contacts"]
    nr_v, nr_state, _ = do_read(replicas, contacts, repair=False)
    rr_v, rr_state, repaired = do_read(replicas, contacts, repair=True)
    latest = max(replicas.values())

    both_return_latest = nr_v == latest and rr_v == latest
    print("  both modes return the latest version = %s (no-repair %d, repair %d)" % (both_return_latest, nr_v, rr_v))

    norepair_leaves_stale = stale_count(nr_state) == stale_count(replicas) and stale_count(nr_state) > 0
    print("  without repair the stale replica stays stale = %s (%d stale before and after)"
          % (norepair_leaves_stale, stale_count(nr_state)))

    repair_heals = stale_count(rr_state) == 0
    print("  read repair leaves zero stale replicas = %s (%s)" % (repair_heals, rr_state))

    repair_targeted_behind = repaired == ["C"]
    print("  read repair wrote back only to the behind, contacted replica = %s (repaired %s)" % (repair_targeted_behind, repaired))

    convergence_differs = stale_count(nr_state) != stale_count(rr_state)
    print("  the two modes leave the replica set in different states = %s (%d vs %d stale)"
          % (convergence_differs, stale_count(nr_state), stale_count(rr_state)))

    ok = both_return_latest and norepair_leaves_stale and repair_heals and repair_targeted_behind and convergence_differs
    print("-" * 108)
    print("SELF-TEST %s  both_return_latest=%s  norepair_leaves_stale=%s  repair_heals=%s  repair_targeted_behind=%s  convergence_differs=%s"
          % ("PASS" if ok else "FAIL", both_return_latest, norepair_leaves_stale, repair_heals, repair_targeted_behind, convergence_differs))
    return ok


def main():
    p = argparse.ArgumentParser(description="Read repair: on a quorum read that contacts a replica holding an older version than the newest observed, write the newest version back to that replica during the read, because a correct quorum read returns the latest value but leaves a stale replica stale, so the read traffic itself should converge the replicas rather than letting divergence persist until the next write.")
    p.add_argument("--read", action="store_true")
    p.add_argument("--converge", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("replicas=%s  read_contacts=%s  file=%s  (the replica versions and read set are a fixture)"
          % (data["replicas"], data["read_contacts"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.read:
        read_view(data)
    elif args.converge:
        converge_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
