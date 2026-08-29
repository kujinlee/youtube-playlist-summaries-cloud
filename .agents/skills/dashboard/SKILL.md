---
name: dashboard
description: Record what changed in this repo as a dated dashboard entry, and regenerate the project dashboard page. Use when work has landed that a person who was away would need to know about, when a decision starts waiting on the human, when one stops waiting, or when the user types /dashboard or asks to update the dashboard. Not for explaining a code change (use explain-diff), the state of one body of work (use brief), or findings needing a file/don't-file verdict (use explain-findings).
---

# Dashboard

Append one entry to the project's append-only store and regenerate the page.

**Announce at start:** "Using the dashboard skill to record an entry."

## Why this exists

The goal (`docs/anchors.md`, anchor `status-visibility`): *a person who was away can see the current
state, what changed, and what needs them — without reading the chat transcript.*

The chat transcript is not that. It is accurate and unfollowable, it is gone after a `/compact`, and
the one thing the reader actually needs — *a decision is waiting on them* — sits in paragraph four of
the fifth message. The store is the durable answer; this skill is how a line gets into it.

`scripts/check-dashboard-entry.py` refuses a branch that changes tracked files and records no entry,
so this is not an optional nicety. A branch either has an entry or declares `NO-ENTRY: <reason>` in
its PR body — and the page **displays** the declarations, which is the only reason anyone would ever
notice the gate quietly hollowing out.

## The store

`docs/dashboard-entries.md`. **Append-only, newest at the END.**

> ⛔ **Append one block. Never edit or delete an existing one.**
>
> A correction is a **new entry**, not a rewrite. Entry ids are positional — `YYYY-MM-DD/N`, where
> `N` counts entries sharing that date in file order — so editing history renumbers ids that other
> entries already point at, and silently rebinds a standing `[resolved:]` to a different item.
> That is not a style rule; it is why the ids are stable enough to reference at all.

## The grammar

```
## YYYY-MM-DD [needs-you] [resolved: YYYY-MM-DD/N]
One plain-language line a non-engineer can read. This is the title.
Any further plain lines belong to the same entry.
<!--tech-->
Technical detail: commit SHAs, file paths, script names.
```

- **The header line carries the date and flags, and nothing else.** A title on the header line is
  rejected, as is `##YYYY-MM-DD` with no space, an impossible date, and a typo'd flag.
- **The first non-blank line after the header is the title.** A header over an empty body is
  malformed — and this is the one shape the ratchet cannot see at diff level, so it is on you.
- **`<!--tech-->` on its own line** splits the plain part from the technical part. Optional; without
  it the whole body is plain.
- **Flags are zero or more.** Both may appear; a second `[resolved:]` is kept, not discarded.

### `[needs-you]` — only when a decision is genuinely waiting

Flag an entry `[needs-you]` when **the human has to decide or do something before work can
continue**. Not for progress, not for something interesting, not to draw attention. The section
exists so that its being non-empty means something; an entry flagged because it felt important is
the one edit that degrades the page for every future reader.

### `[resolved: <id>]` — clearing one

An item leaves *What needs you* when a **later** entry names its id. Later means later **in the
file**, which is what "append" already gives you.

⚠ **Read the id off the page, not off the file.** `N` is assigned by the parser, counting blocks
that share a date — including ones you would not think of as entries. The page prints each entry's
id; that is the authority. An id naming an entry that does not exist, or one that exists but does
not parse, is an **error** on the entry declaring it, and the page will say so rather than silently
leaving the item open forever.

## Regenerate — one command

```bash
python3 scripts/gen-dashboard.py
```

It composes and writes the page, and **exits non-zero if it does not** — so its exit code is the
answer to "did that work", and there is nothing to check by hand afterwards.

> ⛔ **No `mv` glob, and no writing the page yourself.** The generator returns a fragment and hands
> it to the composer, which lifts the Ask tray verbatim from an existing page. Writing the fragment
> straight to the served path loses the tray and the charset, silently — the page still renders, and
> the reader simply has no way to ask anything back.

A `PostToolUse` hook (`.claude/hooks/regen-dashboard.sh`) runs this for you whenever the store is
written, and prints `↻ dashboard regenerated`. Run the command yourself when the page needs
rebuilding for any other reason — a new commit, a PR opening or closing — since those change the
page without touching the store.

**Anything the generator could not measure is announced on the page as NOT CHECKED, with its
reason.** A dead `git` or a missing `gh` never renders as a confident zero. If you see such a note,
that is the page working; treat it as a finding, not as noise.

## Serving, the Ask tray, the push loop, and verification

**Follow `.agents/skills/shared/explainer-delivery.md`.** It is the one description of how the page
reaches the reader and how the reader reaches back — where the file goes, serving it, arming the
push loop so the Send button is not lying, and driving every affordance before handing it over.

Do not restate any of it here. The dashboard's own delivery differs in exactly one respect: the page
has a **stable slug**, so its URL is `http://127.0.0.1:7391/dashboard` and it is regenerated in place
rather than published once per subject.
