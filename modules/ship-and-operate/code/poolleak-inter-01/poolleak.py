"""Release a pooled connection on every path -- in a finally block or a context manager -- not only when the work succeeds, or a failure on one code path leaks a connection, the pool bleeds to exhaustion, and healthy requests on every path are rejected.

A connection pool hands out a fixed number of reusable connections. Each request acquires one, does its work, and must return it so the next request can use it. The whole point of the pool is that connections are borrowed and given back; a connection that is borrowed and not given back is gone from the pool for good.

The bug is releasing only on success: the code acquires the connection, runs the work, and then releases -- but if the work raises before reaching the release line, control jumps past it and the connection is never returned. It is leaked. One leaked connection is invisible; the pool just has one fewer. But every request that fails on that path leaks another, so the available count ratchets downward, one per failure, and never recovers.

The consequence is delayed and misdirected. Nothing breaks at the first leak, or the second. Then the pool's available count hits zero, and the next request -- however healthy -- cannot acquire a connection and is rejected. A handful of failures on one code path has become a total outage on all paths, and the symptom (healthy requests failing for lack of a connection) points nowhere near the cause (an unreleased connection on an unrelated error path).

The fix is to make release unconditional: put it in a finally block, or borrow the connection with a context manager whose exit returns it, so the connection goes back to the pool whether the work returned or threw. Then a failing request fails alone, its connection reclaimed, and the pool never bleeds.

On this fixture a pool of 3 serves 7 requests, 3 of which error. The leaky caller releases only on success, leaks all 3 error connections, drains the pool to zero, and rejects a healthy request; the safe caller releases in finally, leaks nothing, and rejects nobody. This computes both.

  --leaky   the available-connection count over time when release happens only on success
  --safe    the same sequence when release happens in a finally block
  --check   the leaky caller bleeds the pool and rejects a healthy request; the finally caller keeps the pool whole

pool_size and the request sequence are the fixture; the available count over time, the leaked count, and the rejected requests under each caller are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "poolleak.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


class Pool:
    """A fixed pool of reusable connections."""

    def __init__(self, size):
        self.size = size
        self.available = size

    def acquire(self):
        """Take a connection, or return False if the pool is exhausted."""
        if self.available <= 0:
            return False
        self.available -= 1
        return True

    def release(self):
        """Return a connection to the pool."""
        self.available += 1


def do_work(request):
    """Simulate the request; raise if this request is flagged to error."""
    if request["error"]:
        raise RuntimeError("work failed for %s" % request["id"])


def leaky_serve(pool, request):
    """BUG: release only after the work returns -- an exception skips the release and leaks the connection."""
    if not pool.acquire():
        return "rejected"
    try:
        do_work(request)
    except RuntimeError:
        return "error-leaked"    # returned without releasing: the connection is lost
    pool.release()
    return "ok-released"


def safe_serve(pool, request):
    """FIX: release in finally -- the connection returns whether the work returned or threw."""
    if not pool.acquire():
        return "rejected"
    try:
        do_work(request)
        return "ok-released"
    except RuntimeError:
        return "error-released"
    finally:
        pool.release()


def run(pool_size, requests, serve):
    """Serve the sequence with the given caller, tracking the timeline and outcomes."""
    pool = Pool(pool_size)
    timeline, rejected, leaked = [], [], 0
    for r in requests:
        outcome = serve(pool, r)
        if outcome == "rejected":
            rejected.append(r["id"])
        elif outcome == "error-leaked":
            leaked += 1
        timeline.append((r["id"], outcome, pool.available))
    return {"available": pool.available, "leaked": leaked, "rejected": rejected, "timeline": timeline}


# ----------------------------------------------------------------- printing

def _print_run(title, result, pool_size, note):
    print(title)
    print("-" * 60)
    print("  request  outcome          available after")
    for rid, outcome, avail in result["timeline"]:
        print("  %-7s  %-15s  %d" % (rid, outcome, avail))
    print("-" * 60)
    print("  leaked=%d  rejected=%s  available=%d/%d" % (result["leaked"], result["rejected"], result["available"], pool_size))
    print("  %s" % note)


def leaky_view(data):
    r = run(data["pool_size"], data["requests"], leaky_serve)
    _print_run("LEAKY — release only on success (the error path skips release)", r, data["pool_size"],
               "every error leaks a connection; the pool drains and then rejects a healthy request")


def safe_view(data):
    r = run(data["pool_size"], data["requests"], safe_serve)
    _print_run("SAFE — release in a finally block (every path returns the connection)", r, data["pool_size"],
               "a failing request fails alone; the pool stays whole")


def check(data):
    print("SELF-TEST — the leaky caller bleeds the pool and rejects a healthy request; the finally caller keeps the pool whole")
    print("-" * 112)
    pool_size, requests = data["pool_size"], data["requests"]
    leaky = run(pool_size, requests, leaky_serve)
    safe = run(pool_size, requests, safe_serve)
    n_errors = sum(1 for r in requests if r["error"])
    err_ids = {r["id"] for r in requests if r["error"]}

    leaky_leaks_every_error = leaky["leaked"] == n_errors
    print("  the leaky caller leaks one connection per error = %s (%d leaked, %d errors)" % (leaky_leaks_every_error, leaky["leaked"], n_errors))

    leaky_exhausts_pool = leaky["available"] == 0
    print("  the leaky caller drains the pool to zero = %s (available %d)" % (leaky_exhausts_pool, leaky["available"]))

    leaky_rejects_healthy = any(rid not in err_ids for rid in leaky["rejected"])
    print("  the leaky caller rejects a healthy request = %s (rejected %s)" % (leaky_rejects_healthy, leaky["rejected"]))

    safe_no_leak = safe["leaked"] == 0 and safe["available"] == pool_size
    print("  the finally caller leaks nothing and keeps the pool full = %s (available %d/%d)" % (safe_no_leak, safe["available"], pool_size))

    safe_no_rejection = len(safe["rejected"]) == 0
    print("  the finally caller rejects no requests = %s" % safe_no_rejection)

    ok = (leaky_leaks_every_error and leaky_exhausts_pool and leaky_rejects_healthy
          and safe_no_leak and safe_no_rejection)
    print("-" * 112)
    print("SELF-TEST %s  leaky_leaks_every_error=%s  leaky_exhausts_pool=%s  leaky_rejects_healthy=%s  safe_no_leak=%s  safe_no_rejection=%s"
          % ("PASS" if ok else "FAIL", leaky_leaks_every_error, leaky_exhausts_pool, leaky_rejects_healthy,
             safe_no_leak, safe_no_rejection))
    return ok


def main():
    p = argparse.ArgumentParser(description="Connection-pool leak: release a pooled connection on every path (a finally block or a context manager), not only on success, because a failure on one code path leaks a connection, the pool bleeds to exhaustion, and healthy requests on every path are then rejected.")
    p.add_argument("--leaky", action="store_true")
    p.add_argument("--safe", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("pool_size=%d  requests=%d  file=%s  (these are a fixture)" % (data["pool_size"], len(data["requests"]), DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.leaky:
        leaky_view(data)
    elif args.safe:
        safe_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
