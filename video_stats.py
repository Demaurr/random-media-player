import tkinter as tk
from tkinter import ttk
from datetime import datetime
from summary_generator import HTMLSummaryReport
from static_methods import open_in_default_app

class VideoStatsApp:
    """
    VideoStatsApp class represents an application for displaying video statistics for a session and generating HTML summary reports.

    Args:
        master (tk.Tk | tk.Frame): The parent widget or frame to which this VideoStatsApp belongs.
        video_data (list): A list of dictionaries containing video statistics.
        session_time (int): The duration of the session in seconds. Defaults to 0.

    Attributes:
        master: The parent widget or frame to which this VideoStatsApp belongs.
        video_data (list): A list of dictionaries containing video statistics.
        session_time (int): The duration of the session in seconds.

    Methods:
        __init__(self, master, video_data, session_time=0):
            Initializes the VideoStatsApp with the specified parameters and default settings.
            Args:
                master (tk.Tk | tk.Frame): The parent widget or frame to which this VideoStatsApp belongs.
                video_data (list): A list of dictionaries containing video statistics.
                session_time (int): The duration of the session in seconds. Defaults to 0.

        create_table(self):
            Creates a table to display video statistics using the ttk.Treeview widget.

        center_window(self):
            Centers the application window on the screen.

        format_session_time(self, seconds):
            Formats session time from seconds to HH:MM:SS format.
            Args:
                seconds (int): The duration of the session in seconds.

        generate_report_html(self):
            Generates an HTML summary report based on the video statistics and saves it to a file in the REPORT_FOLDER.

    Example:
        # Create a Tkinter window
        root = tk.Tk()

        # Assuming video_data is a list of dictionaries containing video statistics
        video_data = [...]

        # Create a VideoStatsApp instance
        app = VideoStatsApp(root, video_data)
        
        # Start the Tkinter event loop
        root.mainloop()
    """

    def __init__(self, master, report_folder, video_data, session_time=0, fg="black", bg="white", for_current=False):
        """
        Initializes the VideoStatsApp with the specified parameters and default settings.
        Args:
            master (tk.Tk | tk.Frame): The parent widget or frame to which this VideoStatsApp belongs.
            video_data (list): A list of dictionaries containing video statistics.
            session_time (int): The duration of the session in seconds. Defaults to 0.
        """
        self.report_folder = report_folder + "\\"
        self.master = master
        self.video_data = video_data
        self.session_time = session_time
        self.master.title("Video Stats For This Session")

        self.master.configure(bg=bg)
        self.master.geometry("800x500")
        if not for_current:
            self.master.protocol("WM_DELETE_WINDOW", self.on_closing)  # Set initial window size
        self.center_window()  # Center the window on the screen

        # Frame to hold the heading label and the button
        self.heading_frame = tk.Frame(master, bg=bg)
        self.heading_frame.pack(pady=5)

        self.heading_label = tk.Label(
            self.heading_frame,
            text="Statistics For The Session",
            font=("Segoe UI", 24, "bold"),
            fg=fg,
            bg=bg,
            pady=8
        )
        self.heading_label.pack(side="left", anchor="w")

        self.generate_report_button = tk.Button(
            self.heading_frame,
            text="Generate Summary Report",
            font=("Segoe UI", 12, "bold"),
            bg="green",
            fg="white",
            activebackground="#006400",
            activeforeground="white",
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=3,
            cursor="hand2",
            command=self.generate_report_html
        )
        self.generate_report_button.pack(side="right", padx=10)

        def on_enter(e): e.widget.config(bg="#228B22")
        def on_leave(e): e.widget.config(bg="green")
        self.generate_report_button.bind("<Enter>", on_enter)
        self.generate_report_button.bind("<Leave>", on_leave)

        self.session_time_label = tk.Label(
            master,
            text=f"Session Time: {self.format_session_time(self.session_time)}",
            font=("Segoe UI", 14, "bold"),
            fg=fg,
            bg=bg,
            pady=4
        )
        self.session_time_label.pack(pady=(0, 10))

        self.create_table()

    def on_closing(self):
        self.master.destroy()
        # self.master.withdraw()
        # self.master.withdraw()
        # self.master.quit()
        # self.master.quit()

    def create_table(self):
        """
        Creates a table to display video statistics using the ttk.Treeview widget.
        """
        columns = ("Title", "Times", "Watchtime", "Folder")
        table_frame = tk.Frame(self.master, bg=self.master["bg"])
        table_frame.pack(fill="both", expand=True, padx=20, pady=10)

        style = ttk.Style(self.master)
        style.theme_use("clam")
        style.configure(
            "Stats.Treeview.Heading",
            font=("Segoe UI", 15, "bold"),
            background="black",
            foreground="white"
        )
        style.configure(
            "Stats.Treeview",
            font=("Segoe UI", 12),
            rowheight=32,
            background="black",
            fieldbackground="black",
            foreground="white"
        )
        style.map("Stats.Treeview", background=[("selected", "#222")])

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="none",
            style="Stats.Treeview"
        )

        # Set heading style explicitly
        for col in columns:
            self.tree.heading(col, text=col, anchor="center", command=lambda _col=col: None)
        self.tree.tag_configure('oddrow', background="#222", foreground="white")
        self.tree.tag_configure('evenrow', background="#333", foreground="white")

        self.tree.column("Title", width=200, anchor="w")
        self.tree.column("Times", width=70, minwidth=40, anchor="center", stretch=False)
        self.tree.column("Watchtime", width=120, anchor="center")
        self.tree.column("Folder", width=300, anchor="w")

        for idx, video in enumerate(self.video_data):
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            self.tree.insert(
                "",
                "end",
                values=(video["File Name"], video["Count"], video["Duration Watched"], video["Folder"]),
                tags=(tag,)
            )

        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

    def center_window(self):
        """
        Centers the application window on the screen.
        """
        window_width = 800
        window_height = 500

        position_right = int(self.master.winfo_screenwidth() / 2 - window_width / 2)
        position_down = int(self.master.winfo_screenheight() / 2 - window_height / 2)

        self.master.geometry("+{}+{}".format(position_right, position_down))

    def format_session_time(self, seconds):
        """
        Formats session time from seconds to HH:MM:SS format.
        Args:
            seconds (int): The duration of the session in seconds.
        Returns:
            str: The formatted session time in HH:MM:SS format.
        """
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def generate_report_html(self):
        """
        Generates an HTML summary report based on the video statistics and saves it to a file in the REPORT_FOLDER.
        """
        try:
            current_datetime = datetime.today().strftime("%Y%m%d_%H%M%S")
            report_generator = HTMLSummaryReport(self.video_data)
            html_content = report_generator.generate_html(session_time=self.format_session_time(self.session_time), date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))  
            with open(f"{self.report_folder}summary_report_{current_datetime}.html", "w", encoding="utf-8") as file:
                file.write(html_content)
            print(f"Summary Report Generated At: {self.report_folder}summary_report_{current_datetime}.html")
            open_in_default_app(f"{self.report_folder}summary_report_{current_datetime}.html")
        except Exception as e:
            print(f"Error generating report: {e}")
            error_message = f"An error occurred while generating the report: {e}"
            tk.messagebox.showerror("Error", error_message)
            self.on_closing()


if __name__ == "__main__":
    # Sample video data
    video_data = [
        {"File Name": "video1.mp4", "Count": 10, "Duration Watched": "02:30:00", "Folder": "Folder A"},
        {"File Name": "video2.mp4", "Count": 5, "Duration Watched": "01:45:00", "Folder": "Folder B"},
        {"File Name": "video3.mp4", "Count": 8, "Duration Watched": "01:20:00", "Folder": "Folder C"},
        {"File Name": "video4.mp4", "Count": 12, "Duration Watched": "03:10:00", "Folder": "Folder D"},
        {"File Name": "video5.mp4", "Count": 6, "Duration Watched": "02:00:00", "Folder": "Folder E"}
    ]

    root = tk.Tk()
    app = VideoStatsApp(root, "Files/", video_data)
    root.mainloop()

