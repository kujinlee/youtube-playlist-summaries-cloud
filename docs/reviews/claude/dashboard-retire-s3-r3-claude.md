Reviewed head: 073c9431048e176999822476a9342c3659773032

# Round 3 — `dashboard-retire-s3` — Claude half — the round 2 fold (`git diff d7cf5ed6 073c9431`)

Mandate: refute that the fold closes G1–G3 without opening a new hole. Result: G1 and G2 are closed as
specified, and G3 is closed in the docstring. There is one MINOR left over from round 1 (`*` lines), one
fix-induced MINOR overclaim (the sentence that hands G1 over to check-page-links), and two NITs. Nothing is
BLOCKER or MAJOR.

## G1 — `/dashboard#` back in check-page-links rule 2: CLOSED, behaves exactly as master

- `/dash(?:board)#` is a non-capturing group, not an optional one, so it matches exactly `/dashboard#`.
  `"/dash" + "board"` equals `"/dashboard"`. `built_hrefs` is byte-identical to master `829660eb`
  (I diffed the function).
- I ran 26 inputs through master's and the branch's `built_hrefs`: the four reviewer inputs, an f-string,
  and the near-misses `/dashboard`, `/dashboard-archive#x`, `/dashboards#x`, `/x/dashboard#x`,
  `/dashboard/#x`, `/dashboard?a#x`, `/DASHBOARD#x` and a `_self_test_x` body. Each ran both with and
  without a `# /goals` prefilter line. **All 26 results were the same on both versions.** No near-miss is
  accepted or refused differently.
- The K8 tuple moved into `_self_test_review_r1_inputs()`, and it is unchanged: 25 entries, `old == new`
  is True, and no `REVIEW_R1_INPUTS` reference is left. The move is needed. Run against the old
  module-level tuple, rule 2 reports `check-retired-references.py:349` and `:350` (`/dashboard#`). Rule 2
  over the real `scripts/*.py` at the head finds 0.
- Both new page-links mutations, applied by hand in the copy, kill their named case. Each turns the four
  G1 cases red, which is the same pattern as G4, declined in round 2.

## G2 — `_whole_line_comment`: CLOSED for `/*`; the `*` branch carried over from round 1 is still open (R3-1)

These were run through `_text_findings("app/x.ts", …, "//")`. `R` = `fetch("/dashboard");`.

| input | result | correct? |
|---|---|---|
| `/* a */ /* b */ R` | refused | yes |
| `/* a */R` | refused | yes |
| `*/` | passed | yes |
| `const s = "/*"; R` | refused | yes |
| `"/* x */ y" + R` | refused | yes |
| `/*/ R` | passed | yes (in JS, `/*/` opens a comment) |
| `/** gen-dashboard.py */`, `/* gen-dashboard.py */\t` | passed | yes |
| `*/ R` | **passed** | no |
| ` * R` (a multiplication continuation) | **passed** | no |
| `*gen() { R }` (a generator method) | **passed** | no |
| `/* a */ // gen-dashboard.py` | refused | false positive (NIT R3-4) |
| `/* a */ /* gen-dashboard.py */` | refused | false positive (NIT R3-4) |

The G2 mutation applied by hand turns exactly `G2 code after a closed block comment on its line is
refused` red.

## Findings

**R3-1 — MINOR — not fix-induced** (the `s.startswith("*")` skip dates from round 1, and the fold moved it
unchanged into `_whole_line_comment`). `scripts/check-retired-references.py:229`
(`return comment == "//" and s.startswith("*")`).
- Any `//`-kind line that starts with `*` is skipped, comment or not. Inputs above: `*/ fetch("/dashboard");`,
  ` * fetch("/dashboard");` and `*gen() { fetch("/dashboard"); }` all pass.
- **This can happen in live files.** CSS inside a TS template literal starts lines with `*`:
  `lib/html-doc/render.ts:22` and `lib/html-doc/render-dig-deeper.ts:29` (`*{box-sizing:border-box}`). A
  line like `*{background:url(/dashboard)}` there would pass.
- No live file holds a retired name on such a line today. A grep of every tracked JS/TS file for
  `^\s*\*/\s*\S` found nothing.
- The docstring does list "a `*` line" as not scanned, so it is disclosed. But it justifies the skip with
  "comments are not run", and that is false for these shapes.
- **Fix (or file):** skip a `*` line only when it is `*` alone, `*/` alone, or `* ` followed by text
  inside a block comment that is being tracked as open. The minimum fix is to treat `*/ code` the way G2
  treats `/* … */ code`, and to reword the docstring bullet so it states the bound.

**R3-2 — MINOR — fix-induced** (new sentence). `scripts/check-retired-references.py:50-51` says "For a
`/dashboard#` href, check-page-links rule 2 reads the joined value (G1)". The plan's K8-scope paragraph
says "is check-page-links rule 2's". Both claim more than rule 2 does. Rule 2 (`check_sources`,
`scripts/check-page-links.py:407-411`; `built_hrefs:200`) reads only:
- top-level `scripts/*.py`;
- outside `_self_test*` functions;
- excluding `page_markup.py` and `check-page-links.py`;
- and only a file that names a home path somewhere (the prefilter).

Input that passes both checks: a file whose only content is `h = "/dash" + "board#" + slug`. It also
passes on master, so this is parity with master and not a regression. The check-page-links comment
(`:104-106`) states the prefilter bound. The K8 docstring and the plan do not. **Fix:** add "in top-level
`scripts/*.py` that names a home path", or point to that comment.

**R3-3 — NIT — fix-induced.** The four short claims do not list the same exclusions:
- **Where:** backlog #736, roadmap S3 line, ok message (`:296-298`), plan K8-scope paragraph.
- **What they omit:** the `ALLOWED` literals, K8 itself, names joined at run time, `.css`/`.txt`, and an
  extensionless file with no `#!`. The docstring lists all five. None of the short claims says "only",
  so none of them is false, but they disagree with each other and with the docstring.
- **A wrong reason:** the plan and backlog say every exclusion is "because it holds history, not code".
  That is not the reason for whole-line comments, which are skipped because they are not run. It is also
  not true of every file under `docs/superpowers/`, which holds executable files:
  `docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py` and `verify-schema.sh`.
  The docstring's per-prefix reasons are accurate. The one-line summary is not.

**R3-4 — NIT — fix-induced, conservative direction.** A line that is all comment but opens with `/* … */`
followed by more comment is now refused: `/* a */ // gen-dashboard.py` and
`/* a */ /* gen-dashboard.py */`. These are false refusals, not false passes, and no live file has this
shape (the live scan is rc 0). No action needed.

## G3 — the claims: CLOSED in the docstring

The docstring's NOT SCANNED section matches the code:
- `_prose` skips every `Expr` string;
- `TEXT_SUFFIXES` and the `#!` rule decide the text kinds;
- `EXEMPT_PREFIXES` has five entries with reasons;
- `ALLOWED` is keyed by file;
- a run-time join is out of reach.

The remaining gaps are R3-2 and R3-3.

## Pins and the anchor resolve

- `scripts/check-page-links.py`: manifest 46 entries, pin 46.
- `scripts/check-retired-references.py`: manifest 16 entries, pin 16.
- The plan's anchor resolve (`docs/superpowers/plans/2026-11-24-dashboard-retire.md:56-73`), run in the
  worktree, printed `every anchor resolves exactly once` (rc 0).

## Gate lines (run in the worktree at 073c9431)

- `check-retired-references.py --self-test`: `73/73 passed` (rc 0)
- `check-retired-references.py`: `check-retired-references: ok — no scanned string constant, source or config line, page table or key_link names a retired thing (docstrings, whole-line comments, .md/.html/Makefiles and the exempt prefixes are not scanned)` (rc 0)
- `check-page-links.py --self-test`: `100/100 self-test cases passed` (rc 0)
- `check-plan-code.py --self-test`: `506/506 passed` (rc 0)
- `check-docs.py`: `Documentation integrity OK` (rc 0)

VERDICT: CONVERGED
