---
id: cancel-inter-01
title: Cancel outstanding tool calls on abort — an unawaited call runs to completion anyway and applies a side effect the abandoned run no longer wants
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: A harness fires several tool calls in parallel and waits, and then the turn ends early — the user interrupts, a deadline fires, an error aborts the loop, or one call returns a result that makes the rest unnecessary. At that instant some calls are done and some are still running, and the harness must decide what to do with the ones still running. The lazy answer is to stop waiting — drop the futures and move on — but stopping the wait does not stop the work: a fire-and-forget call keeps executing in the background to completion, finishing its computation, spending its tokens or API quota, and, if it has a side effect, carrying that effect out. The agent was interrupted, but the email it was mid-send still sends, the order still places, the file still writes; the run is gone and its actions are not. That is the real danger, sharper than the wasted compute — an effectful call outliving the run performs an action nobody is waiting for, from a plan that has since been abandoned. Active cancellation fixes both: on abort the harness sends a cancel to every outstanding call, so the running work stops instead of completing, no more budget is spent, and the pending side effects are prevented or handed to compensation. Cancellation must be an explicit step, because the default behavior of an unawaited call is to run to completion, not to stop. On a fixture of four in-flight calls (one done, three running, two of them effectful), fire-and-forget lets all three finish and applies two unwanted side effects while active cancel stops the three and prevents both.
eli5: Imagine you send three friends off to run errands for you at the same time — one to mail a letter, one to buy concert tickets, one to grab groceries. Then you get a call: the plan is off, never mind. If you just stop waiting for them and go home, they don't know that — they keep going, mail the letter, buy the non-refundable tickets, and spend your money on errands you no longer want. Stopping your own waiting didn't stop them. What you actually have to do is call each friend and tell them to stop right now. Computer tool calls are the same: when an AI agent's task is cancelled, the tasks it already kicked off keep running in the background unless something actively tells them to stop — and the ones that spend money or send messages will do exactly that, for a job that's already been called off.
---

## Why this module

Parallelism and cancellation are two halves of one feature, and it is easy to build the first without the second. A harness that runs tool calls concurrently gets the speedup immediately, and in the happy path — all calls finish, the turn completes — nothing ever tests what happens when the turn does not finish. So the cancellation half goes unbuilt, and the gap only shows up when a run is interrupted, which is exactly when it matters.

The core misconception is that not waiting for a result is the same as stopping the work. It is not. Launching a tool call starts an independent piece of execution — a thread, a coroutine, an HTTP request in flight — and that execution has its own momentum. When the harness stops awaiting it, the awaiting stops but the execution continues, because nothing told it otherwise. The call runs to completion in the background, invisible to the abandoned run.

For a pure, read-only call that is merely wasteful: it spends tokens, compute, or third-party quota that the run will never use. For an effectful call it is dangerous: the side effect lands. An agent cancelled mid-turn still sends the email, places the order, deletes the file — because the tool call that would do those things was already in flight, and cancelling the agent did not cancel the call. This module takes a set of in-flight calls at an abort and compares fire-and-forget against active cancellation.

**Not awaiting a call is not the same as stopping it — an in-flight call runs to completion on its own momentum, wasting budget and, if effectful, applying a side effect for a run that has already been abandoned.**

## Concepts

The distinction that matters is between the read-only calls and the effectful ones, because the cost of leaking them is different in kind. A leaked read-only call costs resources — money and quota — which is a quantitative loss you can absorb. A leaked effectful call causes an action in the world — a message sent, a charge made, a record changed — which is a qualitative failure: the system did something it was told to stop doing. Cancellation matters for both, but it is a correctness requirement, not just an optimization, for the effectful ones.

The reason cancellation must be explicit is a property of how asynchronous work behaves by default: the default is to complete. An unawaited future, an orphaned thread, a fired HTTP request — none of them stop themselves when the code that created them loses interest. Stopping requires an active signal: cancel the future, close the connection, send an abort to the tool. If the harness does nothing, the work finishes; doing nothing is the wrong default, so the harness must do something.

There is a hard edge worth naming: some effects cannot be un-fired once cancellation loses the race. If an effectful call has already committed its side effect at the moment the cancel arrives, cancellation cannot prevent it — it can only trigger compensation (a reversing action, like a refund for a charge). So cancellation has two regimes: for calls not yet effectful, prevent the effect; for calls already effectful, compensate. This is why irreversible tool calls need both a confirmation gate before they run and a cancellation-plus-compensation story for when a run is aborted after they start.

<svg role="img" aria-label="A timeline of an effectful call with the abort and the cancel signal: if cancel arrives before the effect commits it prevents it, if after it can only compensate" viewBox="0 0 440 130">
<line x1="30" y1="60" x2="410" y2="60" stroke="var(--line)"/>
<circle cx="90" cy="60" r="4" fill="var(--ink)"/>
<text x="90" y="45" fill="var(--muted)" font-size="8" text-anchor="middle">abort</text>
<circle cx="250" cy="60" r="4" fill="var(--s2)"/>
<text x="250" y="45" fill="var(--s2)" font-size="8" text-anchor="middle">effect commits</text>
<line x1="150" y1="60" x2="150" y2="90" stroke="var(--s1)"/>
<text x="150" y="104" fill="var(--s1)" font-size="8" text-anchor="middle">cancel before: prevent</text>
<line x1="340" y1="60" x2="340" y2="90" stroke="var(--muted)"/>
<text x="340" y="104" fill="var(--muted)" font-size="8" text-anchor="middle">cancel after: compensate</text>
</svg>
^ Cancel that beats the commit prevents the effect; cancel that arrives after it can only trigger compensation, not undo it.

**Leaking a read-only call wastes resources but leaking an effectful one performs an unwanted action, so cancellation is a correctness requirement there; it must be explicit because async work completes by default, and effects already applied need compensation, not just cancellation.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/cancel-inter-01. The fixture is four calls in flight when the turn aborts: one already done, three still running, two of the running ones effectful.

```json filename=modules/agent-harness/code/cancel-inter-01/cancel.json:3-8 COMPLETE
  "calls": [
    {"id": "t1", "done": true, "effectful": false},
    {"id": "t2", "done": false, "effectful": true},
    {"id": "t3", "done": false, "effectful": true},
    {"id": "t4", "done": false, "effectful": false}
  ]
```

The running calls are the ones not yet done at the abort.

```python filename=modules/agent-harness/code/cancel-inter-01/cancel.py:34-36 COMPLETE
def running(calls):
    """Calls still in progress at the moment the turn aborts."""
    return [c for c in calls if not c["done"]]
```

Fire-and-forget stops awaiting, but the running calls complete anyway — so their work is done and their effects applied.

```python filename=modules/agent-harness/code/cancel-inter-01/cancel.py:39-43 COMPLETE
def fire_and_forget(calls):
    """Stop awaiting, but the running calls complete anyway -- work done, effects applied."""
    run = running(calls)
    return {"completed_after_abort": [c["id"] for c in run],
            "side_effects_applied": [c["id"] for c in run if c["effectful"]]}
```

Active cancel stops the running calls, so none complete and no pending effects land.

```python filename=modules/agent-harness/code/cancel-inter-01/cancel.py:46-48 COMPLETE
def active_cancel(calls):
    """Cancel the running calls -- they stop, so no extra work and no pending effects."""
    return {"completed_after_abort": [], "side_effects_applied": []}
```

Before running it, predict: fire-and-forget lets t2, t3, t4 finish and applies the two effectful ones (t2, t3); cancel stops all three and applies none. Run `--state`:

```text filename=cancel.py --state
STATE — in-flight calls at the abort, and their fate under each policy
------------------------------------------------------------------
  id    status    effectful   fire-and-forget   cancel
  t1    done      False       already done      already done
  t2    running   True        runs to done*     stopped
  t3    running   True        runs to done*     stopped
  t4    running   False       runs to done      stopped
------------------------------------------------------------------
  * a running effectful call that completes applies its side effect
```

The prediction holds. Under fire-and-forget every running call runs to done, and the two starred ones — t2 and t3, effectful — apply their side effects. Under cancel, all three running calls are stopped. The already-done t1 is unaffected either way.

<svg role="img" aria-label="Four calls at abort: t1 done; t2, t3, t4 running. Fire-and-forget lets t2 t3 t4 run to completion with t2 and t3 applying side effects; cancel stops t2 t3 t4" viewBox="0 0 440 160">
<text x="60" y="20" fill="var(--muted)" font-size="9" text-anchor="middle">at abort</text>
<text x="60" y="40" fill="var(--muted)" font-size="8">t1 done</text>
<text x="60" y="60" fill="var(--ink)" font-size="8">t2 run (fx)</text>
<text x="60" y="80" fill="var(--ink)" font-size="8">t3 run (fx)</text>
<text x="60" y="100" fill="var(--ink)" font-size="8">t4 run</text>
<text x="210" y="20" fill="var(--s2)" font-size="9" text-anchor="middle">fire-and-forget</text>
<rect x="150" y="52" width="120" height="14" fill="var(--s2)"/>
<text x="278" y="63" fill="var(--s2)" font-size="8">t2 done -&gt; effect!</text>
<rect x="150" y="72" width="120" height="14" fill="var(--s2)"/>
<text x="278" y="83" fill="var(--s2)" font-size="8">t3 done -&gt; effect!</text>
<rect x="150" y="92" width="120" height="14" fill="var(--s1)"/>
<text x="278" y="103" fill="var(--muted)" font-size="8">t4 done (waste)</text>
<text x="210" y="130" fill="var(--muted)" font-size="9" text-anchor="middle">active cancel</text>
<line x1="150" y1="145" x2="270" y2="145" stroke="var(--s1)" stroke-dasharray="4 3"/>
<text x="330" y="148" fill="var(--s1)" font-size="8">t2 t3 t4 stopped</text>
</svg>
^ Fire-and-forget drives every running call to completion — t2 and t3 fire their effects; cancel stops all three before they land.

Now the impact each policy leaves behind. Run `--impact`:

```text filename=cancel.py --impact
IMPACT — what each policy leaves behind after the abort
------------------------------------------------------------
  fire-and-forget: 3 calls keep running, 2 side effects applied ['t2', 't3']
  active cancel:   0 calls keep running, 0 side effects applied []
------------------------------------------------------------
  cancel turns wasted work and unwanted effects into nothing
```

Fire-and-forget leaves three calls burning to completion and two unwanted side effects applied — t2 and t3 did their thing for a run that no longer exists. Active cancel leaves nothing running and no effects applied. The difference is not a performance tweak; it is whether the abandoned run performed two actions in the world it was told to abandon.

<svg role="img" aria-label="Side effects applied after abort: fire-and-forget applies two; active cancel applies zero" viewBox="0 0 440 120">
<text x="110" y="24" fill="var(--ink)" font-size="10" text-anchor="middle">fire-and-forget</text>
<rect x="70" y="36" width="34" height="34" fill="var(--s2)" stroke="var(--line)"/>
<text x="87" y="58" fill="var(--ink)" font-size="9" text-anchor="middle">t2</text>
<rect x="108" y="36" width="34" height="34" fill="var(--s2)" stroke="var(--line)"/>
<text x="125" y="58" fill="var(--ink)" font-size="9" text-anchor="middle">t3</text>
<text x="110" y="90" fill="var(--s2)" font-size="9" text-anchor="middle">2 effects fired</text>
<text x="330" y="24" fill="var(--ink)" font-size="10" text-anchor="middle">active cancel</text>
<rect x="270" y="36" width="120" height="34" fill="var(--panel)" stroke="var(--s1)"/>
<text x="330" y="58" fill="var(--s1)" font-size="9" text-anchor="middle">(none)</text>
<text x="330" y="90" fill="var(--s1)" font-size="9" text-anchor="middle">0 effects fired</text>
</svg>
^ Two side effects for an abandoned run versus none — the impact of cancellation is measured in unwanted actions prevented, not just cycles saved.

## Build

The self-test plants the failure and names each claim as a boolean flag. It checks that some calls are running at the abort, that fire-and-forget completes every running call and applies unwanted side effects, and that active cancel stops every running call and prevents all pending effects.

```python filename=modules/agent-harness/code/cancel-inter-01/cancel.py:98-104 COMPLETE
    faf_applies_effects = len(faf["side_effects_applied"]) > 0
    print("  fire-and-forget applies unwanted side effects = %s (%s)" % (faf_applies_effects, faf["side_effects_applied"]))

    cancel_stops_all = cxl["completed_after_abort"] == []
    print("  active cancel stops every running call = %s" % cancel_stops_all)

    cancel_prevents_effects = cxl["side_effects_applied"] == []
    print("  active cancel prevents all pending side effects = %s" % cancel_prevents_effects)
```

Run `--check`. It exits non-zero if any flag is false, so it fails loudly if fire-and-forget ever stops leaking effects or cancel ever lets one through:

```text filename=cancel.py --check
SELF-TEST — fire-and-forget lets running effectful calls apply their side effects; cancel stops them
------------------------------------------------------------------------------------------------------------
  some calls are still running at the abort = True (['t2', 't3', 't4'])
  fire-and-forget lets every running call finish = True
  fire-and-forget applies unwanted side effects = True (['t2', 't3'])
  active cancel stops every running call = True
  active cancel prevents all pending side effects = True
```

**The self-test measures the leaked side effects specifically, not just the wasted calls — because the leaked effect is the correctness failure, while the wasted compute is only a cost.**

## Definition of done

You can explain why not awaiting a call is not the same as stopping it, and what keeps the call running.
You can distinguish the cost of leaking a read-only call (resources) from leaking an effectful one (an unwanted action), and say which makes cancellation a correctness requirement.
You can explain why cancellation must be an explicit step — async work completes by default.
You can name the four common abort triggers (user interrupt, deadline, error, an early sufficient result) and predict the leak under fire-and-forget for each.
You can describe the two cancellation regimes — prevent the effect if not yet applied, compensate if already applied — and connect it to gating irreversible tools.

## Boss fight

Consider the race that cancellation can lose. Suppose the cancel signal for t2 arrives just after t2 has already sent its email. Cancellation cannot un-send it; the effect is committed. Reason about what the harness must do: it cannot prevent, so it must either compensate (send a correction, issue a refund) or at minimum record that the effect happened so the abandoned run's partial actions are known. This is why cancellation alone is insufficient for irreversible effects and why the topic pairs it with a confirmation gate before such calls run — the gate reduces how often you launch an irreversible call you might need to cancel, and compensation handles the cases where cancellation lost the race.

Now consider the short-circuit trigger specifically. A common pattern fans out a query to several backends and needs only the first successful answer. The moment the first returns, the others are moot — but if they are not cancelled, they run to completion, and if any is effectful (say each backend logs the query or increments a counter) the fan-out applies N effects when the run needed one answer. The lesson generalizes past interrupts: cancellation is required not only when the user aborts but whenever the harness itself decides it no longer needs an outstanding call, which the highly parallel patterns do constantly.

**Cancellation can lose the race to a committed effect, so irreversible calls need a pre-run gate and post-hoc compensation, not cancellation alone; and cancellation is required not only on user abort but on every short-circuit, where a fan-out that keeps its moot calls running applies N effects for a run that needed one answer.**

## External resources

Structured-concurrency designs (Python's asyncio task cancellation, Kotlin coroutines, Trio's cancel scopes) exist precisely to make cancellation propagate to outstanding work rather than leaving orphaned tasks running.
Anthropic's and OpenAI's streaming and tool-use guidance describe aborting in-flight requests on client disconnect, the network-level version of this cancellation.
The topic's own modules on gating irreversible tools and on idempotent retries cover the companion disciplines — reducing irreversible launches, and making a re-issued call safe — that cancellation works alongside.
