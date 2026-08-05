"""
Input Processor Node

Processes raw user input and prepares it for the workflow.
"""

import logging
from typing import Dict, Any

from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


def input_processor(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process raw user input and initialize state for processing.

    This node:
    1. Extracts the user query from messages or original_query
    2. Initializes iteration counters
    3. Prepares the state for reference resolution

    Args:
        state: Current agent state

    Returns:
        Updated state with processed input
    """
    # Get the query - either from messages or original_query
    query = state.get('original_query', '')
    messages = state.get('messages', [])

    if not query and messages:
        # Extract query from last human message
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break
            elif isinstance(msg, dict) and msg.get('role') == 'user':
                query = msg.get('content', '')
                break

    if not query:
        logger.warning("No query found in input")
        return {
            "original_query": "",
            "error": "No query provided",
            "next_node": "format"
        }

    logger.info(f"Processing query: {query[:100]}...")

    # Initialize state
    return {
        "original_query": query,
        "resolved_query": query,  # Will be updated by reference_resolver
        "iteration_count": 0,
        "next_node": "resolver"
    }
