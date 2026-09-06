<!-- codex-review: model=gpt-5.5 -->

**Findings**

**Blocking** — `armed` is not the same as “plan currently obligates banners”; paused plans will false-positive.

Evidence: `check-plan-progress.py` explicitly stands down a named plan before reading steps:

```python
if "paused" in fields:
    return ALLOW, "", None
```

[scripts/check-plan-progress.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-progress.py:99)

`begin-plan.py --pause` writes that state:

```python
SENTINEL.write_text(SENTINEL.read_text().rstrip("\n") + f"\npaused: {why.strip()}\n")
```

[scripts/begin-plan.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/begin-plan.py:369)

Concrete false positive: plan is paused with `paused: waiting on CI`; user asks for a one-line backlog typo fix; assistant edits `docs/backlog.md`; no step banner is required because the active plan is deliberately paused. Spec predicate fires: `armed AND unticked>0 AND edited AND zero banners`.

Smallest fix: replace boolean `armed` with parsed sentinel state: `active = plan named AND "paused" not in sentinel fields`; the inverse warning may only use `active`.

---

**Blocking** — `unticked == 0` is not the only quiet condition; `total == 0` is `CANNOT RUN`, but the spec would classify it as finished.

Evidence: `count_steps()` returns `(done, total)`:

```python
marks = _STEP_RE.findall(plan_text)
return sum(1 for m in marks if m == "x"), len(marks)
```

[scripts/check-plan-progress.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-progress.py:71)

The owning guard treats zero parsed steps as failure, not “done”:

```python
if total == 0:
    return BLOCK, (
        f"CANNOT RUN: parsed ZERO step checkboxes from `{plan}`. Either the plan's shape "
```

[scripts/check-plan-progress.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-progress.py:112)

The spec’s F3 says:

```text
armed · unticked == 0 · edited · zero banners | QUIET — the plan is finished
```

[docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md:161)

Concrete false negative: sentinel names a malformed plan with no `- [ ]` / `- [x]` lines, assistant edits a repo file, no banner. `count_steps()` gives `(0, 0)`, spec sees `unticked == 0`, stays quiet. The existing stop guard says this is `CANNOT RUN`.

Smallest fix: import or duplicate the owning decision shape: `total == 0 -> CANNOT_RUN`; only compute `unticked = total - done` after that.

---

**High** — “edited a file inside repo root” is too broad and will cry wolf on ignored/session/generated files.

Evidence: the repo deliberately contains session-local state under the repo root:

```gitignore
.claude/executing-plan
.claude/executing-plan.state
.claude/plans/
.claude/banner-warnings.log
.claude/ci-watching
```

[.gitignore](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.gitignore:86)

The spec rejects git-tracked and chooses:

```text
Path inside the repo root; no git call
```

[docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md:57)

Concrete false positive: plan is active, assistant writes `.claude/ci-watching` or `.claude/plans/scratch.md` via `Write`, emits no banner because it is arming/recording harness state, not executing a user-visible step. Predicate fires because the path is inside `ROOT`.

Smallest fix: define a tracked-work predicate, not a root predicate: at minimum exclude `.git/`, `.claude/executing-plan*`, `.claude/plans/`, `.claude/banner-warnings.log`, `.claude/ci-watching`, build outputs, and other ignored runtime artifacts; better, pass in a precomputed `plan_work_edit` with explicit allow/exclude tests.

---

**High** — the proposed tool set misses realistic edit tools, so the measured failure can still stay quiet.

Evidence: the spec only scans:

```text
any `Edit` / `Write` / `NotebookEdit` tool use
```

[docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md:125)

The current settings already treat only `Edit|Write` as post-edit hooks:

```json
"matcher": "Edit|Write"
```

[.claude/settings.json](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/settings.json:52)

Concrete false negatives: `MultiEdit` changes three files in one operation; or a plan step runs `python - <<'PY'` / `perl -pi` / `git apply` through `Bash`. No `Edit`/`Write`/`NotebookEdit` block exists, so `edited == false`; active plan, unticked steps, zero banners stays quiet. The spec admits Bash but not `MultiEdit`, and the admitted list is incomplete.

Smallest fix: include every file-mutating tool the runtime exposes, especially `MultiEdit`, and state Bash/subagent mutation as an explicit blind spot with a falsifier proving it stays quiet by design.

---

**High** — the transcript window does not mean the same thing for tool use as for assistant text.

Evidence: the existing window is built around visible assistant text and has one special case:

```python
if rec.get("type") != "user":
    continue
if _is_tool_result(rec):
    continue
start = i + 1
```

[scripts/check-banner-armed.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:92)

The spec says the same records should feed tool scanning:

```text
`records_since_last_user(lines) -> list[dict] | None` — the window
...
`edited_paths_of(records, root) -> list[str]` — the new extractor.
```

[docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md:139)

Concrete false negative: the main turn dispatches an `Agent`/subagent that edits repo files as the plan work and returns; main transcript contains the dispatch/result, not the subagent’s internal `Edit`. The current project already documents this class of invisibility:

```text
Subagent activity is not in these transcripts (no isSidechain records exist)
```

[scripts/skill-usage-audit.py output cited in docs/backlog.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/backlog.md:33)

Smallest fix: specify whether subagent work is in or out. If in, the detector needs a source beyond the main transcript. If out, §8 must name it.

---

**Medium** — the import precedent is cited too narrowly; `count_steps()` alone is not the owner of “work left”.

Evidence: `begin-plan.py` borrows three names, not just `count_steps`:

```python
missing = [n for n in ("count_steps", "next_pending_task", "parse_sentinel")
           if not hasattr(mod, n)]
```

[scripts/begin-plan.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/begin-plan.py:104)

The owning stop predicate depends on sentinel parsing and pause before count:

```python
fields = parse_sentinel(sentinel_text)
if "paused" in fields:
    return ALLOW, "", None
```

[scripts/check-plan-progress.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-progress.py:99)

There is no import cycle today: `check-plan-progress.py` imports only stdlib and does not import `check-banner-armed.py`. The cost is not runtime I/O from import. The coupling that bites is semantic: importing only `count_steps()` gives a different definition of “plan still active” than the guard that owns stopping.

Smallest fix: borrow `parse_sentinel` too, or expose a small `plan_state(sentinel_text, plan_text)` helper from `check-plan-progress.py` that returns `paused`, `cannot_run`, `unticked`.

---

**Medium** — the path test is underspecified and wrong at repo boundaries.

Evidence: the spec simultaneously says the pure predicate is “a string comparison passed in”:

```text
the predicate is a string comparison passed in, not I/O performed inside a function
```

[docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md:74)

and says file paths “resolve inside `ROOT`”:

```text
carries a file path that resolves inside `ROOT`
```

[docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md:125)

Concrete failures:
- Symlink under repo to outside: syntactic inside-root passes if implemented by prefix, but the mutation is outside.
- Symlink outside to repo: resolved path inside-root fires even though the visible tool path was a scratchpad path.
- `.git/` writes: inside root but not plan work.
- Case-insensitive macOS: `/users/...` and `/Users/...` can name the same tree but fail naive string/`relative_to` comparisons on non-existing paths.
- Worktrees: `.git` may be a file pointing outside the root; “inside root” does not mean “inside repository metadata” or “tracked worktree file”.

Smallest fix: write the path predicate as a separate pure helper with self-tests for symlink, traversal, `.git`, ignored paths, absolute/relative paths, and macOS case normalization assumptions. Do not leave it as prose.

---

**Medium** — several falsifiers are vacuous against the current unfixed code.

Evidence: current `decide()` returns quiet before `armed` is consulted:

```python
banner = highest_banner(texts)
if banner is None:
    return QUIET, ""
```

[scripts/check-banner-armed.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:147)

Therefore F2, F3, F4, and F5 all pass against unfixed code for the same reason: zero banners always returns `QUIET`, regardless of `armed`, `unticked`, or `edited`. F7 also passes against unfixed code because the existing branch already says:

```python
if armed:
    return QUIET, ""
```

[scripts/check-banner-armed.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:154)

F6 only becomes meaningful if the implementation actually plumbs unreadable-plan state into `decide()`; as written, the existing function has no `unticked` input and cannot observe it.

Smallest fix: make F1 the red test against current code; make the rest mutation/control tests tied to named branches, not advertised as falsifiers of the unfixed defect. Add one explicit anti-vacuity check that stubs/removes `edited_paths_of` or the new `banner is None` branch and proves the intended cases go red.

---

**Low** — measured claims about transcript tool fields are unsupported in the repo.

Evidence: the spec claims:

```text
tool_use blocks sit in the same assistant records the guard already walks
...
across six transcripts `Edit` and `Write` both carry `input.file_path`.
`NotebookEdit` was absent from all six
```

[docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md:128)

I found no JSONL transcripts in the repo, and `rg` over `.claude docs scripts` only finds these assertions, not the measured payloads. Label this unverified unless the spec cites the transcript files or includes a fixture.

The docstring claim is verified: the cited gap is real:

```python
WHAT IT CANNOT SEE, stated rather than hidden:
  * a multi-step job never announced at all.
```

[scripts/check-banner-armed.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-banner-armed.py:35)

Smallest fix: move the transcript-shape claim into executable fixtures, or cite the exact transcript paths and redact only what is necessary.

---

**Medium** — §8 understates the blind spots.

Evidence: §8 lists Bash, banner quality, and work with no plan:

```text
A turn that does plan work entirely through `Bash`
...
Whether the banner was any good.
...
Work done with no plan armed at all.
```

[docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md:198)

Missing blind spots:
- Subagent/internal tool use not present in main transcript.
- `MultiEdit` or any non-listed editing tool.
- Paused sentinel state.
- Zero-step/malformed plan state.
- Tool path absent, renamed, or runtime-specific.
- Edits to ignored/runtime files inside root.
- Compaction/resume windows where transcript shape is not equivalent to one user turn.

Smallest fix: expand §8 and add at least one self-test per deliberately accepted blind spot, so “cannot see” does not become an accidental quiet pass.

VERDICT: NOT CONVERGED
