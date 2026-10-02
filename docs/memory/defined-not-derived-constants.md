---
name: defined-not-derived-constants
description: "FIRES-WHEN: deciding whether to define or derive a sentinel or constant — Defining a sentinel instead of deriving it decoupled the blob-addressing spec from backlog #23 — a shape change can't move a constant that was never computed from the shape"
metadata: 
  node_type: memory
  type: project
  originSessionId: 562085d6-32ed-48ac-9814-b2f5e07b1cfe
  modified: 2026-08-07T02:26:15.479Z
---

**2026-08-06, blob-addressing item 2.** `mdHash('')` was the de facto value for "no corrections". It
is **derived** — the hash of the empty *string* — so when backlog #23 turns corrections into
`{from, to}` pairs, the empty value stops being a string and the sentinel has to be re-picked.
That is why item 2 looked blocked on #23.

Replacing it with a **defined** constant (`no_corrections_hash()` returns a pinned literal that today
happens to equal `mdHash('')`) removed the dependency outright: an empty pair list hashes to the same
constant *by definition*. The slice shipped in PR #53 instead of queueing behind a separate feature.

**Generalisable:** when a value looks like it blocks work on a shape change, ask whether it is
*computed from* the shape or merely *equal to* something computed from it. Only the first is a real
dependency. Guard the constant with an assertion that pins its literal value, and comment against the
obvious future "simplification" of re-deriving it.

**The second half of the same slice** is the more familiar lesson: a nullable
`workspace_videos.corrections_hash` conflated "no corrections" with "nobody ever computed this", and
that conflation is *why* 2903 wrong rows stayed invisible while `is not distinct from` returned TRUE
for two NULLs. Backfilling repairs rows once; `NOT NULL` makes the state unrepresentable. Same move
as `art_detached_is_dig` in [[detached-dig-retention-decision]], and the same root shape as
[[test-harness-can-launder-failures]].

**Also learned here:** a "blocked by X" note in a roadmap is worth re-reading before honouring it.
This one was two claims sharing a sentence, and only one held. See [[blob-addressing-spec-state]].
