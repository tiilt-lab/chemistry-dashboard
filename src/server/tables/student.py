from app import db
from datetime import datetime
from utility import verify_characters
import hashlib
import os
import binascii
import random
import string
import re

class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lastname = db.Column(db.String(50), nullable=False)
    firstname = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(10), nullable=False)
    biometric_captured = db.Column(db.String(3), nullable=True) 
    creation_date = db.Column(db.DateTime, nullable=False)


    LAST_NAME_MAX_LENGTH = 50
    FIRST_NAME_MAX_LENGTH = 50
    USER_NAME_MAX_LENGTH = 10

    def __hash__(self):
        return hash(self.id)

    def __init__(self, lastname, firstname, username,biometric_captured):
        self.lastname = lastname
        self.firstname = firstname
        self.username = username
        self.biometric_captured = biometric_captured
        self.creation_date = datetime.utcnow()

    def json(self):
        return dict(
            id=self.id,
            lastname=self.lastname,
            firstname=self.firstname,
            username=self.username,
            biometric_captured=self.biometric_captured,
            creation_date=str(self.creation_date) + ' UTC'
        )

    @staticmethod
    def verify_fields(lastname=None,firstname=None, username=None):
        message = None
        if lastname != None:
            if len(lastname) > Student.LAST_NAME_MAX_LENGTH:
                message = 'Last Name must not exceed {0} characters.'.format(Student.LAST_NAME_MAX_LENGTH)
        if firstname != None:
            if len(firstname) > Student.FIRST_NAME_MAX_LENGTH:
                message = 'Frst Name must not exceed {0} characters.'.format(Student.FIRST_NAME_MAX_LENGTH)

        if username != None:
            if len(username) > Student.USER_NAME_MAX_LENGTH:
                message = 'Username must not exceed {0} characters.'.format(Student.USER_NAME_MAX_LENGTH)
        return message == None, message
