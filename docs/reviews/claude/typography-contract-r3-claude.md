# Round 3 — `typography-contract` — Claude half (adversarial, refute mandate)

Subject: `git diff origin/master...HEAD` at `bd9e2cb3`. Nothing in the worktree was written. All
scratch work is under `scratchpad/typo-r3-tmp/`. Measurement: Chromium via Playwright,
`m2.mjs`/`m3b.mjs`, which are copies of `em-measure.mjs` with two changes. They print the worst
pair as hex. They also parse `color(srgb …)`, because the reference script silently returns
nonsense for `color-mix()` output: I saw `#0.5df7…` before fixing it. Each value is the MINIMUM
contrast over every `.ex-body b`/`strong` against its nearest painted ancestor. There are six
states: `d`/`l` = OS dark/light, `+l`/`+d` = `data-theme` pressed on `<html>`.

Sixteen constructed fragments (`typo-r3-tmp/frags/`, generator `gen.py`) were composed by HEAD's
`brief-compose.py` and by `origin/master`'s (`typo-r3-tmp/master/`). **All 16 got rc=0 from both.**

## Bet being scored (last row of `decision-log.jsonl`)

> round 3 finds no Blocking/High/Medium — no theme state below 4.5:1 for bold text on a
> role-using page or **a fragment with its own dark --em** …

**REFUTED** by M1. Fixture 13 declares its own dark `--em`, gets a live theme control and the
switcher from the composer, and measures 1.92:1 in OS-dark with nothing pressed (master: 8.45:1).

---

## M1 — Medium — `scripts/brief-compose.py:135` — the OS-dark `--em` default assumes the page went dark, so a page that stays LIGHT under OS-dark gets light-blue bold on cream

**What happens.** `@media (prefers-color-scheme: dark) { html:where(:not([data-theme="light"])) { --em: #9db8e8; } }`
applies whenever the OS is dark. Nothing pressed, the page's ground is whatever the FRAGMENT's
bare `:root` says. A fragment can have a light `:root`, both `:root[data-theme]` palettes and no
`prefers-color-scheme` block. That is "light by default, dark on a press", and the composer gives
it a live toggle (`composer_adds_control` only asks for both selectors). Such a fragment stays
light under OS-dark, and its `--em` becomes the dark-mode value:

```
fixture                       HEAD                                   master
03-pressed-only-noem          d  :1.92 #9db8e8/#fbfaf7               d  :8.45 #2d4a7c/#fbfaf7
13-pressed-only-grey-em-dark  d  :1.92 #9db8e8/#fbfaf7               d  :8.45 #2d4a7c/#fbfaf7
```

(`03` declares no `--em`. `13` declares `--em:#ffffff` in its own `:root[data-theme="dark"]`, so
it is "a fragment with its own dark --em". Both composed with rc=0 and carry `id="schemer"` plus
the theme button. The other five states are ≥ 5.74 on both.)

The fixture shape does not occur among today's 22 committed fragments: every one with both pressed
blocks also has an OS-dark block. But nothing in §2 or the composer requires that block. Codex's
r2 Medium was also a constructed fragment, so this sits on the same evidentiary footing.

**It also makes a §2 sentence false.** `explainer-delivery.md` §2 says: *"a bare `:root` (0,1,0)
wins with nothing pressed and loses on a press, which is what stops a light-only palette going
half-live."* Fixture 03 is a light palette that goes half-live with NOTHING pressed, and the new
rule is the cause. That sentence holds only when the bare `:root` happens to declare `--em`.

**Caused by which fold.** The r1 fold introduced the OS-dark default. The r2 fold kept it while
lowering its specificity, and specificity is irrelevant here because the fragment declares no
competing `--em`. So **the r2 fold did not cause it; the r1 fold did.** It sits in the same
component, `em-dark-state`, as r1's and r2's findings. By the letter of the arming condition (a
finding caused by the *previous* round's fix) this is not thrashing, because r1 was not the
previous round. It is still the third consecutive round with a finding in that component, and
the coordinator should judge that.

**Fix.** Two options were measured, plus one direction that is untested:

- ✗ *Derive `--em` from the page instead of hard-coding a hex*: `color-mix(in srgb, var(--accent) 60%, var(--fg))`
  in all three rules (`typo-r3-tmp/patched2/`). This fixes 03 (9.84/8.99) and 13, but it
  **breaks fixture 14 at 1.16:1 in OS-dark** because of M2's `--fg` cycle: an invalid `--fg`
  makes `--em` invalid. It also changes the owner's chosen hues. Not recommended as written.
- ✗ Deleting the pressed pair along with it (`typo-r3-tmp/patched/`) reopens 06 at `l+d` 1.54:1.
  That is the half-live case the pair exists for, so the pair must stay.
- ✓ *Recommended, preserves the owner's hues:* this is the shape `assert_theme_complete` already
  applies to other tokens. When the composer will add a live control, refuse a fragment whose
  bare `:root` is light and which has no OS-dark block unless that `:root` declares `--em`. The
  simpler general form: require `--em` in every palette block the fragment declares. Add a
  COMPUTED-colour case on fixture 13, which Codex r2 already asked for. The current case
  (`brief-compose.py:1225-1232`) checks spelling only and stays green on fixture 13.

## M2 — Medium (pre-existing on master, NOT caused by this branch) — `scripts/brief-compose.py:87-89` vs the fragments' `--ink:var(--fg)` — the `--prose` role resolves to NOTHING on 2 of the 4 role-using pages in the most common state

**What happens.** The shim's `:root { … --fg3: var(--ink-faint,…); --fg2: var(--ink-soft,…); --fg: var(--ink,…) }`
has the same specificity as the fragment's bare `:root` and comes later. The decision-ladder and
why-not-converging fragments declare `--ink:var(--fg); --ink-soft:var(--fg2); --ink-faint:var(--fg3)`
(their own comment says each *"resolves to THIS palette's own role"*). That makes a cycle, so all
six tokens are invalid at computed-value time in **OS light, nothing pressed**:

```
2026-10-23-topic-decision-ladder light null  {"fg":"","fg2":"","inks":"","prose":"", "body":"rgb(0, 0, 0)"}
2026-10-23-topic-decision-ladder light light {"fg":"#1b1a18","fg2":"#3d3a35",…,"prose":"#3d3a35","body":"rgb(27, 26, 24)"}
2026-10-20-topic-why-not-converg light null  {"fg":"","fg2":"","inks":"","prose":"", "body":"rgb(0, 0, 0)"}
master-ladder.html (origin/master) light null {"fg":"","fg2":"",…}   ← identical on master
```

The other two role-using pages, 2026-10-06 and 2026-10-07, declare hex values and are unaffected.
Legibility is not harmed: the result is black on cream. But §2's table row *"`--prose` | body
text | `--fg2`"* is false on those two pages in the default state, and so is everything else
reading `--fg`/`--fg3`. OS-light-unpressed then renders differently from light-pressed, which is
a half-live toggle by another route. It also blocks any `--em` fix that derives from `--fg` (M1).

**Fix.** Out of this branch's scope. File it to the backlog: drop the shim's `--fg*` aliases to
`html` (0,0,1) like `--rule`, so a fragment's `:root` wins, or forbid the reverse alias in
fragments. ⚠ The 2026-10-06/10-07 pages were not measured for the reverse direction.

## L1 — Low — `scripts/brief-compose.py:131-133` (comment added by the r2 fold): *"every fragment rule beats it"* is false for a fragment `html{}` rule

Fixture 09 declares its dark `--em:#ffffff` as `@media (prefers-color-scheme: dark){ html{--em:#ffffff} }`.
That is (0,0,1), it ties `html:where(…)`, and the shim comes later, so the shim wins:
`09-html-em-in-media  d  :2.86 #9db8e8/#666666` (master: 1.54, so this is better than master and
not a regression). §2 itself only promises the `:root`-prefixed (0,2,0) forms and a bare `:root`,
which is accurate. The shim comment overstates. **Fix:** say "every fragment `:root` rule", or put
both `--em` defaults at zero specificity (`:where(html)` / `:where(html:not([data-theme="light"]))`)
so a fragment `html{}` wins too. Caused by the r2 fold: the sentence, yes; the behaviour, no.

## L2 — Low — the headline figures *"1.90 / 2.05 / 1.90 :1"* are not the worst case (shim comment `:126-127`, backlog #226, dashboard entry)

On the `origin/master` versions of the three pages, the minimum over all bold text in OS-dark is
`1.78 #2d4a7c/#1a2620`, `1.79 #2d4a7c/#2a2118`, `1.78 #2d4a7c/#1a2620`. Bold inside tinted cards is
worse than bold on the page ground. The stated figures understate the defect and cannot be
reproduced as minima. **Fix:** quote the minima, or say "on the page ground". Introduced by the r1 fold.

## L3 — Low — `docs/dashboard-entries.md` (added by this branch): garbled sentence

*"bold words … were dark blue on a dark background, at about a less than half the minimum
readable contrast."* **Fix:** "at less than half the minimum readable contrast".

---

## The four questions

1. **Six-state sweep.** The four committed role-using pages measure ≥ 7.57:1 in every state
   (dev-process-speed 7.57–7.75, retrieval 7.87–7.98, why-not-converging and decision-ladder
   7.79–7.89). HEAD's recompose of the three changed fragments is byte-identical to the committed
   pages apart from title and stamp. Among the fragments: Codex's grey fixture is 5.74:1 in every
   dark state when it declares `--em` in all dark blocks (07). It is 2.86:1 at `l+d` when its
   pressed-dark block omits `--em` (06), the same on master, and an incomplete palette. M1's
   fixtures are the only new sub-4.5 states.
2. **Did lowering the pressed pair to `html[data-theme]` reopen the half-live toggle?** **No.**
   Measured: `d+l` is 8.45:1 on 05, 06, 07, 08 (dark `--em` in a bare `:root` inside the media
   block), 09 and 16. To reopen it, a fragment's dark-carrying rule would need specificity
   strictly between (0,1,1) and (0,2,0) and still apply under a light press. A (0,1,1) tie loses
   on source order, and (0,1,0) loses outright. No realistic selector sits in that window.
3. **§2's cascade sentences.** The specificities are correct: `html:where(…)` is (0,0,1),
   `html[data-theme=…]` is (0,1,1), the `:root[…]`/`:root:not(…)` forms are (0,2,0), and a bare
   `:root` is (0,1,0). Two sentences fail. *"…which is what stops a light-only palette going
   half-live"* is false by M1. The role table's `--prose` row is false on two pages by M2, which
   predates this branch. A side note: a fragment that writes its palettes as `html[data-theme]`
   or bare `[data-theme]` (fixtures 11 and 12) gets no theme control and no switcher, so those
   forms never reach the roles. That is outside §2's claims.
4. **Records.** Mutations 27 → 30 and the total 2003 → 2006 match `scripts/mutations/brief-compose.json`
   (30 entries; master has 27) and `check-plan-code.py`. I did NOT run `--self-test`, so the
   154-case claim is unverified here. I also did not re-verify "all 22 fragments compose with the
   same rc and controls"; my 16 fixtures did. Backlog #226 correctly stays open. Its "fixed …
   in every combination" claim holds for the three pages but not for the class (M1), and its
   figures carry L2. The r2 coordinator note's *"six theme states measured on five pages
   (min 5.74:1)"* is true of what it measured.

VERDICT: NOT CONVERGED
