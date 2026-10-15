<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None established.

## High

None established.

## Medium

- **M1 — The rewritten refusal misidentifies the destination when external storage and degradation coincide.** `.claude/hooks/enforce-handoff-path.sh:75` says the hook prints “the SHARED path above,” referring to `.remember/remember.md`. With external storage, `handoff_mode=per_session`, and no session ID, the live hook instead printed `<external-store>/remember.md` plus the degradation notice. The instruction to obey the hint remains safe; its new explanation contradicts the displayed destination. Say “the shared file in the resolved store.”

- **M2 — The fold’s prescribed inventory command still skips the symlink on this machine.** `.agents/skills/handoff/SKILL.md:15`, `scripts/check-handoff-path.py:49`, `docs/process-rationale.md:371`, and the new memory lesson recommend `grep -R` as the fix. Installed BSD grep treats `-R` and `-r` identically and defaults to skipping symlinks. `grep -Rn REMEMBER_HANDOFF .claude/skills` returned no matches; `grep -RSn` found the handoff skill. Specify GNU grep or use the verified BSD flags. The fold’s claimed verification does not establish symlink coverage here.

- **M3 — The fold withdraws claims in one location while retaining affirmative versions elsewhere.** `scripts/check-handoff-path.py:45` still says “measured stale by 376 lines,” contradicting the new withdrawal of measured drift. The dashboard’s technical block at `:14880–14889` still invokes absent `check-withdrawal`, names “either settings file,” and says `.remember/` contains only `remember.md`. The actual resolver selected three absent configuration layers; the resolved store contained **104 entries**, with one matching `remember*`. These are incomplete repairs within the fold’s expressly claimed withdrawal.

- **M4 — The newly expanded provenance does not support “FIVE consecutive rounds” on the harness.** `docs/memory/a-harness-cannot-read-a-cause-from-a-childs-text.md:3–7` changes four rounds to five and identifies rounds 9–13. Reading those records from `backlog-249-260-fixes`, rounds 9–10 concern withdrawal/parser problems; their harness mentions are validation or coverage discussion. They do not establish five consecutive rounds with the stated harness cause. Round 13 also explicitly refutes the frame-marker and identifier repairs summarized as having worked. Bound the account to the witnessed rounds and disclose the remaining defects.

## Low

- **The dashboard retains contradictory counts.** `docs/dashboard-entries.md:14834` still says four documents, and `:14858` says “both” hint situations; the rewritten surrounding account says five sites and three situations.
- **The fold introduces trailing whitespace.** `git diff --check 7cf48d43^..7cf48d43` fails at `docs/reviews/codex/plugins-handoff-citations-r1-codex.md:16,22`.

## Checked and found SOUND

- Whole-worktree `grep -RS` inventory included dotted directories and symlink targets. **No sixth distinct live stale-locator site established.** Historical quotations and the skill alias are not additional live sites.
- Live hook probes confirmed the three Boolean hint conditions. No fourth trigger established. Valid IDs select per-session files; missing, empty, `..`, and slash-containing IDs degrade to the shared file.
- The real resolver selects `single`; all three actual configuration sources are absent. No fourth configuration layer established.
- Handoff guard passes. Self-test passes **10/10**, covering seven synthetic text cases and three file cases. It does not itself test the rewritten skill; the separate normal invocation does.
- Skill instructions retain read-before-write, printed-path precedence, the subagent exception, artifact references, and next-session tailoring. No instruction weakening established.
- Refusal render: **exit 2**, empty stdout, complete **29-line stderr**, no sentinel expansion. Literal `$TMPDIR` and `$EDITOR` survive.
- `docs/plugins.md` remains **260/260 lines**. Fold: **2 added/2 removed**; whole branch: **5/5**. No load-bearing clause dropped.
- Hook length **2,027** and quoted current locations verified. Dashboard headings remain **307**; memory index rows measure **190** and **172** characters. All five handoff mutation anchors still bind.
- Documentation guard and shell syntax check pass. Repository remains clean.

## CANNOT RUN

**These are failures to validate, not passes.**

- `check-selftest-counts.py` exits **1**, naming both `check-plan-code.py` and `check-paid-caller-arrival.py`. `node_modules` is absent; the paid-caller suite independently returns **12/32**, exit **1**, with `ERR_MODULE_NOT_FOUND`. Both scripts are unchanged by this branch. Environmental; no branch defect filed.
- Historical hook growth, historical “always has” configuration, and the harness experiments cannot be independently reproduced from this worktree. Reading another branch’s review records establishes attribution, not experimental replay.

## Instruments

Commit message read first; both round 1 reviews; fold and whole-branch diffs; whole-worktree BSD grep with explicit symlink following; installed-hook inspection; isolated live-hook runs; real configuration resolver; sentinel refusal rendering; guards, self-tests, mutation-anchor checks, line/count arithmetic, and cross-branch provenance inspection.

**Reviewed `7cf48d43`. No review file written.**
