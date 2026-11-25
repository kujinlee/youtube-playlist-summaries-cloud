Reviewed head: 56cc0f9817414986cc2504b87bf36d518ed3c373

# Round 3, Claude half: `decision-card-options` (PR #635, backlog #727)

My mandate was to refute two things: the round-2 rejection of Codex XM1, and the round-1 fold (dd86eaa1). **I could
not refute either.** I found four MINOR issues, one of them pre-existing. None is a BLOCKER or a MAJOR.

## 1. The XM1 adjudication holds, measured on behaviour

**Method.** I extracted master's `scripts/` with `git archive origin/master scripts`. I then composed the same
option-less fragments with master's `brief-compose.py` and HEAD's, using the same `--source`
(`docs/explainers/2026-11-08-topic-ci-sweep-speed.html`). The fragments were:

- the four real fragments in `docs/explainers/` that carry `data-decision`;
- `syn1`, with six decisions: a labelled one with a `.rec` sibling, one on an `<h2>` with `title="a&#124;b"` (an
  encoded `|` in a NON-choice attribute), one on an `<li>` with a nested `.rec`, an answered one, one inside a
  `<div>` with a `.rec` outside it, and one whose body text contains `A|B`;
- `syn2`, which has `data-decision-rec` and no options;
- `syn3`, with twin `<li>`s whose closing tags are omitted (so the script's own twin path runs).

**Bytes.** For every page both versions composed, I substituted master's `DECISION_JS` for HEAD's and
normalised the provenance `<time>`. **The result was identical to master's output** (6 of 6 pages). The only
difference between the two pages is the shared script.

**Behaviour.** I loaded each page in jsdom (`runScripts: 'dangerously'`, an http URL so `LIVE` holds, and a fetch
mock). For each page I recorded:

- every `.ex-pick` box's buttons and spans;
- then, on a fresh page each time, a click on **every** button: the box afterwards, the POST bodies, the box
  after `change` or `Cancel`, and localStorage.

**Master and HEAD gave identical JSON for every page**: 11 boxes and 33 clicks across `publishable-components`,
`syn1` and `syn3`, plus three real pages whose decisions are all answered (0 boxes). An option-less tag has no
`data-ex-options` (`scripts/brief-compose.py:1718-1722`), so `offer` takes the `else` branch (`:1360-1368`),
which is master's code verbatim. The rejection stands.

**The one behavioural difference I found** is that `syn2` composes on master and is REFUSED on HEAD ("has
data-decision-rec but no data-decision-options", `:1628-1631`). This is the specified orphan-rec refusal, and no
fragment in `docs/explainers/` carries either attribute. It is not a finding, but it does qualify the claim "a
card without options is unchanged": a page with a rec and no options is no longer accepted.

## 2. The round-1 fold holds

- **Encoded `|`.** The check runs on the decoded start-tag text, so any spelling that `html.unescape` turns into
  `|` is caught. That includes `&verbar;`, `&VerticalLine;` and the no-`;` form `&#124`. `&amp;#124;` is correctly
  not refused: the regex matches only `&amp;`, and the parser yields the literal text `&#124;`. An encoded `|` in a
  non-choice attribute of an OPTION-LESS decision is not refused (`syn1` composed). The refusal is gated on
  `options is not None` (`:1625`), as the comment states.
- **Bare and empty attributes.** A bare `data-decision-options` arrives as `""` and gives `[""]`, which is refused
  as "at least two". A bare rec with options is refused as "not one of". A bare rec with no options is refused as
  an orphan. When an attribute appears twice, the first one wins, which matches the browser.
- **The `.rec` sibling warning.** The parent stack entry is compared by identity, so `<p>` auto-closing is
  handled correctly, and so are a `.rec` nested in a later sibling and one after the parent closes. Two edge
  cases are under m2 and m3.
- **The 13 mutations.** I applied each one to a scratch copy of `scripts/` and ran the suite. **All 13 turned
  their named case red**, and each anchor matched exactly once. The control copy failed only the ambient
  `every real fragment in docs/explainers/ composes`, because the copy sits outside the repository. That matches
  the coordinator's round-1 note.
- `python3 scripts/brief-compose.py --self-test` gives **264/264 passed**.

## Findings

**m1 MINOR: the code comment still makes the byte-identity claim XM1 measured false.** At
`scripts/brief-compose.py:1119-1121` the comment says "written only when options are declared, so a page without
any composes byte-identical to before." The page does not compose byte-identical: it is 580 bytes longer
(Codex), and my test above confirms the difference is `DECISION_JS`. The round-2 adjudication says this
overstatement is where the invariant came from. **Fix:** reword it to "so an option-less TAG is unchanged, and its
card runs master's button code; the page differs only by the shared `DECISION_JS`, whose choices branch it never
takes."

**m2 MINOR: the `.rec` warning misses a sibling after an implicitly closed element.**
`decision_warnings('<ul><li data-decision data-decision-options="A|B">Q?<li class="rec">R</ul>')` returns `[]`.
In the DOM the second `<li>` is a sibling, so the card ignores a `.rec` with no warning. The cause is that
`_DecisionScan` models only `<p>` auto-closing (`_close_p`), so the second `<li>` sees the first as its parent
(`:1553-1555`). It is a false negative only, and the warning refuses nothing. **Fix:** either state the bound in
the `decision_warnings` docstring (only `<p>` implicit closure is modelled), or close an open `li`/`dd`/`dt`/
`option` the same way `_close_p` does.

**m3 MINOR: the warning fires on an ANSWERED decision.**
`decision_warnings('<p data-decision="A" data-decision-options="A|B">Q?</p><p class="rec">R</p>')` warns that
"its card … shows no ★". An answered card shows no buttons at all, so the warning is noise. **Fix:** in
`decision_warnings` (`:1661-1663`), also require that the decision is not answered (`found[n-1][2] == ""`).

**m4 MINOR (pre-existing; file, do not fold): refusals and the new warning count lines from different
origins.** `main` passes the whole fragment to `decision_warnings` (`:1922`). `compose` passes
`render_decisions` only the text after `</style>` (`:1747`, `:1814`). For one fragment the warning says
"line 7", which is correct in the file, while a `_choices` refusal on the next line says "line 5". The new
`_choices` refusals inherit master's body-relative numbering. **Fix:** offset `render_decisions`' line numbers by
the number of lines in `head`, or file it as a backlog row.

Doc note (not a finding): `explainer-delivery.md` §3a lists the refusals but omits "a rec with no options". One
clause would complete it.

VERDICT: CONVERGED
