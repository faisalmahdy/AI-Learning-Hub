"""Alert on the absence of an expected success, not only on errors -- a job that stops running emits no error, so error-based alerting stays silent through the whole outage.

Error-based alerting fires on the presence of a bad thing: an exception, a failed run, a non-2xx status. That is the right shape for a job that runs and fails -- something errors, a rule matches it, an alert goes out. It has one blind spot, and it is a wide one: a job that stops running entirely emits nothing. A crashed cron that never starts, a queue consumer wedged on a lock, a scheduler that skipped the trigger, a broker that quietly stopped delivering -- none of these produce an error event, because nothing ran to produce one. There is no event for an error rule to match, so the alert stays quiet while the job does nothing.

That is the trap: silence reads as health. The dashboards are green, the error rate is zero, the on-call is undisturbed -- precisely because the component is so broken it cannot even fail out loud. The longer it is down, the calmer the error-based monitoring looks, until someone notices downstream that the reports stopped, the data is stale, the queue is backing up.

The fix inverts the question. Instead of watching for an error to appear, watch for a success to be missing: a dead man's switch. Record the time of the last success, and alert when the time since it exceeds the expected run interval plus a margin. Now a job that runs and fails still trips the error rule, and a job that silently dies trips the freshness rule when its next success fails to arrive -- the alert fires on the absence of the heartbeat, which is the only signal a dead component still sends.

On this fixture the job succeeds, errors once (caught by error alerting), succeeds again, then dies silently. Error alerting sees no event after the last success and never fires; the freshness check watches the gap since the last success grow past the interval-plus-margin threshold and fires. This computes both.

  --timeline  the events, the last success time, and the current gap
  --alerts    whether error-based and freshness-based alerting fire during the silent outage
  --check     error alerting catches the errored run but misses the silent death; the freshness check catches it

events, the expected interval, the margin, and the current time are the fixture; the last success, the gap, and each alert's firing are computed. Stdlib only.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "deadman.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def last_success_time(events):
    """The time of the most recent success, or None if there was never one."""
    successes = [e["time"] for e in events if e["outcome"] == "success"]
    return max(successes) if successes else None


def error_alert_fires_after(events, since):
    """Error-based alerting: does any ERROR event occur at or after `since`? Silence emits no event."""
    return any(e["outcome"] == "error" and e["time"] >= since for e in events)


def freshness_gap(events, now):
    """Time since the last success -- the age of the heartbeat."""
    last = last_success_time(events)
    return None if last is None else now - last


def freshness_alert_fires(events, now, interval, margin):
    """Dead man's switch: fire when the gap since the last success exceeds the interval plus a margin."""
    gap = freshness_gap(events, now)
    return gap is not None and gap > interval + margin


# ----------------------------------------------------------------- printing

def timeline_view(data):
    events = data["events"]
    last = last_success_time(events)
    print("TIMELINE — the job's events, and the gap since the last success")
    print("-" * 52)
    for e in events:
        print("  t=%-4d  %s" % (e["time"], e["outcome"]))
    print("  (no events after t=%d -- the job went silent)" % events[-1]["time"])
    print("-" * 52)
    print("  now=%d  last success=%d  gap=%d  (expected interval %d)" % (data["now"], last, data["now"] - last, data["interval"]))


def alerts_view(data):
    events, now, interval, margin = data["events"], data["now"], data["interval"], data["margin"]
    last = last_success_time(events)
    err = error_alert_fires_after(events, last)      # any error since the last success?
    fresh = freshness_alert_fires(events, now, interval, margin)
    print("ALERTS — does each scheme fire during the silent outage after the last success?")
    print("-" * 52)
    print("  error-based    : %s  (looks for an error event after t=%d -- there is none)" % (err, last))
    print("  freshness-based: %s  (gap %d > interval+margin %d)" % (fresh, now - last, interval + margin))
    print("-" * 52)
    print("  error alerting is blind to silence; the freshness check catches the dead job")


def check(data):
    print("SELF-TEST — error alerting catches the errored run but misses the silent death; the freshness check catches it")
    print("-" * 112)
    events, now, interval, margin = data["events"], data["now"], data["interval"], data["margin"]
    last = last_success_time(events)

    error_alert_catches_errors = error_alert_fires_after(events, 0)
    print("  error alerting fires on the run that errored = %s (a real error at some t)" % error_alert_catches_errors)

    gap = freshness_gap(events, now)
    job_died_silently = gap > interval and not error_alert_fires_after(events, last)
    print("  the job went silent after its last success (big gap, no error) = %s (gap %d)" % (job_died_silently, gap))

    error_alert_misses_silence = not error_alert_fires_after(events, last)
    print("  error alerting is silent during the outage = %s (no error event after t=%d)" % (error_alert_misses_silence, last))

    freshness_fires = freshness_alert_fires(events, now, interval, margin)
    print("  the freshness (dead man's switch) alert fires = %s" % freshness_fires)

    gap_is_abnormal = gap > interval + margin
    print("  the gap exceeds the interval plus margin (genuinely late) = %s (%d > %d)" % (gap_is_abnormal, gap, interval + margin))

    ok = (error_alert_catches_errors and job_died_silently and error_alert_misses_silence
          and freshness_fires and gap_is_abnormal)
    print("-" * 112)
    print("SELF-TEST %s  error_alert_catches_errors=%s  job_died_silently=%s  error_alert_misses_silence=%s  freshness_fires=%s  gap_is_abnormal=%s"
          % ("PASS" if ok else "FAIL", error_alert_catches_errors, job_died_silently, error_alert_misses_silence,
             freshness_fires, gap_is_abnormal))
    return ok


def main():
    p = argparse.ArgumentParser(description="Dead man's switch: alert on the absence of an expected success, not only on errors, because a job that stops running emits no error -- so error-based alerting stays silent through the outage while a freshness check on the last success catches it.")
    p.add_argument("--timeline", action="store_true")
    p.add_argument("--alerts", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    data = load()
    print("events=%d  interval=%d  margin=%d  now=%d  file=%s  (these are a fixture)"
          % (len(data["events"]), data["interval"], data["margin"], data["now"], DATA.name))
    print("")

    if args.check:
        return 0 if check(data) else 1
    if args.timeline:
        timeline_view(data)
    elif args.alerts:
        alerts_view(data)
    else:
        p.print_help()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
