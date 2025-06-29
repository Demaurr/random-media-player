import tkinter as tk
from tkinter import ttk

from category_manager import CategoryManager
from static_methods import sort_treeview_column
from custom_messagebox import showinfo, showwarning, showerror, askyesno
from player_constants import Colors

class Tooltip:
    def __init__(self, widget, category_window):
        self.widget = widget
        self.category_window = category_window
        self.tooltip = None
        self.text = None
        self.widget.bind('<Motion>', self.on_motion)
        self.widget.bind('<Leave>', self.hide_tooltip)
        self.last_item = None
        
    def show_tooltip(self, text, event):
        x = event.x_root + 15
        y = event.y_root + 10

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tooltip,
            text=text,
            justify='left',
            background=Colors.BLACK,
            foreground=Colors.PLAIN_WHITE,
            relief='solid',
            borderwidth=1,
            font=("Segoe UI", 9),
            padx=5,
            pady=5
        )
        label.pack()
        
        self.text = text

    def on_motion(self, event):
        item = self.widget.identify_row(event.y)
        
        if not item:
            self.hide_tooltip()
            self.last_item = None
            return
            
        if item != self.last_item:
            self.hide_tooltip()
            self.last_item = item
            values = self.widget.item(item)['values']
            if values and len(values) > 1:
                categories_text = values[1]
                if '+' in categories_text:
                    file_path = values[2]
                    categories = self.category_window.category_manager.get_categories_of_files(file_path)
                    if self.category_window.selected_category in categories:
                        categories.remove(self.category_window.selected_category)
                    
                    if categories:
                        tooltip_text = "All categories:\n" + "\n".join(f"• {cat}" for cat in sorted(categories))
                        self.show_tooltip(tooltip_text, event)

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None
            self.text = None

class CategoryWindow(tk.Toplevel):
    def __init__(self, parent, files=None):
        super().__init__(parent)
        self.master = parent
        self.title("Category Manager")
        self.geometry("850x400")
        self.minsize(850, 400)  # Set minimum size
        self.configure(bg=Colors.PLAIN_BLACK)
        
        self.category_manager = CategoryManager()
        self.files = files if isinstance(files, list) else [files] if files else []
        self.selected_category = None
        
        self._set_styles()
        self._create_widgets()
        self.center_window()
        
        self.transient(parent)
        self.grab_set()
        
    def _set_styles(self):
        style = ttk.Style(self.master)
        
        style.configure(
            "Category.Treeview",
            background=Colors.PLAIN_BLACK,
            foreground=Colors.PLAIN_WHITE,
            fieldbackground=Colors.PLAIN_BLACK,
            rowheight=30,
            borderwidth=0,
            font=("Segoe UI", 10)
        )
        
        style.configure(
            "Category.Treeview.Heading",
            background=Colors.BLACK_HOVER,  
            foreground=Colors.HEADER_COLOR_RED,
            relief="flat",
            font=("Segoe UI", 11, "bold")
        )
        style.map(
            "Category.Treeview",
            background=[("selected", "#8B0000")],
            foreground=[("selected", Colors.PLAIN_WHITE)]
        )
        
        style.layout("Category.Treeview", [('Category.Treeview.treearea', {'sticky': 'nswe'})])

    def _create_widgets(self):
        self.left_frame = tk.Frame(self, bg=Colors.PLAIN_BLACK, padx=10, pady=10)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)
        
        self.right_frame = tk.Frame(self, bg=Colors.PLAIN_BLACK, padx=10, pady=10)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.category_label = tk.Label(
            self.left_frame,
            text="Categories",
            font=("Segoe UI", 16, "bold"),
            bg=Colors.PLAIN_BLACK,
            fg=Colors.HEADER_COLOR_RED
        )
        self.category_label.grid(row=0, column=0, pady=(0, 10), sticky='w')
        
        self.category_tree = ttk.Treeview(
            self.left_frame,
            columns=("Category", "Count", "Status"),
            show="headings",
            style="Category.Treeview"
        )
        self.category_tree.heading("Category", text="Category",
            command=lambda: sort_treeview_column(self.category_tree, "Category", False))
        self.category_tree.heading("Count", text="#", anchor=tk.CENTER,
            command=lambda: sort_treeview_column(self.category_tree, "Count", False))
        self.category_tree.heading("Status", text="In Selection",
            command=lambda: sort_treeview_column(self.category_tree, "Status", False))
        self.category_tree.column("Category", minwidth=100)
        self.category_tree.column("Count", width=50, anchor=tk.CENTER)
        self.category_tree.column("Status", width=80)
        self.category_tree.grid(row=1, column=0, sticky='nsew')
        self.category_controls = tk.Frame(self.left_frame, bg=Colors.PLAIN_BLACK)
        self.category_controls.grid(row=2, column=0, pady=5, sticky='ew')
        
        entry_frame = tk.Frame(self.category_controls, bg=Colors.PLAIN_BLACK)
        entry_frame.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        
        self.new_category_entry = tk.Entry(
            entry_frame,
            bg=Colors.BLACK,
            fg=Colors.PLAIN_WHITE,
            insertbackground=Colors.PLAIN_WHITE,
            font=("Segoe UI", 10),
            relief=tk.FLAT
        )
        self.new_category_entry.pack(fill=tk.X, ipady=5)
        
        self.files_label = tk.Label(
            self.right_frame,
            text="Files in Category",
            font=("Segoe UI", 16, "bold"),
            bg=Colors.PLAIN_BLACK,
            fg=Colors.HEADER_COLOR_RED
        )
        self.files_label.grid(row=0, column=0, pady=(0, 10), sticky='w')
        self.files_tree = ttk.Treeview(
            self.right_frame,
            columns=("Filename", "Categories", "Full Path"),
            show="headings",
            style="Category.Treeview"
        )
        self.files_tree.heading("Filename", text="File",
            command=lambda: sort_treeview_column(self.files_tree, "Filename", False))
        self.files_tree.heading("Categories", text="In Categories",
            command=lambda: sort_treeview_column(self.files_tree, "Categories", False))
        self.files_tree.heading("Full Path", text="Full Path",
            command=lambda: sort_treeview_column(self.files_tree, "Full Path", False))
        self.files_tree.column("Filename", minwidth=100)
        self.files_tree.column("Categories", width=120)
        self.files_tree.column("Full Path", width=0, stretch=False)
        self.files_tree.tag_configure('in_category', font=("Segoe UI", 10, "bold"), foreground="red")
        
        self.files_tree.grid(row=1, column=0, sticky='nsew')
        self.file_controls = tk.Frame(self.right_frame, bg=Colors.PLAIN_BLACK)
        self.file_controls.grid(row=2, column=0, pady=5, sticky='ew')
        
        def create_button(parent, text, command, bg_color, hover_color):
            btn = tk.Button(
                parent,
                text=text,
                command=command,
                bg=bg_color,
                fg=Colors.PLAIN_WHITE,
                font=("Segoe UI", 10, "bold"),
                relief=tk.FLAT,
                padx=10,
                pady=0,
                cursor="hand2"
            )
            btn.bind("<Enter>", lambda e: btn.configure(background=hover_color))
            btn.bind("<Leave>", lambda e: btn.configure(background=bg_color))
            return btn
    
        self.add_category_btn = create_button(
            self.category_controls, "Add", self.add_category,
            Colors.GREEN, Colors.GREEN_HOVER
        )
        self.add_category_btn.pack(side=tk.LEFT, padx=2)
        
        self.rename_category_btn = create_button(
            self.category_controls, "Rename", self.rename_category,
            Colors.ORANGE, Colors.ORANGE_HOVER
        )
        self.rename_category_btn.pack(side=tk.LEFT, padx=2)
        
        self.delete_category_btn = create_button(
            self.category_controls, "Delete", self.delete_category,
            Colors.RED, Colors.RED_HOVER
        )
        self.delete_category_btn.pack(side=tk.LEFT, padx=2)
        
        # File Button
        self.remove_file_btn = create_button(
            self.file_controls, "Remove Selected", self.remove_selected_files,
            Colors.RED, Colors.RED_HOVER
        )
        self.remove_file_btn.pack(side=tk.LEFT, padx=2)
        self._keybindings()

        self.tooltip = Tooltip(self.files_tree, self)
    
    def _keybindings(self):
        """Set up key bindings for the category window."""
        self.bind('<Return>', lambda e: self.add_category())
        self.bind('<Escape>', lambda e: self.destroy())
        self.category_tree.bind('<<TreeviewSelect>>', self.on_category_select)
        self.files_tree.bind('<Delete>', self.remove_selected_files)
        self.refresh_categories(select_recent=True)

    def refresh_categories(self, select_recent=False):
        """Refresh the category list and optionally select the most recent category."""
        self.category_tree.delete(*self.category_tree.get_children())
        categories_with_dates = self.category_manager.get_all_categories_with_dates()
        categories_with_dates.sort(key=lambda x: x[1], reverse=True)

        items = []
        for category, _ in categories_with_dates:
            files = self.category_manager.get_category_files(category)
            files_in_category = 0
            if self.files:
                for file in self.files:
                    if self.category_manager.is_file_in_category(category, file):
                        files_in_category += 1

            if not self.files:
                status = "—"
            elif files_in_category == 0:
                status = "None"
            elif files_in_category == len(self.files):
                status = "All"
            else:
                status = f"{files_in_category}/{len(self.files)}"

            item_id = self.category_tree.insert("", tk.END, values=(category, str(len(files)), status))
            items.append(item_id)

        if select_recent and items:
            self.category_tree.selection_set(items[0])
            self.category_tree.see(items[0])
            self.on_category_select()

    def on_category_select(self, event=None):
        """Handle category selection."""
        self.files_tree.delete(*self.files_tree.get_children())
        selection = self.category_tree.selection()
        if selection:
            category = self.category_tree.item(selection[0])['values'][0]
            self.selected_category = category
            files = self.category_manager.get_category_files(category)

            # Batch load all categories for all files in this category
            file_categories_map = {f: set(self.category_manager.get_categories_of_files(f)) for f in files}
            selected_files_in_category = set(self.files) if self.files else set()

            for file in sorted(files):
                filename = file.split('\\')[-1]
                categories = file_categories_map[file].copy()
                if category in categories:
                    categories.remove(category)
                if not categories:
                    categories_text = ""
                elif len(categories) <= 2:
                    categories_text = ", ".join(categories)
                else:
                    categories_text = f"{list(categories)[0]}, {list(categories)[1]} +{len(categories)-2}"
                item_id = self.files_tree.insert("", tk.END, values=(filename, categories_text, file))
                if file in selected_files_in_category:
                    self.files_tree.item(item_id, tags=('in_category',))

    def add_category(self):
        """Add files to a category."""
        category_name = self.new_category_entry.get().strip()
        if not category_name:
            if not self.selected_category:
                showwarning(self, "Warning", "Please enter a category name or select an existing category.")
                return
            category_name = self.selected_category
            
        if self.files:
            added_count = 0
            already_exists_count = 0
            
            for file_path in self.files:
                if file_path and self.category_manager.add_to_category(category_name, file_path):
                    added_count += 1
                else:
                    already_exists_count += 1
            
            if added_count > 0:
                showinfo(self, "Success", 
                    f"Added {added_count} file{'s' if added_count > 1 else ''} to category '{category_name}'"
                    + (f"\n{already_exists_count} file{'s' if already_exists_count > 1 else ''} already in category" if already_exists_count > 0 else "")
                )
            elif already_exists_count > 0:
                showinfo(self, "Info", f"All {already_exists_count} files already exist in this category.")
        
        self.new_category_entry.delete(0, tk.END)
        self.refresh_categories(select_recent=True)

    def rename_category(self):
        """Rename selected category."""
        selection = self.category_tree.selection()
        if not selection:
            showwarning(self, "Warning", "Please select a category to rename.")
            return
            
        old_name = self.category_tree.item(selection[0])['values'][0]
        new_name = self.new_category_entry.get().strip()
        
        if not new_name:
            showwarning(self, "Warning", "Please enter a new category name.")
            return

        success, message = self.category_manager.rename_category(old_name, new_name, merge=False)
        
        if not success and "already exists" in message:
            merge = askyesno(
                self,
                "Category Exists",
                f"Category '{new_name}' already exists.\nWould you like to merge '{old_name}' into '{new_name}'?\n\n" +
                "Note: This will combine all files and remove duplicates.",
                icon='question'
            )
            if merge:
                success, message = self.category_manager.rename_category(old_name, new_name, merge=True)

        if success:
            showinfo(self, "Success", message)
            self.new_category_entry.delete(0, tk.END)
            self.refresh_categories()
        else:
            showerror(self, "Error", message)

    def delete_category(self):
        """Delete selected category."""
        selection = self.category_tree.selection()
        if not selection:
            showwarning(self, "Warning", "Please select a category to delete.")
            return
            
        category = self.category_tree.item(selection[0])['values'][0]
        if askyesno(self, "Confirm Delete", f"Are you sure you want to delete category '{category}'?"):
            if self.category_manager.delete_category(category):
                showinfo(self, "Success", f"Deleted category '{category}'")
                self.refresh_categories()
            else:
                showerror(self, "Error", "Failed to delete category.")

    def remove_selected_files(self, event=None):
        """Remove selected files from the current category."""
        selected_files = self.files_tree.selection()
        if not selected_files:
            showwarning(self, "Warning", "Please select files to remove.")
            return
            
        category_selection = self.category_tree.selection()
        if not category_selection:
            showwarning(self, "Warning", "Please select a category first.")
            return
            
        category = self.category_tree.item(category_selection[0])['values'][0]
        
        if askyesno(self, "Confirm Remove", 
                              f"Remove {len(selected_files)} file(s) from category '{category}'?"):
            removed_count = 0
            for item in selected_files:
                file_path = self.files_tree.item(item)['values'][2]
                if self.category_manager.remove_from_category(category, file_path):
                    removed_count += 1
            
            if removed_count > 0:
                showinfo(self, "Success", 
                    f"Removed {removed_count} file{'s' if removed_count > 1 else ''} from category '{category}'"
                )
                self.refresh_categories()
                self.on_category_select()
            else:
                showerror(self, "Error", "Failed to remove files from category.")

    def center_window(self):
        """Center the window on the screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')