# Retire the dashboard page and the per-PR entry rule — implementation plan (slices S1–S3)

> **Anchor:** `status-visibility` — **ADR:** 0010
> **Goal:** A person who was away can see the current state, what changed, and what needs them — without reading the chat transcript.

**Status:** 🟠 current — DRAFT plan, written 2026-11-24 from the approved spec
`docs/superpowers/specs/2026-11-24-dashboard-retire-design.md` (owner approved 2026-11-24 18:46, spec §7).
Phase 2: dual adversarial review to convergence or the round cap (`docs/review-method.md` §0 Q4c) before any
task is dispatched. Nothing is built.

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` — a NEW subagent per
> task, per fold and per review round. Steps use checkbox (`- [ ]`) syntax. Read the spec section each task
> names before writing code: the plan states decisions, the spec states reasons.

**Goal:** New asks live one file each in `docs/asks/`, the goal tree's NEEDS YOU reads them, the old store is
frozen, the per-PR entry rule is gone, and the `/dashboard` page is deleted.

**Architecture:** One directory reader, `read_asks`, lives in the gate file beside the fence rule and the
decision grammar it reuses; the goal tree and the compaction snapshot call it and nothing else lists
`docs/asks/`. The order is forced (spec §5): the new reader first (S1, additive), the freeze and the rule's
removal second (S2), the page's deletion last (S3). Each slice is one branch and one PR, mergeable alone.

**Tech stack:** Python 3.12, standard library only in the gate file (merge-ready's fixtures copy that ONE
file); each script's own `--self-test` with its `case(name, got, want)` helper; mutation manifests in
`scripts/mutations/*.json`, pinned in `scripts/mutations/expected_mutations.py`.

**Spec:** `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md`. Goal thread: `dashboard-decisions`.

## Global constraints

- **Name rule:** `^\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*\.md$`. The one exempt name is `.gitkeep`.
- **Caps:** `MAX_ASK_BYTES` = 64 KiB (65,536 bytes) per file; `MAX_ASKS` = 1,000 entries.
- **Answer rule (spec §3, r6 Claude m2):** a line `L` closes an ask only when `L.rstrip() == "## Answer"`
  and its index is not in `fenced_lines(text)`. Nothing looser.
- **One reader.** No script but the gate file lists `docs/asks/` or re-implements the fence rule, the
  answer rule or `decisions()`. A caller loads the gate and calls it.
- **The gate file imports the standard library only** at module level (`fixture_git` stays a lazy import
  inside the self-tests).
- **The old store's bytes are never edited** except S2's header lines 3–6, once.
- **A mutation is a two-file edit.** Every task that edits a manifested script edits its manifest and its
  pin in the same commit; an entry whose anchor is deleted is DELETED, never left unbound. After every
  task run *The anchor resolve* (below) over ALL manifests.
- **Cite symbols, never line numbers,** in code comments and commit messages. Line numbers in the spec were
  measured at `b02f0a25` and have moved.
- **Each slice opens as a DRAFT PR at its first commit** (the local mutation sweep is partial:
  `python3 scripts/check-plan-code.py --mutate . --only <script>`).
- **No single command over about 270 seconds.** Run the sweep one script at a time.
- **Back up to the scratchpad before any `rm` or `git rm`** of a file this plan deletes.
- **Commit explicit paths** with `git commit -F -`; never `git add -A`.

### The anchor resolve — run after every task, in every slice

The harness refuses an unbound anchor only when that script's sweep runs. This reads every manifest at once
and takes about a second (run on this plan's branch 2026-11-24: 107 manifests, 0 unbound).

```python
import json, sys
from pathlib import Path

bad = []
for man in sorted(Path("scripts/mutations").glob("*.json")):
    for m in json.loads(man.read_text(encoding="utf-8")):
        path = Path(m["file"])
        if not path.is_file():
            bad.append(f"{man.name}: {m['name'][:60]!r}: file {m['file']} is missing")
            continue
        src = path.read_text(encoding="utf-8")
        for before, _after in m["edits"]:
            n = src.count(before)
            if n != 1:
                bad.append(f"{man.name}: {m['name'][:60]!r}: anchor matches {n} times")
print("\n".join(bad) or "every anchor resolves exactly once")
sys.exit(1 if bad else 0)
```

**FAILS IF:** any manifest entry's `before` text occurs 0 or 2+ times in its `file`, or the file is gone.
It does not check `expect`; the per-script sweep does.

## Review focus

Five inputs the spec implies and no gate row names. Each has a case in the task that owns the code.

1. **A Finder or editor artefact in `docs/asks/`** (`.DS_Store`, `foo.md~`) on the owner's machine. Expected:
   the goal tree reports the asks source NOT READ naming the file, never a silent skip; A1 in CI is not
   affected because it reads HEAD's tree (Task 2, behaviors 2.9 and 2.10).
2. **An ask file that is not UTF-8.** Expected: a PROBLEM naming the file, not a traceback (Task 1, 1.13).
3. **A Windows-edited ask: `## Answer\r\n`.** Expected: ANSWERED — `rstrip()` removes the `\r` (Task 1, 1.9).
4. **The pinned blob is absent from the clone** (a shallow checkout) when L1 fails. Expected: still REFUSED,
   and the message says the diff could not be printed; never a pass (Task 12, 12.6).
5. **An ask with a question and nothing else** (no body, no trailing newline). Expected: OPEN, shown with
   the missing-decision warning (Task 1, 1.14; Task 3, 3.3).

## How the four carried findings are addressed (spec §3, *Carried into the plan*)

| Finding | Decision | Task | Test |
|---|---|---|---|
| r6 Claude **M1** — L1's cutover window is the normal case | BUILD all three parts. (1) `LEGACY_STORE_BLOB` beside `LEGACY_STORE_SHA256`; L1 prints `git diff <BLOB> <HEAD's blob>` and `git cat-file blob <BLOB> > docs/dashboard-entries.md`. (2) `LEGACY_STORE_BASE_BLOB` — master's store as S2 last merged it — and `check-ask-store.py --cutover-check origin/master`, run immediately before the squash. (3) a post-merge step merges master into every open PR whose diff still edits the store — narrowed ON PURPOSE from the spec's "every PR still open": a PR whose diff does not touch the store carries nothing L1 refuses, and squashing it cannot move the store, so no merge is owed to it (backlog #730 L4) | 12, 13 | 12.3–12.8; 13's listing command and its falsifier |
| r6 Claude **m1** — `.gitkeep` and F1 | BUILD. F1 considers only base names matching the name rule; a non-empty `.gitkeep` is a PROBLEM in `read_asks`, so A1 and the goal tree both refuse it | 1, 2 | 1.4; 2.5, 2.6 |
| r6 Claude **m2** — the `## Answer` match is not exact | BUILD. The Global-constraints rule, in one function `answered(text)`; the skill teaches the exact line | 1, 11 | 1.6–1.9; Task 11's grep |
| r6 Claude **m3** — A1 "HEAD's tree" vs `read_asks(dir)` | PICKED: **A1 lists `git ls-tree --name-only HEAD docs/asks/` and passes those names to `read_asks`.** File content is read from the working tree, which in CI equals HEAD. Stated in A1's docstring and `--help` | 2 | 2.9–2.11 |

Why the `git ls-tree` form and not "A1 reads the working tree": every other clause of the gate reads the
committed tree (`collect`), `docs/CLAUDE.md` rule 3 already teaches that, and an untracked scratch file
failing a CI-shaped gate locally is a false red. The goal tree keeps the directory listing, where an
untracked file IS what the owner would see.

## Mutation arithmetic from 44 / 70 (spec §4.2)

Measured on this branch 2026-11-24 by locating each entry's anchor in its enclosing top-level symbol of
`scripts/check-dashboard-entry.py` (44 entries) and `scripts/gen-dashboard.py` (70 entries).

| Manifest | Today | After S1 | After S2 | After S3 |
|---|---|---|---|---|
| gate (`check-dashboard-entry.json`, renamed `check-ask-store.json` in S2) | 44 | **62** = 44 + 18 new (Tasks 1–2) | **63** = 62 − 9 deleted + 10 new (Tasks 9, 12) | **45** = 63 − 18 deleted (Task 16) |
| `gen-dashboard.json` | 70 | 70 | **72** = 70 + 2 (Task 7) | **0** — file deleted (Task 15) |
| `page_chrome.json` | 114 | 114 | 114 | **117** = 114 + 3 new (Task 14) |

- **The 9 deleted in S2** anchor in code R1 removes: `ENTRY_ISH` 1, `_added_entry_line` 1,
  `added_entry_problems` 1, `collect` 2 ("collect stops reading the entry patch…", "the entry ratchet fails
  OPEN…"), `main` 1 ("main drops the entry problems…"), `verdict` 3.
- **4 re-bound in S2, not deleted:** `collect` 2 (the broken-git and missing-git entries) and `main` 1 (the
  git-failure fail-open entry) follow the git calls into `ask_store_problems` and `main`; `_declaration_reason`
  1 ("the marker parameter is ignored…") keeps its anchor and its `expect` names the `NO-REVIEW:` case.
- **The 18 deleted in S3:** 12 anchor in the grammar that leaves with the page (`parse_entries` 7,
  `header_error` 3, `BLOCK` 1, `_first_sentence` 1); 6 anchor in the cutover code Task 16 deletes
  (`cutover_problem` 1, the `--cutover-check` REF read 1, `store_edit_prs` 4 — Task 12's mutations expecting
  12.8, 12.12 and 12.13–12.16).
- **The 45 after S3** = the 23 below + Tasks 1–2's 18 + L1's 4 (expecting 12.2, 12.3, 12.5, 12.10).
- **23 stay throughout:** `fence_closes` 4, `fenced_lines` 1, `exemption_reason` 4, `_declaration_reason` 4,
  `_indented` 1, `EMPH` 1, `decisions` 2, `decision_errors` 3, plus the 3 re-bound `collect` / `main` entries.
- ⚠ **A measured refinement of the spec's "the contrast mutations MOVE":** of the 70 generator entries
  exactly ONE touches contrast, and it anchors `PROSE_CONTRAST_MIN` — the dashboard's own prose threshold,
  whose subject is deleted. None anchors `contrast_ratio` or `_luminance`. So nothing moves: that entry is
  deleted with the page, and Task 14 writes 3 NEW formula mutations in `page_chrome.json`.

Pins for the other manifests change only by the mutations this plan names: `goal-tree.json` 520 → 525 (S1);
`compaction-state.json` 89 → 91 (S1); `explainer-serve.json` 123 → 126 (S1); `regen-pages.json` 73 → 74 (S1);
`check-reference-namespace.json` 22 → 23 (S1). S2 and S3 deletions in those and in `check-merge-ready.json`
(214) follow one rule — an entry whose anchor's code is deleted goes — and the builder states each resulting
count in its commit message, from the anchor resolve's output.

---

# Slice S1 — open the new store beside the old one

Branch `dashboard-retire-s1` from `origin/master`. Additive: the per-PR rule and the page are untouched, so
**this PR still owes a dashboard entry** under today's rule. Slice gate: `gen-dashboard.py --self-test`
prints the same count before and after (the page is unchanged).

### Task 1: `read_asks` — the one directory reader

**Files:**
- Modify: `scripts/check-dashboard-entry.py` (new symbols after `decision_errors`; cases in `_self_test_body`
  and, for the FIFO and symlink worlds, `_impure_self_test`)
- Modify: `scripts/mutations/check-dashboard-entry.json`, `scripts/mutations/expected_mutations.py`

**Interfaces:**
- Consumes: `fenced_lines(text) -> set[int]` (0-based line indices), already in the file.
- Produces:
  - `ASKS_REL = "docs/asks"`, `ASK_NAME` (the compiled name rule), `ASK_KEEP = ".gitkeep"`,
    `ANSWER = "## Answer"`, `MAX_ASK_BYTES = 64 * 1024`, `MAX_ASKS = 1000`
  - `answered(text: str) -> bool`
  - `read_asks(directory: Path, names: list[str] | None = None) -> tuple[list[dict], list[str]]` — the OPEN
    asks, each `{"stem": str, "question": str, "body": str}` in filename order, and the problems as plain
    sentences each naming its file. `names=None` lists the directory; a list reads exactly those names from
    it. `question` is the first line without `# `; `body` is every line after the first.

**Enumerated behaviors** (the case NAME is the first cell's text after the number; mutations cite it):

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1.1 | a valid open ask is returned | `2026-11-25-a.md` = question, `**Decide:**` block | 1 ask, stem `2026-11-25-a`, 0 problems |
| 1.2 | a valid answered ask is not returned | same plus `## Answer` and a line | 0 asks, 0 problems |
| 1.3 | an empty .gitkeep is neither an ask nor a problem | directory holds only an empty `.gitkeep` | `([], [])` |
| 1.4 | a non-empty .gitkeep is a PROBLEM | `.gitkeep` holds `x` | 1 problem naming `.gitkeep` |
| 1.5 | a missing directory is a PROBLEM, never no asks | path does not exist | 0 asks, 1 problem |
| 1.6 | a `## Answer` inside a fence leaves the ask OPEN | the line sits between ` ``` ` fences | 1 ask |
| 1.7 | `## Answer — A` leaves the ask OPEN | trailing text on the heading | 1 ask |
| 1.8 | an indented `## Answer` leaves the ask OPEN | four leading spaces | 1 ask |
| 1.9 | `## Answer` with trailing space or CR closes the ask | `## Answer \r` | 0 asks |
| 1.10 | a name that fails the rule is a PROBLEM | `Foo.md`, `2026-11-25-a.txt`, `.DS_Store`, `2026-11-25-a.md~` | one problem each |
| 1.11 | an empty file, or one with no `# ` first line, is a PROBLEM | 0 bytes; first line `Which form?` | one problem each |
| 1.12 | a conflict marker on ANY line is a PROBLEM | valid first line, then `<<<<<<<`, two `## Answer` sides, `>>>>>>>`; and a `>>>>>>>` inside a fence | 0 asks from that file, 1 problem |
| 1.13 | a file over the cap, or not UTF-8, is a PROBLEM | 65,537 bytes; bytes `b"# q\n\xff"` | one problem each, no exception |
| 1.14 | a question with no body is OPEN | `# Which form?` with no newline | 1 ask, `body == ""` |
| 1.15 | a PROBLEM entry still returns the readable asks | 1.1's file beside `Foo.md` | 1 ask AND 1 problem |
| 1.16 | over MAX_ASKS is a PROBLEM, not a truncation | `MAX_ASKS` patched to 3 (restored in `finally`), 4 valid files | 3 asks AND 1 problem stating both numbers |
| 1.17 | a symlink, a subdirectory and a FIFO are PROBLEMS, and the FIFO does not block | impure world; the FIFO case asserts the call returns in under 0.5 s | one problem each |

- [ ] **Step 1: Write the failing cases** 1.1–1.16 in `_self_test_body` over a `tempfile.TemporaryDirectory`,
  and 1.17 in `_impure_self_test`. The two that fix the spec's exact values:

```python
case("`## Answer — A` leaves the ask OPEN",
     [a["stem"] for a in read_asks(world({"2026-11-25-a.md": "# Q?\nbody\n## Answer — A\nyes\n"}))[0]],
     ["2026-11-25-a"])
case("a conflict marker on ANY line is a PROBLEM",
     (lambda r: (r[0], len(r[1])))(read_asks(world({"2026-11-25-a.md":
         "# Q?\n<<<<<<< ours\n## Answer\nA\n=======\n## Answer\nB\n>>>>>>> theirs\n"}))),
     ([], 1))
```

- [ ] **Step 2: Run** `python3 scripts/check-dashboard-entry.py --self-test`. Expected: FAIL, `NameError:
  name 'read_asks' is not defined` (or the cases reported failing), rc 1.
- [ ] **Step 3: Implement** the constants, `answered` and `read_asks`. Per entry: `os.open(path, O_RDONLY |
  O_NONBLOCK | O_NOFOLLOW)`, `os.fstat` on the descriptor, `stat.S_ISREG` or PROBLEM, `st_size >
  MAX_ASK_BYTES` is a PROBLEM, read at most `MAX_ASK_BYTES + 1` bytes, decode strictly. Names are sorted;
  the conflict test is `line.startswith(("<<<<<<<", ">>>>>>>"))` over every line, before `answered`.
- [ ] **Step 4: Run** the self-test. Expected: PASS, the pure count is 149 plus the new cases, rc 0.
- [ ] **Step 5: Add 11 mutations** to the manifest, each `expect`ing the case named:

| Mutation name | Edit | Expects |
|---|---|---|
| the answer rule loosens to a prefix | `.rstrip() == ANSWER` → `.startswith(ANSWER)` | 1.7 |
| the answer rule strips leading space | `.rstrip()` → `.strip()` in `answered` | 1.8 |
| the answer rule ignores the fence | drop the `fenced_lines` test in `answered` | 1.6 |
| a conflict marker is looked for on the first line only | scan `lines[:1]` | 1.12 |
| the per-file cap is dropped | remove the `MAX_ASK_BYTES` comparison | 1.13 |
| a non-regular entry is read | remove the `S_ISREG` test | 1.17 |
| MAX_ASKS truncates in silence | drop the over-cap problem | 1.16 |
| the name rule admits uppercase | `[a-z0-9]` → `[A-Za-z0-9]` | 1.10 |
| a non-empty .gitkeep is skipped | drop its size test | 1.4 |
| a problem drops the readable asks | return `[]` when problems exist | 1.15 |
| a missing directory reads as no asks | return `([], [])` on `FileNotFoundError` | 1.5 |

- [ ] **Step 6: Pin and sweep.** Set `"scripts/check-dashboard-entry.py": 55` in `expected_mutations.py`;
  run `python3 scripts/check-plan-code.py --mutate . --only scripts/check-dashboard-entry.py`. Expected: every
  mutation red via the case it names. Run the anchor resolve.
- [ ] **Step 7: Commit** the three paths: `Ask store S1: read_asks, the one reader of docs/asks/ (spec §2.3)`.

**FAILS IF:** any of 1.1–1.17 is red, or a listed mutation survives.

### Task 2: A1 and F1, run by the existing PR step

**Files:**
- Modify: `scripts/check-dashboard-entry.py` (`f1_problems`, `ask_store_problems`, `main`, docstring, cases)
- Create: `docs/asks/.gitkeep` (0 bytes)
- Modify: `scripts/mutations/check-dashboard-entry.json`, `scripts/mutations/expected_mutations.py`

**Interfaces:**
- Consumes: `read_asks`, `ASK_NAME`, `ASKS_REL` (Task 1).
- Produces:
  - `f1_problems(base_files: dict[str, bytes], head_files: dict[str, bytes]) -> list[str]` — pure. Only keys
    matching `ASK_NAME` are considered.
  - `ask_store_problems(base: str | None, root: Path) -> tuple[list[str], str | None]` — `(problems, err)`.
    A1: names from `git ls-tree --name-only HEAD docs/asks/` (basenames), passed to `read_asks(root /
    ASKS_REL, names)`; a name tracked at HEAD and absent on disk is a PROBLEM. F1, only when `base` is given:
    files at `git merge-base <base> HEAD` and at HEAD, read with `git cat-file blob`. Any git failure is
    `err`, and `main` prints `CANNOT RUN — … Treat this as NOT CHECKED.` and returns 2.
  - `main` calls it after `collect`; a non-empty problem list prints `REFUSED — ` and returns 1 whatever the
    entry verdict, the waiver included.
  - Its git calls go through `subprocess.run`, so the existing `_with_run` stub reaches them (r1 Claude M2).

**Enumerated behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 2.1 | gaining an answer passes F1 | head = base + `## Answer\n…` | `[]` |
| 2.2 | an appended superseding note passes F1 | head = answered base + a paragraph | `[]` |
| 2.3 | an edited question is refused | first line differs | 1 problem naming the file |
| 2.4 | a deleted ask is refused | name in base, absent in head | 1 problem: "gone at HEAD" |
| 2.5 | deleting .gitkeep with the first ask passes F1 | base `{".gitkeep": b""}`, head `{"2026-11-25-a.md": …}` | `[]` |
| 2.6 | a base file outside the name rule is not F1's subject | base `{"Foo.md": b"x"}`, head `{}` | `[]` (A1 refuses it while it exists) |
| 2.7 | a rewritten answer is refused | text under `## Answer` changed | 1 problem |
| 2.8 | main refuses a bad ask file at HEAD | impure: commit `docs/asks/Foo.md` | rc 1, output names `Foo.md` |
| 2.9 | an untracked scratch file does not fail A1 | impure: `docs/asks/.DS_Store` untracked | rc as without it |
| 2.10 | the directory listing still reports that file | `read_asks(dir)` on the same world | 1 problem (the goal tree's view) |
| 2.11 | a tracked ask missing on disk is a PROBLEM | impure: `rm` without commit | rc 1, "tracked at HEAD, missing on disk" |
| 2.12 | A1's own git failure is CANNOT RUN | pure: `_with_run(_boom, lambda: ask_store_problems("master", ROOT))`, and again with a stub returning `_R(128, "", "fatal")` | `err is not None` both times, `problems == []` |
| 2.13 | a tree holding only `.gitkeep` passes | impure: a `fixture_git` temp repo with `docs/asks/.gitkeep` committed; `ask_store_problems(None, <that repo>)` — never this checkout (r3 Claude M1: the mutation harness stages a tree with no `.git`, where a live `git ls-tree HEAD` exits 128) | `([], None)` |
| 2.14 | main refuses on A1's problem list | pure: `collect` stubbed clean, `ask_store_problems` stubbed `(["x"], None)` | rc 1, `REFUSED — ` |
| 2.15 | main is CANNOT RUN on A1's err | pure: `collect` stubbed clean, `ask_store_problems` stubbed `([], "boom")` | rc 2, never 0 or 1 |

**Why 2.12 is driven directly, not through `main` (r1 Claude M2):** through `main`, a missing `git` fails first
inside `collect` (its first `git` call), so a `main`-level case passes on `collect`'s CANNOT RUN even when
`ask_store_problems` swallows its own error and returns `([], None)` — a fail-open with no witness.

**The existing `main` cases stub A1 too (r1 Claude M1).** The case "main: an entry-only branch with a malformed
entry exits 1" (and the CANNOT RUN case beside it) stubs only `g["collect"]` and calls `main(["--base",
"master"])`. After this task that call reaches A1's real `git merge-base master HEAD`; in a CI `pull_request`
checkout there is `origin/master` and no local `master`, so git fails, `main` returns 2 and the case is red —
in CI only. Every existing `main` case therefore saves `g["ask_store_problems"]`, stubs it `([], None)`, and
restores it in the same `finally` as `collect`.

- [ ] **Step 1: Write the failing cases** 2.1–2.7, 2.12, 2.14 and 2.15 (pure) and 2.8–2.11, 2.13 (impure,
  `fixture_git` as the existing cannot-run cases build theirs); add the `ask_store_problems` stub to every
  existing `main` case.
- [ ] **Step 2: Run** the self-test. Expected: FAIL on the new names.
- [ ] **Step 3: Implement** `f1_problems`, `ask_store_problems`, the `main` call, and one docstring paragraph
  stating the m3 decision in these words: *A1 reads the names git tracks at HEAD (`git ls-tree`), not the
  directory listing; content comes from the working tree.*
- [ ] **Step 4: Create** `docs/asks/.gitkeep`, commit it WITH the code (Step 5's live run reads the directory at HEAD; 2.13 builds its own).
- [ ] **Step 5: Run** the self-test (PASS), then the gate itself after committing:
  `python3 scripts/check-dashboard-entry.py --base origin/master`. Expected: no `REFUSED` line that names
  `docs/asks`.
- [ ] **Step 5b: Run the self-test where CI runs it — no local `master` (r1 Claude M1's falsifier).** The
  local run cannot show the break, because `master` exists here:

```bash
S="$(mktemp -d)/c" && git clone -q . "$S" && git -C "$S" checkout -q --detach
git -C "$S" branch -D master 2>/dev/null   # a clone made from a worktree has no local master to delete
! git -C "$S" rev-parse -q --verify refs/heads/master && git -C "$S" rev-parse -q --verify origin/master \
  && (cd "$S" && set -o pipefail && python3 scripts/check-dashboard-entry.py --self-test | tail -2)
```

  Expected: rc 0 and the SAME TWO summary lines as Step 5 — the pure suite's `N/N passed`, then the impure
  suite's `M/M cannot-run cases passed` (r3 Claude m5: `tail -1` showed only the second; measured on a
  copy 2026-11-24, today's lines are `149/149 passed` and `13/13 cannot-run cases passed`). `pipefail` is load-bearing (r2 Codex m4): without it the
  pipeline's status is `tail`'s, 0 over a red self-test — measured 2026-11-24 with a child that prints and
  exits 1: rc 0 plain, rc 1 under `pipefail`. **FAILS IF** any `main` case is red there — the case reached
  real git. Control, run once: remove the `ask_store_problems` stub from the malformed-entry case and this run
  goes red (rc 2 where the case wants 1).
- [ ] **Step 6: Add 7 mutations** and pin `62`:

| Mutation name | Edit | Expects |
|---|---|---|
| F1 checks every base file | drop the `ASK_NAME` filter in `f1_problems` | 2.5 |
| F1 accepts a rewritten ask | prefix test → `True` | 2.3 |
| F1 misses a deleted ask | skip names absent from head | 2.4 |
| A1 lists the directory instead of HEAD's tree | pass `None` for `names` | 2.9 |
| main stops running A1 | drop the `ask_store_problems` call's refusal | 2.14 |
| A1's git failure returns err=None | `ask_store_problems`' failure branch returns `(problems, None)` | 2.12 |
| main ignores A1's err | drop the `if err:` return 2 after `ask_store_problems` | 2.15 |

- [ ] **Step 7: Sweep, resolve, commit.** The control must be GREEN in the staged tree, which has no `.git`:
  `python3 scripts/check-plan-code.py --mutate . --only scripts/check-dashboard-entry.py` reports no
  red-control or NOT MEASURED line (r3 Claude M1). **FAILS IF** any case of this suite reads this checkout's
  git — measured 2026-11-24 in a copy with no `.git`: `git ls-tree --name-only HEAD docs/asks/` rc 128, the
  same call in a `fixture_git` temp repo rc 0.

**FAILS IF:** a file at HEAD under `docs/asks/` that `read_asks` calls a PROBLEM passes the gate; or an ask
present at the merge base is absent or not a byte prefix at HEAD and the gate passes.
⛔ **F1's pre-committed retreat (spec §3):** a review finding caused by an F1 fix deletes F1 — `f1_problems`,
behaviors 2.1–2.7 and three mutations — and the pin drops by 3. It is not patched.

### Task 3: the goal tree reads `docs/asks/` and shows the question, the options and the warning

**Files:**
- Modify: `scripts/goal-tree.py` (`ASKS_REL`, `NEEDS_SOURCES`, `needs_from_asks`, the source loop in
  `collect`, `_item_line`, `_ref_html`, `needs_html`, `needs_lines`; cases)
- Modify: `scripts/mutations/goal-tree.json`, `scripts/mutations/expected_mutations.py`

**Interfaces:**
- Consumes: `read_asks`, `decisions`, `decision_errors` from the gate, loaded with
  `_sibling("check-dashboard-entry")`.
- Produces:
  - `NEEDS_SOURCES = ("dashboard", "asks", "ledger", "backlog")`
  - `needs_from_asks(directory: Path) -> tuple[list[dict], list[str]]` — one `_item("decision", "asks",
    <stem>, None, <question cut to 160>, …)` per open ask, with two added keys: `options: list[str]` (each
    option's text, ` [recommended]` kept) and `decision_warning: str | None` (the `decision_errors(body,
    "needs-you")` sentences joined with `; `).
  - the source loop gains a directory source: for `asks` it calls `needs_from_asks(root / ASKS_REL)` and
    treats an exception or a non-empty problem list exactly as it treats the store's today (`errors["asks"]`
    ending ` — NOT READ`).
  - `_ref_html("asks", ref, None)` prints `<code>{ref}</code> <span class="src">(docs/asks/)</span>`; the
    ledger's wording is unchanged.

**Enumerated behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 3.1 | K4: an open ask file is a NEEDS YOU item | fixture `docs/asks/` with one open ask | 1 item, `source == "asks"`, `ref` = stem, `href is None` |
| 3.2 | a valid ask shows its question and options, no warning | `**Decide:**` with two options, one recommended | text line and two option lines; `decision_warning is None` |
| 3.3 | an ask with no decision block is KEPT, with a warning | question only | 1 item; the warning names the missing block |
| 3.4 | malformed choices are named in the warning | one option only | 1 item; the warning carries `decision_errors`' sentence |
| 3.5 | K5: a missing docs/asks is never "nothing waits on you" | no directory, other sources empty | `needs_state` is not the all-clear; lines say `asks` NOT READ |
| 3.6 | K5: a PROBLEM entry marks the source NOT READ and keeps the readable ask | 3.1's ask beside `Foo.md` | 1 item AND NOT READ |
| 3.7 | an answered ask is not an item | file with `## Answer` | 0 items |
| 3.8 | the item's ref is stable across runs | two `collect` calls on one tree | the `(source, ref)` diff is empty |
| 3.9 | the old store's asks still show | fixture root with one open ask in the store, driven through `collect` (not `needs_from_dashboard` directly) | 1 item, `source == "dashboard"`, `/dashboard#…` link |
| 3.10 | the all-clear names four sources | every source read, none open | the line names dashboard asks, ask files, the ledger and the backlog |

- [ ] **Step 1: Write the failing cases** 3.1–3.10 beside the existing `needs_from_dashboard` cases.
- [ ] **Step 2: Run** `python3 scripts/goal-tree.py --self-test`. Expected: FAIL on the new names.
- [ ] **Step 3: Implement.** The source loop in `collect` keeps its tuple text verbatim — `("dashboard",
  DASHBOARD_REL, needs_from_dashboard),` stays one line — and the `asks` directory source is a separate
  `try` block after the loop, because Step 5's old-reader sever anchors that exact text (r3 Claude m3). If
  the implementation must reshape it, take the anchor from the implemented line and run the all-manifest
  anchor resolve before Step 5. Options and the warning print under the item in both `_item_line` (text) and
  `needs_html` (a `<ul class="opts">` and a `<p class="warn">`), every string through `html.escape`.
- [ ] **Step 4: Run** the self-test (PASS) and `python3 scripts/check-page-links.py --self-test`.
- [ ] **Step 5: Add 5 mutations**, pin `525`: "the goal tree's call to read_asks is severed" (return
  `([], [])`; expects 3.1), "the goal tree's call to the old store's reader is severed" (in the source loop of
  `collect`, `needs_from_dashboard),` → `lambda _t: ([], [])),`; expects 3.9 — spec K4: *in S1 the same holds
  for the old store's reader*, r1 Codex M4), "an asks problem is dropped" (expects 3.6), "a missing decision
  drops the ask" (expects 3.3), "the asks source leaves NEEDS_SOURCES" (expects 3.5). No existing
  `goal-tree.json` entry anchors that call (checked 2026-11-24: 0 entries' `before` text names
  `needs_from_dashboard`), so the old-reader sever is new. Task 10 deletes it with its anchor.
- [ ] **Step 6: Sweep** `--only scripts/goal-tree.py` in the draft PR's CI (520+ mutations exceed one local
  command's budget); run the anchor resolve locally; commit.

**FAILS IF (K4, K5):** either severed-call mutation (the new reader's or the old reader's) stays green; or the
tree prints "nothing waits on you" while `docs/asks/` is missing or holds a PROBLEM.

### Task 4: the compaction snapshot counts both sources

**Files:**
- Modify: `scripts/compaction-state.py` (`pending_asks`, `decision_section` wording, cases)
- Modify: `scripts/mutations/compaction-state.json`, `scripts/mutations/expected_mutations.py`

**Interfaces:**
- Consumes: `read_asks` through `_load("check-dashboard-entry.py", …)`.
- Produces: `pending_asks(root) -> (count | None, newest, why | None)`, unchanged in shape. `count` = open
  entries in the old store (today's path) + `len(asks)`; `newest` gains the last `RECENT_ASKS` stems in
  filename order as `{"id": stem, "title": question}`; ANY problem from `read_asks`, or a failure to load it,
  returns `(None, [], why)` — the CANNOT RUN line.

**Enumerated behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 4.1 | K6: the count is the fixture's | store with 1 open ask, `docs/asks/` with 2 open and 1 answered | `count == 3` |
| 4.2 | a PROBLEM in docs/asks is CANNOT RUN, never 0 | `Foo.md` in the directory | `count is None`, `why` names it |
| 4.3 | a gate that cannot be loaded is CANNOT RUN | `_load` raises | `count is None` |
| 4.4 | a FIFO ask file does not block the hook | `os.mkfifo(docs/asks/2026-11-25-a.md)` | returns in under 0.5 s, `count is None` |
| 4.5 | the newest asks are the last stems | 7 open ask files | 5 ids, the 5 latest names |

- [ ] **Step 1: Write the failing cases.** **Step 2: Run** `python3 scripts/compaction-state.py --self-test`
  (FAIL). **Step 3: Implement.** **Step 4: Run** (PASS).
- [ ] **Step 5: Add 2 mutations**, pin `91`: "pending_asks stops calling read_asks" (expects 4.1), "an asks
  problem counts as zero" (expects 4.2). Sweep `--only scripts/compaction-state.py`, resolve, commit.

**FAILS IF (K6):** `pending_asks` returns a count other than the fixture's, 0 on a problem, or exceeds 0.5 s
on the FIFO case.

### Task 5: the staleness watch and the rebuild mapping

**Files:**
- Modify: `scripts/explainer-serve.py` (`DIR_SOURCES`, `PAGE_SOURCES["goal-tree"]`, the `/_stale` handler,
  the coverage case), `scripts/regen-pages.py` (`pages_for`)
- Modify: `scripts/mutations/explainer-serve.json`, `scripts/mutations/regen-pages.json`, pins

**Interfaces:**
- Produces: `DIR_SOURCES = frozenset({"docs/asks"})`; `source_mtime(path: Path) -> tuple[int, str]` — for a
  file its `st_mtime_ns` and its path; for a directory the maximum over the directory itself and its `*.md`
  children (one level) and the path that holds that maximum. `/_stale` replies `stale <that path>`.

**Enumerated behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 5.1 | an added ask file makes the goal tree stale | create a file after the build time | `stale docs/asks/<name>` |
| 5.2 | an appended answer makes it stale | in-place append to an existing ask | `stale docs/asks/<name>` |
| 5.3 | an untouched directory is fresh | build time after every mtime | `fresh` |
| 5.4 | a directory not in DIR_SOURCES is still refused | coverage case with `docs/` declared as a source | the case fails closed |
| 5.5 | a non-`.md` child is not watched | touch `docs/asks/.gitkeep` only (directory mtime held) | `fresh` |
| 5.6 | an edit under docs/asks rebuilds the goal tree | `pages_for` payload with `file_path` `…/docs/asks/2026-11-25-a.md` | `["goal-tree"]` |
| 5.7 | a path that merely contains `docs/asks` does not | `…/notes/docs/asks-old/x.md` | `[]` |

- [ ] **Steps 1–4:** failing cases (through `_drive_stale` for 5.1–5.3 and 5.5), red run of
  `python3 scripts/explainer-serve.py --self-test` and `python3 scripts/regen-pages.py --self-test`,
  implementation, green run.
- [ ] **Step 5: Add mutations**, pins `126` and `74`: "a directory source reads only its own mtime" (expects
  5.2), "any directory is accepted as a source" (expects 5.4), "the stale reply names the directory, not the
  child" (expects 5.1); "an ask edit rebuilds nothing" (expects 5.6). Sweep both scripts, resolve, commit.

**FAILS IF:** an in-place append to an ask leaves `/_stale` answering `fresh`.

### Task 6: the namespace guard, the backlog rows and the slice's record

**Files:**
- Modify: `scripts/check-reference-namespace.py` (`SCOPE` gains `"docs/asks/"`; one case), its manifest
  ("docs/asks leaves the scope", expects the case; pin `23`)
- Modify: `docs/backlog.md` (the ✍-tag row, backlog #623, retargeted to `scripts/goal-tree.py`; one new row
  for this retirement, numbered by the next free row), `docs/goal-threads.md` (a line under
  `## GOAL dashboard-decisions`), `docs/roadmap-to-launch.md` (one row), `docs/dashboard-entries.md` (this
  PR's own entry — the rule is still live)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 6.1 | an added bare number in an ask file is refused | `_v("docs/asks/2026-11-25-a.md", "+see #623")` | 1 violation |
| 6.2 | the qualified form passes | `+see backlog #623` | 0 violations |

- [ ] **Step 1–4:** case red, `SCOPE` edit, case green: `python3 scripts/check-reference-namespace.py --self-test`.
- [ ] **Step 5: Docs.** After editing `docs/backlog.md` run `python3 scripts/gen-backlog-page.py --self-test`
  as well as the document guards.
- [ ] **Step 6: Slice gate.** Run every `python3 scripts/check-*` step of `.github/workflows/ci.yml` that
  reads `docs/`, with `--base origin/master` where the step passes one; then commit and run
  `python3 scripts/check-dashboard-entry.py --base origin/master`. Expected: its message says an entry block
  was added.

**FAILS IF:** a bare `#N` added under `docs/asks/` passes `check-reference-namespace.py --base`.

---

# Slice S2 — cut over: freeze the old store and remove the per-PR rule

Branch `dashboard-retire-s2` from `origin/master` after S1 merges. `check-merge-ready.py` is expected to
answer HOLD (a gate is loosened); the owner pre-approved the merge on convergence and green CI (spec O2).
Task 12 is LAST and is written after master is merged in for the final time.

### Task 7: C1 — `gen-dashboard.py --assert-no-open-asks`

**Files:** Modify `scripts/gen-dashboard.py` (`main`, cases), `scripts/mutations/gen-dashboard.json`, pin `72`.

**Interfaces:** Produces the flag: reads `docs/dashboard-entries.md` (or the store named by
`--store PATH`), prints
`ok — the old store holds 0 open asks` rc 0, or `REFUSED — <n> open ask(s): <ids>` rc 1; an unreadable store
or any entry with a parse error is `CANNOT RUN` rc 2.

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 7.1 | a store with one open ask is refused, naming its id | fixture `[needs-you]` entry, no resolver | rc 1, the id in the output |
| 7.2 | a resolved ask passes | the same plus its `[resolved: …]` entry | rc 0 |
| 7.3 | an unreadable store is CANNOT RUN | missing file; an entry with a bad header | rc 2 each |
| 7.4 | the live store passes today | this repo | rc 0 (0 open asks, measured in the spec's §8) |

- [ ] **Steps 1–4:** failing cases, red `python3 scripts/gen-dashboard.py --self-test`, implement over
  `unresolved(parse_entries(text))` — the two existing functions, no new reader — green.
- [ ] **Step 5: 2 mutations:** "assert-no-open-asks passes an open ask" (expects 7.1), "a parse error reads as
  no asks" (expects 7.3). Sweep `--only scripts/gen-dashboard.py`, resolve, commit.

**FAILS IF (C1):** an open ask in the store at S2's merge ref and the step is green.

### Task 8: rename the gate and repoint every loader, in one commit

**Files:**
- `git mv scripts/check-dashboard-entry.py scripts/check-ask-store.py`;
  `git mv scripts/mutations/check-dashboard-entry.json scripts/mutations/check-ask-store.json` (every `file`
  field rewritten); the pin's key renamed; the row in `scripts/sweep-costs.json` renamed
- Modify the by-filename loaders: `scripts/gen-dashboard.py` (`_gate_module`), `scripts/goal-tree.py`
  (`needs_from_asks`), `scripts/compaction-state.py` (`pending_asks`), `scripts/check-review-recorded.py`
  (`_load_declaration_parser`), `scripts/check-merge-ready.py` (`DASHBOARD_GATE` renamed `ASK_STORE_GATE`,
  `_dashboard_gate`, the gate list's argv, `_real_cde`, `_gate_main`)
- Modify the tables and live-tree cases that name the file: `scripts/check-fixture-variation.py`,
  `scripts/check-main-drivable.py`, `scripts/check-plan-code.py` (including the case named for the chain
  through `gen-dashboard.py`), `scripts/check-publishability.py` (its synthetic `requires-skill dashboard`
  world stays), `scripts/check-shipping-sets.py`, `scripts/check-ratchet-contract.py`,
  `scripts/check-fixture-git-isolation.py`, `scripts/check-selftest-counts.py`, and the manifests that name
  it (`batch-ci.json`, `check-fixture-git-isolation.json`, `check-publishability.json`, `check-plan-code.json`)
- Modify `.github/workflows/ci.yml`: the self-test step's name and path, AND the `dashboard entry ratchet`
  step's script path (`scripts/check-dashboard-entry.py` → `scripts/check-ask-store.py`, its arguments
  unchanged; Task 9 drops `--pr-body-file`, Task 12 replaces the step). Without it every commit between this
  task and Task 12 runs a CI gate against a file that no longer exists (r1 Codex M3)

No behavior changes, so there is no new case: the test is that every existing suite stays green.

- [ ] **Step 1: Record the before state.** Run and save the last line of each:
  `gen-dashboard.py`, `goal-tree.py`, `compaction-state.py`, `brief-compose.py`, `check-review-recorded.py`,
  `check-merge-ready.py`, `check-plan-code.py`, `check-fixture-variation.py`, `check-main-drivable.py`,
  `check-publishability.py`, `check-shipping-sets.py`, `check-ratchet-contract.py` — each with `--self-test`.
- [ ] **Step 2: Rename and repoint.**
- [ ] **Step 3: Find what is left.** Expected output: nothing.

```bash
git grep -n -E 'with_name\("check-dashboard-entry|_sibling\("check-dashboard-entry|_load\("check-dashboard-entry|"scripts/check-dashboard-entry\.py"|scripts/check-dashboard-entry\.py' -- scripts .github .claude/settings.json ':!scripts/fixtures' | grep -v -E '^\S+:[0-9]+:\s*#' || true
```

- [ ] **Step 4: Re-run Step 1's twelve suites.** Expected: the same counts, all rc 0. Then
  `python3 scripts/check-explainer-delivery.py` and the anchor resolve.
- [ ] **Step 5: Commit** `Ask store S2: the gate file is check-ask-store.py; every loader repointed`.

**FAILS IF:** any Step-1 suite's count changes or its rc is non-zero; or Step 3 prints a line that is a load,
an argv, a workflow `run:` line or a manifest `file` (a comment naming the old file as history is not).
Control, run 2026-11-24 on the unrenamed tree: Step 3's `.github` half prints `ci.yml:988` (the self-test) and
`ci.yml:1112` (the PR gate) — so the grep sees the gate step, and a rename that repoints only the self-test
leaves `ci.yml:1112` printed.

### Task 9: remove R1 and `NO-ENTRY:`; narrow the escape diagnosis

**Files:**
- Modify `scripts/check-ask-store.py`: delete `verdict`, `NO_ENTRY`, `EXEMPT_DIRS`, `EXEMPT_FILES`,
  `_is_exempt`, `ENTRY_ISH`, `_added_entry_line`, `added_entry_problems`, `added_reference_errors`, the
  entry half of `collect`, and `--pr-body-file`; `exemption_reason` and `_declaration_reason` take
  `marker="NO-REVIEW:"` as their default. `parse_entries`, `header_error`, `HEADER`, `FLAG`, `BLOCK`,
  `_first_sentence` and the names `gen-dashboard.py` binds from `_GATE` STAY until S3.
- Modify `scripts/check-merge-ready.py`: `GATE_ESCAPE = {"review recorded": "NO-REVIEW:"}`;
  `ESCAPE_LOOKALIKE` narrows to `no-review`; `escape_diagnosis` loses its `other` branches (MISDIRECTED and
  "the other marker is in the body but inert"); the gate list's `dashboard entry` row becomes
  `("ask store", ["python3", "scripts/check-ask-store.py", "--base", …])` with no PR body
- Modify both manifests and pins; `scripts/check-review-recorded.py` cases if they pass the marker
- Modify `.github/workflows/ci.yml`: the gate step drops `--pr-body-file /tmp/pr-body.md`, its `BODY` env and
  its `printf` (the flag no longer parses, so leaving it turns the step red with an argparse error). The
  `review recorded` step writes its own body file and is untouched

**Interfaces:** Produces `main(argv)` with `--self-test` and `--base` (optional, no default): with a base it
runs A1 and F1; without, A1 only (Task 12 adds L1 to both). Output stays `ok — …` / `REFUSED — …` /
`CANNOT RUN — …`.

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 9.1 | a branch with no store edit and no waiver passes | impure: a commit touching `scripts/x.py` only | rc 0 |
| 9.2 | a fenced `NO-REVIEW:` line is not granted (K7) | `exemption_reason` on a fenced marker | `None` |
| 9.3 | the default marker is NO-REVIEW: | `exemption_reason("NO-REVIEW: docs only")` | `"docs only"` |
| 9.4 | `NO-ENTRY:` is no longer a marker | `exemption_reason("NO-ENTRY: x")` | `None` |
| 9.5 | INVISIBLE still diagnoses | merge-ready fixture: the exact token, fenced | the INVISIBLE sentence |
| 9.6 | MISSPELLED still diagnoses | `no-review:` lower case | the MISSPELLED sentence |
| 9.7 | without --base, F1 is not run and git's merge-base is not asked | impure: no remote | rc 0 on a clean tree |
| 9.8 | `--pr-body-file` is gone | `main(["--base", "origin/master", "--pr-body-file", "x"])` | argparse exit 2 (`SystemExit`, code 2) |

- [ ] **Step 1: Write 9.1–9.8**; delete the cases whose subject is deleted (the entry ratchet's, the
  MISDIRECTED fixtures). **Step 2: Run** `check-ask-store.py`, `check-merge-ready.py` and
  `check-review-recorded.py` self-tests (FAIL: 9.3, 9.4, 9.7, 9.8 — the flag still parses).
- [ ] **Step 3: Implement the deletions.** Back up the pre-edit gate file to the scratchpad first.
- [ ] **Step 4: Run** the three self-tests and `gen-dashboard.py --self-test` (PASS; the page still loads
  its grammar).
- [ ] **Step 5: K7's proof.** In a scratch copy replace `exemption_reason`'s body with `return "stub"`; run
  the `check-review-recorded.py` and `check-merge-ready.py` self-tests against it. Expected: BOTH red. If
  either stays green, add the case that reddens it before continuing.
- [ ] **Step 6: Manifests.** Delete the 9 entries and re-bind the 4 named in *Mutation arithmetic*; pin the
  gate at `53` (62 − 9; Task 12 adds 10). In `check-merge-ready.json` delete each entry whose anchor sits in
  a removed branch and state the new pin in the commit message. Sweep the gate script, resolve, commit.

- [ ] **Step 6b: The CI step no longer passes the flag (r2 Codex M1).** `ci.yml` keeps ONE legitimate
  `--pr-body-file` — the `check-review-recorded (PR only)` step's own — so a whole-file grep can never print
  nothing. The check reads the gate's step alone (its lines up to the next `- name:`, comments dropped):

```bash
STEP=$(awk '/- name: dashboard entry ratchet$/{f=1;print;next} f&&/- name:/{f=0} f&&!/^[[:space:]]*#/' .github/workflows/ci.yml)
test -n "$STEP" && printf '%s\n' "$STEP" | grep -q 'scripts/check-ask-store.py' \
  && ! printf '%s\n' "$STEP" | grep -n -e '--pr-body-file' -e 'BODY' \
  && test "$(grep -c -- '--pr-body-file' .github/workflows/ci.yml)" -eq 1
```

  Expected: rc 0, nothing printed. Controls, run 2026-11-24 on copies of today's `ci.yml`: with Task 8's
  rename only (flag still passed) → rc 1, printing the `BODY`, `printf` and `--pr-body-file` lines; with
  Task 9's edit → rc 0; with Task 9's edit AND the review-recorded step's flag also removed → rc 1 (count 0).
  The step is still named `dashboard entry ratchet` here; Task 12 Step 7 replaces it.

**FAILS IF (K7):** either self-test is green over the stub; or 9.2 grants the fenced line; or Step 6b
returns 0 while the gate's step still passes `--pr-body-file` (9.8 is the flag's removal; Step 6b is CI
not passing it).

### Task 10: drop the old-store readers

**Files:** Modify `scripts/goal-tree.py` (delete `needs_from_dashboard`, `DASHBOARD_REL`, the `dashboard`
row of the source loop; `NEEDS_SOURCES = ("asks", "ledger", "backlog")`; the module docstring; the all-clear
wording), `scripts/compaction-state.py` (the store read and `MAX_STORE` leave `pending_asks`;
`decision_section` says "ask files"), both manifests and pins.

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 10.1 | K4: an open ask in the OLD store contributes nothing | fixture store with one open ask, empty `docs/asks/` | 0 items; no `dashboard` source in the snapshot |
| 10.2 | the goal tree no longer loads the generator | `collect` with `_sibling` patched to raise on `gen-dashboard` | no exception |
| 10.3 | the all-clear names three sources | every source read | ask files, the ledger, the backlog |
| 10.4 | the snapshot counts ask files only | Task 4's fixture | `count == 2` |
| 10.5 | the FIFO case is the ask-file case | Task 4's 4.4 kept; the FIFO-store case deleted | under 0.5 s |

- [ ] **Steps 1–4:** cases (3.9 and the store half of 4.1 are deleted with their subject), red, implement,
  green on both self-tests.
- [ ] **Step 5: Manifests.** Delete the entries anchored in removed code (in `goal-tree.json`
  the two that name the dashboard source and Task 3's old-reader sever; one in `compaction-state.json` is the
  FIFO-store entry, re-bound to 4.4's anchor rather than deleted). Resolve; commit.

**FAILS IF:** 10.1 returns an item, or `git grep -n 'gen-dashboard' scripts/goal-tree.py
scripts/compaction-state.py` prints a load.

### Task 11: the skill, the doc rules, the declarations and the amendments

**Files:**
- `git mv .agents/skills/dashboard .agents/skills/needs-you`; replace the symlink `.claude/skills/dashboard`
  with `.claude/skills/needs-you` → `../../.agents/skills/needs-you`; rewrite `SKILL.md` (spec §3's row:
  how to write an ask, how to record its answer, never edit or delete an ask, never write the old store)
- `scripts/check-explainer-delivery.py`: `PAGE_SKILLS = ["explain-topic"]`
- The doc rows of spec §3 *Doc rules*: `docs/dev-process.md` (two rows become one, net −1 line),
  `docs/process-checklists.md`, `docs/CLAUDE.md` rule 3, the four memory files and the `MEMORY.md` row,
  `docs/roadmap-to-launch.md`; `docs/available-skills.md` by `python3 scripts/regen-skills-doc.py`
- `docs/marketplace/components.json` (the `skill-dashboard` and `check-dashboard-entry` components renamed
  to their new paths), then `docs/marketplace/shipping-sets.json` regenerated:
  `python3 scripts/mkt_stage.py --declare docs/marketplace/components.json docs/marketplace/shipping-sets.json`
  (needs `claude`; run locally, committed with the change)
- The dated notes of spec §6 at the top of the four earlier specs

- [ ] **Step 1: The skill teaches the exact line (m2).** After the rewrite this must print at least one line,
  and the second command none:

```bash
grep -n -F 'exactly `## Answer`' .agents/skills/needs-you/SKILL.md
grep -n -E 'dashboard-entries\.md.*(append|add an entry)|regen-pages\.py --page dashboard' .agents/skills/needs-you/SKILL.md || true
```

- [ ] **Step 2: Run** `python3 scripts/check-explainer-delivery.py`, `python3 scripts/check-docs.py`,
  `python3 scripts/check-shipping-sets.py --map docs/marketplace/components.json`,
  `python3 scripts/check-shipping-sets.py --closure docs/marketplace/shipping-sets.json`,
  `python3 scripts/check-inventory.py` (rc 3 is the owner's checkpoint, as CI treats it), and
  `python3 scripts/check-memory-index-budget.py`. Expected: each rc 0 (inventory 0 or 3).
- [ ] **Step 3: Commit.**

**FAILS IF:** `check-docs.py` is red on the shortened spine; the closure reports a `gap:`; or Step 1's first
command prints nothing.

### Task 12: freeze the store — L1, both pins, the CI steps (the LAST task; addresses M1 parts 1 and 2)

**Files:**
- Modify `docs/dashboard-entries.md` (header lines 3–6 only)
- Modify `scripts/check-ask-store.py` (`LEGACY_STORE_REL`, `LEGACY_STORE_SHA256`, `LEGACY_STORE_BLOB`,
  `LEGACY_STORE_BASE_BLOB`, `legacy_store_problem`, `cutover_problem`, `PR_LIST_LIMIT`, `store_edit_prs`,
  `main`), manifest, pin `63`
- Modify `.github/workflows/ci.yml` (the gate steps; the `fetch-depth: 0` comment reworded to name F1 and L1's
  diff), `scripts/check-merge-ready.py` (the replayed step also runs C1)

**Interfaces:**
- `legacy_store_problem(head_blob: str | None, head_bytes: bytes | None, diff: Callable[[str, str], str | None]) -> str | None`
  — pure. `None` when `sha256(head_bytes) == LEGACY_STORE_SHA256`. Otherwise a message holding, in order:
  what differs (the first 40 lines of `diff(LEGACY_STORE_BLOB, head_blob)`, or "the diff could not be
  printed" when `diff` returns `None`), then the two literal commands
  `git diff <LEGACY_STORE_BLOB> <head_blob>` and
  `git cat-file blob <LEGACY_STORE_BLOB> > docs/dashboard-entries.md`.
- `cutover_problem(ref_blob: str | None) -> str | None` — `None` when `ref_blob == LEGACY_STORE_BASE_BLOB`,
  else a message naming both blobs and saying: merge master in, re-run C1, re-pin all three constants.
- `main`: L1 runs in BOTH modes (with and without `--base`), reading
  `git rev-parse HEAD:docs/dashboard-entries.md` and `git cat-file blob`. `--cutover-check REF` runs only
  `cutover_problem(git rev-parse REF:docs/dashboard-entries.md)` — REF is any revision, so `<sha>^1` works.
- `PR_LIST_LIMIT = 1000`; `store_edit_prs() -> tuple[list[str], str | None]` — `gh pr list --state open
  --limit PR_LIST_LIMIT --json number,headRefName`, then `gh pr diff <n> --name-only` per PR; returns one
  `PR <n> (<branch>) edits the frozen store` line per PR whose diff names `docs/dashboard-entries.md`. Any
  non-zero rc, an unparseable list, or a list of exactly `PR_LIST_LIMIT` entries (there may be more) is
  `err`. `--list-store-prs` prints the lines and returns 0, or `CANNOT RUN — … Treat this as NOT CHECKED.`
  rc 2. It exists for Task 13 and leaves in Task 16 (r1 Codex M1).

**Enumerated behaviors:**

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 12.1 | the pinned bytes pass | fixture store, pins computed from it | `None` |
| 12.2 | a missing store is refused | `head_bytes is None` | a problem |
| 12.3 | an appended entry is refused and shown | pinned bytes + one entry; `diff` returns the added lines | the message contains the stray entry's text |
| 12.4 | one edited byte of an old entry is refused | one byte flipped | a problem |
| 12.5 | the message carries the restore command by BLOB | 12.3's message | contains `git cat-file blob <LEGACY_STORE_BLOB> > docs/dashboard-entries.md` and no commit id |
| 12.6 | a pinned blob absent from the clone is still refused | `diff` returns `None` | a problem saying the diff could not be printed |
| 12.7 | the printed restore command repairs the tree | impure: fixture repo; commit an appended entry; run the printed command; commit | L1 red before, green after |
| 12.8 | master's store moved since the pin is refused | `cutover_problem("<another blob>")` | a problem naming both blobs |
| 12.9 | master's store unchanged passes | `cutover_problem(LEGACY_STORE_BASE_BLOB)` | `None` |
| 12.10 | push mode runs L1 | impure: `main([])` over a tree with an appended entry | rc 1 |
| 12.11 | the two HEAD pins describe the store on disk | the file at `ROOT / LEGACY_STORE_REL`: `git hash-object -- <path>` and `hashlib.sha256` of its bytes — no `HEAD`, no `rev-parse`, so no repository is needed | equal to `LEGACY_STORE_BLOB` and `LEGACY_STORE_SHA256` |
| 12.12 | the cutover check reads the revision it is given | impure: fixture repo, commit A (store = pinned base), commit B appends an entry, commit C on top; `--cutover-check C^1` and `--cutover-check A` | rc 1 for `C^1` (B's store), rc 0 for `A` |
| 12.13 | a PR beyond gh's default page is listed | `subprocess.run` stubbed: `gh pr list` returns `min(<--limit>, 31)` PRs (30 when `--limit` is absent), PR 31's diff names the store | PR 31 listed |
| 12.14 | a full page is CANNOT RUN | the stub returns exactly `PR_LIST_LIMIT` PRs | `err` names the limit |
| 12.15 | a failed `gh pr list` is CANNOT RUN, never "no PRs" | `gh pr list` rc 1 | `err is not None`; `--list-store-prs` rc 2 |
| 12.16 | a failed `gh pr diff` is CANNOT RUN, never "no edit" | PR 7's diff rc 1, PR 8's lists the store | `err` names PR 7, rc 2 |

- [ ] **Step 1: Write 12.1–12.16** against a fixture store (the constants patched in the case, as other
  suites patch theirs; 12.13–12.16 through `_with_run`) — 12.11 alone patches nothing: it reads the
  constants as committed against the store file on disk (r2 Codex M3: 12.11 was expected red in Step 3
  without ever being written). ⚠ **12.11 reads no git history (r3 Claude M1, M2).** `git hash-object <path>`
  needs no repository (measured 2026-11-24 in a copy with no `.git`: rc 0, and the blob equals
  `git rev-parse HEAD:docs/dashboard-entries.md` in this checkout), and `docs/` is in `HARNESS_TREE`, so it
  runs in the mutation harness's staged tree. It has NO base half: `LEGACY_STORE_BASE_BLOB` is master's
  store at pin time, which after S2's squash master no longer holds, so any self-test reading of it would go
  red on master from S2 until Task 16 deletes the constant. That pin is checked where its subject exists —
  Step 6's and Step 10's `--cutover-check origin/master`, which return 1 on a base blob other than the
  store they read (12.8, 12.12). After the squash that pin has no subject left on master; what holds from
  then on is L1 over master's tip (Task 13 Step 1).
  **Step 2: Run** the self-test (FAIL, 12.11 among the names).
- [ ] **Step 3: Implement** `legacy_store_problem`, `cutover_problem` and `main`, with the three constants
  set to a placeholder that 12.11 refuses (`"UNPINNED"`). Run: 12.1–12.10 and 12.12–12.16 PASS, 12.11 FAIL.
- [ ] **Step 4: Merge master in for the last time**, as ONE command that completes or aborts:
  `git merge --no-edit origin/master`. Name that master commit in the commit message, for a reader — no
  code reads it (12.11 has no base half; r3 Claude M2).
- [ ] **Step 5: C1 on the merged tree:** `python3 scripts/gen-dashboard.py --assert-no-open-asks`. Expected
  rc 0. On rc 1, re-ask each named ask as a file in `docs/asks/`, answer it in the old store on master
  through its own PR first, and return to Step 4.
- [ ] **Step 6: Pin.** Before the header edit: `git rev-parse origin/master:docs/dashboard-entries.md` →
  `LEGACY_STORE_BASE_BLOB`. Rewrite header lines 3–6 (a frozen record; new asks live in `docs/asks/`). Then:

```bash
git hash-object docs/dashboard-entries.md
python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" docs/dashboard-entries.md
```

  The two outputs are `LEGACY_STORE_BLOB` and `LEGACY_STORE_SHA256`. Commit the store and the gate file
  together, then run the self-test: 12.11 PASS; and `python3 scripts/check-ask-store.py --cutover-check
  origin/master` rc 0 — the base pin's own check, made while master still holds that store.
- [ ] **Step 7: CI.** Replace the PR-only `dashboard entry ratchet` step and its PR-body file:

```yaml
      - name: ask store (pull request)
        if: github.event_name == 'pull_request'
        run: |
          python3 scripts/check-ask-store.py --base "origin/$GITHUB_BASE_REF"
          python3 scripts/gen-dashboard.py --assert-no-open-asks
      - name: ask store (push)
        if: github.event_name == 'push'
        run: python3 scripts/check-ask-store.py
```

  The push-mode step runs on `batch/**` as well as `master` (ci.yml's `on.push.branches`), and that is
  intended (r1 Claude m5): a batch branch is master plus ready PR heads, so a batch carrying a store edit is
  red exactly as that PR would be. No `if:` on the ref.

- [ ] **Step 8: 10 mutations:** "L1 compares nothing" (expects 12.3), "a missing store passes L1" (12.2),
  "the restore command is dropped from L1's message" (12.5), "push mode skips L1" (12.10), "the cutover check
  accepts any blob" (12.8), "the cutover check reads HEAD instead of REF" (12.12), "the PR list keeps gh's
  default limit" (drop `--limit`; 12.13), "a full page passes" (12.14), "a failed PR list reads as no PRs"
  (12.15), "a failed PR diff reads as no edit" (12.16). Sweep, resolve.
- [ ] **Step 9: Slice gate.** `gen-dashboard.py`, `goal-tree.py`, `compaction-state.py`, `brief-compose.py`
  self-tests and `check-explainer-delivery.py`, `check-docs.py` — all rc 0. Then, committed:
  `python3 scripts/check-ask-store.py --base origin/master` prints `ok — `.
- [ ] **Step 10: Immediately before the squash** (the coordinator's step, after review and green CI):

```bash
git fetch origin master
python3 scripts/check-ask-store.py --cutover-check origin/master
```

  Expected: rc 0. On rc 1 a PR merged an entry after the pin: return to Step 4 and re-pin all three.
  ⚠ **This check is early, not sufficient (r1 Codex M2):** master can move between it and the squash, and
  `--match-head-commit` pins the PR head, not the base. The binding check is Task 13 Step 1: push-mode
  L1 over master's tip after the squash. A store that moved inside the window leaves the squash's own store
  different from the pinned bytes, so L1 is red on it — no window is left, and no commit has to be found.

**FAILS IF (L1):** the store at HEAD differs from the pinned bytes, or is missing, and the step is green —
on a pull request or on a push to master. **FAILS IF (M1 part 2):** master's store moved between the pin and the
squash and Task 13 Step 1 — push-mode L1 over `origin/master` — returns 0 (behavior 12.10 is that check on a
fixture; 12.12 holds Step 10's early check to the revision it is given).

### Task 13: the post-merge cutover (M1 part 3) — the coordinator's, outward-facing

No file changes. Run once, right after S2's squash lands. The code it runs is `check-ask-store.py
--post-cutover` (`post_cutover`), built and tested in S2 (backlog #730).

⟳ **SPLIT route taken (r5, backlog #730) — and DONE.** Round 5 found Medium/Low defects in this task's
shell (Step 1's exit 1 meant three things; a dirty worktree was not excluded) — the Phase 6 review's
falsifier. So the steps were not patched again: Steps 1, 2, 4 and 5 are now ONE tested entry point,
`--post-cutover`, with one case per backlog #730 finding and a mutation per case. Step 3 (the per-PR
repair) stays by hand: it writes to other branches, which a gate must never do.

⛔ **The shape rule for this task** (Phase 6 review,
`docs/reviews/architecture-review-2026-11-24-dashboard-retire-cutover.md`): this task has no builder, no PR
and no case, so nothing checks its text before it runs once, on master. So every command below is ONE call
of a tested entry point of `check-ask-store.py`, run in ONE shell call, and that call's own exit status is
the answer — read from the `post-cutover rc N` line it prints last, never from the shell's `$?`. No shell
variable is carried from one step to the next (the coordinator's shell calls share no state), and no step
identifies the squash commit. ⟳ backlog #730 r1 F3: the ONE worktree is Step 1's own — a fresh, detached
worktree of `origin/master` built and removed inside that one call, so no prior state (a missing path, a
local edit blocking a checkout) can collide with it. **A step that needs more than that is code for the gate
file, with a case and a mutation — never more shell here.**

- [x] **Step 1: the whole cutover check, one command.** ✅ 2026-11-26 08:37: `post-cutover rc 0` on master `829660eb` (CI run 45858774949).

```bash
git fetch -q origin +refs/heads/master:refs/remotes/origin/master && d="$(mktemp -d)/pc" && git worktree add -q --detach "$d" origin/master && (cd "$d" && python3 scripts/check-ask-store.py --post-cutover); git worktree remove --force "$d"
```

  Run it from any checkout of this repository. ⛔ **The status is N in the LAST line the script prints,
  `post-cutover rc N` — never the shell's `$?`** (r1 F3: a failed `cd` or `checkout` exits 1, which is this
  table's "the store moved", and the trailing `worktree remove` sets `$?` anyway). **No `post-cutover rc N`
  line means the check did not run** (the fetch, `mktemp` or `worktree add` failed, or the script crashed):
  NOT CHECKED, never a pass — read the error, fix it, re-run. A fresh worktree has no local edit, so the
  gate it runs is `origin/master`'s own (rc 4 cannot come from a stale copy), and before the squash it holds
  no gate file, so `python3` cannot open it and no rc line is printed: that is "S2 not merged" too.

  `--post-cutover` fetches `origin master` itself and reads only COMMITTED objects of `origin/master`
  (`git ls-tree` / `git cat-file`), never the working tree, so a dirty worktree cannot move its verdict
  (case "730 L1: a dirty worktree …"). It refuses to judge with a gate copy that is not master's: the
  running script's blob id must equal `origin/master`'s `scripts/check-ask-store.py` blob, else rc 4 (case
  "730 L1: a running gate that is not master's blob …") — which is why the command runs from a fresh
  detached worktree of `origin/master`, and why a local edit to the gate cannot be the judge. In order it checks:
  L1 (the store is the pinned bytes), A1 (`docs/asks/` is well-formed), the open PRs that still edit the
  store (Task 12's `store_edit_prs`; an empty `gh pr diff` answer is CANNOT RUN), and master's CI: the CI
  run on the fetched head commit — the newest `CI` push run on `master` whose `headSha` IS the fetched
  `origin/master` commit, listed whatever its status — must be `completed`, and the run's conclusion, the
  `verify` job's conclusion, and both `check-ask-store self-test` and `ask store (push)` in that job must be
  `success`; read-only `gh run list` / `gh run view`. ⟳ r2 G1–G3: a run on any other commit never answers,
  though it carry S2's gate (S2's own squash does); the head's run not yet listed, or listed and not
  completed, is rc 8. ⟳ r1 F1: in `verify` an earlier red step marks the later ones `skipped`, which is what
  a red run looks like, so `skipped`, `cancelled`, `failure` or absent — of a step, the job or the run — is
  red. Each check prints one `ok — ` / `REFUSED (rc N) — ` / `CANNOT RUN — ` line;
  the last line is `post-cutover rc N`.

  | rc | means | do |
  |---|---|---|
  | 0 | all four green | done — Task 13 is complete |
  | 1 | master's store moved off the pins; the message prints the stray text and `git cat-file blob <LEGACY_STORE_BLOB> > docs/dashboard-entries.md` | repair in a PR of its own: run `python3 scripts/gen-dashboard.py --assert-no-open-asks` in this checkout, re-ask each id it names as a file in `docs/asks/`, restore the store with the printed command. The pins stay |
  | 2 | CANNOT RUN — git or `gh` could not answer (fetch, cat-file, `gh pr list`, `gh run list`/`view`) | NOT a pass: fix the cause, re-run |
  | 3 | S2 IS NOT MERGED — `origin/master` has no gate file, or one without L1. Nothing else was checked | wait for the squash, re-run |
  | 4 | the running gate is not `origin/master`'s blob | re-run from a clean detached checkout of `origin/master` |
  | 5 | A1 refuses `docs/asks/` on master | fix the named ask file in a PR |
  | 6 | an open PR still edits the store; each is named | Step 2 |
  | 7 | the CI run on the fetched head commit is completed and not green: the run, its `verify` job or one of the two steps is not `success` (failure, skipped, cancelled or absent); the line names each | read that run; repair as rc 1 |
  | 8 | the CI run on the fetched head commit is not listed yet, or not completed | wait for it, re-run |

  When several checks refuse, rc is the first in the order 1, 5, 6, 7, 8; a CANNOT RUN is reported as rc 2
  only when nothing refused, and every line is printed either way.
- [x] **Step 2: For each PR Step 1 named (rc 6)** (✅ none owed: Step 1 returned rc 0, so no PR was named), in its worktree: merge master (`git merge --no-edit
  origin/master`), restore the store (`git checkout origin/master -- docs/dashboard-entries.md`), re-ask any
  question its dropped entry held as a file in `docs/asks/`, commit, push. Its CI now runs under L1.
- [x] **Step 3: Re-run Step 1's command.** ✅ rc 0 on the first run (2026-11-26 08:37, run 45858774949 on `829660eb`), so no re-run was owed. Expected: rc 0 (rc 8 means only that the CI run on the fetched
  head commit has not completed yet — re-run).

**FAILS IF:** Step 1 returns 0 while the store at `origin/master` differs from the pinned bytes, while an
open PR still edits the store, or while the CI run on the fetched head commit is absent, not completed, or has
its conclusion, its `verify` job's conclusion, `ask store (push)` or `check-ask-store self-test` anything but
`success` (a run whose L1 step was skipped by an earlier red is red); or a later push to master turns `ask store (push)` red (then the repair is 12.7's command,
taken from the step's own output, in a PR of its own).
**Test:** the twenty-six `730 …` impure cases of `check-ask-store.py --self-test`; each but three has a
mutation in `scripts/mutations/check-ask-store.json` that turns exactly it red: M1 (rc 0, 1, 2, 3, 5 kept
apart), L1 (the dirty worktree, the stale judge), Step 2's listing (rc 6), L2 (a failed `gh run list` is
rc 2), and `main`'s dispatch; the r1 fold's: F1 (GitHub's real step shapes — the head's self-test red with
the L1 step skipped over an older commit's green, the L1 step skipped in a green job, the self-test absent,
all rc 7), F6 (only `verify`'s steps count), F2 (`gh pr list`, `gh run view`, and git failing on master's
store or an ask, all rc 2), F4 (an empty `gh pr diff`), F5 (the fetch's explicit refspec); and the r2 fold's:
G1 (a green run on an earlier commit carrying the gate is rc 8), G3 (the head's run in progress over an older
commit's green is rc 8), G2 (the `verify` job failed in a run concluded `success`, and the run failed in
another job, both rc 7), and the newest of two runs on the head commit judged. The three without a mutation
of their own: M1's rc 0 (the all-green world, which a mutation breaking any clause turns red with others),
F1's head-red-over-older-green, and G2's run cancelled after both steps succeeded (the last two refused by
more than one clause, so no single mutation turns either alone red).
Not driven by a case: the Step 1 shell line itself (it is read by its last line, above). Behind them: 12.10 is push-mode L1 (mutation "push mode skips L1"); 12.3 is
L1's comparison itself (mutation "L1 compares nothing" — Task 12 Step 8 binds it to 12.3, and so does this
line; backlog #730 L3); 12.13–12.16 are the PR listing (a PR past gh's default page, a full page, a failed
list, a failed diff); 12.7 is Step 2's repair — a branch carrying an appended entry is red under L1, and the
printed command makes it green.
**FAILS IF (the shape rule):** a review of this task finds a defect in shell written here. Then the task is
not patched again: its steps become one entry point of the gate file with its own cases (the review's
*SPLIT* route).

---

# Slice S3 — delete the page

Branch `dashboard-retire-s3` from `origin/master` after S2 merges and Task 13 is done.

### Task 14: the contrast formula moves; the theme check gets a new subject

**Files:**
- Modify `scripts/page_chrome.py` (gains `_luminance(colour: str) -> float` and
  `contrast_ratio(fg: str, bg: str) -> float`, moved byte for byte from the generator, with cases)
- Modify `scripts/brief-compose.py` (`_contrast` calls `page_chrome.contrast_ratio`; the comment naming the
  generator's `CONTRAST_MIN` is reworded; `_DASHBOARD` and its lazy load are deleted)
- Modify `scripts/check-theme-token-coverage.py` (`PAGE_SRC` → `scripts/goal-tree.py`; a reader for a CSS
  block), `scripts/goal-tree.py` (the light block gains two tokens)
- Modify `scripts/mutations/page_chrome.json` (+3, pin `117`), `check-theme-token-coverage.json`, pins

**The theme check's new reference — decided here (spec §4.2 left it open), measured 2026-11-24:** no
surviving generator has a `light_vars = (…)` assignment; each declares its light palette as a
`:root[data-theme="light"]{…}` block. `scripts/goal-tree.py` is the page that absorbs the asks and is
composed through `brief-compose.py`, so the shim applies to it. Its light block covers 9 of the shim's 11
tokens; `--structure-bg` and `--structure-br` are missing (the goals and features pages miss
`--structure-br`). So this task adds both tokens to the goal tree's light block, with the values the
dashboard's `light_vars` gives them, and `KNOWN_GAP` stays empty.

**Interfaces:** Produces `css_block_tokens(text: str, selector: str) -> set[str]` in the theme check — the
tokens declared with a colon inside the first `selector{…}` block; RAISES `ValueError` when no block matches
(so `main` stays CANNOT RUN rc 2, as `palette_tokens` does today).

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 14.1 | black on white is 21 | `contrast_ratio("#000000", "#ffffff")` | `21.0` (2 dp) |
| 14.2 | the ratio is symmetric | swap the arguments | equal |
| 14.3 | a second pair pins the formula | `contrast_ratio("#1b2024", "#1d1c22")` | `1.03` (2 dp; the 2026-09-01 defect) |
| 14.4 | a three-digit and a malformed colour | `"#fff"`; `"red"` | as the moved code answers today — copy its two existing cases |
| 14.5 | brief-compose asks page_chrome | `_contrast` with `page_chrome.contrast_ratio` patched | the patched value |
| 14.6 | the goal tree's light block covers the shim | live run of the theme check | rc 0, `KNOWN_GAP` empty |
| 14.7 | a missing light block is CANNOT RUN | `css_block_tokens("", …)` | raises `ValueError` |
| 14.8 | a token only mentioned is not declared | `var(--card)` inside the block, no `--card:` | not in the set |

- [ ] **Steps 1–4:** cases; red runs of `page_chrome.py`, `brief-compose.py` and
  `check-theme-token-coverage.py` self-tests; implement; green. The generator keeps working until Task 15 by
  importing the two functions from `page_chrome`.
- [ ] **Step 5: 3 mutations in `page_chrome.json`:** "the luminance weights are swapped" (expects 14.3), "the
  ratio stops ordering lighter over darker" (14.2), "the 0.05 flare term is dropped" (14.1). Re-point the
  theme check's 4 entries to the new reader's anchors. Sweep both scripts, resolve, commit.

**FAILS IF:** `brief-compose.py --self-test` is green with `page_chrome.contrast_ratio` stubbed to `21.0`;
or the theme check passes while the goal tree's light block omits a shim token.

### Task 15: K8's scanner, then delete the page, its hook and its rows

**Files:**
- Create: `scripts/check-retired-references.py`, `scripts/mutations/check-retired-references.json`, its pin,
  its `scripts/sweep-costs.json` row, and two CI steps (`--self-test`, and the live scan)
- Create: `docs/explainers/dashboard-archive.html` (a small record page, the work-lines precedent)
- Delete (back each up to the scratchpad first): `scripts/gen-dashboard.py`,
  `scripts/mutations/gen-dashboard.json` and its pin and cost row, `.claude/hooks/regen-dashboard.sh` and
  its `command` in `.claude/settings.json`
- Modify: `scripts/explainer-serve.py` (`REGENERABLE` and `PAGE_SOURCES` lose `dashboard`; `RETIRED_FILES`
  gains `"dashboard.html": "/dashboard-archive"`), `scripts/check-page-links.py` (`PAGES`, `CI_PAGES`,
  `HREF_LITERAL`, `HOME_PATHS`), `scripts/page_markup.py` (`key_link` loses the `dashboard` kind;
  `ENTRY_SLUG` if nothing else uses it), `scripts/regen-pages.py`, `scripts/regen-pages.sh`,
  `.claude/hooks/regen-pages.sh`, `scripts/check-fixture-variation.py` and the other guard tables that name
  the generator, `.github/workflows/ci.yml` (the generator's self-test step, C1's line, the
  check-page-links comment: three CI pages), `docs/marketplace/components.json` + the regenerated
  `shipping-sets.json` (`gen-dashboard` and `hook-regen-dashboard` leave), `docs/portable-practices.md`
  (the hook list), `docs/dev-process.md` (its `regen-pages` wording if it names five pages)
- Modify two self-test fixtures that hold `"scripts/gen-dashboard.py"` as an arbitrary script path in a list
  (r1 Claude m4; K8's scanner visits list elements and would refuse them): `scripts/check-review-decision.py`
  (the case "a harness script is no longer assumed contained") and `scripts/gen-goals-page.py` (the
  `annotate_code` fixture `_shown`). Rename each to `scripts/gen-backlog-page.py`, a live script, so the
  scanner needs no exemption for a retired name; each file's self-test count is unchanged

**Interfaces:** `check-retired-references.py` — `RETIRED_PATHS` (`gen-dashboard.py`,
`check-dashboard-entry.py`, `regen-dashboard.sh`, the `dashboard` skill directory), `RETIRED_ROUTE =
"/dashboard"`, `scan(root: Path) -> list[str]` (one sentence per finding: file, category, the literal), and
`main`: rc 0 `ok — …`, rc 1 listing findings, rc 2 `CANNOT RUN` when a file it must parse does not parse or
`.claude/settings.json` / a workflow is unreadable. Python sources are read with `ast` — string constants
that are call arguments, path-literal operands, list or tuple elements, and dict keys of `REGENERABLE`,
`PAGES`, `PAGE_SOURCES` — never by a name grep; comments and docstrings are not visited.

**Enumerated behaviors** (seeded in a scratch tree; each refused case is named for its category):

| # | Behavior | Seed | Expected |
|---|---|---|---|
| 15.1 | a `with_name(…)` load is refused | `Path(__file__).with_name("gen-dashboard.py")` | 1 finding, category `load` |
| 15.2 | `_sibling`, `_load` and `spec_from_file_location` loads are refused | one seed each | 1 finding each |
| 15.3 | a `ROOT / "scripts" / …` path literal is refused | `ROOT / "scripts" / "gen-dashboard.py"` | 1 finding |
| 15.4 | a hook command is refused | `.claude/settings.json` with `run-hook.sh regen-dashboard.sh` | category `hook` |
| 15.5 | a workflow run line is refused | `run: python3 scripts/check-dashboard-entry.py` | category `workflow` |
| 15.6 | an argv literal is refused | `["python3", "scripts/check-dashboard-entry.py", "--base", b]` in a gate table | category `argv` |
| 15.7 | a manifest file field is refused | `{"file": "scripts/gen-dashboard.py", …}` | category `manifest` |
| 15.8 | a page-table key is refused | `REGENERABLE = {"dashboard": …}`; the same for `PAGES`, `PAGE_SOURCES` | 1 finding each |
| 15.9 | a `key_link("dashboard", …)` call is refused | one call | category `link` |
| 15.10 | a literal href to the route is refused | `f'<a href="/dashboard#{slug}">'` in a generator | category `link` |
| 15.11 | prose and comments pass | a comment and a docstring naming `gen-dashboard.py`; a dated doc | 0 findings |
| 15.12 | the RETIRED_FILES row passes | `RETIRED_FILES = {"dashboard.html": "/dashboard-archive"}` | 0 findings |
| 15.13 | `/dashboard-archive` and `/dashboards` are not the route | hrefs to each | 0 findings |
| 15.14 | a script that does not parse is CANNOT RUN | a syntax error in a scanned file | rc 2 |
| 15.15 | `/dashboard` answers with the archive record | `explainer-serve` case: `retired_target("dashboard.html")` | `/dashboard-archive`, not a 404 |

- [x] **Step 1: Write the scanner's seeded cases** 15.1–15.14. **Step 2: Run** its `--self-test` (FAIL).
- [x] **Step 3: Implement `scan`.** **Step 4: Run** the self-test (PASS), then the LIVE scan. Expected: rc 1,
  listing exactly what this task and Task 16 must still remove — save that list; it is the work list.
- [x] **Step 5: Write 15.15** and the page-set cases (four regenerable pages; three CI pages), red.
- [x] **Step 6: Delete and repoint** every item of the Files list. Write the archive record page.
- [x] **Step 7: Run** `explainer-serve.py`, `check-page-links.py`, `page_markup.py`, `regen-pages.py`,
  `brief-compose.py`, `goal-tree.py`, `check-shipping-sets.py`, `check-review-decision.py`,
  `gen-goals-page.py` self-tests, `check-page-links.py --build --ci`,
  the closure check, and the LIVE scan. Expected: all rc 0 except the scan, which lists only gate-file items
  Task 16 owns.
- [x] **Step 8: Mutations for the scanner** — one per category that drops that category's visitor, each
  expecting its seeded case (8 entries), plus "prose is scanned" expecting 15.11. Pin `9`. Resolve
  (the deleted manifest must leave no pin behind: `python3 scripts/check-plan-code.py --self-test`).
- [x] **Step 9: Commit.**

**FAILS IF (K8):** a seeded reference of any category passes the scan; or the prose seed or the
`RETIRED_FILES` seed fails it; or the live scan is green while a load, hook, run line, argv, manifest field,
page-table key or literal link still names a retired thing.

### Task 16: shrink the gate, wire K8 into CI, close the slice

**Files:**
- Modify `scripts/check-ask-store.py`: delete `parse_entries`, `header_error`, `valid_date`, `HEADER`,
  `FLAG`, `BLOCK`, `_first_sentence` and its constants, `--cutover-check`, `cutover_problem`,
  `LEGACY_STORE_BASE_BLOB`, `--list-store-prs`, `store_edit_prs`, `PR_LIST_LIMIT`, and their cases (12.8,
  12.9, 12.12–12.16); manifest −18 (12 grammar + 6 cutover), pin `45`
- Modify `.github/workflows/ci.yml` (the live `check-retired-references.py` step), `CONTEXT.md`, the ADR-0015
  sentence and `.gitignore` only where a sentence would become false, `docs/roadmap-to-launch.md`,
  `docs/goal-threads.md`, `docs/backlog.md` (this work's row closed), the memory row
  `nothing-needs-you-must-read-the-dashboard` (reads the goal tree's NEEDS YOU count)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 16.1 | the gate still reads asks, decisions and waivers | the staying cases of Tasks 1, 2, 9, 12 | unchanged counts |
| 16.2 | L1 is still green | live run, no `--base` | rc 0 — nothing in S3 touches the store |
| 16.3 | the live scan is green | `python3 scripts/check-retired-references.py` | rc 0 |
| 16.4 | NEEDS YOU still shows an ask | Task 3's 3.2–3.6 | green |

- [x] **Step 1:** delete the grammar and its cases; run `check-ask-store.py`, `check-merge-ready.py`,
  `check-review-recorded.py`, `goal-tree.py`, `compaction-state.py` self-tests. Expected: rc 0.
- [ ] **Step 2:** manifests, pins, the anchor resolve, `--only scripts/check-ask-store.py` sweep.
  ⟳ S3 build: manifest 98 → 54, pin repinned. 14 left with the grammar and the base-blob check; 31 with
  `store_edit_prs` and `post_cutover` (backlog #730), deleted too after Task 13's one run answered rc 0 (the plan's
  45 predates #730). One of the 31 anchors in the staying `_ask_tree` and is kept, retargeted to a new case. The
  anchor resolve passes. The local `--only` sweep was NOT RUN (54 × ~9 s exceeds the 265 s call bound); the PR's
  CI shards run it, so this box stays unticked until they are green.
- [x] **Step 3:** add the CI step; run the live scan (16.3) and every `python3 scripts/check-*` docs step.
- [x] **Step 4:** `python3 scripts/check-ratchet-contract.py` — the new guard has a `--self-test`, no
  fail-open handler and a caller. Commit.

**FAILS IF:** the live K8 scan is red; or L1 is red; or any self-test in Step 1 changes a staying case's
result.

---

## Self-review (run 2026-11-24, by the plan's author)

| Spec part | Task |
|---|---|
| §2.3 ask file, `read_asks`, the bounded read | 1 |
| §3 A1, F1; m1, m3 | 2 |
| §2.4 question, options, warning; K4, K5 | 3 (and 10 for K4 after the cutover) |
| K6, the FIFO ask case | 4, 10 |
| §2.3c `/_stale`, `pages_for`, `SCOPE` | 5, 6 |
| C1 | 7, 12 (CI line), 15 (removed) |
| §1.2 loaders by filename; the rename | 8 |
| R1, R4, K7 | 9 |
| §3 doc rules, the skill (m2's teaching), §6 amendments, marketplace | 11, 15 |
| L1, the pin, M1 | 12, 13 |
| §4.1 deletions, R2, R3, the archive record, K8 | 14, 15, 16 |

Not built by this plan, by the spec's own scope: the ✍ tag styling (backlog #623, retargeted in Task 6);
W2–W4 of the architecture review beyond what §2.3c placed in S1.

Two places where the plan corrects a spec expectation with a measurement, both stated where they bite: the
contrast mutations do not move (none exists on the formula) and the theme check's new reference palette is
the goal tree's, which needs two tokens added.
