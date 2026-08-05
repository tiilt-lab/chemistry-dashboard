"""
Analysis Tools for BLINC Agent V3

Tools for deep analysis of sessions, collaboration, and speakers.
"""

import logging
import sys
import os
from typing import Dict, Any, List, Optional

# Add server directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)


def _get_db_connection():
    """Get direct MySQL connection for agent tools."""
    import mysql.connector
    return mysql.connector.connect(
        host='localhost',
        user='vagrant',
        password='vagrant',
        database='discussion_capture'
    )


def list_sessions() -> Dict[str, Any]:
    """
    List all available sessions with basic metadata.

    Returns:
        List of sessions with ID, name, speaker count, discourse type
    """
    logger.info("Listing all sessions")

    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                sd.id as session_device_id,
                COALESCE(s.name, sd.name) as session_name,
                cs.discourse_type,
                (SELECT COUNT(DISTINCT speaker_id) FROM transcript WHERE session_device_id = sd.id) as speaker_count,
                (SELECT COUNT(*) FROM transcript WHERE session_device_id = sd.id) as transcript_count
            FROM session_device sd
            JOIN session s ON s.id = sd.session_id
            LEFT JOIN concept_session cs ON cs.session_device_id = sd.id
            ORDER BY sd.id
        """)

        sessions = cursor.fetchall()
        cursor.close()
        connection.close()

        return {
            'tool_name': 'list_sessions',
            'result_count': len(sessions),
            'results': sessions,
            'is_relevant': True
        }

    except Exception as e:
        logger.error(f"List sessions error: {e}")
        return {
            'tool_name': 'list_sessions',
            'error': str(e),
            'result_count': 0,
            'results': [],
            'is_relevant': False
        }


def get_session_overview(session_id: int) -> Dict[str, Any]:
    """
    Get comprehensive overview of a specific session.

    Args:
        session_id: The session device ID

    Returns:
        Session overview with topics, participants, and key info
    """
    logger.info(f"Getting session overview for: {session_id}")

    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get session info
        cursor.execute("""
            SELECT
                sd.id as session_device_id,
                sd.name as device_name,
                s.name as session_name
            FROM session_device sd
            JOIN session s ON s.id = sd.session_id
            WHERE sd.id = %s
        """, (session_id,))
        session_info = cursor.fetchone()

        if not session_info:
            cursor.close()
            connection.close()
            return {
                "tool_name": "get_session_overview",
                "error": f"Session {session_id} not found",
                "result_count": 0,
                "results": [],
                "is_relevant": False
            }

        # Get speakers
        cursor.execute("""
            SELECT DISTINCT s.id, s.alias
            FROM speaker s
            JOIN transcript t ON t.speaker_id = s.id
            WHERE t.session_device_id = %s
        """, (session_id,))
        speakers = cursor.fetchall()

        # Get transcript count and duration
        cursor.execute("""
            SELECT
                COUNT(*) as transcript_count,
                MAX(start_time + length) as duration
            FROM transcript
            WHERE session_device_id = %s
        """, (session_id,))
        transcript_stats = cursor.fetchone()

        # Get concept session info
        cursor.execute("""
            SELECT
                id,
                discourse_type,
                generation_status
            FROM concept_session
            WHERE session_device_id = %s
        """, (session_id,))
        concept_session = cursor.fetchone()

        # Get cluster themes if available
        clusters = []
        if concept_session:
            cursor.execute("""
                SELECT cluster_name, node_count
                FROM concept_cluster
                WHERE concept_session_id = %s
                ORDER BY node_count DESC
                LIMIT 5
            """, (concept_session['id'],))
            clusters = cursor.fetchall()

        cursor.close()
        connection.close()

        # Build overview
        overview = {
            "session_device_id": session_id,
            "session_name": session_info.get('session_name') or session_info.get('device_name'),
            "duration_seconds": transcript_stats.get('duration') if transcript_stats else None,
            "transcript_count": transcript_stats.get('transcript_count', 0) if transcript_stats else 0,
            "speakers": [s['alias'] for s in speakers] if speakers else [],
            "speaker_count": len(speakers) if speakers else 0,
            "discourse_type": concept_session.get('discourse_type') if concept_session else None,
            "has_concept_map": concept_session is not None,
            "main_themes": [c['cluster_name'] for c in clusters] if clusters else []
        }

        return {
            "tool_name": "get_session_overview",
            "result_count": 1,
            "results": [overview],
            "is_relevant": True
        }

    except Exception as e:
        logger.error(f"Session overview error: {e}")
        return {
            "tool_name": "get_session_overview",
            "error": str(e),
            "result_count": 0,
            "results": [],
            "is_relevant": False
        }


def get_collaboration_analysis(session_id: int) -> Dict[str, Any]:
    """
    Get 7C collaboration quality analysis for a session.

    Args:
        session_id: The session device ID

    Returns:
        7C dimensions with scores and explanations
    """
    import json as json_lib
    logger.info(f"Getting collaboration analysis for: {session_id}")

    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Get 7C analysis (stored as JSON in analysis_summary column)
        cursor.execute("""
            SELECT analysis_summary
            FROM seven_cs_analysis
            WHERE session_device_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (session_id,))
        row = cursor.fetchone()

        cursor.close()
        connection.close()

        if not row or not row.get('analysis_summary'):
            return {
                "tool_name": "get_collaboration_analysis",
                "error": f"No 7C analysis found for session {session_id}",
                "result_count": 0,
                "results": [],
                "is_relevant": False
            }

        # Parse the JSON analysis
        analysis = row['analysis_summary']
        if isinstance(analysis, str):
            analysis = json_lib.loads(analysis)

        # Format dimensions with descriptions
        dimension_descriptions = {
            "climate": "Psychological safety and supportive atmosphere",
            "communication": "Clarity, active listening, articulation",
            "contribution": "Balanced participation, equal voice",
            "conflict": "Constructive disagreement, productive debate",
            "context": "Shared understanding, common ground",
            "constructive": "Building on others' ideas",
            "compatibility": "Working style alignment"
        }

        dimensions = {}
        overall_score = 0
        for dim_name in ['climate', 'communication', 'contribution', 'conflict',
                         'context', 'constructive', 'compatibility']:
            dim_data = analysis.get(dim_name, {})
            score = dim_data.get('score', 0)
            overall_score += score
            dimensions[dim_name] = {
                "score": score,
                "explanation": dim_data.get('explanation', ''),
                "evidence": dim_data.get('evidence', []),
                "description": dimension_descriptions.get(dim_name, '')
            }

        overall_score = overall_score / 7 if dimensions else 0

        result = {
            "session_device_id": session_id,
            "overall_score": round(overall_score, 1),
            "dimensions": dimensions
        }

        return {
            "tool_name": "get_collaboration_analysis",
            "result_count": 1,
            "results": [result],
            "is_relevant": True
        }

    except Exception as e:
        logger.error(f"Collaboration analysis error: {e}")
        return {
            "tool_name": "get_collaboration_analysis",
            "error": str(e),
            "result_count": 0,
            "results": [],
            "is_relevant": False
        }


def compare_sessions(session_ids: List[int] = None) -> Dict[str, Any]:
    """
    Compare multiple sessions across dimensions.

    Args:
        session_ids: List of session IDs to compare. If None or empty,
                     compares ALL available sessions (useful for "best/highest" queries)

    Returns:
        Comparison across topics, metrics, and participation
    """
    # If no session_ids provided, get ALL sessions
    if not session_ids:
        logger.info("No session_ids provided - comparing ALL sessions")
        all_sessions = list_sessions()
        if all_sessions.get('results'):
            session_ids = [s['session_device_id'] for s in all_sessions['results']]
            logger.info(f"Found {len(session_ids)} sessions to compare: {session_ids}")
        else:
            return {
                "tool_name": "compare_sessions",
                "error": "Could not retrieve sessions for comparison",
                "result_count": 0,
                "results": [],
                "is_relevant": False
            }

    logger.info(f"Comparing sessions: {session_ids}")

    if len(session_ids) < 2:
        return {
            "tool_name": "compare_sessions",
            "error": "Need at least 2 sessions to compare",
            "result_count": 0,
            "results": [],
            "is_relevant": False
        }

    try:
        sessions = []
        for sid in session_ids[:10]:  # Max 10 sessions for comprehensive comparison
            overview = get_session_overview(sid)
            if overview.get('results'):
                sessions.append(overview['results'][0])

            analysis = get_collaboration_analysis(sid)
            if analysis.get('results') and sessions:
                sessions[-1]['collaboration'] = analysis['results'][0]

        if len(sessions) < 2:
            return {
                "tool_name": "compare_sessions",
                "error": "Could not retrieve enough sessions for comparison",
                "result_count": 0,
                "results": [],
                "is_relevant": False
            }

        # Build comparison
        comparison = {
            "sessions_compared": [s['session_device_id'] for s in sessions],
            "session_details": sessions,
            "summary": {
                "themes": {s['session_device_id']: s.get('main_themes', []) for s in sessions},
                "speaker_counts": {s['session_device_id']: s.get('speaker_count', 0) for s in sessions},
                "collaboration_scores": {
                    s['session_device_id']: s.get('collaboration', {}).get('overall_score', 0)
                    for s in sessions if s.get('collaboration')
                }
            }
        }

        return {
            "tool_name": "compare_sessions",
            "result_count": len(sessions),
            "results": [comparison],
            "is_relevant": True
        }

    except Exception as e:
        logger.error(f"Session comparison error: {e}")
        return {
            "tool_name": "compare_sessions",
            "error": str(e),
            "result_count": 0,
            "results": [],
            "is_relevant": False
        }


def analyze_speaker(
    speaker_name: str,
    session_ids: Optional[List[int]] = None,
    include_samples: bool = True,
    include_metrics: bool = True
) -> Dict[str, Any]:
    """
    Analyze a speaker's participation patterns with comprehensive profile.

    Returns a full SpeakerProfile structure for agent reasoning:
    - Session participation metrics
    - Communication style (LIWC-based)
    - Contribution types breakdown
    - Interaction patterns
    - Sample quotes for grounding
    - Reasoning hints

    Args:
        speaker_name: Name of the speaker to analyze
        session_ids: Optional list of sessions to limit analysis
        include_samples: Whether to include sample quotes
        include_metrics: Whether to include detailed LIWC metrics

    Returns:
        Comprehensive speaker profile
    """
    logger.info(f"Analyzing speaker: {speaker_name} (sessions={session_ids})")

    try:
        connection = _get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Find the speaker
        cursor.execute("""
            SELECT id, alias FROM speaker
            WHERE alias LIKE %s
            LIMIT 1
        """, (f"%{speaker_name}%",))
        speaker = cursor.fetchone()

        if not speaker:
            cursor.close()
            connection.close()
            return {
                "tool_name": "analyze_speaker",
                "error": f"Speaker '{speaker_name}' not found",
                "result_count": 0,
                "results": [],
                "is_relevant": False
            }

        speaker_id = speaker['id']
        speaker_alias = speaker['alias']

        # Build session filter
        session_filter = ""
        session_params = [speaker_id]
        if session_ids:
            placeholders = ','.join(['%s'] * len(session_ids))
            session_filter = f"AND t.session_device_id IN ({placeholders})"
            session_params.extend(session_ids)

        # === Session Participation ===
        cursor.execute(f"""
            SELECT
                COUNT(DISTINCT t.session_device_id) as total_sessions,
                COUNT(t.id) as total_utterances,
                SUM(t.word_count) as total_word_count,
                SUM(CASE WHEN t.question = 1 THEN 1 ELSE 0 END) as total_questions,
                AVG(t.word_count) as avg_utterance_length,
                GROUP_CONCAT(DISTINCT t.session_device_id) as session_ids_str
            FROM transcript t
            WHERE t.speaker_id = %s {session_filter}
        """, session_params)
        participation = cursor.fetchone() or {}

        session_participation = {
            "total_sessions": participation.get('total_sessions') or 0,
            "session_ids": [int(x) for x in (participation.get('session_ids_str') or '').split(',') if x],
            "total_utterances": participation.get('total_utterances') or 0,
            "total_word_count": participation.get('total_word_count') or 0,
            "total_questions_asked": participation.get('total_questions') or 0,
            "avg_utterance_length": round(float(participation.get('avg_utterance_length') or 0), 1)
        }

        # === Communication Style (LIWC metrics) ===
        communication_style = {}
        if include_metrics:
            cursor.execute(f"""
                SELECT
                    AVG(t.analytic_thinking_value) as avg_analytic,
                    AVG(t.clout_value) as avg_clout,
                    AVG(t.authenticity_value) as avg_authenticity,
                    AVG(t.emotional_tone_value) as avg_emotional_tone,
                    AVG(t.certainty_value) as avg_certainty
                FROM transcript t
                WHERE t.speaker_id = %s {session_filter}
            """, session_params)
            metrics = cursor.fetchone() or {}

            avg_analytic = round(float(metrics.get('avg_analytic') or 0), 1)
            avg_clout = round(float(metrics.get('avg_clout') or 0), 1)
            avg_authenticity = round(float(metrics.get('avg_authenticity') or 0), 1)
            avg_tone = round(float(metrics.get('avg_emotional_tone') or 0), 1)
            avg_certainty = round(float(metrics.get('avg_certainty') or 0), 1)

            # Generate style summary
            style_summary = _generate_style_summary(
                avg_analytic, avg_clout, avg_authenticity, avg_tone, avg_certainty
            )

            communication_style = {
                "avg_analytic_thinking": avg_analytic,
                "avg_clout": avg_clout,
                "avg_authenticity": avg_authenticity,
                "avg_emotional_tone": avg_tone,
                "avg_certainty": avg_certainty,
                "style_summary": style_summary
            }

        # === Contribution Types (from concept nodes) ===
        cursor.execute(f"""
            SELECT
                cn.node_type,
                COUNT(*) as count
            FROM concept_node cn
            JOIN concept_session cs ON cn.concept_session_id = cs.id
            WHERE cn.speaker_id = %s
            {'AND cs.session_device_id IN (' + ','.join(['%s'] * len(session_ids)) + ')' if session_ids else ''}
            GROUP BY cn.node_type
        """, [speaker_id] + (session_ids or []))
        contribution_rows = cursor.fetchall()

        contributions = {
            "questions": 0,
            "ideas": 0,
            "hypotheses": 0,
            "conclusions": 0,
            "examples": 0,
            "problems": 0,
            "solutions": 0,
            "concept_types_breakdown": {}
        }

        for row in contribution_rows:
            node_type = row['node_type']
            count = row['count']
            contributions["concept_types_breakdown"][node_type] = count

            # Map to high-level categories
            if node_type == 'question':
                contributions["questions"] += count
            elif node_type == 'idea':
                contributions["ideas"] += count
            elif node_type in ('hypothesis', 'uncertainty'):
                contributions["hypotheses"] += count
            elif node_type == 'conclusion':
                contributions["conclusions"] += count
            elif node_type == 'example':
                contributions["examples"] += count
            elif node_type == 'problem':
                contributions["problems"] += count
            elif node_type == 'solution':
                contributions["solutions"] += count

        # === Interaction Patterns ===
        # Calculate turn-taking balance (speaker's share of conversation)
        cursor.execute(f"""
            SELECT
                (SELECT COUNT(*) FROM transcript WHERE speaker_id = %s {session_filter.replace('t.', '')}) as speaker_utterances,
                (SELECT COUNT(*) FROM transcript WHERE session_device_id IN (
                    SELECT DISTINCT session_device_id FROM transcript WHERE speaker_id = %s {session_filter.replace('t.', '')}
                )) as total_utterances
        """, session_params + session_params)
        turn_data = cursor.fetchone() or {}

        speaker_utterances = turn_data.get('speaker_utterances') or 0
        total_utterances = turn_data.get('total_utterances') or 1
        turn_taking_balance = round(speaker_utterances / total_utterances * 100, 1) if total_utterances > 0 else 0

        interaction_patterns = {
            "turn_taking_balance": turn_taking_balance,
            "initiative_score": _calculate_initiative_score(contributions, session_participation),
            "engagement_level": "high" if session_participation["total_utterances"] > 20 else "medium" if session_participation["total_utterances"] > 10 else "low"
        }

        # === Sample Quotes ===
        sample_quotes = []
        if include_samples:
            cursor.execute(f"""
                SELECT
                    t.transcript as text,
                    t.start_time as timestamp,
                    t.session_device_id as session_id,
                    t.word_count,
                    t.question
                FROM transcript t
                WHERE t.speaker_id = %s {session_filter}
                AND t.word_count > 10
                ORDER BY t.word_count DESC
                LIMIT 5
            """, session_params)
            quotes = cursor.fetchall()

            for q in quotes:
                sample_quotes.append({
                    "text": q['text'][:300] + "..." if len(q['text']) > 300 else q['text'],
                    "timestamp": q['timestamp'],
                    "session_id": q['session_id'],
                    "word_count": q['word_count'],
                    "is_question": bool(q['question'])
                })

        # === Reasoning Hints ===
        reasoning_hints = _generate_reasoning_hints(
            session_participation, communication_style, contributions, interaction_patterns
        )

        cursor.close()
        connection.close()

        # Build complete speaker profile
        profile = {
            "speaker_alias": speaker_alias,
            "speaker_id": speaker_id,
            "session_participation": session_participation,
            "communication_style": communication_style,
            "contributions": contributions,
            "interaction_patterns": interaction_patterns,
            "sample_quotes": sample_quotes,
            "reasoning_hints": reasoning_hints
        }

        return {
            "tool_name": "analyze_speaker",
            "result_count": 1,
            "results": [profile],
            "is_relevant": True
        }

    except Exception as e:
        logger.error(f"Speaker analysis error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "tool_name": "analyze_speaker",
            "error": str(e),
            "result_count": 0,
            "results": [],
            "is_relevant": False
        }


def _generate_style_summary(
    analytic: float,
    clout: float,
    authenticity: float,
    tone: float,
    certainty: float
) -> str:
    """Generate a natural language summary of communication style."""
    traits = []

    # Analytic thinking
    if analytic >= 70:
        traits.append("highly analytical")
    elif analytic >= 50:
        traits.append("moderately analytical")
    elif analytic < 30:
        traits.append("narrative-focused")

    # Clout/confidence
    if clout >= 70:
        traits.append("confident and authoritative")
    elif clout >= 50:
        traits.append("self-assured")
    elif clout < 30:
        traits.append("tentative")

    # Authenticity
    if authenticity >= 70:
        traits.append("personally engaged")
    elif authenticity < 30:
        traits.append("formal and distanced")

    # Emotional tone
    if tone >= 70:
        traits.append("positive")
    elif tone < 30:
        traits.append("concerned or critical")

    # Certainty
    if certainty >= 70:
        traits.append("certain in assertions")
    elif certainty < 30:
        traits.append("exploratory and questioning")

    if not traits:
        return "Balanced communication style"

    return f"{', '.join(traits[:-1])}, and {traits[-1]}" if len(traits) > 1 else traits[0].capitalize()


def _calculate_initiative_score(contributions: Dict, participation: Dict) -> float:
    """Calculate initiative score based on contribution patterns."""
    # Questions and new ideas indicate initiative
    questions = contributions.get("questions", 0)
    ideas = contributions.get("ideas", 0)
    problems = contributions.get("problems", 0)

    initiative_contributions = questions + ideas + problems
    total_utterances = participation.get("total_utterances", 1)

    if total_utterances == 0:
        return 0.0

    # Normalize to 0-100 scale
    raw_score = (initiative_contributions / total_utterances) * 100
    return min(100, round(raw_score * 5, 1))  # Scale up since ratio is usually small


def _generate_reasoning_hints(
    participation: Dict,
    style: Dict,
    contributions: Dict,
    patterns: Dict
) -> Dict[str, Any]:
    """Generate reasoning hints for the agent."""
    strengths = []
    notable_patterns = []
    areas_of_focus = []

    # Identify strengths
    if contributions.get("questions", 0) > 5:
        strengths.append("Strong at asking probing questions")
    if contributions.get("ideas", 0) > 5:
        strengths.append("Prolific idea generator")
    if contributions.get("conclusions", 0) > 2:
        strengths.append("Good at synthesizing conclusions")
    if style.get("avg_analytic_thinking", 0) >= 70:
        strengths.append("Highly analytical thinker")
    if style.get("avg_clout", 0) >= 70:
        strengths.append("Confident communicator")
    if participation.get("total_questions_asked", 0) > 10:
        strengths.append("Inquisitive and curious")

    # Identify notable patterns
    if patterns.get("turn_taking_balance", 0) > 30:
        notable_patterns.append("Dominates conversation share")
    elif patterns.get("turn_taking_balance", 0) < 10:
        notable_patterns.append("Quieter participant, speaks less frequently")

    if style.get("avg_certainty", 0) < 30:
        notable_patterns.append("Often expresses uncertainty or explores ideas tentatively")

    if contributions.get("hypotheses", 0) > 3:
        notable_patterns.append("Frequently proposes hypotheses")

    if contributions.get("examples", 0) > 3:
        notable_patterns.append("Uses examples to illustrate points")

    # Identify areas of focus (from contribution types)
    breakdown = contributions.get("concept_types_breakdown", {})
    if breakdown:
        sorted_types = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
        areas_of_focus = [f"{t[0]}s" for t in sorted_types[:3]]

    return {
        "strengths": strengths[:4] if strengths else ["Active participant"],
        "notable_patterns": notable_patterns[:3] if notable_patterns else ["Standard participation pattern"],
        "areas_of_focus": areas_of_focus if areas_of_focus else ["General discussion topics"]
    }


def get_speaker_session_profile(
    speaker_name: str,
    session_id: int
) -> Dict[str, Any]:
    """
    Get speaker profile specific to one session.

    Useful for questions like:
    - "How did Tucker participate in session 19?"
    - "What was David's role in the fusion discussion?"

    Args:
        speaker_name: Name of the speaker
        session_id: Session to analyze

    Returns:
        Session-specific speaker profile
    """
    return analyze_speaker(
        speaker_name=speaker_name,
        session_ids=[session_id],
        include_samples=True,
        include_metrics=True
    )


def compare_speakers(
    speaker_names: List[str],
    session_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Compare multiple speakers' participation patterns.

    Args:
        speaker_names: List of speaker names to compare (2-5)
        session_id: Optional session to limit comparison

    Returns:
        Comparative analysis of speakers
    """
    logger.info(f"Comparing speakers: {speaker_names} (session={session_id})")

    if len(speaker_names) < 2:
        return {
            "tool_name": "compare_speakers",
            "error": "Need at least 2 speakers to compare",
            "result_count": 0,
            "results": [],
            "is_relevant": False
        }

    try:
        profiles = []
        session_filter = [session_id] if session_id else None

        for name in speaker_names[:5]:  # Max 5 speakers
            result = analyze_speaker(name, session_ids=session_filter)
            if result.get('results'):
                profiles.append(result['results'][0])

        if len(profiles) < 2:
            return {
                "tool_name": "compare_speakers",
                "error": "Could not find enough speakers for comparison",
                "result_count": 0,
                "results": [],
                "is_relevant": False
            }

        # Build comparison
        comparison = {
            "speakers_compared": [p['speaker_alias'] for p in profiles],
            "session_scope": session_id if session_id else "all sessions",
            "profiles": profiles,
            "comparison_summary": {
                "participation": {
                    p['speaker_alias']: {
                        "utterances": p['session_participation']['total_utterances'],
                        "word_count": p['session_participation']['total_word_count'],
                        "questions": p['session_participation']['total_questions_asked']
                    }
                    for p in profiles
                },
                "communication_styles": {
                    p['speaker_alias']: p['communication_style'].get('style_summary', 'Unknown')
                    for p in profiles
                },
                "top_contributions": {
                    p['speaker_alias']: [
                        k for k, v in sorted(
                            p['contributions']['concept_types_breakdown'].items(),
                            key=lambda x: x[1], reverse=True
                        )[:3]
                    ]
                    for p in profiles
                }
            }
        }

        return {
            "tool_name": "compare_speakers",
            "result_count": len(profiles),
            "results": [comparison],
            "is_relevant": True
        }

    except Exception as e:
        logger.error(f"Speaker comparison error: {e}")
        return {
            "tool_name": "compare_speakers",
            "error": str(e),
            "result_count": 0,
            "results": [],
            "is_relevant": False
        }


# =============================================================================
# Hypothesis Testing Tools (Co-Discovery)
# =============================================================================

def test_hypothesis(
    hypothesis: str,
    session_ids: Optional[List[int]] = None,
    include_counter_evidence: bool = True
) -> Dict[str, Any]:
    """
    Systematically test a hypothesis across available evidence.

    This tool supports hypothesis-driven inquiry where users propose claims
    that the agent tests systematically across multiple representations.

    Args:
        hypothesis: The claim to test (e.g., "Tucker demonstrates systems thinking")
        session_ids: Optional list of sessions to search (default: all)
        include_counter_evidence: Whether to actively search for disconfirming evidence

    Returns:
        Structured assessment with supporting/countering evidence and confidence
    """
    import re
    from .artifact_tools import search_for_sessions, get_transcript, get_7c_analysis

    logger.info(f"[test_hypothesis] Testing: '{hypothesis[:80]}...'")

    results = {
        'tool_name': 'test_hypothesis',
        'hypothesis': hypothesis,
        'supporting_evidence': [],
        'countering_evidence': [],
        'neutral_evidence': [],
        'confidence': 0.0,
        'verdict': 'insufficient_evidence',  # supported, refuted, mixed, insufficient_evidence
        'sessions_examined': [],
        'is_relevant': True
    }

    try:
        # Step 1: Find relevant sessions
        if session_ids:
            sessions_to_check = session_ids
            logger.info(f"[test_hypothesis] Using specified sessions: {session_ids}")
        else:
            # Use semantic search to find relevant sessions
            search_result = search_for_sessions(hypothesis, top_k=5)
            sessions_to_check = [s['session_id'] for s in search_result.get('sessions', [])]
            logger.info(f"[test_hypothesis] Found {len(sessions_to_check)} relevant sessions via search")

        results['sessions_examined'] = sessions_to_check

        if not sessions_to_check:
            logger.warning("[test_hypothesis] No sessions found to examine")
            return results

        # Step 2: Gather evidence from each session
        for session_id in sessions_to_check:
            try:
                # Get transcript for direct quotes
                transcript = get_transcript(session_id)
                if transcript.get('artifact'):
                    utterances = transcript['artifact'].get('utterances', [])
                    for utt in utterances[:50]:  # Limit for performance
                        text = utt.get('text', '')
                        speaker = utt.get('speaker_tag', 'Unknown')

                        if _is_relevant_to_hypothesis(text, hypothesis):
                            evidence_item = {
                                'session_id': session_id,
                                'speaker': speaker,
                                'text': text[:300],
                                'source': 'transcript',
                                'relevance': 'supporting'  # Default - could be enhanced with sentiment
                            }
                            results['supporting_evidence'].append(evidence_item)

                # Get 7C for collaboration-related hypotheses
                collab_terms = ['collaborat', 'communicat', 'conflict', 'engage', 'participat', 'interact']
                if any(term in hypothesis.lower() for term in collab_terms):
                    seven_c = get_7c_analysis(session_id)
                    if seven_c.get('artifact'):
                        dims = seven_c['artifact'].get('dimensions', {})
                        overall = seven_c['artifact'].get('overall_score', 0)
                        evidence_item = {
                            'session_id': session_id,
                            'overall_score': overall,
                            'dimensions': {k: v.get('score', 0) for k, v in dims.items()},
                            'source': '7c_analysis',
                            'relevance': 'supporting' if overall > 60 else 'countering'
                        }
                        if evidence_item['relevance'] == 'supporting':
                            results['supporting_evidence'].append(evidence_item)
                        else:
                            results['countering_evidence'].append(evidence_item)

            except Exception as e:
                logger.warning(f"[test_hypothesis] Error examining session {session_id}: {e}")

        # Step 3: Calculate confidence and verdict
        sup_count = len(results['supporting_evidence'])
        counter_count = len(results['countering_evidence'])

        logger.info(f"[test_hypothesis] Evidence: {sup_count} supporting, {counter_count} countering")

        if sup_count == 0 and counter_count == 0:
            results['confidence'] = 0.0
            results['verdict'] = 'insufficient_evidence'
        elif counter_count == 0 and sup_count > 0:
            results['confidence'] = min(0.9, 0.3 + sup_count * 0.1)  # Cap at 0.9
            results['verdict'] = 'supported'
        elif sup_count == 0 and counter_count > 0:
            results['confidence'] = min(0.9, 0.3 + counter_count * 0.1)
            results['verdict'] = 'refuted'
        else:
            ratio = sup_count / (sup_count + counter_count)
            results['confidence'] = 0.4 + (ratio - 0.5) * 0.4  # Range: 0.2-0.6 for mixed
            results['verdict'] = 'mixed'

        results['result_count'] = sup_count + counter_count

        logger.info(f"[test_hypothesis] Verdict: {results['verdict']} (confidence: {results['confidence']:.2f})")

        return results

    except Exception as e:
        logger.error(f"[test_hypothesis] Error: {e}")
        return {
            'tool_name': 'test_hypothesis',
            'hypothesis': hypothesis,
            'error': str(e),
            'supporting_evidence': [],
            'countering_evidence': [],
            'confidence': 0.0,
            'verdict': 'error',
            'sessions_examined': [],
            'result_count': 0,
            'is_relevant': False
        }


def _is_relevant_to_hypothesis(text: str, hypothesis: str) -> bool:
    """
    Check if a piece of text is relevant to a hypothesis.

    Uses simple term matching - could be enhanced with embeddings for better accuracy.
    """
    import re

    # Extract key terms from hypothesis (words with 4+ characters)
    key_terms = re.findall(r'\b\w{4,}\b', hypothesis.lower())

    # Remove common stop words
    stop_words = {'that', 'this', 'with', 'from', 'have', 'were', 'been', 'being', 'does', 'about'}
    key_terms = [t for t in key_terms if t not in stop_words]

    if not key_terms:
        return False

    text_lower = text.lower()

    # Check if at least 2 key terms appear (or 1 if hypothesis is short)
    min_matches = 2 if len(key_terms) > 2 else 1
    matches = sum(1 for term in key_terms if term in text_lower)

    return matches >= min_matches
