"""
Tool Descriptions for BLINC Agent V3

8-TOOL ARTIFACT-CENTRIC DESIGN
==============================
Discovery:
1. list_sessions       - Discovery: what sessions exist
2. search_for_sessions - Discovery: find sessions by topic

Artifact Retrieval (separate tools, clearer intent):
3. get_transcript      - Get full transcript with per-utterance LIWC
4. get_concept_map     - Get concept graph (nodes, edges, clusters, patterns)
5. get_7c_analysis     - Get 7C collaboration dimensions
6. get_liwc_metrics    - Get LIWC linguistic metrics (session/speaker, timeseries)

Speaker & Graph:
7. get_speaker_profile - Complete speaker view with graph connections
8. find_concept_path   - Graph reasoning (algorithmic traversal)

Legacy:
- get_artifacts        - Combined artifact retrieval (prefer separate tools above)
- synthesize           - Cross-rep synthesis (done by synthesis node now)

These descriptions follow OpenAI's best practices:
- Define WHEN the tool should be invoked
- Define HOW arguments should be constructed
- Provide clear examples
- Explain what NOT to use the tool for
"""

TOOL_DESCRIPTIONS = {

    # =========================================================================
    # OPTIMAL 6-TOOL DESIGN (Primary tools to use)
    # =========================================================================

    "list_sessions": {
        "description": """
List all available sessions with metadata.

USE THIS FIRST to understand what data exists before retrieving artifacts.

WHEN TO USE:
- "What sessions are available?"
- "Show me all sessions"
- Starting point for any query when you don't know which sessions exist
- Before calling get_artifacts() to find valid session IDs

RETURNS: All sessions with:
- session_id, session_name, discourse_type
- speakers list
- artifacts_available (which of transcript/concept_map/collaboration exist)
""",
        "parameters": {}
    },

    "search_for_sessions": {
        "description": """
Find sessions relevant to a query using semantic search.

WHEN TO USE:
- "Which sessions discussed AI/fusion/collaboration?"
- Finding sessions about a specific topic
- Cross-session thematic search
- Don't know which sessions might be relevant

AFTER THIS: Use get_transcript/get_concept_map/get_7c_analysis to get full data

RETURNS: Ranked list of relevant sessions with match scores and previews
""",
        "parameters": {
            "query": "What to search for (topic, theme, keyword)",
            "top_k": "Number of sessions to return (default 3)"
        }
    },

    # =========================================================================
    # ARTIFACT RETRIEVAL TOOLS (Separate, Clearer Intent)
    # =========================================================================

    "get_transcript": {
        "description": """
Get complete transcript for a session with per-utterance LIWC scores.

WHEN TO USE:
- "What was said in session X?"
- "Show me the discussion transcript"
- Need to see WHAT was said and HOW (linguistic style)
- Looking for specific quotes or statements

PREFER THIS OVER get_artifacts when you only need transcript data.

RETURNS:
- summary: total utterances, words, questions, avg LIWC scores
- speaker_profiles: per-speaker statistics
- utterances: full transcript with timestamps and LIWC scores per utterance
""",
        "parameters": {
            "session_id": "The session ID to get transcript for"
        }
    },

    "get_concept_map": {
        "description": """
Get concept map with nodes, edges, clusters, reasoning patterns, AND GRAPH STATISTICS.

MANDATORY - USE THIS TOOL FOR:
- "What ideas emerged in session X?"
- "How are ideas connected in this discussion?"
- "What were the main themes?"
- "Show me how concepts relate"
- Understanding the STRUCTURE of ideas (not just content)
- Question density, idea distribution by speaker

USE INSTEAD OF get_artifacts when you only need concept map data.

TIP: After getting the concept map, use find_concept_path to trace specific connections.

RETURNS (IMPORTANT - USE ALL OF THESE):
- summary.node_types: COUNT of each type (question, idea, problem, solution, hypothesis, etc.)
  → Use for "question density" = questions / total_nodes
  → Use for "idea distribution" = ideas / total_nodes
- summary.speaker_contributions: WHO contributed WHAT types
  → Example: "David": {"total": 12, "by_type": {"idea": 8, "question": 3, "problem": 1}}
  → Use to see idea distribution BY SPEAKER
- summary.total_nodes, summary.total_edges: Graph size metrics
- nodes: All concept nodes with text, type, speaker
- edges: All relationships between concepts (leads_to, supports, challenges)
- clusters: Thematic groupings with summaries
- hub_nodes: Most connected concepts (key ideas) with connection counts
- reasoning_patterns: Detected patterns (causal_chains, hypothesis_testing, etc.)

EXAMPLE: For "question density in session 20":
1. get_concept_map(session_id=20)
2. Extract summary.node_types → {"question": 3, "idea": 15, "problem": 5, ...}
3. Calculate: question_density = 3 / (3+15+5+...) = 3/23 = 13%

EXAMPLE: For "idea distribution by speaker":
1. get_concept_map(session_id=20)
2. Extract summary.speaker_contributions
3. Report: "David contributed 15 ideas (65%), Lex contributed 8 ideas (35%)"
""",
        "parameters": {
            "session_id": "The session ID to get concept map for"
        }
    },

    "get_7c_analysis": {
        "description": """
Get 7C collaboration analysis with SCORES AND SPECIFIC EVIDENCE.

WHEN TO USE:
- "How well did they collaborate?"
- "Was the discussion productive?"
- "Did they build on each other's ideas?" → constructive dimension
- "Was there disagreement?" → conflict dimension
- "Did everyone participate?" → contribution dimension
- "Was the discussion psychologically safe?" → climate dimension

7 DIMENSIONS - USE THE RIGHT ONE FOR THE QUESTION:
- climate: Psychological safety, supportive atmosphere → "Did they feel safe sharing?"
- communication: Clarity, active listening → "Did they understand each other?"
- contribution: Balanced participation → "Did everyone participate equally?"
- conflict: Constructive disagreement handling → "How did they handle disagreements?"
- context: Shared understanding → "Did they build common ground?"
- constructive: Building on others' ideas → "Did they extend each other's points?"
- compatibility: Working style alignment → "Did their styles mesh?"

RETURNS (IMPORTANT - USE coded_segments FOR EVIDENCE):
- dimensions[dim_name].score: 0-100 score
- dimensions[dim_name].explanation: Why this score
- dimensions[dim_name].coded_segments: SPECIFIC EVIDENCE from the discussion!
  → These are actual quotes/moments that support the score
  → CITE THESE in your answer, not just the score number!
- dimensions[dim_name].keywords_detected: Key terms found

EXAMPLE: For "Was there constructive conflict?":
1. get_7c_analysis(session_id=19)
2. Check dimensions.conflict.score AND dimensions.conflict.coded_segments
3. Report: "Conflict score: 60/100. Evidence: [cite specific coded_segments]"
""",
        "parameters": {
            "session_id": "The session ID to get 7C analysis for"
        }
    },

    "get_liwc_metrics": {
        "description": """
Get LIWC linguistic metrics for a session or speaker.

Data source: Real LIWC scores per utterance (not LLM-generated).

WHEN TO USE:
- "What's the linguistic style in session X?"
- "How analytical was the discussion?"
- "Compare speakers' communication styles"
- Need LINGUISTIC STYLE and THINKING PATTERNS analysis

5 Dimensions (0-100 scale):
- emotional_tone: Positive vs negative expression
- analytic_thinking: Logical, formal reasoning
- clout: Confidence and social dominance
- authenticity: Personal, honest expression
- certainty: Conviction and definitiveness

Args:
- session_id: Session to analyze
- speaker: Optional speaker name to filter
- include_timeseries: If True, get full time series data

RETURNS:
- session_summary: aggregated stats (avg, min, max, std)
- speaker_breakdown: per-speaker LIWC profiles
- timeseries: time-ordered data (if requested)
""",
        "parameters": {
            "session_id": "The session ID to analyze",
            "speaker": "Optional: Speaker name to filter",
            "include_timeseries": "Optional: True to get full time series"
        }
    },

    # =========================================================================
    # LEGACY COMBINED ARTIFACT TOOL
    # =========================================================================

    "get_artifacts": {
        "description": """
LEGACY: Combined artifact retrieval. Prefer the separate tools above:
- get_transcript - for transcript data
- get_concept_map - for concept graph data
- get_7c_analysis - for collaboration metrics
- get_liwc_metrics - for LIWC linguistic analysis

WHEN TO USE:
- When you need ALL artifacts at once (transcript + concept_map + collaboration)
- "Tell me about the discussion" (holistic view)

Args:
- session_id: The session to retrieve
- include: List of artifacts to include (default: all three)
  - 'transcript': Full transcript with all utterances
  - 'concept_map': Complete graph with nodes, edges, clusters
  - 'collaboration': 7C analysis with scores and evidence

RETURNS: Complete artifacts bundle
""",
        "parameters": {
            "session_id": "The session ID to get artifacts for",
            "include": "List of artifacts: ['transcript', 'concept_map', 'collaboration']"
        }
    },

    "get_speaker_profile": {
        "description": """
Get complete profile for a speaker across all representations.

WHEN TO USE:
- "How did [Name] participate?"
- "What did [Name] contribute?"
- "Who did [Name] interact with?"
- Understanding a speaker's ideas and how they connect to others

PREFER THIS OVER deprecated tools (analyze_speaker, get_speaker_artifacts)

RETURNS:
- Transcript summary: utterances, questions, analytic/certainty scores, sample quotes
- Concept summary: concepts contributed by type, with GRAPH CONNECTIONS
  - Outgoing: ideas this speaker influenced
  - Incoming: ideas that influenced this speaker
  - Which other speakers they connected to/from

This shows HOW a speaker's ideas connected to others, not just WHAT they said.
""",
        "parameters": {
            "speaker_name": "Name of the speaker (e.g., 'Lex', 'Tucker')",
            "session_id": "Optional: limit to specific session (None = all sessions)"
        }
    },

    "synthesize": {
        "description": """
THE KEY SYNTHESIS TOOL. Cross-rep AND/OR cross-session synthesis.

WHEN TO USE:
- Reasoning ACROSS representations holistically
- Comparing patterns across multiple sessions
- Finding convergences (same insight in multiple sources)
- Surfacing discrepancies (conflicting signals)
- "Compare the Nuclear Fusion and AI Alive sessions"
- "How did collaboration quality relate to idea generation?"

SUPPORTS:
1. Single-session cross-rep synthesis: synthesize(20, "How did they collaborate?")
2. Multi-session synthesis: synthesize([19, 20, 21], "Compare collaboration quality")
3. Both: Compare across sessions AND across representations

RETURNS:
- Insights from each representation (transcript, concept_map, collaboration)
- Cross-rep patterns (convergences, complementary, discrepancies)
- Cross-session patterns (similarities, differences, best performer)
- Citations from each layer
- Integrated summary narrative

PREFER THIS OVER:
- synthesize_cross_representation (deprecated, single-session only)
- cross_reference_claim (deprecated, subsumed by this)
- compare_sessions (this does more)
""",
        "parameters": {
            "session_ids": "Single int or list of session IDs",
            "question": "The question/focus for synthesis",
            "focus": "Optional focus (speaker name, topic)"
        }
    },

    "find_concept_path": {
        "description": """
Find reasoning path between two concepts in a session's concept map.

MANDATORY - USE THIS TOOL FOR:
- "How did they get from [idea A] to [idea B]?"
- "What's the connection between X and Y?"
- "How did the discussion evolve from X to Y?"
- "Trace the reasoning from [start] to [conclusion]"
- Any query asking about connections, paths, or reasoning chains between ideas

KEY ADVANTAGE:
- Uses FUZZY TEXT MATCHING - you don't need exact concept text or IDs
- Just provide approximate concept descriptions (e.g., "fusion" matches "nuclear fusion energy")
- Does BFS graph traversal automatically - don't try to trace paths manually!

EXAMPLES:
- find_concept_path(session_id=20, from_concept="fusion", to_concept="energy")
- find_concept_path(session_id=19, from_concept="AI reasoning", to_concept="consciousness")

RETURNS: The complete path showing each step's relationship type and how ideas connect.
""",
        "parameters": {
            "session_id": "The session to search in",
            "from_concept": "Text of starting concept (fuzzy matched - approximate is OK)",
            "to_concept": "Text of target concept (fuzzy matched - approximate is OK)",
            "max_depth": "Maximum path length (default 5)"
        }
    },

    # =========================================================================
    # REASONING TOOLS
    # =========================================================================

    "think": {
        "description": """
Use this tool to think through complex problems step by step.

WHEN TO USE:
- The query requires multi-step reasoning
- You need to analyze information from previous tool results
- You're deciding between multiple possible approaches
- The situation is ambiguous and needs careful consideration
- You need to synthesize information from multiple sources

WHEN NOT TO USE:
- Simple factual queries that can be answered directly
- When you already know exactly which tool to use

HOW TO USE:
- Write out your reasoning process clearly
- Consider multiple angles
- Identify what information you still need
- Plan your next steps

The thought will be recorded for transparency but not shown to the user.
""",
        "parameters": {
            "reasoning": "Your step-by-step reasoning process"
        }
    },

    "clarify": {
        "description": """
Ask the user for clarification when the query is genuinely ambiguous.

WHEN TO USE:
- The query references "the session" or "that discussion" with NO context
- Multiple very different interpretations are equally valid
- Critical information is missing that prevents any useful response

WHEN NOT TO USE (IMPORTANT - default to NOT clarifying):
- You can make a reasonable assumption and search
- The query mentions any specific topic, name, or identifier
- You have session context from the conversation
- A search would likely find relevant results anyway
- The query is general (e.g., "what topics were discussed?") - just search all

PRINCIPLE: When in doubt, SEARCH rather than ask. Users prefer results over questions.
""",
        "parameters": {
            "question": "A clear, specific question to ask the user",
            "options": "2-4 specific options the user can choose from"
        }
    },

    # =========================================================================
    # DEPRECATED ARTIFACT TOOLS (kept for backward compatibility)
    # Use get_artifacts() instead
    # =========================================================================

    "get_transcript_artifact": {
        "description": """
DEPRECATED: Use get_artifacts(session_id, include=['transcript']) instead.

This tool delegates to get_artifacts internally.
""",
        "parameters": {
            "session_id": "The session ID to get transcript for"
        }
    },

    "get_concept_map_artifact": {
        "description": """
DEPRECATED: Use get_artifacts(session_id, include=['concept_map']) instead.

This tool delegates to get_artifacts internally.
""",
        "parameters": {
            "session_id": "The session ID to get concept map for"
        }
    },

    "get_collaboration_artifact": {
        "description": """
DEPRECATED: Use get_artifacts(session_id, include=['collaboration']) instead.

This tool delegates to get_artifacts internally.
""",
        "parameters": {
            "session_id": "The session ID to get 7C analysis for"
        }
    },

    "get_speaker_artifacts": {
        "description": """
DEPRECATED: Use get_speaker_profile() instead.

This tool delegates to get_speaker_profile internally.
""",
        "parameters": {
            "speaker_name": "Name of the speaker",
            "session_id": "Optional: limit to specific session"
        }
    },

    "cross_reference_claim": {
        "description": """
DEPRECATED: Use synthesize(session_id, claim) instead.

This tool delegates to synthesize internally.
""",
        "parameters": {
            "session_id": "The session to check",
            "claim": "The claim to verify"
        }
    },

    "synthesize_cross_representation": {
        "description": """
DEPRECATED: Use synthesize() instead.

synthesize() supports both single-session and multi-session synthesis.
This tool delegates to synthesize internally.
""",
        "parameters": {
            "session_id": "The session to analyze",
            "question": "The question to answer",
            "focus": "Optional focus"
        }
    },

    # =========================================================================
    # SEARCH TOOLS (Legacy - prefer artifact tools when possible)
    # =========================================================================

    "search_transcripts": {
        "description": """
Search discussion transcripts for specific content, quotes, or moments.

WHEN TO USE:
- Finding what was said about a specific topic
- Looking for exact quotes or statements
- Finding when something was mentioned
- Searching for specific moments in discussions
- Questions like "what did [Speaker] say about X?"

WHEN NOT TO USE:
- Finding session-level patterns (use search_sessions)
- Analyzing collaboration quality (use get_collaboration_analysis)
- Understanding how ideas connect (use explore_concepts)

HOW TO USE:
- query: The topic, concept, or phrase to search for
- session_ids: Optional list to limit search to specific sessions
- speaker: Optional speaker name to filter results (e.g., "Tucker", "David")
- limit: Number of results (default 10)

RETURNS: Transcript chunks with speaker, timestamp, and context.

EXAMPLE: To find what Tucker said about AI:
- First, check session table: Tucker is in Session 19
- search_transcripts(query="AI reasoning", session_ids=[19], speaker="Tucker")
""",
        "parameters": {
            "query": "Search query - topic, phrase, or concept to find",
            "session_ids": "Optional: List of session IDs to search within",
            "speaker": "Optional: Speaker name to filter results",
            "limit": "Number of results to return (default 10)"
        }
    },

    "search_sessions": {
        "description": """
Search for sessions by topic, pattern, or characteristics.

WHEN TO USE:
- Finding sessions about a specific topic
- Looking for sessions with certain patterns
- Questions like "which sessions discussed X?"
- Browsing what sessions are available
- Finding sessions with particular qualities

WHEN NOT TO USE:
- Finding specific quotes (use search_transcripts)
- Analyzing one session deeply (use get_session_overview)
- Comparing specific sessions (use compare_sessions)

HOW TO USE:
- query: What you're looking for in sessions
- limit: Number of sessions to return

RETURNS: Session summaries with topics, participants, and key metrics.
""",
        "parameters": {
            "query": "What to search for in sessions",
            "limit": "Number of sessions to return (default 5)"
        }
    },

    "search_concepts": {
        "description": """
Search the concept map for specific ideas, questions, or hypotheses.

WHEN TO USE:
- Finding specific concepts or ideas discussed
- Looking for questions that were asked
- Finding hypotheses or conclusions
- Understanding what ideas emerged in discussions

WHEN NOT TO USE:
- Finding exact quotes (use search_transcripts)
- Understanding how concepts connect (use explore_concepts)
- Getting full concept map (use get_concept_map)

RETURNS: Concept nodes with type, speaker, and theme context.
""",
        "parameters": {
            "query": "The concept, idea, or question to search for",
            "session_ids": "Optional: List of session IDs to search within",
            "concept_types": "Optional: Filter by type (question, idea, hypothesis, etc.)",
            "limit": "Number of results (default 10)"
        }
    },

    "search_communities": {
        "description": """
Search thematic communities (clusters of related concepts) across sessions.

WHEN TO USE:
- Understanding major themes across discussions
- Finding sessions that share similar topics
- Answering "what themes emerged?" questions
- Global understanding of discussion patterns

WHEN NOT TO USE:
- Finding specific quotes or moments
- Analyzing one session in detail

RETURNS: Community summaries with key concepts and participating sessions.
""",
        "parameters": {
            "query": "Theme or topic to search for",
            "limit": "Number of communities (default 5)"
        }
    },

    # =========================================================================
    # ANALYSIS TOOLS
    # =========================================================================

    "list_sessions": {
        "description": """
Get a list of all available sessions with basic metadata.

WHEN TO USE:
- "What sessions are available?"
- "Show me all sessions"
- "How many sessions are there?"
- Getting a complete list of sessions before comparison
- Starting exploration of available data

WHEN NOT TO USE:
- Looking for sessions about a specific topic (use search_sessions)
- Getting details about one session (use get_session_overview)

RETURNS: List of all sessions with:
- Session ID
- Session name
- Speaker count
- Transcript count
- Discourse type
""",
        "parameters": {}
    },

    "get_session_overview": {
        "description": """
Get a comprehensive overview of a specific session.

WHEN TO USE:
- "What happened in session X?"
- "Tell me about the [Name] session"
- Understanding a session before diving into details
- Getting context about participants, topics, and flow

WHEN NOT TO USE:
- Comparing multiple sessions (use compare_sessions)
- Finding specific content (use search_transcripts)
- Analyzing collaboration (use get_collaboration_analysis)

REQUIRES: session_id - the specific session to analyze

RETURNS: Session summary including:
- Main topics and themes
- Participants and their roles
- Key moments and insights
- Duration and structure
""",
        "parameters": {
            "session_id": "The session ID to get overview for"
        }
    },

    "get_collaboration_analysis": {
        "description": """
Get 7C collaboration quality analysis for ONE specific session.

WHEN TO USE:
- "How well did they collaborate in session X?" (specific session)
- "Was the discussion productive in the Nuclear Fusion session?"
- "Did everyone participate equally in session 20?"
- Analyzing group dynamics for a KNOWN session

WHEN NOT TO USE:
- "Which session had the best collaboration?" → Use compare_sessions() instead!
- "Find the session with highest collaboration" → Use compare_sessions() instead!
- Finding what was discussed (use search_transcripts)

NOTE: For queries about "best/highest/most" collaboration across sessions,
use compare_sessions() which compares ALL sessions and ranks them.

REQUIRES: session_id - you must already know which specific session to analyze

RETURNS: Seven collaboration dimensions (0-100 scores):
- Climate: Psychological safety, supportive atmosphere
- Communication: Clarity, active listening, articulation
- Contribution: Balanced participation, equal voice
- Conflict: Constructive disagreement, productive debate
- Context: Shared understanding, common ground
- Constructive: Building on others' ideas
- Compatibility: Working style alignment

Each dimension includes score, explanation, and evidence.
""",
        "parameters": {
            "session_id": "The session ID to analyze (must be a specific session you already know)"
        }
    },

    "compare_sessions": {
        "description": """
Compare multiple sessions across multiple dimensions. MANDATORY for "best/highest/most" queries.

MANDATORY - USE THIS TOOL FOR:
- "Which session has the best collaboration?" → compare_sessions() with NO session_ids (compares ALL)
- "Which session had the highest [metric]?" → compare_sessions() with NO session_ids
- "Which session was most productive?" → compare_sessions() with NO session_ids
- "Find the session with the best [quality]" → compare_sessions() with NO session_ids

ALSO USE FOR:
- "Compare session X and Y" → compare_sessions(session_ids=[X, Y])
- "What's different between these sessions?"
- Analyzing patterns across sessions

WHEN NOT TO USE:
- Analyzing a single session (use get_session_overview)
- Finding content in sessions (use search_transcripts)

Args:
- session_ids: List of session IDs to compare. If empty/None, compares ALL sessions.
  Use empty list for "best/highest" queries to ensure comprehensive comparison.

RETURNS: Comparison across:
- Topics and themes
- Collaboration metrics (7C scores)
- Participant dynamics
- Key differences, similarities, AND rankings (best/worst)
""",
        "parameters": {
            "session_ids": "List of session IDs to compare. Pass empty list [] or omit for 'best/highest' queries to compare ALL sessions."
        }
    },

    "analyze_speaker": {
        "description": """
Get a comprehensive profile of a speaker across all their sessions.

WHEN TO USE:
- "How does [Name] participate?"
- "What's [Name]'s discussion style?"
- "Tell me about [Name]'s contributions"
- Understanding individual speaker patterns across multiple sessions
- Assessing a speaker's overall thinking style and engagement

WHEN NOT TO USE:
- Finding what a speaker said (use search_transcripts with speaker filter)
- Analyzing a speaker within ONE specific session (use get_speaker_session_profile)
- Comparing two speakers (use compare_speakers)

HOW TO USE:
- speaker_name: The speaker to analyze (e.g., "Lex", "Julia", "Tucker")

RETURNS: Comprehensive SpeakerProfile including:
- Session participation: which sessions, utterance counts, avg length
- Communication style: LIWC metrics (analytic, clout, authenticity, tone, certainty)
- Contribution types: breakdown of ideas, questions, hypotheses, examples, etc.
- Interaction patterns: turn-taking balance, initiative score, engagement level
- Sample quotes: representative utterances with context
- Reasoning hints: strengths, notable patterns, areas of focus
""",
        "parameters": {
            "speaker_name": "Name of the speaker to analyze"
        }
    },

    "get_speaker_session_profile": {
        "description": """
Get a speaker's profile within a specific session.

WHEN TO USE:
- "How did [Name] participate in [Session]?"
- "What did [Name] contribute to the [Topic] discussion?"
- Understanding a speaker's role in a particular session
- Assessing a speaker's contributions to a specific topic

WHEN NOT TO USE:
- Understanding speaker patterns across ALL sessions (use analyze_speaker)
- Finding specific quotes (use search_transcripts with speaker filter)
- Comparing speakers (use compare_speakers)

HOW TO USE:
- speaker_name: The speaker to analyze (e.g., "David", "Lex")
- session_id: The specific session to analyze

RETURNS: Session-specific profile including:
- Session metrics: utterance count, average length, word count
- Communication style: LIWC metrics for that session
- Contributions: types of contributions (questions, ideas, etc.)
- Key quotes: notable statements from this session
""",
        "parameters": {
            "speaker_name": "Name of the speaker to analyze",
            "session_id": "The session ID to analyze the speaker within"
        }
    },

    "compare_speakers": {
        "description": """
Compare two or more speakers across their participation patterns.

WHEN TO USE:
- "Compare [Name1] and [Name2]"
- "Who is more analytical, [Name1] or [Name2]?"
- "How do these speakers differ in their discussion style?"
- Understanding relative participation patterns
- Identifying complementary or contrasting styles

WHEN NOT TO USE:
- Analyzing a single speaker (use analyze_speaker)
- Finding what speakers said (use search_transcripts)
- Session-level comparison (use compare_sessions)

HOW TO USE:
- speaker_names: List of 2+ speaker names to compare
- session_ids: Optional - limit comparison to specific sessions

RETURNS: Comparison including:
- Side-by-side metrics: utterance counts, avg lengths
- Style comparison: LIWC scores for each speaker
- Contribution comparison: types of contributions each makes
- Key differences: what distinguishes each speaker
- Similarities: shared patterns between speakers
""",
        "parameters": {
            "speaker_names": "List of speaker names to compare (minimum 2)",
            "session_ids": "Optional: Limit comparison to specific sessions"
        }
    },

    # =========================================================================
    # GRAPH NAVIGATION TOOLS
    # =========================================================================

    "explore_concepts": {
        "description": """
Explore how concepts connect in the discussion graph.

WHEN TO USE:
- "How does X relate to Y?"
- "What ideas are connected to X?"
- "What led to this conclusion?"
- Understanding reasoning chains and idea development
- Following the flow of discussion

WHEN NOT TO USE:
- Finding specific quotes (use search_transcripts)
- Getting all concepts (use get_concept_map)
- Session-level analysis (use get_session_overview)

HOW TO USE:
- concept_id: Starting concept to explore from
- direction: "outgoing" (what it leads to), "incoming" (what led to it), "both"
- depth: How many hops to explore (1-3)

RETURNS: Connected concepts with relationship types and paths.
""",
        "parameters": {
            "concept_id": "The concept node ID to explore from",
            "direction": "Exploration direction: 'outgoing', 'incoming', or 'both'",
            "depth": "How many hops to explore (1-3, default 2)"
        }
    },

    "find_reasoning_path": {
        "description": """
Find the reasoning path between two concepts.

WHEN TO USE:
- "How did they get from X to Y?"
- "What's the connection between these ideas?"
- "Trace the reasoning from X to Y"
- Understanding how conclusions were reached

REQUIRES: Both source and target concept IDs

RETURNS: The path of concepts and relationships connecting them.
""",
        "parameters": {
            "source_id": "Starting concept ID",
            "target_id": "Target concept ID",
            "max_depth": "Maximum path length to search (default 4)"
        }
    },

    "get_concept_map": {
        "description": """
Get the full concept map structure for a session.

WHEN TO USE:
- "Show me the concept map"
- "What ideas emerged in this session?"
- Understanding the complete structure of ideas
- Seeing how all concepts relate

WHEN NOT TO USE:
- Finding specific concepts (use search_concepts)
- Exploring connections (use explore_concepts)

REQUIRES: session_id

RETURNS: All concepts, relationships, and clusters for the session.
""",
        "parameters": {
            "session_id": "The session ID to get concept map for"
        }
    },

    # =========================================================================
    # Co-Discovery Tools (Hypothesis-Driven Inquiry)
    # =========================================================================
    "test_hypothesis": {
        "description": """
Systematically test a user's hypothesis across sessions.

WHEN TO USE:
- User explicitly states a hypothesis: "I think Tucker shows systems thinking"
- User asks to verify a claim: "Is it true that session 20 had the best collaboration?"
- User proposes a theory to test: "What if the Nuclear Fusion session was more creative?"
- User uses phrases like "I believe", "I suspect", "Could it be that"

HOW TO USE:
- Extract the hypothesis claim clearly from the user's query
- Optionally specify session_ids to narrow the scope of testing
- Set include_counter_evidence=True for balanced assessment (default)

EXAMPLE:
User: "I think Tucker demonstrates systems thinking in session 19"
→ test_hypothesis(hypothesis="Tucker demonstrates systems thinking", session_ids=[19])

User: "Is it true that session 20 had better collaboration than session 19?"
→ test_hypothesis(hypothesis="session 20 had better collaboration", session_ids=[19, 20])

RETURNS:
- supporting_evidence: Evidence that supports the hypothesis
- countering_evidence: Evidence that contradicts the hypothesis
- confidence: 0.0-1.0 confidence in the verdict
- verdict: 'supported', 'refuted', 'mixed', or 'insufficient_evidence'
- sessions_examined: Which sessions were checked

IMPORTANT: Report BOTH supporting and countering evidence honestly.
Do not cherry-pick evidence to confirm the hypothesis.
""",
        "parameters": {
            "hypothesis": "The claim to test (required). Should be a clear statement.",
            "session_ids": "Optional list of session IDs to examine. If not provided, searches all.",
            "include_counter_evidence": "Whether to actively search for disconfirming evidence (default: True)"
        }
    }
}


def get_tools_prompt() -> str:
    """
    Generate a formatted tools prompt for the reasoning model.

    This creates a clear, structured description of all available tools
    that the model can use to understand when and how to use each one.
    """
    lines = ["# Available Tools\n"]

    for tool_name, tool_info in TOOL_DESCRIPTIONS.items():
        lines.append(f"## {tool_name}")
        lines.append(tool_info["description"].strip())
        lines.append("")

        if tool_info.get("parameters"):
            lines.append("**Parameters:**")
            for param, desc in tool_info["parameters"].items():
                lines.append(f"- `{param}`: {desc}")
            lines.append("")

    return "\n".join(lines)
