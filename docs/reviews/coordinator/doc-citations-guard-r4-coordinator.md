# Round 4 — `doc-citations-guard` (backlog #49) — coordinator

⚠ Both halves ran. Filed after the Codex half landed, because a coordinator document for a round
whose halves are incomplete makes `check-review-rounds.py` exit 1 — measured 2026-10-15, with the
message *"round 4: only claude"*.

```yaml
round: 4
fixes_nontrivial: true
subject: doc-citations-guard
halves:
  claude: ran
  codex: ran
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: diff-document-seam, disposition: fixed}
  - {id: H2, severity: High, aim: deliverable, fix_induced: true, component: diff-document-seam, disposition: fixed}
  - {id: H3, severity: High, aim: deliverable, fix_induced: true, component: diff-document-seam, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: rename-pairing, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
  - {id: M3, severity: Medium, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
  - {id: M4, severity: Medium, aim: instrument, fix_induced: true, component: exemption-rows, disposition: fixed}
  - {id: M5, severity: Medium, aim: instrument, fix_induced: false, component: suite, disposition: fixed}
  - {id: M6, severity: Medium, aim: instrument, fix_induced: false, component: suite, disposition: fixed}
  - {id: M7, severity: Medium, aim: instrument, fix_induced: false, component: suite, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: false, component: suite, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: true, component: delivery-figures, disposition: fixed}
  - {id: L3, severity: Low, aim: instrument, fix_induced: false, component: suite, disposition: fixed}
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: diff-document-seam, disposition: fixed}
  - {id: XH1, severity: High, aim: deliverable, fix_induced: true, component: diff-document-seam, disposition: fixed}
  - {id: XH2, severity: High, aim: deliverable, fix_induced: true, component: document-reader, disposition: fixed}
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: true, component: hunkless-refusal, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: true, component: document-reader, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: true, component: hunkless-refusal, disposition: fixed}
```

## ⛔ THE CODEX HALF'S FIVE FINDINGS (`X*`), AND THREE WERE REGRESSIONS THIS ROUND SHIPPED

Every one of those three is a FALSE REFUSAL, which is the direction backlog #56 measured as fatal —
a fail-open costs a missed defect, a false refusal costs the whole gate.

| id | finding | shipped by |
|---|---|---|
| XM1 | a DELETION-ONLY edit to any scoped document returned rc=2: the refusal keyed on "nothing was added" when a deletion hunk HAS a header and adds nothing. The historical replay collected 672 such lines | this round's H2 fix |
| XM3 | `color.ui=always` returned rc=2, because git's ANSI decoration is not in the allow-list | this round's H2 fix |
| XM2 | the symlink refusal sat in the SHARED reader, so citing an ordinary code symlink was rc=2 — git numbers the document there, and following a cited link disagrees with nothing | this round's H3 fix |
| XH2 | the line-rule fix was INCOMPLETE and its witness passed anyway: `read_text()` applies universal newlines, so a lone `\r` became `\n` before `split("\n")` could help | this round's H1 fix |
| XH1 | TWO MORE routes into the seam — a `textconv` driver masking the cited line, and `working-tree-encoding` — taking the class to FIVE | the design, not a fix |

⛔ **AND MY COMMENT CLAIMING TEXTCONV IMMUNITY WAS FALSE, which Codex said in those words.** Worse,
I had already "corrected" that claim once in the wrong direction, by adopting the Claude half's
explanation that textconv always yields a real `@@` line. It does sometimes. The class is defined by
WHAT THE DIFF SHOWS, not by what produced it.

⭐ **The sweep also caught a defence that had stopped being witnessed** — a shape not previously
recorded here. The new no-content refusal SHADOWED the older allow-list refusal: the binary routes
hit the new check first, so the old clause still protected a real shape while no case could tell.
Its mutation went from killed to SURVIVING without anyone touching it, and 77/77 stayed green.
Coverage decayed as a side effect of a fix added nearby.

## Verdict: NOT CONVERGED — 6 High (3 Claude, 2 Codex, 1 coordinator) and 10 Medium

`C1` is the coordinator's own finding, filed because it was reproduced rather than suspected.

## THE ROUND'S ONE RESULT, which is a reframing and not a defect list

**The diff and the document are two oracles, and nothing checked they describe the same object.**
H1, H2, H3 and C1 are that single seam reached four ways. The seam DID NOT EXIST before round 4:
`violations()` used to take its content from the same bytes that carried the numbers. The redesign
closed four header fail-opens by construction — the Claude half attacked that class and could not
reconstruct any of them — and opened this one.

| route | how it reaches the seam | closed by |
|---|---|---|
| H1 | Python's `splitlines()` breaks on 7 characters git does not, shifting every later line number | `split("\n")` |
| H2 | a hunkless diff of a CHANGED file (a NUL byte; `docs/** -diff` in a tracked `.gitattributes`) | the exit refusal in `added_lines` |
| H3 | a symlink: git numbers the link text, the reader dereferenced to the target | `is_symlink()` before `is_file()` |
| C1 | `diff.external` / `GIT_EXTERNAL_DIFF` replaces git's output wholesale | ⛔ ALSO the H2 exit refusal — see below |

⛔ **AND I CREDITED THE WRONG FIX FOR C1, WHICH THE REVIEW HALF CAUGHT AND I THEN MEASURED.** The
commit and the code comment said `--no-ext-diff` closed that fail-open. Three worlds over one
fixture:

    world                      shipped        no --no-ext-diff     no flag AND no H2 exit fix
    no driver                  rc=1 fires     rc=1 fires           rc=1 fires
    diff.external configured   rc=1 fires     rc=2 CANNOT RUN      rc=0 ⛔ FAIL-OPEN

**The exit refusal closes the fail-open for all four routes.** The right characterisation is the
reviewer's — *anything that removes the hunk headers* — and two of the four routes are committable
by an author, which no invocation flag could ever have covered. `--no-ext-diff` keeps its place for
a smaller, different job: it turns a FALSE CANNOT RUN into a correct finding for a developer who has
a diff driver configured, and backlog #56's measured verdict is that a gate red from birth gets
switched off. ⟳ My textconv explanation was wrong the same way: textconv emits a real unified diff,
so there IS an `@@` line and it was never in this class — the discriminator is the hunk headers, not
the provenance of the content.

## H1 is the finding of the round, because it breaks a contract and not just a case

Both directions reproduced with adjacent controls: a form feed let a drifted citation pass (control,
one character different, fires), and a U+2028 made an innocent append inherit a year-old citation.
That second direction breaks **added-lines-only**, which is what the 96.7% exclusion and the 12.4%
living rate are justified by. Four tracked documents already disagreed with git's line count, and
the producer of U+2028/U+2029 here is this project's own review halves — so the exclusion of
`docs/reviews/` was the only thing keeping it latent.

## Thrashing: it continues, and the seam is FILED rather than patched a fifth time

Per finding, *did the previous round's fix cause this?* — **8 of 14 yes** (H1, H2, H3, M1, M2, M3,
M4, L2), and all four of the High-severity ones. That is a third consecutive fix-induced round in
one component, so the arming condition holds for the third time.

**The test — can a redesign remove it?** The Claude half answered it by PROTOTYPING, not arguing:
compare citation STRINGS between the pre-image and post-image documents, so no line numbers cross
the boundary and no diff text is parsed at all. Measured against every fixture in the round: it
catches H1 in both directions, H2 by both routes and H3, keeps every correct verdict, and leaves the
real repository green. **So the answer is YES — and it is NOT taken in this round**, because it
changes what the gate ASSERTS (*on an added line* becomes *new to this document*) and the
0.25/commit figure does not transfer. Filed as backlog **#291** with the measurement as its
argument, on exactly the ground r1 L2's fence exemption was deferred.

⚠ **So this round's honest verdict is: the instances are fixed and the SEAM is not.** The Claude
half predicted *"a fourth route is likely, because the seam remains"*; the Codex half then found the
fourth AND the fifth, and three of this round's own fixes shipped false refusals.
⭐ **THE OWNER WAS ASKED AGAIN ON 2026-10-16 WITH THAT EVIDENCE AND CHOSE THE REBUILD** — #291,
built the same day in `353dcef1`. The seam is gone: citations are compared as STRINGS between two
blobs git itself supplies, no line number crosses any boundary, and the firing rate came out
NARROWER (0.23/commit against 0.25) rather than wider as the review had warned. Round 5 reviews
that rebuild.

## Ambient cases: six through ten, and I wrote the tenth while fixing the ninth

M5 (eighth — a one-letter stem makes the separator rule an equivalent mutation) and M6 (ninth — the
case named the empty-tree refusal and its fixture reached the git-failure raise) came from the
review. The tenth is mine: a case asserting `added_lines` arithmetic over a literal string, written
to answer M3, which cannot see a flag the pure function never receives — it survived at 72/72.

**All ten have one shape: the fixture exercises the PURE function while the clause under test lives
in the impure caller.** Every witness added this round therefore returns a TUPLE whose second
element is an adjacent control, because a single assertion is exactly what each of the ten was.

## What the round also established, stated because a round that only lists fixes overstates itself

* **The structural `@@` claim is TRUE.** Both halves hunted a column-0 `@@` that is not a hunk
  header, and a hunk header off column 0, across funcname suffixes (one containing a form feed),
  `\ No newline`, `----`, `+@@` content, binary entries, mode-change-only, symlinks, empty diffs and
  CRLF. Neither found one. ⟳ And the one gap the Claude half deferred is now MEASURED rather than
  reasoned: a genuinely conflicted merge still yields a two-tree diff with `@@`, never `@@@`,
  because `git diff <ref>` is always two-tree. The guard fires correctly.
* **Every figure reproduced**, re-derived by importing the module, including 10 firings over 40
  commits at 0.25/commit across the same four commits.
* **`EXAMINED_KEYS` is exact** — 23 pinned, 23 examined, empty difference both ways.
* **The manifest was verified by a second party applying every edit**: all anchors bind once, no
  duplicate names or anchors, every `expect` names a real case, all killed and attributed.
