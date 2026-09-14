# Adversarial review — `schema-gates-in-ci`, round 3 (Codex)

**REVIEW GAP:** claude — not invoked. Round 3 was scoped to ONE commit (`fe0785e4`, the repairs for
round 2's Claude half), which no reviewer had seen; the round exists because on this branch every
round's fixes have introduced a defect. The cheap half was the right instrument for a delta that
small, and the Claude half had just reviewed everything before it. Re-attempt if wanted.

**Dispatched with** `scripts/codex-review.py`; model `gpt-5.5`; `gate_ran=true`; 5m22s. It built
`m4_codex_r3`, ran the full suite and the self-tests, and removed the container.

**Verdict: 1 Medium. No Blocking, no High.** The destructive path — the container-name allow-list
that gates `docker rm -f` — came back clean, which was the round's main question.

---

<!-- codex-review: model=gpt-5.5 -->

**Finding**

Medium: [scripts/check-storage-independence.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-storage-independence.py:188) strips any computed `$VAR/` prefix without proving that variable is a repo root. That can make the resolver silently check a real but wrong repo file and miss the file the gate actually reads.

I reproduced this with a temp tree:

```sh
TMP=$(mktemp -d)
cat "$TMP/docs/real.sql"
```

with both `tmp/docs/real.sql` containing `storage.objects` and `docs/real.sql` existing clean. `gate_files()` returned `docs/real.sql` and `scripts/gate.sh`; `problems()` returned `[]`. So a storage read behind a computed non-root variable can be erased into a clean repo-relative path.

The new fixture at [scripts/check-storage-independence.py:491](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-storage-independence.py:491) exercises “unquoted computed assignment requires generic strip,” but it does not prove the stripped variable is root-like. It passes because the fixture’s computed variable is intended to be a root alias by construction.

**Verified**

`start-schema-db.sh --self-test`: 23/23  
`check-storage-independence.py --self-test`: 49/49  
`check-plan-code.py --self-test`: 128/128, `EXPECTED_MUTATIONS` sum 574  
`check-storage-independence` manifest count: 15  
`check-plan-code.parse_fail_names` sees the `[FAIL]` contract and parsed the storage self-test output as no failures.  
`scripts/ci/start-schema-db.sh m4_codex_r3` plus `PGCONTAINER=m4_codex_r3 M4_PHASE=post scripts/check-schema-gates.sh`: green, all 15 gates. `m4_codex_r3` removed afterward.

I did not find an issue in the revised container-name allow-list, and `scripts/ci/seed-corpus.sql` is in scope while only `scripts/ci/storage-service-fixture.sql` is excluded.

---

# Coordinator response — accepted and fixed

## MEDIUM — stripping ANY `$VAR/` assumed every variable is a repo root

It is not. The reviewer built a gate reading `"$TMP/docs/real.sql"` from a `mktemp -d`; the strip
turned it into the repo's own `docs/real.sql`, which exists and is clean, so the guard **checked a
real but wrong file and reported green**. That is worse than a plain miss: it is a confident check of
the wrong subject.

A root-like assignment announces itself — `$(cd … && pwd)`, `dirname "$0"`,
`git rev-parse --show-toplevel`. Only those are stripped now. Anything else keeps its prefix, fails
to resolve, and is simply absent from the population: a MISS, which is the safe direction.

⚠ **The reviewer was also right that my r2 fixture proved less than it claimed.** It used a computed
variable that was *intended* as a root alias, so it could not distinguish "root-like" from "any
variable". The new case uses `SCRATCH=$(mktemp -d)` and asserts the decoy is NOT in scope.

## Coverage — and two more anchor defects of exactly the kind this branch keeps producing

Self-test **49 → 50**; manifest **15 → 16**; `EXPECTED_MUTATIONS` **574 → 575**; **16/16 attributable**
via `check-plan-code.parse_fail_names`, over a control that parses to `[]`.

⚠ **The r3 fix ORPHANED r2's mutation anchor** — the third time on this branch that a refactor moved
the text a mutation binds to. Caught by asserting every anchor resolves exactly once before running.

⚠ **And re-anchoring it introduced a subtler one:** the replacement targeted the FIRST LINE of a
two-line comprehension, leaving a dangling clause — so the mutated suite died of `SyntaxError`,
produced no `[FAIL]` line, and the kill attributed to NOTHING. That is portable practice §22 again, in
the anchor rather than the case. The anchor now covers the whole expression, and the r3 mutation sits
on a distinct substring so the two cannot collide.

## Verified after fixing

    self-test 50/50 · mutations 16/16 attributable · check-plan-code 128/128
    M4_PHASE=post scripts/check-schema-gates.sh   73 ✓ / 0 ✗, 15/15, exit 0
    eight repo guards                             rc=0
