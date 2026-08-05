from app import db
from datetime import datetime


class ExpertConceptMapRating(db.Model):
    """
    Expert ratings for AI-generated concept maps.

    Allows human experts to evaluate concept map quality across
    multiple dimensions using a Likert scale (1-5).
    """
    __tablename__ = 'expert_concept_map_rating'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    expert_id = db.Column(db.String(100), nullable=False)
    session_device_id = db.Column(db.Integer, db.ForeignKey('session_device.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum('draft', 'submitted'), default='draft')

    # Ratings stored as JSON: {"node_accuracy": 4, "relationship_validity": 3, ...}
    ratings = db.Column(db.JSON)
    comment = db.Column(db.Text, default='')

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One rating per expert per session_device
    __table_args__ = (
        db.UniqueConstraint('expert_id', 'session_device_id', name='unique_expert_concept_map_device'),
    )

    session_device = db.relationship("SessionDevice", backref="expert_concept_map_ratings")

    def __init__(self, expert_id, session_device_id, ratings=None, comment='', status='draft'):
        self.expert_id = expert_id
        self.session_device_id = session_device_id
        self.ratings = ratings or self._empty_ratings()
        self.comment = comment
        self.status = status

    @staticmethod
    def _empty_ratings():
        return {
            'node_accuracy': None,
            'relationship_validity': None,
            'completeness': None,
            'granularity': None,
            'usefulness': None,
        }

    def update_rating(self, ratings, comment=None, status=None):
        self.ratings = ratings
        if comment is not None:
            self.comment = comment
        if status:
            self.status = status
        self.updated_at = datetime.utcnow()

    def json(self):
        return dict(
            id=self.id,
            expert_id=self.expert_id,
            session_device_id=self.session_device_id,
            status=self.status,
            ratings=self.ratings,
            comment=self.comment,
            created_at=self.created_at.isoformat() if self.created_at else None,
            updated_at=self.updated_at.isoformat() if self.updated_at else None,
        )
