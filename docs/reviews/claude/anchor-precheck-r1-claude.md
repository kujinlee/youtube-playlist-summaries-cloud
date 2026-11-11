# anchor-precheck — round 1, Claude half

Subject: branch `anchor-precheck` (PR #405), `git diff origin/master...HEAD` at `916d7fd2`.
Mandate: refute. Every claim below was executed on a copy (`rsync` of the worktree into a
scratch directory, `node_modules` symlinked), never on the tracked files.

## What I tried to break, and what held

| Attack | Executed evidence | Result |
|---|---|---|
| Pre-check disagrees with `run_mutations`' own application rule | Probe applied `run_mutations`' exact loop (`count > 1` → refuse, `not in` → refuse, `replace(find, repl, 1)` sequentially) and `anchor_problems` to each of the **2,108** real entries independently | **0 disagreements**; 13 multi-edit entries, 0 empty-edit entries; whole-manifest `anchor_problems` returns `[]` — no false refusal on today's tree |
| False refusal from staged ≠ delivered text | `stage_tree` uses `shutil.copytree` with default `symlinks=False` (follows links, copies bytes); both sides read in universal-newline text mode, so CRLF is normalised identically | No divergence found |
| Empty find-string / entry with no edits | `"".count` on non-empty text is `len+1` → both sides refuse; no edits → both sides clean | Agree |
| The 3 new manifest entries | Applied each in memory to the copy and ran `--self-test` | each red via its named case (2, 1 and 1 FAIL respectively) |
| Self-test as delivered | `python3 scripts/check-plan-code.py --self-test` | `244/244 passed`, 6.6s |
| The two `ANCHOR = "VALUE != 1"` worlds passing ambiently | Removed both lines | both cases red (`got (False, False)`, and a crash on `_evT.files[...]`): the line is load-bearing, and the cases can only pass after a real control ran |
| Pre-check narrowed to the first entry | `anchor_problems(muts[:1], …)` | killed by the "refused UP FRONT, naming both" case |
| Cost | `anchor_problems` alone over the real manifest | 0.52s |

## Findings

### L1 (Low) — the `--only` property is claimed three times and witnessed by no case
`scripts/check-plan-code.py:3657-3659` (comment: *"so --only naming ANOTHER target still sees it"*),
the PR body and the backlog #252 row all assert it. The case at `:3665` calls
`mutate_delivered(_r, progress=…)` with **no `only=`**.

Executed: replaced `:2510` with
`drift += anchor_problems([m for m in muts if only is None or m['file'] in only], _read)` →
**`244/244 passed`**. The property is true today only because of statement order; a refactor that
moves the pre-check below the `--only` filter stays green. Fix: a case that passes `only=` naming a
target other than the orphan's (the `_mini(..., second=True)` world has one) and asserts the refusal.

### L2 (Low) — `break` in `anchor_problems` is unmutated
`scripts/check-plan-code.py:2416`. Executed: deleting it → `244/244 passed`. Effect without it:
after a NOT FOUND the next edit of the same entry is checked against un-advanced text, giving a
second, possibly misleading, message. The entry is still refused, so this cannot produce a false
green — a nit, recorded so the survivor is known rather than discovered.

### L3 (Low) — backlog #252 is marked ✅ while its own falsifier still fires
`docs/backlog.md:267`. The leading cell now reads `✅ (was 🟠)`, but (a) the status column of the
same row still reads `🟠 **OPEN — filed 2026-10-07**`, and (b) the row's `FAILS IF` is *"an anchor
absent from its target, **or an `expect` naming no case**, is discoverable only by running the
mutation"*. Executed: `anchor_problems([{…, 'expect': ['NO SUCH CASE']}], …)` → `[]`; the function
never reads `expect`, as the PR itself says. So the row's stated gate still fails and the row is
ticked. The repo's convention for a half-shipped row keeps the open marker and says so (row 56:
`🟡 … NARROWED — HALF OF THIS SHIPPED`). `check-docs.py` reports `Documentation integrity OK`, so no
guard sees the contradiction. Fix: keep #252 open/narrowed to the `expect` half (or move that half
explicitly into #208 and edit #252's `FAILS IF` to the anchor half before ticking it).

## Observations (not findings)

- **Stand-down of the pre-check in the total-shortfall world** (`:4052-4056`). Removing the stand-down
  reddens exactly one case — *"...and it names the arithmetic"*. *"a TOTAL SHORTFALL prints no tally
  either (path 3 of 3)"* passes **with or without** it, because a pre-check refusal prints no tally
  either. The world as a whole is still witnessed by the arithmetic case, so this is acceptable, but
  that one case is now the only thing proving the late path was reached. The monkeypatch itself works
  because `_mutate_output` drives `main()` in-process and `mutate_delivered` resolves the name from
  module globals; a rename would `KeyError` loudly, not silently no-op.
- **Every shard now refuses on any orphan.** Consistent with the existing *"EVERYTHING ABOVE THIS LINE
  IS OVER THE WHOLE MANIFEST"* rule; the cost is 12 red shards in under a second instead of one red
  shard after ~15 minutes. Intended, and the better trade.
- The `_texts` cache re-reads files the home-escape loop just read; harmless duplication.
- A non-UTF-8 target raises `UnicodeDecodeError` (not `OSError`) in `_read`, but the home-escape loop
  directly above performs the same read with the same `except OSError` and would crash first — not
  introduced here (unverified by execution; read from `:2479-2483`).

VERDICT: CONVERGED
