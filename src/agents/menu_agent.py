"""
agents/menu_agent.py
----------------------
Menu Agent for SnackStack.

Binds the search_menu_catalog tool to the LLM, runs a bounded tool-calling
loop (the LLM may call the tool, read results, and decide to call it again
or answer -- capped at MAX_ITERATIONS so a stuck agent can't loop forever),
and hands off to the Synthesizer node via a LangGraph Command.

Expected graph state (a shared TypedDict defined at the graph level) is
expected to carry at least:
    user_query:    str            -- original user message
    menu_query:    Optional[str]  -- sub-query from the Orchestrator, if any
    menu_response: Optional[str]  -- written here by this node
"""

import os
import sys
from typing import Any, Dict, List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Command

from agents.prompts import MENU_AGENT_PROMPT
from tools.menu_tools import search_menu_catalog

MAX_ITERATIONS = 5

MENU_TOOLS = [search_menu_catalog]
_TOOLS_BY_NAME = {t.name: t for t in MENU_TOOLS}

_MODEL_NAME = os.environ.get("MENU_AGENT_MODEL", "gpt-4o-mini")
_llm = ChatOpenAI(model=_MODEL_NAME, temperature=0)
_llm_with_tools = _llm.bind_tools(MENU_TOOLS)


def _run_tool_calling_loop(messages: List[Any]) -> List[Any]:
    """Run the bind-tools -> call -> execute -> repeat loop, capped at
    MAX_ITERATIONS. Mutates and returns the running message list.

    If the cap is hit while the model still wants to call tools, one
    final untooled nudge forces a concrete answer instead of returning
    an empty/incomplete response.
    """
    for _ in range(MAX_ITERATIONS):
        response: AIMessage = _llm_with_tools.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            return messages  # Model gave a final answer -- done.

        for call in response.tool_calls:
            tool = _TOOLS_BY_NAME.get(call["name"])
            if tool is None:
                output = f"Error: unknown tool '{call['name']}'"
            else:
                try:
                    output = tool.invoke(call["args"])
                except Exception as exc:  # keep the loop alive on tool errors
                    output = f"Error running tool '{call['name']}': {exc}"
            messages.append(ToolMessage(content=str(output), tool_call_id=call["id"]))

    # Hit MAX_ITERATIONS while the model was still calling tools -- force closure.
    messages.append(
        HumanMessage(
            content=(
                "You've reached the maximum number of tool calls. "
                "Give your best final answer now, based only on the tool "
                "results above, without calling any more tools."
            )
        )
    )
    final_response = _llm.invoke(messages)  # note: no tools bound here
    messages.append(final_response)
    return messages


def menu_agent_node(state: Dict[str, Any]) -> Command:
    """LangGraph node: answer the menu-related portion of the user's query.

    Reads `menu_query` (falling back to `user_query`) from state, runs the
    tool-calling loop, and routes to the Synthesizer with the result.
    """
    query = state.get("menu_query") or state.get("user_query", "")

    messages: List[Any] = [
        SystemMessage(content=MENU_AGENT_PROMPT),
        HumanMessage(content=query),
    ]

    messages = _run_tool_calling_loop(messages)

    final_message = messages[-1]
    menu_response = final_message.content or "I couldn't find an answer to that menu question."

    return Command(
        goto="synthesizer_node",
        update={
            "menu_response": menu_response,
            "menu_messages": messages,
        },
    )


if __name__ == "__main__":
    # Quick manual smoke test (bypasses the graph, calls the node directly)
    test_state = {"user_query": "Something creamy and non-vegetarian under 400 rupees"}
    result = menu_agent_node(test_state)
    print(f"goto: {result.goto}")
    print(f"menu_response:\n{result.update['menu_response']}")
    test_state = {"user_query": "Hello, how are you?"}
    result = menu_agent_node(test_state)
    print(f"goto: {result.goto}")
    print(f"menu_response:\n{result.update['menu_response']}")
    