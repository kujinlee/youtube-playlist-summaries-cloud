<!-- codex-review: model=gpt-5.5 -->

**High**

1. `mutate-schema.py:996` silently accepts duplicate anchors.

Quoted code:

```python
if find not in original:
    results.append((label, "INVALID", "anchor not found — mutation never applied"))
    continue
copy_of[target].write_text(original.replace(find, repl, 1))
```

Failure scenario: a future edit makes a mutation anchor occur twice in `0027_stable_blob_addressing.sql`. The harness still mutates only the first occurrence, then may report `RED` for the wrong region or `GREEN` for the intended guard. This contradicts the nearby claim that duplicate anchors fail loudly.

What would prove me wrong: a check equivalent to `original.count(find) == 1` before `replace(..., 1)`, with non-unique anchors classified `INVALID`.

2. `scripts/check-paid-caller-arrival.py:96` can miss a real production caller.

Quoted code:

```python
if SYMBOL not in src:
    continue
...
if SYMBOL not in raw:
    continue
...
(code if SYMBOL in bare else commented).append(entry)
```

Concrete missed caller:

```ts
const fn = 'record_' + 'artifact';
await supabase.rpc(fn, { p_ws, p_video });
```

I executed that fixture through the script’s own `report()` path; it printed `production callers: 0` and returned `0` / `DORMANT`.

It also false-positives on non-caller strings:

```ts
export const help = 'record_artifact is the future paid RPC';
```

That returned `1` / `BACKLOG 26 HAS FIRED`.

What would prove me wrong: parsing production TS/TSX for actual `supabase.rpc(...)` calls, including simple computed constants, or explicitly documenting that only contiguous literal spellings are in scope.

**Low**

3. `scripts/run-schema-assertions.sh:68` lets ordinary callers lower the assertion floor.

Quoted code:

```bash
ASSERTION_FLOOR="${M4_ASSERTION_FLOOR:-119}"
```

and:

```bash
elif [ "$RAN" -lt "$ASSERTION_FLOOR" ]; then
```

Concrete scenario: `M4_ASSERTION_FLOOR=0 ./scripts/run-schema-assertions.sh` exits green and reports:

```text
schema assertions: 119 assertions passed against the live schema (floor 0), rolled back clean
```

So a caller can disable the ratchet in a real run, despite the comment saying the overrides exist only for self-test. It does disclose `floor 0`, so this is Low rather than Medium.

What would prove me wrong: refusing `M4_ASSERTION_FLOOR` outside `--self-test`, or emitting an explicit warning/error when the real corpus floor differs from `119`.

**Checked Non-Findings**

I did not find a destructive internal `m4-base-db.sh` call site. Internal names are pid-derived: `m4_verify_base_$$`, `m4_mutate_base_{pid}`, `m4_gate_mut_$$_*`, `m4_xr_base_{pid}`, etc. The direct CLI still accepts broad prefixes, but I did not find an internal caller that can reach `postgres`, `template0`, or a meaningful non-throwaway name.

`m4-base-db.sh --self-test` passed 10/10 and confirmed the clone carried data: `8384 vs 8384 profiles`.

`run-schema-assertions.sh --self-test` passed 15/15.

`check-paid-caller-arrival.py --self-test` passed 9/9, but its fixtures do not include computed RPC names.

I did not run `mutate-schema.py` or `mutate-live-schema-check.sh` because I could not establish that no other reviewer was using the shared Postgres.

NOT CONVERGED.
