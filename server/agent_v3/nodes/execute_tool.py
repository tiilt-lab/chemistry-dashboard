"""
Execute Tool Node for BLINC Agent V3

Executes the tool selected by reason_and_act.

Includes:
- Result caching for performance (avoids duplicate API/DB calls)
- Proper error handling with structured error info
"""

import json
import hashlib
import logging
from typing import Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

# Conversation-level result cache
# Key: (conversation_id, tool_name, args_hash)
# Value: tool result
_result_cache: Dict[str, Dict[str, Any]] = {}

# Cache metrics for performance monitoring
_cache_metrics = {
    'hits': 0,
    'misses': 0,
    'total_calls': 0
}


def _get_cache_key(conversation_id: str, tool_name: str, tool_input: dict) -> str:
    """Generate a deterministic cache key for a tool call."""
    # Sort dict keys for deterministic hashing
    input_str = json.dumps(tool_input, sort_keys=True, default=str)
    input_hash = hashlib.md5(input_str.encode()).hexdigest()[:16]
    return f"{conversation_id}:{tool_name}:{input_hash}"


def get_cache_metrics() -> dict:
    """Return cache performance metrics."""
    total = _cache_metrics['total_calls']
    hits = _cache_metrics['hits']
    return {
        **_cache_metrics,
        'hit_rate': hits / total if total > 0 else 0.0
    }


def clear_conversation_cache(conversation_id: str) -> int:
    """Clear cache entries for a specific conversation. Returns count cleared."""
    global _result_cache
    prefix = f"{conversation_id}:"
    keys_to_remove = [k for k in _result_cache if k.startswith(prefix)]
    for key in keys_to_remove:
        del _result_cache[key]
    return len(keys_to_remove)

# Session name to ID mapping for input normalization
SESSION_NAME_TO_ID = {
    'living in nyc': 18, 'nyc': 18, 'new york': 18,
    'is ai alive': 19, 'ai alive': 19, 'ai': 19,
    'nuclear fusion': 20, 'fusion': 20,
    'shaw interview': 21, 'shaw': 21,
    'collaboration literacy': 22, 'literacy': 22,
    'dinosaurs': 23, 'dinosaur': 23,
    'country music': 24, 'country': 24, 'music': 24,
    'abundance': 25
}


def _normalize_session_id(value):
    """Convert session name to ID if needed."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # Try to parse as int first
        try:
            return int(value)
        except ValueError:
            pass
        # Look up by name
        normalized = value.lower().strip()
        if normalized in SESSION_NAME_TO_ID:
            return SESSION_NAME_TO_ID[normalized]
        # Try partial match
        for name, sid in SESSION_NAME_TO_ID.items():
            if name in normalized or normalized in name:
                return sid
    return value  # Return as-is if we can't normalize


def _normalize_tool_input(tool_name: str, tool_input: dict) -> dict:
    """Normalize tool input - convert session names to IDs, etc."""
    if not tool_input:
        return tool_input

    normalized = tool_input.copy()

    # Normalize session_id parameter
    if 'session_id' in normalized:
        normalized['session_id'] = _normalize_session_id(normalized['session_id'])

    # Normalize session_ids list
    if 'session_ids' in normalized and isinstance(normalized['session_ids'], list):
        normalized['session_ids'] = [
            _normalize_session_id(sid) for sid in normalized['session_ids']
        ]

    return normalized


def execute_tool(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the tool selected by the reasoning node.

    Features:
    - Result caching to avoid duplicate API/DB calls
    - Structured error handling with proper propagation
    - Metrics tracking for performance monitoring

    Args:
        state: Current agent state with current_tool and current_tool_input

    Returns:
        Updated state with tool results
    """
    global _cache_metrics, _result_cache

    tool_name = state.get('current_tool')
    tool_input = state.get('current_tool_input', {}) or {}
    conversation_id = state.get('conversation_id', 'default')

    # Normalize input - convert session names to IDs, etc.
    tool_input = _normalize_tool_input(tool_name, tool_input)

    _cache_metrics['total_calls'] += 1

    # Check conversation-level cache FIRST
    cache_key = _get_cache_key(conversation_id, tool_name, tool_input)
    if cache_key in _result_cache:
        cached_result = _result_cache[cache_key]
        _cache_metrics['hits'] += 1
        logger.info(f"[Cache HIT] {tool_name} - returning cached result")
        return {
            'retrieval_results': [cached_result],
            'tools_used': state.get('tools_used', []),
            'next_action': 'grade' if cached_result.get('result_count', 0) > 0 else 'continue',
            'cache_hit': True
        }

    _cache_metrics['misses'] += 1

    # Also check for duplicate in current turn's results (backward compat)
    existing_results = state.get('retrieval_results', [])
    for existing in existing_results:
        if (existing.get('tool_name') == tool_name and
            existing.get('query_params') == tool_input and
            existing.get('is_relevant', False)):
            logger.info(f"Skipping duplicate call to {tool_name} with same params (turn-level)")
            return {
                'next_action': 'continue'
            }

    logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

    if not tool_name:
        logger.warning("No tool specified for execution")
        return {
            'next_action': 'continue'
        }

    try:
        # Import tools - check COMBINED_TOOLS first (includes artifact tools)
        from ..tools import ALL_TOOLS, COMBINED_TOOLS

        # Prefer COMBINED_TOOLS (artifact-centric), fall back to ALL_TOOLS
        if tool_name in COMBINED_TOOLS:
            tool_fn = COMBINED_TOOLS[tool_name]
        elif tool_name in ALL_TOOLS:
            tool_fn = ALL_TOOLS[tool_name]
        else:
            logger.error(f"Unknown tool: {tool_name}")
            return {
                'retrieval_results': [{
                    'tool_name': tool_name,
                    'error': f"Unknown tool: {tool_name}",
                    'result_count': 0,
                    'results': [],
                    'is_relevant': False
                }],
                'next_action': 'continue'
            }

        # Execute the tool
        result = tool_fn(**tool_input)

        # Track tools used
        tools_used = state.get('tools_used', []).copy()
        if tool_name not in tools_used:
            tools_used.append(tool_name)

        # Handle special cases
        if tool_name == 'think':
            # Thinking doesn't produce retrieval results
            return {
                'tools_used': tools_used,
                'current_thought': result.get('thought', ''),
                'next_action': 'continue'
            }

        if tool_name == 'clarify':
            # Clarification needs special handling
            return {
                'tools_used': tools_used,
                'next_action': 'clarify',
                'clarification_question': result.get('question'),
                'clarification_options': result.get('options', [])
            }

        # Normal tool result
        # Store query_params for deduplication
        result['query_params'] = tool_input

        # Cache the result for future calls
        _result_cache[cache_key] = result
        logger.info(f"[Cache STORE] {tool_name} - cached result ({result.get('result_count', 0)} results)")

        return {
            'retrieval_results': [result],
            'tools_used': tools_used,
            'next_action': 'grade' if result.get('result_count', 0) > 0 else 'continue',
            'cache_hit': False
        }

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Tool execution error: {e}")
        logger.error(f"Traceback: {error_details}")

        # Structure the error for proper handling
        error_result = {
            'tool_name': tool_name,
            'error': str(e),
            'error_type': type(e).__name__,
            'error_details': error_details[:500],  # Truncate for logging
            'result_count': 0,
            'results': [],
            'is_relevant': False,
            'query_params': tool_input
        }

        # Track error count in state for visibility
        error_count = state.get('tool_error_count', 0) + 1

        return {
            'retrieval_results': [error_result],
            'next_action': 'continue',
            'tool_error_count': error_count,
            'last_error': str(e)
        }
