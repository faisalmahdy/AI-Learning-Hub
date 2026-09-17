"""Guard a read-modify-write with a version check, or one update is silently lost -- two clients both read the same value, both write back, and the second overwrites the first without ever seeing it.

Updating a shared record usually means read-modify-write: read the current value, compute a new one from it, write it back. That is three steps, and between the read and the write, someone else can write. If your write is blind -- it just stores your value -- then you overwrite whatever landed in between as if it were never there.

So two clients that both read the same starting value and both write back produce a lost update. Each computed its new value from the same old value, unaware of the other, and the one that writes second overwrites the first. The record ends at the second writer's value, and the first writer's change -- fully computed, apparently committed -- simply vanishes. The count is wrong, and nothing errored.

Optimistic concurrency control fixes this without a lock. The client remembers the version it read and sends it with the write as an expected version. The store performs a compare-and-swap: it applies the write only if the record is still at that version, and rejects it otherwise. A rejection is information -- it means someone wrote since you read, so your value is based on stale data. The rejected client re-reads the now-current value, re-applies its change to that, and writes again against the fresh version, which succeeds. Both changes land, in a serialized order, with no lock held.

On this fixture the record starts at 100, client A subtracts 10 and client B subtracts 5, applied A then B; the correct result is 85. A blind write leaves 95 -- A's subtraction is lost. Compare-and-swap rejects B's stale write, B retries against A's result, and the record ends at the correct 85. This computes both.

  --blind    the blind read-modify-write: both read 100, and B's write overwrites A's, losing an update
  --occ      the compare-and-swap: B's stale write is rejected, B retries against the fresh value, both land
  --check    the blind path loses an update while the compare-and-swap path rejects the stale write, retries, and gets the correct total

initial value/version and the two deltas are the fixture; the blind final value and the compare-and-swap final value are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "occ.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def new_store(data):
    """The shared record: a value and a version that bumps on every accepted write."""
    return {"value": data["initial_value"], "version": data["initial_version"]}


def blind_write(store, value):
    """Overwrite the record unconditionally -- no check that it is still what the writer read."""
    store["value"] = value
    store["version"] += 1
    return {"accepted": True}


def cas_write(store, value, expected_version):
    """Compare-and-swap: apply the write only if the record is still at the version the client read."""
    if store["version"] != expected_version:
        return {"accepted": False, "current_version": store["version"], "current_value": store["value"]}
    store["value"] = value
    store["version"] += 1
    return {"accepted": True}


def run_blind(data):
    """Both clients read the start value, then write their result back blindly, A then B."""
    store = new_store(data)
    a_read = store["value"]                          # A reads 100
    b_read = store["value"]                          # B reads 100 (before A's write lands)
    blind_write(store, a_read + data["client_a_delta"])   # A writes 90
    blind_write(store, b_read + data["client_b_delta"])   # B writes 95, overwriting A
    return store["value"]


def run_occ(data):
    """Both read the start version; A's CAS succeeds, B's is rejected, B re-reads and retries."""
    store = new_store(data)
    a_val, a_ver = store["value"], store["version"]       # A reads (100, v1)
    b_val, b_ver = store["value"], store["version"]       # B reads (100, v1)
    cas_write(store, a_val + data["client_a_delta"], a_ver)          # A: CAS at v1 -> accepted, 90 v2
    first = cas_write(store, b_val + data["client_b_delta"], b_ver)  # B: CAS at v1, store is v2 -> rejected
    retried = False
    if not first["accepted"]:
        b_val, b_ver = first["current_value"], first["current_version"]   # B re-reads (90, v2)
        cas_write(store, b_val + data["client_b_delta"], b_ver)           # B: CAS at v2 -> accepted, 85 v3
        retried = True
    return store["value"], retried, first["accepted"]


# ----------------------------------------------------------------- printing

def _correct(data):
    return data["initial_value"] + data["client_a_delta"] + data["client_b_delta"]


def blind_view(data):
    final = run_blind(data)
    print("BLIND — both read then overwrite, A then B")
    print("-" * 60)
    print("  start %d; A reads %d, B reads %d (both before any write lands)" % (data["initial_value"], data["initial_value"], data["initial_value"]))
    print("  A writes %d, then B writes %d (overwriting A)" % (data["initial_value"] + data["client_a_delta"], data["initial_value"] + data["client_b_delta"]))
    print("  final = %d   correct = %d   lost update? %s" % (final, _correct(data), final != _correct(data)))
    print("-" * 60)
    print("  B never saw A's change, so writing over it dropped A's update")


def occ_view(data):
    final, retried, b_first_ok = run_occ(data)
    print("OCC — compare-and-swap on the version read")
    print("-" * 60)
    print("  A CAS at v%d -> accepted (%d)" % (data["initial_version"], data["initial_value"] + data["client_a_delta"]))
    print("  B CAS at v%d -> %s (store moved to v%d)" % (data["initial_version"], "accepted" if b_first_ok else "REJECTED", data["initial_version"] + 1))
    print("  B re-reads the fresh value and retries: %s" % retried)
    print("  final = %d   correct = %d   lost update? %s" % (final, _correct(data), final != _correct(data)))
    print("-" * 60)
    print("  the rejection told B its read was stale, so it recomputed against the fresh value")


def check(data):
    print("SELF-TEST — the blind path loses an update while the compare-and-swap path rejects the stale write, retries, and gets the correct total")
    print("-" * 112)
    correct = _correct(data)
    blind_final = run_blind(data)
    occ_final, retried, b_first_ok = run_occ(data)

    blind_loses_update = blind_final != correct
    print("  the blind read-modify-write loses an update = %s (final %d, correct %d)" % (blind_loses_update, blind_final, correct))

    occ_rejects_stale_write = b_first_ok is False
    print("  compare-and-swap rejects B's stale write = %s" % occ_rejects_stale_write)

    occ_retries = retried is True
    print("  B re-reads and retries against the fresh version = %s" % occ_retries)

    occ_final_correct = occ_final == correct
    print("  compare-and-swap reaches the correct total = %s (final %d)" % (occ_final_correct, occ_final))

    occ_applied_both = occ_final == data["initial_value"] + data["client_a_delta"] + data["client_b_delta"]
    print("  both updates were applied under CAS = %s" % occ_applied_both)

    ok = (blind_loses_update and occ_rejects_stale_write and occ_retries
          and occ_final_correct and occ_applied_both)
    print("-" * 112)
    print("SELF-TEST %s  blind_loses_update=%s  occ_rejects_stale_write=%s  occ_retries=%s  occ_final_correct=%s  occ_applied_both=%s"
          % ("PASS" if ok else "FAIL", blind_loses_update, occ_rejects_stale_write, occ_retries,
             occ_final_correct, occ_applied_both))
    return ok


def main():
    p = argparse.ArgumentParser(description="Optimistic concurrency control: guard a read-modify-write with a compare-and-swap on the version read, because two clients that both read then write blindly lose one update -- the second overwrites the first without seeing it -- while a CAS rejects the stale write so the loser re-reads and retries and both changes land, without holding a lock.")
    p.add_argument("--blind", action="store_true")
    p.add_argument("--occ", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("value=%d version=%d  A%+d  B%+d  file=%s  (these are a fixture)"
          % (data["initial_value"], data["initial_version"], data["client_a_delta"], data["client_b_delta"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.blind:
        blind_view(data)
    elif args.occ:
        occ_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
