# Round 1 — `603-decision-tags` (PR #563, backlog #603) — coordinator — NOT CONVERGED (both halves)

Codex half: `docs/reviews/codex/603-decision-tags-r1-codex.md`. Claude half: `docs/reviews/claude/603-decision-tags-r1-claude.md`. Both reviewed `4699e55a`.

```yaml
round: 1
fixes_nontrivial: true
subject: 603-decision-tags
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: decision-scan, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: decision-ids, disposition: fixed}
  - {id: X3, severity: Low, aim: instrument, fix_induced: false, component: self-test, disposition: fixed}
  - {id: X4, severity: Low, aim: instrument, fix_induced: false, component: self-test, disposition: fixed}
  - {id: F1, severity: High, aim: deliverable, fix_induced: false, component: walkthrough-page, disposition: fixed}
  - {id: F2, severity: High, aim: deliverable, fix_induced: false, component: walkthrough-page, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: false, component: decision-scan, disposition: fixed}
  - {id: F4, severity: High, aim: instrument, fix_induced: false, component: self-test, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: false, component: decision-css, disposition: fixed}
  - {id: F6, severity: Low, aim: deliverable, fix_induced: false, component: decision-ids, disposition: fixed}
```

Severity mapping: a review's MAJOR is `High`, MINOR is `Low`. F4 is one finding of five survivors; its Mb (the OS-dark half unpinned) is the MAJOR part, so it is recorded `High`.

**Both halves agreed on the two code defects** (Codex 1 = Claude F3, Codex 2 = Claude F6), and both measured the same contrast figures (10.72 / 7.59 / 9.77 / 7.83:1).

## What changed

- **A decision the owner cannot see is REFUSED (X1, F3).** `_DecisionScan` now keeps an ancestor stack. A mark is CANNOT RUN, naming the element, when it is ON a table row/section, `select`/`option`/`datalist`, a raw-text element (`textarea`, `title`, `xmp`, `iframe`, `noembed`, `noframes`, `plaintext`, `script`, `style`), `template`, `noscript` or a void element; when it or an ancestor carries `hidden` or `inert`; or when it is INSIDE `template`, `noscript`, `select` or `datalist`. An unclosed `<p hidden>` stays on the stack, which can only produce a refusal, never a silent count.
- **`<details>` is OPENED, not refused.** Every `<details>` on or around a decision gets `open`, so its tag shows on load. Chosen over moving the tag onto the `<summary>`: the tag stays where the fragment marked it.
- **One parse on 3.12 and 3.14.** The scan names the browser's raw-text set in `CDATA_CONTENT_ELEMENTS`, so 3.12 treats `textarea`/`title` like 3.14 does; nothing after `<plaintext>` counts on either. The case emulates 3.12 on any interpreter (a subclass with 3.14's own raw-text list emptied), and the suite was run under both: 222/222 each.
- **Ids are namespaced and a collision is refused (X2, F6).** `ex-decision-{n}`; a fragment `id` or `name` equal to one the tags need is CANNOT RUN.
- **The tag leads with the fragment's own label (F5).** `data-decision-label="D7"` renders `🟨 ✍ D7 — DECISION 6 of 13`, and the counter's link shows it too. Taken rather than declined: the walkthrough numbers its decisions D1–D9 and Q1–Q4, and a bare "DECISION 5" on a page that says "D5" reads as the wrong one. `text-transform: none` on the tag and the counter stops `.box .lbl` capitalising the recorded answer.
- **The walkthrough's marks follow the spec (F1, F2).** Decision Q1 carries its 11-09 answer (spec §2b, "accepted for this milestone", selection card A). The spec-approval box carries 11-11 05:53 (spec status line, §2c). Q2's answer is the §2c line ("evaluated for SHIPPING as a portable, engine-agnostic CI layer, not only as a harvest"). Two owner items had no mark and now have one: the C5 corpus content review (spec deliverable 11, "THE OWNER'S … This cannot be delegated") and the copyright holder (spec §4: "A legal name or entity is a one-line decision the owner still owns"). The page now reads 13 decisions, 2 remaining.
- **The survivors are killed (X3, X4, F4).** New cases: first open with decision 1 answered and 2 open; the answered count at two inputs; a whitespace-only value is open; the position guard (factored into `_decision_offset` so it can be reached); WCAG contrast ≥ 4.5 computed from `DECISION_CSS` for both tag states in all four theme blocks, OS-dark included; the OS-dark block equals the dark toggle and differs from light; the answered rule reads the green tokens.

Self-test 207 → 222 (and 222/222 under Python 3.12). Manifest 58 → 77 (19 new; three 603 entries re-anchored onto the rewritten loop). `check-plan-code.py --mutate . --only scripts/brief-compose.py`: 77 mutations, 77 killed, 77 attributed to the case each names, 0 survivors (a diagnostic slice, not the gate).

## Not done

- No check makes a fragment mark EVERY owner decision it contains. F2's two missing marks were found by reading the page against the spec. Whether a decision is the owner's is a judgement about prose, which no parse can make.

Round 2 alternates: ONE half.
