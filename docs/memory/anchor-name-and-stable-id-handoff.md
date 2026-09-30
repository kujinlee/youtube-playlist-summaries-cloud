---
name: anchor-name-and-stable-id-handoff
description: "FIRES-WHEN: resuming stable blob IDs, anchors, or M4 — ⭐ RESUME HERE for stable blob IDs. M4 MERGED 2026-08-27 (PR #155, c517faa) AND M4-β APPLIED TO PROD the same day 14:01 UTC — 0027 IS LIVE ON PRODUCTION, re-measured against the prod catalog 2026-08-27 (do NOT repeat the stale 'prod is still v10/0026' claim; task #157 is discharged). The roadmap EXISTS (2026-08-22-append-only-generations-roadmap.md) — I once failed to find it and re-derived it wrongly"
metadata: 
  node_type: memory
  type: project
  originSessionId: 92595a72-4e72-4cb8-9e2c-8cddc19a2bb3
  modified: 2026-08-28T04:54:59.767Z
---

**2026-08-24. Two things: where the stable-id work actually stands, and the naming decision that came out of failing to find it.**

## The roadmap EXISTS — do not re-derive it

`docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md` (219 lines) is the milestone
spine M1–M7 for stable blob addressing. It has a *measured starting position with the command that
produced each row*, a milestone contract that reconciles the backlog **behind** the plan, and an
explicit exclusions section.

**I could not find it and wasted about an hour re-deriving it — and reached a conclusion the document
had already corrected in itself.** I claimed "17 rounds never converged, so cut scope"; its **M3**
quotes `docs/reviews/spec-blob-addressing-r17-coordinator.md:3` — *"stop reviewing this document and
start task #36 … the next genuine test is the migration, not round 18"*, Blockings 4→3→1→1. My claim
came from stale checkboxes in `roadmap-to-launch.md`. **My "minimal slice / don't ship the log"
proposal is WITHDRAWN** — it was a competing design, not a rescue.

**The anchor for the whole feature is ADR-0006** ("Blob addresses are derived from immutable
identity, not from display attributes"). ✅ **`accepted` 2026-08-24 — M3 DONE (PR #148, `61d91c0`).**
ADR-0007 accepted with it (its status said the two stand or fall together); **ADR-0002 is now PARTLY
superseded** — only its *rejection* of video-level shared summaries falls; its `(playlist_id,
owner_id)` cross-tenant guard STANDS. ADR-0009 (encoder) accepted, shipped in v7.

⚠ **ACCEPTED IS NOT IMPLEMENTED** — 0 of 26 migrations define `video_artifacts`/`video_generations`;
prod holds 0. **NEXT IS M4:** promote the four spec `schema/*.sql` files as migrations **`0027+`**,
inert, no caller. That is the first time this schema executes outside a review's rollback.

**Two lessons M3 measured, both cheap to re-lose:** *(1)* 8 of round 17's 9 findings were ALREADY
applied (`efee284`, `1a7c076`) — verified by reading each `⟳ round 17` marker, not re-applied; the ONE
live residue was in the **design spec §5.1**, where ADR-0007 said it was, not in the ADR everyone
looked at. *(2)* **ADR-0006's front matter was BROADER than its own Consequences section** — "supersedes
ADR-0002" vs "supersedes 0002's *rejection*". Trusting the header would have retired a live
cross-tenant guard. See [[true-about-the-name-silent-about-the-layer]].

**State when handed off:** M2 slice A **shipped today** (prod v8→v10, all 12 tasks). Next per the
plan is **M3**. The plan itself is stale in three measured ways: M2 shown as "specced, next action
writing-plans"; **M4 says migrations `0026+` but `0026` is taken** (`record_correction_spend`) so it
is `0027+`; starting table reads 2,722 tests / Fly v7 / migration 0025 vs today's 2,819 / v10 / 0026.

✅ **PR #144 REWORKED 2026-08-24** (`2b40881` → `45fb2b5`, force-pushed onto master; CI green,
awaiting the human merge). The roadmap section now *points* at the spine and keeps only the three
facts it does not carry; the convergence claim is corrected in place; the spine itself is reconciled
with today (`0026`, 2,819/274, Fly `v10`, M4 → `0027+`, M2 slice A shipped). One extra defect found
in the rework: v1's *"0 files reference `isServableSummaryKey`"* silently depended on
`--exclude-dir=docs` — the symbol is in 22 files, all documentation, including the plan asserting it.

## The naming decision — backlog #64, PR #145 **MERGED 2026-08-24** (`fe1328e`)

User: *"'stable blob addressing' was the good name. Renaming it to 'append-only generations' wasn't a
good move."*

**Two independent causes of the miss, and only one is naming** — fixing only the famous one leaves
the other live:
- my search **truncated**: `ls docs/superpowers/plans/ | head -20` over an **82-file** dir, file at
  position **80**;
- the plan is named for the **mechanism**, the goal is the **anchor**.

The feature spans three vocabularies (`stable-blob-addressing`, `append-only-generations`,
`cloud-blob-key-encoding`) + 96 review files; no single word finds them all. **The ADR number is the
one identifier that survives a rename.**

**⭐ DESIGN SETTLED — [ADR-0010](../../../../code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/adr/0010-documents-declare-their-anchor.md)
`docs/adr/0010-documents-declare-their-anchor.md`, PR #146 (CI green, awaiting merge).** Header is
**`Anchor:` / `ADR:` / `Goal:`** — `Anchor` is the PRIMARY KEY, not the ADR number (not every goal has
an ADR; corrections-in-cloud has none). Index is **generated**, one card per **anchor**, folded into
backlog **#59** (my #64(2) duplicated it). Backfill = the **living set, 22 of 162** specs+plans
(referenced 15 ∪ modified-30d 19); reviews (716) never; the **backlog gets nothing** —
`ROOTS["adr-0006-addressing"]` is already its anchor. Rejected, with reasons, in the ADR: central
relationship doc (**we already run one — `ROOTS`/`DEPENDS` — and its own roadmap lists 2 defects in
it**), free-text tags (uncontrolled vocabulary silently stops matching), ADR-in-filename (a doc serves
two ADRs; 47 links). **DO NOT rename existing files** (user decision).

**Principle worth keeping:** *a central file that holds NAMES is safe; a central file that holds STATE
drifts.* And: **declare upward in the document, derive downward by aggregation.**

✅ **SHIPPED 2026-08-24 (PR #147, `b4223f5`).** `docs/anchors.md` (9 anchors), 22 backfilled headers,
`scripts/check-anchors.py` (6 rules, 15-case self-test, in CI). The `ROOTS` key was renamed
`adr-0006-addressing` → `stable-blob-addressing`, so the backlog graph and the registry are ONE
vocabulary. **R6 is a FLOOR of 22** — R1 only guards new files, so without it the whole backfill
could be deleted with every other rule still green; mutation-tested on the real tree. Backlog #64
CLOSED. ⚠ **The check cannot tell whether a `Goal:` line is TRUE** — 22 hand-written sentences the
index will render as fact.

**ADR-0010's stated acceptance condition is now MET** (`status: proposed — accepted when the header
check ships and passes on the living set`). Flipping it to `accepted` is outstanding and is a human
gate, like ADR-0006's.

**⭐⭐⭐⭐⭐ WHERE M4 STANDS 2026-08-27 12:53 UTC — RESUME HERE. M4 IS MERGED.**

**PR #155 MERGED, squash `c517faa`** (user said "merge it"). `0027` is on `master` —
`supabase/migrations/0027_stable_blob_addressing.sql`, 142,832 bytes, 1,898 lines, 161 catalog
objects. Branch was `docs/m4-round7` @ `7c95059`, 33 commits (`git rev-list --count 74f450b..7c95059`),
CI `verify` green. Five ratchets green on master after the merge: `check-docs`,
`check-roadmap-consistency`, `check-anchors`, `check-review-rounds`, `check-arch-findings`.

✅ **M4-β WAS APPLIED — 2026-08-27 14:01 UTC. THE WINDOW BELOW IS CLOSED; DO NOT RE-OPEN IT.**
**MEASURED 2026-08-27 ~21:5x PDT** over the read-only `CLAUDE_RO_DATABASE_URL` (`claude_ro`): all
five M4 relations are LIVE in production — `workspaces`, `workspace_videos`, `video_generations`,
`video_artifacts`, `video_artifact_sources` — each with `relrowsecurity` **and** `relforcerowsecurity`
true and exactly one owner-read policy. Production and local agree on all 18 `public` tables. So
**`0027` IS applied to prod**; Fly release is v10.

⛔ **(superseded, kept because I nearly believed it again)** This block previously read *"PRODUCTION
IS UNTOUCHED … schema `0026` … M4-β is a SECOND human gate and has NOT been given (task #157)"*. That
was true when written and expired at 14:01 UTC the same day. See [[process-conventions]]: prod
once sat EIGHT DAYS behind a migration while every document read *"merged, done"* — **the inverse error
is equally available, and this file shipped it.** Verify prod by reading prod, in both directions.

**Why it merged with review residue.** Rounds 10+11 found 1 Blocking · 8 High · 8 Medium · 6 Low and
**not one was in `0027`** — every finding was in an INSTRUMENT (gate scripts, assertion harness). Both
halves of both rounds independently confirmed the migration. **Instrument hardening is its own slice**
(user decision 2026-08-27, task #156), including any round 12.

⚠ **Each fix round caused the next round's worst finding** — r10 H2's `set -uo pipefail` → r11 B1
(gate 14 green over the violation it exists to detect); r10 H4's regex scanner → r11 H1 (240 comments
misread). `portable-practices` §12, measured twice in one evening.

**Follow-up PR #156 open** (`docs/m4-merged-tick`): the pre-PR merge tick could only ever say *"OPEN,
NOT MERGED"*, and that expired at the merge. Corrected in both the spine and `roadmap-to-launch.md`,
in place, with the superseded wording named.

⚠ **UNFILED, verified 2026-08-27 (filing is the user's step):** `M1`/`M2`/`M3` mean **two different
things** in two live files — `roadmap-to-launch.md` (Deploy · Sync · Acceptance) vs the spine
(honest card · corrections-in-cloud · discharge-the-design-gate). My own MEMORY.md carries both
readings one line apart. This is a live instance of **backlog #39** (the identifier IS the position),
and sharper than the filed one: the ambiguity is across two files *today*, not across time.

---

The four superseded dated blocks that used to follow here — the 2026-08-26 fork (a) decision and the 2026-08-25 15:05 / 14:10 / 11:0x states — are kept verbatim in [[m4-superseded-trail]]. They are history, not current state; this file holds what is still true.
