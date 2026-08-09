"""Shared autobahn message handling for the audio & video WebSocket services.

The live and post-hoc protocols in both services (four classes) carried
byte-identical onMessage/onClose bodies — with one exception: only one of the
four logged the full traceback when process_json raised. The other three
logged str(e) and discarded the stack, making a post-hoc failure hard to
locate. This mixin is that handling, once, with the traceback everywhere.

Subclasses (which also inherit autobahn's WebSocketServerProtocol) provide:
    process_binary(payload), process_json(data), send_json(message), signal_end()
and are expected to have a ``last_message`` attribute (inactivity watchdog).
"""
import json
import logging
import time
import traceback


class WsMessageMixin:
    def onMessage(self, payload, is_binary):
        self.last_message = time.time()
        if is_binary:
            try:
                self.process_binary(payload)
            except Exception as e:
                logging.warning('Error processing binary: {0}'.format(e))
            return
        try:
            payload = payload.decode('utf-8')
            data = json.loads(payload)
        except Exception:
            logging.warning('Payload is not properly formatted JSON.')
            self.send_json({'type': 'error', 'message': 'Payload is not properly formatted JSON.'})
            return
        try:
            self.process_json(data)
        except Exception:
            # Full traceback: three of the four copies logged only str(e),
            # throwing away the stack that pinpoints the failure.
            logging.warning('Error processing json: %s', traceback.format_exc())

    def onClose(self, wasClean, code, reason):
        logging.info("close was triggered externally..... wasclean {0}, code {1}, reason {2}".format(
            wasClean, code, reason))
        self.signal_end()
