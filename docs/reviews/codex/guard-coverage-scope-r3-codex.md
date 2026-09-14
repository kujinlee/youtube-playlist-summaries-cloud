# Adversarial review — `guard-coverage-scope` (PR #298), round 3 (Codex)

**REVIEW GAP:** claude — not invoked. Round 3 was scoped to ONE commit (`1b4ccec0`, the repair for
round 2's Medium), which no reviewer had seen. The Claude half had reviewed everything before it.

**Verdict: 1 Medium. No Blocking, no High.** ⭐ It found the attack I could NOT: I predicted `or` and
nested parentheses and asked it to try those — it reports both were caught — and it constructed the
one that works, in a place I had not thought to look.

---

<!-- codex-review: model=gpt-5.5 -->

**Findings**
Medium — `JOIN ... ON` predicates can narrow a clause without being reported.  
[scripts/check-guard-coverage.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-guard-coverage.py:424) locates only the first `where`, and [scripts/check-guard-coverage.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-guard-coverage.py:428) splits only the text after it. A realistic catalog edit can move the old `_uq` narrowing into a join before the `where`:

```sql
select 'index:' || indexrelid::regclass::text from pg_index
  join pg_class c on c.oid = indexrelid and c.relname like '%_uq'
 where indrelid = any (array[...]::regclass[]) and indisunique
```

Measured against full `CATALOG_SQL`: `clause_scopes(sql)['index']` stayed unchanged, `clause_predicates(sql)['index']` returned only `['indisunique']`, and `scope_problems(...)` returned `[]`. This matters because joining catalog tables to ask about `pg_class.relname` or `pg_proc` metadata is a natural way to write these clauses, and the trigger clause already has a join. The `or` and nested-parenthesis attacks I tried were caught; `and` inside strings/functions tends to false-positive rather than hide; folded `any(...)` variants I tried fail closed through `clause_scopes`.

**Other Notes**
`EXPECTED_PREDICATES` matches today’s four clauses: check `contype = 'c'`, fk `contype = 'f'` plus public namespace, index `indisunique`, trigger `not t.tgisinternal` at [scripts/check-guard-coverage.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-guard-coverage.py:441). A future legitimate predicate fails closed, which is acceptable; the risk is social, not a current correctness bug.

`_clause_body()` preserves last-clause behavior and missing clauses fail closed via empty body plus `CANNOT RUN`. Literal `union all` can truncate because [scripts/check-guard-coverage.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-guard-coverage.py:370) is a raw substring search, but the likely result is malformed extraction/fail-closed unless paired with the join blind spot above.

The new mutation dies via the named case. Targeted replay parsed by `check-plan-code.parse_fail_names` returned the named `_uq` case and the sibling “OTHER clause” case; full mutate reported attribution clean.

**Verification**
`./scripts/check-guard-coverage.py --self-test` → `34/34 passed`  
`python3 scripts/check-plan-code.py --self-test` → `128/128 passed`  
`python3 scripts/check-plan-code.py --mutate .` → `579 killed, 579 attributed, 0 survivor(s)`  
Docker image `m4_codex_gc_r3:latest` built with committed public build args, then removed.

---

# Coordinator response — accepted and fixed

## MEDIUM — the narrowing moves into the JOIN, and the pin was reading only the WHERE

Exactly right, and measured on the full query: `clause_scopes['index']` unchanged,
`clause_predicates['index']` returning only `['indisunique']`, verdict CLEAN. The `_uq` defect back
in the one place a WHERE-only reader cannot see, using a join — which, as you say, is the natural way
to write these clauses, and the trigger clause already does it.

Conditions now come from EVERY `on` and `where` in the clause body. That has a consequence worth
stating: the trigger clause's own join condition `p.oid = t.tgfoid` is now visible, and it is
**declared in `EXPECTED_PREDICATES` rather than exempted** — because declaring it is precisely what
makes an ADDED join condition visible.

**Measured after the fix:**

    shipped query                      CLEAN
    `join pg_class c on … like '%_uq'` CAUGHT — ['c.oid = indexrelid', "c.relname like '%_uq'"]
    the table array for that edit      UNCHANGED, which is why the array test alone misses it

Three cases (34 → 37) and one mutation (9 → 10): reverting the extractor to the WHERE-only form
turns the join case red, via the case that names it.

## Your other notes, dispositions

* **`EXPECTED_PREDICATES` fails closed on a future legitimate predicate** — agreed, and kept. That is
  the ratchet's whole shape: a new predicate forces a decision instead of sliding in. You called the
  risk social rather than correctness, which is the right reading.
* **Literal `union all` inside a clause could truncate `_clause_body`** — agreed and NOT fixed. It
  fails closed (malformed extraction → the scope test refuses), and no clause contains that text.
  Recorded here rather than guarded, because a guard against a string nobody writes is a rule with no
  falsifier.

## Verified after fixing

    check-guard-coverage.py --self-test      37/37
    guard-coverage mutations                 10/10 attributable, control clean
    M4_PHASE=post scripts/check-schema-gates 73 ✓ / 0 ✗, 15/15, exit 0
    nine repo guards                         rc=0
    EXPECTED_MUTATIONS                       579 -> 580
