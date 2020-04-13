import argparse
import os
from discussion_capture_client import DiscussionCaptureAPIClient
from audio_processor_client import AudioProcessorClient

# This example creates a session, adds a device, and transmits
# a wave file using the newly created device's credentials.
# Finally this example, closes the session.
def main():
    # --- Command line arguments ---
    # parser = argparse.ArgumentParser()
    # parser.add_argument('--ip', type=str, help='IP of the server')
    # parser.add_argument('--id', type=str, help='Client ID for API access')
    # parser.add_argument('--secret', type=str, help='Client Secret for API access')
    # parser.add_argument('--file', type=str, help='The wave file to transmit')
    # parser.add_argument('--https', type=bool, nargs='?', default=False, help='Wethoer or not the server is behind https')
    # args = parser.parse_args()

    # if not os.path.exists(args.file):
    #     print('File does not exist.')
    #     return

    # --- Debug input ---
    ip = '192.168.99.135'
    usr = 'api'
    psd = 'J5FND04N0O8XLHQE'
    client_id = '4297ad8bfe88011a7277d38fc03ee6e3c2b499d1195da59f926c4a440c4c9e5d'
    client_secret = '6f97f4c2e131a8940256a425859e7403380e3c5169dca4ccd1d8cca096ff4b3c'
    filename = './test.wav'
    https = False

    api = DiscussionCaptureAPIClient(ip, client_id, client_secret, https)
    session = api.create_session(name='test', keywordListId=1, features=True)
    print('Session {0} created.'.format(session.get('id')))
    session_device = api.create_session_device(session.get('id'), 'test device')
    print('Session device {0} created.'.format(session_device.get('session_device').get('id')))
    apc = AudioProcessorClient(ip, False)
    print('Audio file is being transmitted...please wait...')
    apc.start(filename, session_device.get('key'))
    with apc.lock:
        print('Audio file sent.')
    api.stop_session(session.get('id'))
    print('Session {0} closed.'.format(session.get('id')))

if __name__ == '__main__':
    main()
