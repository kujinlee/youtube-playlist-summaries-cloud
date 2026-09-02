#!/usr/bin/env python3
"""Render `docs/backlog.md` as a browsable HTML page at a STABLE url.

    python3 scripts/gen-backlog-page.py          # → ~/explainers/backlog-table.html
    python3 scripts/gen-backlog-page.py --self-test
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

Its COMPLETENESS, though, is mechanical. `coverage_errors` refuses to write the page unless the
groups cover the derived open set exactly once. So a line here can be badly worded, but an open item
can never go silently missing — which is the failure that matters when the page is answering "what
is left?". When an item is filed or closed, this script FAILS until `GROUPS` is updated. That is the
intended cost: a loud stop beats a quiet omission.

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
import html
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
GROUPS: list[tuple[str, str, list[tuple[int, str]]]] = [
    ("Paid work can be lost when a video's address changes",
     "Every summary is filed under a name built from the video's title, so changing the title "
     "changes the address — and not everything pointing at the old one follows. Summaries cost "
     "real money, so losing one loses money. Six items, one root cause; they were split apart "
     "during the addressing work when a single fix kept failing review.", [
        (17, "The background worker and the sync process can write at the same time with nothing "
             "stopping them. On one path that destroys paid content, not just a pointer."),
        (19, "When a video moves between playlists, a worker finishing late can overwrite the "
             "winner's content with stale content."),
        (20, "Renaming a video orphans all of its dig-deeper documents — only half the address is "
             "protected."),
        (21, "Dig-deeper writes have the same stale-address exposure but write somewhere else, so "
             "they need their own fix."),
        (22, "When a video is re-addressed, the “this was paid for” status does not reliably "
             "follow it — the database row carries no stable identity to hang it on."),
        (25, "Rendered pages and PDFs have no identity of their own either. Two designs for one "
             "have already been refuted, so this needs a fresh pass."),
        (60, "Corrections you type never reach a summary the background worker regenerates on its "
             "own — and the row claims they were applied. Fixing it is blocked by the same "
             "overwrite problem as the items above: the corrected version can be thrown away while "
             "the record still says it exists."),
     ]),
    ("Anonymous users hold more database access than intended",
     "All measured in production, and none of it currently reachable through the web API — but the "
     "grants are real, and the third item is about the next one arriving by accident.", [
        (30, "TRUNCATE — delete everything in a table — is granted to the anonymous and signed-in "
             "roles on all five money tables. Row-level security does not cover that verb."),
        (33, "Anonymous callers hold EXECUTE on nearly every database function. Each migration says "
             "<code>revoke … from public</code>, which reads like “anonymous excluded” and is not."),
        (54, "The durable fix. The detector half shipped on 2026-08-21; the half that revokes the "
             "default changes production grants and is waiting on your go-ahead."),
     ]),
    ("Money-path edge cases",
     "Small, well understood, and each needs one decision before the code can be written.", [
        (26, "Two different retry ceilings could govern a paid job — one attempt, or five. The "
             "function that used to decide was deleted; nothing decides now."),
        (27, "A summary that a paid dig was built from is currently pinned for the life of the "
             "workspace. Decide whether cleanup is ever allowed to release it."),
        (28, "If reserving budget times out, 6¢ is stranded permanently and an attempt is burned. "
             "Introduced by the serve-path work this month."),
        (61, "Cloud corrections will record what they spent <em>after</em> the call rather than "
             "reserving it first — a deliberate choice to keep the first slice shippable. This "
             "adds the reservation, and a check that the spending bound still covers everything "
             "the job pays for once corrections run inside it."),
        (62, "A correction that FAILS still pays Gemini, and nothing records it — so neither the "
             "per-person daily limit nor the overall spending cap ever sees that money. Measured "
             "in production: the spend table was empty after a real failed press. Corrections can "
             "be made to fail on purpose, so this is a way to spend past a limit rather than an "
             "accounting rounding error."),
        (63, "When a correction fails, the person who was just charged sees the internal error "
             "text rather than anything they can act on. The friendly-message mechanism already "
             "exists a few lines away in the same function."),
     ]),
    ("Sync",
     "One item, and its symptom is silence rather than an error.", [
        (32, "Each local folder records which cloud it last synced with. Point it at a different "
             "cloud and sync uploads nothing, forever, without complaining."),
     ]),
    ("Product features you might actually want",
     "Nothing here is broken; this is the work that makes the product better.", [
        (1,  "Deep-dives serve a stale cached copy and silently always regenerate, with no progress "
             "indicator. Bring them level with summaries."),
        (2,  "Re-summarising leaves the PDF stale. Decide: keep generating PDFs, or make the HTML "
             "printable and drop them."),
        (3,  "Clickable timestamps inside deep-dives, jumping to the right moment in the video."),
        (8,  "Reframe the deep-dive from a separate document into an expandable detail view under "
             "each summary section. Large, and explicitly “someday”."),
        (12, "Share links currently carry the summary only — a dig-deeper cannot be shared."),
        (15, "Generate the magazine-style rendering when a video is ingested rather than on first "
             "view, so the first view is not slow and sharing always works."),
        (23, "Corrections you write are handed to the model as free-form instructions, and a fresh "
             "summarise can silently drop them while reporting success. Make them exact "
             "find-and-replace pairs instead."),
        (24, "Slide placeholders in cloud dig-deepers render as captions with no link. Make them "
             "clickable timestamps."),
        (51, "Feasibility study: summarise a single video without having to create a playlist first."),
        (52, "Split a large playlist into focused smaller ones, with the same video allowed in "
             "several — and decide whether they can share one paid summary."),
     ]),
    ("Small visual polish",
     "Extra-small items, mostly in the renderer, all independent of everything above.", [
        (4, "A markdown edge case: a closing code fence carrying a language name is accepted."),
        (5, "The colour palette is copy-pasted between two renderers; extract it once."),
        (6, "The gold “lead” line is over-emphasised and competes with the section heading."),
        (7, "Bold bullet labels usually just repeat the first words of the sentence. Drop them."),
        (81, "Entries you have already answered still say “waiting on you” in their text. The "
             "machinery to fix that was built and works — it has simply never been used, because "
             "the asks were always written as ordinary sentences instead of in the form the page "
             "understands. Costs nothing to start doing correctly."),
     ]),
    ("The reusable toolkit — the second deliverable",
     "Not about the product: about the development harness being reusable on a new project.", [
        (18, "32 of the 42 installed skills have never once been used. Audit, trim, and find out "
             "why the wanted ones never fire."),
        (40, "Package the explainer tooling as an installable plugin so a new project gets it "
             "without copying files."),
        (47, "A knowledge graph over document fragments, so prior work is found rather than "
             "remembered."),
        (49, "A checker that resolves every <code>file:line</code> a spec cites — eight were wrong "
             "in a single document."),
        (50, "Refine the <code>/brief</code> skill — the page this one is a sibling of."),
        (56, "Render the launch roadmap as a standing page like this one, deriving its ticks from "
             "git rather than trusting them, so “where are we overall” stops being a hand "
             "reconciliation."),
        (57, "A page over the 690 review documents, surfacing the one number that predicts a "
             "runaway review — how much of each round was caused by the last round's fixes — while "
             "it can still change a decision."),
        (58, "Every gate in one place: what it is, what it last returned, and which have never "
             "failed — because a gate that cannot fail is the one to distrust."),
     ]),
    ("Process, tooling and bookkeeping",
     "Instruments and habits. Cheap individually; they are what stops the expensive items above "
     "from recurring.", [
        (16, "After a deploy, a browser tab left open keeps running the old JavaScript with no "
             "“refresh available” prompt."),
        (29, "A guard-coverage checker only inspects the parked schema, so the guards in real "
             "migrations are invisible to it."),
        (38, "Extract the sidebar's load/refresh state machine into a hook — a reviewer, asked "
             "directly, said the current version was not worth its complexity."),
        (39, "Roadmap items are identified by their position, so renumbering silently changes what "
             "an old reference means."),
        (41, "The prod read-only smoke. Built and green on 2026-08-21 — this row has simply not "
             "been closed yet."),
        (42, "Next.js says <code>middleware</code> is deprecated on every startup. It is the "
             "authentication gate, so this is read-the-guide-first work."),
        (45, "Leftover medium and low findings from a review round, presented for your decision "
             "rather than fixed."),
        (46, "Normalise unusual Unicode in titles before building a filename, so characters that "
             "fold into path syntax never reach the address."),
        (53, "You can verify which release is live, but not which commit it was built from. "
             "Deliberately dormant until its trigger fires."),
        (66, "Ninety-two written notes from past work sessions exist on one machine, are excluded "
             "from git, and have no backup. Nobody has decided whether they are worth keeping. "
             "The expensive part of that folder was already reclaimed; this is the residue, and "
             "the decision is yours."),
        (67, "Two helpers working at the same time can corrupt each other's results — measured "
             "twice, once producing a false alarm that was filed as a blocking defect before anyone "
             "traced it, and once nearly swallowing uncommitted work. Most of the danger has since "
             "been engineered out. What is left is that the warning about it sits in a comment "
             "inside one script, names two scripts that no longer exist, and is absent from the "
             "document where the decision to run two helpers is actually made."),
        (71, "Four of the pages this project generates — including this one — each turn markdown "
             "into HTML with their own separate code, and they no longer agree. On this page it "
             "shows: a piece of SQL renders with a character swallowed, and file paths lose the "
             "asterisks in them. The fix that removes it already exists in a fourth generator and "
             "cannot be reached from the other three."),
        (72, "The inventory that polices our safety checks cannot see one that is not NAMED like "
             "one. It says in writing that it catches a check even before anyone wires it up; that "
             "second route is unreachable, and was measured to be."),
        (73, "A superseded piece of that same inventory is still in the file, and the only thing "
             "that still runs it is its own test — so part of its reported coverage is of "
             "machinery nothing uses. Waiting on the decision above."),
        (78, "The check that makes sure work gets written up cannot see a branch that ONLY writes "
             "one up — the most common way an entry is added. One question is being answered by "
             "one test: excusing a branch from owing an entry silently excuses the entry it added "
             "from being well-formed. It also runs only when a pull request opens, by which time "
             "you have already read the page."),
        (82, "The same check reads the SHAPE of an entry's header but never asks whether the "
             "thing it points at exists. An entry can say “this settles the question from "
             "Tuesday” while naming a Tuesday that never happened, and it passes — the page is "
             "left to say “could not parse this entry” after you have already opened it."),
        (83, "A settled item tells you it was decided but never what was decided, and the card "
             "carrying it still wears the styling of something live. Two small things, one "
             "effect: you cannot tell from the page which questions are actually closed."),
        (84, "The guide for writing these entries says you may put an example in a code block "
             "and the page will leave it alone. The page had no idea what a code block was, so "
             "one example could cut an entry in half and quietly take the identifier belonging "
             "to the next one — and those identifiers are how an entry says which earlier "
             "question it answers. Fixed and merged; the row stays for the record."),
        (85, "Three separate pieces of that same machinery each work out for themselves what a "
             "code block is, and only one of them is the shared version. Nothing is broken "
             "today and the part the page uses is the correct one — but these copies have "
             "already disagreed twice, once in a way that made a real question invisible."),
     ]),
]


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
    """PURE. Same posture as `coverage_errors`: the prose may be wrong, the graph may not be
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
        kids = sorted((n for n, (_, r, _) in DEPENDS.items() if r == rk),
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
        kids = sorted((n for n, (_, r, _) in DEPENDS.items() if r == rk),
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
    """Item number → its row's raw text, for one version of the file."""
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


def parse(lines: Sequence[str]) -> list[dict]:
    rows: list[dict] = []
    header: list[str] = []
    section = ""
    for line in lines:
        if line.startswith("## "):
            section, header = line[3:].strip(), []
            continue
        if re.match(r"^\|\s*#\s*\|", line):
            header = [c.strip().lower() for c in CELL_SPLIT.split(line)[1:-1]]
            continue
        if not re.match(r"^\|\s*\d+\s*\|", line):
            continue
        cells = [c.strip() for c in CELL_SPLIT.split(line)[1:-1]]
        if not header or len(cells) != len(header):
            raise ShapeError(f"row has {len(cells)} cells, header has {len(header)}: {line[:70]}")
        col = dict(zip(header, cells))
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


def coverage_errors(groups: list, open_nums: set[int]) -> list[str]:
    """PURE. The grouping is prose; this is the part that cannot be wrong silently."""
    grouped = [n for _, _, items in groups for n, _ in items]
    errors = []
    missing = sorted(open_nums - set(grouped))
    extra = sorted(n for n in grouped if n not in open_nums)
    dupes = sorted({n for n in grouped if grouped.count(n) > 1})
    if missing:
        errors.append(f"open items missing from GROUPS: {missing}")
    if extra:
        errors.append(f"GROUPS names items that are not open: {extra}")
    if dupes:
        errors.append(f"items appearing in more than one group: {dupes}")
    return errors


# ─── rendering ──────────────────────────────────────────────────────────────────────────────────

def card(r: dict) -> str:
    sev = "done" if r["closed"] else r["sev"]
    flag = ('<span class="flag" title="This row&#39;s own Status cell carries a warning — read it '
            'before trusting any summary of this item">&#9888; see status</span>') if r["warned"] else ""
    meta = "".join(
        f'<span class="chip"><b>{lbl}</b>{md(val)}</span>'
        for lbl, val in (("was ", r["was"]), ("touches ", r["touches"]),
                         ("size ", r["size"]), ("bundle ", r["bundle"]))
        if val and val not in {"—", "-"})

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
<article class="item" data-sev="{sev}" data-state="{'closed' if r['closed'] else 'open'}"{attrs} id="i{r['num']}">
  <div class="num"><a href="#i{r['num']}">#{r['num']}</a></div>
  <div class="body">
    <div class="titleline"><span class="badge" hidden></span><h3>{md(r['title'])}</h3>{flag}</div>
    <div class="meta">{meta}{stamp}</div>
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
          generated_at: str = "") -> str:
    open_rows = [r for r in rows if not r["closed"]]
    closed_rows = [r for r in rows if r["closed"]]
    by_sev = {k: sum(1 for r in open_rows if r["sev"] == k)
              for k in ("crit", "high", "med", "low", "none")}
    flagged = [r for r in rows if r["warned"]]
    by_num = {r["num"]: r for r in rows}

    open_nums = {r["num"] for r in open_rows}
    errors = coverage_errors(GROUPS, open_nums)
    if errors:
        raise ShapeError("GROUPS does not cover the open set — " + "; ".join(errors))
    errors = depends_errors(DEPENDS, ROOTS, open_nums)
    if errors:
        raise ShapeError("DEPENDS is incoherent — " + "; ".join(errors))

    order = {"crit": 0, "high": 1, "med": 2, "low": 3, "none": 4}
    open_rows.sort(key=lambda r: (order[r["sev"]], r["num"]))
    closed_rows.sort(key=lambda r: r["num"])

    gate_of, groups_html = {}, ""
    for gi, (title, framing, items) in enumerate(GROUPS, 1):
        # ORDERED, not as listed. Items that survive the root — or have no root — come first;
        # anything the root deletes sinks to the bottom, because that is work you should not start.
        ordered = sorted(items, key=lambda it: (dep_rank(it[0]), it[0]))

        used_roots = {DEPENDS[n][1] for n, _ in ordered if n in DEPENDS}
        starthere = ""
        for rk in sorted(used_roots):
            if rk not in ROOTS:
                continue
            tally = {}
            for n, _ in ordered:
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
        for n, line in ordered:
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
  --serif:Georgia,'Iowan Old Style','Times New Roman',serif;
  --sans:ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif;
  --mono:ui-monospace,'SF Mono',Menlo,Consolas,monospace;
}}
@media (prefers-color-scheme:dark){{:root{{
  --ink:#e7e9ee; --ink-2:#a9b2c0; --ink-3:#7a8494; --ink-faint:#7a8494;
  --ground:#101318; --panel:#171b22; --card:#171b22; --line:#2a3039; --line-2:#20252d;
  --measured:#4fc9b8; --problem:#f0836a; --structural:#8fb0e0;
  --pending:#eab464; --pending-bg:#251d10; --ink-soft:#a9b2c0; --good:#4fc9b8;
}}}}
:root[data-theme="dark"]{{
  --ink:#e7e9ee; --ink-2:#a9b2c0; --ink-3:#7a8494; --ink-faint:#7a8494;
  --ground:#101318; --panel:#171b22; --card:#171b22; --line:#2a3039; --line-2:#20252d;
  --measured:#4fc9b8; --problem:#f0836a; --structural:#8fb0e0;
  --pending:#eab464; --pending-bg:#251d10; --ink-soft:#a9b2c0; --good:#4fc9b8;
}}
:root[data-theme="light"]{{
  --ink:#12161c; --ink-2:#39424f; --ink-3:#6b7686; --ink-faint:#6b7686;
  --ground:#f7f6f3; --panel:#ffffff; --card:#ffffff; --line:#dfdcd5; --line-2:#eceae5;
  --measured:#0f7268; --problem:#ad3a22; --structural:#3d5a86;
  --pending:#a8690b; --pending-bg:#fdf4e3; --ink-soft:#39424f; --good:#0f7268;
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
<p class="dek">Grouped by what the item <em>is</em>, not by how loud its marker is. This is the one
part of the page written by hand — but it refuses to build if the groups do not cover every open
item exactly once, so an item can be described badly here and still never go missing. Each number
opens its full entry below.</p>

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
</div>

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
  var f = {{state:'open', sev:'all'}};
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
      var show = okS && okV;
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

    lines = SAMPLE.splitlines()
    rows = parse(lines)
    by = {r["num"]: r for r in rows}

    case("reads both tables, six-column and three-column", lambda: len(rows) == 4)
    case("the three-column row is read against ITS header", lambda: by[9]["title"] == "Delta")
    case("a row whose width disagrees with its header RAISES", lambda: _raises(
        lambda: parse(["| # | Item | Status |", "|---|---|---|", "| 5 | x | y | z |"]), ShapeError))
    case("a row before any header RAISES rather than guessing", lambda: _raises(
        lambda: parse(["| 5 | x | y |"]), ShapeError))

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

    case("coverage passes when the groups match exactly",
         lambda: coverage_errors([("g", "f", [(1, "x"), (2, "y")])], {1, 2}) == [])
    case("coverage FAILS on an open item nobody grouped",
         lambda: "missing" in " ".join(coverage_errors([("g", "f", [(1, "x")])], {1, 2})))
    case("coverage FAILS when a group names a closed item",
         lambda: "not open" in " ".join(coverage_errors([("g", "f", [(1, "x"), (7, "z")])], {1})))
    case("coverage FAILS on a duplicate across groups",
         lambda: "more than one" in " ".join(
             coverage_errors([("a", "f", [(1, "x")]), ("b", "f", [(1, "x")])], {1})))

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
    case("GROUPS covers the REAL backlog's open set exactly once",
         lambda: coverage_errors(GROUPS, {r["num"] for r in real if not r["closed"]}) == [])
    case("the real file parses at all (fail-closed on a restructure)", lambda: len(real) > 20)

    failed = 0
    for name, fn in cases:
        try:
            ok = bool(fn())
        except Exception as exc:                                   # noqa: BLE001 - report, not hide
            ok, name = False, f"{name}  [raised {exc!r}]"
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
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
    try:
        text = BACKLOG.read_text()
        rows = parse(text.splitlines())
        attach_history(rows, text)
        fragment = build(rows, git("rev-parse", "--short", "HEAD"),
                         git("log", "-1", "--format=%cI", "--",
                             "docs/backlog.md")[:16].replace("T", " "),
                         subprocess.run(["date", "+%Y-%m-%d %H:%M %Z"],
                                        capture_output=True, text=True).stdout.strip(),
                         page_chrome.provenance(
                             _dt.datetime.now().strftime("%Y-%m-%d %H:%M"), REPO))
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
        print("   " + (composed.stderr.strip() or composed.stdout.strip() or "no output").splitlines()[0])
        print("   The page renders and reloads; only the ask-a-question button is missing.")
        return 0

    print(f"wrote {args.out}  ({len(rows)} rows, {open_n} open, Ask tray lifted)")
    print("     http://127.0.0.1:7391/backlog-table   (start: python3 scripts/explainer-serve.py)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
