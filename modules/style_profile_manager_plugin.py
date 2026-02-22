"""
Style & Profile Manager Plugin v1.0

Adds a dedicated tab for browsing, editing, enabling/disabling
style instructions and design profiles. Disabled items are hidden
from all dropdowns across the app without being deleted.
"""

import tkinter as tk
from tkinter import ttk, messagebox

PLUGIN_NAME = "Style & Profile Manager"

# Built-in style names that ship with populate_default_styles().
# They can be disabled but a warning is shown before deletion.
_BUILTIN_STYLES = {
    "Heartbroken", "Furious", "Panicked", "Seductive", "Sarcastic",
    "Whispering", "Shouting", "Crying", "News Anchor", "Bedtime Story",
    "Meditation Guide", "Drill Sergeant", "Game Show Host", "Auctioneer",
}


# ── Public entry point ────────────────────────────────────────────────────────

def initialize(app):
    """Called by ModuleHub once at startup."""
    cfg = app.app_config
    cfg.setdefault("disabled_styles", [])
    cfg.setdefault("disabled_profiles", [])

    # Patch update_style_combo so disabled styles are hidden app-wide
    _patch_style_combo(app)

    # Patch director.get_styles so batch director blocks filter disabled styles
    if hasattr(app, "director") and app.director is not None:
        _patch_director_styles(app)

    tab = StyleProfileManagerTab(app.notebook, app)
    app.notebook.add(tab, text="🗂 Manager")


# ── Patching helpers ──────────────────────────────────────────────────────────

def _patch_style_combo(app):
    """Replace update_style_combo with a version that filters disabled styles."""
    def _filtered_update():
        disabled = set(app.app_config.get("disabled_styles", []))
        styles = sorted(
            k for k in app.app_config.get("style_instructions", {})
            if k not in disabled
        )
        if hasattr(app, "style_combo_custom"):
            app.style_combo_custom["values"] = styles
        if hasattr(app, "style_combo_design"):
            app.style_combo_design["values"] = styles

    app.update_style_combo = _filtered_update


def _patch_director_styles(app):
    """Wrap director.get_styles to exclude disabled styles."""
    bd = app.director
    _orig = bd.get_styles

    def _filtered():
        disabled = set(app.app_config.get("disabled_styles", []))
        return [s for s in _orig() if s not in disabled]

    bd.get_styles = _filtered


# ── State sync ────────────────────────────────────────────────────────────────

def _sync_app_state(app):
    """Rebuild live app dicts and refresh all dropdowns after any change."""
    disabled_profiles = set(app.app_config.get("disabled_profiles", []))
    all_profiles = app.app_config.get("design_profiles", {})

    # Rebuild the live design_profiles dict (what batch director reads)
    if hasattr(app, "design_profiles"):
        app.design_profiles = {
            k: v for k, v in all_profiles.items()
            if k not in disabled_profiles
        }

    # Refresh style combos (uses the patched version that filters disabled)
    if hasattr(app, "update_style_combo"):
        try:
            app.update_style_combo()
        except Exception:
            pass

    # Refresh batch director style lists + speaker combos
    if hasattr(app, "director") and app.director is not None:
        try:
            app.director.refresh_sm_list()
        except Exception:
            pass


# ── Main tab frame ────────────────────────────────────────────────────────────

class StyleProfileManagerTab(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#f5f5f5")
        self.app = app
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg="#2c3e50", padx=15, pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(
            hdr, text="🗂  Style & Profile Manager",
            bg="#2c3e50", fg="white", font=("Segoe UI", 13, "bold")
        ).pack(side=tk.LEFT)

        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.styles_panel = StylesPanel(nb, self.app)
        nb.add(self.styles_panel, text="  ✨ Styles  ")

        self.profiles_panel = ProfilesPanel(nb, self.app)
        nb.add(self.profiles_panel, text="  🎙 Design Profiles  ")


# ── Shared split-pane base ────────────────────────────────────────────────────

class _BasePanel(tk.Frame):
    """Left = filterable list with enable/disable. Right = inline editor."""

    def __init__(self, parent, app):
        super().__init__(parent, bg="#f0f0f0")
        self.app = app
        self._selected_name = None
        self._list_names = []

        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=4,
                               bg="#cccccc")
        paned.pack(fill=tk.BOTH, expand=True)

        # ── Left panel ────────────────────────────────────────────────────
        left = tk.Frame(paned, bg="white")
        paned.add(left, minsize=230, stretch="never")

        # Search bar
        sf = tk.Frame(left, bg="white", padx=8, pady=8)
        sf.pack(fill=tk.X)
        tk.Label(sf, text="🔍", bg="white",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_list())
        ttk.Entry(sf, textvariable=self.search_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # Stat label  (e.g. "12 items, 2 disabled")
        self.stat_lbl = tk.Label(left, text="", bg="white",
                                 font=("Segoe UI", 8), fg="#999")
        self.stat_lbl.pack(anchor="w", padx=8)

        # Listbox
        lb_frame = tk.Frame(left, bg="white")
        lb_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(
            lb_frame, selectmode=tk.SINGLE, font=("Segoe UI", 10),
            activestyle="none", selectbackground="#3498db",
            selectforeground="white", bg="white", bd=0,
            highlightthickness=0
        )
        sb = ttk.Scrollbar(lb_frame, orient=tk.VERTICAL,
                           command=self.listbox.yview)
        self.listbox.config(yscrollcommand=sb.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # Bottom controls
        bc = tk.Frame(left, bg="#f4f4f4", padx=8, pady=6)
        bc.pack(fill=tk.X)
        ttk.Button(bc, text="✅ Enable", command=self.enable_selected,
                   width=9).pack(side=tk.LEFT, padx=(0, 3))
        ttk.Button(bc, text="⛔ Disable", command=self.disable_selected,
                   width=9).pack(side=tk.LEFT)
        ttk.Button(bc, text="+ New", command=self.new_item,
                   width=7).pack(side=tk.RIGHT)

        # ── Right panel (editor) ──────────────────────────────────────────
        self.right = tk.Frame(paned, bg="white", padx=14, pady=12)
        paned.add(self.right, stretch="always")

        self._build_editor(self.right)
        self.refresh_list()

    # ── Subclass interface ────────────────────────────────────────────────

    def _all_items(self):       raise NotImplementedError
    def _disabled_set(self):    raise NotImplementedError
    def _build_editor(self, p): raise NotImplementedError
    def _load_into_editor(self, name, data): raise NotImplementedError
    def _clear_editor(self):    raise NotImplementedError
    def save_item(self):        raise NotImplementedError
    def delete_item(self):      raise NotImplementedError
    def new_item(self):         raise NotImplementedError

    def _enable_name(self, name):  raise NotImplementedError
    def _disable_name(self, name): raise NotImplementedError

    # ── Shared list logic ─────────────────────────────────────────────────

    def refresh_list(self):
        query = self.search_var.get().lower()
        disabled = self._disabled_set()
        all_names = sorted(self._all_items().keys())
        filtered = [n for n in all_names if query in n.lower()]

        self.listbox.delete(0, tk.END)
        self._list_names = []

        for name in filtered:
            is_off = name in disabled
            prefix = "  ⊘  " if is_off else "  ✔  "
            self.listbox.insert(tk.END, prefix + name)
            if is_off:
                self.listbox.itemconfig(self.listbox.size() - 1, fg="#aaaaaa")
            self._list_names.append(name)

        n_total = len(all_names)
        n_dis = len([n for n in all_names if n in disabled])
        self.stat_lbl.config(
            text=f"{n_total} items" + (f"  •  {n_dis} disabled" if n_dis else "")
        )

        # Re-select previously selected item if still visible
        if self._selected_name and self._selected_name in self._list_names:
            idx = self._list_names.index(self._selected_name)
            self.listbox.selection_set(idx)
            self.listbox.see(idx)

    def _on_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self._list_names):
            return
        name = self._list_names[sel[0]]
        self._selected_name = name
        self._load_into_editor(name, self._all_items().get(name))

    def enable_selected(self):
        name = self._get_sel()
        if not name:
            return
        self._enable_name(name)
        self.refresh_list()
        _sync_app_state(self.app)
        # Refresh status label in editor if this item is loaded
        if self._selected_name == name:
            self._load_into_editor(name, self._all_items().get(name))

    def disable_selected(self):
        name = self._get_sel()
        if not name:
            return
        self._disable_name(name)
        self.refresh_list()
        _sync_app_state(self.app)
        if self._selected_name == name:
            self._load_into_editor(name, self._all_items().get(name))

    def _get_sel(self):
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self._list_names):
            return None
        return self._list_names[sel[0]]


# ── Styles panel ──────────────────────────────────────────────────────────────

class StylesPanel(_BasePanel):

    def _all_items(self):
        return self.app.app_config.get("style_instructions", {})

    def _disabled_set(self):
        return set(self.app.app_config.get("disabled_styles", []))

    # ── Editor ───────────────────────────────────────────────────────────

    def _build_editor(self, p):
        tk.Label(p, text="Style Editor", font=("Segoe UI", 12, "bold"),
                 bg="white", fg="#2c3e50").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        tk.Label(p, text="Name:", bg="white",
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w")
        self.name_entry = ttk.Entry(p, font=("Segoe UI", 10), width=30)
        self.name_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0))

        tk.Label(p, text="Instruction:", bg="white",
                 font=("Segoe UI", 9)).grid(
            row=2, column=0, sticky="nw", pady=(10, 0))
        self.instr_text = tk.Text(
            p, height=9, font=("Segoe UI", 10), wrap=tk.WORD,
            bg="#f8f9fa", relief="flat", bd=0,
            highlightthickness=1, highlightbackground="#ddd",
            highlightcolor="#3498db"
        )
        self.instr_text.grid(row=2, column=1, sticky="nsew",
                             padx=(8, 0), pady=(10, 0))

        self.status_lbl = tk.Label(p, text="", bg="white",
                                   font=("Segoe UI", 8, "italic"), fg="#7f8c8d")
        self.status_lbl.grid(row=3, column=0, columnspan=2,
                             sticky="w", pady=(6, 0))

        btn_f = tk.Frame(p, bg="white")
        btn_f.grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(btn_f, text="💾 Save", command=self.save_item).pack(
            side=tk.LEFT, padx=(0, 6))
        self.del_btn = ttk.Button(btn_f, text="🗑 Delete",
                                  command=self.delete_item)
        self.del_btn.pack(side=tk.LEFT)

        p.columnconfigure(1, weight=1)
        p.rowconfigure(2, weight=1)
        self._clear_editor()

    def _clear_editor(self):
        self.name_entry.delete(0, tk.END)
        self.instr_text.delete("1.0", tk.END)
        self.status_lbl.config(text="Select a style from the list, or click + New",
                               fg="#7f8c8d")
        self._selected_name = None

    def _load_into_editor(self, name, data):
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, name)
        self.instr_text.delete("1.0", tk.END)
        self.instr_text.insert("1.0", data or "")

        is_disabled = name in self._disabled_set()
        is_builtin = name in _BUILTIN_STYLES
        parts = []
        if is_builtin:
            parts.append("⭐ Built-in")
        parts.append("⊘ Disabled" if is_disabled else "✔ Enabled")
        self.status_lbl.config(
            text="  •  ".join(parts),
            fg="#e74c3c" if is_disabled else "#27ae60"
        )

    def new_item(self):
        self._selected_name = None
        self.name_entry.delete(0, tk.END)
        self.instr_text.delete("1.0", tk.END)
        self.name_entry.insert(0, "New Style")
        self.name_entry.focus()
        self.name_entry.selection_range(0, tk.END)
        self.status_lbl.config(text="New — enter a name and instruction, then Save",
                               fg="#e67e22")

    def save_item(self):
        name = self.name_entry.get().strip()
        instr = self.instr_text.get("1.0", tk.END).strip()

        if not name:
            messagebox.showwarning("Required", "Style name cannot be empty.")
            return
        if not instr:
            messagebox.showwarning("Required", "Instruction cannot be empty.")
            return

        styles = self.app.app_config.setdefault("style_instructions", {})

        # Handle rename
        if self._selected_name and self._selected_name != name:
            if name in styles and not messagebox.askyesno(
                    "Overwrite", f"'{name}' already exists. Overwrite it?"):
                return
            styles.pop(self._selected_name, None)
            # Keep disabled state under the new name
            dis = self.app.app_config.get("disabled_styles", [])
            if self._selected_name in dis:
                dis.remove(self._selected_name)
                dis.append(name)

        styles[name] = instr
        self._selected_name = name
        self.app.save_app_config()
        self.refresh_list()
        _sync_app_state(self.app)
        self.status_lbl.config(text=f"✔ Saved '{name}'", fg="#27ae60")

    def delete_item(self):
        name = self._selected_name or self.name_entry.get().strip()
        if not name:
            return

        msg = f"Permanently delete style '{name}'?"
        if name in _BUILTIN_STYLES:
            msg = (f"'{name}' is a built-in style.\n\n"
                   f"Delete it permanently? (You can Disable it instead "
                   f"to hide it while keeping it recoverable.)")
        if not messagebox.askyesno("Confirm Delete", msg):
            return

        self.app.app_config.get("style_instructions", {}).pop(name, None)
        dis = self.app.app_config.get("disabled_styles", [])
        if name in dis:
            dis.remove(name)
        self.app.save_app_config()
        self._clear_editor()
        self.refresh_list()
        _sync_app_state(self.app)

    def _enable_name(self, name):
        dis = self.app.app_config.setdefault("disabled_styles", [])
        if name in dis:
            dis.remove(name)
        self.app.save_app_config()

    def _disable_name(self, name):
        dis = self.app.app_config.setdefault("disabled_styles", [])
        if name not in dis:
            dis.append(name)
        self.app.save_app_config()


# ── Profiles panel ────────────────────────────────────────────────────────────

class ProfilesPanel(_BasePanel):

    def _all_items(self):
        return self.app.app_config.get("design_profiles", {})

    def _disabled_set(self):
        return set(self.app.app_config.get("disabled_profiles", []))

    def _is_builtin(self, name):
        return hasattr(self.app, "voice_recipes") and name in self.app.voice_recipes

    # ── Editor ───────────────────────────────────────────────────────────

    def _build_editor(self, p):
        tk.Label(p, text="Design Profile Editor",
                 font=("Segoe UI", 12, "bold"),
                 bg="white", fg="#2c3e50").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        tk.Label(p, text="Name:", bg="white",
                 font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w")
        self.name_entry = ttk.Entry(p, font=("Segoe UI", 10), width=30)
        self.name_entry.grid(row=1, column=1, sticky="ew", padx=(8, 0))

        tk.Label(p, text="Voice Description:", bg="white",
                 font=("Segoe UI", 9)).grid(
            row=2, column=0, sticky="nw", pady=(10, 0))
        self.desc_text = tk.Text(
            p, height=5, font=("Segoe UI", 10), wrap=tk.WORD,
            bg="#f8f9fa", relief="flat", bd=0,
            highlightthickness=1, highlightbackground="#ddd",
            highlightcolor="#3498db"
        )
        self.desc_text.grid(row=2, column=1, sticky="nsew",
                            padx=(8, 0), pady=(10, 0))

        tk.Label(p, text="Style Instruction:", bg="white",
                 font=("Segoe UI", 9)).grid(
            row=3, column=0, sticky="nw", pady=(8, 0))
        self.instr_text = tk.Text(
            p, height=4, font=("Segoe UI", 10), wrap=tk.WORD,
            bg="#f8f9fa", relief="flat", bd=0,
            highlightthickness=1, highlightbackground="#ddd",
            highlightcolor="#3498db"
        )
        self.instr_text.grid(row=3, column=1, sticky="nsew",
                             padx=(8, 0), pady=(8, 0))

        # Temperature / Top-P row
        sp_f = tk.Frame(p, bg="white")
        sp_f.grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

        tk.Label(sp_f, text="Temperature:", bg="white",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.temp_var = tk.DoubleVar(value=0.8)
        self.lbl_temp = tk.Label(sp_f, text="0.80", bg="white",
                                 font=("Consolas", 9), width=4)
        ttk.Scale(sp_f, from_=0.1, to=1.5, variable=self.temp_var,
                  length=100).pack(side=tk.LEFT, padx=(4, 0))
        self.lbl_temp.pack(side=tk.LEFT)
        self.temp_var.trace_add(
            "write",
            lambda *_: self.lbl_temp.config(text=f"{self.temp_var.get():.2f}")
        )

        tk.Label(sp_f, text="   Top-P:", bg="white",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.top_p_var = tk.DoubleVar(value=0.84)
        self.lbl_p = tk.Label(sp_f, text="0.84", bg="white",
                               font=("Consolas", 9), width=4)
        ttk.Scale(sp_f, from_=0.1, to=1.0, variable=self.top_p_var,
                  length=100).pack(side=tk.LEFT, padx=(4, 0))
        self.lbl_p.pack(side=tk.LEFT)
        self.top_p_var.trace_add(
            "write",
            lambda *_: self.lbl_p.config(text=f"{self.top_p_var.get():.2f}")
        )

        self.status_lbl = tk.Label(p, text="", bg="white",
                                   font=("Segoe UI", 8, "italic"), fg="#7f8c8d")
        self.status_lbl.grid(row=5, column=0, columnspan=2,
                             sticky="w", pady=(6, 0))

        btn_f = tk.Frame(p, bg="white")
        btn_f.grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(btn_f, text="💾 Save", command=self.save_item).pack(
            side=tk.LEFT, padx=(0, 6))
        self.del_btn = ttk.Button(btn_f, text="🗑 Delete",
                                  command=self.delete_item)
        self.del_btn.pack(side=tk.LEFT)

        p.columnconfigure(1, weight=1)
        p.rowconfigure(2, weight=1)
        p.rowconfigure(3, weight=1)
        self._clear_editor()

    def _clear_editor(self):
        self.name_entry.delete(0, tk.END)
        self.desc_text.delete("1.0", tk.END)
        self.instr_text.delete("1.0", tk.END)
        self.temp_var.set(0.8)
        self.top_p_var.set(0.84)
        self.status_lbl.config(
            text="Select a profile from the list, or click + New",
            fg="#7f8c8d"
        )
        self._selected_name = None

    def _load_into_editor(self, name, data):
        if not isinstance(data, dict):
            data = {}
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, name)
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert("1.0", data.get("desc", ""))
        self.instr_text.delete("1.0", tk.END)
        self.instr_text.insert("1.0", data.get("instruct", ""))
        self.temp_var.set(data.get("temp", 0.8))
        self.top_p_var.set(data.get("top_p", 0.84))

        is_disabled = name in self._disabled_set()
        is_builtin = self._is_builtin(name)
        parts = []
        if is_builtin:
            parts.append("⭐ Built-in")
        parts.append("⊘ Disabled" if is_disabled else "✔ Enabled")
        self.status_lbl.config(
            text="  •  ".join(parts),
            fg="#e74c3c" if is_disabled else "#27ae60"
        )

    def new_item(self):
        self._selected_name = None
        self.name_entry.delete(0, tk.END)
        self.desc_text.delete("1.0", tk.END)
        self.instr_text.delete("1.0", tk.END)
        self.temp_var.set(0.8)
        self.top_p_var.set(0.84)
        self.name_entry.insert(0, "New Profile")
        self.name_entry.focus()
        self.name_entry.selection_range(0, tk.END)
        self.status_lbl.config(
            text="New — fill in Name and Voice Description, then Save",
            fg="#e67e22"
        )

    def save_item(self):
        name = self.name_entry.get().strip()
        desc = self.desc_text.get("1.0", tk.END).strip()
        instr = self.instr_text.get("1.0", tk.END).strip()

        if not name:
            messagebox.showwarning("Required", "Profile name cannot be empty.")
            return
        if not desc:
            messagebox.showwarning("Required", "Voice Description cannot be empty.")
            return

        profiles = self.app.app_config.setdefault("design_profiles", {})

        # Handle rename
        if self._selected_name and self._selected_name != name:
            if name in profiles and not messagebox.askyesno(
                    "Overwrite", f"'{name}' already exists. Overwrite it?"):
                return
            profiles.pop(self._selected_name, None)
            dis = self.app.app_config.get("disabled_profiles", [])
            if self._selected_name in dis:
                dis.remove(self._selected_name)
                dis.append(name)

        profiles[name] = {
            "desc": desc,
            "instruct": instr,
            "temp": round(self.temp_var.get(), 2),
            "top_p": round(self.top_p_var.get(), 2),
        }
        self._selected_name = name
        self.app.save_app_config()
        self.refresh_list()
        _sync_app_state(self.app)
        self.status_lbl.config(text=f"✔ Saved '{name}'", fg="#27ae60")

    def delete_item(self):
        name = self._selected_name or self.name_entry.get().strip()
        if not name:
            return

        msg = f"Permanently delete profile '{name}'?"
        if self._is_builtin(name):
            msg = (f"'{name}' is a built-in profile.\n\n"
                   f"Delete it permanently? (You can Disable it instead "
                   f"to hide it while keeping it recoverable.)")
        if not messagebox.askyesno("Confirm Delete", msg):
            return

        self.app.app_config.get("design_profiles", {}).pop(name, None)
        dis = self.app.app_config.get("disabled_profiles", [])
        if name in dis:
            dis.remove(name)
        self.app.save_app_config()
        self._clear_editor()
        self.refresh_list()
        _sync_app_state(self.app)

    def _enable_name(self, name):
        dis = self.app.app_config.setdefault("disabled_profiles", [])
        if name in dis:
            dis.remove(name)
        self.app.save_app_config()

    def _disable_name(self, name):
        dis = self.app.app_config.setdefault("disabled_profiles", [])
        if name not in dis:
            dis.append(name)
        self.app.save_app_config()
