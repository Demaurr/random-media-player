import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os

from player_constants import Colors
from custom_messagebox import showerror, showinfo, showwarning, askyesno
from notes_manager import NotesManager
from snippets_manager import SnippetsManager

class NotesManagerGUI:
    def __init__(self, notes_manager=None, snippets_manager=None, 
                 parent=None, file_path=None, file_hash=None, minimal=False):
        self.notes_manager = notes_manager or NotesManager()
        self.root = tk.Toplevel(parent) if parent else tk.Toplevel()
        self.root.title("File Notes Manager")
        self.root.geometry("1000x600")
        self.root.resizable(False, False)
        self.center_window()
        self.root.transient(parent)
        self.root.grab_set()
        self.root.focus_force()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.title("Notes Manager" if not file_path 
                        else "Notes Manager - " + os.path.basename(file_path))

        self.colors = {
            'bg_primary': Colors.PLAIN_BLACK,
            'bg_secondary': Colors.PLAIN_BLACK,
            'bg_tertiary': Colors.BLACK_ENTRYBOX, 
            'fg_primary': Colors.PLAIN_WHITE,    
            'fg_secondary': '#cccccc',     
            'accent_red': Colors.PLAIN_RED,      
            'accent_orange': Colors.PLAIN_ORANGE,
            'accent_green': '#44ff44',    
            'border': '#555555',          
            'select': '#ff4444',         
            'button_bg': '#2d2d2d',       
            'button_hover': '#3d3d3d'     
        }
        
        self.setup_styles()
        self.snippets_manager = snippets_manager or SnippetsManager()
        
        # file_path display and index_hash internally stored
        self.current_file_path = tk.StringVar()
        self.current_index_hash = None
        if file_path:
            self.current_file_path.set(file_path)
            self.current_index_hash = self.notes_manager._resolve_key(file_path)
        elif file_hash:
            self.current_index_hash = file_hash
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        
        self.current_notes_list = []
        
        self.apply_theme()
        self.setup_ui()
        self._key_bindings()
        self.refresh_notes_list()
        self.load_note()

    def on_close(self):
        self.root.grab_release()
        self.root.destroy()

    def _key_bindings(self):
        self.root.bind('<Escape>', lambda e: self.root.destroy())
        
    def setup_styles(self):
        self.style = ttk.Style()
        
        self.root.configure(bg=Colors.PLAIN_BLACK)
        self.style.theme_use('clam')
        self.style.configure('Dark.TFrame', 
                           background=Colors.PLAIN_BLACK,
                           borderwidth=0)
        
        self.style.configure('Card.TFrame', 
                           background=Colors.PLAIN_BLACK,
                           borderwidth=0,
                           relief='solid')
        self.style.configure('Dark.TLabel', 
                           background=Colors.PLAIN_BLACK,
                           foreground=Colors.PLAIN_WHITE,
                           font=('Segoe UI', 12))
        
        self.style.configure('Card.TLabel', 
                           background=Colors.PLAIN_BLACK,
                           foreground=Colors.PLAIN_WHITE,
                           font=('Segoe UI', 11))
        
        self.style.configure('Title.TLabel', 
                           background=Colors.PLAIN_BLACK,
                           foreground=Colors.PLAIN_RED,
                           font=('Segoe UI', 11, 'bold'))
        
        self.style.configure('Info.TLabel', 
                           background=Colors.PLAIN_BLACK,
                           foreground=self.colors['fg_secondary'],
                           font=('Segoe UI', 9))
        self.style.configure('Dark.TButton',
                            background=Colors.PLAIN_BLACK,
                           foreground=Colors.PLAIN_WHITE,
                           borderwidth=0,
                           focuscolor='none',
                           font=('Segoe UI', 10, 'bold'))
        
        self.style.map('Dark.TButton',
                      foreground=[('active', Colors.PLAIN_GRAY),
                                ('pressed', Colors.PLAIN_RED)])
        
        self.style.configure('Accent.TButton',
                            background=Colors.PLAIN_BLACK,
                           foreground=Colors.PLAIN_RED,
                           borderwidth=0,
                           focuscolor='none',
                           font=('Segoe UI', 10, 'bold'))
        
        self.style.map('Accent.TButton',
                      foreground=[('active', '#ff6666'),
                                ('pressed', '#cc2222')])
        
        self.style.configure('Dark.TEntry',
            fieldbackground="#1a1a1a",
            foreground=Colors.PLAIN_WHITE,
            borderwidth=0,
            insertcolor=Colors.PLAIN_BLACK,
            background="#1a1a1a",
            font=('Segoe UI', 11)
        )

        self.style.layout('Dark.TEntry', [
            ('Entry.padding', {'sticky': 'nswe', 'children': [
                ('Entry.textarea', {'sticky': 'nswe'})
            ]})
        ])
        self.style.configure('Dark.TCombobox',
                           fieldbackground=Colors.BLACK_ENTRYBOX,
                           foreground=Colors.PLAIN_WHITE,
                           borderwidth=0,
                           arrowcolor=Colors.PLAIN_WHITE)
        self.style.configure('Dark.TLabelframe',
                           background=Colors.PLAIN_BLACK,
                           borderwidth=0,
                           relief='solid',)
        
        self.style.configure('Dark.TLabelframe.Label',
                           background=Colors.PLAIN_BLACK,
                           foreground=Colors.PLAIN_RED,
                           font=('Segoe UI', 15, 'bold'))
    
    def apply_theme(self):
        """Apply the dark theme to the window."""
        self.root.configure(bg=Colors.PLAIN_BLACK)
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="15", style='Dark.TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        left_panel = ttk.Frame(main_frame, padding="10", style='Card.TFrame')
        left_panel.grid(row=0, column=0, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_panel.columnconfigure(0, weight=1)
        left_panel.rowconfigure(3, weight=1)

        search_frame = ttk.LabelFrame(left_panel, text="Search & Filter", padding="10", style='Dark.TLabelframe')
        search_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        search_frame.columnconfigure(0, weight=1)
        
        ttk.Label(search_frame, text="Search:", style='Card.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(search_frame, textvariable=self.search_var, width=30, style='Dark.TEntry', font=('Segoe UI', 9)).grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10), ipady=2)

        filter_frame = ttk.Frame(search_frame, style='Card.TFrame')
        filter_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))

        btn_all = ttk.Button(filter_frame, text="All", command=self.show_all_notes, style='Dark.TButton')
        btn_all.grid(row=0, column=0, padx=(0, 5))
        btn_recent = ttk.Button(filter_frame, text="Recent", command=self.show_recent_notes, style='Dark.TButton')
        btn_recent.grid(row=0, column=1, padx=(0, 5))
        btn_top = ttk.Button(filter_frame, text="Top Rated", command=self.show_high_rated, style='Dark.TButton')
        btn_top.grid(row=0, column=2)

        for btn in (btn_all, btn_recent, btn_top):
            btn.bind("<Enter>", lambda e: e.widget.configure(cursor="hand2"))
            btn.bind("<Leave>", lambda e: e.widget.configure(cursor=""))

        listbox_frame = ttk.Frame(left_panel, style='Card.TFrame')
        listbox_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)
        
        self.notes_listbox = tk.Listbox(
            listbox_frame,
            height=12,
            bg=Colors.BLACK_ENTRYBOX,
            fg=Colors.PLAIN_WHITE,
            selectbackground=Colors.PLAIN_RED,
            selectforeground=Colors.PLAIN_WHITE,
            borderwidth=0,
            font=('Segoe UI', 11),
            selectmode=tk.EXTENDED
        )
        self.notes_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.notes_listbox.bind('<Double-Button-1>', self.on_note_double_click)
        self.notes_listbox.bind('<Return>', self.on_note_double_click)
        self.notes_listbox.bind('<<ListboxSelect>>', lambda e: None)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.notes_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.notes_listbox.configure(yscrollcommand=scrollbar.set)
        
        right_panel = ttk.Frame(main_frame, padding="10", style='Card.TFrame')
        right_panel.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(1, weight=1)
        
        file_path_frame = ttk.Frame(right_panel, style='Card.TFrame')
        file_path_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_path_frame.columnconfigure(0, weight=0)  
        file_path_frame.columnconfigure(1, weight=1)  

        ttk.Label(file_path_frame, text="File Path:", style='Card.TLabel').grid(
            row=0, column=0, sticky=tk.W, padx=(0, 8)
        )

        self.video_key_entry = ttk.Entry(
            file_path_frame,
            textvariable=self.current_file_path,
            width=30,
            background="#1a1a1a",
            state="readonly",
        )
        self.video_key_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.video_key_entry.configure(font=('Segoe UI', 11), background="#1a1a1a")

        right_panel.columnconfigure(0, weight=1)

        edit_frame = ttk.LabelFrame(right_panel, text="Note Details", padding="15", style='Dark.TLabelframe')
        edit_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        edit_frame.columnconfigure(1, weight=1)
        edit_frame.rowconfigure(0, weight=1)
        
        ttk.Label(edit_frame, text="Note:", style='Card.TLabel', font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky=(tk.W, tk.N), padx=(0, 10))
        
        note_text_frame = ttk.Frame(edit_frame, style='Card.TFrame')
        note_text_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        note_text_frame.columnconfigure(0, weight=1)
        note_text_frame.rowconfigure(0, weight=1)
        
        self.note_text = tk.Text(note_text_frame, height=10, wrap=tk.WORD,
                               bg=Colors.BLACK_ENTRYBOX,
                               fg=Colors.PLAIN_WHITE,
                               insertbackground=Colors.PLAIN_WHITE,
                               selectbackground=Colors.PLAIN_RED,
                               selectforeground=Colors.PLAIN_WHITE,
                               borderwidth=0,
                               relief='solid',
                               font=('Segoe UI', 11))
        self.note_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.note_text.bind("<Control-KeyPress-s>", self.save_note)
        self.note_text.bind("<Control-KeyPress-S>", self.save_note)
        
        note_scrollbar = ttk.Scrollbar(note_text_frame, orient=tk.VERTICAL, command=self.note_text.yview)
        note_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.note_text.configure(yscrollcommand=note_scrollbar.set)
        
        metadata_frame = ttk.Frame(edit_frame, style='Card.TFrame')
        metadata_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        metadata_frame.columnconfigure(1, weight=1)
        metadata_frame.columnconfigure(3, weight=1)
        
        ttk.Label(metadata_frame, text="Rating:", style='Card.TLabel').grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.rating_var = tk.StringVar()
        self.rating_entry = ttk.Combobox(
            metadata_frame, textvariable=self.rating_var,
            values=["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
            width=15, style='Dark.TCombobox'
        )
        self.rating_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        ttk.Label(metadata_frame, text="Tags:", style='Card.TLabel').grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.tags_var = tk.StringVar()
        self.tags_entry = ttk.Entry(
            metadata_frame, textvariable=self.tags_var,
            style='Dark.TEntry', font=('Segoe UI', 10, "bold"), foreground="red"
        )
        self.tags_entry.grid(row=0, column=3, sticky=(tk.W, tk.E), pady=(0, 8))

        ttk.Label(metadata_frame, text="Mood:", style='Card.TLabel').grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.mood_var = tk.StringVar()
        self.mood_entry = ttk.Entry(
            metadata_frame, textvariable=self.mood_var,
            width=15, style='Dark.TEntry', font=('Segoe UI', 9)
        )
        self.mood_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 20))

        ttk.Label(metadata_frame, text="Context:", style='Card.TLabel').grid(row=1, column=2, sticky=tk.W, padx=(0, 5))
        self.context_var = tk.StringVar()
        self.context_entry = ttk.Entry(
            metadata_frame, textvariable=self.context_var,
            style='Dark.TEntry', font=('Segoe UI', 9)
        )
        self.context_entry.grid(row=1, column=3, sticky=(tk.W, tk.E), pady=(0, 8))

        ttk.Label(metadata_frame, text="Updated:", style='Card.TLabel').grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.timestamp_var = tk.StringVar()
        ttk.Label(metadata_frame, textvariable=self.timestamp_var, style='Info.TLabel').grid(row=2, column=1, columnspan=3, sticky=tk.W)
        
        button_frame = ttk.Frame(right_panel, style='Card.TFrame')
        button_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(15, 0))

        btn_load = ttk.Button(button_frame, text="Load", command=self.load_note, style='Dark.TButton')
        btn_load.grid(row=0, column=0, padx=(0, 8))
        btn_save = ttk.Button(button_frame, text="Save", command=self.save_note, style='Accent.TButton')
        btn_save.grid(row=0, column=1, padx=(0, 8))
        btn_delete = ttk.Button(button_frame, text="Delete", command=self.delete_note, style='Dark.TButton')
        btn_delete.grid(row=0, column=2, padx=(0, 8))
        btn_clear = ttk.Button(button_frame, text="Clear", command=self.clear_form, style='Dark.TButton')
        btn_clear.grid(row=0, column=3, padx=(0, 8))
        btn_refresh = ttk.Button(button_frame, text="Refresh", command=self.refresh_notes_list, style='Dark.TButton')
        btn_refresh.grid(row=0, column=4)

        for btn in (btn_load, btn_save, btn_delete, btn_clear, btn_refresh):
            btn.bind("<Enter>", lambda e: e.widget.configure(cursor="hand2"))
            btn.bind("<Leave>", lambda e: e.widget.configure(cursor=""))

        bottom_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(15, 0))
        bottom_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar()
    
    def on_search_change(self, *args):
        """Handle search input changes."""
        query = self.search_var.get().strip()
        if query:
            results = self.notes_manager.search_notes(query)
            self.populate_listbox(results)
        else:
            self.show_all_notes()
    
    def populate_listbox(self, notes_list):
        """
        Populate the listbox with file paths for visual clarity.
        Store internal mapping of index_hash -> note_data for later lookup.
        
        Args:
            notes_list: List of (index_hash, note_data) tuples from notes_manager
        """
        self.notes_listbox.delete(0, tk.END)
        self.current_notes_list = []
        
        for index_hash, note_data in notes_list:
            file_paths = note_data.get("file_paths", set())
            
            if file_paths:
                for file_path in sorted(file_paths):
                    display_name = os.path.basename(file_path)
                    self.notes_listbox.insert(tk.END, display_name)
                    self.current_notes_list.append((index_hash, note_data, file_path))
            else:
                self.notes_listbox.insert(tk.END, f"[Hash: {index_hash[:8]}...]")
                self.current_notes_list.append((index_hash, note_data, None))
    
    def on_note_select(self, event):
        pass
    
    def on_note_double_click(self, event):
        """Show note details only on double-click or Enter key."""
        widget = event.widget
        try:
            if widget.curselection():
                index = widget.curselection()[0]
            else:
                index = widget.index(tk.ACTIVE)

            if index < len(self.current_notes_list):
                index_hash, note_data, file_path = self.current_notes_list[index]
                
                if not self.is_snippet_file(file_hash=index_hash):
                    self.enable_all_fields()
                
                if file_path:
                    self.current_file_path.set(file_path)
                self.current_index_hash = index_hash
                self.load_note_data(note_data)
        except Exception as e:
            showerror(self.root, "Error", f"Failed to load notes: {e}")

    
    def load_note(self):
        """Load note for the current file path."""
        file_path = self.current_file_path.get().strip()
        file_hash = self.current_index_hash
        if not file_path:
            messagebox.showwarning("Warning", "Please select a file or enter a file path.")
            return

        is_snippet = self.is_snippet_file(file_hash=file_hash)
        
        if is_snippet:
            self.disable_non_snippet_fields()
            snippet = self.snippets_manager.get_snippet_by_output_file(file_path)
            self.note_text.delete(1.0, tk.END)
            self.note_text.insert(1.0, snippet.get("Notes", ""))
        else:
            self.enable_all_fields()
            note_data = self.notes_manager.get_note(file_path)
            if note_data:
                self.current_index_hash = self.notes_manager._resolve_key(file_path)
                self.load_note_data(note_data)
            else:
                self.clear_form()
    
    def load_note_data(self, note_data):
        """Load note data into form fields."""
        self.note_text.delete(1.0, tk.END)
        self.note_text.insert(1.0, note_data.get("note", ""))
        
        self.rating_var.set(str(note_data.get("rating", "")) if note_data.get("rating") is not None else "")
        self.tags_var.set(", ".join(note_data.get("tags", [])))
        self.mood_var.set(note_data.get("mood", ""))
        self.context_var.set(note_data.get("context", ""))
        
        timestamp = note_data.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                self.timestamp_var.set(dt.strftime("%Y-%m-%d %H:%M:%S"))
            except:
                self.timestamp_var.set(timestamp)
        else:
            self.timestamp_var.set("")

    
    def save_note(self, event=None):
        """Save note using file path (internally resolved to hash)."""
        file_path = self.current_file_path.get().strip()
        file_hash = self.current_index_hash
        note = self.note_text.get(1.0, tk.END).strip()

        if not file_path:
            showwarning(self.root, "Warning", "Please select or enter a file path.")
            return None
        if note == "":
            showwarning(self.root, "Warning", "Note cannot be empty.")
            return None

        confirm = askyesno(self.root, "Confirm Save", f"Are you sure you want to save the note for:\n{os.path.basename(file_path)}?")
        if not confirm:
            return None

        if self.is_snippet_file(file_hash=file_hash):
            success = self.snippets_manager.update_snippet(file_path, Notes=note)
            if not success:
                showerror(self.root, "Error", "Failed to update snippet note.")
                return None
            self.load_note()
            return

        rating = self.rating_var.get().strip()
        tags = self.tags_var.get().strip()
        mood = self.mood_var.get().strip()
        context = self.context_var.get().strip()

        rating_value = None
        if rating:
            try:
                rating_value = float(rating)
            except ValueError:
                showerror(self.root, "Error", "Rating must be a number.")
                return None

        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []

        self.notes_manager.set_note(
            file_key=file_path,
            note=note,
            rating=rating_value,
            tags=tags_list,
            mood=mood if mood else None,
            context=context if context else None
        )

        self.refresh_notes_list()
        self.update_stats()
        self.load_note()

    def is_snippet_file(self, file_hash=None):
        if not file_hash:
            return False
        return self.snippets_manager.is_snippet(file_hash)
    
    def disable_non_snippet_fields(self):
        """Disable metadata fields for snippet files."""
        self.rating_entry.config(state=tk.DISABLED)
        self.tags_entry.config(state=tk.DISABLED)
        self.mood_entry.config(state=tk.DISABLED)
        self.context_entry.config(state=tk.DISABLED)

    def enable_all_fields(self):
        """Enable all metadata fields."""
        self.rating_entry.config(state=tk.NORMAL)
        self.tags_entry.config(state=tk.NORMAL)
        self.mood_entry.config(state=tk.NORMAL)
        self.context_entry.config(state=tk.NORMAL)
    
    def delete_note(self):
        """Delete the current note using file path."""
        file_path = self.current_file_path.get().strip()
        file_hash =  self.current_index_hash

        if self.is_snippet_file(file_hash=file_hash):
            showwarning(self.root, "Not Allowed", "Cannot delete note for a snippet file.")
            return
    
        if not file_path:
            showwarning(self.root, "Warning", "Please select or enter a file path.")
            return
        
        if askyesno(self.root, "Confirm Delete", f"Are you sure you want to delete the note for:\n{os.path.basename(file_path)}?"):
            self.notes_manager.delete_note(file_path)
            self.clear_form()
            self.refresh_notes_list()
            self.update_stats()
    
    def clear_form(self):
        """Clear all form fields."""
        self.note_text.delete(1.0, tk.END)
        self.rating_var.set("")
        self.tags_var.set("")
        self.mood_var.set("")
        self.context_var.set("")
        self.timestamp_var.set("")
    
    def refresh_notes_list(self):
        """Refresh the notes list display."""
        self.show_all_notes()
    
    def show_all_notes(self):
        """Show all notes in the listbox."""
        notes_list = self.notes_manager.list_notes()
        self.populate_listbox(notes_list)
        self.search_var.set("")
    
    def show_recent_notes(self):
        """Show recent notes."""
        notes_list = self.notes_manager.get_recent_notes(20)
        self.populate_listbox(notes_list)
        self.search_var.set("")
    
    def show_high_rated(self):
        """Show highly rated notes (rating >= 7)."""
        notes_list = self.notes_manager.get_notes_by_rating(7)
        self.populate_listbox(notes_list)
        self.search_var.set("")
    
    def update_stats(self):
        """Update the statistics display."""
        total_notes = self.notes_manager.get_notes_count()
        
        rated_notes = sum(1 for _, data in self.notes_manager.list_notes() if data.get('rating') is not None)
        tagged_notes = sum(1 for _, data in self.notes_manager.list_notes() if data.get('tags'))
        
        stats_text = f"Total Notes: {total_notes} | Rated: {rated_notes} | Tagged: {tagged_notes}"

    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

def open_notes_manager_gui(notes_manager, parent=None, file_path=None):
    """
    Function to open the Notes Manager GUI.
    Call this from your main application.

    Args:
        notes_manager: Instance of NotesManager
        parent: Optional parent Tkinter window
        file_path: Optional initial file path to load
    """
    gui = NotesManagerGUI(notes_manager, parent=parent, file_path=file_path)
    return gui

if __name__ == "__main__":
    from notes_manager import NotesManager

    notes_manager = NotesManager()
    gui = open_notes_manager_gui(notes_manager, file_path="sample_3.mp4")

    gui.root.mainloop()
    
    print("Testing Notes Manager GUI.")