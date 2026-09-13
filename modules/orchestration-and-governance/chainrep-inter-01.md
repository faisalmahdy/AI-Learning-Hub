---
id: chainrep-inter-01
title: Replicate with a chain — writes head-to-tail, reads and acks at the tail — so a read never returns a value the whole chain doesn't have
topic: orchestration-and-governance
level: intermediate
status: ready
time: 15 min
summary: Chain replication orders the replicas in a line — head, middle(s), tail — applies a write at the head and passes it down one hop at a time, commits (acknowledges) it only when it reaches the tail, and serves all reads from the tail. That arrangement buys strong consistency almost for free through one structural invariant: because propagation is strictly head-to-tail, the replicas holding the new value are always a prefix of the chain, so if the tail holds the new value every replica ahead of it does too — the tail is the last to know, which is exactly why trusting it is safe. A read at the tail therefore returns a value guaranteed present on every replica, an acknowledged write (one that reached the tail) is visible to every later tail read, reads are linearizable and never stale relative to an acknowledged write, and two simultaneous reads cannot disagree because they all go to the one tail. Naive replication breaks both halves: it acknowledges as soon as the first replica (the head) applies the write, before the others catch up, and it lets a read hit any replica — so a read to a lagging replica returns the old value even after the write was acknowledged (a stale read of committed data), and two reads at the same moment to different replicas can disagree. On a fixture where a write flows through three replicas, whenever the tail holds the new value the whole chain does, while a naive scheme that acknowledges once the head has the write then reads the tail returns the stale old value.
eli5: Imagine passing a note down a line of people, front to back, and the rule is: the note "counts as delivered" only when the very last person has it, and whenever you want to know the note you ask the last person. Since the note travels front-to-back, if the last person has it, everyone in front of them definitely has it too — so the last person's answer is always safe and complete. The sloppy way is to say "delivered!" the moment the first person gets it and then ask anyone in the line: you might ask someone the note hasn't reached yet and get the old answer, and two people you ask might tell you different things. Asking only the last person, and only calling it done when they have it, keeps everyone's answer consistent.
---

## Why this module

Replicating data for durability creates a consistency problem: with several copies, a reader can reach a copy that has not yet seen the latest write, and two readers can see different things at the same moment. The usual escapes are quorums (contact a majority and reconcile) or a primary that funnels everything through one node. Chain replication is a third design that gets strong consistency from pure topology, and it is worth understanding because the guarantee falls out of the shape rather than from voting or version reconciliation.

The shape is a line, and the two rules are: writes travel head to tail, and reads and acknowledgements happen at the tail. The consequence is an invariant that does all the work — since a write only ever moves forward along the chain, the replicas that have it form a prefix, and the tail is the end of the line, so the tail having the write means the prefix is the whole chain. The tail is deliberately the last to learn anything, and that is precisely what makes it the safe place to read: it can never show you a value that the rest of the chain is still catching up to.

Contrast this with the tempting shortcut of writing to replicas asynchronously, calling the write done when the first one acknowledges, and reading from whichever replica is closest. This module runs a write down a three-replica chain and compares reading the tail against reading any replica.

**Because writes propagate strictly head-to-tail and the tail is last, a value present at the tail is present on every replica — so tail reads are consistent and never stale relative to an acknowledged write, whereas acknowledging at the first replica and reading any replica returns stale, divergent reads.**

## Concepts

The fixture is the value of each replica — head, middle, tail — at each step as a new write flows down the chain.

```json filename=modules/orchestration-and-governance/code/chainrep-inter-01/chainrep.json:3-8 COMPLETE
  "propagation": [
    ["old", "old", "old"],
    ["new", "old", "old"],
    ["new", "new", "old"],
    ["new", "new", "new"]
  ],
```

A chain read returns the tail's value. The chain invariant checks that if the tail holds the new value, every replica does. A divergence check asks whether the replicas disagree at a given instant — the hazard a read-from-any scheme exposes.

```python filename=modules/orchestration-and-governance/code/chainrep-inter-01/chainrep.py:32-45 COMPLETE
def tail_read(state, tail_index):
    return state[tail_index]


def tail_committed_implies_all(state, tail_index, new="new"):
    """Chain invariant: if the tail holds the new value, every replica does."""
    if state[tail_index] == new:
        return all(v == new for v in state)
    return True


def diverges(state):
    """Do the replicas disagree at this instant (a read-from-any hazard)?"""
    return len(set(state)) > 1
```

The invariant is the whole guarantee in one line: `state[tail] == new` implies `all(v == new)`. It holds for free because propagation is head-to-tail, so the tail is never ahead of the replicas before it.

<svg role="img" aria-label="A write flowing down a chain head to middle to tail; at each step the new value fills a prefix, and only when the tail is filled is the whole chain filled" viewBox="0 0 320 120">
  <text x="10" y="12" font-size="8" fill="var(--muted)">new value (filled) spreads head → tail; tail last</text>
  <g font-size="7">
  <text x="6" y="34" fill="var(--muted)">s1</text>
  <rect x="26" y="26" width="30" height="14" fill="var(--s1)"/><rect x="58" y="26" width="30" height="14" fill="none" stroke="var(--line)"/><rect x="90" y="26" width="30" height="14" fill="none" stroke="var(--line)"/>
  <text x="6" y="58" fill="var(--muted)">s2</text>
  <rect x="26" y="50" width="30" height="14" fill="var(--s1)"/><rect x="58" y="50" width="30" height="14" fill="var(--s1)"/><rect x="90" y="50" width="30" height="14" fill="none" stroke="var(--line)"/>
  <text x="6" y="82" fill="var(--muted)">s3</text>
  <rect x="26" y="74" width="30" height="14" fill="var(--s1)"/><rect x="58" y="74" width="30" height="14" fill="var(--s1)"/><rect x="90" y="74" width="30" height="14" fill="var(--s1)"/>
  <text x="30" y="102" fill="var(--muted)">head</text><text x="62" y="102" fill="var(--muted)">mid</text><text x="94" y="102" fill="var(--muted)">tail</text>
  </g>
  <text x="140" y="40" font-size="7.5" fill="var(--ink)">tail filled ⇒ head and mid filled</text>
  <text x="140" y="56" font-size="7.5" fill="var(--ink)">(the tail is the last box to fill)</text>
  <text x="140" y="82" font-size="7.5" fill="var(--s1)">so reading the tail is always safe</text>
</svg>
^ The new value fills a prefix of the chain that grows head-to-tail; the tail's box is the last to fill. So the moment the tail has the new value, every box before it does too — the invariant that makes a tail read safe.

**The chain invariant — tail holds new implies all hold new — is a free consequence of head-to-tail propagation, so the tail is the one replica whose value is always fully replicated.**

## Worked example

Source: faisalmahdy/AI-Learning-Hub — the replication step of a strongly-consistent store, reduced to three replicas so every step is checkable by hand.

Run `--propagate` to watch the write flow down.

```text filename=chainrep.py --propagate
  step   head   middle  tail
  0      old    old     old
  1      new    old     old
  2      new    new     old
  3      new    new     new
```

At step 1 only the head has the new value; at step 2 the head and middle; at step 3 all three. At every step the replicas holding "new" are a prefix ending no later than the tail, and the tail holds "new" only at step 3 — the same step at which all three do. That is the invariant playing out: the tail is never the odd one out ahead of the others.

Now `--read` compares the two read strategies at each step, flagging divergence.

```python filename=modules/orchestration-and-governance/code/chainrep-inter-01/chainrep.py:66-67 COMPLETE
    for i, s in enumerate(prop):
        print("  %-5d  %-11s   %-15s  %s" % (i, tail_read(s, tail), s, diverges(s)))
```

The divergent column marks where read-from-any is unsafe.

```text filename=chainrep.py --read
  step   chain(tail)   naive replicas   divergent?
  0      old           ['old', 'old', 'old']  False
  1      old           ['new', 'old', 'old']  True
  2      old           ['new', 'new', 'old']  True
  3      new           ['new', 'new', 'new']  False
```

The chain read returns old at steps 0–2 and new at step 3 — and every one of those values is held by all three replicas at that step (old is fully replicated through step 2 in the sense that the committed value is still old; new is fully replicated at step 3). A naive read-from-any is different: at steps 1 and 2 the replicas diverge, so a read hitting the head returns new while a read hitting the tail returns old, at the same instant. Worse, a naive scheme acknowledges the write once the head has it at step 1 — and a read to the tail right after that acknowledgement returns old, a stale read of data the client was told is committed. The chain never has that window, because it does not acknowledge until the tail, and it does not read anywhere but the tail.

<svg role="img" aria-label="At step 1 the chain reads the tail (old, fully committed) while naive reads can hit the head (new) or tail (old), disagreeing, and naive has already acknowledged the write" viewBox="0 0 320 120">
  <text x="10" y="14" font-size="8.5" fill="var(--muted)">reading just after the write starts (step 1)</text>
  <text x="14" y="36" font-size="8" fill="var(--s1)">chain: read tail</text>
  <rect x="120" y="26" width="50" height="14" fill="var(--s1)"/><text x="126" y="37" font-size="7.5" fill="var(--panel)">old</text>
  <text x="176" y="37" font-size="7.5" fill="var(--ink)">consistent (not yet acked)</text>
  <text x="14" y="64" font-size="8" fill="var(--s2)">naive: read any</text>
  <rect x="120" y="54" width="40" height="14" fill="var(--s2)"/><text x="126" y="65" font-size="7" fill="var(--panel)">head:new</text>
  <rect x="162" y="54" width="40" height="14" fill="none" stroke="var(--s2)"/><text x="168" y="65" font-size="7" fill="var(--s2)">tail:old</text>
  <text x="208" y="65" font-size="7.5" fill="var(--ink)">disagree — and already acked!</text>
  <text x="14" y="96" font-size="7.5" fill="var(--muted)">naive acked at step 1 but a tail read still says old — a stale read of committed data</text>
</svg>
^ Just after the write starts, the chain reads only the tail and gets a consistent value (it has not acknowledged yet). Naive replication has already acknowledged (the head applied it) but its replicas disagree, so a read can return either value — including a stale old from a lagging replica.

**The chain read returns a fully-replicated value at every step, while naive read-from-any diverges mid-propagation and, having acknowledged at the head, serves a stale old value from the tail — committed data read as absent.**

## Build

The self-test establishes the guarantee: the chain invariant holds at every step, and every tail read returns a value present on all replicas.

```python filename=modules/orchestration-and-governance/code/chainrep-inter-01/chainrep.py:77-88 COMPLETE
    chain_invariant_holds = all(tail_committed_implies_all(s, tail) for s in prop)
    print("  chain invariant holds at every step (tail=new => all=new) = %s" % chain_invariant_holds)

    tail_read_always_replicated = all(
        (tail_read(s, tail) != "new") or all(v == "new" for v in s) for s in prop)
    print("  every tail read returns a value present on all replicas = %s" % tail_read_always_replicated)

    # naive: acknowledge as soon as the head has the write
    head_ack_step = next(i for i, s in enumerate(prop) if s[0] == "new")
    naive_ack_then_tail_stale = prop[head_ack_step][tail] != "new"
    print("  naive: after head-acknowledges (step %d), a tail read is stale = %s (%s)"
          % (head_ack_step, naive_ack_then_tail_stale, prop[head_ack_step][tail]))
```

Then the contrast and the commit semantics: naive read-from-any can diverge, and when the chain commits (tail has the write) it is genuinely on every replica.

```python filename=modules/orchestration-and-governance/code/chainrep-inter-01/chainrep.py:90-95 COMPLETE
    naive_reads_can_diverge = any(diverges(s) for s in prop)
    print("  naive read-from-any can return divergent values across replicas = %s" % naive_reads_can_diverge)

    commit_step = next(i for i, s in enumerate(prop) if s[tail] == "new")
    chain_committed_everywhere = all(v == "new" for v in prop[commit_step])
    print("  when the chain commits (tail=new at step %d) the write is on every replica = %s" % (commit_step, chain_committed_everywhere))
```

Running the check confirms every clause.

```text filename=chainrep.py --check
  chain invariant holds at every step (tail=new => all=new) = True
  every tail read returns a value present on all replicas = True
  naive: after head-acknowledges (step 1), a tail read is stale = True (old)
  naive read-from-any can return divergent values across replicas = True
  when the chain commits (tail=new at step 3) the write is on every replica = True
```

**The check shows the chain invariant and tail-read safety holding at every step, and the naive scheme both diverging across replicas and serving a stale tail read after its early acknowledgement — consistency from topology versus a race from acknowledging and reading anywhere.**

## Definition of done

Done means tail reads are shown always fully-replicated and chain commits shown to be everywhere, while the naive acknowledge-early read-any scheme is shown to go stale and diverge. The invariant clause is the load-bearing one: it proves the consistency is a property of the chain's shape, not of luck or timing, so it holds under any propagation speed rather than only in the lucky case.

Two clarifications ground this. First, the strength of chain replication is not just consistency but the simplicity of its failure handling, which is why it is used in real systems. If the head fails, its successor becomes the new head; if the tail fails, its predecessor becomes the new tail (and the same prefix invariant keeps reads safe); a middle failure is patched by linking its neighbors — each case is a local, well-defined reconfiguration coordinated by a small master, with no quorum voting on the data path. The tradeoff is write latency: a write must traverse the whole chain before it is acknowledged, so latency grows with chain length, and the head and tail carry asymmetric load. Second, chain replication is one point in a design space alongside the neighbors in this topic: primary-backup routes all reads and writes through one primary (simpler, but the primary is a bottleneck and a read from a lagging backup is stale — the same naive hazard); quorum systems (R + W > N) trade per-operation voting for flexible latency and no fixed head/tail; and the CRAQ variant of chain replication lets any replica serve reads by having non-tail replicas check with the tail for the committed version, recovering read throughput while keeping the guarantee. The through-line across all of them is the rule this module isolates: never treat a value as readable-and-consistent until it is known to be on every replica the design relies on, and pick the single place (here, the tail) whose answer certifies that.

<svg role="img" aria-label="Chain replication tradeoffs: simple local failure recovery and strong consistency, at the cost of write latency growing with chain length; CRAQ lets non-tail replicas serve reads" viewBox="0 0 320 118">
  <rect x="14" y="22" width="150" height="42" fill="none" stroke="var(--s1)"/>
  <text x="22" y="37" font-size="7.5" fill="var(--s1)">chain replication</text>
  <text x="22" y="49" font-size="7" fill="var(--ink)">strong consistency + simple</text>
  <text x="22" y="58" font-size="7" fill="var(--ink)">local failure recovery</text>
  <rect x="176" y="22" width="130" height="42" fill="none" stroke="var(--s2)"/>
  <text x="184" y="37" font-size="7.5" fill="var(--s2)">cost / variant</text>
  <text x="184" y="49" font-size="7" fill="var(--ink)">write latency ∝ length;</text>
  <text x="184" y="58" font-size="7" fill="var(--ink)">CRAQ: any replica reads</text>
  <text x="14" y="84" font-size="7.5" fill="var(--muted)">rule: a value is consistent-readable only when it is on every replica relied on</text>
  <text x="14" y="104" font-size="7.5" fill="var(--ink)">the tail is the single place whose answer certifies full replication</text>
</svg>
^ Chain replication gives strong consistency and simple local failure recovery (promote a neighbor), at the cost of write latency that grows with chain length; the CRAQ variant lets non-tail replicas serve reads by checking the tail's committed version. The general rule is to designate one place — here the tail — whose answer certifies a value is on every replica.

**Done means tail reads are always fully-replicated and chain commits are everywhere while naive acknowledge-early read-any goes stale and diverges — so replicate with a chain (writes head-to-tail, reads and acks at the tail), reading a value as consistent only once the certifying replica confirms it is everywhere.**

## Boss fight

A team runs a replicated key-value store with three copies. To cut latency they write to all three asynchronously, acknowledge the write as soon as any one copy confirms, and let clients read from whichever copy is nearest. Users occasionally report that a value they just successfully wrote reads back as the old value, and that two clients see different values for the same key at the same time. How would you restructure replication to fix both, and what does it cost?

Both symptoms are the naive acknowledge-early, read-any hazard. Acknowledging as soon as one copy confirms means the write is reported successful before the other two copies have it, so a read to a lagging copy returns the old value even though the client was told the write committed — the "reads back as old" complaint. Reading from whichever copy is nearest means two clients can hit copies at different points in receiving the write, so they see different values at the same instant — the "two clients disagree" complaint. Neither can be fixed by tuning; they are inherent to committing before full replication and reading from any replica. The restructure is chain replication: arrange the three copies in a chain (head, middle, tail), send every write to the head and propagate it strictly down the chain, acknowledge the write to the client only when it reaches the tail, and serve every read from the tail. Because writes move head-to-tail and the tail is last, any value the tail has is on all three copies, so a tail read is never stale relative to an acknowledged write, and since all reads go to the one tail, two clients cannot disagree. This makes reads linearizable and eliminates both complaints. The cost is write latency and read throughput: a write must traverse the whole chain before it is acknowledged (latency grows with chain length), and all reads funnel through the tail rather than spreading across the nearest copies. If read latency or throughput is critical, the CRAQ variant recovers it — any copy can serve reads by checking with the tail for the current committed version, keeping the consistency guarantee while spreading read load — or, if the workload can tolerate it, a quorum design (R + W > N) is the alternative that trades the fixed head/tail for majority voting on each operation. The non-negotiable change is to stop acknowledging before the write is fully replicated and stop reading from replicas that may be behind; pick one place whose answer certifies full replication and read there.

## External resources

The chain replication paper (van Renesse and Schneider, "Chain Replication for Supporting High Throughput and Availability") and the CRAQ follow-up (Terrace and Freedman) — the protocol, the failure-recovery reconfiguration, and the variant that lets non-tail replicas serve consistent reads.

Comparative treatments of replication schemes (primary-backup, quorum/Dynamo-style R+W>N, and chain replication) in distributed-systems texts and the systems that use them (for example, object stores and coordination services built on chain replication) — the tradeoffs in latency, throughput, and consistency this module contrasts.
