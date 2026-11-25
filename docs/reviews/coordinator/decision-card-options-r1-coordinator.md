# Round 1 — `decision-card-options` (PR #635, backlog #727) — coordinator — Codex NOT CONVERGED, Claude CONVERGED; all 5 findings FIXED

```yaml
round: 1
fixes_nontrivial: true
subject: decision-card-options
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: choice-encoding, disposition: fixed}
  - {id: F1, severity: Low, aim: deliverable, fix_induced: false, component: choice-encoding, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: false, component: attribute-presence, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: false, component: rec-line, disposition: fixed}
  - {id: F4, severity: Low, aim: instrument, fix_induced: false, component: manifest, disposition: fixed}
```

Both halves reviewed `12933d93`. Codex (`docs/reviews/codex/decision-card-options-r1-codex.md`) reported one MAJOR;
Claude (`docs/reviews/claude/decision-card-options-r1-claude.md`) four MINOR. X1 and F1 are the same defect.

| Finding | Verified against the code | Fix |
|---|---|---|
| **X1 / F1** — a `\|` inside a choice cannot be represented; `A&#124;B\|C` became three buttons | Reproduced: `HTMLParser` decodes the attribute before `_choices` splits it | **Refuse, never split.** The scan records whether the decision's start tag has a character reference that decodes to `\|` (`_CHARREF`: numeric, hex or named, `;` optional), and `_choices` refuses it ("a choice cannot contain `\|`"). `&amp;` and other references are unaffected. Documented in `explainer-delivery.md` §3a. Bound: an encoded `\|` in ANOTHER attribute of the same decision element is refused too (stated in the comment) |
| **F2** — a valueless `data-decision-options` / `-rec` read as absent (Yes / No card, or no ★) | Reproduced: a bare attribute's value is `None` | The scan records a bare attribute as `""`, so `_choices` refuses it: "at least two", "not one of", or "nothing for it to recommend" |
| **F3** — with options declared, a `.rec` line is ignored silently | Confirmed; intended behaviour, no notice | New PURE `decision_warnings`: options, no `data-decision-rec`, and a `.rec` SIBLING after the element before the next decision → a stderr WARNING from `main` (it refuses nothing). The sibling test compares parent stack entries by identity, which matches `recOf` reading `host.nextElementSibling` |
| **F4** — five killed clauses not in the manifest | Each anchor taken from Claude's list | Five entries added, plus eight for the new clauses (encoded-`\|` refusal, bare options, bare rec, the `.rec` flag, the sibling test, the rec-present and options-present conditions, the watch reset). `brief-compose`: 117 → 130 |

**Shown red without each fix** (each mutation applied to a copy, suite run): all 13 new mutations turn their
named case red. The control copy (no mutation) fails only `every real fragment in docs/explainers/ composes`, which
is ambient because the copy sits outside the repository.
Self-test 261 → 264 (three new cases: encoded `|`, bare attribute, `.rec` warning); docstring count updated.
