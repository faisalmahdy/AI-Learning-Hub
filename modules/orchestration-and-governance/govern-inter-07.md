---
id: govern-inter-07
title: Require a quorum before trusting a vote — 100% of the two who answered is not consensus
topic: orchestration-and-governance
level: intermediate
status: ready
time: 5-8h
summary: A governed panel votes on whether to authorize a consequential action, and the tempting rule is to go with the majority of whoever answered — which breaks the instant some voters are slow or down, because if three of five time out and the two who replied both say yes, the majority-of-responders rule reports 100% approval and acts on the word of two voters out of five. A quorum rule fixes it: before counting the vote at all, require that enough voters responded, and below that threshold the round is inconclusive — withhold and escalate rather than let a non-representative minority stand in for the panel. On the degraded round (2 of 5 reply, both yes, 100% of responders) the naive rule approves while the quorum rule returns no-quorum and withholds; on the healthy round (4 of 5 reply, 3 yes) both approve; on the contested round (4 reply, 1 yes) both withhold. The quorum blocks exactly the under-supported decision and nothing else, because 100% approval of two responders is not the same evidence as 60% of five, and a decision made by whoever happened to be reachable is a coincidence, not consensus.
eli5: Imagine a five-person safety committee has to okay something risky. One day three members are out sick, the two who show up both say "sure," and the chairman announces "unanimous, approved!" — but it was really just two people deciding for five. The fix is a rule: unless enough members actually show up, you don't hold the vote at all — you postpone and get more people, instead of letting a lucky pair speak for everybody.
---

## Why this module

Governance is the discipline of not letting a system act on a signal weaker than the action deserves, and voting panels are one of its main tools: before an agent is promoted, a change ships, or an irreversible step runs, ask a panel and go with the result. The failure this module is about is subtle because the vote itself looks fine — the tempting rule, "act on the majority of whoever answered," is correct whenever everyone answers. The problem is that in any real distributed panel, not everyone answers. Voters are slow, down, or partitioned away, and the rule silently redefines "the panel" to mean "the subset that happened to reply."

Watch what that does under degradation. A five-member panel is asked to authorize an action. Three members time out — slow, crashed, unreachable — and the two who reply both vote yes. The majority-of-responders rule computes: two yes, zero no, 100% approval, act. It has just authorized a consequential action on the agreement of two voters out of five, and it did so while reporting the highest possible confidence, 100%. That number is a lie of composition: it is 100% of a sample so small and so non-random (it is exactly the voters who were reachable) that it carries almost none of the assurance the panel of five was supposed to provide. A decision made by whoever happened to be up is a coincidence of availability, not a consensus.

The fix is a quorum: a minimum number of responses required before the vote is counted at all. Below the quorum, the round is inconclusive — you withhold the action and escalate, rather than let two votes stand in for five. Above the quorum, you count the majority as usual. This module builds both rules and runs them across a degraded round (two reply), a healthy round (four reply), and a contested round (four reply but mostly no), showing that the quorum rule blocks exactly the under-supported decision while agreeing with the naive rule everywhere the panel actually turned out. Everything runs offline against a rounds fixture, stdlib Python 3, `$0.00`. The instinct to unlearn is that a vote's result is its approval rate. A vote's result is trustworthy only when enough of the panel weighed in; the approval rate of a handful of responders is a statistic about who was reachable, not about what the panel thinks.

## Concepts

Named here so you can find them again; each is built below.

- **Panel and quorum** — the full set of voters, and the minimum responses required to trust a round.
- **Responder** — a voter who actually replied; a timeout is not a responder.
- **Majority of responders** — the naive rule: yes beats no among those who answered.
- **No-quorum** — the quorum rule's verdict when too few responded; inconclusive, escalate.
- **Approval rate** — yes over responders; a lie of composition when responders are few.
- **Representativeness** — whether the responders stand in fairly for the panel; a quorum enforces it.

## Worked example

Source: a governance gate — the panel approval that authorizes a consequential agentic action, the kind an orchestration layer runs before promoting an agent or executing an irreversible step. The rounds stand in for real votes under partial availability, chosen so the degraded round exposes the naive rule.

Script and fixture: `modules/orchestration-and-governance/code/govern-inter-07/` — `quorum.py`, and `rounds.json`, three rounds of a five-voter panel. Every command runs from there.

### Counting a round

A round is a list of votes, some of which are timeouts; the responders are the ones who actually replied.

```
# quorum.py:41-51 — COMPLETE (responders exclude timeouts; the tally counts among responders)
def responders(votes):
    """Voters who actually replied (not 'timeout')."""
    return [v for v in votes if v != "timeout"]


def tally(votes):
    r = responders(votes)
    return {"total": len(votes), "responded": len(r),
            "yes": r.count("yes"), "no": r.count("no")}
```

The tally keeps `total` and `responded` separate on purpose — the gap between them is exactly the information the naive rule throws away. A timeout is not a no and not a yes; it is a voter who was not heard from, and conflating "did not respond" with any vote is the root of the bug.

### The two decision rules

The naive rule reads only the responders; the quorum rule checks how many responded first.

```
# quorum.py:54-68 — COMPLETE (majority of responders vs a quorum gate before the majority)
def decide_naive(votes):
    """The bug: majority of whoever answered, ignoring how many stayed silent."""
    t = tally(votes)
    if t["responded"] == 0:
        return "withhold"
    return "approve" if t["yes"] > t["no"] else "withhold"


def decide_quorum(votes, quorum):
    """The fix: require `quorum` responses first; below it the round is inconclusive."""
    t = tally(votes)
    if t["responded"] < quorum:
        return "no-quorum"              # not enough voters to trust the result -- escalate
    return "approve" if t["yes"] > t["no"] else "withhold"
```

The two functions are identical except for the four-line guard in `decide_quorum`: if fewer than `quorum` voters responded, it returns `no-quorum` before ever looking at the yes/no split. That guard is the whole module.

<svg viewBox="0 0 700 160" role="img" aria-label="A decision flow. A vote arrives. First gate: did at least quorum voters respond? If no, return no-quorum and escalate. If yes, second gate: do yes votes beat no? If yes, approve; if no, withhold. The naive rule skips the first gate and goes straight to the majority check.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">the quorum rule adds one gate before the majority check</text>
    <rect x="30" y="60" width="80" height="30" fill="var(--panel)" stroke="var(--line)"></rect><text x="70" y="79" text-anchor="middle" fill="var(--ink)" font-size="8">vote in</text>
    <line x1="110" y1="75" x2="150" y2="75" stroke="var(--ink)"></line>
    <rect x="150" y="55" width="130" height="40" fill="var(--acc-soft)" stroke="var(--acc-line)"></rect><text x="215" y="72" text-anchor="middle" fill="var(--acc-ink)" font-size="8">responded ≥ quorum?</text><text x="215" y="86" text-anchor="middle" fill="var(--acc-ink)" font-size="7">(the new gate)</text>
    <line x1="215" y1="95" x2="215" y2="125" stroke="var(--s2)"></line><text x="222" y="118" fill="var(--s2)" font-size="7">no</text>
    <rect x="150" y="125" width="130" height="26" fill="var(--s2)"></rect><text x="215" y="142" text-anchor="middle" fill="var(--panel)" font-size="8">no-quorum → escalate</text>
    <line x1="280" y1="75" x2="330" y2="75" stroke="var(--acc-line)"></line><text x="298" y="68" fill="var(--acc-ink)" font-size="7">yes</text>
    <rect x="330" y="55" width="110" height="40" fill="var(--panel)" stroke="var(--line)"></rect><text x="385" y="79" text-anchor="middle" fill="var(--ink)" font-size="8">yes &gt; no?</text>
    <line x1="440" y1="75" x2="490" y2="75" stroke="var(--s1)"></line><text x="458" y="68" fill="var(--s1)" font-size="7">yes</text>
    <rect x="490" y="60" width="90" height="30" fill="var(--s1)"></rect><text x="535" y="79" text-anchor="middle" fill="var(--panel)" font-size="8">approve</text>
    <line x1="385" y1="95" x2="385" y2="125" stroke="var(--muted)"></line><text x="392" y="118" fill="var(--muted)" font-size="7">no</text>
    <rect x="330" y="125" width="110" height="26" fill="var(--panel)" stroke="var(--muted)"></rect><text x="385" y="142" text-anchor="middle" fill="var(--muted)" font-size="8">withhold</text>
    <text x="150" y="40" fill="var(--s2)" font-size="7">naive skips straight here ↓ (no first gate)</text>
  </g>
</svg>
^ The quorum rule inserts one gate — did enough voters respond? — before the majority check. Fail it and the round is inconclusive; the naive rule has no such gate and drops straight into the majority of whoever answered.

Run all three rounds:

```
# $ python3 quorum.py --rounds
#   round        votes                          naive     quorum
#   degraded     yes,yes,timeout,timeout,timeout approve   no-quorum
#   healthy      yes,yes,yes,no,timeout         approve   approve
#   contested    yes,no,no,no,timeout           withhold  withhold
```

run: 2026-08-27 · deterministic; the rounds are a fixture · 5 voters, quorum 3 · `python3 quorum.py --rounds`

The degraded row is the failure: two voters replied, both yes, three timed out, and the naive rule approves — authorizing the action on 2 of 5. The quorum rule (which needs 3) returns no-quorum and refuses to act. On the healthy round, four replied with a clear majority, so both rules approve — the quorum did not get in the way of a well-supported decision. On the contested round, four replied but mostly no, so both withhold. The quorum rule differs from naive on exactly one round: the one where too few voters spoke.

<svg viewBox="0 0 700 200" role="img" aria-label="Three rounds shown as five voter slots each. Degraded: two yes, three timeout — naive approves (highlighted as wrong), quorum blocks. Healthy: three yes, one no, one timeout — both approve. Contested: one yes, three no, one timeout — both withhold. A quorum line at three responders separates degraded (below) from the others (at or above).">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">three rounds of 5 voters — quorum needs 3 responders to trust the vote</text>
    <text x="30" y="48" fill="var(--muted)" font-size="8">degraded</text>
    <rect x="110" y="34" width="24" height="20" fill="var(--s1)"></rect><rect x="138" y="34" width="24" height="20" fill="var(--s1)"></rect><rect x="166" y="34" width="24" height="20" fill="var(--line)"></rect><rect x="194" y="34" width="24" height="20" fill="var(--line)"></rect><rect x="222" y="34" width="24" height="20" fill="var(--line)"></rect>
    <text x="270" y="48" fill="var(--s2)" font-size="8">2 replied → naive APPROVES, quorum blocks</text>
    <text x="30" y="98" fill="var(--muted)" font-size="8">healthy</text>
    <rect x="110" y="84" width="24" height="20" fill="var(--s1)"></rect><rect x="138" y="84" width="24" height="20" fill="var(--s1)"></rect><rect x="166" y="84" width="24" height="20" fill="var(--s1)"></rect><rect x="194" y="84" width="24" height="20" fill="var(--s2)"></rect><rect x="222" y="84" width="24" height="20" fill="var(--line)"></rect>
    <text x="270" y="98" fill="var(--s1)" font-size="8">4 replied, 3 yes → both approve</text>
    <text x="30" y="148" fill="var(--muted)" font-size="8">contested</text>
    <rect x="110" y="134" width="24" height="20" fill="var(--s1)"></rect><rect x="138" y="134" width="24" height="20" fill="var(--s2)"></rect><rect x="166" y="134" width="24" height="20" fill="var(--s2)"></rect><rect x="194" y="134" width="24" height="20" fill="var(--s2)"></rect><rect x="222" y="134" width="24" height="20" fill="var(--line)"></rect>
    <text x="270" y="148" fill="var(--muted)" font-size="8">4 replied, 1 yes → both withhold</text>
    <line x1="158" y1="26" x2="158" y2="170" stroke="var(--acc-line)" stroke-dasharray="4 3"></line><text x="158" y="184" text-anchor="middle" fill="var(--acc-ink)" font-size="7">quorum = 3 →</text>
    <text x="560" y="184" fill="var(--muted)" font-size="7">yes=filled crop, no=dark, timeout=faint</text>
  </g>
</svg>
^ Only the degraded round falls below the quorum of 3 responders, and it is the only round where the two rules disagree: naive approves it, the quorum rule blocks it. Where the panel actually turned out, the quorum rule agrees with the majority.

### The approval-rate lie

The `--tally` view shows why 100% can mean less than 75%.

```
# $ python3 quorum.py --tally
#   degraded     responded 2/5  yes=2 no=0  approval-of-responders=100%
#      naive=approve  quorum=no-quorum
#   healthy      responded 4/5  yes=3 no=1  approval-of-responders=75%
#      naive=approve  quorum=approve
#   contested    responded 4/5  yes=1 no=3  approval-of-responders=25%
#      naive=withhold  quorum=withhold
```

run: 2026-08-27 · deterministic · `python3 quorum.py --tally`

Whether a decision authorizes the action comes down to one predicate — only a clean `approve` acts, and both `withhold` and `no-quorum` do not:

```
# quorum.py:70-72 — COMPLETE (only 'approve' authorizes; withhold and no-quorum do not act)
def acts(decision):
    """Only a clean 'approve' authorizes the action; withhold and no-quorum do not."""
    return decision == "approve"
```

<svg viewBox="0 0 700 170" role="img" aria-label="Two approval rates with their sample sizes. The degraded round: 100% but only 2 of 5 voters filled in, so 3 slots are empty question marks. The healthy round: 75% with 4 of 5 filled. Despite the lower rate, the healthy round rests on more voters.">
  <g font-family="var(--mono)" font-size="9">
    <text x="20" y="16" fill="var(--muted)">an approval rate without its denominator: 100% of 2 vs 75% of 4</text>
    <text x="30" y="52" fill="var(--s2)" font-size="8">degraded</text>
    <rect x="110" y="38" width="26" height="22" fill="var(--s1)"></rect><rect x="140" y="38" width="26" height="22" fill="var(--s1)"></rect>
    <rect x="170" y="38" width="26" height="22" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="3 2"></rect><rect x="200" y="38" width="26" height="22" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="3 2"></rect><rect x="230" y="38" width="26" height="22" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="3 2"></rect>
    <text x="185" y="53" fill="var(--muted)" font-size="9">?</text><text x="213" y="53" fill="var(--muted)" font-size="9">?</text><text x="243" y="53" fill="var(--muted)" font-size="9">?</text>
    <text x="280" y="53" fill="var(--s2)" font-size="8">100% — but of only 2; 3 unheard → no quorum</text>
    <text x="30" y="112" fill="var(--s1)" font-size="8">healthy</text>
    <rect x="110" y="98" width="26" height="22" fill="var(--s1)"></rect><rect x="140" y="98" width="26" height="22" fill="var(--s1)"></rect><rect x="170" y="98" width="26" height="22" fill="var(--s1)"></rect><rect x="200" y="98" width="26" height="22" fill="var(--s2)"></rect>
    <rect x="230" y="98" width="26" height="22" fill="var(--panel)" stroke="var(--line)" stroke-dasharray="3 2"></rect><text x="243" y="113" fill="var(--muted)" font-size="9">?</text>
    <text x="280" y="113" fill="var(--s1)" font-size="8">75% of 4 — lower rate, more evidence</text>
    <text x="30" y="150" fill="var(--muted)" font-size="8">the higher rate rests on fewer voters; the quorum counts the empty slots</text>
  </g>
</svg>
^ The degraded round's 100% is 100% of two voters with three unheard; the healthy round's 75% rests on four. The naive rule sees only the rate and ranks degraded highest; the quorum rule counts the empty slots and throws it out.

Read the approval-of-responders column against the responded column. The degraded round has the highest approval rate of all three — 100% — and it is the least trustworthy, because it is 100% of only two voters. The healthy round's 75% is lower but worth far more, because it is 75% of four. The naive rule sees only the rate and so ranks the degraded round as the most approved; the quorum rule sees the denominator and throws the degraded round out. A rate without its sample size is not evidence, and the naive rule acts on the rate alone.

**A vote is trustworthy only when enough of the panel responded, so require a quorum before counting it — majority-of-responders reports 100% approval on two of five voters and authorizes the action, while a quorum gate returns inconclusive and escalates, because an approval rate without its denominator measures who was reachable, not what the panel decided.**

### The self-test

The `--check` mode plants the bug — majority of responders — and proves it: the naive rule acts on the degraded round while the quorum rule blocks it, both act on the healthy round, and the quorum rule returns no-quorum exactly when too few responded.

```
# $ python3 quorum.py --check
#   naive ACTS on the degraded round (2 of 5 replied) = True (approve)
#   the quorum rule does NOT act on the degraded round = True (no-quorum)
#   both rules act on the healthy round (4 of 5 replied) = True (naive=approve, quorum=approve)
#   the quorum rule returns no-quorum exactly when responders < quorum = True
#   SELF-TEST PASS ...
```

run: 2026-08-27 · deterministic · `python3 quorum.py --check`

The `both_act_healthy` line is the one that keeps the quorum rule from being mere caution: a rule that blocked everything would also block the degraded round, but it would be useless. The quorum rule must approve the well-supported healthy round to show it blocks under-support specifically, not decisions in general. And `gates_on_responses` proves the guard is exactly a response-count threshold, nothing more — it does not second-guess the majority when the panel showed up.

```
# quorum.py:112-117 — COMPLETE (naive acts on the degraded round; the quorum rule blocks it)
    naive_acts_degraded = acts(decide_naive(degraded))
    print("  naive ACTS on the degraded round (2 of 5 replied) = %s (%s)"
          % (naive_acts_degraded, decide_naive(degraded)))

    quorum_blocks_degraded = not acts(decide_quorum(degraded, q))
    print("  the quorum rule does NOT act on the degraded round = %s (%s)"
          % (quorum_blocks_degraded, decide_quorum(degraded, q)))
```

### The running tally

| round | responded | yes / no | approval rate | naive | quorum |
|---|---|---|---|---|---|
| degraded | 2 / 5 | 2 / 0 | 100% | approve | no-quorum |
| healthy | 4 / 5 | 3 / 1 | 75% | approve | approve |
| contested | 4 / 5 | 1 / 3 | 25% | withhold | withhold |

Read the approval-rate column against the two decision columns. The naive rule is a pure function of the rate — it approves the two rounds with rate above 50% and withholds the one below, so it ranks the 100% degraded round as its most confident approval. The quorum rule adds the responded column as a gate, and that one addition flips exactly the degraded round from approve to blocked while leaving the two well-attended rounds alone. The two rules agree on every round where the panel turned out and disagree only where it did not — which is precisely the behavior a governance gate should have.

### What we did not settle

This is the response-count quorum, the floor under any panel vote; real governance layers more on top. The quorum size itself is a policy choice — a strict majority of the panel (3 of 5 here), or a supermajority for higher-stakes actions — and it should scale with how irreversible the action is. Timeouts here are neutral, but a cautious policy might treat a timeout as an implicit no for an irreversible action (fail-safe) rather than an abstention. The quorum guards representativeness, not correctness: govern-inter-02 is the companion point that even a full, well-attended council only helps when its voters fail independently, so a quorum of correlated voters can be unanimous and wrong. And a repeatedly no-quorum gate is itself a signal — the panel is unhealthy — that should page a human rather than silently stall. The invariant: never trust a vote whose panel did not show up, and never let an approval rate be read without its denominator.

## Build

The build in one paragraph: before counting a panel's vote, require a quorum of responses — a minimum number of voters who actually replied — and if fewer responded, return inconclusive and escalate rather than acting on the majority of a non-representative handful; above the quorum, take the majority as usual. Keep the responded count separate from the panel total so the gap is visible, never read an approval rate without its denominator, size the quorum to the action's irreversibility, and page a human when a panel repeatedly fails to reach quorum.

We opened on the degraded round. The number that proves the fix is the decision on the round where only two of five replied:

```
# modules/orchestration-and-governance/code/govern-inter-07/ — COMPLETE, run from that directory
$ python3 quorum.py --check
  naive ACTS on the degraded round (2 of 5 replied) = True (approve)
  the quorum rule does NOT act on the degraded round = True (no-quorum)
```

Now build your own. Take a real approval panel or voting quorum and simulate rounds with some voters timing out. Your number to beat is not the approval rate; it is **the decision under partial response: the naive rule should authorize an action on a minority of the panel while your quorum rule withholds it, and both should agree on a well-attended round**. Confirm your quorum returns inconclusive exactly when responders fall below the threshold. Bring back both rules' decisions on a degraded round. Good luck.

## Definition of done

- [ ] A tally separating panel total from responders (timeouts excluded)
- [ ] A naive rule: majority of responders
- [ ] A quorum rule: inconclusive below a response threshold, majority above it
- [ ] Confirmation the naive rule acts on a degraded round (too few responders)
- [ ] Confirmation the quorum rule withholds that round and both act on a healthy round
- [ ] Confirmation the quorum returns no-quorum exactly when responders fall below the threshold
- [ ] `python3 quorum.py --check` printing SELF-TEST PASS: naive_acts_degraded, quorum_blocks, both_act_healthy, gates_on_responses
- [ ] Dated recall pass in the ledger

## Boss fight

From memory, module closed, no notes.

1. Why does "majority of whoever answered" break under partial availability? What does it silently redefine?
2. The degraded round had 100% approval. Why is that the least trustworthy of the three rounds?
3. What does the quorum rule check before it looks at the yes/no split, and what does it return if that check fails?
4. Why does the self-test insist both rules approve the healthy round, not just that the quorum blocks the degraded one?
5. Your own panel was run with timeouts. What did each rule decide on a degraded round, and did they agree on a well-attended one?

## External resources

- Distributed-systems material on quorums (Paxos/Raft majority quorums, or a database's read/write quorum) — my summary: why a majority of a known membership is required to make a decision safely under failures; read it for the same denominator discipline applied to replicated state.
- Any deliberative body's quorum rules (parliamentary procedure, board bylaws) — my summary: the long-standing human institution of refusing to transact business below a quorum; read it to see this module's rule as an old idea, not a new one.
- This hub, *govern-inter-02* (councils help only when voters fail independently) — read it for the companion caveat: a quorum ensures the panel showed up, but not that its members are independent, and correlated voters can be unanimous and wrong.
