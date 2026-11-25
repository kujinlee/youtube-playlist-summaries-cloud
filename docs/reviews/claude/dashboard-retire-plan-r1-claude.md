Reviewed head: c15800910df7fc0de651e0553c6abdbdbaae89b2

# Dashboard-retire plan — adversarial review r1, Claude half

Subject: `docs/superpowers/plans/2026-11-24-dashboard-retire.md`, which implements the approved spec
`docs/superpowers/specs/2026-11-24-dashboard-retire-design.md`. The spec was not argued.

## What was checked and held

- **Gate mutation arithmetic.** The gate has 44 mutations in `scripts/mutations/` that anchor to
  `scripts/check-dashboard-entry.py`, counted by symbol:
  - parse_entries 7; exemption_reason 4; _declaration_reason 4; collect 4; fence_closes 4;
  - verdict 3; decision_errors 3; header_error 3; main 2; decisions 2;
  - 1 each for _added_entry_line, _indented, BLOCK, added_entry_problems, EMPH, ENTRY_ISH, fenced_lines and
    _first_sentence.

  That matches the plan's 9 deleted in S2, 12 deleted in S3 and 23 staying.
- **Pins in `scripts/mutations/expected_mutations.py`.** Every number the plan quotes matches the file:
  gen-dashboard 70 (:267), goal-tree 520 (:486), check-dashboard-entry 44 (:857), page_chrome 114 (:1510),
  explainer-serve 123 (:1576), compaction-state 89 (:1963), check-merge-ready 214 (:2168),
  check-reference-namespace 22 (:2221), regen-pages 73 (:2291).
- **Symbols the plan edits exist as named.**
  - goal-tree: `DASHBOARD_REL` :127, `NEEDS_SOURCES` :133, `needs_from_dashboard` :1305, the source loop
    :1563, `needs_state` :2445, `needs_lines` :2525.
  - compaction-state: `_load` :151, `_open_regular` :343, `pending_asks` :473, which reads through
    `gen-dashboard.unresolved` :482.
  - explainer-serve: `REGENERABLE` :223, `PAGE_SOURCES` :243, `RETIRED_FILES` :277, `retired_target` :1031,
    `_drive_stale` :4340, the coverage case at :3195.
  - check-merge-ready: `DASHBOARD_GATE` :653, the gate-list row :2198, `_real_cde` and `_gate_main`
    :4171–4280.
  - regen-pages: `pages_for` :594.
  - ci.yml: self-test steps :984–988, the PR-only ratchet step :1106–1113.
- **Slice order.** S1 is additive and keeps `needs_from_dashboard` alive while `read_asks` lands. S2
  renames the gate and freezes the store by SHA-256 in the same task that removes R1. NEEDS YOU never reads
  nothing between slices, and the old store is never left unguarded.
- **Retired-path literals.** I swept every list or tuple literal in tracked Python with an AST walk. Every
  hit outside the two retired scripts is in a file that plan Tasks 13–15 name:
  - check-main-drivable, check-merge-ready, check-page-links, check-plan-code and check-publishability;
  - check-ratchet-contract, check-review-decision, gen-goals-page and regen-pages.

  `check-review-decision.py:806` and `gen-goals-page.py:1016` use `scripts/gen-dashboard.py` only as an
  arbitrary script path inside a fixture. They stay correct after the file is deleted, but the K8 scanner
  in Task 15 visits list elements and will flag them. Task 15's allow-list or a fixture rename must cover
  them (MINOR 4).
- **`docs/CLAUDE.md` rule 3.** Both spec :350 and plan :578 cover it.

## Findings

### MAJOR 1 — Task 2 turns an existing impure case red, and only in CI

Evidence:
- Plan :242–248: after Task 2, `main` calls `ask_store_problems(base, ROOT)` after `collect`, and a git
  failure there returns rc 2.
- `scripts/check-dashboard-entry.py:1470–1477`: the existing case "main: an entry-only branch with a
  malformed entry exits 1" stubs ONLY `g["collect"]`, then calls `main(["--base", "master"])`.

After Task 2, that call reaches the real F1/A1 git (`git merge-base master HEAD` or similar) at ROOT. In a
CI `pull_request` checkout (ci.yml :73–80, fetch-depth 0) there is `origin/master` but no local `master`
branch. Git therefore fails, `main` returns 2 instead of 1, and the case goes red.

Locally `master` exists and the case stays green, so the implementer's local run will not show the break.
`check-plan-code --mutate --only` will not show it either. The "could-not-tell exits 2" case is not
affected, because it returns before A1.

Fix: Task 2 Step 1 must:
- stub `ask_store_problems` in every existing `main` case (save it, then restore it in `finally`, as
  `collect` is handled);
- add two `main` cases: a stubbed problem list gives rc 1, and a stubbed `(_, err)` gives rc 2.

Also add the S2 rename's impure suite to the "run in a checkout with no local master" check. The cheap way
is a `git -C <scratch clone> branch -D master` world in the case itself.

### MAJOR 2 — behaviour 2.12 does not reach the path it names, so A1's git-failure branch is unguarded

Evidence:
- Plan :265: 2.12 is "a broken git under A1 is CANNOT RUN — impure: `git` not on `PATH` → rc 2".
- Plan :286: no mutation in Task 2's table targets `ask_store_problems`' err return.

Driven through `main`, a missing `git` fails first inside `collect`, at its first git call
(`check-dashboard-entry.py:1308` and after). So 2.12 passes on `collect`'s existing CANNOT RUN, and it
would still pass if `ask_store_problems` swallowed its own git error and returned `([], None)`. That is a
fail-open path: no asks read, rc 0.

Fix: drive `ask_store_problems` directly, with the runner stubbed to raise or return non-zero (the
existing `_with_run` / `_boom` pattern), and assert `err` is not None. Add the mutation "A1's git failure
returns err=None" to the Task 2 table, naming that case.

### MINOR 3 — 1.16's trigger contradicts itself

Plan :184 gives the trigger as both "1,001 valid names" and "`MAX_ASKS` patched to 3 with 4 files". These
are two different worlds: an implementer picks one, and the other is not tested.

Fix: state one trigger. Patch `MAX_ASKS` to 3 with 4 files: it is cheap and deterministic. Keep 1,001 only
if the real cap is the thing under test.

### MINOR 4 — K8's scanner will flag two fixture literals the plan does not list

Evidence: `scripts/check-review-decision.py:806` and `scripts/gen-goals-page.py:1016` hold
`"scripts/gen-dashboard.py"` as a list element in a self-test fixture. Plan :791 says the K8 scanner
visits list and tuple elements.

Neither file is in Task 15's edit list (plan :476–488). After S3, `check-retired-references.py` will
refuse them, or Task 15's Step 7 run will surface them as a surprise.

Fix: name both in Task 15. Either rename the fixture path to a live script, for example
`scripts/gen-backlog-page.py`, or exempt them with a reason.

### MINOR 5 — the push-mode L1 freeze also runs on `batch/**`

ci.yml's `on.push.branches` is `[master, 'batch/**']`. Task 12's push-mode "ask store" L1 step therefore
runs on batch branches as well as master. That is probably intended, since a batch branch must not edit
the frozen file either, but the plan does not say so.

Fix: one sentence in Task 12 that states it is intended. Otherwise guard it with
`if: github.ref == 'refs/heads/master'`.

## Not run

I did not execute the plan's fenced anchor-resolve block (plan :56–74) or the Task 8 grep on a scratch
copy before writing this. Treat those as NOT RUN in this half. The mutation counts and pins above were
checked by direct count against `scripts/mutations/` and `expected_mutations.py`, not by running that
block.

VERDICT: NOT CONVERGED
