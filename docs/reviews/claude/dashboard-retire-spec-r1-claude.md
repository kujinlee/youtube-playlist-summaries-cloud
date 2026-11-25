Reviewed head: 0487f068096d66c8c2e58d11a12cd04e6cecc33c

# Claude half, round 1: adversarial review of `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md` (at 0487f068)

**Verdict: NOT CONVERGED.** Five majors and some minors, but no blocker. Most findings are scope gaps with a clear fix. The two that matter most are the unenforced append-only rule (M1) and K8 as specified (M2).

I did not reopen the owner's decision (retire the page and the per-PR rule, keep the asks).

**What I checked:**
- **Citations:** every file:line I spot-checked is accurate. That covers goal-tree, compaction-state, gen-dashboard, check-dashboard-entry, check-review-recorded, check-merge-ready, ci.yml, check-page-links, theme-token, page_markup, explainer-serve, the five guard exemptions, the docs lines and the memory lines.
- **Numbers re-run against the live store, all match:** 591 entries, 71 needs-you, 2 heads-up, 28 resolves, 96 flagged, 0 parse errors, 0 unresolved asks, parse time 0.053 s, manifests 70/44. The two unresolved heads-ups are `2026-08-31/5` and `2026-09-15/10`.
- **Only drift:** 626/32 are now 627/33, because the spec counts itself (m1).
- **Safe:** I ran nothing that writes into the worktree. Imports ran with `PYTHONDONTWRITEBYTECODE=1`, and the rename test ran in a scratch copy.

---

## BLOCKER

None. I looked for a missed reader that silently empties NEEDS YOU:
- `goal-tree.py`'s `collect` loop around line 1563 already wraps the dashboard source in try/except and records "NOT READ". It is loud, not silent.
- `session-state.sh` reaches the store only through `goal-tree.py`.
- `check-idle-stop.py`, `check-stalled-work.py` and the Stop hooks do not read asks.

## MAJOR

**M1. Nothing enforces "append-only", and a deletion can silently close an ask.**
- **Evidence:**
  - K1–K3 inspect only added header lines. `check-dashboard-entry.py:1308` `collect` parses the `-U0` patch.
  - K2's `added_reference_errors(base_text, head_text)` reports only new errors.
  - Ids are positional: the per-date ordinal is claimed at `check-dashboard-entry.py:665-670`, and the docstring at `:761` says appending renumbers.
- **Measured on the live store:**
  - Deleting one narrative entry (any of 2026-08-30/1–/4, or 2026-08-31/1) reopens an ask: unresolved goes 0→1, with K2 at 0 errors and K1 and K3 vacuous.
  - The mirror case is worse. A deletion that shifts a resolver's target onto an open ask closes it without any signal. **That is NEEDS YOU emptying itself.**
  - A trial "strip the narrative, keep the 96 flagged" changes 66 of 96 ids, reopens 63 asks and yields 19 errors.
- **Why it matters now:** once the narrative is declared dead history, the incentive to tidy it grows.
- **Fix:** add **K9**. Every base entry must survive unchanged at HEAD and in the same order: compare `(id → raw)` over `parse_entries(base)`, allowing only the one S2 edit to the header prose at lines 3–6. Mutate it with a "delete one narrative entry" case.

**M2. K8 fails on day one, or its exemption grows until it checks nothing.**
- **Evidence:** outside reviews, explainers and superpowers, the K8 pattern hits 74 files. 31 of them are in `scripts/` (mutations excluded); the spec estimates "about 10". Several hits are files the spec itself keeps:
  - `docs/dashboard-entries.md`, `docs/backlog.md`, `docs/roadmap-to-launch.md`, `docs/portable-practices.md` (:13 and :1410), `docs/round-header-template.md`
  - the non-dated memory files: a-check-result-is-not-the-claim, a-mutation-loses-its-binding, assert-the-property-not-the-mechanism, fixing-a-premise-is-not-covering-the-branch, a-costbenefit-finding-expires-when-the-denominator-moves
  - history comments in check-plan-code, expected_mutations, check-main-drivable, page_markup, page_chrome, check-theme-token-coverage, gen-goals-page, check-fixture-git-isolation, check-selftest-counts, check-review-decision and others.
- **Fix:** have K8 match **executable** references only:
  - file loads: `with_name("…dashboard…")`, `_sibling(...)`, `spec_from_file_location(... "gen-dashboard.py")`, `ROOT / "scripts" / "check-dashboard-entry.py"`
  - hook commands in `.claude/settings.json`
  - `run:` lines in `ci.yml`
  - `"file"` fields in `scripts/mutations/*.json`
  - keys of `REGENERABLE`, `PAGES` and `PAGE_SOURCES`

  State the frozen set as globs, not counts. State the observation that fails it: an executable load of a deleted path.

**M3. R4's reasoning is wrong, so it would delete the diagnosis for the incident that actually happened.**
- **Evidence:** `check-merge-ready.py:530` holds `GATE_ESCAPE`. `escape_diagnosis` (:2063) has three states. Only MISDIRECTED needs two markers. INVISIBLE (the exact token sits inside a fence, backticks or indentation) and MISSPELLED both work with a single marker. INVISIBLE was the real 2026-09-26 incident. "With one marker left there is nothing to confuse" is therefore false.
- **Fix:** keep `escape_diagnosis`, set `GATE_ESCAPE = {"review recorded": "NO-REVIEW:"}`, and drop only the MISDIRECTED branch and its fixtures. Keep `ESCAPE_LOOKALIKE` (:535) for `NO-REVIEW`.

**M4. Moving `exemption_reason` into `check-review-recorded.py` breaks merge-ready's fixtures and adds a heavy dependency.**
- **Evidence:**
  - `check-review-recorded.py:134` resolves `ROOT` from `__file__`, and `_load_declaration_parser` loads `ROOT/"scripts"/…`.
  - merge-ready's fixtures (`check-merge-ready.py:4171-4185`) copy only the gate file into `tempfile.mkdtemp()` and point `DASHBOARD_GATE` at it.
  - Once that file loads a sibling via `ROOT`, `ROOT` becomes the temp dir's parent, the load fails, and every one of those fixtures goes CANNOT RUN.
  - It also builds a chain: merge-ready → check-review-recorded (a large module) → ask-store.
- **Fix:** keep `exemption_reason` and the fence rule in the renamed `check-ask-store.py`. Today's `check-dashboard-entry.py` imports only stdlib, so it is the right home. Otherwise extract a tiny import-free module. Either way, the spec must say how the `:4171-4185` fixtures are rewritten.

**M5. The §4 inventory misses readers, and one of them breaks at S2.**
- **Main miss:** `scripts/check-explainer-delivery.py:53` hardcodes `PAGE_SKILLS = ["explain-topic", "dashboard"]` and requires `dashboard/SKILL.md` to cite `shared/explainer-delivery.md`. S2 rewrites the dashboard skill, and Q2 may rename it, so it stops producing a page. The guard then fails with "missing", or forces a false citation.
- **Second miss, the S2 rename:** in a scratch copy I renamed `check-dashboard-entry.py` → `check-ask-store.py`. `gen-dashboard.py:327` (`_gate_module`'s `with_name("check-dashboard-entry.py")`) then fails on import with FileNotFoundError. `brief-compose.py:609` `_contrast` lazily loads gen-dashboard, so `assert_em_in_every_palette` (called at `brief-compose.py:1784`) fails at runtime on every brief page that carries the text-style switcher. gen-dashboard survives until S3, so S2 must repoint `:327` in the same slice.
- **Smaller misses:**
  - `check-publishability.py:1902` uses `requires-skill dashboard` in a fixture.
  - The comment at `ci.yml:73` says fetch-depth 0 is "REQUIRED by the dashboard entry ratchet". K2 and K9 still need it, so reword it rather than deleting it.
- **Fix:** add these rows to the inventory. S2 removes `"dashboard"` from `PAGE_SKILLS`, or keeps the citation if a skill still composes a page, and repoints gen-dashboard's gate load. S3 repoints `brief-compose._contrast` to `page_chrome`'s `contrast_ratio`, along with `brief-compose.py:439`'s comment naming `gen-dashboard.CONTRAST_MIN`.

## MINOR

- **m1. Counts move.** 626/32 are now 627/33 because the spec counts itself, and the plan will add more. State the frozen set as globs (ties into M2).
- **m2. Nothing marks the goal tree stale after an ask is added, once S3 lands.**
  - `explainer-serve.py` `PAGE_SOURCES["goal-tree"]` is `["docs/goal-threads.md", "docs/goal-tree-answers.json"]`, without the store.
  - `regen-pages.py` `pages_for` maps only `goal-threads.md` to goal-tree.
  - `regen-dashboard.sh` (`settings.json:158`) is the only on-edit rebuild for a store write, and S3 deletes it.
  - **Fix:** S3 adds `docs/dashboard-entries.md` to `PAGE_SOURCES["goal-tree"]`, and to `pages_for`.
- **m3. Stale names after S3:**
  - `ci.yml:968` says check-page-links "builds the four … (dashboard, goals…)"; it will be three.
  - The case at `check-plan-code.py:7860` is named "check-dashboard-entry.py reaches compaction-state through gen-dashboard.py".
  - §5 S3's "four pages" is ambiguous: there are four regenerable pages but three CI-built ones. Say which.
- **m4. "Added block" is defined by added `+##` lines, so K1/K3 are both too loose and too strict.**
  - A modified header slips through.
  - Measured: a fenced `## Example heading` inside a new entry's body is flagged as a bad header ("not a real calendar date"), because `added_entry_problems` ignores fences.
  - **Fix:** define it as the parse difference of base and HEAD entries, which also falls out of K9.
- **m5. The resolve grammar is a trap.**
  - `[resolved: 2026-08-31/5, 2026-09-15/10]` parses as ONE id and errors ("names no entry").
  - Two brackets, `[resolved: a] [resolved: b]`, works and clears both heads-ups.
  - The rewritten skill text should state this. If the spec intends S2 to close the two heads-ups, say which form it uses.
- **m6. A needs-you ask without a Decide block passes K1.** `decision_errors` is not wired in (backlog #81). That is acceptable, but the spec should list it as an explicit bound of K1.
- **m7. Mutation bookkeeping.** The `contrast_ratio` and `CONTRAST_MIN` mutations move from `gen-dashboard.json` (for example the `PROSE_CONTRAST_MIN` manifest entry around line 343) to `page_chrome`. Count them in the 70/44 → N arithmetic, and have `expected_mutations.py` (:267, :857) say what it becomes.

## What holds up

- **Option A, "ids are positional": correct.** The ordinal is per date in file order (`:665-670`), and `resolvers` key on that id with the first later resolver winning. My deletion runs in M1 confirm it: any edit to the narrative renumbers ids and moves resolutions.
- **S1 is a safe merge point.** `check-dashboard-entry.py` imports only stdlib, and K5's try/except "NOT READ" path already exists in `goal-tree.py`.
- **S1 → S2 → S3 is the right order and it is forced,** once M4's ownership question and M5's same-slice repoint are settled. No slice leaves NEEDS YOU reading an empty source without saying so.
- **K4–K7 do not pass vacuously.** Each depends on a parse that raises, or reports NOT READ, when the store or page is missing. That leaves K1/K3 (m4), K8 (M2) and the missing K9 (M1).

VERDICT: NOT CONVERGED
