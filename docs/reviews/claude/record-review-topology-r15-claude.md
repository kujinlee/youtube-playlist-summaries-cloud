# Round 15 — Claude half — `record-review-topology` @ `dc9fe107` + uncommitted delta

**Two defects, both in the deliverable (`scripts/check-review-recorded.py`), both fail-opens, both
found by attacking the gate's CLASSIFIER and its second question rather than its diff.** The r14
repair itself is correct and complete: `diff_argv` is the only path-producing builder left, both
rename directions are closed, and I could not break them with copy detection, `diff.relative`, or a
case-only rename on a case-insensitive filesystem. The counts are all honest. The instrument is fine.
The gate is not.

**VERDICT: NOT CONVERGED** — H1 is the same class as r14's High (a fail-open in the gate this branch
ships) and it also falsifies a written r11 claim.

---

## H1 (High) — `docs/` is NOT prose in this repository: it holds two CI-executed gate scripts and the M4 manifest, so a branch changing them owes no review AND skips the final-tree question

**Claim.** `PROSE_DIRS = ("docs/",)` (`scripts/check-review-recorded.py:145`, rule at `:149-156`)
classifies every path under `docs/` as prose. Two of the fifteen schema gates *are files under
`docs/`*, and they are run by CI. A pull request that changes only them gets
`ok — no guarded path changed — a review round is not required`, rc=0 — and because
`second_question` (`:343`) short-circuits on `not guarded_changes(changed)`, the final-tree question
is not asked either. **Both halves of this gate go silent over executable CI gate code.**

**The subject, by name:**

| path | what runs it |
|---|---|
| `docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh` (217 lines) | `scripts/check-schema-gates.sh:30` — **gate 1/15** |
| `docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py` (1,084 lines) | `scripts/check-schema-gates.sh:33` — **gate 2/15** |
| `docs/superpowers/specs/m4/live-manifest.txt`, `t1-blast-radius.sql`, `seed-assertion-corpus.sql`, `accepted-additions.txt` | gates 10/15 and 14/15 read them as the expected-schema manifest |

`.github/workflows/schema-gates.yml:80-81` and `:103-104` list
`docs/superpowers/specs/2026-08-03-stable-blob-addressing/**` and `docs/superpowers/specs/m4/**` as
**path-filter triggers** — the workflow itself declares these paths to be gate subjects. This is not
parked spec material: **21 commits have touched them, the most recent being `31fc8a72` (PR #298),
merged into this branch's own merge-base**, and it edited `mutate-schema.py`.

**Measured.** In an isolated copy, importing the shipped module:

```
is_prose('docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py') = True
is_prose('docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh')  = True
is_prose('docs/superpowers/specs/m4/live-manifest.txt')                                = True
is_prose('docs/superpowers/specs/m4/t1-blast-radius.sql')                              = True

guarded_changes(all four) = []
verdict(...)         -> 0 | no guarded path changed — a review round is not required
second_question(...) -> (False, None)        # the final-tree question is never asked
```

**Failure scenario.** A branch weakens a mutation in `mutate-schema.py` — or relaxes a line in
`live-manifest.txt` so gate 10 stops noticing a schema object — and opens a PR. `check-review-rounds.py`
passes vacuously (zero rounds). `check-review-recorded.py` prints `ok` and exits 0. The schema-gate
code merges with no review round and no `NO-REVIEW:` declaration. That is precisely the 2026-09-09
night this file's `WHY THIS EXISTS` section was written against, reached through the classifier
instead of through the diff.

**Why this is not a pedantic scope quibble.** The docstring at `:129-144` does not merely pick a
denylist; it *argues* one, on a premise that is false for this repository:

> "A denylist of PROSE **can be completed**, because prose is the small set: `docs/`, and the handful
> of Markdown files at the root. So the default is GUARDED, a new path is obliged from the day it
> appears."

The set was never completed — `docs/` is not the small prose set here, and the guarded-by-default
property the paragraph sells does not hold inside it. A comment asserting a property the code lacks
is this branch's own named signature defect.

**And it falsifies a recorded review claim.** `docs/reviews/claude/record-review-topology-r11-claude.md:451-453`
states: *"`PROSE_DIRS`/`PROSE_FILES` … is a denylist, so a new top-level path is guarded by default;
`docs/` **searched for executable artefacts that would be wrongly exempt, none found**."* Two exist,
both are gates, both are named in a CI workflow's path filter. Re-deriving rather than inheriting
that claim is what found this.

**Fix sketch (not a hypothesis I verified end to end).** `is_prose` needs an exception list inside
the prose directory — the natural one is to reuse the two globs `schema-gates.yml` already declares,
so the two files cannot disagree about which `docs/` paths are gate subjects. A cheaper, blunter
version that is still correct in the safe direction: a path under `docs/` whose suffix is not
`.md`/`.txt`, or which carries the executable bit, is guarded. Either way it needs a case and a
manifest entry; the current suite has 17 `is_prose`/`guarded_changes` cases and not one of them
reaches inside `docs/`.

---

## M1 (Medium) — an EMPTY `NO-REVIEW:`, which question one explicitly REFUSES, fully waives question two

**Claim.** `verdict()` refuses a bare `NO-REVIEW:` with no reason — `:214-215`, pinned by the case
*"an EMPTY NO-REVIEW: is refused"* and by a manifest entry. `second_question()` applies a weaker rule
to the same marker: `if waiver is not None` (`:345`) accepts the empty string. When a review document
was added, `verdict()` returns 0 at its review-document branch (`:207`) and never reaches its own
refusal — so the empty declaration is never rejected anywhere, and it silently turns the final-tree
gate from CANNOT RUN into a pass.

**Measured, end to end**, in a throwaway repo (`lib/x.ts` edited, `docs/reviews/claude/s-r1-claude.md`
added, no verdict file — the ordinary "Codex round not yet run" state):

```
=== PR body: none  ===                       (control)
FAILED — CANNOT RUN — no Codex verdict was added by this branch, so whether any round
saw the code about to merge is UNKNOWN.
rc=2

=== PR body: "NO-REVIEW:\n" (bare marker, no reason) ===
ok — review recorded in this range: docs/reviews/claude/s-r1-claude.md
ok — NO-REVIEW:  — the final-tree question is WAIVED, not passed
rc=0
```

`reason_of("…NO-REVIEW:\n", "NO-REVIEW:")` returns `''`, not `None` — verified against the shared
`check-dashboard-entry.exemption_reason`, so this is the real parser's behaviour, not a stand-in.

**Failure scenario.** An author writes `NO-REVIEW:` on its own line with the reason on the next line,
or leaves a PR-template stub, while also filing the round's Claude half. The stale-round check — the
half this branch exists to add — is waived by a declaration the file elsewhere calls "not a
declaration", and the log line reads as a legitimate waiver (only a double space betrays it).

**Fix.** `second_question` should treat an empty waiver the way `verdict` does. One line, plus the
case that is currently missing: the suite cases `second_question(["lib/x.ts"], "master moved")` and
`second_question(["lib/x.ts"], None)` at `:996-1005` and nothing in between.

---

## L1 (Low) — `--pr-body-file` naming a missing file exits 1 with a traceback, not the documented CANNOT RUN 2

`main` reads the body file at `:741-742`, **outside** the `try` block added at `:748` for exactly this
class. Measured: `--pr-body-file <missing>` → `FileNotFoundError` traceback, `rc=1`.

The docstring's own `FAILS IF` list promises exit 2 for cannot-reach-the-subject, and the comment at
`:744-747` records this as an r1 Major already fixed *for the git calls* — *"'Cannot run' collapsing
into an ordinary failure is the exact shape this repo refuses"*. Fixed as an instance, one statement
short of the class.

**Not reachable from CI**: `.github/workflows/ci.yml:424` writes the file with `printf` in the same
step, so it always exists. Low on that basis, and it fails loud rather than open.

---

## Verified by execution and found clean

**The r14 repair (brief items 1, 2).**

* `diff_argv` is the only path-producing `git diff` left in the file. Enumerated every git
  invocation: `ls-tree` (`:455`), `merge-base --is-ancestor` (`:495`), `rev-parse
  --is-shallow-repository` (`:654`), `merge-base` (`:658`, `:718`), and three diffs, all through
  `diff_argv` (`:505`, `:663`, `:722`). `--diff-filter=A` is appended only under `added_only`.
* **Direction 1** — `lib/x.ts` renamed into `docs/`: gate now FAILS naming `lib/x.ts` (rc=1).
  **Control**: deleting `--no-renames` from `diff_argv` restores `ok — no guarded path changed`,
  rc=0. The flag is load-bearing.
* **Direction 2** — a review document relocated into `docs/reviews/<writer>/` alongside a code edit:
  q1 now passes on the relocated document. **Control**: without the flag it reports *"2 guarded
  path(s) changed and no review round was recorded"* — r14's Medium reproduced.
* **Third directions I went looking for, all held**: `diff.renames = copies` in the repo config
  (config cannot re-enable what the command line turns off); `diff.relative = true`; a **case-only
  rename** on this case-insensitive APFS volume (`lib/Widget.ts` → `lib/widget.ts` yields both paths
  and the gate fires on both); a path renamed *and* edited (scenario B did exactly that). Submodule
  and symlink handling is r4's, unchanged, and its cases still pass.

**Counts (brief item 4), all counted independently, not read off the subject's tallies.**

| declared | actual |
|---|---|
| `check-review-recorded.py --self-test  # 122` | 122/122 passed |
| `codex-review.py --self-test  # 85` | 85/85 passed |
| `check-plan-code.py --self-test` | 128/128 |
| `check-ratchet-contract.py --self-test` | 41/41 |
| `sum(EXPECTED_MUTATIONS.values())` declared 622 | 622, and **every per-file entry matches** its manifest |
| `check-review-recorded.json` 36 | 36 |
| `codex-review.json` 12 | 12 |

`check-fixture-variation` OK (513 parameters / 50 files) · `check-selftest-counts` OK (38 scripts,
each verified by running it) · `check-review-rounds` OK · `check-docs` OK · `check-anchors` OK ·
`check-guard-coverage --self-test` 37/37.

**Mutation honesty (brief item 3).** I applied all 48 entries of the two changed manifests
individually in an isolated copy, over a control proved green first: **0 survivors, 0 unattributed,
0 anchor-ambiguity**. Specifically the new `case_line` entry — `expect` =
`"the line keeps the canonical shape the harness documents: got=False"` — attributes exactly. Its
stability is real: the garbled tail is `: got=False` from a **boolean** case, so it embeds no `repr`
of a fixture and moves with no data. The sibling boolean case garbles to a *different* prefix
(`…and omits the parenthesis entirely…: got=False`), so the two cannot be confused. The
`--no-renames` entry attributes to *"the diff asks git NOT to pair a deletion with an addition"*.

*(Correction to my own method, recorded because the number was wrong before it was right: my first
attribution harness reported 17 unattributed entries. That was my bug — `expect` may be a **list**,
and I compared a list against a list of names. Re-run list-aware: 0 problems. The subject was never
wrong here.)*

**Regression (brief item 5).** `case_line`, `_load_fail_parser`, `reviewed_state`, `unredirected`,
`verdict_record`, `classify`, `tail_candidates`, `classify_verdict`, `second_question`, `round_tail`
— all untouched by this delta except `second_question`'s surrounding text, and all still killed and
attributed by their manifest entries.

**`docs/plugins.md`.** The stale `(63 cases)` is deleted rather than corrected, and no other live
prose copy of a `codex-review.py` case count exists. The only remaining occurrence is the dated
`35 -> 51` inside backlog row 68 — a historical record of what a merged PR did, not a claim about
today. Not filed.

## Claims I read but did not execute

The `schema-gates.yml` path filters and `check-schema-gates.sh:30,33` are read from source; I did not
run the schema gates (they need Postgres). That does not weaken H1 — the claim is that those files
are gate code and are named by the workflow, both of which are textual facts I quoted.

## Rules of engagement

Every script ran from an isolated copy at `…/scratchpad/iso` with its `.git` **pointer file deleted
and the deletion asserted**; scenarios ran in four throwaway `git init` repos under `…/scratchpad/lab`.
No `GIT_DIR`/`GIT_WORK_TREE`/`GIT_COMMON_DIR`/`GIT_INDEX_FILE` was ever exported. No mutating git ran
in the worktree; re-checked at the end — HEAD still `dc9fe107`, 20 `git status --short` entries,
identical to the start.

VERDICT: NOT CONVERGED
