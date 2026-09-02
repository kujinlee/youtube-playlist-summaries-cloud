

===== message index 94 =====
Review complete. Everything below was executed, not read.

---

**HIGH — `(?!#)` re-opens the gate/page divergence the whole change exists to close: a `###` line makes the page render "Could not parse this entry" while the gate says ok**

- WHERE: `scripts/check-dashboard-entry.py:322-325` vs `scripts/gen-dashboard.py:360`
- WHAT: the gate excludes level-3 headings —
  ```python
  # `(?!#)` keeps `###` out: a level-3
  # heading is ordinary body markup and several entries use one, so treating it as a
  # failed entry header would refuse them.
  ENTRY_ISH = re.compile(r"^\+##(?!#)")
  ```
  The renderer's block splitter does **not**: `BLOCK = re.compile(r"^##\s*\S")` (`gen-dashboard.py:360`). `\s*` matches zero characters, so `\S` matches the third `#`. Executed: `BLOCK.match("### Worth knowing")` → `True`.
- WHY IT MATTERS: end-to-end, on an entry-only branch adding `## 2026-09-01 … ### Worth knowing …`:
  ```
  GATE  added_entry_problems -> []
  GATE  verdict              -> (0, 'no tracked files changed outside the exempt paths')
  PAGE block: '## 2026-09-01'      -> error: None
  PAGE block: '### Worth knowing'  -> error: header must be '## ' then a YYYY-MM-DD date …
  ```
  That is precisely `verdict`'s own refusal text — "the page would render it under 'Could not parse this entry'" — arriving as a **pass**. It is the sixth divergence `header_error`'s docstring says it exists to prevent, re-created one function away from that docstring.
  The stated justification is also false as measured: `docs/dashboard-entries.md` contains **zero** `^###` lines (`grep -c` over the file), so "several entries use one" is not true of any entry, and if one did exist the page would already be broken by it. The commit message repeats the claim ("`(?!#)` is load-bearing in the other direction … Mutation-covered") and the manifest entry `entry-attempt regex stops excluding sub-headings` now pins the divergence in place.
- FIX: derive one regex from the renderer's block grammar instead of hand-writing a near-copy — `ENTRY_ISH = re.compile(r"^\+" + BLOCK.pattern[1:])` with `BLOCK` moved into this file beside `HEADER`/`FLAG` and imported by `gen-dashboard.py`, and delete the `###` self-test case (it asserts the divergence). If `###` bodies are genuinely wanted, the change belongs in `BLOCK`, not in a second matcher.

Two smaller divergences fall out of the same split (executed): `+## ` / `+##` / `+## \t` are **refused by the gate** and treated as ordinary body text by `BLOCK` (`^##\s*\S` needs a non-space). Same fix closes them.

---

**HIGH — the widened matcher retroactively re-judges already-merged PR bodies; the dashboard's exemption list went from empty to one entry, and that entry is false**

- WHERE: `scripts/check-dashboard-entry.py:96-120` (`_declaration_reason`) consumed by `scripts/gen-dashboard.py:724-756` (`no_entry_prs`)
- WHAT: `no_entry_prs` re-reads the bodies of the last 40 **merged** PRs through the gate's current `exemption_reason`. I ran the real function against live `gh` output:
  ```
  err: None
   #198 Repair master: the #80 palette retune orphaned a mutation an
        reason='repair of a red I introduced in #197; the dashboard entry for #80 already describes the change this restores coverage for.**'
  ```
  Diffing new-vs-old semantics across all 40 bodies, #198 is the **only** divergence: `old=None`, `new=<above>`. Its body line 18 is
  `**NO-ENTRY: repair of a red I introduced in #197; … coverage for.**`
  and `git show 86ecade5 --stat` shows that PR changed `docs/dashboard-entries.md | 49 ++++…` — it **wrote an entry**. It passed the gate via `added_entry`, never via an exemption.
- WHY IT MATTERS: `no_entry_prs`'s own docstring says *"the page shows exactly the exemptions the gate granted. A display that disagrees with the gate is worse than none."* The page now claims a PR that wrote a 49-line entry was exempted from writing one. Before #203 the list was empty; 100% of its current content is wrong, and spec §7's purpose is exactly to let someone count exemptions ("eleven of the last twelve branches skipped their entry"). Nothing in the change considered that widening the matcher rewrites history for a display fed by merged-PR bodies.
- FIX: `no_entry_prs` should not re-derive a verdict for PRs the gate already judged. Smallest change that closes it: bound the listing to PRs merged on or after the widening date, or record the granted exemption at gate time rather than re-parsing bodies later. If neither is wanted, at minimum the page must stop presenting a re-derivation as "the exemptions the gate granted".

---

**MEDIUM — the closer is only stripped when it immediately follows the marker, so the one real-world bold shape leaks `**` into the reason; no case covers it**

- WHERE: `scripts/check-dashboard-entry.py:112-120`
  ```python
  m = EMPH.match(s)
  opener = m.group(1) if m else ""
  rest = s[len(opener):]
  if not rest.startswith(NO_ENTRY):
      return None
  rest = rest[len(NO_ENTRY):]
  if opener and rest.startswith(opener):
      rest = rest[len(opener):]
  return rest.strip()
  ```
- WHAT: executed — `exemption_reason("**NO-ENTRY: x**")` → `'x**'`. The handled shape is `**NO-ENTRY:** reason` (closer adjacent to the marker); the shape a person actually writes, and the only one present in 40 merged PR bodies (#198), is `**NO-ENTRY: reason**` — bold wrapping the whole declaration. `page_markup.render_inline` emits the trailing `**` literally (verified: rendered output ends `…coverage for.**`).
- WHY IT MATTERS: the docstring at `:108-110` presents the closer rule as complete (*"an author's own emphasis inside the reason survives verbatim"*). It is complete for the shape that was tested and silently wrong for the shape that occurs. There is no `case(...)` for `**NO-ENTRY: r**` anywhere in the 104.
- FIX: after computing `rest`, also strip a trailing `opener` when it closes the line: `if opener and rest.rstrip().endswith(opener): rest = rest.rstrip()[:-len(opener)]`. Add the case with the literal from #198.

---

**MEDIUM — `check-plan-code.py`'s narrative comments describe a bump that is not the one recorded**

- WHERE: `scripts/check-plan-code.py:450-457` and `:1967-1971`
  ```python
  # ⟳ 2026-09-01, backlog #78: 18 -> 23. …
  # THREE of the five mutations are on the WIRING …
  "scripts/check-dashboard-entry.py": 27,
  ...
  # ⟳ 141 -> 146, backlog #78 (five entries on the entry gate's content check).
  case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 150)
  ```
- WHAT: `git show 8b395aaf:scripts/check-plan-code.py` confirms PR #201 wrote `23` / `146` with matching prose. PR #203 added four more mutations (manifest is 27 entries, `json.load` count) and bumped both literals to `27` / `150` **without adding a ⟳ line for its own +4**. So the file states "18 -> 23" and "141 -> 146 (five entries)" next to values of 27 and 150 — nine entries.
- WHY IT MATTERS: this file's convention (and its own entry at `docs/dashboard-entries.md:1413`, *"One number left alone deliberately"*) is that every bump carries a paragraph naming what bought it. Four mutations now have no narrative, and anyone auditing coverage reads a baseline four short. Nothing mechanical catches it — `check-docs`, `check-selftest-counts` and `--mutate .` all pass (I ran all three).
- FIX: append a second ⟳ line for #203's +4 (`23 -> 27`, `146 -> 150`, naming the emphasis mutations), leaving #201's paragraph untouched.

---

**LOW — one new case is vacuous: it passes in the pre-fix world and under the exact naive implementation its comment names as the threat**

- WHERE: `scripts/check-dashboard-entry.py:482-485`
  ```python
  # ⚠ Emphasis in the REASON is the author's text and must survive verbatim. A
  # naive lstrip("*") on the remainder would eat it.
  case("emphasis inside the reason is preserved",
       exemption_reason("NO-ENTRY: keep **bold** here"), "keep **bold** here")
  ```
- WHAT: I built the named naive implementation in a `/tmp` copy (`return rest.lstrip("*_").strip()`, repo untouched) and ran the full suite: **103/104**, one failure, and it is not this case:
  ```
  [FAIL] a mismatched closer is left in the reason: got 'odd' want '* odd'
  ```
  The same case also survives reverting `EMPH` to never match (`/tmp` copy, 8 failures, this case not among them) — i.e. it holds identically before #203. Its sibling `"...and also when the marker itself was emphasised"` survives the naive implementation too (it fails only the EMPH revert).
- WHY IT MATTERS: the comment asserts a falsifier that does not falsify. The threat is covered by exactly one case — `"a mismatched closer is left in the reason"` — and the two cases advertised as covering it do not.
- FIX: move the naive-`lstrip` comment onto the mismatched-closer case, where it is true, and either delete `"emphasis inside the reason is preserved"` or change its input to one that discriminates (e.g. `NO-ENTRY: **bold** first` → `**bold** first`, which `lstrip("*_")` does eat).

---

**LOW — the mutation named for the ORDER does not test the order**

- WHERE: `scripts/mutations/check-dashboard-entry.json`, `"the content check sinks below the exemption short-circuit"`, edit `"    if entry_problems:"` → `"    if entry_problems and False:"`
- WHAT: the edit deletes the check; it does not move it. The author's central claim is "the ORDER is the fix" (`check-dashboard-entry.py:363-366`).
- WHY IT MATTERS: minor — I confirmed the order is still covered, by a *case* rather than a mutation: relocating the block below `if not real: return 0, …` turns `"entry-only branch with a MALFORMED entry is refused"` red (that case is `verdict(["docs/dashboard-entries.md"], False, "", ["bad header"])`, and `real` is empty there). So coverage exists; only the mutation's name overstates what it does.
- FIX: rename the entry to `"the content check is disabled"`, or make the edit an actual relocation.

---

**LOW — `verdict`'s new parameter defaults to `()`, so any caller that forgets it silently skips the content check**

- WHERE: `scripts/check-dashboard-entry.py:361-362` — `def verdict(changed, added_entry, pr_body, entry_problems: list[str] | tuple = ()) -> …`
- WHAT: `grep -rn "collect(" --include=*.py scripts/` returns only this file's own definition, self-test and `main` (and an unrelated `gen-dashboard`-side `collect` in `gen-goals-page.py:173`), so no external caller unpacks the old 3-tuple — that class is empty. But the *default* means the fix is opt-in for every future caller, and only `main` is guarded (by the `"main: an entry-only branch with a malformed entry exits 1"` case).
- FIX: make it a required positional parameter; `main` and the self-test are the only call sites.

---

**Classes I checked and found empty, so you know what is not covered by silence**

- `ENTRY_ISH` against diff noise: executed on `+++ b/docs/dashboard-entries.md`, `--- a/…`, `@@ -1,2 +1,3 @@`, `+####`, CRLF (`+## 2026-08-28 [needs-you]\r` → `[]`). No false matches, no misses.
- Emphasis false passes: executed `***NO-ENTRY:*** x`→`x`, `_NO-ENTRY:_ x`→`x`, `- **NO-ENTRY:** x`→`None`, `> **NO-ENTRY:** x`→`None`, `****NO-ENTRY:**** x`→`None`, `**_NO-ENTRY:_** x`→`None`. No non-deliberate shape exempts. (The last two are false *refusals*, loud, not filed.)
- The four inert contexts: the bold variants pass because the fence/indent/comment scan runs before `_declaration_reason`, i.e. for the right reason — but the blockquote one is redundant with the manifest's `"line-leading rule removed"`, which already reddens `exemption_reason — blockquoted`.
- `added_entry_problems` fence-blindness: not a defect. `BLOCK` is fence-blind too, so a fenced `## 2026-…` inside an entry body breaks the page as well; gate and renderer agree here.
- Repaired anchors: `if not _indented(head): → if True:` preserves the original edit's intent exactly (it removed the same indent conjunct). `if not rest.startswith(NO_ENTRY): → if NO_ENTRY not in rest:` is *stronger* than its predecessor — it now covers both scan points, and I confirmed it still reddens via the named case (`"> NO-ENTRY: quoted"` → `'Y: quoted'`, not `None`).
- Verification claims I re-ran: `--self-test` → `104/104` + `13/13`; `check-plan-code.py --mutate .` → `OK — 7 file(s), 150 mutation(s), 0 survivor(s)`; `check-docs.py` rc=0; `check-selftest-counts.py` rc=0.
- **NOT RUN, treat as unverified:** `tsc --noEmit`, the 2819-test unit suite, and the `service_role` confinement check. I did not execute them and make no claim about them.

VERDICT: NOT CONVERGED

===== message index 110 =====
Analysis is complete. Full review below.

---

Your `[resolved:]` confirmation is **correct** — I reproduced it independently: `header_error("## 2026-09-01 [resolved:]")` → `None`, `added_entry_problems` → `[]`, `verdict` → `(0, 'no tracked files changed outside the exempt paths')`, while `parse_entries` sets `error = "[resolved:] with no entry id after it"`. Not re-reported. `**_NO-ENTRY:_**` skipped as instructed.

You asked for other shapes in the same class. I swept the boundary by differential execution — same entry text through `added_entry_problems` and through `parse_entries` (including its PASS 2). **Four more shapes, three of them a different root cause than the empty payload.** They are H1 and H2 below.

---

**HIGH (H1) — the header/page divergence is not one bug: four more shapes pass the gate and render broken, and two of them are body-level, which `added_entry_problems` cannot see by construction**

- WHERE: `scripts/check-dashboard-entry.py:328-358` (`added_entry_problems`) vs `scripts/gen-dashboard.py:487-520`
- WHAT: executed differential, gate rc vs page error, one entry per row:

| entry | gate | page error |
|---|---|---|
| `## 2026-09-01` + blank first body line | `rc=0` | `no title line — the first line after the header is blank` |
| `## 2026-09-01 [resolved:   ]` (whitespace payload) | `rc=0` | `[resolved:] with no entry id after it` |
| `## 2026-09-01 [resolved: 1999-01-01/1]` | `rc=0` | `[resolved: 1999-01-01/1] names no entry in this file` |
| `## 2026-09-01 [resolved:x] [resolved:x]` | `rc=0` | `[resolved: x] names no entry in this file` |

  The whitespace-payload row is the same root as your `[resolved:]` find (`FLAG`'s `[^\]]*`), but the other three are **not**: the blank-title error comes from `gen-dashboard.py:506`, and the dangling-reference errors from PASS 2 at `gen-dashboard.py:509-519`. Neither is reachable from a header check at all.
- WHY IT MATTERS: the scope comment says the gap is bounded and names exactly one excluded consumer —
  ```
  ⚠ SCOPE, stated so the gap is visible rather than implied: this validates the
  HEADER only. The decision grammar (`decision_errors`) is enforced by the
  RENDERER and deliberately NOT wired in here …
  ```
  (`check-dashboard-entry.py:344-349`). Naming one exclusion reads as an enumeration of the exclusions. There are at least three more renderer-side `entry["error"]` producers, every one of which renders "Could not parse this entry" — the exact string `verdict`'s new refusal text promises to prevent. This is a completeness claim in the one comment whose job is to bound a gap.
- FIX: stop deriving the gate's verdict from a header regex and derive it from the renderer. `added_entry_problems` should reconstruct the added block and call `gen-dashboard.parse_entries`, reporting any `entry["error"]`; PASS 2 needs the whole file, so read the post-merge file rather than the patch. If that inversion is too large for a follow-up, then the scope comment must say *"there are N renderer-side error producers and this checks one of them"*, and list them — otherwise the next reader believes the boundary is closed.

---

**HIGH (H2) — `(?!#)` is itself a member of this class, and its stated justification is measurably false**

- WHERE: `scripts/check-dashboard-entry.py:322-325` vs `scripts/gen-dashboard.py:360`
- WHAT:
  ```python
  # `(?!#)` keeps `###` out: a level-3
  # heading is ordinary body markup and several entries use one, so treating it as a
  # failed entry header would refuse them.
  ENTRY_ISH = re.compile(r"^\+##(?!#)")
  ```
  The renderer's splitter is `BLOCK = re.compile(r"^##\s*\S")`. `\s*` matches zero characters, so `\S` matches the third `#`. Executed: `BLOCK.match("### Worth knowing")` → `True`. End to end on an entry-only branch:
  ```
  GATE  verdict -> (0, 'no tracked files changed outside the exempt paths')
  PAGE  '## 2026-09-01'     -> error: None
  PAGE  '### Worth knowing' -> error: header must be '## ' then a YYYY-MM-DD date …
  ```
  The justification is false as measured: `docs/dashboard-entries.md` contains **zero** `^###` lines. "Several entries use one" is true of no entry, and had one existed the page would already be broken by it — the premise refutes itself. The commit message repeats it ("load-bearing in the other direction … Mutation-covered"), and the manifest entry `entry-attempt regex stops excluding sub-headings` now pins the divergence in place.
- Two smaller divergences fall out the same way (executed): `+## `, `+##`, `+## \t` are **refused by the gate** and treated as ordinary body text by `BLOCK`.
- WHY IT MATTERS: `header_error`'s docstring is *"Shared by the parser and the ratchet so they CANNOT disagree about what a header is"*. That claim was already false for `[resolved:]`; `(?!#)` adds a second, self-inflicted disagreement introduced by the very PR that invokes the docstring.
- FIX: one regex, not a near-copy. Move `BLOCK` into `check-dashboard-entry.py` beside `HEADER`/`FLAG`, have `gen-dashboard.py` import it, and set `ENTRY_ISH = re.compile(r"^\+" + BLOCK.pattern[1:])`. Delete the `###` self-test case and its mutation — they assert the divergence. If `###` bodies are wanted, the change belongs in `BLOCK`.

---

**HIGH (H3) — the widened matcher retroactively re-judges merged PR bodies; the page's exemption list went from empty to one entry, and that entry is false**

- WHERE: `check-dashboard-entry.py:96-120` consumed by `gen-dashboard.py:724-756` (`no_entry_prs`)
- WHAT: `no_entry_prs` re-reads the last 40 **merged** PR bodies through the gate's *current* `exemption_reason`. Live run:
  ```
  err: None
   #198 Repair master: the #80 palette retune orphaned a mutation an
        reason='repair of a red I introduced in #197; … this restores coverage for.**'
  ```
  Diffing new-vs-old semantics across all 40 bodies, #198 is the **only** divergence (`old=None`, `new=<above>`). Its body line 18 is `**NO-ENTRY: … coverage for.**`, and `git show 86ecade5 --stat` shows `docs/dashboard-entries.md | 49 ++++…` — that PR **wrote an entry**. It passed via `added_entry`, never via an exemption.
- WHY IT MATTERS: `no_entry_prs`'s own docstring: *"the page shows exactly the exemptions the gate granted. A display that disagrees with the gate is worse than none."* Before #203 the list was empty; 100% of its current content is wrong, and §7 exists precisely so someone can count exemptions. Nothing in the change considered that widening a matcher rewrites history for a display fed by merged-PR bodies.
- FIX: don't re-derive a verdict for PRs already judged — bound the listing to PRs merged on/after the widening, or record the granted exemption at gate time instead of re-parsing bodies later.

---

**MEDIUM (M1) — the closer is stripped only when adjacent to the marker, so the one real-world bold shape leaks `**`; no case covers it**

- WHERE: `check-dashboard-entry.py:112-120`
  ```python
  rest = rest[len(NO_ENTRY):]
  if opener and rest.startswith(opener):
      rest = rest[len(opener):]
  return rest.strip()
  ```
- WHAT: executed — `exemption_reason("**NO-ENTRY: x**")` → `'x**'`. The handled shape is `**NO-ENTRY:** reason`; the shape people write, and the only one in 40 merged bodies (#198), is `**NO-ENTRY: reason**`. `page_markup.render_inline` emits the trailing `**` literally (verified: output ends `…coverage for.**`). No `case(...)` covers it.
- FIX: `if opener and rest.rstrip().endswith(opener): rest = rest.rstrip()[:-len(opener)]`, plus the case using #198's literal.

---

**MEDIUM (M2) — one new case is vacuous, and its comment names a falsifier that does not falsify**

You asked specifically for these. I tested all ~30 new cases by reverting in `/tmp` copies (repo untouched) — four reverts plus the naive implementation the code itself names. Results:

| revert applied in `/tmp` | new cases that go red |
|---|---|
| `EMPH` never matches (undo #203) | 8 |
| `added_entry_problems` returns `[]` | 4 |
| `verdict` ignores `entry_problems` | 7 |
| closer-strip unconditional | 6 |
| `ENTRY_ISH` loses `(?!#)` | 1 |
| naive `rest.lstrip("*_").strip()` | **1** |

- WHERE: `check-dashboard-entry.py:482-485`
  ```python
  # ⚠ Emphasis in the REASON is the author's text and must survive verbatim. A
  # naive lstrip("*") on the remainder would eat it.
  case("emphasis inside the reason is preserved",
       exemption_reason("NO-ENTRY: keep **bold** here"), "keep **bold** here")
  ```
- WHAT: built exactly that naive implementation and ran the suite: **103/104**, and the single failure is a different case — `[FAIL] a mismatched closer is left in the reason: got 'odd' want '* odd'`. The advertised case survives. It also survives the `EMPH` revert, i.e. it holds identically in the pre-#203 world — genuinely vacuous with respect to this change. Its sibling `"...and also when the marker itself was emphasised"` survives the naive implementation too (it only fails the `EMPH` revert), so it is vacuous with respect to the named threat though not to the change.
- The named threat is covered by exactly one case, `"a mismatched closer is left in the reason"` — not by either case advertised as covering it.
- FIX: move the comment onto the mismatched-closer case where it is true; change this case's input to one that discriminates (e.g. `NO-ENTRY: **bold** first` → `**bold** first`, which `lstrip("*_")` does eat) or delete it.

Every other new case is load-bearing against at least one revert. No other vacuity found.

---

**MEDIUM (M3) — `check-plan-code.py`'s narrative describes a bump that is not the one recorded**

- WHERE: `scripts/check-plan-code.py:450-457` and `:1967-1971`
  ```python
  # ⟳ 2026-09-01, backlog #78: 18 -> 23. …
  # THREE of the five mutations are on the WIRING …
  "scripts/check-dashboard-entry.py": 27,
  ...
  # ⟳ 141 -> 146, backlog #78 (five entries on the entry gate's content check).
  case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 150)
  ```
- WHAT: `git show 8b395aaf:scripts/check-plan-code.py` confirms #201 wrote `23`/`146` with matching prose. #203 added four more mutations (manifest is 27 entries) and bumped both literals to `27`/`150` **with no ⟳ line of its own**. Nothing mechanical catches it — I ran `check-docs.py` (rc=0), `check-selftest-counts.py` (rc=0) and `--mutate .` (green).
- WHY IT MATTERS: this file's convention, stated in its own entry at `docs/dashboard-entries.md:1413`, is that every bump carries a paragraph naming what bought it. Four mutations now have none, and an auditor reads a baseline four short.
- FIX: append a second ⟳ line for #203's `23 -> 27` / `146 -> 150`, leaving #201's paragraph alone.

---

**LOW (L1) — the mutation named for the ORDER does not test the order**

- WHERE: `scripts/mutations/check-dashboard-entry.json`, `"the content check sinks below the exemption short-circuit"`, edit `"    if entry_problems:"` → `"    if entry_problems and False:"`
- WHAT: the edit deletes the check; it does not move it. You asked specifically about the order claim, so: **the order is genuinely covered, but by a case, not by this mutation.** Relocating the block below `if not real: return 0, …` turns `"entry-only branch with a MALFORMED entry is refused"` red — that case is `verdict(["docs/dashboard-entries.md"], False, "", ["bad header"])`, where `real` is empty, so it can only pass if the check runs first. The author's "the ORDER is the fix" claim stands; only the mutation's name overstates what it does.
- FIX: rename to `"the content check is disabled"`, or make the edit an actual relocation.

---

**LOW (L2) — `verdict`'s new parameter defaults to `()`**

- WHERE: `check-dashboard-entry.py:361-362` — `entry_problems: list[str] | tuple = ()`
- WHAT: `grep -rn "collect(" --include=*.py scripts/` returns only this file's definition, self-test and `main`, plus an unrelated `collect` in `gen-goals-page.py:173` — so the 3-tuple→4-tuple change breaks no caller; that class is empty. But the default makes the content check opt-in for every future caller, guarded only for `main`.
- FIX: make it a required positional; there are two call sites.

---

**Classes checked and found empty, so you know what is not covered by silence**

- **`added_entry_problems` on real patch input** (you asked): executed against `+++ b/docs/dashboard-entries.md`, `--- a/…`, `@@ -1,2 +1,3 @@`, `+####`, CRLF (`+## 2026-08-28 [needs-you]\r` → `[]`). No false matches, no misses. The `+++` header does not match because position 1 is `+`, not `#`.
- **Fenced `## ` inside an entry body** (you asked): **not a defect.** `BLOCK` is fence-blind too, so a fenced `## 2026-…` example breaks the page as well; the gate refusing it is the renderer's own behaviour, not a divergence. Measured: `docs/dashboard-entries.md` currently has 13 fenced lines and none starts `##`.
- **The two repaired anchors** (you asked): `if not _indented(head): → if True:` removes exactly the indent conjunct its predecessor removed — original intent preserved. `if not rest.startswith(NO_ENTRY): → if NO_ENTRY not in rest:` is **stronger** than its predecessor, because `_declaration_reason` now serves both scan points instead of one; I confirmed it still reddens via the case it names (`"> NO-ENTRY: quoted"` → `'Y: quoted'`, not `None`). Neither is weaker.
- **Emphasis false passes**: executed `***NO-ENTRY:*** x`→`x`, `_NO-ENTRY:_ x`→`x`, `- **NO-ENTRY:** x`→`None`, `> **NO-ENTRY:** x`→`None`, `****NO-ENTRY:**** x`→`None`. No non-deliberate shape exempts.
- **The four inert contexts under emphasis**: pass for the right reason (the fence/indent/comment scan runs before `_declaration_reason`), though the blockquote case is redundant with the manifest's `"line-leading rule removed"`.
- **Verification claims re-run**: `--self-test` → `104/104` + `13/13`; `check-plan-code.py --mutate .` → `OK — 7 file(s), 150 mutation(s), 0 survivor(s)`; `check-docs.py` rc=0; `check-selftest-counts.py` rc=0.
- **UNVERIFIED — treat as NOT RUN**: `tsc --noEmit`, the 2819-test unit suite, and the `service_role` confinement check. I did not execute them and make no claim about them.

VERDICT: NOT CONVERGED