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
                if time.time() - connection.last_message > 300:
                    logging.warning('Closing client due to inactivity.')
                    connection.send_close('Connection closed due to inactivity.')
                    connection.signal_end()

    def check_connection_authentication(self):
        # is_valid_key() is an HTTP POST (30s timeout) per running connection.
        # This sweep fires on a 5s LoopingCall on the reactor — done inline,
        # a slow API server blocked ingest for every pod for up to
        # 30s x connections. Validate off-reactor; only the teardown of
        # expired connections is marshalled back onto the reactor.
        from twisted.internet import threads

        if getattr(self, '_auth_sweep_running', False):
            return  # previous sweep still in flight (slow API) — don't stack
        self._auth_sweep_running = True

        with self.lock:
            candidates = [c for c in list(self.connections) if c.running]

        def _sweep(conns=candidates):
            expired = []
            for connection in conns:
                try:
                    if not connection.config.is_valid_key():
                        expired.append(connection)
                except Exception:
                    logging.exception('key validation errored; keeping connection')
            return expired

        def _teardown(expired):
            self._auth_sweep_running = False
            for connection in expired:
                logging.info('Closing client due to expired key.')
                connection.send_close('Your access has been revoked.')
                connection.signal_end()

        def _failed(f):
            self._auth_sweep_running = False
            logging.warning('auth sweep failed: %s', f)

        threads.deferToThread(_sweep).addCallbacks(_teardown, _failed)

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

    def get_number_of_connections(self):
        with self.lock:
            return len(self.connections)
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