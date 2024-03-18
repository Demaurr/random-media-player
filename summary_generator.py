STYLE_FILE = "../Styles/style.css"

class HTMLSummaryReport:
    def __init__(self, data):
        """
        Initialize HTMLSummaryReport class with data.

        Args:
        - data (list): A list of dictionaries where each dictionary represents attributes.
        """
        self.data = data

    def format_session_time(self, seconds):
        """
        Formats session time from seconds to HH:MM:SS format.
        Args:
            seconds (int): The duration of the session in seconds.
        Returns:
            str: The formatted session time in HH:MM:SS format.
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def generate_html(self, date="0", session_time="00:00:00"):
        """
        Generate an HTML summary report.

        Returns:
        - html_content (str): HTML content of the summary report.
        """
        total_count = sum(item.get('Count', 0) for item in self.data)
        # total_count = len(self.data)
        total_duration_seconds = sum(self.parse_duration(item.get('Duration Watched', '0:00:00')) for item in self.data)

        # total_duration_hours, remaining_duration_seconds = divmod(total_duration_seconds, 3600)
        # total_duration_minutes, total_duration_seconds = divmod(remaining_duration_seconds, 60)
        total_duration = self.format_session_time(seconds=total_duration_seconds)

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<title>Summary Report</title>
<link rel="stylesheet" type="text/css" href="{STYLE_FILE}">
</head>
<body>
<div class="container">
<h1>Summary Report</h1>
<div class="datetime"><p class="generation">Generated on: {date}</p><span class="sessiontime">Session Lasted: {session_time}</span></div>
<p>Total Count of Videos: {total_count}</p>
<p>Total Duration Watched: {total_duration}</p>
<table>
<tr><th>Item Name</th><th>Times</th><th>Duration</th><th>Folder Name</th></tr>\n"""

        for value in self.data:
            html_content += f"<tr><td><strong>{value.get('File Name', '')}</strong></td><td>{value.get('Count', '')}</td><td>{value.get('Duration Watched', '')}</td><td>{value.get('Folder', '')}</td></tr>\n"
        html_content += "</table>\n</div>\n</body>\n</html>"
        return html_content

    def parse_duration(self, duration_str):
        """
        Parse duration string in format 'H:MM:SS.mmm' and return duration in seconds.

        Args:
        - duration_str (str): Duration string in format 'H:MM:SS.mmm'.

        Returns:
        - duration_seconds (float): Duration in seconds.
        """
        try:
            hours, minutes, seconds = map(float, duration_str.split(':'))
            return int(hours) * 3600 + int(minutes) * 60 + seconds
        except ValueError:
            # Handle the case where the duration string is not in the expected format
            print(f"Error: Unable to parse duration string '{duration_str}'. Returning 0.")
            return 0


