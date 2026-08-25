<!-- codex-review: model=gpt-5.5 -->

**Findings**

**High — `ASSERT_FILE` can make the assertion harness report success over no executable assertions.**

Premise:

[scripts/run-schema-assertions.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/run-schema-assertions.sh:46):
```bash
ASSERTIONS=$(awk '/@RE-RUNNABLE/{p=1;next} /@MIGRATION-ONLY/{p=0;next} p' "$ASSERT")
```

[scripts/run-schema-assertions.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/run-schema-assertions.sh:47):
```bash
if [ -z "$(printf '%s' "$ASSERTIONS" | tr -d '[:space:]')" ]; then
```

[scripts/run-schema-assertions.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/run-schema-assertions.sh:53):
```bash
SQL=$(printf 'begin;\n'
      cat "$SEED"
      printf '%s' "$ASSERTIONS"
      printf '\n\\echo ASSERTIONS_OK\nrollback;\n')
```

Executed against a scratch M4 database with:

```sql
-- @RE-RUNNABLE
-- comment-only block: no SQL assertion
-- @MIGRATION-ONLY
```

Result:
```text
assert_exit=0
schema assertions: RE-RUNNABLE subset passed against the live schema, and rolled back clean
```

That is success over seed-only execution. The seed asserts itself, but the harness claim is that the re-runnable assertion subset passed. It did not run any executable assertion.

The selector is also not SQL-aware. This marked file:

```sql
-- @RE-RUNNABLE
-- selected comment keeps the harness from treating this as empty
select '@MIGRATION-ONLY' as marker_inside_a_string_literal;
select 1/0 as should_have_failed_if_the_block_ran;
```

also returned:

```text
assert_exit=0
schema assertions: RE-RUNNABLE subset passed against the live schema, and rolled back clean
```

The `@MIGRATION-ONLY` string literal stopped selection before the failing assertion.

**High — Task 2’s final grep gate contradicts its own “must keep” predicate.**

The plan says per-playlist correction reads are still valid:

[docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:237):
```text
> ADR-0011 removes `workspace_videos.corrections` and `.corrections_hash`. **It does not remove
> corrections.** They stay in `videos.data`, per-playlist. So assertions reading
> `data->>'corrections'` are still valid and **must be kept**.
```

It then measures those as keepers:

[docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:246):
```bash
# MUST STAY — corrections in videos.data, which ADR-0011 keeps. MEASURED: 11 code lines.
```

But the final gate is a bare repo-schema grep and expects no output:

[docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:271):
```bash
grep -rn "corrections" docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/ \
  | grep -v "corrections_hash_of\|no_corrections_hash\|^.*:-- "
```

[docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md:276):
```text
Expected: **no output**. Anything remaining is a column reference to a column that no longer exists.
```

Executed the plan’s own split today:
```text
must_go=32
must_stay=11
```

So either the 11 valid `videos.data` lines remain and Step 5 fails, or an implementer deletes valid assertions to satisfy Step 5. This is a real plan contradiction, not just wording.

**Low — `build-m4-schema.py`’s comment stripper can blind the end-state predicate.**

Premise:

[scripts/build-m4-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/build-m4-schema.py:76):
```python
Bound: naive. It would also cut a `--` inside a string literal; the spec has none, and an
over-eager cut can only make an assertion stricter, never blind it.
```

[scripts/build-m4-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/build-m4-schema.py:79):
```python
return "\n".join(line.split("--")[0] for line in sql.splitlines())
```

[scripts/build-m4-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/build-m4-schema.py:119):
```python
residual = [ln.strip() for ln in code.splitlines()
            if "corrections_hash" in ln
```

Executed:
```text
strip_comments("select '--' || wv.corrections_hash;") -> "select '"
assert_end_state(... + "select '--' || wv.corrections_hash;") -> []
```

Search did not find this shape in the current schema, so this is residual risk, not a current silent bad build.

**Claims Re-Run**

Reproduced:

```text
bash scripts/mutate-live-schema-check.sh
✅ every mutation caught — check-live-schema.py is load-bearing
```

```text
python3 scripts/check-live-schema.py --self-test
16/16 self-test cases passed
```

```text
python3 scripts/build-m4-schema.py --self-test
14/14 self-test cases passed
```

Rollback proof, scratch database, normalized catalog:

```text
adds=161
70 column
38 constraint
13 function
12 index
5 policy
8 relation
14 trigger
1 type
LEFTOVER=0
DESTROYED=0
skipping-notices=0
```

Migration ordering, temp Supabase workdir plus scratch DB:

```text
Applying migration 9998_probe_create.sql...
Applying migration 9999_probe_drop.sql...
probe_relations=0
```

Config/search:

[supabase/config.toml](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/config.toml:64):
```toml
schema_paths = []
```

Search for `supabase/rollback` found only the rollback file and plan references, not an execution path. `db reset --sql-paths` applies seed paths, and `migration repair` edits migration history; neither showed a rollback-directory replay path in CLI help.

**Still Unexecuted**

I measured 49 fenced blocks / 156 fenced content lines across the reviewed docs, not 148 by my counting. The unexecuted remainder is mostly future task snippets and commit commands in the plan. The risky unexecuted blocks are the Task 2 grep gate at lines 271-274 and the assertion marker examples at lines 734-737; both can fail in the same “prose says measured, selector says otherwise” family, and the first is already contradictory.

Working tree remained clean.

NOT CONVERGED.
