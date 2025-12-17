#!/usr/bin/env python3
"""
Debugging Workflows for LangGraph Agents.

Patterns for debugging and inspecting agent execution:
- Thread state inspection
- Checkpoint history analysis
- Error tracing
- Step-by-step execution review
"""

import os
from datetime import datetime
from typing import Optional, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphRecursionError


# ============================================================================
# State Inspection
# ============================================================================

class StateInspector:
    """
    Inspect and debug LangGraph state.

    Features:
    - View current state
    - Compare states across checkpoints
    - Track state changes
    """

    def __init__(self, graph, checkpointer):
        self.graph = graph
        self.checkpointer = checkpointer

    def get_current_state(self, thread_id: str) -> dict:
        """Get current state for a thread."""
        config = {"configurable": {"thread_id": thread_id}}
        state = self.graph.get_state(config)
        return {
            "values": state.values,
            "next": state.next,
            "config": state.config,
            "created_at": state.created_at,
            "parent_config": state.parent_config,
        }

    def get_state_at_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str
    ) -> dict:
        """Get state at a specific checkpoint."""
        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id
            }
        }
        state = self.graph.get_state(config)
        return {
            "values": state.values,
            "next": state.next,
            "checkpoint_id": checkpoint_id
        }

    def list_checkpoints(self, thread_id: str, limit: int = 10) -> list:
        """List all checkpoints for a thread."""
        config = {"configurable": {"thread_id": thread_id}}
        checkpoints = []

        for checkpoint in self.checkpointer.list(config, limit=limit):
            cp_config = checkpoint.config["configurable"]
            checkpoints.append({
                "checkpoint_id": cp_config.get("checkpoint_id"),
                "checkpoint_ns": cp_config.get("checkpoint_ns", ""),
                "metadata": checkpoint.metadata
            })

        return checkpoints

    def compare_states(
        self,
        thread_id: str,
        checkpoint_id_1: str,
        checkpoint_id_2: str
    ) -> dict:
        """Compare states between two checkpoints."""
        state1 = self.get_state_at_checkpoint(thread_id, checkpoint_id_1)
        state2 = self.get_state_at_checkpoint(thread_id, checkpoint_id_2)

        # Find differences in values
        differences = {}
        all_keys = set(state1["values"].keys()) | set(state2["values"].keys())

        for key in all_keys:
            val1 = state1["values"].get(key)
            val2 = state2["values"].get(key)
            if val1 != val2:
                differences[key] = {
                    "checkpoint_1": val1,
                    "checkpoint_2": val2
                }

        return {
            "checkpoint_1": checkpoint_id_1,
            "checkpoint_2": checkpoint_id_2,
            "differences": differences
        }


# ============================================================================
# Execution Tracer
# ============================================================================

class ExecutionTracer:
    """
    Trace execution steps through the graph.

    Records:
    - Node visits
    - State changes
    - Timing information
    - Errors
    """

    def __init__(self):
        self.trace: list[dict] = []
        self.start_time: Optional[datetime] = None

    def start(self):
        """Start tracing."""
        self.trace = []
        self.start_time = datetime.now()

    def record_step(
        self,
        node: str,
        state_before: dict,
        state_after: dict,
        duration_ms: float,
        error: Optional[str] = None
    ):
        """Record an execution step."""
        self.trace.append({
            "node": node,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": duration_ms,
            "state_before": state_before,
            "state_after": state_after,
            "error": error
        })

    def get_trace(self) -> list[dict]:
        """Get the execution trace."""
        return self.trace

    def summary(self) -> dict:
        """Get trace summary."""
        total_duration = sum(step["duration_ms"] for step in self.trace)
        nodes_visited = [step["node"] for step in self.trace]
        errors = [step for step in self.trace if step["error"]]

        return {
            "total_steps": len(self.trace),
            "total_duration_ms": total_duration,
            "nodes_visited": nodes_visited,
            "error_count": len(errors),
            "errors": errors
        }


# ============================================================================
# Debug Agent
# ============================================================================

class DebugAgent:
    """
    Agent with built-in debugging capabilities.

    Features:
    - Verbose mode for step-by-step output
    - State inspection
    - Checkpoint navigation
    - Error handling with context
    """

    def __init__(self, verbose: bool = False):
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
        self.checkpointer = MemorySaver()
        self.verbose = verbose
        self.tracer = ExecutionTracer()
        self.graph = self._build_graph()
        self.inspector = StateInspector(self.graph, self.checkpointer)

    def _build_graph(self):
        """Build agent graph with debugging hooks."""

        def call_model(state: MessagesState) -> dict:
            if self.verbose:
                print(f"[DEBUG] Agent called with {len(state['messages'])} messages")

            response = self.llm.invoke(state["messages"])

            if self.verbose:
                print(f"[DEBUG] Agent response: {response.content[:100]}...")

            return {"messages": [response]}

        builder = StateGraph(MessagesState)
        builder.add_node("agent", call_model)
        builder.add_edge(START, "agent")
        builder.add_edge("agent", END)

        return builder.compile(checkpointer=self.checkpointer)

    def chat(self, message: str, thread_id: str = "default") -> str:
        """Chat with debugging."""
        config = {"configurable": {"thread_id": thread_id}}

        if self.verbose:
            print(f"\n[DEBUG] Starting chat for thread: {thread_id}")
            print(f"[DEBUG] Input: {message}")

        self.tracer.start()

        try:
            result = self.graph.invoke(
                {"messages": [HumanMessage(content=message)]},
                config
            )
            return result["messages"][-1].content
        except Exception as e:
            if self.verbose:
                print(f"[DEBUG] Error: {e}")
            raise

    def inspect_thread(self, thread_id: str) -> dict:
        """Inspect a thread's current state."""
        return self.inspector.get_current_state(thread_id)

    def get_history(self, thread_id: str, limit: int = 10) -> list:
        """Get checkpoint history for a thread."""
        return self.inspector.list_checkpoints(thread_id, limit)

    def replay_from_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        new_message: str
    ) -> str:
        """Replay from a specific checkpoint with a new message."""
        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id
            }
        }

        if self.verbose:
            print(f"[DEBUG] Replaying from checkpoint: {checkpoint_id}")

        result = self.graph.invoke(
            {"messages": [HumanMessage(content=new_message)]},
            config
        )

        return result["messages"][-1].content


# ============================================================================
# Error Analysis
# ============================================================================

class ErrorAnalyzer:
    """
    Analyze and categorize agent errors.

    Categories:
    - LLM errors (rate limits, content filters)
    - Tool errors (execution failures)
    - Graph errors (recursion, invalid state)
    - Timeout errors
    """

    ERROR_CATEGORIES = {
        "rate_limit": ["rate limit", "quota exceeded", "too many requests"],
        "content_filter": ["content filter", "safety", "blocked"],
        "timeout": ["timeout", "timed out", "deadline"],
        "recursion": ["recursion", "max iterations", "loop detected"],
        "tool_error": ["tool", "function", "execution failed"],
    }

    def categorize(self, error: Exception) -> dict:
        """Categorize an error."""
        error_str = str(error).lower()

        for category, keywords in self.ERROR_CATEGORIES.items():
            if any(kw in error_str for kw in keywords):
                return {
                    "category": category,
                    "error_type": type(error).__name__,
                    "message": str(error),
                    "recoverable": category in ["rate_limit", "timeout"]
                }

        return {
            "category": "unknown",
            "error_type": type(error).__name__,
            "message": str(error),
            "recoverable": False
        }

    def suggest_fix(self, error_analysis: dict) -> str:
        """Suggest a fix for the error."""
        suggestions = {
            "rate_limit": "Implement exponential backoff or reduce request frequency",
            "content_filter": "Review input for policy violations, add content preprocessing",
            "timeout": "Increase timeout, break into smaller operations, or optimize prompts",
            "recursion": "Add recursion limit to graph, review conditional edges",
            "tool_error": "Check tool implementation, validate inputs, add error handling",
            "unknown": "Review stack trace, add logging for more context"
        }
        return suggestions.get(error_analysis["category"], "No suggestion available")


# ============================================================================
# Message History Analyzer
# ============================================================================

class MessageAnalyzer:
    """Analyze message history for debugging."""

    def analyze_conversation(self, messages: list[BaseMessage]) -> dict:
        """Analyze a conversation for debugging."""
        human_msgs = [m for m in messages if isinstance(m, HumanMessage)]
        ai_msgs = [m for m in messages if isinstance(m, AIMessage)]

        return {
            "total_messages": len(messages),
            "human_messages": len(human_msgs),
            "ai_messages": len(ai_msgs),
            "avg_human_length": (
                sum(len(m.content) for m in human_msgs) / len(human_msgs)
                if human_msgs else 0
            ),
            "avg_ai_length": (
                sum(len(m.content) for m in ai_msgs) / len(ai_msgs)
                if ai_msgs else 0
            ),
            "conversation_turns": min(len(human_msgs), len(ai_msgs))
        }

    def find_issues(self, messages: list[BaseMessage]) -> list[str]:
        """Find potential issues in message history."""
        issues = []

        if not messages:
            issues.append("Empty message history")
            return issues

        # Check for very long messages
        for i, msg in enumerate(messages):
            if len(msg.content) > 10000:
                issues.append(f"Message {i} is very long ({len(msg.content)} chars)")

        # Check for repetition
        contents = [m.content for m in messages]
        if len(contents) != len(set(contents)):
            issues.append("Duplicate messages detected")

        # Check conversation flow
        for i in range(1, len(messages)):
            prev_type = type(messages[i-1])
            curr_type = type(messages[i])
            if prev_type == curr_type and prev_type in (HumanMessage, AIMessage):
                issues.append(f"Consecutive same-type messages at position {i}")

        return issues


# ============================================================================
# Debug Session
# ============================================================================

class DebugSession:
    """
    Interactive debug session for agents.

    Provides a REPL-like interface for debugging.
    """

    def __init__(self, agent: DebugAgent):
        self.agent = agent
        self.current_thread = "debug-session"
        self.history: list[dict] = []

    def chat(self, message: str) -> str:
        """Send a message and record for debugging."""
        start = datetime.now()

        try:
            response = self.agent.chat(message, self.current_thread)
            duration = (datetime.now() - start).total_seconds()

            self.history.append({
                "input": message,
                "output": response,
                "duration_s": duration,
                "error": None,
                "timestamp": start.isoformat()
            })

            return response
        except Exception as e:
            self.history.append({
                "input": message,
                "output": None,
                "error": str(e),
                "timestamp": start.isoformat()
            })
            raise

    def inspect(self) -> dict:
        """Inspect current thread state."""
        return self.agent.inspect_thread(self.current_thread)

    def show_history(self) -> list:
        """Show debug session history."""
        return self.history

    def switch_thread(self, thread_id: str):
        """Switch to a different thread."""
        self.current_thread = thread_id
        print(f"Switched to thread: {thread_id}")

    def replay(self, checkpoint_id: str, message: str) -> str:
        """Replay from a checkpoint."""
        return self.agent.replay_from_checkpoint(
            self.current_thread,
            checkpoint_id,
            message
        )


# ============================================================================
# Demo Functions
# ============================================================================

def demo_state_inspection():
    """Demonstrate state inspection."""

    print("=== State Inspection Demo ===\n")

    agent = DebugAgent(verbose=True)

    # Have a conversation
    thread_id = "inspect-demo"
    agent.chat("Hello!", thread_id)
    agent.chat("What is 2+2?", thread_id)

    # Inspect state
    state = agent.inspect_thread(thread_id)
    print(f"\nCurrent state has {len(state['values'].get('messages', []))} messages")
    print(f"Next nodes: {state['next']}")

    # List checkpoints
    checkpoints = agent.get_history(thread_id)
    print(f"\nCheckpoint history: {len(checkpoints)} checkpoints")
    for cp in checkpoints[:3]:
        print(f"  - {cp['checkpoint_id'][:20]}...")


def demo_error_analysis():
    """Demonstrate error analysis."""

    print("=== Error Analysis Demo ===\n")

    analyzer = ErrorAnalyzer()

    # Simulate different errors
    errors = [
        Exception("Rate limit exceeded. Please wait 60 seconds."),
        Exception("Content blocked by safety filter"),
        GraphRecursionError("Maximum recursion depth exceeded"),
        Exception("Tool execution failed: invalid input"),
    ]

    for error in errors:
        analysis = analyzer.categorize(error)
        fix = analyzer.suggest_fix(analysis)
        print(f"Error: {error}")
        print(f"  Category: {analysis['category']}")
        print(f"  Recoverable: {analysis['recoverable']}")
        print(f"  Fix: {fix}\n")


def demo_message_analysis():
    """Demonstrate message analysis."""

    print("=== Message Analysis Demo ===\n")

    messages = [
        HumanMessage(content="Hello!"),
        AIMessage(content="Hi there! How can I help you today?"),
        HumanMessage(content="What is machine learning?"),
        AIMessage(content="Machine learning is a subset of AI that enables systems to learn from data..."),
        HumanMessage(content="Give me an example"),
        AIMessage(content="A common example is email spam filtering..."),
    ]

    analyzer = MessageAnalyzer()

    stats = analyzer.analyze_conversation(messages)
    print("Conversation stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    issues = analyzer.find_issues(messages)
    print(f"\nIssues found: {len(issues)}")
    for issue in issues:
        print(f"  - {issue}")


def demo_debug_session():
    """Demonstrate interactive debug session."""

    print("=== Debug Session Demo ===\n")

    agent = DebugAgent(verbose=False)
    session = DebugSession(agent)

    # Simulate a debug session
    print("Starting debug session...\n")

    session.chat("What is Python?")
    session.chat("How do I install it?")

    print("Session history:")
    for entry in session.show_history():
        print(f"  In: {entry['input'][:30]}...")
        print(f"  Out: {entry['output'][:30] if entry['output'] else 'ERROR'}...")
        print(f"  Time: {entry.get('duration_s', 0):.2f}s\n")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("Debugging Workflow Demonstrations\n")
    print("=" * 50 + "\n")

    demo_state_inspection()
    print("\n" + "=" * 50 + "\n")

    demo_error_analysis()
    print("\n" + "=" * 50 + "\n")

    demo_message_analysis()
    print("\n" + "=" * 50 + "\n")

    demo_debug_session()
