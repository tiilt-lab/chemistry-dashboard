"""
Reasoning Tools for BLINC Agent V3

Tools that help the agent think and interact with users.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def think(reasoning: str) -> Dict[str, Any]:
    """
    Explicit thinking tool for complex reasoning.

    This tool allows the agent to pause and think through
    complex problems step by step. The thought is recorded
    for transparency but not shown to the user.

    Args:
        reasoning: The agent's reasoning process

    Returns:
        Dict with the recorded thought
    """
    logger.info(f"Agent thinking: {reasoning[:200]}...")

    return {
        "tool_name": "think",
        "thought": reasoning,
        "result_count": 0,
        "results": [],
        "is_relevant": True  # Thinking is always "relevant"
    }


def clarify(question: str, options: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Ask the user for clarification.

    This tool should be used sparingly - prefer searching over asking.
    Only use when the query is genuinely ambiguous.

    Args:
        question: The clarification question to ask
        options: Optional list of choices for the user

    Returns:
        Dict with clarification request
    """
    logger.info(f"Agent requesting clarification: {question}")

    return {
        "tool_name": "clarify",
        "question": question,
        "options": options or [],
        "needs_clarification": True,
        "result_count": 0,
        "results": [],
        "is_relevant": True
    }
