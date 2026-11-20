<!-- codex-review: model=gpt-6.1-sol -->

External-copy scans reproduced every round 2 input. CM1/Cm1/CM3/CM4/CM5’s original inputs are fixed. CM2 and Cm2’s narrowed behavior matches the bounds stated in `_invocations`. Fresh baseline components equal the committed report. No invalid or duplicate `unread` locations found.

Self-test last line: `103/103 self-test cases passed`

- **MAJOR — scripts/check-publishability.py:236:** CM1 remains incomplete for nested fallback expressions. Input appended to external `scripts/page_chrome.py`: `REVIEW_NESTED = os.getenv("REVIEW_NESTED") or (None or None)`. Observed: no detector-6 config finding, although the fallback always returns `None`. Any nonconstant AST operand counts as working. Fix-induced: no.

- **MAJOR — scripts/check-publishability.py:302:** Blank lines between numbered prerequisites break introduction inheritance. Input appended to external `brief/SKILL.md`: `Read these prerequisites:\n\n1. `TaskList`\n\n2. `TaskStop``. Observed: detector 4 reports `TaskList` at line 225 but omits `TaskStop` at line 227. The backward walk stops at the blank, then checks the preceding item as the introduction. Fix-induced: no; CM4 remains incomplete.

- **MINOR — scripts/check-publishability.py:323:** A verb appearing anywhere is treated as an imperative, including explicit negation. Input: `This is a reference list of tools that we never use:\n\n- `TaskCreate` is merely a historical example.` Observed: detector-4 `tool-name` finding at external `brief/SKILL.md:200`, despite the explicit mention-only context. Fix-induced: yes.

- **MINOR — scripts/check-publishability.py:321:** Introduction lookup walks backward through a preceding list into an unrelated imperative. Input: `Read the section headings:\n- Overview\nHistorical examples (not instructions):\n- `TaskUpdate` is only an example.` Observed: detector-4 `tool-name` finding at external `brief/SKILL.md:221`; lookup crosses `- Overview` and inherits “Read”. Fix-induced: yes.

## Loosening answers
LOOSENING-CHECK 636d4531ad22: not a loosening
VERDICT: NOT CONVERGED
