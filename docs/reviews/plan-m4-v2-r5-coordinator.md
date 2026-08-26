# M4 v2 — ROUND 5 coordinator adjudication

**Subject:** PR #153 (`d6688d8`) — the round-4 fixes.
**Halves:** [`plan-m4-v2-r5-codex.md`](plan-m4-v2-r5-codex.md) (2 Blocking, 1 High, 2 Medium) ·
[`plan-m4-v2-r5-claude.md`](plan-m4-v2-r5-claude.md) (3 Blocking, 3 High, 5 Medium, 3 Low).
Both **NOT CONVERGED**. The halves were run independently; the Claude half records that it
deliberately did not read the Codex one.

**Every finding below was re-derived by the coordinator against the code before being acted on.**
Where that re-derivation changed the finding, it is marked ⚠ and the change is stated — that
happened **three times**, and two of them mattered.

---

## ⭐ The three adjudications that changed something

### 1. ⚠ B1's prescribed fix does not fix the case B1 measured

Both halves prescribed the same repair: *"absent mode must compare on `name_of(o)`"*. Both halves
also measured **two** survivor shapes. `name_of` only fixes the first.

| Survivor | Manifest line | `name_of` match? |
|---|---|---|
| body hot-fixed: `fn:record_artifact(uuid)@HOTFIXED` | `fn:record_artifact(uuid)@…` | ✅ caught |
| **signature drifted**: `fn:record_artifact(uuid, text)@…` | `fn:record_artifact(uuid)@…` | ❌ **still invisible** |

A wrong `drop function` signature is *by definition* the case where the live signature differs from
the manifest's — which is why the drop was a no-op in the first place. So the rendered name differs
too, and `name_of` leaves the exact defect both halves demonstrated (a live `SECURITY DEFINER`
`record_artifact` on a database certified M4-free) wide open.

**Fixed by matching on the SYMBOL** — digest *and* argument list dropped (`m4_catalog.symbol_of`),
which is the same normalisation r5 L2 independently needed. Mutation 15 in the harness is that exact
shape and now goes RED.

> **Adopting a review's fix DIRECTION without re-deriving it against the review's own evidence is
> how a round ships a fix that passes its own test and not the defect.** This would have been the
> sixth consecutive instance of the pattern the round is about.

### 2. ⚠ One row of the Claude half's B2 table is vacuous evidence

Row 7 lists `alter view video_artifacts_current set (security_invoker = true)` among the sabotages
that survived at exit 0. **MEASURED: that statement is a no-op.** M4 already ships all three views
with `security_invoker=true`, and `reloptions` is byte-identical before and after:

```
video_artifacts_current|{security_invoker=true}     <- before
alter view … set (security_invoker = true);  exit 0
video_artifacts_current|{security_invoker=true}     <- after
```

A gate "failing to catch" that is reporting on a sabotage that never happened. I hit the same trap
writing the harness — my first mutation 12 copied the direction from the review and reported
MUTATION SURVIVED against an unchanged database.

**B2 itself is unaffected**: rows 1-6 and 8 are real, were reproduced, and the Codex half measured
the RLS and function-metadata sabotages independently. Only this row's evidence is withdrawn.
The dangerous direction is `= false`, and mutation 12 now measures `reloptions` before and after and
declares itself NOT RUN if nothing changed.

### 3. B3 was found by one half only, and is the most structurally serious

The Codex half did not report it. It is confirmable by reading: `gen-m4-manifest.py:88` read its
baseline from the local `postgres` database and refused when that database had M4, while
`check-schema-gates.sh:73` runs gate 7 unconditionally in both phases. In the **post** phase the
local database has `0027` applied *by definition*, so gate 7 exits 2 → `fail=1` → the suite is
**permanently red from the moment the milestone succeeds**. Third unsatisfiable milestone this plan
has shipped, in the gate added to close the second.

⚠ The cause was not the refusal. It was reading `before` from the working database at all, which
also made the diff **asymmetric** — `before` from `postgres`, `after` from a
`pg_dump --no-privileges` clone — so B2's new ACL digests would have produced phantom differences.
One fix, two defects: both readings now come from the same throwaway, rolled back on the throwaway
if it arrives carrying M4.

---

## Dispositions

| # | Half | Finding | Disposition |
|---|---|---|---|
| **B1** | both | `--expect-absent` blind to a drifted survivor | ✅ **FIXED** — matched by symbol, not `name_of` (see 1 above). Mutations 14, 15 |
| **B2** | both | digest covers definitions, not enforcement state | ✅ **FIXED** — 18 enforcement columns digested; mutations 7-12; self-test asserts each column is still read |
| **B3** | claude | `M4_PHASE=post` unsatisfiable | ✅ **FIXED** — throwaway baseline + rollback; **proven** by `gen-m4-manifest.py --self-test` |
| **H1** | claude / codex M | `# sha256:` is self-consistent, not integrity | ✅ **FIXED (as documentation)** — the claim was the defect. It catches truncation; gate 7 + git catch edits, and the docstring now says exactly that |
| **H2** | claude | `check-schema-gates.sh` has no automated caller | 🟡 **PARTIAL, stated** — the hook could not match `supabase/migrations/0027_*.sql`, the file gates 7-8 are *about*; fixed, plus the rollback and the m4 spec SQL. ⚠ **The chain still terminates in a human**, and CI cannot close it: gates 7-8 need Docker + a live stack |
| **H3** | claude | `select 1;` defeats the alphanumeric guard | ✅ **FIXED, and differently than asked** — a fifth syntactic proxy would have been the fifth round of the same move. `--self-test` now BUILDS an M4 database and proves a violated invariant exits 1 and a holding one exits 0 |
| **M1** | claude | absent polarity effectively unmutated | ✅ **FIXED** — mutations 13-15; mutation 2's label corrected (its residue is 140/161, dominated by columns and constraints, not triggers) |
| **M2** | claude | `con:` identity depends on `search_path` | ✅ **FIXED** — `set search_path = pg_catalog`, and schema names taken from the JOIN |
| **M3** | claude | `information_schema.columns` is privilege-filtered (43% of the manifest) | ✅ **FIXED** — columns read from `pg_attribute` |
| **M4** | claude | `read_only_url` duplicated and drifted | ✅ **FIXED** — `check-anon-exposure.py` imports the one implementation |
| **M5** | claude / codex H | `--prod` subject is a label, not a measurement | ✅ **FIXED** — prints measured `current_user@host/db, read_only=…`; the session is `set … read only`, so read-only is a mechanism |
| **M** | codex | plan:963 `--expect-present   # pointed at prod` | ✅ **FIXED** — `--prod` added; "nine checks, numbered 0-8" corrected to eight, 1-8 |
| **M** | codex | manifest integrity over the unique set, not the file | ✅ **SUBSUMED by H1** — ⚠ its duplicate-line sub-claim is **withdrawn**: the Claude half measured that a duplicated line collapses in the set with the header still matching, exit 0, which is correct |
| **L1** | claude / codex H | DB URL in the host process table | ✅ **FIXED** — `docker exec -e PGU` with no value inherits from the caller's environment; argv now shows only the name. Fixed in both callers |
| **L2** | claude | `forbidden()` evaded by an added argument | ✅ **FIXED** — matched on every spelling (`_keys`) |
| **L3** | claude | `col:` digest coarse (`USER-DEFINED`) | ✅ **FIXED** — `format_type` carries the exact type, length and precision. ⚠ The half of L3 about present-mode ignoring EXTRA objects is **not fixed and should not be**: a real database legitimately holds more than M4 |

**Severity split L1/H (codex High vs claude Low):** settled at **Low**. It is pre-existing
(`check-anon-exposure.py` did the same), the URL was measured injection-safe, and psql's failure
message does not leak the password. Fixed anyway — it was one argument.

---

## What was executed

```
python3 scripts/check-live-schema.py --self-test        53/53, exit 0
python3 scripts/gen-m4-manifest.py --self-test           4/4,  exit 0   ← proves the B3 post-phase path
python3 scripts/gen-m4-manifest.py --check              manifest current, 161 objects, exit 0
./scripts/mutate-live-schema-check.sh                   16/16 caught, exit 0
./scripts/run-schema-assertions.sh --self-test           9/9,  exit 0   ← incl. the live RED proof
python3 scripts/check-anon-exposure.py --local          exit 0 (22/22 self-test)
python3 scripts/check-live-schema.py --prod --expect-absent
    live schema [--prod — claude_ro@<prod>/postgres, read_only=on]:
    M4 is ABSENT as expected — checked all 161 objects
M4_PHASE=pre ./scripts/check-schema-gates.sh            exit 1 — gates 3 and 4 only
check-docs · check-anchors · check-review-rounds · check-test-counts
  · check-arch-findings · check-vocabulary-collisions · check-producer-enumeration   all exit 0
```

**Gates 3 and 4 are PRE-EXISTING and unrelated.** Both halves measured them red at `d6688d8` before
any of this work. Re-verified: neither file is modified on this branch, neither imports any changed
module, both last changed in PR #118, and their failures name `video_artifacts_paid_uq` (an unmutated
guard) and stale `reserved_by` sentinel entries.

**⭐ The `--prod` run is the first evidence that `--prod` works.** r4 added the flag and claimed the
gate could now reach production; nothing had ever pointed it there. Production is confirmed pre-M4.

---

## The pattern, and what actually generalises

Five of the nine rows in the Claude half's cascade table are round 4's own fixes. r4's stated lesson
— *"a fix that moves a trust boundary must carry the guarantee across with it"* — is correct and was
applied in exactly one direction each time.

The r5 half offered: *every one of these gates is a predicate over a **projection** of the database,
and the defect is always in what the projection drops.* Names dropped definitions. Definitions drop
enforcement state. `live ∩ manifest` drops the survivor that drifted.

**What this round adds, from adjudicating it rather than reading it:**

> A projection's blind spot is not discoverable from the counter-examples you have already seen.
> Every previous fix here was built by asking *"what did the last counter-example have that my check
> missed?"* — which is a question with an unbounded supply of answers and no stopping rule. The
> assertion selector moved four times that way (`anything` → `non-comment` → `;` → `select 1`), and
> `ENFORCEMENT_COLUMNS` was one sabotage-list away from being the fifth.
>
> The two fixes in this round that are *not* of that shape both replaced a proxy with the property
> itself: the selector now proves a block goes **RED** against a live database instead of inspecting
> its characters, and the manifest generator now **executes** the post-phase path instead of
> refusing it. Both were more work and neither can be defeated by a cleverer counter-example.
>
> So the question that finds the next one is not *"is this check correct?"* but **"what would I have
> to observe for this check to be lying, and can I make the check observe that instead?"**

---

## VERDICT

**NOT CONVERGED at round 5.** All 3 Blocking, 3 High and 5 Medium are addressed, with the three
adjudicated changes above. **Round 6 is required**, and its priority is the fixes in this round —
because that is where five of the last nine defects came from.

⚠ **Phase 6 (architecture review) fired at round 4** and has not run. Five non-converging rounds now.

⛔ Merging stays a human gate. Applying M4-β to production is a second one. `0027` does not exist yet.
