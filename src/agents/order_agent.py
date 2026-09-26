"""
agents/order_agent.py
------------------------
Order Agent for SnackStack.

Same pattern as menu_agent.py (bind tool -> bounded tool-calling loop ->
Command to synthesizer_node), plus one extra step up front: it tries to
extract an order ID / tracking ID / email from the query with regex. If
none is found, it calls interrupt() to pause the graph and ask the human
for one, rather than guessing or letting the LLM call the tool blind.

Expected graph state:
    user_query:     str            -- original user message
    order_query:    Optional[str]  -- sub-query from the Orchestrator, if any
    order_response: Optional[str]  -- written here by this node

Note: interrupt() only works when the graph is compiled with a
checkpointer (e.g. MemorySaver) and invoked with a thread_id, since
pausing/resuming requires persisted state. Resuming is done by the
caller via graph.invoke(Command(resume=<identifier>), config=...).
"""

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command, interrupt

from agents.prompts import ORDER_AGENT_PROMPT
from tools.order_tools import get_order_status

MAX_ITERATIONS = 5

ORDER_TOOLS = [get_order_status]
_TOOLS_BY_NAME = {t.name: t for t in ORDER_TOOLS}

_MODEL_NAME = os.environ.get("ORDER_AGENT_MODEL", "gpt-4o-mini")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
_llm = ChatOpenAI(model=_MODEL_NAME, temperature=0)
_llm_with_tools = _llm.bind_tools(ORDER_TOOLS)


# ---------------------------------------------------------------------------
# Identifier extraction
# ---------------------------------------------------------------------------
# Matches order IDs like "ORD1001", "ord-1001", "ORD 1001"
_ORDER_ID_RE = re.compile(r"\bORD[\s-]?\d{3,}\b", re.IGNORECASE)

# Matches tracking IDs like "TRK-8841-AR"
_TRACKING_ID_RE = re.compile(r"\bTRK-[A-Za-z0-9]{2,}-[A-Za-z]{2,}\b", re.IGNORECASE)

# Matches standard email addresses
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def extract_identifier(text: str) -> Optional[str]:
    """Try to pull an order ID, tracking ID, or email out of free text.

    Checked in this priority order: order ID -> tracking ID -> email.
    Returns the matched substring (normalized to uppercase for IDs), or
    None if nothing was found.
    """
    if not text:
        return None

    order_match = _ORDER_ID_RE.search(text)
    if order_match:
        return re.sub(r"[\s-]", "", order_match.group()).upper()

    tracking_match = _TRACKING_ID_RE.search(text)
    if tracking_match:
        return tracking_match.group().upper()

    email_match = _EMAIL_RE.search(text)
    if email_match:
        return email_match.group()

    return None


# ---------------------------------------------------------------------------
# Tool-calling loop (same pattern as menu_agent.py)
# ---------------------------------------------------------------------------
def _run_tool_calling_loop(messages: List[Any]) -> List[Any]:
    """Run bind-tools -> call -> execute -> repeat, capped at MAX_ITERATIONS."""
    for _ in range(MAX_ITERATIONS):
        response: AIMessage = _llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return messages

        for call in response.tool_calls:
            tool = _TOOLS_BY_NAME.get(call["name"])
            if tool is None:
                output = f"Error: unknown tool '{call['name']}'"
            else:
                try:
                    output = tool.invoke(call["args"])
                except Exception as exc:
                    output = f"Error running tool '{call['name']}': {exc}"
            messages.append(ToolMessage(content=str(output), tool_call_id=call["id"]))

    messages.append(
        HumanMessage(
            content=(
                "You've reached the maximum number of tool calls. "
                "Give your best final answer now, based only on the tool "
                "results above, without calling any more tools."
            )
        )
    )
    final_response = _llm.invoke(messages)
    messages.append(final_response)
    return messages


def order_agent_node(state: Dict[str, Any]) -> Command:
    """LangGraph node: answer the order-status portion of the user's query.

    First tries to extract an identifier (order ID / tracking ID / email)
    with regex. If none is found, interrupts the graph to ask the human
    directly, rather than letting the LLM guess or call the tool blind.
    """
    query = state.get("order_query") or state.get("user_query", "")

    identifier = extract_identifier(query)

    if identifier is None:
        # Pause the graph and hand control back to the human/caller.
        human_reply = interrupt(
            {
                "reason": "missing_identifier",
                "message": (
                    "I couldn't find an order ID, tracking ID, or email in "
                    "your message. Could you share one of those so I can "
                    "look up your order?"
                ),
            }
        )
        # Execution resumes here once the caller does
        # graph.invoke(Command(resume=<human_reply>), config=...)
        human_reply = str(human_reply)
        identifier = extract_identifier(human_reply)

        if identifier is None:
            # Still nothing usable -- let the LLM explain the situation
            # rather than calling the tool with garbage.
            query = f"{query} {human_reply}".strip()
        else:
            query = human_reply

    messages: List[Any] = [
        SystemMessage(content=ORDER_AGENT_PROMPT),
        HumanMessage(
            content=(
                f"User query: {query}\n"
                f"Extracted identifier: {identifier if identifier else 'none found'}"
            )
        ),
    ]

    messages = _run_tool_calling_loop(messages)

    final_message = messages[-1]
    order_response = final_message.content or "I couldn't find an answer to that order question."

    return Command(
        goto="synthesizer_node",
        update={
            "order_response": order_response,
            "order_messages": messages,
        },
    )


if __name__ == "__main__":
    # Quick manual smoke tests for the regex extractor (no LLM calls)
    samples = [
        "Where is my order ORD1002?",
        "Can you track TRK-6612-KM for me?",
        "Check status for rohan.das@example.com",
        "Hey, what's happening with my food?",  # no identifier -> None
    ]
    for s in samples:
        identifier = extract_identifier(s)
        print(f"{s!r} -> {identifier}")
        if identifier is None:
            print("Skipping node invocation: interrupt() requires a compiled graph.")
            continue
        result = order_agent_node({"order_query": s})
        print(f"goto: {result.goto}")
        print(f"order_response:\n{result.update['order_response']}")

