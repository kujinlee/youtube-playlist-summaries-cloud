# Retire the dashboard page and the per-PR entry rule; keep the asks as the goal tree's NEEDS YOU source

> **Anchor:** `status-visibility` — **ADR:** 0010
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** ✅ APPROVED by the owner 2026-11-24 18:46 on the walkthrough page (`docs/explainers/2026-11-24-brief-dashboard-retire-spec-walkthrough.html`: all six cards answered, the recommendations taken, CONFIRM = A). Review converged at round 7 (Codex). Next: the Phase 2 plan, which owes §3. History: Rounds 1–4 of review folded (r1 both halves, r2 Codex, r3 Claude, r4 Codex, all NOT CONVERGED;
`docs/reviews/coordinator/dashboard-retire-spec-r1-coordinator.md`, `…-r2-…`, `…-r3-…`, `…-r4-coordinator.md`); §7's three questions DECIDED by the owner.
⟳ **Phase 6 fold (2026-11-24):** rounds 2–4 THRASHED on how an answer identifies its ask, and the architecture review
(`docs/reviews/architecture-review-2026-11-24-ask-store.md`) removed the class instead of gating it: **one file per ask in
`docs/asks/`, the answer written into the same file; the old store frozen whole** (§2.3). r3's keys, K2, K3, K9, K10 and K11
are gone (`docs/reviews/coordinator/dashboard-retire-spec-r4-phase6-coordinator.md`). Round 6 (both halves, past the round cap) found two BLOCKERs, folded: K7 and K8 restored (the fold had dropped them) and
a conflict marker anywhere in an ask made a PROBLEM; its MAJOR and MINORs are carried into the plan (§3)
(`docs/reviews/coordinator/dashboard-retire-spec-r6-coordinator.md`). Owed next: the owner's approval walkthrough. Nothing here is built.

Goal thread: `dashboard-decisions` (`docs/goal-threads.md`). Why this anchor: the page being retired and the
goal tree that keeps its asks are both pages of `status-visibility`, and the two specs this one amends
(§1.2) are anchored there.

## In plain words

Today every pull request must add a dated paragraph to `docs/dashboard-entries.md`, and a page at
`/dashboard` renders those paragraphs. The owner decided to stop both. One part of that file is still
needed: the entries that ask the owner a question, and the later entries that record the answer. The
goal tree reads those to fill its NEEDS YOU list, and it must keep showing every ask.

From the cutover on, a new ask is its own small file in `docs/asks/`, and its answer is written into
that same file. Nothing has to point from an answer to its question, so an answer cannot close the
wrong one. The old file is kept whole and frozen: it holds no open ask today, and a check keeps it
from changing.

The catch this spec exists for: the code that reads asks today lives inside the two scripts being
retired. Deleting them as they stand would empty NEEDS YOU without any error. So the new reader comes
first, the old store is frozen and the rule removed second, and the page is deleted last.

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

⚠ **Loaders BY FILENAME, which a rename breaks even though they read no asks** (r1 Codex BLOCKER, Claude M5).
Each one loads a file by its path string, so `git mv` alone turns it into a FileNotFoundError at import:

| Loader | Where | Loads | Breaks at |
|---|---|---|---|
| the page's grammar import | `scripts/gen-dashboard.py:327` (`_gate_module`, `with_name("check-dashboard-entry.py")`) | the gate | S2's rename — and through it `brief-compose._contrast` (`scripts/brief-compose.py:609`), which lazily loads the generator, so `assert_em_in_every_palette` (`:1784`) fails on every brief page with the text-style switcher (measured in a scratch copy, Claude r1) |
| the goal tree and the compaction snapshot, after S1 | `scripts/goal-tree.py:1309`, `scripts/compaction-state.py:482` | the gate, for `read_asks` (S1 adds it there, §2.3) | S2's rename |
| the waiver parser | `scripts/check-review-recorded.py:678`, `scripts/check-merge-ready.py:653` | the gate | S2's rename |
| the explainer-delivery guard | `scripts/check-explainer-delivery.py:53` (`PAGE_SKILLS = ["explain-topic", "dashboard"]`) | `.agents/skills/dashboard/SKILL.md`, which must cite `shared/explainer-delivery.md` | S2's skill rewrite and rename |

S2 repoints every one of these in the same slice (§5).

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
| `docs/superpowers/specs/2026-09-06-referential-entry-gate-design.md` | why the parser lives in the gate: a `[resolved: …]` reference is a property of the whole store (backlog #82). Under §2.3 new asks carry no reference, so that reason holds only for the frozen file, which C1 reads once and L1 then holds by digest |
| backlog #85 | three fence scanners for one Markdown rule had drifted; unified in the gate. The fence rule must not be copied when code moves |
| backlog #389 (done, PR #434) | the precedent for retiring a page: the goal tree absorbed work-lines, and the history was archived as a small frozen record page (`docs/explainers/work-lines-archive.html`, 2,984 bytes), served through `RETIRED_FILES` (`scripts/explainer-serve.py:277`) |
| backlog #623 (open) | dashboard asks should carry ✍ DECISION tags, built in `gen-dashboard.py` — its target file is being deleted; retargeted in §5 |
| backlog #586 | per-PR edits to the shared store are why a docs-only PR selects most mutation manifests, and `scripts/batch-ci.py:82` measured the store touched by 73 PRs — the cost this retirement removes |

Searched and found nothing: no earlier spec, ADR or backlog row proposes deleting the page.

## 2. Design

⟳ **Phase 6 fold.** §2.1–§2.3 are rewritten to the architecture review's option (b)
(`docs/reviews/architecture-review-2026-11-24-ask-store.md` §3). The r3/r4 design — an ask KEY beside the
positional id, `ref`, `dup_key`, `unapplied`, the fail-safe duplicate read and the conditional positional resolve —
is deleted, not kept as an alternative. Why in one line: every r2–r4 finding was about a REFERENCE from an answer to
an ask inside one shared, ordered file (review §2), and (b) has neither the reference nor the shared file.

### 2.1 Concern → mechanism (after all slices)

| Concern | Mechanism | Evidence it is the only one |
|---|---|---|
| Where an ask lives | one file per ask, `docs/asks/YYYY-MM-DD-<slug>.md` (§2.3) | new directory; nothing else writes there (A1 refuses any other file shape) |
| How an answer names its ask | it does not: the answer is written INTO the ask's file, under `## Answer` | no reference exists to resolve, so K2, K3 and K11 have no subject (§3 *Deleted*) |
| An ask's identity | the file's stem | allocated by the tree: git cannot hold two distinct files at one path — two branches adding one path with DIFFERENT content conflict at merge (`AA`), while IDENTICAL additions coalesce into one file, which is one ask (both measured, review §3 (b); r6 Codex MINOR); no id, no key, no position |
| Which asks are open | a file with no `## Answer` heading outside a code fence | `read_asks` in `scripts/check-ask-store.py` (the renamed gate file), the ONE directory reader (§2.3) |
| The old asks | `docs/dashboard-entries.md`, kept whole and FROZEN — 0 open asks, held by C1 at the cutover and L1 after it (§2.3b) | no reader parses it after S2: a frozen file with zero open asks contributes a constant empty list |
| Showing the owner what waits on them | `scripts/goal-tree.py` NEEDS YOU | after S3 no other page lists asks |
| A PR-body waiver line | `exemption_reason`, STAYING in `scripts/check-ask-store.py`; `check-review-recorded.py` and `check-merge-ready.py` load it from there, as today | its one remaining marker is `NO-REVIEW:`. It does not move (r1 Claude M4): the gate file imports only the standard library, which is what lets merge-ready's fixtures copy that ONE file into a temp dir (`scripts/check-merge-ready.py:4171`–`:4185`); `check-review-recorded.py` resolves `ROOT` from `__file__` and would break them |
| One Markdown fence rule | `fence_closes` / `FENCE` in `check-ask-store.py`, beside `exemption_reason`; `read_asks` uses it for `## Answer` | backlog #85 — no copy |
| One decision grammar | `decisions` / `decision_errors` in `check-ask-store.py`, run over an ask file's body | today's `**Decide:**` grammar, unchanged; read, never re-parsed |
| One WCAG contrast formula | `page_chrome.py` | today `scripts/gen-dashboard.py:1431`, borrowed by `scripts/brief-compose.py:609` |

### 2.2 What already does this?

| New thing | Existing mechanism | Why it is not enough as it stands |
|---|---|---|
| `check-ask-store.py` | `scripts/check-dashboard-entry.py` | it is the same file, `git mv`'d in S2 so history and the grammar's mutations follow, and shrunk: it keeps the fence rule, `exemption_reason`, `decisions` / `decision_errors` and (until S3, for the page) `parse_entries`; it gains `read_asks`, A1, F1 and L1. `parse_entries`, the header grammar and the ask model (`unresolved`, `resolvers`, `cleared_ids`) leave with the page in S3 rather than moving anywhere |
| `read_asks` | `needs_from_dashboard` (`scripts/goal-tree.py:1305`), `pending_asks` (`scripts/compaction-state.py:473`) | both read the shared store through the generator; the new reader reads a directory, and both callers move to it |
| the archive record page | `RETIRED_FILES`, `scripts/explainer-serve.py:277` | nothing new: one more row in that table |

### 2.3 An ask file

```md
docs/asks/2026-11-25-archive-form.md

# Which archive form do we keep?
One plain sentence saying what is being asked.

**Decide:** which archive form to keep
- A small record page [recommended]
- A full frozen render

## Answer
The owner chose the record page. 2026-11-26.
```

| Rule | Text |
|---|---|
| Name | `^\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*\.md$` — the date the ask was written, then a specific lowercase-kebab slug. Lowercase only, so `Foo.md` beside `foo.md` (two files on Linux CI) cannot both be valid (review §3 (b), measured) |
| Question | the first line, `# <question>` |
| Decision | the `**Decide:**` block and `[recommended]`, exactly today's grammar (`scripts/check-dashboard-entry.py:25`, `:347`–`:349`), read by `decisions()` |
| Open / answered | OPEN while the file has no `## Answer` line outside a code fence (the one fence rule); ANSWERED once it has one. A `## Answer` inside a fence leaves it OPEN (review §3 (b), measured) |
| Answered asks | stay in the directory as the record; nothing deletes them. F1 lets an ask only grow |
| Identity | the file stem. The goal tree's NEEDS YOU item `ref` is the stem, so its diff between runs (`(source, ref)`, `scripts/goal-tree.py:1165`) is stable |

**`read_asks(dir) -> (asks, problems)`** — one function, in `check-ask-store.py`. It lists `docs/asks/` and returns
each OPEN ask (stem, question, body) plus a PROBLEM for anything it cannot read as an ask. A problem makes the source
NOT READ — never "nothing waits on you" (K5) — while the readable asks are still returned, as the goal tree does for
the store today (`scripts/goal-tree.py:1317`). PROBLEM cases, each a plan case (review §3 *What can still go wrong*):
a missing directory; a file whose name fails the rule; an empty file or one with no `# ` first line; a
non-regular entry (symlink, FIFO, subdirectory); a file over the per-file cap; a file holding a git conflict marker ANYWHERE — a line beginning `<<<<<<<` or
`>>>>>>>`, inside a code fence or not (r6 Codex BLOCKER: a conflict after a valid `# ` first line, with `## Answer` in a
side, otherwise reads as ANSWERED and drops from NEEDS YOU, and F1 passes it because the base text survives as a
prefix — measured by Codex on a scratch shape). Git writes both markers in every conflict hunk, so `=======`, a legal
setext underline, is not needed to detect one.

**Bounded per-file read** (review §3, compaction-state's FIFO history): `read_asks` opens each entry the way
`_open_regular` does today (`scripts/compaction-state.py:343`) — `O_NONBLOCK`, `fstat` on the descriptor, regular
file only, at most `MAX_ASK_BYTES` (64 KiB) — and lists at most `MAX_ASKS` (1,000) entries; over that is a PROBLEM,
not a truncation. So the whole read is bounded by count × cap, and a FIFO in `docs/asks/` is refused without
blocking. `compaction-state.pending_asks` calls `read_asks` and keeps its CANNOT RUN line for any problem; it no
longer opens the store itself, so `MAX_STORE` (`scripts/compaction-state.py:143`) and its FIFO case move to a FIFO
ASK FILE case. "Newest" for the snapshot's `RECENT_ASKS` = the last stems in filename order (the date prefix).

### 2.3b The old store, frozen — and the cutover

`docs/dashboard-entries.md` keeps its name, its place and every byte of its 591 entries (§7 Q1 A; five guards
exempt it by path: `scripts/check-canonical-source.py:248`, `scripts/check-reference-namespace.py:61`,
`scripts/batch-ci.py:99`, `scripts/compaction-state.py:476`, `scripts/goal-tree.py:127`). Its header lines 3–6 are
rewritten once, in S2, to say it is a frozen record and new asks live in `docs/asks/`. After that it is never
written again, and no reader parses it: its two open heads-ups (`2026-08-31/5`, `2026-09-15/10`) stay open in a
file nothing displays — the spec's own reason for closing them ("after S3 nothing would display them") holds without
writing an entry.

**The cutover rule — master appends to the old store until S2 merges, and nothing is lost either side of it.**

| When | Where a new ask goes | What reads it | What makes a mistake loud |
|---|---|---|---|
| before S1 merges | the old store (today's rule) | the goal tree, through the generator | today's gates |
| S1 merged, S2 not | EITHER: the old store (the per-PR rule still owes an entry) or a file in `docs/asks/` | the goal tree reads BOTH sources (S1) | A1 / F1 on the new files; today's gates on the old store |
| S2's own merge | — | S2 drops the old-store reader | **C1**: S2's CI runs `gen-dashboard.py --assert-no-open-asks` — the real `unresolved(parse_entries(store))` over the store at HEAD — GitHub's merge ref, master + S2 — and FAILS if it is not empty. An ask still open there is re-asked as a file (and answered in the old store) before S2 can merge |
| after S2 | `docs/asks/` only | the goal tree reads `docs/asks/` only | **L1**: any change to `docs/dashboard-entries.md` makes the `ask store` step FAIL on that PR — whatever workflow the branch was cut under, since a pull request's CI runs the merge commit's workflow **[D]** |
| the residual race: a PR whose last CI ran BEFORE S2 merged (old workflow, green, no re-run) adds an entry and merges after S2 | its entry lands in the frozen file | nothing — so it must not stay silent | **L1 on master**: master's own next CI run, and every later PR's, FAILS on the digest. L1's message prints the bytes that differ from the pinned file and the restore command (`git checkout <S2 merge commit> -- docs/dashboard-entries.md`); the repair PR restores the file and re-asks any question in the stray entry as an ask file. Loud on every PR until repaired — never a quiet loss. ⚠ r6 Claude M1: this window is the normal case, not a residual one, and the repair cannot be built from a digest alone — carried, with its fix, in §3 *Carried into the plan* |

**The pin.** L1 compares the store's SHA-256 with `LEGACY_STORE_SHA256`, a constant in `check-ask-store.py`, written
ONCE in S2 after S2's header edit and after S2 last merges master in. It is never re-pinned: the repair for a
mismatch is to RESTORE the pinned bytes, not to accept new ones, so after S3 deletes the parser nothing needs it.
⚠ The pin's value cannot be stated here: `origin/master` has moved since the review measured 1,721,850 bytes at
`f63709f3` (592 entries at `89fc5eeb`, still 0 open asks — measured in this fold), and the per-PR rule keeps adding
entries until S2. **"Zero open asks" is a cutover precondition (C1), not a standing fact.**

### 2.3c The staleness watch and the document guards (review W2, W3)

**`/_stale` must see a new or answered ask file.** `PAGE_SOURCES` (`scripts/explainer-serve.py:243`) takes FILES
only: `/_stale` takes the newest `st_mtime_ns` over `(REPO / s).is_file()` sources (`:2070`), and the coverage case
"every declared source is a real file" (`:3197`) refuses a directory. Watching the directory's own mtime is NOT
enough — MEASURED in this fold on this machine: creating a file and an atomic replace each change the directory's
mtime, an in-place append (how `## Answer` is usually added) does not. **Decision:** S1 makes `PAGE_SOURCES` accept a
DIRECTORY entry whose staleness time is the max `st_mtime_ns` over the directory itself and its `*.md` children
(one level, no recursion); `PAGE_SOURCES["goal-tree"]` gains `docs/asks`; the coverage case becomes "every declared
source is a real file, or a directory named in `DIR_SOURCES`" with a case that a directory NOT in that set is still
refused (so the r1 lesson recorded at `:247`–`:250` keeps its teeth); and the `/_stale` reply names the child that
moved. Cases: an added ask file, an appended `## Answer`, and an untouched directory (fresh). `regen-pages.pages_for`
(`scripts/regen-pages.py:594`) gains: an edit whose `file_path` is under `docs/asks/` rebuilds `goal-tree`, as an edit
of the threads file does today. (This replaces the r1 plan to add `docs/dashboard-entries.md` to `PAGE_SOURCES` — the
frozen file never changes.)

**Document guards over an ask file — MEASURED in this fold** (a scratch clone at `0c0a3368`, two sample ask files
committed in `docs/asks/`, one open with a `**Decide:**` block and one answered; every non-self-test `check-*` step
that reads `docs/` from `.github/workflows/ci.yml`, run with and without the commit): all 24 return the same rc
with and without the files (22 rc 0; `check-decision-scheme.py` rc 1 and `check-inventory.py` rc 3 on both, a
pre-existing state of the tree, not the asks); none names `docs/asks/`. A SECOND sample with defects planted —
a bare `#623`, a citation of line 999,999 of `scripts/goal-tree.py`, a missing script path:

| Guard | Sees `docs/asks/`? | Consequence |
|---|---|---|
| `check-doc-citations.py --base` | YES — refused the out-of-range line | no exemption needed; an ask's citation is checked like any doc's |
| `check-reference-namespace.py --base` | **NO** — the bare `#623` passed. Its `SCOPE` is an allow-list of reader-facing surfaces (`scripts/check-reference-namespace.py:111`) | **S1 adds `docs/asks/` to `SCOPE`**, with a case: an added bare `#N` in an ask file is refused. An ask is the most owner-facing text in the repository; the old store was exempt only as a dated record (`:61`), and that reason does not carry over to a live question |
| `check-plan-leak.py --base` | CANNOT RUN here — no plan text in the scratch clone; NOT RUN, not a pass | the pre-push hook compares every added line, whatever its path; no path filter to extend (rerun in the plan's own push) |
| the other 22 | no finding on the two clean samples; the planted defects went through the two guards above only | no path exemption is added — the review's W3 rule: add one only where a guard fires |

The three guards that exempt the OLD store by path (`check-canonical-source.py:248`,
`check-reference-namespace.py:61`, `batch-ci.py:99`) keep that exemption for the frozen file; none of them fired on
`docs/asks/`, so none gains one.

### 2.4 What the owner sees for an ask after the page is gone

Today the goal tree shows an ask's title (cut to 160 characters) linked to `/dashboard#<slug>`
(`scripts/goal-tree.py:1314`); the question and its options are readable only on the dashboard page.
Deleting the page would leave a title and a dead link.

So from S1, a NEEDS YOU item read from `docs/asks/` shows, under the question, its options as a plain list —
read by the gate's own `decisions()` over the file's body, never re-parsed — and it has no page link (its
`ref` is the file stem). The old store's items keep their `/dashboard` link until S2 drops that reader. The
yellow ✍ tag styling stays backlog #623's work, now aimed at `scripts/goal-tree.py`.

**A malformed ask stays visible, with its diagnosis** (r1 Codex MAJOR). The store gate deliberately does
not run `decision_errors` (backlog #81, held by the owner 2026-09-01; `scripts/check-dashboard-entry.py:795`),
so today only the page shows that an open ask has no usable decision (`scripts/gen-dashboard.py:944`). After
S1 the goal tree does the same: for each open ask file it calls the gate's `decision_errors` on the body, and a
non-empty result is printed under the title as a warning line — the ask is KEPT in NEEDS YOU, never dropped.
Cases: a valid open ask (question and options shown, no warning); an ask file with no `**Decide:**`
block (question and warning); a block with malformed choices (warning names the error). This is also A1's
stated bound: A1 does not refuse a decision-less ask, by the owner's #81 ruling.

## 3. Gates removed and kept

### Removed

| Gate | Where | Why it can go |
|---|---|---|
| R1 "a branch that changes tracked files adds an entry or declares `NO-ENTRY:`" | `verdict`, `scripts/check-dashboard-entry.py:813`; CI step `dashboard entry ratchet`, `.github/workflows/ci.yml:1106`; replayed by `scripts/check-merge-ready.py:2198` | O1 |
| R2 `gen-dashboard.py --self-test` | `.github/workflows/ci.yml:984` | its subject is deleted |
| R3 the dashboard rows of the page-link, theme-token and contrast checks | `scripts/check-page-links.py:82`, `:91`, `:253`; `scripts/check-theme-token-coverage.py:70` | their subject is deleted |
| R4 the two-marker branches of the escape diagnosis ONLY — MISDIRECTED and "the other marker is in the body but inert" | `escape_diagnosis`, `scripts/check-merge-ready.py:2063`; its `other` branches at `:2087`–`:2103` | they compare two markers, and one is left. ⚠ **The diagnosis itself stays** (r1 Claude M3): INVISIBLE (the exact token is in the body but fenced, indented or backticked — the actual 2026-09-26 incident) and MISSPELLED (`ESCAPE_LOOKALIKE`, `:535`) work with one marker. `GATE_ESCAPE` (`:530`) becomes `{"review recorded": "NO-REVIEW:"}`; `ESCAPE_LOOKALIKE` narrows to `no-review`; the INVISIBLE and MISSPELLED fixtures stay, the MISDIRECTED ones go |

### Kept and added — each with its falsifier

| # | Gate | FAILS IF: |
|---|---|---|
| A1 | **new** (replaces K1) — every file in `docs/asks/` is a readable ask | any entry of `docs/asks/` at HEAD is a PROBLEM to `read_asks` (§2.3): its name fails the name rule (the one exempt name is `.gitkeep`), it has no `# <question>` first line, it is empty, not a regular file, or over `MAX_ASK_BYTES`. Reads HEAD's tree only — no base, no history — so CI's merge ref is its right subject. A conflict marker on ANY line fails it, not only the first (r6 Codex BLOCKER; §2.3) Not refused, by the owner's #81 ruling (§2.4): an ask with no usable `**Decide:**` block — it is shown with its warning instead. Cases: each refused shape; a valid open ask; a valid answered ask; a `## Answer` inside a fence (valid, OPEN); a valid `# ` first line followed by two conflicting `## Answer` sides between `<<<<<<<` and `>>>>>>>` — a PROBLEM, A1 red, and the goal tree reports the source NOT READ (K5), never the ask answered |
| F1 | **new**, optional — an existing ask only grows | for a file in `docs/asks/` present at the merge base, the base text is not a prefix of HEAD's text, or the file is gone at HEAD. MEASURED by the review on six cases (§3 (b)): gaining an answer and appending a superseding note pass; an edited question, a rewritten answer and a deletion are refused. It also refuses an `AA` conflict resolved by taking one side, since the other side's file was on master **[I]**. ⛔ **Pre-committed retreat:** F1 protects the RECORD of one ask and no other ask, because no ask depends on another file. If a review round finds a fix-induced defect in F1, F1 is DELETED and an ask's text becomes editable (git history keeps the original) — it is not patched. It must not become the next K9 |
| L1 | **new** — the old store is frozen | the SHA-256 of `docs/dashboard-entries.md` at HEAD differs from `LEGACY_STORE_SHA256` (§2.3b), or the file is missing. Mutated by "append one entry" and "edit one byte of an old entry" — each must go red; a case that the message prints the differing text (so a stray ask is visible) and the restore command |
| C1 | **new, S2 only** — the cutover leaves no ask behind | `unresolved(parse_entries(store))` over the store at S2's HEAD is not empty (`gen-dashboard.py --assert-no-open-asks`, run in the `ask store` step from S2 until S3 deletes the generator; after S3, L1 holds the bytes C1 passed on). Fixture: a store with one open ask — refused, naming its id |
| K4 | the goal tree reads the asks through the one reader | `needs_from_asks` returns no item for a fixture `docs/asks/` holding one open ask; or its call to `read_asks` is severed and the goal tree's self-test stays green. In S1 the same holds for the old store's reader, which the goal tree still calls until S2 |
| K5 | an unreadable source is never an empty NEEDS YOU | `docs/asks/` is missing or holds a PROBLEM entry (§2.3) and the goal tree prints "nothing waits on you" (today: `scripts/goal-tree.py:1317` reports the store NOT READ; the new source keeps that behaviour) |
| K6 | the compaction snapshot reports the open-ask count | `pending_asks` returns a count other than the fixture's, or returns 0 when `read_asks` cannot be loaded or reports a PROBLEM (today it returns CANNOT RUN, `scripts/compaction-state.py:485`); or a FIFO ask file blocks it past its time bound |
| K7 | `NO-REVIEW:` is still parsed by one definition | `check-review-recorded.py --self-test` or `check-merge-ready.py --self-test` goes green with `exemption_reason` replaced by a stub; or a fenced `NO-REVIEW:` line is granted |
| K8 | nothing still EXECUTES or LINKS a retired thing | any of these, anywhere in the tree, names a retired path (`gen-dashboard.py`, `check-dashboard-entry.py` — retired by S2's rename to `check-ask-store.py`, `regen-dashboard.sh`, the `dashboard` skill — renamed `needs-you` in S2) or the `/dashboard` route: a file load (`with_name(…)`, `_sibling(…)`, `_load(…)`, `spec_from_file_location(…)`, a `ROOT / "scripts" / …` path literal); a hook `command` in `.claude/settings.json`; a `run:` line in `.github/workflows/*.yml`; a `"scripts/<retired>.py"` string literal inside a list or tuple that is an argv — passed to `subprocess.*` or held in a command table such as `check-merge-ready.py`'s gate list (r3 Claude m2; live case `scripts/check-merge-ready.py:2198`, `["python3", "scripts/check-dashboard-entry.py", …]`, which S2 repoints by name and K8 then guards); a `"file"` field in `scripts/mutations/*.json`; a key of `REGENERABLE`, `PAGES` or `PAGE_SOURCES`; a `key_link("dashboard", …)` call or an `href` to `/dashboard` emitted by a page generator. **Bound on the href category** (r3 Claude m2): K8 is a static scan and sees a LITERAL `/dashboard` (or `/dashboard#`) string in a generator; it does not see an href assembled at run time (`f"/{name}"`). The one builder that assembles page links by name, `key_link`, is covered by its own category; any other runtime-built link to the route lands on the archive record page S3 serves at `/dashboard`, not a 404. The ONE allowed `/dashboard` hit is its `RETIRED_FILES` row (`scripts/explainer-serve.py:277`). ⚠ **Not a name grep** (r1 Claude M2, Codex MINOR): the bare-name pattern hit 74 files outside the frozen directories, most of them history the spec keeps, so a grep would fail on day one or grow an exemption list that checks nothing. Prose and comments that mention a retired name are history and are not in K8's scope — K8 has no exemption list to grow. **Proof the scan sees what it claims** (r2 Codex MINOR): its `--self-test` seeds, in a scratch tree, one retired reference per covered category above, the argv category seeded from `check-merge-ready.py:2198`'s shape — each must FAIL the scan, each case named for its category — and two that must PASS: a prose/comment mention of `gen-dashboard.py` in a script and a dated doc, and the permitted `RETIRED_FILES` row. A scan that finds nothing fails the seeded cases |

⚠ **No live source can prove K4 or K6.** The old store holds 0 open asks and `docs/asks/` holds none yet, so "the
same answer before and after" is 0 = 0 whether or not the reader works. Both are proven on a fixture with open
asks, and by a mutation that severs the call.

A1, F1 and L1 (and C1 from S2 until S3) run in CI on pull requests as one step, `ask store`, calling
`python3 scripts/check-ask-store.py --base "origin/$GITHUB_BASE_REF"`; it takes no PR body. Only F1 uses the base.
Its `--self-test` runs unconditionally, as today's does at `.github/workflows/ci.yml:987`. The checkout's
`fetch-depth: 0` stays — F1 diffs against the merge base; no kept check walks history — and the comment at `ci.yml:73`
that justifies it is reworded to name the ask-store step, not deleted. Today's step is PR-only (`if: github.event_name == 'pull_request'`, `ci.yml:1107`); S2 adds a
second invocation WITHOUT `--base` on push events, running A1 and L1 only, so the §2.3b race is caught on master itself.

### Deleted by the Phase 6 fold — no subject under §2.3

| Check / mechanism | Was | Why it has no subject |
|---|---|---|
| K1 (as an entry check) | an ADDED store entry parses | the store takes no entries after S2 (L1); A1 is its replacement over ask files |
| K2 | an added `[resolved: …]` resolves, to an earlier entry | there are no references |
| K3 | the store takes asks and answers only; a resolve targets an ask | the directory holds ask files only (A1); an answer cannot exist apart from its ask |
| K9 | the store is append-only over entries — the `rstrip` rule, the unclosed-fence diagnosis | no shared file is appended to; a fence left open in one ask cannot swallow another ask. L1 freezes the old file outright |
| K10 | (withdrawn in r3) the history walk | — |
| K11 | an ask is named by its key — all four clauses | the path is the key; git cannot hold two distinct files at one path — differing additions conflict (`AA`, measured in both orders), identical ones coalesce into one ask (review §3 (b)) |
| the key grammar | `[needs-you: <key>]`, `KEY`, `key` / `ref` beside `id`, `dup_key`, `unapplied`, the fail-safe duplicate read, the positional resolve permitted for a duplicated key | no two distinct asks can share a path, and no answer names anything |
| the S2 closing entry | `[resolved: 2026-08-31/5] [resolved: 2026-09-15/10]` | the old store is not written again (§2.3b) |
| the skill's "one id per bracket" trap | `[resolved: a, b]` parses as one id | no brackets |

### Carried into the plan (round cap, r6)

Round 6 is past the round cap (`docs/review-method.md` §0 Q4c), so these findings do not change the mechanism here.
Each is carried with its proposed fix, and **the plan must address every row** — build the fix, or refute it with
a measurement — before S1 or S2 (as the row says) is built. Source: `docs/reviews/claude/dashboard-retire-spec-r6-claude.md`.

| Finding | What is wrong | Proposed fix the plan must address | Slice |
|---|---|---|---|
| r6 Claude M1 — L1's cutover window is the normal case | every PR open when S2 merges carries an entry (R1) and green pre-S2 CI, so each one that merges after S2 turns master red; the pin can be stale at S2's own squash, because a PR merged between S2's last master-merge and its squash adds an entry C1 never saw; a SHA-256 alone cannot print the differing bytes, and `git checkout <S2 merge commit>` cannot be hardcoded and restores the wrong bytes in the stale-pin case | (1) pin the git BLOB id as well — `LEGACY_STORE_BLOB`, `git hash-object` of the frozen bytes, written once in S2 — so L1 prints `git diff <BLOB> <HEAD's blob>` and the restore command `git cat-file blob <BLOB> > docs/dashboard-entries.md`, correct whatever commit S2 lands as; (2) S2's merge step checks master's store is unchanged since the pin (`git diff <pin-base> origin/master -- docs/dashboard-entries.md` empty), else re-merge master and re-pin; (3) a post-merge cutover step merges master into every PR still open, so its CI re-runs under L1 and it drops its entry. §2.3b's "residual race" row is restated accordingly | S2 |
| r6 Claude m1 — `.gitkeep` and F1 | F1 covers every file present at the base, so deleting `.gitkeep` when the first ask lands is refused; an empty base is a prefix of anything, so `.gitkeep` can grow text A1 never reads | F1 applies only to files matching the name rule; A1 requires `.gitkeep` to be empty | S1 |
| r6 Claude m2 — the `## Answer` match is not exact | trailing text (`## Answer — A`), leading space and a four-space indented block are unspecified; a loose match closes an ask silently | the rule is `line.rstrip() == "## Answer"` at column 0, outside a fence; cases `## Answer — A` (stays OPEN) and `    ## Answer` (stays OPEN); the skill teaches the exact line | S1 |
| r6 Claude m3 — A1 "HEAD's tree" vs `read_asks(dir)` | `read_asks` lists the filesystem; locally an untracked scratch file fails A1 and an uncommitted deletion passes it | either A1 is stated to read the working tree, or A1 lists `git ls-tree HEAD docs/asks/` and passes `read_asks` those names; the plan picks one and states it in A1's row | S1 |

### Doc rules that say "every PR adds an entry"

| Where | Change |
|---|---|
| `docs/dev-process.md:162`–`:163` | two rows become one: `scripts/check-ask-store.py` — *every file in `docs/asks/` is a readable ask that only grows, and the old store stays frozen*. Net −1 line, inside the budget `scripts/check-docs.py` enforces |
| `docs/process-checklists.md:1162`–`:1163` | the same two full rows become one |
| `docs/process-checklists.md:400` | the committed-diff list names `check-ask-store.py` |
| `docs/process-checklists.md:557`, `:678` | reworded only if they say an entry is still ADDED to the store — it is a frozen dated record after S2 (L1) |
| `docs/CLAUDE.md:24` | rule 3 names `check-ask-store.py`; the committed-diff warning still holds |
| `docs/portable-practices.md:16` | drop `regen-dashboard.sh` from the hook list; `:13` and `:1410` are dated measurements and stay |
| `.agents/skills/dashboard/SKILL.md` → `.agents/skills/needs-you/SKILL.md` (§7 Q2, decided) | rewritten: how to write an ask and how to record its answer; no "record what changed", no page. It teaches §2.3: a new ask is a new file `docs/asks/YYYY-MM-DD-<slug>.md` (a specific lowercase-kebab slug, `# <question>` first, then the `**Decide:**` block); its answer is a `## Answer` section appended to that same file; an ask is never edited or deleted (F1), and `docs/dashboard-entries.md` is never written (L1). `.claude/skills/dashboard` (the symlink) is renamed with it; `scripts/check-explainer-delivery.py:53` drops `"dashboard"` from `PAGE_SKILLS`, since the skill no longer composes a page |
| `docs/memory/nothing-needs-you-must-read-the-dashboard.md` and its `MEMORY.md` row | the rule becomes "read the goal tree's NEEDS YOU count" — the command it names (`regen-pages.py --page dashboard`) stops existing |
| `docs/memory/parallel-branches-append-to-one-log.md` | the store leaves its list of files every branch appends to |
| `docs/memory/merge-ready-slice-merged-324.md:21`, `docs/memory/push-is-mine-merging-is-theirs.md:34` | the `NO-ENTRY` mentions are removed |
| `docs/roadmap-to-launch.md` | history rows stay; one new row records the retirement and this spec |

## 4. Inventory — every hit, classified

Source: `git grep -l -E 'dashboard-entr|gen-dashboard|check-dashboard-entry|regen-dashboard'` at
`b02f0a25` — **626 files** (627 once this spec exists; the count moves with every document that names the
store, so the frozen set below is stated as globs, not counts — r1 Claude m1).

### 4.1 Delete

| File | Slice |
|---|---|
| `scripts/gen-dashboard.py` | S3 |
| `scripts/mutations/gen-dashboard.json` | S3 (the `contrast_ratio` entries move to `page_chrome`'s manifest, §4.2) |
| `.claude/hooks/regen-dashboard.sh` and its registration at `.claude/settings.json:158` | S3 |
| `.claude/skills/dashboard` (a symlink to `.agents/skills/dashboard`) | renamed to `needs-you` with the skill in S2 (§7 Q2, decided) |

### 4.2 Rename or edit

| File | Change | Slice |
|---|---|---|
| `scripts/check-dashboard-entry.py` → `scripts/check-ask-store.py` | gains `read_asks`, `MAX_ASK_BYTES` / `MAX_ASKS`, A1 and F1 in S1 (§2.3, §3); in S2 `git mv`, gains L1, `LEGACY_STORE_SHA256` and C1's call, loses `verdict`'s owed-entry branch, `NO_ENTRY`, `EXEMPT_*`, `_is_exempt` and the entry checks K1 / K2 / K3 (§3 *Deleted*); KEEPS `exemption_reason`, `_declaration_reason`, the fence rule and `decisions` / `decision_errors`, its default marker becoming `NO-REVIEW:` (§2.1, r1 Claude M4); in S3 loses `parse_entries` and the header grammar with the page | S1, S2, S3 |
| `scripts/mutations/check-dashboard-entry.json` → `check-ask-store.json` | follows the file; R1's entries are deleted, never left unbound | S2 |
| `scripts/goal-tree.py` | S1: a `needs_from_asks` reader over `docs/asks/` beside `needs_from_dashboard`; the source loop at `:1563` reads a DIRECTORY for it (today it reads files by `(key, rel, fn)`); item `ref` is the stem; options and the decision warning shown (§2.4); K5 for the new source. S2: `needs_from_dashboard` and its `dashboard` source removed, `DASHBOARD_REL` (`:127`) with it; `:42` docstring; cases at `:5349`, `:5653` | S1, S2 |
| `scripts/compaction-state.py` | S1: `pending_asks` counts both sources — `read_asks` (bounded per file, §2.3) and the old store as today; S2: the old store's read, its `MAX_STORE` cap and FIFO case go, replaced by a FIFO-ask-file case; `:41`, `:474` wording; case at `:2084` | S1, S2 |
| `scripts/check-review-recorded.py` | `:678` `_load_declaration_parser` repointed to `check-ask-store.py`; nothing moves into it | S2 |
| `scripts/gen-dashboard.py` | `:327` `_gate_module` repointed to `check-ask-store.py` in the SAME slice as the rename (r1 Codex BLOCKER); its `--self-test` stays green through S2, and with it `brief-compose.py`'s lazy load (`:609`) | S2 (deleted S3) |
| `scripts/check-merge-ready.py` | `:653` `DASHBOARD_GATE` renamed and pointed at `check-ask-store.py`; `:2198` replays `ask store`; `escape_diagnosis`'s two-marker branches removed, the rest kept (R4); fixtures at `:2353`, `:4171`–`:4280` keep copying ONE stdlib-only file, renamed — `_real_cde` reads `check-ask-store.py` and writes it under that name | S2 |
| `.github/workflows/ci.yml` | `:984`–`:985` removed (S3); `:987`–`:988` and `:1106`–`:1113` renamed, the PR body dropped (S2); comments at `:73` (fetch-depth, reworded — §3), `:968` (check-page-links builds three CI pages, not four — r1 Claude m3), `:1064`, `:1120` | S2, S3 |
| `scripts/brief-compose.py` | `:609` `_contrast` takes `contrast_ratio` from `page_chrome.py`; the comment at `:439` naming `gen-dashboard.CONTRAST_MIN` is repointed | S3 |
| `scripts/page_chrome.py` | gains `contrast_ratio` / `_luminance` (moved, with their mutations) | S3 |
| `scripts/page_markup.py` | `key_link` loses the `dashboard` kind (`:206`), cases `:990`, `:999` | S3 |
| `scripts/check-page-links.py` | `:82`, `:91`, `:99`, `:104`, `:253`–`:255` lose the dashboard | S3 |
| `scripts/check-theme-token-coverage.py` | `:70` `PAGE_SRC` needs another generator's palette as its reference — which one is a plan decision, UNVERIFIED here | S3 |
| `scripts/explainer-serve.py` | S1: `PAGE_SOURCES` accepts a declared directory (`DIR_SOURCES`), `PAGE_SOURCES["goal-tree"]` gains `docs/asks`, `/_stale` takes the max mtime over the directory and its `*.md` children, the `:3197` coverage case admits declared directories only (§2.3c). S3: `:224`, `:244` removed; `RETIRED_FILES` (`:277`) gains `dashboard.html`; cases | S1, S3 |
| `scripts/regen-pages.py`, `scripts/regen-pages.sh`, `.claude/hooks/regen-pages.sh` | S1: `pages_for` (`scripts/regen-pages.py:594`) maps an edit under `docs/asks/` to `goal-tree` (§2.3c; replaces r1 Claude m2's mapping of the frozen store). S3: fixtures and comments naming the dashboard | S1, S3 |
| `scripts/mutations/expected_mutations.py`, `scripts/sweep-costs.json` | pins (`:267`, `:857`) and cost rows for the two scripts. The `contrast_ratio` / `CONTRAST_MIN` mutations (e.g. the `PROSE_CONTRAST_MIN` entry of `gen-dashboard.json`) MOVE to `page_chrome`'s manifest in S3 and are counted there; the plan states each slice's arithmetic from 70 / 44 (r1 Claude m7) | S1, S2, S3 |
| `scripts/check-fixture-variation.py` (`:263`, `:1270`, `:1440`), `scripts/check-main-drivable.py`, `scripts/check-plan-code.py`, `scripts/check-publishability.py`, `scripts/check-shipping-sets.py` (`:1812`), `scripts/check-ratchet-contract.py` | tables and live-tree cases that name either script; each is re-pointed or its row removed (including the case NAME at `scripts/check-plan-code.py:7860`, "check-dashboard-entry.py reaches compaction-state through gen-dashboard.py" — r1 Claude m3). `check-publishability.py:1902`'s `requires-skill dashboard` is a SYNTHETIC fixture world (`:1893`), not a load of the real skill, and stays. The exact edit per case is the plan's work — UNVERIFIED case by case here | S2, S3 |
| `docs/marketplace/components.json`, `shipping-sets.json`, `inventory.json` | four components leave (`skill-dashboard`, `gen-dashboard`, `check-dashboard-entry`, `hook-regen-dashboard`), one arrives; regenerated by their own tools, never hand-edited | S2, S3 |
| `docs/dashboard-entries.md` | header lines 3–6 only, then frozen by L1 (§2.3b) | S2 |
| `docs/asks/` (new) | created with a `.gitkeep`; the first ask file is written by whoever next asks | S1 |
| `scripts/check-reference-namespace.py` | `SCOPE` (`:111`) gains `docs/asks/`, with a case (§2.3c) | S1 |
| `.agents/skills/dashboard/SKILL.md`, the docs and memory rows of §3 | as §3 | S2 |
| `CONTEXT.md:154`, `docs/adr/0015-a-page-paraphrases-freely-and-cites-decision-symbols.md:67`, `.gitignore:160` | name the store or the generator in passing; reworded only where they would become false | S3 |
| `docs/backlog.md` | row 623 retargeted to `scripts/goal-tree.py`; one new row for this work | S1 |

### 4.3 Keep, untouched — the frozen set

| Glob | Count at `b02f0a25` (moves; not a bound) | Why |
|---|---|---|
| `docs/reviews/**` | 484 | frozen testimony |
| `docs/explainers/**` | 26 | pages as delivered on their day |
| `docs/superpowers/**` | 32 | earlier specs and plans; two are amended by a dated note (§6), none rewritten |
| `docs/marketplace/scan-*.json`, `docs/marketplace/experiment-tier-*` | 6 | dated measurements |
| `docs/memory/**`, except the rows §3 edits | — | records and rules; a mention of a retired name is history. Five non-dated rule files also name a script in passing (r1 Claude M2) and stay unless a sentence becomes FALSE |
| `docs/backlog.md`, `docs/roadmap-to-launch.md`, `docs/portable-practices.md`, `docs/round-header-template.md`, `docs/dashboard-entries.md` | — | history rows and dated measurements, except the lines §3 and §4.2 name |
| `scripts/fixtures/*.json` | 3 | recorded corpora; a fixture naming a deleted path is still the recording |
| `scripts/batch-ci.py`, `scripts/check-canonical-source.py`, `scripts/check-reference-namespace.py` | 3 | they name the STORE, which stays |
| comments and docstrings in `scripts/**` citing either script as history (`scripts/check-backlog-closure.py:82`, `scripts/peer-sites.py:481`, `scripts/gen-backlog-page.py:2771`, `scripts/codex-review.py:1933` and the like; 31 files in `scripts/` hit the bare name, mutations excluded — Claude r1) | — | a dated account; reworded only where it would become FALSE |

**This table is no longer K8's exemption list** (r1 Claude M2). K8 inspects executable loads and links only
(§3), so prose here is out of its scope by construction, and K8 needs no list that can grow.

## 5. Slices — independently mergeable, in this order

⟳ **Re-cut in the Phase 6 fold.** The old S1 (*move the ask model beside the grammar*) is DROPPED: under §2.3 the
ask model (`unresolved`, `resolvers`, `cleared_ids`) has no live reader after S2, so it leaves with the page in S3
instead of moving (review §5). The new S1 is the new store, additive.

| # | Slice | Changes behaviour? | What proves it worked |
|---|---|---|---|
| S1 | **Open the new store beside the old one.** `read_asks`, A1 and F1 added to `scripts/check-dashboard-entry.py` (no rename yet) and run by its existing PR step; `docs/asks/` created (an empty `.gitkeep` is NOT an ask — A1 exempts exactly that one name, with a case); the goal tree gains `needs_from_asks` and reads BOTH sources; `compaction-state.pending_asks` counts both; `explainer-serve.py` learns directory sources and `PAGE_SOURCES["goal-tree"]` gains `docs/asks`, `regen-pages.pages_for` maps `docs/asks/` edits to `goal-tree` (§2.3c); `check-reference-namespace.py`'s `SCOPE` gains `docs/asks/` (§2.3c). The per-PR rule and the page are untouched. | Yes, additively — a second NEEDS YOU source | K4 for both readers and K6 on fixtures with open asks; a mutation severing each call site goes red; A1's and F1's cases; K5 for a missing `docs/asks/` and a PROBLEM entry; the `/_stale` cases (added file, appended answer, untouched directory, a non-declared directory still refused); an added bare `#N` in an ask file refused; `gen-dashboard.py --self-test` unchanged |
| S2 | **Cut over: freeze the old store and remove the per-PR rule.** Merge master in LAST. C1 must pass on the merge ref; rewrite the store's header lines 3–6; write `LEGACY_STORE_SHA256` from the resulting bytes (§2.3b) and add L1. Drop the old-store readers from the goal tree (`needs_from_dashboard`, the `dashboard` source at `scripts/goal-tree.py:1563`) and from `compaction-state.pending_asks`. Rename to `check-ask-store.py` and, IN THE SAME SLICE, repoint every by-filename loader of §1.2 (`gen-dashboard.py:327`, `check-review-recorded.py:678`, `check-merge-ready.py:653`) and `check-explainer-delivery.py`'s `PAGE_SKILLS`; delete R1 and `NO-ENTRY:`; `exemption_reason` stays with `NO-REVIEW:` as its marker; narrow R4; rename the skill to `needs-you` (§3); the `ask store` CI step (PR with base, push without — §3); merge-ready; the doc rules of §3. This is the slice O2 pre-approves: `check-merge-ready.py` will report HOLD for it. | Yes — a gate is removed, a store frozen | C1 green on S2's merge ref and red on its open-ask fixture; L1's two mutations red and its message case; a PR with no store edit and no waiver passes the `ask store` step; a PR that edits `docs/dashboard-entries.md` fails it; K4–K7 (K4 now: the goal tree has NO dashboard source and an open-ask fixture in the OLD store contributes nothing); at the merge point `gen-dashboard.py --self-test`, `goal-tree.py --self-test`, `compaction-state.py --self-test`, `brief-compose.py --self-test` and `check-explainer-delivery.py` are green (r1 Codex BLOCKER); `check-docs.py` green on the shortened `docs/dev-process.md` |
| S3 | **Delete the page.** Everything in §4.1 and the S3 rows of §4.2, including `parse_entries`, the header grammar and the ask model leaving `check-ask-store.py` / the generator, and C1's CI line; the goal tree shows an ask's question and options (§2.4); `/dashboard` serves a small archive record. | Yes — a page is removed | K8, including its seeded cases — one refused reference per covered category, the prose mention and the `RETIRED_FILES` row passing; L1 still green (nothing in S3 touches the store); `check-page-links.py` and `regen-pages.py --self-test` green with the dashboard gone from both page sets — r1 Claude m3, two different "four"s: `REGENERABLE` (`scripts/explainer-serve.py:223`) holds five pages today and four after; `check-page-links.py --build --ci` builds four today (`ci.yml:968`: dashboard, goals, features, backlog table) and three after; `/dashboard` answers with the archive record, not a 404; K5; the §2.4 cases (valid ask, missing decision, malformed choices) |

**Order is forced, and the constraint is now one sentence** (review §5): the goal tree reads `docs/asks/` and C1
passes BEFORE the old reader and the page are deleted. S3 before S2 deletes the generator the goal tree still loads
for the old store (§1.2) — NEEDS YOU goes NOT READ, loudly, but the asks there would be unread; S2 before S1 would
drop the old store's reader while no other source exists, so an ask written in the old store on S2's day would be
dropped — C1 is what refuses that, and S1 is what lets an author write the ask somewhere C1 does not need to clear.

Each slice opens as a draft PR at its start (the mutation sweep is partial locally), and S2 and S3 each
re-run the all-manifest anchor resolve after their deletions.

## 6. Amendments to earlier specs

Made as a dated note at the top of each, pointing here; the bodies are not rewritten.

| Spec | Superseded by O1 |
|---|---|
| `docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md` | R3 (dashboard as change log); the `/dashboard` row of the page-question table; the *Change* row of the key table; migration step 4's *Dashboard asks* bullet (asks stay in the store — NEEDS YOU keeps three sources: the store, the ledger, the backlog); step 5; step 6's "each change line links to its dashboard entry"; §8 choices 1 and 8 |
| `docs/superpowers/specs/2026-08-28-project-dashboard-design.md`, `2026-08-31-dashboard-ask-choices-design.md`, `2026-08-31-dashboard-collapsed-cards-design.md` | the page, the per-PR rule and the collapsed cards are retired; §6.2's grammar and the ask-choices rules stay in force |

## 7. Questions for the owner — DECIDED

Decided by the owner, 2026-11-24 17:05–17:08, on selection cards. Each row keeps the recommendation it
was decided against.

| # | Question | Decision |
|---|---|---|
| Q1 | **What happens to the 21,611 lines of history?** Narrative entries are 495 of 591. | **DECIDED — A: keep `docs/dashboard-entries.md` whole; only the header changes.** Entry ids are positional (`YYYY-MM-DD/N` counts every entry of a day), so removing narrative renumbers the asks: a trial strip changed 66 of 96 kept ids and turned 0 open asks into 63. Keeping it costs nothing measurable — the whole store parses in 0.05 s. L1 freezes it by digest from S2 (§3). Not chosen: **B** archive file and start empty; **C** strip narrative and rewrite every id and reference; **D** as A plus a full frozen render (2.07 MB) |
| Q2 | **The `/dashboard` command.** After S2 it no longer records what changed; it writes an ask or an answer. | **DECIDED — A: rename the skill to `/needs-you`** in S2, so the name says what it does (§3, §4.1). Not chosen: keep the name `dashboard` |
| Q3 | **Nothing will answer "what changed, and why did it matter?" in plain words.** The goal tree lists what merged; the per-PR paragraph was the only plain-words account. | **DECIDED — A: accept the loss**; the PR titles and descriptions remain. The owner first asked whether the goal tree's readability suffers. Answer recorded: no — the goal tree reads only the ASKS from the store; its line text comes from `docs/goal-threads.md`. Not chosen: the goal tree's change lines show each PR's first description sentence (a separate backlog row) |

Decided here as mechanical, not asked: the store keeps its file name; the two open heads-ups
(`2026-08-31/5`, `2026-09-15/10`) stay open in the frozen file and are NOT closed — the old store is not written
again after S2's header edit (§2.3b), and after S2 nothing reads it, so nothing displays them; the old page is
archived as a small record page, the work-lines precedent, not a full render; the contrast formula moves to
`page_chrome.py`; `exemption_reason` STAYS in the renamed gate file (r1 Claude M4 — the earlier draft moved it to
`check-review-recorded.py`).

**A coordinator mechanism choice inside the owner's decisions (Phase 6 fold), not a new question:** new asks are
files in `docs/asks/` with the answer in the same file (§2.3), adopting option (b) of
`docs/reviews/architecture-review-2026-11-24-ask-store.md`. It replaces the r3/r4 ask-key design, which the round
cap stopped on THRASHING in one component (`docs/reviews/coordinator/dashboard-retire-spec-r4-coordinator.md`); the
fold is recorded in `docs/reviews/coordinator/dashboard-retire-spec-r4-phase6-coordinator.md`. No existing entry is
touched, so Q1 A (keep the file whole; header-only change) stands, and it serves O1 by making an answer unable to
close the wrong ask — it names none.

**To confirm in the approval walkthrough — not a blocking question:** the owner's recorded wording on the
selection card (11-24 09:57, option A) named `docs/dashboard-entries.md` — "KEEP the needs-you/resolved asks as the
goal tree's NEEDS YOU source". Under §2.3 the old file stays whole and read-only, holds every past ask and answer,
and new asks live in `docs/asks/`, which becomes the goal tree's NEEDS YOU source. The walkthrough confirms that
this still meets the decision's intent (the asks keep feeding NEEDS YOU), rather than its letter (that one file).
**CONFIRMED by the owner 2026-11-24 18:46** (walkthrough card CONFIRM, option A, via APPROVE).

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
| `added_reference_errors` accepts a forward reference, and `unresolved` then leaves the ask open | MEASURED | a two-entry fixture, run in r1 by Codex and again in the fold |
| `header_error` refuses `[needs-you] [heads-up]` but accepts `[heads-up] [resolved: …]` and `[needs-you] [resolved: …]` | MEASURED | `header_error` on each header, in the fold |
| A fenced `## Example` inside a body is not an entry to `parse_entries`; `## Not a date` outside a fence is an error entry | MEASURED | `parse_entries` on a fixture, in the fold |
| `[resolved: a, b]` is refused as one id; `[resolved: a] [resolved: b]` clears both | MEASURED | `parse_entries` on a fixture (Claude r1; the comma case re-run in the fold) |
| That the positional-shift hazard ever fired on master | NOT MEASURED | — |
| The mutation counts after each slice | UNVERIFIED | depends on which entries anchor to moved lines; the plan computes it |
| That `check-merge-ready.py` reports HOLD for S2 | INFERRED | S2 removes failure-path lines and a gate invocation, which its loosening detector targets; not run |
| Marketplace declarations regenerate cleanly with four components gone | UNVERIFIED | `check-shipping-sets.py` not run against the changed tree |
| The r2–r4 findings all concern a reference from an answer to an ask inside one shared, ordered file | MEASURED | the architecture review's §2, each finding traced to its round document |
| Under option (b): two branches adding one ask path conflict (`AA`) in both merge orders; identical content merges as one file; two different answers conflict (`UU`); an answer against a delete conflicts (`UD`); `Foo.md` beside `foo.md` are two files on a case-sensitive file system | MEASURED | the review's §3 (b), a scratch repository |
| F1's six cases: gaining an answer and appending a note pass; an edited question, a rewritten answer and a deletion are refused | MEASURED | the review's §3 (b), a prefix sketch, not the gate |
| `origin/master` at `89fc5eeb`: 592 entries, 0 parse errors, 0 open asks, 2 open heads-ups (`2026-08-31/5`, `2026-09-15/10`); one store commit since `f63709f3` | MEASURED | the real `parse_entries` / `unresolved` / `unresolved_heads_up`, this fold |
| The review's pin `d58f8056c7fea06a…` (1,721,850 bytes at `f63709f3`) is already stale | MEASURED | the store at `89fc5eeb` has one more entry; so the pin is written in S2, not here |
| Directory mtime on this machine: a created file and an atomic replace change it; an in-place append does not | MEASURED | `stat` before and after each, this fold |
| 24 document guards return the same rc with and without two sample ask files; none fires on them | MEASURED | a scratch clone at `0c0a3368`, each guard run on both trees (§2.3c) |
| `check-doc-citations.py` refuses an out-of-range citation in an ask file; `check-reference-namespace.py` passes a bare `#623` there | MEASURED | the same clone, a planted-defect commit (§2.3c) |
| `check-plan-leak.py` over an ask file | NOT RUN | no plan text in the scratch clone; CANNOT RUN is not a pass |
| That the goal tree's diff stays stable when `ref` is a file stem | INFERRED | `(source, ref)` at `scripts/goal-tree.py:1165`; the plan's case proves it |
| A conflict after a valid first line, with `## Answer` in a side, reads as ANSWERED to the §2.3 rule and passes F1's prefix test, before r6's fold | MEASURED | Codex r6, a scratch check of both predicates |
| F1 catching an `AA` resolved by taking one side | INFERRED | the other side's file is on master at the base; not run |

## Out of scope

- The ✍ tag styling of an ask on the goal tree (backlog #623, retargeted).
- Moving asks into the ledger or the backlog (the earlier spec's plan; O1 keeps them in the store).
- Any change to the grammar or bytes of EXISTING entries. New asks are files (§2.3), not entries.
- Closing the two open heads-ups in the frozen file — nothing reads it after S2 (§2.3b).
- The other standing pages (`/goals`, `/features`, `/backlog-table`, `/goal-tree`).
