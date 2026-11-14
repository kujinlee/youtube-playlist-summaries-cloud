---
name: true-about-the-name-silent-about-the-layer
description: "FIRES-WHEN: about to assert a negative about code or tooling ('X does not happen', 'nothing reads Y', 'that command doesn't exist') — a claim correct about the object it NAMES can be silent about the layer that overrides it; citation-checking cannot catch it, only 'what else touches this?' can"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: dca6fb13-6aee-4a29-9254-0fa87e826497
  modified: 2026-09-07T03:53:51.199Z
---

⛔ **A negative claim needs a SEARCH, not a read.** Before asserting "X does not happen", "nothing reads Y", "only Z
touches this", or "the tool has no X", ask **"what else touches this?"** — triggers, wrappers, subscribers, a predicate
that ignores a field, a test that covers the neighbour, a dependency outside the file. Grep the *table*, not the
function; the *field*, not the predicate. **Open every file before writing a line about it.**

**For tooling:** before saying a slash command, flag or feature doesn't exist, name the three layers and which you
checked — project (`.claude/commands/`), plugin (the skills list), **built-in (the CLI binary — `claude --version`)**.
My training data is guaranteed stale on a continuously shipping product; when the user asserts a version-gated fact
about their own tooling, check the version rather than memory.

**Why:** measured as the dominant defect mode at three+ layers — a trigger *under* a function, a hash *beside* a
predicate, a dependency *outside* a test, a built-in *outside* the enumerated directories. Two reviewers share a blind
spot when they share a *question*: Codex independently "verified" the first one by stopping at the same function.

**How to apply:** treat "I recognise this name from an import" as the signal to open the file — the risk factor is
**familiarity, not haste** (the least-verified task was the one whose file had been read most recently). Each finding
got *smaller* once measured ("accept, it is unavoidable"; "derive it, write nothing"; "delete a write nobody asked
for") — see [[check-the-assumption-not-just-the-code]].

Distinct from [[quote-the-code-dont-characterise-it]] (paraphrasing instead of pasting) and from
[[a-mechanism-can-be-silently-overridden]] (the same disease in a *guard*). Related: [[a-convention-catches-what-you-read]],
[[a-measurement-is-only-as-good-as-its-corpus]], [[measure-the-population-the-code-actually-sees]].

## History
**Spec layer — four instances, backlog #23 slice A (2026-08-23/24).** Every serious defect in five rounds had this
shape; none was a wrong line number (a reviewer verified ~40 citations correct in the pass that found two Blockings).

| The claim | True about | Silent about |
|---|---|---|
| "`update_video_annotations` doesn't bump `updated_at`" | the function (`0021:19-56`) | the trigger under it (`0015_video_updated_at_trigger.sql:13-14`) |
| "there is no content hash" | `isFresh` (`read-model.ts:20-25`) | the envelope's `sourceMdHash` (`model-store.ts:23`) |
| "18 tests cover this path" | the `extractQuickView` call | the file write — `mockWriteFile` never in an `expect`; 2,722 tests pass without it |
| "`companion.ts:43` shows ignoring the hash is deliberate" | that a line exists | that it complains about the behaviour |

**Plan layer — 4–0 (2026-08-24).** After a dual gate returned 2 Blocking + 5 High per half, one rule (open every file)
found four more neither half caught, two fatal on first run: `@testing-library/user-event` not a dependency (0 hits in
`package.json` and lockfile); fixtures with `bullets: []` against a `.min(3)` schema (`html-doc/types.ts:42`,
`model-store.ts:35`); a fixture unlike what `ingestion/summary-core.ts:101-116` emits; a mock gone dead.

**Harness layer — 2026-09-06.** Told the user `/goal` isn't a command after checking `.claude/commands/` and the skills
list; it is a built-in (shipped around Claude Code v2.1.139; `claude --version` reported 2.1.221). The enumeration was
exhaustive — of the wrong population — and the error discouraged the user from a tool they already had.
