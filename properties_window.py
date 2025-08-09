import os
import csv
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
from player_constants import (
    SNIPPETS_HISTORY_CSV, 
    VIDEO_STATS_CSV, 
    VIDEO_SNIPPETS_FOLDER, 
    Colors
)
from static_methods import (
    convert_bytes, 
    get_file_transfer_history, 
    get_screenshots_for_file, 
    normalise_path, 
    seconds_to_hhmmss,
    get_watch_stats_for_filenames,
    get_all_related_paths
)
import threading
from image_player import ImageViewer
from videoplayer import MediaPlayerApp
from favorites_manager import FavoritesManager
from category_manager import CategoryManager
from notes_manager import NotesManager
from description_manager import DescriptionManager

class PropertiesWindow(tk.Toplevel):
    def __init__(self, parent, file_path, category_manager = None, favorites_manager=None, notes_manager=None, description_manager=None):
        super().__init__(parent)
        self.parent = parent
        self.file_path = file_path
        self.category_manager = category_manager or CategoryManager()
        self.favorites_manager = favorites_manager or FavoritesManager()
        self.notes_manager = notes_manager or NotesManager()
        self.description_manager = description_manager or DescriptionManager()
        self._setup_styles()
        self.geometry("1000x600")
        self.minsize(600, 400)
        self.maxsize(1000, 600)
        self.configure(bg=self.colors['bg_primary'])
        self.transient(self.parent)
        self.grab_set()
        self._center_window(self, 1000, 600)
        self._show_properties_window()

    def _setup_styles(self):
        self.colors = {
            'bg_primary': Colors.PLAIN_BLACK,     
            'bg_secondary': '#1A1F26',    
            'bg_card': '#252B35',        
            # 'bg_hover': '#2D3441',  
            'bg_hover': Colors.BLACK_HOVER,      
            'accent': '#dc3545',          
            'accent_hover': '#c82333',    
            'text_primary': Colors.PLAIN_WHITE,    
            'text_secondary': '#B0BEC5', 
            'text_muted': Colors.TEXT_MUTED_GRAY,     
            'border': '#37474F',         
            'success': Colors.SUCCESS_GREEN,        
            'warning': Colors.WARNING_ORANGE,        
        }

    def _show_properties_window(self):
        if os.path.isdir(self.file_path):
            messagebox.showinfo("Folder Selected", "The selected item is a folder. Please select a file.")
            return

        file_exists = os.path.isfile(self.file_path)
        if not file_exists:
            deleted_notice = True
        else:
            deleted_notice = False

        
        related_paths = get_all_related_paths(self.file_path)
        stats = self._get_video_stats()
        # screenshots = sorted(get_screenshots_for_file(os.path.basename(self.file_path)))
        screenshots = self._get_screenshots(related_paths)
        snippets = self._get_video_snippets()

        # win = tk.Toplevel(self.parent)
        # win.title(f"Properties - {os.path.basename(self.file_path)}")
        # win.geometry("1000x600")
        # win.minsize(600, 400)
        # win.maxsize(1000, 600)
        # win.configure(bg=self.colors['bg_primary'])
        # win.transient(self.parent)
        # win.grab_set()
        # self._center_window(win, 1000, 600)

        main_container = tk.Frame(self, bg=self.colors['bg_primary'])
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        self._create_header(main_container, stats, screenshots)

        if deleted_notice:
            warning_label = tk.Label(
                main_container,
                text="⚠️ This file has been deleted or moved. Stats are shown from history.",
                font=("Segoe UI", 11, "bold"),
                bg=self.colors['bg_primary'],
                fg=self.colors['warning'],
                anchor="w"
            )
            warning_label.pack(fill="x", pady=(0, 10), padx=10)

        self._create_scrollable_content(main_container, stats, screenshots, snippets)
        self._bind_window_events()
        # win.bind('<Escape>', lambda e: self.destroy())
        # print(self.file_path)
        # print(get_file_transfer_history(self.file_path).values())
        # print(normalise_path(self.file_path) in get_file_transfer_history(self.file_path).values())

    def _get_screenshots(self, file_paths):
        file_names = set(os.path.basename(path) for path in file_paths)
        screenshots = []
        for file_name in file_names:
            screenshots += get_screenshots_for_file(file_name)
        return sorted(screenshots)

    def _create_header(self, parent, stats, screenshots):
        header_frame = tk.Frame(parent, bg=self.colors['bg_card'], relief="flat", bd=0)
        header_frame.pack(fill="x", pady=(0, 15))
        
        border_frame = tk.Frame(header_frame, bg=self.colors['accent'], height=3)
        border_frame.pack(fill="x")
        
        content_frame = tk.Frame(header_frame, bg=self.colors['bg_card'])
        content_frame.pack(fill="x", padx=20, pady=15)
        thumb_frame = tk.Frame(content_frame, bg=self.colors['bg_card'])
        thumb_frame.pack(side="left", padx=(0, 20))

        self._create_thumbnail(thumb_frame, screenshots)

        info_frame = tk.Frame(content_frame, bg=self.colors['bg_card'])
        info_frame.pack(side="left", fill="both", expand=True)
        file_name = os.path.basename(self.file_path)
        name_label = tk.Label(
            info_frame, 
            text=file_name, 
            font=("Segoe UI", 18, "bold"), 
            bg=self.colors['bg_card'], 
            fg=self.colors['text_primary'],
            anchor="w",
            wraplength=700,
            justify="left"
        )
        name_label.pack(fill="x", pady=(0, 8))
        duration = seconds_to_hhmmss(int(float(stats.get("Duration (s)", "0.0")))) if stats else "Unknown"
        duration_frame = tk.Frame(info_frame, bg=self.colors['bg_card'])
        duration_frame.pack(fill="x", pady=(0, 8))
        
        tk.Label(
            duration_frame,
            text="⏱",
            font=("Segoe UI", 15),
            bg=self.colors['bg_card'],
            fg=self.colors['accent']
        ).pack(side="left", padx=(0, 8))
        
        tk.Label(
            duration_frame,
            text=f"Duration: {duration}",
            font=("Segoe UI", 14, "bold"),
            bg=self.colors['bg_card'],
            fg=self.colors['text_secondary']
        ).pack(side="left")

        path_label = tk.Label(
            info_frame,
            text=os.path.dirname(self.file_path),
            font=("Segoe UI", 10),
            bg=self.colors['bg_card'],
            fg=self.colors['text_muted'],
            wraplength=500,
            justify="left",
            anchor="w"
        )
        path_label.pack(fill="x")

    def _create_thumbnail(self, parent, screenshots):
        thumb_container = tk.Frame(parent, bg=self.colors['bg_secondary'], relief="flat", bd=0)
        thumb_container.pack()
        
        padding_frame = tk.Frame(thumb_container, bg=self.colors['bg_secondary'])
        padding_frame.pack(padx=3, pady=3)

        if screenshots:
            try:
                img_path = screenshots[0]
                img = Image.open(img_path)
                img.thumbnail((150, 150))
                thumb_img = ImageTk.PhotoImage(img)
                thumb_label = tk.Label(
                    padding_frame, 
                    image=thumb_img, 
                    bg=self.colors['bg_secondary'],
                    relief="flat",
                    bd=0
                )
                thumb_label.image = thumb_img
                thumb_label.pack()
            except Exception:
                self._create_placeholder_thumbnail(padding_frame)
        else:
            self._create_placeholder_thumbnail(padding_frame)

    def _create_placeholder_thumbnail(self, parent):
        placeholder = tk.Frame(parent, bg=self.colors['bg_hover'], width=150, height=150)
        placeholder.pack_propagate(True)
        placeholder.pack()
        
        tk.Label(
            placeholder,
            text="📁",
            font=("Segoe UI", 32),
            bg=self.colors['bg_hover'],
            fg=self.colors['text_muted']
        ).pack(expand=True)

    def _create_scrollable_content(self, parent, stats, screenshots, snippets):
        canvas_frame = tk.Frame(parent, bg=self.colors['bg_primary'])
        canvas_frame.pack(fill="both", expand=True, pady=(0, 20))

        canvas = tk.Canvas(
            canvas_frame, 
            bg=self.colors['bg_primary'], 
            highlightthickness=0,
            relief="flat",
            bd=0
        )
        
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.colors['bg_primary'])

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        content_container = tk.Frame(scroll_frame, bg=self.colors['bg_primary'])
        content_container.pack(fill="both", expand=True)

        left_frame = tk.Frame(content_container, bg=self.colors['bg_primary'], width=400)
        left_frame.pack(side="left", fill="y", expand=True, padx=(0, 10))

        right_frame = tk.Frame(content_container, bg=self.colors['bg_primary'], width=450)
        right_frame.pack(side="right", fill="both", expand=False, padx=(10, 0))

        self._create_categories_section(left_frame)
        self._create_watch_stats_section(left_frame)
        self._create_stats_section(left_frame, stats)
        self._create_description_section(right_frame, stats.get("File Size", 0))
        self._create_notes_section(right_frame)
        self._create_screenshots_section(right_frame, screenshots)
        self._create_snippets_section(right_frame, snippets)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    def _create_description_section(self, parent, size=None):
        content_frame = self._create_section_card(parent, "Description", "ℹ️", self.colors['bg_primary'])
        
        desc_container = tk.Frame(
            content_frame, 
            width=450, 
            bg=self.colors["bg_primary"]
            )
        desc_container.pack(anchor="w", fill="x", pady=(2, 6), padx=10)

        description = self.description_manager.get_description(self.file_path)
        self.file_size = size
        self._desc_var = tk.StringVar(value=description)

        self._desc_label = tk.Label(
            desc_container,
            text=description if description else "Double-click to add a description.",
            font=("Segoe UI", 11, "italic"),
            bg=self.colors['bg_primary'],
            fg=self.colors['text_primary'],
            wraplength=480,
            justify="left",
            anchor="w"
        )
        self._desc_label.pack(anchor="w", pady=(2, 6), fill="x")

        self._desc_entry = tk.Text(
            desc_container,
            height=6,
            font=("Segoe UI", 11),
            wrap="word",
            width=70,
            bg=self.colors['bg_primary'],
            fg=self.colors['text_primary']
        )

        def switch_to_entry(event=None):
            self._desc_label.pack_forget()
            self._desc_entry.delete("1.0", "end")
            self._desc_entry.insert("1.0", self._desc_var.get())
            self._desc_entry.pack(anchor="w", fill="x", pady=(2, 6))
            self._desc_entry.focus_set()

        def save_description(event=None):
            new_desc = self._desc_entry.get("1.0", "end").strip()
            self.description_manager.set_description(self.file_path, self.file_size, new_desc)
            self.description_manager._load_descriptions()
            self._desc_var.set(new_desc)
            self._desc_label.config(
                text=new_desc if new_desc else "Double-click to add a description."
            )
            self._desc_entry.pack_forget()
            self._desc_label.pack(anchor="w", pady=(2, 6), fill="x")

        self._desc_label.bind("<Double-Button-1>", switch_to_entry)
        self._desc_entry.bind("<FocusOut>", save_description)
        self._desc_entry.bind("<Control-Return>", save_description)



    def _create_notes_section(self, parent):
        content_frame = self._create_section_card(parent, "Notes", "📝")
        note_data = self.notes_manager.get_note(self.file_path)
        if note_data:
            note_card = tk.Frame(
                content_frame,
                bg=self.colors['bg_card'],
                bd=0, relief="flat")
            note_card.pack(fill="none", pady=5, padx=5)

            note_text = note_data.get("note", "")
            tk.Label(
                note_card,
                text=f"“{note_text}”" if note_text else "No note.",
                font=("Segoe UI", 11, "italic"),
                bg=self.colors['bg_card'],
                fg=self.colors['text_primary'],
                wraplength=450,
                justify="left",
                anchor="w"
            ).pack(anchor="w", pady=(2, 6))

            mood = note_data.get("mood")
            if mood and mood != "None":
                mood_label = tk.Label(
                    note_card,
                    text=f"Mood: {mood}",
                    font=("Segoe UI", 8, "italic"),
                    bg=self.colors['bg_card'],
                    fg=self.colors['text_secondary'],
                    anchor="e"
                )
                mood_label.place(relx=1.0, y=0, anchor="ne", x=-2)

            tags = note_data.get("tags", [])
            if tags:
                tag_frame = tk.Frame(note_card, bg=self.colors['bg_card'])
                tag_frame.pack(anchor="w", pady=(0, 2), fill="x")
                tag_strs = [f"#{t}" for t in tags]
                max_width = 380
                row = 0
                col = 0
                cur_width = 0
                for tag in tag_strs:
                    tag_lbl = tk.Label(
                        tag_frame,
                        text=tag,
                        font=("Segoe UI", 10, "bold"),
                        bg=self.colors['bg_card'],
                        fg=self.colors['accent'],
                        padx=6, pady=2,
                        relief="flat",
                        bd=0
                    )
                    tag_lbl.update_idletasks()
                    tag_width = tag_lbl.winfo_reqwidth() + 8
                    if cur_width + tag_width > max_width:
                        row += 1
                        col = 0
                        cur_width = 0
                    tag_lbl.grid(row=row, column=col, padx=(0, 4), pady=(0, 2), sticky="w")
                    cur_width += tag_width
                    col += 1

            rating = note_data.get("rating")
            if rating:
                stars = "★" * int(round(float(rating))) + "☆" * (5 - int(round(float(rating))))
                rating_label = tk.Label(
                    note_card,
                    text=f"{stars}",
                    font=("Segoe UI", 11, "bold"),
                    bg=self.colors['bg_card'],
                    fg="#FFD700"
                )
                rating_label.pack(anchor="w", pady=(2, 2))

            timestamp = note_data.get("timestamp")
            if timestamp:
                tk.Label(
                    note_card,
                    text=f"🕒 {timestamp[:19].replace('T', ' ')}",
                    font=("Segoe UI", 8),
                    bg=self.colors['bg_card'],
                    fg=self.colors['text_muted']
                ).pack(anchor="e", pady=(2, 0))
        else:
            tk.Label(
                content_frame,
                text="No notes for this file.",
                font=("Segoe UI", 10, "italic"),
                bg=self.colors['bg_card'],
                fg=self.colors['text_muted']
            ).pack(anchor="w", pady=10)

    def _create_section_card(self, parent, title, icon="", bg_color=None):
        card_frame = tk.Frame(
            parent, 
            bg=self.colors['bg_card'] if not bg_color else bg_color, 
            relief="flat", 
            bd=0
        )
        card_frame.pack(fill="x", pady=(0, 20))

        header_frame = tk.Frame(
            card_frame, 
            bg=self.colors['bg_card'] if not bg_color else bg_color
            )
        header_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        if icon:
            tk.Label(
                header_frame,
                text=icon,
                font=("Segoe UI", 16),
                bg=self.colors['bg_card'] if not bg_color else bg_color,
                fg=self.colors['accent']
            ).pack(side="left", padx=(0, 10))
        
        tk.Label(
            header_frame,
            text=title,
            font=("Segoe UI", 16, "bold"),
            bg=self.colors['bg_card'] if not bg_color else bg_color,
            fg=self.colors['text_primary']
        ).pack(side="left")
        
        separator = tk.Frame(
            card_frame,
            bg=self.colors['border'] if not bg_color else bg_color, 
            height=1)
        separator.pack(fill="x", padx=20)
        
        content_frame = tk.Frame(
            card_frame, 
            bg=self.colors['bg_card'] if not bg_color else bg_color
            )
        content_frame.pack(fill="x", padx=20, pady=(10, 15))
        
        return content_frame

    def _create_stats_section(self, parent, stats):
        content_frame = self._create_section_card(parent, "Video Statistics", "📊")
        
        if stats:
            stats_grid = tk.Frame(content_frame, bg=self.colors['bg_card'])
            stats_grid.pack(fill="x")
            
            row = 0
            for k, v in stats.items():
                if k == "File Path":
                    continue

                if k == "File Size":
                    v = convert_bytes(v)
                
                stat_frame = tk.Frame(stats_grid, bg=self.colors['bg_card'])
                stat_frame.pack(fill="x", pady=2)
                
                tk.Label(
                    stat_frame,
                    text=f"{k}:",
                    font=("Segoe UI", 11, "bold"),
                    bg=self.colors['bg_card'],
                    fg=self.colors['text_secondary'],
                    anchor="w"
                ).pack(side="left", padx=(0, 10))
                
                tk.Label(
                    stat_frame,
                    text=str(v),
                    font=("Segoe UI", 11),
                    bg=self.colors['bg_card'],
                    fg=self.colors['text_primary'],
                    anchor="w",
                    wraplength=200
                ).pack(side="left")
                
                row += 1
        else:
            tk.Label(
                content_frame,
                text="No statistics available",
                font=("Segoe UI", 11),
                bg=self.colors['bg_card'],
                fg=self.colors['text_muted']
            ).pack(anchor="w")

    def _create_screenshots_section(self, parent, screenshots):
        heading = f"Screenshots: {len(screenshots)}" if screenshots else "Screenshots"
        content_frame = self._create_section_card(parent, heading, "🖼️")

        thumbnails_frame = tk.Frame(content_frame, bg=self.colors['bg_card'])
        thumbnails_frame.pack(fill="both", expand=True)

        self._screenshots_images = screenshots
        self._screenshots_loaded_thumbnails = []
        self._screenshots_render_index = 0

        loading_label = tk.Label(
            content_frame,
            text="⏳ Loading thumbnails...",
            font=("Segoe UI", 10),
            bg=self.colors['bg_card'],
            fg=self.colors['text_muted'],
        )

        load_more_btn = tk.Button(
            content_frame,
            text="Load More",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors['accent'],
            fg="white",
            relief="flat",
            padx=10,
            pady=5,
            command=lambda: draw_next_batch()
        )

        def draw_next_batch():
            loading_label.pack(pady=20)
            load_more_btn.config(state="disabled")

            def worker():
                start = self._screenshots_render_index
                end = min(start + 100, len(self._screenshots_images))
                new_thumbnails = []

                for img_path in self._screenshots_images[start:end]:
                    try:
                        if not os.path.exists(img_path):
                            continue
                        with Image.open(img_path) as img:
                            if img.mode in ('RGBA', 'P'):
                                img = img.convert('RGB')
                            img.thumbnail((200, 150), Image.Resampling.LANCZOS)
                            thumb_img = ImageTk.PhotoImage(img.copy())
                            filename = os.path.basename(img_path)
                            if len(filename) > 15:
                                filename = filename[:12] + "..." + filename[-12:]
                            new_thumbnails.append((thumb_img, filename, img_path))
                    except Exception:
                        new_thumbnails.append(("error", os.path.basename(img_path), img_path))

                def update_ui():
                    if not thumbnails_frame.winfo_exists():
                        return
                    
                    loading_label.pack_forget()
                    load_more_btn.config(state="normal")

                    if self._screenshots_render_index == 0 and not new_thumbnails:
                        no_screenshots_frame = tk.Frame(content_frame, bg=self.colors['bg_card'], width=250, height=100)
                        no_screenshots_frame.pack_propagate(False)
                        no_screenshots_frame.pack()
                        tk.Label(
                            no_screenshots_frame,
                            text="📷\nNo screenshots found",
                            font=("Segoe UI", 12),
                            bg=self.colors['bg_card'],
                            fg=self.colors['text_muted'],
                            justify="center"
                        ).pack(expand=True)
                        load_more_btn.pack_forget()
                        return

                    frame_width = thumbnails_frame.winfo_width() or 500
                    thumb_width = 240
                    # print(frame_width // thumb_width)
                    max_cols = max(2, frame_width // thumb_width)
                    total = self._screenshots_render_index
                    row = total // max_cols
                    col = total % max_cols

                    for idx, item in enumerate(new_thumbnails):
                        if item[0] == "error":
                            error_frame = tk.Frame(thumbnails_frame, bg=self.colors['bg_hover'], width=100, height=75)
                            error_frame.grid(row=row, column=col, padx=5, pady=5, sticky="w")
                            error_frame.pack_propagate(False)
                            tk.Label(
                                error_frame,
                                text="❌\nError",
                                font=("Segoe UI", 10),
                                bg=self.colors['bg_hover'],
                                fg=self.colors['text_muted'],
                                justify="center"
                            ).pack(expand=True)
                        else:
                            thumb_img, filename, img_path = item
                            thumb_container = tk.Frame(thumbnails_frame, bg=self.colors['bg_hover'], relief="flat", bd=1)
                            thumb_container.grid(row=row, column=col, padx=5, pady=5, sticky="w")

                            thumb_label = tk.Label(
                                thumb_container,
                                image=thumb_img,
                                bg=self.colors['bg_hover'],
                                relief="flat",
                                bd=0,
                                cursor="hand2"
                            )
                            thumb_label.image = thumb_img
                            thumb_label.pack(padx=3, pady=3)

                            name_label = tk.Label(
                                thumb_container,
                                text=filename,
                                font=("Segoe UI", 8),
                                bg=self.colors['bg_hover'],
                                fg=self.colors['text_secondary'],
                                wraplength=160
                            )
                            name_label.pack(pady=(0, 3))

                            def on_thumb_enter(e, container=thumb_container):
                                container.config(bg=self.colors['accent'])
                                for child in container.winfo_children():
                                    if hasattr(child, 'config'):
                                        child.config(bg=self.colors['accent'])

                            def on_thumb_leave(e, container=thumb_container):
                                container.config(bg=self.colors['bg_hover'])
                                for child in container.winfo_children():
                                    if hasattr(child, 'config'):
                                        child.config(bg=self.colors['bg_hover'])

                            for widget in [thumb_container, thumb_label, name_label]:
                                widget.bind("<Enter>", on_thumb_enter)
                                widget.bind("<Leave>", on_thumb_leave)

                            def open_image_viewer(event, img_idx=total + idx):
                                valid_files = [f for f in self._screenshots_images if os.path.exists(f)]
                                if not valid_files:
                                    messagebox.showerror("No Images", "No valid screenshot files found.")
                                    return
                                try:
                                    viewer_win = tk.Toplevel(self.parent)
                                    viewer_win.configure(bg="black")
                                    viewer_win.focus_force()
                                    viewer_win.grab_set()
                                    parent.grab_release()
                                    ImageViewer(viewer_win, valid_files, index=img_idx, width=1000, height=600)
                                except Exception as ex:
                                    messagebox.showerror("Error", f"Could not open image viewer:\n{ex}")

                            thumb_label.bind("<Button-1>", lambda e, idx=total + idx: open_image_viewer(e, img_idx=idx))

                        col += 1
                        if col >= max_cols:
                            col = 0
                            row += 1

                    self._screenshots_render_index += len(new_thumbnails)
                    self._screenshots_loaded_thumbnails.extend(new_thumbnails)

                    if self._screenshots_render_index >= len(self._screenshots_images):
                        load_more_btn.pack_forget()
                    else:
                        load_more_btn.pack(pady=10)

                thumbnails_frame.after(100, update_ui)

            threading.Thread(target=worker, daemon=True).start()

        if screenshots:
            draw_next_batch()
        else:
            no_screenshots_frame = tk.Frame(content_frame, bg=self.colors['bg_card'], width=250, height=100)
            no_screenshots_frame.pack_propagate(False)
            no_screenshots_frame.pack()
            tk.Label(
                no_screenshots_frame,
                text="📷\nNo screenshots found",
                font=("Segoe UI", 12),
                bg=self.colors['bg_card'],
                fg=self.colors['text_muted'],
                justify="center"
            ).pack(expand=True)

    def _create_snippets_section(self, parent, snippets):
        content_frame = self._create_section_card(parent, "Video Snippets", "✂️")
        display_keys = ["Output File", "Total Duration (s)", "Trim Mode", "File Size (MB)", "Notes"]

        if snippets:
            snippet_files = [snip.get("Output File", "") for snip in snippets if snip.get("Output File", "")]
            video_files = snippet_files
            all_files = list(dict.fromkeys(snippet_files + video_files))

            for i, snip in enumerate(snippets):
                snippet_card = tk.Frame(content_frame, bg=self.colors['bg_hover'])
                snippet_card.pack(fill="x", pady=3)

                snippet_content = tk.Frame(snippet_card, bg=self.colors['bg_hover'])
                snippet_content.pack(fill="x", padx=15, pady=10)
                tk.Label(
                    snippet_content,
                    text=f"Snippet {i+1}",
                    font=("Segoe UI", 10, "bold"),
                    bg=self.colors['bg_hover'],
                    fg=self.colors['accent']
                ).pack(anchor="w")

                for k in display_keys:
                    v = seconds_to_hhmmss(float(snip.get(k, "0.0"))) if k == "Total Duration (s)" else snip.get(k, "")
                    if k == "Output File":
                        v = os.path.basename(v)
                    detail_text = f"{k}: {v}"
                    tk.Label(
                        snippet_content,
                        text=detail_text,
                        font=("Segoe UI", 10),
                        bg=self.colors['bg_hover'],
                        fg=self.colors['text_secondary'],
                        wraplength=400,
                        justify="left",
                        anchor="w"
                    ).pack(anchor="w", pady=1)

                def open_snippet(event=None, output_file=snip.get("Output File", "")):
                    if not output_file or not os.path.exists(output_file):
                        messagebox.showerror("File Not Found", "Snippet output file does not exist.")
                        return
                    try:
                        idx = video_files.index(output_file)
                    except ValueError:
                        idx = 0
                    try:
                        parent.grab_release()
                        app = MediaPlayerApp(
                            parent=parent, 
                            video_files=video_files, 
                            current_file=output_file, 
                            random_select=False,
                            favorites_manager = self.favorites_manager,
                            category_manager=self.category_manager,
                            notes_manager=self.notes_manager,
                        )
                        app.update_video_progress()
                        app.lift()
                        app.focus_force()
                        app.mainloop()
                    except Exception as ex:
                        messagebox.showerror("Error", f"Could not open video player:\n{ex}")

                snippet_card.bind("<Button-1>", open_snippet)
                snippet_content.bind("<Button-1>", open_snippet)

                def on_enter(event=None, card=snippet_card, content=snippet_content):
                    card.config(bg=self.colors['bg_primary'])
                    content.config(bg=self.colors['bg_primary'])
                    for child in content.winfo_children():
                        child.config(bg=self.colors['bg_secondary'], cursor="hand2")

                def on_leave(event=None, card=snippet_card, content=snippet_content):
                    card.config(bg=self.colors['bg_hover'])
                    content.config(bg=self.colors['bg_hover'])
                    for child in content.winfo_children():
                        child.config(bg=self.colors['bg_hover'], cursor="arrow")

                for widget in [snippet_card, snippet_content]:
                    widget.bind("<Enter>", on_enter)
                    widget.bind("<Leave>", on_leave)

        else:
            tk.Label(
                content_frame,
                text="No snippets found",
                font=("Segoe UI", 11),
                bg=self.colors['bg_card'],
                fg=self.colors['text_muted']
            ).pack(anchor="w")

    def _create_categories_section(self, parent):
        content_frame = self._create_section_card(parent, "Categories", "🏷️")
        categories = self.category_manager.get_file_categories(self.file_path)
        is_favorite = self.favorites_manager.check_favorites(self.file_path)
        if categories or is_favorite:
            if is_favorite:
                fav_label = tk.Label(
                    content_frame,
                    text="Favorites",
                    font=("Segoe UI", 10, "bold"),
                    bg="black",
                    fg="#FFC107",
                    padx=8,
                    pady=4,
                    relief="flat",
                    bd=0
                )
                fav_label.pack(anchor="w", pady=2, padx=4)

            for cat in categories:
                cat_label = tk.Label(
                    content_frame,
                    text=cat,
                    font=("Segoe UI", 10, "bold"),
                    bg=self.colors['bg_hover'],
                    fg=self.colors['accent'],
                    padx=8,
                    pady=4,
                    relief="flat",
                    bd=0
                )
                cat_label.pack(anchor="w", pady=2, padx=4)
        else:
            tk.Label(
                content_frame,
                text="No categories assigned",
                font=("Segoe UI", 10),
                bg=self.colors['bg_card'],
                fg=self.colors['text_muted']
            ).pack(anchor="w")

    def _create_watch_stats_section(self, parent):
        content_frame = self._create_section_card(parent, "Watch Stats", "👁️")
        loading_label = tk.Label(
            content_frame,
            text="Loading...",
            font=("Segoe UI", 10),
            bg=self.colors['bg_card'],
            fg=self.colors['text_muted']
        )
        loading_label.pack(anchor="w")

        def update_stats():
            related_paths = get_all_related_paths(self.file_path)
            stats = get_watch_stats_for_filenames(related_paths)
            def update_ui():
                if not content_frame.winfo_exists():
                    return
                loading_label.destroy()
                tk.Label(
                    content_frame,
                    text=f"Times Watched: {stats['watch_count']}",
                    font=("Segoe UI", 10, "bold"),
                    bg=self.colors['bg_card'],
                    fg=self.colors['text_primary']
                ).pack(anchor="w", pady=1)
                tk.Label(
                    content_frame,
                    text=f"Total Duration Watched: {seconds_to_hhmmss(stats['total_seconds'])}",
                    font=("Segoe UI", 10),
                    bg=self.colors['bg_card'],
                    fg=self.colors['text_secondary']
                ).pack(anchor="w", pady=1)
                tk.Label(
                    content_frame,
                    text=f"Last Watched: {stats['last_watched']}",
                    font=("Segoe UI", 10),
                    bg=self.colors['bg_card'],
                    fg=self.colors['text_secondary']
                ).pack(anchor="w", pady=1)

                if len(related_paths) > 1:
                    tk.Label(
                        content_frame,
                        text="Related File Paths:",
                        font=("Segoe UI", 10, "bold"),
                        bg=self.colors['bg_card'],
                        fg=self.colors['accent']
                    ).pack(anchor="w", pady=(4, 1))
                    for p in related_paths:
                        tk.Label(
                            content_frame,
                            text=f"> {p}",
                            font=("Segoe UI", 8),
                            bg=self.colors['bg_card'],
                            fg=self.colors['text_muted'],
                            wraplength=250,
                            justify="left"
                        ).pack(anchor="w", pady=1)

                    tk.Label(content_frame, text="", bg=self.colors['bg_card']).pack()
                
            if content_frame.winfo_exists():
                content_frame.after(0, update_ui)

        threading.Thread(target=update_stats, daemon=True).start()

    def _bind_window_events(self):
        """Bind window events for better UX"""
        # ESC key to close
        self.bind('<Escape>', lambda e: self._close_window())
        self.focus_set()

    def _get_video_stats(self):
        try:
            with open(VIDEO_STATS_CSV, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if normalise_path(row.get("File Path", "")) == normalise_path(self.file_path):
                        return row
        except Exception:
            return {}
        return {}

    def _get_video_snippets(self):
        snippets = []
        try:
            file_paths = set(
                filter(
                    None,
                    [normalise_path(p) for p in get_file_transfer_history(self.file_path).values() if p is not None]
                )
            )
            with open(SNIPPETS_HISTORY_CSV, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    original_file = normalise_path(row.get("Original File", ""))
                    if original_file in file_paths:
                        snippets.append(row)
        except Exception as e:
            print(f"Error getting video snippets: {e}")
            pass
        return snippets

    def _center_window(self, window, width, height):
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x_coordinate = (screen_width - width) // 2
        y_coordinate = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x_coordinate}+{y_coordinate}")

    # def _close_window(self, window):
    #     def do_close():
    #         if hasattr(self, '_desc_entry') and self._desc_entry is not None:
    #             try:
    #                 new_desc = self._desc_entry.get("1.0", "end").strip()
    #                 self.description_manager.set_description(self.file_path, self.file_size, new_desc)
    #             except Exception:
    #                 pass
    #         window.unbind_all("<MouseWheel>")
    #         window.destroy()
    #     window.after(0, do_close)
    def _close_window(self):
        def do_close():
            if hasattr(self, '_desc_entry') and self._desc_entry is not None:
                try:
                    new_desc = self._desc_entry.get("1.0", "end").strip()
                    self.description_manager.set_description(self.file_path, self.file_size, new_desc)
                except Exception:
                    pass
            self.unbind_all("<MouseWheel>")
            self.destroy()

        # Always schedule cleanup in the main loop
        self.after(0, do_close)