---
status: proposed — supersedes ADR-0002 if accepted
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

- **`tenantId` is named now and equals `auth.uid()`.** No team support is implied or built. The name
  exists so that a future workspace is an RLS predicate change rather than a re-keying of every stored
  object. Real team support would additionally require converting every `owner_id = auth.uid()` policy
  to a membership lookup and deciding who pays under the per-owner cost guardrails.

- **Cross-generation reuse must be validated, not assumed.** A dig belongs to the generation whose
  section spans produced it; attaching it to a different generation's summary requires a span-overlap
  check. Unvalidated mixing would silently mislabel paid content, which is worse than showing none.
