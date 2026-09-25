# Round 1 — `round-record-substrate` — Claude half (adversarial)

**Subject:** `docs/superpowers/specs/2026-09-25-round-record-substrate-design.md`
**Branch:** `backlog-117-parser-substrate` · **HEAD:** `5c9aea57` · **Date:** 2026-09-25
**Mandate:** refute, do not confirm. Phase 1 design spec, nothing implemented, human gate not yet passed.

**Verdict: NOT CONVERGED. The spec should NOT pass its Phase 1 gate as written.**

Two Blocking findings. The direction is right — `json.loads` is the correct substrate and the
rejections of `pyyaml` and of vendoring reproduce — but the spec's **feasibility evidence measures
an object that discards five of the eight keys the record actually carries**, and both of its
**pre-committed falsifiers are measurably incapable of firing**. The deletion list also removes the
enforcement of two of the six defects the spec cites as its own motivation, with no survivor named.

All numeric claims below were produced by running code against this tree. Commands are quoted.

---

## Findings

### B1 — Blocking · `header-schema` · aim: deliverable · fix_induced: false

**Deleting `parse_header`'s body deletes the guards for r3's Blocking and r6's High, and the
"kept, unchanged" list names no survivor. Both defects reopen.**

§1 says what is deleted (`parse_header`'s regex body, `_findings_span`, `_scalarise`,
`_block_findings`) and what is kept (`_validate`, `REQUIRED`, `ROUND_REQUIRED`). But:

- `_validate` is **per-finding only** (`scripts/check-review-decision.py:273-284`). It never sees a
  top-level key.
- `ROUND_REQUIRED` (`:263`) is a **constant**. The code that enforces it is the loop at `:245-251`
   — inside `parse_header`, i.e. inside the region marked for deletion.
- The refusal of an absent `findings:` key — the explicit repair for **r3's Blocking** — is `:232`,
  also inside the deleted region.
- The `round:` presence/int check is `:203-205`, also inside it.

`json.loads` does not supply any of these. JSON is happy to omit a key; **an absent key is exactly
the "a missing key is a silence" shape that cost r3 a Blocking.** Measured, applying only what the
spec says survives:

```
$ python3 .../m5.py       # json.loads(json.dumps(obj)) then _validate on each finding, then decide()
  absent `findings` key        -> _validate raises? no  |  decide() = STOP
  absent `fixes_nontrivial`    -> _validate raises? no  |  decide() = STOP
  findings not a list          -> _validate raises? no  |  decide() = STOP
  fixes_nontrivial as a string -> _validate raises? no  |  decide() = ROUND_OWED
```

`{"round": 1, "fixes_nontrivial": false}` is **well-formed JSON** and reaches **STOP**. That is r3's
Blocking restored verbatim, and `{"round": 1, "findings": []}` reaching STOP is r6's High restored.
The spec's own "How we would know it failed" bullet — *"a round document is malformed and `decide()`
returns a verdict instead of `CANNOT_RUN`"* — fires on the design as specified.

⚠ **The spec's §1 warning is aimed one notch too low.** It warns that a reader will delete
`_validate`; the actual hazard is that a reader will believe `_validate` was ever enough. The
architecture review that convened this work says the reshaping *"reduces `_validate` to a schema
check"* (`docs/reviews/architecture-review-2026-09-25-decision-family.md:180`) — **changed**, not
*"kept, unchanged"*. The spec and the review disagree about the one function both call load-bearing.

**Fix:** §1 must name a top-level schema check as part of what is BUILT, not what is kept: required
keys `round` (int), `fixes_nontrivial` (bool), `findings` (list), each refusing on absence and on
wrong type. That is also F2/#185's seam falling out of the redesign, as the review predicted.

---

### B2 — Blocking · `conversion-falsifiers` · aim: instrument · fix_induced: false

**Neither pre-committed falsifier can fire on the hazard §2 calls "the one real hazard in this
change". Falsifier 2 is vacuous by construction; falsifier 1 is a five-value collapse.**

**(a) Falsifier 2 cannot fail.** `parse_header` *already* refuses unless the list-marker count inside
`_findings_span` equals the parsed finding count (`:243-246`). So for every document that parses
today, the parity §2.2 proposes to check holds **by construction**. Measured over the whole corpus:

```
$ python3 .../m2.py
falsifier-2 (span markers vs parsed findings) disagreements across the 30: 0
```

**(b) And it cannot be made independent without reintroducing a fixed defect.** §2.2 says *"count
`findings:` list markers in the original YAML by an independent count"*. Either it reuses
`_findings_span` — then it is the broken parser's own rule and part (a) applies — or it counts
markers over the whole header, which is **r2's Medium** (a bullet inside a `halves` block scalar
counted as a finding, a false CANNOT RUN; pinned by the case at `:600-606`). This is the repo's
recorded *a second implementation of one rule drifts*, arriving in the falsifier rather than the code.

**(c) Both falsifiers pass on a document the old parser genuinely misreads.** `_scalarise` splits
flow mappings on `,` (`:302-311`), so a comma inside a quoted value silently truncates the field:

```
$ python3 .../m4.py
B) component value contains a comma
  parsed   : ... 'component': 'check-docs', ...        # source said "check-docs, check-backlog"
  falsifier2 markers-in-span=1  len(findings)=1  -> PASS
  verdict  : ('STOP', 'converged — 1 round(s) with no Blocking/High ...')
```

Parity passes, the verdict is unchanged, and the conversion writes the **truncated** component into
the new substrate permanently. `component` is the thrashing axis, so a truncation that is inert today
can arm or disarm `ARCHITECTURE_REVIEW` in a later round. Neither falsifier looks *inside* a finding's
values, which is where the parser's remaining misreads live.
⚠ Honest bound: **0 live instances of this shape in the 30** (`m2.py`). This is a hole in the
falsifier, not a live corruption.

**(d) Falsifier 1's discriminating power, measured.** `decide()` collapses the whole record to one of
five strings. Over the corpus it currently produces two:

```
$ python3 .../m6-subjects
8 subjects carry the 30 parseable rounds
  arm-prod-drift-cron ROUND_OWED | decision-card-soundness ARCHITECTURE_REVIEW | fix-src-viewer-escaping ARCHITECTURE_REVIEW
  peer-sites ROUND_OWED | review-decision-procedure ARCHITECTURE_REVIEW | seed-explainer-serve-manifest ARCHITECTURE_REVIEW
  velocity-177 ROUND_OWED | velocity-doc-consistency ROUND_OWED
```

30 documents → 8 comparisons drawn from a 2-value observed range. A misread must flip one of eight
coarse labels to be seen.

**Fix:** the falsifier that actually covers the class is a **field-level diff of the source header
against the converted JSON** — every key and every finding's every field, compared as text. That is
cheap, it is not a second implementation of anybody's rule, and it catches (c). Keep verdict
invariance as a cheap smoke test; drop the parity check or state plainly that it is a regression
guard on an invariant the old parser enforces, not a misread detector.

---

### H1 — High · `roundtrip-evidence` · aim: deliverable · fix_induced: false

**§2's feasibility measurement measures `parse_header`'s return value, not the document. It is a
tautology, and it is blind to exactly the region that makes conversion hard.**

The spec states the method: *"import `check-review-decision`, `parse_header` each document,
`json.dumps`, `json.loads`, compare"*. `parse_header` returns `{round, findings, fixes_nontrivial}`
and nothing else (`:248-251`). Measured against the source text of the same 30 documents:

```
$ python3 .../m5.py
top-level keys PRESENT IN SOURCE headers : {'round': 30, 'fixes_nontrivial': 30, 'subject': 30,
        'halves': 30, 'findings': 30, 'deliverable_code_findings': 1, 'deliverable_findings': 4,
        'stopping_rule': 4}
top-level keys RETURNED by parse_header  : {'round': 30, 'findings': 30, 'fixes_nontrivial': 30}
=> discarded by the object the round-trip measured: ['deliverable_code_findings',
   'deliverable_findings', 'halves', 'stopping_rule', 'subject']
round-trip of parse_header OUTPUT: 30 docs, 0 failures  (types present: ['bool', 'int', 'list'])
```

A dict of `int`/`bool`/`list`-of-`str`-and-`bool` **cannot** fail `json.dumps`/`json.loads`. "30
round-tripped cleanly, 0 failures" measures Python's stdlib, not the corpus.

Two consequences beyond the rhetoric:

1. **Three top-level keys the spec never mentions exist in the live record** —
   `deliverable_findings` (4 documents), `stopping_rule` (4), `deliverable_code_findings` (1). §3
   enumerates only `subject` and `halves` as carried through. A converter written to §3 drops them.
2. The claims *"headers with a YAML comment: 0"* and *"headers with a block scalar: 0"* were produced
   by the same blind method. One of them is false — see **H2**.

**Fix:** re-measure over the **raw header text** of each document, enumerate every top-level key
found, and state the conversion rule for each.

---

### H2 — High · `roundtrip-evidence` · aim: deliverable · fix_induced: false

**"headers with a YAML comment: 0" is false. One exists, and JSON cannot carry it.**

```
$ python3 .../m3.py
===  seed-explainer-serve-manifest-r2-coordinator.md
   6:   codex: standin-by-claude   # round 1's Codex half timed out; see that round's REVIEW GAP
```

`docs/reviews/coordinator/seed-explainer-serve-manifest-r2-coordinator.md:9`. JSON has no comment
syntax, so a mechanical conversion **silently deletes the only record of why that round's Codex half
was a stand-in** — a REVIEW GAP explanation, which is precisely the kind of evidence
`check-review-rounds.py` exists to make non-silent. The spec's §2 asserts *"nothing in the corpus
uses a YAML feature JSON lacks, and the conversion is mechanical."* Measured, that is wrong for one
document, and it is wrong inside `halves` — the region H1 shows the measurement never looked at.

⚠ **The block-scalar count (0) I re-derived and it reproduces.** The comment count does not.

**Fix:** state where comment text goes (a `note` field, or prose below the header), and re-run the
feature scan over raw text.

---

### H3 — High · `scope-entanglement` · aim: deliverable · fix_induced: false

**#187 (`disposition`'s vocabulary) is entangled, not out of scope, and the architecture review that
convened this spec says so explicitly. Landing #117 first forecloses the cheap repair.**

The spec's out-of-scope bullet: *"It does not widen `disposition` — backlog #187. Four out-of-set
values exist in the record ... and will still be refused after this change."* True of the name,
silent about the layer. Measured:

```
$ python3 .../m1.py        # the 42 that do not parse are NOT homogeneous
  100  no ```yaml header block          (39 within the *-r*-coordinator.md population)
    3  disposition out of set: 'refuted' / 'redesigned' / 'retreat'
       ship-src-root-alone-r1/r2/r3-coordinator.md

$ python3 .../m6.py        # widen REQUIRED["disposition"] and nothing else
  RECOVERED: ship-src-root-alone-r1 -> round 1, 10 findings
  RECOVERED: ship-src-root-alone-r2 -> round 2,  9 findings
  RECOVERED: ship-src-root-alone-r3 -> round 3,  7 findings
=> 3 documents are recoverable TODAY by #187 alone, through the reader this spec deletes
```

Those three are a complete, gapless `1..3` sequence — a whole subject. Today #187 is "widen a set".
After this PR it is "widen a set **and hand-convert three YAML documents with no reader**", because
the no-fallback rule means nothing can read them mechanically again.

And the review is explicit: F5's proposed row says the policy call *"must be made before #117's
schema pins the enum"* (`docs/reviews/architecture-review-2026-09-25-decision-family.md:337`). The
spec does not engage that sentence.

**Fix (cheap):** either convert **33** documents, not 30 — deciding the enum in this PR is a
one-constant change — or state in §2 that the three are knowingly stranded and who converts them.

---

### H4 — High · `validate-unfalsified` · aim: instrument · fix_induced: false

**The `_validate` branch the spec relies on as r2's Blocking survivor is pinned by ZERO self-test
cases. Measured by mutation.**

Gut the missing-field refusal (`:277-279`) to `continue` and run the suite:

```
$ python3 .../run_mut.py
--- CONTROL: 61/61 self-test cases passed
--- MUTANT: _validate ignores a MISSING decision field: 61/61 self-test cases passed
```

The case written for it — *"a finding whose severity lost its colon REFUSES"* (`:579-584`) — still
goes green, because its fixture also omits `component`, so the **separate** component check at
`:282-284` raises instead. The case is satisfied by an **ambient reason**; it never exercised the
branch it names.

This is load-bearing for the spec, not just for the script. Under YAML the missing-colon shape was
one way to lose a field; under JSON, `{"id": "H1", "aim": "deliverable"}` is *well-formed*, and this
unfalsified branch becomes the **only** thing between it and a clean read. §1 keeps `_validate`
"unchanged" precisely because it is trusted.

**Fix:** before the swap, add a case per `REQUIRED` key whose fixture is complete **except** that
key, and add a mutation-manifest entry anchored on `:277`.

---

### M1 — Medium · `selftest-retirement` · aim: instrument · fix_induced: false

**"Many of the 61 cases exist only to exercise malformed YAML" and "the count WILL fall" do not
survive counting. Three cases would go RED, not retire.**

```
$ python3 (ast over _self_test)
case( occurrences: 62   (61 cases + the `def case`)
cases in the 'reading the record' section: 16
```

16 of 61 touch the record at all. Classifying those 16 against the spec's own kept-set:

| lose their subject (5) | survive as rules, need a JSON rewrite (8) | **no survivor named — would go RED (3)** |
|---|---|---|
| block-style item parsed; block-style High → ROUND_OWED; empty `- ` item; braces in a GAP string; bullet in a block scalar | round number / findings / booleans / aim parse; no header raises; explicit empty list; out-of-set severity; no component | **header missing `round` raises**; **no `findings` key REFUSES**; the `fixes_nontrivial` presence rule (via B1) |

The third column is B1 observed from the test suite's side. The spec's sizing row invites retiring
this whole area as "cases that lose their subject"; ⚠ **a case that tested a RULE through a malformed
header is not a case that tested the PARSER**, and three of these tested a rule the change does not
implement. If B1 is fixed properly the count plausibly **rises**, which the sizing row forecloses.

Also: *"a finding whose severity lost its colon REFUSES"* must be **rewritten** (a JSON finding with
no `severity` key), not retired — and per H4 it must be rewritten with a fixture that isolates it.

---

### M2 — Medium · `manifest-retirement` · aim: instrument · fix_induced: false

**Two mutation-manifest entries anchor in deleted code, and one of them is r3's Blocking guard — a
defect B1 shows the change reopens. That is not "retired with its subject".**

```
$ python3 (anchors of scripts/mutations/check-review-decision.json vs the deleted region)
  RETIRES-with-subject   an absent findings key stops being refused, so silence r...  lines=[232]
  RETIRES-with-subject   flow mappings are scanned across the whole body again        lines=[216]
  ... 8 others survive
manifest entries anchored ENTIRELY in deleted code: 2 of 10
```

The second is a genuine retirement — flow-mapping scanning ceases to exist. The first is not: the
**rule** (*an absent `findings` key must not read as a clean round*) survives the change and, per B1,
is the rule the change breaks. Retiring its mutation entry removes the only mechanical falsifier for
it. The sanctioned ratchet fall requires the SUBJECT to die; here only the anchor does.

**Fix:** re-anchor that entry onto the new schema check. Sizing row should read "1 retirement, 1
re-anchor", not "entries anchored in deleted code must be retired".

---

### M3 — Medium · `authoring-cost` · aim: deliverable · fix_induced: false

**"14 lines today, 13 as JSON — one line shorter, at the same density" is an apples-to-oranges
comparison produced by the same wrong object as H1. Faithful JSON is 18 lines, +29%.**

The spec's §1 example is `decision-card-soundness-r1` (its `H1 / cost-evidence` finding is that
document's). Measured on it:

```
$ sed -n '/```yaml/,/^```$/p' docs/reviews/coordinator/decision-card-soundness-r1-coordinator.md
  14 non-blank lines: round, fixes_nontrivial, subject, halves:, 2 halves entries, findings:, 7 findings

$ python3 -c "... 1 + 2 scalars + 1 open + 7 findings + 1 close + 1 = 13"
```

**13 is the JSON of `{round, fixes_nontrivial, findings}` — the parsed object, with `subject` and
`halves` dropped.** A faithful JSON rendering of the same header, one finding per line, is **18**.
Rendered and counted over real headers:

```
$ python3 .../render
review-decision-procedure-r7      YAML 10  -> JSON 14
decision-card-soundness-r1        YAML 14  -> JSON 18
velocity-177-r6                   YAML  7  -> JSON 11
$ python3 .../m6.py   (all 30)
YAML non-blank median 11 (7–28)   JSON equivalent median 15 (12–32)
JSON longer in 30/30 documents; equal 0; shorter 0
```

⚠ The spec's own displayed pair is **4 YAML lines vs 8 JSON lines** — it contradicts its own sentence
two lines later.

**This goes to whether #117 is discharged.** #117 asks *"which authoring cost to pay"* and prices
option (1) at *"the hand-writability the header exists to offer"*. The spec's rebuttal —
*"Measured, the residual cost is **quotes**, at one line shorter"* — is the one place it answers
#117's actual question, and the measurement behind it is wrong in sign. The choice may still be
right (the *agent-not-human* argument from `round-header-template.md:3` and `:39` stands on its own
and I checked it). The **price** must be restated: `+4 lines per header, +29% on a real one`.

---

### M4 — Medium · `prior-art-evidence` · aim: deliverable · fix_induced: false

**The PRIOR ART table's stated evidence does not reproduce, though its conclusion does.**

Spec: *"`check-review-rounds.py` ... Confirmed: it contains no reference to `halves`."*

```
$ grep -c halves scripts/check-review-rounds.py
13
```

All 13 are its own file-existence notion of a "half" (docstring `:2`, `:9-10`, `:30`, `:79`, case
names `:584`, `:615`, `:637`). The **conclusion** — it answers the half question from file existence,
never from this header — is correct and I verified it. But a reader checking the claim runs exactly
that grep and gets 13, and this repository's recorded failure is *a check result is not the claim*.

**Fix:** state the evidence that reproduces — it never opens a round header / never reads the
`halves:` key.

---

### M5 — Medium · `migration-cutover` · aim: deliverable · fix_induced: false

**The no-fallback rule is right as policy and unstated as a transition. "30" is a count taken inside
the corpus it measures.**

The rule ("a migration that leaves the subject alive is not a migration") is sound and I do not
dispute it. What is missing is the cutover:

- **The 30 is already moving.** This very review adds `round-record-substrate-r1-*`; the coordinator
  half will add a YAML header written against the current template. Measured, 4 of the 8 subjects
  carrying the 30 are mid-flight (`ROUND_OWED`), so more YAML headers are owed before this can merge.
  The spec must say *convert at merge time, re-run the count then* — not *convert the 30 measured on
  2026-09-25*.
- **A branch in flight** whose round documents are YAML gets `CANNOT RUN — a round document for
  '<branch>' has no usable header` after this merges (`:653-655`). That is the loud failure the
  design wants, but it is a real cost the spec does not name, and the remedy (convert those too)
  should be stated.
- **The template change is the only thing making the next author emit JSON.** §3 already lands it in
  the same PR; state that as the mechanism, because there is no other.

---

### L1 — Low · `deletion-size` · aim: deliverable · fix_induced: false

**"121 lines" does not reproduce by any measurement I could construct.**

```
$ python3 (ast over scripts/check-review-decision.py)
  parse_header       198-251   54 lines
  _findings_span     287-299   13
  _scalarise         302-311   10
  _block_findings    314-345   32
  TOTAL: 109   (+2 for FINDING_RE at :195 = 111)
  contiguous region 195–345 minus the surviving _validate/REQUIRED/ROUND_REQUIRED block: 118
```

109, 111 or 118 depending on convention; not 121. Immaterial to the decision, material to the habit —
the sizing row reads *"small, and NET NEGATIVE — 121 lines deleted"*, and the net stays negative at
every one of these numbers.

---

### L2 — Low · `defect-inventory` · aim: deliverable · fix_induced: false

**The six-defect table omits the defect #117's own row cites as its second piece of evidence.**

`docs/backlog.md:145` names two: *"r6 M1 — the flow-mapping scan covered the whole YAML body ...;
**r7 L1 — malformed block-scalar text (`claude: |` with nothing indented beneath it) is accepted and
read**"*. Verified in the record:

```
$ sed -n '/```yaml/,/```/p' docs/reviews/coordinator/review-decision-procedure-r7-coordinator.md
  - {id: L1, severity: Low, aim: deliverable, fix_induced: true, component: parse-header, disposition: filed}
```

The spec's table stops at r6. r7 L1 is a **`halves`-parsing** defect — in the field §3 declares
untouched documentation. JSON does dissolve it (a malformed object raises), which strengthens the
spec; leaving it out weakens the inventory and leaves `halves` looking inert when the record shows
the parser stumbled over it.

---

## What I checked and found clean

A clean re-derivation is a fact about the round.

| Claim | How I checked | Result |
|---|---|---|
| "30 currently-parseable round documents" | `parse_header` over the population `rounds_for` actually globs (`docs/reviews/coordinator/*-r*-coordinator.md`) | ✅ **exactly 30**, 72 total |
| "42 do not parse, 39 with no header at all" | same run | ✅ **exactly 42 / 39** |
| "headers with a block scalar: 0" | regex `:\s*[|>]` over the 30 raw headers | ✅ 0 |
| `pyyaml` rejection | `ls requirements.txt pyproject.toml setup.py` → all absent; `import yaml` → `ModuleNotFoundError` | ✅ sound, stdlib-only by construction |
| the `parse_header` name collision is three different functions | `check-anchors.py:80` and `gen-goals-page.py:90` both parse a `> **Anchor:**` opening; different signatures, different returns | ✅ blast radius is one file |
| r1 B1, r2 B, r2 M, r6 M are genuinely **structural** and dissolve under JSON | each shape is inexpressible in JSON (two list syntaxes; `"severity" "High"`; span ambiguity; braces in prose) | ✅ correct classification |
| "it does not change any decision rule" | `scope_for`, `thrashing_component`, `converged`, `sequence_error`, `decide`, `exit_code_for` untouched by the deletion region | ✅ true |
| `--self-test` green and the declared count honest | `python3 scripts/check-review-decision.py --self-test` → `61/61`; docstring `:5` says 61 | ✅ agree |
| the tool still files this against itself | `python3 scripts/check-review-decision.py` on `review-decision-procedure` → `ARCHITECTURE_REVIEW — thrashing: 'parse-header' ... r6 and r7` | ✅ reproduces |
| §1's warning that deleting `_validate` reopens r2's Blocking | `_validate:273-284` is the only value check | ✅ correct — and see **H4** for why it is untested |

⚠ **One self-correction, recorded rather than hidden.** My first pass at M2 read the mutation
manifest with a guessed schema (`anchor`/`find`) — those keys do not exist; entries carry
`edits: [[old, new]]`. The first run therefore reported "0 of 10" over an empty match set. Re-run
against the real schema: **2 of 10**. *A report format is a contract.*

---

## Verdict

**NOT CONVERGED.** B1 and B2 are design defects, not wording: as specified, the change reopens two
of the six defects it cites as motivation, and the controls it pre-commits for its own stated
residual risk cannot fire. H3 is a foreclosure with a three-document cost that is cheap to avoid now
and expensive to avoid later.

**The substrate choice is right.** `json.loads` is the correct answer to #117, the rejections
reproduce, and the *agent-not-human* argument for JSON stands. What must change before the Phase 1
gate:

1. §1 names a **top-level schema check** as built (B1) — which is also F2/#185's seam.
2. §2 replaces the parity falsifier with a **field-level source-to-JSON diff** (B2).
3. §2 re-measures over **raw header text**, enumerating all eight top-level keys (H1, H2).
4. §2 converts **33** documents, or states the three stranded ones and who converts them (H3).
5. §3/Sizing restate the authoring cost as **+4 lines per header**, since that is the answer to the
   question #117 actually asked (M3).
6. Sizing replaces "cases retired with their subject" with the **three cases that would go red** and
   the missing-field cases H4 shows are absent today.
