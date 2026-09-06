<!-- codex-review: model=gpt-5.5 -->

**Blocking** — F4’s side-effect test patches `ROOT` in a way that makes `_plan_steps()` unable to import the real checker, so the test will stay red after the planned fix.

Evidence: Task 5 patches `globals()["ROOT"] = _root` before calling `run_decide` ([plan:585-590](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:585)). Task 4 wires `steps = _plan_steps() if armed else _UNSET` before `decide()` ([plan:535-538](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:535)). `_plan_steps()` imports from `ROOT / "scripts" / "check-plan-progress.py"` ([plan:354-359](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:354)).

Executed probe with `ROOT` set to a tempdir: `exec_module` raises `FileNotFoundError` for `/tmp/.../scripts/check-plan-progress.py`. Because `_plan_steps()` catches `Exception` and returns `None` ([plan:385-392](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:385)), `decide()` takes the hoisted CANNOT_RUN branch ([plan:400-404](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:400)), not WARN. The planned F4 assertion requires `_rc == WARN` and a log ending in `unbannered\t3 unticked` ([plan:592-594](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:592)), so it fails for the wrong reason after implementation.

Smallest fix: split the import base from the fixture root. Keep a stable `SCRIPTS = Path(__file__).resolve().parent` or `REPO_ROOT = Path(__file__).resolve().parent.parent` for `_load_plan_progress()`, and patch only the runtime state roots (`SENTINEL`, `WARN_LOG`, and an explicit root argument used by `_edit_inside_repo`/plan path resolution). Or copy `scripts/check-plan-progress.py` into `_root/scripts/` in the fixture, but that weakens the “real borrowed checker” claim.

**Blocking** — F6’s new anchor does not exist in the real hook, so the self-test will crash with `ValueError` today and after the Task 6 edit.

Evidence: the planned test uses `hook.index('check-plan-progress.py "${ARGS[@]}"')` ([plan:676-678](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:676)). The real hook line is `if ! python3 "$REPO_ROOT/scripts/check-plan-progress.py" "${ARGS[@]}"; then` ([hook:39](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/hooks/block-idle-stop.sh:39)). The Task 6 target edit preserves the same quoting shape ([plan:708](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:708)).

Executed search: `hook.count('check-plan-progress.py "${ARGS[@]}"') == 0`; `hook.index(...)` raises `ValueError`. The actual executable substring is `check-plan-progress.py" "${ARGS[@]}"`, count 1. This violates Step 2’s expected “F6 prints FAIL” ([plan:683-686](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:683)) and Step 4’s expected pass.

Smallest fix: anchor on a string that actually exists exactly once, e.g. `hook.index('check-plan-progress.py" "${ARGS[@]}"')`, or better parse executable non-comment lines and locate the line containing both `check-plan-progress.py` and `"${ARGS[@]}"`.

**Medium** — The plan’s “both `Nothing is blocked` messages” claim is internally inconsistent with its own Task 7 instruction.

Evidence: the spec says “Both `Nothing is blocked` messages are corrected” ([spec:292-294](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md:292)), but the plan explicitly says not to touch `scripts/check-ci-watched.py:107` because that sentence is accurate there ([plan:743](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:743)). The self-review maps all of §8 to T7 and says “No gaps” ([plan:787](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:787)), while Task 7 implements only the `check-banner-armed.py` message.

Smallest fix: make the plan explicitly say the spec’s “both” means both relevant `check-banner-armed.py` warning classes, or amend the spec coverage note to acknowledge the deliberate `check-ci-watched.py` exception.

**Claims I Verified As Correct**

The F4 fixture is otherwise a WARN-shaped fixture: sentinel exists, plan has 1 done and 4 total, transcript has an Edit tool use inside the patched root, and no banner text. The failure is the patched import base, not the fixture’s predicate.

The `globals()` patching does reach module-global reads: `_armed()` reads `SENTINEL`, `_plan_steps()` reads `ROOT` and `SENTINEL`, `_edit_inside_repo(..., ROOT)` receives patched `ROOT`, and the WARN message uses `WARN_LOG.relative_to(ROOT)`.

The `finally` restore in F4 restores all three patched globals even if `run_decide()` or the assertion expression raises ([plan:595-596](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-09-04-banner-guard-inverse.md:595)).

Task 3a’s signature-only split is behavior-preserving as written. Task 3b’s red is a real printed FAIL after 3a, not a crash: `decide(..., steps=None)` is accepted, then today’s code returns QUIET.

`except Exception` does not catch `KeyboardInterrupt` or `SystemExit`; those inherit from `BaseException`, not `Exception`.

The count instruction is adequate: `check-plan-code.count_drift()` requires the canonical `--self-test  # N cases` form ([check-plan-code.py:1121](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-plan-code.py:1121)), and Task 7 points at the existing canonical line `:47`.

VERDICT: NOT CONVERGED
