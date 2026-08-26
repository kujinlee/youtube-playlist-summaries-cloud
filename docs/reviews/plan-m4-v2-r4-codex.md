<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Blocking — live-catalog gate is still not in the milestone gate chain.**  
The plan says to add it:

`docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:415`
```bash
In `scripts/check-schema-gates.sh`, take the phase from the environment and **refuse to guess**:
```

`docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:430`
```bash
run "7/8  live catalog matches M4_PHASE=${M4_PHASE:-pre}"  python3 ./scripts/check-live-schema.py "$LIVE_FLAG"
```

But the actual gate script still has only six gates and no live-catalog call:

`scripts/check-schema-gates.sh:29`
```bash
run "1/6  schema + assertions (verify-schema.sh)"      "$SPEC/verify-schema.sh"
```

`scripts/check-schema-gates.sh:46`
```bash
run "6/6  documentation integrity"                     python3 scripts/check-docs.py
```

Search run:
```bash
rg -n "check-live-schema|gen-m4-manifest.py --check|run-schema-assertions|mutate-live-schema-check" .github .claude package.json scripts -S
```

Result: `check-live-schema.py` is called by `scripts/run-schema-assertions.sh`, but that script is not called by `scripts/check-schema-gates.sh`, `.github/`, `.claude/hooks/`, or `package.json`. The hook only reminds users to run the old gate:

`.claude/hooks/check-schema-gates.sh:39`
```bash
║      ./scripts/check-schema-gates.sh                                     ║
```

`.claude/settings.json:46`
```json
"command": "bash .claude/hooks/check-schema-gates.sh",
```

Impact: every claim that the promotion gate now verifies the deployed catalog is false for the automated path.

**Blocking — a truncated manifest makes `--expect-present` pass over a partial database.**  
The loader accepts any non-empty set:

`scripts/check-live-schema.py:72`
```python
with open(path) as f:
    objs = {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}
```

`scripts/check-live-schema.py:74`
```python
if not objs:
```

The verdict is subset-only:

`scripts/check-live-schema.py:91`
```python
if mode == "absent":
```

`scripts/check-live-schema.py:93`
```python
return manifest <= live
```

And success reports whatever count the manifest contained:

`scripts/check-live-schema.py:212`
```python
if verdict(live, manifest, mode):
```

`scripts/check-live-schema.py:213`
```python
print(f"live schema: M4 is {mode.upper()} as expected — checked all {len(manifest)} "
```

Executed proof:
```bash
# temp manifest: table:workspaces
# temp db: only public.workspaces
python3 scripts/check-live-schema.py --database m4_round4_truncated_manifest_probe --manifest "$MF" --expect-present
```

Output:
```text
live schema: M4 is PRESENT as expected — checked all 1 objects (1 table)
truncated_manifest_rc=0
```

This is not theoretical staleness. If the trust root is truncated and `gen-m4-manifest.py --check` is not wired, the production gate can bless a database missing 160 of 161 objects.

**High — `ASSERT_FILE` can still report success over zero assertions.**  
The new check treats any non-comment, non-whitespace character as executable SQL:

`scripts/run-schema-assertions.sh:70`
```bash
EXECUTABLE=$(printf '%s\n' "$ASSERTIONS" | grep -v '^[[:space:]]*--' | tr -d '[:space:]')
```

Success is only the marker:

`scripts/run-schema-assertions.sh:86`
```bash
if ! printf '%s' "$OUT" | grep -q ASSERTIONS_OK; then
```

Executed proof against a migrated scratch database with override file:
```sql
-- @RE-RUNNABLE
;
-- @MIGRATION-ONLY
```

Output:
```text
schema assertions: RE-RUNNABLE subset passed against the live schema, and rolled back clean
assert_semicolon_rc=0
```

A semicolon parses and asserts nothing. The harness still has a success-over-nothing path.

**High — the one automated schema command currently fails.**  
Executed:
```bash
./scripts/check-schema-gates.sh; printf 'schema_gates=%s\n' "$?"
```

Output ended with:
```text
10 problem(s) — guard coverage NOT met
❌ FAILED: ./scripts/check-guard-coverage.py
...
5 problem(s) — sentinel meanings NOT met
❌ FAILED: ./scripts/check-sentinel-meanings.py
...
❌ at least one schema gate failed — the work is NOT done
schema_gates=1
```

So even before wiring the new live gate, the advertised “one command” is red.

**Medium — the manifest ratchet ignores stale header/prose.**  
`gen-m4-manifest.py --check` passed:

```text
manifest is current — 161 objects (5 tables · 3 views · 70 columns · 14 triggers · 13 functions · 1 type · 12 indexes · 5 policies · 38 constraints)
gen_check=0
```

But the committed manifest still says:

`docs/superpowers/specs/m4/live-manifest.txt:14`
```text
# 5 tables · 3 views · 70 columns · 14 triggers · 13 functions · 1 type · 12 indexs · 5 policys · 38 constraints
```

Cause: `--check` compares object sets, not rendered file contents:

`scripts/gen-m4-manifest.py:154`
```python
if committed != manifest:
```

This is low mechanical damage, but it proves `--check` is not actually a full file staleness detector.

**Medium — stale plan references survived PR #152.**  
PR #152 deleted the hand-written symbols, but the plan still cites them:

`docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:646`
```text
survive, and must be named. Those seven are `M4_LIVE_TRIGGERS` in `check-live-schema.py`.
```

`docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:705`
```text
`check-live-schema.py --expect-absent` reports any surviving function by name (Task 3's
```

`docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:706`
```text
`M4_FUNCTIONS`). If a signature is wrong, that gate goes red — which is exactly why the gate had to
```

Also stale expected self-test count:

`docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:400`
```text
Expected: `self=0` with `16/16`, `mut=0` with `✅ every mutation caught`. ⚠ A tick records *that*
```

Actual:
```text
20/20 self-test cases passed
```

**Verified Non-Findings**

Rollback ledger string is correct for the CLI. I applied a throwaway migration named exactly `0027_stable_blob_addressing.sql` in a temp Supabase project against a throwaway database.

Output:
```text
Applying migration 0027_stable_blob_addressing.sql...
tmp_ledger_rows=0027,
```

So this rollback line is correct:

`supabase/rollback/rollback_0027_stable_blob_addressing.sql:114`
```sql
delete from supabase_migrations.schema_migrations where version = '0027';
```

Parser probes did not break the new `strip_comments` / `table_body` cases I ran. Executed cases: nested parens in check, dollar-quoted function body before the table, string containing `--` and escaped quote, `''` at end of line, and `create table` inside a comment. `build-m4-schema.py --self-test` also passed `22/22`.

**Executed**

```bash
python3 scripts/build-m4-schema.py --self-test
python3 scripts/check-live-schema.py --self-test
python3 scripts/gen-m4-manifest.py --check
./scripts/mutate-live-schema-check.sh
./scripts/run-schema-assertions.sh
./scripts/check-schema-gates.sh
rg -n "check-live-schema|gen-m4-manifest.py --check|run-schema-assertions|mutate-live-schema-check" .github .claude package.json scripts -S
```

Working tree remained clean. Scratch databases were dropped.

NOT CONVERGED
