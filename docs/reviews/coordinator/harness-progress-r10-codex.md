<!-- codex-review: model=gpt-5.5 -->

Verdict: **NOT CONVERGED**

**Finding: Medium — `EXAMINED_KEYS` preserves static call text, not executed coverage.**

Existing code premise: `analyse()` walks every AST call under the suite with `ast.walk(suite)` at [scripts/check-fixture-variation.py:486](/tmp/harness-r10-review.5rffA7/tree/scripts/check-fixture-variation.py:486), accepts only bare-name calls at [scripts/check-fixture-variation.py:487](/tmp/harness-r10-review.5rffA7/tree/scripts/check-fixture-variation.py:487), and returns key identity as `function.parameter` at [scripts/check-fixture-variation.py:557](/tmp/harness-r10-review.5rffA7/tree/scripts/check-fixture-variation.py:557). The per-file floor then compares only `pinned - keys` at [scripts/check-fixture-variation.py:652](/tmp/harness-r10-review.5rffA7/tree/scripts/check-fixture-variation.py:652).

Measurement: I loaded the archived `228ea1fc` guard and ran synthetic files through `analyse()` and `main()` with pinned `EXAMINED_KEYS`.

Failing scenarios:

- Dead branch:
  `def target(a)` plus `_self_test()` containing `if False: case(... target(1) ...); case(... target(2) ...)`.
  Runtime `target` calls: `[]`.
  Guard result: `keys == ['target.a']`, findings `[]`, `main rc == 0`.

- `TYPE_CHECKING` branch with runtime signature different:
  `if TYPE_CHECKING: def target(a, b)` else `def target(a)`, and both two-arg calls under `if TYPE_CHECKING`.
  Runtime `target` calls: `[]`.
  Guard result: `keys == ['target.a', 'target.b']`, findings `[]`, `main rc == 0`.

- `functools.wraps` rebinding:
  original `target(a)` remains in source, but `target = functools.wraps(target)(wrapper)` makes the executed wrapper call original `target(1)` both times.
  Runtime calls: wrapper sees `1, 2`; original target sees `1, 1`.
  Guard result: `keys == ['target.a']`, findings `[]`, `main rc == 0`.

This makes the residual statement incomplete. It says name identity cannot distinguish same-name/same-signature replacement, and that “every case where the signature differs” is closed at [scripts/check-fixture-variation.py:222](/tmp/harness-r10-review.5rffA7/tree/scripts/check-fixture-variation.py:222). The `TYPE_CHECKING` scenario has a runtime signature difference, yet the old static signature and old static calls preserve the exact key set.

**R9 Fixes**

I did not find the r9 fixes themselves defective in the same narrow way. The manifest has 31 `check-fixture-variation.py` mutations; the r9 entries for lost/paid, pos-only, file-scoped exemptions, varargs, kwargs, per-file key pin, exempt-ratcheted, and deadness-name assertions are present around [scripts/mutations/check-fixture-variation.json:262](/tmp/harness-r10-review.5rffA7/tree/scripts/mutations/check-fixture-variation.json:262) through [scripts/mutations/check-fixture-variation.json:403](/tmp/harness-r10-review.5rffA7/tree/scripts/mutations/check-fixture-variation.json:403). The code handles varargs/kwargs at [scripts/check-fixture-variation.py:504](/tmp/harness-r10-review.5rffA7/tree/scripts/check-fixture-variation.py:504), partitions exempt/paid/lost at [scripts/check-fixture-variation.py:623](/tmp/harness-r10-review.5rffA7/tree/scripts/check-fixture-variation.py:623), and asserts deadness output naming at [scripts/check-fixture-variation.py:870](/tmp/harness-r10-review.5rffA7/tree/scripts/check-fixture-variation.py:870).

**Judgement**

(a) **New structural class**: static source reachability/binding is being mistaken for executed coverage. It is adjacent to r8/r9’s proxy-identity failures, but not just another missing signature grammar case.

**Verification**

Built subject first with `git archive 228ea1fc scripts | tar -x -C /tmp/...`; verified 113 archived script files against `git rev-parse 228ea1fc:<path>` blob hashes.

Controls:
`check-plan-code --self-test`: `128/128 passed`.
`check-fixture-variation --self-test`: `48/48 passed`.
Guard population: `402 parameter(s) examined across 48 file(s)`.

Mutation:
`python3 scripts/check-plan-code.py --mutate .` under redirected `HOME`:
`OK — delivered scripts mutated: 39 file(s), 502 mutation(s), 502 killed, 502 attributed to the case each names, 0 survivor(s)`.

**What The Author Did Not Measure**

Executed reachability of the static call sites; conditional/dead suite branches; runtime rebinding through decorators/wrappers; and attribute-call/classmethod coverage beyond bare `Name(...)` calls.

**What I Did Not Measure**

I did not exhaustively audit all 48 live scripts for existing dead-branch or rebinding instances. I tested representative adversarial fixtures against the archived guard and confirmed the full delivered mutation run.
