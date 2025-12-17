#!/usr/bin/env python3
"""
Evaluation Runner for LangGraph Agents.

Run systematic evaluations using LangSmith:
- Dataset-based evaluation
- Custom evaluators
- Experiment tracking
- Results analysis
"""

import os
from typing import Callable, Any, Optional
from datetime import datetime

from langsmith import Client
from langsmith.evaluation import evaluate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver


# ============================================================================
# Basic Evaluation Setup
# ============================================================================

def create_langsmith_client() -> Client:
    """
    Create LangSmith client for evaluation.

    Requires:
        LANGSMITH_API_KEY environment variable
    """
    return Client()


# ============================================================================
# Target Functions
# ============================================================================

def create_simple_agent() -> Callable:
    """
    Create a simple agent for evaluation.

    Returns a function that takes inputs and returns outputs.
    """
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    def agent_function(inputs: dict) -> dict:
        """Target function for evaluation."""
        question = inputs.get("question", inputs.get("input", ""))

        response = llm.invoke([HumanMessage(content=question)])

        return {
            "answer": response.content,
            "model": "gemini-2.5-flash"
        }

    return agent_function


def create_rag_agent() -> Callable:
    """Create a RAG agent for evaluation."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    def rag_function(inputs: dict) -> dict:
        """RAG target function."""
        question = inputs.get("question", "")
        context = inputs.get("context", "")

        prompt = f"""Answer the question based on the context.

Context:
{context}

Question: {question}

Answer:"""

        response = llm.invoke([HumanMessage(content=prompt)])

        return {
            "answer": response.content,
            "context_used": context
        }

    return rag_function


# ============================================================================
# Basic Evaluators
# ============================================================================

def exact_match_evaluator(run, example) -> dict:
    """
    Check if prediction exactly matches reference.

    Args:
        run: The run object with outputs
        example: The example with expected outputs

    Returns:
        dict with key and score
    """
    prediction = run.outputs.get("answer", "").strip().lower()
    reference = example.outputs.get("answer", "").strip().lower()

    return {
        "key": "exact_match",
        "score": 1.0 if prediction == reference else 0.0
    }


def contains_evaluator(run, example) -> dict:
    """Check if prediction contains expected keywords."""
    prediction = run.outputs.get("answer", "").lower()
    keywords = example.outputs.get("keywords", [])

    if not keywords:
        return {"key": "contains_keywords", "score": 1.0}

    matches = sum(1 for kw in keywords if kw.lower() in prediction)
    score = matches / len(keywords)

    return {
        "key": "contains_keywords",
        "score": score,
        "comment": f"Matched {matches}/{len(keywords)} keywords"
    }


def length_evaluator(run, example) -> dict:
    """Check if response length is within acceptable range."""
    prediction = run.outputs.get("answer", "")
    min_length = example.outputs.get("min_length", 10)
    max_length = example.outputs.get("max_length", 1000)

    length = len(prediction)

    if min_length <= length <= max_length:
        score = 1.0
    elif length < min_length:
        score = length / min_length
    else:
        score = max_length / length

    return {
        "key": "length_check",
        "score": min(1.0, score),
        "comment": f"Length: {length} chars"
    }


# ============================================================================
# Run Evaluation
# ============================================================================

def run_evaluation(
    target_function: Callable,
    dataset_name: str,
    evaluators: list[Callable],
    experiment_prefix: str = "eval",
    metadata: Optional[dict] = None
) -> dict:
    """
    Run evaluation against a dataset.

    Args:
        target_function: Function to evaluate (inputs -> outputs)
        dataset_name: Name of LangSmith dataset
        evaluators: List of evaluator functions
        experiment_prefix: Prefix for experiment name
        metadata: Additional metadata for the experiment

    Returns:
        Evaluation results summary

    Example:
        results = run_evaluation(
            target_function=my_agent,
            dataset_name="qa_test_set",
            evaluators=[exact_match_evaluator, length_evaluator],
            experiment_prefix="qa_eval",
            metadata={"model": "gemini-2.5-flash"}
        )
    """
    results = evaluate(
        target_function,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=experiment_prefix,
        metadata=metadata or {}
    )

    # Process results
    summary = {
        "experiment_name": f"{experiment_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "dataset": dataset_name,
        "total_examples": 0,
        "scores": {}
    }

    # Aggregate scores
    score_totals = {}
    score_counts = {}

    for result in results:
        summary["total_examples"] += 1

        for eval_result in result.get("evaluation_results", []):
            key = eval_result.get("key", "unknown")
            score = eval_result.get("score", 0)

            if key not in score_totals:
                score_totals[key] = 0
                score_counts[key] = 0

            score_totals[key] += score
            score_counts[key] += 1

    # Calculate averages
    for key in score_totals:
        summary["scores"][key] = {
            "average": score_totals[key] / score_counts[key],
            "count": score_counts[key]
        }

    return summary


# ============================================================================
# Experiment Comparison
# ============================================================================

class ExperimentComparison:
    """Compare results across multiple experiments."""

    def __init__(self, client: Optional[Client] = None):
        self.client = client or create_langsmith_client()
        self.experiments: list[dict] = []

    def add_experiment(self, name: str, results: dict):
        """Add experiment results for comparison."""
        self.experiments.append({
            "name": name,
            "results": results,
            "timestamp": datetime.now().isoformat()
        })

    def compare(self, metric: str = "exact_match") -> dict:
        """Compare experiments on a specific metric."""
        comparison = {}

        for exp in self.experiments:
            scores = exp["results"].get("scores", {})
            metric_data = scores.get(metric, {})
            comparison[exp["name"]] = {
                "average": metric_data.get("average", 0),
                "count": metric_data.get("count", 0)
            }

        # Sort by average score
        sorted_experiments = sorted(
            comparison.items(),
            key=lambda x: x[1]["average"],
            reverse=True
        )

        return {
            "metric": metric,
            "ranking": [
                {"name": name, **data}
                for name, data in sorted_experiments
            ],
            "best": sorted_experiments[0][0] if sorted_experiments else None
        }

    def summary_table(self) -> str:
        """Generate a summary table of all experiments."""
        if not self.experiments:
            return "No experiments to compare"

        # Get all metrics
        all_metrics = set()
        for exp in self.experiments:
            all_metrics.update(exp["results"].get("scores", {}).keys())

        # Build table
        lines = ["Experiment Comparison", "=" * 50]
        header = f"{'Experiment':<20}"
        for metric in sorted(all_metrics):
            header += f" {metric:<15}"
        lines.append(header)
        lines.append("-" * 50)

        for exp in self.experiments:
            row = f"{exp['name']:<20}"
            scores = exp["results"].get("scores", {})
            for metric in sorted(all_metrics):
                avg = scores.get(metric, {}).get("average", 0)
                row += f" {avg:<15.3f}"
            lines.append(row)

        return "\n".join(lines)


# ============================================================================
# Batch Evaluation
# ============================================================================

def run_batch_evaluation(
    target_functions: dict[str, Callable],
    dataset_name: str,
    evaluators: list[Callable]
) -> dict:
    """
    Run evaluation for multiple target functions.

    Args:
        target_functions: Dict of name -> function
        dataset_name: Dataset to evaluate against
        evaluators: List of evaluators

    Returns:
        Combined results for all targets
    """
    comparison = ExperimentComparison()

    for name, func in target_functions.items():
        print(f"Evaluating: {name}")

        results = run_evaluation(
            target_function=func,
            dataset_name=dataset_name,
            evaluators=evaluators,
            experiment_prefix=name,
            metadata={"variant": name}
        )

        comparison.add_experiment(name, results)

    return {
        "experiments": comparison.experiments,
        "comparison": comparison.summary_table()
    }


# ============================================================================
# Quick Evaluation (No Dataset Required)
# ============================================================================

def quick_eval(
    target_function: Callable,
    test_cases: list[dict],
    evaluators: list[Callable]
) -> dict:
    """
    Quick evaluation without LangSmith dataset.

    Args:
        target_function: Function to evaluate
        test_cases: List of {"inputs": {...}, "outputs": {...}}
        evaluators: List of evaluator functions

    Returns:
        Evaluation results

    Example:
        results = quick_eval(
            target_function=my_agent,
            test_cases=[
                {"inputs": {"question": "2+2?"}, "outputs": {"answer": "4"}},
                {"inputs": {"question": "Capital of France?"}, "outputs": {"answer": "Paris"}}
            ],
            evaluators=[exact_match_evaluator]
        )
    """
    results = []

    for i, case in enumerate(test_cases):
        # Run target function
        outputs = target_function(case["inputs"])

        # Create mock run and example objects
        class MockRun:
            def __init__(self, outputs):
                self.outputs = outputs

        class MockExample:
            def __init__(self, outputs):
                self.outputs = outputs

        run = MockRun(outputs)
        example = MockExample(case["outputs"])

        # Run evaluators
        eval_results = []
        for evaluator in evaluators:
            eval_result = evaluator(run, example)
            eval_results.append(eval_result)

        results.append({
            "case_id": i,
            "inputs": case["inputs"],
            "expected": case["outputs"],
            "actual": outputs,
            "evaluations": eval_results
        })

    # Aggregate scores
    summary = {"cases": results, "scores": {}}
    for result in results:
        for eval_result in result["evaluations"]:
            key = eval_result["key"]
            score = eval_result["score"]
            if key not in summary["scores"]:
                summary["scores"][key] = []
            summary["scores"][key].append(score)

    # Calculate averages
    for key, scores in summary["scores"].items():
        summary["scores"][key] = {
            "average": sum(scores) / len(scores),
            "min": min(scores),
            "max": max(scores),
            "count": len(scores)
        }

    return summary


# ============================================================================
# Demo Functions
# ============================================================================

def demo_quick_evaluation():
    """Demonstrate quick evaluation without dataset."""

    print("=== Quick Evaluation Demo ===\n")

    agent = create_simple_agent()

    test_cases = [
        {
            "inputs": {"question": "What is 2 + 2?"},
            "outputs": {"answer": "4", "keywords": ["4", "four"]}
        },
        {
            "inputs": {"question": "What is the capital of France?"},
            "outputs": {"answer": "Paris", "keywords": ["paris"]}
        },
        {
            "inputs": {"question": "What color is the sky?"},
            "outputs": {"answer": "blue", "keywords": ["blue"]}
        }
    ]

    results = quick_eval(
        target_function=agent,
        test_cases=test_cases,
        evaluators=[contains_evaluator, length_evaluator]
    )

    print(f"Evaluated {len(results['cases'])} test cases\n")

    for key, scores in results["scores"].items():
        print(f"{key}:")
        print(f"  Average: {scores['average']:.2f}")
        print(f"  Range: {scores['min']:.2f} - {scores['max']:.2f}")


def demo_evaluator_types():
    """Demonstrate different evaluator types."""

    print("=== Evaluator Types Demo ===\n")

    # Mock run and example
    class MockRun:
        outputs = {"answer": "The capital of France is Paris."}

    class MockExample:
        outputs = {
            "answer": "Paris",
            "keywords": ["paris", "capital", "france"],
            "min_length": 10,
            "max_length": 100
        }

    run = MockRun()
    example = MockExample()

    evaluators = [
        ("Exact Match", exact_match_evaluator),
        ("Contains Keywords", contains_evaluator),
        ("Length Check", length_evaluator),
    ]

    print("Testing evaluators on: 'The capital of France is Paris.'\n")

    for name, evaluator in evaluators:
        result = evaluator(run, example)
        print(f"{name}:")
        print(f"  Score: {result['score']:.2f}")
        if "comment" in result:
            print(f"  Comment: {result['comment']}")
        print()


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("Evaluation Runner Demonstrations\n")
    print("=" * 50 + "\n")

    demo_evaluator_types()
    print("=" * 50 + "\n")

    demo_quick_evaluation()
