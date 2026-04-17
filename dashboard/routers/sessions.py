import requests

class SessionsClient:
    def __init__(self, base_url, admin_token, auth_header="X-Admin-Token"):
        self.base_url = f"{base_url}/sessions"
        self.headers = {auth_header: admin_token}

    def list_sessions(self):
        resp = requests.get(self.base_url, headers=self.headers, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def revoke_session(self, ip_client):
        resp = requests.delete(f"{self.base_url}/{ip_client}", headers=self.headers, timeout=5)
        resp.raise_for_status()
        return resp.json()
