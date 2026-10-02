---
name: process-conventions
description: "FIRES-WHEN: about to commit, push, merge, or treat a spec as approved — The standing process rules: branch + PR for EVERY change incl. docs (merging stays a human gate), spec = human gate with plan+impl autonomous, ephemeral task ticks in-convo with a durable file at milestones, and a resume that reads git + files + the RUNNING SYSTEM"
metadata:
  type: feedback
---

> Merged 4 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `branch-pr-standard-practice`, `afk-workflow-gate-boundary`, `task-tracking-convention`, `context-compaction-protocol`

## branch pr standard practice

**Branch + PR is the standard path for EVERY change, docs included.** Work on
`feat/…`, `fix/…` or `chore/…`, push the branch, open a PR, let the human merge.
Committing straight to `master` is the **exception, allowed only when there is no
remote** (`git remote` empty — a PR is impossible there).

**Why:** set by the user 2026-07-30 after I committed three commits (a review doc, a
process change, and a new `lib/storage/testing/in-memory-blob-store.ts` module) directly
to `master` locally, reasoning that docs commits had precedent on this repo. The user's
rule is that "docs-only" is not an exemption — a docs commit to the default branch is
still an unreviewed push, and it is the *habit* that erodes, not the individual commit.
Do not infer "direct to master is fine here" from `git log` showing past direct commits.

**How to apply:**
- Default to a branch before the first commit, not after. If work is already committed on
  `master` locally and unpushed: `git branch <name>` at HEAD, `git reset --hard
  origin/master`, `git checkout <name>`, push the branch. Nothing is lost while unpushed.
- **Merging stays a human gate** — open the PR and notify; never merge.
- Always pass `--repo kujinlee/youtube-playlist-summaries-cloud` to `gh pr` commands
  (see [[gh-two-remotes-footgun]] — PR numbers collide across the two remotes).
- `gh pr create --body "$(cat <<'EOF' … EOF)"` breaks on apostrophes/backticks in the
  body. Write the body to a scratchpad file and use `--body-file`.

Recorded in the repo at `docs/dev-process.md` Phase 5. Related:
[[process-conventions]] (push/merge are human gates regardless).

## afk workflow gate boundary

For AFK/autonomous work under the gate-based dev process, the CRUCIAL human gate that must NOT be skipped is the **spec/design phase**: terminology review (grill-with-docs) and design/intent choices require live human interaction. Once the spec is fixed (human-approved), the **plan and implementation phases can run fully automated (AFK)**, with dual adversarial review (Codex + Claude) substituting for the human approval gates.

**Why:** dual adversarial review reliably substitutes for correctness / completeness / safety verification, but structurally CANNOT judge whether the stated *intent* is what the user actually wants — that intent/terminology/design judgment is the irreplaceable human contribution, and it is concentrated in the spec phase. Correctness lives in plan+impl, where adversarial review suffices.

**How to apply:** keep the human in the loop for grill-with-docs + spec design choices; after spec approval, automate writing-plans + adversarial plan review + SDD implementation without parking for approval — surface only a genuinely NEW intent/scope fork if one arises. See [[dev-process]] and [[stage-1d-merged-followups]].

**Refined 2026-07-12 → "Conditional AFK" (now codified in docs/dev-process.md `## Human-in-the-Loop Policy`).** The plan gate is **convergence of dual review, NOT a human ack** — do NOT stop at the Post-Plan Gate for approval when review converged (0 new Blocking/High) and no goal-affecting ambiguity. Pull the human in ONLY for an *unexpected situation*: non-convergence, a genuine spec-unsettled fork, a blocker (access/deps/red gate), anything that would move the goal, or an outward-facing/irreversible step (push/merge/deploy — always a human gate). User's framing: once the goal (spec) is fixed, plan+impl are trial-and-error toward it and human intervention there rarely changes the outcome.

**Notification is mandatory when you actually need the human.** Use `PushNotification` (pushes to phone if Remote Control connected) at a real human gate — an unexpected situation, or a long autonomous run completed and only the merge gate remains. One line, lead with the decision needed. Silently "waiting" without notifying wastes the user's time (they never saw the request). Do NOT notify for routine progress. (2026-07-12: user flagged that I waited at a gate without pinging their phone — fix going forward.)

## task tracking convention

Two-layer task tracking, confirmed with user 2026-07-22:

- **High-frequency checkmarks → ephemeral.** Individual item ticks are tracked in-conversation
  (or via TodoWrite in a plain terminal session), NOT written to a file each flip. The user
  dislikes file churn on every checkmark.
- **Durable file → updated only at BOUNDARIES.** A milestone/checklist `.md` (e.g.
  `docs/m1.4-finishup-checklist.md`, or `docs/roadmap-to-launch.md`) is edited only when a whole
  group completes, at a merge, or at a milestone flip — never per single item.
- **On `/clear` / session start → reconcile from git + roadmap + files** (ground truth). The user
  explicitly likes this practice; it's what makes the ephemeral layer safe to throw away.

**Why:** ephemeral list = fast cache (cheap, lost on restart); durable file = backing store (rebuilt
into a fresh cache each session via git reconcile). Separating them resolves the tension between
"don't edit files every checkmark" and "keep it durable."

**How to apply:** when tracking multi-item work, tick items inline as you go; only write to the
durable file at a group/milestone boundary. Don't create a file edit per checkbox.

**TodoWrite/TaskCreate note:** these are BUILT-IN Claude Code tools (not installable plugins), on by
default in a normal foreground terminal session. They are ABSENT in this user's sessions because
`~/.claude/settings.json` has `remoteControlAtStartup: true` → sessions run through the remote-control
bridge (phone notifications, voice), whose tool profile omits the interactive todo panel. User chose
(2026-07-22) to KEEP remote control on and use the file-at-boundaries rule rather than disable it.
Don't re-litigate; don't try to "install" TodoWrite. Related: [[launch-roadmap-state]],
[[process-conventions]].

## context compaction protocol

The user manually monitors context size to avoid context rot / performance degradation, via an EXTERNAL ntfy monitor that pushes lines like `[ctx:39%] [386k/1000k] [$170.04*] [Opus 4.8]`. That monitor is a statusline/hook reading the session transcript token count — it runs OUTSIDE my tool sandbox. **I cannot read my own live context-window fill** (no tool returns it) and cannot subscribe to their ntfy topic. Be honest about this limitation; don't pretend to see the number.

**What I CAN do — and the protocol the user wants:** tell them when it is **SAFE TO COMPACT.** Their monitor supplies the number; I supply the state. Division of labor: their monitor = ctx%; my 🟢 = all-clear; user = triggers the compact.

**Why compaction is low-risk in the SDD workflow:** all durable state lives in FILES, not just my context — the ledger `.superpowers/sdd/progress.md`, git commits, per-task briefs/reports `.superpowers/sdd/task-N-*.md`, review docs `docs/reviews/`. On resume I re-read the ledger + `git log`. So a compaction at a task boundary loses nothing. **How to apply:** during a long autonomous run, `PushNotification` a **🟢 SAFE-TO-COMPACT — Task N done** at each task boundary (review converged, ledger+commits written) — that cadence also tracks context growth (each task absorbs an implementer report + 2 reviews). When their ctx% alarm crosses ~50%, they wait for the latest 🟢 then compact. Boundaries are cleanest; mid-task is still fairly safe because reports are files. See [[process-conventions]] (PushNotification is the same channel used for real human gates).

**CRITICAL CAVEAT (learned 2026-07-23 — a real miss):** "safe to compact" is TRUE ONLY IF every
state-changing action since the last checkpoint is durably recorded. The session-start reconcile reads
**git + roadmap + files — NOT live external state.** So any **out-of-band mutation of an external
system leaves NO durable footprint and IS lost on compaction**: ad-hoc SQL against prod (e.g. the user
ran `update guardrail_config set daily_cap_cents=5000` directly on prod — the roadmap still said 500,
and a later session "forgot" it and nearly recorded the wrong value), Supabase-dashboard toggles,
`fly secrets`, OAuth/provider settings changed by hand. **Rules:** (1) the moment an out-of-band
external change happens, WRITE IT DOWN durably (roadmap + memory) — or better, do it through a TRACKED
mechanism (a migration `00NN`, a script, a runbook step) so it lands in git and is auditable; (2) never
trust a doc's number for a money/prod value without a live read — VERIFY against the running system;
(3) before signalling 🟢 SAFE-TO-COMPACT, ask "did anything since the last checkpoint touch external
state without recording it?" — if yes, record first. Git is truth for CODE; it is blind to live infra
state. See [[process-conventions]] (durable-file discipline).

**⟳ IT HAPPENED AGAIN 2026-08-11, AND THE RULE ABOVE DID NOT PREVENT IT — so the rule is the wrong
shape.** Measured: prod sat at migration `0022` while `docs/roadmap-to-launch.md` claimed `0021`, and
`0023` (the serial-coherence fix, merged 2026-08-03) had **never been applied** — prod ran without it
for eight days while every document read "merged, done". Note this is the *same class* as the
`daily_cap_cents` miss above, in a *different* external system, three weeks after the lesson was
written down.

**Why the rule failed: every clause of it fires at MUTATION time and depends on remembering.** That
is exactly the *"a rule that depends on remembering"* shape this project keeps trying to remove (cf.
backlog #29). Nobody is present to run clause (1) when the thing that happens is "a past session
pushed a migration and moved on".

**What actually caught it was a routine LIVE READ during session-start reconcile** — a step with no
suspicion attached, run before anything was believed. So the durable fix is to make reading live
state part of the **reconcile**, not part of the mutation:

> **Session Resume reads THREE things, not two: `git log`, the files, and the RUNNING SYSTEM.**
> Cheap and read-only: `supabase migration list --linked` (schema level), `fly status` /
> `fly releases` (deployed version), and `guardrail_config` via the read-only `claude_ro` role. Do
> this *before* trusting any document's claim about prod. See [[launch-roadmap-state]] for the exact
> commands, including the `docker run postgres:16` psql workaround.

**Corollary worth its own sentence: "merged" is not "deployed", and a slice split across code and
migrations is not shipped until BOTH halves land.** #46's serve-path fix bounds the reserve in
TypeScript and makes settle observable in SQL; shipping only the app half would have been strictly
worse than shipping neither.

