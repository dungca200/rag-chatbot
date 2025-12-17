# LangGraph Agent Patterns

## StateGraph Basics

### State Definition
```python
from langgraph.graph import StateGraph, MessagesState, START, END
from typing import TypedDict, Annotated
from operator import add

# Using MessagesState (includes messages list)
class RAGState(MessagesState):
    context: list[str]
    sources: list[str]

# Custom state with reducers
class CustomState(TypedDict):
    messages: Annotated[list, add]  # Append new messages
    context: Annotated[list[str], add]  # Append context
    query: str  # Replace on update
```

### Building a Graph
```python
from langgraph.graph import StateGraph, START, END

def retrieve_node(state: RAGState) -> dict:
    """Retrieve relevant documents."""
    query = state["messages"][-1].content
    # ... retrieval logic
    return {"context": ["doc1", "doc2"]}

def generate_node(state: RAGState) -> dict:
    """Generate response with context."""
    context = "\n".join(state["context"])
    # ... generation logic
    return {"messages": [AIMessage(content="response")]}

# Build graph
builder = StateGraph(RAGState)
builder.add_node("retrieve", retrieve_node)
builder.add_node("generate", generate_node)

# Define edges
builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", END)

graph = builder.compile()
```

## Checkpointers for Persistence

### InMemorySaver (Development)
```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)

# Use with thread_id
config = {"configurable": {"thread_id": "user-123"}}
result = graph.invoke({"messages": [...]}, config)
```

### SqliteSaver (Production)
```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
graph = builder.compile(checkpointer=checkpointer)

# State persists across sessions
config = {"configurable": {"thread_id": "session-456"}}
result = graph.invoke({"messages": [...]}, config)
```

### State Operations
```python
# Get current state
state = graph.get_state(config)
print(f"Next node: {state.next}")
print(f"Values: {state.values}")

# Update state manually
graph.update_state(config, {"context": ["new context"]})

# Get state history
for checkpoint in graph.get_state_history(config):
    print(f"Checkpoint: {checkpoint.config}")
```

## Conditional Edges

### Router Function
```python
def should_retrieve(state: RAGState) -> str:
    """Decide whether to retrieve or respond directly."""
    last_message = state["messages"][-1].content.lower()
    if "help" in last_message or "what" in last_message:
        return "retrieve"
    return "respond"

builder.add_conditional_edges(
    START,
    should_retrieve,
    {"retrieve": "retrieve", "respond": "generate"}
)
```

### Multiple Conditions
```python
def route_after_retrieve(state: RAGState) -> str:
    if not state.get("context"):
        return "no_results"
    if len(state["context"]) > 5:
        return "summarize"
    return "generate"

builder.add_conditional_edges(
    "retrieve",
    route_after_retrieve,
    {
        "no_results": "fallback",
        "summarize": "summarize",
        "generate": "generate"
    }
)
```

## Streaming Responses

### Stream Mode Options
```python
# Stream full state updates
for event in graph.stream(inputs, config, stream_mode="values"):
    print(event["messages"][-1])

# Stream node updates only
for event in graph.stream(inputs, config, stream_mode="updates"):
    node_name = list(event.keys())[0]
    print(f"{node_name}: {event[node_name]}")

# Stream debug info
for event in graph.stream(inputs, config, stream_mode="debug"):
    print(event)
```

### Async Streaming
```python
async def stream_response(query: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=query)]}

    async for event in graph.astream(inputs, config, stream_mode="values"):
        if event.get("messages"):
            yield event["messages"][-1].content
```

## create_react_agent

### Quick Agent Setup
```python
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

@tool
def search_documents(query: str) -> str:
    """Search knowledge base for information."""
    docs = vector_store.similarity_search(query, k=4)
    return "\n\n".join(doc.page_content for doc in docs)

agent = create_react_agent(
    llm,
    tools=[search_documents],
    prompt="You are a helpful assistant with access to a knowledge base."
)

# Use the agent
result = agent.invoke({
    "messages": [HumanMessage(content="What is RAG?")]
})
```

## Memory and Store

### Long-term Memory Store
```python
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
graph = builder.compile(checkpointer=checkpointer, store=store)

# Store persists across threads
config = {
    "configurable": {
        "thread_id": "thread-1",
        "user_id": "user-123"  # For user-specific memory
    }
}
```

## Error Handling

### Retry Logic
```python
from langgraph.errors import NodeInterrupt

def retrieve_with_retry(state: RAGState) -> dict:
    try:
        docs = vector_store.similarity_search(state["query"], k=4)
        if not docs:
            raise NodeInterrupt("No documents found")
        return {"context": [d.page_content for d in docs]}
    except Exception as e:
        return {"error": str(e), "context": []}
```

### Fallback Nodes
```python
def fallback_node(state: RAGState) -> dict:
    return {
        "messages": [AIMessage(
            content="I couldn't find relevant information. Please try rephrasing."
        )]
    }

builder.add_node("fallback", fallback_node)
```
