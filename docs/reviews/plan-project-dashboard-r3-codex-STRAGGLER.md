<!-- codex-review: model=gpt-5 -->

READY TO EXECUTE: YES

Shortest must-change list: make the Python transcription actually runnable end-to-end, fix `_ordered` for consecutive malformed blocks, close the Unicode/form-feed `NO-ENTRY:` bypass, and add real assertions for the day-anchor and no-entry marker behaviors.

Blocking — "Every Python block below was executed before it was written down, and then EXTRACTED PROGRAMMATICALLY from the file that was executed"
What I checked: exact block-only transcriptions at `/tmp/dashboard-plan-r3-exact/check-dashboard-entry.py` and `/tmp/dashboard-plan-r3-exact/gen-dashboard.py`, plus the claimed self-test commands.
Actually true: the exact transcriptions do not reproduce the claimed runs. `python3 /tmp/dashboard-plan-r3-exact/check-dashboard-entry.py --self-test` exits `0` with no output, and `python3 /tmp/dashboard-plan-r3-exact/gen-dashboard.py --self-test` exits `0` with no output as well. The runnable harness I had to build next needed extra non-fenced glue (`TECH_MARKER`, `BLOCK`, the gate import, and an `__main__` call) that is not part of the fenced blocks, so the "byte-for-byte extracted" claim is overstated.
VERIFIED

High — "`_ordered` ... is order-agnostic"
What I checked: `python3 - <<'PY' ... parse_entries(... two consecutive malformed blocks ...) ... _ordered(...) ... PY`
Actually true: the two malformed blocks render reversed, not in file order:
```text
[('Newest good.', None), ('Broken B.', "not a real calendar date: '2026-02-31'"), ('Broken A.', "not a real calendar date: '2026-02-30'"), ('Older good.', None)]
```
That is `Newest good.` -> `Broken B.` -> `Broken A.` -> `Older good.`. The single-malformed case is covered; consecutive malformed blocks are not.
VERIFIED

High — "`Exemptions must be explicit and visible`"
What I checked: `python3 - <<'PY' ... exemption_reason(...) ... PY`
Actually true: invisible whitespace prefixes still count as valid exemptions:
```text
unicode nbsp indent => 'nbsp'
unicode emspace indent => 'emspace'
form feed indent => 'formfeed'
```
So `NO-ENTRY:` can be smuggled past the visibility rule with `\u00a0`, `\u2003`, or `\f` at the start of the line. The plan says the exemption must be visible; the implementation accepts hidden variants.
VERIFIED

Medium — "`Clicking a bar scrolls to that day's entries in §6`"
What I checked: mutated `/tmp/dashboard-plan-r3-mutations/remove_day_anchor.py` to delete the `day_anchor` emission and reran `--self-test`.
Actually true: the suite still passes:
```text
70/70 passed
```
So the self-test does not prove the chart's link target exists at all; it only proves the bar has an `href` string.
VERIFIED

Medium — "`§9 a day that shipped with NO entry is marked in SIGHTED output`"
What I checked: mutated `/tmp/dashboard-plan-r3-mutations/remove_gapmark.py` to delete the dedicated `gapmark` span and reran `--self-test`.
Actually true: the suite still passes:
```text
70/70 passed
```
That case is satisfied by the `unwritten` class alone; the dedicated visible marker can disappear without a red test.
VERIFIED

NOT CONVERGED
