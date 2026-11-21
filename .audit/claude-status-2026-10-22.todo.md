# Claude status investigation

- [x] Route through the **how** skill. For motivation questions, also route through the **why** skill.
  - Use one Claude explainer for this bounded status investigation. No implementation, architectural redesign or motivation review is requested.
- [x] Throughput checkpoint stays one line: `throughput checkpoint: n/a, read-only investigation`.
- [x] Produce the `how`-shaped output (Overview / Key Concepts / How It Works / Where Things Live / Gotchas), or a recommendation with a tradeoffs table if the request is a decision between alternatives.
- [x] Apply the **unslop** skill to the reply.
- [x] Run actual Claude Code with Read/Glob/Grep only and retain its result and model metadata.
- [x] Check cited findings against the current source and verify no project-source/Evidence changes.
  - The source hash comparison checks 760 existing files. Claude had only read tools. Existing Evidence is not rewritten by the parent; new report artifacts are separate.
- [x] Return Claude's confirmed findings and label hypotheses and unverified claims.

The full implementation goal remains paused. This request authorizes only this investigation.
