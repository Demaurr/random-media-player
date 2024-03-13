STYLE_FILE = "../Styles/style.css"

class HTMLSummaryReport:
    def __init__(self, data):
        """
        Initialize HTMLSummaryReport class with data.

        Args:
        - data (dict): A dictionary containing key-value pairs where each value is another dictionary representing attributes.
        """
        self.data = data

    def generate_html(self, date="0", session_time="00:00:00"):
        """
        Generate an HTML summary report.

        Returns:
        - html_content (str): HTML content of the summary report.
        """
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
<table>
<tr><th>Item Name</th><th>Times</th><th>Duration</th><th>Folder Name</th></tr>\n"""

        for value in self.data:
            html_content += f"<tr><td><strong>{value.get('File Name', '')}</strong></td><td>{value.get('Count', '')}</td><td>{value.get('Duration Watched', '')}</td><td>{value.get('Folder', '')}</td></tr>\n"
        html_content += "</table>\n</div>\n</body>\n</html>"
        return html_content