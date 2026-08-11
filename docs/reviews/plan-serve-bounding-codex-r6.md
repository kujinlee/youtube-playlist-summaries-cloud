<!-- codex-review: model=gpt-5.5 -->

**Fix Verification**

All four Round 5 fixes are present in the file:

- Google error import: line 898 has `import { GoogleGenerativeAIFetchError } from '@google/generative-ai';`.
- `ServeBudget` import: line 428 has `import type { ServeBudget } from '@/lib/serve-budget';`.
- stale `SERVE_CAPS` export claim fixed: line 793 says `SERVE_CAPS stays private`.
- file-structure row fixed: line 43 says `tests/integration/serve-doc-materialize.test.ts` is `mock factory only`, and `reserve-timeout and settle-retry tests live in the mapping file`.

**High**

- Task 6, Step 5: production snippet uses new symbols in `lib/html-doc/serve-doc.ts` without any import instruction. I checked current imports in `serve-doc.ts`: it imports `generateMagazineModel` and `writeModelEnvelope`, but not `generateMagazineModelForServe`, `writeModelEnvelopeWithin`, `callRpcBounded`, `SERVE_BUDGET`, or the `SERVE_*_TIMEOUT_MS` constants. The plan snippet uses all of those at lines 974-999 and 1010-1015. This repeats the missing-import class and would fail `tsc` if applied literally.

- Task 4, Step 1: test snippet uses `BlobStore['put']` and `writeModelEnvelopeWithin` without telling the implementer to update imports. I checked current `tests/lib/html-doc/model-store.test.ts`: line 5 imports `{ writeModelEnvelope, readModelEnvelope, type ModelEnvelope }`, and there is no `BlobStore` import. The plan snippet at lines 519-526 uses both missing symbols. Same compile-fail class.

- Task 6, Steps 1 and 3: duplicate import of `fakeRpcBuilder` into the same file. Step 1 adds `import { fakeRpcBuilder } from '../../support/fake-rpc';` at line 805; Step 3 says to add the same import again at line 895. I verified duplicate same-name imports produce `TS2300: Duplicate identifier`, so this is another literal-application compile failure.

**Medium / Low**

No non-blocking findings beyond the High issues above.

GATE NOT MET  
NOT CONVERGED
