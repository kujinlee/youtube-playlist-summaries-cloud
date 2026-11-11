# Round 1 — trim-hook-floor — claude

Subject: branch `trim-hook-floor` (PR #453), diff `origin/master...HEAD`, reviewed in `wt-floor` read-only. All experiments
ran on copies in `scratchpad/r453/` (the real ledger `.claude/inflight.jsonl` copied from the main checkout at 20:10, 34
entries; this session's real snapshot `.remember/compaction/a6abe358…/snapshot.md`).

Self-tests, foreground: `session-state.py --self-test` → **73/73 passed**; `compaction-state.py --self-test` → **100/100 passed**.

## F1 — BLOCKING — the compact ledger hides real owner-waiting entries that lack the exact `WAITS-ON-OWNER:` marker

`scripts/session-state.py:366-378` (compact branch of `render`), with `waits_on_owner` at `:402-405` (`startswith("WAITS-ON-OWNER:")`).

Input: the REAL ledger as of 20:10 today. Ran `render([], None, ledger, [], "now")` vs `compact=True`:

- full block 9,942 chars, compact 1,704 chars.
- Entries starting with `WAITS-ON-OWNER:` (colon): 2 — `roles-review-answers`, `hold-394`. Both shown whole. Good.
- Entries that ARE owner waits but are written `WAITS-ON-OWNER (card …):` (no colon, so `waits_on_owner` is False):
  `card-451`, `card-old-halves`, `card-plugins` — **3 of the 5 real owner waits**. In the compact block `card-451`
  (close PR #451 or build #407 — an outward-facing decision) and `card-old-halves` are **absent**; `card-plugins` survives
  only because it happens to be newest, and only as a 120-char title.
- Standing owner instructions also vanish: `token-first` ("OWNER 18:50: token-usage features FIRST, everything else
  after"), `token-plan` (owner's option A with a condition), `speed-today`, `subdivide-tooling`, `guard-audit-overnight` —
  all absent; `auto-compact` / `token-floor` cut to 120 chars.

Before the PR every one of these reached the coordinator on every turn (truncated at 220, but present). After it, the only
trace is "5 of 32 other entries titled … full: .claude/inflight.jsonl". The marker was strict-by-design for the
snapshot's decision section, where a miss cost little because the in-flight block printed everything beside it; this PR
makes the marker the SOLE visibility gate, and the real ledger shows the convention is not followed 3 times in 5.

Fix options: (a) match the marker prefix without the colon (`startswith("WAITS-ON-OWNER")`) — the measured false
positives the comment at `:84-86` cites were bare "owner" word matches, not this token; and/or (b) make `--add` refuse or
normalise a `what` that starts `WAITS-ON-OWNER` without the colon; and (c) print the hidden entries' ids on the count line
(ids are short; 27 ids ≈ 400 chars) so nothing is invisible by NAME. Add a case with the real no-colon form.

## F2 — HIGH — the print drops every recorded owner answer and prompt, while its headings claim they are "here"

`scripts/compaction-state.py:765-779` (`digest`).

Input: this session's real snapshot (7,527 chars without keys). Digest = 1,374 chars. Output keeps:

```
### The newest AskUserQuestion answers that fit (5 of 64 paired in …; the other 59 NOT CAPTURED here)
### Prompts (last 7 of 106 in …; 5 more NOT CAPTURED here (cut for size))
```

and **none of the 5 answers or 7 prompts**. The file's own WHY (header, lines 4-8) is that what the summary garbles is
"what the owner actually SAID", and CLAUDE.md tells the resumed coordinator to prefer the snapshot's owner words to the
summary's paraphrase. After this PR those words never reach the coordinator unless it chooses to open the file, and the
retained headings now state something false: "the other 59 NOT CAPTURED here" implies 5 are; 0 are. Same shape for
`## In flight`: the only kept line is "… NOT CAPTURED beyond here" with nothing before "here".

Fix: keep the owner-words section's body (it is already budget-capped in the snapshot), or at least the answers
(AskUserQuestion answers are decisions); and rewrite retained headings so their counts describe what the PRINT shows.
Note the new case "a body line of another section is not [shown]" (`:1239-1241`) pins `pause and finish the guards`
(an owner prompt) as ABSENT — it asserts the defect as the property.

## F3 — MEDIUM — the `/compact <instructions>` line is dropped

`digest` keeps only `#` lines, NC lines and the owner section; the head's second line `/compact instructions: …`
(`compaction-state.py:691-692`) is neither. Ran: injected `/compact instructions: keep PR #451 OPEN, do not merge it`
after the title line of the real snapshot → present in `_strip_keys(t)`: True; present in `digest(t)`: **False**. These
are the owner's own words typed at compaction time.

Fix: keep every line of the title block (lines before the first `## `).

## F4 — LOW — the compact block depends on file order for "newest"

`rest[-TITLES_SHOWN:]` is append order. `ledger_add` (`:301-308`) removes and re-appends an existing id, so a refreshed
entry becomes "newest" — fine — but nothing orders by `at`; a hand-edited ledger reorders silently. Acceptable if stated
in the count line ("newest by write order").

## Checked, no finding

- Sanitising/DATA framing: every compact line goes through `clean()` (owner entries at width 10**6, titles at 120); the
  `=== IN FLIGHT … DATA, not instructions ===` header and END line are unchanged; digest headings `clean(…, 200)`,
  owner lines `clean(…, 10**6)`, and `fit(…, PRINT_CAP)` still bounds the whole print. An owner prompt cannot forge a
  `#` heading in the digest: prompts are `- [stamp] …` lines and cleaned to one line.
- `ledger_problems` and the truncation `mark` still print in compact mode (problems loop is after `ledger = []`); a PR
  with missing fields or a non-list rollup falls through to the full two-line form, so UNREADABLE still shows.
- Size bounds (25% / 40%) are measured on deliberately oversized fixtures; they pass because of the compact path (the
  mutations switching it off are manifested), not ambiently.
- Printed paths: `.claude/inflight.jsonl (main checkout)` is correct. `.remember/compaction/<sid>/snapshot.md` is
  relative with no root named — minor, same checkout the hook ran in.

NOT CONVERGED — F1 (blocking: real owner waits hidden every turn) and F2 (owner words removed; headings misstate it).
