import requests

class AnalyticsClient:
    def __init__(self, base_url, admin_token, auth_header="X-Admin-Token"):
        self.base_url = f"{base_url}/analytics"
        self.headers = {auth_header: admin_token}

    def get_traffic_metrics(self, periode="24h"):
        resp = requests.get(f"{self.base_url}/trafic", params={"periode": periode}, headers=self.headers, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def list_alerts(self, non_acquittees=True):
        resp = requests.get(f"{self.base_url}/anomalies", params={"non_acquittees": non_acquittees}, headers=self.headers, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def acknowledge_alert(self, alert_id):
        resp = requests.get(f"{self.base_url}/alertes/{alert_id}/acquitter", headers=self.headers, timeout=5)
        resp.raise_for_status()
        return resp.json()
