---
name: hardcode-only-what-fails-loudly
description: "FIRES-WHEN: deciding what to hardcode versus derive in a check's configuration — Sort a check's configuration by what happens when it goes stale — hardcode only the parts that announce their own wrongness, derive the rest from the documents"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 44563227-eadb-43b6-9b7a-a92b0c8e93e9
  modified: 2026-08-12T15:16:17.855Z
---

When building a check, do not ask "is this configuration general?". Ask **"what happens when this
configuration goes stale?"** Sort every constant into two piles:

**Loud when wrong → safe to hardcode.** A file path or a heading string that stops matching raises
`cannot_run`, so being wrong announces itself.

**Silent when wrong → must be derived.** An identifier vocabulary (`[AB]\d`), an enumerated file
list. When a new item family appears, the reference matches nothing — so it is not flagged as
*unknown*, it is **invisible**. The check keeps reporting green while quietly ceasing to cover new
work. That is strictly worse than no check, because it also carries authority.

**Measured 2026-08-12** on `scripts/check-roadmap-consistency.py`. Written with `[AB]\d` hardcoded
and `m1.4-finishup-checklist.md` listed by name, it was correct for the week it was written. The user
asked *"if the configuration is not general, how is this useful for new PRs?"* — the honest answer was
that it wasn't. Both were changed to derive from the documents: item families come from the checkbox
lines, checklist files are globbed. A new family is now covered the moment it has checkboxes.

**How to apply:** for each constant in a check, write down the observation that would occur if it
went stale. If you cannot name one, that constant must be derived, not configured.

⭐ **Candidate for `docs/portable-practices.md`** — it is measured, and project-independent
([[project-has-two-deliverables]]).

Same family as [[a-test-that-cannot-fail]] and
[[test-harness-can-launder-failures]]: the recurring shape here is not a wrong answer, it is a check
that cannot see its subject and says nothing about that. See also
[[rls-denial-is-indistinguishable-from-absence]], where a backend's honest "I cannot tell" was read as
a fact.
