from app import db
from utility import verify_characters

class Device(db.Model):
    __tablename__ = 'device'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(64))
    ip_address = db.Column(db.String(64))
    mac_address = db.Column(db.String(64))
    connected = db.Column(db.Boolean, nullable=False)
    archived = db.Column(db.Boolean, nullable=False)
    is_pod = db.Column(db.Boolean, nullable=False)

    NAME_MAX_LENGTH = 64
    NAME_CHARS = 'a-zA-Z0-9\': '
    IP_MAX_LENGTH = 64
    MAC_MAX_LENGTH = 64

    def __hash__(self):
        return hash((self.id))

    def __init__(self, name=None, archived=False, ip_address=None, mac_address=None, is_pod=True):
        self.ip_address = ip_address
        self.connected = False
        self.name = name
        self.mac_address = mac_address
        self.archived = archived
        self.is_pod = is_pod

    def get_name(self):
        if self.name:
            return self.name
        else:
            return "{0} {1}".format('Pod' if self.is_pod else 'Device', self.id)

    def json(self):
        return dict(
            id=self.id,
            ip_address=self.ip_address,
            connected=self.connected,
            mac_address=self.mac_address,
            archived=self.archived,
            name=self.get_name(),
            is_pod=self.is_pod
        )
    @staticmethod
    def verify_fields(name=None, mac_address=None, ip_address=None):
        message = None
        if name != None:
            if len(name) > Device.NAME_MAX_LENGTH:
                message = 'Device name must not exceed {0} characters.'.format(Device.NAME_MAX_LENGTH)
            if not verify_characters(name, Device.NAME_CHARS):
                message = 'Invalid characters in device name.'
        if mac_address != None:
            if len(mac_address) > Device.MAC_MAX_LENGTH:
                message = 'Device mac address must not exceed {0} characters.'.format(Device.MAC_MAX_LENGTH)
            elif mac_address == None:
                message = 'Device mac address cannot be empty.'
        if ip_address != None:
            if len(ip_address) > Device.IP_MAX_LENGTH:
                message = 'Device ip address must not exceed {0} characters.'.format(Device.IP_MAX_LENGTH)
        return message == None, message

