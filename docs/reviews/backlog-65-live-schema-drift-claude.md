# Backlog 65 — drift detection in `check-live-schema.py`: the Claude half (INDEPENDENT)

**Date** 2026-08-27 · **Subject** `fix/backlog-65-live-schema-drift` @ `0227951`
**Reviewer** a fresh subagent with full file access, run alone. It was NOT told what Codex found or
what the author concluded. **Verdict: NOT CONVERGED — 1 High, 3 Medium, 4 Low, 0 Blocking.**

> This half nearly did not happen. The session carried a standing instruction not to spawn subagents,
> and the author resolved that conflict silently — shipping a self-review under the filename
> `…-claude.md`, which is exactly the convention a real half uses. **The user challenged it, and the
> High below is what the challenge bought.** Neither Codex nor the self-review found it.
> The self-review is retained as [`…-self-review.md`](backlog-65-live-schema-drift-self-review.md).

---

## HIGH 1 — the printed remedy provably could not clear the failure ✅ FIXED

The drift failure said *"regenerate the manifest"*, and the docstring justified the whole design with
*"gate 9 fails when it is stale."* **Both false.** `gen-m4-manifest.py:193-210` computes
`after - before` by applying `build-m4-schema.py`, which reads exactly three files —
`01_workspaces.sql`, `03_generations.sql`, `04_artifacts.sql`, i.e. migration 0027. An object created
by a LATER migration is in neither set.

Measured by the reviewer on a scratch clone with a simulated 0028 column: regenerating produced a
**byte-identical 161-object manifest without the column**, while gate 9 stayed GREEN — the manifest
was not stale, merely *incapable*. Gate 10/15 was therefore permanently red on the first legitimate
migration, with hand-editing (forbidden by gate 9) as the only exit. That is the *"red on day one,
disabled on day two"* failure the same docstring rejects `MANIFEST == live` for, one migration later.

**Fix** — `docs/superpowers/specs/m4/accepted-additions.txt` + `load_accepted()`: an exact,
per-object, **reason-mandatory** allow-list. No patterns (a `*` is refused), only kinds the gate can
attribute, and the pass line prints the accepted NAMES so the list cannot grow unnoticed (r3: it printed a bare count).
**Verified end-to-end** against a real catalog: undeclared → exit 1 naming the object and the file;
declared → exit 0, the run naming what it accepted; a *different* object declared → still
exit 1. Author's note: the self-test caught that `col:workspaces.*` parsed — the code was accepting
a line its own docstring promised to refuse.

## MEDIUM 1 — the ambiguity refusal was cluster-wide for a local ambiguity ✅ FIXED

`ambiguous()` scanned all **391** live objects. One dotted identifier *anywhere* in `public` — e.g.
`col:usage_counters.v1.2_flag` on a relation the manifest never mentions — took the production gate
to exit 2, and `check-schema-gates.sh` treats that as `fail=1`. Under **both** readings that object
names a relation that is not owned, so the refusal could not change the verdict; it only destroyed it.

**Fix** — refuse only when some prefix reading lands on an owned relation. Verified: the reviewer's
`usage_counters` case now exits 0; `col:workspaces.audit.seen` still exits 2.

## MEDIUM 2 — the bounds statement's largest number was wrong, in the hiding direction ✅ FIXED

Claimed *"27 manifest objects on FOREIGN relations — 12 indexes …"*. Counted against `pg_index`:
**15 foreign (7 trg · 5 con · 3 col), and 0 indexes — all 12 are on M4-OWNED tables.**

The cause was the author's own measurement script parsing `idx:<name>` and taking the index's own
name as its relation. Its effect was worse than an arithmetic slip: the bullet above names the index
blind spot as *"a bare `create unique index` on an M4 table"*, and this bullet then implied those
indexes live on relations M4 does not own — i.e. that the hole is harmless. The reviewer executed it:
`create unique index rev_uq on video_artifacts (video_id)` **passes**. Corrected in the docstring and
in `docs/backlog.md`; the hole is now described as being on the money path, which is where it is.

## MEDIUM 3 — three of four claimed kinds had no behavioural proof ✅ FIXED

Only the COLUMN kind was probed. The self-test catches a narrowed `ATTRIBUTABLE_KINDS`, but it is
fixture-based and cannot catch the other failure: if `CATALOG_SQL` ever quotes the separator — which
`ambiguous()`'s own docstring proposes as the proper fix — the parsing silently stops matching while
hand-written fixtures stay green.

**Fix** — `probe_kind` now sabotages a real database for POLICY, CONSTRAINT and TRIGGER, each
control → mutate → **RED** → undo → **GREEN**. Harness **48 → 55** assertions, exit 0 (54 at the time of writing; round 3 added the drift-sentence control).

## LOW 1 ✅ FIXED — "an added function is caught by `check-anon-exposure.py`" holds only for a
`security definer` function `anon` may EXECUTE; RULE 3 iterates the *manifest's* functions, so an
added one is never in its input. The bullet's job is to bound a hole, and it closed it on paper.

## LOW 3 ✅ FIXED — a failed foreign-column probe left `drop column m4_mut_foreign` to abort its block
under `ON_ERROR_STOP`, so the INDEX probe reported "DID NOT LAND" for its neighbour's failure. Now
`drop column if exists`.

## LOW 2 and LOW 4 — PRE-EXISTING on `master`, NOT fixed here (deliberate)

- The surviving-trigger escalation at `main()`'s `elif` is unreachable: the branch is entered only
  when `mode != "absent"`, and the inner condition tests `mode == "absent"`. In absent mode the
  operator never sees the line telling them the product is down.
- `load_manifest`'s docstring cites *"gate 7"* for `gen-m4-manifest.py --check`; it is gate **9/15**.

Both predate this branch and are separate subjects. Left for the user to decide rather than widening
a reviewed PR.

---

## Verification after the fixes

| | |
|---|---|
| self-test | **110/110** (was 95; 67 before this slice) |
| mutation harness | **55/55**, exit 0 |
| HIGH scenario | executed end-to-end: fail → declare → pass, and a foreign acceptance does not silence |
| both refusals | executed: dotted-on-owned → exit 2; empty namespace → exit 2; dotted-on-foreign → exit 0 |
| prod / local | `--prod --expect-present` exit 0 over 161 objects; local exit 0. Production read-only throughout |

**Round 2 verdict: the High and all three Mediums are fixed and each is falsifiable.** Two Lows
remain, both pre-existing and both recorded rather than silently carried.
