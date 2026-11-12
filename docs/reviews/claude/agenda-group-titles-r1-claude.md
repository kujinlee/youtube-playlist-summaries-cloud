Reviewed head: 86f03d4af03aac7fecd28734a96bed68233ea70f

# PR #559 (agenda-group-titles): round 1, Claude half (adversarial)

Scope: `git diff origin/master...HEAD`, which covers `scripts/goal-tree.py` (`agenda_html` :2001-2003, CSS :2199-2200, cases
:3958-3962, :4147, :4209), `scripts/mutations/goal-tree.json` (re-bound :2976, new entry at the end),
`scripts/mutations/expected_mutations.py` (pin 336 -> 337), backlog #610 and the dashboard entry.

How it was checked: I ran everything below. Each mutation was applied to a COPY of `scripts/` under the session
scratchpad, outside the repo, with `goal-tree.py --self-test` run there. The probe script imported the module from the
worktree and changed no file in it.

## Self-test

`python3 scripts/goal-tree.py --self-test` at the reviewed head prints, as its last line:
`439/439 self-test cases passed` (rc 0). The docstring's count "439 cases" matches.

Manifest: 337 entries name `scripts/goal-tree.py`, which equals the pin. Every entry's anchor occurs exactly once in
the file at head (0 orphaned, 0 ambiguous).

## (1) Can I build an agenda that breaks "a line not starting with a space is a group label"?

Not through the parser. The rule is applied to the ELEMENTS of `agenda_step_lines` (:1600-1610), before the `"\n".join`.
So a newline inside text cannot create a false title: the classification has already been made.

| Input | Path | Observed `<pre>` output |
|---|---|---|
| `## <b>today</b> PR #5` / `- x <i>` | `parse_agenda` | `<span class="ag-when">&lt;b&gt;today&lt;/b&gt; <a href=".../pull/5">PR #5</a></span>` and the step escaped. Escaped and linked |
| `## a\rb` / `- x\ry` | `parse_agenda` (it splits on `\n` only) | `<span class="ag-when">a\rb</span>`, step `  1. ◇ x\ry ...`. HTML turns the CR into a line break, but the break stays INSIDE the span or the step. No line is misclassified |
| `##  g` (when starts with a space), `-  x` | `parse_agenda` | refused, Malformed. `WHEN_RE`/`STEP_RE` (:1120-1121) require `\S` first, so a parsed `when` is never empty and never indented |
| record `when="  indented"`, `when=""`, `text="a\nb"` | hand-written JSON log line; `_agenda_records` admits it (`D admitted 1`) | `  indented` renders as a plain step line (a group that is not a title); `<span class="ag-when"></span>` (an empty title); `a\nb` puts `b` on its own line, unstyled, and NOT as a title |

**L1 (LOW): the log reader admits `when` values the writer never produces.** `_agenda_records` (:1195-1198) checks only
`isinstance(st["when"], str)`. A hand-edited `agendas.jsonl` with an indented or empty `when` breaks the new rule: the
group shows as a step, or as an empty title. Only `parse_agenda` writes the log, so this is not reachable by the normal
path. The text printout had the same blind spot before this PR. Fix, if wanted: validate `when` against `WHEN_RE`'s
group in the reader, or classify by the derived step structure instead of the leading space.

## (2) Did the two adjusted cases lose a property?

- `:4209` ("an agenda with no change-if draws every step..."): `'<pre class="tree">g\n'` became
  `'<pre class="tree"><span class="ag-when">g</span>\n'`. This is STRICTER: the case still pins "group g is the first
  line" and now also pins the span. Nothing was lost. It now goes red on the new mutation too (see below), so it has
  two jobs.
- `:4147` (the `_kept` case, "keeps every when heading and every step"): `ln.strip()[:2]` became
  `re.sub(r"<[^>]+>", "", ln).strip()[:2]`. **L2 (LOW): this case is now blind to markup at the start of a line, in
  BOTH snapshots it loops over.** Before, any tag at the start of a line changed the first two characters. Now all
  tags are stripped. The new title case (:3958-3962) only partly makes up for this: it reads `_h509`, the snapshot
  with no change-if, and not the second (`change_if="x"`) snapshot. Concrete surviving edit on a copy:
  `if ln.startswith(" ") else` -> `if (ln.startswith(" ") or ag.get("change_if") == "x") else`, which removes the
  titles only when a change-if is set. Result: **439/439 green, SURVIVED.** The edit is contrived, so this is LOW. A
  `count('class="ag-when"') == 2` check inside the `_kept` loop would close it.

## (3) Does the re-bound mutation still delete the first line?

Yes. The anchor `        for ln in agenda_step_lines(snap, ag)) + "</pre>")` occurs exactly once (:2003). Applied to a
copy, the result is **436/439, killed**: the expected case "⭐ #509 r1 Codex L2 ... keeps every when heading and every
step" goes red, along with the new title case and :4209. It drops element `[0]` of `agenda_step_lines`, which is the
first GROUP LABEL ("today"), not the first step. This is the same thing the old anchor's `[1:]` dropped, so the
meaning is unchanged. (The brief says "first step line". Strictly, it was always the first group line.)

## Other mutations tried (on a copy)

| Edit | Result |
|---|---|
| new manifest entry `if True else` (no titles) | KILLED 437/439 (expected case + :4209) |
| `if False else` (every line a title) | KILLED 438/439 |
| `if not ln.startswith(" ")` (inverted) | KILLED 437/439 |
| drop `</span>` (unclosed span) | KILLED, and the page-subset checker also raises `OutsideSubset` |
| `[:-1]` (drop the last line) | KILLED 436/439 |
| rename the CSS selector `.ag-when` -> `.nope` | **SURVIVED 439/439** |
| delete `text-transform:capitalize` | **SURVIVED 439/439** |
| title branch emits raw `ln` (no `_html_line`: no escaping, no links) | **SURVIVED 439/439** |
| step branch emits raw `ln` | **SURVIVED 439/439**, which PREDATES this PR |
| step branch uses `ln.lstrip()` | **SURVIVED 439/439**, which predates it (the old `_kept` form `.strip()`ped too) |

**L3 (LOW): the new case's name claims "in the accent", and no case asserts the style.** Removing or renaming the
`section.agenda .ag-when` rule (:2199-2200) leaves the suite green. The span would then render as an unstyled plain
line, which is the exact thing the owner asked to get rid of. Fix: assert that the CSS block contains the
`.ag-when{...color:var(--accent)` rule, or drop "in the accent" from the case name.

**L4 (LOW): escaping and linking in the agenda `<pre>` is pinned by no case, in either branch.** Both survivors
above show it. The title branch is new code that inherits a gap that already existed for steps. Today the input is
the coordinator's own text, so the risk is a broken page, not an attack. A case with a `## <b>x</b> PR #5` group would
pin both branches.

**L5 (LOW, INFERRED, not looked at in a browser): `text-transform:capitalize` capitalises EVERY word**, link text
included. "carried over" shows as "Carried Over", "next today" as "Next Today", and a `when` naming "backlog #12" shows
"Backlog #12". The dashboard entry calls them "titles", so title case may be intended. If only the first letter was
meant, `::first-letter` does that.

## Not in scope

The backlog #610 row describes a separate defect (reading `docs/backlog.md` from a stale checkout). It is filed, not
fixed, here. That is consistent with the dashboard entry, and I did not review its claims.

## Summary

No BLOCKER, HIGH or MEDIUM. The classification is sound for everything `parse_agenda` can produce. The re-bound
mutation is killed and still means what it meant. The new mutation is killed by its expected case. Five LOW findings
(L1-L5): one is reachable only through a hand-edited log, three are test-strength gaps (the CSS claim, escaping, the
weakened `_kept` form), and one is cosmetic. None needs a fold before merge. All can be filed.

VERDICT: CONVERGED
