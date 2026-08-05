"""
Synthesis Prompt for BLINC Agent V3

Generates the final answer from retrieved information.
"""

SYNTHESIS_PROMPT = """You are synthesizing an answer about collaborative discussions.

## User Query
{query}

## Retrieved Information
{information}

## Conversation Context
{context}

## Instructions

Generate a clear, helpful answer that:

1. **Directly addresses the query** - Start with the most important information
2. **Cites specific evidence** - Reference sessions, speakers, timestamps when available
3. **Acknowledges limitations** - If information is incomplete, say so
4. **Stays focused** - Don't include tangential information

## Response Structure

For factual queries:
- Lead with the answer
- Provide supporting evidence
- Note any caveats

For analytical queries (why, how, what patterns):
- Ground in observable evidence
- Provide analysis based on the data
- Distinguish facts from interpretations

For comparative queries:
- Highlight key similarities
- Highlight key differences
- Provide overall assessment

## Length
- Keep responses concise but complete
- Aim for 2-4 paragraphs for most queries
- Use bullet points for lists or comparisons

## What NOT to do
- Don't include raw JSON or technical details
- Don't make up information not in the retrieved results
- Don't be overly verbose or repeat yourself
"""


def format_synthesis_prompt(
    query: str,
    information: list,
    context: dict
) -> str:
    """
    Format the synthesis prompt with retrieved information.

    Args:
        query: The user's query
        information: List of retrieval results
        context: Conversation context

    Returns:
        Formatted prompt string
    """
    # Format information
    info_sections = []

    for result in information:
        tool_name = result.get('tool_name', 'Search')
        results = result.get('results', [])

        if not results:
            continue

        section_lines = [f"### From {tool_name}"]

        for item in results[:5]:  # Top 5 per tool
            if isinstance(item, dict):
                text = item.get('text', item.get('content', item.get('summary', '')))
                session = item.get('session_device_id', item.get('session_id', ''))
                speaker = item.get('speaker', item.get('speaker_alias', ''))

                if session:
                    section_lines.append(f"**Session {session}**" + (f" ({speaker})" if speaker else ""))
                section_lines.append(text[:600] if text else str(item)[:600])
                section_lines.append("")
            else:
                section_lines.append(str(item)[:600])
                section_lines.append("")

        info_sections.append("\n".join(section_lines))

    info_str = "\n\n".join(info_sections) if info_sections else "No relevant information found."

    # Format context
    context_lines = []
    if context.get('current_session_focus'):
        context_lines.append(f"Currently focused on: Session {context['current_session_focus']}")
    if context.get('compared_sessions'):
        context_lines.append(f"Comparing sessions: {context['compared_sessions']}")

    context_str = "\n".join(context_lines) if context_lines else "General query"

    return SYNTHESIS_PROMPT.format(
        query=query,
        information=info_str,
        context=context_str
    )
