# Architecture review — `conversion-falsifiers`, backlog #117

> **Anchor:** `review-decides-itself` — **ADR:** none
> **Convened by:** the pre-commitment recorded in
> `docs/superpowers/specs/2026-09-25-round-record-substrate-design.md:569-571` — four falsifier
> designs, four distinct failure modes, one component.
> **Subject:** that spec, at **`4118a592`**, branch `backlog-117-parser-substrate`.
> **Every count in this document is stamped at `4118a592` or replaced by a rule.** The working tree
> was clean and byte-identical to HEAD when these were taken (`git status --porcelain` → empty).

---

## Verdict

**It is the wrong problem.** "Verify that a one-shot migration did not silently alter the record" is
hard, four attempts did miss, and the framing is also wrong — but all three of those are downstream
of a fourth thing, which is that **the migration is not owed.** #117's WORK is *"choose among the
three reshapings, then implement; the decision is which authoring cost to pay"*; it names no corpus.
The corpus question is backlog **#119**, which was decided on 2026-09-15 and decided the other way:
*"WORK: none required if old branches simply drain"*, and — explicitly — *"BACKFILLING WAS CONSIDERED
AND REJECTED BY THE USER … the reason is filed here so it is not re-proposed as an obvious cleanup."*
The spec re-proposed it, under a different name, and then spent three rounds building a falsifier for
it.

**And the thing being preserved is not read.** `rounds_for()` is called from exactly one place with
exactly one argument — `git rev-parse --abbrev-ref HEAD` (`scripts/check-review-decision.py:621,628`).
A round document is therefore decision-relevant **only while a branch whose name is exactly its
`<subject>` is checked out**. At `4118a592`, **4 of the 32** parseable coordinator documents satisfy
that; **28 do not**, and the tool can never be invoked with their subject again. The branch under
review demonstrates the rule from the other side: it is named `backlog-117-parser-substrate`, its
records are `round-record-substrate-r*`, and `rounds_for("backlog-117-parser-substrate")` returns
**0 rounds** — the spec is designing a lossless migration of a record the tool cannot currently read
on the branch that is writing it.

**Can a redesign remove it?** Yes, in one sentence: **stop making the machine the author.** All four
designs failed because the conversion is machine-authored, which leaves only a human to check it, and
a human checking a serialisation by eye has no omission signal (design 4) — while any machine checker
available is the broken parser itself (designs 1–3). Swap the roles: **a human writes the JSON header
(an independent second reading of the source text), and a machine asserts that the old reader's
decision-bearing projection equals the new one's.** Both readers stay independent, and both do the
job they are good at. Prototyped and run below: it catches an altered value, a dropped finding, **and
an omitted key** — the class design 4 was blind to. It needs no converter, therefore no ratchet
obligation, no `migrate-round-headers.py`, and no human-read artifact.

Combined with the first paragraph, the work shrinks from *"convert 32 documents with a script plus a
falsifier for the script"* to **"hand-write ≤4 headers on the branches that need them, checked by a
20-line comparator."**

---

## Findings, ordered by consequence

### F1 — Blocking · **structural** · The migration is not required by #117, and #119 already decided the corpus question the other way

**Evidence — #117's own WORK clause**, quoted from `docs/backlog.md:145`:

> **WORK:** choose among the three reshapings, then implement; the decision is which authoring cost
> to pay, not whether the parser is wrong.

The three reshapings it names are (1) a fenced `json` block, (2) vendor a YAML-subset parser,
(3) drop the header and pass counts on the command line. **None of them names the existing corpus.**
Only (3) would force a corpus decision, and it is the one the spec rejects.

**Evidence — #119 (`docs/backlog.md:147`)** is the row that *does* own the corpus, and it is already
decided:

> ⛔ **BACKFILLING WAS CONSIDERED AND REJECTED BY THE USER, 2026-09-15** — writing machine-readable
> claims into a review record after the fact, reconstructed rather than recorded, manufactures
> evidence about review coverage; the reason is filed here so it is not re-proposed as an obvious
> cleanup. … **WORK:** none required if old branches simply drain.

A machine conversion is not literally a backfill — the claims were recorded. But the spec states at
`:244-245` that **"The converter reads through the BROKEN parser"**, so what it writes is *the
parser's reading*, not the author's claim. Measured, that reading is lossy in a way that is silent
and total:

```
$ python3 - <<'PY'   # parse_header on a component containing a comma
  - {id: H1, ..., component: "check-docs, check-backlog", disposition: fixed}
PY
component as read: 'check-docs'
stray key from the split: []
```

`_scalarise` splits on `,` (`:302-311`) and discards the remainder entirely — no stray key, no
signal. A conversion writes `"component": "check-docs"` into the record permanently. That is a
machine-readable claim about review coverage, reconstructed rather than recorded, which is the
sentence #119 forbids.

**Consequence:** the whole `conversion-falsifiers` component — four designs, three rounds, one
convened architecture review — exists to make safe an operation that no open row asks for and one
open row rules out.

---

### F2 — Blocking · **structural** · The tool reads only the current branch's subject, so 28 of the 32 documents have no reader to preserve

**Evidence — the rule, from the code, not from a count.** `main()` derives the subject from the
branch and calls `rounds_for` once:

```
scripts/check-review-decision.py:621   branch = _git("rev-parse", "--abbrev-ref", "HEAD")
scripts/check-review-decision.py:628   rounds = rounds_for(branch)
scripts/check-review-decision.py:356   for f in sorted(d.glob(f"{subject}-r*-coordinator.md")):
```

and it is the **only** reader of the header. Measured at `4118a592`:

```
$ grep -rn 'reviews/coordinator\|"coordinator"' scripts/*.py .claude/hooks/*.sh \
    | grep -v '^scripts/check-review-decision.py'
scripts/check-review-rounds.py:471:HALF_DIRS = ("codex", "claude", "coordinator")
scripts/explainer-serve.py:247:   # …comment citing a coordinator document
scripts/explainer-serve.py:2237:  # …comment citing a coordinator document
scripts/codex-review.py:416:      # …docstring describing the filing layout
```

⚠ **Three hits, not zero — stated as measured rather than as the clean result the claim wanted.**
None of them opens a header: `HALF_DIRS` is a directory tuple used for **filename** discovery, and
the other three are comments. `check-review-rounds.py` answers the halves question from filenames
(`:75-76`) and a prose `REVIEW GAP:` line (`:87`), never from the header block. The claim that
`parse_header` is the header's only reader survives; the evidence is the absence of any *read*, not
the absence of any *mention*.

```
$ grep -rn "calibrate" scripts/ docs/      # the spec's proposed --calibrate
(no hit in either script — confirming r3 Codex's High)
```

**Measured at `4118a592`** (subject == an existing local-or-remote branch name):

| population | count |
|---|---|
| coordinator round-shaped files | 74 |
| distinct subjects | 19 |
| parseable by `parse_header` | **32** |
| parseable **and** subject names a live branch | **4** — `arm-prod-drift-cron` r1–r2, `decision-card-soundness` r1–r2 |
| parseable, no live branch of that name | **28** |

⚠ **The 4/28 split is transitional; the rule behind it is structural.** Branch existence moves.
What does not move is that `rounds_for` is only ever called with the checked-out branch's name, so a
document whose subject will not again name a checked-out branch is unreachable by construction.
Converting it preserves decidability for a call that cannot occur.

---

### F3 — Blocking · **structural** · All four falsifier failures have one root: the machine authors, so the human must check

This is the question the review was convened to answer, and the four failures are not four
independent misses. Each design had to pick a **second reader** to check the machine's output, and
only two were available:

| # | second reader | why it failed | the shared cause |
|---|---|---|---|
| 1 | the parser (`parse_header:235-236` parity) | could not fire | the checker **is** the author |
| 2 | a field-level differ | could not be built — telling one field from two needs a YAML parser | the checker would **have to become** the author |
| 3 | a human, reading the parser's rendering of the source | audited itself | the checker was handed the author's reading |
| 4 | a human, reading **raw** source vs a partial render | no signal for an omission | the checker is independent but given an **unaligned** task |

Designs 1–3 are one mistake (correlated readers). Design 4 broke the correlation and hit the real
wall: a human comparing *whole raw text* on the left against *only the fields the converter produced*
on the right has no key set on the right to notice a missing key. The r3 Codex half named this
exactly (`docs/reviews/codex/round-record-substrate-r3-codex.md`, Blocking 1):
*"unaided whole-header audit."*

**The invariant across all four is the division of labour, not the check.** The machine was given the
job it is bad at (reading YAML) and the human the job they are bad at (spotting an absence in a wall
of text). **Swap them** and both failures dissolve — see *The redesign* below, which was built and
run.

---

### F4 — High · **structural** · The spec asserts seven obligations; exactly one has a mechanism. The ratchet case is a pattern, not a one-off

The lead asked specifically whether the unenforceable-ratchet claim is isolated. It is not. Each row
below was checked for an enforcing mechanism:

| # | obligation (spec line) | mechanism? | evidence |
|---|---|---|---|
| 1 | the converter "owes the full ratchet" (`:290`) | ⛔ **none** | `GUARD_PATH_RE = scripts/check-[\w.-]+\.py` with `fullmatch` (`check-ratchet-contract.py:113,164`); run: `migrate-round-headers.py → False` |
| 2 | "An unknown key is preserved, never dropped — the converter refuses rather than discards" (`:152-153`) | ⛔ **none** | the only check is the human table, which r3 proved blind to omission — the rule with no mechanism is the rule the falsifier cannot see |
| 3 | "the PR states **who** read all of them at **which commit**" (`:316`) | ⛔ **none** | no gate in `scripts/` validates such an attestation, and the spec names none |
| 4 | "The parity check is DROPPED and **must not reappear**" (`:324`) | ⛔ **none** | prose only |
| 5 | "**No test may assert a count** over `docs/reviews/coordinator/`" (`:489`) | ⛔ **none** | `check-selftest-counts.py` compares declared-vs-actual, a different rule |
| 6 | "A fallback YAML reader appears in a later commit → #117 was postponed" (`:434`) | ⛔ **none** | a "how we would know it failed" line with no observer |
| 7 | `check-review-rounds.py` gains a CI refusal (`:348-350`) | ✅ **yes** | it runs in CI — `.github/workflows/ci.yml:203` |

**Six of seven rest on discipline**, in a document whose own subject is that a rule stated where it
cannot be enforced is the drift this family exists to remove (`check-review-decision.py:260-262`).
`docs/dev-process.md` states the repo's own remedy: *"Before adding a rule here, ask whether it can
be a script."* The spec's answer to a defect has repeatedly been a sentence.

⚠ **The six split into two kinds, and only one kind is the converter's.** Rows 1–3 exist *because*
there is a converter and disappear with it (F1/F3). Rows 4–6 are a different shape — **"never do X
again" rules**, each recording a decision the next draft is asked to remember. Those do not
disappear with the converter, and they are the more interesting half: a prohibition with no observer
is how this document's own §2 reintroduced a parity check it had already dropped, and how *"one line
shorter"* survived two sweeps. The remedy for that kind is not a script per rule; it is the one
`check-docs.py` already implements for the spine — **grep for the OLD value, not the new one**,
which §"the sweep that r2 forced" names at `:549` and does not apply to itself.

---

### F5 — High · **structural** · The CI refusal as specified re-creates #56's unsatisfiable gate, and that is what forced an unrelated enum decision into this PR

The spec's cutover (`:348-350`) refuses any coordinator document still carrying a `yaml` header. Its
population is the whole directory, so every historical document is red until converted — which is
what made `disposition` (#187) a blocker (`:401-420`), because three `ship-src-root-alone` documents
cannot be converted while the enum is narrow. The spec resolves this by widening
`REQUIRED["disposition"]` **in this PR**, and records the reasoning as a Blocking (r2 Claude B4).

**The trade was forced by the gate's population, not by the substrate.** Key the refusal on the
**diff** — a coordinator document *added or modified in this PR* carrying a `yaml` header fails —
and the historical corpus is never in scope, nothing is permanently red, and #187 decouples entirely.

Measured, `disposition` is also the wrong field to be blocked on:

```
$ python3 - # AST scan of which header fields the decision rules actually read
thrashing_component    ['component', 'findings', 'fix_induced']
converged              ['aim', 'findings', 'fixes_nontrivial', 'round', 'severity']
sequence_error         ['round']
decide                 ['round']
$ grep -n disposition scripts/check-review-decision.py
:269  "disposition": {"fixed", "filed", "declined"},     # …and nowhere else outside self-test fixtures
```

**`disposition` is validated and consumed by nothing.** It is the only field that can make a document
unreadable without affecting any verdict. Widening it is right (#187 is a real row), but it is not
#117's decision and does not belong in #117's PR.

---

### F6 — High · **structural** · The escalation that convened this review is unreachable by the tool that is supposed to arm it

The pre-commitment fired because a human maintained a table in the spec. Run against the record:

```
$ rounds_for("backlog-117-parser-substrate")   -> 0 rounds
  decide(...)                                  -> ROUND_OWED  "no round recorded"
$ rounds_for("round-record-substrate")         -> 2 rounds
  thrashing_component(...)                     -> None
  decide(...)                                  -> ROUND_OWED  "r1 produced a Blocking"
$ decide(r1,r2 + a recorded r3 with the r3 Codex half's own labels)
  -> ARCHITECTURE_REVIEW  "thrashing: 'conversion-falsifiers' carried fix-induced findings in r2 and r3"
```

**The model is adequate; the reachability is not.** The rule would arm correctly at r3 — but only
under a subject that equals the branch name, and this branch's does not. Nothing checks that
coupling, and the failure is silent: an unnameable subject yields `0 rounds → ROUND_OWED`, which
reads as *you owe a round* rather than *I cannot see your record*. The over-review direction is the
safe one, but **the `ARCHITECTURE_REVIEW` escalation is lost entirely**, and it is lost on the branch
whose escalation this document is.

⚠ This also refutes, in one instance, #185's framing that *"the rule half carries zero recorded
fail-opens"* — this one is in `rounds_for`/`main`, not in `parse_header`, and it survives every
substrate change #117 could make.

---

### F7 — Medium · **structural** · The layer model is sound and closed; the accretion is in how it was derived

Presence / syntax / schema / values is not a per-round accretion of the same kind #117 diagnoses. It
is the complete failure set of deserialising a record — *is it there, is it well-formed, is it the
right shape, are the values legal* — and there is no fifth. Each layer maps to a distinct recorded
defect, and layer 1 is owned by `json.loads`, i.e. outside the code being written.

**What is true is that it took three rounds to reach a standard four-way split**, because the design
was being derived from review findings rather than from the question *"what are the ways reading a
serialised record fails?"* asked once, up front. That is a process observation, not a design defect.

**One real defect inside it:** the sizing table calls the reader swap *"small, and net negative"*
(`:442`) while layers 0, 2 and 3 are all new hand-written code that the spec never sizes. Deleting
109 lines of tokeniser and adding an unsized hand-rolled schema validator is not measured to be net
negative. Grade the claim as unsupported, not wrong.

---

### F8 — Medium · **transitional** · The converter is a second hand-rolled YAML parser, strictly larger than the one being deleted

`parse_header` returns three keys; the header carries more:

```
$ python3 -  # on docs/reviews/coordinator/round-record-substrate-r2-coordinator.md
keys parse_header returns:        ['findings', 'fixes_nontrivial', 'round']
top-level keys IN the document:   ['findings', 'fixes_nontrivial', 'halves', 'round', 'subject']
keys the parser drops:            ['halves', 'subject']
```

The spec requires the converter to *"read the DOCUMENT (nine keys, one inline comment)"* (`:443`), so
it cannot be a re-emission of `parse_header`'s output — it must implement its own YAML reading over a
**larger** surface than the parser being deleted (nine top-level keys plus comment preservation
versus three keys). **#117's verdict applies to it by its own terms**, and "never in the decision
path" is the only thing separating them — which F4 row 1 measured to be unenforceable.

It is also worse-placed than the parser it replaces: `parse_header` misreads at *decision* time and
is repairable by fixing the parser; the converter misreads **once** and writes the misreading into
the record, where it is indistinguishable from testimony.

⚠ Marked transitional because it disappears with the converter, not because the reasoning is
contingent.

---

### F9 — Low · **structural** · Six of the nine top-level keys are read by nothing

Measured over all 35 `yaml` headers at `4118a592`:

```
{'round': 35, 'fixes_nontrivial': 35, 'subject': 35, 'halves': 35, 'findings': 35,
 'deliverable_findings': 5, 'stopping_rule': 5, 'architecture_review': 1, 'deliverable_code_findings': 1}
headers with any '#':  1   (seed-explainer-serve-manifest-r2-coordinator.md)
```

`subject`, `halves`, `architecture_review`, `deliverable_findings`, `deliverable_code_findings` and
`stopping_rule` are read by no code — `check-review-rounds.py` answers the halves question from
filenames and a `REVIEW GAP:` prose line. They are prose wearing a key's clothes.

**This dissolves the spec's hardest carry-through obligation.** If the JSON header carries *exactly*
the schema and everything else moves to prose below it, there is no "nine keys" problem, no "unknown
key preserved" rule to enforce (F4 row 2), and no comment-preservation decision. The spec's §3 already
concedes these are documentation; it then obliges the converter to carry them anyway.

---

## Can a redesign remove it? — yes, and here it is

**The redesign: the human authors, the machine checks.**

1. **No converter.** `scripts/migrate-round-headers.py` is not written. F4's rows 1–6 evaporate with
   it, as does F8.
2. **Convert nothing historical.** Documents that predate the cutover keep their `yaml` header and
   become `CANNOT_RUN` — which is exactly the state 10 of 19 subjects are in today and which #119
   calls *"the gate working"*. No `--fallback`, no second reader: after the cutover there is no YAML
   reading code at all, which discharges #117 **more** completely than conversion does.
3. **A branch that needs decidability converts its own rounds, by hand, in its own PR.** At
   `4118a592` that is 4 documents across 2 subjects. The reviewer of that PR reads a `git diff` —
   the mechanism this repository already trusts for every other change — instead of a bespoke
   human-read artifact with an attestation nothing validates.
4. **The falsifier is a projection comparison, and it is buildable.** Derive the consumed field set
   from the rules, project both readings, compare:

```python
CONSUMED = ("severity", "aim", "fix_induced", "component")     # from the AST scan in F5
def projection(head):
    return {"round": head["round"], "fixes_nontrivial": head["fixes_nontrivial"],
            "findings": [{k: f.get(k, "<ABSENT>") for k in CONSUMED} for f in head["findings"]]}
# assert projection(parse_header(yaml_source)) == projection(json.loads(new_header))
```

**Run at `4118a592` against `decision-card-soundness-r1-coordinator.md` (7 findings):**

```
A. correct conversion    -> AGREE
B. a key omitted         -> DISAGREE (caught)
C. a value altered       -> DISAGREE (caught)
D. a finding dropped     -> DISAGREE (caught)
```

**Why this is not design 1 wearing a hat.** Design 1 compared the parser to itself. Here the two
readings have **independent authors** — a human reading the raw source, and `parse_header` reading
the same bytes — so a disagreement means *either* a transcription slip *or* a parser misread, and
both require a human look. The comma-truncation case (F1) surfaces as a disagreement rather than
being written in silently. Omission surfaces because both sides are complete mappings with comparable
key sets, which is precisely what design 4 lacked.

⚠ **Stated honestly — the residual, and the one thing this does not do.** If the human reproduces the
parser's misreading, the check passes. That requires a person to replicate a regex bug while reading
plain text; the failure modes are uncorrelated, unlike designs 1–3 where they were identical by
construction. And this compares only the **decision-bearing** projection: a difference in `id`,
`disposition` or a prose key is not caught. Under item 2 above that is correct rather than a gap —
those fields drive no verdict (F5, F9) and the source document is untouched in git, so nothing is
lost that could be lost.

**The cutover gate, corrected (F5):** `check-review-rounds.py` refuses a coordinator document
**added or modified in this PR** that carries a `yaml` header, keyed on the `<subject>-r<N>-coordinator.md`
filename grammar. Diff-scoped, so the historical corpus is never red and #56's outcome cannot occur.

---

## Recommendation

> ### **NARROW, and REPLACE the falsifier approach.**

Not *park* — the substrate choice (§1, layers 0–3) is sound, survived three rounds, and discharges
#117 on its own. Not *proceed as specified* — §2 is work that no row asks for, guarded by six
obligations nothing enforces and a check that four designs could not build.

**Keep:** §1 in full (the four layers, the `_validate` retyping, the `isinstance(True, int)` trap,
layer 0). §3 (the template moves with the mechanism). The diff-scoped CI refusal.

**Cut:** §2's converter, the human-read artifact and its attestation, the `--calibrate` proposal, the
nine-key carry-through, the comment-preservation decision, and the in-PR `disposition` widening.

**Add:** the projection comparator (≈20 lines, in `check-review-decision.py`'s `--self-test` against
a committed fixture pair — an invariant, not an observation, so it satisfies the spec's own
*"what the tests may and may not assert"* rule).

**One honest caveat for the human gate.** This recommendation accepts that the parseable historical
record becomes undecidable at cutover. That is a real loss and it is chosen, not overlooked: #119
already decided this corpus drains rather than gets reconstructed, and F2 measures that 28 of the 32
documents have no reachable caller. If the user wants the history machine-readable, that is a
*different* goal from #117 and should be a row of its own — where "a human writes them, a machine
checks the projection" is still the right mechanism, only applied 32 times instead of 4.

---

## Proposed backlog rows

> **#189** 🟠 **`check-review-decision.py` can only see a subject whose name equals the checked-out
> branch, and nothing enforces that coupling — so `ARCHITECTURE_REVIEW` is silently unreachable
> whenever they differ** — filed 2026-09-25, architecture review F6 (structural). ⛔ **MEASURED at
> `4118a592` ON THIS REPOSITORY'S OWN BRANCH:** `main()` calls `rounds_for(git rev-parse
> --abbrev-ref HEAD)` (`:621`, `:628`); the branch is `backlog-117-parser-substrate`, its records are
> `round-record-substrate-r*-coordinator.md`, and `rounds_for` returns **0 rounds** → `ROUND_OWED
> "no round recorded"`. With the records reachable and an r3 recorded, the same rule returns
> `ARCHITECTURE_REVIEW — thrashing: 'conversion-falsifiers' carried fix-induced findings in r2 and
> r3`. ⭐ **THE MODEL IS FINE; THE REACHABILITY IS NOT** — and the failure is silent in the one
> direction that matters: a missing record reads as *no round yet*, not as *I cannot see your
> record*. ⚠ This is a fail-open in the RULE half, which #185 states carries none. **WORK:** either
> refuse when a branch has no matching subject but a `subject:` is recorded elsewhere, or take the
> subject from the record rather than the branch. **FALSIFIER:** a branch whose round documents exist
> under a different subject still gets a verdict instead of a refusal. | `scripts/check-review-decision.py`
> (`rounds_for`, `main`) | S | (tooling) | pending

> **#190** 🟡 **The round header carries six top-level keys that no code reads, and one of them
> (`disposition`) can make a document permanently unreadable without affecting any verdict** — filed
> 2026-09-25, architecture review F5/F9 (structural). **MEASURED at `4118a592`** over 35 `yaml`
> headers: `subject`, `halves`, `architecture_review`, `deliverable_findings`,
> `deliverable_code_findings`, `stopping_rule` have **no reader** — `check-review-rounds.py` answers
> the halves question from filenames (`:75-76`) and a `REVIEW GAP:` prose line (`:87`). An AST scan of
> the decision rules shows they consume exactly `round`, `fixes_nontrivial`, and per finding
> `severity`/`aim`/`fix_induced`/`component`; `disposition` appears only in `REQUIRED` (`:269`) and
> gates parseability for **3** documents (`ship-src-root-alone` r1–r3) that no verdict depends on.
> **WORK:** decide whether the header is a schema or a document. If a schema, the unread keys move to
> prose below it and the header shrinks to what `decide()` reads. ⛔ **Do not bundle with #117** —
> #187 already owns the enum. **FALSIFIER:** a key in the header schema that no code path reads. |
> `docs/round-header-template.md`, `scripts/check-review-decision.py` | S | (tooling) | pending

---

## What we decided this milestone that is not written down

The spec's `THRASHING WATCH` table (`:554-592`) tracks four **design attempts** — `spec`, `r1 fold`,
`r2 fold`, `r3 fold`. Two of those are not rounds: the spec-stage design and the folds between rounds
have no round number, and the header's model is `round × component × fix_induced`. The escalation
this review exists for was therefore tracked **by hand, in prose, in the spec** — correctly, and
outside every mechanism in the family. That the hand-maintained table worked and the tool could not
see it is the most load-bearing thing this branch learned, and it appears nowhere but here.
