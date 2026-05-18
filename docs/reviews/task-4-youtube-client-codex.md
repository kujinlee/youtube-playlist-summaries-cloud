# Task 4 — YouTube Client: Codex Adversarial Review

**Verdict:** Review debt in error chaining, pagination runaway protection, and test coverage

---

## Findings

### Major

**1. `fetchTranscript` error wrapping drops original cause**
`{ cause: err }` not passed to `new Error(...)`. Full stack trace and error type are discarded — network failures, API failures, and parse errors all become indistinguishable. Fix: pass `{ cause: err }`.

**2. Test coverage gaps**
- Batching test checks call count but not which IDs go to which batch
- Missing: empty playlist, non-Error transcript rejection, runaway pagination

---

### Minor

**3. Pagination has no max-page circuit breaker**
An API returning the same `nextPageToken` forever loops indefinitely. Fix: add a page limit (e.g., 100 pages).

**4. `detectLanguage` missing compatibility jamo (ㅋㅋㅋ type characters)**
`/[가-힣ᄀ-ᇿ]/g` excludes U+3130–U+318F. Fix: add `㄰-㆏` back to the range.

**5. URL parsing doesn't validate hostname**
`https://example.com/?list=PLtest123` is accepted silently. Documented as an acceptable limitation — spec says "YouTube playlist URL" and hostname check would add complexity not required by the plan.

---

## Resolutions Applied

- `{ cause: err }` added to `fetchTranscript` error
- Pagination max-page circuit breaker (100 pages) added
- Batch test verifies exact IDs in each call
- Compatibility jamo re-added to `detectLanguage` regex
- Non-Error rejection test added to `fetchTranscript`
