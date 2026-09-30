---
name: true-about-the-name-silent-about-the-layer
description: "FIRES-WHEN: about to claim something about a named object — The dominant defect shape in the #23 spec — a claim correct about the object it names and silent about the layer that overrides it. Citation-checking cannot catch it; only \\\"what else touches this?\\\" can."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: dca6fb13-6aee-4a29-9254-0fa87e826497
  modified: 2026-09-07T03:53:51.199Z
---

⭐ **MEASURED FOUR TIMES IN ONE SPEC (2026-08-23/24, backlog #23 slice A).** Every serious defect in
five review rounds had the same shape, and **none was a wrong line number** — a reviewer verified all
~40 citations as correct in the same pass that found two Blockings.

| The claim | True about | Silent about |
|---|---|---|
| "`update_video_annotations` doesn't bump `updated_at`" | the **function** (`0021:19-56`) | the **trigger** under it (`0015_video_updated_at_trigger.sql:13-14`) — fires on EVERY row update |
| "there is no content hash" | **`isFresh`** (`read-model.ts:20-25`) | the **envelope**, which has carried `sourceMdHash` since Stage 3 (`model-store.ts:23`) |
| "18 tests cover this path" | the **`extractQuickView` call** | the **file write** — `mockWriteFile` never appears in an `expect`; 2,722 tests pass without it |
| "`companion.ts:43` shows ignoring the hash is deliberate" | that a line **exists** there | that it **complains** about the behaviour rather than defending it |

**Why:** Codex independently "verified" the first one — it read the same function and stopped in the
same place. Two reviewers can share a blind spot when they share a *question*.

**How to apply:** before asserting a negative about code ("X does not happen", "nothing reads Y",
"only Z touches this"), ask **"what else touches this?"** — triggers, wrappers, subscribers, a
predicate that ignores a field, a test that covers the neighbour. Grep the *table*, not the function;
the *field*, not the predicate. A negative claim needs a search, not a read.

Distinct from [[quote-the-code-dont-characterise-it]] (which is about paraphrasing instead of pasting)
and from [[a-mechanism-can-be-silently-overridden]] (which is the same disease in a *guard*, one layer
down). Related: [[a-convention-catches-what-you-read]] — a script catches what is THERE.

**The fix pattern that kept recurring:** each of these got *smaller* once measured. The `updated_at`
answer was "accept, it is unavoidable"; the magazine answer was "derive it, write nothing"; the
6¢-per-press answer was "delete a write nobody asked for". See
[[check-the-assumption-not-just-the-code]].

## ⭐ MEASURED 4–0 AT THE PLAN LAYER TOO (2026-08-24)

After a dual adversarial gate on the slice A plan returned 2 Blocking + 5 High from each half, a
mechanical pass with one rule — **open every file before writing a line about it** — found **four
more defects neither half caught**, two of them fatal on first run, *in tasks both halves had just
reviewed closely*:

| Defect | The file you had to open |
|---|---|
| `@testing-library/user-event` imported but **not a dependency** (0 hits in `package.json` *and* the lockfile) | `package.json` — not the test |
| Fixtures used `bullets: []`, which **throws**: schema is `.min(3)` and the writer parses before writing | `html-doc/types.ts:42` **and** `model-store.ts:35` |
| A fixture that is not the document the pipeline emits — tests would pass against a shape that never exists | `ingestion/summary-core.ts:101-116` |
| A mock gone dead after an earlier edit | the task's own diff |

**The common property is the whole lesson: none is visible in the artifact under review. Each needs a
DIFFERENT file than the one the claim is about.** Prose review of a claim about code cannot find what
only the code says — no matter how adversarial the reviewer or how many of them there are.

Now measured at **three layers** (a trigger *under* a function, a hash *beside* a predicate, a
dependency *outside* a test), which makes it the dominant defect mode rather than bad luck.

**Corollary, also measured:** the risk factor is **familiarity, not haste**. The least-verified task
was the one whose file had been read most recently for other work — that familiarity is exactly what
stops the re-check. Treat "I recognise this name from an import" as the signal to open the file, not
to proceed.

## ⭐ FIFTH INSTANCE, and the layer was the HARNESS itself (2026-09-06)

The user said *"set them as goal"*. I checked `.claude/commands/` (two files) and the available-skills
list, found no `goal`, and **told them `/goal` isn't a command in this repo.** The user corrected me:
`/goal` is a **first-party built-in slash command**, shipped around Claude Code **v2.1.139**. Verified
immediately after — `claude --version` reports **2.1.221**.

| The claim | True about | Silent about |
|---|---|---|
| "`/goal` isn't a command here" | `.claude/commands/` and the plugin skill list | **built-in CLI commands**, which appear in neither — the system prompt even says so (`/help`, `/clear` … "aren't skills") |

**Two things make this worse than the earlier four, and they generalise:**

1. **The negative was about a moving target.** The knowledge cutoff (May 2026) is ~4 months behind the
   session date. Anything of the form *"Claude Code does not have X"* is a claim about a product that
   ships continuously, and my training data is **guaranteed stale** on it. `claude --version` is one
   cheap command and settles it.
2. **The enumeration felt exhaustive because it was exhaustive — of the wrong population.** Two
   directories and a list is a real search; it just wasn't the *set the claim was about*. Same shape as
   [[a-measurement-is-only-as-good-as-its-corpus]] and
   [[measure-the-population-the-code-actually-sees]], now at the tooling layer.

**How to apply:** before saying a slash command, flag, or feature **doesn't exist**, name the three
layers and say which you checked — project (`.claude/commands/`), plugin (the skills list), and
**built-in (the CLI binary/version)**. If the answer would change what the user does, run
`claude --version` first. And when the user asserts a version-gated fact about their own tooling,
**check the version rather than the memory** — they are reading release notes I cannot see.

⚠ The work was not wasted: the project's own three-layer roadmap/task tracking
(`docs/dev-process.md`) is mandated independently of what the harness offers, so both mechanisms are
wanted. But the assertion was still wrong, and it was wrong in the one direction that discourages a
user from using a tool they already have.
