import csv
import tkinter as tk
from tkinter import ttk
import os

from fingerprint_manager import MediaFingerprintManager
from static_methods import (
    are_paths_same, 
    build_transfer_graph, 
    get_all_related_paths, 
    normalise_path, 
    sort_treeview_column,
    get_all_identity_paths_multi_optimized
)
from player_constants import ALL_MEDIA_CSV, Colors, ASSOCIATIONS_CSV
from custom_messagebox import showinfo, showwarning, showerror, askyesno
from associations_manager import FileAssociator
from tooltips import ToolTip


class FileAssociationWindow:
    def __init__(self, root, source_file=None, associator=None, graph=None, fingerprint_manager=None):
        self.root = root
        self.root.title("File Associations Manager")
        self.root.geometry("1000x600")
        self.root.minsize(1000, 600)
        self.root.configure(bg=Colors.PLAIN_BLACK)

        self.source_file = normalise_path(source_file) if source_file else None
        self.source_hash = None
        self.fingerprint_manager = fingerprint_manager or MediaFingerprintManager()
        
        if self.source_file and self.fingerprint_manager:
            self.source_hash = self.fingerprint_manager.get_index_hash_by_path(self.source_file)
        
        title = "File Associations Manager"
        if self.source_file:
            title += f" - {os.path.basename(self.source_file)}"
        self.root.title(title)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.root.bind("<Escape>", self.on_closing)

        self.associator = associator or FileAssociator(csv_path=ASSOCIATIONS_CSV, fingerprint_manager=self.fingerprint_manager)
        
        self.transfer_graph = graph or build_transfer_graph()
        self.root.withdraw()
        self.root.deiconify()

        self.related_hashes = set()
        if self.source_hash and self.fingerprint_manager:
            self._build_related_hashes_cache()

        self._setup_styles()
        self._load_all_media()
        self._create_widgets()
        self.center_window()

    def _build_related_hashes_cache(self):
        """Build cache of all hashes related to source file through transfer graph."""
        if not self.source_file:
            return
        
        related_paths = get_all_related_paths(self.source_file, self.transfer_graph)
        
        for path in related_paths:
            file_hash = self.fingerprint_manager.get_index_hash_by_path(path)
            if file_hash:
                self.related_hashes.add(file_hash)

    def _setup_styles(self):
        style = ttk.Style()

        style.configure(
            "Association.Treeview",
            background=Colors.PLAIN_BLACK,
            foreground=Colors.PLAIN_WHITE,
            fieldbackground=Colors.PLAIN_BLACK,
            rowheight=30,
            font=("Segoe UI", 10)
        )

        style.configure(
            "Association.Treeview.Heading",
            background=Colors.BLACK_HOVER,
            foreground=Colors.HEADER_COLOR_RED,
            font=("Segoe UI", 11, "bold")
        )

        style.map(
            "Association.Treeview",
            background=[("selected", "#8B0000")],
            foreground=[("selected", Colors.PLAIN_WHITE)]
        )

        style.configure(
            "Association.TCombobox",
            fieldbackground=Colors.BLACK_ENTRYBOX, 
            background=Colors.BLACK_ENTRYBOX,       
            foreground=Colors.PLAIN_BLACK,
            selectbackground=Colors.WHITE_HOVER,
            selectforeground=Colors.PLAIN_BLACK,
            font=("Segoe UI", 11, "bold") 
        )

    def _create_widgets(self):

        def add_hover_effect(button, normal_color, hover_color):
            button.bind("<Enter>", lambda e: button.config(fg=hover_color))
            button.bind("<Leave>", lambda e: button.config(fg=normal_color))

        self.left_frame = tk.Frame(self.root, bg=Colors.PLAIN_BLACK, padx=10, pady=10)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_frame = tk.Frame(self.root, bg=Colors.PLAIN_BLACK, padx=10, pady=10)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        if self.source_file:
            self.filepath_label = tk.Label(
                self.left_frame,
                text=f"File Path: {self.source_file}",
                font=("Segoe UI", 10, "italic"),
                bg=Colors.PLAIN_BLACK,
                fg=Colors.PLAIN_WHITE,
                wraplength=450,
                justify="left",
                anchor="w"
            )
            self.filepath_label.pack(anchor="w", pady=(0, 10))

        self.assoc_label = tk.Label(
            self.left_frame,
            text="File Associations",
            font=("Segoe UI", 16, "bold"),
            bg=Colors.PLAIN_BLACK,
            fg=Colors.HEADER_COLOR_RED
        )
        self.assoc_label.pack(anchor='w', pady=(0, 10))

        self.assoc_tree = ttk.Treeview(
            self.left_frame,
            columns=("Source", "Target", "Type", "Date", "Hidden"),
            show="headings",
            style="Association.Treeview"
        )

        self.assoc_tree.heading("Source", text="Source File",
            command=lambda: sort_treeview_column(self.assoc_tree, "Source", False))
        self.assoc_tree.heading("Target", text="Target File",
            command=lambda: sort_treeview_column(self.assoc_tree, "Target", False))
        self.assoc_tree.heading("Type", text="Type",
            command=lambda: sort_treeview_column(self.assoc_tree, "Type", False))
        self.assoc_tree.heading("Date", text="Date",
            command=lambda: sort_treeview_column(self.assoc_tree, "Date", False))

        self.assoc_tree.column("Source", width=200)
        self.assoc_tree.column("Target", width=150)
        self.assoc_tree.column("Type", width=80)
        self.assoc_tree.column("Date", width=80)
        self.assoc_tree.column("Hidden", width=0, stretch=False)

        self.assoc_tree.pack(fill=tk.BOTH, expand=True)
        self.assoc_tree.tag_configure("has_assoc", foreground=Colors.PLAIN_RED, font=("Segoe UI", 10, "bold"))
        self.assoc_tree.tag_configure("is_assoc", foreground=Colors.PLAIN_ORANGE, font=("Segoe UI", 10, "bold"))


        self.search_label = tk.Label(
            self.right_frame,
            text="Add Association",
            font=("Segoe UI", 16, "bold"),
            bg=Colors.PLAIN_BLACK,
            fg=Colors.HEADER_COLOR_RED
        )
        self.search_label.pack(anchor='w', pady=(0, 10))

        search_frame = tk.Frame(self.right_frame, bg=Colors.PLAIN_BLACK)
        search_frame.pack(fill=tk.X, pady=(0, 5))

        tk.Label(
            search_frame,
            text="Search:",
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_WHITE
        ).pack(side=tk.LEFT)

        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind("<KeyRelease>", self._on_search)

        self.results_tree = ttk.Treeview(self.right_frame, columns=("Name", "Path", "Size"), show="headings")

        self.results_tree.heading("Name", text="Name")
        self.results_tree.column("Name", width=150, minwidth=100, stretch=True)

        self.results_tree.heading("Path", text="Path")
        self.results_tree.column("Path", width=150, minwidth=100, stretch=True)

        self.results_tree.column("Size", width=0, stretch=False)

        self.results_tree.pack(fill="both", expand=True)
        self.results_tree.bind("<Return>", self._save_association)

        self.stats_label = tk.Label(
            self.left_frame,
            text="Associations: 0 | Unique Sources: 0",
            font=("Segoe UI", 11, "bold"),
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_WHITE,
            anchor="w"
        )
        self.stats_label.pack(anchor="w", pady=(0, 10))


        type_frame = tk.Frame(self.left_frame, bg=Colors.PLAIN_BLACK)
        type_frame.pack(fill=tk.X, pady=5)

        types = ["related", "duplicate", "group", "screenshots", "categories",
                "snippets", "descriptions", "notes"]
        self.type_var = tk.StringVar(value="related")
        type_combo = ttk.Combobox(
            type_frame,
            textvariable=self.type_var,
            values=types,
            state="readonly",
            width=40,
            style="Association.TCombobox"
        )
        type_combo.pack(side=tk.LEFT, padx=5)

        self.add_btn = tk.Button(
            type_frame,
            text="Add Association",
            command=self._save_association,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.GREEN,
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.add_btn.pack(side=tk.LEFT, padx=5)

        self.update_btn = tk.Button(
            type_frame,
            text="Update",
            command=self._update_association,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.ORANGE,
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.update_btn.pack(side=tk.LEFT, padx=5)

        self.delete_btn = tk.Button(
            type_frame,
            text="Delete",
            command=self._delete_association,
            bg=Colors.PLAIN_BLACK,
            fg=Colors.RED,
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.delete_btn.pack(side=tk.LEFT, padx=5)

        buttons = [
            (self.add_btn, Colors.GREEN, Colors.GREEN_HOVER),
            (self.delete_btn, Colors.RED, Colors.RED_HOVER),
            (self.update_btn, Colors.ORANGE, Colors.ORANGE_HOVER),
        ]
        for btn, normal, hover in buttons:
            add_hover_effect(btn, normal, hover)

        self._load_associations()
        self._attach_tooltip_to_tree(self.assoc_tree)
        self._attach_tooltip_to_tree(self.results_tree)
        self.root.deiconify()

    def _attach_tooltip_to_tree(self, tree):
        """Attach tooltips to every cell in the given treeview."""
        tooltip = ToolTip(tree, text="", skipbindings=True, wraplength=300)

        def on_motion(event):
            row_id = tree.identify_row(event.y)
            col_id = tree.identify_column(event.x)

            if not row_id or not col_id:
                tooltip.hide_tooltip()
                return

            col_index = int(col_id.replace("#", "")) - 1
            values = tree.item(row_id, "values")
            if col_index < len(values):
                value = str(values[col_index])
                if value.strip():
                    tooltip.text = value
                    tooltip._on_enter(event)
                else:
                    tooltip.hide_tooltip()
            else:
                tooltip.hide_tooltip()

        tree.bind("<Motion>", on_motion, add="+")
        tree.bind("<Leave>", lambda e: tooltip.hide_tooltip(), add="+")
        ToolTip(self.delete_btn, "Delete the selected association", wraplength=200)
        ToolTip(self.update_btn, "Update the association type of the selected", wraplength=200)

    def _load_all_media(self):
        """Load all media records once into memory and preprocess for fast search."""
        self.all_media = []
        self.all_media_names = []

        with open(ALL_MEDIA_CSV, 'r', newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.all_media = list(reader)
            self.all_media_names = [row['File Name'].lower() for row in self.all_media]

    def _search_media(self, query):
        """Use preprocessed names for faster search."""
        return [
            self.all_media[i]
            for i, name in enumerate(self.all_media_names)
            if query in name
        ]

    def _on_search(self, event=None):
        """Handle search in ALL_MEDIA_CSV."""
        query = self.search_entry.get().lower()
        self.results_tree.delete(*self.results_tree.get_children())

        if len(query) < 2:
            return

        try:
            results = self._search_media(query)
            for row in results:
                file_name = row['File Name']
                file_path = row["Source Folder"] + "\\" + row['File Name']
                self.results_tree.insert("", "end", values=(file_name, file_path, row['File Size (Bytes)']))
        except Exception as e:
            showerror(self.root, "Error", f"Error searching ALL_MEDIA_CSV: {e}")

    def _is_related_to_source(self, source_hash, target_hash):
        """Check if an association is related to the source file via hash."""
        if not self.source_hash:
            return False
        
        return (source_hash in self.related_hashes or 
                target_hash in self.related_hashes)

    def _load_associations(self):
        """Load existing associations into the left treeview using hash-based lookups."""
        self.assoc_tree.delete(*self.assoc_tree.get_children())

        try:
            all_assocs = self.associator.get_all_associations()

            priority_assocs = []
            other_assocs = []

            total_assocs = len(all_assocs)
            
            if self.fingerprint_manager:
                unique_sources = len({a.get("source_hash") for a in all_assocs if a.get("source_hash")})
            else:
                unique_sources = len({normalise_path(a["source_file"]) for a in all_assocs})
            
            self.stats_label.config(text=f"Associations: {total_assocs} | Unique Sources: {unique_sources}")

            for assoc in all_assocs:
                src_hash = assoc.get('source_hash', '')
                tgt_hash = assoc.get('target_hash', '')
                
                if self.source_file and self._is_related_to_source(src_hash, tgt_hash):
                    priority_assocs.append(assoc)
                else:
                    other_assocs.append(assoc)

            other_assocs.sort(key=lambda a: a.get('association_date', ''))

            sorted_assocs = priority_assocs + other_assocs

            for assoc in sorted_assocs:
                source = os.path.basename(assoc['source_file'])
                target = os.path.basename(assoc['target_file'])
                assoc_type = assoc['association_type']
                date = assoc.get('association_date', '')
                
                src_hash = assoc.get('source_hash', '')
                tgt_hash = assoc.get('target_hash', '')

                tags = ()
                if self.source_file:
                    if src_hash in self.related_hashes:
                        tags += ("has_assoc",)
                    if tgt_hash in self.related_hashes:
                        tags += ("is_assoc",)

                hidden_data = f"{src_hash}|{tgt_hash}|{assoc['source_file']}|{assoc['target_file']}"
                self.assoc_tree.insert("", "end", 
                                      values=(source, target, assoc_type, date, hidden_data), 
                                      tags=tags)

        except Exception as e:
            showerror(self.root, "Error", f"Error loading associations: {e}")

    def _update_association(self):
        """Update the type of the selected association using hash-based lookup."""
        selected = self.assoc_tree.selection()
        if not selected:
            showwarning(self.root, "Warning", "Please select an association to update.")
            return

        item = self.assoc_tree.item(selected[0], "values")
        source_display, target_display, old_type, date, hidden_data = item

        new_type = self.type_var.get()
        if new_type == old_type:
            showwarning(self.root, "Warning", "New type is the same as the old type.")
            return

        try:
            if not hidden_data:
                showerror(self.root, "Error", "Unable to retrieve association data.")
                return
            
            parts = hidden_data.split("|")
            if len(parts) < 4:
                showerror(self.root, "Error", "Invalid association data format.")
                return
            
            src_hash, tgt_hash, src_path, tgt_path = parts[0], parts[1], parts[2], parts[3]

            found = False
            for assoc in self.associator.get_all_associations():
                if (assoc.get("source_hash") == src_hash and
                    assoc.get("target_hash") == tgt_hash and
                    assoc["association_type"] == old_type):
                    
                    self.associator.update_association_type(
                        assoc["source_file"], assoc["target_file"], old_type, new_type
                    )
                    found = True
                    break

            if found:
                showinfo(self.root, "Success", f"Association updated to type '{new_type}'.")
                self._load_associations()
            else:
                showerror(self.root, "Error", "Association not found.")
        except Exception as e:
            showerror(self.root, "Error", f"Failed to update association: {e}")

    def _save_association(self, event=None):
        """Save the association using FileAssociator with fingerprint support."""
        if not self.source_file:
            showwarning(self.root, "Warning", "No source file selected")
            return

        selected = self.results_tree.selection()
        if not selected:
            showwarning(self.root, "Warning", "Please select a target file")
            return

        target = self.results_tree.item(selected[0], "values")[1]
        
        if are_paths_same(self.source_file, target):
            showwarning(self.root, "Warning", "Cannot associate a file with itself.")
            return
        
        target_hash = self.fingerprint_manager.get_index_hash_by_path(normalise_path(target))
        if self.source_hash and target_hash == self.source_hash:
            showwarning(self.root, "Warning", "Cannot associate a file with itself (same content detected).")
            return
        
        target_size = self.results_tree.item(selected[0], "values")[2]
        assoc_type = self.type_var.get()

        try:
            self.associator.add_association(self.source_file, target, assoc_type, target_size=target_size)
            showinfo(self.root, "Success", "Association saved successfully!")
            
            self._build_related_hashes_cache()
            
            self._load_associations()
        except ValueError as ve:
            showwarning(self.root, "Warning", str(ve))
        except Exception as e:
            showerror(self.root, "Error", f"Failed to save association: {e}")

    def _delete_association(self):
        """Delete the selected association using hash-based lookup."""
        selected = self.assoc_tree.selection()
        if not selected:
            showwarning(self.root, "Warning", "Please select an association to delete.")
            return

        item = self.assoc_tree.item(selected[0], "values")
        source_display, target_display, assoc_type, date, hidden_data = item

        if not askyesno(self.root, "Confirm Delete", f"Remove association:\n{source_display} -> {target_display}?"):
            return

        try:
            if not hidden_data:
                showerror(self.root, "Error", "Unable to retrieve association data.")
                return
            
            parts = hidden_data.split("|")
            if len(parts) < 4:
                showerror(self.root, "Error", "Invalid association data format.")
                return
            
            src_hash, tgt_hash, src_path, tgt_path = parts[0], parts[1], parts[2], parts[3]
            
            found = False
            for assoc in self.associator.get_all_associations():
                if (assoc.get("source_hash") == src_hash and
                    assoc.get("target_hash") == tgt_hash and
                    assoc["association_type"] == assoc_type):
                    
                    self.associator.remove_association(
                        assoc["source_file"], assoc["target_file"], assoc["association_type"]
                    )
                    found = True
                    break

            if found:
                showinfo(self.root, "Success", "Association removed successfully!")
                self._load_associations()
            else:
                showerror(self.root, "Error", "Association not found.")
        except Exception as e:
            showerror(self.root, "Error", f"Failed to remove association: {e}")

    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def on_closing(self, event=None):
        """Handle window close or Escape key press."""
        self.root.destroy()