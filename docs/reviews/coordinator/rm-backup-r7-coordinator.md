# Round 7 — `rm-backup` — coordinator — ⟳ NOT CONVERGED (Codex: 2 BLOCKERs); BOTH FOLDED by refusing every `[` in a target

REVIEW GAP: claude — alternation (round 7 runs ONE half; round 6 was Claude).

Subject: PR #608, branch `rm-backup-hook`, reviewed head `b49c284c` (the round-6 fold plus its push-time fix), filed at
`62268ac9`. Half: `docs/reviews/codex/rm-backup-r7-codex.md` (VERDICT: NOT CONVERGED, two BLOCKERs). Fold written in
the branch worktree; the pre-fold file is kept in the session scratchpad (`608fold7/check-rm-backup.py`).

```yaml
round: 7
fixes_nontrivial: true
subject: rm-backup
halves:
  claude: gap
  codex: ran
findings:
  - {id: R7-1, severity: Blocker, aim: deliverable, fix_induced: true, component: glob, disposition: fixed}
  - {id: R7-2, severity: Blocker, aim: deliverable, fix_induced: true, component: glob, disposition: fixed}
```

**Past the round cap** (`review-method.md` §0 Q4c): only BLOCKERs are folded. Both are.

| Id | Command | Hook at `62268ac9` | bash 3.2 deleted (reproduced in scratch) |
|---|---|---|---|
| R7-1 | `rm -- "[a]"[bc]` in a dir holding `[a]b`, `ab`, `[a][bc]` | backs up `ab` and `[a][bc]` | `[a]b`, with no backup |
| R7-2 | `rm -- [a\]-z]` in a dir holding `b`, `a-z]` | backs up `a-z]` | `b`, with no backup |

Both were reproduced before the fold: `plan` on the pre-fold copy returned exactly the paths above, and a real
`/bin/bash --noprofile --norc -c 'rm …'` in the scratch directory left `[a][bc]` + `ab` (R7-1) and `a-z]` (R7-2).

**The cause, one sentence.** The lexer drops quotes and backslashes, so a target arrives with no record of which
brackets were literal: R7-1 mixes a quoted (literal) set with an active one, which neither the pattern reading nor
the literal-name reading represents; R7-2's escaped `]` makes the range-refusal regex stop one set early.

**Why the fold is a refusal, not a better reading.** This is the fourth round running in which the previous round's
bracket fix carried the next hole (R4-1 → S29 → R5-1/R5-2 → R6-1 → R7-1/R7-2, all `glob`). Phase 6
(`docs/reviews/architecture-review-2026-11-20-rm-backup-glob.md` §3–§4) already decided that a shape the hook cannot
read is closed by REFUSAL inside this PR, and that the class-removing redesign — let bash match the pattern as data
(`compgen -G`), which needs a quote-preserving lexer — is backlog #686. Round 6 refused only the shapes Phase 6 had
measured; round 7 shows the remaining reader is still unsafe, so the refusal now covers the whole class.

**The fold.**
- `plan`: any target containing `[` — bare, quoted, escaped or ANSI-C-decoded — raises `Refuse("a `[` in an rm target
  (…): bracket names and sets are refused until backlog #686 lets bash read them")`, first in the per-target loop.
- Removed as unreachable: `bash_brackets` (the negated/literal-caret readings, the `[:class:]` refusal, the
  five-negated-set cap) and the Phase 6 wildcard/range regex. Kept: `glob.escape(here)` (a bracketed `cd` directory
  is literal) and the `pat`/`lit` split — the literal name still matters, because in a directory the hook cannot list
  `glob` returns nothing while bash passes `nolist/a*` through and `rm` deletes the file `a*` (reproduced in scratch).
- Docstring: the deny line names `[`, and the Phase 6 principle is written down — a refusal is the answer to a shape
  the hook cannot read.
- Cases (128, unchanged count): "r7: a quoted set beside an active one, and an escaped `]` hiding a range, are refused";
  "every `[` in a target is refused, bare, quoted or escaped" (17 inputs: the old r4–r6 bracket inputs, `'a[1].txt'`,
  `a\[1].txt`, `$'a\x5b1].txt'`); "a Next.js route directory as a target is refused, quoted or escaped"
  (`"app/[id]"`, `app/\[id\]/x.bak`, `app/[id]/x.bak`); "a plain name inside a bracketed working directory is backed
  up as that name"; "a wildcard target in a directory the hook cannot list is backed up as the literal name". The
  P6-2 case (`cd "app/[id]" && rm -f *.bak` → backed up) is kept as the control that a `[` in the cwd is not refused.
- Mutations: 103 → 95. Nine removed with their code (`^` negation, POSIX class, leading `]`, raw brackets, negated
  both ways, negated-set cap, wildcard refusal, range refusal, negator-before-`]`). One added: the new refusal
  disabled (`if False:`), killed by the R7 case. Two rebound to new cases: "a pattern is read only as a pattern" (to
  the unlistable-directory case) and "the literal fallback is the escaped pattern" (to the plain-name-in-`app/[id]` case).

**Replay (cost of the rule).** Over 18,580 past Bash calls (the transcripts grew by 52 since round 6's 18,528):
`{'bash': 18580, 'rm_seen': 186, 'refused': 118, 'notchecked': 4, 'would_back_up': 19}`. Compared with
`ref-r6b.json` as sets of (reason, command): 109 distinct refused items in both, the sets IDENTICAL — 0 newly refused,
0 no longer refused, 0 reasons changed. No real past command, a Next.js `app/[id]` removal included, flips.

**Results after the fold.**
- `python3 scripts/check-rm-backup.py --self-test` → `128/128 self-test cases passed`
- `python3 scripts/check-plan-code.py --mutate . --only scripts/check-rm-backup.py` → `OK — delivered scripts mutated: 1 file(s), 95 mutation(s), 95 killed, 95 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/check-rm-backup.py — a DIAGNOSTIC slice, not the gate`
- `python3 scripts/check-docs.py` → `Documentation integrity OK`
- `python3 scripts/check-reference-namespace.py --base origin/master` → `reference namespaces OK — no bare `#N` added in 14 reader-facing surface(s)`
- `python3 scripts/gen-backlog-page.py --self-test` → `247/247 passed`
- `python3 scripts/check-features.py` → `feature map: 35 nodes (31 built, 4 declared absent); 15 anchors and 29 backlog areas all claimed exactly once`
- `python3 scripts/check-fixture-variation.py scripts/check-rm-backup.py` → `fixture variation OK — 12 parameter(s) examined across 1 file(s); 105 known-unvaried ratcheted, 72 exempt with a written reason`

**Thrashing.** Still armed on `glob`, and this fold ends it by construction: there is no bracket reader left to carry
a hole into round 8. What a refusal costs is a bracketed `rm` target the agent must remove another way (a scratchpad
move, or `find` under the scratchpad) until backlog #686 lands; the replay measured that cost at 0 past commands.
Backlog #686 now says so.
