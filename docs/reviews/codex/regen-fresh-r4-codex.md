<!-- codex-review: model=gpt-6.1-sol -->

Required self-tests passed: regen-pages **106/106**, session-state **132/132**, explainer-serve **239/239**. Scratch reversions of R3-F2 and R3-F3 made their named cases fail. Normal linked-worktree `main_checkout()` resolution returned the main checkout. No blocker reproduced; no real regeneration ran.

### R4-F1 — Low — accident — Docstring promises signal cleanup grace that the handler skips

`scripts/regen-pages.py:78–80` promises SIGTERM followed by `GROUP_GRACE` before SIGKILL, including when the runner receives a stop signal.

Input: SIGTERM to a runner with active generators. `_on_signal()` at `scripts/regen-pages.py:584` immediately sends their groups **SIGKILL**. A scratch probe recorded only SIGKILL, so generator termination handlers receive none of the documented grace. This is a documentation mismatch; no data loss or main-repository write was demonstrated.

## Loosening answers
LOOSENING-CHECK fb89f268396d: not a loosening
LOOSENING-CHECK 712c0aacc4cf: not a loosening
LOOSENING-CHECK 4fbb22a7ffb6: not a loosening
LOOSENING-CHECK d3cc57ddef63: not a loosening
LOOSENING-CHECK 606dad727ce8: not a loosening
LOOSENING-CHECK 935e69a64e55: not a loosening
LOOSENING-CHECK 705455503855: not a loosening
LOOSENING-CHECK 0ca3caeb1539: not a loosening
LOOSENING-CHECK 06eb9b4d1609: not a loosening
LOOSENING-CHECK 68a9fd0367a4: not a loosening
LOOSENING-CHECK e29b3fb8fa9a: not a loosening
LOOSENING-CHECK ef8c9de45337: not a loosening
LOOSENING-CHECK b25e1072da48: not a loosening
LOOSENING-CHECK 0670c030fae3: not a loosening
LOOSENING-CHECK 51049a3f8433: not a loosening
LOOSENING-CHECK 75ec8edc4012: not a loosening
LOOSENING-CHECK 27004bcf2f0b: not a loosening
LOOSENING-CHECK 4a9e19b085f0: not a loosening
LOOSENING-CHECK 647fd36ca84a: not a loosening
LOOSENING-CHECK 1004179b2d29: not a loosening
LOOSENING-CHECK afddc8ea43c6: not a loosening
LOOSENING-CHECK 302dad7bb9d4: not a loosening
LOOSENING-CHECK e2fc910cf7f5: not a loosening
LOOSENING-CHECK 62376f70e7a2: not a loosening
LOOSENING-CHECK 0b55d8682aec: not a loosening
LOOSENING-CHECK e74a4c7a0c52: not a loosening
VERDICT: CONVERGED
