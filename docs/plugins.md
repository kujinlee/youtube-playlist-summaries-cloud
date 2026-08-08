# Plugin Governance

Canonical source for plugin requirements, skill conflict resolution, fallbacks, and cleanup.
Lives in the project repo so the full workflow is reproducible by anyone who clones it.

> **Quick reference:** [`docs/available-skills.md`](available-skills.md) lists every skill, agent,
> and command currently installed — with invoke strings, trigger type, and descriptions.
> Regenerate it after any plugin change: `python3 scripts/regen-skills-doc.py`
> — or just say **"sync docs"** / run `/sync-docs` to let the `sync-docs` skill handle it.

---

## Required Plugins

Install these before starting work on this project.

| Plugin | Install command | Purpose |
|---|---|---|
| `superpowers` | `/plugin install superpowers@claude-plugins-official` | Core workflow skills (brainstorming, TDD, debugging, code review, plans) |
| `mattpocock/skills` | `npx skills@latest add mattpocock/skills` | TDD (discovery mode), diagnose, grill-with-docs, handoff |
| `codex` | Install Codex CLI + `/plugin install codex@openai-codex` | Adversarial review gate at every phase |
| `remember` | `/plugin install remember@claude-plugins-official` | Session continuity across compaction and context resets |

### Optional (used in later phases)

| Plugin | Install command | Purpose |
|---|---|---|
| `playwright` | `/plugin install playwright@claude-plugins-official` | E2E tests (Sub-project 2, Task 7) |
| `pr-review-toolkit` | `/plugin install pr-review-toolkit@claude-plugins-official` | Pre-PR review gate |
| `hookify` | `/plugin install hookify@claude-plugins-official` | Hook configuration management |

---

## Skill Conflict Resolution

When multiple installed skills can handle the same task, use this table.

### TDD

| When | Use | Requires |
|---|---|---|
| Behaviors fully specified upfront (lib functions, components with clear acceptance criteria) | `superpowers:test-driven-development` | superpowers |
| Behavior discovered during implementation (pipelines, API routes, page wiring) | `mattpocock:tdd` | mattpocock/skills |

**Fallback** (mattpocock not installed): use `superpowers:test-driven-development` for all TDD.

### Debugging

| When | Use | Requires |
|---|---|---|
| Clear feedback loop exists: test failure, stack trace, consistent repro, build error | `superpowers:systematic-debugging` | superpowers |
| Building a feedback loop is the hard problem: flaky, prod-only, perf regression, no local repro | `mattpocock:diagnose` | mattpocock/skills |

**Fallback** (mattpocock not installed): use `superpowers:systematic-debugging` for all debugging; add manual repro steps before analysis.

### Writing Skills

| When | Use | Requires |
|---|---|---|
| Creating or editing any Claude Code skill for this project or ecosystem | `superpowers:writing-skills` | superpowers |
| Contributing a skill back to mattpocock's own repo | `mattpocock:write-a-skill` | mattpocock/skills |

**Fallback** (superpowers not installed): use `mattpocock:write-a-skill` as a structural guide only; adapt output to local plugin infrastructure.

### Session Handoff

| When | Use | Requires |
|---|---|---|
| End of session — continuity for next session | `remember:remember` → writes `.remember/now.md` | remember |
| Mid-task agent handoff — passing work to a subagent | `mattpocock:handoff` → temp file with artifact references | mattpocock/skills |

**Fallback** (remember not installed): write a brief handoff note to `.handoff.md` in project root; delete after resuming.

### Code Review (dual review per task)

Both must complete before marking a task done.

| Review | Use | Requires |
|---|---|---|
| Claude code review | `superpowers:requesting-code-review` | superpowers |
| Adversarial review | `codex:rescue` | codex |

**Codex model — resolve the current frontier dynamically, never hard-code a version.**
OpenAI rotates frontier model names (gpt-5.3 → gpt-5.4 → gpt-5.5 → …) and removes old ones
from the ChatGPT-account (OAuth) auth path. The codex CLI leaves `--model` unset by default and
falls back to a slug baked into the binary, which can be a removed model → HTTP 400. So the
adversarial review must select whatever OpenAI currently ships as frontier:

```bash
# Prints the current frontier slug from the live ~/.codex/models_cache.json (lowest priority).
python3 scripts/codex-frontier-model.py            # e.g. gpt-5.5 today
python3 scripts/codex-frontier-model.py --write-config   # also syncs ~/.codex/config.toml
```

Run `--write-config` to keep `~/.codex/config.toml`'s `model` in sync (it writes a managed,
auto-derived block — do not hand-edit the slug). When dispatching the Codex review you may also
pass it explicitly: `codex … -m "$(python3 scripts/codex-frontier-model.py)"`. Either way the
model is derived from OpenAI's live model list, so it tracks new frontier releases automatically.

**Fallback — Codex unavailable for ANY reason → never block; auto-fall back to a Claude adversarial review.**
"Unavailable" covers: not installed, **usage/rate limit hit**, auth failure, HTTP 400/5xx, a hung or
timed-out run (e.g. a `task` that starts a turn but emits no findings), or any other error. The rule
(set 2026-06-20): **do not wait, pause the phase, or burn time retrying** — immediately run a rigorous
**Claude** adversarial review in Codex's place (a fresh subagent with full file access and an explicit
adversarial mandate), save it to the normal `docs/reviews/...-review.md` path, and **note the Codex gap
in the review doc** so the Codex-specific pass can be re-attempted before merge if/when access returns.
One quick check (frontier model sync via `scripts/codex-frontier-model.py --write-config`, a single
re-run) is fine; beyond that, fall back. The Claude adversarial review satisfies the gate for proceeding.

**USE `scripts/codex-review.py` — it makes failure-mode 1 below impossible (added 2026-07-19).**

```bash
# PREFERRED — always for a real review prompt. See the backtick footgun below.
python3 scripts/codex-review.py --prompt-file <path> --out docs/reviews/task-N-<name>-codex.md
#   exit 0 = a real review was written    exit 1 = the gate did NOT run → fall back to Claude
```

**Pass the prompt in a FILE, not as a shell argument (added 2026-08-04).** A review prompt is full of
identifiers, and any **backtick** inside a double-quoted bash string is **command substitution** — the
shell silently rewrites the prompt before Codex ever sees it. Measured 2026-08-04: a round-3 prompt
containing `` `key` `` produced `bash: key: command not found`, the prompt arrived mangled, and no
review was written. `--prompt-file` avoids the shell entirely.

This is the **same root cause** as the `gh --body-file` rule in `docs/dev-process.md` Phase 5, and it
is not a `gh` problem — it applies to **every** double-quoted bash string, including
`git commit -m "$(cat <<'EOF' …)"`, which broke on an apostrophe in the same session. The general rule:
**anything longer than a line goes in a file** (`--prompt-file`, `--body-file`, `git commit -F`).

The wrapper behaved correctly here and that is the point: it refused to write a review file rather than
writing an empty one, so the mangled run failed **loud**. A caller checking only the exit code of a raw
`codex exec` would have recorded a completed gate.

It walks every candidate model in priority order, and decides success **solely** by whether
`codex exec -o/--output-last-message` wrote a substantive final-message file — never the exit code,
never stdout text. Run `--self-test` (15 cases) after touching it. Prefer it over raw `codex exec`
for anything that must actually produce a review; `scripts/codex-frontier-model.py` alone cannot
guarantee a runnable model and says so in its docstring.

**THERE ARE TWO SANDBOXES, AND DISABLING THE OUTER ONE DOES NOTHING TO THE INNER ONE (added 2026-08-07).**

| Layer | Controlled by | What it governs |
|---|---|---|
| Outer | Claude Code's `dangerouslyDisableSandbox` on the Bash call | whether *we* may launch the process |
| **Inner** | **`codex exec -s <mode>`**, default `workspace-write` | what **Codex** may do to the machine |

MEASURED in round 7 of the blob-addressing review: the wrapper passed no `-s`, so Codex sandboxed
*itself*, could not open the Docker socket
(`dial unix …/docker.sock: connect: operation not permitted`), and reported
`0/35 mutations … SQL did not run`. It reviewed by **reading**. Its findings happened to be right,
but the whole reason that artifact was moved out of prose into executable SQL is that reading is the
most expensive way to find defects — **a reviewer that cannot execute is a downgraded gate that still
reports success.** Note the shape: this is the *same class* as the fail-open cases below, one layer
out, and the existing memory note ("run Codex from the coordinator with `dangerouslyDisableSandbox`")
covered the **outer** sandbox only — solving one instance and reading as if it covered the class.

`scripts/codex-review.py` now passes `-s danger-full-access`. `trust_level = "trusted"` in
`~/.codex/config.toml` does **not** substitute — it governs approval prompts, not socket access — and
no narrower mode works, because the verifier needs a unix socket outside every workspace root.
If a review ever reports that it could not run the suite, **treat the gate as not having run.**

**The gate can FAIL OPEN — verify it actually ran (added 2026-07-18).**

1. **Wrong model slug → HTTP 400, empty review. ✅ SOLVED by the wrapper above.**
   `scripts/codex-frontier-model.py` ranks by `priority` without filtering on what the pinned CLI
   supports — it cannot, as the cache has no minimum-client-version field (re-verified 2026-07-19
   across every key of all 7 cached models). It still returns `gpt-5.6-sol`, which CLI 0.142.5
   rejects with *"requires a newer version of Codex"*. The wrapper now falls through
   `gpt-5.6-sol → -terra → -luna → gpt-5.5` automatically.
   **Correction to what this doc previously claimed:** it said such runs exit **0**. Measured
   2026-07-19 — a direct `codex exec` exits **1**. The exit-0 report comes from the plugin's
   background-task path, not the CLI. Because the two disagree, trust *neither* as proof of success:
   **read the output FILE.** A review doc with no findings section is a failed run, not a clean
   review. (Manual fallback if you bypass the wrapper: `codex exec -m gpt-5.5`.)
2. **A confident but wrong CONVERGED.** The fallback rule handles an *absent* reviewer; nothing handles
   a reviewer that completes successfully and clears a live defect. In Stage 3 cloud-sync this happened
   **twice** — see "Reviewer disagreement is the signal" in `docs/dev-process.md`. Never treat a single
   CONVERGED as proof; ask what that reviewer would have had to check to find the class of bug you most
   fear, and prefer the reviewer that reports a finding until you have traced the code yourself.

**Bounded wait — never passively wait on a background review.** When a Codex review is dispatched in
the background, do NOT report "waiting on Codex" across turns or trust the completion ping (it can be
bogus). Within ~2–3 minutes, **read the actual Codex task output file** (`.../tasks/<bgId>.output`).
Treat as a hang → fall back immediately if: the file shows only `Thread ready` / `Turn started` with
no findings, it hasn't grown, the run reports a usage limit / auth / HTTP error, or no output exists.
The default posture is *make progress*, not *wait* — a Claude adversarial review is always available.

### Domain Terminology Stress-Test (Phase 1)

| When | Use | Requires |
|---|---|---|
| After brainstorming spec, before Codex review | `mattpocock:grill-with-docs` | mattpocock/skills |

**Fallback** (mattpocock not installed): use `superpowers:brainstorming` for a second pass with explicit instruction to challenge terminology and surface contradictions.

---

## Cleanup (Optional — Confirm with User Before Proceeding)

The following plugins were installed for this project's workflow and may not be needed on other projects. Ask the user before uninstalling — they may want to keep them globally.

| Plugin | Reason installed | General-purpose? |
|---|---|---|
| `mattpocock/skills` | TDD discovery mode, diagnose, grill-with-docs, handoff | Partially — useful for other projects too |
| `codex` | Adversarial review gate | Yes — useful for any project |

Plugins that are clearly general-purpose and should be kept regardless:
`superpowers`, `remember`, `playwright`, `pr-review-toolkit`, `hookify`

### Uninstall commands (if user confirms)

```bash
# mattpocock/skills (installed via npx, not /plugin)
npx skills@latest remove mattpocock/skills

# codex — uninstall via Claude Code plugin manager
```
