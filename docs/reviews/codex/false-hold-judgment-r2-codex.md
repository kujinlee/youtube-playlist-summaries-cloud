<!-- codex-review: model=gpt-6.1-sol -->

Reviewed HEAD `358a3220`, the round-1 reports, the fold, and `origin/master...HEAD`. **Five MAJOR findings and one MINOR remain.** Reproductions used temporary repositories with GitHub checks stubbed green. No tracked files or GitHub state were changed; `.claude/plans/` was not read.

The original reproductions now HOLD: fenced examples provide no answer; an ignored submodule moving after review returns **3**; the original trailing-whitespace count change is flagged. All seven Claude M1 probes now produce findings and beat assent. The fold nevertheless has the following gaps.

1. **MAJOR — A moved line lets the trailing-whitespace bypass return.**  
   `scripts/check-merge-ready.py:859–865` consumes moved lines from `readded` but leaves them in `raw`. A later rising-count comparison can reuse the consumed raw line when another addition has the same stripped text.

   Concrete original `scripts/check-k.py` (`␠` denotes one ASCII space):
   ```python
   def a():
       expected = """--self-test # 9 cases␠
   """
       return 1

   def b():
       expected = """--self-test # 6 cases␠
   """
       if expected.split("cases", 1)[1].startswith(" "):
           return 1
       return 0

   def c():
       pass
   ```
   Move `a()`’s assignment, including its closing triple quotes, into `c()`. Simultaneously change `b()`’s string from `6 cases␠` to `9 cases`, dropping the space.

   With the actual Git-generated diff, **`b()` changes from 1 to 0**, while `failure_path_flags()` and `hold_reasons()` both return **`[]`**. No reviewer answer is required. The standalone round-1 example is fixed; combining it with move detection defeats the fix. Both exemptions need one shared, occurrence-aware addition budget.

2. **MAJOR — Closing and reopening HTML comments on one line exposes quoted assent.**  
   `scripts/codex-review.py:898–915` stops processing a line after recognizing a comment close. It misses another opener later on that line.

   This review has no actual answer:
   ```text
   <!-- first --> <!-- still quoted
   LOOSENING-CHECK c8dcfcab4a36: not a loosening
   -->
   ```
   The parser nevertheless returns affirmative assent. Recorded against the matching tree containing the original `return 1` → `return 0` reproduction, **`main()` returns 0**.

   The sibling form below also clears:
   ```text
   <!-- first
   --> <!-- still quoted
   LOOSENING-CHECK c8dcfcab4a36: not a loosening
   -->
   ```
   Ordinary and unclosed fences remain safe. A fence marker embedded inside a finding’s answer line does not hide that finding. Nested-comment probing confirmed that the parser ends at the first close; the two valid close/reopen examples above establish the bypass without relying on nested-comment semantics.

3. **MAJOR — The new record exemptions permit unreviewed executable changes.**  
   `scripts/check-merge-ready.py:894–895,958` exempts arbitrary content beneath `docs/reviews/coordinator/`. It also treats the supposedly single decision-log file as a **prefix**.

   Concrete runtime reproduction: a gate loads `DENY` using:
   ```python
   DENY = runpy.run_path("docs/reviews/coordinator/policy.py")["DENY"]
   ```
   Its reviewed branch changes the flagged failure return from `1` to `2`, retaining refusal. Record exact-tree assent, then commit only `policy.py` changing `DENY = True` to `DENY = False`. The gate’s bad-input result changes **2 → 0**, yet merge-ready remains **0**.

   Independently, changing the existing file
   `docs/reviews/decision-scheme/decision-log.jsonl.extra.py`
   after review also preserves the answer and returns **0**. That file is not the named decision log.

   Controls: an ordinary file edit, a rename from an ordinary path into coordinator, a mode change, a symlink change, and the ignored submodule move all return **3**. The problem is the exemption’s scope, rather than whole-tree enumeration.

4. **MAJOR — Neutral prose becomes a permanent finding.**  
   `scripts/codex-review.py:930–932` interprets any mention of the token and an ID as dissent:
   ```text
   The LOOSENING-CHECK parser was exercised for c8dcfcab4a36.
   LOOSENING-CHECK c8dcfcab4a36: not a loosening
   ```
   This parses as `{"c8dcfcab4a36": "finding"}`. The real-git gate returns **3**, despite the explicit assent and absence of dissent. The cross-tree finding rule then prevents later clean assent from clearing it while that record remains.

   Sibling probes with quoted/listed assent likewise manufacture findings. Loose dissent recognition needs to distinguish an answer from explanatory prose or examples.

5. **MAJOR — A corrected replacement cannot retire the earlier finding.**  
   `scripts/check-merge-ready.py:966–977` assumes that an unchanged ID means an unchanged defect. The ID hashes the **removed base text**, not its replacement.

   Concrete sequence:
   - Master: `return 1`.
   - Round 1: replacement `return 0`; reviewer records a finding for `c8dcfcab4a36`.
   - Fix: replacement becomes `return 2`, restoring refusal.
   - Round 2: reviewer records exact-tree `not a loosening`.

   **The result remains 3**, with the earlier finding cited as applying to an unchanged line. The replacement changed and the defect was fixed; its ID cannot change through that fix because master’s removed text remains `return 1`. Carrying findings across unrelated tree edits works, but carrying them across repairs needs evidence about the reviewed replacement or an explicit resolution mechanism.

6. **MINOR — Wrapped dissent is still lost beside another half’s assent.**  
   The parser’s same-line boundary is documented, but remains a concrete dissent-loss case:
   ```text
   LOOSENING-CHECK
   c8dcfcab4a36: finding: return 1 now 0
   ```
   This parses as `{}`. With canonical assent from the other half, the real-git gate returns **0** for the loosening. All seven original M1 spellings are fixed; splitting the token and ID across a newline escapes the new rule.

`--flagged-block` checks: a clean tracked tree correctly falls back to HEAD; tracked uncommitted changes are included; an untracked new file adds no removal flag. Forcing `git stash create` to fail with an index lock produces **rc=2**, empty stdout, and a `CANNOT RUN` diagnostic. I found no additional bypass in that failure path.

Mutation verification passed. Every anchor in both current manifests matched exactly once. Every new or changed entry since `origin/master` was killed through its exact named case:

| Manifest | Fold: new + re-anchored | Total checked since master | Named-case kills |
|---|---:|---:|---:|
| check-merge-ready.json | 15 + 5 | 31 | 31/31 |
| codex-review.json | 8 + 2 | 13 | 13/13 |

The staged controls passed. These mutations do not cover the failing combinations above.

```text
check-merge-ready.py --self-test:     308/308 self-test cases passed
codex-review.py --self-test:          227/227 passed
record-review-verdict.py --self-test: 100/100 passed
```

LOOSENING-CHECK 26a23836138b: not a loosening
LOOSENING-CHECK 795043e96b8f: not a loosening
LOOSENING-CHECK c7f21f95034a: finding: the replacement loop permits reviewer-answered failure-path removals to clear, whereas master held every such removal.
LOOSENING-CHECK 6bd002a6d73a: finding: master’s unconditional failure-path HOLD is now skipped for rising-count exemptions and reviewer-answered lines; the moved-line reproduction also exempts a meaningful trailing-space deletion without review.
LOOSENING-CHECK e8b3c3bfbf22: finding: the replacement HOLD accepts parsed assent that can come from a reopened HTML comment and preserves assent across executable changes under the new record exemptions.
LOOSENING-CHECK f13e64d753fa: not a loosening

VERDICT: NOT CONVERGED
