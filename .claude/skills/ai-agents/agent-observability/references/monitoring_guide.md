# Monitoring Guide

Production monitoring and debugging for LangGraph agents using LangSmith.

## Dashboard Overview

### Key Metrics

```
Latency       → P50, P95, P99 response times
Success Rate  → Percentage of successful runs
Token Usage   → Input/output tokens per run
Cost          → Estimated cost per run
Throughput    → Requests per minute/hour
```

### Filtering Traces

```
By Project     → Filter to specific agent
By Tags        → production, experiment-A, user-tier:premium
By Metadata    → user_id, session_id, feature_flag
By Time        → Last hour, day, week, custom range
By Status      → Success, Error, Running
```

## Thread History Inspection

### Get Thread History

```python
from langsmith import Client

client = Client()

# Get thread history (via LangGraph)
history = list(graph.get_state_history(config))

for state in history:
    print(f"Checkpoint: {state.config['configurable']['checkpoint_id']}")
    print(f"Messages: {len(state.values.get('messages', []))}")
    print(f"Next: {state.next}")
```

### Analyze Conversation Flow

```python
def analyze_thread(graph, thread_id: str):
    """Analyze a conversation thread."""
    config = {"configurable": {"thread_id": thread_id}}

    history = list(graph.get_state_history(config))

    analysis = {
        "total_checkpoints": len(history),
        "message_progression": [],
        "nodes_visited": []
    }

    for state in history:
        msgs = state.values.get("messages", [])
        analysis["message_progression"].append(len(msgs))
        if state.next:
            analysis["nodes_visited"].extend(state.next)

    return analysis
```

## Error Monitoring

### Error Categories

```python
ERROR_CATEGORIES = {
    "llm_error": [
        "rate_limit",
        "context_length",
        "content_filter",
        "api_error"
    ],
    "tool_error": [
        "execution_failed",
        "invalid_input",
        "timeout"
    ],
    "graph_error": [
        "recursion_limit",
        "invalid_state",
        "edge_not_found"
    ]
}
```

### Error Tracking Pattern

```python
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree

@traceable(name="monitored_operation")
def monitored_operation(input_data):
    run_tree = get_current_run_tree()

    try:
        result = process(input_data)

        # Log success metrics
        if run_tree:
            run_tree.extra["metadata"]["status"] = "success"

        return result

    except Exception as e:
        # Log error details
        if run_tree:
            run_tree.extra["metadata"]["status"] = "error"
            run_tree.extra["metadata"]["error_type"] = type(e).__name__
            run_tree.extra["metadata"]["error_message"] = str(e)
        raise
```

### Alerting Patterns

```python
class AlertManager:
    """Monitor and alert on agent issues."""

    def __init__(self, error_threshold: float = 0.05):
        self.error_threshold = error_threshold
        self.recent_errors = []
        self.recent_successes = []

    def record(self, success: bool):
        if success:
            self.recent_successes.append(datetime.now())
        else:
            self.recent_errors.append(datetime.now())

        # Check error rate
        self._check_alerts()

    def _check_alerts(self):
        # Calculate error rate over last 100 requests
        total = len(self.recent_errors) + len(self.recent_successes)
        if total >= 100:
            error_rate = len(self.recent_errors) / total
            if error_rate > self.error_threshold:
                self._send_alert(f"Error rate {error_rate:.1%} exceeds threshold")

    def _send_alert(self, message: str):
        print(f"ALERT: {message}")
        # Integrate with PagerDuty, Slack, etc.
```

## Performance Monitoring

### Latency Tracking

```python
import time
from dataclasses import dataclass

@dataclass
class LatencyMetrics:
    p50: float
    p95: float
    p99: float
    avg: float
    max: float

class LatencyMonitor:
    def __init__(self):
        self.latencies = []

    def record(self, duration_ms: float):
        self.latencies.append(duration_ms)

    def get_metrics(self) -> LatencyMetrics:
        if not self.latencies:
            return LatencyMetrics(0, 0, 0, 0, 0)

        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)

        return LatencyMetrics(
            p50=sorted_latencies[int(n * 0.5)],
            p95=sorted_latencies[int(n * 0.95)],
            p99=sorted_latencies[int(n * 0.99)],
            avg=sum(sorted_latencies) / n,
            max=max(sorted_latencies)
        )
```

### Token Usage Monitoring

```python
class TokenMonitor:
    """Monitor token usage and costs."""

    def __init__(self):
        self.usage_log = []

    def record(self, input_tokens: int, output_tokens: int, model: str):
        self.usage_log.append({
            "timestamp": datetime.now(),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "model": model
        })

    def daily_summary(self) -> dict:
        today = datetime.now().date()
        today_usage = [
            u for u in self.usage_log
            if u["timestamp"].date() == today
        ]

        return {
            "total_input": sum(u["input_tokens"] for u in today_usage),
            "total_output": sum(u["output_tokens"] for u in today_usage),
            "request_count": len(today_usage)
        }
```

## Debugging Workflows

### Step-by-Step Analysis

```python
def debug_run(graph, thread_id: str):
    """Debug a specific run step by step."""
    config = {"configurable": {"thread_id": thread_id}}

    # Get all states
    history = list(graph.get_state_history(config))

    print(f"Total checkpoints: {len(history)}")

    for i, state in enumerate(reversed(history)):
        print(f"\n--- Step {i + 1} ---")
        print(f"Next nodes: {state.next}")

        messages = state.values.get("messages", [])
        if messages:
            last_msg = messages[-1]
            print(f"Last message type: {type(last_msg).__name__}")
            print(f"Content preview: {last_msg.content[:100]}...")

        # Check for tool calls
        if hasattr(messages[-1], 'tool_calls') and messages[-1].tool_calls:
            print(f"Tool calls: {[tc['name'] for tc in messages[-1].tool_calls]}")
```

### Replay and Compare

```python
def replay_with_variation(graph, thread_id: str, checkpoint_id: str):
    """Replay from checkpoint with different input."""

    # Get state at checkpoint
    config = {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id
        }
    }

    original_state = graph.get_state(config)
    print(f"Original state has {len(original_state.values.get('messages', []))} messages")

    # Replay with new input
    new_result = graph.invoke(
        {"messages": [HumanMessage(content="Alternative question")]},
        config
    )

    return {
        "original_messages": len(original_state.values.get("messages", [])),
        "new_messages": len(new_result.get("messages", [])),
        "diverged_at": checkpoint_id
    }
```

## Production Checklist

### Pre-Launch

```markdown
- [ ] LangSmith project created for production
- [ ] API key stored in secret manager
- [ ] Environment variables configured
- [ ] Sample rate set appropriately
- [ ] Error alerting configured
- [ ] Cost budgets set
- [ ] Team access permissions configured
```

### Monitoring Setup

```markdown
- [ ] Latency alerts configured (P95 > threshold)
- [ ] Error rate alerts configured (> 5%)
- [ ] Token usage tracking enabled
- [ ] Cost monitoring dashboard created
- [ ] Daily/weekly report automation
```

### Debugging Readiness

```markdown
- [ ] Meaningful trace names
- [ ] User ID in metadata
- [ ] Session/request ID tracking
- [ ] Feature flags in tags
- [ ] Error context logging
```

## Integration Examples

### Slack Alerts

```python
import requests

def send_slack_alert(message: str, webhook_url: str):
    requests.post(webhook_url, json={"text": message})

# Usage
if error_rate > 0.05:
    send_slack_alert(
        f"Agent error rate: {error_rate:.1%}",
        os.environ["SLACK_WEBHOOK"]
    )
```

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram

agent_requests = Counter(
    "agent_requests_total",
    "Total agent requests",
    ["status", "model"]
)

agent_latency = Histogram(
    "agent_latency_seconds",
    "Agent request latency",
    ["model"]
)

# Record metrics
agent_requests.labels(status="success", model="gemini-2.5-flash").inc()
agent_latency.labels(model="gemini-2.5-flash").observe(duration)
```

### Custom Dashboard

```python
class DashboardMetrics:
    """Aggregate metrics for dashboard."""

    def __init__(self):
        self.metrics = {
            "requests_1h": 0,
            "errors_1h": 0,
            "avg_latency_ms": 0,
            "total_tokens_1h": 0,
            "estimated_cost_1h": 0
        }

    def refresh(self, client: Client, project: str):
        """Refresh metrics from LangSmith."""
        # Query LangSmith API for metrics
        # Update self.metrics
        pass

    def to_json(self) -> dict:
        return self.metrics
```
