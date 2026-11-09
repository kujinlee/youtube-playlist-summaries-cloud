Reviewed head: 15178418a283ebf21ab1ba4cbc85805fe4a80bb1

# Round 5 — `held-pins-head` (PR #541, backlog #538) — Claude half

Scope: `git diff 31aac2aa 15178418` (one self-test case in `scripts/check-merge-ready.py`, two re-anchored entries
in `scripts/mutations/check-merge-ready.json`, plus round-4 records). Past the round cap: only a BLOCKER would be
fixed; anything else is filed.

## What was run (all at 15178418, worktree clean)

- `python3 scripts/check-merge-ready.py --self-test`: **400/400 passed**, rc 0 (58 s).
- Hand-check, one entry at a time, in a `stage_tree` copy, through the helper `handcheck.py` (read first: it loads
  `check-plan-code.py`'s own `load_manifests` / `stage_tree` / `run_suite` / `parse_fail_names`, asserts each
  anchor occurs exactly once, applies the edits, runs the suite and counts the named expect):
  - "a failing `git ls-tree` is read as an answer" (backlog #359 r3): rc 1, **1 fail, exactly the named case**.
  - "the child's driver checks pin_display's answer with isinstance": rc 1, 5 fails, the named case included
    (the other 4 are the dict-subclass / int-subclass siblings, as expected when `isinstance` admits subclasses).
  - "the child's driver checks the dict but not its keys and values": rc 1, 3 fails, the named case included.

## 1. Is the case stricter?

Yes. The old predicate was `startswith("CANNOT RUN") and "`git {w}" in r and "exited 128" in r`. The new one is
`startswith("CANNOT RUN") and want in r`, where each `want` (`` `git merge-base m HEAD` exited 128 ``,
`` `git ls-tree` exited 128 ``, `` `git show` exited 128 ``) contains both old substrings. So every string the new
case accepts the old one accepted too. And it now tells the masking message apart: `_head_blobs`' refusal is
"HEAD: `git ls-tree` of scripts/ exited 128", which does NOT contain `` `git ls-tree` exited 128 ``, while
`pins_home`'s own refusal ("{rev}: `git ls-tree` exited 128") does. The hand-check confirms that the mutation the
case names (pins_home ignores the rc) is now red through this case alone.

## 2. Is the re-anchoring honest?

Every caller of `_exact_pins` at HEAD (`grep -n "_exact_pins("`, `_cross(... reduce=_exact_pins`):
- `_child_pins` (line 1660), reached only from `pin_pair` (lines 1691, 1692, 1694), on `ans[...]` that
  `_head_read` has already passed through `_child_answer_ok`. That function demands `type(a["pins"]) is dict` and
  `type(k) is str and type(v) is int` for every item. The answer comes from `_json_strict`, whose
  `object_pairs_hook` builds a plain `dict`, and JSON decodes only to exact `str` / `int` / `bool` / `float` /
  `None` / `list` / `dict`. A JSON `true` is a `bool` and `_child_answer_ok` refuses it. So no bool, subclass or
  non-int can reach `_exact_pins` from this caller.
- The self-test at line 3244 passes the REAL `pin_display` output of the real display: a plain `{str: int}`.

So `_exact_pins`' type checks cannot fire on any input the code gives them. Its `if not out` (empty → ValueError)
is still reachable (a harness holding `{}`). The two mutations against its type checks were equivalent, and the
CI sweep was right to report them as survivors.

Each re-anchored mutation names a REAL defence. The driver is the only layer that sees the Python object
`pin_display` returned. Under `isinstance` (or `if False:`), `{k: True}` passes and `_int.__int__(True)` serialises
as `1`. JSON then erases the bool, so nothing downstream can see it. The named case requires
`"TypeError: pin_display" in _o`, so the CANNOT RUN that the held-versus-displayed comparison would also produce
cannot answer for it. That is the second clause that masked these entries before backlog #536, and it does not
mask them now: the hand-checks above go red through the named case.

Could the same edit simply delete `_exact_pins`' type checks? Yes. Deleting them changes no verdict, which is
exactly why they are now unpinned. That is not BLOCKING. The lines are a redundant second copy of a check the
driver and `_child_answer_ok` both make first, and removing them would not loosen the gate. What remains is
documentation drift, R5-F1.

## Findings

### R5-F1 — Low — `_exact_pins`' docstring and one test comment still describe the type checks as load-bearing

- `scripts/check-merge-ready.py` `_exact_pins` docstring: "⚠ The type checks carry the rule". Since the r2 child
  read, they can no longer fire. The rule is carried by the `_DRIVER`'s `answer` and by `_child_answer_ok`, and no
  mutation pins these lines any more.
- The comment above the "⭐ main() is CANNOT RUN, rc=2, when pin_display returns …" cases (around line 3950) says
  the refusal must be "`_exact_pins`'s TypeError on what pin_display returned". It is now the driver's TypeError,
  relayed through the child's `{"error": ...}`.

Both are wording only. Either delete the dead type checks, or label them as a redundant fallback that the driver
pre-empts. FILE, not fix (round cap; not a BLOCKER).

No BLOCKING finding.

## Flagged lines

These are the same 15 ids round 4 answered: master's `pins_at`, `held_pins`'s call and `pin_pair`'s two reads,
plus one self-test case. Commit 15178418 does not touch any of those paths. I re-checked each against the branch:

- `pins_at`'s `{}` for a tree with neither file → `pins_text` returns (None, None) → `old`/`new` = `{}`. Same.
- `git ls-tree` / `git show` failure → `pins_home` / `pins_text` raise `PinsUnreadable`. Same, and the case is
  stricter now.
- A reader that refuses, raises (SystemExit included) or returns a non-exact type → the driver's `answer` gives
  `{"error": ...}`, or `_child_answer_ok` refuses → CANNOT RUN. An empty answer → `_exact_pins` ValueError.
  `held_pins` → `_child_pins(ans["held"])`, with the same differ comparison.
- The branch adds refusals that master did not have: a timeout, a non-zero exit, non-JSON or off-schema output,
  bytecode, stdlib-named files, a head with no harness while the base has a display.
- The self-test case at master 2974-2975 survives at lines 3333-3336, and is stricter: it also requires
  "SystemExit" in the reason.

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
LOOSENING-CHECK 7514eca741d1: not a loosening
LOOSENING-CHECK 90f61d5b450f: not a loosening

VERDICT: CONVERGED
