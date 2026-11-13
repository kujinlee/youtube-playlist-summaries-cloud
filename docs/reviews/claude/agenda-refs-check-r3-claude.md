Reviewed head: 7adf04adc75ad9fe2ec61b38ba494db19404a521

# Round 3 — `agenda-refs-check` (backlog #504, PR #525) — Claude half (adversarial)

Scope: the round-2 fold (`git diff 8516de43..HEAD`: `_locked` reading bytes, `_blank_tail_cut`, validation before
truncation, the grammar-side kinds case, 4 new and 4 re-anchored mutations), read against `git diff origin/master...HEAD`,
backlog row #504, the r1/r2 reviews and coordinator docs. Nothing under `.claude/plans/` was read. Every experiment ran on
temp copies outside the repo (`/Users/kujinlee/.claude-tmp/r3/`).

## What was run

| Check | Result |
|---|---|
| `python3 scripts/goal-tree.py --self-test` at HEAD | `410/410 self-test cases passed` |
| The 8 mutations the fold added or re-anchored, plus #499 r3 M2's (temp copy of `scripts/`, applied from `scripts/mutations/goal-tree.json`, self-test run, named case looked for among the FAIL lines) | every anchor matched exactly once; every mutant rc 1 and **killed by the case it names** |
| 18 hand-built logs through `read_agenda_log`, `record_agenda` and `tick_agenda`, at HEAD, at `8516de43` and at `origin/master` (probe: `/Users/kujinlee/.claude-tmp/r3/probe.py`) | see the findings; the rest below |

Inputs that behave correctly at HEAD (RUN): an empty file; a log with no final newline; one ending in spaces/tabs with no
newline (kept, `\n` added, re-read OK); mixed LF/CRLF records; a tail of `\n\r` (cut); Codex r2's CRLF + spaces input; a
log whose LAST record is malformed followed by blank lines (refused, file byte-identical); a BOM (refused as Malformed by
reader and writer alike, unchanged); a raw U+2028 inside a string (accepted, not split); a `\r\n\r\n` whitespace-only log
(emptied). Concurrency: both writers take `flock(LOCK_EX)` on the `a+b` handle before reading, validate, then truncate and
write under the same lock; an `O_APPEND` write after `truncate` lands at the new end (the CRLF case's `startswith` assertion
shows it). Readers do not lock, but between the truncate and the write they see only a log missing blank bytes — still
valid. No defect found there.

## Findings

### N1 — MINOR — fix-induced (r2 F1) — a lone-`\r` log is accepted by the reader and refused by both writers

`_locked` now decodes the raw bytes and splits on `\n` only; `read_agenda_log` still uses `path.read_text()`, whose universal
newlines turn a lone `\r` into a line break. So the two sides no longer agree on what a line is.

Input (RUN): `A + b"\r" + T + b"\r"`, where `A` is a valid agenda record and `T` a valid tick.

| | HEAD | `8516de43` | `origin/master` |
|---|---|---|---|
| `read_agenda_log` | ok, 2 records | ok, 2 records | ok, 2 records |
| `record_agenda` | **Malformed: "line 1 is not an agenda record (Extra data…)"** | ok | ok |

Failure scenario: a log hand-saved with old-Mac line endings renders on the page, but `--record-agenda` and `--tick-agenda`
are refused, and the message names "line 1", a line the reader shows as two valid records. It fails closed — the file is
left byte-identical — and only a hand edit produces such a log, so MINOR. Fix: decide one line model for both sides (e.g.
read the reader's bytes and split on `\n` too, so the page also refuses it, or normalise `\r` in the writer before
validating while keeping the byte offsets for the cut). A case with this input pins it either way.

### N2 — MINOR — fix-induced (r2 F1) — a "blank" tail the reader skips is no longer cut, so #504's blank line returns

`_blank_tail_cut` treats only `b" \t\r\n"` as blank and only `\n` as a line ending. The reader treats a line as blank when
`ln.strip()` is empty (all Unicode whitespace) and, through universal newlines, a lone `\r` as a line ending. The r1 fold's
`str.rstrip()` covered these; the r2 fold narrowed it.

Inputs (RUN; "blank line left" = a whitespace-only line, in the reader's line model, before the appended record):

| Tail after record `A` | HEAD | `8516de43` | `origin/master` |
|---|---|---|---|
| `\n\x0c` | blank line left | cut | blank line left |
| `\n\x0b\n` | blank line left | cut | blank line left |
| `\n` + NBSP (`\xc2\xa0`) | blank line left | cut | blank line left |
| `\r\r\n` | blank line left | cut | blank line left |
| `\r   ` (no `\n`) | blank line left | cut | blank line left |
| whole log `\x0c\n` | not emptied; blank line before record 1 | emptied | not emptied |

Failure scenario: exactly the Low half of backlog #504 ("leaving a blank line replay ignores"), for whitespace outside the
four-byte set. Cosmetic — replay skips blank lines and no data is lost — and the r1 fold's wider set was itself wrong in
the other direction for blanks on the record's OWN line, so this is a regression only relative to `8516de43`, not to
master. Fix: cut after the last line, in the READER's line model, whose `strip()` is non-empty; keep that line's bytes and
its ending as now.

### N3 — MINOR — NOT fix-induced (pre-existing; in #504's class) — invalid UTF-8 crashes the goal tree

Input (RUN at function level): `A + b"\n\xff\n"`. `read_agenda_log` and both writers raise `UnicodeDecodeError`, not
`Malformed`, at HEAD, `8516de43` and `origin/master` alike. `main`'s `--snapshot` path catches only `Malformed` around
`read_agenda_log` (the "never takes the snapshot down with it" block), so the CLI would end in a traceback and no snapshot is
logged — UNVERIFIED end-to-end (traced from the `except Malformed` at the `--snapshot` block, not run through `main`).
Backlog #504's headline is "a hand-edited agenda log cannot crash the goal tree"; this is a hand-edit that still does.
Recommend filing rather than folding (outside the row's stated fix list).

## Review of the round-2 fixes themselves

- **F1** — correct for every `\n`/`\r\n` input tried; bytes on the record's own line are kept; the offset is now a byte
  offset. N1 and N2 are the residue of choosing `\n` as the only line ending and four bytes as the only blanks.
- **F2** — the grammar-side case does catch `re.I` (mutation killed). It probes a finite word set, so a grammar accepting a
  word outside the probe (e.g. a new `\w+` alternative) is not caught by it, but the r1 split-derivation case would see that
  one. Adequate.
- **F3** — validation precedes the truncate; the mutation reordering them is killed by a case whose input has a cuttable
  tail. Correct.

**Findings: 0 BLOCKER, 0 MAJOR, 3 MINOR** (N1 and N2 caused by round 2's F1 fix; N3 pre-existing).

VERDICT: CONVERGED
