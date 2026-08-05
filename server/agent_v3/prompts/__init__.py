"""
Prompts for BLINC Agent V3

Well-crafted prompts that enable intelligent reasoning
without keyword matching.
"""

from .tool_descriptions import TOOL_DESCRIPTIONS, get_tools_prompt
from .reasoning import REASONING_SYSTEM_PROMPT, REASONING_USER_TEMPLATE
from .grading import GRADING_PROMPT
from .synthesis import SYNTHESIS_PROMPT
from .reflection import REFLECTION_PROMPT

__all__ = [
    'TOOL_DESCRIPTIONS',
    'get_tools_prompt',
    'REASONING_SYSTEM_PROMPT',
    'REASONING_USER_TEMPLATE',
    'GRADING_PROMPT',
    'SYNTHESIS_PROMPT',
    'REFLECTION_PROMPT'
]
