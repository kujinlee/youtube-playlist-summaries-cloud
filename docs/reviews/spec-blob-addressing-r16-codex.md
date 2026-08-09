<!-- codex-review: model=gpt-5.5 -->

**Findings**

Blocking - `video_generations.in_flight_until` is not implementable as a self-healing finite timestamp while the ADR’s own bound includes unbounded work.
Evidence: `docs/adr/0007-artifacts-are-an-append-only-log.md:423-426` defines collection as `in_flight_until is null or <= now()` and says the marker is written by whoever starts a paid call; `docs/adr/0007-artifacts-are-an-append-only-log.md:440-445` computes `3 * 60_000 + 400 + 800`, then adds “untimed `countTokens` preflight” and “unbounded upload”; `lib/gemini.ts:82-84` has no timeout around `model.countTokens`, and `lib/html-doc/model-store.ts:51` awaits `blobStore.put(...)` with no timeout shown. A finite timestamp self-heals after crash, but cannot be guaranteed to cover an unbounded operation; `infinity` covers the operation but does not self-heal.
Fix: make the covered operation finite before relying on Option C: add bounded/abortable timeouts for `countTokens` and storage upload, define one derived `IN_FLIGHT_TTL_MS`, and add the promised CI check that fails when `MAGAZINE_MAX_PASSES`, `REQUEST_TIMEOUT_MS`, retry delay, or the explicit preflight/upload bounds exceed it.

Medium - The ADR says the Option C invariant is “enforced by a check,” but this branch adds no executable check.
Evidence: `docs/adr/0007-artifacts-are-an-append-only-log.md:435-447` says the invariant is “stated once and enforced by a check” and “a CI check must fail”; `rg -n "in_flight_until" .` finds only ADR prose, and `git diff 00d0c83..HEAD` changes only the ADR plus `scripts/check-sentinel-meanings.py`, with no new schema assertion or CI script.
Fix: either downgrade the prose to “must be enforced in the implementing slice” or add the check now.

**What I Could Not Break**

- Freeze trigger does not block `in_flight_until`: `schema/03_generations.sql:481-486` freezes only `card`, `md_hash`, `doc_version_major`, `produced_at`, `kind`, and `generation_id`.
- Crash behavior is conceptually self-healing if the timestamp is finite: the collectable predicate at `docs/adr/0007-artifacts-are-an-append-only-log.md:425` lapses automatically.
- B3 is now directionally complete: the ADR names `record_artifact`, replace semantics, append-only provenance trigger migration, and the four `05_assert.sql` assertions.
- H3’s `count(*) > 1` restriction removes the single-source money effect and is idempotent under re-run.
- `verify-schema.sh` ran against live Postgres in rollback and passed: `ASSERTIONS_OK`, `ALL_STATEMENTS_OK`, `ROLLBACK`.
- `./scripts/check-sentinel-meanings.py` passed: 22 nullable columns documented, one justified existing conflation.
- Tree remained clean.

**NOT CONVERGED** - blocking reason: Option C’s finite self-healing marker is specified to cover unbounded work, so the lifecycle invariant cannot be satisfied as written.
