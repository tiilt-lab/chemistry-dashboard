"""
Post-discussion concept map generation service.

This service generates concept maps after a discussion session ends,
allowing the LLM to have access to the full transcript context for better quality.
"""
import logging
import json
import database
from datetime import datetime
from openai import OpenAI
import os
from dotenv import load_dotenv
from tables.concept_session import ConceptSession
from tables.concept_node import ConceptNode
from tables.concept_edge import ConceptEdge
from app import db

load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None


def generate_concepts_for_session_device(session_device_id, node_types=None, edge_types=None):
    """
    Generate concept map from complete discussion transcripts.
    Called as a background job when a session ends.

    Args:
        session_device_id: ID of the session device to process
        node_types: Optional list of concept types to extract (e.g. ['idea', 'question']).
                    When provided, the LLM prompt only includes these types.
                    None means extract all types (default).
        edge_types: Optional list of relationship types to extract.
                    None means extract all types (default).

    Returns:
        ConceptSession object if successful, None if failed
    """
    if not client:
        logging.error(f"Cannot generate concepts - OpenAI client not initialized")
        return None

    logging.info(f"Starting post-discussion concept generation for session_device {session_device_id}")

    try:
        # Find or create ConceptSession
        concept_session = ConceptSession.query.filter_by(
            session_device_id=session_device_id
        ).first()

        if not concept_session:
            concept_session = ConceptSession(session_device_id=session_device_id)
            db.session.add(concept_session)
            db.session.commit()

        # Update status to processing
        concept_session.generation_status = 'processing'
        db.session.commit()

        # Get ALL transcripts for this session device
        transcripts = database.get_transcripts(session_device_id=session_device_id)

        if not transcripts:
            logging.info(f"No transcripts found for session_device {session_device_id}")
            concept_session.generation_status = 'completed'
            concept_session.generated_at = datetime.utcnow()
            db.session.commit()
            return concept_session

        # Prepare full transcript text with line numbers
        transcript_text, line_to_timestamp = prepare_transcript_for_concepts(transcripts)

        # Get speaker aliases for the response
        speaker_aliases = get_speaker_aliases(transcripts)

        # Create reverse mapping: speaker name/alias → speaker_id (for resolving LLM responses)
        speaker_name_to_id = {v: k for k, v in speaker_aliases.items()}

        # Call LLM to extract concepts (pass line mapping for timestamp resolution)
        concepts_result = extract_concepts_from_full_transcript(
            transcript_text, line_to_timestamp,
            node_types=node_types, edge_types=edge_types
        )

        if not concepts_result:
            logging.error(f"Failed to extract concepts for session_device {session_device_id}")
            concept_session.generation_status = 'failed'
            concept_session.generation_error = 'LLM extraction failed'
            db.session.commit()
            return None

        # Clear existing clusters, nodes and edges (in case of re-generation)
        # Must delete clusters first due to foreign key constraints
        from tables.concept_cluster import ConceptCluster
        ConceptCluster.query.filter_by(concept_session_id=concept_session.id).delete()
        ConceptNode.query.filter_by(concept_session_id=concept_session.id).delete()
        ConceptEdge.query.filter_by(concept_session_id=concept_session.id).delete()
        db.session.commit()

        # Store nodes
        nodes = concepts_result.get('nodes', [])
        node_id_map = {}  # Map from index to actual node ID

        for i, node_data in enumerate(nodes):
            node_id = f"node_{session_device_id}_{i}"
            speaker_id = node_data.get('speaker')

            # Resolve speaker ID from name, number, or alias
            resolved_speaker_id = None
            if speaker_id:
                if isinstance(speaker_id, int):
                    # Only use valid positive speaker IDs (skip -1 or other invalid IDs)
                    resolved_speaker_id = speaker_id if speaker_id > 0 else None
                elif str(speaker_id).lstrip('-').isdigit():
                    parsed_id = int(speaker_id)
                    resolved_speaker_id = parsed_id if parsed_id > 0 else None
                elif isinstance(speaker_id, str) and speaker_id in speaker_name_to_id:
                    # LLM returned speaker name (e.g., "Alice") - resolve to database ID
                    resolved_speaker_id = speaker_name_to_id[speaker_id]

            node = ConceptNode(
                id=node_id,
                concept_session_id=concept_session.id,
                text=node_data.get('text', ''),
                node_type=node_data.get('type', 'concept'),
                speaker_id=resolved_speaker_id,
                timestamp=node_data.get('timestamp', 0)
            )
            db.session.add(node)
            node_id_map[i] = node_id

        db.session.commit()

        # Store edges
        edges = concepts_result.get('edges', [])
        for i, edge_data in enumerate(edges):
            source_idx = edge_data.get('source')
            target_idx = edge_data.get('target')

            # Validate indices
            if source_idx not in node_id_map or target_idx not in node_id_map:
                logging.warning(f"Skipping edge with invalid indices: {source_idx} -> {target_idx}")
                continue

            edge_id = f"edge_{session_device_id}_{i}"
            edge = ConceptEdge(
                id=edge_id,
                concept_session_id=concept_session.id,
                source_node_id=node_id_map[source_idx],
                target_node_id=node_id_map[target_idx],
                edge_type=edge_data.get('type', 'relates_to')
            )
            db.session.add(edge)

        # Update discourse type and persist requested types for edit mode UI
        concept_session.discourse_type = concepts_result.get('discourse_type', 'exploratory')
        concept_session.generation_status = 'completed'
        concept_session.generated_at = datetime.utcnow()
        concept_session.requested_node_types = node_types  # None = all types
        concept_session.requested_edge_types = edge_types  # None = all types
        db.session.commit()

        logging.info(f"Successfully generated {len(nodes)} concepts and {len(edges)} edges for session_device {session_device_id}")

        # Now trigger clustering
        try:
            from concept_clustering_semantic import create_semantic_clusters
            cluster_ids = create_semantic_clusters(session_device_id)
            if cluster_ids:
                logging.info(f"Created {len(cluster_ids)} clusters for session_device {session_device_id}")
        except Exception as e:
            logging.error(f"Failed to create clusters: {e}")

        # Re-index session for RAG after concept generation completes
        from indexing_service import reindex_session
        from study_context import get_chroma_path
        reindex_session(session_device_id, reason="concept_map", chroma_path=get_chroma_path())

        return concept_session

    except Exception as e:
        logging.error(f"Error generating concepts for session_device {session_device_id}: {str(e)}", exc_info=True)

        # Update status to failed
        try:
            concept_session = ConceptSession.query.filter_by(
                session_device_id=session_device_id
            ).first()
            if concept_session:
                concept_session.generation_status = 'failed'
                concept_session.generation_error = str(e)
                db.session.commit()
        except:
            pass

        return None


def get_speaker_aliases(transcripts):
    """Get a mapping of speaker_id to alias for all speakers in transcripts."""
    speaker_ids = set()
    for t in transcripts:
        if t.speaker_id:
            speaker_ids.add(t.speaker_id)

    speaker_map = {}
    for speaker_id in speaker_ids:
        speaker = database.get_speakers(id=speaker_id)
        if speaker:
            speaker_map[speaker_id] = speaker.get_alias()
        else:
            speaker_map[speaker_id] = f"Speaker {speaker_id}"

    return speaker_map


def prepare_transcript_for_concepts(transcripts):
    """
    Prepare full transcript text for concept extraction.

    Args:
        transcripts: List of transcript objects

    Returns:
        Tuple of (formatted_string, line_to_timestamp_map)
        - formatted_string: Text with line numbers and speaker labels
        - line_to_timestamp_map: Dict mapping line numbers to start_time values
    """
    speaker_aliases = get_speaker_aliases(transcripts)

    # Format transcripts with line numbers for accurate reference
    transcript_lines = []
    line_to_timestamp = {}

    for i, t in enumerate(transcripts):
        line_num = i + 1  # 1-indexed for readability

        if t.speaker_id and t.speaker_id in speaker_aliases:
            speaker = speaker_aliases[t.speaker_id]
        elif t.speaker_tag:
            speaker = f"Speaker {t.speaker_tag}"
        else:
            speaker = "Unknown"

        time_min = int(t.start_time // 60)
        time_sec = int(t.start_time % 60)

        # Include line number for accurate referencing
        transcript_lines.append(f"L{line_num} [{time_min}:{time_sec:02d}] {speaker}: {t.transcript}")

        # Map line number to actual timestamp
        line_to_timestamp[line_num] = t.start_time

    return "\n".join(transcript_lines), line_to_timestamp


def extract_concepts_from_full_transcript(transcript_text, line_to_timestamp=None,
                                          node_types=None, edge_types=None):
    """
    Extract concepts and relationships from the complete discussion transcript.

    Args:
        transcript_text: Full formatted transcript with line numbers (L1, L2, etc.)
        line_to_timestamp: Dict mapping line numbers to actual timestamps
        node_types: Optional list of concept types to include in the prompt.
                    None = all types (default behavior).
        edge_types: Optional list of relationship types to include in the prompt.
                    None = all types (default behavior).

    Returns:
        Dict with nodes, edges, and discourse_type
    """
    if line_to_timestamp is None:
        line_to_timestamp = {}

    # Full type definitions — only the requested subset is sent to the LLM
    ALL_NODE_TYPES = {
        'idea': 'Main concepts and claims',
        'question': 'Questions asked (preserve question form)',
        'hypothesis': 'Testable predictions or proposed explanations',
        'example': 'Concrete examples given',
        'problem': 'Problems or challenges identified',
        'solution': 'Proposed solutions or approaches',
        'goal': 'Stated objectives or goals',
        'uncertainty': 'Expressed doubts or unknowns',
        'conclusion': 'Final decisions or conclusions reached',
        'action': 'Action items or next steps',
    }

    ALL_EDGE_TYPES = {
        'supports': 'One idea provides evidence for or agrees with another',
        'contrasts_with': 'Two ideas present opposing or alternative viewpoints',
        'elaborates': 'One idea adds detail or explanation to another',
        'builds_on': 'One idea genuinely develops or extends another',
        'challenges': 'One idea disagrees with or counters another',
        'exemplifies': 'One idea is a concrete example of another',
        'answers': 'One idea responds to a question',
        'similar_to': 'Two ideas express similar things in different words',
        'synthesizes': 'One idea combines multiple other ideas',
        'relates_to': 'A thematic connection that doesn\'t fit the above types',
    }

    # Select which types to include in the prompt
    active_node_types = {k: v for k, v in ALL_NODE_TYPES.items()
                         if k in node_types} if node_types else ALL_NODE_TYPES
    active_edge_types = {k: v for k, v in ALL_EDGE_TYPES.items()
                         if k in edge_types} if edge_types else ALL_EDGE_TYPES

    # Build the type sections dynamically
    node_type_lines = "\n".join(f"- {k}: {v}" for k, v in active_node_types.items())
    edge_type_lines = "\n".join(f"- {k}: {v}" for k, v in active_edge_types.items())

    # Optional constraint note when types are filtered
    type_constraint = ""
    if node_types:
        type_constraint += f"\nIMPORTANT: Only extract concepts of these types: {', '.join(node_types)}. Do NOT create nodes of any other type."
    if edge_types:
        type_constraint += f"\nIMPORTANT: Only use these relationship types: {', '.join(edge_types)}. Do NOT create edges of any other type."

    # GPT-4o supports 128K tokens. 400K chars (~100K tokens) is safe for full discussions
    max_chars = 400000  # ~100k tokens - plenty of room for most discussions
    if len(transcript_text) > max_chars:
        logging.warning(f"Transcript very long ({len(transcript_text)} chars), truncating to {max_chars}")
        transcript_text = transcript_text[:max_chars] + "\n[... transcript truncated ...]"

    prompt = f"""Analyze this discussion and extract a knowledge graph that faithfully represents the ideas and how they relate.

DISCUSSION TRANSCRIPT (each line starts with L# for line reference):
{transcript_text}

TASK: Extract the key concepts from this discussion and identify how they are connected. Focus on accurately representing the intellectual content — what was discussed, and how the ideas relate to each other.

CONCEPT TYPES (choose the most fitting):
{node_type_lines}

RELATIONSHIP TYPES (choose the type that best describes the actual relationship):
{edge_type_lines}
{type_constraint}

REQUIREMENTS:
- Extract the concepts that matter — capture the substance of the discussion
- Connect ideas based on their actual intellectual relationship, not their order in the transcript
- If two ideas discuss the same theme at different points, connect them
- For "source_line", use the LINE NUMBER (e.g., 5 for L5) where the concept is primarily mentioned

Return a JSON object:
{{
    "nodes": [
        {{"text": "concept text (3-20 words)", "type": "type", "speaker": "speaker_id_or_name", "source_line": line_number}}
    ],
    "edges": [
        {{"source": node_index, "target": node_index, "type": "relationship_type"}}
    ],
    "discourse_type": "exploratory|problem_solving|analytical|planning|mixed",
    "summary": "1-2 sentence summary of the discussion"
}}"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert knowledge graph extractor for academic discussions.
Extract a concept map that faithfully represents the intellectual content of the discussion.
Connect ideas based on their actual relationships — thematic, logical, argumentative — not just their sequence in the transcript."""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=16000
        )

        result = json.loads(response.choices[0].message.content)

        # Validate and clean the result
        nodes = result.get('nodes', [])
        edges = result.get('edges', [])

        valid_nodes = []
        for node in nodes:
            if node.get('text'):
                # Convert source_line to actual timestamp using the mapping
                source_line = node.get('source_line')
                timestamp = 0

                if source_line and isinstance(source_line, int) and source_line in line_to_timestamp:
                    timestamp = line_to_timestamp[source_line]
                elif node.get('timestamp'):
                    # Fallback to old format for backwards compatibility
                    timestamp = node.get('timestamp', 0)

                valid_nodes.append({
                    'text': node.get('text', ''),
                    'type': node.get('type', 'concept'),
                    'speaker': node.get('speaker', 'Unknown'),
                    'timestamp': timestamp,
                    'source_line': source_line  # Keep reference for debugging
                })

        valid_edges = []
        for edge in edges:
            if 'source' in edge and 'target' in edge:
                source = edge['source']
                target = edge['target']
                # Validate indices
                if isinstance(source, int) and isinstance(target, int):
                    if 0 <= source < len(valid_nodes) and 0 <= target < len(valid_nodes):
                        valid_edges.append({
                            'source': source,
                            'target': target,
                            'type': edge.get('type', 'relates_to')
                        })

        logging.info(f"Extracted {len(valid_nodes)} nodes and {len(valid_edges)} edges from full transcript")

        return {
            'nodes': valid_nodes,
            'edges': valid_edges,
            'discourse_type': result.get('discourse_type', 'exploratory'),
            'summary': result.get('summary', '')
        }

    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse LLM response as JSON: {e}")
        return None
    except Exception as e:
        logging.error(f"Error calling OpenAI API for concept extraction: {e}")
        return None
