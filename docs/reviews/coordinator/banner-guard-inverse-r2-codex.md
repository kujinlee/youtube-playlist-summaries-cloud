<!-- codex-review: model=gpt-5.5 -->

**Blocking — §3.1’s hook snippet uses an undefined root variable and would wedge every Stop.**  
Evidence: spec says to run `python3 "$ROOT/scripts/check-banner-armed.py"` / `check-ci-watched.py` / `check-plan-progress.py` at `docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md:91-94`. The real hook defines `REPO_ROOT`, not `ROOT`, at `.claude/hooks/block-idle-stop.sh:23`, and today uses `"$REPO_ROOT/..."` at `.claude/hooks/block-idle-stop.sh:39`, `:54`, `:65`. If implemented literally, Bash expands `$ROOT` to empty, all scripts resolve under `/scripts/...`, `PLAN_RC != 0`, and the hook exits blocking at the proposed `:96`.  
Smallest fix: change §3.1 to use `"$REPO_ROOT/scripts/..."` and add a hook-level self-test that fails if the referenced scripts cannot be opened.

**High — §3.1 undercounts the new cost/noise: CI now makes GitHub calls on blocked mid-plan stops.**  
Evidence: old order exits before observers when plan progress blocks: `.claude/hooks/block-idle-stop.sh:39-41`. v2 moves `check-ci-watched.py` before the plan check at spec `:92-94`. `check-ci-watched.py` only skips network on default branch or no upstream at `scripts/check-ci-watched.py:141-151`; otherwise it runs `gh pr view --json statusCheckRollup` with a 25s timeout at `scripts/check-ci-watched.py:159-161`. So a pushed PR branch with an armed unfinished plan now pays a network call on every Stop attempt, including Stop-hook continuations. That is new behavior, not just “warnings now print.”  
Smallest fix: either keep CI reachability as a separately justified change with a bounded hook-level cost test, or split the reorder so only `check-banner-armed.py` runs before the blocker until CI’s every-stop network behavior is explicitly accepted.

**High — §3.5 over-widens the transcript window across legitimate fresh turns.**  
Evidence: spec requires skipping boundaries when `isMeta` or `promptSource` is `"system"` / `"sdk"` at `docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md:174-176`. But this repo already documents that a background-task notification is a fresh turn boundary: `scripts/check-plan-progress.py:28-34` says a turn beginning from a background-task notification has `stop_hook_active` false and is a fresh turn. Blanket-skipping `promptSource:"system"` / `"sdk"` can carry a banner from before such a notification into a later turn and suppress the new “edited with no banner” warning. Field semantics were not verified from accessible transcripts in this review; the spec’s claim remains partly unverified.  
Smallest fix: distinguish Stop-hook feedback continuations from background-task notifications. Skip only the former, or require tests proving each skipped `promptSource` value is not a real banner-obligation boundary.

**High — §4 repeats v1’s vacuous-test failure: F4 and F5 already pass today’s unfixed code.**  
Evidence: today’s `decide()` returns `QUIET` immediately when there is no banner: `scripts/check-banner-armed.py:147-149`. F4 is “paused · edited · zero banners -> QUIET” at spec `:227`; it passes today without any paused handling because zero banners short-circuits. F5 is also expected `QUIET` at spec `:228`; today’s unfixed code also goes quiet for no-banner windows, regardless of whether the window fix exists. These are labelled “Discriminating — these FAIL against today’s code” at spec `:220`, which is false.  
Smallest fix: move F4/F5 to regression guards, and add actual discriminators whose expected result differs from today’s `banner is None -> QUIET` behavior.

**Medium — §3.3’s import posture is underspecified and catches the wrong failure set.**  
Evidence: `check-plan-progress.py` cannot be imported by normal module name because of the hyphen; the repo’s existing solution is path import via `importlib.util.spec_from_file_location` in `scripts/begin-plan.py:89-103`. A normal `import check_plan_progress` fails with `ModuleNotFoundError`. Also, path import of a missing renamed file raises `FileNotFoundError`, not `ImportError`; `exec_module` can also surface syntax/runtime exceptions before the borrowed names exist. Spec `:134-138` says “catch ImportError” but does not specify the required path import helper or the non-ImportError failure cases.  
Smallest fix: specify a concrete `_load_plan_progress()` copied from `begin-plan.py`, and catch `ImportError`, `OSError`, `SyntaxError`, and missing-attribute failures inside the I/O shell, returning this guard’s `CANNOT RUN` message.

**Low — §3.8 log widening appears safe today, but the spec’s “reader checked” proof should be recorded.**  
Evidence: search found current readers only in `scripts/check-banner-armed.py:61`, `:173-175`, `:207-214`, its self-test at `:311-313`, docs, and `.claude/banner-warnings.log`. No repo script currently parses the log outside the writer.  
Smallest fix: add the actual negative search result to §3.8 or §6 so this does not depend on reviewer memory.

VERDICT: NOT CONVERGED
