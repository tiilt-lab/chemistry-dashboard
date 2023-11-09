from twisted.python import log
from twisted.internet import reactor, task
from autobahn.twisted.websocket import WebSocketServerFactory
from autobahn.twisted.websocket import WebSocketServerProtocol
from app import socketio
import json
import time
import threading
import database
import logging
import time
import uuid

class ConnectionManager:
    instance = None

    def __init__(self):
        ConnectionManager.instance = self
        self.connections = []
        self.jobs = {}

    def add_connection(self, device_id, socket):
        match = next((conn for conn in self.connections if conn['id'] == device_id), None)
        if match:
            self.remove_connection(match['id'], match['socket'])
        self.connections.append({'id':device_id, 'socket': socket})
        database.set_device_connected(device_id, True)
        database.close_session()
        print(len(self.connections))

    def remove_connection(self, device_id, socket):
        match = next((conn for conn in self.connections if conn['id'] == device_id and conn['socket'] == socket), None)
        if match != None:
            database.set_device_connected(device_id, False)
            self.connections = [conn for conn in self.connections if conn['id'] != device_id]
            database.close_session()
            logging.info('Device {0} has disconnected.'.format(device_id))

    def send_command_and_wait(self, device_id, command):
        match = next((conn for conn in self.connections if conn['id'] == device_id), None)
        success = False
        response = None
        if match:
            job = Job()
            command['job_id'] = job.job_id
            self.jobs[job.job_id] = job
            match['socket'].send_json(command)
            while not job.is_timed_out() and not job.is_complete():
                time.sleep(0.1)
            if job.is_complete():
                success = True
                response = job.response_data
            self.jobs.pop(job.job_id)
        return success, response

    def send_command(self, device_id, command):
        match = next((conn for conn in self.connections if conn['id'] == device_id), None)
        if match:
            match['socket'].send_json(command)
            return True
        return False

    def update_job(self, job_id, response):
        job = self.jobs.get(job_id, None)
        if job:
            job.add_response(response)

class Job:
    def __init__(self, timeout=15.0):
        self.job_id = str(uuid.uuid4())
        self.request_time = time.time()
        self.timeout = timeout
        self.response_time = None
        self.response_data = None

    def add_response(self, data):
        self.response_time = time.time()
        self.response_data = data

    def is_complete(self):
        return self.response_time != None

    def is_timed_out(self):
        return time.time() > self.request_time + self.timeout


class ServerProtocol(WebSocketServerProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_message = time.time()
        self.device_id = None

    def onOpen(self):
        logging.info('Device connected to device websocket...')

    def onMessage(self, payload, is_binary):
        self.last_message = time.time()
        if not is_binary:
            try:
                payload = payload.decode('utf-8')
                data = json.loads(payload)
                self.process_json(data)
            except Exception as e:
                logging.info('Payload is not properly formatted JSON: ' + str(e))

    def onClose(self, *args, **kwargs):
        if self.device_id:
            ConnectionManager.instance.remove_connection(self.device_id, self)

    def process_json(self, data):
        cmd = data.get('cmd', None)

        # Verify message and authenticate.
        if not cmd:
            logging.info('Message missing "cmd".')
            return
        elif cmd == 'auth':
            mac_address = data.get('key', None)
            device = database.get_devices(mac_addr=mac_address, archived=False)
            if device:
                self.device_id = device.id
                ConnectionManager.instance.add_connection(self.device_id, self)
                self.send_json({'cmd': 'auth', 'status': True})
                logging.info('Device {0} has been authenticated and is now connected.'.format(self.device_id))
                session_device = database.get_device_active_session_device(self.device_id)
                if session_device:
                    logging.info('Requesting device {0} join session {1}.'.format(self.device_id, session_device.session_id))
                    self.send_json({'cmd': 'start', 'key': session_device.processing_key})
            database.close_session()

        # Reject any connection that tries to message before authenticating.
        if not self.device_id:
            self.send_json({'cmd': 'auth', 'status': False})
            logging.info('An unauthenticated device has skipped or failed authentication...rejecting connection.')
            self.close_connection()
            return

        # Capture job responses.
        job_id = data.get('job_id', None)
        if job_id:
            ConnectionManager.instance.update_job(job_id, data)

        # Handle commands.
        if cmd == 'help':
            device_key = data.get('key', None)
            state = data.get('state', None)
            session_device = database.get_session_devices(processing_key=device_key)
            if session_device and session_device.button_pressed != state:
                session_device.button_pressed = state
                database.save_changes()
                room_name = str(session_device.session_id)
                socketio.emit('device_update', json.dumps(session_device.json()), room=room_name, namespace="/session")
            database.close_session()

    def close_connection(self):
        self.transport.loseConnection()

    def send_json(self, message):
        payload = json.dumps(message).encode('utf8')
        self.sendMessage(payload, isBinary = False)


def run_server():
    ConnectionManager()
    factory = WebSocketServerFactory()
    factory.protocol = ServerProtocol
    reactor.listenTCP(9001, factory, interface='127.0.0.1')
    thread = threading.Thread(target=reactor.run, kwargs={'installSignalHandlers': False})
    thread.daemon = True
    thread.start()

if __name__ == '__main__':
    run_server()
    data = ''
    while(data != 'q'):
        input()
        ConnectionManager.instance.send_command_and_wait(1, {'cmd': 'mac_address'})
