#!/usr/bin/env python3
"""The marketplace inventory's falsifiers as a guard, and the D1 checkpoint (marketplace-inventory plan, Task 19).

    python3 scripts/check-inventory.py              # the live inventory under this repository
    python3 scripts/check-inventory.py --render     # the same checks; on rc 0 or 3, the Markdown view on stdout
    python3 scripts/check-inventory.py --root DIR   # another tree (the self-test's fixture worlds)
    python3 scripts/check-inventory.py --self-test  # 296 cases

It reads `docs/marketplace/inventory.json`, `components.json`, `shipping-sets.json`, the LATEST `scan-<date>.json`
(by name), `experiment-tier-a.json`, the spec (which owns the `spec` ground kind, §5 rule 1) and
`docs/portable-practices.md` (which owns `practice_entry`).

Exit codes RANK, and the order is the rule (plan Task 19): an input unreadable or absent → 2 (CANNOT RUN: treat
as NOT RUN); else any row or inventory error → 1, and the checkpoint is NOT computed (a fire over rows with errors
is not evidence); else `checkpoint_fires` raising (no phase-1 rows) → 2; else the checkpoint fired → 3 (stop: Human
step H4); else 0. So rc 1 outranks rc 3.

Inputs are read by one bounded reader and one walker (Phase 6 review, 2026-11-22, backlog #699). `_read_json`
returns a value that is UTF-8, free of NaN/Infinity and repeated keys, and at most MAX_DEPTH deep; FILE_SHAPES
declares, per input file, every field a rule reads, and `_violations` is the only code that checks one. A field a
rule compares with a literal is declared `_one_of` its vocabulary (a typo is unreadable, never "the other value").
A rule relating two places lives in `_reference_errors`. Any failure of these is rc 2. No message prints an input
value except through `_show`. `main` is a net: an exception nothing anticipated is rc 2 with `INTERNAL ERROR`,
never Python's own exit 1, which is this guard's code for "row errors". Adding a rule that reads a new input field
means adding that field to FILE_SHAPES in the same commit.

Every error is printed as `<row id>: [<rule>] <why>`; the rule tag names which falsifier refused it.

`row_errors` FIRST checks the row's SHAPE (r1 fold); a row that fails it is reported and NOT handed to the rules:
  [shape]            a row that is not an object, or a field of the plan's row schema (ROW_SCHEMA) missing or of the
                     wrong type: a grade, verdict, phase, harvest, role, criterion key or value, cost grade or route
                     kind outside its vocabulary (§4b: a verdict without a grade is incomplete; the map's
                     1-if-feasible phase is refused); a cost or route estimate that is not a FINITE number, or a
                     public_bar_hours or cost_hours that is not positive
then the rules (each a spec falsifier; the plan's list, plus backlog #696 (a), (c) and (f)):
  [map]              a row whose id is not in components.json, or whose effort or roles differ from the map's (the
                     role rules below read the row's roles; a row that relabelled itself `data` would escape them)
  [ship-experiment]  a SHIP row in a `plugin`-channel package the tier-A experiment does not back (§9), BY ROLE:
                     an entry-point needs its OWN sidecar entry with exercised true, operation_ok true, at least
                     one pass condition, and none `fail` or `CANNOT RUN`; a library is held to that test on the
                     entry-point component its `scenario` names (the id before the first `:`, the convention
                     `<entry-point id>: <description>`), refused if it names none or one from another package (§4:
                     C4 is inherited from the entry-point that uses the library); a data row is outside the rule (its C4 is struck), and so is a non-plugin package
  [shipping-set]     a phase-1 row whose component is absent from its package's components in shipping-sets.json
  [recall-phase]     a recall (effort 1) row at "1" unless the inventory's recall.a is true and recall.b is "pass"
  [next-project]     next_project_hours <= 0 (the ratio is undefined)
  [inherited]        an `inherited` grade with no scenario
  [rests-on]         a non-SHIP row whose rests_on is empty
  [ground-kind]      a rests_on entry whose kind is not one of GROUND_KINDS
  [ground-empty]     (backlog #696 f) a `finding` ground with no ids; a `spec` ground with an empty section,
                     heading or decision; an `experiment` ground with no scenario
  [ground-finding]   a finding id that is not a string, or absent from the scan's findings for the row's OWN
                     component (a borrowed id from another component is refused)
  [ground-spec]      a spec section with no `## <n>. ` line; a heading with no exact `### <heading>` line under
                     that section (before the next `## `); a decision with no `| **D<n>** |` table row in §2 and
                     no `### D<n>.` heading in §2b
  [ground-experiment] an experiment scenario that is not this component's sidecar entry, or has no pass
                     condition `fail`
  [ground-c5]        a c5 ground on a row whose C5 is not `unanswered`
  [measured-finding] C2 or C3 `fail` at grade `measured` with no `finding` ground
  [route]            a non-SHIP row with no route (§9 D10)
  [practice]         (backlog #696 c) a `practice` harvest whose practice_entry is not EXACTLY a `## ` heading of
                     docs/portable-practices.md: the full heading text WITH its number and WITHOUT the `## `
                     prefix, e.g. `10. A surviving mutation does not mean "add a test" — first ask ...`
  [data-c4]          a data row with a C4 other than "struck"
  [corpus-c5]        the memory-corpus row with a SHIP verdict while its C5 is unanswered (§7 item 11)
  [measured-effort]  a `measured` grade on an effort (1) or (2) row (§2b)
and at the inventory level (`inventory_errors`):
  [missing]          a component in components.json with no row
  [duplicate]        two rows for one component
  [phase1-package]   no phase-1 package named (no component of phase "1" in the map)
  [package-shipping] a phase-1 package with no entry in shipping-sets.json
  [scan]             the inventory names a scan other than the latest one

The guard checks that a ground RESOLVES, not that it bears on the verdict; that stays the reviewer's judgement.

Guard classification (check-guard-coverage's vocabulary): SHAPE — every rule asks whether a row is well-formed and
referentially sound against files read at one moment; none asks who got there first.

Caller: the `check-inventory self-test` step of .github/workflows/ci.yml runs `--self-test` ONLY. The live run joins
CI in plan Task 20, in the commit that completes the rows (until then a missing component is rc 1 by construction).
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import math
import re
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MKT = "docs/marketplace"
SPEC = "docs/superpowers/specs/2026-10-15-marketplace-inventory-design.md"
PRACTICES = "docs/portable-practices.md"

VERDICTS = ("SHIP", "NEEDS-WORK", "DON'T-SHIP")
GRADES = ("measured", "inherited", "argued", "none")
PHASES = ("1", "later")
GROUND_KINDS = ("finding", "spec", "experiment", "c5")
ROLES = ("entry-point", "library", "data")                  # spec §4's role table
HARVESTS = ("practice", "none")                             # spec §4c, D6
CRITERIA = ("C1", "C2", "C3", "C4", "C5")                   # spec §4
CRITERION_VALUES = ("pass", "fail", "struck", "unanswered")  # §4 (`struck`: a data row's C4), §7 item 11

# backlog #696 (a): the route vocabulary is spec D10's four routes, and nothing else.
ROUTE_KINDS = {
    "decouple-config": "decouple it behind a config file, so its project-specific values become settings",
    "template-repository": "ship it as a template repository rather than a plugin",
    "portable-core": "ship only its portable core, leaving the project-specific part behind",
    "practice": "publish it as a practice (D6's `harvest: practice`), not as code",
}


class CannotRun(Exception):
    pass


class Context:
    """What a row is checked against besides the four positional inputs: the component map, the package channels,
    each package's shipping set, the practice headings, and the inventory's recall answers."""

    def __init__(self, components, channels, shipping, practice_headings, recall):
        self.components = components            # id -> component dict (components.json)
        self.channels = channels                # package -> channel
        self.shipping = shipping                # package -> set of component ids (shipping-sets.json)
        self.practice_headings = practice_headings
        self.recall = recall                    # inventory.json `recall`


def _fires(pop):
    """public_bar >= 3 x next_project for MORE THAN HALF of `pop`."""
    if not pop:
        raise ValueError("CANNOT RUN: no phase-1 rows")
    for r in pop:
        if not r["cost"]["next_project_hours"] > 0:
            raise ValueError(f"CANNOT RUN: {r.get('id', '?')} has next_project_hours <= 0 "
                             "(a row error; row_errors must have refused it first)")
    over = [r for r in pop
            if r["cost"]["public_bar_hours"] >= 3 * r["cost"]["next_project_hours"]]
    return 2 * len(over) > len(pop)


def checkpoint_fires(rows):
    """D1 checkpoint (spec §2c) over the phase-1 population: phase "1" rows, and nothing else.
    Task 18 resolves recall to "1" or "later" (D11's "only if"); a row still carrying the map's
    "1-if-feasible" label is a row error refused before this runs (rc 1 outranks), and is not counted."""
    return _fires([r for r in rows if r["phase"] == "1"])


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _finite(v):
    """A number that is not NaN or infinite: NaN compares false with everything and infinity outranks every
    estimate, so either would decide the checkpoint without being an estimate (r1 fold, CLAUDE C1). An integer is
    finite when a float can hold it: `math.isfinite` converts to float, and an integer past the float range raises
    OverflowError there instead of answering (r2 fold, CODEX X1), so it is refused before the conversion."""
    if isinstance(v, int) and not isinstance(v, bool):
        return abs(v) <= sys.float_info.max
    return isinstance(v, float) and math.isfinite(v)


def _in(vocab):
    """A string member of `vocab` (the str test first, so an unhashable value is refused, never a TypeError)."""
    return lambda v: isinstance(v, str) and v in vocab


def _str_or_null(v):
    return v is None or isinstance(v, str)


def _criteria_ok(v):
    return (isinstance(v, dict) and set(v) == set(CRITERIA)
            and all(_in(CRITERION_VALUES)(x) for x in v.values()))


def _cost_ok(v):
    """Both estimates finite, the public bar positive; `next_project_hours` <= 0 is its own rule ([next-project])."""
    return (isinstance(v, dict) and _finite(v.get("public_bar_hours")) and v["public_bar_hours"] > 0
            and _finite(v.get("next_project_hours")) and _in(GRADES)(v.get("grade")))


def _route_ok(v):
    return v is None or (isinstance(v, dict) and _in(ROUTE_KINDS)(v.get("kind"))
                         and _finite(v.get("cost_hours")) and v["cost_hours"] > 0 and _in(GRADES)(v.get("grade")))


# The plan's row schema (Task 19), one entry per field: (key, test, what the field must be). Every key is REQUIRED;
# a nullable field is present with null. Keys outside the schema (`notes`) are allowed.
ROW_SCHEMA = (
    ("id", lambda v: isinstance(v, str) and bool(v.strip()), "a non-empty string"),
    ("effort", lambda v: isinstance(v, int) and not isinstance(v, bool), "an integer"),
    ("roles", lambda v: isinstance(v, list) and bool(v) and all(_in(ROLES)(x) for x in v),
     f"a non-empty list of {', '.join(ROLES)}"),
    ("phase", _in(PHASES), f"one of {', '.join(PHASES)} (the map's 1-if-feasible is resolved by Task 18)"),
    ("verdict", _in(VERDICTS), f"one of {', '.join(VERDICTS)}"),
    ("grade", _in(GRADES), f"one of {', '.join(GRADES)} (§4b: a verdict without a grade is incomplete)"),
    ("scenario", _str_or_null, "a string or null"),
    ("rests_on", lambda v: isinstance(v, list), "a list"),
    ("harvest", _in(HARVESTS), f"one of {', '.join(HARVESTS)} (§4c)"),
    ("practice_entry", _str_or_null, "a string or null"),
    ("criteria", _criteria_ok, f"an object with exactly {', '.join(CRITERIA)}, each one of "
                               f"{', '.join(CRITERION_VALUES)}"),
    ("cost", _cost_ok, "an object with a finite positive public_bar_hours, a finite next_project_hours and a grade "
                       f"one of {', '.join(GRADES)} (§2b)"),
    ("route", _route_ok, f"null, or an object with a kind one of {', '.join(ROUTE_KINDS)}, a finite positive "
                         f"cost_hours and a grade one of {', '.join(GRADES)}"),
)


def _shape_errors(row):
    """Why `row` does not have the plan's row SHAPE, one string per field (empty when it does). Runs before every
    rule, so a rule may assume the shape and no traceback is reachable from row content (r1 fold)."""
    if not isinstance(row, dict):
        return [f"a row that is {type(row).__name__}, not an object"]
    out = []
    for key, ok, want in ROW_SCHEMA:
        if key not in row:
            out.append(f"{key} is missing; it must be {want}")
        elif not ok(row[key]):
            out.append(f"{key} {_show(row[key])} is not {want}")
    return out


def _section_lines(spec_lines, sec):
    """The lines under the `## <sec>. ` heading, up to the next `## ` line; None when there is no such heading."""
    for i, line in enumerate(spec_lines):
        if line.startswith(f"## {sec}. "):
            out = []
            for later in spec_lines[i + 1:]:
                if later.startswith("## "):
                    break
                out.append(later)
            return out
    return None


def _spec_ground_error(g, spec_lines):
    """None when the spec ground resolves; else (rule, why)."""
    if "decision" in g:
        d = g["decision"]
        if not isinstance(d, str) or not d.strip():
            return "ground-empty", "a spec ground with an empty decision"
        table = _section_lines(spec_lines, "2") or []
        walk = _section_lines(spec_lines, "2b") or []
        if any(line.startswith(f"| **{d}** |") for line in table) or any(line.startswith(f"### {d}.") for line in walk):
            return None
        return "ground-spec", f"the spec has no decision {d} in §2 or §2b"
    sec = g.get("section")
    if not isinstance(sec, str) or not sec.strip():
        return "ground-empty", "a spec ground with an empty section"
    if "heading" in g and (not isinstance(g["heading"], str) or not g["heading"].strip()):
        return "ground-empty", "a spec ground with an empty heading"
    body = _section_lines(spec_lines, sec)
    if body is None:
        return "ground-spec", f"the spec has no `## {sec}. ` section"
    if "heading" in g and not any(line.rstrip() == f"### {g['heading']}" for line in body):
        return "ground-spec", f"the spec has no `### {g['heading']}` under section {sec}"
    return None


def _backs(entry):
    """A tier-A sidecar entry backs a SHIP: exercised, operation_ok, and every one of its pass conditions neither
    `fail` nor `CANNOT RUN` (an entry with no pass conditions is no evidence)."""
    pcs = (entry or {}).get("pass_conditions") or {}
    return (bool(entry) and entry.get("exercised") is True and entry.get("operation_ok") is True and bool(pcs)
            and not any(v in ("fail", "CANNOT RUN") for v in pcs.values()))


def _named_entry_point(scenario, components):
    """The entry-point component id a library's scenario names (the text before the first `:`), or None."""
    if not isinstance(scenario, str):
        return None
    head = scenario.split(":", 1)[0].strip()
    comp = components.get(head)
    return head if comp and "entry-point" in (comp.get("roles") or []) else None


def row_errors(row, scan, spec_text, sidecar, *, ctx):
    """Every falsifier this row trips, as `<id>: [<rule>] <why>` strings (the rules are listed in the module
    docstring). `ctx` is REQUIRED (keyword-only): without the map, a role rule cannot be applied, and a call that
    omits it raises TypeError rather than skipping the rules silently."""
    shape = _shape_errors(row)
    if shape:
        rid = row["id"] if isinstance(row, dict) and ROW_SCHEMA[0][1](row.get("id")) else "?"
        return [f"{rid}: [shape] {why}" for why in shape]
    rid = row["id"]
    errs = []

    def err(rule, why):
        errs.append(f"{rid}: [{rule}] {why}")

    verdict, grade = row["verdict"], row["grade"]
    roles = row["roles"]
    criteria = row["criteria"]
    ship = verdict == "SHIP"

    comp = ctx.components.get(rid)
    if comp is None:
        err("map", "no component with this id in components.json")
    elif row.get("effort") != comp.get("effort") or list(roles) != list(comp.get("roles") or []):
        err("map", f"effort {_show(row.get('effort'))} / roles {_show(roles)} differ from components.json's "
                   f"{_show(comp.get('effort'))} / {_show(comp.get('roles'))}")

    package = (comp or {}).get("package")
    if ship and comp is not None and ctx.channels.get(package) == "plugin":
        if "entry-point" in roles:
            if not _backs(sidecar.get(rid)):
                err("ship-experiment", "SHIP entry-point not backed by its own tier-A entry (exercised, "
                                       "operation_ok, no pass condition fail or CANNOT RUN)")
        elif "library" in roles:
            named = _named_entry_point(row.get("scenario"), ctx.components)
            if named is None:
                err("ship-experiment", f"SHIP library whose scenario {_show(row.get('scenario'))} names no entry-point "
                                       "component id")
            elif ctx.components[named].get("package") != package:
                err("ship-experiment", f"SHIP library whose named entry-point {named} is in package "
                                       f"{_show(ctx.components[named].get('package'))}, not the library's {_show(package)}")
            elif not _backs(sidecar.get(named)):
                err("ship-experiment", f"SHIP library whose named entry-point {named} is not backed by its tier-A "
                                       "entry")

    phase = row["phase"]
    if phase == "1" and comp is not None and rid not in ctx.shipping.get(package, set()):
        err("shipping-set", f"phase-1 row absent from package {_show(package)}'s components in shipping-sets.json")
    if phase == "1" and row.get("effort") == 1:
        recall = ctx.recall or {}
        if not (recall.get("a") is True and recall.get("b") == "pass"):
            err("recall-phase", f"recall row at phase \"1\" while recall.a is {_show(recall.get('a'))} and recall.b "
                                f"is {_show(recall.get('b'))}")

    nxt = row["cost"]["next_project_hours"]
    if not nxt > 0:
        err("next-project", f"next_project_hours is {_show(nxt)}, which leaves the ratio undefined")

    if grade == "inherited" and not row.get("scenario"):
        err("inherited", "an inherited grade with no scenario")

    grounds = row["rests_on"]
    if not grounds and not ship:
        err("rests-on", "a non-SHIP row with an empty rests_on")

    spec_lines = spec_text.split("\n")
    own = {f.get("id") for f in ((scan.get(rid) or {}).get("findings") or [])}
    for g in grounds:
        kind = g.get("kind") if isinstance(g, dict) else None
        if kind not in GROUND_KINDS:
            err("ground-kind", f"a ground of kind {_show(kind)}, not one of {', '.join(GROUND_KINDS)}")
        elif kind == "finding":
            ids = g.get("ids")
            if not isinstance(ids, list) or not ids:
                err("ground-empty", "a finding ground with no ids")
                continue
            for fid in ids:
                if not isinstance(fid, str) or fid not in own:
                    err("ground-finding", f"finding {_show(fid)} is not in the scan's findings for {rid}")
        elif kind == "spec":
            bad = _spec_ground_error(g, spec_lines)
            if bad:
                err(*bad)
        elif kind == "experiment":
            scen = g.get("scenario")
            if not isinstance(scen, str) or not scen.strip():
                err("ground-empty", "an experiment ground with no scenario")
                continue
            entry = sidecar.get(rid) or {}
            if entry.get("scenario") != scen:
                err("ground-experiment", f"scenario {_show(scen)} is not {rid}'s tier-A entry")
            elif "fail" not in (entry.get("pass_conditions") or {}).values():
                err("ground-experiment", f"scenario {_show(scen)} has no pass condition `fail`")
        elif kind == "c5":
            if criteria.get("C5") != "unanswered":
                err("ground-c5", f"a c5 ground while C5 is {_show(criteria.get('C5'))}")

    if (grade == "measured" and "fail" in (criteria.get("C2"), criteria.get("C3"))
            and not any(isinstance(g, dict) and g.get("kind") == "finding" for g in grounds)):
        err("measured-finding", "C2 or C3 fail graded measured with no finding ground")

    if not row["route"] and not ship:
        err("route", "a non-SHIP row with no route (§9 D10)")

    if row.get("harvest") == "practice" and row.get("practice_entry") not in ctx.practice_headings:
        err("practice", f"practice_entry {_show(row.get('practice_entry'))} is not exactly a `## ` heading of "
                        f"{PRACTICES} (the heading text with its number, without `## `)")
    if "data" in roles and criteria.get("C4") != "struck":
        err("data-c4", f"a data row with C4 {_show(criteria.get('C4'))}, not \"struck\"")
    if rid == "memory-corpus" and ship and criteria.get("C5") == "unanswered":
        err("corpus-c5", "the memory-corpus row ships while its C5 is unanswered (§7 item 11)")
    if grade == "measured" and row.get("effort") in (1, 2):
        err("measured-effort", f"a measured grade on an effort ({row.get('effort')}) row (§2b)")
    return errs


def inventory_errors(inventory, ctx, latest_scan=None):
    """The inventory-level falsifiers (module docstring), as `inventory: [<rule>] <why>` strings."""
    errs = []
    rows = inventory.get("rows") or []
    ids = [r.get("id") if isinstance(r, dict) else None for r in rows]   # a non-object row is row_errors' [shape]
    for cid in ctx.components:
        if cid not in ids:
            errs.append(f"inventory: [missing] component {cid} has no row")
    for cid in sorted({i for i in ids if isinstance(i, str) and ids.count(i) > 1}, key=str):
        errs.append(f"inventory: [duplicate] {ids.count(cid)} rows for {cid}")
    phase1 = sorted({c.get("package") for c in ctx.components.values() if c.get("phase") == "1"}, key=str)
    if not phase1:
        errs.append("inventory: [phase1-package] no phase-1 package is named in components.json")
    for pkg in phase1:
        if pkg not in ctx.shipping:
            errs.append(f"inventory: [package-shipping] phase-1 package {_show(pkg)} has no entry in shipping-sets.json")
    if latest_scan is not None and inventory.get("scan") != latest_scan:
        errs.append(f"inventory: [scan] the inventory names scan {_show(inventory.get('scan'))}; the latest is "
                    f"{_show(latest_scan)}")
    return errs


def _cell(v):
    return "—" if v in (None, "") else str(v).replace("|", "\\|")


def render(rows):
    """The inventory as one Markdown table. Verdict and grade share ONE cell (`SHIP · argued`), so a SHIP row
    never reads as proven when it was only argued (§4b)."""
    out = ["| Component | Effort | Phase | Verdict · grade | Harvest | Route |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        route = r.get("route") if isinstance(r.get("route"), dict) else None
        out.append("| " + " | ".join([
            _cell(r.get("id")), _cell(r.get("effort")), _cell(r.get("phase")),
            _cell(f"{r.get('verdict')} · {r.get('grade')}"), _cell(r.get("harvest")),
            _cell(route.get("kind") if route else None)]) + " |")
    return "\n".join(out) + "\n"


def _refuse_constant(name):
    raise ValueError(f"the JSON constant {name} is not a number")


MAX_DEPTH = 32      # the committed inputs nest at most 6 deep (measured 2026-11-22); 32 is a decision, far above
                    # the data and far below the stack


def _unique_keys(pairs):
    """One object's pairs as a dict, refusing a repeated key: Python's parser keeps the LAST and says nothing."""
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f"the key {_show(k)} appears twice in one object")
        out[k] = v
    return out


def _read_json(path):
    """THE reader for every JSON input: parsed, or CannotRun. What it returns is a BOUNDED value: UTF-8 text (never
    the locale's encoding), no NaN or Infinity constant, no repeated key, and nested at most MAX_DEPTH deep, so
    `repr`, `==` and a recursive walk are total over it."""
    try:
        doc = json.loads(path.read_bytes().decode("utf-8"), parse_constant=_refuse_constant,
                         object_pairs_hook=_unique_keys)
    except (OSError, ValueError) as e:
        raise CannotRun(f"{path} is unreadable ({type(e).__name__}: {e})") from e
    except RecursionError as e:
        raise CannotRun(f"{path} is unreadable (nested too deep to parse)") from e
    todo = [(doc, 1)]
    while todo:                     # iterative: the walk itself must not depend on the stack
        v, depth = todo.pop()
        if isinstance(v, (list, dict)):
            if depth > MAX_DEPTH:
                raise CannotRun(f"{path} is unreadable (nested deeper than {MAX_DEPTH} levels)")
            todo.extend((x, depth + 1) for x in (v.values() if isinstance(v, dict) else v))
    return doc


def _read_text(path):
    """The file's text as UTF-8, or CannotRun."""
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, ValueError) as e:
        raise CannotRun(f"{path} is unreadable ({type(e).__name__})") from e


CHANNELS = ("plugin", "reusable-workflow")                  # check-shipping-sets.py's CHANNELS (it owns the map)
MAP_PHASES = ("1", "1-if-feasible", "later")                # check-shipping-sets.py's PHASES (the map's own)
PASS_VALUES = ("pass", "fail", "argued", "CANNOT RUN")      # plan Task 14 Step 6


def _is_id(v):
    return isinstance(v, str) and bool(v.strip())


def _show(v):
    """A value as a message may print it: bounded in length, and never the repr of a container."""
    if isinstance(v, (list, dict)):
        return f"a list of {len(v)}" if isinstance(v, list) else f"an object with {len(v)} keys"
    text = repr(v)
    return text if len(text) <= 60 else text[:57] + "..."


# A SHAPE is (kind, what it must be, argument). Five kinds, and `_violations` is the only code that reads one.
def _is(want, test):
    return ("is", want, test)


def _one_of(*vocab):
    """Membership by TYPE and value: True is not 1, and 1.0 is not 1."""
    return _is("one of " + ", ".join(repr(m) if not isinstance(m, str) else m for m in vocab),
               lambda v: any(type(v) is type(m) and v == m for m in vocab))


def _null_or(shape):
    return ("null_or", f"null, or {shape[1]}", shape)


def _list_of(item, least=0):
    return ("list", f"a list of at least {least}, each {item[1]}" if least else f"a list, each {item[1]}",
            (item, least))


def _map_of(value):
    return ("map", f"an object whose values are each {value[1]}", value)


def _obj(**fields):
    return ("obj", "an object with " + ", ".join(fields), fields)


_ANY = _is("any value", lambda v: True)
_STR = _is("a string", lambda v: isinstance(v, str))
_ID = _is("a non-empty string", _is_id)
_BOOL = _is("true or false", lambda v: isinstance(v, bool))
_INT = _is("an integer", lambda v: isinstance(v, int) and not isinstance(v, bool))

# Every field of an input FILE that a rule reads, and nothing a rule does not read. A field a rule compares with a
# literal, where a miss would be SILENT, is `_one_of` its vocabulary: a typo is unreadable, never "the other value".
FILE_SHAPES = {
    "components.json": _obj(
        packages=_map_of(_obj(channel=_one_of(*CHANNELS))),
        components=_list_of(_obj(id=_ID, effort=_INT, roles=_list_of(_STR), phase=_one_of(*MAP_PHASES),
                                 package=_STR))),
    "shipping-sets.json": _obj(packages=_map_of(_obj(components=_map_of(_ANY)))),
    "scan-<date>.json": _obj(components=_map_of(_obj(findings=_list_of(_obj(id=_STR))))),
    "experiment-tier-a.json": _obj(components=_map_of(_obj(
        exercised=_BOOL, operation_ok=_BOOL, scenario=_null_or(_STR),
        pass_conditions=_map_of(_one_of(*PASS_VALUES))))),
    "inventory.json": _obj(recall=_obj(), rows=_list_of(_ANY)),
}


def _violations(shape, v, at):
    """Every place `v` departs from `shape`, as (where, why). It recurses on the SHAPE, never on the data, so its
    depth is the shape's; and it prints a value only through `_show`."""
    kind, want, arg = shape
    if kind == "is":
        if not arg(v):
            yield at, f"is {_show(v)}, not {want}"
    elif kind == "null_or":
        if v is not None:
            yield from _violations(arg, v, at)
    elif kind == "list":
        item, least = arg
        if not isinstance(v, list) or len(v) < least:
            yield at, f"is {_show(v)}, not {want}"
        else:
            for i, x in enumerate(v):
                yield from _violations(item, x, f"{at}[{i}]")
    elif kind == "map":
        if not isinstance(v, dict):
            yield at, f"is {_show(v)}, not {want}"
        else:
            for k, x in v.items():
                yield from _violations(arg, x, f"{at}[{_show(k)}]")
    elif kind == "obj":
        if not isinstance(v, dict):
            yield at, f"is {_show(v)}, not {want}"
        else:
            for k, s in arg.items():
                if k not in v:
                    yield f"{at}.{k}", f"is missing; it must be {s[1]}"
                else:
                    yield from _violations(s, v[k], f"{at}.{k}")
    else:
        raise AssertionError(f"no such shape kind: {kind}")


def _reference_errors(cmap, scan, scan_name):
    """The three input rules a shape cannot state, because each relates two places (r1 CODEX X1, r3 CLAUDE C2)."""
    seen = set()
    for c in cmap["components"]:
        if c["id"] in seen:
            yield f"components.json has two components with the id {_show(c['id'])}"
        seen.add(c["id"])
        if c["package"] not in cmap["packages"]:
            yield (f"components.json's {_show(c['id'])} names package {_show(c['package'])}, which `packages` does "
                   "not have")
        if c["id"] not in scan["components"]:
            yield f"{scan_name} has no entry for component {_show(c['id'])} in components.json"


def load(root):
    """Every input, or CannotRun naming the first one that is absent, unreadable or of the wrong shape."""
    root = Path(root)
    mkt = root / MKT
    inventory = _read_json(mkt / "inventory.json")
    cmap = _read_json(mkt / "components.json")
    sets = _read_json(mkt / "shipping-sets.json")
    scans = sorted(mkt.glob("scan-*.json"))
    if not scans:
        raise CannotRun(f"no scan-<date>.json under {mkt}")
    scan = _read_json(scans[-1])
    side = _read_json(mkt / "experiment-tier-a.json")
    spec_text = _read_text(root / SPEC)
    practices = _read_text(root / PRACTICES)
    for name, doc in (("inventory.json", inventory), ("components.json", cmap), ("shipping-sets.json", sets),
                      (scans[-1].name, scan), ("experiment-tier-a.json", side)):
        shape = FILE_SHAPES["scan-<date>.json" if doc is scan else name]
        for where, why in _violations(shape, doc, ""):
            raise CannotRun(f"{name}: {where or 'the document'} {why}")
    for why in _reference_errors(cmap, scan, scans[-1].name):
        raise CannotRun(why)
    headings = frozenset(line[3:].rstrip("\n") for line in practices.splitlines() if line.startswith("## "))
    if not headings:
        raise CannotRun(f"{PRACTICES} has no `## ` heading")
    if "## " not in spec_text:
        raise CannotRun(f"{SPEC} has no `## ` heading")
    ctx = Context(components={c.get("id"): c for c in cmap["components"]},
                  channels={k: v["channel"] for k, v in cmap["packages"].items()},
                  shipping={k: set(v["components"]) for k, v in sets["packages"].items()},
                  practice_headings=headings, recall=inventory.get("recall"))
    return inventory, ctx, scan["components"], side["components"], spec_text, f"{MKT}/{scans[-1].name}"


def main(argv=None):
    """`_main`, behind the soundness net: an exception no rule anticipated is rc 2 and NOT RUN, never Python's own
    exit 1 (which is this guard's code for "row errors"). The message does not start `CANNOT RUN: `, so a case that
    asserts a NAMED refusal cannot be satisfied by the net."""
    for stream in (sys.stdout, sys.stderr):     # a string no encoder accepts is printed escaped, never raised
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    try:
        return _main(argv)
    except Exception as e:      # noqa: BLE001 — the net; rc 2, never success
        where = e.__traceback__
        while where.tb_next is not None:
            where = where.tb_next
        site = f"{Path(where.tb_frame.f_code.co_filename).name}:{where.tb_lineno}"     # the innermost frame
        print(f"INTERNAL ERROR: check-inventory.py raised {type(e).__name__} at {site}; this is a defect in the "
              "guard, not a verdict on the inventory — treat this check as NOT RUN.")
        # ⚠ The words "CANNOT RUN" are deliberately ABSENT: nine older cases assert `"CANNOT RUN" in` the output for
        # a refusal the GUARD must make, and the net saying them too satisfied those cases with a crash (measured:
        # the mutation "a non-object finding is accepted" survived its case through the net).
        return 2


def _main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv == ["--self-test"]:
        return _self_test()
    root, render_md = REPO, False
    rest = list(argv)
    while rest:
        a = rest.pop(0)
        if a == "--render":
            render_md = True
        elif a == "--root" and rest:
            root = Path(rest.pop(0))
        else:
            print("usage: check-inventory.py [--root DIR] [--render] | --self-test", file=sys.stderr)
            return 2
    try:
        inventory, ctx, scan, side, spec_text, latest = load(root)
    except CannotRun as e:
        print(f"CANNOT RUN: {e}. Treat this check as NOT RUN.")
        return 2
    rows = inventory["rows"]
    errors = inventory_errors(inventory, ctx, latest)
    for r in rows:
        errors += row_errors(r, scan, spec_text, side, ctx=ctx)
    status = sys.stderr if render_md else sys.stdout
    if errors:
        for e in errors:
            print(e, file=status)
        print(f"FAIL: {len(errors)} inventory error(s) over {len(rows)} rows; the D1 checkpoint was NOT computed",
              file=status)
        return 1
    try:
        fired = checkpoint_fires(rows)
    except ValueError as e:
        print(f"{e}. Treat the D1 checkpoint as NOT RUN.", file=status)
        return 2
    if render_md:
        print(render(rows), end="")
    if fired:
        print(f"CHECKPOINT: the D1 checkpoint FIRED over {sum(r['phase'] == '1' for r in rows)} phase-1 rows "
              "(public bar >= 3x next project for more than half). Stop: Human step H4.", file=status)
        return 3
    print(f"OK: {len(rows)} rows, 0 errors; the D1 checkpoint did not fire", file=status)
    return 0


def _self_test():
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _plan_asserts():
    """The plan's checkpoint asserts (Task 19), run as written."""
    def _row(phase, pub, nxt):
        return {"phase": phase, "cost": {"public_bar_hours": pub, "next_project_hours": nxt}}

    def _raises(rows):
        try:
            checkpoint_fires(rows)
        except ValueError:
            return True
        return False

    C3 = [_row("1", 3, 1), _row("1", 3, 1), _row("1", 1, 1)]                          # 2 of 3 at exactly 3x
    assert checkpoint_fires(C3)
    assert not checkpoint_fires([_row("1", 3, 1), _row("1", 1, 1)])                    # 1 of 2 is not MORE than half
    assert not checkpoint_fires([_row("1", 2.9, 1), _row("1", 2.9, 1)])                # below 3x
    assert checkpoint_fires([_row("1", 9, 1), _row("later", 1, 1), _row("later", 1, 1)])  # later rows do not count
    assert _raises([_row("later", 9, 1)])                                              # empty phase 1 is not "did not fire"
    # r1 CODEX 2: recall moved to "later" (D11 failed) cannot suppress the checkpoint.
    assert checkpoint_fires(C3 + [_row("later", 1, 1)] * 4)
    # r2 CLAUDE M3: a stray "1-if-feasible" row is never counted (row_errors refuses it first), so it cannot
    # suppress the checkpoint either — and it never makes the checkpoint refuse.
    assert checkpoint_fires(C3 + [_row("1-if-feasible", 1, 1)] * 4)
    # r1 CLAUDE m2: next_project_hours = 0 never fires automatically.
    assert _raises([_row("1", 1, 0)])
    assert _raises([_row("1", 0, 0)])
    return True


def _self_test_body():
    ok = fail = 0

    def case(name, got_fn, want):
        nonlocal ok, fail
        try:
            got = got_fn()
        except Exception as e:      # a crash is a red case, named, never a pass
            got = f"RAISED {type(e).__name__}: {e}"
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {name}: got {got!r} want {want!r}")

    # ── the fixture world ────────────────────────────────────────────────────────────────────────────────────
    components = {
        "ep": {"id": "ep", "effort": 3, "roles": ["entry-point"], "phase": "1", "package": "comp"},
        "ep2": {"id": "ep2", "effort": 3, "roles": ["entry-point"], "phase": "1", "package": "comp"},
        "lib": {"id": "lib", "effort": 3, "roles": ["library"], "phase": "1", "package": "comp"},
        "dat": {"id": "dat", "effort": 3, "roles": ["data"], "phase": "1", "package": "comp"},
        "rec": {"id": "rec", "effort": 1, "roles": ["entry-point"], "phase": "1-if-feasible", "package": "recall"},
        "memory-corpus": {"id": "memory-corpus", "effort": 1, "roles": ["data"], "phase": "1-if-feasible",
                          "package": "recall"},
        "ci": {"id": "ci", "effort": 2, "roles": ["entry-point"], "phase": "later", "package": "ci-layer"},
    }
    channels = {"comp": "plugin", "recall": "plugin", "ci-layer": "reusable-workflow"}
    shipping = {"comp": {"ep", "ep2", "lib", "dat"}, "recall": {"rec", "memory-corpus"}, "ci-layer": {"ci"}}
    headings = frozenset({"10. A thing — first ask", "How an entry earns a place here"})

    def mkctx(**over):
        kw = dict(components=components, channels=channels, shipping=shipping, practice_headings=headings,
                  recall={"a": False, "b": "unanswered"})
        kw.update(over)
        return Context(**kw)

    scan = {"ep": {"findings": [{"id": "ep:2:1"}], "mentions": [{"term": "x"}]},
            "ep2": {"findings": [{"id": "ep2:3:1"}, {"id": "ep2:3:2"}]},
            "lib": {"findings": []}, "dat": {"findings": []}}
    sidecar = {
        "ep": {"exercised": True, "scenario": "A-ep", "operation_ok": True,
               "pass_conditions": {"1": "pass", "2": "argued", "3": "pass"}},
        "ep2": {"exercised": True, "scenario": "A-ep2", "operation_ok": False,
                "pass_conditions": {"1": "fail", "2": "pass"}},
        "lib": {"exercised": False, "scenario": None, "operation_ok": False, "pass_conditions": {"1": "argued"}},
    }
    spec = "\n".join([
        "# Spec", "## 2. Decisions of record", "| **D1** | Audience |", "| **D2** | Decomposition |",
        "## 2b. The walkthrough", "### D1 becomes a working target", "### D10. Every component records a route",
        "## 2c. Owner approval", "| **D7** | Licence |", "### Kept apart",
        "## 3. Scope", "### Effort (3) — comprehensibility", "### Effort (2) — development velocity",
        "## 4. The criteria", "### The role table", ""])

    def crit(**over):
        c = {"C1": "pass", "C2": "pass", "C3": "pass", "C4": "pass", "C5": "pass"}
        c.update(over)
        return c

    def cost(pub=6.0, nxt=2.0):
        return {"public_bar_hours": pub, "next_project_hours": nxt, "grade": "argued"}

    base = {
        "ship-ep": {"id": "ep", "effort": 3, "roles": ["entry-point"], "phase": "1", "verdict": "SHIP",
                    "grade": "measured", "scenario": "A-ep", "rests_on": [], "harvest": "none",
                    "practice_entry": None, "criteria": crit(), "cost": cost(), "route": None},
        "nw": {"id": "ep2", "effort": 3, "roles": ["entry-point"], "phase": "1", "verdict": "NEEDS-WORK",
               "grade": "argued", "scenario": "A-ep2", "rests_on": [{"kind": "finding", "ids": ["ep2:3:1"]}],
               "harvest": "none", "practice_entry": None, "criteria": crit(C3="fail"), "cost": cost(),
               "route": {"kind": "decouple-config", "cost_hours": 4.0, "grade": "argued"}},
        "ship-lib": {"id": "lib", "effort": 3, "roles": ["library"], "phase": "1", "verdict": "SHIP",
                     "grade": "inherited", "scenario": "ep: the A-ep scenario", "rests_on": [], "harvest": "none",
                     "practice_entry": None, "criteria": crit(), "cost": cost(), "route": None},
        "data": {"id": "dat", "effort": 3, "roles": ["data"], "phase": "1", "verdict": "DON'T-SHIP",
                 "grade": "argued", "scenario": None,
                 "rests_on": [{"kind": "spec", "section": "3", "heading": "Effort (2) — development velocity"}],
                 "harvest": "practice", "practice_entry": "10. A thing — first ask",
                 "criteria": crit(C3="fail", C4="struck"), "cost": cost(),
                 "route": {"kind": "practice", "cost_hours": 1.0, "grade": "argued"}},
        "rec": {"id": "rec", "effort": 1, "roles": ["entry-point"], "phase": "later", "verdict": "NEEDS-WORK",
                "grade": "argued", "scenario": None, "rests_on": [{"kind": "spec", "decision": "D1"}],
                "harvest": "none", "practice_entry": None, "criteria": crit(C4="fail"), "cost": cost(),
                "route": {"kind": "template-repository", "cost_hours": 1.0, "grade": "argued"}},
        "corpus": {"id": "memory-corpus", "effort": 1, "roles": ["data"], "phase": "later", "verdict": "NEEDS-WORK",
                   "grade": "argued", "scenario": None, "rests_on": [{"kind": "c5"}], "harvest": "none",
                   "practice_entry": None, "criteria": crit(C4="struck", C5="unanswered"), "cost": cost(),
                   "route": {"kind": "portable-core", "cost_hours": 2.0, "grade": "argued"}},
        "ci": {"id": "ci", "effort": 2, "roles": ["entry-point"], "phase": "later", "verdict": "SHIP",
               "grade": "argued", "scenario": None, "rests_on": [], "harvest": "none", "practice_entry": None,
               "criteria": crit(), "cost": cost(), "route": None},
    }

    def row(name, **over):
        r = copy.deepcopy(base[name])
        for k, v in over.items():
            if v is _DROP:
                r.pop(k, None)
            else:
                r[k] = v
        return r

    def rules(r, side=None, ctx=None):
        errs = row_errors(r, scan, spec, sidecar if side is None else side, ctx=ctx or mkctx())
        return sorted({re.search(r"\[([a-z0-9-]+)\]", e).group(1) for e in errs})

    # ── every base row is clean (the adjacent negative for every rule below) ─────────────────────────────────
    for name in base:
        case(f"the base row {name} is clean", lambda n=name: rules(row(n)), [])

    # [shape] (r1 fold, X2/C1/C2/C3): every field of the plan's row schema, before any rule. Each case breaks ONE
    # field of a base row that is otherwise clean (the base rows above are the adjacent negatives).
    nan, inf = float("nan"), float("inf")
    case("a row that is not an object is a shape error, never a traceback", lambda: rules(42), ["shape"])
    case("a row that is a list is a shape error", lambda: rules([row("nw")]), ["shape"])
    case("a row with no id is a shape error", lambda: rules(row("nw", id=_DROP)), ["shape"])
    case("a row whose id is empty is a shape error", lambda: rules(row("nw", id=" ")), ["shape"])
    case("a row whose id is a list is a shape error, never a traceback", lambda: rules(row("nw", id=["ep2"])),
         ["shape"])
    case("a row with no effort is a shape error", lambda: rules(row("nw", effort=_DROP)), ["shape"])
    case("an effort that is a string is a shape error", lambda: rules(row("nw", effort="3")), ["shape"])
    case("an effort that is a boolean is a shape error", lambda: rules(row("nw", effort=True)), ["shape"])
    case("a row with no roles is a shape error", lambda: rules(row("nw", roles=_DROP)), ["shape"])
    case("an empty roles list is a shape error", lambda: rules(row("nw", roles=[])), ["shape"])
    case("roles given as a bare string is a shape error", lambda: rules(row("nw", roles="entry-point")), ["shape"])
    case("a role outside the vocabulary is a shape error", lambda: rules(row("nw", roles=["Entry-point"])), ["shape"])
    case("a row with no scenario key is a shape error", lambda: rules(row("nw", scenario=_DROP)), ["shape"])
    case("a scenario that is a list is a shape error", lambda: rules(row("nw", scenario=["A-ep2"])), ["shape"])
    case("a rests_on that is a string is a shape error", lambda: rules(row("nw", rests_on="finding")), ["shape"])
    case("a SHIP row with no rests_on key is a shape error", lambda: rules(row("ship-ep", rests_on=_DROP)), ["shape"])
    case("a row with no harvest is a shape error", lambda: rules(row("nw", harvest=_DROP)), ["shape"])
    case("a harvest outside practice/none is a shape error", lambda: rules(row("nw", harvest="bogus")), ["shape"])
    case("harvest `Practice` (wrong case) with a nonsense entry is a shape error, not an escape from [practice]",
         lambda: rules(row("data", harvest="Practice", practice_entry="nonsense")), ["shape"])
    case("a row with no practice_entry key is a shape error", lambda: rules(row("nw", practice_entry=_DROP)),
         ["shape"])
    case("a practice_entry that is a list is a shape error, never a traceback",
         lambda: rules(row("data", practice_entry=["10. A thing — first ask"])), ["shape"])
    case("a row with no criteria is a shape error", lambda: rules(row("nw", criteria=_DROP)), ["shape"])
    case("criteria given as a list is a shape error", lambda: rules(row("nw", criteria=["pass"] * 5)), ["shape"])
    case("criteria missing C5 is a shape error (the memory-corpus SHIP cannot skip its content review)",
         lambda: rules(row("corpus", verdict="SHIP", rests_on=[],
                           criteria={k: v for k, v in crit(C4="struck").items() if k != "C5"})), ["shape"])
    case("criteria with a key outside C1-C5 is a shape error",
         lambda: rules(row("nw", criteria={**crit(C3="fail"), "C6": "pass"})), ["shape"])
    case("a criterion value outside the vocabulary is a shape error",
         lambda: rules(row("nw", criteria=crit(C3="fail", C1="bogus"))), ["shape"])
    case("every criterion value in the vocabulary is clean",
         lambda: rules(row("nw", criteria=crit(C1="struck", C2="unanswered", C3="fail"))), [])
    case("a cost that is not an object is a shape error", lambda: rules(row("nw", cost=[6.0, 2.0])), ["shape"])
    case("a NaN public_bar_hours is a shape error (it would read as not over 3x)",
         lambda: rules(row("nw", cost=cost(pub=nan))), ["shape"])
    case("an infinite public_bar_hours is a shape error", lambda: rules(row("nw", cost=cost(pub=inf))), ["shape"])
    case("a negative public_bar_hours is a shape error", lambda: rules(row("nw", cost=cost(pub=-9.0))), ["shape"])
    case("a public_bar_hours of 0 is a shape error", lambda: rules(row("nw", cost=cost(pub=0))), ["shape"])
    case("a public_bar_hours of 0.5 is clean", lambda: rules(row("nw", cost=cost(pub=0.5))), [])
    case("an integer public_bar_hours is clean", lambda: rules(row("nw", cost=cost(pub=6))), [])
    case("an infinite next_project_hours is a shape error (it would suppress the checkpoint)",
         lambda: rules(row("nw", cost=cost(nxt=inf))), ["shape"])
    case("a NaN next_project_hours is a shape error", lambda: rules(row("nw", cost=cost(nxt=nan))), ["shape"])
    case("a boolean next_project_hours is a shape error", lambda: rules(row("nw", cost=cost(nxt=True))), ["shape"])
    case("a cost with no grade is a shape error",
         lambda: rules(row("nw", cost={"public_bar_hours": 6.0, "next_project_hours": 2.0})), ["shape"])
    case("a cost grade outside the vocabulary is a shape error",
         lambda: rules(row("nw", cost={**cost(), "grade": "guessed"})), ["shape"])
    case("a row with no route key is a shape error", lambda: rules(row("ship-ep", route=_DROP)), ["shape"])
    case("a route kind that is a list is a shape error, never a traceback",
         lambda: rules(row("nw", route={"kind": ["practice"], "cost_hours": 1.0, "grade": "argued"})), ["shape"])
    case("a route with no cost_hours is a shape error",
         lambda: rules(row("nw", route={"kind": "decouple-config", "grade": "argued"})), ["shape"])
    case("an infinite route cost_hours is a shape error",
         lambda: rules(row("nw", route={"kind": "decouple-config", "cost_hours": inf, "grade": "argued"})), ["shape"])
    case("a route cost_hours of 0 is a shape error",
         lambda: rules(row("nw", route={"kind": "decouple-config", "cost_hours": 0, "grade": "argued"})), ["shape"])
    case("a route with no grade is a shape error",
         lambda: rules(row("nw", route={"kind": "decouple-config", "cost_hours": 4.0})), ["shape"])
    case("a route grade outside the vocabulary is a shape error",
         lambda: rules(row("nw", route={"kind": "decouple-config", "cost_hours": 4.0, "grade": "guessed"})),
         ["shape"])
    case("a route carrying extra keys (channel, uses) is clean",
         lambda: rules(row("nw", route={"kind": "portable-core", "channel": "reusable-workflow", "uses": "x@y",
                                        "cost_hours": 12.0, "grade": "argued"})), [])
    case("a row carrying an extra key (notes) is clean", lambda: rules(row("nw", notes="why")), [])
    case("a data row with no criteria reports ONLY [shape] (the rules never see a malformed row)",
         lambda: row_errors(row("data", criteria=_DROP), scan, spec, sidecar, ctx=mkctx())[0].split(" ", 2)[:2]
         + [len(row_errors(row("data", criteria=_DROP), scan, spec, sidecar, ctx=mkctx()))], ["dat:", "[shape]", 1])
    case("a shape error names the row by its id", lambda: row_errors(row("nw", grade=_DROP), scan, spec, sidecar,
                                                                     ctx=mkctx())[0].split(" ")[:2], ["ep2:", "[shape]"])
    case("a non-object row is named `?`", lambda: row_errors(42, scan, spec, sidecar, ctx=mkctx())[0].split(" ")[:2],
         ["?:", "[shape]"])

    # grade (refused by [shape] since the r1 fold)
    case("a NEEDS-WORK row with no grade is an error", lambda: rules(row("nw", grade=_DROP)), ["shape"])
    case("the same NEEDS-WORK row graded is clean", lambda: rules(row("nw", grade="argued")), [])
    case("a SHIP row with no grade is an error", lambda: rules(row("ship-ep", grade=None)), ["shape"])
    case("a grade outside the vocabulary is an error", lambda: rules(row("nw", grade="proven")), ["shape"])
    case("the grade `none` is a grade", lambda: rules(row("nw", grade="none")), [])
    # verdict (refused by [shape] since the r1 fold)
    case("a verdict outside the vocabulary is an error",
         lambda: rules(row("nw", verdict="Needs-Work")), ["shape"])
    # [map]
    case("a row whose roles differ from the map is an error (a relabelled data row escapes no rule)",
         lambda: rules(row("ship-ep", roles=["data"], criteria=crit(C4="struck"))), ["map"])
    case("a row whose effort differs from the map is an error", lambda: rules(row("nw", effort=2)), ["map"])
    case("a row for a component not in the map is an error",
         lambda: rules(row("nw", id="ghost", rests_on=[{"kind": "c5"}], criteria=crit(C3="fail", C5="unanswered"))),
         ["map"])
    # [ship-experiment] — entry-point
    case("a SHIP row whose tier-A entry is exercised: false is an error",
         lambda: rules(row("ship-ep"), side={**sidecar, "ep": {**sidecar["ep"], "exercised": False}}),
         ["ship-experiment"])
    case("the same SHIP row with exercised: true, operation_ok: true is clean",
         lambda: rules(row("ship-ep"), side={**sidecar, "ep": {**sidecar["ep"], "exercised": True,
                                                               "operation_ok": True}}), [])
    case("a SHIP entry-point whose operation_ok is false is an error",
         lambda: rules(row("ship-ep"), side={**sidecar, "ep": {**sidecar["ep"], "operation_ok": False}}),
         ["ship-experiment"])
    case("a SHIP entry-point with a pass condition `fail` is an error",
         lambda: rules(row("ship-ep"), side={**sidecar, "ep": {**sidecar["ep"],
                                                               "pass_conditions": {"1": "pass", "2": "fail"}}}),
         ["ship-experiment"])
    case("a SHIP entry-point with a pass condition `CANNOT RUN` is an error",
         lambda: rules(row("ship-ep"), side={**sidecar, "ep": {**sidecar["ep"],
                                                               "pass_conditions": {"1": "CANNOT RUN"}}}),
         ["ship-experiment"])
    case("a SHIP entry-point whose entry has no pass conditions is an error",
         lambda: rules(row("ship-ep"), side={**sidecar, "ep": {**sidecar["ep"], "pass_conditions": {}}}),
         ["ship-experiment"])
    case("a SHIP entry-point with no tier-A entry is an error",
         lambda: rules(row("ship-ep"), side={k: v for k, v in sidecar.items() if k != "ep"}), ["ship-experiment"])
    # [ship-experiment] — library
    case("a SHIP library row with no sidecar entry of its own, whose scenario names a passing entry-point, is clean",
         lambda: rules(row("ship-lib"), side={k: v for k, v in sidecar.items() if k != "lib"}), [])
    case("the same SHIP library row naming a failing entry-point is an error",
         lambda: rules(row("ship-lib", scenario="ep2: the A-ep2 scenario"),
                       side={k: v for k, v in sidecar.items() if k != "lib"}), ["ship-experiment"])
    case("a SHIP library whose scenario names no component id is an error",
         lambda: rules(row("ship-lib", scenario="the brief page, end to end")), ["ship-experiment"])
    case("a SHIP library whose scenario names a library with a passing entry, not an entry-point, is an error",
         lambda: rules(row("ship-lib", scenario="lib: itself"), side={**sidecar, "lib": sidecar["ep"]}),
         ["ship-experiment"])
    case("a SHIP library is not held to its own exercised: false entry",
         lambda: rules(row("ship-lib")), [])
    # r1 fold (CLAUDE C4): the named entry-point must be in the library's OWN package (§4: C4 is inherited from the
    # entry-point that uses the library).
    case("a SHIP library naming a passing entry-point of ANOTHER package is an error",
         lambda: rules(row("ship-lib", scenario="rec: the recall scenario"), side={**sidecar, "rec": sidecar["ep"]}),
         ["ship-experiment"])
    case("the same SHIP library naming that entry-point, moved into the library's package, is clean",
         lambda: rules(row("ship-lib", scenario="rec: the recall scenario"), side={**sidecar, "rec": sidecar["ep"]},
                       ctx=mkctx(components={**components, "rec": {**components["rec"], "package": "comp"}})), [])
    # [ship-experiment] — outside the rule
    case("a SHIP data row in a plugin package is outside the experiment rule",
         lambda: rules(row("data", verdict="SHIP", rests_on=[], route=None, harvest="none", practice_entry=None)),
         [])
    case("a SHIP entry-point in a non-plugin package is outside the experiment rule",
         lambda: rules(row("ci")), [])
    case("the same SHIP entry-point, its package a plugin, is an error",
         lambda: rules(row("ci"), ctx=mkctx(channels={**channels, "ci-layer": "plugin"})), ["ship-experiment"])
    case("a NEEDS-WORK entry-point with no tier-A entry is outside the experiment rule",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "decision": "D2"}]),
                       side={k: v for k, v in sidecar.items() if k != "ep2"}), [])
    # [shipping-set]
    case("a phase-1 row absent from its package's shipping set is an error",
         lambda: rules(row("nw"), ctx=mkctx(shipping={**shipping, "comp": {"ep", "lib", "dat"}})), ["shipping-set"])
    case("the same row at phase later, absent from the set, is clean",
         lambda: rules(row("nw", phase="later"), ctx=mkctx(shipping={**shipping, "comp": {"ep", "lib", "dat"}})),
         [])
    case("a phase-1 row whose package has no shipping-sets entry is an error",
         lambda: rules(row("nw"), ctx=mkctx(shipping={k: v for k, v in shipping.items() if k != "comp"})),
         ["shipping-set"])
    # phase (refused by [shape] since the r1 fold)
    case("a row at the map's 1-if-feasible label is an error",
         lambda: rules(row("rec", phase="1-if-feasible")), ["shape"])
    case("a row with no phase is an error", lambda: rules(row("nw", phase=_DROP)), ["shape"])
    # [recall-phase]
    case("a recall row at phase 1 while recall.a is false is an error",
         lambda: rules(row("rec", phase="1")), ["recall-phase"])
    case("the same recall row at phase 1 with recall.a true and recall.b pass is clean",
         lambda: rules(row("rec", phase="1"), ctx=mkctx(recall={"a": True, "b": "pass"})), [])
    case("a recall row at phase 1 with recall.a true and recall.b unanswered is an error",
         lambda: rules(row("rec", phase="1"), ctx=mkctx(recall={"a": True, "b": "unanswered"})), ["recall-phase"])
    case("a recall row at phase 1 with recall.a the string \"true\" is an error",
         lambda: rules(row("rec", phase="1"), ctx=mkctx(recall={"a": "true", "b": "pass"})), ["recall-phase"])
    case("a non-recall row at phase 1 is not held to the recall answers",
         lambda: rules(row("nw"), ctx=mkctx(recall={"a": False, "b": "fail"})), [])
    # cost (refused by [shape] since the r1 fold) / [next-project]
    case("a cost with no public_bar_hours is an error",
         lambda: rules(row("nw", cost={"next_project_hours": 2.0, "grade": "argued"})), ["shape"])
    case("a cost with no next_project_hours is an error",
         lambda: rules(row("nw", cost={"public_bar_hours": 2.0, "grade": "argued"})), ["shape"])
    case("a row with no cost is an error", lambda: rules(row("nw", cost=None)), ["shape"])
    case("a cost estimate that is not a number is an error",
         lambda: rules(row("nw", cost=cost(pub="6"))), ["shape"])
    case("next_project_hours of 0 is an error", lambda: rules(row("nw", cost=cost(nxt=0))), ["next-project"])
    case("negative next_project_hours is an error", lambda: rules(row("nw", cost=cost(nxt=-1.0))), ["next-project"])
    case("next_project_hours of 0.5 is clean", lambda: rules(row("nw", cost=cost(nxt=0.5))), [])
    # [inherited]
    case("an inherited grade with no scenario is an error",
         lambda: rules(row("nw", grade="inherited", scenario=None)), ["inherited"])
    case("the same inherited row with a scenario is clean",
         lambda: rules(row("nw", grade="inherited", scenario="ep: A-ep")), [])
    # [rests-on]
    case("a non-SHIP row with an empty rests_on is an error", lambda: rules(row("nw", rests_on=[])), ["rests-on"])
    case("a non-SHIP row with no rests_on is an error", lambda: rules(row("nw", rests_on=_DROP)), ["shape"])
    case("a SHIP row with an empty rests_on is clean", lambda: rules(row("ship-ep", rests_on=[])), [])
    # [ground-kind]
    case("a ground of an unknown kind is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "scope"}])), ["ground-kind"])
    case("a ground with no kind is an error",
         lambda: rules(row("nw", rests_on=[{"ids": ["ep2:3:1"]}])), ["ground-kind"])
    case("an unknown ground on a SHIP row is an error too",
         lambda: rules(row("ship-ep", rests_on=[{"kind": "cites"}])), ["ground-kind"])
    # [ground-finding]
    case("a finding id that is not in the scan is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "finding", "ids": ["ep2:9:9"]}])), ["ground-finding"])
    case("a borrowed finding id from another component is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "finding", "ids": ["ep:2:1"]}])), ["ground-finding"])
    case("one borrowed id among own ids is still an error",
         lambda: rules(row("nw", rests_on=[{"kind": "finding", "ids": ["ep2:3:1", "ep:2:1"]}])), ["ground-finding"])
    case("two of the row's own finding ids are clean",
         lambda: rules(row("nw", rests_on=[{"kind": "finding", "ids": ["ep2:3:1", "ep2:3:2"]}])), [])
    case("a finding id that is an object is an error, never a traceback (r1 fold, CLAUDE C3)",
         lambda: rules(row("nw", rests_on=[{"kind": "finding", "ids": ["ep2:3:1", {"a": 1}]}])), ["ground-finding"])
    # [ground-empty] (backlog #696 f)
    case("a finding ground with empty ids is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "finding", "ids": []}])), ["ground-empty"])
    case("a finding ground with no ids key is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "finding"}])), ["ground-empty"])
    case("a finding ground whose ids is a string, not a list, is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "finding", "ids": "ep2:3:1"}])), ["ground-empty"])
    case("a spec ground with an empty section is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "section": ""}])), ["ground-empty"])
    case("a spec ground with no section and no decision is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "spec"}])), ["ground-empty"])
    case("a spec ground with an empty heading is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "section": "3", "heading": ""}])), ["ground-empty"])
    case("a spec ground with an empty decision is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "decision": ""}])), ["ground-empty"])
    case("an experiment ground with no scenario is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "experiment", "scenario": None}])), ["ground-empty"])
    case("an experiment ground with no scenario on a component whose entry has none is still an error",
         lambda: rules(row("nw", id="lib", roles=["library"], scenario="ep: x",
                           rests_on=[{"kind": "experiment", "scenario": None}])), ["ground-empty"])
    # [ground-spec]
    case("a spec section the spec does not have is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "section": "9"}])), ["ground-spec"])
    case("a spec section alone, which the spec has, is clean",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "section": "2c"}])), [])
    case("a spec heading that is not under its section is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "section": "4",
                                            "heading": "Effort (2) — development velocity"}])), ["ground-spec"])
    case("section 2 does not reach a heading under section 2b",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "section": "2",
                                            "heading": "D10. Every component records a route"}])), ["ground-spec"])
    case("the same heading under section 2b is clean",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "section": "2b",
                                            "heading": "D10. Every component records a route"}])), [])
    case("a spec heading that is only a prefix of a real one is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "section": "3", "heading": "Effort (2)"}])),
         ["ground-spec"])
    case("a decision in the §2 table is clean",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "decision": "D2"}])), [])
    case("a decision headed in §2b is clean",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "decision": "D10"}])), [])
    case("a decision only in §2c is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "decision": "D7"}])), ["ground-spec"])
    case("a decision the spec does not have is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "decision": "D99"}])), ["ground-spec"])
    case("a decision that is a prefix of a real one is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "decision": "D"}])), ["ground-spec"])
    # [ground-experiment]
    case("this component's failed experiment scenario is clean",
         lambda: rules(row("nw", rests_on=[{"kind": "experiment", "scenario": "A-ep2"}])), [])
    case("another component's experiment scenario is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "experiment", "scenario": "A-ep"}])), ["ground-experiment"])
    case("a scenario the sidecar does not have is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "experiment", "scenario": "A-nope"}])), ["ground-experiment"])
    case("this component's scenario with no pass condition `fail` is an error",
         lambda: rules(row("nw", id="ep", rests_on=[{"kind": "experiment", "scenario": "A-ep"}])),
         ["ground-experiment"])
    # [ground-c5]
    case("a c5 ground while C5 is pass is an error",
         lambda: rules(row("nw", rests_on=[{"kind": "c5"}])), ["ground-c5"])
    case("the same c5 ground while C5 is unanswered is clean",
         lambda: rules(row("nw", rests_on=[{"kind": "c5"}], criteria=crit(C3="fail", C5="unanswered"))), [])
    # [measured-finding]
    case("C3 fail graded measured with no finding ground is an error",
         lambda: rules(row("nw", grade="measured", rests_on=[{"kind": "spec", "decision": "D1"}])),
         ["measured-finding"])
    case("C2 fail graded measured with no finding ground is an error",
         lambda: rules(row("nw", grade="measured", criteria=crit(C2="fail"),
                           rests_on=[{"kind": "spec", "decision": "D1"}])), ["measured-finding"])
    case("the same C3 fail graded measured with a finding ground is clean",
         lambda: rules(row("nw", grade="measured")), [])
    case("the same C3 fail graded argued with no finding ground is clean",
         lambda: rules(row("nw", rests_on=[{"kind": "spec", "decision": "D1"}])), [])
    # [route] / route kind (backlog #696 a; refused by [shape] since the r1 fold)
    case("a non-SHIP row with no route is an error", lambda: rules(row("nw", route=None)), ["route"])
    case("a SHIP row with no route is clean", lambda: rules(row("ship-ep", route=None)), [])
    for kind in ROUTE_KINDS:
        case(f"the route kind {kind} is clean",
             lambda k=kind: rules(row("nw", route={"kind": k, "cost_hours": 1.0, "grade": "argued"})), [])
    case("a route kind outside the vocabulary is an error",
         lambda: rules(row("nw", route={"kind": "rewrite-it", "cost_hours": 1.0, "grade": "argued"})), ["shape"])
    case("a route with no kind is an error",
         lambda: rules(row("nw", route={"cost_hours": 1.0, "grade": "argued"})), ["shape"])
    case("a route that is a bare string is an error", lambda: rules(row("nw", route="practice")), ["shape"])
    case("an unknown route kind on a SHIP row is an error too",
         lambda: rules(row("ship-ep", route={"kind": "plugin", "cost_hours": 1.0, "grade": "argued"})), ["shape"])
    # [practice] (backlog #696 c)
    case("a practice_entry without its number is an error",
         lambda: rules(row("data", practice_entry="A thing — first ask")), ["practice"])
    case("a practice_entry with the `## ` prefix is an error",
         lambda: rules(row("data", practice_entry="## 10. A thing — first ask")), ["practice"])
    case("a practice harvest with no practice_entry is an error",
         lambda: rules(row("data", practice_entry=None)), ["practice"])
    case("an unnumbered heading, given exactly, is clean",
         lambda: rules(row("data", practice_entry="How an entry earns a place here")), [])
    case("no practice harvest needs no practice_entry",
         lambda: rules(row("data", harvest="none", practice_entry=None)), [])
    # [data-c4]
    case("a data row with C4 pass is an error", lambda: rules(row("data", criteria=crit(C3="fail"))), ["data-c4"])
    # [corpus-c5]
    case("the memory-corpus row SHIP while its C5 is unanswered is an error",
         lambda: rules(row("corpus", verdict="SHIP")), ["corpus-c5"])
    case("the memory-corpus row SHIP with C5 pass is clean",
         lambda: rules(row("corpus", verdict="SHIP", rests_on=[], criteria=crit(C4="struck"))), [])
    case("another data row SHIP while its C5 is unanswered is not the corpus rule",
         lambda: rules(row("data", verdict="SHIP", criteria=crit(C3="fail", C4="struck", C5="unanswered"),
                           rests_on=[])), [])
    # [measured-effort]
    case("a measured grade on an effort (1) row is an error",
         lambda: rules(row("rec", grade="measured")), ["measured-effort"])
    case("a measured grade on an effort (2) row is an error",
         lambda: rules(row("ci", grade="measured")), ["measured-effort"])
    case("a measured grade on an effort (3) row is clean", lambda: rules(row("nw", grade="measured")), [])

    # ── direct calls: each input, varied at its own call site ────────────────────────────────────────────────
    case("a finding ground against a scan with no entry for the component is an error",
         lambda: [e.split(" ")[1] for e in row_errors(row("nw"), {}, spec, sidecar, ctx=mkctx())], ["[ground-finding]"])
    case("a spec ground against a spec with no such heading is an error",
         lambda: [e.split(" ")[1] for e in row_errors(row("data"), scan, "## 3. Scope\n", sidecar, ctx=mkctx())],
         ["[ground-spec]"])
    case("a SHIP entry-point with an empty sidecar, its package not a plugin, is clean",
         lambda: row_errors(row("ship-ep"), scan, spec, {}, ctx=mkctx(channels={"comp": "reusable-workflow"})), [])
    case("an empty map and an empty inventory have only the phase-1-package error",
         lambda: inventory_errors({"rows": [], "scan": None}, mkctx(components={}), None),
         ["inventory: [phase1-package] no phase-1 package is named in components.json"])
    def bogus():
        with contextlib.redirect_stderr(io.StringIO()):
            return main(["--bogus"])
    case("an unknown argument alone exits 2", bogus, 2)

    # ── inventory level ──────────────────────────────────────────────────────────────────────────────────────
    full = [row(n) for n in base]

    def inv_rules(rows, ctx=None, scan_name="docs/marketplace/scan-2026-01-01.json"):
        errs = inventory_errors({"rows": rows, "scan": "docs/marketplace/scan-2026-01-01.json"}, ctx or mkctx(),
                                scan_name)
        return sorted({re.search(r"\[([a-z0-9-]+)\]", e).group(1) for e in errs})

    case("an inventory with a row per component is clean", lambda: inv_rules(full), [])
    case("a component in the map with no row is an error", lambda: inv_rules(full[:-1]), ["missing"])
    case("two rows for one component is an error", lambda: inv_rules(full + [row("nw")]), ["duplicate"])
    case("no phase-1 package in the map is an error",
         lambda: inv_rules(full, mkctx(components={k: {**v, "phase": "later"} for k, v in components.items()})),
         ["phase1-package"])
    case("a phase-1 package with no shipping-sets entry is an error",
         lambda: inv_rules(full, mkctx(shipping={k: v for k, v in shipping.items() if k != "comp"})),
         ["package-shipping"])
    case("an inventory naming a scan other than the latest is an error",
         lambda: inv_rules(full, scan_name="docs/marketplace/scan-2026-02-01.json"), ["scan"])
    case("a non-object row is no inventory error, never a traceback (row_errors names it)",
         lambda: inv_rules(full + [42]), [])
    case("two rows sharing an unhashable id are no inventory error, never a traceback (row_errors names them)",
         lambda: inv_rules(full + [row("nw", id=["x"]), row("nw", id=["x"])]), [])

    # ── the checkpoint ───────────────────────────────────────────────────────────────────────────────────────
    def _row(phase, pub, nxt):
        return {"phase": phase, "cost": {"public_bar_hours": pub, "next_project_hours": nxt}}

    def _raises(rows):
        try:
            checkpoint_fires(rows)
        except ValueError:
            return True
        return False

    C3 = [_row("1", 3, 1), _row("1", 3, 1), _row("1", 1, 1)]
    case("the plan's checkpoint asserts, run as written", _plan_asserts, True)
    case("two of three phase-1 rows at exactly 3x fire", lambda: checkpoint_fires(C3), True)
    case("one of two at 3x is not MORE than half", lambda: checkpoint_fires([_row("1", 3, 1), _row("1", 1, 1)]), False)
    case("two rows at 2.9x do not fire", lambda: checkpoint_fires([_row("1", 2.9, 1), _row("1", 2.9, 1)]), False)
    case("later rows do not count against a firing phase-1 row",
         lambda: checkpoint_fires([_row("1", 9, 1), _row("later", 1, 1), _row("later", 1, 1)]), True)
    case("an empty phase 1 raises, never `did not fire`", lambda: _raises([_row("later", 9, 1)]), True)
    case("recall rows moved to later cannot suppress the checkpoint",
         lambda: checkpoint_fires(C3 + [_row("later", 1, 1)] * 4), True)
    case("stray 1-if-feasible rows are never counted",
         lambda: checkpoint_fires(C3 + [_row("1-if-feasible", 1, 1)] * 4), True)
    case("next_project_hours 0 raises, never fires", lambda: _raises([_row("1", 1, 0)]), True)
    case("next_project_hours 0 with public bar 0 raises", lambda: _raises([_row("1", 0, 0)]), True)

    # ── render ───────────────────────────────────────────────────────────────────────────────────────────────
    md = render([row("ship-lib"), row("nw")])
    case("render puts verdict and grade in one cell",
         lambda: [ln.split(" | ")[3] for ln in md.splitlines()[2:]], ["SHIP · inherited", "NEEDS-WORK · argued"])
    case("render has one header, one rule and a line per row", lambda: len(md.splitlines()), 4)
    case("render escapes a pipe inside a cell",
         lambda: "a\\|b" in render([row("nw", harvest="a|b")]), True)

    # ── the CLI, end to end over a fixture tree ──────────────────────────────────────────────────────────────
    cli_components = [components[k] for k in ("ep", "ep2", "lib")]

    def tree(name, rows, *, drop=None, scans=("scan-2026-01-01.json",), inv_scan="docs/marketplace/scan-2026-01-01.json",
             scan_doc=None):
        root = Path(tempfile.mkdtemp(prefix=f"inv-{name}-"))
        mkt = root / MKT
        mkt.mkdir(parents=True)
        files = {
            "inventory.json": {"scan": inv_scan, "recall": {"a": False, "b": "unanswered"}, "rows": rows},
            "components.json": {"packages": {"comp": {"channel": "plugin"}}, "components": cli_components},
            "shipping-sets.json": {"packages": {"comp": {"components": {k: {} for k in ("ep", "ep2", "lib")}}}},
            "experiment-tier-a.json": {"components": sidecar},
        }
        for s in scans:
            files[s] = {"components": scan} if scan_doc is None else scan_doc
        for n, doc in files.items():
            if n != drop:
                (mkt / n).write_text(json.dumps(doc))
        (root / SPEC).parent.mkdir(parents=True)
        (root / SPEC).write_text(spec)
        (root / PRACTICES).write_text("# Practices\n\n## 10. A thing — first ask\n")
        return root

    def run(root, *extra):
        buf, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            rc = main(["--root", str(root), *extra])
        return rc, buf.getvalue() + err.getvalue(), buf.getvalue()

    def costed(pubs):
        return [row(n, cost=cost(pub=p, nxt=1.0)) for n, p in zip(("ship-ep", "nw", "ship-lib"), pubs)]

    case("a clean inventory below the threshold exits 0",
         lambda: (lambda r: (r[0], "did not fire" in r[1]))(run(tree("zero", costed((1.0, 1.0, 9.0))))), (0, True))
    case("a clean inventory over the threshold exits 3",
         lambda: (lambda r: (r[0], "CHECKPOINT" in r[1]))(run(tree("three", costed((9.0, 9.0, 1.0))))), (3, True))
    case("rows with an error AND a crossed threshold exit 1, not 3",
         lambda: (lambda r: (r[0], "ep2: [shape]" in r[1], "CHECKPOINT" in r[1]))(
             run(tree("one", costed((9.0, 9.0, 1.0))[:1] + [row("nw", grade=None, cost=cost(9.0, 1.0))]
                      + costed((9.0, 9.0, 1.0))[2:]))), (1, True, False))
    case("a component in the map with no row exits 1",
         lambda: (lambda r: (r[0], "[missing] component lib" in r[1]))(
             run(tree("missing", costed((1.0, 1.0, 1.0))[:2]))), (1, True))
    case("a clean inventory with no phase-1 rows exits 2",
         lambda: (lambda r: (r[0], "no phase-1 rows" in r[1]))(
             run(tree("nophase1", [{**r, "phase": "later"} for r in costed((1.0, 1.0, 1.0))]))), (2, True))
    case("an absent inventory.json exits 2, CANNOT RUN",
         lambda: (lambda r: (r[0], "CANNOT RUN" in r[1]))(run(tree("absent", [], drop="inventory.json"))), (2, True))
    case("an absent sidecar exits 2, CANNOT RUN",
         lambda: (lambda r: (r[0], "experiment-tier-a.json" in r[1]))(
             run(tree("noside", costed((1.0, 1.0, 1.0)), drop="experiment-tier-a.json"))), (2, True))
    case("no scan file exits 2, CANNOT RUN",
         lambda: (lambda r: (r[0], "no scan-<date>.json" in r[1]))(run(tree("noscan", costed((1.0, 1.0, 1.0)),
                                                                            scans=()))), (2, True))
    case("the latest scan is the one read, and an inventory naming an older one exits 1",
         lambda: (lambda r: (r[0], "[scan]" in r[1]))(
             run(tree("twoscans", costed((1.0, 1.0, 1.0)), scans=("scan-2026-01-01.json", "scan-2026-03-01.json")))),
         (1, True))
    case("--render prints the table on stdout when the inventory is clean",
         lambda: (lambda r: (r[0], r[2].splitlines()[2].split(" | ")[3]))(
             run(tree("render", costed((1.0, 1.0, 1.0))), "--render")), (0, "SHIP · measured"))
    case("--render prints no table over rows with errors",
         lambda: (lambda r: (r[0], r[2]))(run(tree("rendererr", costed((1.0, 1.0, 1.0))[:2]), "--render")), (1, ""))
    case("an unknown argument exits 2", lambda: run(tree("usage", []), "--live")[0], 2)

    # r1 fold: a non-object row, and the rows beside it (CLAUDE C3)
    case("a non-object row exits 1 with a [shape] line, and the other rows are still checked",
         lambda: (lambda r: (r[0], "?: [shape]" in r[1], "ep2: [shape]" in r[1]))(
             run(tree("nondict", costed((1.0, 1.0, 1.0))[:1] + [row("nw", grade=None, cost=cost(1.0, 1.0))]
                      + costed((1.0, 1.0, 1.0))[2:] + [42]))), (1, True, True))
    # r1 fold: JSON's NaN / Infinity / -Infinity are not numbers; the loader refuses them (CLAUDE C1)
    for const, pub, nxt in (("NaN", nan, 1.0), ("Infinity", 1.0, inf), ("-Infinity", -inf, 1.0)):
        case(f"an inventory.json holding the JSON constant {const} exits 2, CANNOT RUN",
             lambda c=const, p=pub, n=nxt: (lambda r: (r[0], "CANNOT RUN" in r[1] and c in r[1]))(
                 run(tree(f"const{c}", [row("ship-ep", cost=cost(pub=p, nxt=n))] + costed((1.0, 1.0, 1.0))[1:]))),
             (2, True))

    def big(name):
        root = tree(name, [row("ship-ep", cost=cost(pub=123456.5, nxt=1.0))] + costed((1.0, 1.0, 1.0))[1:])
        p = root / MKT / "inventory.json"
        p.write_text(p.read_text().replace("123456.5", "1e999"))
        return root
    case("a cost of 1e999 (JSON parses it as infinity) exits 1 with a [shape] error",
         lambda: (lambda r: (r[0], "ep: [shape]" in r[1]))(run(big("big"))), (1, True))
    # r1 fold: a scan with no entry for a component in the map is unreadable input (CODEX X1). The adjacent
    # negative is `a clean inventory below the threshold exits 0`, whose scan covers the map and one more.
    case("a scan with no components at all exits 2, CANNOT RUN",
         lambda: (lambda r: (r[0], "CANNOT RUN" in r[1]))(
             run(tree("scan-nocomp", costed((1.0, 1.0, 1.0)), scan_doc={}))), (2, True))
    case("an empty scan exits 2, CANNOT RUN",
         lambda: (lambda r: (r[0], "CANNOT RUN" in r[1]))(
             run(tree("scan-empty", costed((1.0, 1.0, 1.0)), scan_doc={"components": {}}))), (2, True))
    case("a scan with no entry for one component in the map exits 2, CANNOT RUN, naming it",
         lambda: (lambda r: (r[0], "CANNOT RUN" in r[1] and "lib" in r[1]))(
             run(tree("scan-nolib", costed((1.0, 1.0, 1.0)),
                      scan_doc={"components": {k: v for k, v in scan.items() if k != "lib"}}))), (2, True))
    case("a scan entry whose findings is an object, not a list, exits 2, CANNOT RUN",
         lambda: (lambda r: (r[0], "CANNOT RUN" in r[1]))(
             run(tree("scan-findstr", costed((1.0, 1.0, 1.0)),
                      scan_doc={"components": {**scan, "lib": {"findings": {}}}}))), (2, True))
    case("a scan entry whose findings holds a non-object exits 2, CANNOT RUN",
         lambda: (lambda r: (r[0], "CANNOT RUN" in r[1]))(
             run(tree("scan-find42", costed((1.0, 1.0, 1.0)),
                      scan_doc={"components": {**scan, "lib": {"findings": [42]}}}))), (2, True))

    # ── r2 fold ──────────────────────────────────────────────────────────────────────────────────────────────
    # CODEX X1, and its class check over every numeric field of ROW_SCHEMA: an integer past the float range is
    # refused as a [shape] error, never an OverflowError. The adjacent negatives: an integer the float range holds.
    huge = 10 ** 400
    for field, where in (("public_bar_hours", "cost"), ("next_project_hours", "cost"), ("cost_hours", "route")):
        for sign in (1, -1):
            r = row("nw")
            r[where][field] = sign * huge
            case(f"a {where}.{field} of {'-' if sign < 0 else ''}10**400 is a shape error, never an OverflowError",
                 lambda r=r: rules(r), ["shape"])
        r = row("nw")
        r[where][field] = 10 ** 300
        case(f"a {where}.{field} of 10**300 (an integer a float holds) is no shape error", lambda r=r: rules(r), [])
    case("an effort of 10**400 is a [map] error (an integer, unlike the map's), never a traceback",
         lambda: rules(row("nw", effort=huge)), ["map"])
    case("_finite: an integer one past the float range is not finite", lambda: _finite(int(sys.float_info.max) * 2),
         False)
    case("_finite: the largest float, as an integer, is finite", lambda: _finite(int(sys.float_info.max)), True)

    def huge_tree(name, text):
        root = tree(name, [row("ship-ep", cost=cost(pub=123456.5, nxt=1.0))] + costed((1.0, 1.0, 1.0))[1:])
        p = root / MKT / "inventory.json"
        p.write_text(p.read_text().replace("123456.5", text))
        return root
    case("an inventory.json cost of 1 followed by 400 zeros exits 1 with a [shape] error, never a traceback",
         lambda: (lambda r: (r[0], "ep: [shape]" in r[1]))(run(huge_tree("huge", "1" + "0" * 400))), (1, True))
    case("an inventory.json cost of 1 followed by 300 zeros is no error (the adjacent negative)",
         lambda: run(huge_tree("huge300", "1" + "0" * 300))[0], 0)

    # CODEX X2, and its class check over every field of the map, the shipping sets, the scan, the sidecar and the
    # inventory that a rule reads: a wrong-typed one is CANNOT RUN (rc 2), never a traceback. Each case breaks ONE
    # field of the clean CLI tree; its adjacent negative keeps the field's type and changes its value.
    def edited(name, fname, fn, *more):
        """rc, and whether main printed its CANNOT RUN line, over the clean CLI tree with `fn` applied to `fname`'s
        JSON (and each further (fname, fn) pair in `more`)."""
        root = tree(name, costed((1.0, 1.0, 1.0)))
        for f, g in ((fname, fn),) + more:
            p = root / MKT / f
            doc = json.loads(p.read_text())
            g(doc)
            p.write_text(json.dumps(doc))
        r = run(root)
        return r[0], "CANNOT RUN: " in r[1]

    def at(*path, value=None, drop=False):
        def fn(doc):
            for k in path[:-1]:
                doc = doc[k]
            if drop:
                del doc[path[-1]]
            else:
                doc[path[-1]] = value
        return fn

    SC = "scan-2026-01-01.json"
    bad_inputs = (
        ("a component that is not an object", "components.json", at("components", 0, value=42)),
        ("a component id that is a list", "components.json", at("components", 0, "id", value=["ep"])),
        ("a component id that is blank, with a scan entry under that blank id", "components.json",
         at("components", 0, "id", value=" "), (SC, at("components", " ", value={"findings": []}))),
        ("a component with no id", "components.json", at("components", 0, "id", drop=True)),
        ("a component effort that is a string", "components.json", at("components", 0, "effort", value="3")),
        ("a component effort that is a boolean", "components.json", at("components", 0, "effort", value=True)),
        ("component roles that are a boolean", "components.json", at("components", 0, "roles", value=True)),
        ("component roles holding a non-string", "components.json", at("components", 0, "roles", value=[1])),
        ("a component phase that is a list", "components.json", at("components", 0, "phase", value=["1"])),
        ("a component package that is a list", "components.json", at("components", 0, "package", value=["comp"])),
        ("a map package that is not an object", "components.json", at("packages", "comp", value=True)),
        ("a map package channel that is a list", "components.json", at("packages", "comp", "channel", value=[])),
        ("a shipping-set package that is not an object", "shipping-sets.json", at("packages", "comp", value=True)),
        ("a shipping-set package whose components is a boolean", "shipping-sets.json",
         at("packages", "comp", "components", value=True)),
        ("a scan finding whose id is a list (CODEX X2)", SC, at("components", "ep", "findings", 0, "id", value=[])),
        ("a scan finding with no id", SC, at("components", "ep", "findings", 0, "id", drop=True)),
        ("a scan entry outside the map that is not an object", SC, at("components", "zz", value=True)),
        ("a scan entry outside the map whose finding id is a list", SC,
         at("components", "zz", value={"findings": [{"id": []}]})),
        ("a sidecar entry that is not an object", "experiment-tier-a.json", at("components", "ep", value=True)),
        ("a sidecar exercised that is a string", "experiment-tier-a.json",
         at("components", "ep", "exercised", value="true")),
        ("a sidecar operation_ok that is missing", "experiment-tier-a.json",
         at("components", "ep", "operation_ok", drop=True)),
        ("a sidecar scenario that is a list", "experiment-tier-a.json",
         at("components", "ep", "scenario", value=["A-ep"])),
        ("sidecar pass_conditions that are a boolean", "experiment-tier-a.json",
         at("components", "ep", "pass_conditions", value=True)),
        ("sidecar pass_conditions holding a non-string", "experiment-tier-a.json",
         at("components", "ep", "pass_conditions", "1", value=1)),
        ("an inventory recall that is a list", "inventory.json", at("recall", value=[True])),
        ("an inventory with no recall", "inventory.json", at("recall", drop=True)),
    )
    for i, (what, fname, fn, *more) in enumerate(bad_inputs):
        case(f"{what} exits 2, CANNOT RUN, never a traceback",
             lambda i=i, f=fname, fn=fn, more=more: edited(f"in{i}", f, fn, *more), (2, True))
    good_inputs = (
        ("a component effort of another integer", "components.json", at("components", 0, "effort", value=4), 1),
        ("a component phase of another string", "components.json", at("components", 0, "phase", value="later"), 0),
        ("a map package channel of another string", "components.json",
         at("packages", "comp", "channel", value="reusable-workflow"), 0),
        ("an empty shipping-set components object", "shipping-sets.json",
         at("packages", "comp", "components", value={}), 1),
        ("a scan finding with another string id", SC, at("components", "ep", "findings", 0, "id", value="ep:9:9"), 0),
        ("a scan entry outside the map that is well formed", SC, at("components", "zz", value={"findings": []}), 0),
        ("a sidecar scenario of null", "experiment-tier-a.json", at("components", "ep2", "scenario", value=None), 0),
        ("sidecar pass_conditions of another string", "experiment-tier-a.json",
         at("components", "ep2", "pass_conditions", "1", value="argued"), 0),
        ("an inventory recall with other answers", "inventory.json", at("recall", value={"a": True, "b": "pass"}), 0),
    )
    for i, (what, fname, fn, rc) in enumerate(good_inputs):
        case(f"{what} is readable input (exit {rc}, no CANNOT RUN)",
             lambda i=i, f=fname, fn=fn: edited(f"ok{i}", f, fn), (rc, False))

    # the fuzz pass (r2 fold): JSON nested past the parser's stack, and a spec or practices file that is not UTF-8,
    # are unreadable input (rc 2), never a RecursionError or UnicodeDecodeError traceback.
    def deep_tree(name):
        root = tree(name, costed((1.0, 1.0, 1.0)))
        (root / MKT / "inventory.json").write_text("[" * 200000 + "]" * 200000)
        return root
    case("an inventory.json nested 200000 deep exits 2, CANNOT RUN, never a RecursionError",
         lambda: (lambda r: (r[0], "CANNOT RUN" in r[1] and "nested too deep" in r[1]))(run(deep_tree("deep"))),
         (2, True))

    def bytes_tree(name, rel):
        root = tree(name, costed((1.0, 1.0, 1.0)))
        (root / rel).write_bytes(b"## 2. \xff\xfe not utf-8\n")
        return root
    for rel in (SPEC, PRACTICES):
        case(f"a {Path(rel).name} that is not UTF-8 exits 2, CANNOT RUN, never a UnicodeDecodeError",
             lambda rel=rel: (lambda r: (r[0], "CANNOT RUN" in r[1] and "UnicodeDecodeError" in r[1]))(
                 run(bytes_tree(f"bytes-{Path(rel).stem}", rel))), (2, True))

    # ── Phase 6 fold (architecture review 2026-11-22, backlog #699): the bounded reader, FILE_SHAPES and its two
    # vocabularies, the reference rules, total output and the net. Each case beside its adjacent negative.
    def said(name, fname, fn, *more):
        """rc, the CANNOT RUN line (or ""), and the whole output, over the clean CLI tree with `fn` applied."""
        root = tree(name, costed((1.0, 1.0, 1.0)))
        for f, g in ((fname, fn),) + more:
            p = root / MKT / f
            doc = json.loads(p.read_text())
            g(doc)
            p.write_text(json.dumps(doc))
        rc, out, _ = run(root)
        line = next((ln for ln in out.splitlines() if ln.startswith("CANNOT RUN: ")), "")
        return rc, line, out

    # a reference rule: a component whose package `packages` does not have (r3 CLAUDE C2, fail-OPEN before)
    case("a component whose package names no package is rc 2, naming it",
         lambda: (lambda r: (r[0], "names package 'nopkg'" in r[1]))(
             said("ref-pkg", "components.json", at("components", 1, "package", value="nopkg"))), (2, True))
    case("...the same map with the package present is readable (rc 0)",
         lambda: said("ref-pkg-ok", "components.json",
                      lambda d: (at("components", 1, "package", value="nopkg")(d),
                                 at("packages", "nopkg", value={"channel": "plugin"})(d)),
                      ("shipping-sets.json", at("packages", "nopkg", value={"components": {"ep2": {}}})))[:2],
         (0, ""))
    # a reference rule: two components with one id
    for what, extra in (("identical", {}), ("differing in effort", {"effort": 2})):
        case(f"two components with one id ({what}) is rc 2, naming it",
             lambda extra=extra: (lambda r: (r[0], "two components with the id 'ep'" in r[1]))(
                 said(f"ref-dup-{len(extra)}", "components.json",
                      lambda d, extra=extra: d["components"].append({**d["components"][0], **extra}))), (2, True))
    case("...a third component with a distinct id is readable (rc 1, [missing], no CANNOT RUN)",
         lambda: (lambda r: (r[0], r[1], "[missing] component ep9" in r[2]))(
             said("ref-dup-ok", "components.json", lambda d: d["components"].append({**d["components"][0], "id": "ep9"}),
                  (SC, at("components", "ep9", value={"findings": []})))), (1, "", True))
    # a reference rule: the scan covers the map (r1 CODEX X1) — its cases are under the r1 fold above.

    # the vocabularies: a typo is unreadable, never "the other value"
    case("a map channel `Plugin` is rc 2 (it would skip the SHIP rule)",
         lambda: (lambda r: (r[0], "channel" in r[1]))(
             said("voc-ch", "components.json", at("packages", "comp", "channel", value="Plugin"))), (2, True))
    case("...channel `plugin` is readable (rc 0)",
         lambda: said("voc-ch-ok", "components.json", at("packages", "comp", "channel", value="plugin"))[:2],
         (0, ""))
    for typo in ("FAIL", "failed"):
        case(f"a pass condition `{typo}` is rc 2 (it would back a SHIP)",
             lambda typo=typo: (lambda r: (r[0], "pass_conditions" in r[1]))(
                 said(f"voc-pc-{typo}", "experiment-tier-a.json",
                      at("components", "ep", "pass_conditions", "1", value=typo))), (2, True))
    case("...a pass condition `fail` is rc 1 [ship-experiment]",
         lambda: (lambda r: (r[0], r[1], "ep: [ship-experiment]" in r[2]))(
             said("voc-pc-fail", "experiment-tier-a.json", at("components", "ep", "pass_conditions", "1", value="fail"))),
         (1, "", True))
    case("...all pass conditions `pass` is rc 0",
         lambda: said("voc-pc-pass", "experiment-tier-a.json",
                      at("components", "ep", "pass_conditions", value={"1": "pass", "2": "pass"}))[:2], (0, ""))
    case("_one_of matches by TYPE: True is not 1, 1.0 is not 1, 1 is 1",
         lambda: [bool(list(_violations(_one_of(1), v, ""))) for v in (True, 1.0, 1)],
         [True, True, False])
    # the coordinator's addition to the review: a map phase outside the vocabulary (corpus P9, rc 0 under c2)
    case("a map phase `2` is rc 2, naming the phase",
         lambda: (lambda r: (r[0], ".phase" in r[1]))(
             said("voc-ph", "components.json", at("components", 0, "phase", value="2"))), (2, True))
    case("...a map phase `1-if-feasible` is readable (rc 0)",
         lambda: said("voc-ph-ok", "components.json", at("components", 0, "phase", value="1-if-feasible"))[:2],
         (0, ""))
    import importlib.util
    spec_ss = importlib.util.spec_from_file_location("check_shipping_sets",
                                                     Path(__file__).resolve().parent / "check-shipping-sets.py")
    shipping_sets = importlib.util.module_from_spec(spec_ss)
    sys.modules["check_shipping_sets"] = shipping_sets      # its dataclasses look their module up by name
    try:
        spec_ss.loader.exec_module(shipping_sets)
    finally:
        del sys.modules["check_shipping_sets"]
    case("CHANNELS equals check-shipping-sets.CHANNELS (it owns the map), by import",
         lambda: CHANNELS == shipping_sets.CHANNELS, True)
    case("MAP_PHASES equals check-shipping-sets.PHASES (it owns the map), by import",
         lambda: MAP_PHASES == shipping_sets.PHASES, True)

    # the bounded reader: a repeated key, and the depth bound
    def raw(name, fname, old, new):
        root = tree(name, costed((1.0, 1.0, 1.0)))
        p = root / MKT / fname
        text = p.read_text()
        assert old in text, (fname, old)
        p.write_text(text.replace(old, new, 1))
        rc, out, _ = run(root)
        return rc, next((ln for ln in out.splitlines() if ln.startswith("CANNOT RUN: ")), "")
    for fname, old, new, once in (
            ("components.json", '{"packages": ', '{"packages": {}, "packages": ', '{"packages_x": {}, "packages": '),
            ("inventory.json", '{"scan": ', '{"scan": "x", "scan": ', '{"scan_x": "x", "scan": ')):
        case(f"a repeated key in one object of {fname} is rc 2 (Python would keep the last, silently)",
             lambda f=fname, o=old, n=new: (lambda r: (r[0], "appears twice" in r[1]))(raw(f"dupkey-{f}", f, o, n)),
             (2, True))
        case(f"...the same object with a second, distinct key in {fname} is readable (rc 0)",
             lambda f=fname, o=old, n=once: raw(f"dupkey-ok-{f}", f, o, n), (0, ""))
    for depth, want in ((MAX_DEPTH + 1, (2, True)), (MAX_DEPTH, (0, False))):
        nest = "[" * (depth - 1) + "]" * (depth - 1)     # the document itself is level 1
        case(f"an inventory.json nested {depth} deep is {'refused' if want[0] else 'read'}",
             lambda nest=nest, want=want: (lambda r: (r[0], f"nested deeper than {MAX_DEPTH}" in r[1]))(
                 raw(f"depth{len(nest)}", "inventory.json", '{"scan": ', '{"_deep": ' + nest + ', "scan": ')),
             want)

    # total output: a child process, so the stream is a REAL encoder (StringIO accepts anything)
    import os
    import subprocess

    def child(root, env, *extra):
        e = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8", "LC_ALL", "LANG")}
        e.update(env)
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--root", str(root), *extra],
                           capture_output=True, env=e, timeout=60)
        out = r.stdout + r.stderr
        return r.returncode, b"Traceback" in out, b"INTERNAL ERROR" in out, out

    def surrogate_tree(name):
        root = tree(name, costed((1.0, 1.0, 1.0)))
        p = root / MKT / "inventory.json"
        p.write_text(p.read_text().replace('"id": "ep2"', '"id": "\\ud800"', 1))
        return root
    case("a lone surrogate in a row id prints escaped, with the row's rc (1), never a traceback",
         lambda: (lambda r: (r[:3], b"\\ud800: [map]" in r[3]))(
             child(surrogate_tree("surr"), {"PYTHONIOENCODING": "utf-8"})), ((1, False, False), True))
    case("an ASCII-only stdout: a [shape] error prints, no traceback",
         lambda: (lambda r: (r[:3], b"[shape]" in r[3]))(child(tree("ascii-shape", costed((1.0, 1.0, 1.0))[:2] + [
             row("ship-lib", grade=None)]), {"PYTHONIOENCODING": "ascii"})), ((1, False, False), True))
    case("an ASCII-only stdout: --render prints, no traceback",
         lambda: (lambda r: (r[:3], b"SHIP \\xb7 measured" in r[3]))(
             child(tree("ascii-render", costed((1.0, 1.0, 1.0))), {"PYTHONIOENCODING": "ascii"}, "--render")),
         ((0, False, False), True))

    def nonascii_tree(name):
        root = tree(name, costed((1.0, 1.0, 1.0)))
        p = root / MKT / "inventory.json"
        doc = json.loads(p.read_text())
        doc["note"] = "§ — é"
        p.write_bytes(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
        return root
    case("a UTF-8 non-ASCII inventory is read under LC_ALL=C (the reader decodes UTF-8, never the locale's)",
         lambda: child(nonascii_tree("lc-c"), {"LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "0"})[:3],
         (0, False, False))

    # the net: an exception nothing anticipated is rc 2 and NOT RUN, never Python's exit 1
    def boom(*a, **k):
        raise LookupError("an exception no rule anticipated")

    def netted():
        g = globals()
        saved = g["inventory_errors"]
        g["inventory_errors"] = boom
        try:
            rc, out, _ = run(tree("net", costed((1.0, 1.0, 1.0))))
        finally:
            g["inventory_errors"] = saved
        return (rc, "INTERNAL ERROR: check-inventory.py raised LookupError" in out,
                any(ln.startswith("CANNOT RUN: ") for ln in out.splitlines()))
    case("an exception inside _main is rc 2 with INTERNAL ERROR, and no line starts `CANNOT RUN: `", netted,
         (2, True, False))
    case("...the same tree with nothing injected is rc 0", lambda: run(tree("net-ok", costed((1.0, 1.0, 1.0))))[0], 0)

    # the fuzz (thin): every node of every CLI fixture input replaced by each of 12 values, deleted, and (in a list)
    # duplicated, through the REAL reader and a strict UTF-8 stream. No exception escapes `main`; no INTERNAL ERROR.
    def fuzz():
        root = tree("fuzz", costed((1.0, 1.0, 1.0)))
        names = ("inventory.json", "components.json", "shipping-sets.json", "experiment-tier-a.json", SC)
        docs = {n: json.loads((root / MKT / n).read_text()) for n in names}
        current = {}
        vals = (None, True, 0, 10 ** 400, 1.5, "", "zz", "\ud800", [], [[]], {}, {"id": []})

        class Mem:
            def __init__(self, data):
                self.data = data

            def read_bytes(self):
                return self.data

            def __str__(self):
                return "<fuzz>"

        def paths(node, pre=()):
            yield pre
            kids = node.items() if isinstance(node, dict) else enumerate(node) if isinstance(node, list) else ()
            for k, v in kids:
                yield from paths(v, pre + (k,))

        bad, runs = [], 0
        g = globals()
        real = g["_read_json"]
        g["_read_json"] = lambda path: real(Mem(current[path.name])) if path.name in current else real(path)
        try:
            for n in names:
                for p in list(paths(docs[n])):
                    edits = [("=" + repr(v)[:20], v) for v in vals] + ([("del", None)] if p else [])
                    if p and isinstance(p[-1], int):
                        edits.append(("dup", None))
                    for tag, v in edits:
                        doc = copy.deepcopy(docs[n])
                        if not p:
                            doc = v
                        else:
                            parent = doc
                            for k in p[:-1]:
                                parent = parent[k]
                            if tag == "del":
                                del parent[p[-1]]
                            elif tag == "dup":
                                parent.append(copy.deepcopy(parent[p[-1]]))
                            else:
                                parent[p[-1]] = v
                        current.clear()
                        current[n] = json.dumps(doc).encode()
                        raw_out = io.BytesIO()
                        stream = io.TextIOWrapper(raw_out, encoding="utf-8", errors="strict")
                        old = sys.stdout, sys.stderr
                        sys.stdout = sys.stderr = stream
                        runs += 1
                        try:
                            try:
                                main(["--root", str(root)])
                                stream.flush()
                            finally:
                                sys.stdout, sys.stderr = old
                        except BaseException as e:      # noqa: BLE001 — the fuzz counts what escapes
                            bad.append(f"{n}:{p}{tag} ESCAPED {type(e).__name__}")
                            continue
                        if b"INTERNAL ERROR" in raw_out.getvalue():
                            bad.append(f"{n}:{p}{tag} NET")
        finally:
            g["_read_json"] = real
        return runs >= 2000, bad[:3]
    case("the fuzz: over 2000 edits of the fixture inputs, no exception escapes main and none reaches the net",
         fuzz, (True, []))

    print(f"{ok}/{ok + fail} self-test cases passed")
    return 0 if fail == 0 else 1


_DROP = object()


if __name__ == "__main__":
    sys.exit(main())
