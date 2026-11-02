# Round 1 — `comprehensibility-spec` — coordinator — ⟳ NOT CONVERGED (both halves); 18 fixed, 1 to the owner

```yaml
round: 1
fixes_nontrivial: true
subject: comprehensibility-spec
halves:
  codex: ran
  claude: ran
findings:
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: needs-you, disposition: fixed}
  - {id: C2, severity: High, aim: deliverable, fix_induced: false, component: needs-you, disposition: fixed}
  - {id: C3, severity: High, aim: deliverable, fix_induced: false, component: key-links, disposition: fixed}
  - {id: C4, severity: Medium, aim: deliverable, fix_induced: false, component: goal-facet, disposition: fixed}
  - {id: C5, severity: Medium, aim: deliverable, fix_induced: false, component: goal-facet, disposition: fixed}
  - {id: C6, severity: Medium, aim: deliverable, fix_induced: false, component: freshness, disposition: fixed}
  - {id: C7, severity: Medium, aim: deliverable, fix_induced: false, component: question-check, disposition: fixed}
  - {id: C8, severity: Low, aim: deliverable, fix_induced: false, component: row-order, disposition: fixed}
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: freshness, disposition: fixed}
  - {id: H2, severity: High, aim: deliverable, fix_induced: false, component: goal-facet, disposition: fixed}
  - {id: H3, severity: High, aim: deliverable, fix_induced: false, component: status-facet, disposition: fixed}
  - {id: H4, severity: High, aim: deliverable, fix_induced: false, component: needs-you, disposition: filed}
  - {id: H5, severity: High, aim: deliverable, fix_induced: false, component: status-facet, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: key-links, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: false, component: key-links, disposition: fixed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: false, component: explainers, disposition: fixed}
  - {id: M4, severity: Medium, aim: deliverable, fix_induced: false, component: page-roles, disposition: fixed}
  - {id: M5, severity: Medium, aim: deliverable, fix_induced: false, component: question-check, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: vocabulary, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: false, component: freshness, disposition: fixed}
```

Reviewed head `e2ac6e41`. Codex half: `docs/reviews/codex/comprehensibility-spec-r1-codex.md` (C1–C8, its
findings 1–8). Claude half: `docs/reviews/claude/comprehensibility-spec-r1-claude.md` (H1–H5, M1–M5, L1–L2).
Folded into `docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md`.

**Rule applied:** the owner's answers (spec §1, §8) are fixed. A finding is ESCALATED only when its only sound
fix changes one of them; it is then a §10 question with a recommendation, undecided. One was: H4's action half.
H4 is recorded `filed` (OPEN) because that half waits on the owner; its decision half is fixed.

| ID | Sev | Disposition | What the spec now says (or why not) |
|---|---|---|---|
| C1 | High | FIXED | §6 row 4: decision identity = its backlog row; "waiting until picked" EXCLUDES rows a live `owner-wait` entry references; pickup is one write (the entry), so no window and no overlap; entry closing unanswered returns the row, answered changes its status; §7 overlap + absence falsifiers |
| C2 | High | FIXED | `entry_kind() == "owner-wait"` is the predicate; legacy `WAITS-ON-OWNER:` entries migrated; `needs_from_ledger` moves off `waits_on_owner()`; `owner-instruction` excluded (§1 D1, row 4) |
| C3 | High | FIXED | §3: goal cards and goal-tree threads get ids (row 1); thread id rule incl. first-occurrence and past trees; §7 "Links resolve" + a resolving check in row 1 |
| C4 | Medium | FIXED | §7 Feature → goal tests the RESOLVED anchor (explicit, inherited, `none — <reason>`) and unknown slugs |
| C5 | Medium | FIXED | §4 goal derivation: deduplicated union over every node claiming any area; `none` → empty set; empty union shown "no goal" and reported |
| C6 | Medium | FIXED | §7 freshness: recorded source commit vs `origin/master` tip, 1 minute (D3's own words), incl. a rebuild that never ran |
| C7 | Medium | FIXED | row 12: per-type registry of question ids, missing declaration fails, §2 restatements made concrete; the semantic-overlap BOUND is stated |
| C8 | Low | FIXED | #385's closure is row 11, the check is row 12 and last |
| H1 | High | FIXED | D3 marked done (PR #433, `regen-pages.sh`); old row 1 dropped; §5 states the residual gap (merges outside a session's `gh pr merge`) that the freshness falsifier catches; stale 10-25/10-23 citation removed |
| H2 | High | FIXED | measured: `DEPENDS` relations are survives / partly-dissolved-by / blocked-by / dissolved-by on one root (`stable-blob-addressing`); rows 20–22 are deleted by that goal, not serving it — DEPENDENCY, not membership. Kept; `/goals` shows two bands; ADR-0010 ⟳ Scope amendment in row 3. Fits the owner's "derive via area", so not escalated |
| H3 | High | FIXED | §4 *Not a facet*: `check-goal-status` vocabulary is a DOCUMENT's state; shared words mean the same; a spec waiting on the owner enters "blocking now" via an `owner-wait` entry; `/goals` badge counts nothing |
| H4 | High | FILED (decision half FIXED; action half ESCALATED) | row 4: readable asks converted to an entry or a `needs-you` row, 29 unreadable repaired-then-converted or closed, `needs_from_dashboard` + dashboard input to `consolidate` deleted, `[needs-you]` kind retired, answer tray moves to the goal tree's sets and writes the item's own source. Owner actions: §10 Q1 (recommended: include, marked `action`) |
| H5 | High | FIXED | §4: no severity column exists; facet = first word of the existing `Status` column; migration table for 13 keywords and 57 empty cells; `✅` leaves the Item cell; filter treats parked/needs-you as not closed. §8 Q3 (coordinator's) revised |
| M1 | Medium | FIXED | re-measured across line breaks: 6 sites (3 backlog, 2 PR incl. `gen-dashboard.py:966-967`, 1 dashboard); `/dashboard#` and `/goal-tree#` added to §7; `key_link -> str | None`, repo from `repo_slug()`; mutation manifest named in row 1 |
| M2 | Medium | FIXED | §3: goal tree does not import `page_markup`; row 1 moves `goal-tree.segments` into it |
| M3 | Medium | FIXED | row 7: `<meta name="subject">` with a `concept` value; the subject page's generator reads it; PR/concept get no back-link; Q7 check is row 8 |
| M4 | Medium | FIXED | backlog's "Since your last visit" becomes a link to the goal tree's since-T (row 6); `/goals` badges/rungs/PR lists justified in-role (§2); bare `#N` chips qualified and in the §7 key falsifier |
| M5 | Medium | FIXED | row 12 creates the declarations (per page TYPE registry) it checks |
| L1 | Low | FIXED | CONTEXT.md update in row 3; seven-producer list labelled as updated after D2 |
| L2 | Low | FIXED | one bound, in time (with C6/H1) |

**Counts:** 19 findings — 18 fixed, 0 rejected, 1 escalated (H4's action half → spec §10 Q1).
**Fix-induced:** none (round 1). **Next:** round 2, ONE half (alternation), after the owner answers §10 Q1 or in parallel with it.
