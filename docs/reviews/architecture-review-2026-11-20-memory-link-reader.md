# Phase 6 architecture review — the `link-reader` component of `scripts/check-memory-shape.py` (PR #605)

- Subject: `_COMMENT_RE`, `_keep_code`, `link_targets` and their self-test cases, branch `memory-shape-check`, read at
  head `0a077e70`.
- Armed by THRASHING: round 2's XM2 and Xm2 were caused by round 1's comment-stripping fold; round 3's Cm1 and Cm2
  were caused by round 2's code-span fold. Both in the component `link-reader`
  (`docs/reviews/coordinator/memory-shape-check-r{1,2,3}-coordinator.md`).
- Read first: the three coordinator documents, the four review halves, backlog row 677, `CONTEXT.md` (*Structural
  line*, *Rendered reachability*, the lesson vocabulary), the titles under `docs/adr/` (none governs a memory link or a
  guard's dependencies; nothing here re-opens one), and `docs/review-method.md` → *The stop condition*, *Can a redesign
  remove it?*, *The arming condition — full account*.
- Method: no tracked file was changed except this document. Every probe, prototype and mutant ran on copies in the
  session scratchpad, `…/scratchpad/p6-link-reader/` (`cms.py` is the script at `0a077e70`; `repo-mem/` and
  `live-mem/` are copies of `docs/memory/` and of the live memory folder). The differential runs render with
  `markdown-it` 14.2.0 (read from the main checkout's `node_modules`) and read the result with Python's `html.parser`.
  Local Python is 3.14.4; the prototype was also run on 3.12.9, the version CI pins.
- Every claim is tagged **[M]** (measured here: a command was run and its output read) or **[I]** (inferred).

## Verdict

**Redesign now, in this PR, as one fold. The shape is wrong, and a different shape removes the whole finding class.**

1. **A regex that approximates CommonMark is the wrong tool, and so is a real CommonMark parser.** The reader has to
   answer "does a reader see this link", and that depends on block structure, on HTML parsing of what the renderer
   passes through, and on which reader is meant. Against a real renderer today's reader gives a silent false pass on
   31,560 of 300,000 generated documents, in four classes. Review found one of the four. **[M]**
2. **The check does not need the answer it is approximating.** Both memory corpora hold ONE `<!--` and no comment at
   all. Today's reader, and a reader that strips nothing, return the same link set for every file in both. Three
   rounds on this component changed no verdict on any real file. **[M]**
3. **The redesign: bracket, do not parse.** Compute reachability twice, once with only the links that are certainly
   visible and once with every link, and REFUSE (rc 1, its own rule code) wherever the two disagree. It needs no
   knowledge of code spans, fences or blocks. It is about 30 lines replacing 12, and it deletes `_COMMENT_RE` and
   `_keep_code`. On both corpora it changes nothing: 0 new violations, 0 files to edit. **[M]**
4. **I tried to refute it and succeeded four times before it held.** Each refutation was closed by WIDENING what
   counts as uncertain, which can only add a loud refusal. The final form has 0 failures in 300,000 documents.
   That direction is the point: a fix to this shape cannot cause a silent finding. **[M]** for the count, **[I]** for
   the claim about every future fix.
5. **It closes backlog #677 item 1 whole and the link-reader half of item 2.** Items 3, 4, 5 and the escape half of
   item 2 are `frontmatter-parser`, which is not armed and is not touched.
6. **Why now and not filed:** today's impact is nil either way, so nothing is urgent. But the work that #677 item 2
   asks for is cases for the span and fence arms, which is test code for lines the redesign deletes. And the
   docstring's stated bound at line 72 is measured false at this head (Cm1c). If the owner prefers to merge first,
   the minimum is the proposed backlog row in section 6 and a one-line correction of that bound.

## 1. What the check needs: the corpus

`python3 measure.py repo-mem live-mem` and `grep -n '<!--'` over both folders. **[M]**

| | `docs/memory/` (worktree) | live folder |
|---|---|---|
| top-level `.md` files (index included) | 196 | 198 |
| `<!--` | 1 | 1 |
| `-->` | 0 | 0 |
| backticks | 7,076 | 7,108 |
| fence-opening or closing lines (backtick) | 26, in 13 files | 26, in 13 files |
| tilde fences | 0 | 0 |
| a fence line indented four spaces or more | 0 | 0 |
| a backslash-escaped backtick | 0 | 0 |
| index: `<!--` / backticks / fence lines | 0 / 70 / 0 | 0 / 74 / 0 |
| files where today's reader and a reader that strips NOTHING differ | 0 | 0 |
| violations today | 0 | 1 (FRONTMATTER, the known true positive) |

- The one `<!--` is `a-measurement-is-only-as-good-as-its-corpus.md:35`, inside a code span, in a sentence about an
  unclosed `<!--` that "runs to end-of-input". It is not a comment. Five wiki links follow it in that file. **[M]**
- So the corpus holds **zero HTML comments**. The stripping exists for an input no memory file has. **[M]**
- The live folder is a symlink to the MAIN checkout's `docs/memory` (`ls -ld`), so the two columns are two checkouts
  of one corpus, not two corpora. **[M]**

## 2. Is a hand regex the wrong tool? The differential

`fuzz_lib.py` builds documents from 22 tokens (`<!--`, `-->`, backtick runs of 1, 2 and 3, `~~~`, newline, blank
line, four spaces, `- `, `1. `, `# `, `> `, a backslash, `<!`, `<?`, `>`, and numbered links in both forms).
`render.cjs` renders each with `markdown-it` (`html: true`). The ORACLE is what an HTML reader then shows: text nodes
and `href`s, read with `html.parser`. Command: `python3 run3.py 25000 11 12 … 22` (12 seeds). **[M]**

| Over 300,000 documents | count |
|---|---|
| today's reader counts a link the rendered page does not show (SILENT: a false pass) | 31,560 |
| today's reader hides a link the page shows (loud: a false UNLISTED) | 17,906 |

The silent ones, by mechanism (classified by the construct present; shortest example of each):

| Mechanism | count | shortest | found by review? |
|---|---|---|---|
| a link in a fence INFO STRING (rendered as a `class` attribute) | 20,803 | `` ```[[t1]] `` | no |
| a bogus comment, `<!…>` or `<?…>` (an HTML parser reads both as comments) | 10,713 | `<?x[[t1]]` | no |
| span and block structure | 43 | `` `# \n<!--`[[t1]] `` | yes, Cm1 (a), (c) |
| an escaped backtick | 1 | `` \`    <!--`[[t1]]# ``````> ``--> `` | yes, Cm1 (b) |

Two things follow.

- **The next probe did find another construct, twice.** The two largest classes were reported by no round. The
  hypothesis in the brief holds as measured. **[M]**
- **A real CommonMark parser would not have been enough either.** Two of the inputs below are read correctly by the
  parser and still hide a link, because the HTML that the parser emits is then read by an HTML parser with its own
  rules. In ` - <!--\n--> >[[t1]]- ` the list item ends before the `-->`, so the renderer emits the `<!--` raw and
  ESCAPES the `-->`; the page then hides everything to its end. **[M]** A sound reader would need a CommonMark parser
  AND an HTML parser, in that order. That is `CONTEXT.md` → *Rendered reachability* again: "no predicate over text
  can compute it". **[I]**

The oracle's limits: `markdown-it` is not GitHub's renderer, and `html.parser` is not a browser. The counts are
about this pair. The token set is the comment, code and container syntax the three rounds argued; it is not all of
Markdown. **[I]**

## 3. The candidates

| | Candidate | Verdict | Why |
|---|---|---|---|
| (a) | a real CommonMark parser | **reject** | None in the Python stdlib; `markdown`, `markdown_it`, `mistune`, `commonmark`, `marko`, `cmarkgfm` are not importable here, and the repo has no `requirements*.txt` or `pyproject.toml` **[M]**. `markdown-it` 14.2 IS a dependency in `package.json`, and the CI job runs `npm ci`, so a Python guard could shell out to Node. But this worktree has no `node_modules` **[M]**, so the guard would be CANNOT RUN in every fresh worktree; and section 2 shows the parser alone is still wrong. |
| (b) | refuse any file holding `<!--` | **reject as stated** | It fails `a-measurement-is-only-as-good-as-its-corpus.md` today, a valid file whose `<!--` is in a code span **[M]**. Exempting code spans is the round 2 fold again. |
| (c) | keep the regex, bound it in the docstring | **reject** | The bound cannot be written. Section 2 has four classes and the token set was small. The bound at line 72 was already false one round after it was written (Cm1c). |
| (d) | strip nothing; a link in a comment counts | weaker | Exact, and right for the reader that reads raw text (section 5). It re-opens Codex r1 XM2, which was reproduced and accepted. |
| **(e)** | **bracket: two exact readers, refuse where they disagree** | **recommend** | Right for both readers, needs no Markdown knowledge, 0 corpus changes. It is (b) narrowed to the refusals that change a verdict. |

`CONTEXT.md` → *Structural line* records the same conclusion for the workflow readers: "The terminating move is
therefore not a wider pattern but a soundness check: refuse what cannot be classified." (e) is that move.

## 4. The redesign, and the attempts to refute it

**The rule.** A link is UNCERTAIN when it lies after the first `<!` or `<?` in its file, or on a line after a run of
three backticks or tildes. Every other link is SURE. Reachability is computed at both bounds:

- lower: SURE links only; upper: every link.
- `MISSING` = missing at the lower bound. `UNLISTED` = unreachable at the upper bound. Both are certain.
- A target missing only at the upper bound, or a file unreachable only at the lower bound, is reported under a new
  rule code (the prototype calls it `CANNOT-READ`), rc 1, naming the remedy: move the link above the `<!`, or off
  the fence line.

Reachability is monotone in the link sets, so if the true set lies between the bounds, every verdict the two bounds
agree on is the true verdict. **[I]** The prototype is `cms_bracket.py` (the script with `link_targets` and
`index_violations` replaced); `bracket.py` is the same logic for the differential.

**Refutation attempts.** Each row is an input built against the design as it stood. **[M]** unless tagged.

| # | Design as it stood | Refuting input | What it showed | Change |
|---|---|---|---|---|
| 1 | compare the two bounds as SETS, lower = links of the text with comments cut out | `[x](a<!-- -->.md)` plus `<!-- [y](a.md) -->` | cutting splices a link that no reader sees, and the sets agree by accident **[I]** (reasoned, not run) | the lower bound is the links whose POSITION is outside every region; nothing is cut |
| 2 | regions are `<!-- … -->` only | `` ```[[t1]] `` (724 of 937 failures in 20,000) | a fence info string hides a link with no comment at all | the rest of a fence line is a region |
| 3 | one regex with three alternatives | `` <!\```\n<!--``>\n>[[t1]] `` (90 in 100,000) | the `<!…>` alternative consumed a real `<!--`. **This is the round 2 defect, reproduced in my own prototype**: one leftmost scan lets one construct eat another's opener | every opener starts its own region; regions may overlap |
| 4 | `<!--` closes at the next `-->` | ` - <!--\n--> >[[t1]]- ` (21 in 160,000) | a container ends first; the renderer escapes the `-->` | `<!--` runs to the end of the file |
| 5 | `<!…` and `<?…` close at the next `>` | `> <?\\\n>- [[t1]]1. <!`` ` (1 in 200,000) | the `>` is a blockquote marker and is not in the output | `<!` and `<?` run to the end of the file |
| 6 | final | 300,000 documents, seeds 11–22 | **0** lower-bound failures, **0** upper-bound failures | none |

Every change in rows 2–5 made a region larger. A larger region can only move a link from SURE to UNCERTAIN, which
can only turn a pass into a refusal. None of the four could have caused a silent failure, and none did. **[M]** for
these four; **[I]** as a property of the design.

**What the final form costs.**

| Measure | Result |
|---|---|
| both corpora, violations added by the redesign | 0 **[M]** (`python3 widest.py repo-mem live-mem`) |
| files with an opener; link targets SURE / UNCERTAIN | 17 of 196; 940 / 13 (two files) **[M]** |
| UNCERTAIN links in the index | 0 **[M]** |
| existing self-test cases that change | 5 of 104, all on purpose (a comment-only link, the two Codex inputs, the fenced `<!--`, one `link_targets` case) **[M]** (`PYTHONPATH=…/scripts python3 cms_bracket.py --self-test` → `99/104`, same on 3.12.9) |
| each of the twelve review and fuzz inputs | every one is UNCERTAIN, none SURE **[M]** |
| mutations in the manifest that anchor to the deleted lines | 6 of 79 (the comment, unclosed-comment, fence, span, no-closer and keep-code entries) **[M]** (read from the manifest) |
| refusals that were needless in random documents | 76,266 of 124,890: the link was in fact visible **[M]** |

The last row is the price, stated plainly: the redesign refuses more than it must. It refuses the round 2 Codex
input, `` `<!--` [[a]] ``, which round 2 made pass. On the corpus that price is 0 today. It would be paid by a
future index that holds a literal `<!` above its rows: every file reached only through a later row would be
refused, loudly, with the remedy in the message. **[I]**

**Where the widening must stop.** Raw HTML tags and link reference definitions also hide links (2,773 lower-bound
failures in 100,000 documents once `<div `, `<script>`, `title="` and `[t]: ` join the token set). Treating every
`<tag` as an opener costs **65 false refusals on the real corpus**, because memory files are full of `<path>` and
`<N>` placeholders. **[M]** (`python3 run_ext.py 25000 31 32 33 34`; `python3 widest.py`). So the contract stops at
comments, declarations, processing instructions and fence lines, and raw tags stay a STATED bound. Today's reader
has the same hole and does not state it.

**Not refuted, and not proven.** The upper bound misses a link built from entities (`&#91;&#91;a]]`) or split by a
backslash (`[\[a]]`). That fails toward UNLISTED (loud) but toward a missed MISSING (quiet). Today's reader is the
same. The corpus was not searched for either form. **[I]**

## 5. What did this PR decide that is not written down?

1. **Which reader "visible" means.** Round 1's fold accepted "a reader following visible links cannot reach `b.md`"
   (Codex r1), which is the reader of a RENDERED page. But the harness loads `MEMORY.md` as text and the assistant
   opens memory files as text, where a comment is as visible as anything else; and `[[name]]`, the store's own link
   form, is a link in no CommonMark renderer (the oracle renders it as plain text **[M]**). The PR chose the rendered
   reader without saying so, and `CONTEXT.md` has no term for a memory link or for reachability of a lesson. **[M]**
   (grep) The bracket is correct for both readers, which is why this review does not ask the owner to choose. It
   should still be written down.
2. **Two bounds that together require a parser.** "A link in a comment does not count" (round 1) and "a link in a
   code span counts" (round 1's bound, kept in round 2) cannot both be applied without knowing which of the two
   contains the other, and that is block structure. Neither was wrong alone. No round document says the pair is
   what made the reader a parser. **[I]**
3. **A guard does not take a third-party dependency.** Round 2 declined PyYAML because the CI job does not install
   it. That is a rule in force (no `requirements*.txt` exists **[M]**) and it is in no ADR title. **[M]**
4. **The reader's precision is owed to no file.** Three rounds changed no corpus verdict (section 1). The corpus
   control in the docstring measures the HISTORY rules against the pre-audit tree; there is no control for the link
   reader, because the corpus cannot supply one. **[M]**

## 6. Recommended work

**In this PR (one fold, then the alternated review half the topology owes):**

- Replace `_COMMENT_RE`, `_keep_code` and `link_targets`' stripping with the two-bound reading; add the rule code.
- Rewrite the 5 changed cases; add: a link BEFORE an opener stays sure; each of rows 2–5's inputs is uncertain; a
  refusal fires only when the bounds disagree on a verdict (an uncertain link to a file that is reachable anyway
  is not a violation); the fence region is line-bounded.
- Rebind or replace the 6 mutations; add one per region and one per bound.
- Docstring: state the rule, the 300,000-document result with the oracle named and dated, and the raw-tag bound
  with its 65. Replace the false bound at line 72.
- Amend backlog #677: item 1 and the span/fence half of item 2 are closed by the redesign.

**Proposed backlog row (text only; `docs/backlog.md` is not edited here)**, to file if the fold is NOT done in
this PR, and to file in its shortened second half (the vocabulary) either way:

> 🟢 **`check-memory-shape.py`'s link reader approximates CommonMark with one regex, and a Phase 6 review measured
> that no regex and no CommonMark parser can answer "does a reader see this link"** — filed 2026-11-20 from
> `docs/reviews/architecture-review-2026-11-20-memory-link-reader.md`. Against `markdown-it` 14.2 + `html.parser`,
> the reader at `0a077e70` counts a hidden link in 31,560 of 300,000 generated documents, in four classes; review
> found one (a fence info string and a `<!…>`/`<?…>` bogus comment were found by no round). The memory corpus holds
> one `<!--` and no comment, so no real file is affected. Redesign: read links at two bounds (links before the
> first `<!`/`<?` and off a fence line; all links), and report a verdict the bounds disagree on under its own rule
> code; prototype measured 0 failures in 300,000 and 0 new corpus violations. Supersedes backlog #677 item 1 and
> the span/fence half of item 2. Also: `CONTEXT.md` has no term for a memory link's reader (rendered page or raw
> text); name it. **Fails if:** `` ```[[t1]] ``, `<?x[[t1]]` or ` - <!--\n--> >[[t1]]- ` as a file's only link to
> `t1.md` still gives rc 0. ⟦kind: defect⟧ | `scripts/check-memory-shape.py`, `CONTEXT.md` | S | (tooling)

**The stop condition for this component after the fold.** A further `link-reader` finding of the form "construct X
hides a link the lower bound calls sure" is a one-token widening and is folded. A finding of the form "construct X
is refused and should pass" is FILED, not folded: making a refusal pass is what rounds 2 and 3 were.

## 7. Measured and inferred

| Claim | Tag | Evidence |
|---|---|---|
| both corpora: one `<!--`, zero `-->`, zero comments | M | `measure.py`; `grep -n '<!--'` |
| today's reader equals a reader that strips nothing, on every file | M | `measure.py`, both folders |
| 31,560 silent and 17,906 loud misreads in 300,000 documents | M | `run3.py 25000 11…22` |
| the info-string and bogus-comment classes were found by no round | M | the four review halves; the class table |
| no CommonMark parser in the stdlib or installed; `markdown-it` only under the main checkout | M | import probes; `ls node_modules` |
| refusing every `<!--` fails one valid corpus file | M | the corpus table |
| the final design: 0 lower-bound and 0 upper-bound failures in 300,000 | M | `run3.py`, final `bracket.py` |
| the redesign adds 0 violations on both corpora | M | `widest.py`; `cms_bracket.py` over both folders |
| 5 of 104 cases change; the prototype runs on Python 3.12.9 | M | `cms_bracket.py --self-test` |
| every `<tag` as an opener costs 65 corpus refusals | M | `widest.py` |
| the live folder is a symlink to the main checkout | M | `ls -ld` |
| refutation 1 (the splice) | I | reasoned from the regexes; not run |
| a verdict both bounds agree on is the true verdict | I | monotonicity of reachability, given the bounds hold |
| no future widening can cause a silent failure | I | follows from the design; four instances observed |
| a parser plus an HTML reader would be needed for exactness | I | from the container-cut and blockquote inputs |
| GitHub's renderer and a browser agree with the oracle | I | not measured; the counts are about `markdown-it` + `html.parser` |
| entity-built and backslash-split links are a quiet MISSING hole | I | not probed against the corpus |
| the pair "comment hides, code counts" is what required a parser | I | reading of the round documents |
