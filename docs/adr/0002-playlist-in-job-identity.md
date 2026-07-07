---
status: accepted
---

# Playlist is part of a job's identity (per-playlist summaries, not shared)

A cloud **Job**'s work target includes the **playlist**: a summary job is identified by `(owner, playlist, video, section, kind, version)`, not by the video alone. We decided this because the storage model is already per-playlist — the `videos` primary key is `(playlist_id, video_id)` and every artifact is addressed `owner/playlist/…` (matching the local per-output-folder model) — so a video that legitimately belongs to two playlists must produce **two** summary artifacts, one per playlist. The original 1E-a idempotency tuple omitted the playlist, so the second enqueue for the same video under a different playlist would collide on the `jobs_idem_active` index and be **joined** into the first job, leaving the second playlist permanently without its summary. This was invisible in 1E-a (the echo stub wrote nothing) and became load-bearing in 1E-b when the real handler began writing artifacts.

## Considered options

- **Video-level shared summary (rejected).** Generate a video's summary once and reference it from every playlist that contains it — cheaper (no duplicate Gemini spend). Rejected because it contradicts the just-merged 1C storage model: it would require shared blobs across index keys, a video→playlists membership table, and cross-index reference reads — a fundamental storage re-architecture, and a divergence from how the local tool behaves.
- **Per-playlist copies with playlist in the identity (chosen).** Each playlist keeps its own copy of a video's summary, consistent with local and 1C. Add `playlist_id` to the `jobs` table, the `jobs_idem_active` index, `enqueue_job`'s conflict target, `claim`/`LeasedJob`, and `JobKey`. Cost: the same video in two playlists is summarized (and, under 1D, charged) twice — accepted as consistent with existing local behavior.

## Consequences

- The `jobs → playlists` foreign key must be **composite** `(playlist_id, owner_id) references playlists(id, owner_id)` — matching the `videos` guard and backed by `playlists.unique(id, owner_id)` — not single-column `references playlists(id)`. A single-column FK would let a caller enqueue a job carrying their own `owner_id` but another owner's `playlist_id` (RLS only checks `owner_id = auth.uid()`), and the service-role worker would then write into the victim's tenant. The dual adversarial review of the 1E-b spec caught this; the composite FK closes it.
- This re-keys the idempotency index and changes the `enqueue_job` signature — done as a `0009` migration while the `jobs` table is still empty in every environment (1E-a undeployed), so no data migration is required.
- 1D's quota/spend reservation FK anchors to this identity, so the playlist coordinate must be settled before 1D. Revisiting this later (moving to a shared video-level summary) would mean migrating the `jobs` table, re-pointing 1D's reservation, and re-architecting 1C storage — meaningful and cross-cutting.
- The write location is now derived from identity (`playlistId`), never from the job payload, which closes a latent bug where a divergent payload on a joined job could misdirect an artifact.
