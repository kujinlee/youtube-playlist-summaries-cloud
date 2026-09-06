<!-- codex-review: model=gpt-5.5 -->

**Blocking** — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:194-208`

§3.1’s central premise is false: `.claude/executing-plan` is not “exactly as that turn left it” by the time the next `UserPromptSubmit` hook runs. It is a workspace-global mutable file. Between turn T-1 ending and session A’s next prompt, it can be changed by the human (`begin-plan.py --tick`, `--pause`, `rm`), another Claude session in the same working copy, a subagent/session using the same repo, or a Stop hook running in another session. `check-plan-progress.py` also explicitly unlinks it when all steps are ticked (`scripts/check-plan-progress.py:180-182`).

Concrete break: session A ends T-1 armed on plan A, with `## ▶ STEP 2 of 5`. Before A’s next prompt, session B finishes plan B and its Stop hook clears `.claude/executing-plan`. A’s `UserPromptSubmit` now reads `armed=False` and judges A’s prior turn as “banner without a plan,” even though A was armed. The journal file race was deleted, but the shared sentinel race remains.

Fix: either carry per-session/per-turn sampled state again, or make the sentinel session-scoped and window-scoped. A no-state `UserPromptSubmit` design cannot claim all four `decide()` inputs describe the same turn.

**Blocking** — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:196-198`, `:431-445`

F11 does not prove the durability assumption it depends on. `windows()` ordering can show that the prior window’s last record precedes the live window’s first **in final transcript order**; that is not evidence that the prior assistant message had been flushed before the `UserPromptSubmit` hook read the file. The existing bug already proved transcript order is not read-time visibility (`§1.1`, `scripts/check-banner-armed.py:61-65`).

Concrete break: a queued message is submitted while the assistant is still working. `records_since_last_user()` treats “The user sent a new message while you were working” as a real boundary (`scripts/check-banner-armed.py:166-185`), and `UserPromptSubmit` fires when the prompt is submitted, before Claude processes it. If the previous assistant message is still being flushed, the hook can read the same incomplete transcript class that broke Stop. Official Claude Code docs only say `UserPromptSubmit` runs when a prompt is submitted, before processing; they do not guarantee the previous final assistant record is flushed first. Source: https://docs.anthropic.com/en/docs/claude-code/hooks

Fix: F11 must be a real hook-time measurement: capture transcript length/last assistant uuid at Stop and again inside `UserPromptSubmit`, including queued messages, slash commands, `/clear`, resume, and interrupted/continued sessions. A transcript-order assertion is not enough.

**High** — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:246-260`; `scripts/check-banner-armed.py:306-323`, `:490`

§3.2’s blind-spot model is incomplete. It describes only false `unarmed` warnings, but `decide()` has a third wrong-verdict path through the `unbannered` branch. When `banner is None` and `armed=False`, `_plan_steps()` is not called, `steps` is `_UNSET`, `unticked` becomes `0`, and the function returns QUIET.

Concrete break: prior turn was armed, edited a repo file, and emitted no banner. Then the sentinel is removed before the next prompt because the plan finished, was paused, was deleted by the human, or was overwritten/cleared by another session. At `UserPromptSubmit`: `decide([], armed=False, steps=_UNSET, edited=True)` returns QUIET. That is a silent miss of the plan-without-banner class.

Fix: the spec must model missing sentinel + no banner as unknown unless it has a per-turn armed sample. Add an F12-style falsifier for `banner is None`, `edited=True`, prior plan existed, sentinel gone.

**High** — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:251-260`

The claim that the blind-spot rate “cannot be established from recorded transcripts” is too strong. The transcript corpus does contain plan lifecycle signals: `begin-plan.py`, `--tick`, Stop-hook feedback, and “Clearing .claude/executing-plan.” I confirmed at least 20 project transcripts contain `begin-plan.py` references and 10 contain clearing/all-ticked signals. That may not reconstruct perfect sentinel history, but it can produce lower bounds and concrete examples.

Concrete missed measurement: find turns with an all-ticked/clearing hook result after a bannered or unbannered plan turn, then inspect whether the prior window’s highest banner was below total or absent. That directly probes the residue the spec calls invisible.

Fix: rephrase as “not fully measurable from transcripts alone” and mine the available signals before claiming only a loose upper bound.

**Medium** — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:303-318`

§3.5 correctly says exit 2 on `UserPromptSubmit` blocks/erases the prompt, but it over-assumes exit 1 is an ordinary warning channel equivalent to the current Stop wrapper. Claude Code’s current hook docs say non-2 exits are non-blocking errors: the transcript shows a hook-error notice and only the first stderr line, with full stderr going to debug logs. The existing warning messages are multi-line and carry the useful caveats below the first line.

Concrete break: wrapper maps CANNOT_RUN to exit 1 and prints the current multi-line “TREAT THIS AS NOT RUN” message. User sees a generic `UserPromptSubmit hook error` plus maybe the first line, not the full diagnostic. The prompt proceeds, but the observer’s warning channel is degraded.

Fix: specify the actual UX contract for `UserPromptSubmit`: either accept a one-line warning/error, use exit 0 JSON/additional context deliberately, or keep human-facing advisory delivery somewhere that displays the full message.

**Low** — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:356-369`; round-1 finding `docs/reviews/claude/banner-guard-prior-turn-r1-claude.md:142-152`

v3 says only two round-1 non-journal findings survive: opener and assistant-record predicate. That list is incomplete. The `/clear` semantics finding still applies. `/clear` appears inside the transcript, and `records_since_last_user()` does not reset at it; after a clear, the first substantive prompt can still cause the guard to judge a pre-clear turn.

Concrete break: assistant does work, user runs `/clear`, then submits a new prompt. `UserPromptSubmit` fires and the selector can find the last pre-clear assistant window, contradicting §5’s “first substantive turn of a session” language.

Fix: either make `/clear` a hard transcript boundary for this guard, or state explicitly that “session” means transcript file, not visible conversation context, and add a falsifier for the chosen behavior.

**Low** — `docs/superpowers/specs/2026-09-05-banner-guard-prior-turn-design.md:53-80`, `:251-253`

The 48 vs 50 bannered-turn numbers are not explained as different populations. §1.2 says “turns that used a banner at all” = 48 over 524 transcripts / 2104 completed turns. §3.2 says “of 50 bannered completed turns, 26 ended below their total.” Those read like the same population. The spec explains 2628 vs 2629 as live-corpus movement, but it does not explain why the bannered denominator also moved.

Concrete break: a reviewer cannot tell whether `26/50` is a later run, a different filter, or a typo. The warning says not to “correct” 2628/2629, not 48/50.

Fix: timestamp and label the 50-run separately, or make the denominator consistent with §1.2.

VERDICT: NOT CONVERGED
