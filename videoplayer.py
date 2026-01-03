import os
import random
import subprocess
import threading
import time
import timeit
import tkinter as tk

from datetime import timedelta

import vlc

from category_manager import CategoryManager
from category_window import CategoryWindow
from custom_dialogbox import MultiFieldDialog
from deletion_manager import DeletionManager
from favorites_manager import FavoritesManager
from annotations_manager import AnnotationsManager
from logs_writer import LogManager
from notes_window import NotesManagerGUI
from player_constants import (
    FILES_FOLDER, 
    LOG_PATH, 
    REPORTS_FOLDER, 
    SCREENSHOTS_FOLDER, 
    WATCHED_HISTORY_LOG_PATH, 
    VIDEO_SNIPPETS_FOLDER, 
    Colors
    )
from static_methods import build_transfer_graph, get_all_related_paths, get_all_related_paths_multiple, normalise_path, measure_time, measure_class_memory
from video_progress_bar import VideoProgressBar
from video_stats import VideoStatsApp
from volume_bar import VolumeBar
from watch_dictionary import WatchDict
from watch_history_logger import WatchHistoryLogger
from snippets_manager import SnippetsManager
from notes_manager import NotesManager
from associations_manager import FileAssociator
from fingerprint_manager import MediaFingerprintManager
from custom_messagebox import askopenfilename, showinfo, showwarning, showerror, askyesno
from tooltips import ToolTip

class MediaPlayerApp(tk.Toplevel):
    def __init__(self, video_files, current_file=None, random_select=True, video_path=None, watch_history_csv=WATCHED_HISTORY_LOG_PATH,
                  parent=None, category_manager=None, favorites_manager=None, deletion_manager=None,
                  notes_manager=None, snippets_manager=None, trimmed_segments=None,
                  associations_manager=None, fingerprint_manager=None, trimmed_segments_metadata=None, annotations_manager=None):
        super().__init__(parent)
        self.master = parent
        self._get_history_csvfile(watch_history_csv)
        self.favorites_manager = favorites_manager or FavoritesManager()
        self.logger = LogManager(LOG_PATH)
        self.deleter = deletion_manager or DeletionManager(self.favorites_manager)
        self.deleter.set_parent_window(self)
        self.category_manager = category_manager or CategoryManager()
        self.fingerprint_manager = fingerprint_manager or MediaFingerprintManager()
        self.watch_history_logger = WatchHistoryLogger(self.watch_history_csv, self.fingerprint_manager)
        self.snippets_manager = snippets_manager or SnippetsManager()
        self.notes_manager = notes_manager or NotesManager()
        self.associations_manager = associations_manager or FileAssociator()
        self.annotations_manager = annotations_manager or AnnotationsManager(fingerprint_manager=self.fingerprint_manager)

        self.trimmed_segments = trimmed_segments if trimmed_segments is not None else {}
        self.trimmed_segments_metadata = trimmed_segments_metadata if trimmed_segments_metadata is not None else {}
        self._precompute_trimmed_segments(video_files)

        self.bg_color = Colors.PLAIN_BLACK
        self.fg_color = Colors.PLAIN_WHITE
        self.title("Media Player")
        self.geometry("1000x600")
        self.lift()
        self.focus_force()
        self.center_window()
        self.configure(bg=self.bg_color)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.playback_segments = []  
        self.prev_counts = 0
        self.forward_counts = 0
        self.segment_start = 0
        self.segment_speed = 1.0
        self.segment_forward = 0
        self.segment_prev = 0
        self.active_trims = 0
        self.autoplay = True
        self.trim_start = None
        # self.loop_video = False
        self.loop_var = tk.BooleanVar(value=False)
        self.fast_trim = tk.BooleanVar(value=True)
        self._play_start_time = None
        self._total_play_time = 0
        self.trimmed = False
        # self.input_path = None

        self.random_select = random_select
        self.video_index = 0 if not current_file else video_files.index(current_file)
        
        self.current_time_str = "00:00:00"
        self.total_duration_str = "00:00:00"
        
        self._keybinding()
        self.initialize_player(video_files, video_path, cur_file=current_file)

    def _get_history_csvfile(self, watch_history_csv):
        try:
            with open(FILES_FOLDER + "file_info.txt", "r") as file:
                reader = file.readline().strip()
            if reader:
                self.watch_history_csv = reader
            else:
                self.watch_history_csv = watch_history_csv
        except FileNotFoundError:
            self.watch_history_csv = watch_history_csv

    def _get_trimmed_segments_metadata(self):
        """Get metadata for current file's trimmed segments."""
        return self.trimmed_segments_metadata.get(self.current_file, {})
    
    def _on_close(self, event=None):
        if self.active_trims > 0:
            showwarning(
                self,
                "Trimming in Progress",
                f"{self.active_trims} trim job(s) are still running.\n"
                "Please wait until they finish before closing."
            )
            return
        self.session_end = timeit.default_timer()
        self.stop()
        if self.trimmed:
            self.snippets_manager.fill_missing_snippet_fingerprints()
            self.associations_manager.update_missing_fingerprints()
        # tk.Tk.quit(self)
        self.show_session_stats(self.get_stats())
        # if hasattr(self, 'media_player'):
        #     self.media_player.stop()
        #     self.media_player.release()
        # if hasattr(self, 'instance'):
        #     self.instance.release()
        
        # self.deleter.set_parent_window(self.master)
        # self.destroy()
        # print("Closing window...")
        # self.withdraw()
        # print("Window withdrawn")
        # self.quit()
        # print("Application quit")

    def _create_new_player(self):
        self.media_player = self.instance.media_player_new()
        self.media_player.event_manager().event_attach(vlc.EventType.MediaPlayerEncounteredError, self.handle_error)
        self.media_player.event_manager().event_attach(
            vlc.EventType.MediaPlayerEndReached, self._on_video_end
        )
          

    def initialize_player(self, video_files, folder_path, cur_file=None):
        self.instance = vlc.Instance("--aout=directsound", '--avcodec-hw=dxva2', '--file-caching=4000')
        self._create_new_player()

        self.video_files = self.get_video_files(folder_path) if folder_path is not None else video_files
        self.current_file = cur_file
        self.current_fingerprint = self.fingerprint_manager.get_index_hash_by_path(normalise_path(self.current_file))
        self.previous_file = None
        self.playing_video = False
        self.video_paused = False
        self.session_start = None
        self.minimized = False
        # self.watched_videos = {}
        self.watched_videos = WatchDict()
        self.feedback_var = tk.StringVar()
        self.feedback_label = None 
        self.subtitle_delay = 0  # in microseconds
        self.subtitles_visible = True
        
        self._create_widgets()
        self._create_context_menu()
        if self.random_select:
            self.select_random_video()
        elif not self.random_select:
            self.select_sequential_videos()
        if cur_file:
            self.current_file = cur_file
        if self.video_files:
            self.play_video()

    def select_random_video(self):
        """Selects a random video from the list of video files."""
        if self.video_files:
            self.current_file = random.choice(self.video_files)

    def select_sequential_videos(self):
        if self.video_files:
            self.current_file = self.video_files[self.video_index]
            self.video_index += 1

    def _on_video_end(self, event):
        print(f"Video ended. Loop: {self.loop_var.get()}, Autoplay: {self.autoplay}")
        # Schedule play_next or loop on the main thread
        if self.loop_var.get():
            print("Looping video...")
            self.after(50, self._loop_video)
        elif self.autoplay:
            print("Autoplay next video...")
            self.after(200, self.play_next)

    def _loop_video(self):
        """Handle video looping with proper error handling"""
        try:
            if self.current_file and os.path.exists(self.current_file):
                print(f"Restarting looped video: {self.current_file}")
                self.after(0, self.stop)
                self.after(0, self.play_video)
            else:
                print("Current file not available for looping")
                # self.loop_video = False
                self.loop_var.set(False)
        except Exception as e:
            print(f"Error during looping: {e}")
            # self.loop_video = False
            self.loop_var.set(False)
        
    def _get_nearest_annotation(self, timestamp, tolerance=2.0):
        annotations = self.annotations_manager.get_annotations_for_file(self.current_file)
        nearest, min_dist = None, tolerance

        for ann in annotations:
            dist = abs(ann["timestamp_seconds"] - timestamp)
            if dist < min_dist:
                nearest, min_dist = ann, dist

        return nearest

    def update_annotation_at_time(self, event=None, check_existing=True, nearest=None):
        """Update or delete annotation near the current playback time."""
        if not self.current_file or not self.annotations_manager:
            showinfo(self, "No File", "No video is currently playing.")
            return

        was_topmost = self.attributes("-topmost")
        was_playing = not self.video_paused

        if was_playing:
            self.pause_video()
        if was_topmost:
            self.attributes("-topmost", False)

        try:
            if check_existing:
                timestamp = self.media_player.get_time() / 1000
                nearest = self._get_nearest_annotation(timestamp, tolerance=2.0)
                if not nearest:
                    showinfo(self, "Not Found", "No annotation found near current position.")
                    return

            dialog = MultiFieldDialog(
                self,
                title="Update Video Annotation",
                max_height=550,
                header_height=30,
                window_height=250
            )

            dialog.add_info(
                f'Created at: {nearest["created_at"]}\t Modified at: {nearest["modified_at"]}',
                italic=True,
                fg=Colors.PLAIN_ORANGE
            )

            dialog.add_readonly_field("file_path", "File Path", self.current_file)
            dialog.add_readonly_field("timestamp", "Timestamp", self._format_time(nearest["timestamp_seconds"]))

            dialog.add_field(
                "annotation_text",
                "Annotation Text",
                str,
                required=True,
                multiline=True,
                default_value=nearest["annotation_text"]
            )

            def on_delete():
                confirm = askyesno(self,
                    "Confirm Delete",
                    "Are you sure you want to delete this annotation?"
                )
                if confirm:
                    self.annotations_manager.delete_annotation(nearest["annotation_id"])
                    self.show_marquee("Annotation deleted")
                    self.progress_bar.redraw()
                    dialog.result = None
                    dialog.destroy()

            def on_update():
                dialog.destroy()

            dialog.update_idletasks()  
            dialog.add_buttons([
                ("Delete", on_delete, Colors.PLAIN_GRAY, Colors.PLAIN_RED),
            ], sticky_bottom=True, position="right")

            self.wait_window(dialog)

            if not dialog.result:
                return

            new_text = dialog.result.get("annotation_text", "").strip()
            if not new_text:
                showinfo(self, "Invalid", "Annotation text cannot be empty.")
                return

            self.annotations_manager.update_annotation(
                annotation_id=nearest["annotation_id"],
                annotation_text=new_text
            )

            self.show_marquee("Annotation updated")
            self.progress_bar.redraw()

        except Exception as e:
            showerror(self, "Error", f"An error occurred: {e}")
            self.logger.error_logs(f"Error updating annotation: {e}")

        finally:
            if was_playing:
                self.pause_video()
            if was_topmost:
                self.attributes("-topmost", True)


    def add_annotation(self, event=None, timestamp_seconds=None):
        """Open dialog to add an annotation at given timestamp."""
        if not self.current_file:
            showwarning(self, "No File", "No video is currently playing.")
            return
        
        if timestamp_seconds is None:
            timestamp_seconds = self.media_player.get_time() / 1000
        
        nearest = self._get_nearest_annotation(timestamp_seconds, tolerance=2.0)

        if nearest:
            self.update_annotation_at_time(event=None, check_existing=False, nearest=nearest)
            return
        
        was_topmost = self.attributes("-topmost")
        was_playing = not self.video_paused

        if was_playing:
            self.pause_video()
        if was_topmost:
            self.attributes("-topmost", False)
        
        try:
            dialog = MultiFieldDialog(
                self,
                title="Add Video Annotation",
                max_height=500,
                window_height=225
            )

            dialog.add_readonly_field(
                "file_path",
                "File Path",
                f"{self.current_file}")

            dialog.add_readonly_field(
                "timestamp",
                "Timestamp",
                self._format_time(timestamp_seconds)
            )

            dialog.add_field(
                "annotation_text",
                "Annotation Text",
                str,
                required=True,
                multiline=True
            )

            self.wait_window(dialog)

            if not dialog.result:
                return

            text = dialog.result.get("annotation_text", "").strip()
            if not text:
                print("Annotation text is empty. Not saving.")
                return

            self.annotations_manager.add_annotation(
                self.current_file,
                timestamp_seconds,
                text
            )

            self.show_marquee(
                f"Annotation added at {self._format_time(timestamp_seconds)}"
            )
        finally:
            if was_playing:
                self.pause_video()
            if was_topmost:
                self.attributes("-topmost", True)


    def _format_time(self, seconds):
        """Format seconds to HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def delete_annotation_at_time(self, event=None):
        """Delete annotation at current time."""
        if not self.current_file or not self.annotations_manager:
            return
        
        timestamp = self.media_player.get_time() / 1000
        annotations = self.annotations_manager.get_annotations_for_file(self.current_file)
        
        nearest = None
        min_distance = 2.0  # Within 2 seconds
        
        for ann in annotations:
            distance = abs(ann["timestamp_seconds"] - timestamp)
            if distance < min_distance:
                nearest = ann
                min_distance = distance
        
        if nearest:
            if askyesno("Delete", f"Delete annotation: {nearest['annotation_text'][:50]}...?"):
                self.annotations_manager.delete_annotation(nearest["annotation_id"])
                self.show_marquee("Annotation deleted")
                self.progress_bar.redraw()
        else:
            showinfo(self, "Not Found", "No annotation found near current position.")

    def _create_widgets(self):
        """Creates the GUI elements for the media player with improved style and responsiveness."""
        self.drag_bar = tk.Frame(self, height=0, bg=Colors.PLAIN_BLACK, cursor="fleur", pady=0)
        self.drag_bar.pack(fill=tk.X, side=tk.TOP)

        # self.drag_label = tk.Label(self.drag_bar, text="---------", bg="#222", fg=Colors.PLAIN_WHITE, padx=0, pady=0)
        # self.drag_label.pack(side=tk.TOP, fill=tk.X, padx=0, pady=0)

        self.drag_bar.bind("<ButtonPress-1>", self._start_move)
        self.drag_bar.bind("<ButtonRelease-1>", self._stop_move)
        self.drag_bar.bind("<B1-Motion>", self._do_move)
        # self.drag_label.pack_forget()
        # self.drag_bar.pack_forget()

        self.media_canvas = tk.Canvas(self, bg=Colors.PLAIN_BLACK, width=1000, height=500, highlightthickness=0)
        self.media_canvas.pack(pady=0, fill=tk.BOTH, expand=True)

        control_frame = tk.Frame(self, bg=Colors.PLAIN_BLACK, width=1000)
        control_frame.pack(pady=(5, 0), anchor=tk.CENTER)

        # Not used, instead show marquee is best
        self.feedback_label = tk.Label(
            self,
            textvariable=self.feedback_var,
            font=("Segoe UI", 18, "bold"),
            bg=Colors.PLAIN_BLACK,
            fg=Colors.PLAIN_WHITE
        )
    

        def style_btn(btn, bg, fg, activebg=None, activefg=None):
            btn.config(
                bg=bg,
                fg=fg,
                relief=tk.FLAT,
                bd=0,
                font=("Segoe UI", 10, "bold"),
                activebackground=activebg or bg,
                activeforeground=activefg or fg,
                cursor="hand2",
                padx=5,
                pady=0
            )

        self.current_stats_button = tk.Button(
            control_frame, text="Current Stats", command=self.current_stats
        )
        style_btn(self.current_stats_button, Colors.PLAIN_BLACK, Colors.PLAIN_WHITE, Colors.ACTIVE_WHITE)

        self.prev_button = tk.Button(
            control_frame, text="Previous", command=self.play_previous
        )
        style_btn(self.prev_button, Colors.PLAIN_BLACK, Colors.PLAIN_RED, Colors.ACTIVE_RED)

        self.rewind_button = tk.Button(
            control_frame, text="⏪", command=self.rewind
        )
        style_btn(self.rewind_button, Colors.PLAIN_BLACK, Colors.PLAIN_RED, Colors.ACTIVE_RED)

        self.play_button = tk.Button(
            control_frame, text="▶️ Play", command=self.play_video
        )
        style_btn(self.play_button, Colors.PLAIN_BLACK, Colors.PLAIN_WHITE, "#222222")

        self.pause_button = tk.Button(
            control_frame, text="⏸️ Pause", command=self.pause_video
        )
        style_btn(self.pause_button, Colors.PLAIN_BLACK, Colors.WARNING_ORANGE, "#e65100")

        self.fast_forward_button = tk.Button(
            control_frame, text="⏩", command=self.fast_forward
        )
        style_btn(self.fast_forward_button, Colors.PLAIN_BLACK, Colors.PLAIN_RED, Colors.ACTIVE_RED)

        self.next_button = tk.Button(
            control_frame, text="Next", command=self.play_next
        )
        style_btn(self.next_button, Colors.PLAIN_BLACK, Colors.PLAIN_RED, Colors.ACTIVE_RED)

        self.category_button = tk.Button(
            control_frame, text="☰", command=self.open_category_manager
        )
        style_btn(self.category_button, Colors.PLAIN_BLACK, Colors.PLAIN_PURPLE, Colors.CATEGORY_PURPLE)

        self.autoplay_button = tk.Button(
            control_frame, text="Auto: ON", command=self.toggle_autoplay
        )
        style_btn(self.autoplay_button, Colors.PLAIN_BLACK, Colors.SUCCESS_GREEN, "#1565C0")

        self.loop_button = tk.Button(
            control_frame, text="⟲", command=self.toggle_loop
        )
        style_btn(self.loop_button, Colors.PLAIN_BLACK, Colors.PLAIN_WHITE, "#37474F")

        for btn in [
            self.current_stats_button, self.prev_button, self.rewind_button,
            self.play_button, self.pause_button, self.fast_forward_button,
            self.next_button, self.category_button, self.autoplay_button, self.loop_button
        ]:
            btn.pack(side=tk.LEFT, padx=3, pady=0)

        self.time_label = tk.Label(
            control_frame,
            text="00:00:00 / 00:00:00",
            font=("Segoe UI", 10, "bold"),
            fg=Colors.PLAIN_WHITE,
            bg=Colors.PLAIN_BLACK,
            padx=10
        )
        self.time_label.pack(side=tk.RIGHT, padx=(20,10), pady=0)

        self.progress_bar = VideoProgressBar(
            self, self.set_video_position, bg=self.bg_color, highlightthickness=0,
            trimmed_segments=self._get_trimmed_segments(),
            annotations_manager=self.annotations_manager
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=0)

        self.volume_bar = VolumeBar(self, self.media_player, bg=self.bg_color)
        self.volume_bar.pack(side=tk.RIGHT, padx=5, pady=0)


        def on_enter(e): e.widget.config(fg="#444")
        def on_leave(e):
            txt = e.widget["text"]
            if txt in ["Previous", "⏪", "⏩", "Next"]:
                e.widget.config(fg=Colors.PLAIN_RED, bg=Colors.PLAIN_BLACK)
            elif txt == "Current Stats":
                e.widget.config(fg=Colors.PLAIN_WHITE, bg=Colors.PLAIN_BLACK)
            elif txt == "Categories":
                e.widget.config(fg=Colors.CATEGORY_PURPLE, bg=Colors.PLAIN_BLACK)
            elif txt == "Fav +":
                e.widget.config(bg=Colors.PLAIN_WHITE)
            elif txt == "Fav -":
                e.widget.config(bg=Colors.PLAIN_BLACK)
            elif "Pause" in txt or "Resume" in txt:
                e.widget.config(fg=Colors.WARNING_ORANGE, bg=Colors.PLAIN_BLACK)
            elif "Auto" in txt:
                e.widget.config(fg=Colors.SUCCESS_GREEN, bg=Colors.PLAIN_BLACK) if self.autoplay else e.widget.config(fg=Colors.PLAIN_WHITE, bg=Colors.PLAIN_BLACK)
            elif "⟲" in txt:
                e.widget.config(fg=Colors.SUCCESS_GREEN, bg=Colors.PLAIN_BLACK) if self.loop_var.get() else e.widget.config(fg=Colors.PLAIN_WHITE, bg=Colors.PLAIN_BLACK)
            elif "☰" in txt:
                e.widget.config(fg=Colors.PLAIN_PURPLE, bg=Colors.PLAIN_BLACK)
            else:
                e.widget.config(fg=Colors.PLAIN_WHITE, bg=Colors.PLAIN_BLACK)

        for btn in [
            self.current_stats_button, self.category_button, self.prev_button, self.rewind_button,
            self.play_button, self.pause_button, self.fast_forward_button,
            self.next_button, self.autoplay_button, self.loop_button
        ]:
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)
        self.set_tooltip()

    def set_tooltip(self):
        ToolTip(self.play_button, "Play Video (Spacebar)")
        ToolTip(self.category_button, "Open Category Manager (Shift + A)")
        ToolTip(self.autoplay_button, "Toggle Autoplay (A)")
        ToolTip(self.loop_button, "Toggle Loop (L)")
        ToolTip(self.next_button, "Play Next Video (N or Ctrl + Right Arrow)")
        ToolTip(self.prev_button, "Play Previous Video (Shift + Left Arrow or Ctrl + Left Arrow)")
        ToolTip(self.rewind_button, "Rewind 5 Seconds (Left Arrow)")
        ToolTip(self.fast_forward_button, "Fast Forward 10 Seconds (Right Arrow)")

    def _start_move(self, event=None):
        self._drag_last_x = event.x_root
        self._drag_last_y = event.y_root

    def _stop_move(self, event=None):
        # self.drag_bar.config(bg=Colors.PLAIN_BLACK)
        # self.drag_label.pack_forget()
        self._drag_last_x = None
        self._drag_last_y = None

    def _do_move(self, event=None):
        if getattr(self, "_drag_last_x", None) is None:
            return
        # self.drag_bar.config(bg=Colors.HEADER_COLOR_RED)
        # self.drag_label.pack(side=tk.LEFT, padx=3)
        dx = event.x_root - self._drag_last_x
        dy = event.y_root - self._drag_last_y
        self.geometry(f"+{self.winfo_x() + dx}+{self.winfo_y() + dy}")
        self._drag_last_x = event.x_root
        self._drag_last_y = event.y_root


    def toggle_autoplay(self, event=None):
        """Toggle the autoplay setting."""
        self.autoplay = not self.autoplay
        self.autoplay_button.config(
            text=f"Auto: {'ON' if self.autoplay else 'OFF'}",
            fg=Colors.SUCCESS_GREEN if self.autoplay else Colors.PLAIN_WHITE,
            bg=Colors.PLAIN_BLACK
        )
        self.show_marquee("Autoplay is ON" if self.autoplay else "Autoplay is OFF")

    def toggle_always_on_top(self, event=None):
        """Toggle whether the window stays on top of other windows."""
        self.is_on_top = self.attributes("-topmost")
        self.attributes("-topmost", not self.is_on_top)
        # self.drag_label.pack(side=tk.LEFT, padx=0, pady=0)
        # self.drag_bar.config(height=5 if not is_on_top else 0)
        if not self.is_on_top:
            self.drag_bar.config(height=5, bg=Colors.HEADER_COLOR_RED) if not self.video_paused else self.drag_bar.config(height=5, bg=Colors.ORANGE)
        else:
            self.drag_bar.config(height=0, bg=Colors.PLAIN_BLACK) if not self.video_paused else self.drag_bar.config(height=0, bg=Colors.ORANGE)
        
        self.toggle_shorten_window(event=event)
        self.show_marquee("Always on top: " + ("ON" if not self.is_on_top else "OFF"))

    def toggle_shorten_window(self, event=None):
        if not self.minimized:
            if self.attributes("-fullscreen"):
                self.attributes("-fullscreen", False)
                self.update_idletasks()

            if self.state() == "zoomed":
                self.prev_geometry = "zoomed"
                self.state("normal")
            else:
                self.prev_geometry = self.geometry()

            self.toggle_controls_visibility(False)
            self.overrideredirect(True)

            if hasattr(self, "minimized_geometry"):
                self.geometry(self.minimized_geometry)
            else:
                self.minimized_geometry = self.shorten_window()

            self.minimized = True

        else:
            self.minimized_geometry = self.geometry()
            self.overrideredirect(False)

            if self.prev_geometry == "zoomed":
                self.state("zoomed")
            elif self.prev_geometry:
                self.geometry(self.prev_geometry)

            self.toggle_controls_visibility(True)
            self.minimized = False

    def _create_context_menu(self):
        """Create right-click context menu with submenus for audio and subtitle settings."""
        self.context_menu = tk.Menu(self, tearoff=0, bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE)

        audio_channel_menu = tk.Menu(self.context_menu, tearoff=0, bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE)
        audio_channel_menu.add_command(label="Stereo", command=lambda: self.set_audio_channel("stereo"))
        audio_channel_menu.add_command(label="Mono", command=lambda: self.set_audio_channel("mono"))
        audio_channel_menu.add_command(label="Left Channel", command=lambda: self.set_audio_channel("left"))
        audio_channel_menu.add_command(label="Right Channel", command=lambda: self.set_audio_channel("right"))

        audio_track_menu = tk.Menu(self.context_menu, tearoff=0, bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE)
        audio_track_menu.add_command(label="Next Audio Track", command=self.next_audio_track)
        audio_track_menu.add_command(label="Toggle Audio", command=self.toggle_audio)

        subs_menu = tk.Menu(self.context_menu, tearoff=0, bg=Colors.PLAIN_BLACK, fg=Colors.PLAIN_WHITE)
        subs_menu.add_command(label="Increase Delay", command=self.increase_sub_delay)
        subs_menu.add_command(label="Decrease Delay", command=self.decrease_sub_delay)
        subs_menu.add_separator()
        subs_menu.add_command(label="Toggle Subtitles", command=self.toggle_subtitles)
        subs_menu.add_command(label="Next Subtitle Track", command=self.next_subtitle_track)
        subs_menu.add_command(label="Add Subtitle File...", command=self.add_subtitle)
        self.context_menu.add_command(label="Add Notes", command=self.show_notes, accelerator="Shift + N")
        self.context_menu.add_command(label="Add to Category", command=self.open_category_manager, accelerator="Shift + A")
        self.context_menu.add_command(label="Add Annotation", command=self.add_annotation, accelerator="Shift + C")
        self.context_menu.add_separator()

        self.context_menu.add_cascade(label="Audio Stereo", menu=audio_channel_menu)
        self.context_menu.add_cascade(label="Audio Tracks", menu=audio_track_menu)
        self.context_menu.add_cascade(label="Subtitles", menu=subs_menu)
        self.context_menu.add_checkbutton(
            label="Loop",
            variable=self.loop_var,
            command=self.toggle_loop
        )
        self.context_menu.add_checkbutton(
            label="Fast Trim (No Re-encode)",
            variable=self.fast_trim,
            onvalue=True,
            offvalue=False,
            command=lambda: self.toggle_fast_trim(value=not self.fast_trim.get())
        )
        
        self.bind("<Button-3>", self._show_context_menu)
        self.bind("<Button-2>", self._show_context_menu)


    def _show_context_menu(self, event):
        """Show the context menu at mouse pointer position."""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def set_audio_channel(self, mode):
        mapping = {
            "stereo": 0,
            "mono": 5,
            "left": 2,
            "right": 3,
        }
        if mode in mapping:
            self.media_player.audio_set_channel(mapping[mode])
            print(f"Audio channel set to {mode}")
            self.show_marquee(f"Audio: {mode.capitalize()}")


    def shorten_window(self):
        screen_width = self.winfo_screenwidth()
        new_width, new_height = 450, 270
        x = screen_width - (new_width + 20)
        y = 35
        minimized_geometry = f"{new_width}x{new_height}+{x}+{y}"
        self.geometry(minimized_geometry)
        return minimized_geometry

    def toggle_always_on_top_minimized_only(self, event=None):
        """
        Toggle always-on-top ON/OFF but keep minimized state.
        Only valid if already minimized.
        """
        self.is_on_top = self.attributes("-topmost")
        if not self.minimized and not self.is_on_top:
            self.show_marquee("Must be minimized to use this toggle")
            return

        self.attributes("-topmost", not self.is_on_top)

        if not self.is_on_top:
            self.drag_bar.config(height=5, bg=Colors.HEADER_COLOR_RED)
            self.show_marquee("Always on top: ON (Minimized)")
            self.overrideredirect(True)
        else:
            self.drag_bar.config(height=0, bg=Colors.PLAIN_BLACK)
            self.show_marquee("Always on top: OFF (Minimized)")
            self.overrideredirect(False)
    
    def toggle_loop(self, event=None):
        if event is not None:  
            self.loop_var.set(not self.loop_var.get())

        if self.loop_var.get():
            self.loop_button.config(fg=Colors.SUCCESS_GREEN)
            print("Loop enabled")
        else:
            self.loop_button.config(fg=Colors.PLAIN_WHITE)
            print("Loop disabled")
        self.show_marquee("Looping is ON" if self.loop_var.get() else "Looping is OFF")
        if self.loop_var.get() and self.current_file:
            self.last_looped_file = self.current_file

    def _keybinding(self):
        """
        All the key shortcuts bound into the player.
        Automatically unbinds existing ones before rebinding.
        """
        if hasattr(self, "_bindings"):
            for seq, _ in self._bindings:
                self.unbind(seq)
        else:
            self._bindings = []

        self._bindings = [
            ("<Shift-KeyPress-Left>", self.play_previous),
            ("<KeyPress-Left>", self.rewind),
            ("<KeyPress-space>", self.pause_video),
            ("<KeyPress-Right>", self.fast_forward),
            ("<Shift-KeyPress-Right>", self.play_next),
            ("<KeyPress-n>", self.play_next),
            ("<KeyPress-N>", self.play_next),
            ("<KeyPress-m>", self.toggle_mute),
            ("<KeyPress-M>", self.toggle_mute),
            ("<KeyPress-Up>", self.volume_increase),
            ("<KeyPress-Down>", self.volume_decrease),
            ("<KeyPress-f>", self.toggle_fullscreen),
            ("<KeyPress-F>", self.toggle_fullscreen),
            ("<Shift-KeyPress-S>", self.save_screenshot),
            ("<Shift-KeyPress-s>", self.save_screenshot),
            ("<Control-f>", self.add_to_favorites),
            ("<Control-F>", self.add_to_favorites),
            ("<Control-d>", self.remove_from_favorites),
            ("<Control-D>", self.remove_from_favorites),
            ("<KeyPress-x>", self.cycle_playback_speed),
            ("<KeyPress-X>", self.cycle_playback_speed),
            ("<Shift-KeyPress-X>", self.slow_playback_speed),
            ("<Shift-KeyPress-x>", self.slow_playback_speed),
            ("<Control-Right>", self.play_im_next),
            ("<Control-Left>", self.play_im_previous),
            ("<Delete>", self.delete_video),
            ("<Control-Shift-Delete>", self.remove_from_deletion),
            ("<Shift-KeyPress-a>", self.open_category_manager),
            ("<Shift-KeyPress-A>", self.open_category_manager),
            ("<KeyPress-a>", self.toggle_autoplay),
            ("<KeyPress-A>", self.toggle_autoplay),
            ("<Alt-t>", self.toggle_always_on_top),
            ("<Alt-T>", self.toggle_always_on_top),
            ("<F10>", self.toggle_always_on_top_minimized_only),
            ("<Control-S>", self.mark_start),
            ("<Control-s>", self.mark_start),
            ("<Control-E>", self.mark_end),
            ("<Control-e>", self.mark_end),
            ("<Shift-b>", self.add_subtitle),
            ("<Shift-B>", self.add_subtitle),
            ("<KeyPress-B>", self.toggle_subtitles),
            ("<KeyPress-b>", self.toggle_subtitles),
            ("<KeyPress-,>", self.decrease_sub_delay),
            ("<KeyPress-.>", self.increase_sub_delay),
            ("<Control-b>", self.next_subtitle_track),
            ("<Control-B>", self.next_subtitle_track),
            ("<Control-V>", self.next_audio_track),
            ("<Control-v>", self.next_audio_track),
            ("<KeyPress-l>", self.toggle_loop),
            ("<KeyPress-L>", self.toggle_loop),
            ("<Shift-KeyPress-n>", self.show_notes),
            ("<Shift-KeyPress-N>", self.show_notes),
            ("<Escape>", self._on_close),
            ("<KeyPress-q>", self.toggle_fast_trim),
            ("<KeyPress-Q>", self.toggle_fast_trim),
            ("<Return>", self.display_name),
            ("<Shift-KeyPress-c>", self.add_annotation),
            ("<Shift-KeyPress-C>", self.add_annotation),
            ("<Control-Delete>", self.delete_annotation_at_time),
        ]

        for seq, func in self._bindings:
            self.bind(seq, func)

    def _unbind_keys(self):
        """Unbind all keyboard shortcuts used in the player."""
        if hasattr(self, "_bindings"):
            for seq, _ in self._bindings:
                self.unbind(seq)
            self._bindings.clear()

    def show_notes(self, event=None):
        if not self.current_file:
            showwarning(self, "No Video Loaded", "Please load a video in order to view or add notes.")
            return

        file_path = self.current_file
        was_topmost = self.attributes("-topmost")
        was_playing = not self.video_paused

        if was_playing:
            self.pause_video()
        if was_topmost:
            self.attributes("-topmost", False)

        try:
            notes_window = NotesManagerGUI(self.notes_manager, snippets_manager=self.snippets_manager, 
                                           parent=self, file_path=file_path, minimal=True)
            self.wait_window(notes_window.root)
        finally:
            if was_playing:
                self.pause_video()
            if was_topmost:
                self.attributes("-topmost", True)

    def display_name(self, event=None):
        if self.current_file:
            filename = os.path.basename(self.current_file)
            self.show_marquee(f"{filename}")


    def _on_video_loaded(self, title):
        self.reset_values(segment_speed=self.segment_speed)
        self.reset_trim()
        if self.loop_var.get():
            print(f"Looping video: {title}")

        self.title(title)
        self.media_player.set_hwnd(self.media_canvas.winfo_id())
        self.media_player.play()
        # self.set_playback_speed(self.segment_speed)
        self.show_marquee(f"Playing: {self.current_file}")
        self.session_start = timeit.default_timer() if self.session_start is None else self.session_start
        self.playing_video = True
        self.watched_videos.add_watch(self.current_file)
        self.progress_bar.update_progress()

    @measure_time(print_time=True, prefix="[TIMER] ")
    def _precompute_trimmed_segments(self, video_files):
        """Precompute trimmed segments and metadata in the background."""
        
        if not any(f not in self.trimmed_segments for f in video_files):
            print("[INFO] All trimmed segments already precomputed, skipping thread.")
            if hasattr(self, "current_file") and hasattr(self, 'progress_bar') and self.winfo_exists():
                self.after(0, lambda: self._apply_trimmed_segments_to_progress_bar())
            return

        def worker():
            if not hasattr(self, "transfer_graph"):
                self.transfer_graph = build_transfer_graph()

            graph = self.transfer_graph

            try:
                all_related_paths = get_all_related_paths_multiple(video_files, graph=graph)
            except Exception as e:
                print(f"[WARNING] Failed to compute related paths: {e}")
                return
            
            snippets_by_file = {}

            if hasattr(self, "snippets_manager") and self.snippets_manager:
                for path in all_related_paths:
                    try:
                        snippets = self.snippets_manager.get_snippets_by_original_file(path)
                        if snippets:
                            snippets_by_file[path] = snippets
                    except Exception:
                        continue

            for f in video_files:
                if f in self.trimmed_segments:
                    continue

                segments = []
                metadata = {}

                try:
                    related_paths = get_all_related_paths(f, graph=graph)
                except Exception:
                    related_paths = [f]

                for rp in related_paths:
                    if rp in self.trimmed_segments:
                        segments.extend(self.trimmed_segments[rp])

                        rp_meta = self.trimmed_segments_metadata.get(rp, {})
                        metadata.update(rp_meta)
                        continue

                    snippets = snippets_by_file.get(rp, [])
                    for snippet in snippets:
                        try:
                            start = float(snippet["Start Time (s)"])
                            end = float(snippet["End Time (s)"])
                            notes = snippet.get("Notes", "")

                            seg = (start, end)
                            segments.append(seg)

                            if notes:
                                metadata[seg] = {"notes": notes}
                        except Exception:
                            continue

                segments = sorted(set(segments))

                self.trimmed_segments[f] = segments
                self.trimmed_segments_metadata[f] = metadata

            if hasattr(self, "current_file") and hasattr(self, 'progress_bar') and self.winfo_exists():
                self.after(0, lambda: self._apply_trimmed_segments_to_progress_bar())

            print("[INFO] Precomputation of trimmed segments (with metadata) completed.")

        threading.Thread(target=worker, daemon=True).start()

    def _apply_trimmed_segments_to_progress_bar(self):
        """Apply current file's segments and metadata to progress bar."""
        if self.current_file in self.trimmed_segments:
            segments = self.trimmed_segments[self.current_file]
            metadata = self.trimmed_segments_metadata.get(self.current_file, {})
            self.progress_bar.set_trimmed_segments(segments, segment_metadata=metadata)


    def _get_trimmed_segments(self):
        """Get trimmed segments for the current file from the precomputed dict."""
        return self.trimmed_segments.get(self.current_file, [])

    def reset_values(self, segment_speed=None):
        self.playback_segments = []
        self.segment_start = 0
        self.segment_speed = 1.0 if segment_speed is None else segment_speed
        self.segment_forward = 0
        self.segment_prev = 0
        self.prev_counts = 0
        self.forward_counts = 0

    def slow_playback_speed(self, event=None):
        """Slows down playback to the next lower speed."""
        if self.playing_video:
            speeds = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
            current_speed = self.media_player.get_rate()
            lower_speeds = [s for s in speeds if s < current_speed]
            if lower_speeds:
                new_speed = lower_speeds[-1]
            else:
                new_speed = speeds[0]
            self.set_playback_speed(new_speed)
            print(f"Playback Slowed to: {new_speed}x")

    def cycle_playback_speed(self, event=None):
        """Cycles playback speed between 1x, 1.25x, 1.5x, 1.75x, and 2x."""
        if self.playing_video:
            speeds = [1.0, 1.25, 1.5, 1.75, 2.0]
            current_speed = self.media_player.get_rate()
            try:
                index = next(i for i, s in enumerate(speeds) if abs(s - current_speed) < 0.1)
                new_index = (index + 1) % len(speeds)
            except StopIteration:
                new_index = 0
            new_speed = speeds[new_index]
            self.set_playback_speed(new_speed)
            print(f"Playback Speed Changed to: {new_speed}x")
            self.show_marquee(f"Speed: {new_speed}x")

    def set_playback_speed(self, speed):
        if self.playing_video:
            # self.record_segment()
            self.segment_speed = speed
            self.media_player.set_rate(speed)
            self.show_marquee(f"Speed: {speed}x")

    def record_segment(self):
        """Record the current playback segment."""
        segment_end = self.media_player.get_time()
        if segment_end > self.segment_start:
            self.playback_segments.append({
                "start": self.segment_start,
                "end": segment_end,
                "speed": self.segment_speed,
                "forward_counts": self.segment_forward,
                "prev_counts": self.segment_prev
            })
        self.segment_start = segment_end
        self.segment_forward = 0
        self.segment_prev = 0

    def remove_from_deletion(self, event=None):
        self.deleter.remove_from_deletion(self.current_file)
        self.show_marquee(f"Removed Marked {self.current_file} file from deletion list.")
        
        
    def add_to_favorites(self, event=None):
        """Adds the currently playing video to favorites."""
        if self.current_file:
            if self.favorites_manager.add_to_favorites(self.current_file):
                self.show_marquee(f"Added {self.current_file} from favorites")
            else:
                self.show_marquee("Video is already in favorites!")

    def remove_from_favorites(self, event=None):
        """Removes the currently playing video from favorites."""
        if self.current_file:
            if self.favorites_manager.delete_from_favorites(self.current_file):
                self.show_marquee(f"Removed {self.current_file} from favorites")
            else:
                self.show_marquee("Video is not in favorites!")

    def show_marquee(self, text):
        self.media_player.video_set_marquee_string(vlc.VideoMarqueeOption.Text, text.encode('utf-8'))
        self.media_player.video_set_marquee_int(vlc.VideoMarqueeOption.Enable, 1)
        self.media_player.video_set_marquee_int(vlc.VideoMarqueeOption.Timeout, 1000)  # 1 seconds


    def toggle_controls_visibility(self, visibility):
        """Toggle the visibility of all control buttons and progress bars."""
        widgets_with_default_padding = [self.current_stats_button, self.prev_button, self.rewind_button, self.play_button,
                                        self.pause_button, self.fast_forward_button, self.next_button,
                                          self.category_button, self.autoplay_button, self.loop_button]
        widgets_with_custom_padding = [self.time_label, self.progress_bar, self.volume_bar]

        if visibility:
            for widget in widgets_with_default_padding:
                widget.pack(side=tk.LEFT, padx=3, pady=0)  # Pack with default padding

            # Pack widgets with custom padding individually
            # self.time_label.pack(side=tk.RIGHT, padx=10, pady=0)
            self.progress_bar.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=0, expand=True)
            self.volume_bar.pack(side=tk.RIGHT, padx=5, pady=0)
            # self.time_label.pack(side=tk.RIGHT, padx=10, pady=0)
        else:
            for widget in widgets_with_default_padding:
                widget.pack_forget()

            # Forget widgets with custom padding individually
            # self.time_label.pack_forget()
            self.progress_bar.pack_forget()
            self.volume_bar.pack_forget()
            # self.time_label.pack_forget()

    def toggle_fullscreen(self, event=None):
        """Toggle fullscreen mode."""
        try:
            self.fullscreen = not self.attributes("-fullscreen")
            self.attributes("-fullscreen", self.fullscreen) 
            if self.fullscreen:
                self.toggle_controls_visibility(visibility=False)
                self.config(cursor="none")
            else:
                self.toggle_controls_visibility(visibility=True)
                self.config(cursor="")
        except Exception as e:
            print(f"Error toggling fullscreen: {e}")
            showerror(self, "Fullscreen Error", f"Could not toggle fullscreen mode:\n{e}")

    def save_screenshot(self, event):
        """Saves a screenshot of the video frame."""
        # self.ensure_folder_exists(SCREENSHOTS_FOLDER)
        filename = self.current_file.split('\\')[-1]
        # length = self.get_duration_str
        screenshot_path = f"{SCREENSHOTS_FOLDER}\\screenshot_{filename}_{self.media_player.get_time()}.png"
        self.media_player.video_take_snapshot(0, screenshot_path, 0, 0)
        # _convert_single(screenshot_path, delete_original=True)

    def volume_increase(self, event):
        """Increases the volume."""
        current_volume = self.media_player.audio_get_volume()
        new_volume = min(current_volume + 5, 200)
        self.media_player.audio_set_volume(int(new_volume))
        self.show_marquee(f"Volume: {new_volume}")
        self.volume_bar.update_volume(new_volume)

    def volume_decrease(self, event):
        """Decreases the volume."""
        current_volume = self.media_player.audio_get_volume()
        new_volume = max(current_volume - 5, 0)
        self.media_player.audio_set_volume(int(new_volume))
        self.show_marquee(f"Volume: {new_volume}")
        self.volume_bar.update_volume(new_volume)


    def select_file(self):
        """Plays a video file from the start when the 'Get' button is clicked.
            Unused up till Version 1.1.0
        """
        self.time_label.config(text="00:00:00 / " + self.get_duration_str())
        self.play_video()
    
    def current_stats(self):
        # self.watched_videos.increment_duration_and_count(self.current_file, self.media_player.get_time())
        self.session_end = timeit.default_timer()
        self.show_session_stats(self.get_stats(), for_current=True)

    def delete_video(self, event=None):
        """Marks the currently playing video for deletion."""
        if self.current_file:
            self.deleter.mark_for_deletion(self.current_file, commit=True)
            self.show_marquee(f"Marked {self.current_file} for deletion")
            # Added Logging in deletion manager so No need to log here
            # self.logger.update_logs(f"[MARKED FOR DELETION]", self.current_file)

    def play_next(self, event=None):
        """
        Plays the next video in the playlist.
        Stops the current video if it's playing, selects the next video,
        sets it as the current file, and plays it.
        """
        if getattr(self, "_playing_lock", False):
            print("Already transitioning to next video.")
            return

        self._playing_lock = True
        try:
            if not self.video_files:
                showerror(self, "No Videos", "The video list is empty.")
                return

            if self.playing_video:
                self.stop()

            self.previous_file = self.current_file

            if self.random_select:
                self.select_random_video()
            else:
                self.select_sequential_videos()

            self.video_paused = False
            print(f"Now playing: {self.current_file}")
            self.play_video()

        except IndexError:
            self.current_file = None
            showerror(self, "Index Error", "No more videos to play.")
        except Exception as e:
            print(f"An Exception Occurred in play_next(): {e}")
            showerror(self, "Error", f"Failed to play next video: {e}")
        finally:
            self._playing_lock = False

    
    def play_previous(self, event=None):
        """
        Plays the previous video in the playlist.
        Stops the current video, swaps the current and previous file, and plays the previous one.
        """
        if getattr(self, "_playing_lock", False):
            print("Already transitioning between videos.")
            return

        self._playing_lock = True
        try:
            if self.playing_video:
                self.stop()

            if self.previous_file and os.path.exists(self.previous_file):
                if self.previous_file == self.current_file:
                    print("Previous file is same as current. Ignoring.")
                    return

                self.current_file, self.previous_file = self.previous_file, self.current_file
                print(f"Reverted to: {self.current_file}")
                self.play_video()
            else:
                showerror(self, "Error", "Previous file not available or missing.")
        except Exception as e:
            print(f"An error occurred in play_previous(): {e}")
            showerror(self, "Error", f"Could not play previous video: {e}")
        finally:
            self._playing_lock = False


    def get_duration_str(self):
        """
        Get the total duration of the current video in a human-readable format.

        Returns:
            str: A string representing the total duration of the current video in the format 'HH:MM:SS'.
        """
        if self.playing_video:
            total_duration = self.media_player.get_length()
            total_duration_str = str(timedelta(milliseconds=total_duration))[:-3]
            return total_duration_str
        return "00:00:00"
    
    def get_time_str(self, time_duration):
        """
        Convert a duration in milliseconds to a human-readable format.

        Args:
            time_duration (int): Duration in milliseconds.

        Returns:
            str: A string representing the duration in the format 'HH:MM:SS'.
        """
        time_str = str(timedelta(milliseconds=time_duration))[:-3]
        return time_str
    
    def get_video_files(self, folder_path):
        """
        NOT REQUIRED IF USING file_loader.py TO GET VIDEO_FILES

        Get a list of video files in the specified folder.
        Args:
            folder_path (str): The path to the folder containing video files.

        Returns:
            list: A list of paths to video files.
        """
        video_files = []
        for file in os.listdir(folder_path):
            if file.endswith(".mp4") or file.endswith(".mkv") or file.endswith(".avi") or file.endswith(".m4v"):
                video_files.append(os.path.join(folder_path, file))
        return video_files

    def play_im_next(self, event=None):
        """
        Plays the immediate next video in the playlist.
        """
        if self.random_select:
            self.random_select = False
            current_index = self.video_files.index(self.current_file)
            self.video_index = current_index + 1 if current_index < len(self.video_files) else 0
            # self.after(50, self.play_next)
            self.play_next()
            self.random_select = True
        else:
            current_index = self.video_files.index(self.current_file)
            self.video_index = current_index + 1 if current_index < len(self.video_files) else 0
            self.play_next()
    
    def play_im_previous(self, event=None):
        """
        Plays the immediate next video in the playlist.
        """
        if self.random_select:
            self.random_select = False
            current_index = self.video_files.index(self.current_file) 
            self.previous_file = self.video_files[current_index - 1] if current_index > 0 else self.video_files[len(self.video_files) - 1]
            self.play_previous()
            self.random_select = True
        else:
            current_index = self.video_files.index(self.current_file)
            self.previous_file = self.video_files[current_index - 1] if current_index > 0 else self.video_files[len(self.video_files) - 1]
            self.play_previous()
        

    def play_video(self):
        """Starts loading and playing the video in a background thread."""
        def load_and_play():
            try:
                if self.loop_var.get() and hasattr(self, 'current_media'):
                    print("Looping: Seeking to start and replaying cached media.")
                    try:
                        self.media_player.set_time(0)
                        self.media_player.play()
                        self._on_video_loaded(self.previous_title)
                        self.after(220, lambda: self.redraw_progress_bar(self.total_duration))
                    except Exception as e:
                        print(f"Error during loop replay: {e}")
                
                if self.playing_video:
                    self.media_player.stop()
                    time.sleep(0.15)
                    
                if os.path.exists(self.current_file):
                    title = f"[{self.video_files.index(self.current_file) + 1} / {len(self.video_files)}] " + self.current_file.split("\\")[-1]
                    self.current_fingerprint = self.fingerprint_manager.get_index_hash_by_path(self.current_file)
                    self._release_current_media()
                    media = self.instance.media_new(self.current_file)
                    self.current_media = media
                    self._play_start_time = timeit.default_timer()
                    # media.parse_async()
                    self.media_player.set_media(media)
                    self.total_duration = int(self.media_player.get_length()) or 0
                    self.last_looped_file = self.current_file
                    self.previous_title = title
                    # self.last_pos_seconds = self.parse_last_position()
                    self.after(0, lambda: self._on_video_loaded(title))
                    self.after(220, lambda: self.redraw_progress_bar(self.total_duration))
                    # print(self.watch_history_logger.get_last_position(self.current_file))
                else:
                    print(f"The file Doesn't Exists: {self.current_file}")
                    self.logger.error_logs(f"File Not Found: {self.current_file}")
                    self.after(0, self.play_next)
            except Exception as e:
                print(f"An Exception Occurred in play_video: {e}")
                showerror(self, "Error", f"Error loading {self.current_file}: {e}")
                self.logger.error_logs(f"Error loading {self.current_file}: {e}")

        if hasattr(self, '_video_thread') and self._video_thread.is_alive():
            print("Video thread is already running. Waiting for it to finish.")
            return
        self._video_thread = threading.Thread(target=load_and_play, daemon=True)
        self._video_thread.start()
        
    def redraw_progress_bar(self, total_duration=None):
        """Redraw progress bar with precomputed metadata (no searching)."""
        if self.current_file in self.trimmed_segments:
            segments = self.trimmed_segments[self.current_file]
            metadata = self.trimmed_segments_metadata.get(self.current_file, {})
            self.progress_bar.set_trimmed_segments(segments, total_duration, metadata)
        try:
            if hasattr(self.progress_bar, 'set_last_position_from_history'):
                self.progress_bar.set_last_position_from_history(file=self.current_file, total_duration=total_duration)
        except Exception:
            pass


    def _release_current_media(self):
        """
        Releases the current media player and media instance.
        Also handles potential VLC operation timeouts by creating a new VLC instance.
        """
        try:
            if hasattr(self, 'media_player'):
                self._saved_volume = self.media_player.audio_get_volume()
                self._saved_mute_state = self.media_player.audio_get_mute()
                self._saved_playback_rate = self.media_player.get_rate()
            else:
                self._saved_volume = 100
                self._saved_mute_state = False
                self._saved_playback_rate = 1.0

            def vlc_operations():
                try:
                    if hasattr(self, 'media_player'):
                        self.media_player.stop()
                        self.media_player.set_media(None)
                    if hasattr(self, 'current_media') and self.current_media:
                        self.current_media.release()
                        self.current_media = None
                        print("Released current media.")
                except Exception as e:
                    print(f"Error in VLC operations: {e}")
            
            vlc_thread = threading.Thread(target=vlc_operations, daemon=True)
            vlc_thread.start()
            vlc_thread.join(timeout=2)
            
            if vlc_thread.is_alive():
                print("VLC operations timed out, forcing continue...")
                try:
                    self.media_player = None
                    self.current_media = None
                    self.instance = vlc.Instance("--aout=directsound", '--avcodec-hw=dxva2', '--file-caching=4000')
                    self._create_new_player()
                    print("Created a fresh VLC instance after timeout.")

                    if hasattr(self, '_saved_volume'):
                        self.media_player.audio_set_volume(self._saved_volume)
                    if hasattr(self, '_saved_mute_state') and self._saved_mute_state:
                        self.media_player.audio_toggle_mute()
                    if hasattr(self, '_saved_playback_rate'):
                        self.media_player.set_rate(self._saved_playback_rate)

                except Exception as e:
                    print(f"Error while forcing new VLC instance: {e}")
                    self.logger.error_logs(f"Error while forcing new VLC instance: {e}")
                
        except Exception as e:
            print(f"Error during media release: {e}")
            self.logger.error_logs(f"Error during media release: {e}")
        time.sleep(0.15)

    def fast_forward(self, event=None):
        """
        Fast-forwards the currently playing video by 10 seconds.
        """
        if self.playing_video:
            self.forward_counts += 1
            self.segment_forward += 1
            current_time = self.media_player.get_time() + 10000
            current_time_str = str(timedelta(milliseconds=current_time))[:-3]
            self.media_player.set_time(current_time)
            self.show_marquee(f"{current_time_str} / {self.total_duration_str}")
            self.progress_bar.update_progress()
            
    def toggle_mute(self, event=None):
        """Toggle mute/unmute for the media player."""
        if self.media_player:
            is_muted = self.media_player.audio_get_mute()
            self.media_player.audio_toggle_mute()
            self.show_marquee("🔇Muted" if not is_muted else "🔊 Unmuted")
            self.volume_bar.toggle_mute()

    def toggle_fast_trim(self, event=None, value=None):
        """Toggle fast trim mode on/off, with warning when disabling."""
        current_state = self.fast_trim.get() if value is None else value

        if current_state:
            confirm = askyesno(
                self,
                "Warning",
                "Disabling Fast Trim will switch to re-encode mode.\n\n"
                "This makes trimming very slow but more accurate.\n\n"
                "Do you want to continue?"
            )
            if not confirm:
                self.fast_trim.set(True)
                return

            self.fast_trim.set(False)
        else:
            self.fast_trim.set(True)

        if self.fast_trim.get():
            state = "enabled (copy mode, faster but less precise)"
        else:
            state = "disabled (re-encode mode, slower but accurate)"

        self.show_marquee(f"Fast Trim {state}")
        # self.logger.update_logs(f"[FAST TRIM] Now {state}")

    def rewind(self, event=None):
        """
        Rewinds the currently playing video by 5 seconds.
        """
        if self.playing_video:
            self.prev_counts += 1
            self.segment_prev += 1
            current_time = max(self.media_player.get_time() - 5000, 0)
            self.media_player.set_time(current_time)
            self.show_marquee(f"{self.current_time_str} / {self.total_duration_str}")
            self.progress_bar.update_progress()

    def pause_video(self, event=None):
        """
        Pauses or resumes playback of the currently playing video.
        Toggles between pause and resume based on the current playback state.
        """
        if self.playing_video:
            if self.video_paused:
                self._play_start_time = timeit.default_timer()
                self.media_player.play()
                self.video_paused = False
                self.pause_button.config(text="⏸️ Pause")
                self.drag_bar.config(bg=Colors.PLAIN_BLACK) if not self.minimized else self.drag_bar.config(bg=Colors.HEADER_COLOR_RED)
            else:
                if self._play_start_time is not None:
                    self._total_play_time += timeit.default_timer() - self._play_start_time
                    self._play_start_time = None
                self.media_player.pause()
                self.video_paused = True
                self.pause_button.config(text="⏯️ Resume")
                self.drag_bar.config(bg=Colors.ORANGE)

    def stop(self, event=None):
        """
        Stops playback of the currently playing video.
        Logs the watch history before stopping, using real elapsed time.
        """
        if self.playing_video:
            # self.record_segment()
            if self._play_start_time is not None:
                self._total_play_time += timeit.default_timer() - self._play_start_time
                self._play_start_time = None
            total_watched = self.calculate_total_watched()
            duration_watched = self.get_time_str(total_watched)
            total_duration = self.get_duration_str()
            last_position = self.get_time_str(self.media_player.get_time())
            # print(f"Real Elapsed Time: {duration_watched}")
            self._release_current_media()
            self._total_play_time = 0
            
            fingerprint = self.current_fingerprint
            # if hasattr(self, 'fingerprint_manager'):
            #     fingerprint = self.fingerprint_manager.get_index_hash_by_path(self.current_file)

            self.watch_history_logger.log_watch_history(
                self.current_file, total_duration, duration_watched, last_position, fingerprint
            )
            self.watched_videos.increment_duration_and_count(self.current_file, total_watched)
            self.media_player.stop()
            self.playing_video = False
        self.time_label.config(text="00:00:00 / " + self.get_duration_str())

    def calculate_total_watched(self):
        """
        Calculate the total watched time (milliseconds) based on play time only.
        """
        return int(self._total_play_time * 1000)

    def set_video_position_percentage(self, value):
        """
        Sets the playback position of the currently playing video based on the provided value.

        Args:
            value (float): The value representing the desired playback position as a percentage.
                        Value should be between 0 and 100.
        """
        if self.playing_video:
            total_duration = self.media_player.get_length()
            position = int((float(value) / 100) * total_duration)
            self.media_player.set_time(position)

    def set_video_position(self, new_time_in_seconds):
        """
        Takes seconds instead of percentage
        """
        if self.playing_video:
            self.media_player.set_time(int(new_time_in_seconds * 1000))

    def update_video_progress(self):
        """
        Updates the progress of the currently playing video.
        Updates the time label with the current playback time and total duration.
        """
        if self.playing_video and not self.video_paused:
            self.total_duration = int(self.media_player.get_length())
            current_time = self.media_player.get_time()

            # if total_duration - current_time <= 1000:
            #     self.playing_video = False
            # print(current_time, total_duration)

            # the following lines are commented inorder to avoid lag in the video which is caused by progress_bar
            # progress_percentage = (current_time / total_duration) * 100
            # self.progress_bar.set(progress_percentage)

            self.current_time_str = str(timedelta(milliseconds=current_time))[:-3]
            self.total_duration_str = str(timedelta(milliseconds=self.total_duration))[:-3]
            self.time_label.config(text=f"{self.current_time_str} / {self.total_duration_str}")
            # print(total_duration, current_time)
            # if total_duration - current_time <= 500 and (total_duration != 0 or not self.video_paused):
            # if total_duration - current_time <= 500 and (total_duration != 0):
                # print(total_duration, current_time)
                # return
                # return
            self.progress_bar.update_progress()
        self.after(250, self.update_video_progress)

    def parse_last_position(self):
        last_pos_str = self.watch_history_logger.get_last_position(self.current_file)
        if last_pos_str:
            try:
                h, m, s = [int(float(x)) for x in last_pos_str.split(":")]
                last_pos_seconds = h * 3600 + m * 60 + s
                if 0 < last_pos_seconds < self.total_duration:
                    return last_pos_seconds
            except Exception as e:
                print(f"Error parsing last position: {e}")
                return 0
        
    
    def seconds_to_hhmmss(self, seconds, safe_for_filename=True):
        hours = int(seconds) // 3600
        minutes = (int(seconds) % 3600) // 60
        secs = int(seconds) % 60
        if safe_for_filename:
            return f"{hours}h{minutes}m{secs}s"
        else:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def get_video_resolution(self):
        try:
            video_track = self.media_player.video_get_track()
            if video_track == -1:
                return "Unknown"
            width = self.media_player.video_get_width()
            height = self.media_player.video_get_height()
            if width > 0 and height > 0:
                return f"{width}x{height}"
            return "Unknown"
        except Exception as e:
            print(f"[Resolution Error] {e}")
            return "Unknown"

    def get_stats(self):
        """
        Retrieves statistics about watched videos, including total duration watched and count.
        Returns the statistics sorted by duration in descending order.

        Returns:
            list: A list of dictionaries containing statistics for watched videos.
                Each dictionary contains keys 'File Name', 'Duration Watched', 'Count', and 'Folder'.
        """
        sorted_by_duration = dict(sorted(self.watched_videos.items(), key=lambda x: x[1]["duration"], reverse=True))
        watched_stats = [{"File Name": key.split("\\")[-1], "Duration Watched": self.get_time_str(value["duration"]), \
                          "Count": value["count"], "Folder": key.rsplit("\\", 1)[0]} for key, value in sorted_by_duration.items()]
        return watched_stats
    

    def handle_error(self, event):
        print("Error occurred while playing the media.")
        self.destroy()
    
    def show_session_stats(self, video_data, session_start=timeit.default_timer(), for_current=False):
        """
        Displays statistics for watched videos in a separate window.

        Args:
            video_data (list): A list containing statistics for watched videos.
                            Each element in the list is a dictionary with keys 'File Name', 'Duration Watched', 'Count', and 'Folder'.
        """
        start = session_start if self.session_start is None else self.session_start
        session_time = self.session_end-start
        # master = self.master
        if not for_current:
            if hasattr(self, 'media_player'):
                self.media_player.stop()
                self.media_player.release()
            if hasattr(self, 'instance'):
                self.instance.release()
            self._unbind_keys()
            self.destroy()
            self.quit()
            for attr in list(vars(self)):
                setattr(self, attr, None)
        root = tk.Tk()
        VideoStatsApp(root, REPORTS_FOLDER, video_data, int(session_time), fg=Colors.PLAIN_WHITE, bg=Colors.PLAIN_BLACK, for_current=for_current)
        root.mainloop()
    
    def center_window(self):
        """
        Center the Window with Respect to the Screen.
        """
        window_width = 1000
        window_height = 600

        position_right = int(self.winfo_screenwidth() / 2 - window_width / 2)
        position_down = int(self.winfo_screenheight() / 2 - window_height / 2)

        self.geometry("+{}+{}".format(position_right, position_down))

    def print_sessions_stats(self):
        pass

    def open_category_manager(self, event=None):
        """Open the category manager window as a modal dialog."""

        was_playing = not self.video_paused
        was_topmost = self.attributes("-topmost")

        if was_playing:
            self.pause_video()

        if was_topmost:
            self.attributes("-topmost", False)

        try:
            category_window = CategoryWindow(self, 
                                             self.current_file, 
                                             category_manager=self.category_manager, 
                                             fingerprint_manager=self.fingerprint_manager)
            category_window.lift()
            category_window.focus_force()
            self.wait_window(category_window)
            self.category_manager._load_entries()
        finally:
            if was_playing:
                self.pause_video()
            if was_topmost:
                self.attributes("-topmost", True)

        # self.pause_video(event=event)

    def mark_start(self, event=None):
        try:
            if not os.path.exists(VIDEO_SNIPPETS_FOLDER):
                showerror(self, "Snippets Folder Doesn't Exist", "The path for storing snippets doesn't exists.")
                self.logger.error_logs(f"Error {VIDEO_SNIPPETS_FOLDER} doesn't exists.")
                return
            ms = self.media_player.get_time()
            self.trim_start = ms
            self.show_marquee(f"Start marked at {self.get_time_str(ms)}")
            self.time_label.config(fg=Colors.PLAIN_RED)
        except Exception as e:
            showerror(self,"Trim Error", f"Could not mark start:\n{e}")
            self.logger.error_logs(f"Error marking start for trimming: {e}")

    def mark_end(self, event=None):
        try:
            if self.trim_start is None or not self.current_file:
                return
            end_ms = self.media_player.get_time()

            start_ms, end_ms = sorted([self.trim_start, end_ms])

            duration_ms = self.media_player.get_length()
            if start_ms >= duration_ms or end_ms > duration_ms:
                showwarning(self, "Trim", "Invalid positions or video ended. Operation canceled.")
                self.reset_trim()
                return

            start_s = start_ms / 1000.0
            end_s = end_ms / 1000.0

            fast_mode = self.fast_trim.get()

            threading.Thread(
                target=self._trim_worker,
                args=(start_ms, end_ms, fast_mode),
                daemon=True
            ).start()

            self.trim_start = None
            self.time_label.config(fg=Colors.PLAIN_WHITE)

            self.trimmed_segments.setdefault(self.current_file, []).append((start_s, end_s))
            
            if self.current_file not in self.trimmed_segments_metadata:
                self.trimmed_segments_metadata[self.current_file] = {}
            
            self.trimmed_segments_metadata[self.current_file][(start_s, end_s)] = {"notes": ""}

            self.after(200, lambda: self.redraw_progress_bar(self.total_duration))

        except Exception as e:
            showerror(self, "Trim Error", f"Could not mark end:\n{e}")
            self.reset_trim()
            self.logger.error_logs(f"Error marking end for trimming: {e}")

    def reset_trim(self):
        self.trim_start = None

    def _trim_worker(self, start_ms, end_ms, fast_mode=True):
        self.active_trims += 1
        try:
            start_s = start_ms / 1000.0
            duration_s = (end_ms - start_ms) / 1000.0
            base_name = os.path.splitext(os.path.basename(self.current_file))[0]
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            out_file = f"{base_name[:100]}_{self.seconds_to_hhmmss(start_s)}_to_{self.seconds_to_hhmmss(start_s+duration_s)}.mp4"
            out_path = os.path.join(VIDEO_SNIPPETS_FOLDER, out_file)

            if fast_mode:
                cmd = [
                    'ffmpeg', '-y', '-ss', str(start_s), '-t', str(duration_s),
                    '-i', self.current_file, '-c', 'copy', out_path
                ]
            else: 
                cmd = [
                    'ffmpeg', '-y', '-ss', str(start_s), '-t', str(duration_s),
                    '-i', self.current_file,
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                    '-c:a', 'aac',
                    out_path
                ]

            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            if self.winfo_exists():
                self.after(0, lambda: showinfo(
                    self, "Trim Complete",
                    f"Saved clipped video from {self.seconds_to_hhmmss(start_s)} "
                    f"to {self.seconds_to_hhmmss(start_s+duration_s)}\nPath: {out_path}"
                ))
            self.show_marquee(f"Trimmed video saved: {out_path}")

            self.logger.update_logs(
                f"[TRIMMED VIDEO] {self.current_file} "
                f"from {self.seconds_to_hhmmss(start_s)} to {self.seconds_to_hhmmss(start_s+duration_s)}",
                out_path
            )
            self.category_manager.add_to_category("Trimmed Videos", out_path)
            self.snippets_manager.record_trim(
                original=self.current_file,
                output=out_path,
                start_s=start_s,
                end_s=start_s + duration_s,
                mode=fast_mode,
                total_duration_s=duration_s,
                resolution=self.get_video_resolution(),
                file_size=os.path.getsize(out_path),
                video_format=os.path.splitext(out_path)[1][1:],
                notes=""
            )
            self.associations_manager.add_association(
                source_file=self.current_file,
                target_file=out_path,
                association_type="related"
            )

        except FileNotFoundError:
            self.logger.error_logs("ffmpeg not found. Please install ffmpeg and ensure it's in your PATH.")
            showerror(self, "Trim Error", "ffmpeg not found. Please install ffmpeg and ensure it's in your PATH.")
        except Exception as e:
            self.logger.error_logs(f"Unexpected error during trimming: {e}")
            showerror(self, "Trim Error", f"Unexpected error:\n{e}")
        finally:
            self.active_trims -= 1
            self.trimmed = True

    def increase_sub_delay(self, event=None):
        self.subtitle_delay += 50_000  # 0.05 seconds
        self.media_player.video_set_spu_delay(self.subtitle_delay)
        print(f"Subtitle delay: +{self.subtitle_delay / 1_000_000:.3f}s")
        self.show_marquee(f"Subtitle delay: +{self.subtitle_delay / 1_000_000:.3f}s")

    def decrease_sub_delay(self, event=None):
        self.subtitle_delay -= 50_000
        self.media_player.video_set_spu_delay(self.subtitle_delay)
        print(f"Subtitle delay: {self.subtitle_delay / 1_000_000:.3f}s")
        self.show_marquee(f"Subtitle delay: -{self.subtitle_delay / 1_000_000:.3f}s")


    def toggle_subtitles(self, event=None):
        if self.subtitles_visible:
            self.last_subtitle_id = self.media_player.video_get_spu()
            self.media_player.video_set_spu(-1)
            print("Subtitles hidden")
            self.show_marquee("Subtitles hidden")
        else:
            track_list = self.media_player.video_get_spu_description()
            if track_list:
                valid_ids = [id for id, name in track_list if id != -1]
                if hasattr(self, "last_subtitle_id") and self.last_subtitle_id in valid_ids:
                    self.media_player.video_set_spu(self.last_subtitle_id)
                    chosen = [name for (id, name) in track_list if id == self.last_subtitle_id][0]
                    print(f"Subtitles shown: {chosen}")
                    self.show_marquee(f"Subtitles shown: {chosen}")
                else:
                    first_id, first_name = valid_ids[0], [name for id, name in track_list if id == valid_ids[0]][0]
                    self.media_player.video_set_spu(first_id)
                    print(f"Subtitles shown: {first_name}")
                    self.show_marquee(f"Subtitles shown: {first_name}")
            else:
                print("No subtitle tracks available to show")
                self.show_marquee("No subtitle tracks.")
        self.subtitles_visible = not self.subtitles_visible

    def add_subtitle(self, event=None):
        from pathlib import Path

        def path_to_uri(path):
            return Path(path).absolute().as_uri()
        
        if not self.current_file:
            showwarning("Warning", "Please open a media file first!")
            return
            
        current_folder = os.path.dirname(self.current_file)

        subtitle_file = askopenfilename(
            parent=self,
            title="Select Subtitle File",
            initialdir=current_folder, 
            filetypes=[
                ("Subtitle files", "*.srt *.vtt *.ass *.ssa *.sub"),
                ("All files", "*.*")
            ]
        )
        
        if subtitle_file:
            try:
                print(subtitle_file)
                self.media_player.add_slave(0, path_to_uri(subtitle_file), True)
                filename = os.path.basename(subtitle_file)
                showinfo(self, "Success", f"Subtitle loaded: {filename}")
            except Exception as e:
                showerror(self, "Error", f"Failed to load subtitle: {str(e)}")
    
    def next_subtitle_track(self, event=None):
        tracks = self.media_player.video_get_spu_description()
        if not tracks:
            print("No subtitles loaded.")
            return

        current = self.media_player.video_get_spu()
        ids = [id for id, name in tracks if id != -1]

        if current in ids:
            current_index = ids.index(current)
            next_index = (current_index + 1) % len(ids)
        else:
            next_index = 0

        self.media_player.video_set_spu(ids[next_index])
        print(f"Switched to subtitle: {tracks[next_index][1]}")
        self.show_marquee(f"Subtitle: {tracks[next_index][1]}")

    def next_audio_track(self, event=None):
        """Cycle through available audio tracks if multiple exist."""
        tracks = self.media_player.audio_get_track_description()
        if not tracks:
            print("No audio tracks available.")
            self.show_marquee("No audio tracks.")
            return

        current = self.media_player.audio_get_track()
        ids = [id for id, name in tracks if id != -1]
        print(len(ids))

        if not ids:
            print("No valid audio tracks found.")
            self.show_marquee("No valid audio tracks.")
            return

        if current in ids:
            current_index = ids.index(current)
            next_index = (current_index + 1) % len(ids)
        else:
            next_index = 0

        self.media_player.audio_set_track(ids[next_index])
        chosen_name = [name for id, name in tracks if id == ids[next_index]][0]
        print(f"Switched to audio: {chosen_name}")
        self.show_marquee(f"Audio: {chosen_name}")


    def toggle_audio(self, event=None):
        """Toggle between original and last audio track."""
        if not hasattr(self, "last_audio_id"):
            self.last_audio_id = None

        current = self.media_player.audio_get_track()
        tracks = self.media_player.audio_get_track_description()

        if not tracks:
            print("No audio tracks available to toggle.")
            self.show_marquee("No audio tracks.")
            return

        ids = [id for id, name in tracks if id != -1]

        if current != -1:
            self.last_audio_id = current
            self.media_player.audio_set_track(-1)
            print("Audio muted/disabled")
            self.show_marquee("Audio disabled")
        else:
            if self.last_audio_id and self.last_audio_id in ids:
                self.media_player.audio_set_track(self.last_audio_id)
                chosen = [name for (id, name) in tracks if id == self.last_audio_id][0]
                print(f"Audio restored: {chosen}")
                self.show_marquee(f"Audio restored: {chosen}")
            elif ids:
                self.media_player.audio_set_track(ids[0])
                chosen = [name for (id, name) in tracks if id == ids[0]][0]
                print(f"Audio restored: {chosen}")
                self.show_marquee(f"Audio: {chosen}")

    

if __name__ == "__main__":
    import sys
    import tkinter as tk
    dummy_video_files = ["/sample1.mp4", "/sample2.mkv", "/sample3.avi"]
    app = MediaPlayerApp(current_file="/sample1.mp4", video_files=dummy_video_files, random_select=False)
    # app.play_video = "sample.mp4"
    # app.update_video_progress = lambda: None
    app.update_video_progress()
    app.mainloop()
