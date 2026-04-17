import tkinter as tk
from tkinter import ttk, messagebox
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
from datetime import datetime

# Import widgets locaux
try:
    from dashboard.widgets.stats_widget import StatsWidget
    from dashboard.widgets.graph_widget import GraphWidget
    from dashboard.widgets.alert_widget import AlertWidget
    from dashboard.routers.sessions import SessionsClient
    from dashboard.routers.analytics import AnalyticsClient
    from dashboard.routers.config import ConfigClient
except ImportError:
    from widgets.stats_widget import StatsWidget
    from widgets.graph_widget import GraphWidget
    from widgets.alert_widget import AlertWidget
    from routers.sessions import SessionsClient
    from routers.analytics import AnalyticsClient
    from routers.config import ConfigClient

import config


class NetCaptDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("NetCapt - Administration Dashboard")
        self.root.geometry("1200x800")
        
        # Configuration des styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.api_url = config.API_URL
        self.admin_token = config.ADMIN_TOKEN
        
        # Clients API modularisés
        self.client_sessions = SessionsClient(self.api_url, self.admin_token, config.ADMIN_TOKEN_HEADER)
        self.client_analytics = AnalyticsClient(self.api_url, self.admin_token, config.ADMIN_TOKEN_HEADER)
        self.client_config = ConfigClient(self.api_url, self.admin_token, config.ADMIN_TOKEN_HEADER)
        
        self._setup_ui()
        
        # État des données
        self.metrics = {}
        self.sessions = []
        self.alerts = []
        
        # Démarrer le rafraîchissement automatique
        self.refresh_data()

    def _setup_ui(self):
        # Header
        header = ttk.Frame(self.root, padding="10")
        header.pack(fill=tk.X)
        ttk.Label(header, text="NetCapt Monitor", font=("Helvetica", 18, "bold")).pack(side=tk.LEFT)
        self.status_label = ttk.Label(header, text="Status: Connecting...", foreground="orange")
        self.status_label.pack(side=tk.RIGHT)

        # Main Notebook (Tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Création des onglets
        self.tab_overview = ttk.Frame(self.notebook)
        self.tab_sessions = ttk.Frame(self.notebook)
        self.tab_traffic = ttk.Frame(self.notebook)
        self.tab_domains = ttk.Frame(self.notebook)
        self.tab_alerts = ttk.Frame(self.notebook)
        self.tab_config = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_overview, text="Vue Générale")
        self.notebook.add(self.tab_sessions, text="Sessions Actives")
        self.notebook.add(self.tab_traffic, text="Trafic en Direct")
        self.notebook.add(self.tab_domains, text="Top Domaines")
        self.notebook.add(self.tab_alerts, text="Alertes")
        self.notebook.add(self.tab_config, text="Configuration")

        self._setup_tab_overview()
        self._setup_tab_sessions()
        self._setup_tab_traffic()
        self._setup_tab_domains()
        self._setup_tab_alerts()
        self._setup_tab_config()

    def _setup_tab_overview(self):
        self.widget_stats = StatsWidget(self.tab_overview)
        self.widget_stats.pack(fill=tk.BOTH, expand=True)

    def _setup_tab_sessions(self):
        container = ttk.Frame(self.tab_sessions, padding="10")
        container.pack(fill=tk.BOTH, expand=True)
        
        # Treeview pour les sessions
        cols = ("ID", "IP", "Utilisateur", "Requêtes", "Volume (MB)", "Expiration")
        self.tree_sessions = ttk.Treeview(container, columns=cols, show='headings')
        for col in cols:
            self.tree_sessions.heading(col, text=col)
            self.tree_sessions.column(col, width=100)
        
        self.tree_sessions.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.tree_sessions.yview)
        self.tree_sessions.configure(yscroll=scrollbar.set)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        
        # Boutons d'action
        btn_frame = ttk.Frame(self.tab_sessions, padding="5")
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Révoquer Session", command=self.revoke_session).pack(side=tk.LEFT, padx=5)

    def _setup_tab_traffic(self):
        self.widget_traffic = GraphWidget(self.tab_traffic, title="Répartition par Catégorie", chart_type="pie")
        self.widget_traffic.pack(fill=tk.BOTH, expand=True)

    def _setup_tab_domains(self):
        self.widget_domains = GraphWidget(self.tab_domains, title="Top 5 Domaines", chart_type="bar")
        self.widget_domains.pack(fill=tk.BOTH, expand=True)

    def _setup_tab_alerts(self):
        self.widget_alerts = AlertWidget(self.tab_alerts, acknowledge_callback=self.acknowledge_alert_by_id)
        self.widget_alerts.pack(fill=tk.BOTH, expand=True)

    def _setup_tab_config(self):
        container = ttk.Frame(self.tab_config, padding="20")
        container.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(container, text="Paramètres du Système", font=("Helvetica", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=10)
        
        fields = [
            ("Seuil Z-Score", "zscore_seuil"),
            ("Volume Max (MB)", "volume_max_session_mb"),
            ("Durée Max (min)", "duree_session_max_min"),
            ("Requêtes/min Max", "requetes_par_minute_max")
        ]
        
        self.config_vars = {}
        for i, (label, key) in enumerate(fields):
            ttk.Label(container, text=label).grid(row=i+1, column=0, sticky="w", pady=5)
            var = tk.StringVar()
            ttk.Entry(container, textvariable=var).grid(row=i+1, column=1, sticky="ew", pady=5)
            self.config_vars[key] = var
            
        ttk.Button(container, text="Sauvegarder", command=self.save_config).grid(row=len(fields)+1, column=0, columnspan=2, pady=20)

    def refresh_data(self):
        """Récupère les données de l'API via les clients modularisés."""
        try:
            # 1. Alertes
            self.alerts = self.client_analytics.list_alerts()
            self.widget_alerts.update_alerts(self.alerts)
            
            # 2. Métriques globales
            self.metrics = self.client_analytics.get_traffic_metrics()
            self.widget_stats.update_stats(self.metrics, len(self.alerts))
            self._update_charts()
            
            # 3. Sessions
            self.sessions = self.client_sessions.list_sessions()
            self._update_sessions_tree()
                
            self.status_label.config(text=f"Status: Live ({datetime.now().strftime('%H:%M:%S')})", foreground="green")
            
        except Exception as e:
            self.status_label.config(text=f"Status: API Error", foreground="red")
        
        # Planifier le prochain rafraîchissement
        self.root.after(config.REFRESH_INTERVAL_MS, self.refresh_data)

    def _update_sessions_tree(self):
        # Effacer l'ancien contenu
        for i in self.tree_sessions.get_children():
            self.tree_sessions.delete(i)
            
        for s in self.sessions:
            vol_mb = s.get('volume_bytes', 0) / (1024 * 1024)
            self.tree_sessions.insert('', tk.END, values=(
                s.get('session_id', '')[:8],
                s.get('ip_client', ''),
                s.get('user_id', ''),
                s.get('nb_requetes', 0),
                f"{vol_mb:.2f}",
                s.get('expiration', '')[:19].replace('T', ' ')
            ))

    def _update_charts(self):
        # Top Domaines Chart
        top_doms = self.metrics.get("top_domaines", [])
        self.widget_domains.update_chart(top_doms, labels_key="domaine", values_key="count")
            
        # Traffic Split Chart (Pie)
        cats = self.metrics.get("repartition_categories", {})
        self.widget_traffic.update_chart(cats)

    def revoke_session(self):
        selected = self.tree_sessions.selection()
        if not selected:
            return
        
        ip_client = self.tree_sessions.item(selected[0], 'values')[1]
        if messagebox.askyesno("NetCapt", f"Révoquer la session de {ip_client} ?"):
            try:
                self.client_sessions.revoke_session(ip_client)
                self.refresh_data()
            except Exception as e:
                messagebox.showerror("NetCapt", f"Erreur: {e}")

    def acknowledge_alert_by_id(self, alert_id_short):
        full_alert = next((a for a in self.alerts if a['alerte_id'].startswith(alert_id_short)), None)
        
        if full_alert:
            try:
                self.client_analytics.acknowledge_alert(full_alert['alerte_id'])
                self.refresh_data()
            except Exception as e:
                messagebox.showerror("NetCapt", f"Erreur: {e}")

    def save_config(self):
        try:
            new_config = {
                "zscore_seuil": float(self.config_vars["zscore_seuil"].get()),
                "volume_max_session_mb": int(self.config_vars["volume_max_session_mb"].get()),
                "duree_session_max_min": int(self.config_vars["duree_session_max_min"].get()),
                "requetes_par_minute_max": int(self.config_vars["requetes_par_minute_max"].get()),
                "categories_bloquees": [] # TODO: Gérer liste
            }
            
            headers = {config.ADMIN_TOKEN_HEADER: self.admin_token}
            resp = requests.post(f"{self.api_url}/config/seuils", json=new_config, headers=headers)
            if resp.status_code == 200:
                messagebox.showinfo("NetCapt", "Configuration mise à jour.")
            else:
                messagebox.showerror("NetCapt", "Erreur de configuration.")
        except Exception as e:
            messagebox.showerror("NetCapt", f"Données invalides: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = NetCaptDashboard(root)
    root.mainloop()
