#!/usr/bin/env python3
"""Render `docs/backlog.md` as a browsable HTML page at a STABLE url.

    python3 scripts/gen-backlog-page.py          # → ~/explainers/backlog-table.html
    python3 scripts/gen-backlog-page.py --self-test  # 164 cases
    open http://127.0.0.1:7391/backlog-table     # after scripts/explainer-serve.py

WHY THIS EXISTS
---------------
`docs/backlog.md` is 55 rows of dense prose in a six-column markdown table, and the question people
actually ask of it — *"what is left, and what are these things?"* — is not answerable by reading it
top to bottom. Asked twice on 2026-08-21, the second time explicitly: *"list out remaining backlogs
with their descriptions so that I can understand what are they."*

A `/brief` page cannot hold this. A brief is a DATED SNAPSHOT of one moment that needs a decision;
the backlog is a STANDING CATALOG that outlives every brief. Folding one into the other means the
next brief either duplicates 41 rows or silently drops them, and `/latest` moves the moment another
brief is written. Hence a separate page at a fixed address that a bookmark can hold.

THE FILENAME IS THE URL CONTRACT
--------------------------------
Written to `~/explainers/backlog-table.html` — no date prefix, deliberately. `explainer-serve.py`
serves `/backlog-table` from it and, because the name is undated, EXCLUDES it from `/latest`, so
regenerating this page never steals the bookmark that points at the newest brief. Regeneration also
lands in place, which means the server's live-reload poller refreshes any open tab by itself.

WHAT IS DERIVED AND WHAT IS WRITTEN BY HAND
-------------------------------------------
Everything except `GROUPS` is parsed from `docs/backlog.md` in this run — counts, statuses, sizes,
the full text of every entry. Nothing is summarised from recall; this project has measured what that
costs (`docs/backlog.md` #49, and the five-row cost table where four rows were unsupported).

`GROUPS` is the exception and is honest about it: a plain-English line per open item, grouped by
what the item IS rather than by how loud its severity marker is. Severity ordering actively hides
the most important fact in the list — that six of the high-severity items are ONE problem wearing
six numbers.

Its COMPLETENESS is not at stake, because GROUPS is not how an item reaches the reader — every
row gets its own card from the table regardless. Measured 2026-09-11 by deleting a group and
re-rendering: the member kept its card and the count did not move. That is what made backlog
#90's clause 0 possible — grouping is OPT-IN, an ungrouped open item is NORMAL rather than a
debt, and anything no group names is enumerated under "The rest, one line each".

⛔ THIS NO LONGER REFUSES, AND THAT REVERSES THE ORIGINAL TRADE (user's decision, 2026-09-09:
*"refusing refresh is not appropriate"*). The old contract said "a loud stop beats a quiet
omission". MEASURED: the stop was not loud. GROUPS named three items that closed on 2026-09-01/04,
the build raised, and — because NOTHING CALLS THIS GENERATOR — the page simply stayed at its
2026-09-04 12:38 state through 21 commits, looking exactly like a current one. A stale grouping now
costs a ⚠ line and an on-page notice; the view is always rebuilt.

A NOTE ON THE OPEN/CLOSED RULE
------------------------------
Not reimplemented here. `CELL_SPLIT` is imported from `scripts/check-docs.py` and the same test is
applied — Status cell, closed iff it contains a check mark — so this page and the marker ratchet
cannot disagree about what is open. The two tables in the file have DIFFERENT column counts, so each
row is read against its own header rather than a fixed width; a positional read that assumed one
shape is exactly how #46 and #50 were once closed while both were open.
"""
from __future__ import annotations

from typing import Callable, Sequence

import argparse
import contextlib
import html
import os
import inspect
import io
import importlib.util
import pathlib
import re
import subprocess
import datetime as _dt
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import page_chrome  # noqa: E402
import page_markup  # noqa: E402
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
BACKLOG = REPO / "docs/backlog.md"
DEFAULT_OUT = pathlib.Path.home() / "explainers" / "backlog-table.html"


def _cell_split() -> re.Pattern[str]:
    """Borrow the row splitter from the ratchet that owns it, so there is ONE definition of where a
    table cell ends. `\\|` inside a cell is an escaped literal, not a column boundary, and three
    rows of the backlog contain one."""
    spec = importlib.util.spec_from_file_location("check_docs", REPO / "scripts/check-docs.py")
    if spec is None or spec.loader is None:                       # pragma: no cover - unreachable
        raise RuntimeError("cannot load scripts/check-docs.py — refusing to guess the split rule")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CELL_SPLIT


CELL_SPLIT = _cell_split()

SEVERITY = {"🔴": "crit", "🟠": "high", "🟡": "med", "🟢": "low", "✅": "done"}
SEV_NAME = {"crit": "critical", "high": "high", "med": "medium", "low": "low",
            "done": "closed", "none": "unmarked"}


# ─── THE GROUPING — interpretation, checked for completeness but not for truth ───────────────────
SUMMARIES: dict[int, str] = {
    17:
        'The background worker and the sync process can write at the same time with nothing '
        'stopping them. On one path that destroys paid content, not just a pointer.',
    19:
        "When a video moves between playlists, a worker finishing late can overwrite the winner's "
        'content with stale content.',
    20:
        'Renaming a video orphans all of its dig-deeper documents — only half the address is '
        'protected.',
    21:
        'Dig-deeper writes have the same stale-address exposure but write somewhere else, so they '
        'need their own fix.',
    22:
        'When a video is re-addressed, the “this was paid for” status does not reliably follow it — '
        'the database row carries no stable identity to hang it on.',
    25:
        'Rendered pages and PDFs have no identity of their own either. Two designs for one have '
        'already been refuted, so this needs a fresh pass.',
    60:
        'Corrections you type never reach a summary the background worker regenerates on its own — '
        'and the row claims they were applied. Fixing it is blocked by the same overwrite problem '
        'as the items above: the corrected version can be thrown away while the record still says '
        'it exists.',
    30:
        'TRUNCATE — delete everything in a table — is granted to the anonymous and signed-in roles '
        'on all five money tables. Row-level security does not cover that verb.',
    33:
        'Anonymous callers hold EXECUTE on nearly every database function. Each migration says '
        '<code>revoke … from public</code>, which reads like “anonymous excluded” and is not.',
    54:
        'The durable fix. The detector half shipped on 2026-08-21; the half that revokes the '
        'default changes production grants and is waiting on your go-ahead.',
    26:
        'Two different retry ceilings could govern a paid job — one attempt, or five. The function '
        'that used to decide was deleted; nothing decides now.',
    27:
        'A summary that a paid dig was built from is currently pinned for the life of the '
        'workspace. Decide whether cleanup is ever allowed to release it.',
    28:
        'If reserving budget times out, 6¢ is stranded permanently and an attempt is burned. '
        'Introduced by the serve-path work this month.',
    61:
        'Cloud corrections will record what they spent <em>after</em> the call rather than '
        'reserving it first — a deliberate choice to keep the first slice shippable. This adds the '
        'reservation, and a check that the spending bound still covers everything the job pays for '
        'once corrections run inside it.',
    62:
        'A correction that FAILS still pays Gemini, and nothing records it — so neither the '
        'per-person daily limit nor the overall spending cap ever sees that money. Measured in '
        'production: the spend table was empty after a real failed press. Corrections can be made '
        'to fail on purpose, so this is a way to spend past a limit rather than an accounting '
        'rounding error.',
    63:
        'When a correction fails, the person who was just charged sees the internal error text '
        'rather than anything they can act on. The friendly-message mechanism already exists a few '
        'lines away in the same function.',
    32:
        'Each local folder records which cloud it last synced with. Point it at a different cloud '
        'and sync uploads nothing, forever, without complaining.',
    1:
        'Deep-dives serve a stale cached copy and silently always regenerate, with no progress '
        'indicator. Bring them level with summaries.',
    2:
        'Re-summarising leaves the PDF stale. Decide: keep generating PDFs, or make the HTML '
        'printable and drop them.',
    3:
        'Clickable timestamps inside deep-dives, jumping to the right moment in the video.',
    8:
        'Reframe the deep-dive from a separate document into an expandable detail view under each '
        'summary section. Large, and explicitly “someday”.',
    12:
        'Share links currently carry the summary only — a dig-deeper cannot be shared.',
    15:
        'Generate the magazine-style rendering when a video is ingested rather than on first view, '
        'so the first view is not slow and sharing always works.',
    23:
        'Corrections you write are handed to the model as free-form instructions, and a fresh '
        'summarise can silently drop them while reporting success. Make them exact find-and-replace '
        'pairs instead.',
    24:
        'Slide placeholders in cloud dig-deepers render as captions with no link. Make them '
        'clickable timestamps.',
    51:
        'Feasibility study: summarise a single video without having to create a playlist first.',
    52:
        'Split a large playlist into focused smaller ones, with the same video allowed in several — '
        'and decide whether they can share one paid summary.',
    4:
        'A markdown edge case: a closing code fence carrying a language name is accepted.',
    5:
        'The colour palette is copy-pasted between two renderers; extract it once.',
    6:
        'The gold “lead” line is over-emphasised and competes with the section heading.',
    7:
        'Bold bullet labels usually just repeat the first words of the sentence. Drop them.',
    18:
        '32 of the 42 installed skills have never once been used. Audit, trim, and find out why the '
        'wanted ones never fire.',
    40:
        'Package the explainer tooling as an installable plugin so a new project gets it without '
        'copying files.',
    47:
        'A knowledge graph over document fragments, so prior work is found rather than remembered.',
    49:
        'A checker that resolves every <code>file:line</code> a spec cites — eight were wrong in a '
        'single document.',
    50:
        'Refine the <code>/brief</code> skill — the page this one is a sibling of.',
    56:
        'Render the launch roadmap as a standing page like this one, deriving its ticks from git '
        'rather than trusting them, so “where are we overall” stops being a hand reconciliation.',
    57:
        'A page over the 690 review documents, surfacing the one number that predicts a runaway '
        "review — how much of each round was caused by the last round's fixes — while it can still "
        'change a decision.',
    58:
        'Every gate in one place: what it is, what it last returned, and which have never failed — '
        'because a gate that cannot fail is the one to distrust.',
    89:
        'These pages exist so you can see what is going on, but building one costs the main '
        'conversation dearly — nearly a megabyte of single-use scaffolding for one page, all of it '
        'worthless once the link exists. Building them in a forked side-conversation instead is the '
        "idea. What is undecided is who delivers the link, how a reader's question gets back to the "
        'session that wrote the page, and what happens when the inherited context goes stale '
        'mid-build. Only the four agent-written pages are candidates — the three rebuilt by hooks '
        'already cost nothing.',
    103:
        'Ask a question on one of these pages and the answer comes from whichever session is '
        'running now, not the one that wrote the page. The listener outlives the session it '
        'belonged to, so a reader can be answered by a stranger.',
    105:
        'The dark-theme fallback in the page builder describes itself as supplying only what nobody '
        'else supplied. That is true of any one colour and misleading about the set: declaring some '
        'of them and not the rest gives a page a half-working theme switch, which measured as dark '
        'text on a dark background — worse than declaring none at all. Declare the whole palette or '
        'none of it, and the comment should say so rather than let the next author find out by '
        'shipping it.',
    101:
        'A pull request based on another branch runs no checks at all, and the answer it gives — '
        '“no checks reported” — sits in exactly the place a green tick would. Two such requests '
        'were one keystroke from merging with nothing behind them; only the habit of treating '
        '“cannot run” as a failure caught it.',
    111:
        'The hook that protects the session handoff decides whether to act by reading what an '
        'interpreter prints. An interpreter that fails to start, or that prints a greeting first, '
        'yields neither expected answer — and the hook then does nothing at all, silently, for the '
        'rest of the session. Its sibling was repaired exactly this way ten days ago; this is the '
        'copy that was left behind.',
    # ⚠ "on every run", NOT "beneath a green verdict" — r2 finding. The gate DOES exit 1 when
    # a round is genuinely incomplete (the reviewer demonstrated it), so tying the warning to
    # a green verdict states something false on the runs that matter most. The durable claim
    # is that the line prints every time and nobody acts on it.
    112:
        '569 files in the review folder carry no round number and sit outside the check that audits '
        'review rounds, which says so on every single run, under whatever verdict it reached. '
        'Nobody can currently say what fraction of the corpus it covers. Silencing the warning is a '
        'legitimate outcome — the work is to classify the 569 and then decide, not to assume they '
        'all need covering.',
    16:
        'After a deploy, a browser tab left open keeps running the old JavaScript with no “refresh '
        'available” prompt.',
    29:
        'A guard-coverage checker only inspects the parked schema, so the guards in real migrations '
        'are invisible to it.',
    38:
        "Extract the sidebar's load/refresh state machine into a hook — a reviewer, asked directly, "
        'said the current version was not worth its complexity.',
    39:
        'Roadmap items are identified by their position, so renumbering silently changes what an '
        'old reference means.',
    41:
        'The prod read-only smoke. Built and green on 2026-08-21 — this row has simply not been '
        'closed yet.',
    42:
        'Next.js says <code>middleware</code> is deprecated on every startup. It is the '
        'authentication gate, so this is read-the-guide-first work.',
    45:
        'Leftover medium and low findings from a review round, presented for your decision rather '
        'than fixed.',
    46:
        'Normalise unusual Unicode in titles before building a filename, so characters that fold '
        'into path syntax never reach the address.',
    53:
        'You can verify which release is live, but not which commit it was built from. Deliberately '
        'dormant until its trigger fires.',
    66:
        'Ninety-two written notes from past work sessions exist on one machine, are excluded from '
        'git, and have no backup. Nobody has decided whether they are worth keeping. The expensive '
        'part of that folder was already reclaimed; this is the residue, and the decision is yours.',
    67:
        "Two helpers working at the same time can corrupt each other's results — measured twice, "
        'once producing a false alarm that was filed as a blocking defect before anyone traced it, '
        'and once nearly swallowing uncommitted work. Most of the danger has since been engineered '
        'out. What is left is that the warning about it sits in a comment inside one script, names '
        'two scripts that no longer exist, and is absent from the document where the decision to '
        'run two helpers is actually made.',
    72:
        'The inventory that polices our safety checks cannot see one that is not NAMED like one. It '
        'says in writing that it catches a check even before anyone wires it up; that second route '
        'is unreachable, and was measured to be.',
    73:
        'A superseded piece of that same inventory is still in the file, and the only thing that '
        'still runs it is its own test — so part of its reported coverage is of machinery nothing '
        'uses. Waiting on the decision above.',
    85:
        'Three separate pieces of that same machinery each work out for themselves what a code '
        'block is, and only one of them is the shared version. Nothing is broken today and the part '
        'the page uses is the correct one — but these copies have already disagreed twice, once in '
        'a way that made a real question invisible.',
    86:
        'The repair to the branch-cleanup command sits in files that a plugin update will quietly '
        'stop reading, so one day the command goes back to reporting “nothing to clean up” on a '
        'repository full of dead branches — and reads as success. The durable copy now lives in '
        'this repository; what is left is confirming whether it actually takes precedence over the '
        "plugin's own version.",
    # ⚠ NO COUNTS IN THIS SENTENCE, ON PURPOSE. The first draft copied the row's dated
    # measurement — "25 values including a bare question mark" — into prose that reads as
    # present tense. Re-measured 2026-09-11: 27 values, and the question mark is gone. A
    # number in prose has no owner and goes stale silently; a SHAPE claim ("letters are
    # still being used as groupings") stays true until someone fixes it and is visibly
    # false the moment they do.
    90:
        'One table holds goals, defects and one-line chores at once, and its grouping column has '
        'decayed into values that are not groupings at all — single letters, and a bare dash. The '
        'deeper cost is measured rather than argued: several reasonable ways of counting the same '
        'rows disagree about how many items are open, because a status cell is append-only with its '
        'verdict at the END, so a reader taking the first marker it meets gets the original filing '
        'rather than the current state. Every headline count of open work is a range until that is '
        'settled.',
    94:
        'A guard that stops a session mid-plan promises in writing that it can block at most once. '
        'It relaxes only when the turn it interrupted was one it caused itself, so a turn beginning '
        'after a background notification is blocked again — three times in one session, while '
        'legitimately waiting on dispatched work. The behaviour is correct; the description of it '
        'is not, and no escape is offered for the case that actually arose.',
    92:
        'The reviewer wrapper watches a folder for changes during a run and attributes whatever '
        'appears to the reviewer it launched. It can see that the folder changed, never who changed '
        'it — so when both review halves run at once, which is the documented way to run them, it '
        "accuses one of writing the other's file. The false accusation is then written into the "
        'verdict file the build reads. Note the direction: this is a check reporting a failure that '
        'is not real, which is why it does not belong with the ones whose failures look like '
        'passes.',
    93:
        'Two checkers look near-identical and differ on purpose. Merging them — the obvious tidy-up '
        '— silently reinstates a defect that was already fixed, and every gate still passes, so the '
        'trap is laid for whoever cleans up next.',
    # ⚠ "item 100", not "the problem above". The first draft said ABOVE and it was measured
    # FALSE: `ordered` sorts by `dep_rank` before the number, so #104 renders ahead of #100.
    # A spatial word in a description is a claim about a layout the description does not
    # control — reference the item by number, which the renderer cannot reorder away.
    104:
        'The gate that holds work until a plan has been reviewed can only be cleared by that review '
        'converging. A plan that instead ships by a better route leaves the gate armed '
        'indefinitely, blocking unrelated work and directing whoever trips it to go and review a '
        "document that has explicitly disclaimed its own authority. Note the direction: this repo's "
        'usual failure is a gate claiming success it has not earned, and this is a gate reporting a '
        'failure it cannot withdraw. Decide first whether it is item 100 in this same group wearing '
        'a second number.',
    100:
        'The small file recording which plan is running is written by one program and read by three '
        'others, each carrying its own idea of the grammar, and nothing anywhere lists which '
        'combinations of its fields are legal. Nothing is broken today — all three known failures '
        'are fixed — but they were one cause wearing three faces, so this wants a design pass '
        'rather than an edit.',
    107:
        'One message covers two different reasons the mutation harness withholds a coverage figure, '
        'so a reader cannot tell which of them happened. The obvious way to separate them re-adds '
        'the exact thing an earlier slice spent three rounds removing, so any proposal has to say '
        'how it avoids that.',
    108:
        'The mutation harness required a piece of code to be split in two so it could be measured. '
        'That split was an improvement, but next time it may not be, and “the tool needed it” will '
        'read as a reason. Write down which of the two should yield.',
    109:
        'A test that guards a line of code is attached to that line BY ITS TEXT, so improving the '
        'wording detaches it. The test still exists, still passes, and no longer guards anything. '
        'Only a full sweep finds these; it has happened five times.',
    113:
        "The program that builds this page has five mutation tests to its sibling's sixty-four, and "
        'that number came from what one branch happened to fix rather than from the file. What the '
        'gap cost has been counted: four review rounds turned up 1, then 9, then 8, then 15 fresh '
        'tests that could never fail — every one of them found by a person reading, none by a '
        'machine.',
}

# ⛔ THE INDEX'S WORDS ARE PINNED, IN TWO FILES THAT MUST AGREE — and r1's High is why. The first
# version of this claimed that keeping the index OUT of `GROUPS` was a mechanical barrier against
# the retired bin returning as framed prose. The reviewer refuted it by measurement: rewriting this
# dek into a catch-all framing claim left the suite at 164/164 and the guard at exit 0. What stopped
# it was review discipline wearing the word "mechanical".
#
# Now `check-group-claims.py` holds its own copy of both strings and REFUSES when they diverge, so
# changing them is a deliberate act touching two files.
#
# ⛔ THAT GUARDS THIS FIELD, NOT THE PAGE. r2 found the broader claim false too: prose emitted
# ELSEWHERE — the preface above the groups, or new markup around this section — could characterise
# the index without touching either string. No fourth mechanism is being added for it, because
# nothing can stop prose from characterising something and each partial fix invites the same
# finding again. The scope and the residue are written out in `check-group-claims.py`'s docstring.
INDEX_TITLE = "The rest, one line each"
INDEX_DEK = ("No claim here — these open items simply belong to no group, which is the normal "
             "case. Anything with a summary shows it; anything without shows just the row. Both "
             "are fine.")

GROUPS: list[tuple[str, str, str, list[int]]] = [
    # ⭐ FOUR FIELDS NOW: title, framing, FALSIFIER, members — the policy on backlog row #90,
    # adopted 2026-09-11. The falsifier is a FIELD rather than a sentence buried in the prose so a
    # script can check it exists and, where it names a column, evaluate it. The repo already uses
    # this grammar (`NO-CALLER:`, `NO-ENTRY:`, `REVIEW GAP:`).
    #
    # ⛔ A GROUP IS A CLAIM, A TAG IS A LABEL. A tag ("what is this about?") is derived from the
    # Bundle column and cannot be wrong, only useless. A group asserts something about a SET and
    # CAN be wrong — that is the whole difference, and it is why groups are hand-written and
    # OPT-IN. An item needs no group. It needs no summary either.
    #
    # ⚠ ANSWERS IS KEYED BY GROUP POSITION, so retiring a group above one that has answers moves
    # them onto the wrong group in silence. Backlog #39's class exactly. Only position 1 carries
    # answers today and it is still position 1; check this before reordering.
    ("Paid work can be lost when a video's address changes",
     "Every summary is filed under a name built from the video's title, so changing the title "
     'changes the address — and not everything pointing at the old one follows. Summaries cost real '
     'money, so losing one loses money. Six items, one root cause; they were split apart during the '
     'addressing work when a single fix kept failing review.',
     'a member whose root cause is not the address changing under paid work',
     [17, 19, 20, 21, 22, 25, 60]),
    ('Anonymous users hold more database access than intended',
     'All measured in production, and none of it currently reachable through the web API — but the '
     'grants are real, and the third item is about the next one arriving by accident.',
     'a member that was not measured in production, or one reachable through the web API today',
     [30, 33, 54]),
    ('Money-path edge cases',
     'Small, well understood, and each needs one decision before the code can be written.',
     'a member that needs no decision before its code can be written',
     [26, 27, 28, 61, 62, 63]),
    ('Product features you might actually want',
     'Nothing here is broken; this is the work that makes the product better.',
     'a member that is a defect rather than an improvement',
     [1, 2, 3, 8, 12, 15, 23, 24, 51, 52]),
    ('The reusable toolkit — the second deliverable',
     'Not about the product: about the development harness being reusable on a new project.',
     'a member about the product rather than about the development harness',
     [18, 40, 47, 49, 50, 56, 57, 58, 89, 103, 105]),

    # ⚠ THIS GROUP'S FRAMING IS ITS OWN FALSIFIER, AND IT FIRED TWICE ON THE DAY IT WAS WRITTEN.
    # The first draft listed SIX items. #104 — a gate reporting a failure it cannot RETRACT — is
    # neither thing this sentence claims, and #94 is a docstring that overclaims while the guard
    # behaves correctly, which is also neither. Both moved to the bookkeeping group; #104 sits
    # beside #100, which its own row names as the likelier home. ⛔ THE SECOND ONE WAS FOUND BY
    # THE r1 REVIEWER, NOT BY ME, after I had already "fixed" the first and believed the group
    # sound — instance, not class, exactly as this repo keeps recording.
    # ⚠ The tempting repair was to WIDEN the sentence until all six fitted. That is refused on
    # purpose: under the create/retire policy filed on backlog row #90, a framing widened to
    # admit a member has stopped being a claim and become a bin with a better name. The sentence
    # stayed narrow and the membership moved.
    ('Checks that can be wrong without looking wrong',
     'Three items, one shape: a signal that does not do its job. Two are failures indistinguishable '
     'from a pass; the third is a warning printed on every single run that nobody acts on. This is '
     'the class that lets a gap sit for a week in plain sight — including, until today, the missing '
     'descriptions on this page.',
     'a member whose failure is plainly visible AS a failure',
     [101, 111, 112]),
]

# ⛔ THREE GROUPS RETIRED 2026-09-11 under row #90's policy, each by a NAMED trigger, and their
# members did not lose their summaries — that is what splitting SUMMARIES out bought:
#   * `Sync` — trigger (2), fewer than two open members. One item is an item, not a group.
#   * `Small visual polish` — triggers (1) AND (3). Its framing claimed "extra-small items" while
#     #7 is sized S; and after the bundle cleanup its membership {4,5,6,7} became EXACTLY the tag
#     `product / renderer`, so the tag already selects it and the group added only a false clause.
#   * `Process, tooling and bookkeeping` — the CREATE test. 22 items across 13 tags framed as
#     "Instruments and habits. Cheap individually", which nothing could make false. A bin.



# ─── ANSWERS to questions asked FROM the page, keyed by group number ────────────────────────────
#
# The Ask tray means a reader can question this page and have the session answer. An answer that
# lives only in the chat transcript has the problem the page was built to solve — it is gone by
# tomorrow, and the next reader asks the same thing. So answers land HERE, beside the claim that
# prompted them, and survive every regeneration.
ANSWERS: dict[int, list[tuple[str, str]]] = {
    1: [(
        "Once a stable blob address is used — the YouTube videoId, say — doesn't a title change "
        "become a simple property change, with no summary or dig blob lost?",

        "<p>Yes, and that is already the decided design — but the videoId <em>alone</em> is not "
        "enough, and the ADR rejects that exact narrower form in its own list of options.</p>"

        "<p><b>Today</b> a summary's key is built from <code>&lt;serial&gt;_&lt;slug&gt;</code>: a "
        "per-replica serial number and a title-derived slug, both mutable. That is the cause rather "
        "than a symptom — <code>lib/serial-filename.ts</code> builds the base, and "
        "<code>lib/cloud-sync/reconcile-serial.ts</code> exists only to repair the divergence it "
        "creates.</p>"

        "<p><b>ADR-0006</b> replaces it with "
        "<code>&lt;workspaceId&gt;/videos/&lt;videoId&gt;/&lt;generationId&gt;/…</code> — built only "
        "from values that never change. A title change then updates a display attribute and moves "
        "nothing; <code>serialNumber</code> and <code>slug</code> are demoted to display attributes, "
        "with a manifest mapping each logical slot to the blob currently authoritative.</p>"

        "<p><b>Why not videoId on its own.</b> ADR-0006 considered it and rejected it: without the "
        "generation dimension a regeneration still overwrites in place, so two concurrent writers "
        "can still destroy each other's paid work, and there is nothing to compensate <em>from</em> "
        "after a failed interleaving. That is item <a href=\"#i19\">#19</a> — the one thing stable "
        "naming does not fix.</p>"

        "<p><b>So the six split.</b> The orphaning half of <a href=\"#i17\">#17</a>, "
        "<a href=\"#i20\">#20</a> and <a href=\"#i21\">#21</a> dissolves under a stable address. "
        "<a href=\"#i19\">#19</a> and <a href=\"#i22\">#22</a> need the generation dimension and the "
        "manifest, not just a stable name.</p>"

        "<p><b>Why it is still open.</b> Not a missing idea — ADR-0006 is still "
        "<code>status: proposed</code>, and the schema slice was <b>parked on 2026-08-11</b> to "
        "return to the launch roadmap. The price it names is garbage collection: immutable "
        "generations accumulate, and the manifest is what makes a mark-and-sweep possible at all.</p>"
    ), (
        "So we need a proper order of fixes — some of these become obsolete once the main ones are "
        "fixed?",

        "<p>Yes, and the backlog already knows it: <b>16 of the 55 rows</b> carry dependency "
        "language — <em>supersedes, dissolves, moot, blocked by, folds into</em> — but only in "
        "prose, where no ordering is visible and nothing can act on it.</p>"

        "<p><b>Quoted, not paraphrased.</b> <a href=\"#i20\">#20</a> and <a href=\"#i21\">#21</a> "
        "each say: <em>“let ADR-0006's manifest dissolve it … check the third option first; this "
        "may be work the stable-blob-addressing slice deletes rather than work to do.”</em> "
        "<a href=\"#i22\">#22</a>: <em>“When the manifest slice dissolves this, these go red — that "
        "is the signal to close #22.”</em> <a href=\"#i52\">#52</a>: <em>“Blocked on unparking blob "
        "addressing.”</em> <a href=\"#i15\">#15</a>: <em>“Supersedes the need for #14's lazy-warm "
        "once shipped.”</em></p>"

        "<p><b>It has already happened once.</b> ADR-0006 turned most of a five-round conditional-"
        "write spec into work that was <em>moot rather than deferred</em> — that phrase is in "
        "<a href=\"#i17\">#17</a>'s own status cell. Twelve review rounds of a design that the next "
        "decision deleted.</p>"

        "<p><b>So for group 1 the order is not a preference, it is a fact.</b> Do the addressing "
        "slice first: <a href=\"#i20\">#20</a>, <a href=\"#i21\">#21</a> and most of "
        "<a href=\"#i17\">#17</a> are then <em>deleted</em> rather than done. Only "
        "<a href=\"#i19\">#19</a> and <a href=\"#i22\">#22</a> survive it. Fixing #20 or #21 first "
        "means writing a guard for an address that is about to stop existing.</p>"

        "<p><b>What is missing is structure, not knowledge.</b> The Size cell records the "
        "<em>gate</em> — design, decision — and this page derives the \"waiting on\" column from it. "
        "Nothing records <em>dissolved by</em> or <em>blocked by</em>, so no view can order the list "
        "or grey out an item whose prerequisite is unstarted. <b>Proposed, not done:</b> a "
        "<code>Depends</code> field per row, which this page would render as an ordering and as a "
        "\"do not start yet\" marker. That changes the canonical table, so it is your call.</p>"
    ), (
        "Express the dependencies between groups, so work starts at the root-cause items.",

        "<p>Agreed. Two places it can live, and they differ in blast radius rather than in what you "
        "would see on this page. <b>Neither is built — this is the decision, written down.</b></p>"

        "<p><b>A — a <code>DEPENDS</code> map in the generator.</b> Same contract as the grouping "
        "above: hand-written prose, mechanically complete. Each entry is "
        "<code>item → (blocker, relation)</code> where the relation is <em>dissolved-by</em>, "
        "<em>blocked-by</em> or <em>folds-into</em>. The build refuses if a referenced item does "
        "not exist, is already closed, or forms a cycle. Renders as a <em>“#20 — do not start: the "
        "addressing slice deletes this”</em> marker, and sorts roots above the work they gate. "
        "<b>Touches nothing outside this page</b>, and is deleted by deleting a dict.</p>"

        "<p><b>B — a <code>Depends</code> column in <code>docs/backlog.md</code>.</b> The data lives "
        "with the data, so GitHub readers and every future instrument see it too, not just this "
        "page. Costs a change to the canonical table. <b>Checked, not assumed:</b> a seventh column "
        "inserted before <em>Status</em> was driven through both backlog ratchets — the shape check "
        "passes and the marker check still reads the true Status cell, correctly flagging a "
        "synthetic closed-but-still-red row. So it is safe; it is just wider.</p>"

        "<p><b>Recommendation: A first, then promote to B.</b> The vocabulary is the part most "
        "likely to be wrong — whether <em>dissolved-by</em> and <em>blocked-by</em> are really "
        "different relations, and whether a relation belongs to an item or to a whole group. Getting "
        "that wrong in the generator costs one commit; getting it wrong in the canonical table costs "
        "a migration of every row plus whatever has started reading the column. The grouping above "
        "started the same way and has held.</p>"

        "<p><b>One thing A cannot do</b>, and it is the reason B exists: a dependency that only this "
        "page knows is invisible to anyone reading <code>docs/backlog.md</code> on GitHub — which is "
        "where the backlog is normally read. Treat A as the prototype, not the destination.</p>"
    )],
}


# ─── DEPENDENCIES — what has to happen before what ──────────────────────────────────────────────
#
# Asked for 2026-08-22: "express dependencies among groups of backlogs so that work starts at the
# root-cause items." Three things came out of deriving it, and each shaped what is below.
#
# 1. THE ROOT OF GROUP 1 IS NOT A BACKLOG ITEM. #20 and #21 both say the stable-addressing slice
#    "may delete this rather than leave work to do" — and that slice is a PARKED DECISION
#    (ADR-0006, status: proposed), not a row. A dependency field restricted to `#NN` could not
#    express the single most important ordering fact in the list. Hence named roots.
#
# 2. A BARE `#47` IS AMBIGUOUS. #52 says "Blocked on unparking blob addressing (task #47)" — that is
#    TASK 47. BACKLOG 47 is the knowledge graph, unrelated. Encoding a bare number would have
#    recorded a false edge. This is backlog #39 ("the identifier IS the position") biting early, so
#    roots are namespaced strings and item references are validated against the open set.
#
# 3. REGEX EXTRACTION IS NOT VIABLE. A sweep for dependency words hit 13 rows, about half of them
#    false: #4's "fold into any markdown-touching bundle" is a batching hint, #46's "fold into path
#    syntax" is about characters, #27's "superseded" is about blob generations. So this map is
#    hand-written and mechanically validated — the same contract as GROUPS.
ROOTS: dict[str, dict[str, str]] = {
    "stable-blob-addressing": dict(
        label="The stable-addressing slice",
        detail="ADR-0006 — <code>status: proposed</code>, and the schema slice was parked on "
               "2026-08-11 to return to the launch roadmap. Not a backlog row: a decision waiting "
               "to be unparked. Blob keys stop being built from a mutable serial and slug.",
    ),
}

# label, what it means for the reader, css class, sort rank (lower starts sooner)
RELATIONS: dict[str, tuple[str, str, str, int]] = {
    "survives": ("survives it", "The root does not fix this. Real work either way — safe to start "
                 "now.", "live", 1),
    "partly-dissolved-by": ("mostly deleted by", "Most of this goes when the root lands; a named "
                            "residue survives.", "part", 2),
    "blocked-by": ("blocked by", "Cannot start until the root lands.", "block", 3),
    "dissolved-by": ("deleted by", "This disappears when the root lands. Starting it means "
                     "building a guard for an address that is about to stop existing.", "kill", 4),
}

# item → (relation, root key, optional note)
DEPENDS: dict[int, tuple[str, str, str]] = {
    19: ("survives", "stable-blob-addressing",
         "needs the generation dimension, not just a stable name"),
    17: ("partly-dissolved-by", "stable-blob-addressing",
         "residue: <code>persist_summary</code> merge semantics"),
    52: ("blocked-by", "stable-blob-addressing", "blocked on unparking, per its own status cell"),
    20: ("dissolved-by", "stable-blob-addressing", ""),
    21: ("dissolved-by", "stable-blob-addressing", ""),
    22: ("dissolved-by", "stable-blob-addressing", ""),
}


def depends_errors(depends: dict, roots: dict, open_nums: set[int]) -> list[str]:
    """PURE. Same posture as `sanitise_groups`: the prose may be wrong, the graph may not be
    incoherent. A dependency that says DO NOT START must not be pointing at nothing."""
    errors = []
    for item, (rel, root, _note) in sorted(depends.items()):
        if item not in open_nums:
            errors.append(f"#{item} has a dependency but is not an open item")
        if rel not in RELATIONS:
            errors.append(f"#{item}: unknown relation {rel!r} (known: {sorted(RELATIONS)})")
        if root in roots:
            continue
        if root.isdigit():
            if int(root) not in open_nums:
                errors.append(f"#{item} depends on #{root}, which is not an open item")
            elif int(root) == item:
                errors.append(f"#{item} depends on itself")
        else:
            errors.append(f"#{item} names root {root!r}, which is not in ROOTS")
    # item → item edges could cycle; named roots cannot. Walk only the numeric ones.
    for start in depends:
        seen, cur = {start}, depends[start][1]
        while cur.isdigit() and int(cur) in depends:
            nxt = int(cur)
            if nxt in seen:
                errors.append(f"dependency cycle through #{nxt}")
                break
            seen.add(nxt)
            cur = depends[nxt][1]
    return sorted(set(errors))


def dependency_svg(by_num: dict) -> str:
    """The dependency graph as INLINE SVG, laid out from DEPENDS so it cannot disagree with the
    markers beside each item.

    WHY NOT MERMAID HERE. Mermaid needs a renderer, and this page inherits the explain-diff rule —
    self-contained, no CDN, still readable in five years. Vendoring mermaid would put ~1MB of
    library into a 419KB page to draw seven nodes. The mermaid SOURCE is emitted below the diagram
    instead, because that is the part worth having: it renders wherever mermaid already works —
    GitHub, an ADR, a PR body — as `docs/superpowers/specs/2026-08-10-serve-path-deadline-design.md`
    already does."""
    ROW, PAD, RX, RW, IX, IW = 46, 26, 14, 200, 392, 290
    out = []
    for rk, root in ROOTS.items():
        # ⚠ `n in by_num` — PRE-EXISTING, found 2026-09-10 while verifying backlog #110 end to end,
        # and reproduced identically on master. A number DEPENDS names that is not among the rows
        # crashed here with a bare `KeyError` inside `build`, so the page was not written at all and
        # the reader got a traceback instead of this file's own refusal grammar. The way to make it
        # happen is to decorate row #17 — a dependency root — which is exactly the failure #110 is
        # filed about, and it silently made #110's own promise ("the page still builds and tells
        # you") false for the three highest-severity items on it. Nothing goes unsaid by skipping:
        # `depends_errors` already reports "#N has a dependency but is not an open item".
        kids = sorted((n for n, (_, r, _) in DEPENDS.items() if r == rk and n in by_num),
                      key=lambda n: (dep_rank(n), n))
        if not kids:
            continue
        h = max(140, len(kids) * ROW + PAD * 2)
        mid = h / 2
        rows = []
        for i, n in enumerate(kids):
            rel = DEPENDS[n][0]
            lbl, _why, css, _ = RELATIONS[rel]
            y = PAD + i * ROW + ROW / 2
            # Strip markdown before it reaches an SVG label too — `transferClassA` in #19's title
            # rendered its backticks literally. Truncate to what the box can actually hold: 290px
            # of box minus the 52px id gutter, at ~6.2px per character.
            clean = re.sub(r"[*`]", "", by_num[n]["title"])
            title = html.escape(clean[:36] + ("…" if len(clean) > 36 else ""))
            # a cubic from the root's right edge to the item's left edge; flat when aligned
            rows.append(
                f'<path class="e e-{css}" d="M{RX+RW} {mid} C{RX+RW+70} {mid}, {IX-70} {y}, {IX} {y}"/>'
                # label sits just LEFT of its own node, right-aligned — one per row. Placed at the
                # curve midpoint they collided into an unreadable stack, all six within ~40px.
                # y-16, not y-6: at y-6 the incoming curve passed straight through the text
                # and "DELETED BY" read as struck through. Above the box top, the row is clear.
                f'<text class="elabel e-{css}" x="{IX-10}" y="{y-16}" '
                f'text-anchor="end">{lbl}</text>'
                f'<a href="#i{n}"><rect class="n n-{css}" x="{IX}" y="{y-15}" width="{IW}" '
                f'height="30" rx="3"/>'
                f'<text class="nid" x="{IX+12}" y="{y+4}">#{n}</text>'
                f'<text class="ntitle" x="{IX+52}" y="{y+4}">{title}</text></a>')
        out.append(
            f'<figure class="depmap">'
            # The root's full statement lives HERE and nowhere else. Removing the duplicate panel
            # first deleted it outright — the page said "start here" and never said what the thing
            # was. The count check below is what caught that, one edit after it caught the copy.
            f'<p class="rootdetail"><b>{html.escape(root["label"])}</b> — {root["detail"]}</p>'
            f'<svg viewBox="0 0 {IX+IW+12} {h}" role="img" '
            f'aria-label="Dependency map: {html.escape(root["label"])} and the {len(kids)} items it '
            f'governs"><rect class="n n-root" x="{RX}" y="{mid-26}" width="{RW}" height="52" '
            f'rx="3"/><text class="rootlbl" x="{RX+RW/2}" y="{mid-4}" text-anchor="middle">'
            f'{html.escape(root["label"])}</text>'
            f'<text class="rootsub" x="{RX+RW/2}" y="{mid+14}" text-anchor="middle">'
            f'start here · parked</text>' + "".join(rows) + '</svg>'
            f'<figcaption>Arrows read <em>root → item</em>: what the addressing slice does to each '
            f'item if it lands. Click a box to jump to the entry.</figcaption></figure>')
    return "".join(out)


def dependency_mermaid(by_num: dict) -> str:
    """The same graph as mermaid source, for pasting where mermaid renders.

    ⚠ NOT RENDERED HERE — mermaid is not installed and this page cannot fetch it, so this string is
    emitted from the same data as the SVG above but its rendering is unverified. `#` is kept out of
    node labels on purpose: mermaid reads `#nnn;` as an entity, and a label is not worth the risk."""
    lines = ["flowchart LR"]
    for rk, root in ROOTS.items():
        # ⚠ `n in by_num` — PRE-EXISTING, found 2026-09-10 while verifying backlog #110 end to end,
        # and reproduced identically on master. A number DEPENDS names that is not among the rows
        # crashed here with a bare `KeyError` inside `build`, so the page was not written at all and
        # the reader got a traceback instead of this file's own refusal grammar. The way to make it
        # happen is to decorate row #17 — a dependency root — which is exactly the failure #110 is
        # filed about, and it silently made #110's own promise ("the page still builds and tells
        # you") false for the three highest-severity items on it. Nothing goes unsaid by skipping:
        # `depends_errors` already reports "#N has a dependency but is not an open item".
        kids = sorted((n for n, (_, r, _) in DEPENDS.items() if r == rk and n in by_num),
                      key=lambda n: (dep_rank(n), n))
        if not kids:
            continue
        rid = re.sub(r"[^a-zA-Z0-9]", "_", rk)
        lines.append(f'  {rid}(["{root["label"]} — start here"])')
        for n in kids:
            rel = DEPENDS[n][0]
            # Strip markdown before it reaches a mermaid label: a backtick opens a markdown-string
            # in mermaid, and `transferClassA` in #19's title leaked one through. Quotes too.
            raw = re.sub(r"[*`]", "", by_num[n]["title"]).replace('"', "'")
            title = raw[:44] + ("…" if len(raw) > 44 else "")
            lines.append(f'  {rid} -->|{RELATIONS[rel][0]}| item{n}["item {n} · {title}"]')
        for n in kids:
            lines.append(f'  class item{n} {DEPENDS[n][0].replace("-", "_")};')
    lines += [
        "  classDef survives fill:#0f7268,stroke:#0f7268,color:#fff;",
        "  classDef partly_dissolved_by fill:#a8690b,stroke:#a8690b,color:#fff;",
        "  classDef blocked_by fill:#6b7686,stroke:#6b7686,color:#fff;",
        "  classDef dissolved_by fill:#ad3a22,stroke:#ad3a22,color:#fff;",
    ]
    return "\n".join(lines)


def dep_rank(num: int) -> int:
    """Sort key inside a group: no dependency first, then survives, …, deleted-by last. The whole
    point of the ordering is that what may evaporate sinks below what has to be done regardless."""
    d = DEPENDS.get(num)
    return RELATIONS[d[0]][3] if d else 0


def waiting_on(size: str) -> tuple[str, str]:
    """What the item is blocked on, derived from the Size cell — which is where this project already
    records it (`M + design`, `S (decision) + S (impl)`). Not a second source of truth."""
    s = size.lower()
    if "design" in s:
        return "design", "a design conversation"
    if "decision" in s:
        return "decision", "a decision from you"
    if "study" in s:
        return "study", "a feasibility study"
    return "work", "nothing — just the work"


def plain(text: str) -> str:
    """Emphasis stripped, then escaped. Used where markup would be noise rather than meaning."""
    return html.escape(re.sub(r"[*`]", "", text).strip())


def md(text: str) -> str:
    """Escape, then render the inline markdown — through `page_markup`, not here. Backlog #71.

    ⚠ WHAT THIS FILE USED TO DO, AND WHY IT WAS WRONG. Four stacked `re.sub` passes: code, then
    bold, then em, then links. Stacked passes are blind to each other's OUTPUT, so the `*em*` pass
    reached inside the `<code>` element the code pass had just emitted. MEASURED 2026-08-30 over the
    213 strings this file actually renders: **7 crossed tag spans and 12 cases of markup emitted
    inside a code span** — including `docs/backlog.md`'s own `select count(*) filter (…)`, which
    reached the page as `select count(<em>) filter …`, and row #24's `*caption*`, which is inside
    backticks and was italicised straight through them.

    It also rendered `[text](url)` with **no href sanitiser at all**, while
    `explainer-serve.safe_href` had existed unshared for days.

    `page_markup.scan` is one left-to-right pass: a construct consumes its whole span before the
    next is considered, so a span cannot begin in one region and end in another. Both counts are
    now 0, with no real emphasis or link lost.

    `.strip()` is preserved — it was this function's behaviour and the cells rely on it.
    """
    return page_markup.render_inline(text.strip())


# ─── change history, read out of git rather than tracked separately ─────────────────────────────
#
# WHY GIT AND NOT A SNAPSHOT FILE. "What changed since I last looked?" needs a BEFORE. The obvious
# implementation writes a copy of the backlog beside the page and diffs against it — a second
# record of the same facts, which can drift from the first and has no answer for "changed when".
# `docs/backlog.md` has been version-controlled since 2026-06-20; every edit is already recorded,
# with a timestamp. Reading that history cannot disagree with the file, because it IS the file.
#
# MEASURED: 55 versions, ~1,930 row-instances, 1.0 s for the whole walk.
#
# A row is matched by its ITEM NUMBER and compared as raw text. Deliberately looser than `parse` —
# older versions of the file have a different column layout, and a history walk that refused to
# read them would report "no history" for the very items that have been around longest.
ROW = re.compile(r"^\|\s*(\d+)\s*\|(.*)$")


def rows_of(text: str) -> dict[int, str]:
    """Item number → its row's raw text, for one version of the file.

    ⚠ THIS IS A SECOND READING OF "WHAT IS A ROW", and `parse`'s own docstring argues at length
    against exactly that — r2 finding M-4 (Claude) pointed out the argument sits ninety lines below
    an unmentioned counter-example. Said plainly rather than quietly: this regex knows nothing of
    sections, headers or table blocks, and it is deliberately kept that way, because its job is to
    diff HISTORICAL versions of the file whose structure may not match today's. Its keys are only
    ever read through `hist.get`, so a key `parse` does not produce is ignored rather than rendered.
    ⛔ What it must NOT become is a second answer to "is this row on the page" — that question has
    one owner, and it is `parse`. ⚠ THAT SENTENCE IS A CONVENTION, NOT A GUARD: nothing observes it,
    and this project has measured what the difference is worth ("a convention catches what you READ;
    a script catches what is THERE"). `scripts/check-vocabulary-collisions.py` exists for exactly
    this class — one mechanism per concern — and teaching it about this pair is follow-up work,
    named here so the gap is visible rather than implied away by the ⛔."""
    out = {}
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            out[int(m.group(1))] = m.group(2).rstrip()
    return out


def changes_from_versions(versions: Sequence[tuple[str, int, str]]) -> dict[int, dict]:
    """PURE. Versions OLDEST FIRST as (sha, unix_ts, file_text) → per item:

        first   when the item first appeared
        last    when its row last differed from the version before it
        sha     the commit that change landed in
        prev    the row's text immediately BEFORE that change, or None if it never changed

    An item that vanishes and returns is treated as new again — rare, and "new again" is the more
    useful reading of a re-filed number than a silent join across the gap."""
    hist: dict[int, dict] = {}
    prev_version: dict[int, str] = {}
    for sha, ts, text in versions:
        cur = rows_of(text)
        for num, text_now in cur.items():
            if num not in prev_version:
                hist[num] = dict(first=ts, last=ts, sha=sha, prev=None)
            elif prev_version[num] != text_now:
                h = hist.setdefault(num, dict(first=ts, last=ts, sha=sha, prev=None))
                h.update(last=ts, sha=sha, prev=prev_version[num])
        prev_version = cur
    return hist


def word_diff(before: str, after: str) -> str:
    """Word-level diff as HTML — deletions struck through, insertions marked.

    Diffs the PLAIN text, not the markdown. Diffing the source and then converting would splice
    `<del>` through the middle of an emphasis run and produce broken tags; the diff view trades
    formatting for correctness, which is the right way round for something read only when someone
    already wants the detail."""
    import difflib
    a, b = re.sub(r"[*`]", "", before).split(), re.sub(r"[*`]", "", after).split()
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag in ("delete", "replace"):
            out.append("<del>" + html.escape(" ".join(a[i1:i2])) + "</del>")
        if tag in ("insert", "replace"):
            out.append("<ins>" + html.escape(" ".join(b[j1:j2])) + "</ins>")
        if tag == "equal":
            out.append(html.escape(" ".join(a[i1:i2])))
    return " ".join(out)


class ShapeError(Exception):
    """A row whose column count disagrees with its table's header. Raised, never skipped — the
    Status cell would be somewhere other than where this code thinks it is, and reading the wrong
    cell is how a closed marker written for something else once closed two open items."""


DELIMITER_CELL = re.compile(r"^:?-+:?$")


def is_delimiter(line: str) -> bool:
    r"""The `|---|---|` rule under a table header — decided CELL BY CELL.

    ⚠ THREE SPELLINGS OF THIS HAVE BEEN WRONG, each in its own direction, so the rule is GFM's
    rather than a regex over the whole line:
      * `^\|[\s:|-]+\|$` accepted `| | | |` and `| : | : |` — a half-typed row read as a
        delimiter and dropped in silence (r1 M-3);
      * anchoring on `\|$` rejected `|---|---|---`, a valid delimiter with its outer pipe omitted,
        and reported a healthy file (r2 M-1);
      * one hyphen ANYWHERE in the line accepted `| : | - | : |`, whose first cell is not a
        delimiter cell at all (r3, Codex).
    ⛔ ONE hyphen per cell, not three. Three is a convention; GFM's delimiter cell is optional
    colon, one or more hyphens, optional colon — so `|-|-|-|` and `| - | - | - |` are real
    delimiters, and reporting them would be the cry-wolf failure backlog #92 is filed about."""
    s = line.strip()
    # ⚠ A PIPE IS REQUIRED. `---` on its own is a horizontal rule, and without this it satisfied
    # every cell test and consumed a table's delimiter slot.
    if "|" not in s:
        return False
    # ⚠ No `bool(cells)` guard: `str.split` never returns an empty list (verified over "", "|",
    # "||", " | "), so it could not be False and read as a guarded case that was not one (r4 L-2).
    return all(DELIMITER_CELL.match(c.strip()) for c in s.strip("|").split("|"))


def row_ish(line: str) -> bool:
    """Could a reader have meant this line as a row of the table it sits in?

    ⛔ THE TEST IS THE PREFIX LENGTH, and both obvious alternatives are measured failures.
    `startswith("|")` misses `⭐| 5 | … |` — a decoration one character to the LEFT of the one
    #110 is filed about. "Contains a pipe" reports this file's own house style back at it:
    `> paragraphs of literal `|` on GitHub …` is real prose in `docs/backlog.md` and was being
    called a lost backlog item (r3, both halves).

    A decoration on a number cell is a character or two — `⭐`, `#3`, `- `, an indent. Prose that
    merely mentions a pipe has whole words in front of it. Three characters is the line between
    them, and it is a JUDGEMENT — so BOTH SIDES OF THE BOUNDARY are pinned at 3 and at 4, not at 3
    and at 24. r4 measured that sentence false in the upward direction: the negative case used a
    whole sentence, so raising the limit to 20 changed nothing anyone could see."""
    # ⚠ THE ORIGINAL LINE, not the stripped one (r4, Codex). Stripping first meant a four-space
    # indented pipe line was reported — and four spaces in Markdown is a CODE BLOCK, so that line
    # was never going to be a table row. The docstring and the code disagreed and the code was the
    # wrong one of the two. One leading space, which IS one of #110's decorations, is index 1.
    i = line.find("|")
    return 0 <= i <= 3


def report_run(rows: list[dict], unread: Sequence[str]) -> None:
    """Everything a completed run says on the terminal, in one place, for BOTH success arms.

    ⛔ IT EXISTS BECAUSE THE ARMS DISAGREED, and the case that caught it is in this file's own
    suite. `main` succeeds two ways — with an Ask tray and without one — and the no-tray arm
    returned before ANY of the drift notes were printed. So a run that had already gone wrong once
    (no tray) also silently dropped the GROUPS and DEPENDS drift warnings, and the reader
    got the smaller half of the truth exactly when they needed the larger one. This is r1 finding
    M-1's shape a third time; the answer is one function rather than a third copy of the block.

    ⚠ The ⚠ prefix is the existing channel: `explainer-serve._regenerate` collects those lines into
    the Refresh button's warning, and `.claude/hooks/regen-backlog-page.sh` keeps each ⚠ line with
    its three-space continuations."""
    report_unread(unread)
    for note in drift_notes_for(rows, unread):
        print(f"⚠  {note}")


def report_unread(unread: Sequence[str]) -> None:
    """PRINT the unread report. One ⚠ line, then indented detail.

    ⛔ MODULE LEVEL, not a closure inside `main`, and r2 finding H-2 is why: as a closure nothing
    could call it, so a mutation that marked EVERY line with ⚠ — reverting r1's M-2 fix outright —
    left the suite at 110/110. `explainer-serve` collects the ⚠ lines and cuts the join at 400
    characters, so marking all of them spends the whole budget and pushes the other warnings out of
    the Refresh button. The indent is the shape the Ask-tray failure above already uses, and
    `.claude/hooks/regen-backlog-page.sh` keeps an indented line that follows any ⚠ line."""
    for n, line in enumerate(unread_note(unread)):
        print(f"⚠  UNREAD: {line}" if n == 0 else f"   UNREAD: {line}")


def unread_note(unread: Sequence[str]) -> list[str]:
    """Display lines for rows the parser could not read — EMPTY when there were none. Line 0 is a
    SUMMARY that must stand alone; everything after it is detail.

    ⚠ It QUOTES each line rather than counting them. A bare count tells a reader that something is
    missing from the page and gives them no way to find it; this file has already paid for an
    unactionable warning once (r2 finding R2-9, three runs before anyone learned why the Ask tray
    had gone).

    ⛔ WHY LINE 0 IS SHORT, AND WHY THE PREFIX IS NOT IN HERE — r1 finding M-2, MEASURED TWICE.
    `explainer-serve` joins every line starting with ⚠ and cuts the join at 400 characters. The
    first fix folded the remedy into the summary to save it from the cut; measured, that made the
    summary 230 characters, took the note to 585, and left 2 of 6 warnings in the Refresh button —
    the same displacement the finding was about, one round later. So the two channels get different
    amounts: `main` marks ONLY line 0 with ⚠, the rest goes out indented, and the page box — which
    has no budget at all — renders every line. The `UNREAD:` prefix is added by each channel, so
    the string this returns is not a format anybody else has to parse."""
    if not unread:
        return []
    shown, extra = unread[:3], len(unread) - 3
    return [f"{len(unread)} line(s) in docs/backlog.md sit inside a table and were not read — "
            f"no card here, and on no count"] + \
           [ln.strip()[:110] + ("…" if len(ln.strip()) > 110 else "") for ln in shown] + \
           ([f"… and {extra} more"] if extra > 0 else []) + \
           ["a row must start with `|` and its number cell must be a bare integer — "
            "no ⭐, no #, no leading space"]


def parse(lines: Sequence[str], unread: list[str] | None = None) -> list[dict]:
    """Rows, in file order. Pass `unread` to also collect the lines this REFUSED TO READ.

    ⚠ AN OUT-PARAMETER, deliberately, and the alternative was measured against it: returning a
    tuple would rewrite eleven call sites, and a separate walker that re-derived "am I inside a
    table with a header" would be a second implementation of one rule — which this repo has
    watched drift into fabricating text on a live page. There is ONE walk. What the caller gets is
    the same walk's other half.

    ⛔ WHAT MAKES THIS NOT SELF-REFERENTIAL (backlog #110, portable-practices §21). The dropped
    lines are recognised from the FILE'S OWN TEXT — a line inside a table block that this walk did
    not read, decided from the line itself and never from the parse result — so the expectation and
    the subject no longer share a source. The completeness case in
    the suite below was blind precisely because both of its sides came out of this function."""
    rows: list[dict] = []
    header: list[str] = []
    section = ""
    # ⚠ NOT "the line after the header" — r3 finding M-2. A decorated row sitting between the
    # header and the delimiter consumed that one-line window, so the GENUINE delimiter one line
    # later was reported too, carrying a remedy ("the number cell must be a bare integer") that is
    # nonsense about `|---|---|---`. A false warning stapled to a real one is how a reader learns
    # to skim the box. The window is now "until this table has had its delimiter".
    seen_delimiter = False
    # ⛔ FENCE TRACKING WAS HERE IN r1 AND IS REVERTED (r2, Codex) — the reason is WHERE the fix
    # lived. Skipping ``` regions was meant to stop a false POSITIVE in the report; implemented in
    # this walk it also changed what `parse` READS, so its own bugs deleted real rows: `~~~` and
    # indented fences were not recognised at all, and an UNCLOSED fence silently dropped 61 of 110
    # rows. Trading "the warning is noisy" for "rows disappear" is a bad trade, and `docs/backlog.md`
    # has 0 fences today, so the trade bought nothing. A fenced example table is therefore still
    # READ as real rows — pre-existing, older and worse than the noise beside it, and its own slice.
    for line in lines:
        if line.startswith("## "):
            # ⚠ `seen_delimiter` is NOT reset here (r4 L-3): `header` is emptied, and nothing is
            # reported while `header` is falsy, so this reset could be removed with the suite
            # green. The `| # |` branch below is the one that carries the rule, and the input
            # that proves it is a file with TWO item tables — which `docs/backlog.md` is.
            section, header = line[3:].strip(), []
            continue
        if re.match(r"^\|\s*#\s*\|", line):
            header = [c.strip().lower() for c in CELL_SPLIT.split(line)[1:-1]]
            seen_delimiter = False
            continue
        if not re.match(r"^\|\s*\d+\s*\|", line):
            # ⭐ backlog #110. This branch used to be a bare `continue` — the ONE path out of this
            # function that lost a row without saying so. Its sibling (a width that disagrees with
            # the header) has raised since day one; this one dropped ⭐-, #- and space-decorated
            # rows in silence, and the page's completeness invariant could not see it.
            #
            # ⛔ THE GATE IS `header`, WHICH IS THE GATE THE READ BRANCH BELOW USES, and r3's
            # Blocking is why it has to be. r1 gated here on `header` too; r2 narrowed it to a
            # contiguous block, to stop a legend table in the same section reporting healthy rows.
            # MEASURED in r3: reading never narrowed with it. A row is read wherever `header` is
            # live, so between the end of the block and the end of the section a plain
            # `| 111 | … |` was READ ONTO THE PAGE while `| ⭐111 | … |` was dropped in silence —
            # #110's defect verbatim, with this branch's own ratchet green over it.
            #
            # r1's false positives are answered by the FILTER instead. A legend row IS still
            # reported, and that is right rather than noise: where `header` is live,
            # `| 5 | Bundle E |` in a legend is read as item 5 or raises on its width, so a second
            # table there is a hazard and saying so is the service.
            if not header:
                continue
            if not seen_delimiter and is_delimiter(line):
                seen_delimiter = True
                continue
            if unread is not None and row_ish(line):
                unread.append(line)
            continue
        cells = [c.strip() for c in CELL_SPLIT.split(line)[1:-1]]
        if not header or len(cells) != len(header):
            raise ShapeError(f"row has {len(cells)} cells, header has {len(header)}: {line[:70]}")
        col = dict(zip(header, cells))
        # ⚠ A THIRD OUTCOME, and until r4's L-6 this file's own docstring said there were two.
        # A table whose width matches but whose column NAMES do not (`| # | Key | Note |`) reached
        # `main` as a bare `KeyError` traceback rather than its `REFUSED:` grammar, because the
        # handler catches `ShapeError` only. Raised as the sibling it is instead of widening the
        # handler, so the message names the columns. Pre-existing — `master` has the same two lines.
        missing = [c for c in ("#", "item", "status") if c not in col]
        if missing:
            raise ShapeError(f"header has no {', '.join(missing)} column: {line[:70]}")
        num, item, status = col["#"], col["item"], col["status"]

        sev, rest, was = "none", item, ""
        if item and item[0] in SEVERITY:
            sev, rest = SEVERITY[item[0]], item[1:].strip()
        # A closed row reads `✅ (was 🟡) **Title** — …`, and others carry different leading
        # decoration (a ⚠️, a renumbering note). Anchoring the title at position 0 failed on seven
        # rows and put literal `**` in the heading — found by reading the BUILT PAGE, not the source.
        w = re.match(r"\(was\s*(.+?)\)\s*", rest)
        if w:
            was, rest = w.group(1).strip(), rest[w.end():]
        m = re.search(r"\*\*(.+?)\*\*", rest[:400], re.S)
        title = m.group(1) if m and m.start() <= 60 else rest[:80]

        rows.append(dict(
            num=int(num), sev=sev, title=title, body=rest, section=section, was=was,
            touches=col.get("touches", ""), size=col.get("size", ""), bundle=col.get("bundle", ""),
            status=status, closed=("✅" in status),
            # ⚠ read, not inferred. The first version of this flag WAS an inference ("says MERGED
            # but has no ✅") and it fired on #46, #50 and #54 — all genuinely open, all merely
            # DESCRIBING a wrong closure. A derived flag that is wrong is worse than no flag.
            warned=("⚠" in status),
        ))
    return rows


def attach_history(rows: list[dict], working_text: str) -> None:
    """Hang each row's change history off it, in place. Impure by design — it shells out to git.

    THE WORKING COPY IS THE LAST VERSION. An edit that has not been committed is still a change the
    reader wants to see; keying only off commits would show the page as unchanged immediately after
    the edit that changed it, which is the exact staleness this feature exists to remove. It is
    appended only when it actually differs from HEAD, so a clean tree produces no phantom entry."""
    log = subprocess.run(["git", "-C", str(REPO), "log", "--format=%H %ct", "--",
                          "docs/backlog.md"], capture_output=True, text=True)
    entries = [ln.split() for ln in log.stdout.splitlines() if ln.strip()]
    versions: list[tuple[str, int, str]] = []
    for sha, ts in reversed(entries):                       # git logs newest first; walk forwards
        blob = subprocess.run(["git", "-C", str(REPO), "show", f"{sha}:docs/backlog.md"],
                              capture_output=True, text=True)
        if blob.returncode == 0:
            versions.append((sha, int(ts), blob.stdout))
    if versions and versions[-1][2] != working_text:
        versions.append(("working", int(BACKLOG.stat().st_mtime), working_text))

    hist = changes_from_versions(versions)
    live = rows_of(working_text)
    for r in rows:
        h = hist.get(r["num"])
        # `raw` is the CURRENT row text, so the diff compares like with like — the same
        # whole-row form `prev` was captured in, not the parsed-out body.
        r["hist"] = dict(h, raw=live.get(r["num"], "")) if h else None


def bundle_tags(raw: str) -> list[str]:
    """PURE. The Bundle cell as the TAGS it assigns, broadest first.

    The cell holds one hand-written value — `(cloud/money)`, `(comprehensibility)`, `A`, `—`.
    A slash is a family, so `(cloud/money)` assigns BOTH `cloud` and `cloud/money`: asking for
    `cloud` must find the money, test, UX, security, quality and frontend items too, which was
    the whole complaint that prompted this ("I could not see backlogs in bundle such as
    Comprehensibility"). An untagged row gets `untagged` rather than nothing, because a filter
    option with no name cannot be chosen, and a row with no tag must still be reachable.
    """
    s = (raw or "").strip().strip("()").strip()
    if not s or s in {"—", "-", "Item"}:
        return ["untagged"]
    parts = [" ".join(x.lower().split()) for x in s.split("/")]
    parts = [x for x in parts if x]
    if not parts:
        return ["untagged"]
    return [" / ".join(parts[:k + 1]) for k in range(len(parts))]


def bundle_options(rows: list[dict]) -> list[tuple[str, int, int]]:
    """PURE. `(tag, open_count, total_count)`, commonest first then alphabetical.

    DERIVED FROM THE ROWS, never a hand-kept list — the mistake `GROUPS` makes, and the one that
    froze this page for five days. A tag that stops being used disappears from the control by
    itself; a new one appears the first time it is written in the table.

    ⚠ BOTH COUNTS, and that is not padding. The list defaults to showing OPEN items, so a label
    reading `comprehensibility (26)` sits above 10 visible rows — measured 2026-09-09, and a count
    that disagrees with what the reader then sees is the same class of quiet wrongness this page
    exists to remove. Showing `10 open · 26 total` is true under either filter.
    """
    opens: dict[str, int] = {}
    totals: dict[str, int] = {}
    for r in rows:
        for tag in bundle_tags(r.get("bundle", "")):
            totals[tag] = totals.get(tag, 0) + 1
            if not r.get("closed"):
                opens[tag] = opens.get(tag, 0) + 1
    return sorted(((k, opens.get(k, 0), v) for k, v in totals.items()),
                  key=lambda kv: (-kv[1], -kv[2], kv[0]))


def sanitise_groups(groups: list, open_nums: set[int]) -> tuple[list, list[str]]:
    """PURE. GROUPS as it can safely be RENDERED, plus what had to be corrected to get there.

    ⛔ THIS REPLACES A REFUSAL, BY THE USER'S DECISION 2026-09-09: *"refusing refresh is not
    appropriate"*. The old behaviour raised `ShapeError` when GROUPS named an item that is no
    longer open, or named one twice. Both are real drift and both are worth SAYING — but neither
    makes the page assert anything false, because the remedy in each case is to show LESS:

      * an item that is no longer open is dropped from its group (it still renders in the
        closed list, from the row itself);
      * an item claimed by two groups is kept in the first and dropped from the second.

    The page always builds. A stale grouping now costs a warning, not the whole view — which is
    the trade the five-day freeze settled: the page frozen at 2026-09-04 told its reader nothing,
    while a page with one group slightly out of date would have told them almost everything.
    """
    notes, seen, out = [], set(), []
    dropped_closed: list[int] = []
    dropped_dupe: list[int] = []
    for title, framing, falsifier, nums in groups:
        kept = []
        for n in nums:
            if n not in open_nums:
                dropped_closed.append(n); continue
            if n in seen:
                dropped_dupe.append(n); continue
            seen.add(n); kept.append(n)
        out.append((title, framing, falsifier, kept))
    if dropped_closed:
        # ⚠ "no longer open" is an INFERENCE from absence, and r2 finding H-1 measured it stating
        # something false: three rows the parser could not read left `open_nums`, and this line
        # then announced they had closed. `sanitise_groups` cannot see the unread list — it is pure
        # over the numbers it is given — so the caller qualifies the sentence instead. See `build`.
        notes.append(f"GROUPS still names {len(dropped_closed)} item(s) that are no longer open: "
                     f"{sorted(set(dropped_closed))} — dropped from their group for this build")
    if dropped_dupe:
        notes.append(f"item(s) claimed by more than one group: {sorted(set(dropped_dupe))} — kept "
                     f"in the first group only")
    return out, notes


def contradiction_errors(rows: list[dict]) -> list[str]:
    """PURE. Rows whose two statements of closed-ness DISAGREE.

    ⛔ THIS EXISTS BECAUSE THE DISAGREEMENT USED TO BE A `KeyError`. Closed-ness is written
    in TWO cells — the Item cell's leading ✅ marker (which `SEVERITY` maps to "done") and the
    Status cell (which `closed` reads, deliberately, see `parse`). When a row carries the marker
    but the Status cell does not, the row is OPEN with severity "done", and the sort's
    `order[r["sev"]]` has no such key. MEASURED 2026-09-09 on rows 81, 82, 98 and 99: a bare
    `KeyError: 'done'` traceback, and — because nothing CALLS this generator — a page frozen
    since 2026-09-04 with no reader able to tell.

    A crash and a refusal are not the same thing. A refusal names the rows and says what to do;
    a traceback says a dict lookup failed. This turns the one into the other. It does NOT pick
    a winner between the two cells: which one is authoritative is a design question, and a
    generator is the wrong place to settle it.
    """
    bad = sorted(r["num"] for r in rows if not r["closed"] and r["sev"] == "done")
    if not bad:
        return []
    return [f"rows carry a ✅ marker while their Status cell does not, so they are open and done "
            f"at once: {bad} — add the ✅ to the Status cell (the cell `closed` reads), or drop "
            f"the marker"]


# ─── rendering ──────────────────────────────────────────────────────────────────────────────────

def drift_notes_for(rows: list[dict], unread: Sequence[str] = ()) -> list[str]:
    """Everything the page and the terminal both say about drift — ONE list, built once.

    ⛔ IT EXISTS BECAUSE THE TWO CHANNELS DISAGREED (r3 finding H-3). `build` post-processed
    `sanitise_groups`' output and `main` did not, so the page said *"…or could not be READ this
    run"* and the terminal said the flat, false *"no longer open"* — about an item that is open.
    The terminal is the channel `.claude/hooks/regen-backlog-page.sh` surfaces at the moment
    someone types the decorated row, so the reader most likely to act got the wrong sentence and
    the reader who may never open the page got the right one. That was exactly backwards.

    ⚠ THE QUALIFICATION COVERS BOTH FAMILIES, not one (r3 finding H-1). `sanitise_groups` and
    `depends_errors` BOTH decide from `open_nums`, and an unread row has already left it — so both
    of them infer "closed" from an absence the unread row itself caused. Qualified rather than
    suppressed: the drift underneath may be real, and hiding it would trade a false sentence for a
    missing one."""
    open_nums = {r["num"] for r in rows if not r["closed"]}
    notes = contradiction_errors(rows)
    notes += sanitise_groups(GROUPS, open_nums)[1]
    notes += [f"DEPENDS: {e}" for e in depends_errors(DEPENDS, ROOTS, open_nums)]
    if not unread:
        return notes
    return [n + " — or could not be READ this run; see the incomplete-view box"
            if ("no longer open" in n or "is not an open item" in n) else n
            for n in notes]


def card(r: dict) -> str:
    sev = "done" if r["closed"] else r["sev"]
    flag = ('<span class="flag" title="This row&#39;s own Status cell carries a warning — read it '
            'before trusting any summary of this item">&#9888; see status</span>') if r["warned"] else ""
    meta = "".join(
        f'<span class="chip"><b>{lbl}</b>{md(val)}</span>'
        for lbl, val in (("was ", r["was"]), ("touches ", r["touches"]), ("size ", r["size"]))
        if val and val not in {"—", "-"})

    # THE TAGS ARE SHOWN, not merely filterable — the user asked for both, and a filter over a
    # value the card never displays is a control with no referent. Only the LEAF is drawn: an item
    # tagged `cloud / money` shows one chip, while `data-tags` still carries `cloud` so the family
    # filter finds it. Drawing both would put "cloud" on the card twice and say nothing extra.
    tags = bundle_tags(r["bundle"])
    tagchips = "".join(
        f'<button class="tag" data-tag="{html.escape(tg)}" '
        f'title="show every item tagged {html.escape(tg)}">{html.escape(tg)}</button>'
        for tg in ([tags[-1]] if tags != ["untagged"] else []))

    h = r.get("hist")
    # ⚠ VISIBLE, not silent. An item whose history could not be reconstructed — renumbered, or the
    # table restructured under it — must say so. Rendering it as "unchanged" would be the same
    # class of lie as a check that passes because it could not run.
    if h is None:
        stamp, attrs = '<span class="age unknown">history unavailable</span>', ' data-nohist="1"'
    else:
        stamp = (f'<span class="age" data-first="{h["first"]}" data-last="{h["last"]}">'
                 f'{_ago(h["last"])}</span>')
        attrs = f' data-first="{h["first"]}" data-changed="{h["last"]}"'

    # The same dependency marker rides on the card, not only in the group table — a deep link
    # (#i20) lands here, and "do not start this" is the one thing that must not be left behind.
    dep = ""
    if r["num"] in DEPENDS:
        rel, root, note = DEPENDS[r["num"]]
        lbl, why, css, _ = RELATIONS[rel]
        rootname = ROOTS[root]["label"] if root in ROOTS else f"#{root}"
        dep = (f'<div class="depbox d-{css}"><b>{lbl} {html.escape(rootname.lower())}</b>'
               f'<span>{html.escape(why)}</span>' + (f'<span>{note}</span>' if note else "")
               + '</div>')

    diff = ""
    if h and h.get("prev") is not None:
        diff = (f'<details class="diffbox"><summary>what changed in this entry</summary>'
                f'<div class="diff">{word_diff(h["prev"], h["raw"])}</div></details>')

    return f"""
<article class="item" data-sev="{sev}" data-state="{'closed' if r['closed'] else 'open'}" data-tags="{html.escape('|'.join(tags))}"{attrs} id="i{r['num']}">
  <div class="num"><a href="#i{r['num']}">#{r['num']}</a></div>
  <div class="body">
    <div class="titleline"><span class="badge" hidden></span><h3>{md(r['title'])}</h3>{flag}</div>
    <div class="meta">{tagchips}{meta}{stamp}</div>
    {dep}
    <details><summary>the full entry, as filed</summary>
      <div class="prose">{md(r['body'])}</div>
      <div class="status"><b>Status cell</b>{md(r['status'])}</div>
      {diff}
    </details>
  </div>
</article>"""


def _ago(ts: int, now: int | None = None) -> str:
    """Human distance, computed at BUILD time. The page also recomputes nothing — a static page
    that says "2 days ago" a week later is lying, so the absolute date rides along in the title."""
    import datetime
    when = datetime.datetime.fromtimestamp(ts)
    days = (datetime.datetime.now() - when).days if now is None else (now - ts) // 86400
    rel = "today" if days <= 0 else ("yesterday" if days == 1 else f"{days}d ago")
    return f'<time datetime="{when:%Y-%m-%d}" title="{when:%Y-%m-%d %H:%M}">{rel}</time>'


def build(rows: list[dict], sha: str, edited: str, stamp: str,
          generated_at: str = "", unread: Sequence[str] = ()) -> str:
    open_rows = [r for r in rows if not r["closed"]]
    closed_rows = [r for r in rows if r["closed"]]
    by_sev = {k: sum(1 for r in open_rows if r["sev"] == k)
              for k in ("crit", "high", "med", "low", "none")}
    flagged = [r for r in rows if r["warned"]]
    by_num = {r["num"]: r for r in rows}

    open_nums = {r["num"] for r in open_rows}

    # ⛔ NOTHING BELOW REFUSES ANY MORE — the user's decision, 2026-09-09: *"refusing refresh is
    # not appropriate"*. Every one of these was a hand-kept list disagreeing with the table, and
    # every one of them froze the whole page rather than the part it was about. MEASURED: GROUPS
    # named three items that had closed on 2026-09-01/04, so the page stood at its 2026-09-04
    # 12:38 state through 21 commits, and — because nothing CALLS this generator — no reader could
    # tell. A view that is one group out of date beats a view that is five days out of date.
    #
    # Each drift is DROPPED from the render and REPORTED as a ⚠ line, which `_regenerate` already
    # forwards to the Refresh button as "rebuilt WITH A WARNING". Showing less is always safe here;
    # showing something false is not, and none of these can make the page assert anything false.
    # ⚠ ONE BUILDER, called here and by `main` — see `drift_notes_for`. The comment that used to
    # stand at `main`'s copy said "a second call cannot disagree with the one `build` made"; it was
    # true until this branch added post-processing on one side only (r3 finding H-3).
    drift_notes = drift_notes_for(rows, unread)
    groups_ok, _ = sanitise_groups(GROUPS, open_nums)
    # ⚠ backlog #110's note is NOT folded in here — r1 finding H-2. This box is headed "built from
    # a grouping that has drifted" and closes with "every row on this page was read from
    # docs/backlog.md in this run", pointing the reader at the generator. All three sentences are
    # false of an unread row, and the last two contradict the note directly above them. It gets its
    # own box below, with its own heading and the right file named.

    # ⭐ THE REST, AND IT IS AN INDEX RATHER THAN A GROUP — backlog #90's policy, adopted
    # 2026-09-11. Under clause 0 grouping is OPT-IN, so an open item belonging to no group is
    # NORMAL and not a debt. There is therefore nothing here to be ashamed of and no warning to
    # print: the section that used to say "nobody has described them yet" is gone with the
    # `undescribed` function that computed it.
    #
    # HOW THIS DIFFERS FROM THE BIN IT REPLACES: the retired group carried a FRAMING —
    # "Instruments and habits. Cheap individually" — which characterised its members and could not
    # be false. This carries no claim, and says so in its own dek. A group asserts; an index
    # enumerates.
    #
    # ⛔ THAT IS A DESCRIPTION OF INTENT, NOT A GUARANTEE, and three review rounds each measured a
    # broader version of it false. Exactly what holds, stated as a property rather than a promise:
    # the empty falsifier keeps this entry out of rule 1's reach, and rule 4 makes rewording these
    # two strings a TWO-FILE EDIT. ⚠ It does NOT prevent the rewording — measured: change both
    # copies together and the guard exits 0, by design. What it buys is that the change appears in
    # a diff as two files rather than one line. And NOTHING here touches prose elsewhere on the
    # page. Full scope and residue: `check-group-claims.py`'s docstring.
    rest = sorted(open_nums - {n for _, _, _, ns in groups_ok for n in ns})
    groups_for_page = list(groups_ok)
    if rest:
        groups_for_page.append((INDEX_TITLE, INDEX_DEK, "", rest))

    order = {"crit": 0, "high": 1, "med": 2, "low": 3, "none": 4}
    # ⚠ `.get`, not `[]`. A row carrying a ✅ marker while its Status cell does not is OPEN with
    # severity "done" — a real contradiction, reported in `drift_notes` — but it must not take the
    # page down with a `KeyError`. It sorts last. MEASURED 2026-09-09 on rows 81, 82, 98, 99.
    open_rows.sort(key=lambda r: (order.get(r["sev"], len(order)), r["num"]))
    closed_rows.sort(key=lambda r: r["num"])

    gate_of, groups_html = {}, ""
    for gi, (title, framing, _falsifier, items) in enumerate(groups_for_page, 1):
        # ORDERED, not as listed. Items that survive the root — or have no root — come first;
        # anything the root deletes sinks to the bottom, because that is work you should not start.
        ordered = sorted(items, key=lambda n: (dep_rank(n), n))

        used_roots = {DEPENDS[n][1] for n in ordered if n in DEPENDS}
        starthere = ""
        for rk in sorted(used_roots):
            if rk not in ROOTS:
                continue
            tally = {}
            for n in ordered:
                if n in DEPENDS and DEPENDS[n][1] == rk:
                    tally.setdefault(DEPENDS[n][0], []).append(n)
            bits = " · ".join(
                f'<b>{len(v)}</b> {RELATIONS[k][0]}'
                + " (" + ", ".join(f'<a href="#i{n}">#{n}</a>' for n in sorted(v)) + ")"
                for k, v in sorted(tally.items(), key=lambda kv: RELATIONS[kv[0]][3]))
            # ⟲ 2026-08-22, reported from the page: "the stable-addressing slice appears twice."
            # It did — this panel used to repeat the root's title AND its whole ADR paragraph,
            # which the map above already carries. The full statement belongs in ONE place; what a
            # group needs locally is only "which root governs my items, and what does it do to
            # them", plus a way back to the picture. Especially for group 5, whose single blocked
            # item sits far below the map.
            starthere += (f'<p class="rootref"><a href="#order">the stable-addressing slice</a>'
                          f' governs these — {bits}</p>')

        trs = ""
        for n in ordered:
            # ⭐ THE SUMMARY IS LOOKED UP, NOT CARRIED. Until 2026-09-11 a group held
            # `(number, sentence)` pairs, which nested TWO independent things: a claim about a
            # SET (the framing) and a plain-English line about ONE ROW. The nesting is why
            # retiring a group would have deleted 22 perfectly good sentences along with a
            # framing that asserted nothing — measured at 27 items before the split. Separated,
            # a summary outlives any grouping and an ungrouped item can still have one.
            # `.get`, not `[]`: a summary is OPTIONAL, which is the whole of clause 0.
            line = SUMMARIES.get(n, "")
            r = by_num[n]
            cls, label = waiting_on(r["size"])
            gate_of[n] = cls
            mark = ""
            if n in DEPENDS:
                rel, root, note = DEPENDS[n]
                lbl, why, css, _ = RELATIONS[rel]
                rootname = ROOTS[root]["label"] if root in ROOTS else f"#{root}"
                mark = (f'<span class="dep d-{css}" title="{html.escape(why)}">{lbl} '
                        f'{html.escape(rootname.lower())}</span>'
                        + (f'<span class="depnote">{note}</span>' if note else ""))
            trs += (f'<tr class="{"dep-row" if n in DEPENDS else ""}">'
                    f'<td class="mono"><a href="#i{n}">#{n}</a>'
                    f'<span class="dot s-{r["sev"]}" title="filed as {SEV_NAME[r["sev"]]} severity">'
                    f'</span></td><td>{line}{mark}</td>'
                    f'<td class="gate g-{cls}">{label}</td></tr>')
        qa = "".join(
            f'<details class="qa"><summary><span class="qmark">asked</span>{q}</summary>'
            f'<div class="qabody">{a}</div></details>' for q, a in ANSWERS.get(gi, []))
        # ⚠ The number and the count are SIBLINGS of the h3, not children — for the same reason
        # the item badge is. MEASURED: a question asked from this heading arrived tagged
        # "1Paid work can be lost when a video's address changes6". Third instance of one defect
        # (askbtn, then .badge/.flag, now .gn/.cnt), so the rule is now stated where headings are
        # built: NOTHING but the heading's own words goes inside an h2 or h3 on this page.
        groups_html += (f'<section class="grp"><div class="grphead"><span class="gn">{gi}</span>'
                        f'<h3>{title}</h3><span class="cnt">{len(items)}</span></div>'
                        f'<p class="framing">{framing}</p>{starthere}{qa}'
                        f'<div class="tw"><table class="glist"><tbody>{trs}</tbody></table></div>'
                        f'</section>')
    depmap = (dependency_svg(by_num) +
              '<details class="mmd"><summary>the same graph as mermaid source</summary>'
              '<p>For pasting where mermaid already renders — GitHub, an ADR, a PR body. This page '
              'draws its own diagram instead: it may not fetch a renderer, and vendoring one would '
              'add about a megabyte to draw seven nodes.</p>'
              f'<pre><code>{html.escape(dependency_mermaid(by_num))}</code></pre></details>')

    gates = {k: sum(1 for n in gate_of if gate_of[n] == k)
             for k in ("design", "decision", "study", "work")}

    def stat(n, label, cls=""):
        return f'<div class="stat {cls}"><span class="n">{n}</span><span class="l">{label}</span></div>'

    # ⟲ NOT TRUNCATED, and that is the fix. This column used to cut the Status cell at 110
    # characters, which meant the one table whose entire job is to say WHAT IS WRONG WITH THIS ROW
    # stopped mid-sentence. It also forced a nowrap monospace column so wide that the Item column
    # collapsed to roughly one word per line. Full text, wrapped, Item given room.
    flagrows = "".join(
        f'<tr><td class="mono"><a href="#i{r["num"]}">#{r["num"]}</a></td>'
        f'<td class="what">{plain(r["title"])}</td>'
        f'<td class="why">{md(r["status"])}</td></tr>' for r in flagged)
    # COLLAPSED BY DEFAULT (2026-08-22). Reproducing seven Status cells in full is the right content
    # — the truncated version cut mid-sentence in the one table whose job is to say what is wrong —
    # but at full length it pushed the actual backlog below the fold on every visit. A <details>
    # keeps both: the headline and the count are always visible, the evidence is one click away.
    # The count is the part that decides whether to look, so it must never be behind the click.
    tagopts = "".join(
        f'<option value="{html.escape(k)}">{html.escape(k)} — {op} open &middot; {tot} total</option>'
        for k, op, tot in bundle_options(rows))

    # ⚠ THE DRIFT IS ON THE PAGE, not only on a terminal nobody is watching. Every note here used
    # to be a refusal, and the refusal's whole audience was a stdout stream — which is precisely
    # how a five-day-old page kept looking current.
    # ⭐ backlog #110, and DELIBERATELY A SECOND BOX rather than a fifth kind of drift note. Every
    # other note here is about a row that IS on the page and says something odd about itself; this
    # one is about a row that is not on the page at all, and its remedy is in a different file. It
    # reuses `.drift`'s styling because a new class would need its own light and dark values and
    # the theme-token guard is right to demand them (backlog #102).
    unread_box = ""
    if unread:
        unread_box = ('<div class="drift"><b>&#9888; this view is INCOMPLETE — '
                      f'{len(unread)} line(s) in <code>docs/backlog.md</code> could not be read'
                      '</b><ul>'
                      # ⚠ `[1:]` — line 0 is the standalone SUMMARY the terminal needs, and
                      # this box has a heading saying the same thing (r2 finding L-4).
                      + "".join(f"<li>{html.escape(n)}</li>" for n in unread_note(unread)[1:])
                      + '</ul><p>Each line above sits inside a table but is not a row this page '
                        'can read, so it has no card here and is counted nowhere. Fix them in '
                        '<code>docs/backlog.md</code> — a row must begin with <code>|</code> and '
                        'its number cell must be a bare integer.</p></div>')

    drift = ""
    if drift_notes:
        drift = ('<div class="drift"><b>&#9888; this view is built from a grouping that has '
                 'drifted</b><ul>'
                 + "".join(f"<li>{html.escape(n)}</li>" for n in drift_notes)
                 + '</ul><p>' + (
                     'The items themselves are current — every row on this page was read from '
                     '<code>docs/backlog.md</code> in this run. What is out of date is the '
                     'hand-written grouping in <code>scripts/gen-backlog-page.py</code>.'
                     if not unread else
                     'Every row this page COULD read was read from <code>docs/backlog.md</code> in '
                     'this run — see the box above for the ones it could not. What is out of date '
                     'here is the hand-written grouping in '
                     '<code>scripts/gen-backlog-page.py</code>.')
                 + '</p></div>')

    callout = (f'<details class="callout"><summary><span class="warncount">{len(flagged)}</span>'
               f'rows carry a warning in their own Status cell'
               f'<span class="hint">read these before trusting any summary of them</span></summary>'
               f'<p>The rows the backlog itself flags as mis-recorded, half done, or read wrongly by '
               f'an earlier pass. Nothing is inferred — the &#9888; is written in the file.</p>'
               f'<div class="tw"><table class="warn"><thead><tr><th>#</th><th>Item</th>'
               f'<th>What its status says</th></tr></thead><tbody>{flagrows}</tbody></table></div>'
               f'</details>') if flagged else ""

    return f"""<title>Backlog — every item, in plain sight</title>
<style>
:root{{
  --ink:#12161c; --ink-2:#39424f; --ink-3:#6b7686; --ink-faint:#6b7686;
  --ground:#f7f6f3; --panel:#ffffff; --card:#ffffff; --line:#dfdcd5; --line-2:#eceae5;
  --measured:#0f7268; --problem:#ad3a22; --structural:#3d5a86;
  --pending:#a8690b; --pending-bg:#fdf4e3; --ink-soft:#39424f; --good:#0f7268;
  /* ⚠ THE SHIM'S OWN VOCABULARY, and these four are needed because THE LIFTED ASK TRAY READS
     THEM, with no fallback — measured: --bg, --rule, --structure by the tray and SHIM, --defect
     by the tray. Without a light value they keep the shim's DARK value on OS-dark + toggled-light,
     which is backlog #102 on this page. Mapped onto this page's own colours, not invented.
     ⛔ AN EARLIER VERSION OF THIS COMMENT SAID THE OPPOSITE AND WAS WRONG (r3 R3-4): it claimed
     SHIM's `body` paint WINS over this page's. It cannot — SHIM paints with
     `:where(html, body)`, which contributes ZERO specificity, and its own docstring says so:
     "This one is always losable." The page's `body{{background:var(--ground)}}` at (0,0,1) beats
     (0,0,0) whatever the source order. `--bg` does still reach `html`, whose background paints the
     canvas, so it shows in overscroll and gutters — real, but not what the old comment claimed. */
  --bg:#f7f6f3; --rule:#dfdcd5; --structure:#3d5a86; --defect:#ad3a22;
  --serif:Georgia,'Iowan Old Style','Times New Roman',serif;
  --sans:ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;
  --mono:ui-monospace,'SF Mono',Menlo,Consolas,monospace;
}}
@media (prefers-color-scheme:dark){{:root{{
  --ink:#e7e9ee; --ink-2:#a9b2c0; --ink-3:#7a8494; --ink-faint:#7a8494;
  --ground:#101318; --panel:#171b22; --card:#171b22; --line:#2a3039; --line-2:#20252d;
  --measured:#4fc9b8; --problem:#f0836a; --structural:#8fb0e0;
  --pending:#eab464; --pending-bg:#251d10; --ink-soft:#a9b2c0; --good:#4fc9b8;
  --bg:#101318; --rule:#2a3039; --structure:#8fb0e0; --defect:#f0836a;
}}}}
:root[data-theme="dark"]{{
  --ink:#e7e9ee; --ink-2:#a9b2c0; --ink-3:#7a8494; --ink-faint:#7a8494;
  --ground:#101318; --panel:#171b22; --card:#171b22; --line:#2a3039; --line-2:#20252d;
  --measured:#4fc9b8; --problem:#f0836a; --structural:#8fb0e0;
  --pending:#eab464; --pending-bg:#251d10; --ink-soft:#a9b2c0; --good:#4fc9b8;
  --bg:#101318; --rule:#2a3039; --structure:#8fb0e0; --defect:#f0836a;
}}
:root[data-theme="light"]{{
  --ink:#12161c; --ink-2:#39424f; --ink-3:#6b7686; --ink-faint:#6b7686;
  --ground:#f7f6f3; --panel:#ffffff; --card:#ffffff; --line:#dfdcd5; --line-2:#eceae5;
  --measured:#0f7268; --problem:#ad3a22; --structural:#3d5a86;
  --pending:#a8690b; --pending-bg:#fdf4e3; --ink-soft:#39424f; --good:#0f7268;
  --bg:#f7f6f3; --rule:#dfdcd5; --structure:#3d5a86; --defect:#ad3a22;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
     font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}}
/* UNSCOPED, and that is the point. This page had five link rules — .qabody a,
   .depmap a, .rootref a, .num a, td.mono a — and every one of them was correct.
   The links they did NOT reach (three, in .prose and .status, rendered from
   md(r['body']), so the count grows with every markdown link filed into a
   backlog item) fell through to the browser default #0000EE: 1.98:1 on the dark
   --ground and 1.84:1 on --card, against WCAG AA's 4.5. A per-container rule
   only ever covers the containers someone remembered; this one covers the next
   container too. More specific rules still win, including .num a's deliberate
   `color:inherit`. MEASURED 2026-08-29: --structural clears AA on all six
   surfaces, 6.40:1 worst case. */
a{{color:var(--structural)}}
.wrap{{max-width:56rem;margin:0 auto;padding:2.5rem 1.25rem 6rem}}
h1{{font-family:var(--serif);font-size:2.1rem;line-height:1.15;margin:0 0 .5rem;
    text-wrap:balance;letter-spacing:-.01em}}
.dek{{font-family:var(--serif);font-size:1.02rem;color:var(--ink-2);margin:0 0 1.75rem;
      max-width:44rem}}
h2{{font-family:var(--sans);font-size:.78rem;text-transform:uppercase;letter-spacing:.13em;
    color:var(--ink-3);margin:3rem 0 1rem;padding-bottom:.5rem;border-bottom:1px solid var(--line)}}
.stats{{display:flex;flex-wrap:wrap;gap:.5rem;margin:0 0 1.5rem}}
.stat{{flex:1 1 7rem;background:var(--panel);border:1px solid var(--line);border-radius:2px;
       padding:.7rem .85rem;border-left:3px solid var(--ink-3)}}
.stat .n{{display:block;font-family:var(--mono);font-size:1.5rem;font-variant-numeric:tabular-nums;
          line-height:1.1}}
.stat .l{{display:block;font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;
          color:var(--ink-3);margin-top:.2rem}}
.stat.high{{border-left-color:var(--problem)}} .stat.high .n{{color:var(--problem)}}
.stat.med{{border-left-color:var(--pending)}} .stat.med .n{{color:var(--pending)}}
.stat.done{{border-left-color:var(--measured)}} .stat.done .n{{color:var(--measured)}}

.grp{{margin:0 0 2rem}}
.grphead{{display:flex;align-items:baseline;gap:.6rem;margin:0 0 .35rem}}
.grp h3{{font-family:var(--serif);font-size:1.18rem;font-weight:400;margin:0;
         text-wrap:balance;flex:1;min-width:0}}
.gn{{font-family:var(--mono);font-size:.78rem;color:var(--ink-faint);border:1px solid var(--line);
     border-radius:2px;padding:.05rem .4rem;flex:none;align-self:center}}
.cnt{{margin-left:auto;font-family:var(--mono);font-size:.75rem;color:var(--ink-faint);flex:none;
      align-self:center}}
.framing{{font-family:var(--serif);font-size:.95rem;color:var(--ink-2);margin:0 0 .7rem;
          max-width:44rem}}
/* ── THE ASK BOX ─────────────────────────────────────────────────────────────────────────────
   MEASURED 2026-08-22 on the served page: `#qbox` computed `color: rgb(231,233,238)` over
   `background: rgb(255,255,255)` — near-white text on a white field, reported as "font color is
   too light". The tray is LIFTED verbatim by brief-compose.py and spliced AFTER this block, so a
   plain `#qbox` rule here loses the cascade; two ids win without touching the lifted code.
   Both sides are pinned, because fixing only the colour leaves the pair theme-dependent. */
#tray #qbox{{color:var(--ink);background:var(--card);border-color:var(--line);
     caret-color:var(--ink);-webkit-text-fill-color:var(--ink)}}
#tray #qbox::placeholder{{color:var(--ink-3);opacity:1;-webkit-text-fill-color:var(--ink-3)}}
#tray #qbox:focus{{outline:2px solid var(--structural);outline-offset:1px}}
.qa{{border:1px solid var(--line);border-left:3px solid var(--structural);border-radius:2px;
     background:var(--panel);padding:.5rem .8rem;margin:0 0 .8rem;max-width:46rem}}
.qa > summary{{font-family:var(--serif);font-size:.92rem;color:var(--ink);cursor:pointer;
     list-style:none;border-bottom:0;display:flex;gap:.5rem;align-items:baseline}}
.qa > summary::-webkit-details-marker{{display:none}}
.qmark{{font-family:var(--sans);font-size:.6rem;font-weight:700;text-transform:uppercase;
     letter-spacing:.09em;color:var(--structural);border:1px solid var(--structural);
     border-radius:2px;padding:.05rem .3rem;flex:none;align-self:center}}
.qabody{{font-family:var(--serif);font-size:.92rem;line-height:1.65;color:var(--ink-2);
     margin-top:.6rem;padding-top:.6rem;border-top:1px solid var(--line-2)}}
.qabody p{{margin:.55rem 0}}
.qabody code{{font-family:var(--mono);font-size:.85em;background:var(--line-2);
     padding:.05rem .25rem;border-radius:2px}}
.qabody a{{color:var(--structural)}}
table.glist{{border-top:1px solid var(--line)}}
table.glist td{{font-size:.92rem;line-height:1.5}}
table.glist td:first-child{{width:4.6rem}}
table.glist td:nth-child(2){{font-family:var(--serif);color:var(--ink-2)}}
table.glist tr:hover td{{background:var(--panel)}}
.mapo{{font-family:var(--serif);font-size:1.18rem;font-weight:400;margin:2rem 0 .35rem}}
.depmap{{margin:0 0 .8rem;max-width:46rem}}
.depmap svg{{width:100%;height:auto;display:block}}
.depmap .n{{fill:var(--panel);stroke:var(--line);stroke-width:1}}
.depmap .n-root{{fill:var(--panel);stroke:var(--structural);stroke-width:2}}
.depmap .n-kill{{stroke:var(--problem)}} .depmap .n-part{{stroke:var(--pending)}}
.depmap .n-block{{stroke:var(--ink-3)}} .depmap .n-live{{stroke:var(--measured)}}
.depmap .e{{fill:none;stroke-width:1.5;opacity:.85}}
.depmap .e-kill{{stroke:var(--problem);stroke-dasharray:4 3}}
.depmap .e-part{{stroke:var(--pending);stroke-dasharray:6 3}}
.depmap .e-block{{stroke:var(--ink-3);stroke-dasharray:2 3}}
.depmap .e-live{{stroke:var(--measured)}}
.depmap .elabel{{font-family:var(--sans);font-size:9.5px;letter-spacing:.04em;
     text-transform:uppercase;fill:var(--ink-3)}}
.depmap .elabel.e-kill{{fill:var(--problem)}} .depmap .elabel.e-part{{fill:var(--pending)}}
.depmap .elabel.e-live{{fill:var(--measured)}}
.depmap .nid{{font-family:var(--mono);font-size:11px;fill:var(--ink-3)}}
.depmap .ntitle{{font-family:var(--sans);font-size:11.5px;fill:var(--ink)}}
.depmap .rootlbl{{font-family:var(--serif);font-size:13px;fill:var(--ink);font-weight:600}}
.depmap .rootsub{{font-family:var(--sans);font-size:9px;fill:var(--structural);
     text-transform:uppercase;letter-spacing:.09em}}
.depmap a{{cursor:pointer}} .depmap a:hover .n{{fill:var(--line-2)}}
.depmap figcaption{{font-family:var(--serif);font-size:.82rem;color:var(--ink-3);margin-top:.4rem}}
.mmd{{margin:0 0 1.4rem;max-width:46rem}}
.mmd > summary{{font-size:.76rem;color:var(--ink-3);cursor:pointer;list-style:none;
     border-bottom:1px dashed var(--line);display:inline-block}}
.mmd > summary::-webkit-details-marker{{display:none}}
.mmd p{{font-family:var(--serif);font-size:.85rem;color:var(--ink-2);margin:.5rem 0}}
.mmd pre{{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:2px;
     padding:.7rem .85rem;font-family:var(--mono);font-size:.72rem;line-height:1.5;
     white-space:pre;color:var(--ink-2)}}
.depmap .rootdetail{{font-family:var(--serif);font-size:.9rem;color:var(--ink-2);
      margin:0 0 .8rem;max-width:44rem}}
.depmap .rootdetail b{{color:var(--ink)}}
.rootref{{font-family:var(--sans);font-size:.78rem;color:var(--ink-3);margin:0 0 .7rem;
      padding-left:.7rem;border-left:2px solid var(--structural);max-width:46rem}}
.rootref b{{font-family:var(--mono);color:var(--ink)}}
.rootref a{{color:var(--structural)}}
.dep{{display:inline-block;font-family:var(--sans);font-size:.62rem;font-weight:700;
      text-transform:uppercase;letter-spacing:.07em;border-radius:2px;padding:.05rem .35rem;
      margin-left:.45rem;white-space:nowrap;cursor:help;vertical-align:.08em}}
.depnote{{font-family:var(--sans);font-size:.72rem;color:var(--ink-3);margin-left:.4rem}}
.d-kill{{background:var(--problem);color:var(--ground)}}
.d-part{{background:var(--pending);color:var(--ground)}}
.d-block{{background:var(--ink-3);color:var(--ground)}}
.d-live{{background:var(--measured);color:var(--ground)}}
tr.dep-row td{{opacity:.92}}
.depbox{{display:flex;flex-wrap:wrap;gap:.2rem .6rem;align-items:baseline;margin:.4rem 0 0;
      padding:.35rem .6rem;border-radius:2px;font-size:.78rem;background:var(--line-2)}}
.depbox b{{font-family:var(--sans);font-size:.62rem;font-weight:700;text-transform:uppercase;
      letter-spacing:.07em;border-radius:2px;padding:.05rem .35rem;color:var(--ground)}}
.depbox span{{font-family:var(--serif);color:var(--ink-2)}}
.depbox.d-kill b{{background:var(--problem)}} .depbox.d-part b{{background:var(--pending)}}
.depbox.d-block b{{background:var(--ink-3)}} .depbox.d-live b{{background:var(--measured)}}
.dot{{display:inline-block;width:.5rem;height:.5rem;border-radius:50%;margin-left:.4rem;
      vertical-align:.05em}}
.dot.s-high,.dot.s-crit{{background:var(--problem)}}
.dot.s-med{{background:var(--pending)}}
.dot.s-low,.dot.s-none{{background:var(--line)}}
.gate{{font-family:var(--sans);font-size:.7rem;white-space:nowrap;width:9.5rem;
       color:var(--ink-faint);text-transform:uppercase;letter-spacing:.05em}}
.gate.g-design,.gate.g-decision,.gate.g-study{{color:var(--pending);font-weight:600}}
.gate.g-work{{color:var(--measured)}}

.bar{{position:sticky;top:0;z-index:5;background:var(--ground);border-bottom:1px solid var(--line);
      padding:.7rem 0;margin:0 0 1.5rem;display:flex;flex-wrap:wrap;gap:.4rem;align-items:center}}
.bar b{{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-3);
        margin-right:.3rem}}
button.f{{font:inherit;font-size:.8rem;padding:.25rem .7rem;border-radius:100px;cursor:pointer;
          background:transparent;color:var(--ink-2);border:1px solid var(--line)}}
button.f:hover{{border-color:var(--ink-3)}}
button.f[aria-pressed="true"]{{background:var(--ink);color:var(--ground);border-color:var(--ink)}}
button.f:focus-visible{{outline:2px solid var(--structural);outline-offset:2px}}

.seen{{border:1px solid var(--line);border-left:3px solid var(--structural);border-radius:2px;
       background:var(--panel);padding:.6rem .9rem;margin:0 0 .8rem}}
.seenline{{display:flex;flex-wrap:wrap;gap:.5rem .9rem;align-items:center;font-size:.82rem}}
.seenline b{{font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;color:var(--ink-3)}}
#seencounts{{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--ink)}}
.since{{margin-left:auto;font-size:.72rem;color:var(--ink-3);display:flex;gap:.35rem;
        align-items:center}}
.since select{{font:inherit;font-size:.78rem;background:var(--card);color:var(--ink);
               border:1px solid var(--line);border-radius:2px;padding:.1rem .3rem}}
button.f[disabled]{{opacity:.4;cursor:default}}
.badge{{font-family:var(--sans);font-size:.6rem;font-weight:700;text-transform:uppercase;
        letter-spacing:.09em;border-radius:2px;padding:.1rem .35rem;flex:none;align-self:center;
        color:var(--ground)}}
.badge.b-new{{background:var(--structural)}}
.badge.b-updated{{background:var(--pending)}}
.badge.b-closed{{background:var(--measured)}}
.item[data-fresh="1"]{{box-shadow:inset 3px 0 0 var(--structural)}}
.age{{font-size:.7rem;color:var(--ink-faint);font-family:var(--mono);white-space:nowrap;
      align-self:center}}
.age.unknown{{color:var(--pending)}}
.age time{{border-bottom:1px dotted var(--line);cursor:help}}
.diffbox{{margin-top:.8rem;padding-top:.7rem;border-top:1px solid var(--line-2)}}
.diff{{font-family:var(--serif);font-size:.9rem;line-height:1.7;color:var(--ink-3);margin-top:.6rem;
       max-width:44rem}}
.diff del{{background:rgba(173,58,34,.14);color:var(--problem);text-decoration:line-through;
           text-decoration-thickness:1px;padding:.02rem .1rem;border-radius:2px}}
.diff ins{{background:rgba(15,114,104,.14);color:var(--measured);text-decoration:none;
           padding:.02rem .1rem;border-radius:2px}}
@media (prefers-color-scheme:dark){{
  .diff del{{background:rgba(240,131,106,.16)}} .diff ins{{background:rgba(79,201,184,.14)}}
}}
:root[data-theme="dark"] .diff del{{background:rgba(240,131,106,.16)}}
:root[data-theme="dark"] .diff ins{{background:rgba(79,201,184,.14)}}
.item{{display:flex;gap:.9rem;background:var(--card);border:1px solid var(--line);border-radius:2px;
       padding:.85rem 1rem;margin-bottom:.5rem;border-left:3px solid var(--line)}}
.item[data-sev="crit"],.item[data-sev="high"]{{border-left-color:var(--problem)}}
.item[data-sev="med"]{{border-left-color:var(--pending)}}
.item[data-sev="low"]{{border-left-color:var(--ink-3)}}
.item[data-sev="done"]{{border-left-color:var(--measured);opacity:.72}}
.item[hidden]{{display:none}}
.num{{font-family:var(--mono);font-size:.9rem;color:var(--ink-3);min-width:2.4rem;padding-top:.15rem;
      font-variant-numeric:tabular-nums}}
.num a{{color:inherit;text-decoration:none}} .num a:hover{{color:var(--ink)}}
.body{{flex:1;min-width:0}}
/* The badge and the ⚠ flag are SIBLINGS of the h3, never children of it — the Ask tray reads a
   heading by walking its childNodes and skipping only `.askbtn`, so anything else living inside
   an h3 is silently prepended to the question the reader sends. That exact defect is recorded in
   the explain-diff skill ("…had never workedask"); putting a badge in there would reintroduce it
   under a new class name. */
.titleline{{display:flex;align-items:baseline;gap:.45rem;margin-bottom:.35rem}}
.item h3{{font-family:var(--sans);font-size:.98rem;font-weight:600;margin:0;line-height:1.35;
          flex:1;min-width:0}}
.flag{{font-family:var(--sans);font-size:.62rem;font-weight:600;text-transform:uppercase;
       letter-spacing:.08em;color:var(--pending);background:var(--pending-bg);
       border:1px solid var(--pending);border-radius:100px;padding:.05rem .45rem;flex:none;
       align-self:center;white-space:nowrap}}
.meta{{display:flex;flex-wrap:wrap;gap:.35rem;margin-bottom:.2rem}}
.chip{{font-size:.72rem;color:var(--ink-3);border:1px solid var(--line-2);border-radius:2px;
       padding:.05rem .4rem;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.chip b{{font-weight:600;text-transform:uppercase;letter-spacing:.06em;font-size:.62rem;
         color:var(--ink-faint)}}
.chip code{{font-family:var(--mono);font-size:.88em}}
/* A tag is a CONTROL, not decoration — it filters on click, so it must look pressable and keep a
   visible focus ring. Sized like .chip on purpose: same row, same weight, one extra affordance. */
.tag{{font-size:.72rem;font-family:inherit;color:var(--ink-2);background:var(--panel);
  border:1px solid var(--line-2);border-radius:2px;padding:.1rem .4rem;margin-right:.3rem;
  cursor:pointer;letter-spacing:.02em}}
.tag:hover{{color:var(--ink);border-color:var(--ink-3)}}
.tag:focus-visible{{outline:2px solid var(--measured);outline-offset:1px}}
.drift{{border:1px solid var(--pending);border-left-width:3px;border-radius:2px;
  padding:.6rem .8rem;margin:.8rem 0;font-size:.86rem;background:var(--pending-bg)}}
.drift b{{display:block;margin-bottom:.3rem}}
.drift ul{{margin:.3rem 0 .4rem 1.1rem}}
.drift p{{margin:.3rem 0 0;color:var(--ink-2)}}
details{{margin-top:.4rem}}
summary{{font-size:.76rem;color:var(--ink-3);cursor:pointer;list-style:none;display:inline-block;
         border-bottom:1px dashed var(--line)}}
summary::-webkit-details-marker{{display:none}}
summary:hover{{color:var(--ink-2)}}
.prose{{font-family:var(--serif);font-size:.95rem;line-height:1.6;color:var(--ink-2);
        margin:.7rem 0 0;max-width:44rem}}
.prose code,.status code,.why code{{font-family:var(--mono);font-size:.85em;
        background:var(--line-2);padding:.05rem .25rem;border-radius:2px}}
.status{{font-family:var(--serif);font-size:.9rem;color:var(--ink-2);margin-top:.8rem;
         padding-top:.7rem;border-top:1px solid var(--line-2)}}
.status b{{font-family:var(--sans);font-size:.62rem;text-transform:uppercase;letter-spacing:.09em;
           color:var(--ink-faint);display:block;margin-bottom:.2rem}}
.callout{{background:var(--pending-bg);border:1px solid var(--pending);border-left-width:3px;
          border-radius:2px;padding:.7rem 1.15rem;margin:0 0 1rem}}
.callout > summary{{font-family:var(--sans);font-size:.9rem;color:var(--pending);cursor:pointer;
        list-style:none;display:flex;align-items:baseline;gap:.5rem;flex-wrap:wrap;
        border-bottom:0;font-weight:600}}
.callout > summary::-webkit-details-marker{{display:none}}
/* A disclosure needs to LOOK like one, or a collapsed section reads as the whole section. */
.callout > summary::after{{content:"▸ show";font-weight:400;font-size:.72rem;margin-left:auto;
        text-transform:uppercase;letter-spacing:.07em;opacity:.85}}
.callout[open] > summary::after{{content:"▾ hide"}}
.callout[open] > summary{{margin-bottom:.3rem}}
.warncount{{font-family:var(--mono);font-size:1rem;font-variant-numeric:tabular-nums;
        border:1px solid var(--pending);border-radius:2px;padding:0 .35rem;flex:none}}
.hint{{font-family:var(--serif);font-weight:400;font-size:.82rem;color:var(--ink-3);
        font-style:italic}}
.callout p{{font-family:var(--serif);font-size:.93rem;margin:.4rem 0 .8rem;color:var(--ink-2)}}
.tw{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;font-size:.84rem}}
th,td{{text-align:left;padding:.45rem .6rem;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font-size:.65rem;text-transform:uppercase;letter-spacing:.09em;color:var(--ink-faint)}}
td.mono{{font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}}
td.mono a{{color:var(--structural)}}
table.warn td.what{{font-family:var(--sans);font-weight:600;min-width:13rem;width:26%}}
table.warn td.why{{font-family:var(--serif);font-size:.9rem;line-height:1.5;color:var(--ink-2)}}
.foot{{margin-top:3rem;padding-top:1rem;border-top:1px solid var(--line);font-family:var(--mono);
       font-size:.74rem;color:var(--ink-3);line-height:1.9}}
.foot b{{color:var(--ink-2);font-weight:600}}
.empty{{font-family:var(--serif);color:var(--ink-3);padding:1.5rem 0}}
@media (max-width:720px){{
  table.warn td.what{{min-width:8rem}}
  .gate{{width:auto}}
}}
@media (max-width:620px){{.item{{flex-direction:column;gap:.2rem}} h1{{font-size:1.65rem}}}}
{page_chrome.chrome_css()}
</style>

<div class="wrap">
<h1>The backlog, item by item</h1>
{page_chrome.chrome_bar("backlog-table", generated_at)}
<p class="dek">Every row of <code>docs/backlog.md</code>, parsed in this run — not summarised. The
severity stripe records severity <em>when the item was filed</em>; the Status cell is the only live
truth, which is why it is reproduced verbatim inside every card.</p>

<div class="stats">
  {stat(len(open_rows), "open")}
  {stat(by_sev['crit'] + by_sev['high'], "filed high", "high")}
  {stat(gates['design'], "need a design talk", "med")}
  {stat(gates['decision'] + gates['study'], "need your decision", "med")}
  {stat(gates['work'], "just need doing", "done")}
</div>

{callout}

<h2>What these actually are</h2>
<p class="dek">Grouped by what the item <em>is</em>, not by how loud its marker is. The group
headings are the one part of this page written by hand and the only part that can go out of date —
every item below was read from the file in this run. An open item can never go missing: anything no
group names is listed under <em>The rest, one line each</em>, and anything a group names that is no
longer open is dropped with a note at the top. Each number opens its full entry.</p>

<p class="dek" id="vocab"><b>Three words on this page mean three different things, and it is worth
thirty seconds to keep them apart.</b> A <b>tag</b> answers <em>what is this item about?</em> — it
is read straight out of the file's Bundle column, it is how the filter above works, and it cannot
be wrong, only useless. A <b>group</b> answers <em>what do these items have in common that is worth
asserting?</em> — it is a <em>claim</em>, written by hand, and it <em>can</em> be wrong, which is
why every group carries a stated falsifier and why belonging to one is optional. A <b>slice</b> is
neither: it is a piece of work that has to land <em>first</em>, and items are not filed <em>in</em>
it — they are joined <em>to</em> it by one of four edges, because the interesting question is not
which bucket an item sits in but whether it still exists after the slice lands. Tags and groups
both answer <em>which items?</em>; a slice answers <em>in what order, and does this survive?</em>
See the map below.</p>

<h3 class="mapo" id="order">The order to start in</h3>
<p class="framing">Every dependency recorded, drawn from the same data as the markers beside each
item. A root is not always a backlog row — the one below is a parked decision, which is why it
could not be expressed by pointing at an item number.</p>
{depmap}

{groups_html}

<h2>Every row, as filed</h2>

<div class="seen" id="seen" hidden>
  <div class="seenline">
    <b id="seentitle">Since your last visit</b>
    <span id="seencounts"></span>
    <label class="since">baseline
      <select id="sincesel">
        <option value="visit" selected>last visit</option>
        <option value="7">7 days</option>
        <option value="30">30 days</option>
        <option value="0">everything</option>
      </select>
    </label>
    <button class="f" id="onlychanged" aria-pressed="false">show only these</button>
    <button class="f" id="marks">mark all as seen</button>
  </div>
</div>

<div class="bar" role="group" aria-label="Filter items">
  <b>show</b>
  <button class="f" data-k="state" data-v="open" aria-pressed="true">open</button>
  <button class="f" data-k="state" data-v="closed" aria-pressed="false">closed</button>
  <button class="f" data-k="state" data-v="all" aria-pressed="false">all</button>
  <span style="flex:1"></span>
  <b>severity</b>
  <button class="f" data-k="sev" data-v="high" aria-pressed="false">high+</button>
  <button class="f" data-k="sev" data-v="med" aria-pressed="false">medium</button>
  <button class="f" data-k="sev" data-v="low" aria-pressed="false">low</button>
  <button class="f" data-k="sev" data-v="all" aria-pressed="true">any</button>
  <span style="flex:1"></span>
  <b><label for="tagsel">tag</label></b>
  <select id="tagsel" aria-label="Filter by tag">
    <option value="all">any tag — {len(open_rows)} open &middot; {len(rows)} total</option>{tagopts}
  </select>
  <button class="f" id="tagclear" hidden>clear tag</button>
</div>
{unread_box}{drift}

<div id="list">
{''.join(card(r) for r in open_rows)}
{''.join(card(r) for r in closed_rows)}
</div>
<p class="empty" id="none" hidden>Nothing matches that combination.</p>

<div class="foot">
<b>Source</b> docs/backlog.md @ <b>{sha}</b> — last edited {edited}<br>
<b>Rows parsed</b> {len(rows)} &nbsp;·&nbsp; <b>open</b> {len(open_rows)} &nbsp;·&nbsp;
<b>closed</b> {len(closed_rows)} &nbsp;·&nbsp; open by severity: crit {by_sev['crit']},
high {by_sev['high']}, med {by_sev['med']}, low {by_sev['low']}, unmarked {by_sev['none']}<br>
<b>Open/closed rule</b> the Status cell contains ✅ — the same cell and the same test
<code>scripts/check-docs.py</code> uses (its <code>CELL_SPLIT</code> is imported, not copied)<br>
<b>Regenerate</b> python3 scripts/gen-backlog-page.py &nbsp;·&nbsp; <b>Built</b> {stamp}
</div>
</div>

<script>
(function(){{
  var f = {{state:'open', sev:'all', tag:'all'}};
  var items = [].slice.call(document.querySelectorAll('.item'));
  function apply(){{
    var n = 0;
    items.forEach(function(el){{
      var st = el.dataset.state, sv = el.dataset.sev;
      var okS = f.state === 'all' || st === f.state;
      var okV = f.sev === 'all'
        || (f.sev === 'high' && (sv === 'high' || sv === 'crit'))
        || (f.sev === 'med' && sv === 'med')
        || (f.sev === 'low' && (sv === 'low' || sv === 'none'));
      // TAGS ARE A LIST, not a value: an item tagged `cloud / money` carries both `cloud` and
      // `cloud / money`, so asking for the family finds the members.
      var tg = (el.dataset.tags || '').split('|');
      var okT = f.tag === 'all' || tg.indexOf(f.tag) !== -1;
      var show = okS && okV && okT;
      el.hidden = !show;
      if (show) n++;
    }});
    document.getElementById('none').hidden = n > 0;
  }}
  document.querySelectorAll('button.f').forEach(function(b){{
    b.addEventListener('click', function(){{
      var k = b.dataset.k;
      f[k] = b.dataset.v;
      document.querySelectorAll('button.f[data-k="' + k + '"]').forEach(function(o){{
        o.setAttribute('aria-pressed', String(o === b));
      }});
      apply();
    }});
  }});
  var tagsel = document.getElementById('tagsel');
  var tagclear = document.getElementById('tagclear');
  function setTag(v){{
    f.tag = v;
    if (tagsel.value !== v) tagsel.value = v;
    tagclear.hidden = (v === 'all');
    apply();
  }}
  tagsel.addEventListener('change', function(){{ setTag(tagsel.value); }});
  tagclear.addEventListener('click', function(){{ setTag('all'); }});
  // Clicking a tag ON a card filters to it — the chip is the control, so the reader never has to
  // find the same word again in a dropdown of 27.
  document.addEventListener('click', function(ev){{
    var b = ev.target.closest ? ev.target.closest('button.tag') : null;
    if (!b) return;
    ev.preventDefault();
    setTag(b.dataset.tag);
    window.scrollTo({{top: 0, behavior: 'smooth'}});
  }});

  // A deep link (#i41) must win over the default filter, or the row it points at is hidden.
  if (location.hash && /^#i\\d+$/.test(location.hash)) {{
    var t = document.querySelector(location.hash);
    if (t && t.dataset.state === 'closed') {{
      document.querySelector('button.f[data-k="state"][data-v="all"]').click();
      t.scrollIntoView();
    }}
  }}
  apply();

  // ── "since your last visit" ────────────────────────────────────────────────────────────────
  //
  // The baseline is PER READER, and this page is static with no server-side notion of who is
  // looking, so it lives in localStorage. A first visit sets the baseline to now and says so
  // rather than flooring the reader with 41 NEW badges — the honest reading of "since your last
  // visit" when there has not been one.
  var KEY = 'backlog-table:lastSeen';
  var seen = document.getElementById('seen');
  var counts = document.getElementById('seencounts');
  var title = document.getElementById('seentitle');
  var sel = document.getElementById('sincesel');
  var only = document.getElementById('onlychanged');
  var mark = document.getElementById('marks');
  var newest = 0;
  items.forEach(function(el){{
    var c = +(el.dataset.changed || 0);
    if (c > newest) newest = c;
  }});

  var stored = parseInt(localStorage.getItem(KEY) || '', 10);
  var firstVisit = !(stored > 0);
  if (firstVisit) {{ stored = Math.floor(Date.now()/1000); localStorage.setItem(KEY, String(stored)); }}

  function baseline(){{
    var v = sel.value;
    if (v === 'visit') return stored;
    if (v === '0') return 0;
    return Math.floor(Date.now()/1000) - (+v) * 86400;
  }}

  function classify(){{
    var since = baseline(), n = 0, c = 0, u = 0, unknown = 0;
    items.forEach(function(el){{
      var b = el.querySelector('.badge');
      if (el.dataset.nohist) {{ unknown++; el.dataset.fresh = '0'; b.hidden = true; return; }}
      var first = +el.dataset.first, chg = +el.dataset.changed;
      var label = null;
      if (first > since) {{ label = 'new'; n++; }}
      else if (chg > since) {{
        if (el.dataset.state === 'closed') {{ label = 'closed'; c++; }}
        else {{ label = 'updated'; u++; }}
      }}
      el.dataset.fresh = label ? '1' : '0';
      b.hidden = !label;
      if (label) {{ b.textContent = label; b.className = 'badge b-' + label; }}
    }});
    var parts = [];
    if (n) parts.push(n + ' new');
    if (c) parts.push(c + ' closed');
    if (u) parts.push(u + ' updated');
    title.textContent = firstVisit && sel.value === 'visit'
      ? 'First visit — baseline set to now'
      : (sel.value === 'visit' ? 'Since your last visit' : 'Since ' +
         (sel.value === '0' ? 'the beginning' : sel.value + ' days ago'));
    counts.textContent = parts.length ? parts.join('  ·  ')
      : (firstVisit && sel.value === 'visit'
         ? 'changes will be highlighted from now on'
         : 'nothing has changed');
    if (unknown) counts.textContent += '  ·  ' + unknown + ' with no history';
    only.disabled = !parts.length;
    seen.hidden = false;
    if (only.getAttribute('aria-pressed') === 'true' && !parts.length) {{
      only.setAttribute('aria-pressed', 'false');
    }}
    apply();
  }}

  // Folded into the existing filter rather than bolted beside it — two independent hide/show
  // passes over the same elements is how one of them ends up silently winning.
  var baseApply = apply;
  apply = function(){{
    baseApply();
    if (only.getAttribute('aria-pressed') !== 'true') return;
    var n = 0;
    items.forEach(function(el){{
      if (!el.hidden && el.dataset.fresh !== '1') el.hidden = true;
      if (!el.hidden) n++;
    }});
    document.getElementById('none').hidden = n > 0;
  }};

  sel.addEventListener('change', classify);
  only.addEventListener('click', function(){{
    only.setAttribute('aria-pressed', String(only.getAttribute('aria-pressed') !== 'true'));
    apply();
  }});
  mark.addEventListener('click', function(){{
    stored = Math.max(newest, Math.floor(Date.now()/1000));
    localStorage.setItem(KEY, String(stored));
    firstVisit = false;
    sel.value = 'visit';
    only.setAttribute('aria-pressed', 'false');
    classify();
  }});
  classify();
}})();
</script>
<script>{page_chrome.chrome_script()}</script>
"""


# ─── self-test ──────────────────────────────────────────────────────────────────────────────────

SAMPLE = """## Items

| # | Item | Touches | Size | Bundle | Status |
|---|------|---------|------|--------|--------|
| 1 | 🟠 **Alpha** — a thing that `breaks` | lib/a.ts | M + design | A | pending |
| 2 | ✅ (was 🟡) **Beta** — done now | lib/b.ts | S | A | ✅ **MERGED** |
| 3 | 🟢 **Gamma** — small | c.ts | XS | (loose) | ⚠ half done |

## Found during testing (2026-06-19/20)

| # | Item | Status |
|---|------|--------|
| 9 | ✅ **Delta** — a bug | ✅ fixed |
"""


# ⚠ Every row below is one a HUMAN would call a row of this table, and every one of them is a
# decoration this file's own house style already uses somewhere: a ⭐ headline marker, a `#` before
# an id, an indent. `parse` reads none of them, and until backlog #110 it said nothing.
DECORATED = """## Items

| # | Item | Touches | Size | Bundle | Status |
|---|------|---------|------|--------|--------|
| 1 | 🟠 **Alpha** — read normally | a.ts | S | A | pending |
| ⭐2 | 🟠 **Star** — a ⭐ ahead of the number | b.ts | S | A | pending |
| #3 | 🟠 **Hash** — a # ahead of the number | c.ts | S | A | pending |
 | 4 | 🟠 **Indent** — one leading space | d.ts | S | A | pending |
⭐| 5 | 🟠 **Outside** — the ⭐ is before the pipe, so nothing about this line starts with one | e.ts | S | A | pending |
"""


# ── link contrast, MEASURED on the emitted stylesheet ───────────────────────────────────────────
# ⟲ Added 2026-08-29. This page carried FIVE per-container link rules, every one of them correct,
# and still served three links at the browser default #0000EE — 1.98:1 on the dark --ground, 1.84:1
# on --card, against WCAG AA's 4.5 — because those links sat in containers nobody had enumerated
# (.prose and .status, rendered from md(r['body']), so the count grows with the backlog).
#
# A guard asserting those five selectors were PRESENT would have passed on exactly that page. So
# this measures the RATIO instead, across every palette block. The sibling defect in
# gen-dashboard.py was found the same day by a guard that checked presence and let three
# colour-value mutations through; see the note above contrast_failures there.
# ⟲ Round 2 replaced a flat FOREGROUNDS x SURFACES cross-product, which was wrong in both
# directions and passed only because the data hid it. It MISSED `.num a{color:inherit}` — 70 of
# this page's links, taking their colour from `.num` (`--ink-3`) — so a mutation to 1.37:1
# SURVIVED at 64/64. And it would have over-asserted: `--ink-3` measures 4.26:1 on `--ground`
# and 4.22:1 on `--pending-bg`, under AA, so simply adding it to the foreground list reddens a
# CORRECT page. `.num a` only ever renders inside `.item`, whose background is `--card`.
#
# So: explicit (foreground, surface) pairs. The cross-product asserted pairs that never occur
# and missed pairs that do.
LINK_MIN = 4.5
LINK_PAIRS: tuple[tuple[str, str], ...] = (
    # `a` is unscoped, so its colour can land on any surface the page paints.
    ("--structural", "--ground"), ("--structural", "--card"),
    ("--structural", "--panel"), ("--structural", "--pending-bg"),
    ("--ink-3", "--card"),        # .num a inherits .num's colour; .item is --card
    ("--ink", "--card"),          # .num a:hover
)

# Every selector in this page's stylesheet that colours a link, and where its colour comes from.
# `link_rule_drift` asserts the emitted CSS still matches this exactly — that is the ONLY thing
# keeping LINK_PAIRS honest as the page grows. Round 2's defect was a link rule the model had
# never heard of; a new one now fails loudly instead of being silently unmeasured.
# `.depmap a` sets no colour (SVG, coloured by fill) and is listed so its absence is deliberate.
LINK_RULES: dict[str, str] = {
    "a": "var(--structural)",
    ".qabody a": "var(--structural)",
    ".rootref a": "var(--structural)",
    "td.mono a": "var(--structural)",
    ".num a": "inherit",
    ".num a:hover": "var(--ink)",
    ".depmap a": "",
    ".depmap a:hover .n": "",
}

# ⟲ Round 2, second pass. Modelling `.num a` as "inherit" was NOT enough: repointing the
# PARENT — `.num{color:var(--ink-3)}` -> `var(--line)`, 1.37:1 — left `.num a` itself untouched,
# so the drift check saw nothing and the contrast check went on measuring `--ink-3`, a variable
# the links no longer use. MEASURED: that mutation survived at 69/69 against the first version
# of this guard. An inherited colour has to be modelled at its SOURCE, or the model describes a
# page that no longer exists.
LINK_INHERITS: dict[str, tuple[str, str]] = {
    ".num a": (".num", "var(--ink-3)"),
}


def _luminance(colour: str) -> float:
    """WCAG relative luminance of an #rgb or #rrggbb colour."""
    h = colour.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ShapeError(f"not a hex colour: {colour!r}")

    def chan(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def link_contrast_errors(page: str, minimum: float = LINK_MIN) -> list[str]:
    """Every link-colour / surface pair below `minimum`, in EVERY :root palette.

    All four blocks are checked, not just the two media-query ones.

    ⚠ THIS SENTENCE USED TO BE FALSE, and that is worth keeping. It read "the page has a
    manual theme toggle, so `:root[data-theme=…]` is live CSS, not decoration" — and no
    such toggle existed anywhere in the repo. Measured 2026-08-31 for backlog #76:
    `setAttribute('data-theme')` and `documentElement.dataset.theme` returned ZERO hits
    across `scripts/` and across every live page. The palettes were written in
    anticipation, the control was never built, and a guard spent real work validating
    renderings no reader could reach while stating the opposite as fact. It is true now
    because `page_chrome.theme_control()` is on the page and `page_chrome.assert_wired()`
    refuses to write a page where it would not work — a claim about a mechanism needs the
    mechanism, not a comment.

    RAISES ShapeError when it cannot find the palettes or the unscoped rule. A contrast
    check that never reached a stylesheet has not passed — and from a list of zero
    failures the two are indistinguishable.
    """
    blocks = re.findall(r'(:root(?:\[data-theme="\w+"\])?)\{([^}]*)\}', page)
    if len(blocks) < 2:
        raise ShapeError(f"expected several :root palettes, found {len(blocks)}")
    # ANCHORED to the start of a line, and that is load-bearing. A bare substring test
    # for "a{color:var(--structural)}" is satisfied by the SCOPED rules — `.qabody a{…}`,
    # `.rootref a{…}` and `td.mono a{…}` all contain it — so it stays true with the
    # unscoped rule deleted, which is precisely the state that shipped. Measured while
    # writing this guard: the unanchored version passed on the defect it exists to catch.
    if not re.search(r"^a\{color:var\(--structural\)\}", page, re.M):
        raise ShapeError("no UNSCOPED a{} rule — links outside the scoped selectors "
                         "fall back to the browser default")

    def hexes(body: str) -> dict[str, str]:
        return dict(re.findall(r"(--[a-z0-9-]+):\s*(#[0-9a-fA-F]{3,6})\b", body))

    base = hexes(blocks[0][1])
    if not base:
        raise ShapeError("the first :root palette parsed EMPTY")
    out: list[str] = []
    for sel, body in blocks:
        pal = {**base, **hexes(body)}          # later blocks OVERRIDE, they do not replace
        for fg, bg in LINK_PAIRS:
            if fg not in pal or bg not in pal:
                out.append(f"{sel}: {fg} or {bg} is undefined")
                continue
            a, b = _luminance(pal[fg]), _luminance(pal[bg])
            ratio = (max(a, b) + 0.05) / (min(a, b) + 0.05)
            if ratio < minimum:
                out.append(f"{sel}: {fg} {pal[fg]} on {bg} {pal[bg]} = {ratio:.2f}:1")
    return out


def link_rule_drift(page: str) -> list[str]:
    """Selectors that colour a link but are not in LINK_RULES, and vice versa.

    LINK_PAIRS is a hand-written model of where link colours land, and a hand-written model
    goes stale the moment someone adds a rule. This is what makes it fail loudly instead:
    round 2's defect was `.num a{color:inherit}`, a rule the model had never heard of, whose
    70 links were therefore never measured. Any NEW link rule now reddens this case until it
    is added here and paired in LINK_PAIRS.
    """
    css = page[page.index("<style>"):page.index("</style>")]
    colours: dict[str, str] = {}
    for sel, body in re.findall(r"([^{}\n]*?)\{([^}]*)\}", css):
        m = re.search(r"color:\s*([^;}]+)", body)
        colours[sel.strip()] = m.group(1).strip() if m else ""
    found = {s: c for s, c in colours.items() if re.search(r"(^|[\s>])a($|[:\s.])", s)}
    if not found:
        raise ShapeError("found NO link rules at all — the selector scan is broken, not the page")
    out = []
    # An inherited link colour lives on the PARENT, so that is where drift has to be detected.
    for sel, (parent, want) in LINK_INHERITS.items():
        if sel not in found:
            out.append(f"LINK_INHERITS names {sel!r} but the page no longer emits it")
        elif parent not in colours:
            out.append(f"{sel!r} inherits from {parent!r}, which the page no longer emits")
        elif colours[parent] != want:
            out.append(f"{sel!r} inherits from {parent!r}, modelled {want!r} but emitted "
                       f"{colours[parent]!r} — LINK_PAIRS is now measuring the wrong variable")
    for sel in sorted(set(found) | set(LINK_RULES)):
        want, got = LINK_RULES.get(sel), found.get(sel)
        if want is None:
            out.append(f"UNMODELLED link rule {sel!r} -> {got!r}: add it to LINK_RULES and pair "
                       f"its colour in LINK_PAIRS, or its links go unmeasured")
        elif got is None:
            out.append(f"LINK_RULES names {sel!r} but the page no longer emits it")
        elif want != got:
            out.append(f"{sel!r} colour changed: modelled {want!r}, emitted {got!r}")
    return out


def self_test() -> int:
    cases: list[tuple[str, "Callable[[], object]"]] = []

    def case(name, fn):
        cases.append((name, fn))

    def _unread_of(src: Sequence[str]) -> list[str]:
        """Parse `src` for its DROPPED lines only. Called inside a lambda, never above one."""
        seen: list[str] = []
        parse(src, unread=seen)
        return seen

    lines = SAMPLE.splitlines()
    rows = parse(lines)
    by = {r["num"]: r for r in rows}

    case("reads both tables, six-column and three-column", lambda: len(rows) == 4)
    case("the three-column row is read against ITS header", lambda: by[9]["title"] == "Delta")
    case("a row whose width disagrees with its header RAISES", lambda: _raises(
        lambda: parse(["| # | Item | Status |", "|---|---|---|", "| 5 | x | y | z |"]), ShapeError))
    case("a row before any header RAISES rather than guessing", lambda: _raises(
        lambda: parse(["| 5 | x | y |"]), ShapeError))

    # ── backlog #110 — a line inside a table that is NOT read must be REPORTED ──────────────────
    # The sibling branch (a row whose width disagrees with its header) has raised since day one.
    # This one was a bare `continue`, and the page's completeness invariant could not see it
    # because expectation and subject both came out of `parse`.
    #
    # ⚠ Every case here calls through a FUNCTION rather than a value computed once above. A fixture
    # evaluated at registration time takes the whole suite down with it, and a suite that dies emits
    # no `FAIL <name>` line at all — which reads to a harness as "no case covered this", the exact
    # report-format contract this repo measured on 2026-09-10.
    def _dropped() -> list[str]:
        return _unread_of(DECORATED.splitlines())

    # ── THE RULE: inside a block, anything not read is reported, whatever it looks like ──────────
    case("a ⭐ before the number is reported, not silently dropped",
         lambda: any("⭐2" in ln for ln in _dropped()))
    case("a # before the number is reported",
         lambda: any("#3" in ln for ln in _dropped()))
    case("one leading space is reported",
         lambda: any(ln.strip().startswith("| 4 |") for ln in _dropped()))
    # ⭐ r1 finding M-3 (Claude). A decoration OUTSIDE the leading pipe was a silent miss under the
    # first rule, and worse than a miss: the line did not look like a table line, so it ended the
    # block and switched the guard off for every row below it.
    case("a ⭐ before the PIPE is reported — the rule is not a spelling test",
         lambda: any(ln.startswith("⭐|") for ln in _dropped()))
    case("all four decorations are caught, and the readable row still parses",
         lambda: len(_dropped()) == 4
         and [r["num"] for r in parse(DECORATED.splitlines())] == [1])
    case("a line with a single pipe inside a block is reported",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "| 5 | x | y |", "|⭐6"]) == ["|⭐6"])
    # ⭐ r1 finding M-3 (Claude). `| | | |` is a half-typed row somebody is about to fill in.
    # ⚠ THE POSITION IS THE WHOLE CASE, and the first version of it was unfalsifiable: written with
    # the blank row in the BODY it passes whatever `SEPARATOR_ROW` says, because down there nothing
    # consults the regex at all. Reverting the hyphen requirement killed 0 of 108 cases. It has to
    # sit DIRECTLY under the header — the one position where the regex decides — or it is testing
    # the premise instead of the branch.
    case("an all-blank row DIRECTLY under the header is a row, not a delimiter",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "| | | |",
                             "| 5 | x | y |"]) == ["| | | |"])
    case("a colons-only row directly under the header is a row too",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "| : | : | : |",
                             "| 5 | x | y |"]) == ["| : | : | : |"])
    case("an all-blank row in the BODY is reported as well",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "| 5 | x | y |", "| | | |"]) == ["| | | |"])
    # ⭐ r1 finding M1 (Codex). The delimiter is a POSITION, not a spelling: the same text is a
    # valid GFM delimiter under a header and an ordinary row three lines down, so these two cases
    # MUST disagree about identical input.
    case("a hyphen-only row in the BODY is reported, not mistaken for a delimiter",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "| 5 | x | y |", "| - | - | - |"]) == ["| - | - | - |"])
    case("the same text DIRECTLY under the header IS the delimiter, and is not reported",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "| - | - | - |",
                             "| 5 | x | y |"]) == [])

    # ── THE POPULATION, asserted separately from the rule (portable-practices §21) ───────────────
    case("the delimiter under the header is not reported",
         lambda: not any(set(ln.strip()) <= set("|-: ") for ln in _dropped()))
    case("a table with no `| # |` header of its own reports nothing",
         lambda: _unread_of(["## Items", "| Key | Meaning |", "|---|---|",
                             "| A | Bundle A |"]) == [])
    # ⛔ r1 finding H-1 was REVERSED by r3's Blocking, and this case records the reversal rather
    # than quietly dropping it. r1 asked for a legend table in the Items section to report nothing;
    # r2 delivered that by narrowing the report to a contiguous block, and r3 measured what the
    # narrowing cost — a decorated row below the block vanished exactly where a plain one rendered.
    # In a section where `header` is live, a legend row is NOT harmless: `| 5 | Bundle E |` there is
    # read as item 5, or raises on its width. So it is reported, and the delimiter is not.
    case("a legend table in the SAME section is reported — it is a hazard, not decoration",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "| 5 | x | y |", "", "Markers used above:", "",
                             "| Marker | Meaning |", "|---|---|", "| 🟠 | high |"])
         == ["| Marker | Meaning |", "|---|---|", "| 🟠 | high |"])
    # ⚠ r4 L-3. TWO `| # |` tables, which is what `docs/backlog.md` actually is — this is the
    # input that makes the header branch's `seen_delimiter` reset load-bearing.
    case("a second `| # |` table gets its own delimiter, not the first table's",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "| 5 | x | y |", "",
                             "## Found", "| # | Item | Status |", "|---|---|---|",
                             "| 9 | a | b |"]) == [])
    # ⚠ r4 L-6. Right width, wrong column names — the third outcome, which used to be a traceback.
    case("a table whose columns are named differently REFUSES rather than crashing",
         lambda: _raises(lambda: parse(["## Items", "| # | Key | Note |", "|---|---|---|",
                                        "| 7 | a | b |"]), ShapeError))
    case("a legend table in its OWN section reports nothing",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "| 5 | x | y |", "", "## Markers", "",
                             "| Marker | Meaning |", "|---|---|", "| 🟠 | high |"]) == [])

    # ⭐⭐ THE BLOCKING FROM r3, AND ITS FALSIFIER. The two populations are asserted against EACH
    # OTHER, not each alone — which is the only form that can catch a report gate drifting narrower
    # than the read gate. Same context, same row, one character apart.
    _CONTEXTS = [
        [],                                                    # straight under the delimiter
        ["", "some prose"],                                    # after a blank line and prose
        ["### Notes"],                                         # after a sub-heading
        ["<!-- note -->"],                                     # after an HTML comment
        ["", "| Marker | Meaning |", "|---|---|", "| 🟠 | x |", ""],   # after a second table
        ["## Something else"],                                 # a NEW section: neither, and that
    ]                                                          # is what makes this non-vacuous

    def _read_vs_reported(ctx: list[str]) -> tuple[bool, bool]:
        head = ["## Items", "| # | Item | Status |", "|---|---|---|", "| 5 | x | y |"] + ctx
        try:
            # ⚠ A RAISE COUNTS AS "not read", and it is the honest reading: with no live header the
            # plain row does not reach the page either — it stops the build LOUDLY, which is the
            # pre-existing fail-closed sibling this whole item was filed next to.
            read = any(r["num"] == 111 for r in parse(head + ["| 111 | new | pending |"]))
        except ShapeError:
            read = False
        seen: list[str] = []
        parse(head + ["| ⭐111 | new | pending |"], unread=seen)
        return read, any("⭐111" in ln for ln in seen)

    case("wherever a plain row would be READ, a decorated one is REPORTED",
         lambda: all(_read_vs_reported(c)[0] == _read_vs_reported(c)[1] for c in _CONTEXTS))
    case("…and the pairing is not vacuous — it covers both answers",
         lambda: {_read_vs_reported(c)[0] for c in _CONTEXTS} == {True, False})

    # ⚠ THE RESIDUE, PINNED SO IT IS VISIBLE. Where no `| # |` header is live, `parse` reads
    # nothing, so a decorated row there is neither read nor reported. Its plain counterpart RAISES
    # (`ShapeError`, "row has N cells, header has 0"), so the ordinary mistake is loud; the
    # decorated one is not. Closing this needs a way to say "that first cell was MEANT to be a
    # number", which is an allowlist of decorations — the shape this slice has already paid for
    # twice. Stated, not hidden, and left as follow-up work.
    case("a decorated row where NO item table is open is silent — the one stated gap",
         lambda: _unread_of(["## Notes", "| ⭐111 | new | pending |"]) == []
         and _raises(lambda: parse(["## Notes", "| 111 | new | pending |"]), ShapeError))

    # ⭐ r3, both halves. `row_ish`'s three-character prefix is a judgement, so both sides of it are
    # pinned: a decoration is short, prose that merely mentions a pipe is not.
    case("a three-character prefix before the pipe still reads as a decorated row",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "-- | 5 | x |"]) == ["-- | 5 | x |"])
    case("prose that merely mentions a pipe is not a lost row",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "| 5 | x | y |",
                             "> paragraphs of literal `|` on GitHub. Both are enforced by a check"])
         == [])

    # ⭐ r3 finding M-2. A decorated row between the header and the delimiter used to consume the
    # one-line window, so the genuine delimiter was reported too — a false warning stapled to a
    # real one.
    case("a decorated row before the delimiter does not make the delimiter a finding",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "| ⭐2 | x | y |",
                             "|---|---|---|", "| 5 | x | y |"]) == ["| ⭐2 | x | y |"])
    # ⭐ r3, Codex. GFM's delimiter cell is `:?-+:?`, per CELL. Three spellings of this have been
    # wrong; these pin all three directions at once.
    case("a one-hyphen-per-cell delimiter is a delimiter (GFM, not the 3-hyphen convention)",
         lambda: is_delimiter("|-|-|-|") and is_delimiter("| - | - | - |")
         and is_delimiter("|:--|:-:|--:|"))
    # ⚠ `---|---` IS THE CASE, not `---|---|---`. Both spellings survive `.split("|")[1:-1]`,
    # which drops the outer CELLS instead of the outer PIPES; only a two-cell delimiter with both
    # outer pipes omitted tells them apart. Measured — the three-cell version left the mutant green.
    case("a delimiter may omit its outer pipes",
         lambda: is_delimiter("---|---") and is_delimiter("---|---|---")
         and is_delimiter("| --- | ---"))
    case("a horizontal rule is not a table delimiter",
         lambda: not is_delimiter("---") and not is_delimiter("- - -"))
    case("a cell that is not a delimiter cell makes it not a delimiter",
         lambda: not is_delimiter("| : | - | : |") and not is_delimiter("| | | |")
         and not is_delimiter("| 5 | x | y |"))
    # ⚠ r4 finding M-2. Every negative above fails on its FIRST character, so none of them can see
    # the end anchor: dropping the `$` survived 152/152. A cell that STARTS like a delimiter and
    # then keeps going is the one that needs it — and it is a real half-typed row.
    case("a cell that starts like a delimiter and continues is not one",
         lambda: not is_delimiter("|--- draft, fill me in ---|---|")
         and not is_delimiter("|---x|---|"))
    # ⚠ r4 finding M-1, the boundary itself — 3 passes, 4 does not, and the negative is one
    # character over rather than a whole sentence over.
    case("the row_ish boundary is pinned on BOTH sides, at 3 and at 4",
         lambda: row_ish("abc| 5 | x |") and not row_ish("abcd| 5 | x |"))
    # ⚠ r2 finding L-1. The comment claimed a blank line AND `## ` both end the block; only the
    # first was pinned, and deleting the `## ` reset killed 0 of 110 cases. Same class as r1's L-3.
    case("a new `## ` section closes the block",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "| 5 | x | y |", "## Notes", "| ⭐9 | x | y |"]) == [])
    case("the block ends at a blank line",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "| 5 | x | y |", "", "ordinary prose"]) == [])
    # ⭐ r2 finding M3 (Codex). Healthy Markdown written directly under a table, with no blank line
    # between, is not a lost backlog row.
    case("a sub-heading straight after the table ends it, and is not reported",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "| 5 | x | y |", "### Notes", "ordinary prose"]) == [])
    case("an HTML comment straight after the table ends it, and is not reported",
         lambda: _unread_of(["## Items", "| # | Item | Status |", "|---|---|---|",
                             "| 5 | x | y |", "<!-- note -->"]) == [])
    # ⭐ THE CONTROL. If this fires on well-formed input the ⚠ becomes noise, and a detector people
    # learn to skip is the failure mode backlog #92 is filed about.
    case("well-formed tables report nothing unread",
         lambda: _unread_of(SAMPLE.splitlines()) == [])
    # ⚠ r1 finding L-1 (Claude): the case that stood here passed with the whole feature deleted.
    # This one cannot — `parse` without the parameter raises TypeError — and it pins the property
    # that actually matters: collecting the dropped lines does not change what is read.
    case("passing `unread` changes nothing about what is READ",
         lambda: [r["num"] for r in parse(DECORATED.splitlines())]
         == [r["num"] for r in parse(DECORATED.splitlines(), unread=[])] == [1])

    # ── THE DELIVERY. r2 finding H-2: nine mutations reverting every channel round 1 added left
    # the suite 110/110 green. The rule was well covered and nothing asserted that a human is ever
    # told, which is this whole item's own failure mode wearing a different hat.
    # ⚠ THE REAL ROWS, not SAMPLE. `build` renders GROUPS and DEPENDS, which name real item
    # numbers, so a four-row fixture raises `KeyError(19)` before it can render anything. Memoised
    # because each call renders the whole page.
    _built_cache: dict[tuple, str] = {}

    def _built(unread: list[str]) -> str:
        if tuple(unread) not in _built_cache:
            _built_cache[tuple(unread)] = build(
                [dict(r, hist=None) for r in parse(BACKLOG.read_text().splitlines())],
                "sha", "2026-01-01 00:00", "stamp", unread=list(unread))
        return _built_cache[tuple(unread)]

    def _box(page: str, opener: str) -> str:
        """The one box, or "" — so a case cannot pass on a word that appears elsewhere on a
        2 MB page. `"INCOMPLETE" not in page` was the first spelling of the case below and it
        failed on a backlog ROW that happens to contain the word."""
        i = page.find(opener)
        return page[i:page.find("</div>", i) + 6] if i >= 0 else ""

    _INC, _DRIFT = "&#9888; this view is INCOMPLETE", "&#9888; this view is built from a grouping"

    # ⭐ PRE-EXISTING, and it falsified this change's own promise. `dependency_svg` indexed
    # `by_num[n]` for every number DEPENDS names; an unread row that is a dependency child took the
    # whole build down with a KeyError before any warning could print. Reproduced on master.
    def _without_dep_row() -> list[dict]:
        gone = next(iter(DEPENDS))
        return [dict(r, hist=None) for r in parse(BACKLOG.read_text().splitlines())
                if r["num"] != gone]

    case("the dependency map survives a number DEPENDS names but the file does not carry",
         lambda: isinstance(dependency_svg({r["num"]: r for r in _without_dep_row()}), str)
         and isinstance(dependency_mermaid({r["num"]: r for r in _without_dep_row()}), str))
    case("and so does the whole page — an unread dependency row does not take the build down",
         lambda: "&#9888; this view is INCOMPLETE" in build(
             _without_dep_row(), "sha", "2026-01-01 00:00", "stamp", unread=["| ⭐17 | x | y |"]))

    # ── r3 H-1 / H-3 (Claude) and M3 (Codex): ONE drift list, both channels, both note families ──
    def _rows_missing(num: int) -> list[dict]:
        return [dict(r, hist=None) for r in parse(BACKLOG.read_text().splitlines())
                if r["num"] != num]

    _dep = next(iter(DEPENDS))

    # ⚠ r4 L-5. `contradiction_errors(rows)` is [] on the real file, so folding it into
    # `drift_notes_for` was unverified in either channel — `notes = []` survived. A synthetic row
    # that says ✅ in its marker and stays open is the input that gives the family a population.
    case("the contradiction family reaches the drift channel too",
         lambda: any("contradict" in n.lower() or "✅" in n
                     for n in drift_notes_for([dict(num=1, sev="done", closed=False, title="t",
                                                    body="b", section="Items", was="", touches="",
                                                    size="S", bundle="A", status="pending",
                                                    warned=False, hist=None)], [])))
    case("the GROUPS family reaches the drift channel at all",
         lambda: any("no longer open" in n for n in drift_notes_for(_drifted_rows([]), [])))
    case("a GROUPS note is qualified while something is unread",
         lambda: any("no longer open" in n and "could not be READ this run" in n
                     for n in drift_notes_for(_drifted_rows([]), ["| ⭐2 | x |"])))
    case("a DEPENDS note is qualified too, not just a GROUPS one",
         lambda: any("is not an open item" in n and "could not be READ this run" in n
                     for n in drift_notes_for(_rows_missing(_dep), ["| ⭐%d | x |" % _dep])))
    case("and neither is qualified when nothing is unread",
         lambda: not any("could not be READ this run" in n
                         for n in drift_notes_for(_rows_missing(_dep), [])))
    case("the page renders exactly the notes the builder produced",
         lambda: sorted(re.findall(r"<li>([^<]*)</li>",
                                   _box(_drifted(["| ⭐2 | x |"]), _DRIFT)))
         == sorted(html.escape(n) for n in drift_notes_for(_drifted_rows(["| ⭐2 | x |"]),
                                                           ["| ⭐2 | x |"])))

    case("the page carries an INCOMPLETE box when a row could not be read",
         lambda: _INC in _built(["| ⭐2 | x | y |"]))
    case("and carries none when every row was read",
         lambda: _INC not in _built([]))
    case("the box quotes the line, so the reader can find it",
         lambda: "⭐2" in _box(_built(["| ⭐2 | x | y |"]), _INC))
    # ⚠ r2 finding L-3. Arbitrary file text reaches a rendered page here.
    case("the box escapes the line it quotes",
         lambda: "&lt;script&gt;" in _box(_built(["| <script> | x |"]), _INC)
         and "<script>" not in _box(_built(["| <script> | x |"]), _INC))

    # ⚠ r1 finding H-2 named this case and r2 found it had not been written: the drift box's
    # closing sentence reassured the reader that every row had been read, printed directly under a
    # box saying three had not. ⚠ THE DRIFT BOX ONLY RENDERS WHEN SOMETHING HAS DRIFTED, and the
    # real file has drifted in no way today — asserting on `_built` alone passed vacuously in BOTH
    # directions. So one row GROUPS names is forced closed, which is what produces the box.
    # ⚠ A NUMBER GROUPS NAMES AND `DEPENDS` DOES NOT — r4 finding H-1. The first GROUPS entry is
    # 17, which is also a DEPENDS key, so forcing it closed produced BOTH notes and every
    # GROUPS-side assertion was satisfied by the DEPENDS one. Deleting the whole GROUPS family from
    # the drift channel survived 152/152.
    _gnum = next(n for *_, its in GROUPS for n in its if n not in DEPENDS)

    def _drifted_rows(_unread: list[str]) -> list[dict]:
        return [dict(r, hist=None, closed=True) if r["num"] == _gnum else dict(r, hist=None)
                for r in parse(BACKLOG.read_text().splitlines())]

    def _drifted(unread: list[str]) -> str:
        return build(_drifted_rows(unread), "sha", "2026-01-01 00:00", "stamp", unread=unread)

    case("the drift box exists to be asserted about (the fixture is not vacuous)",
         lambda: _DRIFT in _drifted([]) and _DRIFT in _drifted(["| ⭐2 | x |"]))
    case("the page does not claim every row was read while one was not",
         lambda: "every row on this page was read" in _box(_drifted([]), _DRIFT)
         and "every row on this page was read" not in _box(_drifted(["| ⭐2 | x |"]), _DRIFT))
    # ⚠ r2 finding H-1's other half: with a row unread, "no longer open" is a guess made from an
    # absence the unread row itself caused, and it was measured announcing that two OPEN items had
    # closed.
    case("a `no longer open` note is qualified while anything is unread",
         lambda: "could not be READ this run" in _box(_drifted(["| ⭐2 | x |"]), _DRIFT)
         and "could not be READ this run" not in _box(_drifted([]), _DRIFT))

    def _printed(unread: list[str]) -> list[str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            report_unread(unread)
        return buf.getvalue().splitlines()

    case("exactly one printed line is marked ⚠ — the rest are indented detail",
         lambda: sum(1 for ln in _printed(["| ⭐2 | x |", "| ⭐3 | x |"]) if ln.startswith("⚠")) == 1
         and all(ln.startswith("   UNREAD: ")
                 for ln in _printed(["| ⭐2 | x |", "| ⭐3 | x |"])[1:]))
    case("nothing is printed when nothing was unread",
         lambda: _printed([]) == [])
    # ⭐⭐ THE END-TO-END CASE, and r3 finding H-2 is why the two source-shape proxies that stood
    # here are not enough on their own. They assert that two strings appear twice in `main`; they
    # cannot see whether the list those calls receive still holds anything. One inserted line —
    # `unread.clear()` after `attach_history` — killed the whole feature in production with both
    # proxies satisfied and the suite green. So `main` is RUN, against a doctored copy of the real
    # backlog, and both the terminal output and the written page are read back.
    #
    # ⚠ `attach_history` is stubbed: it shells out to `git show` once per historical version of
    # docs/backlog.md, which is seconds of work irrelevant to this path. ⚠ `--out` and `$HOME` both
    # point into a `TemporaryDirectory`, so nothing reaches `~/explainers/`. The one file written
    # outside it is `main`'s intermediate fragment (`NamedTemporaryFile`, the system temp dir),
    # which is unlinked in its own `finally` — named here because r4 read the previous wording as
    # claiming otherwise.
    _e2e_cache: dict[int, tuple[str, str]] = {}

    def _main_end_to_end() -> tuple[str, str]:
        if 0 in _e2e_cache:                      # ⚠ r4 L-8: called seven times, and each call
            return _e2e_cache[0]                 # re-rendered the page and spawned brief-compose.
        # ⚠ THE ROW MATTERS. Decorating an item nothing else mentions leaves `main`'s drift notes
        # identical whether or not they were told about the unread list, so `drift_notes_for(rows,
        # ())` passed 150/150 — r3 finding H-3 reopening itself. `_dep` is named by DEPENDS, so its
        # absence changes what the other notes say.
        doctored = BACKLOG.read_text().replace(f"\n| {_dep} |", f"\n| ⭐{_dep} |", 1)
        with tempfile.TemporaryDirectory() as tmp:
            src = pathlib.Path(tmp) / "backlog.md"
            src.write_text(doctored)
            out = pathlib.Path(tmp) / "page.html"
            saved_backlog, saved_hist = globals()["BACKLOG"], globals()["attach_history"]
            saved_argv, saved_home = sys.argv, os.environ.get("HOME")
            buf = io.StringIO()
            try:
                globals()["BACKLOG"] = src
                globals()["attach_history"] = lambda rows, text: None
                sys.argv = ["gen-backlog-page.py", "--out", str(out)]
                # ⚠ HOME REDIRECTED (r4 L-7). Without it, WHICH of `main`'s two success arms this
                # exercises is decided by whether the developer happens to have `~/explainers/` —
                # so the case asserted about the composed page on one machine and the fallback
                # `write_text` on another, and its name said neither. Redirected, it is always the
                # no-Ask-tray arm; the tray arm is covered by the source-shape proxy below, which
                # is now a statement about a KNOWN gap rather than an unknown one. It is also the
                # insurance this project has already paid for once: `DEFAULT_OUT` resolves
                # `Path.home()` at import, so only the explicit `--out` keeps the reader's live
                # page out of this.
                os.environ["HOME"] = tmp
                with contextlib.redirect_stdout(buf):
                    main()
            finally:
                globals()["BACKLOG"] = saved_backlog
                globals()["attach_history"] = saved_hist
                sys.argv = saved_argv
                if saved_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = saved_home
            _e2e_cache[0] = buf.getvalue(), (out.read_text() if out.exists() else "")
            return _e2e_cache[0]

    case("main RUN end to end reports the unread row on the terminal",
         lambda: any(ln.startswith("⚠  UNREAD: 1 line(s)") for ln in _main_end_to_end()[0].splitlines()))
    case("…and the page it wrote carries the INCOMPLETE box naming that row",
         lambda: "&#9888; this view is INCOMPLETE" in _main_end_to_end()[1]
         and f"⭐{_dep}" in _main_end_to_end()[1])
    case("…and the page was written at all — an unread row does not stop the build",
         lambda: len(_main_end_to_end()[1]) > 100_000)
    # ⭐ r3 finding H-3, end to end. The terminal is the channel the hook surfaces at the moment
    # someone types the row; it was printing the flat, FALSE "no longer open" while the page — which
    # they may never open — got the qualified, true one.
    case("the terminal carries the SAME qualified notes the page does",
         lambda: "could not be READ this run" in _main_end_to_end()[0]
         and "could not be READ this run" in _main_end_to_end()[1])
    # ⚠ The two proxies are KEPT beside the run above, and they are proxies: they cover the arm the
    # end-to-end case did not happen to take (with or without the Ask tray), which no in-process
    # run can force without adding a test-only branch to `main`.
    case("both of main's success paths report — neither arm is silent",
         lambda: inspect.getsource(main).count("report_run(rows, unread)") == 2)
    case("main hands the unread list to BOTH parse and build — the box is wired",
         lambda: inspect.getsource(main).count("unread=unread") == 2)

    # ⭐ r4 finding H-2. `report_run`'s THIRD channel — the "no description in GROUPS" block — is
    # the only one that fires on the real `docs/backlog.md` today (ten items, #110 among them), and
    # three mutations deleting it left 152/152 green. It is asserted here through the same captured
    # stdout the other two channels use.
    def _run_printed(rows: list[dict], unread: list[str]) -> list[str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            report_run(rows, unread)
        return buf.getvalue().splitlines()

    # ⚠ Annotated: `dict(r, hist=None)`'s only typed keyword is `None`, so a checker infers
    # `dict[str, None]` and then calls every `r["num"]` a `None`. The annotation says what the row
    # actually is rather than what one keyword happens to look like.
    _REAL_ROWS: list[dict] = [dict(r, hist=None) for r in parse(BACKLOG.read_text().splitlines())]

    # ⛔ FOUR CASES RETIRED WITH THEIR SUBJECT, 2026-09-11 — the ONE sanctioned kind of coverage
    # fall, recorded here with the count and the reason rather than left as a silent drop.
    # `undescribed()` and `report_run`'s third channel are GONE: under backlog #90's clause 0 an
    # ungrouped open item is normal, so "N open item(s) have no description" is no longer a
    # finding to report. The cases were `the undescribed fixture is not vacuous`, `the
    # undescribed block is printed`, `...and it is SILENT when every open item has a sentence`
    # and `its count is the number of items with no sentence`.
    #
    # ⚠ THREE OF THOSE FOUR WERE WRITTEN THIS MORNING, to fix cases that measured the POPULATION
    # instead of the RULE. They were correct and they are still being deleted, because the rule
    # itself stopped existing — that is retirement-with-subject, not a ratchet fall. The
    # distinction matters: a case deleted because its subject is gone costs nothing; a case
    # deleted because it became inconvenient costs exactly the defect it used to catch.

    # ⚠ r4 finding M-3. The ⚠ PREFIX is the delivery mechanism — `explainer-serve` collects only
    # lines that start with it — and replacing it with three spaces survived 152/152 under both
    # HOMEs. Every drift note must carry it.
    case("every drift note is marked ⚠, which is what the Refresh button collects",
         lambda: all(any(ln.startswith("⚠  ") and note[:40] in ln
                         for ln in _run_printed(_drifted_rows([]), []))
                     for note in drift_notes_for(_drifted_rows([]), [])))

    # ⭐ r3 finding L-4. `.claude/hooks/regen-backlog-page.sh` is shell: no `--self-test`, not a
    # `check-*` guard, in no mutation manifest. It is the channel that reaches the human at the
    # moment they type the decorated row, and its awk was verified by hand and by nothing else.
    # This RUNS the program out of the hook file, so an edit to that line reddens a case.
    def _hook_awk(sample: str) -> str:
        src = (REPO / ".claude/hooks/regen-backlog-page.sh").read_text()
        prog = next(ln for ln in src.splitlines() if ln.lstrip().startswith("echo \"$OUT\" | awk"))
        prog = prog.split("awk ", 1)[1].strip().strip("'")
        return subprocess.run(["awk", prog], input=sample, capture_output=True,
                              text=True).stdout

    # ⚠ ORDINARY PROSE SITS BETWEEN A WARNING AND A LATER INDENTED LINE — r4 finding M-4. Without
    # it the program is byte-identical to a two-pattern grep, so dropping `{p=0}` or the `p &&`
    # guard (which together are the whole state machine) survived.
    _SAMPLE_OUT = ("wrote /x  (110 rows)\n"
                   "⚠  UNREAD: summary\n   UNREAD: detail\n   UNREAD: remedy\n"
                   "an ordinary line that resets the run\n"
                   "   an indented line that belongs to NOTHING\n"
                   "⚠  WITHOUT the Ask tray:\n   missing token: --paper\n"
                   "     http://127.0.0.1:7391/backlog-table\n")

    case("the hook keeps every ⚠ line",
         lambda: _hook_awk(_SAMPLE_OUT).count("⚠") == 2)
    case("the hook keeps the indented detail of BOTH warnings, not just UNREAD's",
         lambda: "UNREAD: remedy" in _hook_awk(_SAMPLE_OUT)
         and "missing token: --paper" in _hook_awk(_SAMPLE_OUT))
    case("the hook drops the ordinary output lines",
         lambda: "110 rows" not in _hook_awk(_SAMPLE_OUT)
         and "7391" not in _hook_awk(_SAMPLE_OUT))
    case("an indented line after ordinary prose belongs to nothing and is dropped",
         lambda: "belongs to NOTHING" not in _hook_awk(_SAMPLE_OUT))

    # ── THE NOTE ────────────────────────────────────────────────────────────────────────────────
    # ⚠ It NAMES the line. A bare count says a row is missing and not which one, and this file has
    # already measured what an unactionable warning costs (r2 finding R2-9).
    case("the note quotes the offending line rather than counting it",
         lambda: any("⭐2" in ln for ln in unread_note(["| ⭐2 | x |"])))
    case("no note at all when nothing was unread",
         lambda: unread_note([]) == [])
    # ⭐ r3 finding M-6. The COUNT is the number a reader acts on, and `len(unread) + 1` in either
    # the note or the box heading passed 127/127. A box saying "2 line(s)" over one quoted line
    # sends someone hunting for a row that does not exist.
    case("the note's total is the number of unread lines",
         lambda: unread_note(["| ⭐2 | x |", "| ⭐3 | x |"])[0].startswith("2 line(s)")
         and unread_note(["| ⭐2 | x |"])[0].startswith("1 line(s)"))
    case("the box's heading carries the same total",
         lambda: "INCOMPLETE — 2 line(s)" in _box(_built(["| ⭐2 | x |", "| ⭐3 | x |"]), _INC))
    # ⭐ r3 finding L-1. `[1:]` — dropping the duplicate summary from the box, which has a heading
    # already — was reverted to `[0:]` at 127/127 green, and the box then said it twice.
    case("the box lists the detail lines only, not its own heading again",
         lambda: len(re.findall(r"<li>", _box(_built(["| ⭐2 | x |"]), _INC)))
         == len(unread_note(["| ⭐2 | x |"])) - 1)
    # ⭐ r3 finding L-2. Deleting the box's whole remedy paragraph passed 127/127 — the case that
    # looked like it covered this tests `unread_note`, and the box's remedy is a separate literal.
    case("the box says what to do, in the file the reader must edit",
         lambda: "bare integer" in _box(_built(["| ⭐2 | x |"]), _INC)
         and "docs/backlog.md" in _box(_built(["| ⭐2 | x |"]), _INC))
    # ⭐ r1 finding M-2 (Claude). `explainer-serve` joins every ⚠ line and cuts at 400 characters,
    # so an uncapped note spends the whole budget and pushes the other warnings out of the button.
    # ⚠ FOUR, not nine (r4 L-4). With nine the tail reads "… and 6 more", which `extra > 1` also
    # produces; only a fourth line distinguishes "say something about the one you did not quote"
    # from "say nothing about it".
    case("a fourth unread line is accounted for, not dropped in silence",
         lambda: unread_note([f"| ⭐{n} | x |" for n in range(4)])[-2].endswith("1 more"))
    case("the quote is cut at 110 characters, not merely cut somewhere",
         lambda: len(unread_note(["| " + "x" * 200 + " |"])[1]) == 111
         and unread_note(["| " + "x" * 105 + " |"])[1].endswith("|"))
    case("the note quotes at most three lines and says how many more there are",
         lambda: len(unread_note([f"| ⭐{n} | x |" for n in range(9)])) == 6
         and any(ln.endswith("6 more") for ln in unread_note([f"| ⭐{n} | x |" for n in range(9)])))
    # ⚠ r2 finding L-2. A quote cut mid-word with no mark cannot be searched for verbatim, and
    # dropping `.strip()` or the cut killed 0 of 110 cases.
    case("a quote longer than the cut is marked as cut",
         lambda: unread_note(["| " + "x" * 200 + " |"])[1].endswith("…")
         and not unread_note(["| short |"])[1].endswith("…"))
    case("a quoted line is stripped, so an indented row still reads as a row",
         lambda: unread_note(["    | ⭐2 | x |"])[1].startswith("| ⭐2"))
    case("the remedy is said, whatever the count",
         lambda: all(any("bare integer" in ln for ln in unread_note(u))
                     for u in ([["| ⭐2 | x |"]] + [[f"| ⭐{n} | x |" for n in range(9)]])))
    # ⭐ THE RATCHET ON M-2. Line 0 is the only line marked ⚠, so it is the only one that spends
    # the Refresh button's 400-character budget. If it grows past a quarter of that budget the
    # other warnings start losing their place, which is the finding itself.
    case("the summary line stays well inside the Refresh button's budget",
         lambda: len(unread_note([f"| ⭐{n} | x |" for n in range(9)])[0]) <= 100)

    case("closed iff the Status cell has a check mark",
         lambda: by[2]["closed"] and by[9]["closed"] and not by[1]["closed"] and not by[3]["closed"])
    case("severity comes from the leading marker", lambda: by[1]["sev"] == "high")
    case("a closed row keeps its ORIGINAL severity out of the title",
         lambda: by[2]["title"] == "Beta" and by[2]["was"] == "🟡")
    case("the body keeps the whole cell, so no prefix is dropped",
         lambda: "done now" in by[2]["body"])
    case("no title carries a literal bold marker",
         lambda: all("**" not in r["title"] for r in rows))
    case("the warning flag is READ, not inferred",
         lambda: by[3]["warned"] and not by[1]["warned"])

    # ⚠ The three inline-markup cases that stood here are DELETED (backlog #71). Inline rendering
    # is `page_markup`'s behaviour and is asserted by its own cases; re-asserting it here would be
    # a second copy of one rule. ONE case is kept, and it is not about markup — it pins the
    # `.strip()` this file's callers depend on, which is genuinely local to `md`.
    case("md strips the cell before rendering",
         lambda: md("   **a**   ") == "<strong>a</strong>")
    case("plain strips emphasis so a cut cannot land mid-marker",
         lambda: plain("**Loud** and `quiet`") == "Loud and quiet")

    # ⟳ 2026-09-09. `coverage_errors` is GONE, superseded by `sanitise_groups`, which reports the
    # same two drifts and then renders anyway. These cases moved with the behaviour rather than
    # being deleted, so the record shows the contract was changed on purpose, not lost.
    case("a matching grouping needs no correction",
         lambda: sanitise_groups([("g", "f", "x", [1, 2])], {1, 2}) == (
             [("g", "f", "x", [1, 2])], []))
    # ⟳ 2026-09-11. This used to read "an ungrouped open item is not a correction — `undescribed`
    # renders it". Under backlog #90's clause 0 an ungrouped open item is NORMAL, not something
    # to render specially, so the second half went with `undescribed`. The first half is the part
    # that still says something: leaving an open item out of every group is not drift.
    case("an ungrouped open item is not a correction",
         lambda: sanitise_groups([("g", "f", "x", [1])], {1, 2})[1] == [])
    case("a group naming a CLOSED item drops it and SAYS SO, instead of refusing",
         lambda: sanitise_groups([("g", "f", "x", [1, 7])], {1}) == (
             [("g", "f", "x", [1])], ["GROUPS still names 1 item(s) that are no longer open: "
                                        "[7] — dropped from their group for this build"]))
    case("a duplicate across groups is kept in the FIRST and reported",
         lambda: sanitise_groups([("a", "f", "x", [1]), ("b", "g", "y", [1])], {1})[0]
         == [("a", "f", "x", [1]), ("b", "g", "y", [])]
         and "more than one group" in " ".join(
             sanitise_groups([("a", "f", "x", [1]), ("b", "g", "y", [1])], {1})[1]))
    # ⚠ THE FALSIFIER FIELD IS CARRIED, NOT DROPPED. `sanitise_groups` rebuilds each tuple, so a
    # fourth field is exactly the kind of thing a rebuild silently loses — and the guard that
    # reads it would then report every group as having no falsifier, which looks like a finding
    # about the DATA rather than about this function.
    case("sanitise_groups carries the falsifier through untouched",
         lambda: sanitise_groups([("g", "f", "the falsifier", [1])], {1})[0][0][2]
         == "the falsifier")
    # ⛔ THE FALSIFIER FOR THE WHOLE CHANGE: the 2026-09-04 defect must no longer stop a build.
    case("the drift that froze the page for five days now only WARNS",
         lambda: sanitise_groups([("g", "f", "x", [78, 83, 87, 1])],
                                 {1})[0] == [("g", "f", "x", [1])])

    # ─ tags ─────────────────────────────────────────────────────────────────
    case("a slash tag assigns the family AND the leaf",
         lambda: bundle_tags("(cloud/money)") == ["cloud", "cloud / money"])
    case("a plain tag assigns itself only",
         lambda: bundle_tags("(comprehensibility)") == ["comprehensibility"])
    case("an em dash and an empty cell are BOTH `untagged`, never nameless",
         lambda: bundle_tags("—") == ["untagged"] and bundle_tags("") == ["untagged"])
    case("tag options are derived from the rows, commonest first",
         lambda: bundle_options([{"bundle": "(cloud/money)"}, {"bundle": "(cloud/test)"},
                                 {"bundle": "(tooling)"}])[0] == ("cloud", 2, 2))
    case("an item counts once per tag it carries, so the family total includes the leaves",
         lambda: {k: (o, tt) for k, o, tt in bundle_options([{"bundle": "(cloud/money)"}])}
         == {"cloud": (1, 1), "cloud / money": (1, 1)})
    # ⚠ the label must not disagree with the default view: a CLOSED row counts in `total`, never
    # in `open`. This is the 2026-09-09 "(26)" over 10 visible rows, pinned.
    case("a closed row counts toward total but not toward open",
         lambda: bundle_options([{"bundle": "(x)", "closed": True},
                                 {"bundle": "(x)", "closed": False}]) == [("x", 1, 2)])

    # ⟳ 2026-09-09. These pin a refusal that USED TO BE A `KeyError` — see `contradiction_errors`.
    _row = lambda n, sev, closed: dict(num=n, sev=sev, closed=closed)
    case("a ✅ marker with no ✅ in Status REFUSES, naming the rows",
         lambda: "81" in " ".join(contradiction_errors([_row(81, "done", False)])))
    case("...and a consistent set does not",
         lambda: contradiction_errors([_row(1, "high", False), _row(2, "done", True)]) == [])
    case("a CLOSED row without the marker is NOT a contradiction (the near-miss that would over-fire)",
         lambda: contradiction_errors([_row(3, "med", True)]) == [])

    case("waiting_on reads the gate out of the Size cell",
         lambda: waiting_on("M + design")[0] == "design"
         and waiting_on("S (decision) + S (impl)")[0] == "decision"
         and waiting_on("M (study)")[0] == "study"
         and waiting_on("XS")[0] == "work")

    # ── the dependency graph ────────────────────────────────────────────────────────────────────
    R = {"root-a": {"label": "A", "detail": "d"}}
    case("a clean graph produces no errors",
         lambda: depends_errors({1: ("survives", "root-a", "")}, R, {1}) == [])
    case("an unknown relation is refused",
         lambda: "unknown relation" in " ".join(
             depends_errors({1: ("vanishes", "root-a", "")}, R, {1})))
    case("a dependency on a CLOSED item is refused",
         lambda: "not an open item" in " ".join(
             depends_errors({1: ("blocked-by", "7", "")}, R, {1})))
    case("a dependency ON a closed item is refused even with a valid relation",
         lambda: depends_errors({1: ("blocked-by", "2", "")}, R, {1, 2}) == [])
    case("an item that is not open cannot carry a dependency",
         lambda: "not an open item" in " ".join(
             depends_errors({9: ("survives", "root-a", "")}, R, {1})))
    # ⭐ The trap that made named roots necessary. #52 says "blocked on unparking blob addressing
    # (task #47)" — TASK 47, while BACKLOG 47 is the knowledge graph. A bare number would have
    # silently recorded an edge to the wrong item; an unknown root name cannot.
    case("an unknown root NAME is refused rather than guessed",
         lambda: "not in ROOTS" in " ".join(
             depends_errors({1: ("survives", "task-47", "")}, R, {1})))
    case("self-dependency is refused",
         lambda: "depends on itself" in " ".join(
             depends_errors({1: ("blocked-by", "1", "")}, R, {1})))
    case("a two-item cycle is caught",
         lambda: "cycle" in " ".join(depends_errors(
             {1: ("blocked-by", "2", ""), 2: ("blocked-by", "1", "")}, R, {1, 2})))
    case("dep_rank puts un-blocked work before work the root deletes",
         lambda: dep_rank(19) < dep_rank(17) < dep_rank(52) < dep_rank(20))
    case("an item with no dependency sorts first of all",
         lambda: dep_rank(999) == 0 and dep_rank(999) < dep_rank(19))
    # ⭐ measures the SHIPPED graph, not a fixture — same posture as the GROUPS coverage case
    case("DEPENDS is coherent against the REAL backlog", lambda: depends_errors(
        DEPENDS, ROOTS,
        {r["num"] for r in parse(BACKLOG.read_text().splitlines()) if not r["closed"]}) == [])
    case("every relation used by DEPENDS is defined",
         lambda: all(rel in RELATIONS for rel, _, _ in DEPENDS.values()))

    # ── change history ──────────────────────────────────────────────────────────────────────────
    V = [("a", 100, "| 1 | alpha |\n| 2 | beta |"),
         ("b", 200, "| 1 | alpha |\n| 2 | beta CHANGED |"),
         ("c", 300, "| 1 | alpha |\n| 2 | beta CHANGED |\n| 3 | gamma |")]
    h = changes_from_versions(V)

    case("rows_of keys a version by item number",
         lambda: rows_of("| 7 | x |\nnot a row\n| 8 | y |") == {7: " x |", 8: " y |"})
    case("an untouched item's last-change is its first appearance",
         lambda: h[1]["first"] == 100 and h[1]["last"] == 100)
    case("an untouched item has no previous text to diff",
         lambda: h[1]["prev"] is None)
    case("a changed item records WHEN and in which commit",
         lambda: h[2]["last"] == 200 and h[2]["sha"] == "b")
    case("a changed item keeps the text it changed FROM",
         lambda: h[2]["prev"] == " beta |")
    case("an item added later is first-seen at its own version, not the file's",
         lambda: h[3]["first"] == 300 and h[3]["last"] == 300)
    case("a later version that changes nothing moves no timestamps",
         lambda: changes_from_versions(V + [("d", 400, V[-1][2])])[2]["last"] == 200)
    case("history of an empty file is empty, not an error",
         lambda: changes_from_versions([]) == {})
    # An item can only be reported NEW or UPDATED if `first` and `last` differ where they should;
    # if the walk collapsed them the page would silently report nothing has ever changed.
    case("first and last are NOT the same field",
         lambda: h[2]["first"] == 100 and h[2]["last"] == 200)

    # ── the page says each thing ONCE ───────────────────────────────────────────────────────────
    # ⟲ Added 2026-08-22 after a reader reported "the stable-addressing slice appears twice in this
    # page". It did: the global map and the per-group panel each carried the root's full statement.
    # Duplication is invisible to the author — you write the second copy on purpose — so it needs a
    # count, not a convention.
    _page = build([dict(r, hist=None) for r in parse(BACKLOG.read_text().splitlines())],
                  "sha", "2026-01-01 00:00", "stamp")
    for _rk, _root in ROOTS.items():
        case(f"the full statement of root {_rk!r} appears exactly once",
             lambda d=_root["detail"]: _page.count(d) == 1)
    case("the dependency map is drawn exactly once", lambda: _page.count("<figure class=\"depmap\"") == 1)

    # ── AN ITEM IN NO GROUP STILL REACHES THE READER — re-aimed 2026-09-11 ─────────────────────
    # ⛔ THE DEFECT THIS LINE OF CASES REPLACES, and the user hit it twice. First the generator
    # REFUSED while four items sat unwritten, so the page stayed a day behind and looked current.
    # Then the replacement rendered them under "Filed, but nobody has described them yet", which
    # made a normal state look like debt and accumulated twelve rows before anyone noticed.
    # Under backlog #90's clause 0 neither happens: grouping is opt-in and the leftovers are an
    # INDEX, not a bucket of shame.
    #
    # ⚠ THE WIRING, not the predicate. This repo keeps finding a correct predicate that nothing
    # calls, so this drives the REAL `build` over the REAL backlog with one item pulled out of a
    # SURVIVING group — #17, which is group 1's first member — and asks whether it still reaches
    # the page, with its summary intact.
    _short = [(g[0], g[1], g[2], [n for n in g[3] if n != 17]) for g in GROUPS]
    _rows17 = [dict(r, hist=None) for r in parse(BACKLOG.read_text().splitlines())]
    _saved, globals()["GROUPS"] = GROUPS, _short
    try:
        _ungrouped_page = build(_rows17, "sha", "2026-01-01 00:00", "stamp")
    finally:
        globals()["GROUPS"] = _saved
    # ⚠ THE HEADING MARKUP, not the bare phrase — and the suite caught this the moment the page
    # gained a paragraph explaining the index BY NAME. A phrase in prose and a rendered section
    # are different claims; greping the phrase made "the section exists" true whenever the page
    # merely mentioned it, and the negative arm below went red rather than silently passing.
    case("an item in no group lands in the index instead of vanishing",
         lambda: "<h3>The rest, one line each</h3>" in _ungrouped_page)
    case("...and it keeps its summary there, rather than rendering as a bare row",
         lambda: SUMMARIES[17][:40] in _ungrouped_page)
    # ⚠ THE NEGATIVE ARM. Without it the case above passes on a page that shows the index
    # ALWAYS — including when every open item is grouped, which is the state the index exists to
    # stay out of. The real GROUPS covers less than every open item, so this drives a fixture
    # where one group claims them all.
    _allrows = [dict(r, hist=None) for r in parse(BACKLOG.read_text().splitlines())]
    _every = [("all of it", "one group claims every open item", "x",
               [r["num"] for r in _allrows if not r["closed"]])]
    _saved2, globals()["GROUPS"] = GROUPS, _every
    try:
        _full_page = build(_allrows, "sha", "2026-01-01 00:00", "stamp")
    finally:
        globals()["GROUPS"] = _saved2
    case("...and the index is ABSENT when every open item is grouped",
         lambda: "<h3>The rest, one line each</h3>" not in _full_page)
    case("the page is built either way, never refused",
         lambda: len(_ungrouped_page) > 1000 and len(_full_page) > 1000)

    # ── links are READABLE, in every palette this page can be rendered under ────────────────────
    case("every link colour clears WCAG AA on every surface it lands on, all four palettes",
         lambda: link_contrast_errors(_page) == [])
    # ⟲ Round 2. The case above measures a HAND-WRITTEN model of which colour lands on which
    # surface; this one asserts the page still matches that model. Without it the model silently
    # stops describing the page — which is exactly how `.num a`'s 70 links went unmeasured.
    case("the page's link rules still match the model that LINK_PAIRS is built from",
         lambda: link_rule_drift(_page) == [])
    # ⟲ The threshold, pinned EXPLICITLY. `LINK_MIN = 4.5 -> 0.0` is currently caught, but only
    # incidentally — by a positive-assertion case that happens to need a non-empty result. Luck is
    # not a guard: state it. (`CONTRAST_MIN` in gen-dashboard.py had the same hole and was NOT
    # caught at all; measured, it survived at 111/111.)
    case("the contrast floor is WCAG AA, not a number someone lowered", lambda: LINK_MIN == 4.5)
    case("...and every modelled link colour is actually paired with a surface",
         lambda: {fg for fg, _ in LINK_PAIRS} == {"--structural", "--ink-3", "--ink"})
    case("a NEW link rule the model has not heard of is reported, not ignored",
         lambda: any("UNMODELLED" in e for e in link_rule_drift(
             _page.replace("</style>", ".newthing a{color:var(--problem)}</style>", 1))))
    case("a link rule that CHANGES colour is reported",
         lambda: any("colour changed" in e for e in link_rule_drift(
             _page.replace(".rootref a{color:var(--structural)}",
                           ".rootref a{color:var(--line)}", 1))))
    case("a scan that matches no link rules RAISES rather than reporting no drift",
         lambda: _raises(lambda: link_rule_drift("<style>body{color:red}</style>"), ShapeError))
    # ⟲ The round-2 survivor, exactly as the reviewer wrote it: repoint the PARENT of an
    # inherited link colour. `.num a` is untouched, so the first version of this guard saw
    # nothing and the contrast check kept measuring a variable the links no longer use.
    case("repointing .num's colour is CAUGHT — the parent is where an inherited colour drifts",
         lambda: any("inherits from" in e for e in link_rule_drift(
             _page.replace(".num{font-family:var(--mono);font-size:.9rem;color:var(--ink-3);",
                           ".num{font-family:var(--mono);font-size:.9rem;color:var(--line);", 1))))
    case("...and deleting the parent rule entirely is also caught",
         lambda: any("no longer emits" in e for e in link_rule_drift(
             _page.replace(".num{font-family:var(--mono);font-size:.9rem;color:var(--ink-3);",
                           ".numGONE{font-family:var(--mono);font-size:.9rem;color:var(--ink-3);", 1))))
    # The round-2 survivor itself, pinned: .num's colour is what .num a inherits, and it is
    # measured against --card because .item — the only place .num renders — is --card.
    case("breaking .num's colour is now CAUGHT (it was the round-2 survivor at 1.37:1)",
         lambda: link_contrast_errors(
             _page.replace("--ink-3:#6b7686", "--ink-3:#dfdcd5")
                  .replace("--ink-3:#7a8494", "--ink-3:#2a3039")) != [])
    # The instrument's own falsifiers. It returns a LIST, so a stylesheet it could not parse
    # would otherwise report "no failures" and be indistinguishable from a readable page.
    case("a page with no palette RAISES rather than reporting no failures",
         lambda: _raises(lambda: link_contrast_errors("<style>a{color:red}</style>"), ShapeError))
    _PAL = (':root{--structural:#3d5a86;--ground:#fff;--card:#fff;--panel:#fff;'
            '--pending-bg:#fff;--ink:#000}\n:root[data-theme="dark"]{}')
    case("a page with palettes but NO unscoped a{} rule RAISES — the defect that shipped",
         lambda: _raises(lambda: link_contrast_errors(_PAL), ShapeError))
    # The NEAR-MISS, which is the whole reason the check is anchored: a page carrying only
    # the SCOPED rules satisfies a bare `"a{color:var(--structural)}" in page` test. That is
    # the exact stylesheet this fix replaced, and an unanchored guard calls it clean.
    case("...and so does one with ONLY the scoped rules, which a substring test would pass",
         lambda: _raises(lambda: link_contrast_errors(
             _PAL + "\n.qabody a{color:var(--structural)}\ntd.mono a{color:var(--structural)}"),
             ShapeError))
    # The measurement itself, pinned against hand-computed values — a broken luminance
    # formula would otherwise make every ratio above pass.
    def _ratio(fg: str, bg: str) -> float:
        a, b = _luminance(fg), _luminance(bg)
        return (max(a, b) + 0.05) / (min(a, b) + 0.05)

    case("black on white is 21:1", lambda: round(_ratio("#000000", "#ffffff"), 2) == 21.0)
    case("a colour against itself is 1:1", lambda: round(_ratio("#3d5a86", "#3d5a86"), 2) == 1.0)
    case("shorthand hex expands (--card is #fff, not #ffffff)",
         lambda: round(_ratio("#fff", "#ffffff"), 2) == 1.0)
    case("the defect this fixed measures what the comment claims: 1.98 on --ground",
         lambda: round(_ratio("#0000EE", "#101318"), 2) == 1.98)
    case("...and 1.84 on --card", lambda: round(_ratio("#0000EE", "#171b22"), 2) == 1.84)
    case("every group's root reference links to the map, which exists",
         lambda: 'id="order"' in _page and _page.count('href="#order"') >= 1)

    # ── the mermaid export ──────────────────────────────────────────────────────────────────────
    _rows = {r["num"]: r for r in parse(BACKLOG.read_text().splitlines())}
    _mmd = dependency_mermaid(_rows)
    case("mermaid export declares a flowchart", lambda: _mmd.startswith("flowchart LR"))
    case("mermaid has one edge per dependency",
         lambda: _mmd.count("-->") == len(DEPENDS))
    # ⚠ a backtick opens a markdown-string in mermaid; #19's title contains one
    case("no markdown survives into a mermaid label",
         lambda: all(c not in _mmd.split("classDef")[0] for c in "`*"))
    case("no unescaped quote can close a mermaid label early",
         lambda: all(ln.count('"') % 2 == 0 for ln in _mmd.splitlines()))
    case("every mermaid node id is a bare identifier",
         lambda: all(re.match(r"^\s+\w+", ln) for ln in _mmd.splitlines()[1:] if ln.strip()))
    case("the svg and the mermaid describe the SAME edge count",
         lambda: dependency_svg(_rows).count('class="e e-') == _mmd.count("-->"))

    case("word_diff marks a deletion and an insertion",
         lambda: "<del>old</del>" in word_diff("the old text", "the new text")
         and "<ins>new</ins>" in word_diff("the old text", "the new text"))
    case("word_diff leaves untouched words unmarked",
         lambda: word_diff("same words here", "same words here") == "same words here")
    case("word_diff escapes html in BOTH sides",
         lambda: "<script>" not in word_diff("<script>a</script>", "<script>b</script>"))
    case("word_diff strips markdown rather than splicing tags through it",
         lambda: "**" not in word_diff("**bold** a", "**bold** b"))

    # ⭐ The one case that measures the SHIPPED grouping rather than a fixture. If an item is filed
    # or closed and GROUPS is not updated, this fails here — before anyone opens the page.
    real = parse(BACKLOG.read_text().splitlines())
    # ⭐ THE INVARIANT THAT MUST HOLD WHATEVER THE GROUPING HAS DRIFTED TO: every open item in the
    # REAL backlog reaches the page exactly once — inside a group, or in the index. Asserting that
    # GROUPS is pristine would re-create the coupling that froze the page for five days, because
    # closing a row would then fail the suite.
    #
    # ⚠ READ OFF THE RENDERED PAGE, NOT RE-DERIVED. The obvious form — `placed + (open - placed)
    # == open` — is a TAUTOLOGY: it is true of any `placed` whatsoever and would pass with the
    # index section deleted outright. This repo has shipped that shape before under the name
    # "a case that cannot fail". So the second half is parsed back out of the HTML the index
    # actually produced, which fails the moment the section stops rendering what it claims.
    _open_real = {r["num"] for r in real if not r["closed"]}
    _san, _ = sanitise_groups(GROUPS, _open_real)
    _placed = [n for *_, its in _san for n in its]
    _real_rows = [dict(r, hist=None) for r in real]
    _real_page = build(_real_rows, "sha", "2026-01-01 00:00", "stamp")
    # ⛔ BOUNDED AT THE NEXT HEADING, and the unbounded version is why this comment exists. The
    # first draft was `split(...)[-1]`, which keeps everything AFTER the heading — including the
    # full "Every row, as filed" table below it, where every open item appears. `_indexed` then
    # collapsed to "all unplaced items" and the invariant became the tautology the paragraph
    # above warns about. Written, then committed three lines later; caught by MEASURING the
    # section and getting 113 items in a 27-item index.
    _idx = (_real_page.split("<h3>The rest, one line each</h3>", 1)[-1].split("<h2", 1)[0]
            if "<h3>The rest, one line each</h3>" in _real_page else "")
    _indexed = {n for n in _open_real - set(_placed) if f'#i{n}">#{n}</a>' in _idx}
    case("every open item reaches the page exactly once — in a group, or in the index",
         lambda: len(_placed) == len(set(_placed))
         and set(_placed).isdisjoint(_indexed)
         and set(_placed) | _indexed == _open_real)
    case("the real file parses at all (fail-closed on a restructure)", lambda: len(real) > 20)
    # ⭐ THE RATCHET the floor above only pretends to be. `> 20` tolerates losing 88 of 110 rows;
    # this fails on the FIRST row the parser cannot read, and names it. Anchored to the file's own
    # lines rather than to `parse`'s output, which is the whole of backlog #110.
    case("the REAL backlog has no row the parser silently skips",
         lambda: _unread_of(BACKLOG.read_text().splitlines()) == [])
    # ⭐ The live counterpart: the REAL backlog must not state closed-ness two ways at once.
    # This is what a bare KeyError looked like on 2026-09-09 (rows 81, 82, 98, 99).
    case("the REAL backlog does not contradict itself about what is closed",
         lambda: contradiction_errors(real) == [])

    failed = 0
    # ⛔ THE FAILURE LINE IS A CONTRACT, and this suite was not keeping it. `check-plan-code`'s
    # harness attributes a kill by `startswith("[FAIL] ")` then `[7:]` then
    # `rsplit(": got ", 1)[0]`. This printed `  FAIL  <name>`, so when the file joined the mutation
    # manifest all five of its entries reported *"matched 0 red case(s) — caught by something else:
    # []"* while every one of them WAS being killed by the case it named. The empty list is the
    # tell: nothing could see the kill, which is indistinguishable from no kill at all.
    #
    # ⚠ The name stays ALONE on the `[FAIL]` line. Appending `[raised …]` to it — which this did —
    # rewrites the very string the harness extracts, so an `expect` naming the case would match
    # nothing. The exception goes on its own line, where it is for a human and for nobody else.
    for name, fn in cases:
        why = ""
        try:
            ok = bool(fn())
        except Exception as exc:                                   # noqa: BLE001 - report, not hide
            ok, why = False, repr(exc)
        if ok:
            print(f"  ok     {name}")
        else:
            print(f"  [FAIL] {name}")
            if why:
                print(f"    raised: {why}")
        failed += not ok
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


def _raises(fn, exc: type[BaseException]) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:                                              # noqa: BLE001
        return False
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT,
                    help=f"where to write (default: {DEFAULT_OUT})")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    def git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(REPO), *a],
                              capture_output=True, text=True).stdout.strip()

    # A refusal here is a NORMAL outcome — filing an item causes it — so it reports as a message a
    # person can act on, not a traceback. The hook that surfaces this prints the last few lines.
    # ⚠ Declared OUTSIDE the try, and reported on BOTH exit paths below. There are two ways this
    # run can succeed — with the Ask tray and without it — and a warning printed on only one of
    # them is a warning that disappears exactly when something else has already gone wrong.
    unread: list[str] = []

    try:
        text = BACKLOG.read_text()
        rows = parse(text.splitlines(), unread=unread)
        attach_history(rows, text)
        fragment = build(rows, git("rev-parse", "--short", "HEAD"),
                         git("log", "-1", "--format=%cI", "--",
                             "docs/backlog.md")[:16].replace("T", " "),
                         subprocess.run(["date", "+%Y-%m-%d %H:%M %Z"],
                                        capture_output=True, text=True).stdout.strip(),
                         page_chrome.provenance(
                             _dt.datetime.now().strftime("%Y-%m-%d %H:%M"), REPO),
                         unread=unread)
        page_chrome.assert_wired(fragment, "gen-backlog-page.py")
    except ShapeError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        print("Nothing was written; the existing page is left as it was.", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    open_n = sum(1 for r in rows if not r["closed"])

    # The Ask tray is LIFTED from a page where it already works, never retyped — `brief-compose.py`
    # owns that, and its docstring records the four rounds of shipped defects that bought the rule.
    # Writing this page directly would silently produce one without a tray; the first draft did, and
    # it took a DOM check to notice, because a missing tray looks exactly like a page that never had
    # one.
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as tmp:
        tmp.write(fragment)
        frag_path = tmp.name
    try:
        composed = subprocess.run(
            [sys.executable, str(REPO / "scripts/brief-compose.py"), "--content", frag_path,
             "--slug", "backlog-table", "--title", "Backlog — every item, in plain sight",
             "--out", str(args.out)], capture_output=True, text=True)
    finally:
        pathlib.Path(frag_path).unlink(missing_ok=True)

    if composed.returncode != 0:
        # NOT silent, and NOT fatal. A fresh clone has no explainer to lift a tray from, and a
        # backlog view without the Ask button is still worth having — a page that cannot be written
        # at all is not. What must never happen is losing the tray without saying so.
        args.out.write_text(fragment)
        print(f"wrote {args.out}  ({len(rows)} rows, {open_n} open)")
        print("⚠  WITHOUT the Ask tray — brief-compose.py could not lift one:")
        # ⚠ THE WHOLE MESSAGE, not `.splitlines()[0]` (r2 finding R2-9). brief-compose puts its
        # headline on line 1 and the ACTIONABLE part — which tokens are missing — on line 2, so
        # printing one line told the reader a page had failed and never why. Measured 2026-09-10:
        # the tray vanished from this page and the reason was invisible for three runs.
        _msg = (composed.stderr.strip() or composed.stdout.strip() or "no output")
        for _line in _msg.splitlines():
            print("   " + _line)
        print("   The page renders and reloads; only the ask-a-question button is missing.")
        report_run(rows, unread)
        return 0

    print(f"wrote {args.out}  ({len(rows)} rows, {open_n} open, Ask tray lifted)")
    # ⚠ SAME PURE FUNCTION `build` used, called again rather than threaded through its
    # return — `build` is the renderer and its signature belongs to rendering. This is a
    # second CALL SITE of one implementation, not a second implementation, which is the
    # distinction this repo keeps paying for when it gets it wrong.
    #
    # It is printed AFTER the success line on purpose: the page WAS written, and the
    # warning qualifies it rather than replacing it. `explainer-serve._regenerate`
    # collects lines starting with ⚠ into the JSON `warning`, which the Refresh button
    # renders as "rebuilt WITH A WARNING: …" — the channel already exists.
    # ⚠ THE SAME FUNCTION `build` used, called a second time — not the same RULE written twice.
    # The distinction is the whole of r3 finding H-3: the previous comment here claimed "a second
    # call cannot disagree with the one `build` made", which was true when both sides called
    # `sanitise_groups` raw and became false the moment one side post-processed it. A second CALL
    # SITE of one implementation is safe; a second implementation is what this repo keeps paying
    # for. The ⚠ prefix is the existing channel: `_regenerate` collects those lines into the
    # Refresh button's warning.
    report_run(rows, unread)
    print("     http://127.0.0.1:7391/backlog-table   (start: python3 scripts/explainer-serve.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
