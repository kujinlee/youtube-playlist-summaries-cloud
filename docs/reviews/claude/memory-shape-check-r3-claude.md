Reviewed head: 6ee2860fbd48e29398ac5446d3afc9027ad45606

# memory-shape-check — round 3, Claude half

Subject: `scripts/check-memory-shape.py`, `scripts/mutations/check-memory-shape.json`, its CI step
(`.github/workflows/ci.yml:614-617`). Reviewed at HEAD `6ee2860f` (the round 2 fold is `f6fb3624`).
Every adversarial input was built in a scratch directory outside the repository; the module was loaded
by path and its pure functions called directly, or `main([], <dir>)` was run over a constructed folder.

`python3 scripts/check-memory-shape.py --self-test` → last line: `self-test: 104/104 cases passed`.

## Corpus runs (read-only)

- `docs/memory/` (worktree): `memory shape ok — 195 files in docs/memory, every rule passed`, rc 0.
- Live folder `~/.claude/projects/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/memory/`
  (read from a copy): rc 1, ONE violation, over 197 files:
  `FRONTMATTER a-forced-choice-test-cannot-fail.md: not well-formed YAML: description is an unquoted value holding ': '`.
  This is a TRUE positive and not fix-induced: the live copy still says
  `description: FIRES-WHEN: scoring …` unquoted (invalid YAML), while the repo copy was quoted by the
  round 1 fold. The live folder also holds 2 files `docs/memory/` lacks (`daily-wake-routine.md`,
  `orchestrator-watches-agents-actively.md`); both pass. No valid file in either corpus is rejected.

## Findings

- **MINOR — scripts/check-memory-shape.py:139:** the inline code-span alternative of `_COMMENT_RE` is
  not block-aware, so a "span" can swallow a real HTML comment and the links inside it count again
  (an UNLISTED false pass — the exact hole the r1 Codex MAJOR closed). Three inputs, each a link a
  reader cannot see, each returned by `link_targets`:
  (a) across list items — `"- a ` b\n- <!-- [x](x.md) -->\n- c ` d"` → `['x.md']` (CommonMark: spans
  never cross block boundaries, so the comment is real → `[]`); also a heading:
  `"# h `\n<!-- [x](x.md) -->\ntext `"` → `['x.md']`;
  (b) a backslash-escaped backtick — `"\\`<!--\\` [a](a.md) -->"` → `['a.md']` (an escaped backtick
  opens no span, so the comment is real → `[]`);
  (c) a 4-space-indented fence line — `"    ```\n<!--\n    ```\n[a](a.md)"` → `['a.md']`, which
  CONTRADICTS the docstring's own bound at line 72 ("a `<!--` in [an indented code block] still opens
  a comment"): the indented backticks are read as an inline span over the `<!--`.
  Impact today is nil (the index holds no `<!--`; one memory file holds one), so MINOR.
  **Fix-induced: yes** (r2 added span recognition; the r1 rule dropped all three comments).

- **MINOR — scripts/mutations/check-memory-shape.json (no entry) / scripts/check-memory-shape.py:139-142,156,489:**
  behaviours the r2 fold STATES have no case, and hand mutants of each survive at 104/104 (applied to a
  scratch copy, `--self-test` run): span closer not same-length (`(?<!`)(?P=ticks)(?!`)` → `` `+ ``;
  changes `"``<!--` [a](a.md) -->"` from `[]` to `['a.md']`), fence closer not same-length/char
  (`(?P=fence)[`~]*` → `` (?:`{3,}|~{3,}) ``), fence indent unbounded (`[ ]{0,3}` → `[ ]*`), an
  unclosed fence no longer running to the end (`|\Z` dropped), tilde fences not recognised
  (`` `{3,}|~{3,} `` → `` `{3,} ``), and the escapes `\L` and a literal TAB removed from `_ESCAPE`
  (the "every escape YAML defines" case at line 489 omits `\a \b \v \f \r \_ \L \P` and TAB, so
  dropping any of them survives). Only removing the fence alternative entirely is killed (103/104).
  **Fix-induced: yes** (all introduced by the r2 fold).

- **MINOR — scripts/check-memory-shape.py:223:** a full-line YAML comment in frontmatter is rejected
  while a trailing one is accepted (the r2 fold's own premise: "a trailing comment is valid").
  Input `# a note` on its own frontmatter line → `FRONTMATTER … line '# a note' is not key: value`
  (valid YAML rejected); `# note: x` → accepted, and stored as a field named `# note`. Corpus has 0
  such lines. **Fix-induced: no** (r1 line rule; r2 extended comment support to tails only).

- **MINOR — scripts/check-memory-shape.py:153,221:** YAML errors still accepted: a value led by a
  block-sequence indicator, `tags: - x` (YAML: "sequence entries are not allowed here") → no
  violation (`-` followed by a space is not in `_YAML_INDICATORS`); a TAB-indented `\ttype: user`
  under `metadata:` (YAML forbids tab indentation) → accepted and read as `metadata.type`; a stray
  indented `  junk: y` under a non-mapping key → accepted in silence. Corpus has 0 of each.
  **Fix-induced: no.**

- **MINOR — scripts/check-memory-shape.py:230:** escapes are VALIDATED but never DECODED, so a value
  r2 now declares valid reads wrong: `name: "foo\x2Dbar"` in `foo-bar.md` (YAML value `foo-bar`) →
  `NAME foo-bar.md: name: foo\x2Dbar does not match the filename slug`. A valid file rejected — loudly,
  never a false pass. Corpus has 0. **Fix-induced: no** (r1 read the same text the same way).

## Round 2 folds — do they hold?

- XM1 (undefined escapes): holds. `"bad\q"`, `"\x4"`, `"\u12"`, `"\x4g"` → refused with the escape
  reason; `"a\\"`, `"a\"b"`, `"\U0001F600"`, `"\ "`, `"\/"`, `"\e"`, `"\L\P\N\_"`, `"<TAB-escape>"` →
  accepted; `"a\\\"` → unterminated. No false accept found.
- Xm1 (trailing comments): holds. `"ok" #c`, `"ok"\t#c`, `'a' # c`, `"a"  # c # d`, `"a" # "b`,
  `plain # c: x`, `x #c:` → accepted; `"ok"#c`, `"ok" x`, `'a'b`, `'it's'`, `"a" "b"`,
  `plain#c: x`, `a: b # c`, `plain: # c` → refused. Matches YAML in every case tried.
- XM2/Xm2 (delimiters inside code): holds for same-block code — `` `<!--` … `-->` ``, fenced and tilde
  blocks, a 4-tick fence not closed by 3, an unclosed fence, a `-->` inside a span inside a comment, a
  span that cannot cross a blank line, an unmatched tick run. Breaks only across blocks / on escapes /
  on indented fences (finding 1).

## Fails loudly?

Yes, every case measured by its real exit code: an unreadable memory file, unreadable index, broken
`*.md` symlink, a directory named `z.md`, `MEMORY.md` as a directory, the memory dir as a plain file,
an unreadable directory, a folder with only `*.MD` files, and `--bogus` → rc 2, each printing
`Treat this as NOT RUN`. An empty `MEMORY.md` → rc 1 (UNLISTED), loud. Nothing reaches rc 0 without
reading at least one file.

## Loosening answers

- Does the fold loosen a gate? It widens what counts as a VISIBLE link (code-span content), which by
  construction can only add reachability, so UNLISTED can only fire less — finding 1 is the place
  where that loosening exceeds what a reader sees. It also accepts more YAML (escapes, trailing
  comments), each verified to match YAML. No rule was removed; rc 2 is untouched.
- Is any loosening unwitnessed by a mutation? Yes — finding 2's survivors.
- None of the findings is a BLOCKER or MAJOR: no valid corpus file is rejected, no fail-open path
  exists, and the one false-pass shape needs an HTML comment the index does not contain. Under the
  round cap these are filed, not folded, unless the coordinator chooses otherwise.

VERDICT: CONVERGED
