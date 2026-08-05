from app import db
from datetime import datetime


class Expert7CAnnotation(db.Model):
    """
    Expert annotations for 7C analysis - used for research evaluation.

    Allows human experts to provide their own 7C scores, analysis, and evidence
    so we can measure inter-rater agreement with LLM-generated analysis.
    """
    __tablename__ = 'expert_7c_annotation'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    expert_id = db.Column(db.String(100), nullable=False)
    session_device_id = db.Column(db.Integer, db.ForeignKey('session_device.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.Enum('draft', 'submitted'), default='draft')

    # Annotation data stored as JSON - same structure as LLM analysis
    # Structure: {
    #   "climate": {"score": 75, "analysis": "...", "evidence": "..."},
    #   "communication": {"score": 80, "analysis": "...", "evidence": "..."},
    #   ...
    # }
    annotation_data = db.Column(db.JSON)

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint: one annotation per expert per session_device
    __table_args__ = (
        db.UniqueConstraint('expert_id', 'session_device_id', name='unique_expert_device'),
    )

    # Relationships
    session_device = db.relationship("SessionDevice", backref="expert_annotations")

    def __init__(self, expert_id, session_device_id, annotation_data=None, status='draft'):
        self.expert_id = expert_id
        self.session_device_id = session_device_id
        self.annotation_data = annotation_data or self._empty_annotation()
        self.status = status

    @staticmethod
    def _empty_annotation():
        """Create empty annotation structure for all 7 dimensions."""
        dimensions = ['climate', 'communication', 'compatibility', 'conflict',
                      'context', 'contribution', 'constructive']
        return {
            dim: {'score': None, 'analysis': '', 'evidence': ''}
            for dim in dimensions
        }

    def update_annotation(self, annotation_data, status=None):
        """Update the annotation data."""
        self.annotation_data = annotation_data
        if status:
            self.status = status
        self.updated_at = datetime.utcnow()

    def json(self):
        return dict(
            id=self.id,
            expert_id=self.expert_id,
            session_device_id=self.session_device_id,
            status=self.status,
            annotation_data=self.annotation_data,
            created_at=self.created_at.isoformat() if self.created_at else None,
            updated_at=self.updated_at.isoformat() if self.updated_at else None
        )

    @staticmethod
    def verify_fields():
        return True, None
