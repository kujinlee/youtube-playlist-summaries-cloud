<!-- claude-review: round=7 writer=claude subject=plugins-handoff-citations head=e3d393d8 -->

NOT CONVERGED — 0 Blocking, 1 High, 5 Medium, 1 Low.

Every finding below is **"complete the decision"**, not **"reopen it"**. Nothing I ran argues against
the one-canonical-source redesign; three of the seven findings are *that the fold did not finish it*,
three are *a stated bound or premise that is false*, and one is a readability residue. I agree with the
Codex half's qualification, and H1 is the strongest evidence for it that exists on this branch.

## Blocking

None found.

## High

### H1 — #289's `FAILS IF` is TRUE at HEAD. The fold recorded it FALSE, and the surviving site is in the document the fold edited to explain the defect.

`docs/backlog.md:279` records #289's falsifier as *"a non-exempt live site describes a mechanism a
`CANONS` entry owns, disagrees with that canon, and `check-canonical-source.py` exits 0"*, and then
states: *"⚠ Checked against HEAD when written … currently **FALSE** — the three known sites were
collapsed to citations in the r7 fold, and a folded search finds no surviving live site making the
unconditional claim."*

A fourth site survives, and it is the one the same commit added a section to.

| site | wording at HEAD |
|---|---|
| `.agents/skills/handoff/SKILL.md:13` | "the delivery fingerprint, each with **the bound it actually has**" |
| `.claude/hooks/enforce-handoff-path.sh:66-67` | "the delivery fingerprint, each with **its real bound**" |
| `docs/plugins.md:82` | "the fingerprint and **each one's real bound**" |
| ⛔ `docs/process-rationale.md:356` | "the symbol, the emission banner, the injection order and **the content fingerprint**" |

`docs/process-rationale.md` is a **declared citing site** for `handoff-path`
(`scripts/check-canonical-source.py:141`), is not exempt (`EXEMPT` at `:180` is
`^(docs/reviews/|docs/dashboard-entries\.md$)`), and carries live mechanism tokens
(`REMEMBER_HANDOFF` ×2, `=== LAST HANDOFF ===` ×1 — derived below). The canon says the fingerprint is
`cksum` of the content ***where `cksum` exists***, falling back to `wc -c`, a byte count
(`.agents/skills/shared/handoff-path.md:35-44`). `:356` says "the content fingerprint", unqualified —
the exact word L9 refuted — and the author's own repair wording ("its real bound") was applied to the
three siblings in this commit and not to this one.

**Nine lines below it, the same file explains why that is wrong:** `docs/process-rationale.md:365-369`
— *"Round 6's L9 corrected the delivery fingerprint … **Three reader-facing sites kept the
unconditional form for a full round**"*. So the document prints the unconditional claim and its own
withdrawal, in one screen. That is verbatim the defect the canon (`handoff-path.md:7-8`) and the guard
(`scripts/check-canonical-source.py:11-13`) both name as the thing that settled the redesign.

**Verified by running, with a known positive first.** The guard exits 0 over this
(`python3 scripts/check-canonical-source.py` → `canonical sources OK — 2 mechanism(s) described once
each`, rc=0), as #289 predicts it would. The search was **mine** — whitespace-folded and
case-insensitive, written inline; I used neither `find-claim.py` (see M5, and **Instruments** for why
that name cannot be cited bare) — and the canon itself was asserted as the known
positive (3 matches) before any negative was trusted. Live non-exempt population: 19 files mention
`fingerprint`; of those, the handoff-mechanism sites are the four above plus
`scripts/check-canonical-source.py` (its own docstring, correctly qualified).

**Which it is:** *complete the decision.* The remedy is the one the other three sites took — one word.
It does not implicate the guard, the canon, or the redesign. What it does implicate is the fold's
**verification claim**: a search that missed a site inside a file the commit was editing is the same
"measured the wrong set" shape the parent commits keep finding.

## Medium

### M1 — Docstring bound 2 is false in its count, its sever, and its instruction to future editors. Measured three ways.

`scripts/check-canonical-source.py:66-70` states:

> 2. THIS FILE CARRIES EVERY TOKEN OF EVERY CANON … So this guard must itself cite every canon it
>    declares, and `shared/corpus-search.md` is cited exactly ONCE here. **Deleting that one citation
>    reddens the guard against ITSELF** … Anyone adding a third canon must add its citation here in
>    the same edit.

The same claim is in the fold's commit message. All three clauses are wrong:

1. **"cited exactly ONCE"** — `shared/corpus-search.md` occurs **twice**: `:68` (this docstring
   sentence) and `:147` (`CANONS[1]["file"] = ".agents/skills/shared/corpus-search.md"`).

2. **"Deleting that one citation reddens the guard against ITSELF"** — it does not.
   Green control, then the sever, then green again:

   ```
   === CONTROL ===  canonical sources OK — 2 mechanism(s) described once each   rc=0
   sever: replaced the literal `shared/corpus-search.md` at :68 with "that canon"
   === AFTER ===    canonical sources OK — 2 mechanism(s) described once each   rc=0
   ```
   *Placement:* the only textual edit was inside the module docstring, line 68, the sentence quoted
   above; `CANONS` was untouched. The guard stays green because `_cites()` expands leftwards over path
   characters and resolves the candidate (`:211-231`), so the `CANONS` entry's own `"file"` **value**
   satisfies the citation requirement.

3. **"Anyone adding a third canon must add its citation here in the same edit"** — refuted by
   construction. On a copy, green control, I added a third `CANONS` entry
   (`{"name": "zz-third", "file": ".agents/skills/shared/zz-third.md", "tokens":
   ["ZZTOKEN_UNIQUE_XYZ"], "cites": []}`, inserted immediately before the `"name": "corpus-search"`
   entry) plus the canon file, and **no** prose citation anywhere:

   ```
   canonical sources OK — 3 mechanism(s) described once each (handoff-path, zz-third, corpus-search)
   rc=0      occurrences of "shared/zz-third.md" in the guard: 1   (the CANONS value alone)
   ```

The guard's actual behaviour is *better* than the docstring claims — self-citation is automatic and
cannot be lost by editing prose. The defect is the stated bound, which this repo has measured as worse
than no bound: it tells a future editor that a prose line is load-bearing when it is inert, and its
sever — the only falsifier offered for the self-reference property — passes.

**Which it is:** *complete the decision.* Replace the sentence with what is true: a canon declares its
own citation through `CANONS[i]["file"]`, so the self-reference is structural.

### M2 — Docstring bound 1's numbers are the PARENT tree's. The commit that wrote them changed them.

`scripts/check-canonical-source.py:62-65`:

> 1. TOKENS MATCH AS SUBSTRINGS … Measured: LATENT, not live — every site carrying the string has at
>    least one bare occurrence **(7 sites, bare counts 1-3)** …

Re-derived by importing the guard's own `_walked_textfiles` and `EXEMPT` (never a re-implementation),
counting `REMEMBER_HANDOFF` and the bare form `REMEMBER_HANDOFF(?!_)` over the live, non-exempt,
non-canon population:

| commit | live sites | bare counts |
|---|---|---|
| `5d09c1be` (parent) | **7** | **1–3** |
| `e3d393d8` (HEAD, the commit that wrote the sentence) | **5** | **1–4** |

HEAD: `.agents/skills/handoff/SKILL.md` (1), `docs/memory/a-vendored-line-number-has-no-owner.md` (1),
`docs/process-rationale.md` (1), `scripts/check-canonical-source.py` (4), `scripts/check-handoff-path.py` (1).
The two that left are `.claude/hooks/enforce-handoff-path.sh` and `docs/plugins.md` — both because
*this commit deleted their recitals*, and `scripts/check-canonical-source.py` rose to 4 bare because
*this commit added the sentence making the claim*.

The **verdict** LATENT still holds, and I verified it independently: all five sites have ≥1 bare
occurrence, so none is required to cite solely because of a `_STATE` match. Only the figures are
stale — and they were stale at commit time, by the commit's own diff.

**Which it is:** *complete the decision.* But note the shape, because it is the branch's class and not
an accident: a measured number was taken before the edit and written after it, in a file inside the
population it measures.

### M3 — A FOURTH cited recital the fold did not count, at a declared citing site, whose own next line claims it is gone.

`scripts/check-handoff-path.py:41-44`:

```
# The path the remember plugin's SessionStart hook actually reads:
#   session-start-hook.sh   REMEMBER_HANDOFF="$REMEMBER_DIR/remember.md"
# Verified by EXECUTING that hook, not by reading it — the `=== LAST HANDOFF ===` block came out
# first, ahead of `=== REMEMBER ===` and `=== MEMORY ===`.
```

Those are three of the four clauses the fold deleted from its three siblings: the symbol assignment,
the banner, the injection order. Two independent problems:

**(a) The comment block contradicts itself two lines later.** `:46` reads *"⟳ 2026-10-14 — WHAT STOOD
HERE IS NOW IN ONE PLACE, AND THIS COMMENT CITES IT."* The recital it says moved is still standing
immediately above the sentence saying it moved. The citation at `:52-53` is present, so
`check-canonical-source.py` is green — the #289 permissiveness, at a site nobody counted.

**(b) The quoted assignment is the `else` branch of two, presented unconditionally.** Measured against
the installed hook named by the canon's own discovery command:

```
$ ls ~/.claude/plugins/cache/claude-plugins-official/remember/*/scripts/session-start-hook.sh
   …/remember/0.33.0/scripts/session-start-hook.sh        (2027 lines)
$ grep -n 'REMEMBER_HANDOFF=' …
1168:    REMEMBER_HANDOFF="$REMEMBER_DIR/remember.${CURRENT_SESSION_ID}.md"
1171:    REMEMBER_HANDOFF="$REMEMBER_DIR/remember.md"
```

`:1167-1176` is `if [ "$HANDOFF_MODE" = "per_session" ] && [ -n "$CURRENT_SESSION_ID" ]` → `:1168`,
`else` → `:1171`. The canon states this correctly ("there are **TWO** assignments — the per-session
path, then the shared one", `handoff-path.md:18-20`, and the hint rule at `:58`). `check-handoff-path.py:41`
says "The path the remember plugin's SessionStart hook **actually reads**" and names one. Under
`handoff_mode: per_session` that is false.

The script's **code** is right (`CONSUMED_PATH` at `:71` is the correct rule for SKILL.md, because the
runtime hint overrides it). Only the comment restates, and only the comment is wrong.

**Which it is:** *complete the decision.* This is the single sharpest argument that the decision is
incomplete rather than wrong: the remedy the fold chose, applied at one more site, fixes it.

### M4 — The canon says THREE triggers at `:58` and records a FOURTH at `:183`, and three citing sites restate the THREE.

Reading the canon as a reader arriving with *"a path was printed at session start — why?"*:

`.agents/skills/shared/handoff-path.md:58-59` — *"Three things print it, and only the first has a
subtle mechanism."* Sections `①` `②` `③` follow. Then at **84% of the file**, under a heading called
`## ⚠ What this file does NOT claim`, as a nested elaboration of a bullet:

`:183-190` — *"⛔⛔ **AND A FOURTH ALREADY EXISTS AT 0.33.0 — NO VENDOR BUMP NEEDED** (r6 CLAUDE H2). A
FLATTENED CONFIG CACHE …"*, measured 2/2 with a fresh-`TMPDIR` negative control.

The count is restated, with a citation, at every reader-facing site:

| site | wording |
|---|---|
| `.agents/skills/shared/handoff-path.md:58` | "Three things print it" |
| `.agents/skills/handoff/SKILL.md:17` | "⛔ **THREE things print it**" |
| `.claude/hooks/enforce-handoff-path.sh:70` | "the THREE things that print one" |
| `docs/plugins.md:86` | "the **THREE triggers** … are described ONCE" |

`check-canonical-source.py` exits 0: a count is not a token, and all four sites cite. This is a second,
independent instance of #289's `FAILS IF`, with a different mechanism from H1's.

Two things make it worth a Medium rather than a nit. First, the canon **predicts this reader's
failure in its own text** — `:195-197`: *"a reader following it will inspect three config layers, find
nothing, and conclude the canon is wrong"* — and then leaves the count at three in four places and
the fourth case with no `④` heading beside `①②③`. Second, the fourth case is the only one whose hinted
path (`remember.<session-id>.md`) *the next session will not read* (`:197-199`) — the original
*handoff with no reader* defect, which is this whole mechanism's reason to exist.

⭐ **And it answers #289's actual open question**, which `docs/backlog.md:279` states as *whether
anything can CHEAPLY find the next recital*: a **number** can, where a paraphrase cannot. The
disagreement above is found by one grep —
`grep -rn -iE '(three|3|four|4) +(things|triggers)' <live population>` — which returned all four sites
plus the canon. A token search cannot reach the fingerprint paraphrases (#289 is right about that), but
restated **counts** are a cheaply-checkable subclass, and three of this branch's recitals were counts.

**Which it is:** *complete the decision.* Reconcile the two senses of "trigger" once in the canon, give
the fourth case a `④`, and the citing sites stop needing a number at all — "the triggers are described
ONCE" carries no count to drift.

### M5 — #289 argues "no cheap finder exists" from a tool that does not exist in this repo, with a property that is false for one of the two tools bearing its name. This branch has already paid for that exact defect, and records it.

`docs/backlog.md:279`, filed by this fold:

> ⭐ So the open question is not the oracle, it is whether anything can CHEAPLY find the next recital:
> a token search cannot (the claims are paraphrased at every site …), and **`scripts/find-claim.py`
> survives line wrapping but is case-sensitive and markup-literal, so it returned 0 for a claim live
> at five sites.**

Measured:

```
$ ls scripts/find-claim.py                  → No such file or directory
$ git ls-tree HEAD   scripts/find-claim.py  → (empty)
$ git ls-tree master scripts/find-claim.py  → (empty)
$ git ls-tree process-281-mechanism-question scripts/find-claim.py
  100755 blob f6ebbb7ab750e73b55930470f03f38c42d3f1d72   scripts/find-claim.py
$ git ls-tree backlog-249-260-fixes          scripts/find-claim.py
  100755 blob ce63a7d96e1f3fb17ef3430f578403ec1af67b0c   scripts/find-claim.py
```

Three separate problems, in increasing order of what they cost:

1. **The path is absent at HEAD and on `master`.** It exists only on two unmerged branches, so #289
   explains why nothing caught the drift by naming something with **no owner in this repo at this
   commit** — no guard can watch it, and a reader following the row finds nothing.

2. **The name denotes two different tools.** `f6ebbb7ab7` (`process-281-mechanism-question`) is 226
   lines, whitespace-folding, **case-SENSITIVE**. `ce63a7d96e` (`backlog-249-260-fixes`, PR #371) is
   1,132 lines and **case-INSENSITIVE by default** (`:163` `re.IGNORECASE if ignore_case else 0`;
   `:1078` `build_pattern(args.pattern, not args.case_sensitive)`). ⚠ Reported to me by the
   coordinator, who measured both; I verified the two blobs differ and that neither path is on
   `master` — the **line counts and the two cited line numbers are UNVERIFIED by me**, since neither
   branch is checked out here. The property #289 asserts is true of one and false of the other, and
   both are absent, so the row cannot be acted on without first discovering which tool it meant.

3. ⛔ **It is the defect this branch already paid for and wrote down.** `scripts/check-handoff-path.py:67-70`:

   > ⟳ An earlier version named `check-withdrawal` as the guard that cannot see this. That guard does
   > not exist in this repo at this commit — it lives only on an unmerged branch — so the sentence
   > explaining why nothing caught this named something with no owner here, **which is the defect it
   > was describing** (round 1 M4).

   Round 1 M4 and #289's residue sentence are the same sentence shape about the same subject, five
   rounds apart, in the same branch. A different name, an unmerged branch, and an explanation of why
   nothing caught something that itself names nothing.

**Why this is a Medium and not a provenance nit.** #289's open question — *can anything cheaply find
the next recital?* — is what drives the next fix, and its "no" rests on two premises. The second is
false as stated (per 2 above). The first is false in a way **M4 demonstrates by example**: restated
**counts** are stable strings, and one grep found the `THREE`/`FOUR` disagreement across all four
sites. So the row's conclusion is not merely unsupported, it is wrong in the direction that matters —
there *is* a cheap finder for a real subclass of these recitals, and #289 currently tells the next
reader there is not.

**Which it is:** *complete the decision.* Delete the clause naming `find-claim.py`, or cite it the way
this repo's own rule requires for content it does not own — by **blob and branch**, not by path. Then
replace the conclusion with M4's measurement.

## Low

### L1 — The refusal now names the same canon twice, four lines apart, and its closing sentence says "both" under three pointers.

Rendered as a blocked reader sees it (the sever and the full output are in **Instruments**), the
refusal lists three pointer lines: `.claude/hooks/enforce-handoff-path.sh:67` and `:71` are both
`.agents/skills/shared/handoff-path.md`, with nothing saying they are the same document, and `:69` is
`corpus-search.md`. The closing line `:73-74` — *"Each is the ONE place that mechanism is described.
This refusal used to RESTATE **both**"* — scoped to two indented bullets before this commit; the commit
added a third pointer line immediately above them. "Both" is still defensible (there are two canons),
but a stopped reader scans three pointers naming two files and has to work that out. And "used to
restate both" now understates what *this* commit removed.

## Checked and found SOUND

- ⭐ **The brief's central hypothesis — that the deletion traded a wrong claim for an unusable
  refusal — is REFUTED, and the refusal is actionable in a way that is asserted, not merely true.**
  I executed the hook with a reverted skill (full output under **Instruments**). The blocked reader
  gets `.remember/remember.md` **three** times, the probable cause, the re-apply instruction, the file
  to edit and the verification command. I then gutted the heredoc further — deleting the action line
  and the sentence naming the path at `.claude/hooks/enforce-handoff-path.sh:62-67`, inside the
  `cat >&2 <<EOF` block, keeping only the citation — and the path **still** reached the reader twice:
  once from `$VERDICT_OUT`, which is built from `CONSUMED_PATH` at `scripts/check-handoff-path.py:71`
  and printed at `:79`, and once from the hook's own "Re-apply" paragraph. So the refusal's primary
  action is backed by a constant that `check-handoff-path.py --self-test` exercises (10/10) and that
  `scripts/mutations/check-handoff-path.json` ratchets (5 expected, `check-plan-code.py:1370` region).
  The deletion removed only the *why*, and the *why* is one path away.
  ⚠ The residue, stated rather than hidden: nothing asserts the refusal's **prose**. Green control on
  `check-canonical-source` / `check-handoff-path` / `check-ratchet-contract` (all rc=0), then the gut
  above, then all three **still rc=0**; no mutation manifest targets
  `.claude/hooks/enforce-handoff-path.sh` at all (`grep -ln enforce-handoff-path scripts/mutations/*.json`
  → nothing). That is a pre-existing gap, not one this fold opened, and the measurement above shows the
  one property that matters survives independently of it.

- **`check-handoff-path.py` works and its falsifier fires.** 10/10 self-test; live rc=0
  (`ok — .agents/skills/handoff/SKILL.md names .remember/remember.md`). Severing the skill to upstream
  (`mktemp` only) → `rc=1` from the script, `rc=2` from the hook, with the refusal printed. Restoring →
  silent `rc=0` on the happy path, as the hook's `:21-22` claims.

- ⭐ **The two new H3 token cases are genuinely bound one-to-one. I constructed the counter-examples
  rather than reasoning about them.** Green control (25/25), then deleting **both** delivery tokens
  from `CANONS["handoff-path"]["tokens"]` (`scripts/check-canonical-source.py:131-135`) in one edit:

  ```
  [FAIL] a site restating the handoff symbol with no citation is detected: got False want True
  [FAIL] a site restating the handoff banner with no citation is detected: got False want True
  23/25 passed
  ```
  Exactly the two named cases fail and no others — neither is satisfiable through the other, and
  neither is collateral. The reason holds on inspection too: each leak file carries only its own token
  (`:483-489`), the banner string contains no `REMEMBER_HANDOFF` and the symbol sentence contains no
  banner, and the assertion requires `repr(tok)` in the finding, so a `hit` raised by a different
  token cannot satisfy it. A widening mutation (`=== LAST HANDOFF ===` → `HANDOFF`) is also killed:
  the banner leak's `hit` becomes `'HANDOFF'` and fails the `repr(tok)` test.

- ⭐ **Scoped mutation harness reproduces, independently of the Codex half.** `HARNESS_TREE` derived
  with `ast.literal_eval` (not grep) from `scripts/check-plan-code.py:199` — **7** paths
  (`scripts`, `supabase`, `docs`, `node_modules/typescript`, `.claude/hooks`, `.github/workflows`,
  `.agents/skills`), all present. On a pruned copy under the scratchpad (59 of 60 manifests removed,
  `EXPECTED_MUTATIONS` rows pruned to match, in the COPY only):

  ```
  [1/1] control scripts/check-canonical-source.py
  [1/5] … [5/5]
  [1/1] re-control scripts/check-canonical-source.py
  OK — delivered scripts mutated: 1 file(s), 5 mutation(s), 5 killed, 5 attributed to the case
       each names, 0 survivor(s) — measured over the WHOLE manifest
  ```

- **Every declared count re-derived by running, not read.** `check-canonical-source --self-test`
  **25/25**. `EXPECTED_MUTATIONS` (`ast`, `check-plan-code.py:587`): **60** files, declared sum
  **1413**, `scripts/check-canonical-source.py` → **5**, `scripts/check-handoff-path.py` → **5**.
  Filesystem manifests: **60** files, **1413** entries — the two agree.
  `check-fixture-variation.py` live: rc=0, *"826 parameter(s) examined across 65 file(s)"*;
  `--self-test` **67/67**; its `check-canonical-source.py` tuple at `:321-325` is exactly
  **4** parameters — `audit.canons`, `audit.root`, `main.argv`, `main.root`.

- ⭐ **Every anchor in EVERY manifest binds exactly once in the pristine file — tested as `count != 1`,
  so an orphan and a multiple are both caught.** 60 manifests, 1413 entries, **0** with `count != 1`,
  and **0** naming a file that does not exist. (The `count != 1` form matters here: `0` is the orphan
  case, and this branch's own `_walked_textfiles` rename at `:213` was safe only because it was checked
  this way first.)

- **The substring widening is real and still LATENT.** A `REMEMBER_HANDOFF_STATE`-only mention is
  matched by the `REMEMBER_HANDOFF` token (`:284`, plain `in`), but all five live carrying sites have
  ≥1 bare occurrence, so no site is required to cite solely because of a `_STATE` match. Verdict
  unchanged from the docstring; only its figures are stale (M2).

- **Bound "5/5 and 3/3" holds.** `scripts/check-canonical-source.py` carries every `handoff-path`
  token (`REMEMBER_ROOT` 1, `PER_SESSION_HANDOFF` 1, `_resolve_memory_project_dir` 1,
  `REMEMBER_HANDOFF` 5, `=== LAST HANDOFF ===` 3) and every `corpus-search` token
  (`git grep --cached` 1, `rg --hidden` 1, `-RSl` 1).

- **The guard has a real caller.** `.github/workflows/ci.yml:313` runs it and `:316` runs its
  `--self-test`, so a missing canon (`audit()`'s first `FAILS IF`, `:265-267`) reddens CI rather than
  only a local run. This answers the worry that the canon now lives inside `.agents/skills/`, the tree
  `npx skills@latest add mattpocock/skills` rewrites: if a vendor update removed
  `.agents/skills/shared/handoff-path.md`, CI fails — and the refusal's own actionable content does not
  depend on it (measured above).

- **The canon's `⛔ RULE` is still findable, and I agree with the Codex half that length alone is not
  the defect.** Two canons total **17,386** characters, and the RULE heading sits at
  `handoff-path.md:16`, **7.5%** into the file. Headings: `:16` (7.5%), `:63` (32.8%), `:109` (52.1%),
  `:165` (80.6%), `:170` (82.0%), `:178` (84.2%); correction/round markers occupy **10 of 203** lines
  (5%), so the correction trail is not what the reader wades through. My argument for the other side
  is **structural, not length** — it is M4, and it would survive shortening the file.

## CANNOT RUN

None. Every finding and every SOUND item above was produced by executing something, with a green
control stated wherever a sever was applied.

⚠ **NOT RUN, therefore NOT VERIFIED (not a pass):** the full 1,413-mutation sweep (CI is authoritative;
I ran the 5-entry scope); the complete repository guard sweep; `test:integration` / `test:e2e`. I make
no claim about those.

## Instruments

Everything ran on **copies** under the session scratchpad, produced with `git archive <rev> | tar -x`.
The worktree was never modified — `git status --porcelain` empty at start and at finish — and the only
file I created in it is this review.

| what | result |
|---|---|
| `check-canonical-source.py --self-test` | **25/25** |
| `check-canonical-source.py` live | rc=0, 2 mechanisms |
| `check-handoff-path.py --self-test` | **10/10** |
| `check-handoff-path.py` live | rc=0 |
| `check-fixture-variation.py --self-test` / live | **67/67** / rc=0, 826 params across 65 files |
| `check-ratchet-contract.py` live | rc=0 |
| scoped `check-plan-code.py --mutate .` | **5 killed, 5 attributed, 0 survivors**, control + re-control green |
| all-manifest anchor audit (`count != 1`) | 60 manifests, 1413 entries, **0** bad |
| hook executed with reverted skill | rc=2, refusal printed (below) |
| vendor hook probed | `remember/0.33.0`, 2027 lines, **2** `REMEMBER_HANDOFF=` assignments (`:1168`, `:1171`), 23 bare-name lines — all three figures agree with the canon |

**Severs applied, each with its exact insertion point and a green control stated beside it:**

1. `scripts/check-canonical-source.py:68`, inside the module docstring — replaced the literal
   `shared/corpus-search.md`. Control rc=0 → after rc=0. (M1.2)
2. `scripts/check-canonical-source.py`, inserted a third `CANONS` dict immediately before the
   `"name": "corpus-search"` entry, plus `.agents/skills/shared/zz-third.md`, no prose citation.
   Control rc=0 → after rc=0, 3 mechanisms. (M1.3)
3. `scripts/check-canonical-source.py:131-135`, inside `CANONS[0]["tokens"]` — removed both
   `"REMEMBER_HANDOFF",` and `"=== LAST HANDOFF ===",`. Control 25/25 → after 23/25, exactly the two
   named cases. (SOUND)
4. `.agents/skills/handoff/SKILL.md`, whole file replaced with an upstream-shaped body naming only
   `mktemp`. Control: hook silent rc=0 → after: hook rc=2 with the refusal. (SOUND)
5. `.claude/hooks/enforce-handoff-path.sh:62-67`, inside the `cat >&2 <<EOF` heredoc — deleted the
   action line and the sentence naming the path, keeping the citation. Control: all three guards rc=0
   → after: all three still rc=0; the path still reaches the reader twice. (SOUND, with the residue
   stated)

**Interpreter, and which claim-search tool I used.** Everything above ran on
**`Python 3.14.4 (main, Apr 7 2026) [Clang 21.0.0]`**, the `python3` on `PATH` in the worktree.

⛔ **I used NEITHER `find-claim.py`.** Both prose sweeps were written inline, in the same process that
imported the guard: whitespace-folded with `re.sub(r"\s+", " ", re.sub(r"[`*_\[\]]", "", body))` and
matched with `re.IGNORECASE`, so they are **markup-stripped and case-insensitive** — strictly weaker
assumptions than either `find-claim.py` makes, which is why they found H1 and M4. I name this
explicitly because a bare "`find-claim.py`" is ambiguous at this commit: the path is absent at HEAD
and on `master`, and the name denotes two tools with **different case semantics** on two unmerged
branches (`f6ebbb7ab7` case-sensitive, `ce63a7d96e` case-insensitive by default). That ambiguity is
itself reportable and is filed as **M5**.
⚠ The earlier draft of this review repeated the brief's and `docs/backlog.md:279`'s characterisation
of `find-claim.py` as "case-sensitive and markup-literal". That is true of only one of the two blobs,
it was never load-bearing for any measurement here, and it is corrected above and in M5.

**Proving known positives before trusting negatives.** The fingerprint sweep asserted the canon
matches (3 hits) before reporting any site as clean; the count sweep asserted `handoff-path.md:58`
matches before enumerating the citing sites; the token population was derived by **importing** the
guard's `_walked_textfiles` and `EXEMPT` rather than re-implementing them (a second implementation of
one rule drifts — 17 recorded instances in this repo). ⚠ Every control was **whitespace-folded, not
line-based**: `handoff-path.md:58-59` wraps "Three things / print it" across a line break, so a
line-based `grep` for that phrase returns 0 and the zero is the instrument, not the repo — folding
first is what made M4's known positive fire.

**The refusal, verbatim, as a blocked reader sees it** (hook executed, skill reverted):

```
╔══════════════════════════════════════════════════════════════════════════╗
║  ⛔ BLOCKED — the handoff skill would write where nothing reads          ║
╚══════════════════════════════════════════════════════════════════════════╝

REVERTED — .agents/skills/handoff/SKILL.md
  SKILL.md does not name .remember/remember.md — the only path the SessionStart hook reads. A handoff written anywhere else has no consumer.

A vendor update (`npx skills@latest add mattpocock/skills`) most likely overwrote it.
Re-apply: the skill must save to .remember/remember.md, keeping mktemp only for the
mid-task-subagent case. See docs/plugins.md → Session Handoff.

MEASURED: three handoff docs were written to $TMPDIR and none was ever read.
The documents were fine. They had no consumer.

Write the handoff to:  .remember/remember.md

That is the one path the remember plugin's SessionStart hook reads. WHY it is
the one that gets read — the symbol, the banner, the injection order and the
delivery fingerprint, each with its real bound — is described ONCE, and this
refusal does not restate it:  .agents/skills/shared/handoff-path.md
  To inventory where a string appears in this repo, and why ONE command is not
  enough:  .agents/skills/shared/corpus-search.md
  Why a path may have been printed at session start, and the THREE things that
  print one:  .agents/skills/shared/handoff-path.md

  Each is the ONE place that mechanism is described. This refusal used to RESTATE
  both, and drift between the copies made it print a claim and its own withdrawal
  in the same message -- which is the defect the single source removes.

Then repair the vendored skill so this stops recurring:
  $EDITOR .agents/skills/handoff/SKILL.md      # see docs/plugins.md -> Session Handoff
  python3 scripts/check-handoff-path.py         # must exit 0
```

## Thrashing or prose floor

**My verdict: THRASHING PERSISTS — and I agree with the Codex half's qualification, which this round's
evidence strengthens rather than merely repeats.**

`docs/dev-process.md:113-120` arms the architecture review on *two consecutive rounds whose findings
came from the previous round's own fix, in one component*. Round 7's Codex M1 was round 6's L9 fix
reaching one site and not its siblings. Round 8's findings here are round 7's own fold: H1 is the r7
fold's three-site repair missing its fourth site **inside the file the same commit edited to explain
the repair**; M1, M2 and M5 are bounds and premises *written by that commit* that were false the moment
it committed them; M3 is the r7 remedy not applied to a site the r7 search never enumerated. That is
the arming condition met for a third consecutive round, and I state it as such.

⚠ And M5 sharpens it in the way that is hardest to argue away: it is **round 1 M4's defect, repeated
in round 7**, with the repo's own written record of having paid for it sitting in a file this branch
edits (`scripts/check-handoff-path.py:67-70`). A class recurring five rounds apart *with its lesson
already committed* is not a floor being approached.

**Now the part the brief asks me to argue rather than assert: is the round-6 H3 self-inflicted
instance thrashing, or a prose floor being enforced by a working instrument?**

It is *neither on its own*, and the distinction that resolves it is **who caught it**. Round 6's fold
wrote the delivery fingerprint unconditionally into the canon and the guard then caught three further
self-inflicted copies during that same fold — that half is a **working instrument**, and an instrument
catching an author's mistake during authoring is the system functioning, not thrashing. Counting it as
thrashing would make every successful guard look like a defect.

But look at what the instrument caught and what it could not. The guard caught **placement** — a
second copy existing. It did not catch, and by `:52-61` of its own docstring cannot catch,
**disagreement**. Every single finding on this branch for two rounds now — r7 M1, and H1, M3, M4 here —
is in the half the instrument is structurally blind to. So the shape is not "prose that keeps being
imperfect"; it is **one defect class, in one component, whose only detector is a human reading four
files side by side**. Six rounds have each found an instance of it. That is the definition this repo
uses, and a prose floor is what you call it when the findings *change character*; these do not. r5's
was a correction reaching the skill and not the hook; r6 L9's was five unconditional copies; r7 M1's
was three cited copies contradicting the canon; mine is a fourth cited copy contradicting the canon,
plus two false bounds and a count restated at four sites. Same class, five consecutive times.

**So: thrashing — and the Codex qualification is correct, which is the operative half.** Reopening
would mean the one-canonical-source redesign is wrong. Nothing I measured says that. The opposite:

- every finding's remedy is *delete the recital, keep the citation* — the redesign's own move, applied
  once more (H1: one word; M3: four comment lines; M4: a heading and a count);
- the guard is sound where it claims to be. Its self-test is honest, its two new H3 cases are bound
  one-to-one by construction, its five mutations are all killed and all attributed, it has a CI caller,
  and the only things wrong with it are three **sentences about itself** (M1, M2);
- the measured trend is the right direction: the mechanism went from six uncompared copies to one canon
  plus citations, and what remains are **four** residual recitals, three of which I can name by
  `file:line` and all of which are one-line edits.

⭐ **The one thing I would add to the chosen decision, because it is what the evidence actually points
at.** #289 records the open question as *whether anything can cheaply find the next recital*, and
answers **no** from two premises: a token search cannot (paraphrase), and `find-claim.py` cannot
(case-sensitivity). **Both premises are wrong**, which makes the answer wrong in the direction that
matters — it tells the next reader to stop looking.

- The second premise names a tool absent from this repo whose two same-named versions disagree on
  exactly the property cited (M5).
- The first is right about paraphrases and wrong as a general conclusion, and M4 is the proof: three
  of this branch's live recitals are **numbers** — `THREE things print it`, `TWO assignments`,
  `23 lines` — and a number is a stable string one grep finds across every citing site in under a
  second. ⚠ With one precondition I had to pay for myself: the search must be **whitespace-folded**.
  `handoff-path.md:58-59` wraps "Three things / print it" across a line break, so line-based
  `grep -c "Three things print it"` returns **0** on the canon while the folded form returns **1** —
  measured both ways. A line-based zero here is the instrument, not the repo.

So completing the decision should include the cheap half that does exist: either hold restated
**counts** the way `tokens` holds symbols, or — better, and strictly in the redesign's own idiom —
delete the counts from the citing sites, because *"the triggers are described ONCE"* carries no number
that can drift.

⚠ One honest limit on this verdict, stated rather than hidden: I reviewed one component across seven
rounds of its own history, and `docs/dev-process.md:113-120` warns that *on a document rounds can be
right forever*. My answer to "is this a signal to go build instead" is **no, but not for long** — the
four remaining edits are nameable and bounded, and if round 8's findings are again *a bound written by
round 7's fold*, the subject has stopped being the mechanism and started being the review loop.
