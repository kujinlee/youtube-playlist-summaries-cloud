# Plan review — project dashboard, round 1, CLAUDE half (Post-Plan Gate)

**Subject:** `docs/superpowers/plans/2026-08-28-project-dashboard-plan.md` (merged `af757d9`)
**Spec:** `docs/superpowers/specs/2026-08-28-project-dashboard-design.md` (v5, `c5fcb07`)
**Reviewer:** Claude half. The Codex half (`plan-project-dashboard-r1-codex.md`) was not read.
**Method:** every Python function in the plan was transcribed into
`…/scratchpad/dash/{task1.py,full.py,gate.py}` and **executed** on Python 3.14.4. The gate was run
against a throwaway git repository and against the eleven first-parent commits on `master`. Claims
about existing repo files were checked by opening those files. Each finding is labelled
**VERIFIED** (I ran it, output quoted) or **INFERRED**.

---

## READY TO EXECUTE: **NO**

The code largely runs. `18/18`, `26/26` and `35/35` self-tests pass as assembled, and the parser
handles most of what was thrown at it. The problem is not that the plan is vague — it is that three
of its verification steps assert outcomes that are false, and the plan's Self-Review claims coverage
it does not have.

**Shortest list of what must change before execution:**

1. **Task 4 Step 6's falsifier does not falsify, and the plan tells the implementer to conclude the
   opposite.** `git stash push` on a *committed* file is a no-op. Replace it with a falsifier that
   actually removes the entry from the branch diff. (B1)
2. **`gen-dashboard.py` must call `brief-compose.py` itself, as `gen-goals-page.py:489` and
   `gen-backlog-page.py:1630` both do**, and fail loud if it does not write. As planned, the
   script's own advertised default invocation overwrites the served page with a trayless,
   charset-less fragment. (B2)
3. **Implement spec §6.2's third falsifier** — `[resolved:]` naming an unknown id is malformed.
   Two of the three stated falsifiers are implemented; this one has no code and no case, and the
   Self-Review says "every row has a case". (B3)
4. **Either implement §7's "the dashboard **displays** [`NO-ENTRY`]" or admit it as a third
   shortfall.** No task renders it. (H1)
5. **Fix the skill path.** `.claude/skills/*` are symlinks into `.agents/skills/*`;
   `check-explainer-delivery.py` reads `.agents/skills`. Task 6 Step 3's "Expected: exit 0" is
   false as written. (H2)
6. Fix the two renderer defects that contradict spec §6.1/§6.2 in code that already exists in the
   plan: malformed blocks sort to the bottom rather than rendering *in place* (H3), and the
   "marked" zero-commit bar is marked only inside a visually-hidden span (H4).

**Counts:** 3 Blocking · 5 High · 8 Medium · 7 Low.

---

## What I ran

```
$ python3 task1.py --self-test          # Task 1, steps 1-6 as written
18/18 passed
rc=0

$ python3 full.py --self-test           # Tasks 1-3 assembled
35/35 passed
rc=0

$ python3 gate.py --self-test           # Task 4, steps 1-5 as written
10/10 passed
rc=0
```

The f-string in Task 3 Step 3 **compiles and produces balanced CSS** — every `{{`/`}}` escape is
correct. `_bar` does **not** divide by zero when every day has zero commits: `max(tallest, 1)`
guards it and the all-zero case yields `height:4px`. Both were concerns raised in the review
prompt; both are clean. VERIFIED.

---

# Blocking

## B1 — Task 4 Step 6's falsifier is inert, and the plan's stated interpretation of its result is inverted

**Claim (Task 4, Step 6):**

> Now falsify it — the check is worthless if it cannot go red:
> ```bash
> git stash push docs/dashboard-entries.md
> python3 scripts/check-dashboard-entry.py --base origin/master; echo "rc=$?"
> git stash pop
> ```
> Expected: `REFUSED` and `rc=1`. **If this prints `ok`, the gate does not work — stop and fix it.**

**What I ran.** A throwaway repository reproducing the branch exactly as Task 1 Step 9 leaves it —
`docs/dashboard-entries.md` **committed**, not merely written:

```
=== branch state: entry COMMITTED, as Task 1 Step 9 leaves it ===
6ad50b2 task 1: parser and store
e0d82bb base

=== Step 6 first half: expect 'ok', rc=0 ===
ok — an entry block was added
rc=0

=== Step 6 SECOND half — the plan's falsifier, VERBATIM ===
No local changes to save
  (git stash push rc=0)
ok — an entry block was added
rc=0

=== git stash list ===
(empty)
```

**What is actually true.** `git stash push <path>` stashes *uncommitted* changes. By Step 6 the
entry has been committed for three tasks, so the command does nothing, exits 0, and stashes
nothing. The check then correctly finds `+## ` in `git diff master...HEAD` and passes. `git stash
pop` on the following line would fail too ("No stash entries found"), though the plan does not
check it.

The severity is not that a test is weak — it is that **the plan hands the implementer a false
diagnosis.** The instruction is "If this prints `ok`, the gate does not work — stop and fix it."
`ok` is exactly what it prints, and the gate is fine. The implementer is sent to repair a correct
mechanism on the strength of a control that was never capable of firing.

**Control — the gate itself is sound.** Two runs with the entry genuinely absent from the branch
diff:

```
=== CONTROL 1: code changed, no entries file at all ===
lib/x.ts
REFUSED — 1 tracked file(s) changed and no entry was added to docs/dashboard-entries.md. …
rc=1

=== CONTROL 2: entry removed from the branch by a commit ===
REFUSED — 1 tracked file(s) changed and no entry was added to docs/dashboard-entries.md. …
rc=1
```

**Fix.** Falsify against the diff the check actually reads, e.g. run with `--base HEAD` (nothing
changed → but note that passes for a different reason), or better: `git commit` a removal on a
scratch branch, or point `--base` at the commit *after* the entry landed. The falsifier must remove
the `+## ` line from `git diff <base>...HEAD`, which is the only input `collect()` has.

VERIFIED. This is `docs/portable-practices.md` §17 — *the control that was never run* — shipped in
commit `9733102` earlier the same day as this plan.

---

## B2 — `gen-dashboard.py`'s documented default invocation overwrites the served page with an unwrapped fragment; the regen hook would do it on every entry write

**Claim (Task 1 Step 1, the script's own docstring):**

> ```
>     python3 scripts/gen-dashboard.py              # -> ~/explainers/dashboard.html
> ```

and (Task 3 Step 5) `--out` defaults to `pathlib.Path.home() / "explainers" / "dashboard.html"`.

**But `build()` returns a fragment, not a page.** Task 3's Interfaces line says so explicitly:

> Produces: `build(...) -> str` returning a complete HTML **fragment** (a `<title>`, one `<style>`,
> then body markup) suitable for `scripts/brief-compose.py --content`.

I executed `build` and inspected the first bytes: it begins `<title>Project dashboard</title>` —
no `<!doctype>`, no `<meta charset="utf-8">`, and **no Ask tray**. VERIFIED.

**What the two existing standing-page generators do instead.** Both call the composer themselves:

- `scripts/gen-goals-page.py:489` — `[sys.executable, ".../brief-compose.py", "--content", frag,
  "--slug", "goals", "--out", str(args.out), "--title", …]`, then `:496`
  `if r.returncode != 0 or not args.out.is_file(): print("FAILED — brief-compose did not write …")`
  and returns 1.
- `scripts/gen-backlog-page.py:1630` — the same shape.

`gen-goals-page.py`'s comment at `:482` states the rule the plan breaks: *"The Ask tray is LIFTED by
brief-compose.py, never re-implemented here — one tray, three page-producing callers."* And
`brief-compose.py:30-31`: *"If no source explainer can be found … this EXITS NONZERO and writes
nothing. A brief that renders without its Ask tray is the failure this script exists to prevent."*

**Consequences, in order of how likely they are to bite:**

1. `python3 scripts/gen-dashboard.py` — the invocation printed in its own `--help` — replaces the
   composed `~/explainers/dashboard.html` with a fragment. The page loses its question tray
   silently; nothing fails.
2. **Task 6 Step 4's regen hook makes this automatic.** It is specified as "modelled on
   `.claude/hooks/regen-goals-page.sh`", which runs `python3 "$REPO/scripts/gen-goals-page.py"`
   with no arguments. For goals that yields a finished page. For the dashboard it yields the
   fragment — so every write to `docs/dashboard-entries.md` would degrade the page. The hook is
   also specified to "Exit 0 unconditionally", so it cannot report this.
3. Served without `<meta charset>`, the fragment's `—`, `●`, `⚠` and `↻` are at the mercy of
   browser sniffing. `explainer-serve.py:618` sends whatever `ctype` the caller passes; the HTML
   branch for a file on disk is not one of the `charset=utf-8` literals at `:628`/`:659`.

**Fix.** Make `gen-dashboard.py` invoke `brief-compose.py` internally with `--out`, and fail
non-zero when the file is not written — i.e. copy `gen-goals-page.py:487-498`. That also deletes
the fragile `mv ~/explainers/*-brief-dashboard.html ~/explainers/dashboard.html` from both Task 3
Step 6 and the SKILL.md, which is a hand-run glob with no error check.

VERIFIED (build output executed; the two generators and `brief-compose.py` read directly).

> Note in the plan's favour, VERIFIED: the *rename claim itself* is correct.
> `DATED = re.compile(r"^\d{4}-\d{2}-\d{2}-")` at `explainer-serve.py:385` and
> `is_standing()` at `:389` mean `dashboard.html` is a standing page and **is** excluded from
> `/latest`, and `resolve_page()` at `:400-417` serves `/dashboard` from `dashboard.html`. The
> plan's reasoning about `/latest` is right; only the mechanism for producing the file is wrong.

---

## B3 — Spec §6.2's third falsifier is not implemented, and the Self-Review claims it is

**Spec §6.2:**

> A `[resolved:]` naming an unknown id is **malformed**.
>
> **Falsifier:** an entry with a bad date, an unknown flag, and a `[resolved:]` pointing at nothing
> must **each** render as an error while the surrounding entries still render.

**Plan Self-Review:** *"§6.2 grammar → Task 1 (every row has a case)."*

**What I ran:**

```
D  empty resolved id      "## 2026-08-29 [resolved: ]\nDone.\n"
   -> err=None  resolves=''             id='2026-08-29/1'
D3 nonexistent target     "## 2026-08-29 [resolved: 1999-01-01/9]\nDone.\n"
   -> err=None  resolves='1999-01-01/9' id='2026-08-29/1'
```

and end-to-end, with a real `needs-you` to clear:

```
empty resolve leaves it open:  ['2026-08-26/1'] | resolves field: '' | error: None
typo'd resolve id, no diagnostic: ['2026-08-26/1'] | error: None
```

**What is actually true.** `FLAG = re.compile(r"\[(needs-you|resolved:\s*[^\]]+)\]")` accepts any
non-`]` payload, and `parse_entries` stores `f.split(":", 1)[1].strip()` without validating it
against any id. `[resolved: ]` even survives — `\s*` backtracks to empty so `[^\]]+` matches the
space, yielding `resolves=''`, which `unresolved()` then discards as falsy. Bad dates and unknown
flags *are* caught; this third case is not, and there is no self-test row for it.

This is the highest-consequence gap in the parser, because it is silent in the direction that
matters: the author appends `[resolved: 2026-08-26/2]` believing they have cleared an item, the
item stays on "What needs you" forever, and nothing anywhere says why. §6.2's whole argument for
treating an unknown flag as malformed — *"a typo'd `[needs-you]` would silently drop an item off
§4"* — applies with equal force here and was not carried across.

**Fix requires a structural change, not a line.** Ids are assigned during the same single pass that
reads `resolves`, so a forward reference cannot be validated inline. `parse_entries` needs a second
pass over `out` after all ids exist, setting `error` on any entry whose `resolves` names no entry.
Add the case the spec's falsifier names.

VERIFIED.

---

# High

## H1 — §7 requires the `NO-ENTRY:` exemption to be **displayed**; no task renders it (unadmitted shortfall)

**Spec §7:**

> **Exemptions must be explicit and visible:** a branch may declare `NO-ENTRY: <reason>` in its
> body, which the check accepts and the dashboard **displays**, so a skipped entry is a recorded
> decision rather than a silence.

**What I ran:**

```
'NO-ENTRY' appears in rendered page: False
build() signature: (entries, days, prs, pr_error, git_error, window) -> 'str'
```

**What is actually true.** `build()` has no parameter that could carry an exemption,
`gen-dashboard.py` never reads a PR body or `gh pr view`, and Task 4's Interfaces line states the
separation as deliberate: *"Consumes: nothing (independent of `gen-dashboard.py` on purpose)"*.
Nothing in Tasks 1–6 renders `NO-ENTRY:`.

The plan's "Gaps, stated rather than hidden" section admits two shortfalls (the `--window` argument,
the cited affordance probe). This is a third, and it is larger than either — see Q6 below, where it
is the mechanism by which the gate hollows out without leaving a trace.

VERIFIED.

## H2 — Task 6 creates the skill at the wrong path, and Step 3's expected result is false

**Claim (File Structure table and Task 6):** *"Create: `.claude/skills/dashboard/SKILL.md`"*, then
Step 3: *"Run: `python3 scripts/check-explainer-delivery.py`. Expected: exit 0."*

**What I checked:**

```
$ ls -ld .claude/skills/brief
lrwxr-xr-x  .claude/skills/brief -> ../../.agents/skills/brief

$ stat -f "%i %N" .claude/skills/brief/SKILL.md .agents/skills/brief/SKILL.md
76299635 .claude/skills/brief/SKILL.md
76299635 .agents/skills/brief/SKILL.md
```

Every skill in `.claude/skills/` is a symlink into `.agents/skills/`; git tracks the real file at
`.agents/skills/<name>/SKILL.md` and the symlink at `.claude/skills/<name>`.
`check-explainer-delivery.py:45` sets `SKILLS = ROOT / ".agents" / "skills"`.

**What I ran** — the audit with `dashboard` added to `PAGE_SKILLS`, with the skill created where the
plan says to create it:

```
SKILLS dir the check reads: …/.agents/skills
audit as-is: []
audit with dashboard: ['dashboard/SKILL.md is missing (renamed or deleted? update PAGE_SKILLS)']
```

So Task 6 Step 1 (add to `PAGE_SKILLS`) plus Task 6 Step 2 (create at `.claude/skills/…`) makes
Step 3 fail. The plan's Step 3 also predicts the *wrong failure mode*: it says "If it fails saying
the skill restates the delivery loop…", which is a different check.

**Fix.** Create `.agents/skills/dashboard/SKILL.md` and add the `.claude/skills/dashboard` symlink,
matching all twenty existing skills.

VERIFIED. (The plan's `scripts/check-explainer-delivery.py:53` citation for `PAGE_SKILLS` is
correct — line 53 is exactly that list.)

## H3 — §6.2 requires a malformed block to render **in place**; `build` sorts it to the bottom, and the self-test case that names this does not test it

**Spec §6.2:** *"Malformed block | rendered **in place**, raw, under a visible 'could not parse this
entry' label, and the page still renders everything else"*. The plan repeats it in
`parse_entries`' docstring: *"the page must show it in place (spec §6.2)"*.

**What I ran** — three entries, the broken one in the middle of the file:

```
input:  ## 2026-08-28 Newest good.  /  ## 2026-02-30 Broken middle.  /  ## 2026-08-27 Older good.
render order: ['Newest good.', 'Older good.', '## 2026-02-30\nBroken middle.']
```

**What is actually true.** `sorted(entries, key=lambda x: (x["date"] or "", x["ordinal"]),
reverse=True)` maps a malformed entry's `date=None` to `""`, which sorts below every real date and,
under `reverse=True`, lands last. A malformed block never renders in place — it always renders at
the very bottom of the page, furthest from the context that would explain it.

**The self-test does not catch this**, and its name says it does:

```python
case("malformed rendered in place", "could not parse" in html_bad.lower(), True)
```

That asserts the string appears *somewhere in the document*. It passes for any position. The one
case whose name encodes the spec requirement is a presence check — this project's
"test harness can launder failures" shape.

VERIFIED.

## H4 — §6.1's "marked" zero-commit bar is marked only inside a visually-hidden span

**Spec §6.1:** *"An entry on a day with zero commits renders in the list and gets a **zero-height
marked bar**, so 'I wrote about a day with no commits' is **visible rather than invisible**."*

**What I ran** — `_bar` for two zero-commit days, one with an entry and one without:

```
with entry   : <a class="bar" href="#d-2026-08-28" style="height:4px" title="…, entry with no commits"
                aria-label="…"><span class="vh"> ●</span></a>
without entry: <a class="bar" href="#d-2026-08-27" style="height:4px" title="2026-08-27: 0 commits"
                aria-label="…"><span class="vh"></span></a>

same css class? True
same height?  True
```

**What is actually true.** The only difference in the rendered box is the `●` inside
`<span class="vh">`, and Task 3 Step 3's own stylesheet defines
`.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}` — the standard
visually-hidden idiom. The `title` and `aria-label` differ too, but a `title` requires a hover and
`aria-label` is not sighted output. **On screen the two bars are pixel-identical.** The requirement
is specifically that this be *visible rather than invisible*; the implementation puts the mark in
the one place that is invisible by construction.

(Secondary: `.vh` is `position:absolute` while `.bar` establishes no containing block, so even if
un-hidden the `●` would position against the nearest positioned ancestor, not the bar.)

**Fix.** Give the marked bar its own visible treatment — a distinct class with a border, a dot
rendered outside the `.vh` span, or a background — and keep the `.vh` text for screen readers.

VERIFIED.

## H5 — a `gh` failure blanks "What needs you", discarding the store-derived needs that are fully knowable without `gh`

**Code (Task 3 Step 3):**

```python
    if pr_error:
        needs_html = (f'<p class="unknown">I could not tell whether anything needs you — '
                      f'{_html.escape(pr_error)}</p>')
```

**What I ran** — one unresolved `needs-you` entry in the store, `gh` failing:

```
section text: <p class="unknown">I could not tell whether anything needs you — gh exited 1: auth</p>
```

The entry "Decide the pricing model." is not in the section. (It appears further down the page in
"What changed", but that is the changelog, not the answer to the page's rank-1 question.)

**What is actually true.** `need = unresolved(entries)` is computed from the local markdown file and
is unaffected by `gh`. Two independent sources feed one section, and the failure of the *optional*
one suppresses the *primary* one. The `CLAUDE.md` rule the comment invokes — *"could not tell" is
NOT "nothing needs you"* — is satisfied, but over-applied: the correct rendering is the known list
**plus** a "could not also check open pull requests" note, not the note alone.

This matters most in exactly the scenario the page exists for: someone returns after time away,
`gh`'s token has expired, and the dashboard reports that it cannot tell whether anything needs them
while holding a file that says something does.

VERIFIED.

---

# Medium

## M1 — the entry id the resolution mechanism depends on is never rendered

`build()` emits `<h3>{date}</h3>`; the `/N` ordinal appears nowhere. VERIFIED:
`is the ordinal ever rendered? False`. Yet the SKILL.md instructs: *"Clear an earlier one by
appending a later entry with `[resolved: YYYY-MM-DD/N]`."* To find `N`, a reader must open the raw
markdown and count blocks with the same date, including or excluding malformed ones correctly (see
M8 — malformed blocks do **not** consume an ordinal, so the count is not simply "the Nth `##` with
this date"). Combined with B3, a wrong `N` is silently accepted. Render the id on each entry.

## M2 — duplicate DOM ids; chart anchors are ambiguous

VERIFIED: two entries on one date produce `ids: ['d-2026-08-28', 'd-2026-08-28'] -> duplicates: True`,
and every malformed entry gets `id="d-?"` (`two malformed -> ids: ['d-?', 'd-?']`). The chart's
`href="#d-<date>"` therefore resolves to whichever comes first. Duplicate `id` attributes are
invalid HTML. Use `e["id"]` (slash-escaped) for the anchor and have the bar link to the first entry
of that date deliberately rather than accidentally.

## M3 — §6.2 "ties keep file order" is violated

**Spec §6.2:** *"Ordering | file order, rendered newest-date-first; **ties keep file order**"*.
VERIFIED:

```
input:  ## 2026-08-28 FIRST in file.  /  ## 2026-08-28 SECOND in file.
render order: ['SECOND in file.', 'FIRST in file.']
```

`reverse=True` reverses the whole key tuple, ordinal included. Sort by `(date,)` descending with a
stable sort, or by `(date, -ordinal)` — not by reversing both.

## M4 — `unresolved` ignores ordering; an earlier or self-referencing entry clears a later one

Docstring: *"needs-you entries not cleared by a **later** `[resolved: <id>]`"*. `cleared` is a flat
set over all entries. VERIFIED:

```
EARLIER entry resolves a LATER one: []      # cleared
self-resolving entry:               []      # cleared itself
```

`## 2026-08-26 [needs-you] [resolved: 2026-08-26/1]` clears itself and never appears on the page —
a way to write a `needs-you` that flags nothing. Either enforce "later" or delete the word from the
docstring and the spec.

## M5 — Task 6 Step 4 is a prose placeholder, and omits the step that makes the hook fire

**Claim (Task 6 Step 4):** *"Create `.claude/hooks/regen-dashboard.sh`, modelled on
`.claude/hooks/regen-goals-page.sh`, firing when `docs/dashboard-entries.md` is written."*
**Plan Self-Review:** *"**Placeholders:** none. Every code step carries the code."*

That is a description, not code, and it is the plan's own standard that it fails. Worse, it omits
registration: `.claude/settings.json:66` carries `"command": "bash .claude/hooks/regen-goals-page.sh"`.
A hook script with no `settings.json` entry never runs, and since the hook is specified to
"Exit 0 unconditionally" there is no signal either way. There is also no verification step that the
hook fired. VERIFIED (settings.json wiring read directly).

Also worth deciding rather than inheriting: `regen-goals-page.sh`'s own header argues against
pairing a derived page with a skill — *"A skill here would be a wrapper whose entire body is 'run
the script', and it would have to join `scripts/check-explainer-delivery.py`'s PAGE_SKILLS… `/backlog-table`
set this precedent: it is a script plus a hook and has no skill at all."* The dashboard skill has a
real non-wrapper job (writing the entry), so a skill is defensible here — but the plan never
engages with the precedent it is departing from.

## M6 — Task 5's two new self-test rows cannot fail for the defect they name

The `case(name, fn)` signature at `explainer-serve.py:761` matches, so the rows are syntactically
valid. But they are substring checks against `RELOAD_JS`, and `"restoreDetails()"` is a substring of
`function restoreDetails()`. VERIFIED:

```
call present   -> "restoreDetails()" in RELOAD_JS = True
CALL DELETED   -> "restoreDetails()" in RELOAD_JS = True

save called          -> row passes = True
SAVE NEVER CALLED    -> row passes = True
```

Both rows pass on a client that defines both functions and calls neither — i.e. on a build where
the feature is entirely dead. They assert that text was typed, not that behaviour exists. Step 5's
manual two-fold check is the real test; these rows should not be presented as guarding it.

## M7 — Task 5's fold key is positional, and shifts on exactly the regeneration that triggers the reload

Proposed: `open.push(d.id || String(i))`. VERIFIED that `build()` emits no ids on its folds:

```
details tags: ['<details>', '<details>']
```

So the key is always `String(i)` — the index in document order. The reload fires when
`dashboard.html` is rewritten, and the commonest rewrite is *a new entry appended to the store*,
which renders newest-first at the **top**, shifting every subsequent fold index by one or two. The
restored open-state is then applied to the wrong folds. The feature works when the page content is
unchanged and misbehaves when it changed — which is the only reason the page reloaded. Emit a
stable `id` on each `<details>` (derived from the entry id plus `plain`/`tech`) and key on that.

## M8 — `##` with no space is silently dropped, contradicting the parser's own docstring

Docstring: *"A malformed block is RETURNED with an error, **never dropped**"*. VERIFIED:

```
H2 '##2026-08-28' with no space: n=0
```

The block splitter tests `line.startswith("## ")`, so a missing space makes the whole entry vanish
with no error and no trace on the page. A missing space after `##` is a plausible hand-typing slip.
(Partial mitigation, INFERRED: the ratchet looks for `+## `, so such an entry would not satisfy the
gate either and the PR would be refused — the author would get *a* signal, just not the right one.)
Split on `^##\s*\S` and let the date/flag rules produce the error.

---

# Low

- **L1 — Task 1 Step 6 states the wrong count.** *"Expected: `19/19` passed"*. VERIFIED actual:
  `18/18 passed`. Step 1 defines 6 cases and Step 5 adds 12. Task 2's `26/26` and Task 3's `35/35`
  are both consistent with 18, so `19` is the sole error — but an implementer running the plan's own
  TDD loop will stop and hunt for a nineteenth case that does not exist.
- **L2 — an entry with no title is accepted silently.** VERIFIED: `"## 2026-08-28\n\n\n"` →
  `title=''`, `error=None`, rendering an empty `<p class="title"></p>`. §6.2 defines Title as "the
  first non-blank line after the header" but does not say what happens when there is none.
- **L3 — `open_prs`' output is trusted structurally.** VERIFIED: `build` interpolates
  `{p["number"]}` **without** `_html.escape` (every other interpolation is escaped), and a PR dict
  missing `title` raises an uncaught `KeyError`. `json.loads` is not checked for list-ness, so a
  JSON object would iterate its keys and `TypeError`. Not reachable through real `gh` output;
  inconsistent with the plan's own escaping discipline and with `commit_dates`/`open_prs` otherwise
  careful error contract.
- **L4 — `NO-ENTRY:` inside a fenced code block in the PR body exempts the branch.** VERIFIED:
  ``verdict(["lib/x.ts"], False, "```\nNO-ENTRY: example from the docs\n```")`` → `rc=0`. The scan is
  line-oriented with no fence awareness. Low because it needs an unlucky PR body, but the ratchet's
  own refusal message contains the literal string, so quoting it back is a plausible accident.
  (VERIFIED that quoting it as `> …'NO-ENTRY: <reason>'…` does **not** trigger — the `>` prefix
  saves it.)
- **L5 — `EXEMPT_PREFIXES` is a prefix match, not a path match.** VERIFIED:
  `docs/dashboard-entries.md.bak` is exempt. Trivial. **Conversely, the concern raised in the review
  prompt is not a defect:** `"docs/reviews-not-really/x.ts".startswith(("docs/reviews/", …))` is
  `False`, so such a path is correctly refused. VERIFIED.
- **L6 — `--window 0` or a negative window yields an empty chart with no complaint.** VERIFIED:
  `bucket_days([...], [], 0, "2026-08-28") == []`, and `build` then renders `<div class="chart"></div>`.
  `argparse` does not constrain the value. A "cannot run" that renders as an empty box.
- **L7 — the plan adds two mechanically-enforced scripts and no pointer rows.** `docs/dev-process.md`
  requires *"write the script and add a pointer row above"*, and its "What is mechanically enforced"
  table has no entry for `check-dashboard-entry.py`. VERIFIED the budget is tight:
  `docs/dev-process.md` is **214 lines against a 220 budget** (`check-docs.py:191`), so two rows fit
  but leave four lines of headroom. Worth a deliberate decision, not a discovery at commit time.

---

## Spec coverage — spot-check of the Self-Review

I checked five of the eleven mappings the Self-Review asserts.

| Self-Review claim | Verdict |
|---|---|
| §6.2 grammar → Task 1 — *"every row has a case"* | **False.** "A `[resolved:]` naming an unknown id is malformed" has neither code nor case (B3). "Malformed block rendered in place" has a case whose assertion does not test placement (H3). "Ties keep file order" is violated (M3). |
| §6.1 rendered once → Task 3 | **Holds** for "rendered exactly once" and "the list is not windowed" — VERIFIED `build` renders every entry. **Fails** on the marked zero-commit bar (H4). |
| §7 the gate → Task 4 | **Partial.** The refusal mechanism is built and works (controls above). The **display** requirement is absent (H1). |
| §10.3 `PAGE_SKILLS` → Task 6 Step 1 | **Holds as a step, fails as written** — right list, wrong skill path (H2). The plan's own warning that this check "cannot enforce its own list" is correct and honest. |
| §10.4 `gh` failure → Task 2 Step 5 + Task 3 | **Partial.** `open_prs` correctly distinguishes `[]` from failure — good, and VERIFIED. `build` then over-applies it (H5). |

**Unadmitted shortfalls beyond the two the plan lists:** §7's `NO-ENTRY:` display (H1), §6.2's
unknown-resolve-id rule (B3), §6.2's tie ordering (M3), §6.1's visible marked bar (H4), and §6.2's
"in place" (H3).

**Correct claims I checked and could not break:**
- Task 3 Step 6's `/latest` exclusion reasoning — VERIFIED correct against
  `explainer-serve.py:385-417`.
- Task 4 Step 7's CI snippet — VERIFIED. `.github/workflows/ci.yml` ends with the two
  `check-function-revokes` steps, the indentation (`      - name:`) matches, and every other
  `python3 scripts/…` step runs bare on `ubuntu-latest` with no Python setup step, so two more fit
  exactly as written.
- `check-anchors.py` passes and `status-visibility` is registered at `docs/anchors.md:39`.
  VERIFIED (`rc=0`).
- `check-ratchet-contract.py:190` globs `scripts/check-*.py`, so the new ratchet is picked up
  automatically; it has a `--self-test` and no `except` handler returning 0, so it should satisfy
  the contract. INFERRED — I did not place a file in the repo to run it.

**Task 4's CI split (Priority 4).** Running the two `--self-test`s but not the ratchet is
**coherent, and the plan says why** — the ratchet needs the PR body, and that wiring is deferred.
But it does mean the gate that is the entire justification for §7 does not actually gate anything
until Task 6, and Task 6 Step 5's verification list does not include running it either. If the PR
lands with the ratchet still unwired, §7 is a script nobody executes. Make the wiring an explicit
acceptance criterion of the PR rather than a step inside a task.

---

## Q6 — would the gate have refused the six PRs merged today, and is that the right cost?

**What I ran** — `verdict()` against the real file lists of every first-parent commit on `master`
from 2026-08-28, with `added_entry=False` and an empty body:

```
ff5857b fix(docs): a count in prose is a claim about a moving number (#173)   files=  3 exempt=0 -> REFUSED
59385bb fix(skills): explain-topic was UNREACHABLE for four days (#172)       files=  2 exempt=0 -> REFUSED
af757d9 docs(plan): the dashboard build plan (#171)                           files=  3 exempt=0 -> REFUSED
c5fcb07 docs(spec): dashboard v5 (#170)                                       files=  3 exempt=2 -> REFUSED
4b93902 docs(spec): a project dashboard (#169)                                files=  8 exempt=4 -> REFUSED
71c7e40 docs(backlog): row 54 prescribed a mechanism (#168)                   files=  1 exempt=0 -> REFUSED
```

**All six. Six for six.** (The five older ones in the same listing too — eleven for eleven.) Note
`71c7e40` is a **single-file backlog edit** and `4b93902` is half review documents, which are exempt
— the non-exempt half still triggers the refusal.

**Is that the intended cost?** For four of the six, yes, and unambiguously. "I wrote the dashboard
spec", "explain-topic was unreachable for four days and is now fixed", "a backlog row prescribed a
mechanism that does not work" — these are precisely what a person returning after time away needs,
and the gate is doing exactly the job §7 argues for. I would not narrow the exemption list.

**Will `NO-ENTRY:` become a reflex that hollows it out? Yes — as currently specified, and here is
the mechanism.** Look at the two spec PRs, `4b93902` and `c5fcb07`: the same document, iterated
twice in one day, plus `af757d9` for its plan. That cadence — spec v4 → v5 → plan, three PRs, one
piece of work — is this repo's normal rhythm, and it is the case where writing three distinct
plain-language entries feels like paperwork. That is where `NO-ENTRY:` gets typed.

What makes it *hollowing* rather than a healthy escape valve is that the exemption currently costs
nothing and leaves no trace:

- it is one line in a PR body, written by the same agent that would have written the entry;
- **nothing displays it** — H1. §7 says the dashboard displays it, and no task does;
- nothing counts it, so nobody can see "eleven of the last twelve branches declared NO-ENTRY";
- the "bar with no entry" alarm §7.3 promises repairs cannot distinguish a `NO-ENTRY` day from an
  ordinary one, because the exemption never reaches the page.

So the failure would be silent and cumulative — the page would go on looking healthy while
describing less and less. **H1 is therefore not a cosmetic omission; it is the gate's only feedback
loop, and the spec identified it correctly.** Implement the display and the reflex becomes
self-limiting: a reader who sees three "no entry recorded — *typo fix*" rows in a week will say so.
Ship the gate without it and the plan has built the mechanism §7 was written to avoid, with better
packaging.

**Recommendation:** keep the gate and the exemption list exactly as scoped, and treat H1 as
Blocking-adjacent rather than a nice-to-have — it is the difference between a gate and a formality.

---

## Method note

Everything above marked VERIFIED was executed on Python 3.14.4 from transcriptions of the plan's own
code blocks, or read directly out of the named repo file. No repo file was modified; the only file
written is this review. The git experiments ran in a throwaway repository under the session
scratchpad. Two things the review prompt flagged as suspected defects — the f-string's brace
balance and `_bar`'s division by zero — were run and are **clean**; a third, the
`str.startswith`-with-tuple semantics on `docs/reviews-not-really/x.ts`, was run and behaves
correctly.

NOT CONVERGED
