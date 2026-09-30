---
name: name-and-define-every-reference
description: "FIRES-WHEN: about to write a bare identifier — #39, M4, C5, §2 — or jargon — ⭐ Never a bare `#39` or `M4` — qualify the namespace (and do NOT try to script it); gloss jargon inline on first use"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0cfd7079-9c4f-4f89-9a59-337f426f6311
  modified: 2026-09-22T01:52:29.896Z
---

> Merged 2 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `feedback-name-every-reference`, `feedback-define-terms`

## feedback name every reference

**A bare `#39` is not a reference.** Write `backlog #39` or `task #39`. Same for `PR #155`,
`migration 0027`, `spine M4`, `roadmap M2`, `ADR-0011`, `round 11`.

**Why:** this project reuses small integers across independent namespaces, and the reader cannot
resolve them. Measured on 2026-08-27, twice in one day:

- searching `#26` in `docs/backlog.md` returns **nothing** — that file uses bare `| 26 |` in a
  table — so the item had to be found by grepping the CONCEPT instead. A wrong turn during
  M4 task 10;
- four bare `#39`s in one message, inside an argument that bare numbers are ambiguous, while
  **task #39** and **backlog #39** are unrelated items. The user had to ask *"backlog or task?"*.

⚠ **The cost is small and paid by the READER**, which is why nothing surfaces it and why it has to
be a habit. It is not caught by any gate.

**How to apply:** qualify on first use in every message, commit body, PR description and review
document. Inside the document that owns the namespace (`docs/backlog.md` citing its own rows) a bare
number is fine — do not retrofit the 1,556 historical ones.

⛔ **Do NOT try to make this a script.** MEASURED at three scopes before writing it down: 1,556 bare
`#N` across `docs/`, and 24 on a single branch diff of which ~90% were `Phase 6 #1`,
`Architecture Review #2`, `#54(a)` — titles and ordinals, not references. Making it usable means
notching a syntactic proxy one case at a time, which is the sequence
[[a-convention-catches-what-you-read]] and `run-schema-assertions.sh` both record costing four
rounds. The property is semantic.

Written down in the repo at `docs/process-checklists.md` → *"Qualify every number in prose"*, with
a pointer row in `docs/dev-process.md`. Related: [[it-already-exists-under-a-name-i-didnt-search]] —
the same namespace confusion, one step earlier, at search time.

### ⟳ RECURRED 2026-09-21, across an entire session, and the failure mode is DENSITY

The user, after a day of work that filed six rows and merged two pull requests:

> *"btw, qualify number such as PR xxx, backlog YYY"*

**The rule was already here and I broke it continuously.** Not once — in nearly every message, and in
the pull-request bodies too. The reason is worth recording because it is not forgetfulness:

**When one namespace dominates a session, bare numbers start to feel unambiguous — to the writer.**
Everything I touched that day was a backlog row, so `#154`, `#155`, `#156` read as obviously backlog
rows *to me*. They are not obviously anything to a reader arriving cold, and this session had
`#154`–`#159` (backlog), `#329`/`#330` (pull requests), `#137`/`#317`/`#327` (merged pull requests
cited as history) and `r1`–`r4` (review rounds) all live **at the same time**. The denser the work,
the more the qualifier is needed and the less it feels needed. That inversion is the trap.

**How to apply, in addition to the above:** qualify on **every** use in a report, not just first use
per message — a reader who skims lands mid-message, and a table row or a bullet is its own entry
point. Cheapest habit: never type `#` without the noun in front of it. `backlog #154`, `PR #330`,
`round 4`, `ADR-0010`.

## feedback define terms

Define new terms, acronyms, and domain jargon **inline, in plain language, on first use.** Don't assume the user knows an acronym or a coined term just because it's in the code or spec.

**Why:** Unexplained jargon confuses the user and slows comprehension. They explicitly asked for reader-friendly writing.

**How to apply:** The first time an acronym or non-obvious term appears in a turn, gloss it briefly in parentheses or a short clause — e.g., "settle (write the *real* cost, not the estimate)", "RLS (row-level security — the DB rule that keeps one user's rows invisible to another)", "the reaper (the sweep that reclaims jobs whose worker died)". Keep it short; don't lecture. Pairs with the standing preference for plain, easy-to-grasp output ([[the-user-does-not-follow-in-real-time]]). Related: [[feedback-flag-transitional-choices]].

**Never use bare back-references as labels** (added 2026-08-02). Numbering items "#1/#2/#3" in one turn and then referring to "#1 and #2" later — even a few messages on — is unreadable: the user often returns to a thread **days later** and has to scroll back to decode it. Give every item a **self-describing name** (`the summary-handler lost update`, `the dig-at-a-deleted-base race`) and reuse the name, not the number. Same rule for `A3`, `Class A`, `WB-H1`-style internal codes: name what it *is* on each use ("A3 — the base relocation").

**Compactness is a real failure mode, not a style preference.** The user has twice said an explanation was too compressed to follow, and that they were left guessing or skipping. When explaining a race, a bug, or an interaction: give a **concrete timeline with real values** (serial 3 vs 7, `007_alpha.md`), say **who writes what**, and state **what is actually lost**. Prefer one worked example over three abstract sentences.

