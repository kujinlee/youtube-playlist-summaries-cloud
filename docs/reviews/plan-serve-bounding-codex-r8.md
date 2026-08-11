<!-- codex-review: model=gpt-5.5 -->

**Findings**

Medium - Task 6 Step 2: `Run: npx jest serve-doc-mapping serve-doc-materialize -v` still pretends to verify both files, but default `jest.config.ts` excludes `tests/integration`. I checked with `npx jest --listTests serve-doc-mapping serve-doc-materialize`; it selected only `tests/lib/html-doc/serve-doc-mapping.test.ts`. Concrete failure: a bad `serve-doc-materialize.test.ts` mock-factory edit would not be caught at this step. Not High because Task 6 Step 4 and Step 6 both later run `npm run test:integration -- serve-doc-materialize`, so the task cannot reach commit with that integration file unverified.

No Blocking or High findings.

**Round 6 Fix Verification**

Found the `serve-doc.ts` import block in Task 6 Step 5:

> `import { generateMagazineModelForServe } from '@/lib/gemini';`  
> `import { writeModelEnvelopeWithin } from './model-store';`  
> `import { callRpcBounded } from '@/lib/serve-rpc';`  
> `import { SERVE_BUDGET, SERVE_RESERVE_RPC_TIMEOUT_MS, SERVE_PUT_TIMEOUT_MS, SERVE_SETTLE_RPC_TIMEOUT_MS } from '@/lib/serve-budget';`

Found the `model-store.test.ts` import instruction in Task 4 Step 1:

> `import { writeModelEnvelopeWithin } from '@/lib/html-doc/model-store';`  
> `import type { BlobStore } from '@/lib/storage/blob-store';`

Found the duplicate `fakeRpcBuilder` fix in Task 6 Step 3:

> `` `fakeRpcBuilder` is already imported by Step 1 — do NOT import it twice (TS2300). ``

**Structural Change Judgment**

Acceptable. `npx tsc --noEmit` is the right owner for normal static import-list defects here, and `tsconfig.json` includes `**/*.ts` / `**/*.tsx`, so it covers the planned test files. I also ran `npx tsc --noEmit`; current repo is clean.

Limits checked: `tsc` would not catch an omitted export from a Jest mock factory, because TypeScript sees the real module, not the runtime mock object. It also cannot catch a test command selecting zero or partial tests. Path aliases are not a gap here: both Jest configs map `^@/(.*)$`, matching `tsconfig` paths.

**Command Audit**

Round 7 fixes are present where they matter: integration runs now use `npm run test:integration -- serve-doc-materialize` and `npm run test:integration -- serve-config-invariant`. I verified those patterns select the intended integration files.

`./scripts/check-schema-gates.sh` exists and is executable. `npx supabase` resolves in this repo; `npx supabase --version` returned `2.113.0`. Unit `npx jest <pattern>` commands select intended unit files under `jest.config.ts`; `model-store` also selects `tests/lib/model-store-cloud.test.ts`, but that is extra coverage, not a false green.

Mutation steps are covered by the suites they run: Task 3 wrapper mutation by `gemini-serve-budget`, Task 5 timeout race by `serve-rpc`, Task 6 retry/timeout branches by `serve-doc-mapping`, and Task 7 floor mutation by `serve-config-invariant`.

GATE MET  
CONVERGED
