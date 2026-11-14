---
name: measure-the-population-the-code-actually-sees
description: "FIRES-WHEN: about to trust a count, a filter, a grep, a negative result or a feasibility probe — measure what the CONSUMER actually sees, by calling its own parser; a filter is a hypothesis about the source's vocabulary"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 026980a1-ac42-4306-9327-ecd78a7e933b
  modified: 2026-09-09T02:09:06.506Z
---

**The rule: derive a population by asking the CONSUMER — call its own parser (`b.parse(...)`,
`g.collect(...)`), use the splitter it uses, run the guard against the real callee. Never glob the
source file, hand-copy its grammar, or trust a synthetic stand-in.** A filter, regex or `^anchor` you
wrote is a HYPOTHESIS about the source's vocabulary; the source is the authority.

Before trusting a NEGATIVE result (zero hits, "absent", "settled"), do one of:
- **check a known positive** — and confirm WHICH object matched, not merely that something did;
- **ask the source for its vocabulary** (`--jq '[.[]|.state] | unique'`) instead of listing the
  values you expect;
- **allowlist DONE, never blocklist not-done** (`status=="completed"` plus a floor on how many exist);
- **split on a content marker, not an offset**, asserting the marker occurs exactly once;
- **compare case- and whitespace-insensitively** when the medium can transform text (CSS uppercase,
  wrapped lines);
- **enumerate before reading a range** — get the item count from the document
  (`grep -nE "^#+ (H|M|L)[0-9] " <review>`) and reconcile it with what you acted on; a teammate's
  stated counts are a free falsifier.

**Why:** a renderer's blast radius is what REACHES it, not the file the text lives in; and a negative
count is the most dangerous shape — zero reads as "the feature is dead" when it usually means "my
pattern is wrong", with no output to sanity-check.

**How to apply:**
- Name the subject of every count in the same sentence ("on the rendered page", "over parsed rows",
  "per source line" are three claims).
- **The writer must ask the reader's parser, not imitate it.** The tell is a character list, regex or
  `^anchor` hand-written where the consumer has a function. ⚠ That means *whichever* splitter the
  specific consumer uses — `splitlines()` is not universally right.
- **A marker humans emphasise will appear in bold in the wild** (`**Decide:**`, `NO-ENTRY:`,
  `REVIEW GAP:`) — match with the consumer's parser, never `^marker`.
- **From a synthetic run, ask: what is the real callee's signature, and did I open it?**
- **Never wait on `pgrep -f` for a name that appears in the waiting command** — wait on a signal the
  subject emits (a completion marker, a sentinel file, `run_in_background` exit).
- **Before a feasibility probe, write the sentence it must support** and ask whether the counted thing
  could be fully present while the sentence stays false — availability is a proxy for validity.
- **A fix inside a heredoc is not a fix.** If the repair does not land in a file that outlives the
  turn (memory, script, checklist), it is an instance fix wearing the word "class".

Related: [[a-positional-read-needs-a-verified-shape]], [[check-the-assumption-not-just-the-code]],
[[a-retrospective-number-needs-provenance]], [[quote-the-code-dont-characterise-it]],
[[after-fixing-search-for-the-class]], [[a-check-result-is-not-the-claim]].

## History (condensed; every instance was written up as fact before being caught)

| date | what I measured | what the consumer saw |
|---|---|---|
| 2026-08-30 (#71) | whole `docs/adr/*.md` through each renderer: 145 emphasis spans, 17 links would render | `gen-goals-page` renders only 39 one-line `Goal:` strings: **0** — caught by generating the page |
| 2026-08-30 | "on the live page": 10 crossed spans / 15 markup-in-code (re-rendered every LINE) | page said **6 and 10**; the generator's parser **7 and 12** over 213 cells |
| 2026-09-01 (#81, shipped in PR #199) | `grep -c '^Decide:'` → 0, "the ask grammar has NEVER been used" | **10** occurrences, all `**Decide:**`; `decisions()` → 3 real decisions, 3 settled blocks |
| 2026-09-06 (#99, PR #234) | security guard `"\n" in why or "\r" in why` | readers split with `str.splitlines()`, honouring **eleven** separators — 2 of 11 covered; fixed as `len(cleaned.splitlines()) > 1`, corpus derived the same way |
| 2026-09-08 (PR #270) | `check-plan-file-tags.py` iterated `splitlines()` | `extract` iterates `split("\n")`: **8 of 9** separators disagreed, all hiding a live tag; also `read_text()` universal-newline translation made `\r` look like a disagreement in the TEST |
| 2026-09-22 (#164) | `check-fixture-variation` on a synthetic `render_banner(steps, index)` → "would be caught" | real `check-banner-armed.decide(texts, armed, steps, …)` carries the step inside `texts`: `findings=[]`. Caught by asking an agent to REFUTE ([[dual-review-what-it-catches]], [[a-filed-finding-s-proposed-fix-is-a-hypothesis]]) |
| 2026-09-26/27 | six disposable filters in one session: `grep -v RECONSTRUCTED`; a grep for a wrapped sentence; `tail -n +10` off by one; `[class*=float]` (real class `askbtn`); `includes('Sixteen of nineteen')` under CSS uppercase; `gh pr checks` filter missing **QUEUED** → "CI settled" before CI started | of ~8 instances, **2 were in memory and 6 nowhere** the next morning |
| 2026-10-04 | `until ! pgrep -f "partial-sweep.py"` — matched its own command line; "still RUNNING" reported three times; `[p]artial-sweep[.]py` matched three stale WAITERS | the output file's mtime had not moved for 23 minutes ([[a-hang-is-not-a-diagnosis]]) |
| 2026-10-05 | review read with `sed -n` ranges from a `^## ` scan while findings were `^### ` | **2 of 11 findings never read**; the teammate's "3 Mediums, 4 Lows" did not match |
| 2026-10-20 | "feasibility": 176 of 261 verdicts carry a `head`, 20 subjects ≥2 heads, 32% unresolvable | already refuted the session before; the owner: *"last session it was determined that git history doesn't give clear signal because real cause of defect cannot be known"* — confirmed verbatim in the transcript ([[the-answer-may-only-exist-in-the-transcript]]) |
