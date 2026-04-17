import tkinter as tk
from tkinter import ttk

class StatsWidget(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, padding="20", **kwargs)
        self.stat_cards = {}
        self._setup_ui()

    def _setup_ui(self):
        stats_info = [
            ("Requêtes Totales", "total_requetes", "0"),
            ("Volume Total", "total_bytes", "0 MB"),
            ("Sessions Actives", "active_sessions", "0"),
            ("Alertes", "total_alerts", "0")
        ]
        
        for i, (label, key, default) in enumerate(stats_info):
            frame = ttk.LabelFrame(self, text=label, padding="10")
            frame.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            self.columnconfigure(i, weight=1)
            
            var = tk.StringVar(value=default)
            lbl = ttk.Label(frame, textvariable=var, font=("Helvetica", 14, "bold"))
            lbl.pack()
            self.stat_cards[key] = var

    def update_stats(self, metrics: dict, nb_alerts: int):
        self.stat_cards["total_requetes"].set(str(metrics.get("total_requetes", 0)))
        vol_mb = metrics.get("total_bytes", 0) / (1024 * 1024)
        self.stat_cards["total_bytes"].set(f"{vol_mb:.2f} MB")
        self.stat_cards["active_sessions"].set(str(metrics.get("utilisateurs_actifs", 0)))
        self.stat_cards["total_alerts"].set(str(nb_alerts))
