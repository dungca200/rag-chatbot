# Human-in-the-Loop (HITL)

## Overview

Human-in-the-loop patterns allow humans to review, approve, or modify agent actions before execution. Essential for high-stakes operations, compliance requirements, and building trust.

## Interrupt Function

The `interrupt()` function pauses graph execution and waits for human input.

```python
from langgraph.types import interrupt, Command
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import InMemorySaver

def sensitive_action(state: MessagesState) -> dict:
    """Action requiring human approval."""
    last_message = state["messages"][-1].content

    # Pause for human review
    approval = interrupt({
        "action": "send_email",
        "details": last_message,
        "question": "Approve this email?"
    })

    if approval.get("approved"):
        # Proceed with action
        result = send_email(last_message)
        return {"messages": [AIMessage(content=f"Email sent: {result}")]}
    else:
        reason = approval.get("reason", "No reason provided")
        return {"messages": [AIMessage(content=f"Action cancelled: {reason}")]}

# Build graph
builder = StateGraph(MessagesState)
builder.add_node("agent", agent_node)
builder.add_node("sensitive", sensitive_action)
builder.add_edge(START, "agent")
builder.add_edge("agent", "sensitive")
builder.add_edge("sensitive", END)

# Must use checkpointer for interrupts
graph = builder.compile(checkpointer=InMemorySaver())
```

## Using Interrupts

### Invoking and Resuming

```python
# Initial invocation - will pause at interrupt
config = {"configurable": {"thread_id": "user-123"}}
result = graph.invoke({"messages": [HumanMessage(content="Send report")]}, config)

# Check if interrupted
state = graph.get_state(config)
if state.next:  # Pending nodes exist
    # Show interrupt data to user
    interrupt_data = state.tasks[0].interrupts[0].value
    print(f"Approval needed: {interrupt_data}")

    # Resume with human input
    result = graph.invoke(
        Command(resume={"approved": True}),
        config
    )
```

### Multiple Interrupt Points

```python
class WorkflowState(MessagesState):
    stage: str
    approved_stages: list[str]

def stage_one(state: WorkflowState) -> dict:
    result = process_stage_one(state)

    approval = interrupt({
        "stage": "one",
        "result": result,
        "message": "Review stage one output"
    })

    if not approval.get("approved"):
        return {"messages": [AIMessage(content="Stage one rejected")]}

    return {"stage": "two", "approved_stages": ["one"]}

def stage_two(state: WorkflowState) -> dict:
    result = process_stage_two(state)

    approval = interrupt({
        "stage": "two",
        "result": result,
        "message": "Review stage two output"
    })

    if not approval.get("approved"):
        return {"messages": [AIMessage(content="Stage two rejected")]}

    return {"approved_stages": state["approved_stages"] + ["two"]}
```

## Approval Patterns

### Simple Approval

```python
def requires_approval(state: MessagesState) -> dict:
    """Simple yes/no approval."""
    approval = interrupt("Proceed with this action?")

    if approval:  # Truthy means approved
        return execute_action(state)
    return {"messages": [AIMessage(content="Action cancelled by user")]}
```

### Approval with Modification

```python
def editable_approval(state: MessagesState) -> dict:
    """Allow human to modify before approval."""
    draft = generate_draft(state)

    response = interrupt({
        "type": "edit",
        "draft": draft,
        "instructions": "Edit the draft or approve as-is"
    })

    if response.get("action") == "approve":
        final = response.get("edited", draft)  # Use edited or original
        return {"messages": [AIMessage(content=final)]}
    elif response.get("action") == "reject":
        return {"messages": [AIMessage(content="Draft rejected")]}
    else:  # regenerate
        return {"messages": [AIMessage(content="Regenerating...")]}
```

### Multi-Level Approval

```python
class ApprovalState(MessagesState):
    approval_level: int
    approvers: list[str]

def multi_level_approval(state: ApprovalState) -> dict:
    """Require multiple approvals."""
    level = state.get("approval_level", 0)
    required_levels = ["manager", "director", "vp"]

    if level >= len(required_levels):
        return execute_final_action(state)

    approver = required_levels[level]
    approval = interrupt({
        "level": approver,
        "message": f"Approval needed from {approver}"
    })

    if approval.get("approved"):
        return {
            "approval_level": level + 1,
            "approvers": state.get("approvers", []) + [approval.get("approver_id")]
        }
    else:
        return {"messages": [AIMessage(content=f"Rejected by {approver}")]}
```

## Tool Review

### Review Before Execution

```python
from langgraph.prebuilt import ToolNode

def review_tool_calls(state: MessagesState) -> dict:
    """Review tool calls before execution."""
    last_message = state["messages"][-1]

    if not last_message.tool_calls:
        return state

    # Show tools to human for review
    tools_to_review = [
        {"name": tc["name"], "args": tc["args"]}
        for tc in last_message.tool_calls
    ]

    approval = interrupt({
        "type": "tool_review",
        "tools": tools_to_review,
        "message": "Review these tool calls before execution"
    })

    if approval.get("approved"):
        # Execute approved tools (might be filtered)
        approved_tools = approval.get("approved_tools", tools_to_review)
        # Continue to tool node
        return state
    else:
        return {
            "messages": [AIMessage(content="Tool execution cancelled by reviewer")]
        }

# Insert review before tool execution
builder.add_node("review", review_tool_calls)
builder.add_node("tools", ToolNode(tools))
builder.add_edge("agent", "review")
builder.add_edge("review", "tools")
```

### Selective Tool Review

```python
SENSITIVE_TOOLS = {"send_email", "delete_record", "make_payment"}

def selective_review(state: MessagesState) -> dict:
    """Only review sensitive tools."""
    last_message = state["messages"][-1]

    if not last_message.tool_calls:
        return {"needs_review": False}

    sensitive_calls = [
        tc for tc in last_message.tool_calls
        if tc["name"] in SENSITIVE_TOOLS
    ]

    if sensitive_calls:
        approval = interrupt({
            "sensitive_tools": sensitive_calls,
            "message": "Sensitive operations require approval"
        })

        if not approval.get("approved"):
            return {
                "messages": [AIMessage(content="Sensitive operation denied")],
                "needs_review": False
            }

    return {"needs_review": False}
```

## State Modification

### Human Editing State

```python
def allow_state_edit(state: MessagesState) -> dict:
    """Allow human to directly edit state."""
    current_output = state["messages"][-1].content

    response = interrupt({
        "type": "state_edit",
        "current_state": {
            "output": current_output,
            "metadata": state.get("metadata", {})
        },
        "message": "Review and modify state if needed"
    })

    if response.get("modified"):
        # Apply human modifications
        return {
            "messages": [AIMessage(content=response["new_output"])],
            "metadata": response.get("new_metadata", state.get("metadata"))
        }

    return state
```

### Feedback Loop

```python
class FeedbackState(MessagesState):
    feedback_history: list[dict]
    iteration: int

def iterative_refinement(state: FeedbackState) -> dict:
    """Iterate based on human feedback."""
    output = generate_output(state)

    feedback = interrupt({
        "output": output,
        "iteration": state.get("iteration", 0),
        "message": "Provide feedback or approve"
    })

    if feedback.get("approved"):
        return {"messages": [AIMessage(content=output)]}

    # Store feedback and regenerate
    return {
        "feedback_history": state.get("feedback_history", []) + [feedback],
        "iteration": state.get("iteration", 0) + 1,
        "messages": [HumanMessage(content=feedback.get("feedback", ""))]
    }

def should_continue_refinement(state: FeedbackState) -> str:
    """Check if should continue refining."""
    if state.get("iteration", 0) >= 5:  # Max iterations
        return "finalize"
    # Check if last message was approval
    return "refine"
```

## Integration Patterns

### REST API for Approvals

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
pending_approvals = {}  # In production, use database

class ApprovalRequest(BaseModel):
    thread_id: str
    approved: bool
    feedback: str = ""

@app.post("/approve")
async def handle_approval(request: ApprovalRequest):
    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        result = graph.invoke(
            Command(resume={
                "approved": request.approved,
                "feedback": request.feedback
            }),
            config
        )
        return {"status": "completed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pending/{thread_id}")
async def get_pending(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = graph.get_state(config)

    if state.next:
        interrupt_data = state.tasks[0].interrupts[0].value
        return {"pending": True, "data": interrupt_data}

    return {"pending": False}
```

### Webhook Notifications

```python
import httpx

async def notify_approver(interrupt_data: dict, webhook_url: str):
    """Send notification when approval needed."""
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json={
            "type": "approval_needed",
            "data": interrupt_data,
            "timestamp": datetime.now().isoformat()
        })
```

## Best Practices

1. **Clear Interrupt Data**: Include all information needed for decision
2. **Timeout Handling**: Set timeouts for pending approvals
3. **Audit Trail**: Log all approvals/rejections with timestamps
4. **Graceful Degradation**: Handle cases where approver is unavailable
5. **Batching**: Allow batch approvals for repetitive tasks

```python
# Example: Timeout handling
from datetime import datetime, timedelta

def check_timeout(state: MessagesState) -> dict:
    """Check if approval has timed out."""
    started = state.get("interrupt_started")
    if started:
        if datetime.now() - started > timedelta(hours=24):
            return {
                "messages": [AIMessage(content="Approval timed out")],
                "timed_out": True
            }
    return state
```
