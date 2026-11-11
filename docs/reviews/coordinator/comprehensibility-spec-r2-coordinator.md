# Round 2 — `comprehensibility-spec` — coordinator — ⟳ NOT CONVERGED (Codex); 4 fixed, 0 to the owner

```yaml
round: 2
fixes_nontrivial: true
subject: comprehensibility-spec
halves:
  codex: ran
  claude: skipped
findings:
  - {id: C1, severity: High, aim: deliverable, fix_induced: true, component: status-facet, disposition: fixed}
  - {id: C2, severity: High, aim: deliverable, fix_induced: true, component: needs-you, disposition: fixed}
  - {id: C3, severity: High, aim: deliverable, fix_induced: true, component: needs-you, disposition: fixed}
  - {id: C4, severity: Medium, aim: deliverable, fix_induced: true, component: freshness, disposition: fixed}
```

REVIEW GAP: claude — alternation

Reviewed head `fde542a7`. Codex half: `docs/reviews/codex/comprehensibility-spec-r2-codex.md` (C1–C4, its findings
1–4; verdict `docs/reviews/verdicts/comprehensibility-spec-r2-codex.verdict.json`). Round 2 is alternated, so only
Codex ran. Folded into `docs/superpowers/specs/2026-11-02-comprehensibility-suite-design.md`.

**Rule applied:** the owner's answers (spec §1, §8, §10 Q1) are fixed; a finding is escalated only if its only sound
fix changes one. None did.

| ID | Sev | Disposition | What the spec now says |
|---|---|---|---|
| C1 | High | FIXED | §4: a normalisation (strip leading `🔴🟠🟡🟢🔵⏳⟳` and a `(was …)`/`(filed …)` parenthetical; first word, upper-cased), then a table DERIVED from all 422 rows through `gen-backlog-page.parse` on `fde542a7`: `✅` 131 → done; OPEN/PENDING/REOPENED/FIX/IN/BLOCKED 249 → open; DEFERRED 2 → parked; 20 prose-leading and 20 contradicted by a later `✅` → by hand; empty 0. No first word maps to `needs-you` — set by hand on 16 flagged rows. No default; the facet is prepended, the old cell (glyphs, `ACTION:`) kept. Also corrected: severity glyphs lead the Status cell on 189 rows, not only the Item cell. §5 and §9 re-measured |
| C2 | High | FIXED | row 4 and §7 now use D1's rule verbatim: "waiting until picked" excludes rows ANY live entry references. Kept consistent by an invariant — an entry that picks a `needs-you` row MUST be `owner-wait`; a live non-`owner-wait` entry referencing one is reported by §7's completeness falsifier. Both sources of D1 unchanged |
| C3 | High | FIXED | row 4 *Answering — one order*: (1) write the ROW (status leaves `needs-you`, prose records `answered <date> — closes entry <id>`), (2) close the ENTRY. In between: "blocking now" only. Recovery: a live `owner-wait` entry named by a `closes entry <id>` note is closed at the next tray load or session start. Entry-first forbidden. Row-only and entry-only cases stated. §7 *Answering is ordered* falsifier added; the dashboard-asks bullet's "closes the entry OR changes the status" removed |
| C4 | Medium | FIXED | §7 freshness compares against the REMOTE tip (`git ls-remote origin refs/heads/master`), merge time from GitHub (`mergedAt`, else the tip's committer date); a failed remote query is NOT RUN, never a pass |

**Counts:** 4 findings — 4 fixed, 0 rejected, 0 escalated.
**Fix-induced:** all 4 — each sits in text the round-1 fold wrote (C1: H5's migration table; C2: C1's
`owner-wait` exclusion; C3: C1's "same step" and H4's tray line; C4: C6/L2's `origin/master` bound). This is the FIRST
round with fix-induced findings (round 1 had none), so the thrashing condition (two consecutive) is not met; if round 3
again finds fix-induced findings in `needs-you`, Phase 6 arms.
**Next:** round 3, ONE half (alternation: Claude).
