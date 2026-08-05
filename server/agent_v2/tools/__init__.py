"""
Tool Definitions for BLINC Agent V2

Provides all tools available to the LangGraph agent:

RAG Service Tools (new):
- search_sessions_multi: RRF fusion across collections
- hybrid_session_search: metric + semantic hybrid
- get_sessions_by_metrics: metric-first filtering
- get_contrastive_sessions: high/low comparison
- generate_ultra_insights: THREE-LAYER insights
- search_speakers: speaker profile search
- find_similar_sessions: structural similarity

Adapted Existing Tools:
- search_transcript_chunks: semantic chunk search
- search_concept_nodes: concept node search
- search_concept_clusters: cluster/theme search
- get_node_neighbors: graph traversal
- get_concept_path: path between concepts
- get_causal_chain: causal reasoning chain
- get_cluster_subgraph: cluster structure
- get_speaker_contribution_graph: speaker contributions
- get_full_concept_map: complete concept map
- get_7c_analysis: 7C collaborative quality
- get_liwc_metrics: LIWC linguistic metrics
- compare_sessions: session comparison
- compare_speakers: speaker comparison
"""

from .rag_tools import (
    search_sessions_multi,
    hybrid_session_search,
    get_sessions_by_metrics,
    get_contrastive_sessions,
    generate_ultra_insights,
    search_speakers,
    find_similar_sessions,
    search_chunks
)

from .search_tools import (
    search_transcript_chunks,
    search_concept_nodes,
    search_concept_clusters
)

from .graph_tools import (
    get_node_neighbors,
    get_concept_path,
    get_causal_chain,
    get_cluster_subgraph,
    get_speaker_contribution_graph,
    get_full_concept_map
)

from .artifact_tools import (
    get_7c_analysis,
    get_liwc_metrics,
    get_session_summary
)

from .comparison_tools import (
    compare_sessions,
    compare_speakers
)

# All tools available to the agent
all_tools = [
    # RAG Service tools
    search_sessions_multi,
    hybrid_session_search,
    get_sessions_by_metrics,
    get_contrastive_sessions,
    generate_ultra_insights,
    search_speakers,
    find_similar_sessions,
    search_chunks,
    # Search tools
    search_transcript_chunks,
    search_concept_nodes,
    search_concept_clusters,
    # Graph tools
    get_node_neighbors,
    get_concept_path,
    get_causal_chain,
    get_cluster_subgraph,
    get_speaker_contribution_graph,
    get_full_concept_map,
    # Artifact tools
    get_7c_analysis,
    get_liwc_metrics,
    get_session_summary,
    # Comparison tools
    compare_sessions,
    compare_speakers
]

__all__ = [
    'all_tools',
    # RAG Service tools
    'search_sessions_multi',
    'hybrid_session_search',
    'get_sessions_by_metrics',
    'get_contrastive_sessions',
    'generate_ultra_insights',
    'search_speakers',
    'find_similar_sessions',
    'search_chunks',
    # Search tools
    'search_transcript_chunks',
    'search_concept_nodes',
    'search_concept_clusters',
    # Graph tools
    'get_node_neighbors',
    'get_concept_path',
    'get_causal_chain',
    'get_cluster_subgraph',
    'get_speaker_contribution_graph',
    'get_full_concept_map',
    # Artifact tools
    'get_7c_analysis',
    'get_liwc_metrics',
    'get_session_summary',
    # Comparison tools
    'compare_sessions',
    'compare_speakers'
]
