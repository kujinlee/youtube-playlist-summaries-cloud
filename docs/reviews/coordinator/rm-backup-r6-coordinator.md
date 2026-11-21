# Round 6 — `rm-backup` — coordinator — ⟳ NOT CONVERGED (Claude: 1 MAJOR, 1 MINOR); Phase 6 (4 findings, 3 BLOCKERs); ALL FOLDED by one refusal

REVIEW GAP: codex — alternation (round 6 runs ONE half; round 5 was Codex).

Subject: PR #608, branch `rm-backup-hook`, reviewed head `4cc1cedf` (a delta review of the r5 fold). Half:
`docs/reviews/claude/rm-backup-r6-claude.md`. Convened alongside it, because round 5 ARMED thrashing on `glob`:
the Phase 6 architecture review `docs/reviews/architecture-review-2026-11-20-rm-backup-glob.md` (Opus), verdict
**MERGE AFTER A NAMED SMALL FIX**. The fold was written by the coordinator in the scratch repo `fold-r1`
(commit "fold r6 + Phase 6") and copied into this branch.

```yaml
round: 6
fixes_nontrivial: true
subject: rm-backup
halves:
  claude: ran
  codex: gap
findings:
  - {id: R6-1, severity: Major, aim: deliverable, fix_induced: true, component: glob, disposition: fixed}
  - {id: R6-2, severity: Minor, aim: deliverable, fix_induced: true, component: glob, disposition: fixed}
  - {id: P6-1, severity: Blocker, aim: deliverable, fix_induced: false, component: glob, disposition: fixed}
  - {id: P6-2, severity: Blocker, aim: deliverable, fix_induced: false, component: glob, disposition: fixed}
  - {id: P6-3, severity: Blocker, aim: deliverable, fix_induced: false, component: glob, disposition: fixed}
  - {id: P6-4, severity: Minor, aim: deliverable, fix_induced: false, component: glob, disposition: fixed}
```

**Past the round cap** (`review-method.md` §0 Q4c): only BLOCKERs are folded. P6-1..P6-3 are; R6-1, R6-2, P6-4 and
the review's older `"a[1]"*` miss are closed by the SAME change (each is a case of its first test), so they are
recorded `fixed`, not filed.

| Id | Command | Hook at `4cc1cedf` | bash 3.2 deleted |
|---|---|---|---|
| R6-1 | `rm -f [\!a-]*` | literal reading `[a-!]` is an empty range | `!x`, `a1` — `a1` LOST |
| R6-2 | five negated sets | refusal untested | — (no case, no mutation) |
| P6-1 | `rm -f [a-z]*` (UTF-8 locale) | code-point range | also `Makefile`, `README.md` |
| P6-2 | `cd "app/[id]" && rm -f *.bak` | `[id]` read as a set | every `.bak` |
| P6-3 | `rm -f "app/[id]/"*.bak` | quotes dropped, `[id]` a set | the bracketed files |
| P6-4 | `rm -f -- [a\-z]x` | escaped `-` read as a range | `-x` |

**The cause, one sentence (Phase 6 §2).** The union of readings covers only a negator hidden by quotes; a bracket
set beside a wildcard can be quoted (wholly literal) and a range follows locale collation, and NO Python reading
reproduces either, because the lexer has already dropped which characters were quoted.

**The fold — refuse what no reading can match (Phase 6 §4, prototype `p6/proto/crb.py`).**
- A target holding `[` together with `*`/`?`, or a `-` inside a set, is REFUSED with a message.
- The `cd` directory is `glob.escape`d before the target is joined to it.
- What remains globbed — a set with no wildcard and no range — is read every way (negated and literal caret)
  PLUS the target as a literal name, so the r5 "raw target" and r6 "all-literal" readings were dead and are
  removed (their mutations with them).
- Cases: the four r4–r6 bracket cases are rewritten on single-character fixtures (no wildcard), each
  expectation checked against bash 3.2 by `echo` expansion (`h/[^k]` → `! ] ^ a b`; `h/[\!a]` → `! a`;
  `h/[k^]` → `^ k`; `h/[!]^]` → `! a b k`; `h/[^a/b]one` → itself; `cd "app/[id]"; *.bak` → `x.bak`), each a
  subset of the plan; plus "a bracket set beside a wildcard, or holding a `-`, is refused" and "a bracketed
  working directory is a literal path". Mutations: three added (each refusal half, the escape), three dropped,
  R6-2's cap now killed.

**Measured after the fold (scratch "fold r6 + Phase 6", copied into this branch):** self-test 127/127; scoped
mutation sweep 101/101 killed, each by the case it names; replay over 18,468 past Bash calls: 186 `rm`s seen,
118 refused — 0 verdicts changed against round 5 (Phase 6 measured 0 of 562 recorded `rm` calls with a real
bracket glob target).

**Thrashing.** R6-1 is caused by the r5 fold (`glob`), so the chain is R4-1 → S29 → R5-1/R5-2 → R6-1. Phase 6 was
convened for it before the merge and its answer is this fold: the hook stops deriving a meaning it cannot know
and refuses instead. The class-removing redesign (ask bash, `compgen -G`, with a quote-aware lexer; measured safe
and 5 ms a call by the review) is recorded on **backlog #686**, size M.
