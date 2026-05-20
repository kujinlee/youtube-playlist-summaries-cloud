# Task 12: Sort Bar Component — Codex Adversarial Review

---

## High

No additional high-severity issues found beyond the known `type="button"` finding (flagged by Claude review).

---

## Medium

**1. Sort direction not exposed with reliable accessible announcement**
- File: `components/SortBar.tsx:36-41`
- Why: `aria-pressed` only communicates selected/unselected, not ascending/descending. The direction is only conveyed via the visible arrow in button text; `title` is not a reliable screen reader announcement mechanism.
- Fix: Add explicit `aria-label` with direction: `aria-label={`${fullName}, ${isActive ? `sorted ${order === 'asc' ? 'ascending' : 'descending'}` : 'not sorted'}`}`. Hide decorative arrow with `aria-hidden`.

**2. Repeated-click toggle not tested through controlled prop updates**
- File: `tests/components/SortBar.test.tsx:115-125`
- Why: Tests check asc→desc and desc→asc as separate isolated renders, never as a real controlled sequence: click → rerender with emitted props → click again. A parent-side regression could pass these tests while breaking the actual toggle experience.
- Fix: Add test using `rerender`: click active asc column, assert `desc` emitted, rerender with `order="desc"`, click again, assert `asc` emitted.

**3. Rapid double-click emits the same direction twice (stale props)**
- File: `components/SortBar.tsx:23-25`
- Why: Two clicks before the parent rerenders both read the same `order` prop, so both calls emit the same next direction.
- Fix: Document that toggling requires a parent rerender between clicks (controlled component contract), and add a regression test for rapid clicks documenting the expected behavior.

---

## Low

**4. Tests query by `title` rather than accessible button name**
- Why: Validates tooltip attributes more than accessible behavior. Once aria-labels are added, prefer `getByRole('button', { name: /depth/i })` for interaction tests.

**5. No assertion on rendered column order**
- Why: Tests confirm 7 buttons exist but not their left-to-right sequence. A reorder in COLUMNS would pass undetected.
- Fix: Assert `getAllByRole('button').map(b => b.textContent?.replace(/[↑↓]/g, ''))` equals the expected column order.

---

## Actions

- Medium #1 (aria-label + aria-hidden): **Fix** — significant accessibility gap
- Medium #2 (rerender toggle test): **Fix** — adds real integration confidence
- Medium #3 (rapid double-click): **Document** — inherent to controlled component pattern; add test documenting expected behavior
- Low #4 (title→aria-label queries): **Fix** — update interaction tests once aria-labels added
- Low #5 (column order test): **Fix** — trivial, closes a real gap
