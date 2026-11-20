# Round 2 — `memory-shape-check` — coordinator — ❌ NOT CONVERGED (2 High, 2 Medium)

The Codex half reviewed `97eed4d8` (branch `memory-shape-check`, PR #605, `scripts/check-memory-shape.py`, the
round-1 fold). Codex (`gpt-6.1-terra`, `docs/reviews/codex/memory-shape-check-r2-codex.md`, 2 MAJOR, 2 MINOR)
was NOT CONVERGED. Its baseline: `self-test: 89/89`, `docs/memory/` ok at 195 files, and the live memory folder
FAILED on one true positive (see *Live corpus* below).

REVIEW GAP: claude — alternation

```yaml
round: 2
fixes_nontrivial: true
subject: memory-shape-check
halves:
  codex: ran
  claude: gap
findings:
  - {id: XM1, severity: High, aim: deliverable, fix_induced: false, component: frontmatter-parser, disposition: fixed}
  - {id: Xm1, severity: Medium, aim: deliverable, fix_induced: true, component: frontmatter-parser, disposition: fixed}
  - {id: XM2, severity: High, aim: deliverable, fix_induced: true, component: link-reader, disposition: fixed}
  - {id: Xm2, severity: Medium, aim: deliverable, fix_induced: true, component: link-reader, disposition: fixed}
```

`X` = the Codex half; `M` = MAJOR, `m` = MINOR. Every finding was REPRODUCED before it was fixed. Each input was
built in a scratch directory outside the repository and run against `97eed4d8`. Each gave the observation the
review reported:
- XM1: `[]`.
- Xm1: `FRONTMATTER … unterminated double-quoted string`.
- XM2: `UNLISTED a.md`.
- Xm2: `[]`, so `gone` was hidden.

The new suite was then run against the OLD rule code (the `97eed4d8` rules with the new self-test attached). It
gave **94/102, 8 red**, and every finding has at least one of the red cases. The two cases added later (below) pin
behaviour that the old code already had, so they cannot be red on it. Each is guarded by a mutation.

**fix_induced.** Xm1, XM2 and Xm2 are caused by the round-1 fold. XM2 and Xm2 come from its `<!-- -->` stripping,
which knew nothing about code spans. Xm1 comes from its `_DQ_RE.fullmatch`, which allowed nothing after the
closing quote. XM1 is NOT fix-induced: before the fold, the reader accepted every double-quoted value, and the fold
did not narrow its escapes.

**PyYAML is not used.** It is not importable in this checkout's `python3` (`ModuleNotFoundError: No module named
'yaml'`). It is also not installed by the CI job that runs this check. So the hand parser stays, made correct for
the two cases the brief named.

## Fold

| Id | Finding | Reproduced on `97eed4d8` | Fix | Cases (red on the old code) |
|---|---|---|---|---|
| XM1 | `description: "bad\q"` passes | `[]` | `_DQ_RE` admits only the YAML 1.2 §5.7 escapes: `\0 \a \b \t` TAB `\n \v \f \r \e \  \" \/ \\ \N \_ \L \P \xHH \uHHHH \UHHHHHHHH`. A value that only the loose any-escape form closes is reported as *an escape YAML does not define*, apart from *unterminated* | FRONTMATTER on `"bad\q"`; `scalar_problem` names a bad escape and an unterminated string apart. Adjacent: every defined escape in one value stays NOT malformed |
| Xm1 | `description: "valid" # comment` refused | `FRONTMATTER … unterminated` | After a closing quote, only `\s+#…` may follow (`_TAIL_RE`). A plain value's ` #…` is dropped before the `: ` rule. The value READ drops its trailing comment, quoted or plain (`scalar_text`) | NOT malformed: `"valid" # comment`, `d # see: the rule`. `name: "beta" # the slug` is the slug. Refused, and kept refused: `"a" b`, `"a"#x` (YAML needs whitespace before `#`) |
| XM2 | `` `<!--` [[a]] `` hides `a` | `UNLISTED a.md` | `_COMMENT_RE` is ONE leftmost scan. It matches a fenced block, an inline code span or a comment. `_keep_code` drops only a comment and keeps code whole. So a delimiter inside code is consumed with the code, and a backtick inside a comment is consumed with the comment. A span closes on a backtick run of the same length, never across a blank line. An opener with no closer is literal | the Codex input stays reachable; a `<!--` in a fenced block that holds a blank line hides nothing after the fence |
| Xm2 | `` `<!--` [[gone]] `-->` `` hides `gone` | `[]` | the same scan | the dead `gone` is now MISSING |

**Cases added after the red run** (they pin a stated bound or an adjacent rule, not a finding):
- `name: beta # the slug`, so a plain value's comment is not read.
- `` see `[[a]]` `` with a fenced `[[b]]`. A link INSIDE code still counts, as the round-1 bound says.

Two `link_targets` cases also show that a literal backtick does not open a span. Both were green on the old code:
- a backtick with no closer;
- a span that would cross a blank line.

**Bound, now stated in the docstring.** An INDENTED code block (four spaces) is not recognised as code. A `<!--`
in one still opens a comment.

## Live corpus

- `docs/memory/`: `memory shape ok — 195 files`.
- The live memory folder (read-only): 1 violation over 197 files. It is
  `FRONTMATTER a-forced-choice-test-cannot-fail.md: … an unquoted value holding `: ``. This is the same true
  positive Codex reported and round 1 fixed in the checked-in copy. The live folder's copy is not this branch's to
  edit.
- No new false positive in either corpus.

## Instruments

- Manifest: 65 → 79 mutations.
  - Eight anchors were rebound to the rewritten scalar and comment readers: the unterminated-quote returns, `_DQ_RE`,
    the `: ` rule (now over `plain`), the empty-value guard, `_COMMENT_RE`'s unclosed arm and the `sub` call.
  - 14 were added. They cover the escape set (2), the bad-escape message, the trailing-comment tail (3), the plain
    comment, the value read (2), and the fence, span, unclosed-span, blank-line and keep-code arms of the scan.
  - `check-plan-code.py --mutate . --only scripts/check-memory-shape.py` ran on a scratch worktree: 79 killed, 79
    attributed, 0 survivors.
- `EXPECTED_MUTATIONS` was raised to 79.
- `check-fixture-variation.py scripts/check-memory-shape.py`: OK, 8 parameters, no new key.
- The docstring's declared count is now 104 cases.
- A decision-log row was added for this unit, `accrete`, `retroactive: true`, `outcome: continued`. The round-1
  fold recorded no row, so `check-decision-scheme.py` trigger 1 (NOT FED) failed on this subject until it was added.

⚠ **For the coordinator.** This fold is a SECOND accrete on the same two components. Round 2's findings were caused
by round 1's fold. If round 3 also carries fold-caused findings in `frontmatter-parser` or `link-reader`, that is the
THRASHING arming condition for Phase 6 (`docs/dev-process.md`). The ladder's next route is then `redesign`.
