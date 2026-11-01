Reviewed head: 621503e551b5640d2bc381044d47d65f5e10f753

# Round 3 — `trim-always-loaded` — Claude half

REVIEW GAP: codex — alternation (round 3 is the Claude half only).

Scope: the r2 fold (`git diff 8488b775..621503e5`) and the PR as a whole against its claim — no action clause
in master's `docs/dev-process.md` / `docs/plugins.md` is missing from those files on this head; every moved
block is master's text verbatim except declared edits; the stated character counts and token estimates are
exact; no fold introduced a false statement. Mandate: refute. Round cap (`docs/review-method.md` §0 Q4c):
this is the last ordinary round.

**Result: the claim is refuted on the "counts are exact" and "declared edits" clauses (three Low/Medium
findings, all in `docs/trim-floor-walkthrough.md`, two of them introduced by the r1 fold). The
action-clause sweep found no Medium omission; five Low MOVED-only clauses are listed. No finding is a
BLOCKER: none produces a false green, data loss or a security effect.**

## What I ran

- `git rev-parse HEAD` = `621503e5…`; `git fetch`; `origin/master` = `549cfb4d`, which is also the merge
  base, so the comparison base is current. Worktree clean (`git status --short` empty), so the measure
  script's working-tree read equals HEAD.
- `python3 …/scratchpad/measure_trim.py` — confirmed it measures `git show origin/master:<path>` against
  the working tree with `len()` on decoded text (characters). Output:

  | File | origin/master | HEAD |
  |---|---:|---:|
  | `CLAUDE.md` | 1,042 | 1,042 |
  | `AGENTS.md` | 325 | 325 |
  | `docs/dev-process.md` | 25,159 | 14,673 |
  | `docs/plugins.md` | 20,851 | 10,621 |
  | total | 47,377 | 26,661 (−20,716, 43.7%) |

  raw tokens 5,179; cached-weighted 518; fresh-write-weighted 6,474.
- `wc -l`: `dev-process.md` 214, `plugins.md` 166 (matches the walkthrough's line sentence).
- `wc -c` growth of the on-demand docs vs `origin/master`; `wc -c ~/.claude/CLAUDE.md` = 6,688 (matches).
- Systematic sweep (script in scratchpad, `sweep_r3.py`): split both master files into sentences/table rows,
  kept every unit matching `must|never|do not|don't|always|run|refuse|⛔` — **90 units (44 dev-process, 46
  plugins)**. 21 are verbatim in the HEAD spine; the other 69 I classified by hand below.
- Line-level verbatim check: every non-empty line of master's two files searched in the union of HEAD's five
  docs (`dev-process`, `plugins`, `review-method`, `process-checklists`, `process-rationale`). Only 5 lines
  are not found verbatim: the 3 dev-process rows carrying the declared `#56`/`#137` → `backlog #…`
  qualification, and the 2 plugins blocks carrying the r1 fold's bracketed relocation notes. A
  whitespace-normalised diff of the moved Agent-tool paragraph against master shows ONLY the inserted
  bracket.
- `python3 scripts/check-docs.py` in the FOREGROUND: **rc=0, "Documentation integrity OK"**; WARN that
  `dev-process.md` is 214/220 (6 lines of runway).

## Findings

| # | Severity / disposition | File:line | Finding | Fix-induced? |
|---|---|---|---|---|
| F1 | **Medium — FILE** | `docs/trim-floor-walkthrough.md:29` | The table row `CLAUDE.md` + `AGENTS.md` says **1,371 / 1,371**. Measured `len()`: 1,042 + 325 = **1,367**. The table no longer sums: 1,371 + 25,159 + 20,851 = 47,381 ≠ the stated 47,377 total (the total and the two per-file rows are right). Refutes "the stated character counts are exact". Fix: 1,371 → 1,367 in both columns. | **Yes** — introduced by the r1 fold (`git log -S'1,371'` → `8488b775`); r2 re-measured the other rows and missed this one. |
| F2 | **Low — FILE** | `docs/trim-floor-walkthrough.md:45-46` | "`process-checklists.md` +17,073 B, `review-method.md` +14,423 B". Measured `wc -c` HEAD minus `origin/master`: **+17,142** and **+14,485**. The differences (69 and 62 bytes) are exactly the r1 fold's two bracketed relocation notes, so the figures predate the r1 fold. (`process-rationale.md` +930 is correct.) Fix: restate both. | **Yes** — r1 fold made them stale. |
| F3 | **Low — FILE** | `docs/trim-floor-walkthrough.md:4`, `:63-70` | The page says every paragraph was "MOVED, verbatim" and lists "**Two** small text changes made during the move" (the `backlog #` qualification and the italic header lines). There is a third: the r1 fold inserted `[moved from \`plugins.md\`; …]` notes into the moved Agent-tool paragraph (`docs/review-method.md:891`) and the layer-table row (`docs/process-checklists.md:1173`). It is declared only in the r1 coordinator record, not on the owner-facing page that makes the verbatim claim. Fix: add it as a third bullet and say "Three". (Minor same-section wording: "Three bare references … Both were checked".) | **Yes** — r1 fold. |

### Action-clause sweep — MOVED-only clauses (all Low — FILE)

Each is absent from the spine and present only in an on-demand doc. For each: would a coordinator acting
from the spine alone act wrongly?

| # | Master clause (now only in `review-method.md` / `process-checklists.md`) | Wrong action from the spine alone? |
|---|---|---|
| S1 | Bounded wait (never wait passively; no waiting-on-Codex report across turns; fall back at once only on limit, auth or HTTP error, or no output file) | Possibly: the spine kept the output-file read and the quiet-file rule but did not forbid ending a turn on a waiting report. Low: memory rows on waiting lines cover it. |
| S2 | Fallback: the Claude replacement review is noted "so the Codex-specific pass can be **re-attempted before merge** if/when access returns" | Yes, mildly — the spine says note the gap, not re-attempt it before merge. A coordinator would merge on the fallback alone. Low: the fallback itself "satisfies the gate for proceeding". |
| S3 | `codex-review.py` comment: "`--verdict` is RETIRED (rc=2)" | Yes, narrowly — the spine maps rc=2 to "CANNOT RUN → fall back", so a coordinator passing the retired flag from habit would fall back instead of fixing the invocation. Low: requires a stale invocation. |
| S4 | Handoff lagging check: "if a resume ever finds a `handoff-XXXXXX.md` in `$TMPDIR`, something wrote one anyway" | Yes — a resuming coordinator would not look; the spine keeps only the leading gate. Low: layer 2 still blocks the wrong path before anything is written. |
| S5 | `check-python-pin.py`: "the rule is *every job pins **or is exempt with a reason***" | The spine row says "every CI job pins Python" — stricter than the guard. A coordinator adding a non-python job would add a needless pin; not harmful. Low. |

Every other unit of the 90 is PRESENT in substance in the spine (including all r1/r2 restorations: commit
before spawning and the three serialise-only hazards, alternation `REVIEW GAP` line, resolver refusal →
`codex exec -m` in a worktree, rc=3 recovery, output-contract and writer-dir filing, failed capture with no
findings section, prefer the finding-reporting reviewer, completion-ping caution, `--self-test` after
touching the wrapper and the handoff guard, bounded one-check fallback with full file access, plan-leak
8-word bound / per-clone install / not in CI, schema-gates workflow before the required-check setting,
thrashing rule, round cap) or is measurement/history/guard-internal behaviour that changes no coordinator
action (e.g. selection-card shape details, which the hook enforces; plan-mode `rc=2` refusals; memory-index
units; the `check-plan-code` 10-minute local refusal, which the tool announces itself).

## r2 fold specifically

- The re-measured per-file rows, total, −44%, and token figures (5.2k / 520 / 6.5k) match `len()` within
  the stated rounding. The 166-line statement is correct.
- The two restored plugins clauses (`--self-test` after touching the wrapper; one quick check / single
  re-run, full file access) are faithful to master.
- The dashboard rewording ("a different measurement; the two need reconciling") removes the unsupported
  inference. No new false statement found in the r2 diff itself; F1–F3 survive from the r1 fold.

No file under `.claude/plans/` was read.

VERDICT: NOT CONVERGED
