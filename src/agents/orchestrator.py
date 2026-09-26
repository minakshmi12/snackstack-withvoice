"""
agents/orchestrator.py
------------------------
Orchestrator for SnackStack.

Uses llm.with_structured_output() so the routing decision comes back as a
validated Pydantic object (list of agent names + reasoning) instead of
free-form text that would need brittle parsing.
"""

import os
import sys
from enum import Enum
from typing import List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.agents.prompts import ORCHESTRATOR_PROMPT


class AgentName(str, Enum):
    """The specialist agents the Orchestrator is allowed to route to."""
    MENU_AGENT = "menu_agent"
    ORDER_AGENT = "order_agent"


class RoutingDecision(BaseModel):
    """Structured routing decision produced by the Orchestrator LLM."""

    agents: List[AgentName] = Field(
        default_factory=list,
        description=(
            "Which specialist agent(s) should handle this query, in the "
            "order they should be consulted. Include both menu_agent and "
            "order_agent if the query needs both. Empty list if the query "
            "is unrelated to food or orders."
        ),
    )
    menu_query: Optional[str] = Field(
        default=None,
        description="The sub-query to send to menu_agent, or null if not applicable.",
    )
    order_query: Optional[str] = Field(
        default=None,
        description="The sub-query to send to order_agent, or null if not applicable.",
    )
    reasoning: str = Field(
        description="One short sentence explaining why the query was routed this way."
    )


_MODEL_NAME = os.environ.get("ORCHESTRATOR_MODEL", "gpt-4o-mini")
_llm = ChatOpenAI(model=_MODEL_NAME, temperature=0)
_structured_llm = _llm.with_structured_output(RoutingDecision)


def route_query(user_query: str) -> RoutingDecision:
    """Ask the Orchestrator LLM how to route a single user query.

    Args:
        user_query: The raw query text from the user.

    Returns:
        A validated RoutingDecision: agents (list), menu_query, order_query,
        and reasoning.
    """
    if not user_query or not user_query.strip():
        return RoutingDecision(
            agents=[],
            menu_query=None,
            order_query=None,
            reasoning="Empty query -- nothing to route.",
        )

    messages = [
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        HumanMessage(content=user_query),
    ]
    decision: RoutingDecision = _structured_llm.invoke(messages)
    return decision


if __name__ == "__main__":
    # Quick manual smoke test across the main routing scenarios
    test_queries = [
        "What's a good vegan option under 300 rupees?",
        "Where is my order ORD1002?",
        "Is Butter Chicken spicy, and can you also check status of TRK-6612-KM?",
        "What's the weather like today?",
    ]
    for q in test_queries:
        print(f"Query: {q}")
        result = route_query(q)
        print(f"Query: {q}")
        print(f"  agents:      {[a.value for a in result.agents]}")
        print(f"  menu_query:  {result.menu_query}")
        print(f"  order_query: {result.order_query}")
        print(f"  reasoning:   {result.reasoning}\n")