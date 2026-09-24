# Support Agent Eval Suite

Generated 2026-09-24 04:42 UTC. 10 cases, 10 passed, 0 failed (100% pass rate). Average weighted score 0.97 against a pass threshold of 0.75.

## Summary by dimension

| Dimension | Weight | Avg score | Threshold | Cases below threshold |
|---|---|---|---|---|
| task_success | 0.35 | 1.00 | 0.80 | 0 |
| tool_correctness | 0.3 | 1.00 | 0.80 | 0 |
| quality | 0.2 | 0.86 | 0.60 | 0 |
| cost | 0.1 | 1.00 | 0.90 | 0 |
| latency | 0.05 | 1.00 | 0.90 | 0 |

## Case results

| Case | Tags | Result | Weighted score | task_success | tool_correctness | quality | cost | latency |
|---|---|---|---|---|---|---|---|---|
| password-reset-with-email | password, tier1 | PASS | 0.98 | 1.00 | 1.00 | 0.90 | 1.00 | 1.00 |
| password-reset-no-email | password | PASS | 0.98 | 1.00 | 1.00 | 0.90 | 1.00 | 1.00 |
| login-trouble | password | PASS | 0.98 | 1.00 | 1.00 | 0.90 | 1.00 | 1.00 |
| order-status-with-id | order, tier1 | PASS | 0.97 | 1.00 | 1.00 | 0.85 | 1.00 | 1.00 |
| order-status-no-id | order | PASS | 0.97 | 1.00 | 1.00 | 0.85 | 1.00 | 1.00 |
| delivery-keyword-order | order, edge-case | PASS | 0.96 | 1.00 | 1.00 | 0.80 | 1.00 | 1.00 |
| refund-request | refund, tier1 | PASS | 0.97 | 1.00 | 1.00 | 0.85 | 1.00 | 1.00 |
| cancellation-request | refund | PASS | 0.96 | 1.00 | 1.00 | 0.80 | 1.00 | 1.00 |
| refund-takes-priority-over-password | refund, priority, edge-case | PASS | 0.97 | 1.00 | 1.00 | 0.85 | 1.00 | 1.00 |
| ambiguous-fallback | fallback, edge-case | PASS | 0.99 | 1.00 | 1.00 | 0.95 | 1.00 | 1.00 |
