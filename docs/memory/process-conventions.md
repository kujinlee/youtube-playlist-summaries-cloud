---
name: process-conventions
description: "FIRES-WHEN: about to commit, push, merge, or treat a spec as approved — The standing process rules: branch + PR for EVERY change incl. docs (merge when READY), spec = human gate with plan+impl autonomous, ephemeral task ticks in-convo with a durable file at milestones, and a resume that reads git + files + the RUNNING SYSTEM"
metadata:
  type: feedback
---

> Merged 4 memories. Former names (still referenced by other memories): `branch-pr-standard-practice`, `afk-workflow-gate-boundary`, `task-tracking-convention`, `context-compaction-protocol`

## The rules (current)

1. **Branch + PR for EVERY change, docs included.** Branch before the first commit. Direct commit to `master` only
   when there is no remote. Docs PRs are batched; roadmap/backlog ticks ride in the PR they describe.
   **Merge when READY** — `check-merge-ready.py --pr N` READY ⇒ squash; HOLD ⇒ verify it, real ⇒ owner
   ([[push-is-mine-merging-is-theirs]] holds the full rule). Push needs no permission.
2. **The spec is the human gate; plan + implementation run autonomously** ("Conditional AFK", `docs/dev-process.md`
   → Human-in-the-Loop Policy). Dual adversarial review to convergence (or the round cap) replaces human approval of
   the plan. Pull the human in only for an unexpected situation: a fork the spec did not settle, a blocker, anything
   that moves the goal, or an outward-facing/irreversible step (deploy, delete, spend, a HOLD).
3. **Notify when I actually need the human** — `PushNotification`, one line, decision first. Never "wait" silently;
   never notify routine progress.
4. **Task ticks are ephemeral; the durable file is edited only at boundaries** (a group completes, a merge, a
   milestone flip) — `docs/roadmap-to-launch.md` and similar. No file edit per checkbox.
5. **Session resume reads THREE things: `git log`, the files, and the RUNNING SYSTEM** — `supabase migration list
   --linked`, `fly status` / `fly releases`, and `guardrail_config` via the read-only `claude_ro` role (commands in
   [[launch-roadmap-state]]). Before trusting any document's claim about prod. **"Merged" is not "deployed".**
6. **Record any out-of-band external change durably the moment it happens** (ad-hoc prod SQL, dashboard toggles,
   `fly secrets`) — better, do it through a tracked mechanism (migration, script). Before signalling 🟢
   SAFE-TO-COMPACT, ask whether anything touched external state unrecorded.

**Why:** a docs commit to the default branch is still an unreviewed push, and it is the habit that erodes. Dual review
can verify correctness but structurally cannot judge whether the INTENT is what the user wants — that is concentrated
in the spec. Git is truth for code and blind to live infra; a rule that fires at mutation time depends on remembering,
so the live read belongs in the reconcile.

**How to apply:**
- Committed on local `master` by mistake and unpushed: `git branch <name>`, `git reset --hard origin/master`,
  `git checkout <name>`, push the branch.
- Pass `--repo kujinlee/youtube-playlist-summaries-cloud` to `gh pr` ([[gh-two-remotes-footgun]] — PR numbers
  collide across the two remotes). Long bodies via `--body-file`, never a heredoc in `$(...)`.
- Compaction: their external monitor shows ctx%; I cannot read my own context fill. My part is a 🟢 SAFE-TO-COMPACT
  at task boundaries — durable state is in the ledger `.superpowers/sdd/progress.md`, git, and `docs/reviews/`.

## History

- **2026-07-12:** Conditional AFK codified ([[stage-1d-merged-followups]]); at that time push/merge/deploy were all human gates. Push was removed
  2026-09-30; merge became merge-when-READY on 2026-10-25 (re-stated 11-06). This file said "never merge" until the
  2026-11-14 audit. Same day: the user flagged I waited at a gate without pinging their phone.
- **2026-07-22:** two-layer task tracking agreed. At that time TodoWrite/TaskCreate were absent from this user's
  sessions because `remoteControlAtStartup: true` ran them through the remote-control bridge; the user chose to keep
  remote control on. (`docs/dev-process.md` now lists `TaskCreate`/`TaskUpdate` as Phase 3 tools.)
- **2026-07-23:** the user ran `update guardrail_config set daily_cap_cents=5000` on prod; the roadmap still said 500
  and a later session nearly recorded the wrong value.
- **2026-07-30:** I committed three commits (a review doc, a process change, `lib/storage/testing/in-memory-blob-store.ts`)
  directly to local `master`, reasoning from docs-commit precedent. The user set branch + PR for every change.
- **2026-08-11:** it happened again in a different system — prod sat at migration `0022` while the roadmap claimed
  `0021`, and `0023` (merged 2026-08-03) had never been applied; prod ran without it for eight days. Caught by a
  routine LIVE READ at session start, which became rule 5. A slice split across code and migrations is not shipped
  until BOTH halves land.
