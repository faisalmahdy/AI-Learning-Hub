---
id: harness-inter-24
title: Return an unknown tool name as an observation, not an exception — or one hallucinated name aborts the whole loop
topic: agent-harness
level: intermediate
status: ready
time: 16 min
summary: A model does not always emit a tool name that exists — it misremembers (reed_file for read_file, serch_web for search_web) and hands the harness a call to a tool that is not on the menu. This is not a schema problem (a real tool with bad arguments); the tool does not exist, so there is nothing to validate or run. The naive dispatcher treats the menu as a dictionary and looks the name up, which raises on a miss, and that uncaught exception aborts the whole turn — every queued call after the bad one is discarded over a typo the model could have fixed itself. The harness should hand the miss back as an observation instead: name the unknown tool, list the ones that exist, and suggest the nearest real name by edit distance, so the loop survives and the model self-corrects. On a fixture of five calls where two names are hallucinated, the naive dispatcher runs one call then crashes and abandons the other four, while the observation dispatcher runs all three real calls and returns a recoverable did-you-mean for each unknown one.
eli5: Imagine a helper who sometimes asks for a tool by slightly the wrong name — "the reed-file thing." A bad manager, hearing a name not on the exact list, throws up their hands and walks off the job, abandoning everything still to do. A good manager says "there's no reed-file, but we have read-file — did you mean that?" and keeps going. The helper hears the correction and fixes it on the next try. One wrong name should be a note back, not the end of the whole job.
---

## Why this module

An agent loop dispatches whatever tool name the model produces, and the model produces names that do not exist — so a dispatcher that treats a missing name as an error to raise rather than a result to return will abort an entire turn over a single hallucinated word.

Tool calls are the model's output, and model output is not trusted to be well-formed. One way it goes wrong is a call to a tool that is not on the menu: the model reaches for `read_file` and emits `reed_file`, or invents a plausible-sounding tool that was never registered. This is a distinct failure from a real tool invoked with bad arguments — there the tool exists and its schema can reject the call — because here there is no tool at all, nothing to validate and nothing to run. The tempting implementation dispatches by dictionary lookup: keep a map from name to handler, look up the emitted name, call it. On a hit that is correct; on a miss it raises, and in the middle of an agent loop that exception is not a local error, it is the end of the turn. Every tool call the model had queued behind the bad one is thrown away, along with the reasoning and the partial results already accumulated, because one name was off by a character.

**A call to a tool that isn't on the menu is model output to handle, not an invariant to assume — dispatch it by a lookup that raises and one hallucinated name aborts the whole loop and discards every call behind it.**

The fix is the same discipline the harness already applies to a tool that returns an error: hand the problem back to the model as an observation. When a call names an unknown tool, return an error message that names it, lists the tools that do exist, and — because the model is usually one edit away — suggests the nearest real name. The loop stays alive. The model reads "no tool named serch_web; did you mean search_web?", corrects itself, and continues, exactly as it would after any other tool result. A wrong tool name becomes a recoverable turn instead of a crash. This module dispatches a run both ways and counts what each keeps.

## Concepts

**A hallucinated tool name** is a call whose name is not on the menu. It is not a schema error (no real tool to check) and not a runtime error (nothing ran); it is a name that resolves to nothing.

**The observation dispatcher** treats an unknown name as a result: it returns an error observation naming the tool, listing the menu, and suggesting the nearest real name, then continues to the next call.

```python filename=modules/agent-harness/code/harness-inter-24/unknowntool.py:57-66 COMPLETE
def dispatch_observation(menu, calls):
    """Dispatch every call; a known name executes, an unknown one becomes a recoverable error observation."""
    log = []
    for name in calls:
        if name in menu:
            log.append((name, "executed", None))
        else:
            obs = "no tool named %r; available: %s; did you mean %r?" % (name, menu, nearest(name, menu))
            log.append((name, "error-observation", obs))
    return log
```

**The naive dispatcher** looks the name up in a map and lets the lookup raise on a miss. That exception, uncaught by the loop, aborts the whole turn.

```python filename=modules/agent-harness/code/harness-inter-24/unknowntool.py:69-76 COMPLETE
def dispatch_naive(menu, calls):
    """Dispatch by dict lookup: execute known names, but raise (aborting the loop) on the first unknown one."""
    tools = {t: t for t in menu}
    log = []
    for name in calls:
        log.append((name, "executed", None))
        _ = tools[name]  # KeyError on an unknown name -- uncaught, this aborts the whole turn
    return log
```

<svg role="img" aria-label="A known name executes on both dispatchers; an unknown name crashes the naive loop but becomes an error observation that keeps the observation loop running" viewBox="0 0 300 108" width="300" height="108">
  <rect x="6" y="44" width="60" height="20" fill="none" stroke="var(--line)"/><text x="12" y="57" fill="var(--ink)" font-size="8">tool call</text>
  <line x1="66" y1="54" x2="92" y2="40" stroke="var(--line)"/><line x1="66" y1="54" x2="92" y2="72" stroke="var(--line)"/>
  <text x="70" y="36" fill="var(--muted)" font-size="7">on menu</text><text x="70" y="86" fill="var(--muted)" font-size="7">unknown</text>
  <rect x="92" y="30" width="70" height="18" fill="var(--s1)"/><text x="96" y="43" fill="var(--panel)" font-size="8">execute</text>
  <rect x="92" y="64" width="94" height="18" fill="none" stroke="var(--s2)"/><text x="96" y="77" fill="var(--ink)" font-size="8">naive: raise ✗</text>
  <line x1="186" y1="73" x2="212" y2="73" stroke="var(--s2)"/><text x="214" y="76" fill="var(--s2)" font-size="7">loop aborts</text>
  <rect x="92" y="64" width="94" height="18" fill="none" stroke="var(--s1)" stroke-dasharray="3 2"/><text x="96" y="98" fill="var(--muted)" font-size="7">obs: error observation → loop continues</text>
  <text x="6" y="106" fill="var(--muted)" font-size="8">same unknown name: a crash for one dispatcher, a recoverable note for the other</text>
</svg>
^ A name on the menu executes either way; an unknown name raises and kills the naive loop, but becomes an error observation the observation dispatcher hands back so the loop keeps running.

**Treat an unknown tool name the way you treat any tool result — return it as an observation, not an exception — so a hallucinated name costs one recoverable turn instead of the entire loop.**

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/harness-inter-24/unknowntool.py

The fixture is a four-tool menu and a run of five calls, two of which name tools that do not exist.

```json filename=modules/agent-harness/code/harness-inter-24/unknowntool.json:3-4 COMPLETE
  "menu": ["search_web", "read_file", "run_python", "list_dir"],
  "calls": ["search_web", "reed_file", "run_python", "serch_web", "list_dir"]
```

Run `--dispatch` to play the run through both dispatchers.

```text filename=--dispatch
DISPATCH — naive (crashes on the first miss) vs observation (survives every miss)
--------------------------------------------------------------------------
  call            naive                observation
  search_web      executed             executed
  reed_file       CRASH — loop aborts  error-observation
  run_python      (never reached)      executed
  serch_web       (never reached)      error-observation
  list_dir        (never reached)      executed
--------------------------------------------------------------------------
  naive ran 1 of 5 calls then aborted; the observation dispatcher ran all 5.
```

The first call, `search_web`, is on the menu and runs under both dispatchers. The second, `reed_file`, is a typo for `read_file` — and here the two paths split completely. The naive dispatcher raises on the lookup and the loop is over: `run_python`, `serch_web`, and `list_dir` are never reached, so two perfectly valid tool calls (`run_python`, `list_dir`) are discarded as collateral damage of one misspelling. The observation dispatcher records `reed_file` as an error observation and moves on, executing `run_python`, recording `serch_web` as a second error observation, and executing `list_dir`. It completed all three real calls and turned both hallucinations into recoverable feedback. The naive column is not just wrong on the bad call; it loses everything downstream of it, which is the real cost.

<svg role="img" aria-label="The naive dispatcher runs call 1 then aborts, losing calls 2-5; the observation dispatcher runs all five, executing three and returning two error observations" viewBox="0 0 300 100" width="300" height="100">
  <text x="6" y="12" fill="var(--muted)" font-size="8">five calls in order (■ executed  ▨ error-obs  ✕ lost)</text>
  <text x="6" y="34" fill="var(--muted)" font-size="8">naive</text>
  <rect x="50" y="24" width="24" height="14" fill="var(--s1)"/><rect x="78" y="24" width="24" height="14" fill="var(--s2)"/><text x="84" y="34" fill="var(--panel)" font-size="8">✕</text>
  <rect x="106" y="24" width="24" height="14" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/><rect x="134" y="24" width="24" height="14" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/><rect x="162" y="24" width="24" height="14" fill="none" stroke="var(--line)" stroke-dasharray="2 2"/>
  <text x="196" y="34" fill="var(--s2)" font-size="7">aborted — 4 lost</text>
  <text x="6" y="64" fill="var(--muted)" font-size="8">obs</text>
  <rect x="50" y="54" width="24" height="14" fill="var(--s1)"/><rect x="78" y="54" width="24" height="14" fill="none" stroke="var(--s2)"/><rect x="106" y="54" width="24" height="14" fill="var(--s1)"/><rect x="134" y="54" width="24" height="14" fill="none" stroke="var(--s2)"/><rect x="162" y="54" width="24" height="14" fill="var(--s1)"/>
  <text x="196" y="64" fill="var(--s1)" font-size="7">all 5 handled</text>
  <text x="6" y="92" fill="var(--muted)" font-size="8">one typo costs the naive loop four calls; the observation loop loses nothing</text>
</svg>
^ The naive dispatcher aborts at the second call and loses the four behind it; the observation dispatcher executes the three real calls and returns a recoverable error for the two hallucinated ones.

## Build

The error observation is only useful if the model can act on it, which is why it carries a suggestion. Run `--suggest`.

```text filename=--suggest
SUGGEST — the nearest real tool for each unknown name (did-you-mean)
------------------------------------------------------------
  reed_file      -> read_file      (edit distance 1)
  serch_web      -> search_web     (edit distance 1)
------------------------------------------------------------
  each hallucinated name is one edit from a real tool, so the suggestion is reliable.
```

Both hallucinated names are exactly one character-edit from a real tool: `reed_file` is one substitution from `read_file`, `serch_web` one insertion from `search_web`. That is not a coincidence — a model hallucinating a tool name is usually retrieving a near-miss of a real one, not inventing from nothing, so the minimum-edit-distance tool on the menu is a high-quality "did you mean." Putting it in the observation turns a bare rejection into a correction the model can accept immediately, cutting the recovery from "guess again from the whole menu" to "apply the one suggested fix." The listing of the full menu is the backstop for the rare case where the suggestion is wrong. This is the same move as a shell's command-not-found hint or a compiler's "did you mean" — the difference is that here the consumer is a model that will read the hint and retry within the same loop, so a good suggestion is worth real tokens saved.

<svg role="img" aria-label="Each unknown name maps to its nearest menu tool by one edit: reed_file to read_file, serch_web to search_web" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">unknown name → nearest menu tool (edit distance 1)</text>
  <rect x="10" y="24" width="90" height="16" fill="none" stroke="var(--s2)"/><text x="16" y="35" fill="var(--ink)" font-size="8">reed_file</text>
  <line x1="100" y1="32" x2="150" y2="32" stroke="var(--s1)"/><polygon points="150,29 156,32 150,35" fill="var(--s1)"/><text x="108" y="28" fill="var(--muted)" font-size="7">−1 edit</text>
  <rect x="156" y="24" width="90" height="16" fill="var(--s1)"/><text x="162" y="35" fill="var(--panel)" font-size="8">read_file</text>
  <rect x="10" y="54" width="90" height="16" fill="none" stroke="var(--s2)"/><text x="16" y="65" fill="var(--ink)" font-size="8">serch_web</text>
  <line x1="100" y1="62" x2="150" y2="62" stroke="var(--s1)"/><polygon points="150,59 156,62 150,65" fill="var(--s1)"/><text x="108" y="58" fill="var(--muted)" font-size="7">−1 edit</text>
  <rect x="156" y="54" width="90" height="16" fill="var(--s1)"/><text x="162" y="65" fill="var(--panel)" font-size="8">search_web</text>
  <text x="6" y="86" fill="var(--muted)" font-size="8">a hallucinated name is usually a near-miss, so the nearest tool is a reliable did-you-mean</text>
</svg>
^ Each unknown name is one edit from a real tool, so the minimum-edit-distance menu entry is a trustworthy did-you-mean the model can apply on its next turn.

## Definition of done

The self-test pins both dispatchers: the naive one aborts before finishing the real calls, the observation one runs every real call and recovers every miss, each suggestion is the true nearest tool, and a known name is never misrouted.

```python filename=modules/agent-harness/code/harness-inter-24/unknowntool.py:135-149 COMPLETE
    naive_aborts_early = len(executed) < len(real)
    print("  the naive dispatcher aborts before running every real call = %s (ran %d of %d real, crashed on %r)"
          % (naive_aborts_early, len(executed), len(real), crashed_on))

    obs_log = dispatch_observation(menu, calls)
    ran = [name for name, status, _ in obs_log if status == "executed"]
    obs_runs_all_real = ran == real
    print("  the observation dispatcher runs every real call = %s (%d of %d)" % (obs_runs_all_real, len(ran), len(real)))

    errored = [name for name, status, _ in obs_log if status == "error-observation"]
    unknown_recoverable = errored == unknown
    print("  every unknown name comes back as a recoverable error, not a crash = %s (%s)" % (unknown_recoverable, errored))

    suggestion_is_nearest = all(edit_distance(u, nearest(u, menu)) == min(edit_distance(u, t) for t in menu) for u in unknown)
    print("  each suggestion is the true minimum-edit-distance tool = %s (%s)" % (suggestion_is_nearest, [nearest(u, menu) for u in unknown]))
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the naive dispatcher aborts early; the observation one runs every real call and recovers every miss
----------------------------------------------------------------------------------------------------------------
  the naive dispatcher aborts before running every real call = True (ran 1 of 3 real, crashed on 'reed_file')
  the observation dispatcher runs every real call = True (3 of 3)
  every unknown name comes back as a recoverable error, not a crash = True (['reed_file', 'serch_web'])
  each suggestion is the true minimum-edit-distance tool = True (['read_file', 'search_web'])
  a known name always resolves to itself (never misrouted) = True
```

**Done means unknown names are proven recoverable, not fatal: the naive dispatcher runs 1 of 3 real calls and aborts on the first hallucinated name, while the observation dispatcher runs all 3 real calls, returns a recoverable error observation for both hallucinated names, suggests the true nearest tool (read_file, search_web) for each, and never misroutes a name that is on the menu.**

## Boss fight

Predict the two ways a did-you-mean makes things worse, not better. It is tempting to auto-apply the nearest tool instead of merely suggesting it.

The first trap is that silently rerouting a call to its nearest match is a dangerous convenience. A one-edit suggestion is a good hint but not a certainty, and the cost of a wrong reroute is not symmetric: sending a call meant for `list_dir` to a near-named `list_db` executes the wrong tool with the model's arguments, which for an effectful tool can delete, send, or spend against the wrong target — an error far worse than a rejected call the model would have retried. The rule is to suggest, never substitute: the observation names the nearest tool, but the model must re-issue the call itself, so the decision stays with the reasoner that has the context. Auto-correction also hides the hallucination from any logging that watches tool-call validity, so a rising rate of near-miss names — a signal the menu is confusing or the model is degrading — vanishes into silently-fixed calls.

```python filename=modules/agent-harness/code/harness-inter-24/unknowntool.py:52-54 COMPLETE
def nearest(name, menu):
    """The menu tool closest to `name` by edit distance -- the did-you-mean suggestion."""
    return min(menu, key=lambda t: (edit_distance(name, t), t))
```

The second trap is that recovering from an unknown name must not become an infinite loop. Returning an error observation keeps the loop alive, which is the point — but if the model re-emits the same wrong name every turn, or oscillates between two wrong names, the loop now runs forever handling the same recoverable error, burning budget without progress. An unknown-name observation is progress only if it changes the next call; a repeated identical failure is not. So the recovery has to sit under the same no-progress and budget bounds that guard every other loop: cap how many times a turn may fail to produce a runnable call, and treat "keeps calling tools that don't exist" as a terminal condition, not an eternal retry. And edit distance is a weak matcher — it will happily suggest a badly wrong tool when the hallucinated name is far from everything on the menu, so gate the suggestion on a distance threshold and omit it (just list the menu) when nothing is close, rather than proposing a tool the model never wanted. The observation makes a wrong name recoverable; the loop bounds make sure recovery actually terminates.

**Return an unknown tool name as an error observation — naming it, listing the real menu, and suggesting the nearest name by edit distance — so a hallucinated call costs one recoverable turn instead of aborting the loop; but only suggest, never auto-substitute (a wrong reroute runs the wrong effectful tool and hides the signal), gate the suggestion on a distance threshold so a far-off name gets the menu and not a bad guess, and keep the recovery under the loop's no-progress and budget bounds so a model that keeps emitting the same unknown name terminates instead of retrying forever.**

## External resources

Any agent-framework documentation on tool-call error handling and the observation/action loop (for example the ReAct pattern and function-calling error conventions) — the general principle that a tool failure, including an unknown tool, is fed back to the model as an observation rather than raised.

Writing on edit distance / Levenshtein distance and "did you mean" suggestion systems (shell command-not-found handlers, compiler diagnostics) — the matching technique behind the suggestion and its accuracy limits.

The companion "validate a tool call against its schema before executing" and "return a tool error as an observation" modules — schema validation handles the known-tool-bad-arguments case this module's unknown-tool case sits beside, and returning errors as observations is the same loop-survival discipline applied to runtime failures.
