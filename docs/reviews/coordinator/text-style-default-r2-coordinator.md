# Round 2 — `text-style-default` — coordinator — ⟳ NOT CONVERGED (Codex); REDESIGN (the claim, and a strict format)

REVIEW GAP: claude — round 2 alternates to the Codex half alone (rounds 2+ alternate, `review-method.md` → *Round topology*).

```yaml
round: 2
fixes_nontrivial: true
subject: text-style-default
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: true, component: palette-scanner, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: true, component: palette-scanner, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: true, component: palette-scanner, disposition: fixed}
  - {id: X4, severity: Medium, aim: deliverable, fix_induced: false, component: em-guard, disposition: fixed}
```

Codex on `f88f10d0`, every repro measured in Chromium. **X1** `!important` on `--em` ignored — false accept at
1.00:1 and a false refusal of a 9.04:1 page. **X2** whitespace inside an attribute selector read as a descendant and
skipped. **X3** an `--em` override inside `@supports` with no `--bg` of its own never validated, yet it wins. **X4** a
`body` background overriding the palette — every block check passes, the page renders 1.00:1. **Held:** 181/181; the
14 new cases red on `aaf6fe67`; 49/49 mutations attributed; 2354 real; 24 fragments compose, 0 refused.

**Why the bet lost — and why patching cannot win.** All four are the CSS CASCADE: importance, selector parsing,
context precedence, and which element paints the ground. A Python scanner re-implementing the cascade is a parser
standing in for a browser; #381 spent four rounds closing that shape one route at a time.

**Route: REDESIGN of the claim.** The guard becomes a strict lint of the house palette FORMAT — canonical root blocks
spelled exactly, no `!important` on palette tokens, `--em` only beside `--bg`, the page ground only `var(--bg)` — and
refuses everything off-format by name. It stops claiming rendered readability: only a browser can verify that, and
`explainer-delivery.md` §5b already makes browser verification mandatory for every page.

**Thrashing?** X1–X3 are induced by round 1's scanner (fix_induced) — the first round of fix-induced findings in this
component, so the arming condition (two consecutive) is not met.
