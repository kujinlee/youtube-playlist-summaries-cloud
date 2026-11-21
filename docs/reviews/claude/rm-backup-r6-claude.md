Reviewed head: 4cc1cedf48d6dbc02078cd0fd928a67f26cd6d84

# Round 6 — `rm-backup` — Claude half (delta review of `1a4c5906..4cc1cedf`)

Subject: PR #608, branch `rm-backup-hook`, head `4cc1cedf`. Scope: `scripts/check-rm-backup.py` and
`scripts/mutations/check-rm-backup.json`, i.e. the round-5 fold (`bash_brackets` returns every reading). The claim under
test is the coordinator's: *"the class 'the hook chose a reading bash did not' cannot recur for a bracket set — it can
only over-back-up"* (`docs/reviews/coordinator/rm-backup-r5-coordinator.md`).

What was run:
- `python3 scripts/check-rm-backup.py --self-test` → `126/126 self-test cases passed`.
- A probe harness (scratchpad `r6/tools/probe.py`) that builds a fresh fixture, calls `plan()` on the command, then
  runs the same command under `/bin/bash -c` (3.2.57(1)-release) and diffs what disappeared against the plan.
- Every mutation in the manifest whose `expect` names a bracket case (8 entries, including the two new r5 entries),
  applied to a scratch copy of `scripts/` and checked for its NAMED case going `[FAIL]`. All 8: rc 1, named case red.
  (`check-plan-code.py --mutate` could not run on a partial scratch tree — it said CANNOT RUN; it was not used.)

## Findings

R6-1 — MAJOR: the "literal" reading is built by moving the negator to the END of the set; when the set ends in `-`, that makes a reversed range Python reads as matching NOTHING — a silent miss of exactly the class the fold claims cannot recur

`scripts/check-rm-backup.py:815` builds the literal reading as `"[" + body + neg + "]"`. A trailing `-` is the POSIX way
to put a hyphen in a set, and then the moved negator closes a range: `[\!a-]` becomes `[a-!]`. In Python 3.14,
`fnmatch.translate('[a-!]*')` is `(?s:(?!).*)\z` — a reversed range is dropped and the set matches nothing. For `!` the
raw target does not rescue it (Python reads the raw `[!a-]` as a NEGATION too), so no reading backs up the literal-`!`
interpretation.

Fixture: files `a1`, `-x`, `!x`, `^n`, `keep`, `b2`.

| Command | Readings (`bash_brackets`) | Hook planned | bash 3.2 deleted |
|---|---|---|---|
| `rm -f [\!a-]*` | `[!a-]*`, `[a-!]*` | `!x ^n b2 keep` | `!x a1` — **`a1` NOT BACKED UP** |
| `rm -f ["!"a-]*` | same | `!x ^n b2 keep` | `!x a1` — **`a1` NOT BACKED UP** |
| `rm -f [\^a-][^z]*` | 4 combos + raw; the one bash means is `[a-^][!z]*`, empty | `!x ^n b2 keep` | `^n a1` — **`a1` NOT BACKED UP** |
| `rm -f [\^a-]*` (control) | raw `[^a-]*` = literal `{^,a,-}` in Python | covers `a1 ^n` | `^n a1` — ok |

(`echo [\!a-]*` in bash 3.2 expands to `-x !x a1`; `-x` was not removed in the probe only because `rm` took it as an
option. With `rm -f -- [\!a-]*` it would also be deleted and also not planned.)

No refusal, no crash: the hook allows the command silently. Severity: it is the same shape Codex rated BLOCKER as R5-1
(a quoted negator), narrowed by needing a trailing `-` in the set, which I judge few would type unprompted — so MAJOR,
not BLOCKER. It does refute the fold's stated guarantee: the hook still CHOOSES a spelling for the literal reading, and
the spelling can be wrong. Suggested fix (a hypothesis, not verified): put the negator where it cannot join a range —
e.g. first after a leading `]`, or as its own alternative piece (`[body]` and the bare negator character read as
separate readings of that position) — and add `[\!a-]*` and `[\^a-][^z]*` to the r5 case with a mutation that restores
the end placement.

R6-2 — MINOR: the "more than four negating sets" refusal has no case and no mutation

`scripts/check-rm-backup.py:817-818`. `grep` finds the refusal text only at its raise; no self-test case drives it and no
manifest entry mutates it. Probed: `rm -f [^x][^x][^x][^x][^x]*` → Refuse, as written. Deleting the check would not lose
a backup (it only bounds 2^n globs), so this is coverage, not safety.

## Claims checked and NOT refuted

- R5-1 (`[\^a]*`, `["^"a]*`) and R5-2 (`[^a/b]*` with dir `[^a`): both now planned a superset of what bash deleted.
- Common idioms, each a superset of bash's deletions: `rm -rf .[^.]*`, `rm -rf .[!.]*`, `rm -f [^a]*`, `rm -f [a-c]*`,
  `rm -rf [^]]*`, `rm -rf [^]a]*`, `rm -rf d/[^e]*`, `rm -f "[^a]"*`. No crash and no unexpected refusal in any of them.
- Each new/changed manifest entry goes red on the case it names (8/8, above).

## Outside the delta (pre-existing, not counted toward the verdict)

`rm -f "a[1]"*` — quoted brackets followed by an unquoted `*`. bash deletes `a[1]z`; the hook planned only `a1` (the
lexer drops the quotes, so the brackets are read as a set and the raw target, being a pattern, is not taken as a
literal prefix). Same at `0286e19b`-era logic; I did not find it in backlog #686 by text search and the coordinator may
wish to file it.

VERDICT: NOT CONVERGED
