---
name: agentic-chatbot-workflow
description: Build production-ready agentic workflows with LangGraph. Covers ReAct agents, multi-agent patterns (Supervisor, Swarm, Orchestrator), tool calling, and human-in-the-loop. Use when building AI agents that reason and act, orchestrating multiple specialized agents, or implementing approval workflows.
license: Complete terms in LICENSE.txt
---

# Agentic Chatbot Workflow Guide

## Overview

Build agentic AI systems that can reason, plan, and execute complex tasks using LangGraph. This skill covers single-agent and multi-agent patterns with human oversight.

**Pattern Overview:**
```
ReAct        → Single agent with tools (reason + act loop)
Supervisor   → Manager delegates to specialized workers
Swarm        → Peer agents hand off to each other
Orchestrator → Central planner coordinates multi-step execution
```

## Quick Start

### ReAct Agent

```python
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool

@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
agent = create_react_agent(llm, tools=[search])

response = agent.invoke({"messages": [{"role": "user", "content": "Find info about LangGraph"}]})
```

### Supervisor Workflow

```python
from scripts.supervisor_workflow import SupervisorWorkflow

workflow = SupervisorWorkflow(thread_id="user-123")
response = workflow.run("Research AI trends and write a summary")
print(response.answer)
print(f"Workers used: {response.workers_used}")
```

### HITL Approval

```python
from scripts.hitl_workflow import HITLWorkflow

workflow = HITLWorkflow(thread_id="user-123")
result = workflow.start("Send an email to team@example.com")

if result.get("pending_approval"):
    # Human reviews and approves
    response = workflow.approve(approved=True, feedback="Looks good")
```

## Agent Patterns

### 1. ReAct (Reasoning + Acting)

Single agent that iteratively reasons about what to do and takes actions.

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

class ReActState(MessagesState):
    tools_called: list[str]

def call_model(state: ReActState) -> dict:
    response = llm.bind_tools(tools).invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: ReActState) -> str:
    if state["messages"][-1].tool_calls:
        return "tools"
    return END

builder = StateGraph(ReActState)
builder.add_node("agent", call_model)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", should_continue)
builder.add_edge("tools", "agent")
```

### 2. Supervisor Pattern

Manager agent routes to specialized workers.

```python
from pydantic import BaseModel
from typing import Literal

class RouteDecision(BaseModel):
    next: Literal["researcher", "writer", "FINISH"]

def supervisor(state):
    response = llm.with_structured_output(RouteDecision).invoke([
        {"role": "system", "content": "Route to appropriate worker."},
        *state["messages"]
    ])
    return {"next": response.next}

def route(state) -> str:
    return state.get("next", END)

builder.add_conditional_edges("supervisor", route, {
    "researcher": "researcher",
    "writer": "writer",
    "FINISH": END
})
```

### 3. Swarm Pattern

Peer agents hand off to each other without central coordination.

```python
from langchain_core.tools import tool

@tool
def handoff_to_sales(reason: str) -> str:
    """Transfer to sales agent."""
    return f"__HANDOFF__:sales:{reason}"

@tool
def handoff_to_support(reason: str) -> str:
    """Transfer to support agent."""
    return f"__HANDOFF__:support:{reason}"

# Each agent has handoff tools to other agents
support_agent = create_react_agent(llm, [support_tools, handoff_to_sales])
sales_agent = create_react_agent(llm, [sales_tools, handoff_to_support])
```

### 4. Orchestrator Pattern

Central orchestrator plans and coordinates execution.

```python
class TaskPlan(BaseModel):
    steps: list[str]
    agents_needed: list[str]

def planner(state) -> dict:
    plan = llm.with_structured_output(TaskPlan).invoke([...])
    return {"plan": plan.steps, "current_step": 0}

def executor(state) -> dict:
    step = state["plan"][state["current_step"]]
    # Route to appropriate agent
    result = agent.invoke(step)
    return {"current_step": state["current_step"] + 1}

def should_continue(state) -> str:
    if state["current_step"] >= len(state["plan"]):
        return "synthesizer"
    return "executor"
```

## Tool Calling

### Define Tools

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

@tool
def calculate(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))

class SearchInput(BaseModel):
    query: str = Field(description="Search query")
    limit: int = Field(default=5, description="Max results")

@tool(args_schema=SearchInput)
def search(query: str, limit: int) -> list[str]:
    """Search for information."""
    return [f"Result {i}" for i in range(limit)]
```

### ToolNode

```python
from langgraph.prebuilt import ToolNode

tools = [calculate, search, get_weather]
tool_node = ToolNode(tools)

# In graph
builder.add_node("tools", tool_node)
builder.add_conditional_edges("agent", should_use_tools, {
    "tools": "tools",
    END: END
})
builder.add_edge("tools", "agent")
```

### InjectedState

```python
from langgraph.prebuilt import InjectedState
from typing import Annotated

@tool
def get_user_data(
    state: Annotated[AgentState, InjectedState]
) -> dict:
    """Get current user data."""
    return {"user_id": state["user_id"]}
```

## Human-in-the-Loop

### Interrupt for Approval

```python
from langgraph.types import interrupt, Command

def sensitive_action(state):
    # Pause for human approval
    approval = interrupt({
        "action": "send_email",
        "details": state["email_content"],
        "message": "Approve this email?"
    })

    if approval.get("approved"):
        return execute_action(state)
    return {"messages": [AIMessage(content="Action cancelled")]}
```

### Resume After Approval

```python
# Initial invoke - pauses at interrupt
result = graph.invoke({"messages": [msg]}, config)

# Check if interrupted
state = graph.get_state(config)
if state.next:
    # Show approval request to human
    interrupt_data = state.tasks[0].interrupts[0].value

    # Resume with approval
    result = graph.invoke(
        Command(resume={"approved": True}),
        config
    )
```

### Tool Review Pattern

```python
SENSITIVE_TOOLS = {"send_email", "delete_record", "make_payment"}

def review_tools(state):
    tool_calls = state["messages"][-1].tool_calls
    sensitive = [tc for tc in tool_calls if tc["name"] in SENSITIVE_TOOLS]

    if sensitive:
        approval = interrupt({
            "tools": sensitive,
            "message": "Review these sensitive operations"
        })
        if not approval.get("approved"):
            return {"messages": [AIMessage(content="Operations cancelled")]}

    return state
```

## State Management

### Basic State

```python
from langgraph.graph import MessagesState

class AgentState(MessagesState):
    context: str
    user_id: str
```

### Annotated State (Accumulating)

```python
from typing import Annotated
from operator import add

class WorkflowState(MessagesState):
    # Appends to list on each update
    results: Annotated[list[str], add]
    # Overwrites on each update
    current_step: int
```

### Checkpointers

```python
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

# In-memory (dev)
checkpointer = InMemorySaver()

# SQLite (persistent)
checkpointer = SqliteSaver.from_conn_string("workflow.db")

graph = builder.compile(checkpointer=checkpointer)

# Thread-based conversations
config = {"configurable": {"thread_id": "user-123"}}
result = graph.invoke(inputs, config)
```

## Streaming

```python
# Stream state updates
for event in graph.stream(inputs, config, stream_mode="values"):
    print(event["messages"][-1].content)

# Stream with node info
for event in graph.stream(inputs, config, stream_mode="updates"):
    for node, update in event.items():
        print(f"Node {node}: {update}")
```

## Environment Variables

```bash
GOOGLE_API_KEY=your-gemini-api-key
```

## Dependencies

```
langchain>=0.3.0
langchain-google-genai>=2.0.0
langgraph>=0.2.0
pydantic>=2.0.0
```

## Reference Files

- [references/multi_agent_patterns.md](references/multi_agent_patterns.md) - Supervisor, Swarm, Orchestrator patterns
- [references/tool_calling.md](references/tool_calling.md) - Tool creation, ToolNode, error handling
- [references/human_in_the_loop.md](references/human_in_the_loop.md) - Interrupts, approvals, reviews

## Scripts

- `scripts/react_agent.py` - Single ReAct agent with tools
- `scripts/supervisor_workflow.py` - Supervisor multi-agent system
- `scripts/swarm_workflow.py` - Swarm peer-to-peer handoffs
- `scripts/orchestrator_workflow.py` - Orchestrator with planning
- `scripts/hitl_workflow.py` - Human-in-the-loop patterns
