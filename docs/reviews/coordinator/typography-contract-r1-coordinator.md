# Round 1 — `typography-contract` — coordinator — ❌ NOT CONVERGED (1 High, 3 Medium, 4 Low)

```yaml
round: 1
fixes_nontrivial: true
subject: typography-contract
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: em-dark-state, disposition: fixed}
  - {id: M1, severity: Medium, aim: records, fix_induced: false, component: closure, disposition: fixed}
  - {id: M2, severity: Medium, aim: deliverable, fix_induced: false, component: contract-text, disposition: fixed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: false, component: contract-text, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: contract-text, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: false, component: contract-text, disposition: fixed}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: false, component: contract-text, disposition: fixed}
  - {id: L4, severity: Low, aim: deliverable, fix_induced: false, component: contract-text, disposition: fixed}
```

Both halves: closing backlog #226 hid part (c) (Codex M, Claude H). Claude measured WHY it matters: with the
OS dark and nothing pressed, neither keyed `--em` rule applies, and bold text rendered at 1.90 / 2.05 / 1.90 :1
on three real pages. Claude M: the reserved list omitted `--cool`/`--hot`/`--defect`; "opts in" did not say a
page MUST, though without `.ex-body` the composer silently drops the switcher. Lows (both halves): "values live
in ONE place" ignored fragment overrides; the hue parenthetical was false of the owner's own reference page;
"storage holds only the opt-outs" is true of `page_chrome` only; the tabular-producer list omitted two.

Dispositions: H1 FIXED in the deliverable — one shim rule, `:root:not([data-theme="light"])` inside the OS-dark
media query (kept out of the `html{}` block `shim_dark_tokens` reads, so no fragment is newly refused); three
pages recomposed and re-measured 8.33–9.00 :1 in all four states; one case, one mutation, scoped run 28/28.
M1 FIXED: #226 reopened as PARTLY — part (c)'s GUARD remains. M2/M3 and all Lows FIXED in the text, each claim
re-checked (17 fragments declare `--warn`, 19 `--defect`; no tabular producer emits `.ex-body`). FOLD:
coordinator. Round 2: Codex.
