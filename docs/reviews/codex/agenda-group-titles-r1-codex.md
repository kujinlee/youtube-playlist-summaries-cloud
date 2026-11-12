<!-- codex-review: model=gpt-6.1-sol -->

- **LOW — `scripts/goal-tree.py:2002`: leading whitespace defeats group styling.** Executed with snapshot step `when=" today", text="x"`; the snapshot reader accepts this shape. Page output:
  ```html
  <pre class="tree"> today
    1. ◇ x — d</pre>
  ```
  The group receives no `ag-when` span. The text parser strips heading whitespace, so this concerns accepted snapshot/log data.

- **LOW — `scripts/mutations/goal-tree.json:2976`: the re-bound mutation deletes the heading, not the first numbered step.** Applied and executed in memory; its target matches exactly once. Input: group `today`, step `FIRST STEP`. Observed:
  ```html
  <pre class="tree">  1. ◇ FIRST STEP — d</pre>
  ```
  It still exercises omission of the first `agenda_step_lines` element, but its name overstates numbered-step coverage.

Other mandated probes, executed at `scripts/goal-tree.py:2002`:

| Input | Observed All steps output |
|---|---|
| `when="<b>today</b>"` | `<span class="ag-when">&lt;b&gt;today&lt;/b&gt;</span>` — safely escaped |
| `when=""` | `<span class="ag-when"></span>` — empty title |
| `when="today", text="x\nFAKE GROUP"` | Title span, then `  1. ◇ x`, then unwrapped `FAKE GROUP — d` |

The newline probe refutes the literal physical-line rule: an unindented continuation is not a group label and receives no title span. Classification operates on list elements. Empty headings and unmarked multiline steps were rejected by `parse_agenda`; the direct snapshot probes rendered successfully.

The adjusted tests:

- **`scripts/goal-tree.py:4147` loses sensitivity to HTML wrappers.** A concrete renderer edit wrapping step output in `<span class="unexpected">...</span>` was rejected by the old prefix expression (`"<s"`) but accepted by the new expression (`"1."`). Executed the expressions against the seven-line fixture. This is weaker markup sensitivity, with no demonstrated loss of step-preservation coverage.
- **`scripts/goal-tree.py:4209`: no lost property identified.** The replacement still requires the initial `g` heading followed immediately by a newline, now inside its required title span; the other assertions remain unchanged.

Ran `python3 scripts/goal-tree.py --self-test`. Final line:
```text
439/439 self-test cases passed
```

VERDICT: NOT CONVERGED
