---
name: discover-the-target-and-read-it-back-uncached
description: "FIRES-WHEN: about to write to or repair a remote or production resource — Two near-misses repairing one prod blob: .env.local points at LOCAL Supabase so the first attempt aimed at the wrong project (refused only because the path was DISCOVERED, not rebuilt), and the write's read-back was answered by a stale CDN copy"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 92595a72-4e72-4cb8-9e2c-8cddc19a2bb3
  modified: 2026-08-24T23:10:44.493Z
---

**MEASURED 2026-08-24**, hand-repairing one corrupted `▶` URL in a production summary (the
correction path could not: PR #139's guard refuses `▶` changes in both directions).

## 1 — `.env.local` points at the LOCAL stack. The prod write credential is not on this machine.

`NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321`, so `SUPABASE_SERVICE_ROLE_KEY` there is the
**local** key. The first repair attempt therefore aimed at the wrong database entirely — and I only
noticed because the object wasn't found. (`CLAUDE_RO_DATABASE_URL` in the same file *is* prod. One
file, two different targets — check which before every credentialed action.)

**It wrote nothing, and that was the design, not luck.** The script *discovered* the object by
listing and refused on `found 0`. The layout `${owner}/${playlist_key}/${file}` is one I could write
from memory — and it is **correct** — so a version that rebuilt the path would have created a stray
object in the wrong project and reported success. **ADR-0009's "the seam owns the mapping" earned its
keep outside the code it was written for.** Never reconstruct a physical key; discover it and refuse
unless exactly one match. Same family as [[a-positional-read-needs-a-verified-shape]].

**Where the prod credential does live: inside the Fly machine.** Run the repair there
(`flyctl ssh console -C ...`, payload base64'd to dodge the quoting footgun) rather than copying a
write key to a laptop. Node 22 + global `fetch` + the Storage REST API needs no `node_modules`.

## 2 — A read-back a CACHE can answer is not a read-back.

The script wrote, immediately re-read, got different bytes, and printed
`REFUSED: READ-BACK MISMATCH`. **The write had actually succeeded** — the re-read was served a stale
CDN copy (`cf-cache-status: HIT`; a cache-busted re-read returned the repaired `sha256`).

Both halves matter. Refusing was **right**: it reported ambiguity rather than success, which is the
posture this repo demands. But the check itself was weak in a way that reads as a scary failure —
verify through a path the cache cannot answer, and better still through the **application** (the
real proof was downloading via the app and diffing against the pre-correction document, not reading
storage). Compare [[a-mechanism-can-be-silently-overridden]]: ask what a layer *between* you and the
subject could be answering instead.

**Also do this:** pin the expected pre-write `sha256` from bytes you measured earlier, and refuse if
prod disagrees — that is what proves the target has not moved since you decided what to write.
