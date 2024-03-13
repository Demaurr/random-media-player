import tkinter as tk
from tkinter import ttk
from datetime import datetime
from summary_generator import HTMLSummaryReport

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

    def __init__(self, master, report_folder, video_data, session_time=0):
        """
        Initializes the VideoStatsApp with the specified parameters and default settings.
        Args:
            master (tk.Tk | tk.Frame): The parent widget or frame to which this VideoStatsApp belongs.
            video_data (list): A list of dictionaries containing video statistics.
            session_time (int): The duration of the session in seconds. Defaults to 0.
        """
        self.report_folder = report_folder
        self.master = master
        self.video_data = video_data
        self.session_time = session_time

        self.master.title("Video Stats For This Session")

        self.master.geometry("800x500")  # Set initial window size
        self.center_window()  # Center the window on the screen

        # Frame to hold the heading label and the button
        self.heading_frame = tk.Frame(master)
        self.heading_frame.pack(pady=5)

        self.heading_label = tk.Label(self.heading_frame, text="Statistics For The Session", font=("Tahoma", 20, "bold"), fg="Black")
        self.heading_label.pack(side="left")

        # Add a button for generating the summary report
        self.generate_report_button = tk.Button(self.heading_frame, text="Generate Summary Report", font=("Open Sans", 12, "bold"), bg="green", fg="white", command=self.generate_report_html)
        self.generate_report_button.pack(side="left", padx=10, pady=10)

        self.session_time_label = tk.Label(master, text=f"Session Time: {self.format_session_time(self.session_time)}", font=("Open Sans", 14, "bold"))
        self.session_time_label.pack(pady=5)

        self.create_table()

    def create_table(self):
        """
        Creates a table to display video statistics using the ttk.Treeview widget.
        """
        columns = ("Title", "Times", "Watchtime", "Folder")
        self.tree = ttk.Treeview(self.master, columns=columns, show="headings", selectmode="none")

        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Open Sans", 16, "bold"))

        self.tree.heading("Title", text="Title")
        self.tree.heading("Times", text="Times")
        self.tree.heading("Watchtime", text="Watchtime")
        self.tree.heading("Folder", text="Folder")

        self.tree.column("Title", width=150)
        self.tree.column("Times", width=100)
        self.tree.column("Watchtime", width=150)
        self.tree.column("Folder", width=350)

        self.tree.tag_configure('oddrow', background='grey')
        self.tree.tag_configure('evenrow', background='white')

        for idx, video in enumerate(self.video_data):
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            self.tree.insert("", "end", values=(video["File Name"], video["Count"], video["Duration Watched"], video["Folder"]), tags=(tag,))

        self.tree.pack(side="left", fill="both", expand=True, padx=20, pady=10)

        # Add a vertical scrollbar
        scrollbar = ttk.Scrollbar(self.master, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")

        self.tree.configure(yscrollcommand=scrollbar.set)

    def center_window(self):
        """
        Centers the application window on the screen.
        """
        window_width = 800
        window_height = 600

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
        current_datetime = datetime.today().strftime("%Y%m%d_%H%M%S")
        report_generator = HTMLSummaryReport(self.video_data)
        html_content = report_generator.generate_html(session_time=self.format_session_time(self.session_time), date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))  
        with open(f"{self.report_folder}summary_report_{current_datetime}.html", "w", encoding="utf-8") as file:
            file.write(html_content)


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
    app = VideoStatsApp(root, video_data)
    root.mainloop()

