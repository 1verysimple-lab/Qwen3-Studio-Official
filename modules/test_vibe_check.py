import tkinter as tk
from tkinter import ttk, messagebox

def initialize(app):
    """
    Vibe Check Test Module.
    Used to verify the Module Hub synchronization and loading logic.
    """
    plugin_tab = ttk.Frame(app.notebook)
    app.notebook.add(plugin_tab, text="✨ Vibe Check")
    
    f = tk.Frame(plugin_tab, padding=40)
    f.pack(fill=tk.BOTH, expand=True)
    
    tk.Label(f, text="✨ Plugin System: ONLINE", font=("Segoe UI", 16, "bold")).pack(pady=10)
    tk.Label(f, text="This module was loaded successfully via the Module Hub registry.", font=("Segoe UI", 10)).pack()
    
    def ping():
        messagebox.showinfo("Vibe Check", "The synchronization engine is ready for deployment!")
        
    ttk.Button(f, text="Test Connection", command=ping).pack(pady=20)
    
    print("Module 'test_vibe_check' initialized successfully.")
