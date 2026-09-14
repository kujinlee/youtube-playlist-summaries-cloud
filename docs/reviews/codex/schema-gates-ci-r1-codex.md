# Adversarial review — `schema-gates-in-ci`, round 1 (Codex)

**Both halves ran.** The Claude half is `docs/reviews/claude/schema-gates-ci-r1-claude.md` (2 Blocking,
1 High, 5 Medium, 4 Low — all fixed before this run, so Codex reviewed the FIXED tree).

**Dispatched with** `scripts/codex-review.py --prompt-file … --out …/schema-gates-ci-r1-codex.md`;
model `gpt-5.5`; `gate_ran=true`. It built its own database (`m4_codex_review`), ran the full suite,
and removed the container.

**Verdict: 1 High, 1 Medium, 1 Low. All three ACCEPTED and fixed.**

---

<!-- codex-review: model=gpt-5.5 -->

**Findings**

1. **High — `check-storage-independence.py` does not cover two schema gates that can read SQL directly.**  
   The new guard’s population is only Python files under `scripts/`: files invoked as `scripts/*.py` from the suite and top-level `scripts/*.py` importing `m4_catalog`/`m4_base_db` ([scripts/check-storage-independence.py:64](scripts/check-storage-independence.py:64), [scripts/check-storage-independence.py:74](scripts/check-storage-independence.py:74), [scripts/check-storage-independence.py:78](scripts/check-storage-independence.py:78), [scripts/check-storage-independence.py:83](scripts/check-storage-independence.py:83)). But the suite’s first two gates are outside that population: `verify-schema.sh` and `mutate-schema.py` under `docs/superpowers/specs/2026-08-03-stable-blob-addressing/` ([scripts/check-schema-gates.sh:30](scripts/check-schema-gates.sh:30), [scripts/check-schema-gates.sh:33](scripts/check-schema-gates.sh:33)). Gate 1 directly concatenates and executes `05_assert.sql` against Postgres, including the already-applied migration plus assertion SQL ([docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:106](docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:106), [docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:107](docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:107), [docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:130](docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:130), [docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:131](docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh:131)).  
   That leaves the dangerous direction open: a future assertion in `05_assert.sql` can query `storage.objects` or `storage.buckets`, pass against the minimal CI fixture ([scripts/ci/storage-service-fixture.sql:54](scripts/ci/storage-service-fixture.sql:54), [scripts/ci/storage-service-fixture.sql:60](scripts/ci/storage-service-fixture.sql:60)), and the “no gate reads storage” guard still reports green. The guard even states the limitation but bounds it incorrectly: “the shell gates reach Postgres through these same Python modules” ([scripts/check-storage-independence.py:35](scripts/check-storage-independence.py:35), [scripts/check-storage-independence.py:37](scripts/check-storage-independence.py:37)). Gate 1 plainly does not.

2. **Medium — `start-schema-db.sh` still allows `PGCONTAINER` to delete arbitrary non-Supabase containers.**  
   With no positional argument, the script resolves `NAME` from `PGCONTAINER` ([scripts/ci/start-schema-db.sh:49](scripts/ci/start-schema-db.sh:49), [scripts/ci/start-schema-db.sh:50](scripts/ci/start-schema-db.sh:50), [scripts/ci/start-schema-db.sh:52](scripts/ci/start-schema-db.sh:52)). The refusal list blocks only `supabase_*`, `*_supabase*`, `postgres`, and empty ([scripts/ci/start-schema-db.sh:63](scripts/ci/start-schema-db.sh:63), [scripts/ci/start-schema-db.sh:65](scripts/ci/start-schema-db.sh:65)). Anything else reaches `docker rm -f "$NAME"` ([scripts/ci/start-schema-db.sh:90](scripts/ci/start-schema-db.sh:90)).  
   So `PGCONTAINER=redis scripts/ci/start-schema-db.sh`, `PGCONTAINER=m4_prod_client scripts/ci/start-schema-db.sh`, or any leaked non-Supabase container name is destructively removed before a fresh DB is started. The r1 `${1-...}` fix correctly preserves an empty explicit argument, but the remaining env path is still broader than the throwaway naming discipline used elsewhere.

3. **Low — the schema workflow path filter omits the dependency files for gate 15’s required TypeScript parser.**  
   The workflow explicitly says `node_modules` is a gate dependency and that gate 15 fails cannot-run without TypeScript ([.github/workflows/schema-gates.yml:128](.github/workflows/schema-gates.yml:128), [.github/workflows/schema-gates.yml:135](.github/workflows/schema-gates.yml:135), [.github/workflows/schema-gates.yml:136](.github/workflows/schema-gates.yml:136)). The parser imports `typescript` directly ([scripts/ts-comment-spans.mjs:34](scripts/ts-comment-spans.mjs:34)), and `typescript` is declared in `package.json` ([package.json:63](package.json:63)). But the workflow path filters include app/schema/script/spec paths only, not `package.json` or `package-lock.json` ([.github/workflows/schema-gates.yml:62](.github/workflows/schema-gates.yml:62), [.github/workflows/schema-gates.yml:76](.github/workflows/schema-gates.yml:76), [.github/workflows/schema-gates.yml:79](.github/workflows/schema-gates.yml:79), [.github/workflows/schema-gates.yml:93](.github/workflows/schema-gates.yml:93)). A dependency-only PR can therefore change the parser dependency surface without running the schema workflow whose comments say that dependency is load-bearing.

**Notes**

I did not find a current auth-fixture false-green in the existing tree. The seed now creates two users/workspaces and one playlist per workspace, and the live behavioral assertions exercised that corpus.

I also did not find a new issue in the `prod-drift` client seam: `PGCONTAINER: m4_prod_client` is set for the production check ([.github/workflows/schema-gates.yml:209](.github/workflows/schema-gates.yml:209), [.github/workflows/schema-gates.yml:212](.github/workflows/schema-gates.yml:212), [.github/workflows/schema-gates.yml:213](.github/workflows/schema-gates.yml:213)), and cleanup is `if: always()` ([.github/workflows/schema-gates.yml:215](.github/workflows/schema-gates.yml:215), [.github/workflows/schema-gates.yml:217](.github/workflows/schema-gates.yml:217)).

**Verification**

Ran:

```text
scripts/ci/start-schema-db.sh m4_codex_review
PGCONTAINER=m4_codex_review M4_PHASE=post scripts/check-schema-gates.sh
docker rm -f m4_codex_review
```

Result: DB build passed with 27 migrations; full schema suite passed 15/15, including 120 live assertions, 58/58 schema mutations, and 29/29 live-schema mutations. Also ran `check-storage-independence.py --self-test` and ordinary mode: 26/26 cases, guard reports 12 gate files checked.

---

# Coordinator response — all three accepted, and the High was a hole in a guard written an hour earlier

## HIGH — the guard's own STATED BOUND was false, which is this branch's recurring defect

The docstring read: *"a non-Python gate … is real and bounded — the shell gates reach Postgres
through these same Python modules."* Gate 1 plainly does not: `verify-schema.sh` concatenates
`05_assert.sql` (**2,517 lines, 122 assertion sites**) and executes it directly. Measured before
fixing — population **12 files, 0 spec-dir gates, 0 `.sql`**.

Three separate defects had to be fixed to close it, and the middle one is the interesting failure:

1. **The population missed the non-Python gates.** Widened to read them out of the suite.
2. ⭐ **The widened version STILL missed them**, because gates 1 and 2 are invoked as `"$SPEC/…"` and
   my regex matched literal paths only. *That is the same miss as the finding itself, one level
   down* — I looked for the shape I expected instead of the shape the file uses. Fixed by expanding
   the suite's own variable assignments.
3. **Then it over-fired.** With migrations in scope it reported three hits in
   `0007_storage_and_rpcs.sql` — all correct by the letter of the rule and all meaningless, because a
   migration is the SUBJECT the gates read the catalog about, and that file's use of `storage.buckets`
   is *why the fixture exists*. The guard fired on its own premise. Population is now "things that
   read the catalog to reach a VERDICT", never "things the verdict is about".

Population **12 → 21** (12 Python + 6 spec-dir gates + `05_assert.sql` and siblings, 0 migrations).
Comment handling is now per kind — `ast` for Python (exact), `--`/`/* */` for SQL, `#` for shell —
and the two approximations are stated in the docstring, including that they err toward MISSING a
reference rather than inventing one.

**Self-test 26 → 38 cases. Manifest 7 → 11 mutations, 11/11 killing via the case each names.**
⚠ One of the four new mutations went *"RED but NOT via its case"* first: my migration-exclusion case
asserted the absence of a file the fixture never made a CANDIDATE, so it could not fail. The fixture
now names the migration in its suite text. A case that cannot fail is not coverage.

## MEDIUM — a deny-list where an allow-list belonged, and it was live

`PGCONTAINER=redis scripts/ci/start-schema-db.sh` would have run `docker rm -f redis`. The reviewer
found a live unrelated container on this machine to prove the reach. The rule is now an ALLOW-list:
only `m4_[a-z0-9_]*` may be destroyed; anything unrecognised is refused.

**Falsified live:** `PGCONTAINER=redis_ru202 scripts/ci/start-schema-db.sh` → refused, and the
container **survived**. Four cases added, each of which the deny-list version passed.

⚠ Stated bound: this still permits deleting any `m4_*` container, including one another agent is
using. The alternative is a registry of live containers, which this script cannot read.

## LOW — accepted

`package.json` and `package-lock.json` added to both path lists. Gate 15 answers comment detection
with the TypeScript compiler and has no fallback, so its dependency surface is a gate dependency —
this workflow's own comments say so while the filter ignored it.

## On the Claude half

Codex found no error in it and I found none: every one of its twelve was reproducible. Its two
Blocking findings were the two that mattered, and its auth-fixture verification (building the image's
own `auth.uid()` beside the fixture's) is the measurement that settled the branch's largest risk.
