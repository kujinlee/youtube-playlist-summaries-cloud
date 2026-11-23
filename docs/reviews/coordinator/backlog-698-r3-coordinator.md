# Round 3 — `backlog-698` — coordinator — the `<details>` fix edited a reading in place; track open elements, never patch a view

```yaml
round: 3
fixes_nontrivial: true
subject: backlog-698
halves:
  codex: "GAP: alternation"
  claude: ran
findings:
  - {id: F1, severity: Major, aim: deliverable, fix_induced: true, component: corpus-views, disposition: accepted}
  - {id: F2, severity: Minor, aim: deliverable, fix_induced: false, component: corpus-views, disposition: accepted}
  - {id: F3, severity: Minor, aim: deliverable, fix_induced: true, component: mutations, disposition: accepted}
  - {id: F4, severity: Minor, aim: deliverable, fix_induced: false, component: cannot-see-doc, disposition: accepted}
  - {id: N1, severity: Nit, aim: deliverable, fix_induced: false, component: cannot-see-doc, disposition: accepted}
  - {id: N2, severity: Nit, aim: deliverable, fix_induced: false, component: renderer-call, disposition: accepted}
```

The Claude half reviewed 7cf29bb4, the round-2 fold (`git diff a0af8a4e..HEAD`): [`claude/backlog-698-r3-claude.md`](../claude/backlog-698-r3-claude.md). Verdict NOT CONVERGED.

REVIEW GAP: codex — alternation

**What held:**

- the self-test passes 63/63;
- the real build passes `--out` + `--check` under node 18, 20 and 22, with no stderr;
- six mutations die on their named case in a full external clone, and all 77 mutation anchors resolve exactly once;
- the 14 CI `check-*` steps the reviewer ran pass;
- the letters-only view adds 0 false hits over 3,498 benign files.

## Dispositions

- **F1 (MAJOR, fix-induced): an unclosed `<details>` inside a container hides a visible run. ACCEPT.**
  - The cause: round 2 changed the tight and loose readings in place, which broke the add-only rule.
  - Fix: give `_Visible` a stack of open elements, so a container's end tag closes every element opened inside it, as the browser does.
  - Case: the reviewer's reproducer, refused as it was on a0af8a4e, red on 7cf29bb4 first.
  - **Fixed in 85e4c989.**
- **F2 (MINOR): the same runaway with `hidden` or an unshown element, e.g. `<div><span hidden>x</div>`. ACCEPT.** The element stack closes it. Add a case.
  - **Fixed in 85e4c989.**
- **F3 (MINOR, fix-induced): two re-attributed mutations are not equivalent.** They are "source quote fragmented in raw Markdown" and "source quote read only in `read`". ACCEPT.
  - Add a case with hidden text inside a source quote, and point those two mutations at it.
  - Narrow the `views` docstring's "no run-level case can tell the readings apart".
  - **Fixed in 85e4c989.**
- **F4 (MINOR): full-width and mathematical-bold letters are missed. ACCEPT.** Apply NFKC normalisation in `letters_only`, first checking that every group-D fragment is unchanged by it. Add a case.
  - **Fixed in 85e4c989.** It uses NFKD, not NFKC: NFKC composes a decomposed accent and would lose that hit, which breaks add-only. A case asserts both forms leave every group-D fragment unchanged.
- **N1:** give the "294" figure its unit, or replace it with the measured 1,002 (file, fragment) hits over 3,498 files.
  - **Fixed in 85e4c989.**
- **N2:** add one line to the rc-2 list: any warning node prints from its environment makes the run CANNOT RUN, by design.
  - **Fixed in 85e4c989.**

## Thrashing watch

The fix-induced findings fall in a different component in each round:

| Round | Fix-induced findings |
|---|---|
| 2 | X3, in `renderer-call` |
| 3 | F1, in `corpus-views`; F3, in `mutations` |

**Not armed:** no component carries fix-induced findings in two consecutive rounds.

⚠ `corpus-views` is the component to watch. It had findings in rounds 1, 2 and 3, and two of the three fixes produced the next round's finding in it. **If round 4 carries a fix-induced finding in `corpus-views`, Phase 6 arms.**

Round 4 alternates to Codex. It is under the round cap, so its findings are FILED unless a BLOCKER.
