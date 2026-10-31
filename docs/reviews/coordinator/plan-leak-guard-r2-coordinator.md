# Round 2 — `plan-leak-guard` (PR #443, backlog #393) — coordinator — NOT CONVERGED; route SPLIT

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 2
fixes_nontrivial: true
subject: plan-leak-guard
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - id: F1
    severity: Blocking
    aim: deliverable
    disposition: fixed
    fix_induced: false
  - id: F2
    severity: High
    aim: deliverable
    disposition: filed
    filed_as: "backlog #416"
    fix_induced: false
  - id: F3
    severity: Medium
    aim: deliverable
    disposition: fixed
    fix_induced: true
  - id: F4
    severity: Low
    aim: deliverable
    disposition: fixed
    fix_induced: false
  - id: F5
    severity: Low
    aim: deliverable
    disposition: fixed
    fix_induced: true
  - id: F6
    severity: Low
    aim: deliverable
    disposition: filed
    filed_as: "backlog #416"
    fix_induced: false
  - id: F7
    severity: Low
    aim: deliverable
    disposition: filed
    filed_as: "backlog #416"
    fix_induced: false
  - id: F8
    severity: Low
    aim: deliverable
    disposition: filed
    filed_as: "backlog #416"
    fix_induced: false
  - id: F9
    severity: Low
    aim: deliverable
    disposition: filed
    filed_as: "backlog #416"
    fix_induced: false
```

Claude reviewed `821929e9`, the pre-push redesign plus the master merge, with real pushes into bare remotes.

**The redesign held** on every push form, history shape and metadata channel tried. The public-at-base filter is not fed by an earlier commit of the same push, and SessionStart install and warn behave as described. 105/105 cases passed; 68/68 mutations were killed and attributed.

**Route: SPLIT.** Round 1 spent the REDESIGN rung.
- **Fold:** F1, Blocking: `diff.noprefix` drops every added line, giving a silent hits 0. F3 and F5, both caused by the redesign: a relative hooks path resolved from another directory, and a file-name hit printing its phrase. F4, cheap: `GIT_NO_REPLACE_OBJECTS`.
- **File as backlog #416:** F2, markup and entity normalisation, which is the larger change and is measured against the 97 committed explainers; F6, an abbreviated `--no-verify`, which predates this PR; F7, numbered and table rows in plans; F8, ref names; and F9, text that `gh` publishes without a push (PR bodies, comments, `gh api` writes), added after the fold started.

**False-block check, last 40 merged commits: 1 hit.** `82fc68f1`, `docs/memory/push-is-mine-merging-is-theirs.md:60`. The coordinator judged it without printing plan text: the line shares ONE 8-word run with one plan, and that run is a quotation of one of the owner's own chat instructions, which appears in both places. So it is not plan-authored text, and the hit is a false block. It is recorded here as the measured false-block rate: 1 in 40.
