# Architecture review — the node-tree spec's migration slices

- **Date:** 2026-11-23
- **Convened on:** THRASHING — component `migration-slices` of the spec review `goal-node-tree-spec` carried
  findings caused by the previous round's fold in round 2 (XM1, N2) and in round 3 (F2, F3, F4, F6).
- **Subject:** `docs/superpowers/specs/2026-11-23-goal-node-tree-design.md` §5.1 (slices S1–S5) and §5.1.1 (the
  page-trigger inventory), and `docs/adr/0016-names-live-in-one-node-tree.md`, at commit `256c7b4f`
  (branch `goal-node-tree-spec`).
- **Reviewer:** Claude (Fable 5.2), one agent, no second half.
- **Legend:** **[M]** = a command I ran, or code I read, at `256c7b4f`. **[I]** = inferred, not run.
- **Raw output:**
  `/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/ntr-p6/`
  (`predicate-file.txt`, `predicate-symbols.txt`: the two searches of §4).
- **Not reopened:** the owner's decisions D1–D8, the owner questions Q11–Q13, and every ADR.

---

## 1. Verdict

**The class is real and a redesign removes it. Applied to the spec in the same change as this review.**

| Question | Answer |
|---|---|
| Is the coordinator's reading right? | **Yes, with one addition.** The spec lists by hand the readers of each retired name and the triggers of each page, claims each list complete, and gates a slice on the list. Every round found another member. The addition: half of the class (the triggers) governs a mechanism that cannot do what the spec assumed. |
| Thrashing or prose floor? | **Thrashing.** All four r3 findings are Minor, yet each repeats the defect behind r1's Blocker (XB1) and r2's Major (XM1) — an enumerated list standing in for the real set. One change of shape retires every one of them; that is what separates thrashing from a prose floor. |
| Can a redesign remove it? | **Yes.** The trigger inventory is deleted, because no new trigger is owed. The reader lists stop being the gate; a search of the whole tree is. |
| New machinery | **None.** One `git grep` per retired name in the slice's FAILS IF, and one existing rule quoted from `scripts/regen-pages.py`. |
| Needs the owner | **Nothing.** No decision or ✍ question changes. |

---

## 2. The class, with per-finding evidence

**The defect:** a slice says "X is retired and every reader below is updated", then lists the readers; or "this
page gains a source and these triggers follow", then lists the triggers. The list is written from a search run
once, and the slice's FAILS IF tests the list, not the tree.

| Round | Finding | What was missing from which list | Caused by the previous fold? |
|---|---|---|---|
| r1 | XB1 (Blocking) | S2 named 5 readers of `docs/anchors.md`; a grep found 21 | no (the draft) |
| r1 | CM3 (Medium) | the page sources and hook lists that follow the new derivations | no (the draft) |
| r2 | XM1 (Medium) | the `/goals` hook's `case` list lacked the new source | **yes** — the r1 fold added the S4 routing |
| r2 | N3 (Medium) | three rules of `check_cross` that read the deleted registry | no |
| r2 | N2 (Medium) | not this class: an order defect in the rename of `harness-speed` | yes |
| r3 | F1 (Minor) | the callers of the value `ANCHORS_MD` produces, and two self-test assertions | no |
| r3 | F2 (Minor) | two pages absent from "every trigger of every page" | **yes** — the r2 fold added §5.1.1 |
| r3 | F3 (Minor) | two reads absent from a sentence listing one generator's reads | **yes** |
| r3 | F4 (Minor) | one hook and one slice absent from the sentence naming the hook edits | **yes** |
| r3 | F6 (Minor) | a status message that follows the S3 routing | **yes** |

Sources: `docs/reviews/coordinator/goal-node-tree-spec-r1-coordinator.md` (rows XB1, CM3),
`docs/reviews/coordinator/goal-node-tree-spec-r2-coordinator.md`, `docs/reviews/claude/goal-node-tree-spec-r3-claude.md`.
Nine of the ten rows are one defect. Three consecutive rounds; the last two fix-induced.

**The class is still live at the reviewed commit [M].** One search, run for this review, finds what the fourth
round would have reported: `docs/backlog.md` names `docs/anchors.md` in 9 rows and `docs/marketplace/inventory.json`
in 3 places, and S2 puts `docs/backlog.md` in neither its "prose to update" list nor its "left as history" list.
S2 also lists `regen-pages.py` as a script it touches; that file contains no reference to the registry
(`git grep -i anchor -- scripts/regen-pages.py` prints nothing). The list is wrong in both directions.

---

## 3. What the code says about page triggers

The round 2 fold built §5.1.1 on an assumption: when a page starts to read a file, an edit of that file must
rebuild the page. **That is not how pages are built since backlog #408 [M].**

- `scripts/regen-pages.py` docstring: *"EVERY PAGE IS BUILT FROM A FRESH `origin/master`, NEVER FROM THE CALLER'S
  WORKING TREE (backlog #408)."* `fresh()` (`:431`) is documented as *"The ONE way a page is built"*.
- Each edit hook says the same about itself. `.claude/hooks/regen-goals-page.sh`: *"the page shows MASTER, not
  the edit that fired this hook"*. `after_edit_line` (`scripts/regen-pages.py:743`) prints *"this edit appears
  after it merges"*.
- A merge rebuilds every page whatever was edited: `pages_for` (`:594`) returns `sorted(pages)` for a command
  containing `gh pr merge`, and `pages` is `explainer-serve.REGENERABLE`, *"ONE list: a page added there is
  rebuilt on merge without touching this file"*.

So an edit trigger never shows the edit. What it does is bring one page up to the current `origin/master`,
which matters only when master moved without this session running `gh pr merge`. That benefit does not depend
on WHICH file was edited, so no source list can be "complete" or "incomplete" for it.

Consequences for the findings:

| Finding | Under the measured rule |
|---|---|
| r2 XM1 — `/goals` would miss a rebuild on a `docs/goal-threads.md` edit | no harm: the edit reaches `/goals` when it merges, and the merge rebuilds `/goals` |
| r3 F2 — `/backlog-table` unrebuilt on a `docs/features.md` edit | no harm, same reason. The stranded `epic:` parent F2 describes is caught by G3 in CI (`check-features.py`), before any merge |
| r3 F3, F4, F6 | they describe text that no longer exists once §5.1.1 goes |

The round 2 coordinator had already found half of this (XM1 "PARTLY ... S4's `pages_for` change WOULD have
rebuilt `/goals`") and then added the inventory anyway. The inventory is the fix-induced structure.

---

## 4. Options

| | Option | Removes the class? | Cost | Verdict |
|---|---|---|---|---|
| A | Keep both lists, narrow the claim from "every" to "the pages listed" (round 3's suggestion) | **No.** The slice still gates on "any file in the S2 reader list", so a reader outside the list passes | none | rejected |
| B | One declared-reads table per generator; hooks, `pages_for` and `PAGE_SOURCES` derive from it; a test fails on an undeclared read | For triggers, yes | **High.** A read tracer over 5 generators, and 4 shell `case` lists plus 2 Python structures re-based. `PAGE_SOURCES` is literal files on purpose: its comment (`scripts/explainer-serve.py:246-256`) records that widening it turned its self-test red twice | rejected for this design: it would build machinery for a trigger that cannot show the edit (§3). Filed as backlog #710, as a question about the hooks themselves |
| C | **Triggers: the design adds none**, and says why (§3). **Readers: each slice that retires a name is gated by a search of the whole tree**, with the history set written once as path patterns; the reader list stays as a draft-time lead, labelled not exhaustive | **Yes**, both halves | one `git grep` per retired name | **recommended** |
| D | Register the retired name as a token in `check-canonical-source.py` | Partly | changes a shared guard | rejected: that guard passes any file that CITES the canon, so a reader that cites ADR-0016 passes; its `EXEMPT` (`:248`) is two paths shared by every canon, and the history set here is seven; it does not read `*.json` (`SEARCHED`, `:259`) |

Also checked and not a fit [M]: `check-doc-citations.py` reads `path:line` citations in a diff, and a bare path
is not one; `check-docs.py`'s living-link check reads Markdown links only, and round 3 found no living document
links the registry that way.

### Option C, measured [M]

The search, at `256c7b4f`, with the history set as pathspecs:

```
git grep -n -F -- 'anchors.md' -- . ':!docs/reviews' ':!docs/superpowers' ':!docs/explainers' \
  ':!docs/dashboard-entries.md' ':!docs/backlog.md' ':!docs/marketplace/*.json' \
  ':!docs/adr/0016-names-live-in-one-node-tree.md'
```

| Measure | Result |
|---|---|
| lines / files it prints today (the work S2 owes) | 48 lines in 19 files |
| the same for the symbols `parse_registry`, `registry_anchors`, `ANCHORS_MD`, `anchor_slugs` | 18 lines in 5 files |
| r1 XB1's readers | all printed |
| r2 N3's three `check_cross` sites | `:284`, `:289`, `:297` printed; `:253` printed |
| r3 F1's seven cited lines | 5 printed (`check-features.py:461`, `gen-backlog-page.py:1306`, `:3019`, `:4097`, `:4424`); the other 2 (`check-features.py:306`, `:316`) use the local `declared`, assigned at the printed `:297` |
| both hooks' `case` arms and comments | printed (`regen-goals-page.sh` 1 line, `regen-features-page.sh` 3) |

The token is `anchors.md`, not `docs/anchors.md`: three readers build the path as `DOCS / "anchors.md"`
(`scripts/gen-features-page.py:745`, `scripts/gen-goals-page.py:435`, `scripts/gen-backlog-page.py:4375`).

**FAILS IF, as the slice now states it:** after S2 the search prints a line. It prints 48 today, so the check
is not vacuous.

---

## 5. What was applied

| Where | Change |
|---|---|
| spec §5.1 S2 | the reader list is relabelled a draft-time lead; the gate is the search; `docs/backlog.md` joins the history set by name; one sentence states what replaces the registry's slug set at every former consumer (F1) |
| spec §5.1 S2, S3, S4 | every added edit trigger is removed: no hook gains a source, `pages_for` gains no route, `PAGE_SOURCES` gains nothing. S2 still removes `docs/anchors.md` from each, forced by the search |
| spec §5.1 FAILS IF | the dispatcher test and the "one edit dispatcher per page" rule are deleted |
| spec §5.1.1 | replaced by the measured rule of §3, in 3 short paragraphs |
| spec §5.1 S3 | says which slice gives the trunks their slugs (F5) |
| ADR-0016 | its FAILS IF line for the deleted registry names the search |
| `docs/backlog.md` | backlog #710: the per-source edit hooks and `PAGE_SOURCES` are hand-kept copies of what each generator reads, and since backlog #408 an edit hook cannot show the edit |

The six round 3 findings are dispositioned one by one in
`docs/reviews/coordinator/goal-node-tree-spec-r3-coordinator.md`.

---

## 6. What this does NOT cover

- **A reader that spells the name another way.** `"anchors" + ".md"`, or a path read from configuration, is not
  printed. No such reader exists today [M: a search of `scripts`, `.claude` and `.agents` for the bare word `anchors`
  as a quoted path part prints only the `anchors:` FIELD name, 3 lines in `check-features.py`]; one
  added later would read a deleted file, and whether that fails loudly depends on that reader.
- **The history set is a judgment, written once.** `docs/backlog.md` bodies and the marketplace `*.json` notes
  keep the old name. That matches §2.5.1's last row (prose and history are not checked) and leaves Q4
  (`docs/dashboard-entries.md`) with the owner.
- **Slug retirement in prose.** A renamed slug in a structured field is caught by G1–G5. In prose it is not
  searched for, by the spec's existing decision.
- **Stale pages after a merge made elsewhere.** A merge on GitHub, or from another session, rebuilds nothing
  here until an edit hook fires or Refresh is pressed. Unchanged by this design; part of backlog #710.
- **The `/_stale` banner.** `PAGE_SOURCES` will name fewer files than the pages read (it already does, by its
  own comment). The banner is not made truer by this design.
- **The plan.** The line-number leads in S2 are from `256c7b4f`'s base. The plan re-runs the search at its own
  base; that is why the list is no longer the gate.
- **Round 2's N2.** An ordering defect, not a list defect. This redesign does nothing for that kind; the
  "every slice ends green" FAILS IF is what catches it.
