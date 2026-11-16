# Round 2 — `idle-stop-guard` — coordinator — ⟳ NOT CONVERGED (Codex half)

Codex (`gpt-6.1-sol`, `docs/reviews/codex/idle-stop-guard-r2-codex.md`) reviewed `db0db19d`: 5 MAJOR, 1 MINOR,
NOT CONVERGED. Self-test 73/73 and 79/79 mutations killed, quoted by the reviewer.

REVIEW GAP: claude — alternation (rounds 2+ run one half; Claude reviews round 3).

```yaml
round: 2
fixes_nontrivial: true
subject: idle-stop-guard
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: true, component: question-exception, disposition: fixed}
  - {id: XM2, severity: Major, aim: deliverable, fix_induced: false, component: payload-reader, disposition: fixed}
  - {id: XM3, severity: Major, aim: deliverable, fix_induced: false, component: payload-reader, disposition: fixed}
  - {id: XM4, severity: Major, aim: deliverable, fix_induced: false, component: ci-signal, disposition: fixed}
  - {id: XM5, severity: Major, aim: deliverable, fix_induced: true, component: worktree-signal, disposition: fixed}
  - {id: Xm6, severity: Minor, aim: deliverable, fix_induced: true, component: self-test, disposition: fixed}
```

**Fix-induced:** XM1 (the AskUserQuestion exception is the r1 fold's), XM5 (the walk budget is the r1 fold's),
Xm6 (the question cases are the r1 fold's). **Thrashing check:** this is the FIRST fix-induced round; Phase 6
arms only if round 3 also carries findings caused by this round's fix in one component.

## Dispositions — decided by the coordinator before the fold

| Finding | Disposition | Direction for the fold |
|---|---|---|
| **XM1** — an ANSWERED `AskUserQuestion` keeps the exception: ask → "Yes" → "Starting now." → stop ALLOWS with nothing running | FIX | An answered question is not a reason to stop — the answer is work to act on. The exception holds only when the `AskUserQuestion` call has NO answering `tool_result` after it, or its result is a rejection/dismissal. Measure what a dismissed card records in a real transcript if you can; otherwise state it as UNVERIFIED in the docstring. |
| **XM2** — `splitlines()` splits on U+2028 inside a JSON string, so a human record is skipped | FIX | Split JSONL on `\n` only. Add a case with a literal U+2028 in a human prompt. |
| **XM3** — a deeply nested record raises `RecursionError`, exits 1, and so ALLOWS | FIX | A record that cannot be parsed for ANY reason (including `RecursionError`) makes the transcript UNREADABLE → fail closed (block), as other unreadable evidence does. Case through `main()`. |
| **XM4** — `statusCheckRollup: 42` or `status: []` raises `TypeError` → exit 1 → ALLOWS | FIX | Validate the `gh` JSON shape; anything malformed is NOT CHECKED → block. Cases for both inputs. |
| **XM5** — the 1.0 s walk deadline is not checked inside the file loop (13 s measured with 10 ms `lstat`) | FIX | Check the deadline per entry; exceeding it is NOT CHECKED (fail closed). Case with an injected slow `lstat` through the real walk. |
| **Xm6** — mutating the list-form human prompt test to `False` survives | FIX | Add the killing case: AskUserQuestion, then a human prompt as `[{"type":"text","text":"Continue"}]`, then a closing reply → BLOCK. |

## Fold

Self-test 73 → **93/93**; mutations 79 → **99, 99 killed, 0 survivors** (four shards of 25/25/25/24, each run on
the final files and each attributed to the case it names). **Red before:** the new cases written first ran
**78/90 against the unfixed code, 12 red** — XM1 5, XM2 1, XM3 3, XM4 2, XM5 1; Xm6's case is green on correct
code by design and is red under the reviewer's mutant (`False and any(`: 73/90).

| Finding | Change | Red before | Measured / bound |
|---|---|---|---|
| **XM1** | `last_tool_asked` tracks the card's `id`; a `tool_result` for THAT id answers it unless it is the owner's rejection (`is_error: true` and the text `doesn't want to proceed`, string or list form). The exception holds only for an unanswered or rejected card; a card with no id, or one a HOOK refused, gets none. | 5 | Measured over 207 `AskUserQuestion` results in this project's transcripts: 9 owner rejections (`is_error`, "The user doesn't want to proceed with this tool use…"), 47 hook refusals (`is_error`, "PreToolUse:AskUserQuestion hook error"), the rest answered (`is_error` false). **Bound:** if the harness rewords the rejection text, a rejected card reads as answered → BLOCK, never ALLOW (stated in the docstring). |
| **XM2** | The tail is split on `\n` only. A torn FIRST or LAST line (the tail's cut, a write in progress) is skipped; a torn MIDDLE line makes the transcript unreadable (None). | 1 | 837 transcripts split on `\n`: 0 unparseable lines; 47 contain U+2028/U+2029 (so `splitlines()` was live, not theoretical). The U+2028 case now asserts the prompt is READ (False, not None) — the first version survived the `splitlines` mutant because an unreadable transcript also blocks. |
| **XM3** | Every parse of outside data catches every exception. An unreadable transcript drops the exception and the refusal says so. | 3 | Through `main()`: a record nested 200,000 deep → exit 2, naming the transcript. **Class search found two siblings, both red on HEAD:** a deep `gh` answer (`pending_ci` raised `RecursionError`) and a deep usage cache (`usage_stop` raised it) — both fixed and cased. |
| **XM4** | `pending_ci` validates shape: a rollup that is not a list or null, a check that is not an object, a `__typename`/`status`/`state` that is not a string or absent → None (unread → block). | 2 | Cases: rollup `42`, status `[]`, state `{}`, check `"x"` → `[None]*4`; an absent status and a null rollup are well formed (`[]`). `decide` over a malformed answer blocks and names (c). |
| **XM5** | `_recent` checks the deadline per FILE as well as per directory; the walk takes an injectable `lstat`. | 1 | 300 files at 10 ms an `lstat`, 0.2 s budget → None inside 1.5 s. A second case (empty directories on a per-call clock) keeps the per-DIRECTORY check load-bearing — the mutation run found it shadowed by the per-file check and SURVIVING until that case was added. **Bound:** one huge directory listing (`os.walk`'s own `scandir`) is still not interrupted (docstring). |
| **Xm6** | Case added: ask → list-form human prompt → closing reply → BLOCK. | 0 (kills the mutant) | Reviewer's mutant now dies. |

**Hook latency, re-measured through `.claude/hooks/check-idle-stop.sh`** in a scratch repo: a `gh` on PATH that
sleeps 30 s, a FIFO `transcript_path`, an empty HOME, and a builder worktree of 400,000 old files (the walk alone:
None in 1.01 s against its 1 s budget; unbounded it takes 4.75 s). Three runs: **exit 2 in 4.16 / 4.11 / 4.11 s**,
naming (a), (b) and (c) — under the 10 s hook timeout by ~5.8 s. Worst case by construction: `GH_TIMEOUT_S` 3 s
+ `WALK_BUDGET_S` 1 s + start-up.

**Gates (last lines):** `check-idle-stop.py --self-test` 93/93 · `check-plan-code.py --self-test` 506/506 ·
`check-selftest-counts.py --only scripts/check-idle-stop.py` verified (the full run is CI's — it exceeds the
270 s call limit locally) · `check-fixture-variation.py` OK · `check-ratchet-contract.py` OK ·
`check-guard-coverage.py` ✅ · `check-docs.py` OK. The mutation run used a staged copy of the tree (the harness
refuses `--only` with `--shard`); the pin `scripts/check-idle-stop.py: 99` is in `expected_mutations.py`.
