---
name: explainer-pages-lead-with-diagrams
description: Building any explainer/brief/findings page? Draw the mechanism as inline SVG diagrams wherever possible — the owner finds prose-only explanations confusing
metadata:
  node_type: memory
  type: feedback
  originSessionId: b387c8e6-9003-42f5-a944-1d4eb1de0c9b
  modified: 2026-11-12T19:37:30.225Z
---

Owner 2026-11-12 11:37, after the stale-pages page (three SVG diagrams: today's flow, proposed flow, decision rule):
"Diagram make it much easier to follow. I hope you use diagram whenever possible in explainer pages."
Earlier the same day the prose-only chat explanation of the same design was "confusing".

**Why:** the owner skims; a flow or a decision rule drawn as boxes and arrows is understood at a glance, while
the same content in paragraphs has to be read and reconstructed.

**How to apply:** for every page from explain-topic / explain-diff / brief / explain-findings, ask "is there a
flow, a before/after, a decision rule or a structure here?" — if yes, draw it as inline SVG (colour tokens, both
themes) before writing prose about it. Prose explains *why*; the diagram carries *what connects to what*.
Use the house colours from CONTEXT.md "The common look" (gold headings) — never an invented accent
(I used purple on 11-12 and the owner noticed). Rule also lives in `.agents/skills/shared/explainer-delivery.md` §2.
