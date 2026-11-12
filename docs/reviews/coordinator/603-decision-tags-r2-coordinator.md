# Round 2 — `603-decision-tags` (PR #563, backlog #603) — coordinator — NOT CONVERGED (Codex)

Codex half: `docs/reviews/codex/603-decision-tags-r2-codex.md`, reviewed `6cc2fd04` (the r1 fold).

REVIEW GAP: claude — alternation (rounds 2+ run ONE half; round 3 is Claude's).

```yaml
round: 2
fixes_nontrivial: true
subject: 603-decision-tags
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: true, component: decision-scan, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: true, component: decision-scan, disposition: fixed}
  - {id: X3, severity: Low, aim: deliverable, fix_induced: true, component: decision-scan, disposition: fixed}
  - {id: X4, severity: Low, aim: instrument, fix_induced: true, component: self-test, disposition: fixed}
```

Severity mapping: a review's MAJOR is `High`, MINOR is `Low`. **All four were caused by the r1 fold.** Three are in
`decision-scan` (the r1 component of X1/F3); a fold-caused finding there in round 3 is THRASHING and arms Phase 6.
So this fold prefers REMOVING machinery to adding it.

## What changed

- **The `<details>` auto-open is REMOVED, not patched (X1, X2).** r1 added `open` to every `<details>` around a
  decision. It failed both ways Codex found: a quoted ` open ` in another attribute (`title=" open "`) read as the
  attribute, and a named accordion group (`name="g"`) shows only one section on load whatever the markup says. Both
  are properties of opening, so the opening is gone — the regex, the per-decision `<details>` list carried through the
  scan, and its edit loop. A mark ON a `<details>`, or inside one anywhere but its first `<summary>`, is now CANNOT
  RUN: *"it is in a <details> outside its <summary>, which is collapsed until the reader opens it — move the mark
  outside the <details>, or onto its <summary>"*. Refused even with `open`, because a named group can close it. A
  grep of all 34 fragments under `docs/explainers/` found no mark inside a `<details>` (the walkthrough has no
  `<details>` at all), so no fragment moved.
- **The ancestor stack closes a `<p>` the way HTML does (X3).** A start tag from the HTML "close a p element" set
  (`div`, `p`, `ul`, `ol`, `section`, `h1`–`h6`, `details`, `pre`, `blockquote`, `li`, `hr`, …) pops an open `p` in
  button scope. Codex's exact fragment, `<p hidden>Hidden paragraph<div data-decision>Visible sibling</div>`, now
  counts 1. Two places it stays open, both erring toward a refusal: a scope boundary (`button`, `table`, `td`, …),
  and a hidden FORMATTING element (`b`, `i`, `a`, …) above the p — the browser re-opens that one around what follows,
  `hidden` and all. `table` is left out of the closing set (it closes a p only in no-quirks mode).
- **The contrast check refuses what it cannot fully evaluate (X4).** `_hex_lum` accepts `#rgb`, `#rrggbb`, and the
  alpha forms only when opaque (`#rgbf`, `#rrggbbff`); anything else — alpha below `ff`, `rgba`/`hsla`/`rgb()`, a
  named colour, `var()`, an empty value — is a `ValueError`, the ratio becomes 0 and the readability case goes red.
  Codex's appended-`00` mutation is a manifest entry now (one colour pair; the all-colours version was run on a temp
  copy and goes red through the same case).
- **Filed backlog #615:** nothing checks that a page marks EVERY decision it asks (r1's NOT DONE, now a row).

Self-test 222 → 224 (the `<details>` OPENS case replaced; the implicit-`</p>` case and the contrast-refusal case
added), 224/224 under Python 3.12 and 3.14. Manifest 77 → 86 (the auto-open mutation deleted with its code; 10 added:
four on the `<details>` refusal, three on the implicit `</p>`, two on the contrast refusal, and Codex's `00`; one r1
entry re-anchored onto the narrowed loop tuple). All 34 fragments re-composed on both interpreters: the 33
decision-free pages are byte-identical to master's composer (generation stamp normalised), the walkthrough reads
13 / 2 remaining / 11 answered and is identical to the r1 composer's output.

## Not done

- No check makes a fragment mark EVERY owner decision it contains — filed as backlog #615.

Round 3 alternates: ONE half (Claude).
