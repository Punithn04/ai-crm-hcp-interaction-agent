import logging
from typing import Annotated, TypedDict

from groq import BadRequestError
from langchain_core.messages import AIMessage, AnyMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.orm import Session

from app.agent.llm import get_llm
from app.agent.tools import build_tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the AI assistant embedded in the "Log HCP Interaction" screen of a \
pharmaceutical CRM, built for field representatives visiting Healthcare Professionals (HCPs).

You help the rep log interactions via natural conversation instead of filling a form by hand, look up
HCP history, edit previously logged interactions, suggest follow-up actions, and find marketing
materials or samples to mention. Always use the available tools to perform actions and look up data
rather than guessing. Be concise and professional, the way a life-science field rep would expect.

IMPORTANT: Call at most ONE tool per user message unless the user explicitly asks for multiple
separate actions. As soon as a tool result satisfies the user's request (e.g. the interaction was
logged), immediately reply to the user in plain text summarizing what you did and STOP — do not
call further tools "just in case" or to explore extra information the user did not ask for."""


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_agent_graph(db: Session, ctx: dict):
    tools = build_tools(db, ctx)
    llm_with_tools = get_llm().bind_tools(tools)

    def call_model(state: AgentState) -> AgentState:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT), *messages]
        try:
            response = llm_with_tools.invoke(messages)
        except BadRequestError:
            logger.exception("Groq tool-call generation failed; falling back to a plain text reply")
            response = AIMessage(
                content="I completed part of that request but hit an issue generating a follow-up "
                "action. Let me know if you'd like me to try again or take a different action."
            )
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", ToolNode(tools))
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()
