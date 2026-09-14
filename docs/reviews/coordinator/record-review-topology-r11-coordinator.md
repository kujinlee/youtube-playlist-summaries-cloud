# record-review-topology — round 11, coordinator adjudication

**Both halves ran.** Claude: `docs/reviews/claude/record-review-topology-r11-claude.md` — the half
owed by all ten previous rounds, discharged as one whole-branch review against the shipping tree
rather than ten retroactive ones. Codex: `docs/reviews/codex/record-review-topology-r11-codex.md`
(`gpt-5.5`), verdict `docs/reviews/verdicts/record-review-topology-r11-codex.verdict.json`,
`gate_ran: true`, `head dc9fe107`, `dirty {}`.

That verdict is also the first to carry the new `prompt` field — the r11 High that no mechanism can
close, recorded rather than hidden.

## Claude half — 1 Blocking, 7 High, 6 Medium, 7 Low

All Blocking and High addressed in `dc9fe107`; the adjudication and the evidence are in the review
document itself. The two headline findings are one expression pulling opposite ways, and the
measurement that settles them is on this branch: the gate went from naming five files — three of
them `origin/master`'s own, already reviewed — to naming exactly the two genuinely unreviewed.

## Codex half — 1 Blocking, nothing else

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | Blocking | The 21 new mutation entries are **not measurable by the project's own contract**. `check-plan-code.py:966-968` refuses an entry whose EDIT ANCHORS repeat an earlier entry's, and two pairs did exactly that; and attribution is `w == f` — **exact equality** (`:1254`) over names from `parse_fail_names`, so the `expect` fragments matched nothing. `--mutate .` exits at the preflight: *"NOT MEASURED — the mutation harness produced no coverage verdict."* | **FIXED** — distinct anchors for both pairs, and every `expect` is now the exact case name, DERIVED from the observed red set rather than transcribed |

**It was right, and it corrected me on a premise I had checked and misread.** Before writing the
entries I read `check-plan-code.py:1977` — *"The duplicate-NAME rule is NOT the duplicate-ANCHORS
rule that entry 9 covers"* — and concluded only names were checked. The sentence says the opposite:
both rules exist. I characterised the code instead of quoting the rule itself, in the one review
where that is the named offence.

## ⭐ What chasing the Blocking then found, which neither half had asked for

`codex-review.py`'s failure printer was `[FAIL] {name}: got={got!r}`. `parse_fail_names` truncates a
case name at the LAST `": got "` — **with the trailing space** — so `": got="` never matched, every
parsed name kept its `: got=…` tail, and `w == f` could never be true. **Every one of the nine new
producer entries would have been unattributable**, and the harness would have said so per file, not
per entry.

It survived this long because nothing had ever tried to attribute a kill in that file: it sat in
`WIDENED_MANIFEST_DEBT` with zero mutations until this round. **Adding the manifest is what made the
producer's silence audible.** This is the recorded *a guard's own output is a CONTRACT* shape,
inside the file that decides whether a review gate ran, and it is the second time this session that
a weaker stand-in disagreed with its subject — the first was my own verifier, matching `expect` as
a substring where the harness uses equality.

The printer is now canonical. The verifier now imports `parse_fail_names` and `load_manifests`
**from the subject** instead of re-deriving them, and `load_manifests` reports `NONE`.

## ⚠ The incident, recorded because it is evidence for a finding

Mid-round, a reviewer probing environment redirection ran `codex-review.py --self-test` under an
exported `GIT_DIR` aimed at the live worktree; the fixture's `git commit` moved this branch's real
ref off its pushed merge commit. Recovered with `git reset --mixed`, verified against `origin`,
nothing lost. It upgraded that finding from reasoned-only to demonstrated, and it is written up in
the Claude half along with the two lessons: a `cp -R` of a git WORKTREE is not isolated until its
`.git` pointer file is deleted, and a brief that forbids mutating git while blessing `--self-test`
forbids nothing.

## ⚠ ROUND 12 IS OWED, by this branch's own rule

The r11 repair touches `scripts/codex-review.py` and both manifests — guarded code — so every round
including r11 is stale against the tree that ships. The gate will say so. Round 12 runs both halves
against the current tree, under the practice this branch exists to protect: **the fixes are held
UNCOMMITTED so the reviewers see the state that will actually merge**, and `reviewed_state` records
the tree entry of each one at dispatch.

NOT CONVERGED — r12 owed.
