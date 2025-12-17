# Multi-Agent Patterns

## Overview

Multi-agent systems coordinate multiple specialized AI agents to solve complex tasks. Choose patterns based on task complexity and coordination needs.

## Pattern Comparison

| Pattern | Coordination | Best For |
|---------|-------------|----------|
| Supervisor | Centralized | Clear task delegation, hierarchical workflows |
| Swarm | Peer-to-peer | Dynamic routing, customer support |
| Orchestrator | Sequential/Parallel | Complex pipelines, content generation |

## Supervisor Pattern

Central supervisor agent routes tasks to specialized workers.

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from typing import Literal

class SupervisorState(MessagesState):
    next: str

class RouteDecision(BaseModel):
    next: Literal["researcher", "writer", "FINISH"]
    reason: str

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

def supervisor(state: SupervisorState) -> dict:
    """Decide which worker to route to."""
    messages = state["messages"]

    response = llm.with_structured_output(RouteDecision).invoke([
        {"role": "system", "content": """You are a supervisor managing workers:
        - researcher: Gathers information and facts
        - writer: Creates written content
        - FINISH: Task is complete

        Decide which worker should act next."""},
        *messages
    ])

    return {"next": response.next}

def researcher(state: SupervisorState) -> dict:
    """Research agent gathers information."""
    response = llm.invoke([
        {"role": "system", "content": "You are a researcher. Find relevant facts."},
        *state["messages"]
    ])
    return {"messages": [{"role": "assistant", "content": f"[Research]\n{response.content}"}]}

def writer(state: SupervisorState) -> dict:
    """Writer agent creates content."""
    response = llm.invoke([
        {"role": "system", "content": "You are a writer. Create polished content."},
        *state["messages"]
    ])
    return {"messages": [{"role": "assistant", "content": f"[Writer]\n{response.content}"}]}

def route_supervisor(state: SupervisorState) -> str:
    """Route based on supervisor decision."""
    return state.get("next", END)

# Build graph
builder = StateGraph(SupervisorState)
builder.add_node("supervisor", supervisor)
builder.add_node("researcher", researcher)
builder.add_node("writer", writer)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges("supervisor", route_supervisor, {
    "researcher": "researcher",
    "writer": "writer",
    "FINISH": END
})
builder.add_edge("researcher", "supervisor")
builder.add_edge("writer", "supervisor")

graph = builder.compile()
```

## Swarm Pattern

Peer agents hand off to each other without central coordination.

```python
from langgraph.prebuilt import create_react_agent
from langgraph_swarm import create_handoff_tool, create_swarm

# Define handoff tools
handoff_to_sales = create_handoff_tool(
    agent_name="sales_agent",
    description="Transfer to sales for pricing and purchases"
)

handoff_to_support = create_handoff_tool(
    agent_name="support_agent",
    description="Transfer to support for technical issues"
)

handoff_to_billing = create_handoff_tool(
    agent_name="billing_agent",
    description="Transfer to billing for payment questions"
)

# Create specialized agents
support_agent = create_react_agent(
    llm,
    tools=[lookup_docs, handoff_to_sales, handoff_to_billing],
    prompt="You are a support agent. Help with technical issues."
)

sales_agent = create_react_agent(
    llm,
    tools=[check_inventory, create_quote, handoff_to_support],
    prompt="You are a sales agent. Help with purchases."
)

billing_agent = create_react_agent(
    llm,
    tools=[check_balance, process_payment, handoff_to_support],
    prompt="You are a billing agent. Handle payments."
)

# Create swarm
swarm = create_swarm(
    agents=[support_agent, sales_agent, billing_agent],
    default_agent="support_agent"
)

# Compile with checkpointer for persistence
graph = swarm.compile(checkpointer=checkpointer)
```

## Orchestrator Pattern

Central orchestrator plans and executes multi-step workflows.

```python
from typing import Annotated
from operator import add

class OrchestratorState(MessagesState):
    plan: list[str]
    current_step: int
    results: Annotated[list[str], add]

def planner(state: OrchestratorState) -> dict:
    """Create execution plan."""
    response = llm.with_structured_output(Plan).invoke([
        {"role": "system", "content": "Create a step-by-step plan."},
        *state["messages"]
    ])
    return {"plan": response.steps, "current_step": 0}

def executor(state: OrchestratorState) -> dict:
    """Execute current step."""
    step = state["plan"][state["current_step"]]

    # Route to appropriate agent based on step
    if "research" in step.lower():
        result = researcher.invoke({"messages": [{"role": "user", "content": step}]})
    elif "write" in step.lower():
        result = writer.invoke({"messages": [{"role": "user", "content": step}]})
    else:
        result = general_agent.invoke({"messages": [{"role": "user", "content": step}]})

    return {
        "results": [result["messages"][-1].content],
        "current_step": state["current_step"] + 1
    }

def should_continue(state: OrchestratorState) -> str:
    """Check if more steps remain."""
    if state["current_step"] >= len(state["plan"]):
        return "synthesizer"
    return "executor"

def synthesizer(state: OrchestratorState) -> dict:
    """Combine all results into final output."""
    results = "\n\n".join(state["results"])
    response = llm.invoke([
        {"role": "system", "content": "Synthesize these results into a coherent response."},
        {"role": "user", "content": results}
    ])
    return {"messages": [{"role": "assistant", "content": response.content}]}

# Build orchestrator graph
builder = StateGraph(OrchestratorState)
builder.add_node("planner", planner)
builder.add_node("executor", executor)
builder.add_node("synthesizer", synthesizer)

builder.add_edge(START, "planner")
builder.add_edge("planner", "executor")
builder.add_conditional_edges("executor", should_continue)
builder.add_edge("synthesizer", END)
```

## State Sharing Between Agents

### Shared Context via State

```python
class SharedState(MessagesState):
    # Shared across all agents
    context: dict
    artifacts: Annotated[list[str], add]

    # Agent-specific
    current_agent: str

def agent_node(state: SharedState) -> dict:
    # Access shared context
    context = state.get("context", {})

    # Add to shared artifacts
    return {
        "artifacts": ["New artifact from agent"],
        "context": {**context, "last_update": "agent_name"}
    }
```

### Message-Based Communication

```python
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

def agent_with_handoff(state: MessagesState) -> dict:
    # Send structured message to next agent
    handoff_message = AIMessage(
        content="Handing off to specialist",
        additional_kwargs={
            "handoff_to": "specialist_agent",
            "context": {"key": "value"}
        }
    )
    return {"messages": [handoff_message]}
```

## When to Use Each Pattern

### Supervisor
- Clear hierarchy needed
- Task types known upfront
- Central logging/monitoring required
- Example: Content moderation pipeline

### Swarm
- Dynamic routing based on conversation
- Customer-facing applications
- Agents need autonomy
- Example: Customer support chatbot

### Orchestrator
- Complex multi-step tasks
- Order of operations matters
- Need planning before execution
- Example: Research report generation

## Error Handling

```python
from langgraph.errors import NodeInterrupt

def robust_agent(state):
    try:
        result = perform_action(state)
        return {"messages": [AIMessage(content=result)]}
    except Exception as e:
        # Log error and return graceful response
        return {
            "messages": [AIMessage(content=f"Error encountered: {str(e)}")],
            "error": str(e)
        }

# Or use retry logic
from tenacity import retry, stop_after_attempt

@retry(stop=stop_after_attempt(3))
def reliable_llm_call(messages):
    return llm.invoke(messages)
```

## Performance Tips

1. **Parallel Execution**: Use `add_node` with async functions for I/O-bound tasks
2. **Caching**: Cache LLM responses for repeated queries
3. **Early Exit**: Add conditional edges to skip unnecessary steps
4. **Batching**: Group similar operations when possible
