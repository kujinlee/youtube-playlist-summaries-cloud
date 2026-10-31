# Round 1 — guards-cannot-run — claude

Subject: branch `guards-cannot-run` (PR #440) at `870f99ac`, against `origin/master`. Read-only in the shared
worktree; every experiment ran on copies under the scratchpad. No file under `.claude/plans/` was read.

## Gates run

| Gate | Result |
|---|---|
| `--self-test`, all five changed guards | transcript-references 22/22, banner-armed 241/241, closing-table 156/156, handoff-path 22/22, ci-watched 92/92 — all rc 0 |
| `check-plan-code.py --mutate . --only scripts/<f>.py` | transcript-references 9/9 killed, handoff-path 7/7, closing-table 50/50, ci-watched 44/44, banner-armed __BANNER__ — every kill credited to the case it names |
| Stop hook as registered (`run-hook.sh block-idle-stop.sh`, copied tree, `HOME` redirected) | payload `[]` gives exit 1; a `\xff` transcript gives exit 1, with and without `stop_hook_active`. No traceback and no exit 2, so a CANNOT RUN does not block or loop |
| Real transcripts, 580 files under `~/.claude/projects/*/*.jsonl`, read-only | 0 undecodable, 0 with zero parsed records, so neither new transcript refusal fires on this corpus |

## Findings

### M1 — Major — a surviving mutation brings #357(5) back: `all(...)` → `any(...)`
`scripts/check-ci-watched.py:538`. The only rejecting case is `[123]`, a list of ONE non-object. `all` and `any`
give the same answer on a one-element list, so the case cannot tell them apart. RAN on a scratch copy with
`all` → `any`: `--self-test` **92/92 green**. Then `run_decide` with `_pr_checks_raw` returning
`[{"name":"v","state":"PENDING"}, 5]` gave **`RAISED AttributeError: 'int' object has no attribute 'get'`**. That is
the #357(5) traceback, back, for a mixed list. On the real branch the same input correctly gives rc 2.
**Fix:** add a mixed-list case (one valid row plus one non-object) and a manifest entry for `all` → `any`.

### M2 — Major — a surviving mutation brings #357(2) back for every non-list payload, in two guards
`scripts/check-banner-armed.py:1301`, `scripts/check-transcript-references.py:130`. Both guards' only case is `[]`.
RAN with `if not isinstance(data, dict)` changed to `if isinstance(data, list)` in each:
banner-armed **241/241 green** (in a tree with `.claude/` present; without it, one unrelated reachability case fails
in the control and the mutant alike), transcript-references **22/22 green**. Through `--decide`, the payloads
`"str"`, `123`, `null` and `true` then each exit **1 with a Traceback** in both guards. The branch as written
handles all four (rc 2). The fix is right. The case does not pin it. That is a one-input case over a union, the same
pattern as M1. **Fix:** give each case a second, non-list payload (`null` is the likeliest to be met in practice) and
add the mutation.

### m1 — Minor — invalid UTF-8 in the Stop-hook PAYLOAD still tracebacks into exit 1 in three guards, depending on locale
`scripts/check-banner-armed.py:3419`, `scripts/check-closing-table.py:1714`, `scripts/check-transcript-references.py:369`
(`sys.stdin.read()`). Input: `printf '{"transcript_path":"/x\xff"}' | python3 scripts/<g>.py --decide`. Under
`LANG=en_US.UTF-8` (this machine) all three exit **1 with `UnicodeDecodeError`**. Under `LC_ALL=C` all three exit 2,
because Python's UTF-8 mode reads stdin with surrogateescape. `check-ci-watched` is unaffected (its `payload_from`
handles it). This is unchanged from master (master banner-armed: rc 1, traceback), and #357's five inputs do not
include it, so it is not a regression. But the PR's stated invariant is "never a traceback on input they cannot
read", and the payload is input. Claude Code emits valid UTF-8 JSON, so realism is low. **Fix:** read
`sys.stdin.buffer` and decode inside the existing handler, or file it as #357's sixth input.

### m2 — Minor — one bad byte now blinds the whole transcript, while a bad JSON line is just skipped
`scripts/check-*.py` transcript reads (`read_text(encoding="utf-8")` inside `(OSError, UnicodeDecodeError)`). All 580
real transcripts contain raw multi-byte UTF-8 (`files-with-raw-nonascii=580`), so a torn final write can split a
character. RAN on a real transcript from this project, via `check-transcript-references.judge`:
whole file → rc 0; plus a torn final record ending in ASCII → **rc 0** (the permissive parser drops it); plus a torn
final record ending mid-character (`…"ab\xe2\x9b`) → **rc 2 CANNOT RUN**. So one class of input (a torn last record)
gets two verdicts depending on where the cut fell. This is not a regression: master tracebacks there. But the
refusal is coarser than the parser it sits beside. **Fix (optional):** decode per line with `errors="replace"` and
let the existing parser drop the bad record. Or keep strict and note in the docstring that it is deliberate.

### m3 — Minor — #331(a) is closed only for TOTAL corruption; partial corruption still passes QUIET
`scripts/check-transcript-references.py:142`. RAN through `judge`: `[user "go", assistant "see #291", user "again",
assistant "x"]` gives rc 1 (control). The same with the judged assistant record truncated by 3 bytes gives **rc 0,
"no completed turn to judge yet"**. Only the first record parsing, followed by three `not json` lines, also gives
**rc 0**. The backlog row's own fix shape was a raw-line-vs-parsed-record comparison. The branch implements
`not records`, which is weaker. The row says "(a) FIXED", and that is true of its stated falsifier (`not json` →
2) but not of the class. ⚠ Do NOT simply switch to "any dropped line → CANNOT RUN". See m4: on this corpus that would
refuse **16 of 580** valid transcripts. **Fix:** reword the row to "(a) fixed for a transcript with no parseable
record; partial corruption is still quiet", or narrow it as m4 describes.

### m4 — Minor, pre-existing, and it constrains m3 — `splitlines()` breaks real records apart
`scripts/check-banner-armed.py` `_parse_records` callers, i.e. every `read_text(...).splitlines()` in the three Stop
guards. Measured over the 580 real transcripts: in **16 files** `splitlines()` and `split("\n")` disagree, because
of raw ` ` (15 files), ` ` (8) or `\x85` (1) inside JSON strings. The permissive parser then drops **140**
fragments. Read with `split("\n")`, the same files drop **0** lines. So the dropped-line signal m3 would need is
polluted by the reader itself. Fix the reader before any line-count rule.

### m5 — Minor — on the handoff hook, an undecodable SKILL.md went from a WARNING to a BLOCK with a false headline, and nothing records the change
`.claude/hooks/enforce-handoff-path.sh` (the `1|2)` arm). RAN the hook in a copied tree with the real SKILL.md plus a
trailing `\xff`. On master: **exit 1**, "reached no verdict (no receipt)". On the branch: **exit 2, BLOCKED**, under
the banner "the handoff skill would write where nothing reads". That is false here: the file DOES name
`.remember/remember.md` and the guard simply could not decode it. The CANNOT RUN text does appear in the body. A
block is consistent with how missing and empty files were already treated, and the backlog row implies it is wanted.
But the dashboard entry says "Nothing a working session sends them changes", and no case drives the hook over this
input. **Fix:** a hook case for receipt `2`, and a CANNOT RUN headline distinct from REVERTED. Or state in the entry
that `/handoff` is now blocked, not warned, on this input.

## Checked and not refuted

- Stop-hook rc mapping: every observer's 2 is folded into `exit 1` (`block-idle-stop.sh` final condition). Only
  `check-plan-progress`'s non-{0,3} and banner rc 4 reach `exit 2`. With `stop_hook_active: true` the outcome is the
  same exit 1, so there is no trap.
- ci-watched: `[]`/`null`/`""` → QUIET (no checks), `{}`/`123`/`"[]"`/`[[]]`/`[null]` → 2, object rows with junk field
  types → WARN (the existing fail-closed `row_is_resolved`), denied directory → 2. The `[123]` case reads the real
  sentinel, but `rows is None` returns CANNOT RUN before `watching` is consulted, so the case is not ambient.
- handoff-path: the CLI case copies the script into a fresh root and runs it as a subprocess, so the case is not ambient.
- The `#357` row's "11 cases, 8 mutations" and the dashboard's "12 cases, 9 mutations" agree once #331(a)'s one case
  and one mutation are added. `EXPECTED_MUTATIONS` +9 matches the manifest growth (2+1+1+2+3).

## Verdict

**NOT CONVERGED** — Blocking 0, Major 2 (M1, M2: two surviving mutations, each of which reinstates a #357
traceback that the suite claims to cover), Minor 5.
