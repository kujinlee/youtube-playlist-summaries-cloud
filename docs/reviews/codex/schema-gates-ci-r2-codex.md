# Adversarial review — `schema-gates-in-ci`, round 2 (Codex)

**Scope: the DELTA since round 1**, not the branch — because on the previous branch both late defects
were introduced by fixes, so the repairs are what needs reviewing.

**Dispatched with** `scripts/codex-review.py --prompt-file … --out …/schema-gates-ci-r2-codex.md`;
model `gpt-5.5`; `gate_ran=true`. It built its own database (`m4_codex_r2`), ran the full suite and
`--mutate .`, and removed the container. ⚠ It took **10m27s** against r1's 1m31s and sat at 0% CPU with
no output file for most of it — I read that as this repo's documented hang signature and dispatched
the Claude half as a fallback. It was not hung; it was slow. The fallback was still correct under the
rule, and the cost was one extra review rather than a missed one.

**Verdict: 1 High, 1 Medium. Both ACCEPTED and fixed.**

---

<!-- codex-review: model=gpt-5.5 -->

**Findings**

High — [scripts/check-storage-independence.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-storage-independence.py:126) only pulls sibling `*.sql` and `schema/*.sql` for non-Python gates, but [scripts/run-schema-assertions.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/run-schema-assertions.sh:46) defines `SEED="$REPO/docs/superpowers/specs/m4/seed-assertion-corpus.sql"` and [scripts/run-schema-assertions.sh](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/run-schema-assertions.sh:317) concatenates `cat "$SEED"` into the SQL sent to `psql`. That seed is verdict-affecting: it builds the corpus and asserts itself before the live assertion gate can pass. A future `select count(*) from storage.objects` or any fixture-dependent storage check in that seed would reach Postgres while `check-storage-independence.py` still reports clean. I enumerated `gate_files()` on the real tree: 21 files, and `docs/superpowers/specs/m4/seed-assertion-corpus.sql` is not one of them.

Medium — [scripts/check-storage-independence.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-storage-independence.py:70) recognizes only unquoted `storage.<name>`, and both non-Python scanners ultimately rely on that regex via [scripts/check-storage-independence.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-storage-independence.py:167). Real storage reads it misses:
`select 1 from "storage"."objects";`
and, in shell, `psql -c 'select 1 from "storage"."objects";'`.
Those are valid Postgres reads of the storage schema, and they matter for this guard’s claim: either can make the CI storage fixture load-bearing while the guard stays green. I also confirmed the same miss occurs inside Python SQL strings through `storage_refs()`.

**Checks Run**

`python3 scripts/check-storage-independence.py --self-test` → 38/38 passed.

`python3 scripts/check-plan-code.py --self-test` → 128/128 passed.

`check-plan-code.parse_fail_names` sees canonical `[FAIL] <case>` lines and ignores the old checkmark shape; the delivered mutation run also verified the real path:
`python3 scripts/check-plan-code.py --mutate .` → 43 files, 570 mutations, 570 killed, 570 attributed, 0 survivors.

`scripts/ci/start-schema-db.sh --self-test` → 14/14 passed. I did not find a destructive allowed name beyond the stated `m4_*` blast radius, nor a legitimate workflow name now refused.

`scripts/ci/start-schema-db.sh m4_codex_r2` → ready, 27 migrations applied, M4 present.

`PGCONTAINER=m4_codex_r2 M4_PHASE=post scripts/check-schema-gates.sh` → all schema gates green. `m4_codex_r2` was removed afterward and is no longer present.

---

# Coordinator response — both accepted; the guard's population grew twice more

Both findings are the same root cause as r1's High and as each other: **my rule was narrower than the
thing it reads.** Three rounds, three widenings of the same guard.

## HIGH — a gate's OWN variables name more subjects

`run-schema-assertions.sh:47` sets `SEED="$REPO/docs/superpowers/specs/m4/seed-assertion-corpus.sql"`
and `:318` does `cat "$SEED"` into the SQL it sends to psql. Verdict-affecting, and outside the
population — because r1's fix expanded only the SUITE's variables, one level deep. Reproduced before
fixing: `seed in population? False`.

Resolution is now TRANSITIVE: every admitted `.sh`/`.py` is itself read for variable assignments and
path tokens, to a fixpoint. Population **21 → 31**.

⚠ **Then it over-fired again, exactly as it did in r1.** With transitive resolution the population
swallowed `scripts/ci/storage-service-fixture.sql` — which reads `storage.buckets` because *creating
those tables is its entire job*. The guard flagged the very file whose safety it exists to certify.
Fixed by naming the class rather than patching the instance: `NOT_A_GATE = ("supabase/", "scripts/ci/")`
behind a single `_is_subject()` predicate with three call sites, so the next exclusion is one tuple
entry and not a fourth copy of a prefix test. Population settles at **27**.

## MEDIUM — quoted identifiers are real Postgres and were invisible

`select 1 from "storage"."objects"` and the shell form both escaped a rule that matched only the bare
identifier. Quoting is not exotic — it is what a generator emits. `STORAGE_REF` now accepts optional
double quotes on either side; `mystorage.x` still does not match, and `"auth"."users"` still does not.

## Coverage, and two process defects found while adding it

**Self-test 38 → 46. Manifest 11 → 13. 13/13 attributable, verified with
`check-plan-code.parse_fail_names` itself.** `EXPECTED_MUTATIONS` 570 → 572.

⚠ **The `_is_subject` refactor ORPHANED a mutation anchor** — anchors bind by TEXT, and
`startswith("supabase/")` no longer existed. Caught by asserting every anchor resolves exactly once
BEFORE running, which is now part of the check rather than something noticed afterwards. Both
exclusion mutations were re-anchored to distinct lines so neither can mask the other.

⚠ **And one new mutation SURVIVED because my fixture was wrong, not because the rule was.** The
transitive-step mutation passed while the case that names it stayed green: the fixture put the
seed file BESIDE its gate, where the sibling glob finds it anyway. Real life puts
`run-schema-assertions.sh` in `scripts/` and its seed under `docs/superpowers/specs/m4/`. The fixture
now mirrors that, and the mutation dies via its case.

## Verified after fixing

    ./scripts/check-storage-independence.py --self-test      46/46
    13/13 mutations attributable (harness's own parser)      control parses to []
    M4_PHASE=post scripts/check-schema-gates.sh              73 ✓ / 0 ✗, 15/15, exit 0
    check-docs, check-selftest-counts, check-fixture-variation,
    check-ratchet-contract, check-storage-independence, check-anchors   all rc=0
