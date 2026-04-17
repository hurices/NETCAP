import tkinter as tk
from tkinter import ttk

class AlertWidget(ttk.Frame):
    def __init__(self, parent, acknowledge_callback, **kwargs):
        super().__init__(parent, padding="10", **kwargs)
        self.acknowledge_callback = acknowledge_callback
        self._setup_ui()

    def _setup_ui(self):
        cols = ("ID", "Utilisateur", "Type", "Gravité", "Score", "Heure")
        self.tree = ttk.Treeview(self, columns=cols, show='headings')
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        btn_frame = ttk.Frame(self, padding="5")
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text="Acquitter l'alerte", command=self._on_acknowledge).pack(side=tk.LEFT)

    def _on_acknowledge(self):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0], 'values')
            self.acknowledge_callback(values[0])

    def update_alerts(self, alerts: list):
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        for a in alerts:
            self.tree.insert('', tk.END, values=(
                a.get('alerte_id', '')[:8],
                a.get('user_id', ''),
                "Trafic Anormal",
                "HAUTE",
                f"{a.get('score_zscore', 0):.2f}",
                a.get('timestamp_detection', '')[11:19]
            ))
