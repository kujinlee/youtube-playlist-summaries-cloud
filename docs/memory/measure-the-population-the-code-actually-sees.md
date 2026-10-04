---
name: measure-the-population-the-code-actually-sees
description: "FIRES-WHEN: about to trust a measurement, a filter, or a negative result — Twice in one session I measured a renderer over whole FILES when the generator only ever passes it a few parsed strings — 145 predicted emphasis spans were really 0, and \\\"read off the live page\\\" was really a simulation"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 026980a1-ac42-4306-9327-ecd78a7e933b
  modified: 2026-09-09T02:09:06.506Z
---

**MEASURED 2026-08-30 (backlog #71), twice, both written into documents as fact before being caught.**

1. **145 → 0.** I fed whole `docs/adr/*.md` files through each renderer to size the blast radius.
   Fair for three of four generators — but `gen-goals-page` renders **only the one-line `Goal:`
   strings**: 39 of them, containing **zero** emphasis spans, links, code spans or bold. The spec
   claimed 145 emphasis spans and 17 links would start rendering there. The page's output does not
   change at all. Caught by **generating the page** and finding 0 `<em>` where 145 were predicted.
2. **"On the live page" was a simulation.** I reported 10 crossed spans / 15 markup-in-code as read
   from `backlog-table.html`. Those came from re-rendering every LINE of `docs/backlog.md`. The page
   itself said **6 and 10**; the generator's own parser yields **7 and 12** over 213 parsed cells.
   Three subjects, three numbers, all defensible — and I attributed one to another.

3. **⭐ 10 → 0, and it got FILED AND MERGED. 2026-09-01, backlog #81.** I reported *"`Decide:`
   appears **zero times** in `docs/dashboard-entries.md`"* and built a whole backlog row on it —
   *"the ask grammar has NEVER been used, so the settle mechanism has never fired"*. It shipped in
   PR #199. **It is false.** The true count is **10**, and the gate's own `decisions()` resolves them
   to **3 real decisions across 2 entries**; the store already rendered **3 settled ask blocks, 0
   live**, two of them predating the filing. The mechanism had worked since 2026-08-31.
   **The cause: `grep -c '^Decide:'` → 0, because every real occurrence is `**Decide:**` in bold.**
   An anchored pattern cannot see an emphasised marker. Caught only by rendering the page the row
   demanded and noticing three settled blocks where there should have been one.

4. **⭐⭐ 2 of 11, IN A SECURITY GUARD, AND THE REVIEW CAUGHT IT ONE ROUND LATER. 2026-09-06,
   backlog #99, PR #234.** A code review found that `--pause` let a newline into
   `.claude/executing-plan`, injecting a live `plan:` field so the Stop guard supervised a
   *different* plan. I fixed it with `if "\n" in why or "\r" in why`. **The next review round found
   that guard defeated by EIGHT more separators** — `\v \f \x1c \x1d \x1e \x85 U+2028 U+2029 —
   because the readers (`parse_sentinel`, `strip_field`) split with `str.splitlines()`, which
   honours **eleven**. I had hand-written a copy of the consumer's rule and covered two of them.
   Codex named the two Unicode ones; **enumerating the actual `splitlines()` set found the other
   six**. Fixed as `len(cleaned.splitlines()) > 1` — ask the function the reader calls — and the
   self-test now *derives* its separator corpus the same way, so the test cannot fall behind either.

5. **⭐⭐ THE SAME FUNCTION, THE OPPOSITE DIRECTION — I used `splitlines()` where the subject uses
   `split("\n")`. 2026-09-08, PR #270.** `check-plan-file-tags.py` exists to fence the tag grammar
   `check-plan-code.extract` used to parse, and its whole premise is *the fence and the parser must
   agree on what a tag is*. I iterated `text.splitlines()`; `extract` iterates `md.split("\n")`.
   **Eight of nine separators disagreed, every one in the direction that HIDES a live tag**: given
   `x<SEP>```\n<!-- file: m.py -->`, the separator opened a fence in my guard that never opens in
   the parser, so the tag was skipped as "fenced" while `extract()` returned `files=['m.py']` and
   my guard returned **0 findings**. Fixed to `split("\n")`; 0 disagreements across all nine after.
   ⚠ **#4 said "ask the function the reader calls" and I reached for `splitlines()` as if it were
   universally the right one.** It is only right when the *consumer* calls it. The rule is not
   "prefer `splitlines()`" — it is *use whichever splitter the specific consumer uses*.
   ⚠ And my first re-measurement said `\r` still disagreed: **a defect in the TEST**, because
   `read_text()` does universal-newline translation, so I fed `extract()` a raw string and the fence
   a translated file. Route both sides through the same read before calling a difference real.

**⚠ THE WRITER MUST ASK THE READER'S PARSER, NOT IMITATE IT.** Instances 1-3 are a *reader*
measuring the wrong population; #4 is a *writer* validating against a hand-copy of the reader's
grammar. Same root: a second implementation of one rule. The tell is a **character list, a regex, or
a `^anchor` written by hand where the consumer has a function**. Lengthening the list rebuilds the
defect one release later.

**⚠ THE EMPHASIS BLIND SPOT IS A RECURRING CLASS, not one grep.** Three instances, all 2026-09-01:
`REVIEW GAP:` (fixed once already), `NO-ENTRY:` in `**bold**` unrecognised by `check-dashboard-entry`,
and this. **A marker that humans emphasise will be emphasised in the wild** — match it with the
consumer's parser, never with `^marker`.

**Why:** a renderer's blast radius is a property of *what reaches it*, not of the file the text lives
in. Files contain headers, prose and table scaffolding a generator never passes to a renderer.
And a *negative* count is the most dangerous shape: zero hits reads as "the feature is dead" when it
often means "my pattern is wrong" — there is no output to sanity-check against.

**How to apply:** derive the population **by calling the consumer's own parser** (`b.parse(...)`,
`g.collect(...)`), never by globbing the source. And when reporting a count, **name its subject in the
same sentence** — "on the rendered page", "over parsed rows", "per source line" are three different
claims. Related: [[a-positional-read-needs-a-verified-shape]],
[[check-the-assumption-not-just-the-code]], [[a-retrospective-number-needs-provenance]],
[[quote-the-code-dont-characterise-it]].

⟳ **2026-09-22 — THE SUBTLEST FORM YET: THE RUN WAS CORRECT AND THE CONCLUSION WAS ABOUT A
DIFFERENT SUBJECT.** Writing an architecture review, I tested whether `check-fixture-variation`
would catch a frozen step number by running `analyse` on a **synthetic** function I wrote for the
purpose — `render_banner(steps, index)` — where `index` genuinely is a parameter. It flagged, as it
should. I then published, into the review AND into backlog #164, that the row's own worked example
*"would be caught"*. **The real subject is `check-banner-armed.decide(texts, armed, steps, …)`
(`:503`), where the step rides INSIDE `texts` and there is no `decide.step` at all.** Re-measured
against the real signature: `findings=[]`. The row had been right; my correction was wrong.

⭐ **The tell I missed: I never ran the guard against the SUBJECT THE ROW NAMED.** Nothing in my
transcript shows `decide` being opened before the conclusion was written. A synthetic fixture proves
what the tool does to *that fixture*; it is evidence about the real subject only if the shapes
match, and "does this quantity appear as a parameter?" is precisely the shape that differed.

⭐⭐ **Ask, before writing any conclusion from a synthetic run: *what is the real callee's
signature, and did I open it?*** If the finding is about whether a tool SEES something, the
synthetic and the real subject must agree on the structure that decides visibility.

Caught by asking an idle agent to REFUTE the finding rather than confirm it — an adversarial prompt
found in minutes what a confirming one would have ratified. See [[dual-review-what-it-catches]] and
[[a-filed-finding-s-proposed-fix-is-a-hypothesis]].

---

## ⟳⟳ 2026-09-26/27 — SIX instances in ONE session, and the repair I announced each time was DISPOSABLE

⛔ **This is the session's dominant defect and the one I handled worst.** Six distinct instances, each
"fixed" inside a throwaway heredoc or one-off bash line, so **nothing survived the tool call.** Measured
the next morning when the user asked what I had done to stop repeating it: of ~8 instances, **2 were in
memory and 6 were nowhere.**

| # | the filter I wrote | what the source actually emits | cost |
|---|---|---|---|
| 1 | `grep -v RECONSTRUCTED` to exclude a file | a `backlog.md` row mentioning **both** terms on one line | hid the very site I was enumerating |
| 2 | `grep -c "statement about the local figure's…"` | the sentence **wraps**, so no single line contains it | reported present text as absent |
| 3 | `tail -n +10` for a 10-line header | off by one; kept a blank line | reported a reviewer's testimony as **ALTERED** |
| 4 | `[class*=float]` for the selection floater | the element's class is **`askbtn`** | declared a working affordance broken |
| 5 | `txt.includes('Sixteen of nineteen')` | CSS `text-transform: uppercase` → `innerText` returns **SIXTEEN OF NINETEEN** | declared rendered content missing |
| 6 | `select(.state=="PENDING" or "IN_PROGRESS")` on `gh pr checks` | a **QUEUED** check is neither, and `verify` had not appeared yet | **"CI settled" while CI had not started** |

⭐ **THE ONE-LINE RULE, and it is the same for all six:** *the filter is a HYPOTHESIS about the source's
vocabulary; the source is the authority.* Before trusting a negative result, do one of:

- **check against a known positive** — a case you are certain about. #4 and #5 both died to this in one
  step (`observer-family`'s answer was known; the label was on screen).
- **ask the source for its vocabulary** rather than guessing it — for state machines, enumerate what
  actually appears (`--jq '[.[]|.state] | unique'`) instead of listing the values you expect.
- **invert to an allowlist of DONE**, never a blocklist of not-done — #6's fix. `status=="completed"` for
  all, plus a floor on how many checks must exist.
- **split on a content marker, not an offset** — #3's fix, asserting the marker occurs exactly once.
- **compare case- and whitespace-insensitively** when the medium may transform the text — #2, #5.

⛔ **AND THE PART THAT MAKES THIS ENTRY DIFFERENT FROM THE FIVE ABOVE IT: a fix inside a heredoc is not a
fix.** I wrote a no-stray-pipe assertion for a markdown row, congratulated myself on a "class fix", and it
evaporated with the tool call — then the *same* pipe defect recurred within the hour because the second
occurrence was a different command. **If the repair does not land in a file that outlives the turn — a
memory, a script, a checklist — it is an instance fix wearing the word "class".** Related:
[[after-fixing-search-for-the-class]], [[a-check-result-is-not-the-claim]].

⟳ **2026-10-04, AND IT COST THREE WRONG PROGRESS REPORTS — a watcher that matched ITSELF.**
`until ! pgrep -f "partial-sweep.py"; do sleep 60; done` can never terminate: `pgrep -f` matches on
the **whole command line**, and the waiter's own command line contains the string `partial-sweep.py`
inside its quoted pattern. So the loop found "a process" forever, I reported *"still RUNNING"* three
times, and a stale waiter from an earlier sweep had been spinning on the same bug for over an hour.
The real signal was the output file's **mtime**, unchanged for 23 minutes.

⛔⛔ **AND THE KNOWN-POSITIVE CHECK THIS FILE PRESCRIBES WAS ALSO WRONG.** I ran
`pgrep -f "[p]artial-sweep[.]py"`, got three PIDs, and read that as *the pattern finds the real
sweep*. All three were the stale **waiters** — the bracket trick protects the pattern, not the
haystack, and their command lines held the unbracketed literal. **A known-positive check is only
evidence if you confirm WHICH object matched**, not that something did.

**How to apply:** never wait on `pgrep` for a process whose name appears in the waiting command.
Wait on a signal the subject itself emits and the watcher cannot contain — a completion marker in
the output (`until grep -q "^elapsed" out`), a sentinel file, or the process's exit via
`run_in_background`. See [[a-hang-is-not-a-diagnosis]].
