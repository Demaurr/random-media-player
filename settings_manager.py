import importlib
from tkinter import filedialog, messagebox
import player_constants
import default_settings
import tkinter as tk
import os
from datetime import datetime
from custom_messagebox import showinfo, showwarning, showerror, askyesno

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, on_save_callback=None):
        super().__init__(parent)
        self.title("Settings")
        self.configure(bg="black")
        self.on_save_callback = on_save_callback
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        heading = tk.Label(self, text="Settings", bg="black", fg="red", font=("Open Sans", 32, "bold"))
        heading.pack(pady=(18, 7))

        self.constants = {
            "FILES_FOLDER": player_constants.FILES_FOLDER,
            "LOGS_FOLDER": player_constants.LOGS_FOLDER,
            "STYLES_FOLDER": player_constants.STYLES_FOLDER,
            "DEMO_FOLDER": player_constants.DEMO_FOLDER,
            "FAV_PATH": player_constants.FAV_PATH,
            "FAV_FILES": player_constants.FAV_FILES,
            "SKIP_FOLDERS": player_constants.SKIP_FOLDERS
        }

        self.constants_path = os.path.join(os.path.dirname(__file__), "player_constants.py")
        self.default_content = self._read_file(self.constants_path)
        main_container = tk.Frame(self, bg="black")
        main_container.pack(fill="both", expand=True, padx=25, pady=(10, 0))
        self.canvas = tk.Canvas(main_container, bg="black", highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="black")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.bind_mousewheel()
        self.entries = {}
        row = 0
        label_font = ("Open Sans", 11, "bold")
        header_font = ("Open Sans", 14, "bold")
        entry_font = ("Open Sans", 11)
        base_dir = os.path.dirname(os.path.abspath(__file__))

        def add_category_header(text):
            nonlocal row
            header = tk.Label(self.scrollable_frame, text=text, bg="black", fg="red", font=header_font, anchor="w")
            header.grid(row=row, column=0, columnspan=3, sticky="w", padx=(0, 10), pady=(15, 8))
            row += 1

        add_category_header("Base Folders")
        folder_keys = ["FILES_FOLDER", "LOGS_FOLDER", "STYLES_FOLDER", "DEMO_FOLDER"]
        for key in folder_keys:
            if key in self.constants:
                self._add_setting_row(self.scrollable_frame, key, self.constants[key], row, label_font, entry_font, base_dir, True)
                row += 1
    
        add_category_header("Favorites")
        fav_keys = ["FAV_PATH", "FAV_FILES"]
        for key in fav_keys:
            if key in self.constants:
                self._add_setting_row(self.scrollable_frame, key, self.constants[key], row, label_font, entry_font, base_dir, True)
                row += 1

        add_category_header("Skip Folders")
        if "SKIP_FOLDERS" in self.constants:
            skip_folders_text = tk.Text(self.scrollable_frame, height=8, width=48, font=entry_font, 
                                     bg="#222", fg="white", relief=tk.FLAT, 
                                     highlightthickness=1, highlightbackground="red")
            skip_folders_text.grid(row=row, column=1, padx=(0, 5), pady=6, sticky="ew")
            skip_folders_text.insert("1.0", "\n".join(self.constants["SKIP_FOLDERS"]))
            
            label = tk.Label(self.scrollable_frame, text="SKIP_FOLDERS", bg="black", fg="white", 
                           font=label_font, anchor="w")
            label.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
            self.entries["SKIP_FOLDERS"] = skip_folders_text  # Add to entries for saving
            row += 1
            help_text = tk.Label(self.scrollable_frame, 
                               text="Enter one folder path per line. These paths will be skipped during media scanning.",
                               bg="black", fg="gray", font=("Open Sans", 9, "italic"), anchor="w", justify="left")
            help_text.grid(row=row, column=1, sticky="w", padx=(0, 10), pady=(0, 10))
            row += 1

        button_frame = tk.Frame(self, bg="black")
        button_frame.pack(side="bottom", fill="x", pady=(0, 18))
        button_container = tk.Frame(button_frame, bg="black")
        button_container.pack(anchor="center")

        save_btn = tk.Button(button_container, text="Save", command=self.save_settings, 
                            bg="red", fg="white", font=("Open Sans", 12, "bold"), 
                            width=12, relief=tk.FLAT, activebackground="#aa0000", 
                            activeforeground="white", cursor="hand2")
        save_btn.pack(side="left", padx=8)
        
        cancel_btn = tk.Button(button_container, text="Cancel", command=self.destroy, 
                              bg="white", fg="black", font=("Open Sans", 12, "bold"), 
                              width=12, relief=tk.FLAT, activebackground="#ddd", 
                              activeforeground="black", cursor="hand2")
        cancel_btn.pack(side="left", padx=8)
        
        reset_btn = tk.Button(button_container, text="Reset to Default", command=self.reset_to_default, 
                             bg="black", fg="red", font=("Open Sans", 12, "bold"), 
                             width=16, relief=tk.FLAT, activebackground="#222", 
                             activeforeground="red", cursor="hand2", 
                             borderwidth=2, highlightbackground="red", highlightcolor="red")
        reset_btn.pack(side="left", padx=8)

        self.center_window(730, 600)
        
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
        
    def center_window(self, width=700, height=600):
        num_settings = len(self.constants)
        header_height = 80  
        setting_height = 45 
        category_header_height = 40
        button_frame_height = 70
        skip_folders_extra = 100
        
        content_height = (
            header_height +                    
            (3 * category_header_height) +     
            (num_settings * setting_height) +  
            skip_folders_extra +           
            button_frame_height                
        )
        
        estimated_height = min(800, max(400, content_height))
        
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (estimated_height // 2)
        self.geometry(f"{width}x{estimated_height}+{x}+{y}")

    def bind_mousewheel(self):
        """Bind mousewheel to canvas for all platforms."""
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)
        
    def unbind_mousewheel(self):
        """Unbind mousewheel from canvas for all platforms."""
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling."""
        if not self.canvas.winfo_exists():
            return
            
        if event.num == 5 or event.delta < 0:  
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")

    def _on_close(self):
        """Clean up and close the window."""
        self.unbind_mousewheel()
        self.destroy()

    def save_settings(self):
        new_values = {}
        for key, entry in self.entries.items():
            if isinstance(entry, tk.Text):
                value = [line.strip() for line in entry.get("1.0", "end-1c").split("\n") if line.strip()]
                new_values[key] = value
            else:
                new_values[key] = entry.get().strip()

        self.update_constants_file(new_values)
        if self.on_save_callback:
            self.on_save_callback()
        self.unbind_mousewheel()
        self.destroy()

    def update_constants_file(self, new_values):
        import re
        with open(self.constants_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        base_values = {}
        for line in lines:
            for key in new_values:
                if key != "SKIP_FOLDERS":
                    pattern = rf"^{key}\s*=\s*(.+)(?:#.*)?$"
                    match = re.match(pattern, line)
                    if match and "rf\"" not in match.group(1) and "\\" not in match.group(1):
                        base_values[key] = new_values[key]

        updated_lines = []
        for line in lines:
            if not line.strip() or line.strip().startswith('#'):
                updated_lines.append(line)
                continue

            line_updated = False
            for key, new_value in new_values.items():
                pattern = rf"^({key}\s*=\s*)(.+?)(\s*#.*)?$"
                match = re.match(pattern, line)
                if match:
                    prefix = match.group(1)
                    old_value = match.group(2).strip() 
                    comment = match.group(3) or ""

                    if key == "SKIP_FOLDERS":
                        items = [f'r"{item}"' for item in sorted(new_value)]
                        value_str = "{" + ", ".join(items) + "}"
                        updated_lines.append(f"{prefix}{value_str}{comment}\n")
                    elif old_value in base_values:
                        updated_lines.append(f"{prefix}{old_value}{comment}\n")
                    elif "rf\"" in old_value or "rf'" in old_value:
                        updated_lines.append(line)
                    else:
                        updated_lines.append(f"{prefix}r\"{new_value}\"{comment}\n")
                    
                    line_updated = True
                    break
            
            if not line_updated:
                updated_lines.append(line)

        with open(self.constants_path, "w", encoding="utf-8") as f:
            f.writelines(updated_lines)

    def reset_to_default(self):
        """Reset settings to default values."""
        # confirm = messagebox.askyesno(
        #     "Confirm Reset",
        #     "Are you sure you want to reset all settings to default values?"
        # )
        confirm = askyesno(self, "Confirm Reset", "Are you sure you want to reset all settings to default values?")
        
        if confirm:
            try:
                default_values = {
                    name: value for name, value in vars(default_settings).items()
                    if not name.startswith('_')
                }
                self.update_constants_file(default_values)
                base_dir = os.path.dirname(os.path.abspath(__file__))
                from static_methods import ensure_folder_exists
                
                for key, value in default_values.items():
                    if key != "SKIP_FOLDERS" and isinstance(value, str) and "." not in value:
                        folder_path = os.path.join(base_dir, value)
                        ensure_folder_exists(folder_path)
                
                # messagebox.showinfo(
                #     "Settings Reset",
                #     "Settings have been reset to default values."
                # )
                showinfo(self, "Settings Reset", "Settings have been reset to default values.")

                if self.on_save_callback:
                    self.on_save_callback()
                
                self.unbind_mousewheel()
                self.destroy()
                
            except Exception as e:
                # messagebox.showerror(
                #     "Reset Failed",
                #     f"Failed to reset settings: {str(e)}"
                # )
                showerror(self, "Reset Failed", f"Failed to reset settings: {str(e)}")

    def _add_setting_row(self, parent, key, value, row, label_font, entry_font, base_dir, add_browse_button):
        label = tk.Label(parent, text=key, bg="black", fg="white", font=label_font, anchor="w")
        label.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
        
        entry = tk.Entry(parent, width=48, font=entry_font, bg="#222", fg="white", insertbackground="white", 
                        relief=tk.FLAT, highlightthickness=1, highlightbackground="red")
        entry.insert(0, value)
        entry.grid(row=row, column=1, padx=(0, 5), pady=6, sticky="ew")
        self.entries[key] = entry

        if add_browse_button:
            def browse_folder(entry=entry):
                folder_selected = filedialog.askdirectory(initialdir=base_dir, title="Select Folder")
                if folder_selected:
                    abs_folder = os.path.abspath(folder_selected)
                    if os.path.commonpath([abs_folder, base_dir]) == base_dir:
                        entry.delete(0, tk.END)
                        entry.insert(0, abs_folder)
                    else:
                        # messagebox.showwarning("Invalid Folder", "Please select a folder within the application's directory.")
                        showwarning(self, "Invalid Folder", "Please select a folder within the application's directory.")

            browse_btn = tk.Button(parent, text="📁", command=browse_folder, bg="#333", fg="white", 
                                font=("Open Sans", 12), relief=tk.FLAT, cursor="hand2")
            browse_btn.grid(row=row, column=2, padx=(0, 5), pady=6, sticky="ew")