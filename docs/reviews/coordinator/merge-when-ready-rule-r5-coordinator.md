# Round 5 — `merge-when-ready-rule` — coordinator — ❌ NOT CONVERGED (1 High, 1 Medium) — BET LOST, SPLIT

```yaml
round: 5
fixes_nontrivial: true
subject: merge-when-ready-rule
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XH1, severity: High, aim: deliverable, fix_induced: true, component: hunk-association, disposition: fixed}
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: true, component: hunk-association, disposition: fixed}
```

REVIEW GAP: claude — round 5 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex half, final tree `9bea98cd` (backlog #353's first form), run against real git 2.49.0 output.
It re-applied all 57 mutations over a green control (57/57 via their named cases) and reproduced 8 of 40
with no join refusal.

**XH1 — a FALSE READY, the direction the rule exists to prevent, and caused by #353's own positional join.**
A type change (`T`) is one `--name-status` entry and TWO patch sections; a submodule under
`diff.submodule=log` is one entry and NO section. Equal counts paired a gate's `return 1 -> 0` with the
submodule: `hold_reasons == []`, READY. A `textconv=true` or external-command diff driver suppressing a
gate's section did the same. **XM1:** a plain type change alone made the counts differ -> CANNOT RUN.

**The bet's named failure observation fired**, so the route is SPLIT (decision log, written before round 6):
the PATH SOURCE held — Codex confirmed production paths and statuses come from the machine list — and only
HUNK ASSOCIATION continues.

Dispositions — both FIXED by removing the inference rather than patching it:
- the positional join is DELETED. `gather(read, base)` asks git for EACH entry's patch restricted to its own
  paths (`patch_cmd`: `--literal-pathspecs`, `-- <old> <new>`), so a hunk belongs to its file by construction;
  `patch_hunks` reads hunks only, never a header.
- `GIT_PLAIN` (`--no-ext-diff --no-textconv --no-relative`) and `--submodule=short` make the patch the plain one
  whatever the reader's config, so no driver can hide a section.
- the real-git world adds a type change, a gitlink under `diff.submodule=log`, a textconv and an external
  driver over gates, and a glob-named gate, and ASSERTS the world truly holds a `T` entry with two sections
  and a submodule entry, so the case cannot pass for an ambient reason.
- `main()` and the world both read through `gather`; one git call per changed file (replay: 1,149 calls over
  40 PRs, ~0.5s each). Replay 8 of 40, unchanged.

Mutations 57 -> 59: the count-mismatch entry RETIRED WITH ITS SUBJECT (the join is gone); three anchors
rebound onto per-file patches; three added (`--no-textconv`, `--no-ext-diff`, `--literal-pathspecs` — the last
named on the flag assertion, because git matches a pathspec literally first and a glob can only pull in a
sibling's hunks, a false HOLD). Scoped sweep 59/59, each by its named case. 173 cases.
