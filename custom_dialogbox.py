import tkinter as tk
from custom_messagebox import showerror, showinfo, showwarning
from static_methods import add_hover_effect, center_window

class MultiFieldDialog(tk.Toplevel):
    def __init__(self, parent, title="Input Dialog", max_height=500, header_height=40):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.configure(bg="#000000")
        self.transient(parent)
        self.grab_set()
        self.overrideredirect(False)
        self.focus_force()
        
        self.fields = []
        self.entries = {}
        self.result = None
        self.max_height = max_height

        header_frame = tk.Frame(self, bg="#000000", height=header_height)
        header_frame.pack(fill="x", pady=(0, 10))
        
        accent_line = tk.Frame(header_frame, bg="#e53935", height=3)
        accent_line.pack(fill="x")
        
        title_label = tk.Label(header_frame, text=title, font=("Segoe UI", 20, "bold"),
                               fg="white", bg="#000000")
        title_label.pack(pady=(10, 5))

        self.main_container = tk.Frame(self, bg="#000000")
        self.main_container.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.canvas = tk.Canvas(self.main_container, bg="#000000", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.main_container, orient="vertical", command=self.canvas.yview,
                                      bg="#333333", troughcolor="#000000", width=10)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#000000")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        hint_frame = tk.Frame(self, bg="#000000")
        hint_frame.pack(fill="x", padx=15, pady=(0, 10))

        hint_label = tk.Label(
            hint_frame,
            text="Ctrl + S to save   •   Esc to cancel",
            font=("Segoe UI", 9, "italic"),
            fg="#666666",
            bg="#000000"
        )
        hint_label.pack(anchor="center")
        self._keybindings()

    def _keybindings(self):
        """Set up keybindings for the dialog."""
        self.bind("<Control-S>", lambda event: self.on_ok())
        self.bind("<Control-s>", lambda event: self.on_ok())
        self.bind("<Escape>", lambda event: self.on_cancel())

    def _on_canvas_configure(self, event):
        """Resize the canvas window to match canvas width"""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
        # self.canvas.itemconfig(self.canvas_frame, width=450)

    def add_buttons(self, buttons, sticky_bottom=False, position="right"):
        """
        Add custom buttons to the dialog.

        buttons: List of tuples (button_text, callback_function, bg_color, hover_color)
        sticky_bottom: if True, buttons will be placed at the bottom of the dialog, outside scrollable frame.
        """
        if not hasattr(self, 'btn_frame'):
            if sticky_bottom:
                self.btn_frame = tk.Frame(self, bg="#000000", pady=2)
                self.btn_frame.pack(fill="x", padx=15, pady=(0, 3), side="bottom")
            else:
                self.btn_frame = tk.Frame(self.scrollable_frame, bg="#000000")
                self.btn_frame.pack(fill="x", pady=(0, 3))
        for btn_text, callback, bg_color, hover_color in buttons:
            print(btn_text)
            btn = tk.Button(
                self.btn_frame,
                text=btn_text,
                command=callback,
                bg=bg_color,
                fg="white",
                activebackground=hover_color,
                font=("Segoe UI", 11, "bold"),
                relief="flat",
                padx=20,
                pady=0,
                cursor="hand2",
                bd=0,
                highlightthickness=0
            )
            btn.pack(side=position, padx=(0, 10))
            add_hover_effect(btn, bg_color, hover_color)

    def add_info(self, text, fg="#aaaaaa", font_size=9, italic=True):
        """
        Add a small info/hint text at the bottom of the dialog.
        Example usage: add_info("Created on 2024-01-15 . ID: 12345")
        """
        style = ("Segoe UI", font_size, "italic") if italic else ("Segoe UI", font_size)
        info_label = tk.Label(
            self.scrollable_frame,
            text=text,
            font=style,
            fg=fg,
            bg="#000000",
            anchor="w",
            justify="left",
            wraplength=460
        )
        info_label.pack(fill="x", pady=(2, 5))
        return info_label

    def _add_field_ui(self, field_name, display_name, field_type=str, required=False, 
                  multiline=False, readonly=False, value=None, default_value:str=None):
        """
        Internal method to create field UI.
        default_value: string value for the field if no value is provided.
        """
        if default_value:
            value = default_value

        row_frame = tk.Frame(self.scrollable_frame, bg="#000000", pady=2)
        row_frame.pack(fill="x", pady=3)

        label_text = f"{display_name}"
        label = tk.Label(row_frame, text=label_text, fg="#cccccc", bg="#000000",
                        font=("Segoe UI", 11, "bold"), anchor="w")
        label.pack(side="top", anchor="w", pady=(0, 1))
        
        if required:
            req_label = tk.Label(row_frame, text="*", fg="#e53935", bg="#000000",
                                font=("Segoe UI", 12, "bold"))
            req_label.place(x=label.winfo_reqwidth() + 2, y=0)

        input_bg = "#f5f5f5"
        fg_color = "#333333"
        
        if readonly:
            input_bg = "#2a2a2a"
            fg_color = "#ffffff"
        elif multiline:
            input_bg = "white"
        else:
            input_bg = "white"

        if readonly:
            lbl_frame = tk.Frame(row_frame, bg="#2a2a2a", height=28)
            lbl_frame.pack(fill="x", pady=1)
            lbl_frame.pack_propagate(False)
            
            lbl = tk.Label(lbl_frame, text=str(value), font=("Segoe UI", 11, "italic"), 
                        fg=fg_color, bg=input_bg, anchor="w", padx=8)
            lbl.pack(fill="both", expand=True)
            self.entries[field_name] = lbl
        elif multiline:
            text_frame = tk.Frame(row_frame, bg="white", relief="flat", bd=1)
            text_frame.pack(fill="both", expand=True, pady=1)
            
            text_widget = tk.Text(text_frame, height=5, font=("Segoe UI", 11, "bold"), 
                                fg=fg_color, bg=input_bg, wrap="word", 
                                relief="flat", bd=0, padx=8, pady=6)
            text_widget.pack(fill="both", expand=True)
            if value:
                text_widget.insert("1.0", str(value))
            self.entries[field_name] = text_widget
        else:
            entry_frame = tk.Frame(row_frame, bg="white", relief="flat", bd=1)
            entry_frame.pack(fill="x", pady=1)
            
            entry_var = tk.StringVar(value=str(value) if value else "")
            entry = tk.Entry(entry_frame, textvariable=entry_var, fg=fg_color, bg=input_bg,
                            font=("Segoe UI", 11, "bold"), relief="flat", bd=0, 
                            insertbackground="black", selectbackground="#e53935")
            entry.pack(fill="both", expand=True, padx=8, pady=6)
            entry.focus_set()
            self.entries[field_name] = entry_var

        self.fields.append({
            "name": field_name,
            "type": field_type,
            "required": required,
            "multiline": multiline,
            "readonly": readonly
        })

        self.update_idletasks()
        new_height = min(250 + len(self.fields) * 60, self.max_height)
        center_window(self, width=520, height=new_height)


    def add_field(self, field_name, display_name, field_type=str, required=False, multiline=False, default_value=None):
        self._add_field_ui(field_name, display_name, field_type, required, multiline, readonly=False, default_value=default_value)

    def add_readonly_field(self, field_name, display_name, value, default_value=None):
        self._add_field_ui(field_name, display_name, type(value), required=False, 
                        multiline=False, readonly=True, value=value, default_value=default_value)

    def on_ok(self):
        results = {}
        try:
            for field in self.fields:
                name = field["name"]
                f_type = field["type"]
                required = field["required"]
                multiline = field["multiline"]
                readonly = field["readonly"]

                if readonly:
                    value = self.entries[name].cget("text")
                elif multiline:
                    value = self.entries[name].get("1.0", "end").strip()
                else:
                    value = self.entries[name].get().strip()

                if required and not value:
                    showerror(self.parent, "Required Field", f"'{name}' is required.")
                    return

                if value:
                    if f_type == bool:
                        value = value.lower() in ["true", "1", "yes"]
                    elif f_type != str:
                        value = f_type(value)

                results[name] = value

            self.result = results
            self.destroy()
        except ValueError as e:
            showerror(self.parent, "Invalid Input", f"Error: {e}")

    def on_cancel(self):
        self.result = None
        self.destroy()

def ask_user_info():
    dialog = MultiFieldDialog(root, "User Information")
    dialog.add_readonly_field("user_id", "User ID", 12345)
    dialog.add_field("name", "Full Name", str, required=True)
    dialog.add_field("age", "Age", int, required=True)
    dialog.add_field("email", "Email Address", str, required=True)
    dialog.add_field("bio", "Biography", str, multiline=True)
    dialog.add_field("subscribe", "Newsletter Subscription", bool)
    dialog.add_readonly_field("created", "Account Created", "2024-01-15")
    def custom_save():
        print("Custom Save action!")
        dialog.on_ok()

    def custom_cancel():
        print("Custom Cancel action!")
        dialog.on_cancel()

    dialog.add_buttons([
        ("Save", custom_save, "#e53935", "#b71c1c"),
        ("Cancel", custom_cancel, "#424242", "#616161"),
        ("Info", lambda: print("Clicked Info!"), "#2196f3", "#1976d2")
    ])

    root.wait_window(dialog)
    
    if dialog.result:
        showinfo(root, "Result", f"Collected Data:\n{dialog.result}")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Modern Dialog Demo")
    center_window(root, 500, 300)
    root.configure(bg="#000000")

    accent_frame = tk.Frame(root, bg="#e53935", height=3)
    accent_frame.pack(fill="x")

    main_frame = tk.Frame(root, bg="#000000", padx=40, pady=40)
    main_frame.pack(expand=True, fill="both")

    tk.Label(main_frame, text="Dialog System",
            font=("Segoe UI", 19, "bold"), fg="white", bg="#000000").pack(pady=(0, 10))

    tk.Label(main_frame, text="Click below to open the dialog with user fields:",
            font=("Segoe UI", 11), fg="#cccccc", bg="#000000").pack(pady=(0, 30))

    launch_btn = tk.Button(main_frame, text="Launch Dialog", command=ask_user_info,
                        bg="#e53935", fg="white", font=("Segoe UI", 12, "bold"),
                        activebackground="#b71c1c", padx=30, pady=10, 
                        relief="flat", cursor="hand2", bd=0,
                        highlightthickness=0)
    launch_btn.pack()

    footer = tk.Label(root, text="UI Example • Red/Black Theme", 
                    font=("Segoe UI", 9), fg="#666666", bg="#000000")
    footer.pack(side="bottom", pady=10)

    root.mainloop()