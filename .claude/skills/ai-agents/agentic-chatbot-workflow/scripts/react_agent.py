#!/usr/bin/env python3
"""
ReAct Agent with LangGraph.

A single agent that reasons and acts using tools.
Implements the ReAct (Reasoning + Acting) pattern.

Usage:
    python react_agent.py

Environment variables:
    GOOGLE_API_KEY: Your Google API key for Gemini
"""

import os
from typing import Annotated
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# ============================================================================
# Pydantic Models
# ============================================================================

class AgentResponse(BaseModel):
    """Schema for agent response."""
    answer: str
    tools_used: list[str] = Field(default_factory=list)
    thread_id: str


class CalculationResult(BaseModel):
    """Schema for calculation results."""
    expression: str
    result: float
    steps: list[str] = Field(default_factory=list)


# ============================================================================
# Tools
# ============================================================================

@tool
def search_web(query: str) -> str:
    """Search the web for information.

    Use this when you need current information or facts not in your knowledge.

    Args:
        query: The search query to execute
    """
    # Placeholder - integrate with actual search API
    return f"Search results for '{query}': [Simulated search results would appear here]"


@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression.

    Use this for any calculations, math problems, or numerical operations.

    Args:
        expression: Math expression like '2 + 2', 'sqrt(16)', or '15 * 0.2'
    """
    import math

    # Safe evaluation with limited builtins
    allowed = {
        "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "pow": pow, "sqrt": math.sqrt,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "log": math.log, "log10": math.log10,
        "pi": math.pi, "e": math.e
    }

    try:
        result = eval(expression, {"__builtins__": {}}, allowed)
        return f"Result: {result}"
    except Exception as e:
        return f"Error evaluating expression: {e}"


@tool
def get_current_time() -> str:
    """Get the current date and time.

    Use this when the user asks about the current time, date, or day.
    """
    from datetime import datetime
    now = datetime.now()
    return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S')}"


@tool
def analyze_text(text: str, analysis_type: str = "summary") -> str:
    """Analyze text content.

    Use this for text analysis tasks like summarization or sentiment.

    Args:
        text: The text to analyze
        analysis_type: Type of analysis - 'summary', 'sentiment', or 'keywords'
    """
    if analysis_type == "summary":
        return f"Summary of text ({len(text)} chars): [Summary would be generated here]"
    elif analysis_type == "sentiment":
        return "Sentiment: Neutral (placeholder - integrate with actual sentiment analysis)"
    elif analysis_type == "keywords":
        words = text.split()[:5]
        return f"Keywords: {', '.join(words)}"
    else:
        return f"Unknown analysis type: {analysis_type}"


# ============================================================================
# LLM Setup
# ============================================================================

def get_llm():
    """Initialize Gemini chat model."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=os.environ.get("GOOGLE_API_KEY"),
        temperature=0.7
    )


# ============================================================================
# ReAct Agent (Using Prebuilt)
# ============================================================================

def create_simple_react_agent():
    """Create a ReAct agent using the prebuilt helper."""
    llm = get_llm()
    tools = [search_web, calculate, get_current_time, analyze_text]

    # System prompt for the agent
    system_prompt = """You are a helpful AI assistant with access to tools.

When answering questions:
1. Think about whether you need to use a tool
2. If yes, use the appropriate tool and incorporate the results
3. If no, answer directly from your knowledge
4. Always explain your reasoning

Be concise but thorough in your responses."""

    agent = create_react_agent(
        llm,
        tools,
        prompt=system_prompt
    )

    return agent


# ============================================================================
# ReAct Agent (Custom Graph)
# ============================================================================

class ReActState(MessagesState):
    """State for custom ReAct agent."""
    tools_called: list[str]


def build_custom_react_agent():
    """Build a custom ReAct agent graph for more control."""
    llm = get_llm()
    tools = [search_web, calculate, get_current_time, analyze_text]
    tool_node = ToolNode(tools)

    def call_model(state: ReActState) -> dict:
        """Call the LLM with tool binding."""
        messages = state["messages"]

        # Add system message if not present
        if not messages or not isinstance(messages[0], SystemMessage):
            system = SystemMessage(content="""You are a helpful AI assistant.
Use tools when needed to answer questions accurately.
Always explain your reasoning.""")
            messages = [system] + list(messages)

        # Bind tools and invoke
        response = llm.bind_tools(tools).invoke(messages)

        # Track tools called
        tools_called = state.get("tools_called", [])
        if response.tool_calls:
            tools_called = tools_called + [tc["name"] for tc in response.tool_calls]

        return {"messages": [response], "tools_called": tools_called}

    def should_continue(state: ReActState) -> str:
        """Determine if we should continue to tools or end."""
        last_message = state["messages"][-1]

        # If there are tool calls, route to tools
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"

        return END

    # Build graph
    builder = StateGraph(ReActState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", tool_node)

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        END: END
    })
    builder.add_edge("tools", "agent")

    return builder.compile(checkpointer=InMemorySaver())


# ============================================================================
# Agent Interface
# ============================================================================

class ReActAgent:
    """ReAct agent with conversation memory."""

    def __init__(self, thread_id: str = "default", use_custom: bool = False):
        self.thread_id = thread_id
        self.checkpointer = InMemorySaver()

        if use_custom:
            self.graph = build_custom_react_agent()
        else:
            agent = create_simple_react_agent()
            self.graph = agent

    def chat(self, message: str) -> AgentResponse:
        """Send a message and get a response."""
        config = {"configurable": {"thread_id": self.thread_id}}

        result = self.graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config
        )

        # Extract response
        last_message = result["messages"][-1]
        tools_used = result.get("tools_called", [])

        return AgentResponse(
            answer=last_message.content,
            tools_used=tools_used,
            thread_id=self.thread_id
        )

    def stream_chat(self, message: str):
        """Stream response token by token."""
        config = {"configurable": {"thread_id": self.thread_id}}

        for event in self.graph.stream(
            {"messages": [HumanMessage(content=message)]},
            config,
            stream_mode="values"
        ):
            if event.get("messages"):
                last_msg = event["messages"][-1]
                if hasattr(last_msg, "content") and last_msg.content:
                    yield last_msg.content

    def clear_history(self):
        """Clear conversation by starting new thread."""
        import uuid
        self.thread_id = str(uuid.uuid4())


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """Interactive CLI for ReAct agent."""
    print("ReAct Agent initialized. Type 'quit' to exit, 'clear' to reset.\n")

    agent = ReActAgent(use_custom=True)

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("Goodbye!")
                break

            if user_input.lower() == "clear":
                agent.clear_history()
                print("Conversation cleared.\n")
                continue

            # Get response
            response = agent.chat(user_input)

            print(f"\nAgent: {response.answer}")

            if response.tools_used:
                print(f"\nTools used: {', '.join(response.tools_used)}")

            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
