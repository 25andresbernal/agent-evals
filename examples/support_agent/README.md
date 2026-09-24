# Example: support agent eval suite

A small, deterministic, rule-based customer support agent (`agent.py`),
evaluated against a scorecard (`scorecard.yaml`) and ten cases
(`cases.yaml`). `report.md` in this directory is a real, committed run: you
can read it without running anything.

The agent needs no API key and makes no network call, so this suite runs
fully offline, including its quality dimension, which uses `FakeJudge`.

Reproduce the committed report:

```bash
agent-evals run examples/support_agent/suite.yaml \
  --out examples/support_agent/report.md \
  --json examples/support_agent/run.json
```

Files:

- `agent.py`: the agent under test. Three tools: `send_password_reset_link`,
  `lookup_order_status`, `escalate_to_human`.
- `cases.yaml`: ten cases covering password resets, order lookups, refund
  escalation, a priority edge case where two intents collide, and a
  fallback case with no matching intent.
- `scorecard.yaml`: the weighted dimensions and thresholds this suite holds
  the agent to.
- `suite.yaml`: ties the three files above together for the CLI.
- `report.md`: the committed output of the command above.
