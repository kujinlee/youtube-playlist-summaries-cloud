# Round 1 — `text-style-default` — coordinator — ⟳ NOT CONVERGED (both halves); ACCRETE with a closed grammar

```yaml
round: 1
fixes_nontrivial: true
subject: text-style-default
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: em-guard, disposition: fixed}
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: palette-scanner, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: false, component: palette-scanner, disposition: fixed}
  - {id: Xm4, severity: Low, aim: deliverable, fix_induced: false, component: em-guard, disposition: fixed}
  - {id: Xm5, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm3, severity: Low, aim: deliverable, fix_induced: false, component: palette-scanner, disposition: fixed}
  - {id: Cm4, severity: Low, aim: deliverable, fix_induced: false, component: palette-scanner, disposition: fixed}
  - {id: Cm5, severity: Low, aim: deliverable, fix_induced: false, component: palette-scanner, disposition: fixed}
```

`X` = Codex, `C` = Claude, both on `9aa3b909`. **Both reproduced:** 22–23 of 24 fragments compose byte-identically under
both composers (the 24th is the intended change); both committed pages: three topmost buttons, h2 changes colour,
OS-dark bold 9.04:1 and h2 7.23:1; 35/35 mutations attributed; 2340 real; 164/164.

Duplicates: XM3 = CM1 — the `--em` refusal runs only when the COMPOSER adds the switcher; a fragment bringing its own
`#schemer` is styled identically and never checked (2.06:1). Xm4 = Cm2 — the guard checks PRESENCE, not a usable value
(`var(--x)` → 1.00:1, `initial`, the light value in a dark block). Xm5 = Cm6 — the dashboard still says browser
verification is to do.

**The scanner leaks BOTH ways** — fails open: `:root,body` lists (XM1), `--tokens:{--em:…}` (XM2), `@import …;`
before a palette (Cm3), CSS nesting (Cm4); fails closed: split `:root` rules, `:root .card`, `:where(:root)` (Cm5),
`--tokens:{…};--em:…` (XM2). A regex standing in for a CSS parser — the shape #381 spent four rounds closing one
route at a time. **Route: ACCRETE with a CLOSED GRAMMAR:** support a declared set of forms, refuse everything else by
name; enforce whenever the finished page carries a switcher; check the VALUE (a literal colour with adequate
contrast on the block's own `--bg`; anything unresolvable refused as unverifiable).
