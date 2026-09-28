---
id: govern-inter-10
title: Trip a circuit breaker after repeated failures — or every request keeps hammering a dead dependency
topic: orchestration-and-governance
level: intermediate
status: ready
time: 23 min
summary: When a dependency goes down, sending every request into its timeout ties up workers and keeps the dependency from recovering — a local outage becomes total. A circuit breaker trips open after consecutive failures, fast-fails while open, and probes to recover. On a 10-request outage it cuts downstream load from 10 calls to 4 and wasted work from 310 to 130.
eli5: If you keep phoning a shop that never picks up, you waste your whole day on hold and their phone keeps ringing off the hook. A circuit breaker is a rule: after three no-answers, stop calling for a while, then try once to see if they're back. You save your time, and you stop jamming their line so they can recover.
---

## Why this module

The failure this prevents is the one that takes down the whole system after only one piece of it broke.

Picture a service that calls a downstream dependency, and the dependency goes down. Every call now times out — thirty seconds of a worker sitting on its hands waiting for an answer that will never come. With no protection, the service keeps sending: request after request, each one grabbing a worker and holding it for the full timeout. Within seconds every worker is blocked waiting on the dead dependency, so the service can no longer answer even the requests that have nothing to do with it. And all that traffic you keep throwing at the sick dependency is exactly the load that stops it from recovering. A partial outage — one dependency down — has become a total one. This is a metastable failure, and it is one of the most common ways distributed systems die.

The circuit breaker cuts the loop. It is a small state machine wrapped around the call. It counts consecutive failures, and once they cross a threshold it trips open: while open, calls fail immediately without touching the dependency at all. No worker blocks, no load reaches the thing that is struggling. After a cooldown it lets exactly one probe through — half-open — and if that probe succeeds the dependency is back and the breaker closes; if it fails, the breaker re-opens and waits again. The breaker trades a burst of fast, honest failures for not making the outage worse, and it notices recovery on the first probe that gets through.

The instinct it fights is "just retry." Retrying a transient blip is right; retrying a downed dependency, on every request, is how you convert a blip into a collapse. The breaker is the governor that decides when to stop trying.

We will run one outage two ways. Without a breaker, all twenty requests call downstream and the ten during the outage each burn a thirty-unit timeout — 310 units of wasted work, ten full calls piled on a dependency that cannot answer. With a breaker, only four requests reach the sick dependency, the rest fail for free, and it still serves every request after recovery — 130 units total.

**Sending every request into a dead dependency's timeout is how one outage becomes total; the breaker fails fast so workers stay free and the dependency gets room to recover.**

## Concepts

The breaker has three states and the transitions between them are the whole design. Closed is normal: calls go through, and a running count of consecutive failures is kept. When that count reaches the failure threshold, the breaker trips to open. Open is the protective state: no call is made, every request fails instantly, and a timer counts down the cooldown. When the cooldown elapses, the breaker moves to half-open and permits a single probe call. If the probe succeeds, the dependency has recovered and the breaker returns to closed with the failure count reset. If the probe fails, the breaker snaps back to open for another full cooldown.

The key insight is what each state optimizes. Closed optimizes for normal operation — no overhead, calls flow. Open optimizes for the outage — it sheds load, both from your own workers, who no longer block, and from the dependency, which no longer receives traffic it cannot handle. Half-open optimizes for recovery detection — it spends exactly one request to ask "are you back?" rather than reopening the floodgates and risking a re-collapse. That single-probe discipline matters: a naive "cooldown then resume all traffic" would slam a just-barely-recovered dependency and knock it down again. The breaker recovers by testing, not by hoping.

Three parameters tune it, and each is a real trade. The failure threshold decides how many failures you tolerate before tripping — too low and a couple of unrelated blips open the circuit needlessly; too high and you block a lot of workers before protection kicks in. The cooldown decides how long you stay open — too short and you probe a still-sick dependency too often, adding load; too long and you stay dark well after it recovered, failing requests you could have served. The half-open probe count — one, here — decides how cautiously you test recovery. These are the knobs; the states are the machine.

What the breaker does not do is make failed requests succeed. During the outage, requests fail either way — the honest question is not "fail or not" but "fail slow and destructively, or fast and cheaply." The breaker chooses fast and cheap, which keeps the blast radius small and hands the dependency the quiet it needs to come back.

**The breaker cannot turn an outage into success; it turns slow, load-piling failures into fast, free ones, and tests for recovery with a single probe instead of a flood.**

## Worked example

The fixture is an outage and a set of breaker parameters — the outage window is what the breaker has to survive.

```json filename=modules/orchestration-and-governance/code/govern-inter-10/stream.json:7-12 COMPLETE
  "requests": 20,
  "recover_at": 10,
  "fail_threshold": 3,
  "cooldown": 4,
  "timeout_cost": 30,
```

Twenty requests. The dependency is down for the first ten and recovers at request 10. Three consecutive failures trip the breaker; while open it waits four requests before probing; a timed-out call costs thirty units, a successful one costs one.

```text filename=modules/orchestration-and-governance/code/govern-inter-10/breaker.py --stream
STREAM — 20 requests; downstream down for [0,10), up after
------------------------------------------------------
  fail_threshold=3  cooldown=4  timeout_cost=30  ok_cost=1
  requests 0..9 time out; 10..19 succeed.
```

The no-breaker policy is the naive one: send everything, always.

```python filename=modules/orchestration-and-governance/code/govern-inter-10/breaker.py:48-56 COMPLETE
def run_no_breaker(data):
    """Send every request to downstream, no matter how many have just failed."""
    calls, cost, log = 0, 0, []
    for i in range(data["requests"]):
        up = downstream_up(i, data)
        calls += 1
        cost += data["ok_cost"] if up else data["timeout_cost"]
        log.append((i, "CLOSED", "ok" if up else "TIMEOUT", cost))
    return calls, cost, 0, log
```

The breaker wraps the same call in the state machine.

```python filename=modules/orchestration-and-governance/code/govern-inter-10/breaker.py:59-83 COMPLETE
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
```

Predict the breaker's path before running. Requests 0, 1, 2 fail and trip it open at 2. Requests 3, 4, 5 fast-fail during cooldown. Request 6 is the probe — still down — so it fails and re-opens. Requests 7, 8, 9 fast-fail. Request 10 is the next probe, and the dependency is back, so it closes. Now run both.

<svg role="img" aria-label="The circuit breaker state machine: closed trips to open on failures, open goes to half-open after cooldown, half-open closes on a successful probe or reopens on a failed one" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <rect x="30" y="70" width="90" height="40" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="52" y="94" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">CLOSED</text>
  <rect x="185" y="70" width="90" height="40" fill="var(--s2)" stroke="var(--line)"/><text x="205" y="94" font-family="var(--mono)" font-size="11" fill="var(--ink)">OPEN</text>
  <rect x="340" y="70" width="100" height="40" fill="var(--acc-soft)" stroke="var(--acc-line)"/><text x="352" y="94" font-family="var(--mono)" font-size="11" fill="var(--acc-ink)">HALF-OPEN</text>
  <line x1="120" y1="90" x2="185" y2="90" stroke="var(--ink)"/><text x="120" y="60" font-family="var(--mono)" font-size="9" fill="var(--muted)">3 fails</text>
  <line x1="275" y1="90" x2="340" y2="90" stroke="var(--ink)"/><text x="280" y="60" font-family="var(--mono)" font-size="9" fill="var(--muted)">cooldown</text>
  <path d="M390 110 Q400 150 235 150 Q75 150 75 110" fill="none" stroke="var(--acc-ink)"/><text x="200" y="168" font-family="var(--mono)" font-size="9" fill="var(--acc-ink)">probe ok → close</text>
  <path d="M390 70 Q390 30 300 30 Q230 30 230 70" fill="none" stroke="var(--s2)"/><text x="255" y="24" font-family="var(--mono)" font-size="9" fill="var(--s2)">probe fails → reopen</text>
</svg>
^ Closed trips open after three failures, open waits out the cooldown then probes half-open, and the probe either closes the breaker or sends it back to open.

```text filename=modules/orchestration-and-governance/code/govern-inter-10/breaker.py --run
  req   no-breaker            breaker
   0    TIMEOUT              TIMEOUT (CLOSED)
   1    TIMEOUT              TIMEOUT (CLOSED)
   2    TIMEOUT              TIMEOUT (OPEN)
   3    TIMEOUT              fast-fail (OPEN)
   4    TIMEOUT              fast-fail (OPEN)
   5    TIMEOUT              fast-fail (OPEN)
   6    TIMEOUT              TIMEOUT (probe->OPEN)
   7    TIMEOUT              fast-fail (OPEN)
   8    TIMEOUT              fast-fail (OPEN)
   9    TIMEOUT              fast-fail (OPEN)
  10    ok                   ok (probe->CLOSED)
  11    ok                   ok (CLOSED)
  ...
  19    ok                   ok (CLOSED)
----------------------------------------------------------
  no-breaker: 20 calls, 310 cost.  breaker: 14 calls, 130 cost, 6 fast-failed.
```

The trace matches the prediction exactly. Under no-breaker, all ten outage requests time out — ten full thirty-unit calls piled on the dead dependency. Under the breaker, only requests 0, 1, 2, and the probe at 6 actually call downstream during the outage; requests 3, 4, 5, 7, 8, 9 fast-fail for zero cost. Then request 10's probe finds the dependency back and closes the breaker, and 11 through 19 serve normally. The load the breaker put on the sick dependency during its outage is exactly this count.

<svg role="img" aria-label="Timeline of 20 requests: the first 10 are the outage; the breaker sends real calls at 0,1,2 and probes at 6 and 10, fast-fails the rest, and serves 10 onward" viewBox="0 0 460 150" width="460" height="150">
  <rect x="0" y="0" width="460" height="150" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="20" font-family="var(--mono)" font-size="10" fill="var(--muted)">outage: requests 0–9</text>
  <line x1="20" y1="26" x2="216" y2="26" stroke="var(--s2)"/>
  <text x="250" y="20" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">recovered: 10–19</text>
  <line x1="222" y1="26" x2="440" y2="26" stroke="var(--acc-line)"/>
  <g font-family="var(--mono)" font-size="8">
    <rect x="20" y="60" width="18" height="18" fill="var(--s2)" stroke="var(--line)"/><text x="24" y="73" fill="var(--ink)">T</text>
    <rect x="40" y="60" width="18" height="18" fill="var(--s2)" stroke="var(--line)"/><text x="44" y="73" fill="var(--ink)">T</text>
    <rect x="60" y="60" width="18" height="18" fill="var(--s2)" stroke="var(--line)"/><text x="64" y="73" fill="var(--ink)">T</text>
    <rect x="80" y="60" width="18" height="18" fill="var(--panel)" stroke="var(--line)"/><text x="83" y="73" fill="var(--muted)">·</text>
    <rect x="100" y="60" width="18" height="18" fill="var(--panel)" stroke="var(--line)"/><text x="103" y="73" fill="var(--muted)">·</text>
    <rect x="120" y="60" width="18" height="18" fill="var(--panel)" stroke="var(--line)"/><text x="123" y="73" fill="var(--muted)">·</text>
    <rect x="140" y="60" width="18" height="18" fill="var(--s2)" stroke="var(--line)"/><text x="143" y="73" fill="var(--ink)">P</text>
    <rect x="160" y="60" width="18" height="18" fill="var(--panel)" stroke="var(--line)"/><text x="163" y="73" fill="var(--muted)">·</text>
    <rect x="180" y="60" width="18" height="18" fill="var(--panel)" stroke="var(--line)"/><text x="183" y="73" fill="var(--muted)">·</text>
    <rect x="200" y="60" width="18" height="18" fill="var(--panel)" stroke="var(--line)"/><text x="203" y="73" fill="var(--muted)">·</text>
    <rect x="222" y="60" width="18" height="18" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="226" y="73" fill="var(--acc-ink)">P</text>
    <rect x="242" y="60" width="18" height="18" fill="var(--acc-soft)" stroke="var(--acc-ink)"/><text x="246" y="73" fill="var(--acc-ink)">✓</text>
    <rect x="262" y="60" width="178" height="18" fill="var(--acc-soft)" stroke="var(--acc-ink)"/><text x="330" y="73" fill="var(--acc-ink)">✓ served 12–19</text>
  </g>
  <text x="20" y="100" font-family="var(--mono)" font-size="9" fill="var(--muted)">T = real call, times out   P = probe   · = fast-fail (free)   ✓ = served</text>
  <text x="20" y="120" font-family="var(--mono)" font-size="9" fill="var(--muted)">4 real calls hit the sick dependency; 6 requests fast-fail; recovery caught at the first probe after 10</text>
</svg>
^ Only four requests touch the dependency during the outage — the three that trip the breaker and the probe at 6 — and the probe at 10 catches recovery immediately.

```python filename=modules/orchestration-and-governance/code/govern-inter-10/breaker.py:86-88 COMPLETE
def outage_calls(log, data):
    """How many downstream calls landed during the outage (the load put on the sick dependency)."""
    return sum(1 for row in log if row[0] < data["recover_at"] and row[2] == "TIMEOUT")
```

<svg role="img" aria-label="Two bar comparisons: total wasted cost 310 without breaker versus 130 with, and outage calls 10 without versus 4 with" viewBox="0 0 460 180" width="460" height="180">
  <rect x="0" y="0" width="460" height="180" fill="var(--panel)" stroke="var(--line)"/>
  <text x="16" y="22" font-family="var(--mono)" font-size="11" fill="var(--muted)">wasted cost</text>
  <rect x="90" y="30" width="200" height="20" fill="var(--s2)" stroke="var(--line)"/><text x="296" y="46" font-family="var(--mono)" font-size="10" fill="var(--ink)">310 no-breaker</text>
  <rect x="90" y="56" width="84" height="20" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="180" y="72" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">130 breaker</text>
  <text x="16" y="112" font-family="var(--mono)" font-size="11" fill="var(--muted)">calls onto the sick dependency</text>
  <rect x="90" y="120" width="200" height="20" fill="var(--s2)" stroke="var(--line)"/><text x="296" y="136" font-family="var(--mono)" font-size="10" fill="var(--ink)">10 no-breaker</text>
  <rect x="90" y="146" width="80" height="20" fill="var(--acc-line)" stroke="var(--acc-ink)"/><text x="176" y="162" font-family="var(--mono)" font-size="10" fill="var(--acc-ink)">4 breaker</text>
</svg>
^ The breaker more than halves the wasted work and cuts the load on the struggling dependency from ten calls to four — while still serving every post-recovery request.

## Build

Reproduce the trace and the totals. Pure standard library, deterministic outage, so 310 versus 130 and 20 versus 14 calls come out exactly.

Run `--stream` for the setup, `--run` for the per-request trace, `--check` for the gate. The self-test checks the two wins — fewer calls, less waste — plus the two facts that keep them honest: that the shed load is specifically on the sick dependency, and that the breaker still serves everything after recovery.

```python filename=modules/orchestration-and-governance/code/govern-inter-10/breaker.py:129-136 COMPLETE
    fewer_calls = cb < cn
    print("  the breaker calls downstream fewer times = %s (%d vs %d)" % (fewer_calls, cb, cn))

    sheds_outage_load = outage_calls(logb, data) < outage_calls(logn, data)
    print("  it sheds load on the sick dependency during the outage = %s (%d vs %d calls)"
          % (sheds_outage_load, outage_calls(logb, data), outage_calls(logn, data)))

    wastes_less = costb < costn
    print("  it wastes less total work = %s (cost %d vs %d)" % (wastes_less, costb, costn))
```

The `recovers` flag, checked just below, is the one that keeps the breaker honest. It is trivially easy to write a "breaker" that reduces load — just fail everything forever. The whole point is to shed load during the outage *and* resume serving the moment the dependency is back, and `recovers` demands the breaker serve all ten post-recovery requests. Load reduction without recovery is not a breaker, it is an outage of your own making. Here is the full gate.

```text filename=modules/orchestration-and-governance/code/govern-inter-10/breaker.py --check
SELF-TEST — the breaker makes fewer downstream calls and wastes less work, and still recovers
----------------------------------------------------------------------------------------
  the breaker calls downstream fewer times = True (14 vs 20)
  it sheds load on the sick dependency during the outage = True (4 vs 10 calls)
  it wastes less total work = True (cost 130 vs 310)
  it still serves every request after recovery = True (10 of 10)
----------------------------------------------------------------------------------------
SELF-TEST PASS  fewer_calls=True  sheds_outage_load=True  wastes_less=True  recovers=True
```

Four True flags. Fewer_calls: 14 beats 20. Sheds_outage_load: 4 outage calls instead of 10, the load taken off the sick dependency. Wastes_less: 130 units instead of 310. Recovers: all 10 post-recovery requests served. The last two together are the real claim — cheaper during the outage, and no slower to recover once the dependency returns.

**A breaker that only sheds load is easy and useless; the test insists it also serves everything after recovery, which is what separates protection from a self-inflicted outage.**

## Definition of done

You are done when you reproduce the trace and can walk the state machine from memory.

Concretely: `--run` shows the breaker tripping at request 2, probing and re-opening at 6, and closing at 10; `--check` prints PASS with 14 calls versus 20 and 130 cost versus 310. You can name the three states and every transition between them, and say what each state optimizes: closed for normal flow, open for shedding load, half-open for cheap recovery detection. You can explain why the single probe matters — resuming all traffic at once risks re-collapsing a fragile dependency — and you can describe the metastable failure the breaker prevents: workers all blocked on timeouts, load piling on a dependency that then cannot recover.

The habit to carry: any call to a dependency that can fail should be wrapped in a breaker, and the breaker's job is not to make the call succeed but to fail fast when the dependency is down and to test cheaply for its return.

## Boss fight

The instructive failure is the retry that turns a five-minute blip into a two-hour outage.

A dependency has a brief hiccup. The calling service, with no breaker but a helpful retry policy, retries every failed request three times. Now each user request generates three downstream calls, all timing out, all holding workers. The workers saturate, the retry queue backs up, and the extra 3× load lands on the dependency exactly as it is trying to recover — so it stays down. The hiccup would have cleared in thirty seconds; the retry storm keeps it down for hours, and the postmortem says "increased load prevented recovery." A breaker would have tripped after three failures and let the dependency breathe. This is why retries and breakers are complements, not alternatives: retry the transient, break on the sustained.

Your turn, two moves. First, tune the cooldown and watch the recovery-versus-load trade. Shorten the cooldown to 2 and predict: the breaker probes more often during the outage, so it makes more outage calls (more load on the sick dependency) but would notice a recovery sooner. Lengthen it to 8 and predict the opposite: fewer probes, less load, but if the dependency recovered early in the cooldown the breaker stays dark and fails requests it could have served. Run both and read `outage_calls` and the recovery request off the trace. Second, break the `recovers` guarantee to see why it is tested. Make the half-open probe never close the breaker — treat every probe as a failure — and predict: `fewer_calls`, `sheds_outage_load`, and `wastes_less` all still pass (you shed even more load), but `recovers` fails, because the breaker never serves the post-recovery requests. That single failing flag is the difference between a breaker and a service that decided to stay down.

## External resources

Michael Nygard's "Release It!" is the origin of the circuit breaker as a stability pattern; its chapter on the pattern walks the three states and the failure modes they guard against, in production terms.

The AWS Builders' Library article "Avoiding fallback in distributed systems" and Google's SRE book chapter on "Addressing cascading failures" both describe the metastable outage — workers saturated on timeouts, load preventing recovery — that the breaker exists to prevent.

For the interaction with retries, the same SRE literature on "handling overload" covers why breakers, retries with backoff and jitter, and load shedding are layers of one strategy, each covering a failure mode the others do not.
