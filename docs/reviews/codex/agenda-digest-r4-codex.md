<!-- codex-review: model=gpt-6.1-sol -->

- **Low — scripts/goal-tree.py:1764:** Focus-step escaping and reference linking lack a discriminating test/mutation. Replacing `_html_line(st["text"], repo)` with raw `st["text"]` leaves **357/357 cases green**, despite allowing HTML injection and dropping reference links in the focus list.

- **Low — scripts/goal-tree.py:1759:** The empty “In flight now” message is unguarded. Replacing `"<li>nothing in flight</li>"` with `""` leaves **357/357 cases green**. No case fails by name when this new empty-state behavior disappears.

VERDICT: NOT CONVERGED
