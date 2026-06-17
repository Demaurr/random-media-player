import tkinter as tk
from tkinter import ttk
from _themes import THEMES
from custom_messagebox import showerror, showinfo, showwarning
from custom_textbox import EditableTextbox
from static_methods import add_hover_effect, center_window
from typing import Any, Callable
from contextlib import contextmanager



class MultiFieldDialog(tk.Toplevel):
    def __init__(self, parent, title="Input Dialog", theme="crimson_dark", max_height=500, header_height=40, window_width=520, window_height=400,
                 window_position="center", offset_x=20, offset_y=20):
        super().__init__(parent)
        self.parent = parent
        self.theme=THEMES[theme]
        self.main_bg = self.theme["bg"]
        self.title(title)
        self.configure(bg=self.theme["bg"])
        self.transient(parent)
        self.grab_set()
        self.overrideredirect(False)
        self.focus_force()
        
        self.fields = []
        self.entries = {}
        self.selections = {}
        self.ranked_selections = {}
        self.tree_selections = {}
        self.sections_meta = []
        self.result = None
        self.max_height = max_height
        self.window_width = window_width
        self.window_height = window_height
        self.wraplength = 0.9  * window_width
        self.default_input_padx = 0
        self.default_input_pady = 0

        self.window_position = window_position
        self.offset_x = offset_x
        self.offset_y = offset_y

        header_frame = tk.Frame(self, bg=self.theme["bg"], height=header_height)
        header_frame.pack(fill="x", pady=(0, 10))
        
        accent_line = tk.Frame(header_frame, bg=self.theme["accent"], height=3)
        accent_line.pack(fill="x")
        
        title_label = tk.Label(header_frame, text=title, font=("Segoe UI", 20, "bold"),
                               fg=self.theme["fg"], bg=self.theme["bg"])
        title_label.pack(pady=(10, 5))

        self.main_container = tk.Frame(self, bg=self.theme["bg"])
        self.main_container.pack(fill="both", expand=True, padx=15, pady=5)
        
        self.canvas = tk.Canvas(self.main_container, bg=self.theme["bg"], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.main_container, orient="vertical", command=self.canvas.yview,
                                      bg=self.theme["hover"], troughcolor=self.theme["bg"], width=10)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.theme["bg"])

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.current_section = None
        self.sections = []

        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Configure>", self._on_canvas_configure)

        hint_frame = tk.Frame(self, bg=self.theme["bg"])
        hint_frame.pack(fill="x", padx=15, pady=(0, 10))

        hint_label = tk.Label(
            hint_frame,
            text="Ctrl + S to save   •   Esc to cancel",
            font=("Segoe UI", 9, "italic"),
            fg="#666666",
            bg=self.theme["bg"]
        )
        hint_label.pack(anchor="center")
        self._keybindings()
        self.update_idletasks()
        # self.geometry(f"{self.window_width}x{min(self.window_height, self.max_height)}")
        self._apply_geometry(
            self.window_width,
            min(self.window_height, self.max_height)
        )
        self.after(10, self._evaluate_dependencies)

    def _sort_tree(self, tree, col):
        data = [(tree.set(k, col), k) for k in tree.get_children("")]
        try:
            data.sort(key=lambda t: float(t[0]))
        except ValueError:
            data.sort(key=lambda t: t[0].lower())

        for index, (_, k) in enumerate(data):
            tree.move(k, "", index)

    def _keybindings(self):
        """Set up keybindings for the dialog."""
        self.bind("<Control-S>", lambda event: self.on_ok())
        self.bind("<Control-s>", lambda event: self.on_ok())
        self.bind("<Escape>", lambda event: self.on_cancel())

    def _on_canvas_configure(self, event):
        """Resize the canvas window to match canvas width"""
        self.canvas.itemconfig(self.canvas_frame, width=event.width)
        # self.canvas.itemconfig(self.canvas_frame, width=450)
        # self.canvas.itemconfig(self.canvas_frame, width=self.window_width)

    def _get_field_value(self, name):
        entry = self.entries.get(name)

        if entry is None:
            return None

        if isinstance(entry, tk.StringVar):
            return entry.get().strip()

        if isinstance(entry, tuple):  # dropdown
            var, reverse = entry
            return reverse.get(var.get())

        if isinstance(entry, tk.Text):
            return entry.get("1.0", "end").strip()

        if hasattr(entry, "cget"):  # readonly label
            return entry.cget("text")

        return None


    def _evaluate_dependencies(self):
        # === Handle fields ===
        for field in self.fields:
            dep = field.get("depends_on")
            if not dep:
                continue

            target_name, condition = dep
            row = self.entries.get(f"{field['name']}__row")
            if not row:
                continue

            value = self._get_field_value(target_name)
            try:
                visible = bool(condition(value))
            except Exception:
                visible = False

            if visible and not field["visible"]:
                row.pack(fill="x", pady=3)
                field["visible"] = True
            elif not visible and field["visible"]:
                row.pack_forget()
                field["visible"] = False

        # === Handle sections ===
        for section in getattr(self, "sections_meta", []):
            dep = section.get("depends_on")
            container = section.get("container")
            if not dep or not container:
                continue

            target_name, condition = dep
            value = self._get_field_value(target_name)
            try:
                visible = bool(condition(value))
            except Exception:
                visible = False

            if visible and not section["visible"]:
                container.pack(fill="x", pady=(10, 14))
                section["visible"] = True
            elif not visible and section["visible"]:
                container.pack_forget()
                section["visible"] = False

        self.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _apply_geometry(self, width, height):
        self.update_idletasks()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        parent = self.parent

        # default fallback
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2

        if self.window_position == "center":
            pass  # keep default

        elif self.window_position == "left":
            x = self.offset_x
            y = (screen_h - height) // 2

        elif self.window_position == "right":
            x = screen_w - width - self.offset_x
            y = (screen_h - height) // 2

        elif self.window_position == "top_left":
            x = self.offset_x
            y = self.offset_y

        elif self.window_position == "top_right":
            x = screen_w - width - self.offset_x
            y = self.offset_y

        elif self.window_position == "relative" and parent is not None:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()

            x = px + (pw - width) // 2
            y = py + (ph - height) // 2

        elif self.window_position == "parent_right" and parent is not None:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()

            x = px + pw - width - self.offset_x
            y = py + (parent.winfo_height() - height) // 2

        elif self.window_position == "parent_left" and parent is not None:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()

            x = px + self.offset_x
            y = py + (parent.winfo_height() - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")



    def add_buttons(self, buttons, sticky_bottom=False, position="right"):
        """
        Add custom buttons to the dialog.

        buttons: List of tuples (button_text, callback_function, bg_color, hover_color)
        sticky_bottom: if True, buttons will be placed at the bottom of the dialog, outside scrollable frame.
        """
        if not hasattr(self, 'btn_frame'):
            if sticky_bottom:
                self.btn_frame = tk.Frame(self, bg=self.theme["bg"], pady=2)
                self.btn_frame.pack(fill="x", padx=15, pady=(0, 3), side="bottom")
            else:
                parent = self._get_active_container()
                self.btn_frame = tk.Frame(parent, bg=self.theme["bg"])
                self.btn_frame.pack(fill="x", pady=(0, 3))
        for btn_text, callback, bg_color, hover_color in buttons:
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

    def add_info(self, text, fg="#aaaaaa", font_size=9, italic=True, align="left"):
        """
        Add a small info/hint text at the bottom of the dialog.
        Example usage: add_info("Created on 2024-01-15 . ID: 12345")
        """
        align_map = {
            "left":   {"anchor": "w", "justify": "left"},
            "center": {"anchor": "center", "justify": "center"},
            "right":  {"anchor": "e", "justify": "right"},
        }

        if align not in align_map:
            raise ValueError("align must be 'left', 'center', or 'right'")
        
        cfg = align_map[align]

        style = ("Segoe UI", font_size, "italic") if italic else ("Segoe UI", font_size)
        parent = self._get_active_container()
        info_label = tk.Label(
            parent,
            text=text,
            font=style,
            fg=fg,
            bg=self.theme["bg"],
            anchor=cfg["anchor"],
            justify=cfg["justify"],
            wraplength=self.wraplength
        )
        info_label.pack(fill="x", pady=(2, 5))
        return info_label

    def _get_active_container(self):
        """
        Returns the frame where new widgets should be added.
        Defaults to the main scrollable frame if no section is active.
        """
        return self.current_section or self.scrollable_frame


    def _add_field_ui(
        self,
        field_name,
        display_name,
        field_type=str,
        required=False,
        multiline=False,
        readonly=False,
        value=None,
        default_value: str = None,
        layout="stacked",
        input_bg=None,
        input_fg=None,
        field_font_size=11,
        input_font_size=11,
        input_padx=None,
        input_pady=None,
        placeholder=None,
        hidden=None,
        validators: list | Callable=None,
        depends_on: tuple | None = None,
    ):

        """
        Internal method to create field UI.
        layout: "stacked" for label above input, "inline" for label left, input right
        """
        input_bg = input_bg or self.theme["input_bg"]
        input_fg = input_fg or self.theme["input_fg"]


        if default_value is not None:
            value = default_value
            placeholder = None
        
        if validators is None:
            validators = []
        elif callable(validators):
            validators = [validators]
        
        parent = self._get_active_container()

        row_frame = tk.Frame(parent, bg=self.main_bg, pady=2)
        row_frame.pack(fill="x", pady=3)

        label_text = f"{display_name}"
        label = tk.Label(
            row_frame,
            text=label_text,
            fg=self.theme["muted"],
            bg=self.main_bg,
            font=("Segoe UI", field_font_size, "bold"),
            anchor="w",
        )
        padx = input_padx if input_padx is not None else self.default_input_padx
        pady = input_pady if input_pady is not None else self.default_input_pady


        if layout == "stacked":
            label.pack(side="top", anchor="w", pady=(0, 1))
        elif layout == "inline":
            label.pack(side="left", padx=(0, 10))

        if required:
            field_font_size+=1
            req_label = tk.Label(
                row_frame,
                text="*",
                fg=self.theme["accent"],
                bg=self.main_bg,
                font=("Segoe UI", field_font_size, "bold"),
            )
            if layout == "stacked":
                req_label.place(x=label.winfo_reqwidth() + 2, y=0)
            elif layout == "inline":
                req_label.pack(side="left")

        if readonly:
            input_bg = self.theme["readonly_bg"]
            input_fg = self.theme["readonly_fg"]

        if readonly:
            lbl_frame = tk.Frame(row_frame, bg=input_bg, height=28)
            if layout == "stacked":
                lbl_frame.pack(fill="x", pady=1)
            elif layout == "inline":
                lbl_frame.pack(side="left", fill="x", expand=True, pady=1)
            lbl_frame.pack_propagate(True)

            lbl = tk.Label(
                lbl_frame,
                text=str(value),
                font=("Segoe UI", input_font_size, "italic"),
                fg=input_fg,
                bg=input_bg,
                anchor="w",
                justify="left",
                wraplength=self.wraplength,
                padx=8,
                pady=2,
            )
            lbl.pack(fill="both", expand=True)
            self.entries[field_name] = lbl

        elif multiline:
            text_frame = tk.Frame(row_frame, bg="white", relief="flat", bd=1)
            if layout == "stacked":
                text_frame.pack(fill="both", expand=True, pady=1)
            elif layout == "inline":
                text_frame.pack(side="left", fill="both", expand=True, pady=1)

            text_widget = tk.Text(
                text_frame,
                height=5,
                font=("Segoe UI", 11, "bold"),
                fg=input_fg,
                bg=input_bg,
                wrap="word",
                relief="flat",
                bd=0,
                padx=8,
                pady=6,
            )
            text_widget.pack(fill="both", expand=True, padx=padx, pady=pady)
            text_widget.bind("<KeyRelease>", lambda e: self._evaluate_dependencies())

            if value:
                text_widget.insert("1.0", str(value))
            self.entries[field_name] = text_widget

        else:
            entry_frame = tk.Frame(row_frame, bg="white", relief="flat", bd=1)
            if layout == "stacked":
                entry_frame.pack(fill="x", pady=1)
            elif layout == "inline":
                entry_frame.pack(side="left", fill="x", expand=True, pady=1)

            entry_var = tk.StringVar(value=str(value) if value else "")
            entry = tk.Entry(
                entry_frame,
                textvariable=entry_var,
                fg=input_fg,
                bg=input_bg,
                font=("Segoe UI", 11, "bold"),
                relief="flat",
                bd=0,
                insertbackground="black",
                selectbackground=self.theme["accent"],
                show="*" if hidden else ""
            )
            entry.pack(fill="both", expand=True, padx=padx, pady=pady)
            entry_var.trace_add("write", lambda *_: self._evaluate_dependencies())
            entry.focus_set()
            self.entries[field_name] = entry_var
            if placeholder:
                def on_focus_in(event, ev=entry, pv=placeholder):
                    if ev.get() == pv:
                        ev.delete(0, "end")
                        ev.config(fg=input_fg)
                def on_focus_out(event, ev=entry, pv=placeholder):
                    if not ev.get():
                        ev.insert(0, pv)
                        ev.config(fg="#888888")
                
                entry.insert(0, placeholder)
                entry.config(fg="#888888")
                entry.bind("<FocusIn>", on_focus_in)
                entry.bind("<FocusOut>", on_focus_out)

        self.fields.append(
            {
                "name": field_name,
                "type": field_type,
                "required": required,
                "multiline": multiline,
                "readonly": readonly,
                "layout": layout,
                "validators": validators,
                "depends_on": depends_on,
                "visible": True,
            }
        )
        self.entries[f"{field_name}__row"] = row_frame


        self.update_idletasks()
        new_height = min(self.window_height + len(self.fields) * 60, self.max_height)
        # center_window(self, width=self.window_width, height=new_height)
        self._apply_geometry(self.window_width, new_height)

    def validate_fields(self):
        """
        Validate all fields, dropdowns, and selections.
        Returns True if all validations pass, otherwise shows error and returns False.
        """
        

        for field in self.fields:
            name = field.get("name", "")
            required = field.get("required", False)
            validators = field.get("validators", [])
            multiline = field.get("multiline", False)
            readonly = field.get("readonly", False)
            is_dropdown = field.get("dropdown", False)

            # for field in self.fields:
            if not field.get("visible", True):
                continue 

            if field.get("smart_text"):
                value = self.entries[name].get()

            elif readonly:
                value = self.entries[name].cget("text")
            elif multiline:
                value = self.entries[name].get("1.0", "end").strip()
            elif is_dropdown:
                var, reverse_map = self.entries[name]
                label = var.get().strip()
                value = reverse_map.get(label)
            else:
                value = self.entries[name].get().strip()

            if required and (value is None or value == "" or (isinstance(value, list) and not value)):
                showerror("Validation Error", f"Field '{name}' is required.")
                return False

            for validator in validators:
                try:
                    result = validator(value)
                    if isinstance(result, tuple):
                        valid, msg = result
                    else:
                        valid, msg = result, None
                    if not valid:
                        showerror("Validation Error", msg or f"Field '{name}' is invalid.")
                        return False
                except Exception as e:
                    showerror("Validation Error", str(e))
                    return False

        for group_name, meta in self.selections.items():
            vars_map = meta["_vars"]
            selected = {k: v.get() for k, v in vars_map.items()}
            count = sum(selected.values())

            if meta["_required"] and count < meta["_min"]:
                showerror(
                    "Selection Required",
                    f"Please select at least {meta['_min']} option(s) in '{meta['_title']}'."
                )
                return False

        return True



    def add_field(self, field_name, display_name, field_type=str, required=False, multiline=False, default_value=None,
                   layout="stacked", field_font_size=11, input_padx=None, input_pady=None, placeholder=None, hidden=None, validators=None,
                   depends_on=None):
        self._add_field_ui(field_name, display_name, field_type, required, multiline, readonly=False, default_value=default_value, 
                           layout=layout, field_font_size=field_font_size, input_padx=input_padx, input_pady=input_pady, placeholder=placeholder, hidden=hidden,
                           validators=validators, depends_on=depends_on)

    def add_readonly_field(self, field_name, display_name, value, default_value=None, 
                           layout="stacked", field_font_size=11, input_padx=None, input_pady=None):
        self._add_field_ui(field_name, display_name, type(value), required=False, multiline=False, readonly=True, value=value, 
                           default_value=default_value, layout=layout, field_font_size=field_font_size, input_padx=input_padx, input_pady=input_pady)


    def _toggle_pill(self, frame, var, active_bg, inactive_bg, label):
        def toggle(_=None):
            var.set(not var.get())
            if var.get():
                frame.configure(bg=active_bg)
                label.configure(bg=active_bg, fg="white")
            else:
                frame.configure(bg=inactive_bg)
                label.configure(bg=inactive_bg, fg=self.theme["muted"])

        frame.bind("<Button-1>", toggle)
        label.bind("<Button-1>", toggle)

    def add_selections(
        self,
        name: str,
        title: str,
        options,
        default=None,
        active_bg=None,
        inactive_bg="#1e1e1e",
        required=False,
        min_selected=1,
        columns=3 
    ):
        active_bg = active_bg or self.theme["accent"]
        default = set(default or [])
        self.selections[name] = {
            "_vars": {},
            "_required": required,
            "_min": max(1, min_selected),
            "_title": title
        }
        parent = self._get_active_container()

        container = tk.Frame(parent, bg=self.main_bg, pady=6)
        container.pack(fill="x", pady=(6, 10))

        title_lbl = tk.Label(
            container,
            text=title,
            fg=self.theme["muted"],
            bg=self.theme["bg"],
            font=("Segoe UI", 11, "bold"),
            anchor="w"
        )
        title_lbl.pack(anchor="w", pady=(0, 6))

        pills_frame = tk.Frame(container, bg=self.theme["bg"])
        pills_frame.pack(fill="x")

        col = 0
        row = 0

        for key, text in options:
            var = tk.BooleanVar(value=key in default)
            self.selections[name]["_vars"][key] = var

            pill = tk.Frame(
                pills_frame,
                bg=active_bg if var.get() else inactive_bg,
                padx=10,
                pady=6,
                highlightthickness=1,
                highlightbackground="#333333",
                bd=0
            )

            lbl = tk.Label(
                pill,
                text=text,
                font=("Segoe UI", 10, "bold"),
                fg="white" if var.get() else self.theme["muted"],
                bg=pill["bg"],
                cursor="hand2"
            )
            lbl.pack()

            pill.grid(row=row, column=col, padx=2, pady=2, sticky="w")

            def on_enter(event, pill=pill, lbl=lbl):
                pill.configure(bg="gray")
                lbl.configure(bg="gray", fg="white")

            def on_leave(event, pill=pill, lbl=lbl, var=var):
                pill.configure(bg=active_bg if var.get() else inactive_bg)
                lbl.configure(fg="white" if var.get() else self.theme["muted"], bg=pill["bg"])

            pill.bind("<Enter>", on_enter)
            pill.bind("<Leave>", on_leave)
            lbl.bind("<Enter>", on_enter)
            lbl.bind("<Leave>", on_leave)

            self._toggle_pill(pill, var, active_bg, inactive_bg, lbl)

            col += 1
            if col >= columns:
                col = 0
                row += 1

        self.update_idletasks()
        new_height = min(
            self.window_height + (len(self.fields) * 60) + (len(options) * 28),
            self.max_height
        )
        # center_window(self, width=self.window_width, height=new_height)
        self._apply_geometry(self.window_width, new_height)

    def add_ranked_selections(
        self,
        name: str,
        title: str,
        options,
        *,
        active_bg=None,
        inactive_bg=None,
    ):
        active_bg = active_bg or self.theme["accent"]
        inactive_bg = inactive_bg or self.theme["section_bg"]

        parent = self._get_active_container()

        container = tk.Frame(parent, bg=self.main_bg, pady=6)
        container.pack(fill="x", pady=(8, 12))

        title_lbl = tk.Label(
            container,
            text=title,
            fg=self.theme["muted"],
            bg=self.main_bg,
            font=("Segoe UI", 11, "bold"),
            anchor="w"
        )
        title_lbl.pack(anchor="w", pady=(0, 6))

        list_frame = tk.Frame(container, bg=self.main_bg)
        list_frame.pack(fill="x")

        items = []
        drag_item = {"item": None}

        def refresh_ranks():
            for i, it in enumerate(items, start=1):
                it["rank"].config(text=str(i))

        def start_drag(item):
            drag_item["item"] = item
            item["frame"].configure(bg=self.theme["hover"])

        def stop_drag():
            if drag_item["item"]:
                drag_item["item"]["frame"].configure(bg=inactive_bg)
            drag_item["item"] = None

        def on_motion(event):
            if not drag_item["item"]:
                return

            y = event.y_root

            for idx, it in enumerate(items):
                frame = it["frame"]
                top = frame.winfo_rooty()
                mid = top + frame.winfo_height() // 2

                if y < mid:
                    cur = items.index(drag_item["item"])
                    if cur != idx:
                        items.pop(cur)
                        items.insert(idx, drag_item["item"])
                        _repack()
                    break
            else:
                # dragged below all items
                cur = items.index(drag_item["item"])
                if cur != len(items) - 1:
                    items.pop(cur)
                    items.append(drag_item["item"])
                    _repack()

        def _repack():
            for it in items:
                it["frame"].pack_forget()
            for it in items:
                it["frame"].pack(fill="x", pady=2)
            refresh_ranks()

        for key, label in options:
            row = tk.Frame(
                list_frame,
                bg=inactive_bg,
                padx=10,
                pady=6,
                highlightthickness=1,
                highlightbackground=self.theme["border"],
                cursor="hand2"
            )
            row.pack(fill="x", pady=2)

            rank_lbl = tk.Label(
                row,
                width=3,
                fg="white",
                bg=inactive_bg,
                font=("Segoe UI", 10, "bold")
            )
            rank_lbl.pack(side="left")

            text_lbl = tk.Label(
                row,
                text=label,
                fg="white",
                bg=inactive_bg,
                font=("Segoe UI", 10, "bold"),
                anchor="w"
            )
            text_lbl.pack(side="left", fill="x", expand=True)

            item = {
                "key": key,
                "frame": row,
                "rank": rank_lbl
            }
            items.append(item)

            for w in (row, rank_lbl, text_lbl):
                w.bind("<Button-1>", lambda e, it=item: start_drag(it))
                w.bind("<B1-Motion>", on_motion)
                w.bind("<ButtonRelease-1>", lambda e: stop_drag())

        refresh_ranks()

        self.ranked_selections[name] = {
            "_type": "ranked",
            "_items": items,
            "_title": title
        }

        self.update_idletasks()
        # center_window(
        #     self,
        #     width=self.window_width,
        #     height=min(self.max_height, self.window_height + len(options) * 34)
        # )
        self._apply_geometry(self.window_width, height = min(self.max_height, self.window_height + len(options) * 34))



    def add_dropdown_field(
        self,
        field_name,
        display_name,
        options,
        *,
        required=False,
        default=None,
        layout="stacked",
        field_font_size=11,
        input_font_size=11,
        readonly=True,
    ):
        """
        Add a dropdown (combobox) field.

        options: list of values OR list of (value, label)
        default: default selected value
        """

        values = []
        labels = {}
        for opt in options:
            if isinstance(opt, tuple):
                values.append(opt[0])
                labels[opt[0]] = opt[1]
            else:
                values.append(opt)
                labels[opt] = opt

        parent = self._get_active_container()

        row_frame = tk.Frame(parent, bg=self.main_bg, pady=2)
        row_frame.pack(fill="x", pady=3)

        label = tk.Label(
            row_frame,
            text=display_name,
            fg=self.theme["muted"],
            bg=self.main_bg,
            font=("Segoe UI", field_font_size, "bold"),
            anchor="w"
        )

        if layout == "stacked":
            label.pack(anchor="w", pady=(0, 1))
        else:
            label.pack(side="left", padx=(0, 10))

        if required:
            tk.Label(
                row_frame,
                text="*",
                fg=self.theme["accent"],
                bg=self.main_bg,
                font=("Segoe UI", field_font_size + 1, "bold")
            ).pack(side="left")

        var = tk.StringVar(value=labels.get(default, "") if default else "")
        var.trace_add("write", lambda *_: self._evaluate_dependencies())

        combo_frame = tk.Frame(row_frame, bg="gray", relief="flat", bd=0)
        if layout == "stacked":
            combo_frame.pack(fill="x", pady=1)
        else:
            combo_frame.pack(side="left", fill="x", expand=True, pady=1)

        combo = ttk.Combobox(
            combo_frame,
            textvariable=var,
            values=[labels[v] for v in values],
            state="readonly" if readonly else "normal",
            font=("Segoe UI", input_font_size, "bold"),
            background="gray"
        )
        combo.pack(fill="x", padx=8, pady=6)

        reverse_map = {labels[v]: v for v in values}

        self.entries[field_name] = (var, reverse_map)

        self.fields.append({
            "name": field_name,
            "type": str,
            "required": required,
            "dropdown": True
        })

        self.update_idletasks()
        new_height = min(self.window_height + len(self.fields) * 60, self.max_height)
        # center_window(self, width=self.window_width, height=new_height)
        self._apply_geometry(self.window_width, height = new_height)


    def add_section(
        self,
        title: str,
        description: str | None = None,
        *,
        accent=None,
        bg=None,
        padding=10,
        collapsible=False,
        collapsed=False,
        depends_on: tuple | None = None,
    ):
        """
        Create a visual section to group related fields.

        Example:
            dialog.add_section("User Details", collapsible=True)
        """

        parent = self._get_active_container()
        bg = bg or self.theme["section_bg"]
        accent = accent or self.theme["accent"]

        container = tk.Frame(
            parent,
            bg=bg,
            padx=padding,
            pady=padding,
            highlightthickness=1,
            highlightbackground=self.theme["border"],
        )
        container.pack(fill="x", pady=(10, 14))

        header = tk.Frame(container, bg=bg)
        header.pack(fill="x", pady=(0, 6))

        title_lbl = tk.Label(
            header,
            text=title,
            font=("Segoe UI", 13, "bold"),
            fg="white",
            bg=bg,
            anchor="w",
        )
        title_lbl.pack(side="left")

        accent_line = tk.Frame(header, bg=accent, height=2)
        accent_line.pack(fill="x", expand=True, padx=(10, 6), pady=6)

        is_collapsed = tk.BooleanVar(value=collapsed)

        toggle_lbl = None
        if collapsible:
            toggle_lbl = tk.Label(
                header,
                text=">" if collapsed else "V",
                font=("Segoe UI", 12, "bold"),
                fg=accent,
                bg=bg,
                cursor="hand2",
            )
            toggle_lbl.pack(side="right")

        if description:
            desc_lbl = tk.Label(
                container,
                text=description,
                font=("Segoe UI", 9, "italic"),
                fg="#aaaaaa",
                bg=bg,
                anchor="w",
                justify="left",
                wraplength=self.wraplength,
            )
            desc_lbl.pack(fill="x", pady=(0, 8))
        else:
            desc_lbl = None

        content = tk.Frame(container, bg=bg)
        content.pack(fill="x")

        def toggle_section(_=None):
            if is_collapsed.get():
                content.pack(fill="x")
                if desc_lbl:
                    desc_lbl.pack(fill="x", pady=(0, 8))
                is_collapsed.set(False)
                if toggle_lbl:
                    toggle_lbl.config(text="V", font=("Segoe UI", 12, "bold"), fg=accent)
            else:
                content.pack_forget()
                if desc_lbl:
                    desc_lbl.pack_forget()
                is_collapsed.set(True)
                if toggle_lbl:
                    toggle_lbl.config(text=">", font=("Segoe UI", 12, "bold"), fg=accent)

            self.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        if collapsible:
            toggle_lbl.bind("<Button-1>", toggle_section)
            title_lbl.bind("<Button-1>", toggle_section)
            header.bind("<Button-1>", toggle_section)

            if collapsed:
                content.pack_forget()
                if desc_lbl:
                    desc_lbl.pack_forget()

        self.current_section = content
        self.sections.append(container)

        self.sections_meta.append({
            "container": container,
            "depends_on": depends_on,
            "visible": True 
        })

        return content

    def add_inline_buttons(
        self,
        field_name,
        buttons,
        *,
        position="right",
        spacing=6
    ):
        """
        Add buttons inline with an existing field.

        buttons: List of tuples (text, callback, bg, hover_bg)
        position: 'right' or 'left'
        """

        row = self.entries.get(f"{field_name}__row")
        if not row:
            raise ValueError(f"No field named '{field_name}' found")

        btn_frame = tk.Frame(row, bg=self.main_bg)
        btn_frame.pack(side=position, padx=(spacing, 0), pady=1)

        for text, callback, bg, hover in buttons:
            btn = tk.Button(
                btn_frame,
                text=text,
                command=callback,
                bg=bg,
                fg="white",
                activebackground=hover,
                font=("Segoe UI", 10, "bold"),
                relief="flat",
                padx=12,
                pady=4,
                cursor="hand2",
                bd=0,
                highlightthickness=0
            )
            btn.pack(side="left", padx=2)
            add_hover_effect(btn, bg, hover)

    def add_table(
        self,
        name: str,
        title: str,
        *,
        columns,
        rows=None,
        selectable=True,
        multi_select=False,
        sortable=True,
        height=6,
        rows_sorter: Callable = None,
        tags_styles=None,
        tags_setter: Callable = None,
        row_action: dict | None = None,
        hidden_columns: list[str] = None,  # <-- new
    ):

        parent = self._get_active_container()
        rows = rows or []
        t = self.theme
        
        # Default tags styles if not provided
        if tags_styles is None:
            tags_styles = {
                "evenrow": {"background": t["input_bg"]},
                "oddrow": {"background": t["readonly_bg"], "foreground": t["readonly_fg"]},
                "hover": {"background": t["accent_hover"]}
            }
        
        # Default tags setting method if not provided
        if tags_setter is None:
            tags_setter = lambda idx, row: ("evenrow" if idx % 2 == 0 else "oddrow",)

        container = tk.Frame(parent, bg=t["bg"], pady=6)
        container.pack(fill="x", pady=(8, 12))

        title_lbl = tk.Label(
            container,
            text=title,
            fg=t["muted"],
            bg=t["bg"],
            font=("Segoe UI", 11, "bold"),
            anchor="w"
        )
        title_lbl.pack(anchor="w", pady=(0, 6))

        style = ttk.Style()
        # style.theme_use("default")
        style.configure(
            "Dialog.Treeview",
            background=t["input_bg"],
            foreground=t["input_fg"],
            fieldbackground=t["input_bg"],
            rowheight=28,
            font=("Segoe UI", 10),
            borderwidth=0,
        )
        style.configure(
            "Dialog.Treeview.Heading",
            background=t["section_bg"],
            foreground=t["fg"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        style.map(
            "Dialog.Treeview",
            background=[("selected", t["accent"])],
            foreground=[("selected", t["input_fg"])],
        )

        table_frame = tk.Frame(container, bg=t["border"], highlightthickness=1, highlightbackground=t["border"])
        table_frame.pack(fill="x", padx=2, pady=2)

        tree = ttk.Treeview(
            table_frame,
            columns=[c[0] for c in columns],
            show="headings",
            height=height,
            selectmode="extended" if multi_select else "browse",
            style="Dialog.Treeview"
        )

        vsb = tk.Scrollbar(
            table_frame,
            orient="vertical",
            command=tree.yview,
            bg=t["bg"],
            troughcolor=t["bg"],
            width=10
        )
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        for key, label, width in columns:
            if sortable:
                if rows_sorter:
                    tree.heading(key, text=label, command=lambda k=key: rows_sorter(tree, k))
                else:
                    tree.heading(key, text=label, command=lambda k=key: self._sort_tree(tree, k))
            else:
                tree.heading(key, text=label)
            tree.column(key, width=width, anchor="w", stretch=True)

        item_map = {}
        for idx, row in enumerate(rows):
            hidden_columns = hidden_columns or []

            tags = tags_setter(idx, row)


            # Prepare values only for visible columns
            visible_values = [row.get(col[0], "") for col in columns]

            # Save full row (including hidden columns) in item_map
            iid = tree.insert("", "end", values=visible_values, tags=tags)
            item_map[iid] = row 
            
            
            # iid = tree.insert(
            #     "",
            #     "end",
            #     values=values,
            #     tags=tags
            # )
            # item_map[iid] = row

        for tag_name, tag_styles in tags_styles.items():
            tree.tag_configure(tag_name, **tag_styles)

        if row_action:
            for event, callback in row_action.items():
                def handler(e, cb=callback):
                    row_id = tree.focus()  # currently selected row
                    if not row_id:
                        return
                    row_data = item_map.get(row_id, {})
                    cb(row_data, tree, row_id)
                tree.bind(event, handler)

        def on_motion(event):
            row_id = tree.identify_row(event.y)
            
            for iid in tree.get_children():
                idx = tree.index(iid)
                row_data = item_map.get(iid, {})
                tags = tags_setter(idx, row_data)
                tree.item(iid, tags=tags)
            
            if row_id:
                current_tags = list(tree.item(row_id, "tags"))
                hover_tag = next((tag for tag in tags_styles.keys() if "hover" in tag), "hover")
                tree.item(row_id, tags=(hover_tag,))

        tree.bind("<Motion>", on_motion)

        self.tree_selections[name] = {
            "_type": "table",
            "_tree": tree,
            "_rows": item_map,
            "_selectable": selectable,
            "_title": title,
            "_tags_styles": tags_styles,  # Store for future reference
            "_tags_setting_method": tags_setter  # Store for future reference
        }

        self.update_idletasks()
        # center_window(
        #     self,
        #     width=self.window_width,
        #     height=min(self.max_height, self.window_height + height * 30)
        # )
        self._apply_geometry(self.window_width, height = min(self.max_height, self.window_height + height * 30))

    def add_smart_text(
        self,
        field_name,
        display_name,
        *,
        default="",
        required=False,

        display_font=("Segoe UI", 11),
        display_fg=None,
        display_bg=None,

        edit_font=("Segoe UI", 11),
        edit_fg=None,
        edit_bg=None,

        multiline=True,
        height=4,

        validator=None,
        on_save=None,
    ):
        parent = self._get_active_container()

        row = tk.Frame(parent, bg=self.main_bg)
        row.pack(fill="x", pady=3)

        label = tk.Label(
            row,
            text=display_name,
            fg=self.theme["muted"],
            bg=self.main_bg,
            font=("Segoe UI", 11, "bold"),
            anchor="w"
        )
        label.pack(anchor="w")

        widget = EditableTextbox(
            row,
            text=default,

            display_font=display_font,
            display_fg=display_fg or self.theme["fg"],
            display_bg=display_bg or self.theme["bg"],

            edit_font=edit_font,
            edit_fg=edit_fg or self.theme["input_fg"],
            edit_bg=edit_bg or self.theme["input_bg"],

            multiline=multiline,
            height=height,

            validator=validator,
            on_save=on_save
        )

        widget.pack(fill="x", expand=True)

        self.entries[field_name] = widget

        self.fields.append({
            "name": field_name,
            "type": str,
            "required": required,
            "smart_text": True
        })
        self.entries[f"{field_name}__row"] = row

    def end_section(self):
        """Stop routing widgets into the current section."""
        self.current_section = None        

    def on_ok(self):
        if not self.validate_fields():
            return

        results = {}
        try:
            for field in self.fields:
                name = field.get("name", "")
                f_type = field["type"]
                required = field.get("required", False)
                multiline = field.get("multiline", False)
                readonly = field.get("readonly", False)

                if field.get("smart_text"):
                    value = self.entries[name].get()

                elif readonly:
                    value = self.entries[name].cget("text")

                elif multiline:
                    value = self.entries[name].get("1.0", "end").strip()
                elif field.get("dropdown"):
                    var, reverse_map = self.entries[name]
                    label = var.get().strip()
                    value = reverse_map.get(label)
                else:
                    value = self.entries[name].get().strip()

                if value:
                    if f_type == bool:
                        value = value.lower() in ["true", "1", "yes"]
                    elif f_type != str:
                        value = f_type(value)

                results[name] = value

            for group_name, meta in self.selections.items():
                vars_map = meta["_vars"]
                selected = {k: v.get() for k, v in vars_map.items()}
                count = sum(selected.values())

                if meta["_required"] and count < meta["_min"]:
                    showerror(
                        "Selection Required",
                        f"Please select at least {meta['_min']} option(s) in '{meta['_title']}'."
                    )
                    return

                results[group_name] = selected

            for group_name, meta in self.ranked_selections.items():
                if meta.get("_type") == "ranked":
                    ordered = [item["key"] for item in meta["_items"]]
                    results[group_name] = ordered

            for group_name, meta in self.tree_selections.items():
                if meta.get("_type") == "table":
                    tree = meta["_tree"]
                    row_map = meta["_rows"]

                    if meta["_selectable"]:
                        selected = tree.selection()
                        results[group_name] = [row_map[iid] for iid in selected]
                    else:
                        results[group_name] = list(row_map.values())

            self.result = results
            self.destroy()

        except ValueError as e:
            showerror("Invalid Input", f"Error: {e}")
        except Exception as e:
            showerror("Error", f"An unexpected error occurred:\n{e}")


    def on_cancel(self):
        self.result = None
        self.destroy()

    def _cleanup(self):
        """Minimal cleanup to prevent common memory leaks."""
        if hasattr(self, '_after_ids'):
            for after_id in self._after_ids:
                self.after_cancel(after_id)
        
        self.entries.clear()
        self.fields.clear()
        self.selections.clear()
        self.ranked_selections.clear()
        self.tree_selections.clear()
        self.sections.clear()
        self.sections_meta.clear()
        
        self.parent = None
        
        self.canvas = None
        self.scrollbar = None
        self.scrollable_frame = None
        self.main_container = None

    @contextmanager
    def section(self, title, **kwargs):
        """Context manager for sections."""
        self.add_section(title, **kwargs)
        try:
            yield
        finally:
            self.end_section()

    def use_template(self, template_name, **kwargs):
        """
        Apply a predefined template to the dialog.
        
        Usage:
            dialog.use_template("user_management", user_data=user, mode="edit")
            dialog.use_template("project_task", mode="task")
        """
        templates = {
            # "user_management": user_management_template,
            # "project_task": project_task_template
        }
        
        if template_name not in templates:
            raise ValueError(f"Unknown template: {template_name}. "
                           f"Available: {list(templates.keys())}")
        
        # Clear any existing content
        self.fields.clear()
        self.entries.clear()
        
        # Apply the template
        template_func = templates[template_name]
        template_func(self, **kwargs)
        
        return self
    
def ask_user_info():
    dialog = MultiFieldDialog(root, "User Information", window_width=600, window_height=100)
    dialog.add_readonly_field("user_id", "User ID", 12345)
    dialog.add_field("name", "Full Name", str, required=True)
    dialog.add_field("age", "Age", int, required=True)
    dialog.add_field("email", "Email Address", str, required=True)
    dialog.add_field("bio", "Biography", str, multiline=True)
    dialog.add_field("subscribe", "Newsletter Subscription", bool)
    dialog.add_readonly_field("created", "Account Created", "2024-01-15")
    dialog.add_field("new_email", "Email", str, layout="inline")
    dialog.add_readonly_field("new_user_id", "User ID", 12345, layout="inline", field_font_size=20)
    def custom_save():
        print("Custom Save action!")
        dialog.on_ok()

    def custom_cancel():
        print("Custom Cancel action!")
        dialog.on_cancel()

    dialog.add_buttons([
        ("Save", custom_save, "#e53935", "#b71c1c"),
        ("Cancel", custom_cancel, "#424242", "#616161"),
        ("Info", lambda: print("Clicked Info!"), "#2196f3", "#1976d2"),
    ], sticky_bottom=False)

    dialog.add_selections(
        name="preferences",
        title="Preferences",
        options=[
            ("email_notifications", "Email notifications"),
            ("sms_alerts", "SMS alerts"),
            ("dark_mode", "Enable dark mode"),
            ("bright_mode", "Enable dark mode"),
            ("light_mode", "Enable dark mode"),
        ],
        default=["dark_mode"],
        required=True,
        min_selected=1,
        active_bg="red",
        inactive_bg="black",
        columns=4
    )
    dialog.add_dropdown_field(
        field_name="role",
        display_name="User Role",
        options=[
            ("admin", "Administrator"),
            ("editor", "Editor"),
            ("viewer", "Viewer")
        ],
        default="editor",
        required=True,
        layout="inline"
    )

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