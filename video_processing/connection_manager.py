import time
import logging
import threading

class ConnectionManager:
    def __init__(self):
        self.lock = threading.RLock()
        self.connections = []
        self.connections_by_session = {}
        self.connections_by_auth = {}

    def check_connections(self):
        with self.lock:
            for connection in list(self.connections):
                if time.time() - connection.last_message > 30:
                    logging.warning('Closing client due to inactivity.')
                    connection.send_close('Connection closed due to inactivity.')
                    connection.signal_end()

    def check_connection_authentication(self):
        with self.lock:
            for connection in list(self.connections):
                if connection.running and not connection.config.is_valid_key():
                    logging.info('Closing client due to expired key.')
                    connection.send_close('Your access has been revoked.')
                    connection.signal_end()

    def add(self, connection):
        with self.lock:
            if not connection in self.connections:
                self.connections.append(connection)

    def associate_keys(self, connection, session_key, auth_key):
        with self.lock:
            # Maintains associated connections by session
            if not session_key in self.connections_by_session:
                self.connections_by_session[session_key] = [connection]
            else:
                self.connections_by_session[session_key].append(connection)

            # Maintains that only one connection can use a key at a time.
            if not auth_key in self.connections_by_auth:
                self.connections_by_auth[auth_key] = connection
            else:
                self.connections_by_auth[auth_key].send_close('Another connection is using the same credentials.')
                self.connections_by_auth[auth_key].signal_end()
                self.connections_by_auth[auth_key] = connection

    def get_associated_connections(self, session_key):
        with self.lock:
            if not session_key in self.connections_by_session:
                return []
            else:
                return self.connections_by_session[session_key]

    def remove(self, connection, session_key, auth_key):
        with self.lock:
            if connection in self.connections:
                self.connections.remove(connection)
            if session_key and session_key in self.connections_by_session and connection in self.connections_by_session[session_key]:
                self.connections_by_session[session_key].remove(connection)
                if len(self.connections_by_session[session_key]) == 0:
                    del self.connections_by_session[session_key]

            if auth_key and auth_key in self.connections_by_auth and self.connections_by_auth[auth_key] == connection:
                del self.connections_by_auth[auth_key]