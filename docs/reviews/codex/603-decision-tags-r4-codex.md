<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: 63e1a9e24f0340baad30f17a890d662c791883fc

No BLOCKER found in `2729b01b..63e1a9e2`.

Evidence run:

- `python3 scripts/brief-compose.py --self-test`: **226/226 passed**.
- `scripts/brief-compose.py:3103,3110`: all **8 new mutations killed**, each attributed to its named test; before/after controls green. Used the existing harness with an in-memory selection of the eight fold mutations.
- Composed **all 34 fragments** against master `2f5e3f3d`, using identical tray inputs and fixed timestamps: **33 decision-free outputs byte-identical**; walkthrough **13 total / 2 remaining / 11 answered**. No corpus refusal or crash.
- `scripts/brief-compose.py:1154,1269`: direct probes confirmed marks ON/INSIDE both SVG and MathML refuse; hidden paragraphs remain protected across either foreign root; visible decisions after closed roots count.

**FILE-ONLY — Low, existing #616**, `scripts/brief-compose.py:1306`: `<p>a<b hidden>c</p><div data-decision>d</div>` still returns `(1, 1)` before and after the fold. This is the acknowledged pre-existing misnesting gap. Searched all 34 fragments for hidden paragraph/formatting siblings; none found. No new non-BLOCKER finding.

Worktree remained clean; no commits or GitHub actions.

VERDICT: CONVERGED
