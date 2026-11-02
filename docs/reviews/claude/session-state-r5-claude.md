# Round 5 — `session-state` — Claude half (confirmation, mandate REFUTE)

Subject: `git diff fb8ade4a 1e973222` on branch `session-state`, head `1e973222`. Every experiment ran in a
`mktemp -d` copy. No checkout was edited.

## Claims checked

| # | Claim | Result | Evidence |
|---|---|---|---|
| 1 | The `scripts/session-state.py` change is prose only | **CONFIRMED** | The diff touches 7 lines, all docstring. An AST comparison of `fb8ade4a` against `1e973222`, with every module, class and function docstring removed, came out **equal**. `git diff --quiet fb8ade4a 1e973222 -- scripts/mutations/` reports no change. |
| 1b | Mutations still bind and kill | **CONFIRMED** | I ran `check-plan-code.py --mutate . --only scripts/session-state.py` on a `git archive` copy with `node_modules/typescript` linked in. Result: 17 mutations, 17 killed, 17 attributed to the case each names, 0 survivors. This is a diagnostic slice, not the full gate. |
| 2 | 36/36 self-test cases pass | **CONFIRMED** | `python3 scripts/session-state.py --self-test` printed `36/36 self-test cases passed`. |
| 3a | Ledger erasure past MAX_LEDGER | **CONFIRMED for `--add`, REFUTED for `--done`** | See F1. Four `--add`s of about 20 KB each grew the ledger to 80,248 bytes, which is over 65,536. The next `--add new` left only `['new']`. |
| 3b | A missing `statusCheckRollup` reads as `NO CHECKS` | **CONFIRMED** | Through `collect()`, a fake `gh` returning `[{"number":7}]` printed `PR #7 \`?\` head  · ? · checks: NO CHECKS`. |
| 4 | Backlog #369 row and falsifier | **Mostly accurate**, with two overclaims | See F1 and F2. |
| 4 | Backlog #362 row | Accurate | It adds `r4 → DEFER` and a pointer to #369. |
| 4 | Round-4 coordinator record | Accurate except the `--add`/`--done` wording | See F1. The YAML matches the Codex doc: XP1 is High and fix-induced, XP2 is Medium. 17/17 and 36/36 match the Codex table. |
| 4 | Decision log | Structure correct | `split` goes from `outcome: null` to `continued` with an `observed` field. The new `defer` row has `outcome: stopped` and `rounds_at_termination: 4`, `retroactive: false`. The `observed` text repeats the `--add/--done` wording (F1). |
| 4 | Dashboard entry | Accurate | The added top-folder qualifier is narrower than the real bound, which only applies after a compaction in a subdirectory, so it errs on the safe side. The r4 line is true. |
| 4 | PR body has no fetch | **CONFIRMED** | `gh pr view 410`: the body never mentions `fetch` or STALE. "the next write replaces it" is true, because `--done` does not write; see F1. The **title** is stale; see F3. |

## Findings

### F1 — Low (prose): "the next `--add`/`--done` REPLACES it" is false for `--done`

`ledger_done()` reads an oversized ledger as `entries == []`. Then `len(kept) == len(entries)`, so it returns
`False` **without writing**. I ran this against an 80,248-byte ledger that held `j0`:

```
--done j0       -> "ledger: no such id j0", exit 0, file size unchanged (80,248)
--add new w o   -> ledger now ['new']   (erasure)
```

`--done` never erases anything. What it does instead is **misreport a recorded id as absent**, with exit 0. That
behaviour is not described anywhere. Codex's own r4 table shows the same thing: its `--done new` ran only after
`--add new` had already shrunk the file to 64 bytes.

The sentence appears in four places:
- the script docstring, line 42 ("the next `--add`/`--done` REPLACES it");
- coordinator XP1 ("the next successful `--add`/`--done` atomically replaces it");
- decision-log `split.observed` ("the next successful --add/--done atomically REPLACES it");
- backlog #369 (1) ("`ledger_add`/`ledger_done` then atomically replace it").

The `read_ledger` docstring line ("a write then replaces it") and the PR body ("the next write replaces it") are
both true.

The #369 falsifier covers only `--add`. It should also require that `--done` against an oversized ledger exits 2,
not "no such id". This is a one-line prose fix in each place. No code changes.

### F2 — Low (prose): backlog #369 overclaims "a missing or non-list `statusCheckRollup`" reads as `NO CHECKS`

I ran each value through `collect()` with a fake `gh`. Only the **falsy** values give `NO CHECKS`:

| `statusCheckRollup` | Printed |
|---|---|
| missing, `null`, `{}`, `""`, `[]` | `NO CHECKS` |
| `{"a":1}` | `1 unreadable` |
| `"ab"` | `2 unreadable` |
| `5` | `TypeError`, which the hook would report as CANNOT RUN |

The cause is `p.get("statusCheckRollup") or []`. The docstring says only "missing", which is accurate. The
backlog row's "non-list" is broader than what was measured. The proposed fix is still right.

### F3 — Low (prose): the PR #410 title still says "derived from git and gh"

The body correctly says "from `gh` alone", and the script makes no `git` call: `grep '"git"'` finds nothing.
The title is left over from the pre-split design. It is the same kind of stale claim as the fetch line that this
commit removed from the body.

## Not found

- No change to code, cases or mutations.
- No overclaim in the #362 row or the dashboard r4 line.
- The verdict JSON for r4 Codex is well formed: `gate_ran: true`, head `fb8ade4a`, `refused: false`.

## Disposition

All three findings are false or broader-than-measured prose. This round exists to confirm a prose-only
correction, so false prose is in scope. Each fix is one sentence in a docstring, a record or the PR title. None
needs code or a new case, and none reopens the stable half's design.

VERDICT: NOT CONVERGED
