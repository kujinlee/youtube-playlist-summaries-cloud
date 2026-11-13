# Round 1 — `answer-binds-file` (PR #543, backlog #544) — coordinator — CONVERGED (both halves); one Medium folded

```yaml
round: 1
fixes_nontrivial: true
subject: answer-binds-file
halves:
  codex: ran
  claude: ran
findings:
  - {id: C-F1, severity: Medium, aim: deliverable, fix_induced: false, component: symlink-binding, disposition: fixed}
  - {id: C-F2, severity: Low, aim: adjacent, fix_induced: false, component: bound-prose, disposition: fixed}
```

Codex (`docs/reviews/codex/answer-binds-file-r1-codex.md`) and Claude (`docs/reviews/claude/answer-binds-file-r1-claude.md`)
both reviewed `3863c11a`, and both report CONVERGED.

**Refutation attempts that held.** These failed to defeat the binding:
- a change to the answer's own file: new bytes, a mode change, a case-only rename, deletion, or a stale `dirty`;
- moving an answer to another line;
- an unreachable head or a failed `ls-tree` (each still HOLDs);
- the same-half rule, checked per id;
- delete-then-re-add laundering.

**C-F1 (Medium) — the symlink-target binding has no end-to-end case.** Renaming `gather`'s `via` key survives the
suite. The fold adds a real-git case that edits the target after the round, plus that mutation; the pin rises by 1.

**C-F2 (Low) — `.gitattributes` is not bound.** A change to `.gitattributes` is a change in a different file, so it
lies inside the bound the owner accepted. The fold names it in the comment that lists what now passes.

**The HOLD to expect.** The Claude half answered the 4 lines carrying the change itself `finding:`: the
`review_answers` signature, its docstring, and the two lines of the flipped "any edit voids" case. That is true: they
ARE the loosening. The owner approved it on 2026-11-08 at 11:33 PST, card A: "do A and create explain-topic page for
that". Verified line by line at merge time, those 4 are the owner-approved change and nothing else.
