DISCOURSE_SCHEMAS = {
    'exploratory': {
        'node_types': ['question', 'idea', 'elaboration', 'example', 'uncertainty', 
                      'assumption', 'metaphor', 'speculation'],
        'edge_types': ['explores', 'relates_to', 'contrasts_with', 'builds_on',
                      'questions', 'exemplifies', 'elaborates', 'clarifies']
    },
    'problem_solving': {
        'node_types': ['problem', 'cause', 'solution', 'constraint', 'evaluation',
                      'challenge', 'workaround', 'trade_off'],
        'edge_types': ['causes', 'solves', 'constrains', 'evaluates',
                      'mitigates', 'worsens', 'alternatives_to']
    },
    'planning': {
        'node_types': ['goal', 'task', 'resource', 'timeline', 'dependency',
                      'milestone', 'risk', 'action', 'decision_point'],
        'edge_types': ['requires', 'precedes', 'enables', 'blocks',
                      'depends_on', 'contributes_to', 'delays']
    },
    'analytical': {
        'node_types': ['observation', 'hypothesis', 'data', 'interpretation', 'conclusion',
                      'evidence', 'counterpoint', 'synthesis', 'implication'],
        'edge_types': ['supports', 'contradicts', 'derives_from', 'leads_to',
                      'challenges', 'synthesizes', 'qualifies']
    },
    'mixed': {
        'node_types': ['concept', 'statement', 'reference', 'aside', 'clarification'],
        'edge_types': ['relates_to', 'follows', 'refers_to', 'contextualizes']
    }
}

# Additional universal node types that can appear in any discourse
UNIVERSAL_NODE_TYPES = [
    'question',      # Any question asked
    'example',       # Concrete instance or case
    'uncertainty',   # Expression of doubt or unknowing
    'action',        # Action item or next step
    'synthesis',     # Combining multiple ideas
    'challenge',     # Disagreement or counterpoint
    'assumption',    # Underlying belief or premise
    'clarification', # Restating for clarity
    'metaphor',      # Analogical thinking
    'anecdote'      # Personal story or experience
]

# Additional universal edge types for richer relationships
UNIVERSAL_EDGE_TYPES = [
    'questions',     # When someone questions a concept
    'exemplifies',   # When example illustrates idea
    'elaborates',    # Adding detail or depth
    'clarifies',     # Making something clearer
    'challenges',    # Disagreeing or pushing back
    'synthesizes',   # Combining ideas
    'applies',       # Using concept in new context
    'contextualizes',# Providing background
    'answers',       # Responding to a question
    'agrees_with',   # Expressing agreement
    'disagrees_with' # Expressing disagreement
]

def get_all_node_types():
    """Get all possible node types across all schemas plus universal types"""
    all_types = set(UNIVERSAL_NODE_TYPES)
    for schema in DISCOURSE_SCHEMAS.values():
        all_types.update(schema['node_types'])
    return list(all_types)

def get_all_edge_types():
    """Get all possible edge types across all schemas plus universal types"""
    all_types = set(UNIVERSAL_EDGE_TYPES)
    for schema in DISCOURSE_SCHEMAS.values():
        all_types.update(schema['edge_types'])
    return list(all_types)

def get_schema_for_discourse(discourse_type):
    """Get the appropriate schema with universal types included"""
    base_schema = DISCOURSE_SCHEMAS.get(discourse_type, DISCOURSE_SCHEMAS['mixed'])
    return {
        'node_types': base_schema['node_types'] + UNIVERSAL_NODE_TYPES,
        'edge_types': base_schema['edge_types'] + UNIVERSAL_EDGE_TYPES
    }

# Semantic categories for visualization grouping
NODE_CATEGORIES = {
    'epistemic': ['question', 'uncertainty', 'hypothesis', 'assumption', 'evidence'],
    'conceptual': ['idea', 'concept', 'elaboration', 'interpretation', 'synthesis'],
    'operational': ['task', 'action', 'solution', 'resource', 'milestone'],
    'evaluative': ['evaluation', 'challenge', 'constraint', 'trade_off'],
    'illustrative': ['example', 'metaphor', 'anecdote', 'data'],
    'structural': ['goal', 'problem', 'conclusion', 'decision_point']
}

# Edge strength weights for different relationship types
EDGE_WEIGHTS = {
    # Strong connections
    'causes': 1.0,
    'enables': 1.0,
    'answers': 1.0,
    'solves': 1.0,
    
    # Medium connections
    'builds_on': 0.7,
    'supports': 0.7,
    'elaborates': 0.7,
    'exemplifies': 0.7,
    
    # Weak connections
    'relates_to': 0.5,
    'contextualizes': 0.5,
    'refers_to': 0.5,
    
    # Opposition connections
    'contradicts': 0.8,
    'challenges': 0.8,
    'disagrees_with': 0.7
}