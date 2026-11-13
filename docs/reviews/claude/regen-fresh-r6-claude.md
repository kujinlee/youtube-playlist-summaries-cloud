Reviewed head: 36eabe19c78b528e2b411e322681ae7b6c7815c0

# regen-fresh — round 6 (Claude): the loosening answers on the post-merge tree (PR #536, backlog #408)

Scope is narrow: re-answer the 26 lines `check-merge-ready.py --pr 536 --flagged-block` flags, judged on THIS tree, and confirm the merge of master changed nothing in the runner.

## 1. The merge `36eabe19` touched nothing in the runner

- `git diff 77b2247c 36eabe19 -- scripts/regen-pages.py scripts/regen-pages.sh scripts/explainer-serve.py` is empty (0 lines).
- `git diff --stat 77b2247c 36eabe19 -- scripts/` lists 7 files (check-main-drivable, check-usage-pace, goal-tree and their mutation manifests, expected_mutations.py). That stat is identical, file for file and line for line, to master's own change from the merge base to `311d3631` (PR #537). The merge added nothing of the branch's own, and changed nothing else in `scripts/`.

## 2. Each flagged path, judged on this tree

**explainer-serve.py `_regenerate` (fb89f268396d, 712c0aacc4cf).** Master ran the generator directly with `subprocess.run(..., timeout=left)`. The branch runs `REGEN_EXEC([python, regen-pages.py, --page, want], timeout=left)`, where `REGEN_EXEC is run_in_group` (a self-test case asserts this). Every outcome master reported is still reported:
- a timeout raises `TimeoutExpired`, and `run_in_group` re-raises it after SIGTERM/SIGKILL to the group, so the handler still sends 504;
- any non-zero exit still gets 500. The runner's `--page` exit is the generator's own rc (124 on a timeout, -1 → 255 when `launch` raised, negative → 128+n when a signal killed it), or 2 for CANNOT RUN or an unknown page, or 1 for an unexpected exception. None of these is 0;
- the allow-list check (400) comes before the call, unchanged, and `want` reaches the argv only after it passes.
The runner can also refuse things master never could (a stale tree is CANNOT RUN). That adds refusals; it does not remove any.

**explainer-serve.py self-test spies (4fbb22a7ffb6, d3cc57ddef63).** The monkeypatch moved from `subprocess.run` to `REGEN_EXEC`, which is the seam production now calls. The 504/500/signal cases still drive through it. The argv cases now assert the runner's argv, and a new case checks every key. 239/239 pass.

**regen-pages.py docstring EXIT CODES (606dad727ce8).** It is extended, not weakened: `--hook` 0, `--all` 0/1 plus 2 for CANNOT RUN, and `--page` the generator's rc or 2. `main` does exactly this.

**`launch` (935e69a64e55, 705455503855, 0ca3caeb1539, 06eb9b4d1609).** Master: a timeout → 124, otherwise the generator's rc. The branch keeps both: `p.wait(timeout)` → 124 "timed out after Ns", otherwise `p.returncode`. It also ends the whole process group before returning, and says so when the group survived SIGKILL. The output tail is now stdout+stderr in full, not the last 300 characters of one of them. That is more text, and none of it is a refusal. The `stdin=DEVNULL` and `errors="replace"` arguments are kept.

**`regen` (68a9fd0367a4).** It gains a `tree` parameter, and `run` takes `(script, timeout, tree)`. It still never raises: an exception becomes rc -1 and the other pages still run.

**`main` (e29b3fb8fa9a, ef8c9de45337, b25e1072da48, 0670c030fae3).** The timing, the report and the `--all` exit 1 on any non-zero rc are unchanged. They now run inside `with tree_for() as (tree, sha)`, which adds a CANNOT RUN exit (2 for `--all`/`--page`, 0 plus a printed line for `--hook`). The unexpected-exception fallback `1 if a.all else 0` became `1 if loud else 0` with `loud = a.all or a.page is not None`. That is a superset: `--all` still exits 1 there. A stop signal raises `SystemExit(128+n)` from `_on_signal`. The `except Exception` does not catch it, so it exits non-zero after the tree is discarded.

**Self-test fakes and drives (51049a3f8433, 75ec8edc4012, 27004bcf2f0b, 4a9e19b085f0, 647fd36ca84a, 1004179b2d29, afddc8ea43c6, 302dad7bb9d4).** These are signature changes only, `(s, t)` → `(s, t, w)`, plus an injected `tree_for`. Every master assertion is still there with the same expected values: the failing/hung/raising trio and its rcs `[1, 124, -1]`, the named failure lines, `--hook` exit 0 with "NOT rebuilt", `--hook` on an unrelated or garbage payload launching nothing (`1 / 0` run), and `--all` exiting 1. New cases add the fresh-tree hand-off and the CANNOT RUN exit 2. 107/107 pass.

**regen-pages.sh (e2fc910cf7f5, 62376f70e7a2, 0b55d8682aec, e74a4c7a0c52).** Master looped over four generators and exited 1 when any failed. The branch keeps the `~/explainers` exit-2 refusal and then runs `exec python3 scripts/regen-pages.py --all`, so the runner's exit code is the script's. `--all` runs `sorted(REGENERABLE)`, which contains all four of master's generators (gen-backlog-page, gen-goals-page, gen-features-page, gen-dashboard) plus goal-tree. It exits 1 when any fails and 2 when the fresh tree cannot be made. One change is not a refusal: master's per-generator log in `/tmp/regen-<g>.log` is gone. Its content now appears inline in the report (each failure's name, exit code and output tail).

## 3. Runs on this tree

- `python3 scripts/regen-pages.py --self-test` → rc 0, `107/107 self-test cases passed`, 0 `[FAIL]`, 24 s.
- `python3 scripts/explainer-serve.py --self-test` → rc 0, `239/239 passed`, 6 s.

No findings.

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
