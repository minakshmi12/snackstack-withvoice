"""Shared state schema for the SnackStack LangGraph pipeline."""

from typing import Annotated, Any, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class StackState(TypedDict, total=False):
    user_query: str
    messages: Annotated[List[BaseMessage], add_messages]
    agents: List[str]
    pending_agents: List[str]
    menu_query: Optional[str]
    order_query: Optional[str]
    menu_response: Optional[str]
    order_response: Optional[str]
    menu_messages: Optional[List[Any]]
    order_messages: Optional[List[Any]]
    final_response: Optional[str]
