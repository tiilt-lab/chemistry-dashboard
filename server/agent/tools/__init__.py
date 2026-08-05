"""
Agent Tools Module

Provides 17 tools organized into 4 categories:
1. Semantic Search Tools (5) - ChromaDB-based semantic search
2. Graph Traversal Tools (6) - MySQL-based graph queries
3. Artifact Retrieval Tools (4) - Direct artifact access
4. Comparison Tools (2) - Cross-session/speaker analysis

All tools inherit from BaseTool and are registered in ToolRegistry.
"""

from .base import (
    BaseTool,
    ToolResult,
    ToolRegistry,
    ToolCategory,
    ParameterSpec,
    get_tool_registry
)

# Graph tools (6)
from .graph_tools import (
    GetNodeNeighborsTool,
    GetConceptPathTool,
    GetCausalChainTool,
    GetClusterSubgraphTool,
    GetSpeakerContributionGraphTool,
    TraceConceptToSourceTool
)

# Search tools (5)
from .search_tools import (
    SearchTranscriptChunksTool,
    SearchConceptNodesTool,
    SearchConceptClustersTool,
    SearchSessionsTool,
    SearchSpeakersTool
)

# Artifact tools (4)
from .artifact_tools import (
    GetFullConceptMapTool,
    Get7CAnalysisTool,
    GetLIWCMetricsTool,
    GetTranscriptContextTool
)

# Comparison tools (2)
from .comparison_tools import (
    CompareSessionsTool,
    CompareSpeakersTool
)

__all__ = [
    # Base classes
    'BaseTool',
    'ToolResult',
    'ToolRegistry',
    'ToolCategory',
    'ParameterSpec',
    'get_tool_registry',

    # Graph tools (6)
    'GetNodeNeighborsTool',
    'GetConceptPathTool',
    'GetCausalChainTool',
    'GetClusterSubgraphTool',
    'GetSpeakerContributionGraphTool',
    'TraceConceptToSourceTool',

    # Search tools (5)
    'SearchTranscriptChunksTool',
    'SearchConceptNodesTool',
    'SearchConceptClustersTool',
    'SearchSessionsTool',
    'SearchSpeakersTool',

    # Artifact tools (4)
    'GetFullConceptMapTool',
    'Get7CAnalysisTool',
    'GetLIWCMetricsTool',
    'GetTranscriptContextTool',

    # Comparison tools (2)
    'CompareSessionsTool',
    'CompareSpeakersTool',
]
