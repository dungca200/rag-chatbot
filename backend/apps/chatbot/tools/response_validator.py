import logging
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from core.clients.gemini_client import get_chat_model

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    """Schema for validation output."""
    confidence_score: float = Field(
        description="Confidence score from 0.0 to 1.0 indicating how well the response is supported by the context"
    )
    is_grounded: bool = Field(
        description="Whether the response is fully grounded in the provided context"
    )
    issues: List[str] = Field(
        default=[],
        description="List of potential issues or unsupported claims"
    )


VALIDATION_PROMPT = """You are a response validator for a RAG system. Your job is to check if a response is grounded in the provided context.

Analyze the following:

CONTEXT:
{context}

RESPONSE:
{response}

Evaluate:
1. Is every claim in the response supported by the context?
2. Are there any hallucinations or unsupported statements?
3. What is your confidence that this response is accurate based on the context?

Provide:
- confidence_score: 0.0 (completely unsupported) to 1.0 (fully grounded)
- is_grounded: true if response is well-supported, false otherwise
- issues: list any specific unsupported claims or concerns"""


def validate_response(
    response: str,
    context: str,
    threshold: float = 0.7
) -> Dict:
    """
    Validate if a response is grounded in the provided context.

    Args:
        response: The generated response to validate
        context: The source context
        threshold: Minimum confidence score to consider response valid

    Returns:
        Dict with confidence_score, is_grounded, and issues
    """
    if not response or not response.strip():
        return {
            "success": False,
            "error": "Empty response",
            "confidence_score": 0.0,
            "is_grounded": False,
            "is_valid": False,
            "issues": ["Response is empty"]
        }

    if not context or not context.strip():
        return {
            "success": True,
            "confidence_score": 0.5,
            "is_grounded": False,
            "is_valid": False,
            "issues": ["No context provided for validation"]
        }

    try:
        llm = get_chat_model(temperature=0.0)
        structured_llm = llm.with_structured_output(ValidationResult)

        prompt = VALIDATION_PROMPT.format(
            context=context[:4000],  # Limit context size
            response=response[:2000]  # Limit response size
        )

        result = structured_llm.invoke(prompt)

        is_valid = result.confidence_score >= threshold and result.is_grounded

        logger.info(f"Validation: score={result.confidence_score}, grounded={result.is_grounded}")

        return {
            "success": True,
            "confidence_score": result.confidence_score,
            "is_grounded": result.is_grounded,
            "is_valid": is_valid,
            "issues": result.issues,
            "threshold": threshold
        }

    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        # On error, return conservative estimate
        return {
            "success": False,
            "error": str(e),
            "confidence_score": 0.5,
            "is_grounded": False,
            "is_valid": False,
            "issues": [f"Validation error: {str(e)}"]
        }


def quick_validate(
    response: str,
    sources: List[str]
) -> Dict:
    """
    Quick validation check based on source presence.

    Args:
        response: The generated response
        sources: List of source keys/references

    Returns:
        Dict with basic validation status
    """
    has_sources = bool(sources)

    # Very basic heuristic
    if not has_sources:
        return {
            "success": True,
            "has_sources": False,
            "confidence_score": 0.3,
            "warning": "Response generated without source documents"
        }

    return {
        "success": True,
        "has_sources": True,
        "source_count": len(sources),
        "confidence_score": 0.8
    }
