Reviewed head: 02795757f65a07ec4183c186f4418e1f6572105f

# goal-tree-superseded (backlog #484, PR #480) — round 1 — Claude half

Reviewed range: `origin/master...02795757` (branch `build-484`).

Method: read the full diff and the backlog #484 row. Ran `python3 scripts/goal-tree.py --self-test`:
176/176 passed. Ran `row_fates` over the REAL `docs/backlog.md` and over eight constructed backlogs.
Ran `derive_thread` over seven constructed sources. Applied four mutants to a scratch copy of
`scripts/` and ran the self-test against each. No git writes except this file and its verdict, and no
Postgres. Everything marked EXECUTED was run. Anything else is labelled UNVERIFIED.

---

## H1 — High — any mention of the word in the Status cell marks the row, and the PR's own row is now ✖ withdrawn

**Where:** `scripts/goal-tree.py:126` (`WITHDRAWN_RE = \bWITHDRAWN\b`), `:125`, and `:568-572`
(`row_fates` searches the whole Status cell).

**Input (EXECUTED, the real backlog at this head):** `row_fates(docs/backlog.md)` returns

```
405 ('superseded', 'superseded → backlog #481 (method refuted, goal moved)')
484 ('withdrawn', 'withdrawn')
```

Row 484 is this PR's own row. Its Status cell is `✅ **FIXED 2026-11-02, PR #480** — ... `WITHDRAWN`
prints ✖ withdrawn ...`. The cell describes the mechanism, so the mechanism marks the row. Any thread
naming `backlog #484` would print `✖ backlog #484 ... — withdrawn` for a fix that shipped. The
self-test's only "title is not the Status cell" negative does not cover this, because here the word
IS in the Status cell.

Status cells are append-only, so this is a class and not one row. Each of these constructed cells is
EXECUTED as `withdrawn`:

- `🟠 OPEN — NOT WITHDRAWN, despite r2` (a negation);
- `✖ WITHDRAWN 2026-10-01 ⟳ REOPENED 2026-10-05 — 🟠 OPEN` (a history the row has since left);
- `✅ FIXED — a \`WITHDRAWN\` row prints ✖ withdrawn` (a quotation).

`SUPERSEDED by backlog #M` has the same exposure. One example is `Previously: SUPERSEDED by backlog #12;
reopened`.

**Fix:** read a fate only from a marker that states the row's CURRENT state. One option is a leading
status marker at the start of the cell, or after its last `⟳`. Another is a structured token such as
`⟦fate: superseded → backlog #M⟧` or `⟦fate: withdrawn⟧` in the `⟦kind: …⟧` style the rows already use.
Add the three inputs above as negatives, plus row 484's actual Status cell.

## M1 — Medium — the real backlog's "SUPERSEDED" rows are not read, so the FAILS-IF still holds for them

**Where:** `scripts/goal-tree.py:125`. The regex requires the exact phrase `SUPERSEDED by backlog #N`,
uppercase and with a pointer.

**Input (EXECUTED, the real backlog):** rows 124, 125, 127, 189 and 213 have Status cells that read
`✅ **SUPERSEDED 2026-10-26 (audit)** — …`. Row 327 reads `… superseded by backlog #328/#329`. None of
them appears in `row_fates`. Constructed: `✅ **SUPERSEDED 2026-10-26 (audit)**` returns `{}`, and
`closed, superseded by backlog #12` returns `{}`. Backlog #484's FAILS-IF is *"a thread whose backlog
row says SUPERSEDED or WITHDRAWN prints ✅"*. A thread naming row 189 with its PR merged prints ✅
today. No thread in `docs/goal-threads.md` names these rows yet, so the defect is latent rather than
on the page. The PR's docs (`docs/goal-threads.md:17-18`, the command file) advertise only the exact
phrase, but the row's FAILS-IF does not.

**Fix:** the same structured marker as H1 fixes both. Without one, either narrow the FAILS-IF to the
exact phrase or recognise a bare current-state `SUPERSEDED` and print "superseded (no forward
pointer)". A bare-word match on its own would misfire on row 208 (`the text below … is SUPERSEDED`)
and row 48 (`SUPERSEDED BY EVENTS`), which is why the marker is the better fix.

## M2 — Medium — one fated ref overrides a live ref and an open PR on the same leaf

**Where:** `scripts/goal-tree.py:276-279` (`if fated:` with any fated row).

**Input (EXECUTED, `derive_thread`):**

- `- fix · backlog #10, backlog #11 · f`, where #10 is `SUPERSEDED by backlog #12` and #11 is `🟠 OPEN`:
  `('superseded', 'superseded → backlog #12 … · no PR names it yet')`. Live row #11 vanishes behind ✖.
- `- fix · backlog #10, PR #21 · f`, where PR #21 is open: `('superseded', '… · PR #21 open · NO
  CHECKS')`. The glyph is ✖ while a PR is open.

Everywhere else the module's rule for several refs is that the worst state wins: *"a thread is merged
only when ALL its PRs are"* (`PRECEDENCE`). Here one row's ✖ is final for the whole leaf, which
contradicts that rule. A reader scanning glyphs sees "closed" on a leaf with open work.

**Fix:** apply the fate only when every backlog ref is fated, or let `open`/`inflight` beat it, which
keeps ⏳ with the superseded note in the detail. Either way, state the choice and pin it with a case.

## M3 — Medium — four mutants of `derive_thread`'s new block survive the self-test

**Where:** `scripts/goal-tree.py:276-279`. Every new case has exactly ONE backlog ref, so nothing
combines refs. **EXECUTED on a scratch copy, each 176/176 green:**

1. `state = fated[0][0]` (the first fate wins, not "superseded beats withdrawn across rows"). The
   case "SUPERSEDED beats WITHDRAWN" tests one cell in `row_fates`, never two rows in `derive_thread`.
   The constructed `backlog #10 (WITHDRAWN), backlog #11 (SUPERSEDED)` leaf is `superseded` only
   because of the `any(...)`, and no case exercises it.
2. `dict.fromkeys` dedupe removed (two rows with the same fate print the detail twice).
3. `if fated and len(fated) == len(rows)` (M2's alternative: no case decides between the two).
4. `if fated and state != "open"` (no case pins the precedence against an open PR).

**Fix:** add a two-row leaf with distinct fates, a two-row leaf with one fated row and one live row,
and a fated row with an open PR. Then add mutants 1, 3 and 4 to `scripts/mutations/goal-tree.json`.
Mutants 3 and 4 depend on which behaviour M2 chooses.

## L1 — Low — the second table's row numbers collide with the Items table

**Where:** `row_fates` keys `fates` by `r["num"]` across every table `gen-backlog-page.parse` returns.
`## Found during testing` (`docs/backlog.md:475`) has rows 9, 10 and 11, which are also Items rows.
Constructed (EXECUTED): a `| 10 | **t** | ✖ WITHDRAWN |` row in that table yields `{10: withdrawn}`, so a
`backlog #10` leaf, which means Items #10, would print ✖. Nothing in that table is withdrawn today.
**Fix:** read fates from the `## Items` table only, or key them by (section, num).

## L2 — Low — a leaf naming a row that does not exist silently keeps the merge's ✅

**Where:** `:276`. `- fix · backlog #99, PR #20` with no row 99 returns `('merged', 'merged aaaa111')`
(EXECUTED). A typo in a ref therefore drops the check without saying so. **Fix:** a ref to a row the
parser did not return is ❓ or adds a note to the detail.

## L3 — Low — the detail text claims a reason the row may not give

**Where:** `:570`. Every superseded row prints `(method refuted, goal moved)`, which is true of
backlog #405 and is not implied by `SUPERSEDED by backlog #M` in general. **Fix:** print
`superseded → backlog #M`, and leave the reason to the row.

---

Checked and found sound: escaped `\|` inside both the title and the status (EXECUTED, read correctly);
the second table's three-column layout (EXECUTED, its status is read); `(was 🟠)` is not matched. An
unreadable or partly unreadable backlog yields ⚠ for every backlog-ref leaf, and no ✅. Both
`collect` paths that set `fates_error` also leave `errors["backlog"]` set, so the snapshot is not
logged. A source with no `fates` key fails closed to CANNOT RUN (EXECUTED). Superseded + in flight +
waits stays ✖ with both notes in the detail (EXECUTED).

H1 is live on this PR's own row. M1 and M2 mean the glyph still misleads in cases the row's FAILS-IF
covers.

VERDICT: NOT CONVERGED
