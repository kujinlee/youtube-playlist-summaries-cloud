---
name: position-column-is-not-vestigial
description: "FIRES-WHEN: about to remove videos.position or call a column dead — videos.position is NOT vestigial — it orders every readIndex. Only the claimVideoSlot RETURN field was dead (removed as A6a). Dropping the column is a real slice."
metadata: 
  node_type: memory
  type: project
  originSessionId: 18820d36-e0cd-46c7-945b-e5f3417ebb5f
  modified: 2026-08-04T00:50:53.299Z
---

`videos.position` is **not** dead code, despite an earlier note claiming it was. The claim came from
grepping the identifier and finding no consumers — but the symbol plays two structurally different
roles, and the grep flattened them:

- **the field on `claimVideoSlot`'s return value** — genuinely dead. Removed 2026-08-03 as **A6a**
  (`93631da`). Worth removing rather than commenting: A2's bug was literally
  `playlistIndex = slot.position + 1`, stamping a video's position in the *YouTube playlist* from
  the *other replica's* storage insertion ordinal. Deleting the field makes that unwriteable, and
  the compiler proves it.
- **the column** — load-bearing. `lib/storage/supabase/supabase-metadata-store.ts` orders every
  `readIndex` by it, it is `not null`, and it carries a deferrable unique constraint.

**A6b — dropping the column — is still open and is a real slice, not a cleanup:**
- needs a replacement `ORDER BY`, and the obvious candidate is a trap: `serialNumber` lives in the
  `data` jsonb, so `.order('data->>serialNumber')` sorts as **text** (`"10"` before `"2"`) unless a
  generated column is added;
- would be the **third** `claim_video_slot` signature change (0007 → 0023 → this) and would reshape
  migration 0023's rolling-deploy back-compat wrapper;
- `reorder_videos` (migration 0005) has **zero production callers** — only an integration test;
- likely **dissolved entirely** by the proposed ADR-0006 stable-blob-addressing work, so it may never
  be worth doing.

**Generalisable lesson:** check consumers *per usage site, not per symbol*. The tell here was that
the SQL reference list and the TypeScript reference list never overlapped.

Related: [[serial-coherence-slice-state]].
