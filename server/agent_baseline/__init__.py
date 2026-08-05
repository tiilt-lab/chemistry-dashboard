"""
BLINC Agent Baseline - Transcript-Only Variant

A baseline agent with access to only transcript data for fair comparison with V7.
Uses the same ReAct architecture and prompting style, but with restricted tools.

Tools available:
- list_sessions: List sessions (no collaboration scores)
- search_sessions: Semantic search on transcript collection only
- get_transcript: Get session transcript
- get_speaker_profile: Psycholinguistic metrics only (no concept data)
"""
