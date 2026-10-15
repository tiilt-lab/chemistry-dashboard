from app import db
from datetime import datetime, timezone

class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # The name-based sign-up form (until 2026-10-14) stored a first and last
    # name; the form now asks for a username plus the student's group and
    # team, nothing else. Old records keep their names for display.
    lastname = db.Column(db.String(50), nullable=True)
    firstname = db.Column(db.String(50), nullable=True)
    username = db.Column(db.String(20), nullable=False)
    # The group (table) and team (or role) the student typed when enrolling,
    # as the class names them. The coding pass reads the team off the
    # profile when the session's devices did not fix it.
    group_name = db.Column(db.String(64), nullable=True)
    team_name = db.Column(db.String(64), nullable=True)
    biometric_captured = db.Column(db.String(3), nullable=True) 
    creation_date = db.Column(db.DateTime, nullable=False)


    LAST_NAME_MAX_LENGTH = 50
    FIRST_NAME_MAX_LENGTH = 50
    USER_NAME_MAX_LENGTH = 20
    USER_NAME_MIN_LENGTH = 5
    LABEL_MAX_LENGTH = 64

    def __hash__(self):
        return hash(self.id)

    def __init__(self, username, *, biometric_captured='no', group_name=None,
                 team_name=None, firstname=None, lastname=None):
        self.username = username
        self.group_name = group_name
        self.team_name = team_name
        self.firstname = firstname
        self.lastname = lastname
        self.biometric_captured = biometric_captured
        self.creation_date = datetime.now(timezone.utc).replace(tzinfo=None)

    @property
    def legacy_name(self):
        """The first and last name of a record from the old form, or ''."""
        return " ".join(p for p in (self.firstname, self.lastname) if p)

    @property
    def name(self):
        """What the pages show: the old form's first and last name when a
        record has one, else the username."""
        return self.legacy_name or self.username

    @staticmethod
    def _norm(value):
        return " ".join(str(value or "").split()).lower()

    def identity_matches(self, group_name=None, team_name=None):
        """Self-service re-enrollment proof (students have no passwords):
        the group and team on record must be typed again, compared
        case-insensitively with spacing ignored. It stops a classmate from
        casually overwriting someone else's voice print by typing their
        username, nothing more. A record with neither on file (the old
        form's) accepts a blank group and team."""
        n = Student._norm
        return n(self.group_name) == n(group_name) and n(self.team_name) == n(team_name)

    def json(self):
        return dict(
            id=self.id,
            lastname=self.lastname,
            firstname=self.firstname,
            username=self.username,
            name=self.name,
            group_name=self.group_name,
            team_name=self.team_name,
            biometric_captured=self.biometric_captured,
            creation_date=str(self.creation_date) + ' UTC'
        )

    @staticmethod
    def verify_fields(lastname=None,firstname=None, username=None, group_name=None, team_name=None):
        message = None
        if lastname is not None:
            if len(lastname) > Student.LAST_NAME_MAX_LENGTH:
                message = 'Last Name must not exceed {0} characters.'.format(Student.LAST_NAME_MAX_LENGTH)
        if firstname is not None:
            if len(firstname) > Student.FIRST_NAME_MAX_LENGTH:
                message = 'Frst Name must not exceed {0} characters.'.format(Student.FIRST_NAME_MAX_LENGTH)
        for label, value in (('Group', group_name), ('Team', team_name)):
            if value is not None and len(value) > Student.LABEL_MAX_LENGTH:
                message = '{0} must not exceed {1} characters.'.format(label, Student.LABEL_MAX_LENGTH)

        if username is not None:
            if len(username) > Student.USER_NAME_MAX_LENGTH:
                message = 'Username must not exceed {0} characters.'.format(Student.USER_NAME_MAX_LENGTH)
        return message is None, message
