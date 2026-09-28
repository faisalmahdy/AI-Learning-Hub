---
id: splitvote-inter-01
title: Randomize the election timeout — identical timeouts split the vote and elect no leader, forever
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: In a leader-election protocol, when the leader fails each follower waits an election timeout, then starts an election — increment the term, vote for itself, ask the others for votes — and a candidate becomes leader only with a majority. The failure is symmetry: give every node the same fixed timeout and they all time out at the same instant, all become candidates in the same term, and all vote for themselves before any can grant a vote to another, so each candidate ends with exactly one vote, none has a majority, and the term produces no leader; then they all time out together again and the split repeats — an election livelock with no progress and no leader. The fix is to draw each node's timeout at random from a range so the values differ: one node has the smallest timeout, times out first, becomes the sole candidate, and asks the others while they are still waiting, so they grant and it reaches a majority before anyone else starts a competing election. On the fixture five nodes need a majority of three: with equal timeouts of 150 every node self-votes, each candidate has one vote, and no leader is elected; with distinct timeouts the node at 150 is the unique earliest, collects all five votes, and wins in one round. The randomness does nothing but break the tie, and breaking the tie is the whole point — this is why Raft and similar protocols specify a randomized election timeout rather than a constant.
eli5: Imagine a group of friends deciding who leads, where the rule is "if no one has spoken up after a countdown, put your own hand up and ask everyone to vote for you." If everyone counts down from the exact same number, they all throw their hands up at the same second, each votes for themselves, and nobody gets more than one vote — so no leader, and they start the countdown over and do it again, stuck. The fix is to let each person count down from a slightly different number. Then one person's countdown ends first, they raise their hand while everyone else is still counting, and everyone else just votes for them. The different countdowns don't make anyone a better leader — they only make sure one person goes first.
---

## Why this module

Leader election is how a cluster picks the one node allowed to make decisions, and it has to work exactly when things are worst: the old leader just died, every remaining node notices at about the same time, and they all want to fix it. That simultaneity is the trap. A protocol that is correct when one node acts can deadlock when all of them act at once.

The specific way it deadlocks is a split vote — every node nominates itself, no one wins, and the cluster sits leaderless while the elections churn. What breaks the deadlock is not a smarter voting rule but a dumber one: make the nodes not act in unison, by giving each a different timeout.

**A leader election fails not from a bad vote-counting rule but from every node acting at the same instant, and randomizing the timeout is what desynchronizes them.**

## Concepts

The election protocol is simple. A follower that has not heard from a leader within its election timeout becomes a candidate: it advances to a new term, votes for itself, and requests votes from every other node. Each node grants its vote to the first candidate that asks it in a given term, and it will only ask once it has itself timed out. A candidate that collects a majority becomes leader.

Now make every node's timeout the same constant. When the leader dies, all followers' timeouts expire at the same instant. Every one of them becomes a candidate in the same term simultaneously, and the first thing a candidate does is vote for itself — so before any node can grant its vote to a peer, its vote is already spent on itself. Each candidate ends the term with exactly one vote. With more than two nodes, one vote is not a majority, so no one wins.

That is a split vote, and it is stable. The term ends with no leader, so the nodes time out again — still on the same constant, still in unison — and produce another split. Nothing is blocked; the cluster is busy holding elections. It just never elects anyone. This is a livelock, and a leaderless cluster usually cannot serve writes, so it is an outage.

Randomizing the timeout removes the simultaneity that causes it. Draw each node's timeout uniformly from a range, and the nodes no longer expire together. One node has the smallest draw; it times out first, becomes the sole candidate, and requests votes while every other node is still below its own timeout — so they have not self-voted, and they grant. That candidate reaches a majority and wins before the next node even wakes up. The randomness carries no information about who should lead; its only job is to make one node go first.

**Identical timeouts make every node a self-voting candidate at once, so no one gets a majority; randomized timeouts make one node time out first and win before the others start.**

<svg role="img" aria-label="Two rows. Symmetric: all nodes fire at the same time and tie, no leader. Broken symmetry: nodes fire at staggered times, the first one wins." viewBox="0 0 320 140">
<rect x="0" y="0" width="320" height="140" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">symmetry is the bug; staggering is the fix</text>
<text x="20" y="46" fill="var(--s1)" font-size="10">same timeout</text>
<circle cx="150" cy="42" r="4" fill="var(--s1)"></circle>
<circle cx="158" cy="42" r="4" fill="var(--s1)"></circle>
<circle cx="166" cy="42" r="4" fill="var(--s1)"></circle>
<circle cx="174" cy="42" r="4" fill="var(--s1)"></circle>
<text x="190" y="46" fill="var(--s1)" font-size="9">all at once &#8594; tie, no leader</text>
<text x="20" y="96" fill="var(--s2)" font-size="10">random timeout</text>
<circle cx="120" cy="92" r="4" fill="var(--s2)"></circle>
<circle cx="150" cy="92" r="4" fill="var(--muted)"></circle>
<circle cx="180" cy="92" r="4" fill="var(--muted)"></circle>
<circle cx="210" cy="92" r="4" fill="var(--muted)"></circle>
<text x="120" y="118" fill="var(--s2)" font-size="9">first one wins &#8594; a leader</text>
</svg>
^ When all nodes are identical they act together and no unique winner can emerge; distinct timeouts give one node a head start, and one head start is all the election needs.

## Worked example

Source: faisalmahdy/AI-Learning-Hub — modules/orchestration-and-governance/code/splitvote-inter-01/splitvote.py

The fixture is five nodes, once with equal timeouts and once with distinct ones.

```json filename=modules/orchestration-and-governance/code/splitvote-inter-01/splitvote.json:3-4 COMPLETE
  "fixed_timeouts": [150, 150, 150, 150, 150],
  "randomized_timeouts": [150, 165, 170, 180, 195]
```

A majority is more than half, and the election gives the sole earliest candidate everyone's vote, or lets a tie self-vote.

```python filename=modules/orchestration-and-governance/code/splitvote-inter-01/splitvote.py:30-32 COMPLETE
def majority(n):
    """Votes needed to win: more than half the nodes."""
    return n // 2 + 1
```

```python filename=modules/orchestration-and-governance/code/splitvote-inter-01/splitvote.py:35-48 COMPLETE
def elect(timeouts):
    """Run one election round: the earliest node(s) become candidates; a sole earliest wins all votes, a tie self-votes."""
    n = len(timeouts)
    smallest = min(timeouts)
    earliest = [i for i, t in enumerate(timeouts) if t == smallest]
    votes = {i: 0 for i in range(n)}
    if len(earliest) == 1:
        votes[earliest[0]] = n           # sole candidate asks first, everyone grants
    else:
        for c in earliest:
            votes[c] = 1                 # simultaneous candidates each vote for themselves
    top = max(votes.values())
    winner = max(votes, key=votes.get) if top >= majority(n) else None
    return winner, votes
```

Run the equal-timeout case and no one wins.

```text filename=splitvote.py --fixed
FIXED — 5 nodes, majority 3, timeouts [150, 150, 150, 150, 150]
----------------------------------------------------------------
  votes: {0: 1, 1: 1, 2: 1, 3: 1, 4: 1}
  winner: NONE (split vote)
----------------------------------------------------------------
  all time out together, all self-vote, none reaches a majority -- the election repeats
```

Five candidates, one vote each, majority three — no one reaches it. The cluster has no leader, and because every node will time out again on the same 150, the next round splits identically. It never converges.

<svg role="img" aria-label="Five nodes all timing out at the same time 150, each raising a hand for itself, each with one vote, none reaching the majority line of three." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">equal timeouts: all self-vote at t=150</text>
<line x1="30" y1="60" x2="290" y2="60" stroke="var(--grid)" stroke-dasharray="4 3"></line>
<text x="294" y="63" fill="var(--muted)" font-size="9">majority 3</text>
<rect x="40" y="95" width="30" height="25" fill="var(--s1)"></rect>
<rect x="90" y="95" width="30" height="25" fill="var(--s1)"></rect>
<rect x="140" y="95" width="30" height="25" fill="var(--s1)"></rect>
<rect x="190" y="95" width="30" height="25" fill="var(--s1)"></rect>
<rect x="240" y="95" width="30" height="25" fill="var(--s1)"></rect>
<text x="46" y="134" fill="var(--muted)" font-size="9">1</text>
<text x="96" y="134" fill="var(--muted)" font-size="9">1</text>
<text x="146" y="134" fill="var(--muted)" font-size="9">1</text>
<text x="196" y="134" fill="var(--muted)" font-size="9">1</text>
<text x="246" y="134" fill="var(--muted)" font-size="9">1</text>
<text x="40" y="86" fill="var(--s1)" font-size="9">each candidate: 1 vote, none clears the line</text>
</svg>
^ Every node's single self-vote falls short of the majority line, and since all five reset on the same timeout the split recurs every round — a leaderless livelock.

## Build

Distinct timeouts break the symmetry and elect in one round.

```text filename=splitvote.py --randomized
RANDOMIZED — 5 nodes, majority 3, timeouts [150, 165, 170, 180, 195]
----------------------------------------------------------------
  votes: {0: 5, 1: 0, 2: 0, 3: 0, 4: 0}
  winner: node 0
----------------------------------------------------------------
  the earliest node times out first and collects a majority before others start
```

Node 0 has the smallest timeout, so it times out first, asks while nodes 1–4 are still waiting, and they all grant — five votes, a clear majority, elected. No other node ever became a candidate.

<svg role="img" aria-label="Five nodes on a timeline with staggered timeouts. Node 0 at 150 fires first and collects votes from the others, which have not yet timed out at 165, 170, 180, 195." viewBox="0 0 320 150">
<rect x="0" y="0" width="320" height="150" fill="var(--panel)"></rect>
<text x="12" y="18" fill="var(--ink)" font-size="12">distinct timeouts: node 0 fires first and wins</text>
<line x1="40" y1="110" x2="290" y2="110" stroke="var(--line)"></line>
<circle cx="60" cy="110" r="6" fill="var(--s2)"></circle>
<text x="50" y="100" fill="var(--s2)" font-size="9">n0 150</text>
<circle cx="120" cy="110" r="4" fill="var(--muted)"></circle>
<text x="108" y="128" fill="var(--muted)" font-size="8">n1 165</text>
<circle cx="140" cy="110" r="4" fill="var(--muted)"></circle>
<text x="150" y="128" fill="var(--muted)" font-size="8">n2 170</text>
<circle cx="180" cy="110" r="4" fill="var(--muted)"></circle>
<text x="186" y="128" fill="var(--muted)" font-size="8">n3 180</text>
<circle cx="240" cy="110" r="4" fill="var(--muted)"></circle>
<text x="228" y="128" fill="var(--muted)" font-size="8">n4 195</text>
<line x1="60" y1="104" x2="120" y2="104" stroke="var(--s2)"></line>
<line x1="60" y1="100" x2="180" y2="88" stroke="var(--s2)"></line>
<text x="70" y="80" fill="var(--s2)" font-size="9">n0 asks; others grant (still waiting) &#8594; 5 votes</text>
</svg>
^ Node 0's earlier timeout lets it request votes while the others are still counting down, so it collects a majority before any of them can nominate itself.

The self-test states both outcomes and pins the winner.

```python filename=modules/orchestration-and-governance/code/splitvote-inter-01/splitvote.py:81-85 COMPLETE
    fixed_no_leader = fw is None
    print("  fixed timeouts elect no leader (split vote) = %s (votes %s)" % (fixed_no_leader, fv))

    fixed_all_self = all(v == 1 for v in fv.values())
    print("  every node got exactly one vote (all self-voted) = %s" % fixed_all_self)
```

```python filename=modules/orchestration-and-governance/code/splitvote-inter-01/splitvote.py:91-94 COMPLETE
    winner_is_earliest = rw == min(range(len(rand)), key=lambda i: rand[i])
    print("  the elected node is the one with the smallest timeout = %s" % winner_is_earliest)

    winner_has_majority = rv[rw] >= majority(n) if rw is not None else False
    print("  the winner reached a majority = %s (%d of needed %d)" % (winner_has_majority, rv[rw] if rw is not None else 0, majority(n)))
```

```text filename=splitvote.py --check
SELF-TEST — fixed timeouts elect no leader while randomized timeouts elect exactly the earliest node with a majority
----------------------------------------------------------------------------------------------------------------
  fixed timeouts elect no leader (split vote) = True (votes {0: 1, 1: 1, 2: 1, 3: 1, 4: 1})
  every node got exactly one vote (all self-voted) = True
  randomized timeouts elect a leader = True (node 0)
  the elected node is the one with the smallest timeout = True
  the winner reached a majority = True (5 of needed 3)
----------------------------------------------------------------------------------------------------------------
SELF-TEST PASS  fixed_no_leader=True  fixed_all_self=True  random_elects=True  winner_is_earliest=True  winner_has_majority=True
```

**winner_is_earliest is the honest part: the randomness picks the leader by nothing but who drew the shortest timeout — it is not choosing a better node, only choosing one node, which is all the election needs.**

## Definition of done

You can trace why identical timeouts produce a split vote: all nodes time out together, each self-votes before it can grant a vote to a peer, so each candidate has one vote and none has a majority.

You can explain why the split is stable and therefore a livelock — the nodes reset on the same timeout and repeat the split, leaving the cluster leaderless.

You can describe how randomizing the timeout fixes it: one node times out first and collects votes while the others are still waiting, winning before any competing candidacy starts.

You can state that the randomness carries no information about leadership quality — it only breaks the symmetry — and name a real protocol (Raft) that specifies a randomized election timeout for this reason.

## Boss fight

Your five-node cluster loses its leader during a network blip, and instead of re-electing quickly it goes leaderless for several seconds, cycling through terms with no winner, before finally recovering. The logs show every node becoming a candidate in the same term, over and over.

First: explain what the logs are showing in terms of this module, and why the cluster does eventually recover on its own even with identical timeouts — what tiny real-world difference eventually lets one node win, and why relying on it is a bug, not a feature.

Then: you randomize the timeout, and now you must pick the range. Too narrow a range and the problem persists; too wide and re-election is slow. Explain the tension — what a range narrower than the vote round-trip time does, and what a very wide range costs — and how the range should relate to the time it takes a candidate to collect votes.

Finally: randomized timeouts make a single split unlikely but not impossible — two nodes can still draw close values and split. Explain why the protocol does not need to prevent every split, only to make repeated splits improbable, and how a fresh random timeout on each failed term turns a possible split into a quickly self-correcting one rather than a stable livelock.

## External resources

The Raft paper's leader-election section specifies randomized election timeouts precisely to avoid split votes, and its discussion of choosing the timeout range against the broadcast (vote round-trip) time is exactly the boss fight's tension.

Any treatment of symmetry breaking in distributed algorithms (leader election on a ring, exponential backoff for contention) is the same idea generalized: identical deterministic behavior across symmetric nodes cannot elect a unique one, and randomness is the standard way to break the tie.
