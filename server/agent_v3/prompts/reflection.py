"""
Reflection Prompt for BLINC Agent V3

Self-reflection on the generated answer before returning to user.
"""

REFLECTION_PROMPT = """You are reviewing an answer before it's sent to the user. Return your response as JSON.

## Original Query
{query}

## Generated Answer
{answer}

## Information Used
{tools_used}

## Task
Evaluate the answer quality and suggest improvements if needed.

## Evaluation Criteria

1. **Completeness**: Does it fully address the query?
2. **Accuracy**: Is it grounded in the retrieved information?
3. **Clarity**: Is it easy to understand?
4. **Relevance**: Does it stay on topic?
5. **Actionability**: Does it help the user?

## Response Format
{{
    "quality_score": 0.0-1.0,
    "is_complete": true/false,
    "is_accurate": true/false,
    "issues": ["list of any issues found"],
    "suggested_followups": ["2-3 follow-up questions the user might ask"],
    "confidence": 0.0-1.0
}}

## Guidelines
- Be honest about limitations
- A score of 0.7+ is acceptable
- Suggest follow-ups that would genuinely help the user
- If the answer is good, say so
"""


def format_reflection_prompt(
    query: str,
    answer: str,
    tools_used: list
) -> str:
    """
    Format the reflection prompt.

    Args:
        query: Original user query
        answer: Generated answer
        tools_used: List of tools that were used

    Returns:
        Formatted prompt string
    """
    tools_str = ", ".join(tools_used) if tools_used else "No tools used"

    return REFLECTION_PROMPT.format(
        query=query,
        answer=answer,
        tools_used=tools_str
    )
