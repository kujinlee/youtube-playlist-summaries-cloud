# Stable blob addressing — round 1, coordinator's own pass

**Artifact:** `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md` @ `2d59fe8`
**Date:** 2026-08-06
**Status:** independent of the Codex and Claude reviews running in parallel; written before either
reported, so agreement is evidence and disagreement is a signal to adjudicate by reading code
(`dev-process.md` → *Reviewer disagreement is the signal*).

All three findings share one root: **§11.0's workspace-level dedup was decided after §5's manifest
and §5.2's card split, and nothing reconciled the three key shapes.**

---

## BLOCKING

### B1 — A shared video is TWO rows, so it has two cards for one body

**Defect.** §5.2.1 places the video judgments (`ratings`, `overallScore`, `videoType`, `audience`,
`language`, `tags`) "on the video", and the human fields (`corrections`, `personalNote`,
`personalScore`) already live there. But **`videos` has primary key `(playlist_id, video_id)`**
(`0001:30`) — a video in two playlists is two rows. §11.0 then makes both playlists share **one**
manifest row and therefore **one** blob.

**Failure scenario.** Playlists P1 and P2 in workspace W both contain video V.
1. User opens V under P1 and adds a correction: *"Clawcode" → "Claude Code"*.
2. §5.2.2 requires the correction to be applied before the generation publishes, so the shared body
   changes for **both** playlists.
3. P2's row still has `corrections = NULL` and `mdCorrectionsHash` describing the uncorrected text.

P2 now asserts an uncorrected body while serving a corrected one. Symmetrically, `ratings` may differ
between P1 and P2 for the same bytes, and a reader cannot tell which row describes what it is reading.

**This is root-cause shape #4 — a row claiming something the blob does not satisfy — reappearing at a
level §5.2 did not cover.** §5.2 bound the *card* to the generation and explicitly moved the video
judgments *off* it; that is correct when there is one video row and becomes wrong the moment two rows
share a body.

**Evidence:** `supabase/migrations/0001_core_schema.sql:30`; spec §5 manifest key; §5.2.1; §11.0.

**Change.** Either (a) scope shared artifacts' scalars to the workspace too — which requires the entity
in B2 — or (b) restrict dedup to blobs whose scalars are provably identical, or (c) state explicitly
that dedup applies only to the *body* and that per-playlist scalars are intentionally independent,
with a rule for which row a reader trusts. Not choosing is the one unacceptable option.

---

### B2 — The manifest key names an entity that does not exist

**Defect.** `video_artifacts` is keyed `(workspace_id, video_id, slot)` and `video_generations` is
keyed `(workspace_id, video_id, generation_id)`. **No table in the schema represents "video V in
workspace W."** Every existing table is per-playlist (`videos`), per-owner (`usage_counters`,
`serve_owner_budget`, `quota_allowance`) or global (`spend_ledger`, `guardrail_config`) — verified by
listing every `create table` across all 21 migrations.

**Consequence.** The manifest **cannot** carry a foreign key to `videos`: an FK needs a unique
`(workspace_id, video_id)` on the referenced side, and `videos` is unique on `(playlist_id, video_id)`.
So referential integrity between the manifest and the rows it describes is **application-maintained by
construction** — the class of invariant that drifts, and the one this whole spec exists to stop relying
on.

**Evidence:** every `create table` in `supabase/migrations/`; spec §5 and §5.2 schemas.

**Change.** Introduce the missing entity — a workspace-scoped video record that the manifest and
generations reference and that `videos` (per-playlist membership) points at. This also gives B1 a
home for shared scalars.

---

### B3 — GC roots from the manifest, and nothing prunes the manifest on delete

**Defect.** §8 defines GC as *"mark and sweep over `video_artifacts`; anything not referenced is a
candidate."* The manifest is therefore the **root set**. But §8 specifies no rule that removes manifest
rows, and B2 shows no FK can cascade them.

**Failure scenario.** A user hard-deletes playlist P1 (its only playlist containing V).
1. `playlists → videos` cascades (`0001:32`), so the `videos` row for V disappears.
2. `video_artifacts (W, V, 'summary')` survives — nothing deletes it and nothing can cascade it.
3. GC marks V's blobs as **referenced**, forever.

The blobs are retained indefinitely for content the user explicitly deleted. **This inverts both
decisions made today:** the 90-day ceiling in §8 becomes unbounded, and *"an explicit delete outranks
retention"* fails in its worst form — the delete returns 200 while the content is kept.

Compounding it, the delete path already treats blob cleanup as best-effort and returns 200 on failure
(`app/api/playlists/[id]/route.ts:79-82`, *"invisible orphan accepted"*), so **nothing reports this**.
That is root-cause shape #5 layered on shape #4.

**Evidence:** spec §8; `0001:32`; `app/api/playlists/[id]/route.ts:73-83`.

**Change.** Deletion must remove manifest rows in the same transaction as the row delete, and the
sweeper needs a second root — objects with **no** manifest row at all — so an orphaned blob is
collectable rather than invisible. §11.0's reference counting is necessary but not sufficient: it
answers *"may I delete this blob?"* and not *"who deletes the manifest row?"*

---

## Notes for adjudication

- B1 and B3 both follow from B2. If the missing workspace-scoped video entity is added, B1 gains a
  home for shared scalars and B3 gains a cascade path. Fix B2 first and re-derive the other two rather
  than patching them independently.
- These are **design-level** findings against an unimplemented spec, so "failure scenario" means a
  state the design permits, not an observed incident.
- What I checked and believe is sound: §3's re-verified ground truth (16 facts, re-checked 2026-08-05);
  §6.1's both-directions rule, which correctly covers the split case §6 never named; and §11.2's
  membership-not-identity conclusion, which I tried and failed to break — every identity fallback I
  could construct reproduced the unrevocable-grant defect it names.
