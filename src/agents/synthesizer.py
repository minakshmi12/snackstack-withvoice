"""
agents/synthesizer.py
------------------------
Synthesizer for SnackStack.

Runs after the specialist agents (menu_agent_node, order_agent_node) and
merges whichever of them ran into one coherent, user-facing reply.

Why this node matters for parallel dispatch:
    If the Orchestrator fans out to both menu_agent_node and order_agent_node
    at once (e.g. via LangGraph's Send API), they execute in the same
    superstep and each writes to a different state key (menu_response /
    order_response). Both `Command(goto="synthesizer_node")` calls resolve
    to the SAME downstream node in that superstep, so synthesizer_node runs
    exactly once, after both branches have finished -- by which point state
    already has both fields populated. This node's only job is to read
    whatever landed in state and produce one final answer; it does not need
    to know whether one or two agents ran.

Expected graph state:
    user_query:     str
    menu_response:  Optional[str]
    order_response: Optional[str]
    final_response: str  -- written here
"""

import os
import sys
from typing import Any, Dict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END
from langgraph.types import Command

from agents.prompts import SYNTHESIZER_PROMPT
load_dotenv()

_MODEL_NAME = os.environ.get("SYNTHESIZER_MODEL", "gpt-4o-mini")
_llm = ChatOpenAI(model=_MODEL_NAME, temperature=0.3)


def _build_context(state: Dict[str, Any]) -> str:
    """Assemble whatever specialist outputs are present into one context
    block for the LLM. Missing agents are simply omitted, not padded with
    placeholder text.
    """
    parts = [f"Original user query: {state.get('user_query', '')}"]

    menu_response = state.get("menu_response")
    if menu_response:
        parts.append(f"\nMenu Agent output:\n{menu_response}")

    order_response = state.get("order_response")
    if order_response:
        parts.append(f"\nOrder Agent output:\n{order_response}")

    return "\n".join(parts)


def synthesizer_node(state: Dict[str, Any]) -> Command:
    """LangGraph node: merge specialist outputs into one final reply.

    Handles three cases:
      1. Only menu_response is present.
      2. Only order_response is present.
      3. Both are present (typical when the query spanned menu + order,
         especially after parallel dispatch).
    If neither is present, returns a graceful fallback instead of calling
    the LLM on empty context.
    """
    menu_response = state.get("menu_response")
    order_response = state.get("order_response")

    if not menu_response and not order_response:
        final_response = (
            "I'm not sure how to help with that -- I couldn't find a menu "
            "or order match for your request. Could you rephrase, or "
            "provide an order ID / tracking ID / email if you're asking "
            "about an existing order?"
        )
        return Command(goto=END, update={"final_response": final_response})

    context = _build_context(state)

    messages = [
        SystemMessage(content=SYNTHESIZER_PROMPT),
        HumanMessage(content=context),
    ]

    response = _llm.invoke(messages)
    final_response = response.content or "Sorry, I couldn't put together an answer for that."

    return Command(goto=END, update={"final_response": final_response})


if __name__ == "__main__":
    # Quick manual smoke tests covering all three cases
    test_states = [
        {
            "user_query": "What's a good vegan option under 300 rupees?",
            "menu_response": "Vegan Buddha Bowl (INR 319, 4.6/5) and Aglio e Olio "
                              "(INR 279, 4.5/5) are both vegan. Aglio e Olio fits under 300.",
            "order_response": None,
        },
        {
            "user_query": "Where's my order ORD1002?",
            "menu_response": None,
            "order_response": "Order ORD1002 (Butter Chicken, INR 379) is Out for "
                               "Delivery, tracking TRK-7723-PS, estimated delivery 2025-01-12.",
        },
        {
            "user_query": "Is Butter Chicken spicy, and where's my order TRK-6612-KM?",
            "menu_response": "Butter Chicken (INR 379, 4.9/5) is a creamy, mildly "
                              "spiced tomato curry -- not very spicy.",
            "order_response": "Order ORD1003 (Vegan Buddha Bowl) is Preparing, "
                               "tracking TRK-6612-KM, estimated delivery 2025-01-13.",
        },
    ]

    for s in test_states:
        result = synthesizer_node(s)
        print(f"Query: {s['user_query']}")
        print(f"Final response:\n{result.update['final_response']}\n{'-'*60}")