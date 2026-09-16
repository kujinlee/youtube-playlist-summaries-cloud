# Round 3 — `seed-explainer-serve-manifest` — coordinator

```yaml
round: 3
fixes_nontrivial: true
subject: seed-explainer-serve-manifest
halves:
  claude: ran
  codex: gap
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: questions-write, disposition: fixed}
  - {id: M1, severity: Medium, aim: instrument, fix_induced: true, component: regenerate, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: true, component: case-naming, disposition: fixed}
  - {id: M3, severity: Medium, aim: instrument, fix_induced: true, component: stale-endpoint, disposition: fixed}
  - {id: M4, severity: Medium, aim: instrument, fix_induced: false, component: reload-client, disposition: filed}
  - {id: M5, severity: Medium, aim: deliverable, fix_induced: false, component: send-headers, disposition: fixed}
  - {id: L1, severity: Low, aim: instrument, fix_induced: false, component: revision-ordering, disposition: filed}
  - {id: L2, severity: Low, aim: instrument, fix_induced: false, component: safe-path, disposition: filed}
  - {id: L3, severity: Low, aim: instrument, fix_induced: false, component: dead-code, disposition: filed}
  - {id: L4, severity: Low, aim: instrument, fix_induced: true, component: bind-shape-case, disposition: filed}
  - {id: L5, severity: Low, aim: instrument, fix_induced: false, component: index-chrome, disposition: filed}
```

## REVIEW GAP: codex — timed out a THIRD time; this branch will merge with no Codex pass

`gpt-5.5: try_next — timed out`, `gate_ran=false`, recorded in
`docs/reviews/verdicts/seed-explainer-serve-manifest-r3-codex.verdict.json`. The wrapper again wrote
no review rather than a partial one, and this time took nothing with it (round 1's failure path
quarantined seven of the concurrent reviewer's files).

⚠ **Three attempts, three timeouts. State it plainly: this branch has had three rounds of
SINGLE-half review, not three rounds of dual review.** Each round used a fresh independent reviewer
with an adversarial mandate, and they were productive — rounds 2 and 3 each found a High against the
previous round's own work. But `docs/plugins.md` records that the two halves catch *different
classes*, and that diversity is what is missing. Worth re-attempting before any further work on this
file; not worth blocking on, per the standing fallback rule.

## The attribution audit came back CLEAN — the pre-commitment is NOT triggered

Round 2's coordinator pre-committed that a **third** fix-induced attribution defect would mean
stopping. The reviewer audited all 36 entries explicitly:

> all 36 manifest entries kill, and all 36 kill the case they name, by an exact plain-`False` match,
> zero by exception.

So the manifest does not lie, and the branch continues on its merits rather than on a technicality.

## H1 — HIGH — `/questions` could record nothing and answer `{"ok": true}`

`scripts/explainer-serve.py:1241`. **fix-induced: yes** — round 2's M5 added seven cases to
`do_POST`'s *preamble* and none to its *success arm*.

`question_text`'s docstring is the longest justification in the file and its subject is one measured
incident: a POST answered `ok: true` and appended "(empty)", so *"the caller had no way to learn its
words were gone"*. **Eight cases guard the empty-question half. Zero guarded the write.** Measured,
each alone at **188/188 SURVIVED**: deleting the append; `"a"` → `"w"` (truncating every past
question); deleting the `mkdir`; the success body becoming `{"ok": false}`.

⭐ **Third depth of one mistake on this branch.** Round 1 cased one clause of a four-clause verdict.
Round 2 cased the 504 arm and not the 500 arm three lines below. Round 3: the preamble and not the
success arm. *After fixing, SEARCH for the class* — and each time the miss was one level away from
where the fix landed.

**Fixed** with four cases that **read the file back**. Asserting the reply is exactly what the
2026-08-17 incident proved insufficient. ⚠ They build a sandbox `ROOT`/`QUESTIONS`, because the real
ones live under the reader's `$HOME` and a case writing there would both assert the ambient world
and touch the reader's file.

## M1, M2, M3, M5 — fixed

- **M1** the seven allow-list cases call `_regenerate` **directly**, so nothing proved
  `POST /regenerate` reaches it — changing the route literal survived 188/188, and a real POST would
  have fallen into the questions arm. The argument was cased at the function, not at the wiring.
  One case, reusing both drivers, asserting the recorded argv.
- **M2** ⭐ **two of my case NAMES claimed properties the cases structurally cannot test.** (a) *"not
  an unhandled KeyError on the suffix map"* — the fixture 404s one line above the map and never
  reaches it; the map cannot be reached by an unknown path at all. (b) *"undecodable bytes … not an
  unhandled UnicodeDecodeError"* — a lenient decode survives, because `json.loads` raises on the
  replacement characters anyway, so the 400 comes from the parser either way. Neither had a manifest
  entry, so neither lied to the ratchet — but a case name is a claim, and both overstated. Renamed to
  what they test.
- **M3** `/_stale`'s fixture declared **one** source, which makes `max` and `min` the same function:
  `max` → `min`, and dropping the `is_file()` filter, both survived. The fixture now declares three
  sources — one newer, one older, one **missing** — and requests both the bare slug and the `.html`
  form, because `.removesuffix(".html")` was unexercised by every case that asked for the bare slug.
- **M5** `_send`'s Content-**Type** value was unasserted; a hardcoded `"text/plain"` survived, i.e.
  every page in the server served as plain text with nothing going red.

## M4, L1–L5 — FILED as backlog #130, and why the line is drawn here

⭐ **M4 is the sharpest thing in the round and it is still filed, deliberately.** Six documented
decisions in the injected live-reload client each survive, because **every case asserts a token is
present in the source STRING rather than that the client behaves**: deleting the injection entirely;
injecting it into `.png` responses; dropping `busyTyping()` from the reload guard (a reload eats a
half-typed question); folds restoring by POSITION instead of id — *the exact bug that comment names*
— passing because the case asserts the absence of the token the **old fix** introduced;
`MISS_LIMIT = 3` → `1`, whose comment says **⛔ NOT 1**; and `indexOf('stale') === 0` → `!== -1`.

Casing it needs a delivery-level harness — a JS engine, or executing the injected script — which is
a **new mechanism**, and `review-method.md` Q3 says a Medium needing a new mechanism is **filed**,
not smuggled into the branch in flight.

**The boundary, stated rather than drifted into.** Round 3 applied 151 mutations and found **78
survivors**; 77 sit outside backlog #129's process layer. Rounds 2 and 3 each found roughly the same
proportion. ⚠ **That is not a failure to converge — it is what "cover a 2,100-line file" looks like,
and it has no endpoint.** The signal that **#122 itself is complete** is a different one: its stated
work was *seed a manifest, add the key, raise the declared sum* from four named candidates, and there
are now **42 entries with a clean attribution audit**. Raising coverage further is a real job and it
is **backlog #130**, filed as #122's *successor, not its reopening*.

## Evidence

`python3 scripts/check-plan-code.py --mutate .` — **685 mutations, 685 killed, 685 attributed to the
case each names, 0 survivors**, every control proved green first. Suite **188 → 196**, manifest
**36 → 42**, declared total **679 → 685**. Fourteen gates green, including under the non-existent
`$HOME` the harness spawns with.

## Q4 / Q5

**Convergence: reached for THIS branch's subject.** Q4(a) asks whether discovery has dried up *on the
thing under review*. Every remaining finding is aimed at the **instrument** and is recorded in #130;
the deliverable findings this round (H1, M5) are fixed and re-measured. The attribution audit — the
property #122 exists to establish — is clean at 42/42.

**Q4(b) tree identity:** no code changed after the sweep that produced 685/685/685/0. The review docs
and backlog rows written afterwards contain no code.

**Thrashing: not armed.** H1, M1, M2 and M3 are fix-induced, but in **four different components**
(`questions-write`, `regenerate`, `case-naming`, `stale-endpoint`) — the rule needs two consecutive
rounds in **one**. `manifest-attribution`, which thrashed in rounds 1–2 and carried the
pre-commitment, came back **clean** this round.

⚠ **One pattern is worth naming even though no rule fires on it: the same mistake at three depths in
three rounds** — a clause, an adjacent `if`, an adjacent arm. It is the argument for #130 being
worked with a sweep rather than finding-by-finding.
