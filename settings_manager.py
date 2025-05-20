import importlib
import player_constants
import tkinter as tk
import os

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, on_save_callback=None):
        super().__init__(parent)
        self.title("Settings")
        self.configure(bg="black")
        self.on_save_callback = on_save_callback

        self.constants = {
            "FILES_FOLDER": player_constants.FILES_FOLDER,
            # "CSV_FOLDER": player_constants.CSV_FOLDER,
            # "SCREENSHOTS_FOLDER": player_constants.SCREENSHOTS_FOLDER,
            # "REPORTS_FOLDER": player_constants.REPORTS_FOLDER,
            "LOGS_FOLDER": player_constants.LOGS_FOLDER,
            "STYLES_FOLDER": player_constants.STYLES_FOLDER,
            "SKIP_FOLDERS": ", ".join(player_constants.SKIP_FOLDERS),
            # "FOLDER_LOGS": player_constants.FOLDER_LOGS,
            # "LOG_PATH": player_constants.LOG_PATH,
            # "FAV_PATH": player_constants.FAV_PATH,
            # "WATCHED_HISTORY_LOG_PATH": player_constants.WATCHED_HISTORY_LOG_PATH,
            # "DELETE_FILES_CSV": player_constants.DELETE_FILES_CSV,
            # "FAV_FILES": player_constants.FAV_FILES,
            # "FILE_TRANSFER_LOG": player_constants.FILE_TRANSFER_LOG,
        }

        self.constants_path = os.path.join(os.path.dirname(__file__), "player_constants.py")
        self.default_content = self._read_file(self.constants_path)

        # Heading
        heading = tk.Label(self, text="Settings", bg="black", fg="red", font=("Open Sans", 28, "bold"))
        heading.pack(pady=(18, 10))

        # Frame for form
        form_frame = tk.Frame(self, bg="black")
        form_frame.pack(padx=25, pady=10, fill="both", expand=True)

        self.entries = {}
        row = 0
        label_font = ("Open Sans", 11, "bold")
        entry_font = ("Open Sans", 11)
        for key, value in self.constants.items():
            label = tk.Label(form_frame, text=key, bg="black", fg="white", font=label_font, anchor="w")
            label.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
            entry = tk.Entry(form_frame, width=48, font=entry_font, bg="#222", fg="white", insertbackground="white", relief=tk.FLAT, highlightthickness=1, highlightbackground="red")
            entry.insert(0, value)
            entry.grid(row=row, column=1, padx=(0, 5), pady=6, sticky="ew")
            self.entries[key] = entry
            row += 1

        button_frame = tk.Frame(self, bg="black")
        button_frame.pack(pady=(10, 18))

        save_btn = tk.Button(button_frame, text="Save", command=self.save_settings, bg="red", fg="white", font=("Open Sans", 12, "bold"), width=12, relief=tk.FLAT, activebackground="#aa0000", activeforeground="white", cursor="hand2")
        save_btn.grid(row=0, column=0, padx=8)
        cancel_btn = tk.Button(button_frame, text="Cancel", command=self.destroy, bg="white", fg="black", font=("Open Sans", 12, "bold"), width=12, relief=tk.FLAT, activebackground="#ddd", activeforeground="black", cursor="hand2")
        cancel_btn.grid(row=0, column=1, padx=8)
        reset_btn = tk.Button(button_frame, text="Reset to Default", command=self.reset_to_default, bg="black", fg="red", font=("Open Sans", 12, "bold"), width=16, relief=tk.FLAT, activebackground="#222", activeforeground="red", cursor="hand2", borderwidth=2, highlightbackground="red", highlightcolor="red")
        reset_btn.grid(row=0, column=2, padx=8)

        self.center_window(600, 300)
        for btn, bg, fg in [
            (save_btn, "red", "white"),
            (cancel_btn, "white", "black"),
            (reset_btn, "black", "red"),
        ]:
            btn.bind("<Enter>", lambda e, b=btn, c=bg, f=fg: b.config(bg=f, fg=c))
            btn.bind("<Leave>", lambda e, b=btn, c=bg, f=fg: b.config(bg=c, fg=f))

    def _read_file(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
        
    def center_window(self, width=600, height=500):
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def save_settings(self):
        new_values = {key: entry.get() for key, entry in self.entries.items()}
        from static_methods import ensure_folder_exists
        for key, value in new_values.items():
            if key != "SKIP_FOLDERS":
                ensure_folder_exists(value)

        self.update_constants_file(new_values)
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()

    def update_constants_file(self, new_values):
        import re
        with open(self.constants_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            for key, value in new_values.items():
                if key == "SKIP_FOLDERS":
                    pattern = r"^(SKIP_FOLDERS\s*=\s*)(.+)"
                    match = re.match(pattern, line)
                    if match:
                        items = [f'r"{item.strip()}"' for item in value.split(",") if item.strip()]
                        value_str = "[" + ", ".join(items) + "]"
                        lines[i] = f"{match.group(1)}{value_str}\n"
                else:
                    pattern = rf"^({key}\s*=\s*)(.+)"
                    match = re.match(pattern, line)
                    if match:
                        value = value.strip()
                        if not (value.startswith('r"') or value.startswith("r'")):
                            value = f'r"{value}"'
                        lines[i] = f"{match.group(1)}{value}\n"

        with open(self.constants_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def reset_to_default(self):
        with open(self.constants_path, "w", encoding="utf-8") as f:
            f.write(self.default_content)
        if self.on_save_callback:
            self.on_save_callback()
        self.destroy()