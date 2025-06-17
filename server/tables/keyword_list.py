from app import db
from datetime import datetime
from .keyword_list_item import KeywordListItem
from utility import verify_characters

class KeywordList(db.Model):
    __tablename__ = 'keyword_list'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False)
    name = db.Column(db.String(64))

    keywords = db.relationship("KeywordListItem", lazy='joined', uselist=True)

    NAME_MAX_LENGTH = 64
    NAME_CHARS = 'a-zA-Z0-9\': '

    def __hash__(self):
        return hash((self.id))

    def __init__(self, owner_id):
        self.owner_id = owner_id
        self.creation_date = datetime.utcnow()

    def get_name(self):
        if not self.name:
            return 'List {0}'.format(self.id)
        else:
            return self.name

    def json(self):
        return dict(
            id=self.id,
            creation_date=str(self.creation_date) + ' UTC',
            name=self.get_name(),
            keywords=[keyword.keyword for keyword in self.keywords]
        )

    @staticmethod
    def verify_fields(name=None, keywords=None):
        message = None
        if name != None:
            if len(name) > KeywordList.NAME_MAX_LENGTH:
                message = 'Name must not exceed {0} characters.'.format(KeywordList.NAME_MAX_LENGTH)
            if not verify_characters(name, KeywordList.NAME_CHARS):
                message = 'Invalid characters in list name.'
        if keywords != None:
            for keyword in keywords:
                valid, keyword_message = KeywordListItem.verify_fields(keyword=keyword)
                if not valid:
                    message = keyword_message
        return message == None, message
