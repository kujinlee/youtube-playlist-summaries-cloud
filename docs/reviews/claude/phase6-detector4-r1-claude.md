Reviewed head: 637950d2d159740a9c2885dc13ef531051951c89

# phase6-detector4 — round 1, Claude half

Subject: `git diff 49c3f923..637950d2` (`scripts/check-publishability.py`, `scripts/mutations/check-publishability.json`,
`scripts/mutations/expected_mutations.py`, `docs/marketplace/scan-2026-11-17.json`), against the build spec of
`docs/reviews/architecture-review-2026-11-21-publishability-detector4.md` §5–§6.

Method: I read the diff line by line and asked, for each branch of `_Blocks` and `introduces()`, what input reaches
it and what HEAD's code did with that input. Every input below was run through BOTH versions. HEAD's file was taken
with `git show 49c3f923:scripts/check-publishability.py` into a scratch copy outside the repository, and the build's
file was copied the same way; both were loaded side by side and `classify_match` / `_markdown_kind` were called on
fixture `.md` files in scratch. Nothing in the worktree was mutated.

## Findings

### BLOCKER 1 — any line starting with `#` is a heading, and a heading is a one-line block: a tracked file loses 3 dependencies

`scripts/check-publishability.py:317` (`elif ln.lstrip().startswith("#")`) and `:371` (`before` returns `(j, j)` for a
heading).

This is a silent loss caused by the build. It is observed on a tracked file:

- `docs/superpowers/specs/2026-09-25-decision-card-soundness-design.md:386` term `reach`, `:386` term `aim`,
  `:387` term `Can a redesign remove it?`: **HEAD = dependency, build = mention.** The introducer is line 384,
  `#136 also carries:`, which continues a paragraph that holds "cannot **read** as exhaustive". `#136` is not a heading
  in CommonMark, which needs a space after the `#`s. HEAD's `_introduced` tested the colon line, whatever it was, and
  then joined the non-blank lines above it, so it found `read`. The build classifies the line as `heading`, reads it
  as a one-line block, finds no `LEAD_VERBS` word in it, and so nothing introduces the list.
- Minimal repro: `Read the notes before you start, it\n#136 also carries:\n\n- \`aim\`\n` gives HEAD dependency,
  build mention. With `#136` replaced by `No. 136`, both give dependency.
- The same mechanism applies to a real heading with prose directly above it and no blank line between:
  `Please run everything below\n## Setup:\n\n- \`CronList\`\n` gives HEAD dependency, build mention.
  `Then run the steps\n### Steps:\n\n\`\`\`\nCronList\n\`\`\`\n` (an untagged fence) gives HEAD dependency, build mention.
- How common the shape is: 219 lines in 122 tracked `.md` files start with `#<digit>`. These are backlog numbers that
  wrap to the start of a line.

Scope against the stop condition: FAILS IF 1 is defined over §4.2's set, which excludes `docs/superpowers/`. Over that
set I observed **0** losses (below). Over the tracked `docs/superpowers/` set I observed **3**. These contradict the
§6 invariant "the build reports every dependency the function it replaces reported". Whether that triggers the
fallback to N is for the coordinator to decide; I am reporting the observation.

### MAJOR 2 — the list model drops HEAD's dependencies on indented lists and on uneven sibling indents (constructed; 0 on the tracked corpus)

`scripts/check-publishability.py:358` (`first_sibling`'s break) and `:336–350` (`owner`).

These are silent losses caused by the build, and every one was constructed. HEAD's walk climbed through any list item
at any indent, and through any adjacent indented line. The build's `first_sibling` has three differences:

- it ends the list at a text, table or fence line at or left of the item's indent;
- it never treats an earlier, deeper-indented item as a sibling;
- it ends the list at any heading-class line, even an indented one.

When there is no enclosing owner to climb to, the dependency is lost. Each row below gives **HEAD dependency → build
mention**:

| Input (term `CronList`, last line) | Shape |
|---|---|
| `Run these:\n\n 9. \`CronA\`\n10. \`CronList\`\n` | right-aligned numbers: the first item is 1 column deeper |
| `Read these:\n  - \`CronA\`\n- \`CronList\`\n` | first item deeper than a later sibling |
| `Run these:\n\n  - \`CronA\`\n  more about A\n  - \`CronList\`\n` | an indented list with a (lazy) continuation at the item indent |
| `Run these:\n\n  - \`CronA\`\n  \`\`\`\n  x\n  \`\`\`\n  - \`CronList\`\n` | an indented list with a fence at the item indent |
| `Run these:\n\n  - a\n  \| t \|\n  - \`CronList\`\n` | an indented list with a table line at the item indent |
| `Run these:\n- a\n  # note\n- \`CronList\`\n` | an indented `#` line between top-level items |

When the list is nested under an item, the climb through `owner` recovers it. For example,
`Run these:\n\n- a\n  - \`B\`\n  cont\n  - \`X\`` is a dependency in both versions. So the loss is limited to a top-level
list that is itself indented, or whose first item is deeper than a later one.

The third row also meets FAILS IF 3 in its literal form. Deleting the line `more about A`, which lies outside the
term's sentence and outside the introducing block, turns mention into dependency. The build would call this
structure ("prose at the list's own indent ends it"). But for an indented list, that line is a lazy continuation in
CommonMark, not prose that ends the list.

### MINOR 3 — a table-class line can no longer introduce or join an introducing paragraph (constructed, contrived)

`scripts/check-publishability.py:371` (`table` is not in `before`'s accepted classes) and `:327` (`start` joins only
`text`).

This is a silent loss caused by the build, and both inputs are unlikely in real prose:

- `| Step | Run these:\n\n- \`CronList\`\n` (a pipe row with no trailing pipe, ending in a colon): HEAD dependency, build
  mention.
- `| run | x |\nthe following:\n\n- \`CronList\`\n`: HEAD dependency, build mention.

### MINOR 4 — "REQUIRES on the line is redundant" is refuted for a self-overlapping term (unreachable on today's vocabulary)

`scripts/check-publishability.py:408–411`.

The unit test iterates `re.finditer(tok, unit)`, and `finditer` yields only non-overlapping matches. HEAD's single
`re.search(REQUIRES + lookbehind + tok, text)` backtracked onto an overlapping occurrence. Input
`This requires ba-a-a here.\n` with term `a-a` gives **HEAD dependency, build mention**. The first non-overlapping
match, `a-a` right after the `b`, fails the lookbehind, and the overlapping match one position later, which HEAD
found, is never tried.

To reach this, a term needs a border, meaning a prefix equal to its suffix, AND the character before that border
inside the term must not be alphanumeric. The live vocabulary (16 derived terms plus 42 harness tools) has 8 bordered
terms (`tasklist`, `workflow`, `remotetrigger`, …). All have border length 1, preceded by a letter, so none can reach
it today.

The fuzzer I ran (200,000 random 1–3-line inputs; 31,328 HEAD-REQUIRES hits; 0 misses) found nothing else. Apart from
this, the claim holds.

### MINOR 5 — the folded INSTRUCTS-on-paragraph is not the spec's form (precision direction, no loss vs HEAD)

`scripts/check-publishability.py:395–423`.

Spec §5.1(3) says to try `INSTRUCTS` "on the paragraph joined up to the term". The build folds that into the
every-span test, and the two are not equivalent. `INSTRUCTS`'s gap `[^\`.]*` admits `!` and `?`, but `SENTENCE_END`
ends a sentence at them. On the input `Run it!\nThen \`CronList\` again.\n`, the spec's joined-INSTRUCTS matches
(observed: `re.search(INSTRUCTS + tok, unit)` is True), while the build gives mention and HEAD gives mention. The same
holds for `Read it? Or\n\`CronList\`.` and `Use the tool!\n\`CronList\``.

The build is arguably more correct here. This is an unrecorded deviation, not a loss.

### MINOR 6 — the 1 MB timing case's prose half does not witness the unit bound

The new case "one term in a file holding a 1 MB table, or a 1 MB run of non-blank prose lines, is judged within 1 s
(FAILS IF 6)" stays green under mutation "sentence: the unit is unbounded" (`self.start(i, max(0, i - UNIT))` →
`self.start(i, 0)`). Only "the joined sentence looks back at most 12 lines" goes red (nfail=1). Its table half is
witnessed: "a table row joins the paragraph above it" turns it red.

So the case name claims a FAILS IF 6 guard on prose, but the prose half passes whether or not the bound exists. The
bound itself is still killed by the 12-line case.

## Observed, no finding

- **Self-test:** `python3 scripts/check-publishability.py --self-test` → `116/116 self-test cases passed`, which
  matches the docstring's line 5 count of 116.
- **Differential (HEAD vs build `_markdown_kind`, every `(line, code-span content or CamelCase word)` pair):**

  | Set | Pairs | Losses | Gains |
  |---|---|---|---|
  | §4.2 set (296 files) | 9,725 | **0** | 77 |
  | `docs/reviews/` (2,986 files) | 212,197 | **0** | 1,152 |
  | `docs/backlog.md` + `docs/roadmap-to-launch.md` + `docs/dashboard-entries.md` | 22,878 | **0** | 49 |
  | `docs/superpowers/` (203 files) | 54,336 | **3** (BLOCKER 1) | 980 |

- **Live scan:** a fresh `--out` scan, written to scratch, equals `docs/marketplace/scan-2026-11-17.json` once
  `measured_at` is removed. No `(component, detector, file, text, term)` row of the 49c3f923 report is absent from it,
  and 22 rows are new. Scan time: 25.0 s. Detector 1 calls the same `_markdown_kind`, so the differential above covers
  it; it showed no live loss.
- **Time:** one term in a 50,000-item flat list (950 KB) took 0.044 s (HEAD 0.049 s). A 20,000-pair nested list took
  0.040 s, and a 300-deep nest took 0.003 s. The whole-file scan is quadratic for a flat list where every line holds a
  term (`first_sibling` per item). No tracked file reached the 1 s bound: the full scan ran in 25 s.
- **FAILS IF 5:** `LIST_ITEM.match` and `FENCE.match` each occur once, at `:319` and `:308`, both inside `_Blocks`.
  `NEGATES` and `_introduced` are gone.
- **Mutations:** I applied all 31 new or re-anchored `check-publishability.py` entries one at a time, each to its own
  scratch copy of `scripts/`, with `PLAN_CODE_MUTATION_RUN=1`. The control was 106/106 green. All 31 anchors resolved
  exactly once, and **all 31 turned their named `expect` case red**. Spot-checked for an ambient pass:
  - "a read instruction on its own line" is killed only by `Some context with no stop\nRead \`CronList\` first.`, the
    one input whose only path is line-INSTRUCTS.
  - "a lazy line joins any item" is killed by `- Read the guide\nSome notes:\n- \`CronList\``.
  - "a continuation line does not reach the item" is killed by `1. Run the\n   following:\n   - \`CronList\``.

  Each of these is a real witness of its branch. The spec asked for the two `NEGATES` mutations to be removed. The
  build removed one and re-aimed the other so that it re-adds the filter, which the p6 prohibition case kills. That is
  a stronger choice than removal.
- **Spec match:**
  - Deleted as the spec says: the fence scan, the list walk, `_introduced`, and `NEGATES`.
  - Added beyond the spec: the fence climb `b.climbs(b.owner(opened))` (spec §5.1(2) asks for it: "including a fence
    inside an introduced item"), the table class, and `UNIT = 12` (both from §4.3).
  - Not as the spec says: the two admitted deviations, assessed in MINOR 4 and MINOR 5.

VERDICT: NOT CONVERGED
