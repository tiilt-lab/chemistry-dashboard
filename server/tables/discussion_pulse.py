from app import db
from datetime import datetime

class DiscussionPulse(db.Model):
    """
    Store periodic summaries of discussion progress.
    Generated every ~60 seconds during a session for real-time monitoring.
    """
    __tablename__ = 'discussion_pulse'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_device_id = db.Column(db.Integer, db.ForeignKey('session_device.id', ondelete='CASCADE'), nullable=False)

    # Time range covered by this pulse
    start_time = db.Column(db.Float, nullable=False)  # Seconds from session start
    end_time = db.Column(db.Float, nullable=False)    # Seconds from session start

    # Summary content
    summary_text = db.Column(db.Text, nullable=False)

    # Topics as JSON array: ["topic1", "topic2", ...]
    topics = db.Column(db.JSON)

    # Optional speaker participation for this segment
    speaker_count = db.Column(db.Integer)
    dominant_speaker_id = db.Column(db.Integer, db.ForeignKey('speaker.id'), nullable=True)

    # Generation metadata
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    transcript_count = db.Column(db.Integer)  # Number of transcripts summarized

    # Relationships
    session_device = db.relationship("SessionDevice", backref="discussion_pulses")

    def __init__(self, session_device_id, start_time, end_time, summary_text, topics=None,
                 speaker_count=None, dominant_speaker_id=None, transcript_count=None):
        self.session_device_id = session_device_id
        self.start_time = start_time
        self.end_time = end_time
        self.summary_text = summary_text
        self.topics = topics or []
        self.speaker_count = speaker_count
        self.dominant_speaker_id = dominant_speaker_id
        self.transcript_count = transcript_count
        self.created_at = datetime.utcnow()

    def format_time_range(self):
        """Format time range as MM:SS - MM:SS"""
        start_min = int(self.start_time // 60)
        start_sec = int(self.start_time % 60)
        end_min = int(self.end_time // 60)
        end_sec = int(self.end_time % 60)
        return f"{start_min}:{start_sec:02d} - {end_min}:{end_sec:02d}"

    def json(self):
        return dict(
            id=self.id,
            session_device_id=self.session_device_id,
            start_time=self.start_time,
            end_time=self.end_time,
            time_range=self.format_time_range(),
            summary_text=self.summary_text,
            topics=self.topics or [],
            speaker_count=self.speaker_count,
            dominant_speaker_id=self.dominant_speaker_id,
            transcript_count=self.transcript_count,
            created_at=self.created_at.isoformat() if self.created_at else None
        )
