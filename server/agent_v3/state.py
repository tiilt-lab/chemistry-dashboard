"""
Agent State Definition for BLINC Agent V3

PRAS Architecture: Plan-Reflect-Act-Synthesize
Supports true cross-representation reasoning with:
- Query decomposition into sub-goals
- Representation-aware retrieval planning
- Reflection loops per sub-goal
- Cross-representation convergence/tension analysis
- Grounded synthesis with explicit citations
"""

from typing import TypedDict, Annotated, List, Optional, Dict, Any
from operator import add
from langchain_core.messages import BaseMessage


# =============================================================================
# PRAS Stage Types
# =============================================================================

class SubGoal(TypedDict, total=False):
    """
    A sub-goal from query decomposition.

    Example:
    {
        "id": "sg1",
        "description": "Find causal relationships in student A's contributions",
        "indicators": ["causal edges in concept map", "causal language in transcript"],
        "primary_representation": "concept_map",
        "secondary_representations": ["transcript"],
        "session_filter": 19,
        "speaker_filter": "Tucker",
        "satisfied": False,
        "evidence": []
    }
    """
    id: str
    description: str
    indicators: List[str]
    primary_representation: str
    secondary_representations: List[str]
    # Explicit filters - eliminates need for regex parsing
    session_filter: Optional[int]
    speaker_filter: Optional[str]
    satisfied: bool
    evidence: List[Dict[str, Any]]


class RetrievalStep(TypedDict, total=False):
    """A single step in a retrieval plan."""
    representation: str
    purpose: str
    tool: str
    parameters: Dict[str, Any]
    priority: str  # "primary", "secondary", "verification"


class RetrievalPlan(TypedDict, total=False):
    """Plan for retrieving evidence for a sub-goal."""
    subgoal_id: str
    steps: List[RetrievalStep]


class SubGoalResult(TypedDict, total=False):
    """Results from targeted retrieval for a sub-goal."""
    subgoal_id: str
    steps_executed: List[Dict[str, Any]]
    satisfied: bool
    evidence_summary: str
    representations_used: List[str]


class ConvergencePoint(TypedDict, total=False):
    """A point where multiple representations converge on the same conclusion."""
    claim: str
    supporting_reps: List[str]
    evidence: List[Dict[str, Any]]
    confidence: str  # "high", "medium", "low"


class TensionPoint(TypedDict, total=False):
    """A point where representations seem to conflict."""
    aspect: str
    rep1: Dict[str, Any]
    rep2: Dict[str, Any]
    interpretation: str


class CrossRepAnalysis(TypedDict, total=False):
    """Analysis of cross-representation reasoning."""
    convergence_points: List[ConvergencePoint]
    tension_points: List[TensionPoint]
    gaps: List[Dict[str, Any]]
    overall_confidence: float
    confidence_rationale: str


class GroundedClaim(TypedDict, total=False):
    """A claim with explicit grounding in evidence."""
    claim: str
    grounding: List[Dict[str, Any]]  # {"rep": str, "evidence": str, "citation": str}
    confidence: str
    convergence_note: Optional[str]


# =============================================================================
# Citation Types (for clickable artifact references)
# =============================================================================

class ArtifactRef(TypedDict, total=False):
    """Reference to a specific artifact for popover display."""
    session_id: Optional[int]
    speaker: Optional[str]
    concept_id: Optional[str]
    dimension: Optional[str]       # For 7C analysis
    cluster_id: Optional[str]
    timestamp: Optional[float]


class CitationPreview(TypedDict, total=False):
    """Preview content for citation popover."""
    title: str
    content: str                   # Up to 300 chars for preview
    metadata: Dict[str, Any]       # Type-specific metadata


class Citation(TypedDict, total=False):
    """
    Enhanced citation with full artifact reference for clickable popovers.

    Citation types:
    - transcript: (Session X, Speaker) - Direct quotes
    - concept: [Concept: "text"] - Concept map nodes
    - 7c: [7C: Dimension Score/100] - Collaboration metrics
    - cluster: [Cluster: "name"] - Thematic clusters
    - session: [Session: X Overview] - Session summaries
    - speaker: [Speaker: Name] - Speaker profiles

    Example:
    {
        "id": "cite-1",
        "citation_type": "transcript",
        "inline_text": "(Session 19, Tucker)",
        "reference_text": "Tucker's discussion on AI reasoning capabilities",
        "artifact_ref": {
            "session_id": 19,
            "speaker": "Tucker",
            "timestamp": 245.5
        },
        "preview": {
            "title": "Tucker - Session 19",
            "content": "AI systems can produce results that were not...",
            "metadata": {"wordCount": 45, "emotionalTone": 72}
        }
    }
    """
    id: str                        # Unique citation ID (e.g., "cite-1")
    citation_type: str             # "transcript" | "concept" | "7c" | "cluster" | "session" | "speaker"
    inline_text: str               # Text shown inline in response
    reference_text: str            # Text shown in reference list
    artifact_ref: ArtifactRef      # Reference for fetching artifact details
    preview: CitationPreview       # Preview data for popover
    # Grounding fields (for verification)
    source_chunk_id: Optional[str] # Deterministic ID for traceability
    validated: bool                # Whether citation was validated against retrieval results


class SpeakerProfile(TypedDict, total=False):
    """
    Comprehensive speaker profile for agent reasoning.

    Used for analyzing speaker participation patterns, communication style,
    and contribution types across sessions.
    """
    # Identity
    speaker_alias: str
    speaker_id: int

    # Participation Metrics
    session_participation: Dict[str, Any]  # {total_sessions, session_ids, total_utterances, etc.}

    # Communication Style (LIWC-based)
    communication_style: Dict[str, Any]  # {avg_analytic, avg_clout, style_summary, etc.}

    # Contribution Types
    contributions: Dict[str, Any]  # {questions, ideas, hypotheses, etc.}

    # Interaction Patterns
    interaction_patterns: Dict[str, Any]  # {responsivity, social_impact, etc.}

    # Sample Quotes (for grounding)
    sample_quotes: List[Dict[str, Any]]

    # Agent Reasoning Hints
    reasoning_hints: Dict[str, Any]  # {strengths, notable_patterns, areas_of_focus}


# =============================================================================
# Legacy Types (preserved for backwards compatibility)
# =============================================================================

class RetrievalResult(TypedDict, total=False):
    """Result from a retrieval tool."""
    tool_name: str
    query_used: str
    results: List[Dict[str, Any]]
    relevance_scores: List[float]  # 0-1 scores from grading
    is_relevant: bool  # Overall relevance assessment
    result_count: int


class AgentState(TypedDict, total=False):
    """
    State for the Ultra Agent workflow.

    Designed for intelligent reasoning, not keyword routing.
    """

    # === Core Query ===
    original_query: str
    current_query: str  # May be rewritten

    # === Conversation Context ===
    conversation_id: str
    messages: Annotated[List[BaseMessage], add]

    # Session focus (for multi-turn)
    current_session_focus: Optional[int]
    previous_session_focus: Optional[int]
    session_history: List[int]
    compared_sessions: List[int]
    current_speaker_focus: Optional[str]

    # Comparison query tracking
    is_comparison: bool  # True if this is a comparison/superlative query

    # === Hypothesis-Driven Inquiry (Co-Discovery) ===
    is_hypothesis: bool  # True if this is a hypothesis query to test
    extracted_hypothesis: Optional[str]  # The extracted hypothesis claim

    # === User Steering Preferences (Co-Discovery) ===
    preferred_representations: List[str]  # User-specified reps to focus on
    analysis_mode: Optional[str]  # 'explore', 'compare', 'trace', or None
    exclude_representations: List[str]  # Reps user wants to skip

    # === Reasoning State ===
    # Current thought from the think tool
    current_thought: Optional[str]
    # Accumulated thoughts for transparency
    thought_history: List[str]

    # === Tool Execution ===
    # Current tool being called
    current_tool: Optional[str]
    current_tool_input: Optional[Dict[str, Any]]

    # All retrieval results (accumulated)
    retrieval_results: Annotated[List[RetrievalResult], add]

    # Tools used in this query
    tools_used: List[str]

    # === Self-Reflection ===
    # Number of query rewrites attempted
    rewrite_count: int
    # Maximum rewrites allowed
    max_rewrites: int

    # Document grading results
    grading_result: Optional[Dict[str, Any]]

    # === Query Routing ===
    # Route decision: "fast_path", "reasoning", or "plan"
    route: Optional[str]
    # Fast path tool and args (if simple query)
    fast_path_tool: Optional[str]
    fast_path_args: Optional[Dict[str, Any]]

    # === Planning (for analytical queries) ===
    # Query decomposition plan
    query_plan: Optional[Dict[str, Any]]
    # Plan execution status: "ready", "executing", "executed", "failed"
    plan_status: Optional[str]

    # === PRAS: Query Decomposition (Stage 1) ===
    # Abstract constructs identified in query (e.g., "systems thinking")
    abstract_constructs: List[str]
    # Operationalization of constructs into observable indicators
    operationalization: Dict[str, List[str]]
    # Decomposed sub-goals
    sub_goals: List[SubGoal]
    # Current sub-goal being processed
    current_subgoal_index: int

    # === PRAS: Representation Planning (Stage 2) ===
    # Retrieval plans per sub-goal
    retrieval_plans: Dict[str, RetrievalPlan]

    # === PRAS: Targeted Retrieval (Stage 3) ===
    # Results per sub-goal
    subgoal_results: Dict[str, SubGoalResult]
    # Current step in retrieval plan
    current_retrieval_step: int
    # Reflections during retrieval
    retrieval_reflections: List[Dict[str, Any]]
    # Discovered sessions (for discovery chaining)
    _discovered_sessions: List[int]

    # === PRAS: Cross-Rep Reasoning (Stage 4) ===
    # Cross-representation analysis results
    cross_rep_analysis: Optional[CrossRepAnalysis]

    # === PRAS: Grounded Synthesis (Stage 5) ===
    # Claims with explicit grounding
    grounded_claims: List[GroundedClaim]
    # Representations actually used in synthesis
    representations_used: List[str]

    # === PRAS: Control ===
    # Current PRAS stage: "decompose", "plan", "retrieve", "reason", "synthesize"
    pras_stage: Optional[str]
    # Whether to use PRAS (complex queries) or legacy ReAct (simple queries)
    use_pras: bool

    # === Diagnostic Reasoning (for causal queries) ===
    # Generated hypotheses
    hypotheses: List[Dict[str, Any]]
    # The diagnostic query being analyzed
    diagnostic_query: Optional[str]
    # Evidence gathered per hypothesis
    hypothesis_evidence: Dict[str, List]
    # Scores and evaluations per hypothesis
    hypothesis_scores: Dict[str, Dict]
    # Primary hypothesis ID
    primary_hypothesis: Optional[str]
    # Contributing factor hypothesis IDs
    contributing_factors: List[str]
    # Diagnostic status
    diagnostic_status: Optional[str]
    # Full diagnostic reasoning trace
    diagnostic_reasoning: Optional[Dict[str, Any]]

    # === Verification ===
    # Claim verification results (raw from verify_claims node)
    verification_result: Optional[Dict[str, Any]]
    # Formatted verification for API response
    verification: Optional[Dict[str, Any]]

    # === Reasoning Trace (for transparency) ===
    # Full reasoning trace for response
    reasoning_trace: Optional[Dict[str, Any]]

    # === Control Flow ===
    iteration_count: int
    max_iterations: int

    # Next action: "continue", "rewrite", "synthesize", "clarify"
    next_action: str

    # === Output ===
    # Final synthesized answer
    final_answer: Optional[str]

    # Confidence in answer (0-1)
    confidence: float

    # Reflection on the answer
    reflection: Optional[str]

    # Citations for the answer
    citations: List[Dict[str, Any]]

    # Follow-up suggestions
    follow_ups: List[str]

    # Error if any
    error: Optional[str]


def create_initial_state(
    query: str,
    conversation_id: str,
    conversation_context: Optional[Dict] = None
) -> AgentState:
    """
    Create initial state for a new query.

    Args:
        query: User's query text
        conversation_id: Unique conversation identifier
        conversation_context: Optional context from previous turns
    """
    context = conversation_context or {}

    return AgentState(
        # Core
        original_query=query,
        current_query=query,

        # Conversation
        conversation_id=conversation_id,
        messages=[],

        # Session context (from previous turns)
        current_session_focus=context.get('current_session_focus'),
        previous_session_focus=context.get('previous_session_focus'),
        session_history=context.get('session_history', []),
        compared_sessions=context.get('compared_sessions', []),
        current_speaker_focus=context.get('current_speaker_focus'),

        # Reasoning
        current_thought=None,
        thought_history=[],

        # Tools
        current_tool=None,
        current_tool_input=None,
        retrieval_results=[],
        tools_used=[],

        # Self-reflection
        rewrite_count=0,
        max_rewrites=2,
        grading_result=None,

        # Query routing
        route=None,
        fast_path_tool=None,
        fast_path_args=None,

        # Planning
        query_plan=None,
        plan_status=None,

        # Diagnostic reasoning
        hypotheses=[],
        diagnostic_query=None,
        hypothesis_evidence={},
        hypothesis_scores={},
        primary_hypothesis=None,
        contributing_factors=[],
        diagnostic_status=None,
        diagnostic_reasoning=None,

        # Verification
        verification_result=None,
        verification=None,

        # Reasoning trace
        reasoning_trace=None,

        # PRAS: Query Decomposition (Stage 1)
        abstract_constructs=[],
        operationalization={},
        sub_goals=[],
        current_subgoal_index=0,

        # PRAS: Representation Planning (Stage 2)
        retrieval_plans={},

        # PRAS: Targeted Retrieval (Stage 3)
        subgoal_results={},
        current_retrieval_step=0,
        retrieval_reflections=[],
        _discovered_sessions=[],

        # PRAS: Cross-Rep Reasoning (Stage 4)
        cross_rep_analysis=None,

        # PRAS: Grounded Synthesis (Stage 5)
        grounded_claims=[],
        representations_used=[],

        # PRAS: Control
        pras_stage=None,
        use_pras=False,

        # Hypothesis-Driven Inquiry (Co-Discovery)
        is_hypothesis=False,
        extracted_hypothesis=None,

        # User Steering Preferences (Co-Discovery)
        preferred_representations=[],
        analysis_mode=None,
        exclude_representations=[],

        # Control
        iteration_count=0,
        max_iterations=8,
        next_action="continue",

        # Output
        final_answer=None,
        confidence=0.0,
        reflection=None,
        citations=[],
        follow_ups=[],
        error=None
    )
