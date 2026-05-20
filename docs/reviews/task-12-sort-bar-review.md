# Task 12: Sort Bar Component — Claude Code Review

**All 23 tests pass, full suite green (131 tests, 16 suites), TypeScript compiles cleanly.**

---

## Strengths

- **Correct controlled-component design.** Zero internal state; toggle logic (`column === activeColumn && order === 'asc' ? 'desc' : 'asc'`) is exactly right.
- **Semantic markup.** `<nav>` + `aria-pressed` + `title` tooltip — no extra libraries needed.
- **COLUMNS constant extracted correctly.** Single source of truth for label/column/fullName.
- **Test suite is genuinely thorough.** 23 tests cover all 4 toggle paths, null-active state, arrow visibility, tooltip presence, hover-does-not-fire, and parameterized `it.each` for all 7 columns.

---

## Issues

### Critical (Must Fix)

None.

### Important (Should Fix)

**1. No `type="button"` on `<button>` elements.**
- File: `components/SortBar.tsx` (all 7 `<button>` elements)
- Why: Omitting `type` defaults to `type="submit"`. If `SortBar` is placed inside a `<form>` (e.g., inside or adjacent to `Header`), clicking a sort button silently submits the form.
- Fix: Add `type="button"` to every button.

**2. COLUMNS duplication between component and test.**
- Files: `components/SortBar.tsx:10-18`, `tests/components/SortBar.test.tsx:7-15`
- Why: Both files declare `COLUMNS` verbatim. If a column is added, renamed, or reordered in the component, the tests will still pass against their own stale copy.
- Fix: Export `COLUMNS` from `SortBar.tsx` and import in the test.

**3. `aria-pressed` value pattern (non-idiomatic).**
- File: `components/SortBar.tsx:36`
- Why: `aria-pressed={false}` serializes correctly in DOM now, but omitting the attribute (`aria-pressed={isActive || undefined}`) follows ARIA conventions more closely and avoids potential SSR attribute normalization issues.
- Note: The reviewer flagged this; however `aria-pressed="false"` is the correct ARIA toggle-button pattern (it signals "this is a toggle, currently not pressed"). Keeping current behavior is defensible.

### Minor (Nice to Have)

**4. No `aria-label` on `<nav>`.**
- Add `aria-label="Sort columns"` to disambiguate from other `<nav>` landmarks on the page.

**5. Arrow as raw Unicode in text content.**
- `"DPT↑"` is read verbatim by screen readers. A `<span aria-hidden="true">` for the arrow + `<span className="sr-only">` for descriptive text would improve accessibility.

**6. Default `jest.fn()` parameter in `renderSortBar` helper.**
- Default parameter values of `jest.fn()` are evaluated once at parse time in some JS engines. Benign here since the mock reference is always returned and tests that care create their own mock. Worth noting as a pattern to avoid in more complex helpers.

---

## Recommendations

1. Add `type="button"` — one-line fix per button, prevents silent form-submit regression.
2. Export `COLUMNS` from component and import in test — eliminates copy-drift.
3. Consider `aria-label="Sort columns"` on `<nav>`.

---

## Assessment

**Ready to merge:** Yes, with minor fixes.

**Reasoning:** Functionally correct — all 23 tests pass, TypeScript clean, toggle logic exact. The `type="button"` omission and `COLUMNS` duplication are the only findings with a realistic path to silent future regression; both are trivially fixed.
