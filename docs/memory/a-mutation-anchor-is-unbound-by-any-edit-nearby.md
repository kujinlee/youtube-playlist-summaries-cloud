---
name: a-mutation-anchor-is-unbound-by-any-edit-nearby
description: "FIRES-WHEN: editing a file mutation anchors bind to — a rename, a comment, a merge resolution — ⭐⭐ SEVEN anchors orphaned in ONE session by ordinary edits — a comment insertion, a case rename, a merge resolution. One was a BLOCKING red CI step. The 15-second check is the harness's OWN rule, and re-typing a broader one reproduced bugs already on record"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e8d4fa1c-667d-4d08-bd64-55931cd5a12f
  modified: 2026-09-23T00:31:37.819Z
---

2026-09-22, across PRs #332 and #333. **Seven manifest bindings were orphaned by edits that had
nothing to do with mutation testing**, and each cost a different amount depending on how it was
found:

| What broke it | Found by | Cost |
|---|---|---|
| a comment INSERTED into a two-line anchor | a 35-minute sweep, `NOT MEASURED — treat as NOT CHECKED` | 35 min |
| a case RENAME (an `expect` naming a case that no longer existed) | the same sweep | 35 min |
| a comment REWRITE, anchor spanned 3 comment lines + a `return` | **a review round** — it was a **Blocking**, a red required CI step | a whole round |
| four more, from restructuring the code the anchors point at | the 15-second check | seconds |

**Why:** anchors bind by **TEXT**. Any edit that changes, splits or moves the anchored span unbinds
it, and *nothing says so* until something applies the manifest. A multi-line anchor that includes
**comment lines** is the most fragile kind — comments are exactly what gets rewritten.

**How to apply:**
- ⭐ **Run the 15-second check before any sweep, over EVERY manifest.** The rule is the harness's
  own single line, `check-plan-code.py:1451` — exact equality against the case names that went
  **RED**, exactly one match required — plus `src.count(anchor) == 1`.
- ⛔ **Do not re-type a BROADER pre-check.** Mine reproduced two of the three bugs already recorded
  for an earlier ad-hoc copy: `expect` is sometimes a bare **string** (iterating it yields one
  "orphan" per character), and a duplicate-anchor rule **stricter than the harness's** invents
  failures. A checker re-typed per use degrades — see [[a-second-implementation-of-one-rule-drifts]].
- ⚠ **Derive the population.** My first corrected run covered **2 of 4** manifests, which is exactly
  how the Blocking got past me. Glob `scripts/mutations/*.json`; never pick.
- **Anchor on CODE, not comments.** When re-anchoring, prefer the statement plus the *next section's
  header* over the preceding comment block — the comment above a line is what people rewrite.
- **A merge resolution is an edit like any other** and orphans anchors the same way.

See [[a-mutation-loses-its-binding]] (the earlier, narrower instance),
[[a-measurement-is-only-as-good-as-its-corpus]], [[a-check-result-is-not-the-claim]].
