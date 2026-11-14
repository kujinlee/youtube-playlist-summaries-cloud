---
name: a-mutation-loses-its-binding
description: "FIRES-WHEN: refactoring, deduplicating or deleting code that mutation entries anchor to or whose cases they name, or promoting a mutation from a scratch harness into a manifest. Anchors bind by TEXT; deletions orphan CASES too; promotion drops the harness's protection"
metadata:
  type: feedback
---

> Merged 2 memories. Former names (still referenced by other memories): `a-refactor-orphans-the-mutation-guarding-it`, `promoting-a-mutation-leaves-its-protection-behind`

**The rule: a mutation is coupled to code by LITERAL TEXT at one end and by a named CASE at the other. Any edit that moves either end is a two-file edit, and only the full `--mutate .` sees the break — `--self-test` stays green.**

**How to apply:**
- **Before editing guarded code,** grep `scripts/mutations/*.json` for the text you will change. After, re-point the entry so the SAME named case still goes red — preserve the INTENT, not the text. A repair that changes which case fires is a different mutation wearing the old name.
- **Don't anchor on a HOT LINE** (the expression every fix to that logic must touch) — it is guaranteed to orphan next round. Prefer a constant, message string or signature.
- **Before ANY deletion, ask both sides:** does it delete an anchor a surviving mutation needs? Does it delete the only CASE that can go red for a surviving mutation? For the second, re-anchor onto a case that drives the surviving function DIRECTLY — never retire the mutation while its subject still ships. Coverage routed through a caller dies with that caller.
- **"Anchor not found" is FAILED, never skipped**; an `expect` naming a case that cannot go red is rejected too.
- **Promoting a check from a scratch harness: ask what the HARNESS provided** (fake `HOME`, temp cwd, scratch clone, stubbed credential) — it does not travel with the diff. And prefer the WEAKEST mutation that still fails via its named case.
- **Control the instrument:** to prove a safety property over a manifest, also restore the dangerous form and confirm the instrument reports a breach.

**Why:** improving code (dedup, rename, retune a constant, delete a caller) is exactly what breaks the textual coupling, and nothing local looks wrong — the code is better, the manifest count is unchanged, the suite is green.

## History (condensed)

- **2026-09-01, twice:** PR #197 retuned a colour token a `page_chrome.json` anchor quoted → red on master `86ecade5`, repaired by PR #198. `fix-no-entry-emphasis` collapsed two `startswith(NO_ENTRY)` copies into `_declaration_reason()` and orphaned two mutations; suite **104/104** green throughout, harness refused with *"anchor NOT FOUND — it was not applied, so its 'caught' verdict would be meaningless"*.
- **2026-09-08, backlog #91, a hot line orphaned twice one commit apart** (r1 H2, r2 H3 both rewrote `check()`'s honest-zero branch). `--self-test` green both times (201/201, 207/207); only `--mutate .` saw `358 of 359 … NOT MEASURED`, rc=1 — the cardinality clause refusing a tally.
- **2026-09-09, `retire-plan-mode` PR 2 (#271), the inverse:** deleting plan mode's cases left **3 survivors + 2 `expect` fields matching 0 red cases** over a **74/74** green suite; anchors all resolved, but those five mutations' only red cases were plan-mode cases reaching `run_mutations`/`run_suite` end-to-end. Retiring them "for consistency" with the 20 legitimately retired would have shrunk real coverage.
- **PR #178, promotion:** a hand-battery mutation "call `_self_test` WITHOUT the sandbox", run under `env HOME=<tmp>` on purpose, was lifted into `gen-dashboard.json` where CI runs it with the real `HOME`; `OUT_DEFAULT` is absolute under `~/explainers/`. Reproduced by round 2's Claude half: entry 39 + an `--out`-defaulting case → `SENTINEL INTACT=False`. The falsifier, written after: every entry under a fake HOME with a sentinel — **47/47 clean, control = 1 breach**.

Related: [[a-mutation-anchor-is-unbound-by-any-edit-nearby]] (the later, broader instance), [[what-mutation-testing-proves]], [[assert-the-property-not-the-mechanism]], [[a-report-format-is-a-contract]], [[measure-the-population-the-code-actually-sees]], [[a-test-that-cannot-fail]], [[after-fixing-search-for-the-class]], [[an-instrument-that-edits-the-repo-corrupts-its-peers]], [[a-convention-catches-what-you-read]].
