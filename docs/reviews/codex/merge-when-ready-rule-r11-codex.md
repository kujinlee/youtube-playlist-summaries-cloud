<!-- codex-review: model=gpt-6.1-sol -->

1. **High — HONEST-SYNTACTIC: TypeScript gates are excluded, allowing an ordinary weakening to report READY.** [scripts/check-merge-ready.py:511](scripts/check-merge-ready.py#L511) limits top-level gate code to `.py` and `.sh`. The failure matcher at line 507 also omits `process.exit(...)`.

   This excludes the existing `scripts/check-service-confinement.ts`, which CI invokes through `npm run check:confinement`.

   **Executed evidence:** copied the actual confinement gate into a temporary git repository containing an unauthorized service import, then committed:

   ```diff
   -    process.exit(1);
   +    process.exit(0);
   ```

   Running the actual gate through `ts-node` changed its exit **1 → 0**, while it continued reporting the unauthorized import. Production `gather()` collected the exact removal, but `hold_reasons()` returned **`[]`**. Driving `main()` with **real git reads and passing external-check stubs** returned **0** and printed **READY**.

   This rewrites the failure statement itself; it requires no crafted paths, evasion, or semantic inference. The entire existing TypeScript gate class lacks this protection.

   **Disposition: backlog, no fold**, under the precommitted round-11 DEFER decision. No file written.

Verification at HEAD `444c7586`:

- Requested self-test: **199/199 passed**.
- Mutations: **75/75 killed through every named assertion**, individually over a green control; no crashes.
- Last 40 merged changes replayed: **10 HOLD / 30 READY**, **313 git calls**, zero collection errors. Held: #398, #387, #386, #384, #382, #381, `11c1d5db`, #367, #366, #360.
- `main()` controls with real git reads confirmed **0 READY, 1 NOT READY, 2 CANNOT RUN, 3 HOLD**. The CANNOT RUN control used an actual failed git command.
- No round-10-induced defect found. Repository unchanged.

VERDICT: NOT CONVERGED
