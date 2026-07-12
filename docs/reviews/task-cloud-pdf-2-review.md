# Task 2 — `assertCloudSummaryMdKey` — dual review trail

**Files:** `lib/html-doc/assert-cloud-summary-md-key.ts` + test. Base 0f73afc → head bdedcb9.

## Claude code review (SDD task-reviewer, sonnet) — original impl f22ce18
**Spec ✅ / Task quality Approved.** Faithful verbatim copy of the brief's guard + test. Verified: non-string short-circuits first in the `||` chain (no stray TypeError); doc comment about `assertLogicalKey` permitting embedded slashes is true (`blob-store.ts:22` only rejects leading `/` + `..` segments); test try/catch is non-vacuous (catches both "didn't throw" and "wrong shape"). Minor (non-blocking): `FOO.MD` fail-closed over-reject; broad `..` substring match; no non-string test row. No Critical/Important.

## Codex adversarial review (gpt-5.5) — round 1
0 Blocking / 0 High. **Medium:** guard is a denylist → bypasses pass (`nested%2ffoo.md`, ` foo.md`, `foo\nbar.md`, `a／b.md`, `${'a'.repeat(10000)}.md`); suggested an ASCII allowlist. **Low:** tests don't lock those. Confirmed OK: throw carries `statusCode:409`; valid `0007_intro.md` accepted; no false-positive on the documented shape.

## Controller adjudication of the Medium
Codex's *instinct* (allowlist > denylist for a hard boundary) is right, but its *ASCII* pattern would 409 legitimate keys: this project supports Korean/CJK summaries and `lib/slugify.ts` keeps `\p{L}\p{N}`. Verified the real key shape = `${padSerial(serial)}_${slugify(title)}.md`, and slugify emits ONLY `\p{L}\p{N}` + `-` (replaces everything else — incl. slashes/whitespace/control/dots/`%`/homoglyphs — with `-`). So a **unicode-aware allowlist** `^[\p{L}\p{N}][\p{L}\p{N}_-]{0,127}\.md$/u` is **provably regression-free** (accepts every possible slugify output, Korean included) AND closes every bypass Codex named. Applied in `872f752`; test adds a Korean accept + all bypass rejects + non-string + (bdedcb9) U+2044/U+2215 homoglyphs + max-length accept.

## Codex re-review (round 2) — hardened guard 872f752 — **CONVERGED**
0 Blocking / High / Medium. Verified NO over-rejection (slugify output always matches; NFD combining marks are stripped by slugify not emitted; empty-slug `0007_.md` accepted; 60-char slug well under the 128 bound; cloud serials are SQL int) and NO remaining bypass (allowlist rejects `%2f`, whitespace, newline/tab, control chars, `\`, `..`, leading dot, over-long, non-string, U+FF0F/U+2044/U+2215). One Low (pin homoglyphs/max-length in tests) → addressed in bdedcb9.

**Final:** 27/27 guard tests; full suite 2013/2013 (at 872f752); tsc clean. Task quality Approved, both passes converged.
