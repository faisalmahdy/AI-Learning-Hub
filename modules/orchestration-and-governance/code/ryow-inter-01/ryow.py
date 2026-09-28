"""Give a client read-your-writes with a session token -- pin the version it last wrote and route its reads only to a replica caught up to that version -- because a naive any-replica read can land on a lagging replica and return the client's own stale data.

In an eventually-consistent store a write lands on one replica and spreads to the rest over time, so at any moment the replicas hold different versions of the data. That is fine until a client writes and then immediately reads. If the read is routed to a replica that has not yet received the write, the client gets back a value older than the one it just wrote -- it reads its own stale data. Nothing errored; the write is safe and will propagate; but from the client's point of view its update vanished, which is baffling and erodes trust.

One fix is to make every read strongly consistent -- a quorum read with R + W > N -- but that is a heavy, system-wide hammer: it makes every read, for every client, touch a quorum, paying latency that most reads did not need. Read-your-writes is a per-client property, and it can be bought per client, far more cheaply.

The session-token fix does exactly that. When a client writes, it remembers the version that write produced -- a token carried in its session. On each subsequent read, the router only considers replicas whose version is at least the client's last-write version, so the client is never served a value older than its own write. Replicas that have caught up serve it; laggards are skipped (or the read waits until one catches up). Other clients, with their own or no tokens, keep reading cheaply from any replica.

The guarantee this gives is scoped and precise: this client will always see its own writes, while the system as a whole stays eventually consistent. It is causal consistency for one session -- monotonic, self-consistent reads -- without paying for global strong consistency on every operation.

The rule: give a client read-your-writes by pinning its last-write version in a session token and routing each read only to a replica whose version is at least that token -- because a naive any-replica read can hit a lagging replica and return the client's own stale write, and a session token fixes it per client without forcing every read through a quorum.

On this fixture the client last wrote version 5; the replicas are at versions 5, 3, and 6. A naive read can land on the version-3 replica and return stale; a session-pinned read is eligible only for the version-5 and version-6 replicas, so it never returns stale. This computes both.

  --replicas   each replica's version, whether it is stale for this client, and whether a session read may use it
  --reads      the versions a naive any-replica read could return vs a session-pinned read
  --check      a naive read can return the client's own stale data; a session token routes only to caught-up replicas

client_write_version and the replicas are the fixture; the stale set and the session-eligible set are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "ryow.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def is_stale(replica, cwv):
    """A replica is stale for this client if its version is behind the client's last write."""
    return replica["version"] < cwv


def session_eligible(replicas, cwv):
    """Replicas a session-pinned read may use: those caught up to the client's last write."""
    return [r for r in replicas if r["version"] >= cwv]


# ----------------------------------------------------------------- printing

def replicas_view(data):
    cwv, reps = data["client_write_version"], data["replicas"]
    print("REPLICAS — client last wrote version %d" % cwv)
    print("-" * 52)
    print("  replica   version   stale?   session may use?")
    for r in reps:
        print("  %-7s   %-7d   %-6s   %s"
              % (r["id"], r["version"], is_stale(r, cwv), not is_stale(r, cwv)))
    print("-" * 52)
    print("  a session read uses only replicas at or ahead of the client's write")


def reads_view(data):
    cwv, reps = data["client_write_version"], data["replicas"]
    naive = [r["version"] for r in reps]
    session = [r["version"] for r in session_eligible(reps, cwv)]
    print("READS — versions each strategy could return (client wrote %d)" % cwv)
    print("-" * 54)
    print("  naive any-replica read could return:  %s" % naive)
    print("    of which stale (< %d):              %s" % (cwv, [v for v in naive if v < cwv]))
    print("  session-pinned read could return:     %s" % session)
    print("    of which stale (< %d):              %s" % (cwv, [v for v in session if v < cwv]))
    print("-" * 54)
    print("  the naive read can serve a version older than the client's own write")


def check(data):
    print("SELF-TEST — a naive read can return the client's own stale data; a session token routes only to caught-up replicas")
    print("-" * 120)
    cwv, reps = data["client_write_version"], data["replicas"]
    eligible = session_eligible(reps, cwv)

    some_replica_lags = any(is_stale(r, cwv) for r in reps)
    print("  some replica is behind the client's last write = %s" % some_replica_lags)

    naive_can_read_stale = any(r["version"] < cwv for r in reps)
    print("  a naive any-replica read can return a stale value = %s (%s)"
          % (naive_can_read_stale, [r["id"] for r in reps if r["version"] < cwv]))

    session_never_stale = all(r["version"] >= cwv for r in eligible)
    print("  every session-eligible replica is at or ahead of the write = %s" % session_never_stale)

    session_excludes_laggards = all(is_stale(r, cwv) == (r not in eligible) for r in reps)
    print("  the session policy excludes exactly the lagging replicas = %s" % session_excludes_laggards)

    session_has_a_replica = len(eligible) > 0
    print("  at least one replica can serve the session read = %s (%s)"
          % (session_has_a_replica, [r["id"] for r in eligible]))

    ok = (some_replica_lags and naive_can_read_stale and session_never_stale
          and session_excludes_laggards and session_has_a_replica)
    print("-" * 120)
    print("SELF-TEST %s  some_replica_lags=%s  naive_can_read_stale=%s  session_never_stale=%s  session_excludes_laggards=%s  session_has_a_replica=%s"
          % ("PASS" if ok else "FAIL", some_replica_lags, naive_can_read_stale,
             session_never_stale, session_excludes_laggards, session_has_a_replica))
    return ok


def main():
    p = argparse.ArgumentParser(description="Read-your-writes: give a client read-your-writes by pinning its last-write version in a session token and routing each read only to a replica whose version is at least that token -- because a naive any-replica read can hit a lagging replica and return the client's own stale write, and a session token fixes it per client without forcing every read through a quorum.")
    p.add_argument("--replicas", action="store_true")
    p.add_argument("--reads", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("client_write_version=%d  replicas=%d  file=%s  (the versions are a fixture)"
          % (data["client_write_version"], len(data["replicas"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.replicas:
        replicas_view(data)
    elif args.reads:
        reads_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
