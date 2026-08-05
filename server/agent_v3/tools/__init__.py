"""
Tools for BLINC Agent V3

OPTIMAL 6-TOOL DESIGN (Recommended)
===================================
1. list_sessions       - Discovery: what sessions exist
2. search_for_sessions - Discovery: find sessions by topic
3. get_artifacts       - Retrieve complete artifacts (flexible include param)
4. get_speaker_profile - Complete speaker view with graph connections
5. synthesize          - Cross-rep AND cross-session synthesis
6. find_concept_path   - Graph reasoning (algorithmic traversal)

Design Principles:
- Artifact-centric: Once relevant, provide artifacts FULLY (no fragment search)
- Multi-representation: Three artifact types (Transcript, Concept Map, 7C)
- Cross-rep synthesis: Reason across representations, find convergences/discrepancies
- Tool economy: Minimal set of principled tools (not proliferation)

Legacy tools kept for backward compatibility but delegate to the optimal 6.
"""

# =============================================================================
# OPTIMAL 6-TOOL DESIGN (Recommended)
# =============================================================================
from .artifact_tools import (
    # Core 8 tools (new design)
    list_sessions as artifact_list_sessions,
    search_for_sessions,
    get_transcript,
    get_concept_map,
    get_7c_analysis,
    get_liwc_metrics,
    get_speaker_profile,
    find_concept_path,
    # Legacy combined tools
    get_artifacts,
    synthesize,
    # Backward compatibility aliases (deprecated)
    get_transcript_artifact,
    get_concept_map_artifact,
    get_collaboration_artifact,
    get_speaker_artifacts,
    synthesize_cross_representation,
    cross_reference_claim,
    get_session_artifacts,
    # Registries
    ARTIFACT_TOOLS,
    COMBINED_TOOLS as ARTIFACT_COMBINED_TOOLS,
    ARTIFACT_TOOL_DESCRIPTIONS
)

# =============================================================================
# LEGACY TOOLS (Backward Compatibility)
# =============================================================================
from .search_tools import (
    search_transcripts,
    search_sessions,
    search_concepts,
    search_communities
)
from .analysis_tools import (
    list_sessions,
    get_session_overview,
    get_collaboration_analysis,
    compare_sessions,
    analyze_speaker,
    get_speaker_session_profile,
    compare_speakers,
    # Co-Discovery tools
    test_hypothesis
)
from .graph_tools import (
    explore_concepts,
    find_reasoning_path,
    get_concept_map as graph_get_concept_map  # Renamed to avoid conflict with artifact_tools version
)
from .reasoning_tools import (
    think,
    clarify
)
from .cross_rep_tools import (
    trace_to_transcript,
    get_multi_rep_evidence,
    get_speaker_unified_view,
    check_evidence_convergence,
    find_representation_gaps
)

# =============================================================================
# ALL TOOLS (Legacy - 21 fragmented tools)
# =============================================================================
ALL_TOOLS = {
    # Reasoning
    "think": think,
    "clarify": clarify,
    # Search
    "list_sessions": list_sessions,
    "search_transcripts": search_transcripts,
    "search_sessions": search_sessions,
    "search_concepts": search_concepts,
    "search_communities": search_communities,
    # Analysis
    "get_session_overview": get_session_overview,
    "get_collaboration_analysis": get_collaboration_analysis,
    "compare_sessions": compare_sessions,
    "analyze_speaker": analyze_speaker,
    "get_speaker_session_profile": get_speaker_session_profile,
    "compare_speakers": compare_speakers,
    # Graph
    "explore_concepts": explore_concepts,
    "find_reasoning_path": find_reasoning_path,
    "get_concept_map": get_concept_map,  # Uses artifact_tools version with graph stats
    # Cross-Representation Tools
    "trace_to_transcript": trace_to_transcript,
    "get_multi_rep_evidence": get_multi_rep_evidence,
    "get_speaker_unified_view": get_speaker_unified_view,
    "check_evidence_convergence": check_evidence_convergence,
    "find_representation_gaps": find_representation_gaps
}

# =============================================================================
# COMBINED TOOLS (Optimal 8 + Legacy for transition)
# =============================================================================
COMBINED_TOOLS = {
    # OPTIMAL 8 TOOLS (from artifact_tools - new versions)
    "list_sessions": artifact_list_sessions,  # Use artifact_tools version
    "search_for_sessions": search_for_sessions,
    "get_transcript": get_transcript,
    "get_concept_map": get_concept_map,
    "get_7c_analysis": get_7c_analysis,
    "get_liwc_metrics": get_liwc_metrics,
    "get_speaker_profile": get_speaker_profile,
    "find_concept_path": find_concept_path,
    # Legacy combined tools
    "get_artifacts": get_artifacts,
    "synthesize": synthesize,
    # Backward compatibility aliases (deprecated)
    "get_transcript_artifact": get_transcript_artifact,
    "get_concept_map_artifact": get_concept_map_artifact,
    "get_collaboration_artifact": get_collaboration_artifact,
    "get_speaker_artifacts": get_speaker_artifacts,
    "synthesize_cross_representation": synthesize_cross_representation,
    "cross_reference_claim": cross_reference_claim,
    "get_session_artifacts": get_session_artifacts,
    # Keep legacy analysis tools
    "compare_sessions": compare_sessions,
    "think": think,
    # Co-Discovery tools (hypothesis-driven inquiry)
    "test_hypothesis": test_hypothesis,
    # Legacy tools referenced by representation_planner
    "get_collaboration_analysis": get_collaboration_analysis,
    "get_session_overview": get_session_overview,
    "analyze_speaker": analyze_speaker,
    "search_transcripts": search_transcripts,
    "search_concepts": search_concepts,
}

__all__ = [
    # Tool registries
    'ALL_TOOLS',
    'ARTIFACT_TOOLS',
    'COMBINED_TOOLS',
    'ARTIFACT_TOOL_DESCRIPTIONS',
    # OPTIMAL 8 TOOLS
    'list_sessions',
    'search_for_sessions',
    'get_transcript',
    'get_concept_map',
    'get_7c_analysis',
    'get_liwc_metrics',
    'get_speaker_profile',
    'find_concept_path',
    # Legacy combined tools
    'get_artifacts',
    'synthesize',
    # Backward compatibility aliases (deprecated)
    'get_transcript_artifact',
    'get_concept_map_artifact',
    'get_collaboration_artifact',
    'get_speaker_artifacts',
    'synthesize_cross_representation',
    'cross_reference_claim',
    'get_session_artifacts',
    # Legacy tools
    'think',
    'clarify',
    'search_transcripts',
    'search_sessions',
    'search_concepts',
    'search_communities',
    'get_session_overview',
    'get_collaboration_analysis',
    'compare_sessions',
    'analyze_speaker',
    'get_speaker_session_profile',
    'compare_speakers',
    'explore_concepts',
    'find_reasoning_path',
    'get_concept_map',  # Uses artifact_tools version with graph stats
    'graph_get_concept_map',  # Legacy graph_tools version
    'trace_to_transcript',
    'get_multi_rep_evidence',
    'get_speaker_unified_view',
    'check_evidence_convergence',
    'find_representation_gaps',
    # Co-Discovery tools
    'test_hypothesis'
]
