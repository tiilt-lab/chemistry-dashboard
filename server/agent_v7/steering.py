"""
User Steering for BLINC Agent V7

Simple approach: Pass user preferences to the LLM and let it understand.
No regex parsing - the LLM is smart enough to understand
"focus on concept map, don't use collaboration assessment" without pattern matching.
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SteeringDirectives:
    """
    User's steering preferences - just pass to LLM as natural language.
    """
    # The raw query - LLM will understand preferences from context
    raw_instructions: str = ""

    # API-level overrides (when explicitly passed via API, not extracted from query)
    api_preferred: List[str] = field(default_factory=list)
    api_excluded: List[str] = field(default_factory=list)


def extract_steering(
    query: str,
    conversation_history: List[Dict] = None,
    memory_steering: Dict = None
) -> SteeringDirectives:
    """
    Create steering directives from query and context.

    We don't parse the query with regex - the LLM understands natural language.
    We just pass the raw query and any API-level preferences.
    """
    directives = SteeringDirectives(raw_instructions=query)

    # Include API-level preferences from memory (these were explicitly set via API)
    if memory_steering:
        directives.api_preferred = memory_steering.get('preferred_artifacts', [])
        directives.api_excluded = memory_steering.get('excluded_artifacts', [])

    return directives


def format_steering_for_prompt(steering: SteeringDirectives) -> str:
    """
    Format steering for inclusion in LLM prompt.

    The LLM will read the user's query and understand their preferences.
    We only add explicit notes for API-level overrides.
    """
    parts = []

    # API-level preferences (explicit overrides)
    if steering.api_preferred:
        parts.append(f"User explicitly requested to focus on: {', '.join(steering.api_preferred)}")

    if steering.api_excluded:
        parts.append(f"User explicitly requested to skip: {', '.join(steering.api_excluded)}")

    if not parts:
        return "No explicit preferences. Understand user intent from their query."

    return "\n".join(parts)


# Keep validate_tool_call as a minimal safety net for API-level exclusions only
def validate_tool_call(tool_name: str, steering: SteeringDirectives) -> tuple[bool, str]:
    """
    Validate tool call against EXPLICIT API-level exclusions only.

    This is a safety net for when the frontend explicitly passes exclusions.
    We don't try to parse the query - the LLM handles that.
    """
    # Only check API-level exclusions (explicitly passed, not extracted from query)
    if not steering.api_excluded:
        return True, ""

    # Simple mapping for API-level exclusions
    tool_to_artifact = {
        'get_collaboration_assessment': ['7c', 'collaboration'],
        'get_concept_map': ['concept_map'],
        'get_transcript': ['transcript'],
    }

    artifacts = tool_to_artifact.get(tool_name, [])
    for artifact in artifacts:
        if artifact in steering.api_excluded:
            return False, f"Explicitly excluded via API: {artifact}"

    return True, ""
