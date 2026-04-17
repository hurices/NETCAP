import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class GraphWidget(ttk.Frame):
    def __init__(self, parent, title="Distribution", chart_type="pie", **kwargs):
        super().__init__(parent, **kwargs)
        self.title = title
        self.chart_type = chart_type
        self.fig, self.ax = plt.subplots(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_chart(self, data: dict | list, labels_key="domaine", values_key="count"):
        self.ax.clear()
        
        if self.chart_type == "pie":
            if isinstance(data, dict) and data:
                labels = list(data.keys())
                values = list(data.values())
                self.ax.pie(values, labels=labels, autopct='%1.1f%%')
                self.ax.set_title(self.title)
        
        elif self.chart_type == "bar":
            if isinstance(data, list) and data:
                labels = [d[labels_key] for d in data[:5]]
                values = [d[values_key] for d in data[:5]]
                self.ax.bar(labels, values, color='skyblue')
                self.ax.set_title(self.title)
                self.ax.tick_params(axis='x', rotation=45)
                self.fig.tight_layout()
        
        self.canvas.draw()
