---
description: Append the last question and the answer you gave to submission/Q&A log.md (checked, atomic write)
allowed-tools: Bash(python scripts/log_answer.py:*)
---

Log the most recent question-and-answer exchange from THIS conversation to `submission/Q&A log.md`.

Rules (follow all of them; if any can't be met, log nothing and say why):

1. **Only a real answer.** Take the user's most recent question before this command and the answer you actually
   gave to it in this conversation. If you did not answer it (you asked a clarifying question, the tool call
   failed, or you declined), stop and say "Nothing logged: no answer was given."
2. **Verbatim.** Copy the answer text exactly as you wrote it: no rewording, no new figures, no added conclusions.
   You may leave out tool output and code blocks that were not part of the answer itself.
3. **Data source.** Use exactly one of:
   - `QuickBooks sandbox via MCP`: the answer came from QuickBooks MCP tool results in this conversation;
   - `ABC workbook via the skill`: it came from the monthly-trend-analysis skill or its report;
   - `QuickBooks sandbox via MCP + ABC workbook via the skill`: both.

   If the answer came from neither, don't log it; say it isn't a data answer.
4. **Key figures.** List the figures your answer cites, copied exactly as written in the answer (the script
   refuses any figure that isn't in the answer word for word).
5. **No secrets.** Never include tokens, keys, client IDs or secrets, the realm ID (not even part of it), or
   anything from `connection/.secrets/`, and never read those files. The script refuses such entries; if it
   does, report that and do not rephrase the entry to get past the check.

Then write the entry by running this command once, with the JSON filled in:

```bash
python scripts/log_answer.py <<'JSON'
{"question": "<the user's question>", "source": "<one of the three sources>", "answer": "<your answer, verbatim>", "figures": ["<figure>", "<figure>"]}
JSON
```

Report the script's one-line result (logged at <time>, or NOT logged and why). $ARGUMENTS
