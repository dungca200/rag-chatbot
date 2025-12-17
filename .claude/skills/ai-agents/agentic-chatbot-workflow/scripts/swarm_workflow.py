#!/usr/bin/env python3
"""
Swarm Multi-Agent Workflow with LangGraph.

Peer-to-peer agent handoffs without central coordination.
Agents hand off to each other based on conversation context.

Usage:
    python swarm_workflow.py

Environment variables:
    GOOGLE_API_KEY: Your Google API key for Gemini
"""

import os
from typing import Annotated, Literal
from operator import add
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# ============================================================================
# Pydantic Models
# ============================================================================

class SwarmResponse(BaseModel):
    """Response from swarm workflow."""
    answer: str
    agents_involved: list[str]
    thread_id: str


class HandoffRequest(BaseModel):
    """Request to hand off to another agent."""
    target_agent: str
    reason: str
    context: str = ""


# ============================================================================
# State Definition
# ============================================================================

class SwarmState(MessagesState):
    """State for swarm workflow."""
    current_agent: str
    agents_involved: Annotated[list[str], add]
    handoff_count: int


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
# Handoff Tools
# ============================================================================

@tool
def handoff_to_support(reason: str) -> str:
    """Transfer conversation to support agent.

    Use when the user has technical issues, bugs, or needs help using features.

    Args:
        reason: Brief reason for the handoff
    """
    return f"__HANDOFF__:support:{reason}"


@tool
def handoff_to_sales(reason: str) -> str:
    """Transfer conversation to sales agent.

    Use when the user asks about pricing, plans, purchases, or upgrades.

    Args:
        reason: Brief reason for the handoff
    """
    return f"__HANDOFF__:sales:{reason}"


@tool
def handoff_to_billing(reason: str) -> str:
    """Transfer conversation to billing agent.

    Use when the user has questions about invoices, payments, or refunds.

    Args:
        reason: Brief reason for the handoff
    """
    return f"__HANDOFF__:billing:{reason}"


# ============================================================================
# Agent-Specific Tools
# ============================================================================

@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for support articles.

    Args:
        query: Search query for knowledge base
    """
    # Placeholder - integrate with actual KB
    return f"Knowledge base results for '{query}': [Article 1: Troubleshooting guide, Article 2: FAQ]"


@tool
def check_system_status() -> str:
    """Check current system status and known issues."""
    return "System Status: All systems operational. No known issues."


@tool
def get_pricing_info(plan: str = "all") -> str:
    """Get pricing information for plans.

    Args:
        plan: Specific plan name or 'all' for all plans
    """
    pricing = {
        "starter": "$9/month",
        "professional": "$29/month",
        "enterprise": "Custom pricing"
    }
    if plan == "all":
        return f"Pricing: {pricing}"
    return f"{plan.title()} plan: {pricing.get(plan, 'Plan not found')}"


@tool
def check_inventory(product: str) -> str:
    """Check product inventory availability.

    Args:
        product: Product name to check
    """
    return f"Inventory for {product}: In stock (15 units available)"


@tool
def get_invoice(invoice_id: str) -> str:
    """Retrieve invoice details.

    Args:
        invoice_id: Invoice ID to look up
    """
    return f"Invoice {invoice_id}: Amount $99.00, Status: Paid, Date: 2024-01-15"


@tool
def process_refund(invoice_id: str, reason: str) -> str:
    """Initiate a refund request.

    Args:
        invoice_id: Invoice ID for refund
        reason: Reason for refund request
    """
    return f"Refund request initiated for invoice {invoice_id}. Reason: {reason}. Processing time: 3-5 business days."


# ============================================================================
# Agent Nodes
# ============================================================================

def create_agent_node(agent_name: str, system_prompt: str, tools: list):
    """Create an agent node with specific tools and prompt."""

    def agent_node(state: SwarmState) -> dict:
        messages = state["messages"]

        # Bind tools to LLM
        llm_with_tools = llm.bind_tools(tools)

        response = llm_with_tools.invoke([
            SystemMessage(content=system_prompt),
            *messages
        ])

        return {
            "messages": [response],
            "current_agent": agent_name,
            "agents_involved": [agent_name]
        }

    return agent_node


# Support Agent
support_tools = [search_knowledge_base, check_system_status, handoff_to_sales, handoff_to_billing]
support_prompt = """You are a friendly support agent. Your job is to:
1. Help users with technical issues and questions
2. Search the knowledge base for solutions
3. Check system status for known issues
4. Hand off to sales for pricing questions
5. Hand off to billing for payment issues

Be helpful and patient. Resolve issues when possible."""

support_node = create_agent_node("support", support_prompt, support_tools)


# Sales Agent
sales_tools = [get_pricing_info, check_inventory, handoff_to_support, handoff_to_billing]
sales_prompt = """You are a helpful sales agent. Your job is to:
1. Provide pricing information
2. Explain plan features and benefits
3. Help users choose the right plan
4. Check product availability
5. Hand off to support for technical questions
6. Hand off to billing for payment issues

Be informative and help users make good decisions."""

sales_node = create_agent_node("sales", sales_prompt, sales_tools)


# Billing Agent
billing_tools = [get_invoice, process_refund, handoff_to_support, handoff_to_sales]
billing_prompt = """You are a professional billing agent. Your job is to:
1. Look up invoice details
2. Process refund requests
3. Answer billing questions
4. Hand off to support for technical issues
5. Hand off to sales for pricing/plan questions

Be accurate and helpful with financial matters."""

billing_node = create_agent_node("billing", billing_prompt, billing_tools)


# ============================================================================
# Tool Execution and Routing
# ============================================================================

def create_tool_node():
    """Create tool node that handles all agent tools."""
    all_tools = support_tools + sales_tools + billing_tools
    # Remove duplicates
    unique_tools = list({t.name: t for t in all_tools}.values())
    return ToolNode(unique_tools)


def parse_handoff(content: str) -> tuple[str, str] | None:
    """Parse handoff from tool result."""
    if "__HANDOFF__:" in content:
        parts = content.split(":")
        if len(parts) >= 3:
            return parts[1], parts[2]
    return None


def route_after_tools(state: SwarmState) -> str:
    """Route after tool execution - check for handoffs."""
    messages = state["messages"]
    handoff_count = state.get("handoff_count", 0)

    # Prevent infinite handoff loops
    if handoff_count >= 5:
        return "finalize"

    # Check last message for handoff
    for msg in reversed(messages[-3:]):
        if hasattr(msg, "content"):
            handoff = parse_handoff(str(msg.content))
            if handoff:
                target, reason = handoff
                return target

    # Check if agent wants to continue
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return "finalize"


def route_after_agent(state: SwarmState) -> str:
    """Route after agent - to tools or end."""
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return "finalize"


def finalize_node(state: SwarmState) -> dict:
    """Generate final response."""
    messages = state["messages"]
    current_agent = state.get("current_agent", "support")

    # Get last AI message that isn't a tool call
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
            return {"messages": []}  # Keep existing message

    # If no good message, generate one
    response = llm.invoke([
        SystemMessage(content=f"You are the {current_agent} agent. Provide a final helpful response."),
        *messages
    ])

    return {"messages": [response]}


# ============================================================================
# Graph Builder
# ============================================================================

def build_swarm_workflow(checkpointer=None):
    """Build the swarm multi-agent workflow."""
    init_llm()

    builder = StateGraph(SwarmState)

    # Add agent nodes
    builder.add_node("support", support_node)
    builder.add_node("sales", sales_node)
    builder.add_node("billing", billing_node)

    # Add tool node
    builder.add_node("tools", create_tool_node())

    # Add finalize node
    builder.add_node("finalize", finalize_node)

    # Start with support as default
    builder.add_edge(START, "support")

    # Agent routing
    for agent in ["support", "sales", "billing"]:
        builder.add_conditional_edges(
            agent,
            route_after_agent,
            {
                "tools": "tools",
                "finalize": "finalize"
            }
        )

    # Tool routing (can hand off to any agent)
    builder.add_conditional_edges(
        "tools",
        route_after_tools,
        {
            "support": "support",
            "sales": "sales",
            "billing": "billing",
            "tools": "tools",
            "finalize": "finalize"
        }
    )

    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)


# ============================================================================
# Workflow Interface
# ============================================================================

class SwarmWorkflow:
    """Swarm workflow with conversation memory."""

    def __init__(self, thread_id: str = "default", start_agent: str = "support"):
        self.thread_id = thread_id
        self.start_agent = start_agent
        self.checkpointer = InMemorySaver()
        self.graph = build_swarm_workflow(self.checkpointer)

    def chat(self, message: str) -> SwarmResponse:
        """Send a message through the swarm."""
        config = {"configurable": {"thread_id": self.thread_id}}

        result = self.graph.invoke(
            {
                "messages": [HumanMessage(content=message)],
                "current_agent": self.start_agent,
                "agents_involved": [],
                "handoff_count": 0
            },
            config
        )

        # Get final message
        last_message = result["messages"][-1]
        agents = list(set(result.get("agents_involved", [])))

        return SwarmResponse(
            answer=last_message.content if hasattr(last_message, "content") else str(last_message),
            agents_involved=agents,
            thread_id=self.thread_id
        )

    def stream_chat(self, message: str):
        """Stream swarm execution."""
        config = {"configurable": {"thread_id": self.thread_id}}

        for event in self.graph.stream(
            {
                "messages": [HumanMessage(content=message)],
                "current_agent": self.start_agent,
                "agents_involved": [],
                "handoff_count": 0
            },
            config,
            stream_mode="values"
        ):
            if event.get("messages"):
                last_msg = event["messages"][-1]
                if hasattr(last_msg, "content") and last_msg.content:
                    yield {
                        "content": last_msg.content,
                        "current_agent": event.get("current_agent", "unknown"),
                        "agents_involved": event.get("agents_involved", [])
                    }

    def clear_history(self):
        """Clear by starting new thread."""
        import uuid
        self.thread_id = str(uuid.uuid4())


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """Interactive CLI for swarm workflow."""
    print("Swarm Workflow initialized.")
    print("Agents: support, sales, billing")
    print("Agents hand off to each other as needed.")
    print("Type 'quit' to exit, 'clear' to reset.\n")

    workflow = SwarmWorkflow()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("Goodbye!")
                break

            if user_input.lower() == "clear":
                workflow.clear_history()
                print("Conversation cleared.\n")
                continue

            # Get response
            response = workflow.chat(user_input)

            print(f"\nAgent: {response.answer}")
            print(f"\nAgents involved: {', '.join(response.agents_involved)}")
            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
