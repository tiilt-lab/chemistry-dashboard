"""
Agent Message Model

Stores individual messages in agent conversations.
Includes rich metadata like citations, tools used, and reasoning trace.
"""

from app import db
from datetime import datetime
import json


class AgentMessage(db.Model):
    __tablename__ = 'agent_message'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conversation_id = db.Column(db.String(36), db.ForeignKey('agent_conversation.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.Enum('user', 'assistant', name='message_role'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    citations = db.Column(db.JSON, nullable=True)  # Array of Citation objects
    tools_used = db.Column(db.JSON, nullable=True)  # Array of tool names and params
    reasoning_trace = db.Column(db.JSON, nullable=True)  # Array of thought steps
    confidence = db.Column(db.Float, nullable=True)  # 0-1 for assistant messages
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    conversation = db.relationship('AgentConversation', back_populates='messages')

    # Index for efficient conversation queries
    __table_args__ = (
        db.Index('idx_conversation_created', 'conversation_id', 'created_at'),
    )

    def __init__(self, conversation_id, role, content, citations=None,
                 tools_used=None, reasoning_trace=None, confidence=None):
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.citations = citations
        self.tools_used = tools_used
        self.reasoning_trace = reasoning_trace
        self.confidence = confidence
        self.created_at = datetime.utcnow()

    def json(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'role': self.role,
            'content': self.content,
            'citations': self.citations,
            'tools_used': self.tools_used,
            'reasoning_trace': self.reasoning_trace,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @staticmethod
    def from_grounded_response(conversation_id: str, response: dict) -> 'AgentMessage':
        """Create an assistant message from a GroundedResponse dict."""
        return AgentMessage(
            conversation_id=conversation_id,
            role='assistant',
            content=response.get('answer', ''),
            citations=response.get('citations'),
            tools_used=response.get('tools_used'),
            reasoning_trace=response.get('reasoning_trace'),
            confidence=response.get('confidence')
        )
