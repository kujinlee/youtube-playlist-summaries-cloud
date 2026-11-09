Reviewed head: 0d9a226646ede8c5f12702115d086e54c9044807

# Round 7 — `held-pins-head` (PR #541, backlog #538) — Claude half: re-answering the flagged lines

Scope: the 16 flagged ids, against `scripts/check-merge-ready.py` at `0d9a2266`. This is not a new code review. I
read the r3 Claude review, the r3 coordinator record's "Phase 6 outcome", the Phase 6 architecture review
(`docs/reviews/architecture-review-2026-11-08-held-pins-child.md`), r4 (Codex), r5 (Claude) and r6 (Codex), and
`git diff 15178418 0d9a2266 -- scripts/`. Python 3.14.4, macOS (`/usr/local/bin/python3`).

## What I ran

| Check | Result |
|---|---|
| `python3 scripts/check-merge-ready.py --self-test` at `0d9a2266` | **400/400**, rc 0 (68 s) |
| Repro M: master's file (`b15e4f96`) as `python3 scripts/check-merge-ready.py --help`, in a real repository whose HEAD commits R3-F1's `scripts/importlib/__init__.py` | the shadow **RAN** (logged pid and argv), rc 0 |
| Repro M, the same entry point with `--pr 541` and a shadow that prints `FORGED: READY` and calls `os._exit(0)` | `FORGED: READY`, **rc 0**. Master's gate never evaluated the PR |
| Repro B, the branch's file (`0d9a2266`) as the gate process, the same two runs | the same: the shadow ran, `FORGED: READY`, rc 0. That is equal to master, not wider (backlog #578) |
| The branch's `pin_pair` read from outside `scripts/` (`python3 -I`), HEAD = lowered pin 5 -> 4 + the shadow | `CANNOT RUN: HEAD: 'scripts/importlib/__init__.py' is named for the standard-library module 'importlib', which it would shadow in the child`. The shadow did NOT run |
| The same, control: HEAD = the lowered pin only | `falls: ['loosens a gate: the mutation pin for scripts/check-vocabulary-collisions.py drops 5 -> 4']` |

Each repository was built fresh in my scratchpad: base = that revision's `scripts/` (bytecode removed), then a commit
lowering the pin, then a commit adding the shadow. The shadow delegates to the real `importlib` and logs to a file
outside the repository.

## R3's five ids: is "master never executed it" false?

**Yes, it is false.** Every r3 `finding:` answer rests on that premise, and it does not hold for master as it is
actually invoked. Master's gate runs as `python3 scripts/check-merge-ready.py`, so the WORKING TREE's `scripts/` is
`sys.path[0]`. `main()` refuses a working tree that is not the PR head, so it is HEAD's committed files. Master's
`import importlib.util` at the top of the file therefore runs a committed `scripts/importlib/__init__.py` before
`main()`. Repro M shows that this code can do anything, up to exiting rc 0 with no verdict. So master did NOT refuse
this input on any path; it ran the forge in the gate process itself.

On the branch, the same input reaching the child is refused, CANNOT RUN, at `_materialise` (the stdlib-name refusal).
The child path is therefore strictly tighter than master's in-process read. The gate-process exposure is identical
on both sides, and is backlog #578.

- **`46da71649200`** (`reader = _pins_reader(PINS_READER)`, now `_head_read` in a child). In master, this import ran
  in the gate process with the working tree's `scripts/` first on `sys.path`; a stdlib shadow had already run at
  startup. On the branch, the child refuses any stdlib-named top-level file (repro B: CANNOT RUN). Non-stdlib
  siblings, `coverage_verdict.py` today, were trusted by master too, and now come from HEAD's committed blobs rather
  than the working tree.
- **`ed1d0f2f0938`** (the `_cross(... pin_display ...)` parse, now the driver's `answer()` plus `_child_pins` ->
  `_cross(..., reduce=_exact_pins)`). The exact-type check moved into the driver, and `_child_answer_ok` plus
  `_json_strict` (duplicate keys refused) were added on top. The R3 forge route to rewrite the serialised parse is
  closed by the refusal (repro B). Master's parse could be forged by the same file (repro M).
- **`3e8b51e50547`** (`old = pins_at(run, merge-base)`). The base display is now parsed by HEAD's harness in the
  child instead of the working-tree harness in-process. `main()` already holds the two to the same commit. A base
  with no pins file is still `{}` (`base_home is None`). With the R3 forge, the branch says CANNOT RUN and master's
  gate exits rc 0 forged.
- **`be450713bce4`** (`new = pins_at(run, "HEAD")`). The same as above for HEAD's display. Repro B control: an honest
  5 -> 4 fall is still held.
- **`c47564441466`** (`held = held_pins()`). The held pins now come from the child's `held` answer through
  `_child_pins`. The held-versus-display comparison is unchanged. R3 says the check could be "forged without editing
  `check-plan-code.py`". That is true of master too: a stdlib shadow or a harness sibling in the working tree. The
  stdlib route into the child is now refused.

## The `ea055975` edit: self-test only

`git diff 15178418 0d9a2266 -- scripts/check-merge-ready.py` has two hunks, both at lines 3323-3327, inside
`_self_test_body` (lines 2064-4350, reached only from `_self_test` / `--self-test`). The edit adds a comment and
changes one `check(...)` from `r[:11] == "CANNOT RUN:"` to `(r[:11], "SystemExit" in r) == ("CANNOT RUN:", True)`.
Every result the new case accepts, the old one accepted too. No production line changed. The manifest gains one
entry (the child's import catch narrowed to `Exception`), and the old `_cross` entry's `expect` drops the reader
case. The pin moves 187 -> 188. r6 Codex hand-checked both; I did not re-mutate.

## The other 11 ids (checked, not re-measured)

- `d2d3b8498823`, `a3675a17d265`, `c65bf04c5a84`, `7987d773f208`, `aeac2f13505f`, `1ae2b3e74a4b`, `e36f8dfa2eb5`,
  `bb9bf96e21f2`: `pins_at` and its docstring become `pins_text` + `_head_read` + `_child_pins`. The no-file case is
  still `{}`. Every other failure is still `PinsUnreadable` with the rev and home in the message. A head with no
  harness is now CANNOT RUN even when only the base has a display (bound (b)), which is stricter.
- `584faa467301`, `7514eca741d1`, `90f61d5b450f`: self-test `check`s. Each now requires `"SystemExit" in r` in
  ADDITION to the `CANNOT RUN:` prefix (compared against master's text at `b15e4f96`), so each is strictly stronger.

## Loosening answers
LOOSENING-CHECK d2d3b8498823: not a loosening
LOOSENING-CHECK a3675a17d265: not a loosening
LOOSENING-CHECK c65bf04c5a84: not a loosening
LOOSENING-CHECK 7987d773f208: not a loosening
LOOSENING-CHECK aeac2f13505f: not a loosening
LOOSENING-CHECK 46da71649200: not a loosening
LOOSENING-CHECK ed1d0f2f0938: not a loosening
LOOSENING-CHECK 1ae2b3e74a4b: not a loosening
LOOSENING-CHECK e36f8dfa2eb5: not a loosening
LOOSENING-CHECK bb9bf96e21f2: not a loosening
LOOSENING-CHECK 3e8b51e50547: not a loosening
LOOSENING-CHECK be450713bce4: not a loosening
LOOSENING-CHECK c47564441466: not a loosening
LOOSENING-CHECK 584faa467301: not a loosening
LOOSENING-CHECK 7514eca741d1: not a loosening
LOOSENING-CHECK 90f61d5b450f: not a loosening
VERDICT: CONVERGED
