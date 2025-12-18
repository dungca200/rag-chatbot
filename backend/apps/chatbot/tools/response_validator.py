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


HUMANIZE_PROMPT = """You are a response editor. Your job is to take a response and make it sound more natural and human while keeping the same meaning.

Rules:
- Keep the same factual content and meaning
- Remove robotic phrases like "Based on the context...", "The document states...", "According to the provided information..."
- Make it sound like a knowledgeable colleague explaining something
- Be professional but warm - no emojis, no excessive casualness
- Keep it concise
- If the response says information isn't available, make that sound natural too (not "The context does not provide...")
- Don't add information that wasn't in the original response

Original response:
{response}

Rewritten response (same content, more natural tone):"""


def humanize_response(response: str) -> str:
    """
    Rewrite a response to sound more natural and human.

    Args:
        response: The original response to humanize

    Returns:
        A more natural-sounding version of the response
    """
    if not response or not response.strip():
        return response

    # Check if response already sounds natural (skip processing)
    robotic_phrases = [
        "based on the context",
        "based on the provided",
        "the context does not",
        "the document states",
        "according to the provided",
        "the information provided",
        "i cannot find",
        "i apologize",
    ]

    response_lower = response.lower()
    needs_humanizing = any(phrase in response_lower for phrase in robotic_phrases)

    if not needs_humanizing:
        return response

    try:
        llm = get_chat_model(temperature=0.3)
        prompt = HUMANIZE_PROMPT.format(response=response)
        result = llm.invoke(prompt)

        humanized = result.content.strip()
        logger.info("Response humanized successfully")
        return humanized

    except Exception as e:
        logger.warning(f"Failed to humanize response: {str(e)}")
        return response  # Return original on error
