#!/usr/bin/env python3
"""
Orchestrator Multi-Agent Workflow with LangGraph.

Central orchestrator that plans and coordinates specialized agents
for complex multi-step tasks.

Usage:
    python orchestrator_workflow.py

Environment variables:
    GOOGLE_API_KEY: Your Google API key for Gemini
"""

import os
from typing import Annotated, Literal
from operator import add
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# ============================================================================
# Pydantic Models
# ============================================================================

class TaskPlan(BaseModel):
    """Plan created by orchestrator."""
    steps: list[str] = Field(description="List of steps to complete the task")
    agents_needed: list[str] = Field(description="Agents required for each step")


class StepResult(BaseModel):
    """Result of executing a step."""
    step: str
    agent: str
    output: str
    success: bool = True


class OrchestratorResponse(BaseModel):
    """Final orchestrator response."""
    answer: str
    plan: list[str]
    results: list[str]
    thread_id: str


# ============================================================================
# State Definition
# ============================================================================

class OrchestratorState(MessagesState):
    """State for orchestrator workflow."""
    plan: list[str]
    agents_for_steps: list[str]
    current_step: int
    step_results: Annotated[list[str], add]
    task_complete: bool


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
# Orchestrator Nodes
# ============================================================================

def planner_node(state: OrchestratorState) -> dict:
    """Create execution plan for the task."""
    messages = state["messages"]

    system_prompt = """You are a task planner. Create a step-by-step plan to complete the user's request.

AVAILABLE AGENTS:
- researcher: Gathers information, facts, data, and research
- writer: Creates written content, drafts, articles, summaries
- reviewer: Reviews content for quality, accuracy, completeness
- analyst: Analyzes data, identifies patterns, provides insights

INSTRUCTIONS:
1. Break down the task into clear, actionable steps
2. Assign the most appropriate agent to each step
3. Order steps logically (research before writing, writing before review)
4. Keep plans focused and efficient (3-6 steps typically)

Create a plan with steps and agent assignments."""

    response = llm.with_structured_output(TaskPlan).invoke([
        SystemMessage(content=system_prompt),
        *messages
    ])

    return {
        "plan": response.steps,
        "agents_for_steps": response.agents_needed,
        "current_step": 0,
        "task_complete": False
    }


def executor_node(state: OrchestratorState) -> dict:
    """Execute the current step with the assigned agent."""
    plan = state["plan"]
    agents = state["agents_for_steps"]
    current = state["current_step"]
    previous_results = state.get("step_results", [])

    if current >= len(plan):
        return {"task_complete": True}

    step = plan[current]
    agent = agents[current] if current < len(agents) else "researcher"

    # Build context from previous steps
    context = ""
    if previous_results:
        context = "\n\nPrevious step results:\n" + "\n---\n".join(previous_results)

    # Get agent-specific prompt
    agent_prompts = {
        "researcher": """You are a research specialist. Your task:
1. Gather relevant information and facts
2. Find supporting data and evidence
3. Identify key points
Be thorough and cite sources when possible.""",

        "writer": """You are a professional writer. Your task:
1. Create clear, well-structured content
2. Use appropriate tone and style
3. Make content engaging and readable
Focus on quality and clarity.""",

        "reviewer": """You are a content reviewer. Your task:
1. Check for accuracy and completeness
2. Identify areas for improvement
3. Ensure quality standards are met
Be constructive and thorough.""",

        "analyst": """You are a data analyst. Your task:
1. Analyze information and data
2. Identify patterns and insights
3. Draw meaningful conclusions
Be analytical and evidence-based."""
    }

    prompt = agent_prompts.get(agent, agent_prompts["researcher"])

    response = llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=f"""Task: {step}

Original request: {state['messages'][0].content}
{context}

Please complete this step.""")
    ])

    result = f"[{agent.upper()} - Step {current + 1}]\n{response.content}"

    return {
        "step_results": [result],
        "current_step": current + 1,
        "messages": [AIMessage(content=result)]
    }


def should_continue(state: OrchestratorState) -> str:
    """Check if more steps remain."""
    if state.get("task_complete"):
        return "synthesizer"

    current = state.get("current_step", 0)
    plan = state.get("plan", [])

    if current >= len(plan):
        return "synthesizer"

    return "executor"


def synthesizer_node(state: OrchestratorState) -> dict:
    """Synthesize all results into final output."""
    messages = state["messages"]
    results = state.get("step_results", [])
    plan = state.get("plan", [])

    results_text = "\n\n---\n\n".join(results)

    system_prompt = """You are a synthesizer. Your job is to:
1. Combine the results from all steps into a coherent response
2. Ensure the final output fully addresses the original request
3. Present information clearly and professionally
4. Remove redundancy while keeping important details

Create a polished final response."""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"""Original request: {messages[0].content}

Steps completed: {', '.join(plan)}

Step results:
{results_text}

Please synthesize these results into a final response.""")
    ])

    return {
        "messages": [AIMessage(content=response.content)],
        "task_complete": True
    }


# ============================================================================
# Graph Builder
# ============================================================================

def build_orchestrator_workflow(checkpointer=None):
    """Build the orchestrator multi-agent workflow."""
    init_llm()

    builder = StateGraph(OrchestratorState)

    # Add nodes
    builder.add_node("planner", planner_node)
    builder.add_node("executor", executor_node)
    builder.add_node("synthesizer", synthesizer_node)

    # Add edges
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "executor")

    # Conditional edge from executor
    builder.add_conditional_edges(
        "executor",
        should_continue,
        {
            "executor": "executor",
            "synthesizer": "synthesizer"
        }
    )

    builder.add_edge("synthesizer", END)

    return builder.compile(checkpointer=checkpointer)


# ============================================================================
# Workflow Interface
# ============================================================================

class OrchestratorWorkflow:
    """Orchestrator workflow with conversation memory."""

    def __init__(self, thread_id: str = "default"):
        self.thread_id = thread_id
        self.checkpointer = InMemorySaver()
        self.graph = build_orchestrator_workflow(self.checkpointer)

    def run(self, task: str) -> OrchestratorResponse:
        """Run a task through the orchestrator."""
        config = {"configurable": {"thread_id": self.thread_id}}

        result = self.graph.invoke(
            {
                "messages": [HumanMessage(content=task)],
                "plan": [],
                "agents_for_steps": [],
                "current_step": 0,
                "step_results": [],
                "task_complete": False
            },
            config
        )

        # Get final message
        last_message = result["messages"][-1]

        return OrchestratorResponse(
            answer=last_message.content,
            plan=result.get("plan", []),
            results=result.get("step_results", []),
            thread_id=self.thread_id
        )

    def stream_run(self, task: str):
        """Stream orchestrator execution."""
        config = {"configurable": {"thread_id": self.thread_id}}

        for event in self.graph.stream(
            {
                "messages": [HumanMessage(content=task)],
                "plan": [],
                "agents_for_steps": [],
                "current_step": 0,
                "step_results": [],
                "task_complete": False
            },
            config,
            stream_mode="values"
        ):
            yield {
                "plan": event.get("plan", []),
                "current_step": event.get("current_step", 0),
                "step_results": event.get("step_results", []),
                "messages": [m.content for m in event.get("messages", []) if hasattr(m, "content")]
            }

    def clear_history(self):
        """Clear by starting new thread."""
        import uuid
        self.thread_id = str(uuid.uuid4())


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """Interactive CLI for orchestrator workflow."""
    print("Orchestrator Workflow initialized.")
    print("Agents: researcher, writer, reviewer, analyst")
    print("The orchestrator plans and coordinates multi-step tasks.")
    print("Type 'quit' to exit, 'clear' to reset.\n")

    workflow = OrchestratorWorkflow()

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

            print("\nOrchestrator is planning and executing...\n")

            # Stream results
            for update in workflow.stream_run(user_input):
                if update.get("plan") and update["current_step"] == 0:
                    print("Plan created:")
                    for i, step in enumerate(update["plan"], 1):
                        print(f"  {i}. {step}")
                    print()

                if update.get("step_results"):
                    latest = update["step_results"][-1] if update["step_results"] else ""
                    if latest:
                        print(f"{latest}\n")
                        print("-" * 40)

            # Final result
            print("\n" + "=" * 40)
            print("FINAL RESULT:")
            print("=" * 40)
            response = workflow.run(user_input)
            print(response.answer)
            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
