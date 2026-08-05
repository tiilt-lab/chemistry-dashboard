"""
Artifact-Centric Tools for BLINC Agent V7

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
    """Get direct MySQL connection (study-aware via study_context)."""
    from study_context import get_db_connection
    return get_db_connection()


def _get_rag_service():
    """Lazy import of RAG service (study-aware via study_context)."""
    from rag_service import RAGService
    from study_context import get_chroma_path
    return RAGService(persist_directory=get_chroma_path())


def _load_dimension_definitions_from_db() -> Dict[str, str]:
    """Load dimension definitions from the default dimension_schema in the DB.

    Returns a dict mapping dimension key -> description.
    Falls back to basic 7C definitions if DB query fails.
    """
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
            dims = row['dimensions']
            if isinstance(dims, str):
                dims = json.loads(dims)
            return {d['key']: d.get('description', d.get('name', '')) for d in dims}
    except Exception as e:
        logger.debug(f"Could not load dimension definitions from DB: {e}")

    # Fallback to basic 7C definitions
    return {
        "climate": "Psychological safety and supportive atmosphere",
        "communication": "Clarity, active listening, articulation",
        "contribution": "Balanced participation, equal voice",
        "conflict": "Constructive disagreement handling",
        "context": "Shared understanding, common ground",
        "constructive": "Building on others' ideas",
        "compatibility": "Working style alignment"
    }


# =============================================================================
# TOOL 1: list_sessions - Discovery
# =============================================================================

def list_sessions() -> Dict[str, Any]:
    """
    List all available sessions with metadata and collaboration scores.

    Use this FIRST to understand what data is available before retrieving artifacts.
    For superlative queries (best/worst collaboration), use the collaboration_score
    to identify top candidates, then call get_7c_analysis for detailed breakdown.

    Returns:
        All sessions with: id, name, speakers, discourse_type, artifacts_available,
        and collaboration_score (overall 7C average, 0-100)
    """
    logger.info("Listing all sessions")

    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Use subqueries to avoid duplicates from LEFT JOINs when multiple
        # concept_session or seven_cs_analysis records exist per session_device
        cursor.execute("""
            SELECT
                sd.id as session_id,
                sd.name as device_name,
                s.name as session_name,
                (SELECT cs.discourse_type FROM concept_session cs
                 WHERE cs.session_device_id = sd.id LIMIT 1) as discourse_type,
                (SELECT GROUP_CONCAT(DISTINCT COALESCE(NULLIF(sp.alias, ''), CONCAT('Speaker_', sp.id)))
                 FROM transcript t
                 JOIN speaker sp ON t.speaker_id = sp.id
                 WHERE t.session_device_id = sd.id) as speakers,
                (SELECT COUNT(DISTINCT t.speaker_id)
                 FROM transcript t
                 WHERE t.session_device_id = sd.id) as speaker_count,
                (SELECT COUNT(*) FROM transcript WHERE session_device_id = sd.id) as transcript_count,
                (SELECT COUNT(*) FROM concept_node cn
                 JOIN concept_session ccs ON cn.concept_session_id = ccs.id
                 WHERE ccs.session_device_id = sd.id) as concept_count,
                (SELECT sca.analysis_summary FROM seven_cs_analysis sca
                 WHERE sca.session_device_id = sd.id ORDER BY sca.id DESC LIMIT 1) as seven_c_json
            FROM session_device sd
            JOIN session s ON s.id = sd.session_id
            ORDER BY sd.id
        """)

        sessions = []
        for row in cursor.fetchall():
            # Calculate overall collaboration score from 7C JSON
            collaboration_score = None
            if row['seven_c_json']:
                try:
                    import json
                    seven_c = json.loads(row['seven_c_json']) if isinstance(row['seven_c_json'], str) else row['seven_c_json']
                    scores = []
                    for dim, data in seven_c.items():
                        if isinstance(data, dict) and 'score' in data:
                            scores.append(data['score'])
                    if scores:
                        collaboration_score = round(sum(scores) / len(scores), 1)
                except Exception as e:
                    logger.warning(f"Failed to parse 7C JSON for session {row['session_id']}: {e}")

            sessions.append({
                "session_id": row['session_id'],
                "device_name": row['device_name'],
                "session_name": row['session_name'],
                "discourse_type": row['discourse_type'],
                "speakers": row['speakers'].split(',') if row['speakers'] else [],
                "speaker_count": row['speaker_count'] or 0,
                "collaboration_score": collaboration_score
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
    top_k: int = 10,  # Increased from 5 for better recall
    min_score: float = 0.20,  # Absolute minimum similarity (full queries score higher than topic keywords)
    min_relative_score: float = 0.65  # Relative threshold to reduce false positives
) -> Dict[str, Any]:
    """
    Find sessions relevant to a query using multi-collection semantic search with RRF fusion.

    Searches across THREE collections for comprehensive discovery:
    - transcript_collection: Content/topic matches (what was discussed)
    - seven_c_collection: Collaboration quality matches (how they discussed)
    - concept_collection: Structural matches (ideas and relationships)

    Uses Reciprocal Rank Fusion (RRF) to combine rankings from all collections,
    ensuring sessions that are relevant across multiple dimensions rank higher.

    Use to DISCOVER which sessions are relevant, then use get_artifacts() to retrieve.

    Args:
        query: What to search for
        top_k: Maximum sessions to return (default 10)
        min_score: Minimum absolute RRF score. Default 0.20.
        min_relative_score: Minimum score relative to best match. Default 0.60 means
                           sessions must score at least 60% of the best match.
                           Balances recall with precision to avoid false positives.

    Returns:
        Ranked list of relevant session IDs with match reasons and collection contributions
    """
    logger.info(f"[Multi-Collection Search] Query: '{query}'")

    try:
        rag = _get_rag_service()

        # =========================================================================
        # STEP 0: Check for exact session name match FIRST (priority over semantic)
        # =========================================================================
        exact_match_sessions = []
        try:
            conn = _get_db_connection()
            cursor = conn.cursor(dictionary=True)
            # Check for exact or partial name match (case insensitive)
            cursor.execute("""
                SELECT DISTINCT
                    sd.id as session_device_id,
                    s.id as session_id,
                    COALESCE(s.name, sd.name) as session_name,
                    sd.name as device_name
                FROM session_device sd
                JOIN session s ON sd.session_id = s.id
                WHERE LOWER(s.name) = LOWER(%s)
                   OR LOWER(s.name) LIKE LOWER(%s)
                   OR LOWER(sd.name) LIKE LOWER(%s)
            """, (query, f"%{query}%", f"%{query}%"))
            exact_match_sessions = cursor.fetchall()
            cursor.close()
            conn.close()
            if exact_match_sessions:
                logger.info(f"  [exact_match] Found {len(exact_match_sessions)} sessions matching name '{query}'")
        except Exception as e:
            logger.warning(f"  [exact_match] Name lookup failed: {e}")

        # =========================================================================
        # STEP 1: Query all three collections
        # =========================================================================
        results_per_collection = top_k * 3  # Get more results per collection for better fusion

        results_by_collection = {}

        # Search transcript collection (what was said)
        try:
            transcript_results = rag.transcript_collection.query(
                query_texts=[query],
                n_results=results_per_collection
            )
            results_by_collection['transcript'] = transcript_results
            logger.info(f"  [transcript] Found {len(transcript_results.get('documents', [[]])[0])} results")
        except Exception as e:
            logger.warning(f"  [transcript] Search failed: {e}")
            results_by_collection['transcript'] = {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}

        # Search 7C collection (collaboration quality)
        try:
            seven_c_results = rag.seven_c_collection.query(
                query_texts=[query],
                n_results=results_per_collection
            )
            results_by_collection['seven_c'] = seven_c_results
            logger.info(f"  [seven_c] Found {len(seven_c_results.get('documents', [[]])[0])} results")
        except Exception as e:
            logger.warning(f"  [seven_c] Search failed: {e}")
            results_by_collection['seven_c'] = {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}

        # Search concept collection (idea structure)
        try:
            concept_results = rag.concept_collection.query(
                query_texts=[query],
                n_results=results_per_collection
            )
            results_by_collection['concept'] = concept_results
            logger.info(f"  [concept] Found {len(concept_results.get('documents', [[]])[0])} results")
        except Exception as e:
            logger.warning(f"  [concept] Search failed: {e}")
            results_by_collection['concept'] = {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}

        # =========================================================================
        # STEP 2: Reciprocal Rank Fusion (RRF)
        # =========================================================================
        k = 60  # Standard RRF constant
        session_rrf_scores = {}  # session_id -> RRF score
        session_metadata = {}    # session_id -> best metadata
        session_collections = {}  # session_id -> which collections matched
        session_previews = {}    # session_id -> best preview snippet

        for collection_name, results in results_by_collection.items():
            docs = results.get('documents', [[]])[0]
            metas = results.get('metadatas', [[]])[0]
            dists = results.get('distances', [[]])[0]

            for rank, (doc, meta, dist) in enumerate(zip(docs, metas, dists)):
                if not meta:
                    continue
                sid = meta.get('session_device_id')
                if not sid:
                    continue

                similarity = 1 - dist  # Convert distance to similarity

                # Skip very low similarity results
                if similarity < 0.15:
                    continue

                # RRF score contribution: 1/(k + rank + 1)
                rrf_contribution = 1.0 / (k + rank + 1)

                if sid not in session_rrf_scores:
                    session_rrf_scores[sid] = 0.0
                    session_collections[sid] = []
                    session_previews[sid] = ""

                session_rrf_scores[sid] += rrf_contribution

                # Track which collections contributed
                if collection_name not in session_collections[sid]:
                    session_collections[sid].append(collection_name)

                # Keep best metadata (prefer transcript metadata as it has more info)
                if sid not in session_metadata or collection_name == 'transcript':
                    session_metadata[sid] = meta

                # Keep best preview (prefer transcript content)
                if collection_name == 'transcript' and doc:
                    session_previews[sid] = doc[:200]

        # =========================================================================
        # STEP 3: Build ranked session list
        # =========================================================================
        session_scores = {}
        for sid, rrf_score in session_rrf_scores.items():
            meta = session_metadata.get(sid, {})
            speakers_str = meta.get('speakers', '')
            speakers = speakers_str.split(',') if speakers_str else []

            session_scores[sid] = {
                "session_id": sid,
                "session_name": meta.get('session_name', f"Session {sid}"),
                "device_name": meta.get('device_name'),
                "speakers": speakers,
                "best_match_score": round(rrf_score, 4),  # RRF score for backward compatibility
                "collections_matched": session_collections.get(sid, []),
                "match_preview": session_previews.get(sid, "")
            }

        # Sort by RRF score
        sorted_sessions = sorted(session_scores.values(), key=lambda x: x['best_match_score'], reverse=True)
        # Debug: log all session scores before filtering
        for s in sorted_sessions:
            logger.info(f"  [RRF] Session {s['session_id']} ({s['session_name']}): score={s['best_match_score']:.4f}, collections={s['collections_matched']}")

        # =========================================================================
        # STEP 3.5: Inject exact name matches at the TOP with high priority
        # =========================================================================
        if exact_match_sessions:
            exact_match_ids = set()
            for em in exact_match_sessions:
                sid = em['session_device_id']
                exact_match_ids.add(sid)
                # Check if already in semantic results
                existing = next((s for s in sorted_sessions if s['session_id'] == sid), None)
                if existing:
                    # Boost existing score to ensure it's at top
                    existing['best_match_score'] = max(existing['best_match_score'], 1.0)
                    existing['match_type'] = 'exact_name_match'
                    logger.info(f"  [exact_match] Boosted session {sid} ({em['session_name']}) to top")
                else:
                    # Add exact match with high score
                    sorted_sessions.insert(0, {
                        "session_id": sid,
                        "session_device_id": sid,
                        "session_name": em['session_name'],
                        "device_name": em.get('device_name'),
                        "speakers": [],
                        "best_match_score": 1.0,  # High score for exact match
                        "collections_matched": ['exact_name'],
                        "match_preview": f"Exact name match for '{query}'",
                        "match_type": 'exact_name_match'
                    })
                    logger.info(f"  [exact_match] Added session {sid} ({em['session_name']}) as exact match")
            # Re-sort to put boosted exact matches at top
            sorted_sessions = sorted(sorted_sessions, key=lambda x: x['best_match_score'], reverse=True)

        # =========================================================================
        # STEP 4: Smart filtering with relative threshold
        # =========================================================================
        if sorted_sessions:
            # Calculate threshold from SEMANTIC results only (exclude exact matches)
            semantic_sessions = [s for s in sorted_sessions if s.get('match_type') != 'exact_name_match']
            if semantic_sessions:
                best_semantic_score = semantic_sessions[0]['best_match_score']
            else:
                best_semantic_score = 0.05  # Default if no semantic results

            # Scale min_score to RRF range (RRF scores are typically 0.01-0.05)
            rrf_min_score = min_score * 0.05  # Scale down since RRF scores are much smaller
            relative_threshold = best_semantic_score * min_relative_score

            ranked = []
            for s in sorted_sessions[:top_k]:
                # Always include exact name matches
                if s.get('match_type') == 'exact_name_match':
                    ranked.append(s)
                elif s['best_match_score'] >= relative_threshold and s['best_match_score'] >= rrf_min_score:
                    ranked.append(s)
                else:
                    logger.info(f"  [Search] Excluded session {s['session_id']} "
                               f"(score {s['best_match_score']:.4f} < threshold {max(relative_threshold, rrf_min_score):.4f})")
        else:
            ranked = []

        # Log collection coverage for debugging
        if ranked:
            multi_collection_count = sum(1 for s in ranked if len(s.get('collections_matched', [])) > 1)
            logger.info(f"[Multi-Collection Search] {len(ranked)} sessions found, "
                       f"{multi_collection_count} matched in multiple collections")

        # =========================================================================
        # STEP 5: Build response
        # =========================================================================
        response = {
            "tool_name": "search_for_sessions",
            "query": query,
            "sessions_found": len(ranked),
            "sessions": ranked,
            "is_relevant": len(ranked) > 0,
            "result_count": len(ranked),
            "search_type": "multi_collection_rrf",
            "collections_searched": ["transcript", "seven_c", "concept"]
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
# TOOL 2B: find_sessions_by_structure - Signal-Based Discovery
# =============================================================================

def find_sessions_by_structure(
    edge_types: List[str] = None,
    node_types: List[str] = None,
    min_count: int = 1,
    seven_c_dimension: str = None,
    min_seven_c_score: float = None,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Find sessions based on concept map structure or 7C scores.

    Use this for PATTERN QUERIES where you need to find sessions based on
    structural signals rather than semantic text search.

    Args:
        edge_types: List of edge types to search for (e.g., ["challenges", "contrasts_with"])
                   Available: challenges, contrasts_with, builds_on, supports, elaborates, relates_to
        node_types: List of node types to search for (e.g., ["hypothesis", "question"])
                   Available: idea, question, hypothesis, reasoning, synthesis, problem, solution, goal
        min_count: Minimum count of matching edges/nodes to include session
        seven_c_dimension: 7C dimension to filter by (e.g., "conflict_score")
                          Available: climate_score, communication_score, contribution_score,
                                    conflict_score, context_score, constructive_score, compatibility_score
        min_seven_c_score: Minimum score (0-100) for the 7C dimension
        top_k: Maximum number of sessions to return

    Returns:
        Sessions ranked by signal strength with counts

    Examples:
        - find_sessions_by_structure(edge_types=["challenges", "contrasts_with"])
          → Find sessions with disagreement/debate
        - find_sessions_by_structure(node_types=["hypothesis", "reasoning"])
          → Find sessions with speculative/analytical thinking
        - find_sessions_by_structure(seven_c_dimension="conflict_score", min_seven_c_score=60)
          → Find sessions with high conflict scores
    """
    logger.info(f"Finding sessions by structure: edges={edge_types}, nodes={node_types}, 7c={seven_c_dimension}")

    try:
        conn = _get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sessions_data = {}

        # Query 1: Count edges by type per session
        if edge_types:
            placeholders = ','.join(['%s'] * len(edge_types))
            cursor.execute(f"""
                SELECT cs.session_device_id, ce.edge_type, COUNT(*) as count
                FROM concept_session cs
                JOIN concept_node cn ON cn.concept_session_id = cs.id
                JOIN concept_edge ce ON ce.source_node_id = cn.id
                WHERE ce.edge_type IN ({placeholders})
                GROUP BY cs.session_device_id, ce.edge_type
            """, edge_types)

            for row in cursor.fetchall():
                sid = row['session_device_id']
                if sid not in sessions_data:
                    sessions_data[sid] = {'edge_counts': {}, 'node_counts': {}, 'seven_c': {}}
                sessions_data[sid]['edge_counts'][row['edge_type']] = row['count']

        # Query 2: Count nodes by type per session
        if node_types:
            placeholders = ','.join(['%s'] * len(node_types))
            cursor.execute(f"""
                SELECT cs.session_device_id, cn.node_type, COUNT(*) as count
                FROM concept_session cs
                JOIN concept_node cn ON cn.concept_session_id = cs.id
                WHERE cn.node_type IN ({placeholders})
                GROUP BY cs.session_device_id, cn.node_type
            """, node_types)

            for row in cursor.fetchall():
                sid = row['session_device_id']
                if sid not in sessions_data:
                    sessions_data[sid] = {'edge_counts': {}, 'node_counts': {}, 'seven_c': {}}
                sessions_data[sid]['node_counts'][row['node_type']] = row['count']

        # Query 3: Get 7C scores if requested
        if seven_c_dimension:
            # 7C scores are in JSON column analysis_summary - we extract session_device_id and parse JSON in Python
            cursor.execute("""
                SELECT session_device_id, analysis_summary
                FROM seven_cs_analysis
                WHERE analysis_status = 'completed'
            """)

            for row in cursor.fetchall():
                sid = row['session_device_id']
                if sid not in sessions_data:
                    sessions_data[sid] = {'edge_counts': {}, 'node_counts': {}, 'seven_c': {}}
                # Parse JSON analysis_summary to extract scores
                try:
                    import json as json_module
                    summary = row.get('analysis_summary', '{}')
                    if isinstance(summary, str):
                        summary = json_module.loads(summary)
                    sessions_data[sid]['seven_c'] = {
                        'climate_score': summary.get('climate', {}).get('score', 0),
                        'communication_score': summary.get('communication', {}).get('score', 0),
                        'contribution_score': summary.get('contribution', {}).get('score', 0),
                        'conflict_score': summary.get('conflict', {}).get('score', 0),
                        'context_score': summary.get('context', {}).get('score', 0),
                        'constructive_score': summary.get('constructive', {}).get('score', 0),
                        'compatibility_score': summary.get('compatibility', {}).get('score', 0)
                    }
                except Exception as e:
                    logger.warning(f"Failed to parse 7C JSON for session {sid}: {e}")

        # Get session names
        cursor.execute("SELECT id as session_device_id, name as session_name FROM session_device")
        session_names = {r['session_device_id']: r['session_name'] for r in cursor.fetchall()}

        cursor.close()
        conn.close()

        # Score and filter sessions
        results = []
        for sid, data in sessions_data.items():
            # Calculate total signal count
            edge_total = sum(data['edge_counts'].values()) if data['edge_counts'] else 0
            node_total = sum(data['node_counts'].values()) if data['node_counts'] else 0
            signal_count = edge_total + node_total

            # Apply minimum count filter
            if signal_count < min_count and not seven_c_dimension:
                continue

            # Apply 7C filter if specified
            if seven_c_dimension and min_seven_c_score is not None:
                score = data['seven_c'].get(seven_c_dimension, 0)
                if score < min_seven_c_score:
                    continue

            results.append({
                'session_id': sid,
                'session_name': session_names.get(sid, f"Session {sid}"),
                'edge_counts': data['edge_counts'],
                'node_counts': data['node_counts'],
                'seven_c': data['seven_c'] if seven_c_dimension else {},
                'signal_strength': signal_count
            })

        # Sort by signal strength
        results.sort(key=lambda x: x['signal_strength'], reverse=True)
        results = results[:top_k]

        return {
            'tool_name': 'find_sessions_by_structure',
            'edge_types_searched': edge_types or [],
            'node_types_searched': node_types or [],
            'seven_c_filter': {'dimension': seven_c_dimension, 'min_score': min_seven_c_score} if seven_c_dimension else None,
            'sessions_found': len(results),
            'sessions': results,
            'is_relevant': len(results) > 0,
            'result_count': len(results)
        }

    except Exception as e:
        logger.error(f"Structure search error: {e}")
        return {
            'tool_name': 'find_sessions_by_structure',
            'error': str(e),
            'sessions': [],
            'is_relevant': False
        }


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
                sd.name as device_name,
                s.name as session_name,
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

        result["device_name"] = session_meta['device_name']
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

        # Get concept session (including requested types for edit mode awareness)
        cursor.execute("""
            SELECT id, discourse_type, requested_node_types, requested_edge_types
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

        # V7: Return more hub nodes for fuller picture
        hub_nodes = sorted(
            [(nid, count) for nid, count in connections_per_node.items()],
            key=lambda x: x[1],
            reverse=True
        )[:10]  # V7: Increased from 5 to 10

        node_map = {n['id']: n for n in nodes}
        hubs = [{
            "node_id": nid,
            "connections": count,
            "text": node_map.get(nid, {}).get('text', ''),  # V7: Full text, no truncation
            "type": node_map.get(nid, {}).get('type', '')
        } for nid, count in hub_nodes if nid in node_map]

        # Parse requested types from concept_session (for edit mode scope awareness)
        raw_req_nodes = cs.get('requested_node_types')
        raw_req_edges = cs.get('requested_edge_types')
        if isinstance(raw_req_nodes, str):
            raw_req_nodes = json.loads(raw_req_nodes)
        if isinstance(raw_req_edges, str):
            raw_req_edges = json.loads(raw_req_edges)

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
            "hub_nodes": hubs,
            "requested_node_types": raw_req_nodes,  # None = all types
            "requested_edge_types": raw_req_edges,   # None = all types
        }

    except Exception as e:
        logger.error(f"Get concept map data error: {e}")
        return {"available": False, "error": str(e)}


def _get_collaboration_data(session_id: int) -> Dict[str, Any]:
    """Internal: Get complete 7C collaboration data including coded segments."""
    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get analysis summary and AI baseline (for edit detection)
        cursor.execute("""
            SELECT
                id as analysis_id,
                analysis_summary,
                ai_baseline,
                total_segments_analyzed,
                llm_model_used,
                created_at
            FROM seven_cs_analysis
            WHERE session_device_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (session_id,))
        row = cursor.fetchone()

        if not row or not row.get('analysis_summary'):
            cursor.close()
            connection.close()
            return {"available": False, "reason": "No 7C analysis available"}

        analysis_id = row['analysis_id']

        # V7 FIX: Get ACTUAL coded segments from seven_cs_coded_segment table
        # These have timestamps, speaker, confidence, actual quotes, and coding reasons
        cursor.execute("""
            SELECT
                dimension,
                start_time,
                speaker_tag,
                text_snippet,
                coding_reason,
                confidence
            FROM seven_cs_coded_segment
            WHERE analysis_id = %s
            ORDER BY dimension, start_time
        """, (analysis_id,))
        coded_segment_rows = cursor.fetchall()

        cursor.close()
        connection.close()

        # Group coded segments by dimension
        coded_segments_by_dim = {}
        for seg in coded_segment_rows:
            dim = seg['dimension']
            if dim not in coded_segments_by_dim:
                coded_segments_by_dim[dim] = []
            coded_segments_by_dim[dim].append({
                "timestamp": seg['start_time'],
                "speaker": seg['speaker_tag'],
                "quote": seg['text_snippet'],
                "reason": seg['coding_reason']
            })

        analysis = row['analysis_summary']
        if isinstance(analysis, str):
            analysis = json.loads(analysis)

        # Parse AI baseline for edit detection
        baseline = row.get('ai_baseline')
        if baseline and isinstance(baseline, str):
            baseline = json.loads(baseline)
        if not baseline or not isinstance(baseline, dict):
            baseline = {}

        # Build dimension data — dynamically from analysis_summary keys
        # Load definitions from DB schema for display labels
        dimension_definitions = _load_dimension_definitions_from_db()

        dimensions = {}
        total_score = 0

        for dim_name, dim_data in analysis.items():
            if not isinstance(dim_data, dict) or 'score' not in dim_data:
                continue  # Skip non-dimension keys (e.g., metadata)
            definition = dimension_definitions.get(dim_name, dim_data.get('definition', dim_name.replace('_', ' ').title()))
            score = dim_data.get('score', 0)
            total_score += score

            # Use REAL coded segments if available, fall back to summary evidence
            real_coded_segments = coded_segments_by_dim.get(dim_name, [])

            dim_entry = {
                "score": score,
                "definition": definition,
                "explanation": dim_data.get('explanation', ''),
                # V7: Include ACTUAL coded segments with quotes, reasons, and confidence
                "coded_segments": real_coded_segments if real_coded_segments else dim_data.get('evidence', [])
            }

            # Detect edits by comparing current vs AI baseline
            # Converged design:
            #   Strong signal (edited=True): score changed AND (explanation OR evidence) also changed
            #   Light signal (stale_explanation=True): score changed but text fields unchanged
            #   Text-only changes: no annotation — agent picks them up naturally
            baseline_dim = baseline.get(dim_name, {})
            if baseline_dim:
                baseline_score = baseline_dim.get('score')
                baseline_explanation = baseline_dim.get('explanation', '')
                baseline_evidence = baseline_dim.get('evidence', [])
                current_explanation = dim_data.get('explanation', '')
                current_evidence = dim_data.get('evidence', [])

                score_changed = (baseline_score is not None and baseline_score != score)
                explanation_changed = (baseline_explanation != current_explanation)
                evidence_changed = (json.dumps(baseline_evidence, sort_keys=True) != json.dumps(current_evidence, sort_keys=True))
                text_changed = explanation_changed or evidence_changed

                if score_changed:
                    dim_entry["original_ai_score"] = baseline_score
                    if text_changed:
                        # Strong: score + text both changed — user invested effort
                        dim_entry["edited"] = True
                        dim_entry["explanation_updated"] = explanation_changed
                        dim_entry["evidence_updated"] = evidence_changed
                    else:
                        # Light: score-only change — stale warning, no [Edited by you]
                        dim_entry["stale_explanation"] = True

            dimensions[dim_name] = dim_entry

        dim_count = len(dimensions) if dimensions else 1
        overall_score = round(total_score / dim_count, 1)

        # Sort for strengths/weaknesses
        sorted_dims = sorted(dimensions.items(), key=lambda x: x[1]['score'], reverse=True)

        # V7: Full explanations, no truncation
        strengths = [{
            "dimension": d[0],
            "score": d[1]['score'],
            "why": d[1]['explanation'] if d[1]['explanation'] else ""  # V7: Full explanation
        } for d in sorted_dims[:3]]  # V7: Top 3 strengths

        weaknesses = [{
            "dimension": d[0],
            "score": d[1]['score'],
            "why": d[1]['explanation'] if d[1]['explanation'] else ""  # V7: Full explanation
        } for d in sorted_dims[-3:] if d[1]['score'] < 70]  # V7: Bottom 3 weaknesses

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

        # Find ALL speaker records with this alias (same person may have multiple IDs)
        cursor.execute("""
            SELECT id, alias FROM speaker WHERE alias LIKE %s
        """, (f"%{speaker_name}%",))
        speakers = cursor.fetchall()

        if not speakers:
            cursor.close()
            connection.close()
            return {
                "tool_name": "get_speaker_profile",
                "error": f"Speaker '{speaker_name}' not found",
                "is_relevant": False
            }

        # Get all speaker IDs (same person may have multiple records across sessions)
        speaker_ids = [s['id'] for s in speakers]
        speaker_alias = speakers[0]['alias']  # Use first alias as canonical name

        session_filter = f"AND t.session_device_id = {session_id}" if session_id else ""
        speaker_id_list = ', '.join(str(sid) for sid in speaker_ids)

        # Transcript data with session-relative comparison (query all speaker IDs)
        cursor.execute(f"""
            SELECT
                t.session_device_id,
                COALESCE(s.name, sd.name) as session_name,
                COUNT(*) as utterance_count,
                SUM(t.word_count) as word_count,
                SUM(CASE WHEN t.question = 1 THEN 1 ELSE 0 END) as questions,
                AVG(t.analytic_thinking_value) as avg_analytic,
                AVG(t.certainty_value) as avg_certainty,
                -- Session totals for comparison
                (SELECT COUNT(*) FROM transcript t2 WHERE t2.session_device_id = t.session_device_id) as session_total_utterances,
                (SELECT COUNT(DISTINCT t2.speaker_id) FROM transcript t2 WHERE t2.session_device_id = t.session_device_id) as session_speaker_count
            FROM transcript t
            JOIN session_device sd ON t.session_device_id = sd.id
            JOIN session s ON sd.session_id = s.id
            WHERE t.speaker_id IN ({speaker_id_list}) {session_filter}
            GROUP BY t.session_device_id, s.name, sd.name
        """)
        transcript_data = cursor.fetchall()

        # Calculate comparative metrics for each session (raw data, not interpreted)
        # The LLM should reason about what these patterns mean
        for row in transcript_data:
            # Convert Decimal to int/float for calculations (MySQL returns Decimal types)
            session_total = int(row.get('session_total_utterances') or 1)
            speaker_count = int(row.get('session_speaker_count') or 1)
            utterances = int(row.get('utterance_count') or 0)
            questions = int(row.get('questions') or 0)

            # Comparative metrics (let LLM interpret what they mean)
            row['participation_share_pct'] = round(utterances * 100.0 / session_total, 1) if session_total > 0 else 0
            row['question_rate_pct'] = round(questions * 100.0 / utterances, 1) if utterances > 0 else 0
            row['session_speaker_count'] = speaker_count
            row['expected_equal_share_pct'] = round(100.0 / speaker_count, 1) if speaker_count > 0 else 100.0

        # Sample quotes (from all speaker IDs with this alias)
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
            WHERE t.speaker_id IN ({speaker_id_list}) {session_filter}
            AND t.word_count > 15
            ORDER BY t.word_count DESC
            LIMIT 5
        """)
        sample_quotes = cursor.fetchall()

        # Concept data (from all speaker IDs with this alias)
        session_concept_filter = f"AND cs.session_device_id = {session_id}" if session_id else ""
        cursor.execute(f"""
            SELECT
                cn.id as node_id,
                cn.node_type,
                cn.text,
                cs.session_device_id
            FROM concept_node cn
            JOIN concept_session cs ON cn.concept_session_id = cs.id
            WHERE cn.speaker_id IN ({speaker_id_list}) {session_concept_filter}
        """)
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
            "speaker_ids": speaker_ids,  # May have multiple IDs if same person across sessions
            "session_scope": session_id if session_id else "all sessions",

            "transcript_summary": {
                "sessions_participated": len(transcript_data),
                "participation_by_session": [{
                    "session_id": d['session_device_id'],
                    "session_name": d['session_name'],
                    "utterances": int(d['utterance_count'] or 0),
                    "words": int(d['word_count'] or 0),
                    "questions_asked": int(d['questions'] or 0),
                    # Comparative metrics for LLM to reason about
                    "question_rate_pct": d.get('question_rate_pct', 0),
                    "participation_share_pct": d.get('participation_share_pct', 0),
                    "session_speaker_count": d.get('session_speaker_count', 1),
                    "expected_equal_share_pct": d.get('expected_equal_share_pct', 100),
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
# NEW TOOL: get_collaboration_assessment - Collaboration Analysis Retrieval
# =============================================================================

def get_collaboration_assessment(session_id: int) -> Dict[str, Any]:
    """
    Get collaboration assessment for a session.

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
    logger.info(f"Getting collaboration assessment for session {session_id}")

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
        "tool_name": "get_collaboration_assessment",
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
    "get_collaboration_assessment": get_collaboration_assessment,
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

#### 5. get_collaboration_assessment(session_id)
Get collaboration assessment.
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
