Reviewed head: 8ee4ee9f0f39d19802220c65a405caf09078df28

# compaction-watcher — round 3 — Claude half

**Subject:** `git diff origin/master...HEAD` on `compaction-watcher` (PR #527, backlog #537), at the head above, in the
worktree `.claude/worktrees/cbw`. Codex half: `REVIEW GAP: codex — alternation` (round 3 runs this half only).

**Bottom line.** I found no bypass in the rule as shipped. Every character the templates allow outside the verbatim
literals is `[A-Za-z0-9._/-]`, a leading `~` followed by `/`, the digits of N, and one optional space. Bash expands none
of these except the `~`, which becomes `$HOME`. So the path is one literal word and the rest of the command is a fixed
string. The defects are in what the tests pin down and in what the documents still say. F1 is a hole in the tests on
exactly the axis that has failed twice before (characters the path is allowed to contain). F2 is a backlog row that
still describes the round-0/1 rule.

## What I ran

| Check | Result |
|---|---|
| `python3 scripts/check-compaction-boundary.py --self-test` | **105/105 passed** at the head |
| `check-plan-code.py --mutate . --only scripts/check-compaction-boundary.py` | **CANNOT RUN — NOT CHECKED**: the worktree has no `node_modules/typescript` |
| The 17 watcher entries in `scripts/mutations/check-compaction-boundary.json`, applied by my own script to a temp copy of `scripts/`, with the expected case names checked against the `[FAIL]` lines | **17/17 killed**, each by the case it names. Every anchor occurs exactly once |
| 9 mutations of my own, on a temp copy | **5 SURVIVE** (F1, F6), 4 killed |
| Re-measured the corpus, all 185 top-level `*.jsonl` files, assistant and `api-request-blob` records | Per occurrence: **141/141 and 0/215 reproduce**. Per distinct `tool_use` id: **106/106 and 0/193** (F3) |
| The same measurement over subagent transcripts (`*/**/*.jsonl`, 531 files) | 1/1 watchers matched, 0/145 others |

## Bypass attempts (question 1)

None of these turned into a bypass:

- **`..`**: `/tmp/../tmp/x/explainers/questions.md` matches, and it is still one literal file. The same goes for
  **a symlinked directory, a symlink, or a FIFO** at that path. The rule decides by file NAME, so a CI log saved or
  linked as `…/explainers/questions.md` would be exempted. Doing that takes a deliberate act of naming a file, and no
  accidental watcher would look like it. See F5, a NIT about documenting this.
- **`-` as the first character of a segment** (`/-/explainers/questions.md`) matches, but the path always starts with
  `/` or `~`, so tail can never read it as an option.
- **`~user`** is refused: the `~` alternative must be followed directly by `/explainers`.
- **Huge N**: `tail -n 000099999999999999999 -F …` matches. On this macOS, `tail -n 99999999999999999999999999` exits
  1 with `illegal offset … Result too large`, so the Monitor ends at once. It is exempted, but no work runs. Leading
  zeros are harmless (`tail -n 000002` → 2 lines).
- **The verbatim awk and grep text**: the programs are fixed and single-quoted. awk reads only its stdin, and no
  template has a file argument after the program. The END anchor (`fullmatch`) is pinned by a mutation that I
  reproduced being killed.

## Regressions in round 2's change (question 2)

None found. Round 2 changed only `question_watcher` and the module constants. `scan` still sets
`"watcher": question_watcher(inp.get("command"))` once, when the Monitor's `tool_use` arrives, and `signals` still
skips `st["watcher"]`. Neither line changed in round 2: `git diff 2a92ecbf..HEAD` touches neither. `["watcher"]` is
read nowhere else, so nothing else needs the key (`grep -n '\["watcher"\]' scripts/*.py`). The plan and agent
branches, `decide`, `ceiling` and the TaskStop/notification closing paths are byte-identical to master. Their master
cases still pass among the 105.

## Findings

### F1 — MINOR — the path's character class is pinned only against glob and brace characters; widening it by a space or `$` survives

`scripts/check-compaction-boundary.py:131` (`WATCHER_PATH`). Its own comment says the class allows *"ONE file: no glob,
brace, quote, `$` or space"*. The cases at `:756` and `:822` test only the glob/brace part. The manifest's path-class
entry replaces the class with `[^ ]*`, so a space is never exercised, and a mutant that adds one is not caught.

**Failure scenario.** Suppose someone later widens the class to admit a space, or `$` to support `$HOME/...`. Nothing
goes red, and the exemption reopens in the same shape round 2 closed (R2-3):

- **With a space admitted:** `tail -n 0 -F /tmp/ci.log /x/explainers/questions.md 2>/dev/null | awk '<§5>'` is
  exempted. tail follows two files, and one of them is a CI log.
- **With `$` admitted:** `tail -n 0 -F /tmp/ci.log$IFS/explainers/questions.md …` is exempted. The unquoted `$IFS`
  word-splits the path into two files.

The existing "exactly ONE file" case (`:756`) appends the second path AFTER the template, where no mutant of the path
class can reach. The second path has to go INSIDE the path position.

**Evidence.** My mutations, each on a temp copy of `scripts/`:

| Mutation | Self-test |
|---|---|
| `[A-Za-z0-9._/-]*` → `[A-Za-z0-9._/ -]*` | **105/105 passed (SURVIVES)** |
| `[A-Za-z0-9._/-]*` → `[A-Za-z0-9._/$-]*` | **105/105 passed (SURVIVES)** |
| `(?:~\|/` → `(?:~[a-z]*\|/` (admits `~user`) | **105/105 passed (SURVIVES)** |
| the path class → `/.*` | 104/105 (killed) |

**Fix.** Add a negative case with the second path inside the path position, plus a `$VAR` path and a `~user` path:
`QW_CMD.replace("~/explainers", "/tmp/ci.log /x/explainers")`, `QW_CMD.replace("~/explainers",
"/tmp/ci.log$IFS/explainers")` and `QW_CMD.replace("~/", "~root/")`. Add one mutation entry per widening (a space,
`$`), and bump the pin.

### F2 — MINOR — backlog #537's "Fix" text still describes the round-0/1 rule

`docs/backlog.md:508`. The row says the fix exempts *"a Monitor whose command's FIRST stage is `tail [-n N] -F
<...>/explainers/questions.md` with nothing chained outside quotes"*. That was round 0/1's rule: a first-stage test
plus a quote-aware chaining scan. The shipped rule is 5 exact full-command templates. Two consequences:

- A reader of the backlog believes any filter chain is exempted. Under the shipped rule, a bare `tail -F` is NOT
  exempted (the BOUND case at `:807` asserts exactly that).
- The row's BOUND (*"this one in another shape, still blocks"*) is right, but the text above it contradicts it.

**Evidence.** Compare the row with `question_watcher`'s docstring (`:279`) and with `docs/dashboard-entries.md`'s
`<!--tech-->` block, which does describe the templates.

The docstring (`:51-60`), the dashboard entry and the goal-threads line are current. I checked the dashboard's
counts: 105 cases is +22 on 83, and 17 watcher mutations is 3 kept from round 0 plus 14 from round 2, which is
47 → 64.

### F3 — MINOR — "141 watchers / 0 of 215" counts duplicate records, not distinct Monitor calls

The claim appears at `scripts/check-compaction-boundary.py:54` (*"141 watchers"*) and `:133-138` (*"141 watchers, 5
shapes"*, *"S1: 136×"* and so on), in `docs/backlog.md:508`, in the dashboard entry, and in the r2 coordinator doc.

Each of the 57 `api-request-blob` occurrences has the same `tool_use` id as an assistant record already counted (57 of
57). So 35 of the 141 "watchers" and 22 of the 215 "others" are the same calls counted twice.

| Unit | Watchers matched | Others matched |
|---|---|---|
| Per occurrence (assistant + blob records) | 141/141 | 0/215 |
| Per distinct `tool_use` id | **106/106** | **0/193** |
| Distinct command strings | **5** (all 5 match) | 0/186 |

The conclusion still holds in every unit. The wording, though, gives a sample about 1.3× its real size, and that
number is the one quoted as support for *"141 watchers, 5 shapes"*. It also hides that the corpus holds exactly 5
distinct watcher strings, and that the "path and N vary" generalisation has 2 real paths behind it.

**Fix.** Say *"141 Monitor records (106 distinct calls, 5 distinct commands)"*, or count by id.

### F4 — NIT — the pin's comment stops at round 1's count

`scripts/check-plan-code.py:2674`. The comment ends at *"55 - 5 + 18 = 68"*, but the pin is `64`. Round 2's line is
missing: *"r2 fold: the 18 shlex-clause entries retired, 14 added, one per template clause. 68 - 18 + 14 = 64"*. A
reader who checks the arithmetic finds a pin that disagrees with its own comment.

### F5 — NIT — the BOUND does not say the file is identified by name only

`scripts/check-compaction-boundary.py:131` and the docstring BOUND at `:58-60`. A `..` segment, a symlink, or a FIFO
named `…/explainers/questions.md` is exempted whatever it actually carries.

**Failure scenario.** This happens only if a CI log or an event FIFO is deliberately placed at that name. No accidental
watcher looks like that, so a code fix is not warranted. One clause in the BOUND would stop a later reviewer from
re-deriving it: *"the path is matched as a name; what it resolves to is not checked"*.

### F6 — NIT — `~` admits only `~/explainers/…`, which the docstring's "`~` or `/...`" can be misread against

`scripts/check-compaction-boundary.py:131`. `~/repo/docs/explainers/questions.md` is NOT matched (measured: False),
because the `~` alternative is bare. This fails safe, and no transcript has that form (paths in the corpus:
`~/explainers/questions.md` 105×, one absolute path 1×). Still, the docstring's *"path (`~` or `/...` of
`[A-Za-z0-9._/-]` …)"* reads as if `~/...` took the class too.

Two related mutants survive: N may be empty (`[0-9]*`), and an unescaped `.` in `questions\.md`. Both are harmless:
the first makes tail read `-F` as its count and exit with an error; the second only admits `questionsXmd`. I list them
for completeness, not as findings.

## Not checked

- The real mutation harness: CANNOT RUN in this worktree (no `node_modules/typescript`). This is NOT a pass. I
  reproduced the 17 watcher entries with my own script instead, which is weaker: it does not run the harness's own
  placement or anchor rules.
- The 47 pre-existing entries in the manifest.
- Whether "re-armed every 30 min" and the 11:00-11:07 log counts are true. I did not re-read
  `.claude/compaction-boundary.log`.

VERDICT: NOT CONVERGED
