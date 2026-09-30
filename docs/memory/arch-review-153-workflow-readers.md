---
name: arch-review-153-workflow-readers
description: "FIRES-WHEN: citing architecture review #153 or PR #329 — backlog #153 CLOSED by PR #329 (READY, not merged as of 2026-09-21). Verdict: extract _structural() into a shared library. Found a LIVE false green in check-python-pin.py → #154 must land first"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0cfd7079-9c4f-4f89-9a59-337f426f6311
  modified: 2026-09-22T01:00:41.419Z
---

**PR #329**, branch `arch-review-153-workflow-readers`, head `ccff9878`. **READY** —
`check-merge-ready.py --pr 329` says *"READY — every gate CI will run has been run here"*, CI green
(`verify` 7m48s, `schema-gates` 1m32s). **NOT MERGED** — human gate. Docs-only, zero script changes.

Artifact: `docs/reviews/architecture-review-2026-09-21-workflow-readers.md`.

**Armed by a falsifier pre-committed in code** (`check-python-pin.py:126-128`), not by a schedule and
not by the thrashing count — the coordinator had answered the thrashing condition by redesigning and
written down what would prove that wrong. It fired.

## The verdict, so it is not re-derived

**Extract `_structural()` into `scripts/workflow_structure.py`** (underscored = importable library;
`page_markup.py` is the CONTEXT.md precedent, and `coverage_verdict.py` is a *worked* precedent for
the same extraction **including moving its mutations**). **NOT a real parse** — no guard imports a
third-party package, PyYAML is absent, no `requirements.txt`, no `pip install` in either workflow, so
a parser dependency lands **inside the interpreter `check-python-pin.py` exists to pin**. Local
helper imports ARE house style (8 guards, 6 local modules) — that was Codex's "stdlib-only"
correction, and it argues *for* the extraction.

## What the review found that #153 did not know

1. **#153's scope was wrong in both directions.** `check-ci-watched.py` opens no workflow (sentinel +
   `gh`); `check-ratchet-contract.py:835` — unnamed by the row — is the only member that fails OPEN.
2. **R3's fail-open, reproduced:** a YAML comment describing a REMOVED step, block-scalar text, and
   `if: false` all satisfy *"something executes this guard"*, indistinguishably from a real step.
   59% of `ci.yml` is text it reads as executable. **Latent** — 0 of 40 guards depend on it, and not
   vacuously (21 of 40 rest on `ci.yml` alone and survive masking).
3. ⭐ **A LIVE FALSE GREEN IN SHIPPED CODE → backlog #154, which must land BEFORE #155.**
   `_BLOCK_SCALAR` cannot span the space in `- run:`, so the dash-shorthand step leaves its heredoc
   read as structure. **The live path is not the obvious one:** `pin_took_effect` speaks only for the
   job the guard RUNS IN while `declared_pins` speaks for ALL jobs — so job A's genuine pin satisfies
   provenance and job B (no `setup-python`, one heredoc) reads as pinned. `rc 0, "every job pins
   3.12"`. Verbatim the defect #137/#317 exist to end. The suite *looks* like it covers it
   (`:880-882`) and does not — its fixture has no `uses:` line.

## Rows filed, sequenced

**#154** (🟠 the false green, FIRST) · **#155** (the extraction, **SIZE NOT KNOWN**) · **#156** (R3's
`if: false` + its `ci.yml`-only corpus) · **#157** (soundness check for pins/steps) · **#158** (the
flow-mapping bound: read `{k: v}` or refuse).

⚠ **#155's size is unknown because THREE rounds each found another unbudgeted consumer:** the consumer
has no test seam (the mask must live in `main()`, which `--self-test` returns before reaching, so
neither a case nor a mutation can bind — the blob construction needs extracting to a pure function
first); `check-fixture-variation.py` is a third affected guard, and because `analyse()` skips
`_`-prefixed names, **keeping the underscore names pins an EMPTY key set**; and `check-ratchet-contract`
owes its own bookkeeping. **Decided with the user 2026-09-21: size #155 by ATTEMPTING it, not by more
review rounds.** r4 swept for a fourth consumer and found none — the set is `check-plan-code`,
`check-selftest-counts`, `check-ratchet-contract`, `check-fixture-variation`.

**The transfer, by ANCHOR LINE not index** (indices shift): `:232 :244 :245 :249 :254 :260 :263 :264
:278 :295 :298 :349` = 12. `EXPECTED_MUTATIONS` 39 → 27 + a new key = 12, sum preserved — a
**transfer, not a ratchet fall**. ⚠ **The 12 killing CASES move too**, and the declared count 84 falls
(externally pinned in `check-selftest-counts.POPULATION` — bare names there, full paths in
`EXPECTED_MUTATIONS`). ⚠ Re-derive all four after #154 lands; #154 touches one of the twelve.

## Also landed

`CONTEXT.md` gains **structural line** and **soundness check** — three guards built the same primitive
and no round could say so, the same gap that created the Verification Stack section. Its stale "26
scripts" is **removed, not corrected** (a number in prose has no owner, and the file is inside the
corpus it describes). Roadmap section under anchor `review-decides-itself`.

## Two process facts worth keeping

* **`check-review-rounds.py` wants both halves per round; the alternating topology runs one.** The
  resolution is a `REVIEW GAP:` line stating alternation as the reason — precedent
  `plan-m4-promote-schema-r3-claude.md:3`. Needed on r2, r3 AND r4.
* ⚠ **NOT FILED, offered to the user:** `check-docs.py` counts a backlog row's columns and cannot tell
  whether content is in the RIGHT column. An edit anchored on a string beginning with the pipe that
  *closes* a cell silently lands one column early — it happened to #155, 6 cells, gate green.
* The rounds' own lesson is its own memory: [[an-inference-stated-as-measured]].
