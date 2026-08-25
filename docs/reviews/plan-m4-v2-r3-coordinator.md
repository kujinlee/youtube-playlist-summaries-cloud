# M4 plan v2 — round 3 COORDINATOR adjudication

**Subject:** `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md` + six extracted artifacts @ `2649094`
**Halves:** `…-r3-codex.md` (**NOT CONVERGED**, 2H/1L) · `…-r3-claude.md` (**NOT CONVERGED**, 3B/3H/4M/3L)

**Anchor:** stable-blob-addressing · **ADR:** 0006, 0007, 0011

---

## ⭐ THE DEFECT CLASS SHIFTED, AND THAT IS THE HEADLINE

| Round | The finding, in one line |
|---|---|
| r2 | **The code has never run.** All 8 Blockings sat in fenced blocks in a Markdown file |
| r3 | **The code runs. The claims about what it covers are wider than the code.** |

Round 2's shape is closed by construction — extraction worked, and **both halves independently
reproduced every measurement** in the extraction commits: 3/3 mutations, 16/16 and 14/14 self-tests,
the rollback proof (`skipping/LEFTOVER/DESTROYED = 0/0/0`), the 161-object inventory with its 14
triggers and 7/7 split, and the migration-ordering probe. Codex additionally confirmed no CLI path
replays `supabase/rollback/`, checking `db reset --sql-paths` and `migration repair`.

**So the artifacts are right. What was wrong is what I said about them** — and every r3 Blocking/High
sits in a seam *between* artifacts, where nothing executes.

⚠ **THE SUBJECT MOVED MID-REVIEW.** The Claude half was dispatched against `2649094`; the Codex fixes
landed as `5d5f1ed` while it ran. It re-ran each finding against both builds and labelled them. Two
of its findings (the comment-only fail-open, `strip_comments`' inverted bound) were found by Codex
too and were already closed — recorded, not double-counted.

---

## Disposition

| # | Finding | Half | Disposition |
|---|---|---|---|
| B1 | `build-m4-schema.py`'s end-state predicate is blind to **both** column edits | claude | ✅ **FIXED.** Coordinator-verified end-to-end |
| B2 | The gate names **29 of 161** objects (18%) and reports PRESENT with all 7 own-table guards dropped | claude | ⛔ **NOT FIXED — design fork, recorded in Task 3, escalated to the human** |
| B3 | The rollback never deletes the `schema_migrations` row, so Step 6's re-apply is a silent no-op | claude | ✅ **FIXED.** Rollback re-proven |
| H1 | `ASSERT_FILE` / selector fail-open, two shapes | codex | ✅ **FIXED** in `5d5f1ed` |
| H2 | Step 5's grep gate contradicts its own must-keep predicate | codex | ✅ **FIXED** in `5d5f1ed` |
| L1 | `strip_comments` blinded by a quoted `--` | codex | ✅ **FIXED** in `5d5f1ed` |

### B1 — verified by hand, not taken on trust

The residual filter excludes any line containing `no_corrections_hash`. The line it must catch is

```
  corrections_hash   text not null default no_corrections_hash(),
```

whose own DEFAULT contains that string. **MEASURED:** drift the anchor by one space and the script
exits **0**, reports `already`, and emits the ADR-0011 column into `0027`. The bare `corrections
text,` column was unguarded outright. A column DEFINITION is not a reference, so it needed its own
assertion over the table block.

⚠ **Bounded honestly:** `check-live-schema.py`'s `ADR0011_REMOVED` *would* have caught this after
apply, so it was netted one layer downstream. The Blocking is that `build-m4-schema.py`'s stated
verdict — *"rests on the END STATE"* — was false for two of its eight edits.

⚠ **And the first fix was wrong in the same way the defect was.** My table-block extractor used
`create table X\s*\((.*?)\n\);`, which passed against the real spec (it closes on its own line) and
failed on a fixture closing `primary key (a, b));` — **a pattern matching what I READ, not what is
THERE**, written into the very check meant to catch that. Replaced with paren-depth matching.
Self-test **14 → 22**.

### B3 — verified by search, since it is a negative claim

`grep -c schema_migrations` returns **0** in both the rollback and the plan. Presence in that table
is what marks a migration applied. Step 9 now deletes the row, guarded by an `information_schema`
check so a database that never ran the CLI is unaffected. Rollback re-proven: `0/0/0`.

---

## The recurring defect, now at FIVE and FOUR instances in one day

| Shape | Count today | Newest instance |
|---|---|---|
| *fixed at one of two sites* | **4** | H2 — created **by** the edit that introduced the requirement. **A predicate is a requirement, so its gate is a caller** |
| `$?` read after a pipe or substitution | **5** | `echo "exit=$? $(grep …)"` reported 0 while the command returned 1 |

Both now have a stated counter-practice. Neither is yet mechanical, and that is the honest status.

---

## Verdict

**NOT CONVERGED.** Five of six findings fixed; **B2 is a design fork the human owns.**

Round 4 is due on the fixes. ⛔ **Merging remains a human gate, and the M4-β production apply a
second one.** Nothing in this round changes either.
