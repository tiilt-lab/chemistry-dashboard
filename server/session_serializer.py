# server/session_serializer.py
"""
Session Serializer for Hierarchical RAG

Generates rich text documents from concept maps and 7C analysis
for session-level semantic search.
"""

import json
import logging
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionSerializer:
    """
    Serializes session data (concept maps + 7C analysis) into embeddable text documents.

    The output captures:
    - Semantic content (cluster summaries, key concepts)
    - Structural patterns (edge types, concept chains)
    - Collaborative quality (7C scores, evidence, explanations)
    """

    # Node types considered important for different purposes
    KEY_NODE_TYPES = {
        'inquiry': ['question', 'uncertainty'],
        'reasoning': ['hypothesis', 'evidence', 'conclusion', 'interpretation'],
        'problem_solving': ['problem', 'cause', 'solution', 'constraint'],
        'construction': ['idea', 'elaboration', 'example', 'synthesis'],
        'evaluation': ['evaluation', 'challenge', 'counterpoint']
    }

    # Edge types grouped by category
    EDGE_CATEGORIES = {
        'building': ['builds_on', 'elaborates', 'supports', 'extends', 'clarifies'],
        'challenging': ['challenges', 'contradicts', 'questions', 'disagrees_with'],
        'connecting': ['relates_to', 'similar_to', 'contrasts_with', 'synthesizes'],
        'causal': ['causes', 'leads_to', 'enables', 'solves', 'answers']
    }

    def serialize_all(self, session_device_id: int) -> Optional[Dict]:
        """
        Generate 3 separate documents for the 5-collection architecture.

        Returns separate documents for:
        - transcript: Full session transcript for topic-based search
        - concepts: Concept map structure for pattern queries
        - seven_c: 7C analysis for quality queries

        Args:
            session_device_id: The session device to serialize

        Returns:
            Dict with 'transcript', 'concepts', 'seven_c' texts and shared 'metadata'
            Returns None if no data available
        """
        from tables.concept_session import ConceptSession
        from tables.seven_cs_analysis import SevenCsAnalysis
        from tables.transcript import Transcript

        # Get concept session
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()

        # Get 7C analysis
        seven_cs = SevenCsAnalysis.query.filter_by(
            session_device_id=session_device_id,
            analysis_status='completed'
        ).order_by(SevenCsAnalysis.created_at.desc()).first()

        # Get transcripts
        transcripts = Transcript.query.filter_by(
            session_device_id=session_device_id
        ).order_by(Transcript.start_time).all()

        # Check if we have any data
        if not concept_session and not seven_cs and not transcripts:
            logger.warning(f"No data found for {session_device_id}")
            return None

        # Generate separate documents
        transcript_text = None
        concepts_text = None
        seven_c_text = None

        # 1. Full transcript document
        if transcripts:
            transcript_text = self._serialize_transcripts(transcripts)

        # 2. Concept map structure document
        if concept_session and concept_session.nodes:
            concepts_text = self._serialize_concept_structure(
                concept_session.nodes,
                concept_session.edges,
                concept_session.discourse_type
            )

        # 3. 7C analysis document
        if seven_cs and seven_cs.analysis_summary:
            seven_c_text = self._serialize_seven_cs(seven_cs)

        # At least one document must exist
        if not any([transcript_text, concepts_text, seven_c_text]):
            logger.warning(f"No content to serialize for session_device {session_device_id}")
            return None

        # Compute shared metadata for filtering
        metadata = self._compute_all_metrics(
            session_device_id, concept_session, seven_cs, transcripts
        )

        return {
            "transcript": transcript_text,
            "concepts": concepts_text,
            "seven_c": seven_c_text,
            "metadata": metadata
        }

    def serialize_for_embedding(self, session_device_id: int) -> Optional[Dict]:
        """
        Generate rich session document for embedding (legacy combined format).

        Args:
            session_device_id: The session device to serialize

        Returns:
            Dict with 'text' (document for embedding) and 'metadata' (for filtering)
            Returns None if no data available
        """
        from tables.concept_session import ConceptSession
        from tables.seven_cs_analysis import SevenCsAnalysis
        from tables.transcript import Transcript

        # Get concept session
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()

        # Get 7C analysis
        seven_cs = SevenCsAnalysis.query.filter_by(
            session_device_id=session_device_id,
            analysis_status='completed'
        ).order_by(SevenCsAnalysis.created_at.desc()).first()

        # Get transcripts
        transcripts = Transcript.query.filter_by(
            session_device_id=session_device_id
        ).order_by(Transcript.start_time).all()

        # Check if we have any data
        if not concept_session and not seven_cs and not transcripts:
            logger.warning(f"No data found for {session_device_id}")
            return None

        document_parts = []

        # 1. Serialize full transcripts with speaker labels
        if transcripts:
            document_parts.append(self._serialize_transcripts(transcripts))

        # 2. Serialize concept map structure (with speaker attribution)
        if concept_session and concept_session.nodes:
            document_parts.append(self._serialize_concept_structure(
                concept_session.nodes,
                concept_session.edges,
                concept_session.discourse_type
            ))

        # 3. Serialize 7C analysis
        if seven_cs and seven_cs.analysis_summary:
            document_parts.append(self._serialize_seven_cs(seven_cs))

        if not document_parts:
            logger.warning(f"No content to serialize for session_device {session_device_id}")
            return None

        # Combine into embedding document
        document = "\n\n".join(filter(None, document_parts))

        # Compute metrics for filtering
        metadata = self._compute_all_metrics(
            session_device_id, concept_session, seven_cs, transcripts
        )

        return {
            "text": document,
            "metadata": metadata
        }

    def _serialize_transcripts(self, transcripts: List) -> str:
        """
        Serialize full session transcripts with speaker labels.
        This provides rich semantic content for embedding.
        """
        if not transcripts:
            return ""

        # Build speaker alias lookup
        speaker_aliases = self._get_speaker_aliases(transcripts)

        lines = ["TRANSCRIPT:"]
        for t in transcripts:
            # Get speaker label
            if t.speaker_id and t.speaker_id in speaker_aliases:
                speaker = speaker_aliases[t.speaker_id]
            elif t.speaker_tag:
                speaker = t.speaker_tag
            else:
                speaker = "Unknown"

            # Add transcript with speaker label
            lines.append(f"{speaker}: {t.transcript}")

        return "\n".join(lines)

    def _get_speaker_aliases(self, transcripts: List) -> Dict[int, str]:
        """Build speaker_id to alias mapping."""
        import database as db_helper

        speaker_ids = set(t.speaker_id for t in transcripts if t.speaker_id)
        speaker_map = {}

        for speaker_id in speaker_ids:
            speaker = db_helper.get_speakers(id=speaker_id)
            if speaker:
                speaker_map[speaker_id] = speaker.alias or speaker.get_alias()
            else:
                speaker_map[speaker_id] = f"Speaker {speaker_id}"

        return speaker_map

    def _serialize_concept_structure(self, nodes: List, edges: List,
                                      discourse_type: str = None) -> str:
        """
        Serialize the actual concept map structure - nodes, edges, and chains.
        Includes speaker attribution for each concept.
        """
        if not nodes:
            return ""

        import database as db_helper

        parts = []

        # Discourse type header
        if discourse_type:
            parts.append(f"DISCUSSION TYPE: {discourse_type}")

        # Build speaker lookup for nodes
        speaker_ids = set(n.speaker_id for n in nodes if n.speaker_id)
        speaker_map = {}
        for speaker_id in speaker_ids:
            speaker = db_helper.get_speakers(id=speaker_id)
            if speaker:
                speaker_map[speaker_id] = speaker.alias or speaker.get_alias()
            else:
                speaker_map[speaker_id] = f"Speaker {speaker_id}"

        # Group nodes by type with speaker attribution
        by_type = defaultdict(list)
        for node in nodes:
            node_type = node.node_type or 'concept'
            speaker_name = speaker_map.get(node.speaker_id, "Unknown") if node.speaker_id else "Unknown"
            by_type[node_type].append((node.text, speaker_name))

        # Key concepts by type with speaker attribution (no truncation)
        parts.append("\nCONCEPT STRUCTURE:")

        # Node type configuration: (plural_label, verb_phrase)
        # All 10 supported node types from concept_generation_service.py
        node_type_config = {
            'question': ('Questions', 'asked'),
            'idea': ('Ideas', 'proposed'),
            'hypothesis': ('Hypotheses', 'hypothesized'),
            'example': ('Examples', 'illustrated'),
            'problem': ('Problems', 'identified'),
            'solution': ('Solutions', 'suggested'),
            'goal': ('Goals', 'set goal'),
            'uncertainty': ('Uncertainties', 'expressed doubt'),
            'conclusion': ('Conclusions', 'concluded'),
            'action': ('Actions', 'proposed action'),
        }

        # Process all node types without truncation
        for node_type, (label, verb) in node_type_config.items():
            if by_type.get(node_type):
                nodes_of_type = by_type[node_type]
                parts.append(f"- {label} ({len(nodes_of_type)}):")
                for text, speaker in nodes_of_type:
                    parts.append(f'  {speaker} {verb}: "{text[:80]}"')

        # Edge type patterns
        if edges:
            edge_counts = Counter(e.edge_type for e in edges)
            parts.append("\nRELATIONSHIP PATTERNS:")

            for edge_type, count in edge_counts.most_common(5):
                description = self._get_edge_description(edge_type, count, len(edges))
                parts.append(f"- {edge_type} ({count}): {description}")

        # Concept chains - showing argument flow
        if edges:
            chains = self._extract_concept_chains(nodes, edges)
            if chains:
                parts.append("\nCONCEPT CHAINS (argument flow):")
                for chain in chains[:3]:  # Top 3 chains
                    parts.append(chain)

        return "\n".join(parts)

    def _get_edge_description(self, edge_type: str, count: int, total: int) -> str:
        """Generate a description for an edge type based on its frequency."""
        ratio = count / total if total > 0 else 0

        descriptions = {
            'builds_on': "Ideas frequently elaborated on each other",
            'elaborates': "Concepts were developed with more detail",
            'supports': "Evidence provided for claims",
            'challenges': "Productive disagreement present",
            'contradicts': "Conflicting viewpoints explored",
            'questions': "Inquiry-driven connections",
            'relates_to': "Thematic connections between ideas",
            'causes': "Causal reasoning demonstrated",
            'solves': "Solutions linked to problems",
            'answers': "Questions addressed with responses",
            'synthesizes': "Multiple ideas combined"
        }

        base = descriptions.get(edge_type, "Connections between concepts")

        if ratio > 0.3:
            return f"(dominant) {base}"
        elif ratio > 0.15:
            return f"(significant) {base}"
        else:
            return base

    def _extract_concept_chains(self, nodes: List, edges: List, max_depth: int = 4) -> List[str]:
        """
        Extract meaningful concept chains showing argument flow.
        Returns formatted chain strings like:
        [question] "Why..." -> [hypothesis] "Because..." -> [evidence] "Data shows..."
        """
        if not edges:
            return []

        # Build adjacency list
        adj = defaultdict(list)
        for edge in edges:
            adj[edge.source_node_id].append((edge.target_node_id, edge.edge_type))

        # Create node lookup
        node_map = {n.id: n for n in nodes}

        # Find chains starting from questions, problems, or hypotheses
        start_types = {'question', 'problem', 'hypothesis', 'observation'}
        chains = []

        for node in nodes:
            if node.node_type in start_types and node.id in adj:
                chain = self._follow_chain(node, adj, node_map, max_depth)
                if len(chain) >= 2:
                    chains.append(chain)

        # Format chains as strings
        formatted_chains = []
        for chain in chains[:5]:  # Limit to 5 chains
            chain_str = " -> ".join([
                f'[{n.node_type}] "{n.text[:50]}..."' if len(n.text) > 50
                else f'[{n.node_type}] "{n.text}"'
                for n in chain
            ])
            formatted_chains.append(chain_str)

        return formatted_chains

    def _follow_chain(self, start_node, adj: Dict, node_map: Dict,
                      max_depth: int) -> List:
        """Follow a chain of connected concepts."""
        chain = [start_node]
        current = start_node.id
        visited = {current}

        for _ in range(max_depth):
            if current not in adj:
                break

            # Find best next node (prefer meaningful edge types)
            best_next = None
            best_priority = -1

            priority_edges = ['leads_to', 'causes', 'supports', 'builds_on',
                            'answers', 'elaborates', 'solves']

            for next_id, edge_type in adj[current]:
                if next_id in visited or next_id not in node_map:
                    continue

                priority = priority_edges.index(edge_type) if edge_type in priority_edges else len(priority_edges)
                if best_next is None or priority < best_priority:
                    best_next = next_id
                    best_priority = priority

            if best_next is None:
                break

            chain.append(node_map[best_next])
            visited.add(best_next)
            current = best_next

        return chain

    def _serialize_seven_cs(self, analysis) -> str:
        """
        Serialize 7C analysis with scores, explanations, and evidence.

        The explanation serves as a "semantic shortcut" - natural language queries
        about collaboration quality can match against these interpretive descriptions.
        Key evidence provides concrete grounding from the transcript.
        """
        if not analysis or not analysis.analysis_summary:
            return ""

        parts = ["COLLABORATIVE QUALITY ASSESSMENT:"]

        # Iterate over whatever dimensions are present (active) in this analysis
        for dimension, dim_data in analysis.analysis_summary.items():
            if not dim_data:
                continue

            score = dim_data.get('score', 0)
            explanation = dim_data.get('explanation', '')
            evidence_list = dim_data.get('evidence', [])

            # Format evidence (top 2 quotes, no truncation)
            evidence_str = ""
            if evidence_list:
                evidence_quotes = evidence_list[:2]
                evidence_str = "; ".join(f'"{e}"' for e in evidence_quotes if e)

            parts.append(f"""
{dimension.upper()} ({score}/100):
  {explanation if explanation else 'No explanation available'}
  Evidence: {evidence_str if evidence_str else 'No evidence recorded'}""")

        return "\n".join(parts)

    def _compute_all_metrics(self, session_device_id: int,
                             concept_session, seven_cs, transcripts=None) -> Dict:
        """
        Compute all metrics for ChromaDB metadata filtering.
        These are stored alongside the embedding for efficient filtering.
        """
        from tables.session_device import SessionDevice
        from tables.session import Session

        # Get session_device and related session
        session_device = SessionDevice.query.get(session_device_id)
        session_id = session_device.session_id if session_device else None
        session = Session.query.get(session_id) if session_id else None

        # Get session and device names
        session_name = session.name if session else None
        device_name = session_device.name if session_device else None

        # Get speaker names from transcripts (use speaker_tag directly)
        speaker_names = []
        if transcripts:
            speaker_tags = set()
            for t in transcripts:
                if t.speaker_tag:
                    speaker_tags.add(t.speaker_tag)
            speaker_names = sorted(list(speaker_tags))[:10]  # Limit to 10 speakers

        metrics = {
            "session_device_id": session_device_id,
            "session_id": session_id,
            "session_name": session_name,
            "device_name": device_name,
            "speakers": ",".join(speaker_names) if speaker_names else None,
            "indexed_at": datetime.utcnow().isoformat(),
            "has_concept_map": concept_session is not None and concept_session.generation_status == 'completed',
            "has_seven_cs": seven_cs is not None,
            "transcript_count": len(transcripts) if transcripts else 0
        }

        # Concept map metrics
        if concept_session and concept_session.nodes:
            nodes = concept_session.nodes
            edges = concept_session.edges or []

            # Basic counts
            metrics["node_count"] = len(nodes)
            metrics["edge_count"] = len(edges)
            metrics["discourse_type"] = concept_session.discourse_type or "unknown"

            # Node type counts and ratios
            node_types = Counter(n.node_type for n in nodes)
            metrics["question_count"] = node_types.get('question', 0)
            metrics["hypothesis_count"] = node_types.get('hypothesis', 0)
            metrics["solution_count"] = node_types.get('solution', 0)
            metrics["problem_count"] = node_types.get('problem', 0)

            # Ratios (for filtering)
            total_nodes = len(nodes)
            if total_nodes > 0:
                metrics["question_ratio"] = round(metrics["question_count"] / total_nodes, 3)
            else:
                metrics["question_ratio"] = 0.0

            # Edge type counts
            if edges:
                edge_types = Counter(e.edge_type for e in edges)
                metrics["challenge_count"] = edge_types.get('challenges', 0) + edge_types.get('contradicts', 0)
                metrics["support_count"] = edge_types.get('supports', 0) + edge_types.get('builds_on', 0)

                total_edges = len(edges)
                metrics["challenge_ratio"] = round(metrics["challenge_count"] / total_edges, 3)
            else:
                metrics["challenge_count"] = 0
                metrics["support_count"] = 0
                metrics["challenge_ratio"] = 0.0

            # Cluster info
            if concept_session.clusters:
                metrics["cluster_count"] = len(concept_session.clusters)
                metrics["cluster_names"] = json.dumps([
                    c.cluster_name for c in concept_session.clusters[:5]
                ])
            else:
                metrics["cluster_count"] = 0
                metrics["cluster_names"] = "[]"

            # Duration from node timestamps
            timestamps = [n.timestamp for n in nodes if n.timestamp]
            if timestamps:
                metrics["duration_seconds"] = max(timestamps) - min(timestamps)
            else:
                metrics["duration_seconds"] = 0

            # Speaker count from nodes
            speakers = set(n.speaker_id for n in nodes if n.speaker_id)
            metrics["speaker_count"] = len(speakers)
        else:
            # Defaults when no concept map
            metrics["node_count"] = 0
            metrics["edge_count"] = 0
            metrics["discourse_type"] = "unknown"
            metrics["question_count"] = 0
            metrics["question_ratio"] = 0.0
            metrics["challenge_count"] = 0
            metrics["challenge_ratio"] = 0.0
            metrics["cluster_count"] = 0
            metrics["cluster_names"] = "[]"
            metrics["duration_seconds"] = 0
            # Get speaker count from transcripts if no concept map
            if transcripts:
                speakers = set(t.speaker_id for t in transcripts if t.speaker_id)
                metrics["speaker_count"] = len(speakers)
            else:
                metrics["speaker_count"] = 0

        # Collaboration assessment metrics (dynamic dimensions)
        if seven_cs and seven_cs.analysis_summary:
            summary = seven_cs.analysis_summary
            for dimension, dim_data in summary.items():
                if dim_data and isinstance(dim_data, dict):
                    metrics[f"{dimension}_score"] = dim_data.get('score', 0)

        return metrics

    def generate_fallback_summary(self, session_device_id: int) -> Optional[Dict]:
        """
        Generate a basic summary from transcripts when no concept map exists.
        Used as fallback for sessions without concept generation.
        """
        from tables.transcript import Transcript
        from openai import OpenAI
        import os

        # Get transcripts
        transcripts = Transcript.query.filter_by(
            session_device_id=session_device_id
        ).order_by(Transcript.start_time).limit(100).all()

        if not transcripts:
            logger.warning(f"No transcripts found for fallback summary: {session_device_id}")
            return None

        # Combine transcript text
        full_text = " ".join([t.transcript for t in transcripts])[:8000]

        # Use LLM to generate summary
        try:
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": f"Summarize this discussion in 3-4 sentences, focusing on main topics and discussion patterns:\n\n{full_text}"
                }],
                temperature=0.3,
                max_tokens=200
            )
            summary = response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating fallback summary: {e}")
            summary = "Summary generation failed."

        # Basic metrics from transcripts
        speaker_ids = set(t.speaker_id for t in transcripts if t.speaker_id)

        # Get session_id
        from tables.session_device import SessionDevice
        session_device = SessionDevice.query.get(session_device_id)
        session_id = session_device.session_id if session_device else None

        return {
            "text": f"DISCUSSION SUMMARY (from transcripts):\n{summary}",
            "metadata": {
                "session_device_id": session_device_id,
                "session_id": session_id,  # Added for routing to pod details
                "indexed_at": datetime.utcnow().isoformat(),
                "has_concept_map": False,
                "has_seven_cs": False,
                "node_count": 0,
                "edge_count": 0,
                "discourse_type": "unknown",
                "transcript_count": len(transcripts),
                "speaker_count": len(speaker_ids),
                "cluster_count": 0,
                "cluster_names": "[]"
            }
        }

    def get_llm_context(self, session_device_id: int, max_chars: int = 4000) -> str:
        """
        Get rich context for LLM insight generation.

        Combines transcript excerpts + concept structure + 7C analysis
        into a single document optimized for LLM context windows.

        Args:
            session_device_id: The session to get context for
            max_chars: Maximum characters to return (default 4000 ~1000 tokens)

        Returns:
            Rich text document with full session data, or empty string if no data
        """
        result = self.serialize_for_embedding(session_device_id)
        if not result:
            return ""

        text = result['text']

        # Truncate intelligently if needed (keep beginning + end for context)
        if len(text) > max_chars:
            # Keep more from beginning (transcript start) and end (7C analysis)
            beginning = int(max_chars * 0.6)
            ending = max_chars - beginning - 50  # 50 chars for separator
            text = text[:beginning] + "\n\n...[content truncated]...\n\n" + text[-ending:]

        return text
