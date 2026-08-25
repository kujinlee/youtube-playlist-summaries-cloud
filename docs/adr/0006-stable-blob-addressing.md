---
status: accepted 2026-08-24 (M3) — supersedes ADR-0002's REJECTION of video-level shared summaries
  only; 0002's (playlist_id, owner_id) cross-tenant guard stands. Phase 1 is CLOSED: eighteen design
  reviews, and round 17's coordinator asked for no round 18 — "the next genuine test is the migration,
  not round 18" (docs/reviews/spec-blob-addressing-r17-coordinator.md:121-123), Blockings 4 → 3 → 1 → 1.
  ⚠ ACCEPTED IS NOT IMPLEMENTED. The schema has never run: 0 of 26 migrations define
  video_artifacts/video_generations, and prod holds 0 such tables. The next milestone is M4 (promote
  the schema as migrations 0027+) in
  docs/superpowers/plans/2026-08-22-append-only-generations-roadmap.md
---

# Blob addresses are derived from immutable identity, not from display attributes

A blob's address is `<tenantId>/videos/<videoId>/<generationId>/…` — built only from values that never
change — and a per-video **manifest** maps each logical slot (`summary`, `dig:<sectionId>`, …) to the
blob key that is currently authoritative. We decided this because the previous address,
`base = <serial>_<slug>`, is derived from two *mutable* values (a per-replica serial and a
title-derived slug), so any change to either silently orphaned every paid Gemini artifact addressed by
it — a bug class we fixed three separate times without removing its cause.

## Considered options

- **Keep `<serial>_<slug>` and guard every mutation (status quo, rejected).** This is what
  `fix/serial-coherence-sync` does, correctly: plan the relocation, copy with sources retained, verify,
  update metadata, delete best-effort, refuse on ambiguity. It took four adversarial review rounds and
  its correctness rests on a pre-write freshness check that is narrowed, not closed. Rejected because
  it makes *moving a mutable address* safe rather than removing the need to move it — every future
  writer must remember the protocol.

- **Stable address, single copy per slot (rejected).** Address on `videoId` alone, no generation
  dimension. Fixes orphaning from serial/slug changes, but a regeneration still overwrites the previous
  artifact in place, so two concurrent writers can still destroy each other's paid work and there is
  nothing to compensate *from* after a failed interleaving.

- **Stable address + generation dimension + manifest (chosen).** Nothing is ever overwritten, so blobs
  cannot collide at all; the only mutable state is one small manifest row per slot, which makes a
  conditional (compare-and-swap) write trivially sufficient. Locks, lease protocols and drain-waits
  become unnecessary. The cost is garbage collection — see Consequences.

## Consequences

- **This supersedes ADR-0002's rejection of video-level shared summaries.** 0002 rejected that option
  on *cost* — "a fundamental storage re-architecture" — not on correctness. That objection no longer
  holds once the re-architecture is happening anyway. Whether to actually *take* the cross-playlist
  saving is a separate decision: it requires removing `playlist_id` from `jobs_idem_active` and
  re-pointing the 1D spend-reservation FK, and any re-keying must preserve the composite
  `(playlist_id, owner_id)` cross-tenant injection guard that 0002 introduced.

- **Garbage collection becomes necessary — and becomes possible.** Immutable generations accumulate.
  This is *already* the status quo (old `.r<V>` dig blobs and post-relocation old-base blobs pile up
  forever), but today nothing can identify what is unreferenced. The manifest is what makes a
  mark-and-sweep possible, and it needs a grace period so a blob written but not yet published is never
  collected.

- **The address and the human filename become separate concepts.** Cloud keys are opaque and stable;
  local files keep human-readable `003_alpha.md` names for Obsidian, with the manifest as the mapping.
  `serialNumber` and `slug` are demoted to display attributes. This formalizes an asymmetry that
  already exists — `LocalFsBlobStore` ignores `Principal.id` entirely, so the two layouts were never
  really the same.

- **⟳ SUPERSEDED 2026-08-06 — the segment is a `workspaceId`, resolved through a workspace row rather
  than compared to `auth.uid()`.** (Amended again below: in this slice that id *equals* the uid; what
  changed is the predicate, not the value.)
  The earlier text here said *"`tenantId` is named now and equals `auth.uid()`"*. Round-1 review of the
  spec found that contradicts the spec's own §11.2 and would bake in a whole-corpus blob migration:
  once real workspaces arrive, a uid-valued segment forces every object to move — §1's thesis broken
  by the slice implementing it. A uid-valued segment also grants its creator **unrevocable** access,
  since the storage fast path names them directly and an `OR` cannot be revoked.

  **Decided (user, 2026-08-06) — the middle slice.** A `workspaces` table ships now: one per user,
  auto-provisioned in the existing `handle_new_user()` trigger, with `playlists.workspace_id`
  referencing it. The storage predicate becomes a single `security definer` `workspace_readable()`
  check. **No teams, no ACL, no roles** — those stay out of scope, and `workspace_readable` is the one
  place they are later added, so no path ever changes again. Detail: spec §5.0.

  **⟳ CORRECTED 2026-08-06 (round 4, Codex #11) — `id` is NOT an independent UUID in this slice; it
  EQUALS `owner_id`, for migrated and new workspaces alike.** An independent UUID breaks every *new*
  user: `Principal.id` is `auth.uid()` (`lib/storage/resolve.ts:93`) and `objectKey` composes
  `${p.id}/…`, so a new user writes to `<uid>/…` while their workspace has an unrelated id, and
  `workspace_readable` matches nothing — they cannot read their own blobs while the `service_role`
  worker keeps writing them.

  **This does not weaken the decision above, and the distinction is the whole point.** What made a
  uid-valued segment dangerous was never the *value*; it was the **predicate** — the old design let
  storage compare the path segment to `auth.uid()` directly, which grants the creator access that no
  row change can revoke. `workspace_readable` derives access from `workspaces.owner_id`, so it is
  revoked by an `UPDATE`. A workspace id that happens to equal a uid grants nothing on its own. The
  invariant that carries the safety is therefore *"no predicate may compare a path segment to
  `auth.uid()`"* — a claim about a predicate, checkable by one grep at one site — and **not** *"the id
  must never equal a uid"*, a claim about a value that would have forced a whole-corpus migration to
  enforce. **Expiry:** the day multiple workspaces per user ship, `id` can no longer equal `owner_id`,
  and `Principal` must become workspace-aware in that slice.

  **The name buys less than it appears to, and the honest scope matters more than the name.** It makes
  exactly one future transition free — a solo owner's *own* workspace gaining members, where the
  tenant keeps its id. It does **nothing** for the common case, a project joining an *existing* team,
  or for any ownership transfer: those still move every object. The reason is structural — while the
  tenant is a path segment, changing tenant changes every address.

  This is the one place the design knowingly violates its own rule: **ownership is mutable, and it is
  in the address.** Accepted because no ownership-transfer feature exists, so the value is immutable
  in practice.

  **If teams ever ship, do not conclude that every object must be re-keyed.** `storage.objects`
  carries an `owner_id` column, so authorization can move off the path entirely — transfer then
  becomes one `UPDATE` with no bytes moved, and addresses stay immutable. Preconditions and the
  measured evidence (including that `owner_id` is currently populated on only 390 of 973 objects,
  because `service_role` writes leave it NULL) are in §11.2 of the spec.

- **Cross-generation reuse must be validated, not assumed.** A dig belongs to the generation whose
  section spans produced it; attaching it to a different generation's summary requires a span-overlap
  check. Unvalidated mixing would silently mislabel paid content, which is worse than showing none.
