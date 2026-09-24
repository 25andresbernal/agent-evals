# Writing an eval a PM can own

Most teams building an AI agent skip straight to "does it work" measured by
vibes: someone tries it for ten minutes, it feels fine, it ships. That is
not a quality bar. It is an absence of one. An eval suite is how you write
down what "good" means before you ship, so you can check the agent against
it every time it changes instead of re-forming your opinion from scratch.

This is not an engineering exercise you hand off. Deciding what a good
response looks like, how much a mistake costs, and which failures are
acceptable is a product decision. This doc is about how to make that
decision and turn it into a scorecard and a set of cases, using the tools
in this repository.

## Start from the scorecard, not the cases

Before you write a single eval case, decide what you are actually holding
the agent to. In this framework that is the `Scorecard`: a short YAML file
naming the dimensions that matter and how much each one counts.

A support agent scorecard might weigh task success heavily, tool
correctness almost as heavily, a quality rubric a bit less, and cost and
latency lightly, as a backstop rather than the main signal. A code-review
agent might weigh correctness of the flagged issues heavily and weigh tone
barely at all. The weights are a product call: they say what you are
willing to trade off. Write them down, and expect to argue about them with
engineering. That argument is the point. It surfaces disagreements about
priorities you would otherwise discover after launch.

Each dimension also gets a threshold: the minimum score that dimension has
to clear, even if the overall weighted average is fine. This matters
because weighted averages hide failure. An agent that is excellent at
answering questions and terrible at knowing when to escalate can still post
a high average if task success is worth more than escalation correctness.
A per-dimension threshold stops a strength from masking a specific,
dangerous weakness.

## Write cases from real failures, not from imagination

The fastest way to write a useless eval suite is to invent ten cases that
sound plausible and call it done. Real inputs are stranger, more specific,
and more repetitive than anything you would think to write. Cases should
come from:

- Support tickets, chat logs, or transcripts where the agent (or a human
  doing the job today) got it wrong.
- Edge cases someone on the team already knows about and has been quietly
  worried about.
- The most common request, verbatim, because an agent that fails the
  common case has failed regardless of how it does on the tail.

When you find a real failure, write the case so its expected outcome
encodes the actual fix, not a vague description of it. "The agent should
not promise a refund" is not testable. "The response does not contain the
word 'refund' when the case is tagged `no-refund-authority`" is. Look at
`examples/support_agent/cases.yaml` in this repository for the shape: each
case is one input, one or more phrases the output must contain, and the
exact tool calls (with arguments) a correct agent should make.

Aim for cases that isolate one thing at a time, plus a few that combine
signals on purpose. The `refund-takes-priority-over-password` case in the
example suite exists because a real agent like this could plausibly see
both "refund" and "password" in one message and route to the wrong branch.
That is a one-line case to write and it catches a real class of bug.

Ten to twenty cases per scorecard is a reasonable starting size for a
single agent behavior. You do not need hundreds before you ship the first
version. You need enough to cover the common path, the two or three known
edge cases, and one or two things that would be embarrassing if they broke
silently.

## Setting thresholds without gaming yourself

A threshold that is too loose tells you nothing. A threshold set to
whatever the agent currently scores tells you even less, because it will
always pass. Set thresholds from the cost of being wrong, not from the
agent's current performance:

- If a wrong answer costs a support ticket and an apology, a task success
  threshold in the 0.7 to 0.8 range per case, and needing to hit it, is
  reasonable.
- If a wrong answer costs money moving or a compliance exposure, tool
  correctness on the specific tool that spends money should sit close to
  1.0, and you should consider making that one dimension a hard gate
  outside the weighted average entirely.
- Cost and latency thresholds should come from what the product can afford
  per interaction, not from what the agent happens to cost today. If your
  unit economics need a response under a cent, say so in the scorecard
  even if the current agent blows past it. That is useful information, not
  a suite you need to fix.

Revisit thresholds when the agent's job changes, not on a schedule. A
threshold set for an internal tool with a human always double-checking the
output is not the threshold for the same agent once it talks to customers
directly.

## The LLM judge is a second opinion, not a verdict

`task_success` and `tool_correctness` check things you can specify exactly:
does the output contain this phrase, did the agent call this tool with
these arguments. A lot of what makes a response good cannot be specified
that precisely. Was it warm without being saccharine? Did it stay
appropriately brief? Did it avoid a confident-sounding wrong answer? That
is what the `llm_judge` scorer and its rubric are for.

Write the rubric the way you would brief a new team member reviewing
transcripts: what does a 1.0 look like, what does a 0.0 look like, and what
should the judge weigh if it has to choose. Vague rubrics ("rate the
quality") produce vague, inconsistent scores. Specific rubrics ("does the
response resolve the request or state the next step, in a warm but
efficient tone, without jargon or overpromising") produce scores you can
trust and defend.

Treat judge disagreement as information, not noise. When the judge scores a
case lower than you expected, read the transcript before you change the
rubric or the threshold. Sometimes the judge is right and you missed a real
problem. Sometimes the rubric is ambiguous and needs to be more specific.
Only rarely is the fix to loosen the threshold until the disagreement goes
away. That last move quietly turns your quality bar into theater.

This repository ships two judges. `FakeJudge` is a deterministic, offline
heuristic used by the test suite and by the example when no API key is
set: it exists so the pipeline runs without a network call, not as a
stand-in for real judgment. `AnthropicJudge` calls a real Claude model with
your rubric and returns a score and a reasoning string. Use `FakeJudge` in
CI so the suite runs on every commit at no cost, and run with
`AnthropicJudge` before you make a real ship decision.

## Avoiding the ways evals get gamed

An eval suite loses its value the moment people start optimizing to pass
it instead of using it to check quality. A few habits keep that from
happening:

- Do not let the person who built the agent be the only one who writes or
  edits the cases. A second set of eyes, ideally someone closer to the
  end user, catches cases that quietly assume the agent's own behavior.
- Do not shrink a threshold to make a suite pass. If a case keeps failing,
  either the agent has a real problem or the case is wrong. Fix one of
  those two things and say which one you fixed, in the commit message,
  so the history stays honest.
- Keep a few cases the agent's builders do not see while iterating, the way
  a held-out test set works in traditional ML. It is easy to
  unconsciously overfit an agent's prompt to the cases in front of you.
- Re-run the suite after any change to the prompt, the tools, or the
  underlying model, not just after changes that were meant to affect
  behavior. Use `agent-evals compare old.json new.json` to see exactly
  which cases moved and in which direction before you ship.

## What this looks like end to end

1. Define the scorecard: which dimensions, how much each counts, what
   threshold each has to clear.
2. Pull real inputs and write cases against them, including the exact
   tool calls a correct agent makes.
3. Wire up an adapter so `agent-evals` can call your agent: one function
   that takes the input and returns an `AgentResponse`.
4. Run `agent-evals run suite.yaml --out report.md --json run.json` and
   read the report like a hiring manager reading a candidate's work: does
   it actually do the job, not just look like it might.
5. Before a real ship decision, run the quality dimension against a real
   judge, not the fake one, and read a sample of the judge's reasoning
   strings yourself.
6. Keep the suite in version control next to the agent. Every prompt
   change is a candidate to break a case; the suite is what tells you
   before your users do.

The example in `examples/support_agent/` in this repository follows this
exact structure end to end and is a reasonable template to copy for a new
agent.
