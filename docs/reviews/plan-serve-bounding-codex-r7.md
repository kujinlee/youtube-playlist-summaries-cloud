<!-- codex-review: model=gpt-5.5 -->

**Fix Verification**

Round 6’s three fixes are present:

- Task 6 Step 5 import block is explicit:
  > `import { generateMagazineModelForServe } from '@/lib/gemini';`  
  > `import { writeModelEnvelopeWithin } from './model-store';`  
  > `import { callRpcBounded } from '@/lib/serve-rpc';`  
  > `SERVE_BUDGET, SERVE_RESERVE_RPC_TIMEOUT_MS, SERVE_PUT_TIMEOUT_MS, SERVE_SETTLE_RPC_TIMEOUT_MS`

- Task 4 Step 1 import instruction is explicit:
  > `import { writeModelEnvelopeWithin } from '@/lib/html-doc/model-store';`  
  > `import type { BlobStore } from '@/lib/storage/blob-store';`

- Task 6 Step 3 avoids duplicate `fakeRpcBuilder`:
  > `` `fakeRpcBuilder` is already imported by Step 1 — do NOT import it twice (TS2300). ``

**Structural Change Judgment**

Acceptable for normal TypeScript-visible imports. In this repo, `tsconfig.json` includes `**/*.ts`, and `@/*` is mapped in both Jest configs, so missing value/type imports in source, unit tests, and integration tests should be caught by `npx tsc --noEmit`.

But it does not cover runtime/test-runner configuration. Concrete place in this plan: integration tests run with plain `npx jest tests/integration/...`, which selects zero tests under the default `jest.config.ts`. `tsc --noEmit` cannot catch “test file not selected by Jest”.

Other classes `tsc` would not fully own: Jest mock factory hoisting/runtime closure errors, dynamic `require()`/string module names, SQL migration literals, and runner-specific config mismatches. I did not find a current path-alias mismatch; both Jest configs map `^@/(.*)$`.

**High**

- Task 6 Steps 2/4/6 and Task 7 Steps 2/4: integration test commands cannot execute the intended tests.  
  Concrete failure: the plan says:
  > `npx jest tests/integration/serve-doc-materialize -v`  
  > `npx jest tests/integration/serve-doc-materialize serve-doc-mapping -v`  
  > `npx jest tests/integration/serve-config-invariant -v`

  I checked `jest.config.ts`: `testMatch` includes `tests/lib`, `tests/api`, `tests/scripts`, smoke, and components, but not `tests/integration`. I also ran:
  > `npx jest tests/integration/serve-doc-materialize --listTests`

  It returned no test files. The correct runner does select it:
  > `npm run test:integration -- --listTests tests/integration/serve-doc-materialize`

  This means the money pin and CHECK-floor tests can appear “run” in task steps while actually not running. That is a test-that-cannot-fail defect in a money-path plan.

**Blocking**

None found.

**Medium / Low**

No additional Medium/Low findings recorded.

GATE NOT MET  
NOT CONVERGED
