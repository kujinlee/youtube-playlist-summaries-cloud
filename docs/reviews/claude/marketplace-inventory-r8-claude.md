Reviewed head: 1fd65315dc2c29f795c87ad739da6b182614e1e4

# PR #376 r8 — Claude half (FINAL round, round cap: only a BLOCKER is folded)

Scope, per the brief: pay for the merge HOLD's `NO-REVIEW:` line — (1) the `_VOID_EXPECTED` work in
`scripts/check-claim-propagation.py`, (2) the explainer-page edits at `d06da80c` / `4d07ee59`, and
(3) confirm `scripts/recall-llm.py` is not in the diff.

## Measurements (run at the head above, in the PR worktree)

| Check | Result |
|---|---|
| `python3 scripts/check-claim-propagation.py --self-test` | **58/58 self-test cases passed** |
| `python3 scripts/check-claim-propagation.py` | rc=0, `derived figures OK — 2 figure(s) agree with their source` |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/check-claim-propagation.py --allow-long-local` | EXIT=0, **18 mutation(s), 18 killed, 18 attributed, 0 survivor(s)** (diagnostic slice) |
| `git diff origin/master...HEAD --name-only \| grep recall-llm` | no match (grep rc=1) — `scripts/recall-llm.py` is NOT in the diff |
| `git ls-tree -r --name-only <c> -- app lib components worker supabase \| wc -l` | 248 at HEAD, `a4f6d4b5`, `2e79f464`, `d06da80c`, `4d07ee59`, `origin/master` — the page's 248 and its "re-run it" claim hold |
| the nine enumerated files, `wc -l` summed (`explain-diff`/`brief`/`explain-findings`/`explain-topic` SKILL.md, `shared/explainer-delivery.md`, `brief-compose`, `explainer-serve`, `page_chrome`, `page_markup`) | **6,542 at `a4f6d4b5`; 11,272 at HEAD** |

## Part 1 — `_VOID_EXPECTED` / `_Carriers.VOID`: refutation attempted, not refuted

The identity case (`sorted(_Carriers.VOID) == sorted(_VOID_EXPECTED)`) plus one behaviour case per
literal member is sound: removing a member reddens both, adding one reddens the identity case, and
the manifest's mutation 17 ("the VOID vocabulary shrinks…") is killed. Probes run against
`_derived_values` / `_derived_carrier_counts` (script in the coordinator's scratchpad, `r8probe.py`):

| Input | values | counts | Verdict |
|---|---|---|---|
| `<p><BR DATA-DERIVED="k">771 after</p>` | `{}` | `{k:1}` | correct (parser lowercases) |
| `<b data-derived="k">12</br>77</b>` | `{k:'1277'}` | `{k:1}` | correct (stray void end tag ignored) |
| `<b data-derived="k">12<img>77</b>` | `{k:'1277'}` | `{k:1}` | correct |
| `<span data-derived="k"/>999` | `{}` | `{k:1}` | loud: "DERIVED figure absent" |
| `<input data-derived="k" value="1277">` | `{}` | `{k:1}` | loud: "absent" (r4 CODEX H2 holds) |
| `<p><keygen data-derived="k">771 after</p>` | `{k:'771 after'}` | `{k:1}` | see L1 |
| `<p><image data-derived="k">771 after</p>` | `{k:'771 after'}` | `{k:1}` | see L1 |

No input found where a WRONG displayed figure passes because of the void handling.

## Part 2 — explainer edits `d06da80c` / `4d07ee59`

`d06da80c` dated "same nine, today" → "same nine, at `a4f6d4b5`" in two places and dated the
11,624 / 665 / 11,642 figures. `4d07ee59` corrected 262 → 248 files. The arithmetic holds
(11,624 − 647 + 665 = 11,642) and the spec agrees with 11,624 and 6,542 at `a4f6d4b5`.

## Findings

### B1 — BLOCKER: the page tells the owner "today" the nine files are 6,542 lines (1.82× low); at HEAD they are 11,272 and the spec says 11,237

`docs/explainers/2026-10-15-brief-marketplace-inventory-walkthrough.fragment.html:410` (and the
composed `.html`, same row):

    <tr><td>Same nine files, today: 3,599 vs 6,542</td><td><strong>1.82× low</strong></td></tr>

Input: that row, read at HEAD. Observed: the same nine files sum to **11,272** at HEAD (table
above), and the spec's own re-measurement — `docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md:169`,
*"Re-measured 2026-11-09 at master `cfad72b3`, at the owner's request … This part needs to be
updated"* — says **11,237 (1.72x)**. So "today" the ratio is ~3.1× low, not 1.82×. The page
contradicts the spec, and the false figure is presented in the present tense in a comparison table
the owner reads as the summary. This is exactly the instance `d06da80c` set out to fix (it retitled
"same nine, today" at two other sites) and missed: instance, not class. Fix: date the row ("at
`a4f6d4b5`"), as its two siblings now are — and, if the page is meant to reflect the owner's 11-09
request, carry the `cfad72b3` re-measurement (see M1).

### M1 — Medium: the page carries none of the spec's 11-09 re-measurement

The spec §3 now leads with an 11-09 (`cfad72b3`) column the owner asked for (nine files 11,237;
effort (3) Python 15,222; total 16,503; shared contracts 677). The page's figures (fragment
:327, :344–356, :368–373) are all dated to `a4f6d4b5` / "the time of writing", so they are not false,
but the page says nothing of the later measurement, and :373's "at the time of writing the shared
contracts are 665 and the total 11,642" will read as the latest word. Not folded under the cap;
reported.

### L1 — Low: elements the HTML parser treats as void are missing from `VOID`

`scripts/check-claim-propagation.py:144` / `:683`. `keygen`, `image` (parsed as `img`), `basefont`,
`bgsound`, `frame` are inserted-and-immediately-popped by the WHATWG tree builder but absent from
`VOID`. Input `<p><keygen data-derived="k">771 after</p>` → observed `{'k': '771 after'}` (the
carrier swallows following text). Consequence is almost always a LOUD mismatch (a false positive),
not a silent pass; the only "pass" I could construct (`<keygen data-derived="k">12<p>77</p>` →
`'1277'`) displays the correct digits anyway. All are obsolete; no page uses them.

### L2 — Low: the identity case's name says "the 14 HTML void elements"

`scripts/check-claim-propagation.py:684`. To my knowledge the current WHATWG void-elements list is
13; `param` was removed with the element's obsoletion, though the parser still treats it as void, so
INCLUDING it is the right behaviour. The case name overstates the standard; behaviour is correct.
Not verified against the live standard in this round (no network fetch made).

VERDICT: NOT CONVERGED
