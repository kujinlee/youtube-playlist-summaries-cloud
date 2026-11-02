<!-- codex-review: model=gpt-6.1-sol -->

All reproductions used synthetic plans. No real plan content was read or quoted.

1. **Blocking — `scripts/check-plan-leak.py:240`: pushed history is unscanned.** Commit a leak in `a:1`, then remove it in a second commit. Checker returns **0**. A push to a disposable bare remote succeeded, and the intermediate blob remained retrievable. Comparing endpoint trees cannot protect committed history.

2. **Blocking — `scripts/check-plan-leak.py:344`: ignores push targets.** With clean HEAD and a leaking `secret` branch, `git push origin secret` passes the HEAD scan. The same problem covers `--all`, tags pointing to leaking commits, and commands targeting another checkout.

3. **Blocking — `scripts/check-plan-leak.py:328`: misses ordinary Git invocation forms.** Direct hook tests of `git -C /tmp/r push` and `git -c x.y=z push` invoked no scan and returned no denial. An alias such as `git ship` also bypasses detection. The registration at `.claude/settings.json:15` adds another narrow command filter.

4. **Blocking — `scripts/check-plan-leak.py:328`: comments activate the escape.** Input `git push # ALLOW_PLAN_LEAK=1` bypasses scanning without setting the environment variable. Likewise, `git push; echo ALLOW_PLAN_LEAK=1` exempts the preceding push.

5. **Blocking — `scripts/check-plan-leak.py:136`: quoted filenames disappear.** Add synthetic plan text at `quoted"name.md:1`. Git quotes the patch header; the parser only accepts literal `+++ b/`. Checker returns **0**.

6. **Blocking — `scripts/check-plan-leak.py:240`: binary content is omitted.** Add a tracked file containing a NUL followed by a qualifying plan run. Git emits a binary-file notice rather than added lines; checker returns **0**.

7. **Blocking — `scripts/check-plan-leak.py:282`: local base is mistaken for published history.** Put an unpublished leaking commit into local `origin/master` using `git update-ref`, then add another copy in the next commit. Checker returns **0** because the unpublished phrase is treated as public. Pushing both commits publishes it.

8. **Blocking — `scripts/check-plan-leak.py:217`: worktree discovery failure permits incomplete scanning.** With a private plan only in another worktree, the healthy scan returns **1**. Make `git worktree list --porcelain` fail while other Git operations work: discovery falls back to local plans and the scan returns **0**. This contradicts the promised block on Git failure.

9. **Major — `scripts/check-plan-leak.py:163`: wrapping defeats matching.** Split a qualifying run into two six-word added lines at `a:1` and `a:2`. Checker returns **0**. This documented limitation still defeats the requested normalization protection.

10. **Major — `scripts/check-plan-leak.py:255`: inconsistent Unicode normalization falsely blocks.** Put an eight-word run containing `Straße` in a tracked base file, then add its uppercase equivalent. Python casefolding identifies the plan match, but Git’s case-insensitive prefilter misses the public equivalent. Checker returns **1** despite the run already being public.

11. **Major — `scripts/check-plan-leak.py:351`: stderr is not a private terminal channel.** Running `python3 scripts/check-plan-leak.py` through the Bash tool exposes matched words in captured tool stderr. Running it with `2>review.log` persists them in a file. The output channel does not enforce the claimed terminal-only boundary.

Validation completed:

- Self-tests: **63/63 passed**.
- Requested mutation command: **38/38 killed**; its output explicitly identifies this as a diagnostic slice, **not the gate**.
- Additional surviving mutation: remove Git-option support from `PUSH`; **63/63 still pass**. Existing hook positives use plain `git push`, so they pass for an ambient reason.
- Performance: **300,000 clean added lines scanned in 2.07 seconds**, without a hang.

**NOT CONVERGED**
