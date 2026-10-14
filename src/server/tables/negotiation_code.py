from app import db
import json


class NegotiationCode(db.Model):
    """One utterance's codes in one coding run: {dimension: code | [codes]}
    as JSON, whatever dimensions the run's scheme has. Goes with its run
    (re-runs replace the set) and with its transcript row (a post-hoc audio
    re-run that rewrites the transcript drops the codes). The four Viking
    columns remain for rows written before migration 7f8091021324 and are
    read only when ``codes`` is empty."""
    __tablename__ = 'negotiation_code'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    run_id = db.Column(db.Integer, db.ForeignKey('negotiation_coding_run.id', ondelete='CASCADE'), nullable=False, index=True)
    transcript_id = db.Column(db.Integer, db.ForeignKey('transcript.id', ondelete='CASCADE'), nullable=False, index=True)
    codes = db.Column(db.Text)          # JSON {dimension: value}
    emotion = db.Column(db.String(16))  # legacy Viking columns (pre-7f8091021324 rows)
    rip = db.Column(db.String(16))
    frame = db.Column(db.String(32))
    listening = db.Column(db.Text)

    LEGACY = ('emotion', 'rip', 'frame', 'listening')

    def __hash__(self):
        return hash(self.id)

    def __init__(self, run_id, transcript_id, codes):
        self.run_id = run_id
        self.transcript_id = transcript_id
        self.set_values(codes)

    def set_values(self, codes):
        codes = dict(codes or {})
        self.codes = json.dumps(codes)
        # Mirror the Viking columns while they exist, for anything old.
        self.emotion = codes.get('emotion') if isinstance(codes.get('emotion'), str) else None
        self.rip = codes.get('rip') if isinstance(codes.get('rip'), str) else None
        self.frame = codes.get('frame') if isinstance(codes.get('frame'), str) else None
        listening = codes.get('listening')
        self.listening = json.dumps(list(listening)) if isinstance(listening, list) else None

    def values(self):
        """{dimension: code | [codes]} for this utterance."""
        if self.codes:
            try:
                parsed = json.loads(self.codes)
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                return parsed
        try:
            listening = json.loads(self.listening) if self.listening else []
        except Exception:
            listening = []
        return {'emotion': self.emotion, 'rip': self.rip, 'frame': self.frame,
                'listening': listening if isinstance(listening, list) else []}

    def listening_list(self):
        value = self.values().get('listening')
        return value if isinstance(value, list) else []

    def json(self):
        return dict(id=self.id, run_id=self.run_id, transcript_id=self.transcript_id, codes=self.values())
