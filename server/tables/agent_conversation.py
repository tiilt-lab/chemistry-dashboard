"""
Agent Conversation Model

Tracks multi-turn conversations with the agentic RAG system.
Each conversation can optionally focus on a specific session.
"""

from app import db
from datetime import datetime
import uuid


class AgentConversation(db.Model):
    __tablename__ = 'agent_conversation'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    session_device_id = db.Column(db.Integer, db.ForeignKey('session_device.id', ondelete='SET NULL'), nullable=True)
    agent_version = db.Column(db.String(10), nullable=False, default='v3')  # v3, v4, v5, v6, baseline
    title = db.Column(db.String(255), nullable=True)  # Auto-generated from first query
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('agent_conversations', lazy='dynamic'))
    session_device = db.relationship('SessionDevice', backref=db.backref('agent_conversations', lazy='dynamic'))
    messages = db.relationship('AgentMessage', back_populates='conversation',
                               cascade='all, delete-orphan', lazy='dynamic')

    def __init__(self, user_id, session_device_id=None, title=None, agent_version='v3'):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.session_device_id = session_device_id
        self.agent_version = agent_version
        self.title = title
        self.created_at = datetime.utcnow()
        self.last_active = datetime.utcnow()

    def json(self, include_messages=False):
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'session_device_id': self.session_device_id,
            'agent_version': self.agent_version,
            'title': self.title,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'message_count': self.messages.count() if self.messages else 0
        }

        if include_messages:
            # Order by created_at when fetching messages
            result['messages'] = [m.json() for m in self.messages.order_by('created_at').all()]

        return result

    def update_title_from_query(self, query: str):
        """Auto-generate title from first query if not set."""
        if not self.title:
            # Truncate and clean the query for title
            title = query.strip()[:100]
            if len(query) > 100:
                title += "..."
            self.title = title

    def touch(self):
        """Update last_active timestamp."""
        self.last_active = datetime.utcnow()
