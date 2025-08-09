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
from deletion_manager import DeletionManager
from favorites_manager import FavoritesManager
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
from video_progress_bar import VideoProgressBar
from video_stats import VideoStatsApp
from volume_bar import VolumeBar
from watch_dictionary import WatchDict
from watch_history_logger import WatchHistoryLogger
from snippets_manager import SnippetsManager
from notes_manager import NotesManager
from custom_messagebox import askopenfilename, showinfo, showwarning, showerror, askyesno


class MediaPlayerApp(tk.Toplevel):
    def __init__(self, video_files, current_file=None, random_select=True, video_path=None, watch_history_csv=WATCHED_HISTORY_LOG_PATH,
                  parent=None, category_manager=None, favorites_manager=None, deletion_manaager=None,
                  notes_manager=None, snippets_manager=None):
        super().__init__(parent)
        self._get_history_csvfile(watch_history_csv)
        self.favorites_manager = favorites_manager or FavoritesManager()
        self.logger = LogManager(LOG_PATH)
        self.deleter = deletion_manaager or DeletionManager(self.favorites_manager)
        self.deleter.set_parent_window(self)
        self.category_manager = category_manager or CategoryManager()
        self.watch_history_logger = WatchHistoryLogger(self.watch_history_csv)
        self.snippets_manager = snippets_manager or SnippetsManager()
        self.notes_manager = notes_manager or NotesManager()

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
        self.autoplay = True
        self.trim_start = None
        self.loop_video = False
        # self.input_path = None

        self.random_select = random_select
        self.video_index = 0 if not current_file else video_files.index(current_file)
        
        self.current_time_str = "00:00:00"
        self.total_duration_str = "00:00:00"
        
        self._keybinding()
        self.initialize_player(video_files, video_path, cur_file=current_file)
        

    def _get_history_csvfile(self, watch_history_csv):
        try:
            # You Can Add a Folder in file_info.txt as default One
            with open(FILES_FOLDER + "file_info.txt", "r") as file:
                reader = file.readline().strip()
            if reader:
                self.watch_history_csv = reader
            else:
                self.watch_history_csv = watch_history_csv
        except FileNotFoundError:
            self.watch_history_csv = watch_history_csv
    
    def _on_close(self, event=None):
        self.session_end = timeit.default_timer()
        self.stop()  # Call the stop method when the window is closed
        # tk.Tk.quit(self)
        self.show_seassion_stats(self.get_stats())
        if hasattr(self, 'media_player'):
            self.media_player.stop()
            self.media_player.release()
        if hasattr(self, 'instance'):
            self.instance.release()
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
        # self.fav_csv = FILES_FOLDER +"Favorites.csv"
        self.instance = vlc.Instance()
        # self.media_player = self.instance.media_player_new()

        # self.media_player.event_manager().event_attach(vlc.EventType.MediaPlayerEncounteredError, self.handle_error)
        # self.media_player.event_manager().event_attach(
        #     vlc.EventType.MediaPlayerEndReached, self._on_video_end
        # )
        self._create_new_player()

        self.video_files = self.get_video_files(folder_path) if folder_path is not None else video_files
        self.current_file = cur_file
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
        # Schedule play_next or loop on the main thread
        if self.loop_video:
            self.after(50, self.stop)
            self.after(200, self.play_video)
        elif self.autoplay:
            # self.current_media.release()
            self.after(200, self.play_next)


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

        self.media_canvas = tk.Canvas(self, bg="black", width=900, height=400, highlightthickness=0)
        self.media_canvas.pack(pady=(0, 0), fill=tk.BOTH, expand=True)

        control_frame = tk.Frame(self, bg="black")
        control_frame.pack(pady=(5, 0), fill=tk.X)

        self.feedback_label = tk.Label(
            self,
            textvariable=self.feedback_var,
            font=("Segoe UI", 18, "bold"),
            bg="black",
            fg="white"
        )
    

        def style_btn(btn, bg, fg, activebg=None, activefg=None):
            btn.config(
                bg=bg,
                fg=fg,
                relief=tk.FLAT,
                bd=0,
                font=("Segoe UI", 12, "bold"),
                activebackground=activebg or bg,
                activeforeground=activefg or fg,
                cursor="hand2",
                padx=5,
                pady=0
            )

        self.current_stats_button = tk.Button(
            control_frame, text="Current Stats", command=self.current_stats
        )
        style_btn(self.current_stats_button, "white", "black", "#e0e0e0")

        self.prev_button = tk.Button(
            control_frame, text="Previous", command=self.play_previous
        )
        style_btn(self.prev_button, "red", "white", "#b30000")

        self.rewind_button = tk.Button(
            control_frame, text="⏪", command=self.rewind
        )
        style_btn(self.rewind_button, "red", "white", "#b30000")

        self.play_button = tk.Button(
            control_frame, text="▶️ Play", command=self.play_video
        )
        style_btn(self.play_button, "black", "white", "#222")

        self.pause_button = tk.Button(
            control_frame, text="⏸️ Pause", command=self.pause_video
        )
        style_btn(self.pause_button, "#FF9800", "white", "#e65100")

        self.fast_forward_button = tk.Button(
            control_frame, text="⏩", command=self.fast_forward
        )
        style_btn(self.fast_forward_button, "red", "white", "#b30000")

        self.next_button = tk.Button(
            control_frame, text="Next", command=self.play_next
        )
        style_btn(self.next_button, "red", "white", "#b30000")

        self.category_button = tk.Button(
            control_frame, text="☰", command=self.open_category_manager
        )
        style_btn(self.category_button, "purple", "white", "#4B0082")

        self.autoplay_button = tk.Button(
            control_frame, text="Auto: ON", command=self.toggle_autoplay
        )
        style_btn(self.autoplay_button, "#00C853", "white", "#1565C0")

        self.loop_button = tk.Button(
            control_frame, text="⟲", command=self.toggle_loop
        )
        style_btn(self.loop_button, "#000000", "white", "#37474F")

        for btn in [
            self.current_stats_button, self.prev_button, self.rewind_button,
            self.play_button, self.pause_button, self.fast_forward_button,
            self.next_button, self.category_button, self.autoplay_button, self.loop_button
        ]:
            btn.pack(side=tk.LEFT, padx=3, pady=2)

        self.time_label = tk.Label(
            control_frame,
            text="00:00:00 / 00:00:00",
            font=("Segoe UI", 13, "bold"),
            fg="white",
            bg="black",
            padx=10
        )
        self.time_label.pack(side=tk.RIGHT, padx=10, pady=0)

        self.progress_bar = VideoProgressBar(
            self, self.set_video_position, bg=self.bg_color, highlightthickness=0
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=8)

        self.volume_bar = VolumeBar(self, self.media_player, fg=self.fg_color, bg=self.bg_color)
        self.volume_bar.pack(side=tk.RIGHT, padx=5, pady=0)

        def on_enter(e): e.widget.config(bg="#444")
        def on_leave(e):
            txt = e.widget["text"]
            if txt in ["Previous", "⏪", "⏩", "Next"]:
                e.widget.config(bg="red")
            elif txt == "Current Stats":
                e.widget.config(bg="white")
            elif txt == "Categories":
                e.widget.config(bg="purple")
            elif txt == "Fav +":
                e.widget.config(bg="white")
            elif txt == "Fav -":
                e.widget.config(bg="black")
            elif "Pause" in txt or "Resume" in txt:
                e.widget.config(bg="#FF9800")
            elif "Auto" in txt:
                e.widget.config(bg="#00C853") if self.autoplay else e.widget.config(bg="#000000")
            elif "⟲" in txt:
                e.widget.config(bg="#000000") if not self.loop_video else e.widget.config(bg="#00C853")
            elif "☰" in txt:
                e.widget.config(bg="purple")
            else:
                e.widget.config(bg="black")

        for btn in [
            self.current_stats_button, self.category_button, self.prev_button, self.rewind_button,
            self.play_button, self.pause_button, self.fast_forward_button,
            self.next_button, self.autoplay_button, self.loop_button
        ]:
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

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
            bg="#00C853" if self.autoplay else "#000000"
        )
        self.show_marquee("Autoplay is ON" if self.autoplay else "Autoplay is OFF")

    def toggle_always_on_top(self, event=None):
        """Toggle whether the window stays on top of other windows."""
        is_on_top = self.attributes("-topmost")
        self.attributes("-topmost", not is_on_top)
        # self.drag_label.pack(side=tk.LEFT, padx=0, pady=0)
        # self.drag_bar.config(height=5 if not is_on_top else 0)
        if not is_on_top:
            self.drag_bar.config(height=5, bg=Colors.HEADER_COLOR_RED)
        else:
            self.drag_bar.config(height=0, bg=Colors.PLAIN_BLACK)
        
        self.toggle_shorten_window(event=event)
        self.show_marquee("Always on top: " + ("ON" if not is_on_top else "OFF"))

    def toggle_shorten_window(self, event=None):
        if not self.minimized:
            if self.attributes("-fullscreen"):
                self.attributes("-fullscreen", False)
                self.update_idletasks()
            self.prev_geometry = self.geometry()
            self.toggle_controls_visibility(False)

            self.overrideredirect(True)

            screen_width = self.winfo_screenwidth()
            new_width, new_height = 450, 270
            x = screen_width - (new_width + 20)
            y = 35
            self.geometry(f"{new_width}x{new_height}+{x}+{y}")

            self.minimized = True
        else:
            self.overrideredirect(False)
            if self.prev_geometry:
                self.geometry(self.prev_geometry)
            self.toggle_controls_visibility(True)

            self.minimized = False

    
    def toggle_loop(self, event=None):
        self.loop_video = not self.loop_video
        if self.loop_video:
            self.loop_button.config(bg="#00C853")
        else:
            self.loop_button.config(bg="#000000")
        self.show_marquee("Looping is ON" if self.loop_video else "Looping is OFF")

    def _keybinding(self):
        """
        All the keys Shortcuts binded into the player
        """
        self.bind("<Shift-KeyPress-Left>", self.play_previous)
        self.bind("<KeyPress-Left>", self.rewind)
        self.bind("<KeyPress-space>", self.pause_video)
        self.bind("<KeyPress-Right>", self.fast_forward)
        self.bind("<Shift-KeyPress-Right>", self.play_next)
        self.bind("<KeyPress-n>", self.play_next)
        self.bind("<KeyPress-N>", self.play_next)
        self.bind("<KeyPress-m>", self.toggle_mute)
        self.bind("<KeyPress-M>", self.toggle_mute)
        self.bind("<KeyPress-Up>", self.volume_increase)
        self.bind("<KeyPress-Down>", self.volume_decrease)
        self.bind("<KeyPress-f>", self.toggle_fullscreen)
        self.bind("<KeyPress-F>", self.toggle_fullscreen)
        self.bind("<Shift-KeyPress-S>", self.save_screenshot)
        self.bind("<Shift-KeyPress-s>", self.save_screenshot)
        self.bind("<Control-f>", self.add_to_favorites)
        self.bind("<Control-F>", self.add_to_favorites)
        self.bind("<Control-d>", self.remove_from_favorites)
        self.bind("<Control-D>", self.remove_from_favorites)
        self.bind("<KeyPress-x>", self.cycle_playback_speed)
        self.bind("<KeyPress-X>", self.cycle_playback_speed)
        self.bind("<Control-Right>", self.play_im_next)
        self.bind("<Control-Left>", self.play_im_previous)
        self.bind("<Delete>", self.delete_video)
        self.bind('<Control-Shift-Delete>', self.remove_from_deletion)
        self.bind("<Shift-KeyPress-a>", self.open_category_manager)
        self.bind("<Shift-KeyPress-A>", self.open_category_manager)
        self.bind("<KeyPress-a>", self.toggle_autoplay)
        self.bind("<KeyPress-A>", self.toggle_autoplay)
        self.bind("<Alt-t>", self.toggle_always_on_top)
        self.bind("<Alt-T>", self.toggle_always_on_top)
        self.bind('<Control-S>', self.mark_start)
        self.bind('<Control-s>', self.mark_start)
        self.bind('<Control-E>', self.mark_end)
        self.bind('<Control-e>', self.mark_end)
        self.bind('<Shift-b>', self.add_subtitle)
        self.bind('<Shift-B>', self.add_subtitle)
        self.bind('<KeyPress-B>', self.toggle_subtitles)
        self.bind('<KeyPress-b>', self.toggle_subtitles)
        self.bind('<KeyPress-,>', self.decrease_sub_delay)
        self.bind('<KeyPress-.>', self.increase_sub_delay)
        self.bind('<Control-b>', self.next_subtitle_track)
        self.bind('<Control-B>', self.next_subtitle_track)
        self.bind('<KeyPress-l>', self.toggle_loop)
        self.bind('<KeyPress-L>', self.toggle_loop)
        self.bind('<Shift-KeyPress-n>', self.show_notes)
        self.bind('<Shift-KeyPress-N>', self.show_notes)
        self.bind('<Escape>', self._on_close)

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
            notes_window = NotesManagerGUI(self.notes_manager, snippets_manager=self.snippets_manager, parent=self, file_path=file_path)
            self.wait_window(notes_window.root)
        finally:
            if was_playing:
                self.pause_video()
            if was_topmost:
                self.attributes("-topmost", True)


    def _on_video_loaded(self, title):
        self.reset_values(segment_speed=self.segment_speed)
        self.reset_trim()

        self.title(title)
        self.media_player.set_hwnd(self.media_canvas.winfo_id())
        self.media_player.play()
        # self.set_playback_speed(self.segment_speed)
        self.show_marquee(f"Playing: {self.current_file}")
        self.session_start = timeit.default_timer() if self.session_start is None else self.session_start
        self.playing_video = True
        self.watched_videos.add_watch(self.current_file)
        self.progress_bar.set(0)

    def reset_values(self, segment_speed=None):
        self.playback_segments = []
        self.segment_start = 0
        self.segment_speed = 1.0 if segment_speed is None else segment_speed
        self.segment_forward = 0
        self.segment_prev = 0
        self.prev_counts = 0
        self.forward_counts = 0

    def cycle_playback_speed(self, event=None):
        """Cycles playback speed between 1x, 1.25x, 1.5x, 1.75x, and 2x."""
        if self.playing_video:
            speeds = [1.0, 1.25, 1.5, 1.75, 2.0]
            current_speed = self.media_player.get_rate()
            # Find the closest speed in the list
            try:
                index = next(i for i, s in enumerate(speeds) if abs(s - current_speed) < 0.1)
                new_index = (index + 1) % len(speeds)
            except StopIteration:
                new_index = 0  # Default to the first speed if current is unknown
            new_speed = speeds[new_index]
            self.set_playback_speed(new_speed)
            print(f"Playback Speed Changed to: {new_speed}x")
            self.show_marquee(f"Speed: {new_speed}x")

    def set_playback_speed(self, speed):
        if self.playing_video:
            self.record_segment()
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
        # Reset for next segment
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

    def volume_increase(self, event):
        """Increases the volume."""
        current_volume = self.media_player.audio_get_volume()
        new_volume = min(current_volume + 5, 200)  # Increase volume by 5%, up to 200%
        self.media_player.audio_set_volume(int(new_volume))
        self.show_marquee(f"Volume: {new_volume}")
        self.volume_bar.set(new_volume)  # Update volume bar

    def volume_decrease(self, event):
        """Decreases the volume."""
        current_volume = self.media_player.audio_get_volume()
        new_volume = max(current_volume - 5, 0)
        self.media_player.audio_set_volume(int(new_volume))
        self.show_marquee(f"Volume: {new_volume}")
        self.volume_bar.set(new_volume) 


    def select_file(self):
        """Plays a video file from the start when the 'Get' button is clicked.
            Unused up till Version 1.1.0
        """
        self.time_label.config(text="00:00:00 / " + self.get_duration_str())
        self.play_video()
    
    def current_stats(self):
        # self.watched_videos.increment_duration_and_count(self.current_file, self.media_player.get_time())
        self.session_end = timeit.default_timer()
        self.show_seassion_stats(self.get_stats(), for_current=True)

    def delete_video(self, event=None):
        """Marks the currently playing video for deletion."""
        if self.current_file:
            self.deleter.mark_for_deletion(self.current_file)
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
            self.play_previous()
        

    def play_video(self):
        """Starts loading and playing the video in a background thread."""
        def load_and_play():
            try:
                if self.loop_video and hasattr(self, 'current_media') and self.current_file == getattr(self, 'last_looped_file', None):
                    print("Looping: Seeking to start and replaying cached media.")
                    self.media_player.set_time(0)
                    self.media_player.play()
                    self._on_video_loaded(self.current_file)
                    return
            
                if self.playing_video:
                    self.media_player.stop()
                    # if hasattr(self, 'current_media'):
                    #     print("Releasing current media...")
                    #     self.current_media.release()
                    # if hasattr(self, 'media_player'):
                    #     self.media_player.release()
                    time.sleep(0.3)
                if os.path.exists(self.current_file):
                    title = f"[{self.video_files.index(self.current_file)} / {len(self.video_files)}] " + self.current_file.split("\\")[-1]
                    self._release_current_media()
                    media = self.instance.media_new(self.current_file)
                    self.current_media = media
                    media.parse_async()  # Preloads meta info
                    # self._create_new_player()
                    self.media_player.set_media(media)
                    self.last_looped_file = self.current_file
                    self.after(0, lambda: self._on_video_loaded(title))
                else:
                    print(f"The file Doesn't Exists: {self.current_file}")
                    self.logger.error_logs(f"File Not Found: {self.current_file}")
                    self.after(0, self.play_next)
            except Exception as e:
                print(f"An Exception Occurred in play_video: {e}")
                showerror(self, "Error", f"Error loading {self.current_file}: {e}")
                # self.after(0, lambda: self.show_marquee(f"Error loading {self.current_file}: {e}"))
        if hasattr(self, '_video_thread') and self._video_thread.is_alive():
            print("Video thread is already running. Waiting for it to finish.")
            return
        self._video_thread = threading.Thread(target=load_and_play, daemon=True)
        self._video_thread.start()

        # threading.Thread(target=load_and_play, daemon=True).start()

    def _release_current_media(self):
        try:
            if hasattr(self, 'media_player'):
                print("Releasing current media player...")
                self.media_player.stop()
                self.media_player.set_media(None)
            if hasattr(self, 'current_media') and self.current_media:
                print("Releasing current media...")
                self.current_media.release()
                self.current_media = None
                print("Released current media.")
        except Exception as e:
            print(f"Error during media release: {e}")
        time.sleep(0.25)

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
            
    def toggle_mute(self, event=None):
        """Toggle mute/unmute for the media player."""
        if self.media_player:
            is_muted = self.media_player.audio_get_mute()
            self.media_player.audio_toggle_mute()
            # Optionally show feedback
            self.show_marquee("🔇Muted" if not is_muted else "🔊 Unmuted")

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


    def pause_video(self, event=None):
        """
        Pauses or resumes playback of the currently playing video.
        Toggles between pause and resume based on the current playback state.
        """
        if self.playing_video:
            if self.video_paused:
                self.record_segment()
                self.media_player.play()
                self.video_paused = False
                self.pause_button.config(text="⏸️ Pause")
            else:
                self.record_segment()
                self.media_player.pause()
                self.video_paused = True
                self.pause_button.config(text="⏯️ Resume", bg="#FF9800")

    def stop(self, event=None):
        """
        Stops playback of the currently playing video.
        Logs the watch history before stopping, using real elapsed time.
        """
        if self.playing_video:
            self.record_segment()
            total_watched = self.calculate_total_watched()
            duration_watched = self.get_time_str(total_watched)
            total_duration = self.get_duration_str()
            print(f"Real Elapsed Time: {duration_watched}")
            self._release_current_media()

            skipped_time = (self.prev_counts * 4990) - (self.forward_counts * 9990)
            print(f"Skipped Time: {self.get_time_str(skipped_time)}")
            print(f"Prev Counts: {self.prev_counts}, Forward Counts: {self.forward_counts}")
            
            self.watch_history_logger.log_watch_history(self.current_file, total_duration, duration_watched)
            self.watched_videos.increment_duration_and_count(self.current_file, total_watched)
            self.media_player.stop()
            # self.media_player.release()
            self.playing_video = False
        self.time_label.config(text="00:00:00 / " + self.get_duration_str())

    def calculate_total_watched(self):
        """
        Calculate the total watched time (miliseconds) based on playback segments.
        """
        total = 0
        for seg in self.playback_segments:
            watched = (seg["end"] - seg["start"] + seg["prev_counts"] * 4990 - seg["forward_counts"] * 9990) / seg["speed"]
            total += watched
        return int(total)  # in ms

    def set_video_position(self, value):
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

    def update_video_progress(self):
        """
        Updates the progress of the currently playing video.
        Updates the time label with the current playback time and total duration.
        """
        if self.playing_video and not self.video_paused:
            total_duration = self.media_player.get_length()
            current_time = self.media_player.get_time()

            # if total_duration - current_time <= 1000:
            #     self.playing_video = False
            # print(current_time, total_duration)

            # the following lines are commented inorder to avoid lag in the video which is caused by progress_bar
            # progress_percentage = (current_time / total_duration) * 100
            # self.progress_bar.set(progress_percentage)

            self.current_time_str = str(timedelta(milliseconds=current_time))[:-3]
            self.total_duration_str = str(timedelta(milliseconds=total_duration))[:-3]
            self.time_label.config(text=f"{self.current_time_str} / {self.total_duration_str}")
            # print(total_duration, current_time)
            # if total_duration - current_time <= 500 and (total_duration != 0 or not self.video_paused):
            # if total_duration - current_time <= 500 and (total_duration != 0):
                # print(total_duration, current_time)
                # return
                # return
        self.after(200, self.update_video_progress)
    
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
    
    def show_seassion_stats(self, video_data, session_start=timeit.default_timer(), for_current=False):
        """
        Displays statistics for watched videos in a separate window.

        Args:
            video_data (list): A list containing statistics for watched videos.
                            Each element in the list is a dictionary with keys 'File Name', 'Duration Watched', 'Count', and 'Folder'.
        """
        if not for_current:
            self.destroy()
            self.quit()
        root = tk.Tk()
        start = session_start if self.session_start is None else self.session_start
        app = VideoStatsApp(root, REPORTS_FOLDER, video_data, int(self.session_end-start), fg=self.fg_color, bg=self.bg_color, for_current=for_current)
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
            category_window = CategoryWindow(self, self.current_file, category_manager=self.category_manager)
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
            # if not self.media_player.is_playing():
            #     return
            ms = self.media_player.get_time()
            self.trim_start = ms
            # showinfo(self, "Trim", f"Start marked at {ms/1000:.2f} seconds")
            self.show_marquee(f"Start marked at {self.get_time_str(ms)}")
            self.time_label.config(fg="red")
        except Exception as e:
            showerror(self,"Trim Error", f"Could not mark start:\n{e}")
            self.logger.error_logs(f"Error marking start for trimming: {e}")

    def mark_end(self, event=None):
        try:
            if self.trim_start is None or not self.current_file:
                return
            end_ms = self.media_player.get_time()
            if end_ms < self.trim_start:
                start_ms, end_ms = end_ms, self.trim_start
            else:
                start_ms, end_ms = self.trim_start, end_ms
                
            duration_ms = self.media_player.get_length()
            if start_ms >= duration_ms or end_ms > duration_ms:
                showwarning(self, "Trim", "Invalid positions or video ended. Operation canceled.")
                self.reset_trim()
                return

            # fast or accurate
            # choice = askquestion("Trimming Mode", "Do you want fast trimming (not frame-accurate)?\nChoose 'No' for accurate trimming.")
            # choice = askyesno(self, "Trimming Mode", "Do you want fast trimming (not frame-accurate)?\nChoose 'No' for accurate trimming.")
            # fast_mode = (choice == 'yes')
            fast_mode = (True)

            threading.Thread(
                target=self._trim_worker,
                args=(start_ms, end_ms, fast_mode),
                daemon=True
            ).start()
            self.trim_start = None
            self.time_label.config(fg=Colors.PLAIN_WHITE)

        except Exception as e:
            showerror(self, "Trim Error", f"Could not mark end or start trimming:\n{e}")
            self.reset_trim()
            self.logger.error_logs(f"Error marking end for trimming: {e}")

    def reset_trim(self):
        self.trim_start = None

    def _trim_worker(self, start_ms, end_ms, fast_mode=True):
        try:
            start_s = start_ms / 1000.0
            duration_s = (end_ms - start_ms) / 1000.0
            base_name = os.path.splitext(os.path.basename(self.current_file))[0]
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            out_file = f"{base_name[:100]}_{self.seconds_to_hhmmss(start_s)}_to_{self.seconds_to_hhmmss(start_s+duration_s)}.mp4"
            # out_file = f"{base_name}_{start_s}_to_{start_s+duration_s}.mp4"
            out_path = os.path.join(VIDEO_SNIPPETS_FOLDER, out_file)

            if fast_mode:
                cmd = [
                    'ffmpeg', '-y', '-ss', str(start_s), '-t', str(duration_s),
                    '-i', self.current_file, '-c', 'copy', out_path
                ]
            else:
                cmd = [
                    'ffmpeg', '-y', '-ss', str(start_s), '-t', str(duration_s),
                    '-i', self.current_file, '-c:v', 'libx264', '-c:a', 'aac', out_path
                ]

            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if self.winfo_exists():
                self.after(0, lambda: showinfo(self, "Trim Complete", 
                                           f"Saved clipped video from {self.seconds_to_hhmmss(start_s)} to {self.seconds_to_hhmmss(start_s+duration_s)}\nPath: {out_path}"))
            self.show_marquee(f"Trimmed video saved: {out_path}")
            self.logger.update_logs(
                f"[TRIMMED VIDEO] {self.current_file} from {self.seconds_to_hhmmss(start_s)} to {self.seconds_to_hhmmss(start_s+duration_s)}",
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
        except FileNotFoundError:
            self.logger.error_logs("ffmpeg not found. Please install ffmpeg and ensure it's in your PATH.")
            showerror(self, "Trim Error", "ffmpeg not found. Please install ffmpeg and ensure it's in your PATH.")
        # except subprocess.CalledProcessError:
        #     showerror(self, "Trim Failed", "An error occurred during trimming.")
        except Exception as e:
            self.logger.error_logs(f"Unexpected error during trimming: {e}")
            showerror(self, "Trim Error", f"Unexpected error:\n{e}")

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
            self.media_player.video_set_spu(-1)
            print("Subtitles hidden")
            self.show_marquee("Subtitles hidden")
        else:
            track_list = self.media_player.video_get_spu_description()
            if track_list:
                for (id, name) in track_list:
                    if id != -1:
                        self.media_player.video_set_spu(id)
                        print(f"Subtitles shown: {name}")
                        self.show_marquee(f"Subtitles shown: {name}")
                        break
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
    

if __name__ == "__main__":
    # for testing purposes
    import sys
    import tkinter as tk
    dummy_video_files = ["sample1.mp4", "sample2.mkv", "sample3.avi"]
    app = MediaPlayerApp(video_files=dummy_video_files, random_select=False)
    app.play_video = lambda: None
    # app.update_video_progress = lambda: None
    app.update_video_progress()
    app.mainloop()
