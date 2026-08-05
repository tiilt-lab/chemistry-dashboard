"""
Document Grading Prompt for BLINC Agent V3

Implements Self-RAG / CRAG style document relevance grading.
"""

GRADING_PROMPT = """You are a relevance grader for a discussion analysis system. Return your response as JSON.

## Task
Evaluate whether the retrieved documents are relevant to answering the user's query.

## User Query
{query}

## Retrieved Documents
{documents}

## Instructions
For each document, assess:
1. Does it contain information relevant to the query?
2. Would it help answer what the user is asking?
3. Is it from the right context (session, speaker, topic)?

## Response Format
Respond with a JSON object:
{{
    "overall_relevant": true/false,
    "relevance_score": 0.0-1.0,
    "relevant_count": number of relevant documents,
    "irrelevant_count": number of irrelevant documents,
    "assessment": "Brief explanation of the relevance",
    "should_rewrite": true/false,
    "rewrite_suggestion": "If should_rewrite, suggest how to improve the query"
}}

## Guidelines
- Be lenient: If documents are somewhat related, they're relevant
- Consider partial relevance: Documents might answer part of the query
- Only suggest rewrite if results are clearly off-topic
- If no documents were retrieved, that's a clear signal to rewrite
"""


def format_grading_prompt(query: str, documents: list) -> str:
    """
    Format the grading prompt with query and documents.

    Args:
        query: The user's query
        documents: List of retrieved documents

    Returns:
        Formatted prompt string
    """
    # Format documents for grading
    doc_lines = []
    for i, doc in enumerate(documents[:10], 1):  # Max 10 docs
        text = doc.get('text', doc.get('content', ''))[:500]
        session = doc.get('session_device_id', doc.get('session_id', 'unknown'))
        speaker = doc.get('speaker', doc.get('speaker_alias', ''))

        doc_lines.append(f"### Document {i}")
        doc_lines.append(f"Session: {session}")
        if speaker:
            doc_lines.append(f"Speaker: {speaker}")
        doc_lines.append(f"Content: {text}")
        doc_lines.append("")

    docs_str = "\n".join(doc_lines) if doc_lines else "No documents retrieved"

    return GRADING_PROMPT.format(
        query=query,
        documents=docs_str
    )
