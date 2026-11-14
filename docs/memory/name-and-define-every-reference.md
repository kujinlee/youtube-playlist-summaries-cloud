---
name: name-and-define-every-reference
description: "FIRES-WHEN: about to write a bare identifier — #39, M4, C5, §2 — or jargon — ⭐ Never a bare `#39` or `M4` — qualify the namespace (and do NOT try to script it); gloss jargon inline on first use"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0cfd7079-9c4f-4f89-9a59-337f426f6311
  modified: 2026-09-22T01:52:29.896Z
---

> Merged 2 memories. Former names (still referenced by other memories): `feedback-name-every-reference`, `feedback-define-terms`

## The rule (current)

1. **Never type `#` without the noun in front of it** — `backlog #154`, `PR #330`, `task #39`, `migration 0027`,
   `spine M4`, `roadmap M2`, `ADR-0010`, `round 4`. Qualify on **EVERY use in a report**, not just first use per
   message: a skimming reader lands mid-message, and each table row or bullet is its own entry point. Applies to
   messages, commit bodies, PR descriptions and review documents. Inside the document that owns the namespace
   (`docs/backlog.md` citing its own rows) a bare number is fine — do not retrofit the historical ones.
2. **No bare back-references as labels.** Give every item a self-describing name (`the summary-handler lost update`)
   and reuse the name, not "#1/#2" or `A3`/`WB-H1`-style codes — name what it IS on each use.
3. **Define new terms, acronyms and jargon inline, in plain language, on first use** — e.g. "RLS (row-level security —
   the DB rule that keeps one user's rows invisible to another)". Short, no lecture.
4. **Don't over-compress explanations.** For a race, a bug or an interaction: a concrete timeline with real values,
   who writes what, and what is actually lost. One worked example beats three abstract sentences.

**Why:** this project reuses small integers across independent namespaces. The cost is small and paid by the READER,
so no gate surfaces it. ⚠ **The trap is DENSITY:** when one namespace dominates a session, bare numbers feel
unambiguous to the writer — the denser the work, the more the qualifier is needed and the less it feels needed. The
user has twice said an explanation was too compressed to follow.

**How to apply:** ⛔ **do NOT try to make rule 1 a script.** Measured: 1,556 bare `#N` across `docs/`, and 24 on one
branch diff of which ~90% were titles/ordinals (`Phase 6 #1`, `Architecture Review #2`, `#54(a)`). The property is
semantic; a syntactic proxy gets notched one case at a time ([[a-convention-catches-what-you-read]]). Written in the
repo at `docs/process-checklists.md` → *"Qualify every number in prose"*. Related:
[[it-already-exists-under-a-name-i-didnt-search]] (same confusion at search time),
[[the-user-does-not-follow-in-real-time]], [[feedback-flag-transitional-choices]].

## History

- **2026-08-02:** bare back-references rule added (rule 2) — the user often returns to a thread days later.
- **2026-08-27, twice in one day:** searching `#26` in `docs/backlog.md` returned nothing (the table uses bare
  `| 26 |`), a wrong turn during M4 task 10; and four bare `#39`s in one message, inside an argument that bare numbers
  are ambiguous, while task #39 and backlog #39 were unrelated. The user had to ask *"backlog or task?"*.
- **2026-09-21:** after a day that filed six rows and merged two PRs: *"btw, qualify number such as PR xxx, backlog
  YYY"*. That session had backlog #154–#159, PRs #329/#330, merged PRs #137/#317/#327 and rounds r1–r4 live at once.
  Rule 1 widened from first-use to every use.
