Reviewed head: 7cf29bb418d205533a4f3cc007e18d5f99a161aa

# Round 3 — `backlog-698` (PR #620) — Claude half, adversarial

Reviewed HEAD 7cf29bb4. Scope: the round-2 fold, `git diff a0af8a4e..HEAD` (25162fcc, 7cf29bb4), and whether the whole
branch (`git diff origin/master..HEAD`) meets backlog row 698's **Fails if**: *any line whose rendered text holds a
six-word group-D run passes `--check`*. Codex sits out this round by alternation.

All reproducers below use the self-test's own fixture sentence (`I almost never pay attention to`, a six-word run
planted by the fixture's `d6.md`), not a real group-D quote. The scratch scripts are in
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/bl698/r3-claude-work/`.

## What held (run, not read)

| Check | Result |
|---|---|
| `--self-test` | 63/63 pass (worktree and a full external clone at 7cf29bb4) |
| `--out DIR` then `--check DIR`, real build | rc 0, 180 files, 708 fragments; stderr empty under node 18.20.8, 20.18.2 and 22.14.0 (CI pins 22) |
| stderr strictness on a real environment | No spurious CANNOT RUN on any node version. `NODE_EXTRA_CA_CERTS=/nonexistent` makes node warn, and the run is CANNOT RUN rc 2 with the warning quoted: fails closed and loud, which is correct |
| Letters-only over-refusal, re-measured | Over 3,498 Markdown files under `docs/` and the repo root: 1,002 (file, fragment) word-view hits, **0** letters-only-only hits. The fold's "0 added" holds (the fold's "294" counts something else, and its unit is not stated, see NIT N1) |
| Shortest fragments | 12 letters minimum, 14 fragments under 16 letters, all six-word windows. A dictionary resegmentation exists for 5 of the 14 shortest, but none forms a plausible benign English line, and the corpus measurement found none. Any false alarm refuses rather than passes. No finding |
| Composed vs decomposed letters | Every group-D quote is ASCII letters (non-ASCII is only dashes and the ellipsis; NFKC changes 0 of 708 fragments). A decomposed `e` + U+0301 in the output still matches, because `isalnum` drops the Mn mark and keeps the `e`. Ligature `ﬁ` casefolds to `fi`. Entities resolve through `convert_charrefs` |
| `<details open="false">`, uppercase `<DETAILS>/<SUMMARY>`, `<summary>` outside `<details>`, a second `<summary>`, a stray `</details>` | None gives a false green: each run is still found |
| `delink` on both sides | Reopens nothing that round 1 closed. On the output side it only adds a text. On the quote side it only adds fragments, and the letters view applies to them unchanged. The six LOOSENING-CHECK lines it restores are add-only |
| Mutations in a full external clone | 7cf29bb4 cloned, `node_modules/markdown-it` copied in. Six mutations each go red on the case they name: r1 X1 "no tight reading", r1 X1 "source quote read only in `read`" (both re-attributed), r2 X1 "letters-only keeps whitespace", r2 X2 "source quote not link-reduced", r2 X3 "whitespace on stderr accepted", r2 X4 "a `<details>` close does not end its hiding". The anchor of every edit in all 61 + 16 manifest entries resolves exactly once |
| CI non-self-test checks | rc 0: check-canonical-source, check-fixture-variation, check-ratchet-contract, check-rc-contract, check-docs, check-backlog-closure (warn-only), check-review-rounds, check-decision-scheme, check-reference-namespace and check-doc-citations (`--base origin/master`), check-producer-enumeration, check-gate-falsifiability, check-claim-propagation, check-group-claims. `check-selftest-counts --only build-shipped-corpus.py` verified 63. `check-canonical-source --self-test` 33/33 |

## Findings

### F1 — MAJOR — `fix_induced: true` — component `corpus-views` — an unclosed `<details>` inside a container hides the rest of the file in both joining readings, a loosening of a refusal a0af8a4e made

- **Where:** `scripts/build-shipped-corpus.py:229-230` (`self.details.append(...)`), `:242-245` (popped only on `</details>`), `:252` (`handle_data` drops text when not `_shown()`).
- **Input:** an output file holding
  ```
  > <details>

  I almost never <span hidden>zq</span> pay attention to
  ```
  The same happens with `- <details>` (a list item) or `<div><details></div>`.
- **Observed:** `--check` passes (no hit). On a0af8a4e, before the fold, the same file is refused.
- **Expected:** refuse. Chromium (playwright, `document.body.innerText`) shows `I almost never pay attention to`. The container's end tag (`</blockquote>`, `</li>`, `</div>`) closes the `<details>` implicitly, so the paragraph after it is shown, and the hidden span is not. That is a six-word run in the rendered text, which is the **Fails if** exactly.
- **Why it passes:**
  - `read` keeps the hidden span's text, so it reads `never zq pay`, in both the word and the letters views.
  - `tight` and `loose` still treat the `<details>` as open-and-closed, because only a literal `</details>` pops it. So they drop everything to the end of the file.
  - No view both drops the hidden span and keeps the paragraph.
- **Root cause:** X4's fix CHANGED the `tight` and `loose` readings instead of ADDING a reading. The module's own rule is that every view only adds hits. Before the fold, `tight` was the view that dropped hidden text and kept the rest. Now no such view exists whenever a `<details>` runs away.
- **Fix:** either is sufficient, and the first is the house rule:
  - (a) Keep the pre-fold `tight` reading, with no `<details>` handling, as its own reading, and put the closed-`<details>` drop in a NEW reading.
  - (b) Track the open-element stack in `_Visible`. An end tag of an element opened before a `<details>` (or before a hiding element, see F2) closes it, as the HTML tree builder does.
- **Case:** the blockquote, list and div inputs above, red on 7cf29bb4.
- **Mutation:** one that removes the implicit close (or the extra reading), killed by that case.

### F2 — MINOR — `fix_induced: false` (introduced by the round-1 fold, outside this round's diff) — component `corpus-views` — the same runaway for a `hidden`/unshown element

- **Where:** `scripts/build-shipped-corpus.py:219-226`, `:238-241`.
- **Input:** `<div><span hidden>x</div>`, then a paragraph `I almost never <span hidden>zq</span> pay attention to`.
- **Observed:** pass. Chromium shows the run, because `</div>` closes the span.
- **Expected:** refuse.
- **Why it passes:** `self.hiding` ends only on its own tag's close, so `tight` and `loose` drop the rest of the file. `read` keeps `zq`.
- **Comparison with master:** master misses this too (it reads raw bytes), so this is not a loosening. It is the X4 miss class, which round 2 rated MINOR. F1's fix (b) closes both.
- **Case:** the input above.

### F3 — MINOR — `fix_induced: true` — component `mutations` — two of the twelve re-attributions claim a subsumption that is false; a property case kills them, and none exists

- **Where:**
  - `scripts/mutations/build-shipped-corpus.json`, the entries "a source quote is fragmented in its raw Markdown, not as rendered ⟳ RE-ATTRIBUTED…" and "PR #620 r1 X1: a source quote is read only in the `read` reading (and plain) ⟳ RE-ATTRIBUTED…";
  - the `views` docstring, `scripts/build-shipped-corpus.py:304-308` ("no run-level case can tell several readings apart any more").
- **Input:** a SOURCE quote `I almost never <span hidden>zz</span> pay attention to it`, with an output of `I almost never pay attention to it.`
- **Observed:** HEAD refuses, which is correct. With either mutation's `quote_texts` the output PASSES, because every window keeps `zz`. So on the quote side, `tight`/`loose` against `read`/raw IS distinguishable at the run level. Only `tight` against `loose` is subsumed by the letters view.
- **Effect:** the inventory pin kills both mutations, so nothing is unguarded today. But two names, and the docstring, assert an equivalence that is false. The property case that would kill them honestly is missing, and the inventory case would also die on a harmless reordering.
- **The other ten:** I checked them against this argument. On the output side, `read` (which keeps hidden text) together with `tight` or `loose` (which drop it) covers every split, and `tight` against `loose` differ only in spacing, which the letters view deletes. So the other ten are genuinely run-equivalent: the inventory pin is the only honest killer, and it is labelled as one.
- **Fix:**
  - add the hidden-text source-quote case;
  - re-bind those two mutations to it;
  - narrow the docstring to "`tight` and `loose` are indistinguishable at the run level; `read` against the hiding readings is not".

### F4 — MINOR — `fix_induced: false` — component `cannot-see-doc` (or `corpus-views` if fixed in code) — Latin compatibility forms are a silent miss that *What this cannot see* does not name

- **Where:** `scripts/build-shipped-corpus.py:325` (`letters_only`), `:49-52` (the homoglyph sentence names only "letters from another script (a Cyrillic `а`)").
- **Input:** `I almost ｎｅｖｅｒ pay attention to` (full-width), or `never` in mathematical bold (U+1D427…).
- **Observed:** pass. A reader sees the words, and `casefold` does not map these forms to ASCII.
- **Expected:** refuse, or name the miss.
- **Comparison with master:** pre-existing; master misses them too.
- **Fix:** apply `unicodedata.normalize("NFKC", …)` before `casefold` in `letters_only`, or as an extra add-only text. Every group-D fragment is NFKC-invariant (0 of 708 change), so the quote side is unaffected. Otherwise, name "compatibility forms (full-width, mathematical letters)" beside the homoglyph limit.

### N1 — NIT — `cannot-see-doc` — the measurement's "294" has no unit

`scripts/build-shipped-corpus.py:60-61`: "added 0 hits to the word views' 294". I measured 1,002 (file × fragment) word-view hits over 3,498 files. "294" is presumably files or lines. Name the unit, so the next re-measurement can be compared with it.

### N2 — NIT — `renderer-call` — strict stderr makes an environment warning CANNOT RUN

This is fail-closed and loud (`NODE_EXTRA_CA_CERTS` pointing at a missing file is one such warning), so it is correct. One line under the rc-2 list ("any node warning, an environment one included") would save a confused rerun.

## Thrashing watch / Phase 6

- F1 and F3 are fix-induced, in `corpus-views` and `mutations`.
- **No fix-induced finding is in `renderer-call`.** Round 2's X3 was in `renderer-call`, so the coordinator's two-consecutive-rounds-in-one-component condition is **not met**, and Phase 6 does not arm on this round.
- F1 is the second round running in which a fix to the `_Visible` readings opened a new miss. Round 1's C3 hiding introduced the F2 runaway, and round 2's X4 introduced F1. Both come from the same missing piece: `_Visible` has no element stack, so any start/end pairing it keeps can run away. If round 4 brings another `_Visible` finding caused by the F1 fix, that is the `corpus-views` thrashing signal.

## Mergeability against the **Fails if**

**Not mergeable.** F1 is a rendered six-word run, confirmed in Chromium, that passes `--check`. It was refused one commit before the fold.

VERDICT: NOT CONVERGED
