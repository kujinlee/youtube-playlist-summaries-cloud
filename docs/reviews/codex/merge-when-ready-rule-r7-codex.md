<!-- codex-review: model=gpt-6.1-sol -->

1. **High — filename decoding breaks exact blob ownership, producing false READY.** `scripts/check-merge-ready.py:424`, `:724`, `:782`.

   Executed in a real scratch Git repository with two distinct paths:
   - `scripts/check-a\n.py`: `sys.exit(1)`
   - `scripts/check-a\r.py`: `sys.exit(0)`

   Committed a change replacing the first gate’s `sys.exit(1)` with `sys.exit(0)`. Production-style `subprocess.run(text=True, errors="replace")` translates CR to LF in Git’s output. Both tree entries therefore acquire the same dictionary key; the unchanged second file overwrites the changed gate’s old blob.

   Executed result:
   ```text
   status: M
   hunks: []
   hold_reasons: []
   final_verdict: (0, 'READY')
   ```
   The gate’s removed failure line is missed because another file supplies its blob identity. Read machine paths as bytes, or preserve them with reversible decoding without newline translation.

2. **High — a gate’s symlink target can weaken outside the inspected roots without a HOLD.** `scripts/check-merge-ready.py:713`, `:780`.

   Executed in another real Git fixture:
   ```text
   scripts/check-linked.py -> ../tools/gate.py
   ```
   Changed the committed target from `sys.exit(1)` to `sys.exit(0)`. Running `python3 scripts/check-linked.py` then returned zero.

   Collection sees only `tools/gate.py`, assigns no hunks, and never associates it with the gate:
   ```text
   hunks: []
   hold_reasons: []
   final_verdict: (0, 'READY')
   ```
   Resolve gate symlink targets against the committed trees, or refuse readiness when their changed targets cannot be inspected.

Executed verification:

- Required self-test: **180/180 passed**.
- Green control followed by all **62 mutations: 62 killed through named assertions**.
- First-parent replay: **8/40 held**, unchanged: #398, #387, #386, #382, #381, #367, #366, #360; **313 Git calls**.
- Rename-plus-directory counterexample now HOLDs under all four diff algorithms, both indent-heuristic settings, and `core.autocrlf=true`.
- Exit precedence remains correct: READY plus exception → **3**; NOT READY → **1**; CANNOT RUN → **2**.
- Repository unchanged; no review file written.

VERDICT: NOT CONVERGED
