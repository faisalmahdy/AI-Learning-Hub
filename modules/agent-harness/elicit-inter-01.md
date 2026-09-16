---
id: elicit-inter-01
title: Ask when a required argument is missing — guessing a default and dispatching commits a confidently wrong action
topic: agent-harness
level: intermediate
status: ready
time: 15 min
summary: An agent turns a user's request into a tool call, and the request does not always contain everything the tool needs. "Book me a flight to New York" names a destination but not a date; "delete the old logs" names an action but not which logs. The tool has required parameters, and one is unspecified. The agent faces a fork, and the wrong branch is seductive because it keeps things moving: fill the missing parameter with a guess — a default, today's date, the most common value — and dispatch the tool anyway. The request looks satisfied and nothing errored, but the agent has committed an action the user never specified: a flight on a date they did not choose, a deletion by a threshold they did not set. When the action is irreversible or costly, a guessed parameter is not a small inaccuracy — it is doing the wrong thing with full confidence. The correct behavior is elicitation: when a required parameter cannot be filled from the request or unambiguous context, ask the user a clarifying question naming the gap, and do not dispatch until answered. The tell that separates guessing from knowing is provenance: a guessed value did not come from the request. On a fixture where book_flight requires origin, destination, and date and the request supplied origin (SFO) and destination (NYC) but not date, the guess-and-dispatch agent fills date with "today" (never in the request) and dispatches a booking, while the eliciting agent detects the missing date, asks for it, and dispatches nothing.
eli5: Imagine you ask a helper to mail a package "to Grandma," but you forget to say WHICH day you want it to arrive. A pushy helper just picks a day — say, tomorrow — and ships it, and now it's on its way for a day you never chose, maybe when Grandma isn't even home. A careful helper stops and asks, "What day should it arrive?" before doing anything. Asking costs you a few seconds; guessing wrong costs a wasted shipment you have to chase down. When the action can't be easily undone, the careful helper who asks first is the one you want.
---

## Why this module

The pressure on an agent is to complete the task, and that pressure quietly turns "I don't have enough information" into "I'll fill in the rest." When a request leaves a required parameter unspecified, the model can always produce *a* plausible value — a default, a common choice, today's date — and dispatching with it feels like progress. It is the opposite: the agent has substituted its own guess for the user's intent on a parameter the user cared enough about that the tool requires it, and then acted on that guess. The danger is that nothing looks wrong. The tool call succeeds, the flow completes, and the mistake is discovered only when the user sees a booking, a deletion, or a message they never asked for.

The tool has required parameters, and one of them is unspecified. Fill the missing parameter with a guess and dispatch the tool anyway, and the request is satisfied superficially while the agent has committed an action the user never actually specified — booked a flight for a date the user did not choose, deleted logs by a threshold the user did not set. When the action is irreversible or costly, a guessed parameter is not a small inaccuracy; it is doing the wrong thing with full confidence.

The correct behavior is elicitation: when a required parameter cannot be filled from the request (or unambiguous context), ask the user a clarifying question that names the missing parameter, and do not dispatch until answered. This trades a round-trip of latency for correctness — a question is cheap and reversible, a wrong booking is neither. This module runs both agents on a request with a missing required parameter.

**Before dispatching a tool, check that every required parameter is actually supplied by the request (or safe, stated context); if a required parameter is missing, elicit — ask the user a question naming the gap — rather than filling it with a guessed default and dispatching, because a fabricated required argument turns "helpful" into a confidently wrong, possibly irreversible action the user never asked for.**

## Concepts

**Detect the gap, then either fabricate or ask.** The guessing agent fills each missing required parameter from its defaults and dispatches, recording what it fabricated.

```python filename=modules/agent-harness/code/elicit-inter-01/elicit.py:53-65 COMPLETE
def missing_required(required, provided):
    """The required parameters the request did not supply."""
    return [p for p in required if p not in provided]


def run_guess(data):
    """Fill each missing required parameter from the guess defaults and dispatch the tool."""
    args = dict(data["provided"])
    fabricated = {}
    for p in missing_required(data["required_params"], data["provided"]):
        args[p] = data["guess_defaults"].get(p, "?")
        fabricated[p] = args[p]
    return {"action": "dispatch", "tool": data["tool"], "args": args, "fabricated": fabricated}
```

**The eliciting agent, finding a required parameter missing, asks instead of dispatching** — and returns no tool call.

```python filename=modules/agent-harness/code/elicit-inter-01/elicit.py:68-73 COMPLETE
def run_elicit(data):
    """If a required parameter is missing, ask for it and dispatch nothing."""
    missing = missing_required(data["required_params"], data["provided"])
    if missing:
        return {"action": "ask", "question": "Which %s? (required, not specified)" % ", ".join(missing), "tool": None}
    return {"action": "dispatch", "tool": data["tool"], "args": dict(data["provided"]), "fabricated": {}}
```

<svg role="img" aria-label="The book_flight tool needs origin, destination, date; origin and destination are provided, date is missing; the guess agent fills date with 'today' (fabricated) and dispatches, the elicit agent asks for the date and dispatches nothing" viewBox="0 0 300 122" width="300" height="122">
  <text x="6" y="12" fill="var(--muted)" font-size="8">book_flight needs origin, destination, date</text>
  <text x="14" y="30" fill="var(--s1)" font-size="7">origin ✓ SFO</text>
  <text x="110" y="30" fill="var(--s1)" font-size="7">destination ✓ NYC</text>
  <text x="220" y="30" fill="var(--s2)" font-size="7">date ✗ missing</text>
  <line x1="150" y1="38" x2="150" y2="50" stroke="var(--muted)"/>
  <text x="70" y="62" fill="var(--muted)" font-size="7">fork on the missing date:</text>
  <rect x="14" y="70" width="130" height="40" fill="none" stroke="var(--s2)"/>
  <text x="20" y="84" fill="var(--s2)" font-size="6">guess: date = 'today'</text>
  <text x="20" y="96" fill="var(--s2)" font-size="6">(fabricated) → dispatch</text>
  <text x="20" y="106" fill="var(--s2)" font-size="6">books a flight!</text>
  <rect x="156" y="70" width="130" height="40" fill="none" stroke="var(--s1)"/>
  <text x="162" y="84" fill="var(--s1)" font-size="6">elicit: "which date?"</text>
  <text x="162" y="96" fill="var(--s1)" font-size="6">→ ask, no dispatch</text>
  <text x="162" y="106" fill="var(--s1)" font-size="6">waits for the user</text>
</svg>
^ Two of book_flight's three required parameters are provided and the date is missing; the guessing agent fabricates a date ("today") and dispatches a real booking, while the eliciting agent asks "which date?" and dispatches nothing until the user answers.

## Worked example

Source: faisalmahdy/ai-learning-hub — modules/agent-harness/code/elicit-inter-01/elicit.py

The fixture is the tool's required parameters, what the request supplied, and the default a guessing agent would fabricate.

```json filename=modules/agent-harness/code/elicit-inter-01/elicit.json:3-6 COMPLETE
  "tool": "book_flight",
  "required_params": ["origin", "destination", "date"],
  "provided": {"origin": "SFO", "destination": "NYC"},
  "guess_defaults": {"date": "today"}
```

Run `--slots`.

```text filename=--slots
SLOTS — required parameters of book_flight vs what the request supplied
--------------------------------------------------------------
  origin       provided: 'SFO'
  destination  provided: 'NYC'
  date         MISSING  (a guess would fabricate 'today')
--------------------------------------------------------------
  missing required: ['date']
```

<svg role="img" aria-label="Three required parameters with their provenance: origin and destination trace back to the request, date has no source and would be invented by a guess" viewBox="0 0 300 104" width="300" height="104">
  <text x="6" y="12" fill="var(--muted)" font-size="8">provenance: which required values came from the user?</text>
  <rect x="14" y="22" width="80" height="16" fill="none" stroke="var(--muted)"/><text x="26" y="34" fill="var(--ink)" font-size="7">the request</text>
  <text x="150" y="34" fill="var(--s1)" font-size="7">origin = SFO</text><path d="M94 30 L146 30" fill="none" stroke="var(--s1)"/>
  <text x="150" y="54" fill="var(--s1)" font-size="7">destination = NYC</text><path d="M94 34 L146 50" fill="none" stroke="var(--s1)"/>
  <text x="150" y="80" fill="var(--s2)" font-size="7">date = ?  (no source)</text>
  <path d="M150 76 L120 76" fill="none" stroke="var(--s2)" stroke-dasharray="2 2"/><text x="60" y="79" fill="var(--s2)" font-size="6">nothing to trace to</text>
  <text x="14" y="98" fill="var(--muted)" font-size="6">a value with no provenance is a guess — the signal to ask, not act</text>
</svg>
^ Origin and destination each trace back to something the user said; date traces back to nothing, so any value for it is invented rather than known — provenance is the mechanical signal that separates a parameter the agent may use from one it must elicit.

Read the three required parameters. Origin and destination were supplied by the request — SFO and NYC — so the agent knows them because the user said them. Date is a different case: the tool requires it, and the request never mentioned it. The line "a guess would fabricate 'today'" is the crux of the whole module. "today" is a perfectly plausible date, and an agent under pressure to complete the booking will happily use it — but it is a value the agent invented, not one the user provided, and the user may well have wanted next Tuesday. The slots view makes the invisible visible: two of the three parameters have a provenance (the request), and one does not, which is exactly the signal that the agent should stop and ask rather than proceed.

## Build

Watch what each agent actually does at the dispatch point.

```text filename=--dispatch
DISPATCH — what each agent does with the missing 'date'
------------------------------------------------------------------
  GUESS-AND-DISPATCH:
    action: dispatch book_flight(origin='SFO', destination='NYC', date='today')
    fabricated (never in the request): {'date': 'today'}
  ELICIT:
    action: ask -> 'Which date? (required, not specified)'
    tool dispatched: None
------------------------------------------------------------------
  guessing books a flight on a date the user never chose; eliciting asks first.
```

The two agents diverge completely at the moment of action. The guess-and-dispatch agent emits a real tool call — `book_flight(origin='SFO', destination='NYC', date='today')` — with the fabricated date embedded in it, indistinguishable to the tool from a date the user actually chose. The booking happens. The eliciting agent emits no tool call at all; it returns a question, "Which date?", and waits. The critical property is what is *absent* from the elicit path: there is no dispatch, so there is no action to undo. This is why elicitation is the safe default for a consequential tool — the cost of asking is a round-trip and a moment of the user's attention, while the cost of guessing wrong on `book_flight` is a real reservation, possibly a charge, that someone now has to cancel. The asymmetry is the whole argument: when one branch is cheaply reversible (ask again) and the other is expensively irreversible (unwind a booking), an unfilled required parameter should take the reversible branch.

```python filename=modules/agent-harness/code/elicit-inter-01/elicit.py:115-122 COMPLETE
    required_slot_missing = "date" in missing
    print("  a required parameter is missing from the request = %s (missing: %s)" % (required_slot_missing, missing))

    guess_fabricates = "date" in g["fabricated"] and g["fabricated"]["date"] not in provided.values()
    print("  guess fabricates the missing value (not from the request) = %s (date=%r)" % (guess_fabricates, g["fabricated"].get("date")))

    guess_dispatches = g["action"] == "dispatch"
    print("  guess dispatches the tool anyway = %s (%s)" % (guess_dispatches, g["tool"]))
```

## Definition of done

The self-test pins the missing required parameter, the fabrication and dispatch by the guessing agent, and the question-and-withhold by the eliciting one.

```python filename=modules/agent-harness/code/elicit-inter-01/elicit.py:124-127 COMPLETE
    elicit_asks = e["action"] == "ask" and "date" in e["question"]
    print("  elicit asks a question naming the gap = %s (%r)" % (elicit_asks, e.get("question")))

    elicit_no_dispatch = e["tool"] is None
    print("  elicit dispatches no tool until answered = %s" % elicit_no_dispatch)
```

Run `--check`. Every flag is True and the process exits 0.

```text filename=--check
SELF-TEST — the required date is missing; guessing fabricates and dispatches, eliciting asks and withholds the call
--------------------------------------------------------------------------------------------------------------------
  a required parameter is missing from the request = True (missing: ['date'])
  guess fabricates the missing value (not from the request) = True (date='today')
  guess dispatches the tool anyway = True (book_flight)
  elicit asks a question naming the gap = True ('Which date? (required, not specified)')
  elicit dispatches no tool until answered = True
```

<svg role="img" aria-label="Two outcomes: the guess agent produces a dispatched book_flight call with a fabricated date, the elicit agent produces a question and no call" viewBox="0 0 300 92" width="300" height="92">
  <text x="6" y="12" fill="var(--muted)" font-size="8">missing required 'date' → dispatch a guess, or ask?</text>
  <text x="10" y="34" fill="var(--muted)" font-size="7">guess</text>
  <rect x="70" y="24" width="200" height="16" fill="var(--s2)"/><text x="76" y="36" fill="var(--panel)" font-size="7">book_flight(…, date='today') dispatched</text>
  <text x="10" y="62" fill="var(--muted)" font-size="7">elicit</text>
  <rect x="70" y="52" width="130" height="16" fill="none" stroke="var(--s1)"/><text x="76" y="64" fill="var(--s1)" font-size="7">"Which date?" — no call</text>
  <text x="206" y="64" fill="var(--muted)" font-size="6">nothing to undo</text>
  <text x="10" y="84" fill="var(--muted)" font-size="6">one commits an action the user never chose; the other keeps the choice reversible</text>
</svg>
^ The guessing agent dispatches a booking carrying a date the user never chose; the eliciting agent returns a question and no call, leaving nothing to undo — the difference between a confidently wrong action and a cheap clarifying round-trip.

**Done means the fork is proven on a real request: book_flight requires a date the request never supplied, so the guessing agent fabricates date='today' (a value not in the request) and dispatches a booking, while the eliciting agent asks "Which date?" and dispatches no tool — so a missing required parameter must be elicited, not filled with a guessed default and acted on.**

## Boss fight

Predict two ways elicitation is harder than "ask whenever a slot is empty," because asking too much is its own failure and knowing what to ask is the real skill.

The first trap is that eliciting every gap is as bad as guessing every gap — an agent that stops to ask about parameters it could safely default, or infer, becomes an exhausting interrogator that never gets anything done. The judgment is in classifying the gap. A parameter with a sensible, stated default on a low-stakes, reversible action should be defaulted, not asked (do not ask "which encoding?" before reading a text file when UTF-8 is the obvious default). A parameter that is unambiguously inferable from context should be inferred, not asked (if the user just said "the Q3 report" and there is exactly one, do not ask which file). Only a genuinely required parameter, with no safe default and no unambiguous inference, on a consequential action, warrants a question — and even then you ask once, for everything missing at once, not in a slow drip of one question per turn. So elicitation is not "ask when unsure"; it is a triage: default the safe gaps, infer the inferable ones, batch-ask the truly required-and-ambiguous ones, and calibrate the threshold to the action's stakes and reversibility. An agent that asks about everything trains the user to ignore it or to stop using it, which is how over-asking becomes as unsafe as under-asking.

The second trap is that "provided" and "required" are fuzzier than the fixture's clean membership check, so both detection and the question need care. A parameter can be present but ambiguous ("New York" — the city, or the state? JFK, LGA, or EWR?), which is not a missing-slot but still needs elicitation or disambiguation, so the check is not merely "is the key there" but "is the value unambiguous enough to act on." A parameter can be partially specified ("sometime next week") that needs narrowing rather than a yes/no. And the elicitation itself is a place to get the interaction wrong: a good clarifying question is specific and closed where possible (offer the plausible options — "morning or evening flight?" — rather than an open "when?"), states why it is asking, and preserves the rest of the context so the user does not have to repeat themselves. There is also a safety dimension: a request that is *under*-specified in a way that would make a consequential action dangerous (delete "everything"? which everything?) should trigger not just a slot-fill question but a confirmation of scope, which is where elicitation meets the gate-irreversible-tools discipline — some actions need explicit confirmation even when every slot is filled. So elicitation is a spectrum from "fill the safe default" through "disambiguate the fuzzy value" to "confirm the dangerous scope," and mapping each gap to the right point on it is the actual competence.

**Elicitation is triage, not reflex: default the gaps with a safe stated default, infer the ones unambiguously implied by context, and only batch-ask (once, for all of them) the genuinely required-and-ambiguous parameters of a consequential action — an agent that asks about everything is as unusable as one that guesses everything. And "missing" is fuzzier than an empty slot: a present-but-ambiguous value ("New York" — which airport?) or a partial one ("next week") needs disambiguation, the question should be specific and closed with the plausible options offered, and an under-specified consequential scope ("delete everything?") needs confirmation, not just a slot-fill — where elicitation meets the confirm-irreversible-actions rule.**

## External resources

The Model Context Protocol elicitation feature and agent-framework "human-in-the-loop" / clarifying-question patterns — how a tool-calling agent requests missing information from the user mid-task rather than proceeding on a guess.

Writing on slot filling and clarification in dialogue and task-oriented systems — detecting under-specified requests, deciding when to ask versus default versus infer, and how to phrase an effective clarifying question.

The companion tool-argument-validation and gate-irreversible-tools modules in this topic — validation checks a call the model *did* fully specify, elicitation handles the call it could not, and confirmation gates the consequential call even when fully specified; together they cover the arguments an agent must have, invent, or double-check before acting.
