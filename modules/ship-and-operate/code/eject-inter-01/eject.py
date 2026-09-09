"""Eject a consistently-failing replica from the pool -- a load balancer that keeps routing to a dead host bleeds 1/N forever.

A load balancer spreads requests across a pool of identical backend replicas, and its default behavior is to keep every
replica in rotation and send each one its fair share. That is exactly right when all replicas are healthy. It becomes a
steady, low-grade outage the moment ONE replica goes bad -- a dead disk, a corrupted deploy, a wedged process, an
out-of-memory loop -- because the balancer does not know the replica is bad. It keeps sending it one of every N requests,
and every one of those requests fails or times out. With four replicas, a fifth of all traffic (one in four) that happens
to land on the dead host errors, indefinitely, and no per-request retry fully hides it because the balancer will cheerfully
route the retry to the same dead host again. The pool is mostly healthy, so nothing trips a whole-dependency alarm; the
service just quietly fails a fixed fraction of requests forever.

Passive outlier detection fixes this at the balancer: watch each replica's results, and when one accumulates enough
consecutive failures to be clearly an outlier (not a random blip), EJECT it -- remove it from the rotation for a while --
so its share of traffic is rerouted to the healthy replicas. The failing host now takes zero traffic instead of its 1/N,
and the pool's success rate jumps back to what the healthy replicas can serve. This is distinct from a circuit breaker,
which stops calling an entire dependency when the dependency as a whole is failing; ejection operates one level down, INSIDE
a healthy dependency, removing the single bad instance while keeping the rest of the pool serving. A breaker would either
stay closed (the dependency is mostly fine) or open (cutting off the good replicas too); ejection is the per-host surgery
the breaker's per-dependency switch cannot do.

The eject is provisional: the host is put back after a cooldown (and re-ejected, for longer, if it fails again), because
the goal is to route around a bad instance without permanently shrinking the pool. The threshold is the usual trade-off --
too low and a transient blip ejects a healthy host and reduces capacity; too high and the bad host bleeds traffic longer
before removal.

The rule: a load balancer must detect a consistently-failing replica and eject it from the pool, rerouting its share to
the healthy hosts, because a balancer that keeps a dead replica in rotation sends it a fixed 1/N of all traffic to fail
indefinitely -- ejection is per-host isolation inside a healthy dependency, which a per-dependency circuit breaker cannot
provide.

On this fixture four replicas serve 24 round-robin requests and h2 is dead. Without ejection, h2 is hit every 4th request
-- 6 failures across the run, and it would keep failing forever. With ejection (threshold 3), h2 fails its first three
turns, is ejected, and its remaining three turns are rerouted to healthy hosts -- 3 failures total, then none. This
computes both.

  --route    the per-request host and result, without ejection vs with ejection, and each run's success/failure totals
  --hosts    per-host tallies: h2 is the sole culprit; ejection isolates it and drops its traffic to zero after the threshold
  --check    without ejection the bad host keeps failing 1/N of traffic; with ejection failures are capped and rerouted

hosts, bad_host, requests, and threshold are the fixture; every route, result, and ejection is computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "eject.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def run(hosts, bad_host, requests, threshold, eject):
    """Route requests round-robin. If eject is on, remove a host after `threshold` consecutive failures and reroute."""
    consecutive_fail = {h: 0 for h in hosts}
    ejected = set()
    rr = 0
    log = []
    for r in range(requests):
        picked = None
        for _ in range(len(hosts)):  # advance the rotation, skipping ejected hosts (rerouting)
            cand = hosts[rr % len(hosts)]
            rr += 1
            if eject and cand in ejected:
                continue
            picked = cand
            break
        ok = picked != bad_host
        if ok:
            consecutive_fail[picked] = 0
            log.append({"req": r, "host": picked, "result": "ok"})
        else:
            consecutive_fail[picked] += 1
            log.append({"req": r, "host": picked, "result": "FAIL"})
            if eject and consecutive_fail[picked] >= threshold:
                ejected.add(picked)
    return log, ejected


def totals(log):
    ok = sum(1 for e in log if e["result"] == "ok")
    fail = sum(1 for e in log if e["result"] == "FAIL")
    return ok, fail


# ----------------------------------------------------------------- printing

def route_view(data):
    hosts, bad, reqs, thr = data["hosts"], data["bad_host"], data["requests"], data["eject_threshold"]
    no_log, _ = run(hosts, bad, reqs, thr, eject=False)
    ej_log, ejected = run(hosts, bad, reqs, thr, eject=True)
    print("ROUTE — %d requests round-robin over %s; %s is dead; eject after %d consecutive fails" % (reqs, hosts, bad, thr))
    print("-" * 62)
    print("  req   no-eject          with-eject")
    for i in range(reqs):
        n, e = no_log[i], ej_log[i]
        print("  %-4d  %s %-14s %s %s" % (i, n["host"], n["result"], e["host"], e["result"]))
    no_ok, no_fail = totals(no_log)
    ej_ok, ej_fail = totals(ej_log)
    print("-" * 62)
    print("  no-eject:   %d ok, %d FAIL  (%s never removed)" % (no_ok, no_fail, bad))
    print("  with-eject: %d ok, %d FAIL  (ejected: %s)" % (ej_ok, ej_fail, sorted(ejected)))


def hosts_view(data):
    hosts, bad, reqs, thr = data["hosts"], data["bad_host"], data["requests"], data["eject_threshold"]
    no_log, _ = run(hosts, bad, reqs, thr, eject=False)
    ej_log, ejected = run(hosts, bad, reqs, thr, eject=True)
    print("HOSTS — requests served per host, without ejection vs with ejection")
    print("-" * 66)
    print("  host   no-eject (ok/fail)   with-eject (ok/fail)")
    for h in hosts:
        n_ok = sum(1 for e in no_log if e["host"] == h and e["result"] == "ok")
        n_f = sum(1 for e in no_log if e["host"] == h and e["result"] == "FAIL")
        e_ok = sum(1 for e in ej_log if e["host"] == h and e["result"] == "ok")
        e_f = sum(1 for e in ej_log if e["host"] == h and e["result"] == "FAIL")
        tag = "  <- dead, ejected" if h == bad else ""
        print("  %-5s  %d / %-16d %d / %d%s" % (h, n_ok, n_f, e_ok, e_f, tag))
    print("-" * 66)
    print("  ejection drops %s's traffic to zero after %d fails; healthy hosts absorb its share." % (bad, thr))


def check(data):
    print("SELF-TEST — without ejection the bad host keeps failing 1/N of traffic; with ejection failures are capped and rerouted")
    print("-" * 118)
    hosts, bad, reqs, thr = data["hosts"], data["bad_host"], data["requests"], data["eject_threshold"]
    no_log, _ = run(hosts, bad, reqs, thr, eject=False)
    ej_log, ejected = run(hosts, bad, reqs, thr, eject=True)
    no_ok, no_fail = totals(no_log)
    ej_ok, ej_fail = totals(ej_log)

    no_eject_bleeds = no_fail == reqs // len(hosts)
    print("  no-eject fails 1/%d of traffic (%d of %d) = %s" % (len(hosts), no_fail, reqs, no_eject_bleeds))

    eject_caps_failures = ej_fail == thr
    print("  with-eject caps failures at the threshold = %s (%d failures, threshold %d)" % (eject_caps_failures, ej_fail, thr))

    bad_host_ejected = bad in ejected
    print("  the bad host was ejected = %s (ejected: %s)" % (bad_host_ejected, sorted(ejected)))

    fail_idx_after_eject = [e["req"] for e in ej_log if e["result"] == "FAIL"]
    bad_reaches_zero = all(e["host"] != bad for e in ej_log if e["req"] > max(fail_idx_after_eject))
    print("  the bad host takes no traffic after ejection = %s (last failure at req %d)" % (bad_reaches_zero, max(fail_idx_after_eject)))

    fewer_failures = ej_fail < no_fail
    print("  ejection reduces total failures = %s (%d vs %d)" % (fewer_failures, ej_fail, no_fail))

    ok = no_eject_bleeds and eject_caps_failures and bad_host_ejected and bad_reaches_zero and fewer_failures
    print("-" * 118)
    print("SELF-TEST %s  no_eject_bleeds=%s  eject_caps_failures=%s  bad_host_ejected=%s  bad_reaches_zero=%s  fewer_failures=%s"
          % ("PASS" if ok else "FAIL", no_eject_bleeds, eject_caps_failures, bad_host_ejected, bad_reaches_zero, fewer_failures))
    return ok


def main():
    p = argparse.ArgumentParser(description="Outlier ejection: a load balancer must detect a consistently-failing replica and eject it from the pool, rerouting its share to the healthy hosts, because a balancer that keeps a dead replica in rotation sends it a fixed 1/N of all traffic to fail indefinitely -- ejection is per-host isolation inside a healthy dependency, which a per-dependency circuit breaker cannot provide.")
    p.add_argument("--route", action="store_true")
    p.add_argument("--hosts", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("hosts=%s  bad_host=%s  requests=%d  eject_threshold=%d  file=%s  (the pool, bad host, and threshold are a fixture)"
          % (data["hosts"], data["bad_host"], data["requests"], data["eject_threshold"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.route:
        route_view(data)
    elif args.hosts:
        hosts_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
