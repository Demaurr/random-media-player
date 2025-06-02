import os
import random
import threading
import time
import timeit
from datetime import timedelta

import tkinter as tk
# from tkinter import messagebox  # Remove this import

import vlc

from category_manager import CategoryManager
from category_window import CategoryWindow
from deletion_manager import DeletionManager
from favorites_manager import FavoritesManager
from logs_writer import LogManager
from player_constants import FILES_FOLDER, LOG_PATH, REPORTS_FOLDER, SCREENSHOTS_FOLDER, WATCHED_HISTORY_LOG_PATH
from video_progress_bar import VideoProgressBar
from video_stats import VideoStatsApp
from volume_bar import VolumeBar
from watch_dictionary import WatchDict
from watch_history_logger import WatchHistoryLogger
from custom_messagebox import showinfo, showwarning, showerror, askyesno  # Add this import


class MediaPlayerApp(tk.Tk):
    def __init__(self, video_files, current_file=None, random_select=True, video_path=None, watch_history_csv=WATCHED_HISTORY_LOG_PATH):
        super().__init__()
        self._get_history_csvfile(watch_history_csv)
        self.favorites_manager = FavoritesManager()
        self.logger = LogManager(LOG_PATH)
        self.deleter = DeletionManager()
        self.deleter.set_parent_window(self)  # Set parent window for message boxes
        self.category_manager = CategoryManager()
        self.watch_history_logger = WatchHistoryLogger(self.watch_history_csv)

        self.bg_color = "black"
        self.fg_color = "white"
        self.title("Media Player")
        self.geometry("1000x600")
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
    
    def _on_close(self):
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
        # self.watched_videos = {}
        self.watched_videos = WatchDict()
        self.feedback_var = tk.StringVar()
        self.feedback_label = None 
        
        
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
        # Schedule play_next on the main thread
        if self.autoplay:
            # self.current_media.release()
            self.after(200, self.play_next)


    def _create_widgets(self):
        """Creates the GUI elements for the media player with improved style and responsiveness."""
        self.media_canvas = tk.Canvas(self, bg="black", width=800, height=400, highlightthickness=0)
        self.media_canvas.pack(pady=(5, 0), fill=tk.BOTH, expand=True)

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
            control_frame, text="Autoplay: ON", command=self.toggle_autoplay
        )
        style_btn(self.autoplay_button, "#2196F3", "white", "#1565C0")

        for btn in [
            self.current_stats_button, self.prev_button, self.rewind_button,
            self.play_button, self.pause_button, self.fast_forward_button,
            self.next_button, self.category_button, self.autoplay_button # , self.add_to_favorites_button, self.remove_from_favorites_button
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
            elif "Autoplay" in txt:
                e.widget.config(bg="#2196F3")
            elif "☰" in txt:
                e.widget.config(bg="purple")
            else:
                e.widget.config(bg="black")

        for btn in [
            self.current_stats_button, self.category_button, self.prev_button, self.rewind_button,
            self.play_button, self.pause_button, self.fast_forward_button,
            self.next_button, self.autoplay_button # , self.add_to_favorites_button, self.remove_from_favorites_button
        ]:
            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

    def toggle_autoplay(self):
        """Toggle the autoplay setting."""
        self.autoplay = not self.autoplay
        self.autoplay_button.config(
            text=f"Autoplay: {'ON' if self.autoplay else 'OFF'}",
            bg="#2196F3" if self.autoplay else "#757575"
        )

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

    def _on_video_loaded(self, title):
        self.reset_values(segment_speed=self.segment_speed)

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
        """Cycles playback speed between 1x, 1.5x, and 2x."""
        if self.playing_video:
            current_speed = self.media_player.get_rate()
            if abs(current_speed - 1.0) < 0.1:
                new_speed = 1.5
            elif abs(current_speed - 1.5) < 0.1:
                new_speed = 2.0
            else:
                new_speed = 1.0
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
                                          self.category_button, self.autoplay_button]
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
        self.fullscreen = not self.attributes("-fullscreen")
        self.attributes("-fullscreen", self.fullscreen) 
        if self.fullscreen:
            self.toggle_controls_visibility(visibility=False)
            # Hide cursor in fullscreen mode
            self.config(cursor="none")
        else:
            self.toggle_controls_visibility(visibility=True)
            # Show cursor when exiting fullscreen mode
            self.config(cursor="")

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
        new_volume = min(current_volume + 5, 100)  # Increase volume by 5%, up to 100%
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

        Stops the current video if it's playing, selects a random video from the list of available videos,
        sets it as the current video, and starts playing it.
        """
        try:
            # time.sleep(0.2)
            if self.playing_video:
                self.stop()
            self.previous_file = self.current_file
            # self.current_file = random.choice(self.video_files)
            if not self.random_select:
                self.select_sequential_videos()
            else:
                self.select_random_video()
            self.video_paused = False
            self.play_video()
        except IndexError:
            showerror(self, "Index Error", f"Videos Finished")
        except Exception as e:
            print(f"An Exception Occurred in play_next(): {e}")
    
    def play_previous(self, event=None):
        """
        Plays the previous video in the playlist.

        Stops the current video if it's playing, selects the previous video (if available), sets it as the current video,
        and starts playing it.
        """
        # print(self.previous_file)
        # time.sleep(0.2)
        if self.playing_video:
            self.stop()  # Stop the current video
        if self.previous_file:
            self.current_file, self.previous_file = self.previous_file, self.current_file
            self.play_video()

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
                if self.playing_video:
                    self.media_player.stop()
                    # if hasattr(self, 'current_media'):
                    #     print("Releasing current media...")
                    #     self.current_media.release()
                    # if hasattr(self, 'media_player'):
                    #     self.media_player.release()
                    time.sleep(0.3)
                if os.path.exists(self.current_file):
                    title = self.current_file.split("\\")[-1] + f" [{self.video_files.index(self.current_file)} / {len(self.video_files)}]"
                    self._release_current_media()
                    media = self.instance.media_new(self.current_file)
                    self.current_media = media
                    media.parse_async()  # Preloads meta info
                    # self._create_new_player()
                    self.media_player.set_media(media)
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
        if hasattr(self, 'current_media'):
            print("Releasing current media...")
            self.current_media.release()
            print("Released current media..")
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

    def stop(self):
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
        """Open the category manager window."""
        if not self.video_paused:
            self.pause_video()
        category_window = CategoryWindow(self, self.current_file)
        self.wait_window(category_window)
        self.pause_video()
        # self.pause_video(event=event)

if __name__ == "__main__":
    # for testing purposes
    import sys
    import tkinter as tk
    dummy_video_files = ["sample1.mp4", "sample2.mkv", "sample3.avi"]
    app = MediaPlayerApp(video_files=dummy_video_files, random_select=False)
    app.play_video = lambda: None
    app.mainloop()
