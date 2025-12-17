#!/usr/bin/env python3
"""
LLM-as-Judge Evaluation for LangGraph Agents.

Use Gemini to evaluate agent outputs:
- Correctness judges
- Groundedness evaluation
- Coherence scoring
- Custom criteria evaluation
"""

import os
from typing import Optional, TypedDict, Literal
from enum import Enum

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


# ============================================================================
# Structured Output Schemas
# ============================================================================

class BinaryGrade(TypedDict):
    """Binary grading schema."""
    is_correct: bool
    reasoning: str


class ScoreGrade(TypedDict):
    """Numeric score grading schema."""
    score: int  # 1-5
    reasoning: str


class DetailedGrade(TypedDict):
    """Detailed grading schema."""
    score: int  # 1-5
    strengths: list[str]
    weaknesses: list[str]
    reasoning: str


# Pydantic models for structured output
class CorrectnessGrade(BaseModel):
    """Correctness evaluation result."""
    is_correct: bool = Field(description="Whether the answer is correct")
    reasoning: str = Field(description="Explanation for the grade")


class QualityGrade(BaseModel):
    """Quality score evaluation result."""
    score: int = Field(ge=1, le=5, description="Quality score from 1-5")
    reasoning: str = Field(description="Explanation for the score")


class DetailedEvaluation(BaseModel):
    """Detailed evaluation with multiple dimensions."""
    relevance: int = Field(ge=1, le=5, description="How relevant is the answer")
    accuracy: int = Field(ge=1, le=5, description="How accurate is the answer")
    completeness: int = Field(ge=1, le=5, description="How complete is the answer")
    clarity: int = Field(ge=1, le=5, description="How clear is the answer")
    overall: int = Field(ge=1, le=5, description="Overall quality score")
    reasoning: str = Field(description="Overall assessment")


# ============================================================================
# LLM Judge Base
# ============================================================================

class LLMJudge:
    """
    Base class for LLM-as-judge evaluation.

    Uses Gemini for evaluation with structured output.

    Example:
        judge = LLMJudge()
        result = judge.evaluate_correctness(
            question="What is 2+2?",
            answer="4",
            reference="The answer is 4"
        )
    """

    def __init__(self, model: str = "gemini-2.5-flash", temperature: float = 0.0):
        self.llm = ChatGoogleGenerativeAI(model=model, temperature=temperature)

    def _invoke_with_schema(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        """Invoke LLM with structured output."""
        structured_llm = self.llm.with_structured_output(schema)
        return structured_llm.invoke([HumanMessage(content=prompt)])


# ============================================================================
# Correctness Judge
# ============================================================================

class CorrectnessJudge(LLMJudge):
    """
    Judge for evaluating answer correctness.

    Compares agent output against a reference answer.
    """

    PROMPT_TEMPLATE = """You are evaluating an AI assistant's answer for correctness.

Question: {question}

Reference Answer: {reference}

Assistant's Answer: {answer}

Evaluate if the assistant's answer is correct. Consider:
1. Does it contain the correct information?
2. Are there any factual errors?
3. Is it consistent with the reference?

The answer doesn't need to be word-for-word identical, but must be factually correct."""

    def evaluate(
        self,
        question: str,
        answer: str,
        reference: str
    ) -> dict:
        """Evaluate answer correctness."""
        prompt = self.PROMPT_TEMPLATE.format(
            question=question,
            reference=reference,
            answer=answer
        )

        result = self._invoke_with_schema(prompt, CorrectnessGrade)

        return {
            "key": "correctness",
            "score": 1.0 if result.is_correct else 0.0,
            "reasoning": result.reasoning
        }


def correctness_evaluator(run, example) -> dict:
    """
    Evaluator function using correctness judge.

    Compatible with LangSmith evaluate().
    """
    judge = CorrectnessJudge()

    question = example.inputs.get("question", "")
    answer = run.outputs.get("answer", "")
    reference = example.outputs.get("answer", "")

    return judge.evaluate(question, answer, reference)


# ============================================================================
# Groundedness Judge
# ============================================================================

class GroundednessJudge(LLMJudge):
    """
    Judge for evaluating if answer is grounded in context.

    Checks if the answer is supported by the provided context.
    """

    PROMPT_TEMPLATE = """You are evaluating if an AI assistant's answer is grounded in the provided context.

Context:
{context}

Question: {question}

Assistant's Answer: {answer}

Evaluate if the answer is grounded in the context:
1. Is every claim in the answer supported by the context?
2. Does the answer introduce information not in the context?
3. Does the answer contradict the context?

Score from 1-5:
1 = Not grounded (hallucinated or contradicts context)
2 = Mostly ungrounded (some claims not supported)
3 = Partially grounded (mix of supported and unsupported)
4 = Mostly grounded (minor unsupported details)
5 = Fully grounded (all claims supported by context)"""

    def evaluate(
        self,
        context: str,
        question: str,
        answer: str
    ) -> dict:
        """Evaluate answer groundedness."""
        prompt = self.PROMPT_TEMPLATE.format(
            context=context,
            question=question,
            answer=answer
        )

        result = self._invoke_with_schema(prompt, QualityGrade)

        return {
            "key": "groundedness",
            "score": result.score / 5.0,  # Normalize to 0-1
            "raw_score": result.score,
            "reasoning": result.reasoning
        }


def groundedness_evaluator(run, example) -> dict:
    """Evaluator function for groundedness."""
    judge = GroundednessJudge()

    context = example.inputs.get("context", "")
    question = example.inputs.get("question", "")
    answer = run.outputs.get("answer", "")

    return judge.evaluate(context, question, answer)


# ============================================================================
# Coherence Judge
# ============================================================================

class CoherenceJudge(LLMJudge):
    """
    Judge for evaluating response coherence.

    Checks logical flow, consistency, and clarity.
    """

    PROMPT_TEMPLATE = """You are evaluating the coherence of an AI assistant's response.

Question: {question}

Response: {answer}

Evaluate the coherence of the response:
1. Is it logically structured?
2. Does it flow well from point to point?
3. Is it internally consistent?
4. Is it clear and easy to understand?

Score from 1-5:
1 = Incoherent (confusing, contradictory)
2 = Poorly coherent (hard to follow)
3 = Moderately coherent (some issues)
4 = Mostly coherent (minor issues)
5 = Fully coherent (clear, logical, consistent)"""

    def evaluate(self, question: str, answer: str) -> dict:
        """Evaluate response coherence."""
        prompt = self.PROMPT_TEMPLATE.format(
            question=question,
            answer=answer
        )

        result = self._invoke_with_schema(prompt, QualityGrade)

        return {
            "key": "coherence",
            "score": result.score / 5.0,
            "raw_score": result.score,
            "reasoning": result.reasoning
        }


def coherence_evaluator(run, example) -> dict:
    """Evaluator function for coherence."""
    judge = CoherenceJudge()

    question = example.inputs.get("question", "")
    answer = run.outputs.get("answer", "")

    return judge.evaluate(question, answer)


# ============================================================================
# Helpfulness Judge
# ============================================================================

class HelpfulnessJudge(LLMJudge):
    """
    Judge for evaluating response helpfulness.
    """

    PROMPT_TEMPLATE = """You are evaluating how helpful an AI assistant's response is.

User's Question: {question}

Assistant's Response: {answer}

Evaluate the helpfulness:
1. Does it answer the user's question?
2. Does it provide useful information?
3. Is it actionable (if applicable)?
4. Does it anticipate follow-up needs?

Score from 1-5:
1 = Not helpful (doesn't address the question)
2 = Slightly helpful (addresses but poorly)
3 = Moderately helpful (basic answer)
4 = Very helpful (good answer with detail)
5 = Extremely helpful (comprehensive, anticipates needs)"""

    def evaluate(self, question: str, answer: str) -> dict:
        """Evaluate response helpfulness."""
        prompt = self.PROMPT_TEMPLATE.format(
            question=question,
            answer=answer
        )

        result = self._invoke_with_schema(prompt, QualityGrade)

        return {
            "key": "helpfulness",
            "score": result.score / 5.0,
            "raw_score": result.score,
            "reasoning": result.reasoning
        }


def helpfulness_evaluator(run, example) -> dict:
    """Evaluator function for helpfulness."""
    judge = HelpfulnessJudge()

    question = example.inputs.get("question", "")
    answer = run.outputs.get("answer", "")

    return judge.evaluate(question, answer)


# ============================================================================
# Multi-Criteria Judge
# ============================================================================

class MultiCriteriaJudge(LLMJudge):
    """
    Judge that evaluates multiple criteria at once.
    """

    PROMPT_TEMPLATE = """You are evaluating an AI assistant's response across multiple dimensions.

Question: {question}

Context (if any): {context}

Response: {answer}

Evaluate the response on these criteria (1-5 each):

1. Relevance: How relevant is the answer to the question?
2. Accuracy: How accurate and factually correct is the answer?
3. Completeness: How complete and thorough is the answer?
4. Clarity: How clear and well-written is the answer?
5. Overall: Your overall assessment of quality.

Provide a brief explanation for your overall assessment."""

    def evaluate(
        self,
        question: str,
        answer: str,
        context: str = ""
    ) -> dict:
        """Evaluate response on multiple criteria."""
        prompt = self.PROMPT_TEMPLATE.format(
            question=question,
            context=context or "N/A",
            answer=answer
        )

        result = self._invoke_with_schema(prompt, DetailedEvaluation)

        return {
            "key": "multi_criteria",
            "scores": {
                "relevance": result.relevance / 5.0,
                "accuracy": result.accuracy / 5.0,
                "completeness": result.completeness / 5.0,
                "clarity": result.clarity / 5.0,
                "overall": result.overall / 5.0,
            },
            "score": result.overall / 5.0,  # Overall for compatibility
            "reasoning": result.reasoning
        }


def multi_criteria_evaluator(run, example) -> dict:
    """Evaluator function for multi-criteria evaluation."""
    judge = MultiCriteriaJudge()

    question = example.inputs.get("question", "")
    context = example.inputs.get("context", "")
    answer = run.outputs.get("answer", "")

    return judge.evaluate(question, answer, context)


# ============================================================================
# Custom Criteria Judge
# ============================================================================

class CustomCriteriaJudge(LLMJudge):
    """
    Judge with custom evaluation criteria.
    """

    def __init__(
        self,
        criteria: str,
        description: str,
        model: str = "gemini-2.5-flash"
    ):
        super().__init__(model=model)
        self.criteria = criteria
        self.description = description

    def evaluate(self, question: str, answer: str) -> dict:
        """Evaluate using custom criteria."""
        prompt = f"""You are evaluating an AI assistant's response.

Question: {question}

Response: {answer}

Evaluate the response on this criterion:
{self.criteria}: {self.description}

Score from 1-5:
1 = Very poor
2 = Poor
3 = Acceptable
4 = Good
5 = Excellent"""

        result = self._invoke_with_schema(prompt, QualityGrade)

        return {
            "key": self.criteria.lower().replace(" ", "_"),
            "score": result.score / 5.0,
            "raw_score": result.score,
            "reasoning": result.reasoning
        }


def create_custom_evaluator(criteria: str, description: str):
    """Factory for creating custom criteria evaluators."""
    judge = CustomCriteriaJudge(criteria, description)

    def evaluator(run, example) -> dict:
        question = example.inputs.get("question", "")
        answer = run.outputs.get("answer", "")
        return judge.evaluate(question, answer)

    return evaluator


# ============================================================================
# Pairwise Comparison Judge
# ============================================================================

class PairwiseJudge(LLMJudge):
    """
    Judge for comparing two responses.
    """

    PROMPT_TEMPLATE = """You are comparing two AI assistant responses to determine which is better.

Question: {question}

Response A: {answer_a}

Response B: {answer_b}

Compare the responses and determine which is better overall.
Consider accuracy, helpfulness, clarity, and completeness.

Which response is better: A, B, or TIE?"""

    class ComparisonResult(BaseModel):
        winner: Literal["A", "B", "TIE"]
        reasoning: str

    def compare(
        self,
        question: str,
        answer_a: str,
        answer_b: str
    ) -> dict:
        """Compare two responses."""
        prompt = self.PROMPT_TEMPLATE.format(
            question=question,
            answer_a=answer_a,
            answer_b=answer_b
        )

        result = self._invoke_with_schema(prompt, self.ComparisonResult)

        return {
            "winner": result.winner,
            "reasoning": result.reasoning
        }


# ============================================================================
# Demo Functions
# ============================================================================

def demo_correctness_judge():
    """Demonstrate correctness judge."""

    print("=== Correctness Judge Demo ===\n")

    judge = CorrectnessJudge()

    # Test case 1: Correct answer
    result = judge.evaluate(
        question="What is the capital of France?",
        answer="The capital of France is Paris.",
        reference="Paris"
    )
    print(f"Test 1 - Correct answer:")
    print(f"  Score: {result['score']}")
    print(f"  Reasoning: {result['reasoning']}\n")

    # Test case 2: Incorrect answer
    result = judge.evaluate(
        question="What is the capital of France?",
        answer="The capital of France is London.",
        reference="Paris"
    )
    print(f"Test 2 - Incorrect answer:")
    print(f"  Score: {result['score']}")
    print(f"  Reasoning: {result['reasoning']}")


def demo_groundedness_judge():
    """Demonstrate groundedness judge."""

    print("=== Groundedness Judge Demo ===\n")

    judge = GroundednessJudge()

    context = """Python is a high-level programming language created by Guido van Rossum.
    It was first released in 1991. Python emphasizes code readability and uses
    significant indentation."""

    # Grounded answer
    result = judge.evaluate(
        context=context,
        question="When was Python created?",
        answer="Python was first released in 1991, created by Guido van Rossum."
    )
    print(f"Grounded answer:")
    print(f"  Score: {result['score']:.2f} ({result['raw_score']}/5)")
    print(f"  Reasoning: {result['reasoning']}\n")

    # Hallucinated answer
    result = judge.evaluate(
        context=context,
        question="When was Python created?",
        answer="Python was created in 1985 by a team at Microsoft."
    )
    print(f"Hallucinated answer:")
    print(f"  Score: {result['score']:.2f} ({result['raw_score']}/5)")
    print(f"  Reasoning: {result['reasoning']}")


def demo_multi_criteria():
    """Demonstrate multi-criteria judge."""

    print("=== Multi-Criteria Judge Demo ===\n")

    judge = MultiCriteriaJudge()

    result = judge.evaluate(
        question="Explain how to make coffee",
        answer="To make coffee: 1) Boil water, 2) Add ground coffee to filter, 3) Pour hot water over grounds, 4) Let it drip into your cup, 5) Enjoy!"
    )

    print("Scores:")
    for criterion, score in result["scores"].items():
        print(f"  {criterion}: {score:.2f}")
    print(f"\nReasoning: {result['reasoning']}")


def demo_custom_criteria():
    """Demonstrate custom criteria judge."""

    print("=== Custom Criteria Judge Demo ===\n")

    # Create a custom "professionalism" evaluator
    evaluator = create_custom_evaluator(
        criteria="Professionalism",
        description="How professional and formal is the tone of the response?"
    )

    class MockRun:
        outputs = {"answer": "Hey! That's super cool! Python is like, totally awesome for coding stuff!"}

    class MockExample:
        inputs = {"question": "What is Python?"}
        outputs = {}

    result = evaluator(MockRun(), MockExample())

    print(f"Custom criterion: {result['key']}")
    print(f"Score: {result['score']:.2f} ({result['raw_score']}/5)")
    print(f"Reasoning: {result['reasoning']}")


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    print("LLM-as-Judge Demonstrations\n")
    print("=" * 50 + "\n")

    demo_correctness_judge()
    print("\n" + "=" * 50 + "\n")

    demo_groundedness_judge()
    print("\n" + "=" * 50 + "\n")

    demo_multi_criteria()
    print("\n" + "=" * 50 + "\n")

    demo_custom_criteria()
