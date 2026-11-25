# Retire the dashboard page and the per-PR entry rule; keep the asks as the goal tree's NEEDS YOU source

> **Anchor:** `status-visibility` — **ADR:** 0010
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** 🟠 needs-you — Phase 1 draft, 2026-11-24. Not yet reviewed, not yet walked through. Nothing here is built.

Goal thread: `dashboard-decisions` (`docs/goal-threads.md`). Why this anchor: the page being retired and the
goal tree that keeps its asks are both pages of `status-visibility`, and the two specs this one amends
(§1.2) are anchored there.

## In plain words

Today every pull request must add a dated paragraph to `docs/dashboard-entries.md`, and a page at
`/dashboard` renders those paragraphs. The owner decided to stop both. One part of that file is still
needed: the entries that ask the owner a question, and the later entries that record the answer. The
goal tree reads those to fill its NEEDS YOU list, and it will keep doing so.

The catch this spec exists for: the code that reads those questions lives inside the two scripts being
retired. Deleting them as they stand would empty NEEDS YOU without any error. So the reader moves first,
the rule is removed second, and the page is deleted last.

## The owner's decision this spec designs within (settled, not reopened)

| # | Decision | When |
|---|---|---|
| O1 | Retire the dashboard PAGE and the per-PR dashboard-entry rule. KEEP the needs-you / resolved asks in `docs/dashboard-entries.md` as the goal tree's NEEDS YOU source. | 2026-11-24 09:57, selection card, option A |
| O2 | The implementation PR may merge on dual-review convergence and green CI although it loosens a gate. | same day, stated with O1 |

## 1. Problem — measured at `b02f0a25`, 2026-11-24

### 1.1 What exists

| Thing | Size | What it is |
|---|---|---|
| `scripts/gen-dashboard.py` | 3,588 lines | the page generator, and the ask MODEL (`unresolved`, `resolvers`, `cleared_ids`) |
| `scripts/check-dashboard-entry.py` | 1,511 lines | the per-PR gate, and the store GRAMMAR (`parse_entries`, `fenced_lines`, `decisions`) and the PR-body waiver parser (`exemption_reason`) |
| `docs/dashboard-entries.md` | 21,611 lines, 1.72 MB | 591 entries, 2026-08-28 to 2026-11-24, 0 parse errors |
| `scripts/mutations/gen-dashboard.json` / `check-dashboard-entry.json` | 70 / 44 mutations | pinned in `scripts/mutations/expected_mutations.py:267` and `:857` |

The store, read by its own parser (`parse_entries` then `unresolved`): **71** entries are flagged
`[needs-you]`, **2** `[heads-up]`, **28** carry `[resolved: …]`; **96** entries carry any flag, **495**
are narrative only. **Unresolved asks today: 0.** Unresolved heads-ups: 2 (`2026-08-31/5`,
`2026-09-15/10`). Flagged entries hold 151,738 of 655,489 characters of entry text (23%).

### 1.2 The dependency that makes plain deletion unsafe

Three readers outside the page reach the asks, and every one goes through code slated for deletion:

| Reader | Where | What it calls |
|---|---|---|
| goal tree NEEDS YOU | `scripts/goal-tree.py:1305` (`needs_from_dashboard`) | `_sibling("gen-dashboard")` → `gd.parse_entries`, `gd.unresolved`, `gd._slug`; link from `page_markup.key_link("dashboard", …)` |
| post-compaction snapshot | `scripts/compaction-state.py:473` (`pending_asks`) | `_load("gen-dashboard.py", …)` → `gd.unresolved(gd.parse_entries(text))` |
| the page itself | `scripts/gen-dashboard.py:338` | `_GATE = _gate_module()` — loads `check-dashboard-entry.py` for the grammar |

`gen-dashboard.parse_entries` is not its own code: `scripts/gen-dashboard.py:340` rebinds it from the gate.
So the chain is goal tree → `gen-dashboard.py` → `check-dashboard-entry.py`. `unresolved` itself is
defined in the generator (`scripts/gen-dashboard.py:454`).

`check-goal-status.py` and `brief-compose.py` do **not** read asks: the first only names the store in a
docstring (`scripts/check-goal-status.py:46`); the second loads the generator for a colour formula
(`scripts/brief-compose.py:609`). No SessionStart hook reads the store directly; the compaction snapshot
above is the only hook-side reader.

A second, unrelated dependency sits in the same gate file: `exemption_reason`, the parser for a waiver
line in a PR body. It serves `NO-ENTRY:` (retiring) **and** `NO-REVIEW:` (staying):

| Consumer | Where |
|---|---|
| review-recorded gate | `scripts/check-review-recorded.py:678` (`_load_declaration_parser` loads `check-dashboard-entry.py`) |
| merge-ready | `scripts/check-merge-ready.py:653` (`DASHBOARD_GATE`), used at `:2056` |

### 1.3 What the earlier spec said, and what O1 changes

`docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md` planned the opposite on both halves:
the dashboard stays as *a pure change log* (its R3 and migration step 5) and the asks LEAVE the store for
the in-flight ledger and the backlog, after which `needs_from_dashboard` is deleted (its migration step 4,
*Dashboard asks*). Neither was built: `needs_from_dashboard` is live at `scripts/goal-tree.py:1305`.

O1 supersedes those parts. §6 lists every amended line.

## Prior art

`python3 scripts/prior-art.py --decisions gen-dashboard check-dashboard-entry dashboard-entries.md unresolved exemption_reason`
— 3,584 documents scanned, rc 0. What it returned that bears on this design:

| Source | What it settles here |
|---|---|
| `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` §6.2 | the entry grammar — unchanged by this spec |
| `docs/superpowers/specs/2026-08-31-dashboard-ask-choices-design.md` | `unresolved()` is computed first and `decision_errors` runs only on unresolved entries; one clearing mechanism (`[resolved: <id>]`), no expiry — kept |
| `docs/superpowers/specs/2026-09-06-referential-entry-gate-design.md` | why the parser lives in the gate: a `[resolved: …]` reference is a property of the whole store (backlog #82) — the reason the kept rules in §3 need the parser beside them |
| backlog #85 | three fence scanners for one Markdown rule had drifted; unified in the gate. The fence rule must not be copied when code moves |
| backlog #389 (done, PR #434) | the precedent for retiring a page: the goal tree absorbed work-lines, and the history was archived as a small frozen record page (`docs/explainers/work-lines-archive.html`, 2,984 bytes), served through `RETIRED_FILES` (`scripts/explainer-serve.py:277`) |
| backlog #623 (open) | dashboard asks should carry ✍ DECISION tags, built in `gen-dashboard.py` — its target file is being deleted; retargeted in §5 |
| backlog #586 | per-PR edits to the shared store are why a docs-only PR selects most mutation manifests, and `scripts/batch-ci.py:82` measured the store touched by 73 PRs — the cost this retirement removes |

Searched and found nothing: no earlier spec, ADR or backlog row proposes deleting the page.

## 2. Design

### 2.1 Concern → mechanism (after all slices)

| Concern | Mechanism | Evidence it is the only one |
|---|---|---|
| What is an entry, and which asks are open | `scripts/check-ask-store.py` — the grammar and the ask model in one file | today split across two files (§1.2); this merges them |
| The store stays readable | the same script, run as a gate (§3 K1–K3) | rules already exist as `added_entry_problems` and `added_reference_errors` |
| Showing the owner what waits on them | `scripts/goal-tree.py` NEEDS YOU | after S3 no other page lists asks |
| A PR-body waiver line | `exemption_reason`, owned by `scripts/check-review-recorded.py` | its one remaining marker is `NO-REVIEW:` |
| One Markdown fence rule | `fence_closes` / `FENCE` in `check-ask-store.py`; `check-review-recorded.py` loads it from there | backlog #85 — no copy |
| One WCAG contrast formula | `page_chrome.py` | today `scripts/gen-dashboard.py:1431`, borrowed by `scripts/brief-compose.py:609` |

### 2.2 What already does this?

| New thing | Existing mechanism | Why it is not enough as it stands |
|---|---|---|
| `check-ask-store.py` | `scripts/check-dashboard-entry.py:600` (`parse_entries`) and `scripts/gen-dashboard.py:454` (`unresolved`) | it is the same code, renamed and shrunk — not a new mechanism. It is done as a `git mv`, so history and the grammar's mutations follow |
| the kept store gate | `scripts/check-dashboard-entry.py:745` and `:780` | the same two functions; only the "an entry is owed" branch of `verdict` (`:813`) is removed |
| the archive record page | `RETIRED_FILES`, `scripts/explainer-serve.py:277` | nothing new: one more row in that table |

### 2.3 The kept file

`docs/dashboard-entries.md` keeps its name and its place (O1 names it; five guards exempt it by path:
`scripts/check-canonical-source.py:248`, `scripts/check-reference-namespace.py:61`,
`scripts/batch-ci.py:99`, `scripts/compaction-state.py:476`, `scripts/goal-tree.py:127`). Its header
lines 3–6 are rewritten to say what it now is. From the cutover on it takes two kinds of entry only:

```md
## 2026-11-25 [needs-you]
One plain sentence saying what is being asked.

**Decide:** which archive form to keep
- A small record page [recommended]
- A full frozen render

## 2026-11-26 [resolved: 2026-11-25/1]
The owner chose the record page.
```

Header, flags, the `**Decide:**` block, `[recommended]` and the positional id `YYYY-MM-DD/N` are exactly
today's grammar (`scripts/check-dashboard-entry.py:25`, `:26`, `:347`–`:349`). No grammar change.

### 2.4 What the owner sees for an ask after the page is gone

Today the goal tree shows an ask's title (cut to 160 characters) linked to `/dashboard#<slug>`
(`scripts/goal-tree.py:1314`); the question and its options are readable only on the dashboard page.
Deleting the page would leave a title and a dead link.

So in S3 the goal tree's NEEDS YOU item shows, under the title, the ask's question and options as a
plain list — read by the store's own `decisions()`, never re-parsed — and the item has no link. The
yellow ✍ tag styling stays backlog #623's work, now aimed at `scripts/goal-tree.py`.

## 3. Gates removed and kept

### Removed

| Gate | Where | Why it can go |
|---|---|---|
| R1 "a branch that changes tracked files adds an entry or declares `NO-ENTRY:`" | `verdict`, `scripts/check-dashboard-entry.py:813`; CI step `dashboard entry ratchet`, `.github/workflows/ci.yml:1106`; replayed by `scripts/check-merge-ready.py:2198` | O1 |
| R2 `gen-dashboard.py --self-test` | `.github/workflows/ci.yml:984` | its subject is deleted |
| R3 the dashboard rows of the page-link, theme-token and contrast checks | `scripts/check-page-links.py:82`, `:91`, `:253`; `scripts/check-theme-token-coverage.py:70` | their subject is deleted |
| R4 the `NO-ENTRY:` / `NO-REVIEW:` wrong-marker diagnosis | `GATE_ESCAPE`, `scripts/check-merge-ready.py:530` | with one marker left there is nothing to confuse |

### Kept — each with its falsifier

| # | Gate | FAILS IF: |
|---|---|---|
| K1 | an added entry is well-formed (`added_entry_problems`) | a branch adds a `##` block to the store whose header is not a valid date plus known flags |
| K2 | an added reference resolves (`added_reference_errors`) | a branch adds `[resolved: <id>]` naming no earlier entry in the store |
| K3 | **new** — the store takes asks and answers only | a branch adds a block carrying neither `[needs-you]` nor `[resolved: …]`. This is O1 turned into a check: without it the per-PR narrative can drift back unnoticed. A new `[heads-up]` is refused too — after S3 nothing displays one |
| K4 | the goal tree reads the asks through the store's one parser | `needs_from_dashboard` returns no item for a fixture store holding one open ask; or its call to `unresolved` is severed and the goal tree's self-test stays green |
| K5 | an unreadable store is never an empty NEEDS YOU | the store is missing or holds an unparseable entry and the goal tree prints "nothing waits on you" (today: `scripts/goal-tree.py:1317` reports the source NOT READ) |
| K6 | the compaction snapshot reports the open-ask count | `pending_asks` returns a count other than the fixture's, or returns 0 when the reader cannot be loaded (today it returns CANNOT RUN, `scripts/compaction-state.py:485`) |
| K7 | `NO-REVIEW:` is still parsed by one definition | `check-review-recorded.py --self-test` or `check-merge-ready.py --self-test` goes green with `exemption_reason` replaced by a stub; or a fenced `NO-REVIEW:` line is granted |
| K8 | nothing still points at the retired things | `git grep -l -E 'gen-dashboard|check-dashboard-entry|regen-dashboard'` returns a path outside the frozen set of §4.3 |

⚠ **The live store cannot prove K4 or K6.** It holds 0 open asks today, so "the same answer before and
after" on the live file is 0 = 0 whether or not the reader works. Both are proven on a fixture with open
asks, and by a mutation that severs the call.

K1–K3 run in CI on pull requests as one step, `ask store`, calling
`python3 scripts/check-ask-store.py --base "origin/$GITHUB_BASE_REF"`; it takes no PR body. Its
`--self-test` runs unconditionally, as today's does at `.github/workflows/ci.yml:987`.

### Doc rules that say "every PR adds an entry"

| Where | Change |
|---|---|
| `docs/dev-process.md:162`–`:163` | two rows become one: `scripts/check-ask-store.py` — *an entry added to the ask store parses, resolves, and is an ask or an answer*. Net −1 line, inside the budget `scripts/check-docs.py` enforces |
| `docs/process-checklists.md:1162`–`:1163` | the same two full rows become one |
| `docs/process-checklists.md:400` | the committed-diff list names `check-ask-store.py` |
| `docs/process-checklists.md:557`, `:678` | unchanged — the store is still a dated, append-only record |
| `docs/CLAUDE.md:24` | rule 3 names `check-ask-store.py`; the committed-diff warning still holds |
| `docs/portable-practices.md:16` | drop `regen-dashboard.sh` from the hook list; `:13` and `:1410` are dated measurements and stay |
| `.agents/skills/dashboard/SKILL.md` | rewritten: how to write an ask and how to record its answer; no "record what changed", no page |
| `docs/memory/nothing-needs-you-must-read-the-dashboard.md` and its `MEMORY.md` row | the rule becomes "read the goal tree's NEEDS YOU count" — the command it names (`regen-pages.py --page dashboard`) stops existing |
| `docs/memory/parallel-branches-append-to-one-log.md` | the store leaves its list of files every branch appends to |
| `docs/memory/merge-ready-slice-merged-324.md:21`, `docs/memory/push-is-mine-merging-is-theirs.md:34` | the `NO-ENTRY` mentions are removed |
| `docs/roadmap-to-launch.md` | history rows stay; one new row records the retirement and this spec |

## 4. Inventory — every hit, classified

Source: `git grep -l -E 'dashboard-entr|gen-dashboard|check-dashboard-entry|regen-dashboard'` at
`b02f0a25` — **626 files**.

### 4.1 Delete

| File | Slice |
|---|---|
| `scripts/gen-dashboard.py` | S3 |
| `scripts/mutations/gen-dashboard.json` | S3 (entries anchored to moved code move with it in S1) |
| `.claude/hooks/regen-dashboard.sh` and its registration at `.claude/settings.json:158` | S3 |
| `.claude/skills/dashboard` (a symlink to `.agents/skills/dashboard`) | follows the skill (§7 Q2) |

### 4.2 Rename or edit

| File | Change | Slice |
|---|---|---|
| `scripts/check-dashboard-entry.py` → `scripts/check-ask-store.py` | `git mv`; gains `unresolved`, `resolvers`, `cleared_ids`, `unresolved_heads_up`, `_pos`, `_slug` in S1; loses `verdict`'s owed-entry branch, `NO_ENTRY`, `EXEMPT_*`, `_is_exempt`, `exemption_reason` family in S2; gains K3 | S1 move-in, S2 rename |
| `scripts/mutations/check-dashboard-entry.json` → `check-ask-store.json` | follows the file; R1's entries are deleted, never left unbound | S2 |
| `scripts/goal-tree.py` | `:1309` loads the store script, not the generator; `:42` docstring; in S3 `:1314` drops the link and shows the options (§2.4); cases at `:5349`, `:5653` | S1, S3 |
| `scripts/compaction-state.py` | `:482` loads the store script; `:41`, `:474` wording; case at `:2084` | S1 |
| `scripts/check-review-recorded.py` | becomes the owner of `exemption_reason` and `_declaration_reason`; `:678` loader removed; fence rule loaded from the store script | S2 |
| `scripts/check-merge-ready.py` | `:653` points at `check-review-recorded.py`; `:2198` replays `ask store`; `GATE_ESCAPE` and its diagnosis removed; fixtures at `:2353`, `:4171`–`:4280` | S2 |
| `.github/workflows/ci.yml` | `:984`–`:985` removed (S3); `:987`–`:988` and `:1106`–`:1113` renamed, the PR body dropped (S2); comments at `:1064`, `:1120` | S2, S3 |
| `scripts/brief-compose.py` | `:609` takes `contrast_ratio` from `page_chrome.py` | S3 |
| `scripts/page_chrome.py` | gains `contrast_ratio` / `_luminance` (moved, with their mutations) | S3 |
| `scripts/page_markup.py` | `key_link` loses the `dashboard` kind (`:206`), cases `:990`, `:999` | S3 |
| `scripts/check-page-links.py` | `:82`, `:91`, `:99`, `:104`, `:253`–`:255` lose the dashboard | S3 |
| `scripts/check-theme-token-coverage.py` | `:70` `PAGE_SRC` needs another generator's palette as its reference — which one is a plan decision, UNVERIFIED here | S3 |
| `scripts/explainer-serve.py` | `:224`, `:244` removed; `RETIRED_FILES` (`:277`) gains `dashboard.html`; cases | S3 |
| `scripts/regen-pages.py`, `scripts/regen-pages.sh`, `.claude/hooks/regen-pages.sh` | fixtures and comments naming the dashboard | S3 |
| `scripts/mutations/expected_mutations.py`, `scripts/sweep-costs.json` | pins and cost rows for the two scripts | S2, S3 |
| `scripts/check-fixture-variation.py` (`:263`, `:1270`, `:1440`), `scripts/check-main-drivable.py`, `scripts/check-plan-code.py`, `scripts/check-publishability.py`, `scripts/check-shipping-sets.py` (`:1812`), `scripts/check-ratchet-contract.py` | tables and live-tree cases that name either script; each is re-pointed or its row removed. The exact edit per case is the plan's work — UNVERIFIED case by case here | S2, S3 |
| `docs/marketplace/components.json`, `shipping-sets.json`, `inventory.json` | four components leave (`skill-dashboard`, `gen-dashboard`, `check-dashboard-entry`, `hook-regen-dashboard`), one arrives; regenerated by their own tools, never hand-edited | S2, S3 |
| `docs/dashboard-entries.md` | header lines 3–6 only | S2 |
| `.agents/skills/dashboard/SKILL.md`, the docs and memory rows of §3 | as §3 | S2 |
| `CONTEXT.md:154`, `docs/adr/0015-a-page-paraphrases-freely-and-cites-decision-symbols.md:67`, `.gitignore:160` | name the store or the generator in passing; reworded only where they would become false | S3 |
| `docs/backlog.md` | row 623 retargeted to `scripts/goal-tree.py`; one new row for this work | S1 |

### 4.3 Keep, untouched — the frozen set

| Files | Count | Why |
|---|---|---|
| `docs/reviews/**` | 484 | frozen testimony |
| `docs/explainers/**` | 26 | pages as delivered on their day |
| `docs/superpowers/**` | 32 | earlier specs and plans; two are amended by a dated note (§6), none rewritten |
| `docs/marketplace/scan-2026-11-17.json`, `scan-2026-11-21.json`, `experiment-tier-a.*`, `experiment-tier-b.md` | 6 | dated measurements |
| `docs/memory/*-merged.md` and other dated memory files | about 10 | records of shipped slices |
| `scripts/fixtures/*.json` | 3 | recorded corpora; a fixture naming a deleted path is still the recording |
| `scripts/batch-ci.py`, `scripts/check-canonical-source.py`, `scripts/check-reference-namespace.py` | 3 | they name the STORE, which stays |
| comments citing either script as history (`scripts/check-backlog-closure.py:82`, `scripts/peer-sites.py:481`, `scripts/gen-backlog-page.py:2771`, `scripts/codex-review.py:1933` and the like) | about 10 | a dated account; reworded only if a guard in §3 K8 would otherwise fail |

K8's frozen set is this table. The plan turns it into an explicit path list.

## 5. Slices — independently mergeable, in this order

| # | Slice | Changes behaviour? | What proves it worked |
|---|---|---|---|
| S1 | **Move the ask reader beside the grammar.** The ask model moves from `gen-dashboard.py` into `check-dashboard-entry.py`; the generator rebinds it through `_GATE` as it already does for `parse_entries`; the goal tree and the compaction snapshot load the gate file. No rename yet. | No | K4 and K6 on a fixture with open asks; a mutation severing each call site goes red; `gen-dashboard.py --self-test` unchanged; the two manifests' sum is unchanged (entries relocate) |
| S2 | **Remove the per-PR rule.** Rename to `check-ask-store.py`; delete R1 and `NO-ENTRY:`; move `exemption_reason` to `check-review-recorded.py`; add K3; CI, merge-ready, the skill, the doc rules of §3. This is the slice O2 pre-approves: `check-merge-ready.py` will report HOLD for it. | Yes — a gate is removed | a PR with no store edit and no waiver passes the `ask store` step; K1–K3 each refuse their fixture; K7; `check-docs.py` green on the shortened `docs/dev-process.md` |
| S3 | **Delete the page.** Everything in §4.1 and the S3 rows of §4.2; the goal tree shows an ask's options (§2.4); `/dashboard` serves a small archive record. | Yes — a page is removed | K8; `check-page-links.py` and `regen-pages.py --self-test` green with four pages; `/dashboard` answers with the archive record, not a 404; K5 |

Order is forced: S3 before S1 empties NEEDS YOU silently (§1.2); S2 before S1 would rename a file the
generator loads by path while the goal tree still loads the generator.

Each slice opens as a draft PR at its start (the mutation sweep is partial locally), and S2 and S3 each
re-run the all-manifest anchor resolve after their deletions.

## 6. Amendments to earlier specs

Made as a dated note at the top of each, pointing here; the bodies are not rewritten.

| Spec | Superseded by O1 |
|---|---|
| `docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md` | R3 (dashboard as change log); the `/dashboard` row of the page-question table; the *Change* row of the key table; migration step 4's *Dashboard asks* bullet (asks stay in the store — NEEDS YOU keeps three sources: the store, the ledger, the backlog); step 5; step 6's "each change line links to its dashboard entry"; §8 choices 1 and 8 |
| `docs/superpowers/specs/2026-08-28-project-dashboard-design.md`, `2026-08-31-dashboard-ask-choices-design.md`, `2026-08-31-dashboard-collapsed-cards-design.md` | the page, the per-PR rule and the collapsed cards are retired; §6.2's grammar and the ask-choices rules stay in force |

## 7. Questions for the owner

| # | Question | Recommendation |
|---|---|---|
| ✍ Q1 | **What happens to the 21,611 lines of history?** Narrative entries are 495 of 591. | **A — leave the file whole and append-only; only the header changes.** Entry ids are positional (`YYYY-MM-DD/N` counts every entry of a day), so removing narrative renumbers the asks: a trial strip changed 66 of 96 kept ids and turned 0 open asks into 63. Keeping it costs nothing measurable — the whole store parses in 0.05 s. Alternatives: **B** move everything before the cutover to an archive file and start empty (safe today only because 0 asks are open; needs a new exemption path in five guards); **C** strip narrative and rewrite every id and reference (rewrites an append-only record); **D** as A, plus a full frozen render of the page (2.07 MB) |
| ✍ Q2 | **The `/dashboard` command.** After S2 it no longer records what changed; it writes an ask or an answer. | **Rename it `needs-you`** in S2, so the name says what it does. Alternative: keep the name `dashboard` |
| ✍ Q3 | **Nothing will answer "what changed, and why did it matter?" in plain words.** The goal tree lists what merged; the per-PR paragraph was the only plain-words account. | **Accept the loss** — it is what O1 buys, and the PR titles and descriptions remain. Alternative: the goal tree's change lines show each PR's first description sentence (new work, a separate backlog row) |

Decided here as mechanical, not asked: the store keeps its file name; the two open heads-ups
(`2026-08-31/5`, `2026-09-15/10`) are closed by one `[resolved: …]` entry in S2, since after S3 nothing
would display them; `[heads-up]` stays valid for old entries and is refused on new ones (K3); the old
page is archived as a small record page, the work-lines precedent, not a full render; the contrast
formula moves to `page_chrome.py`; `exemption_reason` moves to `check-review-recorded.py`.

## 8. What was measured, and what was inferred

| Claim | Status | How |
|---|---|---|
| 626 referencing files; the per-directory counts of §4.3 | MEASURED | `git grep -l` with §4's pattern at `b02f0a25` |
| 591 entries, 71 / 2 / 28 flagged, 0 open asks, 2 open heads-ups, 0 parse errors | MEASURED | the store's own `parse_entries`, `unresolved`, `unresolved_heads_up` over the live file |
| The three ask readers of §1.2, and that no other script calls `unresolved` | MEASURED | `git grep` for `unresolved`, `gen-dashboard`, `_sibling(`; each call site read |
| `exemption_reason` depends on no store grammar, only the fence rule | MEASURED | an AST walk of the gate file: it reaches `EMPH`, `FENCE`, `NO_ENTRY`, `_declaration_reason`, `_indented`, `fence_closes` |
| Parse cost 0.05 s; module import 0.04 s | MEASURED | one timed run, this machine |
| A full render is 2.07 MB | MEASURED | `gen-dashboard.py --fragment-only`, 2,068,653 bytes |
| The trial strip: 66 of 96 ids change, 63 asks reopen | MEASURED on a naive strip (kept entries re-joined in order); a careful rewrite would fix references, which is option C's cost, not a refutation |
| The exact edits inside the six guard scripts of §4.2's grouped row, and `check-theme-token-coverage.py`'s new reference palette | UNVERIFIED | their hits were listed, not each traced |
| The mutation counts after each slice | UNVERIFIED | depends on which entries anchor to moved lines; the plan computes it |
| That `check-merge-ready.py` reports HOLD for S2 | INFERRED | S2 removes failure-path lines and a gate invocation, which its loosening detector targets; not run |
| Marketplace declarations regenerate cleanly with four components gone | UNVERIFIED | `check-shipping-sets.py` not run against the changed tree |

## Out of scope

- The ✍ tag styling of an ask on the goal tree (backlog #623, retargeted).
- Moving asks into the ledger or the backlog (the earlier spec's plan; O1 keeps them in the store).
- Any change to the entry grammar.
- The other standing pages (`/goals`, `/features`, `/backlog-table`, `/goal-tree`).
