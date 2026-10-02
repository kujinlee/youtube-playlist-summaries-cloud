---
name: a-mocked-boundary-tests-the-contract-you-imagined
description: "FIRES-WHEN: writing tests that mock a model, API or service boundary — 2,808 green tests + 5 review rounds shipped a feature that fails 6 times in 8 against the REAL model — every test mocks lib/gemini.ts and a fixture writer writes the bare document, so the suite asserted an imagined contract"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 92595a72-4e72-4cb8-9e2c-8cddc19a2bb3
  modified: 2026-08-24T22:38:17.763Z
---

**MEASURED 2026-08-24.** Backlog #23 slice A (corrections in the cloud) shipped to prod as release
v8 with 12 tasks, 4 gates green, 5 spec rounds, dual adversarial review, 25/25 mutations caught, and
2,808 unit tests passing. **The first live press returned HTTP 500.**

Sampling the real `gemini-2.5-flash` call 8 times on one real document, with prod's caps:

| Returned | Rolls | Verdict |
|---|---|---|
| `` ```\n---\ntags: `` | 5 | REJECTED `missing-frontmatter` |
| `` ```markdown\n---\n `` | 1 | REJECTED |
| `---\ntags:` | 2 | ACCEPTED |

The model wraps the document in a code fence ~3 times in 4 (the doc opens with `---`, which reads as
YAML). `assertStructurePreserved` then discards the whole paid correction. **The correction itself
was right in 8 rolls out of 8** — only the packaging was wrong. Fix: `unwrapFencedDocument` at the
transport seam (`lib/gemini.ts`), PR #138. Re-measured after: 0/6 rejected.

**Why:** every test mocks `lib/gemini.ts` at the boundary, and **a person writing a fixture writes
the bare document** — nobody invents a code fence they have never seen. So the suite asserted the
contract we *imagined* while production had the other one. No amount of additional mocked testing,
review rounds, or mutation testing could reach it: they all share the fixture's premise. This is the
same shape as [[true-about-the-name-silent-about-the-layer]] — correct about the object it names,
silent about the layer that actually decides — and of [[check-the-assumption-not-just-the-code]].

**How to apply:**
- **A mocked external boundary is an ASSUMPTION, not a test of it.** For any paid/external call, the
  first live run is a distinct gate — Phase 4 exists for exactly this and it is not optional
  ceremony. `docs/deploy.md` Step 3b cannot cover it: the prod smoke is read-only by construction,
  so it structurally cannot exercise a paid write.
- **Sample it, don't try it once.** The first local repro of this PASSED (the 2-in-8 case). One
  sample would have concluded "prod fluke". 8 rolls turned an anecdote into 6/8 and cost 8¢.
- **Put the real bytes in the fixture.** The regression tests use the actual leading bytes of the
  eight rolls, so the next person inherits the measurement rather than the assumption.
- Note which half held: the validator did its job and named the reason precisely enough to diagnose
  in one run. The defect was upstream of the guard that caught it — fix the producer, never loosen
  the guard ([[quote-the-code-dont-characterise-it]]).

**Residue found in the same run, NOT yet filed** (user owns filing, [[feedback-agree-before-filing]]):
a failed correction **pays and records nothing** (`record_correction_spend` is only reached on
success — prod `correction_spend` stayed empty after a real paid call), and the corrections text is
**stored before** the correction is applied, so the row can carry a correction the document lacks.
