#!/usr/bin/env python3
"""
Supervisor Multi-Agent Workflow with LangGraph.

A supervisor agent that routes tasks to specialized worker agents.

Usage:
    python supervisor_workflow.py

Environment variables:
    GOOGLE_API_KEY: Your Google API key for Gemini
"""

import os
from typing import Literal, Annotated
from operator import add
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# ============================================================================
# Pydantic Models
# ============================================================================

class RouteDecision(BaseModel):
    """Decision made by supervisor."""
    next: Literal["researcher", "writer", "analyst", "FINISH"]
    reason: str = Field(description="Brief reason for routing decision")


class WorkflowResponse(BaseModel):
    """Final workflow response."""
    answer: str
    workers_used: list[str]
    thread_id: str


# ============================================================================
# State Definition
# ============================================================================

class SupervisorState(MessagesState):
    """State for supervisor workflow."""
    next: str
    workers_used: Annotated[list[str], add]
    iteration: int


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


llm = None


def init_llm():
    """Initialize LLM globally."""
    global llm
    llm = get_llm()


# ============================================================================
# Supervisor Node
# ============================================================================

def supervisor_node(state: SupervisorState) -> dict:
    """Supervisor decides which worker to route to."""
    messages = state["messages"]
    workers_used = state.get("workers_used", [])
    iteration = state.get("iteration", 0)

    # Prevent infinite loops
    if iteration >= 5:
        return {"next": "FINISH"}

    system_prompt = f"""You are a supervisor managing a team of workers:

WORKERS:
- researcher: Gathers information, facts, and data. Use for research questions.
- writer: Creates written content, drafts, and summaries. Use for content creation.
- analyst: Analyzes data, identifies patterns, provides insights. Use for analysis tasks.
- FINISH: Task is complete. Use when the user's request has been fully addressed.

CONTEXT:
- Workers already used: {', '.join(workers_used) if workers_used else 'None'}
- Current iteration: {iteration}

INSTRUCTIONS:
1. Review the conversation and latest worker outputs
2. Decide which worker should act next, or if task is complete
3. If research is needed, use researcher
4. If content needs to be written, use writer
5. If analysis is needed, use analyst
6. Once the user's question is fully answered, select FINISH

Respond with your routing decision."""

    response = llm.with_structured_output(RouteDecision).invoke([
        SystemMessage(content=system_prompt),
        *messages
    ])

    return {
        "next": response.next,
        "iteration": iteration + 1
    }


# ============================================================================
# Worker Nodes
# ============================================================================

def researcher_node(state: SupervisorState) -> dict:
    """Researcher gathers information and facts."""
    messages = state["messages"]

    system_prompt = """You are a research specialist. Your job is to:
1. Gather relevant information and facts
2. Find data to support answers
3. Identify key points and details
4. Provide well-sourced information

Be thorough but concise. Present findings clearly."""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        *messages,
        HumanMessage(content="Please research and gather relevant information for this task.")
    ])

    return {
        "messages": [AIMessage(content=f"[Researcher]\n{response.content}")],
        "workers_used": ["researcher"]
    }


def writer_node(state: SupervisorState) -> dict:
    """Writer creates written content."""
    messages = state["messages"]

    system_prompt = """You are a professional writer. Your job is to:
1. Create clear, well-structured content
2. Synthesize information into readable prose
3. Adapt tone and style to the audience
4. Produce polished, publication-ready text

Focus on clarity and engagement."""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        *messages,
        HumanMessage(content="Please write content based on the available information.")
    ])

    return {
        "messages": [AIMessage(content=f"[Writer]\n{response.content}")],
        "workers_used": ["writer"]
    }


def analyst_node(state: SupervisorState) -> dict:
    """Analyst provides data analysis and insights."""
    messages = state["messages"]

    system_prompt = """You are a data analyst. Your job is to:
1. Analyze data and information
2. Identify patterns and trends
3. Draw meaningful conclusions
4. Provide actionable insights

Be analytical and evidence-based."""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        *messages,
        HumanMessage(content="Please analyze and provide insights on this topic.")
    ])

    return {
        "messages": [AIMessage(content=f"[Analyst]\n{response.content}")],
        "workers_used": ["analyst"]
    }


# ============================================================================
# Routing Function
# ============================================================================

def route_supervisor(state: SupervisorState) -> str:
    """Route based on supervisor's decision."""
    next_node = state.get("next", "FINISH")

    if next_node == "FINISH":
        return END

    return next_node


# ============================================================================
# Graph Builder
# ============================================================================

def build_supervisor_workflow(checkpointer=None):
    """Build the supervisor multi-agent workflow."""
    init_llm()

    builder = StateGraph(SupervisorState)

    # Add nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("writer", writer_node)
    builder.add_node("analyst", analyst_node)

    # Add edges
    builder.add_edge(START, "supervisor")

    # Conditional routing from supervisor
    builder.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "researcher": "researcher",
            "writer": "writer",
            "analyst": "analyst",
            END: END
        }
    )

    # Workers return to supervisor
    builder.add_edge("researcher", "supervisor")
    builder.add_edge("writer", "supervisor")
    builder.add_edge("analyst", "supervisor")

    return builder.compile(checkpointer=checkpointer)


# ============================================================================
# Workflow Interface
# ============================================================================

class SupervisorWorkflow:
    """Supervisor workflow with conversation memory."""

    def __init__(self, thread_id: str = "default"):
        self.thread_id = thread_id
        self.checkpointer = InMemorySaver()
        self.graph = build_supervisor_workflow(self.checkpointer)

    def run(self, task: str) -> WorkflowResponse:
        """Run a task through the workflow."""
        config = {"configurable": {"thread_id": self.thread_id}}

        result = self.graph.invoke(
            {
                "messages": [HumanMessage(content=task)],
                "workers_used": [],
                "iteration": 0
            },
            config
        )

        # Get final message
        last_message = result["messages"][-1]
        workers = result.get("workers_used", [])

        return WorkflowResponse(
            answer=last_message.content,
            workers_used=workers,
            thread_id=self.thread_id
        )

    def stream_run(self, task: str):
        """Stream workflow execution."""
        config = {"configurable": {"thread_id": self.thread_id}}

        for event in self.graph.stream(
            {
                "messages": [HumanMessage(content=task)],
                "workers_used": [],
                "iteration": 0
            },
            config,
            stream_mode="values"
        ):
            if event.get("messages"):
                last_msg = event["messages"][-1]
                if hasattr(last_msg, "content"):
                    yield {
                        "content": last_msg.content,
                        "workers_used": event.get("workers_used", [])
                    }

    def clear_history(self):
        """Clear by starting new thread."""
        import uuid
        self.thread_id = str(uuid.uuid4())


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """Interactive CLI for supervisor workflow."""
    print("Supervisor Workflow initialized.")
    print("Workers: researcher, writer, analyst")
    print("Type 'quit' to exit, 'clear' to reset.\n")

    workflow = SupervisorWorkflow()

    while True:
        try:
            user_input = input("Task: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("Goodbye!")
                break

            if user_input.lower() == "clear":
                workflow.clear_history()
                print("Workflow cleared.\n")
                continue

            print("\nProcessing...\n")

            # Stream results
            for update in workflow.stream_run(user_input):
                print(f"{update['content']}\n")
                print(f"Workers used so far: {', '.join(update['workers_used'])}\n")
                print("-" * 40)

            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
