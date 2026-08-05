"""
Community Summarizer for Graph RAG V2

Generates LLM summaries for each detected community.
These summaries enable GraphRAG-style global search.
"""

import logging
from typing import Dict, List, Any

from openai import OpenAI

logger = logging.getLogger(__name__)


COMMUNITY_SUMMARY_PROMPT = """Summarize this community of concepts from a collaborative discussion.

## Community Concepts

{concepts}

## Instructions

Create a brief summary (2-3 sentences) that:
1. Identifies the main theme or topic
2. Highlights key ideas, questions, or conclusions
3. Notes any interesting patterns or disagreements

Focus on the intellectual content, not meta-commentary.

## Response Format
{{
    "theme": "A short (3-5 word) theme title",
    "summary": "2-3 sentence summary of the community",
    "key_concepts": ["3-5 most important concepts"],
    "concept_types": {{"questions": N, "ideas": N, "hypotheses": N, ...}}
}}
"""


class CommunitySummarizer:
    """
    Generates summaries for concept communities using LLM.

    These summaries are then embedded for global search,
    enabling questions about themes across all discussions.
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize the summarizer.

        Args:
            model: OpenAI model to use for summarization
        """
        self.model = model
        self.client = OpenAI()

    def summarize_community(
        self,
        community: Dict[str, Any],
        nodes: List[Dict],
        edges: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary for a single community.

        Args:
            community: Community with node_ids
            nodes: All nodes (will filter to community)
            edges: Optional edges for relationship context

        Returns:
            Community summary with theme, summary text, and key concepts
        """
        community_id = community.get('community_id')
        node_ids = set(community.get('node_ids', []))

        # Get nodes in this community
        community_nodes = [n for n in nodes if n.get('id') in node_ids]

        if not community_nodes:
            return {
                'community_id': community_id,
                'error': 'No nodes found'
            }

        # Format concepts for the prompt
        concepts_text = self._format_concepts(community_nodes)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": COMMUNITY_SUMMARY_PROMPT.format(concepts=concepts_text)
                }],
                temperature=0.3,
                max_tokens=300,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)

            return {
                'community_id': community_id,
                'theme': result.get('theme', 'Untitled Theme'),
                'summary': result.get('summary', ''),
                'key_concepts': result.get('key_concepts', []),
                'concept_types': result.get('concept_types', {}),
                'node_count': len(community_nodes),
                'node_ids': list(node_ids)
            }

        except Exception as e:
            logger.error(f"Community summarization error: {e}")

            # Fallback summary
            return self._fallback_summary(community_id, community_nodes)

    def summarize_all_communities(
        self,
        communities: List[Dict],
        nodes: List[Dict],
        edges: List[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate summaries for all communities.

        Args:
            communities: List of detected communities
            nodes: All concept nodes
            edges: All concept edges

        Returns:
            List of community summaries
        """
        summaries = []

        for community in communities:
            summary = self.summarize_community(community, nodes, edges)
            summaries.append(summary)

        logger.info(f"Generated summaries for {len(summaries)} communities")
        return summaries

    def _format_concepts(self, nodes: List[Dict]) -> str:
        """Format concepts for the prompt."""
        lines = []

        # Group by type
        by_type = {}
        for node in nodes:
            node_type = node.get('node_type', 'concept')
            if node_type not in by_type:
                by_type[node_type] = []
            by_type[node_type].append(node)

        # Format each type
        for node_type, type_nodes in by_type.items():
            lines.append(f"\n### {node_type.title()}s ({len(type_nodes)})")
            for node in type_nodes[:10]:  # Limit per type
                text = node.get('text', '')[:200]
                speaker = node.get('speaker_alias', node.get('speaker', ''))
                if speaker:
                    lines.append(f"- [{speaker}] {text}")
                else:
                    lines.append(f"- {text}")

        return "\n".join(lines)

    def _fallback_summary(
        self,
        community_id: str,
        nodes: List[Dict]
    ) -> Dict[str, Any]:
        """Generate a fallback summary without LLM."""
        # Count types
        type_counts = {}
        for node in nodes:
            t = node.get('node_type', 'concept')
            type_counts[t] = type_counts.get(t, 0) + 1

        # Find most common words for theme
        all_text = " ".join(n.get('text', '') for n in nodes)
        words = all_text.lower().split()
        word_freq = {}
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                      'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                      'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through'}

        for word in words:
            if len(word) > 3 and word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        top_words = sorted(word_freq.items(), key=lambda x: -x[1])[:3]
        theme = " ".join(w[0].title() for w in top_words) if top_words else "Mixed Topics"

        return {
            'community_id': community_id,
            'theme': theme,
            'summary': f"A collection of {len(nodes)} concepts including {', '.join(f'{v} {k}s' for k, v in type_counts.items())}.",
            'key_concepts': [n.get('text', '')[:50] for n in nodes[:5]],
            'concept_types': type_counts,
            'node_count': len(nodes),
            'fallback': True
        }
