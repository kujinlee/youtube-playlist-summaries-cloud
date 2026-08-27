<!-- codex-review: model=gpt-5.5 -->

Blocking

`check-paid-caller-arrival.py` can report DORMANT over a real production caller when the first `record_artifact` on a line is inside a block comment and a later occurrence on that same line is code.

scripts/check-paid-caller-arrival.py:179

FAILING OBSERVATION: `lib/x.ts` contains `/* record_artifact historical note */ await sb.rpc('record_artifact');`; the guard reports `production callers: 0`, `DORMANT`, rc 0.

Verified with:
`python3 - <<'PY' ... mod.report(root, migs, use_live=False) ... PY`

It printed:
`production callers: 0   (comments, not callers: 1)`
`DORMANT — no production caller.`
`RC 0`

High

The migration-ledger anti-rot check still parses comments as schema operations, so a comment can resurrect a symbol after a real drop and let the script report DORMANT for a function that no longer exists.

scripts/check-paid-caller-arrival.py:201

FAILING OBSERVATION: `0028_drop.sql` contains `drop function record_artifact(uuid);` followed by `-- TODO: create function record_artifact again...`; `ledger_net_effect` returns present and the report exits DORMANT.

Verified with:
`python3 - <<'PY' ... (migs/'0028_drop.sql').write_text('drop function record_artifact(uuid);\\n-- TODO: create function record_artifact again if backlog 26 changes\\n') ... PY`

It printed:
`ledger_net_effect: (True, '0028_drop.sql (creates it)')`
`DORMANT — no production caller.`
`RC 0`

Medium

`verify-schema.sh` reports an unreachable Docker/container subject as `schema FAILED` exit 1 on the `M4_DB` path instead of CANNOT RUN exit 2.

docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:128

FAILING OBSERVATION: with `M4_DB=postgres` and a nonexistent `PGCONTAINER`, the script cannot reach Postgres, but prints `❌ schema FAILED` and exits 1.

Verified with:
`PGCONTAINER=definitely_no_such_container_974f6ec M4_DB=postgres docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh >/tmp/verify-no-container-m4db.out 2>&1; rc=$?; printf 'rc=%s\n' "$rc"; tail -20 /tmp/verify-no-container-m4db.out`

It printed:
`rc=1`
`Error response from daemon: No such container: definitely_no_such_container_974f6ec`
`❌ schema FAILED`

Low

`ts-comment-spans.mjs` documents “byte spans” but emits TypeScript UTF-16 code-unit offsets, so its CLI contract is false for any non-BMP character before a comment.

scripts/ts-comment-spans.mjs:2

FAILING OBSERVATION: for `const x = '🖼'; // record_artifact`, the real byte start of `//` is 18, but the tool emits span start 16.

Verified with:
`node --input-type=module - <<'JS' ... commentSpans("const x = '🖼'; // record_artifact\\n", 'x.ts') ... JS`

It printed:
`{"spans":[[16,34]],"documentedByteStart":18,"utf16UnitStart":16}`

NOT CONVERGED
