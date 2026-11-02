Reviewed head: cfdcf659c5ea64271e79ba677812105c360c2217

# PR #463 (backlog #440) — boundary compaction hook — round 1, Claude half

Scope: `git diff origin/master...HEAD` (11 files). Claim under test: *"The hook can never prevent compaction
indefinitely or wedge a session; it fails open on every error path; a blocked call takes no snapshot and an allowed
call takes exactly one; and it defers compaction only while work is genuinely mid-flight."*

**Result: the first three clauses hold under everything I ran. The last clause is refuted by the repository's own
live state: the main checkout's `.claude/executing-plan` is a PAUSED plan armed 2026-10-30 05:16, and the hook
counts any sentinel that exists, so every non-idle auto compaction of the coordinator session is deferred today.**

## What I ran (all foreground)

- `python3 scripts/check-compaction-boundary.py --self-test` → `57/57 self-test cases passed` (0.21 s).
- `main(["--hook"])` driven with a stub snapshot that counts its runs, over four one-line transcripts at W=300000:
  ctx 350k + open Agent + fresh → `block-agent`, **0 snapshots**; ctx 460k → `allow-ceiling`, **1 snapshot**;
  last event 6 min old → `allow-idle`, **1**; no signal → `allow-no-signal`, **1**. Log lines carry the verdict.
- The REAL wrapper `.claude/hooks/compaction-boundary.sh`, copied into a scratch tree whose
  `precompact-snapshot.sh` is a counting stub, with these payloads — every one exited 0 and took exactly one snapshot:
  `not json{`; `[1,2]`; nonexistent `transcript_path`; no `transcript_path`; `"cwd": 5` (Python crashes with
  `TypeError` in `log_path` → wrapper's CANNOT RUN branch → snapshot with no payload); 100,000-deep nested array,
  top level and inside an object; no `trigger`; `trigger: manual`; `CLAUDE_CODE_AUTO_COMPACT_WINDOW=abc` and
  `=2000000`; transcript path that is a directory; stdin held open 5 s (`sleep 5 |`) → returned in **2.09 s**, allowed.
- `.claude/settings.json`: the `manual` matcher is byte-identical to master; only the `auto` entry changed
  (`precompact-snapshot.sh` → `compaction-boundary.sh`, timeout 15 → 20). Worst-case runtime: 2 s stdin + ~0.13 s
  scan of 8 MB (measured below) + 15 s snapshot cap ≈ 17.2 s < 20 s.
- `scan()` over the coordinator's real transcript (`a6abe358…jsonl`, 132 MB, 11,542 assistant records, 241 h span)
  at 152 evenly spaced assistant records, each over its own 8 MB tail, plus one full-file scan to label which open
  calls never close.

## Findings

### F1 — HIGH — BLOCKER — a PAUSED (or another session's) plan sentinel counts as mid-work · not fix-induced

`scripts/check-compaction-boundary.py:323`:

    armed = any((r / ".claude/executing-plan").exists() for r in (checkout, project) if r)

Existence is the whole test. The sentinel has fields the rest of the repo honours — `scripts/begin-plan.py:759`
refuses to advance a plan with `paused:`, and `.claude/hooks/block-idle-stop.sh:35-39,167-169` treats a paused plan
as exit 0 in the common case — and it names its `session:`. This hook reads neither.

**Concrete input, live now:** `/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/executing-plan`,
mtime Oct 30 09:18, fields `armed: 2026-10-30T05:16:54-07:00`, `session: session_01Fqufju9EfJUZ74r5EX25ff`,
`paused: waiting on in-flight work: …`. With this PR merged, every auto compaction of the main session is
`block-plan…` unless the transcript is idle ≥ 5 min or ctx ≥ 450k — for as long as a paused sentinel sits there,
which has been ~2 days. It also reaches OTHER sessions: `project` is `CLAUDE_PROJECT_DIR`, the main checkout, so a
teammate working in a worktree sees the coordinator's sentinel as its own mid-work signal (INFERRED: I could not
observe a teammate's PreCompact environment; my own Bash shell has `CLAUDE_PROJECT_DIR` empty).

This is exactly the "stale sentinel" the backlog row's FAILS-IF names. It does not breach the letter (compaction is
not delayed PAST the ceiling) but it refutes "defers only while work is genuinely mid-flight", and it poisons the
`--summary` measurement the row's cost bound depends on: deferrals logged as `block-plan` would be ordinary
boundaries.

**Fix:** treat a sentinel with a `paused:` field as unarmed, and (for the project-dir copy) require its `session:`
to match the payload's session — or read only the session's own checkout. Add a case for each.
**Siblings searched:** grepped `scripts/*.py` and `.claude/hooks/*.sh` for `paused`: the Stop guard and
`begin-plan.py` both honour it; this file is the only reader of the sentinel that does not.

### F2 — MEDIUM — FILE — the ceiling is not clamped to the model's context limit · not fix-induced

`W_RANGE = (100_000, 1_000_000)` (`:74`) and `CEILING_FACTOR = 1.5` (`:68`) allow a ceiling of 1.5M. The coordinator
transcript's largest observed context is **966,673** tokens, i.e. the model's limit is about 1M. Input run:
`CLAUDE_CODE_AUTO_COMPACT_WINDOW=900000`, ctx 350k, open Agent → `block`, reason "…or at 1350000 tokens". Any
W > ~666k gives a ceiling past the hard limit, so with a persistent signal (F1) and no idle gap the session reaches
the API limit before the hook ever allows. Today's W is 300k (ceiling 450k), so this is latent. The ceiling is also
compared against the LAST assistant usage (`:136`), which excludes the newest tool results, so the real context
at the allowed call can exceed the ceiling by one tool result — harmless at 450k, not at 1M.
**Fix:** cap the ceiling at `min(1.5 × W, L − margin)` with a stated L, or narrow `W_RANGE` to ≤ 600k with that
reason. **Siblings:** none — the ceiling is computed in `decide` and copied into the log record only.

### F3 — MEDIUM — FILE — a lost Agent notification holds the `agent` signal for the whole 8 MB tail (~15 h) · not fix-induced

Measured on the full transcript: **253 Agent calls, 9 never closed** — 3 of them are running right now (`build-438`,
`merge-458`, and this review), so **6 genuinely lost** over 2026-10-28…11-01 (e.g. `r1-382-claude`, `build-407`,
`fold-452-cap`); the builder's 11/243 is the same order. I checked `r1-382-claude`: its teammate never sent
`idle_notification`; a later `ListAgents` row shows it `running` — a stalled agent, not a parsing miss.
The 8 MB tail spans **04:00–18:44 today (≈14.7 h)**, so a lost agent pins `agent` for ~15 h. At the 152 sampled
points: 60 no signal, 69 a live signal, **23 only never-closed signals** (7 involve an agent).

**Sizing the "ceiling is the usual path" risk** — it is NOT the usual path, because idle releases first. Splitting
the transcript at gaps ≥ 5 min between assistant records gives 370 busy stretches: median context growth **8.4k**,
p90 **44.6k**, only **14 of 370 (3.8%)** grow ≥ 150k (the W→1.5W headroom). So a deferral under a stale signal
usually ends at the next idle gap, costing ~0.1 × (a few k to ~45k) per deferred call, and reaches the ceiling in
a small minority of stretches. ⚠ That is per stretch, not per compaction: a stretch that crosses W early is
over-represented among long ones, so the ceiling share of compactions will be higher than 3.8% — the `--summary`
log is the right instrument, provided F1 is fixed first so its `block-plan` rows mean something.
**Proposed bound (cheap):** an open background agent or teammate older than ~3 h stops counting (`build-438`, the
longest live one today, is ~1.2 h). **Siblings:** monitors are already bounded by their own expiry (below).

### F4 — LOW — FILE — monitors that finish without a `<status>` count as open until their 30-minute expiry

**138 Monitor calls, 96 never received a `<status>`**; all 96 have the 30-min expiry, so `signals` drops them at
`expires` (`:181`). 16 of the 23 stale-only samples above are these. Bounded at 30 min, so only noise in the log.

### F5 — LOW — FILE — NOT MEASURED — the 5-minute idle threshold may be longer than the harness's idle compaction

The study's own row (`compaction-study/report.md:12`) quotes the notice "Compacted while idle, **before the prompt
cache expired**". If a session's cache TTL is 5 min, idle compaction fires with the last event < 5 min old, so with
any signal present it is blocked — FAILS-IF clause 2. This transcript's "idle > 60 min rewrites" (report `:55`)
suggests a 1 h TTL here, which makes the 300 s rule safe; the dependence on TTL is not stated in the docstring.
**Fix:** say it in the docstring (the threshold must be below the idle-compaction delay), or check a TTL source.

### F6 — LOW — FILE — `log_path` is not covered by `evaluate`'s fail-open, so a malformed `cwd` loses the log line

`"cwd": 5` → `TypeError` at `:336` (`Path(int)`; only `ValueError, AttributeError` caught) → the Python process exits
1, the wrapper's CANNOT RUN branch runs the snapshot without a payload. Compaction is still allowed; only the log
line and the snapshot's payload are lost. **Siblings:** `checkout_of(Path(payload.get("cwd") or "."))` at `:312` has
the same shape but is inside `evaluate`'s `except Exception`.

## Claim, clause by clause

| Clause | Verdict |
|---|---|
| never prevents compaction indefinitely / wedges | holds at W=300k; F2 is the one way past the hard limit |
| fails open on every error path | holds — 14 crafted inputs, all exit 0 + allow (F6 via the wrapper) |
| blocked → 0 snapshots, allowed → exactly 1 | holds — counted with a stub |
| defers only while work is genuinely mid-flight | **refuted — F1 (live paused sentinel), F3 (lost agents)** |

VERDICT: NOT CONVERGED
