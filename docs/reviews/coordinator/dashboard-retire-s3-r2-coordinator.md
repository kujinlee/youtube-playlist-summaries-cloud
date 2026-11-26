# Round 2 — `dashboard-retire-s3` — coordinator — NOT CONVERGED (Codex), one fold

Codex reviewed the round 1 fold `200c97e0` (`git diff f3bb30da 200c97e0`).

All 25 inputs from round 1 are now refused. The allowed literals are each tied to one file and one exact value, and the `/dashboard` pattern refuses no near-miss route. F3–F6 are closed.

Findings:
- **G1 (High; Codex MAJOR).** F2 is still open. `h = "/dash" + "board#" + slug` passes both checks, because a token scan cannot see a string that is joined at run time. Master's `check-page-links.py` `built_hrefs` refused it.
  - **Fix:** put `/dashboard#` back into `check-page-links.py` (`HREF_LITERAL` / `HOME_PATHS`, wherever master had it), and add a case per reviewer input and a mutation.
  - `/dashboard` now answers with an archive record, so no live page links to `/dashboard#…`.
- **G2 (High; Codex MAJOR, fix-induced).** `scripts/check-retired-references.py` treats any line that begins with `/*` as a whole-line comment, so `/* x */ fetch("/dashboard");` passes.
  - **Fix:** skip a line only when nothing follows the comment's close. Add a case and a mutation.
- **G3 (Medium; Codex MAJOR, fix-induced).** These scan exclusions admit live references:
  - a docstring that code reads as `__doc__`
  - a Makefile, `.html` and `.md` files
  - Python under the exempt prefixes

  The claim "refuses ANY live reference" (docstring, ok message, backlog #736 / the plan's K8 text) is broader than what is scanned.
  - **Fix:** narrow every claim to exactly what is scanned, and name the excluded kinds and why each is excluded. No live Makefile exists. The `.html` and `.md` files are docs and explainer archives that are not loaded as code.

  Widening the scan is not the fix.
- **G4 (Low; Codex MINOR), declined.** The token-boundary mutation turns two cases red. The harness attributes a kill only to the named expect case (`check-plan-code.py`, `run_mutations`), as on PR #643's round 1 fold, so the entry is valid.

**Loosening answers:**
- `1fdca511354b` is G1.
- `ccb31aea05f4` ("merge readiness no longer refuses an open ask in the old store through C1") is the retirement by design. The old store is frozen and pinned byte for byte by L1, so no open ask can be added to it, and asks now live in `docs/asks/` (A1). The owner pre-approved merging the dashboard-retire PRs despite the gate-loosening HOLD (11-24 10:03).

REVIEW GAP: claude — alternation (round 2 is Codex's; round 3 is Claude's).

```yaml
round: 2
fixes_nontrivial: true
subject: dashboard-retire-s3
halves:
  codex: ran
  claude: gap
findings:
  - {id: G1, severity: High, aim: deliverable, fix_induced: true, component: check-page-links, disposition: fixed}
  - {id: G2, severity: High, aim: deliverable, fix_induced: true, component: check-retired-references, disposition: fixed}
  - {id: G3, severity: Medium, aim: deliverable, fix_induced: true, component: check-retired-references, disposition: fixed}
  - {id: G4, severity: Low, aim: deliverable, fix_induced: true, component: check-retired-references, disposition: declined}
```

Review: `docs/reviews/codex/dashboard-retire-s3-r2-codex.md`.
