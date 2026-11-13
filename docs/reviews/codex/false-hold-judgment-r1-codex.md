<!-- codex-review: model=gpt-6-astra -->

Reviewed HEAD `54667f2cc6e26996f3d0ce17aad719a4fe9d55ab`, backlog #508/card A, and `origin/master...HEAD`. Found **three MAJOR bypasses**. Reproductions used temporary repositories; GitHub checks were stubbed green. No GitHub actions or tracked-file edits were made; `.claude/plans/` was not read.

1. **MAJOR — Fenced examples become affirmative reviewer answers.**  
   `scripts/codex-review.py:885–893` matches individual lines without tracking Markdown fences or HTML comments. Both verdict recorders inherit this behavior.

   Concrete gate change in `scripts/check-k.py`:
   ```diff
    def f(bad):
        if bad:
   -        return 1
   +        return 0
        return 0
   ```
   Its flag is `c8dcfcab4a36`. This review supplies **no actual answer**, but clears it:
   ````text
   The following is only a quoted example, not my answer:
   ```text
   LOOSENING-CHECK c8dcfcab4a36: not a loosening
   ```
   VERDICT: CONVERGED
   ````
   Observed: parser returns `{"c8dcfcab4a36": "not a loosening"}`; recording that on the matching tree makes `main()` return **0**, accepting the real loosening. Sibling probes using `~~~` fences and `<!-- … -->` comments also yield affirmative answers. Reject answers inside quoted/code/comment regions.

2. **MAJOR — An ignored submodule change preserves answers from a different tree.**  
   `scripts/check-merge-ready.py:955–965` obtains changed paths using `git diff`, then `tree_matches` compares only those paths and the dirty overlay.

   Concrete input: reviewed commit `R` contains gitlink `policy=A` and:
   ```ini
   [submodule "policy"]
       path = policy
       url = ./policy
       ignore = all
   ```
   Record an affirmative verdict with `head=R`, `dirty={}`, and `gate_ran=true`. After recording it:
   ```sh
   git update-index --cacheinfo 160000,B,policy
   git commit -m 'change policy after review'
   ```
   Here `A` and `B` are distinct commit objects. The actual `git diff --name-only R HEAD` omits `policy`; the tree indexes contain different gitlinks, but `tree_matches` never compares them.

   Observed: the stale answer remains usable and `main()` returns **0**. Ordinary post-review document changes correctly return **3**. Compare the complete tree-entry union, excluding only permitted review records, rather than trusting a configurable diff to enumerate differences.

3. **MAJOR — The rising-count exemption also permits meaningful trailing-whitespace changes.**  
   `scripts/check-merge-ready.py:825,837` strips trailing whitespace before `rising_count` compares the lines.

   Concrete original source, where the count line ends with **one ASCII space**:
   ```python
   def f():
       expected = """--self-test # 6 cases 
   """
       if expected.split("cases", 1)[1].startswith(" "):
           return 1
       return 0
   ```
   Replace `"6 cases \n"` with `"9 cases\n"`: the count rises **and the trailing space disappears**.

   Observed: original `f()` returns **1**, changed `f()` returns **0**, yet `failure_path_flags()` and `hold_reasons()` both return **empty lists**, without any review. This exceeds the authorized pure-count exemption. Preserve trailing whitespace for this comparison. Sibling probes with changed suffix text and two count expressions correctly remain flagged.

Other adversarial checks: duplicate occurrences produced distinct IDs; findings beat affirmative answers within and across records; `gate_ran=false`, a null overlay, ordinary post-review edits, and an injected verdict-read exception did not clear the HOLD.

Mutation verification: **all 22 new mutations**—15 merge-ready, 5 Codex, 2 recorder—and **both re-anchored mutations** matched exactly once and failed their exact named cases. All three isolated controls passed.

```text
check-merge-ready.py --self-test:    292/292 self-test cases passed
codex-review.py --self-test:         221/221 passed
record-review-verdict.py --self-test: 100/100 passed
```

LOOSENING-CHECK 6bd002a6d73a: finding: a real failure-path loosening now clears through an affirmative answer parsed from fenced example text, including without an actual reviewer judgment.
LOOSENING-CHECK e8b3c3bfbf22: finding: the replacement HOLD logic accepts answers from a different tree when an ignored submodule changes after review.
LOOSENING-CHECK f13e64d753fa: not a loosening

VERDICT: NOT CONVERGED
