# Which model should run the skill?

The full eval suite (8 golden cases, 155 checks) was run once with the skill on each model. The grader was always
`claude-sonnet-5-5`, as in the baseline, so only the skill model changed. Run on 2026-10-14; decision record
[D-64](../connection/DECISIONS_LOG.md); run summaries in [`evals/comparisons/`](../evals/comparisons/).

| | Opus 5.5 (baseline v6) | Sonnet 5.5 | Haiku 5.5 |
|---|---|---|---|
| Checks passed | 155/155 | 155/155 | 154/155 |
| Cases passed | 8/8 | 8/8 | 7/8 |
| Case h (prompt injection) | PASS | PASS | PASS |
| Claims failed | none | none | d:F1, a grader error (below) |
| Cost per report (mean of 8 skill runs) | $0.369 | $0.134 | $0.011 |
| Cost per full suite (skill runs + 14 grader calls) | $3.31 | $1.42 | $0.43 |
| Average skill run time | 57.4 s | 26.8 s | 35.3 s |
| 10 client reports a month | $3.69 | $1.34 | $0.11 |
| Run | `v6-run-20261014` | `cmp-sonnet-5-5-20261014` | `cmp-haiku-5-5-20261014-r2` |

- **Opus row:** baseline v6. It ran with resampling enabled but needed none, so it is directly comparable to the
  other two runs, which used `--no-resample` (one sample per case).
- **Grading costs about the same in every run** ($0.35–0.36), so most of Haiku's suite cost is grading.
- **Haiku's one failure is the grader's, not Haiku's.** The commentary mentions Charitable Donations once, as
  "Charitable Donations treated as blank", which F1 allows. The grader's evidence says "it is not forbidden content,
  so F1 should PASS. I am correcting this in the verdict below", and its verdict is FAIL. Recorded as returned; no
  verdict was edited.
- **An earlier Haiku run exposed a harness bug.** `cmp-haiku-5-5-20261014` scored 153/155 because X3 read a
  300-character copy of each command, and Haiku's long chained commands pushed `run_trends.py` past the cut. X3 was
  fixed to read the full command, and this row is the clean re-run (D-64).

**How Haiku behaved.**
- **Chained commands:** it wrapped every script call (8 of 8, in both runs) in several chained shell commands,
  listing folders first. Sonnet chained none, and Opus chained 1 of 11.
- **An option nobody asked for:** once in each run it added `--company`, which changed the company name in that
  report. The checks still passed. The skill works for Haiku, but it follows the instructions less closely.

**Conclusion.**
- On this suite, all three models produced correct, safe reports: every structured check, every real commentary
  claim and the prompt-injection case passed.
- For 10 clients a month I would use **Sonnet 5.5**. It matched Opus on every check at about a third of the cost
  ($1.34 vs $3.69 a month) and in under half the time.
- Haiku would save only about $1.23 a month more, and it followed the skill's instructions less closely. At this
  volume the money is trivial next to the reviewer's time, so commentary quality matters more than price.
- **Trade-off:** Opus stays the reference model the evals were built and baselined on. Switching production to
  Sonnet should wait for a repeat with several samples per model.

**Caveats.**
- **One run per model:** a small sample. The commentary varies from run to run, so a single PASS is evidence, not
  proof.
- **Sonnet was graded by its own model,** which may favour it.
- **The grader can contradict itself.** It did once here (d:F1), in 32 graded commentary claims per run.
- **Cost basis:** costs are the `total_cost_usd` Claude Code reports for each call, at list prices
  (Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, Haiku 5.5 $0.10/$0.50 per million input/output tokens).
- **Scope:** the suite covers one real workbook and two synthetic ones. A client with an unusual export could
  separate the models where these cases don't.
