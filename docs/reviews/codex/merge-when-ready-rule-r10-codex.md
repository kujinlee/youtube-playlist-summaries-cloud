<!-- codex-review: model=gpt-6.1-sol -->

1. **Medium — HONEST-SYNTACTIC: string-valued `sys.exit()` failure statements are invisible.** `scripts/check-merge-ready.py:506–507` recognizes only integer arguments to `sys.exit()`.

   **Ordinary-work scenario:** during diagnostic cleanup, an author changes `sys.exit("invalid input")` to `print("invalid input")`, accidentally allowing validation to succeed.

   **Executed evidence:** committed this change in a temporary git repository under `scripts/check-example.py`:

   ```diff
    import sys
    if True:
   -    sys.exit("invalid input")
   +    print("invalid input")
   ```

   Executing the gate returned **1 before, 0 after**. Production `gather()` collected the exact removal, but `hold_reasons()` returned **`[]`**. Driving `main()` with real git reads and passing external-check stubs returned **rc 0 and printed READY**.

   This rewrites the failure statement itself, at distance zero. It requires no crafted filename, configuration, evasion, or semantic inference, so the precommitted stop rule does not exclude it.

Verification at HEAD `e83086d7`:

- Requested self-test: **196/196 passed**.
- All **73 mutations** executed individually over a green control: **72 killed through every exact named assertion**; mutation **54** aborted with `IndexError`.
- Replayed 10 entries distributed across the last 40 merged changes against their parents: **3 HOLD, 7 READY**, zero collection errors. HOLD: `cd7134f8`, `11c1d5db`, `7f7a1577`. READY: `1e5bee1f`, `a50ddc36`, `c7c6672f`, `fa202473`, `d17beb92`, `446025ab`, `f017577d`.
- No repository files changed; no review file written.

VERDICT: NOT CONVERGED
