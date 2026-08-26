# M4 — round 4 COORDINATOR adjudication

**Subject:** the round-3 fixes, plus **PR #152 (`903004d`), which had been merged with NO review**
**Halves:** `…-r4-codex.md` (**NOT CONVERGED**, 2B/2H/2M) · `…-r4-claude.md` (**NOT CONVERGED**, 2B/3H/5M/4L)

---

## ⭐ THE FINDING OF THE DAY: I FIXED A COUNTING PROBLEM THAT WAS A PREDICATE PROBLEM

r3 B2 said the gate checked **29 of 161** objects. I read that as *too few names* and widened the
inventory to 161 names. **The claude half showed the count was never the defect.**

MEASURED on a real database with M4 fully applied, then sabotaged three ways — and
`--expect-present` printed *"M4 is PRESENT as expected — checked all 161 objects"*, **exit 0**, every
time:

| Sabotage | What the database can do afterwards |
|---|---|
| `alter table … disable trigger` × 7 (`tgenabled='D'`) | every append-only / freeze / immutability rule is inert |
| `create or replace` two guard bodies with `return new` | same, and the function still "exists" |
| `art_dig_has_span` re-added as `check (true)` | the predicate accepts everything |

**The names were all still there.** `CATALOG_SQL` selected identifiers and never `tgenabled`,
`pg_get_triggerdef`, `prosrc` or `pg_get_constraintdef`.

⚠ **And my own mutation harness was ONE WORD from catching it.** It proved the gate by **dropping**
the guards. `disable` leaves every name intact and walks straight past a name-matching gate.
**When the only way you can express a defect is deletion, you are testing existence, not behaviour.**

**FIXED:** every object now carries `@md5(definition)` — trigger def + `tgenabled`, `prosrc`,
`pg_get_constraintdef`, `pg_get_viewdef`, `indexdef`, policy `cmd/roles/qual/with_check`, column
type/nullability/default. Mutations **5** (disable) and **6** (replaced body) added; **7/7 caught**.
Failures now separate **NEVER CREATED** from **EXISTS BUT DOES NOT MATCH ITS DEFINITION**, because
reporting a disabled trigger as "missing" sends a reader hunting for a migration that ran fine.

---

## The second-order version of the same mistake, found by BOTH halves

**A truncated manifest passed.** `load_manifest` checked only non-empty, and because the verdict is a
SUBSET test, **shrinking the manifest shrinks the claim** — a one-line manifest over a one-object
database printed *"checked all 1 objects"*, exit 0.

That is r3 B2 **a third time**: the trust root moved (hand list → derived file) and the *guarantee*
did not move with it. **FIXED:** the manifest states `# objects:` and `# sha256:` of its own body,
and the loader verifies both — a short or hand-edited file is now CANNOT RUN, not a pass.

---

## Disposition

| # | Finding | Half | Disposition |
|---|---|---|---|
| B1 | gate compares NAMES, not definitions | claude | ✅ **FIXED** — digests; 7/7 mutations; self-test 20→24 |
| B2 | truncated manifest passes | both | ✅ **FIXED** — count + sha256, verified by the loader |
| B3 | gate cannot reach production at all | claude | ✅ **FIXED** — `--prod` over `CLAUDE_RO_DATABASE_URL`, the same mechanism `check-anon-exposure.py` uses |
| B4 | no automated caller — nothing runs it | both | ✅ **FIXED** — `check-schema-gates.sh` is now **8 gates**, adding the manifest ratchet and the live catalog, with `M4_PHASE` required once `0027` exists |
| H1 | `;` defeats the "executable SQL" check | codex | ✅ **FIXED** — requires an alphanumeric character. **Third round for this selector** |
| H2 | `check-schema-gates.sh` is currently RED | codex | ⚠ **TRUE AND PRE-EXISTING — not a regression.** Both failing gates (`check-guard-coverage`, `check-sentinel-meanings`) are red at `61d91c0`, before today's M4 work, and no commit today touched the spec schema they read. **Not fixed here; it is its own slice** |
| M1 | `--check` compares sets, not the file | codex | ✅ **FIXED** — compares the rendered file; it was hiding my own `indexs`/`policys` typo |
| M2 | stale `M4_LIVE_TRIGGERS` / `M4_FUNCTIONS` / `16/16` | both | ✅ **FIXED** — and the self-test count is no longer hardcoded in prose (5→16→20→24 in one day) |

### Both halves independently VERIFIED two things I had flagged as unproven

- **Manifest names are deterministic.** Re-derived twice into distinct scratch databases,
  set-identical to the committed file. My "argued, not measured" caveat about constraint and index
  names is now measured.
- **`version = '0027'` is the string the CLI writes** — checked by applying a real throwaway
  migration and reading the ledger. The r3 B3 rollback fix targets the right row.

---

## ⭐ THE PATTERN, STATED PLAINLY BECAUSE IT IS NOW FOUR-FOR-FOUR

Every fix today was **correct about the instance and silent about the class**:

| The fix | What it left open |
|---|---|
| hand-list → derived manifest | the derived file had no integrity check |
| selector must find non-comment content | `;` is non-comment content |
| end-state predicate gains a table-block check | the extractor matched one closing style |
| inventory widened 29 → 161 names | names were never the predicate |

**A fix that moves a trust boundary must carry the guarantee across with it.** That sentence is the
round's real output; everything above is an instance of it.

---

## Verdict

**NOT CONVERGED.** Seven of eight findings fixed and re-verified; H2 is pre-existing and scoped out
with evidence. Round 5 is due on these fixes — three of today's defects were introduced *by* a
previous round's fix, and this round's fixes are the largest yet.

⛔ **Merging stays a human gate. Applying M4-β to production is a second one.**
