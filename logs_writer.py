import datetime

class LogManager:
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path

    def update_logs(self, action, file_path):
        timestamp = self._get_timestamp()
        log_message = f"{timestamp} - {action}: {file_path}\n"
        self._write_to_log(log_message)

    def error_logs(self, error_message):
        timestamp = self._get_timestamp()
        log_message = f"{timestamp} - ERROR: {error_message}\n"
        self._write_to_log(log_message)

    def _write_to_log(self, message):
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as log_file:
                log_file.write(message)
        except Exception as e:
            print(f"Error writing to log file: {e}")

    def _get_timestamp(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
