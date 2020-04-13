from app import db
from datetime import datetime
from utility import verify_characters
import hashlib
import os
import binascii
import random
import string
import re

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(64), nullable=False)
    salt = db.Column(db.String(64), nullable=False)
    hash_pass = db.Column(db.String(128), nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    change_password = db.Column(db.Boolean, nullable=False)
    locked = db.Column(db.Boolean, nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False)

    api_client = db.relationship("APIClient", lazy='joined', uselist=False)

    EMAIL_MAX_LENGTH = 128
    EMAIL_CHARS = 'a-zA-Z0-9@\':!#$%&*+-/=?^_{|}~.'
    ROLE_MAX_LENGTH = 64
    SALT_MAX_LENGTH = 64
    HASH_MAX_LENGTH = 128

    def __hash__(self):
        return hash(self.id)

    def __init__(self, email, role='user', password=None):
        self.email = email
        self.role = role
        self.salt = hashlib.sha256(os.urandom(60)).hexdigest()
        self.change_password = False
        if password != None:
            self.set_password(password, validate=False)
        else:
            self.reset_password(16)
        self.creation_date = datetime.utcnow()
        self.locked = False

    def json(self):
        return dict(
            id=self.id,
            role=self.role,
            email=self.email,
            creation_date=str(self.creation_date) + ' UTC',
            last_login=self.last_login,
            locked=self.locked,
            change_password=self.change_password,
            api_access=(self.api_client != None)
        )

    def verify_password(self, provided_password):
        salt_bytes = self.salt.encode('ascii')
        pwdhash = hashlib.pbkdf2_hmac('sha512', provided_password.encode('utf-8'), salt_bytes, 100000)
        pwdhash = binascii.hexlify(pwdhash).decode('ascii')
        return pwdhash == self.hash_pass

    def reset_password(self, length):
        random_password = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(length))
        self.set_password(random_password, validate=False)
        self.change_password = True
        return random_password

    def set_password(self, password, validate=True):
        if validate:
            password = password.strip()
            if len(password) < 8:
                return False, 'Password must be at least 8 characters long.'
            if len(password) > 64:
                return False, 'Password must be at 64 characters or shorter.'
            if not re.match('.*[0-9]', password):
                return False, 'Password must contain at least one digit.'
            if not re.match('.*[A-Z]', password):
                return False, 'Password must contain at least one uppercase letter.'
            if not re.match('.*[a-z]', password):
                return False, 'Password must contain at least one lowercase letter.'
            if not re.match('.*[!"#$%&\'()*+,-./:;<=>?@[\\]^_`}{|~]', password):
                return False, 'Password must contain at least one special character.'
            if not re.match('^[ a-zA-Z0-9!#$&()*+-.:;<=>?@\[\]_}{|~]*$', password):
                return False, 'Invalid special character.  Please only use the following... \n! # $ & ? @ * + - < = > . : ; [ ] ( ) _'
        salt_bytes = self.salt.encode('ascii')
        pwdhash = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'), salt_bytes, 100000)
        self.hash_pass = binascii.hexlify(pwdhash).decode('ascii')
        self.change_password = False

        return True, 'Password is valid.'

    @staticmethod
    def verify_fields(email=None, role=None):
        message = None
        if email != None:
            if len(email) > User.EMAIL_MAX_LENGTH:
                message = 'Username must not exceed {0} characters.'.format(User.EMAIL_MAX_LENGTH)
            if not verify_characters(email, User.EMAIL_CHARS):
                message = 'Invalid characters in email.'
        if role != None:
            if not role in ['user', 'admin', 'super']:
                message = 'Invalid role.'
        return message == None, message
