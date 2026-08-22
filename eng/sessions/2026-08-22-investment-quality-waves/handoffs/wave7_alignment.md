# Wave 7 alignment — gather

Verdict: **ALIGN WITH EDITS**.

`check_cash_quality` lives in `scripts/kd_research/cash_quality.py`. Wire `--full` + `1d`/`2_parallel` entry. Missing LQ SKIPPED. Do not NLP background. Agent 5 reads cash_quality, does not write it. Schema documents optional object; add destock_rule/cash_conversion_rule to evidence_log enum.
