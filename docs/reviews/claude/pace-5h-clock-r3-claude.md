Reviewed head: 23c202cad9bfb165997b53bf4757f72282413b45

# Review — backlog #645 (usage pace: the 5-hour meter paced against its fixed block clock), round 3, Claude half

- **Subject:** `git diff origin/master...HEAD -- scripts/`, focused on the r2 fold `23c202ca` (`last_notice`, the
  `warn:<weekly>:<5h>` state key, `parts["alone"]`, the three r2 cases, the 4 added + 7 re-bound mutations).
- **Branch / commit reviewed:** `pace-5h-clock` @ `23c202ca`
- **Mandate:** refute. The 5h sentence or the weekly text silenced when it changed, or repeated when it did not; #628's
  weekly rule loosened; a REFUSE, CANNOT RUN or NOT RUN hidden; a crash or silence on a bad state file; mutations that
  do not bind or do not die.

REVIEW GAP: codex — alternation (round 3 runs one half; Codex took r2; owner 2026-10-28).

## What was run

| Check | Result |
|---|---|
| `python3 scripts/check-usage-pace.py --self-test` (worktree, 23c202ca) | 445/445 passed (18 s) |
| `python3 scripts/check-selftest-counts.py --only scripts/check-usage-pace.py` | **rc 1 — `[DRIFT] the docstring declares 442 cases; the suite ran 445`** — see m1 |
| Real-CLI driver: `--hook prompt --cache <tmp> --meter <tmp> --now 1800000000 --root <tmp git repo>`, payload on stdin, 14 sequences (below) | every sequence behaves as the fold claims |
| Anchor resolve over EVERY manifest in `scripts/mutations/*.json` | 5126 edits, 0 resolve other than exactly once; `check-usage-pace.json` has 223 entries = the pin in `expected_mutations.py:2202` |
| 6 mutations applied one at a time to a temp copy of `scripts/` + `.claude/hooks/` outside the repo (all 4 added r2 ones + 2 re-bound `last_notice` ones) | **6/6 KILLED**, each by the case its `expect` names |
| #628's weekly rule vs `git show origin/master:scripts/check-usage-pace.py` | not loosened (traced and driven, below) |

### The driven sequences (one session `s1` unless named; 5h reset at now + 2.5 h; meter band NORMAL)

| Sequence | Output per prompt | Verdict |
|---|---|---|
| weekly 10 → 11 → 12, 5h 75 (Codex r2's input) | said, SILENT, SILENT | holds |
| weekly 10, 5h 75 → 85 → 75 → 100 | said ×4 (AT MOST 2 → NO NEW → AT MOST 2 → STOP) | holds |
| weekly 10, 5h 75 → 0 → 75 (5h WARN → OK → WARN) | said, SILENT, said | holds |
| weekly 85 → 10 → 85, 5h FREE (weekly WARN → OK → WARN) | said, SILENT, said | holds (#628) |
| sessions A, B, A, A, B at the same input | said, said, said, SILENT, said | loud — one state line (#628's design), never silent |
| weekly 10 → 85 → 85 → 10 → 85, 5h 75 | said, weekly text ONLY, SILENT, SILENT, said | holds |
| (85,75) → (85,0) → (85,75) → (86,0) → (86,75) | said, SILENT, `⚠ usage pace: 5h block: AT MOST 2…` only, weekly 86 only, 5h only | holds |
| weekly 99 → 99 → 85 → 85, 5h 75 | REFUSE, REFUSE, said, SILENT | REFUSE never dedupes |
| five_hour absent, weekly 85 ×2 and weekly 10 ×2 | said ×4 | NOT RUN never dedupes |
| no meter (band UNKNOWN, NOT RUN) weekly 10 → 11 → 11 with 5h 75 → 85 | said ×3 | NOT RUN never dedupes |
| state file = binary garbage | said, then SILENT | overwritten; no crash |
| state path is a DIRECTORY | said, said | loud every prompt; no crash |
| state dir read-only (0500) | said, said; weekly 99 → REFUSE said | loud; REFUSE not hidden |
| empty payload (no session) | said, said | loud |
| master-format state line `s1\twarn:<16 hex>` | said | an old line never silences the new key |

**#628 not loosened — traced.** On master the key was `warn:` + the hash of `out`. Here, with no 5h sentence, `fkey` is
`""` and `wkey` is the hash of the whole `message` (`weekly == message`), so a weekly WARN speaks exactly when its text
changed, as before. `alone` is set only in `_evaluate`'s last WARN branch with the band zone NOT WIND-DOWN / NO NEW STARTS
/ UNKNOWN (`:733-734`) — a branch that is an OK on master when the 5h sentence is absent, so silencing its weekly text
never silences a notice master would have said. Every WARN branch ends `{five_note}`, so `message.endswith(five)` always
splits it (checked: `:719-736`). The key parse (`prev.count(":") == 2`) cannot be confused: both digests are hex, and the
`seen:<verdict>` keys hold one colon.

**Probes that did NOT refute:** a 5h zone change with weekly fixed always changes the 5h digest (the zone and its reason
are in the text); a new block changes `Block resets …`; 5h → FREE is silent, which is the same as an OK at weekly < 80 on
master (the gate and the prompt hook never announce FREE; the sentence names its reset); a 5h NOT RUN part sends the
prompt to the `else` branch, which moves the state on.

## Findings

### m1 — MINOR (aim: deliverable; caused by the r2 fold): the declared self-test count is stale, so CI's `check-selftest-counts` goes red

`scripts/check-usage-pace.py:179` declares `--self-test  # 442 cases`; the r2 fold added 3 cases and the suite now runs
445. **Breaking input:** `python3 scripts/check-selftest-counts.py --only scripts/check-usage-pace.py` → rc 1,
`✗ check-usage-pace.py: [DRIFT] the docstring declares 442 cases; the suite ran 445`. CI runs it unfiltered
(`.github/workflows/ci.yml:771`), so the pushed head cannot merge. Loud, no behaviour impact. **Fix:** `442` → `445`.

### n1 — NIT: `evaluate`'s docstring names `parts["five"]` but not the new `parts["alone"]`

`scripts/check-usage-pace.py:636`. The r2 fold made `parts` carry a second key that `main` reads to decide whether the
weekly text is a notice. **Fix:** one clause: "and `alone`: True when the WARN exists only for the 5h sentence".

## Classification

Neither finding is in the dedup logic the fold built; both are text the fold failed to update beside it. m1 is
fold-induced; r2's XM1 was not, so this is ONE fold-caused round, not two consecutive — **not THRASHING**. Both fixes
are mechanical and fully specified. The r3 fold should be text-only (`:179`, `:636`), which by `review-method.md` (b)
still changes guarded code, so round 4 (scoped to that fold) would FILE anything it finds unless a BLOCKER.

VERDICT: NOT CONVERGED
