<!-- codex-review: model=gpt-6.1-terra -->

No new findings. The Python compose-time scan and runtime check do not agree on every input: the documented omitted-end-tag and entity cases pass composition but are refused by the runtime check. That limitation is already recorded in backlog #724.

Both self-tests passed with stdin closed: `brief-compose.py` 255/255 and `ask_answerer.py` 127/127. The mutation manifest and expected count both contain 110 entries; I did not rerun the mutation sweep.

VERDICT: CONVERGED
