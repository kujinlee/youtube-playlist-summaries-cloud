# Round 3 — review-tooling-121-182 — claude

**NOT CONVERGED.** The round-2 bet is refuted on both of its clauses: an example acts as a declaration (finding 1 shows it live, in this PR's own round-2 Codex document), and a `--out` spelling writes into `docs/reviews/` without being refused (finding 3).

Reviewed: `git diff f8350e1f..ffff1e0e` first, then the branch against `origin/master`, at `ffff1e0e`, in the worktree `wt-121`. All experiments ran on scratch copies under `scratchpad/r3exp/`. Nothing in the worktree was edited.

## Gates run (at ffff1e0e)

| Check | Result |
|---|---|
| `codex-review.py --self-test` | 191/191, rc 0 |
| `check-review-rounds.py --self-test` | 119/119, rc 0 |
| `check-review-recorded.py --self-test` | 198/198, rc 0 |
| `check-review-rounds.py` (live) | rc 0: 619 rounds, 41 exemptions, 0 silent gaps, 437 verdicts |
| `check-plan-code.py --mutate . --only scripts/codex-review.py` | 60/60 killed, 0 survivors, rc 0 |
| `… --only scripts/check-review-rounds.py` | 55/55 killed, 0 survivors, rc 0 |
| `… --only scripts/check-review-recorded.py` | 69/69 killed, 0 survivors, rc 0 |
| Four hand mutants of `preamble()` (finding 4) | **all four survive, 119/119** |

## Findings

### 1. Blocking — `scripts/check-review-rounds.py:243` (`preamble`): most documents have no `## ` heading, so for them the preamble is the whole document and X1/X2 still reproduce. It is live on this branch.

**Fix-induced: no.** X1/X2 were never fixed for the document shape most of the corpus uses. **Component: gap-reader.**

The redesign assumes findings sit under a `## ` heading. Measured over every round-numbered document in `docs/reviews/` (`r3exp/audit_repro.py`): **465 of 555 codex halves** and **181 of 315 coordinator documents** contain no `## ` outside a fence. For those documents `preamble()` returns everything, so the position rule excludes nothing. The round-2 numbers ("179 of 191 gap lines are in the preamble", "247 of 251 headers come before the first `## `") are true, but they do not show what they were meant to: in two thirds of the corpus the preamble *is* the document, so "inside the preamble" holds for every line whether it is a declaration or an example.

**Live on this branch.** The r2 Codex half (`docs/reviews/codex/review-tooling-121-182-r2-codex.md`) has no title and no `## `. It quotes the X2 input inside a numbered list item, and the fence is indented, which `FENCE` does not recognise:

```
$ python3 -I -c '…m.declared_gap(<the 5 review docs this branch adds>)'
declared_gap -> docs/reviews/codex/review-tooling-121-182-r2-codex.md — codex: example only
```

So `check-review-recorded` reads the r2 Codex review's own *example* as this branch's `REVIEW GAP: codex` declaration. Today `tail_verdict` passes `gap` over without using it, because this branch has Codex verdicts (the live run exits 1 for the stale tail, as it should). On any branch whose Codex runs all failed, the same quoted line would turn rc 2 (CANNOT RUN) into rc 0.

Constructed inputs, both run:
- **A1 (rounds gate).** A sole `p-r1-codex.md` written in the r2 Codex half's own shape: wrapper stamp, bold verdict, `1. **Major — …**`, an indented ```` ```text ```` block quoting `REVIEW GAP: claude — example only`. `audit(…, set())` returns `[]`, so a claude half that never ran is excused.
- **A2 (final-tree rule).** The same document quoting a codex gap. `first_codex_gap` returns `…p-r1-claude.md — codex: example only`, and `tail_verdict({}, 0, gap)[0] == 0`.
- **X1 in its natural form.** `# Round 1 codex\n\n**Major: example input**\n\n```yaml\nhalves:\n  claude: "GAP: example only"\n```` gives `gap_reasons` = `{'claude': 'example only'}`. The new X1 case passes only because its fixture puts a `## ` heading before the yaml.

This is the bet's named failure observation, so the decision log's route is now SPLIT. The position rule cannot be repaired by tuning the heading: a reviewer's free-form final message has no structure the reader can depend on.

### 2. Major — `scripts/check-review-rounds.py:262-266` (`preamble` fence tracking): a CommonMark-legal fence opener that `FENCE` does not recognise turns its own closer into an opener, which hides every later `## `.

**Fix-induced: yes** (the fence-aware preamble, deviation (b)). **Component: gap-reader.**

`FENCE = ^(`{3,})(\S*)[ \t]*$` rejects an info string that contains a space, such as ```` ```sh title=repro ````, which CommonMark accepts. The opener is skipped, its closing ```` ``` ```` matches as an *opener*, and the rest of the document becomes "fenced". No `## ` is ever seen, so the preamble runs to the end of the file. A document that does use `## ` headings can therefore have an example under one of them read as a declaration:

```
# Round 1 — p — codex / Repro: / ```sh title=repro / echo hi / ``` / ## Finding 1 (Major) / … / ```text / REVIEW GAP: claude — example only / ```
audit(sole p-r1-codex.md, set())  -> []                                   # claude half excused
…same document, opener changed to a bare ```  -> ['p round 1: only codex — claude neither ran nor recorded …']
```

The control differs only in ` title=repro`. The live corpus already has two such openers: `plan-project-dashboard-r6-codex.md` (```` ```bash 8 ````) and `closing-table-r3-codex.md` (```` ``` stray ````). There is a sibling of the same class: an indented opener (a fence inside a list item) with an unindented closer also hides the `## ` that follows (`r3exp/probe.py`, case "indented fence opener").

### 3. Major — `scripts/codex-review.py:549` (`resolve_out`) and `:592` (`out_location_refusal`): on macOS's case-insensitive filesystem, a case variant of `docs/reviews` is neither refused nor normalised.

**Fix-induced: no** (the lexical comparison in r1 missed it as well). **Component: codex-review.**

`os.path.realpath` follows symlinks but does not fold case, and the comparison is a byte-for-byte prefix match:

```
'/Docs/Reviews/claude/x.md'  NOT refused      '/docs/reviews/claude/x.md' refused
'/DOCS/reviews/codex/new.md' NOT refused
temp tree with docs/reviews/claude/: --out <T>/Docs/Reviews/claude/p-r1-claude.md
  resolve_out -> /Docs/Reviews/claude/p-r1-claude.md ; refusal -> None
  after a write: os.listdir(<T>/docs/reviews/claude) == ['p-r1-claude.md']
```

The capture lands in a writer directory without being refused. The only directory watched for it is `--out`'s own, where the file is the expected write. This is the bet's second clause. The input is cheap to produce by accident, for example a tab-completed `Docs/`. A possible fix is to compare `os.path.samefile`/`os.stat` (dev, ino) of the deepest existing ancestor against each tree, or to normalise case when the volume is case-insensitive.

### 4. Minor — `scripts/check-review-rounds.py:262-270`: the sub-rules of the new fence tracking and title rule have no case; four hand mutants survive.

**Fix-induced: yes. Component: mutation-manifest** (and the cases behind it).

I applied each mutant on a copy of `scripts/`, ran `check-review-rounds.py --self-test`, and restored the file before the next one:
- M1 `len(f.group(1)) >= len(fence)` → `==`: 119/119 pass
- M2 drop `not f.group(2)` (a closer may carry an info string): 119/119 pass
- M3 drop the length rule (```` ``` ```` closes a ```` ```` ```` fence): 119/119 pass
- M4 `title is None` dropped (every `# ` line is removed as "the title"): 119/119 pass

M3 matters in practice. Nested fences (```` ````markdown ```` around ```` ```yaml ````) are exactly how the X1/X2 reproductions are quoted in this subject's own review documents. The manifest's one fence mutant removes fence awareness entirely, so it says nothing about these sub-rules.

### 5. Minor — `scripts/check-review-rounds.py:169` (`GAP`) and `:265`: a gap written as a `## REVIEW GAP:` heading can no longer be read.

**Fix-induced: yes. Component: gap-reader.** It fails closed.

The heading is itself the first `## `, so it ends the preamble before it can be read: `gap_reasons('# Round 2 …\n\n## REVIEW GAP: claude — alternation\n…') == {}`. That is the most emphatic way to write a declaration, and 5 of the 16 new KNOWN rounds use it (`fix-src-viewer-escaping` r1 and r2, `seed-explainer-serve-manifest` r1–r3). The leading `#` that `GAP` still allows advertises a form the gate now rejects, and the template row does not mention it. The next coordinator to write it gets a false red, or another exemption.

### 6. Minor — `scripts/check-review-rounds.py:279` (`header_body`), deviation (a): a fence above the title is now "the header".

**Fix-induced: yes. Component: gap-reader.**

`Example of the template:\n\n```yaml\nhalves:\n  claude: "GAP: example"\n```\n\n# Round 1 — s — codex\n\n## F\n` reads as `{'claude': 'example'}`. Nothing in the corpus does this today; I checked, and it is not observed. It is still an example acting as a declaration by construction, and the template row now places the header in "the first fence of the preamble", which includes the lines above the title.

## The 16 KNOWN exemptions are honest

I read every round's documents. Each one records a gap that really happened, and none hides a half that never ran behind a quotation:
- **closing-table r7, r8, r11:** the claude half is present, and its codex gap sits at the end of the document.
- **closing-table r10:** the codex half is filed under `coordinator/`. It declares the claude gap at line 62 and the absence at line 5.
- **fix-src-viewer-escaping r1 and r2, seed-explainer-serve-manifest r1–r3:** the coordinator writes the gap as a `## REVIEW GAP:` heading (finding 5).
- **late-flush-escalation-code r1, referential-entry-gate-code r1:** "Agent tool disabled" at the end of the document.
- **pin-python-interpreter r4, r6, r7:** the claude gap is at the last line, with a by-protocol note at line 5.
- **plan-coverage-verdict-union r1:** coordinator line 13, in the preamble but after a `## `.
- **recall-llm r9:** a blockquoted `### REVIEW GAP: claude` that records the redirect to the architecture review.

The live gate's stale-entry rule confirms that all 16 are still violations without the exemption.

I also checked the converse: does any un-exempted round with a missing half pass *only* through a quoted line (inside a fence, a blockquote, or backticks)? There is exactly one hit, `plan-guard-inventory-population` r2, and it is a real declaration styled as a blockquote. So no live round is wrongly excused today. The defect in finding 1 lives in the reader and in this PR's own r2 Codex document, not in a merged round.

## Not findings (checked)

- `resolve_out` on `alias/..`, a dangling final symlink, `nonexistent/..`, and `docs//reviews` all resolve to the true destination and are refused.
- The X4 watch of a missing directory works, within the stated non-recursive bound. A write into a writer subdirectory created during the run is unseen, which is the documented trade, not a new hole.
- The new X3, X4 and X5 cases each fail through the case they name. Their mutants are in the manifest and are killed.

## Thrashing

The gap-reader carried a fix-induced finding in round 2 (X2) and carries three in round 3 (findings 2, 5 and 6), all caused by the round-2 fold's own preamble code. That is **two consecutive rounds with fix-induced findings in one component**, which meets the arming condition in `dev-process.md`. Finding 1, which is not fix-induced, is the bet's named failure, so the route moves to SPLIT.

| Severity | Count | Fix-induced |
|---|---|---|
| Blocking | 1 | 0 |
| Major | 2 | 1 |
| Minor | 3 | 3 |

**NOT CONVERGED.**
