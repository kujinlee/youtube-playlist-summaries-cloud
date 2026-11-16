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
