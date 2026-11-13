<!-- codex-review: model=gpt-6.1-sol -->

Found five issues against the settled design:

1. **High — Declared waits break step/leaf parity.** [goal-tree.py:1038](scripts/goal-tree.py#L1038) passes `waits=None`. Constructed world: backlog #12 exists, has no PR or ledger entry; its tree leaf declares `waits="PR #20"`. The leaf derives **blocked**, while the agenda step naming exactly backlog #12 derives **next**. No other key read by `derive_thread` is missing.

2. **High — Replay silently loses or misattributes records.** [goal-tree.py:1014](scripts/goal-tree.py#L1014):
   - `[tick]` or `[replaced]` before any agenda produces `[]`, without reporting corruption.
   - `[agenda A, agenda B, replaced(of=A)]` closes **B**, ignoring `of`.
   - A delayed tick intended for A attaches to B; ticks carry no agenda identity.
   
   Concurrent replacements can produce this ordering: both callers read A, then each appends its replacement and new agenda. There is no lock or identity validation.

3. **Medium — Missing agenda files escape as exceptions.** [goal-tree.py:1549](scripts/goal-tree.py#L1549) calls `read_text()` inside a handler that catches only `Malformed`. With a missing path, I reproduced `FileNotFoundError`; CLI execution consequently prints a traceback instead of returning **2 / CANNOT RUN**.

4. **Medium — Closed agendas remain tickable.** [goal-tree.py:1070](scripts/goal-tree.py#L1070) never checks `replaced`. Constructed log: free-step agenda A followed by `replaced(of=A)`. `tick_agenda(..., 1, ...)` succeeds and changes A’s tick list after its replacement states were frozen. Repeating a tick also succeeds, producing `[1, 1]`; this is **Low** severity by itself because the displayed completion state remains unchanged.

5. **Medium — `--tick-agenda 0` triggers the default workflow.** [goal-tree.py:1538](scripts/goal-tree.py#L1538) and the tick dispatch use truthiness. Zero therefore selects default `--snapshot --page` and bypasses the range refusal. Check presence with `is not None`.

Other requested checks:

- The source-error predicate matches `derive()`’s truthy-error test. For collected worlds, any reported source failure makes replacement states `cannot`; I found no partly read replacement through that path.
- Without declared waits, constructed merged, open, next, closed, superseded and CANNOT worlds matched.
- Parser rejects indented steps, empty `##`, and whitespace-only windows; accepts CRLF and ref-only steps. These agree with its stated grammar. Duplicate `window:` lines silently overwrite earlier values—a validation gap, though the settled decisions do not explicitly prohibit duplicates.
- Mocked `main()` confirmed record-plus-snapshot captures the newly recorded agenda; record alone creates no snapshot. Malformed input and refused ticks return **1**.
- All **10** new mutation anchors occur exactly once. I ran all ten on a temporary scripts copy: each failed its named case, with **no traceback**.
- Mutation pin is **162**. Self-tests pass **276/276**, matching the docstring.

No tracked files modified; `.claude/plans/` was not read.

VERDICT: NOT CONVERGED
