# Post-Plan Gate round 2 — Claude adversarial review

**Subject:** commit `c460f015` — `docs/superpowers/plans/2026-09-11-goal-work-threads.md` (plan v2),
`docs/superpowers/specs/2026-09-11-goal-backlog-pr-join-design.md` (spec v4).

**PROOF OF SUBJECT.** The first sentence of the plan's `pr_fanout` docstring at `c460f015`:

> `PR number -> how many threads reach it. PURE.`

That sentence is itself the round-2 Blocking, and it is quoted here from the commit I was pointed at,
not from the working tree — see the next paragraph.

⚠ **THE SUBJECT MOVED UNDER THIS REVIEW, AND THAT CHANGES WHAT THIS DOCUMENT IS.** I read
`c460f015` at the start. Partway through the corpus measurements the working tree acquired
`docs/reviews/codex/plan-goal-work-threads-r2-codex.md` and **85 changed lines in the plan plus 25 in
the spec**, uncommitted. The Codex half of this round had landed *and its findings had already been
applied to the plan* while my half was still measuring. So:

* Findings marked **[c460f015 — already fixed in the tree]** were reached independently here and are
  recorded only as corroboration. They are not asked for again.
* Findings marked **[WORKING TREE]** are against the *r2 remediation itself*, which no reviewer has
  seen. This is where the value is, and it is where the Blocking is.

**Method.** As in round 1, the plan's code was transcribed verbatim into a runnable copy of
`gen-goals-page.py` (both at `c460f015` and again at the working tree), the full self-test was run,
23 mutations were applied to check every new case can fail, and the page was built against the real
repository. Every number below was produced by running something.

---

## Q1 — did the fixes introduce new defects?

### BLOCKING B1 — the r2 fix for the `rel` KeyError ships a case that CRASHES the suite, and it is wrong in three separate ways
**[WORKING TREE]** — plan Task 5, step 1 and step 3.

The r2 remediation hardened two `rel` reads and added a case for them:

```python
        named = {d.get("rel") for d in (t.get("spec"), t.get("plan")) if d}
        for d in t.get("docs", []):
            if d.get("rel") not in named:
```

```python
    eq("a document record with no rel does not crash the renderer",
       "extra document" in render_threads(
           [{"stem": "s", "spec": {"name": "s.md"}, "plan": None,
             "docs": [{"name": "other.md"}], "prs": [], "pr_error": False}], {}), True)
```

Run against the transcribed working-tree code, the suite does not report a failure — it **dies**:

```
  ✓ an extra document on a stem is rendered, not silently dropped
Traceback (most recent call last):
  File ".../gen_goals_v3.py", line 780, in self_test
    "extra document" in render_threads(
  File ".../gen_goals_v3.py", line 466, in render_threads
    f'<a href="/src/{esc(d["rel"])}">{esc(d["name"])}</a></div>')
KeyError: 'rel'
```

Line 466 is **not** the extra-document loop. It is the spec/plan row, which the fix did not touch:

```python
        for side, missing in (("spec", "no spec"), ("plan", "no plan")):
            d = t.get(side)
            if d:
                parts.append(f'<div class="prline"><span class="t">{side}</span>'
                             f'<a href="/src/{esc(d["rel"])}">{esc(d["name"])}</a></div>')
```

Three defects, measured one at a time:

1. **The fixture crashes before the code under test is reached.** The fixture's `spec` is
   `{"name": "s.md"}` with no `rel`, and the spec row dereferences `d["rel"]` directly.
2. **Even past that, the branch the case exists to exercise never fires.** With a rel-less spec,
   `named` evaluates to `{None}`; the rel-less extra document's `d.get("rel")` is also `None`;
   `None not in {None}` is `False`, so the document is silently skipped. Measured:

   ```
   named = {None}
   extra doc's d.get('rel') = None
   would the extra-doc branch fire?   False
   ```

   `"extra document" in html` would be `False`, so the case would assert `False == True` and go red
   anyway. The `.get` hardening converted a crash into a *silent drop* — which is the exact defect
   round 1's H1 was filed against, rebuilt one layer down.
3. **Give the spec a `rel` so both of the above are passed, and the extra-document link still
   crashes**, because that branch's `<a href>` also uses `d["rel"]`:

   ```
   with a rel-bearing spec, the EXTRA-DOC <a href> still raises KeyError: 'rel'
   ```

**What breaks.** Task 5 step 4 says `--self-test → PASS, 59/59`. It cannot pass: the suite emits no
`N/M … passed` line at all. `check-selftest-counts.py`'s documented behaviour for that is
*"a child prints no parseable `N/M … passed` line → exit 2, CANNOT RUN, never a pass"*, so step 4's
second command fails too, and the branch stops at Task 5 with 13 later cases never executed.

**The concrete failing scenario is the plan's own fixture**, run exactly as written. Quarantining
just this one case makes the remaining suite green at `62/62`, which is how every other number in
this review was obtained.

**Fix shape** (a hypothesis, to be run before it is believed): use `d.get("rel", "")` at *all four*
dereference sites, and drop the rel-less document from `named` (`if d and d.get("rel")`) so a missing
`rel` cannot alias a second missing `rel`. Then re-run — the case must go from red to green *via this
fixture*, not by deleting it.

### HIGH H1 — Task 6's literal edit quotes a line that does not exist and drops a closing tag
**[still live in the WORKING TREE]** — plan Task 6, step 3.

The plan says `:385` "currently reads":

```html
    <strong>{docs}</strong> documents, <strong>{spined}</strong> with a milestone spine.
```

It does not. The file reads:

```
384|  <p class="standfirst">One card per goal, keyed by its <strong>anchor</strong> — the name that
385|    survives a rename. <strong>{len(anchors)}</strong> goals, <strong>{docs}</strong> documents,
386|    <strong>{spined}</strong> with a milestone spine.</p>
```

The quoted "line" is a splice of the tail of `:385` and the whole of `:386` **minus its `</p>`**, and
the replacement block the plan supplies also has no `</p>`. An implementer applying "replace that one
line with:" mechanically deletes the paragraph's closing tag; the following `<p class="standfirst">`
then nests inside an unclosed `<p>`, which browsers resolve by auto-closing at an unpredictable point
and which no test in this plan can see. (My harness only rendered correctly because I re-added the
`</p>` by hand.)

Round 1's H2 was *"v1 gave a bare `f"…"` fragment here, which is not an edit an implementer can apply
mechanically."* The remediation replaced one non-applicable edit with a different one. Quote both
lines `:385-386` in full, keep the `</p>`, and say "replace these two lines".

### HIGH H2 — Task 5's own verification expects 35 and the page produces 21
**[still live in the WORKING TREE]** — plan Task 5, step 4.

```bash
grep -c '>no plan<'              /tmp/goals-check.html    # expect 35 — the PAIRING RATE
```

Built against the real repository, that grep returns **21**. The prose beside it is right and the
command is wrong: *"35 of 41 threads show one half absent"* — but the 35 split into two different
strings, and only one of them is being counted.

```
<details class="thread"    41      <- matches the plan's expectation
>no plan<                  21
>no spec<                  14      <- 21 + 14 = 35
```

An implementer runs this, sees 21 against an expected 35, and is left to decide whether the pairing
logic is broken. It is not. Either count both (`grep -c -e '>no plan<' -e '>no spec<'`) or state the
two numbers separately. This is new material — the whole grep block is round 1's M2 fix.

### Q1(a) — `pr_fanout`, its position after `out.sort`, empty threads, and coverage

**[c460f015 — already fixed in the tree, reached independently here]** At `c460f015` the function
counted **threads** while the page rendered `on {n} documents`. Measured over the real corpus, the
two disagree for **5 of 57** PRs:

```
PR      rendered   real document count
#214      2              3
#176      2              3
#225      1              2      <- renders no fan-out at all
#189      1              2      <- renders no fan-out at all
#186      1              2      <- renders no fan-out at all
```

The error is always an **undercount** (a PR touching both halves of one thread is deduped to one),
and it lands hardest on the 6 both-halves threads, which are the design's whole point. `#186` is the
spec's own headline fixture (`#186 · touched code`), so at `c460f015` the retraction's mechanism
reported the wrong number on the example the spec uses to explain it. The working-tree fix
(`pr_fanout(hist_cache.values())`, one vote per document) is **correct**: re-measured, all five
mismatches resolve, `#186→2`, `#176→3`, `#214→3`, and `fanout["147"]` stays **22**.

The other three sub-questions are clean, verified by running:

* **Ordering.** `fan` is computed after `out.sort(...)` and this is harmless — the value is global and
  attached to every record afterwards, so sort order cannot affect it. Under the working-tree version
  `hist_cache` is fully populated by then, because `"threads": [thread_prs(t, history) …]` is
  evaluated inside the loop that builds `out`.
* **Empty `threads`.** An anchor with no documents renders
  `No spec or plan declares this goal.`, `0 thread(s) · 0 PR(s)`. No crash; verified in the built page.
* **Every anchor record gets it.** All 11 do; the loop is over `out`, which is one record per registry
  row.

### Q1(b) — `head` and `a.get("head", "?")[:8]`

**[c460f015 — already fixed in the tree, reached independently here]** At `c460f015` the call was the
only unguarded `subprocess.run` among the four git calls the plan adds or touches, and it sat
*after* every honest `None`/CANNOT-RUN path — so on a machine where git is unavailable the page would
abort at the one call that had no `except`, never reaching the `history could not be read` rendering
the plan built. The working-tree fix adds `timeout=20` and `except (OSError,
subprocess.SubprocessError)`, matching its siblings. Verified: a non-zero return or an exception now
yields `"unknown"`, and `"unknown"[:8]` is `"unknown"`, rendering
`derived from git at unknown` — loud and honest.

**LOW L1** — `main()` renders `git rev-parse --short HEAD` (7 chars) in the masthead while the Work
band renders `head[:8]`. Two different abbreviations of the same commit on one page reads as two
commits. Slice to the same width, or reuse the value `main()` already has.

### Q1(c) — the extra-document loop

Traced, all three cases:

* **spec and plan the same dict** — cannot happen from `pair_documents`: `slot` is chosen by `kind`
  and only one slot is filled per document, so `spec is plan` is unreachable. No defect.
* **`docs` absent** — `t.get("docs", [])` handles it, and `render_threads` is reached from
  `collect`, which always supplies the key. No defect.
* **a doc dict lacking `"rel"`** — this is B1 above, and it is not merely a KeyError: the working-tree
  `.get` fix makes a rel-less extra document collide with a rel-less spec and vanish.

**MEDIUM M1 — `thread_prs` never reads the extra document's history.** The union runs over
`("spec", "plan")` only:

```python
    for side in ("spec", "plan"):
        d = thread.get(side)
```

so a third document on a stem is *rendered as a link* (round 1 H1's fix) while its pull requests are
never fetched, never appear in the thread's `N PR(s)`, and — because it never enters `hist_cache` —
contribute nothing to the document fan-out either. A thread whose only PR-bearing document is the
collision would render `no pull requests`, which is a false absence rather than a stated gap.
Corpus today: **0 threads have an extra document** (distribution 35×1 doc, 6×2 docs), so this is
latent — but it is latent in the one branch the plan added specifically because the collision must be
visible.

### Q1(d) — the widened `DOC_PATH`

**[c460f015 — already fixed in the tree, reached independently here]** The direct probes at
`c460f015`:

| path | verdict at `c460f015` |
|---|---|
| `README-generator.ts` | **documentation** ← wrong |
| `READMEs/index.tsx` | **documentation** ← wrong |
| `CONTEXT.md.ts` | **documentation** ← wrong |
| `CLAUDE.md.ts`, `AGENTS.md.bak` | **documentation** ← wrong |
| `docs-site/app.ts` | code ✓ |
| `.agentsfoo/x.ts` | code ✓ |
| `lib/README.md` | code (a nested README is not covered) |

`^README` and `^CONTEXT\.md` were unanchored prefixes. The working-tree fix anchors the file literals
while leaving the three directory prefixes unanchored, which is the right split:

```python
DOC_PATH = re.compile(
    r"^(docs/|\.remember/|\.agents/|(README(\.md)?|CONTEXT\.md|AGENTS\.md|CLAUDE\.md)$)")
```

Re-probed: all four wrong verdicts above flip to `code`, and every path in round 1's F7 fixture
(`README.md`, `CONTEXT.md`, `AGENTS.md`, `CLAUDE.md`, `.agents/skills/brief/SKILL.md`,
`.remember/remember.md`) still resolves to documentation. No regression.

**The measurement you asked for — the last 400 commits, 256 of them PRs:**

* The widening flips **exactly 10** PRs from `code` to `docs only`, matching the spec's stated
  measurement. All ten are genuinely documentation:
  `#267 #266 #265 #167 #111 #99 #93` (each touching only
  `.agents/skills/**/*.md`) and `#216 #51 #48` (each touching only `CONTEXT.md`).
* **No implementation PR is mis-tagged.** There is no eleventh flip.
* The reverse arm of F7 is also clean: **0** PRs tagged `touched code` whose file list is entirely
  markdown.

**LOW L2 — `.agents/` is broader than the `.agents/skills/**` that was measured.** One tracked file
under it is not documentation:
`.agents/skills/diagnose/scripts/hitl-loop.template.sh`. A PR touching only that file tags
`docs only`, which is F7's stated failure condition. One file today; worth a sentence in the
docstring rather than a narrower regex.

### Q1(e) — the case-count chain

**Counted mechanically from the plan's own step-1 blocks, then verified by running the transcribed
suite.** At `c460f015` the chain was `15 → 25 → 33 → 37 → 43 → 55 → 58`; in the working tree it is
`15 → 25 → 34 → 38 → 45 → 59 → 62`. Both are internally consistent:

```
  Task 1: +10 ->  25   plan declares: ['25']
  Task 2: + 9 ->  34   plan declares: ['34']
  Task 3: + 4 ->  38   plan declares: ['38']
  Task 4: + 7 ->  45   plan declares: ['45']
  Task 5: +14 ->  59   plan declares: ['59']
  Task 6: + 3 ->  62   plan declares: ['62']
```

The transcribed working-tree suite runs **62/62** with B1's case quarantined, and the `c460f015`
suite ran **58/58** with nothing quarantined. The Global Constraints line's "adding 47 cases" also
reconciles (`62 − 15 = 47`). `count_drift`'s regex is
`r"--self-test\s+#\s*(\d+) cases"`, so the shortened form the later tasks use (`# 34 cases`, dropping
`, pure functions only`) still parses. **No arithmetic defect on this axis.**

One caveat that is not arithmetic: **`:6` will still say "pure functions only" while the suite now
covers `annotate_code`, which lives below the collection banner.** Trivial, but it is a claim on the
line every task edits.

---

## Q2 — is the retraction complete?

I did not grep for a remembered phrase. I read both documents end to end, then swept mechanically for
the *inference*: every sentence, docstring, test label, comment and rendered string in which a reader
could conclude "this PR implemented this thread". The residue sorts into three groups.

### Found at `c460f015`, already fixed in the working tree

Recorded as corroboration only — two reviewers reached the same three independently.

1. **Spec §5, the card mockup, still drew the retracted UI.**
   `PR #176  2026-08-29  Retire the plan-as-CI-dependency…   [code]` and
   `blob-addressing-reservation                  ⚠ no code PR yet`
   — while the plan's Task 5 says ⛔ *"NO `n_code` SUMMARY AND NO `no code PR yet` FLAG. Both are
   deleted by the retraction."* The spec's picture of the card is the thing a reader looks at first.
2. **Spec §5's bullet still specified the badge v3 cut**, not merely the v4 claim:
   *"renders as a `spec → plan → PR` thread with a state — **shipped**, **in flight**, **not
   started**"*. That is v2's tri-state label, cut in v3 for being 96%-in-one-bucket, surviving one
   full version past its own retraction.
3. **§3.2a's heading was `The implementation chain — spec → plan → shipped`.** The heading asserted
   in five words exactly what §3.2a's body spends thirty lines withdrawing.

### Still live in the working tree

**MEDIUM M2 — F7a's evidence measures a different population than F7a's rule, and it is the weaker
one.** Spec `:416-418`:

> **F7a — The tag must discriminate over the real corpus.** Fails if every PR in the corpus carries
> the same tag. Measured 2026-09-11: 44 documents reach ≥1 code-touching PR, 1 reaches only doc-only
> PRs, 1 reaches none. ⚠ **This is a weak margin and is stated rather than hidden**

The rule is quantified over **PRs**; the evidence counts **documents**. Measured over the real corpus
by the transcribed code, per PR:

```
distinct PRs reached by anchored documents: 57   ->   38 touched code / 19 docs only
rendered PR lines on the page:              94   ->   72 touched code / 22 docs only
```

That is a **67/33** split, not 96/4. F7a is understating its own health by a wide margin because it
inherited v3's per-document framing, and the consequence is not cosmetic: the "weak margin" sentence
is the stated reason the tag might be cut next, exactly as the badge was. Re-state F7a over PRs and
carry the 38/19 figure.

**LOW L3 — F7 is written against a token the page never emits.** Spec `:410-412` says *"A PR's
`code` / `docs only` tag"* and *"`#186` must tag `code`"*, three times. Item 1 of the v4 fix says the
tag reads **`touched code`**, and the plan's case asserts `>touched code<`. A falsifier whose subject
string does not exist cannot be checked against the page by anyone reading only F7.

**LOW L4 — the mockup's direct-work row keeps the retired bracket style.** Spec `:322`:
`PR #67   2026-08-14  Serve-path deadline          [by path]`, immediately below three rows the r2 fix
rewrote to `#176 · touched code · …`. Direct work is explicitly out of this plan's scope, so this is
the spec's problem, not the plan's — but the two styles now sit four lines apart in one picture.

### Swept and clean

* **The plan.** No surviving sentence claims the tag identifies the implementation. The nearest
  candidate is the plan's own goal line, *"shows the work that pursued it"*, and its Task 5 commit
  message, *"a bulk edit cannot pose as an implementation"* — both are claims about the *page*, not
  about a PR, and the second is a claim the code now makes true.
* **`files_are_code`'s docstring** carries the retraction in its own words
  (*"THIS IS A CLAIM ABOUT ONE COMMIT, NOT ABOUT A THREAD"*).
* **Rendered strings.** The page emits exactly three tag texts (`touched code`, `docs only`,
  `unknown`), two thread flags (`history could not be read — treat as NOT MEASURED`,
  `no pull requests`) and the fan-out span. None asserts implementation. Verified against the built
  page, not read off the plan.
* **`44 shipped / 1 doc-only / 1 no-PR`** at spec `:192` is inside the v3 narrative describing what
  was cut and why. Correct as history.

---

## Q3 — can the new cases fail?

Not argued — **measured**. 23 mutations were applied to the transcribed code, one at a time, over a
control proved green first (`58/58` at `c460f015`, `62/62` in the working tree). Each line below is
the mutation and the cases it turned red.

```
control: 58/58 self-test cases passed  rc=0

  fanout span deleted (always empty)          -> a PR touching many documents renders its fan-out
  fanout span unconditional                   -> a PR touching one document does not claim a fan-out
  tag reads 'implemented'                     -> the two PRs are distinguishable in the markup
                                                 the tag makes no implementation claim
  extra-document loop deleted                 -> an extra document on a stem is rendered…
  pr_error branch removed                     -> an unreadable history says so…
                                                 and it does NOT also claim there are no pull requests
  'no pull requests' branch removed           -> a thread git found no PR for says so
  render_threads returns ""                   -> 9 cases red
  PR_TAIL loses its $ anchor                  -> a PR-looking number mid-subject is not the PR
  DOC_PATH loses .agents/                     -> this repo's documentation outside docs/ is not code
  DOC_PATH loses CONTEXT.md                   -> (same case)
  DOC_PATH narrows to docs/ only              -> (same case)
  annotate_code maps unreadable -> False      -> an unreadable commit is unknown, not False
  pr_fanout counts nothing (always 1)         -> fan-out counts the documents a PR touched
  thread_prs sorted() removed                 -> a thread's PRs are the union…, NEWEST FIRST
  pair_documents drops extras from docs       -> a second document in a slot is kept, not dropped
  doc_stem strips -design only                -> stem strips -plan (+1)
  doc_stem strips anywhere (no $)             -> only a TRAILING suffix is stripped
  excluded_count stops refusing               -> showing more than exist is a refusal…
  'no spec'/'no plan' rows omitted            -> a missing plan is drawn as absent, not omitted
  pair_documents never fills a slot           -> CRASH (see L5)
  git_show_files .splitlines() -> .split()    -> SURVIVED
  git_pr_history returns [] not None on error -> SURVIVED
```

**Every case the plan adds can fail, and each fails via the rule it names.** The three specifically
asked about:

* **`"the tag makes no implementation claim"`** (absence over lowercased HTML). It **can** fail:
  mutating the tag text to `"implemented"` turns it red. It is not vacuous-on-empty either, because
  `render_threads` returning `""` reds nine sibling cases computed from the same `_h`. But see M3.
* **`"a PR touching one document does not claim a fan-out"`** (absence). Making the fan-out span
  unconditional turns it red. Its weakness is wording, not vacuity — a renderer saying
  `on 1 document` (singular) passes it. The working tree already replaced it with a span **count**,
  which closes that.
* **The extra-document case.** Deleting the loop turns it red. In the working tree it is joined by
  B1's case, which cannot pass at all.

### MEDIUM M3 — the no-implementation-claim guard is blind to the one new string most likely to carry the claim

The case runs over `_h`, rendered from `_th` with `_fan = {"186": 1, "187": 1, "147": 22}`. Both of
`_th`'s PRs have a fan-out of **1**, so `fan` evaluates to `""` and **no fan-out span exists in
`_h`**. Proven by mutation:

```
  fan-out text says 'implements N documents'  -> a PR touching many documents renders its fan-out
                                                 ("the tag makes no implementation claim" SURVIVED)
```

The literal word `implements` entered the page and the assertion that no implementation claim is
rendered stayed **green**, because the only fixture it inspects never reaches the branch. The
fan-out string is the retraction's own new invention and it is outside the guard for the retraction.

The working tree replaces this case with a pin on the set of rendered tag texts:

```python
    eq("only the three measured tags can be rendered",
       sorted(set(re.findall(r'<span class="tag [a-z]+">([^<]+)</span>', _h))),
       ["docs only", "touched code"])
```

That is a genuine improvement against `shipped`/`landed` in the *tag* — and it makes M3 **worse**,
because it now inspects only text inside `<span class="tag …">`, which the fan-out span is not.
Re-run the `implements {n} documents` mutation against the working-tree suite before calling this
closed; on my transcription it survives that case too. Assert over `render_threads(_bulk, _fan)`, the
render that actually contains a fan-out.

### MEDIUM M4 — two rules the plan argues for at length have no case at all

Both survivors are in the collection layer:

* **`git_show_files` `.splitlines()` → `.split()`.** The plan devotes a ⚠ paragraph to why this must
  be `.splitlines()` (a path with a space becomes two entries, neither matching `DOC_PATH`, turning a
  documentation PR into a `code` one). Nothing goes red.
* **`git_pr_history` returning `[]` instead of `None` on failure.** This is the plan's own Global
  Constraint — *"`None` (git could not answer) and `[]` (no PRs) must stay distinguishable to the
  renderer"* — and Task 3 carries a ⛔ paragraph on it. The mutation silently converts every CANNOT
  RUN into `no pull requests`: an honest absence in place of a broken deriver, which this project's
  memory records as its most repeated failure. Nothing goes red.

The plan names both under the post-task mutation-manifest obligation, so they are *owed, not
dropped*. The point is narrower: **between Task 3 and that manifest, the None-vs-`[]` chain from git
to page has no executable check anywhere**, and the manifest is the last item of six. Either pull one
end-to-end case forward into Task 3 (inject a `show`/`log` that fails and assert the thread renders
`could not be read`), or state that Task 3 ships a rule whose only guard is a later task.

### LOW L5 — one load-bearing case kills its mutation by dying, not by reporting

`pair_documents never fills a slot` produces
`TypeError: 'NoneType' object is not subscriptable` inside the argument to
`eq("the thread names both halves", …)`. The suite aborts, prints no ratio line, and the remaining
cases never run. The mutation *is* detected — but the plan calls this case "what kills that", and a
case that dies takes 40-odd siblings with it and produces the same no-output signature as B1.
`[… for k in ("spec", "plan")]` guarded with `(t[k] or {}).get("name")` reports instead.

---

## Other findings

**MEDIUM M5 — the new markup reuses two CSS classes that are only defined as descendants of `.doc`.**
`render_threads` emits `<span class="t">` and `<span class="g">` inside `<div class="prline">`, which
sits inside `<div class="docs">`. The stylesheet defines:

```
292:  .doc .t{font-family:var(--mono);font-size:.72rem;color:var(--ink-faint);
294:  .doc .g{grid-column:1/-1;font-size:.86rem;color:var(--ink-soft);max-width:66ch}
```

`.doc` (singular) never appears as an ancestor of the new rows, and `page_chrome.chrome_css()`
defines neither `.t` nor `.g` (checked). So every PR number, date, side label and subject in the new
band renders at body size in body colour instead of small faint monospace — on 94 rows plus 11 band
headers. The plan adds `.thread`, `.thread summary`, `.prline` and three `.tag` rules and stops one
short. Add `.prline .t` / `.prline .g` (or promote both to standalone classes). The browser pass will
catch this only if someone is looking for it, so it belongs in the step-4 checklist.

**MEDIUM M6 — Task 4's Interfaces block still promises a return signature the code does not have.**

> `collect` returns a second value `fanout: dict[str, int]`

`collect` returns one value; the fan-out is attached as `a["fanout"]` on each record, and `main()`
calls `anchors = collect(...)`. An implementer who reads the Interfaces block first — which is what
it is for — writes `return out, fan` and breaks the only caller. (The second half of that sentence,
"how many anchored documents it touched", became *true* with the r2 fix and should stay.)

**LOW L6 — the fan-out loop is specified twice and it is not said that the second replaces the
first.** Task 4 adds `for a in out: a["fanout"] = fan`; Task 5 says "Set it in `collect()` beside
`fanout`" and supplies `for a in out: a["fanout"], a["head"] = fan, head`. Appending rather than
replacing is harmless but leaves dead code; say "replace the loop added in Task 4".

**LOW L7 — `pr_fanout`'s per-document `set()` is unfalsifiable.** `for num in {p["num"] for p in prs}`
dedupes within one document's history, but `prs_from_log` already dedupes by number, so no fixture
can distinguish the set from a plain iteration. Either drop it or give it a fixture with a repeated
number and say why (defence against a future `prs_from_log` that stops deduping).

**LOW L8 — the case label says three and the assertion says two.** `"only the three measured tags can
be rendered"` expects `["docs only", "touched code"]`; `unknown` is absent from `_h` and is covered by
a separate case. Rename, or add an `unknown` PR to the fixture.

**LOW L9 — an unreadable document silently depresses a number rendered on other cards.**
`pr_fanout` skips falsy histories, so a document whose git history could not be read lowers the
fan-out for every PR it would have voted for — including PRs rendered on unrelated goal cards, which
carry no `pr_error` flag of their own. `on 21 documents` and `on 22 documents` are indistinguishable
to a reader. Corpus today: **0 threads have `pr_error`**, so it is latent. One sentence in the
docstring, or render the fan-out as a floor when any history failed.

**LOW L10 — the contrast gate reads only the light block, and says "repeat" without a mechanism.**
The step-4 snippet builds `v` by last-wins over the whole file; the last `:root[data-theme="light"]`
block wins, so it always measures **light**. "Repeat for the dark block's values" has no command.
I measured all four blocks — **every pair passes in both themes**, so round 1's M3 fix is confirmed
correct, but the gate as written cannot show that:

```
light  tag 6.24:1 PASS   tag.docs 4.58:1 PASS   tag.unknown 12.09:1 PASS
dark   tag 6.34:1 PASS   tag.docs 7.19:1 PASS   tag.unknown 11.18:1 PASS
[ref] the rejected --rule/--ink-faint pairing: 2.45:1 light, 3.47:1 dark
```

`tag.docs` clears AA by 0.08 in light; worth knowing before anyone adjusts `--pending-bg`.

**LOW L11 — the fan-out annotation is on the majority of rows, which dilutes "a bulk edit is visible
as one".** Measured on the built page: **54 of 94** PR lines (57%) carry `on N documents`
(51 of 94 before the r2 fix, so this is a pre-existing property, not a regression). Only **3** of
those 54 are cases where the PR reaches nothing beyond its own thread's two documents, so the marker
is not *wrong* — it is just no longer rare enough to read as an alarm. Nothing in the verification
watches this; the `grep -c 'on 22 documents' # expect 22` check stays green either way.

**LOW L12 — `build()` now reads the filesystem.** `total_docs = sum(1 for sub in SUBDIRS for _ in
(DOCS / sub).glob("*.md"))` puts a tree walk in the renderer, whose stated job is to consume records.
It does not violate the plan's literal layering rule (which only forbids I/O *above* the collection
banner), but `excluded_count` was extracted to be testable and the number it consumes is now derived
in the one place a test cannot reach without a repo. Pass `total_docs` in from `collect`.

---

## Measurements taken, for anyone re-running this

Against the real repository, working-tree code, `HOME` redirected:

```
baseline build (unmodified script)            2.24s
with the plan applied                         9.9s – 11.2s   (4.4x – 5.0x)
anchors 11 · threads 41 · both halves 6 · extra-document threads 0
documents: 187 total in SUBDIRS · 47 anchored · 140 excluded · 0 declaring an unregistered anchor
rendered: 41 <details class="thread"> · 21 '>no plan<' · 14 '>no spec<'
          72 '>touched code<' · 22 '>docs only<' · 22 'on 22 documents' · 54 fan-out spans
          2 threads with 'no pull requests' · 0 with 'could not be read'
PRs: 57 distinct · 38 touched code / 19 docs only
last 400 commits: 256 PRs · 10 flipped code->docs-only by the widened DOC_PATH · 0 mis-tagged
                  implementations · 0 PRs tagged code with an all-markdown file list
```

The build time is worth stating plainly: **the plan's own deferred-optimisation trigger** — *"If it
exceeds ~10s, cache `git log --follow` output by `HEAD` sha before merging"* — **is already met on the
first measurement**, on a hook that fires on every write to any spec, plan, ADR or the registry. Treat
it as scheduled work, not a contingency.

---

## Verdict

**NOT-CONVERGED.**

1 Blocking, 2 High, 6 Medium, 12 Low.

The Blocking is the round-2 remediation's own new case: it crashes the suite rather than failing it,
its fixture cannot reach the branch it targets, and two of the three `rel` dereferences it was
written for are untouched. That is this repo's recorded pattern — *a round's Blockings are the
previous round's fixes misfiring* — in its purest form, and it means the branch cannot get past
Task 5.

The two Highs are both mechanical-application defects in verification the previous round wrote: an
edit that deletes a `</p>` and a grep that expects 35 where the page produces 21.

Set against that, the r2 remediation is substantially right where it matters most. The
threads-vs-documents fan-out defect, the unanchored `DOC_PATH`, the unguarded `head` call and all
three surviving retraction claims in the spec were found independently by both halves of this round
and are correctly fixed — verified by re-running, not by reading. The case-count chain is sound at
`15 → 25 → 34 → 38 → 45 → 59 → 62`, every added case can fail via the rule it names, and the round-1
contrast fix passes in both themes.

**Round 3 should attack only B1's fix and M3.** Both are absence-shaped, both are in the retraction's
own machinery, and both have now been wrong once.

---

## ADDENDUM — re-measured against the working tree after the r3 edits landed

The plan moved twice more while this review was being written. Re-run against the file as it stands
now (`15 → 25 → 35 → 39 → 47 → 62 → 65`, which the plan's own declared counts match exactly):

**B1 is HALF fixed and the case is STILL RED.** Both crash sites are gone —
`esc(d.get("rel", ""))` now appears in the spec/plan row and in the extra-document link — so the
suite reports instead of dying. Defect 2 of the three is untouched. Running the plan's own fixture
against the plan's own current `render_threads`:

```
   no crash. 'extra document' in html -> False
   CASE VERDICT: *** STILL RED ***
   rendered: <details class="thread"><summary>s <span class="absent">no pull requests</span></summary>
             <div class="prline"><span class="t">spec</span><a href="/src/">s.md</a></div>
             <div class="prline"><span class="t">plan</span><span class="absent">no plan</span></div>
             </details>
```

`named` is `{None}`; the rel-less extra document's `d.get("rel")` is also `None`; `None not in
{None}` is `False`, so it is skipped and never rendered. Task 5 step 4 says `PASS, 62/62`; it will
print `61/62`. The remaining fix is one clause: `named = {d.get("rel") for d in (t.get("spec"),
t.get("plan")) if d and d.get("rel")}`. Re-run the fixture afterwards — a missing `rel` must not be
able to alias a second missing `rel`.

**M3 is confirmed live against the current file.** Injecting `implements {n} documents` into the
fan-out span and re-running the new tag-set pin:

```
   with 'implements N documents' injected, the tag-set case sees: ['docs only', 'touched code']
   tag-set case still GREEN? True
   the word 'implements' IS on the page: True
```

The pin reads only text inside `<span class="tag …">`. The fan-out span is `<span class="t">`, so the
guard for the retraction cannot see the retraction's own new rendered string. Assert over
`render_threads(_bulk, _fan)`, which is the only fixture that contains a fan-out.
