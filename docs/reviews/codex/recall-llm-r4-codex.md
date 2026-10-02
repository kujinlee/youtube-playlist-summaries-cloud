<!-- codex-review: model=gpt-5.5 -->

## BLOCKING

None.

## HIGH

### H1 · Escaped heredoc delimiters are not refused, so heredoc body lines can be counted as real hook arms

`scripts/check-rc-contract.py:259`

> `if re.search(r"<<-?\s*[\w'\"]", block):`

The new soundness claim says heredocs are unmodelled and therefore refused, but this regex only catches delimiters whose first character is a word char, single quote, or double quote. Bash also accepts escaped delimiters such as `<<\EOF`. In that shape, the guard answers over heredoc body text and can falsely conclude that an rc is handled.

Reproduction:

```python
src = '''case "$RC" in
  0) : ;;
  3) cat <<\\EOF
  5) not an arm; just heredoc body
EOF
     ;;
  6) : ;;
  *) : ;;
esac
'''
```

Observed with `check-rc-contract` helpers:

```text
unmodelled = []
sound = []
handled = {0, 3, 5, 6}
verdict = []
```

Observed with bash:

```text
bash -n: syntax-ok
RC=3 prints the heredoc body line: "  5) not an arm; just heredoc body"
RC=5 goes to *)
```

So the checker reports rc 5 as handled even though bash does not have a `5)` arm. This is the same failure shape the B2 fix was meant to close: an unmodelled quoting/body form is answered over instead of becoming cannot-run.

Observation that would prove this wrong: `unmodelled_quoting()` returns a problem for `<<\EOF` / escaped heredoc delimiters, or another soundness check refuses the block before `handled_codes()` is trusted.

## MEDIUM

None.

## LOW

None.

## ARMING Question

I do **not** find a fifth live instance in `recall-llm.py`.

Bounded enumeration:

`--print-prompt` uses `prepared_prompt()`.

- `read_armed_plan()` before parsed-plan armed scope: no sentinel raises `Refusal`, rc 2. This is routine absence, not armed.
- Sentinel/plan unreadable paths raise `UnreadablePlan`, rc 5.
- Bad plan shape raises `UnreadablePlan`, rc 5.
- After plan verdict passes, `read_corpus()` bare `Refusal` paths are caught at `prepared_prompt()` and converted by `unanswerable_if_armed()` to `Unanswerable`, rc 6.
- Success prints prompt and returns `OK`, rc 0.

`--arm` uses `prepared_prompt()` plus `_arm_body()`.

- All `prepared_prompt()` exits are as above.
- `call_model()` bare `Refusal` paths are inside `do_arm()`’s boundary and become rc 6.
- `parse_response()` / `no_duplicate_keys()` raise `ResponseRejected`, rc 4, not rc 2.
- Cache write `OSError` is caught, prints the paid answer, then raises `Unanswerable`, rc 6.
- Success returns `OK`, rc 0.
- I found no `sys.exit`, `os._exit`, fallthrough, or swallowed exception that exits this armed scope with rc 2.

`--fire` uses `read_armed_plan()` then `_fire_armed()`.

- `read_armed_plan()` is intentionally outside the armed scope: no sentinel remains rc 2; unreadable armed plan is rc 5.
- Inside `_fire_armed()`: paused and completed plans return `OK`.
- Bad plan is rc 5.
- Missing/stale cache is `StaleCache`, rc 3.
- Missing corpus/entry from `cached_entry_verdict()` is explicitly `Unanswerable`, rc 6.
- Any future bare `Refusal` inside `_fire_armed()` is caught by `_fire()` and converted to rc 6.
- Marker read/write exceptions are swallowed only after deciding to surface or not surface; they return rc 0, not rc 2.

Bad usage:

- No mode or multiple modes returns `CANNOT_RUN`, rc 2 before any plan is read.
- Argparse bad usage exits 2 before matcher contract logic runs.
- These are not armed-scope exits.

So the structural arming condition does **not** fire from a fifth recall-matcher instance in this round.

## Other Checks

`unanswerable_if_armed(exc.rc == CANNOT_RUN)` looks safe for the current three boundaries. I found only one rc-2 class: `Refusal` itself. Existing subclasses carry rc 3, 4, 5, and 6, and the boundary preserves them.

`_fire_armed(again, sentinel_text, plan, plan_text)` appears to thread arguments correctly: `again` still controls repeat surfacing, `sentinel_text` still feeds `paused()`, `plan` still feeds cache/marker naming, and `plan_text` still feeds verdict, current step, and fingerprint checks.

The three `DELIBERATELY_UNHANDLED` reasons re-derive as true for the current tree, including `--print-prompt` and mode-combination rc 2 cases.

## Could Not Establish

I did not run the full mutation command `check-plan-code.py --mutate .`; I ran the non-mutating self-test and the other claimed gates. I also did not build a true randomized self-test runner, but I did run both affected self-test suites repeatedly in-process to probe monkeypatch leaks.
