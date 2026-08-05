"""
AgentState Definition for BLINC Agent V2

Defines the state schema for the LangGraph workflow.
State is automatically checkpointed for conversation continuity.
"""

from typing import TypedDict, Annotated, List, Optional, Dict, Any, Sequence
from operator import add
from langchain_core.messages import BaseMessage


def merge_dicts(left: Dict, right: Dict) -> Dict:
    """Merge two dictionaries, with right taking precedence."""
    result = left.copy()
    result.update(right)
    return result


class AgentState(TypedDict, total=False):
    """
    State for LangGraph agent workflow.

    All fields use reducers to handle state updates across nodes.
    """

    # === Message History ===
    # Conversation messages (user + assistant)
    messages: Annotated[List[BaseMessage], add]

    # === Session Context (from conversation) ===
    # Currently focused session (resolved ID)
    current_session_focus: Optional[int]
    # Previously focused session (for "go back" references)
    previous_session_focus: Optional[int]
    # Currently focused speaker
    current_speaker_focus: Optional[str]
    # Session history for ordinal references ("first session", "third one")
    session_history: List[int]
    # Sessions being compared (for "both sessions" references)
    compared_sessions: List[int]

    # === Query Understanding ===
    # Original user query
    original_query: str
    # Query after reference resolution
    resolved_query: str
    # Classified query type
    query_type: str  # topic_search, session_search, comparative, speaker_search, temporal, etc.
    # Query complexity
    complexity: str  # simple, complex
    # Whether query is analytical (needs insights generation)
    is_analytical: bool
    # Extracted entities from query
    entities: Dict[str, Any]  # {session_ids, session_names, speaker_names, topics}

    # === RAG Routing ===
    # Which collections to search
    rag_collections: List[str]  # transcripts, concepts, seven_c, speakers
    # Visualization type for frontend
    visualization_type: str  # chunks, sessions, speakers, timeline, comparison, both
    # Metric filters for hybrid search
    metric_filters: Dict[str, tuple]  # {'debate_score': ('>=', 3)}

    # === Execution State ===
    # Results from tool calls
    tool_results: Annotated[List[Dict], add]
    # Tool call history (for avoiding duplicates)
    tool_call_history: List[str]
    # Citations for answer
    citations: Annotated[List[Dict], add]
    # Overall confidence in answer
    confidence: float

    # === Plan-Execute State ===
    # Generated plan steps
    plan_steps: List[str]
    # Current plan step index
    current_step_index: int
    # Accumulated plan results
    plan_results: List[Dict]

    # === ReAct State ===
    # Current ReAct thought
    current_thought: str
    # Action to take
    current_action: str
    # Action input
    current_action_input: Dict[str, Any]

    # === Control Flow ===
    # Next node to execute
    next_node: str
    # Current iteration count (for loop limiting)
    iteration_count: int
    # Maximum iterations allowed
    max_iterations: int
    # Whether clarification is needed
    needs_clarification: bool
    # Clarification question to ask
    clarification_question: str
    # Clarification options
    clarification_options: List[str]

    # === Deterministic Routing ===
    # Tool forced by classifier (bypasses LLM decision)
    force_tool: Optional[str]
    # Parameters for the forced tool
    force_tool_params: Optional[Dict[str, Any]]
    # Skip LLM decision and go directly to synthesis after forced tool
    skip_to_synthesis: bool

    # === Output ===
    # Final synthesized answer
    final_answer: Optional[str]
    # Response metadata for frontend visualization routing
    response_metadata: Dict[str, Any]
    # Error message if any
    error: Optional[str]


class ResponseMetadata(TypedDict, total=False):
    """
    Response metadata structure for frontend visualization routing.

    This structure determines which visualization components the frontend renders.
    Must match the legacy RAG UI expectations.
    """

    # Query info
    query: str
    query_type: str  # Determines primary visualization
    search_level: str  # chunks | sessions | speakers | timeline | comparison | both

    # Search results by level
    results: List[Dict]  # Chunk-level results
    session_results: List[Dict]  # Session-level results
    speaker_results: List[Dict]  # Speaker-level results

    # Special visualizations
    comparison: Dict  # For comparative queries
    timeline: List[Dict]  # For temporal queries
    similar: List[Dict]  # For similarity queries

    # Enrichment data
    insights: str  # Generated insights
    argumentation: Dict  # debate_score, reasoning_depth
    evolution: Dict  # analytic_evolution, tone_evolution

    # Metadata
    total_found: int
    filters_applied: Dict
    collections_searched: List[str]
    tools_used: List[str]
    confidence: float


def create_initial_state(
    query: str,
    session_device_id: Optional[int] = None,
    conversation_context: Optional[Dict] = None
) -> AgentState:
    """
    Create initial state for a new query.

    Args:
        query: User's query text
        session_device_id: Optional pre-focused session ID
        conversation_context: Optional context from previous turns

    Returns:
        Initialized AgentState
    """
    context = conversation_context or {}

    return AgentState(
        messages=[],
        original_query=query,
        resolved_query=query,

        # Session context
        current_session_focus=session_device_id or context.get('current_session_focus'),
        previous_session_focus=context.get('previous_session_focus'),
        current_speaker_focus=context.get('current_speaker_focus'),
        session_history=context.get('session_history', []),
        compared_sessions=context.get('compared_sessions', []),

        # Query understanding (to be filled by classifier)
        query_type='unknown',
        complexity='unknown',
        is_analytical=False,
        entities={},

        # RAG routing (to be filled by classifier)
        rag_collections=['transcripts'],
        visualization_type='chunks',
        metric_filters={},

        # Execution state
        tool_results=[],
        tool_call_history=[],
        citations=[],
        confidence=0.0,

        # Plan state
        plan_steps=[],
        current_step_index=0,
        plan_results=[],

        # ReAct state
        current_thought='',
        current_action='',
        current_action_input={},

        # Control flow
        next_node='input',
        iteration_count=0,
        max_iterations=5,
        needs_clarification=False,
        clarification_question='',
        clarification_options=[],

        # Output
        final_answer=None,
        response_metadata={},
        error=None
    )
