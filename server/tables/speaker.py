from app import db
from utility import verify_characters

class Speaker(db.Model):
    __tablename__ = 'speaker'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_device_id = db.Column(db.Integer, db.ForeignKey('session_device.id'), nullable=False)
    alias = db.Column(db.String(64))

    NAME_MAX_LENGTH = 64
    NAME_CHARS = 'a-zA-Z0-9\': '

    def __hash__(self):
        return hash((self.id))

    def __init__(self, session_device_id, alias):
        self.session_device_id = session_device_id
        self.alias = alias

    def get_name(self):
        if not self.name:
            return 'Speaker {0}'.format(self.id)
        else:
            return self.name

    def json(self):
        return dict(
            id=self.id,
            session_device_id=self.session_device_id,
            alias=self.get_alias()
        )

    @staticmethod
    def verify_fields(name=None):
        message = None
        if name != None:
            if len(name) > Speaker.NAME_MAX_LENGTH:
                message = 'Alias must not exceed {0} characters.'.format(Speaker.NAME_MAX_LENGTH)
            if not verify_characters(name, Speaker.NAME_CHARS):
                message = 'Invalid characters in alias.'
        return message == None, message
