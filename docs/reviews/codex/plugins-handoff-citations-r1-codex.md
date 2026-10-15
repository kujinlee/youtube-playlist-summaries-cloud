<!-- codex-review: model=gpt-6.1-sol -->

## Blocking

None found.

## High

None found.

## Medium

- **M1 — A fifth live site still has the stale citations.** `.agents/skills/handoff/SKILL.md:13` retains `:795`, `:809-812`, and `:814-825`. It is tracked, actively consumed, and also exposed through `.claude/skills/handoff`. This refutes “these are all of them” and the new four-site accounts in `docs/process-rationale.md:360`, `docs/dashboard-entries.md:14827`, and `docs/memory/a-vendored-line-number-has-no-owner.md:3`. Remove this site’s locators and correct those accounts.

- **M2 — The claimed withheld hint is actually emitted.** `docs/process-rationale.md:385–389` and `docs/dashboard-entries.md:14857–14860` describe behavior the installed hook explicitly superseded. Its condition at `:1544` includes `HANDOFF_MODE_DEGRADED`; `:1546` prints the shared destination and `:1548` explains the degradation. Executing the actual selection and emission blocks with `per_session` and an empty session ID produced:
  
  ```text
  === HANDOFF ===
  Write next handoff to: /store/.remember/remember.md
  (handoff_mode is "per_session", but no session_id reached this hook -- writing to the shared file above, not a per-session one.)
  ```
  
  Correct both accounts. Also qualify `.claude/hooks/enforce-handoff-path.sh:72–74`: a per-session request does not necessarily mean the shared file is unread.

- **M3 — The prior review is overstated as an ignored finding.** `docs/reviews/claude/velocity-177-r5-claude.md:161` inventories a locator while discussing the scope of a documentation invariant. It does not establish that `:795` was stale or identify the vendored-file drift defect. The new “already flagged exactly this” account at `docs/process-rationale.md:370` and corresponding dashboard/memory claims misattribute the evidence. Describe it as an earlier inventory, or cite an actual finding.

## Low

- `docs/dashboard-entries.md:14864` says “replace eight lines with eight.” The diff replaces **five lines with five**. Net zero is correct.
- `docs/dashboard-entries.md:14871` locates mode selection at `:1165`; `config_into HANDOFF_MODE` is at **`:1164`**.
- “Every citation … pointed into the wrong third” is false: in a 2,027-line hook, both old `:795` and current `:1171` lie in the middle third. The locators are stale, but that characterization overstates the measurement.

## Checked and found SOUND

- **Current configuration selects `single`.** I traced `resolve-paths.sh` → `log.sh` → `lib-memory-dir.sh`. The three actual configuration tiers are plugin `config.json`, `~/.remember/config.json`, and `${REMEMBER_DIR}/config.json`; all are absent. Executing the resolver and merge confirmed the default. Checking Claude settings alone would not establish this.
- This worktree’s store resolves to the **main checkout’s `.remember/`**. A delivery record exists there. No current evidence supports `per_session` being enabled. The directory contains many files, so “holds only `remember.md`” is accurate only if restricted to handoff filenames.
- Hook length **2,027**; shared assignment **`:1171`**; per-session assignment **`:1168`**; emit **`:1666`**; delivery/fingerprint block **`:1571–1640`**; hint **`:1546`** all re-derived.
- `python3 scripts/check-docs.py` passed; `docs/plugins.md` is **260 lines before and after**, with a **260-line budget**.
- Dashboard entry is additive; headings rise **306 → 307**.
- Refusal rendered through an isolated stub guard with **exit 2**. Added lines contain no `$`, backticks, or `!`; literal existing escapes rendered correctly. `bash -n` passed.
- Handoff guard passed; its self-test passed **10/10**. `git diff --check` passed.

## CANNOT RUN

- **#371 measurements:** This checkout cannot reproduce the historical harness findings, producer census, or r9–r12 outcomes. The two new memory files contain no “89 producers” claim themselves. Their historical execution claims remain unverified here—**treat this as NOT RUN**, not a pass.
- **Self-test count gate failed.** It reported both `check-plan-code.py` and `check-paid-caller-arrival.py` red. Missing `node_modules/typescript` is confirmed; the latter independently produced `ERR_MODULE_NOT_FOUND` and **12/32** cases passed. Both are unchanged by this diff; this is environmental, not a branch defect. **Treat this as NOT RUN.**
- Current configuration and a delivery record cannot establish “always has” or “never wrong in practice.” Historical configuration correctness is **NOT RUN**.

## Instruments

Git diff/history checks; recursive `rg` across all four requested trees; numbered installed-hook inspection; configuration resolver/merge execution; actual hook-block execution; isolated refusal rendering; docs and handoff guards; self-test count gate; paid-caller self-test; line/header counts. No review file written.
