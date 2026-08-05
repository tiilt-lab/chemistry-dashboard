"""
Artifact-Centric Tools for BLINC Agent V3

OPTIMAL 6-TOOL DESIGN
=====================
1. list_sessions       - Discovery: what sessions exist
2. search_for_sessions - Discovery: find sessions by topic
3. get_artifacts       - Retrieve complete artifacts (flexible include param)
4. get_speaker_profile - Complete speaker view with graph connections
5. synthesize          - Cross-rep AND cross-session synthesis
6. find_concept_path   - Graph reasoning (algorithmic traversal)

DESIGN PRINCIPLES
================
- Artifact-centric: Once relevant, provide artifacts FULLY (no fragment search)
- Multi-representation: Three artifact types (Transcript, Concept Map, 7C)
- Cross-rep synthesis: Reason across representations, find convergences/discrepancies
- Tool economy: Minimal set of principled tools (not proliferation)
"""

import logging
import json
import sys
import os
from typing import Dict, Any, List, Optional, Union

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


def _get_db_connection():
    """Get direct MySQL connection."""
    import mysql.connector
    return mysql.connector.connect(
        host='localhost',
        user='vagrant',
        password='vagrant',
        database='discussion_capture'
    )


def _get_rag_service():
    """Lazy import of RAG service."""
    from rag_service import RAGService
    return RAGService()


# =============================================================================
# TOOL 1: list_sessions - Discovery
# =============================================================================

def list_sessions() -> Dict[str, Any]:
    """
    List all available sessions with metadata.

    Use this FIRST to understand what data is available before retrieving artifacts.

    Returns:
        All sessions with: id, name, speakers, discourse_type, artifacts_available
    """
    logger.info("Listing all sessions")

    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                sd.id as session_id,
                COALESCE(s.name, sd.name) as session_name,
                cs.discourse_type,
                (SELECT GROUP_CONCAT(DISTINCT sp.alias)
                 FROM transcript t
                 JOIN speaker sp ON t.speaker_id = sp.id
                 WHERE t.session_device_id = sd.id) as speakers,
                (SELECT COUNT(*) FROM transcript WHERE session_device_id = sd.id) as transcript_count,
                (SELECT COUNT(*) FROM concept_node cn
                 JOIN concept_session ccs ON cn.concept_session_id = ccs.id
                 WHERE ccs.session_device_id = sd.id) as concept_count,
                (SELECT COUNT(*) FROM seven_cs_analysis WHERE session_device_id = sd.id) as has_7c
            FROM session_device sd
            JOIN session s ON s.id = sd.session_id
            LEFT JOIN concept_session cs ON cs.session_device_id = sd.id
            ORDER BY sd.id
        """)

        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "session_id": row['session_id'],
                "session_name": row['session_name'],
                "discourse_type": row['discourse_type'],
                "speakers": row['speakers'].split(',') if row['speakers'] else [],
                "transcript_count": row['transcript_count'] or 0,
                "concept_count": row['concept_count'] or 0,
                "has_collaboration_analysis": bool(row['has_7c']),
                "artifacts_available": {
                    "transcript": row['transcript_count'] > 0,
                    "concept_map": row['concept_count'] > 0,
                    "collaboration": bool(row['has_7c'])
                }
            })

        cursor.close()
        connection.close()

        return {
            "tool_name": "list_sessions",
            "total_sessions": len(sessions),
            "sessions": sessions,
            "is_relevant": len(sessions) > 0,
            "result_count": len(sessions)
        }

    except Exception as e:
        logger.error(f"List sessions error: {e}")
        return {"tool_name": "list_sessions", "error": str(e), "sessions": [], "is_relevant": False}


# =============================================================================
# TOOL 2: search_for_sessions - Semantic Discovery
# =============================================================================

def search_for_sessions(
    query: str,
    top_k: int = 3,
    min_score: float = 0.25
) -> Dict[str, Any]:
    """
    Find sessions relevant to a query using semantic search.

    Use to DISCOVER which sessions are relevant, then use get_artifacts() to retrieve.

    Args:
        query: What to search for
        top_k: Number of sessions to return
        min_score: Minimum similarity score (0-1) to include results. Default 0.25.
                   Raised to reduce false positives. Set to 0 to return all results.

    Returns:
        Ranked list of relevant session IDs with match reasons
    """
    logger.info(f"Searching for sessions matching: '{query}'")

    try:
        rag = _get_rag_service()

        # Search across transcript collection
        results = rag.transcript_collection.query(
            query_texts=[query],
            n_results=top_k * 3  # Get more to dedupe by session and filter
        )

        # Aggregate by session
        session_scores = {}
        if results and results.get('documents'):
            for i, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][i] if results.get('metadatas') else {}
                dist = results['distances'][0][i] if results.get('distances') else 1
                sid = meta.get('session_device_id')
                score = 1 - dist

                if sid and score >= min_score:
                    if sid not in session_scores:
                        # Parse speakers from comma-separated string
                        speakers_str = meta.get('speakers', '')
                        speakers = speakers_str.split(',') if speakers_str else []

                        session_scores[sid] = {
                            "session_id": sid,
                            "session_name": meta.get('session_name', f"Session {sid}"),
                            "device_name": meta.get('device_name'),
                            "speakers": speakers,
                            "best_match_score": score,
                            "match_preview": doc[:200]
                        }
                    else:
                        session_scores[sid]["best_match_score"] = max(
                            session_scores[sid]["best_match_score"],
                            score
                        )

        # Sort by score and take top_k
        ranked = sorted(session_scores.values(), key=lambda x: x['best_match_score'], reverse=True)[:top_k]

        # Build response
        response = {
            "tool_name": "search_for_sessions",
            "query": query,
            "sessions_found": len(ranked),
            "sessions": ranked,
            "is_relevant": len(ranked) > 0,
            "result_count": len(ranked)
        }

        if ranked:
            response["recommendation"] = "Use get_artifacts(session_id, include=[...]) to retrieve full artifacts"
        else:
            response["message"] = "No confident matches found. Try different or more specific keywords."

        return response

    except Exception as e:
        logger.error(f"Session search error: {e}")
        return {"tool_name": "search_for_sessions", "error": str(e), "sessions": [], "is_relevant": False}


# =============================================================================
# TOOL 3: get_artifacts - Flexible Artifact Retrieval
# =============================================================================

def get_artifacts(
    session_id: int,
    include: List[str] = None
) -> Dict[str, Any]:
    """
    Get COMPLETE artifacts for a session.

    This is the primary artifact retrieval tool. Retrieves full artifacts
    (not fragments) for holistic reasoning.

    Args:
        session_id: The session to retrieve artifacts for
        include: Which artifacts to include. Options:
                 - 'transcript': Full transcript with analytic scores
                 - 'concept_map': Complete concept map with nodes, edges, patterns
                 - 'collaboration': 7C analysis with coded segments
                 Default: all three

    Returns:
        Complete artifacts for the specified session
    """
    if include is None:
        include = ['transcript', 'concept_map', 'collaboration']

    logger.info(f"Getting artifacts for session {session_id}: {include}")

    result = {
        "tool_name": "get_artifacts",
        "session_id": session_id,
        "artifacts_requested": include,
        "artifacts": {}
    }

    try:
        # Get session metadata first
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                sd.id as session_id,
                COALESCE(s.name, sd.name) as session_name,
                cs.discourse_type
            FROM session_device sd
            JOIN session s ON s.id = sd.session_id
            LEFT JOIN concept_session cs ON cs.session_device_id = sd.id
            WHERE sd.id = %s
        """, (session_id,))
        session_meta = cursor.fetchone()

        cursor.close()
        connection.close()

        if not session_meta:
            return {
                **result,
                "error": f"Session {session_id} not found",
                "is_relevant": False
            }

        result["session_name"] = session_meta['session_name']
        result["discourse_type"] = session_meta['discourse_type']

        # Retrieve each requested artifact
        if 'transcript' in include:
            result["artifacts"]["transcript"] = _get_transcript_data(session_id)

        if 'concept_map' in include:
            result["artifacts"]["concept_map"] = _get_concept_map_data(session_id)

        if 'collaboration' in include:
            result["artifacts"]["collaboration"] = _get_collaboration_data(session_id)

        result["is_relevant"] = any(
            a.get("available", True) for a in result["artifacts"].values()
        )
        result["result_count"] = 1

        return result

    except Exception as e:
        logger.error(f"Get artifacts error: {e}")
        import traceback
        traceback.print_exc()
        return {**result, "error": str(e), "is_relevant": False}


def _get_transcript_data(session_id: int) -> Dict[str, Any]:
    """Internal: Get complete transcript data."""
    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get speaker statistics
        cursor.execute("""
            SELECT
                sp.id as speaker_id,
                sp.alias,
                COUNT(t.id) as utterance_count,
                SUM(t.word_count) as word_count,
                SUM(CASE WHEN t.question = 1 THEN 1 ELSE 0 END) as questions_asked,
                AVG(t.analytic_thinking_value) as avg_analytic,
                AVG(t.certainty_value) as avg_certainty,
                MIN(t.start_time) as first_utterance,
                MAX(t.start_time) as last_utterance
            FROM transcript t
            JOIN speaker sp ON t.speaker_id = sp.id
            WHERE t.session_device_id = %s
            GROUP BY sp.id, sp.alias
        """, (session_id,))
        speakers = cursor.fetchall()

        # Get all transcript chunks
        cursor.execute("""
            SELECT
                t.id as chunk_id,
                sp.alias as speaker,
                t.transcript as text,
                t.start_time,
                t.word_count,
                t.question as is_question,
                t.analytic_thinking_value,
                t.certainty_value
            FROM transcript t
            JOIN speaker sp ON t.speaker_id = sp.id
            WHERE t.session_device_id = %s
            ORDER BY t.start_time
        """, (session_id,))
        chunks_raw = cursor.fetchall()

        cursor.close()
        connection.close()

        if not chunks_raw:
            return {"available": False, "reason": "No transcripts found"}

        # Format speaker profiles
        speaker_profiles = [{
            "speaker_id": s['speaker_id'],
            "alias": s['alias'],
            "utterance_count": s['utterance_count'],
            "word_count": s['word_count'] or 0,
            "questions_asked": s['questions_asked'] or 0,
            "avg_analytic_thinking": round(float(s['avg_analytic'] or 0), 1),
            "avg_certainty": round(float(s['avg_certainty'] or 0), 1)
        } for s in speakers]

        # Format chunks
        utterances = [{
            "chunk_id": c['chunk_id'],
            "speaker": c['speaker'],
            "text": c['text'],
            "start_time": c['start_time'],
            "word_count": c['word_count'] or 0,
            "is_question": bool(c['is_question']),
            "analytic_thinking": c['analytic_thinking_value'],
            "certainty": c['certainty_value']
        } for c in chunks_raw]

        # Calculate session-level statistics
        total_words = sum(c['word_count'] or 0 for c in chunks_raw)
        total_questions = sum(1 for c in chunks_raw if c['is_question'])
        avg_analytic = sum(c['analytic_thinking_value'] or 0 for c in chunks_raw) / len(chunks_raw) if chunks_raw else 0
        avg_certainty = sum(c['certainty_value'] or 0 for c in chunks_raw) / len(chunks_raw) if chunks_raw else 0

        return {
            "available": True,
            "summary": {
                "total_utterances": len(chunks_raw),
                "total_words": total_words,
                "total_questions": total_questions,
                "speaker_count": len(speakers),
                "session_avg_analytic_thinking": round(avg_analytic, 1),
                "session_avg_certainty": round(avg_certainty, 1)
            },
            "speaker_profiles": speaker_profiles,
            "utterances": utterances
        }

    except Exception as e:
        logger.error(f"Get transcript data error: {e}")
        return {"available": False, "error": str(e)}


def _get_concept_map_data(session_id: int) -> Dict[str, Any]:
    """Internal: Get complete concept map data."""
    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get concept session
        cursor.execute("""
            SELECT id, discourse_type
            FROM concept_session
            WHERE session_device_id = %s
        """, (session_id,))
        cs = cursor.fetchone()

        if not cs:
            cursor.close()
            connection.close()
            return {"available": False, "reason": "No concept map generated"}

        concept_session_id = cs['id']

        # Get ALL nodes
        cursor.execute("""
            SELECT
                cn.id,
                cn.node_type,
                cn.text,
                sp.alias as speaker
            FROM concept_node cn
            LEFT JOIN speaker sp ON cn.speaker_id = sp.id
            WHERE cn.concept_session_id = %s
        """, (concept_session_id,))
        nodes_raw = cursor.fetchall()

        # Get ALL edges
        cursor.execute("""
            SELECT
                ce.id as edge_id,
                ce.source_node_id,
                ce.target_node_id,
                ce.edge_type
            FROM concept_edge ce
            JOIN concept_node cn ON ce.source_node_id = cn.id
            WHERE cn.concept_session_id = %s
        """, (concept_session_id,))
        edges_raw = cursor.fetchall()

        # Get clusters
        cursor.execute("""
            SELECT
                cc.id,
                cc.cluster_name,
                cc.summary,
                cc.node_count
            FROM concept_cluster cc
            WHERE cc.concept_session_id = %s
            ORDER BY cc.node_count DESC
        """, (concept_session_id,))
        clusters_raw = cursor.fetchall()

        cursor.close()
        connection.close()

        # Build summaries
        node_types = {}
        speaker_contributions = {}
        for n in nodes_raw:
            t = n['node_type'] or 'unknown'
            node_types[t] = node_types.get(t, 0) + 1
            speaker = n['speaker'] or 'Unknown'
            if speaker not in speaker_contributions:
                speaker_contributions[speaker] = {"total": 0, "by_type": {}}
            speaker_contributions[speaker]["total"] += 1
            speaker_contributions[speaker]["by_type"][t] = speaker_contributions[speaker]["by_type"].get(t, 0) + 1

        # Format nodes
        nodes = [{
            "id": n['id'],
            "type": n['node_type'],
            "text": n['text'],
            "speaker": n['speaker']
        } for n in nodes_raw]

        # Format edges
        edges = [{
            "edge_id": e['edge_id'],
            "source": e['source_node_id'],
            "target": e['target_node_id'],
            "relationship": e['edge_type']
        } for e in edges_raw]

        # Format clusters
        clusters = [{
            "cluster_id": c['id'],
            "name": c['cluster_name'],
            "summary": c['summary'],
            "node_count": c['node_count']
        } for c in clusters_raw]

        # Identify reasoning patterns
        reasoning_patterns = _identify_reasoning_patterns(nodes, edges)

        # Find hub nodes
        connections_per_node = {}
        for e in edges_raw:
            src = e['source_node_id']
            tgt = e['target_node_id']
            connections_per_node[src] = connections_per_node.get(src, 0) + 1
            connections_per_node[tgt] = connections_per_node.get(tgt, 0) + 1

        hub_nodes = sorted(
            [(nid, count) for nid, count in connections_per_node.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]

        node_map = {n['id']: n for n in nodes}
        hubs = [{
            "node_id": nid,
            "connections": count,
            "text": node_map.get(nid, {}).get('text', '')[:100],
            "type": node_map.get(nid, {}).get('type', '')
        } for nid, count in hub_nodes if nid in node_map]

        return {
            "available": True,
            "summary": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "total_clusters": len(clusters),
                "node_types": node_types,
                "speaker_contributions": speaker_contributions
            },
            "nodes": nodes,
            "edges": edges,
            "clusters": clusters,
            "reasoning_patterns": reasoning_patterns,
            "hub_nodes": hubs
        }

    except Exception as e:
        logger.error(f"Get concept map data error: {e}")
        return {"available": False, "error": str(e)}


def _get_collaboration_data(session_id: int) -> Dict[str, Any]:
    """Internal: Get complete 7C collaboration data."""
    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                analysis_summary,
                total_segments_analyzed,
                llm_model_used,
                created_at
            FROM seven_cs_analysis
            WHERE session_device_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (session_id,))
        row = cursor.fetchone()

        cursor.close()
        connection.close()

        if not row or not row.get('analysis_summary'):
            return {"available": False, "reason": "No 7C analysis available"}

        analysis = row['analysis_summary']
        if isinstance(analysis, str):
            analysis = json.loads(analysis)

        # Build dimension data
        dimension_definitions = {
            "climate": "Psychological safety and supportive atmosphere",
            "communication": "Clarity, active listening, articulation",
            "contribution": "Balanced participation, equal voice",
            "conflict": "Constructive disagreement handling",
            "context": "Shared understanding, common ground",
            "constructive": "Building on others' ideas",
            "compatibility": "Working style alignment"
        }

        dimensions = {}
        total_score = 0

        for dim_name, definition in dimension_definitions.items():
            dim_data = analysis.get(dim_name, {})
            score = dim_data.get('score', 0)
            total_score += score

            dimensions[dim_name] = {
                "score": score,
                "definition": definition,
                "explanation": dim_data.get('explanation', ''),
                "coded_segments": dim_data.get('evidence', []),
                "keywords_detected": dim_data.get('keywords_found', [])
            }

        overall_score = round(total_score / 7, 1)

        # Sort for strengths/weaknesses
        sorted_dims = sorted(dimensions.items(), key=lambda x: x[1]['score'], reverse=True)

        strengths = [{
            "dimension": d[0],
            "score": d[1]['score'],
            "why": d[1]['explanation'][:200] if d[1]['explanation'] else ""
        } for d in sorted_dims[:2]]

        weaknesses = [{
            "dimension": d[0],
            "score": d[1]['score'],
            "why": d[1]['explanation'][:200] if d[1]['explanation'] else ""
        } for d in sorted_dims[-2:] if d[1]['score'] < 70]

        # Generate interpretation
        interpretation = _interpret_collaboration(overall_score, dimensions)

        return {
            "available": True,
            "analysis_metadata": {
                "segments_analyzed": row['total_segments_analyzed'],
                "model_used": row['llm_model_used'],
                "analyzed_at": str(row['created_at'])
            },
            "summary": {
                "overall_score": overall_score,
                "interpretation": interpretation,
                "strengths": strengths,
                "areas_for_improvement": weaknesses
            },
            "dimensions": dimensions
        }

    except Exception as e:
        logger.error(f"Get collaboration data error: {e}")
        return {"available": False, "error": str(e)}


def _interpret_collaboration(overall: float, dimensions: Dict) -> str:
    """Generate natural language interpretation of collaboration quality."""
    if overall >= 80:
        quality = "excellent"
    elif overall >= 70:
        quality = "good"
    elif overall >= 60:
        quality = "moderate"
    else:
        quality = "limited"

    high_dims = [d for d, v in dimensions.items() if v['score'] >= 80]
    low_dims = [d for d, v in dimensions.items() if v['score'] < 50]

    interpretation = f"Overall {quality} collaboration (score: {overall}/100). "
    if high_dims:
        interpretation += f"Strengths in {', '.join(high_dims)}. "
    if low_dims:
        interpretation += f"Areas for improvement: {', '.join(low_dims)}."

    return interpretation


def _identify_reasoning_patterns(nodes: List[Dict], edges: List[Dict]) -> List[Dict]:
    """Identify key reasoning patterns in the concept map."""
    patterns = []

    # Build adjacency
    node_map = {n['id']: n for n in nodes}
    outgoing = {}
    incoming = {}
    for e in edges:
        src = e.get('source')
        tgt = e.get('target')
        if src:
            if src not in outgoing:
                outgoing[src] = []
            outgoing[src].append(e)
        if tgt:
            if tgt not in incoming:
                incoming[tgt] = []
            incoming[tgt].append(e)

    # Find reasoning chains
    for start_node in nodes:
        if start_node['type'] in ('question', 'problem'):
            chain = _trace_chain(start_node['id'], outgoing, node_map, max_depth=5)
            if len(chain) >= 3:
                patterns.append({
                    "pattern_type": "reasoning_chain",
                    "description": f"Chain from {start_node['type']} to {chain[-1]['type']}",
                    "length": len(chain),
                    "path": [{"id": n['id'], "type": n['type'], "text": (n.get('text') or '')[:100]} for n in chain],
                    "speakers_involved": list(set(n['speaker'] for n in chain if n.get('speaker')))
                })

    # Find causal relationships
    causal_edges = [e for e in edges if e.get('relationship') in ('causes', 'leads_to', 'enables', 'results_in')]
    if causal_edges:
        examples = []
        for e in causal_edges[:3]:
            src_node = node_map.get(e['source'], {})
            tgt_node = node_map.get(e['target'], {})
            examples.append({
                "from": (src_node.get('text') or '')[:80],
                "relationship": e['relationship'],
                "to": (tgt_node.get('text') or '')[:80]
            })
        patterns.append({
            "pattern_type": "causal_reasoning",
            "description": f"Found {len(causal_edges)} causal relationships",
            "count": len(causal_edges),
            "examples": examples
        })

    # Find hypothesis-evidence pairs
    hypotheses = [n for n in nodes if n.get('type') == 'hypothesis']
    for h in hypotheses:
        supporting = [e for e in outgoing.get(h['id'], []) if e.get('relationship') in ('supported_by', 'evidence_for')]
        challenging = [e for e in incoming.get(h['id'], []) if e.get('relationship') in ('challenges', 'contradicts')]
        if supporting or challenging:
            patterns.append({
                "pattern_type": "hypothesis_testing",
                "hypothesis": (h.get('text') or '')[:150],
                "supporting_evidence_count": len(supporting),
                "challenging_evidence_count": len(challenging),
                "speaker": h.get('speaker')
            })

    # Find question-answer pairs
    questions = [n for n in nodes if n.get('type') == 'question']
    for q in questions:
        answers = [e for e in outgoing.get(q['id'], []) if e.get('relationship') in ('answered_by', 'response')]
        if answers:
            answer_nodes = [node_map.get(e['target']) for e in answers if e['target'] in node_map]
            patterns.append({
                "pattern_type": "question_answer",
                "question": (q.get('text') or '')[:100],
                "answer_count": len(answers),
                "answerers": list(set(a.get('speaker') for a in answer_nodes if a and a.get('speaker')))
            })

    return patterns[:15]


def _trace_chain(node_id: int, outgoing: Dict, node_map: Dict, max_depth: int, visited=None) -> List[Dict]:
    """Trace a reasoning chain from a starting node."""
    if visited is None:
        visited = set()

    if node_id in visited or max_depth == 0:
        return []

    visited.add(node_id)
    node = node_map.get(node_id)
    if not node:
        return []

    chain = [node]

    if node_id in outgoing:
        for edge in outgoing[node_id]:
            target = edge.get('target')
            if target:
                rest = _trace_chain(target, outgoing, node_map, max_depth - 1, visited)
                if rest:
                    chain.extend(rest)
                    break

    return chain


# =============================================================================
# TOOL 4: get_speaker_profile - Speaker Analysis with Graph Connections
# =============================================================================

def get_speaker_profile(
    speaker_name: str,
    session_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get complete profile for a speaker across all representations.

    Aggregates speaker data across artifact types:
    - Transcript: utterances, word counts, questions, analytic/certainty scores
    - Concept Map: contributed concepts AND their connections (edges)
    - Cross-session view if no session_id specified

    Args:
        speaker_name: Name of the speaker
        session_id: Optional - limit to specific session (None = all sessions)

    Returns:
        Complete speaker picture with concept graph connections
    """
    logger.info(f"Getting speaker profile for: {speaker_name}")

    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Find speaker
        cursor.execute("""
            SELECT id, alias FROM speaker WHERE alias LIKE %s LIMIT 1
        """, (f"%{speaker_name}%",))
        speaker = cursor.fetchone()

        if not speaker:
            cursor.close()
            connection.close()
            return {
                "tool_name": "get_speaker_profile",
                "error": f"Speaker '{speaker_name}' not found",
                "is_relevant": False
            }

        speaker_id = speaker['id']
        speaker_alias = speaker['alias']

        session_filter = f"AND t.session_device_id = {session_id}" if session_id else ""

        # Transcript data
        cursor.execute(f"""
            SELECT
                t.session_device_id,
                COALESCE(s.name, sd.name) as session_name,
                COUNT(*) as utterance_count,
                SUM(t.word_count) as word_count,
                SUM(CASE WHEN t.question = 1 THEN 1 ELSE 0 END) as questions,
                AVG(t.analytic_thinking_value) as avg_analytic,
                AVG(t.certainty_value) as avg_certainty
            FROM transcript t
            JOIN session_device sd ON t.session_device_id = sd.id
            JOIN session s ON sd.session_id = s.id
            WHERE t.speaker_id = %s {session_filter}
            GROUP BY t.session_device_id, s.name, sd.name
        """, (speaker_id,))
        transcript_data = cursor.fetchall()

        # Sample quotes
        cursor.execute(f"""
            SELECT
                t.transcript as text,
                t.session_device_id,
                t.start_time,
                t.word_count,
                t.analytic_thinking_value,
                t.certainty_value,
                t.question as is_question
            FROM transcript t
            WHERE t.speaker_id = %s {session_filter}
            AND t.word_count > 15
            ORDER BY t.word_count DESC
            LIMIT 5
        """, (speaker_id,))
        sample_quotes = cursor.fetchall()

        # Concept data
        session_concept_filter = f"AND cs.session_device_id = {session_id}" if session_id else ""
        cursor.execute(f"""
            SELECT
                cn.id as node_id,
                cn.node_type,
                cn.text,
                cs.session_device_id
            FROM concept_node cn
            JOIN concept_session cs ON cn.concept_session_id = cs.id
            WHERE cn.speaker_id = %s {session_concept_filter}
        """, (speaker_id,))
        concept_nodes = cursor.fetchall()

        # Get concept edges (connections)
        node_ids = [n['node_id'] for n in concept_nodes]
        concept_edges = {"outgoing": [], "incoming": []}

        if node_ids:
            placeholders = ', '.join(['%s'] * len(node_ids))

            # Outgoing edges
            cursor.execute(f"""
                SELECT
                    ce.source_node_id,
                    ce.target_node_id,
                    ce.edge_type,
                    cn_src.text as source_text,
                    cn_tgt.text as target_text,
                    sp_tgt.alias as connected_to_speaker
                FROM concept_edge ce
                JOIN concept_node cn_src ON ce.source_node_id = cn_src.id
                JOIN concept_node cn_tgt ON ce.target_node_id = cn_tgt.id
                LEFT JOIN speaker sp_tgt ON cn_tgt.speaker_id = sp_tgt.id
                WHERE ce.source_node_id IN ({placeholders})
            """, node_ids)
            outgoing_edges = cursor.fetchall()

            # Incoming edges
            cursor.execute(f"""
                SELECT
                    ce.source_node_id,
                    ce.target_node_id,
                    ce.edge_type,
                    cn_src.text as source_text,
                    cn_tgt.text as target_text,
                    sp_src.alias as connected_from_speaker
                FROM concept_edge ce
                JOIN concept_node cn_src ON ce.source_node_id = cn_src.id
                JOIN concept_node cn_tgt ON ce.target_node_id = cn_tgt.id
                LEFT JOIN speaker sp_src ON cn_src.speaker_id = sp_src.id
                WHERE ce.target_node_id IN ({placeholders})
            """, node_ids)
            incoming_edges = cursor.fetchall()

            concept_edges = {
                "outgoing": [{
                    "from_text": (e['source_text'] or '')[:100],
                    "relationship": e['edge_type'],
                    "to_text": (e['target_text'] or '')[:100],
                    "connected_to": e['connected_to_speaker']
                } for e in outgoing_edges],
                "incoming": [{
                    "to_text": (e['target_text'] or '')[:100],
                    "relationship": e['edge_type'],
                    "from_text": (e['source_text'] or '')[:100],
                    "connected_from": e['connected_from_speaker']
                } for e in incoming_edges]
            }

        # Aggregate by concept type
        concept_by_type = {}
        for n in concept_nodes:
            t = n['node_type'] or 'unknown'
            if t not in concept_by_type:
                concept_by_type[t] = {"count": 0, "examples": []}
            concept_by_type[t]["count"] += 1
            if len(concept_by_type[t]["examples"]) < 3:
                concept_by_type[t]["examples"].append(n['text'][:150] if n['text'] else "")

        cursor.close()
        connection.close()

        return {
            "tool_name": "get_speaker_profile",
            "speaker_alias": speaker_alias,
            "speaker_id": speaker_id,
            "session_scope": session_id if session_id else "all sessions",

            "transcript_summary": {
                "sessions_participated": len(transcript_data),
                "participation_by_session": [{
                    "session_id": d['session_device_id'],
                    "session_name": d['session_name'],
                    "utterances": d['utterance_count'],
                    "words": d['word_count'] or 0,
                    "questions_asked": d['questions'] or 0,
                    "avg_analytic_thinking": round(float(d['avg_analytic'] or 0), 1),
                    "avg_certainty": round(float(d['avg_certainty'] or 0), 1)
                } for d in transcript_data],
                "sample_quotes": [{
                    "text": q['text'][:300] if q['text'] else "",
                    "session_id": q['session_device_id'],
                    "is_question": bool(q['is_question']),
                    "analytic_thinking": q['analytic_thinking_value'],
                    "certainty": q['certainty_value']
                } for q in sample_quotes]
            },

            "concept_summary": {
                "total_concepts_contributed": len(concept_nodes),
                "contribution_by_type": concept_by_type,
                "connections": concept_edges,
                "interaction_summary": {
                    "outgoing_connections": len(concept_edges.get('outgoing', [])),
                    "incoming_connections": len(concept_edges.get('incoming', [])),
                    "speakers_connected_to": list(set(
                        e.get('connected_to') for e in concept_edges.get('outgoing', [])
                        if e.get('connected_to')
                    )),
                    "speakers_connected_from": list(set(
                        e.get('connected_from') for e in concept_edges.get('incoming', [])
                        if e.get('connected_from')
                    ))
                }
            },

            "is_relevant": True,
            "result_count": 1
        }

    except Exception as e:
        logger.error(f"Speaker profile error: {e}")
        import traceback
        traceback.print_exc()
        return {"tool_name": "get_speaker_profile", "error": str(e), "is_relevant": False}


# =============================================================================
# TOOL 5: synthesize - Cross-Rep AND Cross-Session Synthesis
# =============================================================================

def synthesize(
    session_ids: Union[int, List[int]],
    question: str,
    focus: Optional[str] = None
) -> Dict[str, Any]:
    """
    Synthesize insights across representations AND/OR across sessions.

    THE KEY TOOL for holistic reasoning. Supports:
    1. Single-session cross-rep synthesis (reason across transcript, concept map, 7C)
    2. Multi-session synthesis (compare/contrast across sessions)
    3. Multi-session cross-rep synthesis (both)

    Use when you need to:
    - Reason ACROSS representations holistically
    - Compare patterns across multiple sessions
    - Find convergences (same insight in multiple sources)
    - Surface discrepancies (conflicting signals)

    Args:
        session_ids: Single session ID or list of session IDs
        question: The question/focus for synthesis
        focus: Optional focus (speaker name, topic)

    Returns:
        Cross-representation synthesis with citations from each layer
    """
    # Normalize to list
    if isinstance(session_ids, int):
        session_ids = [session_ids]

    logger.info(f"Synthesizing across sessions {session_ids}: '{question}'")

    try:
        synthesis = {
            "tool_name": "synthesize",
            "session_ids": session_ids,
            "question": question,
            "focus": focus,
            "synthesis_type": "single_session" if len(session_ids) == 1 else "cross_session",
            "sessions_analyzed": [],
            "cross_rep_insights": {},
            "cross_session_patterns": {} if len(session_ids) > 1 else None,
            "citations": [],
            "integrated_summary": ""
        }

        # Analyze each session
        for sid in session_ids:
            session_analysis = _analyze_session_for_synthesis(sid, question, focus)
            synthesis["sessions_analyzed"].append(session_analysis)
            synthesis["citations"].extend(session_analysis.get("citations", []))

        # If single session, structure as cross-rep analysis
        if len(session_ids) == 1:
            sa = synthesis["sessions_analyzed"][0]
            synthesis["cross_rep_insights"] = {
                "from_transcript": sa.get("insights", {}).get("transcript", []),
                "from_concept_map": sa.get("insights", {}).get("concept_map", []),
                "from_collaboration": sa.get("insights", {}).get("collaboration", []),
                "convergences": sa.get("cross_rep_patterns", {}).get("convergences", []),
                "complementary": sa.get("cross_rep_patterns", {}).get("complementary", []),
                "discrepancies": sa.get("cross_rep_patterns", {}).get("discrepancies", [])
            }

        # If multiple sessions, do cross-session comparison
        if len(session_ids) > 1:
            synthesis["cross_session_patterns"] = _analyze_cross_session_patterns(
                synthesis["sessions_analyzed"],
                question
            )

        # Build integrated summary
        synthesis["integrated_summary"] = _build_synthesis_summary(synthesis)

        synthesis["is_relevant"] = len(synthesis["sessions_analyzed"]) > 0
        synthesis["result_count"] = len(synthesis["sessions_analyzed"])

        return synthesis

    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        import traceback
        traceback.print_exc()
        return {"tool_name": "synthesize", "error": str(e), "is_relevant": False}


def _analyze_session_for_synthesis(session_id: int, question: str, focus: Optional[str]) -> Dict[str, Any]:
    """Analyze a single session for synthesis."""
    # Get all artifacts
    artifacts = get_artifacts(session_id, include=['transcript', 'concept_map', 'collaboration'])

    analysis = {
        "session_id": session_id,
        "session_name": artifacts.get("session_name", f"Session {session_id}"),
        "representations_available": [],
        "insights": {
            "transcript": [],
            "concept_map": [],
            "collaboration": []
        },
        "cross_rep_patterns": {
            "convergences": [],
            "complementary": [],
            "discrepancies": []
        },
        "citations": []
    }

    transcript_data = artifacts.get("artifacts", {}).get("transcript", {})
    concept_data = artifacts.get("artifacts", {}).get("concept_map", {})
    collab_data = artifacts.get("artifacts", {}).get("collaboration", {})

    # Extract transcript insights
    if transcript_data.get("available"):
        analysis["representations_available"].append("transcript")
        t_insights = _extract_transcript_insights(transcript_data, question, focus)
        analysis["insights"]["transcript"] = t_insights["insights"]
        analysis["citations"].extend([{**c, "session_id": session_id} for c in t_insights["citations"]])

    # Extract concept map insights
    if concept_data.get("available"):
        analysis["representations_available"].append("concept_map")
        c_insights = _extract_concept_insights(concept_data, question, focus)
        analysis["insights"]["concept_map"] = c_insights["insights"]
        analysis["citations"].extend([{**c, "session_id": session_id} for c in c_insights["citations"]])

    # Extract collaboration insights
    if collab_data.get("available"):
        analysis["representations_available"].append("collaboration")
        col_insights = _extract_collab_insights(collab_data, question, focus)
        analysis["insights"]["collaboration"] = col_insights["insights"]
        analysis["citations"].extend([{**c, "session_id": session_id} for c in col_insights["citations"]])

    # Analyze cross-rep patterns within this session
    analysis["cross_rep_patterns"] = _find_within_session_patterns(
        analysis["insights"],
        transcript_data, concept_data, collab_data
    )

    return analysis


def _extract_transcript_insights(transcript: Dict, question: str, focus: Optional[str]) -> Dict:
    """Extract relevant insights from transcript artifact."""
    insights = []
    citations = []

    summary = transcript.get("summary", {})
    speaker_profiles = transcript.get("speaker_profiles", [])
    utterances = transcript.get("utterances", [])

    # Participation pattern
    if speaker_profiles:
        top = max(speaker_profiles, key=lambda x: x.get('utterance_count', 0))
        insights.append({
            "type": "participation",
            "finding": f"{top['alias']} most active ({top['utterance_count']} utterances)",
            "data": {"speaker": top['alias'], "count": top['utterance_count']}
        })

    # Question-asking
    total_q = summary.get("total_questions", 0)
    if total_q > 0:
        insights.append({
            "type": "inquiry",
            "finding": f"{total_q} questions asked",
            "data": {"question_count": total_q}
        })

    # Analytic thinking
    avg_at = summary.get("session_avg_analytic_thinking", 0)
    if avg_at > 20:
        insights.append({
            "type": "thinking_depth",
            "finding": f"Session avg analytic thinking: {avg_at}",
            "data": {"avg_analytic": avg_at}
        })

    # Find relevant quotes for citations
    query_words = [w for w in (focus or question).lower().split() if len(w) > 3][:5]
    for utt in utterances[:50]:
        text = (utt.get('text') or '').lower()
        if any(w in text for w in query_words):
            citations.append({
                "rep": "transcript",
                "speaker": utt.get('speaker'),
                "text": utt.get('text', '')[:200],
                "timestamp": utt.get('start_time')
            })
            if len(citations) >= 3:
                break

    # FALLBACK: If no keyword matches, include substantive utterances
    if not citations and utterances:
        # Pick top utterances by word count (most substantive)
        sorted_utts = sorted(
            [u for u in utterances if (u.get('word_count') or 0) > 10],
            key=lambda x: x.get('word_count', 0),
            reverse=True
        )[:2]
        for utt in sorted_utts:
            citations.append({
                "rep": "transcript",
                "speaker": utt.get('speaker'),
                "text": utt.get('text', '')[:200],
                "timestamp": utt.get('start_time'),
                "note": "substantive utterance (fallback)"
            })

    return {"insights": insights, "citations": citations}


def _extract_concept_insights(concept_map: Dict, question: str, focus: Optional[str]) -> Dict:
    """Extract relevant insights from concept map artifact."""
    insights = []
    citations = []

    summary = concept_map.get("summary", {})
    nodes = concept_map.get("nodes", [])
    patterns = concept_map.get("reasoning_patterns", [])
    hubs = concept_map.get("hub_nodes", [])
    contributions = summary.get("speaker_contributions", {})

    # Discourse structure
    node_types = summary.get("node_types", {})
    if node_types:
        dominant = max(node_types.items(), key=lambda x: x[1])
        insights.append({
            "type": "structure",
            "finding": f"Dominated by {dominant[0]}s ({dominant[1]} nodes)",
            "data": node_types
        })

    # Reasoning patterns
    if patterns:
        types = list(set(p.get("pattern_type") for p in patterns))[:3]
        insights.append({
            "type": "reasoning",
            "finding": f"Patterns found: {', '.join(types)}",
            "data": {"pattern_count": len(patterns), "types": types}
        })

    # Central ideas
    if hubs:
        insights.append({
            "type": "central_ideas",
            "finding": f"Central: {hubs[0].get('text', '')[:50]}",
            "data": {"hub_count": len(hubs)}
        })

    # Contribution
    if contributions:
        top = max(contributions.items(), key=lambda x: x[1].get('total', 0))
        insights.append({
            "type": "contribution",
            "finding": f"{top[0]} contributed {top[1].get('total', 0)} concepts",
            "data": {"top_contributor": top[0], "count": top[1].get('total', 0)}
        })

    # Find relevant concepts for citations
    query_words = [w for w in (focus or question).lower().split() if len(w) > 3][:5]
    for node in nodes[:30]:
        text = (node.get('text') or '').lower()
        if any(w in text for w in query_words):
            citations.append({
                "rep": "concept_map",
                "type": node.get('type'),
                "text": node.get('text', ''),
                "speaker": node.get('speaker')
            })
            if len(citations) >= 3:
                break

    # FALLBACK: If no keyword matches, include hub nodes as citations
    if not citations:
        for hub in hubs[:2]:
            citations.append({
                "rep": "concept_map",
                "type": hub.get('type'),
                "text": hub.get('text', ''),
                "connections": hub.get('connections'),
                "note": "central concept (fallback)"
            })

    return {"insights": insights, "citations": citations}


def _extract_collab_insights(collaboration: Dict, question: str, focus: Optional[str]) -> Dict:
    """Extract relevant insights from 7C collaboration artifact."""
    insights = []
    citations = []

    summary = collaboration.get("summary", {})
    dimensions = collaboration.get("dimensions", {})

    # Overall quality
    overall = summary.get("overall_score", 0)
    interp = summary.get("interpretation", "")
    if overall > 0:
        insights.append({
            "type": "quality",
            "finding": interp,
            "data": {"overall_score": overall}
        })

    # Strengths
    strengths = summary.get("strengths", [])
    if strengths:
        names = [s.get('dimension') for s in strengths]
        insights.append({
            "type": "strengths",
            "finding": f"Strong in: {', '.join(names)}",
            "data": {"strengths": names}
        })

    # Weaknesses
    weak = summary.get("areas_for_improvement", [])
    if weak:
        names = [w.get('dimension') for w in weak]
        insights.append({
            "type": "improvement",
            "finding": f"Could improve: {', '.join(names)}",
            "data": {"weaknesses": names}
        })

    # Add coded segment citations
    for dim, data in list(dimensions.items())[:4]:
        segments = data.get("coded_segments", [])
        if segments and isinstance(segments[0], str):
            citations.append({
                "rep": "7c_analysis",
                "dimension": dim,
                "score": data.get("score"),
                "evidence": segments[0][:150]
            })

    return {"insights": insights, "citations": citations}


def _find_within_session_patterns(insights: Dict, transcript: Dict, concept_map: Dict, collaboration: Dict) -> Dict:
    """Find cross-representation patterns within a single session."""
    convergences = []
    complementary = []
    discrepancies = []

    t_insights = insights.get("transcript", [])
    c_insights = insights.get("concept_map", [])
    col_insights = insights.get("collaboration", [])

    # Check participation convergence
    t_part = next((i for i in t_insights if i.get("type") == "participation"), None)
    c_contrib = next((i for i in c_insights if i.get("type") == "contribution"), None)

    if t_part and c_contrib:
        t_speaker = t_part.get("data", {}).get("speaker", "")
        c_speaker = c_contrib.get("data", {}).get("top_contributor", "")
        if t_speaker and c_speaker and t_speaker.lower() == c_speaker.lower():
            convergences.append({
                "pattern": "dominance_convergence",
                "finding": f"{t_speaker} dominates both verbally and conceptually",
                "reps": ["transcript", "concept_map"]
            })

    # Quality-quantity relationship
    collab_summary = collaboration.get("summary", {}) if collaboration.get("available") else {}
    concept_summary = concept_map.get("summary", {}) if concept_map.get("available") else {}
    overall = collab_summary.get("overall_score", 0)
    nodes = concept_summary.get("total_nodes", 0)

    if overall >= 75 and nodes >= 10:
        convergences.append({
            "pattern": "productive",
            "finding": f"Good collaboration ({overall}) + substantial output ({nodes} concepts)",
            "reps": ["collaboration", "concept_map"]
        })
    elif overall > 0 and overall < 60 and nodes > 15:
        discrepancies.append({
            "pattern": "process_product_gap",
            "finding": f"Many ideas ({nodes}) despite collaboration challenges ({overall})",
            "interpretation": "Individual contribution may outweigh collaboration"
        })

    # Complementary views
    if t_insights and c_insights:
        complementary.append({
            "pattern": "content_structure",
            "value": "Transcript shows WHAT was said; concept map shows HOW ideas connect"
        })

    if col_insights:
        complementary.append({
            "pattern": "process_product",
            "value": "7C shows collaboration PROCESS; concept map shows idea PRODUCT"
        })

    return {"convergences": convergences, "complementary": complementary, "discrepancies": discrepancies}


def _analyze_cross_session_patterns(sessions_analyzed: List[Dict], question: str) -> Dict:
    """Analyze patterns across multiple sessions."""
    patterns = {
        "similarities": [],
        "differences": [],
        "best_performing": None,
        "insights_by_theme": {}
    }

    if len(sessions_analyzed) < 2:
        return patterns

    # Compare collaboration scores
    collab_scores = []
    for sa in sessions_analyzed:
        for insight in sa.get("insights", {}).get("collaboration", []):
            if insight.get("type") == "quality":
                collab_scores.append({
                    "session_id": sa["session_id"],
                    "session_name": sa["session_name"],
                    "score": insight.get("data", {}).get("overall_score", 0)
                })

    if len(collab_scores) >= 2:
        sorted_scores = sorted(collab_scores, key=lambda x: x["score"], reverse=True)
        patterns["best_performing"] = {
            "metric": "collaboration_score",
            "session": sorted_scores[0]["session_name"],
            "score": sorted_scores[0]["score"]
        }

        score_range = sorted_scores[0]["score"] - sorted_scores[-1]["score"]
        if score_range < 10:
            patterns["similarities"].append({
                "type": "collaboration_quality",
                "finding": f"Similar collaboration quality across sessions (range: {score_range})"
            })
        else:
            patterns["differences"].append({
                "type": "collaboration_quality",
                "finding": f"Significant collaboration variation (range: {score_range})",
                "best": sorted_scores[0]["session_name"],
                "worst": sorted_scores[-1]["session_name"]
            })

    # Compare concept counts
    concept_counts = []
    for sa in sessions_analyzed:
        for insight in sa.get("insights", {}).get("concept_map", []):
            if insight.get("type") == "structure":
                concept_counts.append({
                    "session_id": sa["session_id"],
                    "session_name": sa["session_name"],
                    "data": insight.get("data", {})
                })

    if concept_counts:
        # Find common dominant node types
        dominant_types = [c["data"].get(max(c["data"], key=c["data"].get)) if c["data"] else None for c in concept_counts]
        if len(set(t for t in dominant_types if t)) == 1:
            patterns["similarities"].append({
                "type": "discourse_structure",
                "finding": f"All sessions dominated by similar concept types"
            })

    # Group insights by theme
    for sa in sessions_analyzed:
        for rep_name, rep_insights in sa.get("insights", {}).items():
            for insight in rep_insights:
                theme = insight.get("type", "other")
                if theme not in patterns["insights_by_theme"]:
                    patterns["insights_by_theme"][theme] = []
                patterns["insights_by_theme"][theme].append({
                    "session": sa["session_name"],
                    "rep": rep_name,
                    "finding": insight.get("finding")
                })

    return patterns


def _build_synthesis_summary(synthesis: Dict) -> str:
    """Build integrated summary from synthesis."""
    parts = []

    sessions = synthesis.get("sessions_analyzed", [])
    if not sessions:
        return "No sessions available for synthesis."

    synthesis_type = synthesis.get("synthesis_type", "single_session")

    if synthesis_type == "single_session":
        sa = sessions[0]
        parts.append(f"Cross-representation synthesis for {sa['session_name']}:")

        # Key insights from each rep
        for rep_key, rep_insights in synthesis.get("cross_rep_insights", {}).items():
            if rep_key in ["convergences", "complementary", "discrepancies"]:
                continue
            if rep_insights:
                rep_name = rep_key.replace("from_", "").replace("_", " ").title()
                finding = rep_insights[0].get("finding", "") if rep_insights else ""
                if finding:
                    parts.append(f"  {rep_name}: {finding}")

        # Cross-rep patterns
        convs = synthesis.get("cross_rep_insights", {}).get("convergences", [])
        discs = synthesis.get("cross_rep_insights", {}).get("discrepancies", [])
        if convs:
            parts.append(f"\nConverging: {convs[0].get('finding', '')}")
        if discs:
            parts.append(f"Discrepancy: {discs[0].get('finding', '')} - {discs[0].get('interpretation', '')}")

    else:  # cross_session
        session_names = [sa['session_name'] for sa in sessions]
        parts.append(f"Cross-session synthesis comparing: {', '.join(session_names)}")

        cross_patterns = synthesis.get("cross_session_patterns", {})

        if cross_patterns.get("best_performing"):
            bp = cross_patterns["best_performing"]
            parts.append(f"\nBest {bp['metric']}: {bp['session']} ({bp['score']})")

        if cross_patterns.get("similarities"):
            for sim in cross_patterns["similarities"][:2]:
                parts.append(f"Similar: {sim['finding']}")

        if cross_patterns.get("differences"):
            for diff in cross_patterns["differences"][:2]:
                parts.append(f"Different: {diff['finding']}")

    return "\n".join(parts)


# =============================================================================
# TOOL 6: find_concept_path - Graph Reasoning
# =============================================================================

def find_concept_path(
    session_id: int,
    from_concept: str,
    to_concept: str,
    max_depth: int = 5
) -> Dict[str, Any]:
    """
    Find reasoning path between two concepts in a session's concept map.

    Use AFTER getting artifacts when you need to trace how one idea led to another.
    This tool performs BFS graph traversal that would be difficult mentally.

    Args:
        session_id: The session to search in
        from_concept: Text of the starting concept (fuzzy matched)
        to_concept: Text of the target concept (fuzzy matched)
        max_depth: Maximum path length (default 5)

    Returns:
        The reasoning path showing how concepts connect, with relationship types
    """
    logger.info(f"Finding path in session {session_id}: '{from_concept}' -> '{to_concept}'")

    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get concept session
        cursor.execute("""
            SELECT id FROM concept_session WHERE session_device_id = %s
        """, (session_id,))
        cs = cursor.fetchone()

        if not cs:
            cursor.close()
            connection.close()
            return {
                "tool_name": "find_concept_path",
                "error": f"No concept map for session {session_id}",
                "is_relevant": False
            }

        concept_session_id = cs['id']

        # Find source node
        cursor.execute("""
            SELECT id, text, node_type, speaker_id
            FROM concept_node
            WHERE concept_session_id = %s
            AND text LIKE %s
            ORDER BY LENGTH(text)
            LIMIT 1
        """, (concept_session_id, f"%{from_concept}%"))
        source_node = cursor.fetchone()

        if not source_node:
            cursor.close()
            connection.close()
            return {
                "tool_name": "find_concept_path",
                "error": f"Source concept '{from_concept}' not found",
                "suggestion": "Check the concept map in get_artifacts() for exact concept text",
                "is_relevant": False
            }

        # Find target node
        cursor.execute("""
            SELECT id, text, node_type, speaker_id
            FROM concept_node
            WHERE concept_session_id = %s
            AND text LIKE %s
            ORDER BY LENGTH(text)
            LIMIT 1
        """, (concept_session_id, f"%{to_concept}%"))
        target_node = cursor.fetchone()

        if not target_node:
            cursor.close()
            connection.close()
            return {
                "tool_name": "find_concept_path",
                "error": f"Target concept '{to_concept}' not found",
                "suggestion": "Check the concept map in get_artifacts() for exact concept text",
                "is_relevant": False
            }

        source_id = source_node['id']
        target_id = target_node['id']

        # Get all edges for BFS
        cursor.execute("""
            SELECT source_node_id, target_node_id, edge_type
            FROM concept_edge ce
            JOIN concept_node cn ON ce.source_node_id = cn.id
            WHERE cn.concept_session_id = %s
        """, (concept_session_id,))
        all_edges = cursor.fetchall()

        # Build adjacency list
        adjacency = {}
        for edge in all_edges:
            src = edge['source_node_id']
            if src not in adjacency:
                adjacency[src] = []
            adjacency[src].append({
                'target': edge['target_node_id'],
                'type': edge['edge_type']
            })

        # BFS to find shortest path
        from collections import deque

        visited = {source_id}
        queue = deque([(source_id, [])])
        path_found = None

        while queue and not path_found:
            current_id, path = queue.popleft()

            if len(path) >= max_depth:
                continue

            for edge in adjacency.get(current_id, []):
                next_id = edge['target']
                edge_type = edge['type']

                new_step = {
                    'from_id': current_id,
                    'to_id': next_id,
                    'relationship': edge_type
                }

                if next_id == target_id:
                    path_found = path + [new_step]
                    break

                if next_id not in visited:
                    visited.add(next_id)
                    queue.append((next_id, path + [new_step]))

        # Try reverse if no forward path
        if not path_found:
            visited = {target_id}
            queue = deque([(target_id, [])])

            while queue and not path_found:
                current_id, path = queue.popleft()

                if len(path) >= max_depth:
                    continue

                for edge in adjacency.get(current_id, []):
                    next_id = edge['target']
                    edge_type = edge['type']

                    new_step = {
                        'from_id': current_id,
                        'to_id': next_id,
                        'relationship': edge_type
                    }

                    if next_id == source_id:
                        path_found = list(reversed(path + [new_step]))
                        break

                    if next_id not in visited:
                        visited.add(next_id)
                        queue.append((next_id, path + [new_step]))

        cursor.close()

        if not path_found:
            connection.close()
            return {
                "tool_name": "find_concept_path",
                "session_id": session_id,
                "source": {"id": source_id, "text": source_node['text'], "type": source_node['node_type']},
                "target": {"id": target_id, "text": target_node['text'], "type": target_node['node_type']},
                "path_found": False,
                "message": f"No path found within {max_depth} hops. Concepts may not be directly connected.",
                "is_relevant": True,
                "result_count": 0
            }

        # Enrich path with node details
        node_ids = set()
        for step in path_found:
            node_ids.add(step['from_id'])
            node_ids.add(step['to_id'])

        cursor = connection.cursor(dictionary=True)
        placeholders = ', '.join(['%s'] * len(node_ids))
        cursor.execute(f"""
            SELECT cn.id, cn.text, cn.node_type, sp.alias as speaker
            FROM concept_node cn
            LEFT JOIN speaker sp ON cn.speaker_id = sp.id
            WHERE cn.id IN ({placeholders})
        """, list(node_ids))
        nodes_data = {n['id']: n for n in cursor.fetchall()}

        cursor.close()
        connection.close()

        # Build enriched path
        enriched_path = []
        for i, step in enumerate(path_found):
            from_node = nodes_data.get(step['from_id'], {})
            to_node = nodes_data.get(step['to_id'], {})
            enriched_path.append({
                "step": i + 1,
                "from": {
                    "text": from_node.get('text', ''),
                    "type": from_node.get('node_type', ''),
                    "speaker": from_node.get('speaker')
                },
                "relationship": step['relationship'],
                "to": {
                    "text": to_node.get('text', ''),
                    "type": to_node.get('node_type', ''),
                    "speaker": to_node.get('speaker')
                }
            })

        # Generate narrative
        narrative = _generate_path_narrative(enriched_path)

        return {
            "tool_name": "find_concept_path",
            "session_id": session_id,
            "source": {"id": source_id, "text": source_node['text'], "type": source_node['node_type']},
            "target": {"id": target_id, "text": target_node['text'], "type": target_node['node_type']},
            "path_found": True,
            "path_length": len(enriched_path),
            "path": enriched_path,
            "narrative": narrative,
            "is_relevant": True,
            "result_count": 1
        }

    except Exception as e:
        logger.error(f"Find concept path error: {e}")
        import traceback
        traceback.print_exc()
        return {"tool_name": "find_concept_path", "error": str(e), "is_relevant": False}


def _generate_path_narrative(path: List[Dict]) -> str:
    """Generate a human-readable narrative of the reasoning path."""
    if not path:
        return "No path found."

    parts = []
    for i, step in enumerate(path):
        if i == 0:
            parts.append(f"Starting from '{step['from']['text'][:50]}' ({step['from']['type']})")

        rel = step['relationship'].replace('_', ' ')
        parts.append(f"  --[{rel}]--> '{step['to']['text'][:50]}' ({step['to']['type']})")

    return "\n".join(parts)


# =============================================================================
# NEW TOOL: get_transcript - Transcript Artifact Retrieval
# =============================================================================

def get_transcript(session_id: int) -> Dict[str, Any]:
    """
    Get complete transcript for a session with per-utterance LIWC scores.

    Use this to see WHAT was said and HOW it was said (linguistic style).

    Args:
        session_id: The session to retrieve transcript for

    Returns:
        - summary: total utterances, words, questions, avg LIWC scores
        - speaker_profiles: per-speaker statistics
        - utterances: full transcript with timestamps and LIWC scores
    """
    logger.info(f"Getting transcript for session {session_id}")

    # Reuse existing internal function
    transcript_data = _get_transcript_data(session_id)

    # Get session metadata
    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT COALESCE(s.name, sd.name) as session_name
            FROM session_device sd
            JOIN session s ON s.id = sd.session_id
            WHERE sd.id = %s
        """, (session_id,))
        meta = cursor.fetchone()
        cursor.close()
        connection.close()
    except Exception as e:
        logger.error(f"Error getting session metadata: {e}")
        meta = None

    return {
        "tool_name": "get_transcript",
        "session_id": session_id,
        "session_name": meta['session_name'] if meta else f"Session {session_id}",
        "artifact_type": "transcript",
        **transcript_data,
        "is_relevant": transcript_data.get("available", False),
        "result_count": 1 if transcript_data.get("available") else 0
    }


# =============================================================================
# NEW TOOL: get_concept_map - Concept Map Artifact Retrieval
# =============================================================================

def get_concept_map(session_id: int) -> Dict[str, Any]:
    """
    Get complete concept map for a session with nodes, edges, clusters, and patterns.

    Use this to see HOW ideas connect and the structure of reasoning.

    Args:
        session_id: The session to retrieve concept map for

    Returns:
        - summary: node counts by type, speaker contributions
        - nodes: all concept nodes with text, type, speaker
        - edges: all relationships between concepts
        - clusters: thematic groupings
        - reasoning_patterns: detected patterns (causal chains, hypothesis testing, etc.)
        - hub_nodes: most connected concepts
    """
    logger.info(f"Getting concept map for session {session_id}")

    concept_data = _get_concept_map_data(session_id)

    # Get session metadata
    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT COALESCE(s.name, sd.name) as session_name, cs.discourse_type
            FROM session_device sd
            JOIN session s ON s.id = sd.session_id
            LEFT JOIN concept_session cs ON cs.session_device_id = sd.id
            WHERE sd.id = %s
        """, (session_id,))
        meta = cursor.fetchone()
        cursor.close()
        connection.close()
    except Exception as e:
        logger.error(f"Error getting session metadata: {e}")
        meta = None

    return {
        "tool_name": "get_concept_map",
        "session_id": session_id,
        "session_name": meta['session_name'] if meta else f"Session {session_id}",
        "discourse_type": meta['discourse_type'] if meta else None,
        "artifact_type": "concept_map",
        **concept_data,
        "is_relevant": concept_data.get("available", False),
        "result_count": 1 if concept_data.get("available") else 0
    }


# =============================================================================
# NEW TOOL: get_7c_analysis - Collaboration Analysis Retrieval
# =============================================================================

def get_7c_analysis(session_id: int) -> Dict[str, Any]:
    """
    Get 7C collaboration analysis for a session.

    Use this to see HOW WELL the group collaborated across 7 dimensions.

    Dimensions (each 0-100):
        - climate: Psychological safety, supportive atmosphere
        - communication: Clarity, active listening
        - contribution: Balanced participation
        - conflict: Constructive disagreement handling
        - context: Shared understanding
        - constructive: Building on others' ideas
        - compatibility: Working style alignment

    Args:
        session_id: The session to retrieve 7C analysis for

    Returns:
        - summary: overall score, interpretation, strengths, weaknesses
        - dimensions: detailed scores and evidence for each dimension
    """
    logger.info(f"Getting 7C analysis for session {session_id}")

    collab_data = _get_collaboration_data(session_id)

    # Get session metadata
    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT COALESCE(s.name, sd.name) as session_name
            FROM session_device sd
            JOIN session s ON s.id = sd.session_id
            WHERE sd.id = %s
        """, (session_id,))
        meta = cursor.fetchone()
        cursor.close()
        connection.close()
    except Exception as e:
        logger.error(f"Error getting session metadata: {e}")
        meta = None

    return {
        "tool_name": "get_7c_analysis",
        "session_id": session_id,
        "session_name": meta['session_name'] if meta else f"Session {session_id}",
        "artifact_type": "collaboration",
        **collab_data,
        "is_relevant": collab_data.get("available", False),
        "result_count": 1 if collab_data.get("available") else 0
    }


# =============================================================================
# NEW TOOL: get_liwc_metrics - LIWC Linguistic Analysis
# =============================================================================

def get_liwc_metrics(
    session_id: int,
    speaker: str = None,
    include_timeseries: bool = False
) -> Dict[str, Any]:
    """
    Get LIWC-based linguistic metrics for a session or speaker.

    Data source: Real LIWC scores per utterance (not LLM-generated).

    Use this to understand LINGUISTIC STYLE and THINKING PATTERNS.

    5 Dimensions (0-100 scale):
        - emotional_tone: Positive vs negative expression
        - analytic_thinking: Logical, formal reasoning
        - clout: Confidence and social dominance
        - authenticity: Personal, honest expression
        - certainty: Conviction and definitiveness

    Args:
        session_id: Session to analyze
        speaker: Optional speaker name to filter
        include_timeseries: If True, include full time series data

    Returns:
        - session_summary: aggregated stats (avg, min, max, std)
        - speaker_breakdown: per-speaker LIWC profiles
        - timeseries: time-ordered data (if requested)
    """
    logger.info(f"Getting LIWC metrics for session {session_id}, speaker={speaker}")

    try:
        import statistics

        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Build speaker filter
        speaker_filter = ""
        params = [session_id]
        if speaker:
            cursor.execute("SELECT id FROM speaker WHERE alias LIKE %s", (f"%{speaker}%",))
            sp = cursor.fetchone()
            if sp:
                speaker_filter = "AND t.speaker_id = %s"
                params.append(sp['id'])

        # Get LIWC data
        cursor.execute(f"""
            SELECT
                t.start_time,
                sp.alias as speaker,
                t.emotional_tone_value,
                t.analytic_thinking_value,
                t.clout_value,
                t.authenticity_value,
                t.certainty_value
            FROM transcript t
            JOIN speaker sp ON t.speaker_id = sp.id
            WHERE t.session_device_id = %s {speaker_filter}
            ORDER BY t.start_time
        """, params)

        rows = cursor.fetchall()
        cursor.close()
        connection.close()

        if not rows:
            return {
                "tool_name": "get_liwc_metrics",
                "session_id": session_id,
                "available": False,
                "reason": "No LIWC data found",
                "is_relevant": False
            }

        # Calculate aggregates
        dimensions = ['emotional_tone', 'analytic_thinking', 'clout', 'authenticity', 'certainty']

        def calc_stats(values):
            values = [v for v in values if v is not None]
            if not values:
                return {"avg": 0, "min": 0, "max": 0, "std": 0}
            return {
                "avg": round(statistics.mean(values), 1),
                "min": min(values),
                "max": max(values),
                "std": round(statistics.stdev(values), 1) if len(values) > 1 else 0
            }

        # Session-level aggregates
        session_summary = {}
        for dim in dimensions:
            values = [r[f"{dim}_value"] for r in rows]
            session_summary[dim] = calc_stats(values)

        # Speaker breakdown
        speakers = {}
        for row in rows:
            sp = row['speaker']
            if sp not in speakers:
                speakers[sp] = {dim: [] for dim in dimensions}
            for dim in dimensions:
                val = row[f"{dim}_value"]
                if val is not None:
                    speakers[sp][dim].append(val)

        speaker_breakdown = {}
        for sp, data in speakers.items():
            speaker_breakdown[sp] = {
                dim: calc_stats(data[dim]) for dim in dimensions
            }

        result = {
            "tool_name": "get_liwc_metrics",
            "session_id": session_id,
            "speaker_filter": speaker,
            "available": True,
            "utterance_count": len(rows),
            "session_summary": session_summary,
            "speaker_breakdown": speaker_breakdown,
            "is_relevant": True,
            "result_count": 1
        }

        if include_timeseries:
            result["timeseries"] = [{
                "time": r['start_time'],
                "speaker": r['speaker'],
                "emotional_tone": r['emotional_tone_value'],
                "analytic_thinking": r['analytic_thinking_value'],
                "clout": r['clout_value'],
                "authenticity": r['authenticity_value'],
                "certainty": r['certainty_value']
            } for r in rows]

        return result

    except Exception as e:
        logger.error(f"Get LIWC metrics error: {e}")
        import traceback
        traceback.print_exc()
        return {"tool_name": "get_liwc_metrics", "error": str(e), "is_relevant": False}


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

# These allow old code to keep working but delegate to new tools

def get_transcript_artifact(session_id: int, include_full_text: bool = True) -> Dict[str, Any]:
    """DEPRECATED: Use get_artifacts(session_id, include=['transcript'])"""
    result = get_artifacts(session_id, include=['transcript'])
    transcript = result.get("artifacts", {}).get("transcript", {})
    return {
        "tool_name": "get_transcript_artifact",
        "session_id": session_id,
        "session_name": result.get("session_name"),
        "artifact_type": "transcript",
        **transcript,
        "is_relevant": transcript.get("available", False),
        "result_count": 1 if transcript.get("available") else 0
    }


def get_concept_map_artifact(session_id: int) -> Dict[str, Any]:
    """DEPRECATED: Use get_artifacts(session_id, include=['concept_map'])"""
    result = get_artifacts(session_id, include=['concept_map'])
    concept_map = result.get("artifacts", {}).get("concept_map", {})
    return {
        "tool_name": "get_concept_map_artifact",
        "session_id": session_id,
        "session_name": result.get("session_name"),
        "discourse_type": result.get("discourse_type"),
        "artifact_type": "concept_map",
        **concept_map,
        "is_relevant": concept_map.get("available", False),
        "result_count": 1 if concept_map.get("available") else 0
    }


def get_collaboration_artifact(session_id: int) -> Dict[str, Any]:
    """DEPRECATED: Use get_artifacts(session_id, include=['collaboration'])"""
    result = get_artifacts(session_id, include=['collaboration'])
    collaboration = result.get("artifacts", {}).get("collaboration", {})
    return {
        "tool_name": "get_collaboration_artifact",
        "session_id": session_id,
        "session_name": result.get("session_name"),
        "artifact_type": "collaboration",
        **collaboration,
        "is_relevant": collaboration.get("available", False),
        "result_count": 1 if collaboration.get("available") else 0
    }


def get_speaker_artifacts(speaker_name: str, session_id: Optional[int] = None) -> Dict[str, Any]:
    """DEPRECATED: Use get_speaker_profile()"""
    return get_speaker_profile(speaker_name, session_id)


def synthesize_cross_representation(session_id: int, question: str, focus: Optional[str] = None) -> Dict[str, Any]:
    """DEPRECATED: Use synthesize()"""
    return synthesize(session_id, question, focus)


def get_session_artifacts(session_id: int, **kwargs) -> Dict[str, Any]:
    """DEPRECATED: Use get_artifacts()"""
    include = []
    if kwargs.get('include_transcript', True):
        include.append('transcript')
    if kwargs.get('include_concept_map', True):
        include.append('concept_map')
    if kwargs.get('include_collaboration', True):
        include.append('collaboration')
    return get_artifacts(session_id, include=include)


def cross_reference_claim(session_id: int, claim: str) -> Dict[str, Any]:
    """DEPRECATED: Use synthesize() with the claim as the question"""
    return synthesize(session_id, claim, focus=None)


# =============================================================================
# TOOL REGISTRY - OPTIMAL 6 TOOLS
# =============================================================================

ARTIFACT_TOOLS = {
    # Discovery
    "list_sessions": list_sessions,
    "search_for_sessions": search_for_sessions,

    # Artifact retrieval (separate tools - preferred)
    "get_transcript": get_transcript,
    "get_concept_map": get_concept_map,
    "get_7c_analysis": get_7c_analysis,
    "get_liwc_metrics": get_liwc_metrics,

    # Legacy combined artifact retrieval (for backward compatibility)
    "get_artifacts": get_artifacts,

    # Speaker analysis
    "get_speaker_profile": get_speaker_profile,

    # Synthesis (cross-rep AND cross-session)
    "synthesize": synthesize,

    # Graph reasoning
    "find_concept_path": find_concept_path,
}

# Backward compatibility - includes deprecated aliases
COMBINED_TOOLS = {
    **ARTIFACT_TOOLS,
    # Deprecated but kept for compatibility
    "get_transcript_artifact": get_transcript_artifact,
    "get_concept_map_artifact": get_concept_map_artifact,
    "get_collaboration_artifact": get_collaboration_artifact,
    "get_speaker_artifacts": get_speaker_artifacts,
    "synthesize_cross_representation": synthesize_cross_representation,
    "get_session_artifacts": get_session_artifacts,
    "cross_reference_claim": cross_reference_claim,
}

ARTIFACT_TOOL_DESCRIPTIONS = """
## 8-TOOL ARTIFACT-CENTRIC DESIGN

These tools provide a principled set for artifact-centric reasoning.

### DISCOVERY TOOLS

#### 1. list_sessions
List all available sessions with metadata.
Use FIRST to understand what data exists.
Returns: session IDs, names, speakers, which artifacts are available.

#### 2. search_for_sessions(query, top_k=3)
Find sessions relevant to a query using semantic search.
Use to DISCOVER which sessions are relevant, then use artifact tools to retrieve.

### ARTIFACT RETRIEVAL TOOLS (Separate, Clearer Intent)

#### 3. get_transcript(session_id)
Get complete transcript for a session.
Use to see WHAT was said and HOW (linguistic style via per-utterance LIWC).
Returns: summary, speaker_profiles, utterances with timestamps and LIWC scores.

#### 4. get_concept_map(session_id)
Get concept map with nodes, edges, clusters, and reasoning patterns.
Use to see HOW ideas connect and the structure of reasoning.
Returns: nodes, edges, clusters, reasoning_patterns, hub_nodes.

#### 5. get_7c_analysis(session_id)
Get 7C collaboration analysis.
Use to see HOW WELL the group collaborated across 7 dimensions:
- climate, communication, contribution, conflict, context, constructive, compatibility
Returns: summary (overall score, strengths, weaknesses), dimensions with evidence.

#### 6. get_liwc_metrics(session_id, speaker=None, include_timeseries=False)
Get LIWC linguistic metrics (real data, not LLM-generated).
Use to understand LINGUISTIC STYLE and THINKING PATTERNS.
5 Dimensions: emotional_tone, analytic_thinking, clout, authenticity, certainty.
Returns: session_summary (avg, min, max, std), speaker_breakdown, optional timeseries.

### SPEAKER & GRAPH TOOLS

#### 7. get_speaker_profile(speaker_name, session_id=None)
Get complete speaker profile across representations.
- Transcript: utterances, questions, analytic/certainty scores
- Concept Map: concepts contributed AND their graph connections
- Cross-session view if session_id is None

#### 8. find_concept_path(session_id, from_concept, to_concept, max_depth=5)
Find reasoning path between two concepts in a concept map.
Use AFTER getting artifacts when you need to trace how one idea led to another.
Performs BFS graph traversal - don't try to trace paths mentally.
Returns: The path with each step's relationship type, plus narrative.

### LEGACY TOOLS (Backward Compatibility)

#### get_artifacts(session_id, include=['transcript', 'concept_map', 'collaboration'])
Combined artifact retrieval. Prefer separate tools above for clearer intent.

#### synthesize(session_ids, question, focus=None)
Cross-rep AND cross-session synthesis tool.
Note: Synthesis is typically done by the LLM in the synthesis node, not as a tool call.
"""
