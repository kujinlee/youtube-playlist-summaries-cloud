# Round 1 — `617-bind-ci` (backlog #617 part 1) — coordinator — ⟳ NOT CONVERGED; all folded or filed

```yaml
round: 1
fixes_nontrivial: true
subject: 617-bind-ci
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: false, component: contract-parser, disposition: fixed}
  - {id: XM2, severity: Major, aim: deliverable, fix_induced: false, component: contract-parser, disposition: fixed}
  - {id: Xm3, severity: Minor, aim: deliverable, fix_induced: false, component: contract-parser, disposition: fixed}
  - {id: Cm1, severity: Minor, aim: prose, fix_induced: false, component: docstring, disposition: fixed}
  - {id: Cm2, severity: Minor, aim: deliverable, fix_induced: false, component: contract-parser, disposition: partly-fixed-rest-filed}
  - {id: Cm3, severity: Minor, aim: deliverable, fix_induced: false, component: contract-parser, disposition: fixed}
  - {id: Cm4, severity: Minor, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
  - {id: Cm5, severity: Minor, aim: structure, fix_induced: false, component: contract-parser, disposition: filed}
  - {id: Cm6, severity: Minor, aim: deliverable, fix_induced: false, component: tests, disposition: fixed}
```

Reviewed `fb0c31f6` (both halves). Both ran the self-test (40/40) and the mutation slice (28/28) themselves.

- **XM1** a `#` comment naming the shard file counted as THE write (Codex reproduced 40/40 green over a renamed redirect).
  Fixed: `_uncomment` drops `#` lines and ` #` tails, and only a redirect target (`> "…/shard-$V.txt"`) counts.
- **XM2** `merge-multiple: true` under the step's `env:` passed while `with:` said false. Fixed: it counts only as a
  DIRECT child of the step's single `with:` (`_children`).
- **Xm3 / Cm2** false reds: a quoted job index, a quoted `'true'`, an inline comment, `shard-"$SHARD_INDEX".txt` — now
  accepted (one case). **Filed** (backlog #617 row): a step written `- if:` before `name:`, `${SHARD_INDEX:-0}`, and
  Claude's order point (the contract runs before `read_flaky`, so a FALSE red withholds filing present names).
- **Cm1** the docstring claimed the whole hand-over; it now says the two links it checks and that other drifts are red
  through `read_flaky`'s missing-file report.
- **Cm3** the job-index variable was read from ANY step; now from the step that writes the file.
- **Cm4** three hand-made survivors (`<= ind`→`< ind`, two download steps accepted, the `$` anchor — the last moot after
  `fullmatch`) → two cases + two mutants. **Cm6** the "second write" case was a comment → a real redirect.
- **Cm5** the block walk duplicates `step_run_block`'s — **filed**.

After the fold: self-test 46/46; mutation slice 34/34 killed, each by its named case (2 fixture survivors found on the
way: each fixture was red for a SECOND reason that masked the clause — both moved). Fixture variation and self-test
counts green. ⚠ The Claude half's verdict record lists a dirty overlay of my in-progress fold (it recorded while I was
editing); its verdict is NOT CONVERGED, so it vouches for nothing.

Round 2: Codex only (alternation). REVIEW GAP: claude — alternation.
