---
name: a-framing-widened-to-fit-is-no-longer-a-claim
description: "FIRES-WHEN: about to widen a grouping's wording so a member fits — When a member does not fit a grouping's framing, MOVE THE MEMBER — widening the sentence converts a claim into a bin with a better name"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f872245b-d763-4621-9817-c63a543b2ef5
  modified: 2026-09-11T19:34:52.591Z
---

**A grouping's framing is a CLAIM with a truth value; a tag is a LABEL that cannot be wrong, only
useless.** When a member does not satisfy the framing, the cheap repair is to widen the sentence
until it fits. **Refuse that.** A framing widened to admit a member has stopped being a claim and
become a bin with a nicer name. Move the member instead.

**MEASURED 2026-09-11 (PR #290, squash `e597a8e7`).** I created a group *"Checks that can be wrong
without looking wrong"* with **six** members. Three adversarial rounds cut it to **three**:

| round | removed | why it did not fit |
|---|---|---|
| r1 | `#104` | a gate reporting a failure it cannot RETRACT — the inverse direction |
| r1 | `#94` | a docstring that overclaims while the guard behaves correctly |
| r2 | `#92` | a detector producing a FALSE POSITIVE — also the inverse |

⚠ **I found `#104` myself, then stopped** — having fixed it I concluded the group was sound. The
reviewer found `#94` immediately after. **Instance, not class**, again — see
[[after-fixing-search-for-the-class]].

⚠ **Two mechanical discriminators were RUN over the corpus first and BOTH FAILED**, which is why
neither is the rule (see [[a-filed-finding-s-proposed-fix-is-a-hypothesis]]): *"a group must span ≥2
tags"* blesses the worst offender — the 22-item leftovers bin spans **13** tags, more than any real
group — and *"a group must be under N items"* has no clean line (a legitimate group held 11 against
the bin's 22). **Falsifiability is the only discriminator that survives contact with the data.**

**The policy, filed on `docs/backlog.md` row #90.** CREATE when the framing can be WRONG — if no
member could disprove it, it is a tag. RETIRE on three triggers, two mechanical: the falsifier fires
and nobody defends the claim; fewer than two open members; or the claim became true of everything in
view. ⭐ **CLAUSE 0 — the default is NO GROUP**, because the page emits a card for all rows
regardless of the grouping (measured: deleting a group left its member's card and the count
unchanged), so total coverage is a CHOICE and it is what manufactures both the bin and the
hand-written debt. Related: [[a-test-that-cannot-fail]],
[[gates-detect-defects-not-design]].
