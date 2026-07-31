# Acceptance criteria — architecture review 2026-07-30

Companion to [`architecture-review-2026-07-30.md`](architecture-review-2026-07-30.md).
That document says what is wrong. This one says **what "fixed" means**, in terms that can be
checked rather than argued.

Run the mechanical half at any time:

```bash
python3 scripts/check-arch-findings.py             # report; exit 1 only if something REGRESSED
python3 scripts/check-arch-findings.py --evidence  # show the matched files/lines
python3 scripts/check-arch-findings.py --strict    # exit 1 unless every criterion PASSes
```

---

## The rule these criteria are written against

**Every criterion measures adoption, never existence.**

This is not a stylistic preference. Finding #2 *is* the case where the fix was built and
changed nothing: `writeArtifact` implements the commit→promote protocol correctly and has zero
production callers. A criterion like "a shared artifact writer exists" would have been **green
before the review was even written**, while all five writers still hand-rolled the protocol.

So each finding carries three parts:

| Part | Who checks it | Why it's separate |
|---|---|---|
| **Invariant** | — | The one-sentence property. Everything else derives from it. |
| **Mechanical criteria** | `check-arch-findings.py` | Countable. Ratchets, so the number can't quietly grow. |
| **Judgment criteria** | reviewer at PR time | Real but uncountable — a script can't tell a good seam from a bad one. |
| **How the fix can be faked** | reviewer at PR time | The specific green-but-not-fixed state to look for. |

### Ratchet semantics

Each mechanical metric records a **baseline** (measured 2026-07-30) and a **target**.

- `current == target` → **PASS**
- `target < current <= baseline` → **OPEN** — not fixed, not worse
- `current` worse than baseline → **REGRESSED** → non-zero exit

The regression arm is why this belongs in CI. Finding #1 is "12 files fork on
`STORAGE_BACKEND`". Nothing today stops that becoming 15 — no test fails, no type breaks. The
ratchet is the only thing that would notice.

### A note on baselines

Two baselines here differ from the review's prose, and both were widened rather than narrowed
after measurement:

- **#1a is 12, not 11.** The review counted *route* files; `app/page.tsx` forks on
  `STORAGE_BACKEND` too. A criterion that excluded a genuine fork site could reach PASS with
  the bug intact.
- **#2c's probe** keys on each writer's distinct failure message, including
  `"staged MD verify failed"` in `sync-run.ts` — the first version of the probe guessed a
  different identifier and undercounted the strategies 3 → 2.

Both were found by running the script and disbelieving the output. That is the intended way to
use it.

---

## #1 — The Storage Seam doesn't hold

> 12 files re-read `STORAGE_BACKEND` and fork into `serveLocal`/`serveCloud`. Adding a field to
> a response means editing two paths and remembering the second exists — nothing fails if you
> forget. `UUID_RE` copy-pasted into 11 files; a 7-step cloud preamble repeated in 5 routes.

**Invariant:** a route handler cannot observe which storage backend is in use.

| id | Measure | Baseline → Target |
|---|---|---|
| 1a | files under `app/` reading `STORAGE_BACKEND` | 12 → **0** |
| 1b | `const UUID_RE` definitions | 11 → **1** |
| 1c | files forking on `serveLocal`/`serveCloud` | 8 → **0** |

**Judgment criteria**
- Adding a field to a response is a **one-file** edit. Demonstrate it on a real field in the PR
  description — not hypothetically.
- The 7-step cloud preamble is called, not restated, and its steps are ordered inside the shared
  module rather than by convention at each call site.
- The resolver returning the backend-specific implementation is itself tested through its
  interface, using `InMemoryBlobStore` where a blob store is needed (finding #3's payoff).

**How the fix can be faked**
- A `getBackend()` helper that routes still branch on — `STORAGE_BACKEND` disappears from the
  grep while the two code paths survive. Metric 1c is the guard; it must reach 0 *with* 1a.
- Exporting `UUID_RE` from one module but leaving the 11 copies in place. 1b counts definitions,
  not imports, precisely for this.

---

## #2 — The commit→promote protocol has no owner

> `writeArtifact` implements it and has zero callers; 5 writers hand-roll it with 3 different
> verification strategies. One discovered the adapters disagree about `promote()` and fixed it
> locally, in a comment — the other four still assume uniformity.

**Invariant:** exactly one module performs stage → verify → commit → promote → mark, and no
production code outside `lib/storage/` calls `promote()` directly.

| id | Measure | Baseline → Target |
|---|---|---|
| 2a | `.promote()` call sites outside `lib/storage/` | 3 → **0** |
| 2b | production callers of `writeArtifact` | 0 → **≥3** |
| 2c | distinct staged-write verification strategies | 3 → **1** |

**Judgment criteria**
- The adapters' `promote()` semantics are **reconciled at the seam**, not per caller. Either
  both adapters overwrite, or the interface documents create-if-absent as the contract and every
  caller is audited against it. A third local workaround is a failed fix.
- `BlobStore`'s interface states which of overwrite / create-if-absent is normative. The current
  divergence is undocumented in the interface — that is the actual defect.
- `tests/lib/dig/write-dig-section-blob-promote.test.ts` (currently RED **on purpose** on branch
  `test/promote-divergence-finding-2`) goes **green** under both promote semantics.
- **W1 (summary) is traced but unproven** — see the review's scope note. Before this finding is
  closed, the W1 equivalent of that test must exist and pass: a `CURRENT_DOC_VERSION` bump must
  not leave the cloud DB asserting a version its blob does not contain.
- The 8 tests currently guarding `writeArtifact` are guarding **production** afterwards.

**How the fix can be faked**
- Routing one writer through `writeArtifact` and declaring victory. 2a must reach 0 — *all*
  call sites, or the finding's own thesis ("a fix at one call site leaves everyone else holding
  the bug") repeats verbatim.
- Making `promote()` uniform without documenting it in the interface: the next adapter
  reintroduces the divergence with nothing to check it against.

---

## #3 — The seam is not the test surface ✅ DONE

Shipped in PR #38: `lib/storage/testing/in-memory-blob-store.ts` + 23 tests.

| id | Measure | Baseline → Target | Status |
|---|---|---|---|
| 3a | adapter present | 1 → **1** | **PASS** |
| 3b | test file present | 1 → **1** | **PASS** |

These are **regression guards**, not open work. Their value was demonstrated within hours: the
adapter is what made finding #2's divergence provable in a five-minute unit test rather than a
deploy.

---

## #4 — The release rule lives in five places

> The refund rule is character-identical in `worker-runner.ts` and `serve-doc.ts`, plus 3
> non-identical plpgsql predicates. `JobQueue.fail` takes 3 booleans whose invalid combinations
> the database has to defend against — the type permits nonsense.

**Invariant:** one named predicate decides whether a reservation is released, and the type
system makes an invalid failure-report unrepresentable.

| id | Measure | Baseline → Target |
|---|---|---|
| 4a | sites computing the release predicate inline | 2 → **0** |
| 4b | boolean flags on the failure-report type | 3 → **0** |

**Judgment criteria** — this is a **money path**, so judgment carries more weight here than
anywhere else in this document.
- The 3 plpgsql predicates agree with the TypeScript predicate, and the agreement is asserted by
  a test, not by reading. They cannot be collapsed into one language, so the coupling must be
  *checked* instead.
- The replacement for the 3 booleans is a discriminated union whose variants are the states that
  can actually occur (e.g. `{kind:'metered'} | {kind:'not-metered-preflight'} | {kind:'cancelled'}`).
  Per `docs/dev-process.md`, the new member is **required, not optional** — an optional one does
  not propagate and callers silently inherit the ambiguous original.
- **Mutation-check every guard** the fix adds: delete it, watch the covering test go red,
  restore. `docs/dev-process.md` requires this, and this finding is exactly where a test that
  passes in both the buggy and fixed world would be most expensive.
- No behavioural change to release decisions. The refactor must be provably neutral — the money
  tests (32/32) stay green with no expectation edits. **An edited money-test expectation is a
  behaviour change wearing a refactor's clothes.**

**How the fix can be faked**
- Extracting a `shouldRelease()` that both sites call, while the plpgsql predicates keep their
  own copies of the rule. 4a goes to 0 and the real five-way split is untouched.
- Replacing 3 booleans with one string field. The type still permits nonsense; a union of string
  literals is not a discriminated union of *states*.

---

## #5 — Two renderers restate one document

> ~35–40% of `render.ts` restated in `render-dig-deeper.ts`. `esc()` is character-identical and
> neither copy is exported, so neither can be unit-tested — that's the HTML escaper. `theme.ts`
> was split in half purely to keep a golden snapshot byte-identical.

**Invariant:** the HTML escaper exists once, is exported, and is unit-tested.

| id | Measure | Baseline → Target |
|---|---|---|
| 5a | `function esc(` definitions in `lib/html-doc` | 2 → **1** |
| 5b | `esc` is exported | 0 → **1** |
| 5c | dedicated escaper test file | 0 → **1** |

**Judgment criteria**
- `esc()` is a **security** function, so its test covers the injection cases, not just the happy
  path: `<script>`, attribute-context `"`, `&` double-escaping, and — a real gap in the current
  implementation — the fact that it does **not** escape `'`. Either escape it or state in the
  interface that the output is not safe in single-quoted attribute context.
- `theme.ts` is whole again, or an ADR records why the split must persist. "A golden snapshot
  requires it" is a *reason to fix the snapshot*, not a reason to split a module.
- Golden snapshots regenerated deliberately, with the diff reviewed line by line. A byte-identical
  snapshot after a real refactor is evidence the refactor didn't reach the shipped output.

**How the fix can be faked**
- Exporting `esc` from one renderer and importing it into the other, leaving the second
  definition in place as dead code. 5a counts definitions.
- A test that only asserts `esc('<') === '&lt;'`. That passes against a half-broken escaper.

---

## #6 — The shipped nav engine has no unit coverage

> 315 of `nav.ts`'s 607 lines are ES5 inside a template literal, with two self-written DRIFT
> WARNINGs. The TypeScript mirrors are tested; the string version is what ships. Real
> verification is 4,371 lines of Playwright.

**Invariant:** the JavaScript that ships to the browser is the JavaScript under unit test.

| id | Measure | Baseline → Target |
|---|---|---|
| 6a | self-written DRIFT WARNINGs in `nav.ts` | 2 → **0** |
| 6b | unit test executing the **shipped** string | 0 → **≥1** |

**Judgment criteria**
- The DRIFT WARNINGs are removed because drift became **impossible**, not because someone
  deleted the comments. The author of those warnings knew the risk and had no mechanism — that
  is the finding.
- Either the shipped string is generated from the tested TypeScript, or the test executes the
  shipped string directly (jsdom / `new Function`). A mirror tested alongside a mirror is the
  status quo with more files.
- Playwright coverage stays as-is. This adds a fast layer; it does not license deleting the slow
  one.

**How the fix can be faked**
- Testing a TypeScript module that *resembles* the shipped string. That is precisely today's
  arrangement, and the DRIFT WARNINGs exist because the author knew it.
- Deleting the warnings as "stale comments" during an unrelated cleanup. 6a would read PASS
  while the risk is untouched — **the one metric here most likely to go green dishonestly.**

---

## #7 — The local app has no seam and no test

> `CloudApp` (339 lines): 0 direct `fetch()`, 2 test files. `LocalApp` (690 lines): 10 raw
> `fetch()`, a raw `EventSource`, 0 tests. Untested because it has no seam.

**Invariant:** `LocalApp` reaches the network only through an injectable seam, and is tested
through it — the same way `CloudApp` already is.

| id | Measure | Baseline → Target |
|---|---|---|
| 7a | raw `fetch()` in `LocalApp.tsx` | 10 → **0** |
| 7b | raw `EventSource` in `LocalApp.tsx` | 2 → **0** |
| 7c | dedicated `LocalApp` test files | 0 → **≥2** |

**Judgment criteria**
- The seam is the **same shape** `CloudApp` uses. Two different client abstractions for two apps
  against one API is finding #1 recurring at the component layer.
- Tests cover the **SSE state machine** — progress events, completion, error, and disconnect —
  not just initial render. The `EventSource` is the hard part and the reason the seam is needed.
- `LocalApp` is 690 lines against `CloudApp`'s 339 for a comparable job. If the seam doesn't
  shrink it materially, ask what the extra 350 lines are doing before declaring this done.

**How the fix can be faked**
- Wrapping `fetch` in a module-level function inside the same file. The grep goes to 0; nothing
  is injectable; 7c stays 0 and is the real criterion.
- Two shallow render tests to satisfy 7c. The judgment criterion above is what makes 7c mean
  something.

---

## Closing a finding

A finding is closed when **all three** hold:

1. Its mechanical criteria read PASS in `check-arch-findings.py`.
2. Its judgment criteria are confirmed in the PR description, each with a pointer to the code or
   test that satisfies it — not a claim that it was done.
3. Its "how the fix can be faked" list was checked explicitly and none applies.

Then tick it here **and** in `docs/roadmap-to-launch.md` in the same commit — the coherence rule
in `docs/dev-process.md`. A finding marked done in one place and open in the other is exactly
the drift that made the roadmap contradict itself on 2026-07-30.
