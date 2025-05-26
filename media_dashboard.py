import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
from player_constants import DEMO_WATCHED_HISTORY

plt.style.use('dark_background')
# sns.set_palette(sns.color_palette(["#e74c3c", "#44b300", "#ffffff", "#222222"]))

class ScrollableFrame(tk.Frame):
    """A scrollable frame that can contain other widgets"""
    def __init__(self, parent, bg="black"):
        super().__init__(parent, bg=bg)
        
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=bg)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _on_mousewheel(self, event):
        if self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

class DashboardWindow():
    def __init__(self, master=None, csv_path=DEMO_WATCHED_HISTORY):
        self.master = master
        self.master.title("Media Consumption Statistics")
        self.master.configure(bg="black")
        self.csv_path = csv_path
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Set window size and center it
        self.window_width = 1200
        self.window_height = 800
        self.center_window()

        self.master.state('zoomed')
        
        self.create_widgets(self.master)
        self.load_and_plot_data()

    def create_widgets(self, master):
        # Top bar
        btn_frame = tk.Frame(master, bg="black")
        btn_frame.pack(side="top", fill="x", pady=10)

        self.reload_btn = tk.Button(
            btn_frame, text="Reload Data", command=self.load_and_plot_data,
            bg="#44b300", fg="white", font=("Segoe UI", 11, "bold"), bd=0, padx=10, pady=5
        )
        self.reload_btn.pack(side="left", padx=10)

        self.open_btn = tk.Button(
            btn_frame, text="Open CSV...", command=self.open_csv_dialog,
            bg="#e74c3c", fg="white", font=("Segoe UI", 11, "bold"), bd=0, padx=10, pady=5
        )
        self.open_btn.pack(side="left", padx=10)
        

        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self._set_styles()

    
    def _set_styles(self):

        style = ttk.Style()
        style.theme_use('clam')
        style.configure(
            'dashboardStyle.TNotebook.Tab',
            background='black',
            foreground='red',
            font=('Segoe UI', 11, 'bold'),
            minwidth=150
        )
        style.map(
            'dashboardStyle.TNotebook.Tab',
            background=[('selected', '#8B0000')],
            foreground=[('selected', 'white')]
        )
        style.configure(
            "dashboardStyle.Treeview",
            background="black",
            foreground="white",
            fieldbackground="black",
            rowheight=28,
            font=('Segoe UI', 10),
            minwidth=150
        )

        self.overview_scroll = ScrollableFrame(self.notebook)
        self.folder_scroll = ScrollableFrame(self.notebook)
        self.hour_scroll = ScrollableFrame(self.notebook)
        self.weekday_scroll = ScrollableFrame(self.notebook)

        self.month_scroll = ScrollableFrame(self.notebook)
        self.notebook.add(self.overview_scroll, text="Overview")
        self.notebook.add(self.folder_scroll, text="Most Watched Folders")
        self.notebook.add(self.hour_scroll, text="Hourly Consumption")
        self.notebook.add(self.weekday_scroll, text="Weekly Consumption")
        self.notebook.add(self.month_scroll, text="Monthly Consumption")
        style.configure(
            "dashboardStyle.Treeview.Heading",
            background="#e74c3c",
            foreground="white",
            font=('Segoe UI', 10, 'bold')
        )

        self.notebook.configure(style='dashboardStyle.TNotebook')

    def open_csv_dialog(self):
        file_path = filedialog.askopenfilename(
            title="Select Watch History CSV",
            filetypes=[("CSV Files", "*.csv")]
        )
        if file_path:
            self.csv_path = file_path
            self.load_and_plot_data()

    def load_and_plot_data(self):
        COL_TOTAL_DURATION = "Total Duration"
        COL_DURATION_WATCHED = "Duration Watched"
        COL_DATE_WATCHED = "Date Watched"
        COL_FILE_NAME = "File Name"

        try:
            df = pd.read_csv(self.csv_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load CSV: {e}")
            return

        # --- Data Preparation ---
        # Fix durations
        for col in [COL_TOTAL_DURATION, COL_DURATION_WATCHED]:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"00:{x}" if isinstance(x, str) and len(x.split(':')) == 2 else x)
                df[col] = pd.to_timedelta(df[col], errors="coerce")
        
        # Dates
        if COL_DATE_WATCHED in df.columns:
            df[COL_DATE_WATCHED] = pd.to_datetime(df[COL_DATE_WATCHED], errors="coerce")
            df["date"] = df[COL_DATE_WATCHED].dt.date
            df["hour"] = df[COL_DATE_WATCHED].dt.hour
            df["weekday"] = df[COL_DATE_WATCHED].dt.day_name()
            weekday_counts = df["weekday"].value_counts().reindex(
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], fill_value=0
            ).fillna(0)
        else:
            weekday_counts = pd.Series(dtype=int)
            
        # Video name/folder
        if COL_FILE_NAME in df.columns:
            df["video_name"] = df[COL_FILE_NAME].apply(lambda x: os.path.basename(x) if isinstance(x, str) else "Unknown")
            df["primary_folder"] = df[COL_FILE_NAME].apply(lambda x: os.path.dirname(x) if isinstance(x, str) else "Unknown")

        # --- Stats ---
        total_duration = df[COL_TOTAL_DURATION].sum() if COL_TOTAL_DURATION in df.columns else pd.Timedelta(0)
        total_watch_time = df[COL_DURATION_WATCHED].sum() if COL_DURATION_WATCHED in df.columns else pd.Timedelta(0)

        info_items = [
            ("Total Duration", str(total_duration)),
            ("Total Watched", str(total_watch_time)),
            ("Total Videos", str(len(df))),
        ]
        if COL_DATE_WATCHED in df.columns and not df[COL_DATE_WATCHED].isnull().all():
            min_date = df[COL_DATE_WATCHED].min()
            max_date = df[COL_DATE_WATCHED].max()
            info_items.append(("Data covers", f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"))
        if "video_name" in df.columns:
            rewatched = (df["video_name"].value_counts() > 1).sum()
            unique_videos = df["video_name"].nunique()
            info_items.append(("Rewatched Videos", str(rewatched)))
            info_items.append(("Unique Videos", str(unique_videos)))

        # --- Top 10 Most Watched Videos by Count ---
        # if "video_name" in df.columns and "primary_folder" in df.columns:
        #     top_10_count = df.groupby(['video_name', 'primary_folder']).size().nlargest(10).reset_index(name='Count')
        # else:
        #     top_10_count = pd.DataFrame(columns=['video_name', 'primary_folder', 'Count'])

        # --- Top 10 Most Watched Videos by Duration ---
        if "video_name" in df.columns and COL_DURATION_WATCHED in df.columns:
            top_10_duration = df.groupby('video_name')[COL_DURATION_WATCHED].sum().nlargest(10).reset_index()
        else:
            top_10_duration = pd.DataFrame(columns=['video_name', COL_DURATION_WATCHED])

        # --- Top 5 Most Watched Hours ---
        if "hour" in df.columns:
            top_5_hours = df['hour'].value_counts().head(5).reset_index()
            top_5_hours.columns = ['Hour', 'Count']
        else:
            top_5_hours = pd.DataFrame(columns=['Hour', 'Count'])

        if "Duration Category" not in df.columns:
            df["Duration Category"] = df[COL_TOTAL_DURATION].apply(self._categorize_duration)

        if COL_DATE_WATCHED in df.columns:
            last_30 = df[df[COL_DATE_WATCHED] >= (pd.Timestamp.now() - pd.Timedelta(days=30))]
            video_count_by_date = last_30.groupby('date').size()
        else:
            video_count_by_date = pd.Series(dtype=int)

        # --- Clear Scrollable Frames ---
        for scroll_frame in [self.overview_scroll, self.folder_scroll, self.hour_scroll, self.weekday_scroll]:
            for widget in scroll_frame.scrollable_frame.winfo_children():
                widget.destroy()

        # --- Overview Tab ---
        overview_content = self.overview_scroll.scrollable_frame
        overview_left = tk.Frame(overview_content, bg="black")
        overview_right = tk.Frame(overview_content, bg="black")
        overview_left.pack(side="left", fill="both", expand=True, padx=(20, 10), pady=20)  # <-- fill both and expand
        overview_right.pack(side="right", fill="both", expand=True, padx=(10, 20), pady=20)

        # --- Card Metrics ---
        card_metrics = [
            ("Total Duration Elapsed", str(total_duration), "#44b300"),
            ("Total Watched Elapsed", str(total_watch_time), "#e74c3c"),
            ("Total Videos", str(len(df)), "#3498db"),
        ]
        if COL_DATE_WATCHED in df.columns and not df[COL_DATE_WATCHED].isnull().all():
            min_date = df[COL_DATE_WATCHED].min()
            max_date = df[COL_DATE_WATCHED].max()
            card_metrics.append(("Data covers", f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}", "#5C2626"))
            latest_row = df.loc[df[COL_DATE_WATCHED].idxmax()]
            latest_video = latest_row["video_name"] if "video_name" in latest_row else "Unknown"
            card_metrics.append(("Latest Watched Video", str(latest_video), "#3498db"))
        if "video_name" in df.columns:
            rewatched = (df["video_name"].value_counts() > 1).sum()
            unique_videos = df["video_name"].nunique()
            card_metrics.append(("Rewatched Videos", str(rewatched), "#f39c12"))
            card_metrics.append(("Unique Videos", str(unique_videos), "#8e44ad"))
            
        overview_left.grid_rowconfigure(tuple(range(len(card_metrics))), weight=1)
        overview_left.grid_columnconfigure(0, weight=1)

        for i, (label, value, color) in enumerate(card_metrics):
            card = tk.Frame(overview_left, bg=color, bd=0, relief="flat")
            card.grid(row=i, column=0, sticky="nsew", padx=5, pady=2)  # sticky nsew for full fill
            tk.Label(card, text=value, bg=color, fg="white", font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=8, pady=(2,0))
            tk.Label(card, text=label, bg=color, fg="white", font=("Segoe UI", 9)).pack(anchor="w", padx=8, pady=(0,1))
        row_offset = len(card_metrics)

        # self._make_table(overview_left, top_10_count, "Top 10 Most Watched Videos by Count", row_offset, "#e74c3c")
        # self._make_table(overview_left, top_10_duration, "Top 10 Most Watched Videos by Duration", row_offset+1, "#44b300")
        # self._make_table(overview_left, top_5_hours, "Top 5 Most Watched Hours", row_offset+2, "#ffffff")

        # Right Side Plots
        if not video_count_by_date.empty:
            self._plot_last_30_days_with_categories(
                overview_right, video_count_by_date, last_30, df, COL_TOTAL_DURATION
            )
        else:
            tk.Label(overview_right, text="No data for last 30 days.", bg="black", fg="#e74c3c", font=("Segoe UI", 14)).pack(pady=40)

        # Duration category plot as a pie chart
        if COL_TOTAL_DURATION in df.columns:
            duration_counts = df["Duration Category"].value_counts().reindex(
                ["Very Short (<1 min)", "Short (1-3 min)", "Medium (3-10 min)", "Long (10-60 min)", "Very Long (>1 hr)"], fill_value=0
            )
            fig2, ax2 = plt.subplots(figsize=(5, 2.8))
            colors = ["#e74c3c", "#44b300", "#f39c12", "#222222", "#8e44ad"]
            wedges, texts, autotexts = ax2.pie(
                duration_counts.values,
                labels=duration_counts.index,
                autopct='%1.1f%%',
                startangle=140,
                colors=colors,
                textprops={'color':"white"}
            )
            ax2.set_title("Videos by Duration Category", color="white")
            fig2.tight_layout()
            self._embed_plot(overview_right, fig2, 1)

        # self._make_table(overview_left, top_10_count, "Top 10 Most Watched Videos by Count", row_offset, "#e74c3c")

        self._plot_top_10_duration(overview_left, top_10_duration, COL_DURATION_WATCHED, row_offset+1)
        self._populate_folder_tab(df)
        self._populate_hour_tab(df)
        self._populate_weekday_tab(df, weekday_counts, COL_TOTAL_DURATION)
        self._populate_monthly_tab(df)

    def _populate_hour_tab(self, df):
        """Populate the hour tab with plots and tables."""
        hour_content = self.hour_scroll.scrollable_frame
        for widget in hour_content.winfo_children():
            widget.destroy()
        hour_left = tk.Frame(hour_content, bg="black")
        hour_right = tk.Frame(hour_content, bg="black")
        hour_left.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=20)
        hour_right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=20)

        if "hour" in df.columns:
            hour_counts = df["hour"].value_counts().sort_index()
            fig, ax = plt.subplots(figsize=(5.7, 3.3))
            sns.barplot(x=hour_counts.index, y=hour_counts.values, ax=ax, color="#44b300")
            ax.set_title("Media Consumption by Hour of Day", color="white")
            ax.set_xlabel("Hour", color="white")
            ax.set_ylabel("Media Consumed", color="white")
            ax.set_xticks(range(0, 24))
            ax.tick_params(axis='x', labelcolor="white")
            ax.tick_params(axis='y', labelcolor="white")
            fig.tight_layout()
            self._embed_plot(hour_left, fig, 1)

            self._plot_hourly_by_weekday(hour_left, df, 0)
            if "Duration Category" not in df.columns and "Total Duration" in df.columns:
                df["Duration Category"] = df["Total Duration"].apply(self._categorize_duration)
            if "Duration Category" in df.columns:
                self._plot_hour_vs_duration_category(hour_right, df, 0)
        else:
            tk.Label(hour_left, text="No hourly data available.", bg="black", fg="#e74c3c", font=("Segoe UI", 14)).pack(pady=40)

    def _populate_weekday_tab(self, df, weekday_counts, COL_TOTAL_DURATION):
        """Populate the weekday tab with plots and tables."""
        weekday_content = self.weekday_scroll.scrollable_frame
        for widget in weekday_content.winfo_children():
            widget.destroy()
        weekday_left = tk.Frame(weekday_content, bg="black")
        weekday_right = tk.Frame(weekday_content, bg="black")
        weekday_left.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=20)
        weekday_right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=20)

        if "Date Watched" in df.columns:
            if COL_TOTAL_DURATION in df.columns:
                weekday_duration = df.groupby("weekday")[COL_TOTAL_DURATION].sum().reindex(
                    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                ).fillna(pd.Timedelta(0))
                weekday_table_df = pd.DataFrame({
                    "Weekday": weekday_counts.index,
                    "Count": weekday_counts.values,
                    "Total Duration": weekday_duration.apply(lambda td: str(td))
                })
                self._make_table(weekday_right, weekday_table_df, "Weekly Consumption (Count & Duration)", 1, "#44b300")
                plot_row = 0
            else:
                plot_row = 0

            fig, ax = plt.subplots(figsize=(5.5, 3))
            sns.barplot(x=weekday_counts.index, y=weekday_counts.values, ax=ax, color="#44b300")
            ax.set_title("Media Watched by Day of Week", color="white")
            ax.set_xlabel("Day", color="white")
            ax.set_ylabel("Count", color="white")
            ax.tick_params(axis='x', labelcolor="white", rotation=30)
            ax.tick_params(axis='y', labelcolor="white")
            fig.tight_layout()
            self._embed_plot(weekday_left, fig, plot_row)
            
            if COL_TOTAL_DURATION in df.columns:
                weekday_duration_minutes = weekday_duration.apply(lambda td: td.total_seconds() / 60)
                fig2, ax2 = plt.subplots(figsize=(5.5, 3))
                sns.barplot(x=weekday_duration_minutes.index, y=weekday_duration_minutes.values, ax=ax2, color="#e74c3c")
                ax2.set_title("Total Watch Duration by Day of Week", color="white")
                ax2.set_xlabel("Day", color="white")
                ax2.set_ylabel("Total Duration (minutes)", color="white")
                ax2.tick_params(axis='x', labelcolor="white", rotation=30)
                ax2.tick_params(axis='y', labelcolor="white")
                fig2.tight_layout()
                self._embed_plot(weekday_left, fig2, plot_row + 1)
            self._plot_weekday_vs_duration_category(weekday_right, df, 0)
        else:
            tk.Label(weekday_left, text="No weekday data available.", bg="black", fg="#e74c3c", font=("Segoe UI", 14)).pack(pady=40)
    
    def _populate_monthly_tab(self, df):
        """Add a Favorites & Trends tab with monthly trends and a monthly summary table."""
        if not hasattr(self, 'month_scroll'):
            self.month_scroll = ScrollableFrame(self.notebook)
            self.notebook.add(self.month_scroll, text="Favorites & Trends")
        favs_content = self.month_scroll.scrollable_frame
        for widget in favs_content.winfo_children():
            widget.destroy()
        left = tk.Frame(favs_content, bg="black")
        right = tk.Frame(favs_content, bg="black")
        left.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=20)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=20)

        # --- Monthly Trends Plot ---
        if "Date Watched" in df.columns:
            df["month"] = pd.to_datetime(df["Date Watched"], errors="coerce").dt.to_period("M")
            monthly_counts = df.groupby("month").size()
            fig, ax = plt.subplots(figsize=(7, 3.5))
            monthly_counts.plot(ax=ax, marker="o", color="#44b300")
            ax.set_title("Monthly Videos Watched", color="white")
            ax.set_xlabel("Month", color="white")
            ax.set_ylabel("Count", color="white")
            ax.tick_params(axis='x', labelcolor="white", rotation=30)
            ax.tick_params(axis='y', labelcolor="white")
            fig.tight_layout()
            self._embed_plot(left, fig, 0)

            # --- Monthly Duration Category Plot ---
            if "Duration Category" in df.columns:
                monthly_cat = df.groupby(["month", "Duration Category"]).size().unstack(fill_value=0)
                # Order columns for consistency
                category_order = [
                    "Very Short (<1 min)", "Short (1-3 min)", "Medium (3-10 min)",
                    "Long (10-60 min)", "Very Long (>1 hr)", "Unknown"
                ]
                monthly_cat = monthly_cat.reindex(columns=category_order, fill_value=0)
                fig_cat, ax_cat = plt.subplots(figsize=(7, 3))
                monthly_cat.plot(kind="bar", stacked=True, ax=ax_cat, colormap="tab20")
                ax_cat.set_title("Monthly Watched by Duration Category", color="white")
                ax_cat.set_xlabel("Month", color="white")
                ax_cat.set_ylabel("Count", color="white")
                ax_cat.tick_params(axis='x', labelcolor="white", rotation=30)
                ax_cat.tick_params(axis='y', labelcolor="white")
                ax_cat.legend(
                    title="Duration Category",
                    fontsize=8,
                    title_fontsize=9,
                    loc="center left",
                    bbox_to_anchor=(1.02, 0.5),
                    borderaxespad=0.
                )
                fig_cat.tight_layout()
                self._embed_plot(left, fig_cat, 1)

            # --- Monthly Table: Count & Total Duration ---
            if "Duration Watched" in df.columns:
                monthly_duration_watched = df.groupby("month")["Duration Watched"].sum()
                monthly_table_df = pd.DataFrame({
                    "Month": monthly_counts.index.astype(str),
                    "Count": monthly_counts.values,
                    "Total Duration Watched": monthly_duration_watched.apply(lambda td: str(td))
                })
            else:
                monthly_table_df = pd.DataFrame({
                    "Month": monthly_counts.index.astype(str),
                    "Count": monthly_counts.values
                })
            self._make_table(right, monthly_table_df, "Monthly Summary (Count & Duration Watched)", 0, "#44b300", table_height=8)
        else:
            tk.Label(left, text="No monthly data.", bg="black", fg="#e74c3c", font=("Segoe UI", 12)).pack(pady=10)
            tk.Label(right, text="No monthly data.", bg="black", fg="#e74c3c", font=("Segoe UI", 12)).pack(pady=10)

    def _populate_folder_tab(self, df):
        """Populate the folder tab with plots and tables."""
        folder_content = self.folder_scroll.scrollable_frame
        for widget in folder_content.winfo_children():
            widget.destroy()
        folder_left = tk.Frame(folder_content, bg="black")
        folder_right = tk.Frame(folder_content, bg="black")
        folder_left.pack(side="left", fill="both", expand=True, padx=(10, 5), pady=20)
        folder_right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=20)

        if "primary_folder" in df.columns:
            folder_counts = df["primary_folder"].value_counts().head(10)
            fig, ax = plt.subplots(figsize=(8, 4))
            sns.barplot(y=folder_counts.index, x=folder_counts.values, ax=ax, palette=["#e74c3c"])
            ax.set_title("Top 10 Most Watched Folders", color="white")
            ax.set_xlabel("Watch Count", color="white")
            ax.set_ylabel("Folder", color="white")
            ax.tick_params(axis='y', labelcolor="white")
            ax.tick_params(axis='x', labelcolor="white")
            fig.tight_layout()
            self._embed_plot(folder_right, fig, 0)
            
            if "Total Duration" in df.columns:
                folder_duration = df.groupby("primary_folder")["Total Duration"].sum().reindex(folder_counts.index).fillna(pd.Timedelta(0))
                folder_table_df = pd.DataFrame({
                    "Folder": folder_counts.index,
                    "Count": folder_counts.values,
                    "Total Duration": folder_duration.apply(lambda td: str(td))
                })
            else:
                folder_table_df = pd.DataFrame({
                    "Folder": folder_counts.index,
                    "Count": folder_counts.values
                })
            self._make_table(folder_left, folder_table_df, "Top Folders (Count & Duration)", 0, "#e74c3c", table_height=6)
            if "video_name" in df.columns and "Duration Watched" in df.columns:
                video_stats = (
                    df.groupby("video_name")["Duration Watched"]
                    .agg(['count', 'sum'])
                    .sort_values(by='count', ascending=False)
                    .head(50)
                    .reset_index()
                )
                video_stats.rename(
                    columns={
                        "video_name": "Video Name",
                        "count": "Count",
                        "sum": "Total Duration Watched"
                    },
                    inplace=True
                )
                # Format duration as string
                video_stats["Total Duration Watched"] = video_stats["Total Duration Watched"].apply(lambda td: str(td))
                self._make_table(
                    folder_left,
                    video_stats[["Video Name", "Count", "Total Duration Watched"]],
                    "Most Watched Videos",
                    1,
                    "#44b300",
                    table_height=10
                )
            else:
                tk.Label(
                    folder_left, text="No video stats available.", bg="black", fg="#44b300", font=("Segoe UI", 12, "bold")
                ).grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        else:
            tk.Label(folder_left, text="No folder data available.", bg="black", fg="#e74c3c", font=("Segoe UI", 14)).pack(pady=40)
    
    def _categorize_duration(self, td):
        if pd.isnull(td):
            return "Unknown"
        minutes = td.total_seconds() / 60
        if minutes < 1:
            return "Very Short (<1 min)"
        elif minutes < 3:
            return "Short (1-3 min)"
        elif minutes < 10:
            return "Medium (3-10 min)"
        elif minutes < 60:
            return "Long (10-60 min)"
        else:
            return "Very Long (>1 hr)"
        
    def _plot_hourly_by_weekday(self, parent, df, row):
        """Plot a multi-line chart of hourly consumption by day of the week."""
        if "hour" not in df.columns or "weekday" not in df.columns:
            tk.Label(parent, text="No data for Hourly by Weekday.", bg="black", fg="#e74c3c",
                     font=("Segoe UI", 12, "bold")).grid(row=row, column=0, sticky="ew", padx=10, pady=10)
            return

        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        pivot = df.groupby(["hour", "weekday"]).size().unstack(fill_value=0)
        pivot = pivot.reindex(columns=weekday_order, fill_value=0)
        hours = list(range(24))
        pivot = pivot.reindex(index=hours, fill_value=0)

        fig, ax = plt.subplots(figsize=(7.5, 3))
        colors = ["#e74c3c", "#44b300", "#f39c12", "#222222", "#8e44ad", "#3498db", "#ffffff"]
        for idx, day in enumerate(weekday_order):
            ax.plot(pivot.index, pivot[day], marker="o", label=day, color=colors[idx % len(colors)])
        ax.set_title("Hourly Consumption by Day of Week", color="white")
        ax.set_xlabel("Hour", color="white")
        ax.set_ylabel("Count", color="white")
        ax.set_xticks(hours)
        ax.tick_params(axis='x', labelcolor="white")
        ax.tick_params(axis='y', labelcolor="white")
        ax.legend(
            title="Weekday",
            fontsize=7,
            title_fontsize=8,
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            borderaxespad=0.
        )
        # fig.tight_layout(rect=[0, 0, 0.82, 1])
        fig.tight_layout()
        self._embed_plot(parent, fig, row)

        
    def _plot_top_10_duration(self, parent, top_10_duration, COL_DURATION_WATCHED, row):
        """Plot the Top 10 Most Watched Videos by Duration as a horizontal bar chart."""
        if not top_10_duration.empty:
            fig3, ax3 = plt.subplots(figsize=(7, 3))
            sorted_top10 = top_10_duration.sort_values(by=COL_DURATION_WATCHED, ascending=False)
            video_labels = sorted_top10["video_name"]
            durations = sorted_top10[COL_DURATION_WATCHED].dt.total_seconds() / 60  # convert to minutes
            sns.barplot(y=video_labels, x=durations, ax=ax3, palette="mako")
            ax3.set_title("Top 10 Videos by Duration", color="white")
            ax3.set_xlabel("Total Duration Watched (minutes)", color="white")
            ax3.set_ylabel("Video Name", color="white")
            ax3.tick_params(axis='x', labelcolor="white")
            ax3.tick_params(axis='y', labelcolor="white")
            fig3.tight_layout()
            self._embed_plot(parent, fig3, row)
        else:
            tk.Label(
                parent, text="No data for Top 10 Most Watched Videos by Duration.", bg="black", fg="#44b300",
                font=("Segoe UI", 10, "bold")
            ).grid(row=row*2, column=0, sticky="ew", padx=10, pady=10)
        
    def _plot_weekday_vs_duration_category(self, parent, df, row):
        """Plot a multi-line chart of weekday vs duration category."""
        if "weekday" not in df.columns or "Duration Category" not in df.columns:
            tk.Label(parent, text="No data for Weekday vs Duration Category.", bg="black", fg="#e74c3c",
                    font=("Segoe UI", 12, "bold")).grid(row=row, column=0, sticky="ew", padx=10, pady=10)
            return

        # Prepare data
        weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        category_order = [
            "Very Short (<1 min)", "Short (1-3 min)", "Medium (3-10 min)",
            "Long (10-60 min)", "Very Long (>1 hr)", "Unknown"
        ]
        pivot = df.groupby(["weekday", "Duration Category"]).size().unstack(fill_value=0)
        pivot = pivot.reindex(index=weekday_order, columns=category_order, fill_value=0)

        fig, ax = plt.subplots(figsize=(7, 3))
        colors = ["#ffffff", "#44b300", "#f39c12", "#222222", "#8e44ad", "#e74c3c"]
        for idx, cat in enumerate(category_order):
            ax.plot(pivot.index, pivot[cat], marker="o", label=cat, color=colors[idx % len(colors)])
        ax.set_title("Weekday Watched by Duration Category", color="white")
        ax.set_xlabel("Weekday", color="white")
        ax.set_ylabel("Count", color="white")
        ax.tick_params(axis='x', labelcolor="white", rotation=30)
        ax.tick_params(axis='y', labelcolor="white")
        ax.legend(
            title="Duration Category",
            fontsize=8,
            title_fontsize=9,
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            borderaxespad=0.
        )
        fig.tight_layout(rect=[0, 0, 0.82, 1])
        self._embed_plot(parent, fig, row)

    def _plot_hour_vs_duration_category(self, parent, df, row):
        """Plot a heatmap of hour vs duration category counts."""
        pivot = pd.pivot_table(
            df,
            index="hour",
            columns="Duration Category",
            values="video_name" if "video_name" in df.columns else df.columns[0],
            aggfunc="count",
            fill_value=0
        )
        hours = list(range(24))
        categories = [
            "Very Short (<1 min)", "Short (1-3 min)", "Medium (3-10 min)",
            "Long (10-60 min)", "Very Long (>1 hr)", "Unknown"
        ]
        pivot = pivot.reindex(index=hours, columns=categories, fill_value=0)

        fig, ax = plt.subplots(figsize=(6.5, 5.3))
        sns.heatmap(pivot, annot=True, fmt="d", cmap="YlGnBu", ax=ax, cbar=True)
        ax.set_title("Hour vs Duration Category", color="white")
        ax.set_xlabel("Duration Category", color="white")
        ax.set_ylabel("Hour of Day", color="white")
        ax.tick_params(axis='x', labelcolor="white", rotation=20)
        ax.tick_params(axis='y', labelcolor="white")
        fig.tight_layout()
        self._embed_plot(parent, fig, row)

    def _plot_last_30_days_with_categories(self, parent, video_count_by_date, last_30, df, COL_TOTAL_DURATION):
        """Plot total and duration category lines for the last 30 days."""
        if COL_TOTAL_DURATION in df.columns and "date" in df.columns:
            # for 30 days only categories
            cat_daily = last_30.groupby(["date", "Duration Category"]).size().unstack(fill_value=0)
            cat_daily = cat_daily.reindex(
                columns=["Very Short (<1 min)", "Short (1-3 min)", "Medium (3-10 min)", "Long (10-60 min)", "Very Long (>1 hr)"],
                fill_value=0
            )
        else:
            cat_daily = None

        fig, ax = plt.subplots(figsize=(6, 4))
        sns.lineplot(x=video_count_by_date.index, y=video_count_by_date.values, ax=ax, color="#e74c3c", marker="o", label="Total")
        if cat_daily is not None:
            colors = {
                "Very Short (<1 min)": "#ffffff",
                "Short (1-3 min)": "#44b300",
                "Medium (3-10 min)": "#f39c12",
                "Long (10-60 min)": "#222222",
                "Very Long (>1 hr)": "#8e44ad"
            }
            for cat in cat_daily.columns:
                if cat_daily[cat].sum() > 0:
                    sns.lineplot(
                        x=cat_daily.index, y=cat_daily[cat].values, ax=ax,
                        marker="o", label=cat, color=colors.get(cat, None), linewidth=1.5, alpha=0.7
                    )
        ax.set_title("Videos Watched in Last 30 Days", color="white")
        ax.set_xlabel("Date", color="white")
        ax.set_ylabel("Count", color="white")
        ax.tick_params(axis='x', rotation=45, labelcolor="white")
        ax.tick_params(axis='y', labelcolor="white")
        ax.legend(loc="upper left", fontsize=8, frameon=False, labelcolor="white")
        fig.tight_layout()
        self._embed_plot(parent, fig, 0)

    def _make_table(self, parent, df, title, row, fg, table_height=6):
        if df.empty:
            tk.Label(
                parent, text=f"No data for {title}.", bg="black", fg=fg,
                font=("Segoe UI", 12, "bold")
            ).grid(row=row*2, column=0, sticky="ew", padx=10, pady=10)
            return
        label = tk.Label(
            parent, text=title, bg="black", fg=fg,
            font=("Segoe UI", 11, "bold")
        )
        label.grid(row=row*2, column=0, sticky="w", padx=10, pady=(10, 0))
        cols = list(df.columns)
        tree = ttk.Treeview(
            parent, columns=cols, show="headings", height=table_height, style="dashboardStyle.Treeview"
        )
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, anchor="center")
        for _, rowdata in df.iterrows():
            tree.insert('', 'end', values=tuple(rowdata))
        tree.grid(row=row*2+1, column=0, sticky="ew", padx=10, pady=5)

    def _embed_plot(self, parent, fig, row):
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

    def on_closing(self):
        plt.close('all')
        self.master.destroy()

    def center_window(self):
        """Centers the application window on the screen."""
        self.master.update_idletasks()
        self.master.geometry(f"{self.window_width}x{self.window_height}")
        
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        
        position_x = int((screen_width - self.window_width) / 2)
        position_y = int((screen_height - self.window_height) / 2)
        
        self.master.geometry(f"{self.window_width}x{self.window_height}+{position_x}+{position_y}")

def show_stats_window(parent=None):
    if parent is not None:
        DashboardWindow(parent)
    else:
        root = tk.Tk()
        DashboardWindow(root)
        root.mainloop()

if __name__ == "__main__":
    show_stats_window()