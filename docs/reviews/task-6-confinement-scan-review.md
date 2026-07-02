# Task 6 Review — service_role confinement import-graph scan

**Reviewer:** Claude (sonnet), fresh subagent (task reviewer, SDD)
**Commits:** 597672a (impl) + 281a68c (fix) | **Verdict:** SPEC ✅ / QUALITY approved *(after fix)*

## Spec compliance
Transitive import-graph scan over all user-facing entrypoints (`app/**`, `middleware.ts`, `pages/**`); returns `[]` in 1B. Additive-only, no scope creep. Missing `app/`/`pages/` dirs return `[]` (no crash).

## Key security question — PASSED
Reviewer confirmed by tracing + live run that the scan catches a **realistic** `@/lib/supabase/service` side-effect import (not just the artificial absolute-path fixture): `extractImportSpecifiers` pattern #2 captures bare `import '...'`; `resolveImport` maps `@/` → repo root → the real file; `reachesService` returns true. The H3 unit test asserts the `@/` side-effect extraction. **No false sense of safety.**

## Findings
- **Important (FIXED, 281a68c):** `check:confinement` npm script lacked the `TS_NODE_COMPILER_OPTIONS='{"module":"commonjs"}'` prefix that every sibling `ts-node` script uses → bare `npm run check:confinement` failed with an ESM import error, so the advertised CI gate didn't run. Fixed to match sibling scripts. Controller-verified: `npm run check:confinement` → `service_role confinement OK`, 4/4 tests, tsc clean, no leftover fixture.
- **Minor (FIXED, 281a68c):** added a realistic `@/`-style planted-violation test (temp fixture under `app/`, deleted after) so a future refactor dropping the `@/` branch is caught by an integration test, not only the extraction unit test.
- **Minor (accepted):** the `path.isAbsolute(spec)` branch exists only for the fixture mechanism; commented accurately.

## Deviation reviewed
Implementer added `path.isAbsolute(spec)` handling so the tmpdir-fixture (absolute-path) test passes. Accepted — the realistic `@/` path is independently covered.
