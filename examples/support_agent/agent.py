"""A small, deterministic, rule-based customer support agent.

This agent needs no API key and makes no network calls, so the example eval
suite in this repository runs end to end offline. It has three tools: it
sends a password reset link, looks up an order's status, and escalates to a
human for anything it should not try to resolve on its own.

It is intentionally simple. The point of this example is the eval suite
around it, not the agent itself: swap this file for a call into a real
agent and the same suite, scorecard, and report generator still work.
"""

from __future__ import annotations

import re

from agent_evals import AgentResponse, ToolCall

ORDER_ID_PATTERN = re.compile(r"\b([A-Z]{1,3}-?\d{4,8})\b")
EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _extract_email(text: str) -> str | None:
    match = EMAIL_PATTERN.search(text)
    if not match:
        return None
    # The pattern's final character class allows a trailing period so it can
    # match multi-part domains like example.co.uk, but that also lets it
    # swallow a sentence-ending period. Strip trailing punctuation instead
    # of trying to make the pattern itself perfect.
    return match.group(0).rstrip(".,;:!?")


def _extract_order_id(text: str) -> str | None:
    match = ORDER_ID_PATTERN.search(text.upper())
    return match.group(1) if match else None


def run_agent(message: str) -> AgentResponse:
    """Route a support message to the right tool and reply.

    Routing is simple keyword matching, checked in a fixed priority order:
    a refund or cancellation request always escalates, even if the message
    also mentions a password or an order, because those requests need a
    human regardless of what else is in the message.
    """
    text = message.lower()
    tool_calls: list[ToolCall] = []

    if any(
        word in text for word in ("refund", "cancel", "cancellation", "furious", "unacceptable")
    ):
        tool_calls.append(
            ToolCall(name="escalate_to_human", args={"reason": "refund_or_cancellation"})
        )
        output = (
            "I'm sorry for the trouble. I'm connecting you with a member of our support "
            "team who can process that for you directly."
        )
    elif any(word in text for word in ("password", "reset", "locked out", "log in", "login")):
        email = _extract_email(message)
        tool_calls.append(ToolCall(name="send_password_reset_link", args={"email": email}))
        if email:
            output = f"I've sent a password reset link to {email}. It expires in 30 minutes."
        else:
            output = (
                "I've sent a password reset link to the email on your account. "
                "It expires in 30 minutes."
            )
    elif any(word in text for word in ("order", "shipment", "tracking", "package", "delivery")):
        order_id = _extract_order_id(message)
        tool_calls.append(ToolCall(name="lookup_order_status", args={"order_id": order_id}))
        if order_id:
            output = (
                f"Order {order_id} is in transit and should arrive within 3 to 5 business days."
            )
        else:
            output = (
                "I can look that up, but I need an order number to check its status. "
                "Could you share the order number from your confirmation email?"
            )
    else:
        output = (
            "I want to make sure I get this right. Could you tell me a bit more about "
            "what you need help with?"
        )

    input_tokens = len(message.split())
    output_tokens = len(output.split())

    return AgentResponse(
        output=output,
        tool_calls=tool_calls,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        model="rule-based-v1",
        cost_usd=0.0,
    )
