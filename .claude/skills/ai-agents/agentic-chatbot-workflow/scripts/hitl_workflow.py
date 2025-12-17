#!/usr/bin/env python3
"""
Human-in-the-Loop (HITL) Workflow with LangGraph.

Demonstrates patterns for human approval, review, and intervention
in agent workflows.

Usage:
    python hitl_workflow.py

Environment variables:
    GOOGLE_API_KEY: Your Google API key for Gemini
"""

import os
from typing import Annotated, Literal, Optional
from operator import add
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import InMemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


# ============================================================================
# Pydantic Models
# ============================================================================

class ApprovalRequest(BaseModel):
    """Request for human approval."""
    action: str
    details: str
    risk_level: Literal["low", "medium", "high"]


class ApprovalResponse(BaseModel):
    """Response from human approval."""
    approved: bool
    feedback: str = ""
    modified_content: Optional[str] = None


class HITLResponse(BaseModel):
    """Final HITL workflow response."""
    answer: str
    approvals_requested: int
    approvals_granted: int
    thread_id: str


# ============================================================================
# State Definition
# ============================================================================

class HITLState(MessagesState):
    """State for HITL workflow."""
    pending_action: Optional[dict]
    approvals_requested: int
    approvals_granted: int
    draft_content: str
    action_type: str


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
# Sensitive Tools (Require Approval)
# ============================================================================

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to a recipient.

    Args:
        to: Email recipient
        subject: Email subject
        body: Email body content
    """
    # Placeholder - would integrate with email service
    return f"Email sent to {to} with subject '{subject}'"


@tool
def delete_record(record_id: str, reason: str) -> str:
    """Delete a record from the database.

    Args:
        record_id: ID of record to delete
        reason: Reason for deletion
    """
    return f"Record {record_id} deleted. Reason: {reason}"


@tool
def make_payment(amount: float, recipient: str, memo: str) -> str:
    """Process a payment.

    Args:
        amount: Payment amount
        recipient: Payment recipient
        memo: Payment memo/description
    """
    return f"Payment of ${amount} sent to {recipient}. Memo: {memo}"


# ============================================================================
# HITL Workflow Nodes
# ============================================================================

def agent_node(state: HITLState) -> dict:
    """Agent processes request and determines action."""
    messages = state["messages"]

    system_prompt = """You are a helpful assistant that can perform actions.

When the user asks you to:
- Send emails → Use send_email tool
- Delete records → Use delete_record tool
- Make payments → Use make_payment tool

For any sensitive action, clearly state what you intend to do.
Format your response as:
ACTION: [action type]
DETAILS: [specific details]
RISK: [low/medium/high]"""

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        *messages
    ])

    # Parse response for action
    content = response.content
    action_type = "none"
    risk_level = "low"

    if "ACTION:" in content:
        if "email" in content.lower():
            action_type = "send_email"
            risk_level = "medium"
        elif "delete" in content.lower():
            action_type = "delete_record"
            risk_level = "high"
        elif "payment" in content.lower():
            action_type = "make_payment"
            risk_level = "high"

    return {
        "messages": [AIMessage(content=content)],
        "draft_content": content,
        "action_type": action_type,
        "pending_action": {
            "type": action_type,
            "content": content,
            "risk": risk_level
        } if action_type != "none" else None
    }


def approval_node(state: HITLState) -> dict:
    """Request human approval for sensitive action."""
    pending = state.get("pending_action")
    approvals_requested = state.get("approvals_requested", 0)

    if not pending:
        return {"approvals_requested": approvals_requested}

    # Create approval request
    approval_request = {
        "type": "approval_required",
        "action": pending["type"],
        "content": pending["content"],
        "risk_level": pending.get("risk", "medium"),
        "message": f"The agent wants to perform: {pending['type']}\n\nDetails:\n{pending['content']}\n\nDo you approve this action?"
    }

    # Interrupt for human approval
    response = interrupt(approval_request)

    # Process approval response
    approved = response.get("approved", False)
    feedback = response.get("feedback", "")
    modified = response.get("modified_content")

    return {
        "approvals_requested": approvals_requested + 1,
        "approvals_granted": state.get("approvals_granted", 0) + (1 if approved else 0),
        "pending_action": {
            **pending,
            "approved": approved,
            "feedback": feedback,
            "modified_content": modified
        }
    }


def execute_node(state: HITLState) -> dict:
    """Execute approved action or report rejection."""
    pending = state.get("pending_action")

    if not pending:
        return {}

    approved = pending.get("approved", False)
    action_type = pending.get("type")
    modified = pending.get("modified_content")
    feedback = pending.get("feedback", "")

    if approved:
        # Execute the action (simulated)
        content = modified or pending.get("content", "")

        if action_type == "send_email":
            result = "Email sent successfully."
        elif action_type == "delete_record":
            result = "Record deleted successfully."
        elif action_type == "make_payment":
            result = "Payment processed successfully."
        else:
            result = "Action completed."

        message = f"Action approved and executed.\n\n{result}"

        if feedback:
            message += f"\n\nUser feedback: {feedback}"

    else:
        message = f"Action was not approved."
        if feedback:
            message += f"\n\nReason: {feedback}"

    return {
        "messages": [AIMessage(content=message)],
        "pending_action": None
    }


def route_after_agent(state: HITLState) -> str:
    """Route based on whether action needs approval."""
    pending = state.get("pending_action")

    if pending and pending.get("type") != "none":
        return "approval"

    return END


def route_after_approval(state: HITLState) -> str:
    """Always proceed to execution after approval."""
    return "execute"


# ============================================================================
# Graph Builder
# ============================================================================

def build_hitl_workflow(checkpointer=None):
    """Build the HITL workflow."""
    init_llm()

    builder = StateGraph(HITLState)

    # Add nodes
    builder.add_node("agent", agent_node)
    builder.add_node("approval", approval_node)
    builder.add_node("execute", execute_node)

    # Add edges
    builder.add_edge(START, "agent")

    builder.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "approval": "approval",
            END: END
        }
    )

    builder.add_edge("approval", "execute")
    builder.add_edge("execute", END)

    return builder.compile(checkpointer=checkpointer)


# ============================================================================
# Advanced HITL Patterns
# ============================================================================

def build_iterative_review_workflow(checkpointer=None):
    """Build workflow with iterative human review."""
    init_llm()

    class ReviewState(MessagesState):
        draft: str
        iteration: int
        max_iterations: int
        approved: bool

    def generate_draft(state: ReviewState) -> dict:
        """Generate or revise draft."""
        messages = state["messages"]
        iteration = state.get("iteration", 0)

        if iteration == 0:
            prompt = "Create a draft based on the user's request."
        else:
            prompt = f"Revise the draft based on feedback. Previous draft:\n{state.get('draft', '')}"

        response = llm.invoke([
            SystemMessage(content="You are a content creator. Create or revise content based on requests."),
            *messages,
            HumanMessage(content=prompt)
        ])

        return {
            "draft": response.content,
            "messages": [AIMessage(content=f"[Draft v{iteration + 1}]\n{response.content}")],
            "iteration": iteration + 1
        }

    def review_draft(state: ReviewState) -> dict:
        """Get human review of draft."""
        draft = state.get("draft", "")
        iteration = state.get("iteration", 1)

        review = interrupt({
            "type": "review",
            "draft": draft,
            "iteration": iteration,
            "message": "Please review this draft. You can approve, request changes, or reject."
        })

        approved = review.get("approved", False)
        feedback = review.get("feedback", "")

        if feedback and not approved:
            return {
                "messages": [HumanMessage(content=f"Feedback: {feedback}")],
                "approved": False
            }

        return {"approved": approved}

    def should_continue_review(state: ReviewState) -> str:
        """Check if should continue iterating."""
        if state.get("approved"):
            return "finalize"

        if state.get("iteration", 0) >= state.get("max_iterations", 3):
            return "finalize"

        return "generate"

    def finalize_content(state: ReviewState) -> dict:
        """Finalize the content."""
        draft = state.get("draft", "")
        approved = state.get("approved", False)

        if approved:
            message = f"Content approved!\n\nFinal version:\n{draft}"
        else:
            message = f"Maximum iterations reached.\n\nFinal draft:\n{draft}"

        return {"messages": [AIMessage(content=message)]}

    builder = StateGraph(ReviewState)

    builder.add_node("generate", generate_draft)
    builder.add_node("review", review_draft)
    builder.add_node("finalize", finalize_content)

    builder.add_edge(START, "generate")
    builder.add_edge("generate", "review")

    builder.add_conditional_edges(
        "review",
        should_continue_review,
        {
            "generate": "generate",
            "finalize": "finalize"
        }
    )

    builder.add_edge("finalize", END)

    return builder.compile(checkpointer=checkpointer)


# ============================================================================
# Workflow Interface
# ============================================================================

class HITLWorkflow:
    """HITL workflow with conversation memory."""

    def __init__(self, thread_id: str = "default"):
        self.thread_id = thread_id
        self.checkpointer = InMemorySaver()
        self.graph = build_hitl_workflow(self.checkpointer)

    def start(self, message: str) -> dict:
        """Start workflow - may pause for approval."""
        config = {"configurable": {"thread_id": self.thread_id}}

        result = self.graph.invoke(
            {
                "messages": [HumanMessage(content=message)],
                "approvals_requested": 0,
                "approvals_granted": 0,
                "pending_action": None,
                "draft_content": "",
                "action_type": "none"
            },
            config
        )

        return {
            "messages": [m.content for m in result.get("messages", []) if hasattr(m, "content")],
            "pending_approval": self._check_pending(config)
        }

    def _check_pending(self, config: dict) -> Optional[dict]:
        """Check if there's a pending approval."""
        state = self.graph.get_state(config)

        if state.next:
            # There's a pending interrupt
            tasks = getattr(state, "tasks", [])
            if tasks and hasattr(tasks[0], "interrupts") and tasks[0].interrupts:
                return tasks[0].interrupts[0].value

        return None

    def approve(self, approved: bool, feedback: str = "", modified_content: str = None) -> HITLResponse:
        """Submit approval decision."""
        config = {"configurable": {"thread_id": self.thread_id}}

        result = self.graph.invoke(
            Command(resume={
                "approved": approved,
                "feedback": feedback,
                "modified_content": modified_content
            }),
            config
        )

        last_message = result["messages"][-1] if result.get("messages") else None

        return HITLResponse(
            answer=last_message.content if last_message else "No response",
            approvals_requested=result.get("approvals_requested", 0),
            approvals_granted=result.get("approvals_granted", 0),
            thread_id=self.thread_id
        )

    def clear_history(self):
        """Clear by starting new thread."""
        import uuid
        self.thread_id = str(uuid.uuid4())


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    """Interactive CLI for HITL workflow."""
    print("Human-in-the-Loop Workflow initialized.")
    print("Try actions like: 'Send an email to john@example.com'")
    print("or 'Delete user record #12345'")
    print("Type 'quit' to exit, 'clear' to reset.\n")

    workflow = HITLWorkflow()

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
                print("Workflow cleared.\n")
                continue

            # Start workflow
            result = workflow.start(user_input)

            for msg in result["messages"]:
                print(f"\nAgent: {msg}")

            # Check for pending approval
            pending = result.get("pending_approval")

            if pending:
                print("\n" + "=" * 40)
                print("APPROVAL REQUIRED")
                print("=" * 40)
                print(pending.get("message", "Approval needed"))
                print()

                while True:
                    decision = input("Approve? (yes/no/modify): ").strip().lower()

                    if decision in ["yes", "y"]:
                        response = workflow.approve(approved=True)
                        print(f"\nAgent: {response.answer}")
                        break
                    elif decision in ["no", "n"]:
                        reason = input("Reason (optional): ").strip()
                        response = workflow.approve(approved=False, feedback=reason)
                        print(f"\nAgent: {response.answer}")
                        break
                    elif decision == "modify":
                        modified = input("Enter modified content: ").strip()
                        response = workflow.approve(approved=True, modified_content=modified)
                        print(f"\nAgent: {response.answer}")
                        break
                    else:
                        print("Please enter 'yes', 'no', or 'modify'")

            print()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
