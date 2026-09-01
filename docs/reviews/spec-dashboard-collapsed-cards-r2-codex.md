<!-- codex-review: model=gpt-5.5 -->

**Blocking**

None found.

**High**

1. **NEW-IN-V2: §2f can suppress the only path to raw technical detail**

Evidence: §2d requires technical detail to remain nested at the end of the body, `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:180-181`. But §2f says to emit a non-interactive row when the fold body is empty or its tag-stripped text equals the row title, `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:205-207`. The generator currently emits tech separately as `<details id="{eid}-tech">...`, `scripts/gen-dashboard.py:989-991`, and then appends it after the plain fold, `scripts/gen-dashboard.py:1000-1002`.

Executed probe:

```text
entry:
## 2026-08-31
Same title.
<!--tech-->
raw unique detail

title: 'Same title.'
prose: <p class="lede">Same title.</p>
tech? True
tag-stripped prose == title: True
```

Concrete failure scenario: an entry with one plain sentence plus a `<!--tech-->` block has a prose body whose stripped text equals the title. If §2f suppresses the card fold on that comparison alone, the raw technical detail either disappears or must be rendered outside the requested nested fold. That contradicts §2d and F4.

Smallest fix: define the §2f comparison over the complete hidden payload, not prose alone, or state explicitly: “Suppress the fold only when there is no tech block and the rendered prose is empty or text-equal to the title.” Add an F8 variant: single-sentence plain plus unique tech must still emit `{eid}-card` and nested `{eid}-tech`.

**Medium**

None found.

**Low**

1. **NEW-IN-V2: §6 says five `orphaned_delimiters` cases, but there are four**

Evidence: §3a correctly says `page_markup.orphaned_delimiters` has four self-test cases, `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:239-241`. §6 later says `page_markup.py` loses five cases, `docs/superpowers/specs/2026-08-31-dashboard-collapsed-cards-design.md:356-357`. The actual cases are four: `scripts/page_markup.py:436-440`.

Concrete failure scenario: an implementer follows §6 and goes looking for a fifth deletion in `page_markup.py`, risking removal of an unrelated case or leaving the spec’s blast-radius accounting stale.

Smallest fix: change §6 to “its 4 cases.”

**Checked And Correct**

§3a coupling 1 is correct. Current `_prose` still calls `_first_sentence(first, cap=len(first))`, `scripts/gen-dashboard.py:250-252`, so deleting the `cap` parameter requires changing that call. With `cap` removed, the truncation-free `_first_sentence` body should normalize text, return `""` for empty input, accumulate `SENTENCE_END` parts until `TITLE_FLOOR` and non-abbreviation pass, then return `out`; no `cap` references remain from `scripts/gen-dashboard.py:123-159`.

§3a coupling 2 held under targeted probes. For an unterminated long paragraph, abbreviation case, short `TITLE_FLOOR` case, and markup-only paragraph, the title span and dropped `head` were the same raw span because both derive from `_first_sentence`; current no-terminator refusal is at `scripts/gen-dashboard.py:260-261`.

§4’s article fragment boundary is well-defined: entries are emitted as one `<article ...>...</article>` with nested `<details>` but no nested `<article>`, `scripts/gen-dashboard.py:995-1002`. F10 is also scoped correctly if it counts only the What changed section: broken entries emit no `<h3>`, `scripts/gen-dashboard.py:983-988`; ask tray and Worth knowing emit `<h2>`, not `<h3>`, at `scripts/gen-dashboard.py:1138-1141`.

§2b’s anchor claim is correct for current code. Tray links are `href="#{_slug(e["id"])}"`, `scripts/gen-dashboard.py:877-880`; unresolved needs-you entries exclude parse errors, `scripts/gen-dashboard.py:477-481`; What changed renders all non-error entries as articles with that slug id, `scripts/gen-dashboard.py:977-1002`. Executed synthetic tray/card probe: both tray targets were present in What changed.

§3a’s deletion cascade is correct as scoped. Current callers are only `_first_sentence -> _close_orphan_markup -> _orphaned_delimiters -> page_markup.orphaned_delimiters`, `scripts/gen-dashboard.py:157`, `scripts/gen-dashboard.py:193-196`, `scripts/gen-dashboard.py:162-168`, `scripts/page_markup.py:253-269`. `page_markup` has a CI self-test step, `.github/workflows/ci.yml:195-196`, but no case-count pin there. Mutation count is exact at `scripts/check-plan-code.py:432-450` and compared with `got != want`, `scripts/check-plan-code.py:538-543`.

Executed:
`python3 scripts/gen-dashboard.py --self-test` → `266/266 passed`
`python3 scripts/page_markup.py --self-test` → `78/78 passed`
`python3 scripts/check-plan-code.py --mutate .` → `5 file(s), 120 mutation(s), 0 survivor(s)`

NOT CONVERGED.
