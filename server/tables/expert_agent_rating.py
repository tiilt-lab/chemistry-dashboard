"""
Expert Agent Rating Table

Stores expert ratings for agent responses in blind evaluation.
"""

from app import db
from datetime import datetime
import json


class ExpertAgentRating(db.Model):
    """Stores expert ratings for agent responses."""

    __tablename__ = 'expert_agent_rating'

    id = db.Column(db.Integer, primary_key=True)
    expert_id = db.Column(db.String(100), nullable=False)
    response_id = db.Column(db.Integer, db.ForeignKey('agent_response.id'), nullable=False)

    # Rating dimensions (1-5 Likert scale)
    accuracy = db.Column(db.Integer, nullable=False)  # Factually correct
    relevance = db.Column(db.Integer, nullable=False)  # Addresses the question
    groundedness = db.Column(db.Integer, nullable=False)  # Supported by evidence
    analytical_depth = db.Column(db.Integer, nullable=False)  # Meaningful insight
    helpfulness = db.Column(db.Integer, nullable=False)  # Useful and actionable

    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'expert_id': self.expert_id,
            'response_id': self.response_id,
            'ratings': {
                'accuracy': self.accuracy,
                'relevance': self.relevance,
                'groundedness': self.groundedness,
                'analytical_depth': self.analytical_depth,
                'helpfulness': self.helpfulness,
            },
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<ExpertAgentRating {self.id} by {self.expert_id}>'
