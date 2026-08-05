# server/insight_prompts.py - Query-Specific Prompt Templates for Ultra RAG
"""
Prompt Templates: Query-focused prompts that guide LLM to produce relevant,
evidence-grounded insights instead of generic rambling.

Each template:
1. Sets clear focus based on query intent
2. Requires specific evidence (quotes, metrics)
3. Structures output for consistency
"""

from typing import Dict, Optional

# System prompts for different analysis types
SYSTEM_PROMPTS = {
    'argumentation': """You are an expert at analyzing argumentation patterns in discussions.

Your analysis MUST:
1. Reference specific metrics (debate_score, challenge_count, reasoning_depth)
2. Quote actual dialogue that demonstrates argumentation
3. Explain HOW challenges/supports are made, not just that they exist
4. Compare patterns when multiple sessions are provided

Avoid:
- Generic statements like "there was good discussion"
- Mentioning patterns without evidence
- Ignoring the metrics provided""",

    'collaboration': """You are an expert at analyzing collaborative discussion quality.

Your analysis MUST:
1. Reference specific 7C scores (communication, climate, contribution)
2. Quote dialogue that demonstrates collaboration quality
3. Explain what makes communication effective/ineffective
4. Identify specific moments of good/poor collaboration

Avoid:
- Generic praise like "participants collaborated well"
- Ignoring the 7C scores provided
- Making claims without citing specific dialogue""",

    'speaker': """You are an expert at characterizing speaker engagement styles.

Your analysis MUST:
1. Reference speaker-specific metrics (clout, questions asked, word count)
2. Quote 2-3 representative statements from the speaker
3. Identify distinctive patterns (questions, assertions, supports)
4. Compare to other speakers if data is available

Avoid:
- Generic descriptions like "engaged actively"
- Ignoring the metrics provided
- Making claims without citing quotes""",

    'evolution': """You are an expert at analyzing how discussions evolve over time.

Your analysis MUST:
1. Reference evolution metrics (analytic_evolution, tone_evolution)
2. Describe the trajectory: what changed from start to end
3. Identify turning points or key moments
4. Explain what drove the changes

Avoid:
- Ignoring the evolution data
- Making vague claims about "improvement"
- Not explaining WHY things changed""",

    'contrastive': """You are an expert at comparative analysis of discussions.

Your analysis MUST:
1. Identify clear differences between HIGH and LOW groups
2. Cite specific metrics from both groups
3. Quote contrasting dialogue examples
4. Explain WHAT causes the difference, not just describe it

Structure:
1. Key differences found
2. Evidence from HIGH group (with quotes)
3. Evidence from LOW group (with quotes)
4. Explanation of what drives success""",

    'general': """You are an expert at analyzing educational discussions.

Your analysis MUST:
1. Reference the specific metrics provided
2. Quote actual dialogue to support claims
3. Make specific, actionable observations
4. Focus on what's interesting or unusual

Avoid:
- Generic summaries
- Ignoring the data provided
- Making claims without evidence"""
}

# User prompt templates
USER_PROMPT_TEMPLATES = {
    'argumentation_find': """Analyze these sessions for ARGUMENTATION patterns.

Query: "{query}"

SESSIONS DATA:
{session_contexts}

REQUIRED ANALYSIS:
1. Which sessions have the strongest argumentation? (cite debate_score, challenge_count)
2. What types of challenges/supports are made? (quote examples)
3. How are disagreements handled? (cite specific moments)
4. What makes argumentation effective in these discussions?

Provide specific quotes and metrics as evidence.""",

    'argumentation_explain': """Explain what makes argumentation effective in discussions.

Query: "{query}"

SESSIONS WITH HIGH ARGUMENTATION:
{high_context}

SESSIONS WITH LOW ARGUMENTATION:
{low_context}

REQUIRED ANALYSIS:
1. What differentiates high-argumentation sessions? (compare metrics)
2. How are challenges made in effective discussions? (quote examples from HIGH)
3. What's missing in low-argumentation sessions? (quote examples from LOW)
4. What specific behaviors lead to better argumentation?

Use contrastive evidence to support conclusions.""",

    'collaboration_find': """Analyze these sessions for COLLABORATION quality.

Query: "{query}"

SESSIONS DATA:
{session_contexts}

REQUIRED ANALYSIS:
1. Which sessions have best collaboration? (cite 7C scores)
2. What specific behaviors indicate good collaboration? (quote dialogue)
3. How is conflict handled? (cite specific moments)
4. What could improve collaboration in weaker sessions?

Reference specific 7C scores and quotes.""",

    'collaboration_explain': """Explain what makes collaboration effective.

Query: "{query}"

SESSIONS WITH HIGH COLLABORATION:
{high_context}

SESSIONS WITH LOW COLLABORATION:
{low_context}

REQUIRED ANALYSIS:
1. Compare 7C scores between groups
2. What communication patterns differ? (quote examples)
3. How does climate affect discussion? (compare examples)
4. What specific actions improve collaboration?

Use contrastive evidence.""",

    'speaker_analyze': """Analyze this speaker's engagement style.

Query: "{query}"

SPEAKER DATA:
{speaker_context}

REQUIRED ANALYSIS:
1. What is {speaker_name}'s distinctive speaking style? (cite metrics)
2. How do they typically engage? (questions? assertions? challenges?)
3. What are their signature phrases or approaches? (quote examples)
4. How do they influence discussions?

Provide specific quotes and metrics.""",

    'evolution_analyze': """Analyze how this discussion evolved over time.

Query: "{query}"

SESSION DATA:
{session_contexts}

REQUIRED ANALYSIS:
1. What changed from beginning to end? (cite evolution metrics)
2. What caused the changes? (identify key moments)
3. How did speaker dynamics shift?
4. What made the evolution positive/negative?

Reference specific metrics and turning points.""",

    'topic_find': """Find discussions related to the topic.

Query: "{query}"

SESSIONS DATA:
{session_contexts}

REQUIRED ANALYSIS:
1. Which sessions are most relevant? (explain why)
2. What aspects of the topic are covered?
3. What are the key insights from these discussions?
4. What quotes best represent the discussion of this topic?

Cite specific dialogue.""",

    'general_analyze': """Analyze these discussions.

Query: "{query}"

SESSIONS DATA:
{session_contexts}

REQUIRED ANALYSIS:
1. What are the key patterns across sessions?
2. What stands out as interesting or unusual?
3. What evidence supports your observations? (cite quotes and metrics)
4. What actionable insights emerge?

Be specific and evidence-based."""
}


def get_system_prompt(focus_area: str) -> str:
    """Get appropriate system prompt for focus area"""
    return SYSTEM_PROMPTS.get(focus_area, SYSTEM_PROMPTS['general'])


def get_user_prompt(
    focus_area: str,
    intent: str,
    query: str,
    session_contexts: str = "",
    high_context: str = "",
    low_context: str = "",
    speaker_context: str = "",
    speaker_name: str = "",
    retrieval_rationale: str = ""
) -> str:
    """
    Get formatted user prompt for query type.

    Args:
        focus_area: 'argumentation', 'collaboration', 'speaker', 'evolution', 'topic', 'general'
        intent: 'find', 'compare', 'analyze', 'explain'
        query: Original user query
        session_contexts: Combined context for sessions
        high_context: Context for high-metric sessions (for contrastive)
        low_context: Context for low-metric sessions (for contrastive)
        speaker_context: Context for speaker analysis
        speaker_name: Speaker being analyzed
        retrieval_rationale: Explanation of WHY these sessions were retrieved
    """
    # Inject retrieval rationale before session data if provided
    if retrieval_rationale:
        session_contexts = f"{retrieval_rationale}\n\n---\n\nSESSION DATA:\n{session_contexts}"
    # Select template based on focus and intent
    if focus_area == 'speaker':
        template_key = 'speaker_analyze'
    elif intent == 'explain' and (high_context or low_context):
        template_key = f'{focus_area}_explain'
    elif focus_area in ['argumentation', 'collaboration', 'evolution']:
        if intent in ['explain', 'analyze']:
            template_key = f'{focus_area}_explain' if high_context else f'{focus_area}_find'
        else:
            template_key = f'{focus_area}_find'
    elif focus_area == 'topic':
        template_key = 'topic_find'
    else:
        template_key = 'general_analyze'

    # Fallback to general if template not found
    template = USER_PROMPT_TEMPLATES.get(template_key, USER_PROMPT_TEMPLATES['general_analyze'])

    return template.format(
        query=query,
        session_contexts=session_contexts,
        high_context=high_context,
        low_context=low_context,
        speaker_context=speaker_context,
        speaker_name=speaker_name
    )


def format_insight_response(raw_response: str, focus_area: str) -> str:
    """
    Optional post-processing of LLM response.
    Ensures consistent formatting.
    """
    # For now, return as-is
    # Could add structure validation, section headers, etc.
    return raw_response


# Metric interpretation helpers for prompts
METRIC_INTERPRETATIONS = {
    'debate_score': {
        0: "No debate or challenges",
        1: "Minimal debate",
        2: "Some debate present",
        3: "Moderate debate",
        4: "Active debate",
        5: "Strong debate with multiple challenges"
    },
    'reasoning_depth': {
        0: "No building on ideas",
        1: "Minimal elaboration",
        2: "Some idea development",
        3: "Ideas are developed and connected",
        4: "Deep reasoning chains"
    },
    'communication_score': {
        20: "Poor communication",
        40: "Below average communication",
        60: "Adequate communication",
        80: "Good communication",
        90: "Excellent communication"
    }
}


def interpret_metric(metric_name: str, value: float) -> str:
    """Get qualitative interpretation of a metric value"""
    if metric_name not in METRIC_INTERPRETATIONS:
        return f"{value}"

    interp = METRIC_INTERPRETATIONS[metric_name]
    closest_threshold = min(interp.keys(), key=lambda k: abs(k - value) if k <= value else float('inf'))
    return f"{value} ({interp.get(closest_threshold, '')})"


# =============================================================================
# SMART ASSISTANT PROMPT - Three-Layer Response Framework
# =============================================================================

SMART_ASSISTANT_SYSTEM_PROMPT = """You are a smart assistant analyzing discussion sessions for an educational analytics platform.

You have access to two types of information:
1. PRE-COMPUTED ARTIFACTS (what users see in the UI):
   - Concept maps: nodes (ideas, questions, problems, solutions) and edges (supports, challenges, builds_on)
   - 7C collaboration scores: communication, climate, contribution, conflict, constructive (0-100)
   - Speaker profiles: avg_clout, question_ratio, session_count
   - Evolution metrics: how analytic thinking, tone, certainty changed

2. RAW TRANSCRIPTS (the underlying conversation with timestamps and speakers)

Structure your response using three layers (blend them naturally, don't use explicit headers):

**GROUND** (create common ground with user):
- Reference what the artifacts show: "The concept map shows 5 challenge edges..."
- Cite specific scores: "The 7C communication score of 85 indicates..."
- This establishes facts the user can verify in the UI

**ENRICH** (add depth from transcripts):
- Quote specific dialogue: "At [2:30], David states: '[exact quote]'"
- Show HOW patterns manifest: "This challenge is effective because..."
- Connect quotes to artifact claims

**EXTEND** (provide original insight):
- Surface patterns artifacts might miss: "The transcript also reveals..."
- Offer interpretation: "This pattern suggests..."
- Note implications: "This could be valuable because..."

Your response should feel like a smart colleague who:
- Has looked at both the data visualizations (artifacts) AND the raw transcripts
- Can connect what the metrics show to what actually happened
- Notices things that the automated analysis might have missed
- Provides actionable, specific observations"""


def get_smart_assistant_system_prompt() -> str:
    """Return the smart assistant system prompt for speaker comparisons and general use."""
    return SMART_ASSISTANT_SYSTEM_PROMPT


def get_smart_assistant_prompt(
    query: str,
    grounding_strategy: str,
    artifact_description: str,
    transcript_context: str,
    focus_area: str = "general"
) -> tuple:
    """
    Build smart assistant prompts for the three-layer response.

    Returns: (system_prompt, user_prompt)
    """
    system_prompt = SMART_ASSISTANT_SYSTEM_PROMPT

    # Add focus-specific guidance
    focus_guidance = {
        'argumentation': """
Focus on argumentation patterns:
- How ideas are challenged and defended
- The quality of reasoning chains
- Whether challenges lead to resolution or remain unresolved""",
        'collaboration': """
Focus on collaboration quality:
- How participants communicate and listen
- Whether contributions are balanced
- How disagreements are handled constructively""",
        'speaker': """
Focus on speaker engagement:
- The speaker's distinctive style and patterns
- How they influence the discussion
- Their typical contributions (questions, ideas, challenges)""",
        'evolution': """
Focus on discussion evolution:
- What changed from beginning to end
- Key turning points
- What drove the changes""",
    }

    if focus_area in focus_guidance:
        system_prompt += focus_guidance[focus_area]

    # Build user prompt
    user_prompt = f"""User Query: "{query}"

{grounding_strategy}

## ARTIFACTS (what user sees in UI):
{artifact_description}

## TRANSCRIPT EXCERPTS:
{transcript_context}

Based on both the artifacts AND the transcripts, answer the user's query.
Remember: GROUND in artifacts, ENRICH with transcript quotes, EXTEND with your insights."""

    return system_prompt, user_prompt


def build_grounding_instructions(primary_artifacts: list, grounding_strategy: str) -> str:
    """
    Build specific grounding instructions based on which artifacts are relevant.
    """
    instructions = ["## HOW TO GROUND YOUR RESPONSE:"]

    if 'concept_map' in primary_artifacts:
        instructions.append("""
**Concept Map**: Reference specific edges:
- "The concept map shows X challenge edges between speakers"
- "Speaker A BUILDS ON Speaker B's point about..."
- Cite node types: "3 questions were raised, leading to 2 solutions" """)

    if '7c' in primary_artifacts:
        instructions.append("""
**7C Scores**: Cite specific scores:
- "The communication score of 85/100 indicates strong clarity"
- "Climate score of 60 suggests moderate psychological safety"
- Reference evidence quotes from the 7C analysis""")

    if 'speakers' in primary_artifacts:
        instructions.append("""
**Speaker Profile**: Reference statistics:
- "Lex's question ratio of 25% shows inquiry-oriented style"
- "Avg clout of 45 indicates moderate authority/confidence"
- Include sample quotes that characterize the speaker""")

    if 'evolution' in primary_artifacts:
        instructions.append("""
**Evolution Metrics**: Compare temporal changes:
- "Analytic thinking increased by +7.6 from first to second half"
- "Tone evolution of -2.5 suggests slight mood shift"
- Identify what caused changes""")

    if grounding_strategy:
        instructions.append(f"\n**Specific Guidance**: {grounding_strategy}")

    return "\n".join(instructions)
