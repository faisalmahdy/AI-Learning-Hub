"""Trip a circuit breaker after repeated failures -- or every request keeps hammering a dead dependency.

When a downstream dependency goes down, every call to it times out. A service with no protection keeps
sending requests into that timeout: each one ties up a worker for the full timeout, the workers all
pile up waiting on a dependency that cannot answer, and the load you keep throwing at it stops it from
recovering. A local outage becomes a total one -- the classic metastable failure.

A circuit breaker cuts the feedback loop. It watches for consecutive failures and, once they cross a
threshold, trips OPEN: subsequent requests fail immediately without calling downstream at all, so no
worker blocks and no load reaches the sick dependency. After a cooldown it goes HALF_OPEN and lets one
probe through; if the probe succeeds the dependency is back and the breaker closes, if it fails the
breaker re-opens for another cooldown. The breaker trades a burst of fast, honest failures during the
outage for not making the outage worse -- and it notices recovery on the very first probe that gets
through.

On this fixture the downstream is down for the first 10 requests and up for the last 10. Without a
breaker all 20 requests call downstream and the 10 outage calls each burn a 30-unit timeout, for 310
units of wasted work. With a breaker only 4 requests reach the sick dependency (the 3 that trip it plus
one probe), the rest fast-fail for free, and it still serves all 10 requests after recovery -- 130
units total. This runs both and counts calls, cost, and fast-failures.

  --stream     the request stream, the outage window, and the breaker parameters
  --run        the per-request trace under no-breaker vs breaker, with running cost
  --check      the breaker makes fewer downstream calls and wastes less work, and still recovers

The outage window and breaker parameters are the fixture; every call and cost is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "stream.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def downstream_up(i, data):
    """Is the dependency up at request i? Down before recover_at, up after."""
    return i >= data["recover_at"]


# ------------------------------------------------------------- no breaker vs breaker

def run_no_breaker(data):
    """Send every request to downstream, no matter how many have just failed."""
    calls, cost, log = 0, 0, []
    for i in range(data["requests"]):
        up = downstream_up(i, data)
        calls += 1
        cost += data["ok_cost"] if up else data["timeout_cost"]
        log.append((i, "CLOSED", "ok" if up else "TIMEOUT", cost))
    return calls, cost, 0, log


def run_breaker(data):
    """CLOSED -> OPEN after fail_threshold failures; OPEN fast-fails; HALF_OPEN probes to recover."""
    state, fails, opened_at = "CLOSED", 0, None
    calls, cost, fast_failed, log = 0, 0, 0, []
    for i in range(data["requests"]):
        if state == "OPEN":
            if i - opened_at < data["cooldown"]:
                fast_failed += 1
                log.append((i, "OPEN", "fast-fail", cost))
                continue
            state = "HALF_OPEN"  # cooldown elapsed: let one probe through
        probing = state == "HALF_OPEN"
        # CLOSED or HALF_OPEN: actually call downstream
        up = downstream_up(i, data)
        calls += 1
        cost += data["ok_cost"] if up else data["timeout_cost"]
        if up:
            state, fails = "CLOSED", 0
            log.append((i, "probe->CLOSED" if probing else "CLOSED", "ok", cost))
        else:
            fails += 1
            if probing or fails >= data["fail_threshold"]:
                state, opened_at = "OPEN", i
            log.append((i, "probe->OPEN" if probing else state, "TIMEOUT", cost))
    return calls, cost, fast_failed, log


def outage_calls(log, data):
    """How many downstream calls landed during the outage (the load put on the sick dependency)."""
    return sum(1 for row in log if row[0] < data["recover_at"] and row[2] == "TIMEOUT")


def served_after_recovery(log, data):
    """How many post-recovery requests were served successfully."""
    return sum(1 for row in log if row[0] >= data["recover_at"] and row[2] == "ok")


# ----------------------------------------------------------------- printing

def stream_view(data):
    print("STREAM — %d requests; downstream down for [0,%d), up after"
          % (data["requests"], data["recover_at"]))
    print("-" * 54)
    print("  fail_threshold=%d  cooldown=%d  timeout_cost=%d  ok_cost=%d"
          % (data["fail_threshold"], data["cooldown"], data["timeout_cost"], data["ok_cost"]))
    print("  requests 0..%d time out; %d..%d succeed."
          % (data["recover_at"] - 1, data["recover_at"], data["requests"] - 1))


def run_view(data):
    cn, costn, _, logn = run_no_breaker(data)
    cb, costb, ff, logb = run_breaker(data)
    print("RUN — per-request outcome, no-breaker vs breaker")
    print("-" * 60)
    print("  req   no-breaker            breaker")
    for i in range(data["requests"]):
        rn = logn[i]
        rb = logb[i]
        print("  %2d    %-18s   %-18s" % (i, rn[2], "%s (%s)" % (rb[2], rb[1])))
    print("-" * 60)
    print("  no-breaker: %d calls, %d cost.  breaker: %d calls, %d cost, %d fast-failed."
          % (cn, costn, cb, costb, ff))


def check(data):
    print("SELF-TEST — the breaker makes fewer downstream calls and wastes less work, and still recovers")
    print("-" * 88)
    cn, costn, _, logn = run_no_breaker(data)
    cb, costb, ff, logb = run_breaker(data)

    fewer_calls = cb < cn
    print("  the breaker calls downstream fewer times = %s (%d vs %d)" % (fewer_calls, cb, cn))

    sheds_outage_load = outage_calls(logb, data) < outage_calls(logn, data)
    print("  it sheds load on the sick dependency during the outage = %s (%d vs %d calls)"
          % (sheds_outage_load, outage_calls(logb, data), outage_calls(logn, data)))

    wastes_less = costb < costn
    print("  it wastes less total work = %s (cost %d vs %d)" % (wastes_less, costb, costn))

    recovers = served_after_recovery(logb, data) == data["requests"] - data["recover_at"]
    print("  it still serves every request after recovery = %s (%d of %d)"
          % (recovers, served_after_recovery(logb, data), data["requests"] - data["recover_at"]))

    ok = fewer_calls and sheds_outage_load and wastes_less and recovers
    print("-" * 88)
    print("SELF-TEST %s  fewer_calls=%s  sheds_outage_load=%s  wastes_less=%s  recovers=%s"
          % ("PASS" if ok else "FAIL", fewer_calls, sheds_outage_load, wastes_less, recovers))
    return ok


def main():
    p = argparse.ArgumentParser(description="Trip a circuit breaker after repeated failures to fail fast.")
    p.add_argument("--stream", action="store_true")
    p.add_argument("--run", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("requests=%d  recover_at=%d  fail_threshold=%d  cooldown=%d  file=%s  (the outage is a fixture)"
          % (data["requests"], data["recover_at"], data["fail_threshold"], data["cooldown"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.stream:
        stream_view(data)
    elif args.run:
        run_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
