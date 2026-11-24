Reviewed head: b5047031c6ea239ce21bd713ece34c8ebf6f0e0a

# drop-explain-skills — round 1, Claude half (adversarial)

Subject: PR #627, commit b5047031 ("Explainer skills: drop brief, explain-diff and explain-findings, and retire
the PR-open explainer reminder"). Mandate: find anything still live that reads a removed path, id or skill name,
plus stale counts and broken consistency between the checkers.

Note on the brief: the prompt file named in the dispatch
(`scratchpad/de-r1-prompt.md`) did not exist on disk when this round ran, so this review follows the dispatch
message's mandate and output contract only.

Note on the tree: while this round ran, someone else edited `docs/marketplace/components.json` and
`docs/marketplace/inventory.json` in the working tree, and those edits are not committed. Every finding below was
re-read from `git show HEAD:<path>`, not from the working tree.

## What was run (all at HEAD b5047031)

| Check | Result |
|---|---|
| `check-publishability.py --self-test` | 177/177, rc 0 |
| `check-publishability.py --out /dev/null` (live scan) | 43 scanned, 0 CANNOT RUN, rc 0 |
| `check-explainer-delivery.py --self-test` / live | 8/8 / "1 shared description, 2 skills cite it, 0 restatements" |
| `check-shipping-sets.py --self-test` / `--map` / `--closure` | 170/170 / 0 gaps / 0 gaps |
| `check-inventory.py --self-test` / live | 311/311 / rc 3 (the D1 checkpoint fires over 31 phase-1 rows; CI treats rc 3 as a warning) |
| `check-selftest-counts.py --self-test` / `--only check-publishability.py` | 60/60 / verified |
| `check-canonical-source.py`, `mkt_stage.py`, `mkt_seed_repo.py`, `gen-goals-page.py` self-tests | 33/33, 119/119, 14/14, 83/83 |
| `check-run-hook.py --self-test` / live; `check-handoff-path.py --self-test` | 163/163 / 85 worlds ok; 24/24 |
| `check-docs.py`, `check-vocabulary-collisions.py` | OK / OK |

I grepped every tracked file outside `node_modules`, `.git`, `docs/reviews` and `docs/explainers` for
`explain-diff|explain-findings|suggest-explainer|skills/brief|skill-brief`. Nothing executable reads a removed path:
the remaining hits in `scripts/` are synthetic fixture worlds (`mkt_stage.py`, `check-shipping-sets.py`,
`check-explainer-delivery.py`, `check-publishability.py`'s fixture copy at
`scripts/fixtures/check-publishability/brief-SKILL-2f5e3f3d.md`), comments, or history. `candidates()` in
`check-shipping-sets.py` derives from disk (`CANDIDATE_DIRS`), so nothing hard-codes the removed directories.
`.claude/settings.json` no longer registers `suggest-explainer.sh`, and no script names it.

(Process note: running `scripts/regen-skills-doc.py --help` regenerates `docs/available-skills.md` in place. I
restored that file with `git checkout`. Its local-skills section came out identical to the committed hand edit.)

## Findings

**F1 — MAJOR — `docs/marketplace/inventory.json` (29 rows, e.g. :543, :586).** Twenty-nine surviving rows price
part of their route as "+ 4 h the template repository (shared; **owned and described in skill-brief's row**)".
This PR deleted `skill-brief`'s row, so the 4 h shared cost now has no owner and no description anywhere in the
inventory. The 30th mention of "template repository" in the file is a route kind, not a description. A reader
checking any of the 29 routes (`skill-explain-topic` 13 h, `skill-dashboard`, `brief-compose`, `gen-dashboard`, the
five regen hooks, `contract-explainer-delivery`, …) is sent to a row that does not exist. `check-inventory.py`
cannot see this because the route arithmetic is prose in `notes` (backlog #706 already records that blind spot),
so the checker stays green. **Fix:** move the template-repository cost's ownership and description into a surviving
row (for example `skill-explain-topic` or `brief-compose`), and re-point all 29 references. **Fails if** any row
at the new head still says "owned and described in skill-brief's row".

**F2 — MINOR — `docs/marketplace/components.json:2` and `docs/dashboard-entries.md:21531`.** The new count is
wrong. `measured_at` says "⟳ 2026-11-23: 42", and the dashboard entry says "(45 -> 42)". The map holds **43**
components (effort 3: 31, effort 2: 6, effort 1: 6). The parent commit held 46 (effort 3: 34), so the earlier
"45" was already stale, and subtracting 3 from it carried the error forward. The scan prints "43 component(s)",
and the same dashboard entry correctly says "46 -> 43 rows" for the inventory, so the entry contradicts itself.
The same `measured_at` clause also says "skills stay installed here", which is false: this PR removes the skill
directories and their `.claude/skills/` links. **Fix:** say 43 (46 → 43), with the effort split, and drop "stay
installed here". **Fails if** the stated count differs from `len(components)`.

**F3 — MINOR — `scripts/check-publishability.py:2585`.** Under `PLAN_CODE_MUTATION_RUN=1` the script prints "NOT
RUN under the mutation harness: **10** live-tree cases". This PR removed three of them from that `else` block, which
now holds **7** `case(` calls. The message under-reports what the mutation harness skips. The docstring count (177)
was updated, but this number was not. **Fix:** 7, or derive the number from the block. **Fails if** the printed
number differs from the number of cases in the `else` branch.

**F4 — MINOR — `docs/marketplace/inventory.json:1179` (`contract-explainer-delivery`).** The notes still say
"Imported by the five page skills, all exercised and all failing" and "This row owns that price for all five page
skills". After this PR two page skills import the contract (`explain-topic`, `dashboard`, matching
`PAGE_SKILLS`). The row's `scenario` (:1146) is "skill-brief: A-skill-brief …". Its grade (`measured`) rests on a
tier-A observation of a component that is no longer in the map. That is arguably still valid as a recorded
measurement, but the row does not say so at HEAD. **Fix:** say two importers, and add a note on the scenario that
the measuring component was retired and the observation stands as recorded. **Fails if** the row still counts
five importers.

**F5 — MINOR — `docs/roadmap-to-launch.md:1379` (also :1363).** The open checkbox "[ ] **Judge explain-diff in the
next general skill prune**" (FAILS IF the prune keeps it with none of the four outcomes) is now settled: the owner
retired the skill on 2026-11-23. The roadmap still shows it open, and :1363 points to `.agents/skills/explain-diff/`,
which no longer exists. The process doc requires the roadmap to be updated in the same PR as the work it describes.
**Fix:** tick it with the outcome (retired by the owner on 11-23, unused since August), and mark the section
retired. **Fails if** the box is still unticked at merge.

**F6 — NIT — remaining live prose that describes the removed skills as current.**
- `.claude/hooks/regen-features-page.sh:4` and `.claude/hooks/regen-goals-page.sh:4`: "`/explain-diff`, `/brief`
  and `/explain-findings` are composers".
- `scripts/mkt_seed_repo.py:14`: its docstring defines the known-facts set by pointing to
  `.agents/skills/brief/SKILL.md` → *Step 1*, a file that no longer exists. A frozen copy exists at
  `scripts/fixtures/check-publishability/brief-SKILL-2f5e3f3d.md`; re-point the docstring there.
- `docs/memory/document-approval-is-interactive.md:28` ("`explain-topic`, `brief`, `explain-diff`,
  `explain-findings` all cite it") and `docs/memory/explainer-pages-lead-with-diagrams.md:18` ("for every page from
  explain-topic / explain-diff / brief / explain-findings"): instructions that name skills which no longer exist.

None of these break anything. Each sends a reader to something that is gone.

Not findings (checked): `explainer-delivery.md` history lines, `explainer-spec.md`, `portable-practices.md`
:1407-1411, the experiment-tier-a/b records and the `scan-2026-11-*.json` files are dated measurements. They are
correctly left as written. `check-explainer-delivery.py`'s self-test fixtures use the names `explain-diff` and
`brief` as synthetic directory names inside temp worlds, and that is harmless.

VERDICT: NOT CONVERGED
