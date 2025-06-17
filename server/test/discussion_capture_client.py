import requests
import json

class DiscussionCaptureAPIClient():

    def __init__(self, url, client_id, client_secret, https=False):
        self.url = '{0}://{1}'.format('https' if https else 'http', url)
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None

    def get_token(self):
        headers = {
            'X-Client-Id': self.client_id,
            'X-Client-Secret': self.client_secret
        }
        response = requests.get(self.url + '/api/v1/token', headers=headers)
        self.token = response.json().get('token', None)
        return True

    def get_headers(self):
        if not self.token:
            self.get_token()
        return {
            'X-Client-Id': self.client_id,
            'X-Client-Token': self.token
        }

    def create_session(self, name=None, keywordListId=None, byod=None, features=None, doa=None):
        payload = {}
        if name:
            payload['name'] = name
        if keywordListId:
            payload['keywordListId'] = keywordListId
        if byod:
            payload['byod'] = byod
        if features:
            payload['features'] = features
        if doa:
            payload['doa'] = doa
        response = requests.post(self.url + '/api/v1/sessions', json=payload, headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        return None

    def stop_session(self, session_id):
        response = requests.post(self.url + '/api/v1/sessions/{0}/stop'.format(session_id), headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        return None

    def delete_session(self, session_id):
        response = requests.delete(self.url + '/api/v1/sessions/{0}'.format(session_id), headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        return None

    def create_session_device(self, session_id, name):
        payload = {
            'name': name
        }
        response = requests.post(self.url + '/api/v1/sessions/{0}/devices'.format(session_id), json=payload, headers=self.get_headers())
        if response.status_code == 200:
            return response.json()
        return None