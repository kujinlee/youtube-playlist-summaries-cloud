# Round 1 — `decision-buttons` (PR #628) — coordinator — ⟳ NOT CONVERGED; every finding FIXED

```yaml
round: 1
fixes_nontrivial: true
subject: decision-buttons
halves:
  codex: ran
  claude: ran
findings:
  - {id: C1, severity: Major, aim: deliverable, fix_induced: false, component: sent-state, disposition: fixed}
  - {id: C2, severity: Major, aim: deliverable, fix_induced: false, component: recommendation, disposition: fixed}
  - {id: C3, severity: Major, aim: deliverable, fix_induced: false, component: post-shape, disposition: fixed}
  - {id: Cm1, severity: Minor, aim: deliverable, fix_induced: false, component: cases, disposition: fixed}
  - {id: F1, severity: Major, aim: deliverable, fix_induced: false, component: answerer, disposition: fixed}
  - {id: F2, severity: Major, aim: deliverable, fix_induced: false, component: sent-state, disposition: fixed}
  - {id: F3, severity: Minor, aim: deliverable, fix_induced: false, component: recommendation, disposition: fixed}
  - {id: F4, severity: Minor, aim: deliverable, fix_induced: false, component: cases, disposition: fixed}
  - {id: F5, severity: Minor, aim: deliverable, fix_induced: false, component: placement, disposition: fixed}
  - {id: F6, severity: Minor, aim: deliverable, fix_induced: false, component: interaction, disposition: fixed}
```

Codex (`docs/reviews/codex/decision-buttons-r1-codex.md`: 3 Major, 1 Minor) and Claude
(`docs/reviews/claude/decision-buttons-r1-claude.md`: F1–F6) reviewed the same head. I checked every finding against
the code before fixing it. Each proposed fix was treated as a hypothesis, and a test case was written to go red on
the defect.

| Finding | Disposition | Evidence |
|---|---|---|
| **F1** — a click is a paid `claude -p` question when the Ask answerer runs | **fixed** | New `is_decision_answer(q)` in `scripts/ask_answerer.py`. It is a pure check: the section ends `DECISION n of N` and the text starts `ANSWER: `. `pending()`, `page_items()` and the skipped list all filter on it. New case "decision answer: …": with the answerer running, 2 clicks run nothing, have no ledger state and are not shown on the panel. An `ANSWER:` under an ordinary section is still answered, and so is a real question under a heading that contains the tag. 4 mutations on a scratch copy (pending keeps the clicks; the panel shows them; the section need not END with the tag; the `ANSWER: ` prefix is not required) are each KILLED by that case. The control run passes it. The prefix mutation survived at first, and that is why the tagged-heading question was added. §3a and §5 of `explainer-delivery.md` now say a click is always the session's to record. |
| **Codex 1 / F2** — sent state keyed by URL + ordinal, never expires, outlives a recompose | **fixed** | The key is now `ex-pick:<page>:<label without "DECISION n of N">:<hash of the question text>`. A recomposed, renumbered page shows *sent* on the same decision only. The *sent* chip carries a **change** button that forgets the answer and offers the buttons again. A non-2xx is not remembered. Codex's `/latest` scenario is partly moot, because `/latest` is an HTTP redirect, so `location.pathname` is the real page. The ordinal defect it rode on was real. Cases: key shape (3 keys, including an unlabelled decision); renumbered recompose; change forgets (2 keys left); HTTP 400 not stored. |
| **Codex 2 / F3** — `recOf` takes the first `<b>` anywhere; `Recommend:` lead unrecognised | **fixed** | `LEAD` accepts `Recommend`, `Recommended` and `Recommendation`, with an optional colon. The bold is used only when it OPENS the paragraph. Otherwise the text runs to the first sentence end. Cases: "new child", "yes", and "yes, because the deadline matters" do not give "the deadline". Checked on the real fragments with the reviewer's jsdom harness: `2026-11-23-brief-publishable-components` gives `yes`, `yes`, `yes`, `as-is, documented`, and the 28-decision goal-tree walkthrough gives short leads such as `new child` and `merge`. |
| **Codex 3** — a newline in a label breaks the three-line POST shape | **fixed** | `norm()` collapses all whitespace in the label and the quote. Case: a multi-line label is one section line, and the split gives the three parts. |
| **Codex Minor / F4** — the cases pass on the failing inputs; four behaviours survive mutation | **fixed** | The self-test went from 234 to **245/245**. A 21-mutation sweep on a scratch COPY of `brief-compose.py` targeted each named survivor (stop at the next decision; `questionOf` keeps the buttons; no reload of a prior answer; a non-2xx saved) and each fixed bug above. All 21 were KILLED. `scripts/mutations/brief-compose.json` holds no DECISION_JS anchor, so the repository manifest is unaffected. Its slice, `check-plan-code.py --mutate . --only scripts/brief-compose.py`, was run: 94 mutations, 94 killed, 0 survivors. |
| **F5** — the button labels leak into the tray's heading text | **fixed (at the box)** | When the tag sits in an H1–H6, the box is placed AFTER the heading, not inside it, so `headingText` never reads the buttons. Case: "a heading box sits after the heading". Editing the tray's own `headingText` was not possible here, because the tray is lifted verbatim from source pages by `extract_tray` and has no canonical source in `scripts/`. The tag text's own leak into the heading text predates this PR and remains. |
| **F6** — IME Enter, double click, literal colour, no way back from Other… | **fixed** | Enter is guarded by `!e.isComposing && e.keyCode !== 229`. The box is busy while a POST is in flight: buttons and inputs are disabled, and a double click sends one entry. A failed POST re-enables the buttons. `.ex-pick-err` uses the `--decide*` tokens, and the case checks that no literal colour is left. Other… gets **Cancel**, which restores the buttons. Each part has a case and a killed mutation. |

**Gates on the fold** (`node_modules` symlinked read-only from the main checkout into the gitignored worktree path):
`brief-compose.py --self-test` 245/245; `ask_answerer.py --self-test` 124/124; `check-explainer-delivery.py` OK (1 shared
description, 2 skills cite it, 0 restatements); `check-docs.py` OK. The `ask_answerer.py` mutation slice was REFUSED
LOCALLY (52 mutations × 13 s, more than 10 min), so it is NOT RUN here and left to the PR's CI shards. Its one anchor that
the fold had moved ("the panel shows every page's questions on every page") was restored, so the edit is a separate
line and the anchor resolves again.
