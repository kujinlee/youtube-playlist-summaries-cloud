<!-- codex-review: model=gpt-6.1-sol -->

1. **High — HONEST-SYNTACTIC: indentation changes cancel a real failure-path removal.** [scripts/check-merge-ready.py:671](scripts/check-merge-ready.py#L671) treats stripped lines re-added anywhere in the file as moves. This discards Python’s meaningful indentation.

   Ordinary-work scenario: an author adds optional diagnostic logging and accidentally indents the refusal beneath `if verbose`:

   ```diff
        if bad:
   -        print("invalid input")
   -        return 1
   +        if verbose:
   +            print("invalid input")
   +            return 1
        return 0
   ```

   **Executed evidence:** committed both versions in a temporary git repository and ran production `gather → hold_reasons → final_verdict`. Result: `holds=[]`, verdict `(0, "READY")`. Executing `check(True)` returned **1 before, 0 after**. The removed `return 1` is visibly present in the hunk and matches `FAIL_PATH`; cancellation happens before detection. This requires neither dead code nor deliberate evasion, and falls outside the semantic stop rule.

2. **Medium — HONEST-SYNTACTIC: ordinary failure statements remain invisible to `FAIL_PATH`.** [scripts/check-merge-ready.py:505](scripts/check-merge-ready.py#L505) recognizes only single-digit positive status literals and omits ordinary exception statements.

   Ordinary-work scenarios: a gate uses conventional exit status `10` or `-1`, and an error-handling cleanup accidentally changes it to success; or an author converts a validation exception into a diagnostic and inadvertently lets execution continue.

   **Executed evidence:** separate real-git commits under `scripts/check-example.py`:
   
   - `sys.exit(10) → sys.exit(0)`
   - `sys.exit(-1) → sys.exit(0)`
   - `raise ValueError("invalid input") → print("invalid input")`

   Each produced `holds=[]`; driving `main()` with real git reads and passing stubs for external checks returned **rc 0 and printed READY**. The control, `sys.exit(3) → sys.exit(0)`, returned **rc 3, HOLD**. These remove or rewrite the failure statement itself—distance zero—not a remote condition or helper meaning.

Verification at `b1c980e59014cff2c67717820acff7508695b20d`:

- Requested self-test: **191/191 passed**.
- All **71 mutations** applied individually over a green control: **71/71 killed through named assertions**.
- Replayed the last **40 merged PRs**: **9 held**, 313 git calls, zero collection errors. Held PRs: **#398, #387, #386, #382, #381, #379, #367, #366, #360**.
- Repository working tree remains clean; no review file written.

VERDICT: NOT CONVERGED
