# Round 3 — trim-hook-floor — claude

Subject: `git diff 9d76aef1..HEAD -- scripts` at `98d024b4` (worktree `wt-floor`). Mandate: REFUTE the r2 bet
*"owner relevance is DECLARED, not inferred; every owner-kind entry and owner decision is printed whole, untruncated,
by every reader."*

**Verdict: NOT CONVERGED.** The bet's own named failure observation is met three times over: the only writer
declares `routine` for owner text (R3-1); a start-up print has no size cap, so a realistic ledger pushes the whole
block past the harness's 10,000-character replacement (R3-2); and goal-tree decides by text where a kind exists (R3-3).

## What I ran (all in the foreground)

| Check | Result |
|---|---|
| `python3 scripts/session-state.py --self-test` | **95/95 passed** |
| `python3 scripts/compaction-state.py --self-test` | **110/110 passed** |
| Compact block (`render(..., compact=True)`, live `gh` PRs, 9 open) over a COPY of the real ledger | 7,430–7,602 chars; all 12 owner entries whole |
| `snapshot()` + `render_print()` over the copy (+ this session's transcript), plus 0/6/12 synthetic owner entries | see R3-2 and R3-4 |
| `--add` through `main()` on a temp repo holding a copy | see R3-1 |
| `--migrate-kinds` on a temp repo holding a copy of the ORIGINAL (`.bak-kinds`) ledger | see R3-5 |

⚠ **Disclosure.** One probe command was run WITHOUT a temp root, as
`scripts/session-state.py --migrate-kinds --override build-402 --apply` from the worktree. That resolves to the
**real** ledger. It was **refused** (`rc=2`, "`.bak-kinds` already exists"), and I verified afterwards with `cmp` that
both `.claude/inflight.jsonl` and `.claude/inflight.jsonl.bak-kinds` are byte-identical to the copies I took before
starting. Nothing was written.

## Findings

### R3-1 — Blocking — fix-induced — `scripts/session-state.py:336` (`ledger_add`)

**`--add` without `--kind` stores `kind: routine` explicitly. Because the field is declared, the fallback heuristic
is never consulted for that entry, so every R2-1 phrasing that reaches the ledger through its only writer is trimmed again.**

Input (via `main(["--add", ...])` on a temp repo that holds a copy of the real ledger, with no `--kind`):

| id | what starts | stored kind | `guess_kind` would say | tail in the compact block |
|---|---|---|---|---|
| new-instr | `OWNER 23:40: do the next thing … (owner: 'when convenient') …` | routine | owner-instruction | **False** |
| new-note | `NOTE: WAITS-ON-OWNER: pick A or B …` | routine | owner-wait | **False** |
| new-lower | `waits-on-owner (card when back): pick …` | routine | owner-wait | **False** |

All three ids land in `hidden ids:`. The real ledger has **8 entries** written in the `OWNER hh:mm:` form. Each was
correct only because the migration was overridden by hand. The next such entry, or a re-`--add` of an existing id to
update its text, becomes `routine`. A re-add replaces the entry and drops its declared kind.

The docstring says the heuristic is "the fallback for an entry with no `kind`", which fails toward SHOWING. But
`ledger_add` never produces an entry with no kind, so that fallback is unreachable for anything written after this
change. The design moved the guess from the reader to the writer, and the writer's guess (the strict prefix) is the
narrowest one in the file.

Fix: when `--kind` is omitted, either REQUIRE it (refuse), or store `guess_kind(entry)` (its wide reading) rather than
the strict-prefix `routine`. Either way, add a case that writes through `--add`/`ledger_add`, not through a fixture dict.

### R3-2 — Blocking — not fix-induced (uncapped since r1) — `scripts/session-state.py:541` (`collect`) / `render`

**The SessionStart in-flight block has no size cap.** Owner entries are `WHOLE` and unbounded in number. The repo's
own premise (`compaction-state.py` `PRINT_CAP` comment) is that the harness REPLACES SessionStart output over 10,000
characters with a file path. Past that point the whole block disappears, every owner line with it, and nothing says
which ones.

Run: the real ledger copy plus N synthetic `owner-instruction` entries of the ledger's usual length (~420 chars),
with the 9 open PRs from live `gh`:

| extra owner entries | owner entries total | compact block chars |
|---|---|---|
| 0 | 12 | 7,430 |
| 6 | 18 | **10,280** (over 10,000) |
| 12 | 24 | 13,134 |

This is realistic. The ledger had 5 owner waits on 10-28 (the code's own comment) and has 12 now. Owner entries
leave only by `--done`, and `MAX_LEDGER` (64 KB) admits about 150 of them. This meets the bet's named failure
observation ("any owner-wait or owner-instruction entry that any start-up print cuts").

Fix: give `collect` the same discipline the compaction print has. Owner entries go first, under a budget. Past the
budget, print every remaining owner entry's **id** (ids are short, so the list fits), plus the path. Never let the
output exceed PRINT_CAP. Add a case at more than 10,000 characters of owner text.

### R3-3 — High — not fix-induced, but inside the bet — `scripts/goal-tree.py:422-427` (`needs_from_ledger`), `:285-286`, `:264`

**goal-tree still decides owner relevance by the strict text prefix where a declared kind exists.** This is the
second named failure observation. I ran it against the real ledger copy:

- **NEEDS-YOU from the ledger: 1 item** (`roles-review-answers`). The ledger declares **4** `owner-wait` entries.
  `card-451`, `card-old-halves` and `card-plugins` (`WAITS-ON-OWNER (card …` — not normalised, written before r1)
  are missing from the block the owner reads.
- Those three, and all 8 `owner-instruction` entries, fall into `inflight_loose`, **cut to 160 characters** (for
  example `auto-compact-300k`: 160 of 683, `token-plan`: 160 of 539). Line 264 cuts goal-attached entries at 160 too.
- The inverse also holds. A `kind: routine` entry whose text starts `WAITS-ON-OWNER:` (the self-test itself writes
  one, id `d`) **is** listed in goal-tree's NEEDS: `needs_from_ledger([...]) -> True`.

So the two readers disagree about the same entry. The coordinator's question is answered: **yes, this is a hole**.
A kind-only owner-wait (`--add X "pick A or B" d --kind owner-wait`) never reaches the goal tree's NEEDS-YOU block.

Fix: `needs_from_ledger` should use `entry_kind(e) == KIND_WAIT`. Its slice of `rest` must then not assume the
prefix (use `removeprefix`). Its ACTION split can stay on the text after the marker. `loose`/`flying` should use
`is_owner` and print owner entries whole.

### R3-4 — Medium — fix-induced — `scripts/compaction-state.py:843` (`render_print`), `:803` (`digest`)

**Owner entries come first, but when they alone pass PRINT_CAP, the ones after the cut are dropped without being named.**
With the real ledger plus 12 synthetic owner entries, the print (9,620 chars) loses `extra-owner-8` … `-11` entirely.
The only trace is the generic `TRUNCATED at 9771 characters; the rest: the session's snapshot file`. The snapshot
keeps all 24, so nothing is lost on disk. But the print hides owner decisions behind a line that does not say any
were hidden. The case at `:1260` ("past the harness's 10,000-character limit the print SAYS it is cut …") asserts
only `TRUNCATED` and the path. It would pass if every owner entry but the first were silently gone. Its 12,000-`z`
input does exactly that, unchecked.

Fix: when the cut falls inside the owner section, append the ids of the owner entries not shown (the same move as
the compact block's `hidden ids:`). Assert in the case which ids are named.

### R3-5 — Medium — fix-induced — `scripts/session-state.py:1081` (`main`, `--migrate-kinds`)

**`--override` silently drops what it cannot use.** I ran it against the original ledger copy with
`--override build-402 --override no-such=owner-wait --override card-451=routine`, and got `rc=0`:

- `build-402` has no `=`, so it is **dropped**. The proposal for build-402, the very R2-1 entry, stays
  `routine (heuristic)`. With `--apply`, that would be written.
- `no-such=owner-wait` names an id that does not exist: ignored, no word.
- An override for an entry that already declares a kind is ignored (`declared` wins), also without a word.

Backup and second run (checked): the `.bak-kinds` copy is byte-for-byte and made before `_write`. `_write` is
tmp+`os.replace` (atomic), and a second `--apply` is refused (`rc=2`, verified above on the real path). One edge
case: if `_write` refuses (adding `kind` pushes a near-64 KB ledger over `MAX_LEDGER`), the backup already exists.
Every retry is then refused until it is deleted by hand. The original is intact, so this is Low.

Also Low: `--apply` without `--migrate-kinds`, and `--kind` without `--add`, are silently ignored (`--apply` alone
prints the normal block, `rc=0`).

Fix: refuse a malformed override (no `=`), an override naming no entry, and an override on a declared entry. Refuse
`--apply`/`--override`/`--kind` outside their mode.

### R3-6 — Medium — cases passing for an ambient reason

1. `session-state.py:631` ("each of Codex's four hidden phrasings is shown whole … **by the fallback with none**").
   The kind-less fixture is a state the writer never produces (R3-1), so the case certifies a path that real
   entries do not take. The defect it names is live through `--add`, and the suite is green.
2. `session-state.py:584` ("the compact block is at most 25% of the full one"). It passes on a fixture of one owner
   entry among twenty routine. On the real ledger (12 owner, 11 routine), the ledger part of the compact block is
   **77%** of the full one (6,765 / 8,842), and owner lines are 5,594 of those characters. The r2 R2-4 case states
   that cost for an owner-only ledger. But the "floor" case's name still reads as the property, and the real subject
   does not have it.
3. `compaction-state.py:1260`: see R3-4.

### R3-7 — Low — observation, cost

After a compaction, both SessionStart prints carry every owner entry whole: the in-flight block (7,430) and the
compaction digest (7,090). On the real ledger that is 12 entries, about 5.6k characters, **twice per start**. If the
10,000-character limit is per hook this is only cost. If it applies to the combined output (NOT VERIFIED), the pair is
already over it today. The floor this PR exists to cut is, on the real ledger, mostly owner text that is now printed twice.

## Answers to the coordinator's questions

- **A reader that still infers?** Yes: goal-tree (R3-3). The writer also infers, through the strict prefix, and
  declares the result (R3-1). The compaction snapshot and the compact block do read `kind`.
- **Routine to owner treatment, or an owner entry dropped?** Both. A `routine` entry carrying the marker shows in
  goal-tree's NEEDS (R3-3). Owner text written through `--add` becomes routine (R3-1). Owner entries are dropped by
  the uncapped print (R3-2) and by the PRINT_CAP cut without being named (R3-4).
- **`--migrate-kinds` safe?** The backup, the refusal to run twice and the atomic write hold. The overrides fail
  silently (R3-5).
- **Does the 10,000 cut still hide an owner line?** Yes: at 18 owner entries for the in-flight block (R3-2), and at
  24 for the compaction print (R3-4).
- **Ambient passes?** R3-6.

**Thrashing check:** R3-1 and R3-4 are caused by the r2 fix, in the component `owner-relevance-inference`. R2's
findings were not fix-induced. So this is the first fix-induced round, not two consecutive: **not armed**. The route
the decision log names for this failure is SPLIT ("print the whole ledger and trim only the PR list"). Note that
SPLIT does not escape R3-2, because a whole ledger is also unbounded against the 10,000-character replacement.

NOT CONVERGED
