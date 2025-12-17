#!/usr/bin/env python3
"""
Custom Evaluators for LangGraph Agents.

Build custom scoring functions for agent evaluation:
- Text similarity evaluators
- Structured output evaluators
- Multi-metric evaluators
- Domain-specific evaluators
"""

import re
import math
from typing import Callable, Any, Optional
from collections import Counter


# ============================================================================
# Text Similarity Evaluators
# ============================================================================

def jaccard_similarity_evaluator(run, example) -> dict:
    """
    Evaluate using Jaccard similarity between word sets.

    Jaccard = |A ∩ B| / |A ∪ B|
    """
    prediction = run.outputs.get("answer", "").lower()
    reference = example.outputs.get("answer", "").lower()

    # Tokenize
    pred_words = set(prediction.split())
    ref_words = set(reference.split())

    if not pred_words and not ref_words:
        score = 1.0
    elif not pred_words or not ref_words:
        score = 0.0
    else:
        intersection = pred_words & ref_words
        union = pred_words | ref_words
        score = len(intersection) / len(union)

    return {
        "key": "jaccard_similarity",
        "score": score,
        "comment": f"Word overlap: {len(pred_words & ref_words)}/{len(pred_words | ref_words)}"
    }


def cosine_similarity_evaluator(run, example) -> dict:
    """
    Evaluate using cosine similarity of word frequency vectors.

    Cosine = (A · B) / (||A|| × ||B||)
    """
    prediction = run.outputs.get("answer", "").lower()
    reference = example.outputs.get("answer", "").lower()

    # Create word frequency vectors
    pred_counter = Counter(prediction.split())
    ref_counter = Counter(reference.split())

    # Get all words
    all_words = set(pred_counter.keys()) | set(ref_counter.keys())

    if not all_words:
        return {"key": "cosine_similarity", "score": 1.0}

    # Calculate dot product and magnitudes
    dot_product = sum(
        pred_counter.get(word, 0) * ref_counter.get(word, 0)
        for word in all_words
    )

    pred_magnitude = math.sqrt(sum(v ** 2 for v in pred_counter.values()))
    ref_magnitude = math.sqrt(sum(v ** 2 for v in ref_counter.values()))

    if pred_magnitude == 0 or ref_magnitude == 0:
        score = 0.0
    else:
        score = dot_product / (pred_magnitude * ref_magnitude)

    return {
        "key": "cosine_similarity",
        "score": score
    }


def levenshtein_evaluator(run, example) -> dict:
    """
    Evaluate using normalized Levenshtein distance.

    Score = 1 - (edit_distance / max_length)
    """
    prediction = run.outputs.get("answer", "").lower()
    reference = example.outputs.get("answer", "").lower()

    def levenshtein_distance(s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    distance = levenshtein_distance(prediction, reference)
    max_length = max(len(prediction), len(reference), 1)
    score = 1 - (distance / max_length)

    return {
        "key": "levenshtein_similarity",
        "score": max(0, score),
        "comment": f"Edit distance: {distance}"
    }


# ============================================================================
# Semantic Evaluators
# ============================================================================

def semantic_similarity_evaluator(embedding_model=None):
    """
    Create evaluator using embedding similarity.

    Returns a configured evaluator function.
    """
    if embedding_model is None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        embedding_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

    def evaluator(run, example) -> dict:
        prediction = run.outputs.get("answer", "")
        reference = example.outputs.get("answer", "")

        if not prediction or not reference:
            return {"key": "semantic_similarity", "score": 0.0}

        # Get embeddings
        pred_embedding = embedding_model.embed_query(prediction)
        ref_embedding = embedding_model.embed_query(reference)

        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(pred_embedding, ref_embedding))
        pred_norm = math.sqrt(sum(a ** 2 for a in pred_embedding))
        ref_norm = math.sqrt(sum(b ** 2 for b in ref_embedding))

        score = dot_product / (pred_norm * ref_norm) if pred_norm and ref_norm else 0

        return {
            "key": "semantic_similarity",
            "score": max(0, score)  # Ensure non-negative
        }

    return evaluator


# ============================================================================
# Structured Output Evaluators
# ============================================================================

def json_structure_evaluator(run, example) -> dict:
    """
    Evaluate if JSON output has expected structure.
    """
    import json

    prediction = run.outputs.get("answer", "")
    expected_keys = example.outputs.get("expected_keys", [])

    try:
        parsed = json.loads(prediction)

        if not expected_keys:
            return {"key": "json_structure", "score": 1.0}

        present_keys = set(parsed.keys()) if isinstance(parsed, dict) else set()
        expected_set = set(expected_keys)

        missing = expected_set - present_keys
        extra = present_keys - expected_set

        score = len(present_keys & expected_set) / len(expected_set) if expected_set else 1.0

        return {
            "key": "json_structure",
            "score": score,
            "comment": f"Missing: {missing}, Extra: {extra}"
        }

    except json.JSONDecodeError:
        return {
            "key": "json_structure",
            "score": 0.0,
            "comment": "Invalid JSON"
        }


def schema_compliance_evaluator(run, example) -> dict:
    """
    Evaluate if output complies with a schema.
    """
    from pydantic import ValidationError, create_model
    import json

    prediction = run.outputs.get("answer", "")
    schema = example.outputs.get("schema", {})

    if not schema:
        return {"key": "schema_compliance", "score": 1.0}

    try:
        parsed = json.loads(prediction)

        # Create dynamic Pydantic model from schema
        fields = {}
        for field_name, field_type in schema.items():
            if field_type == "str":
                fields[field_name] = (str, ...)
            elif field_type == "int":
                fields[field_name] = (int, ...)
            elif field_type == "float":
                fields[field_name] = (float, ...)
            elif field_type == "bool":
                fields[field_name] = (bool, ...)
            elif field_type == "list":
                fields[field_name] = (list, ...)
            elif field_type == "dict":
                fields[field_name] = (dict, ...)

        DynamicModel = create_model("DynamicModel", **fields)
        DynamicModel(**parsed)

        return {"key": "schema_compliance", "score": 1.0}

    except (json.JSONDecodeError, ValidationError) as e:
        return {
            "key": "schema_compliance",
            "score": 0.0,
            "comment": str(e)[:100]
        }


# ============================================================================
# Quality Evaluators
# ============================================================================

def fluency_evaluator(run, example) -> dict:
    """
    Evaluate response fluency (basic heuristics).

    Checks:
    - Sentence structure
    - Capitalization
    - Punctuation
    """
    prediction = run.outputs.get("answer", "")

    if not prediction:
        return {"key": "fluency", "score": 0.0}

    score = 1.0
    issues = []

    # Check starts with capital
    if prediction and not prediction[0].isupper():
        score -= 0.2
        issues.append("no_capital_start")

    # Check ends with punctuation
    if prediction and prediction[-1] not in ".!?":
        score -= 0.2
        issues.append("no_end_punctuation")

    # Check for repeated words
    words = prediction.lower().split()
    for i in range(len(words) - 1):
        if words[i] == words[i + 1] and words[i] not in ["the", "a", "an", "very"]:
            score -= 0.1
            issues.append("repeated_word")
            break

    # Check for very short response
    if len(prediction) < 10:
        score -= 0.3
        issues.append("too_short")

    return {
        "key": "fluency",
        "score": max(0, score),
        "comment": ", ".join(issues) if issues else "good"
    }


def relevance_evaluator(run, example) -> dict:
    """
    Evaluate if response is relevant to the question.

    Uses keyword overlap between question and answer.
    """
    question = example.inputs.get("question", "").lower()
    prediction = run.outputs.get("answer", "").lower()

    # Extract content words (remove stopwords)
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "what", "how", "why", "when", "where", "who"}

    question_words = set(question.split()) - stopwords
    answer_words = set(prediction.split()) - stopwords

    if not question_words:
        return {"key": "relevance", "score": 1.0}

    # Check how many question keywords appear in answer
    overlap = question_words & answer_words
    score = len(overlap) / len(question_words)

    return {
        "key": "relevance",
        "score": min(1.0, score),
        "comment": f"Keyword overlap: {len(overlap)}/{len(question_words)}"
    }


# ============================================================================
# Multi-Metric Evaluator
# ============================================================================

def create_composite_evaluator(
    evaluators: list[tuple[str, Callable, float]]
) -> Callable:
    """
    Create a composite evaluator from multiple evaluators.

    Args:
        evaluators: List of (name, evaluator_func, weight) tuples

    Returns:
        Composite evaluator function
    """
    def composite_evaluator(run, example) -> dict:
        total_score = 0
        total_weight = 0
        details = {}

        for name, evaluator, weight in evaluators:
            result = evaluator(run, example)
            score = result.get("score", 0)

            total_score += score * weight
            total_weight += weight
            details[name] = score

        final_score = total_score / total_weight if total_weight > 0 else 0

        return {
            "key": "composite_score",
            "score": final_score,
            "comment": str(details)
        }

    return composite_evaluator


# ============================================================================
# Domain-Specific Evaluators
# ============================================================================

def code_correctness_evaluator(run, example) -> dict:
    """
    Evaluate if generated code is syntactically correct.
    """
    import ast

    prediction = run.outputs.get("answer", "")

    # Extract code blocks
    code_blocks = re.findall(r"```python\n(.*?)```", prediction, re.DOTALL)
    if not code_blocks:
        code_blocks = re.findall(r"```\n(.*?)```", prediction, re.DOTALL)
    if not code_blocks:
        code_blocks = [prediction]

    valid_blocks = 0
    for code in code_blocks:
        try:
            ast.parse(code)
            valid_blocks += 1
        except SyntaxError:
            pass

    score = valid_blocks / len(code_blocks) if code_blocks else 0

    return {
        "key": "code_correctness",
        "score": score,
        "comment": f"{valid_blocks}/{len(code_blocks)} valid"
    }


def math_accuracy_evaluator(run, example) -> dict:
    """
    Evaluate mathematical accuracy.
    """
    prediction = run.outputs.get("answer", "")
    expected = example.outputs.get("answer", "")

    # Extract numbers from both
    pred_numbers = re.findall(r"-?\d+\.?\d*", prediction)
    exp_numbers = re.findall(r"-?\d+\.?\d*", expected)

    if not exp_numbers:
        return {"key": "math_accuracy", "score": 1.0}

    # Check if expected number appears in prediction
    for exp_num in exp_numbers:
        if exp_num in pred_numbers:
            return {"key": "math_accuracy", "score": 1.0}

        # Check with tolerance
        try:
            exp_val = float(exp_num)
            for pred_num in pred_numbers:
                pred_val = float(pred_num)
                if abs(exp_val - pred_val) < 0.01 * abs(exp_val):
                    return {"key": "math_accuracy", "score": 1.0}
        except ValueError:
            pass

    return {
        "key": "math_accuracy",
        "score": 0.0,
        "comment": f"Expected: {exp_numbers}, Found: {pred_numbers}"
    }


# ============================================================================
# Evaluator Factory
# ============================================================================

class EvaluatorFactory:
    """Factory for creating and combining evaluators."""

    BUILTIN_EVALUATORS = {
        "exact_match": lambda r, e: {
            "key": "exact_match",
            "score": 1.0 if r.outputs.get("answer", "").strip().lower() ==
                          e.outputs.get("answer", "").strip().lower() else 0.0
        },
        "jaccard": jaccard_similarity_evaluator,
        "cosine": cosine_similarity_evaluator,
        "levenshtein": levenshtein_evaluator,
        "fluency": fluency_evaluator,
        "relevance": relevance_evaluator,
        "json_structure": json_structure_evaluator,
        "code_correctness": code_correctness_evaluator,
        "math_accuracy": math_accuracy_evaluator,
    }

    @classmethod
    def get(cls, name: str) -> Callable:
        """Get a built-in evaluator by name."""
        if name not in cls.BUILTIN_EVALUATORS:
            raise ValueError(f"Unknown evaluator: {name}. Available: {list(cls.BUILTIN_EVALUATORS.keys())}")
        return cls.BUILTIN_EVALUATORS[name]

    @classmethod
    def create_suite(cls, evaluator_names: list[str]) -> list[Callable]:
        """Create a suite of evaluators."""
        return [cls.get(name) for name in evaluator_names]

    @classmethod
    def list_available(cls) -> list[str]:
        """List available evaluators."""
        return list(cls.BUILTIN_EVALUATORS.keys())


# ============================================================================
# Demo Functions
# ============================================================================

def demo_text_similarity():
    """Demonstrate text similarity evaluators."""

    print("=== Text Similarity Evaluators Demo ===\n")

    class MockRun:
        outputs = {"answer": "The capital of France is Paris, a beautiful city."}

    class MockExample:
        outputs = {"answer": "Paris is the capital city of France."}

    run = MockRun()
    example = MockExample()

    evaluators = [
        ("Jaccard", jaccard_similarity_evaluator),
        ("Cosine", cosine_similarity_evaluator),
        ("Levenshtein", levenshtein_evaluator),
    ]

    print(f"Prediction: {run.outputs['answer']}")
    print(f"Reference: {example.outputs['answer']}\n")

    for name, evaluator in evaluators:
        result = evaluator(run, example)
        print(f"{name}: {result['score']:.3f}")


def demo_composite_evaluator():
    """Demonstrate composite evaluator."""

    print("=== Composite Evaluator Demo ===\n")

    composite = create_composite_evaluator([
        ("jaccard", jaccard_similarity_evaluator, 0.3),
        ("fluency", fluency_evaluator, 0.3),
        ("relevance", relevance_evaluator, 0.4),
    ])

    class MockRun:
        outputs = {"answer": "Paris is the capital of France."}

    class MockExample:
        inputs = {"question": "What is the capital of France?"}
        outputs = {"answer": "The capital of France is Paris."}

    result = composite(MockRun(), MockExample())
    print(f"Composite Score: {result['score']:.3f}")
    print(f"Details: {result['comment']}")


def demo_evaluator_factory():
    """Demonstrate evaluator factory."""

    print("=== Evaluator Factory Demo ===\n")

    print("Available evaluators:")
    for name in EvaluatorFactory.list_available():
        print(f"  - {name}")

    print("\nCreating evaluation suite...")
    suite = EvaluatorFactory.create_suite(["exact_match", "jaccard", "fluency"])
    print(f"Suite contains {len(suite)} evaluators")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("Custom Evaluators Demonstrations\n")
    print("=" * 50 + "\n")

    demo_text_similarity()
    print("\n" + "=" * 50 + "\n")

    demo_composite_evaluator()
    print("\n" + "=" * 50 + "\n")

    demo_evaluator_factory()
