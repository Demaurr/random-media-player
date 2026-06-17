import tkinter as tk


class EditableTextbox(tk.Frame):
    def __init__(
        self,
        parent,
        text="",

        # display mode
        display_font=("Segoe UI", 11),
        display_fg="#ffffff",
        display_bg="#1e1e1e",

        # edit mode
        edit_font=("Segoe UI", 11),
        edit_fg="#ffffff",
        edit_bg="#2a2a2a",

        hover_bg=None,

        multiline=True,
        height=4,
        wrap="word",
        wraplength=400,

        editable=True,

        on_save=None,
        on_edit_start=None,
        validator=None,
        placeholder="Double-click to edit...",
    ):
        super().__init__(parent, bg=display_bg)

        self.value = text
        self.multiline = multiline
        self.editable = editable

        self.on_save = on_save
        self.on_edit_start = on_edit_start
        self.validator = validator

        self.display_font = display_font
        self.display_fg = display_fg
        self.display_bg = display_bg

        self.edit_font = edit_font
        self.edit_fg = edit_fg
        self.edit_bg = edit_bg
        self.height = height
        self.wrap = wrap

        self.placeholder = placeholder

        self.hover_bg = hover_bg or display_bg

        self.edit_bg = edit_bg

        self._editing = False

        self.wraplength = wraplength

        # DISPLAY LABEL
        self.label = tk.Label(
            self,
            anchor="w",
            justify="left",
            wraplength=self.wraplength
        )

        self._update_display()
        self.label.pack(fill="both", expand=True)

        self.label.bind("<Double-1>", self._enter_edit_mode)
        self.label.bind(
            "<Enter>",
            lambda e: self.label.configure(bg=self.hover_bg)
        )

        self.label.bind(
            "<Leave>",
            lambda e: self.label.configure(bg=self.display_bg)
        )

        self.text = None

    def _update_display(self):
        if self.value:
            self.label.config(
                text=self.value,
                fg=self.display_fg,
                font=self.display_font
            )
        else:
            self.label.config(
                text=self.placeholder,
                fg="#888888",
                font=self.display_font
            )

    def _enter_edit_mode(self, event=None):
        if self._editing or not self.editable:
            return

        self._editing = True

        if self.on_edit_start:
            self.on_edit_start()

        self.label.pack_forget()

        self.text = tk.Text(
            self,
            font=self.edit_font,
            fg=self.edit_fg,
            bg=self.edit_bg,
            insertbackground=self.edit_fg,
            relief="flat",
            bd=0,
            height=self.height,
            wrap=self.wrap,
        )

        self.text.insert("1.0", self.value)
        self.text.pack(fill="both", expand=True)
        self.text.focus_set()

        self.text.bind("<Control-Return>", self._exit_edit_mode)
        self.text.bind("<Control-KeyPress-S>", self._exit_edit_mode)
        self.text.bind("<Control-KeyPress-s>", self._exit_edit_mode)
        self.text.bind("<FocusOut>", self._exit_edit_mode)
        self.text.bind("<Escape>", self._cancel_edit)

    def _exit_edit_mode(self, event=None):
        if not self._editing:
            return

        new_value = self.text.get("1.0", "end").strip()

        # validation hook
        if self.validator:
            try:
                ok = self.validator(new_value)
                if ok is False:
                    self.text.focus_set()
                    return
            except Exception:
                self.text.focus_set()
                return

        self.value = new_value

        if self.on_save:
            self.on_save(self.value)

        self._destroy_editor()

    def _cancel_edit(self, event=None):
        self._destroy_editor()

    def _destroy_editor(self):
        if self.text:
            self.text.destroy()
            self.text = None

        # self.label.config(text=self.value if self.value else " ")
        self._update_display()
        self.label.pack(fill="both", expand=True)

        self._editing = False
    
    def get(self):
        return self.value

    def set(self, value):
        self.value = value
        self.label.config(text=value)