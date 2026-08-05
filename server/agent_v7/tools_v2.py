"""
Simplified Tool Registry for BLINC Agent V7

5 core tools that return LLM-ready text directly (no formatter needed):
1. list_sessions      - List all available sessions
2. search_sessions    - Find sessions by topic
3. get_transcript     - Get session transcript
4. get_concept_map    - Get concept map structure
5. get_collaboration_assessment - Get collaboration metrics

Design principle: Tools return what the LLM should see directly.
No intermediate JSON that gets formatted later - this prevents data loss.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from functools import wraps

# Import existing tools
from .tools.artifact_tools import (
    list_sessions as _list_sessions,
    search_for_sessions as _search_sessions,
    get_artifacts as _get_artifacts,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Collaboration Framework Definitions (included in tool output for LLM context)
# =============================================================================

SEVEN_C_DEFINITIONS = {
    "climate": "The emotional and affective aspects of the collaboration",
    "communication": "The quantity and quality of information shared among group members",
    "compatibility": "How well group members' working and interaction styles complement each other",
    "conflict": "Approaches to handling disagreements and contentious situations that arise during group work",
    "context": "Environmental factors and situational awareness: the who, why, and where of the collaboration",
    "contribution": "Individual participation and effort balance: what individual participants are, and are not, bringing to the collaboration",
    "constructive": "Overall goals of the collaboration and the team's progress toward achieving them",
}


def tool_wrapper(tool_name: str):
    """Decorator to standardize tool output and logging."""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"[Tool] {tool_name} called with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                result["tool_name"] = tool_name
                logger.info(f"[Tool] {tool_name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"[Tool] {tool_name} error: {e}")
                return {
                    "tool_name": tool_name,
                    "display": f"Error: {str(e)}",
                    "error": str(e),
                }
        return wrapper
    return decorator


# =============================================================================
# Tool 1: list_sessions
# =============================================================================

@tool_wrapper("list_sessions")
def list_sessions() -> Dict[str, Any]:
    """
    List all available discussion sessions with collaboration scores.

    Returns:
        Dict with 'display' containing LLM-ready text of all sessions,
        including collaboration scores for intelligent session selection.
    """
    result = _list_sessions()

    sessions = result.get('sessions', [])

    # Sort by collaboration score for easier scanning (highest first)
    sessions_with_scores = [s for s in sessions if s.get('collaboration_score') is not None]
    sessions_without_scores = [s for s in sessions if s.get('collaboration_score') is None]
    sessions_with_scores.sort(key=lambda x: x.get('collaboration_score', 0), reverse=True)
    sorted_sessions = sessions_with_scores + sessions_without_scores

    # Build LLM-ready text
    lines = [f"=== Available Sessions ({len(sessions)} total) ==="]
    lines.append("(Sorted by collaboration score, highest first)\n")

    for s in sorted_sessions:
        sid = s.get('session_id', s.get('session_device_id', '?'))
        name = s.get('session_name', s.get('name', 'Unnamed'))
        device_name = s.get('device_name', '')
        speakers = s.get('speakers', [])
        speaker_count = s.get('speaker_count', len(speakers))
        speaker_str = ", ".join(speakers[:5]) if speakers else "Unknown"
        collab_score = s.get('collaboration_score')

        # Format: Discussion ID: Session Name (Device Name)
        if device_name:
            lines.append(f"Discussion {sid}: {name} ({device_name})")
        else:
            lines.append(f"Discussion {sid}: {name}")
        lines.append(f"  Speakers ({speaker_count}): {speaker_str}")

        # Show collaboration score prominently
        if collab_score is not None:
            lines.append(f"  Collaboration Score: {collab_score}/100")
        else:
            lines.append(f"  Collaboration Score: N/A")
        lines.append("")

    # Add guidance for LLM
    lines.append("---")
    lines.append("TIP: For detailed collaboration breakdown, call get_collaboration_assessment(discussion_id=N)")
    lines.append("TIP: For speaker contributions, call get_speaker_profile(speaker_name='Name')")

    return {
        "display": "\n".join(lines),
        "session_count": len(sessions),
        "sessions": sorted_sessions,  # Include structured data too
    }


# =============================================================================
# Tool 2: search_sessions
# =============================================================================

@tool_wrapper("search_sessions")
def search_sessions(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Find sessions relevant to a query using semantic search.

    Args:
        query: Topic or keyword to search for
        top_k: Maximum number of results

    Returns:
        Dict with 'display' containing LLM-ready text of matching sessions
    """
    top_k = max(top_k, 5)  # Never return fewer than 5 results
    result = _search_sessions(query=query, top_k=top_k)

    sessions = result.get('sessions', [])

    # Build LLM-ready text
    lines = [f"=== Search Results for \"{query}\" ({len(sessions)} found) ===\n"]

    if not sessions:
        lines.append("No matching discussions found.")
    else:
        # Check if scores are tightly clustered — if so, tell the LLM
        scores = [s.get('relevance_score') or s.get('best_match_score') or s.get('score', 0) for s in sessions]
        if len(scores) >= 3 and scores[0] > 0:
            spread = scores[0] - scores[-1]
            if spread < 0.01:
                lines.append("Note: All results are very close in relevance — explore broadly, not just the top 1-2.\n")

        for i, s in enumerate(sessions, 1):
            sid = s.get('session_id', s.get('session_device_id', '?'))
            name = s.get('session_name', s.get('name', 'Unnamed'))
            device_name = s.get('device_name', '')
            # Check multiple possible score field names
            score = s.get('relevance_score') or s.get('best_match_score') or s.get('score', 0)
            speakers = s.get('speakers', [])
            speaker_str = ", ".join(speakers[:5]) if speakers else "Unknown"
            preview = s.get('match_preview', '')

            # Format: Discussion ID: Session Name (Device Name)
            # Note: Relevance scores intentionally omitted - all returned sessions
            # passed the search threshold, so they're all worth retrieving.
            # Showing scores would cause the decision LLM to over-optimize.
            if device_name:
                lines.append(f"{i}. Discussion {sid}: {name} ({device_name})")
            else:
                lines.append(f"{i}. Discussion {sid}: {name}")
            lines.append(f"   Speakers: {speaker_str}")
            if preview:
                lines.append(f"   Preview: {preview}")
            lines.append("")

    return {
        "display": "\n".join(lines),
        "session_count": len(sessions),
        "query": query,
        "sessions": sessions,  # Include for auto-fetch
    }


# =============================================================================
# Tool 3: get_transcript
# =============================================================================

@tool_wrapper("get_transcript")
def get_transcript(
    discussion_id: Optional[int] = None,
    discussion_ids: Optional[List[int]] = None,
    speaker_filter: str = None,
    keyword_filter: str = None,
    preview: bool = False
) -> Dict[str, Any]:
    """
    Get transcript for a discussion in human-readable format.

    Single mode: full transcript (or filtered by speaker/keyword).
    Batch mode: preview (first 5 + last 5 utterances + metadata) per session.

    Args:
        discussion_id: Discussion to get transcript for
        discussion_ids: Multiple discussions for batch preview
        speaker_filter: Optional - only get utterances from this speaker
        keyword_filter: Optional - only get utterances containing this keyword
        preview: If True, return first 5 + last 5 utterances only

    Returns:
        Dict with 'display' containing LLM-ready formatted transcript
    """
    # Batch mode
    if discussion_ids and len(discussion_ids) > 1:
        return _get_batch_transcripts(discussion_ids)

    if discussion_id is None and discussion_ids:
        discussion_id = discussion_ids[0]

    if discussion_id is None:
        return {"display": "Error: discussion_id is required", "error": "missing discussion_id"}

    result = _get_artifacts(discussion_id, include=['transcript'])

    if result.get('error'):
        return {
            "display": f"Error getting transcript: {result.get('error')}",
            "error": result.get('error'),
        }

    artifacts = result.get('artifacts', {})
    transcript = artifacts.get('transcript', {})

    session_name = result.get('session_name', f'Discussion {discussion_id}')
    device_name = result.get('device_name', '')

    utterances = transcript.get('utterances', [])

    # Apply filters if provided
    if speaker_filter:
        speaker_lower = speaker_filter.lower()
        utterances = [
            u for u in utterances
            if speaker_lower in u.get('speaker', '').lower()
        ]

    if keyword_filter:
        keyword_lower = keyword_filter.lower()
        utterances = [
            u for u in utterances
            if keyword_lower in u.get('text', '').lower()
        ]

    # Build LLM-ready text - include device name in title
    title = f"{session_name} ({device_name})" if device_name else session_name
    lines = [
        f"=== Transcript: {title} ===",
        f"Discussion ID: {discussion_id}",
    ]

    if speaker_filter:
        lines.append(f"Filtered by speaker: {speaker_filter}")
    if keyword_filter:
        lines.append(f"Filtered by keyword: {keyword_filter}")

    lines.append(f"Utterances: {len(utterances)}")

    # Preview mode: first 5 + last 5
    if preview and len(utterances) > 10:
        lines.append("(Preview mode: first 5 + last 5 utterances)")
        lines.append("")
        lines.append("--- Begin Transcript Preview ---")
        lines.append("")
        display_utterances = utterances[:5]
        lines.extend(_format_utterances(display_utterances))
        lines.append(f"  ... ({len(utterances) - 10} utterances omitted) ...")
        lines.append("")
        display_utterances = utterances[-5:]
        lines.extend(_format_utterances(display_utterances))
    else:
        lines.append("")
        lines.append("--- Begin Transcript ---")
        lines.append("")
        lines.extend(_format_utterances(utterances))

    lines.append("")
    lines.append("--- End Transcript ---")

    return {
        "display": "\n".join(lines),
        "discussion_id": discussion_id,
        "session_name": session_name,
        "utterance_count": len(utterances),
        "utterances": utterances,  # Structured data for programmatic use
    }


def _format_utterances(utterances: List[Dict]) -> List[str]:
    """Format utterance list into display lines."""
    lines = []
    for u in utterances:
        speaker = u.get('speaker', 'Unknown') or 'Unknown'
        text = u.get('text', '').strip()
        start_time = u.get('start_time', 0) or 0
        minutes = int(start_time // 60)
        seconds = int(start_time % 60)
        timestamp = f"[{minutes:02d}:{seconds:02d}]"
        lines.append(f"{timestamp} {speaker}: {text}")
    return lines


def _get_batch_transcripts(discussion_ids: List[int]) -> Dict[str, Any]:
    """Batch mode: preview of multiple transcripts."""
    lines = [f"=== Transcript Previews ({len(discussion_ids)} sessions) ===", ""]

    for did in discussion_ids:
        result = _get_artifacts(did, include=['transcript'])
        session_name = result.get('session_name', f'Discussion {did}')
        device_name = result.get('device_name', '')
        title = f"{session_name} ({device_name})" if device_name else session_name

        transcript = result.get('artifacts', {}).get('transcript', {})
        utterances = transcript.get('utterances', [])

        # Collect speakers
        speakers = set()
        for u in utterances:
            s = u.get('speaker', 'Unknown') or 'Unknown'
            speakers.add(s)

        # Duration
        duration_sec = 0
        if utterances:
            last = utterances[-1].get('start_time', 0) or 0
            duration_sec = int(last)

        lines.append(f"--- {title} (Discussion {did}) ---")
        lines.append(f"Speakers: {', '.join(sorted(speakers))}")
        lines.append(f"Utterances: {len(utterances)} | Duration: ~{duration_sec // 60}m {duration_sec % 60}s")
        lines.append("")

        # First 5 + last 5
        if len(utterances) > 10:
            lines.extend(_format_utterances(utterances[:5]))
            lines.append(f"  ... ({len(utterances) - 10} utterances omitted) ...")
            lines.extend(_format_utterances(utterances[-5:]))
        else:
            lines.extend(_format_utterances(utterances))

        lines.append("")

    lines.append("For full transcript, use get_transcript(discussion_id=N)")
    lines.append("=== End Previews ===")

    return {
        "display": "\n".join(lines),
        "discussion_ids": discussion_ids,
        "session_count": len(discussion_ids),
    }


# =============================================================================
# Tool 4: get_concept_map
# =============================================================================

@tool_wrapper("get_concept_map")
def get_concept_map(
    discussion_id: Optional[int] = None,
    discussion_ids: Optional[List[int]] = None,
    node_types: Optional[List[str]] = None,
    edge_types: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get concept map for a discussion showing ideas and their connections.

    Single mode: full adjacency list with optional type filters.
    Batch mode: summary (node/edge counts, hub nodes, discourse type) per session.

    Args:
        discussion_id: Discussion to get concept map for
        discussion_ids: Multiple discussions for batch summary
        node_types: Optional filter - only include nodes of these types
        edge_types: Optional filter - only include edges of these types

    Returns:
        Dict with 'display' containing LLM-ready concept map text
    """
    # Batch mode
    if discussion_ids and len(discussion_ids) > 1:
        return _get_batch_concept_maps(discussion_ids)

    if discussion_id is None and discussion_ids:
        discussion_id = discussion_ids[0]

    if discussion_id is None:
        return {"display": "Error: discussion_id is required", "error": "missing discussion_id"}

    result = _get_artifacts(discussion_id, include=['concept_map'])

    if result.get('error'):
        return {
            "display": f"Error getting concept map: {result.get('error')}",
            "error": result.get('error'),
        }

    artifacts = result.get('artifacts', {})
    concept_map = artifacts.get('concept_map', {})

    session_name = result.get('session_name', f'Discussion {discussion_id}')
    device_name = result.get('device_name', '')

    if not concept_map.get('available', False):
        return {
            "display": f"No concept map available for {session_name}",
            "discussion_id": discussion_id,
            "available": False,
        }

    all_nodes = concept_map.get('nodes', [])
    all_edges = concept_map.get('edges', [])
    summary = concept_map.get('summary', {})

    # Scope awareness: what was requested vs what exists (for agent context)
    # Use the generation service's canonical taxonomy as the baseline
    FULL_NODE_TAXONOMY = {'idea', 'question', 'hypothesis', 'example', 'problem',
                          'solution', 'goal', 'uncertainty', 'conclusion', 'action'}
    FULL_EDGE_TAXONOMY = {'supports', 'contrasts_with', 'elaborates', 'builds_on',
                          'challenges', 'exemplifies', 'answers', 'similar_to',
                          'synthesizes', 'relates_to', 'contradicts', 'leads_to'}

    req_node_types = concept_map.get('requested_node_types')  # None = all
    req_edge_types = concept_map.get('requested_edge_types')  # None = all
    requested_nodes = set(req_node_types) if req_node_types else FULL_NODE_TAXONOMY
    requested_edges = set(req_edge_types) if req_edge_types else FULL_EDGE_TAXONOMY

    present_node_types = {(n.get('type', 'concept') or 'concept').lower() for n in all_nodes}
    present_edge_types = {(e.get('relationship', e.get('type', 'relates_to')) or 'relates_to').lower() for e in all_edges}

    excluded_node_types = sorted(FULL_NODE_TAXONOMY - requested_nodes)
    excluded_edge_types = sorted(FULL_EDGE_TAXONOMY - requested_edges)
    not_found_node_types = sorted(requested_nodes - present_node_types)
    not_found_edge_types = sorted(requested_edges - present_edge_types)

    # Apply node type filter — agent param takes precedence; fall back to user's DB selection
    effective_node_types = node_types if node_types is not None else (req_node_types if req_node_types else None)
    effective_edge_types = edge_types if edge_types is not None else (req_edge_types if req_edge_types else None)

    if effective_node_types:
        node_types_lower = [t.lower() for t in effective_node_types]
        nodes = [n for n in all_nodes if (n.get('type', 'concept') or 'concept').lower() in node_types_lower]
    else:
        nodes = all_nodes

    # Build set of included node IDs for edge filtering
    included_node_ids = {n['id'] for n in nodes}

    # Apply edge type filter + ensure both endpoints are in the filtered node set
    if effective_edge_types:
        edge_types_lower = [t.lower() for t in effective_edge_types]
        edges = [
            e for e in all_edges
            if (e.get('relationship', e.get('type', 'relates_to')) or 'relates_to').lower() in edge_types_lower
            and e.get('source') in included_node_ids
            and e.get('target') in included_node_ids
        ]
    else:
        # Even without edge type filter, only include edges where both nodes passed the node filter
        edges = [
            e for e in all_edges
            if e.get('source') in included_node_ids
            and e.get('target') in included_node_ids
        ]

    # Build node lookup by id
    node_lookup = {n['id']: n for n in nodes}

    # Build outgoing edges map
    outgoing = {}
    incoming_set = set()

    for edge in edges:
        source_id = edge.get('source')
        target_id = edge.get('target')
        relationship = edge.get('relationship', edge.get('type', 'relates_to'))

        if source_id not in outgoing:
            outgoing[source_id] = []
        outgoing[source_id].append((relationship, target_id))
        incoming_set.add(target_id)

    def format_node(node_id):
        node = node_lookup.get(node_id)
        if not node:
            return f"[unknown] {node_id}"
        node_type = node.get('type', 'concept')
        speaker = node.get('speaker', 'Unknown')
        text = node.get('text', '')
        return f"[{node_type}] {speaker}: \"{text}\""

    # Build LLM-ready text - include device name in title
    title = f"{session_name} ({device_name})" if device_name else session_name
    lines = [
        f"=== Concept Map: {title} ===",
        f"Discussion ID: {discussion_id}",
    ]

    # Show filter info if filters are active
    if effective_node_types or effective_edge_types:
        lines.append(f"Showing: {len(nodes)}/{len(all_nodes)} nodes, {len(edges)}/{len(all_edges)} edges")
        if effective_node_types:
            lines.append(f"User-selected node types: {', '.join(effective_node_types)}")
        if effective_edge_types:
            lines.append(f"User-selected relation types: {', '.join(effective_edge_types)}")
    else:
        lines.append(f"Total Nodes: {summary.get('total_nodes', len(nodes))}")
        lines.append(f"Total Edges: {summary.get('total_edges', len(edges))}")

    # Scope awareness markers — only when user has customized the type selection
    if excluded_node_types or excluded_edge_types:
        lines.append("")
        active_n = len(requested_nodes)
        active_e = len(requested_edges)
        lines.append(f"[USER-CONFIGURED SCOPE: {active_n} of {len(FULL_NODE_TAXONOMY)} node types, {active_e} of {len(FULL_EDGE_TAXONOMY)} relation types active]")
        if excluded_node_types:
            lines.append(f"[USER-EXCLUDED NODE TYPES: {', '.join(excluded_node_types)}]")
        if excluded_edge_types:
            lines.append(f"[USER-EXCLUDED RELATION TYPES: {', '.join(excluded_edge_types)}]")
    if not_found_node_types or not_found_edge_types:
        not_found_parts = []
        if not_found_node_types:
            not_found_parts.append(f"node types: {', '.join(not_found_node_types)}")
        if not_found_edge_types:
            not_found_parts.append(f"relation types: {', '.join(not_found_edge_types)}")
        lines.append(f"[NOT FOUND: {'; '.join(not_found_parts)} — requested but no instances in this discussion]")

    # Add node types breakdown (from filtered set when filtered)
    if effective_node_types:
        # Recompute from filtered nodes
        filtered_type_counts = {}
        for n in nodes:
            t = n.get('type', 'concept') or 'concept'
            filtered_type_counts[t] = filtered_type_counts.get(t, 0) + 1
        lines.append("")
        lines.append("Node Types (filtered):")
        for ntype, count in filtered_type_counts.items():
            lines.append(f"  {ntype}: {count}")
    else:
        node_type_counts = summary.get('node_types', {})
        if node_type_counts:
            lines.append("")
            lines.append("Node Types:")
            for ntype, count in node_type_counts.items():
                lines.append(f"  {ntype}: {count}")

    # Add speaker contributions with by_type breakdown (only when unfiltered — totals don't match a filtered view)
    if not effective_node_types:
        speaker_contribs = summary.get('speaker_contributions', {})
        if speaker_contribs:
            lines.append("")
            lines.append("Speaker Contributions:")
            for speaker, data in speaker_contribs.items():
                if isinstance(data, dict):
                    total = data.get('total', 0)
                    by_type = data.get('by_type', {})
                    if by_type:
                        type_str = ", ".join(f"{t}: {c}" for t, c in by_type.items())
                        lines.append(f"  {speaker}: {total} concepts ({type_str})")
                    else:
                        lines.append(f"  {speaker}: {total} concepts")
                else:
                    lines.append(f"  {speaker}: {data} concepts")

    lines.append("")
    lines.append("--- Concept Graph (Adjacency List) ---")
    lines.append("")

    # Build adjacency list
    for node in nodes:
        node_id = node['id']
        has_outgoing = node_id in outgoing
        has_incoming = node_id in incoming_set

        if has_outgoing or (not has_outgoing and not has_incoming):
            lines.append(format_node(node_id))

            if has_outgoing:
                for relationship, target_id in outgoing[node_id]:
                    target_str = format_node(target_id)
                    lines.append(f"   - {relationship} -> {target_str}")

            lines.append("")

    lines.append("--- End Concept Map ---")

    return {
        "display": "\n".join(lines),
        "discussion_id": discussion_id,
        "session_name": session_name,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,  # Structured data for programmatic use
        "edges": edges,  # Structured data for programmatic use
        "summary": summary,  # Structured data for programmatic use
        "filters_applied": {
            "node_types": node_types,
            "edge_types": edge_types,
        } if node_types or edge_types else None,
    }


def _get_batch_concept_maps(discussion_ids: List[int]) -> Dict[str, Any]:
    """Batch mode: summary of concept maps across sessions."""
    lines = [f"=== Concept Map Summaries ({len(discussion_ids)} sessions) ===", ""]

    for did in discussion_ids:
        result = _get_artifacts(did, include=['concept_map'])
        session_name = result.get('session_name', f'Discussion {did}')
        device_name = result.get('device_name', '')
        title = f"{session_name} ({device_name})" if device_name else session_name

        cmap = result.get('artifacts', {}).get('concept_map', {})
        if not cmap.get('available', False):
            lines.append(f"{title} (Discussion {did}): No concept map")
            lines.append("")
            continue

        nodes = cmap.get('nodes', [])
        edges = cmap.get('edges', [])
        summary = cmap.get('summary', {})

        # Node type breakdown
        node_types = summary.get('node_types', {})
        type_str = ", ".join(f"{t}: {c}" for t, c in node_types.items()) if node_types else "N/A"

        # Find hub nodes (most connections)
        edge_count_by_node = {}
        for e in edges:
            s, t = e.get('source'), e.get('target')
            edge_count_by_node[s] = edge_count_by_node.get(s, 0) + 1
            edge_count_by_node[t] = edge_count_by_node.get(t, 0) + 1

        node_lookup = {n['id']: n for n in nodes}
        top_hubs = sorted(edge_count_by_node.items(), key=lambda x: x[1], reverse=True)[:3]
        hub_strs = []
        for nid, cnt in top_hubs:
            n = node_lookup.get(nid)
            if n:
                hub_strs.append(f"\"{n.get('text', '')[:40]}\" ({cnt} connections)")

        lines.append(f"--- {title} (Discussion {did}) ---")
        lines.append(f"Nodes: {len(nodes)} | Edges: {len(edges)}")
        lines.append(f"Discourse: {result.get('discourse_type', 'unknown')}")
        lines.append(f"Types: {type_str}")
        if hub_strs:
            lines.append(f"Hub concepts: {'; '.join(hub_strs)}")
        lines.append("")

    lines.append("For full concept map, use get_concept_map(discussion_id=N)")
    lines.append("=== End Summaries ===")

    return {
        "display": "\n".join(lines),
        "discussion_ids": discussion_ids,
        "session_count": len(discussion_ids),
    }


# =============================================================================
# Tool 5: get_collaboration_assessment
# =============================================================================

def _load_dimension_definitions() -> Dict[str, str]:
    """Load dimension definitions from DB schema or fall back to hardcoded."""
    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT dimensions FROM dimension_schema
            WHERE is_default = 1
            LIMIT 1
        """)
        row = cursor.fetchone()
        cursor.close()
        connection.close()

        if row and row.get('dimensions'):
            import json as _json
            dims = row['dimensions']
            if isinstance(dims, str):
                dims = _json.loads(dims)
            return {d['key']: d.get('description', d.get('name', '')) for d in dims}
    except Exception:
        pass
    return SEVEN_C_DEFINITIONS


def _get_analysis_id_for_session(discussion_id: int) -> Optional[int]:
    """Get the latest analysis ID for a session_device."""
    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id FROM seven_cs_analysis
            WHERE session_device_id = %s
            ORDER BY created_at DESC LIMIT 1
        """, (discussion_id,))
        row = cursor.fetchone()
        cursor.close()
        connection.close()
        return row['id'] if row else None
    except Exception:
        return None


@tool_wrapper("get_collaboration_assessment")
def get_collaboration_assessment(
    discussion_id: Optional[int] = None,
    discussion_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Get collaboration assessment with scores and supporting segments.

    Single mode: detailed view with explanations and evidence per dimension.
    Batch mode: compact comparison table (scores per dim per session).

    Args:
        discussion_id: Single discussion to get assessment for
        discussion_ids: Multiple discussions for comparison table

    Returns:
        Dict with 'display' containing LLM-ready collaboration assessment
    """
    # Batch mode: compact comparison
    if discussion_ids and len(discussion_ids) > 1:
        return _get_batch_collaboration(discussion_ids)

    # Single mode (allow discussion_ids with 1 element too)
    if discussion_id is None and discussion_ids:
        discussion_id = discussion_ids[0]

    if discussion_id is None:
        return {"display": "Error: discussion_id is required", "error": "missing discussion_id"}

    result = _get_artifacts(discussion_id, include=['collaboration'])

    if result.get('error'):
        return {
            "display": f"Error getting collaboration assessment: {result.get('error')}",
            "error": result.get('error'),
        }

    artifacts = result.get('artifacts', {})
    collaboration = artifacts.get('collaboration', {})

    session_name = result.get('session_name', f'Discussion {discussion_id}')
    device_name = result.get('device_name', '')

    if not collaboration.get('available', False):
        return {
            "display": f"No collaboration assessment available for {session_name}",
            "discussion_id": discussion_id,
            "available": False,
        }

    raw_dimensions = collaboration.get('dimensions', {})

    # Load dynamic dimension definitions (edits are surfaced via system context, not here)
    dim_definitions = _load_dimension_definitions()

    # Calculate overall score
    scores = [d.get('score', 0) for d in raw_dimensions.values() if d.get('score')]
    overall_score = sum(scores) / len(scores) if scores else 0

    # Build LLM-ready text - include device name in title
    title = f"{session_name} ({device_name})" if device_name else session_name
    dim_count = len(raw_dimensions)
    lines = [
        f"=== Collaboration Assessment: {title} ===",
        f"Discussion ID: {discussion_id}",
        f"Overall Score: {overall_score:.1f}/100",
        "",
        f"Collaboration quality measured across {dim_count} dimensions.",
        "",
    ]

    # Process each dimension with edit annotations
    for dim_name, dim_data in raw_dimensions.items():
        score = dim_data.get('score', 0)
        explanation = dim_data.get('explanation', 'No explanation available')
        definition = dim_definitions.get(dim_name, dim_data.get('definition', ''))

        # Build header with edit annotation if applicable
        # Strong edit (score + text): [EDITED] marker — agent sees the signal internally
        # Light edit (score only): [STALE-EXPLANATION] marker — no strong edit flag
        if dim_data.get('edited'):
            original = dim_data.get('original_ai_score', '?')
            revision_details = []
            if dim_data.get('explanation_updated'):
                revision_details.append("explanation revised")
            if dim_data.get('evidence_updated'):
                revision_details.append("evidence revised")
            detail_str = " and ".join(revision_details) if revision_details else "text revised"
            lines.append(f"--- {dim_name.upper()} ({score}/100) [EDITED: AI original was {original}, {detail_str}] ---")
        else:
            lines.append(f"--- {dim_name.upper()} ({score}/100) ---")

        if definition:
            lines.append(f"Definition: {definition}")
        lines.append(f"Explanation: {explanation}")

        # Stale explanation warning (score-only change — light signal)
        if dim_data.get('stale_explanation'):
            original = dim_data.get('original_ai_score', '?')
            lines.append(f"[STALE-EXPLANATION: score changed from {original} to {score}, but explanation was written for the original score]")

        lines.append("")

    lines.append("=== End Collaboration Assessment ===")

    return {
        "display": "\n".join(lines),
        "discussion_id": discussion_id,
        "session_name": session_name,
        "overall_score": overall_score,
        "dimensions": raw_dimensions,  # Structured data for programmatic use
    }


def _get_batch_collaboration(discussion_ids: List[int]) -> Dict[str, Any]:
    """Batch mode: score + brief explanation per dimension for each session.

    Provides enough context for the agent to answer comparison questions directly
    or decide which sessions to drill into with single-mode calls.
    """
    lines = [f"=== Collaboration Assessment Previews ({len(discussion_ids)} sessions) ===", ""]

    dim_definitions = _load_dimension_definitions()

    for did in discussion_ids:
        result = _get_artifacts(did, include=['collaboration'])
        session_name = result.get('session_name', f'Discussion {did}')
        device_name = result.get('device_name', '')
        title = f"{session_name} ({device_name})" if device_name else session_name

        collab = result.get('artifacts', {}).get('collaboration', {})
        if not collab.get('available', False):
            lines.append(f"--- {title} (Discussion {did}) ---")
            lines.append("  (no assessment available)")
            lines.append("")
            continue

        dims = collab.get('dimensions', {})
        scores = [d.get('score', 0) for d in dims.values() if d.get('score')]
        avg = sum(scores) / len(scores) if scores else 0

        lines.append(f"--- {title} (Discussion {did}) | Avg: {avg:.0f}/100 ---")

        for dim_name, dim_data in dims.items():
            score = dim_data.get('score', 0)
            explanation = dim_data.get('explanation', '')
            # Truncate explanation to ~80 chars for preview
            brief = (explanation[:80] + '...') if len(explanation) > 83 else explanation
            edit_tag = ""
            if dim_data.get('edited'):
                original = dim_data.get('original_ai_score', '?')
                revisions = []
                if dim_data.get('explanation_updated'):
                    revisions.append("explanation revised")
                if dim_data.get('evidence_updated'):
                    revisions.append("evidence revised")
                detail = " + ".join(revisions) if revisions else "text revised"
                edit_tag = f" [EDITED from {original}, {detail}]"
            elif dim_data.get('stale_explanation'):
                original = dim_data.get('original_ai_score', '?')
                edit_tag = f" [STALE-EXPLANATION: score updated from {original}]"
            lines.append(f"  {dim_name}: {score}/100{edit_tag} — {brief}")

        lines.append("")

    lines.append("For full evidence and definitions, use get_collaboration_assessment(discussion_id=N)")
    lines.append("=== End Previews ===")

    return {
        "display": "\n".join(lines),
        "discussion_ids": discussion_ids,
        "session_count": len(discussion_ids),
    }


# =============================================================================
# Tool 6: get_speaker_profile
# =============================================================================

def _get_db_connection():
    """Get database connection (study-aware via study_context)."""
    from study_context import get_db_connection
    return get_db_connection()


@tool_wrapper("get_speaker_profile")
def get_speaker_profile(
    speaker_name: Optional[str] = None,
    speaker_names: Optional[List[str]] = None,
    discussion_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get a speaker's engagement profile across discussions.

    Single mode: detailed profile with quotes, concept contributions, and connections.
    Batch mode: comparative table of key metrics.

    Args:
        speaker_name: Name of the speaker (partial match supported)
        speaker_names: Multiple speakers for comparison table
        discussion_id: Optional - limit to specific discussion (None = all discussions)

    Returns:
        Dict with 'display' containing LLM-ready speaker profile
    """
    # Batch mode
    if speaker_names and len(speaker_names) > 1:
        return _get_batch_speaker_profiles(speaker_names, discussion_id)

    if speaker_name is None and speaker_names:
        speaker_name = speaker_names[0]

    if speaker_name is None:
        return {"display": "Error: speaker_name is required", "error": "missing speaker_name"}
    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Find ALL speaker IDs with this alias (same person has different ID per session)
        cursor.execute("""
            SELECT id, alias, session_device_id FROM speaker WHERE alias LIKE %s
        """, (f"%{speaker_name}%",))
        speakers = cursor.fetchall()

        if not speakers:
            cursor.close()
            connection.close()
            return {
                "display": f"Speaker '{speaker_name}' not found. Use list_sessions to see available speakers.",
                "found": False,
            }

        speaker_ids = [s['id'] for s in speakers]
        speaker_alias = speakers[0]['alias']
        speaker_id_list = ', '.join(str(sid) for sid in speaker_ids)

        # Discussion filters (discussion_id maps to session_device_id internally)
        session_filter = f"AND t.session_device_id = {discussion_id}" if discussion_id else ""
        session_filter_unaliased = f"AND session_device_id = {discussion_id}" if discussion_id else ""

        # Get participation by session (across ALL speaker IDs)
        cursor.execute(f"""
            SELECT
                t.session_device_id,
                COALESCE(s.name, sd.name) as session_name,
                COUNT(*) as utterance_count,
                SUM(t.word_count) as word_count,
                SUM(CASE WHEN t.question = 1 THEN 1 ELSE 0 END) as questions,
                (SELECT COUNT(*) FROM transcript t2 WHERE t2.session_device_id = t.session_device_id) as session_total_utterances,
                (SELECT COUNT(DISTINCT t2.speaker_id) FROM transcript t2 WHERE t2.session_device_id = t.session_device_id) as session_speaker_count
            FROM transcript t
            JOIN session_device sd ON t.session_device_id = sd.id
            JOIN session s ON sd.session_id = s.id
            WHERE t.speaker_id IN ({speaker_id_list}) {session_filter}
            GROUP BY t.session_device_id, s.name, sd.name
        """)
        session_data = cursor.fetchall()

        # Add comparative metrics for LLM to reason about
        for row in session_data:
            utterances = int(row.get('utterance_count') or 0)
            questions = int(row.get('questions') or 0)
            session_total = int(row.get('session_total_utterances') or 1)
            speaker_count = int(row.get('session_speaker_count') or 1)

            row['participation_share_pct'] = round(utterances * 100.0 / session_total, 1) if session_total > 0 else 0
            row['question_rate_pct'] = round(questions * 100.0 / utterances, 1) if utterances > 0 else 0
            row['expected_equal_share_pct'] = round(100.0 / speaker_count, 1) if speaker_count > 0 else 100

        # Get concept contributions (across ALL speaker IDs)
        session_concept_filter = f"AND cs.session_device_id = {discussion_id}" if discussion_id else ""
        cursor.execute(f"""
            SELECT
                cn.node_type,
                cn.text,
                cs.session_device_id
            FROM concept_node cn
            JOIN concept_session cs ON cn.concept_session_id = cs.id
            WHERE cn.speaker_id IN ({speaker_id_list}) {session_concept_filter}
        """)
        concept_nodes = cursor.fetchall()

        # Get connections to other speakers (across ALL speaker IDs)
        cursor.execute(f"""
            SELECT cn.id FROM concept_node cn
            JOIN concept_session cs ON cn.concept_session_id = cs.id
            WHERE cn.speaker_id IN ({speaker_id_list}) {session_concept_filter}
        """)
        node_rows = cursor.fetchall()
        node_ids = [r['id'] for r in node_rows]

        speaker_connections = {}
        if node_ids:
            placeholders = ', '.join(['%s'] * len(node_ids))

            # Outgoing connections (this speaker → others)
            cursor.execute(f"""
                SELECT DISTINCT sp.alias as connected_speaker, ce.edge_type
                FROM concept_edge ce
                JOIN concept_node cn_tgt ON ce.target_node_id = cn_tgt.id
                JOIN speaker sp ON cn_tgt.speaker_id = sp.id
                WHERE ce.source_node_id IN ({placeholders})
                AND sp.alias != %s
            """, node_ids + [speaker_alias])
            outgoing = cursor.fetchall()

            # Incoming connections (others → this speaker)
            cursor.execute(f"""
                SELECT DISTINCT sp.alias as connected_speaker, ce.edge_type
                FROM concept_edge ce
                JOIN concept_node cn_src ON ce.source_node_id = cn_src.id
                JOIN speaker sp ON cn_src.speaker_id = sp.id
                WHERE ce.target_node_id IN ({placeholders})
                AND sp.alias != %s
            """, node_ids + [speaker_alias])
            incoming = cursor.fetchall()

            # Aggregate connections
            for conn in outgoing:
                other = conn['connected_speaker']
                if other not in speaker_connections:
                    speaker_connections[other] = {"outgoing": [], "incoming": []}
                if conn['edge_type'] not in speaker_connections[other]["outgoing"]:
                    speaker_connections[other]["outgoing"].append(conn['edge_type'])

            for conn in incoming:
                other = conn['connected_speaker']
                if other not in speaker_connections:
                    speaker_connections[other] = {"outgoing": [], "incoming": []}
                if conn['edge_type'] not in speaker_connections[other]["incoming"]:
                    speaker_connections[other]["incoming"].append(conn['edge_type'])

        cursor.close()
        connection.close()

        # Build LLM-ready display
        lines = [
            f"=== Speaker Profile: {speaker_alias} ===",
            f"Scope: {'Discussion ' + str(discussion_id) if discussion_id else 'All discussions'}",
            "",
        ]

        # Discussions participated
        total_utterances = sum(d['utterance_count'] for d in session_data)
        total_words = sum(d['word_count'] or 0 for d in session_data)
        total_questions = sum(d['questions'] or 0 for d in session_data)

        lines.append(f"--- Participation Summary ---")
        lines.append(f"Discussions: {len(session_data)}")
        lines.append(f"Total utterances: {total_utterances}")
        lines.append(f"Total words: {total_words}")
        lines.append(f"Questions asked: {total_questions}")
        lines.append("")

        lines.append(f"--- By Discussion (with comparative metrics) ---")
        for sd in session_data:
            lines.append(f"Discussion {sd['session_device_id']}: {sd['session_name']}")
            lines.append(f"  Utterances: {sd['utterance_count']}, Questions: {sd['questions'] or 0}")
            # Comparative metrics for LLM to interpret
            lines.append(f"  Participation: {sd.get('participation_share_pct', 0)}% of session (equal share would be {sd.get('expected_equal_share_pct', 0)}%)")
            lines.append(f"  Question rate: {sd.get('question_rate_pct', 0)}% of their utterances are questions")
        lines.append("")

        # Concept contributions
        concept_by_type = {}
        for cn in concept_nodes:
            t = cn['node_type'] or 'concept'
            if t not in concept_by_type:
                concept_by_type[t] = []
            concept_by_type[t].append(cn['text'] if cn['text'] else '')

        lines.append(f"--- Concept Contributions ({len(concept_nodes)} total) ---")
        for ctype, concepts in concept_by_type.items():
            lines.append(f"{ctype}: {len(concepts)}")
            for c in concepts:  # Show ALL concepts per type
                lines.append(f"  - {c}")
        lines.append("")

        # Speaker connections
        if speaker_connections:
            lines.append(f"--- Interactions with Other Speakers ---")
            for other_speaker, rels in speaker_connections.items():
                out_rels = ", ".join(rels["outgoing"]) if rels["outgoing"] else "none"
                in_rels = ", ".join(rels["incoming"]) if rels["incoming"] else "none"
                lines.append(f"{other_speaker}:")
                lines.append(f"  {speaker_alias} → {other_speaker}: {out_rels}")
                lines.append(f"  {other_speaker} → {speaker_alias}: {in_rels}")
        else:
            lines.append("(No concept-level interactions with other speakers found)")

        lines.append("")
        lines.append("--- Next Steps ---")
        lines.append(f"To see {speaker_alias}'s actual utterances in a discussion, use:")
        lines.append(f"  get_transcript(discussion_id=N, speaker_filter='{speaker_alias}')")
        lines.append("")
        lines.append("=== End Speaker Profile ===")

        return {
            "display": "\n".join(lines),
            "speaker_alias": speaker_alias,
            "speaker_ids": speaker_ids,  # List of all speaker IDs (one per discussion)
            "discussions": [{"discussion_id": d['session_device_id'], "session_name": d['session_name']} for d in session_data],
            "found": True,
        }

    except Exception as e:
        logger.error(f"Speaker profile error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "display": f"Error getting speaker profile: {str(e)}",
            "error": str(e),
        }


def _get_batch_speaker_profiles(speaker_names: List[str], discussion_id: Optional[int] = None) -> Dict[str, Any]:
    """Batch mode: comparative table of speaker metrics."""
    lines = [f"=== Speaker Comparison ({len(speaker_names)} speakers) ==="]
    if discussion_id:
        lines.append(f"Scope: Discussion {discussion_id}")
    else:
        lines.append("Scope: All discussions")
    lines.append("")

    session_filter = f"AND t.session_device_id = {discussion_id}" if discussion_id else ""

    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Header
        header = f"{'Speaker':<20} {'Utts':>5} {'Words':>6} {'Q%':>5} {'Share%':>7}"
        lines.append(header)
        lines.append("-" * len(header))

        for name in speaker_names:
            cursor.execute("SELECT id, alias FROM speaker WHERE alias LIKE %s", (f"%{name}%",))
            speakers = cursor.fetchall()

            if not speakers:
                lines.append(f"{name[:20]:<20}  (not found)")
                continue

            speaker_ids = [s['id'] for s in speakers]
            speaker_alias = speakers[0]['alias']
            speaker_id_list = ', '.join(str(sid) for sid in speaker_ids)

            cursor.execute(f"""
                SELECT
                    COUNT(*) as utterance_count,
                    SUM(t.word_count) as word_count,
                    SUM(CASE WHEN t.question = 1 THEN 1 ELSE 0 END) as questions,
                    (SELECT COUNT(*) FROM transcript t2 WHERE 1=1 {session_filter.replace('t.', 't2.')}) as session_total
                FROM transcript t
                WHERE t.speaker_id IN ({speaker_id_list}) {session_filter}
            """)
            row = cursor.fetchone()

            utts = int(row.get('utterance_count') or 0)
            words = int(row.get('word_count') or 0)
            questions = int(row.get('questions') or 0)
            total = int(row.get('session_total') or 1)
            q_rate = round(questions * 100.0 / utts, 1) if utts > 0 else 0
            share = round(utts * 100.0 / total, 1) if total > 0 else 0

            lines.append(
                f"{speaker_alias[:20]:<20} {utts:>5} {words:>6} {q_rate:>4.1f}% {share:>5.1f}%"
            )

        cursor.close()
        connection.close()

        lines.append("")
        lines.append("For detailed profile, use get_speaker_profile(speaker_name='Name')")
        lines.append("=== End Comparison ===")

        return {
            "display": "\n".join(lines),
            "speaker_names": speaker_names,
        }

    except Exception as e:
        logger.error(f"Batch speaker profile error: {e}")
        return {"display": f"Error: {str(e)}", "error": str(e)}


# =============================================================================
# Tool Registry
# =============================================================================

CORE_TOOLS = {
    "list_sessions": list_sessions,
    "search_sessions": search_sessions,
    "get_transcript": get_transcript,
    "get_concept_map": get_concept_map,
    "get_collaboration_assessment": get_collaboration_assessment,
    "get_speaker_profile": get_speaker_profile,
}


def get_tool(name: str) -> Optional[Callable]:
    """Get a tool by name."""
    return CORE_TOOLS.get(name)


def execute_tool(name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a tool by name with parameters."""
    tool = get_tool(name)
    if not tool:
        return {
            "tool_name": name,
            "display": f"Error: Unknown tool '{name}'",
            "error": f"Unknown tool: {name}",
        }
    return tool(**params)


def get_tool_names() -> List[str]:
    """Get list of all tool names."""
    return list(CORE_TOOLS.keys())


# =============================================================================
# Tool Schema for OpenAI Function Calling
# =============================================================================

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_sessions",
            "description": "List all sessions with collaboration scores (0-100). USE FIRST for superlative/comparison queries (best/worst/compare). Shows scores to identify top candidates, then call get_collaboration_assessment for detailed breakdown.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_sessions",
            "description": "Search sessions by topic using semantic similarity. May miss related sessions - for exhaustive comparison, use list_sessions instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Topic or keyword to search"},
                    "top_k": {"type": "integer", "description": "Max results", "default": 5}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_transcript",
            "description": "Get discussion transcript. Single mode: full transcript with timestamps. Batch mode (discussion_ids): preview (first 5 + last 5 utterances + metadata) per session.",
            "parameters": {
                "type": "object",
                "properties": {
                    "discussion_id": {"type": "integer", "description": "Single discussion ID"},
                    "discussion_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Multiple discussion IDs for batch preview"
                    },
                    "speaker_filter": {"type": "string", "description": "Filter by speaker"},
                    "keyword_filter": {"type": "string", "description": "Filter by keyword"},
                    "preview": {"type": "boolean", "description": "If true, return first 5 + last 5 utterances only", "default": False}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_concept_map",
            "description": "Get concept map with ideas (nodes) and relationships (edges). Single mode: full adjacency list with optional type filters. Batch mode (discussion_ids): summary per session (counts, hub nodes, discourse type).",
            "parameters": {
                "type": "object",
                "properties": {
                    "discussion_id": {"type": "integer", "description": "Single discussion ID"},
                    "discussion_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Multiple discussion IDs for batch summary"
                    },
                    "node_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by node types: idea, question, hypothesis, example, problem, solution, goal, uncertainty, conclusion, action"
                    },
                    "edge_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by edge types: supports, elaborates, builds_on, challenges, contradicts, relates_to, contrasts_with, synthesizes, leads_to"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_collaboration_assessment",
            "description": "Get collaboration assessment. Single mode: detailed scores, explanations per dimension. Batch mode (discussion_ids): score + brief explanation per dimension per session (preview for triage).",
            "parameters": {
                "type": "object",
                "properties": {
                    "discussion_id": {"type": "integer", "description": "Single discussion ID"},
                    "discussion_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Multiple discussion IDs for comparison table"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_speaker_profile",
            "description": "Get speaker engagement profile. Single mode: detailed metrics, quotes, concept contributions. Batch mode (speaker_names): comparative table of key metrics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "speaker_name": {"type": "string", "description": "Speaker name (partial match supported)"},
                    "speaker_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Multiple speaker names for comparison"
                    },
                    "discussion_id": {"type": "integer", "description": "Optional: limit to specific discussion"}
                }
            }
        }
    },
]
