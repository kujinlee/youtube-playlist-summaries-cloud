# Round 3 — `merge-ready-thrash-hold` — Claude half

Reviewed 7f2286d4 (PR #615, backlog #680 part 2). All probes were run in a full clone
(`.../scratchpad/680b-r3/claude-work/repo`). There, `refs/remotes/origin/master` was set to 7f2286d4, so the
gate's own code is the base and each probe branch adds only coordinator docs. `main()` ran for real against
that repository: every `git` call was real, and only `gh` and the three gate `python3` calls were faked to
pass (harness: `claude-work/mainprobe.py`, variants: `claude-work/variants.py`). The control (two fix-induced
flow items in `det4`, indented) gives **rc=3, `HOLD thrashing armed`**. Every row below is measured against
that control.

## Summary of probes (through `main()`, real git, HEAD = probe branch)

| Variant (both r1 and r2 of subject `zz`, item fix-induced in `det4`) | Valid YAML meaning | rc |
|---|---|---|
| control: `findings:` + `  - {…fix_induced: true…}` | fix-induced | **3** HOLD armed |
| J: `findings:` + `- {…}` (sequence NOT indented, PyYAML's default dump style) | fix-induced | **0 READY** |
| J2: `findings:` + `- id: X` / `  fix_induced: true` / `  component: det4` | fix-induced | **0 READY** |
| P: `findings: []` then `findings :` + items (second key, space before colon) | dup key, last wins → fix-induced | **0 READY** |
| Q: `findings: []` then `"findings":` + items (second key, quoted) | same | **0 READY** |
| R: bare `findings:` then `"findings": [{…}]` | same | **0 READY** |
| A: `findings: []` then indented `  - {…}` under it | invalid YAML | **0 READY** |
| B: `"fix_induced": true` (quoted key) | fix-induced | 0 READY |
| C: `fix-induced: true` (hyphen) | not the field (misspelling) | 0 READY |
| D: r2 `component: det4  # the detector` | component `det4` | 0 READY |
| H: `base: &b {…}` / `findings:` / `  - {<<: *b}` (merge key) | fix-induced | 0 READY |
| G: flow item split over two lines | fix-induced | 3 (cannot judge) |
| K: `findings: [` … `]` multi-line | fix-induced | 3 (cannot judge) |
| N: `findings :` as the only key | fix-induced | 3 (cannot judge) |
| O: `findings:` + `  [ {…} ]` | fix-induced | 3 (cannot judge) |
| L: tab-indented item | (invalid YAML) | 3 armed |
| M: `fix_induced: yes` | true (YAML 1.1) | 3 armed |

The same J, J2, P, A and D inputs, run with `origin/master` set to **3cc76714** and then to **d444dcad**
(each commit's own `main()`), also give rc=0. So none of them came from the round-2 fold.

---

## C1 — MAJOR — A clean round is inferred from ZERO PARSED ITEMS, so valid YAML with fix-induced findings reads as clean (J, J2, R, A)

**fix_induced: false.** J, J2 and A give rc=0 at d444dcad, at 3cc76714 and at 7f2286d4 alike. The cause is
`_findings_span` and `_block_items` in `check-review-decision.py`: both stop at the first line that is not
indented, and that is unchanged on master.

**What happens.** Under a bare `findings:` key, an UNINDENTED block sequence (`- {…}` or `- id: …`) is valid
YAML. It is also what `yaml.dump(..., default_flow_style=None)` emits. `_findings_span` breaks on the first
line that starts without a space, so `declared` is 0. `_block_items` breaks there too, so it reads 0 items.
`parse_round` therefore returns `findings: []`, `findings_key: True`, `findings_inline: ''`,
`findings_keys: 1`, and every check in `thrash_gate` passes. A also reads as clean: `findings: []` followed
by indented items, where `EMPTY_INLINE` accepts the `[]` and nothing reads the lines under it. Master's
`parse_header` makes the same mistake for J and J2: it returns `{'findings': []}` for the J2 document, so
`check-review-decision`'s own convergence path also reads such a round as clean.

**This is the backlog row's FAILS IF, met through `main()` against a real repository.** It is the third
spelling of one class: r1 X1 was an inline value, r2 X1 a second key, and C1 here an unindented sequence or
an `[]` with lines under it. That is why I recommend the structural fix over a fourth spelling-specific
patch. **Make "clean" a positive form, not an absence:** a round is clean only when the header literally
reads `findings: []` (optionally followed by a comment) AND nothing follows it before the next column-0 key.
A bare `findings:` that parses to zero items, or any `- ` line between the key and the next top-level key
(at any indentation) that did not become a parsed item, is unreadable. Corpus cost, measured over the 783
coordinator docs at HEAD:
- a bare `findings:` with zero parsed items: **0** docs;
- `findings: []` with lines under it: **0** docs;
- an unindented `- ` under `findings:`: **0** docs.

So the stricter rule adds no false HOLD today.

**Reproducer (ran).** In the clone, with `git update-ref refs/remotes/origin/master 7f2286d4`, run
`python3 ../variants.py $PWD J_unindented_flow J2_unindented_block A_empty_then_items`. Each prints `['RC 0'] []`.

**Why MAJOR and not BLOCKER.** The gate is new, so this is no worse than master. The input appears in none of
the 783 coordinator docs, which are all written in the indented style. The fold is round 3, before the cap,
so a MAJOR still gets folded. If the coordinator reads the FAILS IF as the gate's whole contract, this is the
finding to promote.

## C2 — MAJOR — The r2 X1 key count reads only one spelling of the key; `findings :`, `"findings":` and `'findings':` are the same YAML key (P, Q)

**fix_induced: false**, because the defect is incomplete, not newly introduced. P gives rc=0 at 3cc76714 and
at d444dcad as well. The fold did not create the hole; it counted `^findings:` and missed the other
spellings. This is brief item 1, refuted on its own named example (`findings :`).

`findings_keys` is `len(re.findall(r"^findings:", body, re.M))`. Take a header that has `findings: []` and
then `findings :` (or `"findings":`) over fix-induced items. YAML loaders that accept duplicate keys keep the
last one, which is the fix-induced list. The count is 1, the inline value is `[]`, and the items are never
read. Result: rc=0.

**Fix:** count every top-level key matching `^["']?findings["']?[ \t]*:`. Better still, count any column-0
key that normalises to `findings`, and treat any count other than 1 as unreadable. The same normalisation
should apply to `findings_dup_fields` names: `p.split(":")[0].strip().strip('"\'')`.

**Reproducer (ran).** `python3 ../variants.py $PWD P_second_key_spaced Q_second_key_quoted` prints `RC 0` for both.

## C3 — MINOR — Without validation, a field-name variant is silently not the field (B, C, H)

**fix_induced: false.** The trade-off was made at the build: the 2026-11-21 decision not to use
`rounds_for`'s validation.

`"fix_induced": true` (a quoted key) parses as the key `'"fix_induced"'`, so `f.get("fix_induced")` is None
and the round is not fix-induced. `parse_header` REFUSES this ("has no `fix_induced`"), but the thrash gate
reads it as clean. The same happens with a misspelled `fix-induced:` and with a YAML merge key `<<: *b`.

The corpus has 28 findings in 15 docs with no `fix_induced` at all, so refusing a missing field outright
would false-HOLD. A narrower rule costs 0 in the corpus: treat an item as unreadable when it carries a key
that normalises (quotes stripped, `-` → `_`, lowercased) to `fix_induced` or `component` but is not spelled
exactly that, or a key starting `<<`.

**Reproducer (ran).** `variants.py … B_quoted_key C_hyphen_key H_merge_key` prints `RC 0` for all three.

## C4 — MINOR — A trailing `# comment` is part of the value (D)

**fix_induced: false.** `_scalarise` is master's.

`component: det4  # the detector` reads as the string `"det4  # the detector"`, so two rounds that YAML reads
as the same component do not intersect, and the result is rc=0. Two related effects run in the false-HOLD
direction:
- `fix_induced: false  # …` is a non-empty string, so it reads as true.
- `fix_induced: no` (YAML 1.1 false) also reads as true.

The corpus has 0 comments in `component` values and 3 `yes` values (in `meter-log-tail` r2 and r3), which
the parser happens to read correctly. **Fix:** strip a ` #…` suffix in `_scalarise`. That touches
`parse_header`'s output, so measure it over the corpus first. Or refuse a value containing ` #` in
`thrash_gate` alone.

**Reproducer (ran).** `variants.py … D_comment_component` prints `RC 0`.

## C5 — MINOR — A rename, copy, whitespace touch or empty file under the review path clears the HOLD

**fix_induced: false.** At d444dcad a renamed or touched review's new path was already in `files`. r2 X2 added
only the check that the path exists at HEAD.

Brief item 2 asked for exactly this case: a rename that still clears. X2's principle was that deleting an old
review is not running one. The cases that still clear are a rename of an old review
(`git mv docs/reviews/architecture-review-2026-07-30.md docs/reviews/architecture-review-2026-11-21-zz.md`),
a copy of one into `coordinator/`, a one-character edit to an old review, and an EMPTY new
`architecture-review-*.md`. All four give **rc=0** beside two fix-induced rounds. A case-only rename to
`Architecture-review-…` does not match `ARCH_REVIEW` and still HOLDs (rc=3), so case is not a bypass.

The docstring says "added or changed", so the one-character edit is the stated rule. The rename, the copy and
the empty file are not stated. **Fix, or state it as a bound:** count only `A` entries whose blob is
non-empty, and not `R` or `C` entries. `parse_name_status` already carries the status. The cheaper
alternative is to add the bound to `thrash_holds`' docstring and to backlog row 680.

**Reproducer (ran).** `bash claude-work/archprobe.sh <clone>` prints `rename RC 0`,
`rename-case-to-nonmatching RC 3`, `modify-old-review RC 0`, `empty-new-review RC 0` and `copy-old-review RC 0`.

## C6 — MINOR — False HOLD on an ordinary PR: editing any old coordinator doc of an already-reviewed subject HOLDs (item 7)

**fix_induced: false.** This is the build's design: "a review at HEAD outside the range clears nothing".

At HEAD, **42 of 182** subjects would HOLD if any one of their coordinator docs were touched: 27 armed and
15 cannot-judge, measured with `thrash_gate` over each subject's last-two paths. They include `hse-slice-c`,
whose Phase 6 review `docs/reviews/coordinator/architecture-review-2026-11-17-hse-slice-c.md` already exists.
The HOLD's remedy ("run the Phase 6 architecture review") is then wrong. A backfill or scrub PR that edits
old round headers (e40d32ad did this for `chrome-bar-reachable`) HOLDs on every subject it touches.

Measured frequency is low: 1 of 174 first-parent master commits since 09-01 touched a coordinator doc of a
subject to which it added no round. **Suggested:** judge only subjects whose range ADDS or modifies their
newest round, or say in the HOLD text that an existing review for the subject can be cited.

**Reproducer (ran):** the 42-subject enumeration script, inline in this review's session. The single-commit
history count was taken with `git log --first-parent origin/master --since=2026-09-01 --name-status`.

---

## Brief items not refuted

- **Item 3 (is anything fix-induced?):** **No.** No finding above was introduced by 7f2286d4. Each one
  reproduces at 3cc76714, and C1, C2 and C4 at d444dcad too. **This PR does NOT arm THRASHING from this
  round:** r2's findings are `fix_induced: false`, and so are all of r3's. The fold's new checks
  (`findings_keys`, `findings_dup_fields`, `head_paths`) produced no false HOLD. Over all 2,999 review docs,
  `findings_keys != 1` occurs in exactly 2: `hse-slice-d-r4` (0 keys, already unreadable) and the Codex r2
  review (not a coordinator doc). `findings_dup_fields` is non-empty in 0.
- **Duplicate-field fold (item 1, the other half):** not bypassed. A comma inside a quoted value that spells a
  second `fix_induced:` is flagged as a duplicate, so it is unreadable, never clean. A nested mapping that
  repeats a key is flagged the same way. An anchored item `- &a {…}` is a count mismatch, so it is cannot-judge.
- **Item 5:** `parse_header` at 7f2286d4 against master 5f32aac8, over all 2,999 `docs/reviews/**/*.md`:
  **0 differences** (559 parse). `check-review-decision.py --self-test` gives **123/123** and
  `check-merge-ready.py --self-test` gives **448/448**, both run in the full clone.
- **Item 4:** refuted — see C1 and C2, both through `main()` against a real repository.
- **Item 6 (mutations): not refuted.** I applied each of the 6 new r2 mutations from their manifests in the
  full clone, ran the owning script's `--self-test`, and restored the file after each one (the clone was clean
  afterwards). **All 6 of 6 failed under their named `expect` case.** The results, as cases passed out of the
  total:

  | Mutation | Self-test result |
  |---|---|
  | `findings_keys` check | 446/448 |
  | dup-fields check | 447/448 |
  | `head_paths` dropped | 443/448 |
  | `frozenset(files)` | 445/448 |
  | crd key count | 122/123 |
  | crd dup `> 2` | 122/123 |

  The harness script is `claude-work/mut.py`.

VERDICT: NOT CONVERGED
