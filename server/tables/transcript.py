from app import db

class Transcript(db.Model):
    __tablename__ = 'transcript'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_device_id = db.Column(db.Integer, db.ForeignKey('session_device.id'), nullable=False)
    start_time = db.Column(db.Integer, nullable=False)
    length = db.Column(db.Integer, nullable=False)
    question = db.Column(db.Boolean, nullable=False)
    transcript = db.Column(db.Text, nullable=False)
    word_count = db.Column(db.Integer, nullable=False)
    speaker_tag = db.Column(db.String(64))
    direction = db.Column(db.Integer)
    emotional_tone_value = db.Column(db.Integer)
    analytic_thinking_value = db.Column(db.Integer)
    clout_value = db.Column(db.Integer)
    authenticity_value = db.Column(db.Integer)
    certainty_value = db.Column(db.Integer)
    topic_id = db.Column(db.Integer)
    speaker_id = db.Column(db.Integer)

    keywords = db.relationship("KeywordUsage", lazy='joined', uselist=True)

    def __hash__(self):
        return hash((self.id))

    def __init__(self, session_device_id, start_time, length, transcript, question, direction, emotional_tone, analytic_thinking, clout, authenticity, certainty, topic_id, speaker_tag, speaker_id):
        self.session_device_id = session_device_id
        self.start_time = start_time
        self.length = length
        self.end_time = start_time + length
        self.question = question
        self.transcript = transcript
        self.word_count = len(transcript.split())
        self.direction = direction
        self.emotional_tone_value = emotional_tone
        self.analytic_thinking_value = analytic_thinking
        self.clout_value = clout
        self.authenticity_value = authenticity
        self.certainty_value = certainty
        self.topic_id = topic_id
        self.speaker_tag = speaker_tag
        self.speaker_id = speaker_id

    def json(self):
        return dict(
            id=self.id,
            session_device_id=self.session_device_id,
            start_time=self.start_time,
            length=self.length,
            question=self.question,
            transcript=self.transcript,
            speaker_tag=self.speaker_tag,
            direction=self.direction,
            emotional_tone_value=self.emotional_tone_value,
            analytic_thinking_value=self.analytic_thinking_value,
            clout_value=self.clout_value,
            authenticity_value=self.authenticity_value,
            certainty_value=self.certainty_value,
            word_count=self.word_count,
            topic_id=self.topic_id,
            speaker_id=self.speaker_id,
            keywords=[keyword.json(suppress=['transcript_id']) for keyword in self.keywords]
        )

    @staticmethod
    def verify_fields(name=None):
        message = None
        # Not implemented
        return message == None, message
