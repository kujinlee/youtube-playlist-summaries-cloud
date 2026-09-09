<!-- provenance (coordinator note, NOT Codex's words): this half needed TWO dispatches.
     Attempt 1 walked the full candidate list and produced nothing — gpt-5.6-sol/-terra/-luna
     all HTTP 400, gpt-5.5 timed out at the 900s default — and was recorded as a REVIEW GAP.
     Attempt 2 forced `--model gpt-5.5 --timeout 1800`, skipping the three deterministic 400s
     and giving the one reachable model the budget it needed. It succeeded in ~22 minutes.
     The intrusion line the wrapper printed names the coordinator's own stdout redirect target
     and is a false positive of the harness setup, not agent behaviour — adjudicated per
     backlog #92. Everything below the rule is Codex's verbatim final message. -->

<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Blocking** — `check-plan-file-tags.py:129` uses `splitlines()`, but the retired parser at `check-plan-code.py:196` uses `md.split("\n")`. The fence can therefore hide tags that `extract()` would assemble.

Observation I ran at exact commit `71f86f9a`: for `x<SEP>```\n<!-- file: m.py -->\n...`, `extract()` returned `['m.py']` while `audit()` returned 0 findings for `\v`, `\f`, `\x1c`, `\x1d`, `\x1e`, `\x85`, `\u2028`, `\u2029`, and `\r`.

That is the core fence claim failing in the dangerous direction: a live plan-mode tag can pass the replacement guard.

**High** — The guard is still falsifiable by narrowing the live corpus. `DOCS = ROOT / "docs"` is not covered by self-test; all self-test cases call `audit(root)` on temp roots. A mutation equivalent to `DOCS = ROOT / "docs" / "reviews"` leaves both the self-test and live run green while skipping non-review docs.

Observation I ran at `71f86f9a` by monkeypatching `ft.DOCS`:
`main([])` returned `0`, printing `plan-mode tags: 0 across 895 documents under docs/`; `main(["--self-test"])` returned `0`, printing `21/21 self-test cases passed`.

This means the green live baseline proves only that the selected corpus is clean, not that the intended corpus is still selected.

**Low** — The recorded `--mutate` conflict branch is unreachable for retired flags. `main()` checks `retired` before `a.mutate`, so `--mutate ROOT --evidence` and `--mutate ROOT --compare DIR` return the generic plan-mode retirement message, not the later “--mutate cannot be combined” message.

Observation I ran: `pc.main(["--mutate", td, "--evidence"])` returned rc `2` with “plan mode was RETIRED… --evidence belonged to it.” It does not reach the branch at `check-plan-code.py:3466-3473`. Behavior is still fail-closed, but the comment says a more specific refusal exists when it cannot fire.

**Checks / Non-Findings**

`check-plan-file-tags.py --self-test`: `21/21 self-test cases passed`.

Live guard: `plan-mode tags: 0 across 1115 documents under docs/`.

`EXPECTED_MUTATIONS`: AST sum is `382`; `scripts/check-plan-file-tags.py` is `8`; manifest length is `8`.

`check-plan-code.py --self-test`: initially red in an isolated worktree because ignored `node_modules/typescript` was absent; after symlinking the repo’s `node_modules`, it passed `229/229`.

Targeted manifest verification for `check-plan-file-tags.py`: green control before and after, 8 declared, 8 measured, 0 survivors.

CANNOT RUN to completion: full `python3 scripts/check-plan-code.py --mutate .`. I tried twice; both ran for several minutes with no final output and were interrupted, the second while inside `run_mutations`.
