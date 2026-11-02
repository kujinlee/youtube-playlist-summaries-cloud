# Round 1 — `review-tooling-121-182` (PR #439, backlog #121, backlog #182) — coordinator — NOT CONVERGED (both halves)

Codex half: `docs/reviews/codex/review-tooling-121-182-r1-codex.md`. Claude half: `docs/reviews/claude/review-tooling-121-182-r1-claude.md`. Both reviewed `76b829ee`.

```yaml
round: 1
fixes_nontrivial: true
subject: review-tooling-121-182
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: gap-reader, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: gap-reader, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: gap-reader, disposition: fixed}
  - {id: X4, severity: High, aim: deliverable, fix_induced: false, component: codex-review, disposition: fixed}
  - {id: X5, severity: High, aim: deliverable, fix_induced: false, component: gap-reader, disposition: fixed}
  - {id: X6, severity: Medium, aim: instrument, fix_induced: false, component: mutation-manifest, disposition: fixed}
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: gap-reader, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: codex-review, disposition: fixed}
  - {id: C3, severity: Low, aim: instrument, fix_induced: false, component: mutation-manifest, disposition: fixed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: gap-reader, disposition: declined}
```

**The gap reader (X1–X3, X5, C1).** Five of the findings share one cause. `yaml_gap()` is a permissive hand parser over YAML it cannot really parse, so it accepted:
- a GAP for the wrong half (X1, and Claude F2);
- a `claude:` key inside a block scalar under `halves:` (X2);
- a comment where the reason belongs (X3);
- a `yaml` fence anywhere in the document instead of the header after the title (C1).

It also returned only one gap where `check-review-recorded.first_codex_gap()` needs the codex one (X5, and Claude F4).

**Fold: narrow the grammar to the one form the corpus uses, instead of parsing more.** Measured over `docs/reviews`: all 87 YAML gap lines are a two-space-indented `codex:` or `claude:` directly under `halves:`, with a double-quoted `"GAP: <reason>"`. The single other line is a stand-in note, not a gap. So:
- read only the header fence, as `check-review-decision.parse_header` does;
- read only direct children of `halves:` at exactly two spaces, and stop at the first line that isn't one;
- require a double-quoted value whose reason is non-empty and isn't a comment;
- return a gap for EACH half;
- make the audit require the gap of the half that is actually missing.

C4 (trailing comments, flow mappings and CRLF not read) is **declined**: an unread form fails CLOSED, as a missing review, and widening the grammar is what produced X1–X3.

**The wrapper (X4, C2).** Codex inherits `GIT_DIR`/`GIT_WORK_TREE` while the recorded head strips them (X4). Filing, the intrusion watch and the `--out` refusal still use `REPO_ROOT` (C2). Fold:
- one environment, with `GIT_*` stripped, for both the recorded state and the Codex subprocess, whose `cwd` is the reviewed root;
- the `--out` refusal and the watch also cover the reviewed root's `docs/reviews/`.

Filing stays under `REPO_ROOT`, as the rows scope it; the PR body says so.

**Instrument (X6, C3).** These mutants survived: "last yaml fence", "`cwd=REPO_ROOT` on the Codex subprocess" and "delete the blank-line skip". Each gets a case that kills it.
