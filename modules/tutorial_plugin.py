import tkinter as tk

def initialize(app):
    """
    This plugin enables the 'Tutorial' tab in the main application.
    The main app window handles the creation and logic for this tab.
    This file simply needs to exist and be enabled in the Module Hub.
    """
    
    # The 'Generate Tutorial' button is now integrated into the main Help menu
    # if the tutorial plugin is active. We find the help menu and add our command.
    
    # This is a bit of a deep dive into the menu structure, might need adjustment
    # if the main app's help menu changes.
    try:
        # The Help menu is the last cascade menu in the menu bar.
        help_menu = app.root.nametowidget(app.root.cget('menu')).winfo_children()[-1]
        
        # Add a separator and our command
        help_menu.add_separator()
        help_menu.add_command(
            label="Interactive Tutorial",
            command=lambda: app.notebook.select(app.tab_tutorial)
        )
    except Exception as e:
        print(f"Failed to inject tutorial link into help menu: {e}")
        # Fallback: If menu injection fails, create a button in the header as before
        # This makes the feature more robust against UI changes.
        try:
            tut_row = tk.Frame(app.brand_frame, bg=app.colors["header_bg"])
            tut_row.pack(anchor=tk.W, pady=(5,0))
            btn = tk.Button(tut_row, text="🎓 Tutorial", 
                command=lambda: app.notebook.select(app.tab_tutorial), 
                bg=app.colors["accent"], fg="white", font=("Segoe UI", 8, "bold"), 
                bd=0, padx=8, pady=2, cursor="hand2")
            btn.pack(side=tk.LEFT)
        except Exception as e2:
            print(f"Fallback tutorial button also failed: {e2}")

    print("Tutorial Plugin Initialized: Tab and menu item enabled.")
