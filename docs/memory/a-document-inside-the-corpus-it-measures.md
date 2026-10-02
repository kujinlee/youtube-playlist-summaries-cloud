---
name: a-document-inside-the-corpus-it-measures
description: "FIRES-WHEN: writing counts into a document that belongs to the corpus it counts — A doc that counts a corpus it belongs to invalidates its own numbers the moment it is committed — derive at render time, never write the count down"
metadata: 
  node_type: memory
  type: project
  originSessionId: 66a4d4cf-146a-4aa0-8d45-f3efd21579f7
  modified: 2026-09-12T14:42:14.739Z
---

**If a document counts a population it is a member of, every count it quotes is stale at commit
time.** Not a typo — a structural property.

Measured 2026-09-11/12 while writing the goal/backlog/PR join. The spec said *"20 of the 45
anchor-declaring documents"*. Adding the spec made it 21 of 46. Adding its **plan** made it 22 of 47.
Three commits, three stale numbers, in a document whose own opening rule says every count must be
dated. The code-tag split moved 44/1/**1** → 44/1/**2** for the same reason.

**How to apply:**

1. **Derive the count at render time.** `gen-goals-page.py` computes `excluded_count(total, shown)`
   from the live tree, so the page reads `140 more…` and cannot drift. A number in prose has no
   owner; a number the page computes has one.
2. **Where prose must quote it, date it AND name the mechanism**, and expect to correct it.
3. **In tests of a pure counting function, use SYNTHETIC numbers** — `excluded_count(10, 4)`, not
   `(187, 47)`. Real-looking numbers read as a corpus claim and invite someone to "correct" them.
4. **Refuse the impossible direction.** `excluded_count` raises on `shown > total`, because that can
   only mean the two numbers were counted over different populations — and `-36 excluded` would be
   believed.

Same family as [[a-measurement-is-only-as-good-as-its-corpus]] and
[[measure-the-population-the-code-actually-sees]], but the cause is different: the corpus is not
wrong or mis-sampled, it *moved because you wrote about it*.
