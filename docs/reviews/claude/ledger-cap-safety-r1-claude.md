# ledger-cap-safety — round 1, Claude half (adversarial)

**Subject:** PR #413, branch `ledger-cap-safety`, head `c3a2b169`, `git diff origin/master...HEAD`
(5 files: `scripts/session-state.py`, `scripts/mutations/session-state.json`, `scripts/check-plan-code.py`,
`docs/backlog.md`, `docs/dashboard-entries.md`).
**Mandate:** refute. Every claim below was executed unless it is labelled UNVERIFIED. All experiments ran
in `mktemp -d` copies. No checkout was edited.

## What I executed and what held

| Check | Result |
|---|---|
| `python3 scripts/session-state.py --self-test` (Python 3.14.4) | 45/45 pass, 45 `[ok]/[FAIL]` lines |
| `check-plan-code.py --mutate . --only scripts/session-state.py` in a full `git archive HEAD` copy with `node_modules/typescript` | `21 mutation(s), 21 killed, 21 attributed to the case each names, 0 survivor(s)`, 13 s |
| Ledger exactly at the cap (65,536 bytes) | read whole (`['a']`, no problem); `--done zz` → False, `--done a` → True. Correct |
| A write landing exactly at the cap | accepted, file 65,536 bytes, reads back clean |
| A write landing one byte over (65,537) | `LedgerRefused`, file never created |
| Symlink → oversized file | refused (`path.stat()` follows the link) |
| Symlink → directory | refused as "not a regular file" |
| Dangling symlink | treated as missing; the link is replaced by a regular file. No data lost |
| Read-only `.claude/` | `PermissionError` at `mkstemp` → OSError → exit 2; file unchanged (1 line) |
| SessionStart hook with a 70,000-byte ledger | block still prints, with `⚠ … is 70000 bytes, over 65536 — NOT READ`, hook rc 0 |
| Rollup: missing, `None`, `{}`, `""`, `0`, `1`, `True`, `False`, `"x"`, `{"a":1}` | every one prints `UNREADABLE (gh gave no check list)` |
| Rollup: `[]` / `[None]` / `[{FAILURE}]` | `NO CHECKS` / `1 unreadable` / `1 fail` |
| `collect()` with gh answering `[{"number":7}]` | `checks: UNREADABLE` — the row's second falsifier holds |
| PR body (`gh pr view 413`) | each factual claim matches what I measured, with the exception in F4 |

The core fix works. What follows are the ways it is still wrong or weaker than claimed.

## Findings

### F1 — MEDIUM — the erasure guard is a second copy of `read_ledger`'s rule, so the defect returns with the suite green if the copies drift
`scripts/session-state.py:201-211` (`_whole`) versus `:154-158` (`read_ledger`).

`_whole` repeats `read_ledger`'s two refusal conditions (`S_ISREG`, `st_size > MAX_LEDGER`) instead of
asking `read_ledger` whether it read everything. They only protect the ledger while they agree exactly.
Nothing pins that agreement.

**Evidence (executed):** I changed only `read_ledger`'s `>` to `>=` (`:157`):
- `--self-test`: **45/45 pass**.
- A ledger of exactly 65,536 bytes holding job `a`, then `ledger_add(p, "b", …)`: ids afterwards **`['b']`**.

That is backlog #369's erasure, back with every case green and every one of the 21 mutations still killed.
The two boundary mutations on the new code also survive (`_whole` `>`→`>=` and `_write` `>`→`>=`: both 45/45).
These two happen to fail safe. The one that matters, `read_ledger`, does not.

**Fix:** keep the rule in one place. `read_ledger` returns (or a `strict=True` variant raises) a
"not read whole" signal, and `ledger_add`/`ledger_done` refuse on that signal instead of calling a parallel
`_whole`. Add a case at exactly `MAX_LEDGER` that updates the ledger and asserts the old job survives.
That case kills the `read_ledger` `>=` mutation. Add it to the manifest.

### F2 — LOW — TOCTOU between `_whole` and `read_ledger`: a writer that ignores the lock still causes total erasure
`scripts/session-state.py:217-221` and `:228-230`.

`_whole` stats the file, then `read_ledger` stats it again. If the file grows past the cap between the two
calls, `read_ledger` returns `[]`. `_write` then writes only the new entry, which is small and passes the
cap check, so `os.replace` erases everything.

**Evidence (executed):** three jobs recorded, then `_whole` wrapped so that an unlocked append of
64 KiB+ happens right after it returns. `ledger_add(p, "new", …)` → **accepted**, ids afterwards
**`['new']`**.

Every writer in this script takes the lock, so the real exposure is a hand edit or another tool. The window
is two syscalls wide. Low, but it is the same erasure. F1's fix closes it too: `read_ledger` decides
completeness from the one stat it reads by. Best is one `open` + `fstat` + bounded `read`, so the size
checked is the size read. `_write`'s cap already covers growth after `read_ledger`'s stat, because that read
gets everything and the rewrite is then over the cap.

### F3 — LOW — `--done` on an under-cap ledger can be refused as "would grow", because the rewrite re-escapes non-ASCII
`scripts/session-state.py:187-190` (`ensure_ascii=True` re-serialisation, then the cap check).

A line written elsewhere with raw UTF-8 grows when rewritten: one CJK character goes from 3 bytes to 6
(`\uXXXX`). The self-test already models lines "written elsewhere".

**Evidence (executed):** a 60,105-byte ledger (under the cap) holding a CJK job and job `x`. `--done x` →
`CANNOT RUN … the ledger would grow to 120053 bytes, over 65536 — refused; trim it first`, **rc 2**. That is
a removal, and `--done` is the trimming tool. `--done cjk` succeeds.

It fails safe, with nothing lost. But the message is false ("grow"), and the user is told to trim while the
trim is the very command being refused.

**Fix:** either write back unchanged, parsed entries as their original bytes (as damaged lines already are),
or word the refusal to say that re-encoding is what grows it. At minimum, do not refuse a `--done` whose body
is no larger than the bytes it read.

### F4 — LOW — the "None" rollup case tests a MISSING key, never an explicit `null`; the claim "each bad rollup value" overstates it
`scripts/session-state.py` self-test, the `for bad_rollup in (None, {}, "")` loop (the
`if bad_rollup is not None:` line skips setting the key).

For `None`, the loop leaves `statusCheckRollup` out entirely. So the case named "a rollup of None reads
UNREADABLE" exercises "missing", and no case ever passes `{"statusCheckRollup": null}`. That is the shape
`gh --json` actually emits for a PR with no rollup. The case's name and its body disagree.

Behaviour is correct: I executed explicit `None` and it prints UNREADABLE. But a future
`p.get("statusCheckRollup", [])`-style regression that treats `null` specially would not be caught by the
named case. The PR body says the cases cover "each bad rollup value", and explicit `null` is not one of them.

**Fix:** iterate over `(MISSING, None, {}, "", 0)` with a sentinel for MISSING, so `None` is set explicitly.

### F5 — LOW — backlog #369 is marked FIXED, but one clause of its own Fix is neither done nor deferred
`docs/backlog.md:351`.

The row's **Fix** says "require each PR element's fields". `collect()` (`:283-285`) still accepts
`[{"number":7}]`. I executed it, and it prints ``PR #7 `?` head  · ? · checks: UNREADABLE``. The rollup half
is satisfied and the row's FALSIFIER holds. The field-requirement clause is silently dropped, though: the
FIXED cell does not say it was deliberately left out.

**Fix:** either implement it, or add one sentence to the FIXED cell saying that clause is out of scope (or
superseded by the per-field `?` rendering), so the row stays true.

### F6 — LOW (doc) — stale docstring now states the defect as current behaviour
`scripts/session-state.py:150`: `⚠ An OVERSIZED ledger returns nothing to keep, and a write then replaces it (backlog #369).`

After this PR, a write does **not** replace it. **Fix:** reword it to "an OVERSIZED ledger returns nothing;
updates refuse it (`_whole`), so nothing replaces it".

### F7 — INFO — two refusal paths have no mutation of their own
I executed hand mutations not in the manifest:
- `_whole`'s `S_ISREG` branch dropped: killed by "a ledger that is not a regular file refuses an update too".
- `ledger_add`'s `_whole(path)` call dropped: killed by the oversized `--add` case. As a cascade it also
  reddens the `--done` and `main` cases, because the add replaced `big`. The shared `big` fixture couples
  those cases, so a single regression reads as three.

Both are killed today. Consider adding the `S_ISREG` mutation to the manifest, and giving the `--done` case
its own oversized fixture so it fails only for its own reason.

## Not attacked / UNVERIFIED
- A real concurrent lock-ignoring writer (F2 was simulated by wrapping `_whole`, not by a second process).
- Behaviour on Linux (`fcntl.flock`, FIFO semantics): macOS only.
- The full mutation sweep (`--mutate .` across all files): only the `--only scripts/session-state.py` slice
  was run. The `2175` total pin in `check-plan-code.py` was not re-derived.

## Verdict
The fix closes the reported path and every claim in the PR body I measured is true, except the F4 overstatement.
F1 is a structural weakness: the protection rests on two copies of one rule staying identical, which I showed
reintroduces the exact erasure with a green suite. It is a cheap change, and the same change closes F2.

VERDICT: NOT CONVERGED
