<!-- codex-review: model=gpt-5.5 -->

**Severity** — Blocking  
**Where** — §8 lines 245-260; `scripts/check-dashboard-entry.py:145-150`, `scripts/check-dashboard-entry.py:241-254`  
**What is wrong** — The one-validator-two-callers design is not buildable against the current gate contract. `collect()` returns only `(changed, added, err)`, where `added` is `any(_added_entry_line(...))`; `verdict()` accepts a boolean and passes immediately on `added_entry`. The new `decision_errors(plain, category)` has no `plain` body or category available at the gate call site.  
**Why it matters** — A branch can add `+## 2026-08-31 [needs-you]` with no decision block, `collect()` reduces that to `added=True`, and `verdict()` returns success before any decision grammar can run. The claimed shared validator can silently check nothing in the highest-risk caller.  
**Suggested fix** — Change the spec to require `collect()` to extract added dashboard entry blocks, not a boolean, and define how diff hunks are reassembled before calling `decision_errors`.

**Severity** — Blocking  
**Where** — §11 lines 317-326; §8 lines 256-260; `scripts/gen-dashboard.py:356-383`, `scripts/gen-dashboard.py:417-451`; `docs/dashboard-entries.md:13`, `docs/dashboard-entries.md:821`, `docs/dashboard-entries.md:870`, `docs/dashboard-entries.md:44`, `docs/dashboard-entries.md:923`  
**What is wrong** — The spec says old entries are not rewritten and grammar work changes nothing on today’s page, but also says `parse_entries` sets `entry["error"]` for malformed `[needs-you]` entries. Resolution is derived only after pass 2 in `unresolved()`, so `parse_entries` cannot know that the three old `[needs-you]` entries without `**Decide:**` are already cleared.  
**Why it matters** — A literal implementation marks all three live historical asks malformed, because the store contains `[needs-you]` entries at lines 13, 821, and 870 with no decision block, cleared later at lines 44 and 923. That breaks the append-only promise while claiming no visible page change.  
**Suggested fix** — Validate decision blocks only for unresolved `needs-you` entries after resolution is computed, or explicitly grandfather entries before an effective date.

**Severity** — High  
**Where** — §4 lines 141-150  
**What is wrong** — The decision grammar is underspecified for Markdown contexts that the repo already treats as semantically inert elsewhere. It does not say whether `**Decide:**` inside a fenced code block, indented code block, blockquote, HTML comment, or nested list in the plain section counts.  
**Why it matters** — Two implementers can both satisfy the text and diverge: one scans lines and treats a quoted/code example as a real decision; another follows Markdown semantics and ignores it. The gate and renderer can then disagree, or worse, both accept a fake ask copied inside example text.  
**Suggested fix** — Define the parser’s block-state rules explicitly, reusing the existing fence/comment/indent discipline from `exemption_reason()` where applicable.

**Severity** — High  
**Where** — §4 lines 143-147  
**What is wrong** — The option grammar does not define minimum option text or malformed empty questions. A line `**Decide:**` with no question and options `- [recommended]` and `- ` can satisfy the written “≥2 options” and “at most one recommendation” rules unless implementers invent extra constraints.  
**Why it matters** — The gate can pass entries that structurally contain a decision block but still do not tell the reader what they can do, recreating defect §1b under a compliant shape.  
**Suggested fix** — Require non-empty opener text after `**Decide:**` and non-empty option text after removing list marker and `[recommended]`.

**Severity** — High  
**Where** — §4 lines 143-145  
**What is wrong** — List shape is ambiguous. The spec says “markdown list items (`- `)” but does not explicitly reject `* ` or `+ `, nested options, continuation lines, or an indented list under the opener. It also does not say whether two `**Decide:**` blocks may be adjacent with no blank line between the previous option list and the next opener.  
**Why it matters** — The renderer may display a different number of decisions/options than the gate validated, especially if one implementation uses a Markdown parser and the other uses line regexes.  
**Suggested fix** — State that only column-relative `- ` option lines immediately following the opener count, define continuation/nesting behavior, and require or forbid a blank separator between decision blocks.

**Severity** — Medium  
**Where** — §4 line 147 versus §6 lines 213-220; §9 line 284  
**What is wrong** — The PR reference rule contradicts itself. §4 says only the literal token `PR #N` names a pull request; §6 says “When an option names `#N`”; §9 tests that backlog `#74` is not a PR.  
**Why it matters** — An implementer following §6 will recreate the bare-`#N` collision §4 explicitly rejects, and options like `close backlog #74` may resolve/link PR 74.  
**Suggested fix** — Replace every §6/§9 bare `#N` phrasing with `PR #N` and add a negative test for bare `#N`.

**Severity** — Medium  
**Where** — §3 lines 95-99; `scripts/check-vocabulary-collisions.py:2-3`, `scripts/check-vocabulary-collisions.py:55-60`; `docs/dev-process.md:143`  
**What is wrong** — The no-expiry decision is justified by invoking `check-vocabulary-collisions.py`, but that script enforces duplicate coordination vocabulary across schema tables, not dashboard lifecycle policy. Its own scope is database mechanism stems, not UI expiry semantics.  
**Why it matters** — The spec uses an unrelated ratchet as authority for a product decision. That can block a valid bounded-retention design without actually proving duplicate lifecycle mechanisms would conflict here.  
**Suggested fix** — Keep “no expiry” only if justified directly by dashboard behavior, or mark expiry as a deferred product decision rather than a collision-gate consequence.

**Severity** — Medium  
**Where** — §7 lines 230-241; §6 lines 225-226; `scripts/gen-dashboard.py:490-503`, `scripts/gen-dashboard.py:506-513`  
**What is wrong** — The PR-state resolver’s cannot-run contract covers `gh pr view` failure, but not unexpected JSON shape or missing fields for the new command. Existing `_gh_json()` only parses JSON; `open_prs()` separately validates shape. The spec does not require equivalent shape validation for `pr view`.  
**Why it matters** — A malformed or partial `gh pr view` response can be treated as a checked state, or crash, depending on implementation. Both violate “could not tell” versus “nothing/stale/open.”  
**Suggested fix** — Specify the exact `gh pr view --json ...` fields and require unexpected shape to render “could not check.”

**Severity** — Medium  
**Where** — §9 lines 273-289  
**What is wrong** — Several falsifiers are vacuous unless the harness is required to prove the guard, not merely observe an outcome. “Gate and renderer agree” can pass if both accept a malformed entry; “Decision required” only names the gate, not the renderer; “Options are unfolded” can be credited by string absence inside `<details>` even if options are not rendered anywhere.  
**Why it matters** — A test suite can report the falsifier table green while the properties are false or while the intended guard never ran. That is exactly the silent-success failure mode the spec claims to prevent.  
**Suggested fix** — For each falsifier, require paired positive/negative fixtures and assert the responsible output, not only absence of a bad string.

**Severity** — Low  
**Where** — §1b lines 48-50; parent spec `docs/superpowers/specs/2026-08-28-project-dashboard-design.md:116`; `scripts/gen-dashboard.py:402-412`  
**What is wrong** — The new spec relies on “title is the entry’s first sentence,” which matches current renderer behavior, but the parent grammar still says title is “the first non-blank line after the header.” The spec says it extends and does not supersede the parent.  
**Why it matters** — Implementers reading parent §6.2 can build title extraction differently from the renderer and from this spec’s premise, especially for wrapped first paragraphs.  
**Suggested fix** — Amend the parent grammar or explicitly state this spec updates the title rule.

NOT CONVERGED
