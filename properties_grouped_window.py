from datetime import datetime
import os
import csv
import random
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image, ImageTk
from typing import List
import threading
import traceback

from annotations_manager import AnnotationsManager
from associations_manager import FileAssociator
from custom_messagebox import showerror
from player_constants import Colors
from static_methods import (
    convert_bytes,
    get_screenshots_for_file_from_index,
    get_screenshots_for_files_from_index,
    natural_sort_iterables,
    normalise_path,
    seconds_to_hhmmss,
    build_screenshot_index,
    build_transfer_graph,
    get_all_related_paths_multiple
)
from image_player import ImageViewer
from favorites_manager import FavoritesManager
from category_manager import CategoryManager
from notes_manager import NotesManager
from description_manager import DescriptionManager
from stats_manager import VideoStatsManager
from snippets_manager import SnippetsManager
from fingerprint_manager import MediaFingerprintManager
from deletion_manager import DeletionManager
from watch_history_logger import WatchHistoryLogger
from tooltips import ToolTip
from mixins import ResetMixin

class GroupedPropertiesWindow(tk.Toplevel, ResetMixin):
    def __init__(self, parent, file_paths: List[str] = None, category_name: str = None,
                 category_manager=None, favorites_manager=None, notes_manager=None,
                 description_manager=None, deletion_manager=None, snippets_manager=None,
                 stats_manager=None, association_manager=None, fingerprint_manager=None,
                 annotations_manager=None, trimmed_segments=None, trimmed_segments_metadata=None,
                 watch_history_logger=None):
        super().__init__(parent)
        self.withdraw()
        self.parent = parent
        self.file_paths = list(set([normalise_path(fp) for fp in (file_paths or [])]))
        self.all_related_file_paths = get_all_related_paths_multiple(self.file_paths)
        self.category_name = category_name
        
        self.fingerprint_manager = fingerprint_manager or MediaFingerprintManager()
        self.category_manager = category_manager or CategoryManager(fingerprint_manager=self.fingerprint_manager)
        self.favorites_manager = favorites_manager or FavoritesManager(fingerprint_manager=self.fingerprint_manager)
        self.notes_manager = notes_manager or NotesManager(fingerprint_manager=self.fingerprint_manager)
        self.deletion_manager = deletion_manager or DeletionManager(fav_manager=self.favorites_manager)
        self.association_manager = association_manager or FileAssociator(deletion_manager=self.deletion_manager,
                                                                         fingerprint_manager=self.fingerprint_manager)
        self.description_manager = description_manager or DescriptionManager(association_manager=self.association_manager,
                                                                              fingerprint_manager=self.fingerprint_manager)
        self.snippets_manager = snippets_manager or SnippetsManager(deletion_manager=self.deletion_manager,
                                                                    association_manager=self.association_manager,
                                                                    fingerprint_manager=self.fingerprint_manager)
        self.stats_manager = stats_manager or VideoStatsManager(snippets_manager=self.snippets_manager,
                                                                deletion_manager=self.deletion_manager)
        self.annotations_manager = annotations_manager or AnnotationsManager(fingerprint_manager=self.fingerprint_manager)

        self.trimmed_segments = trimmed_segments or {}
        self.trimmed_segments_metadata = trimmed_segments_metadata or {}
        self.watch_history_logger = watch_history_logger or WatchHistoryLogger(fingerprint_manager=self.fingerprint_manager)
        
        self._setup_styles()
        self._setup_window()
        self.grouped_data = {}
        self.protocol("WM_DELETE_WINDOW", self._close_window)
        

    def _setup_styles(self):
        self.colors = {
            'bg_primary': Colors.PLAIN_BLACK,
            'bg_secondary': '#1A1F26',
            'bg_card': '#252B35',
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

    def _setup_window(self):
        title = f"(Beta) Group Properties - {self.category_name}" if self.category_name else f"Group Properties - {len(self.file_paths)} Files"
        self.title(title)
        self.geometry("1200x650")
        self.minsize(900, 500)
        self.configure(bg=self.colors['bg_primary'])
        self.transient(self.parent)
        self._center_window(self, 1200, 650)

    def preload_properties(self):
        """Preload all grouped properties data"""
        try:
            self._preload_grouped_data()
            return True
        except Exception as e:
            print(f"Error preloading grouped properties: {e}")
            import traceback
            traceback.print_exc()
            return False

    def show_properties(self):
        """Show the properties window with preloaded data"""
        if self.grouped_data:
            self._build_ui()
            self.deiconify()
        else:
            self._handle_error("No data to display")

    def _preload_grouped_data(self):
        """Aggregate all data from multiple files"""
        total_files = len(self.file_paths)
        total_related_files = len(self.all_related_file_paths)
        total_size = 0
        total_duration = 0.0
        favorite_count = 0
        files_with_notes = 0
        all_categories = set()
        all_stats = []
        all_snippets = []
        all_screenshots = []
        all_annotations = []
        watch_stats_agg = {"total_views": 0, "total_duration": 0, "last_watched": None}
        
        print("Building screenshot index for grouped properties...")
        screenshot_index = build_screenshot_index()
        print("Retriving screenshots for files")
        all_screenshots = get_screenshots_for_files_from_index(self.file_paths, screenshot_index)
        print("Retrieved screenshots")

        if self.watch_history_logger:

            print("Building watch history stats index for grouped properties...")
            self.watch_history_logger.build_fingerprint_stats_index()

            print("Retrieving batch watch history stats for grouped properties...")
            # watch_stats_by_path = self.watch_history_logger.get_watch_stats_for_file_paths_batch(self.file_paths)
            watch_stats_agg = self.watch_history_logger.get_watch_stats_for_file_paths_batch(self.file_paths, aggregate=True)
        
        print("Building category files mapping")
        categories = self.category_manager.get_categories_with_files_for_paths(self.file_paths)
        total_categories = sum(len(v) for v in categories.values() if isinstance(v, list))
        all_categories = set(categories.keys())

        print("Retrieving notes for files...")
        all_file_notes = self.notes_manager.get_notes_for_files(self.file_paths, skip_empty=True)
        print(len(all_file_notes))
        files_with_notes = len(all_file_notes)

        print("Retrieving snippets for files")
        all_file_snippets = self.snippets_manager.get_snippets_for_files(self.file_paths)
        print(len(all_file_snippets))

        for file_path in self.file_paths:
            try:
                try:
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                except Exception:
                    pass
                
                try:
                    is_fav = self.favorites_manager.check_favorites(file_path)
                    if is_fav:
                        favorite_count += 1
                except Exception:
                    pass

                try:
                    stats = self.stats_manager.get_stat(file_path, str(file_size))
                    if stats:
                        all_stats.append(stats)
                        try:
                            dur = float(stats.get("Duration (s)", 0))
                            total_duration += dur
                        except Exception:
                            pass
                except Exception:
                    pass
                
                try:
                    annotations = self.annotations_manager.get_annotations_for_file(file_path)
                    if annotations:
                        for annot in annotations:
                            annot['_source_file'] = os.path.basename(file_path)
                            all_annotations.append(annot)
                except Exception:
                    pass
                
            except Exception as e:
                continue
        
        all_screenshots = list(set(all_screenshots))
        shuffled_screenshots = all_screenshots

        random.shuffle(shuffled_screenshots)

        self.grouped_data = {
            "total_files": total_files,
            "total_related_files": total_related_files,
            "total_size": total_size,
            "total_duration": total_duration,
            "favorite_count": favorite_count,
            "files_with_notes": files_with_notes,
            "all_file_notes": all_file_notes,
            "categories": sorted(list(all_categories), key=lambda x: len(natural_sort_iterables(x)), reverse=True),
            "category_files": categories,
            "total_categories": total_categories,
            "stats": all_stats,
            "screenshots": natural_sort_iterables(all_screenshots),
            "shuffled_screenshots": shuffled_screenshots,
            "snippets": all_file_snippets,
            "annotations": all_annotations,
            "watch_count": watch_stats_agg["total_views"],
            "watch_total_seconds": watch_stats_agg["total_duration"],
            "last_watched_date": watch_stats_agg["last_watched"],
            "last_watched_file": watch_stats_agg.get("last_watched_file", "No Last Watched File")
        }
    
    def _get_defaults(self):
        return {
            "grouped_data": {},
            "file_paths": [],

        }

    def _build_ui(self):
        """Build the UI"""
        if not self.grouped_data:
            self._handle_error("Failed to load grouped data")
            return
        
        main_container = tk.Frame(self, bg=self.colors['bg_primary'])
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        self._create_header_section(main_container)
        
        self._create_scrollable_content(main_container)
        self._bind_window_events()

    def _create_thumbnail(self, parent):
        screenshots = self.grouped_data["shuffled_screenshots"]
        thumb_container = tk.Frame(parent, bg=self.colors['bg_secondary'], relief="flat", bd=0)
        thumb_container.pack()
        
        padding_frame = tk.Frame(thumb_container, bg=self.colors['bg_secondary'])
        padding_frame.pack(padx=3, pady=3)

        if screenshots:
            try:
                img_path = screenshots[0]
                img = Image.open(img_path)
                img.thumbnail((300, 250))
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
        placeholder = tk.Frame(parent, bg=self.colors['bg_hover'], width=250, height=200)
        placeholder.pack_propagate(True)
        placeholder.pack()
        
        tk.Label(
            placeholder,
            text="📁",
            font=("Segoe UI", 32),
            bg=self.colors['bg_hover'],
            fg=self.colors['text_muted']
        ).pack(expand=True)

    def _create_header_section(self, parent):
        """Create enhanced header with visual appeal"""
        header_frame = tk.Frame(parent, bg=self.colors['bg_card'], relief="flat", bd=0)
        header_frame.pack(fill="x", pady=(0, 15))
        
        border_top = tk.Frame(header_frame, bg=self.colors['accent'], height=3)
        border_top.pack(fill="x")
        
        
        content = tk.Frame(header_frame, bg=self.colors['bg_card'])
        content.pack(fill="x", padx=20, pady=15)

        thumb_frame = tk.Frame(content, bg=self.colors['bg_card'])
        thumb_frame.pack(side="left", padx=(0, 20))

        self._create_thumbnail(thumb_frame)
        
        title_text = f"📂 {self.category_name}" if self.category_name else "📊 Group Properties"
        title_label = tk.Label(content, text=title_text, font=("Segoe UI", 28, "bold"),
                bg=self.colors['bg_card'], fg=self.colors['text_primary'])
        title_label.pack(anchor="w", pady=(0, 10))
        
        file_count_text = f"{self.grouped_data['total_files']} file{'s' if self.grouped_data['total_files'] != 1 else ''} in this group"
        subtitle_label = tk.Label(content, text=file_count_text, font=("Segoe UI", 10),
                bg=self.colors['bg_card'], fg=self.colors['text_secondary'])
        subtitle_label.pack(anchor="w")

    def _create_scrollable_content(self, parent):
        """Create scrollable content area"""
        canvas_frame = tk.Frame(parent, bg=self.colors['bg_primary'])
        canvas_frame.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(canvas_frame, bg=self.colors['bg_primary'], highlightthickness=0, relief="flat", bd=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.colors['bg_primary'])
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        content_container = tk.Frame(scroll_frame, bg=self.colors['bg_primary'])
        content_container.pack(fill="both", expand=True)
        
        left_frame = tk.Frame(content_container, bg=self.colors['bg_primary'], width=400)
        left_frame.pack(side="left", fill="y", expand=False, padx=(0, 10))
        
        right_frame = tk.Frame(content_container, bg=self.colors['bg_primary'])
        right_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        self._create_summary_stats_section(left_frame)
        self._create_categories_section(left_frame)
        self._create_statistics_section(left_frame)
        self._create_codec_breakdown_section(left_frame)
        self._create_annotations_section(left_frame)
        self._create_file_list_section(left_frame)
        
        self._create_descriptions_section(right_frame)
        self._create_screenshots_section(right_frame)
        self._create_notes_section(right_frame)
        self._create_snippets_section(right_frame)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

    def _create_categories_section(self, parent):
        """Display categories with hover tooltips showing file counts"""
        
        content_frame = self._create_section_card(parent, "Categories", "🏷️")
        
        category_files = self.grouped_data.get('category_files', {})
        
        if self.grouped_data['categories']:
            for category in self.grouped_data['categories']:
                category_frame = tk.Frame(content_frame, bg=self.colors['bg_hover'])
                category_frame.pack(anchor="w", pady=2, padx=4, fill="x")
                
                files_list = category_files.get(category, [])
                file_count = len(files_list)
                
                category_label = tk.Label(
                    category_frame,
                    text=f"{category} ({file_count})",
                    font=("Segoe UI", 10, "bold"),
                    bg=self.colors['bg_hover'],
                    fg=self.colors['accent'],
                    padx=8,
                    pady=4,
                    relief="flat",
                    bd=0,
                    cursor="hand2"
                )
                category_label.pack(fill="x")
                
                files_tooltip = f"Category: {category}\n\nFiles ({file_count}):\n"
                files_tooltip += "\n".join(f"  • {os.path.basename(f)}" for f in files_list[:10])
                if len(files_list) > 6:
                    files_tooltip += f"\n  ... +{len(files_list) - 10} more"
                
                ToolTip(category_label, files_tooltip, wraplength=350)
            
            if self.grouped_data['favorite_count'] > 0:
                fav_frame = tk.Frame(content_frame, bg="black")
                fav_frame.pack(anchor="w", pady=2, padx=4, fill="x")
                
                fav_label = tk.Label(
                    fav_frame,
                    text=f"⭐ {self.grouped_data['favorite_count']} Favorites",
                    font=("Segoe UI", 10, "bold"),
                    bg="black",
                    fg="#FFC107",
                    padx=8,
                    pady=4,
                    relief="flat",
                    bd=0,
                    cursor="hand2"
                )
                fav_label.pack(fill="x")
                
                fav_tooltip = f"Favorite Files ({self.grouped_data['favorite_count']})"
                ToolTip(fav_label, fav_tooltip, wraplength=250)
        else:
            tk.Label(
                content_frame,
                text="No categories assigned",
                font=("Segoe UI", 10, "italic"),
                bg=self.colors['bg_card'],
                fg=self.colors['text_muted']
            ).pack(anchor="w", pady=10)

    def _create_statistics_section(self, parent):
        """Display statistics"""
        content_frame = self._create_section_card(parent, "Statistics", "📊")
        
        if self.grouped_data['stats']:
            stats_summary = {
                "avg_bitrate": 0.0, 
                "avg_fps": 0.0, 
                "avg_resolution": {"width": 0, "height": 0},
                "count": len(self.grouped_data['stats']), 
                "formats": set(),
                "total_size": 0
            }
            
            for stat in self.grouped_data['stats']:
                try:
                    stats_summary["avg_bitrate"] += float(stat.get("Bitrate (kbps)", 0))
                    stats_summary["avg_fps"] += float(stat.get("FPS", 0))
                    width = float(stat.get("Width", 0))
                    height = float(stat.get("Height", 0))
                    stats_summary["avg_resolution"]["width"] += width
                    stats_summary["avg_resolution"]["height"] += height
                    codec = stat.get("Video Codec", "Unknown")
                    if codec:
                        stats_summary["formats"].add(codec)
                    size = float(stat.get("File Size", 0))
                    stats_summary["total_size"] += size
                except:
                    pass
            
            if stats_summary["count"] > 0:
                stats_summary["avg_bitrate"] /= stats_summary["count"]
                stats_summary["avg_fps"] /= stats_summary["count"]
                stats_summary["avg_resolution"]["width"] /= stats_summary["count"]
                stats_summary["avg_resolution"]["height"] /= stats_summary["count"]
                avg_file_size = stats_summary["total_size"] / stats_summary["count"]
            else:
                avg_file_size = 0
            
            for label, value in [
                ("Avg Bitrate", f"{stats_summary['avg_bitrate']:.0f} kbps"),
                ("Avg FPS", f"{stats_summary['avg_fps']:.1f}"),
                ("Avg Resolution", f"{int(stats_summary['avg_resolution']['width'])}×{int(stats_summary['avg_resolution']['height'])}"),
                ("Avg File Size", convert_bytes(int(avg_file_size)))
            ]:
                item_frame = tk.Frame(content_frame, bg=self.colors['bg_card'])
                item_frame.pack(fill="x", pady=5)
                tk.Label(item_frame, text=label, font=("Segoe UI", 10), bg=self.colors['bg_card'],
                        fg=self.colors['text_secondary']).pack(side="left")
                tk.Label(item_frame, text=value, font=("Segoe UI", 10, "bold"), bg=self.colors['bg_card'],
                        fg=self.colors['accent']).pack(side="right")
        else:
            tk.Label(content_frame, text="No statistics available", font=("Segoe UI", 10, "italic"),
                    bg=self.colors['bg_card'], fg=self.colors['text_muted']).pack(anchor="w", pady=10)

    def _create_codec_breakdown_section(self, parent):
        """Display codec breakdown"""
        codec_map = {}
        container_map = {}
        
        for stat in self.grouped_data['stats']:
            try:
                codec = stat.get("Video Codec", "Unknown")
                container = stat.get("Container Format", "Unknown")
                key = f"{codec} ({container})"
                codec_map[key] = codec_map.get(key, 0) + 1
                container_map[container] = container_map.get(container, 0) + 1
            except:
                pass
        
        if codec_map or container_map:
            content_frame = self._create_section_card(parent, "Format Breakdown", "🎬")
            
            if codec_map:
                tk.Label(content_frame, text="Codecs:", font=("Segoe UI", 10, "bold"),
                        bg=self.colors['bg_card'], fg=self.colors['accent']).pack(anchor="w", pady=(5, 3))
                for codec_key, count in sorted(codec_map.items(), key=lambda x: x[1], reverse=True)[:5]:
                    codec_frame = tk.Frame(content_frame, bg=self.colors['bg_card'])
                    codec_frame.pack(fill="x", pady=1, padx=10)
                    tk.Label(codec_frame, text=codec_key, font=("Segoe UI", 9),
                            bg=self.colors['bg_card'], fg=self.colors['text_secondary']).pack(side="left")
                    tk.Label(codec_frame, text=f"×{count}", font=("Segoe UI", 9, "bold"),
                            bg=self.colors['bg_card'], fg=self.colors['accent']).pack(side="right")
            
            if container_map:
                tk.Label(content_frame, text="Containers:", font=("Segoe UI", 10, "bold"),
                        bg=self.colors['bg_card'], fg=self.colors['accent']).pack(anchor="w", pady=(8, 3))
                for container, count in sorted(container_map.items(), key=lambda x: x[1], reverse=True)[:5]:
                    cont_frame = tk.Frame(content_frame, bg=self.colors['bg_card'])
                    cont_frame.pack(fill="x", pady=1, padx=10)
                    tk.Label(cont_frame, text=container, font=("Segoe UI", 9),
                            bg=self.colors['bg_card'], fg=self.colors['text_secondary']).pack(side="left")
                    tk.Label(cont_frame, text=f"×{count}", font=("Segoe UI", 9, "bold"),
                            bg=self.colors['bg_card'], fg=self.colors['accent']).pack(side="right")

    def _create_descriptions_section(self, parent):
        """Display descriptions"""
        content_frame = self._create_section_card(parent, "Descriptions", "ℹ️")
        
        descriptions_found = 0
        for file_path in self.file_paths[:5]:
            try:
                desc = self.description_manager.get_description(file_path)
                if desc:
                    descriptions_found += 1
                    desc_frame = tk.Frame(content_frame, bg=self.colors['bg_hover'], relief="flat", bd=0)
                    desc_frame.pack(fill="x", pady=4, padx=3)
                    
                    file_name = os.path.basename(file_path)
                    tk.Label(desc_frame, text=file_name, font=("Segoe UI", 9, "bold"),
                            bg=self.colors['bg_hover'], fg=self.colors['accent'], wraplength=350).pack(anchor="w", padx=5, pady=(5, 2))
                    
                    desc_preview = desc[:120] + "..." if len(desc) > 120 else desc
                    tk.Label(desc_frame, text=desc_preview, font=("Segoe UI", 9), bg=self.colors['bg_hover'],
                            fg=self.colors['text_secondary'], wraplength=350, justify="left", anchor="w").pack(anchor="w", padx=5, pady=(2, 5))
            except:
                pass
        
        if descriptions_found == 0:
            tk.Label(content_frame, text="No descriptions available", font=("Segoe UI", 10, "italic"),
                    bg=self.colors['bg_card'], fg=self.colors['text_muted']).pack(anchor="w", pady=10)

    def _create_notes_section(self, parent):
        """Display notes"""
        content_frame = self._create_section_card(parent, "Notes", "📝")
        
        notes_found = 0
        for file_path in self.file_paths[:4]:
            try:
                note_data = self.notes_manager.get_note(file_path)
                if note_data:
                    notes_found += 1
                    note_frame = tk.Frame(content_frame, bg=self.colors['bg_hover'], relief="flat", bd=0)
                    note_frame.pack(fill="x", pady=4, padx=3)
                    
                    file_name = os.path.basename(file_path)
                    tk.Label(note_frame, text=file_name, font=("Segoe UI", 9, "bold"),
                            bg=self.colors['bg_hover'], fg=self.colors['accent'],
                            wraplength=350).pack(anchor="w", padx=5, pady=(5, 2))
                    
                    note_text = note_data.get("note", "")
                    note_preview = note_text[:100] + "..." if len(note_text) > 100 else note_text
                    tk.Label(note_frame, text=note_preview, font=("Segoe UI", 9, "italic"),
                            bg=self.colors['bg_hover'], fg=self.colors['text_secondary'],
                            wraplength=350, justify="left", anchor="w").pack(anchor="w", padx=5, pady=(2, 5))
            except:
                pass
        
        if notes_found == 0:
            tk.Label(content_frame, text="No notes available", font=("Segoe UI", 10, "italic"),
                    bg=self.colors['bg_card'], fg=self.colors['text_muted']).pack(anchor="w", pady=10)

    def _create_annotations_section(self, parent):
        """Display annotations"""
        if not self.grouped_data['annotations']:
            return
        
        heading = f"Annotations ({len(self.grouped_data['annotations'])})"
        content_frame = self._create_section_card(parent, heading, "📌")
        
        for annotation in self.grouped_data['annotations'][:5]:
            annotation_frame = tk.Frame(content_frame, bg=self.colors['bg_secondary'], relief="flat", bd=1)
            annotation_frame.pack(fill="x", pady=3, padx=3)
            
            header_frame = tk.Frame(annotation_frame, bg=self.colors['bg_secondary'])
            header_frame.pack(fill="x", padx=3, pady=(5, 2))
            
            timestamp = annotation.get("timestamp_seconds", 0)
            timestamp_str = seconds_to_hhmmss(int(timestamp))
            source_file = annotation.get('_source_file', 'Unknown')
            
            tk.Label(
                header_frame,
                text=f"⏱ {timestamp_str}",
                font=("Segoe UI", 9, "bold"),
                bg=self.colors['bg_secondary'],
                fg=self.colors['accent']
            ).pack(side="left", padx=(0, 5))

            tk.Label(
                annotation_frame,
                text=f"From: {source_file}",
                font=("Segoe UI", 8),
                bg=self.colors['bg_secondary'],
                fg=self.colors['text_secondary'],
                wraplength=250,
                anchor="w",
                justify="left"
            ).pack(fill="x", padx=3, pady=(0, 2))
            
            annot_text = annotation.get("annotation_text", "")
            annot_preview = annot_text[:100] + "..." if len(annot_text) > 100 else annot_text
            
            tk.Label(
                annotation_frame,
                text=annot_preview,
                font=("Segoe UI", 9),
                bg=self.colors['bg_secondary'],
                fg=self.colors['text_secondary'],
                justify="left",
                anchor="w",
                wraplength=250
            ).pack(fill="both", expand=True, padx=3, pady=(0, 5))

    def _create_snippets_section(self, parent):
        """Display snippets with detailed info and clickable functionality"""
        if not self.grouped_data['snippets']:
            return
        
        heading = f"Video Snippets ({len(self.grouped_data['snippets'])})"
        content_frame = self._create_section_card(parent, heading, "✂️")
        
        display_keys = ["Output File", "Total Duration (s)", "Trim Mode", "File Size (MB)", "Notes"]
        all_snippets = [snip.get("Output File", "Unknown") for snip in self.grouped_data['snippets']]
        
        for i, snip in enumerate(self.grouped_data['snippets'][:6], 1):
        # for i, snip in enumerate(self.grouped_data['snippets'], 1):
            snippet_card = tk.Frame(content_frame, bg=self.colors['bg_secondary'], relief="solid", bd=1)
            snippet_card.pack(fill="x", pady=5, padx=2)
            
            header_frame = tk.Frame(snippet_card, bg=self.colors['bg_secondary'])
            header_frame.pack(fill="x", padx=10, pady=(8, 5))
            
            output_file = snip.get('Output File', 'Unknown')
            file_name = os.path.basename(output_file)
            
            title_label = tk.Label(header_frame, text=f"Snippet {i}: {file_name}", font=("Segoe UI", 10, "bold"),
                    bg=self.colors['bg_secondary'], fg=self.colors['accent'], wraplength=400, justify="left", anchor="w")
            title_label.pack(side="left", anchor="w")
            
            
            content_inner = tk.Frame(snippet_card, bg=self.colors['bg_secondary'])
            content_inner.pack(fill="x", padx=10, pady=(0, 8))
            
            # Duration and Mode
            duration = snip.get("Total Duration (s)", "0")
            try:
                duration_str = seconds_to_hhmmss(int(float(duration)))
            except:
                duration_str = duration
            
            mode = snip.get("Trim Mode", "Unknown")
            
            info_frame = tk.Frame(content_inner, bg=self.colors['bg_secondary'])
            info_frame.pack(fill="x", pady=3)
            
            tk.Label(info_frame, text="⏱ Duration:", font=("Segoe UI", 9),
                    bg=self.colors['bg_secondary'], fg=self.colors['text_secondary']).pack(side="left")
            tk.Label(info_frame, text=duration_str, font=("Segoe UI", 9, "bold"),
                    bg=self.colors['bg_secondary'], fg=self.colors['accent']).pack(side="left", padx=(5, 15))
            
            tk.Label(info_frame, text="📝 Mode:", font=("Segoe UI", 9),
                    bg=self.colors['bg_secondary'], fg=self.colors['text_secondary']).pack(side="left")
            tk.Label(info_frame, text=mode, font=("Segoe UI", 9, "bold"),
                    bg=self.colors['bg_secondary'], fg=self.colors['accent']).pack(side="left", padx=(5, 0))
            file_size = snip.get("File Size (MB)", "0")
            tk.Label(info_frame, text="💾 Size:", font=("Segoe UI", 9),
                    bg=self.colors['bg_secondary'], fg=self.colors['text_secondary']).pack(side="left")
            tk.Label(info_frame, text=f"{file_size} MB", font=("Segoe UI", 9, "bold"),
                    bg=self.colors['bg_secondary'], fg=self.colors['accent']).pack(side="left", padx=(5, 0))
            
            notes = snip.get("Notes", "")
            if notes:
                notes_frame = tk.Frame(content_inner, bg=self.colors['bg_secondary'])
                notes_frame.pack(fill="x", pady=3)
                notes_text = notes[:80] + "..." if len(notes) > 80 else notes
                tk.Label(notes_frame, text=f"📌 {notes_text}", font=("Segoe UI", 8, "italic"),
                        bg=self.colors['bg_secondary'], fg=self.colors['text_secondary'],
                        wraplength=320, justify="left", anchor="w").pack(anchor="w")
            
            button_frame = tk.Frame(snippet_card, bg=self.colors['bg_secondary'])
            button_frame.pack(fill="x", padx=10, pady=(0, 8))
            
            def play_snippet(e, snip_path=output_file):
                try:
                    if os.path.exists(snip_path):
                        from videoplayer import MediaPlayerApp
                        app = MediaPlayerApp(
                            parent=self.parent,
                            video_files=all_snippets,
                            current_file=snip_path,
                            random_select=True,
                            favorites_manager=self.favorites_manager,
                            category_manager=self.category_manager,
                            notes_manager=self.notes_manager,
                            trimmed_segments=self.trimmed_segments,
                            snippets_manager=self.snippets_manager,
                            associations_manager=self.association_manager,
                            deletion_manager=self.deletion_manager,
                            trimmed_segments_metadata=self.trimmed_segments_metadata,
                            fingerprint_manager=self.fingerprint_manager,
                            annotations_manager=self.annotations_manager,
                            description_manager=self.description_manager,
                            stats_manager=self.stats_manager
                        )
                        app.update_video_progress()
                    else:
                        messagebox.showerror("Error", f"Snippet file not found:\n{snip_path}")
                except Exception as ex:
                    messagebox.showerror("Error", f"Could not play snippet:\n{ex}")
            
            play_btn = tk.Button(button_frame, text="▶ Play Snippet", font=("Segoe UI", 9, "bold"),
                    bg=self.colors['accent'], fg="white", relief="flat", padx=10, pady=4,
                    command=lambda sp=output_file: play_snippet(None, sp))
            play_btn.pack(side="left")

    def _create_screenshots_section(self, parent):
        """Display screenshots in grid layout with larger tiles"""
        if not self.grouped_data['screenshots']:
            return
        
        heading = f"Screenshots ({len(self.grouped_data['screenshots'])})"
        content_frame = self._create_section_card(parent, heading, "🖼️")
        
        thumbnails_frame = tk.Frame(content_frame, bg=self.colors['bg_card'])
        thumbnails_frame.pack(fill="both", expand=True)
        
        rendered_count = 0
        col = 0
        row = 0
        max_cols = 3
        
        for img_path in self.grouped_data['shuffled_screenshots'][:12]:
            try:
                if not os.path.exists(img_path):
                    continue
                
                with Image.open(img_path) as img:
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    img.thumbnail((220, 160), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img.copy())
                    
                    cell_frame = tk.Frame(thumbnails_frame, bg=self.colors['bg_card'])
                    cell_frame.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
                    
                    img_label = tk.Label(cell_frame, image=photo, bg=self.colors['bg_secondary'],
                                        cursor="hand2", relief="flat", bd=0, padx=2, pady=2)
                    img_label.image = photo
                    img_label.pack(fill="both", expand=True)
                    
                    def on_enter(e, lbl=img_label):
                        lbl.config(bg=self.colors['accent'])
                    def on_leave(e, lbl=img_label):
                        lbl.config(bg=self.colors['bg_secondary'])
                    img_label.bind("<Enter>", on_enter)
                    img_label.bind("<Leave>", on_leave)
                    rendered_count += 1
                    
                    def open_viewer(e, img_index=self.grouped_data['screenshots'].index(img_path)):
                        valid_files = [f for f in self.grouped_data['screenshots'] if os.path.exists(f)]
                        if not valid_files:
                            messagebox.showerror("Error", "No valid screenshot files found.")
                            return
                        try:
                            viewer_win = tk.Toplevel(self.parent)
                            viewer_win.configure(bg="black")
                            viewer_win.focus_force()
                            viewer_win.grab_set()
                            self.parent.grab_release()
                            ImageViewer(viewer_win, valid_files, index=img_index, width=1000, height=600,
                                       deletion_manager=self.deletion_manager)
                        except Exception as ex:
                            messagebox.showerror("Error", f"Could not open viewer:\n{ex}")
                    
                    img_label.bind("<Button-1>", open_viewer)
                    
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1
            except:
                pass
        
        for i in range(max_cols):
            thumbnails_frame.columnconfigure(i, weight=1)
        
        if rendered_count == 0:
            tk.Label(content_frame, text="No screenshots available", font=("Segoe UI", 10, "italic"),
                    bg=self.colors['bg_card'], fg=self.colors['text_muted']).pack(anchor="w", pady=10)

    def _create_summary_stats_section(self, parent):
        """Create summary statistics section at the bottom"""
        
        content_frame = self._create_section_card(parent, "Summary Statistics", "📊")
        
        unique_codecs = set()
        for stat in self.grouped_data['stats']:
            try:
                codec = stat.get("Video Codec", "")
                if codec:
                    unique_codecs.add(codec)
            except:
                pass
        
        fav_percentage = (self.grouped_data['favorite_count'] / self.grouped_data['total_files'] * 100) if self.grouped_data['total_files'] > 0 else 0
        notes_percentage = (self.grouped_data['files_with_notes'] / self.grouped_data['total_files'] * 100) if self.grouped_data['total_files'] > 0 else 0
        
        summary_items = [
            ("📁 Total Files", str(self.grouped_data['total_files']), f"Files in group: {self.grouped_data['total_files']}"),
            ("💾 Total Size", convert_bytes(self.grouped_data['total_size']), f"Combined size: {convert_bytes(self.grouped_data['total_size'])}"),
            ("⏱ Total Duration", seconds_to_hhmmss(int(self.grouped_data['total_duration'])), f"Total playback time: {seconds_to_hhmmss(int(self.grouped_data['total_duration']))}"),
            ("⭐ Favorites", f"{self.grouped_data['favorite_count']} ({fav_percentage:.0f}%)", f"{self.grouped_data['favorite_count']} files marked as favorite"),
            ("📝 Notes", f"{self.grouped_data['files_with_notes']} ({notes_percentage:.0f}%)", f"{self.grouped_data['files_with_notes']} files have notes"),
            ("📌 Annotations", str(len(self.grouped_data['annotations'])), f"Total annotations: {len(self.grouped_data['annotations'])}"),
            ("🖼️ Screenshots", str(len(self.grouped_data['screenshots'])), f"Available screenshots: {len(self.grouped_data['screenshots'])}"),
            ("✂️ Snippets", str(len(self.grouped_data['snippets'])), f"Created snippets: {len(self.grouped_data['snippets'])}"),
            ("🏷️ Categories", str(len(self.grouped_data['categories'])), f"Assigned categories: {', '.join(self.grouped_data['categories'][:3])}{'...' if len(self.grouped_data['categories']) > 3 else ''}"),
            ("🎬 Video Codecs", str(len(unique_codecs)), f"Codecs: {', '.join(sorted(unique_codecs)[:5])}{'...' if len(unique_codecs) > 5 else ''}"),
            ("📊 Statistics", str(len(self.grouped_data['stats'])), f"Files with stats: {len(self.grouped_data['stats'])}"),
        ]
        
        for label, value, tooltip_text in summary_items:
            item_frame = tk.Frame(content_frame, bg=self.colors['bg_card'])
            item_frame.pack(fill="x", pady=5, padx=2)
            
            label_widget = tk.Label(item_frame, text=label, font=("Segoe UI", 10),
                    bg=self.colors['bg_card'], fg=self.colors['text_secondary'], cursor="hand2")
            label_widget.pack(side="left")
            
            value_widget = tk.Label(item_frame, text=value, font=("Segoe UI", 10, "bold"),
                    bg=self.colors['bg_card'], fg=self.colors['accent'], cursor="hand2")
            value_widget.pack(side="right")
            
            ToolTip(label_widget, tooltip_text, wraplength=250)
            ToolTip(value_widget, tooltip_text, wraplength=250)
            
            separator = tk.Frame(item_frame, bg=self.colors['border'], height=1)
            separator.pack(fill="x", pady=(5, 0))
        
        if self.watch_history_logger and self.grouped_data.get('watch_count', 0) > 0:
            separator_main = tk.Frame(content_frame, bg=self.colors['border'], height=2)
            separator_main.pack(fill="x", pady=10)
            
            watch_label = tk.Label(content_frame, text="👁️ Watch History", font=("Segoe UI", 11, "bold"),
                    bg=self.colors['bg_card'], fg=self.colors['accent'])
            watch_label.pack(anchor="w", pady=(5, 10))
            
            last_watched_file_tooltip = "Not available"
            if self.grouped_data.get('watch_count', 0) > 0:
                last_watched_file_tooltip = f"Last watched file:\n{self.grouped_data["last_watched_file"]}\n\nTime: {self.grouped_data['last_watched_date']}"
            
            watch_items = [
                ("🔍 Total Views", str(self.grouped_data['watch_count']), f"Total times files watched: {self.grouped_data['watch_count']}"),
                ("⏱ Total Watched", seconds_to_hhmmss(int(self.grouped_data['watch_total_seconds'])), f"Total time spent watching: {seconds_to_hhmmss(int(self.grouped_data['watch_total_seconds']))}"),
                ("📅 Last Watched", self.grouped_data['last_watched_date'] if self.grouped_data['last_watched_date'] else "Never", last_watched_file_tooltip),
            ]
            
            for label, value, tooltip_text in watch_items:
                item_frame = tk.Frame(content_frame, bg=self.colors['bg_card'])
                item_frame.pack(fill="x", pady=5, padx=2)
                
                label_widget = tk.Label(item_frame, text=label, font=("Segoe UI", 10),
                        bg=self.colors['bg_card'], fg=self.colors['text_secondary'], cursor="hand2")
                label_widget.pack(side="left")
                
                value_widget = tk.Label(item_frame, text=value, font=("Segoe UI", 10, "bold"),
                        bg=self.colors['bg_card'], fg=self.colors['accent'], cursor="hand2")
                value_widget.pack(side="right")
                
                ToolTip(label_widget, tooltip_text, wraplength=250)
                ToolTip(value_widget, tooltip_text, wraplength=250)
                
                separator = tk.Frame(item_frame, bg=self.colors['border'], height=1)
                separator.pack(fill="x", pady=(5, 0))

    def _create_file_list_section(self, parent):
        """Display file list"""
        content_frame = self._create_section_card(parent, f"Files ({len(self.file_paths)})", "📄")
        
        for i, file_path in enumerate(self.file_paths[:8], 1):
            file_name = os.path.basename(file_path)
            tk.Label(content_frame, text=f"{i}. {file_name}", font=("Segoe UI", 9),
                    bg=self.colors['bg_card'], fg=self.colors['text_secondary'],
                    wraplength=300, justify="left", anchor="w").pack(anchor="w", pady=2)
        
        if len(self.file_paths) > 8:
            tk.Label(content_frame, text=f"... +{len(self.file_paths) - 8} more files",
                    font=("Segoe UI", 9, "italic"), bg=self.colors['bg_card'],
                    fg=self.colors['text_muted']).pack(anchor="w", pady=5)

    def _create_section_card(self, parent, title, icon=""):
        """Create section card"""
        card_frame = tk.Frame(parent, bg=self.colors['bg_card'], relief="flat", bd=0)
        card_frame.pack(fill="x", pady=(0, 20))
        
        header_frame = tk.Frame(card_frame, bg=self.colors['bg_card'])
        header_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        if icon:
            tk.Label(header_frame, text=icon, font=("Segoe UI", 16), bg=self.colors['bg_card'],
                    fg=self.colors['accent']).pack(side="left", padx=(0, 10))
        
        tk.Label(header_frame, text=title, font=("Segoe UI", 16, "bold"), bg=self.colors['bg_card'],
                fg=self.colors['text_primary']).pack(side="left")
        
        separator = tk.Frame(card_frame, bg=self.colors['border'], height=1)
        separator.pack(fill="x", padx=20)
        
        content_frame = tk.Frame(card_frame, bg=self.colors['bg_card'])
        content_frame.pack(fill="x", padx=20, pady=(10, 15))
        
        return content_frame

    def _bind_window_events(self):
        """Bind window events"""
        self.bind('<Escape>', lambda e: self._close_window())
        self.focus_set()

    def _handle_error(self, error_msg):
        """Handle loading errors"""
        showerror(self, "Error", f"Failed to load grouped properties:\n{error_msg}")
        self._close_window()

    def _center_window(self, window, width, height):
        """Center window on screen"""
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x_coordinate = (screen_width - width) // 2
        y_coordinate = (screen_height - height) // 2
        window.geometry(f"{width}x{height}+{x_coordinate}+{y_coordinate}")

    def _close_window(self):
        """Close window safely"""
        try:
            self.unbind_all("<MouseWheel>")
            self.watch_history_logger.clear_fingerprint_index()
            self.watch_history_logger.clear_fingerprint_stats_index()
            self.grouped_data.clear()
        except:
            pass
        self.after(0, self.destroy)