# M4 plan v2.1 — round 2 COORDINATOR adjudication

**Subject:** `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md` @ `794f462`
**Halves:** `…-r2-codex.md` (**NOT CONVERGED**, 6B/2H) · `…-r2-claude.md` (**NOT CONVERGED**, 3B/6H/6M)

**Anchor:** stable-blob-addressing · **ADR:** 0006, 0007, 0011

---

## ⭐ THE ROOT CAUSE, and it is not in the plan's content

**Every Blocking across BOTH rounds — 8 distinct, 0 exceptions — lives inside a fenced code block
that I wrote and never executed.**

| Round | Finding | Form |
|---|---|---|
| r1 | `0028` drop order fails twice | fenced `sql` |
| r1 | `check-live-schema.verdict()` too narrow | fenced `python` |
| r1 | seed corpus violates `NOT NULL` + FK | fenced `sql` |
| r1 | `awk` selector is fail-open | fenced `bash` |
| r2 | two `drop function` signatures are silent no-ops | fenced `sql` |
| r2 | `check-live-schema.py` has no queries, no parser, no `main` | fenced `python` |
| r2 | seed now hits `duplicate key` via `on_auth_user_created` | fenced `sql` |
| r2 | `$REPO` is undefined in Task 4's snippet | fenced `bash` |

**Measured: this plan carries 48 fenced code blocks and 336 lines of executable code, as prose in a
Markdown file.** Not one line of it was ever run by its author. The reviewers run it — that is why
both rounds' most valuable findings came from the half that executes — and it fails every time.

**This is not a defect a v2.2 fixes.** Writing a third revision of unexecuted code invites a third
round of the same finding. `dev-process.md`'s own rule applies: *before adding a rule, ask whether it
can be a script.* The same question applies to a plan — **before writing code into a plan, ask whether
it can be a file.**

### The decision: EXTRACT AND EXECUTE

The four executable artifacts move out of the plan and into the repo, where they can be run:

| Artifact | Destination |
|---|---|
| `0028` rollback SQL | `supabase/migrations/0028_rollback_stable_blob_addressing.sql` (⚠ Task 6 ordering still governs when `0027` may be created) |
| the live-catalog gate | `scripts/check-live-schema.py` — a real script with a real `--self-test` |
| the assertion harness | `scripts/run-schema-assertions.sh` |
| the seed corpus | `docs/superpowers/specs/m4/seed-assertion-corpus.sql` |

**The plan then REFERENCES them and stops containing them.** A plan cannot ship broken code it does
not contain, and every one of these files has a way to be run before it is trusted.

---

## The headline fix HELD, and was proved rather than asserted

**`0028` runs clean.** The Claude half built `01+03+04` with Tasks 1–2 applied by content anchor,
extracted the plan's `0028` byte-for-byte, and executed it:

```
===BUILD_ALL_OK===
DROP TRIGGER ×7 · DROP VIEW ×3 · ALTER TABLE ×1 · DROP TABLE ×4 · ALTER TABLE ×3 ·
DROP TABLE ×1 · DROP FUNCTION ×13 · DROP TYPE ×1
===DROP_OK===
```

Three independent assertions, all stronger than the plan's own claim:

1. **Forward catalog diff `after EXCEPT before` → 0 rows**, across tables, views, indexes, columns,
   triggers, functions, types, policies **and constraints** — broader than the gate's five kinds.
2. **Reverse diff `before EXCEPT after` → 0 rows** — `0028` removes nothing predating M4.
3. **Zero silent no-ops, with a CONTROL.** A negative claim ("no `NOTICE … skipping`") needs proof the
   instrument can see one; it ran the same pipeline against known-absent objects and got the NOTICEs.
   **This is the discipline the rest of the plan lacked** — and it validates the signature fix I
   committed independently at `03b3505`, an hour before the review landed.

Also verified against the schema rather than the prose: `M4_FUNCTIONS` (13), `M4_LIVE_TRIGGERS` (7),
`M4_TABLES` (5), `M4_COLUMNS` (3), `M4_TYPES` (1) are exactly right. ⚠ The plan's "13 triggers" is
**not** — that is a `grep` artifact, off by one (r2-claude M4).

---

## The standing condition fired, and Phase 6 is NOT the answer

Both halves answer **yes**: v2.1's own fixes introduced new defects — the `M4_PHASE` parameter left
its callers unchanged, and the seed's `auth.users` line created a duplicate key.

**Phase 6 does not fire again.** It ran today, produced ADR-0011, and the design it examined is
holding: `0028` works, the inventory is right, ADR-0011 dissolved four findings and introduced none.
What is failing is **execution of the document**, not composition of the design — a different
pathology with a different fix, and the fix is above.

⚠ **The one class signal worth naming:** the `M4_PHASE` fix is the **third** instance today of *fixed
at one of two sites* — after v5's `:120` maintenance-window residue and the `05_assert` sweep. That is
the defect this repo names `true-about-the-name-silent-about-the-layer`, and three instances in one
day says the counter-practice is not yet mechanical. **A fix that adds a requirement must grep for
its callers, in the same edit.**

---

## Findings, both halves, deduplicated

| Finding | Codex | Claude | Disposition |
|---|---|---|---|
| `drop function` signatures wrong | B1 | — | **ALREADY FIXED** `03b3505`; codex proved the consequence (`cannot drop type artifact_kind`) |
| `check-live-schema.py` not a runnable script | B2 | — | → **extract to a real file** |
| Task 9 invokes the suite without `M4_PHASE` | B3 | B1 | → fix caller **and** grep for others |
| Suite cannot be green post-`0027` | B4 | — | **COORDINATOR-VERIFIED AND BROADER: FIVE of six gates rebuild from spec files, not two.** Only `check-docs` has no database. The existing suite is a *pre-migration* suite in its entirety |
| `05_assert` sweep incomplete (`:1913,:1915`) | B5 | H2 | → extend; anchor is also non-unique (codex H1) |
| Seed hits `duplicate key` | B6 | B2 | → extract to a real file and run it |
| `$REPO` undefined in Task 4's snippet | — | B3 | → extract |
| self-test says 5, defines 8 | H2 | M2 | → the real file's `--self-test` prints its own count |
| `check-live-schema` docstring describes the replaced gate | — | M3 | → extract |
| "13 triggers" is a grep artifact | — | M4 | → correct to the measured number |

---

## Hygiene

The Claude half executed `0028` and a full schema build. **Coordinator-verified:** 0 M4 tables, row
counts unchanged (`playlists=5124 videos=3547`), no scratch databases (`storage_vectors` is stock
Supabase), working tree clean apart from the two review files. A transient `extract_0028.py` appeared
at the repo root during the run and was removed by the reviewer before it finished.

⚠ **Verified against `794f462`** for both halves; HEAD was `03b3505` by the time they landed, which is
why the signature Blocking arrives already fixed.
