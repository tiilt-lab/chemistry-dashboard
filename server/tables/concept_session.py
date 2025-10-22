from app import db
from datetime import datetime

class ConceptSession(db.Model):
    __tablename__ = 'concept_session'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_device_id = db.Column(db.Integer, db.ForeignKey('session_device.id', ondelete='CASCADE'), nullable=False)
    discourse_type = db.Column(db.String(50), default='exploratory')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - Fixed cascade settings
    nodes = db.relationship("ConceptNode", back_populates="concept_session", 
                            cascade="all, delete-orphan", passive_deletes=True)
    edges = db.relationship("ConceptEdge", back_populates="concept_session", 
                            cascade="all, delete-orphan", passive_deletes=True)

    def __init__(self, session_device_id, discourse_type='exploratory'):
        self.session_device_id = session_device_id
        self.discourse_type = discourse_type
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def json(self):
        return dict(
            id=self.id,
            session_device_id=self.session_device_id,
            discourse_type=self.discourse_type,
            created_at=str(self.created_at) + ' UTC',
            updated_at=str(self.updated_at) + ' UTC',
            nodes=[node.json() for node in self.nodes],
            edges=[edge.json() for edge in self.edges]
        )