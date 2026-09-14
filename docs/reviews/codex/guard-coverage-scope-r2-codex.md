# Adversarial review — `guard-coverage-scope` (PR #298), round 2 (Codex)

**REVIEW GAP:** claude — not invoked. Round 2 was scoped to ONE commit (`8d0a02c8`, the repairs for
round 1's nine findings), which no reviewer had seen; the round exists because every round on the
previous branch found a defect in the previous round's fixes. The Claude half had just reviewed
everything preceding it, concurrently and on its own database. Re-attempt if wanted.

**Verdict: 1 Medium. No Blocking, no High.** Everything else it attacked came back clean — including
the two things I most wanted contradicted: the nine key classifications match their writers, and it
could not construct a corpus path that invalidates any of the three `MUTATION_EXEMPT` entries.

    python3 scripts/check-plan-code.py --mutate .
      43 file(s), 578 mutation(s), 578 killed, 578 attributed, 0 survivor(s)

---

<!-- codex-review: model=gpt-5.5 -->

Medium, [scripts/check-guard-coverage.py:389](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-guard-coverage.py:389): `clause_scopes()` only extracts the interpolated `array[...]`, so it will miss scope-narrowing predicates that keep the same table array. The exact prior bug class can come back as `where indrelid = any (array{list(OWNED_TABLES)}::regclass[]) and indisunique and indexrelid::regclass::text like '%_uq'`: `scope_problems()` reports clean because the array is unchanged, but future non-`_uq` unique constraints on owned M4 tables become invisible again. That matters because the commit explicitly treats the `_uq` filter as a naming convention acting as a scope rule. Add a self-test/mutation that reintroduces the `_uq` filter or otherwise narrows the index clause without changing the array.

Everything else I attacked came back clean:

- `OWNED_TABLES` matches the five `table:` entries in `docs/superpowers/specs/m4/live-manifest.txt`; `workspaces`, `workspace_videos`, and `video_artifact_sources` are correctly on the owned side.
- The nine key classifications match the writers I checked.
- I could not find a current corpus path that invalidates the three `MUTATION_EXEMPT` entries.
- The list-form `expect` manifests are consumed correctly by `check-plan-code`, and the changed entries attribute through `parse_fail_names`.

Verification run:

- `python3 scripts/check-guard-coverage.py --self-test` → `27/27 passed`
- `python3 scripts/check-plan-code.py --self-test` → `128/128 passed`
- `python3 scripts/check-plan-code.py --mutate .` → `43 file(s), 578 mutation(s), 578 killed, 578 attributed, 0 survivor(s)`
- `PGCONTAINER=m4_codex_gc_r2 M4_PHASE=post scripts/check-schema-gates.sh` → all 15 schema gates green
- Removed `m4_codex_gc_r2` afterward.

---

# Coordinator response — accepted, and the fix produced one more defect of the same family

## MEDIUM — the array is not the whole scope

Correct, and it is the sharpest possible statement of what the `_uq` filter was. `clause_scopes()`
compares which TABLES a clause names, so the prior defect can return without touching them:

    where indrelid = any (array{OWNED}::regclass[]) and indisunique
      and indexrelid::regclass::text like '%_uq'      <- array unchanged, scope narrowed

`clause_predicates()` now pins what each clause may test BESIDES its array, against
`EXPECTED_PREDICATES`. Measured: shipped query CLEAN; re-adding the `_uq` filter with the array
untouched is CAUGHT and names it. Five cases, one mutation (8 → 9), self-test 27 → 34.

⚠ **AND THE FIRST VERSION OF THAT FIX COPIED FOUR LINES.** `clause_predicates` duplicated
`clause_scopes`'s clause locator — which made a mutation anchor ambiguous (the harness refuses a
`find` string matching twice) and, more to the point, created a second implementation of one rule in
the very file arguing that four clauses must not disagree. Extracted to `_clause_body()`: one
locator, two readers. The anchor is unique again and the locator mutation now covers both callers.

⚠ `check-fixture-variation.py` then refused `clause_predicates.sql` — every call passed
`CATALOG_SQL`. The two cases added to satisfy it are the only ones that prove the extractor finds a
narrowing filter in a query it has never seen, which is a better test than the ones I wrote first.

## Verified after fixing

    check-guard-coverage.py --self-test      34/34
    guard-coverage mutations                 9/9 attributable (parse_fail_names, control clean)
    M4_PHASE=post scripts/check-schema-gates 73 ✓ / 0 ✗, 15/15, exit 0
    eight repo guards                        rc=0
    EXPECTED_MUTATIONS                       578 -> 579
