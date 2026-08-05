"""
Agent Response Table

Stores agent responses for expert blind evaluation.
Responses are automatically added when agents answer queries.
"""

from app import db
from datetime import datetime


class AgentResponse(db.Model):
    """Stores agent responses for blind expert evaluation."""

    __tablename__ = 'agent_response'

    id = db.Column(db.Integer, primary_key=True)
    agent_version = db.Column(db.String(50), nullable=False)  # 'v7' or 'baseline-v1', hidden from experts
    query_text = db.Column(db.Text, nullable=False)  # Named query_text to avoid conflict with Model.query
    response_text = db.Column(db.Text, nullable=False)
    conversation_id = db.Column(db.String(100), nullable=True)  # For reference
    pair_id = db.Column(db.String(50), nullable=True)  # Groups paired responses (e.g., 'q4')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to ratings
    ratings = db.relationship('ExpertAgentRating', backref='agent_response', lazy=True)

    def to_dict(self, include_agent=False):
        """Convert to dictionary. By default, hides agent_version for blind evaluation."""
        result = {
            'id': self.id,
            'query': self.query_text,  # Return as 'query' for frontend
            'response': self.response_text,  # Return as 'response' for frontend
            'pair_id': self.pair_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_agent:
            result['agent_version'] = self.agent_version
        return result

    def __repr__(self):
        return f'<AgentResponse {self.id} ({self.agent_version})>'
