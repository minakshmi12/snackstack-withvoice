"""
graph.py
--------
Assembles the SnackStack LangGraph pipeline in TWO selectable dispatch
modes, sharing the same state schema, specialist agents, and Synthesizer:

  mode="parallel" (default):
      START -> orchestrator_node -> Command(goto=[Send("menu_agent_node"),
                Send("order_agent_node")]) -- both run in the SAME
                superstep when a query needs both -> synthesizer_node -> END
      Each specialist node routes to synthesizer_node itself via
      Command(goto="synthesizer_node"). LangGraph collapses duplicate
      goto targets within a superstep, so synthesizer_node runs exactly
      once, only after every dispatched branch has finished.

  mode="sequential":
      START -> orchestrator_node -> (conditional edge) -> menu_agent_node
                -> (conditional edge) -> order_agent_node
                -> (conditional edge) -> synthesizer_node -> END
      The Orchestrator queues needed agents in `pending_agents`; a router
      function checks that queue after each agent and sends the graph to
      whichever agent is still pending, or to the Synthesizer once empty.
      Agents never run concurrently in this mode.

Trade-off: parallel is faster when both agents are needed (latency is
max(menu, order) instead of menu + order); sequential is simpler to
reason about and easier on strict per-minute rate limits.

MULTI-TURN MEMORY (shared by both modes):
    `messages` in StackState is annotated with LangGraph's add_messages
    reducer. Every graph.invoke(..., config={"configurable":
    {"thread_id": X}}) call that reuses the same thread_id resumes from
    the state MemorySaver saved after that thread's last turn, and new
    messages are APPENDED to -- not overwritten by -- that history.
    Different thread_ids get fully isolated conversation memory.

    A MemorySaver checkpointer is also required for order_agent_node's
    interrupt()/resume flow within a single turn (identifier collection).

NOTE: MemorySaver keeps everything in-process memory; fine for
development but lost on restart. Swap in a persistent checkpointer
(e.g. langgraph.checkpoint.sqlite.SqliteSaver) for real deployments
without changing anything else in this file.
"""

import os
import sys
from typing import Annotated, Any, List, Literal, Optional, TypedDict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, Send, interrupt

# Command-based node functions (used as-is in "parallel" mode)
from agents.menu_agent import menu_agent_node as menu_agent_node_parallel
from agents.order_agent import order_agent_node as order_agent_node_parallel

# Lower-level building blocks reused to build the "sequential" variants,
# so both modes share the exact same tool-calling logic.
from agents.menu_agent import _run_tool_calling_loop as _menu_tool_loop
from agents.order_agent import _run_tool_calling_loop as _order_tool_loop
from agents.order_agent import extract_identifier
from agents.prompts import MENU_AGENT_PROMPT, ORDER_AGENT_PROMPT

from agents.orchestrator import AgentName, route_query
from agents.synthesizer import synthesizer_node
from src.state import StackState


# ---------------------------------------------------------------------------
# Synthesizer wrapper (shared by both modes): same synthesis logic as
# agents/synthesizer.py, plus recording the assistant's final answer into
# the accumulating message history for the next turn's checkpoint restore.
# ---------------------------------------------------------------------------
def synthesizer_with_memory_node(state: StackState) -> Command:
    result = synthesizer_node(state)  # Command(goto=END, update={"final_response": ...})
    final_response = result.update.get("final_response", "")
    result.update["messages"] = [AIMessage(content=final_response)]
    return result


# ===========================================================================
# MODE: parallel  (Command + Send)
# ===========================================================================
def orchestrator_node_parallel(state: StackState) -> Command:
    decision = route_query(state["user_query"])

    # Record this turn's user message; add_messages appends it to
    # whatever history MemorySaver already restored for this thread_id.
    turn_update = {"messages": [HumanMessage(content=state["user_query"])]}

    sends: List[Send] = []

    if AgentName.MENU_AGENT in decision.agents:
        sends.append(
            Send(
                "menu_agent_node",
                {**state, "menu_query": decision.menu_query or state["user_query"]},
            )
        )

    if AgentName.ORDER_AGENT in decision.agents:
        sends.append(
            Send(
                "order_agent_node",
                {**state, "order_query": decision.order_query or state["user_query"]},
            )
        )

    if not sends:
        # Unrelated query -- skip straight to the Synthesizer, which has
        # a graceful fallback for empty responses.
        return Command(goto="synthesizer_node", update={**turn_update, "agents": []})

    return Command(
        goto=sends,
        update={**turn_update, "agents": [a.value for a in decision.agents]},
    )


# ===========================================================================
# MODE: sequential  (conditional edges, one agent at a time)
# ===========================================================================
def orchestrator_node_sequential(state: StackState) -> dict:
    decision = route_query(state["user_query"])
    pending = [_AGENT_NODE_NAMES[a] for a in decision.agents]

    return {
        "messages": [HumanMessage(content=state["user_query"])],
        "agents": [a.value for a in decision.agents],
        "pending_agents": pending,
        "menu_query": decision.menu_query or state["user_query"],
        "order_query": decision.order_query or state["user_query"],
    }


def _route_to_next_pending(state: StackState) -> str:
    """Shared router: go to whatever's next in the queue, else synthesize."""
    pending = state.get("pending_agents", [])
    return pending[0] if pending else "synthesizer_node"


def menu_agent_node_sequential(state: StackState) -> dict:
    """Same tool-calling logic as agents/menu_agent.py, but returns a plain
    state update (no Command) -- conditional edges own the routing here.
    """
    query = state.get("menu_query") or state.get("user_query", "")
    messages: List[Any] = [
        SystemMessage(content=MENU_AGENT_PROMPT),
        HumanMessage(content=query),
    ]
    messages = _menu_tool_loop(messages)
    final_message = messages[-1]
    menu_response = final_message.content or "I couldn't find an answer to that menu question."

    pending = [n for n in state.get("pending_agents", []) if n != "menu_agent_node"]

    return {
        "menu_response": menu_response,
        "menu_messages": messages,
        "pending_agents": pending,
    }


def order_agent_node_sequential(state: StackState) -> dict:
    """Same as agents/order_agent.py's node, minus the Command wrapper."""
    query = state.get("order_query") or state.get("user_query", "")
    identifier = extract_identifier(query)

    if identifier is None:
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
        human_reply = str(human_reply)
        identifier = extract_identifier(human_reply)
        query = human_reply if identifier else f"{query} {human_reply}".strip()

    messages: List[Any] = [
        SystemMessage(content=ORDER_AGENT_PROMPT),
        HumanMessage(
            content=(
                f"User query: {query}\n"
                f"Extracted identifier: {identifier if identifier else 'none found'}"
            )
        ),
    ]
    messages = _order_tool_loop(messages)
    final_message = messages[-1]
    order_response = final_message.content or "I couldn't find an answer to that order question."

    pending = [n for n in state.get("pending_agents", []) if n != "order_agent_node"]

    return {
        "order_response": order_response,
        "order_messages": messages,
        "pending_agents": pending,
    }


# ---------------------------------------------------------------------------
# Build and compile the graph for the chosen mode
# ---------------------------------------------------------------------------
def build_graph(mode: Literal["parallel", "sequential"] = "parallel"):
    if mode not in ("parallel", "sequential"):
        raise ValueError(f"mode must be 'parallel' or 'sequential', got {mode!r}")

    builder = StateGraph(StackState)

    if mode == "parallel":
        builder.add_node("orchestrator_node", orchestrator_node_parallel)
        builder.add_node("menu_agent_node", menu_agent_node_parallel)
        builder.add_node("order_agent_node", order_agent_node_parallel)
        builder.add_node("synthesizer_node", synthesizer_with_memory_node)

        builder.add_edge(START, "orchestrator_node")
        builder.add_edge("synthesizer_node", END)
        # No other static edges needed: orchestrator_node, menu_agent_node,
        # and order_agent_node all route dynamically via Command(goto=...).

    else:  # mode == "sequential"
        builder.add_node("orchestrator_node", orchestrator_node_sequential)
        builder.add_node("menu_agent_node", menu_agent_node_sequential)
        builder.add_node("order_agent_node", order_agent_node_sequential)
        builder.add_node("synthesizer_node", synthesizer_with_memory_node)

        builder.add_edge(START, "orchestrator_node")

        destinations = {
            "menu_agent_node": "menu_agent_node",
            "order_agent_node": "order_agent_node",
            "synthesizer_node": "synthesizer_node",
        }
        builder.add_conditional_edges("orchestrator_node", _route_to_next_pending, destinations)
        builder.add_conditional_edges("menu_agent_node", _route_to_next_pending, destinations)
        builder.add_conditional_edges("order_agent_node", _route_to_next_pending, destinations)

        builder.add_edge("synthesizer_node", END)

    # MemorySaver persists StackState (including the accumulating
    # `messages` list) per thread_id across separate graph.invoke() calls,
    # and is required for order_agent_node's interrupt()/resume flow.
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# Default graph -- override at import time with build_graph(mode="sequential")
# or via the SNACKSTACK_MODE env var read below.
_DEFAULT_MODE = os.environ.get("SNACKSTACK_MODE", "parallel")
graph = build_graph(mode=_DEFAULT_MODE)


if __name__ == "__main__":
    import uuid

    mode = sys.argv[1] if len(sys.argv) > 1 else _DEFAULT_MODE
    demo_graph = build_graph(mode=mode)

    # Same thread_id for both turns -> same MemorySaver checkpoint lineage
    # -> turn 2 resumes with turn 1's `messages` already in state.
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    print(f"=== Running demo in mode={mode!r} ===\n")

    turn_1 = "Is Butter Chicken spicy, and can you check my order ORD1002?"
    result_1 = demo_graph.invoke({"user_query": turn_1}, config=config)
    print(f"Turn 1 query: {turn_1}")
    print(f"Turn 1 response:\n{result_1.get('final_response')}\n")
    print(f"Messages accumulated after turn 1: {len(result_1.get('messages', []))}\n")

    turn_2 = "What about Paneer Tikka -- is that spicy too?"
    result_2 = demo_graph.invoke({"user_query": turn_2}, config=config)
    print(f"Turn 2 query: {turn_2}")
    print(f"Turn 2 response:\n{result_2.get('final_response')}\n")
    print(f"Messages accumulated after turn 2: {len(result_2.get('messages', []))}")
    # -- should be 4 (Human/AI x2), proving turn 1's history persisted
    # into turn 2 via the checkpointer, keyed by the shared thread_id.