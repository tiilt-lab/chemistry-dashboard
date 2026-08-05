"""
Graph RAG V2 - Enhanced Graph-Aware Retrieval

Implements Microsoft GraphRAG-inspired features:
1. Community detection using Leiden algorithm
2. Community summarization with LLM
3. Session narrative generation
4. GraphSAGE-style structure-preserving embeddings

These create NEW collections that don't affect existing RAG Discovery.
"""

from .community_detector import CommunityDetector
from .community_summarizer import CommunitySummarizer
from .session_narrator import SessionNarrator
from .indexer import GraphRAGIndexer

__all__ = [
    'CommunityDetector',
    'CommunitySummarizer',
    'SessionNarrator',
    'GraphRAGIndexer'
]
