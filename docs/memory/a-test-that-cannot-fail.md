---
name: a-test-that-cannot-fail
description: "FIRES-WHEN: about to add a check, gate or checklist item — name what makes it FAIL — ⭐ Ask of any check: what observation would make this FAIL? A checklist item can be an unfalsifiable guard, and REMOVING a signal hollows out the falsifier that watched it (F11 went vacuous three times)"
metadata:
  type: feedback
---

> Merged 2 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `a-checklist-item-can-be-an-unfalsifiable-guard`, `removing-a-signal-hollows-out-its-falsifier`

## a checklist item can be an unfalsifiable guard

**MEASURED 2026-08-11.** `docs/m1.4-finishup-checklist.md` B5 read: *"`npm run check:confinement`
passes against the **real deployed environment**, not just local."*

`scripts/check-service-confinement.ts` has no `process.env`, no `fetch`, no client, no network. It
walks the **source import graph**. Against prod it emits byte-identical output, and it already runs in
CI on every push. **The item could never fail, and never had anything to do with the deployment.**

**Why:** someone works the checklist, runs it, sees `service_role confinement OK`, ticks the box —
and now believes something was verified about **production**. The belief is the damage; a missing
check is visible, a false one is not.

**The transferable part — this is [[dual-review-what-it-catches]]'s "guard that passes in
both worlds", one layer OUT.** This project has excellent instruments for that shape:
`check-guard-coverage.py`, SHAPE/SEQUENCE classification, `mutate-schema.py`, the ratchets. **Every one
of them inspects CODE. None inspects a checklist, a gate description, or an acceptance criterion** —
which is precisely where an unfalsifiable guard hides best, because prose is never mutation-tested and
nobody asks a sentence "what would make you fail?"

**How to apply — ask it of the criterion, not just the assertion:**

> *"What observation would make this item FAIL? Name it concretely. If you cannot, the item is
> decoration."*

Run that over any gate list before trusting it. Cheap, and it found this in one pass. Related smell:
an item phrased as a **question** rather than an assertion — B4 (*"check whether a rendering share
starts returning 503"*) has no pass condition either, and was blocking M1.4.

**Resolved by replacement, not retirement** (PR #70): `npm run check:deployed-bundle` fetches what the
live server serves and asserts no `service_role` JWT / `sb_secret_*` key is in it. It can fail, and was
verified failing before being trusted. Its own design lesson: the `anon` JWT and `sb_publishable_` key
legitimately ship to browsers, so it decodes the payload and judges the **claim**, never the shape —
a scanner that flags *"a JWT"* fires every build, gets muted, and then detects nothing.

**And I put a false measurement in it myself.** Mid-review I claimed "/login references 34 chunks, only
9 are script tags, ~26% scanned" — comparing total **occurrences** to **distinct URLs**. Wrong; it is 9
either way. Caught only by measuring instead of eyeballing. See [[quote-the-code-dont-characterise-it]]
— the same rule applies to numbers, and a plausible false number inside a security check is worse than
no number.

See [[gates-detect-defects-not-design]] — the same blind spot from the other side.

## removing a signal hollows out its falsifier

When a fix removes the signal a falsifier reads, **the falsifier does not go red — it goes
vacuous**, and the suite stays green over nothing.

Measured 2026-09-06 (backlog #97, PR #230), twice in one slice:

1. F11's cases discriminated on the **exit code** (`grow=True → WARN` vs `grow=False → QUIET`).
   The whole point of the fix was to stop warning — so both sides became QUIET and the pair
   asserted nothing. Caught only because I asked what the cases still read. The mutation guarding
   that code (`"the late-flush comparison is inverted"`) named one of those cases as its killer, so
   it would have survived at a green suite.
2. **The re-anchor was itself half-done.** I moved F11 onto *"was a record appended"* and stopped
   there — never reading the record. Codex measured it: `flush_line` rewritten to return a constant
   passed **94/94**. So the same defect class the slice existed to fix (a report that records
   *something happened* while destroying *what was measured*) reappeared inside its own fix.

**How to apply:** before changing a behaviour, ask *"which assertion reads the thing I am about to
remove?"* — then re-anchor it onto something that still varies, and check the new anchor reads
**content**, not merely presence or a count. A count is the cheap re-anchor and it is where this
stops half-way. F11 had already been a tautology in two prior spec versions; each time it had
quietly re-anchored onto something that could not vary, which is the recurring shape.

**Why:** a mutation whose `expect` names a now-vacuous case reports "killed" or survives silently,
and either way nobody re-examines it — the failure is invisible at exactly the moment the code it
guards is being rewritten.

Related: [[assert-the-property-not-the-mechanism]], [[a-report-format-is-a-contract]],
[[a-mutation-loses-its-binding]], [[fixing-a-premise-is-not-covering-the-branch]],
[[the-control-refuted-the-premise]]

