# ADR 0001 — No locking on playlist-index.json writes

**Date:** 2026-05-28
**Status:** Accepted (single-user local use) — revisit before team deployment

---

## Context

Every write operation in this app (ingestion, archive, deep-dive, personal review) follows the same read-modify-write pattern against `playlist-index.json`:

```
readIndex()  →  modify in memory  →  writeIndex() (atomic rename via .tmp)
```

The `writeIndex` step is atomic at the filesystem level (rename is atomic on POSIX), so a write will never produce a corrupt or partially-written file. However, the **read-modify-write sequence as a whole is not atomic**. If two concurrent requests read the same index, modify different fields, and write back, the second write silently overwrites the first:

```
Request A: reads index  →  sets video 1 personalScore=4  →  writes
Request B: reads index  →  sets video 2 personalScore=5  →  writes
                                                            ↑ A's change is lost
```

**Affected routes:** `POST /ingest`, `POST /videos/[id]/archive`, `POST /videos/[id]/deep-dive`, `POST /videos/[id]/review` — any route that calls `upsertVideo`, `updateVideoFields`, or `writeIndex` directly.

---

## Decision

**No locking is added at this time.**

The app is a single-user local tool. The race window is a few milliseconds, and losing an annotation or archive flag requires two writes to the same playlist index to interleave within that window — practically impossible for one person at one keyboard.

Adding per-`outputFolder` file locking now (e.g. `proper-lockfile`, `fs-ext`) would add a dependency, complicate every write route, and introduce lock-timeout failure modes — overhead that isn't justified for a single user.

---

## Consequences

**What works fine today:**
- Multiple tabs showing *different* playlists — fully safe, no shared index
- Normal single-tab usage — no concurrent writes possible

**What is unsafe today:**
- Same playlist open in multiple tabs, writing simultaneously (e.g. scoring videos in two tabs at once)
- Background ingestion running while user archives/reviews in the UI — the ingestion loop calls `upsertVideo` per video; a concurrent review save could lose the review field or the ingestion result

**Before team/multi-user deployment, the following must be addressed:**

### Option A — Per-`outputFolder` async file lock (recommended for multi-user)
Use a library such as `proper-lockfile` to acquire an exclusive lock on `playlist-index.json` for the duration of each read-modify-write cycle. All routes serialize against the same lock per playlist folder. Low risk, no schema changes, works with the current file-based storage.

### Option B — Optimistic concurrency with index version field
Add a `version: number` field to `PlaylistIndex`. Each write increments it. The client passes the version it read; the server rejects the write with `409 Conflict` if the version has changed. Clients must retry. More complex but scales to multi-process deployments.

### Option C — Replace `playlist-index.json` with SQLite
Move from a flat JSON index to a SQLite database per playlist folder. SQLite handles row-level locking natively and is well-suited to single-file embedded storage. Significant migration effort but the right answer if the app grows into a team tool with a proper backend.

---

## When to revisit

Revisit this ADR when any of the following is true:

- The app will be served to more than one user simultaneously
- Background ingestion jobs will run on a server while users interact via browser
- The same playlist will be accessible from multiple devices
