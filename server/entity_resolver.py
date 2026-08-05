"""
Entity Resolver for Artifact-Grounded RAG

Resolves natural language references to database entities:
- Session names → session_device_id
- Speaker aliases → speaker records

Uses multiple resolution strategies:
1. Exact match
2. Case-insensitive match
3. Fuzzy match (Levenshtein distance)
4. Semantic search fallback
"""

import logging
import re
from typing import Optional, List, Dict, Tuple, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class EntityResolver:
    """
    Resolves natural language entity references to database IDs.
    """

    def __init__(self, rag_service=None):
        """
        Initialize the entity resolver.

        Args:
            rag_service: Optional RAG service for semantic search fallback
        """
        self.rag = rag_service
        self._session_cache = None
        self._speaker_cache = None

    def _get_all_sessions(self) -> List[Dict]:
        """Get all sessions with their names and device IDs."""
        if self._session_cache is not None:
            return self._session_cache

        try:
            from tables.session import Session
            from tables.session_device import SessionDevice

            sessions = []
            for session in Session.query.all():
                # Get the first session_device for this session
                sd = SessionDevice.query.filter_by(session_id=session.id).first()
                if sd:
                    sessions.append({
                        'session_id': session.id,
                        'session_device_id': sd.id,
                        'name': session.name or f"Session {session.id}",
                        'name_lower': (session.name or f"Session {session.id}").lower()
                    })
            self._session_cache = sessions
            return sessions
        except Exception as e:
            logger.error(f"Error fetching sessions: {e}")
            return []

    def _get_all_speakers(self) -> List[Dict]:
        """Get all unique speaker aliases across all sessions."""
        if self._speaker_cache is not None:
            return self._speaker_cache

        try:
            from tables.speaker import Speaker

            speakers = []
            seen_aliases = set()
            for speaker in Speaker.query.all():
                alias = speaker.alias or f"Speaker {speaker.id}"
                alias_lower = alias.lower()
                if alias_lower not in seen_aliases:
                    speakers.append({
                        'speaker_id': speaker.id,
                        'alias': alias,
                        'alias_lower': alias_lower,
                        'session_device_id': speaker.session_device_id
                    })
                    seen_aliases.add(alias_lower)
            self._speaker_cache = speakers
            return speakers
        except Exception as e:
            logger.error(f"Error fetching speakers: {e}")
            return []

    def clear_cache(self):
        """Clear cached entities (call after data changes)."""
        self._session_cache = None
        self._speaker_cache = None

    def resolve_session(self, reference: str, threshold: float = 0.6) -> Optional[Dict]:
        """
        Resolve a session reference to session_device_id.

        Args:
            reference: Natural language reference (e.g., "Carlson Show", "session 5")
            threshold: Minimum similarity score for fuzzy matching (0-1)

        Returns:
            Dict with 'session_device_id', 'name', 'confidence', 'match_type' or None
        """
        reference = reference.strip()
        reference_lower = reference.lower()

        logger.info(f"Resolving session reference: '{reference}'")

        # Strategy 1: Check for explicit ID pattern (session 5, device 12)
        session_id_match = re.search(r'session\s*(\d+)', reference_lower)
        device_id_match = re.search(r'device\s*(\d+)', reference_lower)

        if device_id_match:
            device_id = int(device_id_match.group(1))
            return {
                'session_device_id': device_id,
                'name': f"Device {device_id}",
                'confidence': 1.0,
                'match_type': 'explicit_device_id'
            }

        if session_id_match:
            session_id = int(session_id_match.group(1))
            # Get session_device_id for this session
            try:
                from tables.session_device import SessionDevice
                sd = SessionDevice.query.filter_by(session_id=session_id).first()
                if sd:
                    return {
                        'session_device_id': sd.id,
                        'name': f"Session {session_id}",
                        'confidence': 1.0,
                        'match_type': 'explicit_session_id'
                    }
            except Exception as e:
                logger.warning(f"Error looking up session {session_id}: {e}")

        # Strategy 2: Name matching
        sessions = self._get_all_sessions()
        if not sessions:
            logger.warning("No sessions found in database")
            return None

        # 2a: Exact match
        for session in sessions:
            if session['name_lower'] == reference_lower:
                logger.info(f"Exact match found: {session['name']}")
                return {
                    'session_device_id': session['session_device_id'],
                    'name': session['name'],
                    'confidence': 1.0,
                    'match_type': 'exact'
                }

        # 2b: Substring match (reference in name or name in reference)
        for session in sessions:
            if reference_lower in session['name_lower'] or session['name_lower'] in reference_lower:
                logger.info(f"Substring match found: {session['name']}")
                return {
                    'session_device_id': session['session_device_id'],
                    'name': session['name'],
                    'confidence': 0.9,
                    'match_type': 'substring'
                }

        # 2c: Fuzzy match using SequenceMatcher
        best_match = None
        best_score = 0

        for session in sessions:
            # Compare against full name
            score = SequenceMatcher(None, reference_lower, session['name_lower']).ratio()

            # Also try matching individual words
            ref_words = set(reference_lower.split())
            name_words = set(session['name_lower'].split())
            word_overlap = len(ref_words & name_words) / max(len(ref_words), 1)

            # Combined score
            combined_score = max(score, word_overlap * 0.9)

            if combined_score > best_score:
                best_score = combined_score
                best_match = session

        if best_match and best_score >= threshold:
            logger.info(f"Fuzzy match found: {best_match['name']} (score: {best_score:.2f})")
            return {
                'session_device_id': best_match['session_device_id'],
                'name': best_match['name'],
                'confidence': best_score,
                'match_type': 'fuzzy'
            }

        # Strategy 3: Semantic search fallback (if RAG service available)
        if self.rag:
            try:
                results = self.rag.search_transcripts(reference, n_results=1)
                if results.get('results'):
                    best = results['results'][0]
                    distance = best.get('distance', 1.0)
                    if distance < 0.5:  # Good semantic match
                        session_device_id = best.get('session_device_id')
                        logger.info(f"Semantic match found: session_device_id={session_device_id}")
                        return {
                            'session_device_id': session_device_id,
                            'name': f"Session {session_device_id}",
                            'confidence': 1 - distance,
                            'match_type': 'semantic'
                        }
            except Exception as e:
                logger.warning(f"Semantic search fallback failed: {e}")

        logger.warning(f"No match found for session reference: '{reference}'")
        return None

    def resolve_speaker(self, reference: str, threshold: float = 0.6) -> Optional[Dict]:
        """
        Resolve a speaker reference to speaker info.

        Args:
            reference: Natural language reference (e.g., "David", "Lex")
            threshold: Minimum similarity score for fuzzy matching (0-1)

        Returns:
            Dict with 'alias', 'speaker_ids', 'confidence', 'match_type' or None
        """
        reference = reference.strip()
        reference_lower = reference.lower()

        logger.info(f"Resolving speaker reference: '{reference}'")

        speakers = self._get_all_speakers()
        if not speakers:
            logger.warning("No speakers found in database")
            return None

        # Strategy 1: Exact match
        matching_speakers = [s for s in speakers if s['alias_lower'] == reference_lower]
        if matching_speakers:
            logger.info(f"Exact speaker match found: {matching_speakers[0]['alias']}")
            return {
                'alias': matching_speakers[0]['alias'],
                'speaker_ids': [s['speaker_id'] for s in matching_speakers],
                'confidence': 1.0,
                'match_type': 'exact'
            }

        # Strategy 2: Prefix match (for abbreviated names)
        for speaker in speakers:
            if speaker['alias_lower'].startswith(reference_lower) or reference_lower.startswith(speaker['alias_lower']):
                logger.info(f"Prefix match found: {speaker['alias']}")
                return {
                    'alias': speaker['alias'],
                    'speaker_ids': [speaker['speaker_id']],
                    'confidence': 0.9,
                    'match_type': 'prefix'
                }

        # Strategy 3: Fuzzy match
        best_match = None
        best_score = 0

        for speaker in speakers:
            score = SequenceMatcher(None, reference_lower, speaker['alias_lower']).ratio()
            if score > best_score:
                best_score = score
                best_match = speaker

        if best_match and best_score >= threshold:
            logger.info(f"Fuzzy speaker match found: {best_match['alias']} (score: {best_score:.2f})")
            return {
                'alias': best_match['alias'],
                'speaker_ids': [best_match['speaker_id']],
                'confidence': best_score,
                'match_type': 'fuzzy'
            }

        logger.warning(f"No match found for speaker reference: '{reference}'")
        return None

    def resolve_entities_in_query(self, query: str) -> Dict[str, Any]:
        """
        Find and resolve all entity references in a query.

        Args:
            query: Natural language query

        Returns:
            Dict with 'sessions' and 'speakers' lists of resolved entities
        """
        result = {
            'sessions': [],
            'speakers': [],
            'original_query': query
        }

        query_lower = query.lower()

        # Get all known entities
        sessions = self._get_all_sessions()
        speakers = self._get_all_speakers()

        # Find session name mentions
        for session in sessions:
            name_lower = session['name_lower']
            # Check if session name appears in query (case-insensitive)
            if len(name_lower) > 3 and name_lower in query_lower:
                resolved = self.resolve_session(session['name'])
                if resolved and resolved not in result['sessions']:
                    result['sessions'].append(resolved)

        # Find speaker mentions
        for speaker in speakers:
            alias_lower = speaker['alias_lower']
            # Check if speaker alias appears in query (word boundary)
            if len(alias_lower) > 2:
                pattern = r'\b' + re.escape(alias_lower) + r'\b'
                if re.search(pattern, query_lower):
                    resolved = self.resolve_speaker(speaker['alias'])
                    if resolved and resolved not in result['speakers']:
                        result['speakers'].append(resolved)

        return result

    def get_available_sessions(self) -> List[str]:
        """Return list of all session names for UI display."""
        sessions = self._get_all_sessions()
        return [s['name'] for s in sessions]

    def get_available_speakers(self) -> List[str]:
        """Return list of all speaker aliases for UI display."""
        speakers = self._get_all_speakers()
        return list(set(s['alias'] for s in speakers))
