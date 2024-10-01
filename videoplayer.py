import tkinter as tk
import vlc
import os
import random
import timeit
from datetime import timedelta
from static_methods import ensure_folder_exists
from watch_history_logger import WatchHistoryLogger
from volume_bar import VolumeBar
from video_progress_bar import VideoProgressBar
from watch_dictionary import WatchDict
from video_stats import VideoStatsApp
from favorites_manager import FavoritesManager
from deletion_manager import DeletionManager
from logs_writer import LogManager
from player_constants import FILES_FOLDER, LOG_PATH, WATCHED_HISTORY_LOG_PATH, SCREENSHOTS_FOLDER, REPORTS_FOLDER


class MediaPlayerApp(tk.Tk):
    
    def __init__(self, video_files, current_file=None, random_select=True, video_path=None, watch_history_csv=WATCHED_HISTORY_LOG_PATH):
        super().__init__()
        ensure_folder_exists(FILES_FOLDER)
        ensure_folder_exists(SCREENSHOTS_FOLDER)
        ensure_folder_exists(REPORTS_FOLDER)
        self.get_history_csvfile(watch_history_csv)
        self.favorites_manager = FavoritesManager(FILES_FOLDER + "Favorites.csv")
        self.logger = LogManager(LOG_PATH)
        self.deleter = DeletionManager()
        self.bg_color = "black"
        self.fg_color = "white"
        self.title("Media Player")
        self.geometry("1000x600")
        self.center_window()
        self.configure(bg=self.bg_color)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.watch_history_logger = WatchHistoryLogger(self.watch_history_csv)
        self.prev_counts = 0
        self.forward_counts = 0
        self.random_select = random_select
        self.video_index = 0 if not current_file else video_files.index(current_file)
        self._keybinding()
        self.initialize_player(video_files, video_path, cur_file=current_file)
        

    def get_history_csvfile(self, watch_history_csv):
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
    
    def on_close(self):
        self.session_end = timeit.default_timer()
        self.stop()  # Call the stop method when the window is closed
        # tk.Tk.quit(self)
        self.show_seassion_stats(self.get_stats())
        # print("Closing window...")
        # self.withdraw()
        # print("Window withdrawn")
        # self.quit()
        # print("Application quit")
          

    def initialize_player(self, video_files, folder_path, cur_file=None):
        # self.fav_csv = FILES_FOLDER +"Favorites.csv"
        self.instance = vlc.Instance()
        self.media_player = self.instance.media_player_new()

        self.media_player.event_manager().event_attach(vlc.EventType.MediaPlayerEncounteredError, self.handle_error)

        self.video_files = self.get_video_files(folder_path) if folder_path is not None else video_files
        self.current_file = cur_file
        self.previous_file = None
        self.playing_video = False
        self.video_paused = False
        self.session_start = None
        # self.watched_videos = {}
        self.watched_videos = WatchDict()
        self.feedback_var = tk.StringVar()
        self.feedback_label = None  # This will hold the label widget
        
        self.create_widgets()
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


    def create_widgets(self):
        """Creates the GUI elements for the media player."""
        self.media_canvas = tk.Canvas(self, bg="black", width=800, height=400)
        self.media_canvas.pack(pady=(5, 0), fill=tk.BOTH, expand=True)

        # Frame to contain control buttons and duration label
        control_frame = tk.Frame(self, bg="black")
        control_frame.pack(pady=(5, 0), fill=tk.X)

        self.feedback_label = tk.Label(
            self,
            textvariable=self.feedback_var,
            font=("Arial", 20, "bold"),
            bg="black",
            fg="white"
        )

        # Control buttons
        self.current_stats_button = tk.Button(
            control_frame,
            text="Current Stats",
            font=("Arial", 12, "bold"),
            command=self.current_stats,
        )
        self.current_stats_button.pack(side=tk.LEFT, padx=5, pady=0)

        self.prev_button = tk.Button(
            control_frame,
            text="Previous",
            font=("Arial", 12, "bold"),
            bg="red",
            fg="white",
            command=self.play_previous,
        )
        self.prev_button.pack(side=tk.LEFT, padx=5, pady=0)

        self.rewind_button = tk.Button(
            control_frame,
            text=" << ",
            font=("Arial", 12, "bold"),
            bg="red",
            fg="white",
            command=self.rewind,
        )
        self.rewind_button.pack(side=tk.LEFT, padx=5, pady=0)

        self.play_button = tk.Button(
            control_frame,
            text="Play",
            font=("Arial", 12, "bold"),
            bg="black",
            fg="white",
            width=10,
            command=self.play_video,
        )
        self.play_button.pack(side=tk.LEFT, padx=5, pady=0)

        self.pause_button = tk.Button(
            control_frame,
            text="Pause",
            font=("Arial", 12, "bold"),
            bg="#FF9800",
            fg="white",
            command=self.pause_video,
        )
        self.pause_button.pack(side=tk.LEFT, padx=5, pady=0)

        self.fast_forward_button = tk.Button(
            control_frame,
            text=" >> ",
            font=("Arial", 12, "bold"),
            bg="red",
            fg="white",
            command=self.fast_forward,
        )
        self.fast_forward_button.pack(side=tk.LEFT, padx=5, pady=0)

        self.next_button = tk.Button(
            control_frame,
            text="Next",
            font=("Arial", 12, "bold"),
            bg="red",
            fg="white",
            command=self.play_next,
        )
        self.next_button.pack(side=tk.LEFT, padx=5, pady=0)

        self.add_to_favorites_button = tk.Button(
            control_frame,
            text=" Fav + ",
            font=("Arial", 12, "bold"),
            bg="white",
            fg="black",
            command=self.add_to_favorites,
        )
        self.add_to_favorites_button.pack(side=tk.LEFT, padx=5, pady=0)

        self.remove_from_favorites_button = tk.Button(
            control_frame,
            text=" Fav - ",
            font=("Arial", 12, "bold"),
            bg="black",
            fg="white",
            command=self.remove_from_favorites,
        )
        self.remove_from_favorites_button.pack(side=tk.LEFT, padx=3, pady=0)

        # Duration label
        self.time_label = tk.Label(
            control_frame,
            text="00:00:00 / 00:00:00",
            font=("Arial", 12, "bold"),
            fg="white",
            bg="black",
        )
        self.time_label.pack(side=tk.RIGHT, padx=10, pady=0)

        # Progress bar
        self.progress_bar = VideoProgressBar(
            self, self.set_video_position, bg=self.bg_color, highlightthickness=0
        )
        self.progress_bar.pack(side=tk.LEFT, padx=5, pady=0)
        self.volume_bar = VolumeBar(self, self.media_player, fg=self.fg_color, bg=self.bg_color)
        self.volume_bar.pack(side=tk.RIGHT, padx=5, pady=0)

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
        self.bind("<Control-Right>", self.play_im_next)
        self.bind("<Control-Left>", self.play_im_previous)
        self.bind("<Delete>", self.delete_video)
        self.bind('<Control-Shift-Delete>', self.remove_from_deletion)

    def remove_from_deletion(self, event=None):
        self.deleter.remove_from_deletion(self.current_file)
        self.show_marquee(f"Removed Marked {self.current_file} file from deletion list.")
        
        
    def add_to_favorites(self, event=None):
        """Adds the currently playing video to favorites."""
        if self.current_file:
            if self.favorites_manager.add_to_favorites(self.current_file):
                # self.show_feedback(f"Added {self.current_file} to favorites")
                self.show_marquee(f"Added {self.current_file} from favorites")
                # self.logger.update_logs(f"[ADDED] to Favorites", self.current_file)
            else:
                # self.show_feedback("Video is already in favorites!")
                self.show_marquee("Video is already in favorites!")

    def remove_from_favorites(self, event=None):
        """Removes the currently playing video from favorites."""
        if self.current_file:
            if self.favorites_manager.delete_from_favorites(self.current_file):
                # self.show_feedback(f"Removed {self.current_file} from favorites")
                self.show_marquee(f"Removed {self.current_file} from favorites")
                # self.logger.update_logs(f"[DELETED] from Favorites", self.current_file)
            else:
                # self.show_feedback("Video is not in favorites!")
                self.show_marquee("Video is not in favorites!")

    def show_marquee(self, text):
        self.media_player.video_set_marquee_string(vlc.VideoMarqueeOption.Text, text.encode('utf-8'))
        self.media_player.video_set_marquee_int(vlc.VideoMarqueeOption.Enable, 1)
        self.media_player.video_set_marquee_int(vlc.VideoMarqueeOption.Timeout, 1000)  # 10 seconds

    def show_feedback(self, message):
        """
        Deprecated
        Displays feedback message on top of the window.
        """
        # Calculate the width of the window
        window_width = self.winfo_width()

        # Place the feedback label at the top of the window, centered horizontally
        self.feedback_label.place(x=window_width // 2, y=0, anchor="n")
        
        # Set the message and configure label for text wrapping
        self.feedback_var.set(message)
        self.feedback_label.config(wraplength=window_width - 20)  # Adjust wraplength as needed

        # Schedule the clear_feedback method to be called after 3 seconds
        self.after(3000, self.clear_feedback)

    def clear_feedback(self):
        """
        Deprecated
        Clears the feedback message
        """
        self.feedback_var.set('')
        self.feedback_label.pack_forget()
        # self.feedback_label.config(textvariable='')


    def toggle_controls_visibility(self, visibility):
        """Toggle the visibility of all control buttons and progress bars."""
        widgets_with_default_padding = [self.current_stats_button, self.prev_button, self.rewind_button, self.play_button,
                                        self.pause_button, self.fast_forward_button, self.next_button,
                                          self.add_to_favorites_button, self.remove_from_favorites_button]
        widgets_with_custom_padding = [self.time_label, self.progress_bar, self.volume_bar]

        if visibility:
            for widget in widgets_with_default_padding:
                widget.pack(side=tk.LEFT, padx=3, pady=0)  # Pack with default padding

            # Pack widgets with custom padding individually
            # self.time_label.pack(side=tk.RIGHT, padx=10, pady=0)
            self.progress_bar.pack(side=tk.LEFT, padx=5, pady=0)
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
        self.attributes("-fullscreen", self.fullscreen)  # Set fullscreen attribute
        if self.fullscreen:
            self.toggle_controls_visibility(visibility=False)  # Hide controls
            # Hide cursor in fullscreen mode
            self.config(cursor="none")
        else:
            self.toggle_controls_visibility(visibility=True)  # Show controls
            # Show cursor when exiting fullscreen mode
            self.config(cursor="")

    def save_screenshot(self, event):
        """Saves a screenshot of the video frame."""
        # self.ensure_folder_exists(SCREENSHOTS_FOLDER)
        filename = self.current_file.split('\\')[-1]
        # length = self.get_duration_str
        screenshot_path = f"{SCREENSHOTS_FOLDER}screenshot_{filename}_{self.media_player.get_time()}.png"
        self.media_player.video_take_snapshot(0, screenshot_path, 0, 0)

    def volume_increase(self, event):
        """Increases the volume."""
        current_volume = self.media_player.audio_get_volume()
        new_volume = min(current_volume + 5, 100)  # Increase volume by 5%, up to 100%
        # self.media_player.audio_set_volume(new_volume)
        self.media_player.audio_set_volume(int(new_volume))
        self.show_marquee(f"Volume: {new_volume}")
        self.volume_bar.set(new_volume)  # Update volume bar

    def volume_decrease(self, event):
        """Decreases the volume."""
        current_volume = self.media_player.audio_get_volume()
        new_volume = max(current_volume - 5, 0)  # Decrease volume by 10%, down to 0%
        # self.media_player.audio_set_volume(new_volume)
        self.media_player.audio_set_volume(int(new_volume))
        self.show_marquee(f"Volume: {new_volume}")
        self.volume_bar.set(new_volume)  # Update volume bar


    def select_file(self):
        """Plays a video file from the start when the 'Select File' button is clicked.
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
            self.play_video()
            self.video_paused = False
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
        # Select the previous video
        if self.previous_file:
            self.current_file = self.previous_file
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
        if self.random_select:
            self.random_select = False
            current_index = self.video_files.index(self.current_file)
            self.video_index = current_index + 1 if current_index < len(self.video_files) else 0
            self.play_next()
            self.random_select = True
        else:
            self.play_next()
    
    def play_im_previous(self, event=None):
        if self.random_select:
            self.random_select = False
            current_index = self.video_files.index(self.current_file) 
            self.previous_file = self.video_files[current_index - 1] if current_index > 0 else self.video_files[len(self.video_files) - 1]
            self.play_previous()
            self.random_select = True
        else:
            self.play_next()
        

    def play_video(self):
        """
        Plays the currently selected video file.
        """
        # print(self.winfo_width())
        try:
            if os.path.exists(self.current_file):
                title = self.current_file.split("\\")[-1] + f" [{self.video_files.index(self.current_file)} / {len(self.video_files)}]"
                self.title(title)
                media = self.instance.media_new(self.current_file)
                self.media_player.set_media(media)
                self.media_player.set_hwnd(self.media_canvas.winfo_id())
                self.media_player.play()
                self.reset_video_counts()
                self.show_marquee(f"Playing: {self.current_file}")
                self.session_start = timeit.default_timer() if self.session_start is None else self.session_start
                self.playing_video = True
                self.watched_videos.add_watch(self.current_file)
                self.progress_bar.set(0)
            else:
                print(f"The file Doesn't Exists: {self.current_file}")
                self.logger.error_logs(f"File Not Found: {self.current_file}")
                self.play_next()
        except FileNotFoundError as e:
            print(f"An Exception Occurred in play_video: {e}")
            self.show_feedback(f"Error {e} Loading {self.current_file}")
            # self.play_next()
        except Exception as e:
            print(f"An Exception Occurred in play_video: {e}")
            self.show_feedback(f"An Unexpected Error Occured in play_video: {e}")
            # self.show_feedback(f"Error {e} Loading {self.current_file}")
            # self.play_next()

    def fast_forward(self, event=None):
        """
        Fast-forwards the currently playing video by 10 seconds.
        """
        if self.playing_video:
            self.forward_counts += 1
            current_time = self.media_player.get_time() + 10000
            current_time_str = str(timedelta(milliseconds=current_time))[:-3]
            self.media_player.set_time(current_time)
            self.show_marquee(f"{current_time_str} / {self.total_duration_str}")
            

    def rewind(self, event=None):
        """
        Rewinds the currently playing video by 5 seconds.
        """
        if self.playing_video:
            self.prev_counts += 1
            current_time = self.media_player.get_time() - 5000
            self.media_player.set_time(current_time)
            self.show_marquee(f"{self.current_time_str} / {self.total_duration_str}")

    def pause_video(self, event=None):
        """
        Pauses or resumes playback of the currently playing video.
        Toggles between pause and resume based on the current playback state.
        """
        if self.playing_video:
            if self.video_paused:
                self.media_player.play()
                self.video_paused = False
                self.pause_button.config(text="Pause")
            else:
                self.media_player.pause()
                self.video_paused = True
                self.pause_button.config(text="Resume")

    def stop(self):
        """
        Stops playback of the currently playing video.
        Logs the watch history before stopping, including the duration watched and total duration.
        """
        if self.playing_video:
            # Log watch history before stopping
            duration_watched = self.get_duration_str()
            # self.watched_videos[self.current_file] =  self.watched_videos.get(self.current_file, 0) + self.media_player.get_time()
            skipped_time = (self.prev_counts * 4990) - (self.forward_counts * 9990)
            print(f"Skipped Time: {self.get_time_str(skipped_time)}")
            print(f"Prev Counts: {self.prev_counts}, Forward Counts: {self.forward_counts}")
            actual_time_duration = self.media_player.get_time()+skipped_time
            total_duration = self.get_time_str(actual_time_duration)
            self.watch_history_logger.log_watch_history(self.current_file, duration_watched, total_duration)
            # print("total_duration:", total_duration, "\n", "Duration Watched(wng):", duration_watched, "\n", "Duration Watched(cor):", self.get_time_str(self.media_player.get_time()+skipped_time))
            self.watched_videos.increment_duration_and_count(self.current_file, actual_time_duration)
            self.media_player.stop()
            self.playing_video = False
        self.time_label.config(text="00:00:00 / " + self.get_duration_str())

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
        self.after(100, self.update_video_progress)

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
        self.master.destroy()
    
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
        # Gets the requested values of the height and width.
        window_width = 1000
        window_height = 600

        # Gets both half the screen width/height and window width/height
        position_right = int(self.winfo_screenwidth() / 2 - window_width / 2)
        position_down = int(self.winfo_screenheight() / 2 - window_height / 2)

        # Positions the window in the center of the page.
        self.geometry("+{}+{}".format(position_right, position_down))

    def reset_video_counts(self):
        self.prev_counts = 0
        self.forward_counts = 0

    def print_sessions_stats(self):
        pass
