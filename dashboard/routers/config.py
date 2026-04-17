import requests

class ConfigClient:
    def __init__(self, base_url, admin_token, headers_config=None):
        self.base_url = f"{base_url}/config"
        # Utiliser le nom du header défini dans config si possible, ou fallback
        self.auth_header = "X-Admin-Token" 
        self.headers = {self.auth_header: admin_token}

    def get_config(self):
        resp = requests.get(self.base_url, headers=self.headers, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def update_config(self, new_config):
        resp = requests.post(self.base_url, json=new_config, headers=self.headers, timeout=5)
        resp.raise_for_status()
        return resp.json()
