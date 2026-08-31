# Adversarial review — dashboard "ask choices" design spec, round 1 (Claude half)

**Subject:** `docs/superpowers/specs/2026-08-31-dashboard-ask-choices-design.md` at `afcb346`,
branch `feat/dashboard-ask-choices`.
**Method:** every load-bearing line citation opened; §1a's measurement re-run against the live store;
§5c/§8's proposed renderer behaviour simulated against `docs/dashboard-entries.md` to see what the
page would actually do.

---

## B1 — Blocking

**Where** §8 (renderer caller) against §11 (*"changes nothing on the page as it stands today"*);
`scripts/gen-dashboard.py:418-432`, `:441`, `:451`, `:759-763`.

**What is wrong.** §8 says the renderer calls `decision_errors(plain, category)` and *"sets
`entry["error"]`"*. It puts no restriction on which entries are validated. Every `[needs-you]` entry
in the store today was written before the grammar existed and none contains a `**Decide:**` block —
measured: `grep -n "Decide:" docs/dashboard-entries.md` returns nothing. So all three become
malformed. Then the cascade in `parse_entries`' pass 2 fires: `ids` is built from `not e["error"]`
(`:418`), so the two entries that carry the clearing markers — `2026-08-29/2` (store line 44) and
`2026-08-30/7` (line 923) — hit `:427-429` and become malformed too.

Simulated with the real store and the real pass-2 code:

```
broken now: 2026-08-29/1  a [needs-you] entry with no **Decide:** block
            2026-08-29/2  [resolved: 2026-08-29/1] names an entry that could not be parsed…
            2026-08-30/5  a [needs-you] entry with no **Decide:** block
            2026-08-30/6  a [needs-you] entry with no **Decide:** block
            2026-08-30/7  [resolved: 2026-08-30/5] names an entry that could not be parsed…
```

**Why it matters.** §11's stated consequence is the opposite of what ships: five entries render as
red *"Could not parse this entry"* cards with their raw text dumped in a `<pre>`, on a page whose
entire subject is that it should be readable by someone who was away. Two of those five are entries
the new rule has no opinion about at all — they are collateral from the id graph. The spec proposes
breaking five live entries while asserting it changes nothing.

Secondary, measured and currently *not* triggered: `bucket_days` builds `with_entry` from
`not e["error"]` (`:458`), so if a date's only entries went malformed, `_bar`'s `unwritten` alarm
(`:651`) would fire *"SHIPPED WITH NO ENTRY"* on a day that has one. On today's store both dates
carry other valid entries, so `has_entry` stays `True` — the exposure is real but latent.

**Suggested fix.** State explicitly that the renderer applies `decision_errors` only to entries whose
header date is on or after a named cutover date, and add a falsifier: *fails if any entry in the
store at `7183111` renders as malformed after the change*.

---

## B2 — Blocking

**Where** §8 (*"one validator, two callers"*); `scripts/check-dashboard-entry.py:145-158`, `:241-254`,
`:21`; `scripts/gen-dashboard.py:294-309`.

**What is wrong.** The gate cannot feed `decision_errors(plain, category)` the thing the renderer
feeds it, and in one case cannot call it at all. Four separate defects:

1. **The gate has no entry body — it has a diff.** `collect` (`:241-254`) runs
   `git diff -U0 <base>...HEAD -- docs/dashboard-entries.md` and returns
   `(changed: list[str], added: bool, err)`. The patch text is consumed by one boolean comprehension
   at `:253` and discarded. `verdict(changed, added_entry: bool, pr_body)` (`:145`) never receives
   entry text. Reconstructing `plain` means skipping `@@` hunk headers, `-` lines and
   `\ No newline`, then re-deriving the `<!--tech-->` cut — none of which the spec specifies.
2. **A header-only edit yields a needs-you header with an empty body.** Adding `[needs-you]` to an
   entry already on the base branch rewrites one line; with `-U0` the body is unchanged context and
   is absent from the patch. `_added_entry_line` (`:57`) matches the new header, so the gate sees a
   `[needs-you]` entry whose reconstructed `plain` is `""`. Either it refuses a correct branch, or
   the implementer special-cases empty-body as "skip" and the gate is fail-open on exactly the edit
   that creates an ask. The spec does not choose.
3. **`docs/dashboard-entries.md` is in `EXEMPT_FILES` (`:21`), and `verdict` returns 0 at `:148`
   before it looks at anything else.** A branch whose only changed paths are exempt — the entries
   file itself, or `docs/reviews/` — exits `0, "no tracked files changed outside the exempt paths"`
   without the new check ever running. §9's falsifier *"Decision required — fails if a `[needs-you]`
   entry with no `**Decide:**` block passes the gate"* is satisfied on such a branch today, with the
   guard doing nothing. This is the house's own worst case: a guard reporting success having checked
   nothing.
4. **"One implementation" is true only of the cheap half.** What differs between the two callers is
   not the option-counting regex; it is the derivation of `plain` — file-and-`<!--tech-->` in the
   renderer, diff-reconstruction in the gate. The obvious remedy (share `parse_entries`) is closed
   off by the dependency arrow the codebase states at `gen-dashboard.py:294-309`: *"a GATE must not
   import the thing it guards"*. So the gate necessarily grows a second body-splitter — the drift
   §8 cites the `page_markup` precedent to avoid.

**Why it matters.** As specified, the gate either does not fire on the branches that matter, fires
wrongly on legitimate ones, or silently grows the duplicate implementation the section exists to
prevent. §9's *"Gate and renderer agree"* row cannot detect any of this (see H5).

**Suggested fix.** Move the shared boundary up: have `check-dashboard-entry.py` own an
`entry_blocks(text) -> list[block]` splitter that `gen-dashboard.py` imports, have the gate
reconstruct the post-image of the entries file (`git show HEAD:docs/dashboard-entries.md`, not a
diff) and run every entry whose header is newly added through it — and state where in `verdict` the
check sits relative to the exempt-path early return.

---

## H1 — High

**Where** §7 (*"Cannot-run is a failure"*); `scripts/gen-dashboard.py:451`, `:711-716`.

**What is wrong.** `unresolved` filters `e["needs_you"] and not e["error"]` (`:451`). Once §8 lets
`decision_errors` set `entry["error"]`, a `[needs-you]` entry with a typo in its decision block is
excluded from the tray, `rows` is empty, `store_error` is `None`, and `build` falls through to
`'<p class="none">Nothing needs you.</p>'` (`:716`) — in green, `--ok`.

**Why it matters.** An authoring slip converts a live ask into a confident all-clear. §7's table
enumerates three dead inputs and misses this one, which is the only one the new mechanism itself
creates. It is the same failure §1a is filed against, arriving through the fix.

**Suggested fix.** Add a row to §7: *a needs-you entry that fails `decision_errors` renders a
"could not read one ask" note in the tray*, plus a falsifier — *fails if a store containing one
malformed needs-you entry renders "Nothing needs you."*

---

## H2 — High

**Where** §5b (*"Omitted entirely when there are none"*) against §7.

**What is wrong.** When the store is unreadable there are zero parsed heads-ups, so under §5b the
"Worth knowing" heading is omitted. §7's table routes an unreadable store to the existing
`store_note`, which `build` emits inside the needs-you block only (`:707-714`). Nothing marks the
Worth-knowing block as NOT CHECKED; it simply is not there.

**Why it matters.** A missing heading is read as "nothing worth knowing", which is the
absence-vs-denial confusion §7 opens by quoting parent §4 against. Two dead-input rules that are each
correct compose into a silent one.

**Suggested fix.** §5b's omit rule applies only when the store was read successfully; on
`store_error` the heading renders with the NOT CHECKED note.

---

## H3 — High

**Where** §4 (*"PR reference"* row and the ⚠ box) against §6 (first line).

**What is wrong.** §4 defines the token as *"the literal token `PR #N`, never a bare `#N`"* and
devotes a warning box to why. §6 opens: *"When an option names `#N`, the renderer resolves N…"* —
the bare-`#N` rule §4 forbids.

**Why it matters.** These are two different implementations of the same rule in one document, and
the spec's own box says which one produces *"a confident, wrong link"*. §9's falsifier *"A backlog
`#N` is not a PR"* would be written by whichever author read §4; an implementer working from §6
writes the collision in and the falsifier catches it only if someone wrote it from the other section.

**Suggested fix.** §6 first line becomes *"When an option carries the token `PR #N`…"*.

---

## H4 — High

**Where** §4 (*"Decision opener"* row) and §9 (*"Heads-up cannot ask"*);
`scripts/check-dashboard-entry.py:83-138`.

**What is wrong.** The rule is *"a line whose first non-space content is exactly `**Decide:**`"*,
with no exclusion for inert Markdown contexts. The file this rule lands in already learned that
lesson for `NO-ENTRY:` and paid for it four times: `exemption_reason` (`:83-138`) handles fenced code
with the CommonMark closing-length rule (`:104-111`), indented code counting tab stops (`:63-80`),
HTML comments across lines (`:114-132`), and blockquotes — each comment records a **measured** escape.

**Why it matters.** This is not hypothetical. The dashboard entry announcing this very feature will
quote `**Decide:** …` in a fenced example, and it will be a `[heads-up]` or an ordinary entry — so
§9's *"Heads-up cannot ask"* falsifier fires on the entry that documents the grammar, and the gate
refuses the branch. Symmetrically, a `**Decide:**` inside a fence in a `[needs-you]` entry is counted
as a real decision the reader cannot act on.

**Suggested fix.** State that `**Decide:**` is recognised only outside fenced code, indented code,
HTML comments and blockquotes, and reuse `exemption_reason`'s scanner rather than writing a fifth
one.

---

## H5 — High

**Where** §9, row *"Gate and renderer agree"*.

**What is wrong.** The stated observation — *"a `[needs-you]` entry the gate accepts renders as a
broken entry, or the reverse"* — cannot fail once §8 is built. Both callers invoke the same
`decision_errors`, so any test that hands the same `plain` string to both is asserting
`f(x) == f(x)`. The thing that can genuinely disagree is the *derivation* of `plain` (B2), and this
row does not name it, so a green tick here is credited to a tautology.

**Why it matters.** It is the only falsifier defending the seam that B2 shows is the seam's whole
risk, and it is unfalsifiable as written.

**Suggested fix.** Restate as: *fails if the gate, given a real branch diff that adds entry E, and
the renderer, given the resulting file, disagree about whether E is malformed* — and drive it from a
constructed git repo, not from two calls to one function.

---

## M1 — Medium

**Where** §4's example block and §5a; `scripts/gen-dashboard.py:223-274`, `scripts/page_markup.py`.

**What is wrong.** §5a specifies the tray rendering only. The same decision block also lands in the
entry card's fold, which goes through `_prose` — paragraphs split on blank lines (`:235`), each
wrapped in one `<p>`, inline markup by `page_markup.render_inline`. Neither implements Markdown
lists (`page_markup` has `LINK_AT`, `DEL_AT`, emphasis and URLs; no list rule). So the block in §4's
example renders inside "What this means" as a single run-on line: *"Decide: Merge the
mutation-harness change - merge PR #181 [recommended] - hold it and tell me what to change - close it
unmerged"*.

**Why it matters.** §11 says the grammar *"is what makes the next 'whether to merge' name its pull
request"* — the first entry written under it produces a mangled card. Nothing in §5 or §9 covers the
entry card's rendering of a decision block.

**Suggested fix.** Either say the entry card renders decision blocks verbatim in a `<pre>`, or scope
list support into `_prose` and give it a falsifier.

---

## M2 — Medium

**Where** §5b (*"showing its title sentence and its first paragraph"*);
`scripts/gen-dashboard.py:249-271`.

**What is wrong.** The title *is* the first sentence of the first paragraph (`:405-411`). Asking for
both reproduces the duplication `_prose(drop_headline=True)` was built to remove — its comment
(`:236-248`) records the measurement: *"an unedited lede repeats it word for word and the eye reads
the same line twice"*.

**Suggested fix.** *"its title sentence, then the remainder of its first paragraph"*, deriving the
split by the same `_first_sentence` re-application the renderer already uses.

---

## M3 — Medium

**Where** §3, the ⚠ rejected-alternative box; `scripts/check-vocabulary-collisions.py:44-58`.

**What is wrong.** The box refuses an expiry *"because `scripts/check-vocabulary-collisions.py`
exists to enforce one mechanism per concern"*. That script reads the **Postgres catalog** for a
hard-coded eight-table list (`TABLES` at `:52-53`) and matches a curated list of coordination column
stems (`MECHANISM_STEMS` at `:56-58`). It cannot see `docs/dashboard-entries.md`, the renderer, or
anything about entry lifecycle, and it would not fail if an expiry shipped.

**Why it matters.** The design conclusion may well be right, but it is presented as mechanically
backed and is not — the house rule is that a script beats a claim only when it reads the thing the
claim is about. A later reader will treat "the ratchet forbids it" as settled.

**Suggested fix.** Keep the argument, drop the citation: *"one mechanism per concern — the principle
`check-vocabulary-collisions.py` enforces for schema, applied here by hand."*

---

## M4 — Medium

**Where** §6 (⚠ *"Bounded like every other subprocess here"*); `scripts/gen-dashboard.py:490-504`,
`:506-513`, `:516-545`.

**What is wrong.** `_gh_json` imposes `timeout=30` **per call** (`:495`). "One `gh pr view` per
distinct PR number per render" bounds duplicates, not the population — and the spec never says what
the population is. If options in resolved entries are also resolved, the count grows monotonically
with an append-only store; at 30 s worst case each, a render has no total bound. Separately, the
renderer already calls `gh pr list --state open` (`:507`) and `gh pr list --state merged --limit 40`
(`:531`) every render: a PR in the first is open, one in the second is merged, so most lookups are
answerable from data already fetched.

**Why it matters.** A page that can take minutes to build, on a mechanism whose stated value is
catching one stale link.

**Suggested fix.** Name the population (options in *unresolved* needs-you decisions only), state a
cap, and derive state from the two existing list calls with `gh pr view` only as fallback. If the
cost is judged not worth it, defer §6 entirely — B1/H1 are the defects the user actually reported.

---

## M5 — Medium

**Where** §6's table and §7's third row.

**What is wrong.** A `PR #N` naming a pull request that does not exist (a typo, or a backlog number
mistakenly written as `PR #74`) makes `gh pr view` exit non-zero, which lands in the *"could not
check"* bucket alongside a network failure or missing `gh`.

**Why it matters.** A writing error and an infrastructure failure are rendered identically, so the
one that a human can fix is indistinguishable from the one they cannot. §7's principle is precisely
that dead inputs must not be conflated.

**Suggested fix.** Distinguish `gh`'s "no pull requests found" from transport/auth failure and mark
the option *"no such pull request"*.

---

## M6 — Medium

**Where** §4, the *Options* row.

**What is wrong.** *"the markdown list items (`- `)"* leaves five shapes undefined, each of which two
implementers would resolve differently:

| Shape | Undefined behaviour |
|---|---|
| `* merge PR #181` / `+ merge PR #181` | valid Markdown lists; do they count as options? If not, a `needs-you` with two `*` options is refused as having none |
| `  - indented option` | is leading whitespace allowed before `-`? |
| a nested list under an option | sub-bullets counted as options, so **one** option with two sub-bullets satisfies "≥2 options" |
| an option that is only `[recommended]` | passes the count and the one-recommendation rule; says nothing |
| `[recommended]` not at end of line | *"may end with `[recommended]`"* — mid-line it is silently not a recommendation, so a marked preference is dropped without complaint |

(Two adjacent decisions with no blank line **are** covered — *"any non-list line ends the list"*, and
the second `**Decide:**` is a non-list line. `**Decide:**` mid-sentence is covered by *"first
non-space content"*. A blockquoted opener is not — see H4.)

**Suggested fix.** One row per shape with an explicit verdict; the nested-list case matters most
because it defeats the ≥2 rule while passing it.

---

## M7 — Medium

**Where** §9, rows *"Options are unfolded"*, *"Heads-up explains on sight"*, *"Separate blocks"*.

**What is wrong.** All three are pure absence assertions (*not inside a `<details>`*, *not only
inside the fold*, *does not appear under this heading*). Each is satisfied by a page that renders the
section empty, or not at all. The existing suite already states the rule these violate —
`gen-dashboard.py:1279-1281`: *"Both assertions are NEGATIVE, so each carries a POSITIVE
companion — otherwise a page that failed to render at all would pass them."*

**Suggested fix.** Pair each with a positive companion in the same row (options present in the tray
section **and** no `<details>` in it).

---

## M8 — Medium

**Where** §9, row *"`heads-up` reaches the parser"*.

**What is wrong.** *"the render must not raise"* is satisfied by wrapping the flag loop in
`try/except`. The property wanted is that the flag reaches a real branch: `needs_you is False`,
`error is None`, and the entry is categorised `heads-up`. Also note the trap the existing suite had
to solve for the identical case (`:1167-1197`): there are **two readings** of `FLAG` — this module's
import-time binding and `_GATE.FLAG` closed over by `header_error` — and updating one leaves
`header_error` rejecting the flag at the header, so the case passes on the *header* message while
the flag-loop `else` is never exercised.

**Suggested fix.** State the falsifier as the parsed values, not the absence of an exception, and
require the case to assert the flag-loop's own outcome.

---

## L1 — Low

**Where** §4, the `FLAG` code block.

**What is wrong.** Written as `[(needs-you|heads-up|resolved:\s*[^\]]*)]` — the outer brackets are
unescaped. The live pattern is `r"\[(needs-you|resolved:\s*[^\]]*)\]"`
(`check-dashboard-entry.py:26`). As presented it is a character class, and it is presented as the
replacement pattern, not as notation.

**Suggested fix.** Quote the escaped form.

---

## L2 — Low

**Where** §6 and §9, citations.

**What is wrong.** §6 cites `_gh_json` as `(:494)`; it is defined at `gen-dashboard.py:490` (`:494`
is the `subprocess.run` line inside it). §9 cites `EXPECTED_MUTATIONS` as `check-plan-code.py:432-451`;
the dict opens at `:432` and closes at `:452`. Every other citation checked was exact.

---

## L3 — Low

**Where** §2 (*"Also out: … the entry gate's existing NO-ENTRY path"*);
`check-dashboard-entry.py:151-155`.

**What is wrong.** `verdict` consults `exemption_reason` only after `added_entry` is false. A branch
that declares `NO-ENTRY:` *and* adds a malformed `[needs-you]` entry has no defined outcome under the
new rule — the exemption path is reached in one ordering and not the other.

**Suggested fix.** One sentence: a declared exemption does not excuse a malformed entry that was
nonetheless written.

---

## L4 — Low

**Where** §5d.

**What is wrong.** The `needs you` gloss is *"a decision is waiting on you — **nothing else on the
page is asking for anything**"* (`gen-dashboard.py:677`). §5d says it is unchanged and *"becomes true
for the first time"*. The second clause was already untrue of the open-PR rows in the same tray
(`:700-702`) and becomes less true beside a "Worth knowing" block.

**Suggested fix.** Trim the gloss to its first clause, which is the part §3 actually makes true.

---

## Premises checked and found correct

Recorded so a later round need not re-open them.

- §1a's measurement reproduces exactly against the store at `7183111`: raw `needs_you` flags
  `['2026-08-29/1', '2026-08-30/5', '2026-08-30/6']`, `unresolved(entries)` `[]`, no parse errors.
- Every line citation in §1a/§1b: tray `:691`, `unresolved` `:439-451`, badge `:768`, *"Nothing needs
  you."* `:716`, entry-ask rows `:692-694`, PR ask `:700-702` (and it does emit no link), glossary
  `:677`, plain fold `:774-776`.
- §4's warning about `gen-dashboard.py:369-383`: the `if/elif/else` is exactly there and the `else`
  at `:382-383` is what a new alternative falls into; the file's own comment records the measured
  `IndexError`.
- `check-dashboard-entry.py:24` does state it owns the grammar; `FLAG` is at `:26`.
- §9's mutation-pin claim: `EXPECTED_MUTATIONS` holds `gen-dashboard.py: 47` (`:443`) and
  `check-dashboard-entry.py: 12` (`:445`), and `check-plan-code.py:496-504` does refuse both
  duplicate names and duplicate edit anchors, so the count cannot be held by copying an entry.
- §1b's quotations of all three asks match the store (lines 27, 840-841, 898), and the ordinal
  mapping `2026-08-30/5` → store line 821, `/6` → line 870 is correct.
- §5c's "malformed → no badge" row: `build` emits `flag` only on the non-error branch (`:768`).
- The store contains no `**Decide:**` anywhere today, so the grammar collides with nothing already
  written — the damage in B1 comes from the *absence* of decision blocks, not their presence.

---

**Verdict: NOT CONVERGED** — 2 Blocking, 5 High, 8 Medium, 4 Low.

The two Blockings are the ones the brief asked me to attack hardest, and both hold under measurement
rather than reading: §11's "nothing changes on the page" is refuted by running the proposed rule
against the real store (five entries break, two of them by cascade), and the one-validator seam is
specified at a boundary the gate cannot reach, in a file the architecture forbids from importing the
only existing implementation of the missing half.
