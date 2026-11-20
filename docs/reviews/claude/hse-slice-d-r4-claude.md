Reviewed head: 0c451cbd65f272c3e509aa2d1b792b882380495e

# Round 4 — `hse-slice-d` — Claude (adversarial) — reviewed 0c451cbd

Commands, run in the worktree at 0c451cbd:
- `python3 scripts/check-publishability.py --self-test` → `105/105 self-test cases passed` (37.9 s)
- `python3 scripts/check-publishability.py --out <scratch>/live.json` → `45 component(s): 45 scanned, 0 CANNOT RUN`.
  Its `components` object is EQUAL to the committed `docs/marketplace/scan-2026-11-17.json`'s (296 findings each,
  0 lost, 0 gained; mentions equal too). The committed `measured_at` is 53f2f20f, the r3 fold's parent: the scan was
  taken on the uncommitted fold. This is the provenance bound already narrowed in round 1 (Xm2), and the content is
  now verified equal at 0c451cbd, so it is not a finding.
- The four round-3 mutations (the last four entries of `scripts/mutations/check-publishability.json`), applied by hand
  on a clone, one at a time, under `PLAN_CODE_MUTATION_RUN=1`: each anchor occurs exactly once, and each mutant
  turns exactly one case red, the case its `expect` names. The full `--only check-publishability` sweep was NOT run
  (158 mutations × 8.1 s per self-test under the harness ≈ 21 min, over the 4-minute bound).

Probes ran on a `git clone` of the worktree in the session scratch directory (outside the repository). Each probe was
committed there and scanned with `--out`. Markdown probes were appended to `.agents/skills/brief/SKILL.md` (base 195
lines) and Python probes to `scripts/page_chrome.py` (base 2759 lines). To decide fix-induced, the same probe tree was
also scanned by the pre-fold script (`git show 53f2f20f:scripts/check-publishability.py`).

Each round-3 fold, checked against its own input:
- XM1 holds: `REVIEW_R4C = os.getenv("REVIEW_R4C") or (None or None)` → `page-chrome` detector 6 `config` at line 2762.
- XM2 holds for blank lines between plain items. Xm2 holds: Codex's "Historical examples:" input is a mention, which
  is the fold's case. Xm1 holds for "tools that we never use:". The control "Read these first:\n\n- `CronDelete`" is a
  finding (`skill-brief` line 228).

## Findings

- **MAJOR — scripts/check-publishability.py:335, 342:** The negation window (24 characters before the verb, `NEGATES`)
  is not clipped to the verb's own sentence or clause. A negation in the PRECEDING sentence therefore cancels a real
  imperative. Input, appended to scratch `brief/SKILL.md`: "Do not guess. Read these first:" + blank +
  "- `CronList`", and "No shortcuts here; run these:" + blank + "- `CronCreate`". Observed: both are detector-4
  MENTIONS at the fold (lines 201 and 207). The pre-fold script, on the same tree, reports both as `tool-name` FINDINGS.
  The same applies to "This step is not optional.\nRead these files:", because the paragraph is joined across lines
  before the window is taken. Live tree: no change (296 → 296, equal sets), so the committed inventory is not wrong
  today. This is why it is MAJOR and not a BLOCKER. Suggested direction: start the window at the last `[.;:!?]`
  before the verb. Fix-induced: YES (Xm1's fold).

- **MINOR — scripts/check-publishability.py:304-306:** XM2's fold keeps a list across blank lines only when the line
  above the blanks is itself a list item. A loose list item with a continuation PARAGRAPH (indented, after a blank)
  therefore still ends the list. Input: "Read these files first:" + blank + "1. `Monitor`" + blank +
  "   It shows the live state." + blank + "2. `ScheduleWakeup`". Observed: `ScheduleWakeup` (line 217) is a mention at
  both the fold and pre-fold. An indented continuation is accepted only when `j == i - 1`. A nested SUB-LIST after a
  blank does keep the list, because `LIST_ITEM` allows leading whitespace. The bound is a prose continuation
  paragraph. Fix-induced: no (an incomplete fix of XM2).

- **MINOR — scripts/check-publishability.py:313:** `_always_none` recognises a constant `None` and a BoolOp whose
  operands are ALL always-None. It does not recognise other expressions that always evaluate to None. Inputs:
  `os.getenv("REVIEW_R4A") or (None and "unused")` (short-circuits to None) and
  `os.getenv("REVIEW_R4B") or (None if REVIEW_R4A else None)`. Observed: neither is reported (the R4C control, an
  `or` of Nones, is). The same rule exists for `and`: `None and X` is always None, but `X and None` is not, so the
  fix is not a simple widening. Fix-induced: no (the same class as XM1, narrower now).

- **MINOR — scripts/check-publishability.py:296-310 (pre-existing, not fold):** An imperative list item that ends in a
  colon does not introduce its nested list. Input: "- Then read these:" + "  - `RemoteTrigger`". Observed: a mention
  at both the fold and pre-fold. The walk climbs over the parent item, and `_introduced` then looks at the paragraph
  ABOVE the parent item, never at the parent item itself. Fix-induced: no.

Checked and NOT a finding:
- A one-capital tool name (`Monitor`, `Bash`, `Read`, ...) is never a `tool-name`. This is the documented camel-case
  bound of detector 4 (`CAMEL_RE`, docstring line 523).
- The blank-line skip cannot climb across a fence, a heading or a table row: none of those matches `LIST_ITEM`, so the
  walk breaks there.
- No index error: `j` stays ≥ 0, because `while i > 0` and `j = i - 1`.

## Loosening answers

Does this change loosen any existing gate? **One detection rule loosens; no existing gate does.**
- The round 3 fold LOOSENS detector 4 itself. A paragraph with a negation within 24 characters before its only
  imperative no longer introduces a list. That is the MAJOR above. It is new behaviour inside this slice's own scanner,
  not an existing gate, and the live inventory is unchanged.
- The branch's edits to existing gates TIGHTEN or only re-pin them:
  - `check-shipping-sets.py`: the edge-set pin 344 → 347, with the three gained edges named and lost 0.
  - `shipping-sets.json`: `expected_count` 102 → 103, adding the new manifest.
  - `check-plan-code.py` and `check-selftest-counts.py`: one new inventory row each.
  - `check-fixture-variation.py`: a new pinned key set.
  - `sweep-costs.json`: a new price.
  - `ci.yml`: adds two steps (the self-test, and the scan red on CANNOT RUN).
  None removes a case, widens an exemption or lowers a count.

VERDICT: CONVERGED
