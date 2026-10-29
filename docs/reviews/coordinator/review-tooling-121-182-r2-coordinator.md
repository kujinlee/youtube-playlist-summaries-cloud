# Round 2 — `review-tooling-121-182` (PR #439) — coordinator — NOT CONVERGED (Codex); the round-1 bet is refuted

REVIEW GAP: claude — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 2
fixes_nontrivial: true
subject: review-tooling-121-182
halves:
  codex: ran
  claude: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: gap-reader, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: true, component: gap-reader, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: codex-review, disposition: fixed}
  - {id: X4, severity: High, aim: deliverable, fix_induced: false, component: codex-review, disposition: fixed}
  - {id: X5, severity: Low, aim: instrument, fix_induced: true, component: mutation-manifest, disposition: fixed}
```

Codex reviewed `e960e592`, the fold first. It found:
- **X1:** a finding's yaml example is still read as the header when it is the document's first fence.
- **X2 (fix-induced):** collecting EVERY prose `REVIEW GAP:` match turns a quoted codex gap into a waiver.
- **X3:** `abspath` collapses `alias/..` before `realpath` resolves the symlink, so an `--out` can overwrite a filed review unwatched.
- **X4:** a reviewed root without `docs/reviews/` yet is never watched.
- **X5 (fix-induced):** the realpath mutant is killed only by macOS's `/var` vs `/private/var` spelling.

**The round-1 bet is lost** (see the decision log). It narrowed WHAT a declaration looks like. X1 and X2 show that the question is WHERE one may appear: the reader still cannot tell a declaration from an example of one, and no grammar of the line can decide that.

**Next rung: REDESIGN, by position.** A gap declaration and the header count only in the document's PREAMBLE, the lines between the `# ` title and the first `## ` heading. Prose and examples after that point are never read as declarations. Measured over the corpus:
- 179 of 191 prose `REVIEW GAP:` lines are in the preamble;
- 247 of 251 yaml headers come before the first `## `.

The rounds whose result changes are exempted by name with a reason, or shown to be quotations. X3, X4 and X5 are local to the wrapper: realpath the joined path before any normalisation, watch a missing directory, and kill the realpath mutant with an explicit symlink.
