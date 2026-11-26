# Architecture review (Phase 6) — PR #644, dashboard-retire S3: what `check-retired-references` (K8) skips

- **Subject:** `scripts/check-retired-references.py` (K8), chiefly `_whole_line_comment` (`:221-229`) and its one
  caller `_text_findings` (`:232-240`), and the sentences in four documents that say what K8 does not read.
- **Armed by:** THRASHING. `python3 scripts/check-review-decision.py` at `17feed6f` prints **[M]**
  `ARCHITECTURE_REVIEW — thrashing: 'check-retired-references' carried fix-induced findings in r2 and r3`.
- **Read first:** `CONTEXT.md`, `docs/adr/` (ADR-0014 bears on the guard's shape; K8 drives `main` through `--root`),
  `docs/review-method.md` (the stop condition, *can a redesign remove it?*, the arming condition), the three
  coordinator round documents, the Claude half of round 3, backlog row 740, and K8 at the head in full.
- **Changed by this review:** this file only. No code and no other document.
- **Tagging:** **[M]** = measured by me (a command run, or code quoted). **[I]** = inferred, not measured.
- **Baseline [M]:** worktree head `17feed6f`. `check-retired-references.py`: rc 0. `--self-test`: 73/73.
  Mutation sweeps and the other gates were NOT run by me. Nothing on GitHub was read.
- **Instrument:** a differential probe over a byte copy of K8 in the session scratch directory, run against the
  worktree's `git ls-files`. Three scans of the text kinds are compared: K8 as it is; K8 with the comment skip
  deleted ("no-skip"); and K8 with a 30-line JS comment lexer in place of the line rule ("lexer"). The probe also
  counts what each of K8's exclusions passes over on the live tree.

## Conclusion

**The thrashing was half structural and half prose. The structural half has one cause, and deleting one function
and its call removes it. Nothing is needed before the merge. Backlog #740 carries it, with a different *Do*.**

1. **The structural half is the comment skip.** The round 1 fold replaced a list of reference forms with a token
   scan, and its docstring says why: "a text scan of a token cannot miss a syntactic form". The same fold added a
   list of comment forms to skip. G2, R3-1 and R3-4 are all entries missing from, or wrong in, that second list.
2. **The prose half is the prose floor.** G3, R3-2 and R3-3 are sentences. No reshaping of the scan removes a
   sentence, though fewer copies of it can disagree.
3. **The skip buys nothing on the live tree [M].** It passes over 16,566 lines, in the 670 files that have a comment marker. None of them names a
   retired thing. K8 with the skip deleted is rc 0 on the live tree.
4. **A per-language lexer is the wrong redesign [M].** The lexer prototype went out of step on a regex literal in a
   live file and misread 57 comment lines in 13 files as code.
5. **No hole on the live tree [M].** Because of point 3, K8's rc 0 at the head is the answer a scan with no comment
   rule at all gives.

**The observations that would make this conclusion wrong:**

- **A live hole:** a tracked line of a text kind that K8 skips and that names a retired thing. The probe counts
  zero. One such line that is not a comment makes the change a merge blocker.
- **A needed skip:** a text-kind comment that must name a retired thing and cannot be reworded. Then the deletion
  needs an allow-list entry for a line, which K8 does not have today (`ALLOWED` is keyed by Python string).

## 1. The finding chain, per finding

| Round | Finding | What it is | Caused by the previous fold? | Can a redesign remove it? | Kind |
|---|---|---|---|---|---|
| r2 G2 | `/* x */ fetch("/dashboard");` passes | a `/*` line was skipped whole | **yes** — the r1 fold added the skip | **yes** — no skip, no comment forms | mechanism |
| r2 G3 | "refuses ANY live reference" is wider than the scan | claims not narrowed when the scan gained exclusions | **yes** | no — any static scan has a bound that prose must state | prose |
| r3 R3-1 | a `//`-kind line starting with `*` is skipped whole | the `*` entry of the same skip | recorded as no; it is the r1 fold's, and the r2 fold repaired its neighbour and moved it unchanged | **yes** | mechanism |
| r3 R3-2 | two sentences overstate check-page-links rule 2 | a new sentence in the r2 fold | **yes** | no — it describes another check | prose |
| r3 R3-3 | four short claims list different exclusions; one shared reason is wrong | four restatements of the docstring's list | **yes** | partly — one list, cited, cannot disagree with itself | prose (duplication) |
| r3 R3-4 | `/* a */ // gen-dashboard.py` is refused | the G2 repair reads everything after `*/` as code | **yes** | **yes** | mechanism |

**Where the skip came from [M]** (`git show <sha>:scripts/check-retired-references.py`):

| Commit | The comment rule |
|---|---|
| `05c13928` (before round 1) | one test, `#` only, inside the hook-body reader |
| `200c97e0` (r1 fold) | `s.startswith(comment) or (comment == "//" and s.startswith(("/*", "*")))` |
| `073c9431` (r2 fold) | `_whole_line_comment`: three branches, the `/*` one looking for `*/` |

**The hole moved; it did not close.** Round 2 found the `/*` entry too wide. The fold narrowed it and left the `*`
entry beside it. Round 3 found the `*` entry too wide (R3-1) and the narrowed `/*` entry too strict (R3-4). That is
the shape the stop condition names.

**Severity fell while it thrashed [M]** (the coordinator documents, this component's rows): a High, a Medium and a
declined Low in round 2; four Low in round 3, one of them a false refusal. The arming condition does not look at severity.

## 2. The structural cause

**K8 was redesigned on one side only.** A check of this kind makes two lists: what counts as a reference, and what
counts as not one. Round 1 found thirteen forms missing from the first list, and the fold stopped keeping that list.
The second list was started in the same commit.

A line rule cannot say whether a line is a comment. That needs the state the line begins in (inside a block comment,
inside a template literal). K8 keeps no state, so each branch of `_whole_line_comment` is a guess from the first
characters:

| First characters | K8's guess | False when |
|---|---|---|
| `//` | comment | the line is inside a template literal **[I]** (no live case sought) |
| `/*` … `*/` then text | code | the text is another comment (R3-4) |
| `*` | comment | CSS in a template literal, `*/ code`, a multiplication, a generator method (R3-1) |

**Live instances of the `*` guess being false [M]:** `lib/html-doc/render.ts:22` and
`lib/html-doc/render-dig-deeper.ts:29`, both `*{box-sizing:border-box}` in a template literal. Neither names a
retired thing.

## 3. The redesigns, measured

**On constructed inputs [M].** 19 inputs: round 3's twelve, plus template literals, regex literals and a `//` inside a
string. "Want" is whether the line holds a reference that runs or is emitted.

| Design | False pass | False refusal |
|---|---|---|
| K8 at the head | 5 | 3 |
| lexer | 0 | 1 (`/['"]/; // gen-dashboard.py`: a quote in a regex literal) |
| no-skip | 0 | 7 (every comment that names a retired thing) |

**On the live tree [M].** 790 text-kind files: 622 with `//`, 48 with `#`, 120 with no comment marker.

| Measure | Value |
|---|---|
| lines K8 skips | 16,566 (`//` 8,389; `#` 3,855; `*` 3,547; `/*` 775) |
| of those, lines naming a retired thing | **0** |
| findings: K8 / lexer / no-skip | 0 / 0 / 0 |
| lines the lexer calls code that begin with `*` | 59 in 15 files |
| of those, lines not shaped like a comment continuation | 2 (the CSS lines above) |

**The lexer is not cheap.** The other 57 lines in 13 files are comments the lexer misread. I traced one file:
`lib/dig/cloud/write-dig-section-blob.ts:22` holds `.replace(/"/g, '\\"')`, and the lexer took the `"` in the
regex for a string opening **[M]**. The same cause in the other 12 files is **[I]**. Telling a regex literal from a
division needs a parser. A lexer that goes out of step can fail in either direction: `/[/*]/` would open a comment
that hides code **[I]**. So a lexer moves the hole to a rarer place and adds code. That is a third round of the same
thrash.

**No-skip is a deletion [M].** Removing the two lines `if comment and _whole_line_comment(s, comment): continue`
in the copy:

- the live scan stays rc 0;
- the self-test goes 70/73, and the three red cases are exactly the ones that assert a comment passes: `15.5`
  (its comment line), `15.11` (the hook, TS and workflow comments) and `G2 a block comment closed … passes`;
- every refusal case stays green, round 1's 25 inputs included.

**What no-skip costs.** A comment in a `.sh`, `.yml`, `.ts` or similar file can no longer name a retired thing. Zero
do today. The first one written gets a refusal naming its line, and the remedy is to reword it. Python is untouched:
`ast` never sees a Python comment, and docstrings stay unread.

**What no-skip does not touch [M].** The docstring exclusion: 17 whole-statement strings in 12 Python files name a
retired thing, so reading them is not free, and round 2 ruled that widening the scan there is not the fix. The kinds
never read: 134 lines in 17 `.md` files and 73 lines in 22 `.html` files name one. All are under `docs/` except
`CONTEXT.md:161`. No file under `.claude/` or `.agents/` outside the scanned kinds matches K8's patterns.

**For the prose half:** one list, cited. The docstring's NOT SCANNED section is accurate (round 3 checked it against
the code). The ok message can be built from `EXEMPT_PREFIXES` and `TEXT_SUFFIXES`. The three documents can point at
that section and stop listing. With the comment bullet gone, the wrong shared reason ("holds history, not code",
plan `:1039`) loses the case it was most wrong about.

## 4. Tried, and failed, to find a live hole

- **The comment skip [M]:** 0 of 16,566 skipped lines name a retired thing (§3).
- **Instruction files [M]:** no skill or command file tells an agent to run a retired script.
- **Help text [M]:** five module docstrings that `argparse` prints name a retired script. Two speak of it as
  history or as "retired". Three read as present tense: `scripts/check-review-recorded.py` ("`check-dashboard-entry.py`
  asks whether an entry was added"), `scripts/check-main-drivable.py` ("`check-dashboard-entry.py:1445` calls
  `main`") and `scripts/page_markup.py` ("Four generators — `gen-dashboard.py`, …"). `docs/round-header-template.md:61` does the same in an example. These are stale sentences of the kind
  round 1's F5 fixed. Nothing loads them. They are the bound G3 disclosed.

## 5. Decided this slice and not written down

- **A comment may narrate the retirement in a text kind.** The plan's cases 15.5 and 15.11 assert it. No file uses
  it. No-skip reverses that choice, so the fold of backlog #740 must say so where K8's scope is stated.
- **K8 has no end date [I].** It runs on every PR for five fixed names. Whether it is itself retired once the names
  are forgotten is not written anywhere I read.

## 6. For the coordinator

- **Before the merge:** nothing. The change in §3 is a fold, and round 3 filed its findings so that no unreviewed
  fold lands after the last fold round. That reasoning still holds.
- **Backlog #740, proposed *Do*:**

  > **Do:** delete the whole-line-comment skip from the text scan (`_whole_line_comment` and its call in
  > `_text_findings`), so every line of a text kind is read. Measured at `17feed6f`: none of the 16,566 lines the
  > skip passes over names a retired thing, and the scan without it is rc 0 on the live tree. Turn the comment
  > halves of cases 15.5, 15.11 and G2 into refusals, remove the G2 mutation (round 3 names it) and lower the pin, and
  > drop the comment bullet from NOT SCANNED. This removes R3-1 and R3-4. Do NOT add a JS lexer instead: a 30-line
  > one misread comments in 13 live files (architecture review 2026-11-26, §3). R3-2: state rule 2's reach by
  > pointing at check-page-links' own comment. R3-3: build the ok message's list from `EXEMPT_PREFIXES` and
  > `TEXT_SUFFIXES`, and have backlog #736, the roadmap S3 line and the plan cite the docstring's NOT SCANNED
  > section, with no list and no shared reason of their own. Also reword the present-tense mentions of
  > the retired scripts in the docstrings of `check-review-recorded.py`, `check-main-drivable.py` and `page_markup.py`,
  > and in `docs/round-header-template.md:61`.

- **Size:** the row stays S. The code change is a deletion.
