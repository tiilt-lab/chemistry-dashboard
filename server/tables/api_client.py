from app import db
from datetime import datetime, timedelta
import hashlib
import os
import binascii
import random
import string

class APIClient(db.Model):
    __tablename__ = 'api_client'
    client_id = db.Column(db.String(64),primary_key=True, nullable=False)
    client_secret_hash = db.Column(db.String(128), nullable=False)
    client_token_hash = db.Column(db.String(128), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    salt = db.Column(db.String(64), nullable=False)
    expiration_date = db.Column(db.DateTime, nullable=True)

    def __hash__(self):
        return hash(self.client_id)

    def __init__(self, user_id):
        self.user_id = user_id
        self.salt = hashlib.sha256(os.urandom(60)).hexdigest()
        self.client_id = hashlib.sha256(os.urandom(64)).hexdigest()

    def generate_secret(self):
        salt_bytes = self.salt.encode('ascii')
        new_secret = hashlib.sha256(os.urandom(64)).hexdigest()
        secret_hash = hashlib.pbkdf2_hmac('sha512', new_secret.encode('utf-8'), salt_bytes, 100000)
        self.client_secret_hash = binascii.hexlify(secret_hash).decode('ascii')
        return new_secret

    def generate_token(self):
        salt_bytes = self.salt.encode('ascii')
        new_token = hashlib.sha256(os.urandom(64)).hexdigest()
        token_hash = hashlib.pbkdf2_hmac('sha512', new_token.encode('utf-8'), salt_bytes, 100000)
        self.client_token_hash = binascii.hexlify(token_hash).decode('ascii')
        self.expiration_date = datetime.utcnow() + timedelta(minutes=30)
        return new_token

    def verify_secret(self, provided_secret):
        salt_bytes = self.salt.encode('ascii')
        secret_hash = hashlib.pbkdf2_hmac('sha512', provided_secret.encode('utf-8'), salt_bytes, 100000)
        secret_hash = binascii.hexlify(secret_hash).decode('ascii')
        return secret_hash == self.client_secret_hash

    def verify_token(self, provided_token):
        salt_bytes = self.salt.encode('ascii')
        token_hash = hashlib.pbkdf2_hmac('sha512', provided_token.encode('utf-8'), salt_bytes, 100000)
        token_hash = binascii.hexlify(token_hash).decode('ascii')
        return token_hash == self.client_token_hash and datetime.utcnow() < self.expiration_date

    def json(self):
        return dict(
            client_id=self.client_id,
            user_id=self.user_id,
            expiration_date= None if self.expiration_date == None else str(self.expiration_date) + ' UTC'
        )
