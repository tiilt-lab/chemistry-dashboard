from app import db
from datetime import datetime
from utility import verify_characters

class Session(db.Model):
    __tablename__ = 'session'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    passcode = db.Column(db.String(64))
    folder = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)
    topic_model_id = db.Column(db.Integer, db.ForeignKey('topic_model.id'), nullable=True)

    keywords = db.relationship("Keyword", lazy='joined', uselist=True)

    NAME_MAX_LENGTH = 64
    NAME_CHARS = 'a-zA-Z0-9\': '
    PASSCODE_MAX_LENGTH = 64

    def __hash__(self):
        return hash((self.id))

    def __init__(self, owner_id, name="Unnamed", folder=None, topic_model=None):
        self.owner_id = owner_id
        self.name = name
        self.creation_date = datetime.utcnow()
        self.folder = folder
        self.topic_model_id = topic_model


    def get_length(self):
        return max((self.end_date - self.creation_date).total_seconds() if self.end_date else (datetime.utcnow() - self.creation_date).total_seconds(), 0.0)

    def json(self):
        return dict(
            id=self.id,
            name=self.name,
            passcode=self.passcode,
            creation_date=str(self.creation_date) + ' UTC',
            end_date=str(self.end_date) + ' UTC' if self.end_date else None,
            length=self.get_length(), # length is not stored in database as it can be derived
            keywords=[keyword.keyword for keyword in self.keywords],
            folder=self.folder,
            topic_model_id=self.topic_model_id
        )

    @staticmethod
    def verify_fields(name=None):
        message = None
        if name != None:
            if len(name) > Session.NAME_MAX_LENGTH:
                message = 'Name must not exceed {0} characters.'.format(Session.NAME_MAX_LENGTH)
            if not verify_characters(name, Session.NAME_CHARS):
                message = 'Invalid characters in name.'
        return message == None, message
