"""
Artifact Schema Definition for Artifact-Grounded RAG

This module defines the queryable schema for all LLM-generated artifacts
that serve as a shared analytical language between users and the system.

Artifacts include:
- Concept maps (nodes, edges, clusters)
- 7C collaborative quality scores
- LIWC linguistic metrics
- Speaker profiles
"""

from typing import Dict, List, Any

# =============================================================================
# 7C COLLABORATIVE QUALITY DIMENSIONS
# =============================================================================
SEVEN_C_DIMENSIONS = {
    "climate": {
        "field": "climate_score",
        "range": [0, 100],
        "description": "Emotional safety, respect, comfort in group interactions",
        "user_vocabulary": [
            "climate", "emotional safety", "respect", "comfortable", "safe",
            "supportive environment", "welcoming", "inclusive"
        ]
    },
    "communication": {
        "field": "communication_score",
        "range": [0, 100],
        "description": "Quality and effectiveness of information exchange",
        "user_vocabulary": [
            "communication", "communicating", "information exchange", "clear",
            "articulate", "expressive", "listening", "dialogue"
        ]
    },
    "compatibility": {
        "field": "compatibility_score",
        "range": [0, 100],
        "description": "How well group members' working styles complement each other",
        "user_vocabulary": [
            "compatibility", "compatible", "working together", "teamwork",
            "complementary", "synergy", "fit"
        ]
    },
    "conflict": {
        "field": "conflict_score",
        "range": [0, 100],
        "description": "Approaches to handling disagreements and contentious situations",
        "user_vocabulary": [
            "conflict", "disagreement", "debate", "tension", "argument",
            "dispute", "confrontation", "resolution"
        ]
    },
    "context": {
        "field": "context_score",
        "range": [0, 100],
        "description": "Environmental factors and situational awareness",
        "user_vocabulary": [
            "context", "contextual", "situational", "environment",
            "setting", "background", "circumstances"
        ]
    },
    "contribution": {
        "field": "contribution_score",
        "range": [0, 100],
        "description": "Individual participation and effort balance",
        "user_vocabulary": [
            "contribution", "participation", "involvement", "engagement",
            "active", "balanced", "equal participation"
        ]
    },
    "constructive": {
        "field": "constructive_score",
        "range": [0, 100],
        "description": "Goal achievement and mutual benefit",
        "user_vocabulary": [
            "constructive", "productive", "goal-oriented", "achievement",
            "beneficial", "outcome", "progress"
        ]
    }
}

# =============================================================================
# CONCEPT MAP METRICS (Argumentation Structure)
# =============================================================================
CONCEPT_MAP_METRICS = {
    "debate_score": {
        "field": "debate_score",
        "description": "Count of challenges + contrasts (argumentation intensity)",
        "user_vocabulary": [
            "debate", "argument", "argumentation", "contested", "disputed",
            "back and forth", "disagreeing"
        ]
    },
    "challenge_count": {
        "field": "challenge_count",
        "description": "Number of challenging/contradicting edges",
        "user_vocabulary": [
            "challenges", "challenging", "contradictions", "pushback",
            "counter-arguments", "disagreements"
        ]
    },
    "reasoning_depth": {
        "field": "reasoning_depth",
        "description": "Count of builds_on + elaborates edges (depth of reasoning)",
        "user_vocabulary": [
            "deep reasoning", "building on ideas", "elaboration", "depth",
            "complex thinking", "developed ideas"
        ]
    },
    "support_count": {
        "field": "support_count",
        "description": "Number of supporting edges",
        "user_vocabulary": [
            "support", "supporting", "agreement", "backing", "endorsing"
        ]
    },
    "question_count": {
        "field": "question_count",
        "description": "Number of question-type nodes",
        "user_vocabulary": [
            "questions", "inquiry", "asking", "curious", "questioning"
        ]
    },
    "node_count": {
        "field": "node_count",
        "description": "Total concept nodes (discussion richness)",
        "user_vocabulary": [
            "concepts", "ideas", "rich discussion", "many ideas"
        ]
    },
    "cluster_count": {
        "field": "cluster_count",
        "description": "Number of thematic clusters",
        "user_vocabulary": [
            "themes", "topics", "clusters", "thematic", "diverse topics"
        ]
    }
}

# =============================================================================
# LIWC LINGUISTIC METRICS (Chunk-Level)
# =============================================================================
LIWC_METRICS = {
    "analytic_thinking": {
        "field": "avg_analytic_thinking",
        "range": [0, 100],
        "description": "Level of analytical, logical thinking in speech",
        "user_vocabulary": [
            "analytical", "analytic thinking", "logical", "systematic",
            "methodical", "rational", "analytical moments"
        ]
    },
    "emotional_tone": {
        "field": "avg_emotional_tone",
        "range": [0, 100],
        "description": "Emotional valence of speech (higher = more positive)",
        "user_vocabulary": [
            "emotional", "emotional tone", "positive", "negative",
            "sentiment", "feeling", "mood"
        ]
    },
    "clout": {
        "field": "avg_clout",
        "range": [0, 100],
        "description": "Confidence and social status in speech",
        "user_vocabulary": [
            "confident", "clout", "authoritative", "leadership",
            "dominant", "assertive"
        ]
    },
    "authenticity": {
        "field": "avg_authenticity",
        "range": [0, 100],
        "description": "Genuine, honest speech patterns",
        "user_vocabulary": [
            "authentic", "genuine", "honest", "sincere", "real"
        ]
    },
    "certainty": {
        "field": "avg_certainty",
        "range": [0, 100],
        "description": "Level of certainty/confidence in statements",
        "user_vocabulary": [
            "certain", "sure", "confident", "definite", "uncertain"
        ]
    }
}

# =============================================================================
# ENTITY TYPES (For Resolution)
# =============================================================================
ENTITY_TYPES = {
    "session": {
        "table": "Session",
        "lookup_field": "name",
        "description": "A discussion session with participants",
        "vocabulary_patterns": [
            r"session\s+\d+",
            r"device\s+\d+",
            # Session names are detected by entity resolver
        ]
    },
    "speaker": {
        "table": "Speaker",
        "lookup_field": "alias",
        "description": "A participant in discussions",
        "vocabulary_patterns": [
            # Speaker names are detected by entity resolver
        ]
    }
}

# =============================================================================
# RETRIEVAL STRATEGIES
# =============================================================================
RETRIEVAL_STRATEGIES = {
    "metric_filter": {
        "description": "Filter by artifact metrics (7C, concept map, LIWC)",
        "use_when": "Query references specific score thresholds or metric comparisons"
    },
    "metric_filter_chunks": {
        "description": "Filter chunks by LIWC metrics",
        "use_when": "Query asks for 'moments' or 'instances' of specific qualities"
    },
    "entity_lookup": {
        "description": "Direct lookup by resolved entity IDs",
        "use_when": "Query references specific sessions or speakers by name"
    },
    "semantic_search": {
        "description": "Semantic similarity search on content",
        "use_when": "Query asks about topics or content without specific metrics"
    },
    "hybrid": {
        "description": "Combine metric filtering with semantic search",
        "use_when": "Query combines topic search with metric requirements"
    },
    "comparison": {
        "description": "Compare two entities side by side",
        "use_when": "Query contains comparison language (compare, vs, difference)"
    }
}

# =============================================================================
# QUERY INTENTS
# =============================================================================
QUERY_INTENTS = [
    "find_sessions",       # Find sessions matching criteria
    "find_chunks",         # Find specific moments/chunks
    "find_speakers",       # Find speakers matching criteria
    "compare_sessions",    # Compare two sessions
    "compare_speakers",    # Compare two speakers
    "analyze_session",     # Deep analysis of one session
    "analyze_speaker",     # Deep analysis of one speaker
    "temporal_analysis",   # Timeline/progression analysis
    "similar_sessions",    # Find sessions similar to reference
]

# =============================================================================
# SCHEMA PROMPT BUILDER
# =============================================================================
def build_schema_prompt() -> str:
    """
    Build a prompt section describing all queryable artifacts.
    This is injected into the LLM prompt for query understanding.
    """
    prompt_parts = []

    prompt_parts.append("## Available Artifacts and Queryable Fields\n")

    # 7C Scores
    prompt_parts.append("### 7C Collaborative Quality Scores (Session-Level)")
    prompt_parts.append("Range: 0-100. Higher = stronger presence of that quality.\n")
    for name, info in SEVEN_C_DIMENSIONS.items():
        vocab = ", ".join(info["user_vocabulary"][:5])
        prompt_parts.append(f"- **{info['field']}**: {info['description']}")
        prompt_parts.append(f"  User might say: {vocab}")
    prompt_parts.append("")

    # Concept Map Metrics
    prompt_parts.append("### Concept Map Metrics (Session-Level)")
    prompt_parts.append("Derived from argumentation structure.\n")
    for name, info in CONCEPT_MAP_METRICS.items():
        vocab = ", ".join(info["user_vocabulary"][:4])
        prompt_parts.append(f"- **{info['field']}**: {info['description']}")
        prompt_parts.append(f"  User might say: {vocab}")
    prompt_parts.append("")

    # LIWC Metrics
    prompt_parts.append("### LIWC Linguistic Metrics (Chunk-Level)")
    prompt_parts.append("Available for 30-second transcript chunks.\n")
    for name, info in LIWC_METRICS.items():
        vocab = ", ".join(info["user_vocabulary"][:4])
        prompt_parts.append(f"- **{info['field']}**: {info['description']}")
        prompt_parts.append(f"  User might say: {vocab}")
    prompt_parts.append("")

    # Entity Types
    prompt_parts.append("### Entity Types")
    prompt_parts.append("- **session**: Referenced by name (e.g., 'Carlson Show', 'Vanessa Podcast')")
    prompt_parts.append("- **speaker**: Referenced by alias (e.g., 'David', 'Lex')")
    prompt_parts.append("")

    return "\n".join(prompt_parts)


def get_all_metric_fields() -> Dict[str, str]:
    """Return mapping of all metric field names to their source."""
    fields = {}
    for name, info in SEVEN_C_DIMENSIONS.items():
        fields[info["field"]] = "7c"
    for name, info in CONCEPT_MAP_METRICS.items():
        fields[info["field"]] = "concept_map"
    for name, info in LIWC_METRICS.items():
        fields[info["field"]] = "liwc"
    return fields


def get_metric_vocabulary() -> Dict[str, str]:
    """Return mapping of user vocabulary terms to metric fields."""
    vocab = {}
    for name, info in SEVEN_C_DIMENSIONS.items():
        for term in info["user_vocabulary"]:
            vocab[term.lower()] = info["field"]
    for name, info in CONCEPT_MAP_METRICS.items():
        for term in info["user_vocabulary"]:
            vocab[term.lower()] = info["field"]
    for name, info in LIWC_METRICS.items():
        for term in info["user_vocabulary"]:
            vocab[term.lower()] = info["field"]
    return vocab
