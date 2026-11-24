# Round 2 — `decision-buttons` (PR #628) — coordinator — ⟳ NOT CONVERGED; every finding FIXED

```yaml
round: 2
fixes_nontrivial: true
subject: decision-buttons
halves:
  codex: ran
  claude: gap
findings:
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: sent-state, disposition: fixed}
  - {id: C2, severity: High, aim: deliverable, fix_induced: true, component: sent-state, disposition: fixed}
  - {id: Cm1, severity: Medium, aim: deliverable, fix_induced: false, component: cases, disposition: fixed}
```

REVIEW GAP: claude — alternation (round 2 is the Codex half; the Claude half reviews round 3)

Codex (`docs/reviews/codex/decision-buttons-r2-codex.md`: 2 Major, 1 Minor) reviewed head `aa459285`. I checked each
finding in `DECISION_JS` (`scripts/brief-compose.py`) before fixing it. Each fix has a self-test case. I ran a
mutation that reverts the fix on a scratchpad copy of `scripts/`, and the case went RED each time. The four mutations
are now in `scripts/mutations/brief-compose.json`, and the pin in `expected_mutations.py` moved from 94 to 98.

C2 is marked `fix_induced: true`. Round 1's F5 fix put the box AFTER the heading so the tray would not read it.
That placement left the tray's own `.askbtn` inside the heading for `questionOf` to read.

| Finding | Disposition | Evidence |
|---|---|---|
| **C1** — the key hashed the question cut at 400 characters, and an unlabelled decision has no other identity | **fixed** | Confirmed: `questionOf` returned `norm(out).slice(0, 400)`, and `key()` hashed that. The hash now covers the FULL normalised question. The posted quote is still cut at 400, so the post shape does not change. Two decisions with the same label (less its ordinal) and the same question are now told apart by their occurrence among THAT pair (`:2`, `:3` …). The global position is not used. The key is computed once per tag, at load, before anything else edits the page. New case "a reload shows 'sent' only on the decision answered — not its identical twin, nor one differing only after character 400, moved": two unlabelled `Same?` decisions, plus two 421-character questions that differ only at the end. The first of each pair is answered, and the reload is a recompose that swaps the long pair. Mutations: put back `.slice(0, 400)` → RED. Drop the occurrence suffix → RED. One wrinkle: the 400-cut mutation SURVIVED the first version of the case. With the cut restored, the occurrence index alone told the long pair apart, as long as they stayed in order. That is why the reload swaps them. |
| **C2** — on a heading decision, `questionOf` read the tray's `.askbtn` ("ask"), which is added after the decision script runs | **fixed** | Confirmed: in `compose()`, `DECISION_JS` comes before the tray `script`, and the tray appends `<button class="askbtn">ask</button>` to every h2/h3. That makes the click-time key differ from the load-time key, and the quote ends in "ask". `questionOf` now reads the host's text at any depth with the tag removed, along with every `BUTTON`, `.ex-pick` and `.askbtn`. Because the key is computed once at load, it is the same at click as well. The harness gained `trayHeadings()`, the tray's heading loop as committed trays have it, minus styles and listeners, and it runs AFTER the pick script. New case "with the tray run, a heading decision is 'sent' after reload and its quote has no 'ask'". Mutation: put back the old exclusion (`.ex-pick` only) → RED, because the quote ends `Heading q?ask`. Bound: the stand-in is not the real tray script, and the harness DOM cannot run the full ~6 KB tray. The case covers the tray's heading contract (a button with text `ask`, appended to h2/h3). It does not test the tray's code. |
| **Cm1** — the heading-placement case did not prove "after" | **fixed** | New case "a heading decision's box is the heading's NEXT element sibling", which asserts `h3.nextElementSibling === box`. Mutation: `insertBefore(box, host)` (box BEFORE the heading) → RED. The old case survives that mutation, which matches what Codex reported. |

## Gates (worktree, after the fold)

- `python3 scripts/brief-compose.py --self-test`: 248/248, up from 245 (three new cases). The USAGE docstring count was updated.
- `python3 scripts/ask_answerer.py --self-test`: 124/124.
- `python3 scripts/check-explainer-delivery.py`: rc 0.
- `python3 scripts/check-docs.py`: OK.
- `python3 scripts/check-plan-code.py --mutate . --only scripts/brief-compose.py`: 98 mutations, 98 killed, 98 attributed to the case each names, 0 survivors, and the re-control passed. This covers ONLY brief-compose, a diagnostic slice and not the full sweep.
