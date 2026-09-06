# The gate reads the store, not a patch — so it can finally judge a reference

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

**Backlog #82.** **v1, 2026-09-06.** The referential half; the syntactic half closed 2026-09-01.

**The gate can judge a header's SYNTAX and never its REFERENCES.** Measured after that fix:
`[resolved: nonsense]`, `[resolved: 2026-09-01/99]` and `[resolved: 2026-13-45/1]` all return
`header_error -> None` while `gen-dashboard.parse_entries` sets *"names no entry in this file"*.

⚠ **Header order is load-bearing** — `check-anchors.py:61` sets `HEAD_LINES = 10`.

---

## 1. Why no regex closes this

Whether `2026-09-01/99` names a real entry is a property of the **whole store**, and
`added_entry_problems` only ever sees a **patch**. No tightening of `FLAG` reaches it. The gate is
not insufficiently strict; it is looking at the wrong object.

**And the obvious fix is forbidden.** Having the gate import `gen-dashboard.parse_entries` inverts
a written rule — `_gate_module`'s docstring, *"a GATE must not import the thing it guards"*. A lazy
import works technically, which is exactly why the rule has to be honoured deliberately rather than
discovered.

---

## 2. The relocation — one grammar, arrow preserved

`parse_entries` (139 lines, `gen-dashboard.py:469-607`) moves into `check-dashboard-entry.py`,
which already owns `HEADER`, `FLAG`, `BLOCK`, `header_error`, `valid_date`, `decisions` and
`decision_errors`. `gen-dashboard` imports it through the `_GATE` handle it already uses for
`header_error`/`FLAG`/`HEADER`. The dependency arrow keeps pointing **page → gate**.

**What travels with it, and why that is not scope creep.** `parse_entries` calls exactly three
things it does not define: `header_error` and `valid_date` (**already in the gate**) and
`_first_sentence` (`gen-dashboard.py:127`). The last one moves too.

⚠ **`_first_sentence` has TWO callers with different jobs** — `parse_entries:584` sets an entry's
title, and `:207` re-applies it while rendering. That is precisely why it must live in ONE place:
the render at `:196-207` documents that it derives the headline *by re-applying `_first_sentence`,
not by prefix-matching*, so a second copy would break the very identity that comment relies on.
`gen-dashboard` imports it back, exactly as it already imports `header_error`.

**Not moving:** everything that renders. The gate gains the entry MODEL, not the page.

---

## 3. The judgement — only errors the branch ADDED

Relocation alone would make the gate able to see referential errors and simultaneously make it
**unusable**: a store that already contains one broken entry would fail every future branch,
including branches that never touch the store. A gate everyone learns to override is worse than no
gate — the verdict `#56` records from measurement and `#98` now cites.

So the gate parses **two** stores and compares:

* **base** — `git show <base>:docs/dashboard-entries.md`
* **head** — the store as this branch leaves it

and reports the **set difference**. An error present in both is pre-existing and is **not** this
branch's to fix.

### 3.1 What identifies an error, and why not the id

The obvious key is `(entry id, message)`. **It is wrong**, and this is the trap worth naming: ids
are POSITIONAL (`YYYY-MM-DD/N`, `N` counting entries that share a date in file order), so appending
one entry can renumber later ones. Keyed by id, a pre-existing error would appear "new" the moment
anything shifted it — the false positive that gets a gate disabled.

**The key is `(header line text, message)`.** The header is what the error is ABOUT, it is stable
under renumbering, and a duplicated header line means duplicated headers, which is its own problem
the page already surfaces.

### 3.2 When the base cannot be read

A first commit, a shallow clone, a renamed file: `git show` fails. That is **CANNOT RUN for the
diff, not a pass and not a block** — the gate falls back to reporting errors in HEAD only if HEAD
has any, and says plainly that it could not establish a baseline. Silence here would mean a branch
could add a broken reference whenever the base lookup failed, which is the fail-open shape this
project has paid for repeatedly.

---

## 4. Falsifiers

| # | Fails if |
|---|---|
| **F1** | `[resolved: nonsense]`, `[resolved: 2026-09-01/99]` and `[resolved: 2026-13-45/1]` added by a branch each make the gate REFUSE — the three shapes measured to pass today |
| **F2** | the SAME broken entry present in base and head produces **rc=0** — a pre-existing error is not this branch's |
| **F3** | a branch that appends a VALID entry after a pre-existing broken one is rc=0, **even though every later id renumbers** — the positional-id trap of §3.1 |
| **F4** | `gen-dashboard` and the gate return byte-identical `parse_entries` output for the live store — one grammar, not two that agree today |
| **F5** | an unreadable base is reported as CANNOT RUN naming the reason, never as a silent pass |
| **F6** | the gate does **not** import `gen-dashboard`: `grep` finds no such import, and the page still imports the gate |
| **F7** | a valid `[resolved: <id>]` naming a real entry is accepted — the check refuses references, not the feature |

F3 is the one a reasonable implementation gets wrong, and F4 is the one that makes the row's claim
("one grammar") true rather than asserted.

---

## 5. Out of scope

* **#78 half (2)** — when the gate runs (`pull_request`-only). Re-read 2026-09-06: a CI-timing
  preference, not a reader-facing defect.
* **The decision grammar** (`decision_errors`) stays renderer-enforced; wiring it into the gate is
  #81 tier 2, HELD by user decision.
* **Rendering.** The gate gains the entry model and nothing that draws.
