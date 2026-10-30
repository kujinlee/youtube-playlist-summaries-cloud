# Round 1 — review-tooling-121-182 — claude

Subject: branch `review-tooling-121-182` (PR #439), `git diff origin/master...HEAD`, at `76b829ee`.
Mandate: refute. Every probe below was RUN; the probe scripts are in the scratchpad under `r121x/`, outside the repo.

## Gates run

| Check | Result |
|---|---|
| `python3 scripts/codex-review.py --self-test` | 176/176 passed, rc=0 |
| `python3 scripts/check-review-rounds.py --self-test` | 99/99 passed, rc=0 |
| `check-plan-code.py --mutate . --only scripts/codex-review.py` | 49 mutations, 49 killed, 49 attributed to the case they name, 0 survivors, rc=0 |
| `check-plan-code.py --mutate . --only scripts/check-review-rounds.py` | 41 mutations, 41 killed, 41 attributed, 0 survivors, rc=0 |
| `python3 scripts/check-review-rounds.py` (live corpus) | rc=0, 617 rounds parsed, 0 silent gaps |
| Corpus diff, old vs new `has_gap_line` over every solo round | **0** rounds pass now that failed before (every YAML-gap document also carries a prose line, as the #182 re-rating said). So the loosening has no effect on today's corpus. The findings below are about the next document |
| Consumers of `head` / `tree` | `check-review-recorded.classify_verdict` (`:788`) reads `head` and `dirty` only. Nothing reads `tree`. `check-merge-ready.py` and `check-review-rounds.py` do not read `head`. **No consumer is broken** by the new field |

## Findings

### F1 — Major — `scripts/check-review-rounds.py:211-227` (`YAML_HEADER`, `yaml_gap`): any ```yaml block anywhere in a document counts as the header, so a solo half that QUOTES the template passes without recording a gap

The comment at `:207` says "ONLY the first ```yaml block (the header…)". The code takes the first ```yaml fence at **any position**. The header's position, immediately after the title, is never checked. Half documents never carry a header (the template records 0 of 435), so in a half document any ```yaml block is by construction NOT a header. And the template's own example block contains `claude: "GAP: this session spawns no subagents"`, which is exactly what a review of the template, of #182, or of `check-review-decision` will paste into a finding.

Failing input, run through `audit()`:

- `q-r2-codex.md` = `# Round 2 codex` + `## M1 the template example` + the template's ````markdown / ```yaml block, quoted verbatim. No claude file and no prose gap. → `audit(...)[0] == []`, so it **passes**.
- Control: the same document with that one fence relabelled ```text → `["q round 2: only codex — claude neither ran nor recorded …"]`. The pass therefore comes from `yaml_gap` alone.

The case `#182 …and neither is one in a fenced block that is not the yaml header` changes only the fence's language tag. It never puts a ```yaml block somewhere other than the header, so it cannot catch this, and the mutation it guards (`\w*` for `yaml`) is the only variant it covers. A half that never ran now passes because its partner quoted an example. That is the loosening the brief asked about.
**Fix shape:** take the header only if the ```yaml fence is the first non-blank block after the `# ` title, which is the template's stated position. Add a case that has a ```yaml block in a finding's body.

### F2 — Medium — `scripts/check-review-rounds.py:635` with `yaml_gap`: the gap does not have to name the MISSING half, even when the header says the missing half RAN

`audit` accepts any gap for either half. That was already true of the prose line. But the YAML form states each half explicitly, so this PR adds a grammar where the contradiction is written down and ignored.

Failing input: the round has `p-r1-codex.md` (codex ran) and `p-r1-coordinator.md` with `halves:\n  codex: "GAP: timed out once, re-ran"\n  claude: ran`. No claude file exists. → `audit == []`, so it **passes**. The header says claude ran, the disk says it did not, and the round is credited on a gap for the half that is present.

On the corpus I ran, no current document has a YAML gap naming a half that is on disk. So this is latent. Still, it answers the brief's question "can a GAP be read from the wrong half": yes. The cheap rule is to require that the gapped half is among the missing ones. `check-review-recorded.gap_names_codex` (`:1098`) already applies it on the other side, which shows the rule is wanted.

### F3 — Medium — `scripts/codex-review.py:490/522/546` (filing), `:574` (`out_location_refusal`), `:905` (`watched_dirs`): only the HEAD moved to the reviewed tree. The other three subjects still come from `REPO_ROOT`

The new `reviewed_root` docstring states the premise: "`codex exec` is spawned with no `cwd=`, so it reviews the tree the caller stands in." In the #121 shape (the wrapper lives in checkout A and is run from worktree B), the following was run in a fixture with that shape:

- `reviewed_root()` → `…/fx/b` (correct)
- `watched_dirs("/tmp/x/r.md")` → `['/tmp/x', '…/fx/a/docs/reviews']`. The intrusion watch covers A, while the agent runs under `-s danger-full-access` in B. That agent is the one recorded guessing its way into `docs/reviews/` (`:886-897`).
- `out_location_refusal("…/fx/b/docs/reviews/r.md")` → `None`, so it is **not refused**. The same path under A → refused. The #176 r1 M5 hazard is back for exactly the call shape #121 is about. End to end, `--out b/docs/reviews/r.md` run from B got as far as model resolution (rc=1 on the stub's missing cache), not the rc=2 refusal.
- `verdict_path` → `…/fx/a/docs/reviews/verdicts/…`. The PR's own end-to-end case reads the verdict from `_wa` (`_vp3`), which confirms it. A record whose new `tree` field says B is filed in A.

None of this is new. Before the PR the record was at least self-consistent: it described A and was filed in A. Now the record describes B and is filed in A. The PR knowingly settles "the reviewed tree is the cwd" for one subject out of four. Either derive the artifact tree from `reviewed_root` as well, or refuse to run when `reviewed_root() != REPO_ROOT`. Refusing is one line and closes all four subjects together. It would also have turned PR #295's two wasted rounds into one immediate refusal.

### F4 — Minor — `scripts/check-review-rounds.py:233-236`: `has_gap_line` returns ONE gap, and prose beats YAML, so `check-review-recorded`'s codex reader can miss a codex gap

- `has_gap_line("REVIEW GAP: claude — none\n" + header with codex: "GAP: usage limit")` → `"claude: none"`.
- A header with `claude: "GAP: …"` listed before `codex: "GAP: …"` → `"claude: …"`.

`check-review-recorded.first_codex_gap` imports this parser and keeps only codex-named results, so a declared codex gap goes unseen. The failure is in the closed direction: a false CANNOT-RUN or red, never a false pass. Fixing it means returning every gap, and both consumers would need that.

### F5 — Minor — surviving mutant, `scripts/check-review-rounds.py:221-222`

I deleted `if not line.strip(): continue` in a scratch copy and the suite stayed **99/99 passed**. The deletion changes behaviour: a blank line inside `halves:` then ends the mapping, so `halves:\n  codex: ran\n\n  claude: "GAP: x"` stops being read as a gap. The current code reads it as `"claude: x"`, which is correct. No case puts a blank line inside `halves:`. (A second mutant I tried, dropping `realpath` in `reviewed_root`, was killed: 175/176.)

### F6 — Minor — `yaml_gap`: false negatives on ordinary YAML spellings, which bring back the #182 trap for those authors

Each of these returns `None`: `halves:  # per half` (a trailing comment), a flow mapping `halves: {codex: ran, claude: "GAP: x"}`, and a CRLF document with a quoted value. All three fail closed. But each is a red required job for an author who followed "the form is YAML", which is the trap #182 exists to close. The fix is a sentence in the template naming the accepted spellings, or tolerating `#` comments and `\r`.

## Verdict

**NOT CONVERGED** — 1 Major (F1), 2 Medium (F2, F3), 3 Minor (F4–F6). No Blocking. Every suite and both scoped mutation sweeps ran green.
