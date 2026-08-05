from app import db
from datetime import datetime

class SevenCsCodedSegment(db.Model):
    __tablename__ = 'seven_cs_coded_segment'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('seven_cs_analysis.id', ondelete='CASCADE'), nullable=False)
    transcript_id = db.Column(db.Integer, db.ForeignKey('transcript.id', ondelete='CASCADE'), nullable=False)

    # Coding details
    dimension = db.Column(db.String(50), nullable=False)  # climate, communication, compatibility, etc.
    start_time = db.Column(db.Float, nullable=False)
    end_time = db.Column(db.Float, nullable=False)
    text_snippet = db.Column(db.Text, nullable=False)
    speaker_tag = db.Column(db.String(64))

    # Why this was coded with this dimension
    coding_reason = db.Column(db.Text)  # Brief LLM explanation
    confidence = db.Column(db.Float)  # 0.0 to 1.0

    # Timestamps
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    analysis = db.relationship("SevenCsAnalysis", back_populates="coded_segments")
    transcript = db.relationship("Transcript")

    # Index for efficient querying
    __table_args__ = (
        db.Index('idx_analysis_dimension', 'analysis_id', 'dimension'),
        db.Index('idx_analysis_time', 'analysis_id', 'start_time'),
    )

    def __init__(self, analysis_id, transcript_id, dimension, start_time, end_time,
                 text_snippet, speaker_tag=None, coding_reason=None, confidence=None):
        self.analysis_id = analysis_id
        self.transcript_id = transcript_id
        self.dimension = dimension
        self.start_time = start_time
        self.end_time = end_time
        self.text_snippet = text_snippet
        self.speaker_tag = speaker_tag
        self.coding_reason = coding_reason
        self.confidence = confidence

    def json(self):
        return dict(
            id=self.id,
            analysis_id=self.analysis_id,
            transcript_id=self.transcript_id,
            dimension=self.dimension,
            start_time=self.start_time,
            end_time=self.end_time,
            text_snippet=self.text_snippet,
            speaker_tag=self.speaker_tag,
            coding_reason=self.coding_reason,
            confidence=self.confidence,
            created_at=self.created_at.isoformat() if self.created_at else None
        )

    @staticmethod
    def verify_fields():
        return True, None